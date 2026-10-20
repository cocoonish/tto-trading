"""Yayın kapısı (sayfa sınavı 26) dogrula.py'yi numpy/pandas kurulu olmayan koşucuda çalıştırır.

20.10.2026: buyuk_ders_yaz.py tepeden numpy istiyordu, yerel kapı geçti, yayın koşucusunda düştü. Bu sınama
kapıyı iki kütüphane ENGELLENMİŞ bir alt süreçte koşturur.
"""
import subprocess
import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent.parent

ENGEL = r'''
import sys, importlib.abc
class Engel(importlib.abc.MetaPathFinder):
    def find_spec(self, ad, yol=None, hedef=None):
        if ad.split(".")[0] in {"numpy", "pandas", "plotly", "scipy", "numba"}:
            raise ModuleNotFoundError(f"engelli: {ad}")
sys.meta_path.insert(0, Engel())
sys.argv = ["dogrula.py"]
import runpy
runpy.run_path("dogrula.py", run_name="__main__")
'''


def test_kapi_agir_kutuphanesiz_kosar():
    r = subprocess.run([sys.executable, "-c", ENGEL], cwd=BURASI, capture_output=True, text=True)
    assert r.returncode == 0, (r.stdout + r.stderr)[-2000:]
