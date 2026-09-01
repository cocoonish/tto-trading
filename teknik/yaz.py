#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Teknik analiz bülteninin YORUM katmanı için güvenli yazma kapısı.

Yazı katmanı (Claude oturumu) yalnız şu alanlara dokunabilir:

    giris                      haftanın çerçevesi — HTML paragraflar
    yorum.<slug>               enstrüman yorumu — HTML (trend, momentum,
                               seviyeler, iki yönlü senaryo + geçersizlik)

Kullanım:
    python3 teknik/yaz.py yama.json --damga <olcum_zamani>
    cat yama.json | python3 teknik/yaz.py - --damga ...

İki sigorta, ikisi de ARAÇTA (rutin metnine güvenilmez — bkz. CLAUDE.md):

1. DAMGA. --damga, hedef dosyanın olcum_zamani'siyle birebir aynı olmalı.
   Yazan taraf hangi ölçüme yorum yazdığını okumuş olmak zorunda; bayat bir
   ölçüme (ya da o yazarken yenilenen ölçüme) yorum yapıştırılamaz.
   Bilerek atlamak için --damgasiz.

2. SAYI KAYNAĞI. Yorumda geçen her "fiyat gibi" sayı (ondalıklı ya da 3+
   basamaklı) ölçüm JSON'unda birebir bulunmak zorunda — uydurma yok. Küçük
   tamsayılar (RSI eşiği 70, SMA200'ün 200'ü, yüzde 50 gibi ≤200) ve yıllar
   serbesttir. Eşleşmeyen sayı varsa yazma REDDEDİLİR ve sayılar listelenir;
   bilinçli istisna için --serbest (gerekçesi yoruma yazılmalı).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
VERI = BURASI.parent / "site" / "src" / "data" / "teknik"


def _sayilari_topla(dugum, havuz: set[str]) -> None:
    if isinstance(dugum, (int, float)) and not isinstance(dugum, bool):
        for n in range(0, 5):
            for deger in (round(float(dugum), n), abs(round(float(dugum), n))):
                s = f"{deger:.{n}f}"
                # Sondaki sıfır yalnız ONDALIKTA kırpılır: "14140" tamsayısını
                # rstrip("0") ile "1414"e çevirmek havuzu sessizce deliyordu.
                if "." in s:
                    s = s.rstrip("0").rstrip(".")
                havuz.add(s)
    elif isinstance(dugum, dict):
        for v in dugum.values():
            _sayilari_topla(v, havuz)
    elif isinstance(dugum, list):
        for v in dugum:
            _sayilari_topla(v, havuz)


SAYI = re.compile(r"\d+(?:[.,]\d+)*")


def _normallestir(ham: str) -> str:
    """Türkçe yazımı makine biçimine çevirir: '14.641,6' → '14641.6'.
    Hem nokta hem virgül varsa nokta binlik ayracıdır; yalnız virgül varsa
    ondalıktır; yalnız nokta belirsizdir (ondalık kabul edilir, binlik hâli
    ayrıca denenir)."""
    if "," in ham and "." in ham:
        return ham.replace(".", "").replace(",", ".")
    return ham.replace(",", ".")


