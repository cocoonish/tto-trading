#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tweet zinciri ÜRETİMİ — yazılmış bültenlerden, deterministik.

Zincir metni yalnız YAYIMLANMIŞ içerikten kurulur: günlük/haftalık bültenin
yazı katmanından geçmiş JSON'u (analiz gönderisi tweet/analiz.py'de). Haftalık
teknik analiz 27.09.2026 sayısıyla sona erdi; onun zinciri 01.10.2026'da
çıkarıldı (kullanıcı kararı), defterdeki ve arşivdeki kayıtları duruyor. Burada yeni hüküm ÜRETİLMEZ — özet cümleleri yazı katmanının kendi
cümleleridir, sayılar ölçümün kendi sayılarıdır. Uydurma yok, sosyal medyada
da yok.

Gönderim ayrı (tweet/gonder.py); bu modül ağa çıkmaz, duman sınaması bunu
sentetik veriyle çağırır.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent
BULTENLER = KOK / "site" / "src" / "data" / "bulten"

# Hesap X Premium: 280 sınırı yok, içerik TEK tweet olarak atılır (zincir
# değil). Sınırlar teknik değil editoryal: bölüm başına kırpma + toplam tavan.
# Tavan TEK yerde durur; analiz.py ve denetim.py buradan okur.
TEK_TAVAN = 3800            # tek tweetin toplam üst sınırı (okunurluk)
YORUM_SINIR = 1200          # anlatı gövdesi (bültenin 'okuması'ndan)
GUNDEM_PARCA = 260          # gündem bölümü başına
GUNDEM_SINIR = 1250         # gündem bloğunun tamamı
BEKLENTI_SINIR = 600        # takvim: "Bugün…" paragrafı + "Beklenen:" birlikte
BEKLENTI_TABAN = 250        # "Bugün…" taşındıktan sonra "Beklenen:"e kalan en az pay
# Biçim 3 (sabah notu): olguların TEK evi `ozet.ne_oldu` maddeleridir ve okuma
# onları yeniden saymaz — gönderi maddelerle açılır, okuma ondan sonra ve daha
# kısa gelir (01.10.2026 incelemesi: gövde yalnız okumadan kurulunca gönderide
# TMSF, ÖTV ve PCE rakamı hiç geçmiyordu).
# MADDELER ÖNCELİKLİDİR (05.10.2026): madde bloğunun ayrı tavanı YOK. Eski
# döngü ilk taşan maddede duruyordu ve biçim 3'ün üç gönderisinin üçünde de
# madde düştü (02.10 4/5 · 04.10 7/10 · 05.10 4/5); düşenlerin beşi de Türkiye
# dışıydı. Taşma artık birim öncelikleriyle çözülür (`_sigdir`): önce
# olağandışı satırı, sonra pano, sonra gündem satırları; maddeler en son.
MADDE_SINIR = 330           # "Bu sabah" maddesi başına
# Okumanın payı "Neye bakılacak" eşik bloğuna (en çok 2 × 170) yer açmak için
# 650'den indi: blok kendi bütçesini mevcut bütçelerden alır, `_kapat` hiçbir
# koşulda "Beklenen"i kırpmaz.
OKUMA_SINIR_3 = 480         # biçim 3'te okuma
GUNDEM_SINIR_3 = 800        # biçim 3'te konu bölümleri
# HAFTALIK KİP: iskelet ve blok bütçeleri `_haftalik3`ün yanında; maddeler
# kalan payı alır (dinamik pay).
MADDE_SINIR_HAFTA = 250     # "Bu hafta" maddesi başına

AYLAR = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
         "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]


def _duz(metin: str) -> str:
    """HTML → düz metin: etiketler söker, varlıkları çözer, boşluk normalleştirir.
    'S&amp;P 500' çözülmeden tweete sızıyor ve HTML kalıntısı engeli günün
    gönderisini düşürüyordu (28.08 ölçüldü)."""
    import html as _html
    m = re.sub(r"<[^>]+>", " ", metin or "")
    m = _html.unescape(m)
    m = re.sub(r"\s+", " ", m).strip()
    # Etiket sökümü kapanış etiketinin yerine boşluk bırakır: "<b>28,2 bp</b>, 10"
    # → "28,2 bp , 10" (14.09 gönderisi bu hâlde gitti; kapı "noktalamadan önce
    # boşluk" diyor). Analizin `_duz`ü aynı kuralı taşıyordu, bülteninki taşımıyordu.
    m = re.sub(r"%\s+(?=[\d−+])", "%", m)
    m = re.sub(r"\s+([,.;:!?)])", r"\1", m)
    return re.sub(r"\(\s+", "(", m)


# Tweet KENDİ BAŞINA durur: siteye link verilmediği gibi oradaki bültene ATIF da
# yapılmaz (31.08 geri bildirimi). Bültenin kendi metni site bağlamında yazılır —
# "bu sayfadaki piyasa fotoğrafı", "bu bültenin takip ettiği", "ayrıntısı
# jeopolitik bölümünde" gibi. Bu izi TAŞIYAN CÜMLE düşürülür; cümleyi yeniden
# yazmak uydurma olurdu, kırpmak değil.
SITE_IZLERI = (
    "bu sayfa", "sayfadaki", "sayfanın", "sayfamız", "sitede", "sitemiz",
    "bu bülten", "bültenimiz", "bültende", "bültenin ", "bu sabah notu",   # öz-atıf; "TCMB haftalık bülteni" düşmez
    "fotoğraf",                              # 'piyasa fotoğrafı' sitedeki tablo
    "bu bölüm", "bölümdeki", "bölümünde",    # bölümler arası çapraz atıf
    "panoda", "panosunda", "panosunun",      # rejim / gösterge panosu
    "tabloda", "tablodaki", "buradaki not",
)
# "yukarıda/aşağıda" Türkçede "daha yüksek/düşük" da demek ("İTO yukarıda
# geliyor"); yalnız SAYFA bağlamında iz sayılır. Eski hâli bu iki sözcüğü
# koşulsuz düşürüyordu ve gerçek bilgi taşıyan cümleler sessizce gidiyordu.
SITE_IZ_KALIPLARI = (
    re.compile(r"\b(yukarıda|aşağıda)(ki)?\s+(tablo|grafik|pano|bölüm|liste|şerit|"
               r"anlat|veril|yazıl|açık|göster|ayrıntı)", re.I),      # açıkla·açıkça
)


# İZ SOL SÖZCÜK SINIRINDA ARANIR. Ham alt dize araması bir izi BAŞKA bir
# sözcüğün ortasında yakalıyordu: "sitede" izi "kapasitede" sözcüğünün içinde
# geçiyor ve kapasite kullanım oranını anlatan MEŞRU bir cümle her ay sessizce
# düşüyordu (22.09.2026'da ölçüldü — "kapasitede sınırlı bir toparlanma"
# cümlesi bu yüzden gönderiye hiç girmedi). Aynı kusur "sitemiz" ↔
# "kapasitemiz" ve "sitede" ↔ "üniversitede" çiftlerinde de var. İzlerin
# TAMAMI sözcük başında duran ifadeler ("sayfadaki", "bültende", "panoda"),
# yani sol sınır şartı hiçbir gerçek izi düşürmez — yalnız sözcük ortasındaki
# tesadüfi eşleşmeyi keser. Sağ tarafa sınır KONMAZ: Türkçe ekli yazımı
# ("bültenin", "panosunda") tam da yakalanmak istenen biçimdir.
# SOL SINIR TEK TANIM: gönderim kapısı (tweet/denetim) aynı sınırı kullanır.
# Kapı izleri ham alt dizeyle arıyordu ve "kapasitede", "üniversitede",
# "kapasitemiz" geçen meşru bir gönderiyi ENGEL'le durduruyordu — üretici aynı
# cümleyi sözcük sınırıyla meşru sayıp gönderiye koyduğu hâlde (01.10.2026).
SOL_SINIR = r"(?<![0-9A-Za-zÇĞİIÖŞÜçğıiöşü])"
_SITE_IZ_RE = re.compile(
    SOL_SINIR + r"(?:" + "|".join(re.escape(i) for i in SITE_IZLERI) + ")")


def _site_izi_var(cumle: str) -> bool:
    alt = cumle.lower()
    return bool(_SITE_IZ_RE.search(alt)) or any(k.search(cumle) for k in SITE_IZ_KALIPLARI)

# ── CÜMLE BİRİMİ (05.10.2026) ────────────────────────────────────────────────
# Gönderi hiçbir koşulda "…" üretmez: seçim birimi madde, TAM cümle ya da
# bölümün tamamıdır; sığmayan birim bütünüyle düşer, ortasından kesilmez.
# Kesik bir cümle okura eksik bir hüküm sunar ve eksik olduğunu da göstermez.
#
# Cümle sınırı TEK tanım (`_KIRP_CUMLE` + `cumleler`); `_site_disi` de aynı
# bölücüyü kullanır. İlk kural "noktadan önce rakam olmayacak" diyordu ve
# rakamla biten her cümleyi ("…%5,089. Aynı gün…") ve rakamla başlayan her
# cümleyi ("açıldı. 5, 10 yıllık…") görmüyordu: bülten metinlerinde 336 aday
# sınırın yalnız %24'ü ondalıklıydı ve satır, sınır bulamadığı için kelime
# ortasından kesiliyordu. Sıra sayısını ("38. haftanın") SAĞDAKİ küçük harf
# ayırır; binlik ayracı ("1.000") boşluk taşımadığı için zaten sınır değildir.
# SIRA SAYISI + ÖZEL AD (05.10.2026 incelemesi): "yılın 7. PPK toplantısı",
# "Netflix 3. Çeyrek" — sağdaki büyük harf sıra sayısını cümle sonu sanıyor ve
# satıra "…sıradaki sınav yılın 7." gibi KESİK bir hüküm giriyordu (eski
# bölücü rakamdan sonra hiç bölmüyordu; 1–3 haneli tam sayı yeniden yarattı).
# Belirsizlik BİRLEŞTİRMEYLE çözülür: nokta 1–3 haneli çıplak tam sayıyı
# kapatıyor ve ardından büyük HARF geliyorsa sınır sayılmaz. Birleşik birim
# tam cümleler taşır, kesik üretemez. Ondalık ("%5,089. Aynı"), saat ("16:45.
# Türkiye'de") ve rakamla süren cümle ("sayısı 61. 2 yıllık") bölünmeye devam
# eder. Ölçüldü: 38 bülten ve 14 analiz gönderisinde 0 değişiklik.
# Bir sınır ancak parantez ve tırnak DENGELİ bir parçayı kapatıyorsa sınırdır:
# "GSYH (II. Çeyrek)" içindeki nokta cümle sonu değildir — orada kesmek okura
# kapanmamış bir parantez bırakırdı.
_KIRP_CUMLE = re.compile(r"[.!?](?=\s+[A-ZÇĞİÖŞÜ\"«“(0-9%−])")
_KISALTMA = {"vb", "vs", "ör", "örn", "bkz", "yy", "dr", "prof", "doç", "st", "no", "sn"}
_SIRA_SAYISI = re.compile(r"(?<![%\d,.+−/:-])\b\d{1,3}$")


