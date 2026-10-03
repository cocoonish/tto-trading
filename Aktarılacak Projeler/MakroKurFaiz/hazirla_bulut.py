#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRO DERSİ — bulut ham arşivini (`veri/ham/`) ders girdisine çevirir (`veri/bulut/`).

Ham yanıtlar bulutta bir kez indirildi (arsiv_makro.py, arsiv_makro2.py); bu
betik yalnız YEREL dosya okur, ağa çıkmaz. Her çıktı deterministik csv.gz
(gzip mtime 0, sabit ondalık) ve `veri/bulut/kunye.json`da sıkıştırılmamış
metnin sha256'sını, ham kaynak dosyalarını (ham künyedeki özleriyle), kapsamı
ve sütun anlamlarını taşır. `ortak_olc.oku` aynı kapıdan okur.

Çıpa: günlük ≤ 30.09.2026, aylık ≤ 08.2026 (anket 09.2026'yı da taşır, o ay
KESİLİR), çeyreklik ≤ 2026Ç2. Ham dosyada ondan sonrası varsa kesilir ve
sayısı künyeye yazılır.

İÇ SINAMALAR (düşerse betik durur, çıktı yazılmaz):
· UYP: net = varlık − yükümlülük (her çeyrekte, 1 milyon USD toleransla).
· Kalan vade: toplam = kamu + TCMB + özel.
· Anket cari ay TÜFE beklentisi, depodaki `enflasyon_aylik.pka_ay_cari` ile
  örtüşen aylarda birebir (iki ayrı yoldan gelen aynı seri).
· ABD Hazinesi 2 ve 10 yıllık par getirileri, depodaki `abd_hazine_gunluk`
  ile örtüşen günlerde birebir.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BURASI = Path(__file__).resolve().parent
HAM = BURASI / "veri" / "ham"
CIKTI = BURASI / "veri" / "bulut"
CIPA_GUN = pd.Timestamp("2026-09-30")
CIPA_AY = pd.Timestamp("2026-08-01")
CIPA_CEYREK = pd.Timestamp("2026-06-30")
KUNYE: dict[str, dict] = {}
HAM_KUNYE = json.loads((HAM / "kunye_bulut.json").read_text(encoding="utf-8"))
AYLAR = {"ocak": 1, "şubat": 2, "mart": 3, "nisan": 4, "mayıs": 5, "haziran": 6, "temmuz": 7,
         "ağustos": 8, "eylül": 9, "ekim": 10, "kasım": 11, "aralık": 12}
EN_AY = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july",
                                     "august", "september", "october", "november", "december"], 1)}


def ham(yol: str) -> bytes:
    return gzip.decompress((HAM / yol).read_bytes())


def kaynak_listesi(yollar) -> list[dict]:
    out = []
    for y in sorted(yollar):
        k = HAM_KUNYE.get(y, {})
        out.append({"ham": y, "sha256": k.get("sha256"), "url": k.get("url"), "an": k.get("an")})
    return out


def yaz(df: pd.DataFrame, ad: str, aciklama: str, sutun_aciklama: dict, yollar, sinir: pd.Timestamp | None,
        ek: dict | None = None, ondalik: int = 6) -> None:
    df = df.sort_index()
    kesilen = 0
    if sinir is not None and isinstance(df.index, pd.DatetimeIndex):
        kesilen = int((df.index > sinir).sum())
        df = df[df.index <= sinir]
    df.index.name = "tarih"
    metin = df.to_csv(float_format=f"%.{ondalik}f", date_format="%Y-%m-%d", lineterminator="\n")
    ham_bayt = metin.encode("utf-8")
    CIKTI.mkdir(parents=True, exist_ok=True)
    with open(CIKTI / f"{ad}.csv.gz", "wb") as f:
        with gzip.GzipFile(fileobj=f, mode="wb", mtime=0) as g:
            g.write(ham_bayt)
    kapsam = {}
    for c in df.columns:
        s = df[c].dropna()
        if len(s):
            kapsam[c] = {"n": int(len(s)), "ilk": str(s.index.min().date()) if hasattr(s.index.min(), "date") else str(s.index.min()),
                         "son": str(s.index.max().date()) if hasattr(s.index.max(), "date") else str(s.index.max())}
    KUNYE[f"{ad}.csv.gz"] = {
        "hazirlayan": "hazirla_bulut.py", "sha256": hashlib.sha256(ham_bayt).hexdigest(),
        "satir": int(len(df)), "sutunlar": list(df.columns), "kesilen_satir": kesilen,
        "cipa_siniri": None if sinir is None else str(sinir.date()), "aciklama": aciklama,
        "sutun_aciklama": sutun_aciklama, "kapsam": kapsam, "kaynaklar": kaynak_listesi(yollar), **(ek or {}),
    }
    print(f"  · {ad}: {len(df)} satır, {len(df.columns)} sütun (kesilen {kesilen})", flush=True)


# ───────────────────────────────────────────────────────────── EVDS
def evds_grup(grup: str) -> tuple[pd.DataFrame, list[str]]:
    """Grubun indirilmiş demetlerini birleştirir; ikinci geçiş (seri2) varsa o kullanılır."""
    for alt in ("seri2", "seri"):
        yollar = sorted(str(p.relative_to(HAM)) for p in (HAM / "evds" / alt).glob(f"{grup}_*.json.gz"))
        if yollar:
            break
    else:
        return pd.DataFrame(), []
    parca = []
    for y in yollar:
        j = json.loads(ham(y))
        df = pd.DataFrame(j.get("items") or [])
        if df.empty:
            continue
        df = df.drop(columns=[c for c in ("UNIXTIME", "YEARWEEK") if c in df.columns])
        df["tarih"] = [evds_tarih(t) for t in df.pop("Tarih")]
        parca.append(df.set_index("tarih"))
    birlesik = pd.concat(parca, axis=1)
    birlesik = birlesik.loc[:, ~birlesik.columns.duplicated()]
    birlesik = birlesik.apply(pd.to_numeric, errors="coerce")
    birlesik.columns = [c.replace("_", ".") for c in birlesik.columns]
    return birlesik.sort_index(), yollar


