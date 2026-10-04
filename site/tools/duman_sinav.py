#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sayfa sınavının KENDİ duman sınaması — ağa çıkmaz, saniyeler sürer.

NEDEN VAR. 2026-09-02'de yayın iş akışı arka arkaya altı kez düştü ve site
on iki saat donmuş kaldı; günün bülteni yayına hiç çıkmadı. Depoda hiçbir
dosya değişmemişti — DİBS hattının verisi tazelendi, iki değer bir sayfadaki
UYDURMA aritmetik örneğinin sabitleriyle tesadüfen çakıştı ve 2. ölçüt bunu
ihlal saydı. Yani sınavın hükmü, sınadığı şeyden bağımsız olarak değişti.

Yanlış alarm veren bir denetim, kapatılan bir denetimdir; üstelik bu denetim
yayının önünde durduğu için yanlış alarmı SİTEYİ DURDURUYOR. Bu yüzden
ölçütün hassasiyeti artık sentetik örneklerle sınanıyor: aşağıdaki her madde
bir gün gerçekten yaşanmış ya da yaşanabilecek bir çarpışmadır.

Koşum:  python site/tools/duman_sinav.py    (0 = geçti, 1 = düştü)
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys

_YOL = pathlib.Path(__file__).resolve().with_name("sayfa_sinavi.py")
_spec = importlib.util.spec_from_file_location("sayfa_sinavi", _YOL)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["sayfa_sinavi"] = _mod
_spec.loader.exec_module(_mod)          # main() yalnız __main__ altında koşar

deger_disi = _mod.deger_disi
ciplak_sayilar = _mod.ciplak_sayilar
ORNEK_AC, ORNEK_KAPA = _mod.ORNEK_AC, _mod.ORNEK_KAPA
MUAF_KALIP = _mod.MUAF_KALIP
olu_ic_baglar = _mod.olu_ic_baglar
olu_capalar = _mod.olu_capalar
olay_okura_ulasti = _mod.olay_okura_ulasti
x_izleri = _mod.x_izleri
kacan_etiketler = _mod.kacan_etiketler
sabit_kap_bulgulari = _mod.sabit_kap_bulgulari

GECTI: list[str] = []
DUSTU: list[str] = []


def sina(ad: str, kosul: bool, ayrinti: str = "") -> None:
    (GECTI if kosul else DUSTU).append(ad if kosul else f"{ad} — {ayrinti}")
    print(f"  {'✓' if kosul else '✗'} {ad}" + (f"  ({ayrinti})" if ayrinti and not kosul else ""))


def tara(mdx: str, ozet: dict) -> tuple[list[str], list[str]]:
    return ciplak_sayilar(deger_disi(mdx), ozet, set(MUAF_KALIP.findall(mdx)))


# ---------------------------------------------------------------------------
print("\n▶ Gerçek ihlal yakalanıyor mu (ölçüt zayıflamadı mı)")

e, u = tara("Bugün eğrinin üç aylık noktası 36,79 seviyesinde.", {"spot_3a": 36.79})
sina("çıplak ondalıklı ölçü ENGEL üretiyor", e == ["spot_3a=36,79"], f"gelen {e}")

e, u = tara('Bugün <Deger proje="x" anahtar="spot_3a" ondalik={2}>36,79</Deger> seviyesinde.',
            {"spot_3a": 36.79})
sina("<Deger> içindeki değer yakalanmıyor", not e and not u, f"gelen {e}")

e, u = tara("Yuvarlanmış hâli de sayılır: 36,8.", {"spot_3a": 36.79})
sina("bir ondalığa yuvarlanmış yazım da yakalanıyor", e == ["spot_3a=36,8"], f"gelen {e}")

# ---------------------------------------------------------------------------
print("\n▶ Örnek bloğu (uydurma sayılar taranmaz)")

ORNEK = ("{/* sinav-ornek: uydurma aritmetik */}\n"
         "Fiyatı 51,00 TL olsun; yıllık kupon oranı %36,8'dir.\n"
         "{/* /sinav-ornek */}\n")
e, u = tara(ORNEK, {"spot_3a": 36.79})
sina("örnek bloğunun İÇİ taranmıyor", not e and not u, f"gelen {e}")

e, u = tara(ORNEK + "\nGerçek ölçü ise bugün 36,79.", {"spot_3a": 36.79})
sina("örnek bloğunun DIŞI hâlâ taranıyor (blok sayfayı körleştirmiyor)",
     e == ["spot_3a=36,79"], f"gelen {e}")

sina("kapanmayan blok dengesizlik olarak görünüyor",
     len(ORNEK_AC.findall("{/* sinav-ornek: x */} ...")) == 1
     and len(ORNEK_KAPA.findall("{/* sinav-ornek: x */} ...")) == 0)

# ---------------------------------------------------------------------------
print("\n▶ Ön bilgideki düzeltme kaydı (tarihli kayıt, düzyazı değil)")

DUZ = ("---\ntitle: 'Pano'\nduzeltmeler:\n  - tarih: '2026-09-30'\n"
       "    alan: 'Eylül vadesi'\n    eski: '4,48 yıl'\n    yeni: '4,49 yıl'\n"
       "    sebep: 'Gün sayımı tek cetvele çekildi.'\ndurum: 'aktif'\n---\n\nGövde.\n")
e, u = tara(DUZ, {"wam_son": 4.49})
sina("düzeltme kaydının 'yeni' değeri canlı değere eşit olsa da taranmıyor",
     not e and not u, f"gelen engel={e} uyari={u}")
e, u = tara(DUZ.replace("Gövde.", "Gövde bugün 4,49 diyor."), {"wam_son": 4.49})
sina("düzeltme bloğu gövdeyi körleştirmiyor", e == ["wam_son=4,49"], f"gelen {e}")
e, u = tara(DUZ.replace("durum: 'aktif'", "description: 'Son ay 4,49 yıl'\ndurum: 'aktif'"), {"wam_son": 4.49})
sina("ön bilginin geri kalanı taranmaya devam ediyor", e == ["wam_son=4,49"], f"gelen {e}")

# ---------------------------------------------------------------------------
print("\n▶ Tam sayı ile ondalıklı ölçü ayrımı")

# 2026-09-02'yi düşüren tam çarpışma: sayım 51, metinde fiyat varsayımı 51,00 TL
e, u = tara("Fiyatı 51,00 TL olsun.", {"kimlik_cok_kaynakli": 51})
sina("tam sayı, ondalıklı yazımla ARANMIYOR (12 saatlik durmanın sebebi)",
     not e and not u, f"gelen engel={e} uyari={u}")

e, u = tara("Pencere 250 iş günü.", {"kimlik_api_n": 250})
sina("tam sayı kendi yazımıyla bulunursa UYARI, ENGEL değil",
     not e and u == ["kimlik_api_n=250"], f"gelen engel={e} uyari={u}")

e, u = tara("Kimlik 51 kaynakta sınandı.", {"kimlik_cok_kaynakli": 51})
sina("iki haneli sayım taranmıyor (çok yaygın)", not e and not u, f"gelen {e} {u}")

# ---------------------------------------------------------------------------
print("\n▶ İşaret")

e, u = tara("Haziran 2023 (−22,1).", {"d3a": 22.1})
sina("metindeki eksili sayı, POZİTİF değerle eşleşmiyor", not e, f"gelen {e}")

e, u = tara("Haziran 2023 (-22,1).", {"d3a": 22.1})
sina("ASCII eksi de aynı korumayı alıyor", not e, f"gelen {e}")

e, u = tara("Taşıma bugün −22,1 seviyesinde.", {"d3a": -22.1})
sina("gerçekten negatif değer, eksili yazımla yakalanıyor",
     e == ["d3a=−22,1"], f"gelen {e}")

# ---------------------------------------------------------------------------
print("\n▶ Kod ve formül taranmaz")

e, u = tara("`spot_3a = 36,79` satırı bir kod parçasıdır.", {"spot_3a": 36.79})
sina("satır içi kod taranmıyor", not e, f"gelen {e}")

e, u = tara("$y = 36{,}79$ formülü.", {"spot_3a": 36.79})
sina("KaTeX taranmıyor", not e, f"gelen {e}")

# ---------------------------------------------------------------------------
print("\n▶ Şekil saat defteri")

import datetime as _dt
# SINIR "yarın" DEĞİL, ERTESİ İŞ GÜNÜ — tanım ortak/bicim.sonraki_is_gunu'da,
# gerekçe orada. Buradaki sınamalar o sınırla koşar; adı da onu söylesin.
import sys as _s0, pathlib as _p0
_s0.path.insert(0, str(_p0.Path(__file__).resolve().parents[2] / "ortak"))
import bicim as _bcm0
YARIN = _bcm0.sonraki_is_gunu(_dt.date.today())
sekil_saat_bulgulari = _mod.sekil_saat_bulgulari
MDX2 = ('<GrafikEmbed src="/projeler/x/a.html" />\n'
        '<GrafikEmbed src="/projeler/x/b.html" />\n')

e, u, n = sekil_saat_bulgulari(
    "x", {"_sekil_tarih": {"a.html": "2026-08-30", "b.html": "2026-09-03"}}, MDX2, YARIN)
sina("eksiksiz defter temiz geçiyor", not e and not u, f"engel={e} uyari={u}")
sina("gömülü figür sayısı doğru", n == 2, f"gelen {n}")

e, u, n = sekil_saat_bulgulari("x", {"_sekil_tarih": {"a.html": "2026-08-30"}}, MDX2, YARIN)
sina("defterde girdisi olmayan figür UYARI, ENGEL değil",
     not e and len(u) == 1 and "b.html" in u[0], f"engel={e} uyari={u}")

ileri = (YARIN + _dt.timedelta(days=3)).isoformat()
e, u, n = sekil_saat_bulgulari(
    "x", {"_sekil_tarih": {"a.html": ileri, "b.html": "2026-09-03"}}, MDX2, YARIN)
sina("ertesi iş gününden ileri şekil saati ENGEL",
     len(e) == 1 and "İLERİ" in e[0], f"engel={e}")

e, u, n = sekil_saat_bulgulari(
    "x", {"_sekil_tarih": {"a.html": None, "b.html": "2026-09-03"}}, MDX2, YARIN)
sina("None = 'ucu ölçülmedi' — engel değil, uyarı da değil",
     not e and not u, f"engel={e} uyari={u}")

e, u, n = sekil_saat_bulgulari(
    "x", {"_sekil_tarih": {"a.html": "dün", "b.html": "2026-09-03"}}, MDX2, YARIN)
sina("çözülemeyen tarih ENGEL", len(e) == 1 and "çözülemeyen" in e[0], f"engel={e}")

# ---------------------------------------------------------------------------
# (18b/18c) AÇIK ŞEKİL TARİHİ. Bu ölçüt yayının ÖNÜNDE duruyor: yanlış alarmı
# siteyi durdurur. Sınamanın çekirdeği BİRLEŞİK DAMGA — ödemeler dengesi
# Şekil 12'nin üç paneli 57 gün arayla bitiyor ve tek bir uç hangi bacağı
# seçse öbürü hakkında yalan olur; damga bu yüzden ikisini birden yazar ve
# ölçüt bunu kusur saymamalı. Ama içindeki her tarih yine sınanmalı.
print("\n▶ Açık şekil tarihi (18b) ve çift ilan çelişkisi (18c)")

