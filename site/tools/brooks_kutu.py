#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Brooks indikatörünün DURUM KUTUSU — okurun TradingView'de göreceği hâliyle.

NEDEN VAR. Sayfa kutuyu düz yazıyla anlatıyordu ve indikatörü kurmamış bir
okur onu HİÇ görmüyordu. Oysa "bu indikatör nasıl kullanılır" sorusunun en
doğrudan cevabı kutudur: okuma sırası orada dizilidir, veto orada görünür,
kurulum orada en sonda durur.

UYDURMA DEĞİL. Kutunun her satırı `brooks_referans`ın GERÇEK barlarda koşan
çıktısından yazılır — Pine'daki satır sırası, koşulları ve renkleri birebir.
Elle yazılmış bir ekran görüntüsü, kod değiştiği gün sessizce yalan söylerdi.

ÇIKTI: site/public/indikatorler/08_durum_kutusu.html — saf HTML/CSS parçası.
Plotly DEĞİL ve iframe'e de girmiyor: çizilen şey bir grafik değil ARAYÜZ.
Sabit yükseklikli bir çerçeve onu dar ekranda kendi içinde kaydırır ve okur
kutunun nerede bittiğini göremez; parça sayfaya doğrudan akar.

    python3 site/tools/brooks_kutu.py
