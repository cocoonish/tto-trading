#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRODAN KURA VE FAİZE — Bölüm 10 (Ticaret hadleri ve emtia) ölçüm katmanı.

Pratikler
  p10a  Emtia paraları: AUD–metal ve CAD–enerji (CNBC New York 17:00,
        Dünya Bankası Pink Sheet), NOK–enerji (ECB referans kuru çaprazı,
        14:15 Orta Avrupa): aylık log değişim korelasyonu, tam örneklem
        2000–2026 ve 36 aylık kayan; Newey–West eğimi ve örneklem dışı kıyas;
        öncü/gecikmeli korelasyon tablosu; 2014-06 → 2016-01 petrol düşüşü.
  p10b  2022 dolar şoku: 03.01.2022 → 31.10.2022 EUR, CAD, JPY (dolara
        karşı) ve enerji fiyatı; Türkiye: aylık Δlog enerji → ΔUSD/TRY,
        Δ2 yıllık DİBS, ve 12 aylık net enerji faturası 2013–2026.
        Yönetilen kur dönemi (2021-12 … 2023-06) kur ve faiz tepkisinde
        AYRI dönemdir, havuzlanmaz.
  sekil_17  aylık AUD–metal, CAD–enerji, NOK–enerji seviyeleri (2000=100)
            ve 36 aylık kayan korelasyonlar.

YÖN. Para birimi serileri "yerel paranın dolar karşısındaki DEĞERİ" olarak
kurulur (artış değer kazancı): CNBC'de AUD XXX/USD olduğu için log(AUD/USD),
CAD USD/XXX olduğu için −log(USD/CAD); NOK, JPY ve EUR aynı kuralla. Türkiye
satırında ise ders sözleşmesi geçerlidir: s = log(USD/TRY), artış TL'nin
DEĞER KAYBI.

