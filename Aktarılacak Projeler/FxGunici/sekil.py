#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FX GÜN İÇİ STRATEJİLER — figürler. Sayıların tamamı `cikti/ders/olcum.json`dan gelir.

Strateji başına altı figür (birim adıyla):
  <birim>-ornek.html   örnek günler: örneklem dışından sabit çekilişle üç işlem — kazanan, kaybeden, tuzak (ana parite)
  <birim>-egri.html    birikimli R, dört parite ve havuzu; altta havuzun tepeden düşüşü
  <birim>-izgara.html  parametre ısı haritası (zaman dilimi × ikinci eksen), örneklem içi ve dışı
  <birim>-kosul.html   koşul kovaları: örneklem içinde seçilen, örneklem dışında sınanan
  <birim>-saat.html    giriş saatine (TSİ) göre işlem başına R
  <birim>-tf.html      zaman dilimi kıyası (5 / 15 / 60 dk): varsayılanın yalnız mum uzunluğu değişir
Ortak figürler: karsilastirma-*.html, haber-*.html, veri-*.html, yontem-*.html.

Biçim seçimi (görev tanımı 10: "hızlı yüklenen bir grafik biçimi seç ve gerekçelendir"):
Plotly HTML, sayfaya `loading="lazy"` iframe olarak gömülür (GrafikEmbed). Kütüphane tek
dosyadır (/js/plotly-4.0.0.min.js) ve bütün figürler onu paylaşır: ilk figürden sonra tarayıcı
önbelleğinden gelir; her figür dosyası yalnız kendi verisini taşır (eğriler haftalık, ızgara
kesiti tek düzlem). Okur ekranın dışındaki figürü indirmez. İnteraktivite (fareyle N, aralık,
tarih okuma) bir backtest figüründe süs değil, sayının kaynağını gösterme yoludur.

Çizilen her figüre sitenin ev stili (site/tools/plotly_stil.py) aynı koşuda uygulanır: figürlerin yüksekliği o
stilin üst payıyla kurulur (sekil_ortak.ust_pay) ve stilsiz bir figürde başlık çizim alanına biner. Kapı
(dogrula.py) her gömülen figürde stilin işaretini arar.

  python3 sekil.py [birim …] [--olcum YOL] [--cikti DİZİN]
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import adlar
import sekil_ortak as so
from sekil_ortak import CLARET, GRI, MAVI, MUREKKEP, TURUNCU, YESIL, baslik_koy, go, make_subplots, vir, yukseklik

#: Paritenin rengi KİMLİĞİNE bağlıdır, sırasına değil: bir parite çıkarılsa da öbürlerinin rengi değişmez. Tabloda
#: olmayan bir parite yedek renkleri künyedeki sırasıyla alır.
RENK_SABIT = {"EURUSD": MAVI, "GBPUSD": CLARET, "USDJPY": TURUNCU, "AUDUSD": YESIL}
YEDEK_RENK = ("#6b4f8a", "#4f7f8a", "#8a6b4f")
#: Parite sözlükleri ölçümün künyesinden kurulur (`parite_kur`; ders_motor.parite_kur'un eşi): parite listesi,
#: nokta büyüklüğü ve ana parite (künyenin ilki) tek yerde, ölçüm dosyasında durur.
PARITE: dict[str, str] = {}
NOKTA: dict[str, float] = {}
RENK: dict[str, str] = {}
ANA = ""
OOS_GOLGE = "rgba(138,138,138,0.13)"
SINYAL_BANT = "rgba(47,93,140,0.16)"
ORNEK_AD = {"kazanan": "Kazanan", "kaybeden": "Kaybeden", "tuzak": "Tuzak"}
#: Stop'suz kuralların R birimi (strateji.py: fiksingte kuralın kendi mumlarının ATR'si, momentumda 60 dakikalık).
R_BIRIMI = {"fiks": "girişteki ATR(14), kuralın kendi mumlarından", "momentum": "girişteki 60 dakikalık ATR(14)"}


def parite_kur(kunye: dict) -> None:
    """Parite sözlüklerini künyeden kurar. Künyede nokta büyüklüğü olmayan parite çizimi DÜŞÜRÜR: tahmin edilen bir
    nokta büyüklüğü fiyat eksenini on kat kaydırır ve figür yine çizilir."""
    global ANA
    ciftler = list(kunye.get("ciftler") or [])
    if not ciftler:
        raise SystemExit("künyede parite listesi yok")
    PARITE.clear(), NOKTA.clear(), RENK.clear()
    yedek = iter(YEDEK_RENK)
    for c in ciftler:
        if c not in (kunye.get("nokta") or {}):
            raise SystemExit(f"künyede nokta büyüklüğü yok: {c}")
        PARITE[c] = f"{c[:3]}/{c[3:]}" if len(c) == 6 and c.isalpha() else c
        NOKTA[c] = float(kunye["nokta"][c])
        RENK[c] = RENK_SABIT.get(c) or next(yedek, GRI)
    ANA = ciftler[0]


def _hane(cift: str) -> int:
    """Fiyatın ondalık hanesi, nokta büyüklüğünden (1e-5 → 5, 1e-3 → 3)."""
    return max(0, round(-math.log10(NOKTA[cift])))


def _tsi(t) -> list[str]:
    return [x.strftime("%Y-%m-%d %H:%M:%S") for x in
            pd.to_datetime(np.asarray(t, dtype=np.int64), unit="s", utc=True).tz_convert("Europe/Istanbul")]


def _saat(t) -> str:
    return pd.Timestamp(int(t), unit="s", tz="UTC").tz_convert("Europe/Istanbul").strftime("%H:%M")


def _r(x, b=2, arti=True) -> str:
    if x is None:
        return "—"
    s = vir(x, b)
    return ("+" + s) if (arti and x > 0) else s


def _ic(o: dict) -> str:
    k = o["kunye"]
    return f"{k['baslangic'][:4]}–{k['ic_bitis'][:4]}"


def _dis(o: dict) -> str:
    return f"{o['kunye']['dis_baslangic'][:4]} →"


def _kunye(o: dict) -> str:
    k = o["kunye"]
    return (f"Dukascopy 1 dk bid/ask · {so.tarih(k['baslangic'])}–{so.tarih(k['bitis'])} · net: gerçek makas + "
            f"{vir(k['temel_kayma_pip'], 1)} pip kayma (haber penceresinde +{vir(k['haber_kayma_pip'], 0)} pip)")


