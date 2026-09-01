#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Teknik analiz bülteninin YORUM katmanı için güvenli yazma kapısı.

Yazı katmanı (Claude oturumu) yalnız şu alanlara dokunabilir:

    giris                      haftanın çerçevesi — HTML paragraflar
    yorum.<slug>               enstrüman yorumu — HTML (trend, momentum,
                               seviyeler, iki yönlü senaryo + geçersizlik);
                               iskelet dört <h4>: Günlük · 4 saatlik · 1 saatlik ·
                               Ortak görüş (ölçümü eksik dilim muaf)
    duzeltmeler                yayımlanmış bir sayının düzeltme kaydı
                               [{alan, eski, yeni, sebep?, tarih?}] — bültenle aynı

Kullanım:
    python3 teknik/yaz.py yama.json --damga <olcum_zamani>
    cat yama.json | python3 teknik/yaz.py - --damga ...

Sigortalar ARAÇTA (rutin metnine güvenilmez — bkz. CLAUDE.md): damga, sayı
kaynağı, okur dili, TAVSİYE DİLİ (ortak/tavsiye_dili.py) ve yorum iskeleti.

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
KOK = BURASI.parent
VERI = KOK / "site" / "src" / "data" / "teknik"
sys.path.insert(0, str(KOK / "ortak"))
sys.path.insert(0, str(KOK / "bulten"))
from tavsiye_dili import TAVSIYE  # noqa: E402  — bülten/analiz/tweet kapılarıyla AYNI kalıp

# Yorumun İSKELETİ SABİT (bulten/YAZIM.md, "Haftalık teknik analiz"): dört
# <h4> başlığı. Ölçümde eksik dilim varsa o dilimin başlığı atlanabilir.
ISKELET = {"Günlük": "gun", "4 saatlik": "s4", "1 saatlik": "s1", "Ortak görüş": None}
KELIME_ARALIGI = (250, 400)        # rehberin istediği; dışına çıkan UYARI alır


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
    p.add_argument("--iskeletsiz", action="store_true",
                   help="dört <h4> iskeleti sigortasını bilinçli atla")
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

    izinli = {"giris", "yorum", "duzeltmeler"}
    yabanci = [k for k in yama if k not in izinli]
    if yabanci:
        raise SystemExit(
            f"yazı katmanı bu alanlara dokunamaz: {', '.join(yabanci)}\n"
            "dokunabildikleri: giris, yorum (slug → HTML), duzeltmeler. Ölçülen "
            "alanlar teknik/olc.py'den gelir; elle yazılırsa bülten ölçüm olmaktan çıkar.")

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

    uyarilar: list[str] = []
    for slug, metin in (yama.get("yorum") or {}).items():
        if slug not in sluglar:
            raise SystemExit(f"bilinmeyen enstrüman: {slug!r} — "
                             f"geçerli: {', '.join(sluglar)}")
        if not str(metin or "").strip():
            continue
        s = dogrula_sayilar(str(metin), havuz)
        if s:
            tum_sorunlu[slug] = s
        # İSKELET: dört <h4>; ölçümü eksik dilimin başlığı muaf.
        basliklar = {re.sub(r"\s+", " ", b).strip() for b in re.findall(r"<h4>(.*?)</h4>", str(metin), re.S)}
        dilimler = sluglar[slug].get("dilimler") or {}
        eksik = [ad for ad, kod in ISKELET.items()
                 if ad not in basliklar and not (kod and (dilimler.get(kod) or {}).get("eksik"))]
        if eksik and not a.iskeletsiz:
            raise SystemExit(
                f"{slug}: yorum iskeleti eksik — <h4> başlıkları: {', '.join(eksik)}. "
                "Rehber dört başlık ister (Günlük · 4 saatlik · 1 saatlik · Ortak görüş); "
                "ölçümü eksik dilim muaf. Bilinçli istisna: --iskeletsiz.")
        n_kelime = len(re.sub(r"<[^>]+>", " ", str(metin)).split())
        if not KELIME_ARALIGI[0] <= n_kelime <= KELIME_ARALIGI[1]:
            uyarilar.append(f"{slug}: {n_kelime} kelime (rehber {KELIME_ARALIGI[0]}–{KELIME_ARALIGI[1]})")
        sluglar[slug]["yorum"] = metin
        degisen.append(f"yorum.{slug} ({n_kelime} kelime)")

    # DÜZELTMELER — bültenle aynı sözleşme (bulten/yaz.py): alan, eski, yeni, sebep, tarih.
    if "duzeltmeler" in yama:
        # Bu dosya da `yaz` adıyla yüklenir; `import yaz` kendini bulur. Bülten
        # sürümü yola göre, ayrı adla yüklenir.
        import importlib.util
        _spec = importlib.util.spec_from_file_location("bulten_yaz", KOK / "bulten" / "yaz.py")
        bulten_yaz = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(bulten_yaz)
        b["duzeltmeler"] = [] if yama["duzeltmeler"] is None else bulten_yaz.duzeltmeleri_dogrula(yama["duzeltmeler"])
        degisen.append(f"duzeltmeler ({len(b['duzeltmeler'])} kayıt)")

    # OKUR DİLİ KAPISI. Sayı denetimi "uydurma yok" der; bu kapı "okura yaz"
    # der. İkisi ayrı kusur: bir cümlenin her sayısı ölçümden gelebilir ve yine
    # de okurun anlamayacağı bir cümle olabilir. Kalıplar ortak/okur_dili.py'de,
    # bülten denetimi ve sayfa sınavıyla ORTAK.
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ortak"))
    import okur_dili
    yazilan = " ".join([str(yama.get("giris") or "")]
                       + [str(v) for v in (yama.get("yorum") or {}).values()])
    # TAVSİYE DİLİ KAPISI: rehber "alın/satın yazılmaz, senaryo dili" der; kapı
    # yalnız rehberde duruyordu ve tavsiye dili sayfaya girip tweet kapısında
    # düşebiliyordu. Kalıp ortak (ortak/tavsiye_dili.py).
    t = TAVSIYE.search(re.sub(r"<[^>]+>", " ", yazilan))
    if t:
        raise SystemExit(f"TAVSİYE DİLİ — yazma reddedildi: {t.group(0)!r}. "
                         "Senaryo dili kullanılır; 'alın', 'satın', 'hedef fiyat' yazılmaz.")
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
    # YORUM DAMGASI: yazı katmanının anı (dilimli UTC) ve sürümü — künye ve RSS bunu okur.
    from datetime import datetime, timezone
    b["yorum_zamani"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    b["yazi_surumu"] = int(b.get("yazi_surumu") or 0) + 1
    hedef.write_text(json.dumps(b, ensure_ascii=False, indent=1) + "\n",
                     encoding="utf-8")
    for u in uyarilar:
        print(f"::warning::{u}")
    print(f"yazıldı: {hedef.name} — " + " · ".join(degisen))
    print(f"yazili = {b['yazili']}" +
          ("" if b["yazili"] else "  (tüm yorumlar + giriş dolunca sayfa yayımlanır)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
