#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Yayın gecikmesinin TEK tanımı — ölçer ve kaydeder, HİÇBİR ŞEYİ DURDURMAZ.

NEDEN VAR. 04.09.2026 sabahı bülten söz verilen saatin 41 dakika ötesinde
sitede oldu ve bunu kullanıcı fark etti; sistem 65 dakika boyunca bildiği hâlde
hiçbir şey söylemedi. Sebebi basit: SÖZ ile GERÇEKLEŞME hiçbir yerde
karşılaştırılmıyordu. Sitenin ilanı (`site/src/data/yayin_takvimi.json`) ve
gerçekleşen anlar (bültenin kendi damgaları, koşu nabzı, gönderi defteri) aynı
depoda duruyordu; ikisini yan yana koyan tek satır kod yoktu. Bu modül o satır.

ÜÇ SINIF VARDIR VE DÖRDÜNCÜSÜ BİLEREK YOKTUR: zamaninda · uyari · alarm.
Yayını DURDURAN bir sınıf bu modülde TANIMLI DEĞİLDİR ve tanımlanmamalıdır.
Geç kalmış bir bülteni durduran bir kapı, gecikmeyi yokluğa çevirir: 02.09'da
yayın kapısının yanlış alarmı siteyi on iki saat dondurmuştu. Kilit yapısaldır
— `bulten/duman.py` bu modülün üçten fazla sınıf tanımlamadığını sınar, yani
gecikme ölçüsü ileride bir yayın kapısına bağlanmak istenirse sınama düşer.

ÖLÇÜ NEDİR. "Yazılan bülten geç mi yazıldı" değil, "SÖZ VERİLEN SAATTE
yerinde miydi". İkincisi yazı hiç gerçekleşmediğinde de konuşur:
  · söz = o günün EN ERKEN tüketici adımı (sitede / X gönderisi), UTC
  · pay = o yayının EN GEÇ tüketici adımı − en erken (hafta içi 24, pazar 16 dk)
  · gerçekleşen = yazı anı (`ilk_yazi_zamani`); yoksa henüz yazılmamış demektir
    ve gecikme "şimdi"ye göre ölçülür.
Söz ve pay KODA YAZILMAZ, takvimden çözülür; takvim de `ortak/yayin_takvimi.
karsilastir` ile iş akışı cron'larına kilitli. Cron kayarsa söz de kayar.

UYDURMA YOK. `ilk_yazi_zamani` alanı yalnız 03.09.2026'dan beri yazılıyor.
Ondan eski bir bülten YAZILMIŞ ama yazı anı kaydedilmemişse ölçüm damgası
(`olusturma`) ALT SINIR olarak kullanılır ve satır `alt_sinir` ile etiketlenir:
gerçek yazı anı ondan 11–14 dakika sonradır, yani o günlerin "zamanında"
hükümleri göründüğünden incedir. Hiç ölçülemeyen bir bacak SIFIR yazılmaz,
boş bırakılır ve sebebi `olculmedi` alanına yazılır.

Kullanım:
    python3 bulten/gecikme.py                 # bugünün satırları
    python3 bulten/gecikme.py --gun 2026-09-04
    python3 bulten/gecikme.py --gecmis        # kayıtlı bütün günleri yeniden oynat
    python3 bulten/gecikme.py --alarm         # bugün alarm varsa çıkış kodu 1
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent
DEFTER = BURASI / "gecikme_defteri.jsonl"

# İstanbul saati takvimde SABİT UTC+3 yazılıyor (ortak/yayin_takvimi.py aynı
# varsayımla cron'la karşılaştırıyor); iki yerde iki ayrı dilim olmasın.
TR_SAAT = 3

# TÜKETİCİ ADIMI = okurun çıktıyı gördüğü adım. "ölçüm" ve "nöbetçi yoklaması"
# ara halkalardır: kendi hedeflerine göre alarm üretmek ölçüldü ve REDDEDİLDİ
# (bulten.yml'in ilan edilen 06:23'ü son on hafta içi gözlemin ONUNDA da
# kaçırılmış; her sabah öten alarm iki haftada okunmaz olur). Ara halkalar
# defterde ve raporda görünür, eşiğe girmez.
TUKETICI = ("sitede", "X gönderisi")

