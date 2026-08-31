# -*- coding: utf-8 -*-
"""El Niño ↔ Türkiye gıda enflasyonu — ÖLÇÜM katmanı.

KURUCU YÖNTEM KARARI. Türkiye'de gıda enflasyonuna ENSO değil, kur ve para
politikası hükmeder. ONI ile HAM gıda enflasyonunu korele etmek, ikisinin de
kendi trendi olduğu için sahte bir ilişki üretir. Bu yüzden ölçüm

    goreceli gıda enflasyonu = gıda(yıllık) − manşet TÜFE(yıllık)

üzerinden yapılır. Bu fark, gıdanın SEPETİN GERİ KALANINA GÖRE ne yaptığını
söyler; ortak parasal trend iki taraftan da düşer. ENSO'nun iddia ettiği şey
zaten budur: gıdayı diğer kalemlerden AYRIŞTIRAN arz şoku.

İki bağımsız ölçüt kullanılır, çünkü tek ölçüt yanıltır:
  1. ÇAPRAZ KORELASYON — ONI(t−k) ile göreceli gıda enflasyonu(t), k=0..24 ay.
     İki seri de kalıcı (persistent) olduğundan katsayı yukarı yanlıdır;
     bu yüzden tek başına kanıt sayılmaz ve bu uyarı çıktıya yazılır.
  2. EPİZOT ÇALIŞMASI — güçlü El Niño zirvelerinden sonraki 18 ayda göreceli
     gıda enflasyonunun ortalaması, koşulsuz ortalamayla kıyaslanır. Kalıcılık
     yanlılığı buradan geçmez.

Ayrıca GEÇİŞ KATSAYISI ölçülür: manşet aylık enflasyonun gıda aylık
enflasyonuna regresyonu. Senaryo hesabı bu katsayıyla kurulur — sepetteki
nominal ağırlıkla değil, GÖZLENEN geçişle.

İlişki zayıf çıkarsa ZAYIF olduğu yazılır. Beklenen sonucu üretmek için ölçüt
seçilmez.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

PROJE = Path(__file__).resolve().parent
DATA = PROJE / "data"

# ONI eşikleri NOAA'nın kendi sınıflandırması: |0,5| zayıf, 1,0 orta,
# 1,5 güçlü, 2,0 çok güçlü. Epizot = eşiği üst üste EN AZ 5 ay aşmak.
ESIK_GUCLU = 1.5
ASGARI_AY = 5
UFUK = 18          # zirveden sonra kaç ay izlenecek
GEC_MAKS = 24      # çapraz korelasyonda en uzun gecikme

# Modern örneklem: Türkiye 2005'te altı sıfır attı ve enflasyon rejimi
# değişti; tam örneklem ayrıca raporlanır ama tez modern örnekleme dayanır.
MODERN_BAS = "2005-01-01"

_UYARI: list[str] = []


def uyar(m: str) -> None:
    if m not in _UYARI:
        _UYARI.append(m)
    print("  ! " + m, flush=True)


def _r(x, n=2):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), n)


def _yillik(s: pd.Series) -> pd.Series:
    return (s / s.shift(12) - 1.0) * 100.0


def _aylik(s: pd.Series) -> pd.Series:
    return (s / s.shift(1) - 1.0) * 100.0


def epizotlar(oni: pd.Series, esik: float) -> list[dict]:
    """Eşiği üst üste ASGARI_AY aşan dönemler; her biri zirvesiyle."""
    ustu = oni >= esik
    out, bas = [], None
    for t, v in ustu.items():
        if v and bas is None:
            bas = t
        elif not v and bas is not None:
            dilim = oni.loc[bas:t][:-1]
            if len(dilim) >= ASGARI_AY:
                out.append({"bas": bas, "bit": dilim.index[-1],
                            "zirve": dilim.idxmax(), "zirve_deger": float(dilim.max()),
                            "ay": int(len(dilim))})
            bas = None
    if bas is not None:                      # hâlâ süren epizot
        dilim = oni.loc[bas:]
        if len(dilim) >= ASGARI_AY:
            out.append({"bas": bas, "bit": dilim.index[-1], "zirve": dilim.idxmax(),
                        "zirve_deger": float(dilim.max()), "ay": int(len(dilim)),
                        "suruyor": True})
    return out


def capraz(oni: pd.Series, hedef: pd.Series, gec_maks: int = GEC_MAKS) -> list[dict]:
    """corr(ONI[t−k], hedef[t]) — k ay gecikme."""
    out = []
    for k in range(gec_maks + 1):
        a = oni.shift(k)
        ort = pd.concat([a, hedef], axis=1).dropna()
        if len(ort) < 60:
            continue
        out.append({"gecikme": k, "korelasyon": _r(ort.iloc[:, 0].corr(ort.iloc[:, 1]), 3),
                    "n": int(len(ort))})
    return out


def main() -> int:
    print("── El Niño hattı · ölçüm")
    oni = pd.read_csv(DATA / "oni.csv", index_col=0, parse_dates=True)["oni"]
    tufe = pd.read_csv(DATA / "tufe.csv", index_col=0, parse_dates=True)
    if oni.dropna().empty or tufe.dropna(how="all").empty:
        raise SystemExit("boş tablo — hat duruyor")

    y = {k: _yillik(tufe[k]) for k in tufe.columns}
    # GÖRECELİ gıda enflasyonu: ortak parasal trend düşer.
    gor_gida = (y["gida"] - y["tufe"]).dropna()
    gor_ham = (y["islenmemis_gida"] - y["tufe"]).dropna()
    print(f"   göreceli gıda serisi: {len(gor_gida)} ay, "
          f"{gor_gida.index.min():%Y-%m} → {gor_gida.index.max():%Y-%m}")

    oni_m = oni.reindex(gor_gida.index.union(oni.index)).interpolate(limit=1)

    sonuc: dict = {"_tarih": f"{tufe.index.max():%d.%m.%Y}",
                   "_ay": f"{tufe.index.max():%Y-%m}",
                   "oni_son": _r(oni.iloc[-1]),
                   "oni_son_ay": f"{oni.index.max():%Y-%m}"}

    # ── 1. çapraz korelasyon (tam ve modern örneklem)
    for etiket, kesit in (("tam", None), ("modern", MODERN_BAS)):
        g = gor_gida if kesit is None else gor_gida.loc[kesit:]
        h = gor_ham if kesit is None else gor_ham.loc[kesit:]
        cg = capraz(oni_m, g)
        ch = capraz(oni_m, h)
        if not cg:
            uyar(f"{etiket}: çapraz korelasyon için yeterli örtüşme yok")
            continue
        en = max(cg, key=lambda d: abs(d["korelasyon"]))
        enh = max(ch, key=lambda d: abs(d["korelasyon"])) if ch else None
        sonuc[f"capraz_{etiket}"] = cg
        sonuc[f"capraz_{etiket}_en_iyi_gecikme"] = en["gecikme"]
        sonuc[f"capraz_{etiket}_en_iyi_kor"] = en["korelasyon"]
        sonuc[f"capraz_{etiket}_n"] = en["n"]
        if enh:
            sonuc[f"capraz_{etiket}_ham_en_iyi_gecikme"] = enh["gecikme"]
            sonuc[f"capraz_{etiket}_ham_en_iyi_kor"] = enh["korelasyon"]
        print(f"   çapraz [{etiket}] gıda: en iyi gecikme {en['gecikme']} ay, "
              f"r={en['korelasyon']}, n={en['n']}"
              + (f"  ·  işlenmemiş: {enh['gecikme']} ay, r={enh['korelasyon']}" if enh else ""))

    # ── 2. epizot çalışması (kalıcılık yanlılığından bağımsız)
    eps = epizotlar(oni, ESIK_GUCLU)
    sonuc["epizotlar"] = [{"bas": f"{e['bas']:%Y-%m}", "zirve": f"{e['zirve']:%Y-%m}",
                           "zirve_deger": _r(e["zirve_deger"]), "ay": e["ay"],
                           "suruyor": bool(e.get("suruyor"))} for e in eps]
    print(f"   güçlü El Niño epizodu (ONI≥{ESIK_GUCLU}, ≥{ASGARI_AY} ay): {len(eps)}")

    kayitlar = []
    for e in eps:
        if e.get("suruyor"):
            continue
        pencere = gor_gida.loc[e["zirve"]:e["zirve"] + pd.DateOffset(months=UFUK)]
        if len(pencere) < 6:
            continue
        kayitlar.append({"zirve": f"{e['zirve']:%Y-%m}", "zirve_oni": _r(e["zirve_deger"]),
                         "goreceli_gida_ort": _r(pencere.mean()),
                         "ay": int(len(pencere))})
    sonuc["epizot_sonrasi"] = kayitlar
    if kayitlar:
        ort_ep = float(np.mean([k["goreceli_gida_ort"] for k in kayitlar]))
        kosulsuz = float(gor_gida.mean())
        sonuc["epizot_ortalama"] = _r(ort_ep)
        sonuc["kosulsuz_ortalama"] = _r(kosulsuz)
        sonuc["epizot_fark"] = _r(ort_ep - kosulsuz)
        print(f"   epizot sonrası {UFUK} ay göreceli gıda ort. {ort_ep:+.2f} puan · "
              f"koşulsuz {kosulsuz:+.2f} · fark {ort_ep - kosulsuz:+.2f}")
    else:
        uyar("ölçülebilir epizot penceresi yok — epizot çalışması yapılamadı")

    # ── 3. geçiş katsayısı: manşet aylık ~ gıda aylık
    a_tufe, a_gida = _aylik(tufe["tufe"]), _aylik(tufe["gida"])
    ort = pd.concat([a_gida, a_tufe], axis=1).dropna()
    ort = ort.loc[MODERN_BAS:]
    x, yy = ort.iloc[:, 0].to_numpy(), ort.iloc[:, 1].to_numpy()
    beta, sabit = np.polyfit(x, yy, 1)
    r2 = float(np.corrcoef(x, yy)[0, 1] ** 2)
    sonuc["gecis_beta"] = _r(beta, 3)
    sonuc["gecis_r2"] = _r(r2, 3)
    sonuc["gecis_n"] = int(len(ort))
    print(f"   geçiş katsayısı β={beta:.3f} (R²={r2:.3f}, n={len(ort)}) — "
          f"gıda aylık 1 puan artarsa manşet {beta:.2f} puan")

    # ── güncel durum
    sonuc["gida_12a"] = _r(y["gida"].iloc[-1])
    sonuc["tufe_12a"] = _r(y["tufe"].iloc[-1])
    sonuc["goreceli_gida_son"] = _r(gor_gida.iloc[-1])
    sonuc["hamgida_12a"] = _r(y["islenmemis_gida"].iloc[-1])

    # grafik tarihçesi
    sonuc["tarihce"] = [
        {"ay": f"{t:%Y-%m}", "oni": _r(oni_m.get(t)), "goreceli_gida": _r(gor_gida.get(t))}
        for t in gor_gida.loc[MODERN_BAS:].index
    ]
    sonuc["uyarilar"] = _UYARI
    sonuc["yontem_notu"] = (
        "Çapraz korelasyon katsayıları yukarı yanlıdır: iki seri de kalıcıdır. "
        "Tez epizot çalışmasına dayanır; korelasyon yalnız gecikme profilini "
        "göstermek için verilir.")
    (DATA / "metrik.json").write_text(
        json.dumps(sonuc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"── ölçüm yazıldı: {DATA/'metrik.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
