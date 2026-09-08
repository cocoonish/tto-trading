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
    # BİR HAT BİRDEN ÇOK KURUMDAN BESLENEBİLİR. `kalip`/`kurum` çifti tek bir
    # (regex, kurum) tarifi taşıyor ve bu, farklı kurumlardan gelen serileri tek
    # regex'e sıkıştırmayı zorunlu kılıyordu — ya da (butce'de olduğu gibi)
    # ikinci kaynağı yazmamayı. Ölçüldü (07.09.2026): butce hattı aylık HMB
    # serilerinin yanında HAFTALIK bir DİBS/eurobond ailesi de taşıyor
    # (`_tarih2`, hattın kendi toleransı 12 gün) ve onu besleyen "Menkul Kıymet
    # İstatistikleri" (TCMB, Perşembe) tarifte HİÇ yoktu: haftalık bir ailenin
    # tek koruması 45 günlük emniyet ağıydı.
    # Kurumu kalıptan ayrı tutmak ŞART: takvimde HMB'nin de adı "…Menkul Kıymet
    # İstatistikleri" ile biten bir serisi var (Kamu Haznedarlığı) ve kurum
    # süzgeci gevşetilseydi butce'yi gereksiz yere tetiklerdi.
    #
    # ÜÇÜNCÜ BACAK: yayımın İLERLETTİĞİ SAAT (ozet.json anahtarı). Ek kaynak
    # hattın ANA saatini değil bir yan bacağını besler — butce'de haftalık
    # yayım `_tarih2`yi ilerletir, `_tarih` aylık kalır. Sürüm ölçüsü yalnız
    # ana saate bakarsa haftalık tetik her hafta "veri gelmedi" sayar ve dört
    # pencerede yanlış alarma varır (08.09.2026'da tam bu sınıftan bir yanlış
    # alarm türev hatlarda ölçüldü). Ölçü bu yüzden ana saat + ek kaynakların
    # ilan ettiği saatlerden kurulur (`hat_surumu`).
    ek_kaynaklar: tuple[tuple[str, tuple[str, ...], str], ...] = ()
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
    # Orta Vadeli Program hattının CANLI bacağı kurdur: program tabloları
    # yayımlanmış bir belgenin sabitleri, ama "programın tutması için yıl
    # sonunda kur kaç olmalı" sorusunun cevabı her yeni kotasyonla değişiyor.
    # Tetiği kur yayımına bağlamanın sebebi bu; tetiği olmayan bir hat
    # takvimde hiç geçmez ve HER koşuda gereksiz yere ağa çıkar.
    Tetik("ovp", "TCMB gösterge niteliğindeki kurlar (her iş günü 15:30)",
          r"Gösterge Niteliğindeki Merkez Bankası Kurları", ("TCMB",),
          en_gec=6, gecikme_dk=30),
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
    # Hat İKİ kurumdan besleniyor: aylık bütçe/borç serileri HMB'den, haftalık
    # DİBS/eurobond ailesi TCMB'nin Menkul Kıymet İstatistikleri'nden. İkincisi
    # 07.09.2026'ya kadar tarifte yoktu ve haftalık bacak (ozet `_tarih2`,
    # hattın kendi toleransı 12 gün — Butce/veri.py) yalnız 45 günlük emniyet
    # ağıyla korunuyordu; o gün 17 gün geride ölçüldü. Yan kazanç: haftalık
    # tetik eklenince AYLIK bacak da her perşembe yoklanıyor, yani hattın
    # tetiksiz kör penceresi 18 günden ≤7 güne iniyor.
    Tetik("butce", "Merkezi Yönetim Bütçe Denge Tablosu + Borç Stoku (HMB) "
                   "+ Menkul Kıymet İstatistikleri (TCMB, haftalık)",
          r"Merkezi Yönetim Bütçe Denge Tablosu|Merkezi Yönetim Borç Stoku"
          r"|Bütçe Finansmanı İstatistikleri|Merkezi Yönetim İç Borç", ("HMB",), en_gec=45,
          # Kalıp BAŞTAN SONA bağlı: HMB'nin "Kamu Haznedarlığı İstatistikleri
          # (… Mevduat ve Menkul Kıymet İstatistikleri)" serisi kurum süzgeciyle
          # zaten eleniyor, ama serbest bir alt dizge eşleşmesi ileride başka bir
          # TCMB serisinde yanlış tetik açabilirdi.
          ek_kaynaklar=((r"^\s*Menkul Kıymet İstatistikleri\s*$", ("TCMB",), "_tarih2"),)),
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


