# -*- coding: utf-8 -*-
"""El Niño hattı — GRAFİK katmanı (Plotly, ev stili).

Dokuz şekil, iki bölük.

TÜRKİYE (01–04). Üçüncüsü ve dördüncüsü bilerek yan yana durur: biri ilişkinin
gecikme profilini gösterir ama kalıcılık yanlısıdır, diğeri o yanlılıktan
geçmeyen epizot kanıtını verir. Okur ikisini birlikte görmeli.

KÜRESEL (05–09). Türkiye ölçümü kısa örneklemde tıkanıyor; şokun GELDİĞİ yerin
verisi 1980'de başlıyor ve orada aynı ölçüt hüküm verebiliyor. 07 numaralı
şekil üç ölçeği (küresel emtia, ABD, Türkiye) AYNI cetvelle yan yana koyar —
tezin omurgası odur. Küresel blok yoksa bu beş şekil hiç üretilmez ve eskileri
SİLİNİR; bayat grafik, bayat sayıdan beterdir çünkü tarihi üstünde yazmaz.
"""
from __future__ import annotations

import json
import pathlib

import plotly.graph_objects as go

PROJE = pathlib.Path(__file__).resolve().parent
DATA = PROJE / "data"
CIKTI = PROJE / "cikti"
CIKTI.mkdir(exist_ok=True)

INK = "#211b12"; GRID = "#d9d2c2"; CLARET = "#8e1f2f"; TEAL = "#1d5c5c"
GOLD = "#9a7327"; INDIGO = "#34456e"; PLUM = "#6d3a5d"


def _duzen(fig, baslik, alt, h=470, y_baslik=""):
    ust = 92 + 26 * len(alt) + 25
    metin = f"<b>{baslik}</b>" + "".join(f"<br><sup>{x}</sup>" for x in alt)
    fig.update_layout(
        title=dict(text=metin, x=0, xanchor="left", y=1.0, yanchor="top",
                   yref="container", pad=dict(t=14, l=0),
                   font=dict(size=15, color=INK, family="Georgia, serif")),
        height=h, plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="Georgia, serif", size=12, color=INK),
        legend=dict(orientation="h", yanchor="top", y=-0.12, x=0,
                    font=dict(size=11), bgcolor="rgba(255,255,255,0)"),
        margin=dict(l=64, r=64, t=ust, b=110), hovermode="x unified", bargap=0.15,
        hoverlabel=dict(bgcolor="white", bordercolor=GRID))
    fig.update_xaxes(gridcolor=GRID, zeroline=False, automargin=True)
    fig.update_yaxes(gridcolor=GRID, zeroline=True, zerolinecolor=INK,
                     zerolinewidth=1.1, automargin=True, title_text=y_baslik)
    return fig


def _yaz(fig, ad):
    fig.write_html(CIKTI / ad, include_plotlyjs="cdn", full_html=True,
                   config={"responsive": True, "displaylogo": False})
    print(f"  yazıldı: cikti/{ad}")


def sekil_01(M, oni_tam):
    x = [k["ay"] for k in oni_tam]
    v = [k["oni"] for k in oni_tam]
    fig = go.Figure()
    fig.add_bar(x=x, y=[max(0, z) if z is not None else None for z in v],
                name="El Niño (ONI > 0)", marker_color=CLARET)
    fig.add_bar(x=x, y=[min(0, z) if z is not None else None for z in v],
                name="La Niña (ONI < 0)", marker_color=TEAL)
    for esik, ad in ((1.5, "güçlü"), (2.0, "çok güçlü")):
        fig.add_hline(y=esik, line=dict(color=INK, width=1, dash="dot"),
                      annotation_text=ad, annotation_position="right",
                      annotation_font=dict(size=10, color=INK))
    _duzen(fig, "Oceanic Niño Index — 1950'den bugüne",
           ["Niño 3.4 bölgesi deniz yüzeyi sıcaklık anomalisinin üç aylık kayan "
            "ortalaması (°C). Etiket ortadaki aya karşılık gelir.",
            f"Son ölçüm {M['oni_son_ay']}: {M['oni_son']:+.2f} °C. "
            "Kaynak: NOAA Climate Prediction Center."],
           h=430, y_baslik="°C")
    fig.update_layout(barmode="relative")
    _yaz(fig, "01-oni-tarihce.html")


