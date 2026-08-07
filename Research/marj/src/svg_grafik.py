# -*- coding: utf-8 -*-
"""
Etkileşimli SVG grafik üreticileri (tek dosyalık HTML raporu için).

Harici kütüphane yok: SVG Python'da kurulur, kesişim çizgisi + araç ipucu
(tooltip) için sayfa sonuna tek bir vanilya-JS motoru eklenir. Her grafiğin
verisi VERI sözlüğüne piksel koordinatlarıyla gömülür; JS yalnızca en yakın
ayı bulup daireleri ve ipucunu konumlandırır.
"""
import json
import math

AYLAR_TR = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]

W, H = 720, 400
SOL, SAG, UST, ALT = 56, 16, 14, 34   # kenar boşlukları


def sayi_tr(v, fmt):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    if fmt == "oran":
        s = f"{v:.2f}"
    elif fmt == "yuzde":
        s = ("-" if v < 0 else "") + f"%{abs(v):.1f}"
    elif fmt == "endeks":
        s = f"{v:,.0f}"
    else:
        s = f"{v:,.1f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def _guzel_adim(kaba):
    us = 10 ** math.floor(math.log10(kaba))
    for k in (1, 2, 2.5, 5, 10):
        if kaba <= k * us:
            return k * us
    return 10 * us


def _y_olcek(vmin, vmax):
    """Ölçek sınırı = %7 paylı GERÇEK veri aralığı; tikler bu aralığın İÇİNDE kalır.
    (Önceki sürüm tick uçlarını sınır sayıyordu ve veriyi taşırıyordu.)"""
    if vmin == vmax:
        vmin, vmax = vmin - 1, vmax + 1
    pay = (vmax - vmin) * 0.07
    vmin -= pay; vmax += pay
    adim = _guzel_adim((vmax - vmin) / 5.5)
    t = math.ceil(vmin / adim) * adim
    tikler = []
    while t <= vmax + 1e-9:
        tikler.append(round(t, 10))
        t += adim
    return vmin, vmax, tikler


def _tarih_tr(ts):
    return f"{AYLAR_TR[ts.month-1]} {ts.year}"