# Sütun ADIYLA sorulur. Eski süzgeç "adında 'tarih' geçen her sütun" diyordu ve
# dosyada ÜÇ sütun birden geçiyor: "İhale Tarihi" (asıl olan), "İtfa Tarihi"
# (senedin vadesi — 2028–2034) ve "Son İhale Tarihi" (kıyas bazının geçmişi).
# Ölçüldü (07.09.2026): üretilen 20 günün 12'si (%60) ihale günü DEĞİLDİ. Bugün
# sahte tetik sayısı sıfır — kirli tarihlerin en yenisi damgadan eski — ama itfa
# günleri 13.09.2028'den itibaren GERÇEK tetiğe döner ve gerekçe metni okura
# "Hazine ihalesi 13.09.2028" diye yazılırdı.
IHALE_SUTUNU = "İhale Tarihi"
# Geleceğe ufuk: strateji üç ayı kapsıyor, ondan uzağı bu dosyada plan değil
# ARTIK olur. Sınır bir eşik değil, dosyanın kendi sözleşmesinin süresi.
IHALE_UFUK_GUN = 120


def _ihale_gunleri(bugun: dt.date | None = None) -> list[dt.date]:
    """Hazine'nin planlanan ihale tarihleri — hattın kendi çıktısından.

    Döner: yalnız `İhale Tarihi` sütunundaki, bugünden ufuk kadar ileriye dek
    olan günler. Sütun yoksa dosyanın GERÇEK sütun adları uyarıya yazılır —
    "bulunamadı" deyip neyin bulunabileceğini söylememek, her düzeltme için ayrı
    bir keşif koşusu demektir (CLAUDE.md)."""
    if not IHALE_CSV.exists():
        return []
    bugun = bugun or _simdi().date()
    ufuk = bugun + dt.timedelta(days=IHALE_UFUK_GUN)
    gunler: list[dt.date] = []
    with IHALE_CSV.open(encoding="utf-8-sig", newline="") as f:
        okuyucu = csv.DictReader(f)
        sutunlar = [s for s in (okuyucu.fieldnames or []) if s]
        if IHALE_SUTUNU not in sutunlar:
            print(f"  [uyarı] {IHALE_CSV.name}: '{IHALE_SUTUNU}' sütunu yok; "
                  f"dosyadaki sütunlar: {sutunlar}")
            return []
        for satir in okuyucu:
            deger = satir.get(IHALE_SUTUNU)
            if not deger:
                continue
            for kalip in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
                try:
                    g = dt.datetime.strptime(str(deger)[:10], kalip).date()
                except ValueError:
                    continue
                # Geçmiş ihaleler tetik üretmez (damga zaten geçmiş), gelecekteki
                # ufkun ötesi de plan değil artık.
                if g <= ufuk:
                    gunler.append(g)
                break
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
#
# BİR TETİK, VERİ İLERLEMEDİYSE TÜKETİLMİŞ SAYILMAZ.
#
# Defter eskiden tek şey biliyordu: hat en son ne zaman KOŞTU. Karar da ona
# bakıyordu — "son koşumdan sonra bir yayım oldu mu". İkisinin arasında sessiz
# bir varsayım var: hat koştuysa veriyi almıştır. `guncelle.py`nin damga
# satırındaki yorum bu varsayımı zaten reddediyordu ("'koştu sayıldı ama veri
# gelmedi' durumu oluşmasın") ama yalnız DÜŞEN koşu için: başarıyla biten ama
# ELİ BOŞ dönen koşu damgayı yine de alıyordu.
#
# 03.09.2026'da kredi hattı tam bunu yaptı. Haftalık Para ve Banka
# İstatistikleri perşembe 14:30'da duyuruldu, hat 16:28 ve 19:12'de koştu,
# ikisinde de 21.08 haftasıyla döndü ve damgayı aldı. Kaynak veriyi geç
# düşürdü — aynı yayımdan beslenen YP mevduatı hattı 06.09'da koştuğunda 28.08
# haftasını buldu. Ama kredinin tetiği tüketilmişti: bir sonraki tetik 10.09
# perşembeydi ve emniyet ağı (11 gün) haftalık döngüden UZUN. Site yedi gün
# boyunca 17 gün eski veriyle kalacaktı, üstelik hattın kendi uyarı dosyası
# "13 gün geride (tolerans 12)" diye yazmış olmasına rağmen: ölçü vardı, onu
# okuyan yoktu.
#
# Defter artık koşunun ne getirdiğini de yazıyor: hattın site kopyasındaki veri
# SÜRÜMÜ (`son_surum`) ve o sürümü değiştirmeyen ARDIŞIK koşu sayısı
# (`deneme`). Sürüm ilerlerse sayaç sıfırlanır; ilerlemezse hat bir sonraki
# pencerede yeniden denenir — önbelleği ATLAYARAK, çünkü önbellekte duran şey
# tam da eli boş dönen koşunun cevabıdır.

