#!/usr/bin/env python3
"""TCMBNetRezerv duman sınaması — ağa çıkmaz, saniyeler sürer.

Hattın ölçüm katmanındaki sözleşmeleri sentetik veriyle sorar. Amaç bir
kusurun BİR KEZ düzeltilip ikinci kez geri gelmesini engellemek: burada
sınanan her madde, bir gün gerçekten yanlış yayımlanmış bir sayıdır.

Koşum:  python duman.py     (çıkış kodu 0 = geçti, 1 = düştü)
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

import altin_etkisi as ae

GECTI: list[str] = []
DUSTU: list[str] = []


def sina(ad: str, kosul: bool, ayrinti: str = "") -> None:
    (GECTI if kosul else DUSTU).append(ad if kosul else f"{ad} — {ayrinti}")
    print(f"  {'✓' if kosul else '✗'} {ad}" + (f"  ({ayrinti})" if ayrinti and not kosul else ""))


def _gunler(n: int) -> pd.DatetimeIndex:
    return pd.bdate_range("2026-01-05", periods=n)


# ---------------------------------------------------------------------------
# 1–5. Taşınan fiyat: ortadaki taşıma tatildir, sondaki taşıma kesintidir
# ---------------------------------------------------------------------------
# 27.08.2026'da ölçüldü: fiyat serisi 918 iş gününün 14'ünde taşınmıştı ve
# fiyat etkisinin SIFIR çıktığı günlerin tamamı (14/14) bu taşımalardan
# doğuyordu — gerçek bir kotasyonla ölçülmüş tek bir sıfır yoktu. Sayfa o
# sıfırı "günün fiyat etkisi 0,00 milyar dolar" diye yayımlıyordu.
print("\n▶ Ölçülemeyen fiyat günleri")

for ad, kaynaklar, beklenen in [
    ("ortadaki tek taşıma (tatil) korunur",
     ["agort03", "ffill", "agort03", "agort03"], [False, False, False, False]),
    ("uçtaki tek taşıma maskelenir",
     ["agort03", "agort03", "agort03", "ffill"], [False, False, True, True]),
    ("uçtaki iki taşıma maskelenir",
     ["agort03", "agort03", "ffill", "ffill"], [False, True, True, True]),
    ("taşıma yoksa hiçbir gün maskelenmez",
     ["agort03", "kap03", "agort03", "agort03"], [False, False, False, False]),
    ("hiç gerçek kotasyon yoksa hepsi maskelenir",
     ["ffill", "ffill", "ffill"], [True, True, True]),
]:
    k = pd.Series(kaynaklar, index=_gunler(len(kaynaklar)))
    m = ae.olculemeyen_fiyat_gunleri(k)
    sina(ad, list(m) == beklenen, f"beklenen {beklenen}, gelen {list(m)}")

# ---------------------------------------------------------------------------
# 6–8. Ayrıştırmanın kendisi
# ---------------------------------------------------------------------------
print("\n▶ Laspeyres ayrıştırması")

i = _gunler(4)
q = pd.Series([25.0, 25.0, 26.0, 26.0], index=i)
p = pd.Series([4000.0, 4100.0, 4100.0, 4100.0], index=i)
k = pd.Series(["agort03", "agort03", "agort03", "ffill"], index=i)

ham = ae.altin_fiyat_etkisi(q, p, None)   # maskesiz kıyas
v = q * p / 1000.0
kimlik = (ham["altin_fiyat_etkisi"] + ham["altin_miktar_etkisi"]
          - (v.shift(-1) - v)).abs().max()
sina("Γ + Λ = ΔV kimliği tutuyor", kimlik < 1e-9, f"artık {kimlik:.2e}")

maskeli = ae.altin_fiyat_etkisi(q, p, k)
sina("uçtaki taşımada fiyat etkisi BOŞ, sıfır değil",
     bool(maskeli["altin_fiyat_etkisi"].iloc[2:].isna().all()
          and float(ham["altin_fiyat_etkisi"].iloc[2]) == 0.0),
     "maskesiz hâlinde 0,00 yazılıyordu")
sina("maskesiz günler maskeden etkilenmiyor",
     bool((maskeli["altin_fiyat_etkisi"].iloc[:2]
           - ham["altin_fiyat_etkisi"].iloc[:2]).abs().max() < 1e-12))

# ΔQ = 0 iken Λ fiyattan bağımsızdır: ölçülebilen sıfır boşaltılmaz.
q2 = pd.Series([25.0, 25.0, 25.0, 25.0], index=i)
m2 = ae.altin_fiyat_etkisi(q2, p, k)
lam2 = m2["altin_miktar_etkisi"].iloc[:-1]     # son satır her zaman boş (L+1 yok)
sina("miktar kımıldamadıysa Λ sıfır kalır (boşalmaz)",
     bool(lam2.notna().all() and (lam2.abs() < 1e-12).all()),
     f"gelen {list(lam2)}")

# ---------------------------------------------------------------------------
# 9. Akım: ölçülemeyen Γ, net alımı da ölçülemez yapar
# ---------------------------------------------------------------------------
print("\n▶ Net döviz alımı")

sev = pd.Series([60.0, 61.0, 61.5, 62.0], index=i)
kamu = pd.Series([6.0, 6.0, 6.0, 6.0], index=i)
ak = ae.net_doviz_alimi(sev, kamu, maskeli["altin_fiyat_etkisi"],
                        maskeli["altin_miktar_etkisi"])
sina("fiyat etkisi boşsa net alım da boş",
     bool(ak["net_doviz_alimi"].iloc[2:].isna().all()
          and ak["net_doviz_alimi"].iloc[:2].notna().all()))

# ---------------------------------------------------------------------------
# 10. Uyarı metni: gerçekten olan şeyi anlatıyor mu?
# ---------------------------------------------------------------------------
print("\n▶ Uyarı metni")

u = ae.fiyat_tasima_tanisi(k)
sina("uçtaki taşıma görünür uyarı üretiyor", bool(u))
sina("uyarı 'boş bırakıldı' diyor, 'bu taşımaya dayanıyor' demiyor",
     bool(u) and "boş bırakıldı" in u[-1] and "dayanıyor" not in u[-1],
     u[-1] if u else "uyarı yok")

# ---------------------------------------------------------------------------
# 11–13. Ons çapasının yaş eşiği: SAĞLIKLI hafta uyarı üretmemeli
# ---------------------------------------------------------------------------
# Çapa CUMA tarihlidir ve izleyen hafta (~+6 gün, Perşembe) yayımlanır; yani
# hiçbir yayım atlanmamışken bile çapanın yaşı bir sonraki yayım gününe kadar
# 13'e çıkar. Eşik 8 iken bu uyarı HER hafta Pazar–Çarşamba ateşliyordu ve
# uyarilar.json üzerinden sayfaya basılıyordu (09.09.2026'da ölçüldü: son çapa
# 28.08, ref 08.09, "11 gün önce, eşik 8"). Kapanamayan bir uyarı, yazarı
# bütün uyarıları görmezden gelmeye alıştırır — bu yüzden sağlıklı haftanın
# uyarı ÜRETMEMESİ de eşiğin sınanan bir özelliğidir.
print("\n▶ Ons çapasının yaş eşiği")

_CUMA = pd.Timestamp("2026-08-28")          # çapanın tarihi (Cuma)
_capalar = pd.DataFrame({"ons": [25.0], "kaynak": ["irfcl_pdf"]},
                        index=pd.DatetimeIndex([_CUMA], name="tarih"))
_bos_seri = pd.Series(dtype=float)


def _tazelik_uyarisi(ref: pd.Timestamp) -> list[str]:
    """Yalnız yaş uyarısını süzer: öbür tanılar boş girdiyle zaten susar."""
    u = ae.altin_tanilari(_capalar, _bos_seri, _bos_seri, pd.DataFrame(),
                          bugun=ref)
    return [x for x in u if x.startswith("ALTIN MİKTAR TAZELİĞİ")]


_carsamba = _CUMA + pd.Timedelta(days=12)   # izleyen haftanın Çarşamba'sı
sina("sağlıklı hafta (Cuma çapası + 12 gün) uyarı ÜRETMEZ",
     not _tazelik_uyarisi(_carsamba),
     f"eşik {ae.ONS_TASIMA_UYARI_GUN}, gelen {_tazelik_uyarisi(_carsamba)}")
sina("bir yayım atlanınca (17 gün) uyarı GELİR",
     bool(_tazelik_uyarisi(_CUMA + pd.Timedelta(days=17))),
     f"eşik {ae.ONS_TASIMA_UYARI_GUN} — atlanan yayım görünmüyor")
# Eşiğin kendisi de sınanır: sağlıklı haftanın 13'ü ile atlanan yayımın 20'si
# arasında kalmalı. Aksi hâlde iki maddeden biri sessizce anlamını yitirir.
sina("eşik sağlıklı hafta ile atlanan yayım ARASINDA",
     13 < ae.ONS_TASIMA_UYARI_GUN < 20,
     f"eşik {ae.ONS_TASIMA_UYARI_GUN}")

# ---------------------------------------------------------------------------
# 14–16. Özetin ETİKET/SAAT ayrımı
# ---------------------------------------------------------------------------
# 09.09.2026'da ölçüldü: sekiz özet alanı `GG.AA` yazımını `_tarih` sonekiyle
# taşıyordu. O sonek sözleşmede SAAT demek; bültenin karanlık denetimi de
# sayfadaki canlı değer bileşeni de alanı saat sanıp çözemiyor ve SESSİZCE
# atlıyordu — sekiz alan bayatlık denetiminin tamamen dışındaydı.
print("\n▶ Özet: etiket ile saat ayrı anahtarlar")

import json as _json
import os as _os
import re as _re

_ozet_kaynak = pathlib.Path(__file__).with_name("ozet_uret.py").read_text(encoding="utf-8")
sina("kısa gün yazımı `_etiket` anahtarına yazılıyor",
     'f"u{i}_etiket"' in _ozet_kaynak and 'f"ak_g{i}_etiket"' in _ozet_kaynak,
     "etiket yeniden `_tarih` sonekine döndü")
sina("`_tarih` alanları TAM yazımla (%d.%m.%Y) kuruluyor",
     not _re.search(r'_tarih"\]\s*=\s*r\["Tarih"\]\.strftime\("%d\.%m"\)',
                    _ozet_kaynak),
     "bir saat alanı yıl taşımıyor")

_ozet_yol = pathlib.Path(__file__).with_name("ozet.json")
if _ozet_yol.exists():
    _o = _json.loads(_ozet_yol.read_text(encoding="utf-8"))
    _cozulemeyen = [k for k, v in _o.items()
                    if k.endswith("_tarih") and isinstance(v, str)
                    and v != "-" and not _re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", v)
                    and not _re.fullmatch(r"\d{2}\.\d{4}", v)]
    sina("özetteki her `_tarih` biçim sözleşmesine uyuyor",
         not _cozulemeyen, f"çözülemeyen: {_cozulemeyen}")

# ---------------------------------------------------------------------------
# 17. Haftalık yayım alınamazsa okur bunu GÖRÜR
# ---------------------------------------------------------------------------
# 09.09.2026'da ölçüldü: haftalık gözlem çekimi düştüğünde tek iz ekrana basılan
# bir satırdı; `uyarilar` listesi kodda SONRA kuruluyordu, yani hata ne uyarı
# kaydına ne sayfaya giriyordu. Bu bacak hattın en hassas çapasıdır (swap ve
# altın miktarı) ve donduğunda günlük seri sessizce aylık çapaya düşer.
print("\n▶ Haftalık yayım alınamazsa")

_net_kaynak = pathlib.Path(__file__).with_name("net_rezerv.py").read_text(encoding="utf-8")
_ekleme = _net_kaynak.find("uyarilar.append(pdf_uyarisi)")
_kurulum = _net_kaynak.find("uyarilar = tazelik_denetimi(")
sina("düşen haftalık çekim uyarı listesine giriyor",
     _ekleme > 0 and _kurulum > 0 and _ekleme > _kurulum,
     "hata yalnız ekrana basılıyor; okur görmüyor "
     f"(ekleme {_ekleme}, liste kurulumu {_kurulum})")

# ---------------------------------------------------------------------------
# 18–24. Net altın: fiyat etkisi BRÜT değil NET altınla kurulur (05.10.2026)
# ---------------------------------------------------------------------------
# Ölçüldü: brüt altınla kurulan Γ net pozisyondan fazla düşülüyordu, çünkü
# TCMB'nin altın cinsinden yükümlülükleri (zorunlu karşılık, bankalar, yurt
# dışı bankalar, Hazine) de yeniden değerleniyor. Brüt altınla kurulan
# akımın Γ'ya eğimi 2026'da −0,27 (t −3,5); net altınla +0,15 (t 1,3)
# (Londra fiyatıyla, birleşik bloklar hariç).
print("\n▶ Net altın")

import inspect as _inspect

i5 = _gunler(5)
_qb = pd.Series([25.0] * 5, index=i5)
_qy = pd.Series([10.0] * 5, index=i5)
_p = pd.Series([4000.0, 4100.0, 4050.0, 4050.0, 4150.0], index=i5)
_k = pd.Series(["agort03"] * 5, index=i5)
_sev = pd.Series([60.0, 61.5, 60.75, 60.75, 62.25], index=i5)   # yalnız yeniden değerleme
_kamu = pd.Series([6.0] * 5, index=i5)
_a = ae.akim_ayristir(_qb, _qy, _p, _k, _sev, _kamu)
sina("Γ net altınla kuruluyor: (25 − 10) × 100 / 1000 = 1,5",
     abs(float(_a["altin_fiyat_etkisi"].iloc[0]) - 1.5) < 1e-12,
     f"gelen {_a['altin_fiyat_etkisi'].iloc[0]} (brüt altın 2,5 verirdi)")
sina("yalnız yeniden değerleme varsa net alım SIFIR",
     bool((_a["net_doviz_alimi"].iloc[:-1].abs() < 1e-12).all()),
     f"gelen {list(_a['net_doviz_alimi'].iloc[:-1])}")
sina("altın değeri tanısı BRÜT kalıyor (rezervdeki kalem)",
     abs(float(_a["altin_deger_ima"].iloc[0]) - 100.0) < 1e-12,
     f"gelen {_a['altin_deger_ima'].iloc[0]}")
_imza = _inspect.signature(ae.arindirma_hatti).parameters["yukumluluk_gram"]
sina("yükümlülük girdisinin varsayılanı YOK (unutulan çağrı yeri brüte dönmez)",
     _imza.default is _inspect.Parameter.empty)
sina("hat yükümlülük serisini çekip ayrıştırmaya veriyor",
     "yukumluluk_gram=altin_yuk" in _net_kaynak
     and "altin_yuk = fetch_grup(ALTIN_YUKUMLULUK_SERIES" in _net_kaynak)
_kod_m = _re.search(r"ALTIN_YUKUMLULUK_SERIES = \{(.*?)\n\}", _net_kaynak, _re.S)
_kodlar = set(_re.findall(r'"(\w+)":', _kod_m.group(1))) if _kod_m else set()
sina("çekilen kalemler = yükümlülük tanımının kalemleri (tek liste)",
     _kodlar == set(ae.YUKUMLULUK_KALEMLERI), f"çekilen {_kodlar}")
sina("çevrimdışı yeniden üretim aynı ayrıştırmayı çağırıyor",
     "akim_ayristir(" in _inspect.getsource(ae._gunlukten_uret))

# Yükümlülük serisi: gram → ons, kalem açılmadan önceki haftalar sıfır,
# açıldıktan SONRA boş gelen hafta çapa olmaz, eksik kalem hata verir.
_cuma = pd.DatetimeIndex(["2026-01-02", "2026-01-09", "2026-01-16"])
_gram = pd.DataFrame({c: [ae.ONS_GRAM * 1e6] * 3 for c in ae.YUKUMLULUK_KALEMLERI},
                     index=_cuma)
_gram.loc[_cuma[0], "yd_banka_g"] = float("nan")       # kalem henüz açılmamış
_gram.loc[_cuma[1], "banka_g"] = float("nan")          # açıldıktan sonra boş
_ys = ae.yukumluluk_ons_serisi(_gram, pd.bdate_range("2026-01-02", "2026-01-20"))
sina("gram → milyon ons: beş kalem × 1 mn ons = 5 (son çapada)",
     abs(float(_ys.loc["2026-01-16", "ons_yukumluluk"]) - 5.0) < 1e-9,
     f"gelen {_ys.loc['2026-01-16', 'ons_yukumluluk']}")
sina("açılmadan önceki hafta sıfır sayılır (ilk çapa 4 mn ons)",
     abs(float(_ys.loc["2026-01-02", "ons_yukumluluk"]) - 4.0) < 1e-9,
     f"gelen {_ys.loc['2026-01-02', 'ons_yukumluluk']}")
sina("açıldıktan sonra boş gelen hafta çapa değil, ara değer",
     _ys.loc["2026-01-09", "ons_yukumluluk_kaynak"] == "ara_deger",
     f"gelen {_ys.loc['2026-01-09', 'ons_yukumluluk_kaynak']}")
try:
    ae.yukumluluk_ons_serisi(_gram.drop(columns=["zk_g"]), _cuma)
    _hata, _tur = False, "hata yok"
except RuntimeError:
    _hata, _tur = True, ""
except Exception as _ex:                       # noqa: BLE001 — teşhis adıyla düşsün
    _hata, _tur = False, f"adlandırılmamış {type(_ex).__name__}"
sina("eksik kalem sessizce brüte düşmez, ADIYLA hata verir", _hata, _tur)
sina("yükümlülük çapası sağlıklı haftada uyarı üretmez, atlanan yayımda üretir",
     not ae.yukumluluk_tazelik_tanisi(_CUMA, bugun=_CUMA + pd.Timedelta(days=13))
     and bool(ae.yukumluluk_tazelik_tanisi(_CUMA, bugun=_CUMA + pd.Timedelta(days=20))))

# Sızıntı tanısı: fazla düşülen fiyat etkisi akımda ters yönlü eğim bırakır.
_rng = np.random.default_rng(7)
_iz = pd.bdate_range("2026-01-05", periods=150)
_gam = pd.Series(_rng.normal(0, 1.5, 150), index=_iz)
_temiz = pd.Series(_rng.normal(0, 1.0, 150), index=_iz)
sina("sızıntı tanısı temiz akımda susuyor", not ae.sizinti_tanisi(_temiz, _gam, None))
sina("sızıntı tanısı fazla düşülen akımda (−0,4·Γ) ateşliyor",
     bool(ae.sizinti_tanisi(_temiz - 0.4 * _gam, _gam, None)))
# Birleşik (çok seanslı) tek nokta: Γ ve akım birlikte büyük. Ölçüldü
# (19.03.2026): kaldıracı tek başına eğimi taşıyordu. `haric` ile düşülür.
_gam2, _ak2 = _gam.copy(), _temiz.copy()
_gam2.iloc[100], _ak2.iloc[100] = -8.5, -12.0
_bir2 = pd.Series(False, index=_iz)
_bir2.iloc[100] = True
sina("tek birleşik nokta maskesiz tanıyı ateşliyor (sınamanın kendisi arızayı üretiyor)",
     bool(ae.sizinti_tanisi(_ak2, _gam2, None)))
sina("birleşik etiket regresyondan düşülünce tanı susuyor",
     not ae.sizinti_tanisi(_ak2, _gam2, _bir2))
_imza_s = _inspect.signature(ae.sizinti_tanisi).parameters["haric"]
sina("sızıntı tanısında birleşik maskenin varsayılanı YOK",
     _imza_s.default is _inspect.Parameter.empty)
sina("iki çağrı yeri de birleşik maskeyi veriyor",
     _inspect.getsource(ae).count('out["akim_birlesik"])') >= 2)

# ---------------------------------------------------------------------------
# 25–29. Bayram arifesi: ortadaki taşıma birleşik akım olur (05.10.2026)
# ---------------------------------------------------------------------------
# Ölçüldü: BİST yarım günde kapalıyken TCMB bilançoyu yayımlıyor ve altını
# yeniden değerliyor; arifeden önceki günün akımı iki günlük fiyat etkisiyle
# 0,89 korelasyonlu (11 vaka). 28.10.2025'te akım bir gün −1,91, ertesi gün
# +7,45 milyar dolar yazılmıştı.
print("\n▶ Bayram arifesi (ortadaki fiyat taşıması)")

for ad, kaynaklar, beklenen in [
    ("tek arife: önceki gün boş, toplam arifeye",
     ["agort03", "agort03", "ffill", "agort03", "agort03"], [(["1"], "2")]),
    ("iki arka arkaya taşıma: iki gün boş, toplam ikincisine",
     ["agort03", "ffill", "ffill", "agort03"], [(["0", "1"], "2")]),
    ("uçtaki taşıma birleştirilmez (ölçülemeyen gün ayrı kural)",
     ["agort03", "agort03", "agort03", "ffill"], []),
    ("serinin başındaki taşıma birleştirilmez (öncesi yok)",
     ["ffill", "agort03", "agort03"], []),
]:
    _ix = _gunler(len(kaynaklar))
    _bl = ae.arife_bloklari(pd.Series(kaynaklar, index=_ix))
    _gelen = [([str(_ix.get_loc(t)) for t in bos], str(_ix.get_loc(h))) for bos, h in _bl]
    sina(ad, _gelen == beklenen, f"beklenen {beklenen}, gelen {_gelen}")

_ix = _gunler(5)
_df = pd.DataFrame({"net_doviz_alimi": [1.0, -2.0, 5.0, 0.5, float("nan")]}, index=_ix)
_kk = pd.Series(["agort03", "agort03", "ffill", "agort03", "agort03"], index=_ix)
_b, _isr = ae.birlesik_akim(_df, _kk, ["net_doviz_alimi"])
sina("birleşik akım toplamı korur (birikim değişmez)",
     abs(_b["net_doviz_alimi"].sum() - _df["net_doviz_alimi"].sum()) < 1e-12
     and abs(float(_b.loc[_ix[2], "net_doviz_alimi"]) - 3.0) < 1e-12
     and pd.isna(_b.loc[_ix[1], "net_doviz_alimi"]) and bool(_isr.loc[_ix[2]]),
     f"gelen {list(_b['net_doviz_alimi'])}")
_df2 = _df.copy(); _df2.loc[_ix[1], "net_doviz_alimi"] = float("nan")
_b2, _ = ae.birlesik_akim(_df2, _kk, ["net_doviz_alimi"])
sina("bloktaki boş gün birleşik değeri de boş bırakır (sıfır sayılmaz)",
     pd.isna(_b2.loc[_ix[2], "net_doviz_alimi"]))

# ---------------------------------------------------------------------------
# Tanılar — kör ya da kaymış bir tanı "sorun yok" diye okunur
# ---------------------------------------------------------------------------
# (1) Zincirleme sapması: miktar sabitken Σ Γ = Q·[P(T) − P(çıpa)] KİMLİKTİR,
# yani D_T tam sıfır olmalı. Γ(L) fiyatı L+1'e yürüttüğü için T son akım
# etiketinin ERTESİ günüdür; P(son etiket) ile kurulan doğrudan etki son
# günün fiyat etkisini eksik sayar ve sapma kimlikten doğar (05.10.2026'ya kadar
# böyleydi: yayımlanan +2,16, doğrusu +1,46).
print("\n▶ Tanılar")
_ix = _gunler(8)
_q = pd.Series(10.0, index=_ix)
_p = pd.Series([4000.0, 4010, 3990, 4050, 4100, 4080, 4120, 4150], index=_ix)
_g = ae.altin_fiyat_etkisi(_q, _p, None)["altin_fiyat_etkisi"]
_dt, _ = ae.zincirleme_tanisi(_g, _q, _p, str(_ix[0].date()))
sina("zincirleme sapması sabit miktarda SIFIR (doğrudan etki son etiketin ertesi gününe)",
     _dt is not None and abs(_dt) < 1e-12, f"D_T {_dt}")

# (2) Değerleme fiyatı tanısı: "ima" çapasında miktar V/P'den kurulur, sapma
# cebirsel olarak sıfırdır — o çapa tanıya bir şey söylemez ve sayılmamalı;
# bağımsız yayımlanan miktarda (IRFCL PDF) sapma uyarı üretmeli.
_ix = _gunler(10)
_fy = pd.Series(4000.0, index=_ix)
_capa = pd.DataFrame({"ons": [25.0, 25.0], "kaynak": ["ima", "irfcl_pdf"]},
                     index=[_ix[3], _ix[8]])
_deger = pd.Series(float("nan"), index=_ix)
_deger[_ix[3]] = 25.0 * 4000.0            # ima: V/Q = P (cebirsel)
_deger[_ix[8]] = 25.0 * 4400.0            # PDF: değerleme fiyatı %10 yukarıda
_etki = pd.DataFrame({"bennet_fark": [0.0] * 10, "altin_fiyat_etkisi": [0.0] * 10}, index=_ix)
_u = ae.altin_tanilari(_capa, _deger, _fy, _etki, bugun=_ix[-1])
_fiyat_u = [x for x in _u if x.startswith("ALTIN FİYAT TANISI")]
sina("fiyat tanısı bağımsız çapada ateşliyor, ima çapasını saymıyor",
     len(_fiyat_u) == 1 and _ix[8].strftime("%d.%m.%Y") in _fiyat_u[0], f"{_fiyat_u}")
sina("fiyat tanısı sayıyı biçim sözleşmesiyle yazıyor (yüzde önde, ondalık virgül)",
     bool(_fiyat_u) and "%10,0" in _fiyat_u[0] and "4.400" in _fiyat_u[0], f"{_fiyat_u}")
import contextlib, io  # noqa: E401,E402
_kor = io.StringIO()
with contextlib.redirect_stdout(_kor):
    ae.altin_tanilari(_capa.iloc[:1], _deger, _fy, _etki, bugun=_ix[-1])
sina("çapaların hepsi ima ise tanının KÖR olduğu koşu çıktısına yazılıyor",
     "ölçülemedi" in _kor.getvalue(), repr(_kor.getvalue()[:120]))

# ---------------------------------------------------------------------------
# Birikim çıpası: birleşik bloğun İÇİNE düşen çıpa önceki etiketleri sayar
# ---------------------------------------------------------------------------
print("\n▶ Birikim çıpası ve birleşik bloklar")
_ix = _gunler(6)
_ak = pd.Series([1.0, float("nan"), 3.0, -1.0, 2.0, 0.5], index=_ix)
_bl = [([_ix[1]], _ix[2])]                    # blok: 1 boş, toplam 2'ye
_ok = ae.birikimli_akim(_ak, str(_ix[1].date()), _bl)
sina("bloğun ilk boş etiketi geçerli çıpa (birikim toplamı kapsar)",
     abs(float(_ok.dropna().iloc[0]) - 3.0) < 1e-12, f"{list(_ok)}")
try:
    ae.birikimli_akim(_ak, str(_ix[2].date()), _bl)
    _hata = False
except RuntimeError:
    _hata = True
sina("çıpa birleşik hedef etiketse görünür hata (önceki etiketi saymaz)", _hata)
sina("çıpa Londra fiyatından önceyse uyarı, sonraysa sessiz",
     bool(ae.cipa_tanisi("2023-06-01", pd.Timestamp("2023-11-17")))
     and not ae.cipa_tanisi("2026-02-27", pd.Timestamp("2023-11-17"))
     and not ae.cipa_tanisi("2023-06-01", None))

# ---------------------------------------------------------------------------
# Londra fiyatı — değerleme saatindeki uluslararası fiyat (05.10.2026)
# ---------------------------------------------------------------------------
# Ölçüldü: TCMB bilançosu altını Londra sabah fiksingi saatinde (10:30)
# değerliyor; BİST ağırlıklı ortalaması değerlemeyi açıklamıyordu (katsayı
# 0,06, t 0,6) ve akıma günde ~0,6 milyar USD gürültü yazıyordu.
print("\n▶ Londra fiyatı")


def _barlar(gunler, saatler, deger, sembol="IGLN.L"):
    """Londra YEREL saatinde başlayan saatlik barlar (indeks UTC başlangıç)."""
    ix, v = [], []
    for gun in gunler:
        for h in saatler:
            yerel = pd.Timestamp(f"{gun} {h:02d}:00", tz="Europe/London")
            ix.append(yerel.tz_convert("UTC"))
            v.append(deger(gun, h))
    return pd.Series(v, index=pd.DatetimeIndex(ix))


# Yaz saati (Temmuz) ve kış saati (Ocak): bar başlangıcı 09:00 ve 10:00
# (Londra) → bitişi 10:00 ve 11:00; 11:00'de başlayan bar dışarıda kalır.
_b = _barlar(["2026-07-06", "2026-01-05"], [8, 9, 10, 11],
             lambda gun, h: {8: 1.0, 9: 10.0, 10: 20.0, 11: 99.0}[h])
_lg = ae.londra_gunluk({"IGLN.L": _b}, pd.Timestamp("2026-07-10 00:00", tz="UTC"))
sina("gün değeri 10:00 ve 11:00'de BİTEN iki barın ortalaması (yaz ve kış saati)",
     list(_lg["IGLN.L"].round(9)) == [15.0, 15.0], f"{_lg.to_dict()}")
# Kapanmamış bar ölçüm değildir: 10:00–11:00 barı 10:30 UTC+1'de (yaz) kapanmadı.
_simdi = pd.Timestamp("2026-07-06 10:30", tz="Europe/London").tz_convert("UTC")
_b_yaz = _barlar(["2026-07-06"], [8, 9, 10, 11],
                 lambda gun, h: {8: 1.0, 9: 10.0, 10: 20.0, 11: 99.0}[h])
_lg2 = ae.londra_gunluk({"IGLN.L": _b_yaz}, _simdi)
sina("kapanmamış bar kullanılmaz (tek kapanmış bar alınır)",
     len(_lg2) == 1 and abs(float(_lg2["IGLN.L"].iloc[0]) - 10.0) < 1e-12, f"{_lg2.to_dict()}")
_b_yarim = _b.copy()
_b_yarim.index = _b_yarim.index + pd.Timedelta(minutes=30)
_lg3 = ae.londra_gunluk({"IGLN.L": _b_yarim}, pd.Timestamp("2026-07-10", tz="UTC"))
sina("saat başında bitmeyen bar alınmaz", _lg3.empty, f"{_lg3.to_dict()}")

# Arşiv kazanır: yayımlanmış bir akımın girdisi yeni indirmeyle değişmez.
_ar = pd.DataFrame({"IGLN.L": [10.0, 11.0]},
                   index=pd.DatetimeIndex(["2026-07-06", "2026-07-07"], name="tarih"))
_yn = pd.DataFrame({"IGLN.L": [10.5, 11.0, 12.0], "SGLD.L": [50.0, 55.0, 60.0]},
                   index=pd.DatetimeIndex(["2026-07-06", "2026-07-07", "2026-07-08"]))
_bir, _fark = ae.londra_arsiv_birlestir(_ar, _yn)
sina("arşivdeki değer korunur, yeni gün ve boş hücre eklenir",
     float(_bir.loc["2026-07-06", "IGLN.L"]) == 10.0
     and float(_bir.loc["2026-07-08", "IGLN.L"]) == 12.0
     and float(_bir.loc["2026-07-06", "SGLD.L"]) == 50.0, f"{_bir.to_dict()}")
sina("arşivle ayrışan hücre sayılır (tanı)", _fark == 1, f"fark {_fark}")

# Ölçek: TCMB değerleme fiyatı / ETC, son çapaların medyanı; çapa yetmezse yok.
_etc = pd.Series([10.0] * 20, index=pd.bdate_range("2026-01-05", periods=20))
_df_ = pd.Series([4000.0, 4010.0, 3990.0],
                 index=pd.DatetimeIndex(["2026-01-09", "2026-01-16", "2026-01-23"]))
_k, _n = ae.londra_olcek(_etc, _df_)
sina("ölçek çapaların medyanı (400)", _k == 400.0 and _n == 3, f"{_k}, {_n}")
_k2, _n2 = ae.londra_olcek(_etc, _df_.iloc[:2])
sina("üç çapadan azsa ölçek YOK (seviye uydurulmaz)", _k2 is None and _n2 == 2)

# Birleşik seri: Londra'nın ilk gününden önce BİST, seviyesi o günde ölçeklenir;
# sonrası yalnız Londra, eksik gün taşınır (BİST'e dönülmez).
_ix = _gunler(6)
_bist = pd.Series([100.0, 102.0, 101.0, 103.0, 104.0, 105.0], index=_ix)
_lo = pd.Series([float("nan"), float("nan"), 202.0, float("nan"), 210.0, 212.0], index=_ix)
_fs = ae.fiyat_serisi(_bist, pd.Series(dtype=float), _ix, _lo)
sina("dikişte sahte hareket yok: S−1 → S değişimi BİST değişiminin ölçeklisi",
     abs(float(_fs["altin_fiyat"].iloc[2] - _fs["altin_fiyat"].iloc[1]) - 2.0 * (101.0 - 102.0)) < 1e-9,
     f"{list(_fs['altin_fiyat'])}")
sina("Londra başladıktan sonra eksik gün BİST'le değil taşımayla dolar",
     float(_fs["altin_fiyat"].iloc[3]) == 202.0
     and _fs["altin_fiyat_kaynak"].iloc[3] == "ffill"
     and _fs["altin_fiyat_kaynak"].iloc[4] == "londra", f"{list(_fs['altin_fiyat_kaynak'])}")
sina("Londra serisi yoksa BİST serisi aynen kalır",
     list(ae.fiyat_serisi(_bist, pd.Series(dtype=float), _ix, None)["altin_fiyat"]) == list(_bist))
_imza_l = _inspect.signature(ae.fiyat_serisi).parameters["londra"]
_imza_h = _inspect.signature(ae.arindirma_hatti).parameters["londra_fiyati"]
sina("Londra girdisinin varsayılanı YOK (iki imzada da)",
     _imza_l.default is _inspect.Parameter.empty and _imza_h.default is _inspect.Parameter.empty)
sina("hat Londra serisini kurup ayrıştırmaya veriyor",
     "londra_fiyati=londra_p" in _net_kaynak and "londra_hazirla(" in _net_kaynak)

# İndirme düşerse sebep okura yazılır ve arşivin son günü söylenir.
_ar2 = pd.DataFrame({"IGLN.L": [10.0], "SGLD.L": [50.0]},
                    index=pd.DatetimeIndex(["2026-07-06"], name="tarih"))
_p_, _a_, _u_, _ = ae.londra_hazirla(None, pd.Timestamp("2026-07-10", tz="UTC"),
                                     pd.Series(dtype=float), _ar2, "kaynak yanıt vermedi")
sina("indirme düşünce okura sebep ve arşivin son günü yazılır",
     any("ALINAMADI" in x and "06.07.2026" in x for x in _u_), f"{_u_}")
_p_, _a_, _u_, _ = ae.londra_hazirla(None, pd.Timestamp("2026-07-10", tz="UTC"),
                                     pd.Series(dtype=float), None, "kaynak yanıt vermedi")
sina("arşiv de yoksa seri kurulmaz ve okura söylenir",
     _p_ is None and any("KURULAMADI" in x for x in _u_), f"{_u_}")
_oz_kaynak = (pathlib.Path(__file__).with_name("ozet_uret.py")).read_text(encoding="utf-8")
sina("fiyat kaynağının her kodunun okur adı var (sayfaya kod etiketi gitmez)",
     all(f'"{k}":' in _oz_kaynak for k in ("londra", "agort03", "kap03", "ffill")))
sina("Londra fiyatının indirmesi bağımlılık listesinde",
     "yfinance" in (pathlib.Path(__file__).with_name("requirements.txt")).read_text(encoding="utf-8"))

# ---------------------------------------------------------------------------
print(f"\n{'═' * 70}")
print(f"  {len(GECTI)} geçti · {len(DUSTU)} düştü")
if DUSTU:
    for d in DUSTU:
        print(f"  ✗ {d}")
    sys.exit(1)
print("  Duman sınaması temiz.")
