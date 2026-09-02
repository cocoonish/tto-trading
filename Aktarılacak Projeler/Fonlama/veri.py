# -*- coding: utf-8 -*-
"""TCMB fonlama & likidite — veri katmanı (EVDS3).

Ne yapar
--------
1. EVDS3 REST servisinden APİ fonlama/sterilizasyon tablosunu, TCMB
   kotasyonlarını (faiz koridoru + GLP), TLREF ve BİST gecelik repo faizini,
   sterilizasyon ihalesi faiz/tutarlarını, analitik bilançoyu, sistem
   likiditesini, TCMB taraflı swap stoklarını, zorunlu karşılık tabanını ve
   kredi/mevduat faizlerini çeker.
2. Her seriyi TTL'li önbelleğe (data/cache/*.csv) yazar; ağ düşerse ESKİ
   önbelleğe düşer ama SESSİZ kalmaz — uyarı basar, uyarilar.json'a taşınır.
3. `son_gun()` / `son_hafta()` ile analizin dönemini VERİDEN okur
   (sabit tarih YASAK).
4. AİLE BAZLI tazelik denetimi yapar: bu hatta beş ayrı yayım ritmi var
   (APİ aynı gün · analitik bilanço 1 gün · TLREF 1 gün · haftalık faiz 6 gün ·
   ZK tabanı 13 gün · kur −1 gün). Tek eşik her koşuda yanlış alarm üretirdi.
5. Kimlik denetimleri: APİ tablosu ile analitik bilanço aynı günde aynı sayıyı
   vermeli; rezerv para bileşenleri toplamı tutmalı. Tutmuyorsa GÖRÜNÜR uyarı
   düşer ve `veri_durum.json`'a yazılır.

Uç nokta notu
-------------
`evds2.tcmb.gov.tr/service/evds` ÖLÜ. Çalışan uç nokta:

    https://evds3.tcmb.gov.tr/igmevdsms-dis/{endpoint}{param}={deger}&...

Sorgu dizesi `?` ile başlamaz; anahtar URL'de DEĞİL `key:` HTTP başlığında
gider. Tek istek ~1000 SATIRLA sınırlı ve aralığın SONUNDAN geriye dolduruyor,
gerisini uyarı vermeden kırpıyor — iş günü seriler 366 günlük, haftalık seriler
900 haftalık parçalar hâlinde çekilir.

Satır sınırı TARİH sayısına bağlıdır, seri sayısına değil: `series=A-B-C`
biçiminde birden çok seri tek istekte gelir ve satır sayısı değişmez. Bu yüzden
seriler demet hâlinde çekilir (45 iş günü serisi × 16 parça = 720 istek yerine
6 demet × 16 parça = 96 istek).

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
        + " / ".join(str(y) for y in _ADAYLAR))


BASE = "https://evds3.tcmb.gov.tr/igmevdsms-dis"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")

CACHE_TTL_SAAT = 12
DEMET = 6                 # tek istekte kaç seri (satır sınırı seri sayısına bağlı DEĞİL)
PARCA_GUN = 366           # iş günü seriler: yıllık parça
PARCA_HAFTA_GUN = 6300    # haftalık seriler: ~900 hafta

_UYARI: list[str] = []
_ANAHTAR: str | None = None


def uyar(mesaj: str) -> None:
    """Görünür uyarı: ekrana basılır ve uyarilar.json'a taşınır."""
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


def _taze(yol: pathlib.Path, ttl_saat: float) -> bool:
    if not yol.exists():
        return False
    return (dt.datetime.now().timestamp() - yol.stat().st_mtime) / 3600 < ttl_saat


def _yas_gun(yol: pathlib.Path) -> float:
    return (dt.datetime.now().timestamp() - yol.stat().st_mtime) / 86400


# --------------------------------------------------------------------------- ayrıştırıcılar
# ÜÇ ayrı tarih biçimi var ve karıştırılırsa seri sessizce boşalır:
#   İŞ GÜNÜ / HAFTALIK(CUMA) → "20-08-2026"   (aynı ayrıştırıcı)
#   AYLIK                    → "2026-6"
#   ÜÇ AYLIK                 → "2026-Q2"      (bu hatta kullanılmıyor, ama
#                               kalıp kopyalanırken int('Q2') tuzağı buradadır)
def _ayristir(items, kolonlar: list[str], biçim: str) -> pd.DataFrame:
    if not items:
        return pd.DataFrame()
    df = pd.DataFrame(items)
    if "Tarih" not in df.columns:
        return pd.DataFrame()
    if biçim == "gun":
        t = pd.to_datetime(df["Tarih"], format="%d-%m-%Y", errors="coerce")
    elif biçim == "ay":
        t = pd.to_datetime(df["Tarih"], format="%Y-%m", errors="coerce")
    else:
        raise ValueError(f"bilinmeyen biçim: {biçim}")
    out = {}
    for k in kolonlar:
        if k in df.columns:
            out[k] = pd.to_numeric(df[k].replace("", None), errors="coerce")
    if not out:
        return pd.DataFrame()
    d = pd.DataFrame(out)
    d.index = t
    return d[~d.index.isna()].sort_index()