def sekil_02(M):
    t = M["tarihce"]
    x = [k["ay"] for k in t]
    fig = go.Figure()
    fig.add_scatter(x=x, y=[k["goreceli_gida"] for k in t], name="Göreceli gıda enflasyonu (sağ)",
                    mode="lines", line=dict(color=CLARET, width=2), yaxis="y2")
    fig.add_scatter(x=x, y=[k["oni"] for k in t], name="ONI (sol)",
                    mode="lines", line=dict(color=INDIGO, width=1.6))
    fig.update_layout(yaxis=dict(title="ONI, °C", gridcolor=GRID),
                      yaxis2=dict(title="puan", overlaying="y", side="right",
                                  showgrid=False, zeroline=False))
    _duzen(fig, "El Niño ile Türkiye'de gıdanın göreceli fiyatı",
           ["Göreceli gıda enflasyonu = gıda yıllık enflasyonu − manşet TÜFE yıllık. "
            "Ortak parasal trend iki taraftan da düşer;",
            "geriye gıdayı sepetin geri kalanından AYRIŞTIRAN şok kalır — ENSO'nun "
            "iddia ettiği kanal budur.",
            "Kaynak: NOAA CPC (ONI), TCMB EVDS / TÜİK (TÜFE)."],
           h=470)
    _yaz(fig, "02-oni-goreceli-gida.html")


def sekil_03(M):
    fig = go.Figure()
    # Örneklem aynıysa tek eğri: iki kez çizmek sahte sağlamlık izlenimi verir.
    seriler = ([("modern", f"{M.get('orneklem_bas','')} → {M.get('orneklem_son','')}", CLARET)]
               if M.get("orneklem_ayni")
               else [("modern", "2005'ten bugüne", CLARET), ("tam", "tam örneklem", GOLD)])
    for etiket, ad, renk in seriler:
        c = M.get(f"capraz_{etiket}")
        if not c:
            continue
        fig.add_scatter(x=[d["gecikme"] for d in c], y=[d["korelasyon"] for d in c],
                        name=ad, mode="lines+markers",
                        line=dict(color=renk, width=2), marker=dict(size=5))
    en = M.get("capraz_modern_en_iyi_gecikme")
    if en is not None:
        fig.add_vline(x=en, line=dict(color=INK, width=1.2, dash="dot"),
                      annotation_text=f"en güçlü: {en} ay",
                      annotation_font=dict(size=11, color=INK))
    _duzen(fig, "Gecikme profili — ONI kaç ay sonra gıdaya vuruyor",
           ["Yatay eksen: ONI'nin kaç ay ÖNCEKİ değeri alındığı. Dikey eksen: o "
            "gecikmedeki korelasyon.",
            "UYARI: iki seri de kalıcı olduğundan katsayılar YUKARI YANLIDIR ve tek "
            "başına kanıt sayılmaz; şekil yalnız gecikmenin NEREDE olduğunu gösterir.",
            "Kanıt için Şekil 04'e bakınız."],
           h=450, y_baslik="korelasyon")
    _yaz(fig, "03-gecikme-profili.html")


def sekil_04(M):
    kayit = M.get("epizot_sonrasi") or []
    if not kayit:
        return
    fig = go.Figure()
    fig.add_bar(x=[k["zirve"] for k in kayit], y=[k["goreceli_gida_ort"] for k in kayit],
                marker_color=[CLARET if k["goreceli_gida_ort"] > 0 else TEAL for k in kayit],
                text=[f"{k['goreceli_gida_ort']:+.1f}".replace(".", ",") for k in kayit],
                textposition="outside", cliponaxis=False, showlegend=False,
                customdata=[k["zirve_oni"] for k in kayit],
                hovertemplate="zirve %{x}<br>ONI %{customdata:+.2f} °C"
                              "<br>sonraki 18 ay göreceli gıda %{y:+.2f} puan<extra></extra>")
    fig.add_hline(y=M["kosulsuz_ortalama"], line=dict(color=INK, width=1.4, dash="dot"),
                  annotation_text=f"koşulsuz ortalama {M['kosulsuz_ortalama']:+.2f}".replace(".", ","),
                  annotation_position="top left", annotation_font=dict(size=11))
    _duzen(fig, "Epizot çalışması — güçlü El Niño zirvelerinden sonraki 18 ay",
           ["Her çubuk bir güçlü El Niño epizodunun (ONI ≥ 1,5 °C, en az beş ay) "
            "zirvesinden sonraki 18 ayda",
            "göreceli gıda enflasyonunun ortalamasıdır. Noktalı çizgi bütün "
            "dönemlerin ortalaması.",
            "Kalıcılık yanlılığı bu ölçütten GEÇMEZ — tezin dayandığı kanıt budur."],
           h=470, y_baslik="puan")
    _yaz(fig, "04-epizot.html")


