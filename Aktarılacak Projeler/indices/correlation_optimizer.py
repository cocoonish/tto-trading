"""Kalibrasyon — haber tonu endeksinin parametreleri ve KARNESI.

SAYFANIN SORUSU: endeks, fiyatin SONRAKI hareketini soyluyor mu? Bu dosya o soruyu
olcer ve canli endeksin parametresini o olcuye gore secer.

ESKI KALIBRASYONUN UC KUSURU (03.10.2026'da olculdu, data/kalibrasyon_kesif.json):
  1. Dovizde fiyat BIR GUN kaymisti: Yahoo'nun kapanmis gunluk doviz barinin
     "Close"u gunun basindaki fiyattir (00:00 UTC saatlik fiyata 0,4–2,7 bp).
  2. Hedef GERIYE donuktu: `pct_change(5)` D'de BITEN bes gunun getirisi; sayfa
     "5 gunluk ileri getiri" diyordu. Ayni arsivle olculdu: kayitli parametrelerde
     geriye donuk bag altinda 0,65, S&P 500'de 0,49; ileri getiriyle bag yok.
     Yani karne "haber tonu haftayi fiyatlar" degil "haftanin fiyatini yansitir"
     diyordu.
  3. Gecikme (lag) amaca HIC girmiyordu: siralama olcusu kaydirilmamis seriyle
     kuruluyordu, lag 0 ile 1 ayni sayiyi veriyordu ve kayitli lag kararsiz
     siralamanin esitlik bozmasindan geliyordu. Canli endekste gecikme yok;
     izgaradan cikarildi.

OLCU (tek tanim, hizali.py):
  * Deger: canli endeksin kendisi, her islem gununun KAPANIS aninda (fiyat.py);
    normalizasyon ve yumusatma yok — okurun gordugu sayi.
  * Hedef: F_h(D) = P(D+h)/P(D) − 1. BIRINCIL ufuk 5 islem gunu (sayfanin ilan
    ettigi), 1 gun ikincil. Ufuk SECILMEZ: iki ufkun ham olcusu kiyaslanamaz
    (5 gunluk ortusen getiride bos dagilim daha genistir).
  * Istatistik: havuzlanmis Spearman ρ (buyuk tek gunlere dayanikli, olcek
    donusumunden bagimsiz).
  * Ornek disi: yuruyen pencere — ilk ILK_EGITIM gun egitim, sonra her ADIM gunde
    yeniden secim; egitimin son h gunu ATILIR (hedefi test donemine tasar); test
    tahminleri egitimin kendi ortalama/sapmasiyla olceklenip havuzlanir.
  * Saf kiyas: (a) secimsiz varsayilan parametre; (b) yalniz FIYATTAN kurulan
    rakip — gecmis gunluk getirilerin ustel ortalamasi, DEVAM ve DONUS isaretiyle
    (sekiz aday), ayni yuruyen pencereden;
    (c) plasebo: hedef dairesel kaydirilir (k = h+20 … n−h−20, BES gun arayla —
    olculdu: 5 gun arali kaydirmalar neredeyse bagimsiz), secim dahil butun
    yordam yeniden kosar; p = (1+b)/(1+K), asla sifir degil.
  * Aile sinamasi: butun varliklarin hedefi AYNI k ile kaydirilir (varliklar
    arasi bagimlilik korunur); aile istatistigi varliklarin ornek disi ρ ortalamasi.

KURAL (once yazildi, olcumden sonra degistirilmez — KARAR 03.10.2026, kullanici):
  aile p ≤ ESIK_P ise, ornek disi ρ'su hem sifirin hem fiyat-yalniz rakibin
  ustunde olan varlik KENDI kalibre parametresini alir ("ongoruyor"); obur her
  varlik TEK varsayilanla (config.DEFAULT_PARAMS) kurulur ("ongormuyor").
  Cikarim kapisi AILE sinamasidir; rakip kiyasi ve sifirin ustu birer ZORUNLU
  KOSULDUR, sinama degil (nokta kiyas: kurali yalniz daraltir, gevsetmez).
  Rakip olculemediyse kosul saglanmis sayilmaz.
  Asgari veri yoksa "olculemedi" ve yine varsayilan.

Ciktilar: data/optimized_params.json (canli endeks bunu okur; varlik basina
`params`) ve data/kalibrasyon_karne.json (karnenin tamami; sayfa ve Sekil 09).
"""

