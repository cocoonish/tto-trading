#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tek seferlik özel tweet — metin dosyasından, istenirse görsellerle.

    python3 tweet/ozel.py --metin tweet/ozel/x.txt --resim a.png --resim b.png
    ... --gonder            # verilmezse KURU: yalnız basar

Düzenli bültenlerin dışında kalan gönderiler için (tema tweetleri, veri
duyuruları). Kimlik altyapısı gonder.py ile ortak: OAuth 2.0, dönen refresh
token şifreli kasaya yazılır (iş akışı commit'ler). Kurallar aynı: LİNK
YAZILMAZ (metinde http görülürse koşu düşer). Gönderim DEFTERLİDİR: anahtar
araç kanalıyla (gonder.py) AYNI biçimde türetilir — bülten → bulten:<tarih>,
analiz slug'ına eşleşen kök → analiz:<slug>, aksi ozel:<kök>; kökteki günde
yayımlanan analiz varsa ozel: yedeğine düşülmez, --anahtar istenir (yoksa araç
kanalı aynı yazıyı bir daha atar). Anahtar defterde kimlikliyse ikinci
gönderim durur (--zorla yalnız --sil ile, düzeltme akışı); gönderimden sonra
defter, metin arşivi ve sitenin aynası gonder.py ile aynı yoldan yazılır —
böylece siteye X bağı kurulur ve araç kanalı aynı yazıyı ikinci kez atmaz.

Görseller X API v2 medya ucuna yüklenir (POST /2/media/upload). Bu uç
'media.write' kapsamı ister; refresh token o kapsamsız üretildiyse 403 döner
ve hata ne yapılacağını söyler.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
KOK = Path(__file__).resolve().parents[1]
import gonder  # noqa: E402 — _erisim_al, JETON_DOSYA, UC, defter/arşiv/ayna ortak

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


AYLAR = ("ocak", "şubat", "mart", "nisan", "mayıs", "haziran", "temmuz", "ağustos",
         "eylül", "ekim", "kasım", "aralık")


def anahtar_turet(metin_yolu: Path, ilk: str, tur: str, gonder: bool) -> str:
    """Defter anahtarı — araç kanalıyla (gonder.py) AYNI biçimde, yoksa aynı içerik
    iki kanaldan iki kez gider: bülten → bulten:<YYYY-MM-DD> (ilk satırdaki
    tarihten); dosya kökü bir analiz slug'ıysa → analiz:<slug>; 'Analiz — '
    başlıklı ama eşleşmeyen kök → durur; aksi → ozel:<kök>.

    ozel: yedeğine düşmeden önce kökteki tarihe bakılır: o gün ya da bir gün
    önce yayımlanan analiz varsa (araç kanalının iki günlük penceresi) ve
    gönderim isteniyorsa DURUR. Serbest başlıklı bir analiz özeti ozel:<kök> ile
    gitse araç kanalı analiz:<slug> defterde yok diye aynı yazıyı ertesi sabah
    bir daha atardı — defterdeki elle yazılmış analiz: kayıtları bunun bir kez
    olduğunu söylüyor. Kuru koşuda öneri basılır, operatör anahtarı görür."""
    kok = metin_yolu.stem
    if tur == "bulten":
        m_t = re.search(r"(\d{1,2})\s+([A-Za-zÇĞİÖŞÜçğıöşü]+)\s+(\d{4})", ilk)
        if not m_t or m_t.group(2).lower() not in AYLAR:
            raise SystemExit(f"bülten gönderisinin ilk satırından tarih çözülemedi: {ilk!r} — --anahtar bulten:YYYY-MM-DD ver")
        return f"bulten:{int(m_t.group(3)):04d}-{AYLAR.index(m_t.group(2).lower()) + 1:02d}-{int(m_t.group(1)):02d}"
    if (KOK / "site" / "src" / "content" / "analiz" / f"{kok}.mdx").exists():
        return f"analiz:{kok}"
    if tur == "analiz":
        raise SystemExit(f"analiz gönderisi ama dosya kökü ({kok}) hiçbir analiz slug'ına eşleşmiyor — "
                         "--anahtar analiz:<slug> ver; yoksa araç kanalı aynı yazıyı bir daha atar")
    m_g = re.search(r"\d{4}-\d{2}-\d{2}", kok)
    if m_g:
        import datetime as _dt
        import analiz as analiz_m
        try:
            gun = _dt.date.fromisoformat(m_g.group(0))
        except ValueError:
            gun = None
        if gun is not None:
            yayimlanan = sorted({an["slug"] for g in (0, 1)
                                 for an in analiz_m.bugunun_analizleri(gun - _dt.timedelta(days=g))})
            if yayimlanan:
                ileti = (f"{kok}: o günlerde yayımlanan analiz var ({', '.join(yayimlanan)}) ama kök "
                         "hiçbirine eşleşmiyor — bu bir analiz özetiyse --anahtar analiz:<slug>, tema "
                         "gönderisiyse --anahtar ozel:<ad> ver; boş bırakılırsa araç kanalı aynı yazıyı bir daha atar")
                if gonder:
                    raise SystemExit(ileti)
                print(f"::warning::{ileti}")
    return f"ozel:{kok}"                             # iş akışı sözleşmesi: boş = ozel:<dosya kökü>


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--metin", required=True, help="tweet metni dosyası")
    p.add_argument("--resim", action="append", default=[],
                   help="eklenecek PNG (tekrarlanabilir, en çok 4)")
    p.add_argument("--gonder", action="store_true",
                   help="gerçekten gönder (verilmezse kuru)")
    p.add_argument("--sil", help="önce bu id'li tweeti sil (düzeltme akışı: "
                                 "eski gönderi kaldırılıp yenisi atılır)")
    p.add_argument("--anahtar", help="defter anahtarı: analiz:<slug> ya da ozel:<ad>; "
                                     "verilmezse türetilir (bülten → bulten:<tarih>, analiz "
                                     "slug'ına eşleşen kök → analiz:<slug>, aksi ozel:<kök>); "
                                     "kökteki günde analiz yayımlandıysa --gonder için ZORUNLU")
    p.add_argument("--zorla", action="store_true",
                   help="anahtar defterde olsa da gönder (yalnız --sil ile: düzeltme)")
    a = p.parse_args()
    if a.zorla and not a.sil:
        raise SystemExit("--zorla yalnız --sil ile: eski gönderi silinmeden aynı anahtara "
                         "ikinci gönderi mükerrer olur")

    metin = Path(a.metin).read_text(encoding="utf-8").strip()
    import denetim as tw_denetim
    baglanti = tw_denetim.link_var(metin)
    if baglanti:
        raise SystemExit(f"metinde link var ({baglanti!r}) — kural: tweetlerde HİÇ link kullanılmaz")
    # KALİTE KAPISI — tweet/denetim.py. Okur dili (ortak tanım), tavsiye dili
    # (bülten denetimiyle aynı kalıp), link, emoji, HTML kalıntısı, sayı
    # ortasında kesik cümle, boş bölüm etiketi, uzunluk ve sorumluluk notu tek
    # kapıdan geçer. Düzenli gönderiler (gonder.py) de aynı kapıyı kullanır;
    # kural bir yerde durur, iki yerde uygulanır.
    # Tür ilk satırdan: özel kanaldan bülten de, analiz de, tema gönderisi de
    # çıkar; türe bağlı ölçütler (başlık satırı, Gündem) yalnız uyanı sınar.
    ilk = metin.split("\n", 1)[0]
    tur = ("bulten" if ilk.startswith(("Sabah Notu", "Haftaya Bakış"))
           else "analiz" if ilk.startswith("Analiz — ") else "ozel")
    engel, uyari = tw_denetim.denetle(metin, tur)
    print(tw_denetim.rapor(engel, uyari, Path(a.metin).name))
    if engel:
        raise SystemExit("tweet denetimi ENGEL üretti — gönderim durdu.")
    if len(a.resim) > 4:
        raise SystemExit("en çok 4 görsel")
    resimler = [Path(r) for r in a.resim]
    for r in resimler:
        if not r.exists():
            raise SystemExit(f"görsel yok: {r}")

    anahtar = a.anahtar
    if not anahtar:
        anahtar = anahtar_turet(Path(a.metin), ilk, tur, a.gonder)
        print(f"· anahtar: {anahtar}")
    if not re.match(r"^(analiz|ozel|bulten|teknik):", anahtar):
        raise SystemExit(f"anahtar 'bulten:', 'teknik:', 'analiz:' ya da 'ozel:' ile başlar: {anahtar!r}")
    defter = gonder._defter_oku(gonder.DEFTER)
    if anahtar and (defter.get(anahtar) or {}).get("idler") and not a.zorla:
        raise SystemExit(f"{anahtar} defterde kimlikli — zaten gönderildi "
                         f"({defter[anahtar]['idler'][0]}). Düzeltme: --sil <id> --zorla.")

    print(f"── özel tweet ({len(metin)} karakter, {len(resimler)} görsel"
          + (f", {anahtar}" if anahtar else "") + (" · KURU" if not a.gonder else "") + ")")
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
    kimlik = str(yanit.json()["data"]["id"])
    print(f"✓ gönderildi — id: {kimlik}")
    # Defter + arşiv + ayna: gonder.py ile aynı yol, aynı biçim.
    import datetime as _dt
    zaman = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    defter[anahtar] = {"idler": [kimlik], "zaman": zaman, "tur": "ozel",
                       "ozet": gonder.hashlib.sha256(metin.encode("utf-8")).hexdigest()[:12]}
    gonder._defter_yaz(gonder.DEFTER, defter)
    yol = gonder._arsivle(anahtar, [metin], [kimlik], zaman)
    print(f"· deftere yazıldı ({anahtar}); arşiv: {yol.relative_to(KOK)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
