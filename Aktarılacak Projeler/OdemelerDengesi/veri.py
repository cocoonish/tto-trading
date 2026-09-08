# -*- coding: utf-8 -*-
"""Ödemeler dengesi ve dış finansman — veri katmanı (EVDS3).

Ne yapar
--------
1. EVDS3 REST servisinden ödemeler dengesi ANALİTİK sunumunu,
   AYRINTILI sunumu, altın & enerji hariç cari işlemler
   tablosunu, TCMB'nin dış borç çevirme oranlarını
  , yurt dışı borçlanma senedi akımını, haftalık
   dış borç ödemelerini, GSYH'yi, USD/TRY kurunu
   ve rezerv STOKUNU çeker.
2. Her seriyi TTL'li önbelleğe (data/cache/*.csv) yazar. Çıktı CSV'leri HER
   koşuda yeniden yazılır — "dosya varsa atla" YASAK.
3. BİRİMİ EVDS meta verisinden OKUR (datagroups → BIRIMI) ve koddaki beklenen
   birimle karşılaştırır. Birim dizeleri normalize edilir: bie_dbafod "milyon
   ABD Doları", diğerleri "milyon ABD doları" yazıyor — büyük/küçük harf farkı
   normalize edilmezse otomatik dönüşüm bu farkı yakalayamaz.
4. `son_ay()` / `son_ceyrek()` / `son_hafta()` / `son_gun()` ile analizin
   dönemini VERİDEN okur (sabit tarih YASAK). Bu hatta DÖRT ayrı yayım ritmi
   var; tek dönem etiketi sessiz bayatlama üretir.
5. AİLE BAZLI tazelik denetimi: aylık ödemeler dengesi (~54 gün gecikme),
   üç aylık GSYH (~145 gün), haftalık dış borç ödemeleri (~5 gün), günlük kur
   (−1 gün). Tek eşik her koşuda yanlış alarm üretirdi. Tazelik serinin KENDİ
   son gözlemi ile DUVAR SAATİ farkından ölçülür; EVDS'in LAST_UPDATED alanı
   GÜVENİLMEZ (ölçüldü: bie_abreserv 2026-06 verisi taşırken meta verisi
   "12-12-2025" diyor).
6. Kimlik denetimleri (ödemeler dengesi kimliği, altın/enerji köprüsü, iki
   sunum arasındaki köprü, uzun vadeli kredi bacakları) ve rezerv akımının
   İŞARET sınaması (akım ↔ stok). Tutmazsa GÖRÜNÜR uyarı düşer.

Uç nokta notu
-------------
`evds2.tcmb.gov.tr/service/evds` ÖLÜ. Çalışan uç nokta:

    https://evds3.tcmb.gov.tr/igmevdsms-dis/{endpoint}{param}={deger}&...

Sorgu dizesi `?` ile başlamaz; anahtar URL'de DEĞİL `key:` HTTP başlığında
gider. Tek istek ~1000 SATIRLA sınırlı ve aralığın SONUNDAN geriye dolduruyor,
gerisini uyarı vermeden kırpıyor. Aylık (609 satır), üç aylık (125) ve haftalık
(712) seriler sınırın altında; GÜNLÜK kur serisi (19 bin gözlem) 366 günlük
parçalar hâlinde çekilir. Satır sınırı TARİH sayısına bağlıdır, seri sayısına
değil — bu yüzden seriler demet hâlinde (`series=A-B-C`) çekilir.

Koşum:  python3 veri.py  [--yenile]
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import sys
import time
import urllib.request

import pandas as pd


def _aylar() -> list[str]:
    """Okura yazılan ay adı — ortak sözleşmeden. Ay kodu ('05.2013') okurun
    elinde bir şey ifade etmez; adı ('Mayıs 2013') eder."""
    try:
        import bicim
    except ImportError:
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "ortak"))
        import bicim
    return bicim.AYLAR_TR

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
#   → <proje>/.evds_key → kök/.evds_key → kardeş TCMBNetRezerv/.evds_key
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
        + " / ".join(str(y) for y in _ADAYLAR))


BASE = "https://evds3.tcmb.gov.tr/igmevdsms-dis"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")

CACHE_TTL_SAAT = 12
DEMET = 6                 # tek istekte kaç seri (satır sınırı seri sayısına bağlı DEĞİL)
PARCA = {"ay": 30000, "ceyrek": 30000, "gun": 366, "hafta": 6300}

_UYARI: list[str] = []
_ANAHTAR: str | None = None


def uyar(mesaj: str) -> None:
    """Görünür uyarı: ekrana basılır ve veri_durum.json'a taşınır."""
    if mesaj not in _UYARI:
        _UYARI.append(mesaj)
    print("  ! " + mesaj, flush=True)


def uyarilar() -> list[str]:
    """Veri katmanının bu koşuda bastığı GÖRÜNÜR uyarılar.

    metrik.py bunu kendi listesine katar; katmadığında tazelik ve
    'ESKİ ÖNBELLEK' uyarıları uyarilar.json'a hiç girmez ve sayfada
    görünmez — düzenin yasakladığı sessiz bayatlamanın tam kendisi.
    """
    return list(_UYARI)


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
        except Exception as ex:            # ağ, zaman aşımı, 5xx…
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


# --------------------------------------------------------------------------- ayrıştırıcı
# DÖRT ayrı tarih biçimi var ve karıştırılırsa seri SESSİZCE boşalır:
#   GÜNLÜK / HAFTALIK(ÇARŞAMBA) → "19-08-2026"
#   AYLIK                       → "2026-6"     (ay BAŞINA çapalanır)
#   ÜÇ AYLIK                    → "2026-Q2"    ← int("Q2") tuzağı tam burada
def _ayristir(items, kolonlar: list[str], bicim: str) -> pd.DataFrame:
    if not items:
        return pd.DataFrame()
    df = pd.DataFrame(items)
    if "Tarih" not in df.columns:
        return pd.DataFrame()
    t = df["Tarih"].astype(str)
    if bicim in ("gun", "hafta"):
        idx = pd.to_datetime(t, format="%d-%m-%Y", errors="coerce")
    elif bicim == "ay":
        idx = pd.to_datetime(t, format="%Y-%m", errors="coerce")
    elif bicim == "ceyrek":
        # "2026-Q2" → çeyrek SONU tarihi. pandas Period bunu doğrudan anlar.
        idx = pd.PeriodIndex(t.str.replace("-", "", regex=False),
                             freq="Q").to_timestamp(how="end").normalize()
    else:
        raise ValueError(f"bilinmeyen biçim: {bicim}")
    out = {}
    for k in kolonlar:
        if k in df.columns:
            out[k] = pd.to_numeric(df[k].replace("", None), errors="coerce")
    if not out:
        return pd.DataFrame()
    d = pd.DataFrame(out)
    d.index = pd.Index(idx)
    return d[~d.index.isna()].sort_index()


def _url(kodlar: list[str], bas: pd.Timestamp, son: pd.Timestamp) -> str:
    return (f"{BASE}/series={'-'.join(kodlar)}"
            f"&startDate={bas:%d-%m-%Y}&endDate={son:%d-%m-%Y}&type=json")


