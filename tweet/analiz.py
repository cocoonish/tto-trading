#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analiz yazısından X gönderisi — yönetici özetinden, deterministik.

Analizler X'e şimdiye dek elle yazılan metinlerle (tweet/ozel/*.txt) çıktı;
her yazı için bir insan oturup özet yazdı ve iş akışını elle tetikledi. Bu
modül aynı işi ARAÇLA yapar: yazının kendi yönetici özetini (tez, soru–cevap
tablosu, altı anahtar ölçüm) alır ve gönderi metnine çevirir. Yeni hüküm
ÜRETMEZ — cümleler yazının kendi cümleleri, sayılar yazının kendi sayılarıdır.

Sayılar SABİTTİR (karar 08.09.2026): analiz yayımlandığı günün metnidir, yalnız
panolar canlıdır. Yazıdaki her <Deger …>yedek</Deger> etiketi sayfada nasıl
basılıyorsa (yedek metniyle) gönderiye de öyle girer; ozet.json OKUNMAZ.
Gönderi ile sayfa aynı sayıyı söyler — iki kaynak bir gün sessizce ayrışmaz.

Ağa çıkmaz; duman sınaması gerçek yazılarla çağırır.
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent
ANALIZ_DIZIN = KOK / "site" / "src" / "content" / "analiz"
OZET_DIZIN = KOK / "site" / "public" / "projeler"

import uret  # tek tavan, tek kırpma, tek tipografi

TEZ_SINIR = 900            # tez paragrafı
SATIR_SINIR = 420          # tablo satırı başına
RAKAM_SINIR = 700          # rakam şeridi
GOVDE_SINIR = uret.TEK_TAVAN
# Gönderimi durdurmayan ama kayda düşmesi gereken bulgular (gonder.py ::warning:: basar).
UYARILAR: list[str] = []
_kirp = uret._kirp

# Yönetici özeti sayfa mobilyasına atıf yapabilir; tweet kendi başına durur.
IZLER = ("bu yazı", "yazının", "yazıda", "yukarıdaki", "aşağıdaki", "bölümünde",
         "bu sayfa", "sayfadaki", "grafikte", "tabloda", "sitede")
# Sol sözcük sınırı üreticinin tek tanımından (uret.SOL_SINIR): ham alt dize
# araması "kapasitede"nin içinde "sitede" buluyordu — bülten tarafında
# 22.09.2026'da kapatılan kusurun analiz eşi. Sağ tarafa sınır konmaz (ekli
# yazım "yazının", "tabloda" yakalanmak istenen biçimdir).
_IZ_RE = re.compile(uret.SOL_SINIR + r"(?:" + "|".join(re.escape(i) for i in IZLER) + ")")


# ── ön bilgi ─────────────────────────────────────────────────────────────────
# Tek ayrıştırıcı: ortak/on_bilgi.py (analiz kapısıyla aynı).
import sys as _sys
_sys.path.insert(0, str(KOK / "ortak"))
import on_bilgi as _on_bilgi  # noqa: E402

on_bilgi = _on_bilgi.ayristir


def analizi_oku(yol: Path) -> dict:
    metin = yol.read_text(encoding="utf-8")
    fm = _on_bilgi.ayristir(metin)
    return {"slug": yol.stem, "yol": yol, "govde": _on_bilgi.govde(metin), **fm}


def analizler(dizin: Path | None = None) -> list[dict]:
    return [analizi_oku(y) for y in sorted((dizin or ANALIZ_DIZIN).glob("*.mdx"))]


# ── sayı çözümü (<Deger>) — SABİT ────────────────────────────────────────────
#
# Eskiden buradan ozet.json okunup değer canlı çözülüyordu. Analiz artık sabit
# (karar 08.09.2026, bkz. modül başlığı): sayfanın gösterdiği şey etiketin
# yedek metnidir, gönderi de onu taşır. `_OZET_ONBELLEK` geriye uyumluluk için
# duruyor (duman sınaması temizliyor); hiçbir şey ona yazmaz.

_OZET_ONBELLEK: dict[str, dict] = {}

