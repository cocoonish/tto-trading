#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRODAN KURA VE FAİZE — Bölüm 3 ölçüm katmanı: tepki fonksiyonu.

Pratikler
  p3a  Türkiye Taylor bandı (aylık): iki enflasyon ölçüsü × iki çıktı açığı
       sürümü × üç r*; AOFM ve politika faizi ile kıyas. `arac_taylor`: Araç 1'in
       açılış girdileri.
  p3b  PPK günleri (111 karar, 2016–2026): DİBS tarih hizası, ima sürprizinin
       (Δ3 ay) gürültüsü ve plasebo sınaması; anket sürprizi (PKA toplantı
       beklentisi) ve kur tepkisi dönem dönem; karar değişimi ile anket sürprizi.
  p3c  ABD–Almanya 2 yıllık farkı ile EUR/USD, haftalık, dört dönem.
  p3d  ABD istihdam ve Türkiye GSYH yayım günleri: varyans/kovaryans oranı.
  sekil_03 Taylor bandı, sekil_04 faiz farkı ↔ EUR/USD.

Öbür modüllerin kullanabileceği yardımcılar (b04 içe aktarır; b03 hiçbir bölüm
modülünü içe aktarmaz): `dibs_gecikme` (ölçüm), `sakin_gunler`,
`abd_gunluk_degisim`, `yayim_gunu_orani`, `hp_suzgec`, `cikti_acigi`. Regresyon,
Türkiye takvimi, DİBS hizası, günlük değişim çerçevesi, olay sınaması ve dolar
sepeti `ortak_olc`dedir (tutarlılık turu, 02.10.2026; bu modüldeki kopyaları
kaldırıldı).

HİZA. PPK (14:00 TSİ) ve GSYH (10:00 TSİ) günlerinin çerçevesi DİBS değişimini
USD/TRY'nin GÜN SONU kapanışıyla aynı piyasa gününde ölçer; DİBS bu yüzden
"gun_sonu" hizasındadır (`ortak_olc.DIBS_KAYMA`, k = 2): D gününe D+2 iş günü
etiketli değer yazılır ve 14:00 kararı D'nin değişimine düşer. Önceki sürüm
ölçülen BİR iş günlük gecikmeyi kullanıyordu; o sayı TCMB gösterge kurunun
SABAH sabitlemesine göredir ("sabah" hizası) ve 14:00 kararını D'nin değil
D+1'in değişimine yazıyordu (tuzak 1). `dibs_gecikme` ölçüm olarak durur ve
"sabah" sabitine karşı sınanır. Kapı `ortak_olc.olay_kapisi`nin güçlü kuralıdır
(gün eşlemeli 1.000 rastgele kümenin %95'ini aşmak); kur serilerinde yönetilen
kur dönemi sınamaya girmez. Cuma: 18.12.2023 öncesi cuma günlerinin USD/TRY
değişimi hafta sonunu taşır ve çerçeveden boşaltılır (`cuma_dus=True`).

ÖLÇÜM TUZAKLARI (bu modül yazılırken ölçüldü)
1. DİBS EĞRİSİNİN TARİHİ PİYASADAN BİR İŞ GÜNÜ GERİDE (sabah sabitlemesine göre).
   Etiket t'deki değer t−1'in SABAH sabitlemesini taşıyor. Ölçü: DİBS 2 ve 5 yıllık
   günlük değişiminin TCMB gösterge kuruyla (15:30 ilanı, sabah sabitlemesi) çapraz
   korelasyonu 2013–2021'in her yılında bir gün kaydırmada tepe yapıyor (5 yıllıkta
   0,51–0,74; aynı günde ≈0). Gün sonu kapanışlarına göre kayma iki iş günüdür
   (Bölüm 2); bu modülün çerçevesi gün sonu hizasındadır (yukarıda HİZA).
   Olaylarla da tutuyor: Başkan'ın görevden alındığı cumartesinin ardından
   (22.03.2021 pazartesi) 2 yıllık sıçrama 23.03 etiketinde (+266 bp, 22.03'te
   +23 bp); 19.03.2025 sabahı başlayan satış 20.03 etiketinde (+227 bp); 24.08.2023
   kararının 3 aylık tepkisi 25.08 etiketinde.
2. PPK GÜNÜ DİBS KAPISI HİZAYA BAĞLI. Bir iş günü öne alınmış (sabah hizası)
   seride plasebo profilinin tepesi hiçbir düğümde karar gününe oturmuyordu;
   gün sonu hizasında sonucu `kapi` satırları düğüm düğüm verir. 3 aylık düğüm
   sıradan günlerde de yüzlerce baz puan oynuyor (ör. 08→09.04.2024 −489 bp):
   ima sürprizi ancak 3 aylık düğüm plasebo sınamasını geçerse kurulur, geçmezse `tani`
   altında yalnız tanı olarak durur. Kur (Yahoo) sınamayı geçiyor; tepki anket
   sürprizine karşı ölçülür.
3. TCMB gösterge kurunun PPK profili karar gününde değil ertesi günde tepe
   yapıyor. Sebep tepkinin geç gelmesi DEĞİL, kurun ölçüm anı: beş 14:00
   kararında (13.09.2018, 19.11.2020, 22.06.2023, 24.08.2023, 21.03.2024) Yahoo
   kuru tepkiyi karar günü etiketinde (−%3,5; −%2,0; +%5,5; −%4,9; −%1,8), TCMB
   kuru ertesi iş günü etiketinde taşıyor; sabah gelen haberi (19.03.2025) ve
   hafta sonu haberini (7 Haziran 2015 seçimi) ise aynı gün taşıyor. Yani 15:30
   ilanı, karardan önceki bir anın fiyatını yansıtıyor. Sağlamlık sınaması bu
   yüzden PPK'da kurulmadı. Aynı sebeple kur ile DİBS'in çapraz korelasyonunun
   tepesi kurun saatine bağlı: TCMB kuruyla 1, Londra gece yarısı kapanışıyla 2
   iş günü. Gecikme kararı kurdan bağımsız tatil sınamasıyla teyit edilir
   (`_tatil_kaniti`: tek günlük tatillerde hareket tatil ETİKETİNDE, tatilden
   sonraki ilk piyasa günü etiketi donmuş; 2013–2026'nın bütün tatillerinde).
   PPK sürprizine işaretli eğim de aynı şeyi söylüyor: 3 ve 6 aylık düğüm
   şahin sürprize ham etikette +1 günde tepki veriyor.
4. BIS'in Türkiye politika faizi (`em_politika_aylik.tur`) AY SONU değeridir:
   fonlama politika faiziyle örtüşen 94 ayın 94'ünde ay sonuna eşit. Politika
   faizi iki kaynakta da ay sonu alınır; AOFM ay ortalamasıdır.
5. 1 Haziran 2018 sadeleşmesinden önce bir hafta vadeli repo (2016–2018'de
   %7,5–8) etkin faiz değildi. PPK dosyası 23.05.2018'de 8,00, 07.06.2018'de
   17,75 yazar: aradaki 975 baz puan tanım değişikliğidir. 07.06.2018 kararının
   önceki etkin oranı AOFM'dir (16,50). Karar değişimi 07.06.2018'de başlar.
6. Fonlama dosyasında politika faizi karar GÜNÜNDE değişir (22.06.2023: 15,0;
   21.03.2024: 50,0), AOFM ve TLREF ertesi gün (ilk karar sonrası fonlama ve
   fiksing); kararın kendisi PPK dosyasından okunur. (Doğrulama turu, 02.10.2026:
   faizi değiştiren 41 kararda politika D, TLREF D+1, AOFM D+1 hareket ediyor.)
7. PKA toplantı beklentisi 05.2025'e kadar "cari ay sonu bir hafta vadeli repo",
   sonra "ilk toplantı" sorusudur. Karar ayının anketi eşlenir: ayın erken
   günlerindeki kararlardan dördünde (12.09.2019, 12.12.2019, 11.09.2025,
   11.12.2025) aynı ay anketi karardan sapıyor, yani anket karardan önce
   toplanmış. Önceki ay anketinin "cari ay sonu" sorusu önceki ayın sonunu
   sorar, eşlenmez. 10.09.2026 kararının anketi aylık çıpanın dışında.
8. "Gerçek zamanlı" HP açığı bugünkü veri sürümüyle kurulur: uç noktası
   sorununu ölçer, GSYH revizyonlarını ölçmez.
9. 18.12.2023 öncesi Yahoo USD/TRY serisinde cuma değeri pazartesi barının
   başındaki fiyattır (Bölüm 1); cuma günü düşen olaylarda kur değişimi hafta
   sonunu da taşır. Çerçeve o cumaların kur değişimini boşaltır
   (`ortak_olc.tr_gunluk_degisim(cuma_dus=True)`); pazartesi değişimi kalır.
10. ÖRNEKLEM DIŞI KIYAS YALNIZ SIFIRA KARŞI YAPILIRSA SÜRÜKLENME KAPIYI AÇAR.
   Sürünen bir seride (2023 sonrası USD/TRY) sabit terim tek başına "değişim
   sıfır" tahminini yener: aylık kur–TÜFE sürprizi regresyonunda oran 0,13
   çıktı, koşulsuz ortalamaya karşı 0,91. `ortak_olc.regresyon` iki kıyası da
   yapar ve hüküm için ikisini de ister.
11. Küçük örneklemde Newey–West t'si anlamsızlaşır: 2021-01…11'de 11 kararın
   yalnız dördünde anket sürprizi sıfırdan farklı ve kur eğiminin t'si −17
   çıkıyor. Eğimi yalnız sıfırdan farklı sürprizler tanımladığı için "n < 10
   vaka tablosudur" kuralı ETKİN gözlem sayısına uygulanır (`asgari_bilgili`):
   2021-01…11 (4) ve yönetilen kur dönemi (19 kararın 6'sı) vaka tablosudur.
   Birini dışarıda bırakma aralığı her regresyonda yazılır.
12. GERÇEK ZAMANLI AÇIĞIN YAYIM GECİKMESİ TAKVİMDEN OKUNUR. "Çeyrek, son
   ayından üç ay sonra kullanılır" kuralı TÜİK takvimine karşı 2013-06…2026-08'in
   159 ayının 33'ünde çeyreği yayımlandığı ayın içinde kullanıyordu: 2016
   öncesinde GSYH çeyrek sonundan ~70 gün sonra (10–11 Haziran, 10 Eylül, 10
   Aralık, 31 Mart) yayımlanırdı; Mart 2014, 2016, 2017 ve 2018'de dördüncü
   çeyrek ayın 29–31'inde çıktı, yani ayın tamamı geleceği görüyordu (açıkta
   3 puana kadar fark). Bir ay, o ay başlamadan yayımlanmış son çeyreği
   kullanır; takvimin kapsamadığı aylarda yedek kural dört aydır.
13. 07.06.2018 ANKETİ KARARDAN SONRA TOPLANMIŞ. Karar faizi 16,50'den 17,75'e
   çıkardı, kur −%1,76 ve 6 aylık getiri +24 bp tepki verdi; aynı ay anketinin
   cari ay sonu ve üç ay sonrası beklentisi İKİSİ DE tam 17,75. Önceki ayın
   anketi (8,00) 1 Haziran sadeleşmesinden önceki repoyu soruyordu. Sürpriz
   yapısal olarak sıfır çıkıyordu; kural (`anket_kirli`) yalnız bu kararı
   yakalıyor. 06.03.2025 ve 12.03.2026'da da aynı ay anketi kararı tek ufukta
   tutturuyor, ama kur ±%0,1 içinde kaldı: önceden doğru tahmin edilmiş karar.
14. Haziran 2018 öncesinde anket bir hafta vadeli repoyu soruyor, oysa etkin
   politika koridor ve geç likidite penceresiydi: 24.01.2017'deki sıkılaştırma
   −55 bp "güvercin sürpriz" diye ölçülür. O dönemde yalnız üç sürpriz sıfırdan
   farklı ve eğim ters işaretli (+0,98, t 0,68); 2016–2020 satırının yanında
   anketin etkin oranı sorduğu Haziran 2018…2020 satırı ayrıca verilir.
15. GERÇEK ZAMANLI BANT AYNI AYIN TÜFE'SİNİ GÖREMEZ. Ay m'nin yıllık TÜFE'si
   m+1'in ilk günlerinde yayımlanır; gerçek zamanlı açıkla aynı bileşimde ay
   m'nin kendi enflasyonu kullanılırsa bilgi kümesi bir ay ileriye bakar. Fark
   küçük değil: 2013–2026'da |π_m − π_{m−1}| ortalaması 1,8 puan (kural faizinde
   ≈ 2,7 puan), Aralık 2022'de 20 puan. Gerçek zamanlı bileşimler o ay
   yayımlanmış son yıllık TÜFE'yi kullanır; tam örneklem bileşimleri ex post
   kalır. Araç 1'in açılış değeri çıpa günü bilinen son TÜFE'dir (Ağustos).
