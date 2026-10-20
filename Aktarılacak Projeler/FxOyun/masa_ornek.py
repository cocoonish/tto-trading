#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FX GÜN İÇİ — masa katmanının GERÇEK mum örnekleri (yalnız 2018–2023).

Her örnek bir durumun iki gerçekleşmesidir: TİPİK (dersin ölçtüğü eğilimle aynı yönde biten) ve TERS GİDEN.
İkisi yan yana durur, çünkü tek bir olay ne bir kuralı doğrular ne yanlışlar; okur, kuralın tuttuğu günle
tutmadığı günün grafikte birbirine ne kadar benzediğini görmelidir.

Seçim kuralı mekaniktir ve tektir: koşula ve sonuca uyan olaylardan `SON` tarihinden önceki EN SON olay.
Kimse "güzel bir grafik" seçmez; koşul `metin/masa/<slug>.toml`daki `[[ornek]]` kaydında yazılıdır.
Bir olay (parite + olay mumunun saati) serinin tamamında BİR kez gösterilir: aynı iki gün iki derste ters rollerle
basılırsa okur aynı grafiği iki ayrı dersin kanıtı sanar. Öncelik derslerin sırasıdır (`SIRA`); sonraki ders bir
sonraki uyan olaya iner.
Veri 31.12.2023'te kesilerek yüklenir (`gozlem.py` ile aynı yol): 2024 sonrasının fiyatları örneklere giremez.

  python3 masa_ornek.py          # seçim (veri ister) → veri/masa_ornek.json, ardından çizim
  python3 masa_ornek.py --ciz    # yalnız çizim (dosyadan)

Grafikteki numaralar sabittir ve bütün derslerde aynı anlamı taşır: ① olay mumu (büyük mum ya da anın ilk mumu),
② mumun yarısı, ③ fiyatın yarıya ilk dokunduğu an (yoksa işaret yok), ④ izleme penceresinin sonu.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

BURASI = Path(__file__).resolve().parent
sys.path.insert(0, str(BURASI))
import masa  # noqa: E402

VERI = BURASI / "veri"
CIKTI = VERI / "masa_ornek.json"
SON = "2023-12-01"
IC_BITIS = date(2023, 12, 31)
BASAMAK = {"EURUSD": 5, "GBPUSD": 5, "AUDUSD": 5, "USDJPY": 3}
ONCE_MUM = 20
TSI = timezone(timedelta(hours=3))
SIRA = ["fx-oyun-okuma", "fx-oyun-acilislar", "fx-oyun-fiksingler", "fx-oyun-haberler", "fx-oyun-backtest",
        "fx-buyuk-mum", "fx-buyuk-suzgec", "fx-buyuk-giris", "fx-buyuk-plan"]


def pencere(o: dict, e: dict, sf) -> tuple[int, int, int]:
    """Olay mumunun (başlangıç, bitiş, dilim) saati: kimliği budur. Bir anın ilk mumu ile bir büyük mum aynı mum
    olabilir (Londra fiksingi ile 15 dakikalık bir büyük mum), o yüzden tekillik olay türüne değil muma bakar."""
    if o["kaynak"] == "buyuk":
        return int(e["bt"]), int(e["bt"]) + int(o["tf"]) * 60, int(o["tf"])
    an = sf.AN[o["an"]]
    bas = int(e["t0"]) - (an.tf * 60 if an.aile == "fiksing" else 0)
    return bas, bas + an.tf * 60, an.tf


def uyar(olcu: dict, kosul: dict) -> bool:
    """Koşul sözlüğü: alan = değer (eşitlik), alan_min / alan_max (sınır)."""
    for k, v in kosul.items():
        if k.endswith("_min"):
            x = olcu.get(k[:-4])
            if x is None or x != x or x < v:
                return False
        elif k.endswith("_max"):
            x = olcu.get(k[:-4])
            if x is None or x != x or x > v:
                return False
        elif olcu.get(k) != v:
            return False
    return True


