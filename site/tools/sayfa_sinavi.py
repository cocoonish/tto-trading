#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sayfa ↔ hat sözleşmesi sınavı (CI'da koşturulabilir).

Bu sınav, "hat koştu ama sayfa yalan söylüyor" sınıfı hataları yakalar. Dokuz
bölüm var; her biri düzenin bir kuralına karşılık gelir:

  (1) <Deger> anahtarları — MDX'te çağrılan her anahtar ozet.json'da var mı?
      Yoksa sayfada STATİK yedek görünür ve veri tazelendikçe donar.
  (2) ÇIPLAK OYNAK SAYI — ozet.json'daki oynak bir değerin Türkçe biçimi,
      MDX'te <Deger> ile sarılmadan düz metin olarak geçiyor mu? (CLAUDE.md
      kural 5'in ihlali: bir sonraki tazelemede o cümle donar.) Ölçüt bir
      ÇAKIŞMA aramasıdır, yani tesadüf üretir; hassasiyeti üç kuralla korunur:
      uydurma sayılarla kurulmuş kutular `sinav-ornek` bloğuyla tarama dışıdır,
      TAM SAYI (sayım) yalnız kendi yazımıyla aranır ve bulgusu uyarıdır,
      eksi işareti sayının parçası sayılır. Üçü de sentetik örneklerle
      sınanıyor: site/tools/duman_sinav.py.
  (3) Şekil yüksekliği — MDX'teki yukseklik={} değeri, üretimin
      cikti/yukseklikler.json'daki gerçek script height'i ile aynı mı?
  (4) Dosya kümesi — üretimdeki figürler siteye birebir kopyalanmış mı ve
      hepsinde ev stili bloğu var mı?
  (5) Panel düzeni — paneller ALT ALTA mı? (yan yana panel yasak)
  (6) KaTeX — her formül ayrıştırılabiliyor mu? (rehype-katex düşmez, ham basar)
  (7) <Deger> anahtarları analiz/araştırma sayfalarında — BİLGİ. Karar
      08.09.2026: yalnız panolar canlıdır; analiz ve ders yazıları yayım
      günündeki metindir ve <Deger> etiketleri yedek metniyle sabit kalır.
      Eksik anahtar orada okuru etkilemez, yalnız sayılır (bilgi satırı);
      bilinmeyen proje niteliği hâlâ engeldir (yazım hatası).
  (8) DERLENMİŞ ÇIKTI — dist/ içinde KaTeX hatası, ham <Deger> etiketi ya
      da çözülmemiş MDX yorumu var mı? Kaynağı sınayan ölçütlerin
      göremediği tek şey: okurun gerçekte gördüğü sayfa.
  (9) OKUR DİLİ — kod ve yapım dili (ortak/okur_dili.py).
  (10) ANALİZ BİÇİMİ — analiz/YAZIM.md'nin araçtaki karşılığı
      (site/tools/analiz_sinavi.py): tarihli slug ve başlık, zorunlu ön
      bilgi, yönetici özeti, kapanış bölümü.
  (11) MANŞET KAPSAMI — her proje sayfasının HAT_MANSET girdisi var mı ve
      anahtarı ozet.json'da mı? (eksik pano tablodan sessizce düşerdi)
  (11b) PROJE BAŞLIĞI — cümle düzeni; '&' engel, Başlık Düzeni uyarı.
  (11c) PROJE BAĞLANTI METNİ — gövdedeki /projeler/ bağları başlığı cümle düzeninde taşır; slug metin olmaz (uyarı).
  (11d) PROJE ÖN BİLGİSİ — kaynak/guncelleme yok → ENGEL; description'da elle sayı, guncelleme büyük harf/şekil no, kaynak '&'/grup kodu, tags büyük harf (uyarı).
  (2c) KOŞU KUTUSU — `sayi=` ya da slotta elle uyarı özeti yok (dosyadan basılır).
  (12) ÖZET SAATİ — her ozet.json'un `_tarih`i çözülüyor, yarından ileri
      değil ve canlı bacakların en yenisinden geride kalmamış.
  (13) BİÇİM TEK KAYNAK (uyarı) — lib/bicim.ts dışında yerel biçimleyici.
  (14) CSS JETONU — kullanılan her var(--x) global.css'te ya da dosyada tanımlı.
  (15) SİMGE SÖZLEŞMESİ — ilan edilen her simge var ve boyutu ilanla aynı.
  (16) YAYIN TAKVİMİ — hakkında sayfasının saatleri iş akışı cron'larıyla aynı.
  (17) KOŞU KAYDI OKUR DİLİ — public/projeler/*/uyarilar.json `uyarilar` ve
      ozet.json'un CÜMLE olan her metin alanı okura OLDUĞU GİBİ basılır
      (ortak/okur_dili.kosu_kaydi_tara): kod dili ve yapım dili (backtick, dosya
      adı, bie_ kodu, komut anahtarı — şablon kusuru) ENGEL; snake_case anahtar
      adı ve biçim sızıntısı (veri kaynaklı olabilir) UYARI.
  (18) ŞEKİL SAAT DEFTERİ — bir hattın figürleri farklı ritimlerdeyse
      GrafikEmbed'in varsayılan damgası (hattın tek ana saati) yalan söyler.
      `_sekil_tarih` sözlüğü açan hatta: çözülemeyen ya da yarından ileri
      tarih ENGEL, defterde girdisi olmayan gömülü figür UYARI.
  (18b) AÇIK ŞEKİL TARİHİ — MDX'teki `tarihAnahtari` gerçekten çözülüyor mu:
      anahtar yok/dizge değil ya da içinde hiç tarih yok → UYARI, tarih
      yarından ileri → ENGEL. Birleşik damga ("aylık … · haftalık …") geçerli
      sayılır; içindeki her tarih ayrıca sınanır.
  (18c) ÇİFT İLAN ÇELİŞMEZ — bir figürün hem açık anahtarı hem defter girdisi
      varsa ikisi aynı günü söylemeli; ayrışırsa şeklin kendi alt başlığı ile
      sayfadaki damga farklı tarih söyler → ENGEL.
  (19) ŞEKİL METNİNDE OKUR DİLİ — gömülü Plotly başlık/alt yazı/lejant metni de
      okura basılır ve 9 · 9b · 17 ölçütlerinin hiçbiri oraya bakmıyordu.
      Yapım dili ENGEL (taban sıfır), kod dili tek satırda toplanan UYARI
      (taban yetmiş altı), anahtar adı ve biçim yalnız sayılır.
  (9b) OKUR DİLİ, derlenmiş çıktıda (uyarı) — bileşen dizgeleri de kapıya girer.
  (20) ÖLÜ İÇ BAĞ — dist/ içindeki her `href="/…"` bir dosyaya, sayfaya ya da
      varlığa çözülmeli. Silinen bir sayfaya bağlanan başka bir sayfa hiçbir
      yerde hata vermez; bağı kuran çoğu zaman bir bileşendir ve kaynakta
      adres diye geçmez, o yüzden ölçüt kaynağa değil ÇIKTIYA bakar.
  (21) X İZİ — derlenmiş çıktıda x.com/twitter.com adresi ve "X gönderisi"
      yazısı YOK (kullanıcı kararı: site gönderiyi okura göstermez, hesap
      hiçbir yere yazılmaz). twitter:card meta'sı ve Türkçe "paylaşım"
      sözcüğü taranmaz — ilki hesap adı taşımaz, ikincisi bir araştırma
      yazısında iktisadi anlamıyla geçer.
  (22) KAÇAN ETİKET — yazı katmanının metin alanları HTML taşır; `set:html`
      yerine metin olarak basılan bir alan okura "<p>" yazısını gösterir.
      dist'te kaçmış etiket ENGEL; `<code>`/`<pre>` içi muaf (bir ders HTML
      anlatıyorsa etiket göstermesi gerekir).
  (24) SABİT KAP — derlenmiş çıktıda analiz ve ders sayfalarının gövdesi
      `data-deger="sabit"` kabındadır (Deger betiği dokunmaz, canlı işareti
      basılmaz); kap yoksa ENGEL. Proje sayfasında kap OLMAMALI (pano
      canlıdır) — varsa ENGEL. Ölçüt dist/ varsa koşar; yoksa koşmadığını
      söyler.
  (25) OLAY OKURA ULAŞTI MI — bülten ölçüm katmanının ürettiği her
      `onemli`/`dikkat` olayın CÜMLESİ derlenmiş sayı sayfasında görünmeli.
      Ölçüt kaynağa değil ÇIKTIYA bakar, çünkü olayı basan da süzen de bir
      BİLEŞENDİR: 07.09.2026'da eklenen tekilleştirme süzgeci `notlar`
      kovasını "yukarıda basılıyor" varsayarak hat hat listesinden atıyordu,
      oysa o kovanın sayfada bölümü hiç olmamıştı. Ölçüldü (10.09.2026,
      derlenmiş 17 sayı): 108 dikkat olayının 108'i okura ulaşmıyor, 37
      önemli olayın 37'si ulaşıyor — kaynak da veri de doğruydu, kusur yalnız
      çıktıda görünüyordu. Bulunamayan olay ENGEL.
  (23) SOLUK METİN — `color: var(--ink-30)` ENGEL. Kontrast 1,90:1 ve
      global.css'in kendi yorumu "yalnız çizgi ve kenarlıkta" diyor; metin
      için en soluk kabul edilen jeton --ink-60 (4,59:1).
      `text-decoration-color` kapsam dışı (alt çizgi, metin değil).

Koşum:  python3 site/tools/sayfa_sinavi.py
Çıkış:  0 = geçti · 1 = en az bir sınav düştü
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys
import urllib.parse
from html import unescape

KOK = pathlib.Path(__file__).resolve().parents[2]

# (sayfa slug'ı, proje klasörü)
# HAT LİSTESİ ELLE TUTULMAZ, guncelle.py'nin kendi kütüğünden TÜRETİLİR.
# Elle tutulan liste altı hat taşıyordu ve sınav geri kalanını hiç görmüyordu:
# hazine-ihrac sayfasında <Deger> ile çağrılan on altı anahtar ozet.json'da
# YOKTU, yani noktalı çizgiyle "canlı" görünen o sayılar aylardır statik
# yedeklerinde donmuştu — ve sınav bunu bulmak için yazılmış olmasına rağmen
# o sayfaya hiç bakmıyordu. Yeni bir hat eklendiğinde de aynı boşluk
# tekrarlanırdı. Kaynak tek: hattın kendisi.
def _hatlar() -> list[tuple[str, str]]:
    # Modül sys.path'ten NORMAL import edilir. spec_from_file_location ile
    # yüklemek dataclass çözümlemesini kırıyor: dataclasses tip adlarını
    # sys.modules[cls.__module__] üzerinden arıyor ve sentetik adla yüklenen
    # modül orada olmadığı için AttributeError veriyor.
    import sys
    if str(KOK) not in sys.path:
        sys.path.insert(0, str(KOK))
    import guncelle
    return [(h.slug, h.klasor) for h in guncelle.HATLAR]


HATLAR = _hatlar()

# KURAL 1 (anahtar varlığı) HER hatta koşar: ölçütü tek ve kesin — sayfada
# çağrılan anahtar ozet.json'da ya vardır ya yoktur, yorum payı sıfırdır.
#
# Kural 2–5 yalnız aşağıdaki hatlarda DÜŞÜRÜR. Sebebi dürüstçe şu: bu ölçütler
# o altı hattın çıktı düzenine göre yazıldı ve liste genişletilince altı hatta
# birden YANLIŞ ALARM verdiler (ör. dosya kümesi ölçütü, çıktısını farklı adla
# kopyalayan hatlarda hepsini "farklı" sayıyor). Yanlış alarmla düşen bir
# denetim, kapatılan bir denetimdir. Ölçütler o hatlar için de düzeltilene
# kadar orada BİLGİ olarak basılır, kapı olmaz.
TAM_SINAV = {"kredi-parasal", "fonlama-likidite", "enflasyon",
             "odemeler-dengesi", "butce-borc", "dibs-verim-egrisi"}

# (2) için: yalnız GERÇEKTEN oynak sayılar taranır. Tarih/oran metinleri, tek
# haneli sayımlar ve yöntemsel sabitler taramaya girmez — yoksa "13 haftalık"
# gibi metodolojik ifadeler yanlış alarm üretir.
TARAMA_ALT_SINIR = 2.0        # |v| bu değerin altındaysa taranmaz
TARAMA_ONDALIK = (1, 2)       # kaç ondalıkla yazılmış olabileceği


def tr(v: float, ondalik: int) -> str:
    m = f"{v:,.{ondalik}f}"
    return (m.replace(",", " ").replace(".", ",").replace(" ", ".")
             .replace("-", "−"))


# ÖRNEK BLOĞU. Bir kutunun İÇİNDEKİ bütün sayılar uydurmaysa (formülün nasıl
# işlediğini göstermek için seçilmiş varsayımlar), o kutu tarama dışıdır:
#     {/* sinav-ornek: uydurma yuvarlak sayılarla aritmetik örneği */}
#     … kutu …
#     {/* /sinav-ornek */}
# Anahtar bazlı `sinav-muaf` bu iş için YANLIŞ ARAÇTI ve bu iki kez ölçüldü.
# Aynı kutu 2026-09-02'de ikinci kez çarpıştı: ilkinde forward_1y1y örnek
# kutusunun 40,03'üyle, ikincisinde kimlik_cok_kaynakli kutunun 51,00 TL
# varsayımıyla — ve ikinci çarpışma yayını 12 saat durdurdu. Anahtar muafiyeti
# çarpışan anahtarı SAYFANIN TAMAMINDA kör eder (yani gerçek bir donmuş sayıyı
# da kaçırır) ve bir sonraki tesadüf için hiçbir şey yapmaz; kutuyu işaretlemek
# ise sebebin kendisini adlandırır: oradaki sayılar veri değil, VARSAYIM.
ORNEK_BLOK = re.compile(
    r"\{/\*\s*sinav-ornek:[\s\S]*?\*/\}[\s\S]*?\{/\*\s*/sinav-ornek\s*\*/\}")