# ─────────────────────────────────────────────────────── 1 · örnek günler
def _ornek_pencere(x: dict) -> np.ndarray:
    """Panelin mumları: sinyal mumundan (ya da olaydan) önceki birkaç saat ve çıkıştan sonraki bir saat. Bütün FX
    günü (17:00 ET → 17:00 ET) 5 dakikalık mumda 288 mumdur ve telefonda mum başına bir pikselin altına iner."""
    m, i = x["mum"], x["islem"]
    sn = 60 * int(x["tf"])
    t = np.asarray(m["t"], dtype=np.int64)
    anlar = [int(i["giris_t"])]
    if i.get("sinyal_t"):
        anlar.append(int(i["sinyal_t"]) - sn)
    if i.get("olay_t"):
        anlar.append(int(i["olay_t"]))
    once = (3 if sn <= 300 else 6) * 3600
    return (t + sn > min(anlar) - once) & (t < int(i["cikis_t"]) + 3600)


def ornek(o: dict, birim: str) -> None:
    b = o["birim"][birim]
    c = ANA
    ornekler = (b["cift"].get(c) or {}).get("ornek") or []
    if not ornekler:
        print(f"  · {birim}: örnek gün yok")
        return
    stopsuz = (b.get("varsayilan") or {}).get("stop_turu") == "yok"
    ad = adlar.BIRIM[birim][0]
    n = len(ornekler)
    gun_sonu = o["kunye"]["gun_sonu_et"]
    basliklar = []
    for x in ornekler:
        i = x["islem"]
        bas = ORNEK_AD.get(x["etiket"], x["etiket"]) + (" (yedek tanım)" if x.get("secim") == "yedek" else "")
        ek_ = f" · en iyi {_r(i['mfe_r'])} R" if x["etiket"] == "tuzak" else ""
        # iki satır: tek satırda (≈ 25 em) telefonun 353 piksellik çerçevesinden taşıyordu
        # Çıkışın kısa adı ("gün sonu kapanışı" → "gün sonu"): tuzak satırı en iyi R'yi de taşır ve uzun adla
        # telefonun çerçevesini aşıyordu (sekil_ortak.panel_tasmasi; kapı aynı ölçüyü sorar).
        cikis = adlar.neden_ad(i, gun_sonu).replace("gün sonu kapanışı", "gün sonu")
        basliklar.append(f"{bas} · {so.tarih(x['gun'])} · {'alış' if i['yon'] > 0 else 'satış'}<br>"
                         f"{_r(i['r'])} R{ek_} · çıkış: {cikis}")
    fig = make_subplots(rows=n, cols=1, vertical_spacing=0.12, subplot_titles=basliklar)
    p, hane = NOKTA[c], _hane(c)
    fiyat = f"%{{y:.{hane}f}}"
    hedef_var = olay_var = False
    for k, x in enumerate(ornekler, start=1):
        m, i = x["mum"], x["islem"]
        sn = 60 * int(x["tf"])
        sec = _ornek_pencere(x)
        t = np.asarray(m["t"], dtype=np.int64)[sec]
        o_, h_, l_, c_ = (np.asarray(m[a], dtype=float)[sec] * p for a in ("o", "h", "l", "c"))
        # Mum, kendi aralığının ORTASINA çizilir: plotly mumu x'te ortalar, başlangıcına çizilen mum sinyal
        # bandından yarım mum kayık görünürdü. Fareyle okunan saat aralığın kendisidir.
        aralik = [f"{_saat(a)}–{_saat(a + sn)} TSİ" for a in t]
        fig.add_trace(go.Candlestick(x=_tsi(t + sn // 2), open=o_, high=h_, low=l_, close=c_, hovertext=aralik,
                                     hoverinfo="text+y",
                                     increasing=dict(line=dict(color="#4d4d4d", width=1), fillcolor="#ffffff"),
                                     decreasing=dict(line=dict(color="#4d4d4d", width=1), fillcolor="#9a9a9a"),
                                     name=f"{x['tf']} dk mum (orta fiyat)", showlegend=(k == 1)), k, 1)
        x0, x1 = _tsi([t[0], t[-1] + sn])
        if i.get("sinyal_t"):
            s0, s1 = _tsi([int(i["sinyal_t"]) - sn, int(i["sinyal_t"])])
            fig.add_vrect(x0=s0, x1=s1, fillcolor=SINYAL_BANT, line_width=0, layer="below", row=k, col=1)
        if i.get("olay_t"):
            olay_var = True
            fig.add_vline(x=_tsi([int(i["olay_t"])])[0], line=dict(color=MUREKKEP, width=1, dash="dash"), row=k, col=1)
        seviyeler = []
        for a in ("ust", "alt", "seviye"):
            v = i.get(a)
            if v is not None and all(abs(v - w) > 1e-9 for w in seviyeler):
                seviyeler.append(v)
        for j, v in enumerate(seviyeler):
            fig.add_trace(go.Scatter(x=[x0, x1], y=[v * p] * 2, mode="lines", line=dict(color=MAVI, width=1, dash="dot"),
                                     name="referans seviye", legendgroup="seviye", showlegend=(k == 1 and j == 0),
                                     hovertemplate="seviye " + fiyat + "<extra></extra>"), k, 1)
        g0, g1 = _tsi([i["giris_t"], i["cikis_t"]])
        if i.get("stop") is not None:
            fig.add_trace(go.Scatter(x=[g0, g1], y=[i["stop"] * p] * 2, mode="lines", line=dict(color=CLARET, width=1.6),
                                     name="stop", legendgroup="stop", showlegend=(k == 1),
                                     hovertemplate="stop " + fiyat + "<extra></extra>"), k, 1)
        if i.get("hedef") is not None:
            hedef_var = True
            fig.add_trace(go.Scatter(x=[g0, g1], y=[i["hedef"] * p] * 2, mode="lines", line=dict(color=YESIL, width=1.6),
                                     name="hedef", legendgroup="hedef", showlegend=not any(
                                         t_.name == "hedef" and t_.showlegend for t_ in fig.data),
                                     hovertemplate="hedef " + fiyat + "<extra></extra>"), k, 1)
        fig.add_trace(go.Scatter(x=[g0], y=[i["giris_f"] * p], mode="markers",
                                 marker=dict(symbol="triangle-up" if i["yon"] > 0 else "triangle-down", size=13,
                                             color=MUREKKEP, line=dict(color="white", width=1.5)),
                                 name="giriş (yürütülen fiyat)", legendgroup="giris", showlegend=(k == 1),
                                 hovertemplate=f"giriş {_saat(i['giris_t'])} TSİ · " + fiyat + "<extra></extra>"), k, 1)
        fig.add_trace(go.Scatter(x=[g1], y=[i["cikis_f"] * p], mode="markers",
                                 marker=dict(symbol="x", size=11, color=MUREKKEP),
                                 name="çıkış", legendgroup="cikis", showlegend=(k == 1),
                                 hovertemplate=f"çıkış {_saat(i['cikis_t'])} TSİ · " + fiyat + "<extra></extra>"), k, 1)
        fig.update_xaxes(rangeslider_visible=False, tickformat="%H:%M", range=[x0, x1], row=k, col=1)
        fig.update_yaxes(tickformat=f".{max(1, hane - 1)}f", row=k, col=1)
    # Bant ve olay çizgisi birer şekildir, lejantta görünmez: lejant girdisi boş bir izle kurulur.
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name="sinyal mumu",
                             marker=dict(symbol="square", size=13, color=SINYAL_BANT)), 1, 1)
    if olay_var:
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", name="olay anı",
                                 line=dict(color=MUREKKEP, width=1, dash="dash")), 1, 1)
    isaret = "Mavi bant: sinyal mumu · noktalı mavi: referans seviye" + ("" if stopsuz else " · kırmızı: stop") + \
             (" · yeşil: hedef" if hedef_var else "") + (" · kesikli: olay anı" if olay_var else "")
    alt = [f"{PARITE[c]} · stratejinin kendi mum uzunluğu (orta fiyat), saatler TSİ · önceden kayıtlı varsayılan",
           f"Örneklem dışından ({_dis(o)}) sabit çekilişle, ayrı günlerde: kazanan, kaybeden ve tuzak (lehine en az "
           "0,5 R gidip zararla kapanan)", isaret]
    if stopsuz:
        alt.append(f"Stop'suz kural: stop çizgisi yok; R birimi {R_BIRIMI.get(b.get('aile'), 'girişteki ATR')}")
    bas = baslik_koy(fig, f"Örnek günler — {ad}", alt)
    fig.update_layout(legend=dict(orientation="h", y=-0.06))
    so._yaz(fig, f"{birim}-ornek.html", yukseklik(bas, 290 * n + 110))


