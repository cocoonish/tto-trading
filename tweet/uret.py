#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tweet zinciri ÜRETİMİ — yazılmış bültenlerden, deterministik.

Zincir metni yalnız YAYIMLANMIŞ içerikten kurulur: günlük/haftalık bültenin
yazı katmanından geçmiş JSON'u ile teknik analizin yorum kapısından geçmiş
JSON'u. Burada yeni hüküm ÜRETİLMEZ — özet cümleleri yazı katmanının kendi
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
TEKNIKLER = KOK / "site" / "src" / "data" / "teknik"

# Hesap X Premium: 280 sınırı yok, içerik TEK tweet olarak atılır (zincir
# değil). Sınırlar teknik değil editoryal: bölüm başına kırpma + toplam tavan.
# Tavan TEK yerde durur; analiz.py ve denetim.py buradan okur.
TEK_TAVAN = 3800            # tek tweetin toplam üst sınırı (okunurluk)
YORUM_SINIR = 1200          # anlatı gövdesi (bültenin 'okuması'ndan)
GUNDEM_PARCA = 260          # gündem bölümü başına
GUNDEM_SINIR = 1250         # gündem bloğunun tamamı
BEKLENTI_SINIR = 600        # ne_bekleniyor bölümü
GIRIS_SINIR = 700           # teknik giriş bölümü

AYLAR = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
         "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]


def _duz(metin: str) -> str:
    """HTML → düz metin: etiketler söker, varlıkları çözer, boşluk normalleştirir.
    'S&amp;P 500' çözülmeden tweete sızıyor ve HTML kalıntısı engeli günün
    gönderisini düşürüyordu (28.08 ölçüldü)."""
    import html as _html
    m = re.sub(r"<[^>]+>", " ", metin or "")
    m = _html.unescape(m)
    return re.sub(r"\s+", " ", m).strip()


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
_SITE_IZ_RE = re.compile(
    r"(?<![0-9A-Za-zÇĞİIÖŞÜçğıiöşü])(?:" + "|".join(re.escape(i) for i in SITE_IZLERI) + ")")


def _site_izi_var(cumle: str) -> bool:
    alt = cumle.lower()
    return bool(_SITE_IZ_RE.search(alt)) or any(k.search(cumle) for k in SITE_IZ_KALIPLARI)

# Cümle sınırı: nokta TEK BAŞINA yetmez. Türkçede sıra sayısı da noktayla
# yazılır ("12. ayını doldurdu") ve binlik ayracı da noktadır; ham (?<=[.!?])\s+
# bunları cümle sanıp "ayını doldurdu." gibi PARÇA üretiyordu. İki koşul eklendi:
# noktadan önce rakam olmayacak, sonrasında büyük harf gelecek.
_CUMLE = re.compile(r"(?<![0-9])(?<=[.!?])\s+(?=[A-ZÇĞİÖŞÜ\"«(])")

# Bir cümle düşünce ondan SONRAKİ cümle öksüz kalabilir: "İkincisi aynı
# dosyanın..." ya da "Hafta sonu bu soruya..." — göndergesi silinmiş bir metin
# tweette anlamsız durur. Öncesi düşmüşse ve cümle ilk sözcüklerinde geriye
# atıf taşıyorsa o da düşer; zincirleme sürer.
_ANAFORA = {"bu", "bunu", "bunun", "buna", "bunlar", "bundan", "o", "onu",
            "onun", "aynı", "ikincisi", "üçüncüsü", "böylece", "dolayısıyla",
            "ayrıca", "oysa", "buradaki", "yani", "söz"}


# Düşen cümleler GÖRÜNÜR tutulur: gonder.py kuru ve gerçek koşuda listeler,
# denetim oranı ölçer. Sessizce silinen bir cümle, yazı katmanının bir daha
# aynı hatayı yapmasına yol açar; görünen cümle geri bildirimdir.
DUSEN: list[tuple[str, str]] = []


def _site_disi(metin: str, bolum: str = "") -> str:
    """Siteye/bültene atıf yapan cümleleri ve öksüz kalan devamlarını düşürür."""
    kalan, onceki_dustu = [], False
    for c in _CUMLE.split(metin or ""):
        if not c.strip():
            continue
        dus = _site_izi_var(c)
        if not dus and onceki_dustu:
            bas = [w.strip('"\'(),;:.') for w in c.lower().split()[:6]]
            dus = any(w in _ANAFORA for w in bas)
        if dus:
            onceki_dustu = True
            DUSEN.append((bolum, c.strip()))
            continue
        onceki_dustu = False
        kalan.append(c)
    return re.sub(r"\s+", " ", " ".join(kalan)).strip()


