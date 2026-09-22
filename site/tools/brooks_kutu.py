#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Brooks indikatörünün DURUM KUTUSU — okurun TradingView'de göreceği hâliyle.

NEDEN VAR. Sayfa kutuyu düz yazıyla anlatıyordu ve indikatörü kurmamış bir
okur onu HİÇ görmüyordu. Oysa "bu indikatör nasıl kullanılır" sorusunun en
doğrudan cevabı kutudur: okuma sırası orada dizilidir, veto orada görünür,
kurulum orada en sonda durur ve emir seviyeleri onun altında.

UYDURMA DEĞİL. Kutunun her satırı `brooks_referans`ın GERÇEK barlarda koşan
çıktısından yazılır — Pine'daki satır sırası, koşulları ve renkleri birebir.
Elle yazılmış bir ekran görüntüsü, kod değiştiği gün sessizce yalan söylerdi.

v2 (15.09.2026). Kutunun ④ satırı artık PAKET adıyla konuşur (kırılım modu ·
bant kenarı · ikinci giriş · başarısız dönüş · dönüş barı — Pine'daki öncelik
sırasıyla tek paket), altına "Emir" satırı geldi (giriş · stop · 1R · 2R),
"Sayım · mikro kanal" satırı "Sayım · bant konumu" oldu ve alt panel GÖRELİ
kipte yazılır: her ölçünün yanında kendi tarihçesindeki sırası, hüküm o
sıradan. Üç örnek bar da göreli kipin tanımlı olduğu yerden seçilir; tarihçe
280 bar ister, o yüzden aday yalnız serinin son kısmındadır.

ÇIKTI: site/public/indikatorler/durum_kutusu.html — saf HTML/CSS parçası.
Plotly DEĞİL ve iframe'e de girmiyor: çizilen şey bir grafik değil ARAYÜZ.
Sabit yükseklikli bir çerçeve onu dar ekranda kendi içinde kaydırır ve okur
kutunun nerede bittiğini göremez; parça sayfaya doğrudan akar.

    python3 site/tools/brooks_kutu.py          # kutuyu yaz
    python3 site/tools/brooks_kutu.py --ara    # üç hikâye için aday barları listele
"""
from __future__ import annotations

import html
import math
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
# Hepsi replikasyonun TEK sabit tablosundan okunur; burada ikinci bir kopya
# tutulsaydı bir gün sessizce ayrışırdı (eşik kapısı Pine ↔ Python'u sınar,
# bu dosyayı sınamaz).
GAP_ESIK = int(R.SABIT_FH["gapEsik"])
MOMENTUM_BAR = int(R.SABIT_FH["momentumBar"])
TRENDLESME_ESIK = int(R.SABIT_FH["trendlesmeEsik"])
# `asgariKalite` bir GÖRÜNÜM girdisidir (etiket eşiği), ölçüm sabiti değil;
# eşik tablosunda durmaz, Pine dosyasından okunur — kutu Pine'ın ④ satırıyla
# aynı eşiği kullanmak zorunda.
ASGARI_KALITE = int(R.pine_sabitleri(SITE / "public" / "indikatorler" / "brooks-fiyat-hareketi.pine")["asgariKalite"])
PENCERE = int(R.SABIT_FH["pencere"])


def _kaynaklar() -> dict:
    kay = [O.bar_oku(y) for y in sorted((SITE / "public" / "teknik").glob("*.html"))]
    return {k.anahtar: k for k in kay if O.govde_kunyesi(k.seri)["gecti"]}


def _ondalik(tick: float) -> int:
    return max(0, -int(math.floor(math.log10(tick)))) if tick > 0 else 2


def _fiyat(v: float, tick: float) -> str:
    """Pine `format.mintick` eşi: tick'in basamağı kadar ondalık, virgülle."""
    return f"{v:.{_ondalik(tick)}f}".replace(".", ",")