# ─────────────────────────────────────────────────────── 2 · birikimli R ve düşüş
def _soluk(renk: str, opak: float = 0.38) -> str:
    """#rrggbb → rgba(…, opak): örneklem içi aynı rengin soluğudur, kimlik rengi değişmez."""
    r, g, b_ = (int(renk[j:j + 2], 16) for j in (1, 3, 5))
    return f"rgba({r},{g},{b_},{opak})"


def _iki_donem(fig, gun: list[str], y: list[float], dis: str, ad: str, renk: str, kalin: float, satir: int = 1,
               hover: str = "") -> None:
    """Bir birikimli seriyi iki iz olarak çizer: örneklem içi soluk, örneklem dışı koyu. Dış iz, iç izin son
    noktasından başlar (iki parça arasında boşluk kalmaz); lejantta tek girdi, ikisi birlikte açılıp kapanır."""
    k = next((j for j, g in enumerate(gun) if g >= dis), len(gun))
    ic, dis_ = slice(0, k), slice(max(0, k - 1), len(gun))
    if k > 0:
        fig.add_trace(go.Scatter(x=gun[ic], y=y[ic], mode="lines", name=ad, legendgroup=ad, showlegend=k >= len(gun),
                                 line=dict(color=_soluk(renk), width=kalin), hovertemplate=hover), satir, 1)
    if k < len(gun):
        fig.add_trace(go.Scatter(x=gun[dis_], y=y[dis_], mode="lines", name=ad, legendgroup=ad, showlegend=True,
                                 line=dict(color=renk, width=kalin), hovertemplate=hover), satir, 1)


def egri(o: dict, birim: str) -> None:
    b = o["birim"][birim]
    k = o["kunye"]
    dis = k["dis_baslangic"]
    stopsuz = (b.get("varsayilan") or {}).get("stop_turu") == "yok"
    birim_r = "R birimi girişteki ATR" if stopsuz else "her işlem 1R risk"
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.68, 0.32], vertical_spacing=0.08,
                        subplot_titles=(f"Birikimli net R ({birim_r})", "Havuzun tepeden düşüşü (R)"))
    egriler = {}
    for c in PARITE:
        e = ((b["cift"].get(c) or {}).get("egri") or {}).get("varsayilan")
        if not e:
            continue
        egriler[c] = pd.Series(e["r"], index=pd.DatetimeIndex(e["gun"]))
        _iki_donem(fig, list(e["gun"]), list(e["r"]), dis, PARITE[c], RENK[c], 1.2,
                   hover="%{x|%d.%m.%Y}: %{y:.1f} R<extra>" + PARITE[c] + "</extra>")
    if egriler:
        # havuz: aynı haftanın parite değerlerinin toplamı (her parite kendi birikimli R'si; eksik hafta
        # bir önceki değeriyle taşınır — birikimli seride işlemsiz hafta değişmez)
        h = pd.concat(egriler, axis=1).ffill().fillna(0.0).sum(axis=1)
        dd = np.maximum.accumulate(np.concatenate([[0.0], h.to_numpy()]))[1:] - h.to_numpy()
        gun = [g.strftime("%Y-%m-%d") for g in h.index]
        _iki_donem(fig, gun, [round(float(v), 2) for v in h], dis, "havuz (paritelerin toplamı)", MUREKKEP, 2.2,
                   hover="%{x|%d.%m.%Y}: %{y:.1f} R<extra>havuz</extra>")
        fig.add_trace(go.Scatter(x=gun, y=-dd, mode="lines", fill="tozeroy", line=dict(color=CLARET, width=1),
                                 fillcolor="rgba(140,47,57,0.22)", name="havuzun düşüşü", showlegend=False,
                                 hovertemplate="%{x|%d.%m.%Y}: −%{customdata:.1f} R<extra>düşüş</extra>",
                                 customdata=dd), 2, 1)
    fig.add_vrect(x0=dis, x1=k["bitis"], fillcolor=OOS_GOLGE, line_width=0, layer="below", row="all", col=1)
    fig.add_hline(y=0, line=dict(color=MUREKKEP, width=0.8), row=1, col=1)
    fig.update_xaxes(tickformat="%Y")              # sayısal biçim: eksende İngilizce ay adı çıkmaz
    bas = baslik_koy(fig, f"Birikimli sonuç — {adlar.BIRIM[birim][0]}",
                     [_kunye(o), f"Önceden kayıtlı varsayılan (veriye bakmadan seçildi) · örneklem içi ({_ic(o)}) soluk, "
                      f"örneklem dışı ({_dis(o)}) koyu ve gri alanda",
                      f"Havuz: aynı kural {len(egriler)} paritede birlikte; haftalık birikimli R"])
    so._yaz(fig, f"{birim}-egri.html", yukseklik(bas, 470))


