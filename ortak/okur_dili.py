# -*- coding: utf-8 -*-
"""Okur dili sınavı — yayına çıkan HER metnin ortak süzgeci.

NEDEN VAR
---------
Yayımladığımız metinlerde iki tür cümle birikiyor ve ikisi de okurun
anlayamayacağı, anlasa bile kararını değiştirmeyecek cümleler:

  (1) KOD DİLİ — dosya, anahtar ve boru hattı adları: "ozet.json'dan okunur",
      "metrik.py hata verir", "MDX'e dokunulmadan tazelenir", "itp_b_sabit".
      Okurun elinde bu şeylerin hiçbiri yok.
  (2) YAPIM DİLİ — kendi sürüm tarihçemizin anlatısı: "bu yazının ilk
      sürümünde şu hata vardı", "önceki sürümde şöyle yazıyordu", "kod
      hatasıydı, düzeltildi". Metnin güvenilirliğini artırmıyor; bulguyu
      taşıyan cümle kalmalı, süreç anlatısı gitmeli.

Ayrım ince ama net: "günlük hizalama bu olayı −4,8σ, haftalık +0,4σ verir,
doğrusu haftalıktır" OKURA bir şey söyler; "ilk hesabımız günlüktü ve
yanlıştı" söylemez. Yayımlanmış bir SAYININ düzeltilmesi bunun dışındadır ve
kalır (okur eski sayıya göre karar vermiş olabilir): tarihli, eski/yeni değeri
yazan kısa bir düzeltme notu — ama sürüm tarihçesi anlatmadan.

NEDEN BURADA
------------
Kural bir yerde değil ÜÇ yerde uygulanmalı: site sayfaları (sayfa_sinavi),
bülten (denetim) ve tweetler (ozel/uret). Üç ayrı kalıp listesi tutulsaydı bir
gün sessizce ayrışırlardı — biri "önceki sürümde"yi yakalar, diğeri yakalamaz
ve hangisinin neyi gördüğü kimsenin aklında kalmazdı. Liste bu yüzden TEK
yerde durur; üç denetim de onu içe aktarır.

Kullanım:
    from okur_dili import tara
    for aile, eslesme, satir in tara(metin):
        ...
"""
from __future__ import annotations

import re

# ── (1) KOD DİLİ — okurun elinde olmayan şeylerin adları
KOD_DILI = [
    # dosya adları: veri.py, ozet.json, x.mdx …
    r"\b[a-zçğıöşü_][a-z0-9çğıöşü_]*\.(?:py|json|csv|mdx|astro|yml|yaml)\b",
    # boru hattı sözcükleri
    r"\bMDX\b", r"\bfrontmatter\b",
    r"\bcommit\b", r"\bworkflow\b", r"\bcron\b", r"\bsubprocess\b",
    # "repo" ve "push" BİLEREK YOK: ikisi de piyasa terimi (repo işlemi, fiyat
    # push'u). Bir denetim, kendi alanının sözlüğünü yasaklayamaz.
    # üç parçalı snake_case anahtar (kod bloğu içindekiler hariç tutulur)
    KOD_DILI_ANAHTAR := r"\b[a-z]+_[a-z]+_[a-z]+\b",
]

# ── (2) YAPIM DİLİ — kendi sürüm tarihçemizin anlatısı
YAPIM_DILI = [
    r"(?:yazının|sayfanın|hattın|metnin|bültenin)\s+"
    r"(?:ilk|önceki|eski)\s+(?:sürüm\w*|hâli|hali)\b",
    r"\bilk\s+sürüm(?:de|ün|ümüz|de[nk])?\b",
    r"\bönceki\s+sürüm(?:de|ün)?\b",
    r"\beski\s+(?:kod|sürüm\w*)\b",
    r"\bbu\s+koşuda\s+düzeltildi\b",
    r"\bdüzeltildi\s*[—–-]",
    r"\bkod\s+hatası(?:ydı|dır)?\b",
    r"\bbiz\s+ilk\s+denemede\b",
    r"\bhatayı\s+yaptı\b",
    r"\bilk\s+hesab(?:ımız|ı)\b.{0,40}\byanlış",
    r"\b(?:yanılmıştık|sanmıştık|demiştik)\b",
]

AILELER = (("kod dili", KOD_DILI), ("yapım dili", YAPIM_DILI))

