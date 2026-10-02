#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRO DERSİ — dördüncü bulut geçişi: kur SÜRÜCÜLERİ (emtia, faiz farkı, risk).

Bölüm 10'un sürücü haritası her paranın en yüksek eş hareketli olduğu emtia,
faiz farkı ve risk ölçüsünü ister (NOK–Brent, CAD–WTI, AUD–bakır, USD/JPY–ABD
ile Japonya faiz farkı, altın–ABD reel faizi, ZAR–altın, CLP–bakır …). Depoda
G10 kurları, ABD, Almanya ve İngiltere getirileri ve aylık emtia endeksleri var;
günlük emtia vadelileri, öbür ülkelerin getirileri, ABD reel faizi ve bazı
paralar yok.

TEK KAYNAK, TEK KAPANIŞ. Bütün seriler aynı yerden (CNBC günlük barları) gelir;
bir kur ile bir emtianın kıyası ancak ikisinin kapanış saati biliniyorsa
kurulur. CNBC'nin döviz barı New York 17:00 kapanışıdır (depodaki G10 kurlarıyla
aynı kaynak); vadelilerin barı borsa seansının kapanışıdır, getirilerin barı
kendi piyasasının kapanışıdır. Saat farkı ölçüm katmanında haftalık örneklemle
ve gecikmeli korelasyonla ele alınır; burada yalnız ham yanıt arşivlenir.

YOKLAMA. Sembol adları TAHMİN EDİLMEZ, SORULUR: her araç için birkaç aday
sembol önce kısa bir pencereyle (son iki yıl) yoklanır, bar döndüren İLK aday
seçilir ve bütün tarihçe beş yıllık parçalarla indirilir. Hiçbir adayı tutmayan
araç rapora "kapalı" diye adayların durum kodlarıyla yazılır — "bulamadım" ile
"yok" aynı şey değildir.

ABD reel faizi ABD Hazinesi'nin günlük reel getiri eğrisidir (TIPS; par eğrisiyle
aynı sunucu, depoda çalışan yol).
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
from datetime import timedelta

import arsiv_makro as am

# araç → aday CNBC sembolleri (sırayla denenir)
ARACLAR = {
    # emtia vadelileri (yakın vade)
    "brent": ["@LCO.1", "@BRN.1"],
    "wti": ["@CL.1"],
    "bakir": ["@HG.1"],
    "altin": ["@GC.1"],
    "gumus": ["@SI.1"],
    "platin": ["@PL.1"],
    "dogalgaz": ["@NG.1"],
    "soya": ["@S.1", "@ZS.1"],
    "demir_cevheri": ["@TIO.1", "@FEF.1", "@SCO.1"],
    # devlet tahvili getirileri
    "jp2y": ["JP2Y-JP", "JP2Y"],
    "jp10y": ["JP10Y-JP", "JP10Y"],
    "au2y": ["AU2Y-AU", "AU2Y"],
    "au10y": ["AU10Y-AU", "AU10Y"],
    "ca2y": ["CA2Y-CA", "CA2Y"],
    "ca10y": ["CA10Y-CA", "CA10Y"],
    "ch2y": ["CH2Y-CH", "CH2Y"],
    "ch10y": ["CH10Y-CH", "CH10Y"],
    "nz2y": ["NZ2Y-NZ", "NZ2Y"],
    "nz10y": ["NZ10Y-NZ", "NZ10Y"],
    "no10y": ["NO10Y-NO", "NO10Y"],
    "us2y": ["US2Y"],
    "us10y": ["US10Y"],
    "de2y": ["DE2Y-DE", "DE2Y"],
    "gb2y": ["GB2Y-GB", "GB2Y"],
    # paralar (USD/XXX ya da XXX/USD; CNBC'nin kendi kotasyonu, New York 17:00)
    "nzd": ["NZD=", "NZDUSD="],
    "nok": ["NOK=", "USDNOK="],
    "sek": ["SEK=", "USDSEK="],
    "clp": ["CLP=", "USDCLP="],
    "cop": ["COP=", "USDCOP="],
    "cnh": ["CNH=", "USDCNH="],
    "krw": ["KRW=", "USDKRW="],
    "zar": ["ZAR=", "USDZAR="],
    "brl": ["BRL=", "USDBRL="],
    "mxn": ["MXN=", "USDMXN="],
    "try": ["TRY=", "USDTRY="],
    "jpy": ["JPY=", "USDJPY="],
    "eur": ["EUR=", "EURUSD="],
    "aud": ["AUD=", "AUDUSD="],
    "cad": ["CAD=", "USDCAD="],
    "gbp": ["GBP=", "GBPUSD="],
    "chf": ["CHF=", "USDCHF="],
    # hisse endeksleri (risk iştahı)
    "spx": [".SPX"],
    "nikkei": [".N225", ".NKY"],
}
ILK_YIL = 2000


