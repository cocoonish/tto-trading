# -*- coding: utf-8 -*-
"""El Niño ↔ Türkiye gıda enflasyonu — VERİ katmanı.

İki kaynak:
  ONI   NOAA CPC'nin Oceanic Niño Index'i (Niño 3.4 bölgesi, üç aylık kayan
        ortalama anomalisi, °C). Üç ayrı genel uç sırayla denenir; hiçbiri
        çalışmazsa hat DURUR — boş tabloyla başarılı çıkmak yasak.
  TÜFE  EVDS'ten manşet, çekirdek ve gıda alt endeksleri (ÖKTG aileleri).
        Kodlar Enflasyon hattının kullandıklarıyla AYNI; iki hat aynı seriyi
        farklı koddan çekerse bir gün sessizce ayrışırlar.
  FRED  IMF birincil emtia fiyatları + ABD TÜFE/gıda/çekirdek + Fed politika
        faizi. NEDEN GEREKLİ: Türkiye TÜFE alt endeksleri 2006'da başlıyor ve
        o pencerede yalnız İKİ güçlü El Niño tamamlandı — yön hakkında hüküm
        kurulamıyor. Aynı epizot tanımı 1980'de başlayan emtia serilerine
        uygulanınca örneklem BEŞ epizoda çıkar: Türkiye'de ölçülemeyen şey
        küresel tarafta ölçülebilir. FRED seçildi çünkü FAO'nun gıda endeksi
        her ay adı değişen bir CSV'de duruyor (kırılgan), FRED ise tek host,
        anahtarsız ve sabit kodlu.

KÜRESEL BLOK YUMUŞAK DÜŞER. ONI ya da TÜFE gelmezse hat DURUR — onlar tezin
gövdesi. FRED gelmezse hat durmaz ama sessiz de kalmaz: kunye.json'a
"kuresel_durum" yazılır, uyarı listesine düşer ve ölçüm katmanı küresel
bölümü hiç üretmez (eski değeri taşımaz).
"""
from __future__ import annotations

import io
import json
import os
import re
import urllib.request
from pathlib import Path

import pandas as pd

PROJE = Path(__file__).resolve().parent
DATA = PROJE / "data"
KOK = PROJE.parent.parent
BASE = "https://evds3.tcmb.gov.tr/igmevdsms-dis"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")

ANAHTAR_YOLLARI = (PROJE / ".evds_key", KOK / ".evds_key",
                   KOK / "Aktarılacak Projeler" / "TCMBNetRezerv" / ".evds_key")

ONI_UCLARI = (
    "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt",
    "https://origin.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt",
    "https://psl.noaa.gov/data/correlation/oni.data",
)

TUFE_SERI = {
    "tufe":            "TP.TUKFIY2025.GENEL",
    "gida":            "TP.FE25.OKTG10",
    "islenmemis_gida": "TP.FE25.OKTG11",
    "islenmis_gida":   "TP.FE25.OKTG14",
    # Çekirdek C. Gıda şokunun ÇEKİRDEĞE ulaşıp ulaşmadığı, bir merkez
    # bankasının "bakma, geç" kararını veren asıl sorudur; ABD tarafında da
    # aynı soru ölçülüyor ve ikisi karşılaştırılıyor.
    "cekirdek_c":      "TP.FE25.OKTG04",
}

# ── FRED (anahtarsız CSV). Kodlar 31.08.2026'da kesif_kuresel.py ile ölçüldü.
FRED_UC = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"
FRED_SERI = {
    # IMF birincil emtia fiyat endeksleri (aylık, USD, 2016=100)
    "emtia_gida":     "PFOODINDEXM",
    "emtia_tum":      "PALLFNFINDEXM",
    "emtia_yakitsiz": "PNFUELINDEXM",
    "emtia_icecek":   "PBEVEINDEXM",
    "emtia_hammadde": "PRAWMINDEXM",
    # ENSO'nun doğrudan vurduğu ürünler (USD/ton ya da USD/kg)
    "bugday":  "PWHEAMTUSDM",
    "misir":   "PMAIZMTUSDM",
    "pirinc":  "PRICENPQUSDM",
    "soya":    "PSOYBUSDM",
    "palm":    "PPOILUSDM",
    "seker":   "PSUGAISAUSDM",
    "kahve":   "PCOFFOTMUSDM",
    "kakao":   "PCOCOUSDM",
    # ABD
    "abd_tufe":      "CPIAUCSL",
    "abd_gida":      "CPIUFDSL",
    "abd_cekirdek":  "CPILFESL",
    "fed_faiz":      "FEDFUNDS",
}
# Küresel blok bunlarsız anlamsızdır; biri bile yoksa blok üretilmez.
FRED_ZORUNLU = ("emtia_gida", "abd_tufe", "abd_gida")