"""
from __future__ import annotations

import html
import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
SITE = BURASI.parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(BURASI))
sys.path.insert(0, str(SITE / "public" / "indikatorler"))
sys.path.insert(0, str(SITE.parent))

import brooks_ornek as O                                          # noqa: E402
import brooks_referans as R                                       # noqa: E402

CIKTI = SITE / "public" / "indikatorler"

# Pine'daki cMurekkep / cClaret / cMavi / cGri ile AYNI. Okur ekranda gördüğü
# rengi sayfada bulamazsa kutu bir şey öğretmez.
MUREKKEP = "#1a1a1a"
CLARET = "#8c2f39"
MAVI = "#2f5d8c"
GRI = "#8a8a8a"

# Pine'ın girdi varsayılanları — kutu onlarla koşar, başka bir eşikle değil.
GAP_ESIK = 20
MOMENTUM_BAR = 6
TRENDLESME_ESIK = 3


def _kaynaklar() -> dict:
    kay = [O.bar_oku(y) for y in sorted((SITE / "public" / "teknik").glob("*.html"))]
    return {k.anahtar: k for k in kay if O.govde_kunyesi(k.seri)["gecti"]}


# ═══════════════════════════════════════════════════════════════════════════
#  Kutu satırları — brooks-fiyat-hareketi.pine'ın 553-613. satırlarının eşi.
#  Sıra, koşul ve renk ORADAN kopyalanır; burada yeniden KARAR verilmez.
# ═══════════════════════════════════════════════════════════════════════════
def fiyat_kutusu(d: dict) -> list[tuple]:
    """(tur, no, ad, deger, renk) — tur: 'baslik' | 'satir'."""
    ai = d["always_in"]
    yf = d["yon_filtresi"]
    sat: list[tuple] = [("baslik", "", "OKUMA SIRASI", "", GRI)]

    sat.append(("satir", "①", "Rejim", "alt panele bak", GRI))

    ai_metin = ai if ai in ("LONG", "SHORT") else "henüz belirsiz"
    sat.append(("satir", "②", "Always-in", ai_metin,
                MAVI if ai == "LONG" else CLARET if ai == "SHORT" else GRI))

    yalniz_al, yalniz_sat = yf == "yalnız AL", yf == "yalnız SAT"
    yasak = ("yalnız AL — short arama" if yalniz_al else
             "yalnız SAT — long arama" if yalniz_sat else "serbest")
    sat.append(("satir", "③", "Yön filtresi", yasak,
                MAVI if yalniz_al else CLARET if yalniz_sat else GRI))

    kb = sum(d["nitelik_boga"].values())
    ka = sum(d["nitelik_ayi"].values())
    kur_boga = d["donus_boga"] and kb > 0 and not yalniz_sat
    kur_ayi = d["donus_ayi"] and ka > 0 and not yalniz_al
    if kur_boga and kur_ayi:
        kur = f"iki yönlü — {kb}/4 boğa · {ka}/4 ayı"
    elif kur_boga:
        kur = f"{kb}/4 boğa"
    elif kur_ayi:
        kur = f"{ka}/4 ayı"
    else:
        kur = "kurulum yok"
    hizali = (kur_boga and ai == "LONG") or (kur_ayi and ai == "SHORT")
    ek = ("  ✓ yönle hizalı" if hizali
          else "  ⚠ yönle hizasız" if (kur_boga or kur_ayi) else "")
    sat.append(("satir", "④", "Kurulum", kur + ek,
                MAVI if hizali else CLARET if (kur_boga or kur_ayi) else GRI))

    # ── BU BAR ──
    sat.append(("baslik", "", "BU BAR", "", GRI))
    sinif = d["bar_sinifi"]
    sinif_metin = sinif + (" · gövde güçlü" if d["govde_gucu"] else "")
    if d["tirasli"]:
        sinif_metin += " · " + d["tirasli"]
    sat.append(("satir", "", "Sınıf", sinif_metin, MUREKKEP))

    ky = d["kapanis_yeri"]
    sat.append(("satir", "", "Kapanışın yeri", f"%{round(ky * 100)}",
                MAVI if ky > 0.5 else CLARET if ky < 0.5 else GRI))

    sat.append(("satir", "", "Boy · mikro",
                f"{d['bar_boyu'] or '—'} · {d['mikro_cift'] or '—'}", MUREKKEP))

    sat.append(("satir", "", "Orta nokta ölçütü",
                "boğa geçti" if d["orta_nokta_boga"] else
                "ayı geçti" if d["orta_nokta_ayi"] else "—",
                MAVI if d["orta_nokta_boga"] else
                CLARET if d["orta_nokta_ayi"] else GRI))

    # ── BAĞLAM ──
    sat.append(("baslik", "", "BAĞLAM", "", GRI))
    c = d["cevirme"]
    sat.append(("satir", "", "Çevirme (kap·uç)",
                f"{c['kapanis']} · {c['uc']}  {d['cevirme_kademesi']}", MUREKKEP))

    t = d["trendlesme"]
    trendlesiyor = abs(t["kapanis"]) >= TRENDLESME_ESIK
    sat.append(("satir", "", "Trendleşme k·z·d",
                f"{t['kapanis']} · {t['zirve']} · {t['dip']}"
                + ("  ⚑" if trendlesiyor else ""), MUREKKEP))

    gap = d["gap_bar"]
    ters = d["ters_iki_kapanis"]
    sat.append(("satir", "", "Ortalama",
                f"gap {gap}" + (" ⚑" if gap >= GAP_ESIK else "")
                + (" · TERS İKİ KAPANIŞ" if ters else ""),
                CLARET if ters else MUREKKEP))

    sat.append(("satir", "", "Sayım · mikro kanal",
                f"{d['bar_sayimi']} · {d['mikro_kanal']} bar", MUREKKEP))

    # ── KALIP · UYARI — yalnız SÖYLEYECEK BİR ŞEY VARKEN ──
    parca = []
    if d["kalip"]:
        parca.append(d["kalip"] + " · kırılım modu")
    elif d["govde_ii"]:
        parca.append("yalnız gövdeler ii")
    if d["iki_barlik"]:
        parca.append(d["iki_barlik"])
    my = d["momentum_yoklugu"]
    if abs(my) >= MOMENTUM_BAR:
        parca.append(f"{abs(my)} bardır {'boğa' if my > 0 else 'ayı'} kapanışı yok")
    kalip_metin = " · ".join(parca)
    iptal = d["iptal"]["iptal"] or "—"
    if kalip_metin or iptal != "—":
        sat.append(("baslik", "", "KALIP · UYARI", "", GRI))
        sat.append(("satir", "", kalip_metin or "—", iptal,
                    CLARET if iptal != "—" else MUREKKEP))
    return sat


def rejim_kutusu(o: dict) -> list[tuple]:
    """brooks-rejim-panosu.pine'ın durum tablosunun eşi."""
    n = o["n"]
    ad = "BANT" if n >= 4 else "trend" if n <= 1 else "ara"
    renk = CLARET if n >= 4 else MAVI if n <= 1 else GRI
    not_ = ("bar sayımına dayalı stop girişi yok · uçlarda fade" if n >= 4 else
            "geri çekilme kurulumları geçerli · fade edilmez" if n <= 1 else
            "pano karar vermez · hangi tarafa yakın olduğunu söyler")
    i = o["isaret"]
    return [
        ("hukum", "① REJİM", ad, f"{n}/5", renk),
        ("not", not_, "", "", renk),
        ("baslik", "Ölçü · dersin Şekil 30'u", "bu pencere", "bant?", GRI),
        ("satir", "Örtüşme oranı  (0,725)", f"{o['ortusme_oran']:.3f}".replace(".", ","),
         "✓" if i["ortusme"] else "—", CLARET if i["ortusme"] else GRI),
        ("satir", "Doji oranı  (0,314)", f"{o['doji_oran']:.3f}".replace(".", ","),
         "✓" if i["doji"] else "—", CLARET if i["doji"] else GRI),
        ("satir", "Ortalama kesişme  (17)", str(o["kesisme"]),
         "✓" if i["kesisme"] else "—", CLARET if i["kesisme"] else GRI),
        ("satir", "Net / aralık  (0,037)", f"{o['net_aralik']:.3f}".replace(".", ","),
         "✓" if i["net"] else "—", CLARET if i["net"] else GRI),
        ("satir", "Azami ardışık trend barı", str(o["azami_dizi"]),
         "✓" if i["dizi"] else "—", CLARET if i["dizi"] else GRI),
    ]


