#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TTO Trading — canlı panelleri (dashboard) tek yerden başlat.

Kullanım:
  python panel.py                 # menü: hangi panel?
  python panel.py hazine          # Hazine İhraç panosu (Dash)      → http://127.0.0.1:8050
  python panel.py fx              # FX Haber Endeksi panosu (Streamlit) → http://localhost:8501
  python panel.py site            # Astro geliştirme sunucusu       → http://localhost:4321
  python panel.py hazine --port 8060
  python panel.py --liste         # panelleri göster, başlatma
  python panel.py hazine --tarayici-yok

Sözleşme:
  · Her panel kendi proje klasöründe koşar. Klasörde .venv varsa ONUN python'u
    kullanılır (guncelle.py --kur / bat\\<proje>\\kur.bat bunu kurar), yoksa bu python.
  · Başlatmadan ÖNCE gerekli paket (dash / streamlit) ve panelin okuduğu veri
    dosyaları denetlenir; eksikse ne yapılacağı yazılır ve panel açılmaz —
    "açıldı ama boş/çöktü" durumu yerine anlaşılır hata.
  · Panel ön planda koşar; Ctrl+C ile kapanır. Tarayıcı 2 sn sonra kendiliğinden
    açılır (--tarayici-yok ile kapatılır).
  · Paneller VERİ ÜRETMEZ, üretilmiş CSV/JSON'u okur. Veriyi tazelemek için:
    python guncelle.py <hat>   (ör. python guncelle.py hazine --tam)
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import threading
import time
import webbrowser
from dataclasses import dataclass, field
from pathlib import Path

KOK = Path(__file__).resolve().parent
PY = sys.executable

for _akis in (sys.stdout, sys.stderr):
    try:
        _akis.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

_COCUK_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}


@dataclass
class Panel:
    ad: str                       # komut satırındaki kısa ad
    baslik: str
    klasor: Path                  # kökten göreli
    komut: list[str]              # python'dan sonraki argümanlar ({port} yer tutucusu)
    port: int
    paketler: list[str] = field(default_factory=list)   # import edilebilir olmalı
    veri: list[str] = field(default_factory=list)       # klasöre göreli, var olmalı
    port_env: str | None = None   # portu ortam değişkeniyle veriyorsa adı
    not_: str = ""
    guncelle_hat: str = ""        # veri eksikse önerilecek guncelle.py hattı


P = Path("Aktarılacak Projeler")
PANELLER: list[Panel] = [
    Panel(
        "hazine", "Hazine İhraç panosu (Dash)", P / "hazineihrac",
        ["dashboard.py"], 8050,
        paketler=["dash", "dash_bootstrap_components", "plotly", "pandas"],
        veri=["hazine_ihale_verileri.csv", "hazine_hedef_gerceklesme.csv",
              "hazine_planlanan_ihaleler.csv"],
        port_env="PORT",
        not_="ihale/tahmin tabloları, filtreler",
        guncelle_hat="hazine",
    ),
    Panel(
        "fx", "FX Haber Endeksi panosu (Streamlit)", P / "indices",
        ["-m", "streamlit", "run", "dashboard.py", "--server.port", "{port}"], 8501,
        paketler=["streamlit", "plotly", "pandas"],
        veri=["data/index_history.json", "data/sentiment_scores.json"],
        not_="duyarlılık endeksi, manşetler, rejim",
        guncelle_hat="fx",
    ),
    Panel(
        "site", "TTO Trading sitesi (Astro dev)", Path("site"),
        [], 4321,
        not_="npm run dev — sayfaların canlı önizlemesi",
    ),
]
PANEL = {p.ad: p for p in PANELLER}


def _renk(m, k):
    return f"\033[{k}m{m}\033[0m" if sys.stdout.isatty() else m


def panel_python(p: Panel) -> str:
    """Panelin yorumlayıcısı: proje klasöründe .venv varsa onun python'u."""
    d = KOK / p.klasor
    for aday in (d / ".venv" / "Scripts" / "python.exe", d / ".venv" / "bin" / "python"):
        if aday.exists():
            return str(aday)
    return PY


def paket_var_mi(py: str, paketler: list[str]) -> list[str]:
    """Verilen yorumlayıcıda import edilemeyen paketleri döndürür."""
    if not paketler:
        return []
    kod = ("import importlib.util,sys;"
           "print(' '.join(m for m in sys.argv[1:] "
           "if importlib.util.find_spec(m) is None))")
    r = subprocess.run([py, "-c", kod, *paketler], capture_output=True, text=True,
                       env=_COCUK_ENV)
    return r.stdout.split()