# ═══════════════════════════════════════════════════════════════════════════
#  Paket seçimi — brooks-fiyat-hareketi.pine `paketAd` (satır 690–702) eşi.
#  Öncelik: kırılım modu > bant kenarı > ikinci giriş > başarısız dönüş >
#  dönüş barı (kalite ≥ asgari, yasak yok). Sıra ve koşullar ORADAN.
# ═══════════════════════════════════════════════════════════════════════════
def paket_sec(ku: "R.Kurulumlar", i: int) -> dict | None:
    fp = ku.fp
    yf = fp.yon_filtresi(i)
    yalniz_al, yalniz_sat = yf == "yalnız AL", yf == "yalnız SAT"
    kb, ka = fp.kalite(i, True), fp.kalite(i, False)
    km = ku.kirilim(i)
    if km:
        return {"ad": "kırılım modu · " + km["kalip"], "cift": True,
                "alis": km["alis"], "satis": km["satis"]}
    bk = ku.bant_kenari(i)
    if bk:
        return {"ad": "bant kenarı · " + ("alış" if bk["yon"] == 1 else "satış"), "cift": False, **bk}
    ik = ku.ikinci_giris(i)
    # Pine: ikinciBoga … and not yalnizSat · ikinciAyi … and not yalnizAl
    if ik and not ((ik["yon"] == 1 and yalniz_sat) or (ik["yon"] == -1 and yalniz_al)):
        return {"ad": "ikinci giriş · " + ("H2" if ik["yon"] == 1 else "L2"), "cift": False, **ik}
    bd = ku.basarisiz_donus(i)
    # Pine: basarisizBoga = aiLong and ayiDonus and kaliteAyi >= asgariKalite
    if bd and bd["kalite"] >= ASGARI_KALITE:
        if bd["yon"] == 1 and not yalniz_sat:
            return {"ad": "başarısız dönüş · alış", "cift": False, **bd}
        if bd["yon"] == -1 and not yalniz_al:
            return {"ad": "başarısız dönüş · satış", "cift": False, **bd}
    # Pine donusAdayBoga/donusAdayAyi → donusBogaSec/donusAyiSec; backtest'in
    # kuralı: iki aday aynı kalitedeyse EMİR YOK (eski hâl boğayı seçiyordu).
    aday_b = fp.donus_bari(i, True) and kb >= ASGARI_KALITE and not yalniz_sat
    aday_a = fp.donus_bari(i, False) and ka >= ASGARI_KALITE and not yalniz_al
    if aday_b and (not aday_a or kb > ka):
        return {"ad": f"dönüş barı · alış {kb}/4", "cift": False, **ku.donus(i, True)}
    if aday_a and (not aday_b or ka > kb):
        return {"ad": f"dönüş barı · satış {ka}/4", "cift": False, **ku.donus(i, False)}
    return None


def bant_konumu(s: "R.Seri", i: int) -> float:
    """Pine `bantKonum`: son `pencere` barın tavan/tabanı içinde kapanışın yeri."""
    w = PENCERE
    if i + 1 < w:
        return 0.5
    pen = range(i - w + 1, i + 1)
    tavan, taban = max(s.h[j] for j in pen), min(s.l[j] for j in pen)
    return (s.c[i] - taban) / (tavan - taban) if tavan > taban else 0.5


