#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tweet zincirini X'e GÖNDERİR — defterli, kuru-koşulu, bayat-korumalı.

    python3 tweet/gonder.py                # bugünün yazılmış içeriğini gönder
    python3 tweet/gonder.py --kuru         # göndermeden zinciri bas
    python3 tweet/gonder.py --tarih 2026-08-30 --tur teknik

Sigortalar (araçta, rutin metninde değil):

· DEFTER (tweet/defter.json): her (tür, tarih) EN FAZLA BİR KEZ gönderilir.
  Defter gönderimden sonra yazılır ve iş akışı onu commit'ler; ikinci koşu
  aynı içeriği görüp geçer. Kuru koşu deftere DOKUNMAZ.
· BAYAT KORUMASI: --tarih verilmedikçe yalnız BUGÜNÜN (UTC) içeriği
  gönderilir. Eski bir bülteni gece yarısından sonra tweetlemek okura "yeni"
  diye eski haber satmaktır; kaçan gün sessizce atlanır, defterlenmez.
· ANAHTAR YOKSA DÜŞMEZ: TW_* ortam değişkenleri boşsa kuru çıktı basılır ve
  0 ile çıkılır — anahtarlar repo secret'ına eklenene dek iş akışı yeşil
  kalır, zincir metni logda görünür.

Kimlik: OAuth 1.0a kullanıcı bağlamı (X API v2 POST /2/tweets).
Gerekenler: TW_API_KEY · TW_API_SECRET · TW_ACCESS_TOKEN · TW_ACCESS_SECRET
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import uret  # noqa: E402

BURASI = Path(__file__).resolve().parent
DEFTER = BURASI / "defter.json"
UC = "https://api.x.com/2/tweets"
ANAHTARLAR = ("TW_API_KEY", "TW_API_SECRET", "TW_ACCESS_TOKEN", "TW_ACCESS_SECRET")


def _defter_oku(yol: Path) -> dict:
    if yol.exists():
        try:
            return json.loads(yol.read_text(encoding="utf-8"))
        except Exception:                                      # noqa: BLE001
            pass
    return {}


def _bas(zincir: list[str], baslik: str) -> None:
    print(f"\n── {baslik} ({len(zincir)} tweet) " + "─" * 30)
    for i, t in enumerate(zincir, 1):
        print(f"\n[{i}/{len(zincir)}] ({len(t)} karakter)")
        print(t)
    print()


def _gonder_zincir(zincir: list[str]) -> list[str]:
    """Zinciri sırayla gönderir, her tweet öncekine yanıt olur. ID listesi döner."""
    from requests_oauthlib import OAuth1Session
    oturum = OAuth1Session(
        os.environ["TW_API_KEY"], os.environ["TW_API_SECRET"],
        os.environ["TW_ACCESS_TOKEN"], os.environ["TW_ACCESS_SECRET"])
    idler: list[str] = []
    for i, metin in enumerate(zincir):
        govde: dict = {"text": metin}
        if idler:
            govde["reply"] = {"in_reply_to_tweet_id": idler[-1]}
        yanit = oturum.post(UC, json=govde, timeout=30)
        if yanit.status_code not in (200, 201):
            raise SystemExit(
                f"tweet {i + 1}/{len(zincir)} gönderilemedi "
                f"(HTTP {yanit.status_code}): {yanit.text[:300]}\n"
                + (f"Zincir yarım kaldı — atılanlar: {idler}. Defter "
                   "YAZILMADI; sorun giderilince koşu aynı içeriği baştan "
                   "dener, yarım zincir elle silinmeli." if idler else ""))
        idler.append(yanit.json()["data"]["id"])
        time.sleep(1)
    return idler


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--tur", choices=("bulten", "teknik", "hepsi"), default="hepsi")
    p.add_argument("--tarih", help="varsayılan: bugün (UTC); bayat koruması "
                                   "yalnız varsayılanda uygulanır")
    p.add_argument("--kuru", action="store_true", help="gönderme, yalnız bas")
    p.add_argument("--defter", help="defter yolu (sınama için)")
    a = p.parse_args()

    defter_yolu = Path(a.defter) if a.defter else DEFTER
    tarih = a.tarih or dt.datetime.now(dt.timezone.utc).date().isoformat()
    anahtar_var = all(os.environ.get(k) for k in ANAHTARLAR)
    kuru = a.kuru or not anahtar_var
    if not a.kuru and not anahtar_var:
        print("::warning::TW_* anahtarları yok — kuru koşu. Zincir gönderilmedi; "
              "anahtarlar repo secret'ına eklenince gönderim açılır.")

    defter = _defter_oku(defter_yolu)
    is_listesi: list[tuple[str, list[str]]] = []

    if a.tur in ("bulten", "hepsi"):
        b = uret.yazilmis_bulten(tarih)
        if b and f"bulten:{tarih}" not in defter:
            is_listesi.append((f"bulten:{tarih}", uret.bulten_zinciri(b)))
    if a.tur in ("teknik", "hepsi"):
        t = uret.yazilmis_teknik(tarih)
        if t and f"teknik:{tarih}" not in defter:
            is_listesi.append((f"teknik:{tarih}", uret.teknik_zinciri(t)))

    if not is_listesi:
        print(f"{tarih}: gönderilecek yeni içerik yok "
              "(yazılmış değil ya da defterde kayıtlı).")
        return 0

    for anahtar, zincir in is_listesi:
        _bas(zincir, anahtar + (" · KURU KOŞU" if kuru else ""))
        if kuru:
            continue
        idler = _gonder_zincir(zincir)
        defter[anahtar] = {
            "idler": idler,
            "zaman": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        }
        defter_yolu.write_text(
            json.dumps(defter, ensure_ascii=False, indent=1) + "\n",
            encoding="utf-8")
        print(f"✓ {anahtar} gönderildi — {len(idler)} tweet, kök: {idler[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