def _dengeli(s: str) -> bool:
    return (s.count("(") == s.count(")") and s.count('"') % 2 == 0
            and s.count("“") == s.count("”") and s.count("«") == s.count("»"))


def _birim_araliklari(m: str) -> list[tuple[int, int]]:
    """Metni TAM cümlelere böler; (başlangıç, bitiş) aralıkları, özgün metinde."""
    out: list[tuple[int, int]] = []
    bas = 0
    for c in _KIRP_CUMLE.finditer(m):
        onceki = re.search(r"([^\W\d_]+)$", m[:c.start()])
        if c.group(0) == "." and onceki:
            soz = onceki.group(1)
            if soz.lower() in _KISALTMA or (len(soz) == 1 and soz.isupper()):
                continue                      # kısaltma ya da baş harf ("A. Yılmaz")
        if c.group(0) == "." and _SIRA_SAYISI.search(m[:c.start()]):
            sag = m[c.end():].lstrip()[:1]
            if sag.isalpha() and sag.isupper():
                continue                      # sıra sayısı + özel ad ("yılın 7. PPK")
        if not _dengeli(m[bas:c.end()]):
            continue                          # parantez/tırnak içindeki nokta
        out.append((bas, c.end()))
        bas = c.end()
        while bas < len(m) and m[bas].isspace():
            bas += 1
    if bas < len(m) and m[bas:].strip():
        out.append((bas, len(m)))
    return out


def cumleler(metin: str) -> list[str]:
    """Metnin TAM cümleleri (gönderinin seçim birimi)."""
    m = (metin or "").strip()
    return [m[a:z].strip() for a, z in _birim_araliklari(m) if m[a:z].strip()]


# Bir cümle düşünce ondan SONRAKİ cümle öksüz kalabilir: "İkincisi aynı
# dosyanın..." ya da "Hafta sonu bu soruya..." — göndergesi silinmiş bir metin
# tweette anlamsız durur. Öncesi düşmüşse ve cümle ilk sözcüklerinde geriye
# atıf taşıyorsa o da düşer; zincirleme sürer.
_ANAFORA = {"bu", "bunu", "bunun", "buna", "bunlar", "bundan", "o", "onu",
            "onun", "aynı", "ikincisi", "üçüncüsü", "böylece", "dolayısıyla",
            "ayrıca", "oysa", "buradaki", "yani", "söz", "sebebi", "nedeni"}


def _anaforik(c: str) -> bool:
    bas = [w.strip('"\'(),;:.') for w in c.lower().split()[:6]]
    return any(w in _ANAFORA for w in bas)


# Düşen cümleler GÖRÜNÜR tutulur: gonder.py kuru ve gerçek koşuda listeler,
# denetim oranı ölçer. Sessizce silinen bir cümle, yazı katmanının bir daha
# aynı hatayı yapmasına yol açar; görünen cümle geri bildirimdir. Bütçeye
# sığmayıp düşen birim de buraya yazılır.
DUSEN: list[tuple[str, str]] = []


def _site_disi(metin: str, bolum: str = "") -> str:
    """Siteye/bültene atıf yapan cümleleri ve öksüz kalan devamlarını düşürür."""
    kalan, onceki_dustu = [], False
    for c in cumleler(metin):
        dus = _site_izi_var(c) or (onceki_dustu and _anaforik(c))
        if dus:
            onceki_dustu = True
            DUSEN.append((bolum, c.strip()))
            continue
        onceki_dustu = False
        kalan.append(c)
    return re.sub(r"\s+", " ", " ".join(kalan)).strip()


# Biçim 2 (arşiv): gündem katmanı 12 bölüm; tweete haber değeri en yüksek beşi
# girer.
GUNDEM_BOLUMLERI = (
    ("kilit", "Kilit gelişme"),
    ("tr_makro", "Türkiye makro"),
    ("tr_politika", "Türkiye politika"),
    ("global_politika", "Jeopolitik"),
    ("global_makro", "Küresel makro"),
)


def _bicim3_bolumleri(kip: str = "gunluk") -> tuple[tuple[str, str], ...]:
    """Biçim 3: gündem satırları bülten kayıt defterinden (bulten/ayar.py,
    YAZI_BOLUMLERI_3 → `tweet` etiketi), kipin okuma sırasıyla. İleriye bakış
    (`takvim`) ayrı satırda "Beklenen:" olarak girer."""
    def etiket(y):
        return (y.haftalik_tweet or y.tweet) if kip == "haftalik" else y.tweet
    return tuple((y.id, etiket(y)) for y in _bulten_ayar().kip_bolumleri(kip)
                 if etiket(y) and y.id != "takvim")


def _bulten_ayar():
    """bulten/ayar.py DOSYA YOLUNDAN yüklenir, sys.path'e bulten/ EKLENMEZ.
    İlk yazım bulten/'ü yolun başına koyuyordu: tweet sürecinde sonradan
    yapılan `import denetim` (ve `import uret`) bültenin aynı adlı modülüne
    düşüyordu — duman sınaması bunu "denetim.denetle yok" diye gösterdi
    (01.10.2026). tweet/denetim.py aynı tuzağı yol sırasıyla adıyla anar."""
    import importlib.util as _iu
    import sys as _sys
    ad = "_tto_bulten_ayar"
    if ad not in _sys.modules:
        spec = _iu.spec_from_file_location(ad, KOK / "bulten" / "ayar.py")
        mod = _iu.module_from_spec(spec)
        _sys.modules[ad] = mod          # dataclass çözümü modülü sys.modules'ta arar
        spec.loader.exec_module(mod)
    return _sys.modules[ad]


def gundem_bolumleri(b: dict) -> tuple[tuple[str, str], ...]:
    if int(b.get("surum") or 2) >= 3:
        return _bicim3_bolumleri("haftalik" if b.get("haftalik") else "gunluk")
    return GUNDEM_BOLUMLERI


# Haftalık bölümler kalın başlıklı ALT BÖLÜMLERDEN kurulur (<h3>); gönderi
# satırı bölümün girişini aldığı için başlık metni cümleye yapışırdı
# ("TL faizi ve DİBS Gösterge getiri …"). Alt başlık gönderiye girmez.
ALT_BASLIK = re.compile(r"<h3\b[^>]*>.*?</h3>", re.I | re.S)


def _kirp(metin: str, sinir: int) -> str:
    """Sınıra sığan en uzun TAM cümle önekini döndürür; hiçbir cümle sığmazsa
    BOŞ döner — birim bütünüyle düşer. "…" ÜRETMEZ (05.10.2026).

    Eski hâli üç kademeliydi (cümle → yan tümce → kelime + "…") ve arşivdeki 40
    gönderinin 21 satırı "…" ile bitiyordu; 04.10 haftalık gönderisi ana
    senaryoyu "…sürdürür…" diye, bir Türkiye satırını açık parantezle kesmişti.
    Kesik bir cümle eksik bir hükümdür ve okur eksik olduğunu göremez.
    Özgün metnin satır sonları korunur (öneki özgün metinden keser)."""
    m = (metin or "").strip()
    if len(m) <= sinir:
        return m
    kes = 0
    for _a, z in _birim_araliklari(m):
        if z > sinir:
            break
        kes = z
    return m[:kes].rstrip()


# ── birim seçimi: satır, okuma, etiketli satır ──────────────────────────────

# Satır SAYI taşımıyorsa bir sonraki cümle de alınır ("Eğrinin biçimi.
# Haftanın en belirgin değişimi…" — 04.10'da Türkiye satırı sayısız kaldı).
# Etiketli satır (ana senaryo, takvim günü) için bütçe ilk cümle kadar ESNER;
# tavan bu.
SATIR_ESNEK = 330

# KAYNAK ÖNCELİĞİ (U7): gündem satırında kaynağı adıyla anan cümle bütçe içinde
# önceliklidir. 05.10'da Türkiye satırı 253 karakterde kesildi ve "Bloomberg
# HT'ye göre…" cümlesi, Küresel satırı ise "Bloomberg ve Reuters'a göre …
# (FXStreet)" cümlesini kaybetti — linksiz bir gönderide güveni kaynağın adı
# taşır. Kaynak sezgisi bir KAPI değil bir sıralama ölçütüdür; yanlış pozitifi
# yalnız hangi cümlenin önce seçileceğini değiştirir. Piyasa adıyla çakışan
# yayın adı listede yok ("Nikkei" bir endekstir, "Nikkei Asia" yayındır).
KAYNAK_ADLARI = (
    "Bloomberg", "Bloomberg HT", "Reuters", "AA Finans", "Anadolu Ajansı", "CNBC", "CNBC-e",
    "Financial Times", "FT", "Wall Street Journal", "WSJ", "Nikkei Asia", "Kyodo",
    "Xinhua", "Caixin", "Euronews", "IEA", "Kpler", "Argus", "Platts", "FXStreet",
    "investingLive", "Foreks", "BusinessToday", "Diken", "OilPrice", "BLS", "AP", "AFP",
    "Politico", "Axios", "Handelsblatt", "Les Echos", "Le Monde", "Ekonomim",
    "Insights Global", "S&P Global", "Moody's", "Fitch",
)
_AYLAR_KUCUK = {a.lower() for a in AYLAR if a}
_KAYNAK_RE = re.compile(
    r"(?<![\w])(?:" + "|".join(re.escape(k) for k in sorted(KAYNAK_ADLARI, key=len, reverse=True))
    + r")(?![\w])")
_GORE_RE = re.compile(r"\b([A-ZÇĞİÖŞÜ][\w&.-]*)['’](?:y?[ae]|n[ae]|n[ıiuü]n)\s+(?:göre|aktardığına)")


def _kaynakli(c: str) -> bool:
    if _KAYNAK_RE.search(c):
        return True
    return any(m.group(1).lower() not in _AYLAR_KUCUK for m in _GORE_RE.finditer(c))


