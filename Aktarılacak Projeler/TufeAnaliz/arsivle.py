#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ARŞİVLE — Eylül 2026 TÜFE yazısının girdilerini yayım gününün hâliyle dondurur.

Analiz yayımlandığı günün metnidir (karar 08.09.2026). Sayıları üreten girdiler
canlı hat dosyalarında kalsaydı hat bir sonraki koşuda onları değiştirir ve
yazının hiçbir sayısı yeniden üretilemezdi. Bu betik o girdilerin yayım günkü
kopyasını `veri/<çıpa>/` altına sıkıştırıp künyesine (sıkıştırılmamış içeriğin
sha256'sı, kaynak yolu, kopyalama anı, kaynağın son commit'i) yazar.

VAR OLANIN ÜZERİNE YAZMAZ: aynı içerik yeniden arşivlenirse dokunulmaz, farklı
içerik gelirse betik durur. Yeni bir pencere yeni bir çıpa dizinidir.

Girdiler:
  · Enflasyon hattı — `ozet.json` (05.10.2026 koşusu, Eylül 2026 verisi) ve
    yazının okuduğu `data/` dosyaları (endeks düzeyleri, arındırılmış seriler,
    katkı ve ağırlık defterleri, dağılım, beklenti isabeti, baz senaryoları,
    reel faiz, günlük fonlama maliyeti, kalem ağacı, uyarılar)
  · DİBS Verim Eğrisi, Fonlama ve Likidite, TÜFEX Başabaş panolarının site
    kopyası `ozet.json` — üçü de 2 Ekim 2026 Cuma kapanışı, yani veri
    YAYIMINDAN ÖNCEKİ seans; yayıma piyasa tepkisi bu arşivde yoktur.
  · Yazının tırnak içinde aktardığı metinler: TCMB PPK karar metni (2026-38) ve
    toplantı özeti (2026-42), 3 Eylül 2026 tarihli Ağustos TÜFE yazısı.
  · Ağustos'un yayılım ölçülerinin 9 Eylül hâli (Enflasyon hattının `dagilim.csv`si,
    36cd300d) — bir aylık revizyonun ölçüsü.