ORNEK_AC = re.compile(r"\{/\*\s*sinav-ornek:")
ORNEK_KAPA = re.compile(r"\{/\*\s*/sinav-ornek\s*\*/\}")


def deger_disi(mdx: str) -> str:
    """MDX'ten <Deger …>…</Deger> bloklarını, örnek bloklarını, kod bloklarını
    ve satır içi kodu çıkar — geriye kalan, gerçekten çıplak duran metindir."""
    s = ORNEK_BLOK.sub(" ", mdx)
    s = re.sub(r"<Deger\b[\s\S]*?</Deger>", " ", s)
    s = re.sub(r"```[\s\S]*?```", " ", s)
    s = re.sub(r"`[^`]*`", " ", s)
    s = re.sub(r"\$\$[\s\S]*?\$\$", " ", s)      # KaTeX blokları
    s = re.sub(r"\$[^$\n]*\$", " ", s)           # satır içi KaTeX
    return s


# Bir sayı gerçekten TARİHSEL SABİT olabilir (başka bir kurumun yayımladığı,
# değişmeyecek bir alıntı). O zaman muafiyet, sayının yanına MDX'in kendi
# içinde yazılır ki gerekçe sayıdan ayrı düşmesin:
#     {/* sinav-muaf: agirlik_kayma_09 — TCMB Blog alıntısı, tarihsel sabit */}
MUAF_KALIP = re.compile(r"\{/\*\s*sinav-muaf:\s*([A-Za-z0-9_]+)")


def sekil_saat_bulgulari(slug: str, ozet: dict, mdx: str, sinir):
    """(18) Şekil saat defteri: (ENGEL listesi, UYARI listesi, figür sayısı).

    Bir hattın figürleri farklı ritimlerde olabilir; GrafikEmbed'in varsayılan
    damgası ise hattın TEK ana saati. `_sekil_tarih` sözlüğü bu boşluğu kapatır
    ve bu ölçüt onu sınar. Modül düzeyinde durmasının sebebi sınanabilir olması
    (site/tools/duman_sinav.py).

    · defterdeki tarih çözülemiyor ya da YARINDAN İLERİ → ENGEL (ölçülmemiş bir
      günü ilan etmek, sıfır yazmakla aynı sınıftan bir uydurmadır),
    · gömülü bir figürün defterde girdisi yok → UYARI (hattın ana saatiyle
      damgalanır; yeni bir figür bunu unutabilir ve yayını durdurmak orantısız),
    · girdi VAR ama değeri None → geçerli: "ucu ölçülmedi", sayfa tarih basmaz.
    """
    import sys as _s
    import pathlib as _p
    _s.path.insert(0, str(_p.Path(__file__).resolve().parents[2] / "ortak"))
    import bicim as _b
    hata_, uyari_ = [], []
    defter = ozet.get("_sekil_tarih") or {}
    for ad, deger in sorted(defter.items()):
        if deger is None:
            continue
        g = _b.tarihe_cevir(str(deger))
        if g is None:
            hata_.append(f"{slug}: şekil saat defterinde çözülemeyen tarih "
                         f"({ad} = {deger!r})")
        elif g > sinir:
            hata_.append(f"{slug}: şekil saati ERTESİ İŞ GÜNÜNDEN İLERİ "
                         f"({ad} = {deger}) — ölçülmemiş bir gün ilan edilemez")
    gomulu = set(re.findall(rf'/projeler/{re.escape(slug)}/([^"\s]+\.html)', mdx))
    eksik = sorted(gomulu - set(defter))
    if eksik:
        uyari_.append(f"{slug}: şekil saat defterinde girdisi olmayan figür "
                      f"({len(eksik)}): {', '.join(eksik[:4])}"
                      + (" …" if len(eksik) > 4 else "")
                      + " — hattın ana saatiyle damgalanıyor")
    return hata_, uyari_, len(gomulu)


# GG.AA.YYYY · YYYY-AA-GG · AA.YYYY — ortak/bicim.tarihe_cevir'in çözdüğü
# yazımlar. Birleşik bir damgada ("aylık 30.06.2026 · haftalık 26.08.2026")
# tarihleri BULMAK için gerekir; çözmek için değil, çözümü bicim yapar.
TARIH_IZI = re.compile(r"\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2}|(?<!\d\.)\b\d{2}\.\d{4}\b")


def acik_saat_bulgulari(nerede: str, ozet: dict, anahtar: str, defter_deger,
                        defter_var: bool, sinir, coz):
    """(18b/18c) MDX'teki `tarihAnahtari` ↔ ozet.json — (ENGEL, UYARI).

    GrafikEmbed sırası: açık anahtar → şekil saat defteri → hattın ana saati.
    Bu ölçüt ilk basamağı sınar ve ilk ikisinin ÇELİŞMEDİĞİNİ de sorar.

    Dört durum, okura ULAŞAN sonuca göre ağırlıklandırılır:

    · anahtar yok ya da dizge değil → UYARI. Bileşen anahtarı ancak DİZGE ise
      kullanır; yoksa sessizce bir alt basamağa düşer, yani yazar bir saat
      İLAN ETMİŞTİR ama sayfa başkasını basar ve ikisi de yeşil görünür.
    · dizge ve TEK bir tarih → yarından ileriyse ENGEL: ölçülmemiş bir günü
      ilan etmek, sıfır yazmakla aynı sınıftan bir uydurmadır.
    · dizge, tek tarih değil ama İÇİNDE tarih(ler) var → BİRLEŞİK DAMGA, geçerli.
      Bileşen tanımadığı dizgeyi olduğu gibi basar (bicim.tarihYaz) ve bazı
      figürler tek bir uçla dürüst anlatılamaz: ödemeler dengesi Şekil 12'nin
      panelleri 57 gün arayla biter, hangi bacak seçilse öbürü hakkında yalan
      olur. Böyle bir damgada tarihlerin HER BİRİ ayrıca sınanır (biri bile
      yarından ileriyse ENGEL) ama dizgenin kendisi kusur sayılmaz — yoksa bu
      ölçüt yayının önünde duran bir YANLIŞ ALARM olurdu.
    · dizge ama içinde hiç tarih yok → UYARI: sayfa şeklin altına tarih diye
      tarih olmayan bir şey basar.

    Ve (18c): aynı figür için hem açık anahtar hem defter girdisi varsa ikisi
    AYNI günü söylemeli. Birlikte durmaları bir güvenlik payıdır — defter bir
    gün yazılmazsa sayfa yine doğru günü basar — ama ayrıştıkları gün figürün
    KENDİ alt başlığı (defterden) ile sayfadaki damga (anahtardan) iki farklı
    tarih söyler ve sayfa kendi kendisiyle çelişir. Dolarizasyon şeklinde tam
    olarak bu olmuştu; tek fark iki ilandan birinin hattın ana saati olmasıydı.
    """
    hata_, uyari_ = [], []
    v = ozet.get(anahtar)
    if not isinstance(v, str) or not v.strip():
        uyari_.append(f"{nerede}: anahtar ozet.json'da yok ya da dizge değil "
                      f"({v!r}) — damga sessizce bir alt basamağa düşüyor")
        return hata_, uyari_
    tek = coz(v)
    parcalar = [] if tek else [coz(m.group(0)) for m in TARIH_IZI.finditer(v)]
    gunler = [tek] if tek else [g for g in parcalar if g]
    if not gunler:
        uyari_.append(f"{nerede}: değer tarih değil ({v!r}) — şeklin altına "
                      "olduğu gibi basılır")
        return hata_, uyari_
    for g in gunler:
        if g > sinir:
            hata_.append(f"{nerede}: şekil tarihi ERTESİ İŞ GÜNÜNDEN İLERİ ({v})"
                         " — ölçülmemiş bir gün ilan edilemez")
            break
    if defter_var and isinstance(defter_deger, str):
        d = coz(defter_deger)
        if d is not None and tek is not None and d != tek:
            hata_.append(f"{nerede}: ÇELİŞKİ — şekil saat defteri {defter_deger}, "
                         f"açık anahtar {v}; figürün kendi alt başlığı ile "
                         "sayfadaki damga farklı gün söyler")
    return hata_, uyari_


# Plotly HTML'inde okura GÖRÜNEN metin alanları. Figürün başlığı, alt yazısı,
# lejant adı ve hover şablonu sayfada okunur; veri dizileri okunmaz.
SEKIL_METIN = re.compile(r'"(?:text|title|name|hovertemplate)":"((?:[^"\\]|\\.){4,8000})"')
SEKIL_ETIKET = re.compile(r"<[^>]{1,40}>")


def sekil_metinleri(ham: str) -> list[str]:
    """Gömülü bir Plotly HTML'inden okura görünen metinleri çıkarır.

    JSON kaçışları (birim kod, açılı ayraç, bölü, tırnak) çözülür ve HTML
    etiketleri boşluğa indirilir — okurun gördüğü düz metin kalsın.
    """
    cikti = []
    for m in SEKIL_METIN.finditer(ham):
        t = m.group(1)
        t = re.sub(r"\\u([0-9a-fA-F]{4})", lambda x: chr(int(x.group(1), 16)), t)
        t = t.replace("\\u003c", "<").replace("\\/", "/").replace('\\"', '"')
        t = SEKIL_ETIKET.sub(" ", t)
        if len(t) > 8:
            cikti.append(t)
    return cikti