def _url(kodlar: list[str], bas: pd.Timestamp, son: pd.Timestamp) -> str:
    return (f"{BASE}/series={'-'.join(kodlar)}"
            f"&startDate={bas:%d-%m-%Y}&endDate={son:%d-%m-%Y}&type=json")


def _demet_cek(kodlar: list[str], bas: pd.Timestamp, son: pd.Timestamp,
               parca_gun: int, biçim: str) -> pd.DataFrame:
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
            p = _ayristir(items, guvenli, biçim)
        except Exception as ex:
            uyar(f"demet düştü ({', '.join(kodlar)} · {imlec:%m.%Y}–{sonu:%m.%Y}: "
                 f"{ex}); seriler tek tek deneniyor.")
            tekler = []
            for k, g in zip(kodlar, guvenli):
                try:
                    it = _cek(_url([k], imlec, sonu)).get("items", [])
                    d = _ayristir(it, [g], biçim)
                    if len(d):
                        tekler.append(d)
                except Exception as ex2:
                    uyar(f"SERİ ALINAMADI: {k} ({imlec:%m.%Y}–{sonu:%m.%Y}) — {ex2}")
                time.sleep(0.2)
            p = pd.concat(tekler, axis=1) if tekler else pd.DataFrame()
        if len(p):
            parcalar.append(p)
        imlec = sonu + pd.Timedelta(days=1)
        time.sleep(0.2)
    if not parcalar:
        return pd.DataFrame()
    d = pd.concat(parcalar)
    d = d[~d.index.duplicated(keep="last")].sort_index()
    return d


def _cache_yolu(kod: str, biçim: str) -> pathlib.Path:
    return CACHE / f"evds_{biçim}_{kod.replace('.', '_')}.csv"


def cek_kume(kodlar: dict[str, tuple[str, str]], biçim: str, parca_gun: int,
             yenile: bool = False, etiket: str = "") -> pd.DataFrame:
    """Bir seri kümesini (ad → (kod, başlangıç)) çeker ve tek DataFrame verir.

    Önbellek SERİ BAZINDA tutulur (demet değişince önbellek geçersizleşmesin).
    Ağ düşerse ve önbellek varsa GÖRÜNÜR uyarıyla eski önbelleğe düşülür.
    """
    ad_kod = {ad: k for ad, (k, _) in kodlar.items()}
    eksik = [ad for ad in kodlar
             if yenile or not _taze(_cache_yolu(ad_kod[ad], biçim), CACHE_TTL_SAAT)]
    if eksik:
        print(f"  {etiket}: {len(eksik)}/{len(kodlar)} seri EVDS'ten çekiliyor "
              f"({-(-len(eksik) // DEMET)} demet)")
        # Aynı başlangıç tarihini paylaşanları bir arada tut — parça sayısı düşer.
        eksik = sorted(eksik, key=lambda a: kodlar[a][1])
        bugun = pd.Timestamp.today().normalize()
        for i in range(0, len(eksik), DEMET):
            grup = eksik[i:i + DEMET]
            bas = min(pd.Timestamp(kodlar[a][1]) for a in grup)
            d = _demet_cek([ad_kod[a] for a in grup], bas, bugun, parca_gun, biçim)
            for a in grup:
                g = ad_kod[a].replace(".", "_")
                if g in d.columns and d[g].notna().any():
                    s = d[g].dropna()
                    s.name = ad_kod[a]
                    s.to_csv(_cache_yolu(ad_kod[a], biçim))
    out: dict[str, pd.Series] = {}
    for ad, (kod, _) in kodlar.items():
        yol = _cache_yolu(kod, biçim)
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
# SERİ KÜMELERİ — ad: (EVDS kodu, EVDS'te yayımlanan başlangıç)
# Birim tuzağı bu hattın en pahalı hatası: aynı grafikte bin TL ile milyon TL
# karıştırmak "trilyon" ölçeğinde gözle yakalanmaz. Birimler burada, kodun
# yanında yazılıdır ve metrik.py dönüşümü TEK yerde yapar.
# ===========================================================================