from __future__ import annotations

import itertools
import json
import math
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from scipy import stats

import config

UFUKLAR = (5, 1)            # ilki birincil
ILK_EGITIM = 100            # yuruyen pencerenin ilk egitim boyu (islem gunu)
ADIM = 21                   # yeniden secim araligi (islem gunu)
PLASEBO_ARALIK = 5          # plasebo kaydirmalari arasi (islem gunu)
ESIK_P = 0.05               # aile sinamasinin esigi
FIYAT_YARIOMUR = (1, 2, 3, 5)   # fiyat-yalniz rakibin ustel ortalama yari omurleri (gun)
GUN_ASGARI = 150            # bundan az olculebilir gun → "olculemedi"
KARNE = os.path.join(config.DATA_DIR, "kalibrasyon_karne.json")


# ── Eski arayuz (panel bunlari kullanir) ───────────────────────────────────────

def compute_correlation(index_series: pd.Series, return_series: pd.Series,
                        lag: int = 0) -> dict:
    """Pearson and Spearman correlation. lag>0 = sentiment leads price by N days."""
    idx = index_series.shift(lag) if lag > 0 else index_series
    combined = pd.DataFrame({"index": idx, "returns": return_series}).dropna()
    if len(combined) < 10:
        return {"pearson_r": 0.0, "pearson_p": 1.0,
                "spearman_r": 0.0, "spearman_p": 1.0, "n_obs": len(combined)}
    pr, pp = stats.pearsonr(combined["index"], combined["returns"])
    sr, sp = stats.spearmanr(combined["index"], combined["returns"])
    return {"pearson_r": round(float(pr), 4), "pearson_p": round(float(pp), 4),
            "spearman_r": round(float(sr), 4), "spearman_p": round(float(sp), 4),
            "n_obs": len(combined)}


def rolling_correlation(index_series: pd.Series, return_series: pd.Series,
                        window: int = 20) -> pd.Series:
    combined = pd.DataFrame({"index": index_series, "returns": return_series}).dropna()
    if len(combined) < window:
        return pd.Series(dtype=float)
    return combined["index"].rolling(window).corr(combined["returns"])


def load_optimized_params() -> dict:
    """Canli endeksin parametreleri: {varlik: params}."""
    if os.path.exists(config.OPTIMIZED_PARAMS):
        with open(config.OPTIMIZED_PARAMS, "r") as f:
            data = json.load(f)
        return {k: v["params"] for k, v in data.items() if isinstance(v, dict) and "params" in v}
    return {}


def load_optimized_full() -> dict:
    if os.path.exists(config.OPTIMIZED_PARAMS):
        with open(config.OPTIMIZED_PARAMS, "r") as f:
            return json.load(f)
    return {}