"""
from __future__ import annotations

import math
import warnings
from functools import lru_cache

import numpy as np
import pandas as pd

import bulut
import ortak_olc as oo

warnings.filterwarnings("ignore", category=FutureWarning)
try:
    warnings.filterwarnings("ignore", category=pd.errors.Pandas4Warning)  # type: ignore[attr-defined]
except AttributeError:
    pass

# ─────────────────────────────────────────────────────────────── sabitler
PI_HEDEF = 5.0            # TCMB enflasyon hedefi, %
KATSAYI_PI = 0.5          # Taylor (1993)
KATSAYI_ACIK = 0.5        # Taylor (1993)
R_YILDIZ = (0.0, 2.0, 4.0)
R_YILDIZ_VARSAYILAN = 2.0
HP_LAMBDA = 1600
RT_ASGARI_CEYREK = 20     # gerçek zamanlı süzgecin ilk penceresi (çeyrek)
YAYIM_YEDEK_AY = 4        # takvim yoksa: çeyreğin açığı son ayından dört ay sonra kullanılır
TAYLOR_ILK_AY = pd.Period("2006-01", "M")
GECIKME_YILLARI = range(2013, 2022)   # kurun serbest dalgalandığı ve korelasyonun okunur olduğu yıllar

DONEM_PPK = [
    ("d2016_2020", "2016-01-01", "2020-12-31", "2016–2020"),
    ("d2021", "2021-01-01", oo.YON_ONCESI_SON, f"2021-01…{oo.YON_ONCESI_AY}"),
    ("yonetilen", oo.YON_ILK, oo.YON_SON, f"yönetilen kur {oo.YON_AY[0]}…{oo.YON_AY[1]}"),
    ("d2023_2026", oo.YON_SONRASI_ILK, "2026-09-30", f"{oo.YON_SONRASI_AY}…2026-09"),
]
DONEM_TAYLOR = [
    ("d2013_2020", "2013-01", "2020-12", "2013–2020"),
    ("d2021", "2021-01", oo.YON_ONCESI_AY, f"2021-01…{oo.YON_ONCESI_AY}"),
    ("yonetilen", oo.YON_AY[0], oo.YON_AY[1], f"yönetilen kur {oo.YON_AY[0]}…{oo.YON_AY[1]}"),
    ("d2023_2026", oo.YON_SONRASI_AY, "2026-08", f"{oo.YON_SONRASI_AY}…2026-08"),
]
DONEM_3C = [
    ("d1999_2007", "1999-01-01", "2007-12-31", "2000–2007 (kur arşivi 2000'de başlar)"),
    ("d2008_2014", "2008-01-01", "2014-12-31", "2008–2014"),
    ("d2015_2019", "2015-01-01", "2019-12-31", "2015–2019"),
    ("d2020_2026", "2020-01-01", "2026-09-30", "2020–2026"),
]
KARAR_ILK = pd.Timestamp("2018-06-07")   # tuzak 5
DIBS_DUGUM = ("n3a", "n6a", "n1y", "n2y", "n5y", "n7y")
HIZA = "gun_sonu"                          # DİBS ↔ Yahoo gün sonu kapanışı (yukarıda HİZA)
KUR_SUTUN = ("usdtry", "usdtry_tcmb")       # kapıda yönetilen kur dönemi dışarıda


# ─────────────────────────────────────────────────────────────── yardımcılar
_iso, _f = oo._iso, oo._f                  # tek tanımlar ortak_olc'de


def _liste(s: pd.Series) -> list:
    return [_f(v) for v in s.values]


kurulmadi = oo.kurulmadi


def hp_suzgec(y: np.ndarray, lam: float = HP_LAMBDA) -> np.ndarray:
    """Hodrick–Prescott eğilimi: (I + λ·DᵀD) τ = y; D ikinci fark matrisi."""
    y = np.asarray(y, dtype=float)
    n = len(y)
    D = np.zeros((n - 2, n))
    i = np.arange(n - 2)
    D[i, i], D[i, i + 1], D[i, i + 2] = 1.0, -2.0, 1.0
    return np.linalg.solve(np.eye(n) + lam * D.T @ D, y)


@lru_cache(maxsize=1)
def dibs_gecikme() -> dict:
    """DİBS etiket gecikmesi (iş günü): DİBS 2 ve 5 yıllık günlük değişiminin
    TCMB gösterge kuruyla (ilan günü, 15:30) çapraz korelasyonunun yıl yıl
    tepe yaptığı kayma; karar en sık tepe."""
    tk = oo.tr_takvim()
    d = oo.oku("dibs_egri_gunluk")
    tc = oo.usdtry_tcmb()
    x = pd.DataFrame({"n2y": d["n2y"].reindex(tk).diff(), "n5y": d["n5y"].reindex(tk).diff(),
                      "tcmb": np.log(tc.reindex(tk)).diff()}, index=tk)
    yillik, tepeler = {}, []
    for yil in GECIKME_YILLARI:
        z = x.loc[str(yil)]
        satir = {}
        for c in ("n2y", "n5y"):
            kor = {k: _f(z[c].shift(-k).corr(z["tcmb"])) for k in (0, 1, 2)}
            tepe = max(kor, key=lambda k: kor[k] if kor[k] is not None else -9)
            tepeler.append(tepe)
            satir[c] = {"k0": kor[0], "k1": kor[1], "k2": kor[2], "tepe": tepe}
        yillik[str(yil)] = satir
    say = {k: tepeler.count(k) for k in (0, 1, 2)}
    karar = max(say, key=say.get)
    tatil = _tatil_kaniti()
    return {"gecikme_is_gunu": int(karar), "tepe_sayisi": {str(k): v for k, v in say.items()},
            "ortak_sabah_sabiti": oo.DIBS_KAYMA["sabah"],
            "ortak_sabah_sabitiyle_tutarli": bool(int(karar) == oo.DIBS_KAYMA["sabah"]),
            "yillik": yillik, "ilk_yil": GECIKME_YILLARI[0], "son_yil": GECIKME_YILLARI[-1],
            "yontem": "DİBS 2 ve 5 yıllık getirisinin günlük değişimi, TCMB gösterge kurunun ilan günü değişimiyle "
                      "0, 1 ve 2 iş günü kaydırılarak yıl yıl korelasyona sokuldu; kur serbestçe dalgalanırken "
                      "korelasyonun en yüksek olduğu kayma etiket gecikmesidir.",
            "tatil_kaniti": tatil,
            "kurdan_bagimsiz_uyumlu": bool(tatil.get("gecikme_is_gunu") == karar),
            "kur_saati_notu": "Korelasyonun tepesi kıyaslanan kurun ölçüm saatine bağlıdır: TCMB gösterge kuru 14:00 "
                              "kararlarını ertesi iş günü etiketinde taşır (ölçüm anı kararın öncesindedir), Londra gece "
                              "yarısı kapanışıyla tepe iki iş gününe kayar. Bu yüzden karar kurdan bağımsız tatil "
                              "sınamasıyla teyit edilir.",
            "olay_kaniti": _olay_kaniti()}


# Saati kesin bilinen iki piyasa olayı: hareketin hangi DİBS etiketine düştüğü (saklı tarih)
OLAY_KANIT = (("2021-03-22", "pazartesi; görevden alma hafta sonunda"),
              ("2025-03-19", "çarşamba; satış sabah başladı"))


def _olay_kaniti() -> list:
    d = oo.oku("dibs_egri_gunluk")["n2y"]
    tk = oo.tr_takvim()
    dd = d.reindex(tk).diff() * 100
    out = []
    for t, ad in OLAY_KANIT:
        t = pd.Timestamp(t)
        j = tk.searchsorted(t)
        if j + 1 >= len(tk) or tk[j] != t:
            continue
        out.append({"olay_gunu": _iso(t), "aciklama": ad,
                    "n2y_olay_gunu_etiketi_bp": _f(dd.iloc[j]), "n2y_ertesi_etiket_bp": _f(dd.iloc[j + 1]),
                    "ertesi_etiket": _iso(tk[j + 1])})
    return out


@lru_cache(maxsize=1)
def _tatil_kaniti() -> dict:
    """Kurdan BAĞIMSIZ gecikme sınaması. DİBS dosyası Türkiye tatillerinde de
    satır taşır; tek günlük bir tatilin (önceki ve sonraki hafta içi gün piyasa
    günü) etiketi ile ertesi etiketin |Δ|'sı karşılaştırılır. Etiket piyasa
    gününü taşıyorsa tatil etiketi donmuş, ertesi etiket hareketli olur; bir iş
    günü geride ise tatil etiketi önceki piyasa gününün hareketini taşır ve
    ertesi etiket (tatilin "piyasası") donmuş çıkar."""
    d = oo.oku("dibs_egri_gunluk")[["n2y", "n5y", "n7y"]]
    f = oo.tr_takvim()
    adim = d.diff().abs().mul(100).mean(axis=1)            # DİBS'in kendi gün sırasında, bp
    idx = d.index
    piyasa = idx.isin(f)
    h_et, s_et, tarih = [], [], []
    for i in range(2, len(idx) - 1):
        if not piyasa[i] and piyasa[i - 1] and piyasa[i + 1]:
            h_et.append(float(adim.iloc[i])); s_et.append(float(adim.iloc[i + 1])); tarih.append(idx[i])
    h_et, s_et = np.array(h_et), np.array(s_et)
    if len(h_et) < 10:
        return kurulmadi("tek günlük tatil sayısı yetersiz", n=int(len(h_et)))
    sirad = float(adim[piyasa].median())
    hm, sm = float(np.median(h_et)), float(np.median(s_et))
    return {"n_tatil": int(len(h_et)), "ilk": _iso(tarih[0]), "son": _iso(tarih[-1]),
            "tatil_etiketi_medyan_bp": hm, "ertesi_etiket_medyan_bp": sm, "siradan_gun_medyan_bp": sirad,
            "tatil_etiketi_buyuk_pay": _f((h_et > s_et).mean()),
            "gecikme_is_gunu": 1 if hm > 3 * max(sm, 1e-9) else (0 if sm > 3 * max(hm, 1e-9) else None),
            "yontem": "Tek günlük tatillerde DİBS 2, 5 ve 7 yıllık getirisinin tatil etiketindeki ve ertesi "
                      "etiketteki mutlak günlük değişimi karşılaştırıldı; hareket tatil etiketinde ve ertesi gün "
                      "donmuşsa etiket piyasadan bir iş günü geridedir.",
            "kaynak": ["dibs_egri_gunluk", "fonlama_gunluk"]}


@lru_cache(maxsize=4)
def _degisim(hiza: str = HIZA) -> pd.DataFrame:
    """Türkiye günlük değişim çerçevesi (`ortak_olc.tr_gunluk_degisim`): DİBS
    düğümleri bp, USD/TRY Yahoo ve TCMB log %; cuma tuzağı boşaltılmış."""
    return oo.tr_gunluk_degisim(hiza, DIBS_DUGUM, kur=True, tcmb=True, cuma_dus=True)


def sakin_gunler(index: pd.DatetimeIndex, olaylar, pencere: int = 2) -> pd.DatetimeIndex:
    """Olay günlerinin ±pencere iş günü dışında kalan günler (olay_profili ile aynı tanım)."""
    poz = set()
    for o in pd.DatetimeIndex(olaylar):
        j = index.searchsorted(o)
        if j < len(index) and index[j] == o:
            for k in range(-pencere, pencere + 1):
                poz.add(j + k)
    return index[[i for i in range(len(index)) if i not in poz]]


def _kapi(degisim: pd.Series, olaylar, kur: bool, k_tohum: int) -> dict:
    """Kanonik olay sınaması (`ortak_olc.olay_kapisi`, güçlü kural); kur serisinde
    yönetilen kur dönemi dışarıda."""
    return oo.olay_kapisi(degisim, olaylar, guclu=True, k_tohum=k_tohum,
                          haric=oo.YONETILEN if kur else None)


@lru_cache(maxsize=1)
def abd_gunluk_degisim() -> pd.DataFrame:
    """ABD iş günleri: Δus2 (bp), G10 dolar sepeti, Δlog(USD/EUR) ve Δlog(USD/JPY)
    (%), hepsi aynı gün aralığında (`ortak_olc.abd_gunluk_degisim`: ABD Hazinesi ve
    altı kurun birlikte olduğu, CNBC bozuk kotasyonu çıkarılmış günler)."""
    g = oo.abd_gunluk_degisim()
    return pd.DataFrame({"us2": g["us2_bp"], "dolar": g["dolar_yuzde"],
                         "usd_eur": g["usd_eur_yuzde"], "usd_jpy": g["usd_jpy_yuzde"]}, index=g.index)


def yayim_gunu_orani(degisim: pd.DataFrame, gunler, ciftler, donemler, k_tohum: int = 0) -> dict:
    """Yayım günü ile sıradan günün varyans ve kovaryans oranı (sürpriz değil).

    Her sütun önce kanonik plasebo sınamasından (`ortak_olc.olay_kapisi`, güçlü
    kural) geçer; geçmeyen sütunun oranı ve onu içeren çiftin kovaryansı yazılmaz.
    `varyans_egim_y_x` heteroskedastisite ile tanımlanan eğimdir:
    (kov_olay − kov_sakin) / (var_olay(x) − var_sakin(x))."""
    gunler = pd.DatetimeIndex(gunler)
    kapi_tam = {c: _kapi(degisim[c], gunler, c in KUR_SUTUN, k_tohum + i) for i, c in enumerate(degisim.columns)}
    kapi = {c: oo.kapi_ozeti(k) for c, k in kapi_tam.items()}
    out = {"kapi": kapi}
    for k, a, b, ad in donemler:
        d = degisim.loc[a:b]
        e = d.loc[d.index.intersection(gunler)]
        s = d.loc[sakin_gunler(d.index, gunler)]
        r = {"ad": ad, "n_olay": int(len(e)), "n_sakin": int(len(s)),
             "ilk": _iso(e.index.min()) if len(e) else None, "son": _iso(e.index.max()) if len(e) else None}
        if len(e) < 10:
            r["durum"] = "vaka tablosu"
            out[k] = r
            continue
        for c in d.columns:
            if kapi[c]["gecti"]:
                r[f"varyans_orani_{c}"] = _f(e[c].var() / s[c].var())
            else:
                r[f"varyans_orani_{c}"] = kurulmadi(oo.kapi_sebebi(kapi[c]))
        for x, y in ciftler:
            if not (kapi[x]["gecti"] and kapi[y]["gecti"]):
                r[f"kov_{x}_{y}"] = kurulmadi("çiftin en az bir serisi plasebo sınamasını geçmedi")
                continue
            ee, ss = e[[x, y]].dropna(), s[[x, y]].dropna()
            ce, cs = ee.cov().iloc[0, 1], ss.cov().iloc[0, 1]
            dv = ee[x].var() - ss[x].var()
            r[f"kov_{x}_{y}"] = {"kov_olay": _f(ce), "kov_sakin": _f(cs), "kov_orani": _f(ce / cs) if cs else None,
                                 "kor_olay": _f(ee.corr().iloc[0, 1]), "kor_sakin": _f(ss.corr().iloc[0, 1]),
                                 "varyans_egim": _f((ce - cs) / dv) if dv > 0 else None}
        out[k] = r
    return out


# ═══════════════════════════════════════════════════════════════ p3a
@lru_cache(maxsize=1)
def cikti_acigi() -> pd.DataFrame:
    """Çeyreklik çıktı açığı (log puan ×100): tam örneklem HP ve gerçek zamanlı
    HP (her çeyrekte o güne kadarki veriyle süzülüp son nokta)."""
    g = oo.oku("gsyh_ceyreklik")["gsyh_mta_hacim"].dropna()
    y = np.log(g.values) * 100
    tam = y - hp_suzgec(y)
    rt = np.full(len(y), np.nan)
    for j in range(RT_ASGARI_CEYREK - 1, len(y)):
        yy = y[: j + 1]
        rt[j] = (yy - hp_suzgec(yy))[-1]
    q = pd.PeriodIndex(g.index, freq="Q")
    return pd.DataFrame({"tam": tam, "gercek_zamanli": rt}, index=q)


@lru_cache(maxsize=1)
def _gsyh_yayim() -> dict:
    """Çeyrek → TÜİK yayım günü (bulut takvimi). Yayım çeyrek sonundan en az
    40 gün sonra gelir; her yayım, sonu yayımdan 40 günden fazla önce biten son
    çeyreğe eşlenir. Takvim yoksa boş sözlük (yedek kural devreye girer)."""
    try:
        gunler = bulut.gsyh_gunleri()
    except bulut.VeriYok as h:
        return {"harita": {}, "sebep": str(h)}
    harita = {}
    for g in pd.DatetimeIndex(gunler).sort_values():
        q = (g - pd.Timedelta(days=40)).to_period("Q")
        if q.asfreq("D", "end").to_timestamp() >= g - pd.Timedelta(days=40):
            q = q - 1
        harita.setdefault(q, g)           # aynı çeyreğin ikinci kaydı (revizyon) ilk yayımı ezmez
    return {"harita": harita, "sebep": None}


def _yayim_ozeti() -> dict:
    y = _gsyh_yayim()
    h = y["harita"]
    if not h:
        return {"durum": "kurulmadi", "sebep": f"TÜİK GSYH yayım takvimi elde yok ({y['sebep']}); yedek kural kullanıldı"}
    gec = pd.Series({q: (g - q.asfreq("D", "end").to_timestamp()).days for q, g in h.items()})
    return {"n_ceyrek": int(len(h)), "ilk_ceyrek": str(min(h)), "son_ceyrek": str(max(h)),
            "ilk_yayim": _iso(min(h.values())), "son_yayim": _iso(max(h.values())),
            "gecikme_gun_medyan": _f(gec.median()), "gecikme_gun_min": int(gec.min()), "gecikme_gun_max": int(gec.max()),
            "gecikme_gun_medyan_2016_oncesi": _f(gec[[q < pd.Period("2016Q1", "Q") for q in gec.index]].median()),
            "gecikme_gun_medyan_2016_sonrasi": _f(gec[[q >= pd.Period("2016Q1", "Q") for q in gec.index]].median()),
            "kaynak": ["bulut/tuik_takvim"]}


def _rt_ceyrek(m: pd.Period) -> pd.Period:
    """Ay m'de kullanılabilen son çeyrek: ay BAŞLAMADAN yayımlanmış son çeyrek
    (TÜİK takvimi). Takvimin kapsamadığı aylarda yedek kural: bir çeyrek, son
    ayından YAYIM_YEDEK_AY ay sonra kullanılır (2016 öncesi gecikme ~70 gündü,
    kural her yayımın ayından sonrasına düşer)."""
    harita = _gsyh_yayim()["harita"]
    bas = m.to_timestamp()
    if harita and bas > min(harita.values()):
        bilinen = [q for q, g in harita.items() if g < bas]
        if bilinen:
            return max(bilinen)
    hedef = m - YAYIM_YEDEK_AY
    q = hedef.asfreq("Q")
    return q - 1 if q.asfreq("M", "end") > hedef else q


def _aylik_acik(acik: pd.Series, aylar: pd.PeriodIndex, gecikmeli: bool) -> pd.Series:
    acik = acik.dropna()
    son_q = acik.index.max()
    vals = []
    for m in aylar:
        q = _rt_ceyrek(m) if gecikmeli else min(m.asfreq("Q"), son_q)
        vals.append(acik.get(q, np.nan))
    return pd.Series(vals, index=aylar)


def _taylor(r: float, pi: pd.Series, acik: pd.Series) -> pd.Series:
    return r + pi + KATSAYI_PI * (pi - PI_HEDEF) + KATSAYI_ACIK * acik


@lru_cache(maxsize=1)
def _taylor_cercevesi():
    enf = oo.oku("enflasyon_aylik")
    enf.index = pd.PeriodIndex(enf.index, freq="M")
    tufe = enf["tufe"]
    acik_q = cikti_acigi()
    aylar = pd.period_range(TAYLOR_ILK_AY, oo.CIPA_AY, freq="M")
    df = pd.DataFrame(index=aylar)
    yy = (tufe / tufe.shift(12) - 1) * 100
    df["pi_gercek"] = yy.reindex(aylar)
    # ay m'nin TÜFE'si m+1'in ilk günlerinde yayımlanır: ay m'de bilinen son değer m−1'inkidir
    df["pi_gercek_yayimli"] = yy.shift(1).reindex(aylar)
    df["pi_pka"] = enf["pka_12a"].reindex(aylar)
    df["acik_tam"] = _aylik_acik(acik_q["tam"], aylar, False)
    df["acik_gercek_zamanli"] = _aylik_acik(acik_q["gercek_zamanli"], aylar, True)
    bilesim = []
    for pk in ("gercek", "pka"):
        for ak in ("tam", "gercek_zamanli"):
            # gerçek zamanlı açık ay m'nin bilgi kümesidir; aynı bileşimde gerçekleşen enflasyon da
            # o ay yayımlanmış son değerdir (PKA beklentisi ayın içinde toplanır, iki sürümde aynı)
            pi_kol = "pi_pka" if pk == "pka" else ("pi_gercek" if ak == "tam" else "pi_gercek_yayimli")
            for r in R_YILDIZ:
                ad = f"i_{pk}_{ak}_r{int(r)}"
                df[ad] = _taylor(r, df[pi_kol], df[f"acik_{ak}"])
                bilesim.append(ad)
    gcol = [c for c in bilesim if c.startswith("i_gercek")]
    pcol = [c for c in bilesim if c.startswith("i_pka")]
    df["bant_alt"] = df[bilesim].min(axis=1, skipna=True)
    df["bant_ust"] = df[bilesim].max(axis=1, skipna=True)
    df["bant_bilesim"] = df[bilesim].notna().sum(axis=1)
    df["bant_gercek_alt"], df["bant_gercek_ust"] = df[gcol].min(axis=1), df[gcol].max(axis=1)
    df["bant_pka_alt"], df["bant_pka_ust"] = df[pcol].min(axis=1), df[pcol].max(axis=1)
    f = oo.oku("fonlama_gunluk")
    aofm = f["aofm"].resample("MS").mean()
    aofm.index = pd.PeriodIndex(aofm.index, freq="M")
    pol_f = f["politika"].dropna().resample("MS").last()
    pol_f.index = pd.PeriodIndex(pol_f.index, freq="M")
    pol_e = oo.oku("em_politika_aylik")["tur"].dropna()
    pol_e.index = pd.PeriodIndex(pol_e.index, freq="M")
    gecis = pd.Period("2018-09", "M")
    politika = pd.concat([pol_e[pol_e.index < gecis], pol_f[pol_f.index >= gecis]]).sort_index()
    df["aofm"] = aofm.reindex(aylar)
    df["politika"] = politika.reindex(aylar)
    return df, bilesim, acik_q, f["politika"].dropna()


def _konum(x: pd.DataFrame, alt: str, ust: str) -> dict:
    a = x["aofm"] < x[alt]
    u = x["aofm"] > x[ust]
    return {"alt_pay": _f(a.mean()), "ic_pay": _f((~a & ~u).mean()), "ust_pay": _f(u.mean()),
            "aofm_eksi_alt_ort_puan": _f((x["aofm"] - x[alt]).mean()),
            "aofm_eksi_ust_ort_puan": _f((x["aofm"] - x[ust]).mean())}


def p3a() -> dict:
    df, bilesim, acik_q, _ = _taylor_cercevesi()
    tam = df.dropna(subset=["aofm"])
    tam = tam[tam["bant_bilesim"] == len(bilesim)]
    donem = {}
    for k, a, b, ad in DONEM_TAYLOR:
        x = tam.loc[pd.Period(a, "M"):pd.Period(b, "M")]
        if not len(x):
            continue
        donem[k] = {"ad": ad, "n": int(len(x)), "ilk": str(x.index.min()), "son": str(x.index.max()),
                    "tum_bant": _konum(x, "bant_alt", "bant_ust"),
                    "gercek_enflasyon_bandi": _konum(x, "bant_gercek_alt", "bant_gercek_ust"),
                    "pka_bandi": _konum(x, "bant_pka_alt", "bant_pka_ust"),
                    "bant_genislik_ort_puan": _f((x["bant_ust"] - x["bant_alt"]).mean())}
    m = oo.CIPA_AY
    s = df.loc[m]
    son = {"ay": str(m), "pi_gercek_yuzde": _f(s["pi_gercek"]), "pi_pka_yuzde": _f(s["pi_pka"]),
           "pi_gercek_yayimli_yuzde": _f(s["pi_gercek_yayimli"]),
           "acik_tam_puan": _f(s["acik_tam"]), "acik_gercek_zamanli_puan": _f(s["acik_gercek_zamanli"]),
           "acik_tam_ceyrek": str(min(m.asfreq("Q"), acik_q["tam"].dropna().index.max())),
           "acik_gercek_zamanli_ceyrek": str(_rt_ceyrek(m)),
           "bilesimler_yuzde": {c[2:]: _f(s[c]) for c in bilesim},
           "bant_alt_yuzde": _f(s["bant_alt"]), "bant_ust_yuzde": _f(s["bant_ust"]),
           "bant_gercek_alt_yuzde": _f(s["bant_gercek_alt"]), "bant_gercek_ust_yuzde": _f(s["bant_gercek_ust"]),
           "bant_pka_alt_yuzde": _f(s["bant_pka_alt"]), "bant_pka_ust_yuzde": _f(s["bant_pka_ust"]),
           "aofm_ay_ort_yuzde": _f(s["aofm"]), "politika_ay_sonu_yuzde": _f(s["politika"]),
           "aofm_eksi_bant_alt_puan": _f(s["aofm"] - s["bant_alt"]),
           "aofm_eksi_bant_ust_puan": _f(s["aofm"] - s["bant_ust"]),
           "aofm_eksi_pka_bant_alt_puan": _f(s["aofm"] - s["bant_pka_alt"]),
           "aofm_eksi_pka_bant_ust_puan": _f(s["aofm"] - s["bant_pka_ust"]),
           "aofm_konum": ("bandın altında" if s["aofm"] < s["bant_alt"] else
                          "bandın üstünde" if s["aofm"] > s["bant_ust"] else "bandın içinde")}
    a = acik_q.dropna()
    a2 = a[a.index >= pd.Period("2005Q1", "Q")]
    fark = (a2["tam"] - a2["gercek_zamanli"]).abs()
    acik_ozet = {"n": int(len(a2)), "ilk": str(a2.index.min()), "son": str(a2.index.max()),
                 "korelasyon": _f(a2.corr().iloc[0, 1]),
                 "ort_mutlak_fark_puan": _f(fark.mean()), "azami_mutlak_fark_puan": _f(fark.max()),
                 "azami_fark_ceyrek": str(fark.idxmax()),
                 "isaret_uyum_pay": _f((np.sign(a2["tam"]) == np.sign(a2["gercek_zamanli"])).mean()),
                 "son_ceyrek": str(a.index.max()), "son_tam_puan": _f(a["tam"].iloc[-1]),
                 "son_gercek_zamanli_puan": _f(a["gercek_zamanli"].iloc[-1]),
                 "bir_onceki_ceyrek": str(a.index[-2]), "bir_onceki_tam_puan": _f(a["tam"].iloc[-2]),
                 "bir_onceki_gercek_zamanli_puan": _f(a["gercek_zamanli"].iloc[-2]),
                 "en_dusuk_tam_puan": _f(a["tam"].min()), "en_dusuk_tam_ceyrek": str(a["tam"].idxmin()),
                 "yontem": "Mevsim ve takvim etkisinden arındırılmış reel GSYH'nin logu HP süzgecinden (λ = 1600) "
                           "geçirildi; tam örneklem sürümü iki yanlı, gerçek zamanlı sürüm her çeyrekte yalnız o "
                           "güne kadarki veriyle süzülüp son noktası alındı (bugünkü veri sürümüyle; revizyon ölçülmez).",
                 "kaynak": ["gsyh_ceyreklik"]}
    once = df.loc[pd.Period("2013-01", "M"):pd.Period("2018-05", "M")].dropna(subset=["aofm", "politika"])
    repo_notu = {"n": int(len(once)), "ilk": str(once.index.min()), "son": str(once.index.max()),
                 "aofm_eksi_politika_ort_puan": _f((once["aofm"] - once["politika"]).mean()),
                 "aofm_eksi_politika_azami_puan": _f((once["aofm"] - once["politika"]).max()),
                 "azami_ay": str((once["aofm"] - once["politika"]).idxmax()),
                 "yontem": "Haziran 2018 öncesinde AOFM ile bir hafta vadeli repo arasındaki aylık fark; o dönemde etkin "
                           "fonlama faizi AOFM'dir.", "kaynak": ["fonlama_gunluk", "em_politika_aylik"]}
    dibs = oo.oku("dibs_egri_gunluk")
    r5 = dibs["r5y"].dropna()
    r5s = r5[r5.index > oo.CIPA_GUN - pd.Timedelta(days=365)]
    r_kiyas = {"tufex_r5y_son_yuzde": _f(r5.iloc[-1]), "tufex_r5y_son_etiket": _iso(r5.index[-1]),
               "tufex_r5y_son12ay_medyan_yuzde": _f(r5s.median()), "tufex_r5y_son12ay_n": int(len(r5s)),
               "tufex_r2y_son_yuzde": _f(dibs["r2y"].dropna().iloc[-1]),
               "not": "r* ölçülmez: 2 puan Taylor (1993) değeri, 0 ve 4 iki puanlık belirsizlik kenarıdır "
                      "(varsayım). Kıyas için piyasanın 5 yıllık reel getirisi verilir (TÜFEX, seyrek kotasyon)."}
    return {
        "yontem": "Kural faizi r* + π + 0,5(π − 5) + 0,5·açık iki enflasyon ölçüsü (gerçekleşen yıllık TÜFE, "
                  "PKA 12 ay sonrası beklentisi), iki çıktı açığı sürümü ve üç r* ile aylık hesaplandı; gerçek "
                  "zamanlı sürümde açık da gerçekleşen enflasyon da o ay bilinen son değerdir; bant on iki "
                  "bileşimin en düşüğü ile en yükseğidir ve AOFM'nin aylık ortalamasıyla kıyaslandı.",
        "kaynak": ["enflasyon_aylik", "gsyh_ceyreklik", "fonlama_gunluk", "em_politika_aylik", "dibs_egri_gunluk"],
        "n": int(len(tam)), "ilk": str(tam.index.min()), "son": str(tam.index.max()),
        "parametreler": {"pi_hedef_yuzde": PI_HEDEF, "katsayi_pi": KATSAYI_PI, "katsayi_acik": KATSAYI_ACIK,
                         "r_yildiz_yuzde": list(R_YILDIZ), "hp_lambda": HP_LAMBDA,
                         "yayim_gecikmesi_kural": "gerçek zamanlı açıkta bir ay, o ay başlamadan TÜİK'in yayımladığı "
                                                  "son çeyreği kullanır; takvimin kapsamadığı aylarda çeyrek, son "
                                                  "ayından dört ay sonra kullanılır",
                         "cipa_ayinda_kullanilan_ceyrek": str(_rt_ceyrek(oo.CIPA_AY)),
                         "cipa_ayindan_sonraki_ceyrek_yayimi": _iso(_gsyh_yayim()["harita"].get(_rt_ceyrek(oo.CIPA_AY) + 1)),
                         "yayim_takvimi": _yayim_ozeti(),
                         "tam_ornek_kural": "ayın kendi çeyreği; veri bitmişse son çeyrek taşınır",
                         "enflasyon_zamanlama": "tam örneklem bileşimlerinde ayın kendi yıllık TÜFE'si, gerçek zamanlı "
                                                "bileşimlerde ay içinde yayımlanmış son yıllık TÜFE (bir önceki ayınki); "
                                                "PKA beklentisi ayın içinde toplandığı için iki sürümde aynıdır",
                         "politika_kaynak": "Eylül 2018'den fonlama politika faizi, öncesi BIS Türkiye politika "
                                            "faizi; ikisi de ay sonu"},
        "son_ay": son,
        "donemler": donem,
        "cikti_acigi": acik_ozet,
        "repo_etkin_degildi": repo_notu,
        "r_yildiz_kiyas": r_kiyas,
    }


def arac_taylor() -> dict:
    """Araç 1'in (Taylor kuralı) açılış girdileri."""
    df, _, _, pol = _taylor_cercevesi()
    s = df.loc[oo.CIPA_AY]
    acik = [_f(s["acik_tam"]), _f(s["acik_gercek_zamanli"])]
    kur = oo.oku("kuresel_aylik")
    fa = kur["faiz_abd"].dropna()
    at = kur["abd_tufe"].dropna()
    at_yy = ((at / at.shift(12) - 1) * 100).dropna()
    return {
        "ay": str(oo.CIPA_AY),
        "pi_gercek_yuzde": _f(s["pi_gercek"]), "pi_pka_yuzde": _f(s["pi_pka"]),
        "pi_hedef_yuzde": PI_HEDEF, "katsayi_pi": KATSAYI_PI, "katsayi_acik": KATSAYI_ACIK,
        "acik_tam_puan": acik[0], "acik_gercek_zamanli_puan": acik[1],
        "acik_alt_puan": min(acik), "acik_ust_puan": max(acik),
        "r_yildiz_yuzde": list(R_YILDIZ), "r_yildiz_varsayilan_yuzde": R_YILDIZ_VARSAYILAN,
        "aofm_ay_ort_yuzde": _f(s["aofm"]),
        "politika_yuzde": _f(pol.iloc[-1]), "politika_gun": _iso(pol.index[-1]),
        "yabanci": {"politika_abd_yuzde": _f(fa.iloc[-1]), "politika_abd_ay": str(fa.index[-1].to_period("M")),
                    "tufe_abd_yillik_yuzde": _f(at_yy.iloc[-1]), "tufe_abd_ay": str(at_yy.index[-1].to_period("M")),
                    "not": "ABD beklenti serisi arşivde yok; beklenen enflasyon yerine son yıllık TÜFE açılış "
                           "değeridir (araçta değiştirilebilir). ABD politika faizi BIS tanımıdır."},
        "yontem": "Aracın açılış değerleri çıpa ayının ölçümleridir; kural faizi ve beklenen reel faiz farkı "
                  "(B bloğu) araçta bu girdilerden hesaplanır.",
        "kaynak": ["enflasyon_aylik", "gsyh_ceyreklik", "fonlama_gunluk", "kuresel_aylik"],
    }