# ─────────────────────────────────────────────────────── 3 · ızgara: ısı haritası
def _isi_iz(isi: dict, donem: str, olcu: str = "beklenti_r"):
    z, metin = [], []
    for satir in isi["hucre"]:
        zs, ms = [], []
        for h in satir:
            d = (h or {}).get(donem) or {}
            v = d.get(olcu)
            n = d.get("n") or 0
            zs.append(v if (v is not None and n >= 30) else None)
            ms.append(f"{_r(v)}<br>n {n}" if v is not None else "—")
        z.append(zs)
        metin.append(ms)
    return z, metin


def izgara(o: dict, birim: str, cift: str = "") -> None:
    cift = cift or ANA
    v = o["birim"][birim]["cift"].get(cift)
    if not v:
        return
    isi = v["isi"]
    y_ad = adlar.PARAM.get(isi["y_ad"], isi["y_ad"])
    ylab = [adlar.DEGER.get(x, x) for x in isi["y"]]
    xlab = [f"{x} dk" for x in isi["x"]]
    # İki dönem ALT ALTA: yan yana dizildiğinde telefonda iki panel başlığı birbirine biniyor, hücreler
    # 50 pikselin altına iniyordu.
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.14,
                        subplot_titles=(f"Örneklem içi ({_ic(o)})", f"Örneklem dışı ({_dis(o)})"))
    tum = [x for d in ("is", "oos") for row in _isi_iz(isi, d)[0] for x in row if x is not None]
    sinir = max(0.25, max((abs(x) for x in tum), default=0.25))
    for j, d in enumerate(("is", "oos"), start=1):
        z, metin = _isi_iz(isi, d)
        fig.add_trace(go.Heatmap(z=z, x=xlab, y=ylab, text=metin, texttemplate="%{text}", zmin=-sinir, zmax=sinir,
                                 colorscale=[[0, CLARET], [0.5, "#f2f0eb"], [1, MAVI]], showscale=(j == 2),
                                 colorbar=dict(title=dict(text="R / işlem"), thickness=10, len=0.8),
                                 hovertemplate="%{y} · %{x}<br>%{text}<extra></extra>", xgap=2, ygap=2), j, 1)
    vx, vy = isi["varsayilan"]
    for j in (1, 2):
        if vx in isi["x"] and vy in isi["y"]:
            fig.add_shape(type="rect", xref=f"x{'' if j == 1 else j}", yref=f"y{'' if j == 1 else j}",
                          x0=isi["x"].index(vx) - 0.5, x1=isi["x"].index(vx) + 0.5,
                          y0=isi["y"].index(vy) - 0.5, y1=isi["y"].index(vy) + 0.5,
                          line=dict(color=MUREKKEP, width=2))
    bas = baslik_koy(fig, f"Parametre ızgarası — {adlar.BIRIM[birim][0]}",
                     [f"{PARITE[cift]} · işlem başına net ortalama R · satırlar: {y_ad} · sütunlar: zaman dilimi",
                      "Öbür parametreler önceden kayıtlı varsayılanda; çerçeveli hücre varsayılanın kendisi",
                      "Renk yalnız en az 30 işlemli hücrede; boş hücre ölçülemedi"])
    so._yaz(fig, f"{birim}-izgara.html", yukseklik(bas, 150 + 2 * 46 * max(2, len(ylab))))


# ─────────────────────────────────────────────────────── 4 · koşul kovaları
KOSUL_HUKUM = {"tuttu": "tuttu", "tutmadi": "tutmadı", "secilmedi": "kova seçilmedi"}
def _kova_sirala(kovalar: list[dict]) -> list[dict]:
    """Kovaların okuma sırası metinle aynı (adlar.KOVA_OKUMA)."""
    ko = adlar.KOVA_OKUMA
    return sorted(kovalar, key=lambda kv: ko.index(kv["kova"]) if kv["kova"] in ko else 50)


def _kova_hover(donem: str, r, n, isabet) -> str:
    if r is None or n is None:
        return ""
    s = f"{donem} {_r(r)} R · {so.vir(n, 0)} işlem"
    return s + (f" · kazanan payı {so.yuzde(100 * isabet, 1)}" if isabet is not None else "")


