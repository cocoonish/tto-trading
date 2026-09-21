#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bulut keşif koşusunun kaydını OHLC arşivine çevirir.

Kullanım: python3 arsivle.py <kayit.txt> <kosu_no> <commit>
Kayıt satırları GitHub zaman damgası taşır (`2026-…Z `), soyulur. Her seri
`=== SERI ad satir olcek sha ===` … `=== SON ad ===` arasındaki base64'ten
kurulur: xz açılır, FARK tablosu (dt, do, h−o, o−l, c−o, v) ham CSV'ye
(t,o,h,l,c,v · %.6f) geri çevrilir ve sha256 başlıktakiyle sınanır — sağlama
ham CSV'nin, yani kodlama katmanı da kapının içinde (tutmazsa ENGEL, dosya
yazılmaz). `veri/<ad>.csv.gz` yazılır, `veri/kunye.json` güncellenir. Ağa
çıkmaz."""
from __future__ import annotations

import base64
import gzip
import hashlib
import json
import lzma
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

KOK = Path(__file__).resolve().parent
VERI = KOK / "veri"
DAMGA = re.compile(r"^\S+Z ")
BASLIK = re.compile(r"=== SERI (\S+) (\d+) (\d+) ([0-9a-f]{64}) ===$")


def fark_ac(yuk: bytes, olcek: int) -> bytes:
    """Fark tablosunu ham CSV'ye çevirir (kesif_indikator_veri.fark_tablosu'nun tersi)."""
    satirlar = yuk.decode().split("\n")
    t0, o0 = (int(x) for x in satirlar[0].split())
    cikti = ["t,o,h,l,c,v"]
    t, c_onceki = t0, o0
    for k, s in enumerate(satirlar[1:]):
        dt, do, ho, ol, co, v = (int(x) for x in s.split())
        # İlk satır: dt = 0 (prepend=t[0]) ve do = o[0] − o[0] = 0.
        t = t0 if k == 0 else t + dt
        o = c_onceki + do
        h, l, c = o + ho, o - ol, o + co
        c_onceki = c
        cikti.append(f"{t},{o/olcek:.6f},{h/olcek:.6f},{l/olcek:.6f},{c/olcek:.6f},{v}")
    return ("\n".join(cikti) + "\n").encode()


def main(kayit: Path, kosu: str, commit: str) -> int:
    VERI.mkdir(exist_ok=True)
    satirlar = [DAMGA.sub("", s.rstrip("\r\n")) for s in kayit.read_text(encoding="utf-8", errors="replace").splitlines()]
    kunye_yol = VERI / "kunye.json"
    kunye = json.loads(kunye_yol.read_text(encoding="utf-8")) if kunye_yol.exists() else {}
    i, n, yazilan = 0, len(satirlar), 0
    while i < n:
        m = BASLIK.match(satirlar[i])
        if not m:
            i += 1
            continue
        ad, bar, olcek, sha = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4)
        j, parca = i + 1, []
        while j < n and satirlar[j] != f"=== SON {ad} ===":
            if satirlar[j] and not satirlar[j].startswith(" "):
                parca.append(satirlar[j].strip())
            j += 1
        if j >= n:
            print(f"ENGEL · {ad}: kapanış satırı yok (kayıt kesik)")
            return 1
        try:
            ham = fark_ac(lzma.decompress(base64.b64decode("".join(parca))), olcek)
        except Exception as e:  # noqa: BLE001
            print(f"ENGEL · {ad}: açılamadı ({type(e).__name__}: {str(e)[:80]})")
            return 1
        if hashlib.sha256(ham).hexdigest() != sha:
            print(f"ENGEL · {ad}: sha256 tutmuyor, yazılmadı")
            return 1
        govde = [s for s in ham.decode().split("\n")[1:] if s]
        if len(govde) != bar:
            print(f"ENGEL · {ad}: {len(govde)} satır, başlık {bar}")
            return 1
        t0, t1 = int(govde[0].split(",")[0]), int(govde[-1].split(",")[0])
        (VERI / f"{ad}.csv.gz").write_bytes(gzip.compress(ham, 9))
        kunye[ad] = {"bar": bar, "sha256": sha,
                     "bas": datetime.fromtimestamp(t0, timezone.utc).strftime("%Y-%m-%d %H:%M"),
                     "son": datetime.fromtimestamp(t1, timezone.utc).strftime("%Y-%m-%d %H:%M"),
                     "kaynak": "Yahoo Finance (yfinance), kapanmamış son bar düşürüldü",
                     "kosu": f"veri.yml keşif #{kosu} (bulten/kesif_indikator_veri.py), commit {commit}"}
        print(f"  {ad:16s} {bar:7d} bar · {kunye[ad]['bas']} → {kunye[ad]['son']}")
        yazilan += 1
        i = j + 1
    kunye_yol.write_text(json.dumps(dict(sorted(kunye.items())), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{yazilan} seri yazıldı → {VERI}")
    return 0 if yazilan else 1


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    sys.exit(main(Path(sys.argv[1]), sys.argv[2], sys.argv[3]))
