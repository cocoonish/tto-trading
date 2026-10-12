#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BRENT 125–150 SENARYOSU — dördüncü arşiv geçişi: VADE EĞRİSİ.

Neden gerekli (ölçüldü, 12.10.2026): ön vade Brent serisi her ayın ilk iş günü
bir kontrattan ötekine ATLAR ve 2026'nın geriye eğimli (backwardation) eğrisinde
bu atlama tek başına büyük bir "hareket" yazar — 01.04.2026'da Brent −%15,7,
aynı gün WTI −%1,3. Her 21 iş günlük pencere tam bir devir içerir. İki soru buna
bağlı ve ikisi de eğri ister:

  1. Kıyas serisinin kendisi: devirden arındırılmış bir Brent getirisi için devir
     günü YENİ kontratın bir önceki günkü fiyatı gerekir (ikinci vade).
  2. Senaryonun kendisi: "bir ay sonra ön vade 125 dolar" demek, bugünün ikinci
     vadesinin (Ocak 2027) 125'e çıkması demektir; bugünkü ön vadenin değil.

Kaynaklar: CNBC sürekli seri ikinci ve sonraki vadeler (@LCO.2 …; yoklanır,
sembol adı tahmin edilmez SORULUR) ve Yahoo'da hâlâ listeli tek tek kontratlar
(NYMEX Brent mali vadelisi BZ, WTI CL, ULSD HO; vadesi dolan kontrat Yahoo'dan
silinir, o yüzden yalnız BUGÜNKÜ eğri kurulabilir).

Yardımcılar ve ilkeler `arsiv_brent.py` başlığında; künye `kunye_egri.json`.
"""
from __future__ import annotations

import sys
import time
from datetime import timedelta

import arsiv_brent as ab

SUREKLI = {
    "brent_2": ["@LCO.2", "@BRN.2"], "brent_3": ["@LCO.3", "@BRN.3"],
    "brent_6": ["@LCO.6", "@BRN.6"], "brent_12": ["@LCO.12", "@BRN.12"],
    "wti_2": ["@CL.2"], "kalorifer_2": ["@HO.2"],
}
AY_KODU = "FGHJKMNQUVXZ"


def _kodlar(kok: str, bas: tuple[int, int], son: tuple[int, int]) -> list[str]:
    a, b = bas[0] * 12 + bas[1] - 1, son[0] * 12 + son[1] - 1
    return [f"{kok}{AY_KODU[m % 12]}{(m // 12) % 100:02d}.NYM" for m in range(a, b + 1)]


@ab.kaynak("CNBC sürekli vadeler")
def cnbc_surekli() -> dict:
    sonuc = {}
    yarin = (ab.SIMDI + timedelta(days=1)).strftime("%Y%m%d")
    iki_yil = (ab.SIMDI - timedelta(days=730)).strftime("%Y%m%d")
    for arac, adaylar in SUREKLI.items():
        if ab.kalan() < 300:
            sonuc[arac] = {"durum": "bütçe doldu"}
            continue
        secilen, yoklama = None, {}
        for sem in adaylar:
            n, d = 0, 0
            for deneme in range(3):
                try:
                    d, gv = ab.al(ab._cnbc_url(sem, iki_yil, f"{yarin}000000"), sn=25, deneme=1)
                except RuntimeError:
                    d, gv = 0, b""
                n = ab._bar_sayisi(gv) if d == 200 else 0
                if n > 20:
                    break
                time.sleep(3.0 * (deneme + 1))
            yoklama[sem] = {"durum": d, "bar": n}
            if n > 20:
                secilen = sem
                break
        if not secilen:
            sonuc[arac] = {"durum": "kapalı", "yoklama": yoklama}
            print(f"   {arac}: kapalı {yoklama}", flush=True)
            continue
        parcalar = {}
        ilk = ab.CNBC_ILK_UZUN if arac.startswith("brent") else ab.CNBC_ILK
        for bas in range(ilk, ab.SIMDI.year + 1, 5):
            if ab.kalan() < 240:
                parcalar[bas] = "bütçe doldu"
                break
            son = f"{bas + 4}1231235959" if bas + 4 < ab.SIMDI.year else f"{yarin}000000"
            u = ab._cnbc_url(secilen, f"{bas}0101", son)
            n, d = 0, 0
            for deneme in range(3):
                try:
                    d, gv = ab.al(u, sn=40)
                except RuntimeError:
                    d, gv = 0, b""
                n = ab._bar_sayisi(gv) if d == 200 else 0
                if n or bas < 2000:
                    break
                time.sleep(3.0 * (deneme + 1))
            if n:
                ab.yaz(f"cnbc_egri/{arac}__{ab._dosya_adi(secilen)}_{bas}.json.gz", gv, u, d,
                       not_=f"{arac} · {secilen}")
            parcalar[bas] = {"durum": d, "bar": n}
            time.sleep(0.4)
        sonuc[arac] = {"durum": "tamam", "sembol": secilen, "yoklama": yoklama, "parcalar": parcalar}
        print(f"   {arac}: {secilen} · " + ", ".join(
            f"{k}:{v.get('bar') if isinstance(v, dict) else v}" for k, v in parcalar.items()), flush=True)
    return sonuc


@ab.kaynak("Yahoo kontratlar")
def yahoo_kontratlar() -> dict:
    try:
        import yfinance as yf
    except ImportError as e:
        raise RuntimeError(f"yfinance yok: {e!r}") from e
    kodlar = (_kodlar("BZ", (2026, 11), (2028, 12)) + _kodlar("CL", (2026, 11), (2027, 12))
              + _kodlar("HO", (2026, 11), (2027, 6)))
    sonuc = {}
    for kod in kodlar:
        if ab.kalan() < 120:
            sonuc[kod] = "bütçe doldu"
            continue
        h = None
        for deneme in range(3):
            try:
                h = yf.Ticker(kod).history(period="1y", interval="1d", auto_adjust=False)
                break
            except Exception as e:  # noqa: BLE001 — 429 bir ölçüm değildir
                sonuc[kod] = f"hata {type(e).__name__}: {e}"[:120]
                time.sleep(4 * (deneme + 1))
        if h is None or h.empty:
            sonuc.setdefault(kod, "boş")
            print(f"   {kod}: {sonuc[kod]}", flush=True)
            time.sleep(0.6)
            continue
        h = h.copy()
        h.index = [t.strftime("%Y-%m-%d") for t in h.index]
        kolon = [c for c in ("Open", "High", "Low", "Close", "Volume") if c in h.columns]
        metin = h[kolon].to_csv(index_label="tarih", float_format="%.6f", lineterminator="\n").encode("utf-8")
        ab.yaz(f"yahoo_egri/{ab._dosya_adi(kod)}.csv.gz", metin, f"yfinance:{kod}:period=1y", 200, not_=kod)
        sonuc[kod] = {"satir": int(len(h)), "ilk": h.index[0], "son": h.index[-1], "son_kapanis": float(h["Close"].iloc[-1])}
        print(f"   {kod}: {len(h)} satır {h.index[0]}→{h.index[-1]} · {h['Close'].iloc[-1]:.2f}", flush=True)
        time.sleep(0.6)
    return sonuc


def main() -> int:
    ab.HAM.mkdir(parents=True, exist_ok=True)
    yahoo_kontratlar()
    cnbc_surekli()
    ab.kaydet("egri")
    return 0 if ab.KUNYE else 1


if __name__ == "__main__":
    sys.exit(main())