# Üç sınıf. Dördüncüsü — yayını durduran sınıf — bilerek yoktur; bkz. modül
# başlığı ve duman sınaması.
SINIFLAR = ("zamaninda", "uyari", "alarm")

# Takvimin "gunler" alanı → hafta günü numaraları (Pzt=0).
GUNLER = {"hafta içi": (0, 1, 2, 3, 4), "pazar": (6,)}

# Yayın adı → (gerçekleşme kaydının nerede durduğu, gönderi defteri anahtarı).
# Tanınmayan bir yayın SESSİZCE ATLANMAZ: satırı üretilir ve "kaydı tanımlı
# değil" diye işaretlenir — bir denetimin bakmadığı yer, geçen sınavla aynı
# görünür.
KAYNAK = {
    "Günlük bülten": ("bulten", "bulten"),
    "Haftaya bakış": ("bulten", "bulten"),
    "Haftalık teknik analiz": ("teknik", "teknik"),
}

# Tekrar koşulu: son beş YAYIN gününün en az üçü uyarı/alarm.
# YÖNTEMSEL SEÇİM, ölçüm değil — "bir iş haftası". Yirmi gözlem birikince
# gecikme dağılımından yeniden türetilmeli (bkz. PLAN olculmesi_gerekenler).
TEKRAR_PENCERE = 5
TEKRAR_ESIK = 3


# ── biçim ────────────────────────────────────────────────────────────────────

def _sayi(v: float | None, ondalik: int = 1) -> str:
    """Sayı yazımı TEK kaynaktan (ortak/bicim); o okunamazsa aynı sözleşmeyle."""
    if v is None:
        return "—"
    try:
        sys.path.insert(0, str(KOK / "ortak"))
        import bicim
        return bicim.sayi(v, ondalik)
    except Exception:                                          # noqa: BLE001
        return f"{v:.{ondalik}f}".replace(".", ",").replace("-", "−")


# ── takvim: söz ve pay ───────────────────────────────────────────────────────

def takvim(kok: Path) -> dict:
    yol = Path(kok) / "site" / "src" / "data" / "yayin_takvimi.json"
    return json.loads(yol.read_text(encoding="utf-8"))


def yayinlar(kok: Path, gun: dt.date) -> list[str]:
    """O gün takvime göre çıkması gereken yayınlar (sırası takvimdeki sırasıdır)."""
    cikti = []
    for y in takvim(kok).get("yayinlar", []):
        gunler = GUNLER.get(str(y.get("gunler", "")))
        if not gunler or gun.weekday() not in gunler:
            continue
        if not y.get("adimlar"):
            continue
        cikti.append(str(y.get("yayin", "")))
    return cikti


def _tuketici_saatler(kok: Path, yayin: str) -> list[tuple[str, int]]:
    """Yayının tüketici adımları — (ad, İstanbul dakikası) listesi, artan."""
    for y in takvim(kok).get("yayinlar", []):
        if str(y.get("yayin", "")) != yayin:
            continue
        saatler = []
        for a in y.get("adimlar", []):
            if str(a.get("ad", "")) not in TUKETICI:
                continue
            ist = str(a.get("istanbul", ""))
            try:
                s, d = ist.split(":")
                saatler.append((str(a.get("ad")), int(s) * 60 + int(d)))
            except ValueError:
                raise ValueError(f"{yayin} · {a.get('ad')}: saat okunamadı ({ist!r})")
        if not saatler:
            # Kapsam kusuruna karşı: sitede yayımlanan bir yayının tüketici
            # adımı hiç yoksa SESSİZCE GEÇMEK, ölçüyü o yayın için kapatmak
            # demektir ve kimse fark etmez.
            raise ValueError(f"{yayin}: takvimde tüketici adımı yok "
                             f"({' / '.join(TUKETICI)}) — gecikme ölçülemez")
        return sorted(saatler, key=lambda x: x[1])
    raise KeyError(f"takvimde böyle bir yayın yok: {yayin}")


