#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sayfa ↔ hat sözleşmesi sınavı (CI'da koşturulabilir).

Bu sınav, "hat koştu ama sayfa yalan söylüyor" sınıfı hataları yakalar. Dokuz
bölüm var; her biri düzenin bir kuralına karşılık gelir:

  (1) <Deger> anahtarları — MDX'te çağrılan her anahtar ozet.json'da var mı?
      Yoksa sayfada STATİK yedek görünür ve veri tazelendikçe donar.
  (2) ÇIPLAK OYNAK SAYI — ozet.json'daki oynak bir değerin Türkçe biçimi,
      MDX'te <Deger> ile sarılmadan düz metin olarak geçiyor mu? (CLAUDE.md
      kural 5'in ihlali: bir sonraki tazelemede o cümle donar.)
  (3) Şekil yüksekliği — MDX'teki yukseklik={} değeri, üretimin
      cikti/yukseklikler.json'daki gerçek script height'i ile aynı mı?
  (4) Dosya kümesi — üretimdeki figürler siteye birebir kopyalanmış mı ve
      hepsinde ev stili bloğu var mı?
  (5) Panel düzeni — paneller ALT ALTA mı? (yan yana panel yasak)
  (6) KaTeX — her formül ayrıştırılabiliyor mu? (rehype-katex düşmez, ham basar)
  (7) <Deger> anahtarları TÜM koleksiyonlarda — analiz ve araştırma
      sayfaları da aynı sözleşmeyi kullanıyor; kural 1 onları görmüyordu.
  (8) DERLENMİŞ ÇIKTI — dist/ içinde KaTeX hatası, ham <Deger> etiketi ya
      da çözülmemiş MDX yorumu var mı? Kaynağı sınayan ölçütlerin
      göremediği tek şey: okurun gerçekte gördüğü sayfa.
  (9) OKUR DİLİ — kod ve yapım dili (ortak/okur_dili.py).
  (10) ANALİZ BİÇİMİ — analiz/YAZIM.md'nin araçtaki karşılığı
      (site/tools/analiz_sinavi.py): tarihli slug ve başlık, zorunlu ön
      bilgi, yönetici özeti, kapanış bölümü.
  (11) MANŞET KAPSAMI — her proje sayfasının HAT_MANSET girdisi var mı ve
      anahtarı ozet.json'da mı? (eksik pano tablodan sessizce düşerdi)
  (12) ÖZET SAATİ — her ozet.json'un `_tarih`i çözülüyor, yarından ileri
      değil ve canlı bacakların en yenisinden geride kalmamış.
  (13) BİÇİM TEK KAYNAK (uyarı) — lib/bicim.ts dışında yerel biçimleyici.
  (9b) OKUR DİLİ, derlenmiş çıktıda (uyarı) — bileşen dizgeleri de kapıya girer.

Koşum:  python3 site/tools/sayfa_sinavi.py
Çıkış:  0 = geçti · 1 = en az bir sınav düştü
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys

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


def deger_disi(mdx: str) -> str:
    """MDX'ten <Deger …>…</Deger> bloklarını, kod bloklarını ve satır içi
    kodu çıkar — geriye kalan, gerçekten çıplak duran metindir."""
    s = re.sub(r"<Deger\b[\s\S]*?</Deger>", " ", mdx)
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
    for slug, klasor in HATLAR:
        proje = KOK / klasor
        mp = KOK / "site/src/content/projeler" / f"{slug}.mdx"
        oj = proje / "ozet.json"
        if not mp.exists() or not oj.exists():
            print(f"  – {slug}: sayfa ya da ozet.json yok, atlandı")
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
        ciplak = []
        for k, v in o.items():
            if k in muaf:
                continue
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                continue
            if abs(v) < TARAMA_ALT_SINIR:
                continue
            for d in TARAMA_ONDALIK:
                metin = tr(float(v), d)
                if len(metin.replace(".", "").replace(",", "")) < 3:
                    continue          # iki haneli sayılar çok yaygın, taranmaz
                if re.search(r"(?<![\d.,])" + re.escape(metin) + r"(?![\d.,])", disi):
                    ciplak.append(f"{k}={metin}")
                    break
        if ciplak:
            bulgu(slug, f"{slug}: ÇIPLAK OYNAK SAYI (kural 5): "
                        + ", ".join(sorted(set(ciplak))))
        print(f"  (2) çıplak oynak sayı: {len(set(ciplak))}"
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
    # (7) <Deger> ANAHTARLARI — YALNIZ PROJE SAYFALARINDA DEĞİL, HER SAYFADA.
    # Kural 1 yalnız site/src/content/projeler/<slug>.mdx'e bakıyordu. Ama
    # <Deger> sözleşmesi koleksiyondan bağımsız: bileşen ozet.json'u
    # /projeler/<proje>/ genel yolundan çekiyor ve analiz/araştırma sayfaları
    # da onu kullanıyor. Büyüme yazısı projeler'den analiz'e taşındığı gün
    # sınavın görüş alanından da çıkmıştı; borçlanma ve İTO yazıları hiç
    # girmemişti. Donan bir sayının hangi klasörde durduğu okur için bir şey
    # ifade etmiyor — denetim de ayırmamalı.
    print("\n▶ Tüm sayfalarda <Deger> anahtarları")
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
        if eksik:
            hata.append(f"{ad}: ozet.json'da olmayan anahtar: {eksik}")
        print(f"  {ad}: {len(kul)} kullanım · eksik {len(eksik)}"
              + (f" · bilinmeyen proje {bilinmez}" if bilinmez else ""))
    print(f"  toplam {n_sayfa} sayfa · {n_kul} <Deger> kullanımı")

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
        if t > bugun + _dt.timedelta(days=1):
            hata.append(f"{slug}/ozet.json: `_tarih` {d['_tarih']} yarından ileri")
        canli = [_bicim.tarihe_cevir(v) for k, v in d.items()
                 if k.endswith("_tarih") and k != "_tarih" and isinstance(v, str)]
        canli = [c for c in canli if c is not None and c <= bugun + _dt.timedelta(days=1)]
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
