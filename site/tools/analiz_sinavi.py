#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analiz yazılarının BİÇİM sınavı — analiz/YAZIM.md'nin araçtaki karşılığı.

Rehberde yazan her zorunluluk burada ölçülür; burada ölçülmeyen kural rehbere
yazılmaz. sayfa_sinavi.py bu modülü 10. ölçüt olarak çağırır; tek başına da
koşar:

    python3 site/tools/analiz_sinavi.py            # bütün analizler
    python3 site/tools/analiz_sinavi.py --yeni     # yalnız rehber sonrası yazılar

Kapsam kararı: rehber 1 Eylül 2026'da yazıldı. O günden SONRA yayımlanan
yazılar biçim ölçütlerinin (tarihli slug, tarihli başlık, zorunlu ön bilgi,
yönetici özeti, kapanış bölümü) kapısından geçer; daha eskiler yalnız BİLGİ
olarak raporlanır. Yayımlanmış yazılar değiştirilmez — kural geriye yürümez.
"""
from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
ANALIZ = KOK / "site" / "src" / "content" / "analiz"

# Rehberin yazıldığı gün: bu tarihten SONRAKİ yazılar kapıdan geçer.
REHBER_TARIHI = date(2026, 9, 1)
YONETICI_ESIGI = 20_000            # bayt — CLAUDE.md kuralı

AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
         "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]

ZORUNLU = ("title", "description", "pubDate", "tags", "durum", "kaynak", "ozet", "seviye")
SEVIYELER = {"giris", "orta", "ileri"}

sys.path.insert(0, str(KOK / "ortak"))
import on_bilgi as _on_bilgi  # noqa: E402  — tweet/analiz.py ile AYNI ayrıştırıcı
from tavsiye_dili import TAVSIYE  # noqa: E402
import okur_dili  # noqa: E402

_CUMLE = re.compile(r"(?<![0-9])(?<=[.!?])\s+(?=[A-ZÇĞİÖŞÜ\"«(])")


def _cumle_sayisi(m: str) -> int:
    m = (m or "").strip()
    return len([c for c in _CUMLE.split(m) if c.strip()]) if m else 0

SLUG_TARIH = re.compile(r"-(\d{4})-(\d{2})-(\d{2})$")
KAPANIS = re.compile(r"^##\s.*(ne ölçmedik|sınırlar|bilinmeyenler)", re.I | re.M)
KAPANIS_TEK_AD = re.compile(r"^##\s+Ne ölçmedik\s*$", re.M)
IZLEME = re.compile(r"^##\s.*(izleme|izlenmeli|izlemeli|izlenecek|takvim)", re.I | re.M)


def on_bilgi(metin: str) -> dict:
    """Ön bilgi — ortak/on_bilgi.py ile ayrıştırılır; katlanmış YAML engeldir."""
    return _on_bilgi.ayristir(metin)


def tarih_tr(g: date) -> str:
    return f"{g.day} {AYLAR[g.month - 1]} {g.year}"


def sina(yol: Path) -> tuple[list[str], list[str], bool]:
    """(engeller, uyarılar, rehber_sonrasi)."""
    metin = yol.read_text(encoding="utf-8")
    slug = yol.stem
    engel: list[str] = []
    uyari: list[str] = []
    try:
        fm = on_bilgi(metin)
    except _on_bilgi.OnBilgiHatasi as e:
        # Okunamayan ön bilgi YAŞA BAKILMADAN kapıdan geçmez: bilinmeyen tarih
        # "eski" değil "bilinmeyen"dir.
        return [f"ön bilgi okunamadı: {e}"], [], True

    pub: date | None = None
    pm = re.match(r"(\d{4})-(\d{2})-(\d{2})$", str(fm.get("pubDate", "")).strip())
    if pm:
        pub = date(int(pm.group(1)), int(pm.group(2)), int(pm.group(3)))
    if not pub:
        engel.append(f"pubDate okunamadı ({fm.get('pubDate')!r}) — YYYY-AA-GG bekleniyor")
    yeni = (pub is None) or (pub > REHBER_TARIHI)

    # ── ön bilgi
    eksik = [k for k in ZORUNLU if not fm.get(k)]
    if eksik:
        engel.append(f"ön bilgide eksik alan: {', '.join(eksik)}")
    sev = str(fm.get("seviye", ""))
    if sev and sev not in SEVIYELER:
        engel.append(f"seviye geçersiz: {sev!r} (giris | orta | ileri)")
    if str(fm.get("durum", "")) not in ("aktif", "taslak", "arsiv"):
        engel.append(f"durum geçersiz: {fm.get('durum')!r}")
    etiketler = fm.get("tags") or []
    if isinstance(etiketler, list):
        buyuk = [t for t in etiketler if isinstance(t, str) and t != t.lower()]
        if buyuk:
            engel.append(f"etiketler küçük harf olmalı: {buyuk}")
    n_ozet = _cumle_sayisi(str(fm.get("ozet") or ""))
    if n_ozet > 2:
        uyari.append(f"ozet tek cümle olmalı ({n_ozet} cümle) — kartta ve gönderide bu görünür")
    n_acik = _cumle_sayisi(str(fm.get("description") or ""))
    if n_acik and (n_acik < 2 or n_acik > 6):
        uyari.append(f"description 2–6 cümle olmalı ({n_acik} cümle)")
    vt = str(fm.get("veriTarihi") or "")
    if vt and not re.match(r"^\d{4}-\d{2}-\d{2}$", vt):
        engel.append(f"veriTarihi YYYY-AA-GG olmalı ({vt!r})")
    elif not vt:
        uyari.append("veriTarihi yok — yazının veri çıpası künyede görünmez")

    # ── tavsiye dili: yayın analiz yapar, tavsiye vermez (ortak/tavsiye_dili.py)
    okur_metni = re.sub(r"<[^>]+>", " ", re.sub(r"```.*?```", " ", metin, flags=re.S))
    t = TAVSIYE.search(okur_metni)
    if t:
        engel.append(f"tavsiye dili: {t.group(0)!r}")

    # ── slug tarihi
    sm = SLUG_TARIH.search(slug)
    if not sm:
        engel.append("slug tarih taşımıyor (<konu>-<YYYY-AA-GG>)")
    elif pub:
        st = date(int(sm.group(1)), int(sm.group(2)), int(sm.group(3)))
        if st != pub:
            engel.append(f"slug tarihi ({st}) ile pubDate ({pub}) farklı")

    # ── başlık tarihi
    baslik = str(fm.get("title", ""))
    if pub:
        bek = tarih_tr(pub)
        if not baslik.startswith(bek + " "):
            engel.append(f"başlık '{bek} ' ile başlamalı (başlık: {baslik[:60]!r})")
    if " — " not in baslik and " – " not in baslik:
        uyari.append("başlıkta alt başlık ayracı (—) yok")

    # ── gövde
    boyut = len(metin.encode("utf-8"))
    yonetici = 'class="yonetici"' in metin
    if boyut > YONETICI_ESIGI and not yonetici:
        engel.append(f"{boyut // 1000} KB'lık yazıda yönetici özeti yok")
    if yonetici:
        for parca, ad in (('class="tez"', "p.tez"), ("<table", "soru–cevap tablosu"),
                          ('class="rakamlar"', "ul.rakamlar")):
            if parca not in metin:
                engel.append(f"yönetici özetinde {ad} yok")
        blok = re.search(r'<div class="yonetici">(.*?)\n</div>', metin, re.S)
        # <Deger> ARANMAZ: analiz yayımlandığı günün metnidir (karar
        # 08.09.2026); sayılar sabit yazılır, canlı bağ yalnız panolarda.
        # RAKAM ŞERİDİ SÖZLEŞMESİ: <li><b>değer</b><span>etiket</span></li>, 5–8 öğe.
        # Tweet üretici bu işaretlemeyi okur; span'sız bir öğe gönderiden düşer.
        rk = re.search(r'<ul class="rakamlar">(.*?)</ul>', metin, re.S)
        if rk:
            ogeler = re.findall(r"<li>(.*?)</li>", rk.group(1), re.S)
            bozuk = [i + 1 for i, li in enumerate(ogeler) if not (re.search(r"<b>.*?</b>", li, re.S) and re.search(r"<span>.*?</span>", li, re.S))]
            if bozuk:
                engel.append(f"rakam şeridinde <b>+<span> sözleşmesine uymayan öğe: {bozuk}")
            if not 5 <= len(ogeler) <= 8:
                uyari.append(f"rakam şeridinde {len(ogeler)} öğe (beklenen 5–8)")
        satirlar = re.findall(r"<tr>\s*<td>(.*?)</td>\s*<td>", blok.group(1), re.S) if blok else []
        if blok and not 4 <= len(satirlar) <= 10:
            uyari.append(f"soru–cevap tablosunda {len(satirlar)} satır (beklenen 4–10)")
        if blok:
            for iz in ("yukarıdaki", "aşağıdaki", "bu yazının", "bölümünde", "grafikte"):
                if iz in blok.group(1).lower():
                    uyari.append(f"yönetici özeti sayfa mobilyasına atıf yapıyor: {iz!r} "
                                 "(tweete olduğu gibi çıkar)")
                    break
    if not KAPANIS.search(metin):
        engel.append("kapanış bölümü yok ('## Ne ölçmedik' ya da '… sınırları')")
    elif not KAPANIS_TEK_AD.search(metin):
        uyari.append("kapanış bölümünün adı '## Ne ölçmedik' olmalı (rehber sonrası yazılarda tek ad)")
    # okur dili (ortak tanım) — sayfa sınavı 9. ölçütle aynı, buradan da düşer
    for aile, esl, sat in okur_dili.tara(metin)[:3]:
        engel.append(f"okur dili ({aile}) satır {sat}: {esl!r}")
    if not IZLEME.search(metin):
        uyari.append("izleme listesi bölümü yok")
    if "<Deger" in metin and "import Deger" not in metin:
        engel.append("<Deger> kullanılıyor ama içe aktarılmamış")
    if "<GrafikEmbed" in metin and "import GrafikEmbed" not in metin:
        engel.append("<GrafikEmbed> kullanılıyor ama içe aktarılmamış")

    return engel, uyari, yeni


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    yalniz_yeni = "--yeni" in argv
    dosyalar = sorted(ANALIZ.glob("*.mdx"))
    dusen = 0
    print(f"▶ Analiz biçim sınavı ({len(dosyalar)} yazı · kapı: {REHBER_TARIHI} sonrası)")
    for yol in dosyalar:
        engel, uyari, yeni = sina(yol)
        if yalniz_yeni and not yeni:
            continue
        kapi = "KAPI" if yeni else "bilgi"
        durum = "✗" if (engel and yeni) else ("!" if (engel or uyari) else "✓")
        print(f"  {durum} {yol.stem} [{kapi}]"
              + (f" · {len(engel)} eksik" if engel else "")
              + (f" · {len(uyari)} uyarı" if uyari else ""))
        for e in engel:
            print(f"      {'ENGEL' if yeni else 'eksik'}: {e}")
        for u in uyari:
            print(f"      uyarı: {u}")
        if engel and yeni:
            dusen += 1
    if dusen:
        print(f"\nANALİZ SINAVI DÜŞTÜ — {dusen} yazı rehbere uymuyor (analiz/YAZIM.md).")
        return 1
    print("  analiz biçim sınavı geçti (rehber sonrası yazılarda engel yok)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