def soz(kok: Path, yayin: str, gun: dt.date) -> dt.datetime:
    """O yayının o günkü SÖZÜ: en erken tüketici adımı, UTC."""
    _ad, dakika = _tuketici_saatler(kok, yayin)[0]
    return (dt.datetime.combine(gun, dt.time(0, 0), dt.timezone.utc)
            + dt.timedelta(minutes=dakika - TR_SAAT * 60))


def pay(kok: Path, yayin: str) -> int:
    """Tolerans = en GEÇ tüketici adımı − en erken (dakika).

    Uydurma bir sayı değil, takvimin KENDİ tüketici aralığı: içerik son
    tüketici adımına kadar yerindeyse okura verilen sözlerin tamamı hâlâ
    tutulabilir. Hafta içi 24 dk (08:11 → 08:35), pazar 16 dk (18:25 → 18:41).
    """
    saatler = _tuketici_saatler(kok, yayin)
    return saatler[-1][1] - saatler[0][1]


# ── gerçekleşen: hepsi ZATEN VAR OLAN alanlardan ─────────────────────────────

def _json(yol: Path):
    try:
        return json.loads(yol.read_text(encoding="utf-8"))
    except Exception:                                          # noqa: BLE001
        return None


def _an(v) -> dt.datetime | None:
    """ISO damgayı UTC'ye çevir. Dilimsiz damgalar UTC'dir (ölçüm katmanı
    `datetime.now(timezone.utc)` yazıyor; eski dosyalarda offset basılmamış)."""
    if not v:
        return None
    try:
        t = dt.datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except ValueError:
        return None
    return t.replace(tzinfo=dt.timezone.utc) if t.tzinfo is None else t.astimezone(dt.timezone.utc)


def _dk(a: dt.datetime | None, b: dt.datetime | None) -> float | None:
    if a is None or b is None:
        return None
    return round((b - a).total_seconds() / 60, 1)


def _gerceklesen(kok: Path, yayin: str, gun: dt.date) -> dict:
    """Bir yayının o günkü halkaları: veri · ölçüm · yazı · X.

    Hiçbir yeni damga yazılmaz; hepsi zaten depoda duran alanlardan okunur —
    bu sayede tarihçe geriye dönük oynatılabiliyor ve eşik sınanabiliyor.
    """
    kok = Path(kok)
    d: dict = {"olcum": None, "yazi": None, "x": None, "veri": None,
               "alt_sinir": False, "olculmedi": "", "dosya_var": False}

    # veri halkası: iş akışının nabzı. YALNIZ o güne aitse sayılır — dünkü
    # nabız "bugün veri koşusu oldu" demek değildir (04.09'un imzası budur).
    nabiz = _json(kok / "bulten" / "kosu_nabzi.json") or {}
    v = _an(nabiz.get("veri_kosusu"))
    if v is not None and v.date() == gun:
        d["veri"] = v

    tur, tweet_anahtari = KAYNAK.get(yayin, (None, None))
    if tur is None:
        d["olculmedi"] = "bu yayının gerçekleşme kaydı tanımlı değil"
        return d

    if tur == "bulten":
        b = _json(kok / "site" / "src" / "data" / "bulten" / f"{gun.isoformat()}.json")
        if b is None:
            d["olculmedi"] = "o güne ait ölçüm dosyası yok"
        else:
            d["dosya_var"] = True
            d["olcum"] = _an(b.get("olusturma"))
            d["yazi"] = _an(b.get("ilk_yazi_zamani"))
            if d["yazi"] is None and b.get("gundem_kaynagi") == "yazili":
                # Yazılmış ama yazı anı kaydedilmemiş (03.09 öncesi). Ölçüm
                # damgası ALT SINIRDIR: gerçek yazı ondan sonradır.
                d["yazi"], d["alt_sinir"] = d["olcum"], True
                d["olculmedi"] = ("yazı anı kaydedilmemiş; ölçüm damgası ALT SINIR "
                                  "olarak kullanıldı")
    else:
        b = _json(kok / "site" / "src" / "data" / "teknik" / f"{gun.isoformat()}.json")
        if b is None:
            d["olculmedi"] = "o güne ait ölçüm dosyası yok"
        else:
            d["dosya_var"] = True
            d["olcum"] = _an(b.get("olcum_zamani"))
            if b.get("yazili"):
                d["yazi"], d["alt_sinir"] = d["olcum"], True
                d["olculmedi"] = ("yazı anı kaydedilmemiş; ölçüm damgası ALT SINIR "
                                  "olarak kullanıldı")

    defter = _json(kok / "site" / "src" / "data" / "tweet" / "defter.json") or {}
    kayit = defter.get(f"{tweet_anahtari}:{gun.isoformat()}") or {}
    d["x"] = _an(kayit.get("zaman"))
    return d


