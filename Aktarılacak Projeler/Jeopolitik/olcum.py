#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JEOPOLİTİK — yazının BÜTÜN sayılarını üreten tek ölçüm katmanı.

Girdi tek dosya: `veri/defter.json` (keşif koşusunun çıktısı, depoda arşiv).
Tüketicisi iki: `sekil.py` figürleri buradan çizer, `dogrula.py` yayımlanan
metni buna karşı sınar. İki ayrı hesap bir gün sessizce ayrışır; sayıyı
üreten yer tektir.

İKİ SÖZLEŞME, ADIYLA:

· ENERJİ HAM ÖN VADE KAPANIŞIDIR. Vade devri için geriye ölçeklenmiş seri
  bir crack spread'e uygulanamaz — üç bacak farklı oranla ölçeklenir ve
  42×HO − CL aritmetiği o farkı spread'in kendisi kadar büyütür. Bir crack,
  aynı gün gerçekten kote edilmiş üç fiyatın aritmetiğidir.

· DARBOĞAZ SINIFLANDIRMASI ELLE DEĞİL, BURADA VE ADIYLA. Kontrol grubu
  "savaş rotasında olmayan" darboğazlardır; sayısı listeden türetilir,
  metne elle yazılmaz.
"""
from __future__ import annotations

import json
import statistics as ist
from pathlib import Path

BURASI = Path(__file__).resolve().parent
DEFTER = BURASI / "veri/defter.json"

SON_GUN = "2026-09-17"     # yazının veri günü — bkz. `uyum()`: 18.09 vade devri günü
KIRILMA = "2026-03-02"       # ölçülen rejim kırılması: fiyat ve geçiş aynı gün
TABAN_GUN = "2026-02-02"     # endeks ve değişim tabanı

# Darboğazların ROLÜ. Kaynak 28 darboğaz sayıyor; yazıdaki kontrol grubu
# elle SEÇİLMİŞ bir alt küme değil, "savaş rotasında olmayan her darboğaz"
# — yani listenin tamamından ÇIKARMA ile kurulur. İlk yazımda on iki
# darboğaz elle sayılmıştı ve ikisinin adı kaynaktakiyle tutmuyordu
# ("Bosphorus"/"Bosporus", "Strait of Gibraltar"/"Gibraltar Strait"):
# İstanbul Boğazı ile Cebelitarık sessizce DÜŞTÜ ve kontrol grubu altı
# yerine beş darboğazla ölçüldü. Ad artık kaynağın kendi yazımıyla.
SAVAS = {
    "Strait of Hormuz": "Hürmüz Boğazı",
    "Kerch Strait": "Kerç Boğazı",
    "Bab el-Mandeb Strait": "Babülmendep",
}
SAVAS_KOMSUSU = {                       # savaşın rotasında, ama çatışma bölgesi değil
    "Bosporus Strait": "İstanbul Boğazı",
    "Suez Canal": "Süveyş Kanalı",
}
ROTA = {"Cape of Good Hope": "Ümit Burnu"}       # yükün kaydığı yol
# Yazıda TR adıyla anılan kontrol darboğazları. Listede olmayan bir kontrol
# darboğazı yine KONTROL sayılır, yalnız TR adı yoksa kaynağın adıyla geçer.
KONTROL_AD = {
    "Gibraltar Strait": "Cebelitarık", "Malacca Strait": "Malaka Boğazı",
    "Taiwan Strait": "Taiwan Boğazı", "Korea Strait": "Kore Boğazı",
    "Dover Strait": "Dover Boğazı", "Panama Canal": "Panama Kanalı",
    "Oresund Strait": "Øresund Boğazı", "Bering Strait": "Bering Boğazı",
    "Magellan Strait": "Macellan Boğazı", "Luzon Strait": "Luzon Boğazı",
    "Bohai Strait": "Bohay Boğazı", "Sunda Strait": "Sunda Boğazı",
    "Lombok Strait": "Lombok Boğazı", "Makassar Strait": "Makassar Boğazı",
    "Mindoro Strait": "Mindoro Boğazı", "Ombai Strait": "Ombai Boğazı",
    "Torres Strait": "Torres Boğazı", "Tsugaru Strait": "Tsugaru Boğazı",
    "Balabac Strait": "Balabac Boğazı", "Windward Passage": "Windward Geçidi",
    "Mona Passage": "Mona Geçidi", "Yucatan Channel": "Yucatán Kanalı",
}


def rol(kod: str) -> tuple[str, str]:
    if kod in SAVAS:
        return SAVAS[kod], "savas"
    if kod in SAVAS_KOMSUSU:
        return SAVAS_KOMSUSU[kod], "savas_komsusu"
    if kod in ROTA:
        return ROTA[kod], "rota"
    return KONTROL_AD.get(kod, kod), "kontrol"


AY_TR = {"01": "Ocak", "02": "Şubat", "03": "Mart", "04": "Nisan", "05": "Mayıs",
         "06": "Haziran", "07": "Temmuz", "08": "Ağustos", "09": "Eylül",
         "10": "Ekim", "11": "Kasım", "12": "Aralık"}


def defter() -> dict:
    return json.loads(DEFTER.read_text(encoding="utf-8"))


# ── enerji ────────────────────────────────────────────────────────────────
class Enerji:
    def __init__(self, d: dict):
        e = d["enerji"]
        self.gunler: list[str] = e["gunler"]
        k = e["kapanis"]
        self.BZ = dict(zip(self.gunler, k["BZ=F"]))
        self.CL = dict(zip(self.gunler, k["CL=F"]))
        self.RB = dict(zip(self.gunler, k["RB=F"]))
        self.HO = dict(zip(self.gunler, k["HO=F"]))
        self.NG = dict(zip(self.gunler, k["NG=F"]))
        self.sapma = e.get("depo_sapma", {})

    # 1 varil = 42 galon; piyasa.py ile AYNI tanım.
    def urun(self, g: str) -> float:   return 42 * self.HO[g]
    def distilat(self, g: str) -> float: return 42 * self.HO[g] - self.CL[g]
    def benzin(self, g: str) -> float:   return 42 * self.RB[g] - self.CL[g]
    def c321(self, g: str) -> float:
        return (2 * 42 * self.RB[g] + 42 * self.HO[g] - 3 * self.CL[g]) / 3

    def ay(self, fn, ay: str) -> float:
        v = [fn(g) for g in self.gunler if g.startswith(ay)]
        return ist.mean(v)

    def pencere(self, bas: str) -> list[str]:
        return [g for g in self.gunler if bas <= g <= SON_GUN]

    def dagilim(self, fn, bas: str) -> dict:
        p = self.pencere(bas)
        v = [fn(g) for g in p]
        bugun = fn(SON_GUN)
        zirve_g = max(p, key=fn)
        return {
            "n": len(p), "bas": p[0], "son": p[-1], "bugun": bugun,
            "medyan": ist.median(v), "zirve": max(v), "zirve_gun": zirve_g,
            "dip": min(v),
            "yuzdelik": sum(1 for x in v if x <= bugun) / len(v) * 100,
            "zirveye": max(v) - bugun,
            "zirveye_yuzde": (max(v) - bugun) / bugun * 100,
        }


# ── darboğaz ──────────────────────────────────────────────────────────────
def darbogazlar(d: dict) -> list[dict]:
    """Rolüyle, adıyla ve YUVARLANMAMIŞ yüzdesiyle; düşüşe göre sıralı."""
    out = []
    for kod, kayit in d["darbogaz"].items():
        ad, r = rol(kod)
        out.append({"kod": kod, "ad": ad, "rol": r, **kayit})
    return sorted(out, key=lambda z: z["gemi_degisim"])


def kontrol(d: dict) -> dict:
    k = [x for x in darbogazlar(d) if x["rol"] == "kontrol"]
    deg = sorted(x["gemi_degisim"] for x in k)
    return {"n": len(k), "medyan": ist.median(deg), "ortalama": ist.mean(deg),
            "en_kotu": deg[0], "en_iyi": deg[-1],
            "en_kotu_ad": min(k, key=lambda x: x["gemi_degisim"])["ad"],
            "en_iyi_ad": max(k, key=lambda x: x["gemi_degisim"])["ad"],
            "adlar": [x["ad"] for x in sorted(k, key=lambda z: z["gemi_degisim"])]}


def mevsim(d: dict, kod: str) -> dict:
    """Aynı TAKVİM penceresinin yıl yıl ortalaması.

    Taban yedi yılı kapsıyor, "şimdi" üç haftalık bir dilim: ikisini
    doğrudan kıyaslamak mevsimi değişime yazar. Bu ölçü o confounder'ı
    ayırır — pencere yıl yıl aynı günleri kapsar."""
    y = d["darbogaz"][kod].get("pencere_yillik") or {}
    yil = sorted(y)
    if len(yil) < 2:
        return {"var": False}
    son = yil[-1]
    onceki = [y[a]["gemi"] for a in yil[:-1]]
    return {"var": True, "yillar": yil, "seri": {a: y[a]["gemi"] for a in yil},
            "tanker": {a: y[a]["tanker"] for a in yil},
            "son": y[son]["gemi"], "onceki_ort": ist.mean(onceki),
            "degisim": y[son]["gemi"] / ist.mean(onceki) * 100 - 100}


def hurmuz_aylik(d: dict) -> list[dict]:
    h = d["hurmuz_aylik"]
    return [{"ay": a, "ad": f"{AY_TR[a[5:7]]} {a[:4]}", **h[a]} for a in sorted(h)]


def main() -> int:
    d = defter()
    E = Enerji(d)
    print(f"ENERJİ  {E.gunler[0]} → {E.gunler[-1]}  ({len(E.gunler)} ortak gün)")
    print(f"  depo sapması: {json.dumps(E.sapma, ensure_ascii=False)}")
    print(f"  kapsam: {d['kapsam']}")

    print("\nHÜRMÜZ AYLIK")
    for r in hurmuz_aylik(d):
        print(f"  {r['ad']:<14} {r['gemi']:7.3f} {r['tanker']:7.3f} "
              f"{r['kap_tanker']:12,.0f} ({r['gun']} gün)")

    print("\nDARBOĞAZ")
    for r in darbogazlar(d):
        print(f"  {r['ad']:<16} {r['rol']:<14} {r['gemi_taban']:8.3f} → "
              f"{r['gemi_simdi']:7.3f}  {r['gemi_degisim']:+8.3f}%  "
              f"tanker {r['tanker_degisim']:+8.3f}%")
    k = kontrol(d)
    print(f"  KONTROL n={k['n']} ortalama {k['ortalama']:+.3f}% "
          f"en kötü {k['en_kotu']:+.3f}% · {', '.join(k['adlar'])}")

    print("\nENERJİ GÜNLERİ")
    for g in [TABAN_GUN, "2026-02-27", KIRILMA, "2026-03-04", "2026-06-30",
              "2026-08-03", "2026-09-01", SON_GUN]:
        print(f"  {g}  {E.BZ[g]:7.3f} {E.CL[g]:7.3f} {E.distilat(g):8.3f} "
              f"{E.benzin(g):7.3f} {E.c321(g):7.3f}")

    print("\nDAĞILIM (3 yıl · 1 yıl)")
    for ad, fn in (("distilat", E.distilat), ("benzin", E.benzin),
                   ("3:2:1", E.c321), ("brent", lambda g: E.BZ[g])):
        for bas, et in (("2023-09-20", "3y"), ("2025-09-20", "1y")):
            z = E.dagilim(fn, bas)
            print(f"  {ad:<9} {et}  n={z['n']:<4} bugün {z['bugun']:8.3f} "
                  f"medyan {z['medyan']:8.3f} zirve {z['zirve']:8.3f} "
                  f"({z['zirve_gun']}) yüzdelik {z['yuzdelik']:5.2f} "
                  f"zirveye {z['zirveye']:6.3f} ({z['zirveye_yuzde']:+.2f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
