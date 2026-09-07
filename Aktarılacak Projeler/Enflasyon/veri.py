# -*- coding: utf-8 -*-
"""Enflasyon panosu — veri katmanı (EVDS3).

Ne yapar
--------
1. EVDS3 REST servisinden TÜFE (2025=100) ağacını, Özel Kapsamlı Göstergeleri
   (ÖKTG A–F + TCMB mal/hizmet ayrışımı), Yİ-ÜFE'yi, beklenti anketlerini,
   fonlama maliyetini ve YKKE'yi çeker.
2. Her seriyi TTL'li önbelleğe (data/cache/*.csv) yazar; ağ düşerse ESKİ
   önbelleğe düşer ama SESSİZ kalmaz — uyarı basar, uyarilar.json'a düşer.
3. `son_ay()` ile analizin "güncel ay"ını veriden okur (sabit tarih YASAK).
4. Aile bazlı tazelik denetimi yapar (TÜFE ile PKA aynı takvimde değil; tek
   eşik her ay yanlış alarm üretirdi).

Uç nokta notu
-------------
Eski `evds2.tcmb.gov.tr/service/evds` yolu ve `tcmb` Python istemcisi ARTIK
ÇALIŞMIYOR (eski yol HTML SPA kabuğu döndürüyor). Çalışan uç nokta:

    https://evds3.tcmb.gov.tr/igmevdsms-dis/{endpoint}{param}={deger}&...

Sorgu dizesi `?` ile başlamaz, parametreler doğrudan yola eklenir; anahtar
URL'de değil `key:` HTTP başlığında gider. Aylık seriler "YYYY-M", günlük
seriler "DD-MM-YYYY" etiketlidir — iki ayrı ayrıştırıcı gerekir.

Satır sınırı: EVDS uzun aralıkta ~1000 satırdan sonrasını aralığın SONUNDAN
geriye doldurup gerisini SESSİZCE kırpıyor. Aylık seriler (≈260 satır) tek
istekte tam gelir; günlük/iş günü seriler yıllık parçalara bölünür.

Koşum:  python3 veri.py
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import time
import urllib.error
import urllib.request

import pandas as pd

# --------------------------------------------------------------------------- yollar
PROJE = pathlib.Path(__file__).resolve().parent
KOK = PROJE.parent.parent                      # …/TTO Trading
VERI = PROJE / "data"
CACHE = VERI / "cache"
for _p in (VERI, CACHE):
    _p.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------- anahtar
# EVDS anahtarı kaynak koda GÖMÜLMEZ. Arama sırası:
#   TTO_EVDS_KEY ortam değişkeni (CI'da depo secret'ı)
#   → <proje>/.evds_key  → kök/.evds_key  → kardeş TCMBNetRezerv/.evds_key
# Bu projeye .evds_key KOPYALANMAZ; kardeş projedeki dosya okunur.
_ADAYLAR = [
    PROJE / ".evds_key",
    KOK / ".evds_key",
    KOK / "Aktarılacak Projeler" / "TCMBNetRezerv" / ".evds_key",
]


def _evds_anahtari() -> str:
    a = (os.environ.get("TTO_EVDS_KEY") or "").strip()
    if a:
        return a
    for yol in _ADAYLAR:
        if yol.exists():
            try:
                a = yol.read_text(encoding="utf-8").strip()
            except OSError as ex:
                print(f"UYARI: {yol} okunamadı ({type(ex).__name__}).")
                a = ""
            if a:
                return a
    raise RuntimeError(
        "EVDS anahtarı bulunamadı. export TTO_EVDS_KEY=<anahtar> ya da şu "
        "dosyalardan birine yazın (.gitignore'da): "
        + " / ".join(str(y) for y in _ADAYLAR)
    )


BASE = "https://evds3.tcmb.gov.tr/igmevdsms-dis"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")

CACHE_TTL_SAAT = 12          # seri verisi
KATALOG_TTL_SAAT = 168       # seri listesi / grup metaverisi (haftalık)

_UYARI: list[str] = []
_ANAHTAR: str | None = None


def uyar(mesaj: str) -> None:
    """Görünür uyarı: ekrana basılır ve uyarilar.json'a taşınır."""
    if mesaj not in _UYARI:
        _UYARI.append(mesaj)
    print("  ! " + mesaj, flush=True)


def anahtar() -> str:
    global _ANAHTAR
    if _ANAHTAR is None:
        _ANAHTAR = _evds_anahtari()
    return _ANAHTAR


def _cek(url: str, deneme: int = 3):
    """EVDS3'ten JSON. Anahtar `key:` BAŞLIĞINDA gider, URL'de değil."""
    son_hata: Exception | None = None
    for i in range(deneme):
        try:
            req = urllib.request.Request(
                url, headers={"key": anahtar(), "User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as ex:           # ağ, zaman aşımı, 5xx…
            son_hata = ex
            if i < deneme - 1:
                time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"EVDS isteği düştü: {son_hata}") from son_hata


def _tazelik():
    """ortak/tazelik — önbellek tazeliğinin TEK tanımı; TTO_YENILE orada okunur.
    Hat kendi klasöründen elle koşturulursa ortak/ PYTHONPATH'te olmayabilir;
    depo kökünden bulunur (kalıp: metrik.py'nin _bicim yardımcısı)."""
    try:
        import tazelik
    except ImportError:
        import pathlib as _pl
        import sys as _sys
        _sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[2] / "ortak"))
        import tazelik
    return tazelik


def _taze(yol: pathlib.Path, ttl_saat: float) -> bool:
    """Önbellek hâlâ kullanılabilir mi — karar ortak/tazelik'te (TTO_YENILE)."""
    return _tazelik().taze(yol, ttl_saat)


