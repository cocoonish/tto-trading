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
Ortak figürler: karsilastirma-*.html, haber-*.html, veri-*.html, yontem-*.html; dokuzuncu dersin (neden başarısız)
figürleri neden-*.html.

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
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

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
#: Stopsuz kuralların R birimi (strateji.py: fiksingte kuralın kendi mumlarının ATR'si, momentumda 60 dakikalık).
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


# ─────────────────────────────────────────────────────── ortak yardımcılar (saat, eşik, ek)
LONDRA_Z, NEWYORK_Z = ZoneInfo("Europe/London"), ZoneInfo("America/New_York")
_SON_SOZ = {1: "bir", 2: "iki", 3: "üç", 4: "dört", 5: "beş", 6: "altı", 7: "yedi", 8: "sekiz", 9: "dokuz", 10: "on",
            20: "yirmi", 30: "otuz", 40: "kırk", 50: "elli", 60: "altmış", 70: "yetmiş", 80: "seksen", 90: "doksan"}


def _bas_buyuk(s: str) -> str:
    """İlk harfi büyük (Türkçe i → İ)."""
    return (("İ" if s[0] == "i" else s[0].upper()) + s[1:]) if s else s


def _sayi_ad(n: int) -> str:
    """Bir ile on arası sayının okunuşu ("dört"), öbürleri rakamla: alt yazıdaki parite sayısı künyeden türer."""
    return _SON_SOZ.get(n, vir(n, 0)) if 0 < n <= 10 else vir(n, 0)


def _turetilmis_not(o: dict) -> str:
    """Birden çok kuralı birlikte çizen figürün notu: varsayılanı ön kayıtta olmayan kurallar adıyla."""
    t = [adlar.BIRIM[b][1] for b, v in o["birim"].items() if adlar.turetilmis(v)]
    return f" (türetilmiş: {', '.join(t)})" if t else ""


def _den(n: int) -> str:
    """Sayının ayrılma eki (den · dan · ten · tan), okunuşunun son sözcüğünden: 2018'den, 30'dan, 2023'ten."""
    if n % 10:
        s = _SON_SOZ[n % 10]
    elif n % 100:
        s = _SON_SOZ[n % 100]
    else:
        s = "yüz" if n % 1000 else "bin"
    kalin = [c for c in s if c in "aeıioöuü"][-1] in "aıou"
    return ("t" if s[-1] in "çfhkpsşt" else "d") + ("a" if kalin else "e") + "n"


def _yerel_sn(gun: str, saat: str, bolge: ZoneInfo) -> int:
    y, a, g = (int(v) for v in gun[:10].split("-"))
    hh, mm = (int(v) for v in saat.split(":"))
    return int(datetime(y, a, g, hh, mm, tzinfo=bolge).timestamp())


def _kova_esik(o: dict) -> int:
    """Bir kovanın (ızgara hücresi, giriş saati, koşul kovası) okunduğu asgari işlem sayısı: ön kaydın kova eşiği
    ([kosul] asgari_kova_islem, künyede). Ders metni aynı eşiği okur; figürde ayrı bir sabit yoktur."""
    return int(o["kunye"]["kosul"]["asgari_kova_islem"])


def _saat_param_notu(param: dict) -> str:
    """Saat değerli parametrelerin TSİ karşılığı (adlar.tsi_yaz): "son giriş (Londra) 11:00 = TSİ yazın 13:00, kışın
    14:00". Parametre yoksa boş."""
    parca = []
    for k, degerler in param.items():
        if k not in adlar.SAAT_SEHIR:
            continue
        for x in (degerler if isinstance(degerler, (list, tuple)) else [degerler]):
            parca.append(f"{adlar.PARAM.get(k, k)} {x} = {adlar.tsi_yaz([f'{adlar.SAAT_SEHIR[k]} {x}'])}")
    return ("Saatler kuralın yerel saati: " + " · ".join(parca)) if parca else ""


# ─────────────────────────────────────────────────────── 1 · örnek günler
def _ornek_pencere(x: dict, r0: int | None = None) -> np.ndarray:
    """Panelin mumları: sinyal mumundan (ya da olaydan) önceki birkaç saat ve çıkıştan sonraki bir saat. Bütün FX
    günü (17:00 ET → 17:00 ET) 5 dakikalık mumda 288 mumdur ve telefonda mum başına bir pikselin altına iner.
    Referansı gece boyunca kurulan kurallarda (Asya aralığı; r0 verilir) panel en geç referansın başında açılır:
    aralığın tepesini ve dibini kuran mumlar panelde görünmeli."""
    m, i = x["mum"], x["islem"]
    sn = 60 * int(x["tf"])
    t = np.asarray(m["t"], dtype=np.int64)
    anlar = [int(i["giris_t"])]
    if i.get("sinyal_t"):
        anlar.append(int(i["sinyal_t"]) - sn)
    if i.get("olay_t"):
        anlar.append(int(i["olay_t"]))
    once = (3 if sn <= 300 else 6) * 3600
    bas = min(anlar) - once
    if r0 is not None:
        bas = min(bas, int(r0))
    return (t + sn > bas) & (t < int(i["cikis_t"]) + 3600)


def _referans_bas(b: dict, x: dict) -> int | None:
    """Gün içinde oluşan referans seviyenin başladığı an (epoch sn): seviye o andan önce yoktur ve çizgisi oradan
    başlar. Açılış ve Asya aralığı kendi penceresinin başından, NY ilk dengesi başlangıcından, haber öncesi aralık
    olaydan `on_mum` mum önceden, haberin ilk mumuna bağlı seviye olay anından, VWAP ve bandı (sinyal anındaki
    değer), fiksing ve momentum ölçüm mumu sinyal mumundan, iç mum referans mumundan, sıkışma kutusu kutunun
    içinde kalan son kesintisiz mumlardan. Önceki günden bilinen seviyeler (PDH/PDL, pivot) ve çözülemeyen hâl için
    None: seviye pencerenin tamamında çizilir."""
    aile, v = b.get("aile"), b.get("varsayilan") or {}
    i, m, gun = x["islem"], x["mum"], x["gun"]
    sn = 60 * int(x["tf"])
    sinyal_bas = int(i["sinyal_t"]) - sn if i.get("sinyal_t") else None
    seviye = v.get("seviye") if aile == "sahte" else None
    if aile == "orb" or seviye == "orb":
        return _yerel_sn(gun, "08:00", LONDRA_Z)
    if aile == "asya" or seviye == "asya":
        return _yerel_sn(gun, "00:00", LONDRA_Z)
    if aile == "nyib" and v.get("baslangic_et"):
        return _yerel_sn(gun, v["baslangic_et"], NEWYORK_Z)
    if aile in ("n1", "n2", "n5") and i.get("olay_t"):
        return int(i["olay_t"])
    if aile in ("n3", "n4") and i.get("olay_t") and v.get("on_mum"):
        return int(i["olay_t"]) - int(v["on_mum"]) * sn
    if aile in ("vwap_donus", "vwap_cekilme", "fiks", "momentum"):
        return sinyal_bas
    if sinyal_bas is None or i.get("ust") is None or i.get("alt") is None:
        return None
    t = np.asarray(m["t"], dtype=np.int64)
    h, l = np.asarray(m["h"], dtype=float), np.asarray(m["l"], dtype=float)
    if aile == "icmum":
        j = [k for k in range(len(t)) if t[k] < sinyal_bas and h[k] == i["ust"] and l[k] == i["alt"]]
        return int(t[j[-1]]) if j else None
    if aile == "sikisma":
        k, bas = int(np.searchsorted(t, sinyal_bas)) - 1, None
        while k >= 0 and h[k] <= i["ust"] and l[k] >= i["alt"]:
            bas, k = int(t[k]), k - 1
        return bas
    return None


def _gece_referansi(b: dict) -> bool:
    """Referansı gece boyunca kurulan kural: Asya aralığı ve onun başarısız kırılımı (_referans_bas'ın Asya dalı)."""
    v = b.get("varsayilan") or {}
    return b.get("aile") == "asya" or (b.get("aile") == "sahte" and v.get("seviye") == "asya")


#: Sıkışma mumlarının gölgesi: sinyal mumunun mavi bandından ayrı, kuralın göstergesi (turuncu) tonunda.
SIKISMA_BANT = "rgba(184,134,11,0.12)"


