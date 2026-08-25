#!/usr/bin/env python3
"""Bülten dosyaları için git birleştirme sürücüsü.

Her sabah aynı çakışma yaşanıyordu: otomatik koşu (cron / başka makine)
`gundem_kaynagi: "otomatik"` bir bülten yazıp gönderiyor, yazı katmanı ise
aynı gün için `"yazili"` bülteni üretiyor. İkisi aynı dosyaya dokunduğu için
`git pull --rebase` elle çözülmesi gereken bir çakışmayla duruyordu.

Kural basit ve tek yönlü: **yazılı bülten otomatik bülteni yener.** Otomatik
bülten yalnız sayıları taşır; yazılı olan hem sayıları hem yazıyı taşır ve
zaten `bulten.py --tur ...` her koşuda sayıları tazeler. Yani yazılı sürümü
seçmek hiçbir veriyi kaybettirmez.

Önbellek dosyalarında (`bulten/onbellek/*.json`) kayıp riski yok: iki taraf da
anahtar→değer sözlüğü olduğu için anahtarlar birleştirilir.

Kurulum otomatiktir; `bulten.py` her koşuda `kur()` çağırarak sürücüyü yerel
git yapılandırmasına yazar (idempotent). Elle kurmak için:

    python3 bulten/birlestir.py --kur
"""
from __future__ import annotations

import json
import shlex
import subprocess
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent


# ── kurulum ────────────────────────────────────────────────────────────────
def kur(sessiz: bool = True) -> None:
    """Birleştirme sürücüsünü yerel git yapılandırmasına yaz (idempotent).

    `.gitattributes` depoda tutulur ama sürücünün komutu `.git/config` içinde
    durur ve depoyla taşınmaz — bu yüzden her koşuda yeniden yazıyoruz.
    """
    # Git bu komutu KABUK üzerinden koşturur; depo yolunda boşluk olduğu için
    # (".../aktif projeler/TTO Trading/...") tırnaklamak zorunlu — tırnaksız
    # hâlde sürücü sessizce çalışmaz ve çakışma elle çözülmek üzere kalır.
    komut = "{} {} %O %A %B %P".format(
        shlex.quote(sys.executable), shlex.quote(str(Path(__file__).resolve())))
    for anahtar, deger in (
        ("merge.bulten.name", "bülten: yazılı sürüm otomatiği yener"),
        ("merge.bulten.driver", komut),
        ("merge.bulten.recursive", "binary"),
        # Üretilmiş Plotly HTML'leri: aynı veriden üretilseler bile her koşuda
        # farklı rastgele div kimlikleri taşırlar, bu yüzden hep çakışırlar.
        # Bulut günde dört kez veri işlediğinden bu çakışma her gün yaşanırdı.
        # `true` komutu çalışıp hiçbir şey yapmaz: çalışma kopyasındaki sürüm
        # kalır. Grafikler türev ürün — kaynağı hattın kendisi, bir sonraki
        # koşuda zaten yeniden üretilirler. ozet.json bu kuralın DIŞINDA:
        # sayfa metnindeki sayıları o besliyor, keyfî taraf seçilemez.
        ("merge.uretilmis.name", "üretilmiş grafik: mevcut sürüm korunur"),
        ("merge.uretilmis.driver", "true"),
    ):
        subprocess.run(["git", "config", anahtar, deger], cwd=KOK,
                       capture_output=True)
    if not sessiz:
        print("  ✓ birleştirme sürücüleri kuruldu (bülten + üretilmiş grafik)")


# ── çözüm kuralları ────────────────────────────────────────────────────────
def _oku(p: str) -> dict | None:
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return None


def _agirlik(b: dict) -> tuple[int, int]:
    """Bülteni sırala: (yazılı mı, kaç kelime). Büyük olan kazanır."""
    yazili = 1 if b.get("gundem_kaynagi") == "yazili" else 0
    kelime = len(str(b.get("yorum", "")).split())
    for v in (b.get("gundem") or {}).values():
        kelime += len(str(v).split())
    return yazili, kelime


def _bulten_coz(o: str, a: str, b: str) -> int:
    """Bülten JSON'u: yazılı sürüm kazanır; ikisi de yazılıysa dolu olan."""
    bizim, onlarin = _oku(a), _oku(b)
    if bizim is None or onlarin is None:
        return 1                      # JSON okunamıyorsa elle çözülsün
    kazanan = bizim if _agirlik(bizim) >= _agirlik(onlarin) else onlarin
    Path(a).write_text(
        json.dumps(kazanan, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


def _onbellek_coz(o: str, a: str, b: str) -> int:
    """Önbellek JSON'u: iki tarafın anahtarları birleştirilir."""
    bizim, onlarin = _oku(a), _oku(b)
    if not isinstance(bizim, dict) or not isinstance(onlarin, dict):
        return 0 if bizim is not None else 1   # sözlük değilse bizimkini tut
    birlesik = {**onlarin, **bizim}            # çakışan anahtarda bizimki
    Path(a).write_text(
        json.dumps(birlesik, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


def main(argv: list[str]) -> int:
    if argv and argv[0] == "--kur":
        kur(sessiz=False)
        return 0
    if len(argv) < 3:
        print("kullanım: birlestir.py %O %A %B %P  |  --kur", file=sys.stderr)
        return 2
    o, a, b = argv[0], argv[1], argv[2]
    yol = argv[3] if len(argv) > 3 else ""
    if "/onbellek/" in yol:
        return _onbellek_coz(o, a, b)
    return _bulten_coz(o, a, b)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