def _yas_gun(yol: pathlib.Path) -> float:
    return _tazelik().yas_gun(yol)


# --------------------------------------------------------------------------- seri çekimi
def _ayristir_aylik(items, kolon) -> pd.Series:
    df = pd.DataFrame(items)
    if kolon not in df.columns:
        return pd.Series(dtype=float)
    t = pd.to_datetime(df["Tarih"], format="%Y-%m", errors="coerce")
    s = pd.to_numeric(df[kolon].replace("", None), errors="coerce")
    s.index = t
    return s.dropna().sort_index()


def _ayristir_gunluk(items, kolon) -> pd.Series:
    df = pd.DataFrame(items)
    if kolon not in df.columns:
        return pd.Series(dtype=float)
    t = pd.to_datetime(df["Tarih"], format="%d-%m-%Y", errors="coerce")
    s = pd.to_numeric(df[kolon].replace("", None), errors="coerce")
    s.index = t
    return s.dropna().sort_index()


def evds_aylik(kod: str, bas: str = "01-01-2005", yenile: bool = False) -> pd.Series:
    """Tek aylık seri. TTL'li önbellek; ağ hatasında eski önbelleğe GÖRÜNÜR
    uyarıyla düşer (çevrimdışı koşu çalışır ama sessiz kalmaz)."""
    guvenli = kod.replace(".", "_")
    cyol = CACHE / f"evds_{guvenli}.csv"
    if _taze(cyol, CACHE_TTL_SAAT) and not yenile:
        s = pd.read_csv(cyol, index_col=0, parse_dates=True).iloc[:, 0]
        s.name = kod
        return s
    son = (pd.Timestamp.today() + pd.DateOffset(months=2)).strftime("01-%m-%Y")
    url = f"{BASE}/series={kod}&startDate={bas}&endDate={son}&type=json"
    try:
        items = _cek(url).get("items", [])
        s = _ayristir_aylik(items, guvenli)
        if s.empty:
            raise RuntimeError("boş yanıt")
    except Exception as ex:
        if cyol.exists():
            uyar(f"EVDS erişilemedi ({kod}: {ex}); ESKİ önbellek kullanılıyor "
                 f"({cyol.name}, {_yas_gun(cyol):.0f} gün eski). Bu seri BAYAT olabilir.")
            s = pd.read_csv(cyol, index_col=0, parse_dates=True).iloc[:, 0]
            s.name = kod
            return s
        raise RuntimeError(f"EVDS düştü ve önbellek yok: {kod} ({ex})") from ex
    s.name = kod
    s.to_csv(cyol)
    time.sleep(0.25)
    return s


EVDS_PARCA_GUN = 366   # günlük seride satır sınırı için yıllık parçalama


def evds_gunluk(kod: str, bas: str = "01-01-2018", yenile: bool = False) -> pd.Series:
    """Tek iş günü serisi — yıllık parçalar hâlinde (EVDS satır sınırı)."""
    guvenli = kod.replace(".", "_")
    cyol = CACHE / f"evdsg_{guvenli}.csv"
    if _taze(cyol, CACHE_TTL_SAAT) and not yenile:
        s = pd.read_csv(cyol, index_col=0, parse_dates=True).iloc[:, 0]
        s.name = kod
        return s
    t0 = pd.to_datetime(bas, dayfirst=True)
    t1 = pd.Timestamp.today().normalize()
    parcalar: list[pd.Series] = []
    try:
        imlec = t0
        while imlec <= t1:
            sonu = min(imlec + pd.Timedelta(days=EVDS_PARCA_GUN - 1), t1)
            url = (f"{BASE}/series={kod}&startDate={imlec:%d-%m-%Y}"
                   f"&endDate={sonu:%d-%m-%Y}&type=json")
            p = _ayristir_gunluk(_cek(url).get("items", []), guvenli)
            if len(p):
                parcalar.append(p)
            imlec = sonu + pd.Timedelta(days=1)
            time.sleep(0.2)
        if not parcalar:
            raise RuntimeError("boş yanıt")
        s = pd.concat(parcalar)
        s = s[~s.index.duplicated(keep="last")].sort_index()
    except Exception as ex:
        if cyol.exists():
            uyar(f"EVDS erişilemedi ({kod}: {ex}); ESKİ önbellek kullanılıyor "
                 f"({cyol.name}, {_yas_gun(cyol):.0f} gün eski). Bu seri BAYAT olabilir.")
            s = pd.read_csv(cyol, index_col=0, parse_dates=True).iloc[:, 0]
            s.name = kod
            return s
        raise RuntimeError(f"EVDS düştü ve önbellek yok: {kod} ({ex})") from ex
    s.name = kod
    s.to_csv(cyol)
    return s


def seri_listesi(grup: str, yenile: bool = False) -> pd.DataFrame:
    """Bir veri grubunun seri kataloğu (SERIE_CODE, SEVIYE, UST_SERIE_CODE,
    START_DATE, END_DATE…). Haftalık TTL — ağaç sık değişmez."""
    cyol = CACHE / f"katalog_{grup}.json"
    if _taze(cyol, KATALOG_TTL_SAAT) and not yenile:
        return pd.DataFrame(json.loads(cyol.read_text(encoding="utf-8")))
    try:
        veri = _cek(f"{BASE}/serieList/type=json&code={grup}")
        kayit = veri if isinstance(veri, list) else veri.get("items", veri)
        if not kayit:
            raise RuntimeError("boş katalog")
        cyol.write_text(json.dumps(kayit, ensure_ascii=False), encoding="utf-8")
    except Exception as ex:
        if cyol.exists():
            uyar(f"EVDS seri kataloğu alınamadı ({grup}: {ex}); eski katalog "
                 f"kullanılıyor ({_yas_gun(cyol):.0f} gün eski).")
            kayit = json.loads(cyol.read_text(encoding="utf-8"))
        else:
            raise
    return pd.DataFrame(kayit)


