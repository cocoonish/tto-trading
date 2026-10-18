#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FX gün içi ders serisinin kapısı (sayfa sınavı 26 bu dosyayı kendiliğinden koşturur).

Yalnız standart kütüphane: yayın koşucusunda pandas, numba ya da plotly yok ve bu kapı onlara ihtiyaç duymaz. Girdisi
depodaki ölçüm dosyasıdır (cikti/ders/olcum.json); ağa çıkmaz, duvar saati okumaz.

Ölçütler:
  1. Yeniden üretim — serinin dersleri ölçüm dosyasından ve şablonlardan yeniden üretilir ve sitedeki MDX'le BİREBİR
     aynı olmalıdır. Elle düzeltilmiş bir ders, ölçümü değişip yeniden yazılmamış bir ders ya da şablonu değişip
     üretilmemiş bir ders düşer. Üretimin kendisi de bir kapıdır: şablonların bütün iddiaları ölçüme karşı sınanır.
  2. Figürler — her gömülen figür sitede durur ve çizildiği ölçüm dosyasının özünü taşır; özü bugünkü ölçümden
     farklı bir figür (ölçüm değişmiş, şekil yeniden çizilmemiş) düşer. Hiçbir derste gömülmeyen figür de düşer.
     Her figürde sitenin ev stili uygulanmış olmalı ve başlık bloğunun her satırı telefonun gömme çerçevesine
     sığmalıdır (ölçü çizim katmanının kendisinden: sekil_ortak.tasan_satirlar).
  3. Sayı envanteri — şablonlardaki her ondalık sayı ve yüzde ya bir yer tutucudan gelir, ya bildirilmiş bir sabittir
     ({{= "…" }}), ya da aşağıdaki tanım listesindedir. Elle yazılmış bir ölçüm şablona giremez.
  4. Sıra — serinin okuma sırası (adlar.DERS_SIRA) sitedeki ders grubunun sırasıyla aynıdır; ön koşullar seridedir.
  5. Ön kayıt — yayımlanan kopya kaynağın kendisidir.
  6. Künye — ölçüm dosyasının pariteleri, nokta/pip büyüklükleri ve penceresi bugünkü ayarla aynıdır.
  7. Ön kaydın geçmişi — ölçüm dosyasının taşıdığı geçmiş beklenen geçmiştir (onkayit_gecmis.BEKLENEN) ve ön kaydın
     içeriğini değiştiren her kayıt ilk sonuçlardan öncedir.
  8. TSİ — strateji şablonlarında bir kural ya da kontrol listesi maddesi (madde imiyle başlayan satır ve devamı) bir
     saat (SS:DD) taşıyorsa TSİ karşılığını da taşır: ya metinde "TSİ" geçer ya da {{! tsi … }} bloğu saat dilimi
     kurallarından hesaplar. Okurun kullanacağı yer tam bu maddelerdir.
  9. Kova sırası — ölçümdeki her koşul kovasının okuma sırası tanımlıdır (adlar.KOVA_OKUMA).
  10. Örnek günler — her panelde stop ve hedef çizgisi en az bir mum uzunluğundadır (sıfır uzunluktaki çizgi ekranda
     yoktur ve alt yazı onu anlatır).
  11. MDX yapısı — bir blok etiketi (<details>, <div …>) satırı açıyorsa ve kapanışı o satırda değilse satırda başka
     metin taşımaz: MDX aynı satırdaki metni paragraf sayar, kapanış etiketini o paragrafta arar ve site derlemesi
     düşer. Kapı derlemeden önce koşar; bu ölçüt o düşüşü zincirin içinde yakalar.
  12. Kod özleri — ölçüm dosyası kendisini üreten kodun dosya başına özünü taşır (künye.kod), her gömülen figür
     kendisini çizen kodun özünü (tto-kod-ozu: sekil_ortak.SEKIL_KODU). İkisi yalnız hashlib ile yeniden hesaplanır;
     kod değişip ölçüm yeniden koşulmadıysa "yeniden ölçülmeli", figür yeniden çizilmediyse "yeniden çizilmeli".
     Listelerin asgari kapsamı kapının kendi kümesinden (OLCUM_KODU_ASGARI · SEKIL_KODU_ASGARI): daraltılan bir
     liste, daralan listeyle yine eşit çıkardı. Figürün çağırdığı plotly.js dosyası sitede durur.
  13. Pariteler — ders metninde geçen her döviz paritesi künyenin paritelerindendir; şablonlarda paritelerin sayısını
     söyleyen sözcük ("dört paritede", "dört majör", "dört majör (…)") künyenin parite sayısıdır ("en az", "bu",
     "öbür" ile başlayan alt küme sayımları hariç). Parite listesi değişince eski sayıyı taşıyan cümleler adıyla
     düşer; paritelerin tam listesi şablonda elle yazılmaz, künyeden basılır (`pariteler` biçimi, `pip_tanimi`).
  14. Örnek eşiği — metin "yarım R" diyorsa örnek günlerin eşiği (künye.ornek.esik) 0,5'tir.
  15. TSİ, üretilmiş metinde ve figürlerde — her yerel saat (Londra, New York, Frankfurt, Tokyo, UTC) TSİ
     karşılığını DEĞERİYLE taşır: kapı karşılığı saat dilimi kurallarından kendisi hesaplar (tarihli saatte o günün,
     "yazın", "kışın", "ara hafta" diye nitelenmişse o rejimin, değilse yaz ve kış saatinin) ve hepsini aynı cümlenin
     TSİ saatlerinde arar; "TSİ" sözcüğünün varlığı yetmez, yanlış bir karşılık da düşer. Birimler: paragraf, madde,
     başlık, ön bilginin okura giden alanları, figür başlığı, katlanır özet ve tablo (italik notuyla birlikte;
     parametre tablosunun değeri aynı bölümün ızgara notuyla da kapanır). Şehri okunamayan saat "şehri belirsiz"
     diye düşer; kuralın adındaki saat (NY IB 08:00, WM/R 16:00) ad sayılır. Giriş dersinin "bütün saatler ayrıca
     TSİ olarak yazılır" cümlesi bu ölçütün sözüdür; ayrıntı tsi_saatleri'nin belgesinde.
  16. Kural sabitleri — metinde ve figürlerde yazılan her "ATR(N)" ön kaydın ATR periyotlarındandır (künye: kuralların
     mum ATR'si atr_kural, haber kurallarının ve gün ATR'sinin periyodu haber_sabit). Periyot ön kayıtta değişirse
     eski sayıyı taşıyan cümle ve figür adıyla düşer; kural kodundaki periyodun ön kayıtla aynı olduğunu birim
     sınaması sorar (testler/test_dogrula.py).
  17. Atıflar — derslerin her literatür atfı (anlatı ve parantez biçimi) atıf kaydında doğrulanmış bir kayda karşılık
     gelir ve kayıt o dersi anar; kaydın her alıntısı bulutta dondurulmuş kaynağın kendi metninde (özet, ilk sayfa ya
     da tam metinden bir pasaj) geçer; künyenin yılı, cildi, sayısı, sayfaları ve başlığı dondurulmuş künyeyle
     tutar; dondurulmuş dizin kayıtlı özleriyle aynıdır. Kaynakça listesi kayıttan basılır. Tanım ve ayrıntı atif.py.

