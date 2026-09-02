#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tweet KALİTE KAPISI — gönderimden önce, araçta.

Neden var: tweet sitenin en kısa metni ve en geniş okur kitlesi. Bülten
denetimi (bulten/denetim.py) sayfayı sınıyor ama tweet o sayfadan KIRPILARAK
kuruluyor: kırpma bir cümleyi sayının ortasında kesebilir, iki bölüm aynı
cümleyi iki kez taşıyabilir, boş kalan bir bölümün etiketi yalnız başına
durabilir. Bunların hiçbirini sayfa denetimi göremez; tweet metnini ancak
tweet metni üzerinde koşan bir denetim görür.

İki sınıf bulgu:
  ENGEL  gönderim durur (tavsiye dili, link, HTML kalıntısı, site atfı,
         sayı ortasında kesilmiş cümle, boş bölüm etiketi, uzunluk, okur dili,
         sorumluluk notu eksik)
  UYARI  loga yazılır, gönderim sürer (tekrar eden cümle, ASCII eksi, çift boşluk)

Kullanım:
    engel, uyari = denetle(metin, tur)      # tur: bulten | teknik | analiz
    python3 tweet/denetim.py dosya.txt      # tek metni sına, çıkış 1 = engel

Kalıplar tek yerde durur: okur dili ortak/okur_dili.py'den, tavsiye dili
ortak/tavsiye_dili.py'den, uzunluk tavanı uret.TEK_TAVAN'dan alınır — ayrı
listeler bir gün sessizce ayrışırdı.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent
# Yol sırası bilinçli: tweet/ EN ÖNDE. bulten/ da yolda dursaydı `import uret`
# bulten/uret.py'yi getirebilir ve aynı kapı iki yoldan iki farklı sonuç verirdi
# (ölçüldü: CLI'da 'bülten' izi engel, gonder yolunda değil). Ortak kalıplar
# ortak/'tan; bulten/'a bağımlılık yok.
sys.path.insert(0, str(KOK / "ortak"))
sys.path.insert(0, str(BURASI))

import okur_dili  # noqa: E402

from tavsiye_dili import TAVSIYE  # noqa: E402  — bülten/teknik/analiz kapılarıyla AYNI kalıp

EN_AZ = 200          # bundan kısa bir tweet içerik değil, kaza
try:
    import uret as _uret
    EN_COK = _uret.TEK_TAVAN          # tavan TEK yerde (uret); burada kopya tutulmaz
except Exception:                                              # noqa: BLE001
    EN_COK = 3800

# İlk satır türe göre bir başlık taşır — okur akışta hangi yayının geldiğini
# ilk bakışta görür. Bülten: "Sabah Notu — 1 Eylül 2026" / "Haftaya Bakış — …";
# analiz: "Analiz — 1 Eylül 2026". Teknik başlığı uret'in kendi kalıbından gelir.
ILK_SATIR = {
    "bulten": re.compile(r"^(Sabah Notu|Haftaya Bakış) — \d{1,2} [A-ZÇĞİÖŞÜ][a-zçğıöşü]+ \d{4}"),
    "analiz": re.compile(r"^Analiz — \d{1,2} [A-ZÇĞİÖŞÜ][a-zçğıöşü]+ \d{4}"),
}

# Aralık tiresi: "%1,25-%2,10", "3-5 gün" → Türkçe yazımda uzun tire (–). UYARI.
# ISO tarih ("2026-09-01") aralık değildir: yıl ve ay tireleri dışarıda.
ARALIK_TIRESI = re.compile(r"(?<!\d{4})(?<!\d{4}-\d{2})(?<=[\d%])-(?=[%\d])")

# Sorumluluk notu: her tür tweet aynı kapanışla biter. Kalıp esnek — "Analizdir;
# yatırım tavsiyesi değildir." ve "Analiz ve ölçümdür; yatırım tavsiyesi
# değildir." ikisi de geçer; aranan çekirdek ifade.
SORUMLULUK = re.compile(r"yatırım tavsiyesi değildir", re.I)