def _cizgi_ekle(fig, x: dict, sec: np.ndarray, t: np.ndarray, sn: int, p: float, k: int, var: dict, kk,
                fiyat: str) -> None:
    """Örnek günün panelinde kuralın KENDİ göstergesi (kosu._ornek_cizgi, tanımı strateji modülünde): sıkışmada
    Bollinger ve Keltner bantları ve sıkışma mumları, VWAP kurallarında gün içi VWAP, dönüşte ± k·σ bandı. Gösterge
    mumların aynı sırasında gelir; boyu tutmazsa çizim düşer (yanlış mumla hizalanmış bir bant çizilmez)."""
    cz = x.get("cizgi") or {}
    tur = cz.get("tur")
    if not tur:
        return
    tx = _tsi(t + sn // 2)

    def seri(ad):
        v = cz.get(ad)
        if v is None:
            return None
        if len(v) != len(sec):
            raise SystemExit(f"örnek gün çizgisi mumlarla aynı boyda değil: {tur} {ad} ({len(v)} ≠ {len(sec)})")
        a = np.asarray([np.nan if w is None else float(w) for w in v], dtype=float)[sec] * p
        return [None if not math.isfinite(w) else float(w) for w in a]

    if tur == "sikisma":
        for ad_, renk, dash, ad, grup in (("bb_ust", TURUNCU, "solid", "Bollinger bandı", "bb"),
                                          ("bb_alt", TURUNCU, "solid", "Bollinger bandı", "bb"),
                                          ("kc_ust", "#5e5e5e", "dash", "Keltner kanalı", "kc"),
                                          ("kc_alt", "#5e5e5e", "dash", "Keltner kanalı", "kc")):
            fig.add_trace(go.Scatter(x=tx, y=seri(ad_), mode="lines", line=dict(color=renk, width=1, dash=dash),
                                     name=ad, legendgroup=grup, showlegend=not var[grup], hoverinfo="skip"), k, 1)
            var[grup] = True
        sq = list(cz.get("sikisma") or [])
        if len(sq) != len(sec):
            raise SystemExit(f"örnek gün sıkışma mumları mumlarla aynı boyda değil ({len(sq)} ≠ {len(sec)})")
        sq = [bool(w) for w, s_ in zip(sq, sec) if s_]
        j = 0
        while j < len(sq):
            if not sq[j]:
                j += 1
                continue
            e = j
            while e + 1 < len(sq) and sq[e + 1]:
                e += 1
            a0, a1 = _tsi([int(t[j]), int(t[e]) + sn])
            fig.add_vrect(x0=a0, x1=a1, fillcolor=SIKISMA_BANT, line_width=0, layer="below", row=k, col=1)
            var["sikisma"] = True
            j = e + 1
    elif tur in ("vwap_donus", "vwap_cekilme"):
        fig.add_trace(go.Scatter(x=tx, y=seri("vwap"), mode="lines", line=dict(color=TURUNCU, width=1.3),
                                 name="VWAP (gün içinde yürür)", legendgroup="vwap", showlegend=not var["vwap"],
                                 hovertemplate="VWAP " + fiyat + "<extra></extra>"), k, 1)
        var["vwap"] = True
        if tur == "vwap_donus":
            for ad_ in ("bant_ust", "bant_alt"):
                fig.add_trace(go.Scatter(x=tx, y=seri(ad_), mode="lines", line=dict(color=TURUNCU, width=1, dash="dot"),
                                         name=f"VWAP ± {vir(float(kk), 1)}σ bandı", legendgroup="vbant",
                                         showlegend=not var["vbant"], hoverinfo="skip"), k, 1)
                var["vbant"] = True


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
                         f"{_r(adlar.islem_r(i))} R{ek_} · çıkış: {cikis}")
    fig = make_subplots(rows=n, cols=1, vertical_spacing=0.12, subplot_titles=basliklar)
    p, hane = NOKTA[c], _hane(c)
    fiyat = f"%{{y:.{hane}f}}"
    var = {"seviye": False, "stop": False, "hedef": False, "olay": False, "takvim": False, "bb": False, "kc": False,
           "sikisma": False, "vwap": False, "vbant": False}
    yonler = set()
    for k, x in enumerate(ornekler, start=1):
        m, i = x["mum"], x["islem"]
        sn = 60 * int(x["tf"])
        r0 = _referans_bas(b, x)
        sec = _ornek_pencere(x, r0 if _gece_referansi(b) else None)
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
        _cizgi_ekle(fig, x, sec, t, sn, p, k, var, (b.get("varsayilan") or {}).get("k"), fiyat)
        t0, t1 = int(t[0]), int(t[-1]) + sn
        x0, x1 = _tsi([t0, t1])
        xr, yr = ("x" if k == 1 else f"x{k}"), ("y domain" if k == 1 else f"y{k} domain")
        if i.get("sinyal_t"):
            s0, s1 = _tsi([int(i["sinyal_t"]) - sn, int(i["sinyal_t"])])
            fig.add_vrect(x0=s0, x1=s1, fillcolor=SINYAL_BANT, line_width=0, layer="below", row=k, col=1)
        # Takvim olayları (paritenin kendi takvimi): kuralın olayı kesikli, günün öbür olayı ince noktalı; adı ve
        # TSİ saati çizginin üstünde. Yakın iki olayın etiketi alt alta düşer.
        olaylar = sorted(((int(e["t"]), e["olay"]) for e in (x.get("takvim") or []) if t0 <= int(e["t"]) <= t1))
        if i.get("olay_t") and all(u != int(i["olay_t"]) for u, _ in olaylar) and t0 <= int(i["olay_t"]) <= t1:
            olaylar = sorted(olaylar + [(int(i["olay_t"]), i.get("olay") or "")])
        onceki, kat_ = None, 0
        for u, ol in olaylar:
            kendi = bool(i.get("olay_t")) and u == int(i["olay_t"])
            var["olay" if kendi else "takvim"] = True
            fig.add_vline(x=_tsi([u])[0], line=dict(color=MUREKKEP if kendi else GRI, width=1,
                                                       dash="dash" if kendi else "dot"), row=k, col=1)
            kat_ = (1 - kat_) if (onceki is not None and u - onceki < 0.3 * (t1 - t0)) else 0
            # Panelin sağ üçte birine düşen olayın etiketi çizginin soluna yaslanır: sağa yazılsaydı telefonun gömme
            # çerçevesinden taşardı (ör. akşam saatindeki FOMC kararı).
            sag = (u - t0) > 0.65 * (t1 - t0)
            fig.add_annotation(x=_tsi([u])[0], xref=xr, y=0.98 - 0.14 * kat_, yref=yr, yanchor="top",
                               xanchor="right" if sag else "left", showarrow=False,
                               text=f"{adlar.OLAY_KISA.get(ol, ol)} {_saat(u)} TSİ",
                               font=dict(size=10, color=MUREKKEP if kendi else "#5e5e5e"),
                               bgcolor="rgba(255,255,255,0.8)")
            onceki = u
        rx0 = _tsi([max(t0, r0)])[0] if r0 is not None and r0 < t1 else x0
        seviyeler = []
        for a in ("ust", "alt", "seviye"):
            v = i.get(a)
            if v is not None and all(abs(v - w) > 1e-9 for w in seviyeler):
                seviyeler.append(v)
        for j, v in enumerate(seviyeler):
            fig.add_trace(go.Scatter(x=[rx0, x1], y=[v * p] * 2, mode="lines", line=dict(color=MAVI, width=1, dash="dot"),
                                     name="referans seviye", legendgroup="seviye", showlegend=not var["seviye"],
                                     hovertemplate="seviye " + fiyat + "<extra></extra>"), k, 1)
            var["seviye"] = True
        # Stop ve hedef çizgisi sinyal mumunun başından (sinyal yoksa girişten bir mum önce) çıkıştan bir mum sonrasına
        # uzanır: giriş ile çıkış aynı dakikadaysa girişten çıkışa çizilen çizgi sıfır uzunlukta kalıp görünmüyordu.
        a0 = int(i["sinyal_t"]) - sn if i.get("sinyal_t") else int(i["giris_t"]) - sn
        a1 = max(int(i["cikis_t"]), int(i["giris_t"]) + sn) + sn
        g0, g1 = _tsi([max(t0, a0), min(t1, a1)])
        if i.get("stop") is not None:
            fig.add_trace(go.Scatter(x=[g0, g1], y=[i["stop"] * p] * 2, mode="lines", line=dict(color=CLARET, width=1.6),
                                     name="stop", legendgroup="stop", showlegend=not var["stop"],
                                     hovertemplate="stop " + fiyat + "<extra></extra>"), k, 1)
            var["stop"] = True
        if i.get("hedef") is not None:
            fig.add_trace(go.Scatter(x=[g0, g1], y=[i["hedef"] * p] * 2, mode="lines", line=dict(color=YESIL, width=1.6),
                                     name="hedef", legendgroup="hedef", showlegend=not var["hedef"],
                                     hovertemplate="hedef " + fiyat + "<extra></extra>"), k, 1)
            var["hedef"] = True
        yon = "alış" if i["yon"] > 0 else "satış"
        yonler.add(yon)
        # İşaretler eksende kırpılmaz: gün sonu kapanışıyla biten işlemin çıkışı panelin sağ kenarına düşer.
        fig.add_trace(go.Scatter(x=[_tsi([i["giris_t"]])[0]], y=[i["giris_f"] * p], mode="markers", cliponaxis=False,
                                 marker=dict(symbol="triangle-up" if i["yon"] > 0 else "triangle-down", size=13,
                                             color=MUREKKEP, line=dict(color="white", width=1.5)),
                                 name=f"giriş ({yon})", legendgroup="giris", showlegend=False,
                                 hovertemplate=f"giriş ({yon}) {_saat(i['giris_t'])} TSİ · " + fiyat + "<extra></extra>"),
                      k, 1)
        fig.add_trace(go.Scatter(x=[_tsi([i["cikis_t"]])[0]], y=[i["cikis_f"] * p], mode="markers", cliponaxis=False,
                                 marker=dict(symbol="x", size=11, color=MUREKKEP),
                                 name="çıkış", legendgroup="cikis", showlegend=(k == 1),
                                 hovertemplate=f"çıkış {_saat(i['cikis_t'])} TSİ · " + fiyat + "<extra></extra>"), k, 1)
        fig.update_xaxes(rangeslider_visible=False, tickformat="%H:%M", range=[x0, x1], row=k, col=1)
        fig.update_yaxes(tickformat=f".{max(1, hane - 1)}f", row=k, col=1)
    # Lejantta girişin iki yönü ayrı (paneller alış ve satışı karıştırabilir); bant ve olay çizgileri birer şekildir,
    # lejant girdileri boş izlerle kurulur.
    for yon, sembol in (("alış", "triangle-up"), ("satış", "triangle-down")):
        if yon in yonler:
            fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name=f"giriş: {yon} (yürütülen fiyat)",
                                     marker=dict(symbol=sembol, size=12, color=MUREKKEP)), 1, 1)
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name="sinyal mumu",
                             marker=dict(symbol="square", size=13, color=SINYAL_BANT)), 1, 1)
    if var["sikisma"]:
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name="sıkışma mumu",
                                 marker=dict(symbol="square", size=13, color=SIKISMA_BANT)), 1, 1)
    if var["olay"]:
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", name="kuralın olayı",
                                 line=dict(color=MUREKKEP, width=1, dash="dash")), 1, 1)
    if var["takvim"]:
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", name="takvimdeki öbür olay",
                                 line=dict(color=GRI, width=1, dash="dot")), 1, 1)
    vwap_ = var["vwap"]
    isaret = ["Mavi bant: sinyal mumu"] \
        + ([(f"noktalı mavi: sinyal anındaki VWAP{' ve bant' if var['vbant'] else ''} (sinyal mumundan)" if vwap_
             else "noktalı mavi: referans seviye (oluştuğu andan)")] if var["seviye"] else []) \
        + (["turuncu: Bollinger bandı · kesikli gri: Keltner kanalı · turuncu gölge: sıkışma mumu (Bollinger'in iki "
            "bandı Keltner'in içinde)"] if var["bb"] else []) \
        + (["turuncu: gün içinde yürüyen VWAP" + (" · noktalı turuncu: bandı" if var["vbant"] else "")]
           if vwap_ else []) \
        + (["kırmızı: stop"] if var["stop"] else []) + (["yeşil: hedef"] if var["hedef"] else []) \
        + (["kesikli: kuralın olayı"] if var["olay"] else []) \
        + (["noktalı gri: takvimdeki öbür olay"] if var["takvim"] else []) + ["▲ alış · ▼ satış girişi · × çıkış"]
    alt = [f"{PARITE[c]} · stratejinin kendi mum uzunluğu (orta fiyat), saatler TSİ · {adlar.varsayilan_ad(b)}",
           f"Örneklem dışından ({_dis(o)}) sabit çekilişle, ayrı günlerde: kazanan, kaybeden ve tuzak (lehine en az "
           f"{vir(float(o['kunye']['ornek']['esik']), 1)} R gidip zararla kapanan)", " · ".join(isaret)]
    if _gece_referansi(b):
        alt.append(f"Panel gece aralığının başından (Londra 00:00; {adlar.tsi_yaz(['Londra 00:00'])}) açılır: "
                   "aralığın tepesini ve dibini kuran mumlar panelde")
    if stopsuz:
        alt.append(f"Stopsuz kural: stop çizgisi yok; R birimi {R_BIRIMI.get(b.get('aile'), 'girişteki ATR')}")
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
    yil = int(k["baslangic"][:4])
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
        hv = h.to_numpy()
        dd = np.maximum.accumulate(np.concatenate([[0.0], hv]))[1:] - hv
        gun = [g.strftime("%Y-%m-%d") for g in h.index]
        _iki_donem(fig, gun, [round(float(v), 2) for v in h], dis, "havuz (paritelerin toplamı)", MUREKKEP, 2.2,
                   hover="%{x|%d.%m.%Y}: %{y:.1f} R<extra>havuz</extra>")
        fig.add_trace(go.Scatter(x=gun, y=-dd, mode="lines", fill="tozeroy", line=dict(color=CLARET, width=1),
                                 fillcolor="rgba(140,47,57,0.22)", name="havuzun düşüşü", showlegend=False,
                                 hovertemplate="%{x|%d.%m.%Y}: −%{customdata:.1f} R<extra>" + f"{yil}'{_den(yil)} bu "
                                               "yana tepeden</extra>", customdata=dd), 2, 1)
        # Örneklem dışının kendi düşüşü: tepe örneklem dışının başında sıfırlanır (tablodaki ölçü). Dolu alan bütün
        # dönemin tepesinden ölçer ve gri alanda da 2018 tepesine göre yazar; ikisi aynı panelde ayrı okunur.
        kd = next((j for j, g in enumerate(gun) if g >= dis), None)
        if kd is not None:
            tepe = np.maximum.accumulate(np.concatenate([[hv[kd - 1] if kd > 0 else 0.0], hv[kd:]]))[1:]
            dd2 = tepe - hv[kd:]
            fig.add_trace(go.Scatter(x=gun[kd:], y=-dd2, mode="lines", line=dict(color=MUREKKEP, width=1.3, dash="dash"),
                                     name="örneklem dışının düşüşü", showlegend=False, customdata=dd2,
                                     hovertemplate="%{x|%d.%m.%Y}: −%{customdata:.1f} R<extra>örneklem dışının "
                                                   "tepesinden</extra>"), 2, 1)
    fig.add_vrect(x0=dis, x1=k["bitis"], fillcolor=OOS_GOLGE, line_width=0, layer="below", row="all", col=1)
    fig.add_hline(y=0, line=dict(color=MUREKKEP, width=0.8), row=1, col=1)
    fig.update_xaxes(tickformat="%Y")              # sayısal biçim: eksende İngilizce ay adı çıkmaz
    bas = baslik_koy(fig, f"Birikimli sonuç — {adlar.BIRIM[birim][0]}",
                     [_kunye(o), ("Türetilmiş varsayılan (ön kayıtlı varsayılandan tek boyutu değiştirilerek)"
                                  if adlar.turetilmis(b) else "Önceden kayıtlı varsayılan (veriye bakmadan seçildi)")
                      + f" · örneklem içi ({_ic(o)}) soluk, "
                      f"örneklem dışı ({_dis(o)}) koyu ve gri alanda",
                      f"Havuz: aynı kural {len(egriler)} paritede birlikte; haftalık birikimli R",
                      f"Düşüş: dolu alan {yil}'{_den(yil)} bu yana en yüksek değere göre; kesikli çizgi örneklem dışının "
                      "başında sıfırlanır (tablodaki azami düşüş onun günlük ölçüsüdür, haftalık çizgi biraz küçük verir)"])
    so._yaz(fig, f"{birim}-egri.html", yukseklik(bas, 470))


# ─────────────────────────────────────────────────────── 3 · ızgara: ısı haritası
GRI_HUCRE = "#dedad2"