Dersler henüz siteye yazılmamışsa (yayın öncesi) kapı bunu söyler ve geçer; bir kısmı yazılmışsa düşer.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
sys.path.insert(0, str(BURASI))

import adlar  # noqa: E402
import atif  # noqa: E402
import ders_yaz as dy  # noqa: E402

GRUP_TS = dy.KOK / "site" / "src" / "lib" / "dersGruplari.ts"

#: Tanım gereği sabit olan sayılar (ölçüm değil): aralık ve sınama düzeyleri (%95, %5, 0,95), pip büyüklükleri
#: (0,0001 · 0,01), olasılık tanımları (%50 yazı tura; %30 ve %70 isabet örneği). Buraya bir ÖLÇÜM yazılamaz; bir
#: kodun sabiti de yazılamaz — örnek gün eşiği, temel kayma ve veri denetiminin kapsam eşikleri künyeden basılır.
TANIM = {"%95", "%5", "%50", "%30", "%70", "0,0001", "0,01", "0,95"}

#: Ölçüt 12'nin asgari kapsamları (kapının kendi kümesi; sınanan listeler bunları taşımalı).
OLCUM_KODU_ASGARI = {"ders_olcum.py", "adlar.py", "kosu.py", "motor.py", "strateji.py", "strat_haber.py", "takvim.py",
                     "metrik.py", "saglamlik.py", "basarisiz.py"}
SEKIL_KODU_ASGARI = {"Aktarılacak Projeler/FxGunici/sekil.py", "Aktarılacak Projeler/FxGunici/sekil_ortak.py",
                     "Aktarılacak Projeler/FxGunici/adlar.py", "site/tools/plotly_stil.py"}

_SAYI = re.compile(r"(?<![\w/.,])(?:%\d+(?:,\d+)?|[−+-]?\d+,\d+%?)")


def _govde(metin: str) -> str:
    if metin.startswith("---\n"):
        metin = metin[metin.index("\n---\n", 4) + 5:]
    metin = re.sub(r"\{\{.*?\}\}|\{%.*?%\}", " ", metin, flags=re.S)
    return re.sub(r"\]\([^)]*\)", "]", metin)                     # bağlantı hedefi okur metni değil


def sayi_envanteri() -> list[str]:
    hata = []
    for yol in sorted((BURASI / "metin").glob("*.md")) + sorted((BURASI / "metin" / "strateji").glob("*.md")):
        for m in _SAYI.finditer(_govde(yol.read_text(encoding="utf-8"))):
            if m.group(0) not in TANIM:
                hata.append(f"{yol.relative_to(BURASI)}: elle yazılmış sayı {m.group(0)!r}")
    return hata


def _figur_json(h: str) -> dict | None:
    """Figürün izleri ve düzeni, Plotly'nin kendi çağrısından (newPlot'un ikinci ve üçüncü argümanı)."""
    dec = json.JSONDecoder()
    i = h.find("Plotly.newPlot(")
    if i < 0:
        return None
    try:
        j = h.index(",", i) + 1
        veri, k = dec.raw_decode(h, j + len(h[j:j + 50]) - len(h[j:j + 50].lstrip()))
        k = h.index(",", k) + 1
        duzen, _ = dec.raw_decode(h, k + len(h[k:k + 50]) - len(h[k:k + 50].lstrip()))
    except ValueError:
        return None
    return {"data": veri, "layout": duzen}


def figur_bicimi(ad: str, h: str) -> list[str]:
    """Gömülen figürün biçimi: sitenin ev stili uygulanmış mı (figürün üst payı o stille kurulur; stilsiz figürde
    başlık çizim alanına biner) ve başlık bloğunun her satırı telefonun gömme çerçevesine sığıyor mu (Plotly başlığı
    sarmaz, sağ ucu kırpılır); panel başlıkları da (sekil_ortak.panel_tasmasi). Ölçü çizim katmanının kendi
    tanımıdır; orada yalnız uyarıdır."""
    import sekil_ortak as so                  # çizim kütüphanesi olmadan da içe aktarılır
    hata = []
    if so.EV_STILI_ISARET not in h:
        hata.append(f"{ad}.html: ev stili uygulanmamış (sekil.py ev stiliyle yeniden koşulmalı)")
    d = _figur_json(h)
    if d is None:
        hata.append(f"{ad}.html: figürün düzeni okunamadı")
        return hata
    bas = ((d["layout"].get("title") or {}).get("text")) or ""
    hata += [f"{ad}.html: başlık satırı telefonun gömme çerçevesinde taşar — {t}" for t in so.tasan_satirlar(bas)]
    hata += [f"{ad}.html: panel başlığı telefonun gömme çerçevesinde — {t}" for t in so.panel_tasmasi(d)]
    if ad.endswith("-ornek"):
        hata += ornek_cizgileri(ad, d)
    return hata + tsi_figurde(ad, d) + atr_figurde(ad, d)


def _an(x) -> float | None:
    from datetime import datetime
    try:
        return datetime.strptime(str(x)[:19], "%Y-%m-%d %H:%M:%S").timestamp()
    except ValueError:
        return None


