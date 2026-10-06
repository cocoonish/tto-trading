#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tweet zincirini X'e GÖNDERİR — defterli, kuru-koşulu, bayat-korumalı.

    python3 tweet/gonder.py                # bugünün yazılmış içeriğini gönder
    python3 tweet/gonder.py --kuru         # göndermeden zinciri bas
    python3 tweet/gonder.py --tarih 2026-08-30 --tur bulten
    python3 tweet/gonder.py --tur duzeltme --kuru   # bekleyen düzeltme yanıtları
    python3 tweet/gonder.py --jeton        # yalnız jeton sağlığı (gönderim yok)

Sigortalar (araçta, rutin metninde değil):

· DEFTER (tweet/defter.json): her (tür, tarih) EN FAZLA BİR KEZ gönderilir.
· DALIN UCU: koşucuda jeton harcanmadan önce jeton ve defterin dalın ucundaki
  sürüm olduğu sorulur; değilse koşu durur (dal_ucu_denetimi).
  Defter gönderimden sonra yazılır ve iş akışı onu commit'ler; ikinci koşu
  aynı içeriği görüp geçer. Kuru koşu deftere DOKUNMAZ.
· BAYAT KORUMASI: --tarih verilmedikçe yalnız BUGÜNÜN (UTC) içeriği
  gönderilir. Eski bir bülteni gece yarısından sonra tweetlemek okura "yeni"
  diye eski haber satmaktır; kaçan gün sessizce atlanır, defterlenmez.
· DÜZELTME YANITI (tweet/duzeltme.py): yazarın `gonderi` alanıyla işaretlediği
  düzeltme kaydı, hedef gönderinin altına yanıt olarak gider; anahtar içeriğe
  bağlı (duzeltme:<hedef>:<sha1>), yani aynı düzeltme iki kez gitmez; kayıt
  metnin özünü de taşır (`metin_oz`), aynı hedefe aynı metin ikinci kez
  kurulmaz (X kopyayı 403 ile reddeder). Hedef
  X'te silinmişse (403 gövdesi "deleted/not visible") bu bir jeton arızası
  sayılmaz: kayıt "hedef_yok" diye terminal yazılır, koşu sürer.
· GÖRSEL YOK (kullanıcı kararı 05.10.2026): gövdede yalnız metin ve yanıt
  alanı gider; `media` alanı kurulamaz (_govde ikinci kilit).
· ETKİLEŞİM ÖLÇÜMÜ (tweet/metrik.py): gönderim bittikten sonra, AYNI erişim
  jetonuyla, haftada bir; hiçbir koşulda gönderimi etkilemez.
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
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import uret  # noqa: E402
import analiz as analiz_m  # noqa: E402
import denetim as denetim_m  # noqa: E402
import duzeltme as duzeltme_m  # noqa: E402
import metrik as metrik_m  # noqa: E402

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


# DALIN UCU (06.10.2026). Yazı katmanı ile işlem fikri ayrı yamalarla, otuz
# saniye arayla push edilir ve iki tweet koşusu tetiklenir. concurrency ikinciyi
# SIRAYA sokar ama checkout öntanımlı olarak olayın KENDİ commit'ini alır:
# birinci koşunun döndürdüğü jeton ve yazdığı defter o commit'te yoktur. İkinci
# koşu harcanmış jetonla açıldı (X 400 "Value passed for the token was invalid")
# ve eski defterle aynı bülteni ikinci kez atmaya hazırlanıyordu; mükerrer
# gönderiyi yalnız ölü jeton durdurdu. Birinci kilit iş akışlarında (checkout
# `ref: main`); bu ikincisi aynı soruyu jeton harcanmadan araçta sorar.
IZLENEN_YOLLAR = ("tweet/oauth2.enc", "tweet/defter.json")


