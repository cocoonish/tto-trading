# -*- coding: utf-8 -*-
"""TÜFEX hattı — duman sınaması. AĞA ÇIKMAZ, saniyeler sürer, çıkış kodu 0/1.

`guncelle.py` bu dosyayı hattın adımlarından ÖNCE koşturur ve düşerse hat hiç
koşmaz. Hat türevdir (DİBS + Enflasyon depo serileri), ağa zaten çıkmaz; sınama
gerçek CSV'lerle koşar.

BURADA DURAN HER MADDE BİR ARIZAYA KARŞILIK GELİR (09.09.2026'da ölçülenler)
--------------------------------------------------------------------------
 1. SAYFA SÖZLEŞMESİ — sayfanın adıyla çağırdığı her anahtar özette var; kopya
    sözleşmesindeki her figür şekil saat defterinde ve çizim listesinde.
    Katılımcı sayısı sayfada elle yazılıydı ("63 katılımcıdan") ve anket
    değiştikçe donacaktı.
 2. SAAT YAZIMI — günlük bacak GG.AA.YYYY, anket ve mevsim bacakları AA.YYYY;
    hiçbir saat anahtarında ay adı ya da ISO yok. anket_*_tarih 08.09.2026
    yazıyordu (serinin ileri doldurulmuş son günü), oysa sayı 20.08.2026'dan
    beri yürürlükte olan Ağustos anketinden geliyor; pka_* ve mevsim_* saatsizdi
    ve sayfa onları hattın günlük saatiyle etiketliyordu.
 3. ANA SAAT — yalnız günlük bacakların en yenisi; aylık bir bacak (ayın son
    gününe demirlenir) ana saati ileri ÇEKEMEZ, donmuş 3y bacağı geri çekemez.
 4. ANKET AYI — günlük seride son basamağın ayı; basamak günü kaynak hattın
    ilan ettiği yayım günü ya da onu izleyen iş günü; aynı ayın aylık kaynak
    satırı günlük değerle birebir (ay eşlemesi yanlışsa burada düşer). Basamak
    tek sütundan aranırsa aynı değerin tekrarında görünmez olur.
 5. ŞEKİL SAAT DEFTERİ — her figür kendi bacağının saatini taşır; farklı
    cinsteki ya da birbirinden uzak bacaklar tek damgayla anlatılmaz, iki
    parçalı damga MDX anahtarına düşer, defterde null durur. Mevsim figürü
    (aylık) hattın günlük saatiyle damgalanıyordu.
 6. SINAV UYUMU — sayfa sınavının 18/18b/18c ölçütleri bu özet ve bu sayfa
    üzerinde ENGEL üretmiyor; yayının önünde duran bir denetimin yanlış alarmı
    arızanın kendisidir.
 7. OKUR DİLİ — figür başlığı ve lejantı, özetin cümle alanları okura olduğu
    gibi basılır.
 8. YAPISAL KİLİT — defterde olmayan bir figür yazılamaz; `if __name__`
    kapısının altında tanım yok.

Koşum:  python3 duman.py
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
import sys

import pandas as pd

BURASI = pathlib.Path(__file__).resolve().parent
KOK = BURASI.parents[1]
sys.path.insert(0, str(BURASI))

import hesap                                                       # noqa: E402
import grafik                                                      # noqa: E402

GECTI, DUSTU = 0, 0
_KUSUR: list[str] = []
_CACHE: dict = {}

GUN_RX = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")
AY_RX = re.compile(r"^\d{2}\.\d{4}$")
# Bir damga TEK tarih ya da iki parçalı olabilir; ölçüt ikisini de çözmeli.
# UZUN yazım alternasyonda ÖNCE gelmek ZORUNDA: "09.09.2026" dizgesinin içinde
# "09.2026" de duruyor ve kısa kalıp önce denenirse GÜNÜ AYA çevirir.
DAMGA_RX = re.compile(r"\d{2}\.\d{2}\.\d{4}|\d{2}\.\d{4}")


def _damga_gunleri(v) -> list:
    """Damga dizgesindeki her tarihi çözer; çözülemeyeni düşürür."""
    if not isinstance(v, str):
        return []
    b = _ortak("bicim")
    return [g for g in (b.tarihe_cevir(p) for p in DAMGA_RX.findall(v)) if g]


def _damga_olcutleri(kok: str, damga, bacak: list[str]) -> list[tuple[str, bool, str]]:
    """Bir damganın taşıması gereken sözleşme — TEK tanım, İKİ çağrı yeri.

    İkinci çağrı yeri (kuralın ilan ettiği sentetik hâller) şart: eski genel
    madde kuralın ürettiği MEŞRU bir çıktıyı kusur sayıyordu ve bu aylarca
    görünmedi, çünkü ölçüt kuralın kendi hâllerine HİÇ koşturulmamıştı.
    """
    import hesap as _h
    b = _ortak("bicim")
    gun_d = sorted(_damga_gunleri(damga))
    gun_b = sorted(g for g in (b.tarihe_cevir(t) for t in bacak) if g)
    olcut = [
        (f"damga_{kok} çözülebilir tarih taşıyor", bool(gun_d), repr(damga)),
        (f"damga_{kok} en eski bacağı gizlemiyor",
         bool(gun_d) and bool(gun_b) and gun_d[0] == gun_b[0],
         f"{damga!r} en eski {gun_d[:1]} ← bacak en eski {gun_b[:1]}"),
    ]
    if gun_b and (gun_b[-1] - gun_b[0]).days > _h.DAMGA_AYRIM_GUN:
        olcut.append((f"damga_{kok}: uzak ayrık bacak adıyla geçiyor",
                      all(t in damga for t in bacak), f"{damga!r} ← {bacak}"))
    return olcut
MDX = KOK / "site" / "src" / "content" / "projeler" / "tufex-basabas.mdx"


def _ortak(ad: str):
    try:
        return __import__(ad)
    except ImportError:
        sys.path.insert(0, str(KOK / "ortak"))
        return __import__(ad)


def sina(ad: str, kosul: bool, ayrinti: str = "") -> None:
    global GECTI, DUSTU
    if kosul:
        GECTI += 1
        print(f"  ✓ {ad}")
    else:
        DUSTU += 1
        _KUSUR.append(ad)
        print(f"  ✗ {ad}" + (f"\n      {ayrinti}" if ayrinti else ""))


def _hesap():
    if "h" not in _CACHE:
        _CACHE["h"] = hesap.hesapla()
    return _CACHE["h"]


def _mdx() -> str:
    return MDX.read_text(encoding="utf-8") if MDX.exists() else ""


# ── 1. sayfa sözleşmesi ──────────────────────────────────────────────────────
def bolum_sozlesme() -> None:
    print("\n▶ Sayfa sözleşmesi")
    d, mevsim, o = _hesap()
    mdx = _mdx()
    sina("proje sayfası bulundu", bool(mdx), str(MDX))
    cagrilan = set(re.findall(r'proje="tufex-basabas"\s+anahtar="([^"]+)"', mdx))
    eksik = sorted(k for k in cagrilan if k not in o)
    sina("sayfanın çağırdığı her anahtar özette var", bool(cagrilan) and not eksik,
         f"eksik: {eksik}")
    sina("katılımcı sayısı özette ve sayfada (elle yazılmıyor)",
         "pka_katilimci" in cagrilan and isinstance(o.get("pka_katilimci"), int),
         f"pka_katilimci={o.get('pka_katilimci')!r}")
    sina("sayfada elle yazılmış katılımcı sayısı yok",
         not re.search(r"\b\d{2,3} katılımcı", mdx))
    gomulu = set(re.findall(r'/projeler/tufex-basabas/([^"\s]+\.html)', mdx))
    sina("gömülü her figür şekil saat defterinde", gomulu <= set(o["_sekil_tarih"]),
         f"{sorted(gomulu - set(o['_sekil_tarih']))}")
    sina("defter, çizim listesi ve figür kaynağı birebir",
         set(o["_sekil_tarih"]) == set(hesap.SEKILLER)
         == set(grafik.figurler(d, mevsim, o)))
    try:
        sys.path.insert(0, str(KOK))
        import guncelle
        kopya = next(h for h in guncelle.HATLAR if h.ad == "tufex").kopya
        sina("kopya sözleşmesindeki her figür defterde",
             set(kopya) == set(hesap.SEKILLER), f"{sorted(set(kopya) ^ set(hesap.SEKILLER))}")
    except Exception as e:                                             # noqa: BLE001
        sina("kopya sözleşmesi okunabildi", False, f"{type(e).__name__}: {e}")
    acik = dict(re.findall(r'src="/projeler/tufex-basabas/([^"]+)"[^>]*tarihAnahtari="([^"]+)"', mdx))
    sina("her figürün sayfada açık damga anahtarı var ve özette çözülüyor",
         set(acik) == set(hesap.SEKILLER)
         and all(isinstance(o.get(a), str) and o[a] for a in acik.values()),
         f"{acik}")


# ── 2–3. saat yazımı ve ana saat ─────────────────────────────────────────────
def bolum_saat() -> None:
    print("\n▶ Saat yazımı")
    _, _, o = _hesap()
    b = _ortak("bicim")
    saatler = {k: v for k, v in o.items() if k.endswith("_tarih") and k != "_sekil_tarih"}
    sina("ana saat GG.AA.YYYY", bool(GUN_RX.match(str(o.get("_tarih")))), repr(o.get("_tarih")))
    gunluk = {k: v for k, v in saatler.items() if k.split("_")[0] in hesap.GUNLUK_BACAKLAR}
    sina("günlük bacaklar GG.AA.YYYY", gunluk and all(GUN_RX.match(str(v)) for v in gunluk.values()),
         str({k: v for k, v in gunluk.items() if not GUN_RX.match(str(v))}))
    aylik = {k: v for k, v in saatler.items()
             if k.split("_")[0] in ("anket", "pka", "mevsim")}
    sina("anket, pka ve mevsim bacakları AA.YYYY (ayın günü yazılmaz)",
         len(aylik) >= 10 and all(AY_RX.match(str(v)) for v in aylik.values()),
         str({k: v for k, v in aylik.items() if not AY_RX.match(str(v))}))
    sina("hiçbir saat anahtarında ay adı ya da ISO yazım yok",
         all(b.tarihe_cevir(v) is not None and not re.search(r"[A-Za-zÇĞİÖŞÜçğıöşü]|-", str(v))
             for v in saatler.values()))
    beklenen = {f"{on}_{v}_tarih" for on in ("anket",) for v in hesap.VADELER
                if f"anket_{v}" in o}
    beklenen |= {"pka_12a_tarih", "pka_24a_tarih", "pka_katilimci_tarih", "mevsim_tarih",
                 "mevsim_ocak_tarih", "mevsim_agustos_tarih", "mevsim_yil_tarih"}
    sina("aylık anahtarların her birinin kendi saati var", beklenen <= set(saatler),
         f"eksik: {sorted(beklenen - set(saatler))}")
    sina("aylık saatler ana saatten ileri değil (ay sonu demiri)",
         all(b.tarihe_cevir(v) <= b.tarihe_cevir(o["_tarih"]) + dt.timedelta(days=31)
             for v in aylik.values()))
    # ana saat: sentetik özet — aylık ileri bacak ve donmuş günlük bacak seçime girmez
    sent = {"basabas_1y_tarih": "01.02.2026", "prim_3y_tarih": "12.06.2025",
            "reel_2y_tarih": "30.01.2026", "anket_1y_tarih": "12.2099",
            "mevsim_tarih": "12.2099", "pka_12a_tarih": "Ağustos 2099"}
    sina("ana saat yalnız günlük bacakların en yenisi",
         hesap.ana_saat(sent) == "01.02.2026", hesap.ana_saat(sent))
    sina("günlük bacak yoksa ana saat boş (uydurulmaz)",
         hesap.ana_saat({"anket_1y_tarih": "08.2026"}) == "")
    sina("metin sırası değil takvim sırası (12.06 > 01.09 tuzağı)",
         hesap.ana_saat({"basabas_3y_tarih": "12.06.2026", "basabas_2y_tarih": "01.09.2026"})
         == "01.09.2026")


# ── 4. anket ayı ─────────────────────────────────────────────────────────────
def bolum_anket() -> None:
    print("\n▶ Anket ayı ve katılımcı")
    d, _, o = _hesap()
    basamak = hesap.anket_basamagi(d)
    sina("günlük seride anket basamağı bulundu", basamak is not None)
    if basamak is None:
        return
    gun, kaynak = hesap.pka_yayim_gunu(d)
    sina("yayım günü kaynak hattın ilanından okundu", kaynak == "kaynak hattın ilanı" and gun is not None,
         f"{gun!r} · {kaynak}")
    # basamak günü: yayım günü ya da onu izleyen ilk iş günü (hafta sonu +2)
    sina("basamak, yayım gününde ya da onu izleyen iş gününde",
         gun is not None and gun <= basamak.day <= gun + 2 and basamak.weekday() < 5,
         f"{basamak:%d.%m.%Y}")
    sina("anket ayı basamağın ayı ve AA.YYYY", o["anket_2y_tarih"] == basamak.strftime("%m.%Y"))
    sina("pka anahtarları anket ayını taşıyor",
         o["pka_12a_tarih"] == o["pka_24a_tarih"] == o["pka_katilimci_tarih"] == o["anket_2y_tarih"])
    sina("geçerlilik başlangıcı basamağın günü", o["pka_gecerli_baslangic"] == f"{basamak:%d.%m.%Y}")
    sina("ay adı etiketi ayrı anahtarda", o["pka_ay_ad"].endswith(str(basamak.year))
         and o["pka_ay_ad"].split()[0] == hesap.AY_AD[basamak.month - 1])
    # Ay eşlemesi aylık kaynakla birebir mi? (yanlış aysa burada düşer)
    try:
        A = pd.read_csv(hesap.DIBS / "aylik.csv", index_col=0, parse_dates=True)
        ay = pd.Timestamp(basamak.year, basamak.month, 1)
        sina("aylık kaynakta anket ayı satırı var", ay in A.index, f"{ay:%Y-%m}")
        if ay in A.index:
            sina("günlük 12a değeri aylık kaynağın aynı ay satırıyla birebir",
                 abs(float(A.loc[ay, "pka_12a"]) - float(o["pka_12a"])) < 1e-6,
                 f"aylık {A.loc[ay, 'pka_12a']} · günlük {o['pka_12a']}")
            sina("katılımcı sayısı aylık kaynağın aynı ay satırıyla birebir",
                 int(A.loc[ay, "pka_12a_n"]) == o["pka_katilimci"],
                 f"aylık {A.loc[ay, 'pka_12a_n']} · özet {o['pka_katilimci']}")
            sonraki = A["pka_12a"].dropna().index.max()
            sina("aylık kaynakta basamaktan ileri bir anket yok ya da henüz yürürlükte değil",
                 sonraki <= ay or sonraki.replace(day=min(gun or 20, sonraki.days_in_month)) > d.index[-1],
                 f"{sonraki:%Y-%m}")
    except FileNotFoundError:
        sina("aylık kaynak dosyası okunabildi", False, str(hesap.DIBS / "aylik.csv"))
    # sentetik: 12a aynı kalır, katılımcı sayısı değişir → basamak yine görülür
    idx = pd.bdate_range("2026-06-01", "2026-08-10")
    sent = pd.DataFrame({"pka_12a": 23.8, "pka_24a": 18.0, "pka_5y": 11.5,
                         "pka_12a_n": [59.0 if t < pd.Timestamp("2026-07-20") else 63.0 for t in idx]},
                        index=idx)
    sina("basamak tek sütuna değil bütün anket sütunlarına bakıyor",
         hesap.anket_basamagi(sent) == pd.Timestamp("2026-07-20"),
         str(hesap.anket_basamagi(sent)))
    sina("anket sütunu yoksa basamak None", hesap.anket_basamagi(pd.DataFrame({"be_2y": [1.0]})) is None)


# ── 5. şekil saat defteri ────────────────────────────────────────────────────
def bolum_defter() -> None:
    print("\n▶ Şekil saat defteri")
    _, _, o = _hesap()
    b = _ortak("bicim")
    defter = o["_sekil_tarih"]
    sinir = b.sonraki_is_gunu(dt.date.today())
    sina("defterdeki her değer ya null ya ÇÖZÜLEBİLİR tek tarih",
         all(v is None or b.tarihe_cevir(v) is not None for v in defter.values()), str(defter))
    sina("birleşik damga deftere GİRMİYOR", all(v is None or " · " not in v for v in defter.values()))
    sina("defterde ertesi iş gününden ileri tarih yok",
         all(v is None or b.tarihe_cevir(v) <= sinir for v in defter.values()))
    sina("mevsim figürü aylık saat taşıyor (günlük saat değil)",
         AY_RX.match(str(defter.get("mevsim.html"))) and defter["mevsim.html"] == o["mevsim_tarih"]
         and defter["mevsim.html"] != o["_tarih"], repr(defter.get("mevsim.html")))
    sina("mevsim saati penceredeki son TÜFE ayı",
         defter["mevsim.html"] == hesap.tufe_aylik().index.max().strftime("%m.%Y"))
    sina("piyasa × anket figürü tek günle anlatılmıyor: defter null, damga iki parçalı",
         defter["basabas_anket.html"] is None and " · " in o["damga_basabas_anket"]
         and o["anket_2y_tarih"] in o["damga_basabas_anket"]
         and o["basabas_2y_tarih"] in o["damga_basabas_anket"], o["damga_basabas_anket"])
    for dosya in hesap.SEKILLER:
        kok = dosya.rsplit(".", 1)[0]
        v = o.get(f"damga_{kok}")
        bacak = [o.get(a) for _, a in hesap.SEKILLER[dosya] if isinstance(o.get(a), str)]
        # BİR DAMGA BAĞLAYICI BACAĞI GİZLEYEMEZ (10.09.2026'da ölçüldü).
        # Burada eskiden "her bacağın tarihi damganın İÇİNDE geçsin" yazıyordu
        # ve madde hattın KENDİ kuralıyla çelişiyordu: bacaklar aynı ritimde ve
        # DAMGA_AYRIM_GUN'den yakınsa kural TEK tarih üretir (en eski bacak),
        # yani daha yeni bacağın tarihi dizgede hiç geçmez. Aşağıdaki sentetik
        # madde tam o davranışı DOĞRU diye iddia ediyor; dosya kendi içinde
        # çelişiyordu ve çelişki yalnız bacaklar 1-7 gün ayrıkken görünüyordu.
        # 10.09'da DİBS eğrisinin 7y düğümü gelmedi, reel bacakları bir gün
        # ayrıştı, madde öttü ve HAT KOMPLE ATLANDI — duman adımlardan önce
        # koşuyor. Yayının önünde duran bir denetimin yanlış alarmı arızanın
        # kendisidir; bir kuralı sınamaya yanlış yazmak onu kalıcı yapar.
        #
        # Ölçülen sözleşme iki parçalı ve kuralın DÖRT hâlinde de geçerli:
        #   (a) damganın EN ESKİ tarihi bacakların en eskisidir — bir damga
        #       bayat bacağı taze gösteremez; ölçünün taşıdığı asıl güvence bu.
        #   (b) bacaklar DAMGA_AYRIM_GUN'den UZAK ayrıksa damga iki parçalıdır
        #       ve her bacak adıyla geçer — eski maddenin DOĞRU olan yarısı.
        for _ad, _kosul, _ayr in _damga_olcutleri(kok, v, bacak):
            sina(_ad, _kosul, _ayr)
        # Özet ile kural AYRIŞMASIN: damga, özetin kendi bacaklarından kuralın
        # ürettiği dizgenin ta kendisi olmalı. Elle tutulan iki liste bir gün
        # sessizce ayrışır.
        sina(f"damga_{kok} kuralın ürettiğiyle aynı",
             v == hesap.sekil_saatleri(o)[dosya],
             f"{v!r} ← {hesap.sekil_saatleri(o)[dosya]!r}")
        if defter[dosya] is not None:
            sina(f"{dosya}: defter ile açık damga aynı günü söylüyor", defter[dosya] == v)
    # sentetik: kuralın dört hâli
    ayni = hesap.sekil_saatleri({"prim_2y_tarih": "08.09.2026", "prim_3y_tarih": "08.09.2026",
                                 "prim_7y_tarih": "08.09.2026"})["prim_tarihce.html"]
    sina("bütün bacaklar aynı günde → tek tarih", ayni == "08.09.2026", repr(ayni))
    yakin = hesap.sekil_saatleri({"prim_2y_tarih": "08.09.2026", "prim_3y_tarih": "05.09.2026",
                                  "prim_7y_tarih": "08.09.2026"})["prim_tarihce.html"]
    sina("aynı ritim, birkaç gün ayrık → EN ESKİ bacak bağlar", yakin == "05.09.2026", repr(yakin))
    uzak = hesap.sekil_saatleri({"prim_2y_tarih": "08.09.2026", "prim_3y_tarih": "12.06.2026",
                                 "prim_7y_tarih": "08.09.2026"})
    dft, dmg = hesap.defter_ayir(uzak)
    sina("donmuş bacak (88 gün) → defter null, damga iki bacağı adıyla taşır",
         dft["prim_tarihce.html"] is None and "3y 12.06.2026" in dmg["damga_prim_tarihce"]
         and "2y ve 7y 08.09.2026" in dmg["damga_prim_tarihce"], dmg["damga_prim_tarihce"])
    karma = hesap.sekil_saatleri({"basabas_2y_tarih": "02.09.2026", "basabas_7y_tarih": "02.09.2026",
                                  "anket_2y_tarih": "08.2026", "anket_7y_tarih": "08.2026"})["basabas_anket.html"]
    sina("farklı cins bacak (aylık × günlük) iki gün ayrıkken bile iki parçalı",
         karma == "anket 08.2026 · piyasa 02.09.2026", repr(karma))

    # ÖLÇÜT, KURALIN KENDİ İLAN ETTİĞİ HÂLLERDEN DE GEÇMELİ (10.09.2026).
    # Eski genel madde tam burada kırılmıştı: "birkaç gün ayrık" hâlini kural
    # DOĞRU üretiyor, madde KUSUR sayıyordu ve iki hüküm aynı dosyada, birkaç
    # satır arayla duruyordu. Çelişki aylarca görünmedi çünkü ölçüt bu hâllere
    # hiç koşturulmamıştı; görünmesi için bacakların 1-7 gün ayrılması gerekti
    # ve o gün (DİBS'in 7y düğümü gelmeyince) hat komple atlandı. Yukarıdaki
    # dört madde kuralın çıktısını, aşağıdaki dört madde AYNI çıktının ölçütten
    # geçtiğini sınıyor — biri kuralı, öbürü ölçütü kilitliyor.
    haller = {
        "hepsi aynı gün": ({"prim_2y_tarih": "08.09.2026", "prim_3y_tarih": "08.09.2026",
                            "prim_7y_tarih": "08.09.2026"}, "prim_tarihce.html"),
        "birkaç gün ayrık": ({"prim_2y_tarih": "08.09.2026", "prim_3y_tarih": "05.09.2026",
                              "prim_7y_tarih": "08.09.2026"}, "prim_tarihce.html"),
        "uzak ayrık": ({"prim_2y_tarih": "08.09.2026", "prim_3y_tarih": "12.06.2026",
                        "prim_7y_tarih": "08.09.2026"}, "prim_tarihce.html"),
        "aylık × günlük": ({"basabas_2y_tarih": "02.09.2026", "basabas_7y_tarih": "02.09.2026",
                            "anket_2y_tarih": "08.2026", "anket_7y_tarih": "08.2026"},
                           "basabas_anket.html"),
    }
    for ad, (girdi, dosya) in haller.items():
        dmg = hesap.sekil_saatleri(girdi)[dosya]
        bac = [girdi[a] for _, a in hesap.SEKILLER[dosya] if a in girdi]
        dusen = [o for o, kosul, _ in _damga_olcutleri("sentetik", dmg, bac) if not kosul]
        sina(f"kuralın '{ad}' hâli ölçütten de geçiyor", not dusen,
             f"{dmg!r} ← {bac} · düşen: {dusen}")
    bos, bos_d = hesap.defter_ayir(hesap.sekil_saatleri({}))
    sina("hiç bacak yoksa defter null, damga boş işaretli (uydurulmaz)",
         all(v is None for v in bos.values()) and all(v == "—" for v in bos_d.values()))
    sina("defter ile damga aynı fonksiyondan ayrılıyor",
         hesap.defter_ayir(hesap.sekil_saatleri(o))[0] == defter)


# ── 6. sınav uyumu ───────────────────────────────────────────────────────────
def bolum_sinav() -> None:
    print("\n▶ Sayfa sınavı uyumu (18 · 18b · 18c)")
    _, _, o = _hesap()
    b = _ortak("bicim")
    try:
        sys.path.insert(0, str(KOK / "site" / "tools"))
        import sayfa_sinavi as ss
    except Exception as e:                                             # noqa: BLE001
        sina("sayfa sınavı içe aktarılabildi", False, f"{type(e).__name__}: {e}")
        return
    sinir = b.sonraki_is_gunu(dt.date.today())
    mdx = _mdx()
    e_, u_, n_ = ss.sekil_saat_bulgulari("tufex-basabas", o, mdx, sinir)
    sina("18: defter engel ve uyarı üretmiyor", not e_ and not u_ and n_ == len(hesap.SEKILLER),
         " | ".join(e_ + u_))
    bulgu = []
    for dosya, anahtar in re.findall(r'src="/projeler/tufex-basabas/([^"]+)"[^>]*tarihAnahtari="([^"]+)"', mdx):
        e2, u2 = ss.acik_saat_bulgulari(dosya, o, anahtar, o["_sekil_tarih"].get(dosya),
                                        dosya in o["_sekil_tarih"], sinir, b.tarihe_cevir)
        bulgu += e2 + u2
    sina("18b/18c: açık damgalar çözülüyor ve defterle çelişmiyor", not bulgu, " | ".join(bulgu[:4]))


# ── 7. okur dili ─────────────────────────────────────────────────────────────
def bolum_okur_dili() -> None:
    print("\n▶ Okur dili")
    d, mevsim, o = _hesap()
    od = _ortak("okur_dili")
    metinler: list[tuple[str, str]] = []
    for ad, fig in grafik.figurler(d, mevsim, o).items():
        if fig.layout.title and fig.layout.title.text:
            metinler.append((f"figür · {ad}", fig.layout.title.text))
        for tr in fig.data:
            if getattr(tr, "name", None):
                metinler.append((f"lejant · {ad}", tr.name))
    for alan, metin in od.ozet_cumleleri(o):
        metinler.append((f"özet · {alan}", metin))
    sina("okur metni torbası dolu", len(metinler) >= 12, str(len(metinler)))
    engel = [f"{n} — {a}: {p}" for n, m in metinler for a, p, _ in od.tara(m)]
    sina("figür ve özet metninde kod ya da yapım dili yok", not engel, " | ".join(engel[:4]))
    kayit = [f"{a}: {p}" for n, m in metinler for _i, a, p in od.kosu_kaydi_tara([m])
             if a in od.KOSU_KAYDI_ENGEL]
    sina("özet cümlelerinde engel sınıfı bulgu yok", not kayit, " | ".join(kayit[:4]))
    sina("anket lejantı yürürlükteki anketin ayını taşıyor",
         any(o["pka_ay_ad"] in m for n, m in metinler if n.startswith("lejant · basabas_anket")))


# ── 8. yapısal kilit ─────────────────────────────────────────────────────────
def bolum_yapi() -> None:
    print("\n▶ Yapısal kilit")
    try:
        grafik.yaz(None, "olmayan.html")
        sina("defterde olmayan figür yazılamıyor", False)
    except KeyError:
        sina("defterde olmayan figür yazılamıyor", True)
    for dosya in ("hesap.py", "grafik.py", "duman.py"):
        kaynak = (BURASI / dosya).read_text(encoding="utf-8")
        # Kapı SATIR BAŞINDA aranır: bu dosyanın kendi gövdesinde de aynı dizge
        # geçiyor (girintili) ve düz metin araması onu kapı sanıp düşüyordu.
        parcalar = re.split(r'^if __name__ == "__main__":', kaynak, maxsplit=1, flags=re.M)
        sina(f"{dosya}: kapının altında tanım yok",
             len(parcalar) == 2 and not re.search(r"^(def|class)\s", parcalar[1], re.M))


def main() -> int:
    print("TÜFEX hattı — duman sınaması (ağa çıkmaz)")
    bolum_sozlesme()
    bolum_saat()
    bolum_anket()
    bolum_defter()
    bolum_sinav()
    bolum_okur_dili()
    bolum_yapi()
    print(f"\n{GECTI} geçti · {DUSTU} düştü")
    if _KUSUR:
        print("Düşenler: " + " | ".join(_KUSUR))
    return 1 if DUSTU else 0


if __name__ == "__main__":
    raise SystemExit(main())
