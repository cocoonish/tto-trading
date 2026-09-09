# -*- coding: utf-8 -*-
"""Kredi & parasal büyüklükler — veri katmanı (EVDS3).

Ne yapar
--------
1. EVDS3'ten dört ayrı frekansta seri çeker:
   · HAFTALIK (Cuma)  — Haftalık Para ve Banka İstatistikleri (bie_hpbitablo1…7),
     para arzı endeksleri, kredi/mevduat faizleri (bie_kt100h,
     bie_mt100h, bie_kt200h), kart harcaması, zorunlu karşılık tabanı;
     ayrıca 31.01.2025'te kapanan ARŞİV tabloları — uzun tarihçe için.
   · İŞ GÜNÜ         — kur, analitik bilanço,
     APİ fonlaması/AOFM, politika faizi kotasyonları.
   · AYLIK           — KKM stoku, banka türüne göre krediler, beklenti anketi.
   · ÜÇ AYLIK        — Banka Kredileri Eğilim Anketi.
2. Her seriyi TTL'li önbelleğe (data/cache/*.csv) yazar; ağ düşerse ESKİ
   önbelleğe düşer ama SESSİZ kalmaz — uyarı basar, uyarilar.json'a taşınır.
3. Dönem sabitlerini VERİDEN okur: son_hafta(), son_gun(), son_ay(), son_ceyrek().
   Koda sabit tarih YAZILMAZ.
4. AİLE BAZLI tazelik denetimi yapar. Bu hatta beş ayrı yayım ritmi var
   (APİ aynı gün · analitik bilanço 1 gün · haftalık 6 gün · ZK tabanı 13 gün ·
   aylık 51 gün); tek eşik her koşuda ya yanlış alarm ya sessiz kabul üretir.
5. Yapısal (kimlik) denetimleri yapar ve bozulanı uyarıya çevirir.

EVDS3 tuzakları (ölçülerek doğrulandı, kalıp Enflasyon hattından)
----------------------------------------------------------------
· `evds2.tcmb.gov.tr/service/evds` ÖLÜ. Çalışan uç nokta
  `https://evds3.tcmb.gov.tr/igmevdsms-dis/…`; sorgu `?` ile başlamaz,
  anahtar URL'de DEĞİL `key:` BAŞLIĞINDA gider.
· Tek istek ~1000 satır döndürüyor ve aralığın SONUNDAN geriye dolduruyor,
  gerisini UYARI VERMEDEN kırpıyor. İş günü serileri 366 günlük, haftalık
  seriler 900 haftalık parçalara bölünür.
· Dört ayrı tarih biçimi: iş günü/haftalık "DD-MM-YYYY", aylık "YYYY-M",
  üç aylık "YYYY-Qn". BKEA'yı aylık ayrıştırıcıya vermek int('Q2') ile düşer.
· Yanıt kolonu = seri kodunun noktaları alt çizgiye çevrilmiş hâli.
· EVDS'in `LAST_UPDATED` alanı TAZELİK ÖLÇÜSÜ DEĞİLDİR (metaveri kaydının
  güncellenme tarihi). Tazelik yalnız son DOLU gözlemden okunur.

Koşum:  python3 veri.py  [--yenile]
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import time
import urllib.request

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------- yollar
PROJE = pathlib.Path(__file__).resolve().parent
KOK = PROJE.parent.parent                      # …/TTO Trading
VERI = PROJE / "data"
CACHE = VERI / "cache"
for _p in (VERI, CACHE):
    _p.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------- anahtar
# EVDS anahtarı kaynak koda GÖMÜLMEZ. Arama sırası (bu projeye KOPYALANMAZ):
#   TTO_EVDS_KEY ortam değişkeni → <proje>/.evds_key → kök/.evds_key
#   → kardeş Aktarılacak Projeler/TCMBNetRezerv/.evds_key
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
KATALOG_TTL_SAAT = 168

_UYARI: list[str] = []
_ANAHTAR: str | None = None


def uyar(mesaj: str) -> None:
    """Görünür uyarı: ekrana basılır ve uyarilar.json'a taşınır."""
    if mesaj not in _UYARI:
        _UYARI.append(mesaj)
    print("  ! " + mesaj, flush=True)


def uyarilar() -> list[str]:
    return list(_UYARI)


def anahtar() -> str:
    global _ANAHTAR
    if _ANAHTAR is None:
        _ANAHTAR = _evds_anahtari()
    return _ANAHTAR