def _isi_iz(isi: dict, donem: str, esik: int, olcu: str = "beklenti_r"):
    """Bir dönemin hücreleri: renkli katman (en az `esik` işlemli hücre), gri katman (daha az işlemli hücre; değer ve
    işlem sayısı yazılı) ve her hücrenin yazısı. İşlemsiz hücre "—"; aynı kombinasyonun ikinci adı ("= tek mum")
    renksiz."""
    renk, gri, yazi = [], [], []
    for satir in isi["hucre"]:
        zr, zg, ys = [], [], []
        for h in satir:
            if h and h.get("esleme"):
                zr.append(None), zg.append(None), ys.append(f"= {adlar.DEGER.get(h['esleme'], h['esleme'])}")
                continue
            d = (h or {}).get(donem) or {}
            v, n = d.get(olcu), int(d.get("n") or 0)
            if v is None or n == 0:
                zr.append(None), zg.append(None), ys.append("—")
                continue
            ys.append(f"{_r(v)}<br>n {vir(n, 0)}")
            zr.append(v if n >= esik else None)
            zg.append(None if n >= esik else 0.5)
        renk.append(zr), gri.append(zg), yazi.append(ys)
    return renk, gri, yazi


def izgara(o: dict, birim: str, cift: str = "") -> None:
    cift = cift or ANA
    b = o["birim"][birim]
    v = b["cift"].get(cift)
    if not v:
        return
    isi = v["isi"]
    aile = b.get("aile") or ""
    esik = _kova_esik(o)
    y_ad = adlar.param_ad(isi["y_ad"], aile)
    ylab = [adlar.deger_yaz(isi["y_ad"], y, aile) for y in isi["y"]]
    xlab = [f"{x} dk" for x in isi["x"]]
    # İki dönem ALT ALTA: yan yana dizildiğinde telefonda iki panel başlığı birbirine biniyor, hücreler
    # 50 pikselin altına iniyordu.
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.14,
                        subplot_titles=(f"Örneklem içi ({_ic(o)})", f"Örneklem dışı ({_dis(o)})"))
    tum = [x for d in ("is", "oos") for row in _isi_iz(isi, d, esik)[0] for x in row if x is not None]
    sinir = max(0.25, max((abs(x) for x in tum), default=0.25))
    esleme = False
    for j, d in enumerate(("is", "oos"), start=1):
        renk, gri, yazi = _isi_iz(isi, d, esik)
        esleme = esleme or any(s.startswith("=") for r in yazi for s in r)
        # Renk ölçeği iki panelin ORTAK ölçeğidir (coloraxis): örneklem dışı panelin bütün hücreleri griyse de ölçek
        # görünür. Yazı ayrı bir iz: ısı haritası değeri boş hücreye yazı basmaz (gri ve işlemsiz hücre de yazı taşır).
        fig.add_trace(go.Heatmap(z=gri, x=xlab, y=ylab, zmin=0, zmax=1, colorscale=[[0, GRI_HUCRE], [1, GRI_HUCRE]],
                                 showscale=False, hoverinfo="skip", xgap=2, ygap=2), j, 1)
        fig.add_trace(go.Heatmap(z=renk, x=xlab, y=ylab, coloraxis="coloraxis", hoverinfo="skip", xgap=2, ygap=2), j, 1)
        hx, hy, ht, hh = [], [], [], []
        for yi, y in enumerate(ylab):
            for xi, x in enumerate(xlab):
                hx.append(x), hy.append(y), ht.append(yazi[yi][xi])
                hh.append(f"{y} · {x}: " + ("işlem yok" if yazi[yi][xi] == "—" else yazi[yi][xi].replace("<br>", " · ")))
        fig.add_trace(go.Scatter(x=hx, y=hy, mode="text", text=ht, textfont=dict(size=11, color=MUREKKEP),
                                 hovertext=hh, hoverinfo="text", showlegend=False), j, 1)
        fig.update_xaxes(type="category", categoryorder="array", categoryarray=xlab, row=j, col=1)
        fig.update_yaxes(type="category", categoryorder="array", categoryarray=ylab, row=j, col=1)
    fig.update_layout(coloraxis=dict(colorscale=[[0, CLARET], [0.5, "#f2f0eb"], [1, MAVI]], cmin=-sinir, cmax=sinir,
                                     colorbar=dict(title=dict(text="R / işlem"), thickness=10, len=0.8)))
    vx, vy = isi["varsayilan"]
    for j in (1, 2):
        if vx in isi["x"] and vy in isi["y"]:
            fig.add_shape(type="rect", xref=f"x{'' if j == 1 else j}", yref=f"y{'' if j == 1 else j}",
                          x0=isi["x"].index(vx) - 0.5, x1=isi["x"].index(vx) + 0.5,
                          y0=isi["y"].index(vy) - 0.5, y1=isi["y"].index(vy) + 0.5,
                          line=dict(color=MUREKKEP, width=2))
    alt = [f"{PARITE[cift]} · işlem başına net ortalama R · satırlar: {y_ad} · sütunlar: zaman dilimi",
           f"Öbür parametreler {adlar.varsayilan_ad(b)}da; çerçeveli hücre varsayılanın kendisi",
           f"Renk en az {esik} işlemli hücrede; gri: {esik}'{_den(esik)} az işlem (değer ve işlem sayısı yazılı); "
           "—: işlem yok"]
    if esleme:
        alt.append("«= tek mum»: aynı kombinasyon; 60 dakikalık mumda 60 dakikalık ilk denge mumun kendisidir ve "
                   "«tek mum» satırında bir kez sayılır")
    sn_ = _saat_param_notu({isi["y_ad"]: isi["y"]})
    if sn_:
        alt.append(sn_)
    bas = baslik_koy(fig, f"Parametre ızgarası — {adlar.BIRIM[birim][0]}" + ("" if cift == ANA else f", {PARITE[cift]}"),
                     alt)
    # Ana paritenin dışındaki ızgara (örneklem dışında artı kalan pariteler: adlar.arti_pariteler) paritesinin adıyla.
    ad = f"{birim}-izgara.html" if cift == ANA else f"{birim}-izgara-{cift.lower()}.html"
    so._yaz(fig, ad, yukseklik(bas, 150 + 2 * 46 * max(2, len(ylab))))


def izgaralar(o: dict, birim: str) -> None:
    """Ana paritenin ızgarası ve örneklem dışında artı kalan öbür paritelerinki (ders metni aynı listeyi gömer)."""
    b = o["birim"][birim]
    izgara(o, birim)
    for c in adlar.arti_pariteler(b, [x for x in PARITE if (b.get("cift") or {}).get(x)]):
        if c != ANA:
            izgara(o, birim, c)


# ─────────────────────────────────────────────────────── 4 · koşul kovaları
KOSUL_HUKUM = {"tuttu": "tuttu", "tutmadi": "tutmadı", "secilmedi": "kova seçilmedi"}
#: Seçilen kovanın vurgu rengi: parite renklerinden (MAVI, CLARET, TURUNCU, YESIL) ayrı, sitenin teal'i.
SECILEN_RENK = "#1d5c5c"


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
    asgari = _kova_esik(o)
    oos_asgari = int(o["kunye"]["uygulama_esik"]["kosul_oos"])
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
        hk = KOSUL_HUKUM[k["hukum"]]
        n_sec = int(k.get("oos_secilen_n") or 0)
        if k["hukum"] == "tutmadi" and n_sec < oos_asgari:
            hk = f"tutmadı (az işlem: {vir(n_sec, 0)})"
        anahtar.append(f"g{gi}"), yazi.append(f"<i>{hk}</i>")
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
                         marker_color=[SECILEN_RENK if s_ else MUREKKEP for s_ in sec], hovertext=oos_h, hoverinfo="text"))
    fig.add_trace(go.Bar(x=[None], y=[anahtar[0]], orientation="h", name="örneklem dışı · seçilen kova (kalın ad)",
                         marker_color=SECILEN_RENK, hoverinfo="skip"))
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
    alt = [f"{PARITE[cift]} · {adlar.varsayilan_ad(o['birim'][birim])} · işlem başına net R, kova kova (fareyle işlem "
           "sayısı ve kazanan payı)",
           f"Kova sınırları örneklem içinden; seçilen kova örneklem içinde koşulsuz ortalamadan (kesikli) iyi ve en az "
           f"{asgari} işlemli",
           f"Hüküm değişkenin satırında: tuttu = seçilen kovaların örneklem dışındaki birlikte ortalaması en az "
           f"{oos_asgari} işlemle artı ve seçilmeyen kovaların birlikte ortalamasının üstünde; tek tek kovalar bunun "
           "altında kalabilir · az işlem: seçilen kovaların örneklem dışı işlemi bu sayının altında"]
    if atlanan:
        alt.append("Sınanamadığı için çizilmeyen: " + ", ".join(atlanan) + " (aynı ölçü ya da bütün kovalar seçildi)")
    bas = baslik_koy(fig, f"Koşul kovaları — {adlar.BIRIM[birim][0]}", alt)
    so._yaz(fig, f"{birim}-kosul.html", yukseklik(bas, 110 + 22 * len(anahtar)))


# ─────────────────────────────────────────────────────── 5 · giriş saati (TSİ)
def _saat_sira(h: int) -> int:
    """Saat kovalarının sırası FX gününün sırasıdır: 01'den 00'a (00 kovası kışın günün son saati, New York 16:00;
    yazın ilk saati, New York 17:00). Kovanın kendi sayısıyla dizmek 00'ı günün en erken girişi gibi en sola
    koyuyordu ve parite parite eklenen kategoriler sona düşüyordu."""
    return (h - 1) % 24


def saat(o: dict, birim: str) -> None:
    b = o["birim"][birim]
    esik = _kova_esik(o)
    fig = make_subplots(rows=1, cols=1, subplot_titles=("İşlem başına net R, giriş saatine (TSİ) göre",))
    tablo = {c: (((b["cift"].get(c) or {}).get("varsayilan")) or {}).get("saat_tsi") or {} for c in PARITE}
    saatler = sorted({int(h) for s in tablo.values() for h in s}, key=_saat_sira)
    # Tek bir yerel saatte giren kuralın iki kovası yaz ve kış saatidir (tanım adlar.mevsim_kovalari, metin de onu
    # okur): her paritede aynı iki kova tutunca adlandırılır. Az kovalı eksende etiket kovanın aralığıdır; yirmi dört
    # kovada aralık telefona sığmaz, saat yazılır ve alt başlık okunuşunu verir.
    mevsimler = {adlar.mevsim_kovalari(s) for s in tablo.values() if s}
    mevsim = next(iter(mevsimler)) if len(mevsimler) == 1 and None not in mevsimler else None
    mevsim_ad = {mevsim[0]: "Yaz saati", mevsim[1]: "Kış saati"} if mevsim else {}
    aralik = len(saatler) <= 6

    def etiket(h: int) -> str:
        if mevsim:
            return f"{mevsim_ad[h]}<br>{h:02d}:00–{h:02d}:59"
        return f"{h:02d}:00–<br>{h:02d}:59" if aralik else f"{h:02d}"

    kat = [etiket(h) for h in saatler]
    yogun = []                          # en az `esik` işlemli kovaların değerleri: eksen onlara göre kurulur
    soluk = False                       # eşiğin altında kalan bir kova var mı (alt başlığın notu yalnız o zaman)
    for c, s in tablo.items():
        if not s:
            continue
        hs = [h for h in saatler if str(h) in s]
        y = [s[str(h)].get("beklenti_r") for h in hs]
        n = [int(s[str(h)].get("n") or 0) for h in hs]
        yogun += [v for v, k in zip(y, n) if k >= esik and v is not None]
        soluk = soluk or any(k < esik for k in n)
        metin = [(f"{mevsim_ad[h]} · " if mevsim else "") + f"{h:02d}:00–{h:02d}:59 TSİ: {_r(v)} R · {vir(k, 0)} işlem"
                 + (f" ({esik}'{_den(esik)} az: metin saymaz)" if k < esik else "") for h, v, k in zip(hs, y, n)]
        fig.add_trace(go.Bar(x=[etiket(h) for h in hs], y=y, name=PARITE[c],
                             marker=dict(color=RENK[c], opacity=[1.0 if k >= esik else 0.28 for k in n]),
                             hovertext=metin, hoverinfo="text"))
    fig.add_hline(y=0, line=dict(color=MUREKKEP, width=0.8))
    # Etiket yatay; çok kovalı eksende ikide (yirmi dört kovada üçte) bir saat yazılır: döndürülmüş saat etiketleri
    # telefonda alttaki lejantın üstüne biniyordu.
    # Saatlerde boşluk varsa (işlem olmayan saat eksende yoktur) her kova etiketlenir: kategori ekseni eşit aralıklıdır
    # ve etiketsiz bir çubuğun saati komşu etiketlerden okunamaz (18 ile 22 arasındaki etiketsiz çubuk 21'dir, 20 değil).
    bosluk = any(_saat_sira(b2) - _saat_sira(a2) > 1 for a2, b2 in zip(saatler, saatler[1:]))
    adim = 1 if (len(kat) <= 8 or bosluk) else (2 if len(kat) <= 16 else 3)
    fig.update_xaxes(type="category", categoryorder="array", categoryarray=kat, tickangle=0,
                     tickvals=kat[::adim], ticktext=kat[::adim],
                     tickfont=dict(size=9 if (bosluk and len(kat) > 12) else 12))
    if yogun:
        y0, y1 = min(0.0, min(yogun)), max(0.0, max(yogun))
        pay = 0.12 * (y1 - y0) or 0.05
        fig.update_yaxes(range=[y0 - pay, y1 + pay])
    fig.update_layout(barmode="group", bargap=0.25)
    eksen = ("kural tek bir yerel saatte girer ve o saatin TSİ karşılığı yaz ve kış saatinde bir saat kayar: iki kova "
             "bir giriş saati seçimi değil, mevsimin kıyasıdır" if mevsim else
             "eksen: giriş saati, TSİ" if aralik else
             "eksen: giriş saati (10 = 10:00–10:59 TSİ)" + ("; işlem olmayan saat eksende yok, her çubuk kendi saatiyle "
                                                            "etiketli" if bosluk else ""))
    alt = [f"İşlem başına net ortalama R, girişin TSİ saatine göre (bütün dönem) · {adlar.varsayilan_ad(b)} · " + eksen]
    if not yogun:
        alt.append(f"Hiçbir saat {esik} işleme ulaşmıyor: çubuklar betimleyicidir, metin saat okuması kurmaz")
    elif soluk:
        alt.append(f"Soluk çubuk: {esik}'{_den(esik)} az işlem, metin bu saatleri saymaz; eksen yoğun saatlere göre "
                   "kurulur, soluk çubuk kırpılabilir")
    alt.append("TSİ = UTC + 3, yıl boyu (Türkiye 2016'dan beri saat değiştirmiyor); seans saatleri Avrupa ve ABD saat "
               "değişimiyle bir saat kayar")
    if 0 in saatler and len(saatler) > 1:
        alt.append("Eksen FX gününün sırasıyla: 01'den 00'a; 00 kovası (TSİ 00:00–01:00) kışın günün son saatidir "
                   "(New York 16:00–17:00), yazın ilk saatidir (New York 17:00–18:00)")
    bas = baslik_koy(fig, f"Giriş saatine göre — {adlar.BIRIM[birim][0]}", alt)
    so._yaz(fig, f"{birim}-saat.html", yukseklik(bas, 400))