# Kaç kez yeniden denenir. ÖLÇÜLMÜŞ BİR SAYI DEĞİL, TAVAN: kaynağın veriyi
# hiç düşürmediği durumda hattın her pencerede koşup durmasını engeller.
# Dört deneme, altı pencerelik günde kabaca bir günü kapsar; en pahalı hat
# (kredi, 869 sn) için toplam maliyet ~58 dakika ve ancak GERÇEKTEN geciken
# bir yayımda ödenir.
TEKRAR_HAKKI = 4
# İki deneme arasındaki en kısa süre (saat). Aynı pencerede peş peşe ateşlenen
# iki koşunun denemeleri boşa harcamasını engeller.
TEKRAR_SAAT = 2


def _defter() -> dict:
    if not DURUM.exists():
        return {}
    try:
        return json.loads(DURUM.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}


def durum_oku() -> dict[str, str]:
    """Her hattın en son BAŞARIYLA koştuğu an."""
    return _defter().get("son_kosum", {}) or {}


def surum_oku() -> dict[str, str]:
    """Her hattın son koşusunda GÖRÜLEN veri sürümü."""
    return _defter().get("son_surum", {}) or {}


def deneme_oku() -> dict[str, int]:
    """Sürümü ilerletmeden biten ardışık koşu sayısı."""
    return _defter().get("deneme", {}) or {}


def izlenen_saatler(hat: str, tarih_anahtarlari: tuple[str, ...] = ()) -> list[str]:
    """Sürüm ölçüsüne giren saat anahtarları: ana saat + tarifin ek
    kaynaklarının ilan ettiği yan saatler. Tek tanım; `hat_surumu` ve duman
    sınaması buradan okur."""
    ana = "_tarih" if (not tarih_anahtarlari or "_tarih" in tarih_anahtarlari) \
        else tarih_anahtarlari[0]
    saatler = [ana]
    t = TETIK.get(hat)
    for _kalip, _kurum, alan in (t.ek_kaynaklar if t else ()):
        if alan and alan not in saatler:
            saatler.append(alan)
    return saatler