# Gündem katmanı bültende 12 bölüm; tweete haber değeri en yüksek beşi girer.
GUNDEM_BOLUMLERI = (
    ("kilit", "Kilit gelişme"),
    ("tr_makro", "Türkiye makro"),
    ("tr_politika", "Türkiye politika"),
    ("global_politika", "Jeopolitik"),
    ("global_makro", "Küresel makro"),
)


# Kelime kırpmasının sonunda kalamayacak sözcükler: bağlaç, edat, sayı.
_ASILI = {"ve", "ile", "ama", "veya", "ya", "da", "de", "ki", "için", "gibi", "kadar",
          "göre", "sonra", "önce", "ancak", "fakat", "yani", "çünkü", "bir", "bu", "o"}
_ASILI_SON = re.compile(r"(?:\d|%|[(,;:—–-])$")


def _kirp(metin: str, sinir: int) -> str:
    """Sınıra sığdırır — üç kademede, en okunurundan başlayarak.

    1. Sınır içinde TAM cümle(ler) varsa orada kes (en az 80 karakter kalsın).
    2. Cümle yoksa yan tümce sınırı: '; ' ': ' ' — ' ', ' (en az 80 karakter).
    3. Yoksa kelime sınırında kes ve '…' ekle — ama son sözcük bağlaç/edat ya
       da sayı ise onu da düşür: "…gündeme geldi ve…" ile "…%1,…" okura yarım
       bir cümlenin ortasında kalmış hissi verir (31.08 ve 01.09 gönderilerinde
       görüldü; kalite kapısı bu ikisini ENGEL sayar).

    Eski eşik "cümle sonu sınırın yarısını geçsin"di: 260 karakterlik pencerede
    125 karakterlik tam bir cümle reddediliyor, yerine kelime ortası kırpma
    seçiliyordu — ve 've' ile biten bir gündem satırı yayına gidiyordu.
    """
    m = metin.strip()
    if len(m) <= sinir:
        return m
    kes = -1
    for isaret in (". ", "! ", "? "):
        i = m.rfind(isaret, 0, sinir)
        kes = max(kes, i + 1 if i > 0 else -1)
    if kes >= 80:
        return m[:kes].strip()
    for isaret in ("; ", ": ", " — ", " – ", ", "):
        i = m.rfind(isaret, 0, sinir - 1)
        if i >= 80:
            return m[:i].rstrip(" ,;:—–") + "…"
    i = m.rfind(" ", 0, sinir - 1)
    govde = (m[:i] if i > 0 else m[:sinir - 1]).rstrip(" ,;:·(—–-")
    sozcukler = govde.split(" ")
    while sozcukler and (sozcukler[-1].lower().strip("\"'()") in _ASILI or _ASILI_SON.search(sozcukler[-1])):
        sozcukler.pop()
    govde = " ".join(sozcukler).rstrip(" ,;:·(—–-")
    return govde + "…"


def _etiketle(etiket: str, metin: str) -> str:
    """'Kilit gelişme: Günün kilit gelişmesi …' ikilemesini önler: cümlenin ilk
    altı sözcüğü etiketin kök sözcüklerini taşıyorsa etiket düşer."""
    kokler = {k[:5].lower() for k in etiket.split() if len(k) > 3}
    bas = [w.strip('"\'(),;:.').lower()[:5] for w in metin.split()[:6]]
    if kokler and kokler <= set(bas):
        return metin
    return f"{etiket}: {metin}"


def _tipografi(metin: str) -> str:
    """Yalnız gönderi metnine: aralık tiresi '–', sayı önünde eksi '−'."""
    # Yıl-ay yazımı ("2024-05") aralık değildir: dört haneli sayıdan sonraki tire kalır.
    m = re.sub(r"(?<!\d{4})(?<!\d{4}-\d{2})(?<=\d)-(?=%?\d)", "–", metin)   # 2026-09-01 dokunulmaz
    m = re.sub(r"(?<![\w.,])-(?=[%\d])", "−", m)
    return m


# SORUMLULUK NOTU her gönderinin son satırıdır ve kırpmadan MUAFTIR. Eskiden
# not gövdeyle birlikte tavana kırpılıyordu: uzun bir sabah gövdesi notu
# düşürebilirdi ve kimse fark etmezdi. Şimdi gövde, notun payı düşülerek
# kırpılır; not her koşulda yerinde kalır. Bültende "bülten" sözcüğü
# kullanılmaz — o sözcük site atfı izidir ve tweet kendi başına durur.
SORUMLULUK_BULTEN = "Ölçüm ve yorumdur; yatırım tavsiyesi değildir."
SORUMLULUK_TEKNIK = "Analizdir; yatırım tavsiyesi değildir."