# ══════════════════════════════════════════════════════════════════════
#  KÜRESEL BÖLÜK (05–09) — kaynak: data/kuresel.json
# ══════════════════════════════════════════════════════════════════════

def sekil_05(G, oni_tam):
    t = {k["ay"]: k["oni"] for k in oni_tam}
    seri = G.get("reel_gida_tarihce") or []
    x = [d["ay"] for d in seri]
    fig = go.Figure()
    fig.add_scatter(x=x, y=[d["deger"] for d in seri],
                    name="Reel küresel gıda emtia fiyatı, yıllık % (sağ)",
                    mode="lines", line=dict(color=CLARET, width=2), yaxis="y2")
    fig.add_scatter(x=x, y=[t.get(d["ay"]) for d in seri], name="ONI (sol)",
                    mode="lines", line=dict(color=INDIGO, width=1.5))
    fig.update_layout(yaxis=dict(title="ONI, °C", gridcolor=GRID),
                      yaxis2=dict(title="yıllık %", overlaying="y", side="right",
                                  showgrid=False, zeroline=False))
    _duzen(fig, "El Niño ile küresel gıda emtia fiyatı",
           ["IMF gıda fiyat endeksi ABD TÜFE'siyle deflate edilmiştir (REEL). "
            "Nominal ölçmek, arz şokunu ABD'nin",
            "kendi enflasyonuyla karıştırırdı. Türkiye ölçümünün tıkandığı yer "
            "burada açılıyor: örneklem "
            f"{G.get('kur_orneklem_bas','')}'de başlıyor ve "
            f"{G.get('kur_olculen','?')} güçlü epizot ölçülebiliyor.",
            "Kaynak: NOAA CPC (ONI), IMF birincil emtia fiyatları / FRED."],
           h=470)
    _yaz(fig, "05-kuresel-gida.html")


def sekil_06(G):
    k = [d for d in (G.get("kirilim") or []) if d.get("fark") is not None]
    if not k:
        return
    k = sorted(k, key=lambda d: d["fark"])
    ad = [("▸ " if d["toplu"] else "") + d["baslik"] for d in k]
    fig = go.Figure()
    fig.add_bar(y=ad, x=[d["fark"] for d in k], orientation="h",
                marker_color=[GOLD if d["toplu"] else
                              (CLARET if d["fark"] > 0 else TEAL) for d in k],
                text=[f"{d['fark']:+.1f}".replace(".", ",") for d in k],
                textposition="outside", cliponaxis=False, showlegend=False,
                customdata=[[d["olculen"], d["bas"]] for d in k],
                hovertemplate="%{y}<br>epizot farkı %{x:+.2f} puan"
                              "<br>ölçülen epizot %{customdata[0]}"
                              "<br>örneklem başı %{customdata[1]}<extra></extra>")
    _duzen(fig, "Hangi ürün El Niño'ya duyarlı",
           ["Her çubuk: güçlü El Niño zirvelerinden sonraki 18 ayda o ürünün REEL "
            "yıllık fiyat değişiminin ortalaması,",
            "eksi bütün dönemlerin ortalaması. Pozitif = epizot sonrası "
            "olağandan pahalı. ▸ işaretliler toplu endeks.",
            "Kanal gerçekse sıralamanın tepesinde ENSO'nun DOĞRUDAN vurduğu "
            "coğrafyaların ürünleri olmalı."],
           h=560, y_baslik="")
    fig.update_xaxes(title_text="puan")
    _yaz(fig, "06-urun-kirilimi.html")


