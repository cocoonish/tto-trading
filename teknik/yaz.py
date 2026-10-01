#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Haftalık teknik analiz ARŞİVİNİN düzeltme kapısı.

Haftalık teknik analiz bülteni 27.09.2026 sayısıyla sona erdi (kullanıcı
kararı, 01.10.2026): ölçüm iş akışı ve ölçüm kodu kaldırıldı, yayımlanmış beş
sayı (30.08–27.09) arşivde kendi adreslerinde duruyor. Arşivdeki bir sayıya
yeni yorum YAZILMAZ — yayımlanmış metin değiştirilmez. Geriye tek meşru iş
kalır: yayımlanmış bir SAYININ düzeltilmesi (okur eski sayıya göre karar vermiş
olabilir). Bu kapı yalnız onu yazar.

    python3 teknik/yaz.py yama.json --tarih 2026-09-27
    cat yama.json | python3 teknik/yaz.py - --tarih 2026-09-27

Yama yalnız `duzeltmeler` taşır: [{alan, eski, yeni, sebep?, tarih?}] — bültenle
aynı sözleşme (bulten/yaz.duzeltmeleri_dogrula). Var olan kayıtların ÜSTÜNE
eklenir; eski kayıt silinmez. Hedef, yayımlanmış (yazili=true) bir arşiv sayısı
olmak zorunda. Düzeltme metni de okur dili ve tavsiye dili kapısından geçer.
Sayfa "Düzeltmeler" bölümü ve /duzeltmeler/ listesi bu alandan okur.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent
VERI = KOK / "site" / "src" / "data" / "teknik"
sys.path.insert(0, str(KOK / "ortak"))
from tavsiye_dili import TAVSIYE  # noqa: E402  — bülten/analiz/tweet kapılarıyla AYNI kalıp
import okur_dili  # noqa: E402


def _bulten_yaz():
    # Bülten de bir yaz.py taşıyor; ad çakışmasın diye yoldan, ayrı adla yüklenir.
    spec = importlib.util.spec_from_file_location("bulten_yaz", KOK / "bulten" / "yaz.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("yama", help="yama JSON dosyası ya da '-' (stdin)")
    p.add_argument("--tarih", required=True,
                   help="düzeltilecek arşiv sayısı (YYYY-AA-GG)")
    a = p.parse_args()

    hedef = VERI / f"{a.tarih}.json"
    if not hedef.exists():
        raise SystemExit(f"arşivde {hedef.name} yok — teknik analiz arşivi "
                         "yalnız yayımlanmış sayıları taşır")
    b = json.loads(hedef.read_text(encoding="utf-8"))
    if not b.get("yazili"):
        raise SystemExit(f"{hedef.name} yayımlanmamış bir ölçüm — düzeltme yalnız "
                         "yayımlanmış sayıya yazılır")

    ham = sys.stdin.read() if a.yama == "-" else Path(a.yama).read_text(encoding="utf-8")
    yama = json.loads(ham)
    yabanci = [k for k in yama if k != "duzeltmeler"]
    if yabanci:
        raise SystemExit(
            f"arşiv sayısına yalnız düzeltme kaydı yazılır; reddedilen alanlar: "
            f"{', '.join(yabanci)}. Haftalık teknik analiz 27.09.2026 sayısıyla sona "
            "erdi; yayımlanmış metin değiştirilmez.")
    yeni = _bulten_yaz().duzeltmeleri_dogrula(yama.get("duzeltmeler"))
    if not yeni:
        print("yama boş — hiçbir kayıt eklenmedi")
        return 0

    metin = " ".join(f"{d['alan']} {d['eski']} {d['yeni']} {d['sebep']}" for d in yeni)
    t = TAVSIYE.search(re.sub(r"<[^>]+>", " ", metin))
    if t:
        raise SystemExit(f"TAVSİYE DİLİ — yazma reddedildi: {t.group(0)!r}")
    bulgu = okur_dili.tara(metin)
    if bulgu:
        dokum = "\n".join(f"  {a_}: {e!r} (satır {s_})" for a_, e, s_ in bulgu)
        raise SystemExit("OKURA DEĞİL KENDİMİZE YAZAN DİL — yazma reddedildi:\n" + dokum)

    b["duzeltmeler"] = list(b.get("duzeltmeler") or []) + yeni
    # Yayım damgası (yorum_zamani) DEĞİŞMEZ: düzeltme bir yayın olayı değildir ve
    # künye ile besleme sayının yayımlandığı anı göstermeye devam eder.
    b["duzeltme_zamani"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    b["yazi_surumu"] = int(b.get("yazi_surumu") or 0) + 1
    hedef.write_text(json.dumps(b, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"yazıldı: {hedef.name} — {len(yeni)} düzeltme kaydı "
          f"(toplam {len(b['duzeltmeler'])})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