def kosul(o: dict, birim: str, cift: str = "") -> None:
    cift = cift or ANA
    v = (o["birim"][birim]["cift"].get(cift) or {}).get("varsayilan")
    if not v or not v.get("kosul"):
        return
    # Satırlar gruplanır: değişkenin adı kendi satırında (çizim alanının içinde, kalın), altında kovaları; eksende
    # kova ve değişkenin hükmü durur. Aynı ölçüyü ikinci adla tekrarlayan ("esdeger") ve bütün kovaları seçen
    # ("hepsi") değişken sınanamadığı için çizilmez; altyazı onları adıyla sayar.
    anahtar, yazi, is_r, oos_r, is_h, oos_h, sec, gruplar, atlanan = [], [], [], [], [], [], [], [], []
    for gi, k in enumerate(v["kosul"]):
        ad = adlar.KOSUL.get(k["degisken"], k["degisken"])
        if k["hukum"] not in KOSUL_HUKUM:
            atlanan.append(ad)
            continue
        bas = len(anahtar)
        anahtar.append(f"g{gi}"), yazi.append(f"<i>{KOSUL_HUKUM[k['hukum']]}</i>")
        is_r.append(None), oos_r.append(None), is_h.append(""), oos_h.append(""), sec.append(False)
        for kv in _kova_sirala(k["kovalar"]):
            secildi = kv["kova"] in (k.get("secilen") or [])
            anahtar.append(f"g{gi}·{kv['kova']}"), yazi.append(f"<b>{kv['kova']}</b>" if secildi else kv["kova"])
            is_r.append(kv["is_r"]), oos_r.append(kv["oos_r"]), sec.append(secildi)
            is_h.append(f"{ad} · {kv['kova']}<br>" + _kova_hover("örneklem içi", kv["is_r"], kv["is_n"], kv.get("is_isabet")))
            oos_h.append(f"{ad} · {kv['kova']}<br>" + _kova_hover("örneklem dışı", kv["oos_r"], kv["oos_n"],
                                                                     kv.get("oos_isabet")))
        gruplar.append((bas, len(anahtar) - 1, ad, k.get("ic_kosulsuz_r")))
    if not gruplar:
        return
    fig = make_subplots(rows=1, cols=1, subplot_titles=("Net R / işlem, kova kova",))
    fig.add_trace(go.Bar(x=is_r, y=anahtar, orientation="h", name="örneklem içi (kovayı seçen)", marker_color="#c4c4c4",
                         hovertext=is_h, hoverinfo="text"))
    fig.add_trace(go.Bar(x=oos_r, y=anahtar, orientation="h", name="örneklem dışı (seçimi sınayan)",
                         marker_color=[MAVI if s_ else MUREKKEP for s_ in sec], hovertext=oos_h, hoverinfo="text"))
    fig.add_trace(go.Bar(x=[None], y=[anahtar[0]], orientation="h", name="örneklem dışı · seçilen kova (kalın ad)",
                         marker_color=MAVI, hoverinfo="skip"))
    for bas_, son_, ad, taban in gruplar:      # değişkenin adı ve koşulsuz ortalaması kendi grubunda
        fig.add_annotation(x=0, xref="paper", xanchor="left", y=anahtar[bas_], yref="y", text=f"<b>{ad}</b>",
                           showarrow=False, font=dict(size=11, color=MUREKKEP), bgcolor="rgba(255,255,255,0.85)")
        if taban is not None and son_ > bas_:
            fig.add_shape(type="line", x0=taban, x1=taban, y0=bas_ + 0.5, y1=son_ + 0.5, xref="x", yref="y",
                          line=dict(color=GRI, width=1.2, dash="dash"))
    fig.add_vline(x=0, line=dict(color=MUREKKEP, width=0.8))
    fig.update_yaxes(type="category", categoryorder="array", categoryarray=anahtar, tickvals=anahtar, ticktext=yazi,
                     autorange="reversed", tickfont=dict(size=11))
    fig.update_layout(barmode="group", bargap=0.25, bargroupgap=0.05)
    alt = [f"{PARITE[cift]} · önceden kayıtlı varsayılan · işlem başına net R, kova kova (fareyle işlem sayısı ve "
           "kazanan payı)",
           "Kova sınırları örneklem içinden; seçilen kova örneklem içinde koşulsuz ortalamadan (kesikli) iyi ve en az "
           "30 işlemli",
           "Hüküm değişkenin satırında: tuttu = seçilen kovalar örneklem dışında artı ve öbür kovalardan iyi"]
    if atlanan:
        alt.append("Sınanamadığı için çizilmeyen: " + ", ".join(atlanan) + " (aynı ölçü ya da bütün kovalar seçildi)")
    bas = baslik_koy(fig, f"Koşul kovaları — {adlar.BIRIM[birim][0]}", alt)
    so._yaz(fig, f"{birim}-kosul.html", yukseklik(bas, 110 + 22 * len(anahtar)))


# ─────────────────────────────────────────────────────── 5 · giriş saati (TSİ)
def saat(o: dict, birim: str) -> None:
    b = o["birim"][birim]
    fig = make_subplots(rows=1, cols=1, subplot_titles=("İşlem başına net R, giriş saatine (TSİ) göre",))
    for c in PARITE:
        s = (((b["cift"].get(c) or {}).get("varsayilan")) or {}).get("saat_tsi") or {}
        if not s:
            continue
        saatler = sorted(int(h) for h in s)
        fig.add_trace(go.Bar(x=[f"{h:02d}:00" for h in saatler], y=[s[str(h)].get("beklenti_r") for h in saatler],
                             name=PARITE[c], marker_color=RENK[c],
                             customdata=[s[str(h)].get("n") for h in saatler],
                             hovertemplate="%{x} TSİ: %{y:.2f} R · n %{customdata}<extra>" + PARITE[c] + "</extra>"))
    fig.add_hline(y=0, line=dict(color=MUREKKEP, width=0.8))
    fig.update_layout(barmode="group", bargap=0.25)
    bas = baslik_koy(fig, f"Giriş saatine göre — {adlar.BIRIM[birim][0]}",
                     ["İşlem başına net ortalama R, girişin TSİ saatine göre (bütün dönem) · önceden kayıtlı varsayılan",
                      "TSİ = UTC + 3 (Türkiye 2016'dan beri yaz saati uygulamıyor); seans saatleri Avrupa ve ABD "
                      "saat değişimiyle bir saat kayar"])
    so._yaz(fig, f"{birim}-saat.html", yukseklik(bas, 400))


# ─────────────────────────────────────────────────────── 6 · zaman dilimi kıyası (5 / 15 / 60 dk)
TF_RENK = {"5": "#9bb6d3", "15": MAVI, "60": MUREKKEP}


def tf(o: dict, birim: str) -> None:
    b = o["birim"][birim]
    ciftler = [c for c in PARITE if (b["cift"].get(c) or {}).get("tf")]
    if not ciftler:
        return
    dilimler = sorted({t for c in ciftler for t in b["cift"][c]["tf"]}, key=int)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.14,
                        subplot_titles=(f"Örneklem içi ({_ic(o)})", f"Örneklem dışı ({_dis(o)})"))
    for j, d in enumerate(("is", "oos"), start=1):
        for t in dilimler:
            hucre = [(b["cift"][c]["tf"].get(t) or {}).get(d) or {} for c in ciftler]
            fig.add_trace(go.Bar(x=[PARITE[c] for c in ciftler], y=[h.get("beklenti_r") for h in hucre],
                                 name=f"{t} dk mum", marker_color=TF_RENK.get(t, GRI), showlegend=(j == 1),
                                 legendgroup=t, customdata=[[h.get("n"), h.get("sharpe")] for h in hucre],
                                 hovertemplate="%{x} · " + t + " dk: %{y:.3f} R · n %{customdata[0]} · Sharpe "
                                               "%{customdata[1]:.2f}<extra></extra>"), j, 1)
        fig.add_hline(y=0, line=dict(color=MUREKKEP, width=0.8), row=j, col=1)
        fig.update_yaxes(title_text="net R / işlem", row=j, col=1)
    fig.update_layout(barmode="group", bargap=0.3)
    v = b["varsayilan"]
    oteki = [adlar.param_yaz(k, x) for k, x in v.items() if k != "tf"]
    bas = baslik_koy(fig, f"Zaman dilimi kıyası — {adlar.BIRIM[birim][0]}",
                     [f"Önceden kayıtlı varsayılan; yalnız mum uzunluğu değişir ({', '.join(oteki)})",
                      "İşlem başına net ortalama R · her parite ayrı · varsayılanın kendi dilimi "
                      f"{v.get('tf')} dk"])
    so._yaz(fig, f"{birim}-tf.html", yukseklik(bas, 520))