import sys as _s2
_s2.path.insert(0, str(_YOL.resolve().parents[2] / "ortak"))
import bicim as _bcm

acik_saat_bulgulari = _mod.acik_saat_bulgulari
COZ = _bcm.tarihe_cevir


def acik(deger, defter=None, defter_var=False, anahtar="k"):
    o = {anahtar: deger} if deger is not None else {}
    return acik_saat_bulgulari("s · f.html → `k`", o, anahtar, defter,
                               defter_var, YARIN, COZ)


e, u = acik("26.08.2026")
sina("tek tarih temiz geçiyor", not e and not u, f"engel={e} uyari={u}")

e, u = acik("07.2026")
sina("AA.YYYY yazımı da tarihtir", not e and not u, f"engel={e} uyari={u}")

e, u = acik("aylık 30.06.2026 · haftalık 26.08.2026")
sina("BİRLEŞİK DAMGA kusur değil (yanlış alarm yok)",
     not e and not u, f"engel={e} uyari={u}")

ileri2 = (YARIN + _dt.timedelta(days=3)).strftime("%d.%m.%Y")
e, u = acik(f"aylık 30.06.2026 · haftalık {ileri2}")
sina("birleşik damganın İÇİNDEKİ ileri tarih ENGEL",
     len(e) == 1 and "İLERİ" in e[0], f"engel={e}")

e, u = acik(None)
sina("anahtar yok → UYARI (sayfa bir alt basamağa düşer)",
     not e and len(u) == 1, f"engel={e} uyari={u}")

e, u = acik(2026)
sina("dizge olmayan değer → UYARI", not e and len(u) == 1, f"engel={e} uyari={u}")

e, u = acik("son ihale günü")
sina("içinde hiç tarih olmayan dizge → UYARI",
     not e and len(u) == 1 and "tarih değil" in u[0], f"engel={e} uyari={u}")

e, u = acik("26.08.2026", defter="26.08.2026", defter_var=True)
sina("çift ilan AYNI günü söylüyorsa temiz", not e and not u, f"engel={e} uyari={u}")

e, u = acik("26.08.2026", defter="21.08.2026", defter_var=True)
sina("çift ilan AYRIŞIYORSA ENGEL",
     len(e) == 1 and "ÇELİŞKİ" in e[0], f"engel={e}")

e, u = acik("26.08.2026", defter=None, defter_var=True)
sina("defterde None + açık anahtar var → çelişki değil",
     not e and not u, f"engel={e} uyari={u}")

e, u = acik("26.08.2026", defter="2026-08-26", defter_var=True)
sina("aynı gün farklı YAZIMLA yazılmışsa çelişki değil",
     not e and not u, f"engel={e} uyari={u}")


# ---------------------------------------------------------------------------
# (19) ŞEKİL METNİNDE OKUR DİLİ. Bu ölçüt yayının önünde duruyor ve ağırlıkları
# BUGÜNKÜ tabana göre seçildi: yapım dili ENGEL (taban sıfır), kod dili UYARI
# (taban yetmiş altı). Ağırlıklar ters çevrilirse site durur; sınama bunu tutar.
print("\n▶ Şekil metninde okur dili (19)")

sekil_metinleri = _mod.sekil_metinleri
sekil_okur_dili = _mod.sekil_okur_dili

HAM = ('var gd = document.getElementById("x");'
       'Plotly.newPlot("x",[{"x":["2026-08-21"],"y":[1.5],'
       '"name":"Kredi b\\u00fcy\\u00fcmesi (bie_hpbitablo2)","type":"scatter",'
       '"hovertemplate":"%{x}\\u003cbr\\u003eR\\u00b2 %{y}"}],'
       '{"title":{"text":"\\u003cb\\u003eBa\\u015fl\\u0131k\\u003c\\u002fb\\u003e'
       '\\u003cbr\\u003e\\u003csup\\u003eBu halka yaz\\u0131n\\u0131n ilk '
       's\\u00fcr\\u00fcm\\u00fcnde \\u00d6L\\u00c7\\u00dcLMEM\\u0130\\u015eTI.'
       '\\u003c\\u002fsup\\u003e"}})')

metinler = sekil_metinleri(HAM)
sina("başlık, lejant ve hover metni çıkarılıyor", len(metinler) >= 2,
     f"gelen {metinler}")
sina("HTML etiketleri düz metne iniyor",
     not any("<b>" in t or "<sup>" in t for t in metinler), f"{metinler}")
sina("birim kod kaçışları çözülüyor",
     any("büyümesi" in t for t in metinler), f"{metinler}")

e, u, say = sekil_okur_dili(metinler, "x/y.html")
sina("figür metnindeki YAPIM DİLİ ENGEL",
     len(e) == 1 and "yapım dili" in e[0], f"engel={e}")
sina("figür metnindeki bie_ kodu UYARI, ENGEL değil",
     len(u) == 1 and "bie_hpbitablo2" in u[0], f"uyari={u}")

e, u, say = sekil_okur_dili(
    ["Veri: TCMB EVDS3 · TP.PY.P06.ON · iş günü · Çıpa: 2 Eylül 2026."], "x/y.html")
sina("kaynağın BÜYÜK harfli alan adı kusur değil (künyedir)",
     not e and not u, f"engel={e} uyari={u}")

e, u, say = sekil_okur_dili(["Eksen etiketi 0.53 ve -1.20 değerleri"], "x/y.html")
sina("biçim ailesi yalnız SAYILIR, uyarı üretmez",
     not e and not u and say.get("biçim", 0) > 0, f"engel={e} uyari={u} say={say}")

e, u, say = sekil_okur_dili(["Kredi büyümesi kur etkisinden arındırılmıştır."],
                            "x/y.html")
sina("temiz alt yazı temiz geçiyor", not e and not u, f"engel={e} uyari={u}")

e2, u2, _ = sekil_okur_dili(metinler + metinler, "x/y.html")
sina("aynı kusur iki kez geçse tek kez bildiriliyor",
     len(e2) == 1 and len(u2) == 1, f"engel={e2} uyari={u2}")

# KAPSAM SÖZLEŞMEDEN. 03.09'dan 22.09.2026'ya ölçüt yalnız `projeler/` tarıyordu;
# indikatör (30), ders (246), teknik (16) ve analiz (5) figürleri görüş alanının
# dışındaydı ve bakılmayan yer geçen sınavla aynı görünüyordu. Beklenti elle
# yazılmaz, AĞAÇTAN bağımsız olarak yeniden türetilir: Plotly taşıyan HTML'i
# olan her üst dizin taramada olmalı. Kök burada SÖZLEŞMEDEN yazılır
# (`site/public` — okurun gördüğü her dosya Astro'nun bu dizininden sunulur),
# sınanan modülün SEKIL_KOK'undan OKUNMAZ: ilk yazımda okunuyordu ve kapsam
# `projeler/`e daraltılınca beklenti de daralıp madde YEŞİL geçti — bir
# regresyon sınamasının beklentisi sınadığı değişkeni paylaşamaz.
_pub = _mod.KOK / "site/public"
_taranan = {hp.relative_to(_pub).parts[0] for hp, _ in _mod.sekil_dosyalari()}
_plotly_olan = {p.relative_to(_pub).parts[0] for p in _pub.rglob("*.html")
                if "Plotly" in p.read_text(encoding="utf-8", errors="ignore")}
sina("figür taraması Plotly taşıyan her üst dizini kapsıyor (kapsam ağaçtan türer)",
     _plotly_olan == _taranan and len(_taranan) >= 2,
     f"taranan={sorted(_taranan)} plotly_olan={sorted(_plotly_olan)}")

sina("veri dizileri metin sayılmıyor",
     not any(t.startswith("2026-08-21") for t in metinler), f"{metinler}")


# ---------------------------------------------------------------------------
# ERTESİ İŞ GÜNÜ SINIRI. Bu, yayının önünde duran bir sınırdır ve 04.09.2026'da
# yanlış alarmı siteyi YİRMİ BİR SAAT durdurdu: TCMB cuma günü PAZARTESİ'nin
# gösterge kurunu yayımlıyor, hat bunu bilerek çekiyor, ölçüt "yarından ileri"
# diyip yayın iş akışını arka arkaya dört kez düşürdü. Sınır artık takvimi
# değil YAYIM SÖZLEŞMESİNİ izliyor; sınama onu her gün için kilitliyor.
print("\n▶ Ertesi iş günü sınırı (ortak/bicim.sonraki_is_gunu)")

_sig = _bcm0.sonraki_is_gunu
sina("perşembe → cuma (hafta içi +1)",
     _sig(_dt.date(2026, 9, 3)) == _dt.date(2026, 9, 4), str(_sig(_dt.date(2026, 9, 3))))
sina("CUMA → PAZARTESİ (+3, arızanın kendisi)",
     _sig(_dt.date(2026, 9, 4)) == _dt.date(2026, 9, 7), str(_sig(_dt.date(2026, 9, 4))))
sina("cumartesi → pazartesi", _sig(_dt.date(2026, 9, 5)) == _dt.date(2026, 9, 7),
     str(_sig(_dt.date(2026, 9, 5))))
sina("pazar → pazartesi", _sig(_dt.date(2026, 9, 6)) == _dt.date(2026, 9, 7),
     str(_sig(_dt.date(2026, 9, 6))))
sina("pazartesi → salı", _sig(_dt.date(2026, 9, 7)) == _dt.date(2026, 9, 8),
     str(_sig(_dt.date(2026, 9, 7))))
sina("sınır GEVŞEMEDİ — en çok +3 gün",
     all((_sig(_dt.date(2026, 9, g)) - _dt.date(2026, 9, g)).days <= 3 for g in range(1, 29)),
     "bir gün +3'ten fazla ileri")

# 04.09'un GERÇEK vakası: cuma çekilen seri pazartesiyle bitiyor.
_cuma, _pzt = _dt.date(2026, 9, 4), _dt.date(2026, 9, 7)
sina("04.09 vakası: pazartesi damgası cuma günü ENGEL DEĞİL", _pzt <= _sig(_cuma),
     "yanlış alarm geri geldi")
sina("iki hafta ileri tarih HÂLÂ engel", _dt.date(2026, 9, 18) > _sig(_cuma),
     "sınır fazla gevşedi")

# Girdi DUVAR SAATİNDEN türetilir, sabit yazılmaz. İlk yazımda "18.09.2026"
# donmuştu ve ölçüt YARIN'a bakıyordu: 04.09'da iki hafta ileriydi, 17.09.2026
# sabahı YARIN oldu, madde düştü ve yayın kapısının İLK adımı siteyi durdurdu.
# Fikstürün girdisi canlıysa beklentisi de canlı olmalı (bkz. YPMevduat, 10.09).
_iki_hafta = (YARIN + _dt.timedelta(days=14)).strftime("%d.%m.%Y")
e, u = acik(_iki_hafta)
sina("açık anahtarda iki hafta ileri tarih ENGEL",
     len(e) == 1 and "İLERİ" in e[0], f"engel={e}")


# ---------------------------------------------------------------------------
print("\n▶ Ölü iç bağ (20. ölçüt)")

import tempfile  # noqa: E402


def _agac(dosyalar: dict[str, str]) -> pathlib.Path:
    """Sentetik bir dist/ ağacı kur ve kökünü döndür."""
    kok = pathlib.Path(tempfile.mkdtemp())
    for yol, icerik in dosyalar.items():
        d = kok / yol
        d.parent.mkdir(parents=True, exist_ok=True)
        d.write_text(icerik, encoding="utf-8")
    return kok