# --------------------------------------------------------------------------- seri kümesi
# (a) TÜFE genel + 13 ANA GRUP. 12 değil 13: ECOICOP v2 ile "12 Sigorta ve
#     finansal hizmetler" ayrı grup oldu, "13 Kişisel bakım…" sona geçti.
ANA_GRUP_AD = {
    "01": "Gıda ve alkolsüz içecekler",
    "02": "Alkollü içecekler ve tütün",
    "03": "Giyim ve ayakkabı",
    "04": "Konut, su, elektrik, gaz ve diğer yakıtlar",
    "05": "Mobilya, ev eşyası ve ev bakımı",
    "06": "Sağlık",
    "07": "Ulaştırma",
    "08": "Bilgi ve iletişim",
    "09": "Eğlence, spor ve kültür",
    "10": "Eğitim hizmetleri",
    "11": "Lokanta ve konaklama hizmetleri",
    "12": "Sigorta ve finansal hizmetler",
    "13": "Kişisel bakım, sosyal koruma ve çeşitli",
}

# (b) ÖKTG — kesin kodlar (bie_oktug2025, önek TP.FE25.OKTG + iki hane).
OKTG_AD = {
    "01": "TÜFE (kontrol kopyası)",
    "02": "A · mevsimlik ürünler hariç",
    "03": "B · işlenmemiş gıda, enerji, alkol-tütün ve altın hariç",
    "04": "C · enerji, gıda, alkol-tütün ve altın hariç",
    "05": "D · işlenmemiş gıda, alkol-tütün hariç",
    "06": "E · alkol-tütün hariç",
    "07": "F · yönetilen/yönlendirilen fiyatlar hariç",
    "08": "Mallar",
    "09": "Enerji",
    "10": "Gıda ve alkolsüz içecekler",
    "11": "İşlenmemiş gıda",
    "12": "Taze meyve-sebze",
    "13": "Diğer işlenmemiş gıda",
    "14": "İşlenmiş gıda",
    "15": "Ekmek ve tahıllar",
    "16": "Diğer işlenmiş gıda",
    "17": "Enerji ve gıda dışı mallar",
    "18": "Temel mallar",
    "19": "Giyim ve ayakkabı",
    "20": "Dayanıklı mallar (altın hariç)",
    "21": "Diğer temel mallar",
    "22": "Alkollü içecekler, tütün ve altın",
    "23": "Hizmet",
    "24": "Kira",
    "25": "Lokanta ve otel",
    "26": "Ulaştırma hizmetleri",
    "27": "Haberleşme hizmetleri",
    "28": "Diğer hizmetler",
}

# Panonun momentum tablosuna giren "merkezî" seriler (etiket → EVDS kodu).
# Enerji ve işlenmemiş gıda BİLİNÇLİ olarak dışarıda: 3a SAAR'ları ±%25 salınıyor
# (seri kataloğunda ölçüldü), merkezî ölçü olarak yayımlanamaz. Katkı ve
# ayrıştırma grafiklerinde ayrıca yer alıyorlar.
ANA_SERI = {
    "tufe":        "TP.TUKFIY2025.GENEL",
    "cekirdek_b":  "TP.FE25.OKTG03",
    "cekirdek_c":  "TP.FE25.OKTG04",
    "hizmet":      "TP.FE25.OKTG23",
    "temel_mal":   "TP.FE25.OKTG18",
    "kira":        "TP.FE25.OKTG24",
    "enerji":      "TP.FE25.OKTG09",
    "gida":        "TP.FE25.OKTG10",
    "islenmemis_gida": "TP.FE25.OKTG11",
    "islenmis_gida":   "TP.FE25.OKTG14",
    "alkol_tutun_altin": "TP.FE25.OKTG22",
    "yonetilen_haric":   "TP.FE25.OKTG07",
    "mallar":      "TP.FE25.OKTG08",
    "yi_ufe":      "TP.TUFE1YI.T1",
    "ykke":        "TP.YKKE.TR",
    # İTO AİLESİ — adlar EVDS'İN KENDİSİNDEN OKUNDU.
    # Serinin adı bir süre "EVDS vermiyor" sanıldı; vermiyor değildi, YANLIŞ
    # UÇTAN soruluyordu. serieList ucu DOĞRU GRUP KODUYLA çağrılınca 51 seri
    # adıyla birlikte geliyor. Doğru sıra: katalogdan grup kodu → serieList →
    # ad. "Bulamadım" ile "yok" arasındaki fark yine buradaydı.
    #   TP.FG.IST1.23  Genel Endeks (İTO 2023=100)          2024-01 →
    #   TP.FG.IST2.23  Gıda Ve Alkolsüz İçecekler           (13 alt grubun ilki)
    #   TP.FG.U95      İstanbul Ücretliler Geçinme Endeksi (1995=100)  1996-01 →
    # Ad okunabiliyor olsa da sayıyla doğrulama KALKMAZ: ad kaynağın
    # etiketidir, sayı kaynağın kendisi. İkisi ayrışırsa hattın haberi olmalı.
    "ito_ist":     "TP.FG.IST1.23",
    # ÜCRETLİLER GEÇİNME ENDEKSİ — İTO'nun ikinci başlık endeksi ve TÜFE'nin
    # değil GEÇİM MALİYETİNİN ölçüsü: sepeti ücretli hane harcama yapısına
    # göre ağırlıklandırılmış. Dört baz varyantı var (1963/1968/1985/1995) ve
    # AYLIK DEĞİŞİMLERİ BİRBİRİNDEN FARKLI — yani "ÜGE şu kadar arttı" cümlesi
    # hangi varyant olduğu söylenmeden kurulamaz. Ağustos 2026'da U95 %1,97,
    # U85 %1,15, U68 %1,33, U63 %1,18 veriyor. İTO'nun yayımladığı ve basında
    # çıkan tablo U95'tir; kimlik 2024-01→2026-08 arasındaki 32 ayın tamamında
    # o tabloyla birebir tutarak pinlendi (bkz. ito_yayim.json → uge).
    "ito_uge":     "TP.FG.U95",
    # KIYAS VARYANTI: aynı endeksin 1985 bazı. Tek başına yayımlanmıyor ama
    # varyantlar arası farkın büyüklüğünü OKURA göstermek için taşınıyor —
    # "hangi ÜGE" sorusunun cevabı sayfada bir sayıyla verilebilsin.
    "ito_uge_85":  "TP.FG.U85",
}

