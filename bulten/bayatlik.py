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

    kaynak yayımladı  +  hat koştu  +  izlenen saat İLERLEMEDİ  +  hak doldu

Bu bileşim "kaynak henüz yayımlamadı" hâlini yapısal olarak dışarıda bırakır,
çünkü `deneme` sayacı ancak bir yayım tetiği ateşledikten sonra artıyor
(`tazeleme.Karar.sayilir` · `durum_yaz(sayilan=…)`).

TARİFİ OLMAYAN HAT ÖLÇÜ DIŞIDIR — ve bu ders pahalı ödendi (08.09.2026).
Türev hatlar (makro · carry · tufex) tazeleme takviminde tarifsizdir: üst hat
koştuğunda koşar, saatleri üst hattan gelir. İlk sürüm sayacı HER başarılı
koşuda artırıyordu; türev hatlar günde altı pencerede koşup haftalık saatlerini
ilerletemediği için aynı gün "hak doldu"ya vardı ve üç hat için yanlış alarm
üretildi. Zincirleme etkisi ölçüldü: gecikme alarmı her uyanmada (on dört koşu)
kırmızı bitti ve e-posta gönderdi; bülten denetimi aynı sahte alarmı UYARI
olarak bastı; duman sınaması CANLI defteri okuduğu için o uyarıyla düştü;
duman düştüğü için veri tazeleme üç pencere boyunca HİÇ koşmadı. Bir alarmın
yanlış pozitifi tek bir e-posta değildi — bir zincirdi. Kural: `TETIK`te
olmayan hat için sayaç ne yazılır ne okunur; bu modül onu adıyla "tarifi yok"
diye sınıflar, alarm sınıfına sokmaz.

MÜKERRERLİK KAYDI. Bu ölçü bir alarm kanalında koşuyor ve o kanal günde 40–70
kez uyanıyor (`gecikme.yml`, `workflow_run`). Kayıt yoksa gerçek bir alarm bile
her uyanmada yeniden öter ve iki günde okunmaz olur. `gecikme.py` ile aynı kalıp:
anahtar `hat|sürüm` — aynı hat aynı sürümde takılı kaldığı sürece BİR kez
bildirilir; sürüm ilerler ve yeniden takılırsa yeni alarmdır. Kayıt depoda
durur (`bayatlik_alarm_kaydi.json`), iş akışı yeni alarmda commit eder.

YAYINI DURDURAN SINIF YOK — YAPISAL KİLİT. `gecikme.py`nin eşi bir kural:
`SINIFLAR` içinde yayını durduran bir sınıf HİÇ TANIMLI DEĞİL ve duman sınaması
hem sabiti hem kaynak metnini sınıyor. Sebebi 02.09'da ölçüldü: yayının önünde
duran bir denetimin yanlış alarmı siteyi on iki saat durdurmuştu. Bayat bir
hattı yayından ÇIKARAN kapı, bayatlığı yokluğa çevirir — yani ölçtüğü şeyi
büyütür.

Komut satırı (gecikme.yml bu biçimde çağırır):
    python3 -u bulten/bayatlik.py --kayit bulten/bayatlik_alarm_kaydi.json \
        --kaydi-yaz --cikti "$GITHUB_OUTPUT"