def _satir_sec(metin: str | list[str], sinir: int, esnek: int | None = None,
               kaynak_oncelik: bool = False, n_ilk: int | None = None) -> str:
    """Bir satırın TAM cümlelerini seçer; özgün sıra korunur.

    İlk cümle her zaman satırın açılışıdır; `esnek` verilmişse ilk cümle o
    sınıra kadar sığar (etiketli satır düşmesin). İlk cümle sayı taşımıyorsa
    bir sonraki cümle de alınır. Sonra bitişik cümleler sınıra kadar eklenir;
    `kaynak_oncelik` varsa kaynağı adıyla anan cümleler önce denenir (atlanan
    bir cümleden sonra geriye atıflı cümle seçilmez). Girdi bir birim listesi
    olabilir (`_html_birimleri`: kalın etiket ilk cümlesine bağlı).

    KAYNAK ÖNCELİĞİ İLK PARAGRAFLA SINIRLIDIR, KAYNAKSIZ SEÇİM BİTİŞİKTİR
    (05.10.2026 incelemesi). Öncelik bölümün TAMAMINDAKİ kaynaklı cümleleri
    öne alıyor, sığmayan kaynaksız cümleyi de `continue` ile atlıyordu: satır
    dört ayrı paragraftan toplanmış bir kolaja dönüyordu ("Euro yine de
    zayıfladı" Lagarde cümlesinden koparılıp ABD eğrisinin arkasına düştü,
    likidite paragrafının son cümlesi "TL faizi ve eğri" satırına eklendi).
    Kaynaklı aday yalnız satırın etiketini taşıyan İLK paragraftan gelir
    (`n_ilk`: ilk paragrafın birim sayısı; verilmezse hepsi); kaynaksız
    cümleler özgün sırayla eklenir ve sığmayan ilkinde durulur."""
    c = cumleler(metin) if isinstance(metin, str) else [x for x in metin if x]
    if not c:
        return ""
    ust = max(sinir, esnek or sinir)
    if len(c[0]) > ust:
        return ""
    sec, uz = [0], len(c[0])
    if not re.search(r"\d", c[0]) and len(c) > 1 and uz + 1 + len(c[1]) <= ust:
        sec.append(1)
        uz += 1 + len(c[1])
    sinir_ = max(sinir, uz)
    kalan = list(range(sec[-1] + 1, len(c)))
    sinir_ilk = len(c) if n_ilk is None else n_ilk
    oncelikli = ([i for i in kalan if i < sinir_ilk and _kaynakli(c[i])]
                 if kaynak_oncelik else [])
    for i in oncelikli:
        if uz + 1 + len(c[i]) > sinir_:
            continue                        # öncelikli aday sığmazsa sıradakine bakılır
        if (i - 1) not in sec and _anaforik(c[i]):
            continue                        # göndergesi seçilmemiş cümle öksüz kalır
        sec.append(i)
        uz += 1 + len(c[i])
    for i in kalan:
        if i in sec:
            continue
        if uz + 1 + len(c[i]) > sinir_:
            break                           # bitişik seçim: sığmayan cümlede durulur
        if (i - 1) not in sec and _anaforik(c[i]):
            continue                        # göndergesi seçilmemiş cümle öksüz kalır
        sec.append(i)
        uz += 1 + len(c[i])
    return " ".join(c[i] for i in sorted(sec))


# ÇEKİNCE (U7): "sebebi netleşmedi" okumanın kesiminin HEMEN ardından
# geliyorsa öncülüyle birlikte eklenir — bitişik uzatma, cümle SEÇİMİ değil
# (öncülsüz alınan "Sebebi netleşmedi" öksüz kalır). Uzatma tavan izin verdikçe
# durur: sığmazsa ilk düşen birim odur.
NETLESMEDI = re.compile(r"\bnetleşme(?:di|miş|yen)\b", re.I)


def _html_birimleri(html: str, bolum: str, etiket_ayrac: str = ".") -> list[list[str]]:
    """HTML → paragraf başına TAM cümle birimleri. Paragrafın kalın etiketi
    ("<strong>Kur.</strong>") kendi başına birim OLMAZ, ilk cümlesine bağlanır:
    ayrı birim olsaydı satır içeriksiz bir etiketle bitebilirdi ("…maliyet
    yazıyor. Kur." — 05.10 gönderisinin Türkiye satırı). Atıf süzgeci birim
    başına uygulanır."""
    pler = re.findall(r"<p\b[^>]*>(.*?)</p>", html or "", re.S) or ([html] if _duz(html) else [])
    out = []
    for p in pler:
        m = re.match(r"\s*<strong>\s*(.*?)\s*</strong>\s*(.*)$", p, re.S)
        etiket = _duz(m.group(1)).rstrip(".:") if m else ""
        c = cumleler(_duz(ALT_BASLIK.sub(" ", m.group(2) if m else p)))
        if etiket and c:
            c = [f"{etiket}{etiket_ayrac} {c[0]}"] + c[1:]
        birim = _site_disi_birim(c, bolum)
        if birim:
            out.append(birim)
    return out


def _okuma_sec(html: str, sinir: int, bolum: str = "yorum") -> tuple[list[str], list[str]]:
    """Okuma: PARAGRAF bütünü birimdir — sığan paragraflar alınır; ilk paragraf
    bile sığmıyorsa onun TAM cümleleri. Paragraf ortasında bitmek okumayı bir
    giriş cümlesinde bırakıyordu ("Mekanizma iki kanaldan işliyor." — 02.10)."""
    paragraflar = _html_birimleri(html, bolum, etiket_ayrac=":")
    duz = [c for p in paragraflar for c in p]
    temel: list[str] = []
    for p in paragraflar:
        if len(" ".join(temel + p)) > sinir:
            break
        temel += p
    if not temel and paragraflar:
        for c in paragraflar[0]:
            if len(" ".join(temel + [c])) > sinir:
                break
            temel.append(c)
    k = len(temel)
    for j in range(k, min(k + 2, len(duz))):
        if NETLESMEDI.search(duz[j]):
            return temel, duz[k:j + 1]
    return temel, []


# Okumanın paragraf içi kalın ara başlığı ("<strong>Mekanizma.</strong>")
# düz metinde cümleye yapışıyordu: "…kurda temkinli. Mekanizma. Kısa ucun…"
# (05.10 gönderisi). Yalnız OKUMADA "Mekanizma:" biçimine çevrilir; takvimin
# gün etiketleri ve maddeler etkilenmez (onlar kendi kuralıyla okunur).
_ARA_BASLIK = re.compile(r"<strong>\s*([^<]{1,60}?)\s*\.\s*</strong>\s*", re.I)


def _ara_baslik(html: str) -> str:
    return _ARA_BASLIK.sub(lambda m: m.group(1) + ": ", html or "")


# ── sözcük kökleri: konu eşleşmesi ──────────────────────────────────────────

_DURAK = {
    "bugün", "dünkü", "cuma", "pazartesi", "salı", "çarşamba", "perşembe", "cumartesi",
    "pazar", "hafta", "haftalık", "haftanın", "sabah", "akşam", "günü", "yüksek",
    "düşük", "güçlü", "zayıf", "sert", "aylık", "yıllık", "olarak", "ancak", "daha",
    "kadar", "sonra", "önce", "için", "gibi", "ayrıca", "bütün", "yeni", "büyük",
    "küçük", "ilk", "son", "ötesi", "ötesinde", "beklenti", "veri", "verisi",
} | _AYLAR_KUCUK


def _kucuk(s: str) -> str:
    return s.replace("I", "ı").replace("İ", "i").lower()


def _kokler(metin: str) -> set[str]:
    durak = {_kucuk(d)[:5] for d in _DURAK}
    out = set()
    for s in re.findall(r"[^\W\d_]+", metin or ""):
        k = _kucuk(s)
        if len(k) < 4 or k[:5] in durak:
            continue
        out.add(k[:5])
    return out


# AYNI SAYILAR — tweet/denetim'in "paragraf çifti aynı sayıları taşıyor"
# ölçüsüyle AYNI kalıp (ondalıklı ya da binlik ayraçlı sayı); duman sınaması
# iki kalıbın kaynak metnini kıyaslar. Kapı ÇİFT kıyasında 4 karakterin altını
# atar (tesadüfi çakışma); burada soru "satır maddelerde olmayan bir ölçüm
# taşıyor mu" olduğu için kısa sayı da sayılır — 05.10 Emtia satırının tek yeni
# ölçümü "4,2 dolar" distilat marjıydı ve 4 karakter filtresiyle satır sayısız
# sayılıp düşüyordu. Kalıp tek başına yetmedi: kaynak öncelikli seçim 4,2'yi
# hiç almıyordu; sayı artık `_gundem_satirlari`ndaki bitişik yedek seçimle
# korunur (satır o gün yine de gündem bütçesine düşebilir — bütçe ayrı karar).
OLGU_SAYI = re.compile(r"%?\d+(?:[.,]\d+)+%?")


# Tam sayı da birimiyle bir ölçümdür ("Almanya'ya 130 bp ödüyor", "%6").
OLCU_TAMSAYI = re.compile(r"%\d+|\b\d+\s*(?:bp|baz puan|puan)\b")


def _sayilar(metin: str) -> set[str]:
    m = metin or ""
    return ({x.strip("%") for x in OLGU_SAYI.findall(m)}
            | {re.sub(r"\s+", " ", x) for x in OLCU_TAMSAYI.findall(m)})


def _etiketle(etiket: str, metin: str) -> str:
    """'Kilit gelişme: Günün kilit gelişmesi …' ikilemesini önler: cümlenin ilk
    altı sözcüğü etiketin kök sözcüklerini taşıyorsa etiket düşer."""
    # Üç harfli sözcük de kök sayılır ("Ana senaryo": {"ana", "senar"}); aksi
    # hâlde "Bu senaryoda …" diye açılan paragraf etiketi yutuyordu.
    kokler = {k[:5].lower() for k in etiket.split() if len(k) >= 3}
    bas = [w.strip('"\'(),;:.').lower()[:5] for w in metin.split()[:6]]
    if kokler and kokler <= set(bas):
        return metin
    return f"{etiket}: {metin}"


def _tipografi(metin: str) -> str:
    """Yalnız gönderi metnine: aralık tiresi '–', sayı önünde eksi '−', işaret
    yüzden ÖNCE ("%+4,5" → "+%4,5", "%-3,41" → "−%3,41"; ortak/bicim
    sözleşmesi). Kaynak MDX ters sırayı taşıyabiliyor (14 analizin 3'ünde 17
    yer) ve aynı gönderide iki biçim yan yana duruyordu; sayı değişmez, yeni
    hüküm yok — tire→eksi dönüşümüyle aynı sınıftan bir yazım düzeltmesi."""
    # Yıl-ay yazımı ("2024-05") aralık değildir: dört haneli sayıdan sonraki tire kalır.
    m = re.sub(r"(?<!\d{4})(?<!\d{4}-\d{2})(?<=\d)-(?=%?\d)", "–", metin)   # 2026-09-01 dokunulmaz
    m = re.sub(r"(?<![\w.,])-(?=[%\d])", "−", m)
    m = re.sub(r"%([+−])(?=\d)", r"\1%", m)    # ASCII tire önce '−'ye döndü
    return m