# ── MUAFİYETLER
# Bir şeyin adını ANMAK ile okura onunla konuşmak aynı değil. Üç meşru yer var:
#   · <code>…</code> ve ` … ` — okura gösterilen kod örneği ya da seri kodu
#   · "makine okunur veri özeti" bağlantısı — okura sunulan bir KAYNAK
#   · frontmatter'daki teknik künye alanları DEĞİL: onlar da okura görünür
MUAF = [
    # ETİKET İÇİ MARKUP'TIR, METİN DEĞİL. Okur <Deger anahtar="itp_b_sabit">
    # etiketinin içini görmez, yalnız sonucu görür; aynı şey src, class ve
    # import satırları için de geçerli. Bunları taramak, sayfanın iskeletini
    # okur diline karıştırmak olurdu — ölçüt bir kez böyle koşturuldu ve 951
    # bulgunun tamamı etiket içiydi.
    re.compile(r"^import\s+.*$", re.M),
    # SIRA BAĞLAYICI: kod bloğu ve backtick ÖNCE maskelenir. Genel etiket
    # maskesi <code> ve </code>'u boşluğa çevirirse, kod bloğu maskesi artık
    # eşleşemez ve içerideki ad taranır — okura kod olarak GÖSTERDİĞİMİZ şeyi
    # kod dili sanmak olurdu.
    re.compile(r"```.*?```", re.S),
    re.compile(r"<code>.*?</code>", re.S),
    re.compile(r"`[^`]+`"),
    re.compile(r"<[^<>]{0,600}>", re.S),
    # Markdown bağlantı HEDEFİ ve çıplak URL: okur bağlantıya tıklar, adresini
    # okumaz. Yayımlanmış bir dosyaya verilen bağlantı okura sunulan bir
    # KAYNAKTIR — "uyarilar.json'dan okunur" cümlesiyle aynı şey değil.
    re.compile(r"\]\([^)]*\)"),
    re.compile(r"https?://\S+"),
    re.compile(r"\{/\*.*?\*/\}", re.S),          # MDX yorumu — okur görmez
    re.compile(r"<!--.*?-->", re.S),
    re.compile(r"makine okunur veri özeti\]\([^)]*\)"),
]


def _maskele(metin: str) -> str:
    """Muaf bölgeleri aynı UZUNLUKTA boşlukla değiştir — satır numarası kaymasın."""
    for kal in MUAF:
        metin = kal.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), metin)
    return metin


# Kod dili kalıpları BÜYÜK/küçük harfe DUYARLI koşar; yapım dili duyarsız.
# Sebep: kaynağın kendi büyük harfli alan adları (YLD_YTM_MID, TP.PY.P06.ON)
# okura verilen KAYNAK KÜNYESİDİR, bizim değişken adımız değil. Duyarsız
# koşturulduğunda ölçüt ikisini ayıramıyor ve künyeyi kod dili sanıyordu.
BAYRAK = {"kod dili": 0, "yapım dili": re.IGNORECASE}


def tara(metin: str, aileler=AILELER, maskele: bool = True) -> list[tuple[str, str, int]]:
    """(aile, eşleşen metin, satır) üçlüleri döndürür. Boş liste = temiz.

    maskele=False: muafiyet uygulanmaz. Makine yazımı metin (koşu kaydı) için —
    orada backtick okura kod göstermez, dizge olduğu gibi basılır."""
    m = _maskele(metin or "") if maskele else (metin or "")
    bulgu = []
    for ad, kaliplar in aileler:
        for kal in kaliplar:
            for e in re.finditer(kal, m, BAYRAK.get(ad, re.IGNORECASE)):
                bulgu.append((ad, e.group(0), m[:e.start()].count("\n") + 1))
    return bulgu