ÖLÇÜLEREK BULUNAN TUZAKLAR (kod onları kapatır, metin adıyla anar)
  1. PINK SHEET AYLIK ORTALAMADIR, CNBC AY SONU DEĞERİ DEĞİL. Ay sonu kurun
     değişimi ile ay ortalaması emtia değişimini eşleştirmek iki şey yapar:
     eşzamanlı korelasyonu düşürür (AUD–metal 0,35; aynı iki seri ay
     ortalamasıyla 0,61) ve kurun bir AY ÖNCEKİ değişimini emtianın bu ayki
     değişimiyle aritmetik olarak ilişkilendirir (ortalamanın değişimi önceki
     ayın günlerini de taşır). Aritmetiğin BÜYÜKLÜĞÜ ölçüldü (denetim): kurun
     kendi ay ortalaması emtianın yerine konunca (aynı gün, öncülük yok) öncü
     korelasyon eşzamanlının 0,76 (AUD) – 0,84 (CAD) katı çıkıyor, yani
     aritmetik öncü korelasyonu eşzamanlının ALTINDA tutar. AUD–metalde öncü
     (0,48) eşzamanlıyı (0,35) aşıyor: aritmetiğin vereceği ≈0,27'nin üstünde
     ≈0,21'lik fazla aritmetik DEĞİLDİR. Ama ortalama penceresiyle örtüşmeyen
     iki ay öncü sınamada ilişki yok (AUD 0,10, t 0,8): fazla ortalama
     penceresinin dışına taşmıyor, "kur emtiayı öngörüyor" kuralı bu veriyle
     kurulamaz. CAD ve NOK'ta öncü korelasyon aritmetiğin verdiği düzeyde.
     Ana tanım ders planının istediği ay sonu kurudur; ay ortalaması hizası
     yanında durur ve öncü/gecikmeli tablo iki hizayı, plaseboyu ve
     örtüşmesiz sınamayı birlikte verir.
  2. CNBC kur dosyası hafta sonu barı da taşır (479 pazar, 6 cumartesi) ve 01–03.01.2020'de bozuk
     EUR/USD kotasyonu vardır. İkisi de ortak tanımda ayıklanır
     (`ortak_olc.cnbc_kur`: hafta içi, bozuk kotasyon günleri çıkarılmış); ay
     sonu değeri ve ay ortalaması oradan okunur.
  3. NOK New York kapanışı değil ECB 14:15 Orta Avrupa sabitlemesidir (euro
     çaprazından USD/NOK); ay sonu değeri ayın son sabitlemesidir. CAD ile
     NOK aynı satırda kıyaslanırken saat farkı adıyla yazılır.
  4. 2022 PENCERESİNDE ENERJİ AYLIK ORTALAMADIR: kur 03.01 → 31.10 günlük
     kapanışlarla, enerji Ocak → Ekim ay ortalamalarıyla ölçülür.
  5. DİBS HİZASI "gun_sonu" (`ortak_olc.DIBS_KAYMA`, k = 2): L etiketli DİBS
     değeri L−1'in sabah sabitlemesidir; ay sonu kur (Yahoo, CNBC) ve DXY gün
     sonu kapanışı olduğu için aylık Δ2 yıllık, D gününe D'den iki Türkiye iş
     günü sonraki etiket yazılarak kurulur (aynı günün gün sonu bilgisi).
     CUMA: 18.12.2023 öncesi Yahoo USD/TRY serisinde cumartesi barı yok; cuma
     biten ayın son değeri pazartesi barının başından (hafta sonu açılışından
     sonra) gelir. `usdtry(cuma_dus=True)` KULLANILMAZ: aylık değişim
     pencereleri bitişik kalır (her hafta sonu tek bir aya yazılır, hiçbiri iki
     kez ya da hiç sayılmaz); perşembeye çekmek o ayın cuma seansını ertesi
     aya taşırdı. Ölçüldü: yönetilen dönem dışı enerji eğimi ay sonu kurla
     −0,0656 (t −2,37), cuma boşaltılınca −0,0691 (t −2,37); hüküm değişmiyor
     (`p10b.turkiye.tepki.usdtry.cuma_duyarliligi`).
  6. ENERJİ FATURASI ile FİYAT: 12 aylık net enerji ithalatı ile 12 aylık
     ortalama enerji endeksi seviyede birlikte eğilimlidir; seviye
     regresyonu sahte ilişki riski taşır. Ana ölçü iki serinin 12 aylık log
     değişimidir; gecikme profili sözleşmelerin fiyata bağlanma gecikmesini
     (boru gazı fiyatı petrole birkaç ay gecikmeyle bağlanır) gösterir.
  7. USD/TRY'NİN EĞİLİMİ SIFIR KIYASINI BOZAR: Türkiye'de aylık kur
     değişiminin ortalaması sıfırdan belirgin büyüktür (kontrollü değer
     kaybı). Rastgele yürüyüş kıyası (değişim sıfır) bu yüzden modelin
     yalnız SABİT TERİMİNİ ödüllendirir: 2023-07 … 2026-08'de enerji eğimi
     sıfırken örneklem dışı oran sıfır kıyasına göre 0,14, koşulsuz ortalama
     kıyasına göre 1,10. Hüküm iki kıyasın da geçmesini ister (p10a'da da).
  8. TÜRKİYE'NİN ENERJİ–KUR EĞİMİ HİZAYA DUYARLI: yönetilen dönem dışında
     ay sonu kurla −0,07 (t −2,4; enerji pahalılaşınca TL değer kazanıyor;
     dolar endeksi kontrol edilince eğim −0,055'e iniyor, yani ortak etkenin
     bir kısmı dolardır — risk iştahı ayrıca ölçülmedi), aynı ilişki kur ay
     ortalamasıyla −0,03 (t −0,8). Mekanik hüküm "ölçülü" der; satır
     `hizaya_duyarli` bayrağını taşır ve metin onu kural olarak kuramaz.
  9. "%10'LUK FİYAT ARTIŞI" BASİT YÜZDEDİR (denetimde düzeltildi): esneklik
     log cinsindendir, %10'luk artışın etkisi 1,1^b − 1'dir; exp(0,1·b) − 1
     10 log puanlık (%10,5) artışı verir ve faturaya etkiyi ≈%5 büyütürdü
     (5,40'a karşı 5,13 milyar dolar).
  10. ÖRTÜŞEN 12 AYLIK DEĞİŞİMDE DM t'si: enerji faturası eşzamanlı ilişkisinin
     hataları 23 ay örtüşür; sözleşme fonksiyonunun varsayılan DM gecikmesi
     (3) t'yi şişirir. DM ayrıca 24 gecikmeyle verilir; hüküm sıfır ve
     koşulsuz ortalama kıyasının ikisini de ister.

ÖLÇÜLEN BULGU (tuzak değil): CAD–enerji ve NOK–enerji 36 aylık kayan
korelasyonu 2024 sonundan itibaren eksiye döndü (ikisi de 2024-11'den beri,
22 ay; CAD'de en düşük −0,44, 2025-09; 2022 ortasında +0,54'tü);
2014–2016 petrol düşüşünde enerji ithalatçısı EUR da CAD'ye yakın değer
kaybetti (−22 ile −27 log puan) ve dolar endeksi aynı pencerede +21 log puan
yükseldi: o dönemin baskın terimi doların kendisiydi.
"""
from __future__ import annotations

import math
import warnings
from functools import lru_cache

import numpy as np
import pandas as pd

import bulut
import ortak_olc as oo
import olcum_b08 as b08

warnings.filterwarnings("ignore", message="Could not infer format")   # ovp_programlar ilk sütunu tarih değil
warnings.filterwarnings("ignore", category=FutureWarning)

# ───────────────────────────────────────────────────────── sabitler (adlı)
BAS = "2000-02-01"            # CNBC 2000-01-03'te başlar: ilk aylık değişim Şubat 2000
SON = str(oo.CIPA_AY.to_timestamp().date())    # Pink Sheet çıpası (2026-08)
KAYAN_AY = 36
KAYAN_ASGARI = 30
OOS_ILK_AY = 120
PETROL = ("2014-06-01", "2016-01-01", "2014-06 → 2016-01 petrol düşüşü")
SOK_2022 = ("2022-01-03", "2022-10-31")
TR_BAS = "2013-02-01"         # DİBS eğrisi 2013-01'de başlar: ilk aylık değişim Şubat 2013
YON_BAS, YON_SON = oo.YONETILEN
DIBS_HIZA = "gun_sonu"        # ay sonu kur ve DXY gün sonu kapanışı (tuzak 5)
TR_DONEMLER = (("oncesi", TR_BAS, oo.YON_ONCESI_SON_AY, f"2013-02 … {oo.YON_ONCESI_AY}"),
               ("yonetilen", oo.YON_ILK, oo.YON_SON_AY, f"yönetilen kur {oo.YON_AY[0]} … {oo.YON_AY[1]} (ayrı dönem)"),
               ("sonrasi", f"{oo.YON_SONRASI_AY}-01", SON, f"{oo.YON_SONRASI_AY} … 2026-08"))
FATURA_BAS = "2013-01-01"
FATURA_AZAMI_GECIKME = 12


_iso, kurulmadi, hukum = oo._iso, oo.kurulmadi, oo.hukum      # tek tanımlar ortak_olc'de
_reg = oo.reg


def _oos_iki(y: pd.Series, x: pd.Series, ilk: int) -> tuple[dict, dict, str | None]:
    """İki saf kıyas (`ortak_olc.oos_takimi`, ufuk 1): (sıfır, koşulsuz ortalama, hüküm için oranlar)."""
    tk = oo.oos_takimi(y, x, ilk)
    return tk["sifir"], tk["ortalama"], oo.takim_oranlari(tk)


# ───────────────────────────────────────────────────────── seriler
def _cnbc() -> pd.DataFrame:
    """CNBC kurları, ortak tanım (tuzak 2)."""
    return oo.cnbc_kur()


def _deger(seri: pd.Series, ters: bool) -> pd.Series:
    """Yerel paranın dolar karşısındaki değeri, log×100 (artış değer kazancı)."""
    x = np.log(seri.dropna()) * 100
    return -x if ters else x


@lru_cache(maxsize=2)
def _aylik_kurlar(hiza: str) -> pd.DataFrame:
    """hiza: 'son' ay sonu (son hafta içi kapanış), 'ort' ay ortalaması."""
    c = _cnbc()
    a = c.resample("MS").last() if hiza == "son" else c.resample("MS").mean()
    out = pd.DataFrame({"aud": _deger(a["aud"], False), "cad": _deger(a["cad"], True),
                        "eur": _deger(a["eur"], False), "jpy": _deger(a["jpy"], True)})
    try:
        nok = _usd_nok()
        out["nok"] = _deger(nok.resample("MS").last() if hiza == "son" else nok.resample("MS").mean(), True)
    except bulut.VeriYok:
        pass
    return out


@lru_cache(maxsize=1)
def _usd_nok() -> pd.Series:
    """USD/NOK = (EUR/NOK)/(EUR/USD), ECB 14:15 Orta Avrupa; hafta içi."""
    x = (bulut.ecb_kur("NOK") / bulut.ecb_kur("USD")).dropna()
    x = x[(x.index.dayofweek < 5) & (x.index <= oo.CIPA_GUN)]
    x.name = "usdnok"
    return x


@lru_cache(maxsize=1)
def _emtia() -> pd.DataFrame:
    k = oo.oku("kuresel_aylik")
    return pd.DataFrame({"metal": np.log(k["emtia_metal"]) * 100,
                         "enerji": np.log(k["emtia_enerji"]) * 100}).dropna()


def _cift(fx: str, emtia: str, hiza: str) -> pd.DataFrame:
    a = _aylik_kurlar(hiza)
    if fx not in a.columns:
        raise bulut.VeriYok("ECB referans kurları: NOK elde yok")
    d = pd.concat([a[fx].diff().rename("fx"), _emtia()[emtia].diff().rename("em")], axis=1)
    return d.loc[BAS:SON].dropna()


# ───────────────────────────────────────────────────────── p10a
def _kayan(d: pd.DataFrame) -> pd.Series:
    return d["fx"].rolling(KAYAN_AY, min_periods=KAYAN_ASGARI).corr(d["em"]).dropna()


def _kor_tablosu(a: pd.Series, e: pd.Series) -> dict:
    out = {}
    for ad, k in (("kur_bir_ay_onde", 1), ("es_zamanli", 0), ("emtia_bir_ay_onde", -1)):
        # kur_bir_ay_onde: kurun t−1 ayındaki değişimi ile emtianın t ayındaki değişimi
        d = pd.concat([a.shift(k).rename("fx"), e.rename("em")], axis=1).loc[BAS:SON].dropna()
        out[ad] = {"kor": float(d["fx"].corr(d["em"])), "n": int(len(d))}
    return out


def _oncu_gecikmeli(fx: str, emtia: str, hiza: str) -> dict:
    a = _aylik_kurlar(hiza)[fx].diff()
    e = _emtia()[emtia].diff()
    out = _kor_tablosu(a, e)
    if hiza != "son":
        return out
    # Ay sonu kur ~ ay ortalaması emtia hizasında aritmetiğin payı: emtianın yerine kurun KENDİ
    # ay ortalaması konur (aynı günler, öncülük yok). Bu plasebonun öncü/eşzamanlı oranı,
    # ortalama almanın tek başına üreteceği öncü korelasyonu verir.
    oz = _kor_tablosu(a, _aylik_kurlar("ort")[fx].diff())
    oran = oz["kur_bir_ay_onde"]["kor"] / oz["es_zamanli"]["kor"]
    beklenen = oran * out["es_zamanli"]["kor"]
    # Örtüşmesiz öncülük: kurun t−2 ayındaki değişimi, emtianın t ayı ortalama değişimiyle (ortalamanın
    # kapsadığı t−1 ve t aylarıyla örtüşmez). Öngörü iddiası ancak burada kurulabilir.
    d = pd.concat([a.shift(2).rename("x"), e.rename("y")], axis=1).loc[BAS:SON].dropna()
    r = _reg(d["y"], d["x"], gecikme=None)
    out.update({
        "plasebo_kurun_kendi_ortalamasi": {"kur_bir_ay_onde": oz["kur_bir_ay_onde"]["kor"],
                                           "es_zamanli": oz["es_zamanli"]["kor"], "oncu_es_orani": oran},
        "aritmetik_beklenen_oncu_kor": beklenen,
        "aritmetik_disi_fazla": out["kur_bir_ay_onde"]["kor"] - beklenen,
        "kur_iki_ay_onde_ortusmesiz": {"kor": float(d["x"].corr(d["y"])), "egim": r["b"][0], "t": r["t"][0],
                                       "n": r["n"], "gecikme": r["gecikme"]},
    })
    return out


def _cift_olc(fx: str, emtia: str, ad: str) -> dict:
    try:
        d = _cift(fx, emtia, "son")
        d_ort = _cift(fx, emtia, "ort")
    except bulut.VeriYok as hata:
        return kurulmadi(str(hata))
    r = _reg(d["fx"], d["em"], gecikme=None)
    oos, oos_ort, oranlar = _oos_iki(d["fx"], d["em"], OOS_ILK_AY)
    kay = _kayan(d)
    kay_ort = _kayan(d_ort)
    son = kay.index.max()
    out = {
        "yontem": (f"{ad}: yerel paranın dolar karşısındaki değerinin aylık log değişimi ile emtia endeksinin "
                   "aylık log değişimi arasındaki korelasyon ve Newey–West eğimi; kur ay sonu kapanışı, "
                   "emtia Pink Sheet ay ortalaması; örneklem dışı kıyas hem rastgele yürüyüş (değişim sıfır) hem "
                   "koşulsuz ortalama."),
        "n": int(len(d)), "ilk": _iso(d.index.min()), "son": _iso(d.index.max()),
        "kor_ay_sonu": float(d["fx"].corr(d["em"])),
        "kor_ay_ortalamasi": float(d_ort["fx"].corr(d_ort["em"])),
        "n_ay_ortalamasi": int(len(d_ort)),
        "egim_yuzde_yuzde": r["b"][0], "se": r["se"][0], "t": r["t"][0], "r2": r["r2"], "gecikme": r["gecikme"],
        "oos": oos, "oos_ortalama": oos_ort,
        "hukum": hukum(r["t"][0], oranlar),
        "kayan_36ay": {"son_tarih": _iso(son), "son": float(kay.loc[son]),
                       "en_dusuk": float(kay.min()), "en_dusuk_tarih": _iso(kay.idxmin()),
                       "en_yuksek": float(kay.max()), "en_yuksek_tarih": _iso(kay.idxmax()),
                       "medyan": float(kay.median()), "eksi_ay_payi_yuzde": float((kay < 0).mean() * 100),
                       "n_pencere": int(len(kay)),
                       "son_eksi_dizi_baslangic": _eksi_dizi(kay)[0], "son_eksi_dizi_ay": _eksi_dizi(kay)[1],
                       "ay_ortalamasi_son": float(kay_ort.iloc[-1]), "ay_ortalamasi_medyan": float(kay_ort.median())},
        "oncu_gecikmeli": {"ay_sonu": _oncu_gecikmeli(fx, emtia, "son"),
                           "ay_ortalamasi": _oncu_gecikmeli(fx, emtia, "ort"),
                           "not": ("Kur bir ay önde: kurun önceki ayki değişimi ile emtianın bu ayki değişimi. "
                                   "Ay sonu hizasında bu korelasyonun bir kısmı ortalama alma aritmetiğidir; "
                                   "aritmetiğin payı kurun kendi ay ortalamasıyla kurulan plasebodan ölçülür ve "
                                   "eşzamanlı korelasyonun altında kalır. Öngörü iddiası yalnız ortalama "
                                   "penceresiyle örtüşmeyen iki ay öncü sınamada kurulabilir.")},
    }
    return out


def _eksi_dizi(kay: pd.Series) -> tuple:
    """Kayan korelasyonun sondaki kesintisiz eksi dizisi: (başlangıç ayı, uzunluk); son değer eksi değilse (None, 0)."""
    if kay.empty or kay.iloc[-1] >= 0:
        return None, 0
    arti = kay[kay >= 0]
    dizi = kay[kay.index > arti.index.max()] if len(arti) else kay
    return _iso(dizi.index.min()), int(len(dizi))


def _bolum(a: pd.DataFrame, e: pd.DataFrame, fx: str, emtia: str, bas: str, son: str) -> dict:
    if fx not in a.columns:
        return kurulmadi("ECB referans kurları: NOK elde yok")
    dfx = float(a.loc[son, fx] - a.loc[bas, fx])
    dem = float(e.loc[son, emtia] - e.loc[bas, emtia])
    return {"kur_degisim_log_yuzde": dfx, "kur_degisim_yuzde": float(100 * (math.exp(dfx / 100) - 1)),
            "emtia_degisim_log_yuzde": dem, "emtia_degisim_yuzde": float(100 * (math.exp(dem / 100) - 1)),
            "oran_kur_emtia": dfx / dem if dem else None}


def _petrol_dusus() -> dict:
    bas, son, ad = PETROL
    e = _emtia()
    son_ = _aylik_kurlar("son")
    ort_ = _aylik_kurlar("ort")
    out = {"ad": ad, "ilk": bas, "son": son,
           "yontem": ("Haziran 2014'ten Ocak 2016'ya emtia endeksinin ay ortalaması ve paranın dolar karşısındaki "
                      "değeri (ay ortalaması; ay sonu kapanışı sağlamlık) log değişimi."),
           "enerji_degisim_log_yuzde": float(e.loc[son, "enerji"] - e.loc[bas, "enerji"]),
           "metal_degisim_log_yuzde": float(e.loc[son, "metal"] - e.loc[bas, "metal"])}
    out["enerji_degisim_yuzde"] = float(100 * (math.exp(out["enerji_degisim_log_yuzde"] / 100) - 1))
    for fx, em in (("cad", "enerji"), ("nok", "enerji"), ("aud", "metal")):
        out[fx] = {"ay_ortalamasi": _bolum(ort_, e, fx, em, bas, son),
                   "ay_sonu": _bolum(son_, e, fx, em, bas, son)}
    out["eur_kiyas"] = {"ay_ortalamasi": _bolum(ort_, e, "eur", "enerji", bas, son)}
    # doların kendi hareketi (ay ortalaması, aynı pencere): "baskın terim dolar" cümlesinin ölçüsü
    dx = oo.oku("yahoo_dxy_vix_gunluk")["dxy"].dropna()
    dx = np.log(dx[dx.index.dayofweek < 5].resample("MS").mean()) * 100
    out["dxy_degisim_log_yuzde"] = float(dx.loc[son] - dx.loc[bas])
    out["n"] = sum(1 for k in ("cad", "nok", "aud") if out[k]["ay_ortalamasi"].get("durum") is None) + 1  # + EUR kıyası
    out["vaka_tablosu"] = True
    out["saat_notu"] = "CAD ve AUD New York 17:00, NOK ECB 14:15 Orta Avrupa sabitlemesinden, dolar endeksi New York kapanışı."
    return out


def p10a() -> dict:
    aud = _cift_olc("aud", "metal", "AUD–metal")
    return {
        "yontem": ("Emtia ihracatçısı paraların (AUD, CAD, NOK) dolar karşısındaki aylık değeri ile ilgili emtia "
                   "endeksinin aylık log değişimleri arasındaki eşzamanlı, öncü ve kayan korelasyon; 2014–2016 "
                   "petrol düşüşünde kur ve emtia değişimi."),
        "n": aud.get("n"), "ilk": aud.get("ilk"), "son": aud.get("son"),
        "kaynak": ["cnbc_kur_gunluk (AUD/USD, USD/CAD, EUR/USD; New York 17:00)",
                   "kuresel_aylik (Pink Sheet metal ve enerji endeksleri, nominal dolar, ay ortalaması)",
                   "bulut: ECB referans kurları (USD/NOK çaprazı, 14:15 Orta Avrupa)",
                   "yahoo_dxy_vix_gunluk (dolar endeksi, petrol penceresi)"],
        "aud_metal": aud,
        "cad_enerji": _cift_olc("cad", "enerji", "CAD–enerji"),
        "nok_enerji": _cift_olc("nok", "enerji", "NOK–enerji"),
        "petrol_2014_2016": _petrol_dusus(),
    }


# ───────────────────────────────────────────────────────── p10b
def _sok_2022() -> dict:
    c = _cnbc()
    b, s = pd.Timestamp(SOK_2022[0]), pd.Timestamp(SOK_2022[1])
    paralar = {}
    for kod, ters in (("eur", False), ("cad", True), ("jpy", True), ("gbp", False), ("aud", False), ("chf", True)):
        x0, x1 = float(c.loc[b, kod]), float(c.loc[s, kod])
        dlog = 100 * math.log(x1 / x0) * (-1 if ters else 1)
        paralar[kod] = {"degisim_log_yuzde": dlog, "degisim_yuzde": float(100 * (math.exp(dlog / 100) - 1)),
                        "baz": x0, "son": x1, "kote": "USD/XXX" if ters else "XXX/USD",
                        "rol": {"eur": "enerji ithalatçısı", "jpy": "enerji ithalatçısı",
                                "cad": "enerji ihracatçısı"}.get(kod, "kıyas")}
    dx = oo.oku("yahoo_dxy_vix_gunluk")["dxy"].dropna()
    ab = oo.oku("abd_hazine_gunluk")["us2"].dropna()
    e = oo.oku("kuresel_aylik")["emtia_enerji"]
    e0, e1 = float(e.loc["2022-01-01"]), float(e.loc["2022-10-01"])
    out = {
        "yontem": ("3 Ocak 2022 ile 31 Ekim 2022 kapanışları arasında paranın dolar karşısındaki değerinin log "
                   "değişimi (eksi değer kaybı); enerji Ocak ve Ekim ay ortalamaları arasında."),
        "kaynak": ["cnbc_kur_gunluk (New York 17:00)", "kuresel_aylik (Pink Sheet enerji, ay ortalaması)",
                   "yahoo_dxy_vix_gunluk (DXY)", "abd_hazine_gunluk (2 yıllık par getiri)"],
        "ilk": SOK_2022[0], "son": SOK_2022[1], "n": len(paralar),
        "paralar": paralar,
        "dxy_degisim_log_yuzde": float(100 * math.log(dx.loc[s] / dx.loc[b])),
        "abd_2y_degisim_bp": float((ab.loc[s] - ab.loc[b]) * 100),
        "abd_2y_baz_yuzde": float(ab.loc[b]), "abd_2y_son_yuzde": float(ab.loc[s]),
        "enerji_degisim_log_yuzde": float(100 * math.log(e1 / e0)),
        "enerji_degisim_yuzde": float(100 * (e1 / e0 - 1)),
        "enerji_zirve_ay": _iso(e.loc["2022-01-01":"2022-10-01"].idxmax()),
        "enerji_zirveye_log_yuzde": float(100 * math.log(e.loc["2022-01-01":"2022-10-01"].max() / e0)),
        "cad_eksi_eur_puan": paralar["cad"]["degisim_log_yuzde"] - paralar["eur"]["degisim_log_yuzde"],
        "cad_eksi_jpy_puan": paralar["cad"]["degisim_log_yuzde"] - paralar["jpy"]["degisim_log_yuzde"],
        "saat_notu": "Kurlar New York 17:00, ABD 2 yıllık getiri New York kapanışı, enerji aylık ortalama.",
        "vaka_tablosu": True,
    }
    return out


@lru_cache(maxsize=2)
def _tr_aylik(cuma_dus: bool = False) -> pd.DataFrame:
    s, _ = oo.usdtry(cuma_dus=cuma_dus)
    s = s.dropna()
    d = oo.dibs(DIBS_HIZA, ("n2y",))["n2y"].dropna()      # Türkiye iş günü takviminde, gün sonu hizası
    dx = oo.oku("yahoo_dxy_vix_gunluk")["dxy"].dropna()
    dx = dx[dx.index.dayofweek < 5]
    ls = np.log(s) * 100
    df = pd.DataFrame({
        "denerji": _emtia()["enerji"].diff(),
        "dkur": ls.resample("MS").last().diff(),
        "dkur_ort": (np.log(s.resample("MS").mean()) * 100).diff(),
        "dn2y_bp": (d.resample("MS").last() * 100).diff(),
        "ddxy": (np.log(dx.resample("MS").last()) * 100).diff(),
    })
    return df.loc[TR_BAS:SON]


def _donem_reg(z: pd.DataFrame, yad: str) -> dict:
    d = z[[yad, "denerji", "ddxy"]].dropna()
    if len(d) < 12:
        return kurulmadi("dönemde gözlem yetersiz")
    r = _reg(d[yad], d["denerji"], gecikme=None)
    rk = _reg(d[yad], d[["denerji", "ddxy"]], gecikme=None)
    out = {"n": r["n"], "ilk": r["ilk"], "son": r["son"], "egim": r["b"][0], "se": r["se"][0], "t": r["t"][0],
           "r2": r["r2"], "gecikme": r["gecikme"], "kor": float(d[yad].corr(d["denerji"])),
           "dolar_kontrollu": {"egim": rk["b"][0], "se": rk["se"][0], "t": rk["t"][0],
                               "dxy_egim": rk["b"][1], "dxy_t": rk["t"][1], "r2": rk["r2"]}}
    ilk = max(24, len(d) // 2)
    if len(d) - ilk >= 10:
        oos, oos_ort, oranlar = _oos_iki(d[yad], d["denerji"], ilk)
        out["oos"] = oos
        out["oos_ortalama"] = oos_ort
        out["hukum"] = hukum(r["t"][0], oranlar)
    else:
        out["oos"] = kurulmadi("örneklem dışı sınama için en az on tahmin gerekir")
        out["oos_ortalama"] = kurulmadi("örneklem dışı sınama için en az on tahmin gerekir")
        out["hukum"] = "tarif edici"
    return out


def _tr_tepki() -> dict:
    df = _tr_aylik()
    yon = (df.index >= YON_BAS) & (df.index <= YON_SON)
    out = {}
    for yad, ad in (("dkur", "usdtry"), ("dn2y_bp", "dibs_2y")):
        bl = {}
        for anahtar, bas, son, etiket in TR_DONEMLER:
            bl[anahtar] = {"etiket": etiket, **_donem_reg(df.loc[bas:son], yad)}
        bl["yonetilen_haric"] = {"etiket": "2013-02 … 2021-11 ve 2023-07 … 2026-08 (yönetilen dönem dışarıda)",
                                 **_donem_reg(df[~yon], yad)}
        out[ad] = bl
    dc = _tr_aylik(cuma_dus=True)
    yc = (dc.index >= YON_BAS) & (dc.index <= YON_SON)
    rc = _donem_reg(dc[~yc], "dkur")
    out["usdtry"]["cuma_duyarliligi"] = {
        "etiket": "yönetilen dönem dışı, 18.12.2023 öncesi cuma kur değeri boşaltılmış (ay perşembe kapanışıyla biter)",
        "n": rc.get("n"), "egim": rc.get("egim"), "t": rc.get("t"), "hukum": rc.get("hukum"),
        "not": "Ana tanım cuma değerini tutar: aylık pencereler bitişik kalır (tuzak 5)."}
    out["usdtry"]["ay_ortalamasi_yonetilen_haric"] = {
        "etiket": "aynı ilişki, kur ay ortalamasıyla (emtia ile aynı hiza)", **_donem_reg(df[~yon], "dkur_ort")}
    out["birim"] = {"usdtry": "USD/TRY'nin aylık log değişimi (%) / enerji endeksinin aylık log değişimi (%)",
                    "dibs_2y": "2 yıllık DİBS getirisinin aylık değişimi (bp) / enerji endeksinin aylık log değişimi (%)"}
    out["isaret"] = "USD/TRY'de artı eğim: enerji pahalılaştığında TL değer kaybeder."
    out["kiyas_notu"] = ("USD/TRY'nin aylık değişiminde belirgin bir eğilim (sürekli değer kaybı) var: sıfır kıyası "
                         "yalnız sabit terimi ödüllendirir, bu yüzden hüküm koşulsuz ortalama kıyasını da ister.")
    hk = out["usdtry"]["yonetilen_haric"]
    ho = out["usdtry"]["ay_ortalamasi_yonetilen_haric"]
    hk["hizaya_duyarli"] = bool(np.sign(hk.get("egim") or 0) != np.sign(ho.get("egim") or 0)
                                or (abs(hk.get("t") or 0) >= 2) != (abs(ho.get("t") or 0) >= 2))
    out["hiza_notu"] = ("Ay sonu kurla kurulan eğim ve aynı ilişkinin kur ay ortalamasıyla (enerjiyle aynı hiza) "
                        "kurulan eğimi yan yana: ikisi ayrışıyorsa sonuç hizaya duyarlıdır.")
    out["hiza_duyarliligi"] = {"ay_sonu_egim": hk.get("egim"), "ay_sonu_t": hk.get("t"),
                               "ay_ortalamasi_egim": ho.get("egim"), "ay_ortalamasi_t": ho.get("t"),
                               "isaret_ayni": bool(hk.get("egim") is not None and ho.get("egim") is not None
                                                   and np.sign(hk["egim"]) == np.sign(ho["egim"])),
                               "ikisi_de_anlamli": bool(abs(hk.get("t") or 0) >= 2 and abs(ho.get("t") or 0) >= 2)}
    return out


def _fatura() -> dict:
    o = oo.oku("odemeler_aylik")
    fatura = -o["hc_enerji_net"].rolling(12, min_periods=12).sum() / 1e3       # milyar USD, artı = net ithalat
    fiyat = oo.oku("kuresel_aylik")["emtia_enerji"].rolling(12, min_periods=12).mean()
    G = b08.aylik_gsyh_usd()
    df = pd.DataFrame({"lf": np.log(fatura) * 100, "lp": np.log(fiyat) * 100}).loc[FATURA_BAS:].dropna()
    d12 = df.diff(12)
    profil = {"gecikme_ay": [], "esneklik": [], "se": [], "t": [], "r2": []}
    for k in range(FATURA_AZAMI_GECIKME + 1):
        r = _reg(d12["lf"], d12["lp"].shift(k), gecikme=b08.HAC_GECIKME)
        profil["gecikme_ay"].append(k); profil["esneklik"].append(r["b"][0]); profil["se"].append(r["se"][0])
        profil["t"].append(r["t"][0]); profil["r2"].append(r["r2"])
    j = int(np.argmax(profil["r2"]))
    r0 = _reg(d12["lf"], d12["lp"], gecikme=b08.HAC_GECIKME)
    dd = d12.dropna()
    # eşzamanlı ilişki: ambargo 1; hatalar 23 ay örtüştüğü için DM t'si 24 gecikmeyle (tuzak 10)
    oos = b08.oos_takim(dd["lf"], dd["lp"], min(60, len(dd) // 2), 1, b08.HAC_GECIKME)
    sev = _reg(df["lf"], df["lp"], gecikme=b08.HAC_GECIKME)
    son = fatura.dropna().index.max()
    oran = (fatura * 1e3 / G * 100).dropna().loc[FATURA_BAS:]
    son_fatura = float(fatura.loc[son])
    on_yuzde = 1.1 ** r0["b"][0] - 1          # %10'luk (basit) fiyat artışının faturaya oranı (tuzak 9)
    return {
        "yontem": ("12 aylık net enerji ithalatının (milyar dolar) 12 aylık log değişimi, Pink Sheet enerji "
                   "endeksinin 12 aylık ortalamasının k ay önceki 12 aylık log değişimine regrese edildi (esneklik); "
                   "standart hata Newey–West (gecikme 24), örneklem dışı kıyas koşulsuz ortalama ve değişimin "
                   "sıfır olması."),
        "kaynak": ["odemeler_aylik (hc_enerji_net, milyon USD)", "kuresel_aylik (emtia_enerji)",
                   "gsyh_ceyreklik ve usdtry_tcmb_gunluk (GSYH oranı için)"],
        "n": r0["n"], "ilk": r0["ilk"], "son": r0["son"],
        "esneklik_es_zamanli": r0["b"][0], "se": r0["se"][0], "t": r0["t"][0], "r2": r0["r2"],
        "gecikme": r0["gecikme"], "oos": oos, "hukum": hukum(r0["t"][0], b08.oranlar(oos)),
        "gecikme_profili": profil,
        "en_iyi_uyum_gecikme_ay": int(profil["gecikme_ay"][j]), "en_iyi_uyum_esneklik": float(profil["esneklik"][j]),
        "en_iyi_uyum_r2": float(profil["r2"][j]),
        "seviye_esnekligi_saglamlik": {"esneklik": sev["b"][0], "t": sev["t"][0], "r2": sev["r2"], "n": sev["n"],
                                       "not": "iki seri seviyede eğilimli; sahte ilişki riski, ana ölçü değil"},
        "son_deger": {"tarih": _iso(son), "fatura_12ay_mlr_usd": son_fatura,
                "fatura_gsyh_yuzde": float(oran.iloc[-1]), "gsyh_oran_tarihi": _iso(oran.index.max()),
                "on_yuzde_fiyat_artisi_mlr_usd": float(son_fatura * on_yuzde),
                "on_yuzde_fiyat_artisi_gsyh_puan": float(oran.iloc[-1] * on_yuzde),
                "on_yuzde_fiyat_artisi_fatura_yuzde": float(100 * on_yuzde)},
        "fatura_gsyh_araligi": {"en_dusuk_yuzde": float(oran.min()), "en_dusuk_tarih": _iso(oran.idxmin()),
                                "en_yuksek_yuzde": float(oran.max()), "en_yuksek_tarih": _iso(oran.idxmax())},
        "donem_notu": ("Enerji faturasının fiyata esnekliği kur tepkisi değildir; yönetilen kur dönemi bu ölçüde "
                       "ayrılmaz."),
    }


def p10b() -> dict:
    tr = _tr_aylik()[["denerji", "dkur"]].dropna()
    return {"yontem": ("2022 dolar şokunun euro, Kanada doları ve yen üzerindeki izi (vaka) ve Türkiye'de aylık "
                       "enerji fiyatı değişiminin kura, 2 yıllık faize ve enerji faturasına yansıması."),
            "n": int(len(tr)), "ilk": _iso(tr.index.min()), "son": _iso(tr.index.max()),
            "kaynak": ["cnbc_kur_gunluk", "kuresel_aylik", "usdtry_yahoo_gunluk", "dibs_egri_gunluk",
                       "yahoo_dxy_vix_gunluk", "abd_hazine_gunluk", "odemeler_aylik"],
            "sok_2022": _sok_2022(),
            "turkiye": {
                "yontem": ("Aylık: Pink Sheet enerji endeksinin (ay ortalaması) log değişimi ile USD/TRY'nin ay sonu "
                           "log değişimi ve 2 yıllık DİBS getirisinin ay sonu değişimi; Newey–West eğimi, dolar "
                           "endeksi kontrollü ikinci tanım, örneklem dışı kıyas rastgele yürüyüş ve koşulsuz "
                           "ortalama; yönetilen kur dönemi ayrı."),
                "kaynak": ["kuresel_aylik (emtia_enerji)", "usdtry_yahoo_gunluk", "dibs_egri_gunluk (n2y)",
                           "yahoo_dxy_vix_gunluk (DXY)", "fonlama_gunluk (yalnız iş günü takvimi)"],
                "tepki": _tr_tepki(),
                "enerji_faturasi": _fatura()}}


# ───────────────────────────────────────────────────────── sekil_17
def sekil_17() -> dict:
    a = _aylik_kurlar("son")
    e = _emtia()
    df = pd.concat([a, e], axis=1).loc["2000-01-01":SON]

    def endeks(s: pd.Series):
        if s.dropna().empty:
            return None
        taban = s.loc["2000-01-01":"2000-12-01"].mean()
        return [None if pd.isna(v) else float(100 * math.exp((v - taban) / 100)) for v in s]
    kor = {}
    for fx, em, ad in (("aud", "metal", "aud_metal"), ("cad", "enerji", "cad_enerji"), ("nok", "enerji", "nok_enerji")):
        try:
            k = _kayan(_cift(fx, em, "son")).reindex(df.index)
            kor[ad] = [None if pd.isna(v) else float(v) for v in k]
        except bulut.VeriYok:
            kor[ad] = None
    return {"baslik": "Emtia paraları: AUD–metal, CAD–enerji, NOK–enerji", "n": int(len(df)),
            "yontem": "Paranın dolar karşısındaki değeri (ay sonu) ve Pink Sheet emtia endeksi, 2000 ortalaması = 100; "
                      "36 aylık kayan korelasyon aylık log değişimlerden.",
            "kaynak": ["cnbc_kur_gunluk", "kuresel_aylik", "bulut: ECB referans kurları (NOK)"],
            "tarih": [_iso(t) for t in df.index],
            "aud_deger_2000_100": endeks(df["aud"]), "metal_2000_100": endeks(df["metal"]),
            "cad_deger_2000_100": endeks(df["cad"]), "enerji_2000_100": endeks(df["enerji"]),
            "nok_deger_2000_100": endeks(df["nok"]) if "nok" in df.columns else None,
            "kor36_aud_metal": kor["aud_metal"], "kor36_cad_enerji": kor["cad_enerji"],
            "kor36_nok_enerji": kor["nok_enerji"],
            "ilk": _iso(df.index.min()), "son": _iso(df.index.max()),
            "not": ("Paranın değeri dolar karşısında (artış değer kazancı), ay sonu kapanışı; emtia Pink Sheet ay "
                    "ortalaması; kayan korelasyon 36 aylık pencerede aylık log değişimlerden.")}


# ───────────────────────────────────────────────────────── giriş
def olc() -> dict:
    out = {"p10a": p10a(), "p10b": p10b(), "sekil_17": sekil_17()}
    return oo.yuvarla(out, 4)


if __name__ == "__main__":
    import json
    import time
    t0 = time.monotonic()
    d = olc()
    print(json.dumps(d, ensure_ascii=False)[:4000])
    print(f"\n{time.monotonic() - t0:.1f} sn")