# ─────────────────────────────────────────────────────────────── seçim (veri ister)
def sec() -> dict:
    import numpy as np
    import pandas as pd

    import buyuk_mum as bm
    import gozlem as gz
    import sinif as sf
    import ayar as ay
    import veri as vr

    istek = [(slug, o) for slug in SIRA for o in masa.spek(slug).get("ornek", [])]
    a = dataclasses.replace(ay.oku(), bitis=IC_BITIS)
    son = int(pd.Timestamp(SON, tz="UTC").timestamp())
    cikti: dict = {}
    kullanilan: set[tuple[str, int, int]] = set()
    for cift in sorted({o["cift"] for _, o in istek}):
        d = vr.oku(cift, a)
        assert int(d.t[-1]) < int(pd.Timestamp("2024-01-01", tz="UTC").timestamp()), "2024 sonrası veri örneğe girdi"
        olay_tf, olay_an, mumlar = {}, {}, {}
        for slug, o in [(s, o) for s, o in istek if o["cift"] == cift]:
            if o["kaynak"] == "buyuk":
                tf = int(o["tf"])
                if tf not in olay_tf:
                    olay_tf[tf], _ = bm.olaylar(d, tf, cift)
                ev = olay_tf[tf]
                cizim_tf = tf
            else:
                an = sf.AN[o["an"]]
                if an.kimlik not in olay_an:
                    olay_an[an.kimlik] = sf.olaylar(d, an, cift)
                ev = olay_an[an.kimlik]
                cizim_tf = 5
            if cizim_tf not in mumlar:
                mumlar[cizim_tf] = vr.mumla(d, cizim_tf)
            M = mumlar[cizim_tf]
            secilen = {}
            for e in reversed(ev.to_dict("records")):
                t = e["bt"] if o["kaynak"] == "buyuk" else e["t0"]
                if t >= son or e["yon"] == 0 or (cift, *pencere(o, e, sf)[:2]) in kullanilan or not uyar(e, o.get("kosul", {})):
                    continue
                if o["kaynak"] == "buyuk":
                    olcu, _ = bm.olc(d, e)
                else:
                    olcu = gz.sonuc(d, e)
                for rol in ("tipik", "ters"):
                    if rol not in secilen and uyar(olcu, o[rol]):
                        secilen[rol] = (e, olcu)
                if len(secilen) == 2:
                    break
            if len(secilen) < 2:
                raise SystemExit(f"{slug} {o['id']}: koşula uyan {'/'.join(r for r in ('tipik', 'ters') if r not in secilen)} olayı yok")
            kayit = {}
            for rol, (e, olcu) in secilen.items():
                bas, mum_son, tf = pencere(o, e, sf)
                kullanilan.add((cift, bas, mum_son))
                izle_son = int(d.t[e["j1"] - 1]) + 60
                i = int(np.searchsorted(M.bt, bas))
                j = int(np.searchsorted(M.bt, izle_son))
                pen = range(max(0, i - ONCE_MUM), min(len(M.bt), j))
                orta = (e["h"] + e["l"]) / 2
                hi, lo = d.mh[e["j0"]:e["j1"]], d.ml[e["j0"]:e["j1"]]
                dok = (lo <= orta) if e["yon"] > 0 else (hi >= orta)
                ilk = int(d.t[e["j0"] + int(np.argmax(dok))]) if dok.any() else None
                kayit[rol] = {
                    "gun": str(e["gun"]), "bas": bas, "mum_son": mum_son, "izle_son": izle_son, "tf": tf,
                    "cizim_tf": cizim_tf, "yon": int(e["yon"]), "o": float(e["o"]), "h": float(e["h"]),
                    "l": float(e["l"]), "c": float(e["c"]), "orta_ilk": ilk,
                    "son_fiyat": float(d.mc[e["j1"] - 1]),
                    "olcu": {k: (bool(v) if isinstance(v, (bool, np.bool_)) else (float(v) if v is not None else None))
                             for k, v in olcu.items() if not isinstance(v, str)},
                    "olay": {k: e[k] for k in ("kapanis", "seans", "haber", "trend", "kova", "kat", "sinif", "uyum")
                             if k in e},
                    "mumlar": [[int(M.bt[k]), float(M.o[k]), float(M.h[k]), float(M.l[k]), float(M.c[k])] for k in pen],
                }
            cikti.setdefault(slug, {})[o["id"]] = {"cift": cift, "basamak": BASAMAK[cift], **kayit}
            print(f"  {slug} {o['id']}: tipik {kayit['tipik']['gun']} · ters {kayit['ters']['gun']}", flush=True)
        del d
    return cikti


