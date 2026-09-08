"""Bir hattın verisi kaynağın verebileceğinden geride mi — ölçünün TEK tanımı.

NEDEN AYRI BİR MODÜL. 03.09.2026'da kredi hattı perşembe yayımından sonra koştu,
21.08 haftasıyla döndü ve damgayı aldı; site on yedi gün eski veriyle kalacaktı.
Ölçü ZATEN VARDI — hattın kendi `uyarilar.json`u "13 gün geride (tolerans 12)"
yazmıştı — ve onu okuyan hiçbir kapı yoktu. Aynı gün konan yeniden deneme defteri
(`tazeleme.son_surum` · `deneme`) arızayı artık ÖLÇÜYOR, ama o sinyalin de
tüketicisi sıfırdı: tek aday `denetim.tazeleme_atlandi` ve o da
`[k for k in kararlar if k.kossun]` süzgeciyle TAM DA ARIZA HÂLİNİ atıyordu
(hakkı dolan hat `kossun=False` döner). Ölçülen ama okunmayan bir sinyal,
ölçülmemiş sinyaldir.

ÖLÇÜNÜN TANIMI DAR VE BİLEREK. "Veri yaşı toleransı aştı" TEK BAŞINA alarm
DEĞİLDİR. Ölçüldü (07.09.2026): ham veri yaşına dayanan bir kapı o gün üç hatta
ateşlerdi ve İKİSİ MEŞRUDU — ödemeler dengesinin temmuz sayısı 11.09'da
yayımlanacaktı (elde olan en yeni veri haziran), hazinenin son ihalesi 17.08'di ve
sıradaki 14.09 (arada ihale yok). Yani ham yaş ölçüsü ilk günden ≥%67 yanlış
pozitif verirdi. Alarma yalnız şu bileşim girer:

    kaynak yayımladı  +  hat koştu  +  ana saat İLERLEMEDİ  +  hak doldu

Bu bileşim "kaynak henüz yayımlamadı" hâlini yapısal olarak dışarıda bırakır,
çünkü `deneme` sayacı ancak bir yayım tetiği ateşledikten sonra artıyor.

YAYINI DURDURAN SINIF YOK — YAPISAL KİLİT. `gecikme.py`nin eşi bir kural:
`SINIFLAR` içinde yayını durduran bir sınıf HİÇ TANIMLI DEĞİL ve duman sınaması
hem sabiti hem kaynak metnini sınıyor. Sebebi 02.09'da ölçüldü: yayının önünde
duran bir denetimin yanlış alarmı siteyi on iki saat durdurmuştu. Bayat bir
hattı yayından ÇIKARAN kapı, bayatlığı yokluğa çevirir — yani ölçtüğü şeyi
büyütür.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent
# Kapsam ölçütü (bulten/duman.py) bu satırı OKUYARAK gecikme.yml'in
# sparse-checkout listesini sınıyor; yol tek parça yazılır ki türetilebilsin.
PROJELER = KOK / "site/public/projeler"

sys.path.insert(0, str(BURASI))
sys.path.insert(0, str(KOK / "ortak"))
import ayar          # noqa: E402
import bicim         # noqa: E402
import tazeleme      # noqa: E402

# Üç sınıf. Dördüncüsü — yayını durduran sınıf — BİLEREK yoktur; bkz. modül
# başlığı ve `bulten/duman.py`nin ölçütü.
SINIFLAR = ("saglikli", "bilgi", "alarm")


@dataclass
class Bulgu:
    hat: str                      # kütükteki kısa ad
    slug: str
    ad: str                       # okurun gördüğü ad
    sinif: str
    surum: str                    # son görülen veri sürümü (ana saat)
    deneme: int                   # sürümü ilerletmeyen ardışık koşu sayısı
    veri_yasi_gun: int | None     # ana saatin bugüne göre yaşı (BİLGİ, eşik değil)
    ritim_gun: int | None         # hattın beklenen azami sessizliği (BİLGİ)
    sebep: str = ""
    tetikleyen: list[str] = field(default_factory=list)


def _hat_slug() -> dict[str, str]:
    """Kısa ad → slug. Kütük tek kaynak; okunamazsa boş döner ve ölçü SUSAR
    (uydurma eşleme, eşleme yapmamaktan kötüdür)."""
    try:
        sys.path.insert(0, str(KOK))
        import guncelle                                        # noqa: E402
        return {h.ad: h.slug for h in guncelle.HATLAR}
    except Exception:                                          # noqa: BLE001
        return {}


def _veri_yasi(slug: str, bugun: dt.date) -> tuple[int | None, str]:
    """Hattın site kopyasındaki ana saatin yaşı (gün) ve ham yazımı.

    BİLGİDİR, EŞİK DEĞİL: bu sayı alarmı tetiklemez (bkz. modül başlığı),
    yalnız bulgunun yanına yazılır ki bakan biri büyüklüğü görsün."""
    y = PROJELER / slug / "ozet.json"
    try:
        d = json.loads(y.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None, ""
    ham = ""
    for a in ("_tarih", "g_tarih"):
        if isinstance(d.get(a), str):
            ham = d[a]
            break
    g = bicim.tarihe_cevir(ham)
    return ((bugun - g).days if g else None), ham


def bulgular(simdi: dt.datetime | None = None) -> list[Bulgu]:
    """Her hat için bayatlık hükmü. Ağa ÇIKMAZ: yalnız depodaki defteri okur.

    Takvim ucuna gitmemesi bilinçli — bu ölçü bir alarm kanalında koşuyor ve
    alarmın kendi hata kaynağı, izlediği arızayla aynı olamaz (CLAUDE.md)."""
    simdi = simdi or dt.datetime.now()
    bugun = simdi.date()
    ad_slug = _hat_slug()
    surumler = tazeleme.surum_oku()
    denemeler = tazeleme.deneme_oku()

    cikti: list[Bulgu] = []
    for hat in sorted(set(surumler) | set(denemeler) | set(ad_slug)):
        slug = ad_slug.get(hat, "")
        n = int(denemeler.get(hat, 0) or 0)
        yas, _ham = _veri_yasi(slug, bugun) if slug else (None, "")
        if n >= tazeleme.TEKRAR_HAKKI:
            sinif = "alarm"
            sebep = (f"kaynak yayımladı, veri gelmedi: {n} koşudur ana saat "
                     f"ilerlemiyor ve yeniden deneme hakkı doldu")
        elif n:
            sinif = "bilgi"
            sebep = (f"son {n} koşu ana saati ilerletmedi; yeniden deneme "
                     f"sürüyor ({n}/{tazeleme.TEKRAR_HAKKI})")
        else:
            sinif = "saglikli"
            sebep = "son koşu veriyi ilerletti"
        cikti.append(Bulgu(
            hat=hat, slug=slug,
            ad=ayar.HAT_ADI.get(slug, slug or hat),
            sinif=sinif,
            surum=str(surumler.get(hat, "") or "?"),
            deneme=n,
            veri_yasi_gun=yas,
            ritim_gun=ayar.RITIM.get(slug),
            sebep=sebep))
    return cikti


def alarmlar(simdi: dt.datetime | None = None) -> list[Bulgu]:
    return [b for b in bulgular(simdi) if b.sinif == "alarm"]


def rapor(simdi: dt.datetime | None = None) -> str:
    b = bulgular(simdi)
    if not b:
        # Defter henüz dolmamış olabilir (mekanizma 07.09.2026'da kondu).
        # Boşluğu "sorun yok" diye okumak, ölçmediğini ölçmüş saymaktır.
        return "  (sürüm defteri boş — henüz hiçbir koşu sürüm yazmadı)"
    satir = []
    for x in sorted(b, key=lambda z: (SINIFLAR.index(z.sinif), z.hat), reverse=True):
        im = {"alarm": "‼", "bilgi": "▸", "saglikli": "·"}[x.sinif]
        yas = f"{x.veri_yasi_gun}g" if x.veri_yasi_gun is not None else "?"
        satir.append(f"  {im} {x.ad:34s} sürüm {x.surum:12s} "
                     f"deneme {x.deneme}/{tazeleme.TEKRAR_HAKKI}  veri {yas}"
                     + (f" — {x.sebep}" if x.sinif != "saglikli" else ""))
    return "\n".join(satir)


if __name__ == "__main__":
    a = alarmlar()
    print(rapor())
    if a:
        print(f"\n{len(a)} hat: kaynak yayımladı, veri gelmedi.")
        # Çıkış kodu 1: alarmı taşıyan iş akışı DÜŞER ve düşen iş akışı
        # e-posta gönderir. Yayın zinciri bu koddan etkilenmez — bu modül
        # yayın kapısında DEĞİL, alarm kanalında koşuyor.
        raise SystemExit(1)
    print("\nkaynak yayımlayıp veri getirmeyen hat yok.")