def sekil_03() -> dict:
    df, _, _, _ = _taylor_cercevesi()
    x = df.loc[pd.Period("2011-01", "M"):]
    kol = ["bant_alt", "bant_ust", "bant_gercek_alt", "bant_gercek_ust", "bant_pka_alt", "bant_pka_ust",
           "aofm", "politika", "pi_gercek", "pi_gercek_yayimli", "pi_pka", "acik_tam", "acik_gercek_zamanli"]
    return {"baslik": "Türkiye Taylor bandı", "birim": "%, açık için puan", "siklik": "aylık",
            "n": int(len(x)), "ilk": str(x.index.min()), "son": str(x.index.max()),
            "yontem": "Taylor kuralı bandı (gerçekleşen, yayımlanan ve PKA beklenen enflasyonla) ile AOFM ve politika "
                      "faizi, aylık.",
            "kaynak": ["enflasyon_aylik", "gsyh_ceyreklik", "fonlama_gunluk", "em_politika_aylik"],
            "tarih": [str(p) for p in x.index], **{k: _liste(x[k]) for k in kol},
            "donemler": [[a, b, ad] for _, a, b, ad in DONEM_TAYLOR],
            "not": "AOFM aylık ortalama, politika faizi ay sonu; 2013 öncesinde bant yalnız gerçekleşen "
                   "enflasyonla kurulur (PKA 2013'te başlar). Haziran 2018 öncesinde politika faizi etkin oran değildi."}


