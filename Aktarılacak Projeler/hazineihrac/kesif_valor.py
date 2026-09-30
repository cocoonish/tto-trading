# -*- coding: utf-8 -*-
"""KEŞİF — ihale duyurularında valör ve vade GERÇEKTE nasıl yazılıyor?

Neden: birikmiş veri setinin 466 satırından birinde (10.04.2023 TLREF'e
Endeksli Devlet Tahvili, TRT010328T12) valör tarihi boş ve vadesi bu yüzden
hesaplanmamış; ağırlıklı ortalama vade o ihaleyi sessizce düşürüyor. Sebebi
tahmin edilmez, ÖLÇÜLÜR: hattın KENDİ ayrıştırıcısı (`_parse_auction_data`)
bütün sonuç duyurularına yeniden koşturulur ve depodaki satırlarla kıyaslanır.

Üç soru:
  1. Valörü okunamayan başka satır var mı; varsa blok metni neye benziyor?
  2. Yeniden ayrıştırma depodaki valör/itfa tarihleriyle birebir mi?
  3. Duyuru vadeyi GÜN olarak da yazıyor mu? Yazıyorsa (itfa − valör) ile
     bağımsız bir sınama olur.

İkinci koşu (düzeltilmiş ayrıştırıcıyla) depodaki HER satırın BÜTÜN alanlarını
kıyaslar ve düzeltilecek/eklenecek satırları ayrıştırıcının tam çıktısıyla
basar (SATIR_JSON) — veri setine giren her değer kaynağın kendi duyurusundan.

Hiçbir şey yazmaz; çıktı koşu kaydındadır. Paketler: PyPDF2 beautifulsoup4
aiohttp plotly (hattın main.py'si tepeden içe aktarıyor).
"""
from __future__ import annotations

import logging
import os
import re
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

KOK = os.path.dirname(os.path.abspath(__file__))
os.chdir(KOK)
sys.path.insert(0, KOK)

import pandas as pd  # noqa: E402
import main as M  # noqa: E402

logging.getLogger().setLevel(logging.WARNING)
for ad in list(logging.root.manager.loggerDict):
    logging.getLogger(ad).setLevel(logging.WARNING)

BAS = "2020-01"          # veri setinin ilk ihalesi 14.01.2020
S = M.TreasuryAuctionScraper(max_pages=200)
DESEN = (r"Tarihinde\s+Gerçekleştirilen\s+İhalelerin\s+Sonuçlarına\s+İlişkin\s+Basın\s+Duyurusu",
         r"Tarihinde\s+Gerçekleştirilen\s+İhalenin\s+Sonuçlarına\s+İlişkin\s+Basın\s+Duyurusu")


def duyurular() -> list[tuple[str, str, str]]:
    """(tarih, başlık, pdf) — API'nin kendi sırası, BAS'tan eskiye inince durur."""
    out, t0 = [], time.time()
    for sayfa in range(1, 400):
        for deneme in range(3):
            try:
                r = S.session.get(S.api_url, params={"category_name": S.category_slug,
                                                     "page": sayfa, "per_page": 20}, timeout=45)
                if r.status_code == 400:
                    return out
                r.raise_for_status()
                posts = r.json()
                break
            except Exception as e:  # noqa: BLE001
                print(f"  sayfa {sayfa} deneme {deneme + 1}: {e}")
                time.sleep(2)
        else:
            print(f"  sayfa {sayfa} alınamadı — tarama burada kesildi")
            return out
        if not posts:
            return out
        en_eski = "9999"
        for p in posts:
            import html as _h
            baslik = _h.unescape((p.get("title") or {}).get("rendered", "") or "").strip()
            tarih = str(p.get("date") or "")
            en_eski = min(en_eski, tarih or en_eski)
            if any(re.search(d, baslik, re.I) for d in DESEN):
                pdf = S._extract_pdf_url_from_content((p.get("content") or {}).get("rendered", "") or "")
                out.append((tarih[:10], baslik, pdf or ""))
        if sayfa % 10 == 0:
            print(f"  sayfa {sayfa}: {len(out)} sonuç duyurusu, en eski {en_eski[:10]} "
                  f"({time.time() - t0:.0f} sn)")
        if en_eski[:7] < BAS:
            return out
    return out