# SORUMLULUK NOTU her gönderinin son satırıdır ve kırpmadan MUAFTIR. Eskiden
# not gövdeyle birlikte tavana kırpılıyordu: uzun bir sabah gövdesi notu
# düşürebilirdi ve kimse fark etmezdi. Şimdi gövde, notun payı düşülerek
# kırpılır; not her koşulda yerinde kalır. Bültende "bülten" sözcüğü
# kullanılmaz — o sözcük site atfı izidir ve tweet kendi başına durur.
SORUMLULUK_BULTEN = "Ölçüm ve yorumdur; yatırım tavsiyesi değildir."
# Analiz gönderisinin kapanışı (tweet/analiz.py). Adı teknik zincirinden kalma;
# değiştirilirse analiz.py ile birlikte değişir.
SORUMLULUK_TEKNIK = "Analizdir; yatırım tavsiyesi değildir."


def _kapat(govde: str, not_: str, tavan: int = TEK_TAVAN) -> str:
    """Gövdeyi tavana sığdır, tipografiyi düzelt, sorumluluk notunu SONRA ekle.

    Bülten gönderisi bütçesini kırpılmamış gövdeden kendisi kurar (`_sigdir`)
    ve tavanı aşan bir gövde kalırsa bunu DUSEN'e kendisi yazar; analiz
    gönderisi kendi kapasite döngüsünü taşır. Burada son çare olarak kesim TAM
    cümle sınırında yapılır — "…" yok (17.09.2026: kırpılmış metnin uzunluğu
    kısaltma kararının ölçüsü olamaz; ölçü çağıranındır)."""
    kap = tavan - len(not_) - 2
    g = (govde or "").strip()
    if len(g) > kap:
        g = _kirp(g, kap)
    return _tipografi(g) + "\n\n" + not_


def _tr_sayi(x: float, ondalik: int = 2) -> str:
    s = f"{x:+,.{ondalik}f}"
    return s.replace(",", "@").replace(".", ",").replace("@", ".")


def _degisim_metni(x: float, birim: str) -> str:
    """Türkçe yazımla işaretli değişim: %'de işaret öne gelir (+%5,98), bp ve
    puan arkada ve boşlukla (+13,5 bp) — biçim sözleşmesi (ortak/bicim)."""
    b = (birim or "").strip()
    hane = 1 if b == "bp" else 2
    if abs(x) < 0.5 * 10 ** -hane:
        return "yatay"
    isaret = "+" if x > 0 else "−"
    govde = _tr_sayi(abs(x), hane).lstrip("+")
    if b == "%":
        return f"{isaret}%{govde}"
    return f"{isaret}{govde} {b}" if b else f"{isaret}{govde}"


def _sigma_metni(s: float) -> str:
    isaret = "+" if s > 0 else ("−" if s < 0 else "")
    return f"{isaret}{abs(s):.1f}".replace(".", ",") + "σ"


def _tr_tarih(iso: str) -> str:
    y, a, g = iso.split("-")
    return f"{int(g)} {AYLAR[int(a)]} {y}"


def _tr_kisa_tarih(t: str) -> str:
    """'21.08.2026' → '21 Ağu' · '07.2026' → 'Tem 2026' · ISO → '21 Ağu'; tanımadığını boş bırakır."""
    t = (t or "").strip()
    m = re.match(r"^(\d{2})\.(\d{2})\.(\d{4})$", t)
    if m:
        return f"{int(m.group(1))} {AYLAR[int(m.group(2))][:3]}"
    m = re.match(r"^(\d{2})\.(\d{4})$", t)
    if m:
        return f"{AYLAR[int(m.group(1))][:3]} {m.group(2)}"
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", t)
    if m:
        return f"{int(m.group(3))} {AYLAR[int(m.group(2))][:3]}"
    return ""


GUNLER = ["pazartesi", "salı", "çarşamba", "perşembe", "cuma", "cumartesi", "pazar"]


def _seans_adi(iso: str) -> str:
    """'2026-10-02' → '2 Eki cuma' (satırın KENDİ bar tarihi)."""
    import datetime as _dt
    try:
        g = _dt.date.fromisoformat(str(iso)[:10])
    except ValueError:
        return ""
    return f"{g.day} {AYLAR[g.month][:3]} {GUNLER[g.weekday()]}"


# ── bülten zinciri ───────────────────────────────────────────────────────────

def _maddeler(html: str) -> list[str]:
    """`ozet.ne_oldu` maddeleri: <li> öğeleri; liste değilse metnin tamamı tek madde."""
    li = re.findall(r"<li\b[^>]*>(.*?)</li>", html or "", re.S)
    return li if li else ([html] if _duz(html) else [])


def _pano_fark(g: dict) -> str:
    """Gösterge farkı SAYFANIN kuralıyla (BultenGovde.gostergeFark'ın eşi).
    Bir oranın farkı puandır; kurun farkı bilerek yüzdedir (`fark_birim`);
    bugün ilerlemeyen göstergenin farkı yazılmaz (`bugun_yeni: false`) —
    18.09 tarihli "Net rezerv (−6,5)" altı gönderide birebir tekrar etmişti."""
    if g.get("bugun_yeni") is False:
        return ""
    f = str(g.get("fark_metin") or "").strip()
    if not f:
        return ""
    f = re.sub(r"(^|[\s(])-(?=\d)", r"\1−", f)
    if str(g.get("fark_birim") or "").strip() == "%":
        return f"{f[0]}%{f[1:]}" if f[:1] in "+−" else f"%{f}"
    birim = str(g.get("birim") or "").strip()
    if birim == "%":
        return f"{f} puan"
    return f


# OLAĞANDIŞI EŞİĞİ sayfanınkiyle AYNI (site/src/lib/anaSayfa.ts
# `OLAGANDISI_SIGMA`); duman sınaması iki tanımı kaynak metninden kıyaslar.
OLAGANDISI_SIGMA = 2
# Pano satırına en çok bu kadar kart girer (sayfa sırasıyla, yalnız yeni olan);
# olağandışı satırına en çok bu kadar hareket (eski öne çıkanlar satırıyla aynı).
PANO_EN_COK = 6
OLAGANDISI_EN_COK = 5


def _satir_tarihleri(b: dict) -> dict[str, dict]:
    """Piyasa satırları adıyla: σ satırının kendi bar tarihi ve kapanış anı."""
    out: dict[str, dict] = {}
    for g in ((b.get("piyasa") or {}).get("gruplar") or []):
        for s in (g.get("satirlar") or []) if isinstance(g, dict) else []:
            if isinstance(s, dict) and s.get("ad"):
                out.setdefault(s["ad"], s)
    return out


def _olagandisi(b: dict, anilan: str, haftalik: bool) -> tuple[str, list[str]]:
    """Sayfanın olağandışı listesinden (`piyasa.en_cok_hareket.sigma`), σ ile.

    Ham yüzde listesi yapısal olarak oynak enstrümanları anlatıyordu (136
    kalemin 85'i VIX, MOVE ve enerji vadelisi) ve σ'yı hiç basmıyordu; getiri
    satırlarını dışladığı için 24.09'un 2,8–3,2σ'lık ABD faizi hareketi hiç
    girmedi. Liste sayfayla AYNI: gönderiye özel bir dışlama LİSTESİ YOK (bayat
    kotasyonlu seri ölçüm katmanında, `piyasa.SIGMA_GUVENILMEZ`, listeye hiç
    girmez). Tek istisna sayının KENDİ kaydıdır: aynı sayının `duzeltmeler`
    kaydı bir enstrümanı adıyla AÇIYORSA (`alan` "ABD 2 yıllık getiri, …")
    o enstrüman olağandışı hareket diye anılmaz — sayfa bu satırı Düzeltmeler
    kutusunun yanında basar, gönderide o kutu yok; 01.10'da gönderinin TEK
    olağandışı satırı bültenin kendi "piyasa hareketi değil" dediği +33,7 bp
    idi. Makas kaydı ("Brent–WTI farkı", "Brent − ABD ham petrolü") Brent'i
    düşürmez. Bilinen sınır: başka bir sayının değerini düzelten kayıt o
    günün doğru σ'sını da gönderiden düşürür — tutucu bir hata, satır sayfada
    kalır (geçmiş 100 kayıtta ≥2σ ile kesişen tek vaka iki 2YY=F kaydı). Seans etiketi
    her satırın KENDİ bar tarihinden — pazartesi sayısı cuma seansını "Günün"
    diye basıyordu (5/5); karma seansta gün satır başına yazılır. Maddelerde
    zaten anılan hareket yinelenmez."""
    em = (b.get("piyasa") or {}).get("en_cok_hareket") or {}
    liste = [h for h in (em.get("sigma") or [])
             if isinstance(h, dict) and isinstance(h.get("sigma"), (int, float))
             and h.get("deger") is not None and abs(h["sigma"]) >= OLAGANDISI_SIGMA]
    satirlar = _satir_tarihleri(b)
    alt = anilan.lower()
    duzeltilen = [str(d.get("alan") or "") for d in (b.get("duzeltmeler") or [])
                  if isinstance(d, dict)]
    secilen = []
    for h in liste:
        ad = str(h.get("ad") or "")
        if ad and any(re.match(re.escape(ad) + r"(?=,|\s(?![−–-]))", a) for a in duzeltilen):
            continue
        deger = abs(float(h["deger"]))
        # Ad, σ katsayısı ya da iki haneli değer maddede geçiyorsa anılmıştır.
        izler = (ad.lower(), f"{abs(h['sigma']):.1f}".replace(".", ",") + "σ",
                 _tr_sayi(deger, 2).lstrip("+"))
        if any(iz and iz in alt for iz in izler):
            continue
        secilen.append((h, str((satirlar.get(ad) or {}).get("tarih") or "")[:10]))
        if len(secilen) >= OLAGANDISI_EN_COK:
            break
    if not secilen:
        return "", []
    tarihler = {t for _, t in secilen}
    tek = len(tarihler) == 1 and "" not in tarihler
    parcalar = []
    for h, t in secilen:
        ek = _sigma_metni(h["sigma"])
        if not tek and t:
            ek += "; " + _seans_adi(t)
        parcalar.append(f"{h['ad']} {_degisim_metni(float(h['deger']), h.get('birim', ''))} ({ek})")
    etiket = "Haftanın olağandışı hareketleri" if haftalik else "Olağandışı hareketler"
    if tek:
        etiket += f" ({_seans_adi(next(iter(tarihler)))})"
    return etiket + ": ", parcalar


