#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bülten — kaynak taraması (RSS/Atom).

Kurum duyuruları (TCMB, Resmî Gazete) ve haber akışları taranır, son N saatte
çıkanlar alınır, başlıklar tekilleştirilir.

Tasarım kararları:
· feedparser varsa kullanılır; yoksa saf ElementTree ile ayrıştırılır. CI'da tek
  bir paketin eksikliği bülteni düşürmesin diye iki yol da var.
· Bir kaynak düşerse (ağ, biçim) o kaynak atlanır ve bültende "okunamadı" olarak
  GÖRÜNÜR. Sessizce boş dönmek, 'bugün haber yok' yalanını üretirdi.
· Yorum yok, duygu skoru yok: başlık ve bağlantı. Yorum katmanı ayrı.
"""
from __future__ import annotations

import html
import json
import re
import unicodedata
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

from ayar import (HABER_KAYNAKLARI, HABER_SINIRI, HABER_ILGILI, HABER_GURULTU,
                  TCMB_DUYURU_URL, RESMI_GAZETE_URL, RG_ILGILI,
                  ABD_HAZINE_URL, ABD_HAZINE_ILGILI,
                  ALAN_KALIPLARI, BOLGE_KALIPLARI, HABER_BOLUMLERI, BOLUM_SINIRI,
                  KAYNAK_PUANI, ONEM_KALIPLARI, KILIT_ESIK, KILIT_SINIRI)


@dataclass
class Haber:
    baslik: str
    baglanti: str
    kaynak: str
    etiket: str = ""
    zaman: str = ""
    kurum: bool = False
    ozet: str = ""            # akıştaki açıklama metni — bültenin "ayrıntı"sı buradan gelir
    bolge: str = ""           # tr | global
    alan: str = ""            # makro | politika | piyasa | kurum
    kaynak_sayisi: int = 1    # aynı öyküyü kaç yayın yazdı
    onem: float = 0.0         # hesaplanan önem puanı


def _getir(url: str, zaman_asimi=20, dogrulama: bool = True) -> str | None:
    try:
        import requests
        if not dogrulama:
            import urllib3
            urllib3.disable_warnings()
        r = requests.get(url, timeout=zaman_asimi, verify=dogrulama, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "Accept": "application/rss+xml, application/xml, text/xml, */*"})
        return r.text if r.ok else None
    except Exception:
        return None


def _zaman_coz(m: str | None) -> datetime | None:
    if not m:
        return None
    try:
        return parsedate_to_datetime(m)
    except Exception:
        pass
    for kalip in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
        try:
            t = datetime.strptime(m.strip(), kalip)
            return t if t.tzinfo else t.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _temiz(m: str, azami: int = 700) -> str:
    """Akış açıklamasındaki HTML'i at, kırp. Bülten okunabilir cümle ister."""
    # İki kez kaçışlanmış metin var (&amp;#039; → &#039; → '); iki geçiş gerekiyor.
    m = html.unescape(html.unescape(m or ""))
    m = re.sub(r"<[^>]+>", " ", m)
    m = re.sub(r"\s+", " ", m).strip()
    # Bazı akışlar açıklamaya kaynak adını ve "devamı" bağlantısını ekliyor.
    m = re.sub(r"(Devamı|Devamını oku|Read more|Continue reading).*$", "", m, flags=re.I).strip()
    return m[:azami].rstrip(" ,;:-") + ("…" if len(m) > azami else "")


def _ayristir(xml_metin: str) -> list[tuple[str, str, "datetime | None", str]]:
    """(başlık, bağlantı, zaman, özet). feedparser varsa o, yoksa ElementTree."""
    try:
        import feedparser
        d = feedparser.parse(xml_metin)
        out = []
        for e in d.entries:
            t = None
            if getattr(e, "published_parsed", None):
                from calendar import timegm
                t = datetime.fromtimestamp(timegm(e.published_parsed), tz=timezone.utc)
            ozet = getattr(e, "summary", "") or getattr(e, "description", "")
            out.append((getattr(e, "title", ""), getattr(e, "link", ""), t, _temiz(ozet)))
        if out:
            return out
    except Exception:
        pass
    try:
        import xml.etree.ElementTree as ET
        kok = ET.fromstring(xml_metin.encode("utf-8", "replace"))
    except Exception:
        return []
    out = []
    for oge in kok.iter():
        etiket = oge.tag.split("}")[-1]
        if etiket not in ("item", "entry"):
            continue
        def al(*adlar):
            for c in oge:
                if c.tag.split("}")[-1] in adlar:
                    return (c.text or "").strip() or (c.attrib.get("href") or "")
            return ""
        out.append((al("title"), al("link"), _zaman_coz(al("pubDate", "updated", "published")),
                    _temiz(al("description", "summary", "content"))))
    return out