def _demet_cek(kodlar: list[str], bas: pd.Timestamp, son: pd.Timestamp,
               parca_gun: int, bicim: str) -> pd.DataFrame:
    """Bir seri demetini tarih parçaları hâlinde çeker.

    Demetin tamamı düşerse (bir kod geçersizse EVDS bütün isteği reddediyor)
    tek tek denenir; böylece bir bozuk kod diğer beşini götürmez.
    """
    guvenli = [k.replace(".", "_") for k in kodlar]
    parcalar: list[pd.DataFrame] = []
    imlec = bas
    while imlec <= son:
        sonu = min(imlec + pd.Timedelta(days=parca_gun - 1), son)
        try:
            items = _cek(_url(kodlar, imlec, sonu)).get("items", [])
            # 1000 satır kırpma alarmı: dolu geldiyse aralığın BAŞI kesilmiş olabilir.
            if len(items) >= 1000:
                uyar(f"KIRPMA RİSKİ: {', '.join(kodlar)} {imlec:%Y}–{sonu:%Y} "
                     f"aralığında {len(items)} satır döndü (EVDS ~1000'de "
                     "kırpar ve aralığın SONUNDAN doldurur).")
            p = _ayristir(items, guvenli, bicim)
        except Exception as ex:
            uyar(f"demet düştü ({', '.join(kodlar)} · {imlec:%m.%Y}–{sonu:%m.%Y}: "
                 f"{ex}); seriler tek tek deneniyor.")
            tekler = []
            for k, g in zip(kodlar, guvenli):
                try:
                    it = _cek(_url([k], imlec, sonu)).get("items", [])
                    d = _ayristir(it, [g], bicim)
                    if len(d):
                        tekler.append(d)
                except Exception as ex2:
                    uyar(f"SERİ ALINAMADI: {k} ({imlec:%m.%Y}–{sonu:%m.%Y}) — {ex2}")
                time.sleep(0.2)
            p = pd.concat(tekler, axis=1) if tekler else pd.DataFrame()
        if len(p):
            parcalar.append(p)
        imlec = sonu + pd.Timedelta(days=1)
        time.sleep(0.15)
    if not parcalar:
        return pd.DataFrame()
    d = pd.concat(parcalar)
    return d[~d.index.duplicated(keep="last")].sort_index()


def _cache_yolu(kod: str, bicim: str) -> pathlib.Path:
    return CACHE / f"evds_{bicim}_{kod.replace('.', '_')}.csv"


def cek_kume(kodlar: dict[str, tuple[str, str, str]], bicim: str,
             yenile: bool = False, etiket: str = "") -> pd.DataFrame:
    """Bir seri kümesini (ad → (kod, grup, başlangıç)) çeker, tek DataFrame verir.

    Önbellek SERİ BAZINDA tutulur (demet değişince önbellek geçersizleşmesin).
    Ağ düşerse ve önbellek varsa GÖRÜNÜR uyarıyla eski önbelleğe düşülür —
    sessizce değil.
    """
    ad_kod = {ad: k for ad, (k, _g, _b) in kodlar.items()}
    parca_gun = PARCA[bicim]
    eksik = [ad for ad in kodlar
             if yenile or not _taze(_cache_yolu(ad_kod[ad], bicim), CACHE_TTL_SAAT)]
    if eksik:
        print(f"  {etiket}: {len(eksik)}/{len(kodlar)} seri EVDS'ten çekiliyor "
              f"({-(-len(eksik) // DEMET)} demet)")
        # Aynı başlangıç tarihini paylaşanları bir arada tut — parça sayısı düşer.
        eksik = sorted(eksik, key=lambda a: kodlar[a][2])
        bugun = pd.Timestamp.today().normalize()
        for i in range(0, len(eksik), DEMET):
            grup = eksik[i:i + DEMET]
            bas = min(pd.Timestamp(kodlar[a][2]) for a in grup)
            d = _demet_cek([ad_kod[a] for a in grup], bas, bugun, parca_gun, bicim)
            for a in grup:
                g = ad_kod[a].replace(".", "_")
                if g in d.columns and d[g].notna().any():
                    s = d[g].dropna()
                    s.name = ad_kod[a]
                    s.to_csv(_cache_yolu(ad_kod[a], bicim))
    out: dict[str, pd.Series] = {}
    for ad, (kod, _g, _b) in kodlar.items():
        yol = _cache_yolu(kod, bicim)
        if not yol.exists():
            uyar(f"SERİ YOK: {ad} ({kod}) — ne EVDS'ten geldi ne önbellekte var.")
            continue
        if not _taze(yol, CACHE_TTL_SAAT):
            uyar(f"ESKİ ÖNBELLEK: {ad} ({kod}) {_yas_gun(yol):.0f} gün eski — "
                 "EVDS'ten tazelenemedi, bu seri BAYAT olabilir.")
        s = pd.read_csv(yol, index_col=0, parse_dates=True).iloc[:, 0]
        out[ad] = s
    df = pd.DataFrame(out).sort_index()
    df.index.name = "tarih"
    return df


# ===========================================================================
# SERİ KÜMELERİ — ad: (EVDS kodu, veri grubu, EVDS'te yayımlanan başlangıç)
#
# BİRİM DENETİMİ. Bütün ödemeler dengesi serileri MİLYON USD; çevirme oranları
# YÜZDE (EVDS meta verisinde "Oran"); GSYH BİN TL; kur TL. Birimler koda
# gömülmez, `GRUP_BIRIM` üzerinden EVDS meta verisiyle KARŞILAŞTIRILIR
# (bkz. birim_denetimi). Farklı birimli serileri toplayan tek yer
# metrik.py'deki GSYH dönüşümüdür ve orada zincir yorumla belgelidir.
#
# ÖLÜ SERİ ≠ HER ZAMAN ÖLÜ (bu koşuda ÖLÇÜLDÜ ve keşif notu DÜZELTİLDİ).
# Keşif TP.ODANA6.Q21, Q35 ve Q36'yı "son 60 ayın tamamında 0" diye eledi.
# Q21 (diğer yatırım varlık — Merkez Bankası) gerçekten hatta alınmaz; Q20
# (diğer yatırım varlık toplamı) onu zaten içeriyor. Ama Q35 (IMF kredileri)
# ve Q36 (ödemeler dengesi finansmanı) BUGÜN sıfır, TARİHÇEDE değil: 1984-12 →
# 2013-05 arasında 147 ayda sıfırdan farklılar (IMF programı yılları) ve
# rezerv kimliği ancak onlarla kapanıyor:
#     Q33 (rezerv varlıklar) = Q34 (resmi rezervler) + Q35 + Q36   → maks sapma 0,00
#     Q204 (ayrıntılı sunum rezerv) = Q34, Q33 DEĞİL               → maks sapma 0,00
# Yani "Q33 = Q204" eşitliği yalnız IMF bacakları sıfırken (2013-06'dan beri)
# doğrudur; tam tarihçede Mayıs 2001'de 3.809 mn USD ayrışıyorlar. İkisi
# TANI amaçlı çekilir — metriğe ve grafiğe girmezler.
# ===========================================================================
_ODANA = "bie_odana6"
_AYR = "bie_odeayrsunum6"
_HC = "bie_hariccariacik"
_ROLL = "bie_oderoll"
_EBS = "bie_odeydiebs"
_DBAFOD = "bie_dbafod"
_GSYH = "bie_gsyhhrccar"
_KUR = "bie_dkdovytl"
_REZ = "bie_abreserv"