def ornek_cizgileri(ad: str, d: dict) -> list[str]:
    """Örnek gün panellerinde stop ve hedef çizgisi en az bir mum uzunluğunda görünür. Giriş ile çıkış aynı
    dakikadayken girişten çıkışa çizilen çizgi sıfır uzunlukta kalıyor ve alt yazının "kırmızı: stop" dediği
    seviye ekranda yoktu. Mum uzunluğu panelin kendi mumlarından (ardışık iki mumun en küçük aralığı)."""
    mum: dict = {}
    for iz in d.get("data") or []:
        if iz.get("type") == "candlestick" and isinstance(iz.get("x"), list):
            t = sorted(a for a in (_an(x) for x in iz["x"]) if a is not None)
            fark = [b - a for a, b in zip(t, t[1:]) if b > a]
            if fark:
                mum[iz.get("xaxis") or "x"] = min(fark)
    hata = []
    for iz in d.get("data") or []:
        if iz.get("name") in ("stop", "hedef") and isinstance(iz.get("x"), list) and len(iz["x"]) == 2:
            a, b = (_an(x) for x in iz["x"])
            uzun = mum.get(iz.get("xaxis") or "x")
            if a is None or b is None or uzun is None or b - a < uzun:
                hata.append(f"{ad}.html: {iz['name']} çizgisi bir mumdan kısa ({iz.get('xaxis') or 'x'} paneli)")
    return hata


def kova_sirasi() -> list[str]:
    """Ölçüm dosyasındaki her koşul kovası adlar.KOVA_OKUMA'da durur: listede olmayan kova ölçümdeki sırasını korur ve
    aynı değişken figürden figüre (ve metinde) ters sırayla basılırdı."""
    if not dy.OLCUM.exists():
        return []
    o = json.loads(dy.OLCUM.read_text(encoding="utf-8"))
    eksik = sorted({kv["kova"] for b in (o.get("birim") or {}).values() for v in (b.get("cift") or {}).values()
                    for k in (((v or {}).get("varsayilan") or {}).get("kosul") or [])
                    for kv in (k.get("kovalar") or []) if kv.get("kova") not in adlar.KOVA_OKUMA})
    return [f"okuma sırası tanımsız koşul kovası (adlar.KOVA_OKUMA): {', '.join(eksik)}"] if eksik else []


def kunye_denetimi() -> list[str]:
    """Ölçüm dosyasının künyesi bugünkü ayarla aynı mı (pariteler, nokta ve pip büyüklükleri, pencere). Bu soru bir
    birim sınaması olarak zincirin İLK adımında soruluyordu ve kendini kilitliyordu: parite listesi değişince sınama
    bir önceki koşunun ölçümünü okuyup düşüyor, ölçümü yenileyecek adım hiç koşmuyordu. Kapıda, ölçümden sonra sorulur."""
    import ayar as ay
    if not dy.OLCUM.exists():
        return []
    a = ay.oku()
    k = json.loads(dy.OLCUM.read_text(encoding="utf-8")).get("kunye") or {}
    hata = []
    if k.get("ciftler") != list(a.ciftler):
        hata.append(f"ölçümün pariteleri {k.get('ciftler')} ayarınkiyle aynı değil {list(a.ciftler)}")
    if k.get("nokta") != {c: a.nokta[c] for c in a.ciftler} or k.get("pip") != {c: a.pip[c] for c in a.ciftler}:
        hata.append("ölçümün nokta/pip büyüklükleri ayarınkiyle aynı değil")
    if (k.get("baslangic"), k.get("bitis")) != (a.baslangic.isoformat(), a.bitis.isoformat()):
        hata.append("ölçümün penceresi ayarınkiyle aynı değil")
    return hata


def onkayit_denetimi() -> list[str]:
    """Ölçüm dosyasının taşıdığı ön kayıt geçmişi beklenen geçmiş mi (tek tanım: onkayit_gecmis)."""
    import onkayit_gecmis as og
    if not dy.OLCUM.exists():
        return []
    k = json.loads(dy.OLCUM.read_text(encoding="utf-8")).get("kunye") or {}
    hata = og.denetle(k.get("onkayit_gecmisi"))
    if k.get("onkayit_ilk_sonuc") != {"commit": og.ILK_SONUC[0], "zaman": og.ILK_SONUC[1]}:
        hata.append("ölçüm dosyasının ilk sonuç kaydı beklenenle aynı değil")
    return hata


_MADDE = re.compile(r"^(?:- |\d+\. )\*\*")
_SAAT = re.compile(r"(?<![\d,.])\d{1,2}:\d{2}(?!\d)")


def tsi_denetimi() -> list[str]:
    """Ölçüt 8: saat taşıyan kural ve kontrol listesi maddesinin TSİ karşılığı (şablonda)."""
    hata = []
    for yol in sorted((BURASI / "metin" / "strateji").glob("*.md")):
        satir = yol.read_text(encoding="utf-8").split("\n")
        i = 0
        while i < len(satir):
            if not _MADDE.match(satir[i]):
                i += 1
                continue
            j = i + 1
            while j < len(satir) and satir[j].startswith("  ") and not _MADDE.match(satir[j].lstrip()):
                j += 1
            madde = " ".join(satir[i:j])
            if _SAAT.search(re.sub(r"\{\{.*?\}\}", " ", madde)) and "TSİ" not in madde and "{{! tsi " not in madde:
                hata.append(f"{yol.relative_to(BURASI)}:{i + 1}: saat var, TSİ karşılığı yok: {madde[:80]}…")
            i = j
    return hata


def olcum_kodu() -> list[str]:
    """Ölçüt 12, ölçüm yarısı: künye.kod'daki her dosyanın bugünkü özü kayıttakiyle aynı ve tek öz tutarlı."""
    if not dy.OLCUM.exists():
        return []
    k = (json.loads(dy.OLCUM.read_text(encoding="utf-8")).get("kunye") or {}).get("kod") or {}
    dosya = k.get("dosya") or {}
    if not dosya:
        return ["ölçüm dosyası kendisini üreten kodun özünü taşımıyor (yeniden ölçülmeli)"]
    hata = []
    eksik = sorted(OLCUM_KODU_ASGARI - set(dosya))
    if eksik:
        hata.append(f"ölçümün kod künyesi asgari dosyaları taşımıyor: {', '.join(eksik)}")
    h = hashlib.sha256()
    for d, o in sorted(dosya.items()):
        yol = BURASI / d
        simdi = hashlib.sha256(yol.read_bytes()).hexdigest() if yol.exists() else None
        if simdi != o:
            hata.append(f"{d}: ölçüm koşulduktan sonra değişti (yeniden ölçülmeli)")
        h.update(f"{d}\0{o}\0".encode())
    if h.hexdigest() != k.get("oz"):
        hata.append("ölçümün kod özü dosya özleriyle tutmuyor")
    return hata


