# -*- coding: utf-8 -*-
"""Merkezi Yönetim Bütçesi & Borç Stoku — veri katmanı (EVDS3).

Ne yapar
--------
1. EVDS3 REST servisinden bütçe gelir/gider kalemlerini, genel bütçe denge ve
   FİNANSMAN tablosunu, iç borç stokunu, brüt dış borcu, DİBS ve eurobond
   stoklarını (yazılı + piyasa değeri, sahiplik, vade, para birimi), merkezi
   yönetim finansal hesaplarını, GSYH'yi, TÜFE'yi ve kuru çeker.
2. BİRİMİ EVDS'ten OKUR. Bu hattın en pahalı hatası birim karıştırmaktır:
   aynı sayfada dört birim dolaşıyor (bin TL · milyon TL · milyon ABD doları ·
   endeks · TL). Birim SERİ düzeyinde değil VERİ GRUBU düzeyinde yayımlanıyor
   (`datagroups` yanıtındaki `BIRIMI` alanı). Kodda beklenen birim yazılı, ama
   HER KOŞUDA EVDS'ten okunanla karşılaştırılır; uyuşmazsa hat DURUR.
3. Her seriyi TTL'li önbelleğe (data/cache/*.csv) yazar; ağ düşerse eski
   önbelleğe düşer ama SESSİZ kalmaz — uyarı basar, veri_durum.json'a taşınır.
4. AİLE BAZLI tazelik denetimi yapar. Bu hatta YEDİ ayrı yayım ritmi var
   (bütçe/iç borç · dış borç · haftalık menkul kıymet · üç aylık GSYH · üç
   aylık finansal hesaplar · TÜFE · kur). Tek eşik her koşuda yanlış alarm
   üretirdi. Finansal hesaplar GSYH'den AYRI bir ailedir: ikisi aynı çeyreklik
   dosyada yan yana durur ama ayrı kurumlar ayrı takvimle yayımlar ve 09.09.2026'da
   ölçüldü — GSYH 2026-Ç2'deyken finansal hesaplar 2026-Ç1'de (161 gün), tek
   ailede `max()` bu bacağın gecikmesini GSYH'nin arkasına gizliyordu.
5. Kimlik denetimleri koşar (toplama kimlikleri + birim mertebesi). Durdurucu
   olanlar düşerse hat DURUR — yanlış birimle çizilmiş dolu bir grafik, boş
   grafikten kötüdür.

Uç nokta notu
-------------
`evds2.tcmb.gov.tr/service/evds` ÖLÜ. Çalışan taban:

    https://evds3.tcmb.gov.tr/igmevdsms-dis/{uç}{param}={değer}&...

Sorgu dizesi `?` ile başlamaz; anahtar URL'de DEĞİL `key:` HTTP başlığında
gider. Tek istek ~1000 SATIRLA sınırlı ve aralığın SONUNDAN geriye doldurur,
gerisini uyarı vermeden kırpar. Bu hattaki en uzun seri aylık (2003→) ≈ 280
satır, haftalık (2020→) ≈ 310, üç aylık (2003→) ≈ 95 — hiçbiri 1000'i aşmıyor.
YALNIZ günlük kur serisi aşıyor; o 366 günlük parçalarla çekilir.

DÖRT tarih biçimi, ÜÇ ayrıştırıcı:
    GÜNLÜK / HAFTALIK(CUMA) → "14-08-2026"   (%d-%m-%Y)
    AYLIK                   → "2026-6"       (%Y-%m)
    ÜÇ AYLIK                → "2026-Q2"      (int('Q2') tuzağı burada)

Koşum:  python3 veri.py  [--yenile]
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import re
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
# EVDS anahtarı kaynak koda GÖMÜLMEZ. Arama sırası Fonlama/veri.py ile AYNI:
#   TTO_EVDS_KEY → <proje>/.evds_key → kök/.evds_key → kardeş TCMBNetRezerv/.evds_key
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
KATALOG_TTL_SAAT = 168        # birim/ad ağacı sık değişmez
DEMET = 6                     # tek istekte kaç seri (satır sınırı seri sayısına bağlı DEĞİL)
PARCA_GUN_GUNLUK = 366        # yalnız günlük kur serisi 1000 satırı aşıyor

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


def _cek(yol: str, deneme: int = 3):
    """EVDS3'ten JSON. Anahtar `key:` BAŞLIĞINDA gider, URL'de değil."""
    url = f"{BASE}/{yol}"
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
def _ayristir(items, kolonlar: list[str], bicim: str) -> pd.DataFrame:
    if not items:
        return pd.DataFrame()
    df = pd.DataFrame(items)
    if "Tarih" not in df.columns:
        return pd.DataFrame()
    ham = df["Tarih"].astype(str)
    if bicim == "gun":                       # GÜNLÜK + HAFTALIK(CUMA)
        t = pd.to_datetime(ham, format="%d-%m-%Y", errors="coerce")
    elif bicim == "ay":                      # "2026-6" → ay BAŞI
        t = pd.to_datetime(ham, format="%Y-%m", errors="coerce")
    elif bicim == "ceyrek":                  # "2026-Q2" — int('Q2') tuzağı
        t = pd.PeriodIndex(ham.str.replace("-", "", regex=False),
                           freq="Q").to_timestamp(how="end").normalize()
        t = pd.Series(t, index=df.index)
    else:
        raise ValueError(f"bilinmeyen biçim: {bicim}")
    out = {}
    for k in kolonlar:
        if k in df.columns:
            out[k] = pd.to_numeric(df[k].replace("", None), errors="coerce")
    if not out:
        return pd.DataFrame()
    d = pd.DataFrame(out)
    d.index = pd.DatetimeIndex(t)
    return d[~d.index.isna()].sort_index()


def _demet_cek(kodlar: list[str], bas: pd.Timestamp, son: pd.Timestamp,
               bicim: str, parca_gun: int | None) -> pd.DataFrame:
    """Bir seri demetini çeker. Bir kod geçersizse EVDS BÜTÜN isteği reddeder;
    o yüzden demet düşerse seriler tek tek denenir — bir bozuk kod diğer beşini
    götürmesin."""
    guvenli = [k.replace(".", "_") for k in kodlar]
    parcalar: list[pd.DataFrame] = []
    imlec = bas
    while imlec <= son:
        sonu = son if parca_gun is None else min(
            imlec + pd.Timedelta(days=parca_gun - 1), son)
        url = (f"series={'-'.join(kodlar)}"
               f"&startDate={imlec:%d-%m-%Y}&endDate={sonu:%d-%m-%Y}&type=json")
        try:
            p = _ayristir(_cek(url).get("items", []), guvenli, bicim)
        except Exception as ex:
            uyar(f"demet düştü ({', '.join(kodlar)}: {ex}); tek tek deneniyor.")
            tekler = []
            for k, g in zip(kodlar, guvenli):
                try:
                    u = (f"series={k}&startDate={imlec:%d-%m-%Y}"
                         f"&endDate={sonu:%d-%m-%Y}&type=json")
                    d = _ayristir(_cek(u).get("items", []), [g], bicim)
                    if len(d):
                        tekler.append(d)
                except Exception as ex2:
                    uyar(f"SERİ ALINAMADI: {k} — {ex2}")
                time.sleep(0.2)
            p = pd.concat(tekler, axis=1) if tekler else pd.DataFrame()
        if len(p):
            parcalar.append(p)
        imlec = sonu + pd.Timedelta(days=1)
        time.sleep(0.2)
    if not parcalar:
        return pd.DataFrame()
    d = pd.concat(parcalar)
    return d[~d.index.duplicated(keep="last")].sort_index()


def _cache_yolu(kod: str, bicim: str) -> pathlib.Path:
    return CACHE / f"evds_{bicim}_{kod.replace('.', '_')}.csv"


def cek_kume(kodlar: dict[str, str], bicim: str, bas: str,
             parca_gun: int | None = None, yenile: bool = False,
             etiket: str = "") -> pd.DataFrame:
    """ad → EVDS kodu sözlüğünü çeker.

    Önbellek SERİ BAZINDA tutulur (demet bileşimi değişince önbellek
    geçersizleşmesin). TTL 12 saat: HMB bütçe gerçekleşmelerini, TÜİK GSYH'yi
    ve TCMB finansal hesapları GERİYE DÖNÜK REVİZE eder — "dosya varsa atla"
    bu hatta revizyonu sonsuza dek gizlerdi.
    """
    def cy(kod):
        return _cache_yolu(kod, bicim)

    eksik = [a for a, k in kodlar.items()
             if yenile or not _taze(cy(k), CACHE_TTL_SAAT)]
    if eksik:
        print(f"  {etiket}: {len(eksik)}/{len(kodlar)} seri EVDS'ten çekiliyor "
              f"({-(-len(eksik) // DEMET)} demet)", flush=True)
        bugun = pd.Timestamp.today().normalize()
        for i in range(0, len(eksik), DEMET):
            grup = [kodlar[a] for a in eksik[i:i + DEMET]]
            d = _demet_cek(grup, pd.Timestamp(bas), bugun, bicim, parca_gun)
            for kod in grup:
                g = kod.replace(".", "_")
                if g in d.columns and d[g].notna().any():
                    s = d[g].dropna()
                    s.name = kod
                    s.to_csv(cy(kod))
    out: dict[str, pd.Series] = {}
    for ad, kod in kodlar.items():
        y = cy(kod)
        if not y.exists():
            uyar(f"SERİ YOK: {ad} ({kod}) — ne EVDS'ten geldi ne önbellekte var.")
            continue
        if not _taze(y, CACHE_TTL_SAAT):
            uyar(f"ESKİ ÖNBELLEK: {ad} ({kod}) {_yas_gun(y):.0f} gün eski — "
                 "EVDS'ten tazelenemedi, bu seri BAYAT olabilir.")
        out[ad] = pd.read_csv(y, index_col=0, parse_dates=True).iloc[:, 0]
    df = pd.DataFrame(out).sort_index()
    df.index.name = "tarih"
    return df


# ===========================================================================
#  SERİ KÜMELERİ
#  Birim veri GRUBU düzeyinde yayımlanıyor; aşağıdaki `beklenen birim` yorumu
#  EVDS'ten okunanla HER KOŞUDA karşılaştırılır (birim_denetimi).
# ===========================================================================

# --- AYLIK · bie_kbmgel · bin TL · AKIM (aylık gerçekleşme, YTD DEĞİL) ------
# TUZAK: EVDS kataloğunda DEFAULT_AGG_METHOD_STR='KÜMÜLATİF' yazıyor; o, düşük
# frekansa çevirirken kullanılacak TOPLAMA YÖNTEMİ, serinin kendisi değil.
# Seri aylık gerçekleşmedir (denetim 2: yıl içi monoton artış YOK).
GELIR = {
    "my_gelir":        "TP.KB.GEL001",   # 1. Merkezi Yönetim Gelirleri
    "gb_gelir":        "TP.KB.GEL002",   # 1.1 Genel Bütçe Gelirleri
    "vergi":           "TP.KB.GEL003",   # 1.1.1 Vergi Gelirleri
    "v_gelir_kazanc":  "TP.KB.GEL004",   # gelir + kurumlar
    "v_gelir":         "TP.KB.GEL005",
    "v_kurumlar":      "TP.KB.GEL010",
    "v_dahilde":       "TP.KB.GEL017",   # dahilde mal ve hizmet
    "v_kdv_dahil":     "TP.KB.GEL018",
    "v_otv":           "TP.KB.GEL021",
    "v_dis_ticaret":   "TP.KB.GEL031",
    "v_kdv_ithal":     "TP.KB.GEL033",
    "v_damga":         "TP.KB.GEL035",
    "tesebbus_mulk":   "TP.KB.GEL038",
    "faiz_pay_ceza":   "TP.KB.GEL061",
    "ozel_butce_gel":  "TP.KB.GEL094",
    "ddk_gel":         "TP.KB.GEL095",
}

# --- AYLIK · bie_kbmgid · bin TL · AKIM -------------------------------------
# YALNIZ ÜST DÜZEY KALEMLER. bie_kbmgid içindeki pek çok alt kalem 2023-11'de
# kesiliyor (GID013, GID029, GID035-037, GID051-052, GID068-070, GID088…) ve
# alt kırılımların toplamı üst kalemi TUTMUYOR.
GIDER = {
    "my_gider":         "TP.KB.GID001",   # A+B
    "faiz_disi_gider":  "TP.KB.GID002",   # A) faiz hariç
    "personel":         "TP.KB.GID003",
    "sgk_primi":        "TP.KB.GID008",
    "mal_hizmet":       "TP.KB.GID014",
    "cari_transfer":    "TP.KB.GID026",
    "hazine_yardim":    "TP.KB.GID033",
    "sgk_hazine_yrd":   "TP.KB.GID034",
    "tarim_destek":     "TP.KB.GID067",
    "sermaye_gider":    "TP.KB.GID110",
    "sermaye_transfer": "TP.KB.GID116",
    "borc_verme":       "TP.KB.GID131",
    "faiz_gideri":      "TP.KB.GID152",   # B) faiz giderleri
    "faiz_ic":          "TP.KB.GID153",
    "faiz_dis":         "TP.KB.GID160",
    "faiz_iskonto":     "TP.KB.GID161",
    "faiz_turev":       "TP.KB.GID162",
    "faiz_kira_sert":   "TP.KB.GID163",
}

# --- AYLIK · bie_kbgen · bin TL · AKIM (GENEL bütçe) ------------------------
# KAPSAM FARKI: bu tablo GENEL BÜTÇE'dir. Denge, nakit dengesi ve FİNANSMAN
# yalnız burada yayımlanıyor. MERKEZİ YÖNETİM dengesi EVDS'te hazır YOK ve
# GEL001 − GID001 ile TÜRETİLİR; iki denge son 24 ayda ortalama %12,6 farklı
# (özel bütçeli idareler + düzenleyici kurumlar). "Aynı" demek yanlıştır.
GENEL = {
    "gb_faiz_disi_denge": "TP.KB.GEN34",
    "gb_denge":           "TP.KB.GEN35",
    "gb_nakit_denge":     "TP.KB.GEN39",
    "gb_finansman":       "TP.KB.GEN40",
    "borclanma_net":      "TP.KB.GEN41",
    "dis_borclanma_net":  "TP.KB.GEN42",
    "dis_kullanim":       "TP.KB.GEN43",
    "dis_odeme":          "TP.KB.GEN44",
    "ic_borclanma_net":   "TP.KB.GEN45",
    "bono_tl_satis":      "TP.KB.GEN47",
    "bono_tl_odeme":      "TP.KB.GEN48",
    "bono_dov_satis":     "TP.KB.GEN63",
    "bono_dov_odeme":     "TP.KB.GEN64",
    "tahvil_tl_satis":    "TP.KB.GEN50",
    "tahvil_tl_odeme":    "TP.KB.GEN51",
    "tahvil_dov_satis":   "TP.KB.GEN53",
    "tahvil_dov_odeme":   "TP.KB.GEN54",
    "ozellestirme":       "TP.KB.GEN58",
    "kasa_banka":         "TP.KB.GEN60",
}

# --- AYLIK · bie_kbicborc · bin TL · STOK -----------------------------------
# YAPISAL SIFIRLAR: A04 (konsolide borç + kur farkları), A06/A07 (nakit /
# nakit dışı bono), A08 (avans) bugün SIFIR dönüyor. Seri var, olgu yok —
# grafikte çizilmez, toplamda yer alır. "Veri gelmedi" ile "gerçekten sıfır"
# ayrımı metrik.py'de açıkça yapılır.
IC_BORC = {
    "ic_borc_toplam":   "TP.KB.A09",
    "ic_tahvil":        "TP.KB.A01",
    "ic_tahvil_nakit":  "TP.KB.A02",
    "ic_tahvil_nkdisi": "TP.KB.A03",
    "ic_bono":          "TP.KB.A05",
    "ic_bono_nakit":    "TP.KB.A06",
    "ic_bono_nkdisi":   "TP.KB.A07",
    "ic_konsolide":     "TP.KB.A04",
    "ic_avans":         "TP.KB.A08",
}

# --- AYLIK · bie_tukfiy2025 · endeks (2025=100) · DEFLATÖR ------------------
# BIRIMI alanı bu grupta BOŞ geliyor; taban grup adındaki "(2025=100)"dan
# düşürülür (birim_denetimi bunu ayrıca not eder).
TUFE = {"tufe": "TP.TUKFIY2025.GENEL"}

# --- ÜÇ AYLIK · bie_brutdbborclu · milyon ABD doları · STOK -----------------
DIS_BORC = {
    "db_toplam":        "TP.BRUTDBORCLU.G1",
    "db_kamu":          "TP.BRUTDBORCLU.G2",
    "db_genel_hukumet": "TP.BRUTDBORCLU.G3",
    "db_merkezi_yon":   "TP.BRUTDBORCLU.G4",     # ← hattın dış bacağı
    "db_my_kisa":       "TP.BRUTDBORCLU.G22",
    "db_my_uzun":       "TP.BRUTDBORCLU.G40",
    "db_tcmb":          "TP.BRUTDBORCLU.G13",
    "db_ozel":          "TP.BRUTDBORCLU.G14",
}

# --- ÜÇ AYLIK · bie_finhestnks7101311 · bin TL · STOK -----------------------
FIN_HESAP = {
    "fh_yukum_toplam":  "TP.FINHESTNKS7101311.ZP45",   # F.0 toplam yükümlülük
    "fh_borc_senedi":   "TP.FINHESTNKS7101311.ZP31",   # F.3
    "fh_bs_kisa":       "TP.FINHESTNKS7101311.ZP32",   # F.3.1
    "fh_bs_uzun":       "TP.FINHESTNKS7101311.ZP33",   # F.3.2
    "fh_krediler":      "TP.FINHESTNKS7101311.ZP34",   # F.4
    "fh_varlik_toplam": "TP.FINHESTNKS7101311.ZP23",   # VF.0
    "fh_net_fin_deger": "TP.FINHESTNKS7101311.ZP1",    # BF.9
    "fh_mevduat":       "TP.FINHESTNKS7101311.ZP5",    # VF.2 Hazine nakit varlığı
}

# --- ÜÇ AYLIK · bie_gsyhhrccar · bin TL · cari fiyatlarla GSYH -------------
GSYH = {"gsyh_cari": "TP.GSYIH20.BY.B1GQ"}

# --- HAFTALIK(CUMA) · bie_dibsyazdeg · milyon TL · YAZILI (nominal) değer ---
# Sektörler İHRAÇÇI değil senedi ELİNDE TUTAN taraftır; ihraççı zaten genel
# yönetimdir. Yurt dışı yerleşik payı ForeignHoldings hattıyla ÇAKIŞIR — bu
# hatta yalnız borç stoku bağlamında verilir.
DIBS_YAZ = {
    "dibs_toplam":    "TP.DIBSYAZDEG.ST",      # S.1 + S.2
    "dibs_yurtici":   "TP.DIBSYAZDEG.S1",
    "dibs_tcmb":      "TP.DIBSYAZDEG.S121",
    "dibs_bankalar":  "TP.DIBSYAZDEG.S122",
    "dibs_fonlar":    "TP.DIBSYAZDEG.S1234",
    "dibs_yurtdisi":  "TP.DIBSYAZDEG.S2",
}

# --- HAFTALIK(CUMA) · bie_dibsvade + bie_dibspiydeg · milyon TL · PİYASA ----
# TUZAK: vade tablosu YAZILI değil PİYASA değeri üzerinden. Kanıt (denetim 6):
#   TP.DIBSVADE.C5.ST ≡ TP.DIBSPIYDEG.ST  ve  TP.DIBSYAZDEG.ST'nin ~1,22 KATI.
# Payları YAZILI stoka uygulamak %22'lik SESSİZ hata üretir; paylar HER ZAMAN
# kendi tablosunun toplamına bölünür.
DIBS_VADE = {
    "dibs_pd_toplam":  "TP.DIBSVADE.C5.ST",
    "dibs_kv_kisa":    "TP.DIBSVADE.C3.ST",     # kalan vade, kısa (<1 yıl)
    "dibs_kv_uzun":    "TP.DIBSVADE.C4.ST",     # kalan vade, uzun
    "dibs_ov_kisa":    "TP.DIBSVADE.C1.ST",     # orijinal vade, kısa
    "dibs_ov_uzun":    "TP.DIBSVADE.C2.ST",
    "dibs_piyasa_deg": "TP.DIBSPIYDEG.ST",      # kanıt serisi
}

# --- HAFTALIK(CUMA) · bie_ebond* · milyon ABD doları -----------------------
# EBONDYAZDEG = yazılı değer; EBONDVADE ≡ EBONDPIYDEG = PİYASA değeri.
# İki toplam birbirinin yerine KULLANILAMAZ (C8=99.964 · YAZDEG.ST=100.706).
# S1311 = merkezi yönetimin kendi eurobondunu tutması → konsolidasyonda
# DÜŞÜLECEK kalem, toplam borca EKLENMEZ.
EUROBOND = {
    "eb_toplam_yaz":   "TP.EBONDYAZDEG.ST",
    "eb_yurtdisi_yaz": "TP.EBONDYAZDEG.S2",
    "eb_yurtici_yaz":  "TP.EBONDYAZDEG.S1",
    "eb_merkezi_yon":  "TP.EBONDYAZDEG.S1311",
    "eb_toplam_pd":    "TP.EBONDVADE.C8.ST",
    "eb_usd_ihrac":    "TP.EBONDVADE.C5.ST",    # ← para birimi kırılımı
    "eb_eur_ihrac":    "TP.EBONDVADE.C6.ST",
    "eb_jpy_ihrac":    "TP.EBONDVADE.C7.ST",
    "eb_kv_kisa":      "TP.EBONDVADE.C3.ST",
    "eb_kv_uzun":      "TP.EBONDVADE.C4.ST",
    "eb_piyasa_deg":   "TP.EBONDPIYDEG.ST",     # kanıt serisi
}

# --- GÜNLÜK · bie_dkdovytl · Türk lirası -----------------------------------
KUR = {"usdtry": "TP.DK.USD.A.YTL", "eurtry": "TP.DK.EUR.A.YTL"}

# (etiket, kod sözlüğü, biçim, başlangıç, parça_gun, aile, hedef dosya)
KUMELER = [
    ("Bütçe gelirleri",        GELIR,     "ay",     "2006-01-01", None, "butce",   "aylik"),
    ("Bütçe giderleri",        GIDER,     "ay",     "2006-01-01", None, "butce",   "aylik"),
    ("Genel bütçe finansmanı", GENEL,     "ay",     "2006-01-01", None, "butce",   "aylik"),
    ("İç borç stoku",          IC_BORC,   "ay",     "2003-01-01", None, "butce",   "aylik"),
    ("TÜFE",                   TUFE,      "ay",     "2005-01-01", None, "tufe",    "aylik"),
    ("Dış borç stoku",         DIS_BORC,  "ceyrek", "2003-01-01", None, "disborc", "ceyreklik"),
    ("Finansal hesaplar",      FIN_HESAP, "ceyrek", "2010-10-01", None, "finhesap", "ceyreklik"),
    ("GSYH",                   GSYH,      "ceyrek", "2003-01-01", None, "ceyrek",  "ceyreklik"),
    ("DİBS yazılı değer",      DIBS_YAZ,  "gun",    "2020-09-11", None, "menkul",  "haftalik"),
    ("DİBS vade",              DIBS_VADE, "gun",    "2020-09-11", None, "menkul",  "haftalik"),
    ("Eurobond",               EUROBOND,  "gun",    "2020-09-11", None, "menkul",  "haftalik"),
    ("Kur",                    KUR,       "gun",    "2006-01-01", PARCA_GUN_GUNLUK, "kur", "gunluk"),
]

# ===========================================================================
#  BİRİM SÖZLEŞMESİ
#  Seri kodu → EVDS veri grubu → BEKLENEN birim. Beklenen birim burada YAZILI
#  ama DOĞRULAYICI değil; doğrulayıcı EVDS'in `datagroups` yanıtıdır. İkisi
#  ayrışırsa hat DURUR: bu hatta 1000× hata gözle yakalanmaz (bin TL ile
#  milyon TL karıştırılınca iki seri de "trilyon" mertebesinde görünür).
# ===========================================================================
GRUP_KURALI = [
    (r"^TP\.KB\.GEL",          "bie_kbmgel",            "bin TL"),
    (r"^TP\.KB\.GID",          "bie_kbmgid",            "bin TL"),
    (r"^TP\.KB\.GEN",          "bie_kbgen",             "bin TL"),
    (r"^TP\.KB\.A\d",          "bie_kbicborc",          "bin TL"),
    (r"^TP\.BRUTDBORCLU\.",    "bie_brutdbborclu",      "milyon ABD doları"),
    (r"^TP\.DIBSYAZDEG\.",     "bie_dibsyazdeg",        "milyon TL"),
    (r"^TP\.DIBSVADE\.",       "bie_dibsvade",          "milyon TL"),
    (r"^TP\.DIBSPIYDEG\.",     "bie_dibspiydeg",        "milyon TL"),
    (r"^TP\.EBONDYAZDEG\.",    "bie_ebondyazdeg",       "milyon ABD doları"),
    (r"^TP\.EBONDVADE\.",      "bie_ebondvade",         "milyon ABD doları"),
    (r"^TP\.EBONDPIYDEG\.",    "bie_ebondpiydeg",       "milyon ABD doları"),
    (r"^TP\.FINHESTNKS",       "bie_finhestnks7101311", "bin TL"),
    (r"^TP\.GSYIH20\.",        "bie_gsyhhrccar",        "bin TL"),
    (r"^TP\.TUKFIY2025\.",     "bie_tukfiy2025",        "endeks (2025=100)"),
    (r"^TP\.DK\.",             "bie_dkdovytl",          "Türk lirası"),
]

# Metrik katmanının kullandığı ÖLÇEK ÇARPANLARI — dönüşüm TEK yerde yapılır.
#   bin TL            → trilyon TL :  / 1e9
#   milyon TL         → trilyon TL :  / 1e6
#   milyon ABD doları → milyar USD :  / 1e3
#   milyon ABD doları → bin TL     :  × 1e3 × kur
OLCEK = {
    "bin TL → trilyon TL": 1e-9,
    "milyon TL → trilyon TL": 1e-6,
    "milyon ABD doları → milyar ABD doları": 1e-3,
    "milyon ABD doları → bin TL (kur ile)": 1e3,
}


def veri_gruplari(yenile: bool = False) -> pd.DataFrame:
    """Tüm veri grubu kataloğu. BİRİM bu tablodaki `BIRIMI` alanındadır."""
    cy = CACHE / "katalog_datagroups.json"
    if _taze(cy, KATALOG_TTL_SAAT) and not yenile:
        return pd.DataFrame(json.loads(cy.read_text(encoding="utf-8")))
    try:
        d = _cek("datagroups/mode=0&type=json")
        kayit = d if isinstance(d, list) else d.get("items", d)
        if not kayit:
            raise RuntimeError("boş katalog")
        cy.write_text(json.dumps(kayit, ensure_ascii=False), encoding="utf-8")
    except Exception as ex:
        if cy.exists():
            uyar(f"Veri grubu kataloğu alınamadı ({ex}); eski katalog "
                 f"({_yas_gun(cy):.0f} gün eski) kullanılıyor.")
            kayit = json.loads(cy.read_text(encoding="utf-8"))
        else:
            raise
    return pd.DataFrame(kayit)


def _grup_birim(dg: pd.DataFrame) -> dict[str, str]:
    """Veri grubu → birim. Endeks gruplarında BIRIMI BOŞ gelir; o zaman grup
    adındaki taban ("(2025=100)") okunur — uydurulmaz, ADDAN düşürülür."""
    out: dict[str, str] = {}
    for _, r in dg.iterrows():
        b = (r.get("BIRIMI") or "").strip()
        if not b:
            ad = r.get("DATAGROUP_NAME") or ""
            m = re.search(r"\((\d{4}=100)\)", ad)
            b = f"endeks ({m.group(1)})" if m else "BİRİM YAYIMLANMAMIŞ"
        out[str(r["DATAGROUP_CODE"])] = b
    return out


def _norm(b: str) -> str:
    return re.sub(r"\s+", " ", (b or "")).strip().casefold()


def birim_denetimi(yenile: bool = False) -> tuple[dict, list[str]]:
    """Kodda yazılı beklenen birimi EVDS'in yayımladığıyla karşılaştırır.

    Dönüş: (rapor, DURDURUCU sapmalar). Sapma varsa hat durur — birim
    değiştiğinde bütün ölçek çarpanları (1e9 / 1e6 / 1e3) yanlışa döner ve
    hata grafikte "makul" görünür.
    """
    dg = veri_gruplari(yenile)
    birim = _grup_birim(dg)
    frek = {str(r["DATAGROUP_CODE"]): (r.get("FREQUENCY_STR") or "").strip()
            for _, r in dg.iterrows()}
    kaynak = {str(r["DATAGROUP_CODE"]): (r.get("DATASOURCE") or "").strip()
              for _, r in dg.iterrows()}
    rapor: dict[str, dict] = {}
    dur: list[str] = []
    for kalip, grup, beklenen in GRUP_KURALI:
        gercek = birim.get(grup)
        if gercek is None:
            dur.append(f"BİRİM: veri grubu {grup} EVDS kataloğunda YOK — "
                       "seri kümesi taşınmış olabilir.")
            continue
        uyar_mi = _norm(gercek) != _norm(beklenen)
        rapor[grup] = {"kod_kalibi": kalip, "beklenen": beklenen,
                       "evds": gercek, "frekans": frek.get(grup, ""),
                       "kaynak": kaynak.get(grup, ""), "uyusuyor": not uyar_mi}
        if uyar_mi:
            dur.append(
                f"BİRİM UYUŞMAZLIĞI: {grup} — kodda '{beklenen}', EVDS'te "
                f"'{gercek}'. Ölçek çarpanları (1e9/1e6/1e3) bu birime bağlı; "
                "düzeltilmeden koşulmaz.")
    return rapor, dur


# --------------------------------------------------------------------------- tazelik
# (etiket, tolerans TAKVİM GÜNÜ, negatif gecikme muaf mı)
# Referans DUVAR SAATİDİR. Verinin kendi son gününü referans almak denetimi
# kendi kendine referanslı yapar ("son gözlem bugün, demek ki taze").
# Ölçülen gecikmeler (23.08.2026): bütçe & iç borç 83 · dış borç 54 ·
# haftalık menkul kıymet 9 · GSYH & finansal hesap 145 · TÜFE 53 · kur 2.
# Toleranslar ölçülenin bir yayım dönemi üstüne konur.
# HMB YAYIM TAKVİMİ — BEKLENEN gün, ölçülmüş değil. Merkezi Yönetim Borç Stoku
# İstatistikleri (hattın ANA saati) izleyen ayın ~20'sinde, Merkezi Yönetim
# Bütçe Denge Tablosu (akım bacağı) ~15'inde yayımlanır; hafta sonuna düşen gün
# izleyen ilk iş gününe kayar. İkisi de resmî takvime karşı ölçüldü (TÜİK Ulusal
# Veri Yayımlama Takvimi, Ağustos 2026 verisi): Denge 15.09.2026 (Salı), Borç
# Stoku 21.09.2026 (Pazartesi — 20'si Pazar). Resmî tatili GÖRMEZ; kaynağın
# takvimine bağlanana kadar buradan çıkan gün "beklenen" diye etiketlenir.
#
# NEDEN GEREKLİ: bütçe ayının gecikmesi ay BAŞINDAN sayılıyordu ve aynı bacak
# sayfada üç ayrı yaşla dolaşıyordu (09.09.2026'da ölçüldü: metin 69 gün, şerit
# 39 gün, yayımdan bu yana 19 gün). Aylık bir gözlemin çıpası ayın ilk günü
# değildir; okurun sorduğu soru "veri ne zaman geldi"dir ve onun ölçüsü yayım
# günüdür.
STOK_YAYIM_GUN = 20
DENGE_YAYIM_GUN = 15


def _is_gunu(t: dt.date) -> dt.date:
    """Hafta sonuna düşen bir yayım günü izleyen ilk iş gününe kayar."""
    while t.weekday() >= 5:
        t += dt.timedelta(days=1)
    return t


def beklenen_yayim(ay, gun: int = STOK_YAYIM_GUN) -> pd.Timestamp:
    """Bir bütçe ayının BEKLENEN yayım günü: izleyen ayın `gun`ü, iş gününe kaymış.

    Ölçüm değildir (bkz. STOK_YAYIM_GUN gerekçesi); anahtar adları da öyle
    yazılır (`beklenen_yayim_*`).
    """
    t = pd.Timestamp(ay).normalize() + pd.DateOffset(months=1)
    return pd.Timestamp(_is_gunu(t.replace(day=gun).date()))


# Aile → (okur etiketi, tolerans [takvim günü], negatif gecikme muaf mı).
# TOLERANSIN ÇIPASI AİLEYE GÖRE DEĞİŞİR ve `gecikme_gun()` tek yerde tanımlar:
# "butce" ailesi BEKLENEN YAYIM GÜNÜNDEN (izleyen ayın 20'si) sayılır — sağlıklı
# aralık 0…~32 gün, 45 bir sonraki yayımın ~13 gün gecikmesine izin verir;
# öbür aileler gözlemin kendi tarihinden sayılır (çeyrek sonu, Cuma, gün).
#
# "finhesap" GSYH'den AYRI: TCMB üç aylık finansal hesapları çeyrek sonundan
# ~90 gün sonra yayımlıyor, yani bir sonraki çeyrek gelene dek bacak ~180 gün
# geride kalır (09.09.2026'da ölçülen gecikme 161 gün, 2026-Ç2 henüz yok);
# 200, o ritmin ~üç hafta ötesidir. GSYH ise TÜİK'ten çeyrek sonundan ~60 gün
# sonra gelir; 170 orada kalır.
TAZELIK = {
    "butce":    ("Bütçe & iç borç stoku (HMB, aylık)",           45, False),
    "disborc":  ("Brüt dış borç (üç aylık)",                    110, False),
    "menkul":   ("DİBS & eurobond (haftalık, Cuma)",             12, False),
    "ceyrek":   ("GSYH (TÜİK, üç aylık)",                       170, False),
    "finhesap": ("Finansal hesaplar (TCMB, üç aylık)",          200, False),
    "tufe":     ("TÜFE (aylık)",                                 60, False),
    "kur":      ("Döviz kuru (günlük)",                           4, True),
}
# Gecikmesi beklenen YAYIM gününden ölçülen aileler → yayım günü.
YAYIM_CIPASI = {"butce": STOK_YAYIM_GUN}
# Ailenin saat yazımı (ortak/bicim sözleşmesi): aylık ve üç aylık saat AA.YYYY
# (ay/çeyrek sonu), haftalık ve günlük saat GG.AA.YYYY. Aylık bir gözlemi gün
# gibi yazmak ("01.07.2026") okura o günün ölçümü gibi görünür.
AILE_BICIM = {"butce": "ay", "tufe": "ay", "disborc": "ceyrek", "ceyrek": "ceyrek",
              "finhesap": "ceyrek", "menkul": "gun", "kur": "gun"}


def tazelik_tolerans(aile: str) -> int:
    """Bir ailenin tolerans eşiği (takvim günü).

    ozet_uret.py bayat bayrağını buradan okur; eşik iki yerde ayrı yazılırsa
    biri güncellenip öteki unutulur ve bayatlık sessizce kaçar.
    """
    return TAZELIK[aile][1]


def gecikme_gun(aile: str, son, bugun=None) -> int:
    """Bir ailenin gecikmesi (takvim günü), DUVAR SAATİNE göre — TEK TANIM.

    Veri katmanının tazelik denetimi de özet üreticisi de buradan ölçer; iki
    ayrı formül bir gün sessizce ayrışırdı. "butce" için çıpa gözlem ayı değil
    BEKLENEN YAYIM GÜNÜDÜR; veri beklenenden ERKEN geldiyse gecikme sıfırdır
    (eksi bir yaş yayımlanmaz).
    """
    bugun = pd.Timestamp(bugun).normalize() if bugun is not None \
        else pd.Timestamp.today().normalize()
    son = pd.Timestamp(son).normalize()
    if aile in YAYIM_CIPASI:
        return max(0, (bugun - beklenen_yayim(son, YAYIM_CIPASI[aile])).days)
    return (bugun - son).days


# Finansal hesaplar bacağının ÖLÇÜM katmanındaki sütunları (ceyreklik_metrik.csv).
# Özet üreticisi bacağın saatini, çizim katmanı Şekil 13'ün damgasını buradan
# ölçer; iki ayrı liste bir gün sessizce ayrışır ve figürün içindeki alt yazı
# sayfadaki damgadan başka bir çeyrek söyler.
FH_KOLONLAR = ("yukum_toplam_trl", "varlik_toplam_trl", "net_fin_deger_trl",
               "borc_senedi_trl", "nakit_trl", "krediler_trl")


def bacak_ucu(df: pd.DataFrame, kolonlar) -> "pd.Timestamp | None":
    """Bir figür/bacak ucu: çizilen sütunların son geçerli gözlemlerinin EN ESKİSİ.

    Neden en eski: bacağın sözü serilerin KIYASIDIR ve kıyas ancak hepsinin
    ölçüldüğü güne kadar kurulabilir. Yapısal yazılır — bugün hangi sütunun daha
    uzun olduğuna bakmaz. Kolon yoksa ya da hepsi boşsa None: damga YAZILMAZ.
    """
    uclar = []
    for k in kolonlar:
        if k in df.columns:
            sr = df[k].dropna()
            if len(sr):
                uclar.append(sr.index[-1])
    return min(uclar) if uclar else None


def saat_yaz(aile: str, t) -> str:
    """Ailenin saatini sözleşmeyle yazar: aylık/üç aylık AA.YYYY, öbürleri GG.AA.YYYY."""
    t = pd.Timestamp(t)
    if AILE_BICIM.get(aile) == "ay":
        return f"{t.month:02d}.{t.year}"
    if AILE_BICIM.get(aile) == "ceyrek":
        return f"{(t.month - 1) // 3 * 3 + 3:02d}.{t.year}"
    return f"{t.day:02d}.{t.month:02d}.{t.year}"


AY_TR = {1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
         7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım",
         12: "Aralık"}
AY_KISA = {1: "Oca", 2: "Şub", 3: "Mar", 4: "Nis", 5: "May", 6: "Haz",
           7: "Tem", 8: "Ağu", 9: "Eyl", 10: "Eki", 11: "Kas", 12: "Ara"}


def gun_ad(t) -> str:
    t = pd.Timestamp(t)
    return f"{t.day} {AY_TR[t.month]} {t.year}"


def ay_ad(t) -> str:
    t = pd.Timestamp(t)
    return f"{AY_TR[t.month]} {t.year}"


def kisa_ad(t) -> str:
    t = pd.Timestamp(t)
    return f"{AY_KISA[t.month]}-{str(t.year)[2:]}"


def ceyrek_ad(t) -> str:
    t = pd.Timestamp(t)
    return f"{t.year}-Ç{(t.month - 1) // 3 + 1}"


# --------------------------------------------------------------------------- dönem
_SON: dict[str, str] = {}


def _son_dolu(df: pd.DataFrame, cekirdek: list[str], ad: str) -> pd.Timestamp:
    kol = [c for c in cekirdek if c in df.columns]
    if not kol:
        raise RuntimeError(f"{ad}: çekirdek seriler yok — EVDS çekimi düşmüş olabilir.")
    tam = df[kol].dropna(how="any")
    if tam.empty:
        raise RuntimeError(f"{ad}: çekirdek seriler boş.")
    return tam.index[-1]


def son_ay(aylik: pd.DataFrame | None = None) -> pd.Timestamp:
    """Bütçe ailesinin son dolu ayı. Sabit tarih YASAK.

    Çekirdek: gelir + gider + iç borç stoku. TÜFE bilinçli DIŞARIDA — TÜFE
    bütçeden ~1 ay ÖNDE yayımlanıyor (2026-07 vs 2026-06); çekirdeğe alınsaydı
    dönem ileri kayar ve bütçe serisi o ayda boş kalırdı.
    """
    if "ay" in _SON:
        return pd.Timestamp(_SON["ay"])
    if aylik is None:
        aylik = pd.read_csv(VERI / "aylik.csv", index_col=0, parse_dates=True)
    t = _son_dolu(aylik, ["my_gelir", "my_gider", "ic_borc_toplam"], "son_ay")
    _SON["ay"] = t.strftime("%Y-%m-%d")
    return t


def son_ceyrek(ceyreklik: pd.DataFrame | None = None) -> pd.Timestamp:
    """GSYH & finansal hesapların son ORTAK çeyreği (oran metriklerinin sonu)."""
    if "ceyrek" in _SON:
        return pd.Timestamp(_SON["ceyrek"])
    if ceyreklik is None:
        ceyreklik = pd.read_csv(VERI / "ceyreklik.csv", index_col=0, parse_dates=True)
    t = _son_dolu(ceyreklik, ["gsyh_cari"], "son_ceyrek")
    _SON["ceyrek"] = t.strftime("%Y-%m-%d")
    return t


def son_dis_ceyrek(ceyreklik: pd.DataFrame | None = None) -> pd.Timestamp:
    """Brüt dış borcun son çeyreği. GSYH'den ÖNDE (54 vs 145 gün gecikme);
    tek bir 'son çeyrek' kullanmak dış borcu bir çeyrek geriye atardı."""
    if "dis" in _SON:
        return pd.Timestamp(_SON["dis"])
    if ceyreklik is None:
        ceyreklik = pd.read_csv(VERI / "ceyreklik.csv", index_col=0, parse_dates=True)
    t = _son_dolu(ceyreklik, ["db_merkezi_yon"], "son_dis_ceyrek")
    _SON["dis"] = t.strftime("%Y-%m-%d")
    return t


def son_hafta(haftalik: pd.DataFrame | None = None) -> pd.Timestamp:
    """Menkul kıymet istatistiklerinin son dolu Cuma'sı."""
    if "hafta" in _SON:
        return pd.Timestamp(_SON["hafta"])
    if haftalik is None:
        haftalik = pd.read_csv(VERI / "haftalik.csv", index_col=0, parse_dates=True)
    t = _son_dolu(haftalik, ["dibs_toplam", "eb_toplam_yaz"], "son_hafta")
    _SON["hafta"] = t.strftime("%Y-%m-%d")
    return t


