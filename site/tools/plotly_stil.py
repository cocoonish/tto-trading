#!/usr/bin/env python3
"""Plotly HTML çıktılarına site ev stilini uygular (v3).

Ham Plotly HTML'leri iframe içinde dağınık görünür (başlık/lejant çakışması,
sabit boyut, uyumsuz eksen renkleri). Bu araç HTML'in sonuna bir "restyle"
script'i enjekte eder: sayfa yüklenince Plotly.relayout ile ev stili uygulanır.
Kaynak verinin/formüllerin olduğu kısma dokunulmaz. İşlem idempotenttir ve
sürüm yükseltmelerinde eski blok söküp yenisi takılır.

Kullanım:
  python3 site/tools/plotly_stil.py --hepsi     # public/projeler altındaki tüm HTML'ler
  python3 site/tools/plotly_stil.py dosya.html …
"""

import re
import sys
from pathlib import Path

ISARET = "<!-- tto-ev-stili -->"

EV_STILI = """
<!-- tto-ev-stili -->
<style>
  html, body { margin: 0; padding: 0; height: 100%; background: #ffffff; }
  .plotly-graph-div { width: 100% !important; height: 100vh !important; }
  .modebar { opacity: 0.25; transition: opacity .2s; }
  .modebar:hover { opacity: 1; }
  .modebar-btn--logomark, .modebar-btn[data-title="Produced with Plotly.js"] { display: none !important; }
</style>
<script>
(function () {
  function uygula() {
    var gd = document.querySelector('.plotly-graph-div');
    if (!gd || !window.Plotly || !gd.layout) { setTimeout(uygula, 120); return; }
    var mevcut = gd.layout.title && gd.layout.title.text ? gd.layout.title.text : null;
    var guncelle = {
      autosize: true,
      'font.family': "-apple-system, 'Segoe UI', Helvetica, Arial, sans-serif",
      'font.size': 12.5,
      'font.color': '#211b12',
      paper_bgcolor: '#ffffff',
      plot_bgcolor: '#ffffff',
      'title.x': 0.01,
      'title.xanchor': 'left',
      'title.font.size': 15,
      'title.font.color': '#211b12',
      // lejant her zaman grafiğin ALTINDA — başlıkla çakışma imkânsız
      'legend.orientation': 'h',
      'legend.yanchor': 'top',
      'legend.y': -0.1,
      'legend.xanchor': 'left',
      'legend.x': 0,
      'legend.font.size': 11,
      'legend.bgcolor': 'rgba(255,255,255,0)',
      'margin.t': mevcut ? 92 : 36,
      'margin.r': 64,
      'margin.b': 110,
      'margin.l': 64,
      'hoverlabel.bgcolor': '#211b12',
      'hoverlabel.bordercolor': '#211b12',
      'hoverlabel.font.color': '#f5f0e6',
      'hoverlabel.font.size': 12
    };
    // tüm eksenlere (subplot dahil) uyumlu ızgara/kenar/yazı stili
    Object.keys(gd.layout).forEach(function (k) {
      if (/^[xy]axis\\d*$/.test(k)) {
        guncelle[k + '.gridcolor'] = '#efe9dc';
        guncelle[k + '.zerolinecolor'] = '#cfc4ab';
        guncelle[k + '.linecolor'] = '#d8cfba';
        guncelle[k + '.tickfont.size'] = 11;
        guncelle[k + '.tickfont.color'] = '#6b6355';
        guncelle[k + '.title.font.size'] = 12;
        guncelle[k + '.title.font.color'] = '#211b12';
      }
    });
    Plotly.relayout(gd, guncelle);
    window.addEventListener('resize', function () { Plotly.Plots.resize(gd); });
    Plotly.Plots.resize(gd);
  }
  if (document.readyState === 'complete') uygula();
  else window.addEventListener('load', uygula);
})();
</script>
"""


def isle(yol: Path) -> str:
    metin = yol.read_text(encoding="utf-8", errors="ignore")
    if "plotly" not in metin.lower():
        return "atlandı (plotly değil)"
    yeni_mi = ISARET not in metin
    # eski enjeksiyon bloğunu sök (işaretten bloğun son </script>'ine kadar)
    if not yeni_mi:
        metin = re.sub(
            re.escape(ISARET) + r"[\s\S]*?</script>\s*", "", metin, count=1
        )
    if "</body>" in metin:
        metin = metin.replace("</body>", EV_STILI + "\n</body>", 1)
    else:
        metin += EV_STILI
    yol.write_text(metin, encoding="utf-8")
    return "stillendi" if yeni_mi else "güncellendi (v3)"


def main():
    argv = sys.argv[1:]
    kok = Path(__file__).resolve().parents[1] / "public" / "projeler"
    dosyalar = (
        sorted(kok.rglob("*.html")) if (not argv or argv[0] == "--hepsi")
        else [Path(a) for a in argv]
    )
    for d in dosyalar:
        print(f"{d.name:36s} {isle(d)}")


if __name__ == "__main__":
    main()
