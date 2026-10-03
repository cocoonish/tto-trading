"""Döviz kurunun günlük kapanışı — TEK tanım, saatlik bardan.

NEDEN VAR. Yahoo'nun günlük döviz barı (`…=X`) kapandığında "Close" alanı
günün KAPANIŞINI değil BAŞINDAKİ fiyatı taşıyor; yüksek ve düşük ise günün
gerçek aralığı. 02.10.2026'da ölçüldü (`Aktarılacak Projeler/KurSaati/`):
EUR/USD'nin 01.10 barı açılış 1,13268 · kapanış 1,13272 · en düşük 1,12194;
CNBC (Tullett Prebon) New York kapanışı 01.10'da 1,1241, 30.09'da 1,1328.
Günlük barın kapanışı CNBC'nin AYNI gün kapanışından medyanda 15,4 bp,
BİR ÖNCEKİ gün kapanışından 3,2 bp sapıyor; gövde/aralık oranı medyanda
0,024 (on iki sembolün hepsinde benzer). Yani Yahoo'dan okunan her günlük
döviz serisi BİR GÜN geriden geliyordu ve D diye basılan değer D−1'in gün
sonuydu. Aynı gün indirilen canlı bar ise canlı fiyatı taşıyor; bar kapanınca
kapanışı günün başına dönüyor. Kusur 21.09.2026'da indikatör hattında
ölçülüp orada saatlik bardan kurularak düzeltilmişti ("gövde yok"); bültene
ve kur hatlarına taşınmamıştı.

Saatlik bar doğru: saatlik barlardan kurulan New York 17:00 kapanışı CNBC'nin
aynı gün kapanışından medyanda 3,8 bp (p90 5,3) sapıyor.

KAPANIŞ ANI (KARAR 02.10.2026, kullanıcı): lira kurları (USD/TRY, EUR/TRY,
GBP/TRY) İSTANBUL 18:00'de kapanır; öbür kurlar New York 17:00'de (küresel
döviz piyasasının standart kapanışı). İstanbul kapanışının gerekçesi ölçüldü:
son 60 iş gününde USD/TRY'nin günlük değişim oynaklığı İstanbul 18:00
kapanışıyla 8,1 bp, New York 17:00 ile 19,4 bp, UTC gün sonuyla 20,5 bp ve
birinci gecikme özilintisi sırasıyla −0,31 · −0,44 · −0,47 — akşam ve gece
saatlerinin sığ kotasyonları ertesi gün geri dönen gürültü taşıyor. 10.09
kararı (UTC günü) "15:00 barı final değil, akşam yayımı ertesi sabah revize
olur" gerekçesiyle İstanbul kapanışını reddetmişti; saatlik barda o gerekçe
yok: 14:00–15:00 UTC barı 15:00'te kapanır ve bir daha değişmez.

KAPANMIŞ SEANS. Bir günün kapanışı ancak kapanış anı geçtikten SONRA vardır
(bir ölçüm ancak kapanmış bir seansı ölçebilir); kapanış anından önceki son
saatlik bar kapanış anına `AZAMI_BOSLUK` kadar yakın değilse o gün ölçülemez
ve seriye girmez — beslemenin sabah kesildiği bir gün sabah fiyatıyla
"kapanış" diye basılmasın.

HAFTA SONU. Yalnız yerel HAFTA İÇİ günleri kapanış taşır. İstanbul 18:00'de
cumartesinin penceresi (cuma 18:00 → cumartesi 18:00) cuma akşamının
barlarını içerir; o barlar bir kapanış değil, pazartesinin penceresine aittir.

ESKİ GEÇMİŞ. Yahoo saatlik barı en çok 730 gün geriye verir; bu İŞ günüdür
(üretimin `730d` çağrısı 03.10.2026'da 18.12.2023'e iniyordu: tam 730 hafta
içi gün) ve pencere her iş günü bir gün ileri kayar — saatlik kapanış
arşivlenmez. Daha eskisi için günlük bar düzeltilerek okunur:
kapanmış bir barın "kapanışı" o günün başındaki, yani bir ÖNCEKİ takvim
gününün sonundaki fiyattır; değer bardan önceki son hafta içi güne yazılır —
YALNIZ bar o günün ERTESİ takvim günüyse. Bu kısım Londra gece yarısı
kapanışıdır, saatlik kısım kararın saatidir; geçiş günü künyeye yazılır.

CUMA. Cumanın ertesi günü cumartesidir; cumartesi barı yoksa cumaya
yazılabilecek tek bar pazartesi barıdır ve onun başı (pazartesi 00:00 Londra,
Yahoo'nun saatlik döviz haftasının da başladığı an) pazar akşamki hafta sonu
açılışından SONRAdır. O cuma ölçülemez: seriye girmez, adıyla döner
(`attrs["olculemeyen"]`). 03.10.2026'da ölçüldü (`bulten/kesif_fx_cuma.py`,
veri.yml keşfi #317): on beş sembolün 2005'ten bu yana günlük geçmişinde
cumartesi ya da pazar barı SIFIR; saatlik barla örtüşen pencerede (18.12.2023
→ 01.10.2026) G10'un 1.716 cumasının hiçbirinde cumartesi barı yok ve
pazartesi barından gelen cuma değeri saatlik kapanıştan medyanda 7,4 bp (p90
26,4 · azami 143,7) sapıyor, pazartesi–perşembe 3,9 bp (p90 12,9); bu kısmın
kendi tanımına (Londra gece yarısı) göre 7,6 bp'ye karşı 1,7. Değer pazartesi
00:00 Londra fiyatından medyanda 2,2 bp uzakta: cumaya hafta sonu boşluğu
(medyan 7,4 bp, p90 26,1) yazılıyor, haftanın değişimi cumanın değişimine
taşınıyordu. Lira kurlarında aynı ölçü 432 cumada medyan 13,4 bp (taban 4,8).
Haftalık bar kaynak DEĞİL: on beş sembolün on ikisinde haftalık kapanış cumanın
günlük barıyla birebir (o da günün başı), kalan üçünde hiçbir kapanışa
yaklaşmıyor. Gerçek bir cuma kapanışı taşıyan tek günlük bar cumartesi barıdır
(13.09.2026 pazar koşusunda ölçüldü; kaynak onu ertesi gün geri çekiyor).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo

import pandas as pd

TR = "tr"
G10 = "g10"
KESIM = {
    TR: ("Europe/Istanbul", dt.time(18, 0)),
    G10: ("America/New_York", dt.time(17, 0)),
}
KESIM_ADI = {TR: "İstanbul 18:00", G10: "New York 17:00"}
# Kapanış anından önceki son saatlik barın kapanışı en çok bu kadar erken
# olabilir: tek bir eksik saatlik bar meşrudur (Yahoo'nun tek tük boşluğu),
# üç saatlik boşluk besleme kesintisidir.
AZAMI_BOSLUK = dt.timedelta(hours=3)
# Canlı kotasyon yalnız ölçüm anında AÇIK bir barın fiyatıysa canlıdır. Son
# bar ölçümden bu kadar önce başladıysa besleme durmuş ya da piyasa kapalıdır
# (pazar öğleden sonrası cuma akşamının fiyatını taşır): kotasyon basılmaz.
CANLI_AZAMI = dt.timedelta(minutes=90)
SAATLIK_DONEM = "730d"          # yfinance'in 60 dakikalık bar sınırı


def kesim_turu(sembol: str) -> str:
    """Lira içeren kur İstanbul'da, öbürleri New York'ta kapanır."""
    return TR if "TRY" in sembol.upper() else G10


def kapanis_ani(gun: dt.date, tur: str) -> pd.Timestamp:
    """O günün kapanış anı, UTC."""
    tz, saat = KESIM[tur]
    return pd.Timestamp(dt.datetime.combine(gun, saat), tz=ZoneInfo(tz)).tz_convert("UTC")


@dataclass
class Kapanislar:
    seri: pd.Series                                   # tarih (gün, tz'siz) → kapanış
    tur: str = G10
    kapanis_utc: dict = field(default_factory=dict)   # 'YYYY-MM-DD' → ISO UTC kapanış anı
    olculemeyen: list = field(default_factory=list)   # barı olup kapanışı kurulamayan günler
    canli: tuple | None = None                        # (kotasyonun anı UTC, son kotasyon) — yalnız bilgi


def saatlik_kapanislar(kapanis: pd.Series, tur: str, simdi: dt.datetime | None = None) -> Kapanislar:
    """Saatlik bar kapanışlarından günlük kapanışlar.

    `kapanis`: saatlik barların BAŞLANGIÇ zamanıyla (tz bilgili ya da UTC)
    indekslenmiş kapanış fiyatları. Bir barın kapanışı başlangıcından bir saat
    sonradır; günün kapanışı, kapanış anında ya da ondan önce kapanan SON
    barın kapanışıdır."""
    simdi_ts = pd.Timestamp(simdi or dt.datetime.now(dt.timezone.utc))
    simdi_ts = simdi_ts.tz_localize("UTC") if simdi_ts.tzinfo is None else simdi_ts.tz_convert("UTC")
    s = pd.to_numeric(kapanis, errors="coerce").dropna()
    if not len(s):
        return Kapanislar(pd.Series(dtype="float64"), tur)
    idx = pd.DatetimeIndex(s.index)
    idx = idx.tz_localize("UTC") if idx.tz is None else idx.tz_convert("UTC")
    s = pd.Series(s.values, index=idx + pd.Timedelta(hours=1), dtype="float64")   # → barın KAPANIŞ anı
    s = s[~s.index.duplicated(keep="last")].sort_index()
    # CANLI KOTASYON: henüz kapanmamış son barın kapanışı ölçüm anının son
    # fiyatıdır. Yalnız BİLGİ olarak taşınır (okura saatiyle basılır); hiçbir
    # kapanışa, değişime ya da oynaklığa girmez.
    # Damga barın KENDİ saatidir: açık barın son fiyatı ölçüm anınındır, kapanmış
    # bir barınki kapanış anının (ölçüm anıyla damgalansa cuma akşamının fiyatı
    # pazar öğleden sonrası "şimdi" diye basılırdı).
    basladi = s[s.index - pd.Timedelta(hours=1) <= simdi_ts]     # ölçüm anında başlamış barlar
    canli = None
    if len(basladi) and simdi_ts - (basladi.index[-1] - pd.Timedelta(hours=1)) <= CANLI_AZAMI:
        zaman = min(basladi.index[-1], simdi_ts)
        canli = (zaman.isoformat().replace("+00:00", "Z"), float(basladi.iloc[-1]))
    s = s[s.index <= simdi_ts]                       # henüz kapanmamış bar kapanış taşımaz
    if not len(s):
        return Kapanislar(pd.Series(dtype="float64"), tur, canli=canli)
    tz, _ = KESIM[tur]
    yerel = s.index.tz_convert(tz)
    gunler = sorted({d for d in yerel.date})
    gunler.append(gunler[-1] + dt.timedelta(days=1))
    deger, ani, olculemeyen = {}, {}, []
    for g in gunler:
        if g.weekday() >= 5:
            continue
        kes = kapanis_ani(g, tur)
        if kes > simdi_ts:
            continue                                  # kapanış anı gelmedi
        onceki = s[(s.index <= kes) & (s.index > kes - pd.Timedelta(hours=24))]
        if not len(onceki):
            continue                                  # o gün işlem yok (tatil/boşluk)
        if kes - onceki.index[-1] > AZAMI_BOSLUK:
            olculemeyen.append(g.isoformat())
            continue
        deger[pd.Timestamp(g)] = float(onceki.iloc[-1])
        ani[g.isoformat()] = kes.isoformat().replace("+00:00", "Z")
    seri = pd.Series(deger, dtype="float64").sort_index()
    seri.name = "kapanis"
    return Kapanislar(seri, tur, ani, olculemeyen, canli)


def gunluk_duzelt(gunluk: pd.Series, pazartesi_cumaya: bool = False) -> pd.Series:
    """Saatlik barın ulaşmadığı ESKİ geçmiş için günlük bar, düzeltilerek.

    `gunluk`: Yahoo günlük barının kapanışları, barın (Londra) GÜNÜYLE
    indeksli. Kapanmış bir barın "kapanışı" o günün başındaki fiyattır, yani
    önceki takvim gününün sonu; değer bardan önceki son hafta içi güne yazılır,
    YALNIZ bar o günün ertesi takvim günüyse (barın başı o günün sonudur).
    Cumanın değeri yalnız cumartesi barından gelir; pazar ya da pazartesi barının
    başı cumanın sonu değildir (pazartesininki hafta sonu açılışından sonradır,
    pazar barı hiç ölçülmedi — 2005'ten bu yana kaynakta yok). Böyle bir cuma
    ölçülemez: seriye girmez, `attrs["olculemeyen"]`de ISO günüyle döner
    (`Kapanislar.olculemeyen` ile aynı sözleşme; okura yalnız serinin SAĞ
    UCUNDA uyarı olarak basılır, tarihçenin ortasında künyede sayılır).
    Bugünün barı (canlı) çağıran tarafından ÖNCEDEN çıkarılmış olmalı.

    `pazartesi_cumaya=True` 03.10.2026 öncesi eşlemeyi olduğu gibi verir
    (pazartesi barı → cuma) ve o cumaları `attrs["pazartesi_barindan"]`da adıyla
    döndürür. YALNIZ bu tuzağı kendisi ölçüp okura anlatan DONMUŞ ölçüm içindir
    (MakroKurFaiz dersi, `ortak_olc.usdtry` cuma tuzağı: sayıları o eşlemeyle
    kuruldu ve dersin metni onu anlatıyor); üretim serisi bu bayrağı taşımaz,
    duman sınaması bunu kaynak metninden ve davranıştan sorar."""
    s = pd.to_numeric(gunluk, errors="coerce").dropna()
    if not len(s):
        s.attrs = {"olculemeyen": [], "pazartesi_barindan": []}
        return s
    idx = pd.DatetimeIndex(s.index)
    if idx.tz is not None:
        idx = idx.tz_convert("Europe/London").tz_localize(None)
    gun = idx.normalize()
    hedef = []
    for t in gun:
        h = t - pd.Timedelta(days=1)
        while h.dayofweek >= 5:
            h -= pd.Timedelta(days=1)
        hedef.append(h)
    out = pd.DataFrame({"hedef": hedef, "bar": gun, "v": s.values}).sort_values("bar")
    # Bar hedefin ERTESİ günü değilse (cuma ← pazar/pazartesi barı) başı hedefin
    # sonu değildir. Eski eşlemede aynı güne iki bar düştüğünde (cumartesi ve
    # pazartesi → cuma) güne YAKIN olan, önce gelen bar kazanıyordu; o kural
    # yalnız cumartesi barı VARSA doğruydu ve 2005'ten bu yana hiç yok.
    ertesi = (out["bar"] - out["hedef"]) == pd.Timedelta(days=1)
    olculemeyen: list[str] = []
    if not pazartesi_cumaya:
        gecerli = out[ertesi]
        olculemeyen = sorted(t.date().isoformat() for t in set(out.loc[~ertesi, "hedef"]) - set(gecerli["hedef"]))
        out = gecerli
    out = out.drop_duplicates("hedef", keep="first")
    pazartesi = sorted(t.date().isoformat() for t in out.loc[(out["bar"] - out["hedef"]) != pd.Timedelta(days=1), "hedef"])
    r = pd.Series(out["v"].values, index=pd.DatetimeIndex(out["hedef"]), dtype="float64").sort_index()
    r.name = "kapanis"
    r.attrs = {"olculemeyen": olculemeyen, "pazartesi_barindan": pazartesi}
    return r


def birlestir(eski: pd.Series, saatlik: Kapanislar) -> tuple[pd.Series, str | None]:
    """Düzeltilmiş günlük geçmiş + saatlik kapanışlar; geçiş günü döner."""
    if not len(saatlik.seri):
        return eski, None
    ilk = saatlik.seri.index[0]
    once = eski[eski.index < ilk] if len(eski) else eski
    r = pd.concat([once, saatlik.seri]).sort_index()
    r = r[~r.index.duplicated(keep="last")]
    r.name = "kapanis"
    return r, ilk.date().isoformat()


def yfinance_saatlik(semboller: list[str], donem: str = SAATLIK_DONEM):
    """yfinance'ten saatlik kapanışlar: {sembol: pd.Series (UTC bar başlangıcı → kapanış)}."""
    import yfinance as yf
    ham = yf.download(semboller, period=donem, interval="60m", progress=False, auto_adjust=False,
                      group_by="ticker", threads=False)
    out = {}
    if ham is None or len(ham) == 0:
        return out
    for k in semboller:
        try:
            c = ham[k]["Close"] if isinstance(ham.columns, pd.MultiIndex) else ham["Close"]
            c = c.dropna()
            if len(c):
                idx = pd.DatetimeIndex(c.index)
                c.index = idx.tz_localize("UTC") if idx.tz is None else idx.tz_convert("UTC")
                out[k] = c.astype("float64")
        except Exception:  # noqa: BLE001 — sembol eksikse çağıran tarafa adıyla düşer
            continue
    return out
