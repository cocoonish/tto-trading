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
    r"\b[a-z]+_[a-z]+_[a-z]+\b",
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


def tara(metin: str, aileler=AILELER) -> list[tuple[str, str, int]]:
    """(aile, eşleşen metin, satır) üçlüleri döndürür. Boş liste = temiz."""
    m = _maskele(metin or "")
    bulgu = []
    for ad, kaliplar in aileler:
        for kal in kaliplar:
            for e in re.finditer(kal, m, BAYRAK.get(ad, re.IGNORECASE)):
                bulgu.append((ad, e.group(0), m[:e.start()].count("\n") + 1))
    return bulgu
