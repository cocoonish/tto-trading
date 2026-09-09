#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TÜFEX ve başabaş enflasyon — hesap katmanı.

Carry hattıyla aynı ilke: kendi veri kaynağına gitmez. Başabaş, reel getiri ve
risk primi serileri DIBS hattının, aylık TÜFE ise Enflasyon hattının depoya
yazdığı CSV'lerden okunur. Sayfadaki başabaş, DİBS sayfasındaki başabaşla aynı
seridir; olamayacağı bir mimari kurulmamıştır.

Üç katman:

  başabaş vs anket   Piyasanın fiyatladığı enflasyon (başabaş) ile anketin
                     AYNI UFKA eşlenmiş ortalaması. Fark = risk primi + likidite
                     primi; DIBS hattı bunu prim_* kolonlarında zaten üretir.
  reel getiri        TÜFEX reel eğrisinin tarihçesi.
  mevsimsellik       Aylık TÜFE'nin takvim deseni: ham eksi mevsimsellikten
                     arındırılmış fark, ay bazında ortalanır. Kısa vadeli
                     başabaş okumasının neden ayına göre düzeltilmesi
                     gerektiğinin ölçüsü.

SAAT SÖZLEŞMESİ — bu dosyada üç ritim yan yana durur ve her anahtar KENDİ
ritminin saatini taşır (ortak/bicim ile aynı yazım):
  · günlük bacaklar (başabaş, reel, prim)   → GG.AA.YYYY, serinin son dolu günü
  · anket bacakları (anket_*, pka_*)        → AA.YYYY, YÜRÜRLÜKTEKİ anketin ayı
  · mevsim deseni (mevsim_*)                → AA.YYYY, pencerenin son TÜFE ayı
Hattın ana saati (`_tarih`) yalnız GÜNLÜK bacakların en yenisidir; aylık bir
bacak ana saati ne ileri ne geri çeker.