# ÖLÇÜLEN ARIZA: bültenin kaynak notu panosu OLMAYAN bir hattı
# /projeler/<slug>/ diye bağlıyordu. Sayfa silindi, bağ kaldı, koşu yeşil bitti.
kok = _agac({
    "bulten/index.html": '<a href="/projeler/ovp/">Orta Vadeli Program</a>',
    "projeler/ovp/ozet.json": "{}",          # varlıklar duruyor, SAYFA yok
})
k = olu_ic_baglar(kok)
sina("panosu silinmiş hatta bağ ENGEL üretiyor", list(k) == ["/projeler/ovp/"], f"gelen {list(k)}")

# Aynı ağaca sayfa konunca susmalı — yoksa ölçüt her yayını durdurur.
(kok / "projeler/ovp/index.html").write_text("<p>pano</p>", encoding="utf-8")
sina("sayfa varsa bağ geçerli", olu_ic_baglar(kok) == {}, f"gelen {list(olu_ic_baglar(kok))}")

# YANLIŞ ALARM OLMASIN: varlık bağı (uzantılı dosya), çapa, sorgu ve dış adres.
kok = _agac({
    "s/index.html": ('<a href="/projeler/x/ozet.json">özet</a>'
                     '<a href="/bulten/#kosu">koşu</a>'
                     '<a href="/arama/?q=kur">arama</a>'
                     '<a href="https://example.com/yok">dış</a>'
                     '<a href="#bolum">çapa</a>'),
    "projeler/x/ozet.json": "{}",
    "bulten/index.html": "<p>b</p>",
    "arama/index.html": "<p>a</p>",
})
sina("varlık · çapa · sorgu · dış adres yanlış alarm üretmiyor",
     olu_ic_baglar(kok) == {}, f"gelen {list(olu_ic_baglar(kok))}")

# Gerçekten kırık bir varlık bağı da yakalanmalı.
kok = _agac({"s/index.html": '<a href="/og/yok.png">kart</a>'})
sina("hedefsiz varlık bağı da yakalanıyor",
     list(olu_ic_baglar(kok)) == ["/og/yok.png"], f"gelen {list(olu_ic_baglar(kok))}")

# (20b) SAYFA İÇİ ÇAPA. Karne söz defterine çapayla bağlar; kayıt basılmazsa
# bağ boşa düşer. Hedef varsa, kodlanmış Türkçe kimlik ve çıplak "#" sessiz.
kok = _agac({
    "b/index.html": ('<a href="#soz-a">a</a><a href="#soz-yok">yok</a><a href="#">üst</a>'
                     '<a href="#%C3%B6zet">özet</a><a href="#y-risk">risk</a>'
                     '<li id="soz-a"></li><section id="özet"></section>'
                     '<section data-x id="y-risk"></section>'),
    "c/index.html": '<a href="#n">n</a><a name="n"></a>',
})
c = olu_capalar(kok)
sina("hedefsiz sayfa içi çapa yakalanıyor (yalnız o)",
     c == {"b/index.html": ["soz-yok"]}, f"gelen {c}")
(kok / "b/index.html").write_text('<a href="#soz-yok">x</a><p id="soz-yok"></p>', encoding="utf-8")
sina("hedef konunca çapa sessiz", olu_capalar(kok) == {}, f"gelen {olu_capalar(kok)}")


# ---------------------------------------------------------------------------
print("\n▶ X izi (21. ölçüt)")

# ÖLÇÜLEN ARIZA: bülten/teknik/analiz künyesinde "Paylaşım · X gönderisi ↗"
# satırı vardı ve bağı BİLEŞEN kuruyordu (lib/x.ts + defter aynası).
kok = _agac({
    "bulten/2026-09-06/index.html":
        '<span class="kunye"><b>Paylaşım</b> <a href="https://x.com/i/status/123">X gönderisi ↗</a></span>',
})
i = x_izleri(kok)
sina("künye bağı ve yazısı ENGEL üretiyor",
     any("x.com" in k for k in i) and any("X gönderi" in k for k in i), f"gelen {sorted(i)}")

# twitter:card künyesi KUSUR DEĞİL: hesap adı taşımaz, adres de yok.
kok = _agac({
    "s/index.html": ('<meta name="twitter:card" content="summary_large_image">'
                     '<meta name="twitter:title" content="TTO Trading">'
                     '<meta name="twitter:image" content="/og/genel.png">'),
})
sina("twitter:card meta'sı yanlış alarm üretmiyor", x_izleri(kok) == {}, f"gelen {sorted(x_izleri(kok))}")

# Türkçe "paylaşım" sözcüğü iktisadi anlamıyla geçiyor (turkiye-piyasa-tarihi).
kok = _agac({"s/index.html": "<p>Gelir paylaşımı sözleşmeleri ve risk paylaşımı.</p>"})
sina("Türkçe 'paylaşım' sözcüğü taranmıyor", x_izleri(kok) == {}, f"gelen {sorted(x_izleri(kok))}")

# Hakkında sayfasının cümlesi de yakalanmalı — bağ olmadan da bir iz.
kok = _agac({"hakkinda/index.html":
             "<p>Analiz yazıları yayın günü X'te de özetiyle paylaşılır.</p>"})
sina("bağsız cümle de yakalanıyor", len(x_izleri(kok)) == 1, f"gelen {sorted(x_izleri(kok))}")

# RSS beslemesi de taranır: bağ oraya da düşebilir.
kok = _agac({"bulten/rss.xml": '<link>https://twitter.com/hesap/status/9</link>'})
sina("rss.xml de taranıyor", len(x_izleri(kok)) == 1, f"gelen {sorted(x_izleri(kok))}")

# Temiz ağaç sessiz kalmalı — yanlış alarm yayını durdurur.
kok = _agac({"s/index.html": "<p>Bülten, teknik analiz ve analiz yazıları RSS ile izlenir.</p>"})
sina("temiz sayfa temiz geçiyor", x_izleri(kok) == {}, f"gelen {sorted(x_izleri(kok))}")

# ÖLÇÜLEN ARIZA (22.09.2026): taranan haber listesi DIŞ KAYNAĞIN metnidir ve
# orada geçen "X hesabı" ÜÇÜNCÜ BİR TARAFIN hesabıdır. Bir parti başkanlığının
# X hesabından paylaşım yaptığını söyleyen bir haber özeti yayını DURDURDU —
# bülten yazılmıştı, site dondu. Kararın koruduğu şey KENDİ hesabımız.
kok = _agac({"bulten/2026-09-22/index.html":
             '<div class="gundem-metin"><p>Petrol geriledi.</p></div>'
             '<ul class="haber-liste" data-astro-cid-vzeo3fk4><li><a href="https://ornek.com/a" data-astro-cid-vzeo3fk4>SPK duyurusu</a>'
             '<span class="h-ozet" data-astro-cid-vzeo3fk4>Bakanlığın X hesabından SPK\'ya yönelik bir '
             'paylaşım yapıldı.</span></li></ul>'})
sina("haber listesindeki üçüncü taraf X hesabı yanlış alarm üretmiyor",
     x_izleri(kok) == {}, f"gelen {sorted(x_izleri(kok))}")

# AMA MUAFİYET YALNIZ YAZI AİLESİNE: haber listesindeki bir x.com ADRESİ hâlâ
# kusurdur — orası okura tıklanacak bir bağ verir.
kok = _agac({"bulten/2026-09-22/index.html":
             '<ul class="haber-liste" data-astro-cid-vzeo3fk4><li><a href="https://x.com/biri/status/5">Haber</a>'
             '</li></ul>'})
sina("haber listesindeki x.com adresi hâlâ ENGEL",
     any("x.com" in k for k in x_izleri(kok)), f"gelen {sorted(x_izleri(kok))}")

# VE MUAFİYET KENDİ CÜMLEMİZİ KAPSAMAZ: aynı sayfada, liste DIŞINDA geçen bir
# öz-atıf yakalanmaya devam etmeli — yoksa daraltma kuralı boşaltır.
kok = _agac({"bulten/2026-09-22/index.html":
             '<div class="gundem-metin"><p>Bu yazı X\'te de özetiyle paylaşılır.</p></div>'
             '<ul class="haber-liste" data-astro-cid-vzeo3fk4><li><span class="h-ozet">Bakanlığın X hesabından.'
             '</span></li></ul>'})
sina("liste dışındaki öz-atıf muafiyete rağmen yakalanıyor",
     len(x_izleri(kok)) == 1, f"gelen {sorted(x_izleri(kok))}")

# HASSASİYET, KAPSAM KADAR ÖLÇÜTÜN PARÇASI. Kalıp genişletildi (hesap anışı,
# Twitter yazımı, X'ten/X'te paylaşım) ve sol harf sınırı ile lokatif şartı
# ölçülerek kondu: sitede "VIX'te", "TÜFEX'te", "FX'te", "MDX'te" ve bir
# istatistik yazısında "Y'den X'e çıkarım" geçiyor. Sonuncusu bugün yalnız
# MDX'in kıvrık kesme işareti sayesinde kurtuluyordu — yani TESADÜFEN.
for _metin, _bekle in [
    ("bu notu X'te paylaştık", True),
    ("X'de paylaşıldı", True),
    ("X'ten paylaşıldı", True),
    ("X hesabımızda duyurduk", True),
    ("Twitter hesabımız", True),
    ("Twitter'da paylaştık", True),
    ("Twitter’da paylaştık", True),
    ("yayın günü X'te de özetiyle çıkar", True),
    ("Y'den X'e çıkarım az bilgi taşır", False),
    ("Y’den X’e çıkarım az bilgi taşır", False),
    ("oynaklık VIX'te de ortaya çıkar", False),
    ("TÜFEX'te yayımlanan kupon", False),
    ("spot FX'te güvenilir değildir", False),
    ("MDX'te oynak sayılar", False),
    ("VIX'ten paylaşılan seri", False),
    ("PRZ kutusu X'te başlar", False),
    ("D noktası X'ten uzaktır", False),
]:
    _k = _agac({"s/index.html": f"<p>{_metin}</p>"})
    _v = bool(x_izleri(_k))
    sina(f"{'yakalanıyor' if _bekle else 'yanlış alarm yok'}: {_metin[:34]}",
         _v == _bekle, f"gelen {_v}")


# ---------------------------------------------------------------------------
print("\n▶ Kaçan etiket (22. ölçüt)")

# ÖLÇÜLEN ARIZA: yazı katmanının bütün metin alanları HTML taşıyor; `yorum` ve
# `gundem.*` set:html ile basılıyordu, `ozet` ise METİN olarak. Dört bülten
# sayısında okur cümlenin başında "<p>" yazısını gördü (yirmi kaçış).
kok = _agac({"bulten/2026-09-06/index.html":
             "<p>&lt;p&gt;Geçen hafta üç şey oldu.&lt;/p&gt;</p>"})
sina("metin olarak basılan yazı alanı ENGEL üretiyor",
     sorted(kacan_etiketler(kok)) == ["&lt;/p&gt;", "&lt;p&gt;"], f"gelen {sorted(kacan_etiketler(kok))}")

kok = _agac({"bulten/2026-09-06/index.html":
             "<div class='ozet-metin'><p>Geçen hafta üç şey oldu.</p></div>"})