def pdf_metni(url: str) -> tuple[str, list[str]]:
    import io
    import PyPDF2
    for deneme in range(3):
        try:
            r = S.session.get(url, timeout=60)
            r.raise_for_status()
            okuyucu = PyPDF2.PdfReader(io.BytesIO(r.content))
            return url, [(s.extract_text() or "") for s in okuyucu.pages]
        except Exception as e:  # noqa: BLE001
            hata = str(e)
            time.sleep(2)
    return url, ["__HATA__ " + hata]


def isin_vade(isin: str):
    """DİBS ISIN'i vadeyi GGAAYY olarak taşır (TRT050527T17 → 05.05.2027)."""
    m = re.match(r"TR[A-Z](\d{2})(\d{2})(\d{2})", str(isin))
    return f"{m.group(1)}.{m.group(2)}.20{m.group(3)}" if m else None


def main() -> int:
    t0 = time.time()
    dok = sys.argv[sys.argv.index("--dok") + 1] if "--dok" in sys.argv else None
    D = duyurular()
    print(f"\n{len(D)} sonuç duyurusu ({time.time() - t0:.0f} sn); PDF'siz: "
          f"{sum(1 for d in D if not d[2])}")

    csv = pd.read_csv("hazine_ihale_verileri.csv", encoding="utf-8-sig", dtype=str)
    anahtar = {(r["ISIN"], r["İhale Tarihi"]): r for _, r in csv.iterrows()}

    urls = sorted({d[2] for d in D if d[2]})
    with ThreadPoolExecutor(max_workers=8) as ex:
        metin = dict(ex.map(pdf_metni, urls))
    hatali = [u for u, s in metin.items() if s and s[0].startswith("__HATA__")]
    print(f"{len(urls)} PDF indirildi ({time.time() - t0:.0f} sn); indirilemeyen {len(hatali)}")
    for u in hatali[:10]:
        print("   ", u, metin[u][0][:120])

    gun_kalibi = re.compile(r"(\d{2,5})\s*[Gg][üu]n")
    gorulen, eksik_valor, gun_sinama = {}, [], Counter()
    bicim = Counter()
    for tarih, baslik, pdf in D:
        for s_no, sayfa in enumerate(metin.get(pdf, [])):
            if sayfa.startswith("__HATA__"):
                continue
            satirlar = S._parse_auction_data(sayfa)
            isinler = list(re.finditer(r"(TR[A-Z0-9]{10})", sayfa))
            for i, sat in enumerate(satirlar):
                k = (sat.get("ISIN", ""), sat.get("İhale Tarihi", ""))
                bas = isinler[i].start() if i < len(isinler) else 0
                son = isinler[i + 1].start() if i + 1 < len(isinler) else len(sayfa)
                blok = sayfa[bas:son]
                bicim[S._sayi_bicimi(blok)] += 1
                if S._sayi_bicimi(blok) == ".":
                    print(f"  İNGİLİZCE biçim: {k} duyuru {tarih} {pdf}")
                gorulen[k] = dict(sat, _pdf=pdf, _duyuru=tarih)
                if not sat.get("Valör Tarihi"):
                    eksik_valor.append((tarih, baslik, pdf, s_no, k, sayfa, bas, blok))
                if gun_kalibi.findall(blok):
                    gun_sinama["gün var"] += 1
                else:
                    gun_sinama["gün yok"] += 1
    print(f"\nSAYI BİÇİMİ (blok başına): {dict(bicim)}")

    # ISIN'in taşıdığı vade ile ayrıştırılan itfa aynı mı (kaynağın kendi iç sınaması)
    uyumsuz = [(k, v.get("İtfa Tarihi"), isin_vade(k[0]), v.get("_pdf")) for k, v in gorulen.items()
               if isin_vade(k[0]) and v.get("İtfa Tarihi") != isin_vade(k[0])]
    print(f"\nISIN VADESİ ↔ AYRIŞTIRILAN İTFA uyumsuz: {len(uyumsuz)}")
    for u in uyumsuz:
        print("  ", u)

    # --dok GÜN: o günün sonuç duyurularının SAYFA METNİ (ham, ayrıştırıcının gördüğü)
    if dok:
        for tarih, baslik, pdf in D:
            if tarih != dok:
                continue
            print("#" * 100)
            print(f"DÖKÜM {tarih} · {baslik}\n{pdf}")
            for s_no, sayfa in enumerate(metin.get(pdf, [])):
                print(f"----- sayfa {s_no + 1} ({len(sayfa)} karakter) -----")
                print(sayfa)
            for u in uyumsuz:
                if u[3] == pdf:
                    print(f"  → uyumsuz satır: {u}")

    # DEPO ↔ YENİ AYRIŞTIRICI — BÜTÜN alanlar. Vade ayrı sınanır (cetvel değişti).
    def _say(x):
        try:
            return float(str(x).strip())
        except (TypeError, ValueError):
            return None
    alanlar = [c for c in csv.columns if c != "Vade (Yıl)"]
    fark, degisen_satir = [], {}
    for k, r in anahtar.items():
        y = gorulen.get(k)
        if y is None:
            continue
        for c in alanlar:
            a, b = str(r[c] if r[c] is not None else "").strip(), str(y.get(c, "") or "").strip()
            a = "" if a.lower() == "nan" else a
            fa, fb = _say(a), _say(b)
            ayni = (a == b) or (fa is not None and fb is not None and abs(fa - fb) < 1e-9) \
                or (a == "" and b in ("", "-")) or (fa is None and fb is None and a in ("", "-") and b in ("", "-"))
            if not ayni:
                fark.append((k, c, a, b))
                degisen_satir[k] = y
        # vade: yeni ayrıştırıcının yazdığı değer = depodaki tarihlerden gün/365
        vy = M.vade_yil(r["Valör Tarihi"], r["İtfa Tarihi"])
        vb = _say(y.get("Vade (Yıl)"))
        if vy is not None and (vb is None or abs(vy - vb) > 1e-9):
            fark.append((k, "Vade (Yıl)·gün/365", vy, vb))
    yeni_k = [k for k in gorulen if k not in anahtar]
    print(f"\nyeniden ayrıştırılan {len(gorulen)} · depoda {len(anahtar)} · depoda olup "
          f"ayrıştırmada olmayan {len(set(anahtar) - set(gorulen))} · yeni {len(yeni_k)}")
    for k in sorted(set(anahtar) - set(gorulen)):
        print("   depoda var, ayrıştırmada yok:", k)
    print(f"\nDEPO ↔ YENİ AYRIŞTIRICI alan farkı: {len(fark)} ({len(degisen_satir)} satır)")
    for f in fark:
        print("  ", f)
    print(f"\nVADE GÜN SINAMASI: {dict(gun_sinama)}")
    import json as _j
    print("\nDÜZELTİLECEK ve EKLENECEK satırlar (hattın ayrıştırıcısının tam çıktısı):")
    for k in sorted(degisen_satir):
        print("SATIR_JSON " + _j.dumps({"tur": "duzelt", **degisen_satir[k]}, ensure_ascii=False))
    for k in sorted(yeni_k):
        print("SATIR_JSON " + _j.dumps({"tur": "yeni", **gorulen[k]}, ensure_ascii=False))

    print(f"\nVALÖRÜ OKUNAMAYAN satır: {len(eksik_valor)}")
    for tarih, baslik, pdf, s_no, k, sayfa, bas, blok in eksik_valor:
        print("=" * 100)
        print(f"{k}  duyuru {tarih}  sayfa {s_no + 1}\n{baslik}\n{pdf}")
        print(blok[:1500])

    # biçim karnesi: valör satırı hangi yazımlarla geçiyor (bütün sayfalar)
    yazim = Counter()
    for u, sayfalar in metin.items():
        for s in sayfalar:
            for m in re.finditer(r"((?:İhraç|Ihraç|İhrac|Valör|Valor)[^\n:]{0,25}:)", s, re.I):
                yazim[re.sub(r"\s+", " ", m.group(1)).strip()] += 1
    print("\nVALÖR ETİKETİ YAZIMLARI (bütün PDF'ler):")
    for y, n in yazim.most_common(30):
        print(f"  {n:5d}  {y!r}")
    print(f"\nbitti ({time.time() - t0:.0f} sn)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