# ── (3) KOŞU KAYDI — hatların OPERATÖR için yazdığı uyarı satırları da okura gider.
# Koşu kutusu uyarilar.json'daki `uyarilar` listesini, veri durumu şeridi
# ozet.json'daki `uyari_metni`/`bayat_cumlesi`ni OLDUĞU GİBİ basar. 9. ölçüt
# bu satırları görmüyordu (kaynak MDX değil, veri dosyası) ve `kkm_aktif`
# bayrağı, `bie_pydibsarsiv` grubu, '5.2%' okura gitti. Burada muafiyet yok:
# backtick okura kod göstermez. Kod dili makine metninde daha sıkı — EVDS grup
# kodu (bie_…), iki parçalı anahtar adı (glp_alis), anahtar:tarih çifti
# (m3:2024-06-28), komut satırı anahtarı (--yenile) — ve biçim sözleşmesi de
# sınanır (ortak/bicim: ondalık virgül, tarih GG.AA.YYYY, eksi U+2212).
# Kaynağın BÜYÜK harfli seri kodu (TP.AB.A19) burada da künyedir, taranmaz.
#
# İKİ AĞIRLIK. Backtick, komut anahtarı, dosya adı, bie_ kodu, anahtar:tarih ve
# yapım dili yalnız ŞABLONDAN gelir — veri ne olsa onları üretmez — bu yüzden
# yayın kapısında ENGEL. Snake_case anahtar adı ise çoğu zaman şablondaki bir
# yer tutucudan gelir ('{ad}' bir sütun adıdır) ve serinin bayatladığı gün
# ortaya çıkar; biçim sızıntısı (ondalık nokta, ISO tarih, ASCII eksi) da öyle.
# İkisi "anahtar adı" / "biçim" ailesiyle döner ve kapı onları UYARI olarak
# listeler — bülten denetiminin `bicim` ölçütüyle aynı ağırlık. Veri kaynaklı
# bir sızıntı yüzünden günün bülteni yayımlanmaz olmasın; ama adıyla görünsün.
KOSU_KAYDI_KOD = [
    r"`[^`]+`",
    r"\bbie_[a-z0-9_]+",
    r"\b[a-z][a-z0-9]*:\d{4}-\d{2}-\d{2}\b",
    r"(?<![\w-])--[a-z][\w-]*",
]
KOSU_KAYDI_ANAHTAR = [
    r"\b[a-zçğıöşü][a-z0-9çğıöşü]*_[a-z0-9çğıöşü_]+\b",     # iki ve daha çok parçalı anahtar adı
]
KOSU_KAYDI_ENGEL = ("kod dili", "yapım dili")
KOSU_KAYDI_UYARI = ("anahtar adı", "biçim")
KOSU_KAYDI_BICIM = [
    # ondalık nokta: 5.2 · 0.0 · 0.98765 — binlik nokta (1.234) üç haneli
    # kümedir ve tarih (17.08.2018) iki noktalıdır; ikisi de eşleşmez.
    r"(?<![\w.])\d+\.\d{1,2}(?![\w.])",
    r"(?<![\w.])\d+\.\d{4,}(?![\w.])",
    r"(?<![\w.])\d{4}-\d{2}-\d{2}(?![\w.])",     # ISO tarih; okura GG.AA.YYYY
    r"(?:(?<=\s)|(?<=\()|^)-\d",                  # ASCII eksi; U+2212 yazılır
]


def kosu_kaydi_tara(satirlar) -> list[tuple[int, str, str]]:
    """Koşu kaydı satırları için (satır no, aile, eşleşme). Boş liste = temiz.

    Aileler: "kod dili" ve "yapım dili" (KOSU_KAYDI_ENGEL — şablon kusuru),
    "anahtar adı" ve "biçim" (KOSU_KAYDI_UYARI — veri kaynaklı olabilir).
    Kod ve yapım dili aileleri muafiyetsiz koşar; snake_case anahtar kalıbı
    kod dilinden çıkarılıp kendi ailesine alınır."""
    bulgu: list[tuple[int, str, str]] = []
    gorulen: set[tuple[int, str]] = set()
    def ekle(i, aile, esl):
        if (i, esl) not in gorulen:
            gorulen.add((i, esl))
            bulgu.append((i, aile, esl))
    aileler = (("kod dili", [k for k in KOD_DILI if k != KOD_DILI_ANAHTAR]),
               ("yapım dili", YAPIM_DILI))
    for i, s in enumerate(satirlar, 1):
        s = str(s or "")
        for aile, esl, _sat in tara(s, aileler, maskele=False):
            ekle(i, aile, esl)
        for kal in KOSU_KAYDI_KOD:
            for e in re.finditer(kal, s):
                ekle(i, "kod dili", e.group(0))
        for kal in KOSU_KAYDI_ANAHTAR:
            for e in re.finditer(kal, s):
                ekle(i, "anahtar adı", e.group(0))
        for kal in KOSU_KAYDI_BICIM:
            for e in re.finditer(kal, s, re.M):
                ekle(i, "biçim", e.group(0))
    return bulgu