# ═══════════════════════════════════════════════════════════════ p3b
def _gurultu(seri: pd.Series, olaylar) -> dict:
    out = {}
    for k, a, b, ad in [("tum", "2016-01-01", str(oo.CIPA_GUN.date()), "2016–2026")] + DONEM_PPK:
        s = seri.loc[a:b].dropna()
        olay = s.loc[s.index.intersection(pd.DatetimeIndex(olaylar))]
        sakin = s.loc[sakin_gunler(s.index, olaylar)]
        if len(olay) < 3 or len(sakin) < 30:
            continue
        so, se = float(sakin.std()), float(olay.std())
        out[k] = {"ad": ad, "n_olay": int(len(olay)), "n_sakin": int(len(sakin)),
                  "sigma_sakin_bp": so, "sigma_olay_bp": se, "varyans_orani": (se / so) ** 2 if so else None,
                  "sakin_iki_sigma_ustu_olay_pay": _f((olay.abs() > 2 * so).mean())}
    return out


def anket_surprizi(ppk: pd.Series, beklenti: pd.DataFrame) -> pd.Series:
    """Karar − karar ayının PKA toplantı beklentisi (bp) (tuzak 7)."""
    b = beklenti["politika_beklenti"].dropna()
    b.index = pd.DatetimeIndex(b.index).to_period("M")
    vals = {t: (v - b[t.to_period("M")]) * 100 for t, v in ppk.items() if t.to_period("M") in b.index}
    return pd.Series(vals, name="anket_bp", dtype=float)