def dal_ucu_denetimi(kok: Path, dal: str = "main", uzak: str = "origin") -> None:
    """HEAD'deki jeton ve defter, dalın uzaktaki ucuyla aynı mı? Değilse durur:
    jeton harcanmaz, defter yazılmaz. Uç okunamazsa uyarı basıp geçer — bu
    ikinci kilittir ve bir ağ kusuru sabahın gönderisini durdurmamalı."""
    def git(*arg: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", str(kok), *arg],
                              capture_output=True, text=True, timeout=60)
    try:
        f = git("fetch", "--quiet", "--no-tags", uzak, dal)
    except (OSError, subprocess.TimeoutExpired) as e:
        print(f"::warning::dalın ucu okunamadı ({type(e).__name__}) — jeton ve "
              "defterin güncelliği sınanamadı, gönderim sürüyor")
        return
    if f.returncode != 0:
        print(f"::warning::dalın ucu okunamadı ({f.stderr.strip()[:160]}) — jeton ve "
              "defterin güncelliği sınanamadı, gönderim sürüyor")
        return
    farkli = [yol for yol in IZLENEN_YOLLAR
              if git("rev-parse", "--verify", "--quiet", f"HEAD:{yol}").stdout.strip()
              != git("rev-parse", "--verify", "--quiet", f"FETCH_HEAD:{yol}").stdout.strip()]
    if farkli:
        raise SystemExit(
            f"checkout bayat: {', '.join(farkli)} {dal} dalının ucundakiyle aynı değil — "
            "önceki bir koşu jetonu döndürmüş ya da deftere yazmış. Bu koşu harcanmış "
            "jetonla açılır ve eski defterle gönderilmiş içeriği yeniden atardı; jeton "
            f"kullanılmadan durdu. İş akışının checkout'u dalın ucunu almalı (ref: {dal}).")


def _erisim_al(dosya: Path) -> str:
    """Refresh token'ı kullanır: erişim jetonu döner, DÖNEN yeni refresh
    token gönderimden önce şifreli dosyaya yazılır (tek kullanımlık jeton
    koşu ortasında ölürsek de kaybolmasın). Koşucuda jeton harcanmadan önce
    checkout'un dalın ucunda olduğu sorulur (dal_ucu_denetimi)."""
    import requests
    if os.environ.get("GITHUB_ACTIONS") == "true" and dosya.resolve() == JETON_DOSYA.resolve():
        dal_ucu_denetimi(KOK)
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


# Gönderi gövdesinde izin verilen alanlar. GÖRSEL YOK (kullanıcı kararı
# 05.10.2026): `media` alanı burada hiç kurulamaz. Görsel yasağı bir zamanlar
# yalnız X'in jeton kapsamına dayanıyordu (30.08'de iki medya ucu 403 verdi ve
# özel gönderi görselsiz gitti) — kapsam açıldığı gün görsel sessizce gidecekti.
GOVDE_ALANLARI = frozenset({"text", "reply"})


def _govde(metin: str, ust: str | None) -> dict:
    """X gönderi gövdesi: metin ve (varsa) yanıtlanan kimlik. Başka alan yok."""
    govde: dict = {"text": metin}
    if ust:
        govde["reply"] = {"in_reply_to_tweet_id": str(ust)}
    fazla = set(govde) - GOVDE_ALANLARI
    if fazla:                                     # ikinci kilit: kod değişse bile
        raise SystemExit(f"gönderi gövdesinde izinsiz alan {sorted(fazla)} — görsel/medya "
                         "gönderilmez (kullanıcı kararı); gönderim durdu, defter yazılmadı.")
    return govde


class HedefYok(SystemExit):
    """Dış hedefe (düzeltme yanıtı) yanıt verilemedi: X yanıtlanan gönderinin
    silindiğini ya da görünmediğini söyledi. Jeton sağlamdır — bu bir kapsam
    arızası DEĞİLDİR. `main` yalnız bunu yakalar: kayıt terminal olarak yazılır
    ("hedef_yok"), arkadaki öğeler ve metrik okuması sürer. Yakalanmadığı her
    yerde SystemExit gibi davranır (ölümcül)."""