sina("set:html ile basılan alan sessiz", kacan_etiketler(kok) == {}, f"gelen {sorted(kacan_etiketler(kok))}")

# KOD BLOĞU MUAF: HTML anlatan bir ders etiketi GÖSTERMEK zorunda; muafiyet
# olmasaydı ölçüt bir gün yayını böyle bir yazı yüzünden durdururdu.
kok = _agac({"arastirma/html-dersi/index.html":
             "<p>Paragraf şöyle yazılır:</p><pre><code>&lt;p&gt;metin&lt;/p&gt;</code></pre>"})
sina("kod bloğu içindeki etiket muaf", kacan_etiketler(kok) == {}, f"gelen {sorted(kacan_etiketler(kok))}")

# Matematikteki karşılaştırma işaretleri etiket değildir.
kok = _agac({"s/index.html": "<p>a &lt; b ve c &gt; d; 5 &lt; 10 olduğundan.</p>"})
sina("küçüktür/büyüktür işareti yanlış alarm üretmiyor",
     kacan_etiketler(kok) == {}, f"gelen {sorted(kacan_etiketler(kok))}")


# ---------------------------------------------------------------------------

# ÖLÇÜLEN KARAR (08.09.2026): yalnız panolar canlı; analiz ve ders gövdesi
# `data-deger="sabit"` kabında, Deger betiği dokunmaz. Kap bileşende kurulur;
# bir düzen değişikliği onu sessizce düşürürse analizler yeniden canlanır ve
# okur bunu göremez — ölçüt ÇIKTIYA bakar.
kok = _agac({
    "analiz/tufe-2026-09-03/index.html": '<div class="prose"><span class="canli-deger" data-proje="x">1,2</span></div>',
    "arastirma/ders-a/index.html": '<div class="prose"><span class="canli-deger">3</span></div>',
    "projeler/enflasyon/index.html": '<div class="prose"><span class="canli-deger">4</span></div>',
})
b = sabit_kap_bulgulari(kok)
sina("analiz sayfasında kapsız canlı alan ENGEL", any(x.startswith("analiz/tufe-2026-09-03") for x in b), str(b))
sina("ders sayfasında kapsız canlı alan ENGEL", any(x.startswith("arastirma/ders-a") for x in b), str(b))
sina("proje sayfasında kap yokken bulgu yok", not any(x.startswith("projeler/") for x in b), str(b))
kok = _agac({
    "analiz/tufe-2026-09-03/index.html": '<div class="prose" data-deger="sabit"><span class="canli-deger">1,2</span></div>',
    "analiz/index.html": '<a href="/analiz/tufe-2026-09-03/">kart</a>',
    "projeler/enflasyon/index.html": '<div class="prose" data-deger="sabit"><span class="canli-deger">4</span></div>',
    "bulten/2026-09-08/index.html": '<p>canlı-deger sözcüğü geçmiyor</p>',
})
b = sabit_kap_bulgulari(kok)
sina("kaplı analiz temiz", not any(x.startswith("analiz/tufe") for x in b), str(b))
sina("analiz liste sayfası (canlı alan yok) taranmaz", not any(x.startswith("analiz/index") for x in b), str(b))
sina("SABİT KAPLI proje sayfası ENGEL — pano canlı kalmalı", any(x.startswith("projeler/enflasyon") for x in b), str(b))


# ---------------------------------------------------------------- iş günü sınırı
# Yayın kapısının "ileri tarih" ölçütü (12 · 18b) bu sınırı kullanıyor ve yanlış
# alarmı SİTEYİ DURDURUR; o yüzden sınırın kendisi de sınanır. Tatil bilmeyen
# bir sınır 31.12.2026'da yayını durduracaktı: TCMB o gün 04.01.2027 valörünü
# ilan eder, hafta sonu bilen ama tatil bilmeyen sınır 01.01.2027 der ve
# yayımlanan DOĞRU tarihi "ileri" sayar.
print("\n▶ Ertesi iş günü sınırı (ortak/bicim.sonraki_is_gunu)")
import datetime as _dtg
import sys as _sg, pathlib as _pg
_sg.path.insert(0, str(_pg.Path(__file__).resolve().parents[2] / "ortak"))
import bicim as _bg

for _g, _bek, _ad in (
    ((2026, 12, 31), (2027, 1, 4), "yılbaşı: 31.12 perşembe -> 04.01 pazartesi"),
    ((2026, 10, 28), (2026, 10, 30), "29 Ekim: 28.10 çarşamba -> 30.10 cuma"),
    ((2026, 4, 22), (2026, 4, 24), "23 Nisan atlanıyor"),
    ((2026, 9, 4), (2026, 9, 7), "cuma -> pazartesi (hafta sonu kuralı duruyor)"),
    ((2026, 9, 9), (2026, 9, 10), "sıradan gün -> ertesi gün (sınır GEVŞEMEDİ)"),
):
    sina(f"iş günü sınırı — {_ad}",
         _bg.sonraki_is_gunu(_dtg.date(*_g)) == _dtg.date(*_bek),
         f"gelen {_bg.sonraki_is_gunu(_dtg.date(*_g))}")

# Hareketli bayramlar GİRİLMEDİKÇE davranış değişmez: uydurma bir tarih,
# olmayan bir tatilde sınırı gevşetir ve gerçek bir ileri tarihi kaçırır.
sina("girilmemiş hareketli bayram yılında davranış hafta sonu kuralıyla aynı",
     _bg.sonraki_is_gunu(_dtg.date(2027, 5, 14)) == _dtg.date(2027, 5, 17),
     f"gelen {_bg.sonraki_is_gunu(_dtg.date(2027, 5, 14))}")
_bg.HAREKETLI_TATIL[2099] = ("2099-03-02",)
sina("hareketli tatil tablosu girildiğinde etkili",
     _bg.sonraki_is_gunu(_dtg.date(2099, 3, 1)) == _dtg.date(2099, 3, 3),
     f"gelen {_bg.sonraki_is_gunu(_dtg.date(2099, 3, 1))}")
_bg.HAREKETLI_TATIL.pop(2099, None)


# ══════════════════════════════════════════════════════════════════════
print("\n▶ Olay okura ulaştı mı (25. ölçüt)")

# ÖLÇÜLEN ARIZA (10.09.2026). Bülten JSON'u sekiz `dikkat` olayı taşıyordu ve
# sayfa hiçbirini basmıyordu: tekilleştirme süzgeci `notlar` kovasını "yukarıda
# basılıyor" varsayarak hat hat listesinden atıyordu, oysa o kovanın sayfada
# bölümü HİÇ OLMAMIŞTI. Derlenmiş 17 sayıda ölçüldü — 108 dikkat olayının
# 108'i yok, kontrol olarak 37 önemli olayın 37'si var. Ölçüt kaynağa değil
# ÇIKTIYA bakmak zorunda, çünkü olayı basan da süzen de bir BİLEŞEN.
#
# Sentetik çerçeve şart: ölçüt deponun O ANKİ dist'ini okusaydı, arıza
# düzeldiği gün madde ölçtüğü hâle bir daha hiç koşmazdı ve geri bozulduğunda
# sessiz kalırdı. Bu, depoda adı konmuş bir kusur sınıfı.
_OLAY_JSON = (
    '{"one_cikanlar": [{"hat": "h1", "anahtar": "a1", '
    '"metin": "Politika faizi 1,00 puan azaldı: %38,00 -> %37,00 ve devam."}], '
    '"notlar": [{"hat": "h2", "anahtar": "a2", '
    '"metin": "Son ihale bilesik maliyeti 2,07 puan azaldi: %43,11 -> %41,04."}]}'
)
_ONEMLI = "Politika faizi 1,00 puan azaldı: %38,00 -> %37,00 ve devam."
_DIKKAT = "Son ihale bilesik maliyeti 2,07 puan azaldi: %43,11 -> %41,04."

def _bulten_agaci(sayfa_govdesi: str) -> pathlib.Path:
    return _agac({
        "site/src/data/bulten/2026-09-10.json": _OLAY_JSON,
        "site/dist/bulten/2026-09-10/index.html": sayfa_govdesi,
    })

# (1) ARIZA HÂLİ — yalnız önemli basılıyor, dikkat kovası düşüyor.
_k = olay_okura_ulasti(_bulten_agaci(f"<ul><li>{_ONEMLI}</li></ul>"))
sina("basılmayan dikkat olayı ENGEL üretiyor",
     len(_k[0]) == 1 and "h2|a2" in _k[0][0], f"gelen {_k[0]}")

# (2) SAĞLIK HÂLİ — ikisi de basılıyor.
_k = olay_okura_ulasti(_bulten_agaci(f"<ul><li>{_ONEMLI}</li><li>{_DIKKAT}</li></ul>"))
sina("iki olay da basılıyorsa ölçüt susuyor", _k[0] == [] and _k[2] == 2, f"gelen {_k}")

# (3) YANLIŞ ALARM OLMASIN — kaçış. Astro kesme işaretini `&#39;`, `&`yi
# `&amp;` diye basar; kaçış çözülmeden aranan cümle sayfada DURSA DA
# bulunamaz. Ölçüldü: bu düzeltme olmadan beş olay kayıp sayılıyordu ve
# beşi de sayfadaydı — yayın kapısında duran bir ölçüt için beş yanlış alarm,
# siteyi durdurmak demek.
_KACISLI = "altın haber-duyarlılık endeksi 1 günde +0,04'den +0,20'ye geçti (S&P kıyas)"
_kok = _agac({
    "site/src/data/bulten/2026-09-10.json":
        '{"one_cikanlar": [], "notlar": [{"hat": "fx", "anahtar": "XAU", '
        f'"metin": "{_KACISLI}"}}]}}',
    "site/dist/bulten/2026-09-10/index.html":
        # SIRA ÖNEMLİ: önce `&`, sonra kesme işareti. Tersi `&#39;`in kendi
        # `&`ini bir kez daha kaçırır (`&amp;#39;`) ve fikstür GERÇEK bir
        # sayfayı taklit etmeyi bırakır — ilk yazımda tam bu oldu ve madde
        # ölçütü değil kendini düşürdü.
        "<span>" + _KACISLI.replace("&", "&amp;").replace("'", "&#39;") + "</span>",
})
sina("HTML kaçışlı cümle yanlış alarm üretmiyor",
     olay_okura_ulasti(_kok)[0] == [], f"gelen {olay_okura_ulasti(_kok)[0]}")

# (4) YANLIŞ ALARM OLMASIN — satır kaydırma. Derleyici cümleyi satırlara
# bölebilir; boşluk tekleştirme iki tarafa da uygulanıyor.
_kok = _agac({
    "site/src/data/bulten/2026-09-10.json":
        '{"one_cikanlar": [], "notlar": [{"hat": "h", "anahtar": "a", '
        f'"metin": "{_DIKKAT}"}}]}}',
    "site/dist/bulten/2026-09-10/index.html":
        "<span>" + _DIKKAT.replace(" ", "\n   ") + "</span>",
})
sina("satırlara bölünmüş cümle yanlış alarm üretmiyor",
     olay_okura_ulasti(_kok)[0] == [], f"gelen {olay_okura_ulasti(_kok)[0]}")

# (5) KAPSAM — derlenmemiş bir sayı SESSİZCE atlanır (dist'te sayfası yok),
# ama ölçüt bunu "geçti" diye SAYMAZ: aranan sayacı artmaz. Koşmamış bir
# ölçütün "temiz" görünmesi, depoda adı konmuş bir kusur.
_kok = _agac({"site/src/data/bulten/2026-09-10.json": _OLAY_JSON,
              "site/dist/bulten/baska/index.html": "<p>x</p>"})