def _pano(b: dict, govde: str) -> list[str]:
    """PANO (günlük) / SEVİYELER (haftalık): gösterge kartlarından, yalnız
    BUGÜN İLERLEYEN (`bugun_yeni is True`), kendi kıyasında DEĞERİ DEĞİŞEN
    (ölçülmüş sıfır fark girmez) ve değeri gövdede zaten geçmeyen kart.

    Eski satır her gün ilk beş kartı basıyordu: 28 gönderinin 28'inde aynı beş
    kalem, ardışık gönderilerde 135 kalemin 61'i değer ve tarihiyle aynıydı ve
    beş pazartesinin beşinde pazarınkiyle birebirdi; 05.10'da 19 kartın 0'ı
    yeniydi. Fark sayfanın kuralıyla (`_pano_fark`): kur yüzde, oranın farkı
    puan. Haftalık sayıda kartların farkı ve "yeni"si önceki HAFTALIK sayının
    ölçüm anından — sayfanın gösterge şeridi ve haftalık tablosuyla aynı kıyas.
    2 yıllık faizin TEK tanımı: gövde bir 2 yıllık getiri anıyorsa gösterge
    kartı ikinci bir 2 yıllık sayı basmaz. Kurun kapanış tanımı ("İstanbul
    18:00") yalnız saatlik bardan kurulmuş kapanışta (`kapanis_ani`) yazılır;
    yedek tanım (günlük bar) okura basılmaz."""
    satirlar = _satir_tarihleri(b)
    parcalar: list[str] = []
    for g in b.get("gostergeler") or []:
        if len(parcalar) >= PANO_EN_COK:
            break
        if g.get("bugun_yeni") is not True or not (g.get("metin") and g.get("ad")):
            continue
        # "YENİ" YALNIZ TARİHİN İLERLEMESİ DEĞİLDİR (05.10.2026): politika faizi ve
        # AOFM her gün yayımlanır, tarihi ilerler, değeri aylardır aynıdır —
        # 01.10, 02.10 ve 04.10'da iki kart PANO_EN_COK'un iki yerini tutup
        # gerçekten yeni bir veriyi (yabancı 4 haftalık akım) dışarıda bıraktı.
        # Fark ÖLÇÜLMÜŞ ve kartın hanesinde sıfırsa (`fark_metin` boş) kart girmez;
        # kıyas ölçülemediyse (`fark` None) "değişmedi" sayılmaz, kart girer.
        # Kör nokta adıyla: günlükte iki yazılmış sayı arasında seri A→B→B
        # giderse değişim panoda görünmez — sayfanın kartı da aynı kıyası taşır.
        f = g.get("fark")
        if (isinstance(f, (int, float)) and not isinstance(f, bool)
                and not str(g.get("fark_metin") or "").strip()):
            continue
        metin = str(g["metin"])
        if metin.replace("−", "-") in govde.replace("−", "-"):
            continue
        if g.get("anahtar") == "gosterge_ytm" and re.search(r"\b2 yıllık", govde):
            continue
        birim = (g.get("birim") or "").strip()
        deger = f"%{metin}" if birim == "%" else (f"{metin} {birim}" if birim else metin)
        ek = []
        fark = _pano_fark(g)
        if fark:
            ek.append(fark)
        zaman = []
        vt = str(g.get("veri_tarihi") or "")
        kisa = _tr_kisa_tarih(vt)
        if vt and vt[:10] != b["tarih"] and kisa and kisa != _tr_kisa_tarih(b["tarih"]):
            zaman.append(kisa)
        tanim = str(g.get("kapanis_tanimi") or "")
        satir = satirlar.get(g["ad"]) or {}
        if tanim and satir.get("kapanis_ani") and satir.get("kapanis_tanimi") == tanim:
            zaman.append(tanim)
        if zaman:
            ek.append(", ".join(zaman))
        parcalar.append(f"{g['ad']} {deger}" + (f" ({'; '.join(ek)})" if ek else ""))
    return parcalar


# ── GÜNLÜK EŞİK BLOĞU — "Neye bakılacak" (U10) ──────────────────────────────
# Günlük risk bölümünün maddeleri gönderiye hiç girmiyordu (biçim 3'teki üç
# günlük sayının on "izlenecek" maddesinin onu da yok). Risk GÜNDEM DÖNGÜSÜNE
# GİRMEZ (kayıt defterinde günlük gönderi etiketi yok, bilerek): etiketle
# döngüye alınınca 800 karakterlik bütçeyi aşıp hiç basılmıyor, girse bile
# 260 kırpması üç maddenin birini kesiyordu. Kendi yolu, kendi bütçesi var.
# Kalıp sözleşmedir ve TEK tanım burada; bülten denetimi kalıba uymayan
# maddeyi bu kalıpla UYARI olarak sorar (bulten/denetim.risk_kalibi).
RISK_KALIBI = re.compile(
    r"^\s*<strong>\s*(?P<tetik>[^<]+?)\s*</strong>\s*→\s*(?P<etki>[^;<]+?)\s*;\s*"
    r"izlenecek:\s*(?P<olcu>.+?)\s*$", re.S)
ESIK_MADDE = 170            # madde başına
ESIK_EN_COK = 2             # madde sayısı
ESIK_SINIR = ESIK_EN_COK * (ESIK_MADDE + 3)


def risk_maddeleri(html: str) -> tuple[list[dict], list[str]]:
    """Günlük risk bölümünün <li> maddeleri: (kalıba uyanlar, uymayanlar)."""
    uyan, uymayan = [], []
    for li in re.findall(r"<li\b[^>]*>(.*?)</li>", html or "", re.S):
        m = RISK_KALIBI.match(li)
        if m:
            uyan.append({"tetik": _duz(m.group("tetik")), "etki": _duz(m.group("etki")),
                         "olcu": _duz(m.group("olcu")), "ham": li})
        elif _duz(li):
            uymayan.append(_duz(li))
    return uyan, uymayan


def risk_satiri(r: dict) -> str:
    """Kalıba uyan risk maddesinin gönderideki satırı (uzunluk ölçüsü de bu)."""
    satir = f"{r['tetik']} → {r['etki']}; izlenecek: {r['olcu']}"
    return satir if re.search(r"[.!?]$", satir) else satir + "."


def _fikir_seviyeleri(b: dict) -> set[tuple[float, str]]:
    """Açık işlem fikirlerinin seviyeleri (giriş · hedef · stop) SAYI olarak,
    birimleriyle: {(|değer| fikrin hanesine yuvarlı, birim)}. Fikir gönderiye
    girmez (karar 04.10.2026); eşik bloğu ya da senaryo satırı bir fikrin
    seviyesini taşırsa o satır düşer.

    İlk yazım seviyeleri DİZGE olarak kuruyor ve dört karakterden kısa yazımı
    atıyordu: bp fikirlerinin (05.10'da üç açık fikrin ikisi) "71", "47",
    "250" seviyeleri kümede hiç yoktu ve evin doğal yazımı ("71 bp'yi aşması",
    "−250 bp'ye daralması") süzgeçten geçiyordu (05.10.2026 incelemesi).
    İşaret ATILIR: ev yazımı ters makası işaretsiz yazar ("371 baz puan ters");
    bedeli, fikir −250 açıkken "CDS 250 bp" satırının da düşmesi — bir
    düşürmedir ve DUSEN'de görünür."""
    out: set[tuple[float, str]] = set()
    kayitlar = list(b.get("fikirler") or [])
    kayitlar += [k for k in ((b.get("fikir_karne") or {}).get("kayitlar") or [])
                 if isinstance(k, dict)]
    for f in kayitlar:
        if not isinstance(f, dict):
            continue
        hane = int(f.get("ondalik") or 2)
        birim = str(f.get("birim") or "")
        for alan in ("giris", "hedef", "stop"):
            v = f.get(alan)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out.add((round(abs(float(v)), hane), birim))
    return out


# Metindeki BÜTÜN sayı: binlik noktalı ya da düz tam kısım, isteğe bağlı ondalık
# virgül. "71", "71,8"in ya da "2.071"in içinde eşleşmez; tarih ("07.09")
# sayı sayılmaz. Ayrıştırıcı burada yerel durur — `bulten.denetim` içe
# aktarılmaz (tweet sürecinde `denetim` ad çakışması, 01.10.2026).
_METIN_SAYI = re.compile(r"(?<![\d.,])[−+-]?(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d+))?(?![\d]|,\d|\.\d)")
_BP_ARKA = re.compile(r"\s*(?:bp|baz puan)", re.I)


def _fikir_tasir(metin: str, seviyeler: set[tuple[float, str]]) -> bool:
    """Satır bir fikir seviyesini taşıyor mu — SAYI olarak kıyas. Ondalıklı
    yazım birimden bağımsız eşleşir (eski davranış: "0,0480", "71,0"); TAM
    SAYI yalnız fikrin birimiyle eşleşir — bp'de ardından "bp"/"baz puan",
    yüzdede önünde "%" (`OLCU_TAMSAYI`daki "tam sayı birimiyle bir ölçümdür"
    ilkesinin eşi). Birimsiz kıyas "47 bin varil", "%47'sinde" gibi
    tesadüfleri de düşürüyordu (7.700 gündem cümlesinde 44'e karşı 20)."""
    if not seviyeler:
        return False
    for m in _METIN_SAYI.finditer(metin or ""):
        tam, ond = m.group(1).replace(".", ""), m.group(2)
        v = float(f"{tam}.{ond}") if ond else float(tam)
        uyan = {br for d, br in seviyeler if abs(d - v) < 1e-9}
        if not uyan:
            continue
        if ond:
            return True
        once = metin[max(0, m.start() - 2):m.start()]
        if "bp" in uyan and _BP_ARKA.match(metin, m.end()):
            return True
        if "%" in uyan and "%" in once:
            return True
    return False


