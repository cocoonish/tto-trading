#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRO DERSİ — Bölüm 10, kur sürücüleri figürleri. Sayılar `veri/olcum.json`dan (b10:
`sekil_surucu_harita`, `sekil_surucu_kayan`, `sekil_usdjpy`; hover ayrıntısı `p10c`).

Şekil numaraları (18–20) başlık ve dosya adı için tek sabitten (`NO`) kurulur.

Sürücü haritası iki panele bölünür (temel sürücüler: faiz farkı ve emtia · risk sürücüleri: VIX,
S&P 500, yuan, dolar sepeti): altı sütun 390 piksellik ekranda hücre başına ~44 piksel bırakır ve
emtia sütununda hücrenin hangi emtia olduğu (Brent, bakır, soya…) yazılamaz. Hücreler çubuk izi
olarak çizilir (Şekil 24'ün, şok × rejim matrisinin kalıbı): ısı haritası çerçeve kalınlığını hücre hücre taşımaz.

Başlık ve alt başlık dar ekrana göre sarılır (Plotly başlığı sarmaz, taşırır): başlık ~50, alt
başlık ~74 karakter — 390 pikselde sığan genişlik (rakamlı satırlar harfli satırlardan geniştir;
ekran görüntüsünde ölçüldü). Sayılara ek getirilmez ("%95'i" yazılmaz): ek sayının okunuşuna göre
değişir, üretici onu bilemez.
"""
from __future__ import annotations

import math
import re

from sekil_ortak import CLARET, GRI, MAVI, MUREKKEP, TURUNCU, go, make_subplots, tarih, vir, _yaz
from sekil_b13 import _OLCEK, _imzali, _olcek_rengi, _sar, _yazi_rengi

NO = {"harita": "18", "kayan": "19", "usdjpy": "20"}
_DOSYA = {"harita": "surucu_haritasi", "kayan": "surucu_kayan", "usdjpy": "usdjpy_faiz_farki"}

BASLIK_EN, ALT_EN, HOVER_EN = 50, 74, 64
DONEM_GOLGE = "rgba(138,138,138,0.13)"
_BOS_KENAR = "#e4dfd5"
_KENAR = "#cfc9bd"
RENK_SINIR = 0.6          # renk ölçeğinin ucu: |korelasyon| ≥ 0,6 tam renk (haritadaki en yüksek değer ~0,54)
_TERS_KALIN = 3.2

# Haritanın panelleri: (kimlik, köşe etiketi, sütunlar). Ölçümde bir panele atanmamış sütun çıkarsa
# çizim DÜŞER: yeni bir sürücü grubu sessizce haritadan kaybolmasın.
_PANELLER = (("temel", "<b>Temel</b><br>sürücüler", ("faiz", "emtia")),
             ("risk", "<b>Risk</b><br>sürücüleri", ("vix", "hisse", "cin", "dolar")))
_SUTUN_KISA = {"faiz": "<b>Faiz farkı</b><br>yerel − ABD", "emtia": "<b>Emtia</b><br>fiyatı",
               "vix": "<b>VIX</b><br>oynaklık", "hisse": "<b>S&P 500</b><br>hisse",
               "cin": "<b>Yuan</b><br>Çin", "dolar": "<b>Dolar</b><br>G10 sepeti"}
_SURUCU_KISA = {"brent": "Brent", "wti": "WTI", "bakir": "bakır", "demir_cevheri": "demir cevheri",
                "altin": "altın", "platin": "platin", "soya": "soya", "abd_reel_10y": "ABD reel faizi",
                "vix": "VIX", "spx": "S&P 500", "cnh": "yuan", "dolar_sepeti": "dolar sepeti"}
_NB = "\u00a0"           # bölünmez boşluk: sarma "en az" ile sayıyı, aralığın iki ucunu ayırmasın
# Para ile sürücünün ayracı: kısa çizgi faiz farkının eksisiyle ("Japon yeni – Japonya − ABD") aynı görünür.
_AYRAC = "\u00a0· "      # bölünmez boşlukla: sarma ayracı satır başına atmasın
_SAYI_AD = {0: "hiçbirinde", 1: "birinde", 2: "ikisinde", 3: "üçünde", 4: "dördünde"}
_SAYI_KOK = {0: "hiçbir", 1: "bir", 2: "iki", 3: "üç", 4: "dört", 5: "beş"}


def _imz(x: float, b: int = 2) -> str:
    """İşaretli sayı; yuvarlanınca sıfır olan değer işaretsiz yazılır ("−0,00" ya da "+0,00" basılmaz)."""
    return vir(0.0, b) if round(x, b) == 0 else _imzali(x, b)


def _dosya(k: str) -> str:
    return f"{NO[k]}_{_DOSYA[k]}.html"


def _baslik(k: str, bulgu: str, alt: list[str]) -> str:
    bas = _sar(f"Şekil {NO[k]} — {bulgu}", BASLIK_EN)
    return bas + "<br><sub>" + "<br>".join(_sar(s, ALT_EN) for s in alt) + "</sub>"


def _ust_pay(baslik: str) -> int:
    """Ev stilinin üst boşluğu (site/tools/plotly_stil.py): 92 + satır başına 26 + üst başlık 26 piksel.
    Figür yüksekliği bu payla kurulur; aksi hâlde ev stili büyüttükçe çizim alanı ezilir."""
    return 92 + 26 * baslik.count("<br>") + 26


def _baslik_yeri(baslik: str) -> dict:
    """Başlık bloğu üstten çapalanır (Şekil 24'ün kalıbı: kendiliğinden yerleşince alt başlık sütun
    başlıklarına binebiliyordu) ve ev stilinin üst payı içinde ORTALANIR: pay satır başına 26 piksel
    büyür, blok satır başına ~19,7 piksel tutar (ekran görüntüsünde ölçüldü); fark üstte bırakılsaydı
    alt başlık ile çizim arasında ~110 piksellik boşluk kalıyordu. 33 piksel: pad 48'de bloğun ölçülen
    üst kenarı; 30 piksel: ilk panelin başlığı ya da sütun başlıkları."""
    satir = baslik.count("<br>") + 1
    kaydir = max(0.0, (_ust_pay(baslik) - 30 - 2 * 33 - 19.7 * satir) / 2)
    return dict(text=baslik, y=1, yref="container", yanchor="top", pad=dict(t=int(48 + kaydir)))


def _para_kisa(k: str) -> str:
    """Satır etiketi dar ekranda sığsın diye ISO kodu (tam ad hover'da); altın adıyla."""
    return {"altin": "Altın"}.get(k, k.upper())


def _surucu_kisa(anahtar: str, ad: str) -> str:
    if anahtar in _SURUCU_KISA:
        return _SURUCU_KISA[anahtar]
    m = re.search(r"_us_(\d+)y$", anahtar)
    return f"{m.group(1)} yıllık fark" if m else ad


def _surucu_orta(ad: str) -> str:
    """Panel başlığı için sürücünün adı: parantez içi açıklama düşer, 'getiri farkı' 'fark' olur."""
    return re.sub(r"\s*\([^)]*\)", "", ad).replace(" getiri farkı", " fark")


def _kayan_asgari(o: dict) -> str | None:
    m = re.search(r"en az (\d+) ortak hafta", o["b10"]["sekil_surucu_kayan"].get("yontem") or "")
    return m.group(1) if m else None


def _donemler(o: dict) -> list[dict]:
    return o["b10"]["p10c"]["donemler"]


def _donem_bantlari(fig, o: dict, satirlar) -> None:
    """Dört alt dönemin ikinci ve dördüncüsü açık gri bant: dönem sınırları her panelde görünür."""
    for i, d in enumerate(_donemler(o)):
        if i % 2 == 1:
            for r in satirlar:
                fig.add_vrect(x0=d["ilk"], x1=d["son"], fillcolor=DONEM_GOLGE, line_width=0, layer="below",
                              row=r, col=1)


def _panel_basliklari(fig, n: int, boyut: float = 12.5) -> None:
    for a in list(fig.layout.annotations)[:n]:
        a.update(x=0, xanchor="left", font=dict(size=boyut, color=MUREKKEP))


# ───────────────────────────────────────────────────────── Şekil: sürücü haritası
def _kisa_donem(et: str) -> str:
    """'2010–2014' → '2010–14' (hover satırı dar ekranda tek satıra sığsın)."""
    return re.sub(r"(\d{4})–\d{2}(\d{2})", r"\1–\2", et)


def _hucre_hover(h: dict, para: str, para_ad: str, c: dict | None, cift: dict, sira: list, pencere: str,
                 sk: str, tam_et: str) -> str:
    """Hücrenin ayrıntısı; `sk` p10c çift kaydında haritanın penceresinin anahtarı (ör. 'siralama_2015_2026')."""
    sat = [f"<b>{para_ad}{_AYRAC}{h['surucu_ad']}</b>"]
    w = (c or {}).get(sk) or {}
    sat.append(f"{pencere} haftalık: korelasyon {_imz(h['kor'])} ({w.get('n', h['n'])} hafta)")
    if w.get("t") is not None:
        sat.append((f"sıra korelasyonu {_imz(w['spearman'])} · " if w.get("spearman") is not None else "")
                   + f"Newey–West t {vir(w['t'], 2)}")
    if w.get("beta") is not None and c:
        sat.append(f"eğim {_imz(w['beta'], 3)}: {c['beta_okur']}")
    satir = f"beklenen işaret: {'artı' if h['beklenen_isaret'] > 0 else 'eksi'}"
    if h["ters"]:
        satir += " — ölçülen işaret bunun tersi"
        if w.get("t") is not None and abs(w["t"]) < 2:
            satir += "; bu pencerede |t| < 2, işaret sıfırdan ayırt edilmiyor"
    sat.append(satir)
    if c:
        t = c["tam"]
        sat.append(f"tam örneklem {tam_et}: {_imz(t['kor'])} (t {vir(t['t'], 2)})")
        nd, na = c.get("donem_sayisi"), c.get("donem_ayni_isaret")
        sat.append(f"etiket: {c['hukum']}" + (f" ({_SAYI_KOK.get(nd, str(nd))} dönemin "
                                               f"{_SAYI_AD.get(na, str(na))} aynı işaret)" if nd and na is not None else ""))
        d = [f"{_kisa_donem(v['etiket'])} {_imz(v['kor'])}" for v in (c.get("donemler") or {}).values()
             if isinstance(v, dict) and v.get("kor") is not None]
        if d:
            sat.append("dönemler: " + " · ".join(d))
        for alan in ("hukum_notu", "kapsam_notu", "beklenen_isaret_notu"):
            if c.get(alan):
                sat.append(c[alan])
        bh = c.get("bacaklar_haftalik") or {}
        if bh.get("fark_varyansinda_abd_payi_yuzde") is not None:
            pay = bh["fark_varyansinda_abd_payi_yuzde"]
            sat.append(f"tam örneklemde farkın haftalık değişim varyansında ABD bacağının payı %{vir(pay, 0)}"
                       + (" (yerel getiri ABD'ninkiyle aynı yönde oynuyor; yerel bacağın katkısı eksi)"
                          if pay > 100 else ""))
        yd = c.get("yonetilen_donem")
        mm = re.search(r"(\d{4})-(\d{2})\s*…\s*(\d{4})-(\d{2})", (yd or {}).get("etiket") or "")
        if mm and yd.get("kor") is not None:
            sat.append(f"yönetilen kur dönemi ({mm[2]}.{mm[1]} … {mm[4]}.{mm[3]}) ölçüye girmez; o dönem ayrı "
                       f"ölçülür: korelasyon {_imz(yd['kor'])} ({yd['n']} hafta)")
    for alt in h.get("alternatif") or []:
        a = cift.get(f"{para}_{alt}")
        if not a or a.get("durum") == "kurulmadi":
            continue
        aw = a.get(sk) or {}
        if aw.get("kor") is None:
            continue
        kap = next((z.get("kapsam_payi_yuzde") for z in sira if z.get("surucu") == alt), None)
        kisa = alt in (h.get("kisa_kapsamli") or [])
        ek = (f" · kapsam oranı %{vir(kap, 0)}, kıyas dışı" if kisa and kap is not None
              else (" · kısa kapsam, kıyas dışı" if kisa else ""))
        sat.append(f"gruptaki öbür aday: {a['surucu_ad']} {_imz(aw['kor'])} ({aw['n']} hafta){ek}")
    if c and c.get("gerekce"):
        sat.append("gerekçe: " + c["gerekce"])
    return _sar("<br>".join(sat), HOVER_EN)


def s_surucu_harita(o: dict) -> None:
    b = o["b10"]
    m = b["sekil_surucu_harita"]
    p = b["p10c"]
    cift = p["ciftler"]
    satirlar, sutunlar, hucre = m["satirlar"], m["sutunlar"], m["hucre"]
    para_ad = dict(zip(satirlar, m["satir_ad"]))
    sutun_ad = dict(zip(sutunlar, m["sutun_ad"]))
    atanmis = {c for _, _, cs in _PANELLER for c in cs}
    eksik = [c for c in sutunlar if c not in atanmis]
    if eksik:
        raise ValueError(f"sürücü haritasında panele atanmamış sütun: {eksik}")
    yil = (m["ilk"][:4], m["son"][:4])
    pencere_et = f"{yil[0]}–{yil[1]}"
    sk = f"siralama_{yil[0]}_{yil[1]}"
    tam_et = f"{p['ilk'][:4]}–{p['son'][:4]}"

    # Hücrelerin ve çiftlerin özeti: başlığın bulgusu ve alt başlığın tarihleri buradan.
    dolu = [(satirlar[i], sutunlar[j], h) for i, r in enumerate(hucre) for j, h in enumerate(r) if h]
    ilkler, sonlar, tlist = [], [], []
    for para, _, h in dolu:
        w = (cift.get(f"{para}_{h['surucu']}") or {}).get(sk) or {}
        if w.get("ilk"):
            ilkler.append(w["ilk"])
            sonlar.append(w["son"])
        tlist.append(w.get("t"))
    ters = [(para, h, t) for (para, _, h), t in zip(dolu, tlist) if h["ters"]]
    ters_zayif = bool(ters) and all(t is not None and abs(t) < 2 for _, _, t in ters)

    paneller = []
    for pid, kose, cols in _PANELLER:
        cols = [c for c in cols if c in sutunlar]
        rows = [i for i in range(len(satirlar)) if any(hucre[i][sutunlar.index(c)] for c in cols)]
        if not cols or not rows:
            continue
        cok = {c: len({hucre[i][sutunlar.index(c)]["surucu"] for i in rows if hucre[i][sutunlar.index(c)]}) > 1
               for c in cols}
        satir_sayisi = 3 if any(cok.values()) else 2
        paneller.append({"kose": kose, "cols": cols, "rows": rows, "cok": cok,
                         "px": len(rows) * (14 * satir_sayisi + 4)})   # 11 piksellik yazı küçülmeden sığsın
    ara = 58                                            # paneller arası: ikinci panelin sütun başlıkları
    cizim = sum(pn["px"] for pn in paneller) + ara * (len(paneller) - 1)

    fig = make_subplots(rows=len(paneller), cols=1, row_heights=[pn["px"] for pn in paneller],
                        vertical_spacing=ara / cizim)
    ann = []
    for pi, pn in enumerate(paneller, start=1):
        cols, rows = pn["cols"], pn["rows"]
        dx, dbase, dyazi, drenk, dyrenk, dhover, dkalin, dkenar = [], [], [], [], [], [], [], []
        bx, bbase = [], []
        for ii, i in enumerate(rows):
            para = satirlar[i]
            for j, c in enumerate(cols):
                h = hucre[i][sutunlar.index(c)]
                if not h:
                    bx.append(j)
                    bbase.append(ii - 0.46)
                    continue
                cf = cift.get(f"{para}_{h['surucu']}")
                ust = f"<b>{_imz(h['kor'])}</b>" + (" · ters" if h["ters"] else "")
                parca = [ust]
                if pn["cok"][c]:
                    parca.append(_surucu_kisa(h["surucu"], h["surucu_ad"]))
                parca.append(h["etiket"] + (" · kısa kapsam" if h.get("kisa_kapsam") else ""))
                dx.append(j)
                dbase.append(ii - 0.46)
                dyazi.append("<br>".join(parca))
                drenk.append(h["kor"])
                dyrenk.append(_yazi_rengi(_olcek_rengi(h["kor"] / RENK_SINIR)))
                dhover.append(_hucre_hover(h, para, para_ad[para], cf, cift,
                                           (p.get("siralama", {}).get(para) or {}).get("sira") or [],
                                           pencere_et, sk, tam_et))
                dkalin.append(_TERS_KALIN if h["ters"] else 1.0)
                dkenar.append(MUREKKEP if h["ters"] else _KENAR)
        if bx:
            fig.add_trace(go.Bar(x=bx, y=[0.92] * len(bx), base=bbase, width=0.94, showlegend=False,
                                 marker=dict(color="white", line=dict(color=_BOS_KENAR, width=1)),
                                 hoverinfo="skip"), pi, 1)
        fig.add_trace(go.Bar(
            x=dx, y=[0.92] * len(dx), base=dbase, width=0.94, showlegend=False,
            marker=dict(color=drenk, colorscale=_OLCEK, cmin=-RENK_SINIR, cmax=RENK_SINIR, showscale=False,
                        line=dict(color=dkenar, width=dkalin)),
            text=dyazi, textposition="inside", insidetextanchor="middle", textangle=0, constraintext="inside",
            textfont=dict(color=dyrenk, size=11), customdata=dhover,
            hovertemplate="%{customdata}<extra></extra>"), pi, 1)
        yk = "yaxis" if pi == 1 else f"yaxis{pi}"
        xr = "x" if pi == 1 else f"x{pi}"
        ust = fig.layout[yk].domain[1]
        for j, c in enumerate(cols):
            ann.append(dict(x=j, xref=xr, y=ust, yref="paper", yanchor="bottom", showarrow=False,
                            text=_SUTUN_KISA.get(c, sutun_ad[c]), font=dict(size=11), hovertext=sutun_ad[c]))
        ann.append(dict(x=0, xref="paper", xanchor="right", xshift=-6, y=ust, yref="paper", yanchor="bottom",
                        showarrow=False, align="right", text=pn["kose"], font=dict(size=11)))
        fig.update_xaxes(visible=False, range=[-0.5, len(cols) - 0.5], fixedrange=True, row=pi, col=1)
        fig.update_yaxes(range=[len(rows) - 0.5, -0.5], tickvals=list(range(len(rows))),
                         ticktext=[_para_kisa(satirlar[i]) for i in rows], showgrid=False, ticks="",
                         showline=False, fixedrange=True, ticklabelstandoff=4, row=pi, col=1)
    # Lejant: renk yönü iki örnekle (hücre değerini yazdığı için sürekli ölçek yerine), kalın çerçeve kendi öğesiyle.
    # Korelasyon bir eğilimdir, kural değil: "sürücü yükselince para değer kazanır" 0,2'lik bir bağ için güçlü kalırdı.
    for ad, r0 in (("artı: sürücü yükselirken para değer kazanma eğiliminde", 0.75),
                   ("eksi: sürücü yükselirken para değer kaybetme eğiliminde", -0.75)):
        if any((h["kor"] > 0) == (r0 > 0) for _, _, h in dolu):
            fig.add_trace(go.Bar(x=[None], y=[None], name=ad, hoverinfo="skip",
                                 marker=dict(color=_olcek_rengi(r0), line=dict(color=_KENAR, width=1))), 1, 1)
    if ters:
        fig.add_trace(go.Bar(x=[None], y=[None], hoverinfo="skip",
                             name="kalın çerçeve: işaret beklenenin tersi" + (" (bu pencerede |t| < 2)" if ters_zayif else ""),
                             marker=dict(color="white", line=dict(color=MUREKKEP, width=_TERS_KALIN))), 1, 1)

    # Başlık: kaç hücrede bağ beklenen yönde VE istikrarlı (tam örneklem işareti de beklenen yönde);
    # en güçlü bağın eşzamanlı R²'si üçte birin altındaysa bu söylenir (ölçümden güçlü değil).
    istikrarli = [h for para, _, h in dolu if not h["ters"] and h["etiket"] == "istikrarlı"
                  and (cift.get(f"{para}_{h['surucu']}") or {}).get("beklenen_isaret_tutuyor") is True]
    en = max((h for _, _, h in dolu), key=lambda h: abs(h["kor"]))
    bulgu = f"{len(dolu)} hücreden {len(istikrarli)} tanesinde bağ beklenen yönde ve istikrarlı; "
    # Tek değişkenli bağda açıklanan pay korelasyonun karesidir (R²): pay VARYANSIN payıdır, değişimin değil.
    if en["kor"] ** 2 < 1 / 3:
        bulgu += (f"en güçlüsü ({_imz(en['kor'])}) bile haftalık değişim varyansının üçte birinden azını "
                  f"açıklıyor (R² {vir(en['kor'] ** 2, 2)})")
    else:
        bulgu += f"en güçlüsü {_imz(en['kor'])} (R² {vir(en['kor'] ** 2, 2)})"
    esik = re.search(r"%(\d+) eşiğinin", m.get("yontem") or "")
    hukum = re.search(r"Hüküm: (.*?'zayıf')", p.get("yontem") or "")
    alt = [f"haftalık (perşembe–perşembe) eşzamanlı korelasyon, {tarih(min(ilkler))}–{tarih(max(sonlar))}",
           "CNBC (kur New York 17:00, emtia vadelisi, yerel getiri) · ABD Hazinesi · Yahoo (USD/TRY, VIX)",
           "para dolara karşı değeriyle (artış: değer kazancı) · altın $/ons",
           "grupta en güçlü aday yazılır"
           + (f"; kapsam oranı %{esik.group(1)} eşiğinin altındaki seçilmez" if esik else ""),
           f"etiket {tam_et} hükmü" + (f": {hukum.group(1).replace('tam örneklemde ', '')}" if hukum else ""),
           "boş hücre: ölçülmedi · TL'de yönetilen kur dönemi dışarıda · öngörü değil"]
    baslik = _baslik("harita", bulgu, alt)
    ust_pay = _ust_pay(baslik)
    fig.update_layout(
        barmode="overlay", bargap=0, annotations=list(fig.layout.annotations) + ann,
        title=_baslik_yeri(baslik), hoverlabel=dict(align="left"),
    )
    # Alt pay: ev stilinin lejant konumu çizim yüksekliğinin %10'u aşağısıdır ve dar ekranda üç öğe alt alta
    # dizilir (alt boşluk ~70 piksel büyür, çizim alanı o kadar daralır): pay buna göre, yoksa 390 pikselde
    # üç satırlık hücre yazısı küçülüyordu.
    _yaz(fig, _dosya("harita"), int(ust_pay + cizim * 1.1 + 140))


# ───────────────────────────────────────────────────────── Şekil: kayan korelasyon
def s_surucu_kayan(o: dict) -> None:
    b = o["b10"]
    k = b["sekil_surucu_kayan"]
    cift = b["p10c"]["ciftler"]
    ciftler, t = k["ciftler"], k["tarih"]
    n = len(ciftler)
    panel_px, ara = 86, 38
    cizim = n * panel_px + (n - 1) * ara
    basliklar = []
    for a in ciftler:
        c = cift[a]
        basliklar.append(f"<b>{c['para_ad']}{_AYRAC}{_surucu_orta(c['surucu_ad'])}</b>")
    fig = make_subplots(rows=n, cols=1, shared_xaxes=True, vertical_spacing=ara / cizim, subplot_titles=basliklar)
    _panel_basliklari(fig, n)
    hepsi = [x for a in ciftler for x in k["seriler"][a] if x is not None]
    ters_lejant = False
    lo = min(-0.5, math.floor(min(hepsi) / 0.5) * 0.5)
    hi = max(0.5, math.ceil(max(hepsi) / 0.5) * 0.5)
    for r, a in enumerate(ciftler, start=1):
        s = k["seriler"][a]
        oz = k["ozet"][a]
        bek = oz["beklenen_isaret"]
        # Beklenenin tersine geçen pencereler: korelasyonun sıfırla arası gölgeli.
        ters_y = [None if x is None else (x if x * bek < 0 else 0.0) for x in s]
        if any(x is not None and x * bek < 0 for x in s):
            fig.add_trace(go.Scatter(x=t, y=ters_y, mode="lines", line=dict(width=0), fill="tozeroy",
                                     fillcolor="rgba(140,47,57,0.30)", hoverinfo="skip", legendgroup="ters",
                                     name="korelasyon beklenen işaretin tersinde", showlegend=not ters_lejant,
                                     legendrank=3), r, 1)
            ters_lejant = True
        fig.add_trace(go.Scatter(x=t, y=s, mode="lines", line=dict(color=MAVI, width=1.7), legendgroup="kayan",
                                 name="52 haftalık kayan korelasyon", showlegend=r == 1, legendrank=1,
                                 hovertemplate="hafta %{x|%d.%m.%Y}: %{y:.2f}<extra>" + basliklar[r - 1]
                                 .replace("<b>", "").replace("</b>", "") + "</extra>"), r, 1)
        fig.add_trace(go.Scatter(x=[t[0], t[-1]], y=[oz["kor_tam"]] * 2, mode="lines",
                                 line=dict(color=GRI, width=1.3, dash="dash"), legendgroup="tam",
                                 name=f"tam örneklem korelasyonu ({cift[a]['tam']['ilk'][:4]}–{cift[a]['tam']['son'][:4]})",
                                 showlegend=r == 1, legendrank=2, hoverinfo="skip"), r, 1)
        fig.add_annotation(x=1, xref=("x" if r == 1 else f"x{r}") + " domain", xanchor="left", xshift=4,
                           y=oz["kor_tam"], yref="y" if r == 1 else f"y{r}", showarrow=False,
                           text=_imz(oz["kor_tam"]), font=dict(size=10.5, color="#5f594f"))
        fig.add_hline(y=0, line=dict(color=MUREKKEP, width=0.8), row=r, col=1)
        fig.update_yaxes(range=[lo, hi], tickvals=[-0.5, 0, 0.5], ticktext=[vir(-0.5, 1), "0", vir(0.5, 1)],
                         fixedrange=True, row=r, col=1)
    _donem_bantlari(fig, o, range(1, n + 1))
    fig.update_xaxes(showticklabels=True, tickformat="%Y", dtick="M24", tickfont=dict(size=10), fixedrange=True)
    # Başlık: beklenen işaretteki pencere payının en küçüğü (aşağı yuvarlanır: "en az") ve gücün en çok değiştiği
    # çift, DÖNEM korelasyonlarıyla (p10c, her biri 150–260 hafta). Kayan pencerenin en düşüğü ile en yükseği güç
    # değişiminin ölçüsü olamaz: korelasyonu SABİT (ρ = 0,5) bağımsız normal haftalarda 885 haftalık bir serinin
    # 52 haftalık pencerelerinin en düşüğü ile en yükseği medyanda 0,52 ayrışır (%90 bant 0,41–0,66; ρ = 0,3'te
    # 0,62; 300 benzetim). Ölçülen en küçük aralık (0,65) bu bandın içinde: aralık güç değişimini göstermez.
    pay = min(k["ozet"][a]["beklenen_isarette_pay_yuzde"] for a in ciftler)
    yon = "bağın yönü büyük ölçüde tutuyor" if pay >= 90 else "bağın yönü dönem dönem değişiyor"
    et = {dn["anahtar"]: dn["etiket"] for dn in _donemler(o)}
    dk = {}
    for a in ciftler:
        z = [(dn, v["kor"]) for dn, v in (cift[a].get("donemler") or {}).items()
             if isinstance(v, dict) and v.get("kor") is not None]
        if len(z) >= 2:
            dk[a] = (min(z, key=lambda q: q[1]), max(z, key=lambda q: q[1]))
    bulgu = f"{n} çiftte {yon} (beklenen işaretteki pencere payı en az{_NB}%{math.floor(pay):d})"
    if dk:
        a = max(dk, key=lambda q: dk[q][1][1] - dk[q][0][1])
        uc = sorted(dk[a], key=lambda q: list(et).index(q[0]))
        bulgu += (f"; gücün en çok değiştiği çift {basliklar[ciftler.index(a)].replace('<b>', '').replace('</b>', '')}: "
                  f"korelasyon {et[uc[0][0]]} döneminde {_imz(uc[0][1])}, {et[uc[1][0]]} döneminde {_imz(uc[1][1])}")
    asgari = _kayan_asgari(o)
    d = _donemler(o)
    alt = [f"haftalık değişim (perşembe–perşembe), pencere sonu {tarih(k['ilk'])}–{tarih(k['son'])}",
           "52 haftalık kayan korelasyon" + (f" (en az {asgari} ortak hafta; azsa çizgi kesilir)" if asgari else ""),
           "CNBC (kur New York 17:00, emtia vadelisi, yerel getiri), ABD Hazinesi",
           "para dolara karşı değeriyle (artış: değer kazancı) · altın $/ons",
           "faiz farkı yerel − ABD · kesikli çizgi ve sağdaki sayı: tam örneklem",
           f"gri bant: {d[1]['etiket']} ve {d[3]['etiket']} dönemleri · eşzamanlı tarif, öngörü değil"]
    baslik = _baslik("kayan", bulgu, alt)
    fig.update_layout(title=_baslik_yeri(baslik), hoverlabel=dict(align="left"))
    _yaz(fig, _dosya("kayan"), int(_ust_pay(baslik) + cizim * 1.1 + 90))


# ───────────────────────────────────────────────────────── Şekil: USD/JPY ve faiz farkı
def s_usdjpy(o: dict) -> None:
    b = o["b10"]
    u = b["sekil_usdjpy"]
    cift = b["p10c"]["ciftler"]
    t = u["tarih"]
    d = _donemler(o)
    vadeler = (("2y", "2 yıllık", CLARET), ("10y", "10 yıllık", TURUNCU))
    sev = u["seviye_korelasyonu"]
    degisim = {v: {dn["anahtar"]: (cift[f"jpy_jp_us_{v}"]["donemler"].get(dn["anahtar"]) or {}).get("kor")
                   for dn in d} for v, _, _ in vadeler}
    seviye = {v: {dn["anahtar"]: (sev[v]["donemler"].get(dn["anahtar"]) or {}).get("kor") for dn in d}
              for v, _, _ in vadeler}
    px = [160, 140, 115, 115, 240]
    ara = 44
    cizim = sum(px) + ara * (len(px) - 1)
    fig = make_subplots(
        rows=5, cols=1, row_heights=px, vertical_spacing=ara / cizim,
        subplot_titles=("USD/JPY (dolar başına yen), haftalık",
                        "ABD − Japonya getiri farkı (yüzde puan)",
                        "52 haftalık korelasyon (haftalık değişimler)",
                        "52 haftalık eğim: farkın 1 baz puanı başına USD/JPY (%)",
                        "Dönem içi korelasyon: seviye ve haftalık değişim"))
    _panel_basliklari(fig, 5)
    fig.add_trace(go.Scatter(x=t, y=u["usdjpy"], mode="lines", line=dict(color=MUREKKEP, width=1.6), name="USD/JPY",
                             hovertemplate="%{x|%d.%m.%Y}: %{y:.2f}<extra>USD/JPY</extra>"), 1, 1)
    for v, ad, renk in vadeler:
        grup = f"v{v}"
        fig.add_trace(go.Scatter(x=t, y=u[f"abd_eksi_japonya_{v}_yuzde"], mode="lines", legendgroup=grup,
                                 name=f"{ad} (ABD − Japonya)", line=dict(color=renk, width=1.6),
                                 hovertemplate="%{x|%d.%m.%Y}: %{y:.2f} puan<extra>" + ad + " fark</extra>"), 2, 1)
        fig.add_trace(go.Scatter(x=t, y=u[f"kor52_{v}"], mode="lines", legendgroup=grup, showlegend=False, name=ad,
                                 line=dict(color=renk, width=1.6),
                                 hovertemplate="%{x|%d.%m.%Y}: %{y:.2f}<extra>" + ad + "</extra>"), 3, 1)
        fig.add_trace(go.Scatter(x=t, y=u[f"beta52_{v}_yuzde_bp"], mode="lines", legendgroup=grup, showlegend=False,
                                 name=ad, line=dict(color=renk, width=1.6),
                                 hovertemplate="%{x|%d.%m.%Y}: %{y:.3f}<extra>" + ad + "</extra>"), 4, 1)
    # Alt panel: dönem × ölçü; seviye taralı, değişim dolu; vade rengi üst panellerle aynı.
    et = [dn["etiket"] for dn in d]
    # Yatay sütun: dar ekranda dikey sütunun genişliği değer yazısına yetmiyordu (390 pikselde ölçüldü).
    hepsi = []
    for v, ad, renk in vadeler:
        for olcu, kume, desen in (("seviye", seviye[v], "/"), ("haftalık değişim", degisim[v], "")):
            x = [kume[dn["anahtar"]] for dn in d]
            hepsi += [z for z in x if z is not None]
            fig.add_trace(go.Bar(
                y=et, x=x, orientation="h", name=f"{ad}, {olcu}", legendgroup=f"v{v}", showlegend=False,
                offsetgroup=f"{v}{olcu}",
                marker=dict(color="white" if desen else renk, line=dict(color=renk, width=1.2),
                            pattern=dict(shape=desen, fgcolor=renk, size=5, solidity=0.35) if desen else None),
                text=[_imz(z) if z is not None else "" for z in x], textposition="outside", cliponaxis=False,
                constraintext="none", textfont=dict(size=10, color=MUREKKEP),
                hovertemplate="%{y}: %{x:.2f}<extra>" + f"{ad}, {olcu}" + "</extra>"), 5, 1)
    for ad, desen in (("taralı sütun: seviye korelasyonu", "/"), ("dolu sütun: haftalık değişim korelasyonu", "")):
        fig.add_trace(go.Bar(x=[None], y=[None], name=ad, hoverinfo="skip",
                             marker=dict(color="white" if desen else GRI, line=dict(color=GRI, width=1.2),
                                         pattern=dict(shape=desen, fgcolor=GRI, size=5, solidity=0.35) if desen else None)),
                      5, 1)
    for r in (2, 3, 4):
        fig.update_xaxes(matches="x", row=r, col=1)
    for r in (1, 2, 3, 4):
        fig.update_xaxes(tickformat="%Y", dtick="M24", tickfont=dict(size=10), row=r, col=1)
    for r in (3, 4):
        fig.add_hline(y=0, line=dict(color=MUREKKEP, width=0.8), row=r, col=1)
    fig.add_vline(x=0, line=dict(color=MUREKKEP, width=0.8), row=5, col=1)
    _donem_bantlari(fig, o, (1, 2, 3, 4))
    fig.update_yaxes(title_text="yen", row=1, col=1)
    fig.update_yaxes(title_text="puan", row=2, col=1)          # iki getirinin farkı: yüzde PUAN
    fig.update_yaxes(range=[-0.5, 1.0], tickvals=[-0.5, 0, 0.5, 1], title_text="korelasyon", row=3, col=1)
    fig.update_yaxes(title_text="% / bp", row=4, col=1)
    fig.update_yaxes(autorange="reversed", ticks="", row=5, col=1)
    fig.update_xaxes(range=[max(-1.35, min(hepsi) - 0.32), min(1.35, max(hepsi) + 0.32)],
                     tickvals=[-1, -0.5, 0, 0.5, 1], title_text="korelasyon", row=5, col=1)
    fig.update_layout(barmode="group", bargap=0.2, bargroupgap=0.06)

    # Başlık: hüküm DEĞİŞİMDEN kurulur ve önce gelir (değişim korelasyonu kaç dönemde artı, aralığıyla); seviye
    # yalnız uyarıdır ve ikinci sıradadır (kaç dönemde eksi). "Seviyede ters yönde ilerledi" denmez: 10 yıllıkta
    # 2015–2019 seviye korelasyonu −0,19'dur, ters yönde bir eğilim cümlesini taşımaz. İki vade aynı sayımı
    # veriyorsa ikisi birlikte anılır.
    say = {v: (sum(1 for x in seviye[v].values() if x is not None and x < 0),
               sum(1 for x in degisim[v].values() if x is not None and x > 0)) for v, _, _ in vadeler}
    nd = len(d)
    kok = _SAYI_KOK.get(nd, str(nd))
    ikisi = say["2y"] == say["10y"]
    vad = "2 ve 10 yıllık" if ikisi else "2 yıllık"
    s_eksi, d_arti = say["2y"]
    dv = [x for v, _, _ in (vadeler if ikisi else vadeler[:1]) for x in degisim[v].values() if x is not None]
    bulgu = (f"USD/JPY ile ABD − Japonya {vad} farkının haftalık değişimleri {kok} dönemin "
             f"{_SAYI_AD.get(d_arti, str(d_arti))} artı korelasyonlu ({_imz(min(dv))}{_NB}…{_NB}{_imz(max(dv))}); "
             f"seviye korelasyonu ise {_SAYI_KOK.get(s_eksi, str(s_eksi))} dönemde eksi")
    asgari = _kayan_asgari(o)
    alt = [f"haftalık (perşembe), {tarih(u['ilk'])}–{tarih(u['son'])} · USD/JPY: CNBC, New York 17:00",
           "fark: ABD Hazinesi getirisi eksi Japonya getirisi (CNBC, Tokyo kapanışı)",
           "korelasyon ve eğim: haftalık değişim, 52 haftalık pencere"
           + (f" (en az {asgari} hafta)" if asgari else ""),
           "eğim: farkın 1 baz puanlık artışında USD/JPY'nin yüzde değişimi",
           "seviye korelasyonu ortak eğilimle şişer ya da ters döner; hüküm değişimden",
           f"gri bant: {d[1]['etiket']} ve {d[3]['etiket']} · boşluk: Japonya getirisi kaynakta yok"
           + (f"; kayan ölçüde pencerede {asgari} ortak haftadan az" if asgari else "")]
    baslik = _baslik("usdjpy", bulgu, alt)
    fig.update_layout(title=_baslik_yeri(baslik), hoverlabel=dict(align="left"))
    _yaz(fig, _dosya("usdjpy"), int(_ust_pay(baslik) + cizim * 1.1 + 110))
