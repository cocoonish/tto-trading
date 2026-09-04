#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Yazı katmanının bülten dosyasına güvenle yazması için ara katman.

Yazı katmanı (bir Claude oturumu) bültenin ÖLÇÜLEN kısmına dokunmamalı: piyasa
fotoğrafı, takvim, göstergeler ve hat hat değişim hep deterministik koşudan
gelir. Yazan taraf yalnız dört alana dokunur:

    yorum        "Günün/Haftanın okuması" — HTML paragraflar
    ozet         {"ne_oldu": "...", "ne_bekleniyor": "..."}
    gundem       bölüm kimliği → HTML metin (bkz. ayar.GUNDEM_YAZI_BOLUMLERI)
    duzeltmeler  [{"alan": "...", "eski": "...", "yeni": "...", "sebep": "...",
                   "tarih": "YYYY-MM-DD"}] — daha önce YAYIMLANMIŞ bir sayının
                 düzeltme kaydı. Metindeki "yayımlanan X yerine gerçek değer Y"
                 kalıbının yapısal eşi: sayfa "Düzeltmeler" bölümünde basar,
                 site /duzeltmeler/ sayfasında bütün bültenlerinkini toplar.
                 Liste bütünüyle yazılır (yama mevcut listeyi DEĞİŞTİRİR).
    (gundem_kaynagi otomatik "yazili" olur — sayfa yalnız bunu yayımlar)

Kullanım — yama dosyası ya da borudan JSON:

    python3 bulten/yaz.py yama.json --damga "<olusturma>" --denetle   # sına, yazma
    python3 bulten/yaz.py yama.json --damga "<olusturma>"             # denetim temizse yaz
    cat yama.json | python3 bulten/yaz.py -
    python3 bulten/yaz.py yama.json --tarih 2026-08-26

Çıkış kodları: 0 yazıldı · 2 girdi hatası · 3 damga uyuşmadı · 5 denetim ENGEL
(dosyaya yazılmadı).

Yama, mevcut içeriğin ÜZERİNE yazar ama dosyadaki diğer her şeyi korur; bir
bölümü boş göndermek onu silmez (kazara boşaltmaya karşı). Silmek gerekirse
alanın değeri olarak açıkça null verilir.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from datetime import date
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent
BULTEN = KOK / "site" / "src" / "data" / "bulten"

YAZILABILIR = ("yorum", "ozet", "gundem", "duzeltmeler")
DUZELTME_ZORUNLU = ("alan", "eski", "yeni")


def duzeltmeleri_dogrula(liste) -> list[dict]:
    """Düzeltme kayıtlarını biçimce sınar; eksik alan varsa yazma REDDEDİLİR.
    Yarım bir düzeltme kaydı ("neyin, neye" yazmayan) okura hesap vermez."""
    if not isinstance(liste, list):
        raise SystemExit("duzeltmeler bir liste olmalı: [{alan, eski, yeni, sebep?, tarih?}]")
    temiz: list[dict] = []
    for i, d in enumerate(liste, 1):
        if not isinstance(d, dict):
            raise SystemExit(f"duzeltmeler[{i}] bir nesne değil")
        eksik = [k for k in DUZELTME_ZORUNLU if not str(d.get(k, "")).strip()]
        if eksik:
            raise SystemExit(f"duzeltmeler[{i}]: eksik alan {', '.join(eksik)} — "
                             "her düzeltme neyin (alan), neyden (eski) neye (yeni) "
                             "düzeltildiğini yazar")
        t = str(d.get("tarih") or date.today().isoformat())
        try:
            dt.date.fromisoformat(t)
        except ValueError:
            raise SystemExit(f"duzeltmeler[{i}]: tarih YYYY-MM-DD olmalı ({t!r})")
        temiz.append({"tarih": t, "alan": str(d["alan"]).strip(),
                      "eski": str(d["eski"]).strip(), "yeni": str(d["yeni"]).strip(),
                      "sebep": str(d.get("sebep") or "").strip()})
    return temiz