def _esik_blogu(b: dict, takvim_etiketleri: list[str]) -> list[str]:
    risk = str((b.get("gundem") or {}).get("risk") or "")
    if not _duz(risk):
        return []
    uyan, uymayan = risk_maddeleri(risk)
    for x in uymayan:
        DUSEN.append(("risk", "kalıba uymuyor (<strong>tetik</strong> → etki; izlenecek: ölçü): " + x))
    takvim_kok = _kokler(" ".join(takvim_etiketleri))
    seviyeler = _fikir_seviyeleri(b)
    out = []
    for r in uyan:
        satir = _site_disi(risk_satiri(r), "risk")
        if not satir:
            continue
        if len(satir) > ESIK_MADDE:
            DUSEN.append(("risk", f"{ESIK_MADDE} karakteri aşıyor: " + satir))
            continue
        if _kokler(r["tetik"]) & takvim_kok:
            DUSEN.append(("risk", "takvimde zaten anılan yayım: " + satir))
            continue
        if _fikir_tasir(satir, seviyeler):
            DUSEN.append(("risk", "işlem fikri seviyesi taşıyor: " + satir))
            continue
        if len(out) < ESIK_EN_COK and sum(len(x) + 1 for x in out) + len(satir) + 2 <= ESIK_SINIR:
            out.append("· " + satir)
    if not out:
        DUSEN.append(("risk", "bölüm dolu ama eşik bloğuna giren madde yok"))
    return out


# ── takvim paragrafları ──────────────────────────────────────────────────────

def _takvim_paragraflari(html: str) -> list[tuple[str, list[str]]]:
    """Takvim <p> paragrafları: (kalın etiket, birimler). Etiket kendi başına
    birim OLMAZ — ilk cümleye bağlanır; gönderi içeriksiz bir gün başlığıyla
    bitemez ("…Salı 6 Ekim."). Etiketsiz paragraf öncekinin devamıdır."""
    out: list[tuple[str, list[str]]] = []
    for p in re.findall(r"<p\b[^>]*>(.*?)</p>", html or "", re.S) or ([html] if _duz(html) else []):
        m = re.match(r"\s*<strong>(.*?)</strong>\s*(.*)$", p, re.S)
        etiket = _duz(m.group(1)) if m else ""
        govde = m.group(2) if m else p
        c = cumleler(_duz(govde))
        if etiket and c:
            birimler = [f"{etiket} {c[0]}"] + c[1:]
        elif etiket:
            birimler = []
        else:
            birimler = c
        out.append((etiket, birimler))
    return out


def _bugun_mu(etiket: str, birimler: list[str]) -> bool:
    ilk = etiket or (birimler[0] if birimler else "")
    return bool(re.match(r"\s*Bugün\b", ilk))


# ── blok düzeni ve bütçe ─────────────────────────────────────────────────────
# Gönderi BLOKLARDAN kurulur; her blok BİRİMLERDEN (madde, satır, cümle) ve her
# birimin bir DÜŞME ÖNCELİĞİ vardır (küçük olan önce düşer; None düşmez).
# Ölçü KIRPILMAMIŞ gövdedir: taşarsa öncelik sırasıyla BİRİM düşer, `_kapat`ın
# sondan kırpmasına hiçbir blok bırakılmaz (17.09.2026: analiz gönderisinde
# kırpma rakam şeridini sessizce yiyordu). 04.10 haftalığında "Önümüzdeki
# hafta"nın iki yönlü sonucu blok düzeniyle KAPANMADI: artık cümle seçiminde
# kayboluyor (gün satırı ilk cümleyi alır) ve onu yalnız yazım kuralı ile
# `iki_yonlu_mu` uyarısı (DUSEN + bulten/denetim.takvim_kalibi) korur.

def _blok(id_: str, birimler: list[tuple[str, int | None]], baslik: str = "",
          on: str = "", ayrac: str = "\n") -> dict:
    return {"id": id_, "birim": [(m, o) for m, o in birimler if m], "baslik": baslik,
            "on": on, "ayrac": ayrac}


def _yaz(bloklar: list[dict]) -> str:
    par = []
    for bl in bloklar:
        birim = [m for m, _ in bl["birim"]]
        if not birim:
            continue
        govde = bl["on"] + bl["ayrac"].join(birim)
        par.append(f"{bl['baslik']}\n{govde}" if bl["baslik"] else govde)
    return "\n\n".join(par)


def _sigdir(bloklar: list[dict], kapasite: int) -> None:
    while len(_yaz(bloklar)) > kapasite:
        aday = [(o, -bi, -ui, bi, ui)
                for bi, bl in enumerate(bloklar)
                for ui, (_m, o) in enumerate(bl["birim"]) if o is not None]
        if not aday:
            break
        _o, _x, _y, bi, ui = min(aday)
        metin, _ = bloklar[bi]["birim"].pop(ui)
        DUSEN.append((bloklar[bi]["id"], "bütçe: " + metin))


KAPASITE = TEK_TAVAN - len(SORUMLULUK_BULTEN) - 2


def _baslik_blogu(b: dict, baslik: str) -> dict:
    ilk = f"{baslik} — {_tr_tarih(b['tarih'])}"
    if int(b.get("surum") or 2) >= 3:
        manset = _site_disi(_duz(b.get("manset") or ""), "manset")
        if manset:
            ilk += "\n" + manset
    return _blok("baslik", [(ilk, None)])


def _madde_birimleri(b: dict, sinir: int, oncelik) -> list[tuple[str, int | None]]:
    """`ne_oldu` maddeleri → gönderi birimleri. Maddenin kalın etiketi kendi
    başına birim OLMAZ, ilk cümlesine bağlanır (`_takvim_paragraflari`
    kalıbı, etiket olduğu gibi). Eski yol düz metni `_kirp`la kesiyordu ve
    "Rezerv." etiketini ayrı cümle sayıyordu: ilk içerik cümlesi bütçeyi
    aşınca ya da site atfı yüzünden düşünce gönderide içeriksiz "· Rezerv."
    satırı basılıyor, DUSEN'e de bir şey yazılmıyordu (05.10.2026 incelemesi).
    Seçim sıkı önektir: ilk (bağlı) birim sınırı aşarsa madde bütünüyle düşer."""
    out = []
    for m in _maddeler((b.get("ozet") or {}).get("ne_oldu") or ""):
        e = re.match(r"\s*<strong>(.*?)</strong>\s*(.*)$", m, re.S)
        etiket = _duz(e.group(1)) if e else ""
        c = cumleler(_duz(e.group(2) if e else m))
        if etiket and c:
            c = [f"{etiket} {c[0]}"] + c[1:]
        elif etiket:
            DUSEN.append(("ne_oldu", "etiketten sonra içerik yok: " + etiket))
            continue
        c = _site_disi_birim(c, "ne_oldu")
        if not c:
            continue                     # içerik atıf yüzünden düştü (DUSEN'de)
        sec, uz = [], 0
        for x in c:
            ek = len(x) + (1 if sec else 0)
            if uz + ek > sinir:
                break
            sec.append(x)
            uz += ek
        if not sec:
            DUSEN.append(("ne_oldu", "ilk cümlesi madde bütçesini aşıyor: " + " ".join(c)))
            continue
        out.append(("· " + " ".join(sec), oncelik(len(out))))
    return out


def _gundem_satirlari(b: dict, sinir: int, blok_sinir: int, maddeler: str = "",
                      kaynak_oncelik: bool = False) -> list[str]:
    """Etiketli gündem satırları. Biçim 3 günlükte maddelerle AYNI KONUYU
    yineleyen ve maddelerde olmayan hiçbir sayı taşımayan satır düşer (05.10
    Küresel: "Euro ve Avrupa siyaseti. Euro dört haftalık düşüş serisini…");
    sayılı satır kalır — 02.10'da TL faizinin tek sayıları gündem satırındaydı.
    "Daha çok gündem" geri bildirimi (31.08) bu yüzden kaldırma değil süzme."""
    gundem = b.get("gundem") or {}
    dolu = [(a, e) for a, e in gundem_bolumleri(b) if str(gundem.get(a) or "").strip()]
    madde_sayi = _sayilar(maddeler)
    madde_kok = [_kokler(m) for m in maddeler.split("\n") if m.strip()]
    satirlar, toplam = [], 0
    for anahtar, etiket in dolu:
        paragraflar = _html_birimleri(str(gundem.get(anahtar) or ""), anahtar)
        birimler = [c for p in paragraflar for c in p]
        if not birimler:
            continue
        secim = _satir_sec(birimler, sinir, esnek=SATIR_ESNEK, kaynak_oncelik=kaynak_oncelik,
                           n_ilk=len(paragraflar[0]))
        if not secim:
            DUSEN.append((anahtar, "ilk cümlesi satır bütçesini aşıyor: " + birimler[0]))
            continue
        if maddeler:
            def ayni_konu(x: str) -> bool:
                return (not (_sayilar(x) - madde_sayi)
                        and any(_kokler(cumleler(x)[0]) & mk for mk in madde_kok))
            if ayni_konu(secim) and kaynak_oncelik:
                # BİTİŞİK YEDEK (05.10.2026 incelemesi): kaynak öncelikli seçim
                # yeni sayı taşımayan kaynaklı cümleleri öne alıp satırın tek
                # yeni ölçümünü dışarıda bırakabiliyor — 05.10 Emtia'da G7 +
                # Husi cümleleri seçildi, "distilat marjı 4,2 dolar" kaldı ve
                # satır "aynı konu" diye düştü. Aynı birimlerle bitişik seçim
                # maddelerde olmayan bir sayı taşıyorsa satır onunla kurulur.
                yedek = _satir_sec(birimler, sinir, esnek=SATIR_ESNEK)
                if yedek and not ayni_konu(yedek):
                    secim = yedek
            if ayni_konu(secim):
                DUSEN.append((anahtar, "maddeyle aynı konu, yeni sayı yok: " + secim))
                continue
        satir = _etiketle(etiket, secim)
        if toplam + len(satir) > blok_sinir:
            DUSEN.append((anahtar, "gündem bütçesi: " + satir))
            continue
        satirlar.append(satir)
        toplam += len(satir) + 1
    return satirlar


def _site_disi_birim(birimler: list[str], bolum: str) -> list[str]:
    """`_site_disi`in birim listesi eşi: atıf taşıyan birim ve göndergesi
    düşen öksüz devamı düşer; birimler (etiket + ilk cümle) bölünmez."""
    kalan, onceki_dustu = [], False
    for c in birimler:
        dus = _site_izi_var(c) or (onceki_dustu and _anaforik(c))
        if dus:
            onceki_dustu = True
            DUSEN.append((bolum, c))
            continue
        onceki_dustu = False
        kalan.append(c)
    return kalan