# Emoji ve süsleme: 30.08 kararı — yok. Aralıklar: semboller, piktogramlar,
# bayraklar, varyasyon seçicisi. Tipografik işaretler (−, ·, →, σ, ≈, ±) serbest.
EMOJI = re.compile("[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF\u2300-\u23FF\u25A0-\u25FF"
                   "\u2B00-\u2BFF\u203C\u2049\u2122\u2139\u3030\u303D\u3297\u3299\u00A9\u00AE\u2022\uFE0F⭐⬆⬇✅❌]")

# Sayıdan hemen önce ASCII tire: "-1,88" yerine "−1,88" olmalı. Aralık tiresi
# ("%1,25-%2,10") ayrı kalıpla (ARALIK_TIRESI) yakalanır — Türkçe yazımda aralık
# için uzun tire (–). İkisi de UYARI: gönderimi durdurmaz, kaydı düşer.
ASCII_EKSI = re.compile(r"(?<![\w.,])-(?=[%\d])")

# LİNK YASAĞI — kullanıcı kararı, istisnasız: tweetlerde HİÇ link kullanılmaz.
# Açık adres, www., markdown bağlantısı, kısaltıcı ve X adresleri, ÇIPLAK alan
# adı (cocoonish.github.io, tcmb.gov.tr) — hepsi ENGEL. Tanım tek yerde durur;
# gonder.py gönderimden hemen önce ve ozel.py de aynı fonksiyonu çağırır, yani
# kapı denetim atlansa bile gönderim katmanında bir kez daha kapanır.
_TLD_LISTE = ("com net org io co gov edu info biz xyz app dev me tv tr de uk us eu ai page site news link ly "
              "ch jp ru se no fr it es nl at dk fi pl cz hu kr cn in br au ca nz za mx ar il sa ae qa sg hk tw be pt gr ie").split()
# TLD ya tamamı küçük ya tamamı BÜYÜK: 'ettik.Biz de' baş harfi büyük bir cümle
# başıdır, alan adı değil; 'COCOONISH.GITHUB.IO' ise alan adıdır.
_TLD = "(?:" + "|".join(_TLD_LISTE + [t.upper() for t in _TLD_LISTE]) + ")"
_ETIKET = r"(?!\d+\.)[A-Za-z0-9][A-Za-z0-9-]*"                 # salt rakamlı etiket alan adı değil ('1.tr')
LINK = re.compile(
    r"https?://\S+"                                            # açık adres
    r"|\bwww\.\S+"                                             # www.
    r"|\[[^\]]+\]\([^)]+\)"                                    # markdown bağlantısı
    r"|\b(?:t\.co|x\.com|twitter\.com|bit\.ly|youtu\.be)(?:/\S*)?"   # kısaltıcılar ve X
    # Çıplak alan adı (kesin): iki+ etiket ("cocoonish.github.io", "tcmb.gov.tr"),
    # ya da 3+ harfli TLD ("bloomberght.com"), ya da yol ("kur.de/x"). Ardından
    # sözcük karakteri gelmez — kesme ('da, ’da), uzun tire, üç nokta dahil.
    r"|(?-i:\b" + _ETIKET + r"(?:\." + _ETIKET + r")+\." + _TLD + r"(?:\.[a-z]{2})?(?:/\S*)?)(?![\w-])"
    r"|(?-i:\b" + _ETIKET + r"\.(?:" + "|".join([t for t in _TLD_LISTE if len(t) >= 3] + [t.upper() for t in _TLD_LISTE if len(t) >= 3]) + r")(?:/\S*)?)(?![\w-])"
    r"|(?-i:\b" + _ETIKET + r"\." + _TLD + r"/\S*)",
    re.I)