# --- İŞ GÜNÜ ---------------------------------------------------------------
GUNLUK: dict[str, tuple[str, str]] = {
    # APİ fonlaması / sterilizasyonu — MİLYON TL, gecikme 0 gün
    "fon_top":        ("TP.APIFON1.TOP",   "2011-01-03"),
    "fon_ihale":      ("TP.APIFON1.IHA",   "2011-01-03"),
    "fon_kot_top":    ("TP.APIFON1.KOT.T", "2011-04-08"),
    "fon_kot_repo":   ("TP.APIFON1.KOT.A", "2011-04-08"),
    "fon_kot_depo":   ("TP.APIFON1.KOT.B", "2011-10-26"),
    "fon_glp":        ("TP.APIFON1.KOT.C", "2015-03-31"),
    "ste_top":        ("TP.APIFON2.TOP",   "2011-01-03"),
    "ste_ihale":      ("TP.APIFON2.IHA",   "2018-01-08"),
    "ste_kot":        ("TP.APIFON2.KOT",   "2011-01-03"),
    "ste_liksen":     ("TP.APIFON2.LIK",   "2025-03-14"),
    "net_fonlama":    ("TP.APIFON3",       "2011-01-03"),
    "aofm":           ("TP.APIFON4",       "2011-01-03"),
    # TCMB kotasyonları — YÜZDE. Politika faizi EVDS'te "politika faizi" adıyla
    # bağımsız GÜNLÜK seri olarak YOK; 1 hafta vadeli repo SATIŞ kotasyonu
    # politika faizidir. ÖLÇÜLDÜ: bu seri 14.09.2018'de BAŞLIYOR — öncesinde
    # TCMB bu vadede kotasyon vermiyor, haftalık repo İHALEYLE fonlanıyordu.
    # Tarihçe için gerçekleşen 1 haftalık işlem faizi (P06.1H) vekil alınır ve
    # örtüşme penceresinde sınanır (metrik.py · dogrulama).
    "politika":       ("TP.PY.P02.1H",  "2011-01-03"),
    "politika_ger":   ("TP.PY.P06.1H",  "2011-01-03"),
    "koridor_alt":    ("TP.PY.P01.ON",  "2011-01-03"),
    "koridor_ust":    ("TP.PY.P02.ON",  "2011-01-03"),
    "glp_satis":      ("TP.PY.P02.LON", "2011-01-03"),
    "glp_alis":       ("TP.PY.P01.LON", "2011-01-03"),
    # Piyasa gecelik faizleri — YÜZDE / hacim BİN TL
    "tlref":          ("TP.BISTTLREF.ORAN",    "2018-12-28"),
    "tlref_endeks":   ("TP.BISTTLREF.KAPANIS", "2019-06-14"),
    "bist_on":        ("TP.AOFOBAP", "2018-12-27"),
    "bist_on_hacim":  ("TP.IHBAP",   "2018-12-27"),
    # Sterilizasyon ihaleleri — faiz YÜZDE, tutar BİN TL (AOFM'nin aynası AOSM)
    "sto_oni_faiz":   ("TP.PY.P06.ONI", "2024-05-09"),
    "sto_oni_tutar":  ("TP.PY.P07.ONI", "2024-05-09"),
    "sto_1hi_faiz":   ("TP.PY.P06.1HI", "2011-01-03"),
    "sto_1hi_tutar":  ("TP.PY.P07.1HI", "2011-01-03"),
    "sto_kvi_faiz":   ("TP.PY.P06.KVI", "2024-05-14"),
    "sto_kvi_tutar":  ("TP.PY.P07.KVI", "2024-05-14"),
    "sto_4hi_faiz":   ("TP.PY.P06.4HI", "2011-01-03"),
    "sto_4hi_tutar":  ("TP.PY.P07.4HI", "2011-01-03"),
    # Sistem likiditesi — MİLYON TL
    "serbest_mevduat":   ("TP.PPIBSM",  "2011-01-03"),
    "gun_basi_likidite": ("TP.PPIGBTL", "2011-01-03"),
    # Analitik bilanço — BİN TL, gecikme 1 gün
    "ab_dis_varlik":  ("TP.AB.A02", "2011-01-03"),
    "ab_ic_varlik":   ("TP.AB.A03", "2011-01-03"),
    "ab_mbp":         ("TP.AB.A15", "2011-01-03"),
    "ab_rezerv_para": ("TP.AB.A16", "2011-01-03"),
    "ab_emisyon":     ("TP.AB.A17", "2011-01-03"),
    "ab_bankalar":    ("TP.AB.A18", "2011-01-03"),
    "ab_zk_bloke":    ("TP.AB.A19", "2011-01-03"),
    "ab_serbest":     ("TP.AB.A20", "2011-01-03"),
    "ab_fon":         ("TP.AB.A21", "2011-01-03"),
    "ab_bankadisi":   ("TP.AB.A22", "2011-01-03"),
    "ab_diger_mbp":   ("TP.AB.A23", "2011-01-03"),
    "ab_api":         ("TP.AB.A24", "2011-01-03"),
    "ab_kamu_mev":    ("TP.AB.A25", "2011-01-03"),
    # TCMB taraflı swap — MİLYON USD, gecikme 0
    "swap_alim":        ("TP.SWAPTEKTAR.TOTALSTOKALIMYONLU",   "2021-01-04"),
    "swap_satim":       ("TP.SWAPTEKTAR.TOTALSTOKSATIMYONLU",  "2021-01-04"),
    "swap_tcmb_piy":    ("TP.SWAPTEKTAR.SWAPKSTOKUSDTUTAR",    "2021-01-04"),
    "swap_bist":        ("TP.SWAPTEKTAR.BISWAPSTOKUSDTUTAR",   "2021-01-04"),
    "swap_gelenek":     ("TP.SWAPTEKTAR.SWAPPALIMSTOKUSDTUTAR", "2021-01-04"),
    "swap_miktar":      ("TP.SWAPTEKTAR.SWAPMSTOKUSDTUTAR",    "2021-01-04"),
    "swap_altin_piy":   ("TP.SWAPTEKTAR.SWAPASTOKUSDTUTAR",    "2021-01-04"),
    "swap_altin_ihale": ("TP.SWAPTEKTAR.SWAPXALIMSTOKUSDTUTAR", "2021-01-04"),
    # Kur — swap stokunun TL karşılığı için. Gecikme −1 gün (TCMB ertesi günün
    # kurunu bir gün önce ilan eder); tazelik denetimi bunu alarm saymaz.
    "usdtry": ("TP.DK.USD.A.YTL", "2011-01-03"),
}