BIRIM_SEKILLERI = (ornek, egri, izgara, kosul, saat, tf)


# ─────────────────────────────────────────────────────── ortak: karşılaştırma
def karsilastirma(o: dict) -> None:
    satir = []
    for b, v in o["birim"].items():
        h = ((v.get("havuz") or {}).get("varsayilan") or {}).get("oos") or {}
        if h.get("n"):
            satir.append((b, h.get("beklenti_r"), h.get("ga_alt"), h.get("ga_ust"), h.get("n")))
    if not satir:
        return
    satir.sort(key=lambda x: x[1] if x[1] is not None else -9)
    fig = make_subplots(rows=1, cols=1, subplot_titles=("Örneklem dışı · net R ve %95 aralığı",))
    fig.add_trace(go.Scatter(
        x=[s[1] for s in satir], y=[adlar.BIRIM[s[0]][1] for s in satir], mode="markers",
        marker=dict(size=9, color=[MAVI if (s[2] or -1) > 0 else (MUREKKEP if (s[1] or 0) > 0 else CLARET) for s in satir]),
        error_x=dict(type="data", symmetric=False, array=[(s[3] - s[1]) if s[3] is not None else 0 for s in satir],
                     arrayminus=[(s[1] - s[2]) if s[2] is not None else 0 for s in satir], color=GRI, thickness=1.2),
        customdata=[[s[4], s[2], s[3]] for s in satir],
        hovertemplate="%{y}: %{x:.3f} R · %95 [%{customdata[1]:.3f}, %{customdata[2]:.3f}] · n %{customdata[0]}"
                      "<extra></extra>", showlegend=False), 1, 1)
    fig.add_vline(x=0, line=dict(color=MUREKKEP, width=0.9))
    bas = baslik_koy(fig, "Örneklem dışında işlem başına net R — bütün stratejiler",
                     [_kunye(o), "Önceden kayıtlı varsayılanlar; dört paritenin işlemleri birlikte (havuz), "
                      f"{so.tarih(o['kunye']['dis_baslangic'])} → {so.tarih(o['kunye']['bitis'])} · çizgi: %95 "
                      "bootstrap aralığı",
                      "Mavi: aralığın alt ucu sıfırın üstünde · siyah: ortalama artı, aralık sıfırı kapsıyor · kırmızı: "
                      "ortalama eksi"])
    so._yaz(fig, "karsilastirma-ozet.html", yukseklik(bas, 90 + 26 * len(satir)))
    kor = o.get("korelasyon") or {}
    if kor.get("tum"):
        # Sıra derslerin sırası (aile aile): aynı bahsi oynayan stratejiler blok olarak görünür. Yalnız alt
        # üçgen çizilir (matris simetrik) ve hücreye yalnız |ρ| ≥ 0,25 yazılır: 22 × 22 matriste her hücreye
        # sayı yazmak telefonda hücreleri okunmaz bir yazı yığınına çeviriyordu; değerin tamamı fareyle okunur.
        sira = [b for bl in adlar.DERS_BIRIM.values() for b in bl if b in kor["birimler"]]
        sira += [b for b in kor["birimler"] if b not in sira]
        ix = [kor["birimler"].index(b) for b in sira]
        ad = [adlar.BIRIM[b][1] for b in sira]
        z = [[kor["tum"][i][j] if c <= r else None for c, j in enumerate(ix)] for r, i in enumerate(ix)]
        metin = [[(vir(v, 2) if (v is not None and abs(v) >= 0.25 and r != c) else "") for c, v in enumerate(satir)]
                 for r, satir in enumerate(z)]
        fig = make_subplots(rows=1, cols=1, subplot_titles=("Günlük R korelasyonu (bütün dönem)",))
        fig.add_trace(go.Heatmap(z=z, x=ad, y=ad, zmin=-1, zmax=1, text=metin, texttemplate="%{text}",
                                 colorscale=[[0, CLARET], [0.5, "#f2f0eb"], [1, MAVI]], textfont=dict(size=9),
                                 colorbar=dict(thickness=10, len=0.6, y=0.7),
                                 hovertemplate="%{y} × %{x}: %{z:.2f}<extra></extra>", xgap=1, ygap=1), 1, 1)
        fig.update_yaxes(autorange="reversed", showgrid=False)
        fig.update_xaxes(tickangle=-50)
        bas = baslik_koy(fig, "Stratejiler arası günlük R korelasyonu",
                         ["Önceden kayıtlı varsayılanlar, dört paritenin günlük R toplamı · bütün dönem · işlemsiz gün 0",
                          "Sıra derslerin sırası (seans, yapı, fade, haber, akış) · hücrede yalnız |ρ| ≥ 0,25",
                          "Sıfıra yakın: iki strateji farklı günlerde ya da farklı yönlerde para kazanıp kaybediyor"])
        so._yaz(fig, "karsilastirma-korelasyon.html", yukseklik(bas, 760))