# Zayıf iz: tek etiket + iki harfli ülke kodu, yolsuz ("kur.de", "snb.ch"). Gerçek
# alan adı da olabilir, noktadan sonra boşluğu unutulmuş "de/da" bağlacı da —
# gönderimi durdurmaz, UYARI olarak listelenir ve yazan kişi bakar.
ZAYIF_LINK = re.compile(r"(?-i:\b" + _ETIKET + r"\.(?:" + "|".join([t for t in _TLD_LISTE if len(t) == 2] + [t.upper() for t in _TLD_LISTE if len(t) == 2]) + r"))(?![\w/-])")
_NOKTA_BENZERI = str.maketrans({"\u2024": ".", "\u3002": ".", "\uff0e": ".", "\u2025": ".."})


def _normalize(metin: str) -> str:
    """Unicode nokta benzerleri ('x．com', 'x․com') gerçek noktaya; NFKC."""
    import unicodedata
    return unicodedata.normalize("NFKC", (metin or "").translate(_NOKTA_BENZERI))


def link_var(metin: str) -> str | None:
    """Metinde link/alan adı varsa yakalanan parçayı döndürür; yoksa None."""
    for m in LINK.finditer(_normalize(metin)):
        parca = m.group(0)
        # 'TCMB.de' gibi tamamı büyük ≥3 harfli etiket + küçük iki harfli TLD:
        # boşluğu unutulmuş cümle sonu — alan adı sayılmaz.
        if re.fullmatch(r"[A-Z0-9]{3,}\.[a-z]{2}", parca):
            continue
        return parca
    return None


def zayif_link(metin: str) -> str | None:
    """Tek etiket + iki harfli ülke kodu ('kur.de'): uyarı, engel değil."""
    m = ZAYIF_LINK.search(_normalize(metin))
    if not m:
        return None
    if re.fullmatch(r"[A-Z0-9]{3,}\.[a-z]{2}", m.group(0)):
        return None
    return m.group(0)


HTML_KALINTI = re.compile(r"<[a-zA-Z/][^>]*>|&nbsp;|&amp;|&lt;|&gt;|&#\d+;|&quot;")

# Bölüm etiketi yalnız kalmış: "Gündem" ya da "Pano:" satırının ardında içerik yok.
BOS_ETIKET = re.compile(r"^(?:[A-ZÇĞİÖŞÜ][^\n:]{1,40}):\s*$", re.M)

# Kırpma bir sayının ortasında bitmiş: "…%1," "…48,2…" "…(0," gibi.
SAYIDA_KESIK = re.compile(r"(?:[\d,.%(]|\bve|\bile|\bama|\bveya)\s*…\s*$", re.M)

# Cümle sınırı — uret._CUMLE ile aynı mantık: noktadan önce rakam olmayacak,
# sonrasında büyük harf gelecek (sıra sayısı ve binlik ayracı cümle sanılmaz).
_CUMLE = re.compile(r"(?<![0-9])(?<=[.!?])\s+(?=[A-ZÇĞİÖŞÜ\"«(])")


def _site_izleri() -> tuple[str, ...]:
    """Site/bülten atfı izleri: uret.SITE_IZLERI + analiz yazıları için 'bu yazı'."""
    try:
        import uret
        temel = tuple(uret.SITE_IZLERI)
    except Exception:                                          # noqa: BLE001
        temel = ("bu sayfa", "sayfadaki", "sitede", "bülten", "yukarıda", "aşağıda")
    return temel + ("bu yazı", "bu yazıda", "yazının devamı", "yazıda ölç", "grafikte gör")


def _site_kaliplari() -> tuple:
    """'yukarıdaki tablo' gibi sayfa mobilyası kalıpları (uret ile tek tanım)."""
    try:
        import uret
        return tuple(uret.SITE_IZ_KALIPLARI)
    except Exception:                                          # noqa: BLE001
        return (re.compile(r"\b(yukarıda|aşağıda)(ki)?\s+(tablo|grafik|pano|bölüm|liste)", re.I),)


def _cumleler(metin: str) -> list[str]:
    out: list[str] = []
    for satir in metin.split("\n"):
        for c in _CUMLE.split(satir):
            c = c.strip()
            if c:
                out.append(c)
    return out


