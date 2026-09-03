#!/usr/bin/env python3
"""Enflasyon duman sınaması — ağa çıkmaz, saniyeler sürer.

Hattın ölçüm ve çizim katmanındaki sözleşmeleri sentetik veriyle sorar.
Burada sınanan her madde, bir gün gerçekten yayını durdurmuş ya da yanlış
yayımlanmış bir sonuçtur.

Koşum:  python duman.py     (çıkış kodu 0 = geçti, 1 = düştü)
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import grafik
import metrik
import veri

GECTI: list[str] = []
DUSTU: list[str] = []


def sina(ad: str, kosul: bool, ayrinti: str = "") -> None:
    (GECTI if kosul else DUSTU).append(ad if kosul else f"{ad} — {ayrinti}")
    print(f"  {'✓' if kosul else '✗'} {ad}"
          + (f"  ({ayrinti})" if ayrinti and not kosul else ""))


def _panel(n: int = 40, bekleyen: bool = False) -> pd.DataFrame:
    """Sentetik aylık SEVİYE paneli: İTO, ÜGE ve TÜFE.

    Seviye kurulur çünkü ölçüm katmanı yüzde değişimi kendisi hesaplar;
    doğrudan oran vermek, sınamayı hattın gerçekte koştuğu yoldan ayırırdı."""
    rng = np.random.default_rng(20260903)
    ay = pd.date_range("2023-01-01", periods=n, freq="MS")
    ito_o = 2.0 + rng.normal(0, 0.6, n)
    uge_o = ito_o + rng.normal(0, 0.4, n)
    tufe_o = 0.85 * ito_o + 0.25 + rng.normal(0, 0.35, n)
    kur = lambda o: pd.Series(100 * np.cumprod(1 + o / 100), index=ay)
    a = pd.DataFrame({"ito_ist": kur(ito_o), "ito_uge": kur(uge_o),
                      "tufe": kur(tufe_o)})
    if bekleyen:
        # SON AY: İTO/ÜGE geldi, TÜFE gelmedi — yayım gününün ÖNCESİ.
        a.loc[a.index[-1], "tufe"] = np.nan
    return a


# ---------------------------------------------------------------------------
# 1. MANŞET KÖPRÜSÜ son_ay()'DAN ÖNCE KOŞMALI
# ---------------------------------------------------------------------------
# 03.09.2026: köprü dolguyu yaptı ama son_ay() ondan ÖNCE çalışıp sonucu
# önbelleğe aldı; dosyaya ağustos yazıldı, analizin "güncel ayı" temmuz kaldı.
# İki sayı da kendi içinde tutarlı olduğu için hiçbir denetim yakalamadı.
print("\n▶ Yayım günü: manşet köprüsünün sırası")

_kos = next(d for d in ast.parse(Path(veri.__file__).read_text(encoding="utf-8")).body
            if isinstance(d, ast.FunctionDef) and d.name == "kos")
_cagri = [n.func.id for n in ast.walk(_kos)
          if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
          and n.func.id in ("_manset_kopru", "son_ay")]
sina("kos() içinde köprü, son_ay()'dan önce çağrılıyor",
     _cagri[:2] == ["_manset_kopru", "son_ay"], f"sıra: {_cagri}")

veri._SON_AY.pop("t", None)
_a = _panel()
_a.loc[pd.Timestamp("2026-05-01"), :] = np.nan   # ay var, TÜFE yok
sina("son_ay() TÜFE'siz ayı güncel ay saymaz",
     veri.son_ay(_a.dropna(how="all")) < pd.Timestamp("2026-05-01")
     or "tufe" not in _a.columns, str(veri.son_ay(_a.dropna(how="all"))))
veri._SON_AY.pop("t", None)

# ---------------------------------------------------------------------------
# 2. KARNE: TÜFE GELDİĞİ AN TAHMİN EKRANDAN DÜŞMEZ, KARNEYE DÖNÜŞÜR
# ---------------------------------------------------------------------------
# 03.09.2026: ağustos TÜFE'si yayımlanınca "bekleyen ay" kalmadı, 17 numaralı
# figür üretilemedi ve ZORUNLU sayıldığı için hat DURDU — çalışan on altı
# figür de kopyalanmadı, pano temmuzda kaldı.
print("\n▶ Yayımdan sonra: karne")

bp = metrik.birlesik_tahmin(_panel())
sina("TÜFE gelmiş ayda bekleyen ay YOK", not bp.get("bekleyen"))
sina("TÜFE gelmiş ayda KARNE var", bool(bp.get("karne")))

k = bp.get("karne") or {}
sina("karne gerçekleşmeyi taşıyor", k.get("gercek") is not None)
sina("karne yedi kuralın hepsini taşıyor", len(k.get("tahmin") or {}) == 7,
     str(sorted((k.get("tahmin") or {}).keys())))
sina("karne sapmayı yazıyor (tahmin − gerçekleşme)",
     all(abs(round(k["tahmin"][x] - k["gercek"], 2) - k["sapma"][x]) < 0.011
         for x in k.get("sapma", {})))

# BAKIŞ AÇISI: karne o ay tahmin edilirken ELDE OLMAYAN hiçbir şeyi
# kullanmamalı. İTO sabit kaydırması yalnız geçmiş aylardan kurulur; aynı
# sayı geçmişle yeniden hesaplanınca birebir tutmalı.
d_ = _panel()
ito_ay, _ = metrik._ito_seri(d_)
dd = pd.DataFrame({"ito": ito_ay,
                   "uge": metrik.aylik(d_["ito_uge"].dropna()),
                   "tufe": metrik.aylik(d_["tufe"].dropna())}).dropna()
g_ = dd.iloc[:-1]
elle = float(dd["ito"].iloc[-1] - (g_["ito"] - g_["tufe"]).mean())
sina("karne ileriye bakmıyor (İTO sabit kaydırma yalnız geçmişten)",
     abs(elle - k["tahmin"]["ito_sabit"]) < 0.011,
     f"elle {elle:.3f} vs karne {k['tahmin']['ito_sabit']:.3f}")
sina("karne hükmü okur diliyle kurulmuş (ondalık virgül, kod adı yok)",
     "," in k.get("hukum", "") and "_" not in k.get("hukum", ""),
     k.get("hukum", ""))

a_b = _panel(bekleyen=True)
bp_b = metrik.birlesik_tahmin(a_b)
bek = bp_b.get("bekleyen") or {}
sina("TÜFE gelmemiş ayda BEKLEYEN ay var", bool(bek))
sina("bekleyen ay yedi kuralın hepsini taşıyor",
     len(bek.get("tahmin") or {}) == 7)

# ÖNCÜLER AYNI GÜN YAYIMLANMAZ. İTO ÜGE'den bir ay öndeyken bekleyen ay,
# İKİSİNİN DE bulunduğu en son TÜFE'siz ay olmalı — yalnız serilerin son
# ayına bakan bir seçim burada hiçbir tahmin üretmiyordu.
a_o = _panel()
a_o.loc[a_o.index[-2:], "tufe"] = np.nan         # TÜFE iki ay geride
a_o.loc[a_o.index[-1], "ito_uge"] = np.nan       # ÜGE bir ay geride
bek_o = (metrik.birlesik_tahmin(a_o) or {}).get("bekleyen") or {}
sina("öncüler ayrı yayımlandığında bekleyen ay kaybolmuyor", bool(bek_o))
sina("bekleyen ay, İKİSİNİN DE bulunduğu en son TÜFE'siz ay",
     bek_o.get("ay") == a_o.index[-2].strftime("%Y-%m"), str(bek_o.get("ay")))

# ---------------------------------------------------------------------------
# 3. 17 NUMARALI FİGÜR: İKİ KİP DE ÇİZİLİR, ÜÇÜNCÜSÜ HATTI DÜŞÜRMEZ
# ---------------------------------------------------------------------------
print("\n▶ Tahmin figürü: iki kip")

sina("karne kipinde figür çiziliyor",
     grafik.sekil_17(bp, "Ağustos 2026") is not None)
sina("bekleyen kipinde figür çiziliyor",
     grafik.sekil_17(bp_b, "Ağustos 2026") is not None)
sina("ne bekleyen ne karne varsa figür ZORUNLU sayılmaz",
     not grafik.tahmin_figuru_var({"n": 30, "yaris": {}}))
sina("figür ile kos() aynı koşulu soruyor",
     grafik.tahmin_figuru_var(bp) and grafik.sekil_17(bp, "x") is not None)

# DOSYA ADI AY TAŞIMAZ: "17_agustos.html" bir ay sonra yalan söyleyen bir
# adres bırakıyordu ve sayfadaki gömme bağlantısını kırıyordu.
sina("17 numaralı çıktının adında ay adı yok",
     not any(ay.lower() in g.lower() for g in grafik.BIR_CIKTI_ADLARI
             for ay in ("ocak", "subat", "şubat", "mart", "nisan", "mayis",
                        "mayıs", "haziran", "temmuz", "agustos", "ağustos",
                        "eylul", "eylül", "ekim", "kasim", "kasım", "aralik",
                        "aralık")),
     str(grafik.BIR_CIKTI_ADLARI))

# ---------------------------------------------------------------------------
print(f"\n{'═' * 70}")
print(f"  {len(GECTI)} geçti · {len(DUSTU)} düştü")
if DUSTU:
    for d in DUSTU:
        print(f"  ✗ {d}")
    sys.exit(1)
print("  Duman sınaması temiz.")