# ─────────────────────────────────────────────────────── 6 · zaman dilimi kıyası (5 / 15 / 60 dk)
#: Zaman diliminin rengi nötr bir tonun açıktan koyuya kademeleridir: parite renkleri (MAVI, CLARET, TURUNCU, YESIL)
#: yalnız paritelere ayrılmıştır ve aynı sayfadaki eğri ve saat figürlerinde onları taşır.
TF_RENK = {"5": "#c4c4c4", "15": "#7d7d7d", "60": "#2b2b2b"}


def tf(o: dict, birim: str) -> None:
    b = o["birim"][birim]
    ciftler = [c for c in PARITE if (b["cift"].get(c) or {}).get("tf")]
    if not ciftler:
        return
    bos = b.get("tf_bos") or {}
    dilimler = sorted({t for c in ciftler for t in b["cift"][c]["tf"]}, key=int)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.14,
                        subplot_titles=(f"Örneklem içi ({_ic(o)})", f"Örneklem dışı ({_dis(o)})"))
    for j, d in enumerate(("is", "oos"), start=1):
        for t in dilimler:
            if t in bos:                       # hiçbir paritede işlem yok: çubuk ve lejant girdisi yok, alt yazıda
                continue
            hucre = [(b["cift"][c]["tf"].get(t) or {}).get(d) or {} for c in ciftler]
            metin = [f"{PARITE[c]} · {t} dk: {_r(h.get('beklenti_r'), 3)} R · {vir(int(h.get('n') or 0), 0)} işlem"
                     + (f" · Sharpe {vir(h['sharpe'], 2)}" if h.get("sharpe") is not None and math.isfinite(h["sharpe"])
                        else "")
                     for c, h in zip(ciftler, hucre)]
            fig.add_trace(go.Bar(x=[PARITE[c] for c in ciftler], y=[h.get("beklenti_r") for h in hucre],
                                 name=f"{t} dk mum", marker_color=TF_RENK.get(t, GRI), showlegend=(j == 1),
                                 legendgroup=t, hovertext=metin, hoverinfo="text"), j, 1)
        fig.add_hline(y=0, line=dict(color=MUREKKEP, width=0.8), row=j, col=1)
        fig.update_yaxes(title_text="net R / işlem", row=j, col=1)
    fig.update_layout(barmode="group", bargap=0.3)
    v = b["varsayilan"]
    aile = b.get("aile") or ""
    oteki = [adlar.param_yaz(k, x, aile) for k, x in v.items() if k != "tf"]
    alt = [f"{_bas_buyuk(adlar.varsayilan_ad(b))}; yalnız mum uzunluğu değişir ({', '.join(oteki)})",
           "İşlem başına net ortalama R · her parite ayrı · varsayılanın kendi dilimi "
           f"{v.get('tf')} dk"]
    for t, x in bos.items():
        alt.append(f"{t} dk mum: hiçbir paritede işlem yok" + (f" — {x['neden']}" if x.get("neden") else ""))
    sn_ = _saat_param_notu({k: x for k, x in v.items() if k in adlar.SAAT_SEHIR})
    if sn_:
        alt.append(sn_)
    bas = baslik_koy(fig, f"Zaman dilimi kıyası — {adlar.BIRIM[birim][0]}", alt)
    so._yaz(fig, f"{birim}-tf.html", yukseklik(bas, 520))


BIRIM_SEKILLERI = (ornek, egri, izgaralar, kosul, saat, tf)


# ─────────────────────────────────────────────────────── ortak: karşılaştırma
#: Korelasyon matrisinin hücresine yazılan değerin eşiği. Daha düşük eşik 22 × 22 matriste telefonda hücreleri
#: okunmaz bir yazı yığınına çeviriyordu; |ρ| ≥ 0,25 çiftlerinin tamamı ders metnindeki tabloda (ders_motor.KOR_ESIK).
KOR_YAZI = 0.5


def karsilastirma(o: dict) -> None:
    satir = []
    for b, v in o["birim"].items():
        h = ((v.get("havuz") or {}).get("varsayilan") or {}).get("oos") or {}
        if h.get("n"):
            satir.append((b, h.get("beklenti_r"), h.get("ga_alt"), h.get("ga_ust"), h.get("n")))
    if not satir:
        return
    satir.sort(key=lambda x: x[1] if x[1] is not None else -9)
    # Stopsuz kuralların R'si girişteki ATR'dir (bir risk değil ölçek birimi): sıralamada iki tür R yan yana durur ve
    # etiket bunu adıyla söyler (tanım ders_motor._stopsuz_birimler ile aynı: varsayılanın stop türü "yok").
    stopsuz = {b for b, v in o["birim"].items() if ((v.get("varsayilan") or {}).get("stop_turu")) == "yok"}
    ad = {s[0]: adlar.BIRIM[s[0]][1] + (" ‡" if s[0] in stopsuz else "") for s in satir}  # kısa: telefonda eksen dar
    fig = make_subplots(rows=1, cols=1, subplot_titles=("Örneklem dışı · net R ve %95 aralığı",))
    fig.add_trace(go.Scatter(
        x=[s[1] for s in satir], y=[ad[s[0]] for s in satir], mode="markers",
        marker=dict(size=9, color=[MAVI if (s[2] or -1) > 0 else (MUREKKEP if (s[1] or 0) > 0 else CLARET) for s in satir]),
        error_x=dict(type="data", symmetric=False, array=[(s[3] - s[1]) if s[3] is not None else 0 for s in satir],
                     arrayminus=[(s[1] - s[2]) if s[2] is not None else 0 for s in satir], color=GRI, thickness=1.2),
        hovertext=[f"{ad[s[0]]}: {_r(s[1], 3)} R · %95 [{_r(s[2], 3)}, {_r(s[3], 3)}] · {vir(s[4], 0)} işlem"
                   for s in satir], hoverinfo="text", showlegend=False), 1, 1)
    fig.add_vline(x=0, line=dict(color=MUREKKEP, width=0.9))
    alt = [_kunye(o), f"Önceden kayıtlı varsayılanlar{_turetilmis_not(o)}; {_sayi_ad(len(PARITE))} paritenin "
           "işlemleri birlikte (havuz), "
           f"{so.tarih(o['kunye']['dis_baslangic'])} → {so.tarih(o['kunye']['bitis'])} · çizgi: %95 bootstrap aralığı",
           "Mavi: aralığın alt ucu sıfırın üstünde · siyah: ortalama artı, aralık sıfırı kapsıyor · kırmızı: "
           "ortalama eksi"]
    if stopsuz & set(ad):
        alt.append("‡ Stopsuz kural: R girişteki ATR(14), yani bir risk değil ölçek birimi; öbür kurallarda R stop "
                   "uzaklığıdır")
    bas = baslik_koy(fig, "Örneklem dışında işlem başına net R — bütün stratejiler", alt)
    so._yaz(fig, "karsilastirma-ozet.html", yukseklik(bas, 90 + 26 * len(satir)))
    kor = o.get("korelasyon") or {}
    if kor.get("tum"):
        # Sıra derslerin sırası (aile aile): aynı bahsi oynayan stratejiler blok olarak görünür. Yalnız alt
        # üçgen çizilir (matris simetrik); hücreye yalnız |ρ| ≥ KOR_YAZI yazılır, değerin tamamı fareyle okunur.
        sira = [b for bl in adlar.DERS_BIRIM.values() for b in bl if b in kor["birimler"]]
        sira += [b for b in kor["birimler"] if b not in sira]
        ix = [kor["birimler"].index(b) for b in sira]
        ad = [adlar.BIRIM[b][1] for b in sira]
        z = [[kor["tum"][i][j] if c <= r else None for c, j in enumerate(ix)] for r, i in enumerate(ix)]
        metin = [[(vir(v, 2) if (v is not None and abs(v) >= KOR_YAZI and r != c) else "") for c, v in enumerate(satir)]
                 for r, satir in enumerate(z)]
        fig = make_subplots(rows=1, cols=1, subplot_titles=("Günlük R korelasyonu (bütün dönem)",))
        fig.add_trace(go.Heatmap(z=z, x=ad, y=ad, zmin=-1, zmax=1, text=metin, texttemplate="%{text}",
                                 colorscale=[[0, CLARET], [0.5, "#f2f0eb"], [1, MAVI]], textfont=dict(size=9),
                                 colorbar=dict(thickness=10, len=0.6, y=0.7),
                                 hovertemplate="%{y} × %{x}: %{z:.2f}<extra></extra>", xgap=1, ygap=1), 1, 1)
        fig.update_yaxes(autorange="reversed", showgrid=False)
        fig.update_xaxes(tickangle=-50)
        bas = baslik_koy(fig, "Stratejiler arası günlük R korelasyonu",
                         [f"Önceden kayıtlı varsayılanlar{_turetilmis_not(o)}, {_sayi_ad(len(PARITE))} paritenin günlük R "
                          "toplamı · bütün dönem · işlemsiz gün 0",
                          f"Sıra derslerin sırası (seans, yapı, fade, haber, akış) · hücrede yalnız |ρ| ≥ {vir(KOR_YAZI, 2)}; "
                          "daha düşük eşiği aşan çiftlerin tamamı metindeki tabloda",
                          "Sıfıra yakın: iki strateji farklı günlerde ya da farklı yönlerde para kazanıp kaybediyor"])
        so._yaz(fig, "karsilastirma-korelasyon.html", yukseklik(bas, 760))


# ─────────────────────────────────────────────────────── ortak: maliyet merdiveni ve rastgele yön
#: Maliyet kademeleri nötr bir tonun açıktan koyuya kademeleridir (parite renkleri yalnız paritelere ayrılmıştır);
#: kademeyi biçim de ayırır (brüt boş daire, yalnız makas dolu daire, kayma 0 boş elmas, temel senaryo dolu elmas, sonra
#: kare ve çarpı).
MALIYET_RENK = {0: ("#8a8a8a", "diamond-open"), 1: (MUREKKEP, "diamond"), 2: ("#6e6e6e", "square"),
                3: ("#3a3a3a", "x")}


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
    seri = [("brüt (orta fiyattan orta fiyata)", "#d4d0c7", "circle-open"),
            ("yalnız makas (kayma ve haber kayması 0)", "#b8b3a8", "circle")]
    for q, kk in enumerate(kademe):
        temel_mi = 3 + q == temel
        seri.append((f"net, kayma {vir(float(kk), 1)} pip" + (" (temel senaryo)" if temel_mi else ""), *MALIYET_RENK[q]))
    for j, (etiket, rk, sembol) in enumerate(seri):
        fig.add_trace(go.Scatter(x=[x[1 + j] for x in satir], y=ad, mode="markers", name=etiket,
                                 marker=dict(symbol=sembol, size=10 if 1 + j == temel else 8, color=rk,
                                             line=dict(width=1.4, color=rk) if sembol.endswith("open") else None),
                                 hovertext=[f"{a}: {_r(x[1 + j], 3)} R · {etiket}" for a, x in zip(ad, satir)],
                                 hoverinfo="text"), 1, 1)
    fig.add_vline(x=0, line=dict(color=MUREKKEP, width=0.9))
    bas = baslik_koy(fig, "Maliyet merdiveni — aynı kural, artan yürütme maliyeti",
                     [f"Önceden kayıtlı varsayılanlar{_turetilmis_not(o)} · kayma her dolumda (giriş, piyasa çıkışı ve "
                      "stop) ödenir; "
                      f"kayma kademelerinde haber penceresindeki dolumlar ayrıca {hk} pip öder",
                      "Brüt ile yalnız makas arasındaki fark gerçek bid/ask makasıdır · R: yürütülen girişten stopa "
                      "planlanan risk, stopsuz kurallarda girişteki ATR(14)"])
    so._yaz(fig, "karsilastirma-maliyet.html", yukseklik(bas, 150 + 26 * len(satir)))