def _sade(c: str) -> str:
    return re.sub(r"[^a-z0-9çğıöşü ]", " ", c.lower()).strip()


def denetle(metin: str, tur: str = "bulten") -> tuple[list[str], list[str]]:
    """(engeller, uyarılar). Boş engel listesi = gönderilebilir."""
    engel: list[str] = []
    uyari: list[str] = []
    m = (metin or "").strip()

    # ── uzunluk
    if len(m) < EN_AZ:
        engel.append(f"metin çok kısa ({len(m)} karakter, en az {EN_AZ})")
    if len(m) > EN_COK:
        engel.append(f"metin çok uzun ({len(m)} karakter, en çok {EN_COK})")

    # ── içerik kuralları (kullanıcı kararları — 30.08 / 31.08)
    baglanti = link_var(m)
    if baglanti:
        engel.append(f"link var ({baglanti!r}) — tweetlerde HİÇ link kullanılmaz")
    zayif = zayif_link(m)
    if zayif and not baglanti:
        uyari.append(f"alan adına benzeyen parça ({zayif!r}) — link ise sil, yazım hatasıysa boşluğu koy")
    if re.search(r"\w \.(?:com|net|org|io|gov|tr)\b", m, re.I):
        uyari.append("boşluklu nokta ile alan adı benzeri parça ('x .com')")
    if EMOJI.search(m):
        engel.append(f"emoji/süsleme var: {EMOJI.search(m).group(0)!r}")
    kalinti = HTML_KALINTI.search(m)
    if kalinti:
        engel.append(f"HTML kalıntısı: {kalinti.group(0)!r}")
    # Site atfı iki kademede: "bu sayfa", "sitede", "bülten", "panoda" gibi
    # izler kesin ENGEL; "yukarıda"/"aşağıda" ise Türkçede "daha yüksek/düşük"
    # anlamına da gelir ("İTO sistematik olarak yukarıda geliyor") — o ikisi
    # gönderimi durdurmaz, kayda düşer ve yazan kişi kararını kendisi verir.
    alt = m.lower()
    belirsiz = {"yukarıda", "aşağıda"}
    izler = [iz for iz in _site_izleri() if iz in alt]
    kesin = [iz for iz in izler if iz not in belirsiz]
    if kesin:
        engel.append("siteye/bültene atıf var: " + ", ".join(repr(i) for i in kesin[:4]))
    for kalip in _site_kaliplari():                       # "yukarıdaki tablo" → kesin atıf
        k = kalip.search(m)
        if k:
            engel.append(f"sayfa mobilyasına atıf: {k.group(0)!r}")
            break
    else:
        if re.search(r"\b(yukarıda|aşağıda)\b", alt):
            uyari.append("'yukarıda/aşağıda' geçiyor — sayfaya atıf mı, seviye mi? Okuyup karar ver.")

    # ── tavsiye dili (bülten denetimiyle aynı kalıp)
    t = TAVSIYE.search(m)
    if t:
        engel.append(f"tavsiye dili: {t.group(0)!r}")

    # ── okur dili (ortak tanım)
    bulgu = okur_dili.tara(m)
    if bulgu:
        dokum = " · ".join(f"{a}: {e!r}" for a, e, _ in bulgu[:4])
        engel.append("okura değil kendimize yazan dil — " + dokum)

    # ── biçim: kırpma kalitesi, boş etiket, kapanış
    if SAYIDA_KESIK.search(m):
        engel.append("kırpma bir sayının ya da bağlacın ortasında bitmiş ("
                     + SAYIDA_KESIK.search(m).group(0).strip() + ")")
    bos = BOS_ETIKET.findall(m)
    if bos:
        engel.append("içeriksiz bölüm etiketi: " + ", ".join(repr(b) for b in bos[:3]))
    if m and not re.search(r"[.!?…»\")]$", m):
        engel.append(f"metin cümle sonuyla bitmiyor: {m[-30:]!r}")
    if not SORUMLULUK.search(m):
        engel.append("sorumluluk notu yok ('… yatırım tavsiyesi değildir.')")
    ilk = ILK_SATIR.get(tur)
    if ilk and not ilk.search(m.split("\n", 1)[0]):
        engel.append(f"{tur} gönderisi başlık satırıyla açılmıyor: {m.split(chr(10), 1)[0][:50]!r}")
    if tur == "bulten" and not re.search(r"^Gündem", m, re.M):
        uyari.append("bülten gönderisinde 'Gündem' bölümü yok")

    # ── tekrar: aynı cümle (≥ 8 kelime) iki kez
    gorulen: dict[str, int] = {}
    for c in _cumleler(m):
        s = _sade(c)
        if len(s.split()) >= 8:
            gorulen[s] = gorulen.get(s, 0) + 1
    tekrar = [s for s, n in gorulen.items() if n > 1]
    if tekrar:
        uyari.append(f"{len(tekrar)} cümle iki kez geçiyor: {tekrar[0][:70]!r}…")
    # Yakın tekrar: iki paragraf aynı SAYILARI taşıyor (yorum "fonlama %37,00'ye
    # indi" ↔ gündem "fonlama … %37,00"). Birebir cümle eşitliği bunu görmez.
    paragraflar = [p for p in re.split(r"\n\s*\n", m) if p.strip()]
    sayilar = [set(re.findall(r"%?\d+(?:[.,]\d+)+%?", p)) for p in paragraflar]
    ortak = []
    for i in range(len(sayilar)):
        for j in range(i + 1, len(sayilar)):
            kesisim = {x for x in sayilar[i] & sayilar[j] if len(x) >= 4}
            if len(kesisim) >= 2:
                ortak.append((i + 1, j + 1, sorted(kesisim)[:3]))
    if ortak:
        i, j, k = ortak[0]
        uyari.append(f"{len(ortak)} paragraf çifti aynı sayıları taşıyor (ör. {i}. ve {j}.: {', '.join(k)}) — yorum ile gündem birbirini tekrarlıyor olabilir")

    # ── tipografi
    n_eksi = len(ASCII_EKSI.findall(m))
    if n_eksi:
        uyari.append(f"sayı önünde ASCII tire {n_eksi} yerde (− ya da – bekleniyor)")
    araliklar = [m[max(0, x.start() - 8):x.end() + 8] for x in ARALIK_TIRESI.finditer(m)]
    if araliklar:
        uyari.append(f"aralık tiresi ASCII {len(araliklar)} yerde (uzun tire – bekleniyor): "
                     + ", ".join(repr(a.strip()) for a in araliklar[:3]))
    if "  " in m:
        uyari.append("çift boşluk var")
    if re.search(r"\s[,.;:!?]", m):
        uyari.append("noktalamadan önce boşluk var")

    return engel, uyari


def rapor(engel: list[str], uyari: list[str], baslik: str = "") -> str:
    satirlar = []
    if baslik:
        satirlar.append(f"── tweet denetimi: {baslik}")
    for e in engel:
        satirlar.append(f"  ✗ ENGEL  {e}")
    for u in uyari:
        satirlar.append(f"  ! UYARI  {u}")
    if not engel and not uyari:
        satirlar.append("  ✓ temiz")
    return "\n".join(satirlar)


def main() -> int:
    import argparse
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("dosya", help="tweet metni (düz metin dosyası, '-' = stdin)")
    p.add_argument("--tur", choices=("bulten", "teknik", "analiz"), default="analiz")
    a = p.parse_args()
    metin = sys.stdin.read() if a.dosya == "-" else Path(a.dosya).read_text(encoding="utf-8")
    engel, uyari = denetle(metin, a.tur)
    print(rapor(engel, uyari, a.dosya))
    return 1 if engel else 0


if __name__ == "__main__":
    raise SystemExit(main())
