#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Brooks indikatörünün ÖLÇÜM aracı — sayfadaki örnekleri üretir.

NEDEN VAR. İndikatör sayfasındaki "nasıl kullanılır" bölümü uydurma barlarla
anlatılamaz (CLAUDE.md: uydurma yok). Örnekler GERÇEK OHLC'den ölçülür ve
ölçen kod burada durur.

KURALLARIN KENDİSİ BURADA DEĞİL. Pine'ın Python replikasyonu okurun da
indirebildiği ayrı bir dosyadadır (`site/public/indikatorler/brooks_referans.py`)
ve bu araç onu İÇE AKTARIR. İki uygulama tutmak, aynı kuralı iki yerde
yazmaktır ve bu depoda ölçülmüş bir kusur sınıfıdır: iki liste bir gün
sessizce ayrışır. Referansın kendi kapısı da eşikleri `.pine` dosyalarıyla
karşılaştırır, yani zincir üç ucundan da bağlı.

VERİ KAYNAĞI. Bu oturumlardan Yahoo'ya çıkılamıyor (proxy 403). Barlar
depodaki teknik bülten figürlerinin İÇİNDEN okunuyor: site/public/teknik/
altındaki Plotly HTML'leri mum grafiğinin OHLC dizilerini gömülü taşır ve
o diziler teknik/olc.py'nin kapanmış-bar disiplininden geçmiştir.

KAPSAM. Kurallar ölçek bağımsız kurulur; dersin eşikleri 5 dakikalık barda
kalibre edilmiştir. Burada ölçülen barlar 1 saatlik, 4 saatlik ve günlüktür
ve bu çıktının künyesine YAZILIR — örnek, dersin kalibrasyon ölçeği değildir.

Kullanım:
    python3 site/tools/brooks_ornek.py            # ölçer, JSON yazar
    python3 site/tools/brooks_ornek.py --denetle  # yalnız kapıları koşturur
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path

BURASI = Path(__file__).resolve().parent
SITE = BURASI.parent
# public/ ne konursa SİTEYE KOPYALANIR. Referans dosyasını oradan içe aktarmak
# yanına bir __pycache__ bırakır ve o dizin de yayına gider — derlenmiş bytecode
# okura sunulmaz. İçe aktarmadan ÖNCE kapatılır; sonra kapatmak geç kalır.
sys.dont_write_bytecode = True
sys.path.insert(0, str(BURASI))
sys.path.insert(0, str(SITE / "public" / "indikatorler"))
import brooks_referans as R                                      # noqa: E402
from brooks_referans import (                                    # noqa: E402
    FiyatPaneli, RejimPanosu, Seri, ema, en_dusuk, en_yuksek,
    gelecege_bakma_sinamasi, pine_sabitleri,
)
KOK = SITE.parent
TEKNIK = SITE / "public" / "teknik"
PINE_FH = SITE / "public" / "indikatorler" / "brooks-fiyat-hareketi.pine"
PINE_RP = SITE / "public" / "indikatorler" / "brooks-rejim-panosu.pine"
CIKTI = SITE / "src" / "data" / "brooks_ornek.json"


# ── Barları depodaki figürlerin içinden okuma ───────────────────────────────
_NEWPLOT = re.compile(r'Plotly\.newPlot\(\s*"[^"]+",\s*(\[.*?\]),\s*\{', re.S)


@dataclass(frozen=True)
class Kaynak:
    """Bir figürden okunan seri + kimliği. Kural katmanı kimliği bilmez."""

    slug: str
    dilim: str
    seri: Seri

    @property
    def anahtar(self) -> str:
        return f"{self.slug}-{self.dilim}"


def bar_oku(yol: Path) -> Kaynak:
    m = _NEWPLOT.search(yol.read_text(encoding="utf-8"))
    if not m:
        raise SystemExit(f"ENGEL · {yol.name} içinde Plotly verisi bulunamadı.")
    izler = json.loads(m.group(1))
    mum = next((t for t in izler if t.get("type") == "candlestick"), None)
    if mum is None:
        raise SystemExit(f"ENGEL · {yol.name} içinde mum izi yok.")
    slug, _, dilim = yol.stem.partition("-")
    seri = Seri(mum["open"], mum["high"], mum["low"], mum["close"], mum["x"])
    # Eksik gözlem sessizce sıfır olmasın (CLAUDE.md: çizim katmanı da veri doldurur).
    for ad, dizi in (("open", seri.o), ("high", seri.h), ("low", seri.l), ("close", seri.c)):
        if any(v is None or (isinstance(v, float) and math.isnan(v)) for v in dizi):
            raise SystemExit(f"ENGEL · {yol.name} · {ad} dizisinde boş gözlem var.")
    return Kaynak(slug, dilim, seri)