# EVDS veri grubu meta verisinden OKUNAN birim (normalize edilmiş hâliyle
# beklenen değer). Meta veri bundan saparsa tanım/birim değişmiş demektir.
GRUP_BIRIM = {
    _ODANA: "milyon abd dolari",
    _AYR: "milyon abd dolari",
    _HC: "milyon abd dolari",
    _ROLL: "oran",
    _EBS: "milyon abd dolari",
    _DBAFOD: "milyon abd dolari",
    _GSYH: "bin tl",
    _KUR: "turk lirasi",
    _REZ: "milyon abd dolari",
}

# --- AYLIK (milyon USD; ODEROLL yüzde) -------------------------------------
AYLIK: dict[str, tuple[str, str, str]] = {
    # Cari işlemler — analitik sunum
    "cari":            ("TP.ODANA6.Q01", _ODANA, "1975-12-01"),
    "ihracat":         ("TP.ODANA6.Q02", _ODANA, "1975-12-01"),
    "ithalat":         ("TP.ODANA6.Q03", _ODANA, "1975-12-01"),
    "mal_denge":       ("TP.ODANA6.Q04", _ODANA, "1975-12-01"),
    "hizmet_gelir":    ("TP.ODANA6.Q05", _ODANA, "1975-12-01"),
    "hizmet_gider":    ("TP.ODANA6.Q06", _ODANA, "1975-12-01"),
    "mal_hizmet":      ("TP.ODANA6.Q07", _ODANA, "1975-12-01"),
    "birincil_gelir":  ("TP.ODANA6.Q08", _ODANA, "1975-12-01"),
    "birincil_gider":  ("TP.ODANA6.Q09", _ODANA, "1975-12-01"),
    "mhb_denge":       ("TP.ODANA6.Q10", _ODANA, "1975-12-01"),
    "ikincil_denge":   ("TP.ODANA6.Q11", _ODANA, "1975-12-01"),
    "sermaye_hesabi":  ("TP.ODANA6.Q12", _ODANA, "1975-12-01"),
    # Finans hesabı — analitik sunum, REZERV HARİÇ (hattın en pahalı tuzağı)
    "fin_hesabi":      ("TP.ODANA6.Q13", _ODANA, "1975-12-01"),
    "dyy_varlik":      ("TP.ODANA6.Q14", _ODANA, "1975-12-01"),
    "dyy_yuk":         ("TP.ODANA6.Q15", _ODANA, "1975-12-01"),
    "port_varlik":     ("TP.ODANA6.Q16", _ODANA, "1975-12-01"),
    "port_yuk":        ("TP.ODANA6.Q17", _ODANA, "1975-12-01"),
    "port_yuk_hisse":  ("TP.ODANA6.Q18", _ODANA, "1975-12-01"),
    "port_yuk_borc":   ("TP.ODANA6.Q19", _ODANA, "1975-12-01"),
    "turev_varlik":    ("TP.ODANA6.Q37", _ODANA, "2014-01-01"),
    "turev_yuk":       ("TP.ODANA6.Q38", _ODANA, "2014-01-01"),
    "diger_varlik":    ("TP.ODANA6.Q20", _ODANA, "1975-12-01"),
    "diger_varlik_gh": ("TP.ODANA6.Q22", _ODANA, "1975-12-01"),
    "diger_varlik_bnk": ("TP.ODANA6.Q23", _ODANA, "1975-12-01"),
    "diger_varlik_dgr": ("TP.ODANA6.Q24", _ODANA, "1975-12-01"),
    "diger_yuk":       ("TP.ODANA6.Q25", _ODANA, "1975-12-01"),
    "diger_yuk_tcmb":  ("TP.ODANA6.Q26", _ODANA, "1975-12-01"),
    "diger_yuk_gh":    ("TP.ODANA6.Q27", _ODANA, "1975-12-01"),
    "diger_yuk_bnk":   ("TP.ODANA6.Q28", _ODANA, "1975-12-01"),
    "diger_yuk_dgr":   ("TP.ODANA6.Q29", _ODANA, "1975-12-01"),
    "csf_toplam":      ("TP.ODANA6.Q30", _ODANA, "1975-12-01"),
    "nhn":             ("TP.ODANA6.Q31", _ODANA, "1975-12-01"),
    "genel_denge":     ("TP.ODANA6.Q32", _ODANA, "1975-12-01"),
    "rezerv_akim":     ("TP.ODANA6.Q33", _ODANA, "1975-12-01"),
    "resmi_rezerv":    ("TP.ODANA6.Q34", _ODANA, "1975-12-01"),
    # TANI amaçlı (metriğe/grafiğe girmez): rezerv kimliğini kapatan iki bacak.
    "imf_kredileri":   ("TP.ODANA6.Q35", _ODANA, "1975-12-01"),
    "od_finansmani":   ("TP.ODANA6.Q36", _ODANA, "1975-12-01"),
    # Altın & enerji hariç cari işlemler (TCMB'nin çekirdek tanımı)
    "hc_cari":         ("TP.HARICCARIACIK.K1",  _HC, "1996-01-01"),
    "hc_altin_ihr":    ("TP.HARICCARIACIK.K2",  _HC, "1996-01-01"),
    "hc_altin_ith":    ("TP.HARICCARIACIK.K3",  _HC, "1996-01-01"),
    "hc_altin_net":    ("TP.HARICCARIACIK.K4",  _HC, "1996-01-01"),
    "hc_enerji_ihr":   ("TP.HARICCARIACIK.K5",  _HC, "1996-01-01"),
    "hc_enerji_ith":   ("TP.HARICCARIACIK.K6",  _HC, "1996-01-01"),
    "hc_enerji_net":   ("TP.HARICCARIACIK.K7",  _HC, "1996-01-01"),
    "hc_altin_haric":  ("TP.HARICCARIACIK.K8",  _HC, "1996-01-01"),
    "hc_enerji_haric": ("TP.HARICCARIACIK.K9",  _HC, "1996-01-01"),
    "hc_cekirdek":     ("TP.HARICCARIACIK.K10", _HC, "1996-01-01"),
    # Ayrıntılı sunum — finans hesabı REZERV DAHİL; köprü Q101 = Q13 + Q33
    "ay_cari":         ("TP.ODEAYRSUNUM6.Q1",   _AYR, "1984-12-01"),
    "ay_sermaye":      ("TP.ODEAYRSUNUM6.Q99",  _AYR, "1984-12-01"),
    "ay_fin_hesabi":   ("TP.ODEAYRSUNUM6.Q101", _AYR, "1984-12-01"),
    "ay_dyy_net":      ("TP.ODEAYRSUNUM6.Q102", _AYR, "1984-12-01"),
    "ay_dyy_varlik":   ("TP.ODEAYRSUNUM6.Q103", _AYR, "1984-12-01"),
    "ay_dyy_yuk":      ("TP.ODEAYRSUNUM6.Q108", _AYR, "1984-12-01"),
    "ay_port_net":     ("TP.ODEAYRSUNUM6.Q114", _AYR, "1984-12-01"),
    "ay_port_yuk":     ("TP.ODEAYRSUNUM6.Q119", _AYR, "1984-12-01"),
    "ay_turev_net":    ("TP.ODEAYRSUNUM6.Q214", _AYR, "2014-01-01"),
    "ay_diger_net":    ("TP.ODEAYRSUNUM6.Q136", _AYR, "1984-12-01"),
    "ay_mevduat_net":  ("TP.ODEAYRSUNUM6.Q137", _AYR, "1984-12-01"),
    "ay_mevduat_yuk":  ("TP.ODEAYRSUNUM6.Q143", _AYR, "1984-12-01"),
    "ay_mevduat_yuk_bnk": ("TP.ODEAYRSUNUM6.Q147", _AYR, "1984-12-01"),
    "ay_kredi_net":    ("TP.ODEAYRSUNUM6.Q152", _AYR, "1984-12-01"),
    "ay_kredi_yuk":    ("TP.ODEAYRSUNUM6.Q157", _AYR, "1984-12-01"),
    "ay_kredi_bnk":    ("TP.ODEAYRSUNUM6.Q166", _AYR, "1984-12-01"),
    "ay_kredi_bnk_kv": ("TP.ODEAYRSUNUM6.Q167", _AYR, "1984-12-01"),
    "ay_kredi_bnk_uv": ("TP.ODEAYRSUNUM6.Q168", _AYR, "1984-12-01"),
    "ay_kredi_bnk_uv_kul": ("TP.ODEAYRSUNUM6.Q169", _AYR, "1984-12-01"),
    "ay_kredi_bnk_uv_ode": ("TP.ODEAYRSUNUM6.Q170", _AYR, "1984-12-01"),
    "ay_kredi_dgr":    ("TP.ODEAYRSUNUM6.Q179", _AYR, "1984-12-01"),
    "ay_kredi_dgr_kv": ("TP.ODEAYRSUNUM6.Q180", _AYR, "1984-12-01"),
    "ay_kredi_dgr_uv": ("TP.ODEAYRSUNUM6.Q181", _AYR, "1984-12-01"),
    "ay_kredi_dgr_uv_kul": ("TP.ODEAYRSUNUM6.Q182", _AYR, "1984-12-01"),
    "ay_kredi_dgr_uv_ode": ("TP.ODEAYRSUNUM6.Q183", _AYR, "1984-12-01"),
    "ay_kredi_gh_uv":  ("TP.ODEAYRSUNUM6.Q176", _AYR, "1984-12-01"),
    "ay_kredi_gh_uv_kul": ("TP.ODEAYRSUNUM6.Q177", _AYR, "1984-12-01"),
    "ay_kredi_gh_uv_ode": ("TP.ODEAYRSUNUM6.Q178", _AYR, "1984-12-01"),
    "ay_ticari_kredi": ("TP.ODEAYRSUNUM6.Q184", _AYR, "1984-12-01"),
    "ay_sdr":          ("TP.ODEAYRSUNUM6.Q203", _AYR, "1984-12-01"),
    "ay_rezerv":       ("TP.ODEAYRSUNUM6.Q204", _AYR, "1984-12-01"),
    "ay_nhn":          ("TP.ODEAYRSUNUM6.Q210", _AYR, "1984-12-01"),
    # TCMB'nin kendi çevirme oranları — YÜZDE, kapsam kısa+uzun vade
    "roll_bnk":        ("TP.ODEROLL.K1", _ROLL, "2006-06-01"),
    "roll_dgr":        ("TP.ODEROLL.K2", _ROLL, "2006-06-01"),
    "roll_bnk_tahvil": ("TP.ODEROLL.K3", _ROLL, "2006-06-01"),
    "roll_dgr_tahvil": ("TP.ODEROLL.K4", _ROLL, "2006-06-01"),
    # Yurt dışı borçlanma senedi (eurobond) akımı — SEYREK alt kırılımlar
    "eb_kullanim":     ("TP.ODEYDIEBS.A1",   _EBS, "2010-01-01"),
    "eb_kullanim_uv":  ("TP.ODEYDIEBS.A11",  _EBS, "2010-01-01"),
    "eb_kullanim_gh":  ("TP.ODEYDIEBS.A112", _EBS, "2010-01-01"),
    "eb_kullanim_bnk": ("TP.ODEYDIEBS.A113", _EBS, "2010-01-01"),
    "eb_kullanim_dgr": ("TP.ODEYDIEBS.A114", _EBS, "2010-01-01"),
    "eb_odeme":        ("TP.ODEYDIEBS.A2",   _EBS, "2010-01-01"),
    "eb_odeme_uv":     ("TP.ODEYDIEBS.A21",  _EBS, "2010-01-01"),
    # Rezerv STOKU — yalnız rezerv AKIMININ işaret yönünü sınamak için
    "rezerv_stok":     ("TP.AB.B4", _REZ, "1981-01-01"),
}