# ── karar ────────────────────────────────────────────────────────────────────

def _sinifla(gecikme_dk: float, pay_dk: int, olcum_var: bool) -> str:
    """Üç sınıf; dördüncüsü yok.

    · gecikme ≤ 0            → zamaninda (sınır DIŞLAMALI DEĞİL: tam 0 zamanında)
    · ölçüm dosyası hiç yok  → alarm. Bu bir gecikme değil YOKLUKTUR: söz
      verilen saatte yayımlanacak bir sayı ortada yoktur ve payı da yoktur.
    · 0 < gecikme ≤ pay      → uyari (içerik son tüketici adımından önce yerinde)
    · gecikme > pay          → alarm
    """
    if gecikme_dk <= 0:
        return "zamaninda"
    if not olcum_var:
        return "alarm"
    return "uyari" if gecikme_dk <= pay_dk else "alarm"


def _darbogaz(g: dict, gun: dt.date) -> str:
    """Zincirin hangi halkası yedi. Kırık halka varsa O yazılır."""
    if not g.get("dosya_var"):
        return "ölçüm"
    if g.get("veri") is None:
        # Kırık halkayı ADIYLA söyler ama neyin ölçülmediğini de söyler: o güne
        # ait bir veri koşusu kaydı YOKSA "veri geç kaldı" demek bir ölçüm
        # değil tahmindir. (Nabız dosyası bugün yalnız SON koşuyu tutuyor.)
        return "veri — o güne ait koşu kaydı yok"
    if g.get("yazi") is None:
        return "yazı"
    bacak = {"ölçüm": _dk(g["veri"], g["olcum"]),
             "yazı": _dk(g["olcum"], g["yazi"]),
             "X gönderisi": _dk(g["yazi"], g["x"])}
    olculen = {k: v for k, v in bacak.items() if v is not None}
    return max(olculen, key=olculen.get) if olculen else ""


def olc(kok: Path, gun: dt.date | None = None, simdi: dt.datetime | None = None,
        yayin: str | None = None) -> list[dict]:
    """O günün her yayını için bir satır. Yayın günü değilse boş liste."""
    kok = Path(kok)
    gun = gun or dt.date.today()
    simdi = simdi or dt.datetime.now(dt.timezone.utc)
    if simdi.tzinfo is None:
        simdi = simdi.replace(tzinfo=dt.timezone.utc)

    satirlar = []
    for ad in yayinlar(kok, gun):
        if yayin is not None and ad != yayin:
            continue
        s = soz(kok, ad, gun)
        p = pay(kok, ad)
        g = _gerceklesen(kok, ad, gun)
        gerceklesen = g["yazi"]
        if gerceklesen is not None:
            gecikme = round((gerceklesen - s).total_seconds() / 60, 1)
            henuz = False
        else:
            gecikme = round((simdi - s).total_seconds() / 60, 1)
            henuz = True
        sinif = _sinifla(gecikme, p, g["dosya_var"])
        satirlar.append({
            "tarih": gun.isoformat(),
            "yayin": ad,
            "soz": s.isoformat(timespec="seconds"),
            "pay_dk": p,
            "veri_nabzi": g["veri"].isoformat(timespec="seconds") if g["veri"] else None,
            "olcum": g["olcum"].isoformat(timespec="seconds") if g["olcum"] else None,
            "ilk_yazi": gerceklesen.isoformat(timespec="seconds") if gerceklesen else None,
            "gecikme_dk": gecikme,
            "henuz_yazilmadi": henuz,
            "alt_sinir": g["alt_sinir"],
            "olculmedi": g["olculmedi"],
            "darbogaz": _darbogaz(g, gun),
            "sinif": sinif,
            "bacaklar": {
                "veri→olcum": _dk(g["veri"], g["olcum"]),
                "olcum→yazi": _dk(g["olcum"], g["yazi"]),
                "yazi→X": _dk(g["yazi"], g["x"]),
            },
        })
    return satirlar