09.09.2026'da ölçüldü: anket_*_tarih alanları 08.09.2026 yazıyordu — anket
serisi günlüğe basamak olarak yayıldığı için "son dolu gün" bugündü, oysa
sayı 20.08.2026'dan beri yürürlükte olan AĞUSTOS anketinden geliyor; pka_12a,
pka_24a ve mevsim_* alanlarının saati hiç yoktu ve sayfa onları hattın günlük
saatiyle etiketliyordu. Bir gözlemin saati, dosyada göründüğü gün değil,
ölçüldüğü dönemdir.
"""
from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import sys

import pandas as pd

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent.parent
DIBS = KOK / "Aktarılacak Projeler" / "DIBS" / "data"
ENF = KOK / "Aktarılacak Projeler" / "Enflasyon" / "data"

VADELER = ("1y", "2y", "3y", "5y", "7y")
# Mevsimsel desen penceresi: son 10 yıl. Daha uzunu rejim değişimlerini
# (2003 bazlı seri, farklı sepetler) desene karıştırır.
MEVSIM_YIL = 10
# Anket ayının ay adı (etiket AYRI anahtarda: saat anahtarına ay adı yazılmaz).
AY_AD = ("Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
         "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık")

# Anket serilerinin günlük eksende BASAMAK attığı günü bulmak için bakılan
# sütunlar: bir ayın ortalaması bir öncekiyle aynı çıkabilir (05→06.2026'da
# 23,82→23,81 — bir yüzdelik daha yakın olsaydı basamak görünmezdi), o yüzden
# tek sütuna değil hepsine birden bakılır.
PKA_SUTUNLAR = ("pka_12a", "pka_24a", "pka_5y", "pka_12a_n")
# DİBS hattının ilan ettiği yayım günü ilanı bulunamazsa basamak günlerinden
# ölçülür; kaç basamağa bakılacağı.
PKA_BASAMAK_PENCERE = 12

# ── ŞEKİL SAAT DEFTERİ — figür → (bacak etiketi, saat anahtarı) ─────────────
# Tek liste: çizim de özet de buradan okur; iki liste bir gün sessizce ayrışır.
# Her figürün damgası BAĞLAYICI bacaktır (en eski); ama iki bacak farklı
# cinsteyse (günlük piyasa × aylık anket) ya da birbirinden DAMGA_AYRIM_GUN'den
# uzaksa tek gün ikisinden biri hakkında yalan söyler — o zaman damga iki
# parçalı yazılır ve defterde null durur (sayfa sınavı defterde tek bir tarih
# ister). Ölçüldü (09.09.2026): Şekil 02b'nin 3y izi 12.06.2026'da donmuş
# (TÜFEX itfa boşluğu), 2y ve 7y bugünde — 88 gün; "en eski" kuralı düz
# uygulansaydı bütün figür üç ay bayat görünürdü, en yenisi yazılsaydı donmuş
# iz bugünün verisi sanılırdı.
SEKILLER: dict[str, tuple[tuple[str, str], ...]] = {
    "basabas_anket.html": (("piyasa", "basabas_2y_tarih"), ("piyasa", "basabas_7y_tarih"),
                           ("anket", "anket_2y_tarih"), ("anket", "anket_7y_tarih")),
    "prim_kesit.html": tuple((v, f"prim_{v}_tarih") for v in VADELER),
    "prim_tarihce.html": (("2y", "prim_2y_tarih"), ("3y", "prim_3y_tarih"),
                          ("7y", "prim_7y_tarih")),
    "reel_tarihce.html": (("1y", "reel_1y_tarih"), ("2y", "reel_2y_tarih"),
                          ("7y", "reel_7y_tarih")),
    "mevsim.html": (("", "mevsim_tarih"),),
}
DAMGA_AYRIM_GUN = 7


def _bicim():
    try:
        import bicim
    except ImportError:
        sys.path.insert(0, str(KOK / "ortak"))
        import bicim
    return bicim


def yukle() -> pd.DataFrame:
    m = pd.read_csv(DIBS / "metrik.csv", parse_dates=["tarih"]).set_index("tarih")
    kolonlar = ([f"be_{v}" for v in VADELER] + [f"r{v}" for v in VADELER]
                + [f"prim_{v}" for v in VADELER]
                + [f"pka_ort_{v}" for v in VADELER if f"pka_ort_{v}" in m.columns]
                + list(PKA_SUTUNLAR) + ["n1y", "n2y"])
    return m[[c for c in kolonlar if c in m.columns]]


def tufe_aylik() -> pd.DataFrame:
    """Enflasyon hattının aylık TÜFE serisi (ham ve arındırılmış), son MEVSIM_YIL yıl."""
    m = pd.read_csv(ENF / "metrik.csv", parse_dates=["tarih"])
    t = m[m["seri"] == "tufe"].set_index("tarih").sort_index()
    return t[t.index >= t.index.max() - pd.DateOffset(years=MEVSIM_YIL)]


def mevsim_deseni(t: pd.DataFrame | None = None) -> pd.DataFrame:
    """Ay bazında ortalama (ham − SA) aylık TÜFE farkı, son MEVSIM_YIL yıl.

    Pozitif fark o ayın mevsimsel olarak PAHALI olduğunu söyler (ham > SA):
    kısa TÜFEX carry'si o ayda görünürde yüksektir ama bu enflasyon haberi
    değil, takvimdir.
    """
    t = tufe_aylik() if t is None else t.copy()
    t["fark"] = t["aylik_ham"] - t["aylik_sa"]
    d = t.groupby(t.index.month)["fark"].agg(["mean", "std", "count"])
    d.index.name = "ay"
    return d.round(3)


def anket_basamagi(d: pd.DataFrame) -> pd.Timestamp | None:
    """Günlük eksende yürürlükteki anketin BAŞLADIĞI gün.

    Anket serileri DİBS hattında aylık değerin yayım gününden itibaren ileri
    doldurulmasıyla kurulur; bu yüzden serinin son dolu günü anketin saati
    DEĞİLDİR — o gün anketin hâlâ yürürlükte olduğu gündür. Anketin kendi saati,
    değerin en son DEĞİŞTİĞİ gündür; ay da o günün ayıdır (yayım aynı ayın
    içinde). Ölçüldü (09.09.2026): 2025-10'dan 2026-08'e her basamak ayın
    20'sinde ya da onu izleyen ilk iş gününde (22.12, 22.06).
    """
    sutunlar = [c for c in PKA_SUTUNLAR if c in d.columns]
    if not sutunlar:
        return None
    s = d[sutunlar].dropna(how="all")
    if s.empty:
        return None
    degisti = (s.ne(s.shift()) & s.notna()).any(axis=1)
    return pd.Timestamp(s.index[degisti][-1])


def _ay(t) -> str:
    """AA.YYYY — aylık saat yazımı (ayın günü yazılmaz)."""
    return pd.Timestamp(t).strftime("%m.%Y")


def _gun(t) -> str:
    return pd.Timestamp(t).strftime("%d.%m.%Y")


def pka_yayim_gunu(d: pd.DataFrame) -> tuple[int | None, str]:
    """(yayım günü, kaynağı): önce DİBS hattının kendi ilanı, yoksa ölçüm.

    DİBS aylık anketi ayın ilk günü etiketiyle alır ve `pka_yayim_gun`'den
    itibaren geçerli sayar; ilanı kendi koşu kaydında durur. Kaynak seri
    anketin gerçek yayım gününü TAŞIMAZ — bu bir varsayımdır ve sayfada okura
    öyle yazılır. İlan bulunamazsa son basamakların en erken günü alınır: bu,
    kuralın veride bıraktığı izdir (hafta sonuna denk gelen ay ileri kayar,
    en erken gün kuralın kendisidir).
    """
    try:
        ilan = json.loads((DIBS / "metrik_ozet.json").read_text(encoding="utf-8"))
        g = ilan.get("esik", {}).get("pka_yayim_gun")
        if g is not None:
            return int(g), "kaynak hattın ilanı"
    except (OSError, ValueError):
        pass
    sutunlar = [c for c in PKA_SUTUNLAR if c in d.columns]
    if not sutunlar:
        return None, "ölçülemedi"
    s = d[sutunlar].dropna(how="all")
    degisti = (s.ne(s.shift()) & s.notna()).any(axis=1)
    gunler = s.index[degisti][-PKA_BASAMAK_PENCERE:]
    if len(gunler) == 0:
        return None, "ölçülemedi"
    return int(min(g.day for g in gunler)), "basamak günlerinden ölçüldü"


GUNLUK_BACAKLAR = ("basabas", "reel", "prim")


def ana_saat(ozet: dict) -> str:
    """Hattın saati = en YENİ GÜNLÜK bacağın günü (GG.AA.YYYY).

    Metin karşılaştırması ("12.06.2026" > "01.09.2026") donmuş 3y bacağını
    hattın tarihi yapıyor, sayfa "81 gün önce" diyordu — veri bugüne aitken.
    Aylık bacaklar (anket, mevsim) bu seçime GİRMEZ: ay damgası ayın son gününe
    demirlenir ve ay bitmeden günlük saati ileri çekerdi.
    """
    def _gunluk(t):
        try:
            return datetime.strptime(str(t), "%d.%m.%Y")
        except ValueError:
            return datetime.min
    gunluk = [v for k, v in ozet.items()
              if k.endswith("_tarih") and k.split("_")[0] in GUNLUK_BACAKLAR
              and _gunluk(v) != datetime.min]
    return max(gunluk, key=_gunluk, default="")


def _liste(etiketler: list[str]) -> str:
    """["1y","2y","7y"] → "1y, 2y ve 7y"; etiket boşsa boş."""
    e = [x for x in etiketler if x]
    if not e:
        return ""
    if len(e) == 1:
        return e[0]
    return ", ".join(e[:-1]) + " ve " + e[-1]


def sekil_saatleri(ozet: dict) -> dict[str, str | None]:
    """Figür → damga: tek çözülebilir tarih ya da iki parçalı dizge ya da None.

    · bütün bacaklar aynı ritimde ve en eski ile en yeni arasında en çok
      DAMGA_AYRIM_GUN varsa → EN ESKİ bacak (kıyas ancak hepsinin ölçüldüğü
      güne kadar kurulur);
    · bacaklar farklı cinsteyse (AA.YYYY × GG.AA.YYYY) ya da daha uzaksa →
      "etiketler tarih · etiketler tarih" (eskiden yeniye), her grup adıyla;
    · hiçbir bacağın saati yoksa → None (uydurulmaz).
    """
    b = _bicim()
    out: dict[str, str | None] = {}
    for dosya, bacaklar in SEKILLER.items():
        gruplar: dict[str, list[str]] = {}
        for etiket, anahtar in bacaklar:
            t = ozet.get(anahtar)
            if isinstance(t, str) and b.tarihe_cevir(t) is not None:
                if etiket not in gruplar.setdefault(t, []):
                    gruplar[t].append(etiket)
        if not gruplar:
            out[dosya] = None
            continue
        sirali = sorted(gruplar, key=lambda t: b.tarihe_cevir(t))
        ayni_cins = len({len(t) for t in sirali}) == 1
        yayilim = (b.tarihe_cevir(sirali[-1]) - b.tarihe_cevir(sirali[0])).days
        if len(sirali) == 1 or (ayni_cins and yayilim <= DAMGA_AYRIM_GUN):
            out[dosya] = sirali[0]
        else:
            out[dosya] = " · ".join(
                (f"{_liste(gruplar[t])} {t}" if _liste(gruplar[t]) else t) for t in sirali)
    return out


def defter_ayir(saatler: dict[str, str | None]) -> tuple[dict[str, str | None], dict[str, str]]:
    """(şekil saat defteri, damga anahtarları).

    Defter yalnız ÇÖZÜLEBİLİR tek tarih ya da None taşır (sayfa sınavı böyle
    ister); iki parçalı damga MDX'in `tarihAnahtari`sine düşer. `damga_*`
    anahtarı HER figür için yazılır — sayfa adıyla çağırıyor, tek günlü figürde
    de defterle aynı tarihi taşır.
    """
    b = _bicim()
    defter, damga = {}, {}
    for dosya, v in saatler.items():
        kok = dosya.rsplit(".", 1)[0]
        if v is None:
            defter[dosya] = None
            damga[f"damga_{kok}"] = "—"
        elif b.tarihe_cevir(v) is not None:
            defter[dosya] = v
            damga[f"damga_{kok}"] = v
        else:
            defter[dosya] = None
            damga[f"damga_{kok}"] = v
    return defter, damga


def hesapla():
    d = yukle()
    tufe = tufe_aylik()
    mevsim = mevsim_deseni(tufe)

    def son(kolon):
        s = d[kolon].dropna()
        return (None, "") if s.empty else (round(float(s.iloc[-1]), 2), _gun(s.index[-1]))

    # ── anket: yürürlükteki anketin ayı ──────────────────────────────────────
    basamak = anket_basamagi(d)
    anket_ay = _ay(basamak) if basamak is not None else None
    yayim_gun, yayim_kaynak = pka_yayim_gunu(d)

    ozet: dict = {}
    for v in VADELER:
        for on, kolon in (("basabas", f"be_{v}"), ("reel", f"r{v}"),
                          ("prim", f"prim_{v}"), ("anket", f"pka_ort_{v}")):
            if kolon not in d.columns:
                continue
            deger, tarih = son(kolon)
            if deger is None:
                continue
            ozet[f"{on}_{v}"] = deger
            # Anket bacağı aylık: saati serinin son dolu günü değil, anketin ayı.
            ozet[f"{on}_{v}_tarih"] = (anket_ay or tarih) if on == "anket" else tarih
    ozet["_tarih"] = ana_saat(ozet)

    # Sayfanın adıyla çağırdığı anket anahtarları HER koşuda yazılır; ölçülemeyen
    # "—" kalır, atlanmaz.
    for kolon, hedef in (("pka_12a", "pka_12a"), ("pka_24a", "pka_24a"),
                         ("pka_12a_n", "pka_katilimci")):
        deger, _ = son(kolon) if kolon in d.columns else (None, "")
        if deger is None:
            ozet[hedef] = "—"
        else:
            ozet[hedef] = int(round(deger)) if hedef == "pka_katilimci" else deger
        ozet[f"{hedef}_tarih"] = anket_ay or ozet["_tarih"]
    ozet["pka_ay_ad"] = (f"{AY_AD[basamak.month - 1]} {basamak.year}"
                         if basamak is not None else "—")
    # Anketin hesapta geçerli sayıldığı İLK gün — kaynak seri anketin gerçek
    # yayım gününü taşımaz; bu gün DİBS hattının "ayın N'i" varsayımının veride
    # bıraktığı izdir ve sayfada okura varsayım olarak yazılır.
    ozet["pka_gecerli_baslangic"] = _gun(basamak) if basamak is not None else "—"
    ozet["pka_yayim_gun"] = yayim_gun if yayim_gun is not None else "—"
    ozet["pka_yayim_gun_kaynak"] = yayim_kaynak

    # ── mevsim: pencerenin son TÜFE ayı bütün mevsim_* anahtarlarının saati ──
    mevsim_ay = _ay(tufe.index.max())
    en_pahali, en_ucuz = int(mevsim["mean"].idxmax()), int(mevsim["mean"].idxmin())
    ozet.update({
        "mevsim_yil": MEVSIM_YIL,
        "mevsim_agustos": round(float(mevsim.loc[8, "mean"]), 2),
        "mevsim_ocak": round(float(mevsim.loc[1, "mean"]), 2),
        "mevsim_en_pahali_ay": en_pahali,
        "mevsim_en_pahali_ay_ad": AY_AD[en_pahali - 1],
        "mevsim_en_ucuz_ay": en_ucuz,
        "mevsim_en_ucuz_ay_ad": AY_AD[en_ucuz - 1],
        "mevsim_aralik": round(float(mevsim["mean"].max() - mevsim["mean"].min()), 2),
        "mevsim_tarih": mevsim_ay,
    })
    for k in ("mevsim_yil", "mevsim_agustos", "mevsim_ocak", "mevsim_en_pahali_ay",
              "mevsim_en_ucuz_ay", "mevsim_aralik"):
        ozet[f"{k}_tarih"] = mevsim_ay

    # ── şekil saat defteri ───────────────────────────────────────────────────
    defter, damga = defter_ayir(sekil_saatleri(ozet))
    ozet["_sekil_tarih"] = defter
    ozet.update(damga)
    return d, mevsim, ozet


if __name__ == "__main__":
    d, mevsim, ozet = hesapla()
    (BURASI / "ozet.json").write_text(
        json.dumps(ozet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("veri tarihi:", ozet["_tarih"], "· anket:", ozet["pka_ay_ad"],
          "· mevsim:", ozet["mevsim_tarih"])
    print(f"{'vade':>5s} {'başabaş':>9s} {'anket':>7s} {'prim':>6s} {'reel':>6s}")
    for v in VADELER:
        print(f"{v:>5s} {str(ozet.get(f'basabas_{v}','—')):>9s} "
              f"{str(ozet.get(f'anket_{v}','—')):>7s} {str(ozet.get(f'prim_{v}','—')):>6s} "
              f"{str(ozet.get(f'reel_{v}','—')):>6s}")
    print("\nmevsimsel desen (ham − SA, son 10 yıl ort., puan):")
    print("  " + "  ".join(f"{ay}:{mevsim.loc[ay,'mean']:+.2f}" for ay in range(1, 13)))
    print("\nşekil saatleri:")
    for ad, t in ozet["_sekil_tarih"].items():
        print(f"  {ad:22s} {t!s:12s} damga: {ozet['damga_' + ad.rsplit('.', 1)[0]]}")