# --- HAFTALIK(CUMA) --------------------------------------------------------
# 2013 başlangıcı bilinçli: 2005'ten çekilirse 1080 satır olur ve EVDS 1000'de
# sessizce kırpar (serinin BAŞI kesilir, uyarı gelmez).
HAFTALIK: dict[str, tuple[str, str]] = {
    # ZK'ya tabi taban, gecikme 13 gün. BİRİMLER AYNI DEĞİLDİR — bu tablo iki
    # ayrı veri grubundan besleniyor ve grupların ölçeği farklı:
    #   bie_tldthvade (TP.TLDTHVADE.*)  → BİN TL
    #   bie_zorundth  (TP.ZORUNDTH.*)   → MİLYON TL / MİLYON USD
    # Kanıt: TP.TLDTHVADE.KB12 (bin TL) tam olarak TP.ZORUNDTH.KB8 × 1000'dir.
    # İki grubu birimi çevirmeden toplamak DTH bacağını 1000 kat küçültür;
    # metrik.py'de bunu yakalayan bir birim denetimi vardır.
    "zk_taban_tl":     ("TP.TLDTHVADE.KB6",  "2013-01-04"),   # BİN TL   (TL mevduat tabanı)
    "zk_taban_dth":    ("TP.TLDTHVADE.KB12", "2013-01-04"),   # BİN TL   (DTH tabanı)
    "zk_taban_toplam": ("TP.TLDTHVADE.KB18", "2013-01-04"),   # BİN TL   (TL + DTH toplamı)
    "dth_usd":         ("TP.ZORUNDTH.KB7",   "2013-01-04"),   # MİLYON USD
    "dth_tl":          ("TP.ZORUNDTH.KB8",   "2013-01-04"),   # MİLYON TL
    "katilim_tl":      ("TP.KYBKATFON.KB1",  "2013-01-04"),   # BİN TL
    "katilim_yp_usd":  ("TP.KYBKATFON.KB6",  "2013-01-04"),   # MİLYON USD
    # Kredi / mevduat faizleri (akım, yıllıklandırılmış) — YÜZDE, gecikme 6 gün
    "f_ticari_tl":   ("TP.KTF17",     "2013-01-04"),
    "f_tuketici":    ("TP.KTFTUK",    "2013-01-04"),
    "f_ihtiyac":     ("TP.KTF10",     "2013-01-04"),
    "f_konut":       ("TP.KTF12",     "2013-01-04"),
    "f_mevduat_tl":  ("TP.TRY.MT06",  "2013-01-04"),
    "f_mevduat_3a":  ("TP.TRY.MT02",  "2013-01-04"),
}

