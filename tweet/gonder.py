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
import hashlib
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import uret  # noqa: E402
import analiz as analiz_m  # noqa: E402
import denetim as denetim_m  # noqa: E402

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent
DEFTER = BURASI / "defter.json"
# SİTE AYNASI YOK. Defter bir zamanlar site/src/data/tweet/defter.json'a da
# yazılıyordu ve sayfa künyesi oradan "X gönderisi ↗" bağı kuruyordu. Site X
# gönderisini artık okura göstermiyor (kullanıcı kararı), o yüzden ayna da
# yazılmıyor: yazılan ama okunmayan bir dosya, bir gün yeniden okunur.
# Gönderilen METNİN arşivi. Defter yalnız kimlik taşıyor; X'te silinen ya da
# düzeltilen bir gönderinin ne dediği depoda kalmıyordu. Her gerçek gönderim
# metniyle birlikte buraya yazılır ve iş akışı commit'ler.
ARSIV = BURASI / "arsiv"
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
    """Defter bozuksa DURUR. Eskiden bozuk JSON sessizce boş defter sayılıyordu:
    boş defter = "hiçbir şey gönderilmedi" = her şey yeniden gönderilir."""
    if not yol.exists():
        return {}
    try:
        return json.loads(yol.read_text(encoding="utf-8"))
    except Exception as e:                                     # noqa: BLE001
        raise SystemExit(f"{yol} okunamadı ({e}) — defter bozuk; elle düzelt, "
                         "boş sayıp yeniden göndermek mükerrer gönderi demek.")


def _bas(zincir: list[str], baslik: str) -> None:
    print(f"\n── {baslik} ({len(zincir)} tweet) " + "─" * 30)
    for i, t in enumerate(zincir, 1):
        print(f"\n[{i}/{len(zincir)}] ({len(t)} karakter)")
        print(t)
    print()


def _arsivle(anahtar: str, zincir: list[str], idler: list[str], zaman: str) -> Path:
    """Gönderilen metni depoya yaz: tweet/arsiv/<tur>-<ad>.txt."""
    ARSIV.mkdir(parents=True, exist_ok=True)
    yol = ARSIV / (anahtar.replace(":", "-") + ".txt")
    baslik = (f"# {anahtar} · {zaman} · "
              + (" ".join(f"https://x.com/i/status/{i}" for i in idler) or "kimlik yok"))
    yol.write_text(baslik + "\n\n" + "\n\n---\n\n".join(zincir) + "\n", encoding="utf-8")
    return yol


def _defter_yaz(defter_yolu: Path, defter: dict) -> None:
    defter_yolu.write_text(json.dumps(defter, ensure_ascii=False, indent=1) + "\n",
                           encoding="utf-8")


def _gonder_zincir(zincir: list[str], erisim: str) -> list[str]:
    """Zinciri sırayla gönderir, her tweet öncekine yanıt olur. ID listesi döner.
    429 ve 5xx'te BİR kez bekleyip yeniden dener — geçici bir kesinti için sabahı
    kaybetmemek; iki kez düşerse gerçekten düşmüştür."""
    import requests
    # LİNK YASAĞI — denetim kapısından bağımsız ikinci kilit: zincirin herhangi
    # bir parçasında link varsa HİÇBİR parça gönderilmez (yarım zincir kalmaz).
    for metin in zincir:
        b = denetim_m.link_var(metin)
        if b:
            raise SystemExit(f"tweet metninde link ({b!r}) — kural: tweetlerde HİÇ link "
                             "kullanılmaz; gönderim durdu, defter yazılmadı.")
    idler: list[str] = []
    for i, metin in enumerate(zincir):
        govde: dict = {"text": metin}
        if idler:
            govde["reply"] = {"in_reply_to_tweet_id": idler[-1]}
        for deneme in (1, 2):
            yanit = requests.post(
                UC, json=govde, timeout=30,
                headers={"Authorization": f"Bearer {erisim}"})
            if yanit.status_code in (429, 500, 502, 503, 504) and deneme == 1:
                print(f"::warning::X {yanit.status_code} — 8 saniye sonra bir kez daha deneniyor")
                time.sleep(8)
                continue
            break
        if yanit.status_code == 402:
            raise SystemExit(
                "X: 'credits depleted' — geliştirici hesabında API kredisi yok. "
                "Konsolun faturalama/credits bölümünden bakiye yüklenmeli; "
                "kredi gelince koşu aynı içeriği baştan dener (defter yazılmadı).")
        if yanit.status_code == 403:
            # TANI: jeton hiç mi geçmiyor, yoksa yalnız YAZMA mı yasak?
            kim = requests.get("https://api.x.com/2/users/me", timeout=30,
                               headers={"Authorization": f"Bearer {erisim}"})
            if kim.status_code == 200:
                kullanici = (kim.json().get("data") or {}).get("username", "?")
                raise SystemExit(
                    f"X 403: jeton GEÇERLİ (@{kullanici} olarak okuyabiliyor) ama "
                    "tweet YAZAMIYOR — refresh token 'tweet.write' kapsamı olmadan "
                    "üretilmiş. Konsolda token üretirken kapsamların tweet.write "
                    "(+ tweet.read, users.read, offline.access) içerdiğinden emin "
                    "olup YENİDEN üret; TW_REFRESH_TOKEN'ı güncelle ve depodan "
                    "tweet/oauth2.enc'i sil (eski zincir geçersizleşir).")
            raise SystemExit(
                f"X 403 (yazma) + /users/me {kim.status_code}: {kim.text[:200]} — "
                "jeton bu uçlara hiç yetkili değil; uygulamanın projeye bağlı ve "
                "izinlerinin Read and Write olduğunu konsoldan doğrula.")
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