def _birim_onek(birimler: list[str], sinir: int, dusen_bolum: str = "") -> list[str]:
    """Sınıra sığan birim öneki (ilk birim sınırı aşsa da tek başına kalır).
    `dusen_bolum` verilmişse önekin dışında kalan her birim DUSEN'e yazılır —
    hiçbir yolda sessiz düşüş kalmaz (05.10.2026: 'Bugün' paragrafının payı
    aşan cümleleri hiçbir yerde görünmüyordu). Verilmezse kalanı çağıran
    kullanır (Beklenen'in payı aşan birimleri düşük öncelikle bloğa girer)."""
    out, uz = [], 0
    for c in birimler:
        ek = len(c) + (1 if out else 0)
        if out and uz + ek > sinir:
            break
        out.append(c)
        uz += ek
    if dusen_bolum:
        DUSEN.extend((dusen_bolum, "takvim payı: " + c) for c in birimler[len(out):])
    return out


def _gunluk3(b: dict) -> list[dict]:
    """Biçim 3 günlük: başlık+manşet → maddeler → günün sınavı ("Bugün…") →
    okuma → Gündem → Neye bakılacak → olağandışı → Pano → Beklenen."""
    bloklar = [_baslik_blogu(b, "Sabah Notu")]
    maddeler = _madde_birimleri(b, MADDE_SINIR, lambda i: None if i == 0 else 80)
    bloklar.append(_blok("ne_oldu", maddeler))
    # İLK 280 (U2): günün sınavı ilk ekranda dursun. Yazarın takviminin ilk
    # "Bugün…" paragrafı KOPYALANMAZ, TAŞINIR: maddelerin hemen arkasına alınır
    # ve "Beklenen:"den çıkar — metin yazarın cümlesi olarak TEK evde kalır.
    paragraflar = _takvim_paragraflari(str((b.get("gundem") or {}).get("takvim") or ""))
    tum_etiketler = [e for e, _bir in paragraflar if e]
    bugun_i = next((i for i, (e, bir) in enumerate(paragraflar) if bir and _bugun_mu(e, bir)), None)
    bugun: list[str] = []
    if bugun_i is not None:
        _e, bir = paragraflar.pop(bugun_i)
        bugun = _birim_onek(_site_disi_birim(bir, "takvim"), BEKLENTI_SINIR, "takvim")
    bloklar.append(_blok("bugun", [(c, None if i == 0 else 72) for i, c in enumerate(bugun)],
                         ayrac=" "))
    temel, ek = _okuma_sec(b.get("yorum") or "", OKUMA_SINIR_3)
    bloklar.append(_blok("yorum", [(c, 65 if i == 0 else 60) for i, c in enumerate(temel)]
                         + [(c, 10) for c in ek], ayrac=" "))
    madde_metni = "\n".join(m for m, _ in maddeler)
    gundem = _gundem_satirlari(b, GUNDEM_PARCA, GUNDEM_SINIR_3, maddeler=madde_metni,
                               kaynak_oncelik=True)
    bloklar.append(_blok("gundem", [(s, 40) for s in gundem], baslik="Gündem"))
    # Beklenen: takvimin geri kalanı; GÜVENCELİ pay "Bugün" paragrafıyla
    # PAYLAŞILIR (taşınan metin yeni içerik değildir), ama bir tabanın altına
    # inmez. Payı AŞAN birimler silinmez: en düşük öncelikle (5) bloğa girer,
    # yalnız gerçekten boş yer varsa gönderide kalır ve sığmayanı `_sigdir`
    # "bütçe:" diye DUSEN'e yazar (05.10.2026: tavanın 470 karakter altında
    # kalan gönderide aynı günün ikinci yayımı — ABD ISM 17:00 — sessizce
    # düşüyordu). Sabit payı kaldırmak çare değildi: ölçüldü, 01.10'da uzak
    # takvim birimleri Gündem'i, Neye bakılacak'ı ve panoyu yerinden ediyordu.
    kalan = _site_disi_birim([c for _e, bir in paragraflar for c in bir], "takvim")
    bek_sinir = max(BEKLENTI_SINIR - len(" ".join(bugun)), BEKLENTI_TABAN)
    bek = _birim_onek(kalan, bek_sinir) if kalan else []
    tasan = kalan[len(bek):]
    gonderide = " ".join(bugun + bek)
    esik = _esik_blogu(b, [e for e in tum_etiketler if e in gonderide])
    bloklar.append(_blok("risk", [(s, 50) for s in esik], baslik="Neye bakılacak"))
    takvim = _blok("takvim", [(c, None if i == 0 else 75) for i, c in enumerate(bek)],
                   on="Beklenen: ", ayrac=" ")
    govde = _yaz(bloklar + [takvim])
    # Risk süzgeci (`gonderide`) ve pano tekilleştirmesi (`govde`) yalnız
    # güvenceli kısımdan kurulur: sonra düşebilecek bir takvim birimi yüzünden
    # risk maddesi ya da pano kartı haksız yere elenmesin.
    takvim["birim"] += [(c, 5) for c in tasan]
    on, ola = _olagandisi(b, madde_metni, haftalik=False)
    bloklar.append(_blok("olagandisi", [(p, 20) for p in ola], on=on, ayrac=" · "))
    bloklar.append(_blok("pano", [(p, 30) for p in _pano(b, govde)], on="Pano: ", ayrac=" · "))
    bloklar.append(takvim)
    if not maddeler and not temel:
        raise SystemExit("bültenin maddeleri de okuması da boş — tweet kurulamaz")
    return bloklar


# HAFTALIK İSKELET (U6, 3.800 içinde): başlık + manşet → maddeler (dinamik
# pay) → Senaryolar (ana · alternatif · kuyruk) → Önümüzdeki hafta (gün gün) →
# Karne → Seviyeler. Konu bölümü satırları, okuma ve öne çıkanlar haftalıkta
# ÇIKAR: gönderi önümüzdeki haftanın yalnız pazartesisini ve ana senaryonun
# sayısız, kesik ilk cümlesini taşıyordu. Her blok kendi bütçesiyle; taşınca
# önce maddeler sondan düşer (dinamik pay), sonra seviyeler, sonra takvimin son
# günleri ve karnenin kayıtları — ana senaryo, takvimin ilk günü ve karnenin
# sayımı düşmez.
SENARYO_SATIR = SATIR_ESNEK
TAKVIM_ESNEK = 250          # gün satırı: ilk cümle (~170), sayısızsa bir sonraki de
TAKVIM_SINIR = 900
KARNE_SATIR = 260           # kapanan kaydın ilk cümlesi
KARNE_SINIR = 600
# Karnenin "kapanan kayıt" paragrafı DEĞİL olanlar: takvimle ve senaryoyla çakışır.
KARNE_DISI = re.compile(r"sınanacak|açık\s+ana\s+senaryo", re.I)


def _senaryolar(b: dict) -> list[tuple[str, int | None]]:
    """Risk bölümünün her <h3> alt bölümünden TEK satır: alt bölümün ilk tam
    cümlesi. Alt bölüm kalın etiketli bir paragrafla açılıyorsa ("Tetik.")
    senaryonun tezi başlıktadır: satır "Alternatif: <başlık>. Tetik: <ilk
    cümle>" olur — kuyruk satırı tetiksiz kalmaz. Ana senaryo düşmez: ilk cümle
    330'u da aşarsa yazarın alt başlığı yazılır. Açık bir işlem fikrinin
    seviyesini taşıyan satır düşer (fikir gönderiye girmez)."""
    ham = str((b.get("gundem") or {}).get("risk") or "")
    bolumler = re.findall(r"<h3\b[^>]*>(.*?)</h3>(.*?)(?=<h3\b|$)", ham, re.I | re.S)
    seviyeler = _fikir_seviyeleri(b)
    out = []
    for i, (h3, govde) in enumerate(bolumler):
        baslik = _duz(h3)
        ad, _, tez = baslik.partition(":")
        ad, tez = ad.strip(), tez.strip()
        ana = i == 0 or ad.lower().startswith("ana")
        if ana:
            ad = "Ana senaryo"
        p = re.search(r"<p\b[^>]*>(.*?)</p>", govde, re.S)
        ilk = p.group(1) if p else govde
        etiketli = re.match(r"\s*<strong>", ilk)
        metin = _site_disi(_duz(_ara_baslik(ilk)), "risk")
        # Yalnız İLK tam cümle (sayısızsa bir sonraki de): sınır 0, esneme 330.
        cumle = _satir_sec(metin, 0, esnek=SENARYO_SATIR) if metin else ""
        adaylar = []
        if etiketli and tez and cumle:
            adaylar.append(f"{ad}: {tez}. {cumle}")
        elif cumle:
            adaylar.append(f"{ad}: {cumle}")
        if tez:
            adaylar.append(f"{ad}: {tez}.")
        uyan = [a for a in adaylar if len(a) <= SENARYO_SATIR]
        if uyan:
            satir = uyan[0]
        elif ana and adaylar:
            satir = min(adaylar, key=len)          # ana senaryo düşmez
        else:
            DUSEN.append(("risk", f"{ad}: ilk cümlesi satır bütçesini aşıyor"))
            continue
        if _fikir_tasir(satir, seviyeler):
            DUSEN.append(("risk", "işlem fikri seviyesi taşıyor: " + satir))
            continue
        out.append((satir, None if ana else 60))
    return out


# İKİ YÖNLÜ SONUÇ İŞARETİ (05.10.2026 incelemesi). Takvimin her gün satırı
# "olay, saat, iki yönlü sonuç" taşır (bulten/YAZIM.md, haftalık kural 9);
# yazar kurala uymayınca araç sessizce bir takvim listesi üretiyordu (04.10:
# beş gün satırının beşi tek yönlü ya da sonuçsuz, iz yok). İşaret ölçülerek
# tanımlandı — basit bir "üstünde|altında|aşarsa" listesi kuralın kendi
# örneğini ("beklenti üstü … altı …") ve "güçlü gelirse … zayıf gelirse"yi
# kaçırıyor, "100 doların üstünde kaldı" gibi betimlemeyi yakalıyordu:
#   koşul eki   -(I)rsA · -mAzsA · -(y)sA (gelirse, çıkarsa, taşırsa,
#               gelmezse, güçlüyse, yüksekse, değilse); "Borsa", "Bursa",
#               "hisse", "Fransa" eşleşmez
#   karşıtlık   "ise"
#   çift        üst/alt aynı satırda ("beklenti üstü … altı …")
# Ölçüt bir KAPI değil UYARIDIR (bulten/denetim.takvim_kalibi) ve DUSEN'e
# yazılır; seçim kuralına dokunmaz — koşul cümlelerini öncelikli almak
# ölçüldü, Çarşamba, Perşembe ve Cuma satırlarını düşürüyordu.
_KOSUL_SON = re.compile(r"(?:[aeıioöuü]rs[ae]|m[ae]zs[ae]|[aeıioöuü]ys[ae]|[kftpçşhl]s[ae])$")
# Bülten arşivinde (gündem metinleri) eki taşıyıp koşul OLMAYAN sözcükler:
# "neredeyse" (57 kez), yönelme hâli "endekse", "terse". Ölçüldü; kalanlar
# (kalırsa, çıkarsa, gelirse, yoksa, …) gerçekten koşuldur.
_KOSUL_DEGIL = {"neredeyse", "endekse", "terse"}
_UST = re.compile(r"\büst(?:ü|ünde|ünden|üne|e)\b", re.I)
_ALT = re.compile(r"\balt(?:ı|ında|ından|ına|a)\b", re.I)