# ═══════════════════════════════════════════════════════════════════════════
#  HTML
# ═══════════════════════════════════════════════════════════════════════════
STIL = """
.bkutu{--bk-murekkep:#1a1a1a;--bk-gri:#8a8a8a;--bk-kagit:#fff;--bk-cizgi:#d8d4cd;--bk-zemin:#f6f4f0;
  position:relative;left:50%;transform:translateX(-50%);
  width:min(1120px,calc(100vw - 32px));
  margin:2.2em 0;padding:16px 14px 18px;border:1px solid var(--bk-cizgi);background:var(--bk-kagit);
  font:12px/1.45 "IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--bk-murekkep)}
.bkutu *{box-sizing:border-box}
.bkutu .bk-h1{margin:0 0 2px;font-size:15px;font-weight:700;font-family:inherit}
.bkutu .bk-alt{margin:0 0 16px;color:var(--bk-gri);font-size:11.5px;max-width:92ch}
.bkutu .izgara{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}
@media(max-width:980px){.bkutu .izgara{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:620px){.bkutu .izgara{grid-template-columns:1fr}}
.bkutu .sut{min-width:0}
.bkutu .durum{font-size:11px;font-weight:700;letter-spacing:.04em;margin:0 0 2px}
.bkutu .kunye{color:var(--bk-gri);font-size:10.5px;margin:0 0 8px;min-height:2.6em}
.bkutu table{width:100%;border-collapse:collapse;border:1px solid var(--bk-cizgi);
  background:var(--bk-kagit);table-layout:fixed;margin:0;font-size:inherit}
.bkutu td{padding:3px 6px;vertical-align:top;overflow-wrap:break-word;word-break:normal;hyphens:none;border:0;font-size:inherit}
.bkutu tr.baslik td{background:var(--bk-zemin);font-weight:700;font-size:10.5px;
  letter-spacing:.05em;color:var(--bk-murekkep)}
.bkutu tr.hukum td{background:var(--bk-zemin);font-weight:700}
.bkutu td.no{width:15px;text-align:center;color:var(--bk-gri)}
.bkutu td.ad{width:42%;color:var(--bk-gri)}
.bkutu td.dg{font-weight:600}
.bkutu td.sag{text-align:right}
.bkutu td.bant{width:34px;text-align:center;font-weight:700}
.bkutu .etiket{margin:14px 0 5px;font-size:10.5px;letter-spacing:.06em;color:var(--bk-gri);
  font-weight:700;text-transform:uppercase}
.bkutu .not{color:var(--bk-gri);font-size:10.5px;padding:3px 5px;border:1px solid var(--bk-cizgi);
  border-top:0;background:var(--bk-kagit)}
.bkutu .aciklama{margin:16px 0 0;padding-top:11px;border-top:1px solid var(--bk-cizgi);
  color:var(--bk-gri);font-size:11px;max-width:104ch}
.bkutu .aciklama b{color:var(--bk-murekkep)}
"""


