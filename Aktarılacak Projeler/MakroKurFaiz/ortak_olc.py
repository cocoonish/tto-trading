#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRODAN KURA VE FAİZE — ölçüm katmanının ORTAK tanımları.

Bütün bölüm modülleri (`olcum_b*.py`) aynı ölçüyü bu dosyanın tek tanımından
okur; aynı ölçü iki modülde iki ayrı kodla kurulmaz (iki ayrı formül bir gün
sessizce ayrışır). Bölümler arası tutarlılık turu (02.10.2026) şu tanımları
modüllerden buraya taşıdı ve modülleri onlara bağladı:

  tr_takvim()            Türkiye iş günü takvimi (b01, b02, b03'te üç kopya vardı)
  DIBS_KAYMA · dibs()    DİBS gösterge etiketinin piyasa gününe hizası
                          (b01 2, b03 1 ve ikisi farklı kaydırma kodu)
  tr_gunluk[_degisim]()  Türkiye günlük çerçevesi (b01, b02, b03)
  cnbc_kur() · dolar_sepeti() · abd_gunluk[_degisim]()
                          CNBC bozuk kotasyon temizliği ve G10 dolar sepeti
                          (b01 temizliyordu, b03'ün kopyası temizlemiyordu)
  YONETILEN              yönetilen kur dönemi (b01 sabiti, öbürleri dizge kopyası)
  bilesik() · aylik_log_tasima()   faiz kotasyonundan bileşik ve taşıma (b05, b11)
  kadran() · KADRAN_ADI_*          faiz × para değeri kadranı (b01, b05)
  reg() · oos_kiyas() · oos_takimi() · hukum() · regresyon()
                          regresyon, iki saf kıyas, ambargolu örneklem dışı
                          sınama ve hüküm (b03, b08, b11, b12, b01 ayrı kurardı)
  olay_kapisi()          plasebo kapısı ve gün eşlemeli rastgele kıyas
                          (b02'nin kapısı kanonikti; b03 zayıf kopyasını kullanırdı)
  donem_sonu_kur()       TCMB dönem sonu kuru (b06)
  usdtry_tcmb()          TCMB kurunun ilan gününe Türkiye takvimiyle geri alınması
                          (b08'in valör sırası ile ortak fonksiyonun takvimsiz iş günü
                          geri alması ayrışıyordu; tatil öncesi ilan tatile yazılıyordu);
                          ilan olmayan arife günleri boştur (`tcmb_ilansiz_gunler`)
  bas_gun() · son_gun()  pencere uçlarının işlem günü (b05, b06'da iki kopya vardı)
  usdtry(cuma_dus=…)     18.12.2023 öncesi cuma değerinin (pazartesi barının başı)
                          boşaltılması; haftalık/aylık/olay pencereli ölçüler okur
  em_kur()               Yahoo EM kurları; MXN'nin Nisan 2018 öncesi gün sonu barı
                          düzeltilmez (b08, b11 ortak okur)

OKUMA. `oku(ad)` arşiv dosyasını açar ve sıkıştırılmamış metnin sha256'sını
künyeyle kıyaslar; tutmazsa okumaz (arşiv elle değiştirilmiş ya da başka bir
çıpadan gelmiştir). Ham bulut arşivinin ayrıştırılmış hâli `veri/bulut/`
altındadır (`hazirla_bulut.py`) ve aynı kapıdan okunur.

USD/TRY (karar 09.09.2026 ve 02.10.2026): kurun konu olduğu her ölçü Yahoo
Finance'ten okunur. Saatlik barın ulaştığı yerde İstanbul 18:00 kapanışı
(`usdtry_ist18`), öncesinde günlük barın düzeltilmiş hâli: Yahoo'nun kapanmış
günlük döviz barında "Close" o günün BAŞINDAKİ fiyattır, değer bir önceki
hafta içi güne yazılır (`ortak/fx_kapanis.gunluk_duzelt`). Geçiş günü künyede
ölçülmüş olarak durur. TCMB gösterge kuru VALÖR tarihlidir (ertesi iş günü)
ve yalnız sağlamlıkta ve dönüşüm kuru olarak, Türkiye iş günü takvimiyle
ilan gününe geri alınarak kullanılır (`usdtry_tcmb`).

İSTATİSTİK. Regresyonların hepsi Newey–West (Bartlett) standart hatasıyla
raporlanır; zaman serisi ilişkileri ayrıca ÖRNEKLEM DIŞI iki saf kıyasla
(rastgele yürüyüş = değişim sıfır, ve koşulsuz ortalama) sınanır, çünkü
"örneklem içi uyum" "yarın hangisini kullanayım" sorusunu cevaplamaz. Yarı ömür
nokta değil aralıktır (medyan-yansız kestirim, bootstrap).
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import math
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

BURASI = Path(__file__).resolve().parent
VERI = BURASI / "veri"
BULUT = VERI / "bulut"
KOK = BURASI.parents[1]
sys.path.insert(0, str(KOK / "ortak"))
import fx_kapanis as _fx  # noqa: E402

CIPA_GUN = pd.Timestamp("2026-09-30")
CIPA_AY = pd.Period("2026-08", "M")
CIPA_CEYREK = pd.Period("2026Q2", "Q")


def _iso(t) -> str | None:
    if t is None:
        return None
    if isinstance(t, pd.Period):
        return str(t)
    try:
        return str(pd.Timestamp(t).date())
    except (ValueError, TypeError):
        return str(t)


def _f(x) -> float | None:
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def kurulmadi(sebep: str, **ek) -> dict:
    """Kurulamayan pratik: sebep okur diliyle; uydurma sayı yerine."""
    return {"durum": "kurulmadi", "sebep": sebep, **ek}


def bas_gun(idx: pd.DatetimeIndex, t) -> pd.Timestamp | None:
    """Olay öncesi kapanış: t'ye eşit ya da ondan önceki son işlem günü."""
    j = idx.searchsorted(pd.Timestamp(t), side="right") - 1
    return idx[j] if j >= 0 else None


def son_gun(idx: pd.DatetimeIndex, t) -> pd.Timestamp | None:
    """Pencere sonu: t'ye eşit ya da ondan sonraki ilk işlem günü."""
    j = idx.searchsorted(pd.Timestamp(t), side="left")
    return idx[j] if j < len(idx) else None


# ─────────────────────────────────────────────────────────────── okuma
@lru_cache(maxsize=None)
def _kunye(dizin: str) -> dict:
    p = Path(dizin) / "kunye.json"
    if not p.exists():
        return {}
    k = json.loads(p.read_text(encoding="utf-8"))
    return k.get("dosyalar", k)


def oku(ad: str, dizin: Path | None = None) -> pd.DataFrame:
    """Arşiv dosyası (`ad` uzantısız ya da .csv.gz'li); öz künyeyle sınanır."""
    dizin = dizin or (BULUT if (BULUT / _ad(ad)).exists() and not (VERI / _ad(ad)).exists() else VERI)
    dosya = _ad(ad)
    ham = gzip.decompress((dizin / dosya).read_bytes())
    k = _kunye(str(dizin)).get(dosya)
    if k is None:
        raise RuntimeError(f"{dosya}: künyede kaydı yok — arşiv dışı dosya okunmaz")
    oz = hashlib.sha256(ham).hexdigest()
    if oz != k.get("sha256"):
        raise RuntimeError(f"{dosya}: öz tutmuyor (künye {k.get('sha256', '')[:12]} · dosya {oz[:12]})")
    df = pd.read_csv(io.BytesIO(ham))
    ilk = df.columns[0]
    try:
        df[ilk] = pd.to_datetime(df[ilk])
        df = df.set_index(ilk).sort_index()
    except (ValueError, TypeError):
        df = df.set_index(ilk)
    return df


def _ad(ad: str) -> str:
    return ad if ad.endswith(".csv.gz") else f"{ad}.csv.gz"


def ozler() -> dict:
    """Ölçüm dosyasına yazılacak: okunan her arşiv dosyasının özü (dogrula.py sınar)."""
    out = {}
    for d in (VERI, BULUT):
        for ad, k in _kunye(str(d)).items():
            if isinstance(k, dict) and "sha256" in k:
                out[f"{d.name}/{ad}"] = k["sha256"]
    return dict(sorted(out.items()))


# ─────────────────────────────────────────────────────────────── dönemler
# Yönetilen kur dönemi: kur korumalı mevduat ve kontrollü kur (Türkiye). Kur
# tepkisinde sıfır eğim tasarım gereğidir; bu dönem AYRI raporlanır, havuzlanmaz.
# Sözleşmenin sabitidir; dönem listelerinin dizgeleri buradan türetilir.
YONETILEN = (pd.Timestamp("2021-12-01"), pd.Timestamp("2023-06-30"))
YON_ILK, YON_SON = str(YONETILEN[0].date()), str(YONETILEN[1].date())                    # 2021-12-01 · 2023-06-30
YON_ONCESI_SON = str((YONETILEN[0] - pd.Timedelta(days=1)).date())                       # 2021-11-30
YON_SONRASI_ILK = str((YONETILEN[1] + pd.Timedelta(days=1)).date())                      # 2023-07-01
YON_ONCESI_SON_AY = str((YONETILEN[0] - pd.offsets.MonthBegin(1)).date())                # 2021-11-01 (ay başı etiketi)
YON_SON_AY = str(YONETILEN[1].to_period("M").to_timestamp().date())                     # 2023-06-01
YON_AY = (str(YONETILEN[0].to_period("M")), str(YONETILEN[1].to_period("M")))           # ("2021-12", "2023-06")
YON_ONCESI_AY = str((YONETILEN[0].to_period("M") - 1))                                   # 2021-11
YON_SONRASI_AY = str((YONETILEN[1].to_period("M") + 1))                                  # 2023-07
YON_CEYREK = (YONETILEN[0].to_period("Q"), YONETILEN[1].to_period("Q"))                 # 2021Q4 · 2023Q2


def yonetilen_mi(t):
    """Gün, ay başı ya da hafta etiketi yönetilen kur döneminde mi (dizi ya da tek değer)."""
    if isinstance(t, (pd.DatetimeIndex, pd.Series, np.ndarray)):
        t = pd.DatetimeIndex(t)
        return (t >= YONETILEN[0]) & (t <= YONETILEN[1])
    t = pd.Timestamp(t)
    return bool(YONETILEN[0] <= t <= YONETILEN[1])


# ─────────────────────────────────────────────────────────────── Türkiye takvimi ve DİBS
@lru_cache(maxsize=1)
def _tr_takvim() -> pd.DatetimeIndex:
    return pd.DatetimeIndex(oku("fonlama_gunluk").index)


def tr_takvim() -> pd.DatetimeIndex:
    """Türkiye iş günü takvimi: Fonlama hattının EVDS iş günleri (2011-01-03 → çıpa).

    Resmî tatiller yoktur; hafta sonu yoktur. TEK tanım: önceki sürümde b01 ve
    b02 bu takvimi, b03 bunun DİBS gün kümesiyle kesişimini kullanıyordu; ikisi
    yalnız iki yerde ayrışır — 2011–2012 (DİBS 2013'te başlar) ve 03.10.2014
    (Kurban Bayramı arifesi: EVDS iş günü, DİBS satırı yok). DİBS'e dayanan
    çerçeveler DİBS'in kapsamına ayrıca kırpılır (`dibs`)."""
    return _tr_takvim()


# DİBS gösterge değerinin TARİH SÖZLEŞMESİ — tek tanım.
#   Olgu (ölçüldü): L etiketli değer, L'den bir önceki Türkiye iş gününün SABAH
#   sabitlemesidir (TCMB gösterge kuru gibi valör tarihli; fiyat öğleden önce).
#   Kanıt 1 — tatil sınaması (olcum_b03._tatil_kaniti): tek günlük tatil H'de
#     etiket H+1'in |Δ|'ı medyanda 0,2 bp (donuk: H+1 etiketi de H−1 sabahıdır),
#     H+2'ninki 17,7 bp (olağan; sıradan gün 13,8–14,2 bp), 2013–2026'da 70 tatil.
#   Kanıt 2 — çapraz korelasyon (olcum_b02.tarih_sozlesmesi, 2013–2021):
#     günlük değişimin sıra korelasyonunun tepesi gün sonu kapanışlarına göre
#     (Yahoo USD/TRY Londra gece yarısı, ZAR, VIX; ABD serileri) +2 iş günü,
#     TCMB gösterge kurunun sabah sabitlemesine göre +1 iş günü.
#   Hiza: D piyasa gününe yazılan değer, D'den k Türkiye iş günü SONRAKİ
#   etiketin değeridir.
#     "gun_sonu" k = 2 — D'nin gün sonu kapanışlarıyla (Yahoo kuru, ABD
#        getirisi, VIX, ZAR) aynı güne oturtur; D'nin 14:00 kararı (PPK) bu
#        hizada D'nin değişimine düşer.
#     "sabah" k = 1 — D'nin gün içi sabitlemeleriyle (TLREF, AOFM, TCMB gösterge
#        kuru) karşılaştırılır; D'nin sabahını ölçer, D öğleden sonrasını değil.
#     "ham" k = 0 — etiketin kendisi (yalnız hiza sınamalarında).
#   Kaydırma Türkiye iş günü TAKVİMİNDE yapılır: DİBS dosyası tatillerde de satır
#   taşıdığı için kendi satır sırasında kaydırmak tatil komşuluğunda k = 2'yi
#   yanlış güne yazar (H−1 için k = 2, H+1 etiketini — H−1 sabahını — verirdi).
DIBS_KAYMA = {"gun_sonu": 2, "sabah": 1, "ham": 0}


def dibs_kayma(hiza: str) -> int:
    if hiza not in DIBS_KAYMA:
        raise KeyError(f"DİBS hizası tanımsız: {hiza} (geçerli: {', '.join(DIBS_KAYMA)})")
    return DIBS_KAYMA[hiza]


@lru_cache(maxsize=32)
def _dibs(dugumler: tuple | None, k: int) -> pd.DataFrame:
    d = oku("dibs_egri_gunluk")
    kol = list(dugumler) if dugumler else list(d.columns)
    tk = tr_takvim()
    tk = tk[(tk >= d.index.min()) & (tk <= d.index.max())]
    x = d[kol].reindex(tk)
    if k:
        x = x.shift(-k)
    return x[x.index <= CIPA_GUN]


def dibs(hiza: str = "gun_sonu", dugumler=None, kayma: int | None = None) -> pd.DataFrame:
    """DİBS gösterge eğrisi (%), Türkiye iş günü takviminde, DİBS'in kapsamında,
    piyasa gününe hizalanmış (`DIBS_KAYMA`). Takvim günü DİBS'te yoksa (03.10.2014)
    o etiket boştur. `kayma` yalnız duyarlılık taramaları içindir: hizayı geçersiz
    kılar ve verilen iş günü kadar kaydırır."""
    k = int(kayma) if kayma is not None else dibs_kayma(hiza)
    return _dibs(tuple(dugumler) if dugumler else None, k).copy()


# ─────────────────────────────────────────────────────────────── kurlar
GECIS_YAHOO_CUMA = pd.Timestamp("2023-12-18")      # öncesinde Yahoo USD/TRY'de cumartesi barı yok


@lru_cache(maxsize=1)
def _usdtry_temel() -> tuple[pd.Series, dict]:
    df = oku("usdtry_yahoo_gunluk")
    ist = df["usdtry_ist18"].dropna()
    ham = df["usdtry_gunbasi"].dropna()
    duz = _fx.gunluk_duzelt(ham)
    gecis = ist.index.min()
    eski = duz[duz.index < gecis]
    s = pd.concat([eski, ist]).sort_index()
    s = s[~s.index.duplicated(keep="last")]
    s = s[s.index.dayofweek < 5]
    s.name = "usdtry"
    # cuma tuzağı: geçiş öncesi cumaların değeri hangi bardan geliyor
    cuma = s[(s.index.dayofweek == 4) & (s.index < gecis)]
    cumartesi = set(ham.index[ham.index.dayofweek == 5].normalize())
    pzt = int(sum(1 for t in cuma.index if (t + pd.Timedelta(days=1)) not in cumartesi))
    kun = {"kaynak": "Yahoo Finance USDTRY=X", "gecis": str(gecis.date()),
           "once": "günlük bar, değer bir önceki hafta içi güne (Londra gece yarısı kapanışı)",
           "sonra": "saatlik bardan İstanbul 18:00", "n": int(len(s)),
           "ilk": str(s.index.min().date()), "son": str(s.index.max().date()),
           "cuma_gunu_gecis_oncesi": int(len(cuma)), "cuma_pazartesi_barindan": pzt,
           "cuma_notu": (f"{gecis.date()} öncesinde arşivde cumartesi barı yok: düzeltilmiş günlük seride cuma "
                         "değeri pazartesi barının başındaki (hafta sonu açılışından sonraki) fiyattır ve hafta "
                         f"sonu haberini cumaya yazar ({pzt}/{len(cuma)} cuma). Cuma değeri isteyen ölçüler "
                         "`cuma_dus=True` ile o cumaları boş alır.")}
    return s, kun


def usdtry(cuma_dus: bool = False) -> tuple[pd.Series, dict]:
    """USD/TRY günlük kapanış (Yahoo): saatlik bardan İstanbul 18:00, öncesi
    düzeltilmiş günlük bar. (seri, künye) döner.

    CUMA TUZAĞI. 18.12.2023 öncesinde arşivde cumartesi barı yoktur; düzeltilmiş
    seride cuma değeri PAZARTESİ barının başındaki fiyattır (hafta sonu
    açılışından sonra) — 987 cumanın 987'si (künye `cuma_pazartesi_barindan`).
    Cuma kotasyonu hafta sonu haberini taşır; pazartesi değişimi (cuma etiketi →
    pazartesi etiketi) ise yalnız pazartesi seansıdır. `cuma_dus=True` geçiş
    öncesi cumaların DEĞERİNİ boş (NaN) yapar: haftalık ve aylık örnekleme o
    hafta perşembeyi alır, cuma penceresi kuran olay çalışması o cumayı ölçmez.
    Günlük DEĞİŞİM çerçevesinde aynı bayrak yalnız cuma değişimini boşaltır
    (`tr_gunluk_degisim`)."""
    s, kun = _usdtry_temel()
    s = s.copy()
    kun = dict(kun)
    kun["cuma_dus"] = bool(cuma_dus)
    if cuma_dus:
        s[(s.index.dayofweek == 4) & (s.index < GECIS_YAHOO_CUMA)] = np.nan
    return s, kun


@lru_cache(maxsize=2)
def _usdtry_tcmb(geri_alma: str) -> pd.Series:
    raw = oku("usdtry_tcmb_gunluk")["usdtry_tcmb_valor"].dropna().sort_index()
    if geri_alma == "is_gunu":
        s = raw.copy()
        s.index = s.index - pd.offsets.BDay(1)
    elif geri_alma == "tr_takvim":
        tk = tr_takvim()
        v = raw.index
        ilan = []
        for i, V in enumerate(v):
            if V > tk[0]:
                ilan.append(tk[tk.searchsorted(V) - 1])            # valörden ÖNCEKİ son Türkiye iş günü
            elif i >= 1:
                ilan.append(v[i - 1])                               # takvim öncesi: dizideki bir önceki valör günü
            else:
                ilan.append(pd.NaT)
        s = pd.Series(raw.values, index=pd.DatetimeIndex(ilan))
        s = s[s.index.notna()]
    else:
        raise KeyError(f"geri alma kuralı tanımsız: {geri_alma}")
    s = s[~s.index.duplicated(keep="last")].sort_index()
    if geri_alma == "tr_takvim":
        s = s.drop(index=_tcmb_ilansiz(s))
    s = s[s.index <= CIPA_GUN]
    s.name = "usdtry_tcmb"
    return s


def _tcmb_ilansiz(s: pd.Series) -> pd.DatetimeIndex:
    """Türkiye takviminde TCMB'nin İLAN ETMEDİĞİ yarım günler (arife).

    Ölçüldü (doğrulama turu, 02.10.2026): bayram arifelerinde ve 28 Ekim'de
    (yarım gün) yeni gösterge kuru ilan edilmiyor; arşiv tatil sonrası valöre bir
    önceki ilanı TEKRAR yazıyor. 2011–2026'da 33 arifenin 33'ünde tatil sonrası
    valörün değeri arife valörününkiyle 4 ondalığa kadar birebir aynı (ör.
    15.04.2024 valörü 32,0060 = 09.04.2024 valörü, yani 08.04.2024 ilanı; 09.04
    Ramazan arifesi). Takvimle geri alınınca bu tekrar arife gününe yazılır ve o
    güne SAHTE bir sıfır değişim düşer. Kural: değeri bir önceki Türkiye iş
    gününkiyle birebir aynı olan gün, ardından tatil geliyorsa ya da 28 Ekim ise
    ilansız sayılır ve seriden çıkar (ölçülemeyen boş bırakılır). Tatil öncesi
    TAM iş günündeki ilan (28.03.2025 → 02.04.2025 valörü) değer değiştirdiği için
    korunur. Yalnız takvim dönemi (2011+): öncesinde dört ondalıklı küçük kurlarda
    birebir eşitlik tesadüfen de sık."""
    tk = tr_takvim()
    r = s.reindex(tk)
    sonraki = pd.Series(list(tk[1:]) + [pd.NaT], index=tk)
    hafta_ici = pd.Series(tk + pd.offsets.BDay(1), index=tk)
    tatil_oncesi = (sonraki != hafta_ici) & sonraki.notna()
    ekim28 = pd.Series((tk.month == 10) & (tk.day == 28), index=tk)
    ayni = r.diff().eq(0) & r.notna()
    gun = tk[(ayni & (tatil_oncesi | ekim28)).values]
    return gun[gun.isin(s.index)]


def tcmb_ilansiz_gunler() -> pd.DatetimeIndex:
    """`usdtry_tcmb()`in ilansız saydığı arife günleri (künye ve sınama için)."""
    raw = oku("usdtry_tcmb_gunluk")["usdtry_tcmb_valor"].dropna().sort_index()
    tk = tr_takvim()
    ilan = [tk[tk.searchsorted(V) - 1] for V in raw.index if V > tk[0]]
    s = pd.Series(raw[raw.index > tk[0]].values, index=pd.DatetimeIndex(ilan))
    s = s[~s.index.duplicated(keep="last")].sort_index()
    g = _tcmb_ilansiz(s)
    return g[g <= CIPA_GUN]


def usdtry_tcmb(geri_alma: str = "tr_takvim") -> pd.Series:
    """TCMB gösterge kuru (döviz alış), İLAN gününe yazılmış.

    Dosya VALÖR tarihlidir (ilanın ertesi iş günü). İlan günü, valör gününden
    ÖNCEKİ son TÜRKİYE iş günüdür (`tr_takvim`; 2011 öncesinde takvim yok, orada
    valör dizisinin bir önceki günü — ardışık iki valör günü ardışık iki Türkiye
    iş günüdür). Takvimsiz bir iş günüyle geri almak (`geri_alma="is_gunu"`)
    resmî tatilden önceki ilanı TATİL gününe yazar (02.04.2025 valörlü kur
    01.04.2025 bayramına düşer; ilan 28.03.2025 cuma) ve 2013–2026'da 88 iş
    gününü kursuz bırakır; o sürüm yalnız bu tuzağın ölçümü içindir (olcum_b02).

    ARİFE. Yarım günlerde (bayram arifeleri, 28 Ekim) TCMB ilan etmez; arşiv tatil
    sonrası valöre önceki ilanı tekrar yazar (15.04.2024 valörü = 08.04.2024
    ilanı; 09.04 arifesinde ilan yok). Bu tekrarlar seriden çıkar
    (`_tcmb_ilansiz`, `tcmb_ilansiz_gunler`): arife günü kursuzdur, sıfır
    değişim taşımaz.

    SAAT: ilan 15:30 TSİ'dir ama sabitleme öğleden ÖNCEDİR ve 14:00 kurul
    kararını taşımaz — 13.09.2018: önceki ilan 6,3945, karar günü ilanı 6,3566,
    ertesi gün 6,0659; Yahoo karar günü kapanışı 6,1287 (olcum_b02, tuzak 2).
    Gün içi bir sabitleme olarak DİBS'in "sabah" hizasıyla aynı saattedir."""
    return _usdtry_tcmb(geri_alma).copy()


def donem_sonu_kur(tarihler) -> pd.Series:
    """TCMB gösterge kuru, dönem sonu: dönemin son iş gününde ilan edilen kur,
    yani dönem sonundan SONRAKİ ilk valör günündeki değer. Valörü takvimsiz bir
    iş günü geri almak yılbaşında 31 Aralık ilanını 1 Ocak'a (tatil) yazar ve
    yıl sonu kuru bir gün kayar; dönüşüm bu yüzden valör serisinden yapılır.
    (Türkiye takvimiyle geri alınmış `usdtry_tcmb` serisinin dönem sonu son
    değeriyle aynı sayıdır.)"""
    v = oku("usdtry_tcmb_gunluk")["usdtry_tcmb_valor"].dropna().sort_index()
    tarihler = pd.DatetimeIndex(tarihler)
    j = v.index.searchsorted(tarihler, side="right")
    deg = [float(v.iloc[k]) if k < len(v) else np.nan for k in j]
    return pd.Series(deg, index=tarihler)


# Yahoo EM günlük barı: "Close" günün BAŞINDAKİ fiyattır ve düzeltilir
# (`gunluk_duzelt`). İSTİSNA — MXN'nin ham barı Nisan 2018 öncesinde ZATEN gün
# sonunu taşıyor. ECB referans kuru çaprazına (USD/MXN = EUR/MXN / EUR/USD, 14:15
# Orta Avrupa) karşı ölçüldü: ham barın günlük log değişiminin ECB değişimiyle
# korelasyonu 2010–2017'nin HER yılında −1 gecikmede tepe yapıyor (bar D'nin
# değişimi ECB D+1'le; bu, CNBC New York 17:00 EUR/USD'nin ECB'ye göre örüntüsüdür:
# gün sonu), 2018'den itibaren 0'da (günün başı; düzeltilince −1). Düzey
# yakınlığı da aynı ayda kırılıyor: ham barın ECB'nin ERTESİ günkü
# sabitlemesine en yakın olduğu günlerin payı 2018-03'te 0,48, 2018-04'te 0,15
# (başka bir ölçüyle 0,54 → 0,33). Geçiş günü bu yüzden 2018-04-01'dir; MXN için
# o günden önce düzeltme UYGULANMAZ (uygulanırsa seri bir gün erkene kayar).
# BRL, ZAR ve INR'de böyle bir kırılma ölçülmedi: gecikme örüntüleri sabah/akşam
# saat dilimi farkıyla tutarlı ve dönem boyunca sabit.
EM_GUN_SONU_GECIS = {"mxn": pd.Timestamp("2018-04-01")}


EM_SICRAMA_ESIK = 0.035      # log; sıçrama ve ertesi gün geri dönüş, ikisi de bu eşiğin üstünde


def geri_donen_sicrama(d: pd.Series, esik: float) -> pd.Series:
    """Yalıtılmış bozuk kotasyon maskesi — TEK tanım. `d` günlük DEĞİŞİM serisidir
    (kurda log değişim, getiride bp): bir günün değişimi ve ertesi günün değişimi
    ikisi de `esik`i aşıyor, işaretleri ters ve iki günlük net hareket küçüğünün
    yarısından az → o gün bozuk (True). EM kurları (`_em_kur_temiz`, eşik
    `EM_SICRAMA_ESIK`) ve Bölüm 10'un CNBC sürücü barları (olcum_b10, kur ve getiri
    eşikleri orada ölçülerek) aynı kuralı buradan okur; iki modülde iki kopya
    olsaydı bir gün sessizce ayrışırdı (02.10.2026'da b10 için taşındı)."""
    n = d.shift(-1)
    return ((d.abs() > esik) & (n.abs() > esik) & (np.sign(d) != np.sign(n))
            & ((d + n).abs() < 0.5 * np.minimum(d.abs(), n.abs()))).fillna(False)


@lru_cache(maxsize=8)
def _em_kur_temiz(kod: str) -> tuple[pd.Series, tuple]:
    """Yalıtılmış bozuk kotasyonlar çıkarılmış EM kuru (olcum_b11'de ölçüldü, tuzak 16).

    Kural: bir günün log değişimi ve ertesi günün log değişimi ikisi de eşiği aşıyor,
    işaretleri ters ve iki günlük net hareket küçüğünün yarısından az → o gün bozuk
    sayılır ve seriden çıkar. Eşik ECB referans kurlarına karşı ölçülerek kondu:
    %3,5'te işaretlenen her gün ECB'den %3'ten fazla sapıyor, %3'te gerçek oynak
    günler de yakalanıyor. ZAR'da 14.11.2024, 14.01.2025 ve 16.01.2025 %14–20'lik
    geri dönen sıçramalardır; çıkarılınca 2024 ve 2025'te ECB çaprazıyla günlük
    korelasyon 0,05–0,18'den 0,41–0,56'ya çıkıyor (doğrulama turu)."""
    s = _em_kur(kod)
    m = geri_donen_sicrama(np.log(s).diff(), EM_SICRAMA_ESIK)
    return s[~m], tuple(_iso(t) for t in s.index[m])


def em_kur_temizlik(kod: str) -> list:
    """`em_kur(kod)`un çıkardığı bozuk kotasyon günleri."""
    return list(_em_kur_temiz(kod.lower())[1])


@lru_cache(maxsize=8)
def _em_kur(kod: str) -> pd.Series:
    raw = oku("em_kur_yahoo_gunluk")[f"{kod}_gunbasi"].dropna()
    duz = _fx.gunluk_duzelt(raw)
    g = EM_GUN_SONU_GECIS.get(kod)
    if g is not None:
        ham = raw[(raw.index < g) & (raw.index.dayofweek < 5)]
        s = pd.concat([ham, duz[duz.index >= g]]).sort_index()
        s = s[~s.index.duplicated(keep="last")]
    else:
        s = duz
    s.name = kod
    return s


def em_kur(kod: str, temiz: bool = True) -> pd.Series:
    """EM kuru (BRL, MXN, ZAR, INR; USD karşısında), Yahoo günlük barı, gün sonu
    tarihli (`EM_GUN_SONU_GECIS` istisnası belgede). `temiz=True` (öntanımlı)
    yalıtılmış bozuk kotasyonları çıkarır (`_em_kur_temiz`); ham seri yalnız
    temizliğin kendisini ölçmek içindir.

    CUMA: arşivde EM kurlarının cumartesi barı HİÇ yok (2010–2026, dört kurda 0);
    düzeltilmiş barlarda cuma değeri USD/TRY'nin 18.12.2023 öncesindeki gibi
    pazartesi barının başıdır ve hafta sonunu taşır (MXN'nin 2018-04 öncesi ham
    barı gerçek cuma kapanışıdır). Haftalık ölçüler perşembeyle örnekler (b11);
    ECB çaprazına göre günlük korelasyonun tepe kayması (doğrulama turu,
    2010–2026): MXN 17 yılın 17'sinde aynı (CNBC New York 17:00 EUR/USD'nin
    örüntüsü; düzeltme bütün seriye uygulansaydı 2010–2017 bir gün kayık), BRL
    16/17 (2011'de iki kayma eşit), INR 16/17; ZAR'da iki komşu kaymanın
    korelasyonu yıldan yıla başa baş (tek yönlü bir kırılma yok), 2024–2025'te
    Pearson 0,05–0,18'e düşüyor (Spearman 0,33–0,50: aykırı kotasyonlar; b11 bu
    yüzden temizlenmiş seriyi okur)."""
    kod = kod.lower()
    return (_em_kur_temiz(kod)[0] if temiz else _em_kur(kod)).copy()


# ─────────────────────────────────────────────────────────────── CNBC ve dolar sepeti
TERS_KOTE = ("eur", "gbp", "aud")      # XXX/USD → dolar yönünde işaret çevrilir
DUZ_KOTE = ("chf", "jpy", "cad")       # USD/XXX
SEPET = TERS_KOTE + DUZ_KOTE
# CNBC bozuk kotasyon denetimi. DXY'nin yayımlanmış sabit ağırlıkları (ICE: EUR
# 57,6 · JPY 13,6 · GBP 11,9 · CAD 9,1 · SEK 4,2 · CHF 3,6); SEK arşivde yok, kalan
# beşi yeniden ölçeklenir. Vekil yalnız aynı saatteki iki kaynağı karşılaştırmak
# içindir; dolar ölçüsü eşit ağırlıklı sepettir.
DXY_AGIRLIK = {"eur": 57.6, "jpy": 13.6, "gbp": 11.9, "cad": 9.1, "chf": 3.6}
CNBC_DXY_FARK_ESIGI = 2.5             # %, günlük değişim farkı (meşru azami 1,74; bozuk 3,38)
CNBC_BLOK_AZAMI_GUN = 10              # geri dönüşün aranacağı azami ortak gün


@lru_cache(maxsize=1)
def _cnbc_ham() -> pd.DataFrame:
    c = oku("cnbc_kur_gunluk")
    return c[c.index.dayofweek < 5]                        # hafta sonu barları ayıklanır (479 pazar · 6 cumartesi)


def _dolar_yonu(c: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({f"usd_{k}": (-np.log(c[k]) if k in TERS_KOTE else np.log(c[k])) for k in SEPET})


@lru_cache(maxsize=1)
def _cnbc_denetim() -> tuple[pd.DatetimeIndex, dict]:
    """CNBC kurlarından DXY ağırlıklarıyla kurulan vekil ile Yahoo DXY'nin günlük
    değişimi AYNI ortak günlerde ters işaretle ve eşikten fazla ayrışıp birkaç
    gün içinde geri dönüyorsa, ayrışmadan önceki son ortak günden geri dönüş
    gününe kadarki CNBC günleri bozuk sayılır.

    Ölçüldü (denetim turu, 02.10.2026): EUR/USD 01–03.01.2020'de 1,1774 · 1,1786 ·
    1,1853 yazıyor (öncesi 1,1210, sonrası 1,1158–1,1193); sepetin 02.01 değişimi
    −%0,58, aynı gün DXY +%0,48. Eşik: 2000–2026'da ayrışmanın en büyük meşru
    değeri %1,74 (Kasım 2008), bozuk blok %3,38 ve %3,54; aradaki %1,0–1,7'lik
    çiftlerin kaynağı DXY'nin kendi tekrarlanan kapanışlarıdır. Ortak gün DXY'nin
    de bulunduğu gündür; 01.01.2020'de DXY kotasyonu yok, o gün bloğun içinde
    olduğu için CNBC takviminden ayrıca çıkar."""
    lk = _dolar_yonu(_cnbc_ham()).dropna()
    w = DXY_AGIRLIK
    vek = sum(lk[f"usd_{k}"] * v for k, v in w.items()) / sum(w.values())     # artış = dolar değer kazancı
    ldxy = np.log(oku("yahoo_dxy_vix_gunluk")["dxy"])
    j = pd.concat([vek.rename("v"), ldxy.reindex(lk.index).rename("d")], axis=1, sort=True).dropna()
    fark = (j["v"].diff() - j["d"].diff()) * 100.0
    bay = fark[fark.abs() > CNBC_DXY_FARK_ESIGI]
    bozuk: list = []
    bloklar, donus = [], set()
    gunler = list(bay.index)
    i = 0
    while i < len(gunler) - 1:
        t1, t2 = gunler[i], gunler[i + 1]
        ara = j.index[(j.index >= t1) & (j.index < t2)]
        toplam = float(fark.loc[t1:t2].sum())
        if (np.sign(bay[t1]) != np.sign(bay[t2]) and len(ara) <= CNBC_BLOK_AZAMI_GUN
                and abs(toplam) < 0.5 * min(abs(bay[t1]), abs(bay[t2]))):
            once = j.index[j.index < t1].max()
            blok = lk.index[(lk.index > once) & (lk.index < t2)]
            dlk = (lk.loc[t1] - lk.loc[once]).abs()
            bozuk.extend(blok)
            donus.add(t2)
            bloklar.append({"ilk": str(blok.min().date()), "son": str(blok.max().date()), "geri_donus": str(t2.date()),
                            "kur": str(dlk.idxmax()).replace("usd_", ""), "fark_giris_yuzde": float(bay[t1]),
                            "fark_cikis_yuzde": float(bay[t2]), "blok_toplami_yuzde": toplam,
                            "ortak_gun_disi": [str(t.date()) for t in blok if t not in j.index]})
            i += 2
        else:
            i += 1
    meru = fark.drop(index=[t for t in fark.index if t in set(bozuk) or t in donus])
    rapor = {
        "esik_yuzde": CNBC_DXY_FARK_ESIGI, "cikan_gun": [str(t.date()) for t in bozuk], "bloklar": bloklar,
        "esigi_asan_gun": int(len(bay)), "kalan_azami_fark_yuzde": float(meru.abs().max()),
        "kalan_azami_fark_gunu": str(meru.abs().idxmax().date()), "n_kiyas_gunu": int(fark.notna().sum()),
        "yontem": "CNBC kurlarından DXY ağırlıklarıyla kurulan vekilin günlük değişimi, aynı günün Yahoo DXY "
                  "değişimiyle karşılaştırıldı; eşikten fazla ayrışıp birkaç gün içinde ters işaretle geri "
                  "dönen bloklar bozuk kotasyon sayılıp CNBC takviminden çıkarıldı.",
    }
    return pd.DatetimeIndex(bozuk), rapor


def cnbc_denetimi() -> dict:
    """CNBC bozuk kotasyon denetiminin raporu (çıkan günler adıyla)."""
    return json.loads(json.dumps(_cnbc_denetim()[1]))


@lru_cache(maxsize=1)
def _cnbc_kur() -> pd.DataFrame:
    bozuk, _ = _cnbc_denetim()
    c = _cnbc_ham()
    return c.drop(index=[t for t in bozuk if t in c.index])


def cnbc_kur() -> pd.DataFrame:
    """CNBC G10 kurları (New York 17:00; EUR, GBP, AUD XXX/USD; CHF, JPY, CAD
    USD/XXX), hafta içi, bozuk kotasyon günleri çıkarılmış (`cnbc_denetimi`).
    CNBC kurunu okuyan her ölçü buradan okur."""
    return _cnbc_kur().copy()


@lru_cache(maxsize=1)
def _dolar_sepeti() -> pd.DataFrame:
    lk = _dolar_yonu(_cnbc_kur()).dropna()
    lk["sepet"] = lk[[f"usd_{k}" for k in SEPET]].mean(axis=1)
    return lk


def dolar_sepeti() -> pd.DataFrame:
    """G10 dolar sepeti: altı CNBC kurunun DOLAR YÖNÜNDE logu (`usd_eur` … `usd_cad`;
    EUR, GBP, AUD işareti çevrilir) ve eşit ağırlıklı ortalaması `sepet` (artış
    doların değer kazancı; log, ×100 değil). Satırlar altı kurun hepsinin
    bulunduğu, bozuk kotasyonu çıkarılmış hafta içi günlerdir."""
    return _dolar_sepeti().copy()


@lru_cache(maxsize=1)
def _abd_gunluk() -> pd.DataFrame:
    a = oku("abd_hazine_gunluk")[["us2", "us10"]]
    a = a[a.index.dayofweek < 5]
    df = pd.concat([a, _dolar_sepeti()], axis=1, sort=True).dropna()
    y = oku("yahoo_dxy_vix_gunluk")
    df["dxy"] = np.log(y["dxy"]).reindex(df.index)
    df["vix"] = y["vix"].reindex(df.index)
    return df


def abd_gunluk() -> pd.DataFrame:
    """ABD ortak gün çerçevesi: `us2`, `us10` (%), altı kurun dolar yönünde logu
    ve `sepet` (log), `dxy` (log), `vix`. Satırlar getiri ile altı kurun hepsinin
    bulunduğu hafta içi günlerdir; değişimler bu ortak günler üzerinden alınır
    (getiri ile kur aynı gün aralığını ölçer). Saat: ABD Hazinesi par getirisi
    New York öğleden sonra, CNBC New York 17:00, VIX New York kapanışı."""
    return _abd_gunluk().copy()


def abd_gunluk_degisim() -> pd.DataFrame:
    """`abd_gunluk`un günlük değişimi: `us2_bp`, `us10_bp`, `dolar_yuzde` (sepet),
    `usd_<kur>_yuzde` (dolar yönünde log ×100), `dxy_yuzde`, `vix_puan`."""
    g = _abd_gunluk()
    out = {"us2_bp": g["us2"].diff() * 100.0, "us10_bp": g["us10"].diff() * 100.0,
           "dolar_yuzde": g["sepet"].diff() * 100.0}
    for k in SEPET:
        out[f"usd_{k}_yuzde"] = g[f"usd_{k}"].diff() * 100.0
    out["dxy_yuzde"] = g["dxy"].diff() * 100.0
    out["vix_puan"] = g["vix"].diff()
    return pd.DataFrame(out, index=g.index).iloc[1:]


# ─────────────────────────────────────────────────────────────── Türkiye günlük çerçevesi
TR_DUGUM = ("n3a", "n2y", "n5y")


def tr_gunluk(hiza: str = "gun_sonu", dugumler=TR_DUGUM, kur: bool = True, tcmb: bool = False,
              cuma_dus: bool = False, kayma: int | None = None) -> pd.DataFrame:
    """Türkiye günlük DÜZEY çerçevesi, Türkiye iş günü takviminde, DİBS'in
    kapsamında: DİBS düğümleri (%, `dibs(hiza)`), USD/TRY (Yahoo) ve istenirse
    TCMB gösterge kuru (ilan günü). Eksik gün boştur; bütün sütunların bulunduğu
    ORTAK günler isteyen ölçü `.dropna()` alır (haftalık örnekleme bütün
    sütunları aynı günden okusun diye)."""
    d = dibs(hiza, dugumler, kayma)
    if kur:
        s, _ = usdtry(cuma_dus=cuma_dus)
        d["usdtry"] = s.reindex(d.index)
    if tcmb:
        d["usdtry_tcmb"] = usdtry_tcmb().reindex(d.index)
    return d


def tr_gunluk_degisim(hiza: str = "gun_sonu", dugumler=TR_DUGUM, kur: bool = True, tcmb: bool = True,
                      cuma_dus: bool = False, kayma: int | None = None) -> pd.DataFrame:
    """Türkiye günlük DEĞİŞİM çerçevesi: Türkiye iş günü takviminde, her sütun
    kendi değişimiyle — DİBS düğümleri baz puan, USD/TRY ve TCMB kuru log ×100.
    Ardışık iki takvim gününün ikisinde de değeri olan sütun o günün değişimini
    taşır; aynı satırdaki sütunlar AYNI takvim aralığını ölçer.

    `cuma_dus=True`: 18.12.2023 öncesi CUMA günlerinin USD/TRY değişimi boşalır
    (değer pazartesi barının başıdır, değişim hafta sonunu taşır); pazartesi
    değişimi korunur, çünkü cuma etiketinden pazartesi etiketine olan hareket
    yalnız pazartesi seansıdır (`usdtry`)."""
    d = dibs(hiza, dugumler, kayma)
    out = {c: d[c].diff() * 100.0 for c in d.columns}
    if kur:
        s, _ = usdtry()
        dk = np.log(s.reindex(d.index)).diff() * 100.0
        if cuma_dus:
            dk[(dk.index.dayofweek == 4) & (dk.index < GECIS_YAHOO_CUMA)] = np.nan
        out["usdtry"] = dk
    if tcmb:
        out["usdtry_tcmb"] = np.log(usdtry_tcmb().reindex(d.index)).diff() * 100.0
    return pd.DataFrame(out, index=d.index)


# ─────────────────────────────────────────────────────────────── faiz kotasyonları
def bilesik(r, kotasyon: str):
    """Kote edilen faizi (%, yıllık) YILLIK EFEKTİF (bileşik) faize (%) çevirir.

      "gecelik"         basit gecelik (ACT/365; TLREF, gecelik faiz): (1 + r/365)^365 − 1
      "haftalik"        bir hafta vadeli repo, basit: (1 + r/52)^52 − 1
      "repo_7_365"      aynı repo, 7/365 gün sayımıyla: (1 + r·7/365)^(365/7) − 1
                        (DİBS panosunun çevrimi; olcum_b05 iki çevrimi karşılaştırır)
      "yariyillik"      altı aylık kuponlu par getiri (ABD Hazinesi): (1 + r/200)^2 − 1
      "yillik_efektif"  zaten yıllık bileşik (Brezilya Selic, DİBS sıfır kuponlu): r
    Seri, dizi ya da tek sayı kabul eder."""
    r = r / 100.0
    if kotasyon == "gecelik":
        y = (1 + r / 365) ** 365 - 1
    elif kotasyon == "haftalik":
        y = (1 + r / 52) ** 52 - 1
    elif kotasyon == "repo_7_365":
        y = (1 + r * 7 / 365) ** (365 / 7) - 1
    elif kotasyon == "yariyillik":
        y = (1 + r / 2) ** 2 - 1
    elif kotasyon == "yillik_efektif":
        y = r
    else:
        raise KeyError(f"faiz kotasyonu tanımsız: {kotasyon}")
    return y * 100.0


def aylik_log_tasima(i, kotasyon: str = "basit"):
    """Yıllık faizin (%) bir aylık LOG taşıması (%, log ×100).

    TEK kural: aylık taşıma, kotasyonun bir aylık getirisinin log karşılığıdır.
      "basit"  kısa vadeli basit oranlar (politika faizleri, gecelik ve bir haftalık
               repo, ABD politika faizi): i/12. Birinci derece yaklaşımdır; gecelik
               faizin günlük bileşik aylık log birikimiyle farkı medyanda 0,0006
               puan, kriz ayında en çok 0,18 puan (olcum_b11, tuzak 3).
      öbürleri 100·ln(1 + bilesik(i, kotasyon)/100)/12 — tam log taşıma; yıllık
               efektif kote edilen Brezilya Selic'i için ln(1 + i)/12 (i/12, Selic'in
               aylık log taşımasını yılda ≈0,5 puan büyütürdü)."""
    if kotasyon == "basit":
        return i / 12.0
    return 100.0 * np.log1p(bilesik(i, kotasyon) / 100.0) / 12.0


# ─────────────────────────────────────────────────────────────── kadran
KADRAN_ADI_DM = {"politika": "faiz ↑, para değer kazanır", "prim": "faiz ↑, para değer kaybeder",
                 "gevseme": "faiz ↓, para değer kaybeder", "guvenli_liman": "faiz ↓, para değer kazanır"}
KADRAN_ADI_EM = {"politika": "faiz ↑, para değer kazanır", "prim": "faiz ↑, para değer kaybeder",
                 "gevseme": "faiz ↓, para değer kaybeder", "prim_dusus": "faiz ↓, para değer kazanır"}


def kadran(dfaiz, dpara_deger, dordu: str = "guvenli_liman"):
    """Faiz × para değeri kadranı. `dpara_deger`: artış YEREL PARANIN DEĞER
    KAZANCI. politika (faiz ↑, para ↑) · prim (faiz ↑, para ↓) · gevşeme (faiz ↓,
    para ↓) · dördüncü kadran (faiz ↓, para ↑): DM'de "guvenli_liman", EM'de
    "prim_dusus". Sıfır hareket "sifir". Seri verilirse Seri, sayı verilirse dizge."""
    tek = np.isscalar(dfaiz) and np.isscalar(dpara_deger)
    y = pd.Series([dfaiz]) if tek else pd.Series(dfaiz)
    p = pd.Series([dpara_deger]) if tek else pd.Series(dpara_deger)
    k = np.select([(y > 0) & (p > 0), (y > 0) & (p < 0), (y < 0) & (p < 0), (y < 0) & (p > 0)],
                  ["politika", "prim", "gevseme", dordu], "sifir")
    if tek:
        return str(k[0])
    return pd.Series(k, index=y.index)


# ─────────────────────────────────────────────────────────────── istatistik
def hac(y, X, gecikme: int | None = None, sabit: bool = True) -> dict:
    """OLS, Newey–West (Bartlett) HAC standart hatası. X tek dizi ya da matris.

    Döner: b (katsayılar, sabit ilk), se, t, r2, n, gecikme."""
    y = np.asarray(y, dtype=float)
    X = np.asarray(X, dtype=float)
    if X.ndim == 1:
        X = X[:, None]
    m = np.isfinite(y) & np.all(np.isfinite(X), axis=1)
    y, X = y[m], X[m]
    if sabit:
        X = np.column_stack([np.ones(len(y)), X])
    n, k = X.shape
    if n <= k + 2:
        return {"n": int(n), "yetersiz": True}
    if gecikme is None:
        gecikme = otomatik_gecikme(n)
    XtX_inv = np.linalg.inv(X.T @ X)
    b = XtX_inv @ X.T @ y
    e = y - X @ b
    S = (X * e[:, None]).T @ (X * e[:, None])
    for L in range(1, gecikme + 1):
        w = 1 - L / (gecikme + 1)
        G = (X[L:] * e[L:, None]).T @ (X[:-L] * e[:-L, None])
        S += w * (G + G.T)
    V = XtX_inv @ S @ XtX_inv
    se = np.sqrt(np.diag(V))
    r2 = 1 - (e @ e) / ((y - y.mean()) @ (y - y.mean())) if n > 1 else float("nan")
    return {"b": b.tolist(), "se": se.tolist(), "t": (b / se).tolist(), "r2": float(r2),
            "n": int(n), "gecikme": int(gecikme)}


def otomatik_gecikme(n: int) -> int:
    """Newey–West gecikmesinin kural değeri ⌊4·(n/100)^(2/9)⌋."""
    return int(math.floor(4 * (n / 100) ** (2 / 9)))


def reg(y: pd.Series, X, gecikme: int | None = None) -> dict:
    """Tek ya da çok değişkenli Newey–West regresyonu, örneklem tarihleriyle.
    Döner: n, ilk, son, sabit, sabit_t, b, se, t (açıklayıcı başına liste), r2,
    gecikme; gözlem yetersizse kurulmadı."""
    if isinstance(X, pd.Series):
        X = X.to_frame()
    d = pd.concat([y.rename("_y"), X], axis=1, sort=True).dropna()
    r = hac(d["_y"].values, d.drop(columns="_y").values, gecikme=gecikme)
    if r.get("yetersiz"):
        return {"n": r["n"], **kurulmadi("regresyon için gözlem yetersiz")}
    return {"n": r["n"], "ilk": _iso(d.index.min()), "son": _iso(d.index.max()),
            "sabit": r["b"][0], "sabit_t": r["t"][0], "b": r["b"][1:], "se": r["se"][1:], "t": r["t"][1:],
            "r2": r["r2"], "gecikme": r["gecikme"]}


OOS_ASGARI = 10
KIYAS_ADI = {"sifir": "rastgele yürüyüş (değişim sıfır)", "ortalama": "koşulsuz ortalama"}


def oos_kiyas(y: pd.Series, x: pd.Series, ilk_pencere: int, kiyas: str = "ortalama",
              ambargo: int = 1, gecikme: int | None = None) -> dict:
    """Genişleyen pencerede y_t = a + b·x_t tahmini (x_t bilinen) ile saf kıyas
    (koşulsuz ortalama ya da sıfır = rastgele yürüyüşün değişimi) arasında
    örneklem dışı karesel hata. Oran < 1 modelin lehine.

    AMBARGO. Eğitim, hedefi t anında GERÇEKLEŞMİŞ satırlarla kurulur: satır s,
    s + ambargo ≤ t ise (ambargo = 1 bütün geçmiş satırlar). Hedef "sonraki h
    dönemin değişimi" olduğunda ambargo = h olmalıdır; yoksa eğitim, t anında
    henüz gerçekleşmemiş hedefleri görür ve oran olduğundan iyi çıkar (olcum_b08:
    aynı sınamada 0,99 sızıntılı, 1,20 ambargolu).
    Diebold–Mariano t'si eşli karesel hata farkının Newey–West ortalamasıdır
    (gecikme verilmezse kural değeri; ambargo > 1 iken en az ambargo); eksi t
    modelin lehine. En az `OOS_ASGARI` tahmin yoksa kurulmadı döner."""
    d = pd.concat([y.rename("y"), x.rename("x")], axis=1, sort=True).dropna()
    e_m, e_k = [], []
    for t in range(ilk_pencere, len(d)):
        egit = d.iloc[: t - ambargo + 1]
        if len(egit) < OOS_ASGARI:
            continue
        X = np.column_stack([np.ones(len(egit)), egit["x"].values])
        b = np.linalg.lstsq(X, egit["y"].values, rcond=None)[0]
        tah = b[0] + b[1] * d["x"].iloc[t]
        kiy = egit["y"].mean() if kiyas == "ortalama" else 0.0
        e_m.append((d["y"].iloc[t] - tah) ** 2)
        e_k.append((d["y"].iloc[t] - kiy) ** 2)
    if len(e_m) < OOS_ASGARI:
        return kurulmadi("örneklem dışı sınama için en az on tahmin gerekir", n=int(len(e_m)),
                         kiyas=KIYAS_ADI[kiyas])
    e_m, e_k = np.array(e_m), np.array(e_k)
    fark = e_m - e_k
    if gecikme is None:
        gecikme = otomatik_gecikme(len(fark))
    if ambargo > 1:
        gecikme = max(int(gecikme), int(ambargo))
    dm = hac(fark, np.zeros((len(fark), 0)), gecikme=gecikme, sabit=True)
    return {"n": int(len(e_m)), "mse_oran": _f(e_m.mean() / e_k.mean()) if e_k.mean() else None,
            "dm_t": _f((dm.get("t") or [None])[0]), "kiyas": KIYAS_ADI[kiyas],
            "ilk": _iso(d.index[ilk_pencere]), "ambargo": int(ambargo), "dm_gecikme": int(gecikme)}


def oos_takimi(y: pd.Series, x: pd.Series, ilk_pencere: int, ufuk: int = 1,
               dm_gecikme: int | None = None, sizinti: bool = False) -> dict:
    """İki saf kıyas birlikte: {"ortalama": …, "sifir": …}, ambargo = ufuk. Hüküm
    bu ikisinden kurulur (`takim_oranlari`). `sizinti=True` ve ufuk > 1 iken
    ambargosuz eşleri de yazılır ("…_ambargosuz"): sızıntının büyüklüğü, hükme
    girmez."""
    out = {k: oos_kiyas(y, x, ilk_pencere, k, ambargo=ufuk, gecikme=dm_gecikme) for k in ("ortalama", "sifir")}
    if sizinti and ufuk > 1:
        for k in ("ortalama", "sifir"):
            out[f"{k}_ambargosuz"] = oos_kiyas(y, x, ilk_pencere, k, ambargo=1, gecikme=dm_gecikme)
    return out


def takim_oranlari(takim: dict) -> list:
    """Hükme giren iki oran (koşulsuz ortalama ve sıfır kıyası, ambargo = ufuk)."""
    return [takim.get(k, {}).get("mse_oran") for k in ("ortalama", "sifir")]


def hukum(t: float | None, oranlar: list) -> str:
    """Hüküm — TEK tanım (Bloomberg HRA 6.1): "ölçülü" ancak |t| ≥ 2 VE verilen
    örneklem dışı karesel hata oranlarının HEPSİ < 1 (koşulsuz ortalama ve sıfır
    kıyası; ambargo = ufuk) ise; oran yoksa ya da biri kurulamadıysa "tarif
    edici". Yalnız sıfıra karşı sınanınca sürüklenen bir seride (sürünen USD/TRY)
    sabit terim tek başına kıyası yener (olcum_b03 tuzak 10, olcum_b10 tuzak 7)."""
    gecti = (t is not None and math.isfinite(t) and abs(t) >= 2 and len(oranlar) > 0
             and all(o is not None and o < 1 for o in oranlar))
    return "ölçülü" if gecti else "tarif edici"


def loo_egim(y: pd.Series, x: pd.Series) -> dict:
    """Birini dışarıda bırakma: her gözlem tek tek atılınca EKK eğiminin aralığı
    ve eğimi en çok oynatan gözlem (kapalı biçim, döngüsüz)."""
    xv, yv = np.asarray(x, float), np.asarray(y, float)
    n = len(xv)
    sx, sy, sxx, sxy = xv.sum(), yv.sum(), (xv * xv).sum(), (xv * yv).sum()
    m = n - 1
    pay = m * (sxy - xv * yv) - (sx - xv) * (sy - yv)
    payda = m * (sxx - xv * xv) - (sx - xv) ** 2
    with np.errstate(divide="ignore", invalid="ignore"):
        b = np.where(payda > 0, pay / payda, np.nan)
    b_tam = (n * sxy - sx * sy) / (n * sxx - sx * sx)
    if not np.isfinite(b).any():
        return kurulmadi("açıklayıcı değişken tek gözlem dışında sabit")
    j = int(np.nanargmax(np.abs(b - b_tam)))
    return {"egim_min": _f(np.nanmin(b)), "egim_max": _f(np.nanmax(b)),
            "en_etkili_gozlem": _iso(x.index[j]), "o_gozlemsiz_egim": _f(b[j])}


def regresyon(y: pd.Series, x: pd.Series, ilk_pencere: int | None = None,
              asgari_bilgili: int | None = None, ufuk: int = 1, gecikme: int | None = None,
              dm_gecikme: int | None = None) -> dict:
    """y = a + b·x, Newey–West; örneklem dışı genişleyen pencere kıyası; hüküm.

    n < 10 ise vaka tablosu (yalnız noktalar, t yazılmaz). Örneklem dışı kıyas
    İKİ saf ölçüte karşı yapılır: rastgele yürüyüş (değişim sıfır; anahtar "oos")
    ve koşulsuz ortalama ("oos_ortalama"). Hüküm `hukum`: |t| ≥ 2 ve İKİ oran da
    < 1 (en az on tahminle) birlikte yoksa "tarif edici".

    `ufuk` h: hedef örtüşen h dönemlik bir değişimse (ör. sonraki 12 ay) örneklem
    dışı eğitim h dönem AMBARGOLANIR ve hem regresyonun hem Diebold–Mariano
    t'sinin Newey–West gecikmesi en az h'dir (`oos_kiyas`).

    `asgari_bilgili`: açıklayıcı değişkeni çoğunlukla SIFIR olan seride (anket
    sürprizi, karar değişimi) eğimi yalnız sıfırdan farklı gözlemler tanımlar;
    onların sayısı bu eşiğin altındaysa satır yine vaka tablosudur (19 kararın
    6'sında sürpriz olan bir dönemin t'si altı gözlemin t'sidir)."""
    d = pd.concat([y.rename("y"), x.rename("x")], axis=1, sort=True).dropna()
    n = len(d)
    out = {"n": int(n), "ilk": _iso(d.index.min()) if n else None, "son": _iso(d.index.max()) if n else None}
    if ufuk > 1:
        out["ufuk"] = int(ufuk)
    if asgari_bilgili is not None:
        nb = int((d["x"].abs() > 1e-9).sum())
        out["n_bilgili"] = nb
        if nb < asgari_bilgili and n >= 10:
            out.update({"durum": "vaka tablosu",
                        "not": f"eğimi tanımlayan sıfırdan farklı gözlem {nb}: test istatistiği yazılmaz",
                        "noktalar": [[_iso(t), _f(r.x), _f(r.y)] for t, r in d.iterrows() if abs(r.x) > 1e-9]})
            return out
    if n < 10:
        out.update({"durum": "vaka tablosu", "not": "on gözlemden az: test istatistiği yazılmaz",
                    "noktalar": [[_iso(t), _f(r.x), _f(r.y)] for t, r in d.iterrows()]})
        return out
    if float(d["x"].std()) == 0.0:
        out.update(kurulmadi("açıklayıcı değişken bu dönemde hiç değişmiyor"))
        return out
    g = gecikme
    if ufuk > 1:
        g = max(otomatik_gecikme(n) if g is None else int(g), int(ufuk))
    r = hac(d["y"].values, d["x"].values, gecikme=g)
    if r.get("yetersiz"):
        out.update(kurulmadi("regresyon için gözlem yetersiz"))
        return out
    out.update({"sabit": r["b"][0], "egim": r["b"][1], "se": r["se"][1], "t": r["t"][1],
                "r2": r["r2"], "gecikme": r["gecikme"],
                "korelasyon": _f(np.corrcoef(d["x"], d["y"])[0, 1])})
    ip = ilk_pencere if ilk_pencere is not None else max(10, n // 2)
    tk = oos_takimi(d["y"], d["x"], ip, ufuk=ufuk, dm_gecikme=dm_gecikme)
    out["oos"] = tk["sifir"]
    out["oos_ortalama"] = tk["ortalama"]
    out["hukum"] = hukum(out["t"], takim_oranlari(tk))
    out["birini_disarida_birak"] = loo_egim(d["y"], d["x"])
    return out


# ─────────────────────────────────────────────────────────────── olay kapısı
OLAY_PENCERE = 2
OLAY_RASTGELE_K = 1000
OLAY_TOHUM = 20261002


def olay_profili(degisim: pd.Series, olaylar, pencere: int = OLAY_PENCERE) -> dict:
    """Olay günlerinin −k…+k iş günü kaymasında |Δ| ortalaması ve sıradan
    günlerin |Δ| ortalamasına oranı (plasebo profili). Tepe 0'da değilse
    tarih sözleşmesi kaymıştır; olay çalışması kurulmaz."""
    s = degisim.dropna()
    idx = s.index
    poz = []
    for o in pd.DatetimeIndex(olaylar):
        j = idx.searchsorted(o)
        if j < len(idx) and idx[j] == o:
            poz.append(j)
    poz = np.array(poz, dtype=int)
    olay_kume = set()
    for p in poz:
        for k in range(-pencere, pencere + 1):
            olay_kume.add(p + k)
    sakin = np.array([i for i in range(len(s)) if i not in olay_kume])
    taban = float(np.nanmean(np.abs(s.values[sakin]))) if len(sakin) else float("nan")
    prof = {}
    for k in range(-pencere, pencere + 1):
        p = poz + k
        p = p[(p >= 0) & (p < len(s))]
        prof[k] = float(np.nanmean(np.abs(s.values[p]))) / taban if len(p) and taban else None
    tepe = max(prof, key=lambda k: prof[k] if prof[k] is not None else -1)
    return {"n_olay": int(len(poz)), "taban_abs": taban, "oran": {str(k): v for k, v in prof.items()},
            "tepe": int(tepe), "tepe_sifirda": bool(tepe == 0)}


def kapi_hukmu(prof: dict) -> bool:
    """Temel kapı: plasebo profilinin tepesi sıfırda VE oran[0] öbür kaymaların en büyüğünü aşıyor."""
    o = prof.get("oran", {})
    o0 = o.get("0")
    oteki = [v for k, v in o.items() if k != "0" and v is not None]
    if o0 is None or not oteki:
        return False
    return bool(prof.get("tepe") == 0 and o0 > max(oteki))


def _konumlar(s: pd.Series, olaylar: pd.DatetimeIndex) -> np.ndarray:
    idx = s.index
    olaylar = pd.DatetimeIndex(olaylar)
    j = idx.searchsorted(olaylar)
    ok = (j < len(idx))
    j = j[ok]
    return j[idx[j] == olaylar[ok]]


def _hizli_profil(a: np.ndarray, poz: np.ndarray, pencere: int = OLAY_PENCERE,
                  ek_maske: np.ndarray | None = None) -> np.ndarray:
    """`olay_profili` ile aynı hesap, konumlar üzerinden (rastgele kümeler için).
    `ek_maske`: tabandan ayrıca çıkarılacak günler — rastgele kümelerde GERÇEK olay
    pencereleri: gerçek profilin tabanı olay pencerelerinin dışındaki sıradan
    günlerdir, rastgele kümeninki de öyle olmalı (olcum_b02, tuzak 9)."""
    n = len(a)
    maske = np.zeros(n, dtype=bool)
    for k in range(-pencere, pencere + 1):
        p = poz + k
        maske[p[(p >= 0) & (p < n)]] = True
    if ek_maske is not None:
        maske = maske | ek_maske
    taban = a[~maske].mean()
    out = np.empty(2 * pencere + 1)
    for i, k in enumerate(range(-pencere, pencere + 1)):
        p = poz + k
        p = p[(p >= 0) & (p < n)]
        out[i] = a[p].mean() / taban
    return out


def rastgele_profil(s: pd.Series, olaylar, k_tohum: int, gun_eslemeli: bool = True,
                    n_olay: int | None = None, pencere: int = OLAY_PENCERE, k: int = OLAY_RASTGELE_K) -> dict:
    """Olay pencerelerinin (±pencere) DIŞINDAKİ günlerden `k` rastgele gün kümesi
    (tohum `OLAY_TOHUM + k_tohum`). `gun_eslemeli`: kümenin haftanın günü
    bileşimi olay günlerininkiyle aynı (PPK'ların ≈%78'i perşembe; +1 kayması
    çoğunlukla cumadır ve bazı serilerde cuma |Δ| yapısal olarak büyük — olcum_b02
    tuzak 5). Kapalıysa düzgün dağılımlı küme."""
    s = s.dropna()
    a = np.abs(s.values)
    poz = _konumlar(s, pd.DatetimeIndex(olaylar))
    yasak = np.zeros(len(s), dtype=bool)
    for kk in range(-pencere, pencere + 1):
        p = poz + kk
        yasak[p[(p >= 0) & (p < len(s))]] = True
    aday = np.flatnonzero(~yasak)
    aday = aday[(aday >= pencere) & (aday < len(s) - pencere)]
    gun = s.index.dayofweek.values
    rng = np.random.default_rng(OLAY_TOHUM + k_tohum)
    if gun_eslemeli and len(poz):
        sayim = {w: int((gun[poz] == w).sum()) for w in range(5)}
        havuz = {w: aday[gun[aday] == w] for w in range(5)}
        if any(len(havuz[w]) < c for w, c in sayim.items()):
            gun_eslemeli = False
    n = int(n_olay if n_olay is not None else len(poz))

    def cek() -> np.ndarray:
        if gun_eslemeli and len(poz):
            return np.sort(np.concatenate([rng.choice(havuz[w], size=c, replace=False)
                                           for w, c in sayim.items() if c]))
        return np.sort(rng.choice(aday, size=n, replace=False))

    prof = np.empty((k, 2 * pencere + 1))
    for i in range(k):
        prof[i] = _hizli_profil(a, cek(), pencere, ek_maske=yasak)
    o0 = prof[:, pencere]
    oteki = np.delete(prof, pencere, axis=1).max(axis=1)
    return {"oran0": o0, "fark": o0 - oteki, "kapi": (prof.argmax(axis=1) == pencere) & (o0 > oteki),
            "ort_profil": prof.mean(axis=0), "ornek_kume": s.index[cek()], "gun_eslemeli": bool(gun_eslemeli)}


def donem_disi(s: pd.Series, olaylar: pd.DatetimeIndex, donem: tuple = YONETILEN,
               pencere: int = OLAY_PENCERE) -> tuple[pd.Series, pd.DatetimeIndex, int]:
    """Seriden bir dönemi (günleri ve olayları) çıkarır. Pencere konumla kaydığı
    için çıkarılan boşluğun ÜSTÜNDEN atlayan bir olay penceresi kalırsa o olay da
    düşer (sayısı döner); bayram boşlukları olağan seride de var, onlar düşmez."""
    a, b = pd.Timestamp(donem[0]), pd.Timestamp(donem[1])
    s2 = s[(s.index < a) | (s.index > b)]
    olaylar = pd.DatetimeIndex(olaylar)
    ev = olaylar[((olaylar < a) | (olaylar > b)) & olaylar.isin(s2.index)]
    idx = s2.index
    tut, dusen = [], 0
    for e in ev:
        p = idx.get_loc(e)
        sol = idx[max(p - pencere, 0)]
        sag = idx[min(p + pencere, len(idx) - 1)]
        if (e < a and sag > b) or (e > b and sol < a):
            dusen += 1
            continue
        tut.append(e)
    return s2, pd.DatetimeIndex(tut), dusen


def olay_kapisi(degisim: pd.Series, olaylar, guclu: bool = True, pencere: int = OLAY_PENCERE,
                k_tohum: int = 0, ilk: str | None = None, son: str | None = None,
                haric: tuple | None = None, yalniz: tuple | None = None) -> dict:
    """Dersin KANONİK olay kapısı (olcum_b02'de ölçüldü). Bir olay çalışması
    ancak bu kapı geçerse kurulur.

    Örneklem olay listesinin kapsadığı dönemle sınırlanır (listede olmayan eski
    olaylar sıradan gün sayılmasın; ilk olaydan 10 gün önce, son olaydan 10 gün
    sonra); `ilk`/`son` ayrıca keser. `haric` (ör. `YONETILEN`) bir dönemi
    çıkarır — kur serilerinde yönetilen kur dönemi havuza girmez; `yalniz`
    yalnız o dönemin içini ölçer.

      kapi        temel kural: plasebo profilinin tepesi olay gününde ve oran[0]
                  öbür dört kaymanın en büyüğünü aşıyor (rastgele geçme olasılığı
                  ≈ %15–22: tepe beş kaymadan birine düşer);
      kapi_guclu  ayrıca oran[0], haftanın günü bileşimi aynı 1.000 rastgele gün
                  kümesinin (tabanları da olay pencerelerinin dışında) %95'ini aşıyor;
      gecti       `guclu` ise kapi_guclu, değilse kapi.
    SAAT çağıranın sorumluluğudur: seri, olay saatini doğru güne yazan hizayla
    verilir (DİBS için `DIBS_KAYMA`: 14:00 kararı "gun_sonu" hizasında olay gününe
    düşer). olcum_b02.kapi(seri, olay, guclu=True) tablo satırlarında saati ayrıca
    sınar."""
    s = degisim.dropna()
    olaylar = pd.DatetimeIndex(olaylar)
    if len(olaylar):
        k_ilk = olaylar.min() - pd.Timedelta(days=10)
        k_son = olaylar.max() + pd.Timedelta(days=10)
        ilk = str(max(k_ilk, pd.Timestamp(ilk)).date()) if ilk else str(k_ilk.date())
        son = str(min(k_son, pd.Timestamp(son)).date()) if son else str(k_son.date())
    if ilk or son:
        s = s.loc[ilk:son]
        olaylar = olaylar[(olaylar >= s.index.min()) & (olaylar <= s.index.max())]
    dusen = 0
    if haric is not None:
        s, olaylar, dusen = donem_disi(s, olaylar, haric, pencere)
    elif yalniz is not None:
        s = s.loc[pd.Timestamp(yalniz[0]):pd.Timestamp(yalniz[1])]
        olaylar = olaylar[(olaylar >= s.index.min()) & (olaylar <= s.index.max())]
    prof = olay_profili(s, olaylar, pencere)
    poz = _konumlar(s, olaylar)
    out = {"n_olay": prof["n_olay"], "n_olay_listede": int(len(olaylar)), "oran": prof["oran"],
           "tepe": prof["tepe"], "taban_abs": prof["taban_abs"],
           "ilk": _iso(s.index.min()) if len(s) else None, "son": _iso(s.index.max()) if len(s) else None,
           "donem_siniri_dusen_olay": int(dusen)}
    o = prof["oran"]
    if not len(poz) or any(v is None for v in o.values()):
        out.update({"kapi": False, "kapi_guclu": False, "gecti": False})
        return out
    hz = _hizli_profil(np.abs(s.values), poz, pencere)
    resmi = np.array([o[str(k)] for k in range(-pencere, pencere + 1)], dtype=float)
    assert np.allclose(hz, resmi, rtol=1e-10, atol=1e-12), "hızlı profil ortak profilden ayrışıyor"
    oteki = max(v for k, v in o.items() if k != "0")
    k_gecer = kapi_hukmu(prof)
    out.update({"kapi": k_gecer, "oran0": float(o["0"]), "oteki_azami": float(oteki),
                "oran0_fazlasi": float(o["0"] - oteki)})
    if guclu:
        rd = rastgele_profil(s, olaylar, k_tohum, pencere=pencere)
        K = len(rd["oran0"])
        p0 = float((1 + (rd["oran0"] >= o["0"]).sum()) / (1 + K))
        pf = float((1 + (rd["fark"] >= o["0"] - oteki).sum()) / (1 + K))
        ort = {str(k): float(v) for k, v in zip(range(-pencere, pencere + 1), rd["ort_profil"])}
        fazla = {kk: float(o[kk] / ort[kk]) for kk in o}
        # Monte Carlo hatası: p, K rastgele kümeden tahmin edilir; hata payı içinde
        # 0,05'e değen p tohuma bağlıdır (20 tohumda PPK × 1 yıllık 9/20 geçiyor) —
        # hüküm değişmez, "sınırda" diye işaretlenir.
        p_hata = float(math.sqrt(p0 * (1 - p0) / K))
        out.update({"p_rastgele_hata": p_hata, "guclu_sinirda": bool(k_gecer and abs(p0 - 0.05) < 2 * p_hata)})
        out.update({"kapi_guclu": bool(k_gecer and p0 < 0.05), "p_rastgele_oran0": p0,
                    "p_rastgele_kapi_farki": pf, "kapi_rastgele_gecme_orani": float(rd["kapi"].mean()),
                    "rastgele_ort_profil": ort, "gun_etkisinden_arindirilmis": fazla,
                    "arindirilmis_tepe": int(max(fazla, key=lambda kk: fazla[kk])),
                    "gun_eslemeli_kiyas": rd["gun_eslemeli"]})
    out["gecti"] = bool(out.get("kapi_guclu") if guclu else k_gecer)
    return out


def kapi_ozeti(k: dict) -> dict:
    """Kapı sonucunun ölçüm dosyasına yazılan kompakt hâli."""
    alan = ("n_olay", "oran", "tepe", "kapi", "kapi_guclu", "p_rastgele_oran0", "guclu_sinirda", "gecti",
            "donem_siniri_dusen_olay")
    return {a: k[a] for a in alan if a in k}


def kapi_sebebi(k: dict) -> str:
    """Kapıdan geçmeyen satırın okur dilinde sebebi (eksi U+2212)."""
    if k.get("tepe") != 0:
        return (f"plasebo profilinin tepesi olay gününde değil ({k['tepe']:+d} iş gününde); ".replace("-", "−")
                + "olay penceresi kurulmaz")
    if not k.get("kapi"):
        return "olay günü oranı komşu kaymaları aşmıyor; olay penceresi kurulmaz"
    ek = ("; sonuç sınırda: rastgele kıyasın tahmin hatası içinde" if k.get("guclu_sinirda") else "")
    return ("olay günü oranı haftanın günü eşlemeli rastgele kümelerin %95'ini aşmıyor" + ek
            + "; olay penceresi kurulmaz")


# ─────────────────────────────────────────────────────────────── kalıcılık
def ar1(s: pd.Series) -> float:
    x = np.asarray(s.dropna(), dtype=float)
    x = x - x.mean()
    return float((x[1:] @ x[:-1]) / (x[:-1] @ x[:-1]))


def yari_omur(rho: float) -> float | None:
    if rho is None or not (0 < rho < 1):
        return None
    return float(math.log(0.5) / math.log(rho))


def ar1_medyan_yansiz(s: pd.Series, tohum: int = 20261002, deneme: int = 400,
                      izgara: np.ndarray | None = None) -> dict:
    """Andrews (1993) ruhunda medyan-yansız AR(1): ρ ızgarasında aynı uzunlukta
    yapay seri üretilir, OLS kestirimlerinin MEDYANI gözlenen ρ̂'ya eşit olan
    ρ seçilir. %90 aralığı aynı ızgaradan (5. ve 95. yüzdelik ters çevrilir).
    Üst uç 1'e dayanırsa yarı ömür üst sınırı SONSUZDUR ve öyle yazılır."""
    x = np.asarray(s.dropna(), dtype=float)
    n = len(x)
    rho_hat = ar1(pd.Series(x))
    rng = np.random.default_rng(tohum)
    izgara = izgara if izgara is not None else np.linspace(0.50, 1.0, 101)
    med, q05, q95 = [], [], []
    for r in izgara:
        # denemeler bir matrisin satırlarıdır: döngü yalnız zaman ekseninde
        e = rng.standard_normal((deneme, n))
        y = np.empty((deneme, n))
        y[:, 0] = e[:, 0] / math.sqrt(max(1 - r * r, 1e-6)) if r < 1 else e[:, 0]
        for i in range(1, n):
            y[:, i] = r * y[:, i - 1] + e[:, i]
        y = y - y.mean(axis=1, keepdims=True)
        tah = np.einsum("ij,ij->i", y[:, 1:], y[:, :-1]) / np.einsum("ij,ij->i", y[:, :-1], y[:, :-1])
        med.append(np.median(tah)); q05.append(np.quantile(tah, 0.05)); q95.append(np.quantile(tah, 0.95))
    med, q05, q95 = map(np.array, (med, q05, q95))

    def ters(egri: np.ndarray) -> float:
        # egri izgarada artan; rho_hat'ı veren ızgara noktası (doğrusal ara değer)
        if rho_hat <= egri[0]:
            return float(izgara[0])
        if rho_hat >= egri[-1]:
            return float(izgara[-1])
        j = int(np.searchsorted(egri, rho_hat))
        a, b = egri[j - 1], egri[j]
        return float(izgara[j - 1] + (rho_hat - a) / (b - a) * (izgara[j] - izgara[j - 1]))
    rho_mu = ters(med)
    alt = ters(q95)   # q95 eğrisini tutturan ρ alt sınır
    ust = ters(q05)
    return {"n": int(n), "rho_ols": rho_hat, "rho_mu": rho_mu, "rho_alt90": alt, "rho_ust90": ust,
            "yo_ols": yari_omur(rho_hat), "yo_mu": yari_omur(rho_mu), "yo_alt90": yari_omur(alt),
            "yo_ust90": yari_omur(ust) if ust < 0.9999 else None, "ust_sonsuz": bool(ust >= 0.9999)}


def yuvarla(x, h: int = 4):
    """olcum.json için: float'ları sabit hanede tutar (metin ondalığı ayrı)."""
    if isinstance(x, float):
        return None if not math.isfinite(x) else round(x, h)
    if isinstance(x, dict):
        return {str(k): yuvarla(v, h) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [yuvarla(v, h) for v in x]
    if isinstance(x, (np.floating,)):
        return yuvarla(float(x), h)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.bool_,)):
        return bool(x)
    if isinstance(x, (pd.Timestamp,)):
        return str(x.date())
    return x
