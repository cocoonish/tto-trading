#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRO DERSİ — dört hesap aracının açılış değerleri: ölçüm dosyasından arac.json.

Araçlar (`site/src/components/Makro*.astro`) varsayılan girdilerini derleme
anında `site/src/data/makro-kur-ve-faiz/arac.json`dan okur; bu dosya ELLE
yazılmaz, `veri/olcum.json`dan bu eşlemeyle üretilir. `dogrula.py` aynı
`kur()` fonksiyonunu çağırıp dosyayla kıyaslar (yalnız standart kütüphane).

  python3 arac_veri.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
CIKTI = KOK / "site/src/data/makro-kur-ve-faiz/arac.json"


def _y(x: float, b: int = 2) -> float:
    return round(float(x), b)


def _sayi(x: float, b: int = 1) -> str:
    s = f"{abs(x):,.{b}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return ("−" if x < 0 and float(s.replace(".", "").replace(",", ".")) != 0 else "") + s


def _yz(x: float, b: int = 1) -> str:
    s = "%" + _sayi(abs(x), b)
    return ("−" + s) if x < 0 and float(_sayi(abs(x), b).replace(".", "").replace(",", ".")) != 0 else s


def _ay(iso: str) -> str:
    return f"{iso[5:7]}.{iso[:4]}"


def _gun(iso: str) -> str:
    return f"{iso[8:10]}.{iso[5:7]}.{iso[:4]}"


def _reel(i: float, pi: float) -> float:
    return ((1 + i / 100) / (1 + pi / 100) - 1) * 100


def kur(o: dict) -> dict:
    t = o["b03"]["arac_taylor"]
    b = o["b06"]["arac_borc"]
    r = o["b07"]["arac_redk"]
    s = o["b07"]["p7a"]["sapma"]
    tam = o["b07"]["p7a"]["tufe"]["tam"]
    k = o["b11"]["arac_kur"]
    acik_alt, acik_ust = t["acik_alt_puan"], t["acik_ust_puan"]
    y = t["yabanci"]
    R = _reel(t["politika_yuzde"], t["pi_pka_yuzde"]) - _reel(y["politika_abd_yuzde"], y["tufe_abd_yillik_yuzde"])
    return {
        "taylor": {
            "tarih_metin": f"{_ay(t['ay'] + '-01')} (politika faizi {_gun(t['politika_gun'])})",
            "pi_anket": _y(t["pi_pka_yuzde"]), "pi_gerceklesen": _y(t["pi_gercek_yuzde"]),
            "pi_hedef": _y(t["pi_hedef_yuzde"]), "r_yildiz": _y(t["r_yildiz_varsayilan_yuzde"]),
            "phi_pi": _y(1 + t["katsayi_pi"]), "phi_y": _y(t["katsayi_acik"]),
            "acik_orta": _y((acik_alt + acik_ust) / 2), "acik_alt": _y(acik_alt), "acik_ust": _y(acik_ust),
            "acik_alt_metin": _yz(acik_alt, 1), "acik_ust_metin": _yz(acik_ust, 1),
            "politika": _y(t["politika_yuzde"]), "i_yabanci": _y(y["politika_abd_yuzde"]),
            "pi_yabanci": _y(y["tufe_abd_yillik_yuzde"]),
        },
        "borc": {
            "tarih_metin": b["ceyrek"].replace("Q", "Ç"),
            "d": _y(b["d_yuzde"], 1), "alfa": _y(b["alfa_yuzde"], 1), "i": _y(b["ortuk_faiz_yuzde"], 1),
            "g": _y(b["nominal_buyume_yuzde"], 1), "pb": _y(b["fdd_gsyh"], 2),
        },
        "redk": {
            "tarih_metin": _ay(s["tarih"]),
            "redk": _y(s["redk_tufe"]), "denge_tam": _y(s["ortalama_tam_endeks"]),
            "denge_2003": _y(s["ortalama_2003_endeks"]),
            "rho_mu": _y(r["rho_aylik"], 4), "rho_alt": _y(r["rho_alt90"], 4), "rho_ols": _y(tam["rho_ols"], 4),
        },
        "kur": {
            "tarih_metin": _gun(k["tarih"]),
            "i_tl": _y(k["i_tl_yuzde"]), "i_usd": _y(k["i_usd_yuzde"]),
            "R": _y(R), "redk_sapma": _y(s["sapma_tam_log"] * 100, 1),
        },
    }


def main() -> int:
    o = json.loads((BURASI / "veri" / "olcum.json").read_text(encoding="utf-8"))
    a = kur(o)
    CIKTI.parent.mkdir(parents=True, exist_ok=True)
    CIKTI.write_text(json.dumps(a, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"── {CIKTI.relative_to(KOK)} yazıldı")
    return 0


if __name__ == "__main__":
    sys.exit(main())
