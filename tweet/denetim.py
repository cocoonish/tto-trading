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
  ENGEL  gönderim durur (tavsiye dili, link, hashtag/cashtag/@, emoji ve
         matematik kalın harf, HTML kalıntısı, site atfı, satır sonunda "…",
         sayıda ya da sıra sayısında kesik, kapanmamış parantez/tırnak, boş
         bölüm etiketi, uzunluk, okur dili, sorumluluk notu eksik)
  UYARI  loga yazılır, gönderim sürer (tekrar eden cümle, ASCII eksi, ters
         işaret sırası "%+", yüzde işaretsiz oran, ":" ile biten paragraf,
         bülten gönderisinin ilk 280 karakterinde ölçüm yok, düzeltme
         metninde sayfa yapısı sözcüğü, çift boşluk)

Tavsiye, okur dili ve site izi NFKC'ye normalleştirilmiş metinde taranır.

Kullanım:
    engel, uyari = denetle(metin, tur)      # tur: bulten | analiz | duzeltme | ozel
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
# analiz: "Analiz — 1 Eylül 2026".
ILK_SATIR = {
    "bulten": re.compile(r"^(Sabah Notu|Haftaya Bakış) — \d{1,2} [A-ZÇĞİÖŞÜ][a-zçğıöşü]+ \d{4}"),
    "analiz": re.compile(r"^Analiz — \d{1,2} [A-ZÇĞİÖŞÜ][a-zçğıöşü]+ \d{4}"),
    # Düzeltme yanıtı (05.10.2026): yayımlanmış bir gönderinin altına, yazarın
    # kendi metniyle — bkz. tweet/duzeltme.py.
    "duzeltme": re.compile(r"^Düzeltme — \S"),
}

# Alt sınır türe göre: bir düzeltme yanıtı "neyin, neyden, neye" diye üç kısa
# öğe taşır ve 200 karakterin altında kalması DOĞALDIR. 200'lük taban
# düzeltmelerin altıda birini (ölçüldü: 85 kaydın 14'ü) sahte ENGEL'e sokardı.
EN_AZ_TUR = {"duzeltme": 60}

# Düzeltme metninde sayfa yapısı sözcükleri (gösterge şeridi, bölüm, satır…)
# okura sitenin iç düzenini anlatır; X okurunun elinde o sayfa yok. UYARI:
# "satır" ve "bölüm" piyasa anlamıyla da geçebilir, yazan kişi bakar.
SAYFA_YAPISI = re.compile(
    r"(?<![0-9A-Za-zÇĞİIÖŞÜçğıiöşü])(?:gösterge şerid|bölüm|satır|söz defter|kurumsal gündem)", re.I)

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
                   "\u2B00-\u2BFF\u203C\u2049\u2122\u2139\u3030\u303D\u3297\u3299\u00A9\u00AE\u2022\uFE0F⭐⬆⬇✅❌"
                   # Matematik alfanümerik (U+1D400–1D7FF): "𝐚𝐥ı𝐧", "𝗝𝗨𝗦𝗧 𝗜𝗡" — kalın/italik
                   # harf süsü. Hem süslemedir hem de ham metinde tavsiye ve okur
                   # dili kalıplarını DELER; o taramalar ayrıca NFKC'de koşar.
                   "\U0001D400-\U0001D7FF]")

# TIKLANIR X ÖĞELERİ (05.10.2026 kararı: hashtag, cashtag ve bahsetme de yasak).
# Link DEĞİLDİR: mesajları ayrı tutulur ki gönderim kilidi "link" diye yanlış
# teşhis koymasın. Cashtag twitter-text tanımını izler — 1–6 harf, isteğe bağlı
# ".xx"/"_xx" eki; rakamlı ($XU100) ya da para birimi ("107,63 $") tanınmaz.
# "$r_t$" gibi bir eşleşme ayrıca formül (KaTeX) kalıntısıdır.
HASHTAG = re.compile(r"(?<![\w&])#[^\s#]")
CASHTAG = re.compile(r"(?<![\w$])\$[A-Za-z]{1,6}(?:[._][A-Za-z]{1,2})?(?![A-Za-z0-9])")
BAHSETME = re.compile(r"(?<![\w@.])@[A-Za-z0-9_]{2,}")

