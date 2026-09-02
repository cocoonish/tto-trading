# -*- coding: utf-8 -*-
"""El Niño ↔ Türkiye gıda enflasyonu — VERİ katmanı.

İki kaynak:
  ONI   NOAA CPC'nin Oceanic Niño Index'i (Niño 3.4 bölgesi, üç aylık kayan
        ortalama anomalisi, °C). Üç ayrı genel uç sırayla denenir; hiçbiri
        çalışmazsa hat DURUR — boş tabloyla başarılı çıkmak yasak.
  TÜFE  EVDS'ten manşet, çekirdek ve gıda alt endeksleri (ÖKTG aileleri).
        Kodlar Enflasyon hattının kullandıklarıyla AYNI; iki hat aynı seriyi
        farklı koddan çekerse bir gün sessizce ayrışırlar.
  KÜRESEL  Dört kaynak, dört ayrı kapı:
        · Dünya Bankası Pink Sheet (xlsx) — aylık emtia endeksleri ve ürün
          fiyatları, 1960'tan bugüne.
        · BLS (anahtarsız v2 API) — ABD TÜFE manşet, gıda ve çekirdek.
        · BIS (SDMX CSV) — merkez bankası politika faizleri; ABD serisi
          1954'te başlıyor, Türkiye ve Euro Bölgesi de aynı uçtan geliyor.
        · ECB (SDMX CSV) — Euro Bölgesi HICP manşet ve gıda, yıllık % değişim.

        NEDEN GEREKLİ: Türkiye TÜFE alt endeksleri 2006'da başlıyor ve o
        pencerede yalnız İKİ güçlü El Niño tamamlandı — yön hakkında hüküm
        kurulamıyor. Aynı epizot tanımı 1960'ta başlayan emtia serilerine
        uygulanınca örneklem kat kat büyür: Türkiye'de ölçülemeyen şey,
        şokun GELDİĞİ yerde ölçülebilir.

        NEDEN BU KAYNAKLAR: FRED bu koşucudan erişilemiyor — üç ucu da zaman
        aşımına uğradı (31.08.2026 keşif koşusu); IMF'in SDMX ucunun DNS'i
        çözülmüyor, datamapper 403 veriyor. Ölçülerek seçilen bu dört kapı
        FRED'in vereceğinden daha fazlasını veriyor: örneklem 1980 yerine
        1960'ta başlıyor ve karşılaştırmaya ikinci bir ekonomi (Euro Bölgesi)
        giriyor.

KÜRESEL BLOK YUMUŞAK DÜŞER. ONI ya da TÜFE gelmezse hat DURUR — onlar tezin
gövdesi. Küresel kaynaklar gelmezse hat durmaz ama sessiz de kalmaz:
kunye.json'a "kuresel_durum" yazılır, uyarı listesine düşer, eski kuresel.csv
SİLİNİR ve ölçüm katmanı küresel bölümü hiç üretmez (eski değeri taşımaz).
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

# ── KÜRESEL KANADIN KAYNAKLARI. 31.08.2026'da koşucudan ölçüldü: FRED üç
# ucundan da ZAMAN AŞIMINA uğruyor, IMF SDMX'in DNS'i çözülmüyor, IMF
# datamapper 403 veriyor. Açık kapılar aşağıdakiler ve FRED'den DAHA İYİLER:
# Pink Sheet aylık emtiayı 1960'a taşıyor (FRED 1980), BIS politika faizini
# 1954'ten veriyor, ECB ikinci bir karşılaştırma ekonomisi (Euro Bölgesi)
# getiriyor. Her kaynak kendi başına yumuşak düşer.
# Dosyanın adresi her güncellemede DEĞİŞEN bir sağlama taşıyor; sabit bir
# adres yazmak, bir gün sessizce ESKİ bir sürümü çekmek demek. 31.08.2026
# koşusu bunu gösterdi: sabit adres 2025-12'de biten bir dosyayı getirdi ve
# emtia serisi yedi ay geride kaldı — koşu yeşil bitti, kimse fark etmedi.
# Bu yüzden adres önce CMO sayfasından ÇÖZÜLÜR; sabit adresler yalnız yedek.
PINK_SAYFA = "https://www.worldbank.org/en/research/commodity-markets"
PINK_KALIP = re.compile(
    r"https://thedocs\.worldbank\.org/[^\"'\s>]*CMO-Historical-Data-Monthly\.xlsx")
PINK_UCLARI = (
    "https://thedocs.worldbank.org/en/doc/18675f1d1639c7a34d463f59263ba0a2-"
    "0050012025/related/CMO-Historical-Data-Monthly.xlsx",
    "https://thedocs.worldbank.org/en/doc/5d903e848db1d1b83e0ec8f744e55570-"
    "0350012021/related/CMO-Historical-Data-Monthly.xlsx",
)
BLS_UC = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
BLS_SERI = {"abd_tufe": "CUUR0000SA0", "abd_gida": "CUUR0000SAF1",
            "abd_cekirdek": "CUUR0000SA0L1E"}
BLS_BAS = 1960
BIS_UC = "https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/M.{}?format=csv"
BIS_ULKE = {"faiz_abd": "US", "faiz_tr": "TR", "faiz_ea": "XM"}
ECB_UC = ("https://data-api.ecb.europa.eu/service/data/ICP/M.U2.N.{}.4.ANR"
          "?format=csvdata&startPeriod=1990-01")
ECB_SERI = {"ea_tufe_12a": "000000", "ea_gida_12a": "010000"}

# Pink Sheet sütun adları dosyanın kendisinden okunur; buradaki eşleme
# ARANACAK adı verir (küçük harfe indirilip boşluklar sadeleştirilerek).
PINK_ENDEKS = {
    "emtia_enerji":   "energy",
    "emtia_yakitsiz": "non-energy",
    "emtia_tarim":    "agriculture",
    "emtia_icecek":   "beverages",
    "emtia_gida":     "food",
    "emtia_yaglar":   "oils & meals",
    "emtia_tahil":    "grains",
    "emtia_diger":    "other food",
    "emtia_hammadde": "raw materials",
    "emtia_gubre":    "fertilizers",
    "emtia_metal":    "metals & minerals",
}
PINK_URUN = {
    "palm":    "palm oil",
    "soya":    "soybeans",
    "pirinc":  "rice, thai 5%",
    "bugday":  "wheat, us hrw",
    "misir":   "maize",
    "seker":   "sugar, world",
    "kahve":   "coffee, robusta",
    "kakao":   "cocoa",
    "muz":     "banana, us",
    "portakal": "orange",
    "cay":     "tea, avg 3 auctions",
}
# Küresel blok bunlarsız anlamsızdır; biri bile yoksa blok üretilmez.
KURESEL_ZORUNLU = ("emtia_gida", "abd_tufe", "abd_gida")

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


AYRAC = "|"          # sütunun başlık hücrelerini birleştiren ayraç


def _ad_sadelestir(x) -> str:
    return re.sub(r"\s+", " ", str(x)).strip().lower()


def _pink_sayfa(xl, sayfa: str) -> pd.DataFrame | None:
    """Pink Sheet sayfasını başlık satırını BULARAK okur.

    Dosyanın başlık düzeni yıllar içinde değişiyor (birim satırı, kod satırı,
    boş satırlar). Sabit skiprows vermek, düzen değişince SESSİZCE yanlış
    sütun okumak demekti. Onun yerine ilk 'YYYYMxx' satırı bulunur ve başlık,
    onun üstündeki satırlar arasından EN ÇOK metin taşıyan satır seçilir.
    """
    df = pd.read_excel(xl, sheet_name=sayfa, header=None)
    if df.empty:
        return None
    # Hücreler str'e TEK TEK çevrilir. Series.astype(str) sütunu tek tip
    # varsayıyor ve karışık tipli sütunda (başlıklarda metin, gövdede sayı)
    # düşüyordu — keşif koşusu bunu 'Monthly Prices' sayfasında yakaladı.
    kol0 = [str(x).strip() for x in df.iloc[:, 0].tolist()]
    ilk = next((i for i, v in enumerate(kol0)
                if len(v) == 7 and v[:4].isdigit() and v[4].upper() == "M"
                and v[5:].isdigit()), None)
    if ilk is None or ilk == 0:
        return None
    # BAŞLIK ÇOK KATLI VE İKİ SAYFADA FARKLI. 'Monthly Indices'te üst satır ana
    # kategorileri (Energy, Non-energy, Agriculture, Food…), alt satır alt
    # kalemleri (Oils & Meals, Grains, Other Food…) taşıyor; 'Monthly Prices'ta
    # ise ad üstte, BİRİM ($/mt) altta duruyor. 31.08.2026'da bu iki düzen
    # sırayla ısırdı: önce "en çok metin taşıyan satırı seç" endeksleri adsız
    # bıraktı, sonra "aşağıdan yukarı ilk dolu hücreyi al" ürün adlarının
    # yerine birimleri koydu ve on bir ürün birden düştü.
    #
    # Doğrusu satır SEÇMEMEK: her sütunun BÜTÜN başlık hücreleri aday olarak
    # saklanır ve eşleme adaylardan herhangi biriyle tutar. Hangi satırın ad,
    # hangisinin birim olduğunu bilmek gerekmez — ve yarın üçüncü bir düzen
    # gelirse de gerekmeyecek.
    ust = df.iloc[:ilk]
    adlar = ["tarih"]
    for j in range(1, df.shape[1]):
        aday = []
        for i in range(len(ust)):
            h = ust.iat[i, j]
            if h is None or not str(h).strip() or str(h).strip().lower() == "nan":
                continue
            a = _ad_sadelestir(h)
            if a and a not in aday:
                aday.append(a)
        adlar.append(AYRAC.join(aday) if aday else f"sutun_{j}")
    # Aynı adı taşıyan iki sütun olursa ikincisi sessizce ilkini ezerdi.
    gorulen: dict[str, int] = {}
    for j, a in enumerate(adlar):
        if a in gorulen:
            gorulen[a] += 1
            adlar[j] = f"{a}{AYRAC}#{gorulen[a]}"
        else:
            gorulen[a] = 0
    veri = df.iloc[ilk:].copy()
    veri.columns = adlar
    idx = pd.to_datetime(
        pd.Series([str(x).strip().replace("M", "-") for x in veri["tarih"].tolist()]),
        format="%Y-%m", errors="coerce")
    veri = veri.drop(columns=["tarih"])
    veri.index = pd.Index(idx)
    veri = veri[~veri.index.isna()]
    return veri.apply(pd.to_numeric, errors="coerce")


def _pink_es(veri: pd.DataFrame, aranan: str) -> pd.Series | None:
    """Sütunu ADAYLARINDAN herhangi biriyle bulur.

    Sütun adı, o sütunun bütün başlık hücrelerinin AYRAC ile birleştirilmişidir
    (ör. "cocoa|$/kg"). Önce tam eşleşme, sonra önek eşleşmesi denenir; önek,
    'coffee, robusta' ↔ 'coffee, robusta **' gibi yıllara göre kuyruk alan
    adlar için gerekli.
    """
    if veri is None:
        return None
    for k in veri.columns:
        if any(p == aranan for p in str(k).split(AYRAC)):
            return veri[k]
    for k in veri.columns:
        if any(p.startswith(aranan) for p in str(k).split(AYRAC)):
            return veri[k]
    return None


_PINK_SUTUNLAR: dict[str, list[str]] = {}


def _pink_adresleri() -> list[str]:
    """Önce CMO sayfasından çöz, sonra sabit yedekler. Sıra önemli: taze olan
    önce denenmeli, yoksa yedek her zaman kazanır ve dosya donar."""
    uclar: list[str] = []
    try:
        req = urllib.request.Request(PINK_SAYFA, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as r:
            sayfa = r.read().decode("utf-8", "replace")
        for m in PINK_KALIP.findall(sayfa):
            if m not in uclar:
                uclar.append(m)
        if uclar:
            print(f"  Pink Sheet adresi sayfadan çözüldü: …{uclar[0][-58:]}")
        else:
            uyar("CMO sayfasında Pink Sheet bağlantısı bulunamadı — yedek adresler")
    except Exception as ex:
        uyar(f"CMO sayfası okunamadı ({ex}) — yedek adresler")
    for u in PINK_UCLARI:
        if u not in uclar:
            uclar.append(u)
    return uclar


def pink_cek() -> tuple[dict[str, pd.Series], list[str]]:
    ham = None
    for uc in _pink_adresleri():
        try:
            req = urllib.request.Request(uc, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                ham = r.read()
            print(f"  Pink Sheet alındı: {len(ham):,} bayt")
            break
        except Exception as ex:
            uyar(f"Pink Sheet ucu düştü: {uc[:60]}… — {ex}")
    if ham is None:
        return {}, list(PINK_ENDEKS) + list(PINK_URUN)
    xl = pd.ExcelFile(io.BytesIO(ham))
    sayfalar = {}
    for sayfa in xl.sheet_names:
        d = _pink_sayfa(xl, sayfa)
        if d is not None and not d.empty:
            sayfalar[_ad_sadelestir(sayfa)] = d
    endeks = sayfalar.get("monthly indices")
    fiyat = sayfalar.get("monthly prices")
    alinan, dusen = {}, []
    for ad, aranan in PINK_ENDEKS.items():
        s = _pink_es(endeks, aranan)
        (alinan.setdefault(ad, s) if s is not None else dusen.append(ad))
    for ad, aranan in PINK_URUN.items():
        s = _pink_es(fiyat, aranan)
        (alinan.setdefault(ad, s) if s is not None else dusen.append(ad))
    if dusen:
        uyar(f"Pink Sheet'te bulunamayan sütun: {', '.join(dusen)}")
        # Eşleme tutmadıysa dosyanın GERÇEK sütun adları künyeye yazılır.
        # Aksi halde "bulunamadı" der ve neyin bulunabileceğini söylemez;
        # düzeltmek için her seferinde yeni bir keşif koşusu gerekirdi.
        _PINK_SUTUNLAR.clear()
        for sayfa_ad, d in sayfalar.items():
            _PINK_SUTUNLAR[sayfa_ad] = [str(c) for c in d.columns]
    else:
        _PINK_SUTUNLAR.clear()
    if alinan:
        ilk = next(iter(alinan.values()))
        print(f"  Pink Sheet: {len(alinan)} seri, {ilk.dropna().index.min():%Y-%m} → "
              f"{ilk.dropna().index.max():%Y-%m}")
    return {k: v.dropna() for k, v in alinan.items()}, dusen


def bls_cek() -> tuple[dict[str, pd.Series], list[str]]:
    """BLS anahtarsız v2: istek başına EN ÇOK 10 YIL. Dilimler birleştirilir."""
    par = {ad: {} for ad in BLS_SERI}
    kod_ad = {v: k for k, v in BLS_SERI.items()}
    bit = pd.Timestamp.today().year
    yil = BLS_BAS
    while yil <= bit:
        y2 = min(yil + 9, bit)
        govde = json.dumps({"seriesid": list(BLS_SERI.values()),
                            "startyear": str(yil), "endyear": str(y2)}).encode()
        try:
            req = urllib.request.Request(
                BLS_UC, data=govde,
                headers={"User-Agent": UA, "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=90) as r:
                j = json.loads(r.read().decode("utf-8"))
        except Exception as ex:
            uyar(f"BLS dilimi düştü {yil}-{y2}: {ex}")
            yil = y2 + 1
            continue
        if j.get("status") != "REQUEST_SUCCEEDED":
            uyar(f"BLS dilimi reddetti {yil}-{y2}: {j.get('message')}")
            yil = y2 + 1
            continue
        for s in j.get("Results", {}).get("series", []):
            ad = kod_ad.get(s.get("seriesID"))
            for d in s.get("data") or []:
                if not str(d.get("period", "")).startswith("M") or d["period"] == "M13":
                    continue
                t = pd.Timestamp(int(d["year"]), int(d["period"][1:]), 1)
                try:
                    par[ad][t] = float(d["value"])
                except (TypeError, ValueError):
                    pass
        yil = y2 + 1
    alinan = {k: pd.Series(v).sort_index() for k, v in par.items() if v}
    dusen = [k for k in BLS_SERI if k not in alinan]
    if alinan:
        ilk = next(iter(alinan.values()))
        print(f"  BLS: {len(alinan)} seri, {ilk.index.min():%Y-%m} → {ilk.index.max():%Y-%m}")
    return alinan, dusen


def _sdmx_csv(url: str) -> pd.Series | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as r:
        df = pd.read_csv(io.StringIO(r.read().decode("utf-8", "replace")))
    if "TIME_PERIOD" not in df.columns or "OBS_VALUE" not in df.columns:
        return None
    d = df[["TIME_PERIOD", "OBS_VALUE"]].dropna()
    idx = pd.to_datetime(d["TIME_PERIOD"].astype(str), format="%Y-%m", errors="coerce")
    s = pd.Series(pd.to_numeric(d["OBS_VALUE"], errors="coerce").to_numpy(),
                  index=pd.Index(idx)).dropna()
    return s[~s.index.duplicated(keep="last")].sort_index() if len(s) else None


def bis_ecb_cek() -> tuple[dict[str, pd.Series], list[str]]:
    alinan, dusen = {}, []
    for ad, ulke in BIS_ULKE.items():
        try:
            s = _sdmx_csv(BIS_UC.format(ulke))
        except Exception as ex:
            s = None
            uyar(f"BIS düştü ({ulke}): {ex}")
        (alinan.setdefault(ad, s) if s is not None else dusen.append(ad))
    for ad, kod in ECB_SERI.items():
        try:
            s = _sdmx_csv(ECB_UC.format(kod))
        except Exception as ex:
            s = None
            uyar(f"ECB düştü ({kod}): {ex}")
        (alinan.setdefault(ad, s) if s is not None else dusen.append(ad))
    for ad, s in alinan.items():
        print(f"  {ad}: {len(s)} ay, {s.index.min():%Y-%m} → {s.index.max():%Y-%m}, "
              f"son {s.iloc[-1]:.2f}")
    return alinan, dusen


def kuresel_cek() -> tuple[pd.DataFrame | None, list[str]]:
    """Küresel blok. YUMUŞAK DÜŞER: eksik seri uyarı üretir, hattı durdurmaz."""
    alinan, dusen = {}, []
    for f in (pink_cek, bls_cek, bis_ecb_cek):
        try:
            a, d = f()
        except Exception as ex:
            uyar(f"{f.__name__} tümüyle düştü: {ex}")
            continue
        alinan.update(a)
        dusen += d
    eksik = [a for a in KURESEL_ZORUNLU if a not in alinan]
    if eksik:
        uyar(f"küresel zorunlu seriler eksik ({eksik}) — KÜRESEL BLOK ÜRETİLMEYECEK")
        return None, dusen
    df = pd.DataFrame(alinan).sort_index()
    df = df[df.index.notna()]
    print(f"  küresel blok: {df.shape[1]} seri, {len(df)} ay, "
          f"{df.index.min():%Y-%m} → {df.index.max():%Y-%m}")
    if dusen:
        print(f"  ! alınamayan: {', '.join(sorted(set(dusen)))}")
    return df, sorted(set(dusen))


def main() -> int:
    DATA.mkdir(exist_ok=True)
    print("── El Niño hattı · veri")
    oni, uc = oni_cek()
    oni.to_frame("oni").to_csv(DATA / "oni.csv", encoding="utf-8")
    tufe = tufe_cek()
    tufe.to_csv(DATA / "tufe.csv", encoding="utf-8")
    kur, kur_dusen = kuresel_cek()
    kur_yol = DATA / "kuresel.csv"
    if kur is not None:
        kur.to_csv(kur_yol, encoding="utf-8")
    elif kur_yol.exists():
        # Eski dosyayı BIRAKMAK, bayat sayıyı taze gibi göstermek olurdu.
        kur_yol.unlink()
        uyar("KÜRESEL BLOK ALINAMADI: bu koşuda küresel seriler çekilemedi; "
             "eski tablo silindi (bayat sayı taze gibi yayımlanmaz).")
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
        "pink_sutunlari": _PINK_SUTUNLAR or None,
        "uyarilar": _UYARI,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"── veri yazıldı: {DATA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