def rastgele(o: dict, cift: str = "") -> None:
    cift = cift or ANA
    k_ = o["kunye"]
    asgari = int(k_["uygulama_esik"]["rastgele"])
    tekrar = int(k_["hukum_kurali"]["rastgele_tekrar"])
    satir, disarida = [], []
    for b, v in o["birim"].items():
        va = (v["cift"].get(cift) or {}).get("varsayilan") or {}
        r = (va.get("rastgele") or {}).get("oos") or {}
        if r.get("n"):
            satir.append((b, va["oos"].get("beklenti_r"), r.get("p05"), r.get("p95"), r.get("ort"), r.get("yuzdelik")))
        elif va:
            disarida.append(f"{adlar.BIRIM[b][1]} (örneklem dışında {vir(int((va.get('oos') or {}).get('n') or 0), 0)} "
                            "işlem)")
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
    BANT = "rgba(138,138,138,0.38)"
    for x, y in zip(satir, ad):
        fig.add_trace(go.Scatter(x=[x[2], x[3]], y=[y, y], mode="lines", line=dict(color=BANT, width=9),
                                 showlegend=False, hoverinfo="skip"), 1, 1)
    fig.add_trace(go.Scatter(x=[x[4] for x in satir], y=ad, mode="markers", name="rastgele yönün ortalaması",
                             marker=dict(symbol="line-ns-open", size=12, color="#5e5e5e", line=dict(width=2)),
                             hovertext=[f"{a}: rastgele ortalama {_r(x[4], 3)} R" for a, x in zip(ad, satir)],
                             hoverinfo="text"), 1, 1)
    fig.add_trace(go.Scatter(x=[x[1] for x in satir], y=ad, mode="markers", name="stratejinin kendisi",
                             marker=dict(symbol="diamond", size=10, color=MUREKKEP),
                             hovertext=[f"{a}: {_r(x[1], 3)} R" + (f" · rastgele dağılımda {vir(x[5], 1)}. yüzdelik"
                                                                        if x[5] is not None else "")
                                        for a, x in zip(ad, satir)], hoverinfo="text"), 1, 1)
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", name=f"rastgele yönün %5–95 bandı ({vir(tekrar, 0)} tekrar)",
                             line=dict(color=BANT, width=9)), 1, 1)
    alt = ["Aynı giriş dakikası, aynı risk uzaklığı, aynı çıkış kuralı; yalnız yön yazı turayla",
           "Stratejinin elması bandın sağındaysa yön seçimi aynı zamanlamaya bir şey katıyordur; bandın yeri "
           "zamanlamanın ve maliyetin payıdır",
           "Sıra: rastgele dağılımdaki yüzdelik"]
    if disarida:
        alt.append(f"Sınama kurulmayan (örneklem dışında {asgari} işlemden az): " + ", ".join(disarida))
    bas = baslik_koy(fig, "Yön seçmenin değeri — strateji ile aynı işlemlerin rastgele yönlüsü", alt)
    so._yaz(fig, "yontem-rastgele.html", yukseklik(bas, 120 + 26 * len(satir)))


# ─────────────────────────────────────────────────────── ortak: veri kalitesi
def _saat_dk(saat: str) -> int:
    """"SS:DD" → günün dakikası."""
    s, d = (int(x) for x in saat.split(":")[:2])
    return 60 * s + d


def _et_dk(x: int, sinir: str) -> str:
    """FX gününün sınırından (künye: fx_gun_siniri_et, New York) x dakika: saat olarak ("16:55")."""
    t = (_saat_dk(sinir) + x) % (24 * 60)
    return f"{t // 60:02d}:{t % 60:02d}"


def _ny_tsi(saat: str) -> str:
    """New York saatinin TSİ karşılığı, ABD yaz ve kış saatinde ("23:55 ya da 00:55"; adlar.tsi_an tek tanım). Kısa
    yazım panel başlığına sığar; hangi değerin hangi rejim olduğunu figürün alt yazısı söyler."""
    yaz, kis = (f"{adlar.tsi_an(g, saat, 'America/New_York'):%H:%M}" for _, g in adlar.TSI_REJIM[:2])
    return yaz if yaz == kis else f"{yaz} ya da {kis}"


def veri(o: dict) -> None:
    k = ((o.get("veri") or {}).get("kalite") or {})
    if not k:
        return
    # Devir profilinin sıfırı FX gününün sınırı, kesikli çizgi pozisyonların kapandığı dilim: ikisi de künyeden
    # (zaman.GUN_SONU · ayar gun_sonu_et); elle yazılan saat ayar değiştiği gün figürde yanlış dilimi gösterirdi.
    sinir, gun_sonu = o["kunye"]["fx_gun_siniri_et"], o["kunye"]["gun_sonu_et"]
    # İki panel ALT ALTA: yan yana dizildiğinde telefonda (353 px) iki panel başlığı üst üste biniyordu.
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.16,
                        subplot_titles=("Saat saat medyan makas (New York saati)",
                                        f"Devir çevresinde beş dakikalık dilimler<br>(New York {sinir} = TSİ "
                                        f"{_ny_tsi(sinir)})"))
    for c in [x for x in PARITE if x in k] + [x for x in k if x not in PARITE]:
        v = k[c]
        m = v.get("makas") or {}
        sh = m.get("saatlik_ny") or {}
        saatler = sorted(int(h) for h in sh)
        fig.add_trace(go.Scatter(x=saatler, y=[sh[str(h)]["medyan"] for h in saatler], mode="lines+markers",
                                 name=PARITE.get(c, c), line=dict(color=RENK.get(c, GRI), width=1.6), marker=dict(size=4),
                                 hovertext=[f"NY {h:02d}:00 · medyan {vir(sh[str(h)]['medyan'], 1)} pip · p95 "
                                            f"{vir(sh[str(h)]['p95'], 1)} pip" for h in saatler],
                                 hoverinfo="text"), 1, 1)
        dv = m.get("devir_profili_medyan_pip") or {}
        dk = sorted(int(x) for x in dv)
        fig.add_trace(go.Scatter(x=dk, y=[dv[str(x)] for x in dk], mode="lines+markers", showlegend=False,
                                 line=dict(color=RENK.get(c, GRI), width=1.6), marker=dict(size=4),
                                 hovertext=[f"{_et_dk(x, sinir)}–{_et_dk(x + 5, sinir)} New York · "
                                            f"{vir(dv[str(x)], 1)} pip ({PARITE.get(c, c)})" for x in dk],
                                 hoverinfo="text"), 2, 1)
    fig.add_vline(x=_saat_dk(gun_sonu) - _saat_dk(sinir), line=dict(color=CLARET, width=1, dash="dash"), row=2, col=1)
    fig.update_xaxes(dtick=3, title_text="New York saati", row=1, col=1)
    fig.update_xaxes(dtick=10, title_text=f"New York {sinir}'den dakika (dilimin başı)", row=2, col=1)
    fig.update_yaxes(title_text="pip", row=1, col=1)
    fig.update_yaxes(title_text="pip", row=2, col=1)
    bas = baslik_koy(fig, "Makas: gün içinde ve devir dakikalarında",
                     [f"Dukascopy 1 dk bid/ask, {so.tarih(o['kunye']['baslangic'])}–{so.tarih(o['kunye']['bitis'])} · "
                      "dakika kapanışlarında ask − bid",
                      "TSİ = New York + 7 saat (ABD yaz saati) ya da + 8 saat (ABD kış saati)",
                      "Alt panel: her nokta beş dakikalık bir dilimin medyan makası · kırmızı kesikli: pozisyonların "
                      f"kapandığı New York {gun_sonu} dilimi (TSİ {_ny_tsi(gun_sonu)})"])
    so._yaz(fig, "veri-makas.html", yukseklik(bas, 700))


# ─────────────────────────────────────────────────────── ortak: haber
SINAMA_AD = (("dogrulandi", "doğrulandı"), ("sessiz", "sessiz"), ("celiski", "çelişki"),
             ("degerlendirilemedi", "değerlendirilemedi"))


def _patika_saat_notu(o: dict, olay: str) -> str:
    """Patika figürünün saat notu, olayın KENDİ ölçüsünden: saatin kaynağı (tarih tarih · kuraldan, olay sayısıyla) ve
    fiyat sınamasının sonucu. Basın toplantıları fiyattan sınanmaz (konuşma tek dakikada sıçrama yapmaz)."""
    t = o.get("takvim") or {}
    sk = ((t.get("sayim") or {}).get(olay) or {}).get("saat_kaynagi") or {}
    kay = " · ".join(x for x in ((f"tarih tarih ({sk['tarih']})" if sk.get("tarih") else ""),
                                 (f"kuraldan ({sk['kural']})" if sk.get("kural") else "")) if x) or "—"
    oz = (((t.get("sinama") or {}).get("ozet")) or {}).get(olay) or {}
    sin = (" · ".join(f"{oz[k]} {ad}" for k, ad in SINAMA_AD if oz.get(k)) if not oz.get("basin_bilgi")
           else "fiyatla sınanmadı (basın toplantısı)") or "—"
    return f"Saatin kaynağı: {kay} · fiyat sınaması: {sin}"


def _dk(x: int) -> str:
    """Olaydan dakika, işaretli (eksi U+2212)."""
    return f"{'+' if x > 0 else ('−' if x < 0 else '')}{abs(x)} dk"


#: Patikaya girmeyen olayın sebebi (strat_haber.patika `dislanan`); ders metnindeki yazımla aynı anlam
#: (ders_motor.NEDEN_OLCU_DISI), figüre sığacak kısalıkta. "tatil ya da ATR yok", aynı olay aynı paritede devam
#: tablosundan da günlük ATR'si olmadığı için düştüyse ölçülmüş sebebiyle yazılır (ders_motor._olcu_disi_kayitlar).
PATIKA_NEDEN = {"tatil_ya_da_atr_yok": "tatil günü ya da günlük ATR yok", "gunluk_atr_yok": "günlük ATR yok",
                "pencerede_fiyat_yok": "olay çevresinde fiyatı olmayan dakika var"}


def _patika_dislanan(o: dict, olay: str, sira: list[str]) -> str:
    """Patikaya girmeyen olaylar, tarih ve sebep birlikte; aynı tarih aynı sebeple bütün paritelerde düştüyse parite
    sayısıyla, yoksa pariteleriyle. Lejanttaki olay sayısı ile takvimin sayısı arasındaki fark buradan okunur."""
    hc = (o.get("haber") or {}).get("cift") or {}
    hs = (o.get("kunye") or {}).get("haber_sabit") or {}
    yon_dk = int(hs.get("patika_yon_sn") or 300) // 60
    atr_var = {(e["olay"], e["tarih"], c) for e in (((o.get("haber") or {}).get("olcu_disi") or {}).get("devam_atr") or [])
               for c in (e.get("parite") or {})}
    grup: dict = {}
    eslenen = [c for c in sira if ((hc[c].get("patika") or {}).get(olay))]
    for c in eslenen:
        for d in (hc[c]["patika"][olay].get("dislanan") or []):
            n = d["neden"]
            if n == "tatil_ya_da_atr_yok" and (olay, d["tarih"], c) in atr_var:
                n = "gunluk_atr_yok"
            grup.setdefault((d["tarih"], n), []).append(c)
    if not grup:
        return ""
    parca = []
    for (t, n), cs in sorted(grup.items()):
        neden = (f"ilk {_sayi_ad(yon_dk)} dakikada fiyat değişmedi, yön yok" if n == "ilk_bes_dakikada_yon_yok"
                 else PATIKA_NEDEN.get(n, n))
        kim = (f"{_sayi_ad(len(cs))} parite" if len(cs) == len(eslenen) and len(cs) > 1
               else ", ".join(PARITE.get(c, c) for c in cs))
        parca.append(f"{so.tarih(t)} ({kim}: {neden})")
    return "Çizilmeyen: " + " · ".join(parca)


