"""Yayın takvimi ↔ iş akışı cron'ları — TEK karşılaştırma.

Hakkında sayfası saatleri site/src/data/yayin_takvimi.json'dan okur; her adımın
saati ilgili iş akışının cron satırından (UTC+3, sabit) türetilmiş olmalıdır.
Bu fonksiyon iki kaynağı karşılaştırır ve ayrışmaları liste olarak döndürür
(boş liste = uyum). İki kapı onu çağırır: bulten/duman.py (veri/bülten
koşularında) ve site/tools/sayfa_sinavi.py (yayın kapısı) — sayfayı yayımlayan
kapı kaymayı görmezse sayfa eski saati anlatmaya devam ederdi.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

CRON = re.compile(r"^\s*-\s*cron:\s*'(\d+) (\d+) (\S+) (\S+) (\S+)'", re.M)
GUNLER = {"hafta içi": {"1-5"}, "pazar": {"0", "7"}}
EN_AZ_ADIM = 6


def karsilastir(kok: Path) -> list[str]:
    """JSON'daki her adımı cron'la karşılaştır; bulguları döndür (boş = uyum)."""
    bulgu: list[str] = []
    yol = kok / "site" / "src" / "data" / "yayin_takvimi.json"
    try:
        tk = json.loads(yol.read_text(encoding="utf-8"))
    except Exception as ex:                                        # noqa: BLE001
        return [f"yayin_takvimi.json okunamadı: {ex}"]
    n = 0
    for y in tk.get("yayinlar", []):
        ad_y = y.get("yayin", "?")
        if re.search(r"\b\d{1,2}:\d{2}\b", str(y.get("aciklama", ""))):
            bulgu.append(f"{ad_y}: açıklamada elle saat var — saat yalnız adımlarda (cron'dan türetilir)")
        for ad in y.get("adimlar", []):
            yml_yolu = kok / ".github" / "workflows" / str(ad.get("is_akisi", ""))
            if not yml_yolu.exists():
                bulgu.append(f"{ad_y} · {ad.get('ad')}: iş akışı yok ({ad.get('is_akisi')})")
                continue
            cronlar = CRON.findall(yml_yolu.read_text(encoding="utf-8"))
            i = int(ad.get("cron_no", 0))
            if len(cronlar) <= i:
                bulgu.append(f"{ad_y} · {ad.get('ad')}: {ad.get('is_akisi')} {i}. cron yok ({len(cronlar)} var)")
                continue
            dk, saat, _gun, _ay, hafta_gunu = cronlar[i]
            if int(saat) + 3 >= 24:
                bulgu.append(f"{ad_y} · {ad.get('ad')}: cron {saat} UTC İstanbul'da güne taşar")
            ist = f"{(int(saat) + 3) % 24:02d}:{int(dk):02d}"
            if ist != ad.get("istanbul"):
                bulgu.append(f"{ad_y} · {ad.get('ad')}: takvim {ad.get('istanbul')} diyor, "
                             f"{ad.get('is_akisi')} cron {ist} İstanbul")
            beklenen = GUNLER.get(str(y.get("gunler", "")))
            if beklenen is not None:
                izinli = beklenen | ({"*"} if y.get("gunler") == "hafta içi" else set())
                if hafta_gunu not in izinli:
                    bulgu.append(f"{ad_y} · {ad.get('ad')}: takvim '{y.get('gunler')}' diyor, "
                                 f"{ad.get('is_akisi')} cron gün alanı '{hafta_gunu}'")
            n += 1
    if n < EN_AZ_ADIM:
        bulgu.append(f"takvimde çok az adım sınandı ({n} < {EN_AZ_ADIM})")
    return bulgu
