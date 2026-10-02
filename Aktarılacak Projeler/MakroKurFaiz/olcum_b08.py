#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRODAN KURA VE FAİZE — Bölüm 8 (Dış ticaret akımı ve cari denge) ölçüm katmanı.

Pratikler
  p8a   Türkiye sektörel dengeleri, çeyreklik 2006Ç4–2026Ç2: kamu (MERKEZİ
        YÖNETİM bütçesi, 12 aylık akım / GSYH; genel yönetim DEĞİL), dış
        denge (12 aylık cari denge / GSYH), özel kesim = dış − kamu (ARTIK).
        İkiz açık katsayısı (Δ4 dış denge ~ Δ4 kamu). OVP 2024–2025 kontrol
        noktası (tasarruf–yatırım farkı, cari/GSYH, genel devlet dengesi).
  p8b   J-eğrisi: REDK'nin (ARTIŞ = TL'nin REEL DEĞER KAZANCI) 0…24 ay
        gecikmeli 12 aylık log değişimine, altın ve enerji hariç mal
        dengesinin (mal dengesi − net parasal olmayan altın − net enerji)
        12 aylık toplamındaki 12 aylık değişimin (GSYH'ye oranla) tepkisi;
        gecikme başına ayrı Newey–West eğimi, gelir (GSYH büyümesi) kontrollü
        profil, yıllık kısıtsız dağıtılmış gecikme. Fiyat/miktar ayrımı
        bulut arşivindeki dış ticaret birim değer ve miktar endekslerinden.
  p8c   REDK sapması (log REDK'nin GENİŞLEYEN pencereli ortalamasından —
        ileriye bakmaz) → sonraki 12 ayda cari/GSYH ve çekirdek cari/GSYH
        değişimi; Newey–West (gecikme 24) ve örneklem dışı kıyas.
  p8d   Kırılgan Beşli vaka tablosu (TEST DEĞİL): 22.05.2013 → 30.08.2013
        BRL, INR, ZAR, TRY, IDR ve kontrol MXN; 2012 cari/GSYH (Dünya Bankası).
  sekil_13  üç denge (çeyreklik)
  sekil_14  J-eğrisi gecikme profili
  sekil_15  REDK sapması × sonraki 12 aylık cari denge değişimi (aylık)

YÖN. s = log(USD/yerel): artış yerel paranın DEĞER KAYBI. TCMB REDK'nin
ARTIŞI TL'nin REEL DEĞER KAZANCI; Marshall–Lerner'in uzun dönem işareti bu
yüzden EKSİdir (reel değer kazancı mal dengesini bozar). Dengeler GSYH'nin
yüzdesidir; oranın farkı PUANDIR.

DÖNÜŞÜM KURU (karar 09.09.2026). Dolar cinsi resmî tablolar TCMB gösterge
kuruyla çevrilir (ortak_olc.usdtry_tcmb; Yahoo değil). Her ayın akımı O AYIN
ortalama kuruyla çevrilir; çeyreklik TL GSYH aylara eşit bölünür (üçte bir)
ve o ayın kuruyla dolara çevrilir. Seçim: sektörel denge TL cinsinden
kurulur (cari dengenin her ayı kendi ayının kuruyla TL'ye, 12 aylık toplam /
4 çeyreklik TL GSYH), çünkü bütçe dengesi de TL akımının TL GSYH'ye oranıdır
ve özdeşlik (S − I) TL milli hesaplarda kurulur. Resmî biçim (dolar cari /
dolar GSYH) yanında durur; fark kur hızla değer kaybederken büyür.

ÖLÇÜLEREK BULUNAN TUZAKLAR (kod onları kapatır, metin adıyla anar)
  1. İKİ DÖNÜŞÜM KURALI HIZLI DEĞER KAYBINDA BİR PUANA YAKIN AYRIŞIR:
     2018Ç4'te TL oranı −%0,86, resmî dolar oranı −%1,84; 2022Ç2'de TL
     −%3,89, dolar −%2,88 (ortalama mutlak fark 0,13 puan). Sebep aritmetik:
     2018'in açık ayları düşük kurda, fazla ayları (Ağustos–Aralık) yüksek
     kurda; TL toplamı yüksek kurlu aylara daha çok ağırlık verir. Hangisinin "doğru"
     olduğu soruya bağlıdır; özdeşlik için TL, uluslararası kıyas için dolar.
  2. PAYDA ETKİSİ: dolar GSYH'si reel değer kaybıyla mekanik olarak küçülür,
     yani açık/GSYH oranı payı hiç değişmeden büyür (Δ(B/G) ≈ ΔB/G −
     (B/G)·Δln G). Çekirdek mal dengesi sıfıra yakın olduğu için p8b'de etki
     küçük; cari açıkta (−%3 civarı) %20'lik bir reel değer kaybı oranı tek
     başına ≈0,6 puan kötüleştirir. Ana ölçü bu yüzden SABİT PAYDALIDIR:
     dengedeki dolar değişimi, değişimin başındaki 12 aylık dolar GSYH'ye
     bölünür; oranın kendi değişimi sağlamlık olarak yanında.
  3. ÖRTÜŞEN UFUKTA ÖRNEKLEM DIŞI SINAMA SIZAR: ortak_olc.oos_kiyas eğitim
     penceresine t'den önceki BÜTÜN satırları alır; hedef "sonraki 12 ayın
     değişimi" olduğunda o satırların son on biri t anında henüz
     gerçekleşmemiştir. Bu modülün `oos_ambargolu`su eğitimi hedefi
     gerçekleşmiş satırlarla sınırlar (ambargo = ufuk) ve Diebold–Mariano
     t'sini ufka uygun Newey–West gecikmesiyle kurar. Sözleşme fonksiyonunun
     sonucu yanında yazılır; hüküm İKİSİNİN de geçmesini ister.
  4. GENİŞLEYEN ORTALAMA EĞİLİMİ SAPMA SANAR: TL 1994–2010 arasında reel
     değer kazandı, 2011–2022 arasında kaybetti; genişleyen ortalamadan
     sapma bu yüzden çoğunlukla eğilimdir (2007-12'de +31, 2021-12'de −63
     log puan; 2026-08'de genişleyen ortalamaya göre −17, kayan 10 yıllık
     ortalamaya göre +6 — aynı gün iki ters hüküm). Sağlamlık olarak kayan 10 yıllık ortalamadan sapma da sınanır.
  5. 2013 PENCERESİNİN UÇ GÜNLERİ İKİ SAATTEN: Yahoo kurları (BRL, INR,
     ZAR, MXN, TRY) düzeltilmiş günlük bardır, D değeri D'nin Londra gece
     yarısı kapanışıdır; 22.05.2013 Bernanke ifadesi 10:00 New York'ta
     (16:00 Orta Avrupa) başladığı için baz OLAY ÖNCESİ son kapanıştır
     (21.05). ECB referans kurları 14:15 Orta Avrupa'dadır, yani 22.05
     sabitlemesi ifadeden ÖNCEdir ve baz o gündür. Yahoo serisinde
     cumartesi barı olmadığı için 30.08.2013 CUMA değeri pazartesi barının
     başından gelir (hafta sonu açılışından sonraki fiyat); ECB sütunu bu
     kusuru taşımaz ve sağlamlık olarak yanında durur.
  6. ALTIN VE ENERJİ HARİÇ MAL DENGESİ ödemeler dengesi tanımıyla kurulur
     (mal dengesi − net parasal olmayan altın − net enerji); kalemler
     1996'dan başlar. Dış ticaret birim değer ve miktar endeksleri 2013'ten
     başlar, ithalat miktarında YAKIT HARİÇ endeks yoktur (değer ağırlığı
     olmadan çıkarılamaz): toplam ithalat miktarı ve yakıt ayrı verilir.
  7. SIZINTININ BÜYÜKLÜĞÜ ÖLÇÜLDÜ: p8c'de sözleşme fonksiyonunun örneklem
     dışı oranı 0,99 (kıyasa denk görünür), ambargolu oran 1,20 (kıyastan
     KÖTÜ). Gerçekleşmemiş hedefleri gören eğitim modeli olduğundan iyi
     gösteriyordu.
  8. GELİR KONTROLÜ İHRACATTA TERS NEDENSELDİR: ihracat GSYH'nin bir
     bileşenidir; ihracat miktarının yurt içi büyümeye "esnekliği" (+1,5)
     talep etkisi değil muhasebedir. Gelir kontrollü ihracat esnekliği bu
     yüzden yalnız sağlamlıktır; ithalatta kontrol anlamlıdır.

ÖLÇÜLEN BULGULAR (tuzak değil): J-eğrisinin KISA kolu yok — gecikme 0'da
eğim sıfır, 4–13 ayda anlamlı eksi, en derin 8. ayda; dolar faturalı
ticarette (baskın para) değer kaybının ilk aylarda dolar cinsi dengeyi
bozması beklenmez. İkiz açık eğimi EKSİ (−0,77): Türkiye'de kamu dengesi
bozulduğunda cari denge iyileşiyor, çünkü ikisini aynı çevrim (durgunlukta
gelir düşer, ithalat düşer) sürüklüyor; özel kesim kamuyu fazlasıyla dengeliyor.
"""
from __future__ import annotations

import math
import warnings
from functools import lru_cache

import numpy as np
import pandas as pd

import bulut
import ortak_olc as oo

warnings.filterwarnings("ignore", message="Could not infer format")   # ovp_programlar ilk sütunu tarih değil
warnings.filterwarnings("ignore", category=FutureWarning)

# ───────────────────────────────────────────────────────── sabitler (adlı)
HAC_GECIKME = 24              # 12 aylık toplamın 12 aylık değişimi ≈ 23 aylık örtüşme
HAC_GECIKME_CEYREK = 8        # çeyreklik Δ4 (4 çeyreklik toplamın 4 çeyreklik değişimi)
JEGRI_AZAMI_GECIKME = 24      # ay
SAPMA_ASGARI_AY = 60          # genişleyen ortalama için asgari geçmiş
SAPMA_KAYAN_AY = 120          # sağlamlık: kayan 10 yıllık ortalama
UFUK_AY = 12
OOS_ILK_AY = 120              # örneklem dışı ilk eğitim penceresi (ay)
OOS_ILK_CEYREK = 40
ALT_DONEM_BAS = "2003-01-01"  # dalgalı kur ve enflasyon hedeflemesi dönemi
YONETILEN_ONCESI_SON = "2021-11-01"   # yönetilen kur dönemi (2021-12 … 2023-06) öncesi son ay
TAPER = {"olay": "2013-05-22", "baz_yahoo": "2013-05-21", "baz_ecb": "2013-05-22", "son": "2013-08-30"}
BESLI = [("BRL", "BRA", "Brezilya"), ("INR", "IND", "Hindistan"), ("ZAR", "ZAF", "Güney Afrika"),
         ("TRY", "TUR", "Türkiye"), ("IDR", "IDN", "Endonezya")]
KONTROL = [("MXN", "MEX", "Meksika")]


# ───────────────────────────────────────────────────────── yardımcılar
def _f(x):
    return None if x is None or (isinstance(x, float) and not math.isfinite(x)) else float(x)


def _iso(t) -> str:
    return str(pd.Timestamp(t).date())


def kurulmadi(sebep: str) -> dict:
    return {"durum": "kurulmadi", "sebep": sebep}


def hukum(t: float | None, oranlar: list) -> str:
    """Bloomberg HRA 6.1: |t| ≥ 2 ve örneklem dışı karesel hata oranı < 1 birlikte."""
    gecti = (t is not None and abs(t) >= 2 and len(oranlar) > 0
             and all(o is not None and o < 1 for o in oranlar))
    return "ölçülü" if gecti else "tarif edici"


def oos_ambargolu(y: pd.Series, x: pd.Series, ilk_pencere: int, ambargo: int,
                  kiyas: str = "ortalama", gecikme: int = HAC_GECIKME) -> dict:
    """Genişleyen pencerede y = a + b·x tahmini ile saf kıyas (koşulsuz ortalama ya
    da sıfır); eğitim yalnız hedefi t anında GERÇEKLEŞMİŞ satırlarla kurulur
    (satır s, s + ambargo ≤ t ise). ambargo = 1 ortak_olc.oos_kiyas'ın eğitim
    kuralıdır. Diebold–Mariano t'si eşli karesel hata farkının Newey–West
    (verilen gecikme) ortalamasıdır; eksi t modelin lehine."""
    d = pd.concat([y.rename("y"), x.rename("x")], axis=1).dropna()
    e_m, e_k = [], []
    for t in range(ilk_pencere, len(d)):
        egit = d.iloc[: t - ambargo + 1]
        if len(egit) < 10:
            continue
        X = np.column_stack([np.ones(len(egit)), egit["x"].values])
        b = np.linalg.lstsq(X, egit["y"].values, rcond=None)[0]
        tah = b[0] + b[1] * d["x"].iloc[t]
        kiy = egit["y"].mean() if kiyas == "ortalama" else 0.0
        e_m.append((d["y"].iloc[t] - tah) ** 2)
        e_k.append((d["y"].iloc[t] - kiy) ** 2)
    if len(e_m) < 10:
        return kurulmadi("örneklem dışı sınama için en az on tahmin gerekir")
    e_m, e_k = np.array(e_m), np.array(e_k)
    dm = oo.hac(e_m - e_k, np.zeros((len(e_m), 0)), gecikme=gecikme, sabit=True)
    return {"n": int(len(e_m)), "mse_oran": float(e_m.mean() / e_k.mean()) if e_k.mean() else None,
            "dm_t": _f((dm.get("t") or [None])[0]), "kiyas": "koşulsuz ortalama" if kiyas == "ortalama" else "sıfır",
            "ambargo_ay": int(ambargo), "dm_gecikme": int(gecikme),
            "ilk": _iso(d.index[ilk_pencere])}


def _sozlesme_oos(y: pd.Series, x: pd.Series, ilk: int, kiyas: str = "ortalama") -> dict:
    o = oo.oos_kiyas(y, x, ilk, kiyas)
    if not o.get("n"):
        return kurulmadi("örneklem dışı sınama için gözlem yetersiz")
    return {"n": o["n"], "mse_oran": o.get("mse_oran"), "dm_t": o.get("dm_t"),
            "kiyas": "koşulsuz ortalama" if kiyas == "ortalama" else "sıfır", "ilk": o.get("ilk")}


def _reg(y: pd.Series, X, gecikme: int) -> dict:
    """Tek ya da çok değişkenli HAC regresyonu; örneklem tarihleri dahil."""
    if isinstance(X, pd.Series):
        X = X.to_frame()
    d = pd.concat([y.rename("_y"), X], axis=1).dropna()
    r = oo.hac(d["_y"].values, d.drop(columns="_y").values, gecikme=gecikme)
    if r.get("yetersiz"):
        return {"n": r["n"], **kurulmadi("regresyon için gözlem yetersiz")}
    return {"n": r["n"], "ilk": _iso(d.index.min()), "son": _iso(d.index.max()),
            "sabit": r["b"][0], "b": r["b"][1:], "se": r["se"][1:], "t": r["t"][1:],
            "r2": r["r2"], "gecikme": r["gecikme"]}


# ───────────────────────────────────────────────────────── ortak seriler
@lru_cache(maxsize=1)
def aylik_kur_ort() -> pd.Series:
    """TCMB gösterge kuru (TL/USD), ay ortalaması; dönüşüm kuru."""
    t = oo.usdtry_tcmb()
    return t.resample("MS").mean()


def _ceyrekten_aya(s: pd.Series, bol: bool) -> pd.Series:
    """Çeyrek sonu tarihli seriyi o çeyreğin üç ayına yayar (bol: üçe böler)."""
    out = {}
    for q, v in s.dropna().items():
        p = pd.Period(q, "Q")
        bas = p.asfreq("M", "s")
        for m in range(3):
            out[(bas + m).to_timestamp()] = v / 3 if bol else v
    return pd.Series(out, dtype="float64").sort_index()


@lru_cache(maxsize=1)
def aylik_gsyh_usd() -> pd.Series:
    """12 aylık dolar GSYH'si (milyon USD), aylık: çeyreklik cari fiyatlı TL GSYH
    aylara eşit bölünür, her ay kendi ortalama TCMB kuruyla dolara çevrilir ve
    12 ay toplanır. Son ay, GSYH'nin bilinen son çeyreğinin son ayıdır."""
    g = oo.oku("gsyh_ceyreklik")["gsyh_cari_bin_tl"] / 1e3          # milyon TL, çeyrek
    ga = _ceyrekten_aya(g, bol=True)
    k = aylik_kur_ort().reindex(ga.index)
    usd = (ga / k).rolling(12, min_periods=12).sum()
    usd.name = "gsyh12_mn_usd"
    return usd.dropna()


@lru_cache(maxsize=1)
def _odemeler() -> pd.DataFrame:
    o = oo.oku("odemeler_aylik")
    o = o[o.index >= "1992-01-01"].copy()     # 1992 öncesi yalnız yıllık (Aralık) gözlem
    o["cekirdek_mal"] = o["mal_denge"] - o["hc_altin_net"] - o["hc_enerji_net"]
    return o


def oniki_toplam(ad: str) -> pd.Series:
    """Ödemeler dengesi kaleminin 12 aylık toplamı (milyon USD)."""
    return _odemeler()[ad].rolling(12, min_periods=12).sum()


def gsyh_orani(ad: str) -> pd.Series:
    """Kalemin 12 aylık toplamı / 12 aylık dolar GSYH, %."""
    return (oniki_toplam(ad) / aylik_gsyh_usd() * 100).dropna()


def _redk_log() -> pd.Series:
    return np.log(oo.oku("redk_aylik")["redk_tufe"].dropna()) * 100


def _gelir_buyume_aylik() -> pd.Series:
    """Mevsim ve takvim arındırılmış reel GSYH'nin yıllık log büyümesi (%), çeyreğin üç ayına."""
    h = np.log(oo.oku("gsyh_ceyreklik")["gsyh_mta_hacim"].dropna()) * 100
    return _ceyrekten_aya(h.diff(4), bol=False)


# ───────────────────────────────────────────────────────── p8a
@lru_cache(maxsize=1)
def _sektorel() -> pd.DataFrame:
    o = _odemeler()
    k = aylik_kur_ort().reindex(o.index)
    cari_tl12 = (o["cari"] * k).rolling(12, min_periods=12).sum()       # milyon TL
    ceyrek = cari_tl12[cari_tl12.index.month.isin([3, 6, 9, 12])].copy()
    ceyrek.index = ceyrek.index + pd.offsets.QuarterEnd(0)
    b = oo.oku("butce_ceyreklik")
    dis = ceyrek / (b["gsyh_yil_trl"] * 1e6) * 100                      # trilyon TL → milyon TL
    # resmî biçim: dolar cari / dolar GSYH (çeyreklik TL GSYH çeyrek ortalama kuruyla)
    g = oo.oku("gsyh_ceyreklik")["gsyh_cari_bin_tl"] / 1e3
    kq = oo.usdtry_tcmb().resample("QE").mean()
    gusd4 = (g / kq.reindex(g.index)).rolling(4, min_periods=4).sum()
    cu = o["cari"].rolling(12, min_periods=12).sum()
    cu = cu[cu.index.month.isin([3, 6, 9, 12])].copy()
    cu.index = cu.index + pd.offsets.QuarterEnd(0)
    dis_usd = cu / gusd4 * 100
    df = pd.DataFrame({"kamu": b["denge_gsyh"], "dis": dis, "dis_usd": dis_usd}).dropna()
    df = df[df.index <= oo.CIPA_CEYREK.end_time.normalize()]
    df["ozel"] = df["dis"] - df["kamu"]
    return df


def _q(t) -> str:
    p = pd.Period(t, "Q")
    return f"{p.year}Ç{p.quarter}"


def p8a() -> dict:
    df = _sektorel()
    son = df.index.max()
    uc = {}
    for c in ("kamu", "dis", "ozel"):
        uc[c] = {"en_dusuk_gsyh_yuzde": float(df[c].min()), "en_dusuk_ceyrek": _q(df[c].idxmin()),
                 "en_yuksek_gsyh_yuzde": float(df[c].max()), "en_yuksek_ceyrek": _q(df[c].idxmax()),
                 "ortalama_gsyh_yuzde": float(df[c].mean())}
    fark = (df["dis"] - df["dis_usd"])
    donusum = {"tl_eksi_usd_azami_mutlak_puan": float(fark.abs().max()),
               "azami_ceyrek": _q(fark.abs().idxmax()),
               "azami_ceyrek_tl_gsyh_yuzde": float(df.loc[fark.abs().idxmax(), "dis"]),
               "azami_ceyrek_usd_gsyh_yuzde": float(df.loc[fark.abs().idxmax(), "dis_usd"]),
               "ortalama_mutlak_puan": float(fark.abs().mean()),
               "bir_puani_asan_ceyrek": int((fark.abs() >= 1).sum())}

    # ikiz açık: 4 çeyreklik değişimler (örtüşen; gecikme 8)
    d4 = df.diff(4).dropna()
    ikiz = _reg(d4["dis"], d4["kamu"], HAC_GECIKME_CEYREK)
    oos = _sozlesme_oos(d4["dis"], d4["kamu"], OOS_ILK_CEYREK, "ortalama")
    ikiz_out = {"n": ikiz["n"], "ilk": ikiz["ilk"], "son": ikiz["son"], "egim": ikiz["b"][0],
                "se": ikiz["se"][0], "t": ikiz["t"][0], "r2": ikiz["r2"], "gecikme": ikiz["gecikme"],
                "ozel_kesim_dengelemesi": 1 - ikiz["b"][0],
                "seviye_korelasyonu_kamu_ozel": float(df["kamu"].corr(df["ozel"])),
                "seviye_korelasyonu_kamu_dis": float(df["kamu"].corr(df["dis"])),
                "oos": oos, "hukum": hukum(ikiz["t"][0], [oos.get("mse_oran")]),
                "yontem": ("Dış dengenin dört çeyreklik değişimi kamu dengesinin dört çeyreklik değişimine "
                           "regrese edildi; eğim 1 tam ikiz açık, 0 özel kesimin kamuyu tamamen dengelemesi "
                           "demektir; standart hata Newey–West, örneklem dışı kıyas koşulsuz ortalama.")}

    # OVP kontrol noktası: kendi yıl sonu ölçümüm (Ç4) ile programın satırı
    ovp = oo.oku("ovp_programlar").reset_index()
    kontrol = []
    for _, r in ovp.iterrows():
        yil = int(r["yil"])
        if yil not in (2024, 2025) or r["sutun"] not in ("gerceklesme", "tahmin"):
            continue
        q4 = pd.Timestamp(f"{yil}-12-31")
        if q4 not in df.index:
            continue
        z = df.loc[q4]
        ovp_ozel = float(r["tasarruf_yatirim_farki_gsyh"] - r["genel_devlet_dengesi_gsyh"])
        kontrol.append({
            "program": r["program"], "yayin_ay": r["yayin_ay"], "yil": yil, "sutun": r["sutun"],
            "ovp_tasarruf_yatirim_farki_gsyh_yuzde": float(r["tasarruf_yatirim_farki_gsyh"]),
            "ovp_cari_gsyh_yuzde": float(r["cari_gsyh"]),
            "ovp_genel_devlet_dengesi_gsyh_yuzde": float(r["genel_devlet_dengesi_gsyh"]),
            "ovp_ozel_artik_gsyh_yuzde": ovp_ozel,
            "olcum_dis_tl_gsyh_yuzde": float(z["dis"]), "olcum_dis_usd_gsyh_yuzde": float(z["dis_usd"]),
            "olcum_kamu_merkezi_yonetim_gsyh_yuzde": float(z["kamu"]), "olcum_ozel_gsyh_yuzde": float(z["ozel"]),
            "fark_cari_usd_puan": float(z["dis_usd"] - r["cari_gsyh"]),
            "fark_cari_tl_puan": float(z["dis"] - r["cari_gsyh"]),
            "fark_dis_tasarruf_yatirim_puan": float(z["dis"] - r["tasarruf_yatirim_farki_gsyh"]),
            "fark_kamu_puan": float(z["kamu"] - r["genel_devlet_dengesi_gsyh"]),
            "fark_ozel_puan": float(z["ozel"] - ovp_ozel)})
    return {
        "yontem": ("Kamu dengesi merkezi yönetim bütçesinin 12 aylık dengesinin GSYH'ye oranı; dış denge 12 aylık "
                   "cari dengenin her ayı kendi ayının TCMB ortalama kuruyla liraya çevrilip toplanmış hâlinin "
                   "dört çeyreklik GSYH'ye oranı; özel kesim dengesi bu ikisinin farkı olarak kalan artık."),
        "kaynak": ["butce_ceyreklik (denge_gsyh, gsyh_yil_trl)", "odemeler_aylik (cari)",
                   "usdtry_tcmb_gunluk (dönüşüm kuru)", "gsyh_ceyreklik (cari fiyatlarla GSYH)",
                   "ovp_programlar (kontrol noktası)"],
        "kapsam_notu": ("Kamu MERKEZİ YÖNETİMDİR (genel yönetim değil: yerel yönetimler, sosyal güvenlik ve fonlar "
                        "dışarıda). Özel kesim ARTIKTIR: kapsam farkı, nakit–tahakkuk farkı, net hata ve noksan ile "
                        "dönüşüm kuru seçimi ona yazılır."),
        "donusum_secimi": ("TL oranı: aylık cari denge o ayın ortalama kuruyla liraya çevrilir; resmî dolar oranı "
                           "(çeyreklik TL GSYH çeyrek ortalama kuruyla dolara) karşılaştırma için yanında."),
        "n": int(len(df)), "ilk": _q(df.index.min()), "son": _q(son),
        "ilk_tarih": _iso(df.index.min()), "son_tarih": _iso(son),
        "son_deger": {"kamu_gsyh_yuzde": float(df.loc[son, "kamu"]), "dis_tl_gsyh_yuzde": float(df.loc[son, "dis"]),
                      "dis_usd_gsyh_yuzde": float(df.loc[son, "dis_usd"]), "ozel_gsyh_yuzde": float(df.loc[son, "ozel"])},
        "uc_degerler": uc, "donusum_farki": donusum, "ikiz_acik": ikiz_out, "ovp_kontrol": kontrol,
        "ovp_notu": ("OVP'nin satırları belgenin yayımlandığı günün verisidir; ödemeler dengesi ve GSYH sonradan "
                     "düzeltildiyse fark ölçüm hatası değil sürüm farkıdır. OVP özel kesim satırı burada "
                     "tasarruf–yatırım farkından genel devlet dengesi çıkarılarak kuruldu (artık)."),
    }


def sekil_13() -> dict:
    df = _sektorel()
    return {"baslik": "Türkiye sektörel dengeleri (% GSYH, 4 çeyreklik akım)",
            "tarih": [_iso(t) for t in df.index], "ceyrek": [_q(t) for t in df.index],
            "kamu": [float(v) for v in df["kamu"]], "dis": [float(v) for v in df["dis"]],
            "ozel": [float(v) for v in df["ozel"]], "dis_usd": [float(v) for v in df["dis_usd"]],
            "birim": "% GSYH", "ilk": _q(df.index.min()), "son": _q(df.index.max())}


# ───────────────────────────────────────────────────────── p8b
@lru_cache(maxsize=1)
def _jegri_cerceve() -> pd.DataFrame:
    B = oniki_toplam("cekirdek_mal")
    G = aylik_gsyh_usd()
    q = _redk_log()
    df = pd.DataFrame({
        "y_sabit": (B - B.shift(12)) / G.shift(12) * 100,          # puan, değişimin başındaki GSYH
        "y_oran": (B / G * 100).diff(12),                           # puan, oranın kendi değişimi
        "dq": q.diff(12),                                           # %, log×100
        "g": _gelir_buyume_aylik(),
    })
    df = df[df.index <= oo.CIPA_AY.to_timestamp()]
    return df


def _profil(df: pd.DataFrame, yad: str, kontrol: bool = False, bas: str | None = None,
            son: str | None = None) -> dict:
    """k = 0…24 için ayrı HAC eğimi; sütun dizileri (kompakt). Örneklem her gecikmede aynıdır
    (reel kur 1994'ten başlar, bağımlı değişken 1997 sonundan), n/ilk/son bir kez yazılır."""
    z = df if bas is None else df[df.index >= bas]
    z = z if son is None else z[z.index <= son]
    out = {"gecikme_ay": [], "egim": [], "se": [], "t": [], "r2": []}
    if kontrol:
        out.update({"gelir_egim": [], "gelir_t": []})
    nler = set()
    for k in range(JEGRI_AZAMI_GECIKME + 1):
        X = pd.DataFrame({"dq": df["dq"].shift(k)}).reindex(z.index)
        if kontrol:
            X["g"] = z["g"]
        r = _reg(z[yad], X, HAC_GECIKME)
        out["gecikme_ay"].append(k)
        out["egim"].append(r["b"][0]); out["se"].append(r["se"][0]); out["t"].append(r["t"][0])
        out["r2"].append(r["r2"])
        if kontrol:
            out["gelir_egim"].append(r["b"][1]); out["gelir_t"].append(r["t"][1])
        nler.add((r["n"], r["ilk"], r["son"]))
    n, ilk, son = sorted(nler)[0]
    out.update({"n": n, "ilk": ilk, "son": son, "ayni_orneklem": len(nler) == 1,
                "birim": "puan (% GSYH) / REDK'nin %1'lik (log) değişimi", "gecikme": HAC_GECIKME})
    return out


def _profil_ozeti(pr: dict) -> dict:
    b = np.array(pr["egim"])
    t = np.array(pr["t"])
    g = pr["gecikme_ay"]
    j = int(np.argmin(b))
    anlamli_eksi = [g[i] for i in range(len(g)) if t[i] <= -2]
    anlamli_arti = [g[i] for i in range(len(g)) if t[i] >= 2]
    return {"en_eksi_gecikme_ay": int(g[j]), "en_eksi_egim_puan_yuzde": float(b[j]),
            "en_eksi_t": float(t[j]), "on_yuzde_reel_deger_kazanci_puan": float(10 * b[j]),
            "anlamli_eksi_gecikmeler_ay": anlamli_eksi, "anlamli_arti_gecikmeler_ay": anlamli_arti,
            "gecikme0_egim": float(b[0]), "gecikme0_t": float(t[0]),
            "gecikme24_egim": float(b[-1]), "gecikme24_t": float(t[-1]),
            # J-eğrisi: ilk altı ayda anlamlı ARTI eğim ve sonra anlamlı EKSİ eğim
            "j_isareti_kisa_arti_uzun_eksi": bool(any(t[i] >= 2 for i in range(7)) and len(anlamli_eksi) > 0)}


def _fiyat_miktar(df: pd.DataFrame) -> dict:
    try:
        e = bulut.dis_ticaret_endeks()
    except bulut.VeriYok as hata:
        return kurulmadi(f"{hata}; fiyat ve miktar ayrımı yapılamadı")
    seriler = {
        "ihracat_miktar": np.log(e["ihr_miktar"]) * 100,
        "ithalat_miktar": np.log(e["ith_miktar"]) * 100,
        "ithalat_yakit_miktar": np.log(e["ith_yakit_miktar"]) * 100,
        "ticaret_hadleri": np.log(e["ihr_birim_deger"] / e["ith_birim_deger"]) * 100,
        "ihracat_birim_deger": np.log(e["ihr_birim_deger"]) * 100,
        "ithalat_birim_deger": np.log(e["ith_birim_deger"]) * 100,
    }
    out = {"yontem": ("Dış ticaret miktar ve birim değer endekslerinin 12 aylık log değişimi, reel efektif kurun "
                      "aynı aydaki ve 12 ay önceki 12 aylık log değişimine ayrı ayrı regrese edildi; ikinci "
                      "tanımda yurt içi gelir büyümesi kontrol."),
           "kaynak": ["bulut: EVDS dış ticaret birim değer ve miktar endeksleri (2010=100)", "redk_aylik",
                      "gsyh_ceyreklik (hacim endeksi)"],
           "birim": "endeksin yüzde değişimi / REDK'nin yüzde değişimi (log×100)",
           "kalemler": {}}
    for ad, s in seriler.items():
        y = s.diff(12)
        kalem = {}
        for k in (0, 12):
            x = df["dq"].shift(k)
            r = _reg(y, x.rename("dq"), HAC_GECIKME)
            rg = _reg(y, pd.DataFrame({"dq": x, "g": df["g"]}), HAC_GECIKME)
            kalem[f"gecikme_{k}"] = {"esneklik": r["b"][0], "se": r["se"][0], "t": r["t"][0], "r2": r["r2"],
                                     "n": r["n"], "ilk": r["ilk"], "son": r["son"],
                                     "gelir_kontrollu_esneklik": rg["b"][0], "gelir_kontrollu_t": rg["t"][0],
                                     "gelir_kontrollu_n": rg["n"],
                                     "gelir_esneklik": rg["b"][1], "gelir_t": rg["t"][1]}
        d = pd.concat([y.rename("y"), df["dq"].shift(12).rename("x")], axis=1).dropna()
        oos = oos_ambargolu(d["y"], d["x"], ilk_pencere=min(60, len(d) // 2), ambargo=UFUK_AY)
        kalem["oos_gecikme_12"] = oos
        kalem["hukum_gecikme_12"] = hukum(kalem["gecikme_12"]["t"], [oos.get("mse_oran")])
        out["kalemler"][ad] = kalem
    out["sinir"] = ("İthalatta yakıt hariç miktar endeksi yok; değer ağırlıkları olmadan toplamdan çıkarılamaz. "
                    "Endeksler 2013'te başlar ve yönetilen kur dönemini (2021-12 … 2023-06) içerir. İhracat GSYH'nin "
                    "bileşeni olduğu için ihracatta gelir kontrolü ters nedenseldir, yalnız sağlamlıktır.")
    return out


def p8b() -> dict:
    df = _jegri_cerceve()
    ana = _profil(df, "y_sabit")
    gelir = _profil(df, "y_sabit", kontrol=True)
    oran = _profil(df, "y_oran")
    alt = _profil(df, "y_sabit", bas=ALT_DONEM_BAS)
    yon_once = _profil(df, "y_sabit", son=YONETILEN_ONCESI_SON)
    # yıllık kısıtsız dağıtılmış gecikme: örtüşmeyen üç yıllık değişim birlikte
    X = pd.DataFrame({"yil0": df["dq"], "yil1": df["dq"].shift(12), "yil2": df["dq"].shift(24)})
    dl = _reg(df["y_sabit"], X, HAC_GECIKME)
    Xg = X.assign(g=df["g"])
    dlg = _reg(df["y_sabit"], Xg, HAC_GECIKME)

    def _dl(r: dict, gelirli: bool) -> dict:
        b, se, t = r["b"], r["se"], r["t"]
        o = {f"yil{i}_egim": b[i] for i in range(3)} | {f"yil{i}_t": t[i] for i in range(3)} | \
            {f"yil{i}_se": se[i] for i in range(3)}
        o.update({"toplam_egim": float(sum(b[:3])), "r2": r["r2"], "n": r["n"], "ilk": r["ilk"], "son": r["son"],
                  "gecikme": r["gecikme"]})
        if gelirli:
            o.update({"gelir_egim": b[3], "gelir_t": t[3]})
        return o
    # örneklem dışı: 12 ay önceki reel kur değişimi → bu yılın değişimi (gerçek öngörü ufku)
    d = pd.concat([df["y_sabit"].rename("y"), df["dq"].shift(12).rename("x")], axis=1).dropna()
    oos_s = _sozlesme_oos(d["y"], d["x"], OOS_ILK_AY, "ortalama")
    oos_a = oos_ambargolu(d["y"], d["x"], OOS_ILK_AY, ambargo=UFUK_AY)
    return {
        "yontem": ("Altın ve enerji hariç mal dengesinin 12 aylık toplamındaki 12 aylık değişim (dolar; değişimin "
                   "başındaki 12 aylık dolar GSYH'ye oranla, puan), reel efektif kurun k ay önceki 12 aylık log "
                   "değişimine her k = 0…24 için ayrı regrese edildi; standart hata Newey–West (gecikme 24)."),
        "kaynak": ["odemeler_aylik (mal_denge, hc_altin_net, hc_enerji_net)", "redk_aylik (redk_tufe)",
                   "gsyh_ceyreklik", "usdtry_tcmb_gunluk (dönüşüm kuru)"],
        "isaret": ("REDK artışı TL'nin reel değer kazancıdır: eksi eğim, reel değer kazancının dengeyi bozduğu "
                   "(Marshall–Lerner yönü) demektir; J-eğrisi kısa gecikmede ARTI, uzun gecikmede EKSİ eğim ister."),
        "birim": "puan (% GSYH) / REDK'nin %1'lik (log) değişimi",
        "n": ana["n"], "ilk": ana["ilk"], "son": ana["son"],
        "profil": ana, "ozet": _profil_ozeti(ana),
        "gelir_kontrollu": {"profil": gelir, "ozet": _profil_ozeti(gelir),
                            "yontem": "Aynı regresyona yurt içi reel GSYH'nin yıllık büyümesi kontrol olarak eklendi."},
        "oran_degisimi": {"profil": oran, "ozet": _profil_ozeti(oran),
                          "yontem": "Bağımlı değişken dengenin GSYH'ye oranının kendi 12 aylık değişimi (payda etkisi dahil)."},
        "alt_donem_2003": {"profil": alt, "ozet": _profil_ozeti(alt),
                           "yontem": "Ana tanım, 2003 sonrası (dalgalı kur ve enflasyon hedeflemesi dönemi)."},
        "yonetilen_oncesi": {"ozet": _profil_ozeti(yon_once), "n": yon_once["n"], "ilk": yon_once["ilk"],
                             "son": yon_once["son"],
                             "gecikme_12": {"egim_puan_yuzde": yon_once["egim"][12], "t": yon_once["t"][12]},
                             "yontem": ("Ana tanım, yönetilen kur dönemi (2021-12 … 2023-06) başlamadan biten "
                                        "örneklem; bu bir kur tepkisi değil, dönem sağlamlık için ayrılır.")},
        "yillik_dagitilmis_gecikme": {"gelirsiz": _dl(dl, False), "gelir_kontrollu": _dl(dlg, True),
                                      "yontem": ("Reel kurun bu yılki, bir yıl önceki ve iki yıl önceki 12 aylık "
                                                 "değişimleri birlikte (örtüşmeyen pencereler).")},
        "oos_gecikme_12": {"sozlesme": oos_s, "ambargolu": oos_a},
        "gecikme_12": {"egim_puan_yuzde": ana["egim"][12], "se": ana["se"][12], "t": ana["t"][12]},
        "hukum_gecikme_12": hukum(ana["t"][12], [oos_s.get("mse_oran"), oos_a.get("mse_oran")]),
        "fiyat_miktar": _fiyat_miktar(df),
    }


def sekil_14() -> dict:
    df = _jegri_cerceve()
    ana = _profil(df, "y_sabit")
    gelir = _profil(df, "y_sabit", kontrol=True)
    return {"baslik": "J-eğrisi: reel kur değişiminin çekirdek mal dengesine gecikmeli etkisi",
            "gecikme_ay": ana["gecikme_ay"], "egim": ana["egim"], "se": ana["se"],
            "egim_gelir_kontrollu": gelir["egim"], "se_gelir_kontrollu": gelir["se"],
            "birim": ana["birim"], "ilk": ana["ilk"], "son": ana["son"], "n": ana["n"]}


# ───────────────────────────────────────────────────────── p8c
@lru_cache(maxsize=1)
def _sapma_cerceve() -> pd.DataFrame:
    q = _redk_log()
    gen = q.expanding(min_periods=SAPMA_ASGARI_AY).mean()
    kay = q.rolling(SAPMA_KAYAN_AY, min_periods=SAPMA_KAYAN_AY).mean()
    G = aylik_gsyh_usd()
    out = {"sapma": q - gen, "sapma_kayan": q - kay, "sapma_tam_ornek": q - q.mean()}
    for ad, kalem in (("cari", "cari"), ("cekirdek", "hc_cekirdek")):
        B = oniki_toplam(kalem)
        oran = B / G * 100
        out[f"{ad}_oran"] = oran
        out[f"{ad}_ileri_sabit"] = (B.shift(-UFUK_AY) - B) / G * 100       # payda başlangıçta sabit
        out[f"{ad}_ileri_oran"] = oran.shift(-UFUK_AY) - oran
    df = pd.DataFrame(out)
    return df[df.index <= oo.CIPA_AY.to_timestamp()]


def _sapma_regresyonu(df: pd.DataFrame, yad: str, xad: str, oos: bool = True) -> dict:
    d = df[[yad, xad]].dropna()
    r = _reg(d[yad], d[xad], HAC_GECIKME)
    out = {"n": r["n"], "ilk": r["ilk"], "son": r["son"], "egim_puan_yuzde": r["b"][0], "se": r["se"][0],
           "t": r["t"][0], "r2": r["r2"], "gecikme": r["gecikme"], "sabit": r["sabit"],
           "on_yuzde_sapma_puan": 10 * r["b"][0]}
    if oos:
        o_s = _sozlesme_oos(d[yad], d[xad], OOS_ILK_AY, "ortalama")
        o_a = oos_ambargolu(d[yad], d[xad], OOS_ILK_AY, ambargo=UFUK_AY)
        out.update({"oos_sozlesme": o_s, "oos_ambargolu": o_a,
                    "hukum": hukum(r["t"][0], [o_s.get("mse_oran"), o_a.get("mse_oran")])})
    return out


def p8c() -> dict:
    df = _sapma_cerceve()
    son = df["sapma"].dropna().index.max()
    sonuc = {
        "yontem": ("Log reel efektif kurun o aya kadarki bütün geçmişin ortalamasından sapması (yüzde), sonraki "
                   "12 ayda 12 aylık cari dengenin dolar değişimine (değişimin başındaki 12 aylık dolar GSYH'ye "
                   "oranla, puan) regrese edildi; standart hata Newey–West (gecikme 24), örneklem dışı kıyas "
                   "koşulsuz ortalama, eğitim yalnız gerçekleşmiş hedeflerle."),
        "kaynak": ["redk_aylik (redk_tufe)", "odemeler_aylik (cari, hc_cekirdek)", "gsyh_ceyreklik",
                   "usdtry_tcmb_gunluk (dönüşüm kuru)"],
        "isaret": "Artı sapma ortalamaya göre pahalı TL'dir; eksi eğim pahalı liranın sonraki yıl cari dengeyi bozduğu demektir.",
        "sapma_son": {"tarih": _iso(son), "sapma_yuzde": float(df.loc[son, "sapma"]),
                      "sapma_kayan_yuzde": _f(df.loc[son, "sapma_kayan"])},
        "sapma_dagilimi": {"en_dusuk_yuzde": float(df["sapma"].min()), "en_dusuk_tarih": _iso(df["sapma"].idxmin()),
                           "en_yuksek_yuzde": float(df["sapma"].max()), "en_yuksek_tarih": _iso(df["sapma"].idxmax())},
    }
    for ad in ("cari", "cekirdek"):
        ana = _sapma_regresyonu(df, f"{ad}_ileri_sabit", "sapma")
        sonuc[ad] = {
            **ana,
            "oran_degisimi": _sapma_regresyonu(df, f"{ad}_ileri_oran", "sapma"),
            "kayan_10_yil_sapma": _sapma_regresyonu(df, f"{ad}_ileri_sabit", "sapma_kayan"),
            "alt_donem_2003": _sapma_regresyonu(df[df.index >= ALT_DONEM_BAS], f"{ad}_ileri_sabit", "sapma", oos=False),
            "ileriye_bakan_tam_ornek_ortalamasi": _sapma_regresyonu(df, f"{ad}_ileri_sabit", "sapma_tam_ornek", oos=False),
        }
    sonuc["cekirdek"]["tanim"] = "altın ve enerji hariç cari denge (TCMB tablosu)"
    sonuc["ileriye_bakan_notu"] = ("Tam örneklem ortalamasından sapma, o gün bilinmeyen gelecek gözlemleri kullanır; "
                                   "yalnız karşılaştırma için örneklem içi verilir.")
    return sonuc


def sekil_15() -> dict:
    df = _sapma_cerceve()
    d = df[["sapma", "cari_ileri_sabit", "cari_oran"]].dropna(subset=["sapma", "cari_oran"])
    return {"baslik": "REDK sapması ve sonraki 12 ayda cari denge değişimi",
            "tarih": [_iso(t) for t in d.index],
            "redk_sapma_yuzde": [float(v) for v in d["sapma"]],
            "cari_gsyh_yuzde": [float(v) for v in d["cari_oran"]],
            "sonraki_12ay_cari_degisim_puan": [_f(v) for v in d["cari_ileri_sabit"]],
            "ilk": _iso(d.index.min()), "son": _iso(d.index.max()),
            "not": "Sonraki 12 ayın değişimi son 12 ayda henüz gerçekleşmediği için boştur."}


# ───────────────────────────────────────────────────────── p8d
def _yahoo_degisim(kod: str) -> dict:
    if kod == "TRY":
        s, kun = oo.usdtry()
        kaynak = "Yahoo USD/TRY (düzeltilmiş günlük bar, Londra gece yarısı)"
    else:
        s = oo.em_kur(kod)
        kaynak = f"Yahoo USD/{kod} (düzeltilmiş günlük bar, Londra gece yarısı)"
    b, e = pd.Timestamp(TAPER["baz_yahoo"]), pd.Timestamp(TAPER["son"])
    if b not in s.index or e not in s.index:
        return kurulmadi(f"Yahoo USD/{kod} serisinde pencere uç günü yok")
    return {"baz_gun": _iso(b), "son_gun": _iso(e), "baz": float(s.loc[b]), "son": float(s.loc[e]),
            "degisim_log_yuzde": float(100 * math.log(s.loc[e] / s.loc[b])),
            "degisim_yuzde": float(100 * (s.loc[e] / s.loc[b] - 1)), "kaynak": kaynak}


def _ecb_degisim(kod: str) -> dict:
    try:
        x = bulut.ecb_kur(kod) / bulut.ecb_kur("USD")         # USD/XXX = (EUR/XXX)/(EUR/USD)
    except bulut.VeriYok as hata:
        return kurulmadi(str(hata))
    b, e = pd.Timestamp(TAPER["baz_ecb"]), pd.Timestamp(TAPER["son"])
    if b not in x.index or e not in x.index:
        return kurulmadi(f"ECB {kod} serisinde pencere uç günü yok")
    return {"baz_gun": _iso(b), "son_gun": _iso(e), "baz": float(x.loc[b]), "son": float(x.loc[e]),
            "degisim_log_yuzde": float(100 * math.log(x.loc[e] / x.loc[b])),
            "degisim_yuzde": float(100 * (x.loc[e] / x.loc[b] - 1)),
            "kaynak": f"ECB referans kuru çaprazı USD/{kod} (14:15 Orta Avrupa)"}


def p8d() -> dict:
    try:
        w = bulut.wdi("cari")
        wdi_hata = None
    except bulut.VeriYok as hata:
        w, wdi_hata = None, str(hata)
    satirlar = []
    for kod, iso3, ad in BESLI + KONTROL:
        if kod == "IDR":
            ana = _ecb_degisim("IDR")
            if ana.get("durum") is None:
                ana["kaynak"] = "ECB referans kuru çaprazı USD/IDR (14:15 Orta Avrupa; Yahoo serisi yok)"
        else:
            ana = _yahoo_degisim(kod)
        satir = {"para": kod, "ulke": ad, "grup": "kontrol" if (kod, iso3, ad) in KONTROL else "kırılgan beşli",
                 "kur": ana, "ecb_saglamlik": _ecb_degisim(kod),
                 "ana_kaynak_ecb": kod == "IDR"}
        if w is None:
            satir["cari_gsyh_2012"] = kurulmadi(wdi_hata)
        elif iso3 not in w.columns or pd.isna(w[iso3].get(pd.Timestamp("2012-12-31"))):
            satir["cari_gsyh_2012"] = kurulmadi("Dünya Bankası dosyasında 2012 değeri yok")
        else:
            satir["cari_gsyh_2012"] = {"deger_yuzde": float(w.loc[pd.Timestamp("2012-12-31"), iso3]),
                                       "kaynak": "Dünya Bankası WDI, cari denge (% GSYH)"}
        satirlar.append(satir)
    # Türkiye: TCMB gösterge kuru (15:30 TSİ ilanı; 22.05 ilanı ifadeden önce) ve kendi ölçümüm
    t = oo.usdtry_tcmb()
    b, e = pd.Timestamp(TAPER["baz_ecb"]), pd.Timestamp(TAPER["son"])
    tcmb = {"baz_gun": _iso(b), "son_gun": _iso(e),
            "degisim_log_yuzde": float(100 * math.log(t.loc[e] / t.loc[b])),
            "kaynak": "TCMB gösterge kuru (ilan günü; 15:30 TSİ)"} if (b in t.index and e in t.index) \
        else kurulmadi("TCMB kurunda uç gün yok")
    df = _sektorel()
    q = pd.Timestamp("2012-12-31")
    turkiye = {"tcmb_kuru_saglamlik": tcmb,
               "cari_gsyh_2012_olcum_usd_yuzde": float(df.loc[q, "dis_usd"]) if q in df.index else None,
               "cari_gsyh_2012_olcum_tl_yuzde": float(df.loc[q, "dis"]) if q in df.index else None}
    besli_deg = [s["kur"].get("degisim_log_yuzde") for s in satirlar if s["grup"] == "kırılgan beşli"]
    besli_deg = [v for v in besli_deg if v is not None]
    return {
        "yontem": ("22 Mayıs 2013 Bernanke ifadesinden önceki son kapanıştan 30 Ağustos 2013 kapanışına dolar "
                   "karşısında log kur değişimi (artı değer kaybı) ve 2012 cari denge/GSYH; bir vaka tablosudur, "
                   "istatistik sınaması yapılmaz."),
        "kaynak": ["em_kur_yahoo_gunluk (BRL, INR, ZAR, MXN)", "usdtry_yahoo_gunluk", "bulut: ECB referans kurları",
                   "bulut: Dünya Bankası WDI cari denge", "usdtry_tcmb_gunluk (sağlamlık)"],
        "vaka_tablosu": True, "test_degil": "n < 10: vaka tablosudur, t yazılmaz.",
        "olay": {"gun": TAPER["olay"], "saat": "10:00 New York (16:00 Orta Avrupa, 17:00 TSİ)",
                 "baz_yahoo": TAPER["baz_yahoo"], "baz_ecb": TAPER["baz_ecb"], "son": TAPER["son"]},
        "saat_notu": ("Yahoo kurları Londra gece yarısı kapanışıdır, baz olay öncesi 21.05; ECB 14:15 Orta Avrupa "
                      "sabitlemesidir, 22.05 sabitlemesi ifadeden öncedir. Yahoo serisinde cumartesi barı yok: 30.08 "
                      "cuma değeri pazartesi barının başından (hafta sonu açılışından sonra) gelir."),
        "n": len(satirlar), "ilk": TAPER["baz_yahoo"], "son": TAPER["son"],
        "satirlar": satirlar, "turkiye": turkiye,
        "besli_medyan_degisim_log_yuzde": float(np.median(besli_deg)) if besli_deg else None,
    }


# ───────────────────────────────────────────────────────── giriş
def olc() -> dict:
    out = {"p8a": p8a(), "p8b": p8b(), "p8c": p8c(), "p8d": p8d(),
           "sekil_13": sekil_13(), "sekil_14": sekil_14(), "sekil_15": sekil_15()}
    return oo.yuvarla(out, 4)


if __name__ == "__main__":
    import json
    import time
    t0 = time.monotonic()
    d = olc()
    print(json.dumps(d, ensure_ascii=False)[:4000])
    print(f"\n{time.monotonic() - t0:.1f} sn")