def kapidan_gecir(is_listesi: list[tuple[str, list[str], list]]) -> tuple[list, list]:
    """Kalite kapısı ÖĞE BAŞINA: kirli öğe düşer ve loga yazılır, temiz öğeler
    gönderilir. Eskiden tek öğedeki engel bütün gönderimi durduruyordu — bir
    analiz gönderisindeki kusur, o sabahın bültenini de X'ten alıkoyuyordu."""
    gecen, dusen = [], []
    for anahtar, zincir, dusen_cumleler in is_listesi:
        tur = anahtar.split(":")[0]
        engel, uyari = denetim_m.denetle("\n".join(zincir), tur)
        if dusen_cumleler:
            uyari = list(uyari) + [f"{len(dusen_cumleler)} cümle site atfı yüzünden düştü: "
                                   + " | ".join(f"[{b}] {c[:70]}…" for b, c in dusen_cumleler[:3])]
        print(denetim_m.rapor(engel, uyari, anahtar))
        if engel:
            print(f"::error::{anahtar}: tweet denetimi ENGEL üretti — bu öğe gönderilmedi.")
            dusen.append((anahtar, engel))
        else:
            gecen.append((anahtar, zincir))
    return gecen, dusen


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--tur", choices=("bulten", "teknik", "analiz", "hepsi"), default="hepsi")
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
    for k, v in defter.items():
        if (v or {}).get("durum") == "gönderiliyor":
            print(f"::warning::{k}: önceki koşu gönderim ortasında kesilmiş görünüyor — "
                  "X'te var mı diye bak, defteri elle tamamla ya da kaydı sil. "
                  "Bu koşuda o içerik yeniden GÖNDERİLMİYOR.")
    is_listesi: list[tuple[str, list[str], list]] = []

    if a.tur in ("bulten", "hepsi"):
        b = uret.yazilmis_bulten(tarih)
        if b and f"bulten:{tarih}" not in defter:
            z = uret.bulten_zinciri(b)
            is_listesi.append((f"bulten:{tarih}", z, list(uret.DUSEN)))
    if a.tur in ("teknik", "hepsi"):
        t = uret.yazilmis_teknik(tarih)
        if t and f"teknik:{tarih}" not in defter:
            z = uret.teknik_zinciri(t)
            is_listesi.append((f"teknik:{tarih}", z, list(uret.DUSEN)))
    # ANALİZ KANALI. Yayın günü pubDate'i bugün olan her analiz yazısı, kendi
    # yönetici özetinden kurulan gönderiyle X'e çıkar. Pencere iki gün: gece
    # yarısından sonra push edilen ya da tetikleyicisi düşen yazı ertesi sabah
    # uyarıyla çıkar; daha eskisi ancak --tarih ile ve bilerek gönderilir.
    # Defter anahtarı analiz:<slug> — özel gönderimle atılmış yazılar deftere
    # işlenir ki araç kanalı aynı yazıyı ikinci kez atmasın.
    if a.tur in ("analiz", "hepsi"):
        gun = dt.date.fromisoformat(tarih)
        for gecikme in (0, 1):
            for an in analiz_m.bugunun_analizleri(gun - dt.timedelta(days=gecikme)):
                anahtar = f"analiz:{an['slug']}"
                if anahtar in defter:
                    continue
                if gecikme:
                    print(f"::warning::{anahtar}: yayın günü {gun - dt.timedelta(days=1)}, "
                          "bir gün gecikmeyle gönderiliyor.")
                z = analiz_m.analiz_zinciri(an)
                for u in analiz_m.UYARILAR:
                    print(f"::warning::{u}")
                analiz_m.UYARILAR.clear()
                is_listesi.append((anahtar, z, list(uret.DUSEN)))

    if not is_listesi:
        print(f"{tarih}: gönderilecek yeni içerik yok "
              "(yazılmış değil ya da defterde kayıtlı).")
        return 0

    # KALİTE KAPISI — tweet/denetim.py, öğe başına. Bültenin sayfa denetimi
    # metni sınıyor ama gönderi o metnin KIRPILMIŞ hâli; kırpmanın kusurunu
    # ancak gönderi metnine bakan bir denetim görür.
    gecen, dusen = kapidan_gecir(is_listesi)

    erisim: str | None = None
    for anahtar, zincir in gecen:
        _bas(zincir, anahtar + (" · KURU KOŞU" if kuru else ""))
        if kuru:
            continue
        if erisim is None:
            erisim = _erisim_al(JETON_DOSYA)
        # İKİ AŞAMALI KAYIT: gönderimden ÖNCE "gönderiliyor" işareti yazılır;
        # süreç POST ile kayıt arasında ölürse bir sonraki koşu bunu görür ve
        # aynı içeriği körlemesine yeniden atmaz. HTTP hatasında işaret silinir
        # (gönderilmediği kesin), kimlik gelince kayıt tamamlanır.
        simdi = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        defter[anahtar] = {"durum": "gönderiliyor", "zaman": simdi,
                           "ozet": hashlib.sha256("\n".join(zincir).encode("utf-8")).hexdigest()[:12]}
        _defter_yaz(defter_yolu, defter)
        try:
            idler = _gonder_zincir(zincir, erisim)
        except SystemExit:
            defter.pop(anahtar, None)
            _defter_yaz(defter_yolu, defter)
            raise
        zaman = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        defter[anahtar] = {"idler": idler, "zaman": zaman}
        _defter_yaz(defter_yolu, defter)
        if defter_yolu.resolve() == DEFTER.resolve():
            _arsivle(anahtar, zincir, idler, zaman)
        print(f"✓ {anahtar} gönderildi — {len(idler)} tweet, kök: {idler[0]}")
    if dusen:
        print(f"\n{len(dusen)} öğe kapıdan geçemedi: " + ", ".join(k for k, _ in dusen))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