def _kapat(govde: str, not_: str, tavan: int = TEK_TAVAN) -> str:
    """Gövdeyi tavana sığdır, tipografiyi düzelt, sorumluluk notunu SONRA ekle."""
    return _tipografi(_kirp(govde, tavan - len(not_) - 2)) + "\n\n" + not_


def _tr_sayi(x: float, ondalik: int = 2) -> str:
    s = f"{x:+,.{ondalik}f}"
    return s.replace(",", "@").replace(".", ",").replace("@", ".")


def _fiyat(x, ondalik: int = 2) -> str:
    """İşaretsiz Türkçe sayı: 14641.6 → '14.641,6'."""
    if x is None:
        return "—"
    nd = max(int(2 if ondalik is None else ondalik), 1)
    s = f"{float(x):,.{nd}f}".replace(",", "@").replace(".", ",").replace("@", ".")
    return s.rstrip("0").rstrip(",") if "," in s else s


def _degisim_metni(x: float, birim: str) -> str:
    """Türkçe yazımla işaretli değişim: %'de işaret öne gelir (+%5,98)."""
    if abs(x) < 0.005:
        return "yatay"
    isaret = "+" if x > 0 else "−"
    govde = _tr_sayi(abs(x)).lstrip("+")
    if birim.strip() == "%":
        return f"{isaret}%{govde}"
    return f"{isaret}{govde}{birim}"


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


# ── bülten zinciri ───────────────────────────────────────────────────────────

def bulten_zinciri(b: dict) -> list[str]:
    """Günlük/haftalık bültenden TEK uzun tweet (hesap Premium).

    Biçim kararları (30.08 geri bildirimi): link yok, emoji yok; hareketler
    ve pano tek satırda '·' ile. GÖVDE ANLATIDIR: sayı dökümü olan özet değil,
    bültenin 'okuması' (yorum) kullanılır — hesap, piyasanın NEDEN böyle
    hareket ettiğinin tercümanı; ne oldu / neden oldu / ne bekleniyor."""
    haftalik = bool(b.get("haftalik"))
    baslik = "Haftaya Bakış" if haftalik else "Sabah Notu"
    tarih = _tr_tarih(b["tarih"])

    oz = b.get("ozet") or {}
    DUSEN.clear()
    anlati = _site_disi(_duz(b.get("yorum") or ""), "yorum") or _site_disi(_duz(oz.get("ne_oldu") or ""), "ne_oldu")
    if not anlati:
        raise SystemExit("bültenin okuması da özeti de boş — tweet kurulamaz")
    bolumler = [f"{baslik} — {tarih}", _kirp(anlati, YORUM_SINIR)]

    # GÜNDEM. Bültenin en zengin katmanı tweete hiç girmiyordu (31.08 geri
    # bildirimi: "daha çok gündem verilmeli"). Her bölümün girişi alınır —
    # özetlenmez, kırpılır; özetlemek uydurma olurdu.
    gundem = b.get("gundem") or {}
    satirlar, toplam = [], 0
    for anahtar, etiket in GUNDEM_BOLUMLERI:
        parca = _site_disi(_duz(gundem.get(anahtar) or ""), anahtar)
        if not parca:
            continue
        satir = _etiketle(etiket, _kirp(parca, GUNDEM_PARCA))
        if toplam + len(satir) > GUNDEM_SINIR:
            break
        satirlar.append(satir)
        toplam += len(satir) + 1
    if satirlar:
        bolumler.append("Gündem\n" + "\n".join(satirlar))

    em = (b.get("piyasa") or {}).get("en_cok_hareket") or {}
    kip = em.get("sigma_kip") or ("haftalik" if haftalik else "gunluk")
    liste = em.get(kip) or []
    if liste:
        etiket = ("Haftanın öne çıkanları" if kip == "haftalik"
                  else "Günün öne çıkanları")
        parcalar = [f"{h['ad']} {_degisim_metni(h['deger'], h.get('birim', ''))}"
                    for h in liste[:5] if h.get("deger") is not None]
        bolumler.append(f"{etiket}: " + " · ".join(parcalar))

    # PANO: birim ve veri tarihi de yazılır. "Net rezerv 66,9 (−0,2)" 1 Eylül
    # gönderisinde 21 Ağustos'un haftalık serisiydi ve okur bunu bilemezdi;
    # sitede her sayının yanında tarihi yazar, gönderide de yazmalı.
    gost = b.get("gostergeler") or []
    parcalar = []
    for g in gost[:5]:
        if not (g.get("metin") and g.get("ad")):
            continue
        birim = (g.get("birim") or "").strip()
        deger = f"%{g['metin']}" if birim == "%" else (f"{g['metin']} {birim}" if birim else g["metin"])
        fark = f" ({g['fark_metin']})" if g.get("fark_metin") else ""
        tarih = ""
        vt = str(g.get("veri_tarihi") or "")
        if vt and vt[:10] != b["tarih"] and _tr_kisa_tarih(vt) and _tr_kisa_tarih(vt) != _tr_kisa_tarih(b["tarih"]):
            tarih = f" · {_tr_kisa_tarih(vt)}"
        parcalar.append(f"{g['ad']} {deger}{fark}{tarih}")
    if parcalar:
        bolumler.append("Pano: " + " · ".join(parcalar))

    ne_bek = _site_disi(_duz(oz.get("ne_bekleniyor") or ""), "ne_bekleniyor")
    if ne_bek:
        etiket = "Önümüzdeki hafta: " if haftalik else "Beklenen: "
        # Metin zaten etiketle başlıyorsa ikilenmesin ("Önümüzdeki hafta:
        # Önümüzdeki hafta takvimde..." — 30.08 taslağında görüldü).
        if ne_bek.lower().startswith(etiket.split(":")[0].lower()):
            bolumler.append(_kirp(ne_bek, BEKLENTI_SINIR))
        else:
            bolumler.append(etiket + _kirp(ne_bek, BEKLENTI_SINIR))
    return [_kapat("\n\n".join(bolumler), SORUMLULUK_BULTEN)]


