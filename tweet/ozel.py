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

# v2 medya ucu 'media.write' kapsamı ister; X'in yeni konsolunun kapsam
# listesinde media.write SEÇENEĞİ YOK (30.08'de görüldü). Eski v1.1 ucu ise
# OAuth 2.0 kullanıcı jetonunu tweet.write kapsamıyla kabul ediyor — önce v2
# denenir, 403'te v1.1'e düşülür.
MEDYA_UC = "https://api.x.com/2/media/upload"
MEDYA_UC_ESKI = "https://upload.twitter.com/1.1/media/upload.json"


def _yukle(erisim: str, yol: Path) -> str:
    import requests

    def dene(uc: str):
        with yol.open("rb") as f:
            return requests.post(
                uc, timeout=60,
                headers={"Authorization": f"Bearer {erisim}"},
                files={"media": (yol.name, f, "image/png")},
                data={"media_category": "tweet_image"})

    yanit = dene(MEDYA_UC)
    if yanit.status_code == 403:
        print(f"· v2 medya ucu 403 (media.write yok) — v1.1 ucuna düşülüyor")
        yanit = dene(MEDYA_UC_ESKI)
    if yanit.status_code == 403:
        # Jeton kapsamı görsele yetmiyor ve konsol media.write sunmuyor
        # (30.08 ölçüldü). Görsel EKLENTİDİR: yüklenemiyorsa tweet metniyle
        # devam eder — koşuyu düşürmek metni de rehin alırdı.
        print("::warning::görsel yüklenemedi (iki uçta 403, media.write "
              "kapsamı yok) — tweet görselsiz gönderiliyor")
        return None
    if yanit.status_code not in (200, 201):
        raise SystemExit(f"medya yükleme düştü (HTTP {yanit.status_code}): "
                         f"{yanit.text[:300]}")
    veri = yanit.json().get("data") or yanit.json()
    kimlik = veri.get("id") or veri.get("media_id_string") or veri.get("media_id")
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
    p.add_argument("--sil", help="önce bu id'li tweeti sil (düzeltme akışı: "
                                 "eski gönderi kaldırılıp yenisi atılır)")
    a = p.parse_args()

    metin = Path(a.metin).read_text(encoding="utf-8").strip()
    if "http" in metin.lower():
        raise SystemExit("metinde link var — kural: tweetlerde link verilmez")
    # OKUR DİLİ KAPISI. Kalıplar ortak/okur_dili.py'de; aynı liste bülten
    # denetiminde ve sayfa sınavında da koşuyor. Tweet en kısa metin ve en
    # geniş okur kitlesi: "ozet.json'dan okunur" ya da "ilk sürümde şöyle
    # demiştik" cümlesinin buraya girmesi, hiçbir okurun anlamayacağı bir
    # satırı en görünür yere koymak demek.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ortak"))
    import okur_dili
    bulgu = okur_dili.tara(metin)
    if bulgu:
        dokum = " · ".join(f"{a_}: {e!r} (satır {s_})" for a_, e, s_ in bulgu[:5])
        raise SystemExit(
            f"metinde okura değil kendimize yazan dil var — {dokum}. "
            "Yapım kararları ve sürüm tarihçesi tweete girmez.")
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
    if a.sil:
        yanit = requests.delete(f"{gonder.UC}/{a.sil}", timeout=30,
                                headers={"Authorization": f"Bearer {erisim}"})
        if yanit.status_code == 200 and yanit.json().get("data", {}).get("deleted"):
            print(f"· eski tweet silindi: {a.sil}")
        else:
            print(f"::warning::eski tweet silinemedi ({yanit.status_code}): "
                  f"{yanit.text[:150]} — yenisi yine de gönderiliyor")
    govde: dict = {"text": metin}
    if resimler:
        idler = [k for k in (_yukle(erisim, r) for r in resimler) if k]
        if idler:
            govde["media"] = {"media_ids": idler}
    yanit = requests.post(gonder.UC, json=govde, timeout=30,
                          headers={"Authorization": f"Bearer {erisim}"})
    if yanit.status_code not in (200, 201):
        raise SystemExit(f"tweet gönderilemedi (HTTP {yanit.status_code}): "
                         f"{yanit.text[:300]}")
    print(f"✓ gönderildi — id: {yanit.json()['data']['id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
