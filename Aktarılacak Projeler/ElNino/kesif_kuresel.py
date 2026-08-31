# -*- coding: utf-8 -*-
"""KEŞİF — açık çıkan kaynakların GERÇEKTEN ne sunduğunu ölçer.

kesif_kaynak.py hangi kapının açık olduğunu söyledi (FRED kapalı; Dünya Bankası
Pink Sheet, BLS, BIS ve ECB açık). Bu betik o kapıların ARDINDAKİNİ ölçer:
Pink Sheet'in sayfa ve sütun adları, serilerin başlangıç/bitiş tarihleri,
BLS'in kaç yıl geriye verdiği. Sütun adı uydurulup hatta girmesin.
"""
from __future__ import annotations

import io
import json
import sys
import urllib.request

import pandas as pd

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")

PINK = ("https://thedocs.worldbank.org/en/doc/"
        "18675f1d1639c7a34d463f59263ba0a2-0050012025/related/"
        "CMO-Historical-Data-Monthly.xlsx")
BLS = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
BIS = "https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/M.{}?format=csv"
ECB = ("https://data-api.ecb.europa.eu/service/data/ICP/M.U2.N.{}.4.ANR"
       "?format=csvdata&startPeriod=1990-01")


def _ham(url: str, veri: bytes | None = None, tur: str | None = None, za: int = 60) -> bytes:
    b = {"User-Agent": UA}
    if tur:
        b["Content-Type"] = tur
    req = urllib.request.Request(url, data=veri, headers=b)
    with urllib.request.urlopen(req, timeout=za) as r:
        return r.read()


def pink() -> None:
    print("══ Dünya Bankası Pink Sheet (aylık)")
    ham = _ham(PINK, za=120)
    print(f"   indirildi: {len(ham):,} bayt")
    xl = pd.ExcelFile(io.BytesIO(ham))
    print(f"   sayfalar: {xl.sheet_names}")
    for sayfa in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name=sayfa, header=None)
        print(f"\n   ── sayfa '{sayfa}'  ({df.shape[0]} satır × {df.shape[1]} sütun)")
        if df.empty:
            print("      (boş sayfa, atlandı)")
            continue
        if sayfa.lower() not in ("monthly prices", "monthly indices"):
            continue
        # Veri bloğu: ilk sütunu YYYYMxx kalıbına uyan ilk satır.
        ilk = None
        for i, v in enumerate(df.iloc[:, 0].astype(str)):
            if len(v) == 7 and v[:4].isdigit() and v[4] == "M" and v[5:].isdigit():
                ilk = i
                break
        print(f"      ilk veri satırı: {ilk}")
        for i in range(0, min(ilk if ilk is not None else 8, 8)):
            hucre = [str(x)[:26] for x in df.iloc[i].tolist()[:14]]
            print(f"      başlık[{i}] {hucre}")
        if ilk is not None:
            print(f"      ilk tarih: {df.iloc[ilk, 0]}   son tarih: {df.iloc[-1, 0]}")
            print(f"      ilk satır değerleri: {[str(x)[:10] for x in df.iloc[ilk].tolist()[:14]]}")
            # BÜTÜN sütun adları — eşleme bunlardan kurulacak, tahminle değil.
            ust = df.iloc[:ilk]
            puan = ust.apply(lambda r: sum(1 for x in r[1:]
                                           if isinstance(x, str) and x.strip()), axis=1)
            bas_i = int(puan.idxmax())
            adlar = [str(x).strip() for x in df.iloc[bas_i].tolist()[1:]]
            print(f"      SÜTUN ADLARI (başlık satırı {bas_i}, {len(adlar)} adet):")
            for j in range(0, len(adlar), 4):
                print("        " + " | ".join(f"{a[:34]:<34}" for a in adlar[j:j+4]))


def bls() -> None:
    print("\n══ BLS (anahtarsız v2) — 10 yıllık dilim sınaması")
    govde = json.dumps({"seriesid": ["CUUR0000SA0", "CUUR0000SAF1", "CUUR0000SA0L1E"],
                        "startyear": "1960", "endyear": "1969"}).encode()
    j = json.loads(_ham(BLS, govde, "application/json"))
    print(f"   durum: {j.get('status')}  mesaj: {j.get('message')}")
    for s in j.get("Results", {}).get("series", []):
        d = s.get("data") or []
        if d:
            print(f"   {s['seriesID']}: {len(d)} gözlem, "
                  f"{d[-1]['year']}-{d[-1]['period']} → {d[0]['year']}-{d[0]['period']}")
        else:
            print(f"   {s['seriesID']}: BOŞ (1960'lar yok)")


def bis() -> None:
    print("\n══ BIS — merkez bankası politika faizleri")
    for ulke in ("US", "TR", "XM"):
        try:
            ham = _ham(BIS.format(ulke)).decode("utf-8", "replace")
        except Exception as ex:
            print(f"   {ulke}: DÜŞTÜ — {str(ex)[:70]}")
            continue
        df = pd.read_csv(io.StringIO(ham))
        kol = [c for c in df.columns if c in ("TIME_PERIOD", "OBS_VALUE")]
        if len(kol) < 2:
            print(f"   {ulke}: beklenen sütunlar yok — {list(df.columns)[:12]}")
            continue
        d = df[["TIME_PERIOD", "OBS_VALUE"]].dropna()
        print(f"   {ulke}: {len(d)} ay, {d['TIME_PERIOD'].iloc[0]} → "
              f"{d['TIME_PERIOD'].iloc[-1]}, son {d['OBS_VALUE'].iloc[-1]}")


def ecb() -> None:
    print("\n══ ECB — Euro Bölgesi HICP (yıllık % değişim)")
    for kod, ad in (("000000", "manşet"), ("010000", "gıda ve alkolsüz içecek")):
        try:
            ham = _ham(ECB.format(kod)).decode("utf-8", "replace")
        except Exception as ex:
            print(f"   {ad}: DÜŞTÜ — {str(ex)[:70]}")
            continue
        df = pd.read_csv(io.StringIO(ham))
        d = df[["TIME_PERIOD", "OBS_VALUE"]].dropna()
        print(f"   {ad}: {len(d)} ay, {d['TIME_PERIOD'].iloc[0]} → "
              f"{d['TIME_PERIOD'].iloc[-1]}, son {d['OBS_VALUE'].iloc[-1]}")


def main() -> int:
    sec = [a.lower() for a in sys.argv[1:] if a.strip()]
    for ad, f in (("pink", pink), ("bls", bls), ("bis", bis), ("ecb", ecb)):
        if sec and ad not in sec:
            continue
        try:
            f()
        except Exception as ex:
            print(f"   !! {ad} keşfi düştü: {type(ex).__name__}: {str(ex)[:120]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
