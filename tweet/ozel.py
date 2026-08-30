#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tek seferlik özel tweet — metin dosyasından, istenirse görsellerle.

    python3 tweet/ozel.py --metin tweet/ozel/x.txt --resim a.png --resim b.png
    ... --gonder            # verilmezse KURU: yalnız basar

Düzenli bültenlerin dışında kalan gönderiler için (tema tweetleri, veri
duyuruları). Kimlik altyapısı gonder.py ile ortak: OAuth 2.0, dönen refresh
token şifreli kasaya yazılır (iş akışı commit'ler). Kurallar aynı: LİNK
YAZILMAZ (metinde http görülürse koşu düşer), defter tutulmaz — tek seferlik
gönderimi çağıran tekrarlamamaktan sorumludur.

Görseller X API v2 medya ucuna yüklenir (POST /2/media/upload). Bu uç
'media.write' kapsamı ister; refresh token o kapsamsız üretildiyse 403 döner
ve hata ne yapılacağını söyler.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gonder  # noqa: E402 — _erisim_al, JETON_DOSYA, UC ortak

MEDYA_UC = "https://api.x.com/2/media/upload"


def _yukle(erisim: str, yol: Path) -> str:
    import requests
    with yol.open("rb") as f:
        yanit = requests.post(
            MEDYA_UC, timeout=60,
            headers={"Authorization": f"Bearer {erisim}"},
            files={"media": (yol.name, f, "image/png")},
            data={"media_category": "tweet_image"})
    if yanit.status_code == 403:
        raise SystemExit(
            f"medya yükleme 403: {yanit.text[:200]}\n"
            "Refresh token büyük olasılıkla 'media.write' kapsamı olmadan "
            "üretildi. Konsoldan kapsamlara media.write ekleyip token'ı "
            "yeniden üret, TW_REFRESH_TOKEN'ı güncelle, tweet/oauth2.enc'i sil.")
    if yanit.status_code not in (200, 201):
        raise SystemExit(f"medya yükleme düştü (HTTP {yanit.status_code}): "
                         f"{yanit.text[:300]}")
    veri = yanit.json().get("data") or yanit.json()
    kimlik = veri.get("id") or veri.get("media_id_string")
    if not kimlik:
        raise SystemExit(f"medya yanıtında id yok: {yanit.text[:200]}")
    print(f"· görsel yüklendi: {yol.name} → {kimlik}")
    return str(kimlik)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--metin", required=True, help="tweet metni dosyası")
    p.add_argument("--resim", action="append", default=[],
                   help="eklenecek PNG (tekrarlanabilir, en çok 4)")
    p.add_argument("--gonder", action="store_true",
                   help="gerçekten gönder (verilmezse kuru)")
    a = p.parse_args()

    metin = Path(a.metin).read_text(encoding="utf-8").strip()
    if "http" in metin.lower():
        raise SystemExit("metinde link var — kural: tweetlerde link verilmez")
    if len(metin) > 3800:
        raise SystemExit(f"metin çok uzun ({len(metin)} karakter)")
    if len(a.resim) > 4:
        raise SystemExit("en çok 4 görsel")
    resimler = [Path(r) for r in a.resim]
    for r in resimler:
        if not r.exists():
            raise SystemExit(f"görsel yok: {r}")

    print(f"── özel tweet ({len(metin)} karakter, {len(resimler)} görsel)"
          + (" · KURU" if not a.gonder else ""))
    print(metin)
    if not a.gonder:
        return 0

    import requests
    erisim = gonder._erisim_al(gonder.JETON_DOSYA)
    govde: dict = {"text": metin}
    if resimler:
        govde["media"] = {"media_ids": [_yukle(erisim, r) for r in resimler]}
    yanit = requests.post(gonder.UC, json=govde, timeout=30,
                          headers={"Authorization": f"Bearer {erisim}"})
    if yanit.status_code not in (200, 201):
        raise SystemExit(f"tweet gönderilemedi (HTTP {yanit.status_code}): "
                         f"{yanit.text[:300]}")
    print(f"✓ gönderildi — id: {yanit.json()['data']['id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