# İşaret sırası: sözleşme "−%1,88" / "+%0,4" (ortak/bicim.py); "%+20,9" ters.
# UYARI: sayı doğru, yazımı kusurlu (biçim sızıntısı yayını durdurmaz).
TERS_ISARET = re.compile(r"%[+−-]\d")

# Yüzde işaretsiz "aylık/yıllık + ondalık" ("yıllık 31,51"). Önündeki vade adı
# ("10 yıllık 4,12", "iki yıllık") ve arkasındaki birim (bp, baz puan, puan, σ,
# yıl, kat, sonradan yazılmış %) muaf. UYARI.
ORAN_ISARETSIZ = re.compile(r"\b(aylık|yıllık)\s+([+−-]?\d+,\d+)(?![\d,])", re.I)
_SAYI_SOZCUGU = {"bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz", "on",
                 "yirmi", "otuz", "kırk", "elli"}
_BIRIM_ARKA = re.compile(r"\s*(?:bp\b|baz\s+puan|puan|σ|yıl|kat\b|%)", re.I)

# Satır sonunda sıra sayısında kesik ("TCMB'nin 35."): yüzde ve ondalık
# içermeyen 1–3 haneli tam sayı. "…%5,089." ile biten satır ENGEL ALMAZ; "6/7."
# bir oran yazımıdır. Endeks adı ("BIST 100.", "S&P 500.") meşru bir cümle
# sonudur — önceki sözcük endeks adıysa muaf.
# ":" geriye bakışta: saatle biten meşru cümle ("TSİ 14:00.") kesik değildir.
SIRA_KESIK = re.compile(r"(?<![%\d,.+−/:-])\b\d{1,3}\.$", re.M)
_ENDEKS_ADI = {"bist", "s&p", "nikkei", "ftse", "stoxx", "dax", "cac", "msci", "russell",
               "nasdaq", "ibex", "kospi", "asx", "smi", "aex", "mib", "topix", "dow"}

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

# Kırpma bir sayının ortasında bitmiş: "…%1," "…48,2…" "…(0," gibi; birimle
# biten sayı da ("+35 bp…", "0,4 puan…", "2,1σ…", "(−0,3…") aynı kesiktir.
SAYIDA_KESIK = re.compile(r"(?:[\d,.%(]|\b(?:bp|puan|ve|ile|ama|veya)|σ|\([^()\n]*\d[^()\n]*)\s*…\s*$", re.M)

# Üreticiler "…" ÜRETMEZ (05.10.2026: tam birim seçimi; sığmayan birim düşer).
# Satır sonundaki her "…" bu yüzden bir kırpma izidir — sayıda olsun olmasın.
SATIR_SONU_UC_NOKTA = re.compile(r"…[ \t]*$", re.M)

# Kapanmamış parantez ya da tırnak — bir cümlenin ortasından kesildiğinin izi
# ("GSYH (II."). Tırnak olarak yalnız " “” «» sayılır; Türkçe kesme işareti
# (') sayılmaz. Satır başına sorulur: gönderinin satırları ayrı birimlerdir.

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


def acik_kalan(satir: str) -> str | None:
    """Satırda kapanmamış parantez ya da tırnak varsa onu döndürür.

    Parantez derinlikle sayılır: ")" açık parantez yokken gelirse ("1)" gibi
    sıralama) yok sayılır — kapanmamış açık parantezi örtmesin. Düz tırnak (")
    tek sayıda geçiyorsa açık kalmıştır; “” ve «» çift olarak sayılır."""
    derinlik = 0
    for ch in satir:
        if ch == "(":
            derinlik += 1
        elif ch == ")" and derinlik:
            derinlik -= 1
    if derinlik:
        return "("
    if satir.count('"') % 2:
        return '"'
    if satir.count("“") > satir.count("”"):
        return "“"
    if satir.count("«") > satir.count("»"):
        return "«"
    return None


def sira_kesik(metin: str) -> str | None:
    """Satır sonunda sıra sayısında kesilmiş cümle ("…TCMB'nin 35."); yoksa None.
    Önceki sözcük bir endeks adıysa ("BIST 100.") meşru cümle sonudur."""
    for m in SIRA_KESIK.finditer(metin):
        satir_basi = metin.rfind("\n", 0, m.start()) + 1
        onceki = metin[satir_basi:m.start()].rstrip().split()
        if onceki and onceki[-1].strip("(\"'“«").lower() in _ENDEKS_ADI:
            continue
        return metin[max(satir_basi, m.start() - 25):m.end()]
    return None


