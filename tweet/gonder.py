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

Kimlik: OAuth 2.0 kullanıcı bağlamı (X'in yeni geliştirici konsolu OAuth 1.0a
access token üretmiyor). X'te refresh token TEK KULLANIMLIK ve her yenilemede
DÖNER: yeni refresh token gelir, eskisi ölür. Bu yüzden güncel refresh token
tweet/oauth2.enc dosyasında ŞİFRELİ tutulur (anahtar: TW_KILIT secret'ı;
dosya depoda ama anahtarsız açılamaz) ve iş akışı her koşuda commit'ler.
Yenisi, gönderimden ÖNCE diske yazılır: koşu tweet atarken ölse bile jeton
kaybolmaz. Jeton yine de yanarsa (dosya ile X'in kaydı ayrışırsa) çare:
konsoldan yeni refresh token al, TW_REFRESH_TOKEN secret'ını güncelle ve
tweet/oauth2.enc dosyasını depodan sil — ilk koşu kendini yeniden kurar.

Gerekenler (repo secret): TW_CLIENT_ID · TW_CLIENT_SECRET · TW_KILIT
(rastgele uzun parola) · TW_REFRESH_TOKEN (yalnız ilk kurulum; sonrası
oauth2.enc'den döner)
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
JETON_DOSYA = BURASI / "oauth2.enc"
UC = "https://api.x.com/2/tweets"
JETON_UC = "https://api.x.com/2/oauth2/token"
ANAHTARLAR = ("TW_CLIENT_ID", "TW_CLIENT_SECRET", "TW_KILIT")


def _kilit():
    """TW_KILIT parolasından Fernet anahtarı türetir (sha256 → urlsafe b64)."""
    import base64
    import hashlib
    from cryptography.fernet import Fernet
    ham = hashlib.sha256(os.environ["TW_KILIT"].encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(ham))


def _refresh_oku(dosya: Path) -> str | None:
    """Güncel refresh token: önce şifreli dosya, yoksa ilk-kurulum secret'ı."""
    if dosya.exists():
        try:
            return _kilit().decrypt(dosya.read_bytes()).decode("utf-8")
        except Exception:                                      # noqa: BLE001
            raise SystemExit(
                f"{dosya.name} çözülemedi — TW_KILIT değişmiş ya da dosya bozuk. "
                "Konsoldan yeni refresh token alıp TW_REFRESH_TOKEN'ı güncelle "
                "ve bu dosyayı depodan sil.")
    return os.environ.get("TW_REFRESH_TOKEN") or None


def _erisim_al(dosya: Path) -> str:
    """Refresh token'ı kullanır: erişim jetonu döner, DÖNEN yeni refresh
    token gönderimden önce şifreli dosyaya yazılır (tek kullanımlık jeton
    koşu ortasında ölürsek de kaybolmasın)."""
    import requests
    refresh = _refresh_oku(dosya)
    if not refresh:
        raise SystemExit(
            "refresh token yok: ne tweet/oauth2.enc ne TW_REFRESH_TOKEN. "
            "Konsoldan refresh token alıp TW_REFRESH_TOKEN secret'ına ekle.")
    yanit = requests.post(
        JETON_UC,
        data={"grant_type": "refresh_token", "refresh_token": refresh,
              "client_id": os.environ["TW_CLIENT_ID"]},
        auth=(os.environ["TW_CLIENT_ID"], os.environ["TW_CLIENT_SECRET"]),
        timeout=30)
    if yanit.status_code != 200:
        raise SystemExit(
            f"jeton yenileme düştü (HTTP {yanit.status_code}): {yanit.text[:300]}\n"
            "Refresh token yanmış olabilir (tek kullanımlıktır ve başka bir "
            "yerde kullanıldıysa ölür). Çare: konsoldan yeni refresh token → "
            "TW_REFRESH_TOKEN secret'ını güncelle → tweet/oauth2.enc'i sil.")
    d = yanit.json()
    yeni = d.get("refresh_token")
    if yeni:
        dosya.write_bytes(_kilit().encrypt(yeni.encode("utf-8")))
        print("· refresh token döndü — oauth2.enc güncellendi (commit edilecek)")
    return d["access_token"]


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


def _gonder_zincir(zincir: list[str], erisim: str) -> list[str]:
    """Zinciri sırayla gönderir, her tweet öncekine yanıt olur. ID listesi döner."""
    import requests
    idler: list[str] = []
    for i, metin in enumerate(zincir):
        govde: dict = {"text": metin}
        if idler:
            govde["reply"] = {"in_reply_to_tweet_id": idler[-1]}
        yanit = requests.post(
            UC, json=govde, timeout=30,
            headers={"Authorization": f"Bearer {erisim}"})
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
    anahtar_var = (all(os.environ.get(k) for k in ANAHTARLAR)
                   and (JETON_DOSYA.exists() or os.environ.get("TW_REFRESH_TOKEN")))
    kuru = a.kuru or not anahtar_var
    if not a.kuru and not anahtar_var:
        print("::warning::TW_* anahtarları eksik — kuru koşu. Zincir gönderilmedi; "
              "TW_CLIENT_ID, TW_CLIENT_SECRET, TW_KILIT ve TW_REFRESH_TOKEN "
              "repo secret'ına eklenince gönderim açılır.")

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

    erisim: str | None = None
    for anahtar, zincir in is_listesi:
        _bas(zincir, anahtar + (" · KURU KOŞU" if kuru else ""))
        if kuru:
            continue
        if erisim is None:
            erisim = _erisim_al(JETON_DOSYA)
        idler = _gonder_zincir(zincir, erisim)
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
