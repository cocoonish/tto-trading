# -*- coding: utf-8 -*-
"""Merkezi Yönetim Bütçesi & Borç Stoku — KEŞİF katmanı (EVDS3).

Ne yapar
--------
1. EVDS3'ün katalog uçlarından (`categories`, `datagroups`, `serieList`) bu hattın
   besleneceği veri gruplarını ve BİRİMLERİNİ okur. Birim, seri düzeyinde DEĞİL
   VERİ GRUBU düzeyinde yayımlanıyor (`BIRIMI` alanı) — bu hattın en pahalı
   hatası birim karıştırmaktır, o yüzden birim koda elle yazılmaz, EVDS'ten okunur.
2. Aday seri kodlarının HER BİRİNİ gerçekten çağırır; dönen son gözlemi, tarihini
   ve gözlem sayısını raporlar. Çağrılmamış / boş dönen kod listeye GİRMEZ.
3. Kimlik ve büyüklük denetimleri koşar (aşağıda DENETLER).
4. Bulguları `data/kesif.json` + ekrana yazar. Her koşuda YENİDEN yazılır
   ("dosya varsa atla" yasak).

Koşum:  python3 kesif.py            (önbellek 12 saat TTL)
        python3 kesif.py --yenile   (önbelleği yok say)

Uç nokta notu
-------------
`evds2.tcmb.gov.tr/service/evds` ÖLÜ. Çalışan taban:

    https://evds3.tcmb.gov.tr/igmevdsms-dis/{uç}{param}={değer}&...

Sorgu dizesi `?` ile başlamaz; anahtar URL'de DEĞİL `key:` HTTP başlığında gider.
Tek istek ~1000 SATIRLA sınırlı ve aralığın SONUNDAN geriye doldurur; bu hattaki
en uzun seri aylık (1979→) = ~560 satır, haftalık 2020→ = ~310 satır, üç aylık
1989→ = ~150 satır. Hiçbiri 1000'i aşmıyor, bu yüzden YILLIK PARÇALAMA gerekmez —
ama günlük kur serisi (TP.DK.*) 1000 satırı aşar, o 366 günlük parçalarla çekilir.

DÖRT tarih biçimi, ÜÇ ayrıştırıcı:
    GÜNLÜK / HAFTALIK(CUMA) → "14-08-2026"   (%d-%m-%Y)
    AYLIK                   → "2026-6"       (%Y-%m)
    ÜÇ AYLIK                → "2026-Q2"      (int('Q2') tuzağı burada)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
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
KATALOG_TTL_SAAT = 168        # ağaç sık değişmez
DEMET = 6                     # tek istekte kaç seri (satır sınırı seri sayısına bağlı DEĞİL)

_UYARI: list[str] = []
_ANAHTAR: str | None = None


def uyar(mesaj: str) -> None:
    if mesaj not in _UYARI:
        _UYARI.append(mesaj)
    print("  ! " + mesaj, flush=True)


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
        except Exception as ex:
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


# --------------------------------------------------------------------------- katalog
def veri_gruplari(yenile: bool = False) -> pd.DataFrame:
    """Tüm veri grubu kataloğu. BİRİMİ bu tabloda (`BIRIMI` alanı)."""
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
                 f"({_yas_gun(cy):.0f} gün eski).")
            kayit = json.loads(cy.read_text(encoding="utf-8"))
        else:
            raise
    return pd.DataFrame(kayit)


def seri_listesi(grup: str, yenile: bool = False) -> pd.DataFrame:
    """Bir veri grubunun seri kataloğu (kod → ad, başlangıç, bitiş)."""
    cy = CACHE / f"katalog_{grup}.json"
    if _taze(cy, KATALOG_TTL_SAAT) and not yenile:
        return pd.DataFrame(json.loads(cy.read_text(encoding="utf-8")))
    try:
        d = _cek(f"serieList/type=json&code={grup}")
        kayit = d if isinstance(d, list) else d.get("items", d)
        if not kayit:
            raise RuntimeError("boş katalog")
        cy.write_text(json.dumps(kayit, ensure_ascii=False), encoding="utf-8")
    except Exception as ex:
        if cy.exists():
            uyar(f"Seri kataloğu alınamadı ({grup}: {ex}); eski katalog "
                 f"({_yas_gun(cy):.0f} gün eski).")
            kayit = json.loads(cy.read_text(encoding="utf-8"))
        else:
            raise
    return pd.DataFrame(kayit)


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
    elif bicim == "ay":                      # "2026-6"
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
    o yüzden demet düşerse seriler tek tek denenir."""
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