def anket_kirli(ppk: pd.Series, beklenti: pd.DataFrame) -> dict:
    """Karardan SONRA toplanmış görünen aynı ay anketleri (tuzak 13). Ölçüt:
    karar ayın ilk yarısında, politika faizini en az 25 bp değiştirmiş, ve
    aynı ay anketinin iki ufku birden (cari ay ve bir sonraki ufuk: cari ay
    sonu ile üç ay sonrası, ya da ilk ile ikinci toplantı) kararı baz puanına
    kadar tutturuyor. Önceden doğru tahmin edilmiş bir karar tek ufukta eşleşir;
    iki ufkun birden kararla aynı olması kararın bilindiğinin izidir."""
    b = beklenti.copy()
    b.index = pd.DatetimeIndex(b.index).to_period("M")
    onceki = ppk.shift(1)
    if KARAR_ILK in onceki.index:
        onceki.loc[KARAR_ILK] = oo.oku("fonlama_gunluk").loc[KARAR_ILK, "aofm"]
    ikinci = {"cari_ay_sonu_repo": "ay3_repo", "ilk_toplanti": "ikinci_toplanti"}
    out = {}
    for t, v in ppk.items():
        m = t.to_period("M")
        if m not in b.index or t.day > 15 or not np.isfinite(onceki.get(t, np.nan)):
            continue
        r = b.loc[m]
        seri = r.get("seri")
        c2 = ikinci.get(seri)
        if c2 is None or c2 not in b.columns or not np.isfinite(r.get(c2, np.nan)):
            continue
        degisim = (v - onceki[t]) * 100
        if abs(degisim) >= 25 and abs(r["politika_beklenti"] - v) * 100 < 1 and abs(r[c2] - v) * 100 < 1:
            out[t] = {"tarih": _iso(t), "karar_degisimi_bp": _f(degisim), "anket_yuzde": _f(r["politika_beklenti"]),
                      "ikinci_ufuk_yuzde": _f(r[c2]), "karar_yuzde": _f(v)}
    return out


