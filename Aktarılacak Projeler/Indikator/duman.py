#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TTO · Yapı ve Momentum — DUMAN SINAMASI (ağa çıkmaz, saniyeler sürer).

Her madde bu depoda gerçekten yapılmış bir kusurun sınıfından; hiçbiri
varsayımsal değil. Düşen madde ENGEL'dir: yayın kapısı (sayfa sınavı 27)
bu dosyayı koşturur.

  ① Geleceğe bakma: seri i'de kırpılınca i'deki ilan değişmez (bar bar).
  ② Ders örneği: harmonik 3.3 Gartley'si PRZ 40,43–40,51 ve teyit verir.
  ③ Pine input öntanımlıları = yapi_referans.SABIT (iki dosya).
  ④ Diverjans tablosu Pine dizileri = DIV_TABLO (iki dosya, 25 satır).
  ⑤ Harmonik bantlar Pine f_klasik çağrıları = HARMONIK (altı kalıp).
  ⑥ Olasılık bloğu = JSON'dan türetilen (pine_sabit --denetle).
  ⑦ pine_denetle on ölçüt iki dosyada geçer.
  ⑧ Emir mekaniği: hedef → +R · stop → −1 · aynı bar → stop+belirsiz ·
     dolmayan limit → None · ufuk dolunca R (−1, hedefR) içinde ·
     boşlukla doluşta payda PLANLANAN risk.
  ⑨ BOS yalnız onaylı swing'e karşı: koşan uçta kırılım olayı üretilmez.
  ⑩ Backtest JSON'un künyesi kural kaynağını ve spread varsayımını taşır;
     her TF için beş paket satırı var.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent
DEPO = KOK.parents[1]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(DEPO / "site" / "tools"))
import backtest as B                       # noqa: E402
import pine_sabit                          # noqa: E402
import veri                                # noqa: E402
import yapi_referans as Y                  # noqa: E402
from brooks_referans import Seri           # noqa: E402

PINE_YAPI = DEPO / "site" / "public" / "indikatorler" / "tto-yapi.pine"
PINE_MOM = DEPO / "site" / "public" / "indikatorler" / "tto-momentum.pine"
JSON = DEPO / "site" / "src" / "data" / "yapi_backtest.json"

# Pine input adı → SABIT anahtarı (dosya bazında hangileri geçmeli)
PINE_ESLEME = {
    "kSwing": "k_swing", "kIc": "k_ic", "atrN": "atr_n", "rsiN": "rsi_n", "emaN": "ema_n",
    "bbN": "bb_n", "bbK": "bb_k", "dispGovde": "disp_govde", "dispKat": "disp_kat",
    "dispPencere": "disp_pencere", "fvgAtr": "fvg_atr", "esitAtr": "esit_atr", "asimAtr": "asim_atr",
    "sweepPencere": "sweep_pencere", "oteAlt": "ote_alt", "oteUst": "ote_ust", "przAzami": "prz_azami_xa",
    "tarihce": "tarihce",
}


def _sina(hata: list[str], kosul: bool, mesaj: str) -> None:
    if not kosul:
        hata.append(mesaj)


def sentetik(noktalar, adim_bar=6, w=0.004) -> Seri:
    o, h, l, c = [], [], [], []
    for p0, p1 in zip(noktalar, noktalar[1:]):
        for k in range(adim_bar):
            a = p0 + (p1 - p0) * k / adim_bar
            b = p0 + (p1 - p0) * (k + 1) / adim_bar
            o.append(a); c.append(b)
            son = k == adim_bar - 1
            h.append(max(a, b) + (w if son and p1 > p0 else 0.001))
            l.append(min(a, b) - (w if son and p1 < p0 else 0.001))
    return Seri(o, h, l, c, [1_700_000_000 + 3600 * i for i in range(len(c))])


def pine_inputlar(yol: Path) -> dict[str, float]:
    out = {}
    for m in re.finditer(r"^\s*(\w+)\s*=\s*input\.(int|float|bool)\(\s*([^,\)]+)", yol.read_text(encoding="utf-8"), re.M):
        ad, tur, deger = m.group(1), m.group(2), m.group(3).strip()
        if tur == "bool":
            continue
        try:
            out[ad] = float(deger)
        except ValueError:
            pass
    return out