def cizgi_svg(gid, tarihler, seriler, fmt="endeks", ref=None, splice_ts=None,
              uc_etiket=True, yukseklik=H, baslik=None):
    """Çizgi grafiği. seriler: [{'ad','renk','vals': list}] — hepsi aynı tarih gridi.
    ref: (deger, etiket) yatay kesikli çizgi. splice_ts: dikey noktalı çizgi (Timestamp).
    Dönen: (html, veri_sozlugu)"""
    h = yukseklik
    n = len(tarihler)
    x0, x1 = SOL, W - SAG
    y0, y1 = UST, h - ALT
    dx = (x1 - x0) / max(n - 1, 1)
    px = [round(x0 + i * dx, 2) for i in range(n)]

    tum = [v for s in seriler for v in s["vals"] if v is not None and not (isinstance(v, float) and math.isnan(v))]
    if ref:
        tum.append(ref[0])
    vmin, vmax, tikler = _y_olcek(min(tum), max(tum))
    def Y(v):
        return round(y1 - (v - vmin) / (vmax - vmin) * (y1 - y0), 2)

    p = []
    p.append(f'<svg viewBox="0 0 {W} {h}" role="img">')
    # ızgara + y etiketleri
    for t in tikler:
        yy = Y(t)
        p.append(f'<line x1="{x0}" y1="{yy}" x2="{x1}" y2="{yy}" stroke="#e8e7e2" stroke-width="1"/>')
        p.append(f'<text x="{x0-7}" y="{yy+3.5}" text-anchor="end" font-size="10.5" fill="#52514e">{sayi_tr(t, fmt)}</text>')
    # x yıl etiketleri (her yılın Ocak'ı; sıklığa göre 1-2 yıl atla)
    yil_idx = [i for i, ts in enumerate(tarihler) if ts.month == 1]
    atla = 2 if len(yil_idx) > 8 else 1
    for j, i in enumerate(yil_idx):
        if j % atla:
            continue
        p.append(f'<line x1="{px[i]}" y1="{y1}" x2="{px[i]}" y2="{y1+4}" stroke="#b9b8b2" stroke-width="1"/>')
        p.append(f'<text x="{px[i]}" y="{y1+16}" text-anchor="middle" font-size="10.5" fill="#52514e">{tarihler[i].year}</text>')
    p.append(f'<line x1="{x0}" y1="{y1}" x2="{x1}" y2="{y1}" stroke="#b9b8b2" stroke-width="1"/>')
    # splice dikey çizgisi
    if splice_ts is not None:
        try:
            i = next(i for i, ts in enumerate(tarihler) if ts >= splice_ts)
            p.append(f'<line x1="{px[i]}" y1="{y0}" x2="{px[i]}" y2="{y1}" stroke="#52514e" stroke-width="1" stroke-dasharray="2,4" opacity=".7"/>')
            p.append(f'<text x="{px[i]+4}" y="{y0+10}" font-size="9" fill="#52514e">proxy →</text>')
        except StopIteration:
            pass
    # referans çizgisi
    if ref:
        yy = Y(ref[0])
        p.append(f'<line x1="{x0}" y1="{yy}" x2="{x1}" y2="{yy}" stroke="#52514e" stroke-width="1.4" stroke-dasharray="6,4"/>')
        p.append(f'<text x="{x0+6}" y="{yy-5}" font-size="10" fill="#52514e">{ref[1]}</text>')
    # seriler
    veri_seriler = []
    for s in seriler:
        yol, onceki = [], False
        pyler = []
        for i, v in enumerate(s["vals"]):
            if v is None or (isinstance(v, float) and math.isnan(v)):
                pyler.append(None); onceki = False; continue
            yy = Y(v)
            pyler.append(yy)
            yol.append(f"{'L' if onceki else 'M'}{px[i]},{yy}")
            onceki = True
        p.append(f'<path d="{" ".join(yol)}" fill="none" stroke="{s["renk"]}" stroke-width="2" stroke-linejoin="round"/>')
        if uc_etiket:
            son_i = max(i for i, v in enumerate(pyler) if v is not None)
            p.append(f'<text x="{px[son_i]-3}" y="{pyler[son_i]-7}" text-anchor="end" font-size="10.5" font-weight="700" fill="{s["renk"]}" stroke="#fff" stroke-width="3" paint-order="stroke">{sayi_tr(s["vals"][son_i], fmt)}</text>')
        veri_seriler.append({"ad": s["ad"], "renk": s["renk"],
                             "py": pyler,
                             "vals": [None if v is None or (isinstance(v, float) and math.isnan(v)) else round(float(v), 3) for v in s["vals"]]})
    # kesişim grubu (gizli)
    p.append(f'<g class="ch" style="display:none"><line x1="0" y1="{y0}" x2="0" y2="{y1}" stroke="#52514e" stroke-width="1" stroke-dasharray="3,3"/>')
    for s in seriler:
        p.append(f'<circle r="4.5" fill="{s["renk"]}" stroke="#fcfcfb" stroke-width="2"/>')
    p.append("</g>")
    # fare yakalama alanı
    p.append(f'<rect class="yakala" x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" fill="transparent"/>')
    p.append("</svg>")

    veri = {"tur": "cizgi", "x0": x0, "dx": round(dx, 4), "n": n, "px": px,
            "tarih": [_tarih_tr(t) for t in tarihler], "fmt": fmt, "series": veri_seriler}
    lejant = ""
    if len(seriler) > 1:
        lejant = '<div class="lejant">' + "".join(
            f'<span><i style="background:{s["renk"]}"></i>{s["ad"]}</span>' for s in seriler) + "</div>"
    bas = f'<figcaption>{baslik}</figcaption>' if baslik else ""
    html = f'<figure class="ich" id="{gid}" data-id="{gid}" data-tur="cizgi">{bas}{lejant}{"".join(p)}<div class="tip"></div></figure>'
    return html, veri


