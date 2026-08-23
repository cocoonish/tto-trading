#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bülten — anlık görüntü deposu.

Her hattın ozet.json'u her koşuda `gecmis/<hat>.jsonl` dosyasına eklenir (yalnız
İÇERİK DEĞİŞTİYSE). Bülten "dün neredeydi, bugün nerede" sorusunu bu depodan
cevaplar.

Kritik ayrıntı — kıyas noktası: bir hat günde iki kez koşulursa iki anlık
görüntü aynı veri sürümünü (_tarih) taşır ve farkları sıfır çıkar. O yüzden
kıyas, `_tarih`i FARKLI olan en son görüntüye göre yapılır: "son veri
yayımından bu yana ne değişti". Aksi hâlde bülten her gün "değişiklik yok"
derdi — hattın verisi haftalıkken bile.

Depo git'ten de kurulabilir: ozet.json dosyaları depoda izlendiği için geçmiş
commit'lerden gerçek bir tarihçe çıkarılabilir (`--git` ile).
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent
PROJELER = KOK / "site" / "public" / "projeler"
GECMIS = BURASI / "gecmis"
GECMIS.mkdir(parents=True, exist_ok=True)


def ozet_yolu(hat: str) -> Path:
    return PROJELER / hat / "ozet.json"


def anlik(hat: str) -> dict | None:
    y = ozet_yolu(hat)
    if not y.exists():
        return None
    try:
        return json.loads(y.read_text(encoding="utf-8"))
    except Exception:
        return None


def _tarih_of(d: dict) -> str:
    for a in ("_tarih", "_tarih2", "tarih"):
        if d.get(a):
            return str(d[a])
    return "?"


def gecmis_oku(hat: str) -> list[dict]:
    y = GECMIS / f"{hat}.jsonl"
    if not y.exists():
        return []
    kayit = []
    for satir in y.read_text(encoding="utf-8").splitlines():
        satir = satir.strip()
        if not satir:
            continue
        try:
            kayit.append(json.loads(satir))
        except json.JSONDecodeError:
            continue
    return kayit


def kaydet(hat: str, ozet: dict, zaman: str | None = None) -> bool:
    """Yeni anlık görüntüyü ekle. İçerik öncekiyle aynıysa yazma. Dönüş: yazıldı mı."""
    onceki = gecmis_oku(hat)
    if onceki and onceki[-1].get("d") == ozet:
        return False
    kayit = {"t": zaman or datetime.now().isoformat(timespec="seconds"),
             "v": _tarih_of(ozet), "d": ozet}
    with open(GECMIS / f"{hat}.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(kayit, ensure_ascii=False) + "\n")
    return True


def onceki_surum(hat: str, simdiki_tarih: str) -> dict | None:
    """`_tarih`i şimdikinden FARKLI olan en son anlık görüntü.

    Kıyas noktası budur: aynı veri sürümünün iki kopyası arasındaki fark sıfırdır
    ve bülten hiçbir şey söylemezdi.
    """
    for kayit in reversed(gecmis_oku(hat)):
        if kayit.get("v") != simdiki_tarih:
            return kayit
    return None


def son_gorulme(hat: str) -> tuple[str, str] | None:
    """(veri sürümü, o sürümün ilk görüldüğü zaman) — gecikme denetimi için."""
    kayitlar = gecmis_oku(hat)
    if not kayitlar:
        return None
    son_v = kayitlar[-1].get("v")
    ilk = next(k for k in kayitlar if k.get("v") == son_v)
    return son_v, ilk.get("t", "")


def gun_once(hat: str, gun: int = 7) -> dict | None:
    """En az `gun` gün önceki son anlık görüntü — haftalık kıyas için.

    Günlük bülten "son veri yayımından bu yana"ya bakar; haftalık bülten ise
    "geçen hafta bu saatte neredeydik" sorusunu sorar. İkisi farklı sorulardır:
    haftalık seride birincisi tek bir yayımı, ikincisi tüm haftayı kapsar.
    """
    from datetime import datetime, timedelta
    sinir = datetime.now() - timedelta(days=gun)
    aday = None
    for kayit in gecmis_oku(hat):
        try:
            t = datetime.fromisoformat(str(kayit.get("t", "")).replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            continue
        if t <= sinir:
            aday = kayit
    return aday


# ─────────────────────────────────────────── git'ten tarihçe kurma
def git_bootstrap(hatlar: list[str], sessiz=False) -> dict[str, int]:
    """Depo geçmişindeki ozet.json sürümlerinden tarihçe kur.

    Böylece sistem ilk gününde bile gerçek 'geçen haftaya göre' farkı üretebilir;
    aksi hâlde ilk bülten boş çıkardı.
    """
    sonuc = {}
    for hat in hatlar:
        rel = f"site/public/projeler/{hat}/ozet.json"
        log = subprocess.run(["git", "log", "--reverse", "--format=%H %cI", "--", rel],
                             cwd=KOK, capture_output=True, text=True)
        n = 0
        mevcut = {(k.get("t"), k.get("v")) for k in gecmis_oku(hat)}
        for satir in log.stdout.splitlines():
            if not satir.strip():
                continue
            sha, zaman = satir.split(None, 1)
            ic = subprocess.run(["git", "show", f"{sha}:{rel}"], cwd=KOK,
                                capture_output=True, text=True)
            if ic.returncode != 0:
                continue
            try:
                d = json.loads(ic.stdout)
            except json.JSONDecodeError:
                continue
            anahtar = (zaman.strip(), _tarih_of(d))
            if anahtar in mevcut:
                continue
            if kaydet(hat, d, zaman=zaman.strip()):
                n += 1
        sonuc[hat] = n
        if not sessiz:
            print(f"  {hat:26s} {n} sürüm eklendi")
    return sonuc


if __name__ == "__main__":
    import sys
    from ayar import RITIM
    if "--git" in sys.argv:
        print("git geçmişinden tarihçe kuruluyor…")
        git_bootstrap(list(RITIM))
    else:
        for h in RITIM:
            k = gecmis_oku(h)
            sg = son_gorulme(h)
            print(f"  {h:26s} {len(k):3d} görüntü" + (f" · son sürüm {sg[0]} ({sg[1][:10]})" if sg else ""))