def _fiyat_tablo(sat: list[tuple]) -> str:
    p = ['<table>']
    for tur, no, ad, dg, renk in sat:
        if tur == "baslik":
            p.append(f'<tr class="baslik"><td colspan="3">{html.escape(ad)}</td></tr>')
        else:
            p.append(
                f'<tr><td class="no">{html.escape(no)}</td>'
                f'<td class="ad">{html.escape(ad)}</td>'
                f'<td class="dg" style="color:{renk}">{html.escape(dg)}</td></tr>')
    p.append('</table>')
    return "".join(p)


def _rejim_tablo(sat: list[tuple]) -> str:
    p, not_ = ['<table>'], ""
    for tur, a, b, c, renk in sat:
        if tur == "hukum":
            p.append(f'<tr class="hukum"><td class="ad" style="color:{renk}">{html.escape(a)}</td>'
                     f'<td class="dg sag" style="color:{renk}">{html.escape(b)}</td>'
                     f'<td class="bant" style="color:{renk}">{html.escape(c)}</td></tr>')
        elif tur == "not":
            not_ = f'<div class="not" style="color:{renk}">{html.escape(a)}</div>'
        elif tur == "baslik":
            p.append(f'<tr class="baslik"><td>{html.escape(a)}</td>'
                     f'<td class="sag">{html.escape(b)}</td>'
                     f'<td class="bant">{html.escape(c)}</td></tr>')
        else:
            p.append(f'<tr><td class="ad">{html.escape(a)}</td>'
                     f'<td class="dg sag">{html.escape(b)}</td>'
                     f'<td class="bant" style="color:{renk}">{html.escape(c)}</td></tr>')
    p.append('</table>')
    return "".join(p) + not_


def _an(iso: str) -> str:
    g, sa = iso[:10], iso[11:16]
    return f"{g[8:10]}.{g[5:7]}.{g[:4]}" + (f" {sa}" if sa else "")