def uygula(hedef: Path, yama: dict) -> tuple[dict, list[str]]:
    b = json.loads(hedef.read_text(encoding="utf-8"))
    degisen: list[str] = []

    yabanci = [k for k in yama if k not in YAZILABILIR]
    if yabanci:
        raise SystemExit(
            f"yazı katmanı bu alanlara dokunamaz: {', '.join(yabanci)}\n"
            f"dokunabileceği alanlar: {', '.join(YAZILABILIR)}\n"
            "ölçülen alanlar (piyasa, takvim, gostergeler, gruplar) deterministik "
            "koşudan gelir; elle yazılırsa bülten ölçüm olmaktan çıkar.")

    if "yorum" in yama:
        y = yama["yorum"]
        if y is None:
            b["yorum"], b["yorum_zamani"] = None, None
            degisen.append("yorum silindi")
        elif str(y).strip():
            b["yorum"] = y
            b["yorum_zamani"] = date.today().isoformat()
            degisen.append(f"yorum ({len(str(y).split())} kelime)")

    if "ozet" in yama and isinstance(yama["ozet"], dict):
        mevcut = b.get("ozet") or {}
        for k in ("ne_oldu", "ne_bekleniyor"):
            if k in yama["ozet"] and str(yama["ozet"][k] or "").strip():
                mevcut[k] = yama["ozet"][k]
                degisen.append(f"ozet.{k}")
        b["ozet"] = mevcut

    if "gundem" in yama and isinstance(yama["gundem"], dict):
        mevcut = b.get("gundem") or {}
        for k, v in yama["gundem"].items():
            if str(v or "").strip():
                mevcut[k] = v
                degisen.append(f"gundem.{k} ({len(str(v).split())} kelime)")
        b["gundem"] = mevcut
        # Sayfa yalnız 'yazili' bültenleri yayımlar; yazan taraf bunu elle
        # işaretlemek zorunda kalmasın diye burada damgalanır.
        if mevcut:
            b["gundem_kaynagi"] = "yazili"

    if "duzeltmeler" in yama:
        if yama["duzeltmeler"] is None:
            b["duzeltmeler"] = []
            degisen.append("düzeltmeler silindi")
        else:
            b["duzeltmeler"] = duzeltmeleri_dogrula(yama["duzeltmeler"])
            degisen.append(f"duzeltmeler ({len(b['duzeltmeler'])} kayıt)")

    # YAZI DAMGASI. `yorum_zamani` yalnız gün taşıyordu ve yalnız yorum
    # değişince atılıyordu; sayfa saat bekliyordu. Her uygulanan yama dilimli
    # bir an ve artan bir sürüm numarası bırakır: okur künyede yazının saatini,
    # denetim ise ölçüm ile yazı arasındaki sırayı görür.
    if degisen:
        b["yazi_zamani"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        b["yazi_surumu"] = int(b.get("yazi_surumu") or 0) + 1
        b.setdefault("ilk_yazi_zamani", b["yazi_zamani"])

    return b, degisen


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("yama", help="yama JSON dosyası ('-' → standart girdi)")
    ap.add_argument("--tarih", default=None, help="YYYY-MM-DD (varsayılan: bugün)")
    ap.add_argument("--yazma", action="store_true", help="dosyaya yazma, ne olacağını göster")
    # 26.08.2026 kazasının mekanik sigortası: yazı 04:31'de yazıldı, ölçüm
    # 05:01'de yeniden kuruldu ve sayfa ölçülmeyen sayıları anlatır oldu.
    # Yazan taraf bülteni OKUDUĞU andaki `olusturma` damgasını buraya verir;
    # yamayı uygularken damga değişmişse ölçüm yazıdan sonra yenilenmiş
    # demektir ve yama reddedilir — metin güncel ölçüme göre gözden geçirilir.
    ap.add_argument("--damga", default=None,
                    help="bülteni okuduğun andaki `olusturma` değeri; "
                         "değişmişse yama reddedilir")
    # Sigorta damga verilmese de çalışmalı. Sebebi mimari: yazı katmanını
    # ateşleyen rutinin metni claude.ai hesabında durur, depodaki rehber
    # (YAZIM.md) ise burada; ikisi ayrı hızlarda değişiyor ve bir aracı rutin
    # metnini DEĞİŞTİREMİYOR. Rehber "--damga ver" derken rutin metni damgasız
    # çağrı gösteriyordu — sigorta sessizce devre dışıydı ve 26.08 kazası tam
    # oradan çıktı. Damgayı zorunlu kılmak kaymayı görünür yapar ama bu sefer
    # de rutini düşürür; doğrusu, damga yokken sigortayı BAŞKA BİR ÖLÇÜYLE
    # sürdürmek.
    #
    # O ölçü yama dosyasının değiştirilme zamanı: yazan taraf yamayı en son
    # yazar, yani dosyanın mtime'ı "yazı bitti" anına yakındır. Bültenin
    # `olusturma` damgası ondan SONRAYSA ölçüm yazı bittikten sonra yeniden
    # kurulmuş demektir — damga kıyasının yakaladığı durumun ta kendisi.
    # Zayıf tarafı: yamanın yazıldığı an, bültenin OKUNDUĞU andan sonradır,
    # yani aradaki dar pencereyi kaçırabilir. Bu yüzden açık damga hâlâ
    # tercih edilendir ve rehber onu ister; mtime yalnız TABANDIR.
    ap.add_argument("--damgasiz", action="store_true",
                    help="her iki sigortayı da bilerek atla (ölçümün "
                         "yenilenmediğini kendin doğruladıysan)")
    # DENETİM KAPISI. Rehber "denetle, sonra kaydet" der; ama denetim diskteki
    # dosyayı okuduğu için yazı henüz dosyada yokken koşuyordu ve yazılmış
    # bültende hiçbir ARAÇ denetimi dayatmıyordu — yalnız rehber metni istiyordu.
    # Şimdi yama bellekte uygulanır, denetim o sonuç üzerinde koşar; ENGEL varsa
    # dosya YAZILMAZ (çıkış 5). --denetle: yalnız sına, yazma. --engelle-yaz:
    # engelleri bilerek geçip yaz (denetim çıktısı JSON'a işlenir, sayfa görmez).
    ap.add_argument("--denetle", action="store_true",
                    help="yamayı bellekte uygula, denetimi koştur, dosyaya YAZMA")
    ap.add_argument("--engelle-yaz", action="store_true",
                    help="denetim engel üretse de yaz (bilinçli istisna; engeller "
                         "JSON'da 'denetim' alanına kaydedilir)")
    a = ap.parse_args()

    ham = sys.stdin.read() if a.yama == "-" else Path(a.yama).read_text(encoding="utf-8")
    try:
        yama = json.loads(ham)
    except ValueError as e:
        print(f"yama okunamadı: {e}", file=sys.stderr)
        return 2

    t = a.tarih or date.today().isoformat()
    hedef = BULTEN / f"{t}.json"
    if not hedef.exists():
        print(f"bülten yok: {hedef.name} — önce 'python3 bulten.py' koşmalı", file=sys.stderr)
        return 2

    # Birleştirme sürücüsünü kur. Bülten dosyasına hem otomatik koşu hem yazı
    # katmanı dokunuyor; sürücü .git/config'de durduğu ve depoyla taşınmadığı
    # için her koşuda yeniden yazılmalı. Eskiden yalnız bulten.py kuruyordu,
    # ama yazı katmanı bülten zaten üretilmişse bulten.py'yi hiç çağırmıyor —
    # o durumda push sırasındaki çakışma çözümsüz kalıyordu.
    try:
        sys.path.insert(0, str(BURASI))
        import birlestir
        birlestir.kur()
    except Exception:
        pass                       # sürücü kurulamazsa yazma işlemi etkilenmez

    mevcut = json.loads(hedef.read_text(encoding="utf-8")).get("olusturma", "")
    if a.damgasiz:
        print("(damga sigortası atlandı — --damgasiz)", file=sys.stderr)
    elif a.damga:
        if mevcut != a.damga:
            print(f"YAMA REDDEDİLDİ: ölçüm katmanı yazı yazılırken yenilenmiş.\n"
                  f"  okuduğun damga : {a.damga}\n"
                  f"  dosyadaki damga: {mevcut}\n"
                  "Bülteni yeniden oku, metni güncel ölçüme göre gözden geçir ve "
                  "yeni damgayla tekrar uygula.", file=sys.stderr)
            return 3
    elif a.yama != "-":
        # Damga verilmedi: yama dosyasının mtime'ıyla taban sigorta. İki taraf
        # da UTC'ye çevrilir — eski hâli yerel saati dilimsiz UTC damgayla
        # kıyaslıyordu ve dilim farkı kadar kördü.
        yazildi = dt.datetime.fromtimestamp(Path(a.yama).stat().st_mtime, tz=dt.timezone.utc)
        try:
            olcum = dt.datetime.fromisoformat(mevcut)
            if olcum.tzinfo is None:
                olcum = olcum.replace(tzinfo=dt.timezone.utc)
        except ValueError:
            olcum = None
        if olcum and olcum > yazildi:
            print(f"YAMA REDDEDİLDİ: ölçüm katmanı yama yazıldıktan SONRA "
                  f"yeniden kurulmuş.\n"
                  f"  yama yazıldı : {yazildi:%Y-%m-%d %H:%M:%S}\n"
                  f"  ölçüm damgası: {mevcut}\n"
                  "Bülteni yeniden oku, metni güncel ölçüme göre gözden geçir, "
                  "yamayı yeniden yaz ve --damga ile uygula.", file=sys.stderr)
            return 3
        print(f"(damga verilmedi; taban sigorta geçti — ölçüm {mevcut}, "
              f"yama {yazildi:%H:%M:%S}. Açık damga için --damga kullan.)",
              file=sys.stderr)

    b, degisen = uygula(hedef, yama)
    if not degisen:
        print("yamada yazılacak içerik yok")
        return 0

    # Denetim, yama uygulanmış BELLEKTEKİ bülten üzerinde koşar.
    import denetim
    d = denetim.Denetim(b)
    kod = d.kos()
    if a.denetle:
        print("(--denetle: dosyaya yazılmadı) " + " · ".join(degisen))
        return kod
    if kod and not a.engelle_yaz:
        print(f"\nYAZMA REDDEDİLDİ: denetim {len(d.engel)} ENGEL üretti. Engelleri giderip "
              "yamayı yeniden uygula; bilinçli istisna için --engelle-yaz.", file=sys.stderr)
        return 5
    if kod:
        b["denetim"] = {"engel": d.engel, "uyari": d.uyari,
                        "zaman": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                        "not": "engellere rağmen --engelle-yaz ile yazıldı"}
        print("::warning::engellere rağmen yazılıyor (--engelle-yaz); engeller JSON'a işlendi.")
    if a.yazma:
        print("(yazılmadı) " + " · ".join(degisen))
        return 0
    hedef.write_text(json.dumps(b, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{hedef.name} güncellendi: " + " · ".join(degisen))

    # GECİKME KAYDI — yazmanın YAN ETKİSİ, ayrı bir adım değil.
    #
    # Rutinin kaçınamayacağı tek araç bu dosya: bültenin yazılmasının başka bir
    # yolu yok ve rutin metni onu adıyla çağırıyor. Hiçbir bayrak, hiçbir
    # argüman gerekmiyor; rutin metni hiç değişmese de kayıt atlanamaz. Sözün
    # (yayın takviminden) tutulup tutulmadığı, ancak KAYIT birikirse
    # sınanabilir bir eşiğe dönüşür.
    #
    # try/except ŞART VE KAPI DEĞİL: gecikme ölçümündeki bir kusur bültenin
    # yazılmasını düşürmemeli. Dosya zaten diske yazıldı; buradan sonrası
    # yalnız defter.
    #
    # Kayıt `uygula()` içinde DEĞİL burada duruyor (planın işaret ettiği satır
    # orasıydı): `uygula()` --denetle ve --yazma kiplerinde de koşuyor ve
    # denetim ENGEL ürettiğinde dosya YAZILMIYOR. Oradan yazılan bir satır,
    # hiç gerçekleşmemiş bir yazıyı deftere geçirirdi — "uydurma yok".
    try:
        sys.path.insert(0, str(BURASI))
        import gecikme
        satir = gecikme.defter_yaz(KOK, b, t)
        if satir:
            print("  " + gecikme.ozet_satiri(satir))
    except Exception as ex:                                    # noqa: BLE001
        print(f"(gecikme kaydı yazılamadı: {ex})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
