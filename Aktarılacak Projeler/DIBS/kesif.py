# -*- coding: utf-8 -*-
"""DİBS verim eğrisi & reel faiz — KEŞİF katmanı (EVDS3).

Bu dosya hattın veri katmanı DEĞİL; "hangi seri hangi kodla, hangi birimde,
hangi kuralla çekilecek" sorusunu GERÇEK API çağrılarıyla yanıtlayan keşif
betiğidir. Sonraki aşama (veri.py) buradaki bulguları ve sınıflandırma
kurallarını kullanır.

Koşum:
    python3 kesif.py            # tam keşif (serieList + doğrulama çekimleri)
    python3 kesif.py --hizli    # önbellekteki serieList ile, yalnız doğrulama

Çıktı:
    data/kesif.json         — makine okunur bulgu dosyası (veri.py bunu okur)
    data/dibs_evren.csv     — DİBS enstrüman evreni (kod, itfa, tür, sınıf)
    data/serieList_pydibs.json — ham serieList önbelleği (TTL'li)

BULGULARIN ÖZETİ (koşum bunları yeniden doğrular, ezbere yazılmaz)
------------------------------------------------------------------
1. EVDS'te SABİT VADELİ (constant maturity) bir TL DİBS getiri eğrisi YOK.
   "TP.ADAY.*" diye bir seri ailesi de yok — kategori/veri grubu uçlarıyla
   tarandı, bulunamadı. Eğri, tek tek kıymetlerden KURULACAK.
2. Kaynak veri grubu: `bie_pydibs` — "Devlet İç Borçlanma Senetlerinin
   Gösterge Niteliğindeki Değerleri", GÜNLÜK, TCMB. Her kıymet için iki seri:
       TP.<ISIN>          → "Değer"  = 100 TL nominal başına GÖSTERGE FİYAT
       TP.<ISIN>.ORAN     → türe göre değişir (aşağıya bak)
3. `.ORAN` serisinin ADI enstrüman türünü ele verir — birim tuzağı burada:
       "Kupon Faiz Oranı"   → DÖNEMSEL kupon TUTARI (100 nominal başına, %
                              değil TUTAR gibi kullanılır; yıllık DEĞİL)
       "Reel Kupon Oranı"   → TÜFE'ye endeksli (TÜFEX) tahvil, reel kupon
       "Kira Getirisi Oranı"→ kira sertifikası (sukuk), TRD ISIN'li
       "Diğer"              → hazine bonosu; değer = KALAN GÜN SAYISI (faiz DEĞİL)
4. TCMB her tahvilin STRIP'lerini de yayımlıyor. Seri adının sonundaki
   parantez etiketi ayrımı verir:
       ...A<ggaayy>  → ANAPARA strip'i  → ödeme 100
       ...K<n>...    → KUPON strip'i    → ödeme = o serinin .ORAN değeri
       (K/A yok)     → kuponlu TAHVİLİN kendisi (sıfır kuponlu DEĞİL)
   Strip'ler sıfır kuponlu olduğu için SPOT (zero) eğri BOOTSTRAP GEREKTİRMEDEN
   doğrudan okunur:  y = (ödeme / fiyat)^(365/gün) − 1
5. Etiketin gövdesi `^\\d+T\\d+$` ise (ör. 24T2, 61T2, 121T2) tahvil SABİT
   KUPONLU nominal DİBS'tir. Gövdenin sonunda "D" varsa (49T4D, 85T2D, 61T2D…)
   tahvil DEĞİŞKEN FAİZLİ ya da TÜFEX'tir; bu durumda yayımlanan kupon yalnız
   CARİ dönemin kuponudur, ileri vadeli kupon strip'ine uygulanırsa getiri
   saçmalar (ölçüldü: %1–%105 arası dağılım). Nominal eğriye ALINMAZ.
6. ISIN'in 10. karakteri "F" olan seriler (TP.TRT030227F18 gibi) fiyatı
   ~48.000 mertebesinde basar; 100 nominal ölçeğinde DEĞİLDİR, dışlanır.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import os
import pathlib
import re
import sys
import time
import urllib.request

# --------------------------------------------------------------------------- yollar
PROJE = pathlib.Path(__file__).resolve().parent
KOK = PROJE.parent.parent                      # …/TTO Trading
VERI = PROJE / "data"
VERI.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------- anahtar
# Fonlama/veri.py ile AYNI arama sırası. Anahtar koda GÖMÜLMEZ.
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
DEMET = 6                 # tek istekte kaç seri (satır sınırı seri sayısına bağlı DEĞİL)
LISTE_TTL_SAAT = 24

_ANAHTAR: str | None = None
_UYARI: list[str] = []


def uyar(m: str) -> None:
    if m not in _UYARI:
        _UYARI.append(m)
    print("  ! " + m, flush=True)


def anahtar() -> str:
    global _ANAHTAR
    if _ANAHTAR is None:
        _ANAHTAR = _evds_anahtari()
    return _ANAHTAR


def _cek(yol: str, deneme: int = 3):
    """EVDS3 JSON. Anahtar `key:` BAŞLIĞINDA gider, URL'de DEĞİL.

    Sorgu dizesi `?` ile başlamaz: .../{uc}/{param}={deger}&{param}={deger}
    """
    son: Exception | None = None
    for i in range(deneme):
        try:
            req = urllib.request.Request(
                f"{BASE}/{yol}", headers={"key": anahtar(), "User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as ex:
            son = ex
            if i < deneme - 1:
                time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"EVDS isteği düştü ({yol[:80]}): {son}") from son


def _taze(yol: pathlib.Path, ttl_saat: float) -> bool:
    return (yol.exists()
            and (dt.datetime.now().timestamp() - yol.stat().st_mtime) / 3600 < ttl_saat)


# --------------------------------------------------------------------------- gözlem çekimi
def gozlem(kodlar: list[str], bas: dt.date, son: dt.date) -> dict[str, dict[str, float]]:
    """{tarih(gg-aa-yyyy): {kod: değer}} — demet demet çeker.

    Tek istek ~1000 SATIRLA sınırlı ve aralığın SONUNDAN doldurur; bu keşifte
    pencere kısa tutulduğu için parçalama gerekmiyor. veri.py'de UZUN tarihçe
    çekilirken YILLIK PARÇALAMA şart (Fonlama/veri.py `_demet_cek`).
    """
    out: dict[str, dict[str, float]] = {}
    for i in range(0, len(kodlar), DEMET):
        g = kodlar[i:i + DEMET]
        url = (f"series={'-'.join(g)}&startDate={bas:%d-%m-%Y}"
               f"&endDate={son:%d-%m-%Y}&type=json")
        try:
            items = _cek(url).get("items", [])
        except Exception as ex:
            uyar(f"demet düştü ({', '.join(g)}): {ex}")
            continue
        for r in items:
            t = r.get("Tarih")
            if not t:
                continue
            hedef = out.setdefault(t, {})
            for k in g:
                v = r.get(k.replace(".", "_"))
                if v not in (None, ""):
                    try:
                        hedef[k] = float(v)
                    except ValueError:
                        pass
        time.sleep(0.12)
    return out


# ===========================================================================
# 1) DİBS ENSTRÜMAN EVRENİ
# ===========================================================================
DG_DIBS = "bie_pydibs"          # güncel, GÜNLÜK
DG_DIBS_ARSIV = "bie_pydibsarsiv"   # 1990'a kadar, ARŞİV (durağan)

# Seri adında ÜÇ ayrı biçim dolaşıyor; üçü de karşılanmazsa kıymetler sessizce
# evrenin dışında kalır (ölçüldü: tek biçim varsayımı 1935 kıymetin 288'ini düşürüyordu):
#   "TRT150328A17 ( 18.03.2026 15.03.2028 )  Değer (24T2A150328)"
#   "TRT070727A14 (2017-07-19/2027-07-07) Değer (121T2DA070727)"
#   "TRT110226A14 (24-02-2016/11-02-2026) Deger (121T2A110226)"   ← 'Deger' aksansız
_AD = re.compile(
    r"^(?P<isin>TR[A-Z]\w+)\s*\(\s*(?P<ihrac>[\d.\-]+)\s*[/\s]\s*(?P<itfa>[\d.\-]+)\s*\)\s*"
    r"(?P<tur>.+?)\s*\((?P<etiket>[^()]*)\)\s*$")
_ETI_SABIT = re.compile(r"^\d+T\d+(K\d+|A\d{6})?$")   # 24T2 / 61T2K8… / 121T2A080328
_ETI_ANAPARA = re.compile(r"A\d{6}$")
_ETI_KUPON = re.compile(r"K\d+")


def _tarih(s: str) -> dt.date | None:
    """gg.aa.yyyy · gg-aa-yyyy · yyyy-aa-gg — üçü de dolaşımda.

    ISO biçimi unutulursa evren kayıtları (itfa/ihraç ISO olarak saklanıyor)
    sessizce None döner ve eğri BOŞ çıkar; bir kez yaşandı.
    """
    if not s:
        return None
    for f in ("%d.%m.%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(s, f).date()
        except ValueError:
            pass
    return None


def seri_listesi(dg: str, yenile: bool = False) -> list[dict]:
    yol = VERI / f"serieList_{dg}.json"
    if yenile or not _taze(yol, LISTE_TTL_SAAT):
        d = _cek(f"serieList/type=json&code={dg}")
        yol.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    return json.loads(yol.read_text(encoding="utf-8"))


def evren(dg: str = DG_DIBS, yenile: bool = False) -> dict[str, dict]:
    """Kıymet bazında birleşik kayıt: {taban_kod: {…}}.

    Fiyat serisi (`TP.<ISIN>`) ile oran serisi (`TP.<ISIN>.ORAN`) AYNI kıymete
    aittir; tür bilgisi yalnız ORAN serisinin adında olduğu için ikisi burada
    birleştirilir.
    """
    ham = seri_listesi(dg, yenile)
    kayit: dict[str, dict] = {}
    ayristirilamayan = 0
    for s in ham:
        ad = (s.get("SERIE_NAME") or "").strip()
        # Arşiv grubunda ad "… Deger (9B) (Arşiv)" biçiminde bitiyor. Son
        # parantez soyulmazsa etiket "Arşiv" olur, sınıflandırma çöker ve
        # tarihçenin KISA UCU sessizce kaybolur (ölçüldü: 2019 eğrisi 3 yılın
        # altında hiç nokta vermiyordu).
        ad = re.sub(r"\s*\((?:Arşiv|Archive)\)\s*$", "", ad)
        m = _AD.match(ad)
        if not m:
            ayristirilamayan += 1
            continue
        kod = s["SERIE_CODE"]
        taban = kod[:-5] if kod.endswith(".ORAN") else kod
        e = kayit.setdefault(taban, {
            "kod": taban, "isin": m.group("isin"),
            "ihrac": str(_tarih(m.group("ihrac")) or ""),
            "itfa": str(_tarih(m.group("itfa")) or ""),
            "etiket": m.group("etiket"),
        })
        if kod.endswith(".ORAN"):
            e["oran_kod"] = kod
            e["oran_tur"] = m.group("tur")
            e["oran_son"] = s.get("END_DATE")
        else:
            e["fiyat_bas"] = s.get("START_DATE")
            e["fiyat_son"] = s.get("END_DATE")
    if ayristirilamayan:
        uyar(f"{dg}: {ayristirilamayan} seri adı ayrıştırılamadı "
             "(TCMB ad biçimini değiştirmiş olabilir).")
    for e in kayit.values():
        et = e["etiket"]
        if e.get("oran_tur") == "Deger":
            e["oran_tur"] = "Değer"
        e["strip"] = ("anapara" if _ETI_ANAPARA.search(et)
                      else "kupon" if _ETI_KUPON.search(et) else "tahvil")
        # Sabit kuponlu nominal DİBS mi? Etiket gövdesinin sonunda "D" varsa
        # değişken faizli / TÜFEX demektir; nominal eğriye giremez.
        e["sabit_nominal"] = bool(
            _ETI_SABIT.match(et)
            and e.get("oran_tur") in ("Kupon Faiz Oranı", None)
            and e["isin"][9:10] != "F")
        e["tufex"] = e.get("oran_tur") == "Reel Kupon Oranı"
        e["sukuk"] = e.get("oran_tur") == "Kira Getirisi Oranı"
        e["bono"] = e.get("oran_tur") == "Diğer"
    return kayit


def aktif(kayit: dict[str, dict], bugun: dt.date, tolerans_gun: int = 7) -> dict[str, dict]:
    out = {}
    for k, v in kayit.items():
        son = _tarih(v.get("fiyat_son") or "")
        if son and (bugun - son).days <= tolerans_gun:
            out[k] = v
    return out


# ===========================================================================
# 2) SPOT (ZERO) EĞRİ DOĞRULAMASI
# ===========================================================================
def spot_egri(kayit: dict[str, dict], ref: dt.date) -> list[dict]:
    """Sabit kuponlu nominal DİBS strip'lerinden `ref` günü spot eğri.

    Ödeme: anapara strip → 100; kupon strip → serinin kendi .ORAN değeri
    (DÖNEMSEL kupon TUTARI, yıllık oran DEĞİL).
    Getiri: yıllık bileşik, ACT/365.
    """
    aday = []
    for k, v in kayit.items():
        if not v["sabit_nominal"] or v["strip"] == "tahvil":
            continue
        itfa = _tarih(v["itfa"])
        if not itfa:
            continue
        gun = (itfa - ref).days
        if gun < 10:          # 10 günden kısa: fiyat kırpması getiriyi patlatır
            continue
        aday.append((gun, k, v))
    aday.sort()
    kodlar = [k for _, k, _ in aday]
    bas = ref - dt.timedelta(days=6)
    fiyat = gozlem(kodlar, bas, ref)
    oran = gozlem([k + ".ORAN" for k in kodlar], bas, ref)
    gun_ad = f"{ref:%d-%m-%Y}"
    f = fiyat.get(gun_ad, {})
    o = oran.get(gun_ad, {})
    out = []
    for gun, k, v in aday:
        p = f.get(k)
        if not p or p <= 0:
            continue
        odeme = 100.0 if v["strip"] == "anapara" else o.get(k + ".ORAN")
        if not odeme or odeme <= 0:
            continue
        T = gun / 365.0
        out.append({
            "kod": k, "itfa": v["itfa"], "etiket": v["etiket"],
            "strip": v["strip"], "vade_yil": round(T, 4),
            "odeme": odeme, "fiyat": p,
            "getiri": round(((odeme / p) ** (1 / T) - 1) * 100, 4),
        })
    return out


def egri_tutarlilik(egri: list[dict]) -> dict:
    """AYNI GÜNE itfa olan farklı strip'ler AYNI getiriyi vermeli.

    Bu hattın kimlik denetimi: sapma büyürse ödeme tanımı ya da etiket
    sınıflandırması bozulmuştur (ör. değişken faizli tahvil nominal eğriye
    sızmıştır).
    """
    grup: dict[str, list[float]] = {}
    for r in egri:
        grup.setdefault(r["itfa"], []).append(r["getiri"])
    sapmalar = [(max(v) - min(v), t, len(v)) for t, v in grup.items() if len(v) > 1]
    sapmalar.sort(reverse=True)
    return {
        "cok_kaynakli_vade": len(sapmalar),
        "maks_sapma_puan": round(sapmalar[0][0], 4) if sapmalar else None,
        "maks_sapma_itfa": sapmalar[0][1] if sapmalar else None,
        "medyan_sapma_puan": (round(sorted(s[0] for s in sapmalar)[len(sapmalar) // 2], 4)
                              if sapmalar else None),
    }


# ===========================================================================
# 3) REFERANS / BEKLENTİ / ENFLASYON SERİLERİ
# ===========================================================================
# (ad, kod, birim, frekans, not)  — birim EVDS3 meta verisinde ALAN olarak YOK;
# seri adından okunur ve büyüklük mertebesiyle sınanır (aşağıda `mertebe`).
REFERANS: list[tuple] = [
    ("tlref",        "TP.BISTTLREF.ORAN", "yüzde", "iş günü",
     "BIST TLREF gecelik referans faiz — carry ayağının kısa ucu"),
    ("politika",     "TP.PY.P02.1H",      "yüzde", "iş günü",
     "1 hafta vadeli repo SATIŞ kotasyonu = politika faizi (14.09.2018'den)"),
    ("politika_ger", "TP.PY.P06.1H",      "yüzde", "iş günü",
     "gerçekleşen 1 haftalık repo işlem faizi — 2018 öncesi vekil"),
    ("aofm",         "TP.APIFON4",        "yüzde", "iş günü",
     "TCMB ağırlıklı ortalama fonlama maliyeti"),
    ("koridor_alt",  "TP.PY.P01.ON",      "yüzde", "iş günü", "gecelik borçlanma"),
    ("koridor_ust",  "TP.PY.P02.ON",      "yüzde", "iş günü", "gecelik borç verme"),
    ("bist_on",      "TP.AOFOBAP",        "yüzde", "iş günü", "BİST gecelik repo AOF"),
    ("pka_12a",      "TP.PKAUO.S01.E.U",  "yüzde", "aylık",
     "PKA 12 ay sonrası yıllık TÜFE beklentisi (uygun ortalama) — FISHER girdisi"),
    ("pka_12a_medyan", "TP.BEK.S01.E.M",  "yüzde", "aylık", "aynı sorunun medyanı"),
    ("pka_12a_std",  "TP.BEK.S01.E.S",    "yüzde", "aylık", "beklenti dağılımının std sapması"),
    ("pka_12a_n",    "TP.BEK.S01.E.X",    "adet",  "aylık", "katılımcı sayısı (anket zayıflarsa uyarı)"),
    ("pka_24a",      "TP.PKAUO.S01.F.U",  "yüzde", "aylık", "24 ay sonrası yıllık TÜFE beklentisi"),
    ("pka_5y",       "TP.PKAUO.S01.G.U",  "yüzde", "aylık", "5 yıl sonrası yıllık TÜFE beklentisi"),
    ("pka_yilsonu",  "TP.PKAUO.S01.D.U",  "yüzde", "aylık", "cari yıl sonu yıllık TÜFE beklentisi"),
    ("pka_faiz_12a", "TP.PKAUO.S04.D.U",  "yüzde", "aylık", "12 ay sonrası politika faizi beklentisi"),
    ("pka_faiz_24a", "TP.PKAUO.S04.E.U",  "yüzde", "aylık", "24 ay sonrası politika faizi beklentisi"),
    ("reel_kesim_12a", "TP.ENFBEK.IYA12ENF", "yüzde", "aylık", "reel kesim 12 ay TÜFE beklentisi"),
    ("hanehalki_12a",  "TP.ENFBEK.HBA12ENF", "yüzde", "aylık", "hanehalkı 12 ay TÜFE beklentisi"),
    ("tufe",         "TP.TUKFIY2025.GENEL", "endeks", "aylık",
     "TÜFE genel endeks (2025=100) — geriye dönük reel faizin paydası"),
    ("ic_borc_tahvil", "TP.KB.A01", "bin TL", "aylık", "iç borç stoku – tahvil"),
    ("ic_borc_bono",   "TP.KB.A05", "bin TL", "aylık", "iç borç stoku – bono"),
    ("ic_borc_toplam", "TP.KB.A09", "bin TL", "aylık", "iç borç stoku – toplam"),
]

# Büyüklük mertebesi denetimi: (ad, alt, üst). Bir oran "yüzde" ise 0–500
# aralığında olmalı; 1000× hata bu eşikte yakalanır.
MERTEBE = {
    "yüzde": (-10.0, 500.0),
    "adet": (1.0, 500.0),
    "endeks": (50.0, 100000.0),
    "bin TL": (1e6, 1e12),
}


def referans_dogrula(bugun: dt.date) -> list[dict]:
    out = []
    gunluk = [r for r in REFERANS if r[3] == "iş günü"]
    aylik = [r for r in REFERANS if r[3] == "aylık"]
    # iş günü: son 30 gün yeter
    veri_g = gozlem([r[1] for r in gunluk], bugun - dt.timedelta(days=45), bugun)
    # aylık: EVDS aylık seride tarih biçimi "YYYY-M"; ayrı pencere
    veri_a = gozlem([r[1] for r in aylik], bugun - dt.timedelta(days=400), bugun)
    for ad, kod, birim, frek, aciklama in REFERANS:
        kaynak = veri_g if frek == "iş günü" else veri_a
        noktalar = [(t, d[kod]) for t, d in kaynak.items() if kod in d]

        def _anahtar(x):
            t = x[0]
            g = _tarih(t)
            if g:
                return (g.year, g.month, g.day)
            p = t.split("-")
            return (int(p[0]), int(p[1]), 1)

        noktalar.sort(key=_anahtar)
        kayit = {"ad": ad, "kod": kod, "birim": birim, "frekans": frek,
                 "aciklama": aciklama, "dogrulandi": bool(noktalar),
                 "gozlem": len(noktalar)}
        if noktalar:
            t, v = noktalar[-1]
            kayit["son_tarih"] = t
            kayit["son_deger"] = v
            alt, ust = MERTEBE.get(birim, (float("-inf"), float("inf")))
            if not (alt <= v <= ust):
                uyar(f"MERTEBE: {ad} ({kod}) son değer {v:,.4f} — '{birim}' için "
                     f"beklenen aralık [{alt:,.0f}, {ust:,.0f}] dışında. "
                     "Birim tanımı değişmiş olabilir.")
                kayit["mertebe_uyarisi"] = True
        else:
            # Seri kapanmış olabilir: EVDS tek istekte ~1000 SATIR döndürür ve
            # aralığın SONUNDAN doldurur; yakın pencere boşsa geriye doğru
            # yıllık parçalarla taranır. "Kod çalışmıyor" ile "seri durmuş"
            # birbirinden ancak böyle ayrılır.
            t, v = _geriye_tara(kod, bugun, frek)
            if t:
                kayit.update(dogrulandi=True, son_tarih=t, son_deger=v,
                             durum="YAYIN DURMUŞ (tarihsel seri)")
                uyar(f"YAYIN DURMUŞ: {ad} ({kod}) son gözlem {t} — kod geçerli "
                     "ama seri güncel değil; yalnız tarihçede kullanılabilir.")
            else:
                uyar(f"SERİ ALINAMADI: {ad} ({kod}) — hiçbir pencerede veri dönmedi.")
        out.append(kayit)
    return out


def _geriye_tara(kod: str, bugun: dt.date, frek: str) -> tuple[str | None, float | None]:
    yil = bugun.year
    while yil >= 2005:
        bas = dt.date(yil, 1, 1)
        son = min(dt.date(yil, 12, 31), bugun)
        d = gozlem([kod], bas, son)
        noktalar = [(t, x[kod]) for t, x in d.items() if kod in x]
        if noktalar:
            def _a(p):
                g = _tarih(p[0])
                if g:
                    return (g.year, g.month, g.day)
                q = p[0].split("-")
                return (int(q[0]), int(q[1]), 1)
            noktalar.sort(key=_a)
            return noktalar[-1]
        yil -= 1
    return None, None



# ===========================================================================
# 4) TÜFEX (TÜFE'ye endeksli DİBS) — REEL EĞRİ ve BAŞABAŞ ENFLASYON
# ===========================================================================
# TÜFEX'in "Değer"i ENDEKSLENMİŞ TL fiyatıdır (100 nominal başına), reel fiyat
# DEĞİL. Reel getiri için Hazine'nin REFERANS ENDEKS oranı gerekir:
#     RefEndeks(t) = TÜFE(m−3) + (gün−1)/D × [TÜFE(m−2) − TÜFE(m−3)]
#     oran(t) = RefEndeks(t) / RefEndeks(ihraç günü)
#     reel getiri = (100 × oran / fiyat)^(365/gün) − 1
# TÜFE burada 2003=100 zinciridir (TP.FG.J0). O seri 2026-01'de DONDU (TÜİK
# 2025=100'e geçti); sonrası TP.TUKFIY2025.GENEL ile ZİNCİRLENİR. Zincir
# katsayısı örtüşme ayından okunur, sabit yazılmaz.
CPI_ESKI = "TP.FG.J0"              # 2003=100, 2026-01'de durdu
CPI_YENI = "TP.TUKFIY2025.GENEL"   # 2025=100, cari


def tufe_zinciri(bugun: dt.date) -> dict[tuple[int, int], float]:
    def _ay(kod: str, bas: dt.date) -> dict[tuple[int, int], float]:
        out = {}
        d = gozlem([kod], bas, bugun)
        for t, x in d.items():
            if kod not in x:
                continue
            p = t.split("-")
            out[(int(p[0]), int(p[1]))] = x[kod]
        return out
    eski = _ay(CPI_ESKI, dt.date(2003, 1, 1))
    yeni = _ay(CPI_YENI, dt.date(2015, 1, 1))
    if not eski or not yeni:
        uyar("TÜFE zinciri kurulamadı — TÜFEX reel eğrisi hesaplanamaz.")
        return {}
    ortak = max(a for a in eski if a in yeni)
    k = eski[ortak] / yeni[ortak]
    cpi = dict(eski)
    for a, v in yeni.items():
        if a > ortak:
            cpi[a] = v * k
    return cpi


def _ref_endeks(g: dt.date, cpi: dict) -> float | None:
    def geri(ym, n):
        y, m = ym
        m -= n
        while m <= 0:
            m += 12
            y -= 1
        return (y, m)
    a = cpi.get(geri((g.year, g.month), 3))
    b = cpi.get(geri((g.year, g.month), 2))
    if a is None or b is None:
        return None
    import calendar
    D = calendar.monthrange(g.year, g.month)[1]
    return a + (g.day - 1) / D * (b - a)


def reel_egri(kayit: dict[str, dict], ref: dt.date, cpi: dict) -> list[dict]:
    aday = []
    for k, v in kayit.items():
        if not v["tufex"] or v["strip"] != "anapara":
            continue
        itfa = _tarih(v["itfa"])
        ihrac = _tarih(v["ihrac"])
        if not itfa or not ihrac or (itfa - ref).days < 60:
            continue
        aday.append(((itfa - ref).days, k, v, ihrac, itfa))
    aday.sort()
    fiyat = gozlem([k for _, k, _, _, _ in aday], ref - dt.timedelta(days=6), ref)
    f = fiyat.get(f"{ref:%d-%m-%Y}", {})
    It = _ref_endeks(ref, cpi)
    out = []
    if not It:
        return out
    for gun, k, v, ihrac, itfa in aday:
        p = f.get(k)
        I0 = _ref_endeks(ihrac, cpi)
        if not p or not I0:
            continue
        T = gun / 365.0
        oran = It / I0
        out.append({
            "kod": k, "ihrac": str(ihrac), "itfa": str(itfa),
            "vade_yil": round(T, 4), "fiyat_endeksli": p,
            "endeks_orani": round(oran, 4),
            "reel_getiri": round(((100.0 * oran / p) ** (1 / T) - 1) * 100, 4),
        })
    return out


def _egriden(egri: list[dict], alan: str, hedef: float) -> float | None:
    """Vade ekseninde doğrusal ara değer — eğri seyrekse None."""
    n = sorted(((r["vade_yil"], r[alan]) for r in egri))
    if not n or hedef < n[0][0] or hedef > n[-1][0]:
        return None
    for (t0, y0), (t1, y1) in zip(n, n[1:]):
        if t0 <= hedef <= t1:
            if t1 == t0:
                return y0
            return y0 + (y1 - y0) * (hedef - t0) / (t1 - t0)
    return None


def turetilmis(egri, r_egri, ref_ser) -> dict:
    """Hattın ana ölçüleri — GERÇEK koşumdan, örnek olarak bir kez hesaplanır."""
    d = {r["ad"]: r.get("son_deger") for r in ref_ser}
    n = {y: _egriden(egri, "getiri", y) for y in (0.25, 1, 2, 3, 5, 7, 9)}
    rr = {y: _egriden(r_egri, "reel_getiri", y) for y in (1, 2, 3, 5, 7)}
    out = {"nominal_spot": n, "tufex_reel_spot": rr}
    if n[2] and n[10 - 1]:
        out["egim_2y10y_puan"] = round((n[9] - n[2]), 3)   # 10y yok → 9y ucu
    if n[2] and n[5]:
        out["egim_2y5y_puan"] = round(n[5] - n[2], 3)
    if n[1] and n[2] and n[5]:
        out["kelebek_1_2_5_puan"] = round(2 * n[2] - n[1] - n[5], 3)
    # FISHER: basit çıkarma DEĞİL.
    bek = d.get("pka_12a")
    if n[1] is not None and bek is not None:
        out["ileri_reel_1y_fisher"] = round(((1 + n[1] / 100) / (1 + bek / 100) - 1) * 100, 3)
        out["ileri_reel_1y_basit_fark"] = round(n[1] - bek, 3)   # yalnız kıyas için
    if n[2] is not None and d.get("pka_24a") is not None:
        out["ileri_reel_2y_fisher"] = round(
            ((1 + n[2] / 100) / (1 + d["pka_24a"] / 100) - 1) * 100, 3)
    for y in (1, 2, 3, 5, 7):
        if n.get(y) is not None and rr.get(y) is not None:
            out[f"basabas_enflasyon_{y}y"] = round(
                ((1 + n[y] / 100) / (1 + rr[y] / 100) - 1) * 100, 3)
    for ad, kisa in (("tlref", "tlref"), ("politika", "politika"), ("aofm", "aofm")):
        if n[2] is not None and d.get(ad) is not None:
            out[f"carry_2y_{kisa}_puan"] = round(n[2] - d[ad], 3)
    return out


# --------------------------------------------------------------------------- ana akış
def kos(yenile: bool = False) -> dict:
    print("EVDS3 → DİBS verim eğrisi & reel faiz KEŞFİ")
    bugun = dt.date.today()

    print("\n[1] DİBS enstrüman evreni")
    kay = evren(DG_DIBS, yenile)
    akt = aktif(kay, bugun)
    print(f"  {DG_DIBS}: {len(kay)} kıymet, {len(akt)} tanesi aktif (son 7 gün)")
    sayim = {
        "toplam": len(kay), "aktif": len(akt),
        "aktif_sabit_nominal": sum(1 for v in akt.values() if v["sabit_nominal"]),
        "aktif_tufex": sum(1 for v in akt.values() if v["tufex"]),
        "aktif_sukuk": sum(1 for v in akt.values() if v["sukuk"]),
        "aktif_bono": sum(1 for v in akt.values() if v["bono"]),
        "aktif_anapara_strip": sum(1 for v in akt.values() if v["strip"] == "anapara"),
        "aktif_kupon_strip": sum(1 for v in akt.values() if v["strip"] == "kupon"),
        "aktif_tahvil": sum(1 for v in akt.values() if v["strip"] == "tahvil"),
    }
    for k, v in sayim.items():
        print(f"    {k:24s} {v}")
    baslangic = min((_tarih(v["fiyat_bas"]) for v in kay.values()
                     if v.get("fiyat_bas") and _tarih(v["fiyat_bas"])), default=None)
    print(f"    en erken fiyat gözlemi   {baslangic}")

    with (VERI / "dibs_evren.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["kod", "isin", "ihrac", "itfa", "etiket", "strip",
                    "oran_tur", "sabit_nominal", "tufex", "sukuk", "bono",
                    "fiyat_bas", "fiyat_son"])
        for v in sorted(kay.values(), key=lambda x: x["itfa"]):
            w.writerow([v["kod"], v["isin"], v["ihrac"], v["itfa"], v["etiket"],
                        v["strip"], v.get("oran_tur", ""), int(v["sabit_nominal"]),
                        int(v["tufex"]), int(v["sukuk"]), int(v["bono"]),
                        v.get("fiyat_bas", ""), v.get("fiyat_son", "")])

    # Vadesi dolan kıymetler güncel gruptan DÜŞÜYOR; tarihçe ARŞİV grubunda.
    # Bu yüzden 2019 gibi bir gün için eğri kurmak isteyen veri.py İKİ grubu
    # birleştirmek zorunda (ölçüldü: güncel grup 2013 için yalnız 5 nokta verir).
    arsiv = evren(DG_DIBS_ARSIV, yenile)
    print(f"  {DG_DIBS_ARSIV}: {len(arsiv)} kıymet (tarihçe için ZORUNLU)")
    gecmis_gun = dt.date(bugun.year - 7, 6, 17)
    while gecmis_gun.weekday() >= 5:
        gecmis_gun -= dt.timedelta(days=1)
    havuz = dict(arsiv)
    havuz.update(kay)
    gecmis = spot_egri(
        {k: v for k, v in havuz.items()
         if (_tarih(v.get("fiyat_bas") or "") or dt.date(2100, 1, 1)) <= gecmis_gun
         <= (_tarih(v.get("fiyat_son") or "") or dt.date(1900, 1, 1))},
        gecmis_gun)
    gecmis.sort(key=lambda r: r["vade_yil"])
    print(f"  tarihçe sınaması {gecmis_gun:%d.%m.%Y}: {len(gecmis)} nokta"
          + (f", {gecmis[0]['getiri']:.2f}% ({gecmis[0]['vade_yil']:.2f}y) → "
             f"{gecmis[-1]['getiri']:.2f}% ({gecmis[-1]['vade_yil']:.2f}y)"
             if gecmis else " — ARŞİV BİRLEŞTİRME ÇALIŞMIYOR"))

    print("\n[2] Spot (zero) eğri doğrulaması")
    # Referans gün: aktif serilerin ORTAK son günü — sabit tarih YASAK.
    sonlar = [_tarih(v["fiyat_son"]) for v in akt.values() if v.get("fiyat_son")]
    ref = max(s for s in sonlar if s)
    # Son gün kısmi dolu olabilir; bir iş günü geri çekilip tam kesit alınır.
    ref = ref - dt.timedelta(days=1)
    while ref.weekday() >= 5:
        ref -= dt.timedelta(days=1)
    print(f"  referans gün: {ref:%d.%m.%Y}")
    egri = spot_egri(akt, ref)
    egri.sort(key=lambda r: r["vade_yil"])
    tut = egri_tutarlilik(egri)
    print(f"  {len(egri)} sıfır kuponlu nokta, "
          f"vade {egri[0]['vade_yil']:.2f}–{egri[-1]['vade_yil']:.2f} yıl"
          if egri else "  EĞRİ BOŞ")
    print(f"  tutarlılık: aynı itfaya {tut['cok_kaynakli_vade']} çoklu kaynak, "
          f"maks sapma {tut['maks_sapma_puan']} puan "
          f"({tut['maks_sapma_itfa']}), medyan {tut['medyan_sapma_puan']} puan")
    if tut["maks_sapma_puan"] is not None and tut["maks_sapma_puan"] > 1.0:
        uyar(f"EĞRİ TUTARSIZ: aynı itfa gününe düşen strip'ler arasında "
             f"{tut['maks_sapma_puan']:.2f} puan fark var; sınıflandırma "
             "kuralı (değişken faizli ayıklama) bozulmuş olabilir.")
    for hedef in (0.25, 0.5, 1, 2, 3, 5, 7, 9):
        yakin = min(egri, key=lambda r: abs(r["vade_yil"] - hedef)) if egri else None
        if yakin and abs(yakin["vade_yil"] - hedef) < max(0.35, hedef * 0.12):
            print(f"    ~{hedef:>4}y → {yakin['getiri']:6.2f}%  "
                  f"({yakin['vade_yil']:.2f}y, {yakin['kod']})")

    print("\n[3] Referans / beklenti / enflasyon serileri")
    ref_ser = referans_dogrula(bugun)
    for r in ref_ser:
        d = f"{r['son_deger']:,.4f}" if r.get("son_deger") is not None else "—"
        print(f"    {'✓' if r['dogrulandi'] else '✗'} {r['kod']:22s} "
              f"{r['birim']:8s} {r['frekans']:8s} son {r.get('son_tarih','—'):>11s} = {d}")

    print("\n[4] TÜFEX reel eğrisi ve başabaş enflasyon")
    cpi = tufe_zinciri(bugun)
    r_egri = reel_egri(akt, ref, cpi)
    r_egri.sort(key=lambda r: r["vade_yil"])
    print(f"  {len(r_egri)} TÜFEX anapara strip'i "
          + (f"({r_egri[0]['vade_yil']:.2f}–{r_egri[-1]['vade_yil']:.2f} yıl)"
             if r_egri else ""))
    for r in r_egri:
        print(f"    {r['vade_yil']:5.2f}y reel {r['reel_getiri']:6.2f}%  "
              f"endeks oranı {r['endeks_orani']:6.3f}  {r['kod']}")

    print("\n[5] Türetilmiş ölçüler (bu koşumdan)")
    tur = turetilmis(egri, r_egri, ref_ser)
    for k, v in tur.items():
        print(f"    {k}: {v}")

    rapor = {
        "kosum": dt.datetime.now().isoformat(timespec="seconds"),
        "referans_gun": ref.isoformat(),
        "veri_grubu": DG_DIBS,
        "veri_grubu_arsiv": DG_DIBS_ARSIV,
        "en_erken_gozlem": baslangic.isoformat() if baslangic else None,
        "arsiv_kiymet": len(arsiv),
        "tarihce_sinamasi": {"gun": gecmis_gun.isoformat(), "nokta": len(gecmis),
                             "egri": gecmis},
        "sayim": sayim,
        "egri": egri,
        "egri_tutarlilik": tut,
        "reel_egri": r_egri,
        "turetilmis": tur,
        "referans_seriler": ref_ser,
        "uyarilar": list(_UYARI),
    }
    (VERI / "kesif.json").write_text(
        json.dumps(rapor, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n  yazıldı: data/kesif.json, data/dibs_evren.csv")
    if _UYARI:
        print(f"[{len(_UYARI)} uyarı]")
    return rapor


if __name__ == "__main__":
    kos(yenile="--yenile" in sys.argv)