def oran_isaretsiz(metin: str) -> list[str]:
    """Yüzde işareti olmadan yazılmış aylık/yıllık oran ("yıllık 31,51")."""
    out = []
    for m in ORAN_ISARETSIZ.finditer(metin):
        onceki = metin[:m.start()].rstrip().split()
        son = (onceki[-1].replace("İ", "i").replace("I", "ı").lower().strip("(")
               if onceki else "")
        if re.fullmatch(r"[\d.,]+(?:[–-]\d+)?", son) or son in _SAYI_SOZCUGU:
            continue                                          # "10 yıllık", "iki yıllık" → vade adı
        if _BIRIM_ARKA.match(metin, m.end()):
            continue                                          # "yıllık 4,1 bp" → fark birimli
        out.append(m.group(0))
    return out


def tiklanir_oge(metin: str) -> str | None:
    """Hashtag, cashtag ya da @ bahsetme — X'te tıklanır öğe; yoksa None."""
    for kalip in (HASHTAG, CASHTAG, BAHSETME):
        m = kalip.search(metin)
        if m:
            return m.group(0)
    return None


def _olcum_sayilari(metin: str) -> set[str]:
    """Ölçüm sayıları — üreticinin tanımıyla (uret._sayilar) TEK tanım."""
    try:
        import uret as _ur
        return _ur._sayilar(metin)
    except Exception:                                          # noqa: BLE001
        return set(re.findall(r"%?\d+(?:[.,]\d+)+%?|%\d+|\b\d+\s*(?:bp|baz puan|puan)\b", metin))


