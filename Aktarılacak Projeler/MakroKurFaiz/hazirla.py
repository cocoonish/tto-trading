#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRODAN KURA VE FAİZE DERSİ — depodaki girdileri BİR KEZ dondurur.

Ders yayımlandığı günün ölçümüdür (karar 08.09.2026): metindeki sayılar ve
figürler CANLI hatlardan okunamaz. Hatların `data/` dosyaları her koşuda
yeniden yazılır; ders bir gün sessizce başka bir veriyi anlatmaya başlardı
("BİR REHBERİN GİRDİSİ, KAYAN BİR PENCEREDEN OKUNAMAZ"). Bu betik ders
pratiklerinin (içindekiler, veri planı bölüm A: "Depoda var") ihtiyaç duyduğu
sütunları TEK bir çıpada keser ve `veri/` altına deterministik `csv.gz`
olarak yazar. `olcum.py` yalnız buradan okur; `dogrula.py` özleri yeniden
sınar.

ÇIPA. Kaynak = bugünün depo hâli (künyede HEAD commit'i ve her kaynağın git
blob özü). Kesim = dersin ilan ettiği veri çıpası: günlük ve haftalık seriler
30.09.2026, aylık 08.2026, çeyreklik 2026Ç2. TCMB gösterge kuru VALÖR tarihlidir
(ertesi iş günü): 30.09.2026'da ilan edilen değerin tarihi 01.10.2026 olduğu
için bu seri çıpanın ertesi iş gününe kadar kesilir; ölçüm katmanı onu bir iş
günü geri alır. Belge (OVP) kesilmez: yayımlanmış bir tablodur.

