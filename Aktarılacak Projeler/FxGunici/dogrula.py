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

#: Tanım gereği sabit olan sayılar (ölçüm değil): aralık ve eşik düzeyleri, pip büyüklükleri, olasılık tanımları,
#: kapsam eşiği (gunluk.py: kapsam < 0,5 tatil). Buraya bir ÖLÇÜM yazılamaz.
TANIM = {"%95", "%5", "%50", "%30", "%70", "0,0001", "0,01", "0,95", "0,5"}

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
    return hata


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
    hata += sira_denetimi()
    hata += kunye_denetimi()
    hata += onkayit_denetimi()
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
        gomulen = set()
        for slug, (mdx, u) in cikti.items():
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