def _cek(url: str, deneme: int = 3):
    son_hata: Exception | None = None
    for i in range(deneme):
        try:
            req = urllib.request.Request(
                url, headers={"key": anahtar(), "User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as ex:
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


# --------------------------------------------------------------------------- ayrıştırıcılar
def _sayi(df: pd.DataFrame, kolon: str) -> pd.Series:
    return pd.to_numeric(df[kolon].replace("", None), errors="coerce")


def _ayristir_gunluk(items, kolon) -> pd.Series:
    """İŞ GÜNÜ ve HAFTALIK(CUMA) serilerin ortak biçimi: 'DD-MM-YYYY'."""
    df = pd.DataFrame(items)
    if kolon not in df.columns or "Tarih" not in df.columns:
        return pd.Series(dtype=float)
    s = _sayi(df, kolon)
    s.index = pd.to_datetime(df["Tarih"], format="%d-%m-%Y", errors="coerce")
    return s.dropna().sort_index()


def _ayristir_aylik(items, kolon) -> pd.Series:
    """AYLIK: 'YYYY-M' (ay sıfırsız olabilir)."""
    df = pd.DataFrame(items)
    if kolon not in df.columns or "Tarih" not in df.columns:
        return pd.Series(dtype=float)
    s = _sayi(df, kolon)
    s.index = pd.to_datetime(df["Tarih"], format="%Y-%m", errors="coerce")
    return s.dropna().sort_index()


_CEYREK_AY = {"1": 1, "2": 4, "3": 7, "4": 10}


def _ayristir_ceyrek(items, kolon) -> pd.Series:
    """ÜÇ AYLIK: 'YYYY-Qn'. Aylık ayrıştırıcıya verilirse int('Q2') ile düşer;
    BKEA'nın tamamı bu tuzağa giriyor — ayrı ayrıştırıcı zorunlu.
    Çeyrek, ÇEYREĞİN İLK AYINA damgalanır (2026-Q2 → 2026-04-01)."""
    df = pd.DataFrame(items)
    if kolon not in df.columns or "Tarih" not in df.columns:
        return pd.Series(dtype=float)
    s = _sayi(df, kolon)
    idx = []
    for t in df["Tarih"].astype(str):
        try:
            yil, ceyrek = t.split("-Q")
            idx.append(pd.Timestamp(int(yil), _CEYREK_AY[ceyrek.strip()], 1))
        except Exception:
            idx.append(pd.NaT)
    s.index = pd.DatetimeIndex(idx)
    return s.dropna().sort_index()


AYRISTIR = {"gun": _ayristir_gunluk, "hafta": _ayristir_gunluk,
            "ay": _ayristir_aylik, "ceyrek": _ayristir_ceyrek}
# Parça uzunlukları — EVDS'in ~1000 satırlık sessiz kırpması için.
# İŞ GÜNÜ: 366 gün (~250 satır). HAFTALIK: 900 hafta (~900 satır, sınırın altında).
# Aylık/üç aylık seriler zaten 250–500 satır; tek istekte tam geliyor.
PARCA_GUN = {"gun": 366, "hafta": 900 * 7, "ay": 0, "ceyrek": 0}
BAS_VARSAYILAN = {"gun": "01-01-2011", "hafta": "01-01-2005",
                  "ay": "01-01-2005", "ceyrek": "01-01-2005"}


def evds(kod: str, frekans: str = "hafta", bas: str | None = None,
         yenile: bool = False) -> pd.Series:
    """Tek seri. TTL'li önbellek; ağ hatasında eski önbelleğe GÖRÜNÜR uyarıyla
    düşer (çevrimdışı koşu çalışır ama sessiz kalmaz)."""
    if frekans not in AYRISTIR:
        raise ValueError(f"bilinmeyen frekans: {frekans}")
    guvenli = kod.replace(".", "_")
    cyol = CACHE / f"{frekans}_{guvenli}.csv"
    if _taze(cyol, CACHE_TTL_SAAT) and not yenile:
        s = pd.read_csv(cyol, index_col=0, parse_dates=True).iloc[:, 0]
        s.name = kod
        return s
    bas = bas or BAS_VARSAYILAN[frekans]
    ayr = AYRISTIR[frekans]
    parca_gun = PARCA_GUN[frekans]
    t0 = pd.to_datetime(bas, dayfirst=True)
    # Bitiş İLERİ atılır: kur serisi ertesi günün kurunu bir gün önce ilan eder
    # (negatif gecikme); "bugün" ile kesmek o gözlemi düşürürdü.
    t1 = pd.Timestamp.today().normalize() + pd.Timedelta(days=10)
    try:
        if parca_gun <= 0:
            url = (f"{BASE}/series={kod}&startDate={t0:%d-%m-%Y}"
                   f"&endDate={t1:%d-%m-%Y}&type=json")
            s = ayr(_cek(url).get("items", []), guvenli)
        else:
            parcalar: list[pd.Series] = []
            imlec = t0
            while imlec <= t1:
                sonu = min(imlec + pd.Timedelta(days=parca_gun - 1), t1)
                url = (f"{BASE}/series={kod}&startDate={imlec:%d-%m-%Y}"
                       f"&endDate={sonu:%d-%m-%Y}&type=json")
                p = ayr(_cek(url).get("items", []), guvenli)
                if len(p):
                    parcalar.append(p)
                imlec = sonu + pd.Timedelta(days=1)
                time.sleep(0.15)
            if not parcalar:
                raise RuntimeError("boş yanıt")
            s = pd.concat(parcalar)
            s = s[~s.index.duplicated(keep="last")].sort_index()
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
    time.sleep(0.15)
    return s


def seri_listesi(grup: str, yenile: bool = False) -> pd.DataFrame:
    """Bir veri grubunun seri kataloğu. Haftalık TTL — ağaç sık değişmez."""
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
                 f"({_yas_gun(cyol):.0f} gün eski).")
            kayit = json.loads(cyol.read_text(encoding="utf-8"))
        else:
            raise
    return pd.DataFrame(kayit)


# ===========================================================================
#  SERİ KÜMELERİ — kodlar seri kataloğundan (Çıpa: kataloğun çekildiği koşu)
#  doğrulanmıştır. Birim her blokta yazılıdır; bu hattın en sinsi hata kaynağı
#  birimdir (bin TL / milyon TL / milyon USD / milyar USD aynı sayfada).
# ===========================================================================

# --- HAFTALIK (Cuma), bie_hpbitablo2 — sektör bilançosu, birim: bin TL ------
H_BILANCO = {
    "mevduat_toplam":  "TP.HPBITABLO2.1",    # 1. Toplam mevduat
    "mevduat_yi":      "TP.HPBITABLO2.2",    # 1.1 Yurt içi yerleşikler
    "mevduat_tl":      "TP.HPBITABLO2.3",    # 1.1.1 TL
    "mevduat_yp":      "TP.HPBITABLO2.6",    # 1.1.2 YP (TL karşılığı)
    "mevduat_yp_usd":  "TP.HPBITABLO2.10",   # 1.1.2.i YP (milyon USD) ← BİRİM FARKLI
    "kredi_toplam":    "TP.HPBITABLO2.22",   # 2. Toplam kredi
    "kredi_yi":        "TP.HPBITABLO2.23",   # 2.1 Yurt içi yerleşikler
    "kredi_tl":        "TP.HPBITABLO2.24",   # 2.1.1 TL          ← arındırmanın TL bacağı
    "kredi_tuk_tl":    "TP.HPBITABLO2.25",   # 2.1.1.a Tüketici (TL)
    "kredi_tic_tl":    "TP.HPBITABLO2.26",   # 2.1.1.b Ticari (TL)
    "kredi_yp":        "TP.HPBITABLO2.28",   # 2.1.2 YP          ← arındırmanın YP bacağı
    "kredi_tic_yp":    "TP.HPBITABLO2.30",   # 2.1.2.b Ticari (YP)
    "takip_toplam":    "TP.HPBITABLO2.38",   # 3. Takipteki alacaklar
    "takip_tl":        "TP.HPBITABLO2.39",
    "takip_yp":        "TP.HPBITABLO2.40",
    "menkul":          "TP.HPBITABLO2.44",   # 5. Menkul değerler
}

# --- HAFTALIK, bie_hpbitablo6 — kredi kırılımı (yurt içi şubeler), bin TL ---
H_KREDI = {
    "k_yi_toplam":   "TP.HPBITABLO6.1",
    "k_tuketici":    "TP.HPBITABLO6.2",
    "k_konut":       "TP.HPBITABLO6.3",
    "k_tasit":       "TP.HPBITABLO6.7",
    "k_ihtiyac":     "TP.HPBITABLO6.11",
    "k_bkk":         "TP.HPBITABLO6.16",   # bireysel kredi kartları
    "k_fkdk":        "TP.HPBITABLO6.19",   # finansal kesim dışı kuruluşlar
    "k_ticari":      "TP.HPBITABLO6.20",
    "k_ticari_tl":   "TP.HPBITABLO6.21",
    "k_kobi_tl":     "TP.HPBITABLO6.25",
    "k_ticari_yp":   "TP.HPBITABLO6.26",
    "k_kobi_yp":     "TP.HPBITABLO6.29",
    "k_diger":       "TP.HPBITABLO6.30",
    "k_kurumsal_kart": "TP.HPBITABLO6.33",
    "k_finansal":    "TP.HPBITABLO6.36",
    "k_yd":          "TP.HPBITABLO6.43",   # 2. Yurt dışı yerleşikler
    "k_takip_tuk":   "TP.HPBITABLO6.50",
    "k_takip_tic":   "TP.HPBITABLO6.55",
    "k_karsilik":    "TP.HPBITABLO6.62",
}

# --- HAFTALIK, bie_hpbitablo1 — para arzı, bin TL ---------------------------
H_PARA = {
    "m1":            "TP.HPBITABLO1.2",
    "dolasim":       "TP.HPBITABLO1.3",
    "vadesiz_tl":    "TP.HPBITABLO1.4",
    "vadesiz_yp":    "TP.HPBITABLO1.8",
    "m2":            "TP.HPBITABLO1.11",
    "vadeli_tl":     "TP.HPBITABLO1.12",
    "vadeli_yp":     "TP.HPBITABLO1.15",
    "m3":            "TP.HPBITABLO1.18",
    "repo":          "TP.HPBITABLO1.19",
    "ppf":           "TP.HPBITABLO1.20",
    "menkul_ihrac":  "TP.HPBITABLO1.21",
}

# --- HAFTALIK, bie_kavramsal — para arzı ENDEKSİ (30.12.2005=100) -----------
# TCMB'nin KENDİ kur etkisi arındırması. Bizim arındırmamızın bağımsız sınavı.
H_ENDEKS = {
    "ham_m1":  "TP.KAVRAMSAL.HAMM1.INDX", "ar_m1": "TP.KAVRAMSAL.ARIM1.INDX",
    "ham_m2":  "TP.KAVRAMSAL.HAMM2.INDX", "ar_m2": "TP.KAVRAMSAL.ARIM2.INDX",
    "ham_m3":  "TP.KAVRAMSAL.HAMM3.INDX", "ar_m3": "TP.KAVRAMSAL.ARIM3.INDX",
}

# --- HAFTALIK, bie_kt100h / bie_mt100h / bie_kt200h — faiz, yüzde -----------
H_FAIZ = {
    "f_ihtiyac":     "TP.KTF10",     # ihtiyaç (yeni kullandırım, yıllıklandırılmış AOF)
    "f_tasit":       "TP.KTF11",
    "f_konut":       "TP.KTF12",
    "f_ticari_tl":   "TP.KTF17",     # ticari TL — makasın kredi bacağı
    "f_ticari_dar":  "TP.KTF18",     # KMH ve kurumsal kart hariç
    "f_tuketici":    "TP.KTFTUK",    # tüketici bileşik
    "f_ticari_usd":  "TP.KTF17.USD",
    "f_ticari_eur":  "TP.KTF17.EUR",
    "mev_tl":        "TP.TRY.MT06",  # TL mevduat toplam — makasın mevduat bacağı
    "mev_tl_3a":     "TP.TRY.MT02",
    "mev_tl_6a":     "TP.TRY.MT03",
    "mev_usd":       "TP.USD.MT06",
    "mev_eur":       "TP.EUR.MT06",
    "kat_ticari":    "TP.KBK.TRY.1",         # katılım kâr payı — ticari
    "kat_tuketici":  "TP.KBK.TRY.KBTFTUK",
}

# --- HAFTALIK, ZK tabanı (13 gün gecikmeli AYRI aile) -----------------------
# bie_tldthvade: bin TL · bie_zorundth: KB7 milyon USD, KB8 milyon TL.
# Sepet kuru = KB8/KB7 (ikisi de MİLYON) — birim varsayımı metrik.py'de
# USD kuruyla makullük denetiminden geçirilir.
H_ZK = {
    "zk_tl_taban":  "TP.TLDTHVADE.KB6",
    "zk_dth":       "TP.TLDTHVADE.KB12",
    "zk_taban":     "TP.TLDTHVADE.KB18",
    "dth_usd":      "TP.ZORUNDTH.KB7",   # milyon USD
    "dth_tl":       "TP.ZORUNDTH.KB8",   # milyon TL
    "dth_pay_usd":  "TP.ZORUNDTH.KB1",
    "dth_pay_eur":  "TP.ZORUNDTH.KB2",
    "dth_pay_maden": "TP.ZORUNDTH.KB3",
    "dth_pay_diger": "TP.ZORUNDTH.KB4",
}

# --- HAFTALIK, yüksek frekanslı talep vekilleri ------------------------------
H_TALEP = {
    "kart_harcama":  "TP.KKHARTUT.KT1",     # bin TL
    "kart_adet":     "TP.KKISLADE.KA1",
    "fin_sirket":    "TP.HPBITABLO7.0",     # finansman şirketleri toplam, bin TL
    "fin_sirket_tuk": "TP.HPBITABLO7.1",
    "fin_sirket_tic": "TP.HPBITABLO7.14",
}

# --- HAFTALIK ARŞİV (30.12.2005 → 31.01.2025) — uzun tarihçe ---------------
# Yeni hpbitablo* tabloları 28.06.2024'te BAŞLAR, arşiv 31.01.2025'te BİTER:
# 32 haftalık örtüşme. Seviyede uç uca ekleme YASAK (yeni tanım ~%0,7 düşük ve
# oran sürükleniyor); birleştirme yalnız BÜYÜME ORANI düzeyinde yapılır.
H_ARSIV = {
    "a_toplam":   "TP.KREDI.L001",   # I. Toplam kredi hacmi
    # Yurt içi TL bacağı: TCMB + mevduat + kalkınma-yatırım + katılım
    "a_tl_tcmb":  "TP.KREDI.L005", "a_tl_mev": "TP.KREDI.L012",
    "a_tl_kal":   "TP.KREDI.L037", "a_tl_kat": "TP.KREDI.L048",
    # Yurt içi YP bacağı
    "a_yp_tcmb":  "TP.KREDI.L006", "a_yp_mev": "TP.KREDI.L022",
    "a_yp_kal":   "TP.KREDI.L040", "a_yp_kat": "TP.KREDI.L049",
    # Mali kesime kullandırılan (yurt içi/dışı ayrımı yok, TL/YP var)
    "a_tl_mali_mev": "TP.KREDI.L056", "a_yp_mali_mev": "TP.KREDI.L057",
    "a_tl_mali_kal": "TP.KREDI.L059", "a_yp_mali_kal": "TP.KREDI.L060",
    "a_tl_mali_kat": "TP.KREDI.L062", "a_yp_mali_kat": "TP.KREDI.L063",
    "a_takip":    "TP.KREDI.L064",   # II. Tasfiye olunacak alacaklar
}

# --- İŞ GÜNÜ ----------------------------------------------------------------
G_KUR = {"usd": "TP.DK.USD.A.YTL", "eur": "TP.DK.EUR.A.YTL"}
G_BILANCO = {          # bie_abanlbil — analitik bilanço, bin TL
    "ab_dis_varlik": "TP.AB.A02", "ab_ic_varlik": "TP.AB.A03",
    "ab_mbp": "TP.AB.A15", "ab_rezerv_para": "TP.AB.A16",
    "ab_emisyon": "TP.AB.A17", "ab_banka_mevduat": "TP.AB.A18",
    "ab_zk_bloke": "TP.AB.A19", "ab_serbest": "TP.AB.A20",
    "ab_api": "TP.AB.A24", "ab_kamu_mevduat": "TP.AB.A25",
}
G_FONLAMA = {          # bie_apifon — milyon TL / yüzde
    "fon_toplam": "TP.APIFON1.TOP", "ster_toplam": "TP.APIFON2.TOP",
    "net_fonlama": "TP.APIFON3", "aofm": "TP.APIFON4",
}
G_FAIZ = {             # bie_pyintbnk — yüzde
    "politika": "TP.PY.P02.1H", "koridor_alt": "TP.PY.P01.ON",
    "koridor_ust": "TP.PY.P02.ON",
}

# GÜNLÜK AİLELER — "günlük" TEK BİR SAAT DEĞİLDİR.
#  Sayfa "günlük aileler <gün>" diye tek bir gün ilan ediyordu ve o gün YALNIZ
#  kur sütunundan (`usd`) türüyordu. Ölçüldü (09.09.2026, data/gunluk.csv):
#  kur 08.09'a kadar dolu, analitik bilanço · APİ fonlaması · faiz kotasyonları
#  04.09'da bitiyor — İKİ İŞ GÜNÜ fark. Fark yapısaldır, gecikme değil: TCMB
#  ertesi iş gününün gösterge kurunu bir gün ÖNCEDEN ilan eder (TAZELİK['kur']),
#  bilanço ise bir gün GECİKMELİ yayımlanır. Yani kur bacağının günü hiçbir
#  zaman "ölçülmüş bir gün" değildir ve onu bütün günlük ailelerin adına yazmak
#  okura üç aileyi iki iş günü taze gösterir.
#  Kaynak TEK: aile tanımı yukarıdaki kod gruplarından türer, elle liste
#  tutulmaz — yeni bir günlük seri eklendiğinde ailesiyle birlikte gelir.
GUNLUK_AILE: dict[str, tuple[str, tuple[str, ...]]] = {
    "kur":     ("döviz kuru", tuple(G_KUR)),
    "bilanco": ("analitik bilanço", tuple(G_BILANCO)),
    "api":     ("APİ fonlaması", tuple(G_FONLAMA)),
    "faiz":    ("TCMB faiz kotasyonları", tuple(G_FAIZ)),
}

# --- AYLIK ------------------------------------------------------------------
A_SERI = {
    "kkm_ddkkm":   "TP.KKM.K1",       # milyar USD
    "kkm_tl":      "TP.KKM.K4",       # milyar TL
    "kkm_gercek":  "TP.KKM.K2",
    "kkm_tuzel":   "TP.KKM.K3",
    # bie_krehacbs — bankacılık sektörü kredileri, bin TL, banka türü ayrımı
    "kh_toplam":   "TP.KREHACBS.A1",
    "kh_mevduat":  "TP.KREHACBS.A2",
    "kh_kalkinma": "TP.KREHACBS.A11",
    "kh_katilim":  "TP.KREHACBS.A20",   # ← katılım bankaları dahil/hariç kıyası
    "kh_sirket":   "TP.KREHACBS.A8",
    "kh_hane":     "TP.KREHACBS.A9",
    # katılım bankaları ayrı tablo (bie_kbkmkre)
    "kb_toplam":   "TP.KB.KRE25",
    "kb_tuketici": "TP.KB.KRE09",
    # beklenti — reel kredi faizi tam Fisher ile hesaplanır (i−π YASAK)
    "pka_12a":     "TP.PKAUO.S01.E.U",
}

# --- ÜÇ AYLIK — Banka Kredileri Eğilim Anketi (net yüzde değişim) -----------
C_BKEA = {
    "bkea_std_isletme":  "TP.BKEA.S001",   # 1.1 işletme kredisi standartları
    "bkea_std_kobi":     "TP.BKEA.S002",
    "bkea_std_buyuk":    "TP.BKEA.S003",
    "bkea_talep":        "TP.BKEA.S024",   # 4.1 işletme kredi talebi
    "bkea_talep_bek":    "TP.BKEA.S049",   # 7.1 gelecek çeyrek beklentisi
    "bkea_std_konut":    "TP.BKEA.S056",
    "bkea_std_tasit":    "TP.BKEA.S057",
    "bkea_std_diger":    "TP.BKEA.S058",
}

# ===========================================================================
#  TAZELİK — aile bazlı. Referans DUVAR SAATİdir; verinin kendi son gününü
#  referans almak denetimi kendi kendine referanslı hâle getirir.
#  (etiket, tolerans, birim)  ·  birim: "isgunu" | "gun" | "gun_donem_sonu"
#
#  "gun_donem_sonu": aylık ve üç aylık gözlemler dönemin İLK gününe damgalanır
#  (2026-6 → 01.06.2026) ama TCMB gecikmeyi dönemin SONUNDAN sayar (51 gün).
#  Damganın kendisinden ölçmek her ay bir aylık sahte gecikme ekler ve hattı
#  her koşuda yanlış yere "bayat" işaretler.
# ===========================================================================
TAZELIK = {
    "api":      ("APİ fonlaması / AOFM (aynı gün yayımlanır)", 3, "isgunu"),
    "bilanco":  ("Analitik bilanço (1 iş günü gecikmeli)", 4, "isgunu"),
    "kur":      ("Döviz kuru (bir gün ÖNCEDEN ilan edilir)", 4, "isgunu"),
    "haftalik": ("Haftalık Para ve Banka İstatistikleri (Perşembe, 6 gün)", 12, "gun"),
    "zk":       ("Zorunlu karşılık tabanı (13 gün)", 20, "gun"),
    "aylik":    ("Aylık para ve banka istatistikleri (51 gün)", 70, "gun_donem_sonu"),
    "ceyrek":   ("Banka Kredileri Eğilim Anketi (51 gün)", 110, "gun_donem_sonu"),
}
# Dönem sonuna çevrim: aylık damga → ay sonu, çeyrek damgası → çeyrek sonu.
DONEM_SONU_AY = {"aylik": 1, "ceyrek": 3}

AY_TR = {1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
         7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"}
AY_KISA = {1: "Oca", 2: "Şub", 3: "Mar", 4: "Nis", 5: "May", 6: "Haz",
           7: "Tem", 8: "Ağu", 9: "Eyl", 10: "Eki", 11: "Kas", 12: "Ara"}


def ad_uzun(t) -> str:
    t = pd.Timestamp(t)
    return f"{AY_TR[t.month]} {t.year}"


def ad_gun(t) -> str:
    t = pd.Timestamp(t)
    return f"{t.day} {AY_TR[t.month]} {t.year}"


def ad_ceyrek(t) -> str:
    t = pd.Timestamp(t)
    return f"{t.year}-Ç{(t.month - 1) // 3 + 1}"


# ===========================================================================
#  ŞEKİL SAAT DEFTERİ — bir figürün damgası, HATTIN saati değildir
# ===========================================================================
#  Bu hat üç ritim taşıyor (haftalık para/banka · aylık KKM ve banka türü ·
#  çeyreklik BKEA) ama dokuz şeklin dokuzu da HAFTALIK saatle damgalanıyordu:
#  grafik.py figürün alt başlığına, GrafikEmbed de sayfada şeklin altına aynı
#  `son_hafta`yı basıyordu. Dört figürde ölçüldü (03.09.2026):
#    · 07_kkm.html — çizilen üç serinin de ucu 2026-07-01, damga 21.08.2026:
#      KAPANMIŞ bir programın Temmuz stoku ağustos tarihiyle sunuluyordu (+51
#      gün). Seri bayat değil (aylık aile için beklenen gecikme zaten 51 gün);
#      yanlış olan veri değil, ETİKET.
#    · 06_dolarizasyon.html — yedi izin BEŞİ 2026-08-14'te bitiyor, yalnız
#      ikisi 08-21'de. Hat bunu kendisi ölçüp uyarı bile basmış ve bloğu ortak
#      tarihe (14.08) çıpalamış; sayfanın METNİ 14.08 derken aynı sayfadaki
#      ŞEKLİN damgası 21.08 diyordu. Sayfa kendi kendisiyle çelişiyordu.
#    · 09_kredi_enflasyon.html — örneklem AYLIK ve figürün kendi alt başlığı
#      "2006-04 → 2026-08 (241 ay)" yazarken damga tek bir GÜN gösteriyordu.
#    · 03_kredi_kirilim.html — dört panel, ÜÇ saat (p1/p2 haftalık 21.08 ·
#      p3 aylık Temmuz · p4 çeyreklik 2026-Ç2). Bu figür tek damgayla dürüst
#      anlatılamaz: en eski bacağı (BKEA) yazmak görsel olarak baskın haftalık
#      panelleri beş ay bayat gösterir, en tazesini yazmak aylık ve çeyreklik
#      panelleri taze gösterir. Bu yüzden defterde None — sayfa o şeklin altına
#      tarih HİÇ basmaz ve figür üç saati kendi panel başlıklarında taşır.
#      Yanlış bir tarih, tarihsizlikten kötüdür.
#  Kalan beş figürün bütün bacakları haftalık kaynaklardan geliyor ve ölçümde
#  hepsi `son_hafta`da bitiyor; onlar ana saatte kalır.
#
#  Defter BURADA duruyor çünkü iki tüketicisi var: grafik.py figürün KENDİ alt
#  başlığına yazar, ozet_uret.py sayfa altındaki damga için ozet.json'a
#  `_sekil_tarih` olarak koyar. İki ayrı liste tutulsaydı bir gün sessizce
#  ayrışır ve hangisinin neyi söylediği kimsenin aklında kalmazdı.
def sekil_saatleri(o: dict, uzun: bool = False) -> dict[str, str | None]:
    """Figür başına veri ucu; `o` = data/metrik_ozet.json.

    Değerler ÖLÇÜMDEN gelir, türetilmez: `son_hafta`, `dol_tarih` (metrik.py'nin
    dolarizasyon bloğunu çıpaladığı ortak tarih), `kkm.son_tarih` ve
    `uzun_capraz.son`. Ölçüm yoksa değer None kalır ve o şeklin altına tarih
    basılmaz — uydurmaktan iyidir.

    `uzun=True` figür alt başlığının yazımını verir ("21 Ağustos 2026" ·
    "Temmuz 2026"); varsayılan site sözleşmesidir ("21.08.2026" · "07.2026",
    ortak/bicim ikisini de çözer, ikincisi ayın son gününe demirler).
    """
    def gun(t):
        if not t:
            return None
        t = pd.Timestamp(t)
        return ad_gun(t) if uzun else t.strftime("%d.%m.%Y")

    def ay(t):
        # AYLIK bir gözlem dönemin İLK gününe damgalanır; onu gün gibi yazmak
        # ("01.07.2026") okura o günün ölçümüymüş gibi görünür. Ay yazılır.
        if not t:
            return None
        t = pd.Timestamp(t)
        return ad_uzun(t) if uzun else t.strftime("%m.%Y")

    hafta = gun(o.get("son_hafta"))
    return {
        "01_kredi_buyume.html": hafta,
        "02_kur_etkisi.html": hafta,
        "03_kredi_kirilim.html": None,          # dört panel, üç saat (yukarı bak)
        # 04'te AOFM ve makası 14 gün daha eski (fonlama tabanı eşiğin altına
        # düştüğü haftalar geçersiz işaretleniyor) ama o iki iz on altı izden
        # ikisi ve TANI izidir; kendi saatleri sayfa metninde `aofm_tarih` ile,
        # beklenti bacağınınki `pka_tarih` ile ayrıca yazılıyor.
        "04_faiz_spread.html": hafta,
        "05_para_arzi.html": hafta,
        "06_dolarizasyon.html": gun(o.get("dol_tarih")),
        "07_kkm.html": ay((o.get("kkm") or {}).get("son_tarih")),
        "08_takip.html": hafta,
        "09_kredi_enflasyon.html": ay((o.get("uzun_capraz") or {}).get("son")),
    }


# --------------------------------------------------------------------------- toplama
def _panel(kodlar: dict[str, str], frekans: str, bas: str | None = None,
           yenile: bool = False) -> pd.DataFrame:
    out: dict[str, pd.Series] = {}
    for ad, kod in kodlar.items():
        try:
            out[ad] = evds(kod, frekans=frekans, bas=bas, yenile=yenile)
        except Exception as ex:
            uyar(f"SERİ ALINAMADI: {ad} ({kod}) — {ex}")
    df = pd.DataFrame(out)
    df.index.name = "tarih"
    return df.sort_index()


def tazelik_tolerans(aile: str = "haftalik") -> int:
    """Bir tazelik ailesinin toleransı (denetimle AYNI kaynaktan).

    ozet_uret.py bayat bayrağını buradan okur; eşik iki yerde ayrı yazılırsa
    biri güncellenip öteki unutulur ve bayatlık sessizce kaçar.
    """
    return int(TAZELIK[aile][1])


def _is_gunu_farki(son: pd.Timestamp, bugun: pd.Timestamp) -> int:
    return int(np.busday_count(son.date(), bugun.date()))


def tazelik_denetimi(paneller: dict[str, tuple[str, pd.DataFrame, list[str]]]) -> list[str]:
    """paneller: aile → (etiketli panel adı, df, denetlenecek kolonlar)."""
    bugun = pd.Timestamp.today().normalize()
    uy: list[str] = []
    for aile, (panel_ad, df, kolonlar) in paneller.items():
        etiket, tol, olcu = TAZELIK[aile]
        for k in kolonlar:
            if k not in df.columns or df[k].dropna().empty:
                uy.append(f"TAZELİK: '{k}' serisi yüklenemedi ({panel_ad}) — "
                          f"{etiket} ailesi eksik.")
                continue
            son = df[k].dropna().index[-1]
            ref = son
            if olcu == "gun_donem_sonu":
                ref = son + pd.offsets.MonthEnd(DONEM_SONU_AY[aile])
            gecikme = (_is_gunu_farki(ref, bugun) if olcu == "isgunu"
                       else (bugun - ref).days)
            # Kur serisinde NEGATİF gecikme normaldir (ertesi günün kuru bir gün
            # önce ilan edilir); "gelecek tarihli veri" alarmı üretilmez.
            if gecikme > tol:
                birim = "iş günü" if olcu == "isgunu" else "gün"
                uy.append(
                    f"TAZELİK: '{k}' son gözlemi {son:%d.%m.%Y} — bugün "
                    f"{bugun:%d.%m.%Y} itibarıyla {gecikme} {birim} geride "
                    f"(tolerans {tol}). {etiket} yayını durmuş olabilir.")
    return uy


def yapisal_denetim(H: pd.DataFrame, G: pd.DataFrame) -> list[str]:
    """Kimlik denetimleri — bozulursa kalem numaralandırması değişmiştir.
    Bunlar tazelik denetimi DEĞİLDİR: seri taze olabilir ama yanlış kalemi
    gösteriyor olabilir (EVDS'te kalem eklendiğinde numaralar kayar)."""
    uy: list[str] = []

    def _oran_kontrol(ad: str, sol: pd.Series, sag: pd.Series, tol: float):
        ort = pd.concat([sol, sag], axis=1).dropna()
        if ort.empty:
            uy.append(f"YAPISAL: {ad} denetimi yapılamadı (ortak gözlem yok).")
            return
        bagil = ((ort.iloc[:, 0] - ort.iloc[:, 1]).abs()
                 / ort.iloc[:, 1].abs().replace(0, np.nan)).max()
        if pd.notna(bagil) and bagil > tol:
            uy.append(f"YAPISAL: {ad} — en büyük bağıl sapma {bagil:.2%} "
                      f"(tolerans {tol:.2%}). Kalem numaralandırması değişmiş olabilir.")

    if {"kredi_toplam"} <= set(H.columns) and {"k_yi_toplam", "k_yd"} <= set(H.columns):
        _oran_kontrol("toplam kredi = yurt içi + yurt dışı "
                      "(HPBITABLO2.22 ≟ HPBITABLO6.1 + HPBITABLO6.43)",
                      H["k_yi_toplam"] + H["k_yd"], H["kredi_toplam"], 1e-4)
    if {"m1", "dolasim", "vadesiz_tl", "vadesiz_yp"} <= set(H.columns):
        _oran_kontrol("M1 kimliği (C + vadesiz TL + vadesiz YP)",
                      H["dolasim"] + H["vadesiz_tl"] + H["vadesiz_yp"], H["m1"], 1e-6)
    if {"m2", "m1", "vadeli_tl", "vadeli_yp"} <= set(H.columns):
        _oran_kontrol("M2 kimliği (M1 + vadeli TL + vadeli YP)",
                      H["m1"] + H["vadeli_tl"] + H["vadeli_yp"], H["m2"], 1e-6)
    if {"m3", "m2", "repo", "ppf", "menkul_ihrac"} <= set(H.columns):
        _oran_kontrol("M3 kimliği (M2 + repo + PPF + ihraç menkul)",
                      H["m2"] + H["repo"] + H["ppf"].fillna(0)
                      + H["menkul_ihrac"].fillna(0), H["m3"], 1e-6)
    if {"kredi_yi", "kredi_tl", "kredi_yp"} <= set(H.columns):
        _oran_kontrol("yurt içi kredi = TL + YP (HPBITABLO2.23 ≟ .24 + .28)",
                      H["kredi_tl"] + H["kredi_yp"], H["kredi_yi"], 1e-4)
    # Birim/işaret kimliği: analitik bilanço APİ kalemi ile net APİ fonlaması
    # aynı günde ters işaretle aynı büyüklük olmalı (A24 bin TL, APIFON3 mn TL).
    if {"ab_api"} <= set(G.columns) and {"net_fonlama"} <= set(G.columns):
        ort = pd.concat([G["ab_api"] / 1000.0, -G["net_fonlama"]], axis=1).dropna()
        ort = ort[ort.iloc[:, 1].abs() > 1000]     # küçük tabanda oran anlamsız
        if len(ort):
            bagil = ((ort.iloc[:, 0] - ort.iloc[:, 1]).abs()
                     / ort.iloc[:, 1].abs()).tail(260)
            # MEDYAN bakılır, maksimum değil: bu kimlik dönem sonu günlerinde
            # (ay/çeyrek kapanışı) değerleme farkıyla birkaç binde bir sapıyor ve
            # tabanı küçük bir günde bu oran %3'e çıkabiliyor. Aranan hata sınıfı
            # başka: birim ya da hizalama bozulursa sapma HER GÜN oluşur.
            if pd.notna(bagil.median()) and bagil.median() > 1e-4:
                uy.append(f"YAPISAL: analitik bilanço APİ kalemi (A24, bin TL) ile "
                          f"net APİ fonlaması (APIFON3, milyon TL) son bir yılda "
                          f"medyan {bagil.median():.2%} ayrışıyor. Birim dönüşümü "
                          "ya da hizalama bozulmuş olabilir.")
            elif float((bagil > 0.02).mean()) > 0.05:
                uy.append(f"YAPISAL: A24 ↔ APIFON3 kimliği günlerin "
                          f"%{(bagil > 0.02).mean() * 100:.0f}'inde %2'den fazla "
                          "sapıyor (dönem sonu değerleme farkından çok daha sık).")
    # Sıfır ≠ veri: uzun süre 0 basan faiz serileri grafiğe girmemeli.
    for k in ("politika", "koridor_alt", "koridor_ust"):
        if k in G.columns:
            son = G[k].dropna().tail(60)
            if len(son) and (son == 0).mean() > 0.5:
                uy.append(f"SIFIR SERİ: '{k}' son 60 iş gününün yarısından "
                          "fazlasında 0 basıyor — kotasyon verilmiyor demektir, "
                          "faiz oranı değil. NaN'a çevrildi.")
    return uy


# --------------------------------------------------------------------------- dönem
_DONEM: dict[str, str] = {}


def _son(df: pd.DataFrame, kolonlar: list[str]) -> pd.Timestamp:
    var = [c for c in kolonlar if c in df.columns]
    if not var:
        raise RuntimeError("dönem okunamadı: çekirdek kolonlar yok")
    tam = df[var].dropna(how="any")
    if tam.empty:
        raise RuntimeError("dönem okunamadı: çekirdek seriler boş")
    return tam.index[-1]


def son_hafta(H: pd.DataFrame | None = None) -> pd.Timestamp:
    """Haftalık analizin çıpası: kredi/mevduat/para arzı çekirdeğinin TAMAMININ
    dolu olduğu son Cuma. Sabit tarih YASAK."""
    if "hafta" in _DONEM:
        return pd.Timestamp(_DONEM["hafta"])
    if H is None:
        H = pd.read_csv(VERI / "haftalik.csv", index_col=0, parse_dates=True)
    t = _son(H, ["kredi_tl", "kredi_yp", "mevduat_tl", "mevduat_yp", "m2"])
    _DONEM["hafta"] = t.strftime("%Y-%m-%d")
    return t


def son_gun_aileleri(G: pd.DataFrame | None = None) -> dict[str, str]:
    """Günlük ailelerin AYRI AYRI son dolu günü (ISO).

    Bir aileden hiçbir sütun yüklenememişse aile sözlükte YER ALMAZ — ölçülmemiş
    bir aileyi bugünün tarihiyle doldurmak, ölçülmemiş şeyi ölçülmüş göstermek
    olurdu.
    """
    if G is None:
        G = pd.read_csv(VERI / "gunluk.csv", index_col=0, parse_dates=True)
    out: dict[str, str] = {}
    for aile, (_, kolonlar) in GUNLUK_AILE.items():
        var = [k for k in kolonlar if k in G.columns and G[k].notna().any()]
        if not var:
            continue
        out[aile] = _son(G, var).strftime("%Y-%m-%d")
    return out


def son_gun(G: pd.DataFrame | None = None) -> pd.Timestamp:
    """Günlük ailelerin BAĞLAYICI günü: hepsinin dolu olduğu son iş günü.

    Eskiden yalnız `usd` sütununa bakıyordu; kur bacağı ertesi iş günü için
    ilan edildiğinden bu, sayfada ilan edilen "günlük aileler" gününü iki iş
    günü ileri atıyordu (bkz. GUNLUK_AILE). Bağlayıcı bacak EN ESKİSİDİR:
    figür damgası kuralının aynısı — bir kıyas ancak hepsinin ölçüldüğü güne
    kadar kurulabilir. Ailelerin tek tek günü `son_gun_aileleri` ile ayrıca
    yayımlanır, yani taze bacak kaybolmaz, adıyla görünür.
    """
    if "gun" in _DONEM:
        return pd.Timestamp(_DONEM["gun"])
    if G is None:
        G = pd.read_csv(VERI / "gunluk.csv", index_col=0, parse_dates=True)
    aileler = son_gun_aileleri(G)
    if not aileler:
        raise RuntimeError("dönem okunamadı: hiçbir günlük aile yüklenemedi")
    t = min(pd.Timestamp(v) for v in aileler.values())
    _DONEM["gun"] = t.strftime("%Y-%m-%d")
    return t


def son_ay(A: pd.DataFrame | None = None) -> pd.Timestamp:
    if "ay" in _DONEM:
        return pd.Timestamp(_DONEM["ay"])
    if A is None:
        A = pd.read_csv(VERI / "aylik.csv", index_col=0, parse_dates=True)
    t = _son(A, ["kh_toplam"])
    _DONEM["ay"] = t.strftime("%Y-%m-%d")
    return t


def son_ceyrek(C: pd.DataFrame | None = None) -> pd.Timestamp:
    if "ceyrek" in _DONEM:
        return pd.Timestamp(_DONEM["ceyrek"])
    if C is None:
        C = pd.read_csv(VERI / "ceyreklik.csv", index_col=0, parse_dates=True)
    t = _son(C, ["bkea_std_isletme"])
    _DONEM["ceyrek"] = t.strftime("%Y-%m-%d")
    return t


# --------------------------------------------------------------------------- ana akış
def kos(yenile: bool = False) -> dict:
    print("EVDS3 → kredi & parasal büyüklükler veri katmanı")
    print(f"  anahtar: {'ortam değişkeni' if os.environ.get('TTO_EVDS_KEY') else 'dosya'}")

    haftalik_kod = {**H_BILANCO, **H_KREDI, **H_PARA, **H_ENDEKS,
                    **H_FAIZ, **H_ZK, **H_TALEP}
    print(f"  haftalık seri: {len(haftalik_kod)}")
    H = _panel(haftalik_kod, "hafta", yenile=yenile)

    print(f"  haftalık ARŞİV seri (uzun tarihçe): {len(H_ARSIV)}")
    ARS = _panel(H_ARSIV, "hafta", yenile=yenile)

    gunluk_kod = {**G_KUR, **G_BILANCO, **G_FONLAMA, **G_FAIZ}
    print(f"  iş günü seri: {len(gunluk_kod)}")
    G = _panel(gunluk_kod, "gun", yenile=yenile)
    # SIFIR ≠ VERİ (1): kotasyon verilmeyen yönler uzun dönem 0 basıyor.
    for k in ("politika", "koridor_alt", "koridor_ust", "aofm"):
        if k in G.columns:
            G[k] = G[k].replace(0.0, np.nan)
    # SIFIR ≠ VERİ (2): analitik bilançoda ZORUNLU KARŞILIK BLOKE HESABI (A19)
    # ayrı bir satır olarak ancak sonradan yayımlanmaya başlıyor; öncesinde
    # bankalar mevduatının tamamı "serbest mevduat" satırında duruyor ve A19
    # sıfır basıyor. Bu sıfırlar "zorunlu karşılık yoktu" demek DEĞİL, "kalem
    # ayrı yayımlanmıyordu" demek. Grafikte sıfır çizmek ve o yıllar için
    # ima edilen ZK oranını %0 hesaplamak yanlış olurdu.
    if "ab_zk_bloke" in G.columns:
        G["ab_zk_bloke"] = G["ab_zk_bloke"].replace(0.0, np.nan)
        dolu = G["ab_zk_bloke"].dropna()
        if len(dolu):
            print(f"  ZK bloke hesabı (TP.AB.A19) fiilen başlangıcı: "
                  f"{dolu.index[0]:%d.%m.%Y} (öncesi sıfır basıyor, NaN'a çevrildi)")

    print(f"  aylık seri: {len(A_SERI)}")
    A = _panel(A_SERI, "ay", yenile=yenile)

    print(f"  üç aylık seri: {len(C_BKEA)}")
    C = _panel(C_BKEA, "ceyrek", yenile=yenile)

    # dönem çıpaları — VERİDEN
    s_h, s_g = son_hafta(H), son_gun(G)
    s_a, s_c = son_ay(A), son_ceyrek(C)
    print(f"  SON HAFTA: {ad_gun(s_h)} · SON İŞ GÜNÜ: {ad_gun(s_g)} · "
          f"SON AY: {ad_uzun(s_a)} · SON ÇEYREK: {ad_ceyrek(s_c)}")

    for u in tazelik_denetimi({
        "haftalik": ("Haftalık Para ve Banka İst.", H,
                     ["kredi_tl", "kredi_yp", "m2", "f_ticari_tl", "mev_tl"]),
        "zk":       ("ZK tabanı", H, ["zk_taban", "dth_usd", "dth_tl"]),
        "kur":      ("Döviz kuru", G, ["usd", "eur"]),
        "bilanco":  ("Analitik bilanço", G, ["ab_rezerv_para", "ab_zk_bloke"]),
        "api":      ("APİ fonlaması", G, ["net_fonlama"]),
        "aylik":    ("Aylık para ve banka ist.", A, ["kh_toplam", "kkm_tl"]),
        "ceyrek":   ("BKEA", C, ["bkea_std_isletme", "bkea_talep"]),
    }):
        uyar(u)
    for u in yapisal_denetim(H, G):
        uyar(u)

    H.to_csv(VERI / "haftalik.csv")
    ARS.to_csv(VERI / "arsiv.csv")
    G.to_csv(VERI / "gunluk.csv")
    A.to_csv(VERI / "aylik.csv")
    C.to_csv(VERI / "ceyreklik.csv")

    durum = {
        "kosum": dt.date.today().isoformat(),
        "son_hafta": s_h.strftime("%Y-%m-%d"),
        "son_gun": s_g.strftime("%Y-%m-%d"),
        "son_ay": s_a.strftime("%Y-%m-%d"),
        "son_ceyrek": s_c.strftime("%Y-%m-%d"),
        "haftalik": [int(H.shape[0]), int(H.shape[1])],
        "arsiv": [int(ARS.shape[0]), int(ARS.shape[1])],
        "gunluk": [int(G.shape[0]), int(G.shape[1])],
        "aylik": [int(A.shape[0]), int(A.shape[1])],
        "ceyreklik": [int(C.shape[0]), int(C.shape[1])],
        "uyarilar": list(_UYARI),
    }
    (VERI / "veri_durum.json").write_text(
        json.dumps(durum, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  yazıldı: haftalik {H.shape} · arsiv {ARS.shape} · gunluk {G.shape} "
          f"· aylik {A.shape} · ceyreklik {C.shape}")
    if _UYARI:
        print(f"\n[{len(_UYARI)} uyarı]")
    return durum


if __name__ == "__main__":
    import sys
    kos(yenile="--yenile" in sys.argv)
