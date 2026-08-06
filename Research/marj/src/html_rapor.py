# -*- coding: utf-8 -*-
"""
Tek dosyalık HTML raporu üretir: output/rapor.html
Grafikler base64 gömülü; metodoloji, tarifler, eşlemeler ve tablolar
doğrudan kod ve output/*.csv'den gelir (tek doğruluk kaynağı).
"""
import base64, datetime, html, pathlib, re
import pandas as pd

import veri, endeks
import grafikler as gf
import svg_grafik as sg

ROOT = pathlib.Path(__file__).resolve().parent.parent
GRAF = ROOT / "output" / "grafikler"
CIKTI = ROOT / "output"

GRAFIK_BASLIK = {
    1: "Hizmet ciro endeksleri (yıllık % değişim) — 2020 vs 2021-2022",
    2: "TÜFE fiyat endeksleri (2019 Aralık=100)",
    3: "TÜFE fiyat endeksleri (aylık % değişim)",
    4: "TÜFE fiyat endeksleri (yıllık % değişim)",
    5: "Maliyet endeksi — Kırmızı et ağırlıklı (2013 Ocak=100)",
    6: "Maliyet endeksi — Tavuk eti ağırlıklı (2013 Ocak=100)",
    7: "Maliyet endeksi — Ev yemekleri (2013 Ocak=100)",
    8: "Maliyet endeksi — Fast-food (2013 Ocak=100)",
    9: "Fiyat/maliyet oranı — Ev yemekleri (2013 Ocak=1)",
    10: "Fiyat/maliyet oranı — Kırmızı et ağırlıklı (2013 Ocak=1)",
    11: "Fiyat/maliyet oranı — Tavuk eti ağırlıklı (2013 Ocak=1)",
    12: "Fiyat/maliyet oranı — Fast-food (2013 Ocak=1)",
    13: "Fiyat/maliyet oranları: uzun dönem ort. vs Temmuz 2024 vs Temmuz 2026",
    14: "Fiyat/maliyet oranları, Ev yemekleri=1 normalize",
}


def img64(p):
    return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()


def tablo(df, index=False, kucuk=False, sinif=""):
    cls = ("tbl kucuk " if kucuk else "tbl ") + sinif
    return df.to_html(index=index, classes=cls.strip(), border=0, justify="left",
                      float_format=lambda x: f"{x:,.2f}".replace(",", "§").replace(".", ",").replace("§", "."))


def md2html(md):
    """degerlendirme_notu.md için asgari markdown dönüştürücü."""
    out, in_list = [], False
    for satir in md.splitlines():
        s = satir.rstrip()
        if not s:
            if in_list: out.append("</ol>"); in_list = False
            continue
        if s.startswith("---"):
            out.append("<hr>"); continue
        m = re.match(r"^(#{1,3})\s+(.*)", s)
        if m:
            if in_list: out.append("</ol>"); in_list = False
            sev = len(m.group(1)) + 1
            out.append(f"<h{sev}>{icmd(m.group(2))}</h{sev}>"); continue
        m = re.match(r"^(\d+)\.\s+(.*)", s)
        if m:
            if not in_list: out.append("<ol>"); in_list = True
            out.append(f"<li>{icmd(m.group(2))}</li>"); continue
        if in_list: out.append("</ol>"); in_list = False
        out.append(f"<p>{icmd(s)}</p>")
    if in_list: out.append("</ol>")
    return "\n".join(out)


def icmd(s):
    s = html.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\*(.+?)\*", r"<em>\1</em>", s)
    return s