sina("sayfası derlenmemiş sayı aranan sayısına girmiyor",
     olay_okura_ulasti(_kok) == ([], 0, 0), f"gelen {olay_okura_ulasti(_kok)}")


# ---------------------------------------------------------------------------
print("\n▶ İşlem fikri okura ulaştı mı (25d): açılan her fikrin kartı, karnenin her kaydı")
# KARAR (04.10.2026): bülten okumasını işlem fikirlerine çeviriyor ve karnesini
# mekanik tutuyor. Bölümü basan da koşulunu (biçim 3, yer, içindekiler) kuran da
# bileşendir; JSON doğruyken fikir okura hiç ulaşmayabilir. Fikstür DERLENMİŞ
# biçimi taşır: kapsam niteliği her etikette (`data-astro-cid-…`), başlık kartın
# çapalı öğesinde. Sentetik ağaç şart — ölçüt deponun o anki dist'ini okusaydı,
# fikirsiz bir günde madde ölçtüğü hâle hiç koşmazdı.
fikir_okura_ulasti = _mod.fikir_okura_ulasti
_FK_CID = ' data-astro-cid-vzeo3fk4'


def _fk_json(fikirler, kayitlar=(), yazili=True, surum=3):
    import json as _json
    return _json.dumps({
        "gundem_kaynagi": "yazili" if yazili else "kural", "surum": surum,
        "fikirler": [{"kimlik": k, "baslik": t} for k, t in fikirler],
        "fikir_karne": {"kayitlar": [{"kimlik": k, "baslik": t} for k, t in kayitlar], "sayim": {}},
    }, ensure_ascii=False)


def _fk_kart(kimlik, baslik):
    return (f'<article class="fk-kart"{_FK_CID}><h3 class="fk-baslik" id="fikir-{kimlik}"{_FK_CID}>'
            f'{baslik}</h3><p class="fk-ust"{_FK_CID}>Faiz · Eğri</p></article>')


def _fk_sayfa(govde):
    return (f'<main><section class="blok yazi-bolumu"{_FK_CID} id="y-risk"><h2{_FK_CID}>Risk</h2></section>'
            f'<section class="blok fikirler"{_FK_CID} id="fikirler"><h2{_FK_CID}>İşlem fikirleri</h2>'
            f'{govde}</section><section{_FK_CID} id="rejim"><p>Yassılaştırıcı başka yerde de geçer</p></section></main>')


_FK1 = ("2026-10-03-1", "TL eğrisinde 2y–7y yassılaştırıcı")
_FK2 = ("2026-10-03-2", "USD/TRY alım yayılımı")
_FKK = ("2026-09-22-1", "Brent kısa")
_FK_YOL = "site/src/data/bulten/2026-10-03.json"
_FK_SAYFA = "site/dist/bulten/2026-10-03/index.html"

# (1) SAĞLIK HÂLİ — iki kart ve bir karne satırı basılmış.
_k = fikir_okura_ulasti(_agac({
    _FK_YOL: _fk_json([_FK1, _FK2], [_FKK]),
    _FK_SAYFA: _fk_sayfa(_fk_kart(*_FK1) + _fk_kart(*_FK2)
                         + f'<table{_FK_CID}><tr><td class="p-ad"{_FK_CID}><span>{_FKK[1]}</span>'
                           f'<span class="p-tarih-ic"{_FK_CID}>açılış 22.09</span></td></tr></table>'),
}))
sina("basılmış fikir ve karne kaydı geçer", _k == ([], 3, 3), f"gelen {_k}")

# (2) ARIZA HÂLİ — ikinci fikrin kartı basılmamış (bileşen listeyi kesti).
_k = fikir_okura_ulasti(_agac({
    _FK_YOL: _fk_json([_FK1, _FK2]),
    _FK_SAYFA: _fk_sayfa(_fk_kart(*_FK1)),
}))
sina("basılmamış fikir ENGEL üretiyor",
     len(_k[0]) == 1 and "USD/TRY alım yayılımı" in _k[0][0] and _k[1:] == (2, 1), f"gelen {_k}")

# (3) ARIZA HÂLİ — kartlar hiç basılmadı ama AYNI başlıklı eski bir fikir
# karnede duruyor. Başlığı bölümün herhangi bir yerinde arayan bir ölçüt bunu
# "ulaştı" sayardı; ölçüt kartın KENDİ başlığına bakar.
_k = fikir_okura_ulasti(_agac({
    _FK_YOL: _fk_json([_FK1], [("2026-09-22-1", _FK1[1])]),
    _FK_SAYFA: _fk_sayfa(f'<table{_FK_CID}><tr><td class="p-ad"{_FK_CID}>{_FK1[1]}</td></tr></table>'),
}))
sina("karnedeki aynı başlık kartın yokluğunu örtmüyor",
     len(_k[0]) == 1 and "kartı sayfada YOK" in _k[0][0], f"gelen {_k}")

# (4) ARIZA HÂLİ — bölüm hiç basılmadı (koşul ya da yer kusuru): karne kaydı da düşer.
_k = fikir_okura_ulasti(_agac({
    _FK_YOL: _fk_json([], [_FKK]),
    _FK_SAYFA: f'<main><section{_FK_CID} id="rejim"><p>{_FKK[1]}</p></section></main>',
}))
sina("basılmamış fikir bölümü karne kaydını da ENGEL yapıyor",
     len(_k[0]) == 1 and "fikir bölümü sayfada YOK" in _k[0][0], f"gelen {_k}")

# (5) YANLIŞ ALARM OLMASIN — kaçış. Astro `&`yi `&amp;`, kesme işaretini
# `&#39;` basar (sıra: önce `&`); kaçış çözülmeden aranan başlık kartta DURSA
# DA bulunamazdı. Satır kaydırma da tekleşir.
_KACIS = ("2026-10-03-3", "Bankacılık & sigorta'nın göreli gücü")
_k = fikir_okura_ulasti(_agac({
    _FK_YOL: _fk_json([_KACIS]),
    _FK_SAYFA: _fk_sayfa(_fk_kart(_KACIS[0], _KACIS[1].replace("&", "&amp;").replace("'", "&#39;")
                                  .replace(" göreli", "\n      göreli"))),
}))
sina("kaçışlı ve satıra bölünmüş başlık yanlış alarm üretmiyor", _k == ([], 1, 1), f"gelen {_k}")
# (5b) YANLIŞ ALARM OLMASIN — eşitsizlik. Fikrin metni DÜZ METİNDİR ve HTML
# taşıyamaz, ama "<" ve ">" bir faiz fikrinde doğal: "2y < 5y". Başlığı etiket
# söker gibi süzmek "< 5y … >" aralığını siler ve kart dursa da ENGEL verirdi
# (inceleme 04.10.2026). Sayfa `&lt;`/`&gt;` basar.
_ESIT = ("2026-10-03-4", "Makas 2y < 5y kalırken 5y > 7y tümseği")
_k = fikir_okura_ulasti(_agac({
    _FK_YOL: _fk_json([_ESIT], [_ESIT]),
    _FK_SAYFA: _fk_sayfa(_fk_kart(_ESIT[0], _ESIT[1].replace("<", "&lt;").replace(">", "&gt;"))),
}))
sina("eşitsizlik taşıyan fikir başlığı yanlış alarm üretmiyor (25d)", _k == ([], 2, 2), f"gelen {_k}")
# (5c) ÇIKIŞ EMRİ — bu sayıda verilen erken kapanış emrinin sebebi fikir
# bölümünde basılmalı; basılmazsa okur emri hiçbir sayfada görmezdi.
import json as _jfk
_EMIR = _jfk.dumps({"gundem_kaynagi": "yazili", "surum": 3, "fikirler": [],
                    "fikir_karne": {"kayitlar": [], "sayim": {}},
                    "fikir_kapat": [{"kimlik": "2026-09-29-1", "sebep": "TÜFE eşiği aştı, görüş bozuldu"}]},
                   ensure_ascii=False)
_k = fikir_okura_ulasti(_agac({_FK_YOL: _EMIR, _FK_SAYFA: _fk_sayfa(
    f'<ul class="fk-emir"{_FK_CID}><li{_FK_CID}><a href="#x">Banka</a>: TÜFE eşiği aştı, görüş bozuldu.</li></ul>')}))
sina("bu sayıda verilen çıkış emri fikir bölümünde (25d)", _k == ([], 1, 1), f"gelen {_k}")
_k = fikir_okura_ulasti(_agac({_FK_YOL: _EMIR, _FK_SAYFA: _fk_sayfa("<p>boş</p>")}))
sina("basılmayan çıkış emri ENGEL (25d)", len(_k[0]) == 1 and "çıkış emri" in _k[0][0], f"gelen {_k}")

# (6) KAPSAM — yazılmamış ya da biçim 2 sayı sorulmaz; fikir taşıyan yazılmış
# bir sayının derlenmiş sayfası YOKSA ise ölçüt SUSMAZ (koşmamış ölçüt geçmiş
# sayılmaz — 20/21'in kuralı).
_k = fikir_okura_ulasti(_agac({
    "site/src/data/bulten/2026-10-01.json": _fk_json([_FK1], yazili=False),
    "site/src/data/bulten/2026-10-02.json": _fk_json([_FK1], surum=2),
    "site/dist/bulten/baska/index.html": "<p>x</p>",
}))
sina("yazılmamış ve biçim 2 sayı sorulmuyor", _k == ([], 0, 0), f"gelen {_k}")
_k = fikir_okura_ulasti(_agac({_FK_YOL: _fk_json([_FK1]), "site/dist/bulten/baska/index.html": "<p>x</p>"}))
sina("derlenmemiş fikirli sayı sessizce atlanmıyor",
     len(_k[0]) == 1 and "derlenmiş sayfası yok" in _k[0][0], f"gelen {_k}")

# (7) YAPISAL KİLİT — ölçüt sınavın ana akışında çağrılıyor (yazılıp listeye
# konmayan bir ölçüt hiç koşmaz).
_ss = _YOL.read_text(encoding="utf-8")
sina("25d sınavın ana akışında koşuyor", "fikir_okura_ulasti(KOK)" in _ss[_ss.find("def main"):])
# Bugün depoda fikir taşıyan bir sayı olmayabilir; o günlerde 25d gerçek ağaçta
# hiçbir şey aramaz. Bileşenin sözleşmesi yapısal olarak kilitli: bölüm var,
# kart çapası kimlikten, içindekiler ve basım AYNI diziden (yaziAkisi).
_bg_fk = (_YOL.parents[1] / "src/components/BultenGovde.astro").read_text(encoding="utf-8")
sina("bileşen fikir bölümünü ve kart çapasını basıyor",
     'id="fikirler"' in _bg_fk and 'id={`fikir-${f.kimlik}`}' in _bg_fk)
sina("içindekiler ve basım aynı diziden (yaziAkisi)",
     _bg_fk.count("yaziAkisi.map(") == 2 and "yaziBolumleri.map((x: any) => ({ id: `y-" not in _bg_fk)


