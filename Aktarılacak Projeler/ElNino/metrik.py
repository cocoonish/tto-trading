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

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJE = Path(__file__).resolve().parent
DATA = PROJE / "data"


def _ortak(ad: str):
    """`ortak/` modülü: guncelle.py PYTHONPATH'e ekler, elle koşuda yedek yol."""
    try:
        return __import__(ad)
    except ImportError:
        sys.path.insert(0, str(PROJE.parents[1] / "ortak"))
        return __import__(ad)


_bicim = _ortak("bicim")


# ═══════════════════════════════════════════════════════════════════════
#  SAAT YAZIMI — hattın TEK tarih yardımcısı (kuresel.py, grafik.py ve
#  ozet_uret.py buradan okur; hiçbiri kendi strftime'ını taşımaz).
#
#  09.09.2026'da ölçüldü: özetteki 37 `*_tarih` anahtarının 37'si de AYLIK
#  bir gözlemi "01.08.2026" diye, yani ayın ilk GÜNÜ gibi yazıyordu. Okur
#  onu o günün ölçümü sanır; sözleşme (ortak/bicim = lib/bicim) aylık saati
#  `AA.YYYY` ister ve ayın son gününe demirler. Günlük saat (koşu günü)
#  `GG.AA.YYYY` kalır; okura ay adı gerekiyorsa ("Haziran 2026") AYRI bir
#  `_ad` anahtarında durur — ISO ya da ay adı bir saat anahtarına girmez.
# ═══════════════════════════════════════════════════════════════════════
def ay_damga(t) -> str | None:
    """Aylık saat: `AA.YYYY`. Ölçülmemiş (None/NaT) → None, uydurulmaz."""
    if t is None or (isinstance(t, float) and np.isnan(t)):
        return None
    t = pd.Timestamp(t)
    if pd.isna(t):
        return None
    return f"{t.month:02d}.{t.year}"


def ay_adi(t) -> str | None:
    """Okur etiketi: "Haziran 2026" — saat anahtarına DEĞİL, `_ad` alanına."""
    if t is None:
        return None
    t = pd.Timestamp(t)
    if pd.isna(t):
        return None
    return f"{_bicim.AYLAR_TR[t.month - 1]} {t.year}"


def ay_iso(t) -> str | None:
    """Makine etiketi "YYYY-AA": yalnız `_uc` defteri ve örneklem sınırları
    gibi ETİKET alanlarında; hiçbir `*_tarih` anahtarına yazılmaz."""
    if t is None:
        return None
    t = pd.Timestamp(t)
    return None if pd.isna(t) else f"{t:%Y-%m}"


def gun_damga(t) -> str | None:
    """Günlük saat: `GG.AA.YYYY` (koşu günü gibi gerçekten GÜN olan saatler)."""
    if t is None:
        return None
    t = pd.Timestamp(t)
    return None if pd.isna(t) else f"{t:%d.%m.%Y}"


def ay_farki(yeni, eski) -> int:
    """İki ay damgası arasındaki ay sayısı (yeni − eski)."""
    a, b = pd.Timestamp(yeni), pd.Timestamp(eski)
    return (a.year - b.year) * 12 + (a.month - b.month)


def ay_kapali(t, bugun: dt.date | None = None) -> bool:
    """Ay kapanmış mı. Kapanmamış bir ayın `AA.YYYY` damgası ayın son gününe,
    yani YARINA düşer ve yayın kapısı (sayfa sınavı 12/18) onu "ölçülmemiş
    gün ilan edildi" diye ENGEL sayar — OVP hattında ölçüldü. Şekil defteri
    böyle bir ucu None bırakır; ay kapandığı gün damga kendiliğinden gelir."""
    b = bugun or dt.date.today()
    t = pd.Timestamp(t)
    return (t.year, t.month) < (b.year, b.month)


def uc(*seriler) -> pd.Timestamp | None:
    """Serilerin BAĞLAYICI ucu: her serinin son dolu gözleminin EN ESKİSİ.

    Bir ölçüm iki bacağın kıyasıysa ancak ikisinin de ölçüldüğü aya kadar
    kurulabilir; en tazesini yazmak öbür bacağı olduğundan yeni gösterir.
    Boş seri → None (ölçülmemiş uç uydurulmaz)."""
    uclar = []
    for s in seriler:
        if s is None:
            return None
        d = s.dropna() if hasattr(s, "dropna") else s
        if len(d) == 0:
            return None
        uclar.append(pd.Timestamp(d.index.max()))
    return min(uclar) if uclar else None