def haber_patika(o: dict) -> None:
    hc = (o.get("haber") or {}).get("cift") or {}
    hs = o["kunye"]["haber_sabit"]
    yon_dk = int(hs["patika_yon_sn"]) // 60
    atr_gun = int(hs["atr_gun"])
    sira = [c for c in PARITE if c in hc] + [c for c in hc if c not in PARITE]   # künye sırası (öbür figürlerle aynı)
    olaylar = sorted({e for h in hc.values() for e in (h.get("patika") or {})})
    for olay in olaylar:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1,
                            subplot_titles=(f"İlk {yon_dk} dakika yukarı kapanan olaylar",
                                            f"İlk {yon_dk} dakika aşağı kapanan olaylar"))
        for c in sira:
            pt = (hc[c].get("patika") or {}).get(olay)
            if not pt:
                continue
            nler = {yon: (pt.get(yon) or {}).get("n") for yon in ("yukari", "asagi")}
            ad_ = f"{PARITE.get(c, c)} (yukarı {vir(nler['yukari'] or 0, 0)} · aşağı {vir(nler['asagi'] or 0, 0)})"
            for j, yon in enumerate(("yukari", "asagi"), start=1):
                d = pt.get(yon)
                if not d:
                    continue
                tau = pt["tau"]
                fig.add_trace(go.Scatter(x=tau + tau[::-1], y=[100 * x for x in d["ust"]] + [100 * x for x in d["alt"][::-1]],
                                         fill="toself", fillcolor=RENK.get(c, GRI) + "22",
                                         line=dict(width=0), hoverinfo="skip", showlegend=False), j, 1)
                fig.add_trace(go.Scatter(x=tau, y=[100 * x for x in d["ort"]], mode="lines",
                                         name=ad_, showlegend=(j == 1), legendgroup=c,
                                         line=dict(color=RENK.get(c, GRI), width=1.6),
                                         hovertext=[f"{_dk(int(tt))}: {so.yuzde(100 * x, 1)} ATR · {PARITE.get(c, c)} · "
                                                    f"{vir(d['n'], 0)} olay" for tt, x in zip(tau, d["ort"])],
                                         hoverinfo="text"), j, 1)
        if not fig.data:
            continue
        for j in (1, 2):
            fig.add_vline(x=0, line=dict(color=MUREKKEP, width=0.9), row=j, col=1)
            fig.add_vline(x=yon_dk, line=dict(color=GRI, width=0.9, dash="dot"), row=j, col=1)
            fig.add_hline(y=0, line=dict(color=GRI, width=0.8), row=j, col=1)
            fig.update_yaxes(title_text="% günlük ATR", row=j, col=1)
        fig.update_xaxes(title_text="olaydan dakika", row=2, col=1)
        alt = [f"Olay anındaki orta fiyattan değişim, önceki {atr_gun} günün ATR'sine bölünmüş · ilk {yon_dk} "
               "dakikanın yönüne göre iki küme; lejantta iki kümenin olay sayısı",
               f"Gölge: ortalamanın %95 aralığı · noktalı çizgi: ilk {yon_dk} dakikanın sonu",
               _patika_saat_notu(o, olay)]
        dis_ = _patika_dislanan(o, olay, sira)
        if dis_:
            alt.append(dis_)
        bas = baslik_koy(fig, f"Ortalama fiyat patikası — {adlar.OLAY.get(olay, olay)}", alt)
        so._yaz(fig, f"haber-patika-{olay.lower().replace('_', '-')}.html", yukseklik(bas, 600))


def haber_fomc(o: dict) -> None:
    hc = (o.get("haber") or {}).get("cift") or {}
    sira = [c for c in PARITE if c in hc] + [c for c in hc if c not in PARITE]
    hs = o["kunye"]["haber_sabit"]
    atr_gun = int(hs["atr_gun"])
    basin_dk = int(hs["fomc_basin_sn"][0]) // 60
    toplanti, parite, nokta = set(), 0, 0
    for c in sira:
        st = (hc[c].get("fomc") or {}).get("satir") or []
        if st:
            parite += 1
            nokta += len(st)
            toplanti |= {r["tarih"] for r in st}
    fig = make_subplots(rows=1, cols=1, subplot_titles=(
        f"Her nokta: bir toplantı, bir parite<br>({vir(len(toplanti), 0)} toplantı, {vir(parite, 0)} parite, "
        f"{vir(nokta, 0)} nokta)",))
    for c in sira:
        st = (hc[c].get("fomc") or {}).get("satir") or []
        if not st:
            continue
        fig.add_trace(go.Scatter(x=[100 * r["karar_atr"] for r in st], y=[100 * r["basin_60_atr"] for r in st],
                                 mode="markers", name=PARITE.get(c, c), marker=dict(size=7, color=RENK.get(c, GRI), opacity=0.8),
                                 hovertext=[f"{so.tarih(r['tarih'])} · {PARITE.get(c, c)}: karar "
                                            f"{so.yuzde(100 * r['karar_atr'], 1)} · basın {so.yuzde(100 * r['basin_60_atr'], 1)} "
                                            "ATR" for r in st], hoverinfo="text"), 1, 1)
    if not fig.data:          # ölçülmemiş figür yazılmaz: boş eksenler "veri yok" demez, "sonuç yok" der
        return
    fig.add_hline(y=0, line=dict(color=GRI, width=0.8))
    fig.add_vline(x=0, line=dict(color=GRI, width=0.8))
    # Eksen başlığı x'te yok (ev stilinin alt lejantına biniyordu); eksenlerin tanımı alt yazıda.
    fig.update_yaxes(title_text="basın (% günlük ATR)")
    # Hareketi sıfır olan nokta eksenin üstündedir: dönüş oranının paydasına girmez (ders_motor.blok_fomc_payda aynı
    # toplantıları sayar), korelasyona girer. Veriden; elle yazılmaz.
    sifir = []
    for c in sira:
        for r in (hc[c].get("fomc") or {}).get("satir") or []:
            kz, bz = r.get("karar_atr") == 0, r.get("basin_60_atr") == 0
            if not (kz or bz):
                continue
            ne = " ve ".join(x for x, v in (("kararın ilk yarım saatinde", kz),
                                            ("basın toplantısının ilk saatinde", bz)) if v)
            yer = "orijinde" if (kz and bz) else ("x = 0 çizgisinde" if kz else "y = 0 çizgisinde")
            sifir.append(f"{PARITE.get(c, c)}'de {so.tarih(r['tarih'])} toplantısında {ne} hareket sıfır: nokta {yer}, "
                         "dönüş oranına girmez")
    bas_bit = f"{14 + (30 + basin_dk) // 60:02d}:{(30 + basin_dk) % 60:02d}"
    alt = [f"x: karar, New York 14:00 → 14:30 · y: basın toplantısı, 14:30 → {bas_bit} · ikisi orta fiyattan, önceki "
           f"{atr_gun} günün ATR'sinin yüzdesi",
           "Sol üst ve sağ alt çeyrek: basın toplantısı karara verilen tepkiyi TERSİNE çevirdi",
           f"New York 14:00 → 14:30 → {bas_bit} = "
           f"{adlar.tsi_yaz(['New York 14:00', 'New York 14:30', f'New York {bas_bit}'], '→')}"]
    alt += sifir
    bas = baslik_koy(fig, "FOMC: kararın ilk yarım saati ve basın toplantısının ilk saati", alt)
    so._yaz(fig, "haber-fomc.html", yukseklik(bas, 470))


# ─────────────────────────────────────────────────────── ortak: dokuzuncu ders (neden başarısız)
#: Kaybın bileşenleri: parite renkleri yalnız paritelere ayrıldığı için bileşenler kendi tonlarını taşır (yön payı
#: koyu camgöbeği, zamanlama payı mor, maliyetin ölçülen makası koyu, varsayılan kayması açık gri).
BILESEN_RENK = {"y": SECILEN_RENK, "z": "#6b4f8a", "c_makas": "#3a3a3a", "c_kayma": "#b8b3a8"}


def _bs(o: dict) -> dict:
    """Dokuzuncu dersin ölçüleri (ders_olcum → basarisiz.bolum); yoksa çizim DÜŞER: boş figür "sonuç yok" der."""
    b = o.get("basarisiz")
    if not b:
        raise SystemExit("ölçümde dokuzuncu dersin kaydı yok (basarisiz)")
    return b


def _kural_ad(o: dict, b: str, stopsuz: bool = False) -> str:
    """Kuralın figür adı; R birimi stop uzaklığı olmayan kural ‡ ile (karsilastirma figürüyle aynı işaret)."""
    return adlar.BIRIM[b][1] + (" ‡" if stopsuz and ((o["birim"][b].get("varsayilan") or {}).get("stop_turu")) == "yok"
                                else "")


def _stopsuz_notu(o: dict, kurallar) -> list[str]:
    s = [b for b in kurallar if ((o["birim"][b].get("varsayilan") or {}).get("stop_turu")) == "yok"]
    return (["‡ Stopsuz kural: R girişteki ATR(14), bir risk değil ölçek birimi; öbür kurallarda R stop uzaklığıdır"]
            if s else [])


def _puan(x: float) -> str:
    return _r(100 * x, 1) + " puan"


def neden_basabas(o: dict) -> None:
    """Kural başına isabetin başabaş isabetine uzaklığı, orta fiyattan ve maliyetten sonra (dört paritenin havuzu)."""
    h = _bs(o)["basabas"]["havuz"]["oos"]
    sira = sorted(h, key=lambda b: (h[b]["acik"], b))
    ad = [_kural_ad(o, b) for b in sira]
    fig = make_subplots(rows=1, cols=1, subplot_titles=("İsabet − başabaş isabeti (puan)",))
    for b, a in zip(sira, ad):
        fig.add_trace(go.Scatter(x=[100 * h[b]["brut_acik"], 100 * h[b]["acik"]], y=[a, a], mode="lines",
                                 line=dict(color="#c9c4ba", width=2), showlegend=False, hoverinfo="skip"), 1, 1)
    fig.add_trace(go.Scatter(
        x=[100 * h[b]["brut_acik"] for b in sira], y=ad, mode="markers", name="orta fiyattan (brüt)",
        marker=dict(symbol="circle-open", size=9, color=GRI, line=dict(width=1.6, color=GRI)),
        hovertext=[f"{a}: brüt isabet {so.yuzde(100 * h[b]['brut_isabet'], 1)} · başabaş "
                   f"{so.yuzde(100 * h[b]['brut_pstar'], 1)} · açık {_puan(h[b]['brut_acik'])}" for b, a in zip(sira, ad)],
        hoverinfo="text"), 1, 1)
    fig.add_trace(go.Scatter(
        x=[100 * h[b]["acik"] for b in sira], y=ad, mode="markers", name="maliyetten sonra (net)",
        marker=dict(symbol="circle", size=9, color=[CLARET if h[b]["acik"] < 0 else MAVI for b in sira]),
        hovertext=[f"{a}: isabet {so.yuzde(100 * h[b]['isabet'], 1)} · başabaş {so.yuzde(100 * h[b]['pstar'], 1)} · "
                   f"açık {_puan(h[b]['acik'])} · {vir(h[b]['n'], 0)} işlem" for b, a in zip(sira, ad)],
        hoverinfo="text"), 1, 1)
    fig.add_vline(x=0, line=dict(color=MUREKKEP, width=0.9))
    fig.update_xaxes(title_text="puan")
    bas = baslik_koy(fig, "İsabet başabaş isabetine ne kadar uzak — maliyetten önce ve sonra",
                     [_kunye(o), f"Örneklem dışı ({_dis(o)}), önceden kayıtlı varsayılanlar{_turetilmis_not(o)}; "
                      f"{_sayi_ad(len(PARITE))} paritenin işlemleri birlikte",
                      "Başabaş isabeti p* = |ortalama kayıp| / (ortalama kazanç + |ortalama kayıp|); açık = isabet − p*. "
                      "Sıfırın solundaki kural kaybettirir: beklenti = açık × (ortalama kazanç + |ortalama kayıp|)",
                      "Boş daire: orta fiyattan orta fiyata (brüt) · dolu daire: gerçek makas ve kaymayla (net)"])
    so._yaz(fig, "neden-basabas.html", yukseklik(bas, 90 + 26 * len(sira)))