def sekil_kodu() -> tuple[str | None, list[str]]:
    """Ölçüt 12, figür yarısı: figür kodunun bugünkü özü ve listenin asgari kapsamı (sekil_ortak.kod_ozu)."""
    import sekil_ortak as so
    liste = {p.relative_to(dy.KOK).as_posix() for p in so.SEKIL_KODU}
    eksik = sorted(SEKIL_KODU_ASGARI - liste)
    return so.kod_ozu(), ([f"figür kodu özünün listesi asgari dosyaları taşımıyor: {', '.join(eksik)}"] if eksik else [])


_DOVIZ = "USD|EUR|GBP|JPY|AUD|NZD|CAD|CHF|TRY|SEK|NOK|DKK|CNH|CNY|MXN|ZAR|HKD|SGD|PLN|HUF|CZK|RUB|INR|KRW|BRL"
_PARITE_AD = re.compile(rf"(?<![A-Z])(?:{_DOVIZ})/(?:{_DOVIZ})(?![A-Z])")
_SAYI_SOZ = {"iki": 2, "üç": 3, "dört": 4, "beş": 5, "altı": 6, "yedi": 7, "sekiz": 8, "dokuz": 9, "on": 10}
# "majör" tek başına da sayım sözcüğüdür ("yalnız dört majör (…)"): yalnız "majör parite"yi arayan kalıp, sayıyı
# parantezli bir listeyle veren cümleyi görmüyordu. Sözcük araları her boşluktur: şablonlar satır sonundan bölünür ve
# "en az⏎iki paritede" bir alt küme sayımıdır, yalnız boşluk arayan kalıp onu elle yazılmış parite sayısı sanardı.
_PARITE_SAYI = re.compile(r"(?<![\wçğıöşüÇĞİÖŞÜ])((?:en\s+az|bu|öbür)\s+)?"
                          r"(iki|üç|dört|beş|altı|yedi|sekiz|dokuz|on)\s+(?:majör(?:\s+parite)?|parite)", re.I)


def parite_denetimi(cikti: dict) -> list[str]:
    """Ölçüt 13: metindeki pariteler künyeden, şablonların parite sayısı künyenin sayısı."""
    if not dy.OLCUM.exists():
        return []
    ciftler = (json.loads(dy.OLCUM.read_text(encoding="utf-8")).get("kunye") or {}).get("ciftler") or []
    adlar_ = {f"{c[:3]}/{c[3:]}" for c in ciftler}
    hata = []
    for slug, (mdx, _) in cikti.items():
        yabanci = sorted(set(_PARITE_AD.findall(mdx)) - adlar_)
        if yabanci:
            hata.append(f"{slug}: künyede olmayan parite geçiyor: {', '.join(yabanci)}")
    for yol in sorted((BURASI / "metin").glob("*.md")) + sorted((BURASI / "metin" / "strateji").glob("*.md")):
        metin = re.sub(r"\{\{.*?\}\}|\{%.*?%\}", " ", yol.read_text(encoding="utf-8"), flags=re.S)
        for m in _PARITE_SAYI.finditer(metin):
            if m.group(1):
                continue
            # Türkçe büyük harf: cümle başındaki "İki" str.lower() ile "i̇ki" olur (i + birleştirici nokta) ve sözlükte
            # yoktur; büyük İ ve I önce Türkçe kuralla küçültülür.
            if _SAYI_SOZ[m.group(2).replace("İ", "i").replace("I", "ı").lower()] != len(ciftler):
                hata.append(f"{yol.relative_to(BURASI)}: parite sayısı elle yazılmış ve künyeyle tutmuyor "
                            f"({m.group(0)!r}; künyede {len(ciftler)} parite)")
    return hata


_ATR_YAZIM = re.compile(r"\bATR\((\d+)\)")


def atr_periyotlari() -> set[int] | None:
    """Ölçüt 16: ön kaydın ATR periyotları, ölçüm künyesinden (kural · haber · gün)."""
    if not dy.OLCUM.exists():
        return None
    k = json.loads(dy.OLCUM.read_text(encoding="utf-8")).get("kunye") or {}
    hs = k.get("haber_sabit") or {}
    p = {k.get("atr_kural"), hs.get("atr_mum"), hs.get("atr_gun")}
    return None if None in p else {int(x) for x in p} | {int(x) for x in k.get("atr_onkayit") or []}


def atr_denetimi(cikti: dict) -> list[str]:
    """Ölçüt 16, metin yarısı: üretilmiş metindeki her ATR(N) ön kaydın periyotlarındandır."""
    p = atr_periyotlari()
    if p is None:
        return ["künyede ATR periyodu yok (atr_kural · haber_sabit.atr_mum · atr_gun): ölçüm yeniden koşulmalı"]
    hata = []
    for slug, (mdx, _) in cikti.items():
        for m in _ATR_YAZIM.finditer(mdx):
            if int(m.group(1)) not in p:
                hata.append(f"{slug}.mdx: {m.group(0)} ön kaydın ATR periyotlarında yok ({sorted(p)}): "
                            f"…{mdx[max(0, m.start() - 40):m.end() + 20]}…")
    return hata


def atr_figurde(ad: str, d: dict) -> list[str]:
    """Ölçüt 16, figür yarısı: başlık bloğundaki ve notlardaki ATR(N)."""
    p = atr_periyotlari()
    if p is None:
        return []                                     # metin yarısı künye eksiğini bir kez söyler
    metinler = [((d.get("layout") or {}).get("title") or {}).get("text") or ""]
    metinler += [a.get("text") or "" for a in (d.get("layout") or {}).get("annotations") or []]
    return [f"{ad}.html: {m.group(0)} ön kaydın ATR periyotlarında yok ({sorted(p)})"
            for t in metinler for m in _ATR_YAZIM.finditer(t) if int(m.group(1)) not in p]


def ornek_esigi(cikti: dict) -> list[str]:
    """Ölçüt 14: "yarım R" diyen metin, örnek günlerin eşiği 0,5 iken doğrudur."""
    if not dy.OLCUM.exists():
        return []
    esik = ((json.loads(dy.OLCUM.read_text(encoding="utf-8")).get("kunye") or {}).get("ornek") or {}).get("esik")
    yarim = sorted(slug for slug, (mdx, _) in cikti.items() if "yarım R" in mdx)
    if yarim and esik != 0.5:
        return [f"metin 'yarım R' diyor ({', '.join(yarim)}), örnek günlerin eşiği {esik}"]
    return []