def denetle(p: Panel) -> bool:
    """Paket ve veri ön koşulları. Eksikse ne yapılacağını yazar."""
    d = KOK / p.klasor
    if not d.exists():
        print(_renk(f"  ✗ proje klasörü yok: {d}", 31))
        return False

    if p.ad == "site":                                   # Node tarafı
        if not (d / "node_modules").exists():
            print(_renk("  ✗ node_modules yok — önce: cd site && npm install", 31))
            return False
        return True

    py = panel_python(p)
    eksik = paket_var_mi(py, p.paketler)
    if eksik:
        print(_renk(f"  ✗ eksik paket: {', '.join(eksik)}", 31))
        print(f"    çözüm: python guncelle.py --kur {p.guncelle_hat or p.ad}"
              f"   (Windows: bat\\{p.guncelle_hat or p.ad}\\kur.bat)")
        return False

    yok = [v for v in p.veri if not (d / v).exists()]
    if yok:
        print(_renk(f"  ✗ panelin okuduğu veri yok: {', '.join(yok)}", 31))
        if p.guncelle_hat:
            print(f"    çözüm: python guncelle.py {p.guncelle_hat} --tam")
        return False

    # Veri var ama bayat olabilir: en yeni veri dosyasının yaşını bildir (engel değil)
    if p.veri:
        yas = min((time.time() - (d / v).stat().st_mtime) / 86400 for v in p.veri)
        if yas > 7:
            print(_renk(f"  [uyarı] veri {yas:.0f} gün önce güncellenmiş — "
                        f"tazelemek için: python guncelle.py {p.guncelle_hat or p.ad}", 33))
    return True


def tarayici_ac(url: str, gecikme: float = 2.0):
    def _ac():
        time.sleep(gecikme)
        try:
            webbrowser.open(url)
        except Exception:
            pass
    threading.Thread(target=_ac, daemon=True).start()


def baslat(p: Panel, port: int, tarayici: bool) -> int:
    d = KOK / p.klasor
    url = f"http://127.0.0.1:{port}" if p.ad == "hazine" else f"http://localhost:{port}"

    if p.ad == "site":
        komut = ["npm", "run", "dev", "--", "--port", str(port)]
        env = _COCUK_ENV
    else:
        py = panel_python(p)
        komut = [py, *[a.replace("{port}", str(port)) for a in p.komut]]
        env = {**_COCUK_ENV}
        if p.port_env:
            env[p.port_env] = str(port)
        if py != PY:
            print(f"  yorumlayıcı: {Path(py).relative_to(KOK)}")

    print(f"\n▶ {p.baslik}")
    print(f"  klasör : {p.klasor}")
    print(f"  komut  : {' '.join(str(x) for x in komut)}")
    print(_renk(f"  adres  : {url}", 36))
    print("  (kapatmak için Ctrl+C)\n")

    if tarayici:
        tarayici_ac(url)
    try:
        return subprocess.run(komut, cwd=d, env=env).returncode
    except KeyboardInterrupt:
        print("\n  panel kapatıldı")
        return 0
    except FileNotFoundError as e:
        print(_renk(f"  ✗ komut çalıştırılamadı: {e}", 31))
        return 1


def menu() -> Panel | None:
    print("\nPaneller:")
    for i, p in enumerate(PANELLER, 1):
        print(f"  {i}. {p.ad:8s} {p.baslik:38s} :{p.port}  "
              f"{_renk(p.not_, 36) if p.not_ else ''}")
    sec = input("\nHangisi? (numara/ad, boş = çık): ").strip()
    if not sec:
        return None
    if sec.isdigit() and 1 <= int(sec) <= len(PANELLER):
        return PANELLER[int(sec) - 1]
    if sec in PANEL:
        return PANEL[sec]
    print(f"  ? {sec} tanınmadı")
    return None


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("panel", nargs="?", help="kısa ad: " + " ".join(PANEL))
    ap.add_argument("--port", type=int, help="varsayılan portu ez")
    ap.add_argument("--liste", action="store_true", help="panelleri göster, başlatma")
    ap.add_argument("--tarayici-yok", action="store_true", help="tarayıcıyı açma")
    a = ap.parse_args()

    if a.liste:
        for p in PANELLER:
            print(f"{p.ad:8s} {p.baslik:38s} :{p.port}  {p.klasor}")
            if p.veri:
                print(f"{'':8s} veri: {', '.join(p.veri)}")
        return 0

    if a.panel:
        if a.panel not in PANEL:
            print(f"tanınmayan panel: {a.panel} — geçerli: {list(PANEL)}")
            return 2
        p = PANEL[a.panel]
    else:
        p = menu()
        if p is None:
            return 0

    print(f"\n{'═' * 64}\n  {p.baslik}\n{'═' * 64}")
    if not denetle(p):
        return 1
    return baslat(p, a.port or p.port, not a.tarayici_yok)


if __name__ == "__main__":
    sys.exit(main())
