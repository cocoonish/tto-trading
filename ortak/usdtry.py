"""USD/TRY — TEK kaynak, TEK tanım: Yahoo Finance (USDTRY=X), kapsam ölçümlü.

KARAR (09.09.2026, kullanıcı): "USD/TRY her yerde Yahoo Finance olmalı."
Kurun KONU olduğu hatlar (usdtry-deval panosu, TL taşıma, OVP'nin gerçekleşen
kur bacağı, REDK regresyonu, bülten piyasa tablosu, teknik) piyasa kurunu
buradan okur. Resmî istatistiklerin DÖNÜŞÜM kuru olarak kullanılan USD/TRY
(TCMB bilançosunun dolar karşılığı, kur etkisinden arındırılmış kredi, borç
stoku, ödemeler dengesi) kapsam dışıdır: o tablolar kurumların kendi
yayımladığı gösterge kuruyla değerlenir ve başka bir kurla değerlemek
yayımlanan sayıyla çelişen bir sayı üretir.

NEDEN TEK TANIM. yfinance `USDTRY=X` bir koşucudan altı aylık ve seviyesi
yıllar geride bir seri döndürmüştü (CLAUDE.md: "veri geldi" ≠ "veri TAM
geldi") ve o gün kaynak EVDS'e çevrilmişti. Kaynak yine Yahoo; sigorta bu
kez KAPSAM ÖLÇÜMÜ: gelen serinin başı, sonu, gözlem sayısı ve seviyesi eldeki
önbellekle kıyaslanır; kapsam çıktının ihtiyacına yetmiyorsa YENİ SERİ
YAZILMAZ, eski önbellek korunur ve sebep adıyla döner. "Bir kaynak kırpmayı
söylemez" — ölçen taraf biz olmalıyız.

KAPANIŞ = İSTANBUL 18:00, SAATLİK BARDAN (02.10.2026). Yahoo'nun kapanmış
günlük döviz barında "Close" alanı günün BAŞINDAKİ fiyatı taşıyor; bu hattın
D diye bastığı her değer D−1'in gün sonuydu (02.10 sabahı gösterge şeridi
USD/TRY'yi 49,01 ile 30.09 diye bastı; 01.10'un İstanbul kapanışı 49,030,
o sabahki canlı kur 49,14). Seri artık `ortak/fx_kapanis`tan kurulur: son 730
gün saatlik bardan İstanbul 18:00 kapanışı (karar 02.10.2026, kullanıcı;
gerekçe ve ölçüm o modülün başlığında), daha eskisi düzeltilmiş günlük bardan
(Londra gece yarısı) — geçiş günü künyede (`kur_kapanis_gecis`). Önbellek
sütununun adı tanımı taşır: eski tanımla yazılmış önbellek taze sayılmaz.

CUMA (03.10.2026). Günlük bar kısmında cumartesi barı olmayan cuma ÖLÇÜLEMEZ:
cumaya yazılabilecek tek bar pazartesi barıdır ve onun başı hafta sonu
açılışından sonradır (2005'ten bu yana cumartesi barı hiç yok; ölçüm
`ortak/fx_kapanis` başlığında). O cumalar seriye girmez; sayıları künyede
(`kur_cuma_olculemeyen`), serinin sağ ucuna düşen olursa uyarıda adıyla
yazılır. Kapsam ölçüsünün paydası onları beklemez — adıyla bilinen bir boşluk
kırpılmış seri değildir. Tanım değişti, sütun adı da değişti (`usdtry_ist18_2`).

KAPANMAMIŞ BAR. Bir günün kapanışı ancak kapanış anı (İstanbul 18:00 = 15:00
UTC) geçtikten sonra vardır; o andan önce bugünün değeri seriye alınmaz (bir
ölçüm ancak KAPANMIŞ bir seansı ölçebilir).

VALÖR YOK. EVDS gösterge kuru VALÖR tarihini taşır (ertesi iş günü) ve resmî
tatil öncesinde yarından ileri bir `_tarih` üretirdi; Yahoo barı işlem
gününü taşır — hattın saati gözlem günüdür.

AĞ: birinci yol yfinance (çerez/crumb el sıkışması kütüphanede; bülten aynı
koşucudan bununla geçiyor), yedek yol çıplak chart isteği — o yol koşucudan
429 alıyor (09.09.2026 ölçüldü), yalnız yfinance kurulu değilse anlamlı.
`ortak/sitecustomize` zaman aşımı, yeniden deneme ve devre kesiciyi
kütüphanenin altına serer.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bicim as _bicim  # noqa: E402  — sayı yazımı tek sözleşmeden (ortak/bicim)
import fx_kapanis as _fx  # noqa: E402  — kapanış anının tek tanımı

SEMBOL = "USDTRY=X"
TUR = _fx.kesim_turu(SEMBOL)                       # "tr": İstanbul 18:00
# Önbellek CSV'sinin sütun adı kapanış TANIMINI taşır; adı farklı bir önbellek
# (eski tanım: günlük barın kapanış alanı) taze sayılmaz, yalnız ağ düşerse
# son çare olarak döner ve bunu uyarısında adıyla söyler.
# `_2` (03.10.2026): günlük bar kısmında cumartesi barı olmayan cuma artık
# ölçülemez sayılır. 02.10 tanımıyla yazılmış önbellekte o cumalar pazartesi
# barının başını taşıyor; o önbellek taze sayılsaydı yeni tanım TTL boyunca
# devreye girmezdi.
SUTUN = "usdtry_ist18_2"
YEDEK_SUTUN = "usdtry_gunluk_yedek_2"   # saatlik bar alınamadığı koşunun serisi (taze sayılmaz)
# 02.10.2026 tanımının sütunları: saatlik kısım bugünküyle aynı, ama saatlik
# barın ulaşmadığı geçmişte (ve yedek seride) cuma değeri pazartesi barının başı.
ONCEKI_SUTUN = "usdtry_ist18"
ONCEKI_YEDEK_SUTUN = "usdtry_gunluk_yedek"
# Eski tanımla (sütun adı başka) yazılmış önbelleğin okura giden adı: D tarihli
# değer D gününün BAŞINDAKİ fiyattır (günlük barın kapanış alanı).
ESKI_KAPANIS = "günün başı, Londra gece yarısı (günlük bar)"
YAHOO_URL = f"https://query1.finance.yahoo.com/v8/finance/chart/{SEMBOL}"
KAYNAK = "Yahoo Finance (USDTRY=X)"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")

# Kapsam sözleşmesi. Başlangıç payı: Yahoo serisi 2005 öncesine gitmez; istenen
# başlangıçtan bu kadar gün geç başlayan seri "tam" sayılır. Bitiş payı:
# hafta sonu + tek tatil. Seviye sınırı: eski önbellekle örtüşen SON ortak
# günde iki kaynağın oranı — yfinance arızası seviyeyi YILLARCA geride
# vermişti; %20 aynı gün için imkânsız bir farktır.
BASLANGIC_PAYI_GUN = 45
BITIS_PAYI_GUN = 5
SEVIYE_SINIRI = 0.20
# Hafta içi gün başına beklenen gözlem oranı: tatiller ve Yahoo'nun tek tük
# boşluğu için pay. 0,9'un altı kırpılmış seridir.
DOLULUK_ORANI = 0.90


@dataclass
class Kur:
    seri: pd.Series                       # DatetimeIndex → kapanış (float)
    kaynak: str = KAYNAK
    ilk: dt.date | None = None
    son: dt.date | None = None
    n: int = 0
    onbellekten: bool = False             # ağdan değil eski dosyadan geldi
    uyarilar: list[str] = field(default_factory=list)
    kapanis: str = _fx.KESIM_ADI[TUR]     # kapanış tanımı (okura yazılır)
    gecis: str | None = None              # saatlik kapanışın başladığı gün (öncesi günlük bar)
    canli: tuple | None = None            # (ölçüm anı UTC, son kotasyon) — yalnız bilgi
    # Günlük bar kısmında ölçülemeyen (seriye girmeyen) cumalar, ISO günüyle,
    # serinin aralığında. SEANSTIR, tatil değil: gün sayan tüketici (OVP'nin
    # yıl gün sayısı ve tatil payı) onları seans sayar; künye sayısını yazar.
    cuma_olculemeyen: list | None = None
    # Serinin TANIMI: kurulduğu önbellek sütununun adı (`SUTUN` = bugünkü
    # tanım). Bu seriden kendi önbelleğini türeten tüketici (TRYREER'in aylık
    # ortalaması) onu yanına yazar ve tanım değişince eskisini taze saymaz.
    tanim: str | None = None


def _yahoo_cek(bas: dt.date, bit: dt.date, simdi: dt.datetime | None = None) -> pd.Series:
    """İstanbul 18:00 kapanışları: saatlik bar + düzeltilmiş günlük bar.

    Dönen serinin `attrs`ı geçiş gününü ve canlı kotasyonu taşır. Saatlik bar
    alınamazsa seri yalnız düzeltilmiş günlük bardan kurulur ve `attrs`taki
    uyarı bunu söyler — son gün en az bir gün geride kalır ama yanlış tarih
    basmaz. Günlük bar kısmının ölçülemeyen cumaları `olculemeyen_gunluk`ta."""
    simdi = simdi or dt.datetime.now(dt.timezone.utc)
    gunluk = _gunluk_cek(bas, bit)
    bugun_londra = pd.Timestamp(simdi).tz_convert("Europe/London").date()
    duz = _fx.gunluk_duzelt(gunluk[gunluk.index.date < bugun_londra])
    cuma = list(duz.attrs.get("olculemeyen") or [])
    try:
        saatlik = _fx.yfinance_saatlik([SEMBOL]).get(SEMBOL)
        kp = _fx.saatlik_kapanislar(saatlik, TUR, simdi) if saatlik is not None else None
    except Exception as e:  # noqa: BLE001
        kp, hata = None, f"{type(e).__name__}: {e}"
    else:
        hata = "saatlik bar boş döndü"
    if kp is None or not len(kp.seri):
        duz.attrs = {"uyari": "saatlik bar alınamadı (" + hata[:120] + "); kapanış düzeltilmiş "
                              "günlük bardan (Londra gece yarısı), son gün en az bir gün geride",
                     "kapanis": "Londra gece yarısı (günlük bar)", "yedek": True,
                     "olculemeyen_gunluk": cuma}
        return _seri_temizle(duz.values, duz.index, duz.attrs)
    birlesik, gecis = _fx.birlestir(duz, kp)
    return _seri_temizle(birlesik.values, birlesik.index,
                         {"gecis": gecis, "canli": kp.canli, "kapanis": _fx.KESIM_ADI[TUR],
                          "olculemeyen": kp.olculemeyen,
                          "olculemeyen_gunluk": [g for g in cuma if gecis is None or g < gecis]})


def _gunluk_cek(bas: dt.date, bit: dt.date) -> pd.Series:
    """Günlük bar (barın Londra günüyle) — önce yfinance, düşerse doğrudan chart ucu.

    NEDEN İKİ YOL. Chart ucuna çıplak `requests` ile giden ilk sürüm GitHub
    koşucusundan 429 (Too Many Requests) aldı ve hat düştü (09.09.2026, koşu
    #142): Yahoo, çerez ve crumb taşımayan datacenter isteklerini
    sınırlıyor. Bülten piyasa fotoğrafı aynı koşucudan yıllardır yfinance ile
    geçiyor — kütüphane çerez/crumb el sıkışmasını ve tarayıcı kimliğini
    kendisi kurar. Ölçülen yol birinci, çıplak istek yalnız yedek."""
    hatalar: list[str] = []
    try:
        return _yfinance_cek(bas, bit)
    except Exception as e:  # noqa: BLE001 — yedek yola düşülür, sebep saklanır
        hatalar.append(f"yfinance: {type(e).__name__}: {e}")
    try:
        return _chart_cek(bas, bit)
    except Exception as e:  # noqa: BLE001
        hatalar.append(f"chart ucu: {type(e).__name__}: {e}")
    raise RuntimeError("; ".join(hatalar))


def _seri_temizle(kapanis, idx, attrs: dict | None = None) -> pd.Series:
    idx = pd.DatetimeIndex(pd.to_datetime(idx))
    if idx.tz is not None:
        # Günlük barın günü BORSANIN (Londra) günüdür; UTC'ye çevrilirse yaz
        # saatinde 00:00 BST bir önceki günün 23:00'üne düşer.
        idx = idx.tz_convert("Europe/London").tz_localize(None)
    idx = idx.normalize()
    s = pd.Series(pd.to_numeric(list(kapanis), errors="coerce"), index=idx,
                  dtype="float64", name="usdtry").dropna()
    s = s[~s.index.duplicated(keep="last")].sort_index()
    s.attrs = dict(attrs or {})
    return s


def _yfinance_cek(bas: dt.date, bit: dt.date) -> pd.Series:
    """yfinance.download — bültenle aynı çağrı biçimi (auto_adjust=False)."""
    import yfinance as yf
    ham = yf.download(SEMBOL, start=bas.isoformat(), end=bit.isoformat(), interval="1d",
                      progress=False, auto_adjust=False, threads=False)
    if ham is None or len(ham) == 0:
        raise RuntimeError("yfinance boş çerçeve döndürdü")
    if isinstance(ham.columns, pd.MultiIndex):
        # (Price, Ticker) ya da (Ticker, Price) — hangisi olursa olsun 'Close' sütunu
        if "Close" in ham.columns.get_level_values(0):
            kap = ham["Close"]
        else:
            kap = ham.xs("Close", axis=1, level=-1)
        kap = kap.iloc[:, 0] if isinstance(kap, pd.DataFrame) else kap
    else:
        kap = ham["Close"]
    return _seri_temizle(kap.values, kap.index)


def _chart_cek(bas: dt.date, bit: dt.date) -> pd.Series:
    """Yahoo chart ucundan günlük kapanış (YEDEK yol). Ağ hatası istisna."""
    import requests
    p1 = int(dt.datetime(bas.year, bas.month, bas.day, tzinfo=dt.timezone.utc).timestamp())
    p2 = int(dt.datetime(bit.year, bit.month, bit.day, tzinfo=dt.timezone.utc).timestamp())
    r = requests.get(YAHOO_URL, params={"period1": p1, "period2": p2, "interval": "1d",
                                        "events": "history", "includePrePost": "false"},
                     headers={"User-Agent": UA, "Accept": "application/json"}, timeout=60)
    r.raise_for_status()
    j = r.json()
    try:
        sonuc = j["chart"]["result"][0]
        zaman = sonuc["timestamp"]
        kapanis = sonuc["indicators"]["quote"][0]["close"]
    except (KeyError, IndexError, TypeError) as e:
        raise RuntimeError(f"Yahoo yanıtı beklenen biçimde değil: {e}") from e
    idx = pd.to_datetime(zaman, unit="s", utc=True)
    return _seri_temizle(kapanis, idx)


def kapanmamis_bari_dusur(s: pd.Series, simdi: dt.datetime | None = None) -> pd.Series:
    """Kapanış anı (İstanbul 18:00) gelmemiş gün seriye girmez."""
    simdi = pd.Timestamp(simdi or dt.datetime.now(dt.timezone.utc))
    simdi = simdi.tz_localize("UTC") if simdi.tzinfo is None else simdi.tz_convert("UTC")
    if not len(s):
        return s
    tut = [_fx.kapanis_ani(t.date(), TUR) <= simdi for t in s.index]
    r = s[tut]
    r.attrs = dict(s.attrs)
    return r


def haftasonu_barini_dusur(s: pd.Series) -> tuple[pd.Series, list[str]]:
    """Cumartesi/pazara düşen bar seriye girmez — FX'te HAFTA SONU SEANS DEĞİLDİR.

    13.09.2026 PAZAR koşusunda ölçüldü: seriye 12.09 CUMARTESİ barı girdi
    (48,55 — cumanın 48,5921 kapanışının %0,086 altında, yani bayat tekrar
    DEĞİL ayrı bir değer), hattın saati oldu ve sayfa cumartesi damgasıyla
    yayımlandı. Kapanmamış bar kuralı onu göremez: cumartesi barı PAZAR
    çekildiğinde artık "bugün" değildir. 14.09 pazartesi Yahoo o barı hiç
    vermedi (gözlem 678 → 677) ve gerileme kapısı öttü, iki pano birden
    siteye kopyalanamadı.

    İki gerekçe birden: (1) deponun kurucu ilkesi — bir ölçüm ancak KAPANMIŞ
    bir seansı ölçebilir, ve cumartesi seans değildir; (2) kaynağın kendisi
    o barı GERİ ÇEKTİ — bugün 3.045 gözlemlik seride (2015 →) hafta sonu barı
    SIFIR. Kaynağın geri çektiği bir bar hiçbir zaman yerleşmiş bir gözlem
    değildi.

    SİLMEK DEĞİL İŞARETLEMEK: düşen gün ADIYLA döner ve hattın uyarı
    listesine (`kur_uyari`) yazılır. Sessiz silme, ölçülmemiş bir şeyi
    ölçülmüş gibi göstermenin en sessiz biçimidir — ve kaynak bir gün
    damgalarını kaydırırsa (meşru bir cuma seansı cumartesiye düşerse)
    sessiz süzgeç gerçek veriyi yok eder, uyarı ise onu adıyla gösterir.

    SONRADAN ÖLÇÜLDÜ (02.10.2026): o cumartesi barı aslında cumanın GERÇEK gün
    sonuydu — Yahoo'nun kapanmış günlük döviz barı günün BAŞINDAKİ fiyatı
    taşır ve cumartesi barının başı cuma gecesidir. Seri artık saatlik bardan
    kurulduğu için hafta sonu günü üretmez; süzgeç, kurulmuş seride bir hafta
    sonu günü belirirse onu adıyla gösteren bekçi olarak kalır.
    """
    if not len(s):
        return s, []
    hs = s.index[s.index.dayofweek >= 5]
    if not len(hs):
        return s, []
    gun = ", ".join(f"{t:%d.%m.%Y}" for t in hs[-5:])
    fazla = f" (+{len(hs) - 5} gün daha)" if len(hs) > 5 else ""
    return s[s.index.dayofweek < 5], [
        f"{len(hs)} hafta sonu barı seriye alınmadı ({gun}{fazla}); "
        "hafta sonu işlem seansı yok"]


def _kapsam_uyarilari(s: pd.Series, bas: dt.date, bugun: dt.date,
                      eski: pd.Series | None, olculemeyen=()) -> list[str]:
    """Gelen serinin kapsamı çıktının ihtiyacına yetiyor mu — yetmiyorsa sebepler.

    `olculemeyen`: kurala göre seriye girmeyen, ADIYLA bilinen günler (günlük
    bar kısmının cumaları). Doluluk paydası onları beklemez: bilinen bir boşluk
    kırpılmış seri değildir — saymak saatlik barın ulaşmadığı geçmişin bütün
    cumalarını eksik sayar ve sağlıklı seriyi %90'ın altına düşürürdü (03.10.2026
    sınamasında, 18.12.2023 öncesi cumalar boşken, %82)."""
    u: list[str] = []
    if s.empty:
        return ["seri boş döndü"]
    ilk, son = s.index[0].date(), s.index[-1].date()
    if (ilk - bas).days > BASLANGIC_PAYI_GUN:
        u.append(f"seri {ilk:%d.%m.%Y} tarihinde başlıyor, {bas:%d.%m.%Y} istenmişti "
                 f"(başı kırpık)")
    if (bugun - son).days > BITIS_PAYI_GUN:
        u.append(f"seri {son:%d.%m.%Y} tarihinde bitiyor, bugün {bugun:%d.%m.%Y} "
                 f"(sonu {(bugun - son).days} gün geride)")
    pencere_bas = max(ilk, bas)
    bilinen = {g for g in olculemeyen if pencere_bas <= pd.Timestamp(g).date() <= son}
    beklenen = len(pd.bdate_range(pencere_bas, son)) - len(bilinen)
    if beklenen and len(s) < DOLULUK_ORANI * beklenen:
        u.append(f"{len(s)} gözlem, hafta içi {beklenen} gün bekleniyordu (seyrek)")
    if eski is not None and len(eski):
        ortak = s.index.intersection(eski.index)
        if len(ortak):
            g = ortak[-1]
            oran = float(s.loc[g]) / float(eski.loc[g]) if float(eski.loc[g]) else 1.0
            if abs(oran - 1.0) > SEVIYE_SINIRI:
                u.append(f"{g:%d.%m.%Y} günü seviye eldeki seriyle "
                         f"{_bicim.yuzde(abs(oran - 1) * 100, 0)} ayrışıyor "
                         f"(yeni {_bicim.sayi(float(s.loc[g]), 4)} · "
                         f"eski {_bicim.sayi(float(eski.loc[g]), 4)})")
    return u


def _kunye_yolu(yol: Path) -> Path:
    return yol.with_name(yol.stem + ".kunye.json")


def _kunye_oku(yol: Path) -> dict:
    """Önbelleğin yanındaki künye (geçiş günü): önbellekten dönen koşu da
    künyesini kaybetmesin — yoksa özetteki alan koşudan koşuya boş/dolu oynar."""
    try:
        return json.loads(_kunye_yolu(yol).read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return {}


def _kunye_yaz(yol: Path, d: dict) -> None:
    try:
        _kunye_yolu(yol).write_text(json.dumps(d, ensure_ascii=False) + "\n", encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass


def _oku(yol: Path) -> pd.Series | None:
    """Önbellek serisi; `attrs['tanim']` sütun adıdır (kapanış tanımı)."""
    try:
        df = pd.read_csv(yol, index_col=0, parse_dates=True)
        s = df.iloc[:, 0].astype(float)
        tanim = str(df.columns[0])
        s.name = "usdtry"
        s = s.sort_index()
        s.attrs = {"tanim": tanim}
        return s
    except Exception:  # noqa: BLE001
        return None


def _onbellek_tanimi(tanim: str | None, yol: Path | None) -> tuple[str, str]:
    """(kapanış adı, uyarı eki) — önbelleğin sütun adı TANIMI taşır ve her
    tanımın kendi cevabı vardır: yedek seri de doğru tarihli bir Londra gece
    yarısı kapanışıdır, "eski tanım" sayılmaz. 02.10.2026 sütunlarının farkı
    yalnız günlük bar kısmının cumasıdır; ek onu serinin sözleşmesiyle söyler."""
    kn = _kunye_oku(yol) if yol is not None else {}
    if tanim == SUTUN:
        return _fx.KESIM_ADI[TUR], ""
    if tanim in (YEDEK_SUTUN, ONCEKI_YEDEK_SUTUN):
        ek = "; eldeki seri günlük bardan (Londra gece yarısı) kurulmuştu"
        if tanim == ONCEKI_YEDEK_SUTUN:
            ek += " ve cuma değerleri pazartesi barının başıdır (hafta sonu açılışından sonraki fiyat)"
        return (kn.get("kapanis") or "Londra gece yarısı (günlük bar)", ek)
    if tanim == ONCEKI_SUTUN:
        g = kn.get("gecis")
        once = f"{pd.Timestamp(g):%d.%m.%Y} öncesinde" if g else "saatlik barın ulaşmadığı geçmişte"
        return (_fx.KESIM_ADI[TUR],
                f"; eldeki seride {once} cuma değeri pazartesi barının başıdır (hafta sonu açılışından "
                "sonraki fiyat)")
    return (ESKI_KAPANIS,
            "; eldeki seri günlük bardan kuruluydu: D tarihli değer D gününün başındaki fiyattır")


def seri(bas: str | dt.date = "2005-01-03", onbellek: str | Path | None = None,
         ttl_saat: float = 12.0, cek=None, simdi: dt.datetime | None = None) -> Kur:
    """USD/TRY günlük kapanış serisi (Kur nesnesi).

    `onbellek`: hattın kendi önbellek dosyası (CSV: tarih, usdtry). Tazelik
    kararı ortak/tazelik'ten geçer (TTL, TTO_YENILE, koşu başına tazeleme).
    `cek`: sınama için değiştirilebilir çekici; öntanımlı Yahoo.
    Ağ düşerse ya da kapsam yetmezse: eski önbellek varsa o döner
    (`onbellekten=True`, sebep `uyarilar`da), yoksa RuntimeError."""
    simdi = simdi or dt.datetime.now(dt.timezone.utc)
    bugun = simdi.date()
    bas_t = pd.Timestamp(bas).date()
    yol = Path(onbellek) if onbellek else None
    eski = _oku(yol) if (yol and yol.exists()) else None

    eski_tanim = (eski.attrs.get("tanim") if eski is not None else None)
    if yol is not None and eski is not None and eski_tanim == SUTUN:
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            import tazelik  # noqa: E402
            if tazelik.taze(yol, ttl_saat):
                # Künye önbellekle birlikte okunur: önbellekten dönen koşu da
                # kapanış tanımını ve uyarılarını taşısın (yoksa ikinci çağrı
                # her seferinde "temiz" der).
                kn = _kunye_oku(yol)
                return Kur(eski[eski.index >= pd.Timestamp(bas_t)], ilk=eski.index[0].date(),
                           son=eski.index[-1].date(), n=len(eski), onbellekten=True,
                           gecis=kn.get("gecis"), kapanis=kn.get("kapanis") or _fx.KESIM_ADI[TUR],
                           uyarilar=list(kn.get("uyarilar") or []),
                           cuma_olculemeyen=kn.get("cuma_olculemeyen"), tanim=SUTUN)
        except ImportError:
            pass

    try:
        yeni = (cek(bas_t, bugun + dt.timedelta(days=1)) if cek is not None
                else _yahoo_cek(bas_t, bugun + dt.timedelta(days=1), simdi))
    except Exception as e:  # noqa: BLE001
        if eski is not None:
            kap, ek = _onbellek_tanimi(eski_tanim, yol)
            return Kur(eski[eski.index >= pd.Timestamp(bas_t)], ilk=eski.index[0].date(),
                       son=eski.index[-1].date(), n=len(eski), onbellekten=True,
                       uyarilar=["Yahoo Finance erişilemedi; eldeki seri kullanıldı "
                                 f"(son gün {eski.index[-1]:%d.%m.%Y}){ek}"],
                       kapanis=kap, tanim=eski_tanim)
        raise RuntimeError(f"USD/TRY çekilemedi ve önbellek yok: {e}") from e

    meta = dict(getattr(yeni, "attrs", {}) or {})
    # YEDEK YOL (saatlik bar alınamadı): günlük bardan kurulan seri en az bir
    # gün geride biter (salı sabahı iki: pazartesi barının cuması ölçülemez).
    # Eldeki seri en az onun kadar yeniyse — HANGİ tanımla
    # yazılmış olursa olsun — o döner: yedeği yayımlamak hattın saatini geri
    # çeker ve gerileme kapısı hattı durdurur. Tanım şartı konmaz: geçiş günü
    # önbellek eski sütun adıyla durur ve koruma tam o gün gerekir. Yedek seri
    # hiçbir koşulda YENİ tanımın sütununa yazılmaz: yazılsaydı bir sonraki
    # koşu onu taze bir İstanbul 18:00 serisi sanırdı.
    yedek = bool(meta.get("yedek"))
    if yedek and eski is not None and len(yeni) and eski.index[-1] >= yeni.index[-1]:
        kap, _ = _onbellek_tanimi(eski_tanim, yol)
        kn = _kunye_oku(yol) if (yol is not None and eski_tanim == SUTUN) else {}
        return Kur(eski[eski.index >= pd.Timestamp(bas_t)], ilk=eski.index[0].date(),
                   son=eski.index[-1].date(), n=len(eski), onbellekten=True,
                   uyarilar=[meta["uyari"].split(";")[0] + f"; eldeki seri kullanıldı "
                             f"(kapanış {kap}, son gün {eski.index[-1]:%d.%m.%Y})"],
                   kapanis=kap, gecis=kn.get("gecis"), cuma_olculemeyen=kn.get("cuma_olculemeyen"),
                   tanim=eski_tanim)
    yeni = kapanmamis_bari_dusur(yeni, simdi)
    # SIRA ÖNEMLİ: hafta sonu barı kapsam denetiminden ÖNCE düşer. Aksi hâlde
    # doluluk ölçütü (len(s) ÷ iş günü) hafta sonu barını hafta içi gözlem
    # sayar ve eksik bir hafta içi gününü maskeler — ölçüt kendi paydasıyla
    # kandırılır.
    yeni, hs_uyari = haftasonu_barini_dusur(yeni)
    # Günlük bar kısmının ölçülemeyen cumaları ADIYLA bilinir; doluluk paydası
    # onları beklemez (bkz. _kapsam_uyarilari).
    gunluk_ol = list(meta.get("olculemeyen_gunluk") or [])
    kusur = _kapsam_uyarilari(yeni, bas_t, bugun, eski, gunluk_ol)
    if kusur:
        if eski is not None:
            kap, ek = _onbellek_tanimi(eski_tanim, yol)
            return Kur(eski[eski.index >= pd.Timestamp(bas_t)], ilk=eski.index[0].date(),
                       son=eski.index[-1].date(), n=len(eski), onbellekten=True,
                       uyarilar=["Yahoo Finance serisi kapsam sınamasını geçemedi, eldeki "
                                 "seri korundu: " + "; ".join(kusur) + ek],
                       kapanis=kap, tanim=eski_tanim)
        raise RuntimeError("USD/TRY serisi kapsam sınamasını geçemedi ve önbellek yok: "
                           + "; ".join(kusur))

    uyarilar = list(hs_uyari) + ([meta["uyari"]] if meta.get("uyari") else [])
    # Yalnız SAĞ UÇ uyarıdır: son ölçülen günden SONRAKİ ölçülemeyen gün
    # beslemenin kesildiğini söyler. Tarihçenin ortasındaki ölçülemeyen gün
    # (yılbaşı — Yahoo tatilde seyrek bar verir) seriden yine dışlanır ama uyarı
    # değildir: 730 günlük pencerede her zaman bir yılbaşı bulunur ve uyarı her
    # koşuda okura basılır, OVP'nin sağ uç ailesine düşüp özeti kalıcı olarak
    # bayat yapardı. Tatil ile kesintiyi ayıran şey o günden SONRA kurulmuş bir
    # kapanış gelip gelmediğidir.
    sag_uc = [g for g in (meta.get("olculemeyen") or []) if pd.Timestamp(g) > yeni.index[-1]]
    if sag_uc:
        uyarilar.append("saatlik barı kapanış anına yetişmeyen gün seriye alınmadı: "
                        + ", ".join(f"{pd.Timestamp(g):%d.%m.%Y}" for g in sag_uc[-5:]))
    # Günlük bar kısmının cuması da aynı kuralla: yalnız SAĞ UÇ uyarıdır (yedek
    # yolda salı sabahı). Tarihçenin ortasındaki cumalar (saatlik barın
    # ulaşmadığı geçmişin hepsi) her koşuda okura basılan bir uyarı olamaz;
    # SAYILARI künyededir.
    sag_cuma = [g for g in gunluk_ol if pd.Timestamp(g) > yeni.index[-1]]
    if sag_cuma:
        uyarilar.append("cuma kapanışı günlük bardan ölçülemedi, seriye alınmadı: "
                        + ", ".join(f"{pd.Timestamp(g):%d.%m.%Y}" for g in sag_cuma[-5:])
                        + " (cumartesi barı yok; pazartesi barı hafta sonu açılışından sonraki fiyatı taşır)")
    cuma_gun = [g for g in gunluk_ol if yeni.index[0] <= pd.Timestamp(g) <= yeni.index[-1]]
    if yol is not None:
        yol.parent.mkdir(parents=True, exist_ok=True)
        gecici = yol.with_name(yol.stem + ".tmp.csv")
        yeni.rename(YEDEK_SUTUN if yedek else SUTUN).to_csv(gecici, index_label="tarih")
        gecici.replace(yol)
        _kunye_yaz(yol, {"gecis": meta.get("gecis"), "kapanis": meta.get("kapanis"), "uyarilar": uyarilar,
                         "cuma_olculemeyen": cuma_gun})
    return Kur(yeni, ilk=yeni.index[0].date(), son=yeni.index[-1].date(),
               n=len(yeni), uyarilar=uyarilar, kapanis=meta.get("kapanis") or _fx.KESIM_ADI[TUR],
               gecis=meta.get("gecis"), canli=meta.get("canli"), cuma_olculemeyen=cuma_gun,
               tanim=YEDEK_SUTUN if yedek else SUTUN)


def kunye(k: Kur) -> dict:
    """Koşu kaydına / ozet.json'a düşecek künye (okur diline uygun).

    `kur_cuma_olculemeyen`: günlük bar kısmında ölçülemediği için seriye
    girmeyen cuma sayısı (cumartesi barı yok; pazartesi barının başı hafta sonu
    açılışından sonradır). Uyarı değil künyedir: tarihçenin ortasındaki bilinen
    bir boşluk her koşuda okura uyarı olarak basılamaz, ama sessiz de kalamaz."""
    return {"kur_kaynak": k.kaynak,
            "kur_ilk": k.ilk.strftime("%d.%m.%Y") if k.ilk else None,
            "kur_son": k.son.strftime("%d.%m.%Y") if k.son else None,
            "kur_gozlem": k.n,
            "kur_kapanis": k.kapanis,
            "kur_kapanis_gecis": (pd.Timestamp(k.gecis).strftime("%d.%m.%Y") if k.gecis else None),
            "kur_cuma_olculemeyen": None if k.cuma_olculemeyen is None else len(k.cuma_olculemeyen),
            "kur_uyari": list(k.uyarilar)}


if __name__ == "__main__":
    k = seri()
    print(json.dumps(kunye(k), ensure_ascii=False, indent=1))
    print(k.seri.tail())
