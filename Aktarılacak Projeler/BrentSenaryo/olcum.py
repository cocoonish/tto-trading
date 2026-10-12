#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BRENT 125–150 SENARYOSU — yazının BÜTÜN sayılarını üreten tek ölçüm katmanı.

Girdi yalnız `veri/*.csv.gz` (`hazirla.py`'nin dondurduğu arşiv; her dosyanın
sha256'sı okunurken yeniden hesaplanır). Çıktı `veri/olcum.json`: `sekil.py`
figürleri, `dogrula.py` yayımlanan metni buna karşı sınar. İki ayrı hesap bir
gün sessizce ayrışır; sayıyı üreten yer tektir.

SORU. "Brent bir ay içinde 125–150 dolara çıkarsa ne olur" bir öngörü değil
KOŞULLU bir sorudur: Brent'in o hareketi yaptığı bilindiğinde öbür varlıklar
geçmişte ne yaptı? Cevap üç ayaktan kurulur ve üçü ayrı ayrı yayımlanır:

  1. 2026 REJİMİ — bu savaşın kendi dört büyük petrol yükselişi (Mart, Mayıs,
     Temmuz, Eylül 2026). 21 iş günlük pencereler; Brent'in YÜKSELDİĞİ
     pencerelerde ayrı eğim (ölçüldü: tepki asimetrik).
  2. EMSALLER — anlatıyla belgelenmiş arz olayları (1990 Körfez, 2002
     Venezuela, 2003 Irak, 2011 Libya, 2019 Abqaiq, 2022 Rusya, 2025
     İsrail–İran, 2026 Hürmüz; pencere olay gününden sabit, sonucu bilmeden)
     ve 1988'den bu yana Brent'in 21 iş günde en az senaryonun alt ucu kadar
     yükseldiği BÜTÜN pencereler (nedeni karışık).
  3. ÖRNEKLEM DIŞI SINAMA — 2026 içinde bir-pencere-dışarıda (her yükseliş
     öbür üçünden tahmin edilir) ve 2026 öncesi pencerelerden 2026'ya.

SÖZLEŞMELER, ADIYLA.
· Ufuk 21 iş günü (≈ bir takvim ayı). Fiyatlar için log değişim (×100),
  getiriler için baz puan fark, oynaklık endeksleri için log değişim,
  rezervler için milyar dolar fark.
· "Brent" iki fiyattır: ICE ön vade vadelisi (basının "Brent"i, senaryonun
  sorduğu) ve fiziki Dated Brent (EIA "Europe Brent Spot FOB"). 2026'da ikisi
  arasında tarihte emsali olmayan bir fark açıldı; ikisi ayrı ayrı ölçülür.
· Vadeli Brent ham ön vade kapanışıdır; VADE DEVRİ GÜNÜ (ayın ilk iş günü)
  günlük getiri hesabına girmez. 21 günlük seviye değişimi devri içerebilir —
  basının "Brent bir ayda %X arttı" cümlesi de ön vade SEVİYESİNİ kıyaslar.
· Döviz çiftleri piyasanın kotasyon yönüyle: USD/TRY yükselişi liranın
  zayıflaması, EUR/USD düşüşü euronun zayıflamasıdır.
· Kapanış saatleri farklıdır (BIST 18:00 TSİ, Brent 19:30 Londra, döviz
  New York 17:00); 21 günlük pencere bu farkı söndürür, günlük eğim söndürmez.
· Kaynak kusurları KURALIYLA ve SAYIMIYLA düzeltilir (`duzelt_cnbc`): CNBC
  USD/TRY'nin 2004 sonundaki bazı günleri eski lira ölçeğinde (×10⁶), BIST 100
  2014 yılı ×100.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.dont_write_bytecode = True

BURASI = Path(__file__).resolve().parent
VERI = BURASI / "veri"
KUNYE = json.loads((VERI / "kunye.json").read_text(encoding="utf-8"))
CIKTI = VERI / "olcum.json"

SLUG = "brent-senaryo-2026-10-12"
BAZ_GUN = "2026-10-09"
SENARYO = {"125": 125.0, "150": 150.0}
UFUK = 21
NW_GECIKME = UFUK - 1
ESIK_ALT = None          # senaryonun alt ucunun log değişimi; senaryo_yeri() kurar
PENCERE_ESIK = 15.0      # 2026 pencereleri: Brent'in 21 iş günlük yükselişi en az %15
PENCERE_ARA = 35         # 2026 pencereleri: birbirinden 35 takvim gününden fazla uzak
GENIS_ARA = 40           # 1988+ geniş küme: birbirinden 40 takvim gününden fazla uzak
TAKVIM_TAVAN = 40        # 21 gözlemlik pencerenin takvim boyu bunu aşarsa (kaynakta boşluk) atılır
LOO_ASGARI = 40          # bir-pencere-dışarıda sınamada eğitimde kalması gereken en az gün


# ─────────────────────────────────────────────────────────────── okuma
def oku(ad: str) -> pd.DataFrame:
    yol = VERI / f"{ad}.csv.gz"
    ham = gzip.decompress(yol.read_bytes())
    beklenen = (KUNYE["dosyalar"].get(yol.name) or {}).get("sha256")
    gercek = hashlib.sha256(ham).hexdigest()
    if beklenen != gercek:
        raise SystemExit(f"{yol.name}: öz künyeyle tutmuyor ({gercek[:12]} ≠ {str(beklenen)[:12]})")
    return pd.read_csv(yol, index_col=0, parse_dates=True)


_ONBELLEK: dict[str, pd.DataFrame] = {}


def tablo(ad: str) -> pd.DataFrame:
    if ad not in _ONBELLEK:
        _ONBELLEK[ad] = oku(ad)
    return _ONBELLEK[ad]


# ─────────────────────────────────────────────────────────────── istatistik
def ekk_nw(y: np.ndarray, x: np.ndarray, gecikme: int) -> dict:
    """y = a + b·x; Newey–West (Bartlett) standart hata. Örtüşen 21 günlük
    pencerelerin hata terimi 20 gecikmeye kadar ilişkili; düz EKK hatası
    örneklemi 21 kat büyük sanır."""
    n = len(y)
    X = np.column_stack([np.ones(n), x])
    XtXi = np.linalg.inv(X.T @ X)
    b = XtXi @ X.T @ y
    e = y - X @ b
    u = X * e[:, None]
    S = u.T @ u
    for L in range(1, gecikme + 1):
        w = 1 - L / (gecikme + 1)
        G = u[L:].T @ u[:-L]
        S += w * (G + G.T)
    V = XtXi @ S @ XtXi
    se = np.sqrt(np.diag(V))
    r2 = 1 - (e @ e) / np.sum((y - y.mean()) ** 2) if n > 2 else float("nan")
    return {"sabit": float(b[0]), "egim": float(b[1]), "se_sabit": float(se[0]), "se": float(se[1]),
            "kov": float(V[0, 1]),
            "t": float(b[1] / se[1]) if se[1] > 0 else float("nan"), "r2": float(r2), "n": int(n),
            "artik_sd": float(np.std(e, ddof=2))}


def ekk(y: np.ndarray, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Düz EKK (sabit dahil sütun X'te); katsayı ve kovaryans."""
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    e = y - X @ b
    s2 = e @ e / (len(y) - X.shape[1])
    return b, s2 * np.linalg.inv(X.T @ X)


def degisim(x: pd.Series, birim: str, h: int = UFUK) -> pd.Series:
    if birim == "log":
        return np.log(x / x.shift(h)) * 100
    if birim == "bp":
        return (x - x.shift(h)) * 100
    if birim == "fark":
        return x - x.shift(h)
    raise ValueError(birim)


def pencere_log(s: pd.Series, h: int = UFUK, azami_gun: int = TAKVIM_TAVAN) -> pd.Series:
    """h GÖZLEMLİK log değişim (×100); pencerenin TAKVİM boyu `azami_gun`ü aşıyorsa boş.
    Kaynakta boşluk varsa (CNBC Brent 29.12.1989 → 09.10.1990) h gözlem bir aydan uzun bir
    aralığı kapsar ve "21 iş günlük değişim" sessizce dokuz aylık değişime dönüşür."""
    s = s.dropna()
    r = np.log(s / s.shift(h)) * 100
    boy = pd.Series(s.index, index=s.index).diff(h).dt.days
    return r[boy <= azami_gun]


def yuzde(m: float | None) -> float | None:
    """Log değişim (×100) → yüzde değişim. Okura giden her fiyat değişimi yüzdedir: büyük hareketlerde
    log ölçü ile yüzde ayrışır (log +53,6 = +%70,8) ve okurun seviye aritmetiği log ölçüde tutmaz.
    Eğimler (esneklikler) log ölçüde kalır."""
    return None if m is None else (math.exp(m / 100) - 1) * 100


def iki_nokta(s: pd.Series, t0: pd.Timestamp, t1: pd.Timestamp, birim: str, tol: int = 5) -> float | None:
    """t0 ve t1'de (ya da en çok `tol` takvim günü öncesinde) gözlenen değerlerden değişim.
    Uçlardan biri boşluktaysa ölçülmez (bir boşluğun üstünden ölçülen değişim uydurmadır)."""
    s = s.dropna()
    a = s[s.index <= t0]
    b = s[s.index <= t1]
    if a.empty or b.empty or (t0 - a.index[-1]).days > tol or (t1 - b.index[-1]).days > tol:
        return None
    x0, x1 = float(a.iloc[-1]), float(b.iloc[-1])
    if birim == "log":
        return math.log(x1 / x0) * 100 if x0 > 0 and x1 > 0 else None
    if birim == "bp":
        return (x1 - x0) * 100
    return x1 - x0


# ─────────────────────────────────────────────────────────────── kaynak düzeltmeleri
def duzelt_cnbc(C: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    C = C.copy()
    say = {}
    if "try" in C:
        m = C["try"] > 1000
        say["try_eski_lira_gun"] = int(m.sum())
        C.loc[m, "try"] = C.loc[m, "try"] / 1e6
    if "bist100" in C:
        x = C["bist100"]
        m = (x.index.year == 2014) & (x > 20000)
        say["bist100_2014_x100_gun"] = int(m.sum())
        C.loc[m, "bist100"] = x[m] / 100
    # Yılbaşı (1 Ocak) barı: piyasa kapalı, kaynak bir önceki kotasyonu ya da sapkın bir
    # değer taşıyabiliyor (ölçüldü: BRL 2010-01-01 −%42) — atılır.
    yilbasi = (C.index.month == 1) & (C.index.day == 1)
    say["yilbasi_bari"] = int(yilbasi.sum())
    C = C[~yilbasi]
    return C, say


SURUCU_AD = {"nikkei": "n225"}
_CNBC: tuple | None = None


def cnbc() -> tuple[pd.DataFrame, dict]:
    """İki CNBC geçişinin birleşimi: bu yazının arşivi (`cnbc_gunluk`) önce, makro dersinin
    sürücü arşivi (`cnbc_surucu_2000`, aynı uç) yalnız BOŞLUĞU doldurur. Örtüşen günlerde
    iki geçişin birebirliği ölçülür ve yazılır — aynı kaynak iki ayrı günde aynı barı vermeli."""
    global _CNBC
    if _CNBC is not None:
        return _CNBC
    A = tablo("cnbc_gunluk")
    S = tablo("cnbc_surucu_2000").rename(columns=SURUCU_AD)
    birlesik, uyum = {}, {}
    for k in sorted(set(A.columns) | set(S.columns)):
        a = A[k].dropna() if k in A else pd.Series(dtype="float64")
        s = S[k].dropna() if k in S else pd.Series(dtype="float64")
        ort = a.index.intersection(s.index)
        if len(ort):
            fark = (a.loc[ort] / s.loc[ort] - 1).abs()
            uyum[k] = {"ortak_gun": int(len(ort)), "birebir_pay": float((fark < 1e-9).mean() * 100),
                       "azami_fark_yuzde": float(fark.max() * 100),
                       "yalniz_surucu": int(len(s.index.difference(a.index))),
                       "yalniz_arsiv": int(len(a.index.difference(s.index)))}
        birlesik[k] = pd.concat([a, s[~s.index.isin(a.index)]]).sort_index()
    C = pd.DataFrame(birlesik).sort_index()
    C = C[C.index.dayofweek < 5]
    C, say = duzelt_cnbc(C)
    say["iki_gecis_uyumu"] = uyum
    _CNBC = (C, say)
    return _CNBC


def brent_vadeli_uzun() -> pd.Series:
    """CNBC ön vade Brent (24.06.1988'den), 2026 penceresinde bültenin serisiyle birebir aynı (ölçülür:
    `kaynak_uyumu`)."""
    C, _ = cnbc()
    return C["brent"].dropna()


def brent_fiziki() -> pd.Series:
    return tablo("eia_spot_gunluk")["brent_spot_gunluk"].dropna()


def devir_gunleri(idx: pd.DatetimeIndex) -> set:
    """Brent ön vadesinin değiştiği gün: her ayın İLK iş günü (ICE Brent kontratı teslim ayından
    iki ay önceki ayın son iş günü dolar). Ölçüldü (`rejim_2026.devir.ornek`): 01.04.2026'da ön vade
    −%14,5, aynı gün WTI −%1,2; aradaki 14,4 log puan devrin kendisi."""
    s = pd.Series(idx, index=idx)
    return set(s.groupby([idx.year, idx.month]).min())


def ikinci_vade() -> pd.Series | None:
    """CNBC sürekli ikinci vade (@LCO.2) — arşivde varsa."""
    try:
        e = tablo("cnbc_egri")
    except (FileNotFoundError, SystemExit):
        return None
    return e["brent_2"].dropna() if "brent_2" in e else None


def brent_devirsiz(on: pd.Series) -> tuple[pd.Series, dict]:
    """Devirden arındırılmış Brent endeksi (son günde ön vadeye eşit): günlük log getiri, devir
    gününde YENİ ön vadenin bir önceki günkü fiyatına (= dünkü ikinci vade) göre ölçülür; ikinci
    vade yoksa o günün WTI getirisi konur (WTI ayın ilk iş günü devretmez — ayın 20'si civarı).
    Ön vadenin kendisi her 21 iş günlük pencerede tam bir devir içerir; geriye eğimli eğride devir
    tek başına bir "düşüş" yazar ve öbür varlıklar ona tepki vermez — kıyas serisinde gürültüdür."""
    on = on.dropna()
    r = np.log(on).diff()
    D = sorted(devir_gunleri(on.index))
    iki = ikinci_vade()
    C, _ = cnbc()
    wti = pd.concat([C["wti"].dropna(), tablo("piyasa_2026")["CL=F"].dropna()]).sort_index()
    wti = wti[~wti.index.duplicated(keep="last")]
    rw = np.log(wti).diff()
    kayit = {"ikinci_vade": 0, "wti": 0, "olcmedi": 0}
    bosluk = {}
    for g in D[1:]:
        i = on.index.get_loc(g)
        once = on.index[i - 1]
        if iki is not None and once in iki.index and g in on.index:
            r.loc[g] = math.log(on.loc[g] / iki.loc[once])
            kayit["ikinci_vade"] += 1
        elif g in rw.index and np.isfinite(rw.loc[g]):
            bosluk[g.strftime("%Y-%m-%d")] = float((r.loc[g] - rw.loc[g]) * 100)
            r.loc[g] = rw.loc[g]
            kayit["wti"] += 1
        else:
            kayit["olcmedi"] += 1
    endeks = np.exp(r.fillna(0).cumsum())
    endeks = endeks / endeks.iloc[-1] * on.iloc[-1]
    kayit["wti_bosluk_2026"] = {k: v for k, v in bosluk.items() if k >= "2025-10-01"}
    if kayit["wti_bosluk_2026"]:
        # yöntem ekinin örneği: pencerenin en büyük devir boşluğu (ön vade ile WTI'nın o günkü getirisi)
        g = max(kayit["wti_bosluk_2026"], key=lambda k: abs(kayit["wti_bosluk_2026"][k]))
        t = pd.Timestamp(g)
        rb = math.log(on.loc[t] / on.loc[on.index[on.index.get_loc(t) - 1]])
        kayit["ornek"] = {"gun": g, "on_vade_yuzde": float((math.exp(rb) - 1) * 100),
                          "wti_yuzde": float((math.exp(rw.loc[t]) - 1) * 100),
                          "fark_log": kayit["wti_bosluk_2026"][g]}
    return endeks, kayit


def egri_bugun() -> dict | None:
    """Yahoo'da listeli Brent kontratlarının BAZ_GUN kapanışı: senaryonun hedef günündeki ön vade
    bugünün ikinci vadesidir. Arşivde yoksa None (senaryo ön vadeyle kurulur, sebebi yazılır)."""
    try:
        k = tablo("egri_kontrat")
    except (FileNotFoundError, SystemExit):
        return None
    sat = k.loc[:BAZ_GUN].iloc[-1]
    bz = {c: float(v) for c, v in sat.items() if c.startswith("BZ") and np.isfinite(v)}
    return {"gun": k.loc[:BAZ_GUN].index[-1].strftime("%Y-%m-%d"), "brent": bz,
            "wti": {c: float(v) for c, v in sat.items() if c.startswith("CL") and np.isfinite(v)},
            "ulsd": {c: float(v) for c, v in sat.items() if c.startswith("HO") and np.isfinite(v)}}


# ─────────────────────────────────────────────────────────────── A — iki Brent
def iki_brent() -> dict:
    sp = brent_fiziki()
    p = tablo("piyasa_2026")["BZ=F"].dropna()
    vu = brent_vadeli_uzun()
    vad = pd.concat([vu[vu.index < p.index[0]], p]).sort_index()
    D = pd.concat([sp.rename("fiziki"), vad.rename("vadeli")], axis=1, sort=True).dropna()
    D["fark"] = D.fiziki - D.vadeli
    son = D.index[-1]
    tarih = D.loc["2000":"2025"]
    eki = D.loc["2026-10-01":]
    out = {
        "son_gun": son.strftime("%Y-%m-%d"), "fiziki_son": float(D.loc[son, "fiziki"]),
        "vadeli_ayni_gun": float(D.loc[son, "vadeli"]), "fark_son": float(D.loc[son, "fark"]),
        "fiziki_son_kaynak_gun": sp.index[-1].strftime("%Y-%m-%d"),
        "ekim_ort_fiziki": float(eki.fiziki.mean()), "ekim_ort_vadeli": float(eki.vadeli.mean()),
        "ekim_ort_fark": float(eki.fark.mean()), "ekim_gun": int(len(eki)),
        "fark_zirve_2026": float(D.loc["2026", "fark"].max()),
        "fark_zirve_2026_gun": D.loc["2026", "fark"].idxmax().strftime("%Y-%m-%d"),
        "fark_zirve_2026_fiziki": float(D.loc[D.loc["2026", "fark"].idxmax(), "fiziki"]),
        "fark_zirve_2026_vadeli": float(D.loc[D.loc["2026", "fark"].idxmax(), "vadeli"]),
        "fiziki_zirve_2026": float(sp.loc["2026"].max()),
        "fiziki_zirve_2026_gun": sp.loc["2026"].idxmax().strftime("%Y-%m-%d"),
        "tarihce_2000_2025": {
            "n": int(len(tarih)), "medyan": float(tarih.fark.median()),
            "p99": float(tarih.fark.quantile(0.99)), "azami": float(tarih.fark.max()),
            "azami_gun": tarih.fark.idxmax().strftime("%Y-%m-%d"),
            "son_gunden_buyuk_pay": float((tarih.fark >= D.loc[son, "fark"]).mean() * 100)},
        "aylik_2026": {k.strftime("%Y-%m"): {"fiziki": float(v.fiziki), "vadeli": float(v.vadeli), "fark": float(v.fark)}
                       for k, v in D.loc["2026"].resample("MS").mean().iterrows()},
        "fiziki_rekor": {"deger": float(sp.max()), "gun": sp.idxmax().strftime("%Y-%m-%d")},
    }
    # Türkiye'nin yakıt ithalatı birim değeri hangi fiyatı izliyor? (TÜİK dış ticaret endeksi, aylık)
    t = tablo("dis_ticaret_endeks")
    uv = np.log(t["ith_yakit_birim_deger"]).diff() * 100
    sm = np.log(sp.resample("MS").mean()).diff() * 100
    fm = np.log(vad.resample("MS").mean()).diff() * 100
    E = pd.DataFrame({"uv": uv, "s0": sm, "s1": sm.shift(1), "f0": fm, "f1": fm.shift(1)}).dropna()
    r2 = {}
    for ad, k in (("fiziki", ["s0", "s1"]), ("vadeli", ["f0", "f1"])):
        X = np.column_stack([np.ones(len(E))] + [E[c] for c in k])
        b, _ = ekk(E.uv.values, X)
        e = E.uv.values - X @ b
        r2[ad] = float(1 - e @ e / np.sum((E.uv - E.uv.mean()) ** 2))
    out["ithalat_birim_deger_r2"] = r2
    out["ithalat_birim_deger_n"] = int(len(E))
    out["ithalat_birim_deger_ilk"] = E.index[0].strftime("%Y-%m")
    out["ithalat_birim_deger_son"] = E.index[-1].strftime("%Y-%m")
    return out


# ─────────────────────────────────────────────────────────────── B — senaryonun yeri
def senaryo_yeri() -> dict:
    global ESIK_ALT
    p = tablo("piyasa_2026")["BZ=F"].dropna()
    baz = float(p.loc[BAZ_GUN])
    out = {"baz_gun": BAZ_GUN, "baz": baz, "senaryo": {}}
    for ad, h in SENARYO.items():
        out["senaryo"][ad] = {"hedef": h, "yuzde": (h / baz - 1) * 100, "log": math.log(h / baz) * 100}
    ESIK_ALT = out["senaryo"]["125"]["log"]
    # Hedef gün (21 iş günü sonra) ön vade bugünün İKİNCİ vadesidir: ICE Brent kontratı teslim ayından
    # iki ay önceki ayın son iş günü dolar — Aralık 2026 kontratı 30.10.2026'da. Öbür varlıkların
    # tepki verdiği değişim, o kontratın bugünkü fiyatından hedefe olan değişimdir (devirsiz).
    hedef_gun = pd.bdate_range(BAZ_GUN, periods=UFUK + 1)[-1]
    out["hedef_gun"] = hedef_gun.strftime("%Y-%m-%d")
    e = egri_bugun()
    out["egri"] = e
    if e and e["brent"]:
        ay = hedef_gun.year * 12 + hedef_gun.month - 1 + 2          # teslim ayı = hedef ay + 2
        kod = f"BZ{'FGHJKMNQUVXZ'[ay % 12]}{(ay // 12) % 100:02d}_NYM"
        ilk = sorted(e["brent"], key=lambda c: ("FGHJKMNQUVXZ".index(c[2]), c[3:5]))
        out["hedef_gun_on_vade"] = kod
        if kod in e["brent"]:
            f2 = e["brent"][kod]
            out["ikinci_vade_bugun"] = f2
            out["devir_payi"] = math.log(baz / f2) * 100
            for ad, h in SENARYO.items():
                out["senaryo"][ad]["log_devirsiz"] = math.log(h / f2) * 100
                out["senaryo"][ad]["yuzde_devirsiz"] = (h / f2 - 1) * 100
        out["egri_kodlari"] = ilk
    for ad, v in out["senaryo"].items():
        v.setdefault("log_devirsiz", None)
    # Eğrinin normalleşme fiyatlaması geçmişte tuttu mu: bugünün ön vadesi (Aralık 2026) Mart zirvesinin
    # son gününde ve 1 Eylül'de ne fiyatlanıyordu (aynı kontrat, Yahoo'da listeli kontrat kapanışı)
    kk = tablo("egri_kontrat")
    if "BZZ26_NYM" in kk:
        z = kk["BZZ26_NYM"].dropna()
        out["aralik26"] = {g: {"gun": z.loc[:g].index[-1].strftime("%Y-%m-%d"), "fiyat": float(z.loc[:g].iloc[-1])}
                           for g in ("2026-03-31", "2026-09-01", BAZ_GUN)}
    y26 = p[p.index >= "2026-01-01"]
    out["yil_ilk"] = {"gun": y26.index[0].strftime("%Y-%m-%d"), "deger": float(y26.iloc[0])}
    out["zirve_2026"] = {"gun": y26.idxmax().strftime("%Y-%m-%d"), "deger": float(y26.max())}
    # 12.10 sabahı kotasyonu bir HABER bilgisidir (bülten, Reuters); ölçüm değildir.
    r = np.log(p).diff().dropna()
    r = r[~r.index.isin(devir_gunleri(p.index))]
    out["gerceklesen_oyn_21g"] = float(r[r.index <= BAZ_GUN].iloc[-UFUK:].std(ddof=1) * math.sqrt(252) * 100)
    out["gerceklesen_oyn_mart_ekim"] = float(r[(r.index >= "2026-03-01") & (r.index <= BAZ_GUN)].std(ddof=1) * math.sqrt(252) * 100)
    # tarihsel sıklık: 21 iş günlük log değişim en az senaryo kadar
    sik = {}
    for ad, s, bas in (("vadeli_1988", brent_vadeli_uzun(), "1988-01-01"), ("fiziki_1987", brent_fiziki(), "1987-01-01")):
        s = s[s.index >= bas]
        if ad == "vadeli_1988":
            s = pd.concat([s[s.index < p.index[0]], p]).sort_index()
            s = s[~s.index.duplicated(keep="last")]
        lr = pencere_log(s).dropna()
        bas_fiyat = s.dropna().shift(UFUK)   # pencerenin başlangıç fiyatı (21 gözlem önce)
        d = {"n": int(len(lr)), "ilk": lr.index[0].strftime("%Y-%m-%d"), "son": lr.index[-1].strftime("%Y-%m-%d")}
        # kaynaktaki boşluklar (ardışık iki gözlem arasında 10 takvim gününden fazla): boşluğa düşen dönem bu
        # sayımın dışındadır ve sayımı kullanan her cümle bunu adıyla söyler (vadeli seride 1990 Körfez Savaşı)
        gi = s.dropna().index
        aralik = gi.to_series().diff().dt.days
        d["bosluk"] = [{"son_once": gi[gi.get_loc(t) - 1].strftime("%Y-%m-%d"), "ilk_sonra": t.strftime("%Y-%m-%d"),
                        "takvim_gun": int(v)} for t, v in aralik[aralik > 10].items()]
        for k, v in out["senaryo"].items():
            m = lr >= v["log"]
            # ayrı epizot: art arda gelen günler tek epizot (aradaki boşluk ≥ 21 iş günü yeni epizot)
            gun = lr.index[m]
            ep = []
            for g in gun:
                if not ep or (lr.index.get_loc(g) - lr.index.get_loc(ep[-1][-1])) > UFUK:
                    ep.append([g])
                else:
                    ep[-1].append(g)
            d[k] = {"pay": float(m.mean() * 100), "gun": int(m.sum()), "epizot": len(ep),
                    "epizotlar": [{"ilk": e[0].strftime("%Y-%m-%d"), "son": e[-1].strftime("%Y-%m-%d"),
                                   "azami": float(lr.loc[e].max()),
                                   "bas_azami": float(bas_fiyat.reindex(e).max())} for e in ep]}
        sik[ad] = d
    out["siklik"] = sik
    # opsiyon piyasasının ima ettiği olasılık (OVX: WTI fonu opsiyonları, 30 gün; çarpıklıksız lognormal,
    # risk-nötr ölçü — gerçek olasılık değil, piyasanın fiyatladığı oynaklığın aritmetiği)
    y = tablo("yahoo_kapanis")
    ovx = y["OVX"].dropna()
    ovx_son = float(ovx.loc[:BAZ_GUN].iloc[-1])
    s1 = ovx_son / 100 * math.sqrt(UFUK / 252)
    from math import erf, sqrt

    def N(z):
        return 0.5 * (1 + erf(z / sqrt(2)))

    sig = ovx_son / 100
    mu = -0.5 * sig ** 2                     # risk-nötr, faizsiz: vadelinin log fiyatının yıllık sürüklenmesi

    def dokunma(b: float, T: float) -> float:
        """Sürüklenmesi μ = −σ²/2 olan log fiyatın T yıl içinde b'ye EN AZ BİR KEZ değme olasılığı
        (yansıma ilkesi, sürekli gözlem): P = N((−b+μT)/σ√T) + e^{2μb/σ²}·N((−b−μT)/σ√T)."""
        if b <= 0:
            return 1.0
        s = sig * math.sqrt(T)
        return N((-b + mu * T) / s) + math.exp(2 * mu * b / sig ** 2) * N((-b - mu * T) / s)

    # DAYANAK hedef günün ön vadesidir: 9 Kasım'da ön vade bugünün Ocak 2027 kontratıdır (Bölüm 1) ve
    # risk-nötr ölçüde bir vadelinin beklenen değeri kendi fiyatıdır — ay sonu olasılığı 104,72'den değil
    # 101,25'ten kurulur. Değme olasılığı İKİ BACAKLIDIR: Aralık kontratı son işlem gününe (30 Ekim) kadar
    # ön vadedir, sonra Ocak; iki kontrat aynı sürücüyle hareket eder (log farkları bugünkü gibi sabit).
    gunler = pd.bdate_range(BAZ_GUN, periods=UFUK + 1)[1:]
    devir = min(g for g in gunler if g.month != pd.Timestamp(BAZ_GUN).month)   # ayın ilk iş günü devri
    n1 = int(sum(g < devir for g in gunler))
    n2 = UFUK - n1
    f1, f2 = baz, out.get("ikinci_vade_bugun") or baz
    T, T1, T2 = UFUK / 252, n1 / 252, n2 / 252

    def dokunma_iki_bacak(H: float) -> float:
        b1, b2 = math.log(H / f1), math.log(H / f2)
        p1 = dokunma(b1, T1)
        s1_ = sig * math.sqrt(T1)
        w = np.linspace(b1 - 12 * s1_, b1, 40001)          # ilk bacakta eşiğe değmemiş yolların bacak sonu
        phi = lambda z: np.exp(-0.5 * z ** 2) / math.sqrt(2 * math.pi)
        yog = (phi((w - mu * T1) / s1_) - math.exp(2 * mu * b1 / sig ** 2) * phi((w - 2 * b1 - mu * T1) / s1_)) / s1_
        p2 = np.array([dokunma(b2 - x, T2) for x in w])
        return (p1 + float(np.trapezoid(yog * p2, w))) * 100

    out["ovx"] = {"gun": ovx.loc[:BAZ_GUN].index[-1].strftime("%Y-%m-%d"), "deger": ovx_son,
                  "aylik_sigma": s1 * 100,
                  "dayanak": f2, "dayanak_kontrat": out.get("hedef_gun_on_vade"),
                  "bacak_gun": {"aralik": n1, "ocak": n2, "devir_gunu": devir.strftime("%Y-%m-%d")},
                  "olasilik": {k: (1 - N((math.log(v["hedef"] / f2) + 0.5 * s1 ** 2) / s1)) * 100
                               for k, v in out["senaryo"].items()},
                  "dokunma_olasiligi": {k: dokunma_iki_bacak(v["hedef"]) for k, v in out["senaryo"].items()},
                  # karşılaştırma için: dayanak bugünkü ön vade (104,72) olsaydı — yazıda kullanılmaz
                  "olasilik_on_vade": {k: (1 - N((v["log"] / 100 + 0.5 * s1 ** 2) / s1)) * 100 for k, v in out["senaryo"].items()},
                  "yuzdelik_2007": float((ovx <= ovx_son).mean() * 100),
                  "zirve_2026": float(ovx.loc["2026"].max()), "zirve_2026_gun": ovx.loc["2026"].idxmax().strftime("%Y-%m-%d")}
    # nominal ve reel rekorlar: vadeli kapanış rekoru, ABD TÜFE ile bugünün dolarına
    vu = brent_vadeli_uzun()
    rk = vu.loc[:"2025"].idxmax()
    k = tablo("kuresel_aylik")["abd_tufe"].dropna()
    tufe_son_ay = k.index[-1]
    carpan = float(k.iloc[-1] / k.loc[rk.strftime("%Y-%m-01")])
    out["rekor"] = {"vadeli_kapanis": float(vu.loc[rk]), "gun": rk.strftime("%Y-%m-%d"),
                    "tufe_carpani": carpan, "tufe_son_ay": tufe_son_ay.strftime("%Y-%m"),
                    "bugunun_dolariyla": float(vu.loc[rk]) * carpan,
                    "senaryo_2008_dolariyla": {kk: v / carpan for kk, v in SENARYO.items()}}
    return out


# ─────────────────────────────────────────────────────────────── C — 2026 rejimi
# (kod, okur adı, grup, birim, kaynak) — kaynak: "p" bülten fotoğrafı, "y" Yahoo düzeltilmiş kapanış,
# "c" CNBC, "tr" depo hatları
KUTUK = [
    ("BZ=F", "Brent (vadeli)", "emtia", "log", "p"), ("CL=F", "WTI", "emtia", "log", "p"),
    ("HO=F", "motorin vadelisi (ULSD)", "emtia", "log", "p"), ("RB=F", "benzin vadelisi (RBOB)", "emtia", "log", "p"),
    ("NG=F", "doğal gaz (Henry Hub)", "emtia", "log", "p"),
    ("GC=F", "altın", "emtia", "log", "p"), ("SI=F", "gümüş", "emtia", "log", "p"), ("HG=F", "bakır", "emtia", "log", "p"),
    ("^GSPC", "S&P 500", "hisse", "log", "p"), ("^NDX", "Nasdaq 100", "hisse", "log", "p"),
    ("^RUT", "Russell 2000", "hisse", "log", "p"), ("^STOXX", "STOXX Europe 600", "hisse", "log", "p"),
    ("^GDAXI", "DAX", "hisse", "log", "p"), ("^FCHI", "CAC 40", "hisse", "log", "p"),
    ("^FTSE", "FTSE 100", "hisse", "log", "p"), ("^N225", "Nikkei 225", "hisse", "log", "p"),
    ("^HSI", "Hang Seng", "hisse", "log", "p"), ("000001.SS", "Şanghay Bileşik", "hisse", "log", "p"),
    ("EEM", "gelişmekte olan piyasa hisseleri (EEM)", "hisse", "log", "p"),
    ("XLE", "ABD enerji sektörü (XLE)", "sektor", "log", "y"), ("XOP", "ABD petrol üreticileri (XOP)", "sektor", "log", "y"),
    ("JETS", "ABD havayolları (JETS)", "sektor", "log", "y"), ("XLY", "ABD isteğe bağlı tüketim (XLY)", "sektor", "log", "y"),
    ("XLP", "ABD temel tüketim (XLP)", "sektor", "log", "y"), ("XLK", "ABD teknoloji (XLK)", "sektor", "log", "y"),
    ("XLU", "ABD kamu hizmetleri (XLU)", "sektor", "log", "y"), ("ITA", "ABD savunma (ITA)", "sektor", "log", "y"),
    ("KSA", "Suudi Arabistan hisseleri (KSA)", "hisse", "log", "y"), ("UAE", "BAE hisseleri (UAE)", "hisse", "log", "y"),
    ("INDA", "Hindistan hisseleri (INDA)", "hisse", "log", "y"), ("EWY", "Kore hisseleri (EWY)", "hisse", "log", "y"),
    ("^VIX", "VIX", "oynaklik", "log", "p"), ("^MOVE", "MOVE", "oynaklik", "log", "p"),
    ("OVX", "petrol oynaklığı (OVX)", "oynaklik", "log", "y"),
    ("us2y", "ABD 2 yıllık", "faiz", "bp", "h"), ("us10y", "ABD 10 yıllık", "faiz", "bp", "h"),
    ("us30y", "ABD 30 yıllık", "faiz", "bp", "h"), ("be5y", "ABD 5 yıllık başabaş enflasyon", "faiz", "bp", "h"),
    ("reel10y", "ABD 10 yıllık reel getiri", "faiz", "bp", "h"),
    ("DX-Y.NYB", "dolar endeksi (DXY)", "doviz", "log", "p"), ("EURUSD=X", "EUR/USD", "doviz", "log", "p"),
    ("USDJPY=X", "USD/JPY", "doviz", "log", "p"), ("GBPUSD=X", "GBP/USD", "doviz", "log", "p"),
    ("USDCHF=X", "USD/CHF", "doviz", "log", "p"), ("USDCAD=X", "USD/CAD", "doviz", "log", "p"),
    ("USDNOK=X", "USD/NOK", "doviz", "log", "p"), ("AUDUSD=X", "AUD/USD", "doviz", "log", "p"),
    ("inr", "USD/INR", "doviz", "log", "c"), ("krw", "USD/KRW", "doviz", "log", "c"),
    ("zar", "USD/ZAR", "doviz", "log", "c"), ("mxn", "USD/MXN", "doviz", "log", "c"),
    ("brl", "USD/BRL", "doviz", "log", "c"), ("pln", "USD/PLN", "doviz", "log", "c"),
    ("HYG", "ABD yüksek getirili kredi (HYG)", "kredi", "log", "p"), ("LQD", "ABD yatırım yapılabilir kredi (LQD)", "kredi", "log", "p"),
    ("EMB", "gelişmekte olan ülke dolar tahvilleri (EMB)", "kredi", "log", "p"),
    ("USDTRY=X", "USD/TRY", "tr", "log", "p"), ("EURTRY=X", "EUR/TRY", "tr", "log", "p"),
    ("XU100.IS", "BIST 100", "tr", "log", "p"), ("bist_usd", "BIST 100 (dolar)", "tr", "log", "tr"),
    ("XBANK.IS", "BIST Bankacılık", "tr", "log", "p"), ("XUSIN.IS", "BIST Sınai", "tr", "log", "p"),
    ("TUR", "Türkiye hisse fonu (TUR, dolar)", "tr", "log", "p"),
    ("TUPRS_IS", "Tüpraş", "tr_hisse", "log", "y"), ("PETKM_IS", "Petkim", "tr_hisse", "log", "y"),
    ("THYAO_IS", "Türk Hava Yolları", "tr_hisse", "log", "y"), ("PGSUS_IS", "Pegasus", "tr_hisse", "log", "y"),
    ("TAVHL_IS", "TAV Havalimanları", "tr_hisse", "log", "y"), ("AKBNK_IS", "Akbank", "tr_hisse", "log", "y"),
    ("GARAN_IS", "Garanti BBVA", "tr_hisse", "log", "y"), ("FROTO_IS", "Ford Otosan", "tr_hisse", "log", "y"),
    ("BIMAS_IS", "BİM", "tr_hisse", "log", "y"), ("ASELS_IS", "Aselsan", "tr_hisse", "log", "y"),
    ("n3a", "DİBS 3 ay", "tr_faiz", "bp", "tr"), ("n2y", "DİBS 2 yıl", "tr_faiz", "bp", "tr"),
    ("n5y", "DİBS 5 yıl", "tr_faiz", "bp", "tr"), ("be_2y", "2 yıllık başabaş enflasyon", "tr_faiz", "bp", "tr"),
    ("r2y", "2 yıllık reel getiri (TÜFE'ye endeksli)", "tr_faiz", "bp", "tr"), ("tlref", "TLREF", "tr_faiz", "bp", "tr"),
    ("net_rezerv_usd", "TCMB net rezerv", "tr_rezerv", "fark", "tr"),
    ("swap_haric_net_rezerv_usd", "swap hariç net rezerv", "tr_rezerv", "fark", "tr"),
]
KOD = {k: (a, g, b, s) for k, a, g, b, s in KUTUK}


def panel_2026() -> pd.DataFrame:
    """Brent'in işlem günü takviminde bütün 2026 serileri (son bilinen kapanış
    ileri taşınır — bir borsanın tatilinde değer kımıldamamıştır)."""
    p = tablo("piyasa_2026")
    bz = p["BZ=F"].dropna()
    idx = bz.index
    X = p.reindex(idx).ffill()
    y = tablo("yahoo_duzeltilmis")
    for k, (_, _, _, s) in KOD.items():
        if s == "y" and k in y:
            X[k] = y[k].reindex(idx, method="ffill")
    C, _ = cnbc()
    for k, (_, _, _, s) in KOD.items():
        if s == "c" and k in C:
            X[k] = C[k].reindex(idx, method="ffill")
    h = tablo("hazine_nominal_2025")
    r = tablo("hazine_reel_2025")
    X["us2y"] = h["2 Yr"].reindex(idx, method="ffill")
    X["us10y"] = h["10 Yr"].reindex(idx, method="ffill")
    X["us30y"] = h["30 Yr"].reindex(idx, method="ffill")
    X["reel10y"] = r["10 YR"].reindex(idx, method="ffill")
    X["be5y"] = (h["5 Yr"] - r["5 YR"]).reindex(idx, method="ffill")
    d = tablo("dibs_gunluk")
    for c in ("n3a", "n2y", "n5y", "be_2y", "r2y"):
        X[c] = d[c].reindex(idx, method="ffill")
    X["tlref"] = tablo("fonlama_gunluk")["tlref"].reindex(idx, method="ffill")
    rz = tablo("rezerv_gunluk")
    X["net_rezerv_usd"] = rz["net_rezerv_usd"].reindex(idx, method="ffill")
    X["swap_haric_net_rezerv_usd"] = rz["swap_haric_net_rezerv_usd"].reindex(idx, method="ffill")
    X["bist_usd"] = X["XU100.IS"] / X["USDTRY=X"]
    return X


def yukselis_pencereleri(bz: pd.Series, esik: float = PENCERE_ESIK) -> list[dict]:
    """Brent'in 21 iş günlük yükselişinin en büyük olduğu, birbirine 35 takvim
    gününden yakın olmayan pencereler (eşik %15). Seçim yalnız Brent'e bakar;
    öbür varlıkların ne yaptığını bilmez."""
    r = (bz / bz.shift(UFUK) - 1) * 100
    secilen = []
    for t, v in r.dropna().sort_values(ascending=False).items():
        if v < esik:
            break
        if all(abs((t - s).days) > PENCERE_ARA for s in secilen):
            secilen.append(t)
    out = []
    for t in sorted(secilen):
        i = bz.index.get_loc(t)
        b = bz.index[i - UFUK]
        out.append({"bas": b.strftime("%Y-%m-%d"), "son": t.strftime("%Y-%m-%d"),
                    "brent_bas": float(bz[b]), "brent_son": float(bz[t]),
                    "brent_yuzde": float(r[t]), "brent_log": float(np.log(bz[t] / bz[b]) * 100)})
    return out


def _kiyas(X: pd.DataFrame) -> tuple[pd.Series, pd.Series, dict]:
    """Kıyas serileri: ön vadenin 21 günlük log değişimi (basının "Brent bir ayda %X") ve devirden
    arındırılmış endeksinkini (öbür varlıkların tepki verdiği fiyat değişimi)."""
    bz = X["BZ=F"]
    d, kayit = brent_devirsiz(bz)
    return np.log(bz / bz.shift(UFUK)) * 100, np.log(d / d.shift(UFUK)) * 100, kayit


def rejim_2026() -> dict:
    """ESAS kıyas devirsiz değişimdir: her 21 iş günlük pencere bir devir içerir ve 2026'nın geriye
    eğimli eğrisinde devir günleri ön vadeye öbür varlıkların görmediği bir sıçrama yazar (ölçüldü:
    01.04.2026'da −14,4 puan). Ön vadeyle kurulan eğim yan yana yazılır."""
    X = panel_2026()
    bz = X["BZ=F"]
    lb, ld, kayit = _kiyas(X)
    pencereler = yukselis_pencereleri(bz)
    for p in pencereler:
        p["devirsiz_log"] = float(ld.loc[pd.Timestamp(p["son"])])
    varliklar = {}
    for k, (ad, grup, birim, _) in KOD.items():
        if k not in X or X[k].dropna().empty:
            continue
        y = degisim(X[k], birim)
        kayit_v = {"ad": ad, "grup": grup, "birim": birim}
        for etiket, x in (("", ld), ("_on", lb)):
            df = pd.concat([x, y], axis=1, keys=["b", "y"]).dropna()
            if len(df) < 120:
                break
            up, dn = df[df.b > 0], df[df.b < 0]
            kayit_v["tum" + etiket] = ekk_nw(df.y.values, df.b.values, NW_GECIKME)
            kayit_v["yukselis" + etiket] = ekk_nw(up.y.values, up.b.values, NW_GECIKME)
            kayit_v["dusus" + etiket] = ekk_nw(dn.y.values, dn.b.values, NW_GECIKME)
        else:
            ep = []
            for p in pencereler:
                t = pd.Timestamp(p["son"])
                ep.append(float(y.loc[t]) if t in y.index and np.isfinite(y.loc[t]) else None)
            son = X[k].dropna()
            # Doğrunun SABİTİ eğilim değildir: yükseliş günlerinden kestirilen doğrunun Brent'in kımıldamadığı
            # bir aya uzatılmış değeridir. Okur onu gerçekleşen eğilimle kıyaslayabilsin diye ikisi yazılır:
            # bütün günlerin ortalama 21 günlük değişimi ve Brent'in bir ayda ±5 log puan içinde kaldığı günlerinki.
            df = pd.concat([ld, y], axis=1, keys=["b", "y"]).dropna()
            yatay = df[df.b.abs() < 5]
            kayit_v.update({"pencere": ep, "son_deger": float(son.iloc[-1]), "son_gun": son.index[-1].strftime("%Y-%m-%d"),
                            "pencere_yuzde": [yuzde(x) for x in ep] if birim == "log" else ep,
                            "ortalama_21g": float(df.y.mean()), "yatay_brent_ortalama": float(yatay.y.mean()),
                            "yatay_brent_gun": int(len(yatay))})
            varliklar[k] = kayit_v
    # Etkin örneklem: Brent'in yükseldiği günler kesintisiz dizilere toplanır; bilgi gün sayısından değil
    # dizilerden (epizotlardan) gelir. 150 dolarlık x'e yakın günlerin hangi dizide olduğu ayrıca yazılır.
    lx = ld.dropna()
    diziler, cari = [], []
    for t, v in lx.items():
        if v > 0:
            cari.append(t)
        elif cari:
            diziler.append(cari); cari = []
    if cari:
        diziler.append(cari)
    dz = [{"bas": d[0].strftime("%Y-%m-%d"), "son": d[-1].strftime("%Y-%m-%d"), "gun": len(d),
           "en_buyuk_x": float(lx.loc[d].max())} for d in diziler]
    ust = lx[lx > 30]
    return {"pencereler": pencereler, "varlik": varliklar, "n_gun": int(lb.dropna().shape[0]),
            "ilk": X.index[0].strftime("%Y-%m-%d"), "son": X.index[-1].strftime("%Y-%m-%d"),
            "ilk_degisim": lb.dropna().index[0].strftime("%Y-%m-%d"), "n_islem_gunu": int(len(X)),
            "devir": kayit, "yukselis_dizileri": dz,
            "yukselis_gunu": int((lx > 0).sum()),
            "x30": {"gun": int(len(ust)), "ilk": ust.index[0].strftime("%Y-%m-%d") if len(ust) else None,
                    "son": ust.index[-1].strftime("%Y-%m-%d") if len(ust) else None}}


def birini_disarida_birak(rejim: dict) -> dict:
    """Her yükseliş penceresi, öbür pencerelerin bulunduğu (dışarıda bırakılanın 42 iş günü öncesi
    ile 21 iş günü sonrası çıkarılmış) Brent-yükseliş günlerinden kestirilen eğimle tahmin edilir.
    Kıyas serisi esas tanımdır (devirsiz)."""
    X = panel_2026()
    _, ld, _ = _kiyas(X)
    out = {}
    for k, v in rejim["varlik"].items():
        y = degisim(X[k], v["birim"])
        df = pd.concat([ld, y], axis=1, keys=["b", "y"]).dropna()
        tahmin, gercek, egilim, kapsama, egitim_pencere = [], [], [], [], []
        for p in rejim["pencereler"]:
            t = pd.Timestamp(p["son"])
            i = X.index.get_loc(t)
            dis = X.index[max(0, i - 2 * UFUK): min(len(X), i + UFUK + 1)]
            egitim = df[(~df.index.isin(dis)) & (df.b > 0)]
            if len(egitim) < LOO_ASGARI or t not in df.index:
                tahmin.append(None); gercek.append(None); egilim.append(None); kapsama.append(None)
                egitim_pencere.append(None)
                continue
            m = ekk_nw(egitim.y.values, egitim.b.values, NW_GECIKME)
            x = float(df.loc[t, "b"])
            tahmin.append(m["sabit"] + m["egim"] * x)
            gercek.append(float(df.loc[t, "y"]))
            # GÖRÜŞSÜZ KIYAS: Brent'in büyüklüğünü kullanmayan tahmin — kalemin, eğitimde Brent'in yükseldiği
            # günlerdeki ortalama 21 günlük değişimi (2026'nın kendi eğilimi). Yıl boyu yükselen bir seri "hiçbir
            # şey olmaz" (sıfır) tahminini Brent'e hiç bakmadan da yener; doğrunun ondan iyi olması gerekir.
            egilim.append(float(egitim.y.mean()))
            # %90 aralığın kapsaması: tablolardaki bantla aynı formül, eğitim doğrusundan
            bant = 1.645 * math.sqrt(max(0.0, m["se_sabit"] ** 2 + (m["se"] * x) ** 2 + 2 * x * m["kov"]) + m["artik_sd"] ** 2)
            kapsama.append(bool(abs(gercek[-1] - tahmin[-1]) <= bant))
            # eğitimde hangi pencerelerin Brent-yükseliş günleri kaldı (dışlama aralığı komşu pencereyi de yutabilir)
            kalan = []
            for q in rejim["pencereler"]:
                if q is p:
                    continue
                qa, qs = pd.Timestamp(q["bas"]), pd.Timestamp(q["son"])
                if ((egitim.index > qa) & (egitim.index <= qs)).any():
                    kalan.append(q["son"])
            egitim_pencere.append(kalan)
        ciftler = [(a, g, e) for a, g, e in zip(tahmin, gercek, egilim) if a is not None]
        if len(ciftler) < 3:
            continue
        a = np.array([c[0] for c in ciftler]); g = np.array([c[1] for c in ciftler]); e = np.array([c[2] for c in ciftler])
        out[k] = {"tahmin": tahmin, "gercek": gercek, "tahmin_egilim": egilim,
                  "isaret_tutan": int(np.sum(np.sign(a) == np.sign(g))),
                  "n": len(ciftler), "rmse": float(np.sqrt(np.mean((g - a) ** 2))),
                  "rmse_sifir": float(np.sqrt(np.mean(g ** 2))),
                  "rmse_egilim": float(np.sqrt(np.mean((g - e) ** 2))),
                  "kapsama": kapsama, "kapsanan": int(sum(1 for c in kapsama if c)),
                  "egitimde_kalan_pencereler": egitim_pencere}
    return out


# ─────────────────────────────────────────────────────────────── D — emsaller
# Anlatıyla belgelenmiş arz olayları: (anahtar, okur adı, olaydan önceki son kapanış günü)
OLAYLAR = [
    ("1990", "1990 Körfez (Irak'ın Kuveyt'i işgali, 2 Ağustos)", "1990-08-01"),
    ("2002", "2002 Venezuela genel grevi (2 Aralık)", "2002-11-29"),
    ("2003", "2003 Irak savaşının başlaması (20 Mart)", "2003-03-19"),
    ("2011", "2011 Libya (15 Şubat'tan itibaren)", "2011-02-14"),
    ("2019", "2019 Abqaiq saldırısı (14 Eylül)", "2019-09-13"),
    ("2022", "2022 Rusya'nın Ukrayna'yı işgali (24 Şubat)", "2022-02-23"),
    ("2025", "2025 İsrail–İran savaşı (13 Haziran)", "2025-06-12"),
    ("2026", "2026 Hürmüz (2 Mart)", "2026-02-27"),
]
# Emsal tablosunun sütunları: (anahtar, okur adı, birim, kaynak)
EMSAL_SUTUN = [
    ("brent_fiziki", "Brent (fiziki)", "log", "eia"), ("brent", "Brent (vadeli)", "log", "c"),
    ("spx", "S&P 500", "log", "c"), ("vix", "VIX", "log", "c"), ("dxy", "dolar endeksi", "log", "c"),
    ("us2y", "ABD 2 yıllık", "bp", "h90"), ("us10y", "ABD 10 yıllık", "bp", "h90"),
    ("altin", "altın", "log", "c"), ("jpy", "USD/JPY", "log", "c"), ("eur", "EUR/USD", "log", "c"),
    ("gbp", "GBP/USD", "log", "c"), ("dax", "DAX", "log", "c"), ("n225", "Nikkei 225", "log", "c"),
    ("try_tcmb", "USD/TRY (TCMB)", "log", "tcmb"), ("bist100", "BIST 100", "log", "c"),
    ("bist_usd", "BIST 100 (dolar)", "log", "c"),
]
BIRIM_EMSAL = {s: b for s, _, b, _ in EMSAL_SUTUN}
# TL gecelik faizi (EVDS TP.PY.P06.ON) bilerek YOK: 2026 Mart'ında TLREF koridorun üstüne (%40)
# çıkarken bu seri %35,5'te kımıldamadı (ölçüldü) — piyasanın fonlama maliyetini ölçmüyor.


def emsal_kaynak() -> dict[str, pd.Series]:
    C, _ = cnbc()
    h = tablo("abd_hazine_1990")
    hz = tablo("hazine_nominal_2025")
    us2 = pd.concat([h["us2y"], hz["2 Yr"]]).sort_index()
    us10 = pd.concat([h["us10y"], hz["10 Yr"]]).sort_index()
    p = tablo("piyasa_2026")
    seri = {"brent_fiziki": brent_fiziki(),
            "us2y": us2[~us2.index.duplicated(keep="last")], "us10y": us10[~us10.index.duplicated(keep="last")],
            "try_tcmb": tablo("usdtry_tcmb_1990")["usdtry_tcmb_valor"]}
    for k in ("brent", "spx", "vix", "dxy", "altin", "jpy", "eur", "gbp", "dax", "n225", "bist100"):
        if k in C:
            seri[k] = C[k]
    ortak = pd.concat([C["bist100"], C["try"]], axis=1, keys=["b", "t"]).dropna()
    seri["bist_usd"] = ortak.b / ortak.t
    # 2026 penceresi için vadeli Brent bültenin serisinden (CNBC ile birebir — ölçüldü)
    seri["brent"] = pd.concat([seri["brent"][seri["brent"].index < p.index[0]], p["BZ=F"].dropna()]).sort_index()
    return seri


def ny_fed_ayristirma(t0: pd.Timestamp, t1: pd.Timestamp) -> dict | None:
    n = tablo("nyfed_haftalik")
    if t1 > n.index.max() + pd.Timedelta(days=7):
        return None
    w = n[(n.index > t0) & (n.index <= t1 + pd.Timedelta(days=3))]
    if w.empty:
        return None
    return {"talep": float(w.talep.sum() * 100), "arz": float(w.arz.sum() * 100),
            "artik": float(w.artik.sum() * 100), "hafta": int(len(w))}


def emsaller() -> dict:
    seri = emsal_kaynak()
    sp = brent_fiziki()
    out = {}
    for k, ad, bas in OLAYLAR:
        t0 = sp.index[sp.index.searchsorted(pd.Timestamp(bas), side="right") - 1]
        i = sp.index.get_loc(t0)
        t1 = sp.index[min(i + UFUK, len(sp) - 1)]
        sat = {"ad": ad, "bas": t0.strftime("%Y-%m-%d"), "son": t1.strftime("%Y-%m-%d"), "deger": {}}
        for s, _, birim, _ in EMSAL_SUTUN:
            if s in seri:
                sat["deger"][s] = iki_nokta(seri[s], t0, t1, birim)
        sat["deger_yuzde"] = {s: (yuzde(v) if BIRIM_EMSAL[s] == "log" else v) for s, v in sat["deger"].items()}
        sat["nyfed"] = ny_fed_ayristirma(t0, t1)
        out[k] = sat
    return out


def tum_yukselisler() -> dict:
    """1988'den bu yana vadeli Brent'in 21 iş günde EN AZ senaryonun alt ucu kadar
    (log ölçüde) yükseldiği, birbirine 40 takvim gününden yakın olmayan bütün
    pencereler. Nedeni karışık: talep toparlanmaları da, arz şokları da burada."""
    seri = emsal_kaynak()
    bz = seri["brent"].dropna()
    r = pencere_log(bz)
    sec = []
    for t, v in r.dropna().sort_values(ascending=False).items():
        if v < ESIK_ALT:
            break
        if all(abs((t - s).days) > GENIS_ARA for s in sec):
            sec.append(t)
    pencere = []
    for t in sorted(sec):
        i = bz.index.get_loc(t)
        t0 = bz.index[i - UFUK]
        sat = {"bas": t0.strftime("%Y-%m-%d"), "son": t.strftime("%Y-%m-%d"), "brent": float(r[t]),
               "brent_yuzde": yuzde(float(r[t])), "deger": {}}
        for s, _, birim, _ in EMSAL_SUTUN:
            if s in seri and s not in ("brent", "brent_fiziki"):
                sat["deger"][s] = iki_nokta(seri[s], t0, t, birim)
        sat["deger_yuzde"] = {s: (yuzde(v) if BIRIM_EMSAL[s] == "log" else v) for s, v in sat["deger"].items()}
        sat["nyfed"] = ny_fed_ayristirma(t0, t)
        pencere.append(sat)
    # gruplar: 2026 (bu savaş) · 2026 öncesi; 2026 öncesi NY Fed ayrıştırmasıyla ayrıca arz/talep baskın
    ozet = {}
    for grup, sec_f in (("y2026", lambda p: p["son"] >= "2026-01-01"),
                        ("once", lambda p: p["son"] < "2026-01-01"),
                        ("once_arz", lambda p: p["son"] < "2026-01-01" and p["nyfed"] and p["nyfed"]["arz"] > p["nyfed"]["talep"]),
                        ("once_talep", lambda p: p["son"] < "2026-01-01" and p["nyfed"] and p["nyfed"]["arz"] <= p["nyfed"]["talep"])):
        ps = [p for p in pencere if sec_f(p)]
        g = {"n": len(ps), "brent_medyan": float(np.median([p["brent"] for p in ps])) if ps else None,
             "brent_medyan_yuzde": float(np.median([p["brent_yuzde"] for p in ps])) if ps else None}
        for s, _, _, _ in EMSAL_SUTUN:
            v = [p["deger"].get(s) for p in ps if p["deger"].get(s) is not None]
            if v:
                vy = [p["deger_yuzde"][s] for p in ps if p["deger"].get(s) is not None]
                g[s] = {"medyan": float(np.median(v)), "medyan_yuzde": float(np.median(vy)),
                        "n": len(v), "arti_pay": float(np.mean(np.array(v) > 0) * 100),
                        "elastikiyet_medyan": float(np.median([p["deger"][s] / p["brent"] for p in ps
                                                               if p["deger"].get(s) is not None]))}
        ozet[grup] = g
    # ÖRNEKLEM DIŞI: 2026 öncesi pencerelerin medyan esnekliği × 2026 penceresinin Brent hareketi
    oos = {}
    once = [p for p in pencere if p["son"] < "2026-01-01"]
    sonra = [p for p in pencere if p["son"] >= "2026-01-01"]
    for s, _, _, _ in EMSAL_SUTUN:
        e = [p["deger"][s] / p["brent"] for p in once if p["deger"].get(s) is not None]
        ciftler = [(np.median(e) * p["brent"], p["deger"][s]) for p in sonra if p["deger"].get(s) is not None]
        if len(e) >= 10 and len(ciftler) >= 3:
            a = np.array([c[0] for c in ciftler]); g_ = np.array([c[1] for c in ciftler])
            oos[s] = {"isaret_tutan": int(np.sum(np.sign(a) == np.sign(g_))), "n": len(ciftler),
                      "rmse": float(np.sqrt(np.mean((g_ - a) ** 2))), "rmse_sifir": float(np.sqrt(np.mean(g_ ** 2))),
                      "esneklik_once": float(np.median(e))}
    return {"esik_log": ESIK_ALT, "pencere": pencere, "ozet": ozet, "orneklem_disi_2026": oos}


# ─────────────────────────────────────────────────────────────── E — Türkiye
def tcmb_oyun_kitabi() -> dict:
    """İki dış şokta TCMB'nin aynı araç seti: bir hafta vadeli repo ihalesini
    kesmek (fonlama koridorun üst bandına çıkar), döviz satmak, kuru yönetilen
    patikada tutmak. Pencereler olaydan önceki son iş gününden 21 iş günü."""
    f = tablo("fonlama_gunluk")
    r = tablo("rezerv_gunluk")
    p = tablo("piyasa_2026")
    d = tablo("dibs_gunluk")
    u = tablo("usdtry_tcmb_1990")["usdtry_tcmb_valor"]
    olaylar = {"2025-03": ("2025-03-18", "siyasi şok (19 Mart 2025)"),
               "2026-03": ("2026-02-27", "petrol şoku (Hürmüz, 2 Mart 2026)")}
    out = {}
    for ad, (bas, aciklama) in olaylar.items():
        b = pd.Timestamp(bas)
        gunler = f.loc[b:].index[:UFUK + 1]
        s = gunler[-1]
        ihale = f.loc[b:s, "fon_ihale"]
        sifir = ihale[ihale <= 0]
        # ara verildiği gün: bir hafta vadeli repo stoku olay öncesi düzeyinin altına ilk indiği gün
        # (stok vadesi dolan repolarla birer birer erir; sıfırlandığı gün ara verildiği gün DEĞİLDİR)
        ara = ihale[(ihale.index > b) & (ihale < ihale.iloc[0])]
        aofm = f.loc[b:s, ["aofm", "koridor_ust"]].dropna()
        tavan = aofm[aofm["aofm"] >= aofm["koridor_ust"] - 0.005]
        rr = r.loc[b:s]
        kayit = {
            "aciklama": aciklama, "bas": bas, "son": s.strftime("%Y-%m-%d"),
            "aofm_bas": float(f.loc[:b, "aofm"].dropna().iloc[-1]), "aofm_zirve": float(f.loc[b:s, "aofm"].max()),
            "tlref_bas": float(f.loc[:b, "tlref"].dropna().iloc[-1]), "tlref_son": float(f.loc[:s, "tlref"].dropna().iloc[-1]),
            "politika_bas": float(f.loc[:b, "politika"].dropna().iloc[-1]),
            "politika_son": float(f.loc[:s, "politika"].dropna().iloc[-1]),
            "koridor_ust_bas": float(f.loc[:b, "koridor_ust"].dropna().iloc[-1]),
            "koridor_ust_son": float(f.loc[:s, "koridor_ust"].dropna().iloc[-1]),
            "ihale_sifir_ilk": sifir.index[0].strftime("%Y-%m-%d") if len(sifir) else None,
            "ihale_ara_ilk": ara.index[0].strftime("%Y-%m-%d") if len(ara) else None,
            "tlref_ara_ilk": float(f.loc[ara.index[0], "tlref"]) if len(ara) and pd.notna(f.loc[ara.index[0], "tlref"]) else None,
            "aofm_tavan_ilk": tavan.index[0].strftime("%Y-%m-%d") if len(tavan) else None,
            "doviz_satisi_21g": float(r.loc[b + pd.Timedelta(days=1):s, "net_doviz_alimi"].sum()),
            "net_rezerv_bas": float(r.loc[:b, "net_rezerv_usd"].dropna().iloc[-1]),
            "net_rezerv_dip": float(rr["net_rezerv_usd"].min()),
            "net_rezerv_dip_gun": rr["net_rezerv_usd"].idxmin().strftime("%Y-%m-%d"),
            "swap_haric_bas": float(r.loc[:b, "swap_haric_net_rezerv_usd"].dropna().iloc[-1]),
            "swap_haric_dip": float(rr["swap_haric_net_rezerv_usd"].min()),
            "swap_haric_dip_gun": rr["swap_haric_net_rezerv_usd"].idxmin().strftime("%Y-%m-%d"),
            "usdtry_tcmb_degisim": float((u.loc[:s].iloc[-1] / u.loc[:b].iloc[-1] - 1) * 100),
            "dibs_2y_bp": float((d.loc[:s, "n2y"].dropna().iloc[-1] - d.loc[:b, "n2y"].dropna().iloc[-1]) * 100),
            "dibs_2y_bas": float(d.loc[:b, "n2y"].dropna().iloc[-1]), "dibs_2y_son": float(d.loc[:s, "n2y"].dropna().iloc[-1]),
        }
        if b >= p.index[0]:
            pu = p["USDTRY=X"].dropna()
            kayit["usdtry_ist18_degisim"] = float((pu.loc[:s].iloc[-1] / pu.loc[:b].iloc[-1] - 1) * 100)
            xu = p["XU100.IS"].dropna()
            kayit["xu100_degisim"] = float((xu.loc[:s].iloc[-1] / xu.loc[:b].iloc[-1] - 1) * 100)
        # Erimenin bileşimi: swap hariç net rezervin düşüşü döviz satışı ile altın fiyat etkisinden (ve
        # swap/öbür kalemlerden) oluşur — "bedeli rezerv ödedi" cümlesinin ne kadarı savunma, ne kadarı fiyat
        ic = r.loc[b + pd.Timedelta(days=1):s]
        if "altin_fiyat_etkisi" in ic:
            kayit["altin_fiyat_etkisi_21g"] = float(ic["altin_fiyat_etkisi"].sum())
        # Etiket sözleşmesi (TCMBNetRezerv/altin_etkisi.py §2): L etiketli akım stokun L → L+1 değişimini taşır.
        # Pencerenin 21 işlem gününün (b+1..s) satışı ve altın etkisi, stokun b+1 → s'den sonraki ilk gün
        # değişimine karşılık gelir; b → s bilanço farkı bir gün kayıktır ve ikisi aynı ayrıştırmada toplanmaz.
        swd = r["swap_haric_net_rezerv_usd"].dropna()
        ileri = swd.shift(-1) - swd                       # etiket L: L → L+1 stok değişimi
        kayit["swap_haric_degisim_islem_21g"] = float(ileri.reindex(ic.index).sum())
        kayit["swap_haric_islem_bas"] = ic.index[0].strftime("%Y-%m-%d")
        kayit["swap_haric_islem_son_bilanco"] = swd.index[swd.index > s][0].strftime("%Y-%m-%d")
        kayit["swap_haric_son"] = float(swd.loc[:s].iloc[-1])
        # haftalık dağılım (Cuma kapanan haftalar): satış ayın tamamına mı, birkaç haftaya mı yayıldı; erimenin
        # satış dışındaki kısmının altının fiyatından gelip gelmediği haftalık altın fiyat etkisiyle sorulur
        # Haftanın erimesi aynı etiketlerin L → L+1 stok değişimlerinin toplamıdır (satış ve altın etkisiyle aynı
        # pencere): haftanın işlemleri, haftanın ilk gününden sonraki haftanın ilk gününe kadarki bilançoda görünür
        hf = ic[["net_doviz_alimi"]].copy()
        if "altin_fiyat_etkisi" in ic:
            hf["altin"] = ic["altin_fiyat_etkisi"]
        hf["sw"] = ileri.reindex(ic.index)
        haftalar = []
        for son_gun, grp in hf.groupby(pd.Grouper(freq="W-FRI")):
            if grp.empty:
                continue
            hafta = {"ilk": grp.index[0].strftime("%Y-%m-%d"), "son": grp.index[-1].strftime("%Y-%m-%d"),
                     "doviz_satisi": float(grp["net_doviz_alimi"].sum()),
                     "swap_haric_degisim": float(grp["sw"].sum()) if grp["sw"].notna().all() else None}
            if "altin" in grp:
                hafta["altin_fiyat_etkisi"] = float(grp["altin"].sum())
            haftalar.append(hafta)
        kayit["haftalik"] = haftalar
        # pencerenin dışına taşan dip: şokun ilk günü ile 60 iş günü sonrası arasında en düşük değer
        uzun = r.loc[b:].iloc[:61]
        kayit["swap_haric_donem_dip"] = float(uzun["swap_haric_net_rezerv_usd"].min())
        kayit["swap_haric_donem_dip_gun"] = uzun["swap_haric_net_rezerv_usd"].idxmin().strftime("%Y-%m-%d")
        out[ad] = kayit
    x = f.loc["2026-03-01":BAZ_GUN, "fon_ihale"]
    kapali = x[x <= 0]
    acilis = x[(x > 0) & (x.index > kapali.index[0])]
    ara = pd.Timestamp(out["2026-03"]["ihale_ara_ilk"])
    # ara verildiği gün (stokun ilk düştüğü gün) → yeniden açıldığı gün; aradaki iş günleri ihalesiz
    out["ust_bant_2026"] = {"ara": out["2026-03"]["ihale_ara_ilk"], "sifir": kapali.index[0].strftime("%Y-%m-%d"),
                            "acilis": acilis.index[0].strftime("%Y-%m-%d"),
                            "is_gunu": int(len(f.loc[ara:acilis.index[0]]) - 1)}
    rs = r.dropna(subset=["net_rezerv_usd"])
    son = rs.iloc[-1]
    out["rezerv_bugun"] = {"gun": rs.index[-1].strftime("%Y-%m-%d"), "net": float(son["net_rezerv_usd"]),
                           "swap_haric": float(son["swap_haric_net_rezerv_usd"]), "brut": float(son["brut_usd"])}
    out["mart_2026_doviz_satisi"] = float(r.loc["2026-03-01":"2026-03-31", "net_doviz_alimi"].sum())
    fs = f.dropna(subset=["tlref"]).iloc[-1]
    out["fonlama_bugun"] = {"gun": f.dropna(subset=["tlref"]).index[-1].strftime("%Y-%m-%d"), "tlref": float(fs["tlref"]),
                            "politika": float(f["politika"].dropna().iloc[-1]), "koridor_ust": float(f["koridor_ust"].dropna().iloc[-1]),
                            "koridor_alt": float(f["koridor_alt"].dropna().iloc[-1]), "aofm": float(f["aofm"].dropna().iloc[-1])}
    dd = d.dropna(subset=["n2y"]).iloc[-1]
    out["dibs_bugun"] = {"gun": d.dropna(subset=["n2y"]).index[-1].strftime("%Y-%m-%d"),
                         **{c: float(dd[c]) for c in ("n3a", "n1y", "n2y", "n5y", "be_2y", "r2y") if c in dd and pd.notna(dd[c])}}
    return out


def tufe_gecis() -> dict:
    """Akaryakıt ve enerji TÜFE kalemlerinin Brent'e (dolar) ve kura esnekliği:
    aylık log değişim, aynı ay + bir ay gecikme. Brent'in TL fiyatı iki bacağa
    ayrılır — kur bacağının katsayısı genel kur geçişkenliğini de taşır ve petrol
    şokunun ölçüsü değildir; senaryo yalnız dolar bacağını oynatır."""
    k = tablo("tufe_kalem_aylik")
    sp = brent_fiziki()
    vu = brent_vadeli_uzun()
    p = tablo("piyasa_2026")["BZ=F"].dropna()
    vad = pd.concat([vu[vu.index < p.index[0]], p]).sort_index()
    u = tablo("usdtry_tcmb_1990")["usdtry_tcmb_valor"]
    um = np.log(u.resample("MS").mean()).diff() * 100
    out = {}
    for fiyat_ad, fiyat in (("vadeli", vad), ("fiziki", sp)):
        bm = np.log(fiyat.resample("MS").mean()).diff() * 100
        for kalem in ("akaryakit", "motorin", "benzin", "enerji", "dogalgaz", "elektrik", "tufe"):
            if kalem not in k:
                continue
            y = np.log(k[kalem]).diff() * 100
            for donem in (("2005", "2026"), ("2018", "2026")):
                D = pd.DataFrame({"y": y, "b0": bm, "b1": bm.shift(1), "k0": um, "k1": um.shift(1)}).loc[donem[0]:donem[1]].dropna()
                X = np.column_stack([np.ones(len(D)), D.b0, D.b1, D.k0, D.k1])
                b, V = ekk(D.y.values, X)
                out[f"{fiyat_ad}:{kalem}:{donem[0]}"] = {
                    "brent_0_1": float(b[1] + b[2]), "se": float(np.sqrt(V[1, 1] + V[2, 2] + 2 * V[1, 2])),
                    "ayni_ay": float(b[1]), "kur_0_1": float(b[3] + b[4]), "n": int(len(D)),
                    "ilk": D.index[0].strftime("%Y-%m"), "son": D.index[-1].strftime("%Y-%m")}
    son = k.dropna(subset=["motorin"]).index[-1]
    out["son_ay"] = son.strftime("%Y-%m")
    out["haziran_eylul"] = {kk: float((k.loc[son, kk] / k.loc["2026-06-01", kk] - 1) * 100)
                            for kk in ("motorin", "benzin", "akaryakit", "enerji", "tufe") if kk in k}
    out["eylul_aylik"] = {kk: float((k.loc[son, kk] / k.loc[son - pd.DateOffset(months=1), kk] - 1) * 100)
                          for kk in ("motorin", "benzin", "akaryakit", "enerji", "tufe") if kk in k}
    return out


def enerji_faturasi() -> dict:
    """Yakıt ithalatı birim değerinin Brent'e esnekliği (TÜİK dış ticaret endeksi; 0–6 ay)
    ve ödemeler dengesinin enerji kalemleri. Sabit hacimle ölçekleme bir ÜST SINIR fikri
    verir, öngörü değildir: hacim ve bileşim fiyatla değişir."""
    o = tablo("odemeler_aylik")
    t = tablo("dis_ticaret_endeks")
    sp = brent_fiziki()
    vu = brent_vadeli_uzun()
    p = tablo("piyasa_2026")["BZ=F"].dropna()
    vad = pd.concat([vu[vu.index < p.index[0]], p]).sort_index()
    out = {}
    uv = np.log(t["ith_yakit_birim_deger"]).diff() * 100
    bm = np.log(vad.resample("MS").mean()).diff() * 100
    D = pd.DataFrame({"uv": uv, **{f"b{L}": bm.shift(L) for L in range(7)}}).dropna()
    X = np.column_stack([np.ones(len(D))] + [D[f"b{L}"] for L in range(7)])
    b, V = ekk(D.uv.values, X)
    out["birim_deger_esneklik"] = {"toplam_0_6": float(b[1:].sum()), "se": float(np.sqrt(V[1:, 1:].sum())),
                                   "ilk_ay_0_1": float(b[1:3].sum()), "ilk_3_ay": float(b[1:5].sum()),
                                   "n": int(len(D)), "ilk": D.index[0].strftime("%Y-%m"), "son": D.index[-1].strftime("%Y-%m")}
    t12 = o[["hc_enerji_ith", "hc_enerji_ihr", "hc_enerji_net", "cari"]].rolling(12).sum() / 1000
    son = t12.dropna().index[-1]
    out["son_ay"] = son.strftime("%Y-%m")
    out["ithalat_12a"] = float(t12.loc[son, "hc_enerji_ith"])
    out["ihracat_12a"] = float(t12.loc[son, "hc_enerji_ihr"])
    out["net_12a"] = float(-t12.loc[son, "hc_enerji_net"])
    out["cari_12a"] = float(t12.loc[son, "cari"])
    b12 = vad.resample("MS").mean().rolling(12).mean()
    f12 = sp.resample("MS").mean().rolling(12).mean()
    out["brent_12a_ort_vadeli"] = float(b12.loc[son])
    out["brent_12a_ort_fiziki"] = float(f12.loc[son])
    # GSYH (dolar): son dört çeyrek TL GSYH / aynı dönemin ortalama TCMB kuru
    g = tablo("gsyh_ceyreklik")["gsyh_cari_bin_tl"].dropna()
    u = tablo("usdtry_tcmb_1990")["usdtry_tcmb_valor"]
    son4 = g.iloc[-4:]
    kur = u.loc[son4.index[0] - pd.offsets.QuarterBegin(startingMonth=1):son4.index[-1]].mean()
    gsyh_usd = float(son4.sum() * 1000 / kur / 1e9)
    out["gsyh_milyar_usd"] = gsyh_usd
    out["gsyh_son_ceyrek"] = son4.index[-1].strftime("%Y-%m")
    out["cari_gsyh"] = out["cari_12a"] / gsyh_usd * 100
    # ÖLÇÜLEN KURAL: aylık net enerji faturası (mn USD) ~ Brent'in aylık ortalaması (0–6 ay gecikme),
    # ay kuklalarıyla (kış gazı). Gecikme katsayılarının toplamı × 12 × 10 = Brent'in kalıcı 10 dolar
    # artışının YILLIK faturaya etkisi. İkinci tanımda Avrupa gazı (Pink Sheet) da girer: Brent'in
    # katsayısı gaz fiyatı sabitken petrolün kendi payıdır (petrole endeksli boru gazı sözleşmeleri
    # bu payın içinde kalır — ayrıştırılamaz).
    pk = tablo("pink_aylik")
    pm = vad.resample("MS").mean()
    pf = sp.resample("MS").mean()
    # Fatura FİZİKİ kargoyu öder (Bölüm 1): kural fiziki Brent'le de kurulur ve bugünkü fiziki fiyatla
    # ölçeklenir — vadeliyle kurulan kural, fiziki primin rekor olduğu bir ayda faturayı eksik sayar.
    for ad, bas, gazli, fiyat in (("2010", "2010-01-01", False, pm), ("2016", "2016-01-01", False, pm),
                                  ("2010_gazli", "2010-01-01", True, pm), ("2010_fiziki", "2010-01-01", False, pf),
                                  ("2010_gazli_fiziki", "2010-01-01", True, pf)):
        y = -o["hc_enerji_net"]
        cols = {f"p{L}": fiyat.shift(L) for L in range(7)}
        if gazli:
            cols.update({f"g{L}": pk["avrupa_gaz"].shift(L) for L in range(7)})
        F = pd.DataFrame({"y": y, **cols}).loc[bas:].dropna()
        ay = pd.get_dummies(F.index.month, prefix="ay", drop_first=True).astype(float).values
        regs = [c for c in F.columns if c != "y"]
        X = np.column_stack([np.ones(len(F)), F[regs].values, ay])
        b, V = ekk(F.y.values, X)
        k = 7
        top = float(b[1:1 + k].sum())
        se = float(np.sqrt(V[1:1 + k, 1:1 + k].sum()))
        out[f"kural_{ad}"] = {"milyar_usd_yillik_10_dolar": top * 12 * 10 / 1000, "se": se * 12 * 10 / 1000,
                              "n": int(len(F)), "ilk": F.index[0].strftime("%Y-%m"), "son": F.index[-1].strftime("%Y-%m")}
        # kuralın yayımlanacak İLK ayın (13 Ekim'de Ağustos) faturası için beklediği değer: izleme listesinin
        # ölçütü — 12 aylık birikimin büyümesi kuralı sınamaz (bir yıl önceki ay zaten düşüktü)
        sonraki = F.index[-1] + pd.DateOffset(months=1)
        tum_ = pd.DataFrame(cols)
        if sonraki in tum_.index and tum_.loc[sonraki, regs].notna().all() and len(set(F.index.month)) == 12:
            z = np.concatenate([[1.0], tum_.loc[sonraki, regs].values.astype(float),
                                [float(sonraki.month == j) for j in range(2, 13)]])
            if len(z) == len(b):
                out[f"kural_{ad}"]["sonraki_ay"] = sonraki.strftime("%Y-%m")
                out[f"kural_{ad}"]["sonraki_ay_tahmin_milyar"] = float(z @ b) / 1000
                gy = sonraki - pd.DateOffset(years=1)
                if gy in o.index and pd.notna(o.loc[gy, "hc_enerji_net"]):
                    out[f"kural_{ad}"]["gecen_yil_ayni_ay_milyar"] = float(-o.loc[gy, "hc_enerji_net"]) / 1000
    e = out["birim_deger_esneklik"]["toplam_0_6"]
    sen = {}
    for ad, h in {"bugun": float(p.loc[BAZ_GUN]), **SENARYO}.items():
        olcek = (h / out["brent_12a_ort_vadeli"]) ** e
        net = out["net_12a"] * olcek
        sen[ad] = {"brent": h, "net_fatura": net, "ek_fatura": net - out["net_12a"],
                   "cari_gsyh": (out["cari_12a"] - (net - out["net_12a"])) / gsyh_usd * 100}
    out["senaryo_12ay"] = sen
    return out


def yabanci_akim() -> dict:
    """Yurt dışı yerleşiklerin DİBS ve hisse akımı iki şokta: şok öncesi son haftadan birikimli
    akımın dibine (on hafta içinde). Hafta cuma günüyle tarihli; birikim bu yazının penceresinde
    yeniden toplanır (hattın kendi birikim sütunu kullanılmaz)."""
    y = tablo("yabanci_haftalik")
    out = {}
    for ad, bas in (("2025-03", "2025-03-14"), ("2026-03", "2026-02-27")):
        b = pd.Timestamp(bas)
        sonraki = y.loc[b + pd.Timedelta(days=1): b + pd.Timedelta(weeks=10)]
        cum = sonraki.cumsum()
        dip = cum["dibs"].idxmin()
        out[ad] = {"bas": bas, "dip_hafta": dip.strftime("%Y-%m-%d"), "hafta": int(len(cum.loc[:dip])),
                   "dibs": float(cum.loc[dip, "dibs"]), "hisse": float(cum.loc[dip, "hisse"]),
                   "toplam": float(cum.loc[dip, "toplam"]),
                   "ilk_4_hafta_dibs": float(sonraki["dibs"].iloc[:4].sum())}
        out[ad]["ilk_4_hafta_pay"] = out[ad]["ilk_4_hafta_dibs"] / out[ad]["dibs"] * 100
    dip26 = pd.Timestamp(out["2026-03"]["dip_hafta"])
    geri = y.loc[dip26 + pd.Timedelta(days=1):]
    out["geri_donus_2026"] = {"bas": dip26.strftime("%Y-%m-%d"), "son": y.index[-1].strftime("%Y-%m-%d"),
                              "dibs": float(geri["dibs"].sum()), "hisse": float(geri["hisse"].sum()),
                              "hafta": int(len(geri))}
    out["geri_donus_2026"]["dibs_geri_pay"] = out["geri_donus_2026"]["dibs"] / -out["2026-03"]["dibs"] * 100
    out["son_4_hafta"] = {"son": y.index[-1].strftime("%Y-%m-%d"), "dibs": float(y["dibs"].iloc[-4:].sum()),
                          "hisse": float(y["hisse"].iloc[-4:].sum())}
    return out


def abd_enflasyon() -> dict:
    """ABD manşet TÜFE'nin Brent'e esnekliği (aylık, 0–2 ay) ve pompa benzininin
    varil fiyatına geçişi (haftalık, EIA). Senaryo: aynı oran üç ay boyunca kalırsa."""
    k = tablo("kuresel_aylik")
    vu = brent_vadeli_uzun()
    p = tablo("piyasa_2026")["BZ=F"].dropna()
    vad = pd.concat([vu[vu.index < p.index[0]], p]).sort_index()
    bm = np.log(vad.resample("MS").mean()).diff() * 100
    D = pd.DataFrame({"h": np.log(k["abd_tufe"]).diff() * 100, "c": np.log(k["abd_cekirdek"]).diff() * 100,
                      "b0": bm, "b1": bm.shift(1), "b2": bm.shift(2)}).dropna()
    out = {}
    for bas in ("2000", "2015"):
        d = D.loc[bas:]
        X = np.column_stack([np.ones(len(d)), d.b0, d.b1, d.b2])
        for y, ad in (("h", "manset"),):
            b, V = ekk(d[y].values, X)
            out[f"{ad}_{bas}"] = {"toplam": float(b[1:].sum()), "se": float(np.sqrt(V[1:, 1:].sum())), "n": int(len(d)),
                                  "son": d.index[-1].strftime("%Y-%m")}
    pm = tablo("eia_pompa_haftalik")["abd_benzin_pompa_haftalik"].dropna()
    w = vad.resample("W-MON").last()
    E = pd.DataFrame({"p": pm.diff(4), "b": (w.diff(4) / 42).reindex(pm.index, method="nearest", tolerance=pd.Timedelta(days=3))}).dropna()
    E = E.loc["2005":]
    X = np.column_stack([np.ones(len(E)), E.b])
    b, V = ekk(E.p.values, X)
    out["benzin_pompa_gecis"] = {"galon_basina_dolar_per_galon": float(b[1]), "se": float(np.sqrt(V[1, 1])),
                                 "n": int(len(E)), "ilk_hafta": E.index[0].strftime("%Y-%m-%d"),
                                 "son_hafta": pm.index[-1].strftime("%Y-%m-%d"), "son_fiyat": float(pm.iloc[-1])}
    # Motorin pompası aynı tanımla (dört haftalık fark; Brent'in galon karşılığı). Motorinin ham petrolden
    # ayrışan rafineri marjı bu denklemde yok — 2026'da distilat marjının yükselişi artıkta kalır.
    dm = tablo("eia_pompa_haftalik")["abd_motorin_pompa_haftalik"].dropna()
    E2 = pd.DataFrame({"p": dm.diff(4), "b": (w.diff(4) / 42).reindex(dm.index, method="nearest", tolerance=pd.Timedelta(days=3))}).dropna()
    E2 = E2.loc["2005":]
    b2, V2 = ekk(E2.p.values, np.column_stack([np.ones(len(E2)), E2.b]))
    out["motorin_pompa_gecis"] = {"galon_basina_dolar_per_galon": float(b2[1]), "se": float(np.sqrt(V2[1, 1])),
                                  "n": int(len(E2)), "ilk_hafta": E2.index[0].strftime("%Y-%m-%d"),
                                  "son_hafta": dm.index[-1].strftime("%Y-%m-%d"), "son_fiyat": float(dm.iloc[-1]),
                                  "rekor": float(dm.max()), "rekor_hafta": dm.idxmax().strftime("%Y-%m-%d")}
    out["benzin_pompa_gecis"]["rekor"] = float(pm.max())
    out["benzin_pompa_gecis"]["rekor_hafta"] = pm.idxmax().strftime("%Y-%m-%d")
    return out


def abd_senaryo(ae: dict, yer: dict) -> dict:
    """Senaryonun ABD pompasına ve manşet TÜFE'sine geçişi. Pompa: dört haftalık geçiş katsayısı × Brent'in
    varil başına artışı / 42 (ön vade, bugünkü 104,72'den). TÜFE: aylık esneklik (0–2 ay) × ön vadenin log
    değişimi — fiyat SEVİYESİNE etki, yıllık enflasyona değil; fiyat üç ay o düzeyde kalırsa."""
    out = {}
    for ad, s in yer["senaryo"].items():
        d = s["hedef"] - yer["baz"]
        sat = {"brent_artis": d}
        for k in ("benzin", "motorin"):
            g = ae[f"{k}_pompa_gecis"]
            sat[k] = {"artis": g["galon_basina_dolar_per_galon"] * d / 42,
                      "seviye": g["son_fiyat"] + g["galon_basina_dolar_per_galon"] * d / 42}
        sat["tufe_seviye_2000"] = ae["manset_2000"]["toplam"] * s["log"]
        sat["tufe_seviye_2015"] = ae["manset_2015"]["toplam"] * s["log"]
        out[ad] = sat
    return out


# ─────────────────────────────────────────────────────────────── F — senaryo tablosu ve hüküm
ESLE_UZUN = {"^GSPC": "spx", "^VIX": "vix", "DX-Y.NYB": "dxy", "us2y": "us2y", "us10y": "us10y", "GC=F": "altin",
             "USDJPY=X": "jpy", "EURUSD=X": "eur", "GBPUSD=X": "gbp", "^GDAXI": "dax", "^N225": "n225",
             "XU100.IS": "bist100", "bist_usd": "bist_usd", "USDTRY=X": "try_tcmb"}


def kanit_ayrinti(rejim: dict, loo: dict, tum: dict, k: str) -> dict:
    """HÜKÜM KODDA. Üç sınama, mekanik:
    (1) 2026 içi bir-pencere-dışarıda: işaret en az 3/4 tutuyor VE tahmin hatası "hiçbir şey olmaz"
        (sıfır) tahmininkinden küçük — geçmeyen ZAYIF;
    (2) görüşsüz kıyas: doğrunun hatası, Brent'in büyüklüğünü kullanmayan tahmininkinden (kalemin
        eğitimde Brent'in yükseldiği günlerdeki ortalama değişimi — 2026'nın kendi eğilimi) küçük;
    (3) uzun tarihçesi olan kalemlerde 2026 öncesi pencerelerden 2026'ya: işaret en az 3/4.
    (1)'i geçip (2)'yi ya da (3)'ü geçemeyen ORTA; üçünü de (ya da (3) yapılamıyorsa ilk ikisini) geçen GÜÇLÜ.
    Bir sınamanın sonucu hükmü değiştirdiğinde gerekçesi okura adıyla yazılır (orta_sebep)."""
    L = loo.get(k)
    o = tum["orneklem_disi_2026"].get(ESLE_UZUN.get(k, ""))
    d = {"ikinci_sinama": o is not None, "orta_sebep": []}
    if not L or L["isaret_tutan"] < 3 or L["rmse"] >= L["rmse_sifir"]:
        d["hukum"] = "zayif"
        return d
    if L["rmse"] >= L["rmse_egilim"]:
        d["orta_sebep"].append("egilim")
    if o is not None and o["isaret_tutan"] < 3:
        d["orta_sebep"].append("gecmis")
    d["hukum"] = "orta" if d["orta_sebep"] else "guclu"
    return d


def kanit(rejim: dict, loo: dict, tum: dict, k: str) -> str:
    return kanit_ayrinti(rejim, loo, tum, k)["hukum"]


def senaryo_tablosu(yer: dict, rejim: dict, loo: dict, tum: dict) -> dict:
    out = {}
    pen = rejim["pencereler"]
    for k, v in rejim["varlik"].items():
        if k == "BZ=F":
            continue
        yk = v["yukselis"]
        ka = kanit_ayrinti(rejim, loo, tum, k)
        sat = {"ad": v["ad"], "grup": v["grup"], "birim": v["birim"], "son_deger": v["son_deger"], "son_gun": v["son_gun"],
               "kanit": ka["hukum"], "kanit_ayrinti": ka, "egim": yk["egim"], "se": yk["se"], "sabit": yk["sabit"],
               "ortalama_21g": v.get("ortalama_21g"), "yatay_brent_ortalama": v.get("yatay_brent_ortalama")}
        for ad, s in yer["senaryo"].items():
            x = s["log_devirsiz"] if s.get("log_devirsiz") is not None else s["log"]
            orta = yk["sabit"] + yk["egim"] * x
            # %90 bant: doğrunun x'teki belirsizliği (sabit, eğim ve ikisinin kovaryansı — Newey–West) ve
            # tek bir pencerenin artık oynaklığı birlikte: tek bir ayın sonucu doğrunun kendisinden geniştir
            bant = 1.645 * math.sqrt(max(0.0, yk["se_sabit"] ** 2 + (yk["se"] * x) ** 2 + 2 * x * yk["kov"])
                                     + yk["artik_sd"] ** 2)
            # petrolün payı = eğim × x; sabit (2026'nın Brent'ten bağımsız eğilimi) ayrıca okunur — S&P 500'de
            # ikisi neredeyse birbirini götürüyor ve tek sayı "petrol hisseyi etkilemiyor" diye yanlış okunurdu
            sat[ad] = {"orta": orta, "alt": orta - bant, "ust": orta + bant, "x": x, "petrol_payi": yk["egim"] * x}
            if v["birim"] == "log":
                sat[ad].update({"orta_yuzde": yuzde(orta), "alt_yuzde": yuzde(orta - bant), "ust_yuzde": yuzde(orta + bant)})
            # seviye: bugünkü değerden — log birim çarpanla, baz puan yüzde puana, fark doğrudan
            s0 = v["son_deger"]
            cev = {"log": lambda m: s0 * math.exp(m / 100), "bp": lambda m: s0 + m / 100, "fark": lambda m: s0 + m}[v["birim"]]
            sat[ad].update({"seviye": cev(orta), "seviye_alt": cev(orta - bant), "seviye_ust": cev(orta + bant)})
        # ÜÇÜNCÜ KOŞUL — devir farkı: x (devirsiz endeksin hedefe değişimi) ön vadenin seviye değişimi ARTI
        # 30 Ekim devrindeki Aralık–Ocak farkıdır; tablolar bugünkü farkı (3,37) varsayar. 2026'nın en geniş
        # devir farkıyla (sıkışmanın eğrinin önünü dikleştirdiği gün) 125 dolarlık hücre ne olurdu:
        bos = (rejim.get("devir") or {}).get("wti_bosluk_2026") or {}
        if bos:
            g = max(bos, key=lambda q: abs(bos[q]))
            x_alt = yer["senaryo"]["125"]["log"] + abs(bos[g])
            o_alt = yk["sabit"] + yk["egim"] * x_alt
            sat["duyarlilik_125"] = {"x": x_alt, "devir_gunu": g, "devir_farki": abs(bos[g]), "orta": o_alt,
                                     "orta_yuzde": yuzde(o_alt) if v["birim"] == "log" else None}
        # en yakın büyüklükteki 2026 pencereleri: 125 ↔ Mayıs ve Eylül (Brent ≈ +21), 150 ↔ Mart (≈ +47)
        sat["mart"] = v["pencere"][0] if pen else None
        sat["mayis_eylul"] = [v["pencere"][1], v["pencere"][3]] if len(pen) >= 4 else None
        sat["pencere"] = v["pencere"]
        dolu = [p for p in v["pencere"] if p is not None]
        sat["pencere_isaret"] = {"arti": sum(p > 0 for p in dolu), "eksi": sum(p < 0 for p in dolu), "n": len(dolu)}
        out[k] = sat
    return out


def tufe_aktarim(yer: dict, tg: dict, st: dict) -> dict:
    """Senaryonun akaryakıt ve TÜFE kalemlerine iki aylık geçişi: kalem esnekliği (2005+, aynı ay +
    bir ay gecikme) × Brent'in dolar bacağı (ön vade log değişimi — pompa fiyatı yakın vade ürün
    fiyatını izler) + kur esnekliği × USD/TRY'nin 2026 rejimindeki orta değeri. ÖTV ve eşel mobil
    kararları HESABIN DIŞINDADIR: esneklik 2005–2026 ortalamasıdır ve iki eşel mobil dönemini de içerir.
    12 aylık satır TCMB'nin yayımlanmış kuralıdır (Brent'te %10 → TÜFE'de 1 puan; Eren ve diğ., 2025)."""
    out = {"donem": f"{tg['vadeli:tufe:2005']['ilk'][:4]}–{tg['vadeli:tufe:2005']['son'][:4]}", "senaryo": {}}
    kur = {ad: st["USDTRY=X"][ad]["orta"] for ad in SENARYO}
    out["kur_varsayimi"] = kur["125"]
    out["kur_varsayimi_150"] = kur["150"]
    # PETROLÜN PAYI ile KURUN PAYI ayrı yazılır: USD/TRY'nin 2026 rejimindeki orta değeri neredeyse
    # tamamen sabittir (eğim ≈ 0 — yönetilen patika), yani kur bacağı petrol olmasa da gelecek olan aylık
    # değer kaybıdır. Senaryonun etkisi YALNIZ petrol bacağıdır; kurlu toplam pompanın TL fiyatını anlatır.
    for ad, s in yer["senaryo"].items():
        kalem, kalem_kurlu = {}, {}
        for k in ("motorin", "benzin", "akaryakit", "enerji", "tufe"):
            e = tg[f"vadeli:{k}:2005"]
            kalem[k] = (math.exp(e["brent_0_1"] * s["log"] / 100) - 1) * 100
            kalem_kurlu[k] = (math.exp((e["brent_0_1"] * s["log"] + e["kur_0_1"] * kur[ad]) / 100) - 1) * 100
        out["senaryo"][ad] = {"kalem": {k: v for k, v in kalem.items() if k != "tufe"},
                              "kalem_kurlu": {k: v for k, v in kalem_kurlu.items() if k != "tufe"},
                              "tufe_2ay_petrol": tg["vadeli:tufe:2005"]["brent_0_1"] * s["log"],
                              "tufe_2ay_kurlu": kalem_kurlu["tufe"],
                              "tufe_2ay_kur_payi": tg["vadeli:tufe:2005"]["kur_0_1"] * kur[ad],
                              "tufe_12ay_tcmb": s["yuzde"] / 10 * 1.0,
                              # TCMB blogunun Temmuz 2025 yazısı: bir yılın sonunda %10 → yaklaşık 0,8 puan
                              "tufe_12ay_tcmb_2025": s["yuzde"] / 10 * 0.8}
    return out


LITRE_VARIL = 158.987294928    # 42 ABD galonu
LITRE_GALON = 3.785411784


def otv_kararlari() -> dict:
    """Resmî Gazete'deki iki ÖTV kararının tabloları (`veri/otv_kararlar.json`; PDF'ler taranmış görüntü,
    tablolar sayfadan okundu). Kaydın özü üretim künyesine girer: tablo elle aktarıldığı için kapı (dogrula.py)
    kaydın PDF özlerini bulut künyesiyle ve ölçümün bu kayıtla üretildiğini ayrıca sorar."""
    return json.loads((VERI / "otv_kararlar.json").read_text(encoding="utf-8"))


def otv_tutari(kr: dict, urun: str, gun: str) -> float | None:
    for k in kr["kararlar"]:
        for u in k["urunler"]:
            if u["ad"] != urun:
                continue
            for d in u["donemler"]:
                if d["bas"] <= gun and (d["son"] is None or gun <= d["son"]):
                    return float(d["otv"])
    return None


def otv_tampon(yer: dict, st: dict) -> dict:
    """Senaryonun pompaya gelen maliyeti ile yürürlükteki ÖTV'nin karşılaştırması — litre başına, KDV HARİÇ
    (KDV ikisine de aynı oranla eklenir; kıyas orandan bağımsızdır).
    · Ham petrol bacağı (rafineri marjı sabit): ön vadenin varil başına artışı / 158,99 litre × senaryonun kuru.
    · Ürün bacağı (marj 2026'daki gibi ham petrolle orantılı açılırsa): ABD motorin (ULSD) ve benzin (RBOB)
      vadelisinin senaryodaki dolar artışı / 3,785 litre × kur. ABD vadelisi Akdeniz ürün fiyatının vekilidir.
    · Tampon: eşel mobil yeniden açılsaydı vergi indirimiyle karşılanabilecek azami tutar = yürürlükteki ÖTV.
    · Takvim adımı: 1 Kasım'da kararın kendisinin getirdiği ÖTV artışı (senaryo ayının içinde, petrolden bağımsız).
    Pompa fiyatının kendisi (TL/litre) ölçülen katmanda yok; oran pompa fiyatına göre değil, vergiye göre kurulur."""
    kr = otv_kararlari()
    hedef = yer["hedef_gun"]
    kur0 = st["USDTRY=X"]["son_deger"]
    out = {"baz_gun": BAZ_GUN, "hedef_gun": hedef, "kur_bugun": kur0,
           "litre_basina_10_dolar": 10 / LITRE_VARIL * kur0, "otv": {}, "senaryo": {}}
    for urun in ("motorin", "kurşunsuz benzin 95 oktan"):
        a, b = otv_tutari(kr, urun, BAZ_GUN), otv_tutari(kr, urun, hedef)
        out["otv"][urun] = {"baz": a, "hedef": b, "adim": b - a,
                            "kasim": otv_tutari(kr, urun, "2026-11-15"), "aralik": otv_tutari(kr, urun, "2026-12-15"),
                            "dolar_karsiligi_baz": a / (kur0 / LITRE_VARIL),      # bugünkü ÖTV kaç dolarlık Brent'i tamponlar
                            "dolar_karsiligi_hedef": b / (kur0 / LITRE_VARIL)}
    out["otv"]["motorin"]["agustos"] = otv_tutari(kr, "motorin", "2026-08-20")
    out["otv"]["motorin"]["ocak27"] = otv_tutari(kr, "motorin", "2027-01-15")
    for ad, s in yer["senaryo"].items():
        kur = st["USDTRY=X"][ad]["seviye"]
        d = s["hedef"] - yer["baz"]
        ho, rb = st["HO=F"], st["RB=F"]
        sat = {"kur": kur, "brent_artis_varil": d,
               "ham_tl_litre": d / LITRE_VARIL * kur,
               "motorin_urun_tl_litre": (ho[ad]["seviye"] - ho["son_deger"]) / LITRE_GALON * kur,
               "benzin_urun_tl_litre": (rb[ad]["seviye"] - rb["son_deger"]) / LITRE_GALON * kur,
               "motorin_urun_artis_galon": ho[ad]["seviye"] - ho["son_deger"],
               "benzin_urun_artis_galon": rb[ad]["seviye"] - rb["son_deger"]}
        m, bz = out["otv"]["motorin"], out["otv"]["kurşunsuz benzin 95 oktan"]
        sat["motorin_tampon_kasim_ham"] = m["hedef"] / sat["ham_tl_litre"]
        sat["motorin_tampon_kasim_urun"] = m["hedef"] / sat["motorin_urun_tl_litre"]
        sat["benzin_tampon_kasim_ham"] = bz["hedef"] / sat["ham_tl_litre"]
        sat["benzin_tampon_kasim_urun"] = bz["hedef"] / sat["benzin_urun_tl_litre"]
        # vergi indirimi yapılmazsa senaryo ayında KDV hariç litre başına toplam artış: petrol + takvim adımı
        sat["motorin_toplam_ham"] = sat["ham_tl_litre"] + m["adim"]
        sat["motorin_toplam_urun"] = sat["motorin_urun_tl_litre"] + m["adim"]
        sat["benzin_toplam_ham"] = sat["ham_tl_litre"] + bz["adim"]
        sat["benzin_toplam_urun"] = sat["benzin_urun_tl_litre"] + bz["adim"]
        out["senaryo"][ad] = sat
    return out


def kaynak_uyumu() -> dict:
    """Bülten piyasa fotoğrafının Brent'i (Yahoo BZ=F) ile CNBC ön vade Brent'in örtüşen günlerdeki farkı:
    2026 penceresinde bülten serisi, öncesi CNBC — iki kaynağın birleşiminde ek bir kırılma olmamalı."""
    p = tablo("piyasa_2026")["BZ=F"].dropna()
    c = brent_vadeli_uzun()
    ort = p.index.intersection(c.index)
    fark = (p.loc[ort] / c.loc[ort] - 1).abs() * 100
    return {"ortak_gun": int(len(ort)), "azami_fark_yuzde": float(fark.max()), "ilk": ort[0].strftime("%Y-%m-%d"),
            "son": ort[-1].strftime("%Y-%m-%d"), "birebir_pay": float((fark < 1e-4).mean() * 100)}


def enerji_kural_senaryo(ef: dict, yer: dict, fiziki_son: float | None = None) -> dict:
    """Ölçülen kuralla yıllık ek fatura: (fiyat − son 12 ayın Brent ortalaması)/10 × kural. İki kural:
    gaz fiyatı sabitken petrolün payı (2010+, ≈ TCMB'nin 2,6'sı) ve gaz da birlikte yükselirse
    (2010+, gazsız denklem). Hacim sabit — bir YIL o fiyatta kalırsa; öngörü değildir."""
    out = {}
    b12 = ef["brent_12a_ort_vadeli"]
    for ad, h in {"bugun": yer["baz"], **SENARYO}.items():
        sat = {"brent": h}
        for kural, anahtar in (("petrol", "kural_2010_gazli"), ("petrol_gaz", "kural_2010")):
            ek = ef[anahtar]["milyar_usd_yillik_10_dolar"] * (h - b12) / 10
            sat[kural] = {"ek": ek, "cari_gsyh": (ef["cari_12a"] - ek) / ef["gsyh_milyar_usd"] * 100}
        out[ad] = sat
    # Fatura fiziki kargoyu öder: fiziki Brent'le kurulan kural, bugünkü fiziki fiyatla (6 Ekim) ve fiziki
    # Brent'in son 12 aylık ortalamasından — vadeliyle kurulan "bugün" satırının fiziki karşılığı
    fz = fiziki_son
    if fz:
        f12 = ef["brent_12a_ort_fiziki"]
        sat = {"brent": fz}
        for kural, anahtar in (("petrol", "kural_2010_gazli_fiziki"), ("petrol_gaz", "kural_2010_fiziki")):
            ek = ef[anahtar]["milyar_usd_yillik_10_dolar"] * (fz - f12) / 10
            sat[kural] = {"ek": ek, "cari_gsyh": (ef["cari_12a"] - ek) / ef["gsyh_milyar_usd"] * 100}
        out["bugun_fiziki"] = sat
    return out


def sekil_verisi(yer: dict) -> dict:
    """Figürlerin zaman serileri — figürler YALNIZ bu dosyadan çizer (sayıyı üreten yer tektir)."""
    def dz(s: pd.Series, b: int = 4) -> dict:
        s = s.dropna()
        return {"t": [x.strftime("%Y-%m-%d") for x in s.index], "v": [round(float(v), b) for v in s.values]}
    out = {}
    bas = "2025-10-01"
    sp = brent_fiziki()
    p = tablo("piyasa_2026")["BZ=F"].dropna()
    out["iki_brent"] = {"fiziki": dz(sp.loc[bas:]), "vadeli": dz(p.loc[bas:BAZ_GUN])}
    # 21 iş günlük değişimin dağılımı (vadeli, 1988+): 2,5 puanlık kovalar
    vu = brent_vadeli_uzun()
    s = pd.concat([vu[vu.index < p.index[0]], p]).sort_index()
    s = s[~s.index.duplicated(keep="last")]
    lr = pencere_log(s).dropna()
    kova = np.arange(-80, 82.5, 2.5)
    say, _ = np.histogram(lr.clip(-79.99, 79.99), bins=kova)
    out["dagilim"] = {"kova_alt": [float(x) for x in kova[:-1]], "gun": [int(x) for x in say], "n": int(len(lr)),
                      "ilk": lr.index[0].strftime("%Y-%m-%d"), "son": lr.index[-1].strftime("%Y-%m-%d"),
                      "son_deger": float(lr.iloc[-1])}
    f = tablo("fonlama_gunluk").loc[bas:BAZ_GUN]
    out["fonlama"] = {k: dz(f[k]) for k in ("tlref", "politika", "koridor_ust", "koridor_alt", "aofm")}
    r = tablo("rezerv_gunluk").loc[bas:BAZ_GUN]
    out["rezerv"] = {k: dz(r[k], 3) for k in ("net_rezerv_usd", "swap_haric_net_rezerv_usd", "net_doviz_alimi")}
    y = tablo("yabanci_haftalik").loc["2025-01-01":]
    out["yabanci"] = {"dibs": dz(y["dibs"].cumsum() / 1000, 3), "hisse": dz(y["hisse"].cumsum() / 1000, 3),
                      "bas": y.index[0].strftime("%Y-%m-%d")}
    d = tablo("dibs_gunluk").loc[bas:BAZ_GUN]
    out["dibs"] = {k: dz(d[k]) for k in ("n2y", "n5y", "be_2y", "r2y")}
    # Vade eğrisi üç günde: Mart zirvesinin son günü, eylül başı, yazının veri günü. Yahoo'da yalnız
    # arşiv günü LİSTELİ kontratlar var (Aralık 2026 ve sonrası) — Mart'ın kendi ön vadeleri (Mayıs,
    # Haziran 2026) silinmiş; o günün eğrisi Aralık 2026'dan başlar.
    k = tablo("egri_kontrat")
    ay_sira = "FGHJKMNQUVXZ"

    def teslim(c: str) -> str:
        return f"20{c[3:5]}-{ay_sira.index(c[2]) + 1:02d}"
    bz = sorted([c for c in k.columns if c.startswith("BZ")], key=teslim)
    egri = {}
    for g in ("2026-03-31", "2026-09-01", BAZ_GUN):
        sat = k.loc[:g].iloc[-1]
        egri[k.loc[:g].index[-1].strftime("%Y-%m-%d")] = {"teslim": [teslim(c) for c in bz if np.isfinite(sat[c])],
                                                           "fiyat": [round(float(sat[c]), 2) for c in bz if np.isfinite(sat[c])]}
    out["egri"] = egri
    on = tablo("piyasa_2026")["BZ=F"].dropna()
    out["egri_on_vade"] = {g: float(on.loc[:g].iloc[-1]) for g in egri}
    return out


def turkiye_ek() -> dict:
    """Türkiye bölümünün dört yan ölçüsü (inceleme turu 2):
    (1) TLREF'in koridorun üst bandını faiz kararı olmadan aştığı 2020 günleri — tavan bir tercih mi, sınır mı;
    (2) swap hariç net rezervin eksi olduğu dönem — stok sıfırda bir duvar değildir;
    (3) USD/TRY'nin repo ihalesinin kapalı kaldığı dönemdeki değişimi (İstanbul 18:00);
    (4) USD/TRY'nin son 21 iş günlük hızı ve o hız sürerse hedef gündeki seviyesi."""
    f = tablo("fonlama_gunluk")
    r = tablo("rezerv_gunluk")
    p = tablo("piyasa_2026")["USDTRY=X"].dropna()
    out = {}
    g = f.loc["2020", ["tlref", "koridor_ust"]].dropna()
    asim = g[g["tlref"] > g["koridor_ust"] + 1e-9]
    fark = (asim["tlref"] - asim["koridor_ust"]) * 100
    out["tlref_tavan_2020"] = {"gun": int(len(asim)), "ilk": asim.index[0].strftime("%Y-%m-%d"),
                               "son": asim.index[-1].strftime("%Y-%m-%d"), "azami_bp": float(fark.max()),
                               "azami_gun": fark.idxmax().strftime("%Y-%m-%d"),
                               "aylar": {k.strftime("%Y-%m"): int(v) for k, v in asim.groupby(asim.index.to_period("M")).size().items()}}
    sh = r["swap_haric_net_rezerv_usd"].dropna()
    eksi = sh[sh < 0]
    out["swap_haric_eksi"] = {"gun": int(len(eksi)), "ilk": eksi.index[0].strftime("%Y-%m-%d"),
                              "son": eksi.index[-1].strftime("%Y-%m-%d"), "asgari": float(eksi.min()),
                              "asgari_gun": eksi.idxmin().strftime("%Y-%m-%d")}
    b0, b1 = p.loc[:"2026-02-27"].index[-1], p.loc[:"2026-08-24"].index[-1]
    n = int(len(p.loc[b0:b1])) - 1
    lg = math.log(p.loc[b1] / p.loc[b0]) * 100
    out["usdtry_repo_kapali"] = {"bas": b0.strftime("%Y-%m-%d"), "son": b1.strftime("%Y-%m-%d"), "is_gunu": n,
                                 "yuzde": (p.loc[b1] / p.loc[b0] - 1) * 100, "log_21g": lg / n * UFUK}
    son = p.index[-1]
    l21 = math.log(p.iloc[-1] / p.iloc[-1 - UFUK]) * 100
    # Son 21 iş günü tek bir pencere: içindeki hafta sonu geçişlerinin sayısı hedef pencereninkinden farklı olabilir;
    # son üç ayın (63 iş günü) 21 güne ölçekli hızı ikinci bir ölçüdür (inceleme, turkiye-15)
    l63 = math.log(p.iloc[-1] / p.iloc[-1 - 3 * UFUK]) * 100 / 3
    out["usdtry_son21"] = {"son_gun": son.strftime("%Y-%m-%d"), "son": float(p.iloc[-1]), "log": l21,
                           "hedef_seviye": float(p.iloc[-1] * math.exp(l21 / 100)),
                           "log_63_21g": l63, "hedef_seviye_63": float(p.iloc[-1] * math.exp(l63 / 100)),
                           "bas_63": p.index[-1 - 3 * UFUK].strftime("%Y-%m-%d")}
    return out


def giris_kapanislari() -> dict:
    """Girişin günleri: 8 Ekim'in yükselişi ve aynı akşamki taahhütten sonra fiyatın kazancını koruyup korumadığı
    (ön vade kapanışı, devirden arındırılmamış — aynı kontrat, Aralık 2026)."""
    on = tablo("piyasa_2026")["BZ=F"].dropna()
    return {g.strftime("%Y-%m-%d"): float(v) for g, v in on.loc["2026-10-05":BAZ_GUN].items()}


def main() -> int:
    yer = senaryo_yeri()
    sonuc = {
        "uretim": {"olcum_py_sha256": hashlib.sha256((BURASI / "olcum.py").read_bytes()).hexdigest(),
                   "girdiler": {k: v["sha256"] for k, v in KUNYE["dosyalar"].items()},
                   "otv_kararlar_sha256": hashlib.sha256((VERI / "otv_kararlar.json").read_bytes()).hexdigest()},
        "slug": SLUG,
        "yontem": {"ufuk": UFUK, "nw_gecikme": NW_GECIKME, "pencere_esik": PENCERE_ESIK, "pencere_ara": PENCERE_ARA,
                   "genis_ara": GENIS_ARA, "takvim_tavan": TAKVIM_TAVAN, "loo_once": 2 * UFUK, "loo_sonra": UFUK,
                   "loo_asgari": LOO_ASGARI, "litre_varil": LITRE_VARIL, "litre_galon": LITRE_GALON},
        "iki_brent": iki_brent(),
        "senaryo_yeri": yer,
        "giris_kapanis": giris_kapanislari(),
        "turkiye_ek": turkiye_ek(),
    }
    _, say = cnbc()
    sonuc["kaynak_duzeltme"] = say
    rj = rejim_2026()
    sonuc["rejim_2026"] = rj
    loo = birini_disarida_birak(rj)
    sonuc["birini_disarida"] = loo
    sonuc["emsaller"] = emsaller()
    tum = tum_yukselisler()
    sonuc["tum_yukselisler"] = tum
    sonuc["tcmb"] = tcmb_oyun_kitabi()
    sonuc["tufe_gecis"] = tufe_gecis()
    sonuc["enerji_faturasi"] = enerji_faturasi()
    sonuc["yabanci"] = yabanci_akim()
    sonuc["abd_enflasyon"] = abd_enflasyon()
    sonuc["abd_senaryo"] = abd_senaryo(sonuc["abd_enflasyon"], yer)
    sonuc["senaryo_tablosu"] = senaryo_tablosu(yer, rj, loo, tum)
    sonuc["tufe_aktarim"] = tufe_aktarim(yer, sonuc["tufe_gecis"], sonuc["senaryo_tablosu"])
    # ABD pompası İKİ YOLLA: ham petrol geçişi (rafineri marjı sabit) ve vadeli ürün yolu — pompa ile vadeli
    # arasındaki bugünkü fark korunur, vadeli senaryo tablosundaki gibi hareket eder (marj 2026'daki gibi açılır)
    for ad in SENARYO:
        for urun, kod in (("benzin", "RB=F"), ("motorin", "HO=F")):
            v = sonuc["senaryo_tablosu"][kod]
            pompa = sonuc["abd_enflasyon"][f"{urun}_pompa_gecis"]["son_fiyat"]
            sonuc["abd_senaryo"][ad][urun]["seviye_vadeli_yolu"] = pompa + (v[ad]["seviye"] - v["son_deger"])
            sonuc["abd_senaryo"][ad][urun]["pompa_vadeli_farki"] = pompa - v["son_deger"]
    sonuc["enerji_faturasi"]["senaryo_kural"] = enerji_kural_senaryo(sonuc["enerji_faturasi"], yer,
                                                                     sonuc["iki_brent"].get("fiziki_son"))
    sonuc["otv_tampon"] = otv_tampon(yer, sonuc["senaryo_tablosu"])
    sonuc["kaynak_uyumu"] = kaynak_uyumu()
    sonuc["sekil"] = sekil_verisi(yer)

    def temiz(o):
        if isinstance(o, dict):
            return {k: temiz(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [temiz(v) for v in o]
        if isinstance(o, (float, np.floating)):
            return None if not np.isfinite(o) else round(float(o), 6)
        if isinstance(o, np.integer):
            return int(o)
        return o
    CIKTI.write_text(json.dumps(temiz(sonuc), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"── {CIKTI.name} yazıldı")
    return 0


if __name__ == "__main__":
    sys.exit(main())