def _sadelestir(b: str) -> str:
    b = unicodedata.normalize("NFKD", html.unescape(b or "")).lower()
    b = re.sub(r"[^a-z0-9ğüşiöç ]", "", b)
    # Boşlukları daralt: " - " iki boşluğa dönüşüyor ve "özet başlığın aynısı mı"
    # karşılaştırmasını sessizce bozuyordu.
    return re.sub(r"\s+", " ", b).strip()


def _ilgili_mi(baslik: str, ozet: str = "") -> bool:
    """Alaka BAŞLIKTAN karara bağlanır; gürültü hem başlıkta hem özette aranır.

    Özette alaka aramak yanlış pozitif üretiyordu: akış açıklaması haberin ilk
    cümlesi olduğu için içinde "ekonomi" ya da "altın" rastgele geçebiliyor ve
    turşu haberi makro bültenine düşüyordu.
    """
    b = (baslik or "").lower()
    if re.search(HABER_GURULTU, b + " " + (ozet or "").lower(), re.I):
        return False
    return bool(re.search(HABER_ILGILI, b, re.I))


def _kaynak_puani(h: "Haber") -> int:
    metin = f"{h.kaynak} {h.baslik}".lower()
    return max((p for ad, p in KAYNAK_PUANI.items() if ad in metin), default=0)


def _ozet_ise_yarar(baslik: str, ozet: str) -> str:
    """Akış açıklaması başlığın tekrarıysa at.

    Google News açıklamayı "başlık + gazete adı" olarak veriyor; bunu bültende
    özet diye göstermek okura bir şey katmaz, yer kaplar.
    """
    if not ozet:
        return ""
    b = _sadelestir(baslik)
    o = _sadelestir(ozet)
    if not o or o.startswith(b[:60]) or b.startswith(o[:60]):
        return ""
    return ozet


def tcmb_duyurulari(pencere_gun: int = 3) -> tuple[list[Haber], bool]:
    """TCMB Basın Duyuruları listesi (RSS yok; liste sayfası düz HTTP ile okunur).

    Bu kaynak bültenin en değerlisi: faiz kararı, makroihtiyati çerçeve, TL likidite
    yönetimi, swap ve zorunlu karşılık düzenlemeleri hep buradan çıkar. Haber
    süzgecine SOKULMAZ — kurum duyurusu 'alakalı mı' diye elenmez.
    Dönüş: (duyurular, okundu_mu).
    """
    yil = datetime.now().year
    ham = _getir(TCMB_DUYURU_URL.format(yil=yil), 25)
    if not ham:
        return [], False
    # Liste: <a href="…DUY2026-35">Başlık (2026-35)</a> … ve ayrı bir alanda gg/aa/yyyy
    kayitlar: list[Haber] = []
    parcalar = re.split(r'(?=href="[^"]*DUY\d{4}-\d+")', ham)
    sinir = datetime.now() - timedelta(days=pencere_gun)
    for parca in parcalar:
        m = re.match(r'href="([^"]*DUY(\d{4})-(\d+))"[^>]*>\s*([^<]{8,200}?)\s*</a>', parca)
        if not m:
            continue
        link, yil_s, no, baslik = m.groups()
        t = re.search(r"(\d{2})/(\d{2})/(\d{4})", parca[:1500])
        zaman = None
        if t:
            try:
                zaman = datetime(int(t.group(3)), int(t.group(2)), int(t.group(1)))
            except ValueError:
                zaman = None
        if zaman and zaman < sinir:
            continue
        if not zaman:
            continue
        baslik = html.unescape(baslik).strip()
        if not link.startswith("http"):
            link = "https://www.tcmb.gov.tr" + link
        kayitlar.append(Haber(baslik, link, "TCMB Basın Duyuruları", "kurum",
                              zaman.isoformat(), True, "", "tr", "kurum"))
    return kayitlar, True