def evds_tarih(t: str) -> pd.Timestamp:
    t = str(t)
    m = re.fullmatch(r"(\d{4})-(\d{1,2})", t)
    if m:
        return pd.Timestamp(int(m.group(1)), int(m.group(2)), 1)
    m = re.fullmatch(r"(\d{4})-Q(\d)", t)
    if m:
        return pd.Period(f"{m.group(1)}Q{m.group(2)}", "Q").to_timestamp("Q").normalize()
    m = re.fullmatch(r"(\d{2})-(\d{2})-(\d{4})", t)
    if m:
        return pd.Timestamp(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    raise ValueError(f"EVDS tarih biçimi tanınmadı: {t}")


def _kod(df: pd.DataFrame, kod: str) -> pd.Series:
    if kod not in df.columns:
        raise RuntimeError(f"EVDS: {kod} indirilen demetlerde yok (sütunlar: {list(df.columns)[:12]}…)")
    return df[kod]


def evds_pka() -> None:
    df, yollar = evds_grup("bie_pkauo")
    if df.empty:
        print("  ! anket grubu yok", flush=True)
        return
    p = "TP.PKAUO."
    enf = pd.DataFrame({
        "cari_ay": _kod(df, p + "S01.A.U"), "ay1": _kod(df, p + "S01.B.U"), "ay2": _kod(df, p + "S01.C.U"),
        "yilsonu": _kod(df, p + "S01.D.U"), "ay12": _kod(df, p + "S01.E.U"), "ay24": _kod(df, p + "S01.F.U"),
        "yil5": _kod(df, p + "S01.G.U"), "gelecek_yilsonu": _kod(df, p + "S01.I.U")})
    # İç sınama: depodaki anket serisiyle (Enflasyon hattı) birebir.
    import ortak_olc as oo
    depo = oo.oku("enflasyon_aylik")["pka_ay_cari"].dropna()
    ortak = enf["cari_ay"].dropna().index.intersection(depo.index)
    fark = (enf["cari_ay"].reindex(ortak) - depo.reindex(ortak)).abs()
    if len(ortak) < 100 or fark.max() > 0.005:
        raise RuntimeError(f"anket cari ay TÜFE beklentisi depodakiyle ayrışıyor: n={len(ortak)}, azami fark {fark.max()}")
    yaz(enf, "evds_pka_enflasyon", "Piyasa Katılımcıları Anketi, enflasyon beklentileri (uygun ortalamalar), %",
        {"cari_ay": "cari ayın aylık TÜFE beklentisi", "ay1": "1 ay sonrasının aylık TÜFE beklentisi",
         "ay2": "2 ay sonrasının aylık TÜFE beklentisi", "yilsonu": "cari yıl sonu yıllık TÜFE beklentisi",
         "ay12": "12 ay sonrasının yıllık TÜFE beklentisi", "ay24": "24 ay sonrasının yıllık TÜFE beklentisi",
         "yil5": "5 yıl sonrasının yıllık TÜFE beklentisi", "gelecek_yilsonu": "gelecek yıl sonu yıllık TÜFE beklentisi"},
        yollar, CIPA_AY, ek={"ic_sinama": {"depo_ile_ortak_ay": int(len(ortak)), "azami_fark": float(fark.max())},
                             "tarih_kurali": "anket ayı (ay başı); yayım günü EVDS'te yok"})
    ilk = _kod(df, p + "S04.C.U")
    cari = _kod(df, p + "S04.A.U")
    top = pd.DataFrame({
        "ilk_toplanti": ilk, "ikinci_toplanti": _kod(df, p + "S04.F.U"), "ucuncu_toplanti": _kod(df, p + "S04.G.U"),
        "cari_ay_sonu_repo": cari, "ay3_repo": _kod(df, p + "S04.B.U"), "yilsonu": _kod(df, p + "S04.H.U"),
        "faiz_12a": _kod(df, p + "S04.D.U"), "faiz_24a": _kod(df, p + "S04.E.U")})
    top["politika_beklenti"] = ilk.combine_first(cari)
    top["seri"] = np.where(ilk.notna(), "ilk_toplanti", np.where(cari.notna(), "cari_ay_sonu_repo", ""))
    top.loc[top["politika_beklenti"].isna(), "seri"] = ""
    yaz(top, "evds_pka_toplanti", "Piyasa Katılımcıları Anketi, politika faizi beklentileri (uygun ortalamalar), %",
        {"ilk_toplanti": "ilk toplantı için politika faizi beklentisi (2025-06'dan)",
         "cari_ay_sonu_repo": "cari ay sonu bir hafta vadeli repo faizi beklentisi (2025-05'e kadar)",
         "politika_beklenti": "ilk toplantı beklentisi, yoksa cari ay sonu repo beklentisi",
         "seri": "politika_beklenti hangi soru", "faiz_12a": "12 ay sonrası politika faizi beklentisi",
         "faiz_24a": "24 ay sonrası politika faizi beklentisi"}, yollar, CIPA_AY,
        ek={"tarih_kurali": "anket ayı (ay başı); anket ayın ilk yarısında toplanır, PPK genellikle ikinci yarıda"})
    kur = pd.DataFrame({"usdtry_cari_ay_sonu": _kod(df, p + "S05.A.U"), "usdtry_yilsonu": _kod(df, p + "S05.B.U"),
                        "usdtry_12a": _kod(df, p + "S05.C.U")})
    yaz(kur, "evds_pka_kur", "Piyasa Katılımcıları Anketi, USD/TRY beklentileri (bankalararası, uygun ortalamalar), TL",
        {"usdtry_cari_ay_sonu": "cari ay sonu", "usdtry_yilsonu": "cari yıl sonu", "usdtry_12a": "12 ay sonrası"},
        yollar, CIPA_AY, ek={"tarih_kurali": "anket ayı (ay başı)"})
    dig = pd.DataFrame({"gecelik_cari_ay_sonu": _kod(df, p + "S03.A.U"), "cari_denge_cari_yil": _kod(df, p + "S06.A.U"),
                        "cari_denge_gelecek_yil": _kod(df, p + "S06.B.U"), "buyume_cari_yil": _kod(df, p + "S07.A.U"),
                        "buyume_gelecek_yil": _kod(df, p + "S07.B.U")})
    yaz(dig, "evds_pka_diger", "Piyasa Katılımcıları Anketi, diğer beklentiler (uygun ortalamalar)",
        {"gecelik_cari_ay_sonu": "cari ay sonu BİST gecelik repo faizi beklentisi, %",
         "cari_denge_cari_yil": "cari yıl cari işlemler dengesi beklentisi, milyar USD",
         "cari_denge_gelecek_yil": "gelecek yıl cari işlemler dengesi beklentisi, milyar USD",
         "buyume_cari_yil": "cari yıl GSYH büyüme beklentisi, %", "buyume_gelecek_yil": "gelecek yıl GSYH büyüme beklentisi, %"},
        yollar, CIPA_AY)


def evds_uyp() -> None:
    df, yollar = evds_grup("bie_uypucay")
    if df.empty or "TP.UYPUCAY.K40" not in df.columns:
        print("  ! UYP yükümlülükleri indirilmemiş (ikinci geçiş gerekir)", flush=True)
        return
    p = "TP.UYPUCAY."
    u = pd.DataFrame({"net": _kod(df, p + "K1"), "varlik": _kod(df, p + "K2"), "yukumluluk": _kod(df, p + "K40"),
                      "rezerv": _kod(df, p + "K32"), "dy_varlik": _kod(df, p + "K3"), "dy_yuk": _kod(df, p + "K41"),
                      "portfoy_yuk": _kod(df, p + "K44"), "portfoy_borc_senedi_yuk": _kod(df, p + "K48"),
                      "diger_yatirim_yuk": _kod(df, p + "K58")}).dropna(how="all")
    fark = (u["net"] - (u["varlik"] - u["yukumluluk"])).abs().dropna()
    if fark.max() > 1.0:
        raise RuntimeError(f"UYP: net ≠ varlık − yükümlülük (azami {fark.max()})")
    yaz(u, "evds_uyp", "Uluslararası yatırım pozisyonu, çeyrek sonu stok, milyon USD (TCMB)",
        {"net": "net UYP", "varlik": "varlıklar", "yukumluluk": "yükümlülükler", "rezerv": "rezerv varlıklar",
         "dy_varlik": "doğrudan yatırım varlıkları", "dy_yuk": "doğrudan yatırım yükümlülükleri",
         "portfoy_yuk": "portföy yükümlülükleri", "portfoy_borc_senedi_yuk": "portföy borç senedi yükümlülükleri",
         "diger_yatirim_yuk": "diğer yatırım yükümlülükleri"}, yollar, CIPA_CEYREK,
        ek={"ic_sinama": {"net_ozdesligi_azami_fark": float(fark.max())}, "tarih_kurali": "çeyrek sonu"})


def evds_kalan_vade() -> None:
    df, yollar = evds_grup("bie_kalvadbg")
    if df.empty:
        print("  ! kalan vade indirilmemiş (ikinci geçiş gerekir)", flush=True)
        return
    p = "TP.KALVADBG."
    k = pd.DataFrame({"kv_borc_mn_usd": _kod(df, p + "K18"), "kamu": _kod(df, p + "K1"),
                      "tcmb": _kod(df, p + "K12"), "ozel": _kod(df, p + "K13")}).dropna(how="all")
    fark = (k["kv_borc_mn_usd"] - k[["kamu", "tcmb", "ozel"]].sum(axis=1, min_count=3)).abs().dropna()
    if len(fark) and fark.max() > 2.0:
        raise RuntimeError(f"kalan vade: toplam ≠ kamu + TCMB + özel (azami {fark.max()})")
    ek = {"ic_sinama": {"toplam_ozdesligi_azami_fark": float(fark.max()) if len(fark) else None}, "tarih_kurali": "ay başı (ay sonu stoku)"}
    df2, y2 = evds_grup("bie_kalanvade")
    if not df2.empty and "TP.KALANVADE.K20" in df2.columns:
        k["kv_borc_alacakli_toplam"] = df2["TP.KALANVADE.K20"]
        f2 = (k["kv_borc_mn_usd"] - k["kv_borc_alacakli_toplam"]).abs().dropna()
        ek["ic_sinama"]["iki_kirilim_azami_fark"] = float(f2.max()) if len(f2) else None
        yollar = yollar + y2
    yaz(k, "evds_kalan_vade", "Kalan vadeye göre kısa vadeli dış borç stoku (borçlu bazında), milyon USD",
        {"kv_borc_mn_usd": "toplam", "kamu": "kamu", "tcmb": "TCMB", "ozel": "özel kesim",
         "kv_borc_alacakli_toplam": "aynı stok, alacaklı/araç kırılımının toplamı"}, yollar, CIPA_AY, ek=ek)


def evds_dis_ticaret() -> None:
    sutun = {}
    yollar = []
    for grup, kod, ad in (("bie_dtihfb10", "TP.DT.IH.FIY.D01.2010", "ihr_birim_deger"),
                          ("bie_dtitfb10", "TP.DT.IT.FIY.D01.2010", "ith_birim_deger"),
                          ("bie_dtitfb10", "TP.DT.IT.FIY.D07.2010", "ith_yakit_birim_deger"),
                          ("bie_dtihmb10", "TP.DT.IH.MIK.D01.2010", "ihr_miktar"),
                          ("bie_dtitmb10", "TP.DT.IT.MIK.D01.2010", "ith_miktar"),
                          ("bie_dtitmb10", "TP.DT.IT.MIK.D07.2010", "ith_yakit_miktar")):
        df, y = evds_grup(grup)
        if df.empty or kod not in df.columns:
            print(f"  ! dış ticaret: {kod} yok", flush=True)
            return
        sutun[ad] = df[kod]
        yollar += y
    yaz(pd.DataFrame(sutun).dropna(how="all"), "evds_dis_ticaret_endeks",
        "Dış ticaret birim değer ve miktar endeksleri, 2010=100 (TÜİK, EVDS)",
        {"ihr_birim_deger": "ihracat birim değer", "ith_birim_deger": "ithalat birim değer",
         "ith_yakit_birim_deger": "ithalat, işlem görmemiş yakıt ve yağlar, birim değer",
         "ihr_miktar": "ihracat miktar", "ith_miktar": "ithalat miktar",
         "ith_yakit_miktar": "ithalat, işlem görmemiş yakıt ve yağlar, miktar"}, sorted(set(yollar)), CIPA_AY)


# ───────────────────────────────────────────────────────────── takvimler
def tuik_takvim() -> None:
    satir, yollar = [], []
    for p in sorted((HAM / "tuik").glob("takvim_*.json.gz")):
        y = str(p.relative_to(HAM))
        yollar.append(y)
        j = json.loads(ham(y))
        for x in j.get("yayindaOlanlarList") or []:
            if x.get("sorumluKisaAd") != "TÜİK":
                continue
            adi = (x.get("adi") or "").strip()
            donem = (x.get("donemi") or "").strip()
            if "Tüketici Fiyat" in adi:
                bulten = "tufe"
            elif adi in ("Dönemsel Gayrisafi Yurt İçi Hasıla", "Gayrisafi Yurt İçi Hasıla") and "eyrek" in donem:
                bulten = "gsyh"
            else:
                continue
            t = pd.Timestamp(x["gTarih"])
            satir.append({"tarih": t.normalize(), "bulten": bulten, "donem": donem, "saat": t.strftime("%H:%M"),
                          "ad": adi, "kimlik": x.get("id")})
    df = pd.DataFrame(satir).drop_duplicates(subset=["tarih", "bulten", "donem"]).set_index("tarih")
    cift = df.reset_index().duplicated(subset=["tarih", "bulten"]).sum()
    yaz(df, "tuik_takvim", "TÜİK ulusal veri yayımlama takvimi: TÜFE ve çeyreklik GSYH bültenlerinin yayım günleri",
        {"bulten": "tufe · gsyh", "donem": "bültenin kapsadığı dönem (TÜİK yazımı)",
         "saat": "takvimdeki saat (eski kayıtlarda 17:00 yer tutucusu görülür; gün esastır)", "ad": "bülten adı"},
        yollar, CIPA_GUN, ek={"ayni_gun_cift": int(cift)})


def fomc_takvim() -> None:
    satir, yollar = [], []
    y = "fomc/fomccalendars.htm.gz"
    t = ham(y).decode("utf-8", "replace")
    yollar.append(y)
    for m in sorted(set(re.findall(r"pressreleases/monetary(\d{8})a\.htm", t))):
        satir.append({"tarih": pd.Timestamp(m), "planli": True, "kaynak": "takvim (bildiri bağlantısı)"})
    for p in sorted((HAM / "fomc").glob("fomchistorical*.htm.gz")):
        y = str(p.relative_to(HAM))
        yollar.append(y)
        h = ham(y).decode("utf-8", "replace")
        for baslik in re.findall(r"<h5[^>]*>([^<]+)</h5>", h):
            m = re.match(r"\s*([A-Za-z]+)(?:/([A-Za-z]+))?\s+(\d{1,2})(?:-(\d{1,2}))?\s*(?:\(unscheduled\)|Meeting)?.*?(\d{4})", baslik)
            if not m:
                continue
            ay1, ay2, g1, g2, yil = m.groups()
            ay = (ay2 or ay1).lower()
            gun = int(g2 or g1)
            if ay not in EN_AY:
                continue
            planli = "unscheduled" not in baslik.lower() and "conference call" not in baslik.lower()
            satir.append({"tarih": pd.Timestamp(int(yil), EN_AY[ay], gun), "planli": planli, "kaynak": "tarihî sayfa"})
    df = pd.DataFrame(satir).sort_values(["tarih", "kaynak"]).drop_duplicates(subset=["tarih"], keep="last").set_index("tarih")
    yaz(df, "fomc_takvim", "FOMC toplantıları: karar günü (toplantının son günü)",
        {"planli": "planlı toplantı (plansız toplantı ve telekonferans hayır)", "kaynak": "hangi sayfadan"},
        yollar, CIPA_GUN)


def bls_takvim() -> None:
    satir, yollar = [], []
    for ad in ("empsit", "cpi"):
        aday = sorted((HAM / "bls").glob(f"{ad}_wayback_*.htm.gz"))
        if not aday:
            print(f"  ! BLS {ad}: arşiv kopyası yok", flush=True)
            continue
        y = str(aday[0].relative_to(HAM))
        yollar.append(y)
        t = ham(y).decode("utf-8", "replace")
        for m in sorted(set(re.findall(r"archives/" + ad + r"_(\d{2})(\d{2})(\d{4})\.htm", t))):
            satir.append({"tarih": pd.Timestamp(int(m[2]), int(m[0]), int(m[1])), "bulten": ad})
    if not satir:
        return
    df = pd.DataFrame(satir).drop_duplicates().set_index("tarih")
    yaz(df, "bls_takvim", "BLS yayım günleri (Employment Situation · CPI), arşiv sayfasındaki bağlantı adlarından",
        {"bulten": "empsit · cpi"}, yollar, CIPA_GUN,
        ek={"not": "Sayfa Internet Archive kopyasından okundu; yalnız tarih listesi için"})


# ───────────────────────────────────────────────────────────── uluslararası
def bis() -> None:
    for dosya, ad, aciklama in (("bis/WS_EER_MRB.csv.gz", "bis_eer_r", "BIS geniş reel efektif kur (64 ekonomi), 2020=100"),
                                ("bis/WS_EER_MNB.csv.gz", "bis_eer_n", "BIS geniş nominal efektif kur (64 ekonomi), 2020=100"),
                                ("bis/WS_CBPOL_M.csv.gz", "bis_politika", "BIS politika faizleri, aylık, %")):
        df = pd.read_csv(io.BytesIO(ham(dosya)), low_memory=False)
        df["tarih"] = pd.to_datetime(df["TIME_PERIOD"].astype(str) + "-01")
        p = df.pivot_table(index="tarih", columns="REF_AREA", values="OBS_VALUE", aggfunc="last")
        p.columns = [str(c) for c in p.columns]
        yaz(p, ad, aciklama + "; artış yerel paranın değer kazancı" if "eer" in ad else aciklama,
            {c: "ISO2 ülke kodu (XM euro alanı)" for c in p.columns[:1]}, [dosya], CIPA_AY,
            ek={"tarih_kurali": "ay başı etiket (BIS ayı)"})


def ecb() -> None:
    sutun, yollar = {}, []
    for p in sorted((HAM / "ecb").glob("exr_*.csv.gz")):
        y = str(p.relative_to(HAM))
        df = pd.read_csv(io.BytesIO(ham(y)), low_memory=False)
        kod = y.split("_")[1].split(".")[0].lower()
        s = pd.Series(pd.to_numeric(df["OBS_VALUE"], errors="coerce").values, index=pd.to_datetime(df["TIME_PERIOD"]))
        sutun[kod] = s.dropna()
        yollar.append(y)
    yaz(pd.DataFrame(sutun), "ecb_kur", "ECB euro referans kurları (14:15 CET), 1 euro = x birim",
        {k: f"1 EUR = x {k.upper()}" for k in sutun}, yollar, CIPA_GUN)


def eurostat() -> None:
    def jsonstat(y: str) -> pd.DataFrame:
        e = json.loads(ham(y))
        ids, size = e["id"], e["size"]
        kat = {d: {v: k for k, v in e["dimension"][d]["category"]["index"].items()} for d in ids}
        kayit = []
        for flat, val in e["value"].items():
            i = int(flat)
            koord = {}
            for d, s in zip(reversed(ids), reversed(size)):
                koord[d] = kat[d][i % s]
                i //= s
            kayit.append({**koord, "deger": val})
        return pd.DataFrame(kayit)
    y = "eurostat/gov_10dd_edpt1.json.gz"
    d = jsonstat(y)
    d["tarih"] = pd.to_datetime(d["time"].astype(str) + "-12-31")
    d["ad"] = d["na_item"].map({"GD": "borc", "B9": "denge"}) + "_" + d["geo"]
    p = d.pivot_table(index="tarih", columns="ad", values="deger", aggfunc="last")
    yaz(p, "eurostat_borc", "Eurostat genel yönetim brüt borcu ve dengesi, % GSYH, yıllık",
        {"borc_XX": "genel yönetim brüt (Maastricht) borcu", "denge_XX": "genel yönetim net borç verme/alma"},
        [y], pd.Timestamp("2025-12-31"))
    y2 = "eurostat/gov_10q_ggdebt.json.gz"
    q = jsonstat(y2)
    q["tarih"] = pd.PeriodIndex(q["time"].str.replace("-", ""), freq="Q").to_timestamp("Q").normalize()
    pq = q.pivot_table(index="tarih", columns="geo", values="deger", aggfunc="last")
    yaz(pq, "eurostat_borc_ceyrek", "Eurostat genel yönetim brüt borcu, % GSYH, çeyreklik",
        {"XX": "genel yönetim brüt borcu"}, [y2], CIPA_CEYREK)


def wdi() -> None:
    for gost, ad, aciklama in (("BN.CAB.XOKA.GD.ZS", "wdi_cari", "cari denge, % GSYH"),
                               ("GC.DOD.TOTL.GD.ZS", "wdi_borc", "merkezi yönetim borcu, % GSYH"),
                               ("NY.GDP.MKTP.KD.ZG", "wdi_buyume", "reel GSYH büyümesi, %"),
                               ("FP.CPI.TOTL.ZG", "wdi_enflasyon", "TÜFE enflasyonu, yıllık %")):
        y = f"wdi/{gost}.json.gz"
        j = json.loads(ham(y))
        rows = [{"tarih": pd.Timestamp(int(r["date"]), 12, 31), "ulke": r["countryiso3code"], "deger": r["value"]}
                for r in (j[1] if len(j) > 1 and j[1] else []) if r.get("value") is not None]
        p = pd.DataFrame(rows).pivot_table(index="tarih", columns="ulke", values="deger", aggfunc="last")
        yaz(p, ad, f"Dünya Bankası WDI ({gost}): {aciklama}, yıllık", {"XXX": "ISO3 ülke kodu"}, [y], pd.Timestamp("2025-12-31"))


def hazine() -> None:
    parca, yollar = [], []
    for p in sorted((HAM / "hazine").glob("par_*.csv.gz")):
        y = str(p.relative_to(HAM))
        df = pd.read_csv(io.BytesIO(ham(y)))
        if "Date" not in df.columns or df.empty:
            continue
        df["tarih"] = pd.to_datetime(df["Date"], format="%m/%d/%Y")
        parca.append(df.set_index("tarih"))
        yollar.append(y)
    df = pd.concat(parca).sort_index()
    df = df[~df.index.duplicated(keep="last")]
    out = pd.DataFrame({"us3m": pd.to_numeric(df.get("3 Mo"), errors="coerce"),
                        "us1y": pd.to_numeric(df.get("1 Yr"), errors="coerce"),
                        "us2y": pd.to_numeric(df.get("2 Yr"), errors="coerce"),
                        "us5y": pd.to_numeric(df.get("5 Yr"), errors="coerce"),
                        "us10y": pd.to_numeric(df.get("10 Yr"), errors="coerce"),
                        "us30y": pd.to_numeric(df.get("30 Yr"), errors="coerce")})
    import ortak_olc as oo
    depo = oo.oku("abd_hazine_gunluk")
    ortak = out.index.intersection(depo.index)
    f2 = (out["us2y"].reindex(ortak) - depo["us2"].reindex(ortak)).abs().dropna()
    f10 = (out["us10y"].reindex(ortak) - depo["us10"].reindex(ortak)).abs().dropna()
    if len(ortak) < 1000 or f2.max() > 0.005 or f10.max() > 0.005:
        raise RuntimeError(f"ABD Hazinesi par getirileri depodakiyle ayrışıyor: n={len(ortak)}, 2y {f2.max()}, 10y {f10.max()}")
    yaz(out, "abd_hazine_1y", "ABD Hazinesi günlük par getiri eğrisi (NY kapanışı), %",
        {"us3m": "3 ay", "us1y": "1 yıl", "us2y": "2 yıl", "us5y": "5 yıl", "us10y": "10 yıl", "us30y": "30 yıl"},
        yollar, CIPA_GUN, ek={"ic_sinama": {"depo_ortak_gun": int(len(ortak)), "azami_fark_2y": float(f2.max()),
                                            "azami_fark_10y": float(f10.max())}})


def acm() -> None:
    import xlrd
    y = "acm/ACMTermPremium.xls.gz"
    kitap = xlrd.open_workbook(file_contents=ham(y))
    adlar = [s.name for s in kitap.sheets()]
    if "ACM Daily" not in adlar:
        raise RuntimeError(f"ACM: günlük sayfa bulunamadı ({adlar})")
    sayfa = kitap.sheet_by_name("ACM Daily")
    bas = [str(c.value).strip() for c in sayfa.row(0)]
    rows = [sayfa.row_values(i) for i in range(1, sayfa.nrows)]
    df = pd.DataFrame(rows, columns=bas)
    tarih_sut = bas[0]
    t = df[tarih_sut].tolist()
    if all(isinstance(v, (int, float)) for v in t):
        df["tarih"] = [pd.Timestamp(xlrd.xldate_as_datetime(v, kitap.datemode)) for v in t]
    else:
        df["tarih"] = pd.to_datetime(pd.Series(t, dtype=str), format="%d-%b-%Y", errors="coerce").values
    df = df.dropna(subset=["tarih"]).set_index("tarih")
    istenen = {"ACMTP02": "acmtp02", "ACMTP05": "acmtp05", "ACMTP10": "acmtp10", "ACMY10": "acmy10",
               "ACMRNY10": "acmrny10", "ACMY02": "acmy02"}
    out = pd.DataFrame({v: pd.to_numeric(df[k], errors="coerce") for k, v in istenen.items() if k in df.columns})
    yaz(out, "acm", f"NY Fed Adrian–Crump–Moench vade primi ve getirileri, günlük, % (sayfa: {sayfa.name})",
        {"acmtp10": "10 yıllık vade primi", "acmy10": "10 yıllık model getirisi", "acmrny10": "10 yıllık risk-nötr getiri",
         "acmtp02": "2 yıllık vade primi", "acmtp05": "5 yıllık vade primi", "acmy02": "2 yıllık model getirisi"},
        [y], CIPA_GUN, ek={"sayfa_basliklari": bas[:8]})


def _cnbc(desen: str) -> tuple[pd.Series, list[str]]:
    parca, yollar = [], []
    for p in sorted((HAM / "cnbc").glob(desen)):
        y = str(p.relative_to(HAM))
        j = json.loads(ham(y))
        bars = (j.get("barData") or {}).get("priceBars") or []
        s = pd.Series({pd.Timestamp(b["tradeTime"][:8]): float(b["close"]) for b in bars if b.get("close")})
        if len(s):
            parca.append(s)
            yollar.append(y)
    s = pd.concat(parca).sort_index()
    s = s[~s.index.duplicated(keep="last")]
    return s[s.index.dayofweek < 5], yollar        # hafta sonu barları kaynakta cumanın kopyası


def gilt() -> None:
    sutun, yollar = {}, []
    for desen, ad in (("GB2Y_GB_*.json.gz", "gb2y"), ("GB10Y_GB_*.json.gz", "gb10y"), ("GB30Y_GB_*.json.gz", "gb30y")):
        s, y = _cnbc(desen)
        sutun[ad] = s
        yollar += y
    y = "boe/iadb_par.csv.gz"
    b = pd.read_csv(io.BytesIO(ham(y)))
    b["tarih"] = pd.to_datetime(b["DATE"], format="%d %b %Y")
    b = b.set_index("tarih")
    for k, ad in (("IUDSNPY", "boe_5y_par"), ("IUDMNPY", "boe_10y_par"), ("IUDLNPY", "boe_20y_par")):
        sutun[ad] = pd.to_numeric(b[k], errors="coerce")
    yollar.append(y)
    df = pd.DataFrame(sutun)
    ortak = df[["gb10y", "boe_10y_par"]].dropna()
    yaz(df, "gilt", "İngiltere devlet tahvili getirileri, günlük, %",
        {"gb2y": "2 yıllık gösterge (CNBC, Londra kapanış barı)", "gb10y": "10 yıllık gösterge (CNBC)",
         "gb30y": "30 yıllık gösterge (CNBC)", "boe_5y_par": "BoE 5 yıllık nominal par getiri (kestirilmiş eğri)",
         "boe_10y_par": "BoE 10 yıllık nominal par getiri", "boe_20y_par": "BoE 20 yıllık nominal par getiri"},
        yollar, CIPA_GUN, ek={"ic_sinama": {"gb10y_boe10y_medyan_fark": float((ortak["gb10y"] - ortak["boe_10y_par"]).median()) if len(ortak) else None,
                                            "ortak_gun": int(len(ortak))}})


SURUCU_ACIKLAMA = {
    "brent": "Brent ham petrol, yakın vade vadeli, $/varil (ICE)", "wti": "WTI ham petrol, yakın vade vadeli, $/varil (NYMEX)",
    "bakir": "bakır, yakın vade vadeli, $/libre (COMEX)", "altin": "altın, yakın vade vadeli, $/ons (COMEX)",
    "gumus": "gümüş, yakın vade vadeli, $/ons", "platin": "platin, yakın vade vadeli, $/ons",
    "dogalgaz": "doğal gaz, yakın vade vadeli, $/MMBtu (NYMEX)", "soya": "soya fasulyesi, yakın vade vadeli, sent/bu (CBOT)",
    "demir_cevheri": "demir cevheri vadelisi",
    "jp2y": "Japonya 2 yıllık devlet tahvili getirisi, %", "jp10y": "Japonya 10 yıllık, %",
    "au2y": "Avustralya 2 yıllık, %", "au10y": "Avustralya 10 yıllık, %", "ca2y": "Kanada 2 yıllık, %",
    "ca10y": "Kanada 10 yıllık, %", "ch2y": "İsviçre 2 yıllık, %", "ch10y": "İsviçre 10 yıllık, %",
    "nz2y": "Yeni Zelanda 2 yıllık, %", "nz10y": "Yeni Zelanda 10 yıllık, %", "no10y": "Norveç 10 yıllık, %",
    "us2y": "ABD 2 yıllık (CNBC), %", "us10y": "ABD 10 yıllık (CNBC), %", "de2y": "Almanya 2 yıllık (CNBC), %",
    "gb2y": "İngiltere 2 yıllık (CNBC), %",
    "nzd": "NZD/USD", "nok": "USD/NOK", "sek": "USD/SEK", "clp": "USD/CLP", "cop": "USD/COP", "cnh": "USD/CNH",
    "krw": "USD/KRW", "zar": "USD/ZAR", "brl": "USD/BRL", "mxn": "USD/MXN", "try": "USD/TRY (CNBC, New York 17:00; ders USD/TRY'yi Yahoo'dan okur, bu yalnız kıyas)",
    "jpy": "USD/JPY", "eur": "EUR/USD", "aud": "AUD/USD", "cad": "USD/CAD", "gbp": "GBP/USD", "chf": "USD/CHF",
    "spx": "S&P 500 endeksi", "nikkei": "Nikkei 225 endeksi",
}


def surucu() -> None:
    """Kur sürücüleri (arsiv_makro4): CNBC günlük barları, araç başına seçilen sembol. Tarih barın
    işlem günüdür (döviz New York 17:00, vadeli borsa seansı, getiri kendi piyasası). Hafta sonu
    barı atılır (kaynakta cumanın kopyası)."""
    import ortak_olc as oo
    sutun, yollar, sembol = {}, [], {}
    for p in sorted((HAM / "cnbc_surucu").glob("*.json.gz")):
        arac = p.name.split("__")[0]
        y = str(p.relative_to(HAM))
        j = json.loads(ham(y))
        bars = (j.get("barData") or {}).get("priceBars") or []
        s = pd.Series({pd.Timestamp(b["tradeTime"][:8]): float(b["close"]) for b in bars if b.get("close")})
        if not len(s):
            continue
        sutun.setdefault(arac, []).append(s)
        yollar.append(y)
        sembol[arac] = HAM_KUNYE.get(y, {}).get("not", "").split(" · ")[-1]
    if not sutun:
        print("  ! sürücü barı yok", flush=True)
        return
    seri = {}
    for a, parca in sutun.items():
        x = pd.concat(parca).sort_index()
        x = x[~x.index.duplicated(keep="last")]
        seri[a] = x[x.index.dayofweek < 5]
    df = pd.DataFrame(seri)
    # iç sınama: CNBC G10 kurları depodaki New York 17:00 serisiyle (aynı kaynak) örtüşen günlerde
    depo = oo.oku("cnbc_kur_gunluk")
    sinama = {}
    for a in ("eur", "gbp", "aud", "jpy", "cad", "chf"):
        if a in df and a in depo:
            o = pd.concat([df[a], depo[a]], axis=1, keys=["yeni", "depo"]).dropna()
            if len(o):
                f = (np.log(o["yeni"] / o["depo"]).abs() * 1e4)
                sinama[a] = {"ortak_gun": int(len(o)), "medyan_fark_bp": round(float(f.median()), 3),
                             "p99_fark_bp": round(float(f.quantile(0.99)), 3)}
    yaz(df, "surucu_gunluk", "Kur sürücüleri: emtia vadelileri, devlet tahvili getirileri, paralar ve hisse endeksleri, günlük kapanış barı (CNBC)",
        {a: SURUCU_ACIKLAMA.get(a, a) for a in df.columns}, yollar, CIPA_GUN,
        ek={"sembol": sembol, "ic_sinama_g10_depo": sinama,
            "not": ("Yakın vade vadeli serisi vade devrinde bir kez sıçrar (devir arındırılmamış); değişim ölçüsü "
                    "bunu adıyla ele alır. Döviz barı New York 17:00, vadeli barı borsa seansı, getiri barı kendi "
                    "piyasasının kapanışıdır: aynı takvim günü farklı saatleri taşır.")})


def abd_reel() -> None:
    """ABD Hazinesi günlük reel getiri eğrisi (TIPS, par), %."""
    parca, yollar = [], []
    for p in sorted((HAM / "hazine").glob("reel_*.csv.gz")):
        y = str(p.relative_to(HAM))
        df = pd.read_csv(io.BytesIO(ham(y)))
        if "Date" not in df.columns or df.empty:
            continue
        df["tarih"] = pd.to_datetime(df["Date"], format="%m/%d/%Y")
        parca.append(df.set_index("tarih"))
        yollar.append(y)
    if not parca:
        print("  ! reel getiri dosyası yok", flush=True)
        return
    df = pd.concat(parca).sort_index()
    df = df[~df.index.duplicated(keep="last")]
    out = pd.DataFrame({ad: pd.to_numeric(df.get(k), errors="coerce")
                        for k, ad in (("5 YR", "reel5y"), ("7 YR", "reel7y"), ("10 YR", "reel10y"),
                                      ("20 YR", "reel20y"), ("30 YR", "reel30y"))})
    yaz(out.dropna(how="all"), "abd_reel_getiri", "ABD Hazinesi günlük reel getiri eğrisi (TIPS, par), %",
        {"reel5y": "5 yıl", "reel7y": "7 yıl", "reel10y": "10 yıl", "reel20y": "20 yıl", "reel30y": "30 yıl"},
        yollar, CIPA_GUN)


def not_kararlari() -> None:
    """Türkiye yabancı para kredi notu kararları. Kaynak ham arşiv değil, `veri/not_kararlari.json`:
    her karar `veri/kaynaklar.json`daki bir doğrulama kaydına (haber arşivi adresiyle) bağlı ve elle
    derlendi; ilan günü ve saati İSTANBUL saatiyle haberin ilk arşiv damgasından. Günü kaynakta
    yazmayan kararlar `gun_dayanagi` (takvim · cikarim) ve ilk haberin damgasıyla (`ilk_iz`) işaretli."""
    yol = BURASI / "veri" / "not_kararlari.json"
    j = json.loads(yol.read_text(encoding="utf-8"))
    df = pd.DataFrame([{"tarih": pd.Timestamp(k["ilan_gunu"]), "kurum": k["kurum"], "eylem": k["tur"],
                        "yon": int(k["yon"]), "ilan_saati": k["ilan_saati"] or "", "ilan_dilimi": k.get("ilan_dilimi") or "",
                        "gun_dayanagi": k["gun_dayanagi"], "ilk_iz": k.get("ilk_iz") or "",
                        "durum": k["durum"],
                        "anahtar": k["anahtar"]} for k in j["kararlar"]]).set_index("tarih")
    yaz(df, "not_kararlari", "Türkiye yabancı para kredi notu kararları (not, görünüm, inceleme), 2012–2024",
        {"kurum": "derecelendirme kuruluşu", "eylem": "not · gorunum · inceleme", "yon": "+1 iyileşme, −1 bozulma",
         "ilan_saati": "İstanbul saatiyle ilk arşiv damgası (boşsa bilinmiyor)",
         "ilan_dilimi": "aksam: saat yok ama kaynak ilanın İstanbul akşamında (18:00 sonrası) olduğunu yazıyor; "
                        "gun_dayanagi 'cikarim' olan kararda akşam dilimi de çıkarımdır",
         "gun_dayanagi": "kaynak: ilan günü kaynakta (ya da kaynağın damgasında) · takvim: kaynak yalnız ertesi "
                         "sabahın haberini veriyor, gün kurumun önceden ilan ettiği takvimden · cikarim: kaynak yalnız "
                         "ertesi günün haberini veriyor, gün ondan çıkarıldı",
         "ilk_iz": "günü kaynakta yazmayan kararda kaynaktaki ilk haberin İstanbul damgası (boşsa gün kaynakta)",
         "durum": "dogrulandi (haber ajansı, gazete ya da televizyon haberi tarihi ve önceki→yeni notu birlikte "
                  "veriyor) · kismen (yalnız ikincil kaynak ya da kaynak karması)",
         "anahtar": "veri/kaynaklar.json doğrulama kaydı"},
        [], CIPA_GUN, ek={"kaynak_dosya": {"yol": "veri/not_kararlari.json",
                                           "sha256": hashlib.sha256(yol.read_bytes()).hexdigest()}})


ADIMLAR = ("evds_pka", "evds_uyp", "evds_kalan_vade", "evds_dis_ticaret", "tuik_takvim", "fomc_takvim", "bls_takvim",
           "bis", "ecb", "eurostat", "wdi", "hazine", "acm", "gilt", "not_kararlari", "surucu", "abd_reel")


def main(argv: list[str] | None = None) -> int:
    """Argümansız: bütün adımlar. Adım adıyla: yalnız o adımlar; künyenin öbür kayıtları korunur."""
    sys.path.insert(0, str(BURASI))
    argv = argv or []
    secili = argv or list(ADIMLAR)
    bilinmeyen = [a for a in secili if a not in ADIMLAR]
    if bilinmeyen:
        raise SystemExit(f"bilinmeyen adım: {bilinmeyen}")
    kp = CIKTI / "kunye.json"
    if argv and kp.exists():
        KUNYE.update(json.loads(kp.read_text(encoding="utf-8"))["dosyalar"])
    for ad in secili:
        print(f"── {ad}", flush=True)
        globals()[ad]()
    kunye = {"hazirla": {"betik": "hazirla_bulut.py", "cipa": {"gunluk": str(CIPA_GUN.date()), "aylik": "2026-08",
                                                               "ceyreklik": "2026Q2"},
                         "not": "Ham arşivden yerel ayrıştırma; ağa çıkılmaz. sha256 sıkıştırılmamış CSV metninin özüdür."},
             "dosyalar": dict(sorted(KUNYE.items()))}
    kp.write_text(json.dumps(kunye, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"── {len(KUNYE)} dosya yazıldı")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