# DJF → merkez ay Ocak; JFM → Şubat; … ONI üç aylık kayan ortalamadır ve
# etiketi ORTA aya karşılık gelir. Bunu kaydırmak bütün gecikme ölçümünü
# bir ay kaydırırdı.
MEVSIM_AY = {"DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6,
             "JJA": 7, "JAS": 8, "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12}

_UYARI: list[str] = []
_A: str | None = None


def uyar(m: str) -> None:
    if m not in _UYARI:
        _UYARI.append(m)
    print("  ! " + m, flush=True)


def _metin_cek(url: str, deneme: int = 3) -> str:
    son = None
    for _ in range(deneme):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8", errors="replace")
        except Exception as ex:
            son = ex
    raise RuntimeError(str(son))


def _oni_ascii(metin: str) -> pd.Series:
    """SEAS YR TOTAL ANOM biçimi."""
    kayit = {}
    for satir in metin.splitlines():
        p = satir.split()
        if len(p) < 4 or p[0] not in MEVSIM_AY:
            continue
        try:
            yil, anom = int(p[1]), float(p[3])
        except ValueError:
            continue
        kayit[pd.Timestamp(yil, MEVSIM_AY[p[0]], 1)] = anom
    return pd.Series(kayit).sort_index()


def _oni_psl(metin: str) -> pd.Series:
    """PSL biçimi: ilk satır yıl aralığı, sonra 'YIL v1 … v12'."""
    kayit = {}
    for satir in metin.splitlines():
        p = satir.split()
        if len(p) != 13:
            continue
        try:
            yil = int(p[0])
            if not 1870 <= yil <= 2100:
                continue
            for i, v in enumerate(p[1:], start=1):
                x = float(v)
                if x < -90:          # eksik veri işareti
                    continue
                kayit[pd.Timestamp(yil, i, 1)] = x
        except ValueError:
            continue
    return pd.Series(kayit).sort_index()


def oni_cek() -> tuple[pd.Series, str]:
    for uc in ONI_UCLARI:
        try:
            metin = _metin_cek(uc)
        except Exception as ex:
            uyar(f"ONI ucu düştü: {uc} — {ex}")
            continue
        s = _oni_ascii(metin) if "oni.ascii" in uc else _oni_psl(metin)
        if len(s) > 500:
            print(f"  ONI alındı: {uc}  ({len(s)} ay, {s.index.min():%Y-%m} → "
                  f"{s.index.max():%Y-%m}, son {s.iloc[-1]:+.2f}°C)")
            return s, uc
        uyar(f"ONI ucu az satır döndü ({len(s)}): {uc}")
    raise SystemExit("ONI hiçbir uçtan alınamadı — hat duruyor")


def _anahtar() -> str:
    a = (os.environ.get("TTO_EVDS_KEY") or "").strip()
    if a:
        return a
    for y in ANAHTAR_YOLLARI:
        if y.exists() and y.read_text(encoding="utf-8").strip():
            return y.read_text(encoding="utf-8").strip()
    raise SystemExit("EVDS anahtarı yok")


def _evds(url: str, deneme: int = 3):
    global _A
    if _A is None:
        _A = _anahtar()
    son = None
    for _ in range(deneme):
        try:
            req = urllib.request.Request(url, headers={"key": _A, "User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as ex:
            son = ex
    raise RuntimeError(f"EVDS düştü: {son}")


def tufe_cek() -> pd.DataFrame:
    kodlar = list(TUFE_SERI.values())
    guvenli = [k.replace(".", "_") for k in kodlar]
    url = (f"{BASE}/series={'-'.join(kodlar)}"
           f"&startDate=01-01-1995&endDate=31-12-2030&type=json")
    items = _evds(url).get("items", [])
    if not items:
        raise SystemExit("EVDS TÜFE serileri boş döndü — hat duruyor")
    df = pd.DataFrame(items)
    idx = pd.to_datetime(df["Tarih"].astype(str), format="%Y-%m", errors="coerce")
    out = {ad: pd.to_numeric(df[g].replace("", None), errors="coerce")
           for ad, g in zip(TUFE_SERI, guvenli) if g in df.columns}
    eksik = [a for a in TUFE_SERI if a not in out]
    if eksik:
        raise SystemExit(f"EVDS'te bulunamayan seri: {eksik} — hat duruyor")
    t = pd.DataFrame(out)
    t.index = pd.Index(idx)
    t = t[~t.index.isna()].sort_index().dropna(how="all")
    print(f"  TÜFE alındı: {t.shape[1]} seri, {len(t)} ay, "
          f"{t.index.min():%Y-%m} → {t.index.max():%Y-%m}")
    return t


def _fred_seri(kod: str) -> pd.Series | None:
    metin = _metin_cek(FRED_UC.format(kod), deneme=2)
    df = pd.read_csv(io.StringIO(metin))
    if df.shape[1] < 2:
        return None
    tar = pd.to_datetime(df.iloc[:, 0], errors="coerce")
    deg = pd.to_numeric(df.iloc[:, 1].replace(".", None), errors="coerce")
    s = pd.Series(deg.to_numpy(), index=pd.Index(tar)).dropna()
    # Aylık seriler ayın ilk gününe damgalıdır; yine de normalize edilir ki
    # ONI ile birleştirme gün farkından sessizce boşa düşmesin.
    s.index = s.index.to_period("M").to_timestamp()
    return s[~s.index.duplicated(keep="last")].sort_index() if len(s) else None


def fred_cek() -> tuple[pd.DataFrame | None, list[str]]:
    """FRED bloğu. Yumuşak düşer: eksik seri uyarı üretir, hattı durdurmaz."""
    alinan, dusen = {}, []
    for ad, kod in FRED_SERI.items():
        try:
            s = _fred_seri(kod)
        except Exception as ex:
            dusen.append(ad)
            uyar(f"FRED serisi düştü: {ad} ({kod}) — {ex}")
            continue
        if s is None or s.empty:
            dusen.append(ad)
            uyar(f"FRED serisi boş: {ad} ({kod})")
            continue
        alinan[ad] = s
    eksik_zorunlu = [a for a in FRED_ZORUNLU if a not in alinan]
    if eksik_zorunlu:
        uyar(f"FRED zorunlu serileri eksik ({eksik_zorunlu}) — KÜRESEL BLOK ÜRETİLMEYECEK")
        return None, dusen
    df = pd.DataFrame(alinan).sort_index()
    print(f"  FRED alındı: {df.shape[1]}/{len(FRED_SERI)} seri, {len(df)} ay, "
          f"{df.index.min():%Y-%m} → {df.index.max():%Y-%m}")
    if dusen:
        print(f"  ! FRED'de alınamayan: {', '.join(dusen)}")
    return df, dusen


def main() -> int:
    DATA.mkdir(exist_ok=True)
    print("── El Niño hattı · veri")
    oni, uc = oni_cek()
    oni.to_frame("oni").to_csv(DATA / "oni.csv", encoding="utf-8")
    tufe = tufe_cek()
    tufe.to_csv(DATA / "tufe.csv", encoding="utf-8")
    kur, kur_dusen = fred_cek()
    kur_yol = DATA / "kuresel.csv"
    if kur is not None:
        kur.to_csv(kur_yol, encoding="utf-8")
    elif kur_yol.exists():
        # Eski dosyayı BIRAKMAK, bayat sayıyı taze gibi göstermek olurdu.
        kur_yol.unlink()
        uyar("kuresel.csv silindi — küresel blok bu koşuda alınamadı")
    (DATA / "kunye.json").write_text(json.dumps({
        "oni_uc": uc,
        "oni_bas": f"{oni.index.min():%Y-%m}", "oni_son": f"{oni.index.max():%Y-%m}",
        "oni_son_deger": round(float(oni.iloc[-1]), 2),
        "tufe_bas": f"{tufe.index.min():%Y-%m}", "tufe_son": f"{tufe.index.max():%Y-%m}",
        "seriler": TUFE_SERI,
        "kuresel_durum": "alindi" if kur is not None else "alinamadi",
        "kuresel_bas": f"{kur.index.min():%Y-%m}" if kur is not None else None,
        "kuresel_son": f"{kur.index.max():%Y-%m}" if kur is not None else None,
        "kuresel_dusen": kur_dusen,
        "uyarilar": _UYARI,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"── veri yazıldı: {DATA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