def ozet_satiri(satir: dict) -> str:
    """Yazı katmanının stdout'una düşen tek cümle."""
    s = _an(satir["soz"])
    ist = (s + dt.timedelta(hours=TR_SAAT)).strftime("%H:%M") if s else "—"
    dk = satir["gecikme_dk"]
    if satir.get("henuz_yazilmadi"):
        return (f"Yayın sözü {ist}; yazı HENÜZ yok, söz {_sayi(abs(dk))} dakika "
                + ("önce geçti." if dk > 0 else "sonra."))
    y = _an(satir["ilk_yazi"])
    ne_zaman = (y + dt.timedelta(hours=TR_SAAT)).strftime("%H:%M") if y else "—"
    tutuldu = "aşıldı" if dk > 0 else "ile tutuldu"
    ek = "  (yazı anı ALT SINIR)" if satir.get("alt_sinir") else ""
    return (f"Yayın sözü {ist}; yazı {ne_zaman}'te bitti, söz "
            f"{_sayi(abs(dk))} dakika {tutuldu}.{ek}")


# ── defter ───────────────────────────────────────────────────────────────────

def defter_oku(defter: Path | None = None) -> list[dict]:
    """Defter satırları, (tarih, yayin) başına SON kayıt kazanır."""
    yol = Path(defter) if defter else DEFTER
    if not yol.exists():
        return []
    son: dict[tuple, dict] = {}
    for satir in yol.read_text(encoding="utf-8").splitlines():
        satir = satir.strip()
        if not satir:
            continue
        try:
            d = json.loads(satir)
        except ValueError:
            continue                       # bozuk satır defteri düşürmez
        son[(d.get("tarih"), d.get("yayin"))] = d
    return [son[k] for k in sorted(son, key=lambda k: (str(k[0]), str(k[1])))]


