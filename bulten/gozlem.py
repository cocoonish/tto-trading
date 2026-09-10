#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bülten — anlık görüntü deposu.

Her hattın ozet.json'u her koşuda `gecmis/<hat>.jsonl` dosyasına eklenir (yalnız
İÇERİK DEĞİŞTİYSE). Bülten "dün neredeydi, bugün nerede" sorusunu bu depodan
cevaplar.

Kritik ayrıntı — kıyas noktası: bir hat günde iki kez koşulursa iki anlık
görüntü aynı veri sürümünü (_tarih) taşır ve farkları sıfır çıkar. O yüzden
kıyas, `_tarih`i FARKLI olan en son görüntüye göre yapılır: "son veri
yayımından bu yana ne değişti". Aksi hâlde bülten her gün "değişiklik yok"
derdi — hattın verisi haftalıkken bile.

Depo git'ten de kurulabilir: ozet.json dosyaları depoda izlendiği için geçmiş
commit'lerden gerçek bir tarihçe çıkarılabilir (`--git` ile).
"""
from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ortak"))
import bicim  # noqa: E402  — tarih ayrıştırma TEK kaynaktan

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent
PROJELER = KOK / "site" / "public" / "projeler"
GECMIS = BURASI / "gecmis"
GECMIS.mkdir(parents=True, exist_ok=True)


def ozet_yolu(hat: str) -> Path:
    return PROJELER / hat / "ozet.json"


def anlik(hat: str) -> dict | None:
    y = ozet_yolu(hat)
    if not y.exists():
        return None
    try:
        return json.loads(y.read_text(encoding="utf-8"))
    except Exception:
        return None


def _tarih_of(d: dict) -> str:
    for a in ("_tarih", "_tarih2", "tarih"):
        if d.get(a):
            return str(d[a])
    return "?"


def gecmis_oku(hat: str) -> list[dict]:
    y = GECMIS / f"{hat}.jsonl"
    if not y.exists():
        return []
    kayit = []
    for satir in y.read_text(encoding="utf-8").splitlines():
        satir = satir.strip()
        if not satir:
            continue
        try:
            kayit.append(json.loads(satir))
        except json.JSONDecodeError:
            continue
    return kayit


def kaydet(hat: str, ozet: dict, zaman: str | None = None) -> bool:
    """Yeni anlık görüntüyü ekle. İçerik öncekiyle aynıysa yazma. Dönüş: yazıldı mı."""
    onceki = gecmis_oku(hat)
    if onceki and onceki[-1].get("d") == ozet:
        return False
    kayit = {"t": zaman or datetime.now().isoformat(timespec="seconds"),
             "v": _tarih_of(ozet), "d": ozet}
    with open(GECMIS / f"{hat}.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(kayit, ensure_ascii=False) + "\n")
    return True


def onceki_surum(hat: str, simdiki_tarih: str) -> dict | None:
    """`_tarih`i şimdikinden FARKLI olan en son anlık görüntü.

    Kıyas noktası budur: aynı veri sürümünün iki kopyası arasındaki fark sıfırdır
    ve bülten hiçbir şey söylemezdi.
    """
    for kayit in reversed(gecmis_oku(hat)):
        if kayit.get("v") != simdiki_tarih:
            return kayit
    return None


# ─────────────────────────────────────────── anahtar başına SAAT
# Bir ozet.json'da tek bir yayım ritmi yoktur. tcmb-net-rezerv'in `_tarih`i
# günlük analitik bilançodan gelir (her iş günü 14:30), ama `h_net` haftalık
# para-banka istatistiğinden (Perşembe 14:30) gelir ve `h_tarih`te durur.
# Hepsi `_tarih` üzerinden okunursa iki yanlış birden çıkar:
#   · panel 14.08 tarihli bir sayıyı 24.08 etiketiyle gösterir,
#   · kıyas noktası her iş günü ilerlediği için haftalık serinin farkı hep
#     sıfır görünür ve gerçek hareket bir günde kaybolur.
# Kural: bir anahtarın kendi saati, önce açıkça tanımlanan alan, yoksa
# `<anahtar>_tarih` geleneği (projelerin ozet_uret.py'leri bunu zaten yazıyor),
# o da yoksa hattın ana saati `_tarih`tir.

def tarih_alani(d: dict, anahtar: str, acik: str = "") -> str:
    """Bir anahtarın saatini tutan alanın ADI. "" → hattın ana saati."""
    if acik:
        return acik
    aday = f"{anahtar}_tarih"
    return aday if isinstance(d, dict) and d.get(aday) else ""


def anahtar_tarihi(d: dict, anahtar: str, acik: str = "") -> str:
    """Bir anahtarın kendi veri tarihi (yoksa hattın ana saatine düşer)."""
    if not isinstance(d, dict):
        return "?"
    alan = tarih_alani(d, anahtar, acik)
    if alan and d.get(alan):
        return str(d[alan])
    return _tarih_of(d)


_AY_DAMGASI = re.compile(r"^\s*\d{1,2}[./]\d{4}\s*$")


def _ay_hassasiyeti(t: str) -> bool:
    """Damga AY hassasiyetinde mi (08.2026) yoksa GÜN mü (01.08.2026)."""
    return bool(_AY_DAMGASI.match(str(t)))


def _ileri_gitti(eski: str, yeni: str) -> bool:
    """Saat GERÇEKTEN ilerledi mi — dizge kıyası değil TARİH kıyası.

    İki kusur birden kapatıyor ve ikisi de 10.09.2026 sayısında ölçüldü.
    (1) YAZIM DEĞİŞİKLİĞİ İLERLEME SAYILIYORDU: Büyüme hattının saati
    "30.06.2026"dan "06.2026"ya döndü — aynı gün, başka yazım — ve iki sayısı
    da BİREBİR aynı kaldığı hâlde hat "veri sürümü ilerledi" diye duyuruldu.
    (2) GERİLEME DE İLERLEME SAYILIYORDU: OVP hattı "09.09.2026 → 08.09.2026"
    diye, yani bir GERİ adımı "ilerledi" diye bastı.

    Çözülebilen iki tarih varsa kıyas SIKI BÜYÜKTÜR; biri çözülemiyorsa dizge
    eşitsizliğine düşülür — ayrıştıramayan bir denetim hep "sorun yok" der,
    o yüzden çözülemeyen hâl susturulmuyor, eski davranışta bırakılıyor."""
    e, y = bicim.tarihe_cevir(eski), bicim.tarihe_cevir(yeni)
    if e is None or y is None:
        return str(eski) != str(yeni)
    # AYNI AYIN İKİ YAZIMI İLERLEME DEĞİLDİR. Ay damgası ortak/bicim
    # sözleşmesinde ayın SON gününe demirlenir; bu yüzden "01.08.2026 →
    # 08.2026" çözüldüğünde 01 Ağustos → 31 Ağustos olur ve saf tarih kıyası
    # otuz günlük sahte bir ilerleme görür. Ay SONU yazımı (30.06.2026 →
    # 06.2026) tesadüfen aynı güne düştüğü için ilk yazımda bu kaçtı: kural
    # ayın son gününde doğru, ayın başında yanlış cevap veriyordu ve 10.09.2026
    # bülteninde el-nino satırında canlıydı. Ölçü GÜN değil, damganın
    # HASSASİYETİ: biri ay biri gün hassasiyetindeyse ve ikisi aynı aya
    # düşüyorsa, değişen şey veri değil YAZIMDIR.
    if (e.year, e.month) == (y.year, y.month) and _ay_hassasiyeti(eski) != _ay_hassasiyeti(yeni):
        return False
    return y > e


def surum_ilerledi(hat: str, simdi: dict, anahtar: str, acik: str = "") -> bool:
    """Bu anahtarın saati BİR ÖNCEKİ SÜRÜME göre ilerledi mi.

    "Önceki sürüm", defterde BUGÜNKÜ görüntüden farklı olan en son kayıttır —
    sondan ikinci kayıt DEĞİL. Ayrım şart: `kaydet` yalnız içerik değiştiğinde
    satır yazar, yani hattın dosyası günlerce aynı kaldığında defterin son
    kaydı bugünkü görüntünün ta kendisidir ve sondan ikinciye bakmak bir sürüm
    fazla geriye gider. O hâlde ölçüt donmuş bir hattı "ilerledi" sayardı ve
    düzeltmek istediği tekrarı aynen üretirdi.

    Defterde farklı bir sürüm hiç yoksa ilerlemiş sayılır: ilk gözlem
    duyurulabilmelidir."""
    for kayit in reversed(gecmis_oku(hat)):
        d = kayit.get("d")
        if not isinstance(d, dict) or anahtar not in d:
            continue
        if d == simdi:
            continue
        return _ileri_gitti(anahtar_tarihi(d, anahtar, acik),
                            anahtar_tarihi(simdi, anahtar, acik))
    return True


def onceki_surum_anahtar(hat: str, anahtar: str, acik: str = "",
                         simdiki_tarih: str = "") -> dict | None:
    """O ANAHTARIN tarihi şimdikinden FARKLI olan en son anlık görüntü.

    `onceki_surum`un anahtar başına çalışan hâli: haftalık bir seri, hattın
    günlük saati ilerlediği için "değişmedi" sayılmasın.
    """
    for kayit in reversed(gecmis_oku(hat)):
        d = kayit.get("d")
        if not isinstance(d, dict) or anahtar not in d:
            continue
        if anahtar_tarihi(d, anahtar, acik) != simdiki_tarih:
            return kayit
    return None


def _dizi_basi(kayitlar: list[dict], deger) -> dict:
    """Sondaki AYNI değerli kesintisiz dizinin ilk kaydı.

    "İlk görülme"yi tarihçenin tamamında aramak yanlış: revizyonla eski bir
    değere dönülürse gecikme olduğundan büyük ölçülür. Aranan, o değere en son
    NE ZAMAN geçildiğidir.
    """
    ilk = kayitlar[-1]
    for k in reversed(kayitlar):
        if k["_deger"] != deger:
            break
        ilk = k
    return ilk


def son_gorulme(hat: str) -> tuple[str, str] | None:
    """(veri sürümü, o sürüme geçilen an) — hat düzeyinde gecikme denetimi."""
    kayitlar = [{**k, "_deger": k.get("v")} for k in gecmis_oku(hat)]
    if not kayitlar:
        return None
    son_v = kayitlar[-1]["_deger"]
    return son_v, _dizi_basi(kayitlar, son_v).get("t", "")


def alan_son_gorulme(hat: str, alan: str) -> tuple[str, str] | None:
    """(alanın değeri, o değere geçilen an) — ALAN düzeyinde gecikme denetimi.

    Hattın ana saati tıkırdarken içindeki haftalık serinin donması, `_tarih`e
    bakan bir denetim için görünmezdir; burada o alan doğrudan izlenir.
    """
    kayitlar = [{**k, "_deger": str(k["d"][alan])} for k in gecmis_oku(hat)
                if isinstance(k.get("d"), dict) and k["d"].get(alan)]
    if not kayitlar:
        return None
    son = kayitlar[-1]["_deger"]
    return son, _dizi_basi(kayitlar, son).get("t", "")


def anahtar_hafta_once(hat: str, anahtar: str, acik: str = "",
                       gun: int = 7) -> dict | None:
    """Bir anahtar için HAFTALIK kıyas noktası: en az `gun` gün önceki görüntü.

    Haftalık bülten "geçen hafta bu saatte neredeydik" sorar; günlük bülten
    "son yayımdan bu yana ne değişti". İkisi farklı sorulardır ve haftalıkta
    sürüm kıyası yanlış cevabı verir — haftalık bir seri hafta içinde bir kez
    yayımlanır, sürüm kıyası o tek yayımı gösterir, oysa haftanın tamamı
    sorulmuştur.

    Tarihçe yetmezse None döner: uydurma kıyas yerine günlük kıyasa düşülür ve
    bülten hangisini kullandığını yazar.
    """
    from datetime import datetime, timedelta
    sinir = datetime.now() - timedelta(days=gun)
    aday = None
    for kayit in gecmis_oku(hat):
        d = kayit.get("d")
        if not isinstance(d, dict) or anahtar not in d:
            continue
        try:
            t = datetime.fromisoformat(str(kayit.get("t", "")).replace("Z", "+00:00")
                                       ).replace(tzinfo=None)
        except (ValueError, TypeError):
            continue
        if t <= sinir:
            aday = kayit
    return aday


def gun_once(hat: str, gun: int = 7) -> dict | None:
    """En az `gun` gün önceki son anlık görüntü — haftalık kıyas için.

    Günlük bülten "son veri yayımından bu yana"ya bakar; haftalık bülten ise
    "geçen hafta bu saatte neredeydik" sorusunu sorar. İkisi farklı sorulardır:
    haftalık seride birincisi tek bir yayımı, ikincisi tüm haftayı kapsar.
    """
    from datetime import datetime, timedelta
    sinir = datetime.now() - timedelta(days=gun)
    aday = None
    for kayit in gecmis_oku(hat):
        try:
            t = datetime.fromisoformat(str(kayit.get("t", "")).replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            continue
        if t <= sinir:
            aday = kayit
    return aday


# ─────────────────────────────────────────── git'ten tarihçe kurma
def git_bootstrap(hatlar: list[str], sessiz=False) -> dict[str, int]:
    """Depo geçmişindeki ozet.json sürümlerinden tarihçe kur.

    Böylece sistem ilk gününde bile gerçek 'geçen haftaya göre' farkı üretebilir;
    aksi hâlde ilk bülten boş çıkardı.
    """
    sonuc = {}
    for hat in hatlar:
        rel = f"site/public/projeler/{hat}/ozet.json"
        log = subprocess.run(["git", "log", "--reverse", "--format=%H %cI", "--", rel],
                             cwd=KOK, capture_output=True, text=True)
        n = 0
        mevcut = {(k.get("t"), k.get("v")) for k in gecmis_oku(hat)}
        for satir in log.stdout.splitlines():
            if not satir.strip():
                continue
            sha, zaman = satir.split(None, 1)
            ic = subprocess.run(["git", "show", f"{sha}:{rel}"], cwd=KOK,
                                capture_output=True, text=True)
            if ic.returncode != 0:
                continue
            try:
                d = json.loads(ic.stdout)
            except json.JSONDecodeError:
                continue
            anahtar = (zaman.strip(), _tarih_of(d))
            if anahtar in mevcut:
                continue
            if kaydet(hat, d, zaman=zaman.strip()):
                n += 1
        sonuc[hat] = n
        if not sessiz:
            print(f"  {hat:26s} {n} sürüm eklendi")
    return sonuc


if __name__ == "__main__":
    import sys
    from ayar import RITIM
    if "--git" in sys.argv:
        print("git geçmişinden tarihçe kuruluyor…")
        git_bootstrap(list(RITIM))
    else:
        for h in RITIM:
            k = gecmis_oku(h)
            sg = son_gorulme(h)
            print(f"  {h:26s} {len(k):3d} görüntü" + (f" · son sürüm {sg[0]} ({sg[1][:10]})" if sg else ""))
