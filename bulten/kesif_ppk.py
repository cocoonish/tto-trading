#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PPK KARAR METNİ KEŞFİ — kararın KENDİ metnini kaynağından okur.

NEDEN VAR. 10.09.2026'da PPK faiz kararı çıktı ve karar üzerine analiz
yazılacaktı; ama bu oturumların çıkış politikası `www.tcmb.gov.tr`yi kapatıyor
(kesif.yml künyesinde ölçülü: ağ geçidi CONNECT'e 403) ve elde kalan tek kanal
arama motoruydu. O kanal ölçülerek GÜVENİLMEZ bulundu: döndürdüğü "piyasa
tepkisi" paragrafı USD/TRY'yi 34,85 diye yazıyordu, oysa hattın kendi ölçümü
09.09 için 48,46 — %28 sapma. Aynı özette bozuk sayılar da vardı ("%B,5").
Bir merkez bankası kararının TONUNU (şahin/güvercin) ölçmek metnin KENDİSİNİ,
üstelik BİR ÖNCEKİ metinle yan yana okumayı gerektirir; ikinci elden özetle
yazılan böyle bir analiz uydurma olurdu.

NE YAPAR. Ağa çıkabilen tek yerden — bulut koşucusundan — PPK basın
duyurularını indirir ve METNİ OLDUĞU GİBİ döker. Yorum YAPMAZ, hüküm KURMAZ:
bu betiğin çıktısı ham girdidir, analiz insanın/yazı katmanının işidir.

SIRA (CLAUDE.md, "dış kaynak önce YOKLANIR"): önce aday adresler KISA zaman
aşımıyla yoklanır, açık kapı bulunur, sonra içerik indirilir. Adres
SABİTLENMEZ, listeden ÇÖZÜLÜR — TCMB duyuru numaraları (DUY2026-NN) yıl içinde
kayar ve sabit bir numara bir sonraki toplantıda yanlış metni getirir.

Koşum (elle):  Keşif iş akışı → betik = bulten/kesif_ppk.py
"""
from __future__ import annotations

import re
import sys
import urllib.error
import urllib.request

UA = "Mozilla/5.0 (compatible; TTO-Trading/1.0; +arastirma)"
YOKLAMA_SN = 8      # aday adres yoklaması — kısa; bir dakikada biter
INDIRME_SN = 30     # açık çıkan kapıdan içerik indirme

# Aday GİRİŞ adresleri. Hiçbiri duyurunun kendisi değil; hepsi LİSTE sayfası,
# çünkü duyuru numarası çözülecek, tahmin edilmeyecek.
def adaylar(yil: int) -> list[tuple[str, str]]:
    """Bir YILIN aday liste sayfaları. Yıl parametre, çünkü ton ölçüsü tek
    yıldan kurulamaz: 2026'nın altı toplantısında politika faizi bir kez
    değişti, yani "hangi metin indirimi getirir" sorusuna tek gözlemle cevap
    verilemez. Arşiv ne kadar geriye giderse hüküm o kadar sınanabilir."""
    return [
        (f"PPK kararları TR {yil}",
         "https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/"
         f"Temel+Faaliyetler/Para+Politikasi/PPK/{yil}"),
        (f"Basın duyuruları TR {yil}",
         "https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/"
         f"Duyurular/Basin/{yil}"),
        (f"Press releases EN {yil}",
         "https://www.tcmb.gov.tr/wps/wcm/connect/EN/TCMB+EN/Main+Menu/"
         f"Announcements/Press+Releases/{yil}"),
    ]


ADAYLAR = adaylar(2026)

ETIKET = re.compile(r"<[^>]+>")
BOSLUK = re.compile(r"[ \t\r\f\v]+")


def _cek(url: str, sn: int) -> tuple[int, str]:
    """(http kodu, gövde). Hata KOD olarak döner — betik düşmez, ölçüm sürer."""
    istek = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(istek, timeout=sn) as y:
            ham = y.read()
            try:
                return y.status, ham.decode("utf-8")
            except UnicodeDecodeError:
                return y.status, ham.decode("iso-8859-9", errors="replace")
    except urllib.error.HTTPError as ex:
        return ex.code, ""
    except Exception as ex:                                    # noqa: BLE001
        return -1, f"{type(ex).__name__}: {ex}"


def _metin(html: str) -> str:
    """HTML → düz metin. Kütüphane yok: keşif betiği bağımlılık İSTEMEZ."""
    g = re.sub(r"(?is)<(script|style|head)[^>]*>.*?</\1>", " ", html)
    g = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>|</tr>", "\n", g)
    g = ETIKET.sub(" ", g)
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&quot;", '"'),
                 ("&#39;", "'"), ("&lt;", "<"), ("&gt;", ">")):
        g = g.replace(a, b)
    g = BOSLUK.sub(" ", g)
    return "\n".join(s.strip() for s in g.split("\n") if s.strip())


def _duyuru_baglari(html: str, taban: str) -> list[tuple[str, str]]:
    """Sayfadaki duyuru bağlarını (metin, adres) olarak çıkar."""
    out: list[tuple[str, str]] = []
    for m in re.finditer(r'(?is)<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html):
        adres, ad = m.group(1), _metin(m.group(2))
        if not ad:
            continue
        if not re.search(r"(?i)DUY20\d\d-\d+|ANO20\d\d-\d+", adres):
            continue
        if adres.startswith("/"):
            adres = "https://www.tcmb.gov.tr" + adres
        elif not adres.startswith("http"):
            adres = taban.rsplit("/", 1)[0] + "/" + adres
        out.append((ad, adres))
    return out


def yoklama(yillar: list[int]) -> int:
    """YOKLAMA KİPİ — arşiv ne kadar geriye gidiyor, yılda kaç karar var.

    Ölçüm hattı kurmadan ÖNCE koşar (CLAUDE.md: "dış kaynak önce YOKLANIR").
    Tam metinleri indirmez, yalnız SAYAR: hangi yılın liste sayfası açılıyor,
    kaç faiz kararı ve kaç toplantı özeti bağı var. Çıktı küçük, bir dakikada
    biter ve "kaç metinlik bir arşiv kurulabilir" sorusunu ölçüyle cevaplar.
    """
    print("PPK ARŞİV YOKLAMASI — yıl yıl kapı ve belge sayımı")
    print("=" * 72)
    toplam_k = toplam_o = 0
    for yil in yillar:
        baglar: dict[str, str] = {}
        acik_sayfa = 0
        for ad, url in adaylar(yil):
            kod, govde = _cek(url, YOKLAMA_SN)
            if kod != 200:
                continue
            acik_sayfa += 1
            for metin, adres in _duyuru_baglari(govde, url):
                baglar.setdefault(adres, metin)
        kararlar = [m for m in baglar.values()
                    if "faiz oran" in m.lower() or "interest rate" in m.lower()]
        ozetler = [m for m in baglar.values()
                   if "toplantı özeti" in m.lower() or "summary of the monetary" in m.lower()]
        # TR ve EN aynı belgeyi iki kez listeliyor; tekil belge sayısı yarısı.
        print(f"  {yil}   açık liste sayfası {acik_sayfa}/3 · "
              f"toplam bağ {len(baglar):3} · faiz kararı {len(kararlar):2} "
              f"(tekil ~{len(kararlar)//2 or len(kararlar)}) · özet {len(ozetler):2}")
        toplam_k += len(kararlar)
        toplam_o += len(ozetler)
    print(f"\n  TOPLAM faiz kararı bağı {toplam_k} · özet bağı {toplam_o}")
    print("  (her belge TR ve EN olarak iki kez listeleniyor)")
    return 0


def main() -> int:
    # Yoklama kipi: `--yokla 2019 2020 …`
    if "--yokla" in sys.argv:
        i = sys.argv.index("--yokla")
        yillar = [int(a) for a in sys.argv[i + 1:] if a.isdigit()]
        return yoklama(yillar or [2026])
    print("PPK KARAR METNİ KEŞFİ")
    print("=" * 72)

    # ---------------------------------------------------- 1. KAPI YOKLAMASI
    print("\n▶ 1. Aday adresler yoklanıyor (her biri en çok "
          f"{YOKLAMA_SN} sn)")
    acik: list[tuple[str, str, str]] = []
    for ad, url in ADAYLAR:
        kod, govde = _cek(url, YOKLAMA_SN)
        durum = "AÇIK" if kod == 200 else f"kapalı ({kod})"
        print(f"    {ad:26} {durum:16} {url[:70]}")
        if kod == 200:
            acik.append((ad, url, govde))
    if not acik:
        print("\n  HİÇBİR KAPI AÇILMADI. Bu koşucudan da TCMB'ye erişilemiyor —")
        print("  karar metni bu yoldan ALINAMAZ. Analiz metne dayandırılamaz.")
        return 1

    # ------------------------------------------------------ 2. BAĞ ÇÖZÜMÜ
    print("\n▶ 2. Duyuru bağları çözülüyor (numara TAHMİN EDİLMİYOR)")
    baglar: dict[str, str] = {}
    for ad, url, govde in acik:
        bulunan = _duyuru_baglari(govde, url)
        print(f"    {ad:26} {len(bulunan)} duyuru bağı")
        for metin, adres in bulunan:
            baglar.setdefault(adres, metin)

    if not baglar:
        print("\n  Bağ bulunamadı. Açık sayfaların GERÇEK içeriğinden ilk 60 satır:")
        for ad, url, govde in acik[:1]:
            for satir in _metin(govde).split("\n")[:60]:
                print("      " + satir[:150])
        return 1

    # Faiz kararı ile toplantı özeti AYRI belgelerdir; ikisi de ilgi alanında,
    # ama tonu belirleyen KARAR metnidir ve önce o basılır.
    def _puan(m: str) -> int:
        ml = m.lower()
        if "faiz oran" in ml or "faiz kararı" in ml or "interest rate" in ml:
            return 0
        if "toplantı özeti" in ml or "summary of the monetary" in ml:
            return 1
        return 2

    # SIRALAMA NUMARAYA GÖRE, ALFABEYE GÖRE DEĞİL. İlk yazımda adrese göre
    # sıralanmıştı ve "…-01" < "…-12" < "…-17" olduğu için betik yılın EN ESKİ
    # üç kararını indirdi; aranan BUGÜNKÜ karardı. Duyuru numarası yıl içinde
    # artıyor, yani en büyük numara en yeni belgedir.
    def _no(adres: str) -> int:
        m = re.search(r"(?i)(?:DUY|ANO)20\d\d-(\d+)", adres)
        return int(m.group(1)) if m else -1

    # Dil de ayrılır: aynı belge TR ve EN olarak iki kez listeleniyor. Okura
    # yazılacak alıntı TÜRKÇE metinden gelmeli; İngilizcesi kıyas için durur.
    def _dil(adres: str) -> str:
        return "EN" if "/EN/" in adres or "ANO" in adres.upper() else "TR"

    sirali = sorted(baglar.items(),
                    key=lambda kv: (_puan(kv[1]), -_no(kv[0]), kv[0]))
    print(f"\n    toplam {len(sirali)} benzersiz duyuru (yeniden eskiye):")
    for adres, metin in sirali[:26]:
        print(f"      [{_puan(metin)}] no={_no(adres):>3} {_dil(adres)} {metin[:74]}")

    # --------------------------------------------------------- 3. METİNLER
    # SON İKİ karar indirilir, HER İKİ DİLDE. Ton ancak KIYASLA ölçülür: tek
    # metin "şahin mi güvercin mi" sorusuna cevap veremez, cevabı veren şey
    # bir önceki metne göre NEYİN DEĞİŞTİĞİDİR. Toplantı özetinin en yenisi de
    # eklenir — karar metni kısa, gerekçe orada.
    kararlar = [(a, m) for a, m in sirali if _puan(m) == 0]
    ozetler = [(a, m) for a, m in sirali if _puan(m) == 1]
    # YILIN BÜTÜN karar metinleri iniyor, son iki karar değil. Sebep ölçüldü:
    # 2026-38 ile 2026-28 yan yana konunca üç paragrafın üçü BİREBİR aynı ve
    # yalnız teşhis paragrafı değişiyor. Tek kıyas "değişti" der, ama o
    # değişimin YILIN EĞİLİMİ mi yoksa tek toplantılık salınım mı olduğunu
    # söyleyemez; altı toplantının altısı elde olmadan "güvercinleşti" cümlesi
    # kurulamaz. Belgeler kısa (~4 KB), maliyeti bir saniye.
    hedef = kararlar + ozetler[:4]
    print(f"\n▶ 3. {len(hedef)} belge indiriliyor "
          f"(yılın {len(kararlar)//2} kararı iki dilde + son iki özet)")

    # Sayfanın gövdesi menü gürültüsünün İÇİNDE duruyor; künye satırından
    # başlayıp adres bloğunda bitiriyoruz. Kesme YAPILMAZSA metin okunmaz,
    # AŞIRI kesilirse iddia kaybolur — sınır belgenin kendi işaretlerinden.
    # Çıpa İKİ DİLDE de tutmalı: EN sayfası "No: 2026-38", TR sayfası
    # "Sayı: 2026-38" yazıyor. İlk yazımda yalnız İngilizcesi vardı ve
    # Türkçe metinlerin DÖRDÜ DE künye çıpası tutmadan döküldü — alıntı
    # okura Türkçe gidecek, yani kaybedilen tam da gereken metindi.
    BAS = re.compile(r"^(No|Say[ıi])\s*:\s*(DUY|ANO)?20\d\d-\d+")
    SON = re.compile(r"(?i)^(Central Bank of the Republic|"
                     r"T[üu]rkiye Cumhuriyet Merkez Bankas[ıi]|"
                     r"Faiz Oranlar[ıi]na [İIi]li[şs]kin Bas[ıi]n Duyurusu \(|"
                     r"Para Politikas[ıi] Kurulu Toplant[ıi] [ÖOo]zeti \(|"
                     r"Press Release on Interest Rates \(|"
                     r"Summary of the Monetary Policy Committee Meeting \()")
    for adres, ad in hedef:
        kod, govde = _cek(adres, INDIRME_SN)
        print("\n" + "=" * 72)
        print(f"BAŞLIK : {ad}  [{_dil(adres)}]  no={_no(adres)}")
        print(f"ADRES  : {adres}")
        print(f"DURUM  : {kod}")
        print("=" * 72)
        if kod != 200:
            print("  (indirilemedi)")
            continue
        satirlar = _metin(govde).split("\n")
        icinde, basildi = False, 0
        for satir in satirlar:
            if not icinde and BAS.match(satir):
                icinde = True
            if not icinde:
                continue
            if SON.match(satir):
                break
            if len(satir) > 2:
                print(satir[:2000])
                basildi += 1
        if not basildi:
            # Çıpa tutmadı: SESSİZ geçme, ham metnin başını dök ki bir sonraki
            # koşu neyin bulunabileceğini bilsin.
            print("  ! künye çıpası tutmadı — ham metnin ilk 80 satırı:")
            for satir in satirlar[:80]:
                print("    " + satir[:200])
    print("\nKEŞİF BİTTİ.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