def son_gun(gunluk: pd.DataFrame | None = None) -> pd.Timestamp:
    """Kurun son iş günü."""
    if "gun" in _SON:
        return pd.Timestamp(_SON["gun"])
    if gunluk is None:
        gunluk = pd.read_csv(VERI / "gunluk.csv", index_col=0, parse_dates=True)
    t = _son_dolu(gunluk, ["usdtry"], "son_gun")
    _SON["gun"] = t.strftime("%Y-%m-%d")
    return t


# --------------------------------------------------------------------------- denetimler
def tazelik_denetimi(cerceveler: dict[str, pd.DataFrame],
                     bugun=None) -> list[str]:
    """Aile bazlı tazelik. Tek eşik bu hatta her koşuda yanlış alarm üretir:
    kur 2 gün, GSYH 145 gün gecikmeli ve İKİSİ DE normaldir.

    Aile içinde `max()` kalır — aile bir KURUMUN bir YAYIMIDIR ve o yayımın
    serileri birlikte ilerler. Farklı takvimle yayımlanan bir bacak aynı aileye
    konursa `max()` onu gizler: finansal hesaplar bu yüzden GSYH'den ayrıldı
    (09.09.2026, 161 güne karşı 70).
    """
    uy: list[str] = []
    aile_kolon: dict[str, list[str]] = {}
    for etiket, kodlar, _b, _bas, _p, aile, hedef in KUMELER:
        aile_kolon.setdefault(aile, [])
        aile_kolon[aile] += [(hedef, ad) for ad in kodlar]
    for aile, kolonlar in aile_kolon.items():
        etiket, tol, negatif_muaf = TAZELIK[aile]
        sonlar = []
        for hedef, ad in kolonlar:
            df = cerceveler.get(hedef)
            if df is None or ad not in df.columns:
                continue
            s = df[ad].dropna()
            if len(s):
                sonlar.append(s.index[-1])
        if not sonlar:
            uy.append(f"TAZELİK: '{etiket}' ailesinden hiçbir seri yüklenemedi.")
            continue
        son = max(sonlar)
        gecikme = gecikme_gun(aile, son, bugun)
        if gecikme < 0 and negatif_muaf:
            continue
        if gecikme > tol:
            cipa = (f"beklenen yayım günü {beklenen_yayim(son, YAYIM_CIPASI[aile]):%d.%m.%Y}"
                    if aile in YAYIM_CIPASI else f"son gözlemi {saat_yaz(aile, son)}")
            uy.append(f"TAZELİK: {etiket} {cipa} ({gecikme} gün önce, "
                      f"tolerans {tol} gün). Yayın durmuş olabilir.")
    return uy