def resmi_gazete() -> tuple[list[Haber], bool]:
    """Bugünkü Resmî Gazete içindekiler — finans/makro ilgisi olanlar.

    RSS yok; ana sayfa günün içindekiler listesini düz HTML olarak veriyor.
    NOT: resmigazete.gov.tr ara sertifikayı sunmadığı için TLS zinciri kurulamıyor
    ve doğrulama YALNIZ bu istekte kapatılıyor. Salt-okunur kamu içeriği; kimlik
    bilgisi gönderilmiyor, yalnız başlık okunuyor. Sertifika düzelirse bu istisna
    kaldırılmalı.
    """
    ham = _getir(RESMI_GAZETE_URL, 20, dogrulama=False)
    if not ham:
        return [], False
    duz = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "|", ham))
    bas = duz.find("YÜRÜTME VE İDARE")
    if bas < 0:
        return [], False
    kesit = duz[bas:bas + 12000]
    out: list[Haber] = []
    bugun = datetime.now().strftime("%Y-%m-%d")
    for parca in re.split(r"\|{2,}", kesit):
        baslik = parca.strip(" |–-").strip()
        if not (12 < len(baslik) < 240):
            continue
        if not re.search(RG_ILGILI, baslik, re.I):
            continue
        if re.search(r"Günlük Değerleri", baslik, re.I):      # her gün çıkan rutin ilan
            continue
        out.append(Haber(html.unescape(baslik), RESMI_GAZETE_URL, "Resmî Gazete",
                         "kurum", bugun, True, "", "tr", "kurum"))
    return out[:8], True


def _kumele(haberler: list[Haber], esik: float = 0.40) -> list[Haber]:
    """Aynı öyküyü anlatan başlıkları teke indir.

    Bir haber on gazetede çıkıyor ("TCMB repo ihalelerine dönüyor" ×10) ve bülten
    on satır olarak gösteriyordu. Başlık kelime kümeleri arasındaki Jaccard
    benzerliği eşiği aşarsa aynı öykü sayılır; temsilci olarak İLK (kurum ya da
    en yeni) başlık kalır, kalanların sayısı 'kaynak' bilgisine yazılır.
    """
    ESANLAM = {"merkez": "tcmb", "bankasi": "", "bankası": "", "bankasindan": "tcmb",
               "cumhuriyet": "", "turkiye": "", "türkiye": ""}
    ETKISIZ = {"icin", "için", "ile", "olarak", "sonra", "once", "önce", "yeni", "yeniden",
               "haberi", "son", "dakika", "aciklama", "açıklama", "karar", "kararı"}

    def kume(b: str) -> set[str]:
        # Gazete eki ("… - Sözcü Gazetesi") kümelemeyi bozuyor; atılır.
        b = re.split(r"\s+[-–—]\s+[^-–—]{3,40}$", b)[0]
        kelime = []
        for k in _sadelestir(b).split():
            k = ESANLAM.get(k, k)
            if not k or k in ETKISIZ or len(k) <= 2:
                continue
            # Türkçe eklemeli dil: "ihalelerine"/"ihalesine"/"ihaleleri" aynı köke
            # inmezse aynı öykü farklı öykü sanılır. Kaba ama işe yarayan kısaltma.
            kelime.append(k[:5])
        return set(kelime)

    kalanlar: list[Haber] = []
    kumeler: list[tuple[set[str], Haber, int]] = []
    for h in haberler:
        kh = kume(h.baslik)
        if not kh:
            continue
        eslesen = None
        for i, (kk, temsil, n) in enumerate(kumeler):
            ortak = len(kh & kk)
            if ortak / max(1, min(len(kh), len(kk))) >= esik:
                eslesen = i
                break
        if eslesen is None:
            kumeler.append((kh, h, 1))
        else:
            kk, temsil, n = kumeler[eslesen]
            # Temsilci, kümedeki EN İTİBARLI kaynak olsun: aynı öyküyü Reuters de
            # bir içerik çiftliği de yazmış olabilir; bültende Reuters görünsün.
            # Özeti olan kayıt, özeti olmayana eşit puanda tercih edilir.
            yeni_temsil = temsil
            if (_kaynak_puani(h), bool(h.ozet)) > (_kaynak_puani(temsil), bool(temsil.ozet)):
                yeni_temsil = h
            kumeler[eslesen] = (kk | kh, yeni_temsil, n + 1)
    for _, temsil, n in kumeler:
        temsil.kaynak_sayisi = n
        if n > 1:
            temsil.kaynak = f"{temsil.kaynak} (+{n - 1} kaynak)"
        kalanlar.append(temsil)
    return kalanlar


