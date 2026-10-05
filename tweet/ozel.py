#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tek seferlik özel tweet — metin dosyasından; YALNIZ METİN.

    python3 tweet/ozel.py --metin tweet/ozel/x.txt
    ... --gonder            # verilmezse KURU: yalnız basar

Düzenli bültenlerin dışında kalan gönderiler için (tema tweetleri, veri
duyuruları). Kimlik altyapısı gonder.py ile ortak: OAuth 2.0, dönen refresh
token şifreli kasaya yazılır (iş akışı commit'ler). Kurallar aynı: LİNK
YAZILMAZ (metinde http görülürse koşu düşer). Gönderim DEFTERLİDİR: anahtar
araç kanalıyla (gonder.py) AYNI biçimde türetilir — bülten → bulten:<tarih>,
analiz slug'ına eşleşen kök → analiz:<slug>, aksi ozel:<kök>; kökteki günde
yayımlanan analiz varsa ozel: yedeğine düşülmez, --anahtar istenir (yoksa araç
kanalı aynı yazıyı bir daha atar). Anahtar defterde kimlikliyse ikinci
gönderim durur (--zorla yalnız --sil ile, biçim hatası akışı); gönderimden
sonra defter ve metin arşivi gonder.py ile aynı yoldan yazılır — araç kanalı
aynı yazıyı ikinci kez atmaz. Siteye HİÇBİR ŞEY yazılmaz (07.09.2026 kararı:
site X gönderisini okura göstermiyor).

GÖRSEL YOK (kullanıcı kararı 05.10.2026). `--resim` verilirse koşu durur;
medya yükleme kodu kaldırıldı ve gönderim gonder._gonder_zincir'den geçer —
oradaki gövde kilidi `media` alanını hiçbir koşulda kurmaz. Kural eskiden
yalnız X'in jeton kapsamına dayanıyordu (30.08'de iki medya ucu 403 verdi ve
tweet görselsiz gitti): kapsam açıldığı gün görsel sessizce giderdi.

İçerik hatası için gönderi silinmez: düzeltme kaydına `gonderi` yazılır ve
gonder.py orijinalin altına "Düzeltme" yanıtı atar (tweet/duzeltme.py).
`--sil` yalnız BİÇİM hatası içindir.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
KOK = Path(__file__).resolve().parents[1]
import gonder  # noqa: E402 — _erisim_al, JETON_DOSYA, UC, _gonder_zincir, defter/arşiv ortak

GORSEL_YOK = ("görsel gönderilmez (kullanıcı kararı 05.10.2026: tweetlerde resim yok) — "
              "--resim kaldırıldı; metni görselsiz gönder")


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
    # Girdi tanımlı kalır ki verilirse argparse'ın belirsiz "unrecognized
    # arguments" hatası yerine kararın kendisi okunsun.
    p.add_argument("--resim", action="append", default=[], help=argparse.SUPPRESS)
    p.add_argument("--gonder", action="store_true",
                   help="gerçekten gönder (verilmezse kuru)")
    p.add_argument("--sil", help="önce bu id'li tweeti sil (BİÇİM hatası akışı: eski "
                                 "gönderi kaldırılıp yenisi atılır; içerik hatası "
                                 "için düzeltme yanıtı kullanılır)")
    p.add_argument("--anahtar", help="defter anahtarı: analiz:<slug> ya da ozel:<ad>; "
                                     "verilmezse türetilir (bülten → bulten:<tarih>, analiz "
                                     "slug'ına eşleşen kök → analiz:<slug>, aksi ozel:<kök>); "
                                     "kökteki günde analiz yayımlandıysa --gonder için ZORUNLU")
    p.add_argument("--zorla", action="store_true",
                   help="anahtar defterde olsa da gönder (yalnız --sil ile: düzeltme)")
    a = p.parse_args()
    if a.resim:
        raise SystemExit(GORSEL_YOK)
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

    anahtar = a.anahtar
    if not anahtar:
        anahtar = anahtar_turet(Path(a.metin), ilk, tur, a.gonder)
        print(f"· anahtar: {anahtar}")
    if not re.match(r"^(analiz|ozel|bulten):", anahtar):
        raise SystemExit(f"anahtar 'bulten:', 'analiz:' ya da 'ozel:' ile başlar: {anahtar!r}")
    defter = gonder._defter_oku(gonder.DEFTER)
    if anahtar and (defter.get(anahtar) or {}).get("idler") and not a.zorla:
        raise SystemExit(f"{anahtar} defterde kimlikli — zaten gönderildi "
                         f"({defter[anahtar]['idler'][0]}). Düzeltme: --sil <id> --zorla.")

    print(f"── özel tweet ({len(metin)} karakter"
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
    # Gönderim araç kanalının yolundan: link kilidi, gövde kilidi (medya yok),
    # 429/5xx'te bir yeniden deneme ve 402/403 teşhisi tek yerde.
    kimlik = str(gonder._gonder_zincir([metin], erisim)[0])
    print(f"✓ gönderildi — id: {kimlik}")
    # Defter + arşiv: gonder.py ile aynı yol, aynı biçim (siteye yazılmaz).
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