def dogrula_sayilar(metin: str, havuz: set[str]) -> list[str]:
    """Ölçümde karşılığı olmayan 'fiyat gibi' sayılar."""
    sade = re.sub(r"<[^>]+>", " ", metin)
    sorunlu = []
    for ham in SAYI.findall(sade):
        aday = _normallestir(ham)
        duz = aday.rstrip("0").rstrip(".") if "." in aday else aday
        if "." not in aday and (len(aday) <= 3 and int(aday) <= 200):
            continue                        # eşik/pencere tamsayıları serbest
        if aday.isdigit() and 1990 <= int(aday) <= 2100:
            continue                        # yıl
        binliksiz = aday.replace(".", "")
        if duz in havuz or aday in havuz or binliksiz in havuz:
            continue
        sorunlu.append(ham)
    return sorted(set(sorunlu))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("yama", help="yama JSON dosyası ya da '-' (stdin)")
    p.add_argument("--tarih", help="hedef bülten (varsayılan: en yenisi)")
    p.add_argument("--damga", help="hedefin olcum_zamani değeri")
    p.add_argument("--damgasiz", action="store_true",
                   help="damga sigortasını bilinçli atla")
    p.add_argument("--serbest", action="store_true",
                   help="sayı-kaynağı sigortasını bilinçli atla")
    a = p.parse_args()

    dosyalar = sorted(VERI.glob("????-??-??.json"))
    if a.tarih:
        hedef = VERI / f"{a.tarih}.json"
    elif dosyalar:
        hedef = dosyalar[-1]
    else:
        raise SystemExit("hedef teknik bülten yok — önce teknik/olc.py koşmalı")
    if not hedef.exists():
        raise SystemExit(f"{hedef} yok")

    b = json.loads(hedef.read_text(encoding="utf-8"))

    if not a.damgasiz:
        if not a.damga:
            raise SystemExit(
                "damga zorunlu: --damga <olcum_zamani>\n"
                f"hedefin damgası şu komutla okunur:\n"
                f"  python3 -c \"import json;print(json.load(open('{hedef}'))"
                f"['olcum_zamani'])\"\n"
                "bilinçli atlamak için --damgasiz")
        if a.damga != b.get("olcum_zamani"):
            raise SystemExit(
                f"damga uyuşmuyor: verilen {a.damga!r}, "
                f"dosyadaki {b.get('olcum_zamani')!r}.\n"
                "Ölçüm sen okuduktan sonra yenilenmiş olabilir — "
                "JSON'u yeniden oku, yorumu güncel sayılarla kur.")

    ham = sys.stdin.read() if a.yama == "-" else Path(a.yama).read_text(encoding="utf-8")
    yama = json.loads(ham)

    izinli = {"giris", "yorum"}
    yabanci = [k for k in yama if k not in izinli]
    if yabanci:
        raise SystemExit(
            f"yazı katmanı bu alanlara dokunamaz: {', '.join(yabanci)}\n"
            "dokunabildikleri: giris, yorum (slug → HTML). Ölçülen alanlar "
            "teknik/olc.py'den gelir; elle yazılırsa bülten ölçüm olmaktan çıkar.")

    sluglar = {e["slug"]: e for e in b["enstrumanlar"]}
    havuz: set[str] = set()
    _sayilari_topla({"enstrumanlar": b["enstrumanlar"]}, havuz)
    # Metodoloji sabitleri: Fibonacci oran ADLARI (%38,2 gibi) ölçü değil
    # gösterge tanımıdır — RSI'ın 70'i neyse bunlar da o. Seviyelerin kendisi
    # (fib.s382 vb.) yine ölçümden doğrulanır.
    havuz.update({"23.6", "38.2", "61.8", "78.6"})

    degisen: list[str] = []
    tum_sorunlu: dict[str, list[str]] = {}

    if "giris" in yama and str(yama["giris"] or "").strip():
        s = dogrula_sayilar(str(yama["giris"]), havuz)
        if s:
            tum_sorunlu["giris"] = s
        b["giris"] = yama["giris"]
        degisen.append(f"giris ({len(str(yama['giris']).split())} kelime)")

    for slug, metin in (yama.get("yorum") or {}).items():
        if slug not in sluglar:
            raise SystemExit(f"bilinmeyen enstrüman: {slug!r} — "
                             f"geçerli: {', '.join(sluglar)}")
        if not str(metin or "").strip():
            continue
        s = dogrula_sayilar(str(metin), havuz)
        if s:
            tum_sorunlu[slug] = s
        sluglar[slug]["yorum"] = metin
        degisen.append(f"yorum.{slug} ({len(str(metin).split())} kelime)")

    # OKUR DİLİ KAPISI. Sayı denetimi "uydurma yok" der; bu kapı "okura yaz"
    # der. İkisi ayrı kusur: bir cümlenin her sayısı ölçümden gelebilir ve yine
    # de okurun anlamayacağı bir cümle olabilir. Kalıplar ortak/okur_dili.py'de,
    # bülten denetimi ve sayfa sınavıyla ORTAK.
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ortak"))
    import okur_dili
    yazilan = " ".join([str(yama.get("giris") or "")]
                       + [str(v) for v in (yama.get("yorum") or {}).values()])
    dil_bulgu = okur_dili.tara(yazilan)
    if dil_bulgu:
        dokum = "\n".join(f"  {a_}: {e!r} (satır {s_})" for a_, e, s_ in dil_bulgu)
        raise SystemExit(
            "OKURA DEĞİL KENDİMİZE YAZAN DİL — yazma reddedildi:\n" + dokum +
            "\nDosya/alan adları ve kendi sürüm tarihçemiz bültene girmez; "
            "bulguyu taşıyan cümle kalır, süreç anlatısı gider.")

    if tum_sorunlu and not a.serbest:
        satirlar = [f"  {k}: {', '.join(v)}" for k, v in tum_sorunlu.items()]
        raise SystemExit(
            "ÖLÇÜMDE KARŞILIĞI OLMAYAN SAYILAR — yazma reddedildi:\n"
            + "\n".join(satirlar) +
            "\nHer seviye/deger ölçüm JSON'undan alınmalı (uydurma yok). "
            "Sayı doğruysa ve ölçümde gerçekten yoksa ölçüm eksik demektir: "
            "önce teknik/olc.py'ye ekletilir. Bilinçli istisna: --serbest.")

    if not degisen:
        print("yama boş — hiçbir alan değişmedi")
        return 0

    b["yazili"] = all(e.get("yorum") for e in b["enstrumanlar"]) and bool(b.get("giris"))
    hedef.write_text(json.dumps(b, ensure_ascii=False, indent=1) + "\n",
                     encoding="utf-8")
    print(f"yazıldı: {hedef.name} — " + " · ".join(degisen))
    print(f"yazili = {b['yazili']}" +
          ("" if b["yazili"] else "  (tüm yorumlar + giriş dolunca sayfa yayımlanır)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