def _siniflandir(baslik: str, ozet: str, kaynak_bolge: str, kaynak_alan: str) -> tuple[str, str]:
    """(bölge, alan). Kaynağın varsayılanı, metindeki kalıplarla ezilebilir.

    Neden ezilsin: AA Dünya akışında bir ABD enflasyon haberi çıkabiliyor, Bloomberg
    HT'de bir seçim haberi. Kaynağa göre sabitlemek bültende yanlış bölüme düşürürdü.
    """
    metin = f"{baslik} {ozet}".lower()
    alan = kaynak_alan if kaynak_alan != "karisik" else ""
    # Alan: politika > makro > piyasa sırasıyla bakılır; politika en ayırt edici.
    for ad in ("politika", "makro", "piyasa"):
        if re.search(ALAN_KALIPLARI[ad], metin, re.I):
            alan = ad
            break
    if not alan:
        alan = "makro"
    bolge = kaynak_bolge if kaynak_bolge != "karisik" else ""
    tr = re.search(BOLGE_KALIPLARI["tr"], metin, re.I)
    gl = re.search(BOLGE_KALIPLARI["global"], metin, re.I)
    if tr and not gl:
        bolge = "tr"
    elif gl and not tr:
        bolge = "global"
    elif tr and gl and not bolge:
        bolge = "tr"          # ikisi de geçiyorsa Türkiye açısı öne alınır
    if not bolge:
        bolge = "global"
    return bolge, alan


def abd_hazine_duyurulari(pencere_gun: int = 7) -> tuple[list[Haber], bool]:
    """ABD Hazinesi basın duyuruları — borç yönetimi operasyonları.

    Neden ayrı bir kaynak: geri alım (buyback) büyüklüğü, üç aylık refinansman,
    ihale takvimi ve nakit yönetimi Hazine'nin işidir, merkez bankasının değil.
    Fed/ECB odaklı haber aramaları bunları getirmez; genel haber akışları da
    çoğu zaman taşımaz. Oysa uzun vadeli faizin ve doların haftalık hareketi
    bazen tamamen buradan gelir.
    Dönüş: (duyurular, okundu_mu).
    """
    yil = datetime.now().year
    ham = _getir(ABD_HAZINE_URL.format(yil=yil), 25)
    if not ham:
        return [], False
    try:
        maddeler = json.loads(ham).get("items", [])
    except Exception:
        return [], False
    sinir = (datetime.now() - timedelta(days=pencere_gun)).strftime("%Y-%m-%d")
    out = []
    for m in maddeler:
        tarih = str(m.get("date", ""))[:10]
        if tarih < sinir:
            continue
        baslik = (m.get("title") or "").strip()
        if not re.search(ABD_HAZINE_ILGILI, baslik, re.I):
            continue
        url = m.get("url") or ""
        if url and not url.startswith("http"):
            url = "https://home.treasury.gov" + url
        out.append(Haber(baslik, url, "ABD Hazinesi", "kurum", tarih, True, "",
                         "global", "kurum_global"))
    return out, True