_ZAMAN = re.compile(r"(?<![\d:,.])([01]\d|2[0-3]):([0-5]\d)(?::([0-5]\d))?(?![\d:])")
#: Yerel saatin şehri ve saat dilimi. "ET" New York saatinin, "ABD" ABD verisinin (New York) kısaltmasıdır.
_YERLER = {"New York": "America/New_York", "ET": "America/New_York", "ABD": "America/New_York",
           "Londra": "Europe/London", "Frankfurt": "Europe/Berlin", "Tokyo": "Asia/Tokyo",
           "Sidney": "Australia/Sydney", "UTC": "UTC"}
_HARF = "A-Za-zÇĞİÖŞÜçğıöşüâîû"
#: Çok sözcüklü şehir adı satır sonundan bölünebilir ("New\nYork"): MDX satır sonunu boşluk basar.
_YER = "|".join(re.escape(k).replace(r"\ ", r"\s+") for k in sorted(_YERLER, key=len, reverse=True))
_YER_RE = re.compile(rf"(?<![{_HARF}])({_YER})(?![{_HARF}])")
_EK = r"(?:['’][a-zçğıöşü]+)?"


def _yer_adi(x: str) -> str:
    """Eşleşen şehir adının sözlükteki yazımı (satır sonu ve fazla boşluk tek boşluk)."""
    return re.sub(r"\s+", " ", x)
_ZAMAN_S = r"(?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d)?"
#: Saat taşıyan adlar sınanmaz: kuralın adındaki saat kuralın tanımında TSİ'siyle yazılır.
_SAATLI_AD = re.compile(r"NY IB \d{2}:\d{2}(?: ve \d{2}:\d{2})?|ilk denge(?: kırılımı|si) — \d{2}:\d{2}|WM/R 16:00"
                        r"|\d{2}:\d{2} rejim[a-zçğıöşü]*")
#: Saat rejimlerinin temsilci günleri: yaz · kış · ara hafta (ABD yaz, Avrupa kış saatinde). Kapı üreticinin
#: yardımcısını (adlar.tsi_yaz) kullanmaz: aynı yardımcının iki tarafta durması bir yanlışı iki tarafta birden saklar.
_REJIM = {"yaz": (2026, 7, 15), "kis": (2026, 1, 15), "ara": (2026, 3, 18)}
_AY = {"Ocak": 1, "Şubat": 2, "Mart": 3, "Nisan": 4, "Mayıs": 5, "Haziran": 6, "Temmuz": 7, "Ağustos": 8,
       "Eylül": 9, "Ekim": 10, "Kasım": 11, "Aralık": 12}
_TARIH_ONCE = re.compile(rf"(?:(\d{{1,2}})\.(\d{{1,2}})\.(\d{{4}})|(\d{{1,2}}) ({'|'.join(_AY)}) (\d{{4}})"
                         rf"(?:,? [a-zçğıöşü]+)?)\s+$")
_CUMLE_SON = re.compile(r"[.!?](?=\s+[A-ZÇĞİÖŞÜ0-9*_(\[“\"]|\s*$)")