# Katkı ayrıştırmasının beşlisi — TCMB'nin aylık Fiyat Gelişmeleri raporundaki
# gruplama. Beşi TÜFE sepetini ÖRTER ve ÖRTÜŞMEZ (bölüşüm tam).
KATKI_GRUP = {
    "gida":              ("Gıda ve alkolsüz içecekler", "TP.FE25.OKTG10"),
    "enerji":            ("Enerji", "TP.FE25.OKTG09"),
    "temel_mal":         ("Temel mallar", "TP.FE25.OKTG18"),
    "alkol_tutun_altin": ("Alkol, tütün ve altın", "TP.FE25.OKTG22"),
    "hizmet":            ("Hizmet", "TP.FE25.OKTG23"),
}

# (e) Beklentiler — dört ayrı kesim, dört ayrı ölçek, karıştırılmaz.
BEKLENTI = {
    "pka_ay_cari":   "TP.PKAUO.S01.A.U",   # cari ayın aylık TÜFE'si
    "pka_ay_1":      "TP.PKAUO.S01.B.U",   # 1 ay sonrasının aylık TÜFE'si
    "pka_ay_2":      "TP.PKAUO.S01.C.U",   # 2 ay sonrasının aylık TÜFE'si
    "pka_yilsonu":   "TP.PKAUO.S01.D.U",   # cari yıl sonu yıllık
    "pka_12a":       "TP.PKAUO.S01.E.U",   # 12 ay sonrası yıllık
    "pka_24a":       "TP.PKAUO.S01.F.U",   # 24 ay sonrası yıllık
    "pka_5y":        "TP.PKAUO.S01.G.U",   # 5 yıl sonrası yıllık
    "pka_12a_medyan": "TP.BEK.S01.E.M",
    "pka_12a_std":   "TP.BEK.S01.E.S",
    "pka_12a_n":     "TP.BEK.S01.E.X",     # katılımcı sayısı — anket zayıflarsa uyarı
    "pka_faiz_12a":  "TP.PKAUO.S04.D.U",   # 12 ay sonrası politika faizi beklentisi
    "reel_kesim_12a": "TP.ENFBEK.IYA12ENF",
    "hanehalki_12a":  "TP.ENFBEK.HBA12ENF",
}

# (g) Faiz — EVDS'te "politika faizi" adında seri YOK. Birincil: TCMB ağırlıklı
# ortalama fonlama maliyeti; ikincil: TLREF. BIS serisi (~2 ay gecikmeli)
# kullanılmıyor.
FAIZ = {
    "aofm":  "TP.APIFON4",
    "tlref": "TP.BISTTLREF.ORAN",
}

# Tazelik: aile başına AYRI tolerans. Tek eşik H-ÜFE gibi bir ay geriden gelen
# hatları her ay yanlışlıkla "bayat" işaretler.
#   (aile etiketi, beklenen gecikme ayı, ayın kaçından sonra uyar)
TAZELIK = {
    "tufe":     ("TÜFE / ÖKTG / Yİ-ÜFE", 1, 6),
    "beklenti": ("PKA beklenti anketi", 0, 25),
    "ykke":     ("Yeni Kiracı Kira Endeksi", 1, 20),
    "ito":      ("İstanbul Tüketici Fiyat İndeksi (İTO, 2023=100)", 1, 5),
}
FAIZ_TAZELIK_GUN = 4   # iş günü seriler: 4 takvim günü