def _karar_degisimi(ppk: pd.Series) -> pd.Series:
    onceki = ppk.shift(1)
    onceki.loc[KARAR_ILK] = oo.oku("fonlama_gunluk").loc[KARAR_ILK, "aofm"]
    return ((ppk - onceki) * 100).loc[KARAR_ILK:].rename("karar_bp")


def _dagilim(s: pd.Series) -> dict:
    s = s.dropna()
    return {"n": int(len(s)), "sifir": int((s.abs() < 1).sum()), "pozitif": int((s >= 1).sum()),
            "negatif": int((s <= -1).sum()), "ort_bp": _f(s.mean()), "medyan_bp": _f(s.median()),
            "ort_mutlak_bp": _f(s.abs().mean()), "sd_bp": _f(s.std()),
            "en_buyuk": {"tarih": _iso(s.idxmax()), "bp": _f(s.max())} if len(s) else None,
            "en_kucuk": {"tarih": _iso(s.idxmin()), "bp": _f(s.min())} if len(s) else None}


def p3b() -> dict:
    ppk = oo.oku("ppk_kararlari")["politika"]
    olaylar = ppk.index
    hz = dibs_gecikme()
    deg = _degisim(HIZA)
    ev = deg.loc[deg.index.intersection(olaylar)]
    kaynak = ["ppk_kararlari", "dibs_egri_gunluk", "fonlama_gunluk", "usdtry_yahoo_gunluk", "usdtry_tcmb_gunluk",
              "bulut/evds_pka_toplanti"]

    # hiza: üç tarih sözleşmesinde plasebo sınaması (ham etiket · sabah hizası · gün sonu hizasında iki gün)
    sakli = _degisim("ham")
    sabah = _degisim("sabah")
    g_hz = oo.dibs(HIZA, ("n3a", "n1y", "n2y", "n5y"))
    iki = {c: (g_hz[c].shift(-1) - g_hz[c].shift(1)) * 100 for c in g_hz.columns}
    hiza = {"dibs_gecikme": hz, "hiza": HIZA, "hiza_kayma_is_gunu": oo.DIBS_KAYMA[HIZA],
            "kapi_sakli_tarih": {c: oo.kapi_ozeti(_kapi(sakli[c], olaylar, False, 40 + i))
                                 for i, c in enumerate(("n3a", "n6a", "n1y", "n2y", "n5y"))},
            "kapi_sabah_hizasi": {c: oo.kapi_ozeti(_kapi(sabah[c], olaylar, False, 50 + i))
                                  for i, c in enumerate(("n3a", "n6a", "n1y", "n2y", "n5y"))},
            "kapi_iki_gunluk": {c: oo.kapi_ozeti(_kapi(iki[c], olaylar, False, 60 + i)) for i, c in enumerate(iki)},
            "not": "DİBS değişimi gün sonu hizasıyla (D gününe D+2 iş günü etiketli değer) USD/TRY kapanışıyla aynı "
                   "piyasa gününe oturtuldu; ham etiket ve sabah hizası (bir iş günü) kıyas için; iki günlük pencere "
                   "gün sonu hizasında karar günü ile ertesi günün toplamıdır."}
    kapi_tam = {c: _kapi(deg[c], olaylar, c in KUR_SUTUN, 10 + i)
                for i, c in enumerate(("n3a", "n6a", "n1y", "n2y", "n5y", "usdtry", "usdtry_tcmb"))}
    kapilar = {c: oo.kapi_ozeti(k) for c, k in kapi_tam.items()}
    gurultu = {c: _gurultu(deg[c], olaylar) for c in ("n3a", "n6a", "n1y")}

    # anket sürprizi (bulut)
    karar = _karar_degisimi(ppk)
    kirli = {}
    try:
        bek = bulut.pka_toplanti_beklentisi()
        ans = anket_surprizi(ppk, bek)
        kirli = anket_kirli(ppk, bek)
        ans = ans.drop([t for t in kirli if t in ans.index])
        seri_turu = bek["seri"].dropna().astype(str)
        seri_turu.index = pd.DatetimeIndex(seri_turu.index).to_period("M")
    except bulut.VeriYok as h:
        ans, seri_turu = None, None
        anket_hata = f"anketin toplantıya özgü faiz beklentisi elde yok ({h})"

    yon_maske = ~oo.yonetilen_mi(ev.index)
    saglamlik = [
        ("etkin_oran_donemi", (ev.index > KARAR_ILK) & yon_maske,
         "Haziran 2018 sadeleşmesinden sonra, yönetilen kur dönemi hariç (anketin sorduğu oran etkin politika faizi)"),
        ("d2018_2020_etkin", (ev.index > KARAR_ILK) & (ev.index <= "2020-12-31"),
         "Haziran 2018…2020 (2016–2020 döneminin anketin etkin oranı sorduğu kısmı)"),
        ("ayin_ilk_yarisi_haric", (ev.index.day > 15) & yon_maske,
         "ayın ilk yarısındaki kararlar hariç, yönetilen kur dönemi hariç (anket zamanlaması belirsiz kararlar)"),
    ]
    tepki = {}
    for hedef, birim in (("usdtry", "% / 100 bp anket sürprizi"), ("n2y", "bp / 100 bp anket sürprizi"),
                         ("n5y", "bp / 100 bp anket sürprizi")):
        if not kapilar[hedef]["gecti"]:
            tepki[hedef] = kurulmadi(oo.kapi_sebebi(kapilar[hedef]), kapi=kapilar[hedef])
            continue
        if ans is None:
            tepki[hedef] = kurulmadi(anket_hata)
            continue
        tepki[hedef] = {"birim": birim}
        x = (ans / 100).rename("anket_100bp")
        for k, a, b, ad in DONEM_PPK:
            e = ev.loc[a:b]
            r = oo.regresyon(e[hedef], x.reindex(e.index), asgari_bilgili=10)
            r["ad"] = ad
            if k == "d2016_2020":
                r["not_soru"] = ("Haziran 2018 öncesinde anket bir hafta vadeli repoyu sorar; o dönemde etkin oran "
                                 "AOFM'dir ve koridor kararları sürprize girmez (sağlamlık: Haziran 2018…2020 satırı)")
            if k == "yonetilen" and hedef == "usdtry":
                r["yonetilen_kur"] = True
                if r.get("durum") == "vaka tablosu":
                    r["not"] = ("yönetilen dönemde eğimi az sayıda sıfırdan farklı sürpriz tanımlıyor; test kurulmaz, "
                                "noktalar verilir")
                elif r.get("t") is not None and abs(r["t"]) < 2:
                    r["not"] = "kur yönetildiği için eğimin sıfırdan ayrışmaması tasarım gereğidir"
                elif r.get("t") is not None:
                    r["not"] = "yönetilen dönemde de eğim sıfırdan ayrışıyor"
            tepki[hedef][k] = r
        hm = ev.index[yon_maske]
        r = oo.regresyon(ev.loc[hm, hedef], x.reindex(hm), asgari_bilgili=10)
        r["ad"] = "2016–2026, yönetilen kur dönemi hariç (havuzlanmış; sağlamlık)"
        tepki[hedef]["yonetilen_haric"] = r
        for k, maske, ad in saglamlik:
            sec = ev.index[maske]
            tepki[hedef][k] = {**oo.regresyon(ev.loc[sec, hedef], x.reindex(sec), asgari_bilgili=10), "ad": ad}
    if not kapilar["usdtry_tcmb"]["gecti"]:
        tepki["usdtry_tcmb"] = kurulmadi(
            oo.kapi_sebebi(kapilar["usdtry_tcmb"]), kapi=kapilar["usdtry_tcmb"],
            **{"not": "sağlamlık sınaması: TCMB gösterge kurunun ölçüm anı 14:00 kararından öncedir; karar tepkisi "
                      "ertesi iş günü etiketine düşer ve profil ertesi günde tepe yapar"})
    elif ans is not None:
        x = (ans / 100).rename("anket_100bp")
        hm = ev.index[yon_maske]
        tepki["usdtry_tcmb"] = {**oo.regresyon(ev.loc[hm, "usdtry_tcmb"], x.reindex(hm), asgari_bilgili=10),
                                "ad": "sağlamlık: TCMB gösterge kuru, yönetilen kur dönemi hariç"}

    if ans is not None:
        a_d = {"tum": _dagilim(ans)}
        for k, a, b, ad in DONEM_PPK:
            a_d[k] = {"ad": ad, **_dagilim(ans.loc[a:b])}
        kd = pd.concat([karar, ans], axis=1, sort=True).dropna()
        kk = {"tum": oo.regresyon(kd["anket_bp"], kd["karar_bp"], asgari_bilgili=10)}
        kk["tum"]["ad"] = f"{_iso(kd.index.min())[:7]}…{_iso(kd.index.max())[:7]}"
        for k, a, b, ad in DONEM_PPK:
            z = kd.loc[max(pd.Timestamp(a), KARAR_ILK):b]
            if len(z):
                kk[k] = {**oo.regresyon(z["anket_bp"], z["karar_bp"], asgari_bilgili=10), "ad": ad}
        degisen = kd[kd["karar_bp"] != 0]
        anket = {
            "yontem": "Anket sürprizi, PPK kararı ile karar ayındaki Piyasa Katılımcıları Anketi'nin politika faizi "
                      "beklentisinin farkıdır (baz puan); Mayıs 2025'e kadar soru 'cari ay sonu bir hafta vadeli "
                      "repo', sonra 'ilk toplantı'dır.",
            "kaynak": ["ppk_kararlari", "bulut/evds_pka_toplanti"],
            "n": int(len(ans)), "ilk": _iso(ans.index.min()), "son": _iso(ans.index.max()),
            "soru": {"cari_ay_sonu_repo": int((seri_turu == "cari_ay_sonu_repo").sum()),
                     "ilk_toplanti": int((seri_turu == "ilk_toplanti").sum())},
            "eslesmeyen": [_iso(t) for t in ppk.index if t not in ans.index and t not in kirli],
            "karardan_sonra_toplanmis": {
                "kararlar": list(kirli.values()),
                "yontem": "Ayın ilk yarısındaki ve faizi en az 25 bp değiştiren kararlarda, aynı ay anketinin iki ufku "
                          "birden (cari ay sonu ile üç ay sonrası, ya da ilk ile ikinci toplantı) kararı baz puanına "
                          "kadar veriyorsa anket karardan sonra toplanmış sayıldı ve sürprizden çıkarıldı.",
                "not": "Eşleşen tek ufuk önceden doğru tahmin edilmiş bir karar da olabilir; o kararlar sürprizde "
                       "kalır, sağlamlık için ayın ilk yarısındaki bütün kararları dışarıda bırakan satır ayrıca verilir."},
            "dagilim": a_d,
            "karar_ile": {"n": int(len(kd)), "ilk": _iso(kd.index.min()), "son": _iso(kd.index.max()),
                          "n_degisen": int(len(degisen)),
                          "degisen_kararda_sifir_surpriz_pay": _f((degisen["anket_bp"].abs() < 1).mean()),
                          "sabit_kararda_sifir_surpriz_pay": _f((kd.loc[kd["karar_bp"] == 0, "anket_bp"].abs() < 1).mean()),
                          "yon_uyum_pay": _f((np.sign(degisen["karar_bp"]) ==
                                              np.sign(degisen["anket_bp"]))[degisen["anket_bp"].abs() >= 1].mean()),
                          "regresyon": kk,
                          "yontem": "Anket sürprizi kararın politika faizinde yaptığı değişime (baz puan) Newey–West "
                                    "ile regresyonlandı; eğim değişimin beklenmeyen payıdır."},
            "erken_karar_kaniti": [{"tarih": _iso(t), "gun": int(t.day), "anket_bp": _f(ans[t])}
                                   for t in ans.index if t.day <= 12 and abs(ans[t]) >= 1],
        }
    else:
        anket = kurulmadi(anket_hata)

    # tanı: ima sürprizi (3 aylık düğüm) sınamayı geçmezse yayımlanmaz
    dibs_gecen = [c for c in ("n3a", "n6a", "n1y", "n2y", "n5y") if kapilar[c]["gecti"]]
    dibs_gecmeyen = [c for c in ("n3a", "n6a", "n1y", "n2y", "n5y") if not kapilar[c]["gecti"]]
    tani = {"yayimlanmaz": not kapilar["n3a"]["gecti"],
            "sebep": ("3 aylık düğüm PPK günlerinde plasebo sınamasını geçmedi (" + oo.kapi_sebebi(kapilar["n3a"]) +
                      "); aşağıdaki sayılar yalnız tanıdır" if not kapilar["n3a"]["gecti"] else
                      "3 aylık düğüm plasebo sınamasını geçti; ima sürprizinin tanı sayıları"),
            "kapiyi_gecen_dugum": dibs_gecen, "kapiyi_gecmeyen_dugum": dibs_gecmeyen,
            "ima_anket_korelasyonu": {c: _f(pd.concat([ev[c], ans], axis=1, sort=True).dropna().corr().iloc[0, 1])
                                      for c in ("n3a", "n6a", "n1y", "n2y")} if ans is not None else None,
            "ima_ile_karar": oo.regresyon(ev["n3a"], karar.reindex(ev.index)),
            "kur_ile_ima": {k: {**oo.regresyon(ev.loc[a:b, "usdtry"], ev.loc[a:b, "n3a"]), "ad": ad}
                            for k, a, b, ad in DONEM_PPK}}

    tablo = ev[["n3a", "n6a", "n1y", "n2y", "n5y", "usdtry"]]
    return {
        "yontem": "Her PPK karar günü için DİBS düğümlerinin (gün sonu hizasıyla: D gününe D+2 iş günü etiketli "
                  "değer) ve USD/TRY'nin aynı piyasa günündeki değişimi ölçüldü; önce plasebo sınaması (güçlü kural) "
                  "soruldu, kur tepkisi kararla anket beklentisinin farkına dönem dönem Newey–West ile regresyonlandı.",
        "kaynak": kaynak,
        "n": int(len(ev)), "ilk": _iso(ev.index.min()), "son": _iso(ev.index.max()),
        "saat": "Karar 14:00 TSİ; DİBS gösterge değeri bir önceki iş gününün sabah sabitlemesidir, gün sonu "
                "hizasında D'nin değeri D+1 sabahının sabitlemesi olur ve 14:00 kararını taşır; USD/TRY 18.12.2023'ten "
                "İstanbul 18:00, öncesi Londra gece yarısı (cuma değişimi hafta sonunu taşıdığı için boşaltıldı); TCMB "
                "gösterge kuru 15:30'da ilan edilir ama ölçüm anı karardan öncedir (14:00 kararının tepkisi ertesi iş "
                "günü etiketine düşer). Getiri ve kur aynı piyasa gününün değişimidir.",
        "hiza": hiza,
        "kapi": kapilar,
        "gurultu": gurultu,
        "ima_surprizi": (kurulmadi("ima sürprizi (DİBS 3 aylık değişimi) PPK günlerinde plasebo sınamasını geçmedi: "
                                   + oo.kapi_sebebi(kapilar["n3a"]), kapi=kapilar["n3a"])
                         if not kapilar["n3a"]["gecti"] else
                         kurulmadi("3 aylık düğüm plasebo sınamasını geçti ama ima sürprizi bu ölçüm katmanında kurulmadı; "
                                   "tanı satırları `tani` altında", kapi=kapilar["n3a"])),
        "tepki": tepki,
        "anket_surprizi": anket,
        "tani": tani,
        "olaylar": {"tarih": [_iso(t) for t in ev.index], "politika_yuzde": _liste(ppk.reindex(ev.index)),
                    "anket_bp": _liste(ans.reindex(ev.index)) if ans is not None else None,
                    **{f"d_{c}": _liste(tablo[c]) for c in tablo.columns},
                    "birim": "DİBS bp, kur log %"},
    }


