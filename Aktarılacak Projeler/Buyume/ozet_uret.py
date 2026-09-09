# -*- coding: utf-8 -*-
"""Büyüme hattı — ÖZET katmanı: ozet.json + uyarilar.json (hat klasörünün KÖKÜ).

Sayfa metnindeki oynak sayılar <Deger proje anahtar> ile buraya bağlanır;
JSON tazelenince metin MDX'e dokunmadan güncellenir (CLAUDE.md kural 5).

KOPYA SÖZLEŞMESİ. Bu katman siteye HİÇBİR ŞEY yazmaz. 09.09.2026'da ölçüldü:
özet doğrudan `site/public/projeler/buyume/ozet.json`a yazılıyordu, yani hattın
çıktısı kopya sözleşmesinin (guncelle.py) dışından siteye giriyordu. İki sonucu
vardı ve ikisi de sessizdi — (1) "veri geriye gidemez" kapısı hattın KENDİ
ürettiği ozet.json'u okur ve o dosya hiç yazılmadığı için kapı bu hatta hiç
kurulamıyordu; (2) uyarilar.json diye bir dosya hiç üretilmiyordu, yani veri ve
ölçüm katmanlarının uyarıları ne sayfaya ne de okur dili kapılarına (sayfa
sınavı 17, guncelle.okur_dili_bulgulari) ulaşıyordu. Artık iki dosya da klasör
kökünde yazılır; siteye kopyalamak guncelle.py'nin işidir.

Ağa çıkmayan iş AYRI fonksiyonlarda (`ozet_kur`, `uyarilar_kur`) durur; duman
sınaması onları gerçek çerçeveyle çağırır (bkz. duman.py).
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

PROJE = Path(__file__).resolve().parent
DATA = PROJE / "data"


def ozet_kur(M: dict) -> dict:
    """Ölçüm çıktısından sayfanın okuduğu düz anahtar sözlüğü.

    `_tarih` hattın SAATİDİR (çeyreğin son ayı, AA.YYYY), `_ceyrek` okur
    ETİKETİDİR ("2026-Ç2") — ikisi ayrı anahtarda durur, çünkü bir saat
    biçim sözleşmesinden geçer (bayatlık denetimi, şekil damgası), bir etiket
    okura basılır.
    """
    o: dict = {
        "_tarih": M["_tarih"],
        "_ceyrek": M["_ceyrek"],
        "buyume_yillik": M["buyume_yillik"],
        "buyume_ceyreklik": M["buyume_ceyreklik"],
        "ayristirma_tabani": M["ayristirma_tabani"],
        "ayarlama_farki": M["ayarlama_farki"],
        "agirlik_donemi": M["agirlik_donemi"],
        "katki_toplami": M["katki_toplami"],
        "artik": M["artik"],
    }
    for kod, v in M["katkilar"].items():
        o[f"k_{kod.lower()}_buyume"] = v["buyume"]
        o[f"k_{kod.lower()}_katki"] = v["katki"]
        o[f"k_{kod.lower()}_agirlik"] = v["agirlik"]
    for kod, v in M["sektorler"].items():
        o[f"s_{kod.lower()}_buyume"] = v["buyume"]
        o[f"s_{kod.lower()}_agirlik"] = v["agirlik"]
    for kod, v in M["dayaniklilik"].items():
        o[f"d_{kod.lower()}_buyume"] = v["nominal_buyume"]
        o[f"d_{kod.lower()}_pay"] = v["pay"]
    return o


def uyarilar_kur(kunye: dict, M: dict) -> dict:
    """Veri + ölçüm katmanlarının uyarıları, tek dosyada ve TARİHLİ.

    Kaynak iki yerde birikiyor (veri.py → kunye.json, metrik.py → metrik.json)
    ve ikisi de yalnız hattın kendi klasöründe duruyordu. Okura giden koşu
    kaydı bu dosyadır; boş liste de yazılır — "uyarı yok" ile "dosya yok"
    aynı görünmemeli.
    """
    u: list[str] = []
    for x in (kunye.get("uyarilar") or []) + (M.get("uyarilar") or []):
        m = str(x).strip()
        if m and m not in u:
            u.append(m)
    return {
        "ceyrek": M.get("_ceyrek", ""),
        "veri_tarihi": M.get("_tarih", ""),
        "kosum": dt.date.today().isoformat(),
        "uyarilar": u,
    }


def main() -> int:
    M = json.loads((DATA / "metrik.json").read_text(encoding="utf-8"))
    try:
        kunye = json.loads((DATA / "kunye.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        kunye = {}

    o = ozet_kur(M)
    (PROJE / "ozet.json").write_text(
        json.dumps(o, ensure_ascii=False, indent=1), encoding="utf-8")
    u = uyarilar_kur(kunye, M)
    (PROJE / "uyarilar.json").write_text(
        json.dumps(u, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"── özet yazıldı: ozet.json ({len(o)} alan) · "
          f"uyarilar.json ({len(u['uyarilar'])} uyarı)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