def cek_kume(kodlar: dict[str, str], bicim: str, bas: str,
             parca_gun: int | None = None, yenile: bool = False,
             etiket: str = "") -> pd.DataFrame:
    """ad → EVDS kodu sözlüğünü çeker. Önbellek SERİ BAZINDA (demet değişince
    önbellek geçersizleşmesin)."""
    def cy(kod): return CACHE / f"evds_{bicim}_{kod.replace('.', '_')}.csv"

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
            uyar(f"ESKİ ÖNBELLEK: {ad} ({kod}) {_yas_gun(y):.0f} gün eski.")
        out[ad] = pd.read_csv(y, index_col=0, parse_dates=True).iloc[:, 0]
    df = pd.DataFrame(out).sort_index()
    df.index.name = "tarih"
    return df


# ===========================================================================
#  ADAY SERİ KÜMELERİ
#  Birim veri GRUBU düzeyinde yayımlanıyor; aşağıdaki yorumlar EVDS'ten okunan
#  `BIRIMI` alanının kopyasıdır, kesif.py her koşuda ikisini KARŞILAŞTIRIR.
# ===========================================================================

# --- AYLIK · bie_kbmgel · bin TL · AKIM (aylık gerçekleşme, kümülatif DEĞİL) --
GELIR = {
    "my_gelir":        "TP.KB.GEL001",   # 1. Merkezi Yönetim Gelirleri
    "gb_gelir":        "TP.KB.GEL002",   # 1.1 Genel Bütçe Gelirleri
    "vergi":           "TP.KB.GEL003",   # 1.1.1 Vergi Gelirleri
    "v_gelir_kazanc":  "TP.KB.GEL004",   # gelir+kurumlar
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

# --- AYLIK · bie_kbmgid · bin TL · AKIM ------------------------------------
GIDER = {
    "my_gider":        "TP.KB.GID001",   # A+B
    "faiz_disi_gider": "TP.KB.GID002",   # A) faiz hariç
    "personel":        "TP.KB.GID003",
    "sgk_primi":       "TP.KB.GID008",
    "mal_hizmet":      "TP.KB.GID014",
    "cari_transfer":   "TP.KB.GID026",
    "hazine_yardim":   "TP.KB.GID033",
    "sgk_hazine_yrd":  "TP.KB.GID034",
    "tarim_destek":    "TP.KB.GID067",
    "sermaye_gider":   "TP.KB.GID110",
    "sermaye_transfer": "TP.KB.GID116",
    "borc_verme":      "TP.KB.GID131",
    "faiz_gideri":     "TP.KB.GID152",   # B) faiz giderleri
    "faiz_ic":         "TP.KB.GID153",
    "faiz_dis":        "TP.KB.GID160",
    "faiz_iskonto":    "TP.KB.GID161",
    "faiz_turev":      "TP.KB.GID162",
    "faiz_kira_sert":  "TP.KB.GID163",
}

# --- AYLIK · bie_kbgen · bin TL · AKIM (GENEL bütçe; MY'nin ~%97'si) --------
# Denge ve FİNANSMAN yalnız genel bütçe düzeyinde yayımlanıyor; merkezi yönetim
# dengesi GEL001−GID001'den TÜRETİLİR (kesif.py bu iki dengeyi karşılaştırır).
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

# --- AYLIK · bie_kbicborc · bin TL · STOK (1979'dan) ------------------------
IC_BORC = {
    "ic_borc_toplam":  "TP.KB.A09",
    "ic_tahvil":       "TP.KB.A01",
    "ic_tahvil_nakit": "TP.KB.A02",
    "ic_tahvil_nkdisi": "TP.KB.A03",
    "ic_bono":         "TP.KB.A05",
    "ic_bono_nakit":   "TP.KB.A06",
    "ic_bono_nkdisi":  "TP.KB.A07",
    "ic_konsolide":    "TP.KB.A04",
    "ic_avans":        "TP.KB.A08",
}

# --- ÜÇ AYLIK · bie_brutdbborclu · milyon ABD doları · STOK -----------------
DIS_BORC = {
    "db_toplam":       "TP.BRUTDBORCLU.G1",
    "db_kamu":         "TP.BRUTDBORCLU.G2",
    "db_genel_hukumet": "TP.BRUTDBORCLU.G3",
    "db_merkezi_yon":  "TP.BRUTDBORCLU.G4",     # ← hattın dış bacağı
    "db_my_kisa":      "TP.BRUTDBORCLU.G22",
    "db_my_uzun":      "TP.BRUTDBORCLU.G40",
    "db_tcmb":         "TP.BRUTDBORCLU.G13",
    "db_ozel":         "TP.BRUTDBORCLU.G14",
}

# --- HAFTALIK(CUMA) · bie_dibsyazdeg · milyon TL · YAZILI (nominal) değer ---
# Sektörler İHRAÇÇI değil ELİNDE TUTAN taraftır; ihraççı genel yönetimdir.
DIBS_YAZ = {
    "dibs_toplam":     "TP.DIBSYAZDEG.ST",      # S.1 + S.2
    "dibs_yurtici":    "TP.DIBSYAZDEG.S1",
    "dibs_tcmb":       "TP.DIBSYAZDEG.S121",
    "dibs_bankalar":   "TP.DIBSYAZDEG.S122",
    "dibs_fonlar":     "TP.DIBSYAZDEG.S1234",
    "dibs_yurtdisi":   "TP.DIBSYAZDEG.S2",
}

# --- HAFTALIK(CUMA) · bie_dibsvade · milyon TL · PİYASA DEĞERİ (!) ----------
# TUZAK: bu tablo YAZILI değil PİYASA değeri üzerinden. Kanıt (kesif.py denetler):
#   TP.DIBSVADE.C5.ST ≡ TP.DIBSPIYDEG.ST ,  TP.DIBSYAZDEG.ST'ten ~%20 BÜYÜK.
DIBS_VADE = {
    "dibs_pd_toplam":  "TP.DIBSVADE.C5.ST",
    "dibs_kv_kisa":    "TP.DIBSVADE.C3.ST",     # kalan vade, kısa (<1 yıl)
    "dibs_kv_uzun":    "TP.DIBSVADE.C4.ST",     # kalan vade, uzun
    "dibs_ov_kisa":    "TP.DIBSVADE.C1.ST",     # orijinal vade, kısa
    "dibs_ov_uzun":    "TP.DIBSVADE.C2.ST",
    "dibs_piyasa_deg": "TP.DIBSPIYDEG.ST",      # kanıt serisi
}

# --- HAFTALIK(CUMA) · bie_ebond* · milyon ABD doları ------------------------
# EBONDYAZDEG = yazılı değer; EBONDVADE = PİYASA değeri (C8 ≡ EBONDPIYDEG.ST).
EUROBOND = {
    "eb_toplam_yaz":   "TP.EBONDYAZDEG.ST",
    "eb_yurtdisi_yaz": "TP.EBONDYAZDEG.S2",
    "eb_yurtici_yaz":  "TP.EBONDYAZDEG.S1",
    "eb_merkezi_yon":  "TP.EBONDYAZDEG.S1311",  # elinde tutan MY (konsolidasyon)
    "eb_toplam_pd":    "TP.EBONDVADE.C8.ST",
    "eb_usd_ihrac":    "TP.EBONDVADE.C5.ST",    # ← para birimi kırılımı
    "eb_eur_ihrac":    "TP.EBONDVADE.C6.ST",
    "eb_jpy_ihrac":    "TP.EBONDVADE.C7.ST",
    "eb_kv_kisa":      "TP.EBONDVADE.C3.ST",
    "eb_kv_uzun":      "TP.EBONDVADE.C4.ST",
    "eb_piyasa_deg":   "TP.EBONDPIYDEG.ST",     # kanıt serisi
}

# --- ÜÇ AYLIK · bie_finhestnks7101311 · bin TL · STOK ----------------------
FIN_HESAP = {
    "fh_yukum_toplam": "TP.FINHESTNKS7101311.ZP45",   # F.0 toplam yükümlülük
    "fh_borc_senedi":  "TP.FINHESTNKS7101311.ZP31",   # F.3
    "fh_bs_kisa":      "TP.FINHESTNKS7101311.ZP32",
    "fh_bs_uzun":      "TP.FINHESTNKS7101311.ZP33",
    "fh_krediler":     "TP.FINHESTNKS7101311.ZP34",   # F.4
    "fh_varlik_toplam": "TP.FINHESTNKS7101311.ZP23",  # VF.0
    "fh_net_fin_deger": "TP.FINHESTNKS7101311.ZP1",   # BF.9
    "fh_mevduat":      "TP.FINHESTNKS7101311.ZP5",    # VF.2 (Hazine nakit varlığı)
}

# --- ÜÇ AYLIK · bie_gsyhhrccar · bin TL · cari fiyatlarla GSYH -------------
GSYH = {"gsyh_cari": "TP.GSYIH20.BY.B1GQ"}

# --- AYLIK · TÜFE (deflatör) -----------------------------------------------
TUFE = {"tufe": "TP.TUKFIY2025.GENEL"}

# --- GÜNLÜK · kur (dış borcun TL karşılığı + kur duyarlılığı) --------------
KUR = {"usdtry": "TP.DK.USD.A.YTL", "eurtry": "TP.DK.EUR.A.YTL"}

# grup → (kod sözlüğü, EVDS veri grubu, biçim, başlangıç, parça_gun)
KUMELER = [
    ("Bütçe gelirleri",   GELIR,     "bie_kbmgel",            "ay",     "2006-01-01", None),
    ("Bütçe giderleri",   GIDER,     "bie_kbmgid",            "ay",     "2006-01-01", None),
    ("Genel bütçe finansmanı", GENEL, "bie_kbgen",            "ay",     "2006-01-01", None),
    ("İç borç stoku",     IC_BORC,   "bie_kbicborc",          "ay",     "2003-01-01", None),
    ("Dış borç stoku",    DIS_BORC,  "bie_brutdbborclu",      "ceyrek", "2003-01-01", None),
    ("DİBS yazılı değer", DIBS_YAZ,  "bie_dibsyazdeg",        "gun",    "2020-09-11", None),
    ("DİBS vade",         DIBS_VADE, "bie_dibsvade",          "gun",    "2020-09-11", None),
    ("Eurobond",          EUROBOND,  "bie_ebondyazdeg",       "gun",    "2020-09-11", None),
    ("Finansal hesaplar", FIN_HESAP, "bie_finhestnks7101311", "ceyrek", "2010-10-01", None),
    ("GSYH",              GSYH,      "bie_gsyhhrccar",        "ceyrek", "2003-01-01", None),
    ("TÜFE",              TUFE,      "bie_tukfiy2025",        "ay",     "2005-01-01", None),
    ("Kur",               KUR,       "bie_dkdovytl",          "gun",    "2006-01-01", 366),
]


# ===========================================================================
#  KOŞUM
# ===========================================================================
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--yenile", action="store_true")
    args = ap.parse_args()

    print("EVDS3 veri grubu kataloğu okunuyor…", flush=True)
    dg = veri_gruplari(args.yenile)
    # BİRİM veri GRUBU düzeyinde yayımlanıyor; bazı endeks gruplarında alan BOŞ
    # geliyor (ör. bie_tukfiy2025) — o zaman grup adındaki taban okunur.
    def _birim(r) -> str:
        b = (r.get("BIRIMI") or "").strip()
        if b:
            return b
        ad = (r.get("DATAGROUP_NAME") or "")
        m = re.search(r"\((\d{4}=100)\)", ad)
        return f"endeks ({m.group(1)})" if m else "BİRİM YAYIMLANMAMIŞ"

    birim = {r["DATAGROUP_CODE"]: _birim(r) for _, r in dg.iterrows()}
    frek = {r["DATAGROUP_CODE"]: (r.get("FREQUENCY_STR") or "").strip()
            for _, r in dg.iterrows()}
    kaynak = {r["DATAGROUP_CODE"]: (r.get("DATASOURCE") or "").strip()
              for _, r in dg.iterrows()}

    # seri adları: veri grubu kataloglarından
    ad_haritasi: dict[str, str] = {}
    for _, _kod, grup, *_ in KUMELER:
        try:
            sl = seri_listesi(grup, args.yenile)
        except Exception as ex:
            uyar(f"{grup} seri kataloğu okunamadı: {ex}")
            continue
        if "SERIE_CODE" in sl.columns:
            for _, r in sl.iterrows():
                ad_haritasi[str(r["SERIE_CODE"])] = str(r.get("SERIE_NAME", "")).strip()

    rapor: list[dict] = []
    veriler: dict[str, pd.DataFrame] = {}

    for etiket, kodlar, grup, bicim, bas, parca in KUMELER:
        print(f"\n=== {etiket}  ({grup} · {birim.get(grup,'?')} · "
              f"{frek.get(grup,'?')} · {kaynak.get(grup,'?')})", flush=True)
        df = cek_kume(kodlar, bicim, bas, parca, args.yenile, etiket)
        veriler[etiket] = df
        for ad, kod in kodlar.items():
            if ad not in df.columns:
                rapor.append({"kume": etiket, "ad": ad, "kod": kod,
                              "dogrulandi": False, "not": "veri dönmedi"})
                continue
            s = df[ad].dropna()
            if s.empty:
                rapor.append({"kume": etiket, "ad": ad, "kod": kod,
                              "dogrulandi": False, "not": "boş seri"})
                continue
            rapor.append({
                "kume": etiket, "ad": ad, "kod": kod,
                "evds_adi": ad_haritasi.get(kod, ""),
                "veri_grubu": grup, "birim": birim.get(grup, ""),
                "frekans": frek.get(grup, ""), "kaynak": kaynak.get(grup, ""),
                "baslangic": f"{s.index[0]:%Y-%m-%d}",
                "son_tarih": f"{s.index[-1]:%Y-%m-%d}",
                "son_deger": float(s.iloc[-1]),
                "gozlem": int(s.size), "dogrulandi": True,
            })
            print(f"  ✓ {kod:<28} {s.index[-1]:%Y-%m-%d}  "
                  f"{s.iloc[-1]:>20,.2f}  ({s.size} gözlem, {s.index[0]:%Y-%m})")

    # ------------------------------------------------------------------ DENETLER
    print("\n=== DENETLER", flush=True)
    denet: list[str] = []

    def d_yaz(ad: str, tamam: bool, ayrinti: str) -> None:
        isaret = "TAMAM" if tamam else "SAPMA"
        satir = f"[{isaret}] {ad}: {ayrinti}"
        denet.append(satir)
        print("  " + satir)

    gel, gid = veriler["Bütçe gelirleri"], veriler["Bütçe giderleri"]
    gen = veriler["Genel bütçe finansmanı"]

    # 1. Toplama kimliği: GID001 = GID002 + GID152
    if {"my_gider", "faiz_disi_gider", "faiz_gideri"} <= set(gid.columns):
        x = gid[["my_gider", "faiz_disi_gider", "faiz_gideri"]].dropna()
        fark = (x["my_gider"] - x["faiz_disi_gider"] - x["faiz_gideri"]).abs()
        oran = (fark / x["my_gider"].abs()).max()
        d_yaz("GID001 = GID002 + GID152", oran < 1e-6, f"en büyük bağıl sapma {oran:.2e}")

    # 2. Seri AKIM mı KÜMÜLATİF mi? Kümülatif olsaydı yıl içinde monotondu.
    if "my_gelir" in gel.columns:
        s = gel["my_gelir"].dropna()
        y = s[s.index.year == s.index[-1].year - 1]
        mono = bool((y.diff().dropna() >= 0).all()) if len(y) > 3 else None
        d_yaz("Bütçe serisi AKIM (kümülatif değil)", mono is False,
              f"{s.index[-1].year-1} yılı içi monoton artış: {mono} "
              f"(True olsaydı seri YTD kümülatif olurdu)")

    # 3. Merkezi yönetim dengesi ile genel bütçe dengesi aynı işaret/mertebede mi
    if {"my_gelir"} <= set(gel.columns) and {"my_gider"} <= set(gid.columns) \
            and "gb_denge" in gen.columns:
        my_denge = (gel["my_gelir"] - gid["my_gider"]).dropna()
        ort = pd.concat([my_denge.rename("my"), gen["gb_denge"].rename("gb")],
                        axis=1).dropna().tail(24)
        oran = (ort["my"] - ort["gb"]).abs().sum() / ort["gb"].abs().sum()
        d_yaz("MY dengesi ≈ GB dengesi (kapsam farkı)", oran < 0.35,
              f"son 24 ayda ortalama |fark|/|GB| = {oran:.1%} "
              f"(özel bütçe + DDK kapsam farkı; %0 BEKLENMEZ)")

    # 4. BİRİM MERTEBESİ: iç borç stoku (bin TL) ile DİBS yazılı değer (milyon TL)
    #    aynı büyüklük olmalı. 1000× hata tam burada yakalanır.
    ic = veriler["İç borç stoku"].get("ic_borc_toplam")
    db = veriler["DİBS yazılı değer"].get("dibs_toplam")
    if ic is not None and db is not None and len(ic.dropna()) and len(db.dropna()):
        ic_trn = ic.dropna().iloc[-1] / 1e9        # bin TL  → trilyon TL
        db_trn = db.dropna().iloc[-1] / 1e6        # milyon TL → trilyon TL
        oran = abs(ic_trn - db_trn) / db_trn
        d_yaz("İç borç stoku ≈ DİBS yazılı değer", oran < 0.10,
              f"{ic_trn:.2f} trl TL (bin TL/1e9) vs {db_trn:.2f} trl TL "
              f"(milyon TL/1e6) → fark %{oran*100:.1f}")

    # 5. TUZAK KANITI: VADE tabloları YAZILI değil PİYASA değeri
    dv = veriler["DİBS vade"]
    if {"dibs_pd_toplam", "dibs_piyasa_deg"} <= set(dv.columns):
        x = dv[["dibs_pd_toplam", "dibs_piyasa_deg"]].dropna()
        esit = (x["dibs_pd_toplam"] - x["dibs_piyasa_deg"]).abs().max() < 1.0
        oran_yaz = float(dv["dibs_pd_toplam"].dropna().iloc[-1]) / \
            float(veriler["DİBS yazılı değer"]["dibs_toplam"].dropna().iloc[-1])
        d_yaz("DİBSVADE ≡ DİBSPİYDEĞ (piyasa değeri)", esit,
              f"özdeşlik {esit}; yazılı değere oran {oran_yaz:.2f}× "
              f"→ VADE tablosu YAZILI değerle TOPLANAMAZ")

    eb = veriler["Eurobond"]
    if {"eb_usd_ihrac", "eb_eur_ihrac", "eb_jpy_ihrac", "eb_toplam_pd"} <= set(eb.columns):
        x = eb[["eb_usd_ihrac", "eb_eur_ihrac", "eb_jpy_ihrac", "eb_toplam_pd"]].dropna()
        kalan = (x["eb_toplam_pd"] - x[["eb_usd_ihrac", "eb_eur_ihrac",
                                        "eb_jpy_ihrac"]].sum(axis=1))
        pay = (kalan / x["eb_toplam_pd"]).iloc[-1]
        d_yaz("Eurobond USD+EUR+JPY ≈ toplam", abs(pay) < 0.02,
              f"artık (diğer para birimleri) payı %{pay*100:.2f}")

    # 6. MERTEBE KIYASI: merkezi yönetim borç stoku / GSYH bilinen bantta mı.
    #    Stok ARAÇ (ihraç) tabanında kurulur — iç borç (A09, ihraç tabanı) ile
    #    brüt dış borç (G4, YERLEŞİKLİK tabanı) TOPLANAMAZ: yurt dışının DİBS'i
    #    iki kez sayılır, yurt içinin eurobondu hiç sayılmaz.
    gs = veriler["GSYH"]["gsyh_cari"].dropna()          # bin TL, üç aylık
    gsyh_yil = gs.rolling(4).sum().dropna()             # 4 çeyrek toplamı
    kur = veriler["Kur"]["usdtry"].dropna()
    dis = veriler["Dış borç stoku"]["db_merkezi_yon"].dropna()   # milyon USD
    eb = veriler.get("Eurobond")
    dibs = veriler.get("DİBS yazılı değer")
    if (len(gsyh_yil) and len(ic.dropna()) and len(dis) and len(kur)
            and eb is not None and dibs is not None):
        t = gsyh_yil.index[-1]
        e_t = kur.asof(t)
        ic_t = ic.dropna().asof(t)                                  # bin TL
        eb_st = eb["eb_toplam_yaz"].dropna().asof(t)                # milyon USD
        eb_s2 = eb["eb_yurtdisi_yaz"].dropna().asof(t)
        eb_k = eb["eb_merkezi_yon"].dropna().asof(t)
        dibs_s2 = dibs["dibs_yurtdisi"].dropna().asof(t)            # milyon TL
        senet_t = (eb_st - eb_k) * 1e3 * e_t                        # bin TL
        kredi_musd = dis.asof(t) - eb_s2 - dibs_s2 / e_t
        kredi_t = kredi_musd * 1e3 * e_t                            # bin TL
        toplam = ic_t + senet_t + kredi_t
        pay = toplam / gsyh_yil.iloc[-1]
        d_yaz("MY borç stoku / GSYH mertebesi", 0.12 < pay < 0.45,
              f"{t:%Y-%m}: (iç {ic_t/1e9:.1f} + yurt dışında ihraç senet "
              f"{senet_t/1e9:.1f} + dış kredi {kredi_t/1e9:.1f}) trl TL / "
              f"{gsyh_yil.iloc[-1]/1e9:.1f} trl TL = %{pay*100:.1f} "
              f"(Türkiye için bilinen bant %15–35)")
        # Dış kredi ARTIĞI pozitif ve mertebede olmalı; değilse eurobond/DİBS
        # sahiplik eşlemesi bozulmuş demektir.
        d_yaz("Dış kredi artığı mertebesi", 2_000 < kredi_musd < 80_000,
              f"{t:%Y-%m}: G4 {dis.asof(t):,.0f} − eurobond(S2) {eb_s2:,.0f} − "
              f"DİBS(S2)/kur {dibs_s2/e_t:,.0f} = {kredi_musd:,.0f} mn USD")

    # 7. İÇ BORÇ ÇEVİRME ORANI — 12 aylık birikimli, mertebe denetimi.
    #    Hazine ihraç hattı İHALEYİ anlatır; burada STOK/FİNANSMAN tarafı var.
    sat = ["bono_tl_satis", "bono_dov_satis", "tahvil_tl_satis", "tahvil_dov_satis"]
    ode = ["bono_tl_odeme", "bono_dov_odeme", "tahvil_tl_odeme", "tahvil_dov_odeme"]
    if set(sat + ode) <= set(gen.columns):
        s12 = gen[sat].sum(axis=1).rolling(12).sum()
        o12 = gen[ode].sum(axis=1).abs().rolling(12).sum()
        cevirme = (s12 / o12).dropna()
        son = float(cevirme.iloc[-1])
        d_yaz("İç borç çevirme oranı (12 aylık)", 0.5 < son < 2.5,
              f"{cevirme.index[-1]:%Y-%m}: %{son*100:.0f} "
              f"(son 5 yıl bandı %{cevirme.tail(60).min()*100:.0f}–"
              f"%{cevirme.tail(60).max()*100:.0f})")

    # 8. TAZELİK — referans DUVAR SAATİ, verinin kendi son günü değil
    bugun = pd.Timestamp.today().normalize()
    tazelik = {}
    for etiket, df in veriler.items():
        if df.empty:
            continue
        son = df.dropna(how="all").index[-1]
        gecikme = (bugun - son).days
        tazelik[etiket] = {"son": f"{son:%Y-%m-%d}", "gecikme_gun": int(gecikme)}
        print(f"  · {etiket:<24} son gözlem {son:%Y-%m-%d}  ({gecikme} gün önce)")

    # ------------------------------------------------------------------ çıktı
    cikti = {
        "_tarih": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "seriler": rapor,
        "denetler": denet,
        "tazelik": tazelik,
        "uyarilar": _UYARI,
    }
    (VERI / "kesif.json").write_text(
        json.dumps(cikti, ensure_ascii=False, indent=1), encoding="utf-8")
    ok = sum(1 for r in rapor if r["dogrulandi"])
    print(f"\n{ok}/{len(rapor)} seri doğrulandı → {VERI/'kesif.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