def defter_yaz(kok: Path, b: dict, gun: dt.date | str,
               defter: Path | None = None,
               simdi: dt.datetime | None = None) -> dict | None:
    """Yazılan bültenin gecikme satırını deftere ekle (append-only).

    Yazı katmanının kaçınamayacağı tek araç `yaz.py`; kayıt onun YAN ETKİSİ,
    ayrı bir adım değil. Hiçbir bayrak, hiçbir argüman gerekmez.
    """
    if isinstance(gun, str):
        gun = dt.date.fromisoformat(gun[:10])
    ad = "Haftaya bakış" if (b.get("tur") == "haftalik" or b.get("haftalik")) \
        else "Günlük bülten"
    satirlar = olc(kok, gun, simdi, yayin=ad)
    if not satirlar:
        return None
    s = dict(satirlar[0])
    s["an"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    yol = Path(defter) if defter else DEFTER
    yol.parent.mkdir(parents=True, exist_ok=True)
    with yol.open("a", encoding="utf-8") as f:
        f.write(json.dumps(s, ensure_ascii=False) + "\n")
    return s


def tekrar(defter: Path | None = None, bugun: dt.date | None = None) -> tuple[bool, str]:
    """Son TEKRAR_PENCERE yayın gününün ≥ TEKRAR_ESIK'i uyarı/alarm mı?

    Tek gün gecikme gürültüden ayrılamaz; bu depodaki arızalar gün-biçimli.
    Defter boşken yapısal olarak SESSİZDİR ve bu bilinçlidir.
    """
    kayit = defter_oku(defter)
    if bugun is not None:
        kayit = [k for k in kayit if str(k.get("tarih", "")) <= bugun.isoformat()]
    gunler: dict[str, str] = {}
    for k in kayit:
        t, s = str(k.get("tarih", "")), str(k.get("sinif", ""))
        # Bir günde iki yayın varsa gün, en kötü sınıfıyla anılır.
        onceki = gunler.get(t, "zamaninda")
        gunler[t] = s if SINIFLAR.index(s if s in SINIFLAR else "zamaninda") \
            > SINIFLAR.index(onceki if onceki in SINIFLAR else "zamaninda") else onceki
    son = [gunler[t] for t in sorted(gunler)[-TEKRAR_PENCERE:]]
    kotu = [x for x in son if x in ("uyari", "alarm")]
    if len(son) < TEKRAR_PENCERE:
        return False, (f"defterde {len(son)} yayın günü var; tekrar koşulu "
                       f"{TEKRAR_PENCERE} gün ister")
    if len(kotu) >= TEKRAR_ESIK:
        return True, (f"son {len(son)} yayın gününün {len(kotu)}'i gecikmeli "
                      f"(eşik {TEKRAR_ESIK})")
    return False, f"son {len(son)} yayın gününün {len(kotu)}'i gecikmeli"


# ── alarm kanalı: kapsam ve mükerrerlik kaydı ────────────────────────────────

# E-POSTA KANALININ KAPSAMI — ölçünün kapsamı DEĞİL.
#
# Ölçü bütün yayınlar için kurulur, defterde ve raporda hepsi görünür. Ama
# e-posta gönderen kanal yalnız eşiği ÖLÇÜLMÜŞ yayını taşır, çünkü "yayının
# önünde duran bir denetimin yanlış alarmı arızanın kendisidir" hükmünün
# kardeşi burada da geçerli: her sabah öten bir alarm iki haftada okunmaz olur.
#
# Bugün o tek yayın günlük bültendir ve hükmü depodaki on hafta içi gözlemden
# geliyor (04.09.2026'da yeniden ölçüldü, `--gecmis`): 08-24, 08-25, 08-26,
# 08-27, 08-28 ve 09-04 alarm; 08-31, 09-01, 09-02, 09-03 temiz. Altı alarmın
# altısı da deponun kendi kaydında arıza geçen günler — YANLIŞ POZİTİF YOK.
#
# Pazarın (Haftaya bakış + Haftalık teknik analiz) elde iki gözlemi var
# (23.08 alarm, 30.08 uyarı ve payı 2,7 dakika) ve iki gözlemle eşik açılmaz.
# Pazar yayınları bu yüzden KAYIT-ONLY: defterde ölçülürler, e-posta
# göndermezler; yokluklarını cron'lu nöbetçi sormaya devam ediyor. Kapsam
# genişletilecekse önce ölçüm birikir — "kapsamı olmayan bir denetim bakmadığı
# yeri geçmiş sayar" biliniyor ve şimdilik bilerek bakılmıyor.
ALARM_KAPSAMI = ("Günlük bülten",)

# Mükerrerlik kaydında kaç satır tutulur. Kayıt bir tarihçe değil, "bu gün için
# alarm zaten gönderildi mi" sorusunun cevabı; pencere değil TAVAN.
ALARM_KAYIT_AZAMI = 120

ALARM_KAYDI = BURASI / "gecikme_alarm_kaydi.json"


def _alarm_anahtari(satir: dict) -> str:
    return f"{satir.get('tarih')}|{satir.get('yayin')}"


def alarm_kaydi_oku(yol: Path | None = None) -> dict:
    """Mükerrerlik kaydı. Bozuk ya da eksik dosya İSTİSNA FIRLATMAZ — kaydı
    okuyamamak alarmı susturmamalı; okunamayan kayıt "hiç alarm gönderilmemiş"
    sayılır, yani en kötü hâlde mükerrer bir e-posta gelir. Kaybolmuş alarmdansa
    çift alarm."""
    p = Path(yol) if yol else ALARM_KAYDI
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except Exception:                                          # noqa: BLE001
        return {}


def alarm_kaydi_yaz(yol: Path | None, satirlar: list[dict],
                    simdi: dt.datetime | None = None) -> dict:
    """Gönderilen alarmları kayda ekle ve dosyayı kur; yazılan sözlüğü döndür."""
    p = Path(yol) if yol else ALARM_KAYDI
    d = alarm_kaydi_oku(p)
    kayitlar = d.get("kayitlar")
    if not isinstance(kayitlar, dict):
        kayitlar = {}
    an = (simdi or dt.datetime.now(dt.timezone.utc)).isoformat(timespec="seconds")
    for s in satirlar:
        kayitlar[_alarm_anahtari(s)] = {
            "an": an,
            "gecikme_dk": s.get("gecikme_dk"),
            "sinif": s.get("sinif"),
            "darbogaz": s.get("darbogaz"),
        }
    if len(kayitlar) > ALARM_KAYIT_AZAMI:
        kalan = sorted(kayitlar)[-ALARM_KAYIT_AZAMI:]
        kayitlar = {k: kayitlar[k] for k in kalan}
    yeni = {
        "_aciklama": ("Gönderilmiş gecikme alarmlarının kaydı. Tek işi aynı gün "
                      "için ikinci kez e-posta göndermemek; ölçünün kendisi "
                      "gecikme_defteri.jsonl'de durur."),
        "kayitlar": kayitlar,
    }
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(yeni, ensure_ascii=False, indent=1) + "\n",
                 encoding="utf-8")
    return yeni