def kimlik_denetimi(a: pd.DataFrame, c: pd.DataFrame,
                    h: pd.DataFrame) -> tuple[list[str], list[str], dict]:
    """Toplama kimlikleri + birim mertebesi.

    Dönüş: (uyarılar, DURDURUCU sapmalar, rapor).
    """
    uy: list[str] = []
    dur: list[str] = []
    rap: dict[str, dict] = {}

    # YUVARLAMA ARTIĞI: HMB finansman tablosunu TAM BİN TL'ye yuvarlayarak
    # yayımlıyor; alt kalemlerin toplamı üst kalemden ±1 bin TL (=1.000 TL)
    # sapabiliyor (ölçüldü: 283 ayın tamamında maksimum mutlak sapma 1,0).
    # Salt bağıl eşik, paydanın küçüldüğü aylarda bu 1 birimi 3e-6'ya
    # büyütüp her koşuda yanlış alarm üretiyordu. Mutlak eşik ÖNCE düşülür.
    def _kimlik(ad: str, sol: pd.Series, sag: pd.Series, olcek: pd.Series,
                esik: float, durdurucu: bool, aciklama: str,
                mutlak_esik: float = 0.0) -> None:
        x = pd.concat([sol.rename("s"), sag.rename("t"),
                       olcek.rename("o")], axis=1).dropna()
        if x.empty:
            uy.append(f"KİMLİK: {ad} — ortak gözlem yok, denetim koşmadı.")
            return
        mutlak = (x["s"] - x["t"]).abs()
        artik = (mutlak - mutlak_esik).clip(lower=0)
        bagil = (artik / x["o"].abs().replace(0, pd.NA)).dropna()
        maks = float(bagil.max()) if len(bagil) else float("nan")
        gecti = bool(maks <= esik)
        rap[ad] = {"n": int(len(x)), "maks_bagil_sapma": maks, "esik": esik,
                   "maks_mutlak_sapma": float(mutlak.max()),
                   "mutlak_esik": mutlak_esik,
                   "gecti": gecti, "durdurucu": durdurucu, "aciklama": aciklama}
        if not gecti:
            msg = (f"KİMLİK SAPMASI: {ad} — en büyük bağıl sapma {maks:.3e} "
                   f"(eşik {esik:.0e}). {aciklama}")
            uy.append(msg)
            if durdurucu:
                dur.append(msg)

    # 1. GID001 = GID002 + GID152 (faiz dahil = faiz hariç + faiz)
    if {"my_gider", "faiz_disi_gider", "faiz_gideri"} <= set(a.columns):
        _kimlik("GID001 = GID002 + GID152", a["my_gider"],
                a["faiz_disi_gider"] + a["faiz_gideri"], a["my_gider"],
                1e-6, True, "Gider ağacının kökü bozulmuş; kalem eşlemesi yanlış.",
                mutlak_esik=2.0)

    # 2. GEN41 = GEN42 + GEN45 (net borçlanma = dış + iç)
    if {"borclanma_net", "dis_borclanma_net", "ic_borclanma_net"} <= set(a.columns):
        _kimlik("GEN41 = GEN42 + GEN45", a["borclanma_net"],
                a["dis_borclanma_net"] + a["ic_borclanma_net"],
                a[["dis_borclanma_net", "ic_borclanma_net"]].abs().sum(axis=1),
                1e-6, True, "Finansman tablosunun kökü bozulmuş.",
                mutlak_esik=2.0)

    # 3. GEN42 = GEN43 + GEN44 (net dış = kullanım + ödeme)
    if {"dis_borclanma_net", "dis_kullanim", "dis_odeme"} <= set(a.columns):
        _kimlik("GEN42 = GEN43 + GEN44", a["dis_borclanma_net"],
                a["dis_kullanim"] + a["dis_odeme"],
                a[["dis_kullanim", "dis_odeme"]].abs().sum(axis=1),
                1e-6, True, "Dış borçlanma bacağı bozulmuş.",
                mutlak_esik=2.0)

    # 4. GEN40 = −GEN39 (finansman = eksi nakit denge)
    if {"gb_finansman", "gb_nakit_denge"} <= set(a.columns):
        _kimlik("GEN40 = −GEN39", a["gb_finansman"], -a["gb_nakit_denge"],
                a["gb_nakit_denge"], 1e-6, False,
                "Nakit denge ↔ finansman özdeşliği tutmuyor.",
                mutlak_esik=2.0)

    # 5. DİBS: S.1 + S.2 = toplam
    if {"dibs_toplam", "dibs_yurtici", "dibs_yurtdisi"} <= set(h.columns):
        _kimlik("DİBS S.1 + S.2 = toplam", h["dibs_toplam"],
                h["dibs_yurtici"] + h["dibs_yurtdisi"], h["dibs_toplam"],
                1e-6, True, "Sahiplik kırılımı toplamı tutmuyor.")

    # 6. TUZAK KANITI (tanı): vade tablosu YAZILI değil PİYASA değeri.
    if {"dibs_pd_toplam", "dibs_piyasa_deg", } <= set(h.columns) \
            and "dibs_toplam" in h.columns:
        x = h[["dibs_pd_toplam", "dibs_piyasa_deg", "dibs_toplam"]].dropna()
        if len(x):
            ozdes = float((x["dibs_pd_toplam"] - x["dibs_piyasa_deg"]).abs().max())
            oran = float(x["dibs_pd_toplam"].iloc[-1] / x["dibs_toplam"].iloc[-1])
            rap["DİBSVADE ≡ DİBSPİYDEĞ"] = {
                "n": int(len(x)), "maks_fark_mn_tl": ozdes,
                "piyasa_yazili_oran": oran, "gecti": ozdes < 1.0,
                "durdurucu": False,
                "aciklama": ("Vade tablosu PİYASA değeri; yazılı değere oranı "
                             f"{oran:.2f}×. Paylar kendi toplamına bölünür.")}
            if ozdes >= 1.0:
                uy.append("KANIT DÜŞTÜ: TP.DIBSVADE.C5.ST artık "
                          "TP.DIBSPIYDEG.ST ile özdeş değil — vade tablosunun "
                          "değerleme tabanı değişmiş olabilir.")

    # 7. BİRİM MERTEBESİ (1000× sınıfı hata burada yakalanır).
    #    İç borç stoku BİN TL (/1e9 → trilyon), DİBS yazılı değer MİLYON TL
    #    (/1e6 → trilyon). İkisi aynı olguyu ölçüyor; %20'den fazla ayrışamaz.
    #    Ölçüldü: 9,01 vs 9,45 trl TL → %4,6. Bir birim hatası %99.900 verirdi.
    if "ic_borc_toplam" in a.columns and "dibs_toplam" in h.columns:
        ic = a["ic_borc_toplam"].dropna()
        db = h["dibs_toplam"].dropna()
        if len(ic) and len(db):
            ic_trn = float(ic.iloc[-1]) * OLCEK["bin TL → trilyon TL"]
            db_trn = float(db.iloc[-1]) * OLCEK["milyon TL → trilyon TL"]
            fark = abs(ic_trn - db_trn) / db_trn
            rap["Birim mertebesi: iç borç ≈ DİBS"] = {
                "ic_borc_trl_tl": ic_trn, "dibs_yazili_trl_tl": db_trn,
                "bagil_fark": fark, "esik": 0.20, "gecti": bool(fark < 0.20),
                "durdurucu": True,
                "aciklama": ("bin TL/1e9 ile milyon TL/1e6 aynı mertebeyi "
                             "vermeli; vermiyorsa ölçek çarpanı yanlış.")}
            if fark >= 0.20:
                msg = (f"BİRİM MERTEBESİ SAPMASI: iç borç {ic_trn:.2f} trl TL "
                       f"(bin TL/1e9) ile DİBS yazılı değer {db_trn:.2f} trl TL "
                       f"(milyon TL/1e6) arasında %{fark*100:.0f} fark var. "
                       "1000× ölçek hatası olabilir.")
                uy.append(msg)
                dur.append(msg)

    # 8. Bütçe serisi AKIM mı? Kümülatif olsaydı yıl içinde MONOTON artardı.
    if "my_gelir" in a.columns:
        s = a["my_gelir"].dropna()
        if len(s):
            y = s[s.index.year == s.index[-1].year - 1]
            mono = bool((y.diff().dropna() >= 0).all()) if len(y) > 3 else None
            rap["Bütçe serisi AKIM"] = {
                "yil": int(s.index[-1].year - 1), "yil_ici_monoton": mono,
                "gecti": mono is False, "durdurucu": False,
                "aciklama": ("EVDS kataloğundaki 'KÜMÜLATİF' etiketi toplama "
                             "yöntemidir; seri aylık gerçekleşmedir.")}
            if mono:
                msg = ("SERİ TİPİ DEĞİŞMİŞ OLABİLİR: bütçe geliri yıl içinde "
                       "monoton artıyor — seri YTD kümülatife dönmüş olabilir. "
                       "12 aylık birikimli hesaplar bozulur.")
                uy.append(msg)
                dur.append(msg)
    return uy, dur, rap


