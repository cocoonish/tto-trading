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


print(f"\n{'═' * 70}")
print(f"  {len(GECTI)} geçti · {len(DUSTU)} düştü")
if DUSTU:
    for d in DUSTU:
        print(f"  ✗ {d}")
    sys.exit(1)
print("  Sayfa sınavının duman sınaması temiz.")