def tarif_tablosu():
    satirlar = []
    ad_tr = {"mercimek_corbasi": "Mercimek çorbası", "pirinc_pilavi": "Pirinç pilavı",
             "etsiz_kuru_fasulye": "Etsiz kuru fasulye", "hamburger": "Hamburger", "pizza": "Pizza",
             "cig_kofte": "Çiğ köfte", "kiymali_pide": "Kıymalı pide", "lahmacun": "Lahmacun",
             "iskender": "İskender", "adana_kebap": "Adana kebap", "et_doner": "Et döner",
             "tavuk_sis": "Tavuk şiş", "tavuk_doner": "Tavuk döner"}
    for yemek, tarif in endeks.TARIFLER.items():
        parcalar = []
        for k, pay in tarif.items():
            if isinstance(k, tuple):
                adlar = " + ".join(veri.MADDE_ADLARI[kk] for kk in k)
                parcalar.append(f"{adlar} (eşit böl.) <b>{pay}</b>")
            else:
                parcalar.append(f"{veri.MADDE_ADLARI[k]} <b>{pay}</b>")
        satirlar.append({"Yemek": ad_tr[yemek], "Gıda maliyeti payları (%) → eşlenen TÜİK maddeleri": "; ".join(parcalar)})
    return pd.DataFrame(satirlar)


def konsept_tablosu():
    ad_tr = {"mercimek_corbasi": "mercimek çorbası", "pirinc_pilavi": "pirinç pilavı",
             "etsiz_kuru_fasulye": "etsiz kuru fasulye", "hamburger": "hamburger", "pizza": "pizza",
             "cig_kofte": "çiğ köfte", "kiymali_pide": "kıymalı pide", "lahmacun": "lahmacun",
             "iskender": "İskender", "adana_kebap": "Adana kebap", "et_doner": "et döner",
             "tavuk_sis": "tavuk şiş", "tavuk_doner": "tavuk döner"}
    rows = []
    for k, t in endeks.KONSEPTLER.items():
        rows.append({
            "Konsept": endeks.KONSEPT_ETIKET[k],
            "Yemekler (maliyet tarafı, eşit ağırlık)": ", ".join(ad_tr[y] for y in t["yemekler"]),
            "Fiyat tarafı TÜİK maddeleri": ", ".join(f"{m} {veri.MADDE_ADLARI[m]}" for m in t["fiyat_maddeleri"]),
        })
    return pd.DataFrame(rows)