def hat_surumu(hat: str) -> str:
    """Hattın site kopyasındaki veri sürümü — hattın İZLENEN SAATLERİ.

    Kütük tek kaynak (`guncelle.HATLAR`): slug da, hangi alanların tarih
    taşıdığı da (`tarih_anahtarlari`) orada duruyor. Burada ikinci bir liste
    tutmak, ikisinin bir gün sessizce ayrışması demek. Okunamazsa boş dizge
    döner ve sürüm kıyası HİÇ yapılmaz (uydurma kıyas, kıyas yapmamaktan
    kötüdür).

    NEDEN BÜTÜN ALANLAR DEĞİL, TEK SAAT. Bir ozet.json birden çok saat taşır ve
    çoğu hatta bunlar FARKLI RİTİMDE: kredide `_tarih` haftalık, `gun_tarih`
    günlük, `ay_tarih` aylıktır. Alanların hepsinden kurulan bir imza, günlük
    bacak her iş günü ilerlediği için HER ZAMAN değişir — yani donan haftalık
    bacak sayacı hiç artıramaz ve yeniden deneme, yazıldığı arıza için hiç
    ateşlenmezdi. En eskisini almak da işlemiyor: aylık bacak bir ay boyunca
    meşru olarak durur ve sağlıklı haftalarda boş yere dört deneme yakardı.
    Ölçü bu yüzden hattın ana saatidir — `RITIM`in denetlediği saatin ta
    kendisi (`_tarih`, yoksa kütükteki ilk alan; `tcmb` hattında `g_tarih`) —
    ARTI tarifin ek kaynaklarının ilan ettiği yan saatler (`izlenen_saatler`):
    butce'de haftalık TCMB yayımı `_tarih2`yi ilerletir, ana saat aylık kalır;
    yan saat imzaya girmezse haftalık tetik her hafta "veri gelmedi" sayar.
    İmza " · " ile birleşir; ana saat okunamazsa boş döner.

    DIŞARIDA KALAN, adıyla: izlenen saatler ilerlerken İÇİNDEKİ başka bir
    alanın donması bu ölçüye görünmez. O ayrı bir denetimin işi ve zaten var —
    `RITIM_ALAN` o alanları tek tek izliyor ve bültende "veri gecikti" olayını
    üretiyor."""
    import sys
    try:
        sys.path.insert(0, str(KOK))
        import guncelle                                        # noqa: E402
        h = next((x for x in guncelle.HATLAR if x.ad == hat), None)
        if h is None:
            return ""
        d = guncelle._ozet_tarih(h)
        if not d:
            return ""
        saatler = izlenen_saatler(hat, tuple(h.tarih_anahtarlari or ()))
        parcalar = []
        for i, a in enumerate(saatler):
            deger = str(d.get(a, "")).strip()
            if deger in ("", "None"):
                if i == 0:
                    return ""                 # ana saat okunamadı: ölçü yok
                continue                      # yan saat bugün yoksa imzaya girmez
            parcalar.append(deger)
        return " · ".join(parcalar)
    except Exception:                                          # noqa: BLE001
        return ""