KAYNAK OLDUĞU GİBİ. Arşiv kaynağın verdiğini saklar; ayıklama (hafta sonu
barı, tatil, valör kaydırması, Yahoo günlük barının bir günlük kayması) ölçüm
katmanında kuralıyla ve sayımıyla yapılır. Sütun adı ne olduğunu söyler:

  usdtry_ist18       Yahoo saatlik bardan İstanbul 18:00 kapanışı (ortak/usdtry,
                     ortak/fx_kapanis); geçiş gününden itibaren
  usdtry_gunbasi     Yahoo GÜNLÜK barın kapanış alanı: D tarihli değer D gününün
                     BAŞINDAKİ fiyattır (= D−1'in Londra gece yarısı kapanışı).
                     Ölçüm katmanı `fx_kapanis.gunluk_duzelt` ile bir iş günü
                     geri yazar. Aynı adlandırma EM kurlarında (`brl_gunbasi` …)
  usdtry_tcmb_valor  TCMB gösterge (döviz alış) kuru, valör tarihli

Geçiş günü (saatlik kapanışın başladığı gün) VARSAYILMAZ, ÖLÇÜLÜR: Fonlama
hattının `usdtry` sütunu `ortak/usdtry.seri()`nin çıktısıdır ve geçişten önce
düzeltilmiş günlük barla birebir aynıdır; birebirliğin bittiği gün geçiştir.
Saatlik kısım ayrıca KurSaati keşif arşivinin saatlik barlarından yeniden
kurulup sınanır.

DOĞRULAMA YAZMADAN ÖNCE. Bütün çerçeveler önce kurulur ve sınanır (birden çok
kaynaktan birleştirilen serilerin örtüşen günlerde birebirliği, yinelenen
tarih, boş sütun); bir sınama düşerse HİÇBİR dosya yazılmaz.

DETERMİNİZM. CSV metni sabit ondalıkla (öntanımlı 6; TCMB kuru 8, çünkü 1990
kuru 0,00231137'dir) ve `\\n` satır sonuyla yazılır; gzip zaman damgası 0.
Künyedeki sha256 SIKIŞTIRILMAMIŞ metnin özüdür. Künye duvar saati taşımaz:
aynı ağaçta yeniden koşu aynı baytları üretir.

ÜSTÜNE YAZMAZ. Var olan arşiv dosyası (ya da künyede bu betiğin kaydı) varsa
hiçbir şey yazılmaz; bilinçli yenileme `--yeniden` ister ve yeni bir pencere
metnin sayılarının yeniden yazılması demektir. Künyede bu betiğe ait olmayan
kayıtlar (bulut arşivleri) `--yeniden` ile de korunur.

Koşum:  python3 hazirla.py [--yeniden]
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

sys.dont_write_bytecode = True

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
AP = KOK / "Aktarılacak Projeler"
TARIH = KOK / "site" / "tools" / "ders_grafik" / "_tarih"
VERI = BURASI / "veri"
KUNYE = VERI / "kunye.json"
HAZIRLAYAN = "hazirla.py"

sys.path.insert(0, str(KOK / "ortak"))
import fx_kapanis as fx  # noqa: E402  — Yahoo günlük barının tek düzeltme tanımı

CIPA = {"gunluk": "2026-09-30", "haftalik": "2026-09-30", "olay": "2026-09-30", "aylik": "2026-08",
        "ceyreklik": "2026Q2", "valor": "2026-10-01"}
SINIR = {"gunluk": pd.Timestamp("2026-09-30"), "haftalik": pd.Timestamp("2026-09-30"),
         "aylik": pd.Timestamp("2026-08-31"), "ceyreklik": pd.Timestamp("2026-06-30"),
         "valor": pd.Timestamp("2026-10-01"), "olay": pd.Timestamp("2026-09-30"), "belge": None}

UYARILAR: list[str] = []
# Planda adı geçip depoda bulunamayan ya da gerçek adı plandakinden farklı olan
# kalemler — ne kullanıldığı adıyla.
BULUNAMAYAN = [
    {"plan": "ortak/usdtry önbelleği (<hat>/data/cache/usdtry_yahoo.csv), "
             "USDTRYDeval/data/cache/usdtry_yahoo.csv",
     "durum": "depoda yok — önbellek izlenmez, yalnız koşucuda durur",
     "yerine": "Aktarılacak Projeler/Fonlama/data/gunluk.csv:usdtry (aynı ortak/usdtry.seri() "
               "çıktısı, EVDS iş günü eksenine hizalı) → usdtry_ist18"},
    {"plan": "DXY barının gövde/aralık sınaması (yahoo_gunluk)",
     "durum": "OatBund Yahoo arşivi yalnız kapanış taşıyor (açılış, yüksek, düşük yok)",
     "yerine": "sınama bu arşivden kurulamaz; G10 yedeği için cnbc_kur_gunluk eklendi"},
    {"plan": "DİBS metrik `politika` (günlük politika faizi)",
     "durum": "seri 14.09.2018'de başlıyor (bir hafta vadeli repo); öncesi yok",
     "yerine": "em_politika_aylik:tur (BIS, aylık, 2002+) ve ppk_kararlari (2016+)"},
]


# ── yardımcılar ─────────────────────────────────────────────────────────────
def _git(*a: str) -> str:
    return subprocess.run(["git", *a], cwd=KOK, capture_output=True, text=True,
                          check=True).stdout.strip()


def kaynak(yol: Path, sutunlar: dict, rol: str = "veri", **ek) -> dict:
    """Bir kaynak dosyanın künye kaydı: yol, git blob özü, HEAD ile aynı mı."""
    rel = yol.relative_to(KOK).as_posix()
    blob = _git("hash-object", rel)
    try:
        head = _git("rev-parse", f"HEAD:{rel}")
    except subprocess.CalledProcessError:
        head = None
    if blob != head:
        UYARILAR.append(f"{rel}: çalışma ağacındaki dosya HEAD'deki sürümden farklı "
                        f"(blob {blob[:10]} · HEAD {head[:10] if head else 'yok'})")
    k = {"yol": rel, "git_blob": blob, "head_blob": head, "temiz": blob == head,
         "rol": rol, "sutunlar": sutunlar}
    k.update(ek)
    return k


def arsiv_ozu_sina(yol: Path, kunye_yolu: Path) -> bool | None:
    """Kaynak bir arşivse (OatBund, KagitOis) kendi künyesindeki özü tutuyor mu."""
    try:
        kn = json.loads(kunye_yolu.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    beklenen = (kn.get("dosyalar", {}).get(yol.name) or {}).get("sha256")
    if not beklenen:
        return None
    gercek = hashlib.sha256(gzip.decompress(yol.read_bytes())).hexdigest()
    if gercek != beklenen:
        UYARILAR.append(f"{yol.name}: kaynak arşivin özü kendi künyesini tutmuyor")
    return gercek == beklenen


def oku(yol: Path, sutunlar: list[str] | None = None) -> pd.DataFrame:
    df = pd.read_csv(yol, index_col=0, parse_dates=True)
    if sutunlar is not None:
        eksik = [c for c in sutunlar if c not in df.columns]
        if eksik:
            raise SystemExit(f"✗ {yol.relative_to(KOK)}: sütun yok {eksik} "
                             f"(gerçek sütunlar: {list(df.columns)})")
        df = df[sutunlar]
    df.index = pd.DatetimeIndex(df.index)
    df.index.name = "tarih"
    return df


def kes(df: pd.DataFrame, frekans: str) -> tuple[pd.DataFrame, dict]:
    """Çıpaya kadar kes; kesilenin sayımı künyeye."""
    s = SINIR[frekans]
    if s is None:
        return df, {"kesilen_satir": 0}
    son = df[df.index > s]
    bilgi = {"kesilen_satir": int(len(son))}
    if len(son):
        bilgi["kesilen_aralik"] = [str(son.index.min().date()), str(son.index.max().date())]
    return df[df.index <= s], bilgi


def tek(a: pd.Series, b: pd.Series, ad: str, tol: float = 1e-12) -> dict:
    """İki kaynağın örtüşen günlerde birebirliği — tutmazsa arşiv YAZILMAZ."""
    a, b = a.dropna(), b.dropna()
    i = a.index.intersection(b.index)
    fark = ((a.loc[i] - b.loc[i]).abs() / b.loc[i].abs().clip(lower=1e-12)) if len(i) else pd.Series(dtype=float)
    k = {"ortak_gun": int(len(i)), "birebir": int((fark <= tol).sum()),
         "azami_goreli_fark": float(fark.max()) if len(i) else None}
    if len(i) == 0 or k["birebir"] != k["ortak_gun"]:
        raise SystemExit(f"✗ {ad}: kaynaklar örtüşen günlerde ayrışıyor {k}")
    return k


# ── dosya kuruluşları ───────────────────────────────────────────────────────
# Her kurucu (ad, çerçeve, meta) döner; meta: frekans, tarih kuralı, pratikler,
# kaynaklar, açıklamalar. Sütun açıklamaları künyeye olduğu gibi yazılır.
OB = AP / "OatBund" / "veri"
OB_KUNYE = OB / "kunye.json"


def oatbund(ad: str, dosya: str, sutun: dict, frekans: str, tarih_kurali: str,
            pratik: list[str], aciklama: str, aciklamalar: dict) -> tuple:
    yol = OB / dosya
    df = oku(yol, list(sutun)).rename(columns=sutun)
    return ad, df, {"frekans": frekans, "tarih_kurali": tarih_kurali, "pratik": pratik,
                    "aciklama": aciklama, "sutun_aciklama": aciklamalar,
                    "kaynaklar": [kaynak(yol, sutun, kaynak_arsiv_ozu_tuttu=arsiv_ozu_sina(yol, OB_KUNYE))]}


def abd_hazine():
    return oatbund(
        "abd_hazine_gunluk.csv.gz", "abd_gunluk.csv.gz", {"us2": "us2", "us10": "us10"},
        "gunluk", "ABD işlem günü", ["1A", "1 (rejim ataması)", "3C", "3D", "4B", "4C", "5A", "11C", "12"],
        "ABD Hazinesi günlük par getiri eğrisi (OatBund arşivi, 01.10.2026 indirmesi)",
        {"us2": "2 yıllık par getiri, %", "us10": "10 yıllık par getiri, %"})


def bund():
    return oatbund(
        "bund_gunluk.csv.gz", "bund_gunluk.csv.gz", {"de2_par": "de2_par", "de10_par": "de10_par"},
        "gunluk", "Bundesbank işlem günü", ["3C", "6D"],
        "Deutsche Bundesbank BBSIS, kupon ödemeli (par) Bund getirisi (OatBund arşivi)",
        {"de2_par": "2 yıl kalan vadeli par getiri, %", "de10_par": "10 yıl kalan vadeli par getiri, %"})


def cnbc_kur():
    return oatbund(
        "cnbc_kur_gunluk.csv.gz", "cnbc_kur_gunluk.csv.gz",
        {k: k for k in ("eur", "gbp", "chf", "jpy", "cad", "aud")},
        "gunluk", "CNBC işlem günü (New York saati); hafta sonu barları kaynakta durur, ölçüm ayıklar",
        ["1A (G10 dolar ölçüsü yedeği)", "3C", "3D", "4B", "10A", "10B", "11C"],
        "CNBC (Tullett Prebon) döviz, New York 17:00 kapanışı (OatBund ek arşivi, 02.10.2026)",
        {"eur": "EUR/USD", "gbp": "GBP/USD", "aud": "AUD/USD",
         "chf": "USD/CHF", "jpy": "USD/JPY", "cad": "USD/CAD"})


def yahoo_dxy_vix():
    return oatbund(
        "yahoo_dxy_vix_gunluk.csv.gz", "yahoo_gunluk.csv.gz", {"dxy": "dxy", "vix": "vix"},
        "gunluk", "Yahoo işlem günü",
        ["1A", "1 (rejim ataması: VIX çeyreği)", "4C", "11B (VIX koşullu)", "11C", "12"],
        "Yahoo Finance günlük kapanış (OatBund arşivi): DX-Y.NYB ve ^VIX. Arşiv yalnız kapanışı "
        "taşır; DXY barının gövde/aralık sınaması buradan kurulamaz",
        {"dxy": "ABD doları endeksi (ICE, DX-Y.NYB), kapanış", "vix": "CBOE VIX, kapanış"})


def cnbc_avrupa():
    s = ("de10y", "fr10y", "it10y", "es10y", "pt10y", "gr10y", "de2y", "it2y")
    return oatbund(
        "cnbc_avrupa_getiri_gunluk.csv.gz", "cnbc_gunluk.csv.gz", {k: k for k in s},
        "gunluk", "CNBC işlem günü; hafta içi barı Avrupa kapanışı (Paris 17:30), hafta sonu barları "
        "kaynakta durur",
        ["6D", "6 (vakalar: İtalya 2011 ve 2018, İspanya 2012, Yunanistan)"],
        "CNBC (Tullett Prebon) gösterge devlet tahvili getirisi, % (OatBund arşivi)",
        {k: f"{k[:2].upper()} {k[2:-1]} yıllık gösterge getiri, %" for k in s})


def ecb_maastricht():
    s = ("DE", "FR", "IT", "ES", "PT", "GR", "IE")
    return oatbund(
        "ecb_maastricht_aylik.csv.gz", "irs_aylik.csv.gz", {k: k for k in s},
        "aylik", "ay sonu", ["6D"],
        "ECB IRS, Maastricht ölçütü 10 yıllık devlet tahvili getirisi, aylık ORTALAMA, % (OatBund arşivi)",
        {k: f"{k} 10 yıl, aylık ortalama, %" for k in s})


def eurostat_uzun():
    s = ("DE", "HU", "PL", "CZ", "RO")
    return oatbund(
        "eurostat_uzun_faiz_aylik.csv.gz", "eurostat_aylik.csv.gz", {k: k for k in s},
        "aylik", "ay sonu", ["10 (Macaristan 2022 vakası)", "6D (DE kıyası)"],
        "Eurostat irt_lt_mcby_m, AB yakınsama ölçütü uzun vadeli faiz, aylık, % (OatBund arşivi)",
        {k: f"{k} uzun vadeli faiz, aylık, %" for k in s})


def dibs_egri():
    yol = AP / "DIBS" / "data" / "metrik.csv"
    s = ["n3a", "n6a", "n1y", "n2y", "n3y", "n5y", "n7y", "n9y", "f_1y1y",
         "be_2y", "be_5y", "r2y", "r5y", "pka_faiz_12a", "pka_faiz_24a"]
    df = oku(yol, s)
    acik = {f"n{k}": f"{v} sıfır kuponlu spot getiri (yıllık bileşik, ACT/365), %"
            for k, v in (("3a", "3 ay"), ("6a", "6 ay"), ("1y", "1 yıl"), ("2y", "2 yıl"),
                         ("3y", "3 yıl"), ("5y", "5 yıl"), ("7y", "7 yıl"), ("9y", "9 yıl"))}
    acik.update({
        "f_1y1y": "1 yıl sonrası 1 yıllık forward (spot eğriden, yıllık bileşik), %",
        "be_2y": "TÜFEX başabaş enflasyonu, 2 yıl, %", "be_5y": "TÜFEX başabaş enflasyonu, 5 yıl, %",
        "r2y": "TÜFEX reel getiri, 2 yıl, %", "r5y": "TÜFEX reel getiri, 5 yıl, %",
        "pka_faiz_12a": "PKA 12 ay sonrası politika faizi beklentisi, GÜNLÜĞE YAYILMIŞ "
                        "(DİBS hattının PKA_YAYIM_GUN = 20 varsayımı: ayın 20'sinden itibaren geçerli)",
        "pka_faiz_24a": "PKA 24 ay sonrası politika faizi beklentisi, günlüğe yayılmış (aynı varsayım)"})
    return "dibs_egri_gunluk.csv.gz", df, {
        "frekans": "gunluk", "tarih_kurali": "TCMB DİBS gösterge değerlerinin günü",
        "pratik": ["1B", "2", "3B", "4A", "4C", "5C", "6C", "10B", "11D", "12 (vekil: TÜFEX reel getiri)"],
        "aciklama": "DİBS hattının ölçüm dosyası: TCMB gösterge değerlerinden sıfır kuponlu eğri, "
                    "forward, TÜFEX ve günlüğe yayılmış PKA faiz beklentileri",
        "sutun_aciklama": acik, "kaynaklar": [kaynak(yol, {c: c for c in s})]}


def fonlama():
    yol = AP / "Fonlama" / "data" / "gunluk.csv"
    s = ["aofm", "politika", "koridor_alt", "koridor_ust", "tlref"]
    df = oku(yol, s)
    # DİBS hattı aynı EVDS serilerini taşır; Fonlama'nınki daha uzun (2011+).
    m = oku(AP / "DIBS" / "data" / "metrik.csv", s)
    sinama = {c: tek(m[c], df[c], f"fonlama↔dibs {c}") for c in s}
    return "fonlama_gunluk.csv.gz", df, {
        "frekans": "gunluk", "tarih_kurali": "EVDS iş günü", "pratik": ["3A", "3B", "4C", "5C", "9B", "11A"],
        "aciklama": "Fonlama hattı: TCMB ağırlıklı ortalama fonlama maliyeti, politika faizi, "
                    "koridor ve TLREF (BİST uzantısıyla)",
        "sutun_aciklama": {"aofm": "TCMB ağırlıklı ortalama fonlama maliyeti, %",
                           "politika": "politika faizi (bir hafta vadeli repo), %; 14.09.2018'de başlar",
                           "koridor_alt": "gecelik borç alma faizi, %", "koridor_ust": "gecelik borç verme faizi, %",
                           "tlref": "TLREF (basit, ACT/365), %"},
        "kaynaklar": [kaynak(yol, {c: c for c in s})],
        "sinama": {"dibs_metrik_ile_ortak_gunlerde_birebir": sinama}}


def _gecis_olc(ist: pd.Series, gunbasi: pd.Series) -> tuple[pd.Timestamp, dict]:
    """Saatlik kapanışın başladığı gün: Fonlama sütununun düzeltilmiş günlük barla
    birebirliğinin BİTTİĞİ gün. Önce ≥ %99 birebir, sonra ≤ %1 birebir şartı
    tutmazsa arşiv yazılmaz."""
    duz = fx.gunluk_duzelt(gunbasi)
    i = ist.index.intersection(duz.index).sort_values()
    es = ((ist.loc[i] / duz.loc[i] - 1).abs() < 1e-9)
    gecis = None
    for k in range(len(es)):
        if not es.iloc[k] and es.iloc[k:k + 20].sum() <= 1:
            gecis = es.index[k]
            break
    if gecis is None:
        raise SystemExit("✗ usdtry: geçiş günü bulunamadı (saatlik kısım ölçülemedi)")
    once, sonra = es[es.index < gecis], es[es.index >= gecis]
    olcu = {"gecis": str(gecis.date()),
            "once_ortak_gun": int(len(once)), "once_birebir": int(once.sum()),
            "sonra_ortak_gun": int(len(sonra)), "sonra_tesadufen_birebir": int(sonra.sum()),
            "son_birebir_gun": str(once[once].index.max().date())}
    if once.mean() < 0.99 or sonra.mean() > 0.01:
        raise SystemExit(f"✗ usdtry: geçiş ölçüsü belirsiz {olcu}")
    return gecis, olcu


def _kursaati_sina(ist: pd.Series) -> dict:
    """Saatlik kısmı KurSaati keşif arşivinin saatlik barlarından yeniden kur."""
    d = AP / "KurSaati" / "veri"
    h = pd.read_csv(d / "yf_fx_60m.csv.gz", header=[0, 1], index_col=0)
    c = pd.to_numeric(h[("USDTRY=X", "Close")], errors="coerce").dropna()
    c.index = pd.to_datetime(c.index, utc=True)
    simdi = json.loads((d / "kunye2_2026-10-02T0626.json").read_text(encoding="utf-8"))["baslangic_utc"]
    kp = fx.saatlik_kapanislar(c, fx.TR, pd.Timestamp(simdi).to_pydatetime())
    i = ist.index.intersection(kp.seri.index)
    bp = ((ist.loc[i] / kp.seri.loc[i] - 1).abs() * 1e4)
    k = {"ortak_gun": int(len(i)), "azami_fark_bp": round(float(bp.max()), 6) if len(i) else None,
         "aralik": [str(i.min().date()), str(i.max().date())] if len(i) else None}
    if not len(i) or k["azami_fark_bp"] > 0.5:
        UYARILAR.append(f"usdtry_ist18: KurSaati saatlik barlarıyla sınama tutmadı {k}")
    return k


def usdtry_yahoo():
    fyol = AP / "Fonlama" / "data" / "gunluk.csv"
    yyol = TARIH / "yf_USDTRY_X.csv"
    fon = oku(fyol, ["usdtry"])["usdtry"].dropna()
    gb = oku(yyol, ["Close"])["Close"].dropna()
    gecis, olcu = _gecis_olc(fon, gb)
    ist = fon[fon.index >= gecis]
    sinama = _kursaati_sina(ist)
    df = pd.concat({"usdtry_ist18": ist, "usdtry_gunbasi": gb}, axis=1, sort=True)
    df.index.name = "tarih"
    return "usdtry_yahoo_gunluk.csv.gz", df, {
        "frekans": "gunluk",
        "tarih_kurali": "usdtry_ist18: EVDS iş günü (Fonlama ekseni, Türkiye tatilleri yok); "
                        "usdtry_gunbasi: Yahoo barının Londra günü",
        "pratik": ["1B", "2", "3B", "4A", "4C", "10B", "11B", "11C", "11D"],
        "aciklama": "USD/TRY, Yahoo Finance (karar 09.09.2026). Olay kuru: geçişten itibaren "
                    "usdtry_ist18, öncesi fx_kapanis.gunluk_duzelt(usdtry_gunbasi). Geçiş günü ölçüldü",
        "sutun_aciklama": {
            "usdtry_ist18": "İstanbul 18:00 kapanışı, saatlik bardan (ortak/fx_kapanis; ortak/usdtry "
                            "SUTUN = usdtry_ist18). Yalnız geçiş gününden itibaren dolu",
            "usdtry_gunbasi": "Yahoo günlük barın kapanış alanı = D gününün BAŞINDAKİ fiyat "
                              "(D−1'in Londra gece yarısı kapanışı); _tarih arşivi 21.08.2026 "
                              "indirmesi, 20.08.2026'da biter"},
        "gecis": olcu,
        "kaynaklar": [
            kaynak(fyol, {"usdtry": "usdtry_ist18"}, aralik=f"{gecis.date()} →",
                   notu="Fonlama hattının ortak/usdtry.seri() çıktısı; geçiş öncesi kısmı "
                        "gunluk_duzelt(usdtry_gunbasi) ile birebir olduğu için alınmadı"),
            kaynak(yyol, {"Close": "usdtry_gunbasi"}),
            kaynak(AP / "KurSaati" / "veri" / "yf_fx_60m.csv.gz", {}, rol="sinama",
                   notu="saatlik barlardan İstanbul 18:00 yeniden kuruldu", sonuc=sinama)]}


def usdtry_tcmb():
    t_yol, o_yol, b_yol = TARIH / "kur.csv", AP / "OdemelerDengesi" / "data" / "gunluk.csv", \
        AP / "Butce" / "data" / "gunluk.csv"
    t = oku(t_yol, ["DK.USD.A.YTL"])["DK.USD.A.YTL"].dropna()
    o = oku(o_yol, ["usdtry"])["usdtry"].dropna()
    b = oku(b_yol, ["usdtry"])["usdtry"].dropna()
    s1, s2 = tek(t, o, "tcmb kur _tarih↔ÖD"), tek(o, b, "tcmb kur ÖD↔Bütçe")
    seri = pd.concat([t[t.index < o.index.min()], o, b[b.index > o.index.max()]]).sort_index()
    df = pd.DataFrame({"usdtry_tcmb_valor": seri})
    df.index.name = "tarih"
    return "usdtry_tcmb_gunluk.csv.gz", df, {
        "frekans": "valor", "ondalik": 8,
        "tarih_kurali": "VALÖR tarihi (ilan gününün ertesi iş günü); ölçüm katmanı bir iş günü geri alır",
        "pratik": ["2, 3B, 4A (yalnız sağlamlık)", "6A, 8A, 8C (dönüşüm kuru, karar 09.09.2026)",
                   "11A (1990–2005 kur bacağı)"],
        "aciklama": "TCMB gösterge niteliğindeki USD döviz alış kuru (EVDS TP.DK.USD.A.YTL), üç "
                    "depo kaynağından birleştirildi; örtüşen günlerde üçü birebir",
        "sutun_aciklama": {"usdtry_tcmb_valor": "TL/USD, döviz alış, valör tarihli"},
        "sinama": {"_tarih_ile_OD": s1, "OD_ile_Butce": s2},
        "kaynaklar": [
            kaynak(t_yol, {"DK.USD.A.YTL": "usdtry_tcmb_valor"}, aralik=f"→ {o.index.min().date()} öncesi"),
            kaynak(o_yol, {"usdtry": "usdtry_tcmb_valor"},
                   aralik=f"{o.index.min().date()} → {o.index.max().date()}"),
            kaynak(b_yol, {"usdtry": "usdtry_tcmb_valor"}, aralik=f"{o.index.max().date()} sonrası",
                   notu="ÖD hattı 11.09.2026'da bitiyor; aynı seriyi taşıyan Bütçe hattıyla çıpaya uzatıldı")]}


def gecelik():
    yol = TARIH / "gecelik.csv"
    df = oku(yol, ["PY.P06.ON"]).rename(columns={"PY.P06.ON": "gecelik_ao"}).dropna(how="all")
    return "gecelik_gunluk.csv.gz", df, {
        "frekans": "gunluk", "tarih_kurali": "EVDS iş günü", "pratik": ["11A"],
        "aciklama": "Bankalararası para piyasası gecelik ağırlıklı ortalama basit faiz (EVDS TP.PY.P06.ON)",
        "sutun_aciklama": {"gecelik_ao": "gecelik ağırlıklı ortalama basit faiz, %"},
        "kaynaklar": [kaynak(yol, {"PY.P06.ON": "gecelik_ao"})]}


def ppk():
    yol = AP / "KagitOis" / "veri" / "ppk_kararlari.csv.gz"
    df = oku(yol, ["politika"])
    return "ppk_kararlari.csv.gz", df, {
        "frekans": "olay", "tarih_kurali": "PPK karar günü", "pratik": ["3B"],
        "aciklama": "PPK faiz kararları, 2016–2026 (KagitOis arşivi; kaynağı bulten/ppk_endeks)",
        "sutun_aciklama": {"politika": "karar sonrası politika faizi, %"},
        "kaynaklar": [kaynak(yol, {"politika": "politika"},
                             kaynak_arsiv_ozu_tuttu=arsiv_ozu_sina(yol, yol.parent / "kunye.json"))]}


def enflasyon():
    yol = AP / "Enflasyon" / "data" / "aylik.csv"
    s = ["tufe", "hizmet", "mallar", "pka_ay_cari", "pka_12a"]
    return "enflasyon_aylik.csv.gz", oku(yol, s), {
        "frekans": "aylik", "tarih_kurali": "ay başı", "pratik": ["2 (anket etiketi)", "3A", "4A", "4C", "7B"],
        "aciklama": "Enflasyon hattı: TÜFE ve özel göstergeler (2025=100), PKA beklentileri",
        "sutun_aciklama": {"tufe": "TÜFE endeksi (TP.TUKFIY2025.GENEL, 2025=100)",
                           "hizmet": "hizmet fiyatları endeksi (TP.FE25.OKTG23)",
                           "mallar": "mallar endeksi (TP.FE25.OKTG08)",
                           "pka_ay_cari": "PKA cari ay aylık TÜFE beklentisi, % (TP.PKAUO.S01.A.U)",
                           "pka_12a": "PKA 12 ay sonrası yıllık TÜFE beklentisi, % (TP.PKAUO.S01.E.U)"},
        "kaynaklar": [kaynak(yol, {c: c for c in s})]}


def pka_faiz():
    yol = AP / "DIBS" / "data" / "aylik.csv"
    s = ["pka_faiz_12a", "pka_faiz_24a"]
    df = oku(yol, s)
    e = oku(AP / "Enflasyon" / "data" / "aylik.csv", ["pka_faiz_12a"])["pka_faiz_12a"]
    return "pka_faiz_aylik.csv.gz", df, {
        "frekans": "aylik", "tarih_kurali": "anketin ay etiketi (ay başı); yayım günü bu dosyada YOK",
        "pratik": ["3A", "5C (yamuk patika; ay etiketi kirliliği)"],
        "aciklama": "PKA politika faizi beklentileri, ham aylık (DİBS hattı)",
        "sutun_aciklama": {"pka_faiz_12a": "12 ay sonrası politika faizi beklentisi, % (TP.PKAUO.S04.D.U)",
                           "pka_faiz_24a": "24 ay sonrası politika faizi beklentisi, % (TP.PKAUO.S04.E.U)"},
        "sinama": {"enflasyon_hatti_pka_faiz_12a_ile": tek(e, df["pka_faiz_12a"], "pka_faiz_12a Enf↔DİBS")},
        "kaynaklar": [kaynak(yol, {c: c for c in s})]}


def gsyh():
    b_yol = AP / "Buyume" / "data" / "harcama_mevsim_takvim.csv"
    o_yol = AP / "OdemelerDengesi" / "data" / "ceyreklik.csv"
    b = oku(b_yol, ["TP_GSYIH30_HY_B1GQ"])["TP_GSYIH30_HY_B1GQ"]
    o = oku(o_yol, ["gsyh_bin_tl"])["gsyh_bin_tl"]
    df = pd.concat({"gsyh_mta_hacim": b, "gsyh_cari_bin_tl": o}, axis=1, sort=True)
    df.index.name = "tarih"
    return "gsyh_ceyreklik.csv.gz", df, {
        "frekans": "ceyreklik", "tarih_kurali": "çeyrek sonu", "pratik": ["3A", "3D", "5B", "6A", "8A", "8C"],
        "aciklama": "GSYH: mevsim ve takvim etkisinden arındırılmış zincirlenmiş hacim endeksi "
                    "(Büyüme hattı, EVDS bie_gsyzhend) ve cari fiyatlarla GSYH (ÖD hattı)",
        "sutun_aciklama": {"gsyh_mta_hacim": "harcama yöntemiyle GSYH, mevsim ve takvim arındırılmış "
                                             "zincirlenmiş hacim endeksi (TP.GSYIH30.HY.B1GQ)",
                           "gsyh_cari_bin_tl": "GSYH, cari fiyatlarla, bin TL (TP.GSYIH20.BY.B1GQ)"},
        "kaynaklar": [kaynak(b_yol, {"TP_GSYIH30_HY_B1GQ": "gsyh_mta_hacim"}),
                      kaynak(o_yol, {"gsyh_bin_tl": "gsyh_cari_bin_tl"})]}


def butce_aylik():
    yol = AP / "Butce" / "data" / "aylik.csv"
    s = ["my_gelir", "my_gider", "faiz_disi_gider", "faiz_gideri", "ic_borc_toplam"]
    return "butce_aylik.csv.gz", oku(yol, s), {
        "frekans": "aylik", "tarih_kurali": "ay başı", "pratik": ["5B", "6A", "8A"],
        "aciklama": "Merkezi yönetim bütçesi (aylık akım, bin TL) ve iç borç stoku (bin TL). "
                    "Faiz dışı denge = my_gelir − faiz_disi_gider",
        "sutun_aciklama": {"my_gelir": "merkezi yönetim gelirleri, bin TL (TP.KB.GEL001)",
                           "my_gider": "merkezi yönetim giderleri, bin TL (TP.KB.GID001)",
                           "faiz_disi_gider": "faiz hariç giderler, bin TL (TP.KB.GID002)",
                           "faiz_gideri": "faiz giderleri, bin TL (TP.KB.GID152)",
                           "ic_borc_toplam": "merkezi yönetim iç borç stoku, bin TL"},
        "kaynaklar": [kaynak(yol, {c: c for c in s})]}


def butce_ceyreklik():
    yol = AP / "Butce" / "data" / "ceyreklik_metrik.csv"
    s = ["gsyh_yil_trl", "denge_gsyh", "fdd_gsyh", "faiz_gsyh", "stok_trl", "stok_gsyh",
         "ic_borc_ceyrek_trl", "dis_senet_ceyrek_trl", "dis_kredi_ceyrek_trl", "doviz_borc_ceyrek_trl",
         "fh_borc_trl", "fh_borc_gsyh", "db_my_mlrusd"]
    return "butce_ceyreklik.csv.gz", oku(yol, s), {
        "frekans": "ceyreklik", "tarih_kurali": "çeyrek sonu", "pratik": ["5B", "6A", "6B", "6C"],
        "aciklama": "Bütçe hattının çeyreklik ölçümleri: 12 aylık akımların GSYH'ye oranı, borç "
                    "stoku ve bacakları (trilyon TL), finansal hesaplardan borç, merkezi yönetim dış borcu",
        "sutun_aciklama": {
            "gsyh_yil_trl": "4 çeyreklik GSYH toplamı, trilyon TL",
            "denge_gsyh": "12 aylık bütçe dengesi / GSYH, %", "fdd_gsyh": "12 aylık faiz dışı denge / GSYH, %",
            "faiz_gsyh": "12 aylık faiz gideri / GSYH, %",
            "stok_trl": "merkezi yönetim borç stoku (bileşik, 2020Ç3+), trilyon TL",
            "stok_gsyh": "borç stoku / GSYH, %",
            "ic_borc_ceyrek_trl": "iç borç stoku, çeyrek sonu, trilyon TL",
            "dis_senet_ceyrek_trl": "dış borçlanma senetleri, trilyon TL (2020Ç3+)",
            "dis_kredi_ceyrek_trl": "dış krediler, trilyon TL (2020Ç3+)",
            "doviz_borc_ceyrek_trl": "döviz cinsi ve dövize endeksli borç, trilyon TL (2020Ç3+)",
            "fh_borc_trl": "finansal hesaplar: borçlanma senetleri + krediler, piyasa değerli, trilyon TL",
            "fh_borc_gsyh": "fh_borc_trl / GSYH, %",
            "db_my_mlrusd": "merkezi yönetim brüt dış borç stoku, milyar USD"},
        "kaynaklar": [kaynak(yol, {c: c for c in s})]}


def kkm():
    yol = AP / "Kredi" / "data" / "metrik_aylik.csv"
    s = ["kkm_tl_mlr", "kkm_usd_mia"]
    return "kkm_aylik.csv.gz", oku(yol, s).dropna(how="all"), {
        "frekans": "aylik", "tarih_kurali": "ay başı", "pratik": ["6B", "5B (tek seferlik kalem adı)"],
        "aciklama": "Kur korumalı mevduat stoku (Kredi hattı)",
        "sutun_aciklama": {"kkm_tl_mlr": "TL KKM, milyar TL (TP.KKM.K4)",
                           "kkm_usd_mia": "döviz dönüşümlü KKM, milyar USD (TP.KKM.K1)"},
        "kaynaklar": [kaynak(yol, {c: c for c in s})]}


def redk():
    yol = AP / "TRYREER" / "reer_analysis_data.csv"
    sut = {"CPI_REER": "redk_tufe", "PPI_REER": "redk_ufe"}
    return "redk_aylik.csv.gz", oku(yol, list(sut)).rename(columns=sut), {
        "frekans": "aylik", "tarih_kurali": "ay başı", "pratik": ["7A", "8B", "8C", "Araç 3"],
        "aciklama": "TCMB reel efektif döviz kuru (2025=100). YÖN: artış TL'nin reel DEĞER KAZANCIDIR",
        "sutun_aciklama": {"redk_tufe": "TÜFE bazlı REDK (TP.RK.T1.Y)",
                           "redk_ufe": "Yİ-ÜFE bazlı REDK (TP.RK.U01.Y)"},
        "kaynaklar": [kaynak(yol, sut)]}


def odemeler():
    yol = AP / "OdemelerDengesi" / "data" / "aylik.csv"
    s = ["cari", "mal_denge", "hc_altin_net", "hc_enerji_net", "hc_cekirdek"]
    return "odemeler_aylik.csv.gz", oku(yol, s).dropna(how="all"), {
        "frekans": "aylik", "tarih_kurali": "ay başı (1984 öncesi gözlemler yalnız Aralık)",
        "pratik": ["8A", "8B", "8C", "10B (enerji dengesi)"],
        "aciklama": "Ödemeler dengesi, milyon USD. Altın ve enerji hariç mal dengesi = "
                    "mal_denge − hc_altin_net − hc_enerji_net",
        "sutun_aciklama": {"cari": "cari işlemler dengesi (TP.ODANA6.Q01)",
                           "mal_denge": "dış ticaret (mal) dengesi, ödemeler dengesi tanımı (TP.ODANA6.Q04)",
                           "hc_altin_net": "net parasal olmayan altın (TP.HARICCARIACIK.K4), 1996+",
                           "hc_enerji_net": "net enerji (TP.HARICCARIACIK.K7), 1996+",
                           "hc_cekirdek": "altın ve enerji hariç cari denge (TP.HARICCARIACIK.K10), 1996+"},
        "kaynaklar": [kaynak(yol, {c: c for c in s})]}


OVP_SATIR = ("yurtici_tasarruf_gsyh", "tasarruf_yatirim_farki_gsyh", "cari_gsyh",
             "genel_devlet_dengesi_gsyh", "kkgd_gsyh")


def ovp():
    yol = AP / "OVP" / "programlar.json"
    p = json.loads(yol.read_text(encoding="utf-8"))
    satir, belge = [], {}
    for pr in p["programlar"]:
        belge[pr["kod"]] = {"kaynak": pr.get("kaynak"), "yayin_ay": pr.get("yayin_ay"),
                            "sayfa": pr.get("sayfa"), "not": pr.get("not")}
        for yil, tur in sorted(pr["sutun"].items()):
            r = {"program": pr["kod"], "yayin_ay": pr["yayin_ay"], "yil": int(yil), "sutun": tur}
            for s in OVP_SATIR:
                v = (pr["deger"].get(s) or {}).get(yil)
                r[s] = float(v) if v is not None else None
            satir.append(r)
    df = pd.DataFrame(satir).sort_values(["program", "yil"]).reset_index(drop=True)
    for s in OVP_SATIR:
        df[s] = df[s].astype("float64")
    return "ovp_programlar.csv.gz", df, {
        "frekans": "belge", "tarih_kurali": "yıl (program sütunu)", "pratik": ["8A (kontrol noktası)"],
        "aciklama": "Orta Vadeli Program tabloları (elle tutulan kayıt), yüzde GSYH satırları; "
                    "sütun: gerceklesme · tahmin · program",
        "sutun_aciklama": {s: p["satir"][s]["ad"] + " (" + p["satir"][s]["tablo"] + ")" for s in OVP_SATIR},
        "belge": belge, "kaynaklar": [kaynak(yol, {s: s for s in OVP_SATIR})]}


def rezerv():
    yol = AP / "TCMBNetRezerv" / "haftalik_rezerv.csv"
    s = ["brut_rezerv_usd", "net_rezerv_usd", "swap_haric_net_rezerv_usd"]
    return "rezerv_haftalik.csv.gz", oku(yol, s), {
        "frekans": "haftalik", "tarih_kurali": "hafta (cuma)", "pratik": ["9A", "9B"],
        "aciklama": "TCMB rezervleri, milyar USD (TCMB Net Rezerv hattı)",
        "sutun_aciklama": {"brut_rezerv_usd": "brüt rezerv", "net_rezerv_usd": "net rezerv",
                           "swap_haric_net_rezerv_usd": "swap hariç net rezerv"},
        "kaynaklar": [kaynak(yol, {c: c for c in s})]}


def dis_borc_odeme():
    yol = AP / "OdemelerDengesi" / "data" / "haftalik.csv"
    s = ["borc_odeme_top", "borc_odeme_haz", "borc_odeme_dgr", "borc_odeme_tcmb"]
    return "dis_borc_odeme_haftalik.csv.gz", oku(yol, s), {
        "frekans": "haftalik", "tarih_kurali": "hafta (çarşamba)", "pratik": ["9A (vekil payda)"],
        "aciklama": "Haftalık dış borç ödemeleri, milyon USD (EVDS bie_dbafod)",
        "sutun_aciklama": {"borc_odeme_top": "toplam (TP.D1TOP)", "borc_odeme_haz": "Hazine (TP.D2HAZ)",
                           "borc_odeme_dgr": "diğer (TP.D3DIG)", "borc_odeme_tcmb": "TCMB (TP.D4TCMB)"},
        "kaynaklar": [kaynak(yol, {c: c for c in s})]}


def kuresel():
    yol = AP / "ElNino" / "data" / "kuresel.csv"
    s = ["emtia_enerji", "emtia_metal", "abd_tufe", "abd_cekirdek", "faiz_abd", "faiz_ea"]
    return "kuresel_aylik.csv.gz", oku(yol, s), {
        "frekans": "aylik", "tarih_kurali": "ay başı", "pratik": ["4C", "10A", "10B", "11A (i*)"],
        "aciklama": "El Niño hattının küresel kanadı: Dünya Bankası Pink Sheet, BLS, BIS",
        "sutun_aciklama": {"emtia_enerji": "Pink Sheet enerji endeksi (nominal USD)",
                           "emtia_metal": "Pink Sheet metal ve mineraller endeksi (nominal USD)",
                           "abd_tufe": "ABD TÜFE, mevsimsellikten arındırılmamış (BLS CUUR0000SA0)",
                           "abd_cekirdek": "ABD çekirdek TÜFE (BLS CUUR0000SA0L1E)",
                           "faiz_abd": "ABD politika faizi, % (BIS WS_CBPOL M.US; efektif fon faiziyle "
                                       "aynı tanımda değil)",
                           "faiz_ea": "euro alanı politika faizi, % (BIS WS_CBPOL M.XM)"},
        "kaynaklar": [kaynak(yol, {c: c for c in s})]}


EM = (("BRL", "brl"), ("MXN", "mxn"), ("ZAR", "zar"), ("INR", "inr"))


def em_kur():
    parca, kay = {}, []
    for kod, ad in EM:
        yol = TARIH / f"yf_{kod}_X.csv"
        parca[f"{ad}_gunbasi"] = oku(yol, ["Close"])["Close"].dropna()
        kay.append(kaynak(yol, {"Close": f"{ad}_gunbasi"}))
    df = pd.concat(parca, axis=1, sort=True)
    df.index.name = "tarih"
    return "em_kur_yahoo_gunluk.csv.gz", df, {
        "frekans": "gunluk", "tarih_kurali": "Yahoo barının Londra günü", "pratik": ["11B", "11C"],
        "aciklama": "EM kurları, Yahoo Finance günlük bar (_tarih arşivi, 21.08.2026 indirmesi; "
                    "20.08.2026'da biter). D tarihli değer D gününün BAŞINDAKİ fiyattır",
        "sutun_aciklama": {f"{ad}_gunbasi": f"USD/{kod}, günlük barın kapanış alanı (günün başı)"
                           for kod, ad in EM},
        "kaynaklar": kay}


EM_FAIZ = ("TUR", "ARG", "BRA", "RUS", "MEX", "ZAF", "IND", "IDN")


def em_politika():
    yol = TARIH / "polfaiz.csv"
    sut = {f"BISPOLFAIZ.{k}": k.lower() for k in EM_FAIZ}
    return "em_politika_aylik.csv.gz", oku(yol, list(sut)).rename(columns=sut).dropna(how="all"), {
        "frekans": "aylik", "tarih_kurali": "ay başı",
        "pratik": ["11B", "3A (tur: 2018 öncesi politika faizi)", "9–10 (Rusya 2014 vakası)"],
        "aciklama": "BIS politika faizleri, EVDS aynası (TP.BISPOLFAIZ.<ülke>), aylık, %",
        "sutun_aciklama": {v: f"{k} politika faizi, %" for k, v in sut.items()},
        "kaynaklar": [kaynak(yol, sut)]}


def yabanci():
    yol = AP / "ForeignHoldings" / "foreign_holdings_data.csv"
    sut = {"Hisse": "hisse", "DIBS": "dibs"}
    df = oku(yol, list(sut)).rename(columns=sut)
    sifir = df[(df == 0).any(axis=1)]
    if len(sifir):
        UYARILAR.append("yabanci_akim_haftalik: tam sıfır gözlem " + ", ".join(
            f"{t.date()} ({', '.join(c for c in df.columns if df.loc[t, c] == 0)})" for t in sifir.index)
            + " — kaynak hat tek taraflı boş haftayı 0 sayıyor olabilir, ölçüm katmanı sorar")
    return "yabanci_akim_haftalik.csv.gz", df, {
        "frekans": "haftalik", "tarih_kurali": "hafta (cuma)", "pratik": ["11D"],
        "aciklama": "Yurt dışı yerleşiklerin haftalık net alımı, milyon USD",
        "sutun_aciklama": {"hisse": "hisse senedi net (TP.MKNETHAR.M7)",
                           "dibs": "DİBS kesin alım net (TP.MKNETHAR.M8)"},
        "kaynaklar": [kaynak(yol, sut)]}


KURUCULAR = (abd_hazine, bund, cnbc_kur, yahoo_dxy_vix, cnbc_avrupa, ecb_maastricht, eurostat_uzun,
             dibs_egri, fonlama, usdtry_yahoo, usdtry_tcmb, gecelik, ppk, enflasyon, pka_faiz, gsyh,
             butce_aylik, butce_ceyreklik, kkm, redk, odemeler, ovp, rezerv, dis_borc_odeme, kuresel,
             em_kur, em_politika, yabanci)


# ── yazım ───────────────────────────────────────────────────────────────────
def _metin(df: pd.DataFrame, ondalik: int, indeksli: bool) -> str:
    return df.to_csv(float_format=f"%.{ondalik}f", lineterminator="\n", index=indeksli,
                     index_label="tarih" if indeksli else None)


def _kapsam(df: pd.DataFrame, gunluk: bool, zaman: str | None) -> dict:
    out = {}
    for c in df.columns:
        if (zaman and c == zaman) or not pd.api.types.is_numeric_dtype(df[c]):
            continue
        s = df[c].dropna()
        if s.empty:
            out[c] = {"n": 0}
            continue
        z = df.loc[s.index, zaman] if zaman else s.index
        k = {"n": int(len(s)), "sifir": int((s == 0).sum())}
        if zaman:
            k.update({"ilk": int(z.min()), "son": int(z.max())})
        else:
            k.update({"ilk": str(z.min().date()), "son": str(z.max().date())})
            if gunluk:
                ig = pd.bdate_range(z.min(), z.max())
                k["is_gunu_dolulugu"] = round(float(len(s.index.intersection(ig)) / max(1, len(ig))), 4)
        out[c] = k
    return out


def hazirla(kurucu) -> tuple[str, bytes, dict]:
    ad, df, meta = kurucu()
    indeksli = meta["frekans"] != "belge"
    if indeksli:
        if df.index.has_duplicates:
            raise SystemExit(f"✗ {ad}: yinelenen tarih {df.index[df.index.duplicated()][:5].tolist()}")
        df = df.sort_index()
        df, kesim = kes(df, meta["frekans"])
        df = df.dropna(how="all")
    else:
        kesim = {"kesilen_satir": 0}
    bos = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and df[c].dropna().empty]
    if bos:
        raise SystemExit(f"✗ {ad}: boş sütun {bos}")
    ondalik = meta.pop("ondalik", 6)
    metin = _metin(df, ondalik, indeksli)
    ham = metin.encode("utf-8")
    sayisal = df.select_dtypes("number")
    yuvarlama = float((sayisal - sayisal.round(ondalik)).abs().max().max()) if not sayisal.empty else 0.0
    zaman = None if indeksli else "yil"
    kayit = {
        "hazirlayan": HAZIRLAYAN, "sha256": hashlib.sha256(ham).hexdigest(),
        "satir": int(len(df)),
        "ilk": (str(df.index.min().date()) if indeksli else int(df["yil"].min())),
        "son": (str(df.index.max().date()) if indeksli else int(df["yil"].max())),
        "sutunlar": list(df.columns), "ondalik": ondalik, "azami_yuvarlama": yuvarlama,
        "cipa_siniri": (str(SINIR[meta["frekans"]].date()) if SINIR.get(meta["frekans"]) is not None
                        else None),
        **kesim, **meta,
        "kapsam": _kapsam(df, meta["frekans"] in ("gunluk", "valor"), zaman),
    }
    # KAPSAM ÖLÇÜLÜR: çıpadan belirgin önce biten sütun adıyla uyarı alır
    # (günlük/haftalık: 7 günden eski; aylık/çeyreklik: çıpa döneminden önce).
    sinir = SINIR.get(meta["frekans"])
    if sinir is not None and meta["frekans"] != "olay":
        pay = pd.Timedelta(days=7) if meta["frekans"] in ("gunluk", "haftalik", "valor") else \
            (pd.Timedelta(days=31) if meta["frekans"] == "aylik" else pd.Timedelta(days=90))
        for c, k in kayit["kapsam"].items():
            if k.get("son") and pd.Timestamp(k["son"]) < sinir - pay + pd.Timedelta(days=1):
                UYARILAR.append(f"{ad}:{c} {k['son']} tarihinde bitiyor (çıpa sınırı {sinir.date()})")
    return ad, ham, kayit


def _gz(ham: bytes) -> bytes:
    tampon = io.BytesIO()
    with gzip.GzipFile(fileobj=tampon, mode="wb", mtime=0) as g:
        g.write(ham)
    return tampon.getvalue()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--yeniden", action="store_true",
                    help="var olan arşivin üstüne yaz (yeni bir ders penceresi demektir)")
    a = ap.parse_args()

    eski = json.loads(KUNYE.read_text(encoding="utf-8")) if KUNYE.exists() else {}
    benim = [k for k, v in (eski.get("dosyalar") or {}).items() if v.get("hazirlayan") == HAZIRLAYAN]
    if not a.yeniden and (benim or "hazirla" in eski):
        print("arşiv zaten var — üstüne yazılmaz (bilinçli yenileme: --yeniden)")
        return 0

    # 1) Bütün çerçeveler önce kurulur ve sınanır; biri düşerse hiçbir şey yazılmaz.
    sonuc = [hazirla(k) for k in KURUCULAR]
    hedef = [ad for ad, _, _ in sonuc]
    if not a.yeniden:
        var = [ad for ad in hedef if (VERI / ad).exists()]
        if var:
            print(f"arşiv dosyaları zaten var ({', '.join(var)}) — üstüne yazılmaz (--yeniden)")
            return 0

    # 2) Yazım.
    VERI.mkdir(parents=True, exist_ok=True)
    for ad, ham, _ in sonuc:
        (VERI / ad).write_bytes(_gz(ham))
    dosyalar = {k: v for k, v in (eski.get("dosyalar") or {}).items()
                if v.get("hazirlayan") != HAZIRLAYAN}
    dosyalar.update({ad: kayit for ad, _, kayit in sonuc})
    head = _git("rev-parse", "HEAD")
    kunye = dict(eski)
    kunye["hazirla"] = {
        "cipa": {"commit": head, "commit_zamani": _git("show", "-s", "--format=%cI", head), **CIPA},
        "not": ("Depodaki girdiler (veri planı bölüm A). Kesim: günlük ve haftalık ≤ 30.09.2026, "
                "aylık ≤ 08.2026, çeyreklik ≤ 2026Ç2, TCMB valör kuru ≤ 01.10.2026 (30.09 ilanı). "
                "sha256 sıkıştırılmamış metnin özüdür; git_blob kaynak dosyanın `git hash-object` özü."),
        "uyarilar": UYARILAR, "bulunamayan": BULUNAMAYAN,
    }
    kunye["dosyalar"] = dict(sorted(dosyalar.items()))
    KUNYE.write_text(json.dumps(kunye, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for ad, _, k in sonuc:
        print(f"  ✓ {ad}: {k['satir']} satır · {k['ilk']} → {k['son']} · {len(k['sutunlar'])} sütun "
              f"· {k['sha256'][:12]}…")
    for u in UYARILAR:
        print("  ! " + u)
    return 0


if __name__ == "__main__":
    sys.exit(main())