# ---------------------------------------------------------------------------
print(f"\n▶ İşlem fikri deftere ulaştı mı ({_mod.TRADELER_OLCUT}): Tradeler sayfası, kart ve kapanış bölümü")
# Kullanıcı (04.10.2026): fikirler "sadece verilmekle kalınmamalı, takip
# edilmeli". Defter (/tradeler/) sayıların kendisinden kurulur; onu basan da,
# fikri açık ya da kapanan bölüme koyan da BİLEŞENDİR. Fikstür derlenmiş biçimi
# taşır (kapsam niteliği her etikette, başlık bülten kartına bağ içinde) ve
# kapanmış durumların kümesi deponun GERÇEK bulten/fikir.py'sinden okunur —
# ölçüt tanımı orada arıyor, fikstür onu kopyalasaydı ayrışmayı göremezdi.
trade_okura_ulasti = _mod.trade_okura_ulasti
_TR_CID = ' data-astro-cid-tr4d3k4r'
_FIKIR_PY = (_YOL.parents[2] / "bulten/fikir.py").read_text(encoding="utf-8")


def _tr_json(fikirler=(), kayitlar=(), yazili=True, surum=3):
    import json as _json
    return _json.dumps({
        "gundem_kaynagi": "yazili" if yazili else "kural", "surum": surum,
        "fikirler": [{"kimlik": k, "baslik": t} for k, t in fikirler],
        "fikir_karne": {"kayitlar": [{"kimlik": k, "baslik": t, "tur": tur, "durum": d}
                                      for k, t, tur, d in kayitlar], "sayim": {}},
    }, ensure_ascii=False)


def _tr_kart(kimlik, baslik):
    return (f'<article class="tr-kart"{_TR_CID}><h3 class="tr-baslik" id="trade-{kimlik}"{_TR_CID}>'
            f'<a href="/bulten/2026-10-03/#fikir-{kimlik}"{_TR_CID}>{baslik}</a></h3>'
            f'<p class="tr-ust"{_TR_CID}>Faiz · Eğri</p></article>')


def _tr_sayfa(acik="", kapanan="", karnesiz=""):
    return (f'<main><section class="tr-bolum"{_TR_CID} id="acik"><h2{_TR_CID}>Açık tradeler</h2>{acik}</section>'
            f'<section class="tr-bolum"{_TR_CID} id="kapanan"><h2{_TR_CID}>Kapanan tradeler</h2>{kapanan}</section>'
            f'<section class="tr-bolum"{_TR_CID} id="karnesiz"><h2{_TR_CID}>Karnesi tutulmayanlar</h2>{karnesiz}</section>'
            '</main>')


_TR1 = ("2026-10-03-1", "TL eğrisinde 2y–7y yassılaştırıcı")
_TR2 = ("2026-10-03-2", "Brent kısa")
_TR_YAZ = "site/src/data/bulten/2026-10-03.json"
_TR_OLC = "site/src/data/bulten/2026-10-07.json"       # yazılmamış sayı: karne yine ölçüdür
_TR_SAYFA = "site/dist/tradeler/index.html"


def _tr_agac(dosyalar):
    return _agac({"bulten/fikir.py": _FIKIR_PY, **dosyalar})


# (1) SAĞLIK HÂLİ — iki fikir defterde, biri yazılmamış bir sayının karnesinde
# stopta kapandı ve "Kapanan tradeler"de duruyor.
_k = trade_okura_ulasti(_tr_agac({
    _TR_YAZ: _tr_json([_TR1, _TR2]),
    _TR_OLC: _tr_json(kayitlar=[(*_TR2, "yalin", "stop"), (*_TR1, "egri", "acik")], yazili=False),
    _TR_SAYFA: _tr_sayfa(acik=_tr_kart(*_TR1), kapanan=_tr_kart(*_TR2)),
}))
sina("defterdeki fikir ve kapanış bölümündeki kapanmış fikir geçer", _k == ([], 3, 3), f"gelen {_k}")

# (2) ARIZA HÂLİ — ikinci fikrin kartı defterde yok (bileşen listeyi kesti).
_k = trade_okura_ulasti(_tr_agac({
    _TR_YAZ: _tr_json([_TR1, _TR2]),
    _TR_SAYFA: _tr_sayfa(acik=_tr_kart(*_TR1)),
}))
sina("defterde kartı olmayan fikir ENGEL",
     len(_k[0]) == 1 and "Brent kısa" in _k[0][0] and "kartı YOK" in _k[0][0] and _k[1:] == (2, 1), f"gelen {_k}")

# (3) ARIZA HÂLİ — stopta kapanmış fikir AÇIK listede bekliyor (grup kuralı
# Python'un kapanmış kümesinden ayrıştı). Sayı doğru, defter yanlış.
_k = trade_okura_ulasti(_tr_agac({
    _TR_YAZ: _tr_json([_TR1, _TR2]),
    _TR_OLC: _tr_json(kayitlar=[(*_TR2, "yalin", "stop")], yazili=False),
    _TR_SAYFA: _tr_sayfa(acik=_tr_kart(*_TR1) + _tr_kart(*_TR2)),
}))
sina("kapanmış fikir açık listedeyse ENGEL",
     len(_k[0]) == 1 and "bölümünde DEĞİL" in _k[0][0], f"gelen {_k}")

# (4) ARIZA HÂLİ — kart yok ama aynı başlıklı başka bir kart duruyor; başlığı
# sayfanın herhangi bir yerinde arayan ölçüt bunu "ulaştı" sayardı.
_k = trade_okura_ulasti(_tr_agac({
    _TR_YAZ: _tr_json([_TR1]),
    _TR_SAYFA: _tr_sayfa(acik=_tr_kart("2026-09-22-1", _TR1[1])),
}))
sina("aynı başlıklı başka kart kartın yokluğunu örtmüyor",
     len(_k[0]) == 1 and "kartı YOK" in _k[0][0], f"gelen {_k}")

# (5) YANLIŞ ALARM OLMASIN — kaçış ve satır kaydırma (25d'nin süzgeci).
_TR_KACIS = ("2026-10-03-3", "Bankacılık & sigorta'nın göreli gücü")
_k = trade_okura_ulasti(_tr_agac({
    _TR_YAZ: _tr_json([_TR_KACIS]),
    _TR_SAYFA: _tr_sayfa(acik=_tr_kart(_TR_KACIS[0], _TR_KACIS[1].replace("&", "&amp;").replace("'", "&#39;")
                                       .replace(" göreli", "\n      göreli"))),
}))
sina("defterde kaçışlı ve satıra bölünmüş başlık yanlış alarm üretmiyor", _k == ([], 1, 1), f"gelen {_k}")
_k = trade_okura_ulasti(_tr_agac({
    _TR_YAZ: _tr_json([("2026-10-03-4", "Makas 2y < 5y kalırken 5y > 7y tümseği")]),
    _TR_OLC: _tr_json(kayitlar=[("2026-10-03-4", "Makas 2y < 5y kalırken 5y > 7y tümseği", "egri", "stop")],
                      yazili=False),
    _TR_SAYFA: _tr_sayfa(kapanan=_tr_kart("2026-10-03-4", "Makas 2y &lt; 5y kalırken 5y &gt; 7y tümseği")),
}))
sina("eşitsizlik taşıyan fikir başlığı defterde yanlış alarm üretmiyor (25e)", _k == ([], 2, 2), f"gelen {_k}")

# (6) KAPSAM — yazılmamış ve biçim 2 sayının fikri sorulmaz; karnesi
# tutulmayan fikrin ufku dolması (sure_olculemez) kapanan bölümü istemez;
# fikir varken derlenmiş defter YOKSA ölçüt susmaz.
_k = trade_okura_ulasti(_tr_agac({
    "site/src/data/bulten/2026-10-01.json": _tr_json([_TR1], yazili=False),
    "site/src/data/bulten/2026-10-02.json": _tr_json([_TR2], surum=2),
    _TR_OLC: _tr_json(kayitlar=[("2026-09-22-4", "TRY OIS–Londra bazı", "olculemez", "sure_olculemez")], yazili=False),
    "site/dist/baska/index.html": "<p>x</p>",
}))
sina("yazılmamış, biçim 2 ve karnesiz fikir defter ölçütünde sorulmuyor", _k == ([], 0, 0), f"gelen {_k}")
_k = trade_okura_ulasti(_tr_agac({_TR_YAZ: _tr_json([_TR1]), "site/dist/baska/index.html": "<p>x</p>"}))
sina("fikir varken derlenmemiş defter sessizce atlanmıyor",
     len(_k[0]) == 1 and "derlenmiş sayfası yok" in _k[0][0], f"gelen {_k}")

# (7) TEK TANIM — kapanmış durumlar ve durum etiketleri: site eşi (lib/fikir.ts)
# Python'un tanımıyla birebir. Ayrışırsa defter kapanmış bir fikri açık sayar
# ve 25e bunu ancak o hâl veride doğduğu gün görürdü.
import ast as _ast
import re as _re
_kapanmis_py = _mod._fikir_kapanmis_durumlar(_YOL.parents[2])
_fk_ts = (_YOL.parents[1] / "src/lib/fikir.ts").read_text(encoding="utf-8")
_m = _re.search(r"FIKIR_KAPANMIS = new Set\(\[(.*?)\]\)", _fk_ts, _re.S)
_kapanmis_ts = set(_re.findall(r"'([a-z_]+)'", _m.group(1))) if _m else set()
sina("lib/fikir FIKIR_KAPANMIS = bulten/fikir KAPANMIS", _kapanmis_ts == _kapanmis_py,
     f"site {sorted(_kapanmis_ts)} · Python {sorted(_kapanmis_py)}")
_m = _re.search(r"FIKIR_DURUM: Record<string, string> = \{(.*?)\};", _fk_ts, _re.S)
_durum_ts = set(_re.findall(r"([a-z_]+):", _m.group(1))) if _m else set()
sina("her karne durumunun okur etiketi var", (_kapanmis_py | {"acik", "olculemez"}) <= _durum_ts,
     f"eksik {sorted((_kapanmis_py | {'acik', 'olculemez'}) - _durum_ts)}")
# Uyarı ve yöntem metni TEK yerde: bülten bölümü ikinci kopyayı taşımaz.
sina("bülten bölümü uyarı/yöntem metnini kendisi yazmıyor (lib/fikir)",
     "const FIKIR_UYARI" not in _bg_fk and "FIKIR_YONTEM" in _bg_fk and "Referans seviye yazarın değil" not in _bg_fk)
sina("bülten bölümü deftere bağ veriyor", "bolumBul('/tradeler/')" in _bg_fk)

# (8) YAPISAL KİLİT — ölçüt ana akışta; kart çapası kimlikten; kapanış bölümü var.
sina(f"{_mod.TRADELER_OLCUT} sınavın ana akışında koşuyor", "trade_okura_ulasti(KOK)" in _ss[_ss.find("def main"):])
_tk = (_YOL.parents[1] / "src/components/TradeKart.astro").read_text(encoding="utf-8")
_tp = (_YOL.parents[1] / "src/pages/tradeler/index.astro").read_text(encoding="utf-8")
sina("defter kartı çapası kimlikten (trade-<kimlik>)", 'id={`trade-${t.kimlik}`}' in _tk)
sina("defter kapanan bölümünü basıyor", 'id="kapanan"' in _tp and "t.grup === 'kapanan'" in _tp)
# Karnesi tutulmayan fikir de kapanır: rozet durumdan, kapanmışsa "açık" demez
# (inceleme 04.10.2026 — erken kapatılan baz fikri "açık" basılıyordu).
sina("karnesiz kartın rozeti kapanmış durumu tanıyor",
     "const karnesizKapali = karnesiz && FIKIR_KAPANMIS.has(durum)" in _tk
     and "karnesizKapali ? FIKIR_DURUM[durum]" in _tk)