def sekil_07(G, M):
    """Aynı cetvel, üç ölçek. Tezin omurgası."""
    kalem = [
        ("Küresel gıda emtiası<br><sub>reel, yıllık %</sub>",
         G.get("kur_epizot_ortalama"), G.get("kur_kosulsuz"),
         G.get("kur_olculen"), G.get("kur_orneklem_bas")),
        ("ABD göreceli gıda<br><sub>gıda − manşet, puan</sub>",
         G.get("abd_epizot_ortalama"), G.get("abd_kosulsuz"),
         G.get("abd_olculen"), G.get("abd_orneklem_bas")),
        ("Türkiye göreceli gıda<br><sub>gıda − manşet, puan</sub>",
         M.get("epizot_ortalama"), M.get("kosulsuz_ortalama"),
         len(M.get("epizot_sonrasi") or []), M.get("orneklem_bas")),
    ]
    kalem = [k for k in kalem if k[1] is not None and k[2] is not None]
    if not kalem:
        return
    fig = go.Figure()
    fig.add_bar(x=[k[0] for k in kalem], y=[k[2] for k in kalem],
                name="koşulsuz ortalama", marker_color=GRID)
    fig.add_bar(x=[k[0] for k in kalem], y=[k[1] for k in kalem],
                name="güçlü El Niño zirvesinden sonraki 18 ay",
                marker_color=[CLARET if (k[1] - k[2]) > 0 else TEAL for k in kalem],
                text=[f"fark {k[1]-k[2]:+.2f}".replace(".", ",") for k in kalem],
                textposition="outside", cliponaxis=False,
                customdata=[[k[3], k[4]] for k in kalem],
                hovertemplate="%{x}<br>epizot sonrası %{y:+.2f}"
                              "<br>ölçülen epizot %{customdata[0]}"
                              "<br>örneklem başı %{customdata[1]}<extra></extra>")
    fig.update_layout(barmode="group")
    _duzen(fig, "Aynı cetvel, üç ölçek — ve neden yalnız biri hüküm verebiliyor",
           ["Üç sütunda da AYNI epizot tanımı (ONI ≥ 1,5 °C, en az beş ay) ve AYNI "
            "18 aylık pencere kullanıldı.",
            "Fark ölçülen EPİZOT SAYISINDA: küresel seriler 1980'de, ABD 1947'de, "
            "Türkiye alt endeksleri 2006'da başlıyor.",
            "Üçün altında epizotla yön iddia edilmez — Türkiye sütunu bu yüzden "
            "bir bulgu, bir sonuç değildir."],
           h=520, y_baslik="")
    _yaz(fig, "07-uc-olcek.html")


def sekil_08(G):
    yol = G.get("fed_yol") or []
    if not yol:
        return
    fig = go.Figure()
    for i, d in enumerate(yol):
        fig.add_scatter(x=[d["faiz_zirve"], d["faiz_18ay"]], y=[d["zirve"]] * 2,
                        mode="lines", line=dict(color=GRID, width=6),
                        showlegend=False, hoverinfo="skip")
    fig.add_scatter(x=[d["faiz_zirve"] for d in yol], y=[d["zirve"] for d in yol],
                    mode="markers", name="ONI zirvesindeki faiz",
                    marker=dict(color=INDIGO, size=13),
                    hovertemplate="zirve %{y}<br>faiz %{x:.2f}%<extra></extra>")
    fig.add_scatter(x=[d["faiz_18ay"] for d in yol], y=[d["zirve"] for d in yol],
                    mode="markers+text", name="18 ay sonra",
                    marker=dict(color=CLARET, size=13),
                    text=[f"{d['degisim']:+.2f}".replace(".", ",") for d in yol],
                    textposition="middle right",
                    hovertemplate="zirve %{y}<br>18 ay sonra %{x:.2f}%<extra></extra>")
    _duzen(fig, "Fed politika faizi, güçlü El Niño zirvesinden sonraki 18 ay",
           ["BU ŞEKİL NEDENSEL DEĞİLDİR ve ortalaması ALINMAZ. Dört pencerenin her "
            "biri El Niño'yla ilgisi olmayan",
            "bir şeyin gölgesinde: Volcker dezenflasyonu, Asya krizi ve LTCM, "
            "faiz artırım döngüsünün ilk adımı,",
            "Kovid sonrası indirim döngüsü. Şekil, epizotların hangi REJİMLERE "
            "denk geldiğini gösterir — başka bir şeyi değil."],
           h=440, y_baslik="")
    fig.update_xaxes(title_text="%")
    _yaz(fig, "08-fed-patikasi.html")