# ── teknik zinciri ───────────────────────────────────────────────────────────

KISA_AD = {"us2y": "ABD 2Y", "us10y": "ABD 10Y", "dxy": "DXY",
           "eurusd": "EUR/USD", "usdchf": "USD/CHF", "xu100": "BIST 100"}


def _teknik_satir(e: dict) -> str | None:
    d1 = (e.get("degisim") or {}).get("h1")
    ondalik = e.get("ondalik")
    birim = " bp" if e.get("tip") == "getiri" else "%"
    ad = KISA_AD.get(e.get("slug"), e.get("ad", "?"))
    parca = f"{ad} {_fiyat(e.get('son'), ondalik)}"
    if d1 is not None:
        parca += f" — hafta {_degisim_metni(d1, birim)}"
    # yapı bayrağı: en bilgilendirici olanı tek kelimeyle
    gun = (e.get("dilimler") or {}).get("gun") or {}
    s1 = (e.get("dilimler") or {}).get("s1") or {}
    for kaynak, ad_ in ((s1, "1s"), (gun, "günlük")):
        y = kaynak.get("yapi") or {}
        if y.get("sikisma"):
            return parca + f"; {ad_} grafikte sıkışma"
        if y.get("cift_tepe"):
            return parca + f"; {ad_} çift tepe {_fiyat(y['cift_tepe']['seviye'], ondalik)}"
        if y.get("cift_dip"):
            return parca + f"; {ad_} çift dip {_fiyat(y['cift_dip']['seviye'], ondalik)}"
    return parca




def teknik_zinciri(t: dict) -> list[str]:
    """Haftalık teknik analizden TEK uzun tweet (hesap Premium).

    Biçim: link yok, emoji yok; enstrüman satırları sade, kapanışta kısa
    sorumluluk notu (analizdir, tavsiye değildir)."""
    tarih = _tr_tarih(t["tarih"])
    DUSEN.clear()
    giris = _site_disi(_duz(t.get("giris") or ""), "giris")
    if not giris:
        raise SystemExit("teknik giriş boş — tweet kurulamaz")
    bolumler = [f"Haftalık Teknik Analiz — {tarih}", _kirp(giris, GIRIS_SINIR)]

    satirlar = [s for s in (_teknik_satir(e) for e in t.get("enstrumanlar") or [])
                if s]
    if satirlar:
        bolumler.append("1 saatlik, 4 saatlik ve günlük grafiklerden özet:\n"
                        + "\n".join(satirlar))

    return [_kapat("\n\n".join(bolumler), SORUMLULUK_TEKNIK)]


# ── kaynak seçimi ────────────────────────────────────────────────────────────

def yazilmis_bulten(tarih: str) -> dict | None:
    yol = BULTENLER / f"{tarih}.json"
    if not yol.exists():
        return None
    b = json.loads(yol.read_text(encoding="utf-8"))
    return b if b.get("gundem_kaynagi") == "yazili" else None


def yazilmis_teknik(tarih: str) -> dict | None:
    yol = TEKNIKLER / f"{tarih}.json"
    if not yol.exists():
        return None
    t = json.loads(yol.read_text(encoding="utf-8"))
    return t if t.get("yazili") else None