# --- HAFTALIK (ÇARŞAMBA) — hattın EN TAZE serisi ---------------------------
HAFTALIK: dict[str, tuple[str, str, str]] = {
    "borc_odeme_top":  ("TP.D1TOP",  _DBAFOD, "2012-12-26"),
    "borc_odeme_haz":  ("TP.D2HAZ",  _DBAFOD, "2012-12-26"),
    "borc_odeme_dgr":  ("TP.D3DIG",  _DBAFOD, "2012-12-26"),
    "borc_odeme_tcmb": ("TP.D4TCMB", _DBAFOD, "2012-12-26"),
}

# --- ÜÇ AYLIK --------------------------------------------------------------
CEYREK: dict[str, tuple[str, str, str]] = {
    # BİN TL ve ÜÇ AYLIK. Ödemeler dengesi MİLYON USD ve AYLIK — dönüşüm
    # zinciri metrik.py'de TEK yerde, yorumla belgeli.
    "gsyh_bin_tl": ("TP.GSYIH20.BY.B1GQ", _GSYH, "1995-01-01"),
}

# --- GÜNLÜK ----------------------------------------------------------------
GUNLUK: dict[str, tuple[str, str, str]] = {
    # GSYH'yi USD'ye çevirmek için ÇEYREK ORTALAMASI alınır. Nokta kur (çeyrek
    # sonu) akım büyüklüğünü çeyrek içi kur hareketi kadar yanıltır.
    # 1994-12 başlangıcı bilinçli: GSYH 1995-Ç1'de başlıyor, ilk çeyreğin
    # ortalaması için o çeyreğin tamamı gerekiyor.
    "usdtry": ("TP.DK.USD.A.YTL", _KUR, "1994-12-01"),
}