def sekil_09(G):
    gec = G.get("gecis") or {}
    if not gec:
        return
    fig = go.Figure()
    for anahtar, ad, renk in (("abd", "Küresel reel gıda → ABD gıda TÜFE'si", INDIGO),
                              ("tr", "Küresel reel gıda → Türkiye göreceli gıda", CLARET)):
        d = gec.get(anahtar)
        if not d or not d.get("profil"):
            continue
        pr = d["profil"]
        fig.add_scatter(x=[p["gecikme"] for p in pr], y=[p["r2"] for p in pr],
                        name=ad, mode="lines+markers",
                        line=dict(color=renk, width=2), marker=dict(size=5),
                        customdata=[p["beta"] for p in pr],
                        hovertemplate="%{x} ay gecikme<br>R² %{y:.3f}"
                                      "<br>β %{customdata:.3f}<extra></extra>")
        fig.add_vline(x=d["gecikme"], line=dict(color=renk, width=1, dash="dot"))
    _duzen(fig, "Küresel fiyattan iç fiyata — geçiş nerede en güçlü",
           ["Her nokta: küresel reel gıda emtia enflasyonunun k ay ÖNCEKİ değeriyle "
            "kurulan regresyonun açıklama gücü.",
            # OKUR DİLİ. Bu satır okura kendi SÜRÜM TARİHÇEMİZİ anlatıyordu
            # ("yazının ilk sürümünde ölçülmemişti… artık ölçülü") ve hiçbir
            # kapı onu görmüyordu: okur dili ölçütleri MDX'i, koşu kaydını ve
            # derlenmiş sayfayı tarıyor, gömülü Plotly HTML'inin BAŞLIK metnini
            # taramıyordu. Kalan bulgu okur için aynı: zincirin bu halkası
            # ölçülüyor mu, ölçülmüyor mu.
            "Bu halka doğrudan ölçülür; zincirin zayıf yeri varsayım değil, "
            "ölçümün kendisidir.",
            "Noktalı dikey çizgiler her eğrinin en güçlü gecikmesi."],
           h=450, y_baslik="R²")
    fig.update_xaxes(title_text="gecikme (ay)")
    _yaz(fig, "09-gecis-profili.html")


KURESEL_DOSYALAR = ("05-kuresel-gida.html", "06-urun-kirilimi.html",
                    "07-uc-olcek.html", "08-fed-patikasi.html",
                    "09-gecis-profili.html")


def main() -> int:
    import pandas as pd
    M = json.loads((DATA / "metrik.json").read_text(encoding="utf-8"))
    oni = pd.read_csv(DATA / "oni.csv", index_col=0, parse_dates=True)["oni"]
    oni_tam = [{"ay": f"{t:%Y-%m}", "oni": None if pd.isna(v) else round(float(v), 2)}
               for t, v in oni.items()]
    print("── El Niño hattı · grafikler")
    sekil_01(M, oni_tam)
    sekil_02(M)
    sekil_03(M)
    sekil_04(M)

    kur_yol = DATA / "kuresel.json"
    if not kur_yol.exists():
        # Küresel blok düşmüşse ESKİ şekilleri bırakmak, tarihi üstünde
        # yazmayan bayat bir grafiği yayında tutmak olurdu.
        silinen = [a for a in KURESEL_DOSYALAR if (CIKTI / a).exists()]
        for a in silinen:
            (CIKTI / a).unlink()
        if silinen:
            print(f"  ! küresel blok yok — eski şekiller SİLİNDİ: {', '.join(silinen)}")
        else:
            print("  ! küresel blok yok — 05–09 üretilmedi")
        return 0
    G = json.loads(kur_yol.read_text(encoding="utf-8"))
    sekil_05(G, oni_tam)
    sekil_06(G)
    sekil_07(G, M)
    sekil_08(G)
    sekil_09(G)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