# ─────────────────────────────────────────────────────── ortak: maliyet merdiveni ve rastgele yön
def maliyet(o: dict, cift: str = "") -> None:
    """Maliyet merdiveni: aynı kural, artan yürütme maliyetiyle. Sütunlar dersin tablosuyla (ders_motor.blok_maliyet_ozet)
    aynıdır: brüt, yalnız makas (kayma ve haber kayması sıfır) ve dört kayma kademesi (haber kayması her kademede)."""
    cift = cift or ANA
    kademe = [str(float(x)) for x in o["kunye"].get("kayma_pip") or []]
    hk = vir(float(o["kunye"]["haber_kayma_pip"]), 1)
    satir = []
    for b, v in o["birim"].items():
        va = (v["cift"].get(cift) or {}).get("varsayilan") or {}
        m = va.get("maliyet") or {}
        if not m:
            continue
        satir.append((b, va.get("oos", {}).get("brut_r"),
                      ((va.get("yalniz_makas") or {}).get("oos") or {}).get("beklenti_r"),
                      *[m.get(k, {}).get("oos", {}).get("beklenti_r") for k in kademe]))
    if not satir or len(kademe) != 4:
        return
    temel = 3 + kademe.index(str(float(o["kunye"]["temel_kayma_pip"])))
    satir.sort(key=lambda x: x[temel] if x[temel] is not None else -9)
    ad = [adlar.BIRIM[x[0]][1] for x in satir]
    fig = make_subplots(rows=1, cols=1, subplot_titles=(f"{PARITE[cift]} · örneklem dışı, R / işlem",))
    seri = [("brüt (orta fiyattan orta fiyata)", GRI, "circle-open"),
            ("yalnız makas (kayma ve haber kayması 0)", YESIL, "circle")]
    renk = {0: (MAVI, "circle-open"), 1: (MUREKKEP, "diamond"), 2: (TURUNCU, "circle"), 3: (CLARET, "circle")}
    for q, kk in enumerate(kademe):
        temel_mi = 3 + q == temel
        seri.append((f"net, kayma {vir(float(kk), 1)} pip" + (" (temel senaryo)" if temel_mi else ""), *renk[q]))
    for j, (etiket, rk, sembol) in enumerate(seri):
        fig.add_trace(go.Scatter(x=[x[1 + j] for x in satir], y=ad, mode="markers", name=etiket,
                                 marker=dict(symbol=sembol, size=10 if 1 + j == temel else 8, color=rk,
                                             line=dict(width=1.4) if sembol.endswith("open") else None),
                                 hovertemplate="%{y}: %{x:.3f} R<extra>" + etiket + "</extra>"), 1, 1)
    fig.add_vline(x=0, line=dict(color=MUREKKEP, width=0.9))
    bas = baslik_koy(fig, "Maliyet merdiveni — aynı kural, artan yürütme maliyeti",
                     ["Önceden kayıtlı varsayılanlar · kayma her dolumda (giriş, piyasa çıkışı ve stop) ödenir; "
                      f"kayma kademelerinde haber penceresindeki dolumlar ayrıca {hk} pip öder",
                      "Brüt ile yalnız makas arasındaki fark gerçek bid/ask makasıdır · R: yürütülen girişten stop'a "
                      "planlanan risk, stop'suz kurallarda girişteki ATR(14)"])
    so._yaz(fig, "karsilastirma-maliyet.html", yukseklik(bas, 150 + 26 * len(satir)))


def rastgele(o: dict, cift: str = "") -> None:
    cift = cift or ANA
    satir = []
    for b, v in o["birim"].items():
        va = (v["cift"].get(cift) or {}).get("varsayilan") or {}
        r = (va.get("rastgele") or {}).get("oos") or {}
        if r.get("n"):
            satir.append((b, va["oos"].get("beklenti_r"), r.get("p05"), r.get("p95"), r.get("ort"), r.get("yuzdelik")))
    if not satir:
        return
    satir.sort(key=lambda x: (x[5] or 0))
    ad = [adlar.BIRIM[x[0]][1] for x in satir]
    # Eksen aralığı bantların uçlarından kurulur: kendiliğinden aralık yalnız işaretlere bakar ve
    # kalın çizgiyle çizilen bandı kenarda kırpar (bandın ucu okura hiç görünmez).
    uclar = [v for x in satir for v in x[1:5] if v is not None]
    pay = 0.06 * (max(uclar) - min(uclar))
    fig = make_subplots(rows=1, cols=1, subplot_titles=(f"{PARITE[cift]} · örneklem dışı, net R / işlem",))
    fig.update_xaxes(range=[min(uclar) - pay, max(uclar) + pay])
    for x, y in zip(satir, ad):
        fig.add_trace(go.Scatter(x=[x[2], x[3]], y=[y, y], mode="lines", line=dict(color="rgba(47,93,140,0.35)", width=9),
                                 showlegend=False, hoverinfo="skip"), 1, 1)
    fig.add_trace(go.Scatter(x=[x[4] for x in satir], y=ad, mode="markers", name="rastgele yönün ortalaması",
                             marker=dict(symbol="line-ns-open", size=12, color=MAVI, line=dict(width=2)),
                             hovertemplate="%{y}: rastgele ortalama %{x:.3f} R<extra></extra>"), 1, 1)
    fig.add_trace(go.Scatter(x=[x[1] for x in satir], y=ad, mode="markers", name="stratejinin kendisi",
                             marker=dict(symbol="diamond", size=10, color=MUREKKEP),
                             customdata=[x[5] for x in satir],
                             hovertemplate="%{y}: %{x:.3f} R · rastgele dağılımda %{customdata:.0f}. yüzdelik"
                                           "<extra></extra>"), 1, 1)
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", name="rastgele yönün %5–95 bandı (1000 tekrar)",
                             line=dict(color="rgba(47,93,140,0.35)", width=9)), 1, 1)
    bas = baslik_koy(fig, "Yön seçmenin değeri — strateji ile aynı işlemlerin rastgele yönlüsü",
                     ["Aynı giriş dakikası, aynı risk uzaklığı, aynı çıkış kuralı; yalnız yön yazı turayla",
                      "Stratejinin elması bandın sağındaysa kenar zamanlamada değil yön seçimindedir",
                      "Sıra: rastgele dağılımdaki yüzdelik"])
    so._yaz(fig, "yontem-rastgele.html", yukseklik(bas, 120 + 26 * len(satir)))


# ─────────────────────────────────────────────────────── ortak: veri kalitesi
def veri(o: dict) -> None:
    k = ((o.get("veri") or {}).get("kalite") or {})
    if not k:
        return
    # İki panel ALT ALTA: yan yana dizildiğinde telefonda (353 px) iki panel başlığı üst üste biniyordu.
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.16,
                        subplot_titles=("Saat saat medyan makas (New York saati)", "17:00 ET devri çevresinde, dakika dakika"))
    for c, v in k.items():
        m = v.get("makas") or {}
        sh = m.get("saatlik_ny") or {}
        saatler = sorted(int(h) for h in sh)
        fig.add_trace(go.Scatter(x=saatler, y=[sh[str(h)]["medyan"] for h in saatler], mode="lines+markers",
                                 name=PARITE.get(c, c), line=dict(color=RENK.get(c, GRI), width=1.6), marker=dict(size=4),
                                 customdata=[sh[str(h)]["p95"] for h in saatler],
                                 hovertemplate="NY %{x}:00 · medyan %{y:.1f} pip · p95 %{customdata:.1f}<extra>"
                                               + PARITE.get(c, c) + "</extra>"), 1, 1)
        dv = m.get("devir_profili_medyan_pip") or {}
        dk = sorted(int(x) for x in dv)
        fig.add_trace(go.Scatter(x=dk, y=[dv[str(x)] for x in dk], mode="lines+markers", showlegend=False,
                                 line=dict(color=RENK.get(c, GRI), width=1.6), marker=dict(size=4),
                                 hovertemplate="17:00 ET %{x:+d} dk · %{y:.1f} pip<extra>" + PARITE.get(c, c) + "</extra>"),
                      2, 1)
    fig.add_vline(x=-5, line=dict(color=CLARET, width=1, dash="dash"), row=2, col=1)
    fig.update_xaxes(dtick=3, title_text="New York saati", row=1, col=1)
    fig.update_xaxes(dtick=10, title_text="17:00 ET'den dakika", row=2, col=1)
    fig.update_yaxes(title_text="pip", row=1, col=1)
    fig.update_yaxes(title_text="pip", row=2, col=1)
    bas = baslik_koy(fig, "Makas: gün içinde ve devir dakikalarında",
                     [f"Dukascopy 1 dk bid/ask, {so.tarih(o['kunye']['baslangic'])}–{so.tarih(o['kunye']['bitis'])} · "
                      "dakika kapanışlarında ask − bid",
                      "TSİ = New York + 7 saat (ABD yaz saati) ya da + 8 saat (ABD kış saati)",
                      "Kırmızı kesikli: pozisyonların kapandığı 16:55 ET"])
    so._yaz(fig, "veri-makas.html", yukseklik(bas, 700))