# --------------------------------------------------------------------------- tazelik
# (etiket, tolerans TAKVİM GÜNÜ, negatif gecikme muaf mı)
#
# Referans DUVAR SAATİDİR ve ölçüm serinin kendi DÖNEM SONUNDAN yapılır (aylık
# seride ay sonu, üç aylıkta çeyrek sonu). EVDS'in LAST_UPDATED alanı
# GÜVENİLMEZ — ölçüldü: bie_abreserv 2026-06 verisi taşırken meta verisi
# "12-12-2025" diyor, bie_odana6 için "05-03-2026".
#
# Toleranslar yayım ritminden TÜRETİLDİ:
#   · Ödemeler dengesi: M ayı verisi ≈ M+11 (yani M sonundan ~42 gün sonra)
#     yayımlanır; bir sonraki yayına kadar en taze dönem sonu ~73 gün geride
#     kalır. 85 gün, normal ritimde yanlış alarm üretmeyen en sıkı eşiktir.
#   · GSYH: Ç çeyreği ≈ Ç sonundan 62 gün sonra; sonraki yayına kadar en taze
#     çeyrek sonu ~153 gün geride kalır → 165 gün.
#   · Haftalık dış borç ödemeleri: çarşamba yayını, ~5 gün → 12 gün.
#   · Kur: TCMB ertesi günün kurunu bir gün ÖNCE ilan eder → negatif gecikme
#     alarm sayılmaz.
TAZELIK_AYLIK = {
    "cari":        ("Ödemeler dengesi — analitik sunum", 85, False),
    "ay_cari":     ("Ödemeler dengesi — ayrıntılı sunum", 85, False),
    "hc_cekirdek": ("Altın & enerji hariç cari", 85, False),
    "roll_bnk":    ("Dış borç çevirme oranları", 85, False),
    "eb_kullanim": ("Yurt dışı borçlanma senedi akımı", 85, False),
    "rezerv_stok": ("Rezerv stoku", 85, False),
}
TAZELIK_HAFTALIK = {
    "borc_odeme_top": ("Haftalık dış borç ödemeleri", 12, False),
}
TAZELIK_CEYREK = {
    "gsyh_bin_tl": ("GSYH, cari fiyatlarla", 165, False),
}
TAZELIK_GUNLUK = {
    "usdtry": ("USD/TRY kuru", 5, True),
}


def tazelik_tolerans(aile: str = "aylik") -> int:
    """Bu ailedeki EN SIKI tolerans (takvim günü).

    ozet_uret.py bayat bayrağını buradan okur; eşik iki yerde ayrı ayrı
    yazılırsa biri güncellenip öteki unutulur ve bayatlık sessizce kaçar.
    """
    tablo = {"aylik": TAZELIK_AYLIK, "haftalik": TAZELIK_HAFTALIK,
             "ceyrek": TAZELIK_CEYREK, "gunluk": TAZELIK_GUNLUK}[aile]
    return min(t for _, t, _ in tablo.values())


AY_TR = {1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
         7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım",
         12: "Aralık"}
AY_KISA = {1: "Oca", 2: "Şub", 3: "Mar", 4: "Nis", 5: "May", 6: "Haz",
           7: "Tem", 8: "Ağu", 9: "Eyl", 10: "Eki", 11: "Kas", 12: "Ara"}


def gun_ad(t) -> str:
    t = pd.Timestamp(t)
    return f"{t.day} {AY_TR[t.month]} {t.year}"


def ay_ad(t) -> str:
    """Aylık dönem adı. Aylık seri AY BAŞINA çapalıdır; okur için ay adı yazılır."""
    t = pd.Timestamp(t)
    return f"{AY_TR[t.month]} {t.year}"


def ceyrek_ad(t) -> str:
    t = pd.Timestamp(t)
    return f"{t.year}-Ç{(t.month - 1) // 3 + 1}"


def kisa_ad(t) -> str:
    t = pd.Timestamp(t)
    return f"{AY_KISA[t.month]}-{str(t.year)[2:]}"


def donem_sonu(t, bicim: str) -> pd.Timestamp:
    """Gözlemin kapsadığı dönemin SON günü.

    Aylık seri ay BAŞINA çapalı geliyor; tazeliği ay başından ölçmek her ay
    30 güne kadar yanlış alarm üretir. Üç aylık seri zaten çeyrek sonuna
    çapalı (ayrıştırıcıda `how='end'`).
    """
    t = pd.Timestamp(t)
    if bicim == "ay":
        return t + pd.offsets.MonthEnd(0)
    if bicim == "ceyrek":
        return t + pd.offsets.QuarterEnd(0)
    return t


# --------------------------------------------------------------------------- dönem
_SON: dict[str, str] = {}


def _son_dolu(df: pd.DataFrame, cekirdek: list[str], ad: str) -> pd.Timestamp:
    var = [c for c in cekirdek if c in df.columns]
    if not var:
        raise RuntimeError(f"{ad}: çekirdek seriler yok — EVDS çekimi düşmüş olabilir.")
    tam = df[var].dropna(how="any")
    if tam.empty:
        raise RuntimeError(f"{ad}: çekirdek seriler boş.")
    return tam.index[-1]


def son_ay(aylik: pd.DataFrame | None = None) -> pd.Timestamp:
    """Ödemeler dengesinin son dolu AYI (ay başına çapalı).

    Çekirdek: manşet cari denge + finans hesabı + çekirdek cari. Rezerv stoku
    ve çevirme oranları bilinçli DIŞARIDA — biri geride kalırsa dönem sessizce
    bir ay geriye düşerdi.
    """
    if "ay" in _SON:
        return pd.Timestamp(_SON["ay"])
    if aylik is None:
        aylik = pd.read_csv(VERI / "aylik.csv", index_col=0, parse_dates=True)
    t = _son_dolu(aylik, ["cari", "fin_hesabi", "hc_cekirdek", "nhn"], "son_ay")
    _SON["ay"] = t.strftime("%Y-%m-%d")
    return t


def son_ceyrek(ceyrek: pd.DataFrame | None = None) -> pd.Timestamp:
    if "ceyrek" in _SON:
        return pd.Timestamp(_SON["ceyrek"])
    if ceyrek is None:
        ceyrek = pd.read_csv(VERI / "ceyreklik.csv", index_col=0, parse_dates=True)
    t = _son_dolu(ceyrek, ["gsyh_bin_tl"], "son_ceyrek")
    _SON["ceyrek"] = t.strftime("%Y-%m-%d")
    return t


def son_hafta(haftalik: pd.DataFrame | None = None) -> pd.Timestamp:
    if "hafta" in _SON:
        return pd.Timestamp(_SON["hafta"])
    if haftalik is None:
        haftalik = pd.read_csv(VERI / "haftalik.csv", index_col=0, parse_dates=True)
    t = _son_dolu(haftalik, ["borc_odeme_top"], "son_hafta")
    _SON["hafta"] = t.strftime("%Y-%m-%d")
    return t


def son_gun(gunluk: pd.DataFrame | None = None) -> pd.Timestamp:
    if "gun" in _SON:
        return pd.Timestamp(_SON["gun"])
    if gunluk is None:
        gunluk = pd.read_csv(VERI / "gunluk.csv", index_col=0, parse_dates=True)
    t = _son_dolu(gunluk, ["usdtry"], "son_gun")
    _SON["gun"] = t.strftime("%Y-%m-%d")
    return t


# --------------------------------------------------------------------------- birim
def _normalize_birim(s: str) -> str:
    """Birim dizesini karşılaştırılabilir hâle getirir.

    ÖLÇÜLDÜ: bie_dbafod "milyon ABD Doları", diğer gruplar "milyon ABD doları"
    yazıyor. Büyük/küçük harf ve Türkçe karakter farkı normalize edilmezse
    birim dizesine göre otomatik dönüşüm yapan kod bu farkı YAKALAYAMAZ.
    """
    t = (s or "").strip().lower()
    for a, b in (("ı", "i"), ("İ", "i"), ("ş", "s"), ("ğ", "g"), ("ü", "u"),
                 ("ö", "o"), ("ç", "c")):
        t = t.replace(a, b)
    return " ".join(t.split())