def neden_anatomi(o: dict) -> None:
    """Kaybın yön, zamanlama ve maliyet payları (ayna işlemle ayrışım), kural başına."""
    a = _bs(o)["ayrisim"]["oos"]
    k = a["kural"]
    sira = sorted(k, key=lambda b: (k[b]["net"], b))
    ad = [_kural_ad(o, b, stopsuz=True) for b in sira]
    fig = make_subplots(rows=1, cols=1, subplot_titles=("R / işlem",))
    parca = (("y", "yön payı", 1), ("z", "zamanlama payı", 1), ("c_makas", "ölçülen makas", -1),
             ("c_kayma", "varsayılan kayma", -1))
    for alan, etiket, isaret in parca:
        fig.add_trace(go.Bar(
            x=[isaret * k[b][alan] for b in sira], y=ad, orientation="h", name=etiket,
            marker=dict(color=BILESEN_RENK[alan], line=dict(width=0)),
            hovertext=[f"{x}: {etiket} {_r(isaret * k[b][alan], 3)} R" for b, x in zip(sira, ad)],
            hoverinfo="text"), 1, 1)
    fig.add_trace(go.Scatter(x=[k[b]["net"] for b in sira], y=ad, mode="markers", name="net = yön + zamanlama − maliyet",
                             marker=dict(symbol="diamond", size=9, color=MUREKKEP, line=dict(width=1, color="white")),
                             hovertext=[f"{x}: net {_r(k[b]['net'], 3)} R · {vir(k[b]['n'], 0)} işlem, "
                                        f"{vir(k[b]['bilesim'], 0)} parite" for b, x in zip(sira, ad)],
                             hoverinfo="text"), 1, 1)
    fig.update_layout(barmode="relative", bargap=0.35)
    fig.add_vline(x=0, line=dict(color=MUREKKEP, width=0.9))
    dis = sorted({x.split(":")[0] for x in a.get("dislanan") or []})
    alt = [_kunye(o), f"Örneklem dışı ({_dis(o)}), önceden kayıtlı varsayılanlar{_turetilmis_not(o)}; kural başına "
           "paritelerin işlem sayısıyla ağırlıklı ortalaması",
           "Ayna işlem: aynı dakikada, aynı stop ve hedef uzaklığıyla TERS yönde açılan işlem. Yön payı = (net − ayna) / 2, "
           "zamanlama payı = (net + ayna) / 2 + maliyet; aynanın maliyeti gerçek işleminkine eşit sayılır",
           "Maliyet iki parça: gerçek bid/ask makası (koyu) ve dolum başına varsayılan kayma (açık)"]
    if dis:
        alt.append("Dışarıda: " + ", ".join(adlar.BIRIM[b][1] for b in dis)
                   + f" (örneklem dışında {vir(int(o['kunye']['uygulama_esik']['rastgele']), 0)} işlemden az; ayna kurulmaz)")
    bas = baslik_koy(fig, "Kaybın anatomisi — yön, zamanlama ve maliyet", alt + _stopsuz_notu(o, sira))
    so._yaz(fig, "neden-anatomi.html", yukseklik(bas, 120 + 26 * len(sira)))


def neden_olcek(o: dict) -> None:
    """R büyüklüğüne göre üçte birlikler: maliyetin R payı R'yle küçülür, brüt büyümez."""
    u = _bs(o)["olcek"]["ucte_bir"]["oos"]
    ad = [f"{s}<br>R ≈ {vir(r, 1)} pip" for s, r in zip(("dar", "orta", "geniş"), u["R"])]
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.2, row_heights=[0.6, 0.4],
                        subplot_titles=("R / işlem (bileşimlerin medyanı)", "pip / işlem"))
    for alan, etiket, renk in (("brut", "brüt", SECILEN_RENK), ("maliyet", "maliyet", "#8a8a8a"),
                               ("net", "net", MUREKKEP)):
        fig.add_trace(go.Bar(x=ad, y=u[alan], name=etiket, marker=dict(color=renk),
                             hovertext=[f"{etiket}: {_r(v, 3)} R" for v in u[alan]], hoverinfo="text"), 1, 1)
    fig.add_trace(go.Bar(x=ad, y=u["maliyet_pip"], name="maliyet (pip)", marker=dict(color="#c9c4ba"),
                         hovertext=[f"gidiş-dönüş maliyeti {vir(v, 2)} pip" for v in u["maliyet_pip"]],
                         hoverinfo="text"), 2, 1)
    fig.update_layout(barmode="group", bargap=0.3)
    fig.add_hline(y=0, line=dict(color=MUREKKEP, width=0.8), row=1, col=1)
    fig.update_yaxes(title_text="R", row=1, col=1)
    fig.update_yaxes(title_text="pip", row=2, col=1)
    bas = baslik_koy(fig, "Ölçek — R büyüdükçe maliyetin payı küçülür, brüt büyümez",
                     [_kunye(o), f"Örneklem dışı ({_dis(o)}); her bileşimin işlemleri kendi R'sine göre üç eşit dilime "
                      f"bölündü (pencerede en az {vir(u['asgari'], 0)} işlemli {vir(u['bilesim'], 0)} bileşim)",
                      "Çubuk: bileşimlerin medyanı; medyanlar toplanmaz (net medyanı brüt medyanı eksi maliyet medyanı "
                      "değildir) · R: girişten stopa planlanan risk, stopsuz kurallarda girişteki ATR(14)",
                      "Alt panel: aynı dilimlerin gidiş-dönüş maliyeti pip olarak; pip maliyeti hemen hemen sabit kalır, "
                      "R'nin pip karşılığı büyür"])
    so._yaz(fig, "neden-olcek.html", yukseklik(bas, 560))


def neden_kenar(o: dict) -> None:
    """Örneklem içinden dışına ne taşındı: maliyet neredeyse birebir, brüt dağınık (bileşim başına)."""
    ken = _bs(o)["kenar"]
    nokta = ken["nokta"]
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.17,
                        subplot_titles=("Maliyet (R / işlem)", "Brüt (R / işlem)"))
    for j, alan in ((1, "maliyet"), (2, "brut")):
        xs = [p[f"{alan}_is"] for p in nokta] + [p[f"{alan}_oos"] for p in nokta]
        lo, hi = min(xs), max(xs)
        fig.add_trace(go.Scatter(x=[lo, hi], y=[lo, hi], mode="lines", line=dict(color=GRI, width=1, dash="dot"),
                                 showlegend=False, hoverinfo="skip"), j, 1)
        for c in PARITE:
            for disari in (False, True):
                ps = [p for p in nokta if p["cift"] == c and p["dislanan"] == disari]
                if not ps:
                    continue
                fig.add_trace(go.Scatter(
                    x=[p[f"{alan}_is"] for p in ps], y=[p[f"{alan}_oos"] for p in ps], mode="markers",
                    name=PARITE[c], legendgroup=c, showlegend=(j == 1 and not disari),
                    marker=dict(size=7, color=RENK[c], symbol="circle-open" if disari else "circle",
                                line=dict(width=1.4, color=RENK[c]), opacity=0.85),
                    hovertext=[f"{adlar.BIRIM[p['kural']][1]} · {PARITE[c]}: örneklem içi {_r(p[f'{alan}_is'], 3)} → "
                               f"dışı {_r(p[f'{alan}_oos'], 3)} R · dışında {vir(p['n_oos'], 0)} işlem"
                               for p in ps], hoverinfo="text"), j, 1)
        fig.add_hline(y=0, line=dict(color=GRI, width=0.8), row=j, col=1)
        fig.add_vline(x=0, line=dict(color=GRI, width=0.8), row=j, col=1)
        fig.update_xaxes(title_text=f"örneklem içi ({_ic(o)})", row=j, col=1)
        fig.update_yaxes(title_text=f"dışı ({_dis(o)})", row=j, col=1)
    g, s = ken["guvenilirlik"], ken["sira_bilesim"]
    dis = sorted({x.split(":")[0] for x in ken.get("dislanan") or []})
    alt = [_kunye(o), f"Her nokta bir kural–parite bileşimi, önceden kayıtlı varsayılanlar{_turetilmis_not(o)}; noktalı "
           "çizgi: iki pencerede aynı değer",
           f"Sıra korelasyonu (bileşimler): maliyet {vir(s['maliyet'], 2)} · brüt {vir(s['brut'], 2)}; brüt yayılımın "
           f"sinyal payı (güvenilirlik) örneklem içinde {vir(g['is'], 2)}, dışında {vir(g['oos'], 2)}"]
    if dis:
        alt.append("Boş daire: " + ", ".join(adlar.BIRIM[b][1] for b in dis)
                   + f" (örneklem dışında {vir(int(o['kunye']['uygulama_esik']['rastgele']), 0)} işlemden az; "
                     "korelasyon ve güvenilirliğe girmez)")
    bas = baslik_koy(fig, "Örneklemden örnekleme ne taşındı — maliyet evet, brüt hayır", alt)
    so._yaz(fig, "neden-kenar.html", yukseklik(bas, 760))


def neden_sans(o: dict) -> None:
    """Kenarsız bir dünyada örneklem dışında net artı çıkan bileşim sayısının dağılımı ve gözlenen sayı."""
    s = _bs(o)["sans"]
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.2,
                        subplot_titles=("Önceden kayıtlı varsayılanlar", "Örneklem içinde seçilen kombinasyonlar"))
    for j, an in ((1, "varsayilan"), (2, "secilen")):
        v = s[an]
        d = v["dagilim"]
        son = max([i for i, p in enumerate(d) if p >= 1e-3] + [v["gozlenen"]]) + 1
        d = d[:son + 1]
        k = list(range(len(d)))
        fig.add_trace(go.Bar(x=k, y=[100 * p for p in d], marker=dict(color=[CLARET if i == v["gozlenen"] else "#c9c4ba"
                                                                              for i in k]),
                             showlegend=False,
                             hovertext=[f"{i} bileşim: olasılık {so.yuzde(100 * p, 1)}" for i, p in zip(k, d)],
                             hoverinfo="text"), j, 1)
        fig.add_vline(x=v["beklenen"], line=dict(color=MUREKKEP, width=1, dash="dot"), row=j, col=1)
        fig.add_annotation(x=v["gozlenen"], y=100 * d[v["gozlenen"]], text=f"gözlenen {v['gozlenen']}", showarrow=True,
                           arrowhead=0, ax=30, ay=-24, font=dict(size=11, color=CLARET), row=j, col=1)
        fig.update_yaxes(title_text="olasılık (%)", row=j, col=1)
        fig.update_xaxes(range=[-0.6, len(d) - 0.4], row=j, col=1)
    fig.update_xaxes(title_text="örneklem dışında net artı çıkan bileşim sayısı", row=2, col=1)
    v, w = s["varsayilan"], s["secilen"]
    bas = baslik_koy(fig, "Şansın beklediği — kenarsız dünyada kaç bileşim artı çıkardı",
                     [_kunye(o), f"Örneklem dışı ({_dis(o)}): brüt sonuç sıfır olsaydı her bileşimin artı çıkma olasılığı "
                      "Φ(−maliyet / standart hata); sayı bu olasılıkların toplamı gibi dağılır",
                      f"Noktalı çizgi: beklenen sayı (varsayılanlarda {vir(v['beklenen'], 1)}, seçilenlerde "
                      f"{vir(w['beklenen'], 1)}) · kırmızı çubuk: gözlenen ({v['gozlenen']} ve {w['gozlenen']})",
                      "Bileşimler aynı günleri paylaşır: beklenen sayı bundan etkilenmez, dağılım genişler"])
    so._yaz(fig, "neden-sans.html", yukseklik(bas, 600))