def bar_svg(gid, kategoriler, seriler, fmt="oran", yukseklik=H, taban_cizgi=None, baslik=None):
    """Gruplu bar grafik. seriler: [{'ad','renk','vals'}]. Tooltip her barda."""
    h = yukseklik
    x0, x1 = SOL, W - SAG
    y0, y1 = UST, h - ALT
    tum = [v for s in seriler for v in s["vals"]]
    alt_deger = min(0, min(tum))
    vmin, vmax, tikler = _y_olcek(alt_deger, max(tum))
    def Y(v):
        return round(y1 - (v - vmin) / (vmax - vmin) * (y1 - y0), 2)
    nK, nS = len(kategoriler), len(seriler)
    grup_g = (x1 - x0) / nK
    bar_g = min(grup_g * 0.72 / nS, 42)
    p = [f'<svg viewBox="0 0 {W} {h}" role="img">']
    for t in tikler:
        yy = Y(t)
        p.append(f'<line x1="{x0}" y1="{yy}" x2="{x1}" y2="{yy}" stroke="#e8e7e2"/>')
        p.append(f'<text x="{x0-7}" y="{yy+3.5}" text-anchor="end" font-size="10.5" fill="#52514e">{sayi_tr(t, fmt)}</text>')
    sifir_y = Y(0) if vmin < 0 else y1
    for k, kat in enumerate(kategoriler):
        merkez = x0 + (k + 0.5) * grup_g
        for si, s in enumerate(seriler):
            v = s["vals"][k]
            bx = merkez - (nS * bar_g) / 2 + si * bar_g
            yy = Y(v)
            ust, boy = (yy, sifir_y - yy) if v >= 0 else (sifir_y, yy - sifir_y)
            tip = f"<b>{kat}</b><div><span style='background:{s['renk']}'></span>{s['ad']}: <b>{sayi_tr(v, fmt)}</b></div>"
            p.append(f'<rect x="{bx:.1f}" y="{ust:.1f}" width="{bar_g-2:.1f}" height="{max(boy,0.5):.1f}" '
                     f'rx="3" fill="{s["renk"]}" data-tip="{tip.replace(chr(34), "&quot;")}"/>')
            p.append(f'<text x="{bx + (bar_g-2)/2:.1f}" y="{(ust - 4) if v>=0 else (ust+boy+11):.1f}" text-anchor="middle" font-size="9.5" fill="#1a1a1a">{sayi_tr(v, fmt)}</text>')
        etiket = kat.replace(" ağırlıklı", "\nağırlıklı")
        for li, parca in enumerate(etiket.split("\n")):
            p.append(f'<text x="{merkez:.1f}" y="{y1+14+li*11}" text-anchor="middle" font-size="10" fill="#52514e">{parca}</text>')
    if taban_cizgi is not None:
        yy = Y(taban_cizgi)
        p.append(f'<line x1="{x0}" y1="{yy}" x2="{x1}" y2="{yy}" stroke="#52514e" stroke-width="1" stroke-dasharray="6,4"/>')
    p.append(f'<line x1="{x0}" y1="{sifir_y}" x2="{x1}" y2="{sifir_y}" stroke="#b9b8b2"/>')
    p.append("</svg>")
    lejant = '<div class="lejant">' + "".join(
        f'<span><i style="background:{s["renk"]}"></i>{s["ad"]}</span>' for s in seriler) + "</div>"
    bas = f'<figcaption>{baslik}</figcaption>' if baslik else ""
    html = f'<figure class="ich" id="{gid}" data-id="{gid}" data-tur="bar">{bas}{lejant}{"".join(p)}<div class="tip"></div></figure>'
    return html, {"tur": "bar"}


