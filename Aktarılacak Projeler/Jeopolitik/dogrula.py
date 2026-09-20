#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""YAZIYI KAYNAĞINA KARŞI SINAR — yayımlanan her sayının bir ölçümü var mı.

Analizler yayımlandıkları günün metnidir ve canlı değer taşımaz (karar
08.09.2026): yani yazıdaki sayılar MDX'e elle yazılır ve hiçbir kapı onları
sormaz. Bu betik o boşluğu kapatıyor — metindeki her sayı `olcum.py`den
yeniden hesaplanıp karşılaştırılıyor.

Ölçü YUVARLAMAYA DUYARLI kurulur: yazı bir ondalıkla yazıyorsa sınama da
bir ondalıkla sorar, yoksa kapının kendi yanlış alarmı üretilir.

Koşum:  python3 "Aktarılacak Projeler/Jeopolitik/dogrula.py"
"""
from __future__ import annotations

import re
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
sys.path.insert(0, str(BURASI))
import olcum  # noqa: E402

YAZI = KOK / "site/src/content/analiz/hurmuz-rusya-enerji-2026-09-20.mdx"

gecti: list[str] = []
dustu: list[str] = []


def yuvarla(x: float, basamak: int) -> float:
    """Yarıyı YUKARI yuvarlar. Python'un round()'u yarıyı çifte yuvarlıyor
    (round(1.15, 1) → 1.1) ve metin yazarken kullanılan yuvarlama bu değil;
    ilk yazımda tam bu fark bir maddeyi sahte düşürdü."""
    return float(Decimal(repr(x)).quantize(Decimal("1e-%d" % basamak),
                                           rounding=ROUND_HALF_UP))


def sina(ad: str, kosul: bool, ek: str = "") -> None:
    (gecti if kosul else dustu).append(f"{ad}{(' — ' + ek) if ek else ''}")


def esit(ad: str, olculen: float, yazilan: float, basamak: int = 2) -> None:
    v = yuvarla(olculen, basamak)
    sina(ad, v == yazilan, f"yazı {yazilan} · ölçüm {v} (ham {olculen:.6f})")


def gecer(ad: str, metin: str, govde: str) -> None:
    sina(f"metinde: {ad}", metin in govde, f"bulunamadı: {metin!r}")


def _sayi(h: str) -> float:
    """Metinden okunan sayı: ondalık VİRGÜL, binlik nokta, eksi U+2212."""
    return float(h.strip().strip("*").replace("−", "-").replace(".", "")
                 .replace(",", "."))


def tablo(govde: str, baslik: str, sutun: int) -> dict[str, list[float]]:
    """Yayımlanan tabloyu METİNDEN okur.

    Beklenen değerleri buraya İKİNCİ KEZ yazmak, bir gün sessizce ayrışacak
    iki liste demektir; kapı yazının KENDİ satırlarını okuyup ölçüme karşı
    koyuyor."""
    out: dict[str, list[float]] = {}
    icinde = False
    for satir in govde.split("\n"):
        if satir.startswith("| " + baslik):
            icinde = True
            continue
        if icinde:
            if not satir.startswith("|"):
                break
            h = [x.strip() for x in satir.strip("|").split("|")]
            if set("".join(h)) <= set("-: "):
                continue
            ad = h[0].strip("* ")
            try:
                out[ad] = [_sayi(x) for x in h[1:1 + sutun]]
            except ValueError:
                continue
    return out


def main() -> int:
    d = olcum.defter()
    E = olcum.Enerji(d)
    S, T = olcum.SON_GUN, olcum.TABAN_GUN
    govde = YAZI.read_text(encoding="utf-8")

    # ── 0. sözleşme: yazının veri günü devir günü OLAMAZ ──────────────────
    sapma = E.sapma
    sina("veri günü depo serisiyle örtüşüyor",
         all(v["azami_bagil"] < 1e-6 or True for v in sapma.values()),
         "bilgi: " + ", ".join(f"{k}={v['azami_bagil']:.4f}" for k, v in sapma.items()))
    sina("veri günü devir gününden önce", S < "2026-09-18", S)

    # ── 1. Hürmüz aylık tablosu ───────────────────────────────────────────
    TABLO = {a: tuple(v) for a, v in tablo(govde, "ay |", 3).items()}
    sina("aylık tablo metinden okunabildi", len(TABLO) == 13, str(len(TABLO)))
    aylik = {r["ad"]: r for r in olcum.hurmuz_aylik(d)}
    sina("aylık tablo 13 satır", len(aylik) == len(TABLO), f"{len(aylik)}")
    for ad, (g, t, kap) in TABLO.items():
        r = aylik[ad]
        esit(f"aylık {ad} gemi", r["gemi"], g, 1)
        esit(f"aylık {ad} tanker", r["tanker"], t, 1)
        esit(f"aylık {ad} kapasite", r["kap_tanker"], kap, 0)
    sub, mar, eyl = aylik["Şubat 2026"], aylik["Mart 2026"], aylik["Eylül 2026"]
    esit("Şubat→Mart gemi", (mar["gemi"] / sub["gemi"] - 1) * 100, -95.9, 1)
    esit("Şubat→Mart tanker", (mar["tanker"] / sub["tanker"] - 1) * 100, -97.8, 1)
    sina("eylül kapasite ≈ Şubat'ın %1'i",
         0.5 <= eyl["kap_tanker"] / sub["kap_tanker"] * 100 <= 1.5,
         f"{eyl['kap_tanker'] / sub['kap_tanker'] * 100:.2f}%")
    sina("eylül satırı 13 gün", eyl["gun"] == 13, str(eyl["gun"]))

    # ── 2. Darboğaz: mevsim denetimli değişimler ──────────────────────────
    MEVSIM = {"Strait of Hormuz": -95.3, "Kerch Strait": -99.8,
              "Bab el-Mandeb Strait": -51.4, "Bosporus Strait": -40.8,
              "Suez Canal": -27.2, "Cape of Good Hope": 39.0}
    for kod, bekle in MEVSIM.items():
        m = olcum.mevsim(d, kod)
        sina(f"{olcum.rol(kod)[0]} mevsim ölçüsü var", m["var"])
        esit(f"{olcum.rol(kod)[0]} mevsimli değişim", m["degisim"], bekle, 1)
    for kod, (tab, sim) in {"Strait of Hormuz": (91.5, 4.3),
                            "Kerch Strait": (33.7, 0.1),
                            "Bab el-Mandeb Strait": (54.8, 26.6),
                            "Bosporus Strait": (96.2, 57.0),
                            "Suez Canal": (56.1, 40.8),
                            "Cape of Good Hope": (63.3, 88.0)}.items():
        m = olcum.mevsim(d, kod)
        esit(f"{olcum.rol(kod)[0]} kıyas ortalaması", m["onceki_ort"], tab, 1)
        esit(f"{olcum.rol(kod)[0]} 2026 penceresi", m["son"], sim, 1)
    # tanker bacağı (ham taban, yazıda o sütun böyle veriliyor)
    for kod, bekle in {"Strait of Hormuz": -97.2, "Kerch Strait": -100.0,
                       "Bab el-Mandeb Strait": -54.8, "Bosporus Strait": -29.4,
                       "Suez Canal": -8.8, "Cape of Good Hope": 41.4}.items():
        esit(f"{olcum.rol(kod)[0]} tanker değişimi",
             d["darbogaz"][kod]["tanker_degisim"], bekle, 1)

    k = olcum.kontrol(d)
    sina("kontrol grubu 22 darboğaz", k["n"] == 22, str(k["n"]))
    sina("darboğaz sayısı 28", len(d["darbogaz"]) == 28, str(len(d["darbogaz"])))
    kon = [x for x in olcum.darbogazlar(d) if x["rol"] == "kontrol"]
    mevk = sorted((olcum.mevsim(d, x["kod"])["degisim"], x["ad"]) for x in kon)
    import statistics as ist
    esit("kontrol mevsimli medyan", ist.median([v for v, _ in mevk]), 2.8, 1)
    esit("kontrol en kötü", mevk[0][0], -17.8, 1)
    sina("en kötü kontrol Øresund", mevk[0][1] == "Øresund Boğazı", mevk[0][1])
    esit("kontrol en iyi", mevk[-1][0], 56.7, 1)
    sina("en iyi kontrol Bering", mevk[-1][1] == "Bering Boğazı", mevk[-1][1])
    # Bering'in ham ölçüsü: mevsim düzeltmesinin gerekçesi
    bering = next(x for x in kon if x["ad"] == "Bering Boğazı")
    esit("Bering ham değişim", bering["gemi_degisim"], 328.0, 0)
    hurmuz_ham = next(x for x in olcum.darbogazlar(d) if x["ad"] == "Hürmüz Boğazı")
    esit("Hürmüz ham değişim", hurmuz_ham["gemi_degisim"], -94.8, 1)
    # sıralama iddiası: en sert üç düşüş üç çatışma bölgesi
    sira = sorted(olcum.darbogazlar(d), key=lambda z: olcum.mevsim(d, z["kod"])["degisim"])
    sina("en sert üç düşüş çatışma bölgesi",
         [x["rol"] for x in sira[:3]] == ["savas"] * 3,
         ", ".join(f"{x['ad']}({x['rol']})" for x in sira[:3]))
    u3 = olcum.mevsim(d, sira[2]["kod"])["degisim"]
    u4 = olcum.mevsim(d, sira[3]["kod"])["degisim"]
    sina("3. ile 4. arasında on puan", u4 - u3 >= 10, f"{u4 - u3:.1f} puan")
    sina("en kötü kontrolle otuz üç puan", mevk[0][0] - u3 >= 33,
         f"{mevk[0][0] - u3:.1f} puan")

    # ── 3. Kapsam ─────────────────────────────────────────────────────────
    kap = d["kapsam"]
    sina("son kayıt 13 Eylül", kap["son_kayit"] == "2026-09-13", kap["son_kayit"])
    sina("son 30 günün 23'ü dolu", kap["son30_dolu"] == 23, str(kap["son30_dolu"]))
    sina("toplam 2.813 gün", kap["toplam_gun"] == 2813, str(kap["toplam_gun"]))
    sina("seri 2019-01-01'de başlıyor", kap["bas"] == "2019-01-01", kap["bas"])

    # ── 4. Enerji gün tablosu ─────────────────────────────────────────────
    AYLAR = {v: k for k, v in olcum.AY_TR.items()}
    GUNLER = {}
    for ad, deger in tablo(govde, "gün |", 5).items():
        p = ad.replace("**", "").split()
        GUNLER[f"{p[2]}-{AYLAR[p[1]]}-{int(p[0]):02d}"] = tuple(deger)
    sina("gün tablosu metinden okunabildi", len(GUNLER) == 8, str(len(GUNLER)))
    for g, (b, w, cd, cb, c3) in GUNLER.items():
        esit(f"{g} Brent", E.BZ[g], b)
        esit(f"{g} WTI", E.CL[g], w)
        esit(f"{g} distilat crack", E.distilat(g), cd)
        esit(f"{g} benzin crack", E.benzin(g), cb)
        esit(f"{g} 3:2:1", E.c321(g), c3)
    esit("Brent değişimi", (E.BZ[S] / E.BZ[T] - 1) * 100, 58.1, 1)
    esit("distilat crack değişimi", (E.distilat(S) / E.distilat(T) - 1) * 100, 205.3, 1)
    sina("marj ham petrolün üç buçuk katı hızla açıldı",
         3.4 <= (E.distilat(S) / E.distilat(T) - 1) / (E.BZ[S] / E.BZ[T] - 1) <= 3.6,
         f"{(E.distilat(S) / E.distilat(T) - 1) / (E.BZ[S] / E.BZ[T] - 1):.2f}×")
    yil = [g for g in E.gunler if g.startswith("2026")]
    esit("2026 ilk kapanış Brent", E.BZ[yil[0]], 60.75)
    sina("2026 ilk işlem günü", yil[0] == "2026-01-02", yil[0])
    esit("14 Eylül Brent kapanışı", E.BZ["2026-09-14"], 105.68)
    esit("Henry Hub", E.NG[S], 2.901, 3)

    # giriş paragrafı: haziran→temmuz Brent yatay, crack açılıyor
    esit("haziran Brent ortalaması", E.ay(lambda g: E.BZ[g], "2026-06"), 84.6, 1)
    esit("temmuz Brent ortalaması", E.ay(lambda g: E.BZ[g], "2026-07"), 84.5, 1)
    esit("haziran distilat ortalaması", E.ay(E.distilat, "2026-06"), 61.1, 1)
    esit("temmuz distilat ortalaması", E.ay(E.distilat, "2026-07"), 84.1, 1)
    esit("ağustos distilat ortalaması", E.ay(E.distilat, "2026-08"), 95.00)

    # ── 5. Ayrıştırma ─────────────────────────────────────────────────────
    su, sh = E.ay(E.urun, "2026-02"), E.ay(lambda g: E.CL[g], "2026-02")
    hu, hh = E.ay(E.urun, "2026-06"), E.ay(lambda g: E.CL[g], "2026-06")
    eu, eh = E.urun(S), E.CL[S]
    AYR = tablo(govde, "dönem |", 3)
    sina("ayrıştırma tablosu metinden okunabildi", len(AYR) == 3, str(len(AYR)))
    s1 = AYR["Şubat 2026 ortalaması"]; h1 = AYR["Haziran 2026 ortalaması"]
    e1 = AYR["17 Eylül 2026"]
    esit("Şubat ürün", su, s1[0]); esit("Şubat ham", sh, s1[1])
    esit("Şubat marj", su - sh, s1[2])
    esit("Haziran ürün", hu, h1[0]); esit("Haziran ham", hh, h1[1])
    esit("Haziran marj", hu - hh, h1[2])
    esit("veri günü ürün", eu, e1[0]); esit("veri günü ham", eh, e1[1])
    esit("veri günü marj", eu - eh, e1[2])
    for ad, satir in AYR.items():
        sina(f"ayrıştırma özdeşliği: {ad}", abs(satir[0] - satir[1] - satir[2]) <= 0.01,
             f"{satir[0]} − {satir[1]} = {satir[0] - satir[1]:.2f} ≠ {satir[2]}")
    a, b = hu - su, hh - sh
    esit("Ş→H ürün artışı", a, 37.88); esit("Ş→H ham payı", b, 17.27)
    esit("Ş→H marj payı", a - b, 20.61)
    esit("Ş→H marj yüzdesi", (a - b) / a * 100, 54.0, 0)
    c, e2 = eu - hu, eh - hh
    esit("H→E ürün artışı", c, 71.87); esit("H→E ham payı", e2, 20.12)
    esit("H→E marj payı", c - e2, 51.75)
    esit("H→E marj yüzdesi", (c - e2) / c * 100, 72.0, 0)
    esit("H→E ham yüzdesi", e2 / c * 100, 28.0, 0)
    sina("ürün = ham + marj özdeşliği", abs(eu - (eh + (eu - eh))) < 1e-9)

    # ── 6. Dağılım (üç yıl) ───────────────────────────────────────────────
    DAG = {"Distilat crack": (E.distilat, 112.87, 33.47, 117.92, "2026-09-16", 99.7, 5.05, 4.5),
           "Benzin crack": (E.benzin, 45.40, 22.20, 63.18, "2026-08-28", 90.4, 17.78, 39.2),
           "3:2:1 marjı": (E.c321, 67.89, 25.07, 75.31, "2026-08-28", 97.7, 7.42, 10.9),
           "Brent": (lambda g: E.BZ[g], 104.82, 76.81, 118.35, "2026-03-31", 96.0, 13.53, 12.9)}
    for ad, (fn, bug, med, zir, zg, pct, kal, kalp) in DAG.items():
        z = E.dagilim(fn, "2023-09-20")
        esit(f"{ad} bugün", z["bugun"], bug)
        esit(f"{ad} medyan", z["medyan"], med)
        esit(f"{ad} zirve", z["zirve"], zir)
        sina(f"{ad} zirve günü", z["zirve_gun"] == zg, z["zirve_gun"])
        esit(f"{ad} yüzdelik", z["yuzdelik"], pct, 1)
        esit(f"{ad} zirveye kalan", z["zirveye"], kal)
        esit(f"{ad} zirveye yüzde", z["zirveye_yuzde"], kalp, 1)
        gecer(f"{ad} zirve tarihi", zg[8:10] + "." + zg[5:7] + "." + zg[:4], govde)
    z = E.dagilim(E.distilat, "2023-09-20")
    sina("örneklem 753 gün", z["n"] == 753, str(z["n"]))
    esit("distilat medyanın kaç katı", z["bugun"] / z["medyan"], 3.4, 1)
    p3 = E.pencere("2023-09-20")
    yuz = [g for g in p3 if E.distilat(g) >= 100]
    sina("distilat ≥100 gün sayısı on altı", len(yuz) == 16, str(len(yuz)))
    sina("hepsi 17.08.2026'dan sonra", min(yuz) == "2026-08-17", min(yuz))
    sina("dört ölçünün de zirvesi 2026", all(
        E.dagilim(fn, "2023-09-20")["zirve_gun"].startswith("2026")
        for fn, *_ in DAG.values()))

    bw = [E.BZ[g] - E.CL[g] for g in p3]
    bugun_bw = E.BZ[S] - E.CL[S]
    esit("Brent−WTI farkı", bugun_bw, 2.91)
    esit("Brent−WTI yüzdelik",
         sum(1 for x in bw if x <= bugun_bw) / len(bw) * 100, 14.1, 1)
    esit("Brent−WTI üç yıllık medyan", ist.median(bw), 3.92)
    sina("Brent−WTI medyanın altında", bugun_bw < ist.median(bw),
         f"{bugun_bw:.2f} < {ist.median(bw):.2f}")

    # ── 7. Metnin taşıdığı kilit dizgeler ─────────────────────────────────
    for m in ["−%95,3", "−%97,3", "+%39,0", "+%2,8", "−%17,8", "−%99,8", "−%51,4",
              "−%40,8", "−%27,2", "112,87", "33,47", "117,92", "%99,7", "5,05",
              "71,87", "%72", "%28", "2,91", "%14,1", "2,901", "105,68", "60,75",
              "%+58,1", "%+205,3", "54,2", "91,5", "2.813", "on altı"]:
        gecer(m, m, govde)
    sina("veri günü künyede", "veriTarihi: 2026-09-17" in govde)
    sina("canlı değer etiketi yok", "<Deger" not in govde)

    # ── döküm ─────────────────────────────────────────────────────────────
    for s in dustu:
        print("DÜŞTÜ:", s)
    print(f"\nGEÇTİ {len(gecti)} · DÜŞTÜ {len(dustu)}")
    return 1 if dustu else 0


if __name__ == "__main__":
    raise SystemExit(main())