# ─────────────────────────────────────────────────────────────── çizim
def ciz() -> None:
    import sekil_ortak as so
    from sekil_ortak import CLARET, GRI, MAVI, MUREKKEP, go, make_subplots

    D = json.loads(CIKTI.read_text(encoding="utf-8"))
    kaynak = "Dukascopy 1 dakikalık alış-satış fiyatlarının ortası · 2018–2023"
    for slug in SIRA:
        for o in masa.spek(slug).get("ornek", []):
            x = D[slug][o["id"]]
            olc = 10 ** x["basamak"]
            fig = make_subplots(rows=2, cols=1, vertical_spacing=0.16,
                                subplot_titles=[f"{o['tipik_ad']} · {so.tarih(x['tipik']['gun'])}",
                                                f"{o['ters_ad']} · {so.tarih(x['ters']['gun'])}"])
            for r, rol in enumerate(("tipik", "ters"), start=1):
                e = x[rol]
                m = e["mumlar"]
                bt = [k[0] for k in m]
                sira = lambda t: max(i for i, b in enumerate(bt) if b <= t)
                fig.add_trace(go.Candlestick(x=list(range(len(m))), open=[k[1] / olc for k in m],
                                             high=[k[2] / olc for k in m], low=[k[3] / olc for k in m],
                                             close=[k[4] / olc for k in m],
                                             increasing=dict(line=dict(color=MAVI, width=1), fillcolor=MAVI),
                                             decreasing=dict(line=dict(color=CLARET, width=1), fillcolor=CLARET),
                                             showlegend=False, hoverinfo="skip"), row=r, col=1)
                i0, i1 = sira(e["bas"]), sira(e["mum_son"] - 60)
                fig.add_vrect(x0=i0 - 0.5, x1=i1 + 0.5, fillcolor="rgba(33,27,18,0.08)", line_width=0, row=r, col=1)
                orta = (e["h"] + e["l"]) / 2 / olc
                fig.add_hline(y=orta, line=dict(color=MUREKKEP, width=1, dash="dash"), row=r, col=1)
                for yy in (e["h"] / olc, e["l"] / olc):
                    fig.add_hline(y=yy, line=dict(color=GRI, width=1), row=r, col=1)
                isaret = [(i0, (e["h"] if e["yon"] > 0 else e["l"]) / olc, "①", 14 if e["yon"] > 0 else -14),
                          (min(len(m) - 1, i1 + 2), orta, "②", 11 if e["yon"] < 0 else -11)]
                if e["orta_ilk"]:
                    isaret.append((sira(e["orta_ilk"]), orta, "③", -11 if e["yon"] < 0 else 11))
                isaret.append((len(m) - 1, e["son_fiyat"] / olc, "④", -14))
                for xx, yy, n, kay in isaret:
                    fig.add_annotation(x=xx, y=yy, text=n, showarrow=False, yshift=kay,
                                       font=dict(size=15, color=MUREKKEP), bgcolor="rgba(255,255,255,0.85)",
                                       row=r, col=1)
                adim = max(1, len(m) // 5)
                tv = list(range(0, len(m), adim))
                fig.update_xaxes(tickvals=tv, ticktext=[datetime.fromtimestamp(bt[k], TSI).strftime("%H:%M") for k in tv],
                                 range=[-0.8, len(m) - 0.2], rangeslider_visible=False, row=r, col=1)
                fig.update_yaxes(tickformat=f".{x['basamak'] - 1}f", nticks=4, row=r, col=1)
            cift = f"{x['cift'][:3]}/{x['cift'][3:]}"
            tf = x["tipik"]["cizim_tf"]
            alt = [f"{cift}, {tf} dakikalık mumlar, saatler TSİ. ① olay mumu (gölgeli), ② mumun yarısı (kesikli), "
                   f"③ fiyatın yarıya ilk dokunduğu mum, ④ izleme penceresinin sonu; düz çizgiler mumun iki ucu. "
                   f"Örnek kuralla seçildi: koşula uyan son olay.",
                   kaynak]
            baslik = so.baslik_koy(fig, o["baslik"], alt)
            so._yaz(fig, slug, f"m_{o['id']}.html", so.yukseklik(baslik, 2 * 270 + 70), ust=so.ust_pay(baslik),
                    olcum=CIKTI)


def ornek_blok(slug: str, kimlik: str, no: str) -> str:
    o = masa._bul(slug, "ornek", kimlik)
    return (f'<GrafikEmbed src="/arastirma/{slug}/m_{kimlik}.html" baslik="{masa._e(o["baslik"])}" no="{no}" '
            f'kaynak="Dukascopy" />\n')


def oz() -> str:
    return hashlib.sha256(CIKTI.read_bytes()).hexdigest()


def main() -> int:
    if "--ciz" not in sys.argv:
        D = sec()
        CIKTI.write_text(json.dumps(D, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        print(f"✓ {CIKTI.relative_to(BURASI)}")
    ciz()
    return 0


if __name__ == "__main__":
    sys.exit(main())