def yapisal_sifir_denetimi(a: pd.DataFrame, h: pd.DataFrame) -> dict:
    """'Veri gelmedi' ile 'gerçekten sıfır' ayrımı.

    Seri DOLU ama son 24 gözlemi sıfırsa: olgu yok (grafikte çizilmez, toplamda
    kalır). Seri BOŞSA: veri yok (uyarı). İkisi karıştırılırsa sayfada "avans
    kalemi sıfırlandı" gibi olmayan bir olay anlatılır.
    """
    out: dict[str, dict] = {}
    for df, adlar in ((a, ["ic_konsolide", "ic_bono_nakit", "ic_bono_nkdisi",
                           "ic_avans", "tahvil_tl_odeme", "ozellestirme",
                           "bono_dov_satis", "bono_dov_odeme"]),
                      (h, [])):
        for ad in adlar:
            if ad not in df.columns:
                out[ad] = {"durum": "seri yok"}
                continue
            s = df[ad].dropna()
            if s.empty:
                out[ad] = {"durum": "boş"}
                continue
            son24 = s.tail(24)
            out[ad] = {
                "durum": "yapısal sıfır" if bool((son24 == 0).all()) else "dolu",
                "son_tarih": f"{s.index[-1]:%Y-%m-%d}",
                "son_deger": float(s.iloc[-1]),
                "sifir_gozlem_son24": int((son24 == 0).sum()),
            }
    return out


