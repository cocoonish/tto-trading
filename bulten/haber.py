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
import re
import unicodedata
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

from ayar import (HABER_KAYNAKLARI, HABER_SINIRI, HABER_ILGILI, HABER_GURULTU,
                  TCMB_DUYURU_URL, RESMI_GAZETE_URL, RG_ILGILI)


@dataclass
class Haber:
    baslik: str
    baglanti: str
    kaynak: str
    etiket: str
    zaman: str = ""
    kurum: bool = False


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


def _ayristir(xml_metin: str) -> list[tuple[str, str, datetime | None]]:
    """(başlık, bağlantı, zaman) üçlüleri. feedparser varsa o, yoksa ElementTree."""
    try:
        import feedparser
        d = feedparser.parse(xml_metin)
        out = []
        for e in d.entries:
            t = None
            if getattr(e, "published_parsed", None):
                from calendar import timegm
                t = datetime.fromtimestamp(timegm(e.published_parsed), tz=timezone.utc)
            out.append((getattr(e, "title", ""), getattr(e, "link", ""), t))
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
        out.append((al("title"), al("link"), _zaman_coz(al("pubDate", "updated", "published"))))
    return out


def _sadelestir(b: str) -> str:
    b = unicodedata.normalize("NFKD", html.unescape(b or "")).lower()
    return re.sub(r"[^a-z0-9ğüşiöç ]", "", b).strip()


def _ilgili_mi(baslik: str) -> bool:
    b = (baslik or "").lower()
    if re.search(HABER_GURULTU, b, re.I):
        return False
    return bool(re.search(HABER_ILGILI, b, re.I))


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
                              zaman.isoformat(), True))
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
                         "kurum", bugun, True))
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
            kumeler[eslesen] = (kk | kh, temsil, n + 1)
    for _, temsil, n in kumeler:
        if n > 1:
            temsil.kaynak = f"{temsil.kaynak} (+{n - 1} kaynak)"
        kalanlar.append(temsil)
    return kalanlar


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
        for baslik, baglanti, zaman in kayitlar:
            if not baslik:
                continue
            if zaman is not None and zaman < sinir:
                continue
            if not k.get("yuksek_oncelik") and not _ilgili_mi(baslik):
                continue          # gürültü: alaka süzgecinden geçmedi
            anahtar = _sadelestir(baslik)[:90]
            if not anahtar or anahtar in gorulen:
                continue
            gorulen.add(anahtar)
            haberler.append(Haber(html.unescape(baslik).strip(), baglanti, k["ad"],
                                  k.get("etiket", ""),
                                  zaman.isoformat() if zaman else "",
                                  bool(k.get("yuksek_oncelik"))))
            n += 1
            if n >= 25:
                break

    # Kurum duyuruları önce (hepsi), sonra haberler — her grup içinde en yeni üstte.
    # Sınır YALNIZ haberlere uygulanır: bir kurum duyurusunu kesmek, bültenin
    # varlık sebebini kesmek olurdu.
    kurumlar = sorted([h for h in haberler if h.kurum], key=lambda h: h.zaman or "", reverse=True)
    digerleri = _kumele(sorted([h for h in haberler if not h.kurum],
                               key=lambda h: h.zaman or "", reverse=True))[:HABER_SINIRI]
    return kurumlar + digerleri, dusen


if __name__ == "__main__":
    h, dusen = tara()
    print(f"{len(h)} haber · {len(dusen)} kaynak okunamadı {dusen if dusen else ''}")
    for x in h[:20]:
        im = "K" if x.kurum else " "
        print(f" {im} [{x.kaynak[:24]:24s}] {x.baslik[:96]}")
