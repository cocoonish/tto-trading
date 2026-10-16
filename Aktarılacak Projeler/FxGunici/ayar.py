#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Proje ayarını (`ayar.toml`) okur ve sınar.

Tek tanım: pariteler, kapsam, örneklem sınırı ve maliyet ızgarası yalnız
`ayar.toml`da durur. Bir alan eksik ya da tutarsızsa betik DÜŞER — varsayılan
bir değerle sessizce sürmek, ayarı değiştiren kişinin değişikliğinin hiç
uygulanmadığını görmemesi demektir.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
VERI = BURASI / "veri"
DUKA = VERI / "dukascopy"


@dataclass(frozen=True)
class Ayar:
    ciftler: tuple[str, ...]
    baslangic: date
    bitis: date
    nokta: dict[str, float]
    pip: dict[str, float]
    es_zamanli: int
    zaman_asimi_sn: float
    deneme: int
    butce_dk: float
    hiz_baslangic: float
    hiz_tavan: float
    ic_baslangic: date
    ic_bitis: date
    dis_baslangic: date
    zaman_dilimleri: tuple[int, ...]
    gun_sonu_et: str
    kayma_pip: tuple[float, ...]
    haber_kayma_pip: float
    haber_pencere_dk: tuple[int, int]

    def nokta_pip(self, cift: str) -> int:
        """Bir pipteki nokta sayısı (tam sayı olmalı: 10)."""
        oran = self.pip[cift] / self.nokta[cift]
        if abs(oran - round(oran)) > 1e-9:
            raise ValueError(f"{cift}: pip/nokta oranı tam sayı değil ({oran})")
        return int(round(oran))


def _gun(s: str) -> date:
    return date.fromisoformat(s)


def oku(yol: Path | None = None) -> Ayar:
    yol = yol or (BURASI / "ayar.toml")
    with open(yol, "rb") as f:
        h = tomllib.load(f)
    v, i, o, s = h["veri"], h["indirme"], h["orneklem"], h["islem"]
    a = Ayar(
        ciftler=tuple(v["ciftler"]),
        baslangic=_gun(v["baslangic"]),
        bitis=_gun(v["bitis"]),
        nokta=dict(v["nokta"]),
        pip=dict(v["pip"]),
        es_zamanli=int(i["es_zamanli"]),
        zaman_asimi_sn=float(i["zaman_asimi_sn"]),
        deneme=int(i["deneme"]),
        butce_dk=float(i["butce_dk"]),
        hiz_baslangic=float(i["hiz_baslangic"]),
        hiz_tavan=float(i["hiz_tavan"]),
        ic_baslangic=_gun(o["ic_baslangic"]),
        ic_bitis=_gun(o["ic_bitis"]),
        dis_baslangic=_gun(o["dis_baslangic"]),
        zaman_dilimleri=tuple(int(x) for x in s["zaman_dilimleri"]),
        gun_sonu_et=str(s["gun_sonu_et"]),
        kayma_pip=tuple(float(x) for x in s["kayma_pip"]),
        haber_kayma_pip=float(s["haber_kayma_pip"]),
        haber_pencere_dk=tuple(int(x) for x in s["haber_pencere_dk"]),
    )
    hata = []
    for c in a.ciftler:
        if c not in a.nokta or c not in a.pip:
            hata.append(f"{c}: nokta/pip tanımı yok")
        else:
            a.nokta_pip(c)
    if not a.baslangic <= a.ic_bitis < a.dis_baslangic <= a.bitis:
        hata.append("tarih sırası bozuk: baslangic ≤ ic_bitis < dis_baslangic ≤ bitis olmalı")
    if any(tf <= 0 or 60 % tf for tf in a.zaman_dilimleri):
        hata.append(f"zaman dilimi 60'ı tam bölmeli: {a.zaman_dilimleri}")
    if hata:
        raise SystemExit("ayar.toml geçersiz:\n  " + "\n  ".join(hata))
    return a


if __name__ == "__main__":
    a = oku()
    print(a)