def onem_puani(h: Haber) -> float:
    """Haberin piyasa önemi: konu ağırlığı + kaynak itibarı + yayılma.

    Neden gerekli: bülten haberleri bölümlere dağıtıyor ama hepsini eşit ağırlıkta
    gösteriyordu. Bir borç yönetimi kararı ile bir atama haberi aynı satırda
    duruyordu; haftanın ana sürücüsü bu yüzden gözden kaçtı.
    """
    metin = f"{h.baslik} {h.ozet}".lower()
    konu = 0
    for agirlik, kalip in ONEM_KALIPLARI:
        if re.search(kalip, metin, re.I):
            konu = max(konu, agirlik)
    puan = float(konu)
    puan += _kaynak_puani(h) / 5.0                 # itibar: en fazla +2
    puan += min(h.kaynak_sayisi - 1, 6) * 0.5      # yayılma: en fazla +3
    if h.kurum:
        puan += 3.0                                # birincil kaynak: haber değil olay
    if h.ozet:
        puan += 0.5                                # ne olduğu belli
    return round(puan, 2)


def kilit_gelismeler(haberler: list[Haber]) -> list[Haber]:
    """Eşiği aşan, bültenin başında ayrıntılı işlenecek maddeler."""
    for h in haberler:
        h.onem = onem_puani(h)
    aday = [h for h in haberler if h.onem >= KILIT_ESIK]
    aday.sort(key=lambda h: (h.onem, h.zaman or ""), reverse=True)
    return aday[:KILIT_SINIRI]


def bolumle(haberler: list[Haber], zengin: int = 26) -> tuple[list[dict], list[dict]]:
    """Haberleri sayfadaki bölümlere dağıt, sonra GÖRÜNECEK olanları zenginleştir.

    Sıra önemli: önce zenginleştirip sonra seçmek, kaynağından okunan özetlerin
    bültene girmeyen maddelere harcanmasına yol açıyordu. Şimdi önce hangi
    maddelerin görüneceği belli oluyor, istek yalnız onlar için yapılıyor.
    """
    out, gorunen = [], []
    kilit = kilit_gelismeler(haberler)
    kilit_kimlik = {id(h) for h in kilit}
    for bid, baslik, bolge, alan in HABER_BOLUMLERI:
        if alan == "kilit":
            secilen = kilit
        elif alan in ("kurum", "kurum_global"):
            secilen = [h for h in haberler if h.kurum and h.alan == alan]
        else:
            aday = [h for h in haberler
                    if not h.kurum and h.bolge == bolge and h.alan == alan]
            # Bölüm dolduğunda, özeti OLAN madde çıplak başlığa tercih edilir:
            # okur için "ne olduğu" bilgisi, dakikalık tazelikten değerlidir.
            aday.sort(key=lambda h: (bool(h.ozet), h.zaman or ""), reverse=True)
            secilen = aday[:BOLUM_SINIRI]
        if secilen:
            gorunen.extend(secilen)
            out.append({"id": bid, "baslik": baslik, "secilen": secilen})
    try:
        zenginlestir(gorunen, azami=zengin)
    except Exception:
        pass
    # Dondurma EN SONDA ve TEK yerde: kilit listesi burada üretilip döndürülür,
    # çağıran taraf kilit_gelismeler()'i ikinci kez çağırmasın. İkinci çağrı
    # zenginleştirmeden sonra koştuğu için FARKLI puanlar üretiyordu ve aynı
    # JSON'da aynı haber iki ayrı önem puanıyla yazılıyordu.
    return ([{"id": b["id"], "baslik": b["baslik"],
              "maddeler": [asdict(h) for h in b["secilen"]]} for b in out],
            [asdict(h) for h in kilit])


# ─────────────────────────── haberi kaynağından zenginleştir
from pathlib import Path as _Path
OZET_ONBELLEK = _Path(__file__).resolve().parent / "onbellek" / "haber_ozet.json"