# ─────────────────────────────────────────────────────── ortak: haber
def haber_patika(o: dict) -> None:
    hc = (o.get("haber") or {}).get("cift") or {}
    olaylar = sorted({e for h in hc.values() for e in (h.get("patika") or {})})
    for olay in olaylar:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1,
                            subplot_titles=("İlk 5 dakika yukarı kapanan olaylar", "İlk 5 dakika aşağı kapanan olaylar"))
        for c, h in hc.items():
            pt = (h.get("patika") or {}).get(olay)
            if not pt:
                continue
            for j, yon in enumerate(("yukari", "asagi"), start=1):
                d = pt.get(yon)
                if not d:
                    continue
                tau = pt["tau"]
                fig.add_trace(go.Scatter(x=tau + tau[::-1], y=[100 * x for x in d["ust"]] + [100 * x for x in d["alt"][::-1]],
                                         fill="toself", fillcolor=RENK.get(c, GRI) + "22",
                                         line=dict(width=0), hoverinfo="skip", showlegend=False), j, 1)
                fig.add_trace(go.Scatter(x=tau, y=[100 * x for x in d["ort"]], mode="lines",
                                         name=f"{PARITE.get(c, c)} (n {d['n']})" if j == 1 else None,
                                         showlegend=(j == 1), legendgroup=c, line=dict(color=RENK.get(c, GRI), width=1.6),
                                         hovertemplate="%{x:+d} dk: %{y:.1f}% ATR<extra>" + f"{PARITE.get(c, c)} · n {d['n']}"
                                                       + "</extra>"), j, 1)
        if not fig.data:
            continue
        for j in (1, 2):
            fig.add_vline(x=0, line=dict(color=MUREKKEP, width=0.9), row=j, col=1)
            fig.add_vline(x=5, line=dict(color=GRI, width=0.9, dash="dot"), row=j, col=1)
            fig.add_hline(y=0, line=dict(color=GRI, width=0.8), row=j, col=1)
            fig.update_yaxes(title_text="% günlük ATR", row=j, col=1)
        fig.update_xaxes(title_text="olaydan dakika", row=2, col=1)
        bas = baslik_koy(fig, f"Ortalama fiyat patikası — {adlar.OLAY.get(olay, olay)}",
                         ["Olay anındaki orta fiyattan değişim, önceki 14 günün ATR'sine bölünmüş · ilk 5 dakikanın "
                          "yönüne göre iki küme",
                          "Gölge: ortalamanın %95 aralığı · noktalı çizgi: ilk 5 dakikanın sonu",
                          "Saatler resmî metinden, tarih tarih; fiyat sınaması hiçbir olayı dışarıda bırakmaz"])
        so._yaz(fig, f"haber-patika-{olay.lower().replace('_', '-')}.html", yukseklik(bas, 600))


def haber_fomc(o: dict) -> None:
    hc = (o.get("haber") or {}).get("cift") or {}
    fig = make_subplots(rows=1, cols=1, subplot_titles=("Her nokta bir FOMC toplantısı",))
    for c, h in hc.items():
        f = (h.get("fomc") or {})
        st = f.get("satir") or []
        if not st:
            continue
        fig.add_trace(go.Scatter(x=[100 * r["karar_atr"] for r in st], y=[100 * r["basin_60_atr"] for r in st],
                                 mode="markers", name=PARITE.get(c, c), marker=dict(size=7, color=RENK.get(c, GRI), opacity=0.8),
                                 customdata=[so.tarih(r["tarih"]) for r in st],
                                 hovertemplate="%{customdata}: karar %{x:.1f}% · basın %{y:.1f}% ATR<extra>"
                                               + PARITE.get(c, c) + "</extra>"), 1, 1)
    if not fig.data:          # ölçülmemiş figür yazılmaz: boş eksenler "veri yok" demez, "sonuç yok" der
        return
    fig.add_hline(y=0, line=dict(color=GRI, width=0.8))
    fig.add_vline(x=0, line=dict(color=GRI, width=0.8))
    fig.update_xaxes(title_text="karar: 14:00 → 14:30 ET (% günlük ATR)")
    fig.update_yaxes(title_text="basın toplantısı: 14:30 → 15:30 ET")
    bas = baslik_koy(fig, "FOMC: kararın ilk yarım saati ve basın toplantısının ilk saati",
                     ["Sol üst ve sağ alt çeyrek: basın toplantısı karara verilen tepkiyi TERSİNE çevirdi",
                      "Değişimler orta fiyattan, önceki 14 günün ATR'sine bölünmüş",
                      "14:00 ET = TSİ 21:00 (ABD yaz saati) ya da 22:00 (ABD kış saati)"])
    so._yaz(fig, "haber-fomc.html", yukseklik(bas, 470))


def main(argv: list[str]) -> int:
    if go is None:
        print("plotly yok: figürler çizilemez (kapı yolu bundan etkilenmez)")
        return 1
    if "--olcum" in argv:
        i = argv.index("--olcum")
        so.OLCUM = Path(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    if "--cikti" in argv:
        i = argv.index("--cikti")
        so.CIKTI = Path(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    o = json.loads(so.OLCUM.read_text(encoding="utf-8"))
    parite_kur(o["kunye"])
    birimler = [b for b in argv if b in o["birim"]] or list(o["birim"])
    for b in birimler:
        for f in BIRIM_SEKILLERI:
            f(o, b)
    if not argv:
        for f in (karsilastirma, maliyet, rastgele, veri, haber_patika, haber_fomc):
            f(o)
    return so.ev_stili(so.YAZILAN)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