def denetle(metin: str, tur: str = "bulten") -> tuple[list[str], list[str]]:
    """(engeller, uyarılar). Boş engel listesi = gönderilebilir."""
    engel: list[str] = []
    uyari: list[str] = []
    m = (metin or "").strip()

    # Tavsiye, okur dili ve site izi NFKC'de taranır: "Dolar 𝐚𝐥ı𝐧." ham metinde
    # kalıbı deler, normalleştirilmiş metinde "Dolar alın." olur.
    n = _normalize(m)

    # ── uzunluk
    en_az = EN_AZ_TUR.get(tur, EN_AZ)
    if len(m) < en_az:
        engel.append(f"metin çok kısa ({len(m)} karakter, en az {en_az})")
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
    oge = tiklanir_oge(n)
    if oge:
        formul = oge.startswith("$") and re.search(re.escape(oge) + r"[^\s$]*\$", n)
        engel.append(f"tıklanır X öğesi ({oge!r}) — hashtag, cashtag ve @ bahsetme kullanılmaz"
                     + ("; formül (KaTeX) kalıntısı olabilir" if formul or "_" in oge else ""))
    kalinti = HTML_KALINTI.search(m)
    if kalinti:
        engel.append(f"HTML kalıntısı: {kalinti.group(0)!r}")
    # Site atfı iki kademede: "bu sayfa", "sitede", "bülten", "panoda" gibi
    # izler kesin ENGEL; "yukarıda"/"aşağıda" ise Türkçede "daha yüksek/düşük"
    # anlamına da gelir ("İTO sistematik olarak yukarıda geliyor") — o ikisi
    # gönderimi durdurmaz, kayda düşer ve yazan kişi kararını kendisi verir.
    alt = n.lower()
    belirsiz = {"yukarıda", "aşağıda"}
    # Sol sözcük sınırı üreticiyle TEK tanım (uret.SOL_SINIR): "kapasitede"
    # içindeki "sitede" bir site atfı değildir.
    try:
        import uret as _ur
        sol = _ur.SOL_SINIR
    except Exception:                                          # noqa: BLE001
        sol = r"(?<![0-9A-Za-zÇĞİIÖŞÜçğıiöşü])"
    izler = [iz for iz in _site_izleri() if re.search(sol + re.escape(iz), alt)]
    kesin = [iz for iz in izler if iz not in belirsiz]
    if kesin:
        engel.append("siteye/bültene atıf var: " + ", ".join(repr(i) for i in kesin[:4]))
    for kalip in _site_kaliplari():                       # "yukarıdaki tablo" → kesin atıf
        k = kalip.search(n)
        if k:
            engel.append(f"sayfa mobilyasına atıf: {k.group(0)!r}")
            break
    else:
        if re.search(r"\b(yukarıda|aşağıda)\b", alt):
            uyari.append("'yukarıda/aşağıda' geçiyor — sayfaya atıf mı, seviye mi? Okuyup karar ver.")

    # ── tavsiye dili (bülten denetimiyle aynı kalıp)
    t = TAVSIYE.search(n)
    if t:
        engel.append(f"tavsiye dili: {t.group(0)!r}")

    # ── okur dili (ortak tanım)
    bulgu = okur_dili.tara(n)
    if bulgu:
        dokum = " · ".join(f"{a}: {e!r}" for a, e, _ in bulgu[:4])
        engel.append("okura değil kendimize yazan dil — " + dokum)

    # ── biçim: kırpma kalitesi, boş etiket, kapanış
    if SAYIDA_KESIK.search(m):
        engel.append("kırpma bir sayının ya da bağlacın ortasında bitmiş ("
                     + SAYIDA_KESIK.search(m).group(0).strip() + ")")
    elif SATIR_SONU_UC_NOKTA.search(m):
        satir = m[:SATIR_SONU_UC_NOKTA.search(m).end()].rsplit("\n", 1)[-1]
        engel.append(f"satır '…' ile bitiyor — gönderi tam birimlerden kurulur: {satir[-40:]!r}")
    for satir in m.split("\n"):
        acik = acik_kalan(satir)
        if acik:
            engel.append(f"kapanmamış {acik!r} — cümle ortasından kesilmiş: {satir[-50:]!r}")
            break
    sk = sira_kesik(m)
    if sk:
        engel.append(f"satır sıra sayısında kesilmiş: {sk!r}")
    for p in re.split(r"\n\s*\n", m):
        son = p.strip().rsplit("\n", 1)[-1]
        if son.endswith(":") and not BOS_ETIKET.fullmatch(son):
            uyari.append(f"paragraf ':' ile bitiyor — ardındaki birim düşmüş olabilir: {son[-50:]!r}")
            break
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
    # Gündem yalnız GÜNLÜK gönderide aranır: haftalık iskelet (05.10.2026)
    # senaryolar, takvim ve karneyle kurulur, konu satırı taşımaz.
    if tur == "bulten" and m.startswith("Sabah Notu") and not re.search(r"^Gündem", m, re.M):
        uyari.append("bülten gönderisinde 'Gündem' bölümü yok")
    # İLK 280: okurun çoğu "daha fazla göster"e basmadan karar verir; o alan bir
    # ölçüm taşımalı. Ölçü üreticinin "ölçüm" tanımıyla aynı (uret._sayilar).
    if tur == "bulten" and not _olcum_sayilari(m[:280]):
        uyari.append("ilk 280 karakterde ölçülmüş sayı yok — manşet ya da ilk madde bir ölçüm taşımalı")
    if tur == "duzeltme":
        y = SAYFA_YAPISI.search(n)
        if y:
            uyari.append(f"düzeltme metni sayfa yapısını anıyor ({y.group(0)!r}) — X okurunun elinde o sayfa yok")

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
    ters = TERS_ISARET.findall(m)
    if ters:
        uyari.append(f"işaret yüzden sonra {len(ters)} yerde ({ters[0]!r}) — sözleşme '−%1,88', '+%0,4'")
    isaretsiz = oran_isaretsiz(m)
    if isaretsiz:
        uyari.append(f"yüzde işaretsiz oran {len(isaretsiz)} yerde ({isaretsiz[0]!r}) — '%' önde yazılır")
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
    p.add_argument("--tur", choices=("bulten", "analiz", "duzeltme", "ozel"), default="analiz")
    a = p.parse_args()
    metin = sys.stdin.read() if a.dosya == "-" else Path(a.dosya).read_text(encoding="utf-8")
    engel, uyari = denetle(metin, a.tur)
    print(rapor(engel, uyari, a.dosya))
    return 1 if engel else 0


if __name__ == "__main__":
    raise SystemExit(main())