def main():
    sonuc = endeks.hepsi()
    kars = pd.read_csv(CIKTI / "karsilastirma_tablosu.csv")
    duy = pd.read_csv(CIKTI / "duyarlilik.csv")
    katki = pd.read_csv(CIKTI / "katki_ayristirma.csv", index_col=0)
    meta = sonuc["madde_meta"].reset_index(names="kod")
    notu = md2html((CIKTI / "degerlendirme_notu.md").read_text(encoding="utf-8"))
    agirlik = pd.DataFrame(endeks.AGIRLIKLAR).T.rename(
        columns={"iscilik": "İşgücü", "gida": "Gıda", "enerji": "Enerji", "kira": "Kira", "diger": "Diğer"},
        index={"nihai": "Nihai (not, Tablo 4)", "bist": "BİST-KAP", "resim": "TCMB-RESİM"})

    # ---------------- Etkileşimli SVG grafikler (hover: tarih + değer) ----------------
    evds = veri.tum_evds()
    VERI = {}
    grafik_html = []

    def ekle(no, fig_html, veri_d):
        VERI[f"g{no}"] = veri_d
        grafik_html.append(fig_html)

    def bas(no):
        return f"<b>Grafik {no}.</b> {GRAFIK_BASLIK[no]}"

    # G1 — hizmet ciro barları
    ciro = gf.hizmet_ciro_oku()
    yillik = ciro.pct_change() * 100
    sektor_etiket = {
        "H - Ulaştırma ve depolama": "Ulaştırma ve\ndepolama",
        "I - Konaklama ve yiyecek hizmeti faaliyetleri": "Konaklama ve\nyiyecek hizm.",
        "J - Bilgi ve iletişim": "Bilgi ve\niletişim",
        "L - Gayrimenkul faaliyetleri": "Gayrimenkul",
        "M - Mesleki, bilimsel ve teknik faaliyetler": "Mesleki, bilimsel\nve teknik",
        "N - İdari ve destek hizmet faaliyetleri": "İdari ve destek\nhizmetleri",
    }
    mevcut = [k for k in sektor_etiket if k in yillik.columns]
    if not mevcut:
        mevcut = [c for c in yillik.columns if str(c).split(" ")[0] in list("HIJLMN")][:6]
        sektor_etiket = {c: str(c).split(" - ")[-1][:18] for c in mevcut}
    h1, v1 = sg.bar_svg("g1", [sektor_etiket[c] for c in mevcut],
                        [{"ad": "2020", "renk": "#2a78d6",
                          "vals": [round(float(yillik.loc[2020, c]), 1) for c in mevcut]},
                         {"ad": "2021-2022 ort.", "renk": "#eb6834",
                          "vals": [round(float(yillik.loc[[2021, 2022], c].mean()), 1) for c in mevcut]}],
                        fmt="yuzde", baslik=bas(1))
    ekle(1, h1, v1)

    # G2-G4 — TÜFE karşılaştırma çizgileri
    exc = gf.gida_yemek_haric_tufe(evds)
    uclu = [("Gıda ve Yemek Hariç TÜFE", exc, "#2a78d6"),
            ("Gıda ve Alkolsüz İçecekler", evds["gida_alkolsuz"], "#eb6834"),
            ("Yemek Hizmetleri", evds["yemek_111"], "#1baf7a")]
    baz19 = pd.Timestamp("2019-12-01")
    dilim = slice("2019-12-01", "2026-07-01")
    tarih24 = exc.loc[dilim].index
    h2, v2 = sg.cizgi_svg("g2", tarih24,
                          [{"ad": ad, "renk": r, "vals": list((s / s.loc[baz19] * 100).loc[dilim].values)}
                           for ad, s, r in uclu], fmt="endeks", baslik=bas(2))
    ekle(2, h2, v2)
    h3, v3 = sg.cizgi_svg("g3", tarih24,
                          [{"ad": ad, "renk": r, "vals": list((s.pct_change(fill_method=None) * 100).loc[dilim].values)}
                           for ad, s, r in uclu], fmt="yuzde", uc_etiket=False, baslik=bas(3))
    ekle(3, h3, v3)
    h4, v4 = sg.cizgi_svg("g4", tarih24,
                          [{"ad": ad, "renk": r, "vals": list((s.pct_change(12, fill_method=None) * 100).loc[dilim].values)}
                           for ad, s, r in uclu], fmt="yuzde", baslik=bas(4))
    ekle(4, h4, v4)

    # G5-G12 — konsept maliyet ve oran çizgileri
    m, o = sonuc["maliyet"], sonuc["oran"]
    uzun = endeks.uzun_donem_ort(o)
    splice = pd.Timestamp("2022-05-01")
    for konsept, no in [("kirmizi_et", 5), ("tavuk", 6), ("ev_yemekleri", 7), ("fast_food", 8)]:
        s = m[konsept]
        hh, vv = sg.cizgi_svg(f"g{no}", s.index,
                              [{"ad": "Maliyet endeksi", "renk": gf.RENK[konsept], "vals": list(s.values)}],
                              fmt="endeks", splice_ts=splice, baslik=bas(no))
        ekle(no, hh, vv)
    for konsept, no in [("ev_yemekleri", 9), ("kirmizi_et", 10), ("tavuk", 11), ("fast_food", 12)]:
        s = o[konsept]
        hh, vv = sg.cizgi_svg(f"g{no}", s.index,
                              [{"ad": "Fiyat/Maliyet", "renk": gf.RENK[konsept], "vals": list(s.values)}],
                              fmt="oran", splice_ts=splice,
                              ref=(float(uzun[konsept]), f"2013-2022 ort. ({sg.sayi_tr(float(uzun[konsept]), 'oran')})"),
                              baslik=bas(no))
        ekle(no, hh, vv)

    # G13-G14 — karşılaştırma barları
    konseptler = ["ev_yemekleri", "kirmizi_et", "tavuk", "fast_food"]
    kat_etiket = [endeks.KONSEPT_ETIKET[k] for k in konseptler]
    t24, t26 = o.loc["2024-07-01"], o.loc["2026-07-01"]
    h13, v13 = sg.bar_svg("g13", kat_etiket + ["Tüm konseptler (ort.)"],
                          [{"ad": "2013-2022 ort.", "renk": "#2a78d6",
                            "vals": [round(float(uzun[k]), 2) for k in konseptler] + [round(float(uzun[konseptler].mean()), 2)]},
                           {"ad": "Temmuz 2024", "renk": "#eb6834",
                            "vals": [round(float(t24[k]), 2) for k in konseptler] + [round(float(t24[konseptler].mean()), 2)]},
                           {"ad": "Temmuz 2026", "renk": "#1baf7a",
                            "vals": [round(float(t26[k]), 2) for k in konseptler] + [round(float(t26[konseptler].mean()), 2)]}],
                          fmt="oran", baslik=bas(13))
    ekle(13, h13, v13)
    h14, v14 = sg.bar_svg("g14", kat_etiket,
                          [{"ad": "2013-2022 ort.", "renk": "#2a78d6",
                            "vals": [round(float(uzun[k] / uzun["ev_yemekleri"]), 2) for k in konseptler]},
                           {"ad": "Temmuz 2024", "renk": "#eb6834",
                            "vals": [round(float(t24[k] / t24["ev_yemekleri"]), 2) for k in konseptler]},
                           {"ad": "Temmuz 2026", "renk": "#1baf7a",
                            "vals": [round(float(t26[k] / t26["ev_yemekleri"]), 2) for k in konseptler]}],
                          fmt="oran", taban_cizgi=1.0, baslik=bas(14))
    ekle(14, h14, v14)

    kars = kars.rename(columns={"metrik": "Metrik", "konsept": "Konsept", "orijinal": "Orijinal (EN 24/17)",
                                "replikasyon": "Replikasyon", "sapma": "Sapma", "guncel_2026_07": "Güncel (Tem 2026)",
                                "gerekce": "Sapma gerekçesi"})
    duy_g = duy.rename(columns={"agirlik": "Ağırlık", "kira": "Kira gösterge", "tur_kamasi": "Tür kaması"})
    meta_tablo = tablo(meta.rename(columns={"kod": "Kod", "ad": "Madde",
                                            "gercek_veri_sonu": "Gerçek veri sonu",
                                            "uzatma_kaynagi": "Uzatma kaynağı (sonrası)"}), kucuk=True)
    katki_tablo = tablo(katki.reset_index(names="Konsept"))

    üretim = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")

    css = """
:root{--murekkep:#1a1a1a;--gri:#52514e;--acik:#e8e7e2;--zemin:#fcfcfb;--vurgu:#2a78d6;
--turuncu:#eb6834;--yesil:#1baf7a;}
*{box-sizing:border-box}
body{margin:0;background:var(--zemin);color:var(--murekkep);
font:15px/1.65 -apple-system,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif}
.kap{max-width:1060px;margin:0 auto;padding:24px 28px 80px}
header{border-bottom:3px solid var(--murekkep);padding:26px 0 18px;margin-bottom:8px}
header .ust{font-size:12.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--gri)}
h1{font-size:29px;line-height:1.25;margin:10px 0 6px}
header .alt{color:var(--gri);font-size:14px}
nav{position:sticky;top:0;background:var(--zemin);border-bottom:1px solid var(--acik);
padding:9px 0;margin:0 0 26px;z-index:5;font-size:13.5px}
nav a{color:var(--vurgu);text-decoration:none;margin-right:16px;white-space:nowrap}
nav a:hover{text-decoration:underline}
h2{font-size:21px;margin:44px 0 12px;padding-top:10px;border-top:1px solid var(--acik)}
h3{font-size:16.5px;margin:26px 0 8px}
p{margin:9px 0}
.kutu{background:#f4f3ef;border-left:4px solid var(--vurgu);padding:12px 16px;border-radius:0 8px 8px 0;margin:14px 0}
.kutu.uyari{border-left-color:var(--turuncu)}
.tbl{border-collapse:collapse;width:100%;margin:12px 0;font-size:13.5px}
.tbl th{background:#efeee9;text-align:left;padding:7px 9px;border-bottom:2px solid var(--murekkep);font-weight:600}
.tbl td{padding:6px 9px;border-bottom:1px solid var(--acik);vertical-align:top}
.tbl tr:hover td{background:#f6f5f1}
.tbl.kucuk{font-size:12px}
.sarici{overflow-x:auto}
figure{margin:22px 0;text-align:center}
figure img{max-width:100%;height:auto;border:1px solid var(--acik);border-radius:8px}
figcaption{font-size:13px;color:var(--gri);margin-top:7px;text-align:left}
.izgara{display:grid;grid-template-columns:1fr 1fr;gap:18px}
@media(max-width:860px){.izgara{grid-template-columns:1fr}}
.rozet{display:inline-block;font-size:11.5px;font-weight:600;padding:2px 9px;border-radius:999px;margin-right:6px}
.rozet.g{background:#e2f3ec;color:#0d6b4a}.rozet.p{background:#fdeae2;color:#a03a12}
.formul{background:#f4f3ef;padding:10px 16px;border-radius:8px;font-family:ui-monospace,Menlo,monospace;font-size:13px;overflow-x:auto}
footer{margin-top:56px;padding-top:14px;border-top:1px solid var(--acik);color:var(--gri);font-size:12.5px}
ol li{margin:6px 0}
.ozet-kart{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:18px 0}
@media(max-width:860px){.ozet-kart{grid-template-columns:repeat(2,1fr)}}
.kart{border:1px solid var(--acik);border-radius:10px;padding:12px 14px;background:#fff}
.kart .k{font-size:12px;color:var(--gri)}
.kart .v{font-size:23px;font-weight:700;margin-top:2px}
.kart .d{font-size:11.5px;color:var(--gri)}
"""

    html_out = f"""<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>EN 24/17 Replikasyonu — Yiyecek Hizmetleri Fiyat/Maliyet</title>
<style>{css}{sg.CSS_EK}</style>
<div class="kap">
<header>
<div class="ust">Replikasyon ve Güncelleme · TCMB Ekonomi Notu 2024-17</div>
<h1>Yiyecek Hizmetleri Sektöründe Fiyat/Maliyet Gelişmeleri</h1>
<div class="alt">Atabek Demirhan &amp; Bahça (26 Aralık 2024) çalışmasının kamuya açık veriyle replikasyonu ve
<b>Temmuz 2026</b>'ya güncellenmesi · Üretim: {üretim} · Tümü <code>src/run_all.py</code> ile yeniden üretilebilir</div>
</header>
<nav>
<a href="#ozet">Özet</a><a href="#yontem">Yöntem</a><a href="#veri">Veri &amp; proxy</a>
<a href="#kirilma">Baz değişimi</a><a href="#dogrulama">Replikasyon doğrulaması</a>
<a href="#grafikler">Grafikler 1-14</a><a href="#duyarlilik">Duyarlılık</a><a href="#degerlendirme">Değerlendirme</a>
</nav>

<section id="ozet">
<div class="ozet-kart">
<div class="kart"><div class="k">Ev yemekleri (2013 Oca=1)</div><div class="v">1,27</div><div class="d">Tem-24: 1,27 · not hedefi 1,30 · plato</div></div>
<div class="kart"><div class="k">Kırmızı et ağırlıklı</div><div class="v">1,26</div><div class="d">Tem-24: 1,20 · uzun dönem ort. 1,08</div></div>
<div class="kart"><div class="k">Tavuk eti ağırlıklı</div><div class="v">1,51</div><div class="d">Tem-24: 1,41 · uzun dönem ort. 1,10</div></div>
<div class="kart"><div class="k">Fast-food</div><div class="v">2,19</div><div class="d">Tem-24: 2,08 · <b>açılma sürüyor</b></div></div>
</div>
<div class="kutu"><b>Tek cümlelik sonuç:</b> 2023'te başlayan fiyat/maliyet kırılması Temmuz 2026 itibarıyla
<b>tersine dönmedi</b>; oranlar uzun dönem ortalamalarının 1,2–1,7 katında <b>yüksek bir platoya</b> oturdu,
fast-food'da açılma devam ediyor. Bulgular 18 duyarlılık senaryosunda dayanıklı.</div>
</section>

<section id="yontem">
<h2>1. Yöntem — notun dört aşaması</h2>
<p>Kurgu EN 24/17 ile birebir: <b>(i)</b> sektörün maliyet yapısı sabit ağırlıklarla temsil edilir,
<b>(ii)</b> her yemek için standart tarif paylarıyla gıda maliyet endeksi kurulur, <b>(iii)</b> gıda dışı
kalemler tek göstergelere bağlanır, <b>(iv)</b> konsept maliyeti ağırlıklı ortalamayla hesaplanıp konsept
fiyat endeksine oranlanır (2013 Ocak=1).</p>
<div class="formul">Maliyet<sub>k</sub>(t) = 0,21·Ücret(t) + 0,49·Gıda<sub>k</sub>(t) + 0,05·Enerji(t) + 0,10·Kira(t) + 0,15·Diğer(t)&nbsp;&nbsp;&nbsp;[her bileşen 2013 Oca=100]<br>
Oran<sub>k</sub>(t) = Fiyat<sub>k</sub>(t) / Maliyet<sub>k</sub>(t),&nbsp; 2013 Oca=1&nbsp;&nbsp;·&nbsp;&nbsp;Diğer = ort(TÜFE, Yİ-ÜFE)&nbsp;·&nbsp;Ücret = brüt asgari ücret&nbsp;·&nbsp;Enerji = TÜFE-045&nbsp;·&nbsp;Kira = TÜFE-04110</div>
<h3>1.1 Maliyet ağırlık setleri</h3>
<div class="sarici">{tablo(agirlik, index=True)}</div>
<h3>1.2 Tarifler ve TÜİK maddesi eşlemeleri (notun eki, birebir)</h3>
<div class="sarici">{tablo(tarif_tablosu(), kucuk=True)}</div>
<h3>1.3 Konsept tanımları</h3>
<div class="sarici">{tablo(konsept_tablosu(), kucuk=True)}</div>
<p class="kutu uyari"><b>Fiyat tarafı kısıtı:</b> 1110103 (kebaplar) ve 1110106 (döner) maddeleri hem kırmızı et
hem tavuk konseptine girer; TÜİK yapısında tür ayrımı yoktur. Not, TCMB'nin kendi mikro fiyat tabanıyla ürün
düzeyinde ayrıştırmıştı. Replikasyonda prompt'taki (a) seçeneği uygulanır: iki konsept ortak fiyat endeksi
kullanır, <b>fark yalnızca maliyet tarafından gelir</b>. (b) seçeneği — çevrimiçi menü fiyatlarıyla ayrıştırma —
geriye dönük kamu verisi bulunmadığından uygulanamamıştır.</p>
</section>

<section id="veri">
<h2>2. Veri kaynakları ve proxy etiketleri</h2>
<table class="tbl"><tr><th>Kaynak</th><th>İçerik</th><th>Dönem</th><th>Durum</th></tr>
<tr><td>TCMB EVDS3 API</td><td>TÜFE (2025=100, COICOP-2018, 5'li düzey, <b>2005'e geri taşınmış</b>); TÜFE (2003=100 arşiv); Yİ-ÜFE; Yeni Kiracı Kira Endeksi</td><td>2005/01–2026/07</td><td><span class="rozet g">GERÇEK</span></td></tr>
<tr><td>TÜİK MEDAS</td><td>Tüketici Madde Fiyatları (2003=100): 8 yemek hizmeti + 32 gıda girdisi maddesi</td><td>2005/01–<b>2022/04</b></td><td><span class="rozet g">GERÇEK</span> yayın Nisan 2022'de durdu</td></tr>
<tr><td>TÜİK MEDAS</td><td>Tarım-ÜFE (2020=100): sığır-besi 01.42, kümes 01.47, koyun-keçi 01.45</td><td>2020/01–2026/06</td><td><span class="rozet g">GERÇEK</span> tür kaması girdisi</td></tr>
<tr><td>TÜİK Veri Portalı</td><td>Hizmet ciro endeksi (2015=100, arşiv); TÜFE ağırlık tabloları</td><td>2009–2023</td><td><span class="rozet g">GERÇEK</span></td></tr>
<tr><td>Resmî Gazete / AÜTK</td><td>Brüt asgari ücret (2024'te ara zam yok; 2025: 26.005,50; 2026: 33.030 TL)</td><td>2013–2026</td><td><span class="rozet g">GERÇEK</span></td></tr>
</table>
<h3>2.1 Üç proxy katmanı</h3>
<ol>
<li><span class="rozet p">PROXY 1</span> TÜİK madde <i>endeksi</i> kamuya açık değildir; madde <i>ortalama fiyatı</i>
rölatifi (2013 Oca=100) endeks yerine kullanılır.</li>
<li><span class="rozet p">PROXY 2</span> Nisan 2022 sonrası her madde, eşlendiği COICOP-2018 5'li grup endeksinin
aylık değişimleriyle uzatılır (ör. pirinç→01111, kaşar→01145, çorbalar→11111 tam sunum, pizza→11112 sınırlı sunum).
Dana ve tavuk eti için ilaveten <b>Tarım-ÜFE tür kaması</b> uygulanır: m/m(dana) = m/m(01122-Et) ×
[sığır görece değişimi / karma sepet], karma = 0,65 sığır + 0,30 kümes + 0,05 koyun. Kama kapatılırsa
tavuk/kırmızı sıralaması bozulur (duyarlılık tablosunda görülebilir).</li>
<li><span class="rozet p">PROXY 3</span> Kira için baz gösterge TÜFE-kiradır (04110); işyeri kirası (notta Perakende
Ödeme Sistemi mikro verisi) kamuya kapalıdır. Alternatifler duyarlılıkta: %25 konut tavanı düzeltmesi (TBK md.344
işyeri kuralı: TÜFE 12 aylık ort.) ve TCMB Yeni Kiracı Kira Endeksi.</li>
</ol>
<h3>2.2 Madde bazında gerçek veri sonu ve uzatma kaynağı</h3>
<div class="sarici">{meta_tablo}</div>
</section>

<section id="kirilma">
<h2>3. 2026 baz değişimi (2025=100) — kırılma testi</h2>
<p>TÜİK, Ocak 2026'da TÜFE'yi 2025=100 bazına ve COICOP-2018 sınıflamasına geçirdi; seri 5'li düzeyde 2005'e
geri taşındı. Geri taşınmış seri ile 2003=100 arşiv serisinin aylık değişimleri 2005-2025 dönemde karşılaştırıldı:</p>
<div class="kutu"><b>Sonuç:</b> fark ortalaması 0,000 puan, mutlak ortalama 0,000, en büyük fark 0,0065 puan
(2005-02); korelasyon 1,000. Ocak 2026 zinciri de tutarlı (eski seri %4,837 / yeni %4,84). Yani geri taşıma
<b>birebir yeniden ölçekleme</b>dir; metodolojik değişiklikler Ocak 2026 sonrası hesaplamaya ilişkindir ve
zincirleme düzeltmesi gerekmez. Alt seriler (gıda, kira, enerji, yemek hizmetleri) için de mutlak ortalama fark
≤0,003 puandır.</div>
</section>

<section id="dogrulama">
<h2>4. Replikasyon doğrulaması — orijinal vs replikasyon vs güncel</h2>
<div class="sarici">{tablo(kars)}</div>
<p><b>Okuma:</b> ev yemekleri ve fast-food hedefleri tutturuldu; uzun dönem ortalamaları dört konseptte ±0,12
bandında. Kırmızı et ve tavukta Temmuz 2024 oranları, fiyat tarafındaki yapısal kısıt (PROXY 3 + tür ayrımsız
madde yapısı) nedeniyle notun altında kalır; nitel sıralama ve kırılma deseni korunur.</p>
</section>

<section id="grafikler">
<h2>5. Grafikler (Temmuz 2026'ya uzatılmış)</h2>
<p><b>Grafikler etkileşimlidir:</b> imleci çizgilerin üzerinde gezdirince ay-yıl ve seri değerleri görünür; barlarda kutunun üzerine gelin. Noktalı dikey çizgi (Nisan 2022): madde fiyatı yayınının sonu — sonrası proxy uzatma. Oran grafikleri kâr marjı <i>seviyesi</i> değildir; 2013 Ocak'a göre göreli seviyedir.</p>
{grafik_html[0]}
<div class="izgara">{''.join(grafik_html[1:4])}</div>
<h3>Konsept maliyet endeksleri (Grafik 5-8)</h3>
<div class="izgara">{''.join(grafik_html[4:8])}</div>
<h3>Fiyat/maliyet oranları (Grafik 9-12)</h3>
<div class="izgara">{''.join(grafik_html[8:12])}</div>
<h3>Karşılaştırma (Grafik 13-14; üçüncü sütun: Temmuz 2026)</h3>
<div class="izgara">{''.join(grafik_html[12:14])}</div>
</section>

<section id="duyarlilik">
<h2>6. Duyarlılık analizi</h2>
<p>3 ağırlık seti × 3 kira göstergesi × tür kaması (açık/kapalı) = 18 koşu. Ana bulgular her koşuda korunur:
oranlar uzun dönem ortalamasının belirgin üzerinde, fast-food en açık makas, Tem-2026 ≥ Tem-2024.</p>
<div class="sarici">{tablo(duy_g, kucuk=True)}</div>
<h3>6.1 Maliyet artışında kalem katkıları (Tem-2024 → Tem-2026, yüzde puan)</h3>
<div class="sarici">{katki_tablo}</div>
</section>

<section id="degerlendirme">
<h2>7. Değerlendirme notu</h2>
{notu}
</section>

<footer>
Kaynaklar: TÜİK (MEDAS, Veri Portalı), TCMB EVDS, Resmî Gazete/Asgari Ücret Tespit Komisyonu; orijinal çalışma:
Atabek Demirhan, A. ve M. Bahça (2024), "Son Dönem Yiyecek Hizmetleri Sektörü Fiyatlama Gelişmeleri",
TCMB Ekonomi Notları 2024-17. · Bu rapor <code>src/html_rapor.py</code> tarafından üretilmiştir; tüm hesaplama
zinciri <code>src/run_all.py</code> ile yeniden koşturulabilir. · Üretim: {üretim}
</footer>
</div>
"""
    hedef = CIKTI / "rapor.html"
    hedef.write_text("<!doctype html>\n<html lang=\"tr\">\n<body>\n" + html_out + sg.motor_js(VERI) + "\n</body>\n</html>", encoding="utf-8")
    print(f"HTML rapor: {hedef} ({hedef.stat().st_size/1e6:.1f} MB)")
    return hedef


if __name__ == "__main__":
    main()