# --- AYLIK (yalnız BAĞIMSIZ DOĞRULAMA için) --------------------------------
# Bunlar grafiğe girmez; hesapladığımız günlük serilerin EVDS'in kendi aylık
# yayımıyla tutup tutmadığını sınamak için çekilir.
AYLIK: dict[str, tuple[str, str]] = {
    "bis_politika":   ("TP.BISPOLFAIZ.TUR",    "2011-01-01"),
    "api_repo_ort":   ("TP.API.REP.ORT.G1",    "2011-01-01"),
    "api_trepo_ort":  ("TP.API.TREP.ORT.G1",   "2011-01-01"),
}

# --------------------------------------------------------------------------- tazelik
# (etiket, tolerans TAKVİM GÜNÜ, negatif gecikme muaf mı)
# Referans DUVAR SAATİDİR: verinin kendi son gününü referans almak denetimi
# kendi kendine referanslı hâle getirir ("son gözlem bugün, demek ki taze").
TAZELIK_GUNLUK = {
    "net_fonlama":  ("APİ fonlaması (TP.APIFON3)",            4, False),
    "aofm":         ("AOFM (TP.APIFON4)",                     4, False),
    "politika":     ("TCMB kotasyonları (TP.PY.P02.1H)",      4, False),
    "tlref":        ("TLREF (TP.BISTTLREF.ORAN)",             5, False),
    "ab_api":       ("Analitik bilanço (TP.AB.A24)",          5, False),
    "serbest_mevduat": ("Sistem likiditesi (TP.PPIBSM)",      4, False),
    "swap_alim":    ("Swap stoku (TP.SWAPTEKTAR.*)",          4, False),
    "usdtry":       ("Döviz kuru (TP.DK.USD.A.YTL)",          4, True),
}
TAZELIK_HAFTALIK = {
    "f_ticari_tl":  ("Haftalık kredi faizi (bie_kt100h)",     12),
    "f_mevduat_tl": ("Haftalık mevduat faizi (bie_mt100h)",   12),
    "zk_taban_tl":  ("ZK'ya tabi taban (bie_tldthvade)",      20),
    "dth_tl":       ("ZK'ya tabi DTH (bie_zorundth)",         20),
}

def tazelik_tolerans(aile: str = "gunluk") -> int:
    """Bu ailedeki EN SIKI tolerans (takvim günü).

    ozet_uret.py bayat bayrağını buradan okur; eşik iki yerde ayrı ayrı
    yazılırsa biri güncellenip öteki unutulur ve bayatlık sessizce kaçar.
    """
    if aile == "gunluk":
        return min(t for _, t, _ in TAZELIK_GUNLUK.values())
    return min(t for _, t in TAZELIK_HAFTALIK.values())


AY_TR = {1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
         7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım",
         12: "Aralık"}
AY_KISA = {1: "Oca", 2: "Şub", 3: "Mar", 4: "Nis", 5: "May", 6: "Haz",
           7: "Tem", 8: "Ağu", 9: "Eyl", 10: "Eki", 11: "Kas", 12: "Ara"}


def gun_ad(t) -> str:
    t = pd.Timestamp(t)
    return f"{t.day} {AY_TR[t.month]} {t.year}"


def kisa_ad(t) -> str:
    t = pd.Timestamp(t)
    return f"{AY_KISA[t.month]}-{str(t.year)[2:]}"


# --------------------------------------------------------------------------- dönem
_SON: dict[str, str] = {}


def son_gun(gunluk: pd.DataFrame | None = None) -> pd.Timestamp:
    """Analizin güncel iş günü: APİ ÇEKİRDEĞİNİN tamamının bulunduğu son gün.

    Sabit tarih YASAK. Kur serisi bilinçli DIŞARIDA: TCMB ertesi günün kurunu
    bir gün önce ilan ediyor, çekirdeğe alınsaydı dönem bir gün ileri kayardı.
    Analitik bilanço da dışarıda: bir gün geriden geliyor.
    """
    if "gun" in _SON:
        return pd.Timestamp(_SON["gun"])
    if gunluk is None:
        gunluk = pd.read_csv(VERI / "gunluk.csv", index_col=0, parse_dates=True)
    cekirdek = [c for c in ("net_fonlama", "fon_top", "ste_top", "politika",
                            "koridor_alt", "koridor_ust") if c in gunluk.columns]
    tam = gunluk[cekirdek].dropna(how="any")
    if tam.empty:
        raise RuntimeError("son_gun: APİ serileri boş — EVDS çekimi düşmüş olabilir.")
    _SON["gun"] = tam.index[-1].strftime("%Y-%m-%d")
    return tam.index[-1]