def _tsi_degerleri(saat: tuple, yer: str, gun: tuple | None, rejim: str | None) -> set[str]:
    """Yerel saatin TSİ karşılıkları: tarihliyse o günün, rejimi adıyla söylenmişse o rejimin, değilse üç rejimin."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    hh, mm, ss = saat
    gunler = [gun] if gun else ([_REJIM[rejim]] if rejim else list(_REJIM.values()))
    out = set()
    for y, a, d in gunler:
        t = datetime(y, a, d, hh, mm, ss or 0, tzinfo=ZoneInfo(_YERLER[yer])).astimezone(ZoneInfo("Europe/Istanbul"))
        out.add(t.strftime("%H:%M") + (t.strftime(":%S") if ss is not None else ""))
    return out


def _parantez_sonu(b: str) -> list[int | None]:
    """Her konum için içinde bulunduğu en içteki parantezin kapanış konumu (parantez dışındaysa None)."""
    son: list[int | None] = [None] * (len(b) + 1)
    yigin: list[int] = []
    eslesme: dict[int, int] = {}
    for i, ch in enumerate(b):
        if ch == "(":
            yigin.append(i)
        elif ch == ")" and yigin:
            eslesme[yigin.pop()] = i
    acik: list[int] = []
    for i, ch in enumerate(b):
        if ch == "(":
            acik.append(eslesme.get(i, len(b)))
        son[i] = acik[-1] if acik else None
        if ch == ")" and acik:
            acik.pop()
    return son


def _cumleler(b: str) -> list[tuple[int, int]]:
    """Cümle aralıkları; parantez içinde bölünmez."""
    out, bas, der = [], 0, 0
    for i, ch in enumerate(b):
        if ch == "(":
            der += 1
        elif ch == ")":
            der = max(0, der - 1)
        elif der == 0 and _CUMLE_SON.match(b, i):
            out.append((bas, i + 1))
            bas = i + 1
    out.append((bas, len(b)))
    return out


def _yer_bitisik(b: str, bas: int, son: int) -> str | None:
    """Saate bitişik şehir: önünde ("New York 08:30", "Londra'nın 09:00", "(Londra) 10:00", "çıkış (New York): 16:00")
    ya da ardında ("08:30 New York", "17:00'de (New York)", "16:55 ET", "15:57:30–16:02:30 Londra"). "(ABD yaz saati)"
    bir saat rejiminin adıdır, şehir değil."""
    m = re.search(rf"(?<![{_HARF}])({_YER})\)?:?{_EK}\s+$", b[max(0, bas - 30):bas])
    if m:
        return _yer_adi(m.group(1))
    m = re.match(rf"{_EK}(?:\s*[–→-]\s*{_ZAMAN_S}{_EK})?\s*\(?\s*({_YER})(?![{_HARF}])(?!\s+(?:yaz|kış) saat)",
                 b[son:son + 40])
    return _yer_adi(m.group(1)) if m else None


_REJIM_AD = (("ara", r"ara hafta|ara dönem"), ("kis", r"kışın|kış saatinde"), ("yaz", r"yazın|yaz saatinde"))


def _rejim_niteligi(metin: str, son: bool = False) -> str | None:
    """Metindeki saat rejimi niteleyicisi; birden çoksa saate en yakını (son=True: metnin sonundaki, saatten önceki
    pencere; değilse baştaki, saatten sonraki pencere)."""
    bul = [(m.start(), ad) for ad, kalip in _REJIM_AD
           for m in re.finditer(rf"(?<![{_HARF}])(?:{kalip})(?![{_HARF}])", metin)]
    if not bul:
        return None
    return (max(bul) if son else min(bul))[1]


def tsi_saatleri(b: str, tablo: bool = False, sozluk: dict | None = None,
                 figur: bool = False) -> list[tuple[int, str]]:
    """Bir metin biriminde TSİ karşılığı yazılmamış yerel saatler: [(konum, neden)].

    Bir saat TSİ'dir: "TSİ" işaretinin kapsamındaysa (işaret bir parantezin içindeyse o parantezin sonuna, değilse
    cümlenin sonuna kadar) ya da ardından "TSİ" geliyorsa ("18:00–18:15 TSİ", "00:55 TSİ'de", "(21:29 yerine 23:58
    TSİ)"); tablo başlık satırında "TSİ" geçen bir tablonun saatleri de TSİ'dir. Öbür her saat yereldir — bitişik bir
    şehri varsa işaretin kapsamında da — ve şehri bitişik şehirden, aralık ortağından, cümlede ya da birimde geçen TEK
    şehirden okunur; bulunamazsa saat "şehri belirsiz"dir. Yerel saatin TSİ karşılıkları hesaplanır (tarihliyse o
    günün, "ara hafta", "yazın", "kışın" diye nitelenmişse o rejimin, değilse yaz ve kış saatinin) ve hepsi aynı
    cümlenin TSİ saatlerinde (tabloda: tablonun ve notunun TSİ saatlerinde) bulunmalıdır. Aynı birimde karşılığı bir
    kez verilmiş saat sonraki anışlarında yeniden istenmez. Tabloda bir parametre değeri ("son giriş 10:00") aynı
    bölümün ızgara notundaki karşılığıyla da kapanır (sozluk: (etiket, saat) → notun değeri doğru mu). figur=True
    (figür başlığı): başlığın öğeleri nokta taşımaz ve satırları sarılarak bölünür; parantez dışındaki "TSİ"nin
    kapsamı öğenin bir sonraki ayracında (" · " ya da ";") biter."""
    zamanlar = [(m.start(), m.end(), (int(m.group(1)), int(m.group(2)), int(m.group(3)) if m.group(3) else None))
                for m in _ZAMAN.finditer(b)]
    if not zamanlar:
        return []
    psonu = _parantez_sonu(b)
    cum = [(0, len(b))] if tablo else _cumleler(b)

    def cumlesi(i: int) -> tuple[int, int]:
        return next(((s, e) for s, e in cum if s <= i < e), (0, len(b)))

    kapsam = []
    for m in re.finditer(r"TSİ", b):
        e = psonu[m.start()]
        if e is None:
            e = cumlesi(m.start())[1]
            if figur:
                k = re.search(r" · |;", b[m.start():e])
                e = m.start() + k.start() if k else e
        kapsam.append((m.start(), e))
    tsi_tablo = tablo and "TSİ" in b.split("\n", 1)[0]
    adlar_ = [(m.start(), m.end()) for m in _SAATLI_AD.finditer(b)]

    def tsi_mi(bas: int, son: int) -> bool:
        if _yer_bitisik(b, bas, son):
            return False
        if tsi_tablo or any(s <= bas < e for s, e in kapsam):
            return True
        if re.match(rf"{_EK}(?:\s*[–→-]\s*{_ZAMAN_S}{_EK})?\s+TSİ", b[son:son + 40]):
            return True
        e = psonu[bas]
        if e is not None:                                   # "(21:29 yerine 23:58 TSİ)"
            ic = b[son:e]
            k = ic.find("TSİ")
            if k >= 0 and "(" not in ic[:k] and not _YER_RE.search(ic[:k]):
                return True
        return False

    tsi_kume = {i: tsi_mi(s, e) for i, (s, e, _) in enumerate(zamanlar)}
    yerel = []
    for i, (s, e, sa) in enumerate(zamanlar):
        if tsi_kume[i] or any(a <= s < z for a, z in adlar_):
            continue
        yerel.append([s, e, sa, _yer_bitisik(b, s, e)])
    for a, c in zip(yerel, yerel[1:]):                          # aralığın iki ucu aynı şehrindir
        if re.fullmatch(rf"{_EK}\s*[–→-]\s*", b[a[1]:c[0]]):
            a[3] = a[3] or c[3]
            c[3] = c[3] or a[3]
    disari = [(s, e) for s, e in kapsam]

    def tek_yer(s0: int, e0: int) -> str | None:
        if s0 is None:
            return None
        yerler = {_YERLER[_yer_adi(m.group(1))] for m in _YER_RE.finditer(b, s0, e0)
                  if not any(s <= m.start() < e for s, e in disari)}
        if len(yerler) == 1:
            z = yerler.pop()
            return next(k for k, v in _YERLER.items() if v == z)
        return None

    def paranteze(i: int) -> tuple[int | None, int | None]:
        e = psonu[i]
        if e is None:
            return None, None
        der, k = 0, i
        while k > 0:
            k -= 1
            if b[k] == ")":
                der += 1
            elif b[k] == "(":
                if der == 0:
                    return k, e
                der -= 1
        return None, None

    out = []
    verilen: set = set()            # birimde TSİ karşılığı verilmiş (şehir, saat, gün, rejim): sonraki anışlar kapanır
    for s, e, sa, yer in yerel:
        if sozluk:
            etiketler = [m.group(1) for m in [re.search(r"([a-zçğıöşü]+(?: [a-zçğıöşü]+)?) $", b[max(0, s - 20):s])] if m]
            satir = b[b.rfind("\n", 0, s) + 1:]
            ilk = re.match(rf"\|\s*\**([a-zçğıöşü ]+?)(?: \((?:{_YER})\))?\**\s*\|", satir.lower()
                           .replace("i̇", "i"))
            if ilk:
                etiketler.append(ilk.group(1).strip())
            if any(sozluk.get((et, b[s:e])) for et in etiketler):
                continue
        cs, ce = cumlesi(s)
        ps, pe = paranteze(s)
        yer = yer or tek_yer(ps, pe) or tek_yer(cs, ce) or tek_yer(0, len(b))
        if not yer:
            out.append((s, "şehri belirsiz"))
            continue
        mt = _TARIH_ONCE.search(b[max(0, s - 40):s])
        gun = None
        if mt:
            gun = ((int(mt.group(3)), int(mt.group(2)), int(mt.group(1))) if mt.group(1)
                   else (int(mt.group(6)), _AY[mt.group(5)], int(mt.group(4))))
        # Saatten sonraki niteleyici yalnız saatin kendi yan cümlesinde aranır: "(New York 16:00), yazın …" ikinci
        # yan cümlenin niteleyicisidir.
        nit = re.split(r"TSİ|[,;()]", b[e:e + 40], maxsplit=1)[0]
        # Rejim niteleyicisi TSİ'nin kendi yazımından okunmaz ("(TSİ ABD yaz saatinde 15:30, kış saatinde 16:30)
        # 08:00–09:00" kış saati demek değildir): saatten önceki pencerede TSİ kapsamı boşlukla örtülür.
        o0 = max(cs, s - 40)
        once = "".join(" " if any(a <= i < z for a, z in kapsam) else b[i] for i in range(o0, s))
        rejim = _rejim_niteligi(nit) or _rejim_niteligi(once, son=True)
        anahtar = (_YERLER[yer], b[s:e], gun, rejim)
        if anahtar in verilen:
            continue
        bek = _tsi_degerleri(sa, yer, gun, rejim)
        var = {b[zs:ze] for j, (zs, ze, _) in enumerate(zamanlar) if tsi_kume[j] and cs <= zs < ce}
        eksik = bek - var
        if eksik:
            out.append((s, f"{yer} {b[s:e]} → TSİ {' · '.join(sorted(bek))} yazılı değil"))
        else:
            verilen.add(anahtar)
    return out


_LEJANT = re.compile(rf"([a-zçğıöşü]+(?: [a-zçğıöşü]+)?) \(({_YER})\) ({_ZAMAN_S}) → (TSİ [^;_]+)")


def _tsi_birimleri(mdx: str):
    """Ölçüt 15'in birimleri, satır numarasıyla: (satır, tür, metin, bölüm). Tür "metin" (paragraf, madde, başlık, ön
    bilginin okura giden alanları, figür başlığı) ya da "tablo" (tablo ve hemen ardından gelen italik notu); bölüm,
    birimin içinde durduğu ikinci düzey başlıktır (ızgara notu yalnız kendi bölümünün tablolarını kapar)."""
    satir = mdx.split("\n")
    i, bolum = 0, ""
    if mdx.startswith("---\n"):
        j = satir.index("---", 1)
        for k in range(1, j):
            m = re.match(r"(title|description|ozet):\s*['\"]?(.*?)['\"]?\s*$", satir[k])
            if m:
                yield k + 1, "metin", m.group(2), bolum
        i = j + 1
    while i < len(satir):
        s = satir[i]
        if not s.strip() or s.startswith("import "):
            i += 1
            continue
        if s.lstrip().startswith("|"):
            j = i
            while j < len(satir) and satir[j].lstrip().startswith("|"):
                j += 1
            k = j
            while k < len(satir) and not satir[k].strip():
                k += 1
            not_ = []
            if k < len(satir) and satir[k].lstrip().startswith("_"):
                while k < len(satir) and satir[k].strip():
                    not_.append(satir[k])
                    k += 1
            yield i + 1, "tablo", "\n".join(satir[i:j] + ([""] + not_ if not_ else [])), bolum
            if not_:
                yield j + 2, "metin", " ".join(not_), bolum
            i = k if not_ else j
            continue
        if s.startswith("#"):
            if s.startswith("## "):
                bolum = s[3:].strip()
            yield i + 1, "metin", s.lstrip("#").strip(), bolum
            i += 1
            continue
        if s.lstrip().startswith("<"):
            for m in re.finditer(r'\bbaslik="([^"]*)"', s):
                yield i + 1, "metin", m.group(1), bolum
            m = re.search(r"<summary>(.*?)</summary>", s)
            if m:
                yield i + 1, "metin", m.group(1), bolum
            i += 1
            continue
        cur, j = [s], i + 1
        while j < len(satir) and satir[j].strip() and not re.match(r"\s*(?:[-*] |\d+\. |\||#|<)", satir[j]):
            cur.append(satir[j])
            j += 1
        yield i + 1, "metin", "\n".join(cur), bolum
        i = j


def _lejant(mdx: str) -> dict:
    """Izgara notlarının parametre sözlüğü, bölüm bölüm: {bölüm: {(etiket, saat): doğru mu}} ("son giriş (Londra)
    10:00 → TSİ yazın 12:00, kışın 13:00"). Notun kendi değeri yanlışsa girdi kapatmaz."""
    out: dict = {}
    for _, tur, b, bolum in _tsi_birimleri(mdx):
        for m in _LEJANT.finditer(b):
            hh, mm, *ss = (int(x) for x in m.group(3).split(":"))
            bek = _tsi_degerleri((hh, mm, ss[0] if ss else None), _yer_adi(m.group(2)), None, None)
            var = {x.group(0) for x in _ZAMAN.finditer(m.group(4))}
            out.setdefault(bolum, {})[(m.group(1), m.group(3))] = bek <= var
    return out


def tsi_metinde(cikti: dict) -> list[str]:
    """Ölçüt 15: üretilmiş metinde her yerel saatin TSİ karşılığı (tsi_saatleri)."""
    hata = []
    for slug, (mdx, _) in cikti.items():
        lej = _lejant(mdx)
        for bas, tur, b, bolum in _tsi_birimleri(mdx):
            sozluk = lej.get(bolum, {}) if tur == "tablo" else None
            tablo_sonu = b.find("\n\n_") if tur == "tablo" else -1
            for k, neden in tsi_saatleri(b, tablo=tur == "tablo", sozluk=sozluk):
                if tablo_sonu >= 0 and k > tablo_sonu:
                    continue                                  # not ayrıca metin olarak sınanır
                satir = bas + b.count("\n", 0, k)
                hata.append(f"{slug}.mdx:{satir}: {neden}: …{b[max(0, k - 50):k + 30].replace(chr(10), ' ')}…")
    return hata


def tsi_figurde(ad: str, d: dict) -> list[str]:
    """Ölçüt 15, figür yarısı: figürün başlık bloğundaki ve üstündeki notlardaki yerel saatler (tsi_saatleri)."""
    import html
    metinler = [((d.get("layout") or {}).get("title") or {}).get("text") or ""]
    metinler += [a.get("text") or "" for a in (d.get("layout") or {}).get("annotations") or []]
    hata = []
    for t in metinler:
        duz = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<br\s*/?>", " ", t)))
        duz = re.sub(r"\s+", " ", duz).strip()
        for k, neden in tsi_saatleri(duz, figur=True):
            hata.append(f"{ad}.html: {neden}: …{duz[max(0, k - 50):k + 30]}…")
    return hata


_BLOK_ETIKET = re.compile(r"^\s*<(details|div)\b[^>]*>(.*)$")


def mdx_yapisi(slug: str, mdx: str) -> list[str]:
    """Ölçüt 11: kapanışı aynı satırda olmayan bir blok etiketi satırında başka metin yoktur."""
    hata = []
    for i, s in enumerate(mdx.split("\n"), 1):
        m = _BLOK_ETIKET.match(s)
        if m and m.group(2).strip() and f"</{m.group(1)}>" not in s:
            hata.append(f"{slug}.mdx:{i}: blok etiketi kendi satırında değil (MDX derlemesi düşer): {s.strip()[:80]}")
    return hata


def sira_denetimi() -> list[str]:
    hata = []
    if not GRUP_TS.exists():
        return [f"ders grubu dosyası yok: {GRUP_TS}"]
    ts = GRUP_TS.read_text(encoding="utf-8")
    m = re.search(r"id:\s*'fx-gunici'.*?slugSirasi:\s*\[(.*?)\]", ts, flags=re.S)
    if not m:
        return ["sitedeki ders gruplarında 'fx-gunici' grubu ya da sırası yok"]
    ts_sira = re.findall(r"'([^']+)'", m.group(1))
    if ts_sira != adlar.DERS_SIRA:
        hata.append(f"ders sırası ayrışıyor: site {ts_sira} ↔ seri {adlar.DERS_SIRA}")
    for slug in adlar.DERS_SIRA:
        sablon = (BURASI / "metin" / f"{slug}.md").read_text(encoding="utf-8")
        on = re.search(r"\nonkosul:\n((?:\s+- .+\n)+)", sablon)
        for s in (re.findall(r"- (\S+)", on.group(1)) if on else []):
            if s not in adlar.DERS_SIRA:
                hata.append(f"{slug}: ön koşul seride değil: {s}")
            elif adlar.DERS_SIRA.index(s) >= adlar.DERS_SIRA.index(slug):
                hata.append(f"{slug}: ön koşul kendisinden sonra geliyor: {s}")
    return hata


def main() -> int:
    hata: list[str] = []
    var = [s for s in adlar.DERS_SIRA if (dy.ICERIK / f"{s}.mdx").exists()]
    hata += sayi_envanteri()
    hata += tsi_denetimi()
    hata += sira_denetimi()
    hata += kunye_denetimi()
    hata += kova_sirasi()
    hata += onkayit_denetimi()
    hata += olcum_kodu()
    if not var:
        if hata:
            print("✗ FX gün içi: " + "\n  ".join(hata))
            return 1
        print("✓ FX gün içi: dersler henüz sitede değil; şablon ve sıra ölçütleri geçti, yeniden üretim sınanmadı")
        return 0
    if len(var) != len(adlar.DERS_SIRA):
        hata.append(f"serinin bir kısmı sitede: {len(var)} / {len(adlar.DERS_SIRA)}")
    if not dy.OLCUM.exists():
        hata.append(f"ölçüm dosyası yok: {dy.OLCUM.relative_to(dy.KOK)}")
    else:
        try:
            cikti = dy.uret()
        except Exception as e:                        # şablon iddiası tutmadı, yer tutucu ölçülemedi …
            cikti = {}
            hata.append(f"üretim düştü: {type(e).__name__}: {e}")
        oz = hashlib.sha256(dy.OLCUM.read_bytes()).hexdigest()
        kod_oz, kod_hata = sekil_kodu()
        hata += kod_hata
        hata += parite_denetimi(cikti) + ornek_esigi(cikti) + tsi_metinde(cikti) + atr_denetimi(cikti)
        hata += atif.denetim({slug: mdx for slug, (mdx, _) in cikti.items()})
        gomulen = set()
        for slug, (mdx, u) in cikti.items():
            hata += mdx_yapisi(slug, mdx)
            yol = dy.ICERIK / f"{slug}.mdx"
            if yol.exists() and yol.read_text(encoding="utf-8") != mdx:
                hata.append(f"{slug}: sitedeki metin ölçümden yeniden üretilen metinle aynı değil")
            for ad in u.sekiller:
                gomulen.add(f"{ad}.html")
                f = dy.SEKIL / f"{ad}.html"
                if not f.exists():
                    hata.append(f"{slug}: gömülen figür yok: {ad}.html")
                    continue
                h = f.read_text(encoding="utf-8")
                m = re.search(r'<meta name="tto-olcum-ozu" content="([0-9a-f]{64})">', h)
                if not m:
                    hata.append(f"{ad}.html: ölçüm özü yok")
                elif m.group(1) != oz:
                    hata.append(f"{ad}.html: başka bir ölçümle çizilmiş (yeniden çizilmeli)")
                m = re.search(r'<meta name="tto-kod-ozu" content="([0-9a-f]{64})">', h)
                if not m:
                    hata.append(f"{ad}.html: kod özü yok (yeniden çizilmeli)")
                elif m.group(1) != kod_oz:
                    hata.append(f"{ad}.html: figür kodu değişti, figür yeniden çizilmedi (yeniden çizilmeli)")
                for js in re.findall(r'<script[^>]*\bsrc="(/[^"]+)"', h):
                    if not (dy.KOK / "site" / "public" / js.lstrip("/")).exists():
                        hata.append(f"{ad}.html: çağırdığı dosya sitede yok: {js}")
                hata += figur_bicimi(ad, h)
        if cikti:
            fazla = sorted(p.name for p in dy.SEKIL.glob("*.html") if p.name not in gomulen)
            if fazla:
                hata.append(f"hiçbir derste gömülmeyen figür: {', '.join(fazla)}")
    kopya = dy.SEKIL / "onkayit.toml"
    if not kopya.exists() or kopya.read_bytes() != dy.ONKAYIT.read_bytes():
        hata.append("ön kaydın yayımlanan kopyası kaynakla aynı değil")
    if hata:
        print("✗ FX gün içi:\n  " + "\n  ".join(hata))
        return 1
    print(f"✓ FX gün içi: {len(adlar.DERS_SIRA)} ders ölçümden birebir üretiliyor; figürler, sayılar, sıra, ön kayıt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