def _onbellek_oku() -> dict:
    try:
        return json.loads(OZET_ONBELLEK.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _onbellek_yaz(d: dict):
    try:
        OZET_ONBELLEK.parent.mkdir(exist_ok=True)
        # Sınırsız büyümesin: en son 500 kayıt yeter.
        if len(d) > 500:
            d = dict(list(d.items())[-500:])
        OZET_ONBELLEK.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


# Sayfaların site geneli açıklamaları özet sanılıyordu: Google News her makale için
# aynı tanıtım cümlesini, TCMB her sayfada kurum tanımını veriyor. Bunlar bilgi değil.
KLISE = re.compile(
    r"comprehensive up-to-date news coverage|aggregated from sources all over the world|"
    r"merkez bankasının temel amacı|son dakika haberleri ve güncel|"
    r"en son haberler|breaking news, latest news|çerez|cookie polic", re.I)


def _tcmb_duyuru_govdesi(ham: str) -> str:
    """TCMB duyuru sayfasından ASIL metni çıkar.

    Sayfa şablonu: "Sayı: 2026-NN" → tarih → başlık → gövde → "Kamuoyunun bilgisine".
    Kurum duyuruları bültenin en değerli maddesi; site geneli açıklamayla yetinmek
    tam da bu maddede bilgi kaybı olurdu.
    """
    duz = re.sub(r"<script.*?</script>|<style.*?</style>", " ", ham, flags=re.S | re.I)
    duz = re.sub(r"<[^>]+>", "\n", duz)
    satir = [x.strip() for x in duz.split("\n") if x.strip()]
    metin = "\n".join(satir)
    m = re.search(r"Sayı:\s*\d{4}-\d+\n[^\n]+\n[^\n]+\n(.{60,1200}?)(?:Kamuoyunun bilgisine|İletişim)",
                  metin, re.S)
    return _temiz(m.group(1).replace("\n", " ")) if m else ""


def _sayfadan_ozet(url: str) -> str:
    """Haberin kendi sayfasından açıklama çıkar.

    Sıra: og:description → meta description → ilk anlamlı paragraf. Google News
    bağlantıları yayıncıya YÖNLENDİRME olduğu için requests'in yönlendirmeyi
    izlemesine güvenilir; yayıncı engellerse boş döner ve bülten başlıkla yetinir.
    """
    # Google News bağlantıları yayıncıya JS ile yönlendiriyor ve düz istekte yalnız
    # Google'ın kendi tanıtım metni geliyor; istek israfı, atla.
    if "news.google.com" in url:
        return ""
    ham = _getir(url, 12, dogrulama="resmigazete.gov.tr" not in url)
    if not ham:
        return ""
    if "tcmb.gov.tr" in url:
        t = _tcmb_duyuru_govdesi(ham)
        if t:
            return t
    for kalip in (r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']{40,600})',
                  r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']{40,600})',
                  r'<meta[^>]+content=["\']([^"\']{40,600})["\'][^>]+name=["\']description["\']'):
        m = re.search(kalip, ham, re.I | re.S)
        if m:
            t = _temiz(m.group(1))
            if len(t) > 40 and not KLISE.search(t):
                return t
    govde = re.sub(r"<(script|style|nav|header|footer)[^>]*>.*?</\1>", " ", ham, flags=re.S | re.I)
    for m in re.finditer(r"<p[^>]*>(.{80,900}?)</p>", govde, re.S):
        t = _temiz(m.group(1))
        if len(t) > 80 and not KLISE.search(t) and not re.search(r"abone|subscribe|giriş yap", t, re.I):
            return t
    return ""


def zenginlestir(haberler: list[Haber], azami: int = 16) -> int:
    """Özeti olmayan en önemli haberleri kaynağından tamamla.

    Neden gerekli: Google News akışları açıklama alanına başlığı tekrar yazıyor;
    bülten o zaman "ne olduğunu" değil yalnız "ne dendiğini" gösteriyordu. Sayfayı
    açıp ilk paragrafı almak, okura gerçek bir bilgi katıyor. Önbellekli: aynı
    bağlantı gün içinde bir kez çekilir.
    """
    onbellek = _onbellek_oku()
    n = 0
    for h in haberler:
        if h.ozet or not h.baglanti:
            continue
        if n >= azami:
            break
        if h.baglanti in onbellek:
            h.ozet = onbellek[h.baglanti]
            continue
        t = _sayfadan_ozet(h.baglanti)
        onbellek[h.baglanti] = t
        n += 1
        if t:
            h.ozet = _ozet_ise_yarar(h.baslik, t)
    _onbellek_yaz(onbellek)
    return n


def tara(pencere_saat: int = 30) -> tuple[list[Haber], list[str]]:
    """Dönüş: (haberler, okunamayan kaynak adları)."""
    simdi = datetime.now(timezone.utc)
    sinir = simdi - timedelta(hours=pencere_saat)
    haberler: list[Haber] = []
    dusen: list[str] = []
    gorulen: set[str] = set()

    rg, rg_ok = resmi_gazete()
    if rg_ok:
        for h in rg:
            anahtar = _sadelestir(h.baslik)[:90]
            if anahtar not in gorulen:
                gorulen.add(anahtar)
                haberler.append(h)
    else:
        dusen.append("Resmî Gazete")

    abd, abd_ok = abd_hazine_duyurulari(max(7, int(pencere_saat / 24) + 1))
    if abd_ok:
        for h in abd:
            anahtar = _sadelestir(h.baslik)[:90]
            if anahtar not in gorulen:
                gorulen.add(anahtar)
                haberler.append(h)
    else:
        dusen.append("ABD Hazinesi duyuruları")

    tcmb, okundu = tcmb_duyurulari()
    if okundu:
        for h in tcmb:
            anahtar = _sadelestir(h.baslik)[:90]
            if anahtar not in gorulen:
                gorulen.add(anahtar)
                haberler.append(h)
    else:
        dusen.append("TCMB Basın Duyuruları")

    for k in HABER_KAYNAKLARI:
        ham = _getir(k["url"], dogrulama=k.get("dogrulama", True))
        if not ham:
            dusen.append(k["ad"])
            continue
        kayitlar = _ayristir(ham)
        if not kayitlar:
            dusen.append(k["ad"])
            continue
        n = 0
        for baslik, baglanti, zaman, ozet in kayitlar:
            if not baslik:
                continue
            if zaman is not None and zaman < sinir:
                continue
            ozet = "" if k.get("ozet_yok") else _ozet_ise_yarar(baslik, ozet)
            if not k.get("yuksek_oncelik") and not _ilgili_mi(baslik, ozet):
                continue          # gürültü: alaka süzgecinden geçmedi
            anahtar = _sadelestir(baslik)[:90]
            if not anahtar or anahtar in gorulen:
                continue
            gorulen.add(anahtar)
            bolge, alan = _siniflandir(baslik, ozet, k.get("bolge", ""), k.get("alan", ""))
            haberler.append(Haber(html.unescape(baslik).strip(), baglanti, k["ad"],
                                  k.get("etiket", ""),
                                  zaman.isoformat() if zaman else "",
                                  bool(k.get("yuksek_oncelik")), ozet, bolge, alan))
            n += 1
            if n >= 40:
                break

    # Kurum duyuruları önce (hepsi), sonra haberler — her grup içinde en yeni üstte.
    # Sınır YALNIZ haberlere uygulanır: bir kurum duyurusunu kesmek, bültenin
    # varlık sebebini kesmek olurdu.
    kurumlar = sorted([h for h in haberler if h.kurum], key=lambda h: h.zaman or "", reverse=True)
    digerleri = _kumele(sorted([h for h in haberler if not h.kurum],
                               key=lambda h: h.zaman or "", reverse=True))
    return kurumlar + digerleri, dusen


if __name__ == "__main__":
    h, dusen = tara()
    bolumler, kilit = bolumle(h)
    print(f"KİLİT ({len(kilit)}):")
    for m in kilit:
        print(f"  {m['onem']:5.1f}  {m['baslik'][:88]}")
    for b in bolumler:
        print(f"\n### {b['baslik']} ({len(b['maddeler'])})")
        for m in b["maddeler"][:4]:
            print(f"  · {m['baslik'][:96]}")
            if m["ozet"]:
                print(f"      {m['ozet'][:150]}")
    print(f"{len(h)} haber · {len(dusen)} kaynak okunamadı {dusen if dusen else ''}")
    for x in h[:20]:
        im = "K" if x.kurum else " "
        print(f" {im} [{x.kaynak[:24]:24s}] {x.baslik[:96]}")