def son_hafta(haftalik: pd.DataFrame | None = None) -> pd.Timestamp:
    """Haftalık faiz ailesinin son dolu Cuma'sı (ZK tabanı bir hafta geriden
    geldiği için çekirdeğe alınmaz — alınsaydı dönem iki hafta geriye düşerdi)."""
    if "hafta" in _SON:
        return pd.Timestamp(_SON["hafta"])
    if haftalik is None:
        haftalik = pd.read_csv(VERI / "haftalik.csv", index_col=0, parse_dates=True)
    cekirdek = [c for c in ("f_ticari_tl", "f_mevduat_tl") if c in haftalik.columns]
    tam = haftalik[cekirdek].dropna(how="any")
    if tam.empty:
        raise RuntimeError("son_hafta: haftalık faiz serileri boş.")
    _SON["hafta"] = tam.index[-1].strftime("%Y-%m-%d")
    return tam.index[-1]


# --------------------------------------------------------------------------- denetimler
def tazelik_denetimi(g: pd.DataFrame, h: pd.DataFrame) -> list[str]:
    bugun = pd.Timestamp.today().normalize()
    uy: list[str] = []
    for ad, (etiket, tol, negatif_muaf) in TAZELIK_GUNLUK.items():
        if ad not in g.columns or g[ad].dropna().empty:
            uy.append(f"TAZELİK: '{etiket}' hiç yüklenemedi.")
            continue
        son = g[ad].dropna().index[-1]
        gecikme = (bugun - son).days
        if gecikme < 0 and negatif_muaf:
            continue          # kur: ertesi günün kuru bugünden ilan edilir
        if gecikme > tol:
            uy.append(f"TAZELİK: {etiket} son gözlemi {son:%d.%m.%Y} "
                      f"({gecikme} gün önce, tolerans {tol} gün). "
                      "Yayın durmuş olabilir.")
    for ad, (etiket, tol) in TAZELIK_HAFTALIK.items():
        if ad not in h.columns or h[ad].dropna().empty:
            uy.append(f"TAZELİK: '{etiket}' hiç yüklenemedi.")
            continue
        son = h[ad].dropna().index[-1]
        gecikme = (bugun - son).days
        if gecikme > tol:
            uy.append(f"TAZELİK: {etiket} son gözlemi {son:%d.%m.%Y} "
                      f"({gecikme} gün önce, tolerans {tol} gün).")
    return uy


