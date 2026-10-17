#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FX gün içi ders serisinin kapısı (sayfa sınavı 26 bu dosyayı kendiliğinden koşturur).

Yalnız standart kütüphane: yayın koşucusunda pandas, numba ya da plotly yok ve bu kapı onlara ihtiyaç duymaz. Girdisi
depodaki ölçüm dosyasıdır (cikti/ders/olcum.json); ağa çıkmaz, duvar saati okumaz.

Ölçütler:
  1. Yeniden üretim — sekiz ders ölçüm dosyasından ve şablonlardan yeniden üretilir ve sitedeki MDX'le BİREBİR
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
     söyleyen sözcük ("dört paritede", "dört majör") künyenin parite sayısıdır ("en az", "bu", "öbür" ile başlayan
     alt küme sayımları hariç). Parite listesi değişince eski sayıyı taşıyan cümleler adıyla düşer.
  14. Örnek eşiği — metin "yarım R" diyorsa örnek günlerin eşiği (künye.ornek.esik) 0,5'tir.
  15. TSİ, üretilmiş metinde — bir yerel saat (Londra, New York, Frankfurt, Tokyo) taşıyan her paragraf ve her madde
     TSİ karşılığını da taşır (tablolar hariç: parametre tablolarının saatleri dipnotta TSİ'siyle). Giriş dersinin
     "bütün saatler ayrıca TSİ olarak yazılır" cümlesi bu ölçütün sözüdür.

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
import ders_yaz as dy  # noqa: E402

GRUP_TS = dy.KOK / "site" / "src" / "lib" / "dersGruplari.ts"

#: Tanım gereği sabit olan sayılar (ölçüm değil): aralık ve sınama düzeyleri (%95, %5, 0,95), pip büyüklükleri
#: (0,0001 · 0,01), olasılık tanımları (%50 yazı tura; %30 ve %70 isabet örneği). Buraya bir ÖLÇÜM yazılamaz; bir
#: kodun sabiti de yazılamaz — örnek gün eşiği, temel kayma ve veri denetiminin kapsam eşikleri künyeden basılır.
TANIM = {"%95", "%5", "%50", "%30", "%70", "0,0001", "0,01", "0,95"}

#: Ölçüt 12'nin asgari kapsamları (kapının kendi kümesi; sınanan listeler bunları taşımalı).
OLCUM_KODU_ASGARI = {"ders_olcum.py", "adlar.py", "kosu.py", "motor.py", "strateji.py", "strat_haber.py", "takvim.py",
                     "metrik.py", "saglamlik.py"}
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
    return hata


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
_PARITE_SAYI = re.compile(r"(?<![\wçğıöşüÇĞİÖŞÜ])((?:en az|bu|öbür) )?(iki|üç|dört|beş|altı|yedi|sekiz|dokuz|on) "
                          r"(?:majör )?parite", re.I)


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


def ornek_esigi(cikti: dict) -> list[str]:
    """Ölçüt 14: "yarım R" diyen metin, örnek günlerin eşiği 0,5 iken doğrudur."""
    if not dy.OLCUM.exists():
        return []
    esik = ((json.loads(dy.OLCUM.read_text(encoding="utf-8")).get("kunye") or {}).get("ornek") or {}).get("esik")
    yarim = sorted(slug for slug, (mdx, _) in cikti.items() if "yarım R" in mdx)
    if yarim and esik != 0.5:
        return [f"metin 'yarım R' diyor ({', '.join(yarim)}), örnek günlerin eşiği {esik}"]
    return []


_SAAT_S = r"(?:[01]\d|2[0-3]):[0-5]\d(?:\s*[–→-]\s*(?:[01]\d|2[0-3]):[0-5]\d)?"
_SEHIR = r"(?:New York|Londra|Frankfurt|Tokyo)"
_YEREL_SAAT = re.compile(rf"(?:{_SAAT_S}\s*{_SEHIR}|{_SEHIR}(?:'[a-zçğıöşü]+)?\s+{_SAAT_S})")


def _metin_birimleri(mdx: str):
    """Paragraflar ve maddeler (madde imiyle başlayan satır yeni birimdir), satır numarasıyla; tablo, başlık ve blok
    etiketi satırları ayrı birimdir ve sınanmaz. Başlık ve etiket satırı TEK satırlık birimdir: ardından boş satırsız
    gelen metin kendi birimidir ve sınanır (etiketin birimine katılsaydı etiketle birlikte sınamanın dışında kalırdı).
    Tablonun ardından boş satırsız gelen satır tablonun satırıdır (GFM) ve tabloyla kalır."""
    cur, bas = [], 1
    for i, sat in enumerate(mdx.split("\n"), 1):
        yeni = (not sat.strip()) or bool(re.match(r"\s*(?:[-*] |\d+\. |\||#|<)", sat))
        if yeni and cur:
            yield bas, "\n".join(cur)
            cur = []
        if sat.strip():
            if not cur:
                bas = i
            cur.append(sat)
            if re.match(r"\s*[#<]", sat):
                yield bas, sat
                cur = []
    if cur:
        yield bas, "\n".join(cur)


def tsi_metinde(cikti: dict) -> list[str]:
    """Ölçüt 15: yerel saat taşıyan her paragraf ve madde TSİ karşılığını da taşır (üretilmiş metinde)."""
    hata = []
    for slug, (mdx, _) in cikti.items():
        for bas, b in _metin_birimleri(mdx):
            if b.lstrip().startswith(("|", "<", "#", "{", "import")):
                continue
            m = _YEREL_SAAT.search(b)
            if m and "TSİ" not in b:
                hata.append(f"{slug}.mdx:{bas}: yerel saat var, TSİ karşılığı yok: …{b[max(0, m.start() - 40):m.end() + 30]}…")
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
        hata += parite_denetimi(cikti) + ornek_esigi(cikti) + tsi_metinde(cikti)
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