# ═══════════════════════════════════════════════════════════════════════════
#  Kutu satırları — brooks-fiyat-hareketi.pine'ın 756–828. satırlarının eşi.
#  Sıra, koşul ve renk ORADAN kopyalanır; burada yeniden KARAR verilmez.
# ═══════════════════════════════════════════════════════════════════════════
def fiyat_kutusu(d: dict, paket: dict | None, konum: float, tick: float) -> list[tuple]:
    """(tur, no, ad, deger, renk) — tur: 'baslik' | 'satir'."""
    ai = d["always_in"]
    yf = d["yon_filtresi"]
    # Künye Pine ile birebir: kutu KAPANMIŞ bir barı anlatır ve figür de
    # tanımı gereği kapanmış bar üzerinden çizilir (`Seri` kapanmış barlardır).
    sat: list[tuple] = [("baslik", "", "OKUMA SIRASI · son kapanmış bar", "", GRI)]

    sat.append(("satir", "①", "Rejim", "alt panele bak", GRI))

    ai_metin = ai if ai in ("LONG", "SHORT") else "henüz belirsiz"
    sat.append(("satir", "②", "Always-in", ai_metin,
                MAVI if ai == "LONG" else CLARET if ai == "SHORT" else GRI))

    yalniz_al, yalniz_sat = yf == "yalnız AL", yf == "yalnız SAT"
    yasak = ("yalnız AL — short arama" if yalniz_al else
             "yalnız SAT — long arama" if yalniz_sat else "serbest")
    sat.append(("satir", "③", "Yön filtresi", yasak,
                MAVI if yalniz_al else CLARET if yalniz_sat else GRI))

    # ④ PAKET adıyla: Pine satır 771–782.
    kb = sum(d["nitelik_boga"].values())
    ka = sum(d["nitelik_ayi"].values())
    kur_boga = d["donus_boga"] and kb > 0 and not yalniz_sat
    kur_ayi = d["donus_ayi"] and ka > 0 and not yalniz_al
    if paket:
        kur = paket["ad"]
    elif kur_boga and kur_ayi:
        kur = f"dönüş barı iki yönlü — {kb}/4 boğa · {ka}/4 ayı (eşiğin altında)"
    elif kur_boga:
        kur = f"dönüş barı {kb}/4 boğa (eşiğin altında)"
    elif kur_ayi:
        kur = f"dönüş barı {ka}/4 ayı (eşiğin altında)"
    else:
        kur = "kurulum yok"
    tekyon = bool(paket) and not paket["cift"]
    hizali = tekyon and ((paket["yon"] == 1 and ai == "LONG") or (paket["yon"] == -1 and ai == "SHORT"))
    karsi = tekyon and ((paket["yon"] == 1 and ai == "SHORT") or (paket["yon"] == -1 and ai == "LONG"))
    ek = "  ✓ yönle hizalı" if hizali else "  ⚠ yöne KARŞI" if karsi else ""
    sat.append(("satir", "④", "Kurulum", kur + ek, MAVI if hizali else CLARET if karsi else GRI))

    # Emir satırı — Pine 784–788. Kırılım modunda iki giriş, hedef yok.
    if not paket:
        emir = "—"
    elif paket["cift"]:
        emir = f"alış stop {_fiyat(paket['alis'], tick)} · satış stop {_fiyat(paket['satis'], tick)}"
    else:
        risk = abs(paket["giris"] - paket["stop"])
        y = paket["yon"]
        emir = (f"giriş {_fiyat(paket['giris'], tick)} · stop {_fiyat(paket['stop'], tick)}"
                f" · 1R {_fiyat(paket['giris'] + y * risk, tick)}"
                f" · 2R {_fiyat(paket['giris'] + 2 * y * risk, tick)}")
    sat.append(("satir", "", "Emir", emir, GRI if not paket else MUREKKEP))

    # ── BU BAR ──
    sat.append(("baslik", "", "BU BAR", "", GRI))
    sinif = d["bar_sinifi"]
    sinif_metin = sinif + (" · gövde güçlü" if d["govde_gucu"] else "")
    if d["tirasli"]:
        sinif_metin += " · " + d["tirasli"]
    gb = d["govde_boslugu"]
    sinif_metin += " · gövde boşluğu ↑" if gb > 0 else " · gövde boşluğu ↓" if gb < 0 else ""
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

    # SAYAÇ, etiket DEĞİL. Pine satır 810 always-in'in yönü varken HER barda
    # sayacın o anki değerini basar (dörtte kapaklı); `bar_sayimi` ise
    # grafikteki ETİKETİN eşi ve yalnız sayımın ilerlediği barda dolu.
    sat.append(("satir", "", "Sayım · bant konumu",
                f"{d['bar_sayaci']} · bantta %{round(konum * 100)} · mikro kanal {d['mikro_kanal']}",
                MUREKKEP))

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
    """brooks-rejim-panosu.pine'ın durum tablosunun eşi — GÖRELİ kip.

    `o` = `RejimPanosu.olcu_goreli(i)`: değerlerin yanında sıra, hüküm
    sıradan. Pine `f_sira` sırayı " · 0,00" diye ekler, hükmün yanına
    "n/5 g" yazar (g = göreli)."""
    n = o["n"]
    ad = "BANT" if n >= 4 else "trend" if n <= 1 else "ara"
    renk = CLARET if n >= 4 else MAVI if n <= 1 else GRI
    # Pine rejimNot ile birebir (brooks-rejim-panosu.pine, rejimNot).
    not_ = ("uçlarda bant kenarı · ortada emir yok · H2/L2 yalnız uçta" if n >= 4 else
            "geri çekilme kurulumları (H2/L2, dönüş barı) · fade edilmez" if n <= 1 else
            "pano karar vermez · hangi tarafa yakın olduğunu söyler")
    i, s = o["isaret"], o["sira"]

    def sira(ad_: str) -> str:
        return " · " + f"{s[ad_]:.2f}".replace(".", ",")

    def satir(etiket: str, deger: str, anahtar: str, isaret: str) -> tuple:
        return ("satir", etiket, deger + sira(anahtar),
                "✓" if i[isaret] else "—", CLARET if i[isaret] else GRI)

    return [
        ("hukum", "① REJİM", ad, f"{n}/5 g", renk),
        ("not", not_, "", "", renk),
        ("baslik", "Ölçü · (Şekil 30 değeri)", "değer · sıra", "bant?", GRI),
        satir("Örtüşme oranı  (0,725)", f"{o['ortusme_oran']:.3f}".replace(".", ","), "ortusme_oran", "ortusme"),
        satir("Doji oranı  (0,314)", f"{o['doji_oran']:.3f}".replace(".", ","), "doji_oran", "doji"),
        satir("Ortalama kesişme  (17)", str(o["kesisme"]), "kesisme", "kesisme"),
        satir("Net / aralık  (0,037)", f"{o['net_aralik']:.3f}".replace(".", ","), "net_aralik", "net"),
        satir("Azami ardışık trend barı", str(o["azami_dizi"]), "azami_dizi", "dizi"),
        # Panonun son satırı. Bant SAYISINA girmez ve bu bir seçim değil
        # dersin hükmü: barbwire bir rejim ölçüsü değil, tekil bir bar kalıbı.
        ("satir", "Barbwire (4.9) — sayıya girmez",
         f"{o['barbwire']['oran']:.2f}".replace(".", ","),
         "VAR ⚠" if o["barbwire"]["var"] else "—",
         CLARET if o["barbwire"]["var"] else GRI),
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
            f'<div class="etiket">Alt panel · rejim panosu (göreli kip)</div>{_rejim_tablo(d["rejim"])}'
            f'</div>')
    govde = (
        '<p class="bk-h1">Durum kutusu üç gerçek barda</p>'
        '<p class="bk-alt">TradingView\'de grafiğin köşesinde duran kutu budur. Satırlar '
        'okuma sırasına göre dizilidir: ① rejim → ② yön → ③ yasak → ④ kurulum → emir. '
        'Kurulum satırı hangi paketin geçerli olduğunu adıyla yazar, altındaki satır o '
        'paketin dört seviyesini. Aşağıdaki üç sütun uydurma değil: her satır, adı yazan '
        'barda ölçüm katmanının gerçekten ürettiği değerdir; alt panel göreli kipte, '
        'her ölçünün yanında son 280 bardaki sırası.</p>'
        f'<div class="izgara">{"".join(sut)}</div>'
        '<p class="aciklama"><b>Üç sütun, üç ayrı sonuç — ve ikisi HAYIR.</b> '
        'Soldaki sütunda dört katman da aynı yöne bakıyor: rejim bant değil, always-in ile '
        'paket aynı yönde, yasak yok — emir satırı dört seviyeyi yazar. '
        'Ortadakinde paket dolu, ama ② ile ④ ters yöne bakıyor — yani barı görürsünüz, '
        'işareti görürsünüz, ve almazsınız. '
        'Sağdakinde paket hizalı olduğu hâlde alt panel BANT diyor: '
        'bu kez itirazı yön değil REJİM ediyor ve dersin en pahalı hatası tam burada '
        'doğar — doğru kurulumu yanlış günde almak; bantta geçerli paket bant kenarı ve '
        'kırılım modudur, dönüş barına stop girişi değil. '
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


def _cerceve(kay: dict, anahtar: str):
    s = kay[anahtar].seri
    tick = R.tick_tahmini(s)
    fp = R.FiyatPaneli(s)
    rp = R.RejimPanosu(s)
    ku = R.Kurulumlar(s, tick)
    return s, tick, fp, rp, ku


def _durum(kay: dict, anahtar: str, damga: str, baslik: str, kod: str) -> dict:
    s, tick, fp, rp, ku = _cerceve(kay, anahtar)
    i = _cipa(s, damga)
    gecerli, aciklama = _olcut(fp, rp, ku, i, kod)
    if not gecerli:
        raise SystemExit(f"ENGEL · '{baslik}' çıpası {damga} artık o hikâyeyi "
                         f"anlatmıyor: {aciklama}")
    d = fp.durum(i)
    o = rp.olcu_goreli(i)
    ad = O.ENSTRUMAN_AD.get(anahtar.rsplit("-", 1)[0], anahtar)
    dilim = O.DILIM_AD.get(anahtar.rsplit("-", 1)[1], "")
    return {
        "baslik": baslik,
        "kunye": f"{ad} · {dilim} · {_an(s.zaman[i])}",
        "fiyat": fiyat_kutusu(d, paket_sec(ku, i), bant_konumu(s, i), tick),
        "rejim": rejim_kutusu(o),
    }


# Üç durum GERÇEK barlardan seçildi ve ZAMAN DAMGASIYLA çıpalanır.
#
# Bir zamanlar burada sabit bir İNDİS yazıyordu ve yanındaki yorum "indeks ve
# gün SABİT yazılır, çünkü yayımlanmış bir figür her koşuda başka bir barı
# anlatmamalı" diyordu — niyet doğru, mekanizma TERSİ. `teknik/olc.py`
# pencereleri SABİT UZUNLUKTA kaydırıyor (s1 420 · s4 360 · günlük 260 bar),
# yani seri her koşuda bir miktar ilerliyor ve sabit bir indis her hafta
# BAŞKA bir barı gösteriyor. Künye de indisten türediği için tarih sessizce
# değişir ve panel başlığı ("A · dört katman da evet") artık tutmayan bir barı
# anlatır. Kusur hiçbir yerde hata vermez.
#
# İki kilit birlikte gider: çıpa damgadan ÇÖZÜLÜR (bulunamazsa ENGEL), ve
# panelin SEÇİM ÖLÇÜTÜ çizim anında YENİDEN SINANIR — çıpa doğru bara
# otursa bile kutu artık o hikâyeyi anlatmıyorsa figür üretilmez. Adaylar
# `--ara` ile listelenir; göreli kip 280 barlık tarihçe istediği için aday
# yalnız serinin son kısmındadır ve pencere kaydıkça çıpa yenilenmelidir.
DURUMLAR = [
    ("us10y-s1", "2026-09-11T13:20", "A · dört katman da evet", "hizali"),
    ("us10y-s1", "2026-09-04T13:20", "B · paket var, yön VETO ediyor", "hizasiz"),
    ("dxy-s1",   "2026-09-11T14:00", "C · paket hizalı, rejim BANT", "bant"),
]


def _cipa(s, damga: str) -> int:
    """Zaman damgasından indis. Bulunamazsa ENGEL — sessizce komşu bara
    kaymak, figürün anlattığı hikâyeyi değiştirir."""
    try:
        return s.zaman.index(damga)
    except ValueError:
        yakin = [z for z in s.zaman if z[:10] == damga[:10]]
        raise SystemExit(
            f"ENGEL · çıpa {damga} seride yok (pencere kaymış olabilir). "
            f"O günün barları: {yakin or 'gün hiç yok'} — çıpa yenilenmeli; "
            f"adaylar için `--ara`")


def _olcut(fp, rp, ku, i: int, kod: str) -> tuple[bool, str]:
    """Panelin ANLATTIĞI hikâye bu barda hâlâ geçerli mi — v2 paketiyle."""
    yon, _, _ = fp.always_in()
    p = paket_sec(ku, i)
    o = rp.olcu_goreli(i)
    if o is None:
        return False, "göreli rejim tanımsız (tarihçe dolmamış)"
    n = o["n"]
    tekyon = bool(p) and not p["cift"]
    hizali = tekyon and ((p["yon"] == 1 and yon[i] == 1) or (p["yon"] == -1 and yon[i] == -1))
    karsi = tekyon and ((p["yon"] == 1 and yon[i] == -1) or (p["yon"] == -1 and yon[i] == 1))
    ad = p["ad"] if p else "—"
    if kod == "hizali":
        return (hizali and n <= 1 and not ad.startswith("bant"),
                f"paket={ad} hizalı={hizali} rejim_n={n} (isteniyor: tek yönlü paket · hizalı · rejim trend)")
    if kod == "hizasiz":
        # Rejim BANT olmamalı: itirazı YÖN etsin, okur "zaten banttı" diyemesin.
        return (karsi and n <= 3,
                f"paket={ad} karşı={karsi} rejim_n={n} (isteniyor: paket VAR, yöne KARŞI, rejim BANT değil)")
    if kod == "bant":
        return (hizali and n >= 4 and ad.startswith("dönüş barı"),
                f"paket={ad} hizalı={hizali} rejim_n={n} (isteniyor: dönüş barı paketi hizalı · rejim BANT)")
    raise SystemExit(f"ENGEL · tanınmayan ölçüt kodu '{kod}'")


def _ara(kay: dict) -> None:
    """Üç hikâye için aday barları listele — çıpa elle seçilmez, aranır."""
    for anahtar in sorted(kay):
        s, tick, fp, rp, ku = _cerceve(kay, anahtar)
        bulgu = {"hizali": [], "hizasiz": [], "bant": []}
        for i in range(len(s)):
            if rp.olcu_goreli(i) is None:
                continue
            for kod in bulgu:
                ok, _ = _olcut(fp, rp, ku, i, kod)
                if ok:
                    bulgu[kod].append(s.zaman[i])
        if any(bulgu.values()):
            print(f"{anahtar}: " + " · ".join(f"{k} {len(v)}" for k, v in bulgu.items()))
            for k, v in bulgu.items():
                if v:
                    print(f"    {k:8s} {', '.join(v[-6:])}")


def main() -> int:
    kay = _kaynaklar()
    if "--ara" in sys.argv:
        _ara(kay)
        return 0
    d = [_durum(kay, a, z, b, k) for a, z, b, k in DURUMLAR]
    yol = kutu_figuru(d, CIKTI / "durum_kutusu.html")
    print(f"{yol.relative_to(SITE.parent)} · {yol.stat().st_size:,} bayt")
    for (a, z, b, k), x in zip(DURUMLAR, d):
        kur = [s for s in x["fiyat"] if s[2] == "Kurulum"]
        emir = [s for s in x["fiyat"] if s[2] == "Emir"]
        rej = x["rejim"][0]
        print(f"  {b:36s} {x['kunye']}")
        print(f"      kurulum: {kur[0][3] if kur else '—'}")
        print(f"      emir   : {emir[0][3] if emir else '—'}")
        print(f"      rejim  : {rej[2]} ({rej[3]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