def kutu_figuru(durumlar: list[dict], yol: Path) -> Path:
    sut = []
    for d in durumlar:
        sut.append(
            f'<div class="sut">'
            f'<p class="durum">{html.escape(d["baslik"])}</p>'
            f'<p class="kunye">{html.escape(d["kunye"])}</p>'
            f'<div class="etiket">Fiyat paneli</div>{_fiyat_tablo(d["fiyat"])}'
            f'<div class="etiket">Alt panel · rejim panosu</div>{_rejim_tablo(d["rejim"])}'
            f'</div>')
    govde = (
        '<p class="bk-h1">Durum kutusu üç gerçek barda</p>'
        '<p class="bk-alt">TradingView\'de grafiğin köşesinde duran kutu budur. Satırlar '
        'okuma sırasına göre dizilidir: ① rejim → ② yön → ③ yasak → ④ kurulum. '
        'Kurulum en sondadır ve bu bilinçlidir — gözü ilk oraya giden okur kararı '
        'çoktan vermiş olur. Aşağıdaki üç sütun uydurma değil: her satır, adı yazan '
        'barda ölçüm katmanının gerçekten ürettiği değerdir.</p>'
        f'<div class="izgara">{"".join(sut)}</div>'
        '<p class="aciklama"><b>Üç sütun, üç ayrı sonuç — ve ikisi HAYIR.</b> '
        'Soldaki sütunda üç katman da aynı yöne bakıyor: rejim trend, always-in '
        'long, kurulum boğa ve hizalı. Ortadakinde kurulum dolu ve kalitesi yüksek, '
        'ama ② ile ④ ters yöne bakıyor — yani barı görürsünüz, etiketi görürsünüz, '
        've almazsınız. Sağdakinde kurulum hizalı olduğu hâlde alt panel BANT diyor: '
        'bu kez itirazı yön değil REJİM ediyor ve dersin en pahalı hatası tam burada '
        'doğar — doğru kurulumu yanlış günde almak. Bir kurulumun üç ayrı sebeple '
        'düşebileceğini kutu tek bakışta gösterir. '
        '<b>Renk sözleşmesi.</b> Mavi boğa tarafı, kızıl ayı tarafı ya da bir uyarı, '
        'gri "karar yok" demektir; ekranda gördüğünüz renk budur. '
        '<b>Eksik bölüm bir kusur değil:</b> "Kalıp · uyarı" ancak söyleyecek bir şey '
        'varken çıkar — her barda boş bir satır basmak, kutuyu okunur yapmak için '
        'harcanan yeri geri alırdı.</p>')
    # Tek çıktı, iki kullanım: `<style>` kapsanmış olduğu için parça hem
    # sayfaya `set:html` ile akar, hem de dosya tek başına açıldığında görünür.
    yol.write_text(f'<style>{STIL}</style>\n<div class="bkutu">{govde}</div>\n',
                   encoding="utf-8")
    return yol


def _durum(kay: dict, anahtar: str, i: int, baslik: str) -> dict:
    s = kay[anahtar].seri
    fp = R.FiyatPaneli(s)
    d = fp.durum(i)
    o = R.RejimPanosu(s).olcu(i)
    ad = O.ENSTRUMAN_AD.get(anahtar.rsplit("-", 1)[0], anahtar)
    dilim = O.DILIM_AD.get(anahtar.rsplit("-", 1)[1], "")
    return {
        "baslik": baslik,
        "kunye": f"{ad} · {dilim} · {_an(s.zaman[i])}",
        "fiyat": fiyat_kutusu(d),
        "rejim": rejim_kutusu(o),
    }


# Üç durum GERÇEK barlardan seçildi; indeks ve gün SABİT yazılır, çünkü
# yayımlanmış bir figür her koşuda başka bir barı anlatmamalı. Seçim ölçütü
# koda yazılı: A hizalı ve kalite>=3, B kurulum var ama yönle hizasız,
# C rejim BANT (n>=4). Üçü de aynı enstrümanda, böylece okur kutuyu
# karşılaştırırken enstrüman değişimini de hesaba katmak zorunda kalmıyor.
DURUMLAR = [
    ("xu100-s4", 322, "A · üç katman da evet"),
    ("xu100-s4", 336, "B · kurulum var, yön VETO ediyor"),
    ("xu100-s4", 305, "C · rejim BANT"),
]


def main() -> int:
    kay = _kaynaklar()
    d = [_durum(kay, a, i, b) for a, i, b in DURUMLAR]
    yol = kutu_figuru(d, CIKTI / "08_durum_kutusu.html")
    print(f"{yol.relative_to(SITE.parent)} · {yol.stat().st_size:,} bayt")
    for (a, i, b), x in zip(DURUMLAR, d):
        kur = [s for s in x["fiyat"] if s[2] == "Kurulum"]
        rej = x["rejim"][0]
        print(f"  {b:36s} {x['kunye']}")
        print(f"      kurulum: {kur[0][3] if kur else '—'}")
        print(f"      rejim  : {rej[2]} ({rej[3]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