def durum_yaz(hatlar: list[str], simdi: dt.datetime | None = None,
              sayilan: "set[str] | frozenset[str]" = frozenset()):
    """Başarıyla koşan hatların damgasını güncelle (başarısızlar dokunulmaz).

    Damgayla birlikte koşunun NE GETİRDİĞİ de yazılır; kararı asıl o belirler.

    `sayilan`: bu koşuda sürüm SAYACINA GİREN hatlar — yani koşusu bir yayım
    tetiğinden ya da onun yeniden denemesinden doğanlar (`Karar.sayilir`).
    Sayaç "kaynak yayımladı, veri gelmedi" ölçüsüdür ve ancak kaynağın
    yayımladığı bilinen bir koşuda anlam taşır. 08.09.2026'da ölçüldü: sayaç
    her başarılı koşuda artıyordu ve türev hatlar (makro · carry · tufex) her
    pencerede koşup haftalık saatlerini ilerletemediği için günde altı kez
    sayılıp aynı gün alarma düştü — alarm kanalı on dört kez öttü, duman
    sınaması canlı defteri okuyup düştü ve veri tazeleme üç pencere atlandı.
    Üç kural birden:
      · tarifi olmayan hat (TETIK'te yok) sayaçtan ve sürüm defterinden
        SİLİNİR — saati üst hattan gelir, ölçü ona uygulanamaz;
      · sürüm değiştiyse sayaç sıfırlanır (kim koşturmuş olsun);
      · sürüm değişmediyse sayaç yalnız SAYILAN koşuda artar; emniyet ağı,
        elle koşu, ölü kalıp ya da kör koşu sayacı olduğu yerde bırakır."""
    simdi = simdi or _simdi()
    defter = _defter()
    d = dict(defter.get("son_kosum", {}) or {})
    s = dict(defter.get("son_surum", {}) or {})
    n = dict(defter.get("deneme", {}) or {})
    for h in hatlar:
        d[h] = simdi.isoformat(timespec="seconds")
        if h not in TETIK:
            s.pop(h, None); n.pop(h, None)
            continue
        yeni_surum = hat_surumu(h)
        if not yeni_surum:
            # Sürüm okunamadı: sayacı ne artır ne sıfırla. Ölçülemeyen bir şeye
            # göre karar vermek, ölçülmüş gibi davranmaktır.
            continue
        if yeni_surum != s.get(h, ""):
            s[h] = yeni_surum
            n[h] = 0
        elif h in sayilan:
            n[h] = int(n.get(h, 0)) + 1
        else:
            n.setdefault(h, 0)
    DURUM.write_text(
        json.dumps({"aciklama": "Her veri hattının en son başarıyla tazelendiği an, "
                                "o koşuda görülen veri sürümü ve sürümü ilerletmeden "
                                "biten ardışık koşu sayısı. tazeleme.py bunu okuyup "
                                "hangi hattın koşacağına karar verir.",
                    "son_kosum": dict(sorted(d.items())),
                    "son_surum": dict(sorted(s.items())),
                    "deneme": dict(sorted(n.items()))},
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ── karar ────────────────────────────────────────────────────────────────────

@dataclass
class Karar:
    hat: str
    kossun: bool
    sebep: str
    tetikleyen: list[str] = field(default_factory=list)
    # Bu koşuda seri önbelleği ATLANSIN mı. Yalnız YENİDEN DENEME'de açılır:
    # hat eli boş döndüyse, önbellekte duran şey tam da o boş cevaptır ve
    # onu okuyan bir "yeniden deneme" hiçbir şeyi yeniden denemez.
    yenile: bool = False
    # Bu koşu SÜRÜM SAYACINA girer mi. Yalnız yayım tetikli koşu ve onun
    # yeniden denemesi: sayaç "kaynak yayımladı, veri gelmedi" ölçer ve
    # kaynağın yayımladığı bilinmeyen bir koşuda (emniyet ağı, elle, tarifi
    # yok, ölü kalıp, kör koşu) artması yanlış alarmdır (bkz. durum_yaz).
    sayilir: bool = False


def kararlar(hatlar: list[str] | None = None,
             simdi: dt.datetime | None = None,
             zorla: bool = False) -> list[Karar]:
    """Her hat için 'koşsun mu' kararı ve gerekçesi."""
    simdi = simdi or _simdi()
    hatlar = hatlar or [t.hat for t in TETIKLER]
    durum = durum_oku()
    surum = surum_oku()
    deneme = deneme_oku()
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
        for kalip, kurum, _alan in t.ek_kaynaklar:
            for k in yayim:
                if kurum and k["kurum"] not in kurum:
                    continue
                if not re.search(kalip, k["adi"], re.I):
                    continue
                an = _an(k["an"])
                if an is None:
                    continue
                if son < an + dt.timedelta(minutes=t.gecikme_dk) <= simdi:
                    tetikleyen.append(f"{k['adi']} — {an:%d.%m %H:%M}")
        if t.kalip:
            # Kalıp takvimde HİÇ eşleşmiyorsa (kaynak seri adını değiştirmiş
            # olabilir) hat sessizce emniyet ağına düşer ve ayda birkaç koşuya
            # iner — kimse fark etmez. Tarih süzgeci olmadan eşleşme sayılıp
            # sıfırsa bu ayrı bir gerekçeyle bildirilir.
            eslesme = sum(1 for k in yayim
                          if (not t.kurum or k["kurum"] in t.kurum)
                          and re.search(t.kalip, k["adi"], re.I))
            if eslesme == 0:
                # KOŞSUN=True BİLİNÇLİ: ölü kalıp hattı emniyet ağına DÜŞÜRMEZ,
                # HER PENCEREDE koşturur. Maliyeti ölçülü (hafta içi altı
                # pencere × en pahalı hat 869 sn ≈ 87 dk/gün) ve bilerek
                # ödeniyor — bayat bir pano, yanmış bir koşucu dakikasından
                # pahalıdır. Gerekçe metni bu yüzden ADIYLA yazıyor;
                # `denetim.olu_kalip` ölçütü de aynı listeyi bültende uyarı
                # olarak basıyor ki durum sessiz kalmasın.
                cikti.append(Karar(ad, True,
                                   "KALIP ÖLÜ — takvimde bu tarife uyan seri yok "
                                   "(kaynak seri adını değiştirmiş olabilir); "
                                   "hat her pencerede koşuyor"))
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
            cikti.append(Karar(ad, True, f"{len(tetikleyen)} yeni yayım", tetikleyen,
                               sayilir=True))
            continue

        # YENİDEN DENEME. Buraya gelmek "son koşumdan bu yana yeni yayım yok"
        # demek — ama son koşu VERİYİ İLERLETTİYSE. İlerletmediyse tetik
        # tüketilmiş sayılmaz: kaynak yayımı geç düşürmüş olabilir ve bir
        # sonraki tetiği beklemek, haftalık bir seride yedi gün bayat sayfa
        # demektir (03.09.2026, kredi hattı).
        kalan_hak = TEKRAR_HAKKI - int(deneme.get(ad, 0))
        gecen_saat = (simdi - son).total_seconds() / 3600
        if deneme.get(ad, 0) and kalan_hak > 0 and gecen_saat >= TEKRAR_SAAT:
            cikti.append(Karar(
                ad, True,
                f"önceki koşu veriyi ilerletmedi ({surum.get(ad, '?')}) — "
                f"yeniden deneniyor ({int(deneme[ad])}/{TEKRAR_HAKKI}), "
                f"önbellek atlanıyor",
                yenile=True, sayilir=True))
            continue

        # Hakkı bitmiş bir hat SESSİZCE beklemez: gerekçe adıyla yazılır,
        # yoksa "yeni yayım yok" satırı sağlıklı bir bekleyişle aynı görünür.
        if deneme.get(ad, 0) >= TEKRAR_HAKKI:
            cikti.append(Karar(ad, False,
                               f"veri {int(deneme[ad])} koşudur ilerlemedi "
                               f"({surum.get(ad, '?')}); yeniden deneme hakkı doldu — "
                               f"sıradaki yayım ya da emniyet ağı bekleniyor"))
            continue

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
    yanlış yazılır ve hiçbir şey patlamaz.

    BELGE BİR ZAMANLAR KODUN TERSİNİ ANLATIYORDU (07.09.2026'da düzeltildi):
    burada ve `kararlar()`da "hat sessizce emniyet ağına düşer, `en_gec` günde
    bir koşar" yazıyordu. Kod bunun TERSİNİ yapıyor — `eslesme == 0` dalı
    `kossun=True` veriyor, yani ölü kalıplı hat HER PENCEREDE koşuyor. Maliyet
    ölçülü: hafta içi altı pencere × en pahalı hat 869 sn ≈ 87 dk/gün, yorumların
    vaat ettiği "on bir günde bir" değil. Aynı dosyadaki reelfx yorumu doğrusunu
    yazıyordu ("hattı HER koşuda EVDS'e gönderirdi"); iki yorum birbiriyle
    çelişiyordu ve kimse ikisini yan yana okumamıştı.

    Onun için kalıplar her koşuda takvime karşı sınanır ve tutmayan varsa yüksek
    sesle söylenir — `denetim.olu_kalip` ölçütü bunu bültende UYARI olarak
    basar (ENGEL değil: takvim ucu düştüğünde bu fonksiyon zaten boş liste
    döndürüyor, yani yanlış alarm riski yapısal olarak yok).

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
        for kalip, kurum, _alan in t.ek_kaynaklar:
            if not any((not kurum or k["kurum"] in kurum)
                       and re.search(kalip, k["adi"], re.I) for k in yayim):
                olu.append((t.hat, kalip))
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