def pine_diziler(yol: Path) -> dict[str, list[float]]:
    out = {}
    for m in re.finditer(r"^var\s+(\w+)\s*=\s*array\.from\(([^\)]*)\)", yol.read_text(encoding="utf-8"), re.M):
        out[m.group(1)] = [float(x) for x in m.group(2).split(",")]
    return out


def kos() -> list[str]:
    hata: list[str] = []
    # ① geleceğe bakma (kısa dilim, bar bar; üretim yolu 22 sn/900 bar)
    s = veri.oku("eurusd-1h").kirp(760)
    h = Y.gelecege_bakma_sinamasi(s, bas=400, adim=1)
    _sina(hata, not h, f"① geleceğe bakma: {len(h)} hata · {h[:1]}")
    # ② ders örneği
    sy = Y.Yapi(sentetik([41, 40, 42, 40.77, 41.74, 40.45, 41.3, 42.5]), {"k_swing": 2})
    g = [p for p in sy.przler if p.ad == "Gartley"]
    _sina(hata, len(g) == 1 and abs(g[0].alt - 40.426) < 0.01 and abs(g[0].ust - 40.506) < 0.01 and g[0].durum == "teyit",
          f"② ders Gartley örneği: {[(p.ad, round(p.alt, 3), round(p.ust, 3), p.durum) for p in sy.przler]}")
    # ③ Pine öntanımlıları
    for yol in (PINE_YAPI, PINE_MOM):
        inp = pine_inputlar(yol)
        for pad, sab in PINE_ESLEME.items():
            if pad in inp:
                _sina(hata, abs(inp[pad] - float(Y.SABIT[sab])) < 1e-9, f"③ {yol.name}: {pad}={inp[pad]} ≠ SABIT[{sab}]={Y.SABIT[sab]}")
        _sina(hata, "kSwing" in inp or yol is PINE_MOM, f"③ {yol.name}: kSwing girdisi yok")
    # ④ diverjans tablosu
    for yol in (PINE_YAPI, PINE_MOM):
        dz = pine_diziler(yol)
        for ad, sutun in (("tabTip", 0), ("tabBb", 1), ("tabRsi", 2), ("tabTr", 3), ("tabId", 6)):
            bekl = [float(r[sutun]) for r in Y.DIV_TABLO]
            _sina(hata, dz.get(ad) == bekl, f"④ {yol.name}: {ad} DIV_TABLO ile aynı değil")
        if yol is PINE_YAPI:
            for ad, sutun in (("tabSl", 4), ("tabTp", 5)):
                bekl = [float(r[sutun]) for r in Y.DIV_TABLO]
                _sina(hata, dz.get(ad) == bekl, f"④ {yol.name}: {ad} DIV_TABLO ile aynı değil")
    # ⑤ harmonik bantlar
    metin = PINE_YAPI.read_text(encoding="utf-8")
    for ad, (b0, b1, d0, d1, bc0, bc1, stop, _) in Y.HARMONIK.items():
        m = re.search(r'f_klasik\("' + re.escape(ad) + r'",\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+),', metin)
        _sina(hata, m is not None, f"⑤ Pine'da f_klasik(\"{ad}\") çağrısı yok")
        if m:
            deg = [float(x) for x in m.groups()]
            bekl = [b0, b1, bc0, bc1, Y.IDEAL_D[ad], stop]
            _sina(hata, all(abs(a - b) < 1e-9 for a, b in zip(deg, bekl)), f"⑤ {ad}: Pine {deg} ≠ HARMONIK {bekl}")
    # ⑥ olasılık bloğu
    if JSON.exists():
        h6 = pine_sabit.denetle()
        _sina(hata, not h6, "⑥ " + "; ".join(h6))
    else:
        hata.append("⑥ yapi_backtest.json yok")
    # ⑦ pine_denetle
    r = subprocess.run([sys.executable, str(DEPO / "site" / "tools" / "pine_denetle.py")], capture_output=True, text=True)
    _sina(hata, r.returncode == 0, "⑦ pine_denetle düştü: " + (r.stdout + r.stderr)[-400:])
    # ⑧ emir mekaniği (sentetik)
    z = [1_700_000_000 + 60 * i for i in range(12)]
    yukari = Seri([10, 10, 10.2, 10.5, 10.9, 11.4, 12, 12, 12, 12, 12, 12], [10.1, 10.1, 10.4, 10.8, 11.2, 11.8, 12.5, 12.1, 12.1, 12.1, 12.1, 12.1],
                  [9.9, 9.95, 10.1, 10.4, 10.8, 11.3, 11.9, 11.9, 11.9, 11.9, 11.9, 11.9], [10, 10.2, 10.5, 10.9, 11.4, 12, 12, 12, 12, 12, 12, 12], z)
    r1 = B.islem(yukari, 0, +1, 10.0, 9.5, 11.0, False, 50)       # piyasa: giriş 10 (bar1 açılış), hedef 11 → +2R
    _sina(hata, r1 and abs(r1["R"] - 2.0) < 1e-9 and not r1["belirsiz"], f"⑧ hedef: {r1}")
    r2 = B.islem(yukari, 0, -1, 10.0, 10.5, 9.0, False, 50)       # satış: stop 10,5 bar3'te vurur → −1
    _sina(hata, r2 and abs(r2["R"] + 1.0) < 1e-9, f"⑧ stop: {r2}")
    genis = Seri([10, 10], [10.1, 12], [9.9, 9.0], [10, 10.5], z[:2])
    r3 = B.islem(genis, 0, +1, 10.0, 9.5, 11.0, False, 50)        # aynı barda ikisi → stop + belirsiz
    _sina(hata, r3 and r3["R"] < 0 and r3["belirsiz"], f"⑧ aynı bar: {r3}")
    r4 = B.islem(yukari, 0, +1, 9.0, 8.5, 10.0, True, 50)         # limit 9,0'a gelmez → None
    _sina(hata, r4 is None, f"⑧ dolmayan limit: {r4}")
    duz = Seri([10] * 12, [10.05] * 12, [9.95] * 12, [10] * 12, z)
    r5 = B.islem(duz, 0, +1, 10.0, 9.5, 11.0, False, 5)           # ufuk dolar, R sınırlı
    _sina(hata, r5 and r5.get("zaman") and -1 < r5["R"] < 2, f"⑧ ufuk: {r5}")
    bosluk = Seri([10, 9.0, 9.0, 9.0], [10.1, 9.3, 9.6, 12.0], [9.9, 8.9, 8.9, 8.9], [10, 9.2, 9.5, 11.5], z[:4])
    r6 = B.islem(bosluk, 0, +1, 9.5, 8.5, 10.5, True, 50)         # limit 9,5 ama bar1 9,0'da açıldı: doluş 9,0; plan riski 1,0; hedef 10,5 → (10,5−9,0)/1,0 = 1,5R
    _sina(hata, r6 and abs(r6["R"] - 1.5) < 1e-9, f"⑧ boşlukla doluş: {r6}")
    r7 = B.islem(bosluk, 0, +1, 9.5, 9.0, 10.5, True, 50)         # boşluk stopun altında/üstünde açıldıysa emir yok
    _sina(hata, r7 is None, f"⑧ stop altında doluş: {r7}")
    # ⑨ koşan uca karşı BOS yok: yükseliş kolu boyunca olay sayısı
    sy2 = Y.Yapi(sentetik([100, 104, 102, 108, 105, 112, 109, 116, 113, 120]), {"k_swing": 2})
    bos = [o for o in sy2.olaylar if o.tur == "BOS"]
    _sina(hata, all(o.seviye in [w.fiyat for w in sy2.swingler] for o in bos), f"⑨ BOS onaylı olmayan seviyeye karşı: {[(o.bar, o.seviye) for o in bos]}")
    # ⑩ JSON künyesi
    if JSON.exists():
        d = json.loads(JSON.read_text(encoding="utf-8"))
        _sina(hata, d["kunye"].get("kural_kaynagi", "").endswith("yapi_referans.py") and "spread_varsayimi" in d["kunye"], "⑩ künye eksik")
        for tf in B.ZAMAN_DILIMLERI:
            pk = {p["paket"] for p in d["paket_toplam"] if p["tf"] == tf}
            _sina(hata, set(B.PAKETLER) <= pk, f"⑩ {tf}: paket satırları eksik {set(B.PAKETLER) - pk}")
    return hata


if __name__ == "__main__":
    h = kos()
    if h:
        print("DUMAN DÜŞTÜ:")
        for x in h:
            print(" ·", x)
        sys.exit(1)
    print("duman: on madde geçti")