# Karne kurulamadıysa ya da bu sayıda çıkış emri verildiyse bölüm yeni fikir
# yokken de basılır (kusur ve emir görünür kalır).
sina("fikir bölümü karne hatasında ve çıkış emrinde de açılıyor",
     "fikirKapat.length > 0" in _bg_fk and "(bicim3 && !!fikirKarne.hata)" in _bg_fk)

# (9) BÖLÜM NUMARALARI — Tradeler bülteni izler; numaralar boşluksuz ve tekil
# (başlık, alt bilgi, 404, hakkında ve kicker'lar bu listeden okur).
_bl = (_YOL.parents[1] / "src/lib/bolumler.ts").read_text(encoding="utf-8")
_no = _re.findall(r"no: '(\d{2})', ad: '([^']+)'", _bl)
sina("bölüm numaraları 01'den boşluksuz ve tekil",
     [n for n, _a in _no] == [f"{i:02d}" for i in range(1, len(_no) + 1)], f"gelen {_no}")
sina("Tradeler Bülten'in hemen ardında", [a for _n, a in _no][:2] == ["Bülten", "Tradeler"], f"gelen {_no[:3]}")


# ---------------------------------------------------------------------------
print("\n▶ Şekil yüksekliği (3): çerçeve figürü kırpıyor mu")
# ÖLÇÜLEN ARIZA (25.09.2026): fonlama Şekil 04'ün alt yazısındaki koşullu
# cümle (alım yönlü swap stoku sıfırken basılıyor) kalktı, figür 1159'dan
# 1133'e kısaldı, sayfa 1159 ilan ediyordu ve eski EŞİTLİK ölçütü yayını
# durdurdu. Aynı gün YP mevduat Şekil 05 ters yönde ayrışmıştı (sayfa 1165,
# figür 1191) ve canlı sitede 26 piksel kırpılıyordu — o hat bu ölçütte yalnız
# bilgiydi. Kural artık: elle yazılan yükseklik ALT SINIR, figürün ilanı onu
# aşarsa ilan (ortak/figur_olcu.py ↔ site/src/lib/grafikOlcu.ts).
yukseklik_denetle = _mod.yukseklik_denetle
fo = _mod._figur_olcu()


def _figur(h: int | None, onde_tablo: bool = False) -> str:
    """Plotly çıktısının biçimi: newPlot("kimlik", [izler], {düzen}, {ayar}).
    Dizgelerde } ] ve kaçışlı tırnak — tarayıcı onlarda şaşmamalı."""
    iz = ('{"type":"table","cells":{"height":24},"header":{"height":42}}' if onde_tablo
          else '{"type":"scatter","name":"a ] } \\" b","y":[1,2]}')
    duzen = '{"margin":{"t":80},' + (f'"height":{h},' if h is not None else "") \
            + '"title":{"text":"x } y ] \\" z"}}'
    return ('<div id="x"></div><script>window.PLOTLYENV={};Plotly.newPlot(\n  "x",\n  ['
            + iz + '],\n  ' + duzen + ',\n  {"responsive": true})</script>')


sina("düzenin yüksekliği okunuyor, tablo hücresininki değil (bütçe Şekil 09)",
     fo.ilan_edilen_yukseklik(_figur(1227, onde_tablo=True)) == 1227,
     f"gelen {fo.ilan_edilen_yukseklik(_figur(1227, onde_tablo=True))}")
sina("düzeninde yükseklik olmayan figür ilan etmiyor sayılır",
     fo.ilan_edilen_yukseklik(_figur(None, onde_tablo=True)) is None,
     f"gelen {fo.ilan_edilen_yukseklik(_figur(None, onde_tablo=True))}")
sina("2.300 piksellik meşru figür okunuyor, tavan dışı yükseklik okunmuyor",
     fo.ilan_edilen_yukseklik(_figur(2300)) == 2300
     and fo.ilan_edilen_yukseklik(_figur(9000)) is None)
sina("çerçeve kuralı: elle yazılan alt sınır, ilan onu aşarsa ilan",
     (fo.cerceve_yuksekligi(1159, 1133), fo.cerceve_yuksekligi(1165, 1191),
      fo.cerceve_yuksekligi(None, 1133), fo.cerceve_yuksekligi(None, None))
     == (1159, 1191, 1133, 540))


def _gomme(src: str, yuk: int | None = None) -> str:
    return (f'<GrafikEmbed\n  src="{src}"\n  baslik="b"\n  no="01"\n'
            + (f"  yukseklik={{{yuk}}}\n" if yuk is not None else "") + "/>\n")


_site = _agac({"04.html": _figur(1133), "05.html": _figur(1191),
               "07.html": _figur(None), "08.html": _figur(None)})
e, b = yukseklik_denetle("fon", {"04.html": 1133},
                         [("projeler/fon", _gomme("/projeler/fon/04.html", 1159))], _site)
sina("25.09 vakası: figür kısaldı, sayfa eski sayıyı ilan ediyor → ENGEL DEĞİL, bilgi",
     e == [] and len(b) == 1, f"engel {e} · bilgi {b}")
e, b = yukseklik_denetle("fon", {"05.html": 1191},
                         [("projeler/fon", _gomme("/projeler/fon/05.html", 1165))], _site)
sina("figür büyüdü, sayfa eski sayıyı ilan ediyor → çerçeve figürü izler, kırpılmaz",
     e == [], f"engel {e}")
e, b = yukseklik_denetle("fon", {"07.html": 1999},
                         [("projeler/fon", _gomme("/projeler/fon/07.html", 1973))], _site)
sina("yüksekliğini ilan etmeyen figürde elle yazılan sayı üretimin altında → ENGEL",
     len(e) == 1 and "kırpılır" in e[0], f"engel {e}")
e, b = yukseklik_denetle("fon", {"04.html": 1133},
                         [("projeler/fon", _gomme("/projeler/fon/05.html", 1191))], _site)
sina("üretilen ama hiçbir sayfada gömülü olmayan figür → ENGEL",
     e == ["04.html: hiçbir sayfada gömülü değil"], f"engel {e}")
# Eski kalıp `src` ile `yukseklik` arasına 400 karakter tanıyordu: yüksekliği
# yazılmamış bir gömmede SONRAKİ gömmenin sayısını okurdu (burada 1200 → geçerdi).
e, b = yukseklik_denetle("fon", {"08.html": 1100},
                         [("projeler/fon", _gomme("/projeler/fon/08.html")
                           + _gomme("/projeler/fon/04.html", 1200))], _site)
sina("gömme bloğu dışına taşılmıyor: komşu gömmenin yüksekliği okunmaz",
     len(e) == 1 and "çerçeve 540" in e[0], f"engel {e}")
# Eski ölçüt ilk bulduğu gömmede duruyordu: panodaki doğru sayı analizdeki
# kırpan sayıyı gizlerdi.
e, b = yukseklik_denetle("fon", {"08.html": 1100},
                         [("projeler/fon", _gomme("/projeler/fon/08.html", 1100)),
                          ("analiz/yazi", _gomme("/projeler/fon/08.html", 900))], _site)
sina("figürün HER gömmesi sorulur: analizdeki kırpan gömme ENGEL",
     len(e) == 1 and "analiz/yazi" in e[0], f"engel {e}")

# İki dilde tek kural: sabitler ve öncelik iki kaynakta aynı kalmalı. Bileşen
# derleme anında TS'ten, kapılar Python'dan okur; biri sessizce değişirse
# kapı, sayfanın kurmadığı bir çerçeveyi sınar.
_ts = (pathlib.Path(__file__).resolve().parents[1] / "src/lib/grafikOlcu.ts").read_text(encoding="utf-8")
_ts_sabit = {ad: int(m.group(1)) for ad in ("ONTANIMLI", "EN_AZ", "EN_COK")
             if (m := __import__("re").search(rf"const {ad} = (\d+);", _ts))}
sina("grafikOlcu.ts ↔ figur_olcu.py: sabitler ve öncelik aynı",
     _ts_sabit == {"ONTANIMLI": fo.ONTANIMLI, "EN_AZ": fo.EN_AZ, "EN_COK": fo.EN_COK}
     and "Math.max(acik, ilan)" in _ts and "Plotly.newPlot(" in _ts,
     f"TS {_ts_sabit} · Python {fo.ONTANIMLI, fo.EN_AZ, fo.EN_COK}")


# ── (27) BASIM SÖZLEŞMESİ ─────────────────────────────────────────────────
# Üç kusur 30.09.2026'da canlı sitede ölçüldü; ölçüt derlenmiş biçime karşı
# sınanır (Astro kapsam nitelikleri dahil) — fikstür gerçeği taşımazsa geçer
# ama canlı çıktıda tutmaz (22.09.2026 dersi).
basim = _mod.basim_bulgulari
_cid = ' data-astro-cid-abc123'
# Büyük harf bağlamı: kusur HTML'de görünmez ("σ" durur, çizimde "Σ" çıkar),
# bağlam derlenmiş CSS'ten hesaplanır. Fikstür derlenmiş biçimi taşır —
# global kural (`.prose thead th`), Astro kapsamlı kural
# (`thead[data-astro-cid-…] th[data-astro-cid-…]`) ve koruma kuralı
# (`.harf-koru, .katex`). İlk ölçüt ham HTML'de "Σ" arıyordu ve bu
# fikstürlerin hiçbirinde tutmazdı.
_CSS = ('<style>.etiket{font-size:.7rem;text-transform:uppercase}'
        '.prose thead th{text-transform:uppercase;letter-spacing:.1em}'
        '.harf-koru,.katex{text-transform:none}'
        f'thead[data-astro-cid-abc123] th[data-astro-cid-abc123]{{text-transform:uppercase}}'
        'table.p-tablo th{text-transform:none}'
        '.kicker:hover{text-transform:uppercase}'
        '@media (max-width:640px){.dar > b{text-transform:uppercase}}</style>')
def _bh(govde, css=_CSS, lang="tr"):
    return basim([("x/index.html", f'<!doctype html><html lang="{lang}"><head>{css}</head><body>{govde}</body></html>')])
sina("büyük harf: tablo başlığında σ (global kural) ENGEL",
     len(_bh('<div class="prose"><table><thead><tr><th>Artık σ</th></tr></thead></table></div>')) == 1)
sina("büyük harf: Astro kapsamlı başlıkta β ENGEL",
     len(_bh(f'<table{_cid}><thead{_cid}><tr{_cid}><th{_cid}>yıllık β</th></tr></thead></table>')) == 1)
sina("büyük harf: .harf-koru içindeki σ geçer",
     not _bh('<div class="prose"><table><thead><tr><th>1<span class="harf-koru">σ</span> aylık</th></tr></thead></table></div>'))
sina("büyük harf: KaTeX çıktısı geçer",
     not _bh('<p class="etiket"><span class="katex"><span class="mord mathnormal">σ</span></span></p>'))
sina("büyük harf: özgül 'none' kuralı ezer (bülten tablosu)",
     not _bh('<table class="p-tablo"><thead><tr><th>1 gün σ</th></tr></thead></table>'))