Koşum:  python3 arsivle.py
"""
from __future__ import annotations

import datetime as dt
import gzip
import hashlib
import json
import subprocess
import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
CIPA = "2026-10-05"
HEDEF = BURASI / "veri" / CIPA
ENF = KOK / "Aktarılacak Projeler/Enflasyon"
PANO = KOK / "site/public/projeler"

# arşiv adı → kaynak (depo köküne göre)
GIRDILER = {
    "enflasyon_ozet.json": ENF / "ozet.json",
    "enflasyon_uyarilar.json": ENF / "uyarilar.json",
    "aylik.csv": ENF / "data/aylik.csv",
    "sa.csv": ENF / "data/sa.csv",
    "katki.csv": ENF / "data/katki.csv",
    "agirlik.json": ENF / "data/agirlik.json",
    "dagilim.csv": ENF / "data/dagilim.csv",
    "beklenti.json": ENF / "data/beklenti.json",
    "baz_senaryo.csv": ENF / "data/baz_senaryo.csv",
    "reel_faiz.csv": ENF / "data/reel_faiz.csv",
    "gunluk.csv": ENF / "data/gunluk.csv",
    "agac.csv": ENF / "data/agac.csv",
    "veri_durum.json": ENF / "data/veri_durum.json",
    "dibs_ozet.json": PANO / "dibs-verim-egrisi/ozet.json",
    "fonlama_ozet.json": PANO / "fonlama-likidite/ozet.json",
    "tufex_ozet.json": PANO / "tufex-basabas/ozet.json",
    # yazının tırnak içinde aktardığı metinler (alıntı kapısı bunlara karşı sorar)
    "ppk_2026-38-TR.json": KOK / "bulten/veri/ppk/2026/2026-38-TR.json",
    "ppk_2026-42-TR.json": KOK / "bulten/veri/ppk/2026/2026-42-TR.json",
    "analiz_2026-09-03.mdx": KOK / "site/src/content/analiz/tufe-eylul-ppk-2026-09-03.mdx",
}
# Belirli bir commit'teki hâliyle dondurulan girdiler (arşiv adı → (commit, depo yolu)).
# Ağustos'un yayılım ölçüleri Ağustos verisiyle 9 Eylül'de hesaplanmıştı; bugünkü değerle
# farkı bu ölçünün bir aylık revizyonudur ve ancak o günkü dosyadan ölçülür.
GIT_GIRDILER = {
    "dagilim_0909.csv": ("36cd300d3bd072de151834f90403ade7e092adb0",
                         "Aktarılacak Projeler/Enflasyon/data/dagilim.csv"),
}
# Hattın `data/sa_onceki.csv`si ARŞİVLENMEZ: hat her koşuda onu `sa.csv`nin aynısı olarak yazar
# (bir önceki arındırma sürümünü taşımaz). Uç nokta revizyonları hattın uç nokta testinden gelir
# (`metrik.vintage_revizyon`: ham seri 1–6 ay kesilip yeniden arındırılır) ve arşivlenmiş hat
# özetinden okunur; testin girdisi olan endeks düzeyleri arşivdedir.


def _commit(yol: Path) -> str | None:
    try:
        s = subprocess.run(["git", "-C", str(KOK), "log", "-1", "--format=%H %cI",
                            "--", str(yol.relative_to(KOK))],
                           capture_output=True, text=True, timeout=30)
        return s.stdout.strip() or None
    except Exception:                                           # noqa: BLE001
        return None


def main() -> int:
    HEDEF.mkdir(parents=True, exist_ok=True)
    kp = HEDEF / "kunye.json"
    kunye = json.loads(kp.read_text(encoding="utf-8")) if kp.exists() else {}
    kunye.setdefault("cipa", CIPA)
    kunye.setdefault("dosyalar", {})
    simdi = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    yeni = 0
    kalemler = [(ad, kaynak, None) for ad, kaynak in GIRDILER.items()]
    kalemler += [(ad, KOK / yol, commit) for ad, (commit, yol) in GIT_GIRDILER.items()]
    for ad, kaynak, commit in kalemler:
        if commit:
            ham = subprocess.run(["git", "-C", str(KOK), "show", f"{commit}:{kaynak.relative_to(KOK)}"],
                                 capture_output=True, check=True, timeout=60).stdout
        else:
            if not kaynak.exists():
                raise SystemExit(f"  ! kaynak yok: {kaynak.relative_to(KOK)}")
            ham = kaynak.read_bytes()
        oz = hashlib.sha256(ham).hexdigest()
        hedef = HEDEF / f"{ad}.gz"
        if hedef.exists():
            eski = hashlib.sha256(gzip.decompress(hedef.read_bytes())).hexdigest()
            if eski != oz:
                raise SystemExit(f"  ! {hedef.name} var ve içeriği farklı — üzerine yazılmaz "
                                 f"(yeni pencere yeni bir çıpa dizinidir)")
            if ad not in kunye["dosyalar"]:
                raise SystemExit(f"  ! {hedef.name} var ama künyede yok — arşiv tutarsız")
            print(f"  = {hedef.name}  (aynı içerik, dokunulmadı)")
            continue
        hedef.write_bytes(gzip.compress(ham, 9, mtime=0))
        kunye["dosyalar"][ad] = {"sha256": oz, "bayt": len(ham),
                                 "kaynak": str(kaynak.relative_to(KOK)),
                                 "kaynak_commit": commit or _commit(kaynak),
                                 "kopyalama_ani": simdi}
        yeni += 1
        print(f"  ✓ {hedef.name}  {len(ham):>9} bayt")
    kunye["kaynak"] = {
        "enflasyon": "TÜİK TÜFE (2025=100) ve Yİ-ÜFE, TCMB EVDS ana ve özel kapsamlı göstergeler, "
                     "üç haneli alt gruplar; TCMB Piyasa Katılımcıları Anketi; TCMB ağırlıklı ortalama "
                     "fonlama maliyeti (Enflasyon hattı, 05.10.2026 koşusu)",
        "piyasa": "DİBS Verim Eğrisi, Fonlama ve Likidite, TÜFEX Başabaş panoları — 2 Ekim 2026 kapanışı "
                  "(veri yayımından önceki seans)",
        "alinti": "TCMB PPK karar metni (10 Eylül 2026) ve toplantı özeti (17 Eylül 2026) paragrafları; "
                  "3 Eylül 2026 tarihli Ağustos TÜFE yazısı",
        "revizyon": "uç nokta revizyonları hattın uç nokta testinden (ham seri 1–6 ay kesilip yeniden "
                    "arındırılır) gelir ve arşivlenmiş hat özetinden okunur; Ağustos yayılım ölçülerinin "
                    "9 Eylül hâli dagilim_0909.csv",
    }
    kp.write_text(json.dumps(kunye, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"  künye: {len(kunye['dosyalar'])} dosya ({yeni} yeni), çıpa {CIPA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