def sekil_okur_dili(metinler, nerede: str):
    """(19) Figür metninde okur dili: (ENGEL, UYARI, aile→sayım).

    NEDEN VAR. Okur dili ölçütleri MDX'i (9), derlenmiş sayfayı (9b) ve koşu
    kaydını (17) tarıyordu; gömülü Plotly HTML'inin BAŞLIK ve ALT YAZI metnini
    hiçbiri taramıyordu. Oysa o metin sayfada, şeklin tam üstünde, okurun
    gözünün ilk gittiği yerde duruyor. Ölçüldü (03.09.2026): 164 figürde 36
    ayrı kod/yapım dili sızıntısı vardı ve HEPSİ her yeşil koşudan geçmişti —
    aralarında bir figürün okura kendi sürüm tarihçemizi anlatan alt yazısı da
    ("bu halka yazının ilk sürümünde ölçülmemişti"). "Bir denetimin KAPSAMI
    denetimin parçasıdır"; bakılmayan yer, geçen sınavla aynı görünür.

    AĞIRLIK, okura ULAŞAN kusura ve BUGÜNKÜ tabana göre:
    · yapım dili → ENGEL. Sürüm tarihçesini okura anlatmanın savunulabilir bir
      hâli yok ve bugün taban SIFIR: tek bulgu düzeltildi, yani bu kapı ancak
      YENİ bir sızıntıda düşer.
    · kod dili → UYARI. Taban bugün sıfır DEĞİL (yetmiş altı bulgu, otuz altı
      ayrı kod, on beş figürde). Bunları ENGEL yapmak yayını MEVCUT kusurla
      durdururdu ve yanlış alarmla düşen bir denetim, kapatılan bir denetimdir.
      Üstelik `bie_` bir tartışma taşıyor: CLAUDE.md kaynağın BÜYÜK harfli
      alan adlarını (`TP.PY.P06.ON`) kaynak künyesi sayıp muaf tutuyor ve EVDS
      grup kodu da bir künye olabilir. Karar verilene kadar sayılır ve görünür
      durur. Çağıran taraf bunları TEK bir uyarı satırında topluyor: yetmiş
      altı satır, kırk üç satırlık uyarı listesini okunmaz hâle getirirdi ve
      kimsenin bakmadığı bir kayıt, olmayan kayıtla aynıdır.
    · anahtar adı ve biçim → yalnız SAYILIR, satır satır basılmaz: biçim
      ailesi tek başına 218 bulgu veriyor (eksen etiketlerindeki ondalık
      nokta) ve her birini uyarı diye basmak, kimsenin bakmadığı bir kayıt
      üretirdi. Sayı görünür, gürültü görünmez.
    """
    # Kalıp listesi burada DEĞİL: aynı kural MDX'te, koşu kaydında, bültende
    # ve tweette de uygulanıyor ve tek tanım ortak/okur_dili.py'de duruyor.
    import sys as _s3
    import pathlib as _p3
    _s3.path.insert(0, str(_p3.Path(__file__).resolve().parents[2] / "ortak"))
    import okur_dili as _od
    hata_, uyari_, sayim = [], [], {}
    gorulen = set()
    for metin in metinler:
        for _i, aile, esl in _od.kosu_kaydi_tara([metin]):
            sayim[aile] = sayim.get(aile, 0) + 1
            if (aile, esl) in gorulen:
                continue
            gorulen.add((aile, esl))
            if aile == "yapım dili":
                hata_.append(f"şekil metni yapım dili — {nerede}: {esl!r}")
            elif aile == "kod dili":
                uyari_.append(f"şekil metni kod dili — {nerede}: {esl!r}")
    return hata_, uyari_, sayim


def ciplak_sayilar(disi: str, ozet: dict, muaf: set[str]) -> tuple[list[str], list[str]]:
    """(2) Çıplak oynak sayı: (ENGEL listesi, UYARI listesi).

    `disi` = deger_disi(mdx), yani <Deger>, örnek bloğu, kod ve KaTeX çıkarılmış
    metin. Modül düzeyinde durmasının sebebi sınanabilir olması: bu ölçüt bir
    kez yanlış alarm verdiğinde yayın 12 saat durdu, yani hassasiyeti kodun
    kendisi kadar önemli (bkz. site/tools/duman_sinav.py).

    İKİ AĞIRLIK — TAM SAYI ile ONDALIKLI ÖLÇÜ aynı şey değil. JSON'da 51 yazan
    bir değer bir SAYIMDIR (kaç gözlem, kaç kaynak, kaç gün eşik) ve sayfada
    "51" diye geçer, "51,00" diye değil; ama tarama ikisini de deniyordu.
    kimlik_cok_kaynakli 52'den 51'e düştüğü gün "51,00" bir aritmetik örneğinin
    FİYAT varsayımıyla çarpıştı ve yayın durdu. Tam sayı artık yalnız kendi
    yazımıyla aranır ve bulgusu KAPI DEĞİL uyarıdır: sayımların çoğu yöntemsel
    sabittir (250 iş günlük pencere, 100 günlük tolerans) ve metinde yazılması
    DOĞRUDUR — ölçüldü, kapı yapmak iki sayfada birden yanlış alarm veriyor.
    """
    ciplak: list[str] = []          # ondalıklı ölçü → kapı
    sayim: list[str] = []           # tam sayı sayım → yalnız uyarı
    for k, v in ozet.items():
        if k in muaf:
            continue
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            continue
        if abs(v) < TARAMA_ALT_SINIR:
            continue
        tam = isinstance(v, int)
        for d in ((0,) if tam else TARAMA_ONDALIK):
            metin = tr(float(v), d)
            if len(metin.replace(".", "").replace(",", "")) < 3:
                continue              # iki haneli sayılar çok yaygın, taranmaz
            # İŞARET DE SAYININ PARÇASI. Eksiyi dışlamayan bir arama, metindeki
            # "−22,1"i pozitif 22,1 değeriyle eşleştirir; tl-tasima'nın tarihsel
            # listesi bu yüzden çarpışıyordu. tr() eksiyi U+2212 ile yazar,
            # kaynak metinde ASCII "-" de geçebilir.
            # SAĞ SINIR: amaç "136,89" içindeki "36,8"i saymamak, cümle sonu
            # noktasını da saymamak DEĞİL. Eski kalıp ayrım yapmıyordu ve
            # "bugün 36,79." gibi CÜMLE SONUNDAKİ her çıplak sayıyı kaçırıyordu
            # — yani ölçütün asıl işi olan sınıfı. Ayraç ancak ardından RAKAM
            # geliyorsa sayının parçasıdır.
            if re.search(r"(?<![\d.,\-\u2212])" + re.escape(metin)
                         + r"(?!\d)(?![.,]\d)", disi):
                (sayim if tam else ciplak).append(f"{k}={metin}")
                break
    return ciplak, sayim


IC_BAG = re.compile(r'\bhref="(/[^"#?]*)(?:[#?][^"]*)?"')


def olu_ic_baglar(dist: pathlib.Path) -> dict[str, list[str]]:
    """Derlenmiş çıktıdaki HEDEFSİZ iç bağlar: adres → onu basan sayfalar.

    NEDEN VAR. Bültenin kaynak notu hattın slug'ını doğrudan
    `/projeler/<slug>/` adresine çeviriyordu; bu, HER HATTIN BİR PANOSU
    OLDUĞUNU varsayar. Varsayım tuttuğu sürece görünmez, tutmadığı gün
    okura 404 verir ve koşu YEŞİL biter — bir sayfanın silinmesi, ona
    bağlanan başka bir sayfayı hiçbir yerde hata vermeden bozar.

    Ölçüt kaynağa değil ÇIKTIYA bakar, çünkü kırık bağların çoğu elle
    yazılmaz: bir bileşen onu slug'dan kurar ve kaynakta `/projeler/` diye
    bile geçmez.

    Hedef üç biçimde var sayılır: dosyanın kendisi (varlıklar — ozet.json,
    rss.xml, og kartı), `<yol>/index.html` (sayfa) ve `<yol>.html`.
    Dış adresler, çapa (#) ve sorgu (?) taranmaz; ikisi de dosya sistemine
    değil sayfanın kendi içine bakar.
    """
    kirik: dict[str, list[str]] = {}
    for h in sorted(dist.rglob("*.html")):
        for m in IC_BAG.finditer(h.read_text(encoding="utf-8", errors="ignore")):
            yol = urllib.parse.unquote(m.group(1))
            p = dist / yol.lstrip("/")
            if p.is_file() or (p / "index.html").is_file() or p.with_suffix(p.suffix + ".html").is_file():
                continue
            kirik.setdefault(yol, []).append(h.relative_to(dist).as_posix())
    return kirik


X_BAG = re.compile(r'https?://(?:www\.)?(?:x|twitter)\.com/[^"\'\s<)]*')
# Türkçe harf sınıfı: SOL SINIR bu ölçütün hassasiyetidir. Sınırsız yazılırsa
# "VIX'te", "TÜFEX'te", "FX'te", "MDX'te" eşleşir ve yayın durur.
_HARF = "A-Za-zÇĞİÖŞÜçğıöşü"
# LOKATİF ŞART ("X'te/X'de" = platformDA) bilerek: bir istatistik yazısında
# "Y'den X'e çıkarım" geçiyor ve orada X bir DEĞİŞKEN. Yönelme hâli dışarıda
# kalmasaydı o cümle yayını durdururdu — ve bugün yalnız MDX'in kıvrık
# kesme işareti sayesinde kurtuluyordu, yani tesadüfen.
X_YAZI = re.compile(
    rf"X gönderi"
    rf"|(?<![{_HARF}])X['’]?(?:te|de)\s+(?:de\s+)?(?:özetiyle\s+)?(?:çıkar|paylaş)"
    rf"|(?<![{_HARF}])X hesab|Twitter hesab|Twitter['’]d[ae]"
    rf"|(?<![{_HARF}])X['’][td][ae]n\s+paylaş")


def x_izleri(dist: pathlib.Path) -> dict[str, list[str]]:
    """Derlenmiş çıktıda X/Twitter izi: bulgu → onu basan sayfalar.

    KULLANICI KARARI (07.09.2026): "Paylaşım · X gönderisi" satırı sitenin
    hiçbir yerinde olmayacak, Twitter hesabı da hiçbir yere yazılmayacak.
    Tweet atılmaya devam ediyor; kaldırılan, sitenin okura gönderiyi
    GÖSTERMESİ. Kararın kendisi bir tercihtir, ama kalıcılığı bir ÖLÇÜ ister:
    bağı kuran şey bir bileşendi (künye satırı) ve kaynakta "x.com" diye
    aranarak bulunamayan biçimlerde geri gelebilir.

    İki aile ayrı ayrı sorulur, çünkü biri öbürü olmadan da dönebilir:
      · BAĞ — x.com / twitter.com adresi (künye bağı, JSON-LD sameAs, bir
        yazının kaynakçası),
      · YAZI — "X gönderisi" etiketi ve "X'te de özetiyle çıkar" cümlesi.

    <meta name="twitter:card|title|description|image"> KUSUR DEĞİL: bağlantı
    önizleme künyesidir, hiçbir hesap adı taşımaz ve adresi de yoktur.
    Türkçe "paylaşım" sözcüğü de taranmaz — bir araştırma yazısında iktisadi
    anlamıyla geçiyor (turkiye-piyasa-tarihi), ölçüt onu kusur sayamaz.
    """
    bulgu: dict[str, list[str]] = {}
    for h in sorted(list(dist.rglob("*.html")) + list(dist.rglob("*.xml"))):
        metin = h.read_text(encoding="utf-8", errors="ignore")
        sayfa = h.relative_to(dist).as_posix()
        for kalip in (X_BAG, X_YAZI):
            for m in kalip.finditer(metin):
                bulgu.setdefault(m.group(0), []).append(sayfa)
    return bulgu


KACAN_ETIKET = re.compile(
    r"&lt;/?(?:p|div|span|strong|em|b|i|u|s|ul|ol|li|br|hr|a|h[1-6]|table|tr|td|th|"
    r"blockquote|figure|figcaption|small|sup|sub)\b[^&]{0,60}&gt;")


def kacan_etiketler(dist: pathlib.Path) -> dict[str, list[str]]:
    """Okura ETİKET OLARAK görünen HTML: bulgu → onu basan sayfalar.

    ÖLÇÜLEN ARIZA (07.09.2026). Yazı katmanının bütün metin alanları HTML
    taşıyor ve `yorum` ile `gundem.*` `set:html` ile basılıyordu; `ozet` ise
    METİN olarak basılıyordu. Sonuç: dört bülten sayısında okur, cümlenin
    başında "<p>" yazısını gördü. Hiçbir kapı bunu sormuyordu — kaynak
    doğruydu, veri doğruydu, yalnız iki taraf farklı sözleşme konuşuyordu.

    Ölçüt genel: `set:html` unutulan HER alan bu izi bırakır, bülten olsun
    proje panosu olsun. Kaynağa değil ÇIKTIYA bakar, çünkü kaçış derleme
    anında doğar.

    KOD BLOĞU MUAF: bir ders HTML anlatıyorsa `<code>`/`<pre>` içinde etiket
    GÖSTERMESİ gerekir ve orada kaçış doğrudur. Muafiyet olmasaydı ölçüt
    bir gün yayını böyle bir yazı yüzünden durdururdu.
    """
    bulgu: dict[str, list[str]] = {}
    for h in sorted(dist.rglob("*.html")):
        metin = re.sub(r"<(code|pre|script|style)[^>]*>.*?</\1>", " ",
                       h.read_text(encoding="utf-8", errors="ignore"), flags=re.S)
        sayfa = h.relative_to(dist).parent.as_posix() or "."
        for m in KACAN_ETIKET.finditer(metin):
            bulgu.setdefault(m.group(0), []).append(sayfa)
    return bulgu


SOLUK_METIN = re.compile(r"(?<!-)\bcolor:\s*var\(--ink-30\)")


def _sade_metin(s: str) -> str:
    """Kıyasın iki tarafına da uygulanan tek süzgeç: boşluk tekleştirme."""
    return re.sub(r"\s+", " ", s).strip()