_DEGER = re.compile(r"<Deger\s+([^>]*?)>(.*?)</Deger>", re.S)


def degerleri_coz(html: str, ozet_dizin: Path | None = None) -> str:
    """<Deger …>yedek</Deger> → yedek metin (sayfadaki sabit sayı). `ozet_dizin`
    geriye uyumluluk için alınır ve KULLANILMAZ — canlı çözüm yok."""
    return _DEGER.sub(lambda m: m.group(2), html)


# ── yönetici özeti ───────────────────────────────────────────────────────────

def _duz(html: str) -> str:
    m = re.sub(r"<[^>]+>", " ", html or "")
    m = (m.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<")
          .replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'"))
    m = re.sub(r"\{/\*.*?\*/\}", " ", m, flags=re.S)
    m = re.sub(r"\s+", " ", m).strip()
    # "% 1,48" → "%1,48": etiket sökümü yüzde ile sayı arasına boşluk bırakır
    m = re.sub(r"%\s+(?=[\d−+])", "%", m)
    m = re.sub(r"\s+([,.;:)])", r"\1", m)
    m = re.sub(r"\(\s+", "(", m)
    return m


def yonetici_ozeti(govde: str) -> dict | None:
    m = re.search(r'<div class="yonetici">(.*?)\n</div>', govde, re.S)
    if not m:
        return None
    blok = degerleri_coz(m.group(1))
    tez_m = re.search(r'<p class="tez">(.*?)</p>', blok, re.S)
    tez = _duz(tez_m.group(1)) if tez_m else ""
    satirlar: list[tuple[str, str]] = []
    for tr in re.findall(r"<tr>(.*?)</tr>", blok, re.S):
        hucreler = re.findall(r"<td>(.*?)</td>", tr, re.S)
        if len(hucreler) >= 2:
            satirlar.append((_duz(hucreler[0]), _duz(hucreler[1])))
    rakamlar: list[tuple[str, str]] = []
    rk = re.search(r'<ul class="rakamlar">(.*?)</ul>', blok, re.S)
    if rk:
        for li in re.findall(r"<li>(.*?)</li>", rk.group(1), re.S):
            # Sözleşme <li><b>değer</b><span>etiket</span></li>; eski bir yazı
            # span'ı atlayıp etiketi <b>'den sonra düz metin yazmış olabilir —
            # o durumda <b>'den sonrası etiket sayılır (rehber sonrası yazılarda
            # kapı tam işaretlemeyi zorunlu kılar).
            b = re.search(r"<b>(.*?)</b>", li, re.S)
            if not b:
                continue
            sp = re.search(r"<span>(.*?)</span>", li, re.S)
            etiket = _duz(sp.group(1)) if sp else _duz(li[b.end():])
            if etiket:
                rakamlar.append((_duz(b.group(1)), etiket))
    return {"tez": tez, "satirlar": satirlar, "rakamlar": rakamlar}


# ── gönderi metni ────────────────────────────────────────────────────────────

def _site_disi(metin: str) -> str:
    """Sayfa mobilyasına atıf yapan cümleleri düşür; düşenler uret.DUSEN'e yazılır.
    Cümle sınırı üreticinin TEK tanımıdır (`uret.cumleler`): analizin kendi
    bölücüsü rakamla biten cümleyi ve parantez içi noktayı ayrı kurallarla
    okuyordu — iki bölücü bir gün aynı metni iki ayrı biçimde keser."""
    kalan = []
    for c in uret.cumleler(metin):
        if _IZ_RE.search(uret._kucuk(c)) or uret._site_izi_var(c):
            uret.DUSEN.append(("analiz", c.strip()))
            continue
        kalan.append(c.strip())
    return " ".join(kalan)


# ── soru başlıkları: cümle düzeni (05.10.2026, şartname A8) ─────────────────
#
# Tablonun soru sütunu eskiden Türkçe büyük harfle basılıyordu ("KANITIN
# GÜCÜ."): arşivdeki sekiz gönderide 58 büyük harfli başlık, gönderi başına
# 6–9 — zaman akışında bağırma gibi okunur. Başlık artık kaynaktaki cümle
# düzeninde kalır. Soru işareti YALNIZ soru biçimindeki başlığa konur: soru
# eki (mi/mı/mu/mü) ya da soru sözcüğü taşıyan başlık. 61 başlığın 17'si soru
# değil ("Kanıtın gücü", "Faize etkisi", "Katalizörler"); kör bir "?" kuralı
# "Kanıtın gücü? Orta." üretirdi. İsim öbeği başlık bültenin düzeniyle iki
# noktayla yazılır: "Kanıtın gücü: Orta. …".
_SORU_EKI = re.compile(r"\bm[iıuü](?:[dt][iıuü]r|s[iıuü]n(?:[iıuü]z)?|y[iıuü]z)?\b")
# Şartnamenin listesi (ne · nerede · nereye · nereden · neden · nasıl · kaça ·
# kadar) ve aynı sınıfın eksik kalan dört sözcüğü (hangi · kaç · kim · niçin ·
# niye): "Hangi kural" bir sorudur ve iki noktayla basılırsa isim öbeği gibi okunur.
_SORU_SOZCUGU = re.compile(
    r"\b(?:ne|nerede|nereye|nereden|neden|nasıl|kaça|kaç|kadar|hangi|kim|niçin|niye)\b", re.I)


def soru_mu(baslik: str) -> bool:
    b = (baslik or "").strip()
    return b.endswith("?") or bool(_SORU_EKI.search(b) or _SORU_SOZCUGU.search(b))


def baslikli_satir(soru: str, cevap: str) -> str:
    """Tablo satırı → gönderi satırı: 'Gelir mi? Evet, …' · 'Kanıtın gücü: Orta. …'."""
    s = (soru or "").strip().rstrip(".?!:").strip()
    return f"{s}{'?' if soru_mu(soru) else ':'} {cevap}"


# ── rakam şeridi: yalnız metinde GEÇMEYEN ölçümler, değer önde ──────────────
#
# Arşivdeki sekiz gönderide şerit değerlerinin 56/63'ü (%88,9) aynı gönderide
# zaten geçiyordu; Hürmüz'de −%95,3 dört kez basıldı. Şerit artık yalnız tez ve
# satırlarda GEÇMEYEN ölçümleri taşır; hiçbiri kalmazsa satır basılmaz (boş
# "Kilit ölçümler:" etiketi kapıda ENGEL'dir). Sonuç adıyla: şerit, metinde
# geçmeyen ölçüm kalmayan yazıda kalkar (05.10.2026: yönetici özetli 12 yazının
# 3'ü) — 17.09.2026'daki "şerit korunur" niyeti bilerek değişti; korunan şey
# artık şerit değil, gönderide BAŞKA YERDE OLMAYAN ölçümdür.
#
# "Geçiyor mu" sorusu SAYININ kendisiyle sorulur, tek tanımdan: ondalıklı sayı
# `uret.OLGU_SAYI`, birimli tam sayı `uret.OLCU_TAMSAYI` (aynı-sayı ölçüsünün
# kalıpları). İşaret sayının parçasıdır ("−22,1" ile "22,1" aynı ölçüm
# değildir). Sayısı kalıba girmeyen ama birim ya da ayraç taşıyan değer ("34
# gün", "6/7") metinde birebir aranır; çıplak tam sayı ("3") tarihlerle
# çakışacağı için aranmaz ve şeritte kalır.
#
# Değer ÖNDE ve uzun tireyle yazılır (sayfa da değeri üstte basar). Bileşik kalemde ("%10,76 ·
# %4,17" | "reel faiz: ankete göre · gerçekleşene göre") değer ve etiket aynı
# sayıda " · " taşıyorsa ikili ikili eşlenir; kalem ayracı "; " — iç ayraçla
# aynı olsaydı "%4,17" yanlış etiketin yanına düşerdi (PPK kararı gönderisi).
# Bölünemeyen bileşik kalem atlanır. Etiket KIRPILMAZ: kalem ya tam basılır ya
# hiç — kısaltma küme sayısı, eşik ve ölçü saati gibi çekinceleri düşürür.
#
# DEĞER İLE ETİKET ARASINDA UZUN TİRE (05.10.2026 incelemesi). Sayfa değeri
# ayrı satırda, kalın ve eş aralıklı basar; gönderide yalnız bir boşluk vardı
# ve etiketi rakamla ya da zaman sözcüğüyle başlayan kalem değere yapışıyordu:
# "%13,7 bir ayda …" (bir ayda %13,7 diye okunur; sayı gözlemlerin payı), "4 /
# 30 temmuz özetiyle …" (tarih gibi), "9,9 puan 2 yıl – 9 yıl" (aralık gibi).
# Değer ÖNDE kalır (A8). Virgül (ondalıkla çakışır), iki nokta (3 etikette
# geçiyor) ve parantez (14 etikette) ayraç olamaz; etiketin içinde " — " geçse
# de değerin hemen ardındaki ilk tire ayraç olarak okunur. Ölçüldü: 13 analizde
# ENGEL 0 → 0, UYARI aynı, gönderiler 2–8 karakter uzuyor.
SERIT_AYRAC = "—"

def _isaret(m: str, i: int) -> str:
    """Sayının işareti: hemen önündeki eksi (U+2212 ya da kelime/sayı ardı
    olmayan ASCII tire). "%−3,41" ve "−%3,28" ikisi de eksidir."""
    j = i
    if j > 0 and m[j - 1] == "%":
        j -= 1
    if j > 0 and m[j - 1] == "−":
        return "−"
    if j > 0 and m[j - 1] == "-" and not (j > 1 and m[j - 2].isalnum()):
        return "−"
    return "+"


def olcu_imleri(metin: str) -> set[tuple[str, str]]:
    # Birim çekim eki alır ("207 baz puanın", "40 puanlık"); `OLCU_TAMSAYI`
    # birimin ardında sözcük sınırı istediği için ekli yazımı ölçüm saymaz ve
    # aynı ölçüm şeritte ikinci kez basılırdı (PPK kararı: "+207 bp" ile "207
    # baz puanın"). Kalıp değiştirilmez; girdi eksiz birime indirgenir.
    m = re.sub(r"\b(bp|puan)[^\W\d_]+", r"\1", (metin or "").replace("baz puan", "bp"))
    out: set[tuple[str, str]] = set()
    kapsanan: list[tuple[int, int]] = []
    for r in uret.OLGU_SAYI.finditer(m):
        out.add((_isaret(m, r.start()), r.group(0).strip("%")))
        kapsanan.append(r.span())
    for r in uret.OLCU_TAMSAYI.finditer(m):
        if any(a <= r.start() < z for a, z in kapsanan):
            continue                 # "%37,0"ın içindeki "%37" ayrı ölçüm değildir
        g = re.sub(r"\s+", " ", r.group(0)).replace("baz puan", "bp")
        out.add((_isaret(m, r.start()), g))
    return out


def _metinde(deger: str, metin: str, imler: set[tuple[str, str]]) -> bool:
    d = (deger or "").strip()
    di = olcu_imleri(d)
    if di:
        return di <= imler
    if re.search(r"[^\W\d_]|/", d):
        return bool(re.search(r"(?<![\w,.%+−-])" + re.escape(d) + r"(?![\w]|[,.]\d)", metin))
    return False


def serit_kalemleri(rakamlar: list[tuple[str, str]], metin: str) -> tuple[list[str], list[str]]:
    """(şeride girecek kalemler — değer önde, uzun tireyle, metinde geçmeyenler, sıra
    korunur; eşlenemediği için atlanan bileşik kalemler)."""
    imler = olcu_imleri(metin)
    out, atlanan = [], []
    for deger, etiket in rakamlar:
        if not (deger and etiket):
            continue
        dp, ep = deger.split(" · "), etiket.split(" · ")
        if len(dp) > 1 and len(dp) != len(ep):
            atlanan.append(f"bileşik kalem eşlenemedi: {deger} | {etiket}")
            continue
        ciftler = list(zip(dp, ep)) if len(dp) > 1 else [(deger, etiket)]
        if all(_metinde(d, metin, imler) for d, _ in ciftler):
            continue                 # bütün parçaları metinde: tekrar
        out.append(" · ".join(f"{d.strip()} {SERIT_AYRAC} {e.strip()}" for d, e in ciftler))
    return out, atlanan


def serit(rakamlar: list[tuple[str, str]], metin: str, sinir: int) -> tuple[str, list[str]]:
    """('Kilit ölçümler: …' satırı ya da "" — boşsa satır basılmaz, düşen
    kalemler). Sınıra sığmayan kalem BÜTÜNÜYLE atlanır. Kayıt çağırana
    bırakılır: tavan döngüsü şeridi her adımda yeniden kurar ve ara adımların
    düşüşleri gerçek bir düşüş değildir."""
    kalemler, dusen = serit_kalemleri(rakamlar, metin)
    secilen: list[str] = []
    for k in kalemler:
        aday = secilen + [k]
        if len(_serit_metni(aday)) > sinir:
            dusen.append(k)
            continue
        secilen = aday
    return (_serit_metni(secilen) if secilen else ""), dusen


def _serit_metni(kalemler: list[str]) -> str:
    return ("Kilit ölçüm: " if len(kalemler) == 1 else "Kilit ölçümler: ") + "; ".join(kalemler)




_TARIH_ONEKI = re.compile(r"^\s*(\d{1,2}\s+(?:Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)\s+\d{4})\s+")


def _baslik(a: dict) -> list[str]:
    """İlk satır bültenle aynı aileden: 'Analiz — 1 Eylül 2026'; ikinci satır
    yazının başlığı (tarih öneki soyulur — ilk satırda zaten var)."""
    title = str(a.get("title") or a["slug"])
    m = _TARIH_ONEKI.match(title)
    if m:
        tarih, govde = m.group(1), title[m.end():]
    else:
        pub = str(a.get("pubDate") or "")[:10]
        try:
            y, ay, g = pub.split("-")
            tarih = f"{int(g)} {AYLAR_TR[int(ay)]} {y}"
        except Exception:                                      # noqa: BLE001
            tarih = pub
        govde = title
    return [f"Analiz — {tarih}", govde.strip()]


AYLAR_TR = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
            "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]


# TEZİN İLK CÜMLESİ ÖLÇÜM TAŞIR (analiz/YAZIM.md). Zaman akışında görünen ilk
# ~280 karakter başlık ve tezin açılışıdır; açılış sayısızsa ("Karar
# sürprizsiz, metin ise tek yönlü değil.") okur gönderinin ölçüm taşıdığını
# görmeden geçer. Kural yazara konur — araç cümle sırasını DEĞİŞTİRMEZ (yeni
# hüküm üretmez) — ve burada UYARI olarak sorulur: gonder.py ::warning:: basar.
def tez_acilisi_olcu_tasir(tez: str) -> bool:
    c = uret.cumleler(tez)
    return bool(c) and bool(uret._sayilar(c[0]))


def _tez_ham(a: dict, yo: dict | None) -> str:
    """Gönderinin tezini kuran ham metin: yönetici özetinin tezi, özet yoksa
    ön bilgideki `ozet` (analiz_zinciri'nin dalıyla AYNI koşul)."""
    if yo and (yo["tez"] or yo["satirlar"]):
        return yo["tez"]
    return _duz(str(a.get("ozet") or ""))


def tez_uyarisi(a: dict, kisa: str | None = None) -> str | None:
    """Tezin ilk cümlesi ölçüm taşımıyorsa uyarı metni, yoksa None — TEK tanım.

    Gönderi kurucusu (`_tez`) ve yayından ÖNCE sorulan analiz sınavı
    (site/tools/analiz_sinavi.py) bunu çağırır: kural yalnız gönderi anında
    sorulsaydı yazar ilk geri bildirimi yazı yayımlandıktan sonra alırdı
    (05.10.2026 incelemesi: 14 analizin 10'u kuralı çiğniyordu). Yol
    gönderinin yoludur — yönetici özeti tezi ya da `ozet` → site atfı süzgeci
    → tez payı → ilk cümle; iki kapı aynı cümleye bakar."""
    if kisa is None:
        kisa = _kirp(_site_disi(_tez_ham(a, yonetici_ozeti(a.get("govde", "")))), TEZ_SINIR)
    if kisa and not tez_acilisi_olcu_tasir(kisa):
        return (f"{a.get('slug', '?')}: tezin ilk cümlesi ölçüm sayısı taşımıyor "
                f"({uret.cumleler(kisa)[0][:80]}) — analiz/YAZIM.md, yönetici özeti")
    return None


def _tez(a: dict, ham: str) -> str:
    tez = _site_disi(ham)
    kisa = _kirp(tez, TEZ_SINIR)
    if tez and not kisa:
        uret.DUSEN.append(("analiz-bütçe", f"tezin ilk cümlesi {TEZ_SINIR} karakteri aşıyor"))
    u = tez_uyarisi(a, kisa)
    if u:
        UYARILAR.append(u)
    return kisa


# KANIT SATIRI EN SON DÜŞER (05.10.2026 incelemesi). Şablon "Kanıtın gücü"nü
# tablonun SONUNA koyuyor (11 yazının 10'unda son satır), düşürme de sondan:
# tavanı aşan her yazıda ilk düşen satır yapısal olarak kanıtın gücüydü ve
# Hürmüz gönderisi ikinci el haber satırlarını, o haberlerin "bağımsız
# doğrulanmadı" çekincesi olmadan taşıdı. Kanıt satırı adıyla tanınır
# (şablonun adı; büyük/küçük harf ve sondaki noktalama yok sayılır) ve ancak
# tablodan geriye yalnız o kaldığında düşer. Kalanların sırası yazarındır;
# "haber satırı önce düşsün" sınıflaması yapılmaz — tabloda karşılığı yok.
KANIT_SORUSU = "kanıtın gücü"


def _kanit_mi(soru: str) -> bool:
    return uret._kucuk((soru or "").strip().rstrip(".?!:").strip()) == KANIT_SORUSU


def _dusecek_satir(sorular: list[str]) -> int:
    """Tavanda düşecek satırın sırası: sondan geriye ilk kanıt DIŞI satır."""
    for i in range(len(sorular) - 1, -1, -1):
        if not _kanit_mi(sorular[i]):
            return i
    return len(sorular) - 1


def analiz_zinciri(a: dict) -> list[str]:
    """Analizden TEK uzun gönderi. Yönetici özeti varsa ondan; yoksa ön
    bilgideki tez (ozet) ve açıklamadan. Link yok, emoji yok, site atfı yok,
    "…" yok: seçim birimi TAM cümledir (uret._kirp), sığmayan birim düşer."""
    uret.DUSEN.clear()
    yo = yonetici_ozeti(a.get("govde", ""))
    baslik = "\n".join(_baslik(a))
    satirlar: list[str] = []
    sorular: list[str] = []          # satırların soru sütunu (kanıt satırını tanımak için)
    rakamlar: list[tuple[str, str]] = []
    if yo and (yo["tez"] or yo["satirlar"]):
        tez = _tez(a, _tez_ham(a, yo))
        for soru, cevap in yo["satirlar"]:
            c = _site_disi(cevap)
            if not c:
                continue
            k = _kirp(c, SATIR_SINIR)
            if not k:                # ilk cümlesi bile sığmayan satır bütünüyle düşer
                uret.DUSEN.append(("analiz-bütçe", f"{soru}: ilk cümle {SATIR_SINIR} karakteri aşıyor"))
                continue
            satirlar.append(baslikli_satir(soru, k))
            sorular.append(soru)
        rakamlar = yo["rakamlar"]
    else:
        # Yedek yol: yalnız ön bilgideki TEZ (ozet). Açıklama alınmaz; yönetici
        # özeti olmayan bir yazının gönderisi kısa olur ve bunu söyler.
        tez = _tez(a, _tez_ham(a, yo))
        if not tez:
            raise SystemExit(f"{a['slug']}: yönetici özeti de tez de yok — gönderi kurulamaz")
        UYARILAR.append(f"{a['slug']}: yönetici özeti yok — yalnız tez gönderildi")
    # Tavan aşılıyorsa ORTADAN kısılır: tez kalır, tablo satırları SONDAN
    # itibaren düşer — "Kanıtın gücü" satırı en son, çünkü gövdedeki
    # iddiaların çekincesidir (`_dusecek_satir`) —, şerit her adımda KALAN
    # metne karşı yeniden kurulur; düşen satırın ölçümü şeride döner.
    #
    # ÖLÇÜ KIRPILMAMIŞ GÖVDEDEN ALINIR. `_kapat` gövdeyi tavana KIRPAR, yani
    # çıktısı tanımı gereği tavanı AŞAMAZ; döngü ölçüyü ondan okuduğu sürece
    # koşulu hiç sağlanmaz ve döngü ÖLÜ KODdur. O hâlde kırpma sondan yer ve
    # gönderinin sonundaki blok sessizce gider. 17.09.2026'da ölçüldü: ham
    # gövde 4132, tavan 3800, şerit çıktıda YOK ve hiçbir kapı sormuyordu.
    # Döngü `_kapat`ı ÇAĞIRMAZ; yalnız sonda bir kez.
    #
    # `_kapat`ın gövdeye bıraktığı pay — sorumluluk notu ve arasındaki boşluk
    # düşülmüş hâli. Tek yerde tanımlanır; iki ayrı aritmetik bir gün ayrışır.
    kapasite = GOVDE_SINIR - len(uret.SORUMLULUK_TEKNIK) - 2

    def _govde() -> str:
        return "\n\n".join(b for b in [baslik, tez, *satirlar] if b)

    def _ham(sinir: int) -> tuple[str, list[str]]:
        g = _govde()
        s, dusen = serit(rakamlar, g, sinir)
        return "\n\n".join(b for b in (g, s) if b), dusen

    while len(_ham(RAKAM_SINIR)[0]) > kapasite and satirlar:
        i = _dusecek_satir(sorular)
        sorular.pop(i)
        uret.DUSEN.append(("analiz-bütçe", satirlar.pop(i)))
    # Satırlar bittiyse şerit kalan paya sığdırılır (kalem bütünüyle düşer).
    pay = min(RAKAM_SINIR, kapasite - len(_govde()) - 2)
    ham, dusen = _ham(pay)
    uret.DUSEN.extend(("analiz-şerit", k) for k in dusen)
    return [uret._kapat(ham, uret.SORUMLULUK_TEKNIK)]



def bugunun_analizleri(gun: date | None = None, dizin: Path | None = None) -> list[dict]:
    """pubDate'i verilen güne eşit, yayımda (durum aktif) analizler."""
    gun = gun or date.today()
    out = []
    for a in analizler(dizin):
        if str(a.get("durum", "aktif")) != "aktif":
            continue
        if str(a.get("pubDate", "")).strip()[:10] == gun.isoformat():
            out.append(a)
    return out


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="analiz gönderisini bas (kuru)")
    p.add_argument("slug", nargs="?", help="analiz slug'ı (varsayılan: bugünün yazıları)")
    a = p.parse_args()
    secilen = [analizi_oku(ANALIZ_DIZIN / f"{a.slug}.mdx")] if a.slug else bugunun_analizleri()
    for an in secilen:
        UYARILAR.clear()
        t = analiz_zinciri(an)[0]
        print(f"── {an['slug']} ({len(t)} karakter)\n{t}\n")
        # Her tarihte çalışan TEK önizleme bu; uyarıları yutmamalı (05.10.2026).
        for u in UYARILAR:
            print(f"  ! {u}")
        for bolum, c in uret.DUSEN:
            print(f"  düştü [{bolum}] {c[:160]}")
