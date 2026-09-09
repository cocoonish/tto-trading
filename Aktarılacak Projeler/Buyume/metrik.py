# -*- coding: utf-8 -*-
"""Büyüme hattı — ÖLÇÜM katmanı.

Ne hesaplanır ve NEDEN o kaynaktan:

YILLIK BÜYÜME  takvim etkisinden arındırılmış zincirlenmiş hacim endeksinden
               (aynı çeyreğin bir yıl öncesine oranı). Takvim arındırması
               bayram kaymalarını temizler; mevsim arındırması YILLIK oranda
               gereksizdir (dört çeyrek öteye kıyaslıyoruz).

ÇEYREKLİK      YALNIZCA mevsim VE takvim arındırılmış endeksten. Arındırılmamış
               seriden çeyreklik değişim almak mevsimi büyüme sanmaktır.

KATKI          Zincirlenmiş hacim endeksleri TOPLANMAZ (zincirleme, bileşenlerin
               toplamının toplama eşit olmasını bozar). Bu yüzden katkı
                   katki_i = w_i(t−4) × g_i(t)
               ile kurulur: w = bileşenin BİR YIL ÖNCEKİ cari fiyatlı GSYH
               içindeki payı, g = bileşenin reel yıllık büyümesi. İthalat payı
               EKSİ girer (GSYH = C + G + Y + ΔS + İhracat − İthalat).

ARTIK          Katkıların toplamı ile ölçülen büyüme arasındaki fark GİZLENMEZ,
               ayrı bir satır olarak yazılır ve neyi taşıdığı söylenir: stok
               değişimi (zincirlenmiş hacim endeksi yayımlanmıyor) ve zincirleme
               tutarsızlığı. Artığı bileşenlere dağıtmak uydurma olurdu.

KİMLİK DENETİMİ  Üç ölçüt; biri düşerse hat DURUR:
   1. Harcama tarafı GSYH ile üretim tarafı GSYH aynı büyümeyi vermeli.
   2. Cari fiyatlarla sektörel toplam + (vergi − sübvansiyon) = GSYH.
   3. Artık makul bantta olmalı (aşırıysa ağırlık ya da hizalama bozuktur).
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

PROJE = Path(__file__).resolve().parent
DATA = PROJE / "data"

# Harcama tarafı ESA kodları → okunur ad ve GSYH kimliğindeki işaret.
HARCAMA = {
    "P311":  ("Hanehalkı tüketimi", +1),
    "P312":  ("Hizmet eden kuruluşlar", +1),
    "P32":   ("Devlet tüketimi", +1),
    "P51G":  ("Sabit sermaye yatırımı", +1),
    "P6":    ("İhracat", +1),
    "P7":    ("İthalat", -1),
}
# Üretim tarafı A10 kodları.
URETIM = {
    "A":   "Tarım, ormancılık, balıkçılık",
    "BTE": "Sanayi",
    "C":   "  İmalat (sanayinin içinde)",
    "F":   "İnşaat",
    "GTI": "Ticaret, ulaştırma, konaklama",
    "J":   "Bilgi ve iletişim",
    "K":   "Finans ve sigorta",
    "L":   "Gayrimenkul",
    "MN":  "Mesleki ve idari faaliyetler",
    "OTQ": "Kamu, eğitim, sağlık",
    "RTU": "Diğer hizmetler",
}
DAYANIKLILIK = {
    "P311": "Dayanıklı mal",
    "P312": "Yarı dayanıklı mal",
    "P313": "Dayanıksız mal",
    "P314": "Hizmetler",
}

_UYARI: list[str] = []


def uyar(m: str) -> None:
    """Görünür uyarı. Cümle OKURA yazılır: `uyarilar.json` siteye kopyalanır ve
    sayfaya olduğu gibi basılır (koşu kutusu), yani anahtar adı ve boru hattı
    dili buraya giremez. Kaynağın kendi büyük harfli kodları (B1G, D21X31,
    P311) kaynak künyesidir ve muaftır."""
    if m not in _UYARI:
        _UYARI.append(m)
    print("  ! " + m, flush=True)


def _oku(ad: str) -> pd.DataFrame:
    y = DATA / f"{ad}.csv"
    if not y.exists():
        raise SystemExit(f"{y} yok — önce veri.py")
    d = pd.read_csv(y, index_col=0, parse_dates=True)
    if d.dropna(how="all").empty:
        raise SystemExit(f"{ad}: tablo boş — hat duruyor (boş tablo başarı değildir)")
    return d


def _sutun(d: pd.DataFrame, sonek: str) -> pd.Series | None:
    """Kolonu SONEKİNDEN bul: grup öneki gruptan gruba değişiyor."""
    adaylar = [c for c in d.columns if c.rsplit("_", 1)[-1] == sonek]
    if not adaylar:
        return None
    return pd.to_numeric(d[adaylar[0]], errors="coerce")


def _yillik(s: pd.Series) -> pd.Series:
    return (s / s.shift(4) - 1.0) * 100.0


def _r(x, n=2):
    return None if x is None or pd.isna(x) else round(float(x), n)


def ceyrek_etiket(t) -> str:
    """Okur ETİKETİ: "2026-Ç2". Saat DEĞİLDİR.

    09.09.2026'da ölçüldü: hat etiketi `str(ts.to_period("Q"))` ile yazıyordu,
    yani "2026Q2" — İngilizce kalıp, üstelik depodaki tek çeyrek yazımıyla
    (kredi `ceyrek`, ödemeler dengesi, DİBS: "2026-Ç2") ayrışıyordu. Etiket
    okura basılıyor: figür başlıkları ve `<Deger anahtar="_ceyrek">` bunu
    gösterir.
    """
    return f"{t.year}-Ç{(t.month - 1) // 3 + 1}"


def ceyrek_saati(t) -> str:
    """Hattın SAATİ: çeyreğin SON AYI, "AA.YYYY" ("06.2026").

    Biçim sözleşmesi (ortak/bicim.py = site/src/lib/bicim.ts) üç aylık bir
    ölçünün gününü yazmaz: hat "30.06.2026" yazıyordu ve GrafikEmbed dört
    figürün altına o günü basıyordu — okur çeyreğin tamamını anlatan bir
    ölçüyü tek bir günün ölçümü sanar. AA.YYYY ayın SON gününe demirlenir,
    yani bayatlık denetimi aynı günü görmeye devam eder (30.06.2026); değişen
    yalnız okura ne yazdığımız.
    """
    return t.strftime("%m.%Y")


def main() -> int:
    print("── Büyüme hattı · ölçüm")
    takvim = _oku("harcama_takvim")
    mevsim = _oku("harcama_mevsim_takvim")
    cari = _oku("harcama_cari")
    uret_z = _oku("uretim_zincir")
    uret_c = _oku("uretim_cari")
    hane = _oku("hanehalki_dayaniklilik")

    gsyh_t = _sutun(takvim, "B1GQ")
    gsyh_m = _sutun(mevsim, "B1GQ")
    gsyh_c = _sutun(cari, "B1GQ")
    gsyh_uz = _sutun(uret_z, "B1GQ")
    gsyh_uc = _sutun(uret_c, "B1GQ")
    for ad, s in (("takvim", gsyh_t), ("mevsim", gsyh_m), ("cari", gsyh_c),
                  ("üretim zincir", gsyh_uz), ("üretim cari", gsyh_uc)):
        if s is None or s.dropna().empty:
            raise SystemExit(f"{ad}: B1GQ (GSYH) serisi yok — hat duruyor")

    son = gsyh_t.dropna().index.max()
    ceyrek = ceyrek_etiket(son)
    print(f"   son çeyrek: {ceyrek}")

    # ── yıllık ve çeyreklik büyüme
    yil_ser = _yillik(gsyh_t)
    cey_ser = (gsyh_m / gsyh_m.shift(1) - 1.0) * 100.0
    buyume_yillik = yil_ser.get(son)
    buyume_ceyreklik = cey_ser.get(son)
    print(f"   yıllık {buyume_yillik:.2f}%  ·  çeyreklik (mevsim+takvim ar.) "
          f"{buyume_ceyreklik:.2f}%")

    # ── MANŞET vs AYRIŞTIRMA TABANI. Bunlar AYNI ŞEY DEĞİL ve karıştırmak
    # ölçü hatasıdır (ilk sürümde karıştırılmıştı):
    #   · MANŞET yıllık büyüme ARINDIRILMAMIŞ zincirlenmiş hacimden gelir.
    #     Üretim tarafı serisi bunu veriyor ve yayımlanan oranla örtüşüyor.
    #   · Harcama AYRIŞTIRMASI takvim arındırılmış seriden kurulur; bileşenlerin
    #     takvim etkisi birbirini götürmesin diye. Bu yüzden ayrıştırmanın
    #     tabanı da o serinin KENDİ büyümesidir, manşet değil.
    # İkisi arasındaki fark takvim arındırmasının kendisidir; kimlik değil,
    # ölçülüp yazılan bir büyüklüktür. Aşırıysa seri seçimi bozuktur.
    mansel = _yillik(gsyh_uz).get(son)
    ayarlama_farki = float(buyume_yillik) - float(mansel)
    if abs(ayarlama_farki) > 0.8:
        raise SystemExit(
            f"AYARLAMA FARKI AŞIRI: manşet (arındırılmamış) {mansel:.2f}% ile "
            f"takvim arındırılmış harcama tabanı {buyume_yillik:.2f}% arasında "
            f"{ayarlama_farki:+.2f} puan var. Takvim arındırması bu kadar "
            "oynatmaz — seri seçimi ya da hizalama bozuk.")
    print(f"   manşet (arındırılmamış, üretim) {mansel:.2f}%  ·  "
          f"ayrıştırma tabanı (takvim ar., harcama) {buyume_yillik:.2f}%  ·  "
          f"ayarlama farkı {ayarlama_farki:+.2f} puan")

    # ── KİMLİK 2: cari fiyatlarla sektörel toplam + vergi = GSYH
    b1g = _sutun(uret_c, "B1G")
    vergi = _sutun(uret_c, "D21X31")
    if b1g is not None and vergi is not None:
        toplam = (b1g + vergi).get(son)
        hedef = float(gsyh_uc.get(son))
        sapma = abs(toplam - hedef) / hedef * 100.0
        if sapma > 0.5:
            raise SystemExit(
                f"KİMLİK DÜŞTÜ: sektörel toplam + vergi = {toplam:,.0f}, "
                f"GSYH = {hedef:,.0f} (%{sapma:.2f} sapma)")
        print(f"   kimlik 2 ✓ sektörel toplam + vergi = GSYH (%{sapma:.3f} sapma)")
    else:
        uyar("Üretim tarafının cari fiyatlı toplamı (B1G) ya da vergi kalemi "
             "(D21X31) bu yayımda yok — sektörel toplam ile GSYH karşılaştırması "
             "bu koşuda yapılamadı.")

    # ── KATKI: w(t−4) × g(t), ithalat EKSİ
    onceki = son - pd.DateOffset(years=1)
    onceki = gsyh_c.index[gsyh_c.index.get_indexer([onceki], method="nearest")][0]
    gsyh_c_onceki = float(gsyh_c.get(onceki))
    katkilar, bilesenler = {}, {}
    toplam_katki = 0.0
    for kod, (ad, isaret) in HARCAMA.items():
        reel = _sutun(takvim, kod)
        nominal = _sutun(cari, kod)
        if reel is None or nominal is None:
            uyar(f"{ad}: reel ya da cari fiyatlı seri bu yayımda yok — "
                 "katkı ayrıştırmasına girmiyor.")
            continue
        g = _yillik(reel).get(son)
        w = float(nominal.get(onceki)) / gsyh_c_onceki
        if pd.isna(g) or pd.isna(w):
            uyar(f"{ad}: büyüme ya da ağırlık ölçülemedi — "
                 "katkı ayrıştırmasına girmiyor.")
            continue
        k = isaret * w * float(g)
        katkilar[kod] = {"ad": ad, "buyume": _r(g), "agirlik": _r(w * 100, 1),
                         "katki": _r(k), "isaret": isaret}
        bilesenler[kod] = {"ad": ad, "buyume": _r(g)}
        toplam_katki += k
    # Artık AYRIŞTIRMA TABANINA göre: katkılar takvim arındırılmış seriden
    # geliyor, manşetten çıkarmak takvim farkını da artığa yıkardı.
    artik = float(buyume_yillik) - toplam_katki
    print(f"   katkı toplamı {toplam_katki:.2f} · artık {artik:+.2f} puan")
    if abs(artik) > 3.0:
        raise SystemExit(
            f"ARTIK AŞIRI ({artik:+.2f} puan): stok ve zincirleme tutarsızlığı bu "
            "kadar büyük olmaz; ağırlık dönemi ya da hizalama bozuk.")

    # ── sektörler
    sektorler = {}
    gsyh_uc_onceki = float(gsyh_uc.get(onceki))
    for kod, ad in URETIM.items():
        reel = _sutun(uret_z, kod)
        nominal = _sutun(uret_c, kod)
        if reel is None:
            continue
        g = _yillik(reel).get(son)
        w = (float(nominal.get(onceki)) / gsyh_uc_onceki * 100.0
             if nominal is not None and not pd.isna(nominal.get(onceki)) else None)
        sektorler[kod] = {"ad": ad, "buyume": _r(g), "agirlik": _r(w, 1)}

    # ── hanehalkı tüketiminin dayanıklılık kırılımı (CARİ fiyatlarla → NOMİNAL)
    hane_toplam = _sutun(hane, "P31HNT")
    dayaniklilik = {}
    for kod, ad in DAYANIKLILIK.items():
        s = _sutun(hane, kod)
        if s is None:
            continue
        pay = (float(s.get(son)) / float(hane_toplam.get(son)) * 100.0
               if hane_toplam is not None else None)
        dayaniklilik[kod] = {"ad": ad, "nominal_buyume": _r(_yillik(s).get(son)),
                             "pay": _r(pay, 1)}

    # ── tarihçe (grafikler için)
    tarihce = []
    for t in gsyh_t.dropna().index[-44:]:
        tarihce.append({
            "ceyrek": ceyrek_etiket(t),
            "yillik": _r(yil_ser.get(t)),
            "ceyreklik": _r(cey_ser.get(t)),
        })

    cikti = {
        "_ceyrek": ceyrek,
        "_tarih": ceyrek_saati(son),
        "buyume_yillik": _r(mansel),                 # MANŞET (arındırılmamış)
        "buyume_ceyreklik": _r(buyume_ceyreklik),
        "ayristirma_tabani": _r(buyume_yillik),      # takvim ar. harcama tarafı
        "ayarlama_farki": _r(ayarlama_farki),
        "onceki_ceyrek": ceyrek_etiket(onceki),
        "agirlik_donemi": ceyrek_etiket(onceki),
        "katkilar": katkilar,
        "katki_toplami": _r(toplam_katki),
        "artik": _r(artik),
        "artik_aciklama": ("stok değişimi (zincirlenmiş hacim endeksi "
                           "yayımlanmıyor) ve zincirleme tutarsızlığı"),
        "sektorler": sektorler,
        "dayaniklilik": dayaniklilik,
        "tarihce": tarihce,
        "uyarilar": _UYARI,
    }
    (DATA / "metrik.json").write_text(
        json.dumps(cikti, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"── ölçüm yazıldı: {DATA/'metrik.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