def _url(sem: str, bas: str, son: str) -> str:
    return (f"https://ts-api.cnbc.com/harmony/app/bars/{urllib.parse.quote(sem)}/1D/"
            f"{bas}000000/{son}/adjusted/EST5EDT.json")


def _bar_sayisi(gv: bytes) -> int:
    try:
        j = json.loads(gv)
    except Exception:  # noqa: BLE001
        return 0
    return len(((j.get("barData") or {}).get("priceBars")) or [])


@am.kaynak("CNBC sürücüler")
def cnbc_surucu() -> dict:
    sonuc = {}
    yarin = (am.SIMDI + timedelta(days=1)).strftime("%Y%m%d")
    iki_yil = (am.SIMDI - timedelta(days=730)).strftime("%Y%m%d")
    for arac, adaylar in ARACLAR.items():
        if am.kalan() < 60:
            sonuc[arac] = {"durum": "bütçe doldu"}
            continue
        yoklama, secilen = {}, None
        for sem in adaylar:
            u = _url(sem, iki_yil, f"{yarin}000000")
            try:
                d, gv = am.al(u, sn=20, deneme=1)
            except RuntimeError as e:
                yoklama[sem] = f"hata {e}"[:80]
                continue
            n = _bar_sayisi(gv) if d == 200 else 0
            yoklama[sem] = {"durum": d, "bar": n}
            if n > 20:
                secilen = sem
                break
            time.sleep(0.5)
        if not secilen:
            sonuc[arac] = {"durum": "kapalı", "yoklama": yoklama}
            continue
        parcalar = {}
        for bas in range(ILK_YIL, am.SIMDI.year + 1, 5):
            if am.kalan() < 45:
                parcalar[bas] = "bütçe doldu"
                break
            son = f"{bas + 4}1231235959" if bas + 4 < am.SIMDI.year else f"{yarin}000000"
            u = _url(secilen, f"{bas}0101", son)
            try:
                d, gv = am.al(u, sn=40)
            except RuntimeError as e:
                parcalar[bas] = f"hata {e}"[:80]
                continue
            n = _bar_sayisi(gv) if d == 200 else 0
            if n:
                am.yaz(f"cnbc_surucu/{arac}__{secilen.replace('=', '').replace('@', '').replace('.', '_').replace('-', '_')}_{bas}.json.gz",
                       gv, u, d, not_=f"{arac} · {secilen}")
            parcalar[bas] = {"durum": d, "bar": n}
            time.sleep(0.3)
        sonuc[arac] = {"durum": "tamam", "sembol": secilen, "yoklama": yoklama, "parcalar": parcalar}
        print(f"   {arac}: {secilen} · " + ", ".join(f"{k}:{(v or {}).get('bar') if isinstance(v, dict) else v}"
                                                   for k, v in parcalar.items()), flush=True)
    return sonuc


@am.kaynak("ABD Hazinesi reel getiri")
def hazine_reel() -> dict:
    sonuc = {}
    for yil in range(2003, am.SIMDI.year + 1):
        if am.kalan() < 60:
            break
        u = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
             f"daily-treasury-rates.csv/{yil}/all?type=daily_treasury_real_yield_curve"
             f"&field_tdr_date_value={yil}&page&_format=csv")
        try:
            d, gv = am.al(u, sn=60)
        except RuntimeError as e:
            sonuc[yil] = f"hata {e}"[:100]
            continue
        am.yaz(f"hazine/reel_{yil}.csv.gz", gv, u, d)
        sonuc[yil] = {"durum": d, "bayt": len(gv)}
    return sonuc


def main() -> int:
    am.HAM.mkdir(parents=True, exist_ok=True)
    for f in (hazine_reel, cnbc_surucu):
        f()
    kp = am.HAM / "kunye_bulut.json"
    eski = json.loads(kp.read_text(encoding="utf-8")) if kp.exists() else {}
    eski.update(am.KUNYE)
    kp.write_text(json.dumps(dict(sorted(eski.items())), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    rp = am.HAM / "rapor.json"
    rapor = json.loads(rp.read_text(encoding="utf-8")) if rp.exists() else {}
    rapor[am.SIMDI.strftime("%Y-%m-%dT%H%M") + "_surucu"] = am.RAPOR
    rp.write_text(json.dumps(rapor, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("\n══ ÖZET")
    for ad, r in am.RAPOR.items():
        print(f"  {ad:26s} {r.get('durum')}  {r.get('sure_sn', '')} sn  {str(r.get('hata', ''))[:160]}")
    s = (am.RAPOR.get("CNBC sürücüler") or {})
    kapali = [a for a, v in s.items() if isinstance(v, dict) and v.get("durum") == "kapalı"]
    print(f"  kapalı araçlar: {kapali}")
    print(f"  toplam {round(time.monotonic() - am.T0)} sn · {len(am.KUNYE)} ham dosya")
    return 0


if __name__ == "__main__":
    sys.exit(main())