# --------------------------------------------------------------------------- ay adları
AY_TR = {1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
         7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"}
AY_KISA = {1: "Oca", 2: "Şub", 3: "Mar", 4: "Nis", 5: "May", 6: "Haz",
           7: "Tem", 8: "Ağu", 9: "Eyl", 10: "Eki", 11: "Kas", 12: "Ara"}


def ad_uzun(t) -> str:
    t = pd.Timestamp(t)
    return f"{AY_TR[t.month]} {t.year}"


def ad_kisa(t) -> str:
    t = pd.Timestamp(t)
    return f"{AY_KISA[t.month]}-{str(t.year)[2:]}"


# --------------------------------------------------------------------------- şekil saatleri
#  BU HATTIN FİGÜRLERİ TEK RİTİMDE DEĞİL. Manşet, çekirdek, katkı ve beklenti
#  serileri ana endeksle birlikte ilerler; KESİT ölçüleri (kırpılmış ortalama,
#  medyan, difüzyon) üç haneli alt kalem kırılımını bekler ve ondan aylarca
#  geride biter. Sayfa hepsine hattın tek ana saatini basarsa kesit paneli
#  bayatken TAZE görünür — okurun "fiyat artışı hâlâ ne kadar yaygın" sorusunu
#  cevapladığını sandığı panel, aslında aylar önceki yaygınlığı gösterir.
#
#  Değerler ÖLÇÜMDEN gelir, türetilmez: `son_ay` (ana endeks), `dagilim__son_ay`
#  (kesitin kendi ucu) ve kanat profillerinin kendi `son_ay`ları. Ölçüm yoksa
#  değer None kalır ve o şeklin altına tarih basılmaz — uydurmaktan iyidir.
#
#  Defter BURADA duruyor çünkü iki tüketicisi var: grafik.py figürün KENDİ alt
#  başlığına yazar, ozet_uret.py sayfa altındaki damga için ozet.json'a
#  `_sekil_tarih` olarak koyar. İki ayrı liste tutulsaydı bir gün sessizce
#  ayrışır ve hangisinin neyi söylediği kimsenin aklında kalmazdı.
def sekil_saatleri(o: dict, ip: dict | None = None, up: dict | None = None,
                   bp: dict | None = None, uzun: bool = False
                   ) -> dict[str, str | None]:
    """Figür başına veri ucu; `o` = data/metrik_ozet.json, kanatlar profil dosyaları.

    `uzun=True` figür alt başlığının yazımını verir ("Ağustos 2026");
    varsayılan site sözleşmesidir ("08.2026", ortak/bicim ayın son gününe
    demirler). AYLIK bir gözlemi gün gibi yazmak ("01.08.2026") okura o GÜNÜN
    ölçümüymüş gibi görünürdü.
    """
    def ay(t):
        if not t:
            return None
        t = pd.Timestamp(t)
        return ad_uzun(t) if uzun else t.strftime("%m.%Y")

    def baglayici(*tarihler):
        """Karma figürün damgası: bacakların EN ESKİSİ.

        Figürün sözü serilerin KIYASIDIR ve kıyas ancak hepsinin ölçüldüğü aya
        kadar kurulabilir; en tazesini yazmak öbür bacağı olduğundan yeni
        gösterir. min() yapısal — bugünkü sıralamayı varsaymaz.
        """
        g = [pd.Timestamp(t) for t in tarihler if t]
        return ay(min(g)) if g else None

    ana = o.get("son_ay")
    kesit = o.get("dagilim__son_ay")
    d: dict[str, str | None] = {
        "01_manset_momentum.html": ay(ana),
        "02_cekirdek_momentum.html": ay(ana),
        "03_arindirma.html": ay(ana),
        "04_katki.html": ay(ana),
        # İKİ RİTİM BİR FİGÜRDE: iki panelin de konusu kesittir, üstteki
        # manşet SAAR'ı yalnız kıyas çizgisidir. Bağlayıcı bacak kesittir.
        "05_dagilim_difuzyon.html": baglayici(kesit, ana),
        "06_hizmet_mal.html": ay(ana),
        "07_beklenti.html": ay(ana),
        # Fonlama maliyeti içinde bulunulan aya kadar var (reel__faiz_tarih),
        # enflasyon bacağı bir ay geride: figür ikisinin KARŞILAŞTIRMASI
        # olduğu için ortak ay bağlar.
        "08_reel_faiz.html": baglayici(o.get("reel__ex_post_tarih") or ana,
                                       o.get("reel__faiz_tarih")),
        # Senaryo bacakları geleceğe uzanır ama ÖLÇÜM değildir; figürün
        # ölçülmüş ucu gerçekleşen seridir.
        "09_baz_etkisi.html": ay(ana),
    }
    if ip:
        # İTO kanadının dördü de aynı profilden çizilir; ucu profilin son ayı.
        # 13'ün alt paneli daha erken bir ayda biter GÖRÜNÜR ama o bir SEÇİMDİR
        # (TÜFE'nin İTO'yu aştığı aylar), ölçümün durduğu yer değil — çizilen
        # izden okunan bir uç orada ölçüm değil, seçim sonucu olurdu.
        for _ad in ("10_ito_tufe.html", "11_ito_kural.html",
                    "12_ito_takvim.html", "13_ito_bulut.html"):
            d[_ad] = ay(ip.get("son_ay"))
    if up:
        d["14_uge_ucler.html"] = baglayici(up.get("son_ay"), ana)
    if bp:
        d["15_sacilim.html"] = baglayici(bp.get("son_ay"), ana)
        d["16_yaris.html"] = ay(bp.get("son_ay"))
        d["17_tahmin.html"] = ay(bp.get("son_ay"))
    return d


# --------------------------------------------------------------------------- toplama
def _panel(kodlar: dict[str, str], yenile: bool = False) -> pd.DataFrame:
    out: dict[str, pd.Series] = {}
    for ad, kod in kodlar.items():
        try:
            out[ad] = evds_aylik(kod, yenile=yenile)
        except Exception as ex:
            uyar(f"SERİ ALINAMADI: {ad} ({kod}) — {ex}")
    df = pd.DataFrame(out)
    df.index.name = "tarih"
    return df.sort_index()


def alt_kalem_kodlari(yenile: bool = False) -> pd.DataFrame:
    """TÜFE ağacı: bie_tukfiy2025 kataloğu, SEVIYE ve UST_SERIE_CODE ile.

    Sessiz bayatlama tuzağı: 349 serinin bir kısmı 12.2025'te BİTİYOR
    (`TP.TUKFIY2025.0815` — sınıflama değişiminde düşen kalemler). END_DATE'i
    genel endeksinkiyle uyuşmayan kalemler işaretlenir; kırpılmış ortalama /
    difüzyon hesabına ALINMAZ.
    """
    kat = seri_listesi("bie_tukfiy2025", yenile=yenile)
    if kat.empty:
        return kat
    # kolon adları büyük harf; bazı kurulumlarda farklı isimler geliyor
    kolon = {c.upper(): c for c in kat.columns}
    kod_k = kolon.get("SERIE_CODE") or kolon.get("SERIECODE")
    ad_k = kolon.get("SERIE_NAME") or kolon.get("SERIENAME")
    kat = kat.rename(columns={kod_k: "kod", ad_k: "ad"})
    for a, b in (("SEVIYE", "seviye"), ("UST_SERIE_CODE", "ust"),
                 ("START_DATE", "bas"), ("END_DATE", "son")):
        if kolon.get(a):
            kat = kat.rename(columns={kolon[a]: b})
    for c in ("seviye", "ust", "bas", "son"):
        if c not in kat.columns:
            kat[c] = None
    kat["kod"] = kat["kod"].astype(str).str.strip()
    # COICOP kuyruğu: TP.TUKFIY2025.<kuyruk>
    kat["kuyruk"] = kat["kod"].str.split(".").str[-1]
    kat["hane"] = kat["kuyruk"].str.len()
    return kat[["kod", "ad", "kuyruk", "hane", "seviye", "ust", "bas", "son"]]


def tazelik_denetimi(aylik: pd.DataFrame, gunluk: pd.DataFrame) -> list[str]:
    """Aile bazlı tazelik. Bugünün takvim gününe göre eşik uygulanır."""
    bugun = pd.Timestamp.today().normalize()
    uy: list[str] = []

    def _son(ad: str):
        if ad not in aylik.columns:
            return None
        s = aylik[ad].dropna()
        return s.index[-1] if len(s) else None

    def _denet(aile: str, ad: str, etiket_seri: str):
        etiket, gecikme, gun_esigi = TAZELIK[aile]
        son = _son(ad)
        if son is None:
            uy.append(f"TAZELİK: '{etiket_seri}' hiç yüklenemedi — {etiket} ailesi eksik.")
            return
        # beklenen son ay
        beklenen = (bugun.replace(day=1) - pd.DateOffset(months=gecikme))
        if bugun.day <= gun_esigi:
            beklenen = beklenen - pd.DateOffset(months=1)
        if son < beklenen:
            eksik = (beklenen.year - son.year) * 12 + (beklenen.month - son.month)
            uy.append(
                f"TAZELİK: '{etiket_seri}' son gözlemi {ad_uzun(son)} — bugün "
                f"{bugun:%d.%m.%Y} itibarıyla {ad_uzun(beklenen)} beklenirdi "
                f"({eksik} ay geride, {etiket} takvimi). Kaynak durmuş olabilir.")

    # KISMİ YAYIM: "veri geldi" ile "veri TAM geldi" aynı şey değil.
    # 03.09.2026'da EVDS'te 72 serinin 57'si ağustosa geçmişti (çekirdek,
    # hizmet, gıda, Yİ-ÜFE, İTO) ama MANŞET ailesi — TP.TUKFIY2025.GENEL ve
    # on üç ana harcama grubu — hâlâ temmuzdaydı. Ölçüm katmanı ortak tarihe
    # hizaladığı için sessizce temmuzda kaldı; hat yeşil bitti, "veri
    # değişmedi" dedi ve yayım gününde pano dünkü ayı gösterdi. Arızanın
    # görüntüsü ile sağlığın görüntüsü yine aynıydı.
    #
    # Bu ölçüt o sessizliği kapatıyor: seriler arasında AY FARKI varsa
    # görünür uyarı düşer ve hangi ailenin geride kaldığı adıyla yazılır.
    son_aylar: dict[str, pd.Timestamp] = {}
    for ad in aylik.columns:
        s_ = aylik[ad].dropna()
        if len(s_):
            son_aylar[ad] = s_.index[-1]
    if son_aylar:
        en_yeni = max(son_aylar.values())
        geride = sorted(ad for ad, t in son_aylar.items() if t < en_yeni)
        if geride:
            ornek = ", ".join(geride[:6]) + (f" +{len(geride) - 6}"
                                             if len(geride) > 6 else "")
            uy.append(
                f"KISMİ YAYIM: {len(geride)}/{len(son_aylar)} seri en yeni aydan "
                f"({ad_uzun(en_yeni)}) GERİDE — {ornek}. Kaynak seri ailelerini "
                f"aynı anda güncellemiyor; ölçüm ortak tarihe hizalandığı için "
                f"pano en geride kalan ailenin ayında kalır. Yayım günüyse "
                f"birkaç saat sonra yeniden koşturun.")

    _denet("tufe", "tufe", "TÜFE (TP.TUKFIY2025.GENEL)")
    _denet("tufe", "cekirdek_c", "Çekirdek C (TP.FE25.OKTG04)")
    _denet("tufe", "yi_ufe", "Yİ-ÜFE (TP.TUFE1YI.T1)")
    _denet("beklenti", "pka_12a", "PKA 12 ay beklentisi (TP.PKAUO.S01.E.U)")
    _denet("ykke", "ykke", "YKKE (TP.YKKE.TR)")
    _denet("ito", "ito_ist",
           "İTO İstanbul Tüketici Fiyat İndeksi, 2023=100 (TP.FG.IST1.23)")

    for ad, kod in FAIZ.items():
        if ad not in gunluk.columns or gunluk[ad].dropna().empty:
            uy.append(f"TAZELİK: faiz serisi '{ad}' ({kod}) yüklenemedi.")
            continue
        son = gunluk[ad].dropna().index[-1]
        gecikme = (bugun - son).days
        if gecikme > FAIZ_TAZELIK_GUN:
            uy.append(f"TAZELİK: '{ad}' ({kod}) son gözlemi {son:%d.%m.%Y} "
                      f"({gecikme} gün önce, tolerans {FAIZ_TAZELIK_GUN}). "
                      "İş günü yayını durmuş olabilir.")

    # Yapısal denetim 1: TP.FE25.OKTG01 ile TP.TUKFIY2025.GENEL BİREBİR aynı olmalı.
    if "oktg01" in aylik.columns and "tufe" in aylik.columns:
        ort = aylik[["tufe", "oktg01"]].dropna()
        if len(ort):
            fark = (ort["tufe"] - ort["oktg01"]).abs().max()
            if fark > 0.01:
                uy.append(
                    f"YAPISAL: TP.FE25.OKTG01 ile TP.TUKFIY2025.GENEL arasında "
                    f"{fark:.3f} puanlık sapma var; ikisi birebir aynı olmalıydı. "
                    "EVDS tarafında kopukluk olabilir.")

    # Yapısal denetim 2: PKA katılımcı sayısı düşerse anket zayıflıyordur.
    if "pka_12a_n" in aylik.columns:
        n = aylik["pka_12a_n"].dropna()
        if len(n) > 13:
            son_n, ort_n = n.iloc[-1], n.iloc[-13:-1].mean()
            if son_n < 0.75 * ort_n:
                uy.append(f"ANKET ZAYIFLADI: PKA katılımcı sayısı {son_n:.0f} "
                          f"(son 12 ay ortalaması {ort_n:.0f}). Beklenti serileri "
                          "daha gürültülü okunmalı.")
    return uy


_SON_AY: dict[str, str] = {}


def son_ay(aylik: pd.DataFrame | None = None) -> pd.Timestamp:
    """Analizin güncel ayı: TÜFE tabanlı ÇEKİRDEK serilerin TAMAMININ bulunduğu
    son ay. Sabit tarih YASAK. Bilinçli gecikmeli (YKKE, İTO) ve ileriden gelen
    (PKA) seriler sayılmaz."""
    if "t" in _SON_AY:
        return pd.Timestamp(_SON_AY["t"])
    if aylik is None:
        aylik = pd.read_csv(VERI / "aylik.csv", index_col=0, parse_dates=True)
    cekirdek = [c for c in ("tufe", "cekirdek_b", "cekirdek_c", "hizmet",
                            "temel_mal", "enerji", "gida") if c in aylik.columns]
    tam = aylik[cekirdek].dropna(how="any")
    if tam.empty:
        raise RuntimeError("son_ay: TÜFE serileri boş — EVDS çekimi düşmüş olabilir.")
    _SON_AY["t"] = tam.index[-1].strftime("%Y-%m-%d")
    return tam.index[-1]


# --------------------------------------------------------------------------- ana akış
YAYIM = VERI.parent / "tuik_yayim.json"


def _yayim_oku() -> dict:
    try:
        return json.loads(YAYIM.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _manset_kopru(aylik: pd.DataFrame, uy: list) -> tuple[pd.DataFrame, dict]:
    """EVDS manşet ailesini geç yayımladıysa TÜİK'in kendi oranıyla doldur.

    DOLGU DEĞİL DE BEKLEME NEDEN OLMUYOR: yayım günü, okurun sayfaya baktığı
    gündür. Panoyu o gün dünkü ayda tutmak, veriyi doğru ama sayfayı yanlış
    yapar. Dolgu üç kuralla güvenli kılınıyor:
      (1) Yalnız EVDS'in HENÜZ vermediği ay doldurulur; EVDS'in verdiği bir ay
          asla ezilmez.
      (2) Kaynak ve yöntem açıkça yazılır (durum dosyasına ve uyarıya).
      (3) EVDS geldiğinde iki sayı karşılaştırılır; ayrışırsa uyarı düşer.
    Ayrıca katkıların toplamı manşete eşit olmalı — bu bir KİMLİK denetimidir
    ve tutmazsa dolgu yapılmaz."""
    y = _yayim_oku()
    if not y:
        return aylik, {}
    kopru: dict = {}
    for ay_s, oran in (y.get("aylik") or {}).items():
        t = pd.Timestamp(ay_s + "-01")
        # KİMLİK: grup katkıları manşete toplanmalı.
        g = (y.get("gruplar") or {}).get(ay_s) or {}
        if g:
            top = sum(float(v.get("katki", 0)) for v in g.values())
            if abs(top - float(oran)) > 0.02:
                uy.append(
                    f"YAYIM KÖPRÜSÜ KURULMADI ({ay_s}): grup katkılarının "
                    f"toplamı {top:.2f}, manşet {oran:.2f} — kimlik tutmuyor.")
                continue
        s_ = aylik["tufe"].dropna() if "tufe" in aylik.columns else pd.Series(dtype=float)
        if not len(s_) or t in s_.index:
            continue                     # EVDS vermişse dokunma
        onceki = t - pd.DateOffset(months=1)
        if onceki not in s_.index:
            continue
        aylik.loc[t, "tufe"] = float(s_.loc[onceki]) * (1 + float(oran) / 100)
        kopru["tufe"] = ay_s
        for kod, blok in g.items():
            ad = f"ana_{kod}"
            if ad not in aylik.columns:
                continue
            sg = aylik[ad].dropna()
            if t in sg.index or onceki not in sg.index:
                continue
            aylik.loc[t, ad] = float(sg.loc[onceki]) * (
                1 + float(blok.get("aylik", 0)) / 100)
            kopru[ad] = ay_s
        # DOĞRULAMA: türetilen seviyeden hesaplanan yıllık ve yıl sonuna göre
        # oran, TÜİK'in yayımladığıyla tutmalı. Tutmuyorsa oran yanlış girilmiş
        # ya da seviye serisi bozuk demektir.
        m = ((y.get("mansetler") or {}).get(ay_s) or {})
        yeni = aylik["tufe"].dropna()
        for alan, ay_geri, etiket in (("yillik", 12, "yıllık"),):
            bek = m.get(alan)
            gecmis = t - pd.DateOffset(months=ay_geri)
            if bek is not None and gecmis in yeni.index:
                bizim = (float(yeni.loc[t]) / float(yeni.loc[gecmis]) - 1) * 100
                if abs(bizim - float(bek)) > 0.05:
                    uy.append(
                        f"YAYIM KÖPRÜSÜ SAPMASI ({ay_s}): türetilen {etiket} "
                        f"%{bizim:.2f}, TÜİK %{bek:.2f} — fark "
                        f"{abs(bizim - float(bek)):.2f} puan.")
        if kopru:
            uy.append(
                f"YAYIM KÖPRÜSÜ: {ay_s} manşet ailesi EVDS'te yok, TÜİK'in "
                f"yayımladığı oranlardan türetildi ({len(kopru)} seri). EVDS "
                f"yayımladığı an iki kaynak karşılaştırılır.")
    return aylik, kopru


def kos(yenile: bool = False) -> dict:
    print("EVDS3 → enflasyon veri katmanı")
    print(f"  anahtar: {'ortam değişkeni' if os.environ.get('TTO_EVDS_KEY') else 'dosya'}")

    kodlar: dict[str, str] = dict(ANA_SERI)
    kodlar.update({f"ana_{k}": f"TP.TUKFIY2025.{k}" for k in ANA_GRUP_AD})
    kodlar.update({f"oktg{k}": f"TP.FE25.OKTG{k}" for k in OKTG_AD})
    kodlar.update(BEKLENTI)

    print(f"  aylık seri: {len(kodlar)}")
    aylik = _panel(kodlar, yenile=yenile)

    print(f"  günlük seri: {len(FAIZ)}")
    gunluk_s: dict[str, pd.Series] = {}
    for ad, kod in FAIZ.items():
        try:
            gunluk_s[ad] = evds_gunluk(kod, yenile=yenile)
        except Exception as ex:
            uyar(f"SERİ ALINAMADI: {ad} ({kod}) — {ex}")
    gunluk = pd.DataFrame(gunluk_s).sort_index()
    gunluk.index.name = "tarih"

    # alt kalem ağacı (kırpılmış ortalama / difüzyon / katkı için)
    print("  TÜFE ağacı (bie_tukfiy2025 kataloğu)")
    agac = alt_kalem_kodlari(yenile=yenile)
    if not agac.empty:
        agac.to_csv(VERI / "agac.csv", index=False)
        print(f"    {len(agac)} seri · hane dağılımı "
              + ", ".join(f"{h}:{n}" for h, n in agac["hane"].value_counts().sort_index().items()))

    # ---- MANŞET KÖPRÜSÜ, son_ay()'DAN ÖNCE KOŞAR.
    # SIRA BAĞLAYICI: son_ay() çekirdek serilerin TAMAMININ bulunduğu son ayı
    # verir ve sonucu önbelleğe alır. Köprü ondan sonra koşarsa dosyaya ağustos
    # yazılır ama analizin "güncel ayı" temmuz kalır — pano yine dünkü ayı
    # gösterir ve hiçbir denetim bunu yakalamaz, çünkü iki sayı da kendi
    # içinde tutarlıdır. Dolgu, ayın kim olduğu sorulmadan ÖNCE yapılmalı.
    _kopru_uy: list[str] = []
    aylik, _kopru = _manset_kopru(aylik, _kopru_uy)
    for _u in _kopru_uy:
        uyar(_u)

    s_ay = son_ay(aylik)
    print(f"  SON AY: {ad_uzun(s_ay)}"
          + (f"  [manşet köprüsü: {len(_kopru)} seri]" if _kopru else ""))

    uy = tazelik_denetimi(aylik, gunluk)
    for u in uy:
        uyar(u)

    aylik.to_csv(VERI / "aylik.csv")
    gunluk.to_csv(VERI / "gunluk.csv")
    durum = {
        "kosum": dt.date.today().isoformat(),
        "son_ay": s_ay.strftime("%Y-%m-%d"),
        "aylik_seri": int(aylik.shape[1]),
        "gunluk_seri": int(gunluk.shape[1]),
        "aylik_gozlem": int(aylik.shape[0]),
        "uyarilar": list(_UYARI),
    }
    (VERI / "veri_durum.json").write_text(
        json.dumps(durum, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  yazıldı: data/aylik.csv ({aylik.shape[0]}x{aylik.shape[1]}), "
          f"data/gunluk.csv ({gunluk.shape[0]}x{gunluk.shape[1]})")
    if _UYARI:
        print(f"\n[{len(_UYARI)} uyarı]")
    return durum


if __name__ == "__main__":
    import sys
    # YAYIM GÜNÜ ÖNBELLEK BAYAT VERİYİ KİLİTLER. Seri önbelleği 12 saat taze
    # sayılıyor; TÜİK ise ayın 3'ünde 10.00'da yayımlıyor. Sabah 07.00'de
    # koşmuş bir tazeleme, yayımdan SONRA koşan bir tazelemeye eski dosyayı
    # verir ve hat "veri değişmedi" diyerek yeşil biter — yayım gününde
    # sayfada dünkü ay durur. Zorlanmış koşu bu yüzden önbelleği ATLAR:
    # elle tetiklenen bir tazelemenin tek sebebi zaten "yeni veri var".
    # Değişkenin adı ve doğru sayılan değerleri ortak/tazelik'te TEK yerde;
    # burada ikinci bir kopya tutmak, ikisinin bir gün sessizce ayrışması demek.
    zorla = "--yenile" in sys.argv or _tazelik().yenile_istendi()
    kos(yenile=zorla)