def koy(sonuc: dict, saat: dict, anahtar: str, deger, uc_: pd.Timestamp | None) -> None:
    """Ölçüyü ve SAATİNİ birlikte yazar: `saat[anahtar]` = bağlayıcı uç.
    Anahtar her koşuda yazılır; ölçülemeyen değer None kalır, atlanmaz."""
    sonuc[anahtar] = deger
    if uc_ is not None:
        saat[anahtar] = pd.Timestamp(uc_)


def saatleri_yaz(sonuc: dict, saat: dict) -> None:
    """`<anahtar>_tarih` geleneği: her ölçünün kendi aylık damgası."""
    for k, t in saat.items():
        sonuc[f"{k}_tarih"] = ay_damga(t)


# ═══════════════════════════════════════════════════════════════════════
#  KAYNAK KAYDI — her kaynağın KENDİ yaşı.
#
#  09.09.2026'da ölçüldü: birleşik küresel tablonun son ayı 2026-08 (Pink
#  Sheet, BIS), ama Euro Bölgesi HICP 2025-12'de bitiyor (8 ay) ve BLS
#  2026-07'de; tek damga ECB'yi taze gösteriyordu. Her kaynağın son gözlemi,
#  hattın en yeni ayına göre yaşı ve okura verilen hükmü ("güncel" / "N ay
#  geride") ayrı anahtarlarda durur; kaynak tablosundaki hüküm buradan türer.
# ═══════════════════════════════════════════════════════════════════════
KAYNAK_AD = {
    "oni":  "ONI (NOAA)",
    "tufe": "Türkiye TÜFE (TÜİK)",
    "pink": "Dünya Bankası emtia fiyatları (Pink Sheet)",
    "bls":  "ABD TÜFE (BLS)",
    "bis":  "politika faizi (BIS)",
    "ecb":  "Euro Bölgesi HICP (ECB)",
}
KAYNAK_ESIK_AY = 3      # bu kadar ay ve üstü geride → koşu kaydına uyarı


def kaynak_kaydi(kod: str, seri: pd.Series | None, hat_ay) -> tuple[dict, str | None]:
    """(anahtarlar, uyarı). Seri boşsa anahtarlar boş değerle yazılır, uyarı
    "ölçülemedi" der — ölçülmemiş kaynak taze gibi görünmez."""
    ad = KAYNAK_AD.get(kod, kod)
    d = seri.dropna() if seri is not None else pd.Series(dtype=float)
    if d.empty:
        return ({f"kaynak_{kod}_tarih": None, f"kaynak_{kod}_yas_ay": None,
                 f"kaynak_{kod}_kapsam": "—", f"kaynak_{kod}_durum": "ölçülemedi"},
                f"{ad} serisi bu koşuda alınamadı; ondan türeyen sayılar üretilmedi.")
    bas, son = pd.Timestamp(d.index.min()), pd.Timestamp(d.index.max())
    yas = max(0, ay_farki(hat_ay, son))
    durum = "güncel" if yas < KAYNAK_ESIK_AY else f"{yas} ay geride"
    kayit = {f"kaynak_{kod}_tarih": ay_damga(son),
             f"kaynak_{kod}_yas_ay": int(yas),
             f"kaynak_{kod}_kapsam": f"{ay_adi(bas)} → {ay_adi(son)}",
             f"kaynak_{kod}_durum": durum}
    uyari = None
    if yas >= KAYNAK_ESIK_AY:
        uyari = (f"{ad} serisi hattın en yeni ayının {yas} ay gerisinde "
                 f"(son gözlem {ay_adi(son)}, hat {ay_adi(hat_ay)}); ondan türeyen "
                 "sayılar o aya kadar ölçülmüştür ve kaynak yenilendiğinde "
                 "kendiliğinden ilerler.")
    return kayit, uyari


# ═══════════════════════════════════════════════════════════════════════
#  ŞEKİL SAAT DEFTERİ — figür başına veri ucu, ÇİZEN kodun ilanı.
#
#  Hattın dokuz figürü dört ritimde: ONI (06.2026), TÜFE (08.2026), reel
#  emtia (emtia ÷ ABD TÜFE → 07.2026), BLS (07.2026). Tek ana saat dördünü
#  de 08.2026 gösterirdi. Bağlayıcı bacak EN ESKİSİDİR (uc()); kapanmamış
#  aya düşen uç None kalır ve sayfa o şeklin altına tarih basmaz.
#
#  Defter BURADA duruyor çünkü iki tüketicisi var: grafik.py figürün kendi
#  alt yazısına yazar, ozet_uret.py `_sekil_tarih` olarak özete koyar. İki
#  ayrı liste bir gün sessizce ayrışırdı. Hangi figürün hangi serileri
#  çizdiği grafik.py'deki çizimle birebir aynı olmak zorunda — duman
#  sınaması bunu figür figür soruyor.
# ═══════════════════════════════════════════════════════════════════════
KURESEL_SEKILLER = ("05-kuresel-gida.html", "06-urun-kirilimi.html",
                    "07-uc-olcek.html", "08-fed-patikasi.html",
                    "09-gecis-profili.html")