def load_karne() -> dict:
    try:
        with open(KARNE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


# ── Izgara ─────────────────────────────────────────────────────────────────────

def izgara() -> list[dict]:
    """Canli endeksin aranan parametreleri (gecikme yok: canli endeks gecikme tasimaz)."""
    anahtar = [k for k in config.PARAM_GRID if k != "lag_days"]
    out = []
    for c in itertools.product(*(config.PARAM_GRID[k] for k in anahtar)):
        p = dict(config.DEFAULT_PARAMS)
        p.update(dict(zip(anahtar, c)))
        p["lag_days"] = 0
        out.append(p)
    return out


def _ayni(a: dict, b: dict) -> bool:
    anahtar = [k for k in config.PARAM_GRID if k != "lag_days"]
    return all(a.get(k) == b.get(k) for k in anahtar)


def varsayilan_sira(grid: list[dict]) -> int:
    """Varsayilan parametrenin izgaradaki yeri — izgarada olmak ZORUNDA."""
    for i, p in enumerate(grid):
        if _ayni(p, config.DEFAULT_PARAMS):
            return i
    raise ValueError("config.DEFAULT_PARAMS izgarada yok: secimsiz kiyas kurulamaz")


AGG_TR = {"weighted_mean": "ağırlıklı ortalama", "bull_bear_ratio": "boğa/ayı oranı",
          "intensity_ratio": "yoğunluk oranı", "directional_strength": "yön gücü"}
DONUSUM_TR = {"raw": "ham skor", "tanh": "tanh dönüşümü", "amplify": "kök büyütmesi"}


def _virgul(v) -> str:
    v = float(v)
    return str(int(v)) if v == int(v) else f"{v:g}".replace(".", ",")


def kisa_ad(p: dict) -> str:
    """Parametre setinin OKURA giden adi (sayfaya ve figure basilir)."""
    nf, mw = float(p.get("neutral_filter", 0)), float(p.get("momentum_weight", 0))
    return " · ".join([
        AGG_TR.get(p.get("aggregation"), str(p.get("aggregation"))),
        f"yarı ömür {_virgul(p.get('time_decay_halflife', 0))} gün",
        DONUSUM_TR.get(p.get("score_transform"), str(p.get("score_transform"))),
        "nötr filtre yok" if nf == 0 else f"|skor| < {_virgul(nf)} atılır",
        "momentum yok" if mw == 0 else f"momentum payı {_virgul(mw)}"])


# ── Yuruyen pencere ────────────────────────────────────────────────────────────

def katlar(n: int) -> list[tuple[int, int]]:
    """(baslangic, bitis) test katlari: ilk ILK_EGITIM gun egitim, sonra ADIM'lik bloklar."""
    out, t = [], ILK_EGITIM
    while t < n:
        out.append((t, min(t + ADIM, n)))
        t += ADIM
    return out


def yuruyen(M: np.ndarray, y: np.ndarray, h: int, spearman) -> dict:
    """M: aday × gun ham degerler; y: hedef. Ornek disi havuzlanmis ρ ve kat ayrintisi."""
    n = M.shape[1]
    tahmin, gercek, secim, isaret = [], [], [], []
    for bas, bit in katlar(n):
        egit = slice(0, max(0, bas - h))            # son h gun atilir: hedef teste tasar
        skor = np.array([spearman(M[c, egit], y[egit]) for c in range(M.shape[0])])
        if np.all(np.isnan(skor)):
            continue
        c = int(np.nanargmax(skor))                  # esitlikte en kucuk sira (belirlenimci)
        e = M[c, egit]
        e = e[~np.isnan(e)]
        if len(e) < 2 or e.std() == 0:
            continue
        z = (M[c, bas:bit] - e.mean()) / e.std()
        tahmin.append(z)
        gercek.append(y[bas:bit])
        secim.append(c)
        isaret.append(spearman(M[c, bas:bit], y[bas:bit], asgari=8))
    if not tahmin:
        return {"rho": math.nan, "n": 0, "secim": [], "kat_isaret": []}
    t, g = np.concatenate(tahmin), np.concatenate(gercek)
    m = ~(np.isnan(t) | np.isnan(g))
    return {"rho": spearman(t, g), "n": int(m.sum()), "secim": secim,
            "kat_isaret": [None if math.isnan(v) else (1 if v > 0 else -1) for v in isaret]}


def secimsiz(s: np.ndarray, y: np.ndarray, spearman) -> float:
    """Tek, onceden yazilmis aday: yuruyen pencerenin TEST gunlerinde ρ (secim yok)."""
    k = katlar(len(s))
    if not k:
        return math.nan
    return spearman(s[k[0][0]:], y[k[0][0]:])


# ── Varlik ve aile ─────────────────────────────────────────────────────────────

def fiyat_rakibi(seri: pd.Series, gunler: pd.Index) -> np.ndarray:
    """Yalniz fiyattan: gecmis gunluk log getirilerin ustel ortalamasi (D'nin kapanisina kadar).

    IKI ISARET birden aday: devam (momentum) ve donus (ters isaret). Yalniz devam
    adaylari olsaydi, fiyatin geri dondugu bir donemde rakibin ornek disi ρ'su
    EKSI cikar ve gecen haftanin fiyatini ters isaretle tasiyan HER seri onu
    "gecerdi" — oysa o seri haberden degil fiyatin kendi donusunden bilgi tasir.
    Secim yuruyen pencerede, adaylarla ayni kuralla (egitimde en yuksek ρ)."""
    r = np.log(seri).diff()
    devam = [r.ewm(halflife=hl, min_periods=hl).mean().reindex(gunler).to_numpy(float)
             for hl in FIYAT_YARIOMUR]
    return np.vstack(devam + [-x for x in devam])


def girdi(anahtar: str, onbellek: dict, simdi=None) -> dict:
    """Bir varligin HAM girdisi: arsivin makaleleri ve kapanislar (ag burada)."""
    import fiyat
    import hizali
    makaleler, abas, ason, denetim = hizali.arsiv(onbellek, anahtar, simdi=simdi)
    if not makaleler:
        return {"anahtar": anahtar, "hata": "arşivde skorlu makale yok", "denetim": denetim}
    fy = fiyat.kapanislar(config.ASSETS[anahtar]["ticker"], simdi=simdi, gun=420)
    return {"anahtar": anahtar, "makaleler": makaleler, "abas": abas, "ason": ason,
            "denetim": denetim, "fy": fy}


def malzeme(g: dict, grid: list[dict]) -> dict:
    """Girdiden olcu malzemesi: gunler, aday matrisi, hedefler, rakip (ag yok)."""
    import fiyat
    import hizali
    import index_builder
    if "hata" in g:
        return g
    fy, anahtar = g["fy"], g["anahtar"]
    anlar = hizali.gecerli_gunler(fy.an, g["abas"], g["ason"])
    if len(anlar) < GUN_ASGARI:
        return {"anahtar": anahtar, "hata": f"ölçülebilir gün {len(anlar)} (< {GUN_ASGARI})",
                "denetim": g["denetim"], "fiyat_tanim": fy.tanim}
    dizi = index_builder.MakaleDizisi(g["makaleler"])
    M = np.vstack([hizali.ham_seri(dizi, p, anlar).to_numpy(float) for p in grid])
    gunler = anlar.index
    hedef = {h: fiyat.ileri_getiri(fy.seri, h).reindex(gunler).to_numpy(float) for h in UFUKLAR}
    tepki = {h: fiyat.geri_getiri(fy.seri, h).reindex(gunler).to_numpy(float) for h in UFUKLAR}
    return {"anahtar": anahtar, "M": M, "gunler": gunler, "hedef": hedef, "tepki": tepki,
            "rakip": fiyat_rakibi(fy.seri, gunler), "denetim": g["denetim"],
            "fiyat_tanim": fy.tanim, "arsiv": [g["abas"].isoformat(), g["ason"].isoformat()]}


def varlik_verisi(anahtar: str, onbellek: dict, simdi=None, grid=None, fy=None) -> dict:
    """girdi + malzeme. `fy` verilirse fiyat agdan alinmaz (sinama)."""
    import hizali
    grid = grid or izgara()
    if fy is None:
        g = girdi(anahtar, onbellek, simdi=simdi)
    else:
        makaleler, abas, ason, denetim = hizali.arsiv(onbellek, anahtar, simdi=simdi)
        g = ({"anahtar": anahtar, "makaleler": makaleler, "abas": abas, "ason": ason,
              "denetim": denetim, "fy": fy} if makaleler
             else {"anahtar": anahtar, "hata": "arşivde skorlu makale yok", "denetim": denetim})
    return malzeme(g, grid)


# ── Donmus girdi: yayimlanan karnenin arsivi depoda durur ──────────────────────
#
# Haber arsivi (data/gdelt_cache.json) depoda degil, is akisinin onbelleginde;
# her pazartesi bir hafta ilerler ve onbellek bir gun silinir. Karnenin sayilari
# o gun yeniden uretilemez olurdu. Kalibrasyon kendi girdisini — makalenin yayim
# ani, skoru, kaynak agirligi (baslik YOK) ve kapanislar — donmus dosyalara yazar;
# karne onlarin ozunu tasir; `--arsivden` ayni karneyi onlardan yeniden kurar.
ARSIV = os.path.join(config.DATA_DIR, "kalibrasyon_arsiv.json.gz")
FIYAT_ARSIV = os.path.join(config.DATA_DIR, "kalibrasyon_fiyat.json.gz")


def _oz(yol: str) -> str:
    import hashlib
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def dondur(girdiler: list[dict]) -> dict:
    """Girdileri iki gzip JSON dosyasina yaz (belirlenimci: mtime 0, anahtar sirali)."""
    import gzip
    arsiv, fy = {}, {}
    for g in girdiler:
        a = g["anahtar"]
        arsiv[a] = {"abas": g["abas"].isoformat(), "ason": g["ason"].isoformat(),
                    "denetim": g["denetim"],
                    "makale": [[m["published"], m.get("score", 0), m.get("source_weight", 1.0)]
                               for m in g["makaleler"]]}
        f = g["fy"]
        fy[a] = {"tanim": f.tanim, "kaynak": f.kaynak, "olculemeyen": f.olculemeyen,
                 "gun": [str(t.date()) for t in f.seri.index],
                 "kapanis": [float(v) for v in f.seri.to_numpy()],
                 "an": [t.isoformat() for t in f.an.reindex(f.seri.index)]}
    for yol, veri in ((ARSIV, arsiv), (FIYAT_ARSIV, fy)):
        ham = json.dumps(veri, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        with open(yol, "wb") as f:
            with gzip.GzipFile(fileobj=f, mode="wb", mtime=0) as z:
                z.write(ham)
    return {"arsiv": os.path.basename(ARSIV), "arsiv_oz": _oz(ARSIV),
            "fiyat": os.path.basename(FIYAT_ARSIV), "fiyat_oz": _oz(FIYAT_ARSIV)}


def cozdur() -> list[dict]:
    """Donmus girdiyi oku → girdi() ile ayni bicim."""
    import gzip
    import fiyat
    from datetime import datetime as _dt
    with gzip.open(ARSIV, "rt", encoding="utf-8") as f:
        arsiv = json.load(f)
    with gzip.open(FIYAT_ARSIV, "rt", encoding="utf-8") as f:
        fy = json.load(f)
    out = []
    for a in config.ASSETS:
        if a not in arsiv or a not in fy:
            out.append({"anahtar": a, "hata": "donmuş girdide yok"})
            continue
        r, p = arsiv[a], fy[a]
        idx = pd.DatetimeIndex(pd.to_datetime(p["gun"]))
        seri = pd.Series(p["kapanis"], index=idx, dtype="float64")
        an = pd.Series([pd.Timestamp(t) for t in p["an"]], index=idx)
        out.append({"anahtar": a, "abas": _dt.fromisoformat(r["abas"]), "ason": _dt.fromisoformat(r["ason"]),
                    "denetim": r["denetim"],
                    "makaleler": [{"published": m[0], "score": m[1], "source_weight": m[2]}
                                  for m in r["makale"]],
                    "fy": fiyat.Fiyat(seri, an, p["tanim"], p["kaynak"], p["olculemeyen"])})
    return out


def kaydirmalar(n: int, h: int) -> list[int]:
    return list(range(h + 20, n - h - 20 + 1, PLASEBO_ARALIK))


def _r(v, n=4):
    return None if v is None or (isinstance(v, float) and math.isnan(v)) else round(float(v), n)


def kalibre_et(veri: list[dict], grid: list[dict]) -> tuple[dict, dict]:
    """Butun varliklar → (optimized_params, karne). Ag yok: veri hazir gelir."""
    import hizali
    sp = hizali.spearman
    dv = varsayilan_sira(grid)
    olcu = [v for v in veri if "M" in v]
    n_ortak = min(v["M"].shape[1] for v in olcu) if olcu else 0
    karne = {"varlik": {}, "aile": {}}

    for h in UFUKLAR:
        ks = kaydirmalar(n_ortak, h)
        aile_bos = np.zeros(len(ks))
        aile_n = 0
        for v in olcu:
            y = v["hedef"][h]
            gercek = yuruyen(v["M"], y, h, sp)
            rakip = yuruyen(v["rakip"], y, h, sp)
            sv = secimsiz(v["M"][dv], y, sp)
            bos = np.array([yuruyen(v["M"], np.roll(y, k), h, sp)["rho"] for k in ks])
            bos_v = np.array([secimsiz(v["M"][dv], np.roll(y, k), sp) for k in ks])
            egit = slice(0, len(y) - h)
            tam = np.array([sp(v["M"][c, egit], y[egit]) for c in range(len(grid))])
            c_tam = int(np.nanargmax(tam)) if not np.all(np.isnan(tam)) else dv
            kv = karne["varlik"].setdefault(v["anahtar"], {"ileri": {}})
            kv["ileri"][str(h)] = {
                "oos": _r(gercek["rho"]), "oos_n": gercek["n"],
                "oos_p": _r(hizali.p_degeri(gercek["rho"], bos)),
                "kat_pozitif": sum(1 for s in gercek["kat_isaret"] if s == 1),
                "kat": len(gercek["kat_isaret"]),
                "varsayilan": _r(sv), "varsayilan_p": _r(hizali.p_degeri(sv, bos_v)),
                "fiyat_rakibi": _r(rakip["rho"]),
                "is_max": _r(tam[c_tam]), "is_max_params": kisa_ad(grid[c_tam]),
                "kalibre_sira": c_tam,
                "kismi_varsayilan": _r(hizali.kismi_spearman(v["M"][dv], y, v["tepki"][h])),
                "K": len(ks), "p_taban": _r(1 / (1 + len(ks)) if ks else math.nan),
            }
            if not math.isnan(gercek["rho"]):
                aile_bos += np.where(np.isnan(bos), 0.0, bos)
                aile_n += 1
            kv["tepki"] = {str(hh): {
                "rho": _r(sp(v["M"][dv], v["tepki"][hh])),
                "p": _r(hizali.p_degeri(sp(v["M"][dv], v["tepki"][hh]),
                                        np.array([sp(v["M"][dv], np.roll(v["tepki"][hh], k))
                                                  for k in kaydirmalar(len(v["tepki"][hh]), hh)]))),
            } for hh in UFUKLAR}
            kv.update({"gun": int(v["M"].shape[1]), "ilk": str(v["gunler"][0].date()),
                       "son": str(v["gunler"][-1].date()), "fiyat_tanim": v["fiyat_tanim"],
                       "denetim": v["denetim"], "arsiv": v["arsiv"]})
        oos = [karne["varlik"][v["anahtar"]]["ileri"][str(h)]["oos"] for v in olcu]
        oos = [o for o in oos if o is not None]
        aile_stat = float(np.mean(oos)) if oos else math.nan
        karne["aile"][str(h)] = {
            "istatistik": _r(aile_stat), "varlik": len(oos),
            "p": _r(hizali.p_degeri(aile_stat, aile_bos / max(aile_n, 1))) if aile_n else None,
            "K": len(ks), "pozitif": sum(1 for o in oos if o > 0)}

    for v in veri:
        if "M" not in v:
            karne["varlik"][v["anahtar"]] = {"hata": v.get("hata"), "denetim": v.get("denetim"),
                                             "fiyat_tanim": v.get("fiyat_tanim")}

    # KURAL — once yazildi (bkz. baslik).
    h0 = str(UFUKLAR[0])
    aile_p = karne["aile"].get(h0, {}).get("p")
    ts = datetime.now(timezone.utc).isoformat()
    params = {}
    for anahtar in config.ASSETS:
        kv = karne["varlik"].get(anahtar, {})
        il = kv.get("ileri", {}).get(h0)
        if not il:
            hukum, p = "ölçülemedi", dict(config.DEFAULT_PARAMS)
        # Rakip olculemediyse "rakibi gecti" denemez: kural ihtiyatli tarafta kalir.
        elif (aile_p is not None and aile_p <= ESIK_P and il["oos"] is not None
              and il["fiyat_rakibi"] is not None
              and il["oos"] > 0 and il["oos"] > il["fiyat_rakibi"]):
            hukum, p = "öngörüyor", dict(grid[il["kalibre_sira"]])
        else:
            hukum, p = "öngörmüyor", dict(config.DEFAULT_PARAMS)
        p["lag_days"] = 0
        kv["hukum"] = hukum
        params[anahtar] = {"params": p, "kaynak": "kalibrasyon" if hukum == "öngörüyor" else "varsayılan",
                           "hukum": hukum, "ufuk": UFUKLAR[0], "timestamp": ts}
    karne["olcum_ani"] = ts
    karne["yontem"] = {"ufuklar": list(UFUKLAR), "ilk_egitim": ILK_EGITIM, "adim": ADIM,
                       "plasebo_aralik": PLASEBO_ARALIK, "esik_p": ESIK_P,
                       "fiyat_yariomur": list(FIYAT_YARIOMUR), "izgara": len(grid),
                       "varsayilan": kisa_ad(config.DEFAULT_PARAMS)}
    return params, karne


def _json(obj):
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    raise TypeError(type(obj))


def kalibre_hepsi(yaz: bool = True, arsivden: bool = False) -> dict:
    """Olcer, kurali uygular, dosyalari BIRLIKTE yazar.

    arsivden=False: girdi haber onbelleginden ve Yahoo'dan; donmus girdiye yazilir.
    arsivden=True : girdi donmus dosyalardan (yeniden uretim); hicbir sey indirilmez.
    Bir varligin girdisi eksikse HICBIR dosya yazilmaz (yarim bir varlik kumesiyle
    canli parametre degismez)."""
    grid = izgara()
    if arsivden:
        girdiler = cozdur()
    else:
        import news_fetcher
        onbellek = news_fetcher._load_historical_cache()
        girdiler = []
        for anahtar in config.ASSETS:
            try:
                g = girdi(anahtar, onbellek)
            except Exception as exc:  # noqa: BLE001 — adiyla dusur
                g = {"anahtar": anahtar, "hata": f"{type(exc).__name__}: {exc}"}
            girdiler.append(g)
    eksik = [f"{g['anahtar']}: {g['hata']}" for g in girdiler if "hata" in g]
    if eksik:
        raise SystemExit("kalibrasyon yazılmadı — girdisi eksik varlık var:\n  " + "\n  ".join(eksik))
    veri = []
    for g in girdiler:
        v = malzeme(g, grid)
        print(f"  {g['anahtar']}: " + (f"{v['M'].shape[1]} gün, {len(g['makaleler'])} makale"
                                       if "M" in v else v.get("hata", "?")), flush=True)
        veri.append(v)
    eksik = [f"{v['anahtar']}: {v['hata']}" for v in veri if "hata" in v]
    if eksik:
        raise SystemExit("kalibrasyon yazılmadı — ölçülemeyen varlık var:\n  " + "\n  ".join(eksik))
    params, karne = kalibre_et(veri, grid)
    if yaz:
        os.makedirs(config.DATA_DIR, exist_ok=True)
        karne["girdi"] = (json.load(open(KARNE, encoding="utf-8")).get("girdi") if arsivden
                          else dondur(girdiler))
        with open(config.OPTIMIZED_PARAMS, "w", encoding="utf-8") as f:
            json.dump(params, f, indent=2, ensure_ascii=False, default=_json)
        with open(KARNE, "w", encoding="utf-8") as f:
            json.dump(karne, f, indent=1, ensure_ascii=False, default=_json)
    return karne


def optimize_all() -> dict:
    """Panelin dugmesi icin: yeni kalibrasyon (karnenin tamami doner)."""
    return kalibre_hepsi()


def karsilastir(eski: dict, yeni: dict, yol: str = "") -> list[str]:
    """Iki karnenin farki (olcum ani ve girdi kunyesi haric): yeniden uretim sinamasi."""
    fark = []
    if isinstance(eski, dict) and isinstance(yeni, dict):
        for k in sorted(set(eski) | set(yeni)):
            if k in ("olcum_ani", "girdi"):
                continue
            fark += karsilastir(eski.get(k), yeni.get(k), f"{yol}.{k}" if yol else k)
    elif isinstance(eski, list) and isinstance(yeni, list) and len(eski) == len(yeni):
        for i, (a, b) in enumerate(zip(eski, yeni)):
            fark += karsilastir(a, b, f"{yol}[{i}]")
    elif eski != yeni:
        fark.append(f"{yol}: {eski!r} → {yeni!r}")
    return fark


if __name__ == "__main__":
    import sys
    if "--arsivden" in sys.argv:
        # YENIDEN URETIM: donmus girdiden ayni karne cikiyor mu? Yazmaz — yazsaydi
        # yeni bir damga (yani yeni bir kalibrasyon kimligi) dogardi.
        kayitli = load_karne()
        k = kalibre_hepsi(yaz=False, arsivden=True)
        fark = karsilastir(kayitli, json.loads(json.dumps(k, default=_json)))
        print("\n".join(fark) if fark else "✓ donmuş girdiden aynı karne")
        sys.exit(1 if fark else 0)
    k = kalibre_hepsi(yaz="--yazma" not in sys.argv)
    for h, a in k["aile"].items():
        print(f"aile {h}g: ort. örnek dışı ρ {a['istatistik']} · p {a['p']} (K={a['K']}) · "
              f"{a['pozitif']}/{a['varlik']} pozitif")
    for anahtar, v in k["varlik"].items():
        il = v.get("ileri", {}).get(str(UFUKLAR[0]), {})
        print(f"  {anahtar:8} {v.get('hukum', v.get('hata'))} · ÖD ρ {il.get('oos')} "
              f"(p {il.get('oos_p')}) · rakip {il.get('fiyat_rakibi')} · tepki 5g "
              f"{v.get('tepki', {}).get('5', {}).get('rho')}")