def alarm_karari(kok: Path, gun: dt.date | None = None,
                 kayit: Path | None = None,
                 simdi: dt.datetime | None = None) -> dict:
    """Bildirim kanalının kararı — HİÇBİR YAYINI DURDURMAZ.

    Döndürür: `satirlar` (o günün tamamı), `alarm` (kapsamdaki alarm satırları),
    `yeni` (kayda göre henüz bildirilmemiş olanlar), `gerekce` (tek cümle).
    """
    kok = Path(kok)
    gun = gun or dt.date.today()
    if simdi is None:
        # GEÇMİŞ BİR GÜNÜ BUGÜNÜN SAATİYLE ÖLÇMEK yanlış olurdu: yazılmamış eski
        # bir bülten bugüne kadar geciktirilmiş sayılırdı. Sınama koşuları
        # (`--gun`) bu yüzden o günün sonunu görür.
        simdi = min(dt.datetime.now(dt.timezone.utc),
                    dt.datetime.combine(gun, dt.time(23, 59), dt.timezone.utc))
    satirlar = olc(kok, gun, simdi)
    alarm = [s for s in satirlar
             if s["sinif"] == "alarm" and s["yayin"] in ALARM_KAPSAMI]
    bilinen = set((alarm_kaydi_oku(kayit).get("kayitlar") or {}).keys()) if kayit else set()
    yeni = [s for s in alarm if _alarm_anahtari(s) not in bilinen]

    kapsam_disi = [s["yayin"] for s in satirlar
                   if s["sinif"] == "alarm" and s["yayin"] not in ALARM_KAPSAMI]
    if yeni:
        gerekce = "; ".join(
            f"{s['yayin']}: söz {_an(s['soz']).strftime('%H:%M')}Z, "
            f"{_sayi(s['gecikme_dk'])} dk gecikme (pay {s['pay_dk']} dk), "
            f"darboğaz {s['darbogaz'] or '—'}" for s in yeni)
    elif alarm:
        gerekce = "alarm var ama bu gün için zaten bildirilmiş — mükerrer e-posta yok"
    elif kapsam_disi:
        gerekce = ("alarm yalnız kayıt tutulan yayınlarda: "
                   + ", ".join(sorted(set(kapsam_disi)))
                   + " — eşiği ölçülmediği için e-posta gönderilmiyor")
    elif satirlar:
        gerekce = "gecikme yok ya da pay içinde"
    else:
        gerekce = "yayın günü değil"
    return {"gun": gun.isoformat(), "satirlar": satirlar, "alarm": alarm,
            "yeni": yeni, "gerekce": gerekce, "kapsam_disi": sorted(set(kapsam_disi))}


# ── rapor ────────────────────────────────────────────────────────────────────

_ISARET = {"zamaninda": "✓", "uyari": "!", "alarm": "✗"}


