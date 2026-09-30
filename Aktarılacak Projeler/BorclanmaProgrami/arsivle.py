#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ARŞİVLE — yazının girdilerini yayım gününün hâliyle dondurur.

Analiz yayımlandığı günün metnidir (karar 08.09.2026). Sayıları üreten
girdiler canlı hat dosyalarında kalsaydı, hat bir sonraki koşuda onları
değiştirir ve yazının hiçbir sayısı yeniden üretilemezdi. Bu betik o
girdilerin yayım günkü kopyasını `veri/` altına sıkıştırıp künyesine
(sıkıştırılmamış içeriğin sha256'sı) yazar. VAR OLANIN ÜZERİNE YAZMAZ:
yeni bir çıpa yeni bir arşivdir (`--zorla` yalnız bilinçli yeniden kurulum).

Girdiler:
  · strateji_arsivi — HMB duyuru akışındaki bütün strateji belgelerinin
    pypdf metni (keşif koşusu 30.09.2026, koşu kaydından çözülen yük)
  · ihale — Hazine İhraç hattının ihale veri seti
  · takvim_* — hattın takvim arşivinin üç sürümü (yeni, karşı olgu, 31.08)
  · kiyas — takvim satırlarının kıyas tahminleri, BUGÜNKÜ yöntemle; yöntem
    ileride değişse de yazının karşı olgusu bu dosyadan yeniden kurulur
  · strateji_gecmisi, hedef_gerceklesme, vade_analizi — hattın defterleri
  · piyasa — yazının andığı eğri, fonlama, anket, enflasyon sayıları

Koşum:  python3 arsivle.py <strateji_arsivi.json> [--zorla]
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
HAT = KOK / "Aktarılacak Projeler/hazineihrac"
VERI = BURASI / "veri"
CIPA = "2026-09-30"

TAKVIMLER = {
    "takvim_yeni": "2026-09-30_Ekim--Aralık-2026-İç-Borçlanma-Stratejisi.csv",
    "takvim_karsi": "2026-09-27_Eylül--Kasım-2026-İç-Borçlanma-Stratejisi.csv",
    "takvim_0831": "2026-08-31_Eylül--Kasım-2026-İç-Borçlanma-Stratejisi.csv",
}

PIYASA = {
    "dibs-verim-egrisi": ["_tarih", "spot_3a", "spot_6a", "spot_1y", "spot_2y", "spot_3y",
                          "spot_5y", "spot_7y", "spot_9y", "spot_9y_tarih", "egim_2y5y",
                          "forward_1y1y", "forward_2y1y", "forward_2y3y", "pka_12a",
                          "pka_24a", "pka_5y", "pka_faiz_12a", "pka_faiz_24a", "anket_ay",
                          "basabas_5y", "risk_primi_5y"],
    "fonlama-likidite": ["_tarih", "politika", "tlref", "koridor_ust", "koridor_alt"],
    "enflasyon": ["_tarih", "baz_momentum_aylik", "c_3a", "c_12a", "tufe_12a"],
    "butce-borc": ["_tarih", "faiz_12a", "faiz_vergi", "faiz_gsyh"],
}


def _yaz(ad: str, ham: bytes, kunye: dict, zorla: bool) -> None:
    hedef = VERI / f"{ad}.gz"
    if hedef.exists() and not zorla:
        eski = hashlib.sha256(gzip.decompress(hedef.read_bytes())).hexdigest()
        if eski != hashlib.sha256(ham).hexdigest():
            raise SystemExit(f"  ! {hedef.name} var ve içeriği farklı — üzerine yazılmaz (--zorla)")
    hedef.write_bytes(gzip.compress(ham, 9, mtime=0))
    kunye["dosyalar"][hedef.name] = {"sha256": hashlib.sha256(ham).hexdigest(),
                                     "bayt": len(ham)}
    print(f"  ✓ {hedef.name}  {len(ham):>9} bayt")


def _kiyas() -> dict:
    """Takvim satırlarının kıyas tahmini, hattın bugünkü yöntemiyle."""
    sys.path.insert(0, str(HAT))
    import pandas as pd
    from main import TreasuryAuctionScraper as T  # noqa: E402
    import vade_proj as V  # noqa: E402
    hist = V._gecmis()
    out = {}
    for ad, dosya in TAKVIMLER.items():
        if ad == "takvim_0831":
            continue        # 31.08 planı yayımlandığı hâliyle okunur, yeniden kestirilmez
        d = pd.read_csv(HAT / "takvim_arsiv" / dosya, encoding="utf-8-sig")
        satirlar = []
        for _, r in d.iterrows():
            kayit = {"ihale": r["İhale Tarihi"], "senet": r["Senet Tanımı"],
                     "terim": r["Vade Terimi"], "itfa": r["İtfa Tarihi"], "yontem": r["Yöntem"]}
            if "hale" in str(r["Yöntem"]):
                yf = str(r["Yöntem"]).lower().replace("̇", "").replace("ı", "i")
                yen = True if "yeniden" in yf else (False if "ilk" in yf else None)
                ym = re.match(r"(\d+)\s*Yıl", str(r["Vade Terimi"]))
                res = T._forecast_from_comparables(r["Senet Tanımı"], r["İtfa Tarihi"],
                                                   float(ym.group(1)) if ym else None,
                                                   hist, yeniden=yen)
                kayit.update({"ham": res["raw_amt"], "kiyas": res["basis"], "n": res["n"],
                              "btc": res["btc"], "son_kiyas": res["last_date"]})
            satirlar.append(kayit)
        out[ad] = satirlar
    return {"yontem": "kıyasların son üç satışının ortalaması (hattın bugünkü yöntemi)",
            "veri_sonu": hist["_d"].max().strftime("%Y-%m-%d"), "takvimler": out}


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    zorla = "--zorla" in sys.argv
    VERI.mkdir(exist_ok=True)
    kp = VERI / "kunye.json"
    kunye = json.loads(kp.read_text(encoding="utf-8")) if kp.exists() else {}
    kunye.update({"cipa": CIPA, "dosyalar": kunye.get("dosyalar", {})})

    arsiv = Path(sys.argv[1]).read_bytes()
    json.loads(arsiv)                                  # geçerli JSON mu
    _yaz("strateji_arsivi.json", arsiv, kunye, zorla)
    _yaz("ihale.csv", (HAT / "hazine_ihale_verileri.csv").read_bytes(), kunye, zorla)
    for ad, dosya in TAKVIMLER.items():
        _yaz(f"{ad}.csv", (HAT / "takvim_arsiv" / dosya).read_bytes(), kunye, zorla)
    _yaz("strateji_gecmisi.json", (HAT / ".strategy_history.json").read_bytes(), kunye, zorla)
    _yaz("hedef_gerceklesme.csv", (HAT / "hazine_hedef_gerceklesme.csv").read_bytes(), kunye, zorla)
    _yaz("vade_analizi.csv", (HAT / "hazine_vade_analizi.csv").read_bytes(), kunye, zorla)
    _yaz("kiyas.json", json.dumps(_kiyas(), ensure_ascii=False, indent=1).encode("utf-8"),
         kunye, zorla)
    piyasa = {}
    for hat, anahtarlar in PIYASA.items():
        oz = json.loads((KOK / "site/public/projeler" / hat / "ozet.json").read_text(encoding="utf-8"))
        piyasa[hat] = {k: oz.get(k) for k in anahtarlar}
    _yaz("piyasa.json", json.dumps(piyasa, ensure_ascii=False, indent=1).encode("utf-8"),
         kunye, zorla)
    kunye["kaynak"] = {
        "strateji_arsivi": "HMB duyuru akışı (hmb.gov.tr portal/v2/posts, kamu-finansmani); "
                           "bulut keşif koşusu 36728396074, 30.09.2026",
        "ihale": "Hazine İhraç hattı ihale veri seti (HMB ihale sonuç duyuruları)",
        "takvim": "Hazine İhraç hattının takvim arşivi",
        "piyasa": "DİBS Verim Eğrisi, Fonlama ve Likidite, Enflasyon, Bütçe ve Borç hatları",
    }
    kp.write_text(json.dumps(kunye, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  künye: {len(kunye['dosyalar'])} dosya, çıpa {CIPA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