def iki_yonlu_mu(metin: str) -> bool:
    """Satır iki yönlü bir sonuç (koşul, karşıtlık ya da üst/alt çifti) taşıyor mu."""
    for w in re.findall(r"[^\W\d_]+", metin or ""):
        k = _kucuk(w)
        if (len(k) >= 5 and not k.startswith(("bors", "burs")) and k not in _KOSUL_DEGIL
                and _KOSUL_SON.search(k)):
            return True
    if re.search(r"\bise\b", _kucuk(metin or "")):
        return True
    return bool(_UST.search(metin or "") and _ALT.search(metin or ""))


def gun_etiketi_mi(etiket: str) -> bool:
    """Gün paragrafı mı ("Pazartesi 5 Ekim.") — "Ötesi" ve "Planı değişen
    takvim" gibi etiketler bir yayımın günü değildir, iki yönlü sonuç sorulmaz."""
    ilk = (_kucuk(etiket or "").split() or [""])[0].strip(".:")
    return ilk in GUNLER


def takvim_satiri(etiket: str, birimler: list[str]) -> str:
    """Haftalık gönderiye giden gün satırı — TEK tanım: `_takvim_gunleri` ve
    bülten denetimi (`takvim_kalibi`) bunu çağırır. Etiketli paragrafın ilk
    cümlesi (sayı taşımıyorsa bir sonraki de); boşsa ilk cümle bütçeyi aşıyor."""
    govde = birimler[0][len(etiket):].strip()
    metin = _site_disi(" ".join([govde] + birimler[1:]), "takvim")
    secim = _satir_sec(metin, 0, esnek=TAKVIM_ESNEK) if metin else ""
    return f"{etiket.rstrip('.:')}: {secim}" if secim else ""


def _takvim_gunleri(b: dict) -> list[tuple[str, int | None]]:
    """Önümüzdeki hafta gün gün: her etiketli gün paragrafının ilk cümlesi
    (sayı taşımıyorsa bir sonraki de); etiketsiz devam paragrafı girmez."""
    out, toplam = [], 0
    for etiket, birimler in _takvim_paragraflari(str((b.get("gundem") or {}).get("takvim") or "")):
        if not etiket or not birimler:
            continue
        satir = takvim_satiri(etiket, birimler)
        if not satir:
            DUSEN.append(("takvim", f"{etiket}: ilk cümlesi satır bütçesini aşıyor"))
            continue
        if gun_etiketi_mi(etiket) and not iki_yonlu_mu(satir):
            DUSEN.append(("takvim", f"{etiket.rstrip('.:')}: gönderiye giden cümle iki yönlü sonuç taşımıyor"))
        if toplam + len(satir) > TAKVIM_SINIR:
            DUSEN.append(("takvim", "takvim bütçesi: " + satir))
            continue
        out.append((satir, None if not out else 40))
        toplam += len(satir) + 1
    return out


def _karne(b: dict) -> list[tuple[str, int | None]]:
    """Karne: sayım ölçülen katmandan (`izleme.karne`; oran yazılmaz — sayıya
    ek getirilmez), kapanan kayıtların cümlesi yazarın karne bölümündeki kalın
    başlıklı paragrafların ilk cümlesi. `izleme` kayıtlarının konusu
    kullanılmaz: 46 kaydın 6'sı SORU biçiminde ve okur hangi tarafın tuttuğunu
    anlayamaz; `sonuc` metni öz-atıf kalıbı taşır."""
    out: list[tuple[str, int | None]] = []
    k = (b.get("izleme") or {}).get("karne") or {}
    if isinstance(k.get("notlanan"), int) and k["notlanan"] > 0:
        # Sayım KÜMÜLATİFTİR (bulten/soz: bütün kayıtlardan) ve hemen altında
        # haftanın kapanan kayıtları durur; etiketsiz "notlanan 39" haftalık
        # gönderide haftada 39 öngörü notlanmış gibi okunuyordu (05.10.2026).
        out.append((f"Karne — şimdiye kadar notlanan {k['notlanan']}: tuttu {k.get('tuttu', 0)} · "
                    f"kısmen {k.get('kismen', 0)} · tutmadı {k.get('tutmadi', 0)}", None))
    ham = str((b.get("gundem") or {}).get("karne") or "")
    toplam = 0
    for p in re.findall(r"<p\b[^>]*>(.*?)</p>", ham, re.S):
        m = re.match(r"\s*<strong>(.*?)</strong>\s*(.*)$", p, re.S)
        if not m:
            continue
        etiket = _duz(m.group(1)).rstrip(".:")
        if KARNE_DISI.search(etiket):
            continue
        metin = _site_disi(_duz(m.group(2)), "karne")
        secim = _satir_sec(metin, 0, esnek=KARNE_SATIR) if metin else ""
        if not secim:
            continue
        satir = f"{etiket}: {secim}"
        if toplam + len(satir) > KARNE_SINIR:
            DUSEN.append(("karne", "karne bütçesi: " + satir))
            continue
        if not out:
            out.append(("Karne", None))
        out.append((satir, 45))
        toplam += len(satir) + 1
    return out


def _haftalik3(b: dict) -> list[dict]:
    bloklar = [_baslik_blogu(b, "Haftaya Bakış")]
    maddeler = _madde_birimleri(b, MADDE_SINIR_HAFTA, lambda i: 70 if i < 3 else 10)
    bloklar.append(_blok("ne_oldu", maddeler))
    bloklar.append(_blok("senaryo", _senaryolar(b), baslik="Senaryolar"))
    bloklar.append(_blok("takvim", _takvim_gunleri(b), baslik="Önümüzdeki hafta"))
    bloklar.append(_blok("karne", _karne(b)))
    govde = _yaz(bloklar)
    bloklar.append(_blok("pano", [(p, 20) for p in _pano(b, govde)], on="Seviyeler: ", ayrac=" · "))
    if not maddeler:
        raise SystemExit("haftalık sayının maddeleri boş — tweet kurulamaz")
    return bloklar


def _bicim2(b: dict) -> list[dict]:
    """Biçim 2 (arşiv): anlatı → Gündem → olağandışı → Pano → Beklenen. Düzen
    yeniden tasarlanmadı; birim kuralı (tam cümle, "…" yok) ve pano/σ
    sözleşmesi aynı."""
    haftalik = bool(b.get("haftalik"))
    oz = b.get("ozet") or {}
    bloklar = [_baslik_blogu(b, "Haftaya Bakış" if haftalik else "Sabah Notu")]
    temel, ek = _okuma_sec(b.get("yorum") or "", YORUM_SINIR)
    if not temel:
        temel, ek = _okuma_sec(oz.get("ne_oldu") or "", YORUM_SINIR, "ne_oldu")
    if not temel:
        raise SystemExit("bültenin okuması da özeti de boş — tweet kurulamaz")
    bloklar.append(_blok("yorum", [(c, None if i == 0 else 60) for i, c in enumerate(temel)]
                         + [(c, 10) for c in ek], ayrac=" "))
    gundem = _gundem_satirlari(b, GUNDEM_PARCA, GUNDEM_SINIR)
    bloklar.append(_blok("gundem", [(s, 40) for s in gundem], baslik="Gündem"))
    sigma_hafta = ((b.get("piyasa") or {}).get("en_cok_hareket") or {}).get("sigma_kip") == "haftalik"
    on, ola = _olagandisi(b, _yaz(bloklar), haftalik=sigma_hafta)
    ne_bek = _site_disi(_duz(oz.get("ne_bekleniyor") or ""), "ne_bekleniyor")
    bek = cumleler(_kirp(ne_bek, BEKLENTI_SINIR)) if ne_bek else []
    etiket = "Önümüzdeki hafta: " if haftalik else "Beklenen: "
    if ne_bek.lower().startswith(etiket.split(":")[0].lower()):
        etiket = ""                      # metin zaten etiketle açılıyor (30.08)
    takvim = _blok("takvim", [(c, None if i == 0 else 75) for i, c in enumerate(bek)],
                   on=etiket, ayrac=" ")
    govde = _yaz(bloklar + [takvim])
    bloklar.append(_blok("olagandisi", [(p, 20) for p in ola], on=on, ayrac=" · "))
    bloklar.append(_blok("pano", [(p, 30) for p in _pano(b, govde)], on="Pano: ", ayrac=" · "))
    bloklar.append(takvim)
    return bloklar


def bulten_zinciri(b: dict) -> list[str]:
    """Günlük/haftalık bültenden TEK uzun tweet (hesap Premium).

    Biçim kararları (30.08 geri bildirimi): link yok, emoji yok. GÖVDE
    yazarın cümleleridir — özetlenmez, seçilir; özetlemek uydurma olurdu.
    Seçim birimi madde, tam cümle ya da satırdır; "…" üretilmez (05.10.2026).
    Bütçe kırpılmamış gövdeden ölçülür ve taşınca birim öncelik sırasıyla
    düşer (`_sigdir`); düşen her birim DUSEN'de görünür."""
    DUSEN.clear()
    if int(b.get("surum") or 2) >= 3:
        bloklar = _haftalik3(b) if b.get("haftalik") else _gunluk3(b)
    else:
        bloklar = _bicim2(b)
    _sigdir(bloklar, KAPASITE)
    govde = _yaz(bloklar)
    if len(govde) > KAPASITE:                     # düşmeyen birimler tavanı aşıyor
        DUSEN.append(("tavan", govde[len(_kirp(govde, KAPASITE)):].strip()))
    return [_kapat(govde, SORUMLULUK_BULTEN)]


# ── kaynak seçimi ────────────────────────────────────────────────────────────

def yazilmis_bulten(tarih: str) -> dict | None:
    yol = BULTENLER / f"{tarih}.json"
    if not yol.exists():
        return None
    b = json.loads(yol.read_text(encoding="utf-8"))
    return b if b.get("gundem_kaynagi") == "yazili" else None
