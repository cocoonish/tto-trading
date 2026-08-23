# -*- coding: utf-8 -*-
"""Ödemeler dengesi & dış finansman — KEŞİF katmanı (EVDS3).

Amaç
----
Hattın veri.py'si yazılmadan ÖNCE aday seri kodlarının GERÇEKTEN çalıştığını,
hangi birimde ve hangi frekansta geldiğini, nerede başlayıp nerede bittiğini
ÖLÇMEK. Çalışmayan kod listeye girmez; çalışan kodun son gözlemi rapora yazılır.

Ne yapar
--------
1. Fonlama/veri.py ile AYNI anahtar arama sırasını kullanır
   (TTO_EVDS_KEY → <proje>/.evds_key → kök/.evds_key → TCMBNetRezerv/.evds_key).
2. Kullanılacak her VERİ GRUBUNUN meta verisini çeker ve BİRİMİ (`BIRIMI`)
   oradan okur — birim tahmin EDİLMEZ, EVDS'ten okunur.
3. Her aday seriyi tek tek çağırır; frekansa göre tarih parçalaması yapar
   (EVDS tek istekte ~1000 satırda sessizce kırpar ve aralığın SONUNDAN
   doldurur; aylık/üç aylık seriler 1000'in altında kaldığı için tek parça,
   günlük kur serisi 366 günlük parçalar hâlinde çekilir).
4. KİMLİK denetimleri koşar (12 tanesi de GEÇİYOR — ölçüldü):
     · analitik sunum ile ayrıntılı sunum aynı ayda aynı cari dengeyi verir
     · çekirdek cari denge tanımı: K10 = K1 − K4 − K7
     · ANALİTİK sunumda finans hesabı REZERVİ İÇERMEZ:
           Q13 = Σ(varlık − yükümlülük),  CA + KA + NHN = Q13 + Q33
     · AYRINTILI sunumda finans hesabı rezervi İÇERİR:
           Q1 + Q99 + Q210 = Q101,  köprü: Q101 = Q13 + Q33
     · uzun vadeli kredi: net yükümlülük = kullanım − geri ödeme
   Ayrıca rezerv AKIMININ işaret yönü rezerv STOKUYLA sınanır (ölçülen aylık
   korelasyon 0,92 → pozitif akım = rezerv artışı, BPM6 standardı).
5. Birim denetimi: GSYH bin TL ve ÜÇ AYLIK, ödemeler dengesi milyon USD ve
   AYLIK. Dönüşüm (bin TL → /1000 → milyon TL → /çeyrek ort. USDTRY) sonucu
   bilinen bir mertebeyle kıyaslanır.
6. Sonucu data/kesif_sonuc.json'a HER KOŞUDA yeniden yazar ("dosya varsa atla"
   yok). JSON'a "_tarih" (aylık son dönem) ve "_tarih2" (üç aylık son dönem)
   düşer.

Tazelik uyarısı
---------------
Veri grubu meta verisindeki `LAST_UPDATED` alanı GÜVENİLMEZ: ölçüldü, bir grup
2026-06 verisi taşırken LAST_UPDATED 2025-12 diyordu. Tazelik, serinin KENDİ
son gözlemi ile duvar saati farkından hesaplanmalı.

Koşum:  python3 kesif.py
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
VERI.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------- anahtar
# Fonlama/veri.py'deki _evds_anahtari() ile AYNI sıra. Anahtar koda GÖMÜLMEZ.
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


def _cek(url: str, deneme: int = 3):
    """EVDS3'ten JSON. Anahtar `key:` BAŞLIĞINDA gider, URL'de DEĞİL."""
    son: Exception | None = None
    for i in range(deneme):
        try:
            req = urllib.request.Request(
                url, headers={"key": anahtar(), "User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as ex:
            son = ex
            if i < deneme - 1:
                time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"EVDS isteği düştü: {son}") from son


# --------------------------------------------------------------------------- meta
def datagrup_meta(kod: str) -> dict:
    """Veri grubu meta verisi. BİRİM buradan okunur (`BIRIMI`)."""
    # datagroups mode=2 kategori bazlı çalışır; mode=0 tüm grupları döndürür.
    global _TUM_GRUP
    if _TUM_GRUP is None:
        _TUM_GRUP = {g["DATAGROUP_CODE"]: g
                     for g in _cek(f"{BASE}/datagroups/mode=0&type=json")}
    return _TUM_GRUP.get(kod, {})


_TUM_GRUP: dict | None = None


def seri_listesi(grup: str) -> dict[str, dict]:
    d = _cek(f"{BASE}/serieList/type=json&code={grup}")
    return {x["SERIE_CODE"]: x for x in d}


# --------------------------------------------------------------------------- gözlem
# ÜÇ ayrı tarih biçimi; karıştırılırsa seri SESSİZCE boşalır.
#   GÜNLÜK / HAFTALIK → "20-08-2026"
#   AYLIK             → "2026-6"
#   ÜÇ AYLIK          → "2026-Q2"   ← int("Q2") tuzağı tam burada
def _ayristir(items, kolon: str, bicim: str) -> pd.Series:
    if not items:
        return pd.Series(dtype=float)
    df = pd.DataFrame(items)
    if "Tarih" not in df.columns or kolon not in df.columns:
        return pd.Series(dtype=float)
    t = df["Tarih"].astype(str)
    if bicim == "gun":
        idx = pd.to_datetime(t, format="%d-%m-%Y", errors="coerce")
    elif bicim == "ay":
        idx = pd.to_datetime(t, format="%Y-%m", errors="coerce")
    elif bicim == "ceyrek":
        # "2026-Q2" → çeyrek SONU tarihi. pandas Period bunu doğrudan anlar.
        idx = pd.PeriodIndex(t.str.replace("-", "", regex=False),
                             freq="Q").to_timestamp(how="end").normalize()
    else:
        raise ValueError(f"bilinmeyen biçim: {bicim}")
    s = pd.to_numeric(df[kolon].replace("", None), errors="coerce")
    s.index = pd.Index(idx)
    s = s[~s.index.isna()].dropna().sort_index()
    return s


BICIM = {"AYLIK": "ay", "ÜÇ AYLIK": "ceyrek", "GÜNLÜK": "gun",
         "HAFTALIK(ÇARŞAMBA)": "gun", "HAFTALIK(CUMA)": "gun", "YILLIK": "ay"}
PARCA = {"gun": 366, "ay": 30000, "ceyrek": 30000}


def seri_cek(kod: str, bicim: str, bas: str) -> pd.Series:
    """Tek seri. Günlük seriler 366 günlük parçalar hâlinde çekilir; aylık ve
    üç aylık seriler 1000 satırın altında kaldığı için tek istekte gelir."""
    guv = kod.replace(".", "_")
    b = pd.Timestamp(bas)
    bugun = pd.Timestamp.today().normalize()
    adim = PARCA[bicim]
    parcalar = []
    imlec = b
    while imlec <= bugun:
        sonu = min(imlec + pd.Timedelta(days=adim - 1), bugun)
        url = (f"{BASE}/series={kod}&startDate={imlec:%d-%m-%Y}"
               f"&endDate={sonu:%d-%m-%Y}&type=json")
        try:
            y = _cek(url)
            items = y.get("items", [])
            # 1000 satır kırpma alarmı: dolu geldiyse aralığın BAŞI kesilmiş olabilir
            if len(items) >= 1000:
                uyar(f"KIRPMA RİSKİ: {kod} {imlec:%Y}–{sonu:%Y} aralığında "
                     f"{len(items)} satır döndü (EVDS ~1000'de kırpar).")
            p = _ayristir(items, guv, bicim)
            if len(p):
                parcalar.append(p)
        except Exception as ex:
            uyar(f"SERİ ALINAMADI: {kod} ({imlec:%Y}–{sonu:%Y}) — {ex}")
        imlec = sonu + pd.Timedelta(days=1)
        time.sleep(0.15)
    if not parcalar:
        return pd.Series(dtype=float)
    s = pd.concat(parcalar)
    return s[~s.index.duplicated(keep="last")].sort_index()


# ===========================================================================
# ADAY SERİLER — (kod, kısa ad, veri grubu)
# Birim veri grubundan OKUNUR (datagrup_meta[...]['BIRIMI']); burada YAZILMAZ.
# ===========================================================================

# --- Cari denge: analitik sunum (aylık, milyon USD) ------------------------
CARI = [
    ("TP.ODANA6.Q01", "cari_denge",        "bie_odana6"),
    ("TP.ODANA6.Q02", "ihracat",           "bie_odana6"),
    ("TP.ODANA6.Q03", "ithalat",           "bie_odana6"),
    ("TP.ODANA6.Q04", "mal_dengesi",       "bie_odana6"),
    ("TP.ODANA6.Q05", "hizmet_gelir",      "bie_odana6"),
    ("TP.ODANA6.Q06", "hizmet_gider",      "bie_odana6"),
    ("TP.ODANA6.Q07", "mal_hizmet_denge",  "bie_odana6"),
    ("TP.ODANA6.Q08", "birincil_gelir",    "bie_odana6"),
    ("TP.ODANA6.Q09", "birincil_gider",    "bie_odana6"),
    ("TP.ODANA6.Q10", "mhb_denge",         "bie_odana6"),
    ("TP.ODANA6.Q11", "ikincil_gelir",     "bie_odana6"),
    ("TP.ODANA6.Q12", "sermaye_hesabi",    "bie_odana6"),
]

# --- Çekirdek cari denge: altın & enerji ayrıştırması ----------------------
CEKIRDEK = [
    ("TP.HARICCARIACIK.K1",  "hc_cari",          "bie_hariccariacik"),
    ("TP.HARICCARIACIK.K2",  "hc_altin_ihr",     "bie_hariccariacik"),
    ("TP.HARICCARIACIK.K3",  "hc_altin_ith",     "bie_hariccariacik"),
    ("TP.HARICCARIACIK.K4",  "hc_altin_net",     "bie_hariccariacik"),
    ("TP.HARICCARIACIK.K5",  "hc_enerji_ihr",    "bie_hariccariacik"),
    ("TP.HARICCARIACIK.K6",  "hc_enerji_ith",    "bie_hariccariacik"),
    ("TP.HARICCARIACIK.K7",  "hc_enerji_net",    "bie_hariccariacik"),
    ("TP.HARICCARIACIK.K8",  "hc_altin_haric",   "bie_hariccariacik"),
    ("TP.HARICCARIACIK.K9",  "hc_enerji_haric",  "bie_hariccariacik"),
    ("TP.HARICCARIACIK.K10", "hc_cekirdek",      "bie_hariccariacik"),
]

# --- Finans hesabı kırılımı (analitik sunum) -------------------------------
# İŞARET UYARISI: BPM6'da finans hesabı NET VARLIK EDİNİMİ − NET YÜKÜMLÜLÜK
# OLUŞUMU'dur; POZİTİF değer SERMAYE ÇIKIŞI demektir. Grafikte "giriş" olarak
# göstermek için yükümlülük bacağının işareti çevrilir — bu dönüşüm metrik.py'de
# TEK yerde yapılacak.
FINANS = [
    ("TP.ODANA6.Q13", "fin_hesabi",        "bie_odana6"),
    ("TP.ODANA6.Q14", "dyy_varlik",        "bie_odana6"),
    ("TP.ODANA6.Q15", "dyy_yukumluluk",    "bie_odana6"),
    ("TP.ODANA6.Q16", "port_varlik",       "bie_odana6"),
    ("TP.ODANA6.Q17", "port_yukumluluk",   "bie_odana6"),
    ("TP.ODANA6.Q18", "port_hisse",        "bie_odana6"),
    ("TP.ODANA6.Q19", "port_borc_senedi",  "bie_odana6"),
    ("TP.ODANA6.Q37", "turev_varlik",      "bie_odana6"),
    ("TP.ODANA6.Q38", "turev_yukumluluk",  "bie_odana6"),
    ("TP.ODANA6.Q20", "diger_varlik",      "bie_odana6"),
    ("TP.ODANA6.Q21", "diger_varlik_tcmb", "bie_odana6"),
    ("TP.ODANA6.Q22", "diger_varlik_gh",   "bie_odana6"),
    ("TP.ODANA6.Q23", "diger_varlik_bnk",  "bie_odana6"),
    ("TP.ODANA6.Q24", "diger_varlik_dgr",  "bie_odana6"),
    ("TP.ODANA6.Q25", "diger_yuk",         "bie_odana6"),
    ("TP.ODANA6.Q26", "diger_yuk_tcmb",    "bie_odana6"),
    ("TP.ODANA6.Q27", "diger_yuk_gh",      "bie_odana6"),
    ("TP.ODANA6.Q28", "diger_yuk_bnk",     "bie_odana6"),
    ("TP.ODANA6.Q29", "diger_yuk_dgr",     "bie_odana6"),
    ("TP.ODANA6.Q30", "csf_toplam",        "bie_odana6"),
    ("TP.ODANA6.Q31", "net_hata_noksan",   "bie_odana6"),
    ("TP.ODANA6.Q32", "genel_denge",       "bie_odana6"),
    ("TP.ODANA6.Q33", "rezerv_varliklar",  "bie_odana6"),
    ("TP.ODANA6.Q34", "resmi_rezervler",   "bie_odana6"),
    ("TP.ODANA6.Q35", "imf_kredileri",     "bie_odana6"),
    ("TP.ODANA6.Q36", "od_finansmani",     "bie_odana6"),
]

# --- Ayrıntılı sunum: vade kırılımı (kaliteli finansman & roll-over payda) --
AYRINTI = [
    ("TP.ODEAYRSUNUM6.Q1",   "ay_cari",            "bie_odeayrsunum6"),
    ("TP.ODEAYRSUNUM6.Q99",  "ay_sermaye_hesabi",  "bie_odeayrsunum6"),
    ("TP.ODEAYRSUNUM6.Q101", "ay_fin_hesabi",      "bie_odeayrsunum6"),
    ("TP.ODEAYRSUNUM6.Q102", "ay_dyy_net",         "bie_odeayrsunum6"),
    ("TP.ODEAYRSUNUM6.Q103", "ay_dyy_varlik",      "bie_odeayrsunum6"),
    ("TP.ODEAYRSUNUM6.Q108", "ay_dyy_yuk",         "bie_odeayrsunum6"),
    ("TP.ODEAYRSUNUM6.Q114", "ay_portfoy_net",     "bie_odeayrsunum6"),
    ("TP.ODEAYRSUNUM6.Q119", "ay_portfoy_yuk",     "bie_odeayrsunum6"),
    ("TP.ODEAYRSUNUM6.Q214", "ay_turev_net",       "bie_odeayrsunum6"),
    ("TP.ODEAYRSUNUM6.Q136", "ay_diger_net",       "bie_odeayrsunum6"),
    ("TP.ODEAYRSUNUM6.Q137", "ay_mevduat_net",     "bie_odeayrsunum6"),
    ("TP.ODEAYRSUNUM6.Q143", "ay_mevduat_yuk",     "bie_odeayrsunum6"),
    ("TP.ODEAYRSUNUM6.Q147", "ay_mevduat_yuk_bnk", "bie_odeayrsunum6"),
    ("TP.ODEAYRSUNUM6.Q152", "ay_krediler_net",    "bie_odeayrsunum6"),
    ("TP.ODEAYRSUNUM6.Q157", "ay_kredi_yuk",       "bie_odeayrsunum6"),
    # Bankalar — kısa/uzun vade ve uzun vadenin kullanım/geri ödeme bacakları
    ("TP.ODEAYRSUNUM6.Q166", "ay_kredi_bnk",       "bie_odeayrsunum6"),
    ("TP.ODEAYRSUNUM6.Q167", "ay_kredi_bnk_kv",    "bie_odeayrsunum6"),
    ("TP.ODEAYRSUNUM6.Q168", "ay_kredi_bnk_uv",    "bie_odeayrsunum6"),
    ("TP.ODEAYRSUNUM6.Q169", "ay_kredi_bnk_uv_kul", "bie_odeayrsunum6"),
    ("TP.ODEAYRSUNUM6.Q170", "ay_kredi_bnk_uv_ode", "bie_odeayrsunum6"),
    # Diğer sektörler (reel sektör)
    ("TP.ODEAYRSUNUM6.Q179", "ay_kredi_dgr",       "bie_odeayrsunum6"),
    ("TP.ODEAYRSUNUM6.Q180", "ay_kredi_dgr_kv",    "bie_odeayrsunum6"),
    ("TP.ODEAYRSUNUM6.Q181", "ay_kredi_dgr_uv",    "bie_odeayrsunum6"),
    ("TP.ODEAYRSUNUM6.Q182", "ay_kredi_dgr_uv_kul", "bie_odeayrsunum6"),
    ("TP.ODEAYRSUNUM6.Q183", "ay_kredi_dgr_uv_ode", "bie_odeayrsunum6"),
    # Genel hükümet uzun vade
    ("TP.ODEAYRSUNUM6.Q176", "ay_kredi_gh_uv",     "bie_odeayrsunum6"),
    ("TP.ODEAYRSUNUM6.Q177", "ay_kredi_gh_uv_kul", "bie_odeayrsunum6"),
    ("TP.ODEAYRSUNUM6.Q178", "ay_kredi_gh_uv_ode", "bie_odeayrsunum6"),
    # Ticari krediler, SDR, rezerv, NHN
    ("TP.ODEAYRSUNUM6.Q184", "ay_ticari_kredi",    "bie_odeayrsunum6"),
    ("TP.ODEAYRSUNUM6.Q203", "ay_sdr",             "bie_odeayrsunum6"),
    ("TP.ODEAYRSUNUM6.Q204", "ay_rezerv",          "bie_odeayrsunum6"),
    ("TP.ODEAYRSUNUM6.Q210", "ay_nhn",             "bie_odeayrsunum6"),
]

# --- Dış borç çevirme oranları (TCMB'nin kendi hesabı) ---------------------
ROLL = [
    ("TP.ODEROLL.K1", "roll_bank",        "bie_oderoll"),
    ("TP.ODEROLL.K2", "roll_diger",       "bie_oderoll"),
    ("TP.ODEROLL.K3", "roll_bank_tahvil", "bie_oderoll"),
    ("TP.ODEROLL.K4", "roll_diger_tahvil", "bie_oderoll"),
]

# --- Yurt dışında ihraç edilen borçlanma senetleri (eurobond akımı) --------
EUROBOND = [
    ("TP.ODEYDIEBS.A1",   "eb_kullanim",     "bie_odeydiebs"),
    ("TP.ODEYDIEBS.A11",  "eb_kullanim_uv",  "bie_odeydiebs"),
    ("TP.ODEYDIEBS.A112", "eb_kullanim_gh",  "bie_odeydiebs"),
    ("TP.ODEYDIEBS.A113", "eb_kullanim_bnk", "bie_odeydiebs"),
    ("TP.ODEYDIEBS.A114", "eb_kullanim_dgr", "bie_odeydiebs"),
    ("TP.ODEYDIEBS.A2",   "eb_odeme",        "bie_odeydiebs"),
    ("TP.ODEYDIEBS.A21",  "eb_odeme_uv",     "bie_odeydiebs"),
]

# --- Dış borç anapara/faiz ödemeleri (HAFTALIK — hattın en taze serisi) ----
# Aylık ödemeler dengesi ~45–55 gün gecikmeliyken bu tablo bir hafta gerideki
# çarşambaya kadar dolu. Aylık hattın "son ay"ını bu seriyle KARIŞTIRMAK
# sessiz bayatlamanın tersi bir hata olur: sayfa ayrı iki dönem gösterir.
BORCODEME = [
    ("TP.D1TOP",  "borc_odeme_top",  "bie_dbafod"),
    ("TP.D2HAZ",  "borc_odeme_haz",  "bie_dbafod"),
    ("TP.D3DIG",  "borc_odeme_dig",  "bie_dbafod"),
    ("TP.D4TCMB", "borc_odeme_tcmb", "bie_dbafod"),
]

# --- GSYH & kur (cari denge / GSYH oranı için) -----------------------------
# BİRİM TUZAĞI: GSYH ÜÇ AYLIK ve BİN TL; ödemeler dengesi AYLIK ve MİLYON USD.
# Oran hesaplanmadan önce GSYH milyon USD'ye çevrilir:
#   GSYH_mnUSD = GSYH_binTL / 1000 / ceyrek_ortalama_USDTRY
# ( bin TL → milyon TL: /1000 ; milyon TL → milyon USD: /kur )
GSYH = [
    ("TP.GSYIH20.BY.B1GQ", "gsyh_cari_tl", "bie_gsyhhrccar"),
]
REZERV = [
    ("TP.AB.B4", "rezerv_stok", "bie_abreserv"),   # mn USD, STOK (akım DEĞİL)
]
KUR = [
    ("TP.DK.USD.A.YTL", "usdtry", "bie_dkdovytl"),
]

KUMELER = {
    "cari": CARI, "cekirdek": CEKIRDEK, "finans": FINANS,
    "ayrinti": AYRINTI, "roll": ROLL, "eurobond": EUROBOND,
    "borcodeme": BORCODEME, "gsyh": GSYH, "kur": KUR, "rezerv": REZERV,
}


# --------------------------------------------------------------------------- keşif
def kesfet() -> dict:
    print("EVDS3 → ödemeler dengesi & dış finansman KEŞFİ")
    print(f"  anahtar: {'ortam değişkeni' if os.environ.get('TTO_EVDS_KEY') else 'dosya'}")

    gruplar = sorted({g for k in KUMELER.values() for _, _, g in k})
    meta_grup = {}
    for g in gruplar:
        m = datagrup_meta(g)
        if not m:
            uyar(f"VERİ GRUBU META YOK: {g}")
            continue
        meta_grup[g] = {
            "ad": m.get("DATAGROUP_NAME"),
            "birim": m.get("BIRIMI"),
            "birim_en": m.get("BIRIMI_EN"),
            "frekans": m.get("FREQUENCY_STR"),
            "kaynak": m.get("DATASOURCE"),
            "baslangic": m.get("START_DATE"),
            "bitis": m.get("END_DATE"),
            "not": (m.get("NOTE") or "").strip(),
        }
        print(f"  grup {g:<22} {m.get('FREQUENCY_STR'):<12} "
              f"birim={m.get('BIRIMI')!r}  {m.get('START_DATE')}→{m.get('END_DATE')}")

    # Seri meta verisi (ad, başlangıç) — serieList'ten
    seri_meta: dict[str, dict] = {}
    for g in gruplar:
        try:
            seri_meta.update(seri_listesi(g))
        except Exception as ex:
            uyar(f"serieList düştü: {g} — {ex}")

    seriler: dict[str, dict] = {}
    veriler: dict[str, pd.Series] = {}
    for kume, liste in KUMELER.items():
        print(f"\n— {kume} ({len(liste)} seri)")
        for kod, ad, grup in liste:
            sm = seri_meta.get(kod, {})
            frek = sm.get("FREQUENCY_STR") or meta_grup.get(grup, {}).get("frekans")
            bicim = BICIM.get(frek or "", "ay")
            bas = sm.get("START_DATE") or meta_grup.get(grup, {}).get("baslangic")
            bas_iso = (pd.Timestamp(dt.datetime.strptime(bas, "%d-%m-%Y")).strftime("%Y-%m-%d")
                       if bas else "1990-01-01")
            s = seri_cek(kod, bicim, bas_iso)
            kayit = {
                "kod": kod, "ad_kisa": ad, "grup": grup,
                "ad": sm.get("SERIE_NAME"),
                "birim": meta_grup.get(grup, {}).get("birim"),
                "frekans": frek,
                "baslangic": None, "bitis": None, "n": int(len(s)),
                "son_deger": None, "dogrulandi": False,
            }
            if len(s):
                kayit.update({
                    "baslangic": s.index[0].strftime("%Y-%m-%d"),
                    "bitis": s.index[-1].strftime("%Y-%m-%d"),
                    "son_deger": float(s.iloc[-1]),
                    "dogrulandi": True,
                })
                veriler[ad] = s
                print(f"  ✓ {kod:<24} n={len(s):<5} {s.index[0]:%Y-%m}→"
                      f"{s.index[-1]:%Y-%m}  son={s.iloc[-1]:,.1f}")
            else:
                print(f"  ✗ {kod:<24} VERİ YOK")
                uyar(f"BOŞ SERİ: {kod} ({ad}) — listeye alınmamalı.")
            seriler[ad] = kayit

    return {"gruplar": meta_grup, "seriler": seriler}, veriler


# --------------------------------------------------------------------------- kimlik
def kimlik_denetimi(v: dict[str, pd.Series]) -> dict:
    """Formül denetimi: tanımlar tutmuyorsa kod ya da işaret yanlıştır."""
    rapor: dict = {}

    def kontrol(ad: str, sol: pd.Series, sag: pd.Series, esik: float, birim: str):
        d = pd.DataFrame({"s": sol, "r": sag}).dropna()
        if d.empty:
            rapor[ad] = {"gecti": False, "not": "seriler kesişmiyor"}
            uyar(f"KİMLİK sınanamadı: {ad}")
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
        im = "✓" if fark.max() <= esik else "✗"
        print(f"  {im} {ad}: n={len(d)}, maks {fark.max():,.2f} {birim} "
              f"({fark.idxmax():%Y-%m})")
        if fark.max() > esik:
            uyar(f"KİMLİK BOZUK: {ad} — maks {fark.max():,.2f} {birim} "
                 f"({fark.idxmax():%Y-%m}), eşik {esik}.")

    print("\n— kimlik denetimleri")
    g = v.get
    # (1) İki sunum aynı cari dengeyi vermeli.
    if g("cari_denge") is not None and g("ay_cari") is not None:
        kontrol("analitik Q01 = ayrıntılı Q1", v["cari_denge"], v["ay_cari"],
                1.0, "mn USD")
    # (2) Çekirdek cari denge TANIMI: K10 = K1 − K4 − K7
    if all(g(k) is not None for k in ("hc_cari", "hc_altin_net", "hc_enerji_net",
                                      "hc_cekirdek")):
        kontrol("K10 = K1 − K4 − K7", v["hc_cekirdek"],
                v["hc_cari"] - v["hc_altin_net"] - v["hc_enerji_net"],
                1.0, "mn USD")
    # (3) Altın net = ihracat − ithalat
    if all(g(k) is not None for k in ("hc_altin_net", "hc_altin_ihr", "hc_altin_ith")):
        kontrol("K4 = K2 − K3", v["hc_altin_net"],
                v["hc_altin_ihr"] - v["hc_altin_ith"], 1.0, "mn USD")
    # (4) Analitik ile hariç-tablosu aynı cari dengeyi vermeli
    if g("cari_denge") is not None and g("hc_cari") is not None:
        kontrol("Q01 = HARICCARIACIK.K1", v["cari_denge"], v["hc_cari"],
                1.0, "mn USD")
    # (5) ANALİTİK sunumun finans hesabı REZERVİ İÇERMEZ.
    #     ÖLÇÜLDÜ: Q13 = Σ(varlık − yükümlülük), rezerv HARİÇ. Rezervi de
    #     toplama katmak Mart 2026'da 43,4 mia USD sapma verir — bu bir veri
    #     hatası değil, sunum farkıdır. Ayrıntılı sunumda (Q101) rezerv İÇERİDE.
    #     İki tabloyu aynı grafikte "finans hesabı" diye yan yana koymak bu
    #     yüzden yanlıştır; hangi tanımın kullanıldığı sayfada yazılmalı.
    bilesen = ["dyy_varlik", "dyy_yukumluluk", "port_varlik", "port_yukumluluk",
               "turev_varlik", "turev_yukumluluk", "diger_varlik", "diger_yuk"]
    if all(g(k) is not None for k in bilesen + ["fin_hesabi"]):
        toplam = (v["dyy_varlik"] - v["dyy_yukumluluk"]
                  + v["port_varlik"] - v["port_yukumluluk"]
                  + v["turev_varlik"] - v["turev_yukumluluk"]
                  + v["diger_varlik"] - v["diger_yuk"])
        kontrol("Q13 = Σ(varlık − yükümlülük), rezerv HARİÇ", v["fin_hesabi"],
                toplam, 5.0, "mn USD")
    # (6) Analitik sunumun ödemeler dengesi kimliği:
    #        CA + KA + NHN = FA(rezerv hariç) + Rezerv Varlıklar
    #     Rezerv işareti BPM6 standardı: POZİTİF = rezerv ARTIŞI (net varlık
    #     edinimi). Mart 2026'da Q33 = −43.420 ve resmi rezerv stoku aynı ay
    #     59,5 mia USD düşmüş — işaret yönü stokla SINANDI (bkz. isaret_denetimi).
    if all(g(k) is not None for k in ("cari_denge", "sermaye_hesabi",
                                      "net_hata_noksan", "fin_hesabi",
                                      "rezerv_varliklar")):
        kontrol("CA + KA + NHN = FA(rez.hariç) + Rezerv",
                v["cari_denge"] + v["sermaye_hesabi"] + v["net_hata_noksan"],
                v["fin_hesabi"] + v["rezerv_varliklar"], 5.0, "mn USD")
    # (6b) AYRINTILI sunumda finans hesabı rezervi İÇERİR: CA + KA + NHN = Q101
    if all(g(k) is not None for k in ("ay_cari", "ay_sermaye_hesabi",
                                      "ay_nhn", "ay_fin_hesabi")):
        kontrol("ayrıntılı: Q1 + Q99 + Q210 = Q101", v["ay_fin_hesabi"],
                v["ay_cari"] + v["ay_sermaye_hesabi"] + v["ay_nhn"],
                5.0, "mn USD")
    # (6c) İki sunum arasındaki köprü: Q101 = Q13 + Q33
    if all(g(k) is not None for k in ("ay_fin_hesabi", "fin_hesabi",
                                      "rezerv_varliklar")):
        kontrol("köprü: Q101 = Q13 + Q33", v["ay_fin_hesabi"],
                v["fin_hesabi"] + v["rezerv_varliklar"], 5.0, "mn USD")
    # (6d) Ayrıntılı sunumun bileşen toplamı
    if all(g(k) is not None for k in ("ay_fin_hesabi", "ay_dyy_net",
                                      "ay_portfoy_net", "ay_turev_net",
                                      "ay_diger_net", "ay_rezerv")):
        kontrol("Q101 = Q102+Q114+Q214+Q136+Q204", v["ay_fin_hesabi"],
                v["ay_dyy_net"] + v["ay_portfoy_net"] + v["ay_turev_net"]
                + v["ay_diger_net"] + v["ay_rezerv"], 5.0, "mn USD")
    # (7) Uzun vadeli kredi: net yükümlülük = kullanım − geri ödeme
    for etiket, uv, kul, ode in (
            ("bankalar UV", "ay_kredi_bnk_uv", "ay_kredi_bnk_uv_kul", "ay_kredi_bnk_uv_ode"),
            ("diğer sekt. UV", "ay_kredi_dgr_uv", "ay_kredi_dgr_uv_kul", "ay_kredi_dgr_uv_ode"),
            ("gen. hükümet UV", "ay_kredi_gh_uv", "ay_kredi_gh_uv_kul", "ay_kredi_gh_uv_ode")):
        if all(g(k) is not None for k in (uv, kul, ode)):
            kontrol(f"{etiket}: net = kullanım − ödeme", v[uv],
                    v[kul] - v[ode], 1.0, "mn USD")
    # (8) TCMB'nin roll-over oranı ile bizim UV kullanım/ödeme oranımız
    #     AYNI OLMAK ZORUNDA DEĞİL (TCMB kısa+uzun vadeyi birlikte alıyor);
    #     ölçüp farkı raporluyoruz ki sayfada yanlış eşitlik kurulmasın.
    if all(g(k) is not None for k in ("roll_bank", "ay_kredi_bnk_uv_kul",
                                      "ay_kredi_bnk_uv_ode")):
        bizim = (100 * v["ay_kredi_bnk_uv_kul"]
                 / v["ay_kredi_bnk_uv_ode"].replace(0, pd.NA)).dropna()
        d = pd.DataFrame({"tcmb": v["roll_bank"], "uv": bizim}).dropna()
        if len(d):
            fark = (d["tcmb"] - d["uv"]).abs()
            rapor["roll_bank: TCMB vs yalnız-UV"] = {
                "n": int(len(d)),
                "ortalama_fark_puan": float(fark.mean()),
                "maks_fark_puan": float(fark.max()),
                "son_tcmb": float(d["tcmb"].iloc[-1]),
                "son_uv": float(d["uv"].iloc[-1]),
                "gecti": True,
                "not": ("TCMB oranı KISA+UZUN vade ve tahvil kapsamını içerir; "
                        "yalnız-UV oranı ondan sapar. Aynı grafikte iki oran "
                        "AYNI seri gibi sunulamaz."),
            }
            print(f"  i roll_bank TCMB vs yalnız-UV: ortalama fark "
                  f"{fark.mean():.1f} puan, son {d['tcmb'].iloc[-1]:.1f} vs "
                  f"{d['uv'].iloc[-1]:.1f}")
    return rapor


# --------------------------------------------------------------------------- işaret
def isaret_denetimi(v: dict[str, pd.Series]) -> dict:
    """Rezerv AKIMININ işaret yönünü STOKLA sına.

    Ödemeler dengesindeki rezerv kalemi bir AKIM; TP.AB.B4 bir STOK. Akım
    pozitifken stok artıyorsa işaret BPM6 standardındadır (pozitif = rezerv
    edinimi). Ters çıkarsa grafikte rezerv çubuğu ters yöne bakar ve
    "rezerv eridi" denecek yerde "rezerv biriktirdi" yazılır.

    Not: stok ile akım BİREBİR tutmaz — stok altın ve parite DEĞERLEME
    etkisini de taşır, akım taşımaz. Bu yüzden eşitlik değil, YÖN sınanır.
    """
    r: dict = {}
    if "rezerv_stok" not in v or "resmi_rezervler" not in v:
        return r
    print("\n— işaret denetimi (rezerv akımı ↔ rezerv stoku)")
    d = pd.DataFrame({"stok": v["rezerv_stok"], "akim": v["resmi_rezervler"]}).dropna()
    d = d.loc["2010":]
    d["stok_d"] = d["stok"].diff()
    dd = d[["stok_d", "akim"]].dropna()
    kor = float(dd["stok_d"].corr(dd["akim"]))
    ayni_yon = float((dd["stok_d"] * dd["akim"] > 0).mean())
    r["rezerv_akim_stok"] = {
        "n": int(len(dd)),
        "korelasyon": round(kor, 3),
        "ayni_yon_orani": round(ayni_yon, 3),
        "gecti": bool(kor > 0.3),
        "yorum": ("pozitif korelasyon → akım POZİTİF = rezerv ARTIŞI (BPM6)"
                  if kor > 0 else "NEGATİF korelasyon → işaret ters, çevir"),
    }
    print(f"  {'✓' if kor > 0.3 else '✗'} aylık korelasyon={kor:.3f}, "
          f"aynı yön oranı={ayni_yon:.0%} → {r['rezerv_akim_stok']['yorum']}")
    if kor <= 0.3:
        uyar("İŞARET ŞÜPHESİ: rezerv akımı ile stok değişimi aynı yönde değil.")
    return r


# --------------------------------------------------------------------------- ölü seri
def olu_seri_denetimi(v: dict[str, pd.Series]) -> list[str]:
    """SIFIR ≠ VERİ. Son 60 ayın tamamı 0 olan seri dolu görünür ama bilgi
    taşımaz; grafikte sıfır çizgisi olarak durur ve kalem varmış izlenimi verir."""
    olu = []
    for ad, s in v.items():
        son = s.iloc[-60:]
        if len(son) >= 24 and (son == 0).all():
            olu.append(ad)
            uyar(f"ÖLÜ SERİ: '{ad}' son {len(son)} dönemin TAMAMINDA 0 — "
                 "hatta alınmamalı ya da 'yok' olarak işlenmeli.")
    return olu


# --------------------------------------------------------------------------- birim
def birim_denetimi(v: dict[str, pd.Series]) -> dict:
    """Mertebe kıyası. GSYH bin TL, ödemeler dengesi milyon USD.

    Referans: Türkiye'nin yıllık GSYH'si son yıllarda 1,0–2,0 trilyon USD
    bandında. Dönüşüm doğruysa 4 çeyreklik toplam bu banda düşer; bin TL'yi
    milyon TL sanmak sonucu 1000 kat küçültür, kura bölmemek 30–50 kat büyütür.
    Bant BİLEREK geniş: burada aranan "doğru sayı" değil, DOĞRU MERTEBE.
    """
    r: dict = {}
    if "gsyh_cari_tl" not in v or "usdtry" not in v:
        return r
    gsyh = v["gsyh_cari_tl"]                    # bin TL, çeyrek
    kur = v["usdtry"]                           # TL/USD, günlük
    # Çeyrek ortalama kur: çeyreğin İŞ GÜNÜ ortalaması (ay sonu kuru DEĞİL —
    # akım büyüklüğü olan GSYH'yi nokta kurla bölmek çeyrek içi kur hareketini
    # tamamen yutar).
    kur_c = kur.resample("QE").mean()
    d = pd.DataFrame({"gsyh_bin_tl": gsyh, "kur": kur_c}).dropna()
    # bin TL → milyon TL (/1000) → milyon USD (/kur)
    d["gsyh_mn_usd"] = d["gsyh_bin_tl"] / 1000.0 / d["kur"]
    y = d["gsyh_mn_usd"].rolling(4).sum().dropna()
    r["gsyh_usd_4ceyrek"] = {
        "son_donem": str(y.index[-1].date()),
        "son_deger_mn_usd": float(y.iloc[-1]),
        "son_deger_trilyon_usd": round(float(y.iloc[-1]) / 1e6, 3),
        "referans_bant_trilyon_usd": [1.0, 2.0],
        "gecti": bool(1.0e6 <= y.iloc[-1] <= 2.0e6),
        "not": ("bin TL → /1000 → milyon TL → /çeyrek ort. USDTRY → milyon USD; "
                "4 çeyreklik toplam yıllık GSYH'dir."),
    }
    im = "✓" if r["gsyh_usd_4ceyrek"]["gecti"] else "✗"
    print(f"\n— birim denetimi\n  {im} 4 çeyreklik GSYH = "
          f"{y.iloc[-1] / 1e6:.3f} trilyon USD "
          f"({y.index[-1].year}-Ç{y.index[-1].quarter}) "
          f"— beklenen bant 1,0–2,0")
    if not r["gsyh_usd_4ceyrek"]["gecti"]:
        uyar("BİRİM ŞÜPHESİ: GSYH USD karşılığı beklenen bandın dışında.")
    # Cari denge / GSYH: 12 aylık birikimli CA ile.
    # FREKANS TUZAĞI: cari denge AYLIK ve ~45 gün gecikmeli, GSYH ÜÇ AYLIK ve
    # ~75 gün gecikmeli. Oran, GSYH'nin son ÇEYREĞİNDE durur; ödemeler dengesi
    # ondan 1–2 ay ilerdedir. Oranı "son ay" diye sunmak sessiz bayatlamadır —
    # ozet.json'a oranın KENDİ dönemi (_tarih2) ayrı yazılmalı.
    if "cari_denge" in v:
        ca12 = v["cari_denge"].rolling(12).sum().dropna()
        ca_c = ca12.resample("QE").last()
        dd = pd.DataFrame({"ca": ca_c, "gsyh": y}).dropna()
        if len(dd):
            oran = 100 * dd["ca"] / dd["gsyh"]
            gecikme_ay = round(
                (v["cari_denge"].index[-1] - oran.index[-1]).days / 30.44, 1)
            r["cari_gsyh_oran"] = {
                "son_donem": str(oran.index[-1].date()),
                "son_yuzde": round(float(oran.iloc[-1]), 2),
                "min_yuzde": round(float(oran.min()), 2),
                "maks_yuzde": round(float(oran.max()), 2),
                "cari_denge_son_ay": str(v["cari_denge"].index[-1].date()),
                "oran_gecikmesi_ay": gecikme_ay,
                "gecti": bool(-15 < oran.iloc[-1] < 10),
                "not": ("12 aylık birikimli CA / 4 çeyreklik GSYH (ikisi de mn "
                        "USD). Oran GSYH'nin son çeyreğinde durur; aylık cari "
                        "denge ondan ilerdedir."),
            }
            print(f"  i cari denge/GSYH son = %{oran.iloc[-1]:.2f} "
                  f"({oran.index[-1].year}-Ç{oran.index[-1].quarter}; "
                  f"tarihçe %{oran.min():.2f} … %{oran.max():.2f})")
            print(f"  i oran, aylık cari dengeden {gecikme_ay} ay geride "
                  f"(GSYH yayım gecikmesi)")
    return r


# --------------------------------------------------------------------------- ana
def kos() -> dict:
    t0 = time.time()
    kesif, veriler = kesfet()
    kim = kimlik_denetimi(veriler)
    kim.update(isaret_denetimi(veriler))
    olu = olu_seri_denetimi(veriler)
    bir = birim_denetimi(veriler)

    aylik = [s for a, s in veriler.items()
             if kesif["seriler"].get(a, {}).get("frekans") == "AYLIK"]
    ceyrek = [s for a, s in veriler.items()
              if kesif["seriler"].get(a, {}).get("frekans") == "ÜÇ AYLIK"]
    son_ay = max((s.index[-1] for s in aylik), default=None)
    son_ceyrek = max((s.index[-1] for s in ceyrek), default=None)

    out = {
        "_kosum": dt.datetime.now().isoformat(timespec="seconds"),
        # TAZELİK: dönem VERİDEN okunur, sabit tarih yazılmaz.
        "_tarih": son_ay.strftime("%Y-%m-%d") if son_ay is not None else None,
        "_tarih2": son_ceyrek.strftime("%Y-%m-%d") if son_ceyrek is not None else None,
        "gruplar": kesif["gruplar"],
        "seriler": kesif["seriler"],
        "kimlik": kim,
        "birim": bir,
        "olu_seriler": olu,
        "uyarilar": list(_UYARI),
        "sure_sn": round(time.time() - t0, 1),
    }
    # HER koşuda yeniden yazılır — "dosya varsa atla" yok.
    (VERI / "kesif_sonuc.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    dogru = sum(1 for s in kesif["seriler"].values() if s["dogrulandi"])
    print(f"\n{dogru}/{len(kesif['seriler'])} seri doğrulandı"
          + (f" · son ay {son_ay:%Y-%m}" if son_ay is not None else "")
          + (f" · son çeyrek {son_ceyrek.year}-Ç{son_ceyrek.quarter}"
             if son_ceyrek is not None else ""))
    print(f"yazıldı: {VERI / 'kesif_sonuc.json'} ({out['sure_sn']} sn)")
    if _UYARI:
        print(f"[{len(_UYARI)} uyarı]")
    return out


if __name__ == "__main__":
    kos()