# ═══════════════════════════════════════════════════════════════ p3c
@lru_cache(maxsize=1)
def haftalik_3c() -> pd.DataFrame:
    a = oo.oku("abd_hazine_gunluk")["us2"]
    d = oo.oku("bund_gunluk")["de2_par"]
    e = oo.cnbc_kur()["eur"]
    g = pd.concat([a, d, e], axis=1, sort=True).dropna()
    g = g[g.index.dayofweek < 5]
    h = g.groupby(g.index.to_period("W-FRI")).tail(1).copy()
    h["fark"] = h["us2"] - h["de2_par"]
    return h


def p3c() -> dict:
    h = haftalik_3c().copy()
    h["d_fark_10bp"] = h["fark"].diff() * 100 / 10
    h["d_eur"] = np.log(h["eur"]).diff() * 100
    donem = {}
    for k, a, b, ad in DONEM_3C:
        x = h.loc[a:b].dropna()
        if len(x) < 30:
            continue
        donem[k] = {"ad": ad, "n": int(len(x)), "ilk": _iso(x.index.min()), "son": _iso(x.index.max()),
                    "degisim": oo.regresyon(x["d_eur"], x["d_fark_10bp"], ilk_pencere=52),
                    "degisim_korelasyon": _f(x[["d_fark_10bp", "d_eur"]].corr().iloc[0, 1]),
                    "seviye_korelasyon": _f(x[["fark", "eur"]].corr().iloc[0, 1]),
                    "seviye_ar1_fark": oo.ar1(x["fark"]), "seviye_ar1_eur": oo.ar1(x["eur"]),
                    "fark_ilk_puan": _f(x["fark"].iloc[0]), "fark_son_puan": _f(x["fark"].iloc[-1]),
                    "eur_ilk": _f(x["eur"].iloc[0]), "eur_son": _f(x["eur"].iloc[-1])}
    x = h.dropna()
    return {
        "yontem": "ABD ile Almanya 2 yıllık getirileri arasındaki farkın haftalık değişimi (10 baz puan birimi) ile "
                  "EUR/USD'nin haftalık log değişimi (%) dört dönemde Newey–West ile regresyonlandı; seviye "
                  "korelasyonu ayrıca verildi.",
        "kaynak": ["abd_hazine_gunluk", "bund_gunluk", "cnbc_kur_gunluk (bozuk kotasyon günleri çıkarılmış)"],
        "n": int(len(x)), "ilk": _iso(x.index.min()), "son": _iso(x.index.max()),
        "birim": "eğim: EUR/USD % değişim / 10 bp fark değişimi; eksi işaret, ABD lehine açılan farkla doların "
                 "değer kazancıdır",
        "saat": "ABD Hazinesi par getirisi New York kapanışı, Bund Bundesbank günlük (Frankfurt), EUR/USD New York "
                "17:00; haftanın üç serinin birlikte bulunduğu son günü alınır. Avrupa getirisi New York öğleden "
                "sonrasını görmez.",
        "uyari": "Seviye korelasyonu sahte olabilir: iki seviye de birim köke yakın (birinci dereceden özilinti 1'e "
                 "yakın); ilişki değişimlerde sınanır.",
        "ilk_donem_notu": "CNBC kur arşivi 03.01.2000'de başlar; ilk dönem fiilen 2000–2007'dir.",
        "donemler": donem,
    }