# --------------------------------------------------------------------------- ana akış
def kos(yenile: bool = False) -> dict:
    print("EVDS3 → Merkezi yönetim bütçesi & borç stoku · veri katmanı")
    print(f"  anahtar: {'ortam değişkeni' if os.environ.get('TTO_EVDS_KEY') else 'dosya'}")

    print("\n=== BİRİM DENETİMİ (EVDS `datagroups`.BIRIMI)")
    birim_rap, birim_dur = birim_denetimi(yenile)
    for grup, r in birim_rap.items():
        print(f"  {'✓' if r['uyusuyor'] else '✗'} {grup:<24} "
              f"{r['evds']:<20} {r['frekans']:<14} {r['kaynak'][:34]}")
    for d in birim_dur:
        uyar(d)

    print("\n=== ÇEKİM")
    hedefler: dict[str, list[pd.DataFrame]] = {}
    for etiket, kodlar, bicim, bas, parca, aile, hedef in KUMELER:
        df = cek_kume(kodlar, bicim, bas, parca, yenile, etiket)
        if df.empty:
            uyar(f"KÜME BOŞ: {etiket} — hiçbir seri yüklenemedi.")
        hedefler.setdefault(hedef, []).append(df)

    def _birlestir(ad: str) -> pd.DataFrame:
        parcalar = [d for d in hedefler.get(ad, []) if not d.empty]
        if not parcalar:
            return pd.DataFrame()
        d = pd.concat(parcalar, axis=1).sort_index()
        d.index.name = "tarih"
        return d

    a = _birlestir("aylik")
    c = _birlestir("ceyreklik")
    h = _birlestir("haftalik")
    g = _birlestir("gunluk")
    cerceveler = {"aylik": a, "ceyreklik": c, "haftalik": h, "gunluk": g}

    # --- dönem çıpaları (VERİDEN okunur, sabit tarih yok) ------------------
    s_ay = son_ay(a)
    s_ceyrek = son_ceyrek(c)
    s_dis = son_dis_ceyrek(c)
    s_hafta = son_hafta(h)
    s_gun = son_gun(g)
    print(f"\n  SON BÜTÇE AYI     : {ay_ad(s_ay)}")
    print(f"  SON GSYH ÇEYREĞİ  : {ceyrek_ad(s_ceyrek)}")
    print(f"  SON DIŞ BORÇ ÇEY. : {ceyrek_ad(s_dis)}")
    print(f"  SON MENKUL HAFTASI: {gun_ad(s_hafta)} (Cuma)")
    print(f"  SON KUR GÜNÜ      : {gun_ad(s_gun)}")

    print("\n=== DENETİMLER")
    for u in tazelik_denetimi(cerceveler):
        uyar(u)
    kim_uy, kim_dur, kim_rap = kimlik_denetimi(a, c, h)
    for u in kim_uy:
        uyar(u)
    for ad, r in kim_rap.items():
        isaret = "✓" if r.get("gecti") else "✗"
        ek = (f"maks bağıl sapma {r['maks_bagil_sapma']:.2e}"
              if "maks_bagil_sapma" in r else
              f"bağıl fark %{r['bagil_fark']*100:.1f}" if "bagil_fark" in r else
              f"yıl içi monoton: {r.get('yil_ici_monoton')}"
              if "yil_ici_monoton" in r else
              f"maks fark {r.get('maks_fark_mn_tl', float('nan')):.3f} mn TL")
        print(f"  {isaret} {ad:<34} {ek}")
    sifir = yapisal_sifir_denetimi(a, h)
    yap = [k for k, v in sifir.items() if v.get("durum") == "yapısal sıfır"]
    if yap:
        print(f"  · yapısal sıfır (olgu yok, veri var): {', '.join(yap)}")

    # --- yazım (HER koşuda; 'dosya varsa atla' YASAK) ----------------------
    a.to_csv(VERI / "aylik.csv")
    c.to_csv(VERI / "ceyreklik.csv")
    h.to_csv(VERI / "haftalik.csv")
    g.to_csv(VERI / "gunluk.csv")

    gecikme = {}
    bugun = pd.Timestamp.today().normalize()
    for ad, df in cerceveler.items():
        if df.empty:
            continue
        son = df.dropna(how="all").index[-1]
        gecikme[ad] = {"son": f"{son:%Y-%m-%d}", "gecikme_gun": int((bugun - son).days)}

    durum = {
        "kosum": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "son_ay": s_ay.strftime("%Y-%m-%d"),
        "son_ceyrek": s_ceyrek.strftime("%Y-%m-%d"),
        "son_dis_ceyrek": s_dis.strftime("%Y-%m-%d"),
        "son_hafta": s_hafta.strftime("%Y-%m-%d"),
        "son_gun": s_gun.strftime("%Y-%m-%d"),
        "birim": birim_rap,
        "olcek": OLCEK,
        "kimlik": kim_rap,
        "yapisal_sifir": sifir,
        "gecikme": gecikme,
        "boyut": {ad: [int(df.shape[0]), int(df.shape[1])]
                  for ad, df in cerceveler.items()},
        "uyarilar": list(_UYARI),
    }
    (VERI / "veri_durum.json").write_text(
        json.dumps(durum, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n  yazıldı: data/aylik.csv ({a.shape[0]}x{a.shape[1]}), "
          f"ceyreklik.csv ({c.shape[0]}x{c.shape[1]}), "
          f"haftalik.csv ({h.shape[0]}x{h.shape[1]}), "
          f"gunluk.csv ({g.shape[0]}x{g.shape[1]})")
    if _UYARI:
        print(f"\n[{len(_UYARI)} uyarı]")
    dur = birim_dur + kim_dur
    if dur:
        for x in dur:
            print("  ✗ " + x)
        raise SystemExit(
            "DUR: birim/kimlik denetimi düştü. Yanlış ölçekli sayı yayına "
            "gitmesin diye metrik ve grafik üretilmiyor. "
            "Ayrıntı: data/veri_durum.json")
    return durum


if __name__ == "__main__":
    kos(yenile="--yenile" in sys.argv)
