"""Hangi veri hattı ne zaman tazelenecek — kararı resmî yayım takvimi verir.

Eski davranış: bülten her koştuğunda on bir hattın hepsi baştan çekiliyordu.
Bulutta önbellek olmadığı için bu 37 dakika sürüyordu ve enflasyon gibi ayda bir
yayımlanan bir seriyi günde iki kez indirmek tamamen boşa gidiyordu.

Yeni davranış: her hattın *kaynağı* belli bir takvimde yayımlanır. TÜİK'in
Ulusal Veri Yayımlama Takvimi TCMB/TÜİK/HMB/BDDK/SPK serilerinin yayım anını
dakikasına kadar verir. Bir hat, ancak beslendiği seri son tazelemeden bu yana
yayımlandıysa koşar. Yayım yoksa hat atlanır — çekilecek yeni veri yoktur.

Üç tetik kaynağı:
  1. Ulusal takvim  — TCMB/TÜİK/HMB serileri (aşağıdaki KALIP'larla eşleşir)
  2. Hazine ihale planı — ulusal takvimde ihaleler yok, hattın kendi CSV'sinden
  3. Emniyet ağı  — takvim susarsa (seri adı değişti, kaynak düştü) `en_gec`
     günden fazla bekleyen hat yine de koşar. Sessiz bayatlamaya karşı sigorta.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import re
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from takvim import ONBELLEK, TUIK_UC, _getir, _onbellege_yaz, _onbellekten

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent
DURUM = BURASI / "tazeleme_durumu.json"
ONBELLEK_SAAT = 4          # ulusal takvim önbelleğinin ömrü
# Takvim ucunun zaman aşımı (sn). ÇAĞIRANA GÖRE DEĞİŞİR: tazeleme koşusunda
# bekleyecek vakit var, ama `denetim.tazeleme_atlandi` aynı ölçüyü YAZI
# KATMANININ kritik yolunda soruyor ve orada çöken bir ağ, bültenin
# yazılmasını dakikalarca geciktirmemeli — düzeltilmeye çalışılan şeyin ta
# kendisi olurdu. Kısa tavan `zaman_asimi()` bağlamıyla dayatılır; imza
# değiştirilmiyor çünkü `_yayimlar` birkaç sınamada tek argümanlı bir sahteyle
# değiştiriliyor ve yeni bir parametre onları sessizce düşürürdü.
TAKVIM_ZAMAN_ASIMI = 25
IHALE_CSV = KOK / "Aktarılacak Projeler" / "hazineihrac" / "hazine_planlanan_ihaleler.csv"
# Strateji duyurusunun beklendiği saat (TR). HMB duyuruyu ayın son iş günü
# mesai bitimine doğru yayımlıyor; erken bakmak boş koşu, geç bakmak bayat
# takvim demek. İkinci şans ertesi iş günü aynı saatte.
STRATEJI_SAATI = (17, 30)

# Ulusal takvim yayım anlarını TÜRKİYE saatiyle verir; bulut koşucusu UTC'de
# çalışır. İkisi karşılaştırılırken saat dilimi sabitlenmezse 14:30'da duyurulan
# seri, bulutta üç saat boyunca "henüz yayımlanmadı" görünür ve hat atlanır.
# Bu yüzden "şimdi" her yerde Türkiye saatidir.
TR = dt.timezone(dt.timedelta(hours=3))


def _simdi() -> dt.datetime:
    """Türkiye saatiyle şimdi (saat dilimi bilgisi taşımayan biçimde)."""
    return dt.datetime.now(TR).replace(tzinfo=None)


@dataclass(frozen=True)
class Tetik:
    """Bir veri hattının ne zaman tazelenmesi gerektiğinin tarifi."""

    hat: str
    besleyen: str                       # insan dili: hattı besleyen yayım
    kalip: str = ""                     # ulusal takvimdeki seri adı (regex)
    kurum: tuple[str, ...] = ()         # sorumlu kurum süzgeci (aynı adlı seriler için)
    en_gec: int = 30                    # emniyet ağı: bu kadar gün sonra takvimsiz koş
    gecikme_dk: int = 45                # yayım anı ile verinin API'ye düşmesi arası
    ihale: bool = False                 # Hazine ihale planından da tetiklensin mi
    strateji: bool = False              # Hazine'nin aylık İç Borçlanma Stratejisi'nden de


# Kalıplar, takvimde GERÇEKTEN bulunan seri adlarından türetildi; uydurma kalıp
# hiç tetiklenmez ve hattı emniyet ağına düşürür (yani sessizce yavaşlatır).
TETIKLER: tuple[Tetik, ...] = (
    Tetik("usdtry", "TCMB gösterge niteliğindeki kurlar (her iş günü 15:30)",
          r"Gösterge Niteliğindeki Merkez Bankası Kurları", ("TCMB",), en_gec=4, gecikme_dk=30),
    Tetik("dibs", "TCMB gösterge kurlar + DİBS getirileri (her iş günü)",
          r"Gösterge Niteliğindeki Merkez Bankası Kurları", ("TCMB",), en_gec=6, gecikme_dk=30),
    Tetik("fonlama", "TCMB Analitik Bilanço (her iş günü 14:30)",
          r"TCMB Analitik Bilanço", ("TCMB",), en_gec=6, gecikme_dk=45),
    # Net rezerv hattının GÜNLÜK serisi tamamen Analitik Bilanço'dan üretilir
    # (TP.AB.A02/A11/A13/A14 — bkz. net_rezerv.py). O yayım burada tetik değilse
    # hat yalnız haftalık yayımda koşar ve günlük seri, her iş günü 14:30'da yeni
    # bilanço düşmesine rağmen Perşembeye kadar donuk kalır. Haftalık tetikler
    # (IRFCL + haftalık para-banka) h_* alanlarını besler; ikisi de gerekli.
    Tetik("tcmb", "TCMB Analitik Bilanço (günlük) + IRFCL ve haftalık para-banka",
          r"TCMB Analitik Bilanço|Uluslararası Rezervler ve Döviz Likiditesi"
          r"|Haftalık Para ve Banka İstatistikleri",
          ("TCMB",), en_gec=6, gecikme_dk=45),
    Tetik("kredi", "Haftalık ve Aylık Para ve Banka İstatistikleri (Perşembe 14:30)",
          r"(Haftalık|Aylık) Para ve Banka İstatistikleri", ("TCMB",), en_gec=11),
    # YP mevduatı hattı kredi ile AYNI yayımdan besleniyor (haftalık para ve
    # banka istatistikleri, perşembe 14:30) ama AYRI tablolardan: stok, stok
    # kırılımı ve resmî parite ayrıştırması. Tetik tarifi olmayan bir hat
    # tazeleme takviminde hiç geçmez ve her koşuda gereksiz yere ağa çıkar.
    Tetik("ypmevduat", "Haftalık Para ve Banka İstatistikleri (Perşembe 14:30)",
          r"Haftalık Para ve Banka İstatistikleri", ("TCMB",), en_gec=11),
    Tetik("yabanci", "TCMB Menkul Kıymet İstatistikleri (Perşembe)",
          r"Menkul Kıymet İstatistikleri", ("TCMB",), en_gec=11),
    Tetik("enflasyon", "TÜFE / Yİ-ÜFE ve alt endeksler (ayın ilk iş günleri)",
          r"Tüketici Fiyat Endeksi|Yurt İçi Üretici Fiyat Endeksi|Hizmet Üretici Fiyat Endeksi",
          ("TÜİK",), en_gec=40, gecikme_dk=90),
    Tetik("marj", "TÜFE ve Hizmet ÜFE alt kalemleri",
          r"Tüketici Fiyat Endeksi|Hizmet Üretici Fiyat Endeksi", ("TÜİK",),
          en_gec=45, gecikme_dk=90),
    Tetik("reer", "TCMB Reel Efektif Döviz Kuru (aylık)",
          r"Reel Efektif Döviz Kuru", ("TCMB",), en_gec=40),
    Tetik("odemeler", "Ödemeler Dengesi + Kısa Vadeli Dış Borç + UYP",
          r"Ödemeler Dengesi İstatistikleri|Kısa Vadeli Dış Borç İstatistikleri"
          r"|Uluslararası Yatırım Pozisyonu", ("TCMB",), en_gec=45),
    Tetik("butce", "Merkezi Yönetim Bütçe Denge Tablosu + Borç Stoku",
          r"Merkezi Yönetim Bütçe Denge Tablosu|Merkezi Yönetim Borç Stoku"
          r"|Bütçe Finansmanı İstatistikleri|Merkezi Yönetim İç Borç", ("HMB",), en_gec=45),
    # Hazine ihaleleri ulusal takvimde yok: hattın kendi ihale planından sürülür.
    # İki ayrı tetik kaynağı, çünkü iki ayrı olay var. İHALE günü sonucu
    # (miktar, faiz, teklif) getirir; STRATEJİ günü önümüzdeki üç ayın
    # takvimini ve aylık borçlanma hedeflerini DEĞİŞTİRİR. Yalnız ihale
    # tetiği varken strateji günü hattı koşturmuyordu: yeni takvim ancak bir
    # sonraki ihaleye kadar görünmüyor, sayfadaki "planlanan ihraçlar" tablosu
    # ve hedefler o zamana dek eski stratejiyi gösteriyordu.
    Tetik("hazine", "Hazine iç borçlanma ihaleleri + aylık İç Borçlanma Stratejisi",
          en_gec=12, ihale=True, strateji=True),
    # GSYH üç aylık ve TÜİK yayımı ~60 gün gecikmeli; emniyet ağı bir çeyreği
    # aşacak kadar uzun (100 gün) çünkü takvim kaydı okunamazsa hattın bir
    # sonraki yayıma kadar beklemesi gerekir, boşuna koşması değil.
    Tetik("buyume", "TÜİK Dönemsel Gayrisafi Yurt İçi Hasıla (üç aylık)",
          r"Gayrisafi Yurt İçi Hasıla", ("TÜİK",), en_gec=100, gecikme_dk=90),
    # El Niño hattının yerli kanadı TÜFE ile ilerler; küresel kanat (ONI) aylık
    # ve takvimsiz — TÜFE günü ikisi birden yoklanır, emniyet ağı bir ayı aşar.
    Tetik("elnino", "NOAA ONI (aylık, takvimsiz) + TÜFE yayımı",
          r"Tüketici Fiyat Endeksi", ("TÜİK",), en_gec=35, gecikme_dk=90),
    # GDELT haber akışı sürekli; resmî yayım takvimi yok, haftalık ritim yeter.
    Tetik("fx", "GDELT haber akışı (resmî takvimi yok, haftalık ritim)", en_gec=9),
    # TÜREV HATLAR (carry, tufex, makro) BİLEREK tarifsiz: kendi kaynaklarına
    # gitmezler, üst hatların depoya yazdığı CSV'lerden saniyeler içinde
    # hesaplanırlar ve kararlar() tarifsiz hattı her koşuda koşturur. Üst
    # hattın tetiğine bağlanmaları yanlış olurdu: üst hat düşüp bir sonraki
    # koşuda kurtulursa türev hattın damgası tetiği geçmiş sayar ve sayfa bir
    # gün bayat kalır.
    # Reel sektör döviz pozisyonu: TCMB, aylık, ~2 ay gecikmeli. BİLEREK
    # KALIPSIZ (fx gibi, yalnız emniyet ağı): yayımın takvimdeki adı bu
    # koşucudan doğrulanamadı ve ölü bir kalıp "KALIP ÖLÜ" ile hattı HER koşuda
    # EVDS'e gönderirdi — aylık bir seri için haftada 31 çekim. 30 günde bir
    # koşar; ad doğrulandığında kalıp yazılır ve hat yayım gününe bağlanır.
    Tetik("reelfx", "TCMB finansal kesim dışındaki firmaların döviz varlık ve "
                    "yükümlülükleri (aylık, ~2 ay gecikmeli; takvimsiz, 30 günde bir)",
          en_gec=30),
)

TETIK = {t.hat: t for t in TETIKLER}

# KÖR KOŞU İMZASI. Takvim ucu okunamadığında her hat "gerekli" sayılır ve
# gerekçesi bu dizgeyle başlar. Metni okuyan ikinci bir yer var (denetim.py'nin
# `tazeleme_atlandi` ölçütü hat hat 17 satır patlatmak yerine tek satıra iner);
# iki ayrı yere yazılmış aynı dizge bir gün sessizce ayrışır, bu yüzden TEK
# tanım burada durur.
KOR_KOSU = "TAKVİM ALINAMADI"


# ── ulusal takvimden yayımlanmış kayıtlar ────────────────────────────────────

def _yayimlar(yillar: tuple[int, ...]) -> tuple[list[dict], bool]:
    """Ulusal takvimin YAYIMLANMIŞ kayıtları (adı, kurumu, yayım anı).

    takvim.tuik() ileriye bakar; burada geriye bakmak gerekiyor: "son
    tazelemeden bu yana ne yayımlandı?" sorusunun cevabı geçmişte.
    """
    cikti: list[dict] = []
    for yil in yillar:
        ad = f"yayim_{yil}"
        # _onbellekten (veri, yazım anı) çifti döndürür. Yayımlanmış liste her
        # iş günü büyüdüğü için süresiz önbellek yanlış cevap verir: dün çekilmiş
        # liste bugünün 14:30 yayımını içermez ve hat sonsuza dek atlanır.
        ham, yazim = _onbellekten(ad)
        taze = False
        if ham and yazim:
            try:
                taze = (dt.datetime.now() - dt.datetime.fromisoformat(yazim)
                        ) < dt.timedelta(hours=ONBELLEK_SAAT)
            except ValueError:
                taze = False
        if not taze:
            metin = _getir(TUIK_UC.format(yil=yil), TAKVIM_ZAMAN_ASIMI)
            if metin:
                try:
                    kayitlar = json.loads(metin).get("yayindaOlanlarList", [])
                except (ValueError, AttributeError):
                    kayitlar = []
                if kayitlar:
                    ham = [{"adi": (x.get("adi") or "").strip(),
                            "kurum": (x.get("sorumluKisaAd") or "").strip(),
                            "an": x.get("gTarih") or ""} for x in kayitlar]
                    _onbellege_yaz(ad, ham)
        # Kaynak düşerse bayat önbellekle devam edilir; emniyet ağı zaten
        # takvimsiz kalan hattı en_gec gününde koşturur.
        cikti += [k for k in (ham or []) if isinstance(k, dict)]
    # İkinci değer: takvim GERÇEKTEN alındı mı. Boş liste ile "kaynak düştü"
    # ayrımı şart — ayrılmazsa TÜİK ucu bir gün düştüğünde on üç hattın hepsi
    # "yeni yayım yok" gerekçesiyle atlanır ve koşu çıkış kodu 0 ile başarılı
    # görünür. Bulutta takvim önbelleği hiç olmadığı için bu senaryo uzak değil.
    return cikti, bool(cikti)


def _an(metin: str) -> dt.datetime | None:
    try:
        return dt.datetime.fromisoformat(str(metin)[:19])
    except (ValueError, TypeError):
        return None


def _is_gunu_geri(g: dt.date) -> dt.date:
    """Hafta sonuna denk gelirse bir önceki iş gününe çek."""
    while g.weekday() >= 5:
        g -= dt.timedelta(days=1)
    return g


def _is_gunu_ileri(g: dt.date) -> dt.date:
    while g.weekday() >= 5:
        g += dt.timedelta(days=1)
    return g


def _ay_son_is_gunu(yil: int, ay: int) -> dt.date:
    son = (dt.date(yil + (ay == 12), (ay % 12) + 1, 1) - dt.timedelta(days=1))
    return _is_gunu_geri(son)


def _strateji_anlari(simdi: dt.datetime) -> list[tuple[str, dt.datetime]]:
    """Hazine'nin üç aylık İç Borçlanma Stratejisi'nin yayım anları.

    Strateji ayın SON İŞ GÜNÜ akşamı yayımlanır ve ertesi günden başlayan ÜÇ
    AYIN ihraç takvimini, aylık borçlanma hedeflerini ve itfa programını
    belirler. Resmî yayım takviminde bu duyurunun kendi satırı yok, ihale
    tetiği de yakalamıyor (strateji günü bir ihale günü değildir).

    Bu ay ve önceki ay için iki an üretilir: son iş günü ve ertesi iş günü.
    İkincisi ikinci şanstır — yayım kayarsa ya da o akşamki koşu düşerse hat
    yine de ertesi gün tazelenir.
    """
    anlar: list[tuple[str, dt.datetime]] = []
    for geri in (0, 1):
        ay, yil = simdi.month - geri, simdi.year
        if ay <= 0:
            ay += 12; yil -= 1
        g = _ay_son_is_gunu(yil, ay)
        anlar.append((f"İç Borçlanma Stratejisi {g:%d.%m}",
                      dt.datetime.combine(g, dt.time(*STRATEJI_SAATI))))
        e = _is_gunu_ileri(g + dt.timedelta(days=1))
        anlar.append((f"İç Borçlanma Stratejisi {g:%d.%m} (ikinci şans)",
                      dt.datetime.combine(e, dt.time(*STRATEJI_SAATI))))
    return anlar


def _ihale_gunleri() -> list[dt.date]:
    """Hazine'nin planlanan ihale tarihleri — hattın kendi çıktısından."""
    if not IHALE_CSV.exists():
        return []
    gunler: list[dt.date] = []
    with IHALE_CSV.open(encoding="utf-8-sig", newline="") as f:
        for satir in csv.DictReader(f):
            for anahtar, deger in satir.items():
                if not anahtar or "tarih" not in anahtar.lower() or not deger:
                    continue
                for kalip in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
                    try:
                        gunler.append(dt.datetime.strptime(str(deger)[:10], kalip).date())
                        break
                    except ValueError:
                        continue
    return sorted(set(gunler))


