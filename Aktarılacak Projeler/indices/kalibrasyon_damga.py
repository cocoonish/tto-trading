"""Bir endeks okumasi HANGI KALIBRASYONUN parametreleriyle kuruldu — tek tanim.

NEDEN VAR. Canli endeks optimize parametrelerle kurulur (toplulastirma yontemi,
yari omur, donusum…). Parametreler yenilendigi gun ayni haber akisi baska bir
sayi verir; snapshot'tan snapshot'a degisim o gun HABERI degil MODELI olcer.
Bulten bu degisimi "haber tonunun olagandisi hareketi" diye basardi ve σ da iki
modelin farklarini karistirirdi. Kural: degisim ve oynaklik YALNIZ ayni
kalibrasyonun iki okumasi arasinda kurulur (ozet_uret.py), tarihce figuru
kalibrasyon degisimini isaretler (web_cikti.ciz_tarihce).

Yeni snapshot'lar kimligi kendisi yazar (`kalibrasyon` alani =
optimized_params.json damgasi). Eskiler yazmiyordu; onlarin kimligi KAYITLI
kalibrasyon tarihlerinden cozulur — 13.04.2026 (sayfanin kaydi; saati
bilinmiyor, gunun basi alindi) ve 22.07.2026 19:23:33 UTC (parametre
dosyasinin damgasi; 22.07 snapshot'i 19:26'da, yani yeni parametrelerle).
"""

from __future__ import annotations

import json

import config

# Kimlik SANIYE cozunurlugundedir: 22.07 dosyasi 15 varlik damgasini ayni
# saniyenin farkli mikrosaniyelerine yazmisti (…628199 → …628227); en buyugunu
# yeni snapshot'a, en kucugunu bu listeye yazmak AYNI kalibrasyonu iki kimlik
# yapar ve kural ertesi gunku ilk kosuda sahte bir "kalibrasyon degisti" basardi.
GECMIS = [
    "2026-04-13T00:00:00",
    "2026-07-22T19:23:33",
]


def _saniye(damga) -> str | None:
    """ISO damgayi UTC saniyesine indir: 'YYYY-AA-GGTSS:DD:SS'."""
    if not damga:
        return None
    from datetime import datetime, timezone
    try:
        t = datetime.fromisoformat(str(damga))
    except ValueError:
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def guncel(yol: str | None = None) -> str | None:
    """Parametre dosyasinin kalibrasyon kimligi (varlik damgalarinin en yenisi, saniye)."""
    try:
        with open(yol or config.OPTIMIZED_PARAMS, encoding="utf-8") as f:
            par = json.load(f)
    except (OSError, ValueError):
        return None
    damga = [_saniye(v.get("timestamp")) for v in par.values()
             if isinstance(v, dict) and v.get("timestamp")]
    damga = [d for d in damga if d]
    return max(damga) if damga else None


def kimlik(kayit: dict) -> str | None:
    """Snapshot'in kalibrasyon kimligi — yazilmamissa tarihinden (GECMIS)."""
    k = _saniye(kayit.get("kalibrasyon"))
    if k:
        return k
    ts = _saniye(kayit.get("timestamp"))
    if not ts:
        return None
    once = [g for g in GECMIS if g <= ts]
    return once[-1] if once else None


def ad(k: str | None, saatli: bool = False) -> str:
    """Okura giden ad: GG.AA.YYYY (saatli=True: GG.AA.YYYY SS:DD UTC)."""
    if not k:
        return "—"
    y, a, g = str(k)[:10].split("-")
    return f"{g}.{a}.{y}" + (f" {str(k)[11:16]} UTC" if saatli and len(str(k)) >= 16 else "")


def degisim_metni(once: str | None, sonra: str | None) -> str:
    """'22.07.2026 → 03.10.2026'; ayni gune dusen iki kimlik saatiyle yazilir."""
    saatli = ad(once) == ad(sonra)
    return f"{ad(once, saatli)} → {ad(sonra, saatli)}"