def _sayfa_metni(html: str) -> str:
    """Derlenmiş sayfayı arama için sadeleştirir: HTML kaçışları ÇÖZÜLÜR
    (`&#39;` → `'`, `&amp;` → `&`), boşluklar tekleştirilir. Kaçışları
    çözmeden aranan bir cümle sayfada dursa da bulunamaz."""
    return _sade_metin(unescape(html))


def olay_okura_ulasti(kok: Path) -> tuple[list[str], int, int]:
    """(25) OLAY OKURA ULAŞTI MI. Ölçüm katmanının `onemli`/`dikkat` diye
    işaretlediği her olayın cümlesi, o sayının DERLENMİŞ sayfasında geçmeli.

    Neden çıktıya bakıyor: olayı sayfaya basan da, "bu zaten yukarıda anıldı"
    deyip süzen de bir bileşendir; ikisi de kaynakta bir olay kovası olarak
    görünmez. 07.09.2026'da konan tekilleştirme süzgeci `notlar` kovasını
    basıldığı VARSAYIMIYLA süzüyordu ve o kovanın sayfada bölümü hiç olmadı;
    JSON doğru, bileşen sözdizimsel olarak doğru, koşu yeşil — ve okur
    ölçümlerin hiçbirini görmüyordu.

    Kıyas cümlenin ilk `ESLESME_UZUNLUK` karakterinden yapılıyor ve İKİ TARAF
    DA aynı süzgeçten geçiyor: sayfa metni HTML kaçışları çözülüp boşlukları
    tekleştirilerek okunuyor. Bu gereklilik ölçülerek görüldü — kaçış çözümü
    olmadan ölçüt beş olayı KAYIP saydı ve beşi de sayfada duruyordu; ortak
    yanları kesme işareti (`&#39;`) ve `&` (`&amp;`) taşımalarıydı ("altın
    haber-duyarlılık endeksi 1 günde +0,04'den…", "S&P 500 …"). Yayının önünde
    duran bir denetimin yanlış alarmı, ölçtüğü kusurdan pahalıdır: bu ölçüt
    yayın kapısında duruyor ve beş yanlış alarm siteyi durdururdu."""
    ESLESME_UZUNLUK = 45
    veri = kok / "site/src/data/bulten"
    dist = kok / "site/dist/bulten"
    bulgu: list[str] = []
    aranan = bulunan = 0
    for kaynak in sorted(veri.glob("*.json")):
        sayfa = dist / kaynak.stem / "index.html"
        if not sayfa.exists():
            continue
        html = _sayfa_metni(sayfa.read_text(encoding="utf-8"))
        b = json.loads(kaynak.read_text(encoding="utf-8"))
        for kova in ("one_cikanlar", "notlar"):
            for o in b.get(kova) or []:
                metin = (o.get("metin") or "").strip()
                if len(metin) < ESLESME_UZUNLUK:
                    continue
                aranan += 1
                if _sade_metin(metin)[:ESLESME_UZUNLUK] in html:
                    bulunan += 1
                else:
                    bulgu.append(
                        f"{kaynak.stem} · {kova} · {o.get('hat')}|{o.get('anahtar')} "
                        f"— ölçülen olay sayfada YOK: {metin[:70]!r}")
    return bulgu, aranan, bulunan


def sabit_kap_bulgulari(dist: Path) -> list[str]:
    """(24) SABİT KAP. Karar 08.09.2026: yalnız panolar canlıdır. Derlenmiş
    çıktıda analiz/ ve arastirma/ sayfalarında `canli-deger` alanı varsa gövde
    `data-deger="sabit"` kabında olmalı (Deger betiği dokunmaz, işaret yok);
    projeler/ sayfasında kap OLMAMALI — pano canlı kalır. Kaynağa değil ÇIKTIYA
    bakılır: kabı bileşen kurar, bir düzen değişikliği onu sessizce düşürebilir."""
    bulgu: list[str] = []
    for h in sorted(dist.rglob("index.html")):
        rel = h.relative_to(dist).as_posix()
        ust = rel.split("/")[0]
        try:
            m = h.read_text(encoding="utf-8")
        except OSError:
            continue
        kap = 'data-deger="sabit"' in m
        canli = "canli-deger" in m
        if ust in ("analiz", "arastirma") and rel.count("/") >= 1:
            if canli and not kap:
                bulgu.append(f"{rel}: canlı değer alanı var ama sabit kap yok — analiz/ders sabittir")
        elif ust == "projeler" and rel.count("/") >= 1:
            if kap:
                bulgu.append(f"{rel}: proje sayfası sabit kapta — pano canlı olmalı")
    return bulgu


def soluk_metin(kok: pathlib.Path) -> list[str]:
    """Metin rengi olarak --ink-30 kullanan yerler — deponun KENDİ kuralı.

    `global.css` jetonun yanına şunu yazmış: "--ink-30 yalnız çizgi ve
    kenarlıkta; metinde kullanılmaz." Kural doğruydu ve HİÇBİR YERDE
    DAYATILMIYORDU: ölçüldü (07.09.2026) — sekiz dosyada on beş yerde metin
    rengi olarak kullanılıyordu. Kontrast 1,90:1; WCAG AA gövde metni 4,5:1,
    büyük metin 3:1, metin dışı öğe 3:1 ister — üçünü de geçmiyor. Bültende
    σ sütunu, 52 hafta aralığı ve tema sütunu bu renkteydi, yani sayfadaki
    en yoğun sayı sütunları okunması en zor sütunlardı.

    Kuralın kendisi zaten yazılıydı; eksik olan onu soran ölçüttü. Bir kural
    yalnız yoruma yazıldığında, o yorumu okumayan bir sonraki oturum onu
    bilmeden çiğner.

    `text-decoration-color` KAPSAM DIŞI: o bir alt çizgi rengi, metnin
    kendisi değil; soluk bir alt çizgi okunabilirliği düşürmez.
    """
    bulgu = []
    for f in sorted(kok.glob("site/src/**/*")):
        if f.suffix not in (".astro", ".css") or not f.is_file():
            continue
        for i, sat in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if SOLUK_METIN.search(sat):
                bulgu.append(f"{f.relative_to(kok / 'site/src').as_posix()}:{i}")
    return bulgu


