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

KAPANMAMIŞ BAR. Yahoo günün henüz kapanmamış barını da döndürür; FX 7/24
işlem gördüğü için bugünün barı akşama kadar değişir. Bülten piyasa
katmanının kuralı burada da geçerli (bir ölçüm ancak KAPANMIŞ bir seansı
ölçebilir): bugüne ait bar, gün UTC olarak kapanmadan seriye alınmaz.

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

SEMBOL = "USDTRY=X"
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


def _yahoo_cek(bas: dt.date, bit: dt.date) -> pd.Series:
    """Günlük kapanış — önce yfinance, düşerse doğrudan chart ucu.

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


def _seri_temizle(kapanis, idx) -> pd.Series:
    idx = pd.DatetimeIndex(pd.to_datetime(idx))
    if idx.tz is not None:
        idx = idx.tz_convert(None)
    idx = idx.normalize()
    s = pd.Series(pd.to_numeric(list(kapanis), errors="coerce"), index=idx,
                  dtype="float64", name="usdtry").dropna()
    s = s[~s.index.duplicated(keep="last")].sort_index()
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
    """Bugüne ait bar, gün (UTC) kapanmadan seriye girmez."""
    simdi = simdi or dt.datetime.now(dt.timezone.utc)
    if len(s) and s.index[-1].date() >= simdi.date():
        return s.iloc[:-1]
    return s


def _kapsam_uyarilari(s: pd.Series, bas: dt.date, bugun: dt.date,
                      eski: pd.Series | None) -> list[str]:
    """Gelen serinin kapsamı çıktının ihtiyacına yetiyor mu — yetmiyorsa sebepler."""
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
    beklenen = len(pd.bdate_range(max(ilk, bas), son))
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


def _oku(yol: Path) -> pd.Series | None:
    try:
        s = pd.read_csv(yol, index_col=0, parse_dates=True).iloc[:, 0].astype(float)
        s.name = "usdtry"
        return s.sort_index()
    except Exception:  # noqa: BLE001
        return None


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

    if yol is not None and eski is not None:
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            import tazelik  # noqa: E402
            if tazelik.taze(yol, ttl_saat):
                return Kur(eski[eski.index >= pd.Timestamp(bas_t)], ilk=eski.index[0].date(),
                           son=eski.index[-1].date(), n=len(eski), onbellekten=True)
        except ImportError:
            pass

    cek = cek or _yahoo_cek
    try:
        yeni = cek(bas_t, bugun + dt.timedelta(days=1))
    except Exception as e:  # noqa: BLE001
        if eski is not None:
            return Kur(eski[eski.index >= pd.Timestamp(bas_t)], ilk=eski.index[0].date(),
                       son=eski.index[-1].date(), n=len(eski), onbellekten=True,
                       uyarilar=["Yahoo Finance erişilemedi; eldeki seri kullanıldı "
                                 f"(son gün {eski.index[-1]:%d.%m.%Y})"])
        raise RuntimeError(f"USD/TRY çekilemedi ve önbellek yok: {e}") from e

    yeni = kapanmamis_bari_dusur(yeni, simdi)
    kusur = _kapsam_uyarilari(yeni, bas_t, bugun, eski)
    if kusur:
        if eski is not None:
            return Kur(eski[eski.index >= pd.Timestamp(bas_t)], ilk=eski.index[0].date(),
                       son=eski.index[-1].date(), n=len(eski), onbellekten=True,
                       uyarilar=["Yahoo Finance serisi kapsam sınamasını geçemedi, eldeki "
                                 "seri korundu: " + "; ".join(kusur)])
        raise RuntimeError("USD/TRY serisi kapsam sınamasını geçemedi ve önbellek yok: "
                           + "; ".join(kusur))

    if yol is not None:
        yol.parent.mkdir(parents=True, exist_ok=True)
        gecici = yol.with_name(yol.stem + ".tmp.csv")
        yeni.rename("usdtry").to_csv(gecici, index_label="tarih")
        gecici.replace(yol)
    return Kur(yeni, ilk=yeni.index[0].date(), son=yeni.index[-1].date(), n=len(yeni))


def kunye(k: Kur) -> dict:
    """Koşu kaydına / ozet.json'a düşecek künye (okur diline uygun)."""
    return {"kur_kaynak": k.kaynak,
            "kur_ilk": k.ilk.strftime("%d.%m.%Y") if k.ilk else None,
            "kur_son": k.son.strftime("%d.%m.%Y") if k.son else None,
            "kur_gozlem": k.n,
            "kur_uyari": list(k.uyarilar)}


if __name__ == "__main__":
    k = seri()
    print(json.dumps(kunye(k), ensure_ascii=False, indent=1))
    print(k.seri.tail())