def sekil_saatleri(M: dict, G: dict | None, uzun: bool = False,
                   bugun: dt.date | None = None) -> dict[str, str | None]:
    """Figür → damga. `M`/`G` = metrik.json / kuresel.json (`_uc` defterli).

    `uzun=True` figür alt yazısının yazımı ("Haziran 2026"); varsayılan site
    sözleşmesi ("06.2026", ortak/bicim ayın son gününe demirler)."""
    u = (M or {}).get("_uc") or {}
    g = (G or {}).get("_uc") or {}

    def en_eski(*adlar):
        if not adlar or any(a is None for a in adlar):
            return None
        t = min(pd.Timestamp(a) for a in adlar)
        if not ay_kapali(t, bugun):
            return None
        return ay_adi(t) if uzun else ay_damga(t)

    oni, tufe = u.get("oni"), u.get("tufe")
    defter = {
        "01-oni-tarihce.html":      en_eski(oni),                 # yalnız ONI
        "02-oni-goreceli-gida.html": en_eski(oni, tufe),          # ONI + göreceli gıda
        "03-gecikme-profili.html":  en_eski(oni, tufe),           # çapraz korelasyon
        "04-epizot.html":           en_eski(oni, tufe),           # epizot + koşulsuz ort.
    }
    if G:
        defter.update({
            "05-kuresel-gida.html": en_eski(oni, g.get("reel_gida")),
            "06-urun-kirilimi.html": en_eski(oni, g.get("kirilim")),
            "07-uc-olcek.html": en_eski(oni, g.get("reel_gida"), g.get("abd"), tufe),
            "08-fed-patikasi.html": en_eski(oni, g.get("faiz_abd")),
            "09-gecis-profili.html": en_eski(g.get("reel_gida"), g.get("abd"), tufe),
        })
    return defter

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

    # KUYRUK DOLDURULMAZ. `interpolate(limit=1)` tek başına serinin SONUNA da
    # bir ay ekliyordu: ONI 2026-06'da bitiyorken 2026-07'ye 1,39 yazıldı ve
    # tarihçeye ölçülmemiş bir ay girdi (09.09.2026'da ölçüldü). Doldurma
    # yalnız iki gerçek gözlemin ARASINDAKİ tek aylık boşluk için; uçlar
    # ölçüldüğü yerde biter.
    oni_m = (oni.reindex(gor_gida.index.union(oni.index))
             .interpolate(limit=1, limit_area="inside"))
    oni_uc, tufe_uc = uc(oni), uc(tufe)
    kanit_uc = uc(oni, tufe)          # ONI ile TÜFE'nin kıyası: en eski bacak

    saat: dict = {}
    sonuc: dict = {"_tarih": ay_damga(tufe_uc),
                   "_ay": ay_iso(tufe_uc),
                   "oni_son_ay": ay_iso(oni_uc),
                   "oni_son_ad": ay_adi(oni_uc),
                   # figür saat defterinin okuduğu uçlar (etiket; özete geçmez)
                   "_uc": {"oni": ay_iso(oni_uc), "tufe": ay_iso(tufe_uc)}}
    koy(sonuc, saat, "oni_son", _r(oni.dropna().iloc[-1]), oni_uc)
    # Her kaynağın kendi yaşı; hattın en yeni ayı TÜFE'nin ayı.
    for kod, seri in (("oni", oni), ("tufe", tufe["tufe"])):
        kayit, uy = kaynak_kaydi(kod, seri, tufe_uc)
        sonuc.update(kayit)
        if uy:
            uyar(uy)

    # ── 1. çapraz korelasyon
    # NOT: TÜFE alt endeksleri zaten 2005 sonrasında başlıyor, yani "tam" ve
    # "modern" örneklem AYNI. İkisini ayrı ayrı raporlamak sahte bir sağlamlık
    # izlenimi verir; örtüşme ölçülür ve aynıysa tek örneklem yazılır.
    sonuc["orneklem_bas"] = f"{gor_gida.index.min():%Y-%m}"
    sonuc["orneklem_son"] = f"{gor_gida.index.max():%Y-%m}"
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
        koy(sonuc, saat, f"capraz_{etiket}_en_iyi_gecikme", en["gecikme"], kanit_uc)
        koy(sonuc, saat, f"capraz_{etiket}_en_iyi_kor", en["korelasyon"], kanit_uc)
        koy(sonuc, saat, f"capraz_{etiket}_n", en["n"], kanit_uc)
        if enh:
            koy(sonuc, saat, f"capraz_{etiket}_ham_en_iyi_gecikme", enh["gecikme"], kanit_uc)
            koy(sonuc, saat, f"capraz_{etiket}_ham_en_iyi_kor", enh["korelasyon"], kanit_uc)
        print(f"   çapraz [{etiket}] gıda: en iyi gecikme {en['gecikme']} ay, "
              f"r={en['korelasyon']}, n={en['n']}"
              + (f"  ·  işlenmemiş: {enh['gecikme']} ay, r={enh['korelasyon']}" if enh else ""))

    # Örneklem özdeşliği: "tam" ve "modern" aynı n'yi veriyorsa iki ayrı
    # örneklem değildir ve öyle sunulamaz.
    if sonuc.get("capraz_tam_n") == sonuc.get("capraz_modern_n"):
        uyar("tam ve modern örneklem AYNI (TÜFE alt endeksleri 2006'da "
             "başlıyor) — iki ayrı kanıt gibi okunmamalı")
        sonuc["orneklem_ayni"] = True

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
    koy(sonuc, saat, "epizot_sayisi", len(eps), oni_uc)
    koy(sonuc, saat, "olculen_epizot", len(kayitlar), kanit_uc)
    if kayitlar:
        ort_ep = float(np.mean([k["goreceli_gida_ort"] for k in kayitlar]))
        kosulsuz = float(gor_gida.mean())
        koy(sonuc, saat, "epizot_ortalama", _r(ort_ep), kanit_uc)
        koy(sonuc, saat, "kosulsuz_ortalama", _r(kosulsuz), kanit_uc)
        koy(sonuc, saat, "epizot_fark", _r(ort_ep - kosulsuz), kanit_uc)
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
    koy(sonuc, saat, "gecis_beta", _r(beta, 3), tufe_uc)
    koy(sonuc, saat, "gecis_r2", _r(r2, 3), tufe_uc)
    koy(sonuc, saat, "gecis_n", int(len(ort)), tufe_uc)
    print(f"   geçiş katsayısı β={beta:.3f} (R²={r2:.3f}, n={len(ort)}) — "
          f"gıda aylık 1 puan artarsa manşet {beta:.2f} puan")

    # ── güncel durum
    koy(sonuc, saat, "gida_12a", _r(y["gida"].iloc[-1]), tufe_uc)
    koy(sonuc, saat, "tufe_12a", _r(y["tufe"].iloc[-1]), tufe_uc)
    koy(sonuc, saat, "goreceli_gida_son", _r(gor_gida.iloc[-1]), tufe_uc)
    koy(sonuc, saat, "hamgida_12a", _r(y["islenmemis_gida"].iloc[-1]), tufe_uc)

    # grafik tarihçesi
    sonuc["tarihce"] = [
        {"ay": f"{t:%Y-%m}", "oni": _r(oni_m.get(t)), "goreceli_gida": _r(gor_gida.get(t))}
        for t in gor_gida.loc[MODERN_BAS:].index
    ]
    # ── HÜKÜM. Kanıtın gücü ÖLÇÜTLE belirlenir. Türkiye TÜFE alt endeksleri
    # kısa olduğu için ölçülebilir epizot sayısı azdır; üçün altında bir örnekle
    # yön iddia etmek istatistik değil hikâyedir.
    n_ep = len(sonuc.get("epizot_sonrasi") or [])
    if n_ep < 3:
        hukum, metin = "yetersiz", (
            f"Ölçülebilir epizot sayısı {n_ep}. Türkiye TÜFE alt endeksleri "
            f"{ay_adi(gor_gida.index.min())} ayında başlıyor ve o tarihten bu yana "
            "yalnız bu kadar güçlü El Niño epizodu tamamlandı. Bu örneklemle "
            "El Niño'nun Türkiye gıda enflasyonuna YÖNÜ hakkında hüküm "
            "kurulamaz; ölçülen fark yönü ne olursa olsun kanıt sayılmaz.")
    else:
        hukum, metin = "olculebilir", f"{n_ep} epizot ölçüldü."
    koy(sonuc, saat, "hukum", hukum, kanit_uc)
    koy(sonuc, saat, "hukum_metin", metin, kanit_uc)
    print(f"   HÜKÜM: {sonuc['hukum']} — {sonuc['hukum_metin'][:80]}…")

    saatleri_yaz(sonuc, saat)
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