@contextmanager
def zaman_asimi(sn: int):
    """Takvim ucuna GEÇİCİ ve kısa bir tavan koy (kritik yoldaki çağıranlar için)."""
    global TAKVIM_ZAMAN_ASIMI
    onceki = TAKVIM_ZAMAN_ASIMI
    TAKVIM_ZAMAN_ASIMI = sn
    try:
        yield
    finally:
        TAKVIM_ZAMAN_ASIMI = onceki


# ── durum defteri ────────────────────────────────────────────────────────────

def durum_oku() -> dict[str, str]:
    """Her hattın en son BAŞARIYLA koştuğu an."""
    if not DURUM.exists():
        return {}
    try:
        return json.loads(DURUM.read_text(encoding="utf-8")).get("son_kosum", {})
    except (ValueError, OSError):
        return {}


def durum_yaz(hatlar: list[str], simdi: dt.datetime | None = None):
    """Başarıyla koşan hatların damgasını güncelle (başarısızlar dokunulmaz)."""
    simdi = simdi or _simdi()
    d = durum_oku()
    for h in hatlar:
        d[h] = simdi.isoformat(timespec="seconds")
    DURUM.write_text(
        json.dumps({"aciklama": "Her veri hattının en son başarıyla tazelendiği an. "
                                "tazeleme.py bunu okuyup hangi hattın koşacağına karar verir.",
                    "son_kosum": dict(sorted(d.items()))},
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ── karar ────────────────────────────────────────────────────────────────────

@dataclass
class Karar:
    hat: str
    kossun: bool
    sebep: str
    tetikleyen: list[str] = field(default_factory=list)


def kararlar(hatlar: list[str] | None = None,
             simdi: dt.datetime | None = None,
             zorla: bool = False) -> list[Karar]:
    """Her hat için 'koşsun mu' kararı ve gerekçesi."""
    simdi = simdi or _simdi()
    hatlar = hatlar or [t.hat for t in TETIKLER]
    durum = durum_oku()
    yillar = tuple({simdi.year, (simdi - dt.timedelta(days=120)).year})
    yayim, takvim_saglam = _yayimlar(yillar)
    ihaleler = _ihale_gunleri()

    cikti: list[Karar] = []
    for ad in hatlar:
        t = TETIK.get(ad)
        if t is None:
            cikti.append(Karar(ad, True, "tazeleme takviminde tarifi yok — koşuluyor"))
            continue
        if zorla:
            cikti.append(Karar(ad, True, "elle zorlandı"))
            continue

        son = _an(durum.get(ad, "")) if durum.get(ad) else None
        if son is None:
            cikti.append(Karar(ad, True, "hiç tazelenmemiş"))
            continue
        if not takvim_saglam:
            cikti.append(Karar(ad, True, f"{KOR_KOSU} — kör koşu "
                                         "(yayım takvimi okunamadığı için hat koşuluyor)"))
            continue

        gecen = (simdi - son).days
        if gecen >= t.en_gec:
            cikti.append(Karar(ad, True,
                               f"emniyet ağı: {gecen} gündür tazelenmedi "
                               f"(sınır {t.en_gec} gün)"))
            continue

        tetikleyen: list[str] = []
        if t.kalip:
            # Kalıp takvimde HİÇ eşleşmiyorsa (kaynak seri adını değiştirmiş
            # olabilir) hat sessizce emniyet ağına düşer ve ayda birkaç koşuya
            # iner — kimse fark etmez. Tarih süzgeci olmadan eşleşme sayılıp
            # sıfırsa bu ayrı bir gerekçeyle bildirilir.
            eslesme = sum(1 for k in yayim
                          if (not t.kurum or k["kurum"] in t.kurum)
                          and re.search(t.kalip, k["adi"], re.I))
            if eslesme == 0:
                cikti.append(Karar(ad, True,
                                   "KALIP ÖLÜ — takvimde bu tarife uyan seri yok "
                                   "(kaynak seri adını değiştirmiş olabilir)"))
                continue
            for k in yayim:
                if t.kurum and k["kurum"] not in t.kurum:
                    continue
                if not re.search(t.kalip, k["adi"], re.I):
                    continue
                an = _an(k["an"])
                if an is None:
                    continue
                # Yayım anı + kaynağın API'ye düşme gecikmesi geçmiş olmalı:
                # 14:30'da duyurulan seriyi 14:31'de çekmek eski veriyi getirir.
                hazir = an + dt.timedelta(minutes=t.gecikme_dk)
                if son < hazir <= simdi:
                    tetikleyen.append(f"{k['adi']} — {an:%d.%m %H:%M}")
        if t.strateji:
            for ad_, an in _strateji_anlari(simdi):
                if son < an <= simdi:
                    tetikleyen.append(ad_)
        if t.ihale:
            for g in ihaleler:
                # İhale günü ve ertesi gün (sonuç/ödeme) tazeleme gerektirir.
                for kayma in (0, 1):
                    an = dt.datetime.combine(g + dt.timedelta(days=kayma), dt.time(18, 0))
                    if son < an <= simdi:
                        tetikleyen.append(f"Hazine ihalesi {g:%d.%m}"
                                          + (" (sonuç günü)" if kayma else ""))

        tetikleyen = sorted(set(tetikleyen))
        if tetikleyen:
            cikti.append(Karar(ad, True, f"{len(tetikleyen)} yeni yayım", tetikleyen))
        else:
            cikti.append(Karar(ad, False,
                               f"yeni yayım yok — son tazeleme {son:%d.%m %H:%M} "
                               f"({gecen} gün önce)"))
    return cikti


def gerekli(hatlar: list[str] | None = None,
            simdi: dt.datetime | None = None,
            zorla: bool = False) -> list[str]:
    return [k.hat for k in kararlar(hatlar, simdi, zorla) if k.kossun]


def olu_kaliplar(yillar: tuple[int, ...] | None = None) -> list[tuple[str, str]]:
    """Takvimde HİÇBİR yayımla eşleşmeyen tetik kalıpları.

    Bu dosyanın en sinsi hata biçimi budur: seri adı değişir ya da kalıp baştan
    yanlış yazılır, hiçbir şey patlamaz, hat sessizce emniyet ağına düşer ve
    günde bir yerine `en_gec` günde bir koşar. Kimse fark etmez — veri "biraz
    eski" görünür, o kadar. Onun için kalıplar her koşuda takvime karşı
    sınanır ve tutmayan varsa yüksek sesle söylenir.

    Takvim hiç çekilemediyse boş liste döner: kaynağın düşmesi kalıbın ölü
    olduğu anlamına gelmez, o durumda yanlış alarm vermek denetimi işe yaramaz
    kılar.
    """
    simdi = _simdi()
    yillar = yillar or tuple({simdi.year, (simdi - dt.timedelta(days=120)).year})
    # _yayimlar (kayıtlar, takvim gerçekten alındı mı) çifti döndürür. Çifti
    # açmadan dolaşmak listenin kendisini kayıt sanar — 26.08 koşusunu düşüren
    # hata buydu. `alindi` bayrağı ayrıca doğru soruyu sorar: takvim BOŞ mu
    # geldi, yoksa hiç mi alınamadı. Alınamadıysa her kalıp ölü görünür ve
    # rapor tamamen yanlış olur.
    yayim, alindi = _yayimlar(yillar)
    if not alindi:
        return []
    olu = []
    for t in TETIKLER:
        if not t.kalip:
            continue
        if not any((not t.kurum or k["kurum"] in t.kurum)
                   and re.search(t.kalip, k["adi"], re.I) for k in yayim):
            olu.append((t.hat, t.kalip))
    return olu


def rapor(hatlar: list[str] | None = None, simdi: dt.datetime | None = None) -> str:
    satir = []
    for k in kararlar(hatlar, simdi):
        isaret = "▶" if k.kossun else "·"
        satir.append(f"  {isaret} {k.hat:10s} {k.sebep}")
        for t in k.tetikleyen[:4]:
            satir.append(f"      ← {t}")
        if len(k.tetikleyen) > 4:
            satir.append(f"      ← (+{len(k.tetikleyen) - 4} yayım daha)")
    return "\n".join(satir)


if __name__ == "__main__":
    import sys
    ONBELLEK.mkdir(exist_ok=True)
    print("Tazeleme takvimi — hangi hat neden koşacak\n")
    print(rapor())
    kos = gerekli()
    print(f"\n{len(kos)}/{len(TETIKLER)} hat tazelenecek: {' '.join(kos) or '(yok)'}")
    olu = olu_kaliplar()
    if olu:
        print("\n  ! TAKVİMDE KARŞILIĞI OLMAYAN KALIP — bu hatlar yalnız emniyet "
              "ağıyla koşuyor:")
        for hat, kalip in olu:
            print(f"      {hat:10s} {kalip}")
    sys.exit(0)