def rapor(satirlar: list[dict]) -> str:
    if not satirlar:
        return "  (yayın günü değil — takvimde bugüne ait yayın yok)"
    cikti = []
    for s in satirlar:
        soz_ist = (_an(s["soz"]) + dt.timedelta(hours=TR_SAAT)).strftime("%H:%M")
        yazi = _an(s["ilk_yazi"])
        yazi_ist = (yazi + dt.timedelta(hours=TR_SAAT)).strftime("%H:%M") if yazi else "—"
        cikti.append(
            f"  {_ISARET.get(s['sinif'], '?')} {s['tarih']} · {s['yayin']:24s} "
            f"söz {soz_ist} · yazı {yazi_ist} · "
            f"{_sayi(s['gecikme_dk'])} dk · pay {s['pay_dk']} dk · "
            f"{s['sinif']}" + (f" · darboğaz: {s['darbogaz']}" if s['darbogaz'] else ""))
        if s["alt_sinir"]:
            cikti.append(f"      ↳ ALT SINIR — {s['olculmedi']}")
        elif s["olculmedi"]:
            cikti.append(f"      ↳ ölçülmedi — {s['olculmedi']}")
    return "\n".join(cikti)


def gecmis(kok: Path) -> list[dict]:
    """Kayıtlı bütün günleri yeniden oynat — eşik SINANABİLİR olsun diye."""
    kok = Path(kok)
    gunler = set()
    for alt in ("bulten", "teknik"):
        d = kok / "site" / "src" / "data" / alt
        if d.exists():
            for f in d.glob("*.json"):
                try:
                    gunler.add(dt.date.fromisoformat(f.stem))
                except ValueError:
                    continue
    satirlar = []
    for g in sorted(gunler):
        # Geçmiş bir gün için "şimdi" o günün sonudur: o günü bugünün saatiyle
        # ölçmek, yazılmamış eski bir bülteni bugüne kadar geciktirmiş sayardı.
        satirlar += olc(kok, g, dt.datetime.combine(g, dt.time(23, 59),
                                                    dt.timezone.utc))
    return satirlar


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gun", default=None, help="YYYY-MM-DD (varsayılan: bugün)")
    ap.add_argument("--gecmis", action="store_true",
                    help="kayıtlı bütün günleri yeniden oynat")
    ap.add_argument("--alarm", action="store_true",
                    help="kapsamdaki YENİ bir alarm varsa çıkış kodu 1 (yalnız "
                         "bildirim kanalı için; yayının önünde DURMAZ)")
    ap.add_argument("--kayit", default=None,
                    help="mükerrerlik kaydı dosyası (verilmezse bulten/"
                         "gecikme_alarm_kaydi.json; 'yok' derse kayıt kullanılmaz)")
    ap.add_argument("--kaydi-yaz", action="store_true",
                    help="yeni alarmları kayda işle (kanal ÖNCE bunu yapar, "
                         "sonra düşer — tersi her uyanmada mükerrer alarm demek)")
    ap.add_argument("--cikti", default=None,
                    help="makine okunur karar dosyası (key=value satırları; "
                         "iş akışı adım çıktısı için)")
    a = ap.parse_args()

    kayit: Path | None = None
    if a.kayit != "yok":
        kayit = Path(a.kayit) if a.kayit else ALARM_KAYDI

    karar = None
    if a.gecmis:
        satirlar = gecmis(KOK)
    else:
        gun = dt.date.fromisoformat(a.gun) if a.gun else dt.date.today()
        karar = alarm_karari(KOK, gun, kayit)
        satirlar = karar["satirlar"]

    print("═" * 74)
    print("  YAYIN GECİKMESİ · söz (yayın takviminden) ↔ gerçekleşen")
    print("═" * 74)
    print(rapor(satirlar))
    var, gerekce = tekrar()
    print(f"\n  Tekrar koşulu: {'TUTUYOR' if var else 'tutmuyor'} — {gerekce}")

    if karar is None:
        return 0

    print(f"  Bildirim kanalı: {karar['gerekce']}")
    if karar["yeni"] and a.kaydi_yaz:
        alarm_kaydi_yaz(kayit, karar["yeni"])
        print(f"  Alarm kaydı işlendi ({kayit}).")
    if a.cikti:
        ozet = karar["gerekce"].replace("\n", " ")
        Path(a.cikti).parent.mkdir(parents=True, exist_ok=True)
        with Path(a.cikti).open("a", encoding="utf-8") as f:
            f.write(f"gun={karar['gun']}\n")
            f.write(f"alarm={'1' if karar['alarm'] else '0'}\n")
            f.write(f"yeni={'1' if karar['yeni'] else '0'}\n")
            f.write(f"ozet={ozet}\n")
    if a.alarm and karar["yeni"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
