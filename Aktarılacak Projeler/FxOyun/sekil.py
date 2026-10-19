#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FX GÜN İÇİ OYUN PLANI — beş dersin figürleri.

GİRDİ TEK YERDEN: `veri/ders.json` (ders_olcum.py). Figürler `site/public/arastirma/<slug>/NN_ad.html` dosyasına
yazılır; dosya adının öneki = dersteki gömmenin numarası = figürün başlığındaki "Şekil NN" (dogrula.py sorar).
Çift y eksenli grafik yok. Saatler TSİ.

  python3 sekil.py
"""
from __future__ import annotations

import json
import sys
import tomllib
from datetime import datetime, timedelta, timezone
from pathlib import Path

BURASI = Path(__file__).resolve().parent
sys.path.insert(0, str(BURASI))
sys.dont_write_bytecode = True

import sekil_ortak as so  # noqa: E402
from sekil_ortak import go, make_subplots, vir  # noqa: E402

D = json.loads(so.OLCUM.read_text(encoding="utf-8"))
EN_AZ = tomllib.loads((BURASI / "onkayit_oyun.toml").read_text(encoding="utf-8"))["hukum"]["en_az_islem"]
CLARET, MAVI, GRI, TURUNCU, YESIL, MUREKKEP = so.CLARET, so.MAVI, so.GRI, so.TURUNCU, so.YESIL, so.MUREKKEP
TSI = timezone(timedelta(hours=3))
SINIF_AD = {"guclu": "güçlü", "normal": "normal", "reddedilen": "reddedilen", "kucuk": "küçük"}
SINIF_RENK = {"guclu": CLARET, "normal": MAVI, "reddedilen": TURUNCU}
AILE_AD = {"acilis": "Açılış", "fiksing": "Fiksing", "veri": "ABD verisi", "mb": "Merkez bankası"}
AILE_RENK = {"acilis": MAVI, "fiksing": TURUNCU, "veri": GRI, "mb": CLARET}
DONEM = {"ic": "2018–2023", "dis": "2024 →"}
AN = {a["an"]: a for a in D["an"]}
KAYNAK = "Dukascopy 1 dakikalık alış-satış fiyatları · " + ", ".join(f"{c[:3]}/{c[3:]}" for c in D["kunye"]["ciftler"])
#: Ders → figürler (ders_yaz.SEKIL ile aynı; kapı ikisini kıyaslar).
SEKILLER = {
    "fx-oyun-okuma": ["01_siniflar", "02_yarisi"],
    "fx-oyun-acilislar": ["01_patika", "02_devam_donus"],
    "fx-oyun-fiksingler": ["01_patika", "02_ay_sonu"],
    "fx-oyun-haberler": ["01_patika", "02_bacaklar"],
    "fx-oyun-backtest": ["01_kazanma_net", "02_maliyet", "03_egri"],
}


def pay(x: float) -> str:
    return so.yuzde(x * 100, 0)


def rr(x: float) -> str:
    return ("+" if round(x, 2) > 0 else "") + vir(0.0 if round(x, 2) == 0 else x, 2)


def tarih(iso: str) -> str:
    return so.tarih(iso)


def _bitir(fig, slug: str, ad: str, bas: str, alt: list[str], cizim: int) -> None:
    baslik = so.baslik_koy(fig, bas, alt)
    alan = cizim - 78                                   # çizim alanı: alt pay (78 px) düşülür
    so._yaz(fig, slug, f"{ad}.html", so.yukseklik(baslik, cizim), ust=so.ust_pay(baslik),
            lejant_y=-min(0.16, 70 / max(alan, 1)))      # lejant ekseninin 70 piksel altında


def bacaklar(rol: str | None = None) -> list[dict]:
    return [b for b in D["bacak"] if rol is None or b["rol"] == rol]


def bacak_etiket(b: dict) -> str:
    return f"{AILE_AD[b['aile']]} · {SINIF_AD[b['sinif']]}"


# ─────────────────────────────────────────────────────────────── okuma 01: dört sınıf
def okuma_01():
    sira = ["guclu", "reddedilen", "normal", "kucuk"]
    O = D["ornek"]
    fig = make_subplots(rows=4, cols=1, vertical_spacing=0.075,
                        subplot_titles=[f"{SINIF_AD[s].capitalize()} · {tarih(O[s]['gun'])} · TSİ {O[s]['tsi']}"
                                        for s in sira])
    for k, s in enumerate(sira):
        o = O[s]
        r = k + 1
        olc = 10 ** o["basamak"]
        zt = [datetime.fromtimestamp(m[0], TSI).strftime("%H:%M") for m in o["mumlar"]]
        fig.add_trace(go.Candlestick(x=zt, open=[m[1] / olc for m in o["mumlar"]], high=[m[2] / olc for m in o["mumlar"]],
                                     low=[m[3] / olc for m in o["mumlar"]], close=[m[4] / olc for m in o["mumlar"]],
                                     increasing=dict(line=dict(color=MAVI, width=1), fillcolor=MAVI),
                                     decreasing=dict(line=dict(color=CLARET, width=1), fillcolor=CLARET),
                                     showlegend=False, hoverinfo="skip"), row=r, col=1)
        ilk = o["ilk"]
        x0 = datetime.fromtimestamp(o["t0"], TSI).strftime("%H:%M")
        x1 = datetime.fromtimestamp(o["t0"] + (o["tf"] - 5) * 60, TSI).strftime("%H:%M")
        orta = (ilk["h"] + ilk["l"]) / 2 / olc
        fig.add_vrect(x0=x0, x1=x1, fillcolor="rgba(26,26,26,0.08)", line_width=0, row=r, col=1)
        for y, dash, renk in ((ilk["h"] / olc, "solid", GRI), (ilk["l"] / olc, "solid", GRI), (orta, "dash", MUREKKEP)):
            fig.add_hline(y=y, line=dict(color=renk, width=1, dash=dash), row=r, col=1)
        fig.update_xaxes(type="category", nticks=6, tickangle=0, rangeslider_visible=False, row=r, col=1)
        fig.update_yaxes(tickformat=".4f", nticks=4, row=r, col=1)
    _bitir(fig, "fx-oyun-okuma", "01_siniflar",
           "Şekil 01 — İlk mumun dört sınıfı: aynı açılış, dört gün",
           ["EUR/USD, Londra açılışı; 5 dakikalık mumlar, saatler TSİ. Gri alan ilk mum, kesikli çizgi mumun yarısı, "
            "düz çizgiler mumun iki ucu.", KAYNAK], 4 * 240 + 60)


# ─────────────────────────────────────────────────────────────── okuma 02: yarısı / devam / dönüş
def okuma_02():
    Y = D["ayna"]["aile"]
    # Merkez bankası satırları dışarıda: birkaç düzine olayla fark ±50 puana çıkar ve öbür ailelerin birkaç puanlık
    # farkını eksene ezer; o aile haber dersinde kendi tablosuyla verilir.
    kat = [(a, s) for a in ("acilis", "fiksing", "veri") for s in ("guclu", "normal", "reddedilen")]
    etiket = [f"{AILE_AD[a]} · {SINIF_AD[s]}" for a, s in kat][::-1]
    olcu = [("orta", "Yarısına döndü (fiksingde: geri verdi)"), ("devam", "Devam etti"), ("donus", "Tersine döndü")]
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.07,
                        subplot_titles=[ad for _, ad in olcu])
    uc = 0
    for i, (m, _) in enumerate(olcu):
        for dn, renk, sembol in (("ic", GRI, "circle"), ("dis", CLARET, "diamond")):
            v = [Y[a][s][dn] for a, s in kat][::-1]
            x = [(r[m] - r[f"{m}_ayna"]) * 100 for r in v]
            uc = max(uc, max(abs(t) for t in x))
            fig.add_trace(go.Scatter(x=x, y=etiket, mode="markers", name=DONEM[dn], showlegend=i == 0,
                                     marker=dict(color=renk, size=9, symbol=sembol),
                                     customdata=[f"{e} · {DONEM[dn]} · gerçek {pay(r[m])}, ayna {pay(r[m + '_ayna'])}"
                                                 f" · {r['n']} olay" for e, r in zip(etiket, v)],
                                     hovertemplate="%{customdata}<extra></extra>"), row=i + 1, col=1)
        fig.add_vline(x=0, line=dict(color="#bdb8ad", width=1), row=i + 1, col=1)
    uc = 5 * (int(uc // 5) + 1)
    fig.update_xaxes(range=[-uc, uc], title_text="gerçek pay eksi aynadaki pay, puan", title_font=dict(size=11),
                     row=3, col=1)
    fig.update_yaxes(tickfont=dict(size=11))
    _bitir(fig, "fx-oyun-okuma", "02_yarisi",
           "Şekil 02 — Gerçek pay eksi şansın payı: açılışta sıfır, fiksingte geri verme",
           ["Her olayda ilk mumdan sonraki yol, ilk mumun kapanışına göre aynalanıp aynı ölçüler yeniden hesaplandı "
            "(yön rastgele olsaydı beklenen pay). Sıfırın sağı şanstan sık, solu şanstan seyrek. Gri daire "
            "2018–2023, bordo elmas 2024 →. Merkez bankası kararları olay az olduğu için haber dersinde.", KAYNAK], 1000)


# ─────────────────────────────────────────────────────────────── patika (açılış, fiksing, haber)
def _patika_panel(fig, yollar: dict, row: int, ilk: bool) -> None:
    for s in ("guclu", "normal", "reddedilen"):
        for dn, dash, en in (("ic", "solid", 2), ("dis", "dot", 2)):
            v = yollar.get(s, {}).get(dn)
            if not v:
                continue
            fig.add_trace(go.Scatter(x=v["dk"], y=v["ortalama"], mode="lines",
                                     name=f"{SINIF_AD[s]} · {DONEM[dn]}", legendgroup=f"{s}{dn}", showlegend=ilk,
                                     line=dict(color=SINIF_RENK[s], width=en, dash=dash),
                                     customdata=[f"{SINIF_AD[s]} · {DONEM[dn]} · {v['n']} olay · {d} dk: {vir(y, 2)} mum boyu"
                                                 for d, y in zip(v["dk"], v["ortalama"])],
                                     hovertemplate="%{customdata}<extra></extra>"), row=row, col=1)
    fig.add_hline(y=0, line=dict(color="#bdb8ad", width=1), row=row, col=1)


def _patika(slug: str, ad: str, gruplar: list[tuple[str, dict]], bas: str, alt: str, satir: int = 260):
    fig = make_subplots(rows=len(gruplar), cols=1, shared_xaxes=False, vertical_spacing=0.12 if len(gruplar) > 2 else 0.18,
                        subplot_titles=[g for g, _ in gruplar])
    # Ortak ve simetrik ölçek, en az ±0,5 mum boyu: hareketin büyüklüğü ilk mumun kendisiyle kıyaslanarak okunsun
    # (panel başına kendi ölçeği sıfır çevresindeki küçük dalgalanmayı büyük bir yol gibi gösterirdi).
    uc = max([0.5] + [abs(y) for _, yol in gruplar for ss in yol.values() for v in ss.values() for y in v["ortalama"]])
    uc = round(uc * 1.1 + 0.05, 1)
    for i, (_, yollar) in enumerate(gruplar):
        _patika_panel(fig, yollar, i + 1, i == 0)
        fig.update_yaxes(title_text="mum boyu", title_font=dict(size=11), range=[-uc, uc], row=i + 1, col=1)
    fig.update_xaxes(title_text="ilk mumdan sonra, dakika", title_font=dict(size=11), row=len(gruplar), col=1)
    _bitir(fig, slug, ad, bas, [alt, KAYNAK], satir * len(gruplar) + 90)


def _havuz_yol(anlar: list[str]) -> dict:
    """Aynı ailenin anlarının ortalama yolları, olay sayısıyla ağırlıklı (aynı pencere boyu şart)."""
    out: dict = {}
    for s in ("guclu", "normal", "reddedilen"):
        for dn in ("ic", "dis"):
            vs = [D["patika"][a][s][dn] for a in anlar if dn in D["patika"].get(a, {}).get(s, {})]
            if not vs:
                continue
            assert len({tuple(v["dk"]) for v in vs}) == 1, "aynı ailede pencere boyları ayrışıyor"
            n = sum(v["n"] for v in vs)
            ort = [sum(v["ortalama"][k] * v["n"] for v in vs) / n for k in range(len(vs[0]["dk"]))]
            out.setdefault(s, {})[dn] = {"n": n, "dk": vs[0]["dk"], "ortalama": ort}
    return out


def _an_baslik(a: str) -> str:
    x = AN[a]
    if x["tsi_yaz"] == x["tsi_kis"]:
        return f"{x['ad']} (TSİ {x['tsi_yaz']})"
    return f"{x['ad']} (TSİ {x['tsi_yaz']}; kış saatinde {x['tsi_kis']})"


def acilis_01():
    g = [(_an_baslik(a), D["patika"][a]) for a in ("tokyo_acilis", "londra_acilis", "ny_acilis")]
    _patika("fx-oyun-acilislar", "01_patika", g,
            "Şekil 01 — Açılıştan sonra ortalama fiyat ilk mumun yönünde yol almıyor",
            "İlk mum kapandıktan sonra ortalama fiyat, ilk mumun kapanışından ve ilk mumun yönünde, ilk mumun boyu "
            "cinsinden; yukarı = mumun yönüne devam. Düz çizgi 2018–2023, noktalı 2024 →.")


def fiksing_01():
    g = [(_an_baslik(a), D["patika"][a]) for a in ("tokyo_fiks", "wmr")]
    _patika("fx-oyun-fiksingler", "01_patika", g,
            "Şekil 01 — Fiksingden sonra koşunun küçük bir kısmı geri veriliyor, büyük dönüş yok",
            "Fiksingden sonra ortalama fiyat, fiksing anındaki fiyattan ve fiksinge giden koşunun yönünde, koşunun boyu "
            "cinsinden; aşağı = koşunun geri verilmesi. Düz çizgi 2018–2023, noktalı 2024 →.", satir=280)


def haber_01():
    g = [("ABD verisi (istihdam, TÜFE)", _havuz_yol(["nfp", "cpi"])),
         ("Merkez bankası: Fed, ECB, BoE", _havuz_yol(["fomc", "ecb", "boe"]))]
    _patika("fx-oyun-haberler", "01_patika", g,
            "Şekil 01 — Haber mumundan sonra ortalama yol iki dönemde ayrışıyor; olay sayısı az",
            "Açıklamadan sonraki ilk 5 dakikalık mum kapandıktan sonra ortalama fiyat, mumun kapanışından ve yönünde, "
            "mumun boyu cinsinden; anlar olay sayısıyla ağırlıklı. Düz çizgi 2018–2023, noktalı 2024 →.", satir=300)


# ─────────────────────────────────────────────────────────────── açılış 02: devam ve dönüş
def _cift_panel(slug, ad, kat, etiket, olcu, bas, alt, satir_px=34, ayna=None):
    fig = make_subplots(rows=1, cols=len(olcu), shared_yaxes=True, horizontal_spacing=0.06,
                        subplot_titles=[o[1] for o in olcu])
    for j, (getir, _) in enumerate(olcu):
        izler = [("ic", GRI, "circle", getir, DONEM["ic"]), ("dis", CLARET, "diamond", getir, DONEM["dis"])]
        if ayna:
            izler += [("ic", GRI, "circle-open", ayna[j], DONEM["ic"] + " ayna"),
                      ("dis", CLARET, "diamond-open", ayna[j], DONEM["dis"] + " ayna")]
        for dn, renk, sembol, f, ad_ in izler:
            x = [f(k, dn) for k in kat]
            fig.add_trace(go.Scatter(x=[v * 100 for v in x], y=etiket, mode="markers", name=ad_, showlegend=j == 0,
                                     marker=dict(color=renk, size=9, symbol=sembol, line=dict(width=1.5, color=renk)),
                                     customdata=[f"{e} · {ad_} · {pay(v)}" for e, v in zip(etiket, x)],
                                     hovertemplate="%{customdata}<extra></extra>"), row=1, col=j + 1)
        fig.update_xaxes(range=[0, 100], tickvals=[25, 50, 75], ticktext=["%25", "%50", "%75"], row=1, col=j + 1)
    fig.update_yaxes(autorange="reversed", tickfont=dict(size=11))
    _bitir(fig, slug, ad, bas, [alt, KAYNAK], satir_px * len(kat) + 170)


def acilis_02():
    kat = [(a, s) for a in ("tokyo_acilis", "londra_acilis", "ny_acilis") for s in ("guclu", "normal", "reddedilen")]
    etiket = [f"{AN[a]['ad'].removesuffix(' açılışı')} · {SINIF_AD[s]}" for a, s in kat]
    Ya = D["ayna"]["an"]
    _cift_panel("fx-oyun-acilislar", "02_devam_donus", kat, etiket,
                [(lambda k, dn: Ya[k[0]][k[1]][dn]["devam"], "Devam etti"),
                 (lambda k, dn: Ya[k[0]][k[1]][dn]["donus"], "Tersine döndü")],
                "Şekil 02 — Güçlü açılış mumu dönüşten sık devam ediyor gibi görünür; yolun aynası da aynısını veriyor",
                "Devam: fiyat öbür ucu görmeden kendi ucunu yarım mum boyu aştı. Dönüş: kendi ucunu yarım mum boyu "
                "aşmadan öbür ucu kırdı. Dolu işaret gerçek, boş işaret yolun aynası (yön rastgele olsaydı). Gri "
                "2018–2023, bordo 2024 →.",
                ayna=[lambda k, dn: Ya[k[0]][k[1]][dn]["devam_ayna"], lambda k, dn: Ya[k[0]][k[1]][dn]["donus_ayna"]])


def fiksing_02():
    F = D["fiksing_ay_sonu"]
    kat = [(a, g, s) for a in ("wmr", "tokyo_fiks") for g in ("ay_sonu", "diger") for s in ("guclu", "normal")]
    ad = {"wmr": "Londra", "tokyo_fiks": "Tokyo"}
    gad = {"ay_sonu": "ay sonu", "diger": "öbür günler"}
    etiket = [f"{ad[a]} · {gad[g]} · {SINIF_AD[s]}" for a, g, s in kat]
    _cift_panel("fx-oyun-fiksingler", "02_ay_sonu", kat, etiket,
                [(lambda k, dn: F[k[0]][dn][k[1]][k[2]]["devam"], "Devam etti"),
                 (lambda k, dn: F[k[0]][dn][k[1]][k[2]]["orta"], "Yarısını geri verdi")],
                "Şekil 02 — Ay sonunda Londra fiksingine güçlü koşu fiksingden sonra nadiren sürüyor",
                "Ay sonu: ayın son Londra iş günü. Devam: koşunun ucu yarım koşu boyu aşıldı, başlangıcı görülmeden. "
                "Gri daire 2018–2023, bordo elmas 2024 →.", satir_px=40)


# ─────────────────────────────────────────────────────────────── haber 02 ve backtest
def _r_aralik(slug, ad, liste, bas, alt):
    etiket = [bacak_etiket(b) for b in liste]
    fig = go.Figure()
    for dn, renk, sembol in (("ic", GRI, "circle"), ("dis", CLARET, "diamond")):
        x = [b[dn].get("ort_R") for b in liste]
        hata = None
        if dn == "dis":
            hata = dict(type="data", symmetric=False, color=CLARET, thickness=1.2, width=4,
                        array=[(b[dn]["ust"] - b[dn]["ort_R"]) if "ust" in b[dn] else 0 for b in liste],
                        arrayminus=[(b[dn]["ort_R"] - b[dn]["alt"]) if "alt" in b[dn] else 0 for b in liste])
        fig.add_trace(go.Scatter(x=x, y=etiket, mode="markers", name=DONEM[dn] + (" (çizgi: güven aralığı)" if dn == "dis" else ""),
                                 marker=dict(color=renk, size=10, symbol=sembol), error_x=hata,
                                 customdata=[f"{e} · {DONEM[dn]} · {b[dn]['n']} işlem · net {rr(b[dn]['ort_R'])} R"
                                             for e, b in zip(etiket, liste)],
                                 hovertemplate="%{customdata}<extra></extra>"))
    fig.add_vline(x=0, line=dict(color="#bdb8ad", width=1))
    fig.update_yaxes(autorange="reversed", tickfont=dict(size=11))
    fig.update_xaxes(title_text="işlem başına net sonuç, R", title_font=dict(size=11))
    _bitir(fig, slug, ad, bas, [alt, KAYNAK], 46 * len(liste) + 170)


def haber_02():
    liste = [b for b in bacaklar("islem")]
    _r_aralik("fx-oyun-haberler", "02_bacaklar", liste,
              "Şekil 02 — İşlem tepkileri: merkez bankasında 2024 sonrasında artı, veride eksi",
              "İşlem başına maliyet sonrası sonuç (R = riske edilen mesafe). Gri daire 2018–2023 (seçim kuralı gereği "
              "artı), bordo elmas 2024 → ve işlem düzeyinde %95 güven aralığı. Merkez bankasının güçlü ve reddedilen "
              "mumunda 2024 → işlemleri birkaç karar gününe düşer; hüküm için az.")


def backtest_01():
    fig = go.Figure()
    for aile in AILE_AD:
        for rol, sembol in (("referans", "circle"), ("islem", "diamond")):
            liste = [b for b in bacaklar(rol) if b["aile"] == aile and b["dis"]["n"]]
            if not liste:
                continue
            fig.add_trace(go.Scatter(
                x=[b["dis"]["kazanma"] * 100 for b in liste], y=[b["dis"]["ort_R"] for b in liste], mode="markers",
                name=f"{AILE_AD[aile]} · {'referans' if rol == 'referans' else 'işlem'}",
                marker=dict(color=AILE_RENK[aile], symbol=sembol, size=[max(8, min(30, b["dis"]["n"] ** 0.5 * 0.9)) for b in liste],
                            opacity=0.8, line=dict(color="white", width=1)),
                customdata=[f"{bacak_etiket(b)} ({'referans' if rol == 'referans' else 'işlem'}) · {b['dis']['n']} işlem · "
                            f"kazanma {pay(b['dis']['kazanma'])} · net {rr(b['dis']['ort_R'])} R" for b in liste],
                hovertemplate="%{customdata}<extra></extra>"))
    fig.add_hline(y=0, line=dict(color="#bdb8ad", width=1))
    fig.update_xaxes(title_text="kazanma oranı, 2024 →", tickprefix="%", title_font=dict(size=11))
    fig.update_yaxes(title_text="işlem başına net, R", title_font=dict(size=11))
    sik = [b for b in bacaklar("referans") if b["aile"] in ("acilis", "fiksing")]
    alt_k, ust_k = min(b["dis"]["kazanma"] for b in sik), max(b["dis"]["kazanma"] for b in sik)
    _bitir(fig, "fx-oyun-backtest", "01_kazanma_net",
           f"Şekil 01 — Açılış ve fiksing tepkileri işlemlerin {pay(alt_k)}–{pay(ust_k)} kadarını kazandı, "
           "hepsi eksi kaldı",
           ["Planın her tepkisi, 2024 → dönemi: yatayda kazanma oranı, dikeyde işlem başına maliyet sonrası sonuç. "
            "Daire referans, elmas işlem tepkisi; büyüklük işlem sayısı.", KAYNAK], 520)


def backtest_02():
    liste = [b for b in bacaklar() if b["dis"]["n"] >= EN_AZ]
    etiket = [f"{bacak_etiket(b)} ({'ref.' if b['rol'] == 'referans' else 'işlem'})" for b in liste]
    fig = go.Figure()
    for alan, ad, renk, sembol in (("brut_R", "maliyetten önce", GRI, "circle"), ("ort_R", "maliyetten sonra", CLARET, "diamond")):
        fig.add_trace(go.Scatter(x=[b["dis"][alan] for b in liste], y=etiket, mode="markers", name=ad,
                                 marker=dict(color=renk, size=10, symbol=sembol),
                                 customdata=[f"{e} · {ad} · {rr(b['dis'][alan])} R" for e, b in zip(etiket, liste)],
                                 hovertemplate="%{customdata}<extra></extra>"))
    for e, b in zip(etiket, liste):
        fig.add_shape(type="line", x0=b["dis"]["brut_R"], x1=b["dis"]["ort_R"], y0=e, y1=e,
                      line=dict(color="#d5d0c6", width=2), layer="below")
    fig.add_vline(x=0, line=dict(color="#bdb8ad", width=1))
    fig.update_yaxes(autorange="reversed", tickfont=dict(size=11))
    fig.update_xaxes(title_text="işlem başına sonuç, R (2024 →)", title_font=dict(size=11))
    _bitir(fig, "fx-oyun-backtest", "02_maliyet",
           "Şekil 02 — Açılışta kenar maliyetten önce de yok; fiksingteki küçük kenarı maliyet yiyor",
           [f"2024 → döneminde en az {EN_AZ} işlemi olan tepkiler (daha azında hüküm kurulmaz). Gri: aynı kurallar "
            "orta fiyatla, makas ve kayma olmadan. Bordo: alış-satış fiyatından, kayma dahil.", KAYNAK], 34 * len(liste) + 160)


def backtest_03():
    fig = go.Figure()
    renk = [CLARET, MAVI, TURUNCU, GRI, YESIL]
    for k, b in enumerate(bacaklar("islem")):
        e = D["egri"].get(b["bacak"], [])
        if not e:
            continue
        fig.add_trace(go.Scatter(x=[t for t, _ in e], y=[v for _, v in e], mode="lines+markers",
                                 name=f"{bacak_etiket(b)} ({len(e)} işlem)", line=dict(color=renk[k % 5], width=2, shape="hv"),
                                 marker=dict(size=5),
                                 customdata=[f"{bacak_etiket(b)} · {tarih(t)} · birikimli {rr(v)} R" for t, v in e],
                                 hovertemplate="%{customdata}<extra></extra>"))
    fig.add_hline(y=0, line=dict(color="#bdb8ad", width=1))
    fig.update_yaxes(title_text="birikimli net, R", title_font=dict(size=11))
    _bitir(fig, "fx-oyun-backtest", "03_egri",
           "Şekil 03 — İşlem tepkileri 2024 sonrasında: birikimli sonuç, işlem işlem",
           ["Her nokta bir işlem, giriş gününe göre: o işleme kadarki maliyet sonrası sonuçların toplamı (R).", KAYNAK], 460)


CIZ = {("fx-oyun-okuma", "01_siniflar"): okuma_01, ("fx-oyun-okuma", "02_yarisi"): okuma_02,
       ("fx-oyun-acilislar", "01_patika"): acilis_01, ("fx-oyun-acilislar", "02_devam_donus"): acilis_02,
       ("fx-oyun-fiksingler", "01_patika"): fiksing_01, ("fx-oyun-fiksingler", "02_ay_sonu"): fiksing_02,
       ("fx-oyun-haberler", "01_patika"): haber_01, ("fx-oyun-haberler", "02_bacaklar"): haber_02,
       ("fx-oyun-backtest", "01_kazanma_net"): backtest_01, ("fx-oyun-backtest", "02_maliyet"): backtest_02,
       ("fx-oyun-backtest", "03_egri"): backtest_03}


def main() -> int:
    if go is None:
        print("✗ plotly kurulu değil; çizim yolu onu ister")
        return 1
    assert set(CIZ) == {(s, a) for s, ads in SEKILLER.items() for a in ads}
    for k in sorted(CIZ):
        CIZ[k]()
    return 0


if __name__ == "__main__":
    sys.exit(main())