def sekil_04() -> dict:
    h = haftalik_3c()
    return {"baslik": "ABD–Almanya 2 yıllık farkı ve EUR/USD", "siklik": "haftalık",
            "birim": "fark: puan; EUR/USD: düzey",
            "n": int(len(h)), "ilk": _iso(h.index.min()), "son": _iso(h.index.max()),
            "yontem": "Haftalık ABD 2 yıllık par getirisi ile Bund 2 yıllık par getirisinin farkı ve EUR/USD.",
            "kaynak": ["abd_hazine_gunluk", "bund_gunluk", "cnbc_kur_gunluk (bozuk kotasyon günleri çıkarılmış)"],
            "tarih": [_iso(t) for t in h.index], "fark_puan": _liste(h["fark"]),
            "eurusd": _liste(h["eur"]), "us2_yuzde": _liste(h["us2"]), "de2_yuzde": _liste(h["de2_par"]),
            "donemler": [[a, b, ad] for _, a, b, ad in DONEM_3C]}


# ═══════════════════════════════════════════════════════════════ p3d
def p3d() -> dict:
    out = {"yontem": "Yayım günlerinde ve olay penceresi dışındaki sıradan günlerde günlük değişimlerin varyansı ve "
                     "kovaryansı karşılaştırıldı; oran 1'in üstündeyse yayım günü bilgi taşır. Sayısal beklenti "
                     "olmadığı için sürpriz hesaplanmaz.",
           "kaynak": ["abd_hazine_gunluk", "cnbc_kur_gunluk", "dibs_egri_gunluk", "usdtry_yahoo_gunluk",
                      "bulut/bls_takvim", "bulut/tuik_takvim"]}
    try:
        g = bulut.abd_istihdam_gunleri()
        d = abd_gunluk_degisim()[["us2", "dolar"]]
        r = yayim_gunu_orani(d, g, [("us2", "dolar")],
                             [("tum", "2000-01-01", "2026-09-30", "2000–2026"),
                              ("d2000_2019", "2000-01-01", "2019-12-31", "2000–2019"),
                              ("d2020_2026", "2020-01-01", "2026-09-30", "2020–2026")], k_tohum=100)
        r["saat"] = "İstihdam 08:30 New York; ABD Hazinesi kapanışı ve CNBC 17:00 New York aynı günü içerir."
        r["birim"] = "us2 baz puan; dolar altı G10 kurunun eşit ağırlıklı log değişimi, %"
        out["abd_istihdam"] = r
    except bulut.VeriYok as h:
        out["abd_istihdam"] = kurulmadi(f"BLS istihdam yayım günleri elde yok ({h})")
    try:
        g = bulut.gsyh_gunleri()
        d = _degisim(HIZA)[["n2y", "n5y", "usdtry"]]
        r = yayim_gunu_orani(d, g, [("n2y", "usdtry")],
                             [("tum", "2013-01-01", "2026-09-30", "2013–2026"),
                              ("d2023_2026", oo.YON_SONRASI_ILK, "2026-09-30", f"{oo.YON_SONRASI_AY}…2026-09")], k_tohum=110)
        r["saat"] = ("GSYH 10:00 TSİ; DİBS gün sonu hizasında (D'nin değeri D+1 sabahının sabitlemesi) ve USD/TRY akşam "
                     "kapanışı yayımı içerir; 18.12.2023 öncesi cuma kur değişimi boşaltıldı.")
        r["birim"] = "DİBS baz puan; USD/TRY log değişim, %"
        r["n_yayim"] = int(len(g))
        # 10:00 olayında DİBS'in sabah hizası da saatle bağdaşır: sabitlemenin 14:00'ten ÖNCE olduğu
        # ölçülü (PPK 14:00 gün sonu hizasında tepe 0), 10:00'dan SONRA olduğu ise ölçülü değil —
        # sabah hizasında tepe 0 yalnız TÜFE'de 1 yıllıkta ve GSYH'de 3 aylıkta, öbür düğümlerde
        # profil düz ya da tepe başka günde. Kapı bu yüzden iki hizada da sorulur.
        sab = _degisim("sabah")
        og = pd.DatetimeIndex(g).intersection(sab.index)
        r["kapi_sabah_hizasi"] = {c: oo.kapi_ozeti(oo.olay_kapisi(sab[c], og, guclu=True, k_tohum=120 + i))
                                  for i, c in enumerate(("n2y", "n5y"))}
        out["tr_gsyh"] = r
    except bulut.VeriYok as h:
        out["tr_gsyh"] = kurulmadi(f"TÜİK GSYH yayım günleri elde yok ({h})")
    return out


# ═══════════════════════════════════════════════════════════════ giriş
def olc() -> dict:
    return oo.yuvarla({
        "p3a": p3a(),
        "arac_taylor": arac_taylor(),
        "p3b": p3b(),
        "p3c": p3c(),
        "p3d": p3d(),
        "sekil_03": sekil_03(),
        "sekil_04": sekil_04(),
    }, 4)


if __name__ == "__main__":
    import json
    import time
    t0 = time.time()
    d = olc()
    print(json.dumps(d, ensure_ascii=False)[:4000])
    print(f"süre {time.time() - t0:.1f} sn")