def birim_denetimi(yenile: bool = False) -> tuple[dict, list[str]]:
    """Birimi EVDS meta verisinden OKUR ve beklenenle karşılaştırır.

    Bu denetim bir "1000× hata" sigortasıdır: bir veri grubunun birimi
    değişirse (ör. bin TL → milyon TL) hesap sessizce bin kat kayar. Ağ
    düşerse önbellekten okunur; hiç okunamazsa GÖRÜNÜR uyarı düşer ama hat
    durmaz (birim değişikliği ihtimali, veri hiç olmamasından iyidir).
    """
    yol = VERI / "gruplar.json"
    ham: dict = {}
    if not yenile and _taze(yol, 24 * 7):
        try:
            ham = json.loads(yol.read_text(encoding="utf-8"))
        except Exception:
            ham = {}
    if not ham:
        try:
            tum = _cek(f"{BASE}/datagroups/mode=0&type=json")
            ham = {g["DATAGROUP_CODE"]: g for g in tum
                   if g.get("DATAGROUP_CODE") in GRUP_BIRIM}
            yol.write_text(json.dumps(ham, ensure_ascii=False, indent=1),
                           encoding="utf-8")
        except Exception as ex:
            uyar(f"BİRİM META VERİSİ ALINAMADI ({ex}) — birim denetimi bu "
                 "koşuda YAPILAMADI. Bir grubun birimi değişmişse hesap "
                 "sessizce kayar.")
            return {}, []
    rapor, uy = {}, []
    for grup, beklenen in GRUP_BIRIM.items():
        g = ham.get(grup) or {}
        okunan = g.get("BIRIMI", "")
        n_okunan = _normalize_birim(okunan)
        gecti = (n_okunan == beklenen)
        rapor[grup] = {
            "ad": g.get("DATAGROUP_NAME", ""),
            "birim_meta": okunan,
            "birim_normal": n_okunan,
            "birim_beklenen": beklenen,
            "frekans": g.get("FREQUENCY_STR", ""),
            "gecti": bool(gecti),
        }
        if not gecti:
            uy.append(
                f"BİRİM DEĞİŞMİŞ OLABİLİR: {grup} meta verisinde birim "
                f"'{okunan}' (normalize: '{n_okunan}'), beklenen "
                f"'{beklenen}'. Dönüşüm zinciri gözden geçirilmeden hesap "
                "GÜVENİLMEZ.")
    return rapor, uy


# --------------------------------------------------------------------------- denetimler
def tazelik_denetimi(a: pd.DataFrame, h: pd.DataFrame, c: pd.DataFrame,
                     g: pd.DataFrame) -> list[str]:
    bugun = pd.Timestamp.today().normalize()
    uy: list[str] = []
    for df, tablo, bicim, aile in ((a, TAZELIK_AYLIK, "ay", "aylık"),
                                   (h, TAZELIK_HAFTALIK, "hafta", "haftalık"),
                                   (c, TAZELIK_CEYREK, "ceyrek", "üç aylık"),
                                   (g, TAZELIK_GUNLUK, "gun", "günlük")):
        for ad, (etiket, tol, negatif_muaf) in tablo.items():
            if ad not in df.columns or df[ad].dropna().empty:
                uy.append(f"TAZELİK: '{etiket}' hiç yüklenemedi.")
                continue
            son = df[ad].dropna().index[-1]
            gecikme = (bugun - donem_sonu(son, bicim)).days
            if gecikme < 0 and negatif_muaf:
                continue      # kur: ertesi günün kuru bugünden ilan edilir
            if gecikme > tol:
                uy.append(
                    f"TAZELİK: {etiket} son dönemi {donem_sonu(son, bicim):%d.%m.%Y} "
                    f"({gecikme} gün önce, {aile} tolerans {tol} gün). "
                    "Yayın durmuş olabilir.")
    return uy