def main() -> int:
    hata: list[str] = []

    uyari: list[str] = []      # kapı değil, adıyla görünen bulgular
    def bulgu(slug: str, mesaj: str) -> None:
        """Kural 2–5 bulgusu: TAM_SINAV'daki hatta kapı, diğerlerinde bilgi."""
        if slug in TAM_SINAV:
            hata.append(mesaj)
        else:
            print(f"  (bilgi, kapı değil) {mesaj}")
    TUM_MDX = sorted((KOK / "site/src/content").rglob("*.mdx"))

    # ÖRNEK BLOĞU KAPANMIŞ MI? Kapanmayan bir açılış, sayfanın geri kalanını
    # sessizce taramadan düşürürdü — yani muafiyet, denetimin kendisinde bir
    # delik açardı. Bu yüzden dengesi ayrıca sorulur ve ENGEL üretir.
    for yol in TUM_MDX:
        m = yol.read_text(encoding="utf-8")
        ac, kapa = len(ORNEK_AC.findall(m)), len(ORNEK_KAPA.findall(m))
        if ac != kapa:
            hata.append(f"{yol.relative_to(KOK / 'site/src/content')}: "
                        f"sinav-ornek bloğu dengesiz ({ac} açılış, {kapa} kapanış) "
                        "— kapanmayan blok sayfanın kalanını taramadan düşürür")
    for slug, klasor in HATLAR:
        proje = KOK / klasor
        mp = KOK / "site/src/content/projeler" / f"{slug}.mdx"
        # ÖZET, HATTIN KLASÖRÜNDEN DEĞİL SİTEDEN OKUNUR. Sayfanın sözleşmesi
        # `site/public/projeler/<slug>/ozet.json`dur: `<Deger>` de `GrafikEmbed`
        # de çalışma anında TAM O DOSYAYI çeker; hat klasöründeki kopya bir
        # uygulama ayrıntısıdır ve her hat onu aynı yere yazmaz. Sınav klasöre
        # bakıyordu ve yiyecek-hizmetleri-marj hattını BÜTÜNÜYLE atlıyordu —
        # o hat özetini `Research/marj/output/` altına yazıyor, kökte
        # `ozet.json` yok. Atlanan hat, geçen sınavla aynı görünür: on yedi
        # figürlü bir sayfa aylarca hiçbir ölçüte girmedi ve kimse fark etmedi.
        # "Bir denetimin KAPSAMI denetimin parçasıdır"; kapsam listeden değil
        # SÖZLEŞMEDEN türetilir, o yüzden önce site kopyası, yoksa hat kopyası.
        oj = KOK / "site/public/projeler" / slug / "ozet.json"
        if not oj.exists():
            oj = proje / "ozet.json"
        if not mp.exists():
            # Proje SAYFASI olmayan hat (çıktısı analiz/araştırma yazılarında
            # gömülü): bu döngü sayfa ölçütlerini koşar, sayfa yoksa koşacak
            # ölçüt de yok. `<Deger>` ve şekil damgası ölçütleri onları başka
            # yerden, sözleşmeden türeyen kapsamla zaten görüyor.
            print(f"  – {slug}: proje sayfası yok (çıktısı yazılara gömülü), atlandı")
            continue
        if not oj.exists():
            # SAYFA VAR AMA ÖZET YOK: sayfadaki her `<Deger>` çalışma anında
            # boşa düşer ve okur statik yedeği görür — donmuş sayı. Sessizce
            # atlamak, bu hattı bir daha hiçbir ölçütün görmemesi demekti.
            uyari.append(f"{slug}: sayfası var ama yayımlanmış ozet.json'u yok "
                         "— sayfadaki canlı değerler statik yedekte donar")
            print(f"  – {slug}: ozet.json bulunamadı, atlandı")
            continue
        mdx = mp.read_text(encoding="utf-8")
        o = json.loads(oj.read_text(encoding="utf-8"))
        print(f"\n▶ {slug}")

        # (1) anahtar varlığı
        kul = re.findall(r'<Deger\s+proje="([^"]+)"\s+anahtar="([^"]+)"', mdx)
        eksik = sorted({a for p, a in kul if p == slug and a not in o})
        yanlis = sorted({p for p, _ in kul if p != slug})
        if eksik:
            hata.append(f"{slug}: ozet.json'da olmayan anahtar: {eksik}")
        if yanlis:
            hata.append(f"{slug}: yanlış proje niteliği: {yanlis}")
        print(f"  (1) <Deger>: {len(kul)} kullanım · eksik {len(eksik)} · "
              f"yanlış proje {len(yanlis)}")

        # (2) çıplak oynak sayı
        disi = deger_disi(mdx)
        muaf = set(MUAF_KALIP.findall(mdx))
        ciplak, sayim = ciplak_sayilar(disi, o, muaf)
        if ciplak:
            bulgu(slug, f"{slug}: ÇIPLAK OYNAK SAYI (kural 5): "
                        + ", ".join(sorted(set(ciplak))))
        if sayim:
            uyari.append(f"{slug}: çıplak SAYIM (kural 5, uyarı — yöntemsel "
                         f"sabit olabilir): " + ", ".join(sorted(set(sayim))))
        print(f"  (2) çıplak oynak sayı: {len(set(ciplak))}"
              + (f" · sayım {len(set(sayim))}" if sayim else "")
              + (f" · muaf: {sorted(muaf)}" if muaf else ""))

        # (2b) statik yedek ↔ canlı değer — BİLGİ (düşürmez)
        # Yedek metin JSON yüklenene kadar (ve JS kapalıyken) görünen sayıdır.
        # Veri her tazelendiğinde doğal olarak kayar, o yüzden hattı DURDURMAZ;
        # ama sapma sayısı büyürse sayfanın "ilk bakış" hâli eskimiş demektir.
        sapan_yedek = []
        for m in re.finditer(r'<Deger\s+proje="' + re.escape(slug)
                             + r'"\s+anahtar="([^"]+)"([^>]*)>([^<]*)</Deger>', mdx):
            a, nit, yedek = m.group(1), m.group(2), m.group(3).strip()
            v = o.get(a)
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                continue
            dm = re.search(r"ondalik=\{(\d+)\}", nit)
            bek = tr(float(v), int(dm.group(1)) if dm else 1)
            if "isaret=" in nit and v > 0:
                bek = "+" + bek
            if yedek != bek:
                sapan_yedek.append(f"{a}: '{yedek}' ≠ '{bek}'")
        print(f"  (2b) statik yedek sapması (bilgi): {len(set(sapan_yedek))}"
              + ("" if not sapan_yedek else "  → " + ", ".join(sorted(set(sapan_yedek))[:6])))

        # (3) şekil yüksekliği
        # BİR HATTIN FİGÜRÜ PROJE SAYFASINDA DURMAK ZORUNDA DEĞİL. İTO kanadının
        # üç figürü Enflasyon hattı tarafından üretiliyor ama analiz yazısında
        # gömülü; ölçüt yalnız projeler/<slug>.mdx'e baktığı için üçünü birden
        # "MDX'te bulunamadı" diye düşürüyordu. Aranan şey figürün hangi
        # dosyada olduğu değil, SİTEDE gömülü olduğu yerdeki yüksekliğin
        # üretimdekiyle aynı olması. Arama bu yüzden bütün içerik ağacında.
        yj = proje / "cikti/yukseklikler.json"
        if yj.exists():
            y = json.loads(yj.read_text(encoding="utf-8"))
            sapan = []
            for dosya, h in y.items():
                kalip = re.compile(r'src="/projeler/' + re.escape(slug) + "/"
                                   + re.escape(dosya)
                                   + r'"[\s\S]{0,400}?yukseklik=\{(\d+)\}')
                m = kalip.search(mdx)
                nerede = f"projeler/{slug}"
                if not m:
                    for baska in TUM_MDX:
                        m = kalip.search(baska.read_text(encoding="utf-8"))
                        if m:
                            nerede = f"{baska.parent.name}/{baska.stem}"
                            break
                if not m:
                    sapan.append(f"{dosya}: hiçbir sayfada gömülü değil")
                elif int(m.group(1)) != h:
                    sapan.append(f"{dosya}: {nerede}'de {m.group(1)} ≠ üretim {h}")
            if sapan:
                bulgu(slug, f"{slug}: yükseklik sapması → " + " · ".join(sapan))
            print(f"  (3) yükseklik: {len(y)} figür · sapma {len(sapan)}")

        # (4) dosya kümesi + ev stili
        uret = {p.name for p in (proje / "cikti").glob("*.html")}
        site = {p.name for p in (KOK / "site/public/projeler" / slug).glob("*.html")}
        if uret != site:
            bulgu(slug, f"{slug}: üretim ile site dosya kümesi farklı: "
                        f"{sorted(uret ^ site)}")
        stilsiz = [n for n in sorted(site)
                   if "tto-ev-stili" not in (KOK / "site/public/projeler" / slug / n)
                   .read_text(encoding="utf-8", errors="ignore")]
        if stilsiz:
            bulgu(slug, f"{slug}: ev stili bloğu YOK: {stilsiz}")
        print(f"  (4) dosya kümesi: üretim {len(uret)} · site {len(site)} · "
              f"ev stilsiz {len(stilsiz)}")

        # (5) panel düzeni — yan yana panel YASAK
        yanyana = []
        for n in sorted(site):
            t = (KOK / "site/public/projeler" / slug / n).read_text(
                encoding="utf-8", errors="ignore")
            sol = {round(float(a), 4) for a, _ in re.findall(
                r'"xaxis\d*":\s*\{[^{}]*?"domain":\s*\[([\d.]+),\s*([\d.]+)\]', t)}
            if len(sol) > 1:
                yanyana.append(f"{n} (sol uçlar {sorted(sol)})")
        if yanyana:
            bulgu(slug, f"{slug}: YAN YANA PANEL: " + ", ".join(yanyana))
        print(f"  (5) panel düzeni: yan yana {len(yanyana)}")

    # (6) KaTeX — FORMÜLLER AYRIŞTIRILIYOR MU?
    # rehype-katex bir formülü ayrıştıramadığında derlemeyi DÜŞÜRMEZ; hatayı
    # sayfaya kırmızı ham LaTeX olarak basar ve `npm run build` yeşil biter.
    # 31.08.2026'da `\textbf{%3,3}` yazıldı — LaTeX'te % yorum karakteri olduğu
    # için süslü parantez yutuldu ve dört formül sayfada ham metin olarak
    # yayımlandı. Kusuru derleme değil OKUR gördü. Denetim buraya kondu ki
    # sınavı koşturan herkes aynı soruyu sorsun.
    # (7) <Deger> ANAHTARLARI — ANALİZ VE ARAŞTIRMA SAYFALARINDA, BİLGİ.
    # Bir zamanlar ENGEL'di: <Deger> sözleşmesi koleksiyondan bağımsızdı ve
    # analiz sayfaları da canlı çekiyordu. KARAR (08.09.2026, kullanıcı):
    # yalnız panolar canlıdır; analiz ve ders yazıları yayımlandığı günün
    # metnidir, <Deger> etiketleri orada yedek metniyle SABİT kalır (Yazi.astro
    # kabı, ölçüt 24). Eksik bir anahtar o sayfalarda okura hiçbir şey
    # yapmaz — 08.09'da DİBS'in üç kıyas anahtarı bir analiz yazısı yüzünden
    # yayını durdurmuştu; o kapı artık burada değil, hattın kendi koşusunda
    # (guncelle.sayfa_anahtar_bulgulari) ve pano ölçütünde (1). Bilinmeyen
    # proje niteliği yazım hatasıdır ve ENGEL kalır.
    print("\n▶ Analiz/araştırma sayfalarında <Deger> anahtarları (bilgi — sayfalar sabit)")
    # Tarayıcı /projeler/<slug>/ozet.json'u çeker; sınavın bakması gereken
    # dosya da odur. Bazı hatların çalışma klasöründeki ozet.json .gitignore'da
    # (Büyüme, El Niño) — proje klasörüne bakmak onları "bilinmeyen proje"
    # sanıyordu. Önce SİTEDEKİ kopya, yoksa proje klasörü.
    ozetler: dict[str, dict] = {}
    ozet_yok: list[str] = []
    for slug, klasor in HATLAR:
        for oj in (KOK / "site/public/projeler" / slug / "ozet.json",
                   KOK / klasor / "ozet.json"):
            if oj.exists():
                try:
                    ozetler[slug] = json.loads(oj.read_text(encoding="utf-8"))
                except Exception as ex:
                    hata.append(f"{slug}: ozet.json okunamadı ({type(ex).__name__})")
                break
        else:
            ozet_yok.append(slug)
    if ozet_yok:
        print(f"  (ozet.json bulunamayan hat: {', '.join(ozet_yok)})")
    icerik = KOK / "site/src/content"
    n_sayfa = n_kul = 0
    for mdx_yol in sorted(icerik.rglob("*.mdx")):
        # projeler/ zaten kural 1'de tam kapsamla sınandı; burada geri kalanlar.
        if mdx_yol.parent.name == "projeler":
            continue
        metin = mdx_yol.read_text(encoding="utf-8")
        kul = re.findall(r'<Deger\s+proje="([^"]+)"\s+anahtar="([^"]+)"', metin)
        if not kul:
            continue
        n_sayfa += 1
        n_kul += len(kul)
        ad = f"{mdx_yol.parent.name}/{mdx_yol.stem}"
        bilinmez = sorted({pr for pr, _ in kul if pr not in ozetler})
        if [x for x in bilinmez if x not in ozet_yok]:
            hata.append(f"{ad}: bilinmeyen proje niteliği: "
                        f"{[x for x in bilinmez if x not in ozet_yok]}")
        eksik = sorted({f"{pr}.{an}" for pr, an in kul
                        if pr in ozetler and an not in ozetler[pr]})
        print(f"  {ad}: {len(kul)} kullanım (sabit) · bugünkü özette olmayan anahtar {len(eksik)}"
              + (f" · bilinmeyen proje {bilinmez}" if bilinmez else ""))
    print(f"  toplam {n_sayfa} sayfa · {n_kul} <Deger> kullanımı — hepsi yedek metniyle sabit")

    print("\n▶ KaTeX")
    # Bir KAPI, aracı eksikken yeşil geçmez: dosya adı değişse ya da node
    # bulunmasa sınav sessizce daralır ve ham LaTeX yayına çıkardı.
    kt = KOK / "site/tools/katex_sinavi.mjs"
    if not kt.exists():
        hata.append("KaTeX sınav aracı (site/tools/katex_sinavi.mjs) yok — ölçüt koşamadı")
    else:
        try:
            r = subprocess.run(["node", str(kt)], cwd=str(KOK / "site"),
                               capture_output=True, text=True)
        except FileNotFoundError:
            r = None
            hata.append("KaTeX: node bulunamadı — ölçüt koşamadı")
        if r is not None:
            cikti = [x for x in r.stdout.splitlines() if x.strip()]
            for satir in cikti[:14]:
                print("  " + satir)
            if r.returncode != 0:
                hata.append("KaTeX: formül ayrıştırılamadı (ayrıntı yukarıda)")
            elif not cikti:
                hata.append("KaTeX: araç çıktı vermedi — ölçüt koşmuş sayılmaz")

    # (8) DERLENMİŞ ÇIKTIYA BAK — OKURUN GÖRDÜĞÜ ŞEY BUDUR.
    # 6. ve 7. ölçütler kaynağı sınıyor ve ikisi de yeşil bitiyordu; sayfada
    # ise üç formül bloğu ve ARDINDAKİ 108 <Deger> etiketi ham metin olarak
    # duruyordu. Çünkü kusur ne KaTeX'te ne anahtar listesindeydi: MDX iki
    # satıra yayılan bir `$$` bloğunun delimiter'ını yanlış eşliyor ve açılan
    # span belgenin sonuna kadar uzuyor. Kaynağı ne kadar iyi sınarsak
    # sınayalım, ÇIKTIYA bakmayan bir denetim bu sınıfı göremez.
    #
    # Bu ölçüt dist/ varsa koşar (npm run build sonrası). Yoksa atlanır ve
    # bunu SÖYLER — sessizce geçmek, koşmayan bir denetimi geçmiş saymaktır.
    print("\n▶ Derlenmiş çıktı (dist/)")
    dist = KOK / "site/dist"
    if not dist.exists():
        print("  – dist/ yok (önce `npm run build`), ÖLÇÜT KOŞMADI")
    else:
        sayfa = sorted(dist.rglob("index.html"))
        kirik = []
        for h in sayfa:
            metin = h.read_text(encoding="utf-8", errors="replace")
            # Hedefi olmayan çıpa: "#kosu"ya bağ var ama sayfada id="kosu" yok.
            if 'href="#kosu"' in metin and 'id="kosu"' not in metin:
                kirik.append((h.relative_to(dist).parent.as_posix() or ".", 0, 0, 0))
                hata.append(f"dist/{h.relative_to(dist).parent.as_posix()}: '#kosu' bağının hedefi yok")
            n_kt = metin.count("katex-error")
            # Ham <Deger> etiketi: MDX bileşeni çözememiş, metne kaçmış.
            n_dg = metin.count("&lt;Deger") + metin.count("&#x3C;Deger")
            # Çözülmemiş MDX yorumu: aynı sınıf kusurun ikinci izi.
            n_yr = metin.count("sinav-muaf")
            if n_kt or n_dg or n_yr:
                kirik.append((h.relative_to(dist).parent.as_posix() or ".",
                              n_kt, n_dg, n_yr))
        for yol, a, b, c in kirik:
            hata.append(f"dist/{yol}: KaTeX hatası {a} · ham <Deger> {b} · "
                        f"çözülmemiş MDX yorumu {c} — sayfa ham metin basıyor")
        print(f"  {len(sayfa)} sayfa tarandı · kırık {len(kirik)}")

    # ---------------------------------------------------------------- (9)
    # YAPIM GÜNLÜĞÜ DİLİ. Sayfa okura yazılır, kendi yapımına değil.
    # "Bu yazının ilk sürümünde şu hata vardı", "önceki sürümde şöyle
    # yazıyordu", "kodda şu düzeltildi" gibi cümleler okurun kararını
    # değiştirmiyor; bulguyu taşıyan cümle kalır, süreç anlatısı gitmelidir.
    # Aynı sınıfa dosya/anahtar adları da girer: ozet.json, metrik.py,
    # itp_* anahtarı — okurun elinde olmayan şeylerdir.
    # ÖLÇÜT NEDEN GEREKLİ: bu dil bir kez temizlendi ve temizlik yalnız
    # hatırlandığı sürece sürer. Kural araca konmazsa bir sonraki yazıda
    # geri gelir.
    print("\n▶ Okur dili (okura değil kendine anlatan cümleler)")
    # KALIP LİSTESİ BURADA DEĞİL. Aynı kural bülten ve tweet katmanlarında da
    # uygulanıyor; üç ayrı liste bir gün sessizce ayrışırdı ve hangisinin neyi
    # gördüğü kimsenin aklında kalmazdı. Tek tanım: ortak/okur_dili.py.
    sys.path.insert(0, str(KOK / "ortak"))
    import okur_dili
    icerik = sorted((KOK / "site/src/content").rglob("*.mdx"))
    bulgu = 0
    for yol in icerik:
        for aile, esl, sat in okur_dili.tara(yol.read_text(encoding="utf-8")):
            hata.append(f"{aile} — {yol.relative_to(KOK / 'site/src/content')}"
                        f":{sat}: {esl!r}")
            bulgu += 1
    print(f"  {len(icerik)} sayfa tarandı · bulgu {bulgu}")

    # ---------------------------------------------------------------- (10)
    # ANALİZ BİÇİMİ. analiz/YAZIM.md'nin araçtaki karşılığı (analiz_sinavi.py):
    # tarihli slug ve başlık, zorunlu ön bilgi, uzun yazıda yönetici özeti,
    # kapanış bölümü. Rehber tarihinden (1 Eylül 2026) sonraki yazılarda KAPI,
    # daha eskilerde bilgi — yayımlanmış yazılar değiştirilmez.
    print("\n▶ Analiz biçimi (analiz/YAZIM.md)")
    try:
        sys.path.insert(0, str(KOK / "site" / "tools"))
        import analiz_sinavi
        if analiz_sinavi.main([]) != 0:
            hata.append("analiz biçim sınavı düştü — rehber sonrası bir yazı analiz/YAZIM.md'ye uymuyor")
    except Exception as ex:                                        # noqa: BLE001
        hata.append(f"analiz biçim sınavı koşturulamadı ({type(ex).__name__}: {ex})")

    # ---------------------------------------------------------------- (11)
    # MANŞET KAPSAMI. Ana sayfa tablosu ve proje kartları HAT_MANSET'ten
    # okur; girdisi olmayan pano tablodan SESSİZCE düşer ve koşu yeşil biter.
    # Hat listesi üç yerde (guncelle kütüğü, projeler koleksiyonu, HAT_MANSET)
    # elle tutuluyor; bu ölçüt üçüncüsünü ilk ikisine bağlar.
    print("\n▶ Manşet kapsamı (lib/anaSayfa.ts HAT_MANSET ↔ projeler/*.mdx ↔ ozet.json)")
    ana = (KOK / "site/src/lib/anaSayfa.ts").read_text(encoding="utf-8")
    proje_mdx = sorted((KOK / "site/src/content/projeler").glob("*.mdx"))
    n_tam = 0
    for yol in proje_mdx:
        slug = yol.stem
        on = yol.read_text(encoding="utf-8")[:2000]
        pasif = re.search(r"^durum:\s*'?(taslak|arsiv)'?", on, re.M) is not None
        m = re.search(r"^\s*'?%s'?:\s*\{([^}]*)\}" % re.escape(slug), ana, re.M)
        if not m:
            (uyari if pasif else hata).append(
                f"HAT_MANSET: {slug} girdisi yok — ana sayfa tablosunda ve kartta veri satırı çıkmaz")
            continue
        oz = KOK / "site/public/projeler" / slug / "ozet.json"
        if not oz.exists():
            (uyari if pasif else hata).append(f"HAT_MANSET: {slug} için ozet.json yok")
            continue
        d = json.loads(oz.read_text(encoding="utf-8"))
        for alan in ("anahtar", "tarihAlani"):
            k = re.search(alan + r":\s*'([^']+)'", m.group(1))
            if k and k.group(1) not in d:
                hata.append(f"HAT_MANSET: {slug}.{alan}='{k.group(1)}' ozet.json'da yok")
        n_tam += 1
    print(f"  {len(proje_mdx)} pano · girdisi ve anahtarı tam {n_tam}")

    # (2c) KOŞU KUTUSU ELLE SAYI TAŞIMAZ. Kutu uyarı listesini koşu kaydından
    # basar; MDX'te `sayi=` ya da slot içinde uyarı özeti kalırsa donar ve
    # 1/2b ölçütleri onu GÖRMEZ (yalnız <Deger> tarar). Kendini kapatan etiket
    # slotsuz sayılır.
    for yol in proje_mdx:
        mdx = yol.read_text(encoding="utf-8")
        for m in re.finditer(r"<KosuKutusu\b([^>]*?)(/?)>", mdx):
            if "sayi=" in m.group(1):
                hata.append(f"{yol.stem}: koşu kutusunda `sayi=` — sayı koşu kaydından gelir, elle yazılmaz")
            if m.group(2):
                continue
            kapanis = mdx.find("</KosuKutusu>", m.end())
            govde = mdx[m.end():kapanis] if kapanis > 0 else ""
            # Slot yazarın yorumu için serbesttir (tolerans, kural — sayı taşıyabilir);
            # yasak olan ESKİ ÖZET kalıbıdır: "N uyarı", "Bu koşuda … düştü", bayatlık hükmü.
            if re.search(r"\d+\s*uyarı|Bu koşuda .* düştü|uyarı yok|BAYAT VERİ", govde, re.I):
                hata.append(f"{yol.stem}: koşu kutusu slotunda elle uyarı özeti — uyarılar dosyadan basılır")

    # ---------------------------------------------------------------- (11b)
    # PROJE BAŞLIĞI YAZIMI (projeler/YAZIM.md): cümle düzeni — ilk sözcük büyük,
    # kalanlar küçük; özel ad ve kısaltmalar korunur; '&' yerine 've'. İki üslup
    # yan yana liste sayfasında ve ana sayfa tablosunda göze çarpıyordu.
    # '&' ENGEL, büyük harf uyarı (özel ad listesi kodda; yanlış alarm ölçülür).
    print("\n▶ Proje başlığı yazımı (projeler/YAZIM.md)")
    OZEL_AD = {"TCMB", "TL", "TÜFEX", "DİBS", "REDK", "USD/TRY", "GSYH", "FX", "TÜFE", "ÜFE",
               "İTO", "PPK", "BIST", "ABD", "AB", "IMF", "OIS", "ASW", "DXY", "GSYİH", "TÜİK",
               "Hazine", "Merkezi", "Türkiye", "İstanbul", "Avrupa", "Fed", "ECB"}
    n_baslik_uyari = 0
    for yol in proje_mdx:
        on = yol.read_text(encoding="utf-8")[:2000]
        m = re.search(r"^title:\s*['\"](.+?)['\"]\s*$", on, re.M)
        if not m:
            continue
        baslik = m.group(1)
        if "&" in baslik:
            hata.append(f"proje başlığı '&' taşıyor ({yol.stem}): {baslik!r} — 've' yazılır")
        sozcukler = re.split(r"[\s:/—–-]+", baslik)[1:]
        buyuk = [w for w in sozcukler if w and w[0].isupper() and w not in OZEL_AD
                 and not w.isupper()]
        if buyuk:
            uyari.append(f"proje başlığı Başlık Düzeni'nde ({yol.stem}): {baslik!r} — {buyuk}")
            n_baslik_uyari += 1
    # (11c) Gövdedeki /projeler/ bağlantı metinleri de aynı kurala uyar: Başlık
    # Düzeni ya da slug'ın kendisi ("kredi-parasal") okura gitmez — uyarı.
    n_bag = 0
    for yol in proje_mdx:
        govde = yol.read_text(encoding="utf-8")
        metinler = [m.group(2) for m in re.finditer(r'<a href="/projeler/([a-z-]+)/?">([^<]*?)</a>', govde, re.S)]
        metinler += [m.group(1) for m in re.finditer(r"\[([^\]]{2,60})\]\(/projeler/[a-z-]+/?\)", govde)]
        for ic in metinler:
            norm = " ".join(ic.split())
            sozcukler = re.split(r"[\s:/—–]+", norm)[1:]
            buyuk = [w for w in sozcukler if w and w[0].isupper() and w not in OZEL_AD and not w.isupper()]
            slugmu = re.fullmatch(r"[a-z]+(?:-[a-z]+)+", norm) is not None
            if buyuk or slugmu:
                uyari.append(f"proje bağlantı metni ({yol.stem}): {norm!r} — {'slug metin olmaz' if slugmu else 'cümle düzeni'}")
                n_bag += 1
    print(f"  {len(proje_mdx)} başlık · uyarı {n_baslik_uyari} · bağlantı metni uyarı {n_bag}")

    # (11d) PROJE ÖN BİLGİSİ (projeler/YAZIM.md; uyarı). description'da elle
    # sayılmış şekil/senaryo sayısı, guncelleme büyük harfle ya da şekil
    # numarasıyla başlıyor, kaynak'ta '&' ya da EVDS grup kodu (bie_…), tags
    # büyük harf. Ayrıştırıcı deponun tek ön bilgi ayrıştırıcısı (ortak/on_bilgi).
    print("\n▶ Proje ön bilgisi (projeler/YAZIM.md)")
    sys.path.insert(0, str(KOK / "ortak"))
    import on_bilgi
    n_on = 0
    for yol in proje_mdx:
        try:
            fm = on_bilgi.ayristir(yol.read_text(encoding="utf-8"))
        except Exception as ex:                                    # noqa: BLE001
            uyari.append(f"ön bilgi ayrıştırılamadı ({yol.stem}): {ex}")
            n_on += 1
            continue
        bulgu = []
        # kaynak ve guncelleme ZORUNLU (projeler/YAZIM.md): şema isteğe bağlı
        # tutuyordu ve rehberin 'zorunlu' dediği şey hiçbir kapıda zorunlu değildi.
        for alan in ("kaynak", "guncelleme"):
            if not str(fm.get(alan) or "").strip():
                hata.append(f"proje ön bilgisi ({yol.stem}): `{alan}` yok — pano künyesi "
                            "kaynağını ve yayım ritmini yazar (projeler/YAZIM.md)")
        acik = str(fm.get("description") or "")
        if re.search(r"\b\d+\s+(grafik|şekil|senaryo|tablo|hesap aracı)", acik, re.I):
            bulgu.append("description elle sayılmış şekil/senaryo sayısı taşıyor")
        ritim = str(fm.get("guncelleme") or "")
        if ritim and ritim[0].isupper() and ritim.split()[0] not in OZEL_AD:
            bulgu.append(f"guncelleme büyük harfle başlıyor: {ritim[:40]!r}")
        if re.search(r"\bŞekil\s*\d", ritim):
            bulgu.append("guncelleme şekil numarası taşıyor")
        kaynak = str(fm.get("kaynak") or "")
        if "&" in kaynak:
            bulgu.append("kaynak '&' taşıyor ('ve' yazılır)")
        if re.search(r"\bbie_[a-z0-9]+", kaynak):
            bulgu.append("kaynak EVDS grup kodu taşıyor (kodlar gövdedeki Kaynaklar'a)")
        etiketler = fm.get("tags") or []
        if isinstance(etiketler, list) and any(str(t) != str(t).lower() for t in etiketler):
            bulgu.append("tags küçük harf olmalı")
        for b_ in bulgu:
            uyari.append(f"proje ön bilgisi ({yol.stem}): {b_}")
        n_on += len(bulgu)
    print(f"  {len(proje_mdx)} pano · ön bilgi uyarı {n_on}")

    # ---------------------------------------------------------------- (12)
    # ÖZET SAATİ. `_tarih` hattın en yeni CANLI bacağının günüdür (CLAUDE.md
    # "Kurucu ilke — saat"); sözleşme yalnız gelenekte yaşıyordu ve bozulduğunda
    # (TÜFEX: metin karşılaştırmasıyla en eski bacak) hiçbir kapı düşmüyordu.
    # ENGEL: `_tarih` yok/çözülemiyor ya da yarından ileri. UYARI: `_tarih`
    # canlı bacakların en yenisinden bir günden fazla geride.
    print("\n▶ Özet saati (public/projeler/*/ozet.json `_tarih`)")
    sys.path.insert(0, str(KOK / "ortak"))
    import bicim as _bicim
    import datetime as _dt
    bugun = _dt.date.today()
    ozetler_hepsi = sorted((KOK / "site/public/projeler").glob("*/ozet.json"))
    for oz in ozetler_hepsi:
        slug = oz.parent.name
        try:
            d = json.loads(oz.read_text(encoding="utf-8"))
        except Exception as ex:                                    # noqa: BLE001
            hata.append(f"{slug}/ozet.json okunamadı: {ex}")
            continue
        t = _bicim.tarihe_cevir(d.get("_tarih"))
        if t is None:
            hata.append(f"{slug}/ozet.json: `_tarih` yok ya da çözülemiyor ({d.get('_tarih')!r})")
            continue
        # SINIR "yarın" DEĞİL, ERTESİ İŞ GÜNÜ (ortak/bicim.sonraki_is_gunu —
        # gerekçe orada): TCMB ertesi iş gününün gösterge kurunu bugün
        # yayımlıyor, yani cuma çekilen seri PAZARTESİ ile biter. "Yarından
        # ileri" kuralı bu yüzden her cuma yanlış alarm veriyordu.
        sinir = _bicim.sonraki_is_gunu(bugun)
        if t > sinir:
            hata.append(f"{slug}/ozet.json: `_tarih` {d['_tarih']} ertesi iş "
                        f"gününden ({sinir:%d.%m.%Y}) ileri")
        canli = [_bicim.tarihe_cevir(v) for k, v in d.items()
                 if k.endswith("_tarih") and k != "_tarih" and isinstance(v, str)]
        canli = [c for c in canli if c is not None and c <= sinir]
        if canli and (max(canli) - t).days > 1:
            uyari.append(f"{slug}/ozet.json: `_tarih` {d['_tarih']} ama bir bacak "
                         f"{max(canli):%d.%m.%Y} — hattın saati geride kalmış olabilir")
    print(f"  {len(ozetler_hepsi)} özet tarandı")

    # ---------------------------------------------------------------- (13)
    # BİÇİM TEK KAYNAK (uyarı). lib/bicim.ts "başka yerde sayı biçimlenmez"
    # der; kural yorumda kalmasın. Hesap araçları henüz kendi biçimleyicisini
    # taşıyor — kapı değil uyarı, ama adıyla görünür.
    print("\n▶ Yerel biçimleyici (lib/bicim.ts dışında)")
    kalip = re.compile(r"toLocaleString\('tr-TR'|toLocaleDateString\(|Intl\.DateTimeFormat\(")
    yerel = []
    for yol in sorted((KOK / "site/src").rglob("*")):
        if yol.suffix not in (".astro", ".ts") or yol.name == "bicim.ts":
            continue
        n = len(kalip.findall(yol.read_text(encoding="utf-8")))
        if n:
            yerel.append((yol.relative_to(KOK / "site/src").as_posix(), n))
    for yol, n in yerel:
        uyari.append(f"yerel biçimleyici: {yol} ({n}) — lib/bicim'e taşınmalı")
    print(f"  {len(yerel)} dosyada yerel biçimleyici")

    # ---------------------------------------------------------------- (14)
    # CSS JETONU TANIMLI MI. `var(--x)` tanımsızsa tarayıcı sessizce kalıtıma
    # düşer: iki içindekiler etiketi ev stilinin grisini almıyordu ve hiçbir
    # şey söylemiyordu. Statik, saniyeler sürer: kullanılan her jeton global.css
    # ya da aynı dosyada tanımlı olmalı.
    print("\n▶ CSS jetonları (var(--x) tanımlı mı)")
    # Tanım her yerde olabilir: global.css, bileşen <style>'ı ya da satır içi
    # style="--d: 40ms" (kademeli animasyon gecikmesi bileşenden gelir).
    dosyalar = sorted((KOK / "site/src").rglob("*.astro")) + sorted((KOK / "site/src").rglob("*.css"))
    tanimli: set[str] = set()
    for yol in dosyalar:
        tanimli |= set(re.findall(r"(--[a-zA-Z0-9-]+)\s*:", yol.read_text(encoding="utf-8")))
    tanimsiz = []
    for yol in dosyalar:
        icerik = yol.read_text(encoding="utf-8")
        for ad in set(re.findall(r"var\((--[a-zA-Z0-9-]+)", icerik)):
            if ad not in tanimli:
                tanimsiz.append(f"{yol.relative_to(KOK / 'site/src').as_posix()}: var({ad})")
    for t in tanimsiz:
        hata.append("tanımsız CSS jetonu — " + t)
    print(f"  {len(tanimli)} jeton tanımlı · tanımsız kullanım {len(tanimsiz)}")

    # ---------------------------------------------------------------- (15)
    # SİMGE SÖZLEŞMESİ. Base.astro'nun ilan ettiği her simge dosyası public/
    # altında var mı; PNG ise gerçek boyutu `sizes` ile aynı mı; SVG ilan
    # edilmiş mi. İlan edilip üretilmeyen ya da üretilip ilan edilmeyen simge
    # sözleşmeyi yarım bırakır.
    print("\n▶ Simge sözleşmesi (Base.astro ↔ public/)")
    import struct as _struct
    base = (KOK / "site/src/layouts/Base.astro").read_text(encoding="utf-8")
    simgeler = re.findall(r'<link rel="(icon|apple-touch-icon)"([^>]*)>', base)
    svg_var = False
    for rel, nit in simgeler:
        href = re.search(r'href="([^"]+)"', nit)
        if not href:
            hata.append(f"simge bağı href'siz: {rel}")
            continue
        dosya = KOK / "site/public" / href.group(1).lstrip("/")
        if not dosya.exists():
            hata.append(f"ilan edilen simge yok: {href.group(1)}")
            continue
        if dosya.suffix == ".svg":
            svg_var = True
        elif dosya.suffix == ".png":
            bas = dosya.read_bytes()[:24]
            g, y = _struct.unpack(">II", bas[16:24]) if bas[12:16] == b"IHDR" else (0, 0)
            m = re.search(r'sizes="(\d+)x(\d+)"', nit)
            if m and (g, y) != (int(m.group(1)), int(m.group(2))):
                hata.append(f"simge boyutu ilanla farklı: {href.group(1)} {g}×{y}, ilan {m.group(1)}×{m.group(2)}")
    if not svg_var:
        hata.append("SVG simge ilan edilmemiş (favicon.svg tek kaynaktır)")
    for png in sorted((KOK / "site/public").glob("*.png")):
        if png.name not in base:
            uyari.append(f"public/{png.name} üretilmiş ama Base.astro ilan etmiyor")
    print(f"  {len(simgeler)} simge ilanı")

    # ---------------------------------------------------------------- (16)
    # YAYIN TAKVİMİ. Hakkında sayfasının saatleri iş akışı cron'larından
    # türetilir; sayfayı YAYIMLAYAN kapı kaymayı görmezse sayfa eski saati
    # anlatmaya devam eder. Karşılaştırma ortak/yayin_takvimi.py'de tek yerde
    # (bulten/duman.py de aynı fonksiyonu çağırır).
    print("\n▶ Yayın takvimi (hakkında ↔ iş akışı cron'ları)")
    sys.path.insert(0, str(KOK / "ortak"))
    import yayin_takvimi
    takvim_bulgu = yayin_takvimi.karsilastir(KOK)
    for b_ in takvim_bulgu:
        hata.append("yayın takvimi — " + b_)
    print(f"  bulgu {len(takvim_bulgu)}")

    # ---------------------------------------------------------------- (18)
    # ŞEKİL SAAT DEFTERİ. GrafikEmbed her şeklin altına "veri <tarih>" basar;
    # tarih, MDX'te `tarihAnahtari` verilmemişse hattın ANA saatinden gelir.
    # Bir hattın figürleri farklı ritimlerdeyse o damga YALAN söyler ve iki
    # yönde birden: FX haber endeksinde GDELT panelleri dört gün eskiyken
    # "bugün" diye damgalanıyor, okur da bunu tersinden okuyup taze endeksi
    # bayat sanıyordu. Çözüm hattın kendi ilanı: `_sekil_tarih` sözlüğü, her
    # figürün ucunu ÇİZEN kodun elinden yazar.
    #
    # Ölçüt ilan edeni ölçer, ilan etmeyeni zorlamaz — 17 hattın hepsine bir
    # defter dayatmak, tek saatli hatlar için boş iş olurdu. Bir hat defteri
    # AÇTIYSA eksiksiz olmalı: gömülü her figürünün girdisi bulunmalı (UYARI,
    # çünkü yeni bir figür bunu unutabilir ve yayını durdurmak orantısız) ve
    # hiçbir tarih YARINDAN İLERİ olmamalı (ENGEL, çünkü bu ölçülemez bir
    # iddiadır). Girdinin değeri null olabilir: "bu figürün ucu ölçülmedi"
    # demektir ve sayfa o şeklin altına tarih basmaz — uydurmaktan iyidir.
    print("\n▶ Şekil saat defteri (ozet.json `_sekil_tarih`)")
    import datetime as _dt2
    sys.path.insert(0, str(KOK / "ortak"))
    import bicim as _bicim2
    sinir = _bicim2.sonraki_is_gunu(_dt2.date.today())
    n_defter = n_sekil = 0
    for slug, _klasor in HATLAR:
        oj = KOK / "site/public/projeler" / slug / "ozet.json"
        mp = KOK / "site/src/content/projeler" / f"{slug}.mdx"
        if not oj.exists() or not mp.exists():
            continue
        try:
            o = json.loads(oj.read_text(encoding="utf-8"))
        except Exception:                                      # noqa: BLE001
            continue
        if not isinstance(o.get("_sekil_tarih"), dict):
            continue
        n_defter += 1
        e_, u_, n_ = sekil_saat_bulgulari(slug, o, mp.read_text(encoding="utf-8"), sinir)
        hata.extend(e_)
        uyari.extend(u_)
        n_sekil += n_
    print(f"  {n_defter} hat defter açmış · {n_sekil} figür")

    # --------------------------------------------------------------- (18b)
    # AÇIK ANAHTAR GERÇEKTEN ÇÖZÜLÜYOR MU. Damganın ilk basamağı MDX'teki
    # `tarihAnahtari`dir, ama 18. ölçüt yalnız DEFTER AÇAN hatta bakıyordu ve
    # açık anahtarı hiçbir şey ölçmüyordu — "bir denetimin KAPSAMI denetimin
    # parçasıdır" kusurunun aynısı, bir basamak yukarıda. GrafikEmbed anahtarı
    # ancak DİZGE ise kullanır; yoksa, null ise ya da sayıysa sessizce hattın
    # ana saatine düşer. Yani yazar bir saat İLAN ETMİŞTİR, sayfa başkasını
    # basar ve ikisi de yeşil görünür. Somut hâli: hazine-ihrac'ta `plan_tarih`
    # yürürlükteki takvimin iskeleti arşivdekilerin hiçbiriyle tutmazsa hiç
    # yazılmıyor; Şekil 02 ve 11 o gün 13 gün eski bir damgaya döner ve kimse
    # görmez.
    # Kapsam listeden değil SÖZLEŞMEDEN: hattı `src` söyler, yani analiz ve
    # araştırma sayfalarına gömülü figürler de girer — bileşen de tam olarak
    # böyle çözüyor.
    # ÜÇ HÂL, okura ULAŞAN kusura göre — hassasiyet de ölçütün parçası:
    #  · anahtar yok ya da DİZGE DEĞİL → bileşen sessizce hattın ana saatine
    #    düşer, ilan edilen saat ile basılan saat ayrışır ve hiçbir iz kalmaz
    #    → UYARI (sayfa yine savunulabilir bir gün basar, yayını durdurmaz);
    #  · dizge ama içinde HİÇ tarih yok → bileşen onu şeklin altına OLDUĞU
    #    GİBİ basar → UYARI;
    #  · içindeki bir tarih YARINDAN İLERİ → ENGEL, ölçülmemiş bir gün okura
    #    basılıyor. 12. ölçüt bu soruyu yalnız `_tarih` için sorar ve bacak
    #    tarihlerini eleyip geçer, yani buraya bakan başka kimse yok.
    # Tarihler dizgenin İÇİNDE aranır, dizgenin kendisi tarih olmak zorunda
    # değil: bileşenin sözleşmesi dizgeyi geçirmek (odemeler-dengesi'nde iki
    # saatli bir etiket bilerek böyle yazılıyor). "Saf tarih değil" diye uyarı
    # üretmek, doğru çalışan bir sayfada kalıcı yanlış alarm olurdu.
    print("\n▶ Açık şekil tarihi (MDX `tarihAnahtari` ↔ ozet.json)")
    n_ta = 0
    for mdx_yol in sorted((KOK / "site/src/content").rglob("*.mdx")):
        for etiket in re.findall(r"<GrafikEmbed\b[^>]*/>", mdx_yol.read_text(encoding="utf-8")):
            ta = re.search(r'tarihAnahtari="([^"]+)"', etiket)
            sr = re.search(r'src="/projeler/([^/"]+)/([^"]+)"', etiket)
            if not ta or not sr:
                continue
            n_ta += 1
            anahtar, slug2, dosya2 = ta.group(1), sr.group(1), sr.group(2)
            nerede = f"{mdx_yol.name} · {dosya2} → `{anahtar}`"
            oj2 = KOK / "site/public/projeler" / slug2 / "ozet.json"
            try:
                o2 = json.loads(oj2.read_text(encoding="utf-8"))
            except Exception as ex:                                # noqa: BLE001
                uyari.append(f"{nerede}: {slug2}/ozet.json okunamadı ({ex})")
                continue
            dft = o2.get("_sekil_tarih")
            dft = dft if isinstance(dft, dict) else {}
            e_, u_ = acik_saat_bulgulari(nerede, o2, anahtar, dft.get(dosya2),
                                         dosya2 in dft, sinir, _bicim2.tarihe_cevir)
            hata.extend(e_)
            uyari.extend(u_)
    print(f"  {n_ta} açık anahtar")

    # ---------------------------------------------------------------- (19)
    # ŞEKİL METNİNDE OKUR DİLİ. Gerekçe ve ağırlıklar sekil_okur_dili'de.
    # Kapsam SÖZLEŞMEDEN: siteye kopyalanmış her gömülü figür — hangi hattın
    # ürettiği, hangi koleksiyonda gömülü olduğu fark etmez; okur hepsini
    # aynı biçimde görüyor.
    print("\n▶ Şekil metninde okur dili (gömülü Plotly başlık ve alt yazıları)")
    n_sek = 0
    kod_bulgu: dict[str, set[str]] = {}
    aile_sayim: dict[str, int] = {}
    for hp in sorted((KOK / "site/public/projeler").rglob("*.html")):
        ham = hp.read_text(encoding="utf-8", errors="ignore")
        if "Plotly" not in ham:
            continue
        n_sek += 1
        nerede = f"{hp.parent.name}/{hp.name}"
        e_, u_, say_ = sekil_okur_dili(sekil_metinleri(ham), nerede)
        hata.extend(e_)
        for satir in u_:
            kod_bulgu.setdefault(satir.split(": ", 1)[-1], set()).add(nerede)
        for a_, n_ in say_.items():
            aile_sayim[a_] = aile_sayim.get(a_, 0) + n_
    if kod_bulgu:
        ornek = ", ".join(sorted(kod_bulgu)[:6])
        uyari.append(
            f"şekil metninde kod dili: {len(kod_bulgu)} ayrı kod, "
            f"{len({y for ys in kod_bulgu.values() for y in ys})} figürde "
            f"({ornek}{' …' if len(kod_bulgu) > 6 else ''}) — figürü üreten "
            "hattın alt yazısı okura değil operatöre yazıyor")
    print(f"  {n_sek} figür · kod dili {len(kod_bulgu)} ayrı kod · "
          + " · ".join(f"{a} {n}" for a, n in sorted(aile_sayim.items())))
    for esl, yerler in sorted(kod_bulgu.items()):
        print(f"    – {esl}: {len(yerler)} figür ({sorted(yerler)[0]}…)")

    # ---------------------------------------------------------------- (17)
    # KOŞU KAYDI OKUR DİLİ. Koşu kutusu uyarilar.json'daki `uyarilar` listesini,
    # veri durumu şeridi ozet.json'daki `uyari_metni`/`bayat_cumlesi`ni OLDUĞU
    # GİBİ basar; bu satırları hatların Python'u operatör için yazıyordu ve 9.
    # ölçüt onları görmüyordu (kaynak MDX değil, veri dosyası): `kkm_aktif`
    # bayrağı, `bie_pydibsarsiv` grubu ve '5.2%' okura gitti, sınav yeşildi.
    # Kural tek yerde (okur_dili.kosu_kaydi_tara); guncelle.py aynı soruyu hat
    # koştuğu anda uyarı olarak sorar. Burada iki ağırlık: şablondan başka
    # yerden gelemeyecek kusur (backtick, dosya adı, bie_ kodu, yapım dili)
    # ENGEL; bir yer tutucudan sızabilecek anahtar adı ve biçim UYARI — veri
    # kaynaklı bir sızıntı günün bültenini durdurmaz, ama adıyla görünür.
    print("\n▶ Koşu kaydı okur dili (public/projeler/*/uyarilar.json · ozet.json)")
    n_kayit = n_kk = 0
    for klasor in sorted(p for p in (KOK / "site/public/projeler").iterdir() if p.is_dir()):
        satirlar: list[tuple[str, str]] = []
        uj = klasor / "uyarilar.json"
        if uj.exists():
            try:
                u = json.loads(uj.read_text(encoding="utf-8"))
                if isinstance(u, dict):
                    satirlar += [("uyarilar.json", str(x)) for x in (u.get("uyarilar") or [])]
            except Exception as ex:                                # noqa: BLE001
                hata.append(f"{klasor.name}/uyarilar.json okunamadı: {ex}")
        oj = klasor / "ozet.json"
        if oj.exists():
            try:
                d = json.loads(oj.read_text(encoding="utf-8"))
                # KAPSAM, LİSTEDEN DEĞİL SÖZLEŞMEDEN — tanım tek yerde:
                # okur_dili.ozet_cumleleri (gerekçesi orada yazılı).
                satirlar += [(f"ozet.json `{a}`", m)
                             for a, m in okur_dili.ozet_cumleleri(d)]
            except Exception:                                      # noqa: BLE001
                pass                       # okunamayan özeti 12. ölçüt düşürür
        n_kayit += len(satirlar)
        for kaynak_adi, metin in satirlar:
            for _i, aile, esl in okur_dili.kosu_kaydi_tara([metin]):
                hedef = hata if aile in okur_dili.KOSU_KAYDI_ENGEL else uyari
                hedef.append(f"koşu kaydı {aile} — {klasor.name}/{kaynak_adi}: {esl!r}")
                n_kk += 1
    print(f"  {n_kayit} satır tarandı · bulgu {n_kk}")

    # (9b) OKUR DİLİ, DERLENMİŞ ÇIKTIDA (uyarı). 9. ölçüt yalnız içerik
    # dosyalarına bakıyor; bileşenlerden gelen dizgeleri ("ozet.json"
    # bağlantı metni) yalnız okurun gördüğü sayfa taşır.
    if (KOK / "site/dist").exists():
        print("\n▶ Okur dili (derlenmiş sayfa metni)")
        n_dist = 0
        for h in sorted((KOK / "site/dist").rglob("index.html")):
            html = h.read_text(encoding="utf-8", errors="replace")
            # Kaynaktaki muafiyetlerin karşılığı: kod bloğu ve satır içi kod
            # okura "kod" olarak sunulur, taranmaz.
            html = re.sub(r"<(script|style|code|pre)[^>]*>.*?</\1>", " ", html, flags=re.S)
            duz = re.sub(r"<[^>]+>", " ", html)
            for aile, esl, _sat in okur_dili.tara(duz):
                if n_dist < 12:
                    uyari.append(f"dist okur dili — {h.relative_to(KOK / 'site/dist').parent.as_posix() or '.'}: "
                                 f"{aile}: {esl!r}")
                n_dist += 1
        print(f"  bulgu {n_dist}")

    # ------------------------------------------------------------ (20)
    # ÖLÜ İÇ BAĞ. Silinen bir sayfaya bağlanan başka bir sayfa hiçbir yerde
    # hata vermez; yalnız okur 404 görür. Ölçüt dist/ varsa koşar.
    print("\n▶ Ölü iç bağ (dist/ içindeki href hedefleri)")
    if not (KOK / "site/dist").exists():
        print("  – dist/ yok (önce `npm run build`), ÖLÇÜT KOŞMADI")
        uyari.append("ölçüt 20 (ölü iç bağ) KOŞMADI — dist/ yok")
    else:
        kirik = olu_ic_baglar(KOK / "site/dist")
        for yol, sayfalar in sorted(kirik.items()):
            hata.append(f"ölü iç bağ {yol} — {len(sayfalar)} sayfada, ör. "
                        f"{sayfalar[0]}")
        print(f"  hedefsiz adres {len(kirik)}")

    # ------------------------------------------------------------ (21)
    # X İZİ. Site X gönderisini okura göstermiyor (kullanıcı kararı); bağı
    # kuran bileşendi, o yüzden ölçüt kaynağa değil ÇIKTIYA bakar.
    print("\n▶ X izi (dist/ içinde gönderi bağı ve 'X gönderisi' yazısı)")
    if not (KOK / "site/dist").exists():
        # KOŞMAYAN ÖLÇÜT, GEÇEN ÖLÇÜT DEĞİLDİR. `npm run sinav` derlemiyor;
        # yerelde onu koşan biri bu kararın TEK kapısının hiç çalışmadığını
        # göremezdi ve rapor yine "GEÇTİ" derdi.
        print("  – dist/ yok (önce `npm run build`), ÖLÇÜT KOŞMADI")
        uyari.append("ölçüt 21 (X izi) KOŞMADI — dist/ yok; `npm run yayin-kontrol` derleyerek koşar")
    else:
        izler = x_izleri(KOK / "site/dist")
        for esl, sayfalar in sorted(izler.items()):
            hata.append(f"X izi {esl!r} — {len(sayfalar)} sayfada, ör. {sayfalar[0]}")
        print(f"  ayrı iz {len(izler)}")

    # ------------------------------------------------------------ (22)
    # KAÇAN ETİKET. Yazı katmanının metni HTML taşır; bir alan `set:html`
    # yerine metin olarak basılırsa okur cümlenin başında "<p>" görür.
    print("\n▶ Kaçan etiket (dist/ içinde okura basılan HTML etiketi)")
    if not (KOK / "site/dist").exists():
        print("  – dist/ yok (önce `npm run build`), ÖLÇÜT KOŞMADI")
        uyari.append("ölçüt 22 (kaçan etiket) KOŞMADI — dist/ yok")
    else:
        kacan = kacan_etiketler(KOK / "site/dist")
        for esl, sayfalar in sorted(kacan.items()):
            hata.append(f"kaçan etiket {esl!r} — {len(sayfalar)} sayfada, ör. {sayfalar[0]}")
        print(f"  ayrı kaçış {len(kacan)}")

    # ------------------------------------------------------------ (24)
    # SABİT KAP. Yalnız panolar canlı; analiz ve ders gövdesi kapta.
    print("\n▶ Sabit kap (dist/: analiz ve ders gövdesi data-deger=\"sabit\", pano değil)")
    if not (KOK / "site/dist").exists():
        print("  – dist/ yok (önce `npm run build`), ÖLÇÜT KOŞMADI")
        uyari.append("ölçüt 24 (sabit kap) KOŞMADI — dist/ yok")
    else:
        sk = sabit_kap_bulgulari(KOK / "site/dist")
        for b in sk:
            hata.append(f"sabit kap — {b}")
        print(f"  ihlal {len(sk)}")

    # ------------------------------------------------------------ (25)
    # OLAY OKURA ULAŞTI MI. Ölçülen her önemli/dikkat olay sayfada görünmeli.
    print("\n▶ Olay okura ulaştı mı (dist/: her önemli/dikkat olayın cümlesi sayfada)")
    if not (KOK / "site/dist/bulten").exists():
        print("  – dist/bulten yok (önce `npm run build`), ÖLÇÜT KOŞMADI")
        uyari.append("ölçüt 25 (olay okura ulaştı mı) KOŞMADI — dist/bulten yok")
    else:
        kayip, aranan, bulundu = olay_okura_ulasti(KOK)
        for k in kayip:
            hata.append(f"ulaşmayan olay — {k}")
        print(f"  aranan {aranan} · sayfada {bulundu} · kayıp {len(kayip)}")

    # ------------------------------------------------------------ (23)
    # SOLUK METİN. global.css'in kendi yorumu "--ink-30 metinde kullanılmaz"
    # diyor; kural hiçbir yerde dayatılmıyordu ve on beş yerde çiğnenmişti.
    print("\n▶ Soluk metin (--ink-30 metin rengi olarak · kontrast 1,90:1)")
    sol = soluk_metin(KOK)
    for y in sol:
        hata.append(f"soluk metin — {y}: `color: var(--ink-30)` kontrast 1,90:1 "
                    f"(AA gövde 4,5:1). global.css: '--ink-30 yalnız çizgi ve "
                    f"kenarlıkta'. Metin için --ink-60 (4,59:1).")
    print(f"  ihlal {len(sol)}")

    print()
    for u in uyari:
        print("  ! " + u)
    if hata:
        for h in hata:
            print("  ✗ " + h)
        print(f"\nSAYFA SINAVI DÜŞTÜ ({len(hata)} bulgu · {len(uyari)} uyarı).")
        return 1
    print(f"SAYFA SINAVI GEÇTİ ({len(uyari)} uyarı).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