# X'in silinmiş/görünmez hedef gövdesi: "You attempted to reply to a Tweet that
# is deleted or not visible to you." Yalnız `detail`/`title` alanında aranır.
HEDEF_YOK_RE = re.compile(r"deleted|not visible", re.I)


def _hedef_yok_mu(yanit) -> bool:
    try:
        d = yanit.json() or {}
    except Exception:                                          # noqa: BLE001
        return False
    if not isinstance(d, dict):
        return False
    alanlar = [d.get("detail"), d.get("title")]
    for h in d.get("errors") or []:
        if isinstance(h, dict):
            alanlar += [h.get("detail"), h.get("title"), h.get("message")]
    return any(isinstance(x, str) and HEDEF_YOK_RE.search(x) for x in alanlar)


def _gonder_zincir(zincir: list[str], erisim: str, ust: str | None = None) -> list[str]:
    """Zinciri sırayla gönderir, her tweet öncekine yanıt olur. ID listesi döner.
    `ust` verilirse zincirin İLK parçası o kimliğe yanıt olur (düzeltme yanıtı).
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
        govde = _govde(metin, idler[-1] if idler else ust)
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
        if yanit.status_code == 403 and i == 0 and ust and _hedef_yok_mu(yanit):
            # Gövde ÖNCE okunur: silinmiş hedefe yanıt bir jeton arızası değildir.
            # Yalnız DIŞ hedefte (zincir içi parça 1 saniye önce atılmış olabilir,
            # geçici görünmezliği kalıcı karara çevrilmez); öbür 403'ler aşağıda.
            raise HedefYok(
                f"yanıtlanan gönderi ({ust}) X'te silinmiş ya da görünmüyor — "
                "düzeltme yanıtı atılamadı (jeton sağlam, işlem gerekmiyor).")
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


def kapidan_gecir(is_listesi: list[tuple[str, list[str], list]],
                  tam: bool = False) -> tuple[list, list]:
    """Kalite kapısı ÖĞE BAŞINA: kirli öğe düşer ve loga yazılır, temiz öğeler
    gönderilir. Eskiden tek öğedeki engel bütün gönderimi durduruyordu — bir
    analiz gönderisindeki kusur, o sabahın bültenini de X'ten alıkoyuyordu.
    `tam` (kuru koşu): düşen birimlerin TAMAMI basılır; normal koşuda uyarı
    satırı ilk üçünü özetler."""
    gecen, dusen = [], []
    for anahtar, zincir, dusen_cumleler in is_listesi:
        tur = anahtar.split(":")[0]
        engel, uyari = denetim_m.denetle("\n".join(zincir), tur)
        if dusen_cumleler:
            # DUSEN yalnız site atfını değil bütçe, şerit ve tam birim
            # düşüşlerini de taşır; her kaydın etiketi sebebini söyler.
            uyari = list(uyari) + [f"{len(dusen_cumleler)} birim gönderiden düştü (etiket sebebi söyler): "
                                   + " | ".join(f"[{b}] {c[:70]}" for b, c in dusen_cumleler[:3])]
        print(denetim_m.rapor(engel, uyari, anahtar))
        if tam and dusen_cumleler:
            print(f"  · düşen birimler ({len(dusen_cumleler)}):")
            for b, c in dusen_cumleler:
                print(f"    [{b}] {c}")
        if engel:
            print(f"::error::{anahtar}: tweet denetimi ENGEL üretti — bu öğe gönderilmedi.")
            dusen.append((anahtar, engel))
        else:
            gecen.append((anahtar, zincir))
    return gecen, dusen


def _metrik_oku(erisim: str, defter: dict, yol: Path | None = None) -> None:
    """tweet/metrik.py'yi çağırır; ne olursa olsun gönderimi ETKİLEMEZ. metrik
    kendi içinde de yutuyor — bu ikinci sarmalayıcı çağrı anındaki kusura karşı
    (imza kayması, öznitelik hatası). Modül düzeyindeki içe aktarma hatası bu
    sarmalayıcının DIŞINDADIR: duman sınaması onu gönderimden önce yakalar ve
    gönderim durur."""
    try:
        print("· " + metrik_m.haftalik(erisim, defter, **({"yol": yol} if yol else {}),
                                       bulten_dizin=uret.BULTENLER))
    except BaseException as e:                                 # noqa: BLE001
        print(f"::warning::etkileşim ölçümü düştü ({type(e).__name__}: {str(e)[:120]}) — gönderim etkilenmedi")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--tur", choices=("bulten", "analiz", "duzeltme", "hepsi"), default="hepsi")
    p.add_argument("--tarih", help="varsayılan: bugün (UTC); bayat koruması "
                                   "yalnız varsayılanda uygulanır")
    p.add_argument("--kuru", action="store_true", help="gönderme, yalnız bas")
    p.add_argument("--defter", help="defter yolu (sınama için)")
    p.add_argument("--jeton", action="store_true",
                   help="yalnız jetonu yenile: refresh token geçerli mi (gönderim ve okuma "
                        "yok; dönen jeton oauth2.enc'e yazılır, iş akışı commit'ler)")
    a = p.parse_args()

    defter_yolu = Path(a.defter) if a.defter else DEFTER
    tarih = a.tarih or dt.datetime.now(dt.timezone.utc).date().isoformat()
    anahtar_var = (all(os.environ.get(k) for k in ANAHTARLAR)
                   and (JETON_DOSYA.exists() or os.environ.get("TW_REFRESH_TOKEN")))
    # JETON SAĞLIK SINAMASI (06.10.2026). Gönderilecek içerik yokken koşu jetona
    # hiç dokunmaz; harcanmış bir jetonla açılan koşudan sonra kalan jetonun
    # canlı olup olmadığı ancak bir sonraki GÖNDERİMDE görünürdü. Bu kip onu
    # gönderim olmadan sorar; dönen jeton her yenilemede olduğu gibi commit'lenir.
    if a.jeton:
        if a.kuru or not anahtar_var:
            raise SystemExit("--jeton kuru koşulmaz ve TW_* anahtarlarını ister: "
                             "jetonu sınamanın tek yolu onu yenilemektir.")
        _erisim_al(JETON_DOSYA)
        print("✓ jeton geçerli — yenilendi; dönen refresh token oauth2.enc'e yazıldı "
              "(commit edilecek). Gönderim ve okuma yapılmadı.")
        return 0
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
    # Teknik kanalı 01.10.2026'da kapandı (yayın 27.09.2026 sayısıyla sona erdi);
    # defterdeki teknik:<gün> kayıtları tarihçe olarak duruyor.
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

    # DÜZELTME KANALI (05.10.2026). Yazarın `gonderi` ile işaretlediği düzeltme
    # kayıtları, hedef gönderinin İLK kimliğine yanıt olarak gider. Pencere son
    # duzeltme_m.PENCERE_GUN gün; geçmiş gönderilere kendiliğinden yanıt yok.
    ust_kimlik: dict[str, str] = {}
    # Düzeltme yanıtının metin özü defter kaydına yazılır (her durumda: gönderiliyor,
    # gönderildi, hedef_yok): adaylar aynı hedefe aynı metni ikinci kez kurmaz —
    # X kopya içeriği 403 ile reddeder ve o 403 koşuyu düşürürdü (duzeltme.metin_ozu).
    metin_oz: dict[str, str] = {}
    if a.tur in ("duzeltme", "hepsi"):
        # Bu kanalın kendi kusuru (okunamayan bir ön bilgi, bozuk bir kayıt)
        # sabahın bültenini X'ten alıkoyamaz: kanal düşerse uyarı basılır,
        # öbür öğeler gider.
        try:
            adaylar, d_uyari = duzeltme_m.adaylar(dt.date.fromisoformat(tarih), defter)
        except Exception as e:                                 # noqa: BLE001
            adaylar, d_uyari = [], [f"düzeltme kanalı okunamadı ({type(e).__name__}: {str(e)[:120]})"]
        for u in d_uyari:
            print(f"::warning::{u}")
        for ad in adaylar:
            # Metin de öğe başına kurulur: bir adayın kusuru (bozuk arşiv, beklenmedik
            # alan) bültenin ve öbür adayların önünü kesmez. Atlanan aday deftere
            # yazılmaz, sonraki koşu yeniden dener.
            try:
                t = duzeltme_m.metin(ad)
            except Exception as e:                             # noqa: BLE001
                print(f"::warning::{ad['anahtar']}: düzeltme metni kurulamadı "
                      f"({type(e).__name__}: {str(e)[:120]}) — bu yanıt gönderilmedi, öbür öğeler gider")
                continue
            ust_kimlik[ad["anahtar"]] = ad["ust"]
            metin_oz[ad["anahtar"]] = ad.get("metin_oz") or duzeltme_m.metin_ozu(ad["metin_ham"])
            is_listesi.append((ad["anahtar"], [t], []))

    if not is_listesi:
        print(f"{tarih}: gönderilecek yeni içerik yok "
              "(yazılmış değil ya da defterde kayıtlı).")
        return 0

    # KALİTE KAPISI — tweet/denetim.py, öğe başına. Bültenin sayfa denetimi
    # metni sınıyor ama gönderi o metnin KIRPILMIŞ hâli; kırpmanın kusurunu
    # ancak gönderi metnine bakan bir denetim görür.
    gecen, dusen = kapidan_gecir(is_listesi, tam=kuru)

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
        oz_alani = {"metin_oz": metin_oz[anahtar]} if anahtar in metin_oz else {}
        defter[anahtar] = {"durum": "gönderiliyor", "zaman": simdi,
                           "ozet": hashlib.sha256("\n".join(zincir).encode("utf-8")).hexdigest()[:12],
                           **oz_alani}
        _defter_yaz(defter_yolu, defter)
        try:
            idler = _gonder_zincir(zincir, erisim, ust=ust_kimlik.get(anahtar))
        except HedefYok as e:
            # Silinmiş hedef: kayıt TERMİNAL yazılır (idler yok) — adaylar aynı
            # anahtarı her koşuda yeniden kurmaz; yazar `gonderi`yi başka bir
            # hedefe çevirirse anahtar değişir. Arkadaki öğeler ve metrik sürer.
            defter[anahtar] = {"durum": "hedef_yok", "hedef": ust_kimlik.get(anahtar),
                               "zaman": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                               **oz_alani}
            _defter_yaz(defter_yolu, defter)
            print(f"::warning::{anahtar}: {e}")
            continue
        except SystemExit:
            defter.pop(anahtar, None)
            _defter_yaz(defter_yolu, defter)
            raise
        zaman = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        defter[anahtar] = {"idler": idler, "zaman": zaman, **oz_alani}
        if anahtar in ust_kimlik:
            defter[anahtar]["yanit"] = ust_kimlik[anahtar]
        _defter_yaz(defter_yolu, defter)
        if defter_yolu.resolve() == DEFTER.resolve():
            _arsivle(anahtar, zincir, idler, zaman)
        print(f"✓ {anahtar} gönderildi — {len(idler)} tweet, kök: {idler[0]}")
    # ETKİLEŞİM ÖLÇÜMÜ — yalnız bu koşu zaten bir erişim jetonu aldıysa (ek jeton
    # dönüşü yok) ve gerçek defterle; gönderimden SONRA, defter commit'inden ÖNCE.
    if erisim is not None and defter_yolu.resolve() == DEFTER.resolve():
        _metrik_oku(erisim, defter)
    if dusen:
        print(f"\n{len(dusen)} öğe kapıdan geçemedi: " + ", ".join(k for k, _ in dusen))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
