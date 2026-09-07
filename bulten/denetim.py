#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bülten KALİTE DENETİMİ — yayından önce koşar, eksikse durdurur.

Neden var: bülteni her sabah bir ajan yazıyor ve kimse başında durmuyor. "Bugünkü
kadar ayrıntılı olacak mı, atladığımız bir şey olacak mı" sorusunun cevabı güven
değil ÖLÇÜM olmalı. Bu script bülteni açar, yazının ve verinin standardı tutup
tutmadığını madde madde ölçer ve tutmuyorsa çıkış kodu 1 verir.

  python3 bulten/denetim.py                 # bugünün bülteni
  python3 bulten/denetim.py 2026-08-23      # belirli gün
  python3 bulten/denetim.py --hepsi         # bütün arşiv
  python3 bulten/denetim.py --ayrinti       # geçen maddeleri de yaz

Denetim üç sınıf bulgu üretir:
  ENGEL   yayına gitmemeli (eksik bölüm, kısa yazı, atıfsız büyük hareket, kod dili)
  UYARI   düzeltilmeli ama yayını durdurmaz (özet oranı düşük, kaynak okunamamış)
  BİLGİ   sayısal döküm
"""
from __future__ import annotations

import argparse
import html as html_kacis
import json
import re
import sys
import unicodedata
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent
BULTEN = KOK / "site" / "src" / "data" / "bulten"

# ─────────────────────────── standart (görev metinlerindeki hedeflerle aynı)
HABER_BOLUM_ASGARI = 200      # kelime — her haber bölümü
YAZI_BOLUM_ASGARI = 300       # kelime — yazı-özel bölümler
YORUM_ASGARI = {"gunluk": 350, "haftalik": 600}
ZORUNLU_HABER_BOLUMU = ["tr_makro", "tr_piyasa", "global_makro", "global_politika",
                        "global_piyasa"]
ZORUNLU_YAZI_BOLUMU = ["faiz_fx_surucu", "emtia_surucu", "risk_firsat", "beklenti"]
ASGARI_ENSTRUMAN = 40
ASGARI_TL_FAIZ = 18
ASGARI_TUREV = 7
ASGARI_HABER = 25
ASGARI_OZET_ORANI = 0.35
ASGARI_KILIT = 3
ASGARI_KRITIK_TAKVIM = 3
BUYUK_HAREKET_ESIGI = 1.5     # % — bunu aşan hareket metinde ANILMALI
# Tazeleme takvimi ucunun yoklama bütçesi (sn) — `tazeleme_atlandi` için.
# CLAUDE.md'nin kaynak yoklama ölçüsüyle aynı: bir kaynağın açık olup
# olmadığı 8 saniyede anlaşılır; kapalıysa beklemenin bedeli bültenin
# geç yazılmasıdır.
TAKVIM_YOKLAMA_SN = 8

# Okura hiçbir şey söylemeyen geliştirici dili
# KOD DİLİ + YAPIM DİLİ — kalıplar burada DEĞİL, ortak/okur_dili.py'de.
# Aynı kural site sayfalarında ve tweetlerde de uygulanıyor; üç ayrı liste bir
# gün sessizce ayrışır ve hangisinin neyi gördüğü kimsenin aklında kalmazdı.
sys.path.insert(0, str(KOK / "ortak"))
import bicim  # noqa: E402
import okur_dili  # noqa: E402
# Yatırım tavsiyesi sayılabilecek kalıplar — TEK tanım ortak/tavsiye_dili.py'de
# (teknik yorum kapısı, analiz kapısı ve tweet kapısı aynı listeyi kullanır).
from tavsiye_dili import TAVSIYE  # noqa: E402


# Bültenin OKURA GÖRÜNEN yazı alanları. Liste elle tutuluyor ama tek yerde
# duruyor ve ölçütün kapsamı buradan okunuyor; yeni bir yazı alanı eklendiğinde
# buraya da eklenmezse dil denetimi onu göremez.
YAZI_ALANLARI = ("gundem", "yorum", "temalar", "notlar", "one_cikanlar",
                 "ozet", "sonuclar", "veri_gunlugu")


# Okurun GÖRMEDİĞİ makine alanları: hat/anahtar/kod adları burada durur ve
# doğaları gereği snake_case'tir. Bunları taramak, bültenin kendi iskeletini
# kod dili sanmak olurdu — ölçüt her koşuda düşerdi ve kimse ona bakmazdı.
MAKINE_ALANI = {"anahtar", "hat", "slug", "kod", "id", "src", "proje",
                "kaynak_kod", "seri", "tip", "grup", "seviye", "durum",
                "ikon", "renk", "sinif"}


def _metinler(b: dict) -> list:
    """Bültenin OKURA GÖRÜNEN yazı yapraklarını topla (makine alanları hariç)."""
    cikan: list[str] = []

    def gez(d, ad=None):
        if isinstance(d, str):
            if ad not in MAKINE_ALANI:
                cikan.append(d)
        elif isinstance(d, dict):
            for k, v in d.items():
                gez(v, k)
        elif isinstance(d, list):
            for v in d:
                gez(v, ad)

    for ad in YAZI_ALANLARI:
        gez(b.get(ad), ad)
    return cikan


def _duz(html: str) -> str:
    # Varlık kaçışları da çözülür: metin HTML olarak yazıldığı için "S&P 500"
    # kaynakta "S&amp;P 500" duruyor ve çözülmeden ad eşleşmesi tutmuyordu —
    # endeksin ADININ parçası olan 500, ölçülmemiş bir sayı gibi listeleniyordu.
    # Okur sayfada "S&P 500" görüyor; denetim de onu görmeli.
    duz = html_kacis.unescape(html or "")
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", duz)).strip()


def _kelime(html: str) -> int:
    return len(_duz(html).split())


def _sade(m: str) -> str:
    m = unicodedata.normalize("NFKD", (m or "").lower())
    return re.sub(r"[^a-z0-9ğüşiöç ]", " ", m)


# Kilit gelişme çapaları — İngilizce başlık, Türkçe metin.
#
# Bu ölçüt başlıktaki 5 harften uzun ilk altı kelimeyi Türkçe metinde arıyordu.
# İngilizce bir başlıkta ("Gold Rises As Treasury Buyback Support Plan Weighs
# On Dollar…") bu kelimeler Türkçe metinde ASLA bulunamaz: uyarı, konu doğru
# düzgün işlenmiş olsa bile kapanmıyordu. Kapanamayan bir uyarı, yazarı bütün
# uyarıları görmezden gelmeye alıştırır — denetimin kendisini işlevsizleştirir.
#
# Artık iki çapa aranıyor: (1) başlıktaki ÖZEL AD benzeri kelimeler — çeviride
# aynen kalanlar (Citadel, Druckenmiller, Bessent, Warsh, BOJ); (2) haberin
# kendi TÜRKÇE konu etiketi (`kaynak` alanı: "Arama — ABD borç yönetimi ve
# tahvil arzı"). İkisinden biri metinde geçiyorsa ölçüt geçer. Hiç çapa
# çıkmıyorsa uyarı da ÜRETİLMEZ; ölçemediğimiz şeyi ölçmüş gibi yapmayız.
CAPA_DISI = {
    "about", "after", "against", "ahead", "amid", "analysis", "another", "as",
    "banks", "before", "billion", "bond", "bonds", "boosts", "buyback",
    "calls", "central", "chief", "could", "data", "deal", "demand", "dollar",
    "down", "economy", "expected", "focus", "from", "global", "gold", "growth",
    "here", "hike", "high", "higher", "hold", "inflation", "interest",
    "into", "investors", "lead", "leads", "less", "level", "market", "markets",
    "may", "million", "more", "most", "new", "news", "next", "over", "plan",
    "policy", "prediction", "price", "prices", "push", "rate", "rates",
    "repression", "rises", "risk", "says", "sees", "shares", "should", "stock",
    "stocks", "support", "than", "that", "these", "this", "through", "time",
    "timely", "trade", "traders", "treasury", "under", "weighs", "what",
    "when", "will", "with", "would", "yields", "com", "reuters", "bloomberg",
    "cnbc", "investing", "advisory",
}


def _kilit_capalari(madde: dict) -> tuple[list[str], list[str]]:
    """(özel ad çapaları, Türkçe konu çapaları) — ikisi de boş olabilir."""
    baslik = madde.get("baslik") or ""
    # Google Haberler beslemesindeki başlıklar " - Yayıncı" ekiyle geliyor ve o
    # ek TEK çapa olarak kalabiliyor ("… inflation to 3.3% - Euronews.com").
    # Yayıncının adı haberin konusu değildir: okura yazılan bir metnin onu
    # anması beklenemez, yani uyarı konu düzgün işlense de kapanmaz. Yayıncı
    # eki atılır; geriye çapa kalmazsa ölçüt zaten uyarı üretmiyor.
    if "news.google.com" in (madde.get("baglanti") or "") and " - " in baslik:
        baslik = baslik.rsplit(" - ", 1)[0]
    ozel = [w for w in re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü.]{4,}", baslik)
            if w.lower().strip(".") not in CAPA_DISI and not w.islower()]
    kaynak = madde.get("kaynak") or ""
    konu = kaynak.split("—", 1)[1] if "—" in kaynak else ""
    konu = re.sub(r"\(\+?\d+\s*kaynak\)", " ", konu)
    tkonu = [w for w in _sade(konu).split() if len(w) > 4]
    return ozel, tkonu


# ─────────────────────────────────────────────── sayı denetimi yardımcıları
# Türkçe sayı: binlik nokta, ondalık virgül. Yıl ve tarih de bu kalıba uyar ama
# ölçülen değerden uzak düştükleri için karşılaştırmada kendiliğinden elenirler.
SAYI = re.compile(r"(?<![\w,.])([+\-−]?\d{1,3}(?:\.\d{3})*(?:,\d+)?)(?![\w])")

# Türkçe küçültme: 'I'.lower() Python'da 'i' verir, doğrusu 'ı'dır. Ayrıca
# 'İ'.lower() iki karaktere açılır ve dizin kayar — sayının hangi ismin yanında
# durduğunu KONUMDAN bulduğumuz için dizin korunmak zorunda. O yüzden birebir
# eşlemeli çeviri tablosu, sonra lower().
_KUCUK = str.maketrans("İIŞĞÜÖÇ", "iışğüöç")

# Yazan taraf yuvarlar: "TLREF %36,9" ile 36,94 aynı sayıdır. Tolerans yazılan
# sayının ONDALIK BASAMAĞINDAN türetilir; sabit bir eşik ya çok gevşek olur ya
# da meşru yuvarlamayı hata sayar.
# Sayı ile ölçülen büyüklüğün adı arasındaki azami uzaklık (karakter).
# Türkçede seviye çoğu kez ikinci sayıdır: "Brent %3,76 düşüşle 85,25 dolara".
# 14 karakterde bu seviye kapsam dışı kalıyordu. 26.08.2026 bülteni üzerinde
# ölçüldü: 14 → 52 sayı doğrulanıyor, 30 → 69, 55 → 78; şüpheli sayısı üçünde
# de 1'de sabit kalıyor (ölçülmeyen bir BIST alt endeksi). Yani pencereyi
# açmak gürültü üretmiyor, yalnız kapsamı büyütüyor. 30, hâlâ aynı cümle
# öbeği içinde kalan bir uzaklık olduğu için seçildi.
YAPISIK_UZAKLIK = 30

# Hareketin OLAĞANDIŞI sayılması için gereken standart sapma. 2,0σ, normal
# dağılımda kabaca yirmi günde bir görülen bir gün demektir — anlatılmayı hak
# eder. Sabit yüzde eşiğinin (BUYUK_HAREKET_ESIGI) yerine değil YANINA konur:
# ikisi farklı soruları yakalar.
OLAGANDISI_SIGMA = 2.0

# Veri iş akışı hafta içi günde dört kez koşar; hafta sonu koşmaz.
# 30 saat, pazar gecesi ile pazartesi sabahı arasını rahatça örter
# ama gerçek bir çöküşü ertesi bültende yakalar.
NABIZ_AZAMI_SAAT = 30

# Metin ölçümün GERİSİNDE kaldığında ne olur: ölçüm katmanı yazı yazıldıktan
# sonra yeniden kurulursa (26.08.2026 sabahı oldu — vade geçişi artefaktları
# 05:01'de temizlendi, yazı 04:31'de yazılmıştı) sayfadaki metin artık
# ölçmediğimiz sayıları anlatır. Tek tek bakınca her sapma "haberden gelmiş
# olabilir" görünür; ayırt eden şey ORANDIR.
#
# O sabahın iki hâli üzerinde ölçüldü:
#   yazı ölçümün gerisinde : 44 doğrulandı, 26 karşılıksız → %37
#   yazı ölçümle tutarlı   : 101 doğrulandı,  4 karşılıksız → %4
# Aradaki uçurum bir eşiği hak edecek kadar geniş. Oran eşiği tek başına
# yetmez: kısa bir metinde üç sayıdan biri karşılıksız çıkabilir, o yüzden
# asgari bir sayı da aranır.
# Bir anahtarın kendi veri tarihi, hattın ana saatinden kaç GÜN geride kalınca
# "karanlık" sayılır. 45 gün: aylık bir seri en kötü ~35 gün geride kalır, yani
# meşru hiçbir yayım ritmi bu eşiğe değmez. Eşiği aşan boşluk "bu seri artık
# beslenmiyor" demektir. (Hat başına ayarı ayar.KARANLIK_GUN geçersiz kılar.)
KARANLIK_GUN = 45


# "<yanlış sayı> yerine <doğru sayı>" — düzeltme kalıbı. Araya birkaç sözcük
# girebilir ("… yerine gerçek hareket …") ama cümle sınırı giremez.
GERI_ALMA = re.compile(r"^[^.;:!?]{0,40}?\byerine\b", re.I)


def _geri_alinan(ham: str, son: int, degerler) -> bool:
    """Bu sayı, yerine ÖLÇÜLEN bir değerin konduğu bir düzeltmenin parçası mı."""
    kuyruk = ham[son:son + 90]
    m = GERI_ALMA.match(kuyruk)
    if not m:
        return False
    for s2 in SAYI.finditer(kuyruk[m.end():]):
        coz = _sayi_coz(s2.group(1))
        if coz is None:
            continue
        y, basamak = coz
        tol = 0.5 * 10 ** (-basamak)
        return any(abs(abs(y) - abs(v)) <= tol for v in degerler)
    return False


def _tarihe(v) -> date | None:
    """ozet.json tarih yazımı → gün. Sözleşme TEK yerde: ortak/bicim.

    BURADA BİR ZAMANLAR İKİNCİ BİR AYRIŞTIRICI VARDI ve yalnız GG.AA.YYYY ile
    ISO tanıyordu. Aylık bir saat gün gibi yazılamayacağı için (01.07.2026 okura
    O GÜNÜN ölçümü gibi görünür) hatlar AA.YYYY yazıyor — ve RITIM'deki beş
    hattın ana saati tam o yazımdaydı (enflasyon · try-reer · marj · butce-borc ·
    reel-sektor-fx). `_tarihe` onları çözemeyince karanlık denetimi o beş hattı
    BÜTÜNÜYLE atlıyordu: ayrıştıramayan bir denetim hep "sorun yok" der.
    Site tarafı aynı yazımı lib/bicim ile çözüyordu; iki tarafın sözleşmesi
    ayrışmıştı. Aynı kusur `Deger.astro`da bir kez daha ölçülmüştü (CLAUDE.md).
    """
    return bicim.tarihe_cevir(v)

def _kutuk_saatleri() -> dict[str, tuple[str, set[str]]]:
    """slug → (ana saat alanı, ilan edilmiş ikincil saatler).

    Kütük (guncelle.HATLAR) tek kaynak: hangi alanın hattın ANA saati olduğu da,
    hangilerinin ayrı ritimde ikincil saat olduğu da orada ilan ediliyor
    (`Hat.tarih_anahtarlari`). Burada ikinci bir liste tutmak, ikisinin bir gün
    sessizce ayrışması demek — ayrıştığı gün de denetim geçmiş görünür.
    Kütük okunamazsa eski sözleşmeye düşülür (`_tarih` + sonek kuralı) ve
    denetim susmaz, yalnız daralır."""
    try:
        sys.path.insert(0, str(KOK))
        import guncelle                                        # noqa: E402
        cikti: dict[str, tuple[str, set[str]]] = {}
        for h in guncelle.HATLAR:
            anahtarlar = tuple(h.tarih_anahtarlari or ("_tarih",))
            ana = "_tarih" if "_tarih" in anahtarlar else anahtarlar[0]
            cikti[h.slug] = (ana, {a for a in anahtarlar if a != ana})
        return cikti
    except Exception:                                          # noqa: BLE001
        return {}


KARSILIKSIZ_ORAN = 0.20
KARSILIKSIZ_ASGARI = 8

# Sayının ardından bunlardan biri geliyorsa o sayı bir FİYAT değil, tarih ya da
# süredir: "24 Ağustos itibarıyla", "52 haftalık aralık", "13 haftalık
# yıllıklandırılmış". Ölçülen katmanda karşılığı olmaması normaldir.
TARIH_SURE = re.compile(
    r"^['\u2019]?\s*(ocak|şubat|mart|nisan|mayıs|haziran|temmuz|ağustos|eylül|ekim"
    r"|kasım|aralık|hafta|haftalık|ay|aylık|yıl|yıllık|gün|günlük|çeyrek|saat|dakika)"
    r"(?![0-9a-zğüşıöç])", re.I)


def _kucult(m: str) -> str:
    return (m or "").translate(_KUCUK).lower()


def _sayi_coz(m: str) -> tuple[float, int] | None:
    """Türkçe biçimli sayıyı (değer, ondalık basamak) olarak çöz."""
    t = m.replace("−", "-").replace("+", "").replace(".", "").replace(",", ".")
    try:
        d = float(t)
    except ValueError:
        return None
    basamak = len(m.split(",")[1]) if "," in m else 0
    return d, basamak


# Ölçülen büyüklüklerin metinde hangi sözcüklerle anıldığı. Hem atıf denetimi
# (hareket anılmış mı) hem sayı denetimi (anılan sayı doğru mu) buna bakar.
ANAHTAR_KELIME = {
            # "dolar/TL" en doğal Türkçe yazım ve eşleştiricide KARŞILIĞI YOKTU:
            # doğru yazılmış bir cümle ("dolar/TL haftalık %0,91 arttı") atıfsız
            # görünüyordu. MOVE ve "ABD 10Y" ile aynı kusur ailesi — kural yazımı
            # ile okur yazımının ayrışması. TL çaprazlarının üçü birden kapatıldı.
            "USD/TRY": ["usd try", "dolar kuru", "usdtry", "dolar tl"],
            "EUR/TRY": ["eur try", "eurotry", "euro tl", "euro kuru"],
            "GBP/TRY": ["gbp try", "gbptry", "sterlin tl"],
            "BIST 100": ["bist"], "BIST 30": ["bist"], "BIST Bankacılık": ["bist", "banka"],
            "S&P 500": ["s p 500", "sp 500", "abd hisse", "wall"],
            "Nasdaq 100": ["nasdaq"], "Dow Jones": ["dow"], "Russell 2000": ["russell"],
            "VIX": ["vix", "oynaklık", "oynaklığı"],
            # MOVE'un hiç karşılığı yoktu: eşleştirici tam adı ("MOVE (tahvil
            # oynaklığı)") arıyordu ve hiçbir doğal Türkçe cümle onu içermez.
            # VIX'in kardeşi olan bu satır, atıf zorunlu olduğu hâlde hangi
            # yazımla anılırsa anılsın atıfsız görünüyordu.
            "MOVE (tahvil oynaklığı)": ["move", "tahvil oynaklığı",
                                        "tahvil oynaklık"],
            "Brent": ["brent", "petrol"], "WTI": ["wti", "petrol"],
            "Altın (XAU, ons)": ["altın"], "Gümüş (XAG, ons)": ["gümüş"],
            "Platin": ["platin"], "Bakır": ["bakır"], "Bitcoin": ["bitcoin", "kripto"],
            "Dolar endeksi (DXY)": ["dolar endeksi", "dxy"],
            "Doğal gaz (Henry Hub)": ["doğal gaz"], "RBOB benzin": ["benzin"],
            "Kalorifer yakıtı": ["distilat", "kalorifer", "motorin"],
            "Nikkei 225": ["nikkei"], "Hang Seng": ["hang seng"], "DAX": ["dax"],
            "STOXX Europe 600": ["stoxx", "avrupa hisse"], "FTSE 100": ["ftse"],
            "CAC 40": ["cac"], "FTSE MIB": ["mib", "italya"],
            # FX haber endeksinin varlık adları (AD_TR) piyasa katmanınınkilerle
            # AYNI ŞEY ama farklı yazılıyor: "ABD 10Y" ile "ABD 10 yıllık". Eşleştirici
            # tam dizgi arayınca doğru yazılmış bir metin bile atıfsız görünüyordu —
            # kapanamayan uyarının tam kardeşi. Doğal Türkçe yazımlar da kabul edilir.
            "ABD 2Y": ["abd 2y", "iki yıllık", "2 yıllık"],
            "ABD 10Y": ["abd 10y", "on yıllık", "10 yıllık"],
            "EUR/USD": ["eur usd", "euro dolar"], "USD/JPY": ["usd jpy", "dolar yen"],
            "USD/CHF": ["usd chf", "frang"], "GBP/USD": ["gbp usd", "sterlin"],
            "AUD/USD": ["aud usd", "avustralya dolar"], "NZD/USD": ["nzd usd", "yeni zelanda"],
            "USD/CAD": ["usd cad", "kanada dolar"],
            "USD/NOK": ["usd nok", "norveç kron"], "USD/SEK": ["usd sek", "isveç kron"],
            "altın": ["altın"], "gümüş": ["gümüş"],
        }


def anilmi(ad: str, sade_metin: str) -> bool:
    """Bir büyüklüğün adı metinde geçiyor mu — TEK eşleştirici.

    İki ayrı ölçüt (piyasa atfı, haber tonu) aynı soruyu soruyor; iki ayrı
    eşleştirici iki ayrı doğru üretirdi.
    """
    # Anahtar kelimeler de metinle AYNI süzgeçten geçirilir. Geçirilmediğinde
    # süzgecin düşürdüğü harfi (ı, ç, ğ…) taşıyan her anahtar ölü doğuyordu:
    # "oynaklık", "isveç kron" ve "norveç kron" metin doğru yazılmış olsa bile
    # HİÇBİR ZAMAN eşleşmiyordu, çünkü metin tarafında "oynakl k" duruyordu.
    # Kusur tek anahtarda değil süzgeç uyuşmazlığındaydı; onarım da orada.
    for k in ANAHTAR_KELIME.get(ad, [ad]):
        if _sade(k) in sade_metin:
            return True
    parcalar = _sade(ad).split()
    return bool(parcalar) and parcalar[0] in sade_metin


class Denetim:
    def __init__(self, b: dict, ayrinti: bool = False):
        self.b = b
        self.ayrinti = ayrinti
        self.engel: list[str] = []
        self.uyari: list[str] = []
        self.bilgi: list[str] = []
        self.gecen: list[str] = []

    def _ok(self, m: str):
        self.gecen.append(m)

    # ────────────────────────────────────────────── bölümler ve uzunluk
    def yazi(self):
        b = self.b
        tur = b.get("tur", "gunluk")
        g = b.get("gundem") or {}
        if b.get("gundem_kaynagi") != "yazili":
            self.engel.append("Gündem yazısı YAZILMAMIŞ — sayfada yalnız otomatik taban "
                              "metin var (gundem_kaynagi 'yazili' değil).")
        for bid in ZORUNLU_HABER_BOLUMU:
            n = _kelime(g.get(bid, ""))
            if n == 0:
                self.engel.append(f"Gündem bölümü BOŞ: {bid}")
            elif n < HABER_BOLUM_ASGARI:
                self.engel.append(f"Gündem bölümü kısa: {bid} — {n} kelime "
                                  f"(asgari {HABER_BOLUM_ASGARI})")
            else:
                self._ok(f"{bid}: {n} kelime")
        for bid in ZORUNLU_YAZI_BOLUMU:
            n = _kelime(g.get(bid, ""))
            if n == 0:
                self.engel.append(f"Yazı bölümü BOŞ: {bid}")
            elif n < YAZI_BOLUM_ASGARI:
                self.engel.append(f"Yazı bölümü kısa: {bid} — {n} kelime "
                                  f"(asgari {YAZI_BOLUM_ASGARI})")
            else:
                self._ok(f"{bid}: {n} kelime")
        ny = _kelime(b.get("yorum") or "")
        hedef = YORUM_ASGARI.get(tur, 350)
        if ny == 0:
            self.engel.append("Okuma yazısı (yorum) YOK")
        elif ny < hedef:
            self.engel.append(f"Okuma yazısı kısa: {ny} kelime (asgari {hedef})")
        else:
            self._ok(f"okuma: {ny} kelime")
        oz = b.get("ozet") or {}
        if not oz.get("ne_oldu") or not oz.get("ne_bekleniyor"):
            self.uyari.append("Kural tabanlı özet ('ne oldu / ne bekleniyor') eksik")

    # ────────────────────────────────────────────── veri katmanları
    def veri(self):
        b = self.b
        p = b.get("piyasa") or {}
        n_enst = sum(len(g.get("satirlar", [])) for g in p.get("gruplar", []))
        if n_enst < ASGARI_ENSTRUMAN:
            self.engel.append(f"Piyasa fotoğrafı eksik: {n_enst} enstrüman "
                              f"(asgari {ASGARI_ENSTRUMAN})")
        else:
            self._ok(f"piyasa: {n_enst} enstrüman")
        if len(p.get("tr_faizleri", [])) < ASGARI_TL_FAIZ:
            self.engel.append(f"TL faiz seti eksik: {len(p.get('tr_faizleri', []))} satır "
                              f"(asgari {ASGARI_TL_FAIZ})")
        if len(p.get("turetilmis", [])) < ASGARI_TUREV:
            self.uyari.append(f"Türev büyüklük az: {len(p.get('turetilmis', []))} "
                              f"(asgari {ASGARI_TUREV})")
        if p.get("eksik"):
            self.uyari.append("Piyasa verisi gelmeyen: " + ", ".join(p["eksik"]))
        if p.get("hata"):
            self.engel.append(f"Piyasa katmanı düştü: {p['hata']}")

        kritik = b.get("kritik_takvim") or []
        if len(kritik) < ASGARI_KRITIK_TAKVIM:
            self.uyari.append(f"Kritik takvim zayıf: {len(kritik)} kayıt")
        else:
            self._ok(f"kritik takvim: {len(kritik)} kayıt")

        h = b.get("haberler") or {}
        maddeler = [m for bol in h.get("bolumler", []) for m in bol.get("maddeler", [])]
        if len(maddeler) < ASGARI_HABER:
            self.engel.append(f"Haber taraması zayıf: {len(maddeler)} madde "
                              f"(asgari {ASGARI_HABER})")
        else:
            self._ok(f"haber: {len(maddeler)} madde")
        ozetli = sum(1 for m in maddeler if m.get("ozet"))
        oran = ozetli / max(1, len(maddeler))
        if oran < ASGARI_OZET_ORANI:
            self.uyari.append(f"Haberlerin yalnız %{oran*100:.0f}'i özetli "
                              f"(hedef %{ASGARI_OZET_ORANI*100:.0f}) — kaynak sayfaları "
                              "okunamamış olabilir")
        kilit = next((bol for bol in h.get("bolumler", []) if bol.get("id") == "kilit"), None)
        n_kilit = len(kilit.get("maddeler", [])) if kilit else 0
        if n_kilit < ASGARI_KILIT:
            self.uyari.append(f"Kilit gelişme sayısı düşük: {n_kilit}")
        else:
            self._ok(f"kilit gelişme: {n_kilit}")
        if h.get("okunamayan"):
            self.uyari.append("Okunamayan kaynak: " + ", ".join(h["okunamayan"]))

    # ────────────────────────────────────────────── atıf: hareket ve kilit haber
    def _metin(self) -> str:
        g = self.b.get("gundem") or {}
        return _sade(" ".join([_duz(v) for v in g.values()]) + " " +
                     _duz(self.b.get("yorum") or ""))

    def atif(self):
        metin = self._metin()
        p = self.b.get("piyasa") or {}
        hareket = (p.get("en_cok_hareket") or {})
        def anilmis(ad: str) -> bool:
            return anilmi(ad, metin)

        for kip, etiket in (("gunluk", "günün"), ("haftalik", "haftanın")):
            for x in (hareket.get(kip) or [])[:3]:
                if x.get("deger") is None or abs(x["deger"]) < BUYUK_HAREKET_ESIGI:
                    continue
                if not anilmis(x["ad"]):
                    self.engel.append(
                        f"ATIFSIZ HAREKET — {etiket} en büyük hareketlerinden "
                        f"{x['ad']} (%{x['deger']}) metinde hiç anılmamış. "
                        "Sebebini yaz ya da 'sebebi anlaşılmıyor' de.")
                else:
                    self._ok(f"{x['ad']} (%{x['deger']}) anılmış")

        # Sabit yüzde eşiği tek başına yanlış yere baktırır: düşük oynaklıklı bir
        # seride %1,5 devasadır, yüksek oynaklıkta gürültüdür. σ eşiği hareketi
        # kendi normaline göre ölçer ve ham listede hiç görünmeyen ama gerçekten
        # olağandışı olanları yakalar (kredi endekslerinin +1,6σ günü gibi).
        for x in (hareket.get("sigma") or []):
            z = x.get("sigma")
            if z is None or abs(z) < OLAGANDISI_SIGMA:
                continue
            imza = f"{x['ad']} ({x['deger']}{x.get('birim', '')}, {z}σ)"
            if not anilmis(x["ad"]):
                self.uyari.append(
                    f"OLAĞANDIŞI HAREKET ANILMAMIŞ — {imza}. Yüzdesi küçük "
                    "olabilir ama bu enstrüman için olağandışı; sebebini yaz.")
            else:
                self._ok(f"{imza} anılmış")

        # kilit gelişmeler metinde geçiyor mu
        h = self.b.get("haberler") or {}
        kilit = next((b for b in h.get("bolumler", []) if b.get("id") == "kilit"), None)
        sade_metin = _sade(metin)
        for m in (kilit or {}).get("maddeler", [])[:4]:
            ozel, konu = _kilit_capalari(m)
            if not ozel and not konu:
                continue                       # ölçülemiyor — uyarı da üretilmez
            if any(_sade(w) .strip() and _sade(w).strip() in sade_metin for w in ozel) \
               or (konu and any(w in sade_metin for w in konu)):
                self._ok(f"kilit gelişme işlenmiş: {m['baslik'][:48]}")
                continue
            arananlar = ", ".join(ozel[:4] + konu[:4]) or "—"
            self.uyari.append(
                f"Kilit gelişme metinde işlenmemiş olabilir: {m['baslik'][:64]} "
                f"(aranan çapalar: {arananlar})")

    # ────────────────────────────────────────────── sayı tutarlılığı
    def _olculen_degerler(self) -> tuple[set[float], list[str]]:
        """(ölçülen bütün sayılar, metinde aranacak büyüklük adları).

        Değerler tek bir HAVUZ olarak toplanır, enstrüman enstrüman değil.
        Sebebi denendi ve görüldü: düzyazıda bir sayının hangi ada ait olduğu
        konumdan güvenilir çıkmıyor. "Nikkei %0,61, Hang Seng %0,68" cümlesinde
        her sayı iki ismin de yanındadır; üstelik faiz dünyasında değerler
        birbirine yapışıktır (TLREF 36,94 ile politika faizi 37,00 arası binde
        bir buçuk). Sayıyı sahibine bağlamaya çalışan ilk sürüm bu yüzden
        bültendeki DOĞRU cümleler için yirmi engel üretti.

        Doğru soru "bu sayı bu enstrümana mı ait" değil, "bu sayı ölçülen
        katmanda HİÇ var mı". Yoksa ezberden yazılmış demektir.
        """
        p = self.b.get("piyasa") or {}
        degerler: set[float] = set()
        adlar: set[str] = set()

        def ekle(ad, *ham):
            for v in ham:
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    degerler.add(float(v))
            sade = re.sub(r"\s*\(.*?\)", "", ad or "").strip()
            if len(sade) >= 3:
                adlar.add(_kucult(sade))
            for k in ANAHTAR_KELIME.get(ad, []):
                if len(k) >= 3:
                    adlar.add(_kucult(k))

        for g in self.b.get("gostergeler", []):
            ekle(g.get("ad"), g.get("deger"), g.get("fark"))
        for r in p.get("tr_faizleri", []):
            ekle(r.get("ad"), r.get("deger"))
        for t in p.get("turetilmis", []):
            ekle(t.get("ad"), t.get("deger"), t.get("d1"))
        for grup in p.get("gruplar", []):
            for r in grup.get("satirlar", []):
                ekle(r.get("ad"), *(r.get(a) for a in
                                    ("son", "d1", "h1", "a1", "ybb",
                                     "yil_yuksek", "yil_dusuk", "yil_konum",
                                     # σ da ölçülen bir sayıdır: metin "1,6
                                     # standart sapma" yazdığında denetim onu
                                     # ölçülen katmanda bulabilmeli.
                                     "d1_sigma", "sigma_gun")))
        # Rejim panosu satırları da ölçülmüş büyüklüktür: iki ölçülen sayının
        # farkı ölçüm olmaktan çıkmaz. Havuza girmezse yazan taraf panonun kendi
        # sayısını metne aldığında denetim onu "karşılığı yok" diye işaretlerdi.
        for r in self.b.get("rejim", []):
            v = r.get("deger")
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                degerler.add(float(v))
        for r in self.b.get("sonuclar", []):
            for a in ("gerceklesme", "onceki", "surpriz", "beklenti_sayi"):
                v = r.get(a)
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    degerler.add(float(v))
        # Grafiklerin çizdiği eğri noktaları da ölçülmüş sayıdır — metin kıyas
        # serisinden bir değer andığında ("21 Ağustos'ta iki yıllık %40,46'ydı")
        # denetim onu havuzda bulabilmeli.
        for seri in ((self.b.get("grafikler") or {}).get("egri") or {}).get("seriler", []):
            for v in seri.get("deger", []):
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    degerler.add(float(v))
        # Olay cümlelerindeki seviye, önceki değer ve fark da ölçülmüş sayıdır.
        for alan in ("one_cikanlar", "notlar", "veri_gunlugu"):
            for o in self.b.get(alan, []):
                for a in ("deger", "onceki", "fark"):
                    v = o.get(a)
                    if isinstance(v, (int, float)) and not isinstance(v, bool):
                        degerler.add(float(v))
        return degerler, sorted(adlar, key=len, reverse=True)

    def sayi(self):
        """Metinde ölçülen bir adın YANINDA duran sayı, ölçülen katmanda var mı.

        YAZIM.md'nin en sert kuralı "sayıları uydurma"ydı ama ölçülmüyordu:
        dil, tekrar, atıf, tazelik, tema ve söz defteri denetleniyor, sayının
        kendisi denetlenmiyordu. Ezberden yazılmış tek bir seviye, bültenin
        bütün ölçüm disiplinini götürür.

        Denetim bilerek UYARI seviyesinde ve DAR kapsamlı. Dar: yalnız ölçülen
        bir büyüklüğün adına YAPIŞIK sayılara bakar — araya cümle sonu ya da
        noktalı virgül girerse bağ kopmuş sayılır. Uyarı: haberden gelen meşru
        sayılar (bir eşik, bir tarife tutarı, bir anket rakamı) ölçülen katmanda
        yoktur ve bunları engele çevirmek denetimi okunmaz kılar. Yazan taraf
        listeye bakıp kaynağını doğrular; kural, iyi niyet yerine bir liste
        üretmiş olur.
        """
        if self.b.get("gundem_kaynagi") != "yazili":
            return                      # kural tabanlı taban zaten ölçülenden türüyor
        g = self.b.get("gundem") or {}
        ham = _duz(" ".join([_duz(v) for v in g.values()]) + " " +
                   _duz(self.b.get("yorum") or ""))
        kucuk = _kucult(ham)
        degerler, adlar = self._olculen_degerler()
        if not degerler or not adlar:
            return

        # Adların metindeki konumları — sözcük sınırıyla. Sınır şart: "altın"
        # anahtarı "enflasyonun ALTINda" içinde de geçiyor ve o bir altın fiyatı
        # değil.
        ad_konum: list[tuple[int, int]] = []
        for a in adlar:
            for m in re.finditer(r"(?<![0-9a-zğüşıöç])" + re.escape(a) +
                                 r"(?![0-9a-zğüşıöç])", kucuk):
                ad_konum.append((m.start(), m.end()))
        if not ad_konum:
            return

        dogru, supheli = 0, []
        for m in SAYI.finditer(ham):
            coz = _sayi_coz(m.group(1))
            if coz is None:
                continue
            x, basamak = coz
            if any(a_bas <= m.start() and m.end() <= a_son for a_bas, a_son in ad_konum):
                continue            # sayı adın kendisi: "Nikkei 225", "STOXX Europe 600"
            if TARIH_SURE.match(ham[m.end():m.end() + 14]):
                continue            # tarih ya da süre
            if not self._yapisik(m.start(), m.end(), ad_konum, ham):
                continue
            tol = 0.5 * 10 ** (-basamak)
            # İşaret düzyazıda RAKAMDA değil sözcükte durur: "%3,76 düşüşle"
            # ölçülen −3,76 ile aynı sayıdır. Mutlak değerle kıyaslanır.
            if any(abs(abs(x) - abs(v)) <= tol for v in degerler):
                dogru += 1
            elif _geri_alinan(ham, m.end(), degerler):
                # Sayı GERİ ALINMAK için yazılmış: "yayımlanan −%11,36 yerine
                # gerçek hareket −%1,74". Yanlış olduğu zaten söylenen bir
                # sayıyı "kaynağını doğrula" diye bildirmek denetimi kendi
                # düzeltmesine karşı çalıştırmak olurdu. Şart sıkı: hemen
                # ardından "yerine" gelmeli VE onu izleyen sayı ölçülen
                # katmanda bulunmalı — yani düzeltmenin doğrusu ölçülmüş olmalı.
                dogru += 1
            else:
                supheli.append((m.group(1), ham[max(0, m.start() - 55): m.end() + 40]))

        if dogru:
            self._ok(f"sayı denetimi: {dogru} sayı ölçülen katmanla doğrulandı")
        if not supheli:
            return
        ornek = " · ".join(f"{s} (…{b.strip()}…)" for s, b in supheli[:4])
        kuyruk = "…" if len(supheli) > 4 else ""
        oran = len(supheli) / max(len(supheli) + dogru, 1)
        if len(supheli) >= KARSILIKSIZ_ASGARI and oran >= KARSILIKSIZ_ORAN:
            # Tek tük sapma haberden gelir; metnin beşte biri ölçümle tutmuyorsa
            # anlatılan artık bu bültenin verisi değildir.
            self.engel.append(
                f"METİN ÖLÇÜMLE TUTMUYOR — ölçülen bir büyüklüğün yanında geçen "
                f"{len(supheli)} sayının ({oran:.0%}) ölçülen katmanda karşılığı yok. "
                "Bu dağılım tek tek hatayı değil, metnin ölçüm katmanının GERİSİNDE "
                "kaldığını gösterir: ölçüm yazıdan sonra yeniden kurulmuş olabilir. "
                f"Bülteni güncel ölçüme göre yeniden yaz. Örnekler: {ornek}{kuyruk}")
        else:
            self.uyari.append(
                f"Ölçülen katmanda karşılığı olmayan {len(supheli)} sayı ölçülen bir "
                f"büyüklüğün yanında geçiyor — kaynağını doğrula ya da ölçülen değeri "
                f"yaz: {ornek}{kuyruk}")

    @staticmethod
    def _yapisik(bas: int, son: int, ad_konum: list[tuple[int, int]], ham: str) -> bool:
        """Sayı, ölçülen bir adın hemen yanında mı — araya cümle sınırı girmeden.

        Nokta, noktalı virgül, iki nokta ve uzun tire bağı koparır: "aylık
        %16,44. Platin %1,36" cümlesinde 16,44 platine ait değildir. Virgül
        ayıraç sayılmaz, çünkü Türkçe sayının kendi içinde geçer.
        """
        for a_bas, a_son in ad_konum:
            if a_son <= bas:
                arasi = ham[a_son:bas]
            elif son <= a_bas:
                arasi = ham[son:a_bas]
            else:
                continue                    # sayı adın içinde (ör. "BIST 100")
            if len(arasi) > YAPISIK_UZAKLIK:
                continue
            if re.search(r"[.;:—]", re.sub(r"\d\.\d", "  ", arasi)):
                continue
            return True
        return False

    # ────────────────────────────────────────────── dil ve üslup
    def dil(self):
        # KAPSAM DENETİMİN PARÇASIDIR. Bu ölçüt yalnız gündem ve yoruma
        # bakıyordu; bültenin OKURA GÖRÜNEN metni bundan ibaret değil —
        # temalar, notlar, öne çıkanlar, söz defteri ve takvimin beklenti
        # alanları da sayfada basılıyor. Kod dili oralara sızdığında ölçüt
        # yeşil kalıyordu.
        tam = " ".join(_duz(x) for x in _metinler(self.b))
        bulgu = okur_dili.tara(tam)
        if bulgu:
            aile, esl, _ = bulgu[0]
            self.engel.append(
                f"Okura değil kendimize yazan dil ({aile}): '{esl}' — "
                f"toplam {len(bulgu)} yer. Dosya/alan adları ve kendi sürüm "
                f"tarihçemiz bültende geçmez.")
        else:
            self._ok("okur dili temiz (kod dili + yapım dili)")
        t = TAVSIYE.search(tam)
        if t:
            self.engel.append(f"Yatırım tavsiyesi kalıbı: '{t.group(0)}'")
        else:
            self._ok("tavsiye dili yok")

    # ────────────────────────────────────────────── tazelik
    def tazelik(self):
        try:
            import ayar, gozlem                       # noqa: E402
        except Exception:
            return
        # Hattın ana saati ve içindeki farklı ritimli alanlar AYRI denetlenir;
        # yalnız ana saate bakmak, günlük bileşeni ilerleyen bir hattın haftalık
        # bileşeni donduğunda denetimi kör bırakır.
        saatler = [(hat, gozlem.son_gorulme(hat), azami, "")
                   for hat, azami in ayar.RITIM.items()]
        saatler += [(hat, gozlem.alan_son_gorulme(hat, alan), azami, ad)
                    for (hat, alan), (azami, ad) in ayar.RITIM_ALAN.items()]
        gecikmis = []
        for hat, sg, azami, ad in saatler:
            if not sg:
                continue
            try:
                t = datetime.fromisoformat(sg[1].replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                continue
            gun = (datetime.now() - t).days
            if gun > azami:
                gecikmis.append(f"{hat}{f' — {ad}' if ad else ''} ({gun}g)")
        if gecikmis:
            self.uyari.append("Veri gecikmiş hatlar: " + ", ".join(gecikmis))

    # ────────────────────────────────────── bugün tazelenemeyen hatlar
    def tazeleme_atlandi(self):
        """Bugün tazelenmesi GEREKEN ama tazelenemeyen hatlar — UYARI, engel değil.

        Mevcut `tazelik` ölçütü bu soruyu SORAMIYOR: eşikleri hattın yayım
        ritmi (4–45 gün), yani "bugünkü koşu hiç gelmedi" hâli o eşiğe varana
        kadar görünmez. 04.09.2026'da veri koşusu 50 dakika yandı ve TEK BİR
        hat bile tazelenmeden iptal edildi; denetim o sabah yalnız
        "hazine-ihrac (16g)" diyebildi — on altı hattın hiçbirinin
        tazelenmediğini söyleyemedi.

        Ölçü iki mevcut kaynağın karşılaştırmasıdır, yeni eşik yoktur:
        resmî yayım takvimi bugün hangi hattın koşması gerektiğini,
        `tazeleme_durumu.json` de son başarılı tazelemeyi söyler.

        ENGEL DEĞİL, bilinçli: kaynak gerçekten yayımlamadığında ya da bir hat
        birkaç gün düştüğünde bu ölçüt her sabah yayını durdururdu. Ve bilinçli
        bir atlama ile sessiz bir arıza AYNI GÖRÜNMEMELİ — sebep satırın içine
        yazılır.

        HASSASİYET KAPISI: takvim ucu okunamadığında (kör koşu) bütün hatlar
        "gerekli" görünür; ölçüt o hâlde hat hat on altı satır patlatmaz, tek
        satıra iner. "Kapsam kadar hassasiyet de denetimin parçasıdır" — on
        altı satırlık bir uyarıya kimse bakmaz.
        """
        # Yalnız BUGÜNÜN bülteni için anlamlı: takvim kararları şu ana ait,
        # arşiv koşusunda (--hepsi) eski bir bülteni bugünün kararlarıyla
        # ölçmek uydurma olurdu.
        bugun = date.today().isoformat()
        if str(self.b.get("tarih", "")) != bugun:
            return
        try:
            sys.path.insert(0, str(BURASI))
            import ayar, tazeleme                              # noqa: E402
            # KISA TAVAN. Bu ölçüt yazı katmanının kritik yolunda koşuyor;
            # takvim ucu düştüğünde bültenin yazılmasını dakikalarca
            # geciktirmek, düzeltilmeye çalışılan arızanın ta kendisi olurdu.
            # 8 saniye deponun kendi kaynak yoklama bütçesi.
            with tazeleme.zaman_asimi(TAKVIM_YOKLAMA_SN):
                kararlar = tazeleme.kararlar()
        except Exception:                                      # noqa: BLE001
            return                                             # ölçemiyorsak susarız
        if not kararlar:
            return

        kor = [k for k in kararlar if str(k.sebep).startswith(tazeleme.KOR_KOSU)]
        if kor:
            self.uyari.append(
                f"Veri yayım takvimi okunamadı: {len(kor)} hattın tamamı kör koşu "
                "listesinde — hangi hattın bugün tazelenmesi gerektiği ölçülemiyor.")
            return

        # KAYNAK YAYIMLADI, VERİ GELMEDİ — bu satır `kossun` süzgecinin
        # ÖNÜNDE durmak zorunda. Hakkı dolan hat `kossun=False` döner, yani
        # aşağıdaki süzgeç TAM DA ARIZA HÂLİNİ atıyordu: ölçü 07.09.2026'da
        # kondu ve tüketicisi sıfırdı. "Yeni yayım yok" satırıyla "yayım oldu
        # ama veri gelmedi" satırı birbirine BİREBİR benzer; ayıran şey
        # `deneme` sayacıdır.
        try:
            import bayatlik                                    # noqa: E402
            al = bayatlik.alarmlar()
        except Exception:                                      # noqa: BLE001
            al = []
        if al:
            self.uyari.append(
                f"Kaynak yayımladı ama veri gelmedi ({len(al)} hat): "
                + " · ".join(f"{b.ad} — son görülen sürüm {b.surum}, "
                             f"{b.deneme} koşudur ilerlemiyor" for b in al[:4])
                + ("…" if len(al) > 4 else "")
                + ". Yeniden deneme hakkı doldu; bu hatların sayfaları o "
                  "sürümde donmuş demektir.")

        gerekli = [k for k in kararlar if k.kossun]
        if not gerekli:
            self._ok("bugün tazelenmesi gereken hat yok")
            return

        # Bütçeyle bilinçli atlanan hatlar (sabah bütçesi henüz YOK; alan
        # doldurulduğunda sebep kendiliğinden ayrışsın diye okunuyor).
        atlanan: set[str] = set()
        try:
            import nabiz                                       # noqa: E402
            d = nabiz.oku(nabiz.yol(BURASI))
            son = (d.get("kosular") or [])[-1] if isinstance(d.get("kosular"), list) else {}
            atlanan = {str(x) for x in (son.get("atlanan_butce") or [])}
        except Exception:                                      # noqa: BLE001
            pass

        durum = tazeleme.durum_oku()
        # Hattın kısa adı → okurun gördüğü ad. Kütük tek kaynak (guncelle.py);
        # okunamazsa kısa ad basılır, ölçüt susmaz.
        ad_slug: dict[str, str] = {}
        try:
            sys.path.insert(0, str(KOK))
            import guncelle                                    # noqa: E402
            ad_slug = {h.ad: h.slug for h in guncelle.HATLAR}
        except Exception:                                      # noqa: BLE001
            pass

        # SEBEBE GÖRE GRUPLA. On üç hattın on üçüne aynı gerekçeyi ayrı ayrı
        # yazmak, bakılmayan bir uyarı üretir; sebep bir kez, hatlar adıyla.
        eksik: dict[str, list[str]] = {}
        for k in gerekli:
            son_tazeleme = str(durum.get(k.hat, ""))
            if son_tazeleme[:10] == bugun:
                continue
            okur_adi = ayar.HAT_ADI.get(ad_slug.get(k.hat, ""), k.hat)
            sebep = ("bütçe ile atlandı" if k.hat in atlanan
                     else "koşu düştü ya da kaynak yayımlamadı")
            eksik.setdefault(sebep, []).append(okur_adi)
        if eksik:
            self.uyari.append(
                "Bugün tazelenmesi gereken ama tazelenemeyen hatlar — "
                + "; ".join(f"{sebep}: {', '.join(adlar)}"
                            for sebep, adlar in eksik.items())
                + ". Bu hatların sayıları dünkü sürümde; kullanılacaksa kendi "
                  "tarihiyle anılmalı.")
        else:
            self._ok(f"gereken {len(gerekli)} hattın hepsi bugün tazelendi")

    def yerlesmemis(self):
        """Kapanmamış seansın barı bültende olmamalı — ENGEL.

        27.08.2026'nın ilk sürümü bunu yaptı: 04:21 UTC'de koştu ve 51
        enstrümanın 21'i o anda HENÜZ AÇIK olan günün barını taşıyordu. O barın
        önceki kapanışa göre farkı "günlük değişim" diye yayımlandı; altında
        işaret ters döndü (gerçek seans −%0,86 iken bülten +%1,78 yazdı) ve
        günün bütün anlatısı o sahte harekete kuruldu.

        Ölçüm katmanında koruma var (piyasa._yerlesmemis_dus) ama tek katmanlı
        bir sigorta yeterli değil: o koruma bir zamanlar YALNIZ beş enerji
        vadelisini kapsıyordu ve kimse fark etmedi. Bu ölçüt yayının SON
        kapısında aynı soruyu bağımsız olarak bir daha sorar. Eşik tablosu
        ölçüm katmanından okunur — iki yerde iki ayrı doğru olmasın.
        """
        try:
            sys.path.insert(0, str(BURASI))
            import piyasa                              # noqa: E402
        except Exception:
            return
        simdi = datetime.now(timezone.utc)
        bugun = simdi.date().isoformat()
        acik = []
        for g in (self.b.get("piyasa", {}).get("gruplar") or []):
            esik = piyasa.KAPANIS_UTC.get(g.get("id", ""), piyasa.VARSAYILAN_KAPANIS)
            if simdi.hour >= esik:
                continue
            for s in (g.get("satirlar") or []):
                if s.get("tarih") == bugun:
                    acik.append(f"{s.get('ad')} ({g.get('id')}, kapanış {esik}:00 UTC)")
        if acik:
            self.engel.append(
                "KAPANMAMIŞ SEANSIN BARI bültende: " + ", ".join(acik[:8])
                + (f" … +{len(acik) - 8}" if len(acik) > 8 else "")
                + ". Bu satırların 'günlük değişim'i dünkü seansı değil geceliği "
                "ölçer ve işareti ters çevirebilir. Ölçümü piyasa kapandıktan "
                "sonra yeniden kurun.")
        else:
            self._ok("kapanmamış seansın barı yok")

    def piyasa_seansi(self):
        """Anlık görüntü HANGİ seansa ait — ve bülten bunu söylüyor mu?

        31.08.2026 pazartesi bülteninde elli piyasa satırının ELLİSİ 28.08
        Cuma kapanışını taşıyordu ve "günlük değişim" diye yayımlandı. Bu
        BAYAT VERİ DEĞİL: pazartesi sabahı son kapanmış seans gerçekten
        Cuma'dır, başka bir sayı yoktur. Kusur ölçümde değil ETİKETTE —
        pazartesi okuyan biri hareketi bugüne ait sanır.

        Ölçütün iki eşiği var ve ikisi farklı şeyi söyler:
        · Beklenen son seans (bülten gününden önceki en yakın hafta içi günü)
          ile anlık görüntünün tarihi AYNIYSA gecikme normaldir; yalnız
          etiketin varlığı denetlenir.
        · Bir gün daha eskiyse UYARI (resmî tatil buna girer).
        · İki gün ve fazlasıysa ENGEL: artık gerçekten bayat veri yayımlanıyor.

        NOT — σ ölçeklemesi BU KUSURUN ÇÖZÜMÜ DEĞİL. Hafta sonu boşluğunun
        oynaklığı şişirdiği sezgisi ölçüldü ve YANLIŞ çıktı: 49 enstrümanda üç
        günlük boşluk σ'sının bir günlüğe oranı medyan 1,00 (bkz. piyasa.py).
        Kapanıştan kapanışa hareket, arada kaç takvim günü olursa olsun tek
        seanslık risktir. Düzeltilecek şey ölçü değil, okurun gördüğü etikettir.
        """
        p = self.b.get("piyasa") or {}
        kt = p.get("kapanis_tarih")
        if not kt:
            self.uyari.append("Piyasa anlık görüntüsünün seans tarihi YOK "
                              "(piyasa.kapanis_tarih) — okur hareketin hangi güne "
                              "ait olduğunu göremez.")
            return
        try:
            bulten_g = datetime.fromisoformat(str(self.b.get("tarih"))[:10]).date()
            kapanis_g = datetime.fromisoformat(str(kt)[:10]).date()
        except Exception:
            return
        beklenen = bulten_g - timedelta(days=1)
        while beklenen.weekday() >= 5:                 # hafta sonunu atla
            beklenen -= timedelta(days=1)
        # Fark TAKVİM günüyle değil KAÇIRILAN SEANS sayısıyla ölçülür. Salı
        # bülteninde Cuma kapanışı üç takvim günü geridedir ama kaçırılan tek
        # bir seans vardır (pazartesi); takvimle ölçmek tek tatili bile engel
        # sayardı.
        fark, g = 0, kapanis_g + timedelta(days=1)
        while g <= beklenen:
            if g.weekday() < 5:
                fark += 1
            g += timedelta(days=1)
        etiket = p.get("kapanis_seansi")
        takvim_gun = (bulten_g - kapanis_g).days
        if fark >= 2:
            self.engel.append(
                f"BAYAT PİYASA ANLIK GÖRÜNTÜSÜ: kapanış {kt}, beklenen son seans "
                f"{beklenen.isoformat()}, {fark} seans kaçırılmış. Bülten bugünkü "
                f"tarihle çıkarken piyasa satırları o kadar eski olamaz.")
            return
        if fark == 1:
            self.uyari.append(
                f"Piyasa anlık görüntüsü beklenen son seanstan bir seans eski "
                f"(kapanış {kt}, beklenen {beklenen.isoformat()}) — resmî tatil "
                f"değilse ölçüm yenilenmeli.")
            return
        if not etiket:
            self.uyari.append("Piyasa anlık görüntüsünde seans ETİKETİ yok "
                              "(piyasa.kapanis_seansi).")
        elif takvim_gun >= 2:
            self._ok(f"piyasa seansı etiketli: {etiket} ({takvim_gun} takvim günü "
                     f"geride — hafta sonu/tatil, tek seans)")
        else:
            self._ok(f"piyasa seansı etiketli: {etiket}")

    def devir(self):
        """Devir düzeltmesi kurulamamış vadeli seri var mı.

        Kurulamadığında seri HAM kontrat kapanışıyla bırakılır (uydurma
        düzeltme, düzeltmemekten kötüdür). Ama o hâlde SEVİYE bir önceki
        yayımla kıyaslanabilir değildir ve seviyeden türeyen rafineri marjları
        da öyle. Yazan taraf bunu bilmeden marj yorumu kurarsa, düzeltmenin
        varlığını/yokluğunu piyasa hareketi diye anlatır.
        """
        ham = [s.get("ad") for g in (self.b.get("piyasa", {}).get("gruplar") or [])
               for s in (g.get("satirlar") or []) if s.get("roll_bilinmiyor")]
        if ham:
            self.uyari.append(
                "Vadeli devir düzeltmesi kurulamadı: " + ", ".join(ham)
                + ". Bu satırlarda SEVİYE ham kontrat kapanışıdır — önceki yayımla "
                "kıyaslamayın, seviyeden türeyen marjlar üzerinden yorum kurmayın. "
                "Günlük yüzde değişimler etkilenmez.")
        else:
            self._ok("vadeli devir düzeltmesi kurulu")

    def haber_tonu(self):
        """Haber endeksindeki olağandışı hareketler METİNDE anılmış mı — ENGEL.

        Ölçüm katmanı günün en olağandışı üç hareketini sıralıyor (eşikle
        değil sıralamayla: sabit eşik burada her gün on sahte olay üretirdi).
        Sıralanmış bir hareket metinde hiç geçmiyorsa bülten onu ölçmüş ama
        SÖYLEMEMİŞ olur — piyasa tarafındaki atıf disiplininin aynısı.

        Sebep de yazılmalı; onu bir ölçüt dayatamaz, ama YAZIM.md dayatır ve
        "sebebi netleşmedi" demek geçerli bir cevaptır. Burada ölçülen, hareketin
        okura hiç görünmemesi.
        """
        try:
            sys.path.insert(0, str(BURASI))
            import gozlem                              # noqa: E402
        except Exception:
            return
        d = gozlem.anlik("fx-haber-endeksi")
        if not d:
            return
        hareketler = d.get("hareket") or []
        if not hareketler:
            self._ok("haber tonu: sıralanacak hareket yok")
            return
        metin = _sade(self._metin())
        anilmayan = [m for m in hareketler if not anilmi(m.get("ad", ""), metin)]
        if anilmayan:
            self.engel.append(
                "HABER TONU ANILMAMIŞ — " + ", ".join(
                    f"{m['ad']} ({m['onceki']:+.2f} → {m['deger']:+.2f})" for m in anilmayan)
                + ". Haber endeksinin günün en olağandışı hareketleri bunlar; "
                "metinde anıl ve sebebini yaz. Sebep netleşmiyorsa "
                "'sebebi netleşmedi' de — ama sessiz geçme.")
        else:
            self._ok(f"haber tonu: {len(hareketler)} olağandışı hareket anılmış")

    # Revizyon kıyasına giren seriler: (ad, satır listesi, anahtar üretici,
    # değer alanı, tolerans, birim alanı). Anahtar MUTLAKA satırın kendi
    # tarihini içerir: kıyas ancak AYNI güne ait sayı için anlamlıdır. Türev
    # büyüklüklerin günü bacaklarının bar günleridir, rejim satırının günü
    # girdilerinin günleri (bileşik anahtar; günler ayrışırsa o gün kıyas
    # yapılmaz — uydurma yok). Tarih alanı olmayan eski bültenler süzgeçte düşer.
    REVIZYON_SERILERI = (
        ("piyasa", lambda b: [s for g in (b.get("piyasa", {}).get("gruplar") or []) for s in (g.get("satirlar") or [])],
         lambda s: (s.get("kod"), s.get("tarih")), "d1", 0.005, "degisim_birim"),
        ("TL faiz", lambda b: b.get("piyasa", {}).get("tr_faizleri") or [],
         lambda s: (s.get("ad"), s.get("tarih")), "deger", 0.005, "birim"),
        ("gösterge", lambda b: b.get("gostergeler") or [],
         lambda s: (s.get("hat"), s.get("anahtar"), s.get("veri_tarihi")), "deger", None, "birim"),
        ("türev", lambda b: b.get("piyasa", {}).get("turetilmis") or [],
         lambda s: (s.get("ad"), s.get("tarih") or None), "deger", None, "birim"),
        ("türev Δ", lambda b: b.get("piyasa", {}).get("turetilmis") or [],
         lambda s: (s.get("ad"), s.get("tarih") or None), "d1", 0.05, "degisim_birim"),
        ("rejim", lambda b: b.get("rejim") or [],
         lambda s: (s.get("ad"), s.get("tarih") or None), "deger", None, "birim"),
    )

    def revizyon(self):
        """Daha önce YAYIMLADIĞIMIZ bir sayı sonradan değişti mi.

        Bir serinin aynı güne ait değeri iki farklı bültende iki farklı
        sayıyla çıkıyorsa, ikisinden biri yanlış yayımlanmıştır. 27.08'de tam
        bu oldu ve yazan taraf bunu ENERJİDE fark edip düzeltti, ama aynı
        kusurun metallerde de olduğunu görmedi — çünkü fark etmesi gözüne
        çarpmasına bağlıydı, ölçülmüyordu. Artık ölçülüyor ve yalnız piyasa
        satırlarında değil: TL faiz seti ve gösterge şeridi de kıyasa girer
        (REVIZYON_SERILERI). Değişen her sayı adıyla listelenir; yazan taraf
        ya kaynağını doğrular ya da "yayımlanan X yerine gerçek değer Y"
        kalıbıyla geri alır.
        """
        try:
            dosyalar = sorted(BULTEN.glob("*.json"))
        except Exception:
            return
        bugunku = self.b.get("tarih")
        oncekiler = [d for d in dosyalar if d.stem < str(bugunku)][-3:]
        if not oncekiler:
            return
        eskiler = []
        for d in reversed(oncekiler):
            try:
                eskiler.append((d.stem, json.loads(d.read_text(encoding="utf-8"))))
            except Exception:
                continue
        degisen = []
        eslesme: dict[str, tuple[int, int]] = {}      # seri → (kıyaslanan çift, bugünkü satır)
        for seri_ad, satirlar, anahtar_f, alan, tol, birim_alani in self.REVIZYON_SERILERI:
            simdi = {}
            for s in satirlar(self.b):
                k = anahtar_f(s)
                if None in k or s.get(alan) is None:
                    continue
                t = tol if tol is not None else 0.5 * 10 ** (-int(s.get("ondalik", 2)))
                simdi[k] = (s.get("ad"), s[alan], s.get(birim_alani) or s.get("birim", ""), t)
            cift = 0
            for stem, eski_b in eskiler:
                for s in satirlar(eski_b):
                    k = anahtar_f(s)
                    if k not in simdi or s.get(alan) is None:
                        continue
                    cift += 1
                    ad, yeni, birim, t = simdi[k]
                    if abs(float(s[alan]) - float(yeni)) <= t:
                        continue
                    if any(x[0] == seri_ad and x[1] == ad for x in degisen):
                        continue
                    degisen.append((seri_ad, ad, s[alan], yeni, birim, stem))
            eslesme[seri_ad] = (cift, len(simdi))
        if degisen:
            satir = ", ".join(f"{sa} · {ad}: {e}{b} → {y}{b} ({g} bülteninde yayımlandı)"
                              for sa, ad, e, y, b, g in degisen[:6])
            self.uyari.append(
                f"YAYIMLANAN SAYI DEĞİŞTİ ({len(degisen)}) — {satir}"
                + (" …" if len(degisen) > 6 else "")
                + ". Her birinin sebebini bul; ölçü düzeltmesiyse metinde "
                "'yayımlanan X yerine gerçek değer Y' kalıbıyla geri al.")
        else:
            # Kapsam denetimin parçasıdır: hangi seride kaç çift kıyaslandı yazılır —
            # türev/rejim satırları tarih taşımayan eski bültenlerle hiç eşleşmez ve
            # bu "temiz" değil "kıyaslanmadı" demektir.
            kapsam = " · ".join(f"{ad} {c}/{n}" for ad, (c, n) in eslesme.items())
            self._ok(f"daha önce yayımlanan sayı değişmemiş — kıyaslanan çift/bugünkü satır: {kapsam}")

    # Okur metninde sayı yazımı: eksi U+2212, ondalık virgül (ortak/bicim ile
    # aynı sözleşme). ASCII tire ve nokta ondalık bir hattın kendi f-string'inden
    # sızar; kapı burada UYARI verir — yeni bir hat eklendiğinde sızıntı adıyla
    # görünsün, yayını durdurmasın (sayı doğru, yazımı kusurlu).
    ASCII_EKSI = re.compile(r"(?:(?<=\s)|(?<=\()|^)-(?=\d)")
    NOKTA_ONDALIK = re.compile(r"(?<![\d.])\d{1,3}\.\d{1,3}(?![\d.])")

    def bicim(self):
        metin = "\n".join(_duz(str(m)) for m in _metinler(self.b))
        eksi = self.ASCII_EKSI.findall(metin)
        # Tarih (31.08) ve sürüm/kod (1.2.3) nokta taşır; yalnız okur cümlesindeki
        # "%7.3" / "-1.247 → -696" kalıbı hedeflenir: önünde % veya işaret olan.
        nokta = re.findall(r"[%+\-−]\d{1,3}\.\d{1,3}(?![\d.])", metin)
        if eksi:
            ornek = re.findall(r"\S*(?:(?<=\s)|(?<=\())-\d\S*", metin)[:3]
            self.uyari.append(f"{len(eksi)} yerde ASCII eksi (−) yerine tire: "
                              + ", ".join(repr(o) for o in ornek))
        if nokta:
            self.uyari.append(f"{len(nokta)} yerde ondalık noktası (virgül olmalı): "
                              + ", ".join(repr(o) for o in nokta[:3]))
        # YÜZDE ÖNDE. Sözleşme (ortak/bicim.yuzde) "%12,8" yazar; "12,8 %"
        # yazımı 07.09.2026'da derlenmiş sayfada 40 yerde ölçüldü ve kaynağı
        # olay cümlesi üreticisiydi (birimi sayının arkasına ekliyordu).
        # Üretici düzeltildi; bu ölçüt yazı katmanından gelecek sızıntıyı da
        # görsün diye kondu — kural bir kez koda yazılınca öbür kapıdan girer.
        # SATIR SONU DEĞİL, BOŞLUK. `\s` satır sonunu da eşliyor ve alanlar
        # "\n" ile birleştirildiği için "…2026-08-31" + "%37,00" çifti yanlış
        # pozitif veriyordu (ölçüldü: 20 bulgunun 20'si). Kusurun gerçek
        # biçimi "12,8 %" — aynı satırda, boşlukla.
        ters = re.findall(r"\d[ \t]+%(?!\d)", metin)
        if ters:
            ornek = re.findall(r"[^\s]+[ \t]+%(?!\d)", metin)[:3]
            self.uyari.append(
                f"{len(ters)} yerde yüzde sayının ARKASINDA (sözleşme: önde, '%12,8'): "
                + ", ".join(repr(o) for o in ornek))
        if not eksi and not nokta and not ters:
            self._ok("sayı yazımı: eksi U+2212, ondalık virgül, yüzde önde")

    def duzeltme(self):
        """Düzeltme kaydı biçimce tam mı; ve 'yayımlanan sayı değişti' uyarısı
        varsa yazan taraf hesabını vermiş mi.

        Yayımlanmış bir sayının düzeltilmesi metinde "yayımlanan X yerine
        gerçek değer Y" kalıbıyla yapılır; aynı düzeltme bültenin `duzeltmeler`
        listesine de yapısal olarak yazılır ki sayfa onu "Düzeltmeler"
        bölümünde bassın ve site bütün düzeltmeleri tek listede toplayabilsin.
        Yarım kayıt (neyin neye düzeltildiğini yazmayan) ENGEL: okura hesap
        vermeyen bir düzeltme, düzeltme değildir.
        """
        liste = self.b.get("duzeltmeler")
        if liste is not None and not isinstance(liste, list):
            self.engel.append("duzeltmeler listesi bozuk (liste değil)")
            liste = []
        liste = liste or []
        bozuk = 0
        for i, d in enumerate(liste, 1):
            eksik = [k for k in ("alan", "eski", "yeni") if not str((d or {}).get(k, "")).strip()]
            if eksik:
                bozuk += 1
                self.engel.append(f"Düzeltme kaydı {i} eksik: {', '.join(eksik)} yok")
        if liste and not bozuk:
            self._ok(f"{len(liste)} düzeltme kaydı biçimce tam")
        elif not liste:
            self._ok("düzeltme kaydı yok (sayı değişmediyse doğal)")
        # Metinde geri alma kalıbı var ama yapısal kayıt yoksa: okur sayfada
        # düzeltmeyi görür, düzeltmeler listesi görmez — UYARI.
        # Ham metinde aranır: _sade() Türkçe 'ı'yı düşürür ("yay mlanan") ve kalıbı kaçırır.
        g = self.b.get("gundem") or {}
        ham = " ".join(_duz(v) for v in g.values()) + " " + _duz(self.b.get("yorum") or "")
        if not liste and re.search(r"yayımlanan\s+[^.]{1,80}?\s+yerine", ham, re.I):
            self.uyari.append("Metinde 'yayımlanan … yerine' geri alma kalıbı var ama "
                              "duzeltmeler kaydı boş — düzeltme kaydını da yaz "
                              "(bulten/yaz.py, alan: duzeltmeler).")

    def karanlik(self):
        """Hattın saati ilerlerken İÇİNDEKİ bir serinin donması.

        `tazelik` ve `gecikme_olaylari` aynı şeyi ölçer: "bu SÜRÜME geçileli kaç
        gün oldu". İkisi de anlık görüntü tarihçesine dayanır ve bu yüzden bir
        şeyi hiç göremez — dosyaya GİRDİĞİ ANDA zaten eski olan değeri. Tarihçe
        yeni başlamışsa (yeni hat, yeni anahtar) sürüm dünkü kadar tazedir;
        oysa taşıdığı veri iki buçuk aylıktır.

        Somut hâli: TÜFEX hattının 3 yıllık başabaş serisi 12.06.2026'da durdu
        (kaynak DİBS eğrisinde o vadede fiyatlanan TÜFEX kıymeti kalmadı), ama
        ozet.json'un ana saati her gün ilerliyor. Sayfadaki tabloda satır
        "25.08.2026" başlığının altında duruyordu. Hiçbir katman itiraz etmedi.

        Burada ölçülen tarihçe değil, DOSYANIN KENDİ İÇ TUTARLILIĞI: her
        `<anahtar>_tarih` alanı, hattın `_tarih`inden ne kadar geride?
        Tarihçe gerektirmediği için ilk koşuda da konuşur.
        """
        try:
            import ayar, gozlem                       # noqa: E402
        except Exception:                                      # noqa: BLE001
            return
        esikler = getattr(ayar, "KARANLIK_GUN", {})
        bilinen_sebep = getattr(ayar, "KARANLIK_BILINEN", {})
        karanlik: list[str] = []
        bilinen: list[str] = []
        cozulemeyen: list[str] = []
        bakilan = 0
        # ALAN KÜMESİ SONEKTEN DEĞİL İLANDAN. Sonek kuralı ("_tarih ile biten")
        # kütüğün İLAN ETTİĞİ 21 ikincil saatin 7'sini görmüyordu — `_tarih2`,
        # `_tarih3`, `faiz_gun` ve `hafta_kisa` o kalıba uymuyor ("_tarih2"
        # `_tarih` ile bitmez. İlan ASILDIR; sonek yalnız ilanı olmayan alanlar
        # için devam eder, çünkü bir hat ozet'ine ilan etmediği yeni bir saat
        # yazabilir ve o da denetlenmelidir.
        ilan = _kutuk_saatleri()
        for hat in ayar.RITIM:
            d = gozlem.anlik(hat)
            if not isinstance(d, dict):
                continue
            ana_alan, ikincil = ilan.get(hat, ("_tarih", set()))
            hat_t = _tarihe(d.get(ana_alan))
            if hat_t is None:
                # Hattın ANA saati çözülemiyorsa hat bütünüyle atlanır — ama
                # sessizce değil: ayrıştıramayan bir denetim hep "sorun yok" der.
                if d.get(ana_alan) is not None:
                    cozulemeyen.append(f"{hat}/{ana_alan} ({d.get(ana_alan)!r} — ana saat)")
                continue
            esik = int(esikler.get(hat, KARANLIK_GUN))
            tarihsel = getattr(ayar, "TARIHSEL_ISARET", None)
            for alan in sorted(set(d) | ikincil):
                if alan == ana_alan:
                    continue
                if alan not in ikincil and not (alan.endswith("_tarih")
                                                and alan != "_tarih"):
                    continue
                v = d.get(alan)
                # "Bu uç nokta ne zaman yaşandı" diyen alanlar tazelik saati
                # DEĞİL: `kum_zirve_tarih` 2026 Şubat'ında donmuş olmalı, o
                # zirvenin tarihi öyle. Ayrım adlandırmadan okunuyor
                # (bkz. ayar.TARIHSEL_ISARET).
                if tarihsel is not None and tarihsel.search(alan[:-6]):
                    continue
                kendi = _tarihe(v)
                if kendi is None:
                    # İLAN EDİLMİŞ bir saat çözülemiyorsa bu bir kusurdur ve
                    # adıyla görünür; ilan edilmemiş bir alanın çözülememesi
                    # (metin bir alan sonekle yakalanmış olabilir) sessiz kalır.
                    if alan in ikincil and v is not None:
                        cozulemeyen.append(f"{hat}/{alan} ({v!r})")
                    continue
                bakilan += 1
                gun = (hat_t - kendi).days
                if gun <= esik:
                    continue
                stem = alan[:-6]
                sebep = bilinen_sebep.get((hat, stem))
                if sebep:
                    bilinen.append(f"{hat}/{stem} ({gun}g — {sebep})")
                else:
                    karanlik.append(f"{hat}/{stem} ({v} — {gun}g geride)")
        # Sebebi yazılmış karanlık seri uyarı değildir; her gün tekrarlanan
        # uyarı yanındaki YENİ uyarıyı da görünmez kılar. Ama sessizce de
        # geçilmez: geçen ölçüt olarak sebebiyle yazılır.
        for b in sorted(bilinen):
            self._ok(f"karanlık ama açıklanmış: {b}")
        if karanlik:
            self.uyari.append(
                f"Hattın saati ilerlerken donmuş {len(karanlik)} seri: "
                + " · ".join(sorted(karanlik)[:6])
                + ("…" if len(karanlik) > 6 else "")
                + ". Bu sayılar sayfada hattın güncel tarihiyle aynı başlığın "
                  "altında duruyor; metinde anılacaklarsa kendi tarihleriyle "
                  "anılmalı.")
        elif bakilan:
            self._ok(f"açıklanmamış karanlık seri yok ({bakilan} anahtar saati denetlendi)")
        if cozulemeyen:
            # Çözülemeyen bir saat, DENETLENMEYEN bir saattir. Muafiyetle
            # kapatılmaz; hat yazımını ortak/bicim sözleşmesine çeker.
            self.uyari.append(
                f"Tarih yazımı çözülemeyen {len(cozulemeyen)} ilan edilmiş saat: "
                + " · ".join(sorted(cozulemeyen)[:6])
                + ("…" if len(cozulemeyen) > 6 else "")
                + ". Bu alanlar bayatlık denetiminin DIŞINDA kalıyor; yazım "
                  "ortak/bicim sözleşmesine çekilmeli (GG.AA.YYYY · AA.YYYY · ISO).")

    def olu_kalip(self):
        """Tetik tarifi takvimde HİÇBİR yayımla eşleşmiyor mu — UYARI.

        `tazeleme.olu_kaliplar()` bu ölçüyü 27.08'den beri üretiyordu ve depoda
        BEŞ çağrı yeri vardı — hiçbiri kapı değildi: `__main__`, duman sınaması
        (dönüşe assert yok) ve `veri.yml`in `continue-on-error: true` taşıyan
        tanı adımı. Yani ölü bir kalıp yalnız kimsenin okumadığı bir log
        satırına düşüyordu.

        Bir kalıp öldüğünde hat emniyet ağına DÜŞMÜYOR, tam tersine HER
        PENCEREDE koşuyor (`kararlar()` `kossun=True` veriyor): maliyeti hafta
        içi altı pencere × en pahalı hat 869 sn ≈ 87 dk/gün. Yani sessiz kalan
        şey hem bir kaynak değişikliği hem bir koşucu faturası.

        ENGEL DEĞİL UYARI: takvim ucu düştüğünde `olu_kaliplar()` zaten boş
        liste döndürüyor, yani yanlış alarm riski yapısal olarak yok — ama bir
        kaynak adı değişikliğinin yayını durdurması da doğru olmazdı.
        """
        try:
            sys.path.insert(0, str(BURASI))
            import tazeleme                                    # noqa: E402
            with tazeleme.zaman_asimi(TAKVIM_YOKLAMA_SN):
                olu = tazeleme.olu_kaliplar()
        except Exception:                                      # noqa: BLE001
            return                                             # ölçemiyorsak susarız
        if not olu:
            self._ok("bütün tetik tarifleri takvimde karşılık buluyor")
            return
        ad_slug: dict[str, str] = {}
        try:
            sys.path.insert(0, str(KOK))
            import guncelle                                    # noqa: E402
            ad_slug = {h.ad: h.slug for h in guncelle.HATLAR}
        except Exception:                                      # noqa: BLE001
            pass
        import ayar                                            # noqa: E402
        satir = " · ".join(
            f"{ayar.HAT_ADI.get(ad_slug.get(hat, ''), hat)} ({kalip[:40]})"
            for hat, kalip in olu[:5])
        self.uyari.append(
            f"Tetik tarifi takvimde karşılık bulmayan {len(olu)} hat: {satir}"
            + ("…" if len(olu) > 5 else "")
            + ". Kaynak seri adını değiştirmiş olabilir; bu hatlar her veri "
              "penceresinde koşuyor ve tazeleme takvimi onlar için işlemiyor.")

    def nabiz(self):
        """Veri iş akışı gerçekten koştu mu — ölçüm katmanının canlılığı.

        `tazelik` denetimi hatların VERİ tarihine bakar ve ancak RITIM eşiği
        (4-45 gün) aşılınca konuşur; bir iş akışı çöküşü o eşiğe varana kadar
        görünmez. 26.08'de veri hattı düştü, dört hattın verisi hazırken
        hiçbiri çekilmedi ve aşağı akıştaki hiçbir katman bunu bilemedi —
        bülten bayat ölçüm üzerine yazılacaktı.

        Nabız bu boşluğu kapatır: iş akışı her koşuda, başarılı olsun olmasın,
        damgasını atar. Burada ölçülen o damganın YAŞI ve son koşunun sonucu.
        """
        y = BURASI / "kosu_nabzi.json"
        if not y.exists():
            self.uyari.append("Veri koşusu nabzı yok (bulten/kosu_nabzi.json) — "
                              "veri iş akışının koşup koşmadığı bilinmiyor.")
            return
        try:
            d = json.loads(y.read_text(encoding="utf-8"))
            t = datetime.fromisoformat(str(d.get("veri_kosusu", "")).replace("Z", "+00:00"))
        except Exception:                                      # noqa: BLE001
            self.uyari.append("Veri koşusu nabzı okunamadı")
            return
        saat = (datetime.now(t.tzinfo) - t).total_seconds() / 3600
        sonuc = str(d.get("sonuc", "bilinmiyor"))
        if saat > NABIZ_AZAMI_SAAT:
            self.uyari.append(
                f"Veri iş akışı {saat:.0f} saattir koşmadı (son: {t:%d.%m %H:%M} UTC, "
                f"sonuç '{sonuc}'). Ölçüm katmanı bayat olabilir — yazmadan önce "
                "hatların veri tarihlerini gözden geçir.")
        elif sonuc not in ("success", "bilinmiyor"):
            self.uyari.append(
                f"Son veri koşusunun tazeleme adımı '{sonuc}' ile bitti "
                f"({t:%d.%m %H:%M} UTC). Bazı hatlar çekilememiş olabilir.")
        else:
            self._ok(f"veri koşusu nabzı taze ({saat:.0f} saat önce, '{sonuc}')")

    def tekrar(self):
        """Aynı olgu bültenin birden çok yerinde yeniden ANLATILIYOR mu.

        Bülten uzadıkça aynı hikâye bölümden bölüme kopyalanıyor ve okur dördüncü
        kez aynı cümleyi okuyor. Ölçü: farklı bölümlerde birebir geçen 7 kelimelik
        öbekler, bin kelimeye normalize edilmiş. Özet bölümlerinin (kilit, yorum)
        diğerlerine değmesi tanımı gereği meşru; ağır ihlal ÖZET OLMAYAN iki
        bölümün birbirini tekrar etmesidir — sayılan budur.
        """
        import tekrar as _t
        r = _t.olc(self.b)
        y = r["yogunluk"]
        ornek = "; ".join(f"[{'+'.join(yer)}] …{s}…"
                          for s, yer in r["agir"][:3])
        if y > _t.YOGUNLUK_ENGEL:
            self.engel.append(
                f"TEKRAR fazla: bin kelimede {y} ağır tekrar (üst sınır "
                f"{_t.YOGUNLUK_ENGEL}) — {len(r['agir'])} öbek aynen yineleniyor. "
                f"Bir olguyu bir kez tam anlat; ikinci geçişte ya yeni bir işlem "
                f"yap ya tek cümleyle an. Örnek: {ornek}")
        elif y > _t.YOGUNLUK_UYARI:
            self.uyari.append(
                f"Tekrar yüksek: bin kelimede {y} ağır tekrar "
                f"(hedef ≤{_t.YOGUNLUK_UYARI}). Örnek: {ornek}")
        else:
            self._ok(f"tekrar düşük: bin kelimede {y} ağır tekrar")
        if len(r["sayi"]) >= _t.SAYI_ADET_ESIK:
            en = ", ".join(f"{s} ({len(yer)} bölüm)" for s, yer in r["sayi"][:5])
            self.uyari.append(
                f"{len(r['sayi'])} sayı {_t.SAYI_BOLUM_ESIK}+ bölümde tekrarlanıyor — "
                f"her tekrarda üzerine yeni bir işlem yapılmıyorsa kes: {en}")

        # GÜNLER ARASI TEKRAR. Yukarıdaki ölçü bir sayının KENDİ içine bakar;
        # okurun asıl şikâyeti "her gün aynı şeyleri söylemeyelim"di ve o
        # eksen hiç ölçülmüyordu. Ölçüm ENGEL DEĞİL UYARI: sakin bir haftada
        # iki sayının benzemesi meşrudur, vadesi gelen bir söz yeniden anılır.
        onceki = self._onceki_yazi()
        if onceki is None:
            self._ok("günler arası tekrar: önceki sayı yok, kıyas koşmadı")
        else:
            g = _t.gunler_arasi(_t.bolumler(self.b), onceki)
            if g["uyari"]:
                agir = ", ".join(f"{a} %{g['bolum'][a]:.0f}" for a in g["agir"][:3])
                self.uyari.append(
                    f"Günler arası tekrar %{g['oran']:.1f} (hedef <%{_t.GUNLER_ARASI_UYARI:.0f}): "
                    f"bu sayının düzyazısının bu kadarı önceki sayıda AYNEN var."
                    + (f" Sürükleyen bölüm: {agir}." if agir else "")
                    + " Bir sayı önceki sayıyı özetlemez; değişeni anlat.")
            else:
                self._ok(f"günler arası tekrar düşük: %{g['oran']:.1f}")

    def _onceki_yazi(self):
        """Bir önceki sayının yazı bölümleri — günler arası kıyasın noktası.

        Bulunamazsa None: ölçülemeyen bir oranı sıfır saymak, tekrarı yok
        saymak olurdu.
        """
        import tekrar as _t
        try:
            dosyalar = sorted(BULTEN.glob("*.json"))
        except Exception:                                      # noqa: BLE001
            return None
        onceki = [d for d in dosyalar if d.stem < str(self.b.get("tarih"))]
        if not onceki:
            return None
        try:
            import json as _j
            b = _j.loads(onceki[-1].read_text(encoding="utf-8"))
        except Exception:                                      # noqa: BLE001
            return None
        bl = _t.bolumler(b or {})
        return bl or None

    def tema(self):
        """Tema defteri bakımı yapılmış mı, yazıda temaya atıf var mı.

        Defter bültenin hafızası: güncellenmezse bülten her gün sıfırdan başlar ve
        haftalarca süren anlatıları göremez.
        """
        t = self.b.get("temalar") or {}
        temalar = t.get("temalar") or []
        if not temalar:
            self.uyari.append("Tema defteri boş ya da okunamadı")
            return
        bugun = self.b.get("tarih")
        canli = [x for x in temalar if x.get("durum") in ("aktif", "izlemede")]
        # Tema ölçüleri piyasa katmanından beslenir. Piyasa düşüp de fotoğraf
        # eskisinden geri yüklendiğinde ölçüler boş kalıyordu: sayfada dolu bir
        # piyasa tablosunun hemen altında sayısız bir tema bölümü çıkıyor, üstelik
        # şablon boş ölçüyü sessizce gizlediği için kimse fark etmiyordu.
        olcusuz = [x["ad"] for x in canli
                   if x.get("varliklar") and not x.get("olculer")]
        if olcusuz:
            self.engel.append("Tema ölçüleri boş (izlenen varlıkları var ama sayı yok): "
                              + ", ".join(olcusuz))
        bayat_olcu = [x["ad"] for x in canli if x.get("olcu_bayat")]
        if bayat_olcu:
            self.uyari.append("Tema ölçüleri önceki fotoğraftan geri yüklendi: "
                              + ", ".join(bayat_olcu))
        bayat = [x["ad"] for x in canli if str(x.get("son_guncelleme", "")) < str(bugun)]
        if bayat:
            self.uyari.append("Tema defteri bugün güncellenmemiş: " + ", ".join(bayat))
        else:
            self._ok(f"tema defteri güncel ({len(temalar)} tema)")
        self._tema_goruntusu_taze(temalar)
        # Her canlı temanın BU koşudaki gelişmesi yazılmalı: tema bölümü bültenin en
        # çok okunan yerlerinden biri ve boş bir "gelişme" alanı okura hiçbir şey vermez.
        yazisiz = [x["ad"] for x in canli if len(_duz(x.get("gelisme", "")).split()) < 15]
        if yazisiz:
            self.engel.append("Tema gelişmesi yazılmamış (her canlı tema için bu koşuda "
                              "ne değiştiği 2-4 cümleyle yazılmalı): " + ", ".join(yazisiz))
        else:
            self._ok(f"tema gelişmeleri yazılı ({len(canli)} canlı tema)")
        metin = self._metin()
        anilan = [x["ad"] for x in temalar
                  if any(w in metin for w in _sade(x["ad"]).split() if len(w) > 4)]
        if not anilan:
            self.engel.append("Yazıda hiçbir temaya atıf yok — gündem olayları listeliyor "
                              "ama piyasayı anlatmıyor olabilir. En az bir temanın adını "
                              "kullanıp tezinin güçlenip güçlenmediğini söyle.")
        else:
            self._ok(f"temaya atıf: {', '.join(anilan[:3])}")

    def _tema_goruntusu_taze(self, temalar: list) -> None:
        """Sayfada duran tema metni DEFTERDEKİYLE aynı mı — ENGEL.

        Tema bölümü bültene ÖLÇÜM anında işlenir; yazı katmanı defteri ondan
        sonra günceller. Yani defteri düzeltmek sayfayı düzeltmez: ölçüm yeniden
        kurulana kadar okur eski metni görür. Bu iki kez ısırdı ve ikisi de
        yayına çıktı — 28.08.2026'da sayfa bir gün önce GERİ ALINMIŞ rakamları
        yeniden bastı; 30.08.2026'da haftaya bakış bülteni "çürütücü ölçüt bugün
        sınanacak — Warsh'ın Jackson Hole konuşması" diyordu, oysa konuşma iki
        gün önce yapılmıştı. İkisinde de defter doğruydu, sayfa eskiydi ve
        aradaki farkı kimse ölçmüyordu.

        Ölçüt basit: bültene işlenmiş görüntü ile defterin şu anki hâli
        karşılaştırılır. Ayrışıyorlarsa yapılacak şey bellidir — ölçümü yeniden
        kur, sonra yaz.
        """
        try:
            defter = json.loads((BURASI / "temalar.json").read_text(encoding="utf-8"))
        except Exception:
            self.uyari.append("Tema defteri okunamadı — sayfadaki görüntünün "
                              "tazeliği doğrulanamıyor")
            return
        canli_defter = {x.get("ad"): x for x in (defter.get("temalar") or [])}
        gomulu = {x.get("ad"): x for x in temalar}
        ayrisan = []
        for ad, d in canli_defter.items():
            g = gomulu.get(ad)
            if g is None:
                ayrisan.append(f"{ad} (sayfada hiç yok)")
                continue
            for alan in ("gelisme", "son_gozlem", "durum", "izlenecek_gosterge"):
                if str(d.get(alan, "")) != str(g.get(alan, "")):
                    ayrisan.append(f"{ad} ({alan})")
                    break
        if ayrisan:
            self.engel.append(
                "TEMA GÖRÜNTÜSÜ ESKİ — sayfaya işlenmiş tema metni defterdekinden "
                "farklı: " + ", ".join(ayrisan[:4]) + ". Defteri düzeltmek sayfayı "
                "düzeltmez; ölçümü yeniden kur, sonra yaz.")
        else:
            self._ok("tema görüntüsü defterle aynı")

    def olagandisilik_penceresi(self):
        """Olağandışılık sıralaması bültenin kıyas penceresini izliyor mu — ENGEL.

        Haftaya bakış bülteninin kıyas penceresi HAFTADIR. 30.08.2026'ya kadar
        haftalık bülten de günlük σ listesini basıyordu ve sayfada "Günün
        olağandışı hareketleri" başlığı duruyordu: haftalık bir bültende günün
        hareketini sıralamak, okuru haftanın hikâyesinden uzaklaştırır. Dahası
        haftalık hareketi günlük σ'ya bölmek ölçek hatasıdır — haftalık değişim
        doğası gereği günlüğün ~√5 katıdır ve sıradan bir hafta bile 2σ'yı aşar.
        """
        p = self.b.get("piyasa") or {}
        h = p.get("en_cok_hareket") or {}
        if not (h.get("sigma") or []):
            return
        kip = h.get("sigma_kip")
        gerekli = "haftalik" if self.b.get("haftalik") else "gunluk"
        if kip is None:
            self.engel.append(
                "OLAĞANDIŞILIK PENCERESİ BİLDİRİLMEMİŞ — ölçüm katmanı σ listesini "
                "hangi pencerede kurduğunu söylemiyor; sayfa başlığı ve sütun adları "
                "buna bakıyor. Ölçümü güncel kodla yeniden kur.")
        elif kip != gerekli:
            self.engel.append(
                f"OLAĞANDIŞILIK PENCERESİ YANLIŞ — bülten '{gerekli}' kipinde ama σ "
                f"listesi '{kip}' penceresinde kurulmuş. Haftaya bakışta haftalık "
                "hareket haftalık σ'ya bölünür; karıştırmak ölçek hatasıdır.")
        else:
            self._ok(f"olağandışılık penceresi bültenin kipini izliyor ({kip})")

    def izleme(self):
        """Süreklilik: bültenin verdiği sözler takip ediliyor mu.

        `bulten/izleme.json` önceki bültenlerin "şunu izleyeceğiz" dediği konuların
        defteri. Vadesi gelmiş açık bir kayıt metinde hiç anılmamışsa bülten dizi
        olmaktan çıkar, her gün sıfırdan başlar. Kasıtlı olarak UYARI seviyesinde:
        yazarı kısıtlamak için değil, unutmasın diye.
        """
        y = BURASI / "izleme.json"
        if not y.exists():
            return
        try:
            defter = json.loads(y.read_text(encoding="utf-8"))
        except Exception:
            self.uyari.append("İzleme defteri (izleme.json) okunamadı")
            return
        self._karne(defter)
        bugun = str(self.b.get("tarih") or "")
        acik = [k for k in defter.get("kayitlar", []) if k.get("durum") == "acik"]
        vadeli = [k for k in acik if str(k.get("vade", "9999")) <= bugun]
        if not vadeli:
            if acik:
                self._ok(f"izleme defteri: {len(acik)} açık kayıt, vadesi gelen yok")
            return
        metin = self._metin()
        sessiz = []
        for k in vadeli:
            kelimeler = [w for w in _sade(k.get("konu", "")).split() if len(w) > 4]
            if not any(w in metin for w in kelimeler):
                sessiz.append(k["konu"])
        if sessiz:
            self.uyari.append("Vadesi gelen izleme kaydı metinde anılmamış (önceki "
                              "bülten söz vermişti — hesabını ver ya da kaydı kapat): "
                              + " · ".join(sessiz))
        else:
            self._ok(f"izleme defteri: vadesi gelen {len(vadeli)} kayıt metinde işlenmiş")

    def _karne(self, defter: dict):
        """Kapanan sözler NOTLANDI mı — karnenin var olma şartı.

        Defter okura açıldığı andan itibaren "kaç söz tuttu" sorusu meşrudur.
        Cevabı ancak kaydı kapatan taraf `isabet` alanını doldurursa doğar;
        doldurmazsa sayfa "isabet oranı verilmiyor" der ve defter yarım kalır.
        Bu yüzden notsuz kapanış uyarıdır — engel değil, çünkü bazı kayıtlar
        (bir sorunun cevabının bulunması gibi) tuttu/tutmadı ile ölçülmez.
        """
        kapanan = [k for k in defter.get("kayitlar", [])
                   if k.get("durum") == "kapandi"]
        if not kapanan:
            return
        notsuz = [k["konu"] for k in kapanan
                  if str(k.get("isabet", "")).lower() not in ("tuttu", "tutmadi", "kismen")]
        if notsuz:
            self.uyari.append(
                f"Kapanan {len(notsuz)} söz notlanmamış (isabet: tuttu | tutmadi | "
                "kismen) — karne bu yüzden isabet oranı veremiyor: "
                + " · ".join(notsuz[:3]) + ("…" if len(notsuz) > 3 else ""))
        else:
            self._ok(f"söz karnesi: kapanan {len(kapanan)} kaydın hepsi notlanmış")

    def kos(self) -> int:
        self.yazi(); self.veri(); self.atif(); self.sayi(); self.nabiz(); self.tekrar()
        self.tema(); self.izleme(); self.dil(); self.tazelik(); self.tazeleme_atlandi()
        self.karanlik(); self.olu_kalip()
        self.yerlesmemis(); self.piyasa_seansi(); self.revizyon(); self.duzeltme()
        self.devir(); self.haber_tonu(); self.bicim()
        self.olagandisilik_penceresi()
        tur = self.b.get("tur", "gunluk")
        print(f"{'═' * 74}")
        print(f"  BÜLTEN DENETİMİ · {self.b.get('tr_tarih', self.b.get('tarih'))} "
              f"· {'haftaya bakış' if tur == 'haftalik' else 'günlük'}")
        print(f"{'═' * 74}")
        if self.ayrinti:
            for m in self.gecen:
                print(f"  ✓ {m}")
        for m in self.uyari:
            print(f"  ! {m}")
        for m in self.engel:
            print(f"  ✗ {m}")
        print(f"\n  {len(self.gecen)} ölçüt geçti · {len(self.uyari)} uyarı · "
              f"{len(self.engel)} ENGEL")
        if self.engel:
            print("\n  Bülten bu hâliyle YAYINA GİTMEMELİ. Yukarıdaki engelleri giderip "
                  "denetimi tekrar koşturun.")
        return 1 if self.engel else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tarih", nargs="?", default=None)
    ap.add_argument("--hepsi", action="store_true")
    ap.add_argument("--ayrinti", action="store_true")
    a = ap.parse_args()

    sys.path.insert(0, str(BURASI))
    if a.hepsi:
        dosyalar = sorted(BULTEN.glob("*.json"))
    else:
        t = a.tarih or date.today().isoformat()
        dosyalar = [BULTEN / f"{t}.json"]
    kod = 0
    for y in dosyalar:
        if not y.exists():
            print(f"bülten yok: {y.name}")
            kod = 1
            continue
        b = json.loads(y.read_text(encoding="utf-8"))
        kod |= Denetim(b, a.ayrinti).kos()
        print()
    return kod


if __name__ == "__main__":
    sys.exit(main())