JS_MOTOR = r"""
<script>
(function(){
const VERI = __VERI__;
const fmtla = (v, f) => {
  if (v === null || v === undefined) return "—";
  let s;
  if (f === "oran") s = v.toFixed(2);
  else if (f === "yuzde") s = (v < 0 ? "-%" : "%") + Math.abs(v).toFixed(1);
  else if (f === "endeks") s = Math.round(v).toLocaleString("tr-TR");
  else s = v.toFixed(1);
  return String(s).replace(".", ",");
};
document.querySelectorAll(".ich").forEach(fig => {
  const d = VERI[fig.dataset.id];
  const svg = fig.querySelector("svg");
  const tip = fig.querySelector(".tip");
  const konum = ev => {
    const fr = fig.getBoundingClientRect();
    let tx = ev.clientX - fr.left + 16, ty = ev.clientY - fr.top - 12;
    if (tx + tip.offsetWidth > fr.width - 6) tx = ev.clientX - fr.left - tip.offsetWidth - 16;
    if (ty < 0) ty = 4;
    tip.style.left = tx + "px"; tip.style.top = ty + "px";
  };
  if (fig.dataset.tur === "cizgi" && d) {
    const ch = svg.querySelector(".ch");
    const cizgi = ch.querySelector("line");
    const daireler = ch.querySelectorAll("circle");
    const alan = svg.querySelector(".yakala");
    alan.addEventListener("mousemove", ev => {
      const pt = new DOMPoint(ev.clientX, ev.clientY).matrixTransform(svg.getScreenCTM().inverse());
      let i = Math.round((pt.x - d.x0) / d.dx);
      i = Math.max(0, Math.min(d.n - 1, i));
      ch.style.display = "";
      cizgi.setAttribute("x1", d.px[i]); cizgi.setAttribute("x2", d.px[i]);
      let ic = "<b>" + d.tarih[i] + "</b>";
      d.series.forEach((s, k) => {
        const c = daireler[k];
        if (s.py[i] === null) { c.style.display = "none"; }
        else { c.style.display = ""; c.setAttribute("cx", d.px[i]); c.setAttribute("cy", s.py[i]); }
        ic += "<div><span style='background:" + s.renk + "'></span>" + s.ad + ": <b>" + fmtla(s.vals[i], d.fmt) + "</b></div>";
      });
      tip.innerHTML = ic; tip.style.display = "block"; konum(ev);
    });
    alan.addEventListener("mouseleave", () => { tip.style.display = "none"; ch.style.display = "none"; });
  } else if (fig.dataset.tur === "bar") {
    svg.querySelectorAll("rect[data-tip]").forEach(r => {
      r.addEventListener("mousemove", ev => {
        tip.innerHTML = r.dataset.tip; tip.style.display = "block"; konum(ev);
        r.setAttribute("opacity", "0.85");
      });
      r.addEventListener("mouseleave", () => { tip.style.display = "none"; r.removeAttribute("opacity"); });
    });
  }
});
})();
</script>
"""

CSS_EK = """
.ich{position:relative;margin:20px 0;border:1px solid var(--acik);border-radius:10px;padding:10px 8px 4px;background:#fff}
.ich svg{width:100%;height:auto;display:block}
.ich .tip{display:none;position:absolute;z-index:20;pointer-events:none;background:#1a1a1a;color:#fff;
padding:7px 10px;border-radius:7px;font-size:12px;line-height:1.5;box-shadow:0 3px 12px rgba(0,0,0,.25);max-width:260px}
.ich .tip span{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:6px}
.ich .tip b{font-weight:700}
.lejant{display:flex;flex-wrap:wrap;gap:4px 16px;font-size:12.5px;color:#1a1a1a;padding:2px 6px 8px}
.lejant i{display:inline-block;width:11px;height:11px;border-radius:3px;margin-right:6px;vertical-align:-1px}
figcaption{font-size:13px;color:#52514e;margin:6px 6px 8px;text-align:left}
"""


def motor_js(veri_sozlugu):
    return JS_MOTOR.replace("__VERI__", json.dumps(veri_sozlugu, ensure_ascii=False, separators=(",", ":")))