def kimlik_denetimi(a: pd.DataFrame) -> tuple[list[str], dict]:
    """Formül/kimlik denetimleri (tazelik DEĞİL).

    Ödemeler dengesi milyon USD ve TAM SAYIYA yuvarlı yayımlanıyor; eşikler
    MUTLAK (mn USD) tutulur, bağıl değil — payda sıfıra yaklaştığında bağıl
    eşik patlıyor (bu hattın oran patlaması riskiyle aynı sebep).

    Sınananlar:
      (1) Ödemeler dengesi kimliği: CA + KA + NHN = FA(rezerv hariç) + Rezerv.
      (2) İKİ SUNUM KÖPRÜSÜ: Q101 (rezerv DAHİL) = Q13 (rezerv HARİÇ) + Q33.
      (3) Ayrıntılı sunum: Q1 + Q99 + Q210 = Q101.
      (4) Aynı büyüklüğün iki koddaki eşitliği: Q01=Q1, Q31=Q210, Q33=Q204=Q34.
      (5) Cari denge ayrışması: Q01 = Q04 + (Q05−Q06) + (Q08−Q09) + Q11.
      (6) Altın/enerji köprüsü: K10 = K1 − K4 − K7; K4 = K2−K3; K7 = K5−K6.
      (7) Finans hesabı = Σ(varlık − yükümlülük), rezerv HARİÇ.
      (8) Uzun vadeli kredi bacakları: net = kullanım − geri ödeme (3 sektör).
    """
    uy: list[str] = []
    rapor: dict = {}

    def _k(ad: str, sol: pd.Series, sag: pd.Series, esik: float,
           birim: str = "mn USD"):
        d = pd.DataFrame({"s": sol, "r": sag}).dropna()
        if d.empty:
            uy.append(f"KİMLİK: '{ad}' sınanamadı — girdi serileri kesişmiyor.")
            return
        fark = (d["s"] - d["r"]).abs()
        rapor[ad] = {
            "n": int(len(d)),
            "maks_fark": float(fark.max()),
            "maks_tarih": str(fark.idxmax().date()),
            "son_fark": float(fark.iloc[-1]),
            "birim": birim, "esik": esik,
            "gecti": bool(fark.max() <= esik),
        }
        if fark.max() > esik:
            uy.append(
                f"KİMLİK BOZUK: {ad} — en büyük sapma {fark.max():,.2f} {birim} "
                f"({fark.idxmax():%m.%Y}); eşik {esik} {birim}. Kalem "
                "numaralandırması ya da tanım değişmiş olabilir.")

    k = set(a.columns)
    if {"cari", "sermaye_hesabi", "nhn", "fin_hesabi", "rezerv_akim"} <= k:
        _k("CA + KA + NHN = FA(rezerv hariç) + Rezerv",
           a["cari"] + a["sermaye_hesabi"] + a["nhn"],
           a["fin_hesabi"] + a["rezerv_akim"], 5.0)
    if {"ay_fin_hesabi", "fin_hesabi", "rezerv_akim"} <= k:
        # HATTIN EN PAHALI TUZAĞI. İki sunumun "finans hesabı" kalemi AYNI
        # DEĞİL: analitik Q13 rezervi İÇERMEZ, ayrıntılı Q101 içerir.
        _k("köprü: Q101(rezerv dahil) = Q13(rezerv hariç) + Q33",
           a["ay_fin_hesabi"], a["fin_hesabi"] + a["rezerv_akim"], 5.0)
    if {"ay_cari", "ay_sermaye", "ay_nhn", "ay_fin_hesabi"} <= k:
        _k("ayrıntılı: Q1 + Q99 + Q210 = Q101",
           a["ay_cari"] + a["ay_sermaye"] + a["ay_nhn"], a["ay_fin_hesabi"], 5.0)
    if {"cari", "ay_cari"} <= k:
        _k("Q01 = Q1 (analitik ↔ ayrıntılı cari)", a["cari"], a["ay_cari"], 1.0)
    if {"cari", "hc_cari"} <= k:
        _k("Q01 = HARICCARIACIK.K1", a["cari"], a["hc_cari"], 1.0)
    if {"nhn", "ay_nhn"} <= k:
        _k("Q31 = Q210 (net hata noksan)", a["nhn"], a["ay_nhn"], 1.0)
    if {"rezerv_akim", "resmi_rezerv", "imf_kredileri", "od_finansmani"} <= k:
        # DOĞRU KİMLİK BU. "Q33 = Q34" tam tarihçede TUTMAZ (Mayıs 2001'de
        # 3.809 mn USD ayrışır): analitik sunumda rezerv varlıklar kalemi IMF
        # kredilerini ve ödemeler dengesi finansmanını da taşır.
        _k("Q33 = Q34 + Q35 + Q36 (rezerv varlıklar kimliği)", a["rezerv_akim"],
           a["resmi_rezerv"] + a["imf_kredileri"] + a["od_finansmani"], 1.0)
    if {"ay_rezerv", "resmi_rezerv"} <= k:
        # Ayrıntılı sunumun rezerv kalemi Q34'e eşittir, Q33'e DEĞİL. İkisi
        # ancak IMF bacakları sıfırken (2013-06'dan beri) çakışır.
        _k("Q204 = Q34 (ayrıntılı sunum rezerv kalemi)",
           a["ay_rezerv"], a["resmi_rezerv"], 1.0)
    if {"cari", "mal_denge", "hizmet_gelir", "hizmet_gider", "birincil_gelir",
            "birincil_gider", "ikincil_denge"} <= k:
        _k("Q01 = Q04 + (Q05−Q06) + (Q08−Q09) + Q11", a["cari"],
           a["mal_denge"] + (a["hizmet_gelir"] - a["hizmet_gider"])
           + (a["birincil_gelir"] - a["birincil_gider"]) + a["ikincil_denge"], 2.0)
    if {"hc_cekirdek", "hc_cari", "hc_altin_net", "hc_enerji_net"} <= k:
        _k("K10 = K1 − K4 − K7 (çekirdek cari köprüsü)", a["hc_cekirdek"],
           a["hc_cari"] - a["hc_altin_net"] - a["hc_enerji_net"], 1.0)
    if {"hc_altin_net", "hc_altin_ihr", "hc_altin_ith"} <= k:
        _k("K4 = K2 − K3 (altın net)", a["hc_altin_net"],
           a["hc_altin_ihr"] - a["hc_altin_ith"], 1.0)
    if {"hc_enerji_net", "hc_enerji_ihr", "hc_enerji_ith"} <= k:
        _k("K7 = K5 − K6 (enerji net)", a["hc_enerji_net"],
           a["hc_enerji_ihr"] - a["hc_enerji_ith"], 1.0)
    if {"fin_hesabi", "dyy_varlik", "dyy_yuk", "port_varlik", "port_yuk",
            "turev_varlik", "turev_yuk", "diger_varlik", "diger_yuk"} <= k:
        # BPM6: finans hesabı = net varlık edinimi − net yükümlülük oluşumu.
        # Türevler 2014-01'de başlıyor; öncesi NaN olduğu için kesişim 2014'ten.
        _k("Q13 = Σ(varlık − yükümlülük), rezerv HARİÇ", a["fin_hesabi"],
           (a["dyy_varlik"] - a["dyy_yuk"]) + (a["port_varlik"] - a["port_yuk"])
           + (a["turev_varlik"] - a["turev_yuk"])
           + (a["diger_varlik"] - a["diger_yuk"]), 5.0)
    for etiket, net, kul, ode in (
            ("bankalar UV", "ay_kredi_bnk_uv", "ay_kredi_bnk_uv_kul", "ay_kredi_bnk_uv_ode"),
            ("diğer sektörler UV", "ay_kredi_dgr_uv", "ay_kredi_dgr_uv_kul", "ay_kredi_dgr_uv_ode"),
            ("genel hükümet UV", "ay_kredi_gh_uv", "ay_kredi_gh_uv_kul", "ay_kredi_gh_uv_ode")):
        if {net, kul, ode} <= k:
            _k(f"{etiket}: net = kullanım − geri ödeme",
               a[net], a[kul] - a[ode], 1.0)
    return uy, rapor


def isaret_denetimi(a: pd.DataFrame) -> tuple[dict, list[str]]:
    """Rezerv AKIMININ işareti STOKLA sınanır.

    BPM6'da rezerv varlıklar finans hesabının varlık bacağıdır: POZİTİF değer
    rezerv ARTIŞI demektir. Bu bir varsayım değil, ÖLÇÜM: akım ile stokun
    aylık farkı aynı yöne bakmalı. (Eşit olmalarını beklemeyiz — stok
    değerleme etkisi, altın fiyatı ve çapraz kur hareketi taşır.)
    """
    uy: list[str] = []
    if not {"rezerv_akim", "rezerv_stok"} <= set(a.columns):
        return {}, ["İŞARET: rezerv akım/stok sınaması yapılamadı."]
    d = pd.DataFrame({"akim": a["rezerv_akim"],
                      "dstok": a["rezerv_stok"].diff()}).dropna()
    d = d.loc[d.index >= "2010-01-01"]
    if len(d) < 24:
        return {}, ["İŞARET: rezerv akım/stok sınaması için yeterli gözlem yok."]
    kor = float(d["akim"].corr(d["dstok"]))
    ayni = float((d["akim"] * d["dstok"] > 0).mean())
    rapor = {"n": int(len(d)), "korelasyon": round(kor, 3),
             "ayni_yon_orani": round(ayni, 3),
             "pencere": f"{d.index[0]:%Y-%m} … {d.index[-1]:%Y-%m}",
             "gecti": bool(kor > 0.5),
             "yorum": ("pozitif korelasyon → akım POZİTİF = rezerv ARTIŞI "
                       "(BPM6). Stok değerleme etkisi taşıdığı için eşitlik "
                       "beklenmez, YÖN beklenir.")}
    if kor <= 0.5:
        uy.append(
            f"İŞARET SINAMASI DÜŞTÜ: rezerv akımı ile stok değişimi arasındaki "
            f"korelasyon {kor:.3f} (aynı yön oranı %{ayni * 100:.0f}). Akımın "
            "işaret konvansiyonu değişmiş olabilir — 'pozitif = rezerv artışı' "
            "cümlesi GÜVENİLMEZ.")
    return rapor, uy