def kimlik_denetimi(g: pd.DataFrame) -> tuple[list[str], dict]:
    """Birim ve hizalama denetimleri. Bunlar formül denetimidir, tazelik değil.

    (1) APİ tablosu ile analitik bilanço AYNI günde AYNI sayıyı vermeli:
        TP.AB.A24 (bin TL) / 1000  =  −TP.APIFON3 (milyon TL).
        Pasifte pozitif APİ kalemi = TCMB'nin piyasaya borçlu olması =
        sterilizasyon; işaret bu yüzden ters.
    (2) TP.APIFON3 = TP.APIFON1.TOP − TP.APIFON2.TOP.
    (3) Rezerv para kimliği: A16 = A17 + A18 + A21 + A22.
    (4) Bankalar mevduatı: A18 = A19 + A20.
    (5) MB parası: A15 = A16 + A24 + A25  (A23 = A24 + A25).
    """
    uy: list[str] = []
    rapor: dict = {}

    def _kimlik(ad: str, sol: pd.Series, sag: pd.Series, olcek: pd.Series,
                esik_bagil: float, birim: str):
        d = pd.DataFrame({"s": sol, "r": sag, "o": olcek}).dropna()
        if d.empty:
            uy.append(f"KİMLİK: '{ad}' sınanamadı — girdi serileri kesişmiyor.")
            return
        fark = (d["s"] - d["r"]).abs()
        bagil = fark / d["o"].abs().clip(lower=1e-9)
        rapor[ad] = {
            "n": int(len(d)),
            "maks_fark": float(fark.max()),
            "maks_bagil": float(bagil.max()),
            "maks_tarih": str(bagil.idxmax().date()),
            "son_fark": float(fark.iloc[-1]),
            "birim": birim,
            "esik_bagil": esik_bagil,
            "gecti": bool(bagil.max() <= esik_bagil),
        }
        if bagil.max() > esik_bagil:
            uy.append(
                f"KİMLİK BOZUK: {ad} — en büyük sapma {fark.max():,.1f} {birim} "
                f"({bagil.max() * 100:.4f}%, {bagil.idxmax():%d.%m.%Y}); eşik "
                f"{esik_bagil * 100:.4f}%. Birim dönüşümü ya da kalem "
                "numaralandırması değişmiş olabilir.")

    if {"ab_api", "net_fonlama"} <= set(g.columns):
        # BİRİM KİMLİĞİ. Analitik bilanço bin TL, APİ tablosu milyon TL; pasifte
        # pozitif APİ kalemi TCMB'nin piyasaya borçlu olması, yani sterilizasyon
        # demektir — işaret ters. İkisi bağımsız yayımlanır; ÖLÇÜLDÜ: son
        # gözlemlerde artık tam sıfır, ama tarihçede sıfır DEĞİL.
        #
        # Artığın kaynağı birim değil KAPSAM: analitik bilançonun APİ kalemi
        # işlemiş faiz ve APİ tablosunda ayrı gösterilmeyen kalemleri de
        # taşıyor. Bu yüzden denetim iki katmanlıdır:
        #   (a) SON PENCERE (250 iş günü) — hattı DURDURAN eşik. Burada artık
        #       küçük kalmalı; büyürse birim/hizalama gerçekten bozulmuştur.
        #   (b) TAM TARİHÇE — yalnız TANI olarak raporlanır. 2017–18 ve 2022–23
        #       fonlama rejimlerinde birkaç bin milyon TL'lik kalıcı artık var
        #       ve bu bir hata değil, kapsam farkıdır; hattı durdurmak yanlış
        #       alarm olurdu.
        d = pd.DataFrame({"a": g["ab_api"] / 1000.0,
                          "b": -g["net_fonlama"]}).dropna()
        if d.empty:
            uy.append("KİMLİK: 'A24/1000 = −APIFON3' sınanamadı.")
        else:
            fark = (d["a"] - d["b"]).abs()
            olcek = max(float(d["a"].abs().median()), 1.0)
            son = fark.iloc[-250:]
            son_olcek = max(float(d["a"].abs().iloc[-250:].median()), 1.0)
            bagil = float(son.max()) / son_olcek
            rapor["A24/1000 = −APIFON3"] = {
                "n": int(len(d)), "n_pencere": int(len(son)),
                "maks_fark": float(fark.max()),
                "maks_tarih": str(fark.idxmax().date()),
                "pencere_maks_fark": float(son.max()),
                "pencere_maks_bagil": bagil,
                "pencere_olcek_medyan": son_olcek,
                "tam_ortalama_mutlak": float(fark.mean()),
                "son_fark": float(fark.iloc[-1]),
                "birim": "mn TL", "esik_bagil": 0.01,
                "gecti": bool(bagil <= 0.01),
                "not": ("artık kapsam farkıdır (bilançonun APİ kalemi işlemiş "
                        "faizi de taşır); eşik son 250 iş gününe uygulanır"),
            }
            if bagil > 0.01:
                uy.append(
                    f"KİMLİK BOZUK: A24/1000 = −APIFON3 — son 250 iş gününde "
                    f"en büyük artık {son.max():,.1f} mn TL (tipik APİ "
                    f"büyüklüğünün %{bagil * 100:.2f}'i, eşik %1). Birim "
                    "dönüşümü ya da tarih hizalaması bozulmuş olabilir.")
            elif fark.max() > 20 * olcek * 0.01:
                pass   # tarihçedeki kapsam artığı: raporda var, uyarı değil
    if {"net_fonlama", "fon_top", "ste_top"} <= set(g.columns):
        _kimlik("APIFON3 = A − B", g["net_fonlama"], g["fon_top"] - g["ste_top"],
                g["ste_top"].clip(lower=1), 1e-6, "mn TL")
    if {"ab_rezerv_para", "ab_emisyon", "ab_bankalar", "ab_fon",
            "ab_bankadisi"} <= set(g.columns):
        _kimlik("A16 = A17+A18+A21+A22", g["ab_rezerv_para"],
                g["ab_emisyon"] + g["ab_bankalar"] + g["ab_fon"] + g["ab_bankadisi"],
                g["ab_rezerv_para"], 1e-6, "bin TL")
    if {"ab_bankalar", "ab_zk_bloke", "ab_serbest"} <= set(g.columns):
        _kimlik("A18 = A19+A20", g["ab_bankalar"],
                g["ab_zk_bloke"] + g["ab_serbest"], g["ab_bankalar"], 1e-6, "bin TL")
    if {"ab_mbp", "ab_rezerv_para", "ab_api", "ab_kamu_mev"} <= set(g.columns):
        _kimlik("A15 = A16+A24+A25", g["ab_mbp"],
                g["ab_rezerv_para"] + g["ab_api"] + g["ab_kamu_mev"],
                g["ab_mbp"], 1e-6, "bin TL")
    return uy, rapor


