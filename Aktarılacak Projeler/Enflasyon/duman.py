#!/usr/bin/env python3
"""Enflasyon duman sınaması — ağa çıkmaz, saniyeler sürer.

Hattın ölçüm ve çizim katmanındaki sözleşmeleri sentetik veriyle sorar.
Burada sınanan her madde, bir gün gerçekten yayını durdurmuş ya da yanlış
yayımlanmış bir sonuçtur.

Koşum:  python duman.py     (çıkış kodu 0 = geçti, 1 = düştü)
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import inspect as _inspect
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

# AYNI GÜVENCE 15 VE 16 İÇİN DE (10.09.2026'da ölçüldü). Yukarıdaki madde
# yalnız Şekil 17'yi sınıyordu; 15 ile 16 bir basamak YUKARIDA, `kos()`un
# `if bp:` kapısında aynı tuzağa düşüyordu. Örneklem 18 ayın altındayken ölçüm
# katmanı `{"n": …, "not": "örneklem yetersiz"}` yazar; o sözlük TRUTHY olduğu
# için ikisi de ZORUNLU çıktı sayılıyordu. Sonuç iki ayrı arıza: Şekil 16 None
# döner, zorunlu çıktı eksik kalır ve HAT DURUR (çalışan on altı figür de
# tazelenmez); Şekil 15 ise uydurma katsayıyla çizilir — gerçek panelle
# ölçüldü, okura "eğim 0,000 · R² 0,000 · artık σ 0,000" basıyordu.
_yetersiz = {"n": 11, "not": "örneklem yetersiz"}
sina("yetersiz örneklemde saçılım ZORUNLU sayılmaz",
     not grafik.sacilim_figuru_var(_yetersiz))
sina("yetersiz örneklemde yarış ZORUNLU sayılmaz",
     not grafik.yaris_figuru_var(_yetersiz))
sina("yetersiz örneklemde saçılım UYDURMA katsayı basmıyor",
     grafik.sekil_15(_yetersiz, _a, "08.2026") is None)
sina("yetersiz örneklemde yarış figürü çizilmiyor",
     grafik.sekil_16(_yetersiz, "08.2026") is None)
sina("15 ile kos() aynı koşulu soruyor",
     grafik.sacilim_figuru_var(bp) == (grafik.sekil_15(bp, _a, "x") is not None))
sina("16 ile kos() aynı koşulu soruyor",
     grafik.yaris_figuru_var(bp) == (grafik.sekil_16(bp, "x") is not None))
# YAPISAL KİLİT: kapı `if bp:`e geri dönerse tuzak da geri gelir.
sina("kos() figürleri `if bp:` ile değil KENDİ koşuluyla alıyor",
     "if sacilim_figuru_var(bp):" in _inspect.getsource(grafik.kos)
     and "if yaris_figuru_var(bp):" in _inspect.getsource(grafik.kos))

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
# 4. ŞEKİL SAAT DEFTERİ: BAĞLAYICI BACAK, YAZIM VE ÖLÇÜLEMEYEN HÂL
# ---------------------------------------------------------------------------
# Bu hattın figürleri tek ritimde değil: kesit ölçüleri (kırpılmış ortalama,
# medyan, difüzyon) üç haneli kırılımı bekler ve ana endeksten aylarca geride
# biter. 05'in İKİ paneli de o kesite dayanır; tek ana saat basılırsa sekiz ay
# bayat bir panel bugünün TÜFE'siyle damgalanır ve okur onu bugünün yaygınlığı
# sanır. Aşağıdaki maddeler damganın hangi bacaktan geldiğini, nasıl yazıldığını
# ve ölçülemeyince ne olduğunu sorar.
print("\n▶ Şekil saat defteri")

_S05 = "05_dagilim_difuzyon.html"

sina("kesit geride ise damga KESİTİN ayı",
     veri.sekil_saatleri({"son_ay": "2026-08-01",
                          "dagilim__son_ay": "2025-12"})[_S05] == "12.2025",
     str(veri.sekil_saatleri({"son_ay": "2026-08-01",
                              "dagilim__son_ay": "2025-12"})[_S05]))

# min() YAPISAL yazılır: bugün kesit geride diye öyle kalacağı varsayılamaz.
# Sıralama tersine döndüğünde de kazanan EN ESKİ bacaktır.
sina("kesit daha TAZE olsa da damga yine en eski bacak",
     veri.sekil_saatleri({"son_ay": "2026-08-01",
                          "dagilim__son_ay": "2026-09"})[_S05] == "08.2026")

sina("kesitin kendi saati ölçülemezse figür ana saate düşer",
     veri.sekil_saatleri({"son_ay": "2026-08-01"})[_S05] == "08.2026")

# Yanlış bir tarih, tarihsizlikten kötüdür: hiç ölçüm yoksa defter None taşır
# ve bileşen o şeklin altına tarih HİÇ basmaz. Soru TEK figüre sorulmaz —
# uydurma bir gün ilk sızacağı yerde tek bir şekil olmayabilir.
_bos = veri.sekil_saatleri({})
sina("hiç ölçüm yoksa HİÇBİR figürün damgası yok (uydurma değil)",
     all(v is None for v in _bos.values()),
     str({k: v for k, v in _bos.items() if v is not None}))

# Fonlama maliyeti içinde bulunulan aya kadar var, enflasyon bacağı bir ay
# geride; figür ikisinin KARŞILAŞTIRMASI olduğu için ortak ay bağlar.
sina("reel faiz damgası fonlamanın DEĞİL enflasyonun ayı",
     veri.sekil_saatleri({"son_ay": "2026-08-01",
                          "reel__ex_post_tarih": "2026-08-01",
                          "reel__faiz_tarih": "2026-09-01"}
                         )["08_reel_faiz.html"] == "08.2026")

# AYLIK bir gözlem GÜN gibi yazılmaz: "01.08.2026" okura o GÜNÜN ölçümüymüş
# gibi görünür. Defterin tamamı ay yazımında olmalı.
_kanat = {"son_ay": "2026-08"}
_defter = veri.sekil_saatleri({"son_ay": "2026-08-01",
                               "dagilim__son_ay": "2025-12"},
                              _kanat, _kanat, _kanat)
sina("defterdeki her damga AA.YYYY yazımında",
     bool(_defter) and all(re.fullmatch(r"\d{2}\.\d{4}", v)
                           for v in _defter.values() if v),
     str(sorted({v for v in _defter.values() if v})))

# Kanat profili üretilemediğinde o figürler ÇİZİLMEZ; defterde de görünmemeli,
# yoksa var olmayan bir şekle hattın ana saati yazılırdı.
sina("kanat profili yoksa kanadın figürleri defterde yok",
     not any(k[:2] in {"10", "11", "12", "13", "14", "15", "16", "17"}
             for k in veri.sekil_saatleri({"son_ay": "2026-08-01"})))

# Figürün İÇİNDEKİ alt yazı okura sayfa damgası kadar görünür; ikisi ayrı
# kaynaktan beslenirse bir gün sessizce ayrışır.
sina("figür alt başlığı aynı tablodan, uzun yazımla",
     veri.sekil_saatleri({"son_ay": "2026-08-01",
                          "dagilim__son_ay": "2025-12"},
                         uzun=True)[_S05] == "Aralık 2025")

# İKİ TÜKETİCİ, TEK TABLO — VE TEK GİRDİ.
#
# Eski madde iki dosyada `sekil_saatleri` DİZGESİNİN geçmesini soruyordu ve
# ölçtüğünü sandığı şeyi ölçmüyordu: tablo tekti ama ona verilen KANATLAR iki
# tüketicide farklıydı. Çizim katmanı kanatları kabul koşulundan geçiriyor
# (`_uge_yukle` n VE yarış ister), özet üreticisi aynı dosyaları SÜZGEÇSİZ
# okuyup veriyordu. Bir profil dosyası var ama yetersizse çizim figürü hiç
# üretmiyor, özet o figüre defterde TARİH yazıyordu — sayfa, o koşuda
# üretilmemiş BAYAT bir figürün altına TAZE damga basıyordu; defterin
# önlemek için yazıldığı kusurun ta kendisi.
#
# Ölçüt artık GARANTİYİ ölçüyor: figürün defter girdisi ancak figür
# çiziliyorsa vardır, ve süzgeç TABLONUN İÇİNDE olduğu için ham kanat veren
# tüketiciyle süzülmüş kanat veren tüketici AYNI defteri alır.
sina("çizim ve özet katmanı saati aynı fonksiyondan alıyor",
     "sekil_saatleri" in Path(grafik.__file__).read_text(encoding="utf-8")
     and "sekil_saatleri" in (veri.PROJE / "ozet_uret.py").read_text(encoding="utf-8"))

_o_ay = {"son_ay": "2026-08-01"}
# (a) Yetersiz kanatlar: hiçbiri figür çizemez → hiçbirine defter girdisi yok.
_yetersiz_ito = {"son_ay": "2026-08"}                       # tablo YOK
_yetersiz_uge = {"son_ay": "2026-08", "n": 11}              # yaris YOK
_yetersiz_bir = {"son_ay": "2026-08", "n": 11}              # ito/uge/yaris YOK
_d = veri.sekil_saatleri(_o_ay, _yetersiz_ito, _yetersiz_uge, _yetersiz_bir)
sina("yetersiz kanat: çizilmeyen figüre defterde tarih YOK",
     not ({"10_ito_tufe.html", "11_ito_kural.html", "12_ito_takvim.html",
           "13_ito_bulut.html", "14_uge_ucler.html", "15_sacilim.html",
           "16_yaris.html", "17_tahmin.html"} & set(_d)),
     str(sorted(set(_d) - {f"0{i}_" for i in range(10)})))

# (b) HAM kanat ile SÜZÜLMÜŞ kanat aynı defteri vermeli — iki tüketicinin
#     girdisi ayrışsa bile. Süzgeç tablonun içinde olduğu için bu yapısal.
_suzulmus = (_yetersiz_ito if veri.ito_kanadi_var(_yetersiz_ito) else None,
             _yetersiz_uge if veri.uge_kanadi_var(_yetersiz_uge) else None,
             _yetersiz_bir if veri.birlesik_kanadi_var(_yetersiz_bir) else None)
sina("ham kanat veren tüketici ile süzülmüş kanat veren AYNI defteri alıyor",
     veri.sekil_saatleri(_o_ay, *_suzulmus) == _d)

# (c) Birleşik kanadın üç figürü AYRI sorulur: bir blok eksikse yalnız o
#     figür düşer, öbürlerinin girdisi kalır.
_kismi = {"son_ay": "2026-08", "n": 32, "yaris": [1], "karne": {"x": 1}}
_d2 = veri.sekil_saatleri(_o_ay, None, None, _kismi)
sina("birleşik kanatta eksik blok yalnız KENDİ figürünü düşürüyor",
     "15_sacilim.html" not in _d2 and "16_yaris.html" in _d2
     and "17_tahmin.html" in _d2, str(sorted(_d2)))

# (d) Çizim katmanı koşulu yeniden yazmıyor, veri katmanından alıyor.
sina("figür koşullarının tanımı veri katmanında (çizim onu ödünç alıyor)",
     grafik.sacilim_figuru_var is veri.sacilim_figuru_var
     and grafik.yaris_figuru_var is veri.yaris_figuru_var
     and grafik.tahmin_figuru_var is veri.tahmin_figuru_var)
sina("kanat yükleyicileri de aynı koşulu okuyor",
     all(f"veri.{f}(d)" in Path(grafik.__file__).read_text(encoding="utf-8")
         for f in ("ito_kanadi_var", "uge_kanadi_var", "birlesik_kanadi_var")))

# ---------------------------------------------------------------------------

# ── AÇIK YILDA ÇOCUK KIRILIMI GEÇ GELİR (09.09.2026) ─────────────────────────
# TÜİK manşeti ayın 3'ünde, üç haneli kırılım EVDS'e ≤17 gün sonra düşer. Üst
# seri dolu, alt tablo boş olan o ay ağırlık çözümünde şart koşulunca hiçbir
# çocuk "tam" çıkmıyor, yılın ağırlığı hiç çözülmüyor ve kesit ölçüleri
# (Şekil 05, medyan/kırpılmış/difüzyon) bir önceki yıla GERİLİYORDU
# (03.09.2026: 07.2026 → 12.2025). Alt tablonun bütünüyle boş olduğu ay
# çözüme girmez; tek tek eksik çocuk yine dışarıda kalır.
_ix = pd.date_range("2025-12-01", "2026-08-01", freq="MS")
# Üç çocuk üç ayrı eğrilikte (doğrusal · kare · karekök): doğrusal üç seri
# eşdoğrusal olur ve EKK payı tek çözümlü çıkmaz — sınama kodu değil kendi
# kurgusunu sınamış olurdu.
_t = np.arange(len(_ix), dtype=float)
_alt = pd.DataFrame({"a": 100 + 2.0 * _t,
                     "b": 100 + 0.35 * _t ** 2,
                     "c": 100 + 6.0 * np.sqrt(_t)}, index=_ix)
_ust = pd.Series(0.5 * _alt["a"] + 0.3 * _alt["b"] + 0.2 * _alt["c"], index=_ix)
_alt_bos = _alt.copy(); _alt_bos.loc[_ix[-1]] = np.nan          # Ağustos kırılımı gelmemiş
_r = metrik._agirlik_coz(_ust, _alt_bos, 2026)
sina("ağırlık çözümü: alt tablosu boş açık ay çözümü düşürmez", _r is not None,
     "Ağustos kırılımı gelmeden 2026 ağırlığı çözülmüyor — kesit önceki yıla geriler")
sina("ağırlık çözümü: boş ay çözüme girmez, dolu aylar girer",
     _r is not None and _r["n_ay"] == len(_ix) - 2, f"n_ay={_r and _r['n_ay']}")
sina("ağırlık çözümü: paylar tutuyor (0,5 · 0,3 · 0,2)",
     _r is not None and np.allclose(_r["paylar"].values, [0.5, 0.3, 0.2], atol=1e-6),
     str(_r and _r["paylar"].round(4).to_dict()))
_alt_tek = _alt.copy(); _alt_tek.loc[_ix[-1], "c"] = np.nan       # yalnız bir çocuk eksik
_r2 = metrik._agirlik_coz(_ust, _alt_tek, 2026)
sina("ağırlık çözümü: tek tek eksik çocuk yine dışarıda kalır",
     _r2 is not None and _r2["eksik_cocuk"] == 1 and "c" not in _r2["paylar"].index,
     str(_r2 and _r2["paylar"].index.tolist()))

# ---------------------------------------------------------------------------
# 5. KISMİ YAYIM: AİLE İÇİ KIYAS — AİLELER ARASI FARK TAKVİMDİR
# ---------------------------------------------------------------------------
# 09.09.2026: ölçüt 72 serinin tamamını tek en yeni aya karşı ölçüyordu. YKKE
# yapısal olarak bir ay geriden gelir ve her koşuda "1/72 seri geride" diye
# sayfaya basılıyordu; ay sonunda PKA cari ayı ilan edince TÜFE ailesinin
# altmış küsur serisi "geride" görünecekti. Yanlış alarm basan bir uyarıyı
# kimse okumaz — ölçütün yakalamak için yazıldığı 03.09 arızası da onunla
# birlikte görünmez olurdu.
print("\n▶ Kısmi yayım: aile içi kıyas")

import datetime as _dt

_AY7, _AY8, _AY9 = (pd.Timestamp(f"2026-0{i}-01") for i in (7, 8, 9))
_kodlar: dict[str, object] = dict(veri.ANA_SERI)
_kodlar.update({f"ana_{k}": None for k in veri.ANA_GRUP_AD})
_kodlar.update({f"oktg{k}": None for k in veri.OKTG_AD})
_kodlar.update(veri.BEKLENTI)
_sutun = list(_kodlar)

# KAPSAM SÖZLEŞMEDEN: kos()'un kurduğu her sütun bir aileye bağlı ve her aile
# TAZELIK'te ilanlı. Ailesiz bir sütun ölçütün görmediği yerdir.
_ailesiz = [k for k in _sutun if veri.seri_ailesi(k) is None]
sina("kos()'un kurduğu her aylık sütunun bir yayım ailesi var", not _ailesiz, str(_ailesiz))
_ilansiz = {veri.seri_ailesi(k) for k in _sutun} - set(veri.TAZELIK)
sina("her aile TAZELIK'te toleransıyla ilanlı", not _ilansiz, str(_ilansiz))
sina("İYA, hanehalkı ve PKA üç ayrı aile (ay içinde üç ayrı günde yayımlanır)",
     len({veri.seri_ailesi("pka_12a"), veri.seri_ailesi("reel_kesim_12a"),
          veri.seri_ailesi("hanehalki_12a")}) == 3)

# (a) 09.09 hâli: YKKE bir ay geride, kalan her şey ağustosta → SATIR YOK.
_bugun_hali = {k: _AY8 for k in _sutun}; _bugun_hali["ykke"] = _AY7
sina("yapısal gecikmeli YKKE kısmi yayım sayılmaz", not veri.kismi_yayim(_bugun_hali),
     str(veri.kismi_yayim(_bugun_hali)))

# (b) Ay sonu: PKA cari ayı ilan etti, TÜFE ailesi henüz geçen ayda → SATIR YOK.
_ay_sonu = {k: _AY7 for k in _sutun}
for _k in _sutun:
    if _k.startswith("pka_"):
        _ay_sonu[_k] = _AY8
sina("ay sonunda öne geçen PKA, TÜFE ailesini 'geride' saydırmaz",
     not veri.kismi_yayim(_ay_sonu), str(veri.kismi_yayim(_ay_sonu))[:160])

# (c) Ay ortası: PKA çıktı, İYA ve hanehalkı henüz çıkmadı → SATIR YOK.
_ay_ortasi = {k: _AY8 for k in _sutun}
for _k in _sutun:
    if _k.startswith("pka_"):
        _ay_ortasi[_k] = _AY9
sina("ay ortasında PKA önde, İYA/hanehalkı geride: satır yok",
     not veri.kismi_yayim(_ay_ortasi), str(veri.kismi_yayim(_ay_ortasi))[:160])

# (d) 03.09 arızası: manşet + on üç ana grup temmuzda, ailenin kalanı ağustosta
# → TEK satır, TÜFE ailesi adıyla, 14 seri, ağustos.
_uc_eylul = {k: _AY8 for k in _sutun}
for _k in ["tufe"] + [f"ana_{k}" for k in veri.ANA_GRUP_AD]:
    _uc_eylul[_k] = _AY7
_uc_eylul["ykke"] = _AY7                       # o gün de bir ay gerideydi
_u = veri.kismi_yayim(_uc_eylul)
sina("03.09 arızası (manşet ailesi geride) TEK satırla yakalanıyor", len(_u) == 1, str(_u))
sina("satır aileyi ve geride kalan sayısını adıyla yazıyor",
     bool(_u) and "TÜFE / ÖKTG / Yİ-ÜFE" in _u[0] and "14/" in _u[0]
     and "Ağustos 2026" in _u[0], (_u or [""])[0][:200])
sina("satırda manşet (TÜFE genel endeks) ilk altı adın içinde",
     bool(_u) and "TÜFE genel endeks" in _u[0].split(" — ", 1)[-1].split(".")[0])
sina("YKKE, TÜFE ailesinin satırında anılmıyor (kendi ailesi)",
     bool(_u) and "Kiracı" not in _u[0])

# (e) OKUR DİLİ: satır sayfaya olduğu gibi basılır — anahtar adı, ISO tarih,
# backtick yok. İlk yazım "ykke" anahtarını basıyordu.
_kusur = [x for x in _u if re.search(r"\b[a-z]+_[a-z]+\b|\d{4}-\d{2}|`", x)]
sina("kısmi yayım satırı okur diliyle (anahtar adı, ISO tarih, backtick yok)", not _kusur, str(_kusur)[:200])
try:
    sys.path.insert(0, str(veri.PROJE.parents[1] / "ortak"))
    import okur_dili as _od
    _b = _od.kosu_kaydi_tara(_u)
    sina("kısmi yayım satırı ortak/okur_dili koşu kaydı taramasından temiz", not _b, str(_b)[:200])
except ImportError as _ex:
    sina("ortak/okur_dili içe aktarıldı", False, str(_ex))

# (f) Durmuş seri: iki ay ve daha çok geride kalan üye "birkaç saat" değil
# "bırakmış olabilir" cümlesini alır.
_durmus = {k: _AY9 for k in _sutun}; _durmus["oktg12"] = _AY7
_ud = veri.kismi_yayim(_durmus)
sina("iki ay geride kalan üye durmuş seri olarak yazılıyor",
     len(_ud) == 1 and "bırakmış olabilir" in _ud[0] and "birkaç saat" not in _ud[0],
     str(_ud)[:200])

# (g) Ailesi tanımsız sütun sessizce atlanmaz, adıyla listelenir.
_yabanci = {k: _AY8 for k in _sutun}; _yabanci["hizmet_ufe"] = _AY7
_uy = veri.kismi_yayim(_yabanci)
sina("ailesi tanımsız sütun adıyla görünür", any("TANIMSIZ" in x for x in _uy), str(_uy)[:160])

# (h) ÖLÇÜ VAR, TÜKETİCİ VAR MI: tazelik_denetimi ölçütü gerçekten çağırıyor.
_td = next(d for d in ast.parse(Path(veri.__file__).read_text(encoding="utf-8")).body
           if isinstance(d, ast.FunctionDef) and d.name == "tazelik_denetimi")
sina("tazelik_denetimi() kısmi yayım ölçütünü çağırıyor",
     any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
         and n.func.id == "kismi_yayim" for n in ast.walk(_td)))

# ---------------------------------------------------------------------------
# 6. FAİZ BACAĞININ SAATİ GÜNDÜR; AÇIK AYIN ETİKETİ GELECEĞE DÜŞER
# ---------------------------------------------------------------------------
# 09.09.2026: özet `faiz_tarih` = "09.2026" yazıyordu — `faiz` 02.09
# kotasyonuyken açık ayın etiketi. Biçim sözleşmesi aylık damgayı ayın son
# gününe demirler: dosya 30.09.2026'yı ilan ediyordu ve sayfa sınavı geleceğe
# düşen bacağı süzüp geçtiği, karanlık denetimi eksi gün farkını eşiğin altında
# saydığı için hiçbir kapı düşmüyordu.
print("\n▶ Faiz bacağının saati")

import ozet_uret

_bugun = _dt.date(2026, 9, 9)
sina("gün varsa faiz saati kotasyonun günü (GG.AA.YYYY)",
     ozet_uret.faiz_saati("2026-09-01", "2026-09-02", _bugun) == "02.09.2026",
     str(ozet_uret.faiz_saati("2026-09-01", "2026-09-02", _bugun)))
sina("gün yoksa yalnız KAPANMIŞ ay yazılır (AA.YYYY)",
     ozet_uret.faiz_saati("2026-08-01", None, _bugun) == "08.2026")
sina("gün yoksa AÇIK ay yazılmaz (ölçülemeyen boş kalır)",
     ozet_uret.faiz_saati("2026-09-01", None, _bugun) is None)
try:
    import bicim as _bicim
    for _ay, _gun in (("2026-09-01", "2026-09-02"), ("2026-08-01", None), ("2026-09-01", None)):
        _v = ozet_uret.faiz_saati(_ay, _gun, _bugun)
        _t = _bicim.tarihe_cevir(_v) if _v else None
        sina(f"faiz saati bugünden ileri değil ({_ay!r}, {_gun!r})",
             _t is None or _t <= _bugun, f"{_v} → {_t}")
except ImportError as _ex:
    sina("ortak/bicim içe aktarıldı", False, str(_ex))

# Özet üreticisi damgayı bu fonksiyondan alıyor; ay etiketini doğrudan basan
# eski yol geri gelmemeli.
_ou = Path(ozet_uret.__file__).read_text(encoding="utf-8")
_main = next(d for d in ast.parse(_ou).body
             if isinstance(d, ast.FunctionDef) and d.name == "main")
_faiz_atama = [n for n in ast.walk(_main) if isinstance(n, ast.Assign)
               for t in n.targets if isinstance(t, ast.Subscript)
               and isinstance(t.slice, ast.Constant) and t.slice.value == "faiz_tarih"]
sina("özet üreticisi faiz_tarih'i faiz_saati() üzerinden yazıyor",
     bool(_faiz_atama) and all(
         "faiz_saati" in ast.dump(n.value) or
         (isinstance(n.value, ast.Name) and n.value.id == "_ft") for n in _faiz_atama)
     and 'reel__faiz_tarih"]).strftime("%m.%Y")' not in _ou)
sina("ölçüm katmanı faiz gününü kendisi yazıyor (reel__faiz_gun)",
     'o["reel__faiz_gun"]' in Path(metrik.__file__).read_text(encoding="utf-8"))
sina("'yayımdan bu yana N gün' özete yazılmıyor (koşu anında donan sayı)",
     "yayim_gecikme_gun" not in _ou)
_mdx = veri.PROJE.parents[1] / "site/src/content/projeler/enflasyon.mdx"
sina("proje sayfası 'yayımdan bu yana N gün' sayısını çağırmıyor",
     _mdx.exists() and 'anahtar="yayim_gecikme_gun"' not in _mdx.read_text(encoding="utf-8"),
     "sayfa yok" if not _mdx.exists() else "anahtar hâlâ çağrılıyor")
sina("proje sayfası yayım tarihini ve günlük bacağın gününü çağırıyor",
     _mdx.exists() and 'anahtar="yayim_tarihi"' in _mdx.read_text(encoding="utf-8")
     and 'anahtar="faiz_gun"' in _mdx.read_text(encoding="utf-8"))

print(f"\n{'═' * 70}")
print(f"  {len(GECTI)} geçti · {len(DUSTU)} düştü")
if DUSTU:
    for d in DUSTU:
        print(f"  ✗ {d}")
    sys.exit(1)
print("  Duman sınaması temiz.")