Çıkış kodu 1 yalnız YENİ (kayda göre henüz bildirilmemiş) alarm varken.
"""

from __future__ import annotations

import argparse
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
ALARM_KAYDI = BURASI / "bayatlik_alarm_kaydi.json"

sys.path.insert(0, str(BURASI))
sys.path.insert(0, str(KOK / "ortak"))
import ayar          # noqa: E402
import bicim         # noqa: E402
import tazeleme      # noqa: E402

# Üç sınıf. Dördüncüsü — yayını durduran sınıf — BİLEREK yoktur; bkz. modül
# başlığı ve `bulten/duman.py`nin ölçütü.
SINIFLAR = ("saglikli", "bilgi", "alarm")
TARIFSIZ = "tazeleme takviminde tarifi yok — saati beslendiği üst hattan gelir, bu ölçü uygulanmaz"


@dataclass
class Bulgu:
    hat: str                      # kütükteki kısa ad
    slug: str
    ad: str                       # okurun gördüğü ad
    sinif: str
    surum: str                    # son görülen veri sürümü (izlenen saatler)
    deneme: int                   # sürümü ilerletmeyen ardışık SAYILAN koşu
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
        yas, _ham = _veri_yasi(slug, bugun) if slug else (None, "")
        ortak = dict(hat=hat, slug=slug, ad=ayar.HAT_ADI.get(slug, slug or hat),
                     veri_yasi_gun=yas, ritim_gun=ayar.RITIM.get(slug))
        if hat not in tazeleme.TETIK:
            # TARİFİ YOK: sayaç bu hat için ne yazılır ne okunur. Defterde eski
            # bir sayaç kalmış olsa bile (temizlik bir sonraki koşuda) alarm
            # sınıfına GİREMEZ — bkz. modül başlığı, 08.09.2026.
            cikti.append(Bulgu(sinif="saglikli", surum="—", deneme=0,
                               sebep=TARIFSIZ, **ortak))
            continue
        n = int(denemeler.get(hat, 0) or 0)
        if n >= tazeleme.TEKRAR_HAKKI:
            sinif = "alarm"
            sebep = (f"kaynak yayımladı, veri gelmedi: {n} koşudur izlenen saat "
                     f"ilerlemiyor ve yeniden deneme hakkı doldu")
        elif n:
            sinif = "bilgi"
            sebep = (f"son {n} koşu izlenen saati ilerletmedi; yeniden deneme "
                     f"sürüyor ({n}/{tazeleme.TEKRAR_HAKKI})")
        else:
            sinif = "saglikli"
            sebep = "son koşu veriyi ilerletti"
        cikti.append(Bulgu(sinif=sinif, surum=str(surumler.get(hat, "") or "?"),
                           deneme=n, sebep=sebep, **ortak))
    return cikti


def alarmlar(simdi: dt.datetime | None = None) -> list[Bulgu]:
    return [b for b in bulgular(simdi) if b.sinif == "alarm"]


# ── mükerrerlik kaydı ────────────────────────────────────────────────────────

def _alarm_anahtari(b: Bulgu) -> str:
    """Aynı hat aynı sürümde takılıysa aynı alarm. Sürüm ilerleyip yeniden
    takılırsa anahtar değişir — o YENİ bir alarmdır."""
    return f"{b.hat}|{b.surum}"


def alarm_kaydi_oku(yol: Path | None = None) -> dict:
    p = Path(yol) if yol else ALARM_KAYDI
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def alarm_kaydi_yaz(yol: Path | None, bulgular_: list[Bulgu],
                    simdi: dt.datetime | None = None) -> dict:
    """Yeni alarmları kayda işle; mevcut kayıtlar korunur."""
    p = Path(yol) if yol else ALARM_KAYDI
    simdi = simdi or dt.datetime.now()
    eski = alarm_kaydi_oku(p)
    kayitlar = dict(eski.get("kayitlar") or {})
    for b in bulgular_:
        kayitlar.setdefault(_alarm_anahtari(b), {
            "hat": b.hat, "ad": b.ad, "surum": b.surum, "deneme": b.deneme,
            "ilk_bildirim": simdi.isoformat(timespec="seconds")})
    yeni = {"aciklama": "Bayat hat alarmının mükerrerlik kaydı: hat|sürüm anahtarı "
                        "bir kez bildirilir. gecikme.yml yeni alarmda bu dosyayı "
                        "commit eder; bulten/bayatlik.py okur.",
            "kayitlar": dict(sorted(kayitlar.items()))}
    p.write_text(json.dumps(yeni, ensure_ascii=False, indent=1) + "\n",
                 encoding="utf-8")
    return yeni


def karar(simdi: dt.datetime | None = None, kayit: Path | None = None) -> dict:
    """Alarm listesi ve kayda göre ayrımı: `yeni` (henüz bildirilmemiş),
    `bilinen` (aynı hat aynı sürümde daha önce bildirildi)."""
    al = alarmlar(simdi)
    bilinen_anahtar = set((alarm_kaydi_oku(kayit).get("kayitlar") or {}).keys()) \
        if kayit else set()
    yeni = [b for b in al if _alarm_anahtari(b) not in bilinen_anahtar]
    bilinen = [b for b in al if _alarm_anahtari(b) in bilinen_anahtar]
    return {"alarm": al, "yeni": yeni, "bilinen": bilinen}


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
        satir.append(f"  {im} {x.ad:34s} sürüm {x.surum:24s} "
                     f"deneme {x.deneme}/{tazeleme.TEKRAR_HAKKI}  veri {yas}"
                     + (f" — {x.sebep}" if x.sinif != "saglikli" or x.sebep == TARIFSIZ else ""))
    return "\n".join(satir)


def _ozet(bulgular_: list[Bulgu]) -> str:
    return " · ".join(f"{b.ad} (sürüm {b.surum}, {b.deneme} koşu)" for b in bulgular_)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--kayit", help="mükerrerlik kaydı (JSON); verilmezse kayıt "
                                    "okunmaz, her alarm YENİ sayılır")
    ap.add_argument("--kaydi-yaz", action="store_true",
                    help="yeni alarmları kayda işle (kanal ÖNCE bunu yapar, SONRA alarm verir)")
    ap.add_argument("--cikti", help="GITHUB_OUTPUT biçiminde karar dosyası")
    a = ap.parse_args(argv)

    kayit = Path(a.kayit) if a.kayit else None
    k = karar(kayit=kayit)
    print(rapor())
    if k["bilinen"]:
        print(f"\n{len(k['bilinen'])} hat bayat ama zaten bildirildi (aynı sürüm): "
              + _ozet(k["bilinen"]))
    if k["yeni"] and a.kaydi_yaz:
        alarm_kaydi_yaz(kayit, k["yeni"])
        print(f"kayıt yazıldı: {kayit or ALARM_KAYDI}")
    if a.cikti:
        with open(a.cikti, "a", encoding="utf-8") as f:
            f.write(f"bayat_alarm={len(k['alarm'])}\n")
            f.write(f"bayat_yeni={'1' if k['yeni'] else '0'}\n")
            f.write(f"bayat_ozet={_ozet(k['yeni'])}\n")
    if k["yeni"]:
        print(f"\n{len(k['yeni'])} hat: kaynak yayımladı, veri gelmedi — {_ozet(k['yeni'])}")
        # Çıkış kodu 1: alarmı taşıyan iş akışı DÜŞER ve düşen iş akışı
        # e-posta gönderir. Yayın zinciri bu koddan etkilenmez — bu modül
        # yayın kapısında DEĞİL, alarm kanalında koşuyor.
        return 1
    print("\nyeni alarm yok."
          + ("" if k["alarm"] else " Kaynak yayımlayıp veri getirmeyen hat yok."))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