def olu_seri_denetimi(g: pd.DataFrame) -> list[str]:
    """SIFIR ≠ VERİ.

    `TP.PY.P01.1H` (1 hafta ALIŞ kotasyonu) ve `TP.PY.P01.LON` (GLP alış)
    yıllardır 0,00 basıyor: bu bir faiz oranı değil, "bu yönde kotasyon
    verilmiyor" demektir. Sıfırı grafiğe basmak koridor bandını tabana çeker.
    Burada yalnız RAPORLANIR; NaN'a çevirme metrik.py'de, tek yerde yapılır.
    """
    uy: list[str] = []
    # Okura sütun adı değil okur adı gider (koşu kutusu bu satırı olduğu gibi basar).
    OKUR_ADI = {"glp_alis": "geç likidite penceresi alış faizi",
                "fon_ihale": "ihale fonlaması",
                "ste_liksen": "likidite senedi sterilizasyonu"}
    for ad in ("glp_alis", "fon_ihale", "ste_liksen"):
        if ad not in g.columns:
            continue
        s = g[ad].dropna()
        if s.empty:
            continue
        son252 = s.iloc[-252:]
        if len(son252) and (son252 == 0).all():
            uy.append(f"ÖLÜ SERİ: {OKUR_ADI.get(ad, ad)} son {len(son252)} iş gününün "
                      "TAMAMINDA 0 — dolu görünüyor ama bilgi taşımıyor; "
                      "grafikte 'yok' olarak işlenecek.")
    return uy


# --------------------------------------------------------------------------- ana akış
def kos(yenile: bool = False) -> dict:
    print("EVDS3 → TCMB fonlama & likidite veri katmanı")
    print(f"  anahtar: {'ortam değişkeni' if os.environ.get('TTO_EVDS_KEY') else 'dosya'}")

    g = cek_kume(GUNLUK, "gun", PARCA_GUN, yenile, etiket="iş günü")
    h = cek_kume(HAFTALIK, "gun", PARCA_HAFTA_GUN, yenile, etiket="haftalık")
    a = cek_kume(AYLIK, "ay", 20000, yenile, etiket="aylık (doğrulama)")

    s_gun = son_gun(g)
    s_hafta = son_hafta(h) if not h.empty else None
    print(f"  SON İŞ GÜNÜ : {gun_ad(s_gun)}")
    if s_hafta is not None:
        print(f"  SON HAFTA   : {gun_ad(s_hafta)} (Cuma)")

    for u in tazelik_denetimi(g, h):
        uyar(u)
    kim_uy, kim_rapor = kimlik_denetimi(g)
    for u in kim_uy:
        uyar(u)
    for u in olu_seri_denetimi(g):
        uyar(u)

    g.to_csv(VERI / "gunluk.csv")
    h.to_csv(VERI / "haftalik.csv")
    a.to_csv(VERI / "aylik.csv")

    durum = {
        "kosum": dt.date.today().isoformat(),
        "son_gun": s_gun.strftime("%Y-%m-%d"),
        "son_hafta": s_hafta.strftime("%Y-%m-%d") if s_hafta is not None else None,
        "gunluk_seri": int(g.shape[1]), "gunluk_gozlem": int(g.shape[0]),
        "haftalik_seri": int(h.shape[1]), "haftalik_gozlem": int(h.shape[0]),
        "aylik_seri": int(a.shape[1]),
        "kimlik": kim_rapor,
        "uyarilar": list(_UYARI),
    }
    (VERI / "veri_durum.json").write_text(
        json.dumps(durum, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  yazıldı: data/gunluk.csv ({g.shape[0]}x{g.shape[1]}), "
          f"data/haftalik.csv ({h.shape[0]}x{h.shape[1]}), "
          f"data/aylik.csv ({a.shape[0]}x{a.shape[1]})")
    for ad, r in kim_rapor.items():
        print(f"    kimlik {'✓' if r['gecti'] else '✗'} {ad}: "
              f"n={r['n']}, maks {r['maks_fark']:,.3f} {r['birim']}")
    if _UYARI:
        print(f"\n[{len(_UYARI)} uyarı]")
    return durum


if __name__ == "__main__":
    kos(yenile="--yenile" in sys.argv)