sina("büyük harf: dönüşümsüz bağlamda σ geçer", not _bh('<p>Günlük σ 1,2</p>'))
sina("büyük harf: yalnız :hover kuralı sayılmaz", not _bh('<p class="kicker">σ</p>'))
sina("büyük harf: @media içindeki çocuk kuralı sayılır",
     len(_bh('<div class="dar"><b>τ</b></div>')) == 1 and not _bh('<div class="dar"><i><b>τ</b></i></div>'))
sina("büyük harf: lang=tr altında 'TradingView' ENGEL",
     len(_bh('<p class="etiket">pine script · tradingview</p>')) == 3)
sina("büyük harf: lang=en ile korunan ad ve büyük harfli 'OIS' geçer",
     not _bh('<p class="etiket"><span lang="en">pine</span> · OIS iskonto</p>'))
sina("büyük harf: İngilizce sayfada ad taranmaz", not _bh('<p class="etiket">tradingview</p>', lang="en"))
sina("büyük harf: bağlı CSS dosyası okunur",
     len(basim([("x/index.html", '<html lang="tr"><head><link rel="stylesheet" href="/_astro/a.css"></head>'
                                 '<body><span class="etiket">Vol σ</span></body></html>')],
               lambda h: ".etiket{text-transform:uppercase}" if h == "/_astro/a.css" else "")) == 1)
# Bülten ızgarası geniş ekranda açılıyor: derlenmiş SIRA sorulur (Astro iki
# <style> bloğunu ters yazınca geniş ekran kuralı temel kurala yeniliyordu).
_gb = _mod.genis_ekran_bulgusu
sina("geniş ekran: temel kuraldan SONRA gelen 'none' geçer",
     _gb(".bulten[data-astro-cid-a]{max-width:46rem}@media (min-width:1200px){.bulten[data-astro-cid-a]{max-width:none}}") is None)
sina("geniş ekran: temel kuraldan ÖNCE gelen 'none' ENGEL",
     _gb("@media (min-width:1200px){.bulten[data-astro-cid-a]{max-width:none}}.bulten[data-astro-cid-a]{max-width:46rem}") is not None)
sina("geniş ekran: yalnız dar ekran kuralı 1440'ı bağlamaz",
     _gb(".bulten{max-width:none}@media (max-width:640px){.bulten{max-width:30rem}}") is None)
sina("geniş ekran: bağlı CSS ile sayfa sınavında ENGEL",
     any("ızgarası" in x for x in basim([("bulten/x/index.html",
         '<html lang="tr"><head><style>@media (min-width:1200px){.bulten{max-width:none}}.bulten{max-width:46rem}</style></head>'
         '<body><article class="bulten"><div class="bulten-izgara"></div></article></body></html>')])))
# Liste tek tanım: site tarafı (harf.mjs) ile kapı aynı adları taşır; eklenti
# KaTeX'ten SONRA kayıtlı (önce koşsa KaTeX'in ürettiği metni sarmaz ama
# KaTeX'e giden ham metni böler).
import buyuk_harf_baglam as _bhm
_SITE = pathlib.Path(__file__).resolve().parents[1]
_hm = (_SITE / "src/lib/harf.mjs").read_text(encoding="utf-8")
_hm_liste = __import__("re").search(r"export const YABANCI = \[(.*?)\];", _hm, __import__("re").S)
_ac = (_SITE / "astro.config.mjs").read_text(encoding="utf-8")
sina("harf.mjs ↔ buyuk_harf_baglam.py: yabancı ad listesi aynı; eklenti KaTeX'ten sonra",
     _hm_liste is not None
     and sorted(__import__("re").findall(r"'([^']+)'", _hm_liste.group(1))) == sorted(_bhm.YABANCI)
     and __import__("re").search(r"rehypeKatex,[^\]]*\],\s*rehypeHarfKoru", _ac) is not None,
     f"harf.mjs {_hm_liste.group(1) if _hm_liste else None} · py {_bhm.YABANCI}")
def _gk(deger, fark):
    # Derlenmiş kartın birebir biçimi (01.10.2026 önizlemesi): seviye iç içe
    # g-birim taşıyabilir, fark ondan sonra gelir.
    return (f'<div class="gosterge"{_cid}> <span class="g-ad"{_cid}>x</span> <span class="g-deger"{_cid}> {deger} </span> '
            f'<span class="g-fark eksi"{_cid}> {fark} </span> </div>')
sina("gösterge farkı '−%0,24' ENGEL (seviye yüzde)",
     len(basim([("b/index.html", _gk("%31,51", "−%0,24"))])) == 1)
sina("gösterge farkı '−0,24 puan' geçer",
     not basim([("b/index.html", _gk("%31,51", "−0,24 puan"))]))
sina("kurun yüzde farkı geçer (seviye yüzde değil: '49,01' · '+%0,02')",
     not basim([("b/index.html", _gk(f'49,01<span class="g-birim"{_cid}></span>', "+%0,02"))]))
sina("rejim farkı birimsiz ('−3,2') ENGEL",
     len(basim([("b/index.html", f'<span class="rj-deger"{_cid}> %24,7 <span class="rj-fark" title="x"{_cid}>−3,2</span> </span>')])) == 1)
sina("rejim farkı '−3,2 puan' (görünmez önekle) geçer",
     not basim([("b/index.html", f'<span class="rj-deger"{_cid}> %24,7 <span class="rj-fark" title="x"{_cid}><span class="gorunmez"{_cid}>önceki ölçüme göre </span>−3,2 puan</span> </span>')]))
sina("bp birimli fark geçer ('−6,5 bp')",
     not basim([("b/index.html", _gk("%40,50", "−6,5 bp"))]))
# Takvimde aynı yayım (gün · saat · olay) iki satır: BDDK'nın on bir alt tablosu
# on bir satır basılıyordu. Aynı günün ikinci satırında tarih hücresi boştur.
def _tk(*satirlar):
    govde = "".join(f'<tr{_cid}> <td class="t-tarih"{_cid}>{t}</td> <td class="t-saat"{_cid}>{sa}</td> '
                    f'<td class="t-ulke"{_cid}>TR</td> <td class="t-olay"{_cid}> {o} <span class="dipnot"{_cid}>not</span></td> </tr>'
                    for t, sa, o in satirlar)
    return f'<table class="takvim"{_cid}><tbody{_cid}>{govde}</tbody></table>'
_gun = '29 Eylül 2026<span class="t-gun"' + _cid + '>Salı</span>'
sina("takvimde aynı yayım iki satır ENGEL (tarih boş ikinci satır dahil)",
     len(basim([("bulten/x/index.html", _tk((_gun, "14:00", "BDDK: Bankacılık sektörü (Ağustos 2026)"),
                                             ("", "14:00", "BDDK: Bankacılık sektörü (Ağustos 2026)")))])) == 1)
sina("aynı gün farklı saat ya da farklı olay geçer",
     not basim([("bulten/x/index.html", _tk((_gun, "10:00", "TÜİK: İşgücü (Ağustos 2026)"),
                                            ("", "10:00", "TÜİK: Dış ticaret (Ağustos 2026)"),
                                            ("", "14:00", "TÜİK: İşgücü (Ağustos 2026)")))]))
# GERÇEK BİÇİM (01.10.2026): olay adı resmî adı ipucunda taşıyan bir öğeye
# sarılı ve önünde bir etiket var. İlk ölçüt adı "ilk etikete kadar" okuyordu,
# her satır boş adla "aynı" çıktı ve derlenmiş sitede 233 sahte bulgu verdi.
def _tk_sarili(*satirlar):
    govde = "".join(f'<tr{_cid}> <td class="t-tarih"{_cid}>{t}</td> <td class="t-saat"{_cid}>{sa}</td> '
                    f'<td class="t-ulke"{_cid}>TR</td> <td class="t-olay"{_cid}> <span title="Resmî ad"{_cid}>{o}</span>'
                    f' <span class="beklenti"{_cid}>model: 50,9</span></td> </tr>'
                    for t, sa, o in satirlar)
    return f'<table class="takvim"{_cid}><tbody{_cid}>{govde}</tbody></table>'
sina("ipucuna sarılı farklı adlar aynı saatte geçer",
     not basim([("bulten/x/index.html", _tk_sarili((_gun, "14:30", "TCMB: Menkul kıymet ist. (39. Hafta 2026)"),
                                                   ("", "14:30", "TCMB: Haftalık para-banka (39. Hafta 2026)")))]))
sina("ipucuna sarılı aynı ad iki satır ENGEL",
     len(basim([("bulten/x/index.html", _tk_sarili((_gun, "14:30", "TCMB: Haftalık para-banka (39. Hafta 2026)"),
                                                   ("", "14:30", "TCMB: Haftalık para-banka (39. Hafta 2026)")))])) == 1)
sina("aynı olay farklı günde geçer",
     not basim([("bulten/x/index.html", _tk((_gun, "14:00", "BDDK: Bankacılık sektörü (39. Hafta 2026)"),
                                            ('1 Ekim 2026<span class="t-gun"' + _cid + '>Perşembe</span>', "14:00",
                                             "BDDK: Bankacılık sektörü (39. Hafta 2026)")))]))
# Biçim 3 günlük sayının katlı SIKIŞIK takvim listesi (derlenmiş biçim): ölçüt
# yalnız tabloyu okuyordu ve bu listede tekrar YAKALANMIYORDU.
def _ts(*satirlar):
    li = "".join(f'<li{_cid}> <span class="ts-zaman"{_cid}>{z}</span> <span title="Resmî ad"{_cid}>{o}</span> '
                 f'<span class="dipnot"{_cid}>not</span> </li>' for z, o in satirlar)
    return f'<ul class="takvim-sikisik"{_cid}>{li}</ul>'
sina("sıkışık takvim listesinde aynı yayım iki satır ENGEL",
     len(basim([("bulten/x/index.html", _ts(("02.10.2026 Cuma · 10:00 · TR", "TÜİK: Dış ticaret (Ağustos 2026)"),
                                             ("02.10.2026 Cuma · 10:00 · TR", "TÜİK: Dış ticaret (Ağustos 2026)")))])) == 1)
sina("sıkışık listede aynı ad farklı saatte geçer",
     not basim([("bulten/x/index.html", _ts(("02.10.2026 Cuma · 10:00 · TR", "TÜİK: Dış ticaret (Ağustos 2026)"),
                                            ("02.10.2026 Cuma · 11:00 · TR", "TÜİK: Dış ticaret (Ağustos 2026)")))]))


# PAZAR DÜZENİNDE HABER TONU (01.10.2026 incelemesi): pazar sayısında olağandışı
# bölümü basılmıyor; haber tonu olayı `notlar` kovasında olduğu için ölçüt 25
# onu sayfada arar — bölüm onu basmazsa site o pazar donar. Gerçek bir biçim 3
# pazar sayısı yokken yapısal kilit: hafta hareketi bölümü haber tonunu basar.
_bg = (_SITE / "src/components/BultenGovde.astro").read_text(encoding="utf-8")
_hh = _bg[_bg.find('id="hafta-hareket"'):]
_hh = _hh[:_hh.find("</section>")]
sina("pazar düzeni haber tonunu basar (ölçüt 25'in aradığı olay)", "haberTonu.map" in _hh)


print(f"\n{'═' * 70}")
print(f"  {len(GECTI)} geçti · {len(DUSTU)} düştü")
if DUSTU:
    for d in DUSTU:
        print(f"  ✗ {d}")
    sys.exit(1)
print("  Sayfa sınavının duman sınaması temiz.")