def olu_seri_denetimi(a: pd.DataFrame) -> list[str]:
    """SIFIR ≠ VERİ (ve ÖLÜ ≠ HER ZAMAN ÖLÜ).

    Q21 hatta alınmıyor. Q35/Q36 yalnız TANI için çekiliyor; burada ne zaman
    sustukları ÖLÇÜLÜR — "bugün sıfır" ile "hep sıfır" bir değildir. SDR
    yalnız tahsis yıllarında canlanır, genel hükümet diğer-yatırım varlığı
    yıllardır sıfır.
    """
    uy: list[str] = []
    for ad, etiket in (("imf_kredileri", "IMF kredileri (Q35)"),
                       ("od_finansmani", "Ödemeler dengesi finansmanı (Q36)")):
        if ad in a.columns:
            s = a[ad].dropna()
            nz = s[s != 0]
            if len(nz):
                print(f"  · TANI: {etiket} {len(nz)} ayda sıfırdan farklı; "
                      f"sonuncusu {nz.index[-1]:%m.%Y}. Bugün sıfır, "
                      "tarihçede değil — rezerv kimliği bu bacaklarla kapanır.")
    for ad, etiket in (("ay_sdr", "Özel Çekme Hakları (Q203)"),
                       ("diger_varlik_gh", "Diğer yatırım varlık — genel hükümet (Q22)"),
                       ("eb_kullanim_gh", "Eurobond ihracı — genel hükümet (A112)")):
        if ad not in a.columns:
            continue
        s = a[ad].dropna()
        if s.empty:
            continue
        son60 = s.iloc[-60:]
        if len(son60) >= 24 and (son60 == 0).all():
            uy.append(f"ÖLÜ SERİ: '{etiket}' son {len(son60)} ayın TAMAMINDA 0 "
                      "— dolu görünüyor ama bilgi taşımıyor; grafikte 'yok' "
                      "olarak işlenecek.")
    # Eurobond alt kırılımları SEYREK: ihraç olmayan ay BOŞ gelir, sıfır değil.
    for ad, etiket in (("eb_kullanim_gh", "A112 (genel hükümet)"),
                       ("eb_kullanim_dgr", "A114 (diğer sektör)")):
        if ad in a.columns:
            s = a[ad]
            pencere = s.loc[s.index >= "2010-01-01"]
            dolu = int(pencere.notna().sum())
            if dolu and dolu < 0.6 * len(pencere):
                print(f"  · SEYREK SERİ: {etiket} {dolu}/{len(pencere)} ayda "
                      "dolu — ihraç olmayan ay BOŞ gelir (sıfır değil).")
    return uy


# --------------------------------------------------------------------------- ana akış
def kos(yenile: bool = False) -> dict:
    print("EVDS3 → ödemeler dengesi ve dış finansman veri katmanı")
    print(f"  anahtar: {'ortam değişkeni' if os.environ.get('TTO_EVDS_KEY') else 'dosya'}")

    birim_rapor, birim_uy = birim_denetimi(yenile)
    for u in birim_uy:
        uyar(u)

    a = cek_kume(AYLIK, "ay", yenile, etiket="aylık")
    h = cek_kume(HAFTALIK, "hafta", yenile, etiket="haftalık (çarşamba)")
    c = cek_kume(CEYREK, "ceyrek", yenile, etiket="üç aylık")
    g = cek_kume(GUNLUK, "gun", yenile, etiket="günlük (kur)")

    s_ay = son_ay(a)
    s_ceyrek = son_ceyrek(c)
    s_hafta = son_hafta(h)
    s_gun = son_gun(g)
    print(f"  SON AY      : {ay_ad(s_ay)}")
    print(f"  SON ÇEYREK  : {ceyrek_ad(s_ceyrek)}")
    print(f"  SON HAFTA   : {gun_ad(s_hafta)} (çarşamba)")
    print(f"  SON GÜN(kur): {gun_ad(s_gun)}")

    for u in tazelik_denetimi(a, h, c, g):
        uyar(u)
    kim_uy, kim_rapor = kimlik_denetimi(a)
    for u in kim_uy:
        uyar(u)
    isaret, isaret_uy = isaret_denetimi(a)
    for u in isaret_uy:
        uyar(u)
    for u in olu_seri_denetimi(a):
        uyar(u)

    # ÇIKTILAR HER KOŞUDA YAZILIR — "dosya varsa atla" YASAK.
    a.to_csv(VERI / "aylik.csv")
    h.to_csv(VERI / "haftalik.csv")
    c.to_csv(VERI / "ceyreklik.csv")
    g.to_csv(VERI / "gunluk.csv")

    bugun = pd.Timestamp.today().normalize()
    durum = {
        "kosum": dt.date.today().isoformat(),
        "son_ay": s_ay.strftime("%Y-%m-%d"),
        "son_ceyrek": s_ceyrek.strftime("%Y-%m-%d"),
        "son_hafta": s_hafta.strftime("%Y-%m-%d"),
        "son_gun": s_gun.strftime("%Y-%m-%d"),
        "gecikme_gun": {
            "aylik": int((bugun - donem_sonu(s_ay, "ay")).days),
            "ceyrek": int((bugun - donem_sonu(s_ceyrek, "ceyrek")).days),
            "haftalik": int((bugun - s_hafta).days),
            "gunluk": int((bugun - s_gun).days),
        },
        "aylik_seri": int(a.shape[1]), "aylik_gozlem": int(a.shape[0]),
        "haftalik_seri": int(h.shape[1]), "haftalik_gozlem": int(h.shape[0]),
        "ceyrek_seri": int(c.shape[1]), "ceyrek_gozlem": int(c.shape[0]),
        "gunluk_seri": int(g.shape[1]), "gunluk_gozlem": int(g.shape[0]),
        "birim": birim_rapor,
        "kimlik": kim_rapor,
        "isaret_rezerv": isaret,
        "olu_seri_hatta_alinmadi": [
            "TP.ODANA6.Q21 (diğer yatırım varlık — Merkez Bankası): son 60 ayın "
            "tamamında 0; Q20 zaten içeriyor.",
        ],
        "tani_serileri": {
            "TP.ODANA6.Q35 / Q36": (
                "IMF kredileri ve ödemeler dengesi finansmanı. Bugün sıfır "
                "(son sıfırdan farklı ay: "
                + (lambda s: (f"{_aylar()[s.index[-1].month - 1]} "
                              f"{s.index[-1].year}") if len(s) else "yok")(
                    a["imf_kredileri"][a["imf_kredileri"] != 0].dropna()
                    if "imf_kredileri" in a.columns else pd.Series(dtype=float))
                + "), ama rezerv kimliği ancak onlarla kapanıyor: "
                  "Q33 = Q34 + Q35 + Q36. Metriğe ve grafiğe GİRMEZLER."),
        },
        "uyarilar": list(_UYARI),
    }
    (VERI / "veri_durum.json").write_text(
        json.dumps(durum, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  yazıldı: data/aylik.csv ({a.shape[0]}x{a.shape[1]}), "
          f"data/haftalik.csv ({h.shape[0]}x{h.shape[1]}), "
          f"data/ceyreklik.csv ({c.shape[0]}x{c.shape[1]}), "
          f"data/gunluk.csv ({g.shape[0]}x{g.shape[1]})")
    for ad, r in kim_rapor.items():
        print(f"    kimlik {'✓' if r['gecti'] else '✗'} {ad}: n={r['n']}, "
              f"maks {r['maks_fark']:,.2f} {r['birim']}")
    if isaret:
        print(f"    işaret {'✓' if isaret['gecti'] else '✗'} rezerv akım↔stok: "
              f"korelasyon {isaret['korelasyon']}, aynı yön "
              f"%{isaret['ayni_yon_orani'] * 100:.0f}")
    if _UYARI:
        print(f"\n[{len(_UYARI)} uyarı]")
    return durum


if __name__ == "__main__":
    kos(yenile="--yenile" in sys.argv)