# ── Gövde kapısı: bir seri GERÇEK mum taşımıyorsa örneğe giremez ────────────
#
# ÖLÇÜLDÜ (16 seri, 5.354 bar). Doji payı iki kümede toplanıyor ve aralarında
# geniş bir boşluk var: sağlıklı serilerde 0,088–0,145 · bozuk serilerde
# 0,954–0,977. Bozuk üçlüde medyan gövde/menzil 0,000–0,014, yani bar
# ANATOMİSİ diye bir şey yok — açılış ile kapanış aynı kotasyondan geliyor.
# Bu, indikatörün kusuru değil BESLEMENİN kusurudur ve her ölçüsünü çürütür:
# bar sınıfı, always-in, kalite, hepsi gövdeden okunur.
#
# Eşik ölçülen boşluğun ortasına konur; sezgiyle değil. Dışlanan seri
# SİLİNMEZ, künyeye SEBEBİYLE yazılır (CLAUDE.md: dışlama işaretlemektir).
GOVDE_KAPISI = 0.50


def govde_kunyesi(s: Seri) -> dict:
    oran = []
    for i in range(len(s)):
        m = s.h[i] - s.l[i]
        oran.append(abs(s.c[i] - s.o[i]) / m if m > 0 else 0.0)
    sirali = sorted(oran)
    doji = sum(1 for v in oran if v <= 0.10) / len(oran)
    return {
        "doji_payi": round(doji, 3),
        "medyan_govde": round(sirali[len(sirali) // 2], 3),
        "sifir_govde_payi": round(sum(1 for v in oran if v == 0) / len(oran), 3),
        "gecti": doji < GOVDE_KAPISI,
    }


# ── Duman sınaması ──────────────────────────────────────────────────────────
def _duman() -> None:
    """Üç kapı: referansın kendi sınaması, EŞİK AYRIŞMASI ve gövde kapısı.

    Kuralların kendi sınaması burada TEKRARLANMAZ — referans dosyası onu
    kendisi taşır ve bu araç onu çağırır. Bir kuralı iki yerde sınamak, onu
    iki yerde yazmakla aynı kusurdur: biri bir gün güncellenmez."""
    hata: list[str] = R.kendini_sina()

    # Pine ile Python AYNI eşiklerde mi — iki uygulama sessizce ayrışmasın.
    hata += [f"eşik ayrışması · {x}" for x in R.pine_ile_karsilastir(PINE_FH, PINE_RP)]

    # Ve AYNI ÖLÇÜLERİ taşıyor mu. Eşik kapısı bunu göremez: yeni bir eşik
    # getirmeyen bir ölçü Pine'a hiç taşınmadan da o kapıyı geçer.
    hata += [f"ölçü kapsamı · {x}" for x in R.olcu_kapsami(PINE_FH, PINE_RP)]

    # Pine'ın derleyicisi bu depoda YOK; statik denetim onun yerine geçmez
    # ama bu depoda gerçekten yapılmış beş hatayı bir daha yapmayı engeller.
    import pine_denetle                                          # noqa: E402
    for y in sorted((SITE / "public" / "indikatorler").glob("*.pine")):
        hata += pine_denetle.denetle(y)

    # SİTEDEKİ KOD ile DEPODAKİ KOD aynı mı. Sayfa kodu `?raw` ile aldığı
    # için "sayfada görünen" ile "indirilen" yapısal olarak aynıdır; ama
    # derlenmiş çıktı bir ÖNCEKİ derlemeden kalmış olabilir ve o zaman site
    # eski sürümü sunar. Kaynak kod değiştiğinde derleme de yenilenmeli.
    dist = SITE / "dist" / "indikatorler"
    if dist.exists():
        import hashlib
        for kaynak in sorted(y for y in (SITE / "public" / "indikatorler").iterdir()
                             if y.is_file()):
            hedef = dist / kaynak.name
            if not hedef.exists():
                hata.append(f"site kopyası eksik: {kaynak.name} — derleme yenilenmeli")
            elif hashlib.md5(kaynak.read_bytes()).digest() != hashlib.md5(hedef.read_bytes()).digest():
                hata.append(f"site kopyası ESKİ: {kaynak.name} — derleme kaynaktan geride, "
                            f"okur eski sürümü indirir")

    # public/ altında derlenmiş bytecode kalmasın — oradaki her şey yayına gider.
    for art in (SITE / "public").rglob("__pycache__"):
        hata.append(f"public altında derlenmiş bytecode: {art.relative_to(SITE)} — yayına gider")

    # Gövde kapısı ilan ettiği iki hâlde de doğru karar vermeli.
    saglikli = R._sentetik(200)
    if not govde_kunyesi(saglikli)["gecti"]:
        hata.append("gövde kapısı sağlıklı seriyi dışladı")
    n = len(saglikli)
    govdesiz = Seri(list(saglikli.c), [c + 1 for c in saglikli.c],
                    [c - 1 for c in saglikli.c], list(saglikli.c), None)
    if govde_kunyesi(govdesiz)["gecti"]:
        hata.append("gövde kapısı açılış=kapanış serisini geçirdi")

    if hata:
        print("DUMAN DÜŞTÜ:", file=sys.stderr)
        for h in hata:
            print("  ✗", h, file=sys.stderr)
        raise SystemExit(1)
    print("duman · referans sınaması + eşik ayrışması + gövde kapısı GEÇTİ")


# ── Örnek arama ─────────────────────────────────────────────────────────────
ENSTRUMAN_AD = {
    "eurusd": "EUR/USD",
    "dxy": "Dolar endeksi (DXY)",
    "usdchf": "USD/CHF",
    "xu100": "BIST 100",
    "us10y": "ABD 10 yıllık getiri",
    "us2y": "ABD 2 yıllık getiri",
}
DILIM_AD = {"s1": "1 saatlik", "s4": "4 saatlik", "gunluk": "günlük"}


def _bar_kunye(fp: FiyatPaneli, i: int, ond: int) -> dict:
    """Bar künyesi — ORAN, sayfaya basılan YUVARLANMIŞ fiyattan hesaplanır.

    Sayfadaki OHLC yuvarlanmış, oran ham değerden gelirse okur aritmetiği
    yeniden kurduğunda BAŞKA bir sayı bulur ve hangisinin doğru olduğunu
    ayırt edemez. Bu depoda bir kez ölçülmüş bir kusur sınıfı: yayımlanan
    bir sayı, yayımlanan öbür sayılardan yeniden üretilebilmelidir."""
    s = fp.s
    o, h, l, c = (round(s.o[i], ond), round(s.h[i], ond),
                  round(s.l[i], ond), round(s.c[i], ond))
    menzil = h - l
    kunye = {
        "zaman": s.zaman[i], "o": o, "h": h, "l": l, "c": c,
        "govde_oran": round(abs(c - o) / menzil, 3) if menzil > 0 else 0.0,
        "sinif": fp.sinif(i),
        "ortusme": 0.0,
    }
    if i > 0:
        oh, ol = round(s.h[i - 1], ond), round(s.l[i - 1], ond)
        onceki = oh - ol
        if onceki > 0:
            kunye["ortusme"] = round(max(0.0, min(h, oh) - max(l, ol)) / onceki, 3)
    return kunye


def ornekleri_ara(kaynaklar: list[Kaynak]) -> dict:
    bulgu: dict = {"flip": [], "kalite": [], "ortusme_reddi": [], "yasak": [], "rejim": [], "sayim": {}}
    for kay in kaynaklar:
        s = kay.seri
        ond = 4 if max(s.c) < 10 else 2 if max(s.c) < 1000 else 0
        fp = FiyatPaneli(s)
        rp = RejimPanosu(s)
        yon, donus, onaysiz = fp.always_in()
        gap = fp.gap_sayaci()
        ad = f"{ENSTRUMAN_AD.get(kay.slug, kay.slug)} · {DILIM_AD.get(kay.dilim, kay.dilim)}"

        # ① always-in dönüşleri — dönüşü kuran ÜÇ bar birlikte yazılır
        for i in donus:
            if i < 3:
                continue
            bulgu["flip"].append({
                "ad": ad, "yon": "long" if yon[i] == 1 else "short",
                "barlar": [_bar_kunye(fp, j, ond) for j in (i - 2, i - 1, i)],
                "rejim": (rp.olcu(i) or {}).get("rejim"),
                "yon_filtresi": fp.yon_filtresi(i),
            })

        # ② sinyal barı kalitesi + ③ örtüşme reddi + ④ yön filtresi yasağı
        for i in range(max(10, int(R.SABIT_FH["kapanisPenc"])), len(s)):
            for boga in (True, False):
                if not fp.donus_bari(i, boga):
                    continue
                nit = fp.nitelikler(i, boga)
                k = sum(nit.values())
                filtre = fp.yon_filtresi(i)
                yasak = (filtre == "yalnız AL" and not boga) or (filtre == "yalnız SAT" and boga)
                kayit = {
                    "ad": ad, "yon": "boğa" if boga else "ayı", "kalite": k,
                    "nitelikler": nit, "bar": _bar_kunye(fp, i, ond),
                    "onceki": _bar_kunye(fp, i - 1, ond),
                    "always_in": {1: "long", -1: "short", 0: "—"}[yon[i]],
                    "yon_filtresi": filtre, "gap": gap[i],
                    "rejim": (rp.olcu(i) or {}).get("rejim"),
                }
                if k == 4:
                    bulgu["kalite"].append(kayit)
                if not nit["n3"] and k >= 2:
                    bulgu["ortusme_reddi"].append(kayit)
                if yasak and k >= 3:
                    bulgu["yasak"].append(kayit)
                # Hangi nitelik en sık bağlıyor? Sayfa "örtüşme en sık bağlayan
                # niteliktir" gibi bir SIRALAMA cümlesi kuracaksa dört niteliğin
                # düşme sayısı yan yana ölçülmüş olmalı — tek niteliğin sayısı
                # sıralama kurmaz. İki kova: kalite ≥ 2 (etiketlenen barlar) ve
                # tam 3/4 (tek niteliğin bağladığı barlar).
                for kova, sart in (("nitelik_dusme_k2", k >= 2), ("nitelik_dusme_k3", k == 3)):
                    if sart:
                        nd = bulgu["sayim"].setdefault(f"_{kova}", {"toplam": 0, "n1": 0, "n2": 0, "n3": 0, "n5": 0})
                        nd["toplam"] += 1
                        for n_ad, n_var in nit.items():
                            if not n_var:
                                nd[n_ad] += 1

        # ⑤ rejim pencereleri — HEPSİ tutulmaz (binlerce pencere), dağılımı
        #    sayılır ve yalnız iki UÇ pencere adıyla saklanır.
        dagilim = {"BANT": 0, "ara": 0, "trend": 0}
        uclar: list[dict] = []
        for i in range(len(s)):
            o = rp.olcu(i)
            if o is None:
                continue
            dagilim[o["rejim"]] += 1
            uclar.append(dict(o, ad=ad, zaman=s.zaman[i], bas=s.zaman[i - rp.pencere + 1]))
        if uclar:
            enb = max(uclar, key=lambda x: (x["n"], -x["net_aralik"]))
            ent = min(uclar, key=lambda x: (x["n"], -x["net_aralik"]))
            bulgu["rejim"].append({"ad": ad, "dagilim": dagilim,
                                   "pencere": len(uclar), "en_bant": enb, "en_trend": ent})

        # ── Yeni ölçülerin SIKLIĞI — sayfadaki her oran buradan doğrulanır
        kal = collections.Counter()
        kad = collections.Counter()
        oz = collections.Counter()
        cev_flip: list[int] = []
        cev_hep: list[int] = []
        dset = {i for i in donus if i >= 3}
        for i in range(int(R.SABIT_FH["maUzunluk"]), len(s)):
            k = fp.kalip(i)
            if k:
                kal[k] += 1
            kad[fp.cevirme_kademesi(i)] += 1
            c = fp.cevirme(i)["kapanis"]
            cev_hep.append(c)
            if i in dset:
                cev_flip.append(c)
            if fp.tirasli(i):
                oz[fp.tirasli(i)] += 1
            if fp.iki_barlik_donus(i):
                oz["iki barlık dönüş"] += 1
            m = fp.mikro_cift(i)
            if m:
                oz[m] += 1
            b = fp.bar_boyu(i)
            if b:
                oz[b] += 1
            if abs(fp.mikro_kanal(i)) >= 5:
                oz["mikro kanal ≥5"] += 1
            if fp.iptal_kurali(i)["iptal"]:
                oz["beş bar iptal"] += 1
            # Orta nokta ölçütü KOŞULLU ölçülür. Koşulsuz sorulduğunda
            # barların neredeyse tamamı bir yönde geçer — çünkü her bar
            # önceki barın orta noktasının bir tarafında kapanır. Ölçü ancak
            # "bu bar bir DÖNÜŞ barı, peki kabul mü ret mi" diye sorulunca
            # ayırt eder; kuralın sorduğu soru da budur. Koşulsuz pay da
            # SAYILIR ki sayfadaki oran dosyadan doğrulansın.
            if fp.orta_nokta_olcutu(i, True) or fp.orta_nokta_olcutu(i, False):
                oz["orta nokta koşulsuz geçen"] += 1
            for yon, ad2 in ((True, "boğa"), (False, "ayı")):
                if fp.donus_bari(i, yon):
                    oz[f"dönüş barı ({ad2})"] += 1
                    if fp.orta_nokta_olcutu(i, yon):
                        oz[f"orta nokta KABUL ({ad2})"] += 1
        bulgu.setdefault("yeni_olcu", {})[ad] = {
            "olculen_bar": len(s) - int(R.SABIT_FH["maUzunluk"]),
            "kalip": dict(kal), "cevirme_kademesi": dict(kad), "ozellik": dict(oz),
            "cevirme_medyan_hep": sorted(cev_hep)[len(cev_hep) // 2] if cev_hep else None,
            "cevirme_medyan_flip": sorted(cev_flip)[len(cev_flip) // 2] if cev_flip else None,
            "flip_bar": len(cev_flip),
        }

        bulgu["sayim"][ad] = {
            "bar": len(s),
            "bas": s.zaman[0],
            "son": s.zaman[-1],
            "flip": len([i for i in donus if i >= 3]),
            "kalite4": len([k for k in bulgu["kalite"] if k["ad"] == ad]),
            "azami_gap": max(gap),
            "onaysiz_dizi": len(onaysiz),
        }
    # Kovaların TAMAMI dosyaya girmez; sayısı yazılır, örneği kırpılır —
    # ölçüm kaydı okunabilir kalmalı ki sayfadaki her sayı buradan doğrulansın.
    for ad in ("ortusme_reddi", "yasak"):
        bulgu["sayim"][f"_{ad}_toplam"] = len(bulgu[ad])
        bulgu[ad] = sorted(bulgu[ad], key=lambda k: (-k["kalite"], -k["bar"]["ortusme"]))[:12]
    return bulgu


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--denetle", action="store_true", help="yalnız kapıları koştur")
    a = ap.parse_args()

    _duman()
    if a.denetle:
        return

    yollar = sorted(TEKNIK.glob("*.html"))
    if not yollar:
        raise SystemExit(f"ENGEL · {TEKNIK} altında figür yok.")
    hepsi = [bar_oku(y) for y in yollar]
    govde = {k.anahtar: govde_kunyesi(k.seri) for k in hepsi}
    gecen = [k for k in hepsi if govde[k.anahtar]["gecti"]]
    dislanan = {k: v for k, v in govde.items() if not v["gecti"]}
    if not gecen:
        raise SystemExit("ENGEL · gövde kapısından geçen seri kalmadı.")
    bulgu = ornekleri_ara(gecen)
    bulgu["kunye"] = {
        "kaynak": "site/public/teknik/*.html (teknik/olc.py'nin kapanmış-bar disiplininden geçmiş OHLC)",
        "esik_kaynagi": {PINE_FH.name: pine_sabitleri(PINE_FH),
                         PINE_RP.name: pine_sabitleri(PINE_RP)},
        "govde_kapisi": GOVDE_KAPISI,
        "govde": govde,
        "dislanan": dislanan,
        "seri": len(gecen),
        "bar": sum(len(k.seri) for k in gecen),
    }
    CIKTI.parent.mkdir(parents=True, exist_ok=True)
    CIKTI.write_text(json.dumps(bulgu, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"yazıldı · {CIKTI.relative_to(KOK)}")
    for ad, v in dislanan.items():
        print(f"  DIŞLANDI · {ad:26s} doji payı {v['doji_payi']:.3f} · medyan gövde/menzil "
              f"{v['medyan_govde']:.3f} — bu besleme gerçek mum gövdesi taşımıyor")
    for ad, s in bulgu["sayim"].items():
        if not isinstance(s, dict) or ad.startswith("_"):
            continue
        print(f"  {ad:34s} {s['bar']:4d} bar  flip {s['flip']:3d}  4/4 {s['kalite4']:3d}  azami gap {s['azami_gap']:3d}")


if __name__ == "__main__":
    main()