def neden_maliyet_esigi(o: dict) -> None:
    """Kuralın başabaş gidiş-dönüş maliyeti (pip) ile ödediği maliyet, kural başına."""
    h = _bs(o)["esik"]["havuz"]["oos"]
    sira = sorted(h, key=lambda b: (h[b]["cstar"], b))
    ad = [_kural_ad(o, b) for b in sira]
    # Eksen, aralığı öbürlerinin dört katından geniş olan kuralın (az işlemli) aralığına göre kurulmaz: o aralık eksenin
    # dışına taşar ve adıyla alt yazıda yazılır. Noktaların hepsi (c* ve ödenen) eksenin içindedir.
    gen = sorted(h[b]["ust"] - h[b]["alt"] for b in sira)
    tasan = [b for b in sira if h[b]["ust"] - h[b]["alt"] > 4 * gen[len(gen) // 2]]
    uclar = [v for b in sira for v in (h[b]["cstar"], h[b]["odenen"])]
    uclar += [v for b in sira if b not in tasan for v in (h[b]["alt"], h[b]["ust"])]
    pay = 0.05 * (max(uclar) - min(uclar))
    fig = make_subplots(rows=1, cols=1, subplot_titles=("pip / işlem (gidiş-dönüş)",))
    fig.update_xaxes(range=[min(uclar) - pay, max(uclar) + pay])
    fig.add_trace(go.Scatter(
        x=[h[b]["cstar"] for b in sira], y=ad, mode="markers", name="başabaş maliyeti c* ve %95 aralığı",
        marker=dict(symbol="diamond", size=9, color=MUREKKEP),
        error_x=dict(type="data", symmetric=False, array=[h[b]["ust"] - h[b]["cstar"] for b in sira],
                     arrayminus=[h[b]["cstar"] - h[b]["alt"] for b in sira], color=GRI, thickness=1.2),
        hovertext=[f"{a}: c* {vir(h[b]['cstar'], 2)} pip · %95 [{vir(h[b]['alt'], 2)}, {vir(h[b]['ust'], 2)}] · ödenen "
                   f"{vir(h[b]['odenen'], 2)} pip" for b, a in zip(sira, ad)], hoverinfo="text"), 1, 1)
    fig.add_trace(go.Scatter(x=[h[b]["odenen"] for b in sira], y=ad, mode="markers", name="ödenen maliyet",
                             marker=dict(symbol="x-thin", size=10, color=CLARET, line=dict(width=2, color=CLARET)),
                             hovertext=[f"{a}: ödenen {vir(h[b]['odenen'], 2)} pip" for b, a in zip(sira, ad)],
                             hoverinfo="text"), 1, 1)
    fig.add_vline(x=0, line=dict(color=MUREKKEP, width=0.9))
    bas = baslik_koy(fig, "Bir kural ne kadar maliyet kaldırır — başabaş maliyeti ve ödenen",
                     [_kunye(o), f"Örneklem dışı ({_dis(o)}), önceden kayıtlı varsayılanlar{_turetilmis_not(o)}; "
                      f"{_sayi_ad(len(PARITE))} paritenin işlemleri birlikte",
                      "c* = ortalama brüt R / ortalama (1 / R'nin pip karşılığı): işlem başına sabit bir gidiş-dönüş maliyeti "
                      "c* olsaydı net R sıfır olurdu (işlemler maliyetle değişmez sayılır)",
                      "Aralık: brüt sonucun önceden kayıtlı bootstrap aralığından · çarpı: kuralın ödediği maliyet "
                      "(makas + kayma); c* ödenenin solundaysa kural kaybettirir"]
                     + ([" · ".join(f"{_kural_ad(o, b)}: aralık {vir(h[b]['alt'], 1)} / {vir(h[b]['ust'], 1)} pip, eksenin "
                                    f"dışına taşar ({vir(h[b]['n'], 0)} işlem)" for b in tasan)] if tasan else []))
    so._yaz(fig, "neden-maliyet-esigi.html", yukseklik(bas, 90 + 26 * len(sira)))


def neden_ay_sonu(o: dict) -> None:
    """Fiksing momentumunun ay sonu alt kümesi: parite × pencere (bugünkü ve eski ay sonu tanımı), GBP/USD yıl yıl."""
    a = _bs(o)["ay_sonu"]
    # Eski tanımın kaydı ailenin bütün üyelerini taşır (fiksing dönüşü dahil): anahtar kural + parite + biçimdir.
    eski = {(u["birim"], u["cift"], u["kim"]): u
            for u in (((o.get("karsi_olgu") or {}).get("ay_sonu_alt_kume") or {}).get("uye") or []) if u.get("ay_sonu")}
    sira = [c for c in PARITE if c in a["parite"]]
    pen = (("is", f"{_ic(o)}"), ("oos", f"{_dis(o)}"))
    satir = [(c, d, f"{PARITE[c]} · {et}") for c in sira for d, et in pen]
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.16, row_heights=[0.58, 0.42],
                        subplot_titles=("Ay sonu · net R ve %95 aralığı",
                                        f"{PARITE.get('GBPUSD', 'GBP/USD')} · yıl yıl net R"))
    y = [s[2] for s in satir][::-1]
    v = {s[2]: a["parite"][s[0]][s[1]]["ay_sonu"] for s in satir}

    def sinirda(k):
        # aralığın sıfıra yakın ucu (alt ya da üst) işaretini bootstrap tohumuna bağlı taşıyorsa (basarisiz._ay_ozeti)
        return any(s_.get("sinirda") for s_ in (v[k].get("sinir") or {}).values())
    fig.add_trace(go.Scatter(
        x=[v[k]["net"] for k in y], y=y, mode="markers", name="net (bugünkü tanım: ayın son Londra iş günü)",
        marker=dict(size=[11 if sinirda(k) else 9 for k in y],
                    symbol=["diamond" if sinirda(k) else "circle" for k in y],
                    color=[MAVI if v[k]["alt"] > 0 else (MUREKKEP if v[k]["net"] > 0 else CLARET) for k in y]),
        error_x=dict(type="data", symmetric=False, array=[v[k]["ust"] - v[k]["net"] for k in y],
                     arrayminus=[v[k]["net"] - v[k]["alt"] for k in y], color=GRI, thickness=1.2),
        hovertext=[f"{k}: net {_r(v[k]['net'], 3)} R · %95 [{_r(v[k]['alt'], 3)}, {_r(v[k]['ust'], 3)}] · brüt "
                   f"{_r(v[k]['brut'], 3)} R · {vir(v[k]['n'], 0)} ay sonu"
                   + "".join(f" · {'alt' if uc == 'alt' else 'üst'} uç sınırda (ucun artı çıktığı tohumların payı "
                             f"%{vir(100 * s_['pozitif_pay'], 1)})"
                             for uc, s_ in sorted((v[k].get("sinir") or {}).items()) if s_.get("sinirda"))
                   for k in y], hoverinfo="text"), 1, 1)
    fig.add_trace(go.Scatter(x=[v[k]["brut"] for k in y], y=y, mode="markers", name="brüt (orta fiyattan)",
                             marker=dict(symbol="circle-open", size=9, color=GRI, line=dict(width=1.5, color=GRI)),
                             hoverinfo="skip"), 1, 1)
    ex, ey = [], []
    for c, d, et in satir:
        u = eski.get(("fiks_momentum", c, "varsayilan"))
        if u:
            ex.append(u["ay_sonu"][d]["beklenti_r"])
            ey.append(et)
    if ex:
        fig.add_trace(go.Scatter(x=ex, y=ey, mode="markers", name="net, eski tanımla (ayın son hafta içi günü)",
                                 marker=dict(symbol="x-thin", size=10, color=TURUNCU, line=dict(width=2, color=TURUNCU)),
                                 hovertext=[f"{k}: eski tanımla net {_r(x, 3)} R" for x, k in zip(ex, ey)],
                                 hoverinfo="text"), 1, 1)
    fig.add_vline(x=0, line=dict(color=MUREKKEP, width=0.9), row=1, col=1)
    gy = a["parite"].get("GBPUSD", {}).get("yil") or {}
    yillar = sorted(gy)
    fig.add_trace(go.Bar(x=yillar, y=[gy[k] for k in yillar], showlegend=False,
                         marker=dict(color=[RENK.get("GBPUSD", CLARET) if gy[k] > 0 else "#c9c4ba" for k in yillar]),
                         hovertext=[f"{k}: {_r(gy[k], 3)} R" for k in yillar], hoverinfo="text"), 2, 1)
    fig.add_hline(y=0, line=dict(color=MUREKKEP, width=0.8), row=2, col=1)
    fig.update_xaxes(type="category", row=2, col=1)
    k_ = o["kunye"]
    bas = baslik_koy(fig, "Ay sonu fiksingi — tek aday, dört paritede",
                     [_kunye(o), "Fiksing momentumu, önceden kayıtlı varsayılan; yalnız ayın son Londra iş günündeki işlemler "
                      "(ayda bir işlem) · aralık: önceden kayıtlı bootstrap",
                      "Mavi: aralığın alt ucu sıfırın üstünde · siyah: net artı, aralık sıfırı kapsıyor · kırmızı: net eksi",
                      "Elmas: aralığın sıfıra yakın ucu sınırda; işareti bootstrap tohumuna bağlı (renk önceden kayıtlı "
                      "yordamın ucundan)",
                      f"Çarpı: ay sonunun eski tanımı (ayın son hafta içi günü); iki tanım İngiltere tatiline denk gelen "
                      f"{vir(len(k_.get('ay_sonu_kayan') or []), 0)} ayda ayrışır",
                      f"Alt panel: {so.tarih(k_['baslangic'])}–{so.tarih(k_['bitis'])}; son yıl eksik"])
    so._yaz(fig, "neden-ay-sonu.html", yukseklik(bas, 640))


def neden_guc(o: dict) -> None:
    """İleriye dönük bir sınamanın gücü: net etkiye göre gereken süre (ayda bir işlem), iki düzeyde."""
    g = _bs(o)["guc"]
    e = g["egri"]
    k_ = o["kunye"]
    gb = g["gbp"]
    aile = _bs(o)["ay_sonu"]["aile"]["n"]
    fig = make_subplots(rows=1, cols=1, subplot_titles=("Gereken süre (yıl)",))
    fig.add_trace(go.Scatter(x=[p["mu"] for p in e], y=[p["yil"] for p in e], mode="lines", name="tek yönlü %5 düzey",
                             line=dict(color=MUREKKEP, width=2),
                             hovertext=[f"etki {_r(p['mu'], 3)} R: {vir(p['yil'], 1)} yıl" for p in e], hoverinfo="text"),
                  1, 1)
    fig.add_trace(go.Scatter(x=[p["mu"] for p in e], y=[p["yil_esik"] for p in e], mode="lines",
                             name=f"aile düzeyi (%5 / {vir(aile, 0)}, iki yönlü)",
                             line=dict(color=MUREKKEP, width=1.4, dash="dash"),
                             hovertext=[f"etki {_r(p['mu'], 3)} R: {vir(p['yil_esik'], 1)} yıl" for p in e],
                             hoverinfo="text"), 1, 1)
    # Noktalar lejantta adlarıyla (ölçülen ile büzülmüş etki birbirine çok yakın: yazı etiketi eğriye ve birbirine biner).
    ad = (("gozlenen", "ölçülen etki", "circle"), ("buzulmus", "büzülmüş etki", "square"),
          ("yari", "yarı etki", "diamond"))
    for k, a, sembol in ad:
        v = gb["senaryo"].get(k)
        if not v:
            continue
        fig.add_trace(go.Scatter(x=[v["mu"]], y=[v["yil"]], mode="markers",
                                 name=f"{a}: {vir(v['mu'], 2)} R → {vir(v['yil'], 1)} yıl",
                                 marker=dict(size=9, symbol=sembol, color=RENK.get("GBPUSD", CLARET),
                                             line=dict(width=1, color="white")),
                                 hovertext=[f"{a}: {_r(v['mu'], 3)} R → {vir(v['yil'], 1)} yıl (aile düzeyinde "
                                            f"{vir(v['yil_esik'], 1)} yıl)"], hoverinfo="text"), 1, 1)
    seri = (datetime.fromisoformat(k_["bitis"]) - datetime.fromisoformat(k_["baslangic"])).days / 365.25
    fig.add_hline(y=seri, line=dict(color=GRI, width=1, dash="dot"))
    # Kısa etiket solda, çizginin altında: o bölgede eğri yok, noktalar sağda (uzun yazı noktalara biniyordu).
    fig.add_annotation(x=e[0]["mu"], y=math.log10(seri), text=f"seri: {vir(seri, 1)} yıl",
                       showarrow=False, xanchor="left", yanchor="top", font=dict(size=11, color=GRI))
    cizgi = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]
    fig.update_yaxes(type="log", tickvals=cizgi, ticktext=[vir(v, 0) for v in cizgi], title_text="yıl")
    # Yatay eksenin başlığı alt yazıda: ev stilinin alt lejantına biniyordu (haber_fomc ile aynı).
    bas = baslik_koy(fig, "Bir etkiyi görmek ne kadar sürer — ayda bir işlemle",
                     [f"{PARITE.get('GBPUSD', 'GBP/USD')} ay sonu fiksingi örneği: ayda bir işlem; işlem başına standart sapma "
                      f"{vir(gb['sd'], 2)} R (bütün dönem) · yatay eksen: gerçek net etki (R / işlem), dikey: logaritmik",
                      "%80 güç: gerçek etki bu büyüklükteyse sınamanın onu sıfırdan ayırma olasılığı %80; n = ((z düzey + "
                      "z güç) × σ / etki)², süre = n / 12",
                      f"Kesikli: {vir(aile, 0)} biçimlik ailenin Bonferroni düzeyi · noktalar: ölçülen etki, ampirik Bayes "
                      "büzülmesinden sonraki etki ve yarıya inmiş etki · noktalı çizgi: bu serinin uzunluğu "
                      f"({so.tarih(k_['baslangic'])}–{so.tarih(k_['bitis'])})"])
    so._yaz(fig, "neden-guc.html", yukseklik(bas, 470))


NEDEN_SEKILLERI = (neden_basabas, neden_anatomi, neden_olcek, neden_kenar, neden_sans, neden_maliyet_esigi,
                   neden_ay_sonu, neden_guc)


def main(argv: list[str]) -> int:
    if go is None:
        print("plotly yok: figürler çizilemez (kapı yolu bundan etkilenmez)")
        return 1
    sorun = so.plotly_js_sina()
    if sorun:
        print(f"✗ {sorun}: figürler çizilmedi")
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
        for f in (karsilastirma, maliyet, rastgele, veri, haber_patika, haber_fomc) + NEDEN_SEKILLERI:
            f(o)
    return so.ev_stili(so.YAZILAN)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
