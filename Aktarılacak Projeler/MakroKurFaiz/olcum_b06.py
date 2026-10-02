#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRODAN KURA VE FAİZE — Bölüm 6 ölçüm katmanı: bütçe açığı II, EM ve para
birliği — risk primi, borç aritmetiği, mali baskınlık.

Pratikler
  p6a  Türkiye Δ(borç/GSYH) ayrışımı, yıl sonu 2007–2025 ve 2026 ilk yarı ayrı:
       kartopu (örtük faiz − nominal büyüme)·d₋₁/(1+g), faiz dışı denge (−fdd),
       kur etkisi α₋₁·ε·d₋₁/(1+g) ve ARTIK ayrı sütun. 2020Ç3 öncesinde stok iç
       borç + merkezi yönetim dış borcu × TCMB dönem sonu kuru ile kurulur;
       örtüşen dönemde (2020Ç3+) resmî stokla karşılaştırılır.
  p6b  Borcu sabit tutan faiz dışı fazla pb* = (r − g)/(1 + g)·d ızgarası, bugünkü
       nokta (örtük ve marjinal faizle), kur şoku fanı (%10/%20/%30) ve KKM
       stokunun kur duyarlılığı.
  p6c  Faiz dışı denge ↔ 5 ve 7 yıllık DİBS getirisi (çeyrek sonu): Newey–West,
       genişleyen pencerede örneklem dışı kıyas; "örneklem içi tarif".
  p6d  Çevre ülke − Almanya 10 yıllık farkları: günlük CNBC 2000–2026 ve aylık ECB
       Maastricht 1999–2026; beş olay penceresi; Eurostat borç ve açık paneli.
  arac_borc  Araç 2'nin açılış girdileri (risk primi katsayısına varsayılan yok).
  sekil_09 Δd ayrışımı · sekil_10 pb* ızgarası ve kur fanı · sekil_11 çevre farkları.

ÖLÇÜM TUZAKLARI (bu modül yazılırken ölçüldü)
1. 2020Ç3 ÖNCESİ STOK İKİ AYRI TABANIN TOPLAMIDIR. İç borç İHRAÇ tabanlıdır
   (yurt içinde ihraç edilen her DİBS, sahibi kim olursa olsun); merkezi
   yönetim dış borcu YERLEŞİKLİK tabanlıdır (alacaklısı yurt dışında olan her
   yükümlülük). Toplandığında yurt dışının elindeki TL DİBS İKİ KEZ sayılır,
   yurt içinin elindeki eurobond HİÇ sayılmaz. Örtüşen 24 çeyrekte türetilmiş
   stok resmî stokun %10–23 ALTINDA kalıyor (yurt içi eurobond > yurt dışı
   DİBS); 2020 öncesinde yurt dışı DİBS payı çok daha yüksekti ve sapmanın
   İŞARETİ bile bilinmiyor. Türetilmiş serinin düzeyi kıyaslanmaz; yıllık
   değişimde sapmanın değişimi artığa düşer ve örtüşen yıllarda ölçülür.
2. Aynı sebeple türetilmiş serinin döviz payı α hem şişik (yurt dışının elindeki
   TL DİBS dövize sayılır) hem eksiktir (yurt içi eurobond yok). Resmî α da ALT
   SINIRDIR: döviz borcu yalnız dış senet ve dış krediden kuruludur, iç borçtaki
   döviz cinsi ve dövize endeksli yurt içi ihraçlar ayrıştırılamıyor.
3. KUR TERİMİ YALNIZ DOLAR KURUYLA. Borcun para birimi kırılımı arşivde yok;
   euro (ve öbür paralar) cinsi borcun EUR/USD hareketinden doğan değerleme
   artığa düşer.
4. DÖNEM SONU KURU. TCMB gösterge kuru valör tarihlidir; dönem sonu kuru,
   dönemin son iş gününde ilan edilen kurdur (= dönem sonundan sonraki ilk valör
   günü). Valörü takvimsiz bir iş günü geri almak yılbaşında 31 Aralık ilanını
   1 Ocak'a (tatil) yazar ve yıl sonu kuru bir gün kayar; dönüşüm bu yüzden
   valör serisinden yapılır. Tek tanım `ortak_olc.donem_sonu_kur`.
5. ARTIK BÜYÜK VE BİLGİ TAŞIR. Artık; Hazine nakit hesabındaki değişimi, iskontolu
   ihraçta nominal ile nakit farkını, TÜFE'ye endeksli tahvillerin anapara
   artışını (nakit faiz gideri yalnız ödemede görünür), dolar dışı değerlemeyi,
   genel bütçe ile merkezi yönetim kapsam farkını ve (2020 öncesinde) iki
   tabanın sapma değişimini taşır. Hiçbiri ayrıca ölçülmedi; kapatmak için
   düzeltme YAPILMAZ.
6. 2026 İLK YARI. Akımlar ocak–haziran toplamıdır, oran payda olarak yıllık
   (dört çeyreklik) GSYH'yi kullanır; örtük faiz yarı yıllıktır (yıllığa
   çevrilmez). Yıllık sütunlarla toplanmaz.
7. ÖRTÜK FAİZ GERİYE BAKAR. Bugünkü örtük faiz eski, ucuz borcun ortalamasıdır;
   enflasyon nominal büyümeyi şişirdiğinde r − g derin eksiye iner (2026Ç2: −17,6
   puan; pb* GSYH'nin eksi %2,6'sı). Marjinal borçlanma faizi (DİBS 2 ve 5 yıllık)
   ayrıca işaretlenir: aynı d'de pb* sıfıra yakın.
8. ÇEYREK SONU DİBS — HİZA "sabah" (`ortak_olc.DIBS_KAYMA`, k = 1). L etiketli
   DİBS değeri L'den bir önceki Türkiye iş gününün sabah sabitlemesidir (tek
   tanım ortak_olc'de; kanıtı Bölüm 3'ün tatil sınaması ve Bölüm 2'nin çapraz
   korelasyonu). Çeyrek sonu getirisi, çeyreğin SON piyasa gününün sabitlemesidir:
   o günün kendi kotasyonu, ertesi etiket. "gun_sonu" hizası (k = 2) gün sonu
   kapanışlarıyla (kur, VIX) aynı güne oturtmak içindir; çeyrek sonu DÜZEYİNDE
   çeyreğin son gününe ertesi çeyreğin ilk sabahının kotasyonunu yazardı. Burada
   kıyaslanan öbür seri bir çeyreklik akımdır (faiz dışı denge), gün içi saati
   yoktur; ölçü bir çeyreğin DÜZEYİDİR ve o çeyreğin içinde kalan son kotasyon
   alınır. k = 0 ve 2 duyarlılık satırlarıdır (p6c).
9. CNBC AVRUPA GETİRİLERİ. Hafta sonu barları kaynakta durur, ayıklanır.
   Portekiz serisi 20.09.2011–06.12.2012 arasında art arda SIFIR taşıyor (314
   iş günü) ve 31.12.2012'de %7'lik iki gün arasında tek bir sıfır var: ikisi de
   veri boşluğudur ve atılır. Sıfır olmayan DONMUŞ diziler de var: İtalya 10 yıllık
   09–23.12.2010 arasında on bir iş günü birebir 4,582 (aynı günlerde Bund 2,95 ile
   3,08 arasında oynuyor, İspanya 5,33'ten 5,56'ya çıkıyor), İtalya 2 yıllık aynı
   aralıkta, Portekiz Ağustos–Eylül 2021'de, Yunanistan 2016–2017'de beş-altı
   günlük diziler. Beş ve daha uzun birebir aynı dizinin ilk günü gerçek son
   kotasyondur ve kalır; sonrakiler taşınmış değerdir ve atılır (günlük Portekiz farkı fiilen 07.12.2012'de başlar,
   kriz zirvesi yalnız aylık seride). Sıfıra yakın bir getirinin gerçek sıfırı
   (Fransa 13.12.2019) kalır. Yunanistan
   günlük serisi 25.11.2014'te başlar; 2010–2012 zirvesi aylık ECB serisinden
   okunur. ECB değerleri aylık ORTALAMADIR, günlük zirveyi düzleştirir.
10. KKM DUYARLILIĞI BRÜTTÜR. Kur garantisi vade sonunda kur artışının mevduat
   faizini aşan kısmını öder; mevduat faizi ve vade dağılımı arşivde yok, bu
   yüzden yazılan tutar faiz mahsubundan önceki üst sınırdır. Garantinin bütçe
   ile TCMB arasında nasıl paylaşıldığı sütun açıklamasında yazmıyor: tutar
   "kimin maliyeti" diye değil "kurun ne kadarına bağlı stok" diye okunur.
"""
from __future__ import annotations

import math
import warnings

import numpy as np
import pandas as pd

import bulut
import ortak_olc as oo

warnings.filterwarnings("ignore", category=FutureWarning)
try:
    warnings.filterwarnings("ignore", category=pd.errors.Pandas4Warning)  # type: ignore[attr-defined]
except AttributeError:
    pass

# ───────────────────────────────────────────────────────── sabitler (adlı)
AYRISIM_ILK_YIL, AYRISIM_SON_YIL = 2007, 2025
RESMI_ILK_YIL = 2021                 # 2020 sonu resmî stok var; 2021'den itibaren iki uç da resmî
ILK_YARI = ("2025-12-31", "2026-06-30")
RG_IZGARA = np.arange(-20, 11, 1)    # r − g, puan (istenen −10…+10; bugünkü nokta için −20'ye uzatıldı)
RG_ISTENEN = (-10, 10)
D_IZGARA = np.arange(20, 61, 5)      # borç/GSYH, %
KUR_SOKLARI = (10, 20, 30)           # USD/TRY artışı, %
YONETILEN_CEYREK = oo.YON_CEYREK      # tek tanım ortak_olc.YONETILEN
DIBS_HIZA = "sabah"                  # çeyrek sonu düzeyi: çeyreğin son piyasa gününün sabitlemesi (tuzak 8)
DIBS_DUGUM_6C = ("n5y", "n7y")
SIFIR_DIZISI_ASGARI = 5              # art arda bu kadar ve fazla sıfır = veri boşluğu
DONMUS_DIZI_ASGARI = 5               # art arda bu kadar ve fazla birebir aynı değer = taşınmış kotasyon

CEVRE = ["it", "es", "pt", "gr", "fr"]
ECB_CEVRE = ["IT", "ES", "PT", "GR", "IE", "FR"]
EUROSTAT_CEVRE = ["IT", "ES", "PT", "EL", "IE", "FR", "DE"]

# Olay pencereleri: "baslangic" olay öncesi kapanış (işlem günü değilse önceki son
# işlem günü), "bitis" pencere sonu (işlem günü değilse sonraki ilk işlem günü).
OLAYLAR_AVRUPA = [
    {"kimlik": "yunanistan_2010_2012", "ulke": "GR", "kaynak": "ecb_aylik", "ilk_ay": "2010-01", "son_ay": "2012-12",
     "ad": "Yunanistan 2010–2012", "not": "Günlük Yunan serisi 2014'te başladığı için zirve aylık ECB ortalamasından."},
    {"kimlik": "italya_2011", "ulke": "IT", "kaynak": "cnbc_gunluk", "baslangic": "2011-06-30", "bitis": "2011-11-30",
     "ad": "İtalya 2011 (Temmuz–Kasım)"},
    {"kimlik": "ispanya_2012", "ulke": "ES", "kaynak": "cnbc_gunluk", "baslangic": "2011-12-30", "bitis": "2012-12-28",
     "ad": "İspanya 2012 (yıl içi zirve)"},
    {"kimlik": "italya_2018_mayis", "ulke": "IT", "kaynak": "cnbc_gunluk", "baslangic": "2018-05-14",
     "bitis": "2018-05-29", "ad": "İtalya Mayıs 2018 (hükümet kuruluşu)"},
    {"kimlik": "italya_2018_butce", "ulke": "IT", "kaynak": "cnbc_gunluk", "baslangic": "2018-09-27",
     "bitis": "2018-10-31", "ad": "İtalya Eylül–Ekim 2018 bütçesi",
     "not": "Açık hedefi 27.09 akşamı açıklandı; pencere 27.09 kapanışından başlar."},
]


# ───────────────────────────────────────────────────────── küçük yardımcılar
_iso, _f, kurulmadi = oo._iso, oo._f, oo.kurulmadi


_bas_gun, _son_gun = oo.bas_gun, oo.son_gun          # tek tanımlar ortak_olc'de


donem_sonu_kur = oo.donem_sonu_kur      # tek tanım ortak_olc'de (tuzak 4)


# ═══════════════════════════════════════════════════════════════ çerçeve
def ceyrek_cercevesi() -> pd.DataFrame:
    c = oo.oku("butce_ceyreklik")
    df = pd.DataFrame(index=c.index)
    df["Y"] = c["gsyh_yil_trl"]
    df["kur"] = donem_sonu_kur(c.index).values
    df["dis_tur"] = c["db_my_mlrusd"] * df["kur"] / 1000          # milyar USD × TL/USD → trilyon TL
    df["D_tur"] = c["ic_borc_ceyrek_trl"] + df["dis_tur"]
    df["D_res"] = c["stok_trl"]
    df["doviz_res"] = c["doviz_borc_ceyrek_trl"]
    df["d_tur"] = df["D_tur"] / df["Y"] * 100
    df["d_res"] = c["stok_gsyh"]
    df["alfa_tur"] = df["dis_tur"] / df["D_tur"]
    df["alfa_res"] = df["doviz_res"] / df["D_res"]
    df["fdd_gsyh"] = c["fdd_gsyh"]
    df["faiz_gsyh"] = c["faiz_gsyh"]
    return df


def _terimler(D0, D1, Y0, Y1, I, PB, alfa0, k0, k1) -> dict:
    """Δd = (i − g)/(1+g)·d₀ − pb + α₀·ε·d₀/(1+g) + artık (hepsi GSYH puanı)."""
    d0, d1 = D0 / Y0 * 100, D1 / Y1 * 100
    g = Y1 / Y0 - 1
    i = I / D0
    eps = k1 / k0 - 1
    kartopu = (i - g) / (1 + g) * d0
    fdd = -PB / Y1 * 100
    kur = alfa0 * eps * d0 / (1 + g)
    dd = d1 - d0
    return {"d_onceki": d0, "d": d1, "delta_d_puan": dd, "kartopu_puan": kartopu, "fdd_terimi_puan": fdd,
            "kur_terimi_puan": kur, "artik_puan": dd - kartopu - fdd - kur,
            "ortuk_faiz_yuzde": i * 100, "nominal_buyume_yuzde": g * 100,
            "r_eksi_g_puan": (i - g) * 100, "alfa_onceki_yuzde": alfa0 * 100,
            "kur_degisimi_yuzde": eps * 100, "fdd_gsyh": PB / Y1 * 100}


def _yillik_ayrisim(df: pd.DataFrame, yil: int, seri: str) -> dict | None:
    t0, t1 = pd.Timestamp(f"{yil - 1}-12-31"), pd.Timestamp(f"{yil}-12-31")
    if t0 not in df.index or t1 not in df.index:
        return None
    a, b = df.loc[t0], df.loc[t1]
    D, alfa = ("D_res", "alfa_res") if seri == "resmi" else ("D_tur", "alfa_tur")
    if not all(np.isfinite([a[D], b[D], a["Y"], b["Y"], b["faiz_gsyh"], b["fdd_gsyh"], a[alfa]])):
        return None
    I = b["faiz_gsyh"] * b["Y"] / 100
    PB = b["fdd_gsyh"] * b["Y"] / 100
    r = _terimler(a[D], b[D], a["Y"], b["Y"], I, PB, a[alfa], a["kur"], b["kur"])
    return {"yil": str(yil), "seri": seri, **r}


def _ilk_yari(df: pd.DataFrame) -> dict:
    t0, t1 = pd.Timestamp(ILK_YARI[0]), pd.Timestamp(ILK_YARI[1])
    a, b = df.loc[t0], df.loc[t1]
    m = oo.oku("butce_aylik").loc[f"{t0.year + 1}-01":f"{t1.year}-{t1.month:02d}"]
    I = m["faiz_gideri"].sum() / 1e9
    PB = (m["my_gelir"] - m["faiz_disi_gider"]).sum() / 1e9
    r = _terimler(a["D_res"], b["D_res"], a["Y"], b["Y"], I, PB, a["alfa_res"], a["kur"], b["kur"])
    return {"donem": f"{t1.year}-ilk-yari", "seri": "resmi", "ilk": _iso(t0), "son": _iso(t1), "n_ay": int(len(m)), **r,
            "not": "Akımlar ocak–haziran toplamı; payda dört çeyreklik GSYH; örtük faiz yarı yıllık (yıllığa "
                   "çevrilmedi); yıllık sütunlarla toplanmaz."}


def _kur_gunu_duyarliligi(tarihler: pd.DatetimeIndex) -> dict:
    """Dönem sonu kuru seçiminin etkisi: son iş günü ilanı (bu modül) ile dönem
    içindeki son valör günü (bir iş günü önceki ilan)."""
    v = oo.oku("usdtry_tcmb_gunluk")["usdtry_tcmb_valor"].dropna()
    a = donem_sonu_kur(tarihler)
    b = pd.Series([float(v.loc[:t].iloc[-1]) for t in tarihler], index=tarihler)
    f = (a / b - 1) * 100
    return {"n": int(len(f)), "ort_mutlak_fark_yuzde": _f(f.abs().mean()), "azami_mutlak_fark_yuzde": _f(f.abs().max()),
            "azami_gun": _iso(f.abs().idxmax()),
            "not": "Dönem içindeki son valör günü bir iş günü önceki ilandır; fark dış borç bacağına aynı oranda yansır."}


def _resmi_ozdeslik() -> dict:
    """Resmî stokun bacakları: döviz borcu = dış senet + dış kredi ve stok = iç borç +
    dış senet + dış kredi her çeyrekte sınanır. Kaynak tanımı döviz borcunu 'döviz
    cinsi ve dövize endeksli borç' diye yazıyor; özdeşlik tutuyorsa yurt içi döviz
    cinsi ihraçlar içinde yoktur ve döviz payı alt sınırdır (tuzak 2)."""
    c = oo.oku("butce_ceyreklik").dropna(subset=["stok_trl"])
    dk = c["dis_senet_ceyrek_trl"] + c["dis_kredi_ceyrek_trl"]
    f1 = (c["doviz_borc_ceyrek_trl"] - dk).abs()
    f2 = (c["stok_trl"] - c["ic_borc_ceyrek_trl"] - dk).abs()
    return {"n": int(len(c)), "ilk": str(pd.Period(c.index.min(), "Q")), "son": str(pd.Period(c.index.max(), "Q")),
            "doviz_eslik_birebir": int((f1 < 1e-5).sum()), "doviz_azami_fark_trl": _f(f1.max()),
            "stok_eslik_birebir": int((f2 < 1e-5).sum()), "stok_azami_fark_trl": _f(f2.max()),
            "yontem": "Resmî döviz borcunun dış borçlanma senetleri ile dış kredilerin toplamına ve resmî stokun iç borç "
                      "artı bu ikisine eşit olup olmadığı her çeyrekte sınandı."}


def _karsilastirma(df: pd.DataFrame) -> dict:
    x = df.dropna(subset=["D_res", "D_tur"])
    fark = x["D_tur"] - x["D_res"]
    fark_d = x["d_tur"] - x["d_res"]
    yil = x[x.index.month == 12]
    return {
        "n": int(len(x)), "ilk": _iso(x.index.min()), "son": _iso(x.index.max()),
        "yontem": "Örtüşen çeyreklerde iç borç artı merkezi yönetim dış borcunun (TCMB dönem sonu kuruyla) "
                  "resmî borç stokundan farkı trilyon TL, yüzde ve GSYH puanı olarak alındı.",
        "fark_trl_ort": _f(fark.mean()), "fark_yuzde_ort": _f((fark / x["D_res"]).mean() * 100),
        "fark_yuzde_asgari": _f((fark / x["D_res"]).min() * 100), "fark_yuzde_azami": _f((fark / x["D_res"]).max() * 100),
        "fark_d_puan_ort": _f(fark_d.mean()), "fark_d_puan_asgari": _f(fark_d.min()),
        "fark_d_puan_azami": _f(fark_d.max()),
        "dis_bacak_turetilmis_eksi_resmi_doviz_trl_son": _f(x["dis_tur"].iloc[-1] - x["doviz_res"].iloc[-1]),
        "kur_gunu_duyarliligi": _kur_gunu_duyarliligi(x.index),
        "yil_sonu_fark_d_degisimi_puan": {str(t.year): _f(v) for t, v in fark_d.loc[yil.index].diff().dropna().items()},
        "ceyrekler": [{"ceyrek": str(pd.Period(t, "Q")), "turetilmis_trl": _f(r["D_tur"]), "resmi_trl": _f(r["D_res"]),
                       "turetilmis_d": _f(r["d_tur"]), "resmi_d": _f(r["d_res"]),
                       "turetilmis_alfa_yuzde": _f(r["alfa_tur"] * 100), "resmi_alfa_yuzde": _f(r["alfa_res"] * 100)}
                      for t, r in x.iterrows()],
        "sebep": "Dış borç bacağı yerleşiklik tabanlı: yurt dışının elindeki TL DİBS iki kez sayılır, yurt içinin "
                 "elindeki eurobond hiç sayılmaz; resmî stok ise iki bacağı da ihraç yerine göre sayar.",
        "resmi_ozdeslik": _resmi_ozdeslik(),
    }


def p6a() -> dict:
    df = ceyrek_cercevesi()
    ana, tur, res = [], [], []
    for y in range(AYRISIM_ILK_YIL, AYRISIM_SON_YIL + 1):
        rt = _yillik_ayrisim(df, y, "turetilmis")
        rr = _yillik_ayrisim(df, y, "resmi")
        if rt:
            tur.append(rt)
        if rr:
            res.append(rr)
        sec = rr if (y >= RESMI_ILK_YIL and rr) else rt
        if sec:
            ana.append(sec)
    iy = _ilk_yari(df)
    t20 = pd.Timestamp(f"{RESMI_ILK_YIL - 1}-12-31")
    kol = ["delta_d_puan", "kartopu_puan", "fdd_terimi_puan", "kur_terimi_puan", "artik_puan"]
    toplam = {k: _f(sum(r[k] for r in ana)) for k in kol}
    alt = {}
    for ad, a, b in (("2007-2012", 2007, 2012), ("2013-2017", 2013, 2017), ("2018-2020", 2018, 2020),
                     ("2021-2023", 2021, 2023), ("2024-2025", 2024, 2025)):
        z = [r for r in ana if a <= int(r["yil"]) <= b]
        alt[ad] = {"n": len(z), **{k: _f(sum(r[k] for r in z)) for k in kol}}
    ortak = [(t, r) for t in tur for r in res if t["yil"] == r["yil"]]
    artik_fark = {t["yil"]: _f(t["artik_puan"] - r["artik_puan"]) for t, r in ortak}
    kur_fark = {t["yil"]: _f(t["kur_terimi_puan"] - r["kur_terimi_puan"]) for t, r in ortak}
    return {
        "n": int(len(ana)), "ilk": ana[0]["yil"], "son": ana[-1]["yil"],
        "yontem": "Merkezi yönetim borç stokunun GSYH'ye oranının yıllık değişimi; örtük faiz ile nominal büyüme farkının "
                  "önceki yıl oranına etkisi (kartopu), faiz dışı dengenin eksisi, döviz cinsi payın dolar kurundaki "
                  "değişimle çarpımı (kur) ve bunların açıklamadığı artık olarak ayrıştırıldı; 2020'ye kadar stok iç "
                  "borç ile dış borcun TCMB dönem sonu kuruyla toplanmasından, 2021'den itibaren resmî stoktan gelir.",
        "kaynak": ["butce_ceyreklik", "butce_aylik (2026 ilk yarı akımları)", "usdtry_tcmb_gunluk (dönüşüm kuru)"],
        "formul": "Δd = (i − g)/(1+g)·d₋₁ − fdd + α₋₁·ε·d₋₁/(1+g) + artık; i = 12 aylık faiz gideri / önceki yıl sonu stok",
        "tablo": ana,
        "ilk_yari_2026": iy,
        "seri_gecisi": {"yil": str(RESMI_ILK_YIL - 1),
                        "turetilmis_d": _f(df.loc[t20, "d_tur"]), "resmi_d": _f(df.loc[t20, "d_res"]),
                        "fark_puan": _f(df.loc[t20, "d_res"] - df.loc[t20, "d_tur"]),
                        "not": f"{RESMI_ILK_YIL} satırı resmî {RESMI_ILK_YIL - 1} sonundan başlar; aradaki düzey farkı "
                               "hiçbir yılın Δd'sine girmez."},
        "toplam_2007_2025": toplam,
        "alt_donem_toplami": alt,
        "turetilmis_tum_yillar": tur,
        "resmi_yillar": res,
        "turetilmis_eksi_resmi_artik_puan": artik_fark,
        "turetilmis_eksi_resmi_kur_terimi_puan": kur_fark,
        "karsilastirma": _karsilastirma(df),
        "artik_kaynaklari": ["Hazine nakit hesabındaki değişim", "iskontolu ihraçta nominal ile nakit farkı",
                             "TÜFE'ye endeksli tahvillerin anapara artışı", "dolar dışı paraların değerlemesi",
                             "genel bütçe ile merkezi yönetim kapsam farkı",
                             "2020'ye kadar iki tabanın sapmasındaki değişim"],
    }


def sekil_09() -> dict:
    a = p6a()
    t = a["tablo"] + [a["ilk_yari_2026"]]
    df = ceyrek_cercevesi()
    y = df[df.index.month == 12]
    return {
        "n": len(t), "ilk": a["ilk"], "son": a["ilk_yari_2026"]["son"],
        "yontem": "Δ(borç/GSYH) ayrışımının yıllık sütunları (kartopu, faiz dışı denge, kur, artık) ve Δd; son çubuk "
                  "2026 ilk yarısıdır ve yıllık değildir.",
        "kaynak": a["kaynak"],
        "donem": [r.get("yil") or r.get("donem") for r in t],
        "seri": [r["seri"] for r in t],
        "delta_d_puan": [r["delta_d_puan"] for r in t],
        "kartopu_puan": [r["kartopu_puan"] for r in t],
        "fdd_terimi_puan": [r["fdd_terimi_puan"] for r in t],
        "kur_terimi_puan": [r["kur_terimi_puan"] for r in t],
        "artik_puan": [r["artik_puan"] for r in t],
        "duzey": {"yil": [str(i.year) for i in y.index],
                  "turetilmis_d": [_f(v) for v in y["d_tur"]], "resmi_d": [_f(v) for v in y["d_res"]]},
    }


# ═══════════════════════════════════════════════════════════════ p6b
def _dibs_kayma() -> int:
    """DİBS etiket kayması (iş günü): hiza "sabah", tek tanım `ortak_olc.DIBS_KAYMA` (tuzak 8)."""
    return oo.dibs_kayma(DIBS_HIZA)


def _dibs_ceyrek_sonu(dugumler=DIBS_DUGUM_6C, kayma: int | None = None) -> pd.DataFrame:
    """Çeyreğin son piyasa günündeki DİBS getirisi (`ortak_olc.dibs`, hiza "sabah");
    `kayma` yalnız duyarlılık satırları için hizayı geçersiz kılar (tuzak 8)."""
    d = oo.dibs(DIBS_HIZA, dugumler, kayma=kayma).dropna()
    q = d.groupby(pd.PeriodIndex(d.index, freq="Q")).last()
    gun = d.index.to_series().groupby(pd.PeriodIndex(d.index, freq="Q")).last()
    q["piyasa_gunu"] = gun
    return q


def _bugun(df: pd.DataFrame) -> dict:
    t1 = df.dropna(subset=["D_res"]).index.max()
    t0 = t1 - pd.offsets.QuarterEnd(4)
    a, b = df.loc[t0], df.loc[t1]
    I = b["faiz_gsyh"] * b["Y"] / 100
    i = I / a["D_res"]
    g = b["Y"] / a["Y"] - 1
    d = b["d_res"]
    eps = b["kur"] / a["kur"] - 1
    return {"ceyrek": str(pd.Period(t1, "Q")), "d_yuzde": d, "alfa_yuzde": b["alfa_res"] * 100,
            "ortuk_faiz_yuzde": i * 100, "nominal_buyume_yuzde": g * 100, "r_eksi_g_puan": (i - g) * 100,
            "fdd_gsyh": b["fdd_gsyh"], "pb_yildiz_gsyh": (i - g) / (1 + g) * d,
            "kur_12a_degisim_yuzde": eps * 100,
            "pb_yildiz_kur_ile_gsyh": (i - g + b["alfa_res"] * eps) / (1 + g) * d,
            "_g": g, "_t1": t1}


def _kkm_duyarlilik() -> dict:
    k = oo.oku("kkm_aylik")
    ay_sonu = k.index + pd.offsets.MonthEnd(0)
    kur = donem_sonu_kur(ay_sonu)
    c = oo.oku("butce_ceyreklik")["gsyh_yil_trl"].dropna()

    def y_icin(t):
        q = t + pd.offsets.QuarterEnd(0)
        return (float(c.loc[q]), str(pd.Period(q, "Q"))) if q in c.index else (float(c.iloc[-1]), str(pd.Period(c.index[-1], "Q")))

    def satir(i: int) -> dict:
        t = ay_sonu[i]
        usd, tl = float(k["kkm_usd_mia"].iloc[i]), float(k["kkm_tl_mlr"].iloc[i])
        kr = float(kur.iloc[i])
        Y, yq = y_icin(t)
        dd = usd * kr                                  # milyar TL
        out = {"ay": str(t.to_period("M")), "kur": kr, "doviz_donusumlu_mlr_usd": usd,
               "doviz_donusumlu_mlr_tl": dd, "tl_kkm_mlr_tl": tl, "toplam_mlr_tl": dd + tl,
               "gsyh_ceyrek": yq, "gsyh_yil_trl": Y, "soklar": []}
        for e in KUR_SOKLARI:
            a_ = dd * e / 100
            b_ = tl * e / 100
            out["soklar"].append({"kur_artisi_yuzde": e,
                                  "doviz_donusumlu_mlr_tl": a_, "doviz_donusumlu_gsyh_yuzde": a_ / (Y * 1000) * 100,
                                  "tl_kkm_mlr_tl": b_, "tl_kkm_gsyh_yuzde": b_ / (Y * 1000) * 100})
        return out

    toplam_tl = k["kkm_usd_mia"].values * kur.values + k["kkm_tl_mlr"].values
    return {
        "n": int(len(k)), "ilk": _iso(k.index.min())[:7], "son": _iso(k.index.max())[:7],
        "yontem": "Kur korumalı mevduatın döviz dönüşümlü kısmı (milyar dolar) TCMB ay sonu kuruyla TL'ye çevrildi; "
                  "TL'den dönüşen kısım ayrıca yazıldı; her şokta duyarlılık stok çarpı kur artışıdır (faiz mahsubundan "
                  "önce, brüt).",
        "kaynak": ["kkm_aylik", "usdtry_tcmb_gunluk (dönüşüm kuru)", "butce_ceyreklik (GSYH)"],
        "kapsam_notu": "Kaynak KKM'yi 'döviz dönüşümlü' (milyar dolar) ve 'TL' (milyar TL) diye ikiye ayırıyor; "
                       "ikisi de kur korumalıdır. Garantinin bütçe ile TCMB arasındaki paylaşımı arşivde yazmıyor.",
        "sutun_saglamasi": {
            "iki_kisim_toplam_zirve_mlr_tl": _f(np.max(toplam_tl)),
            "iki_kisim_toplam_zirve_ay": str(ay_sonu[int(np.argmax(toplam_tl))].to_period("M")),
            "doviz_kismi_toplam_olsaydi_zirve_mlr_tl": _f(np.max(k["kkm_usd_mia"].values * kur.values)),
            "not": "Döviz dönüşümlü sütun bütün KKM'yi taşısaydı stok ikinci satırdaki kadar kalırdı; iki kısmın "
                   "toplamı birinci satırdır. Karar, dış kaynakla kıyaslanacak sağlamadır, burada ölçülmez."},
        "son_ay": satir(len(k) - 1),
        "doviz_donusumlu_zirve": satir(int(np.argmax(k["kkm_usd_mia"].values))),
        "tl_kkm_zirve": satir(int(np.argmax(k["kkm_tl_mlr"].values))),
        "toplam_zirve": satir(int(np.argmax(toplam_tl))),
    }


def p6b() -> dict:
    df = ceyrek_cercevesi()
    b = _bugun(df)
    g = b["_g"]
    izgara = [[_f(rg / 100 / (1 + g) * d) for d in D_IZGARA] for rg in RG_IZGARA]
    dq = _dibs_ceyrek_sonu(("n2y", "n5y"))
    q1 = pd.Period(b["_t1"], "Q")
    marj = {}
    if q1 in dq.index:
        for c in ("n2y", "n5y"):
            r = dq.loc[q1, c] / 100
            marj[c] = {"faiz_yuzde": _f(r * 100), "r_eksi_g_puan": _f((r - g) * 100),
                       "pb_yildiz_gsyh": _f((r - g) / (1 + g) * b["d_yuzde"]),
                       "piyasa_gunu": _iso(dq.loc[q1, "piyasa_gunu"])}
    if not marj:
        marj = kurulmadi(f"{q1} çeyrek sonu için DİBS 2 ve 5 yıllık getirisi elde yok")
    ozd = _resmi_ozdeslik()
    fan = []
    for e in KUR_SOKLARI:
        dyeni = b["d_yuzde"] * (1 + b["alfa_yuzde"] / 100 * e / 100)
        fan.append({"kur_artisi_yuzde": e, "d_yeni": _f(dyeni), "delta_d_puan": _f(dyeni - b["d_yuzde"]),
                    "pb_yildiz_yeni_gsyh": _f((b["ortuk_faiz_yuzde"] - b["nominal_buyume_yuzde"]) / 100 / (1 + g) * dyeni)})
    bugun = {k: (_f(v) if not isinstance(v, str) else v) for k, v in b.items() if not k.startswith("_")}
    bugun["izgara_icinde"] = bool(RG_ISTENEN[0] <= b["r_eksi_g_puan"] <= RG_ISTENEN[1])
    bugun["blanchard_kosulu_r_kucuk_g"] = bool(b["r_eksi_g_puan"] < 0)
    bugun["pb_yildiz_kur_ile_notu"] = ("Kur terimi dahil pb* = (r − g + α·ε)/(1 + g)·d; ε son dört çeyreğin TCMB dönem "
                                       "sonu kuru değişimidir (Araç 2'nin formülü).")
    return {
        "n": int(len(RG_IZGARA) * len(D_IZGARA)), "ilk": bugun["ceyrek"], "son": bugun["ceyrek"],
        "yontem": "Borç oranını sabit tutan faiz dışı fazla pb* = (r − g)/(1 + g)·d bir r − g ve borç oranı ızgarasında "
                  "bugünkü nominal büyümeyle hesaplandı; bugünkü nokta son dört çeyreğin faiz giderinin bir yıl önceki "
                  "stoka oranı (örtük faiz) ve dört çeyreklik GSYH'nin yıllık artışıyla, ayrıca DİBS 2 ve 5 yıllık "
                  "getirisiyle (marjinal faiz vekili) işaretlendi; kur fanı döviz payı çarpı kur artışı kadar anlık "
                  "sıçramadır.",
        "kaynak": ["butce_ceyreklik", "usdtry_tcmb_gunluk", "dibs_egri_gunluk", "kkm_aylik"],
        "izgara": {"r_eksi_g_puan": [int(v) for v in RG_IZGARA], "d_yuzde": [int(v) for v in D_IZGARA],
                   "pb_yildiz_gsyh": izgara, "nominal_buyume_yuzde": _f(g * 100),
                   "istenen_aralik_puan": list(RG_ISTENEN),
                   "genisletme_sebebi": "Bugünkü r − g istenen aralığın dışında; ızgara noktayı içine alacak kadar "
                                        "uzatıldı."},
        "bugun": bugun,
        "marjinal_faizle": marj,
        "kur_fani": {"alfa_yuzde": _f(b["alfa_yuzde"]), "soklar": fan,
                     "not": ("Döviz payı alt sınırdır: resmî döviz borcu dış senet artı dış krediye eşit (özdeşlik "
                             "satırı), yurt içinde ihraç edilen döviz cinsi ve dövize endeksli kâğıtlar içinde yok; "
                             if ozd["doviz_eslik_birebir"] == ozd["n"] else
                             "Resmî döviz borcu dış senet artı dış krediden ayrışıyor (özdeşlik satırı); döviz payının "
                             "kapsamı yeniden sınanmalı; ") +
                            "sıçrama anlıktır, kurun enflasyona geçişiyle nominal GSYH'nin sonradan büyümesi ölçülmedi.",
                     "ozdeslik": ozd},
        "kkm": _kkm_duyarlilik(),
    }


def arac_borc() -> dict:
    df = ceyrek_cercevesi()
    b = _bugun(df)
    y25 = _yillik_ayrisim(df, AYRISIM_SON_YIL, "resmi")
    t25 = pd.Timestamp(f"{AYRISIM_SON_YIL}-12-31")
    return {
        "ceyrek": b["ceyrek"],
        "d_yuzde": _f(b["d_yuzde"]), "alfa_yuzde": _f(b["alfa_yuzde"]),
        "ortuk_faiz_yuzde": _f(b["ortuk_faiz_yuzde"]), "nominal_buyume_yuzde": _f(b["nominal_buyume_yuzde"]),
        "fdd_gsyh": _f(b["fdd_gsyh"]),
        "yil_sonu": {"yil": str(AYRISIM_SON_YIL), "d_yuzde": _f(df.loc[t25, "d_res"]),
                     "alfa_yuzde": _f(df.loc[t25, "alfa_res"] * 100),
                     "ortuk_faiz_yuzde": _f(y25["ortuk_faiz_yuzde"]),
                     "nominal_buyume_yuzde": _f(y25["nominal_buyume_yuzde"]), "fdd_gsyh": _f(y25["fdd_gsyh"])},
        "risk_primi_katsayisi": None,
        "risk_primi_notu": "EM risk primi katsayısına varsayılan konmaz; okur kendi değerini girer.",
        "yontem": "Araç 2'nin açılış değerleri son çeyreğin ölçümleridir: resmî borç oranı, döviz payı (alt sınır), son "
                  "dört çeyreğin örtük faizi, dört çeyreklik nominal GSYH artışı ve 12 aylık faiz dışı denge.",
        "kaynak": ["butce_ceyreklik", "usdtry_tcmb_gunluk"],
    }


def sekil_10() -> dict:
    p = p6b()
    return {"n": p["n"], "ilk": p["ilk"], "son": p["son"],
            "yontem": "pb* ızgarası (r − g × borç oranı), bugünkü nokta (örtük ve marjinal faizle) ve kur şoku fanı.",
            "kaynak": p["kaynak"], "izgara": p["izgara"],
            "bugun": {k: p["bugun"][k] for k in ("ceyrek", "d_yuzde", "r_eksi_g_puan", "pb_yildiz_gsyh", "fdd_gsyh")},
            "marjinal_faizle": p["marjinal_faizle"], "kur_fani": p["kur_fani"]}


# ═══════════════════════════════════════════════════════════════ p6c
def p6c() -> dict:
    c = oo.oku("butce_ceyreklik")["fdd_gsyh"].dropna()
    c.index = pd.PeriodIndex(c.index, freq="Q")
    dq = _dibs_ceyrek_sonu()
    dq_alt = {k: _dibs_ceyrek_sonu(kayma=k) for k in (0, 2)}
    out = {
        "etiket": "örneklem içi tarif",
        "yontem": "Çeyrek sonu 5 ve 7 yıllık DİBS getirisi (piyasa günü) ile 12 aylık faiz dışı denge/GSYH arasındaki "
                  "ilişki düzeyde ve çeyreklik değişimde Newey–West ile, değişimde ayrıca genişleyen pencerede "
                  "rastgele yürüyüş ve koşulsuz ortalama kıyasıyla örneklem dışı sınandı.",
        "kaynak": ["dibs_egri_gunluk", "butce_ceyreklik"],
        "yayim_notu": "Çeyreğin faiz dışı dengesi çeyrek kapandıktan sonra yayımlanır (son ayın bütçesi ertesi ayın "
                      "ortasında); eşzamanlı değişim regresyonu ve onun örneklem dışı sınaması o çeyreğin dengesini "
                      "bilinen sayar, yani bir tahmin değil bir uyum sınamasıdır. Bir çeyrek önceki dengeyle kurulan "
                      "satır, getirinin yayımlanmış dengeye tepkisini sorar.",
        "dibs_etiket_kaymasi_is_gunu": _dibs_kayma(),
        "dibs_hiza": DIBS_HIZA,
    }
    for dug in DIBS_DUGUM_6C:
        y = dq[dug]
        d = pd.concat([y.rename("y"), c.rename("x")], axis=1, sort=True).dropna()
        r_duz = oo.hac(d["y"].values, d["x"].values)
        dy = (d["y"].diff() * 100).dropna()           # bp
        dx = d["x"].diff().dropna()                   # puan
        deg = oo.regresyon(dy, dx)
        dy4 = (d["y"].diff(4) * 100).dropna()
        dx4 = d["x"].diff(4).dropna()
        r4 = oo.hac(dy4.values, dx4.reindex(dy4.index).values, gecikme=4)
        haric = [p for p in dy.index if not (YONETILEN_CEYREK[0] <= p <= YONETILEN_CEYREK[1])]
        deg_h = oo.regresyon(dy.loc[haric], dx.loc[haric])
        deg_g = oo.regresyon(dy, dx.shift(1).dropna())
        duyar = {}
        for k, q in dq_alt.items():
            dk = pd.concat([q[dug].rename("y"), c.rename("x")], axis=1, sort=True).dropna()
            rk = oo.regresyon((dk["y"].diff() * 100).dropna(), dk["x"].diff().dropna())
            duyar[f"kayma_{k}"] = {"n": rk["n"], "egim": rk.get("egim"), "t": rk.get("t"), "hukum": rk.get("hukum")}
        fk = (dq[dug] - dq_alt[2][dug]).dropna() * 100
        duyar["bir_gun_fark_ort_mutlak_bp"] = _f(fk.abs().mean())
        duyar["bir_gun_fark_azami_bp"] = _f(fk.abs().max())
        duyar["bir_gun_fark_azami_ceyrek"] = str(fk.abs().idxmax())
        duyar["not"] = ("Çeyrek sonu düzeyi tek günün kotasyonudur: etiket bir iş günü kaydırılınca getiri bu kadar "
                        "oynar ve değişim eğimi onunla birlikte kayar; eğimin büyüklüğü bu gürültüyle birlikte okunur.")
        out[dug] = {
            "n": int(len(d)), "ilk": str(d.index.min()), "son": str(d.index.max()),
            "isaret_notu": ("Değişim eğimi artı: faiz dışı denge iyileşirken getiri yükseliyor — 'açık büyür, faiz "
                            "artar' beklentisinin tersi; yüksek enflasyon ve sıkılaştırma çeyreklerinde nominal gelirin "
                            "şişmesiyle tutarlı (beklenen yanlılık tablosu metindedir)." if deg.get("egim", 0) > 0 else
                            "Değişim eğimi eksi ya da sıfır."),
            "duzey": {"n": r_duz["n"], "sabit": r_duz["b"][0], "egim_yuzde_per_puan": r_duz["b"][1],
                      "se": r_duz["se"][1], "t": r_duz["t"][1], "r2": r_duz["r2"], "gecikme": r_duz["gecikme"],
                      "hukum": "tarif edici",
                      "not": "Düzeyler birim köke yakın: yalnız tarif, örneklem dışı sınama kurulmaz; t bu yüzden "
                             "hüküm vermez."},
            "degisim": {**deg, "birim": "Δgetiri baz puan / Δfaiz dışı denge puan"},
            "degisim_4c": {"n": r4["n"], "egim_bp_per_puan": r4["b"][1], "se": r4["se"][1], "t": r4["t"][1],
                           "r2": r4["r2"], "gecikme": r4["gecikme"], "hukum": "tarif edici",
                           "not": "Örtüşen dört çeyreklik değişim; örneklem dışı sınama kurulmadı, yalnız tarif."},
            "etiket_kaymasi_duyarliligi": duyar,
            "degisim_bir_ceyrek_gecikmeli": {**deg_g, "birim": "Δgetiri baz puan / bir çeyrek önceki Δfaiz dışı denge puan",
                                             "not": "Açıklayıcı değişken bir çeyrek önceki dengedir: çeyrek sonunda "
                                                    "yayımlanmış olan bilgi."},
            "degisim_yonetilen_haric": {**deg_h, "haric": [str(YONETILEN_CEYREK[0]), str(YONETILEN_CEYREK[1])],
                                        "not": "Kur korumalı ve zorunlu tahvil talebi dönemi dışarıda; dizi bitişik "
                                               "değil, örneklem dışı sınama boşluğun üstünden yürür."},
        }
    return out


# ═══════════════════════════════════════════════════════════════ p6d
def _sifir_dizisi_temizle(s: pd.Series) -> tuple[pd.Series, int]:
    """Veri boşluğu olan sıfırlar: art arda SIFIR_DIZISI_ASGARI ve fazlası, ya da
    iki yanındaki sıfır dışı değerin ikisi de 1 puandan büyük olduğu tek sıfır
    (getiri %7'den sıfıra inip ertesi gün geri dönmez). Sıfıra yakın bir getirinin
    gerçek sıfırı (Fransa 13.12.2019) korunur."""
    z = (s == 0)
    grup = (z != z.shift()).cumsum()
    uzun = z & (z.groupby(grup).transform("sum") >= SIFIR_DIZISI_ASGARI)
    dolu = s.mask(z)
    once, sonra = dolu.ffill().shift(), dolu.bfill().shift(-1)
    tek = z & (once.abs() > 1) & (sonra.abs() > 1)
    sil = uzun | tek
    return s.mask(sil), int(sil.sum())


def _donmus_dizi_temizle(s: pd.Series) -> tuple[pd.Series, list]:
    """Sıfır olmayan, art arda DONMUS_DIZI_ASGARI ve daha fazla iş günü birebir aynı
    değer: ilk gün gerçek son kotasyondur ve kalır, sonrakiler taşınmış değerdir ve
    atılır (tuzak 9). Boş günler diziyi bölmez (tatil arası donma da yakalanır)."""
    x = s.dropna()
    x = x[x != 0]
    grup = (x != x.shift()).cumsum()
    uzun = x.groupby(grup).transform("size") >= DONMUS_DIZI_ASGARI
    ilk = x.index.to_series().groupby(grup).transform("first")
    sil = x.index[uzun & (x.index.to_series() != ilk)]
    diziler = [(str(g.index[0].date()), str(g.index[-1].date()), int(len(g)))
               for _, g in x[uzun].groupby(grup[uzun])]
    return s.mask(s.index.isin(sil)), diziler


def cevre_gunluk() -> tuple[pd.DataFrame, dict]:
    e = oo.oku("cnbc_avrupa_getiri_gunluk")
    e = e[e.index.dayofweek < 5].copy()
    atilan, donmus = {}, {}
    for c in e.columns:
        e[c], atilan[c] = _sifir_dizisi_temizle(e[c])
        e[c], donmus[c] = _donmus_dizi_temizle(e[c])
    df = pd.DataFrame(index=e.index)
    for u in CEVRE:
        df[u] = (e[f"{u}10y"] - e["de10y"]) * 100
    df["it2y"] = (e["it2y"] - e["de2y"]) * 100
    for c in ("de10y", "it10y", "es10y", "it2y", "de2y"):
        df[f"_{c}"] = e[c]
    return df, {"sifir": {k: v for k, v in atilan.items() if v},
                "donmus": {k: {"n_atilan": int(sum(n - 1 for *_, n in v)), "diziler": v}
                           for k, v in donmus.items() if v}}


def ecb_aylik() -> pd.DataFrame:
    m = oo.oku("ecb_maastricht_aylik")
    m.index = pd.PeriodIndex(m.index, freq="M")
    return pd.DataFrame({u: (m[u] - m["DE"]) * 100 for u in ECB_CEVRE}, index=m.index)


def _olay_gunluk(o: dict, df: pd.DataFrame) -> dict:
    u = o["ulke"].lower()
    s = df[u].dropna()
    b, son = _bas_gun(s.index, o["baslangic"]), _son_gun(s.index, o["bitis"])
    w = s.loc[b:son]
    j = w.idxmax()
    r = {"kimlik": o["kimlik"], "ad": o["ad"], "ulke": o["ulke"], "kaynak": "CNBC günlük (Avrupa kapanışı)",
         "ilk": _iso(b), "son": _iso(son), "n_gun": int(len(w) - 1),
         "fark_bas_bp": _f(s.loc[b]), "fark_son_bp": _f(s.loc[son]), "delta_fark_bp": _f(s.loc[son] - s.loc[b]),
         "zirve_bp": _f(w.max()), "zirve_gunu": _iso(j), "bas_zirve_bp": _f(w.max() - s.loc[b]),
         "zirve_son_bp": _f(s.loc[son] - w.max())}
    ulke10, de10 = df[f"_{u}10y"] if f"_{u}10y" in df else None, df["_de10y"]
    if ulke10 is not None:
        r["delta_ulke10y_bp"] = _f((ulke10.loc[son] - ulke10.loc[b]) * 100)
        r["delta_de10y_bp"] = _f((de10.loc[son] - de10.loc[b]) * 100)
    if o["kimlik"] == "italya_2018_mayis":
        r["delta_it2y_bp"] = _f((df["_it2y"].loc[son] - df["_it2y"].loc[b]) * 100)
        r["delta_fark_2y_bp"] = _f(df["it2y"].loc[son] - df["it2y"].loc[b])
        k = oo.cnbc_kur()["eur"].dropna()      # hafta içi, bozuk kotasyon günleri ayıklanmış
        r["delta_eurusd_yuzde"] = _f((math.log(k.asof(son)) - math.log(k.asof(b))) * 100)
        r["saat_notu"] = ("Getiriler Avrupa kapanışı (Paris 17:30), EUR/USD New York 17:00: aynı günün iki kapanışı "
                          "arasında beş buçuk saat var.")
    if "not" in o:
        r["not"] = o["not"]
    return r


def _olay_aylik(o: dict, m: pd.DataFrame) -> dict:
    s = m[o["ulke"]].dropna()
    w = s.loc[pd.Period(o["ilk_ay"], "M"):pd.Period(o["son_ay"], "M")]
    once = s.loc[:pd.Period(o["ilk_ay"], "M") - 1]
    return {"kimlik": o["kimlik"], "ad": o["ad"], "ulke": o["ulke"], "kaynak": "ECB aylık ortalama",
            "ilk": str(w.index.min()), "son": str(w.index.max()), "n_ay": int(len(w)),
            "fark_onceki_ay_bp": _f(once.iloc[-1]) if len(once) else None,
            "zirve_bp": _f(w.max()), "zirve_ayi": str(w.idxmax()), "fark_son_bp": _f(w.iloc[-1]),
            "not": o.get("not")}


def p6d() -> dict:
    df, temizlik = cevre_gunluk()
    atilan = temizlik["sifir"]
    m = ecb_aylik()
    gunluk = {}
    for u in CEVRE:
        s = df[u].dropna()
        gunluk[u.upper()] = {"n": int(len(s)), "ilk": _iso(s.index.min()), "son": _iso(s.index.max()),
                             "ort_bp": _f(s.mean()), "azami_bp": _f(s.max()), "azami_gunu": _iso(s.idxmax()),
                             "son_bp": _f(s.iloc[-1])}
    aylik = {}
    for u in ECB_CEVRE:
        s = m[u].dropna()
        aylik[u] = {"n": int(len(s)), "ilk": str(s.index.min()), "son": str(s.index.max()),
                    "ort_bp": _f(s.mean()), "azami_bp": _f(s.max()), "azami_ayi": str(s.idxmax()),
                    "son_bp": _f(s.iloc[-1])}
    # sınama: günlük CNBC farkının aylık ortalaması ↔ ECB aylık farkı
    sinama = {}
    for u in ("it", "es", "fr", "pt", "gr"):
        g = df[u].dropna()
        ga = g.groupby(pd.PeriodIndex(g.index, freq="M")).mean()
        j = pd.concat([ga.rename("c"), m[u.upper()].rename("e")], axis=1, sort=True).dropna()
        sinama[u.upper()] = {"ortak_ay": int(len(j)), "korelasyon": _f(j.corr().iloc[0, 1]),
                             "ort_mutlak_fark_bp": _f((j["c"] - j["e"]).abs().mean()),
                             "ort_fark_bp": _f((j["c"] - j["e"]).mean())}
    olaylar = [(_olay_aylik(o, m) if o["kaynak"] == "ecb_aylik" else _olay_gunluk(o, df)) for o in OLAYLAR_AVRUPA]
    try:
        eb = bulut.eurostat_borc()
        panel = {}
        son_yil = int(eb["borc"].dropna(how="all").index.max().year)
        for u in EUROSTAT_CEVRE:
            r = {}
            for yil in (2010, son_yil):
                t = pd.Timestamp(f"{yil}-12-31")
                r[str(yil)] = {"borc_gsyh": _f(eb["borc"].loc[t, u]) if t in eb["borc"].index else None,
                               "denge_gsyh": _f(eb["denge"].loc[t, u]) if t in eb["denge"].index else None}
            zirve = eb["borc"][u].dropna()
            r["borc_zirve"] = {"yil": str(zirve.idxmax().year), "borc_gsyh": _f(zirve.max())}
            panel[u] = r
        eurostat = {"n": len(panel), "ilk": "2010", "son": str(son_yil),
                    "yontem": "Eurostat genel yönetim brüt (Maastricht) borcu ve net borç verme/alma, GSYH'ye oran, "
                              "2010 ve son yıl; zirve yılı ayrıca.",
                    "kaynak": ["bulut: eurostat_borc"], "not": "Eurostat'ta Yunanistan EL kodludur.",
                    "panel": panel}
    except bulut.VeriYok as e:
        eurostat = kurulmadi(f"Eurostat genel yönetim borcu: {e}")
    return {
        "n": int(df[CEVRE].notna().any(axis=1).sum()), "ilk": _iso(df.index.min()), "son": _iso(df.index.max()),
        "yontem": "Çevre ülkelerin 10 yıllık gösterge getirisinin aynı kaynaktaki Alman 10 yıllığından farkı baz puan "
                  "olarak günlük (CNBC, Avrupa kapanışı) ve aylık ortalama (ECB Maastricht ölçütü) alındı; olay "
                  "pencerelerinde farkın başlangıç, zirve ve son değeri ölçüldü.",
        "kaynak": ["cnbc_avrupa_getiri_gunluk", "ecb_maastricht_aylik", "cnbc_kur_gunluk", "bulut: eurostat_borc"],
        "gunluk": gunluk,
        "aylik": aylik,
        "sifir_dizisi_atilan": atilan,
        "donmus_dizi_atilan": temizlik["donmus"],
        "temizlik_notu": "Art arda beş ve daha fazla iş günü birebir aynı kalan getiri taşınmış kotasyondur: dizinin "
                         "ilk günü kalır, sonrakiler atılır; uzun sıfır dizileri ve tek başına düşen sıfırlar da veri "
                         "boşluğudur.",
        "sinama_gunluk_aylik": sinama,
        "olaylar": olaylar,
        "eurostat": eurostat,
    }


def sekil_11() -> dict:
    m = ecb_aylik()
    p = p6d()
    return {
        "n": int(len(m)), "ilk": str(m.index.min()), "son": str(m.index.max()),
        "yontem": "Çevre ülke − Almanya 10 yıllık farkı (ECB Maastricht aylık ortalaması, baz puan) ve günlük olay "
                  "pencerelerinin özeti.",
        "kaynak": ["ecb_maastricht_aylik", "cnbc_avrupa_getiri_gunluk"],
        "ay": [str(t) for t in m.index],
        **{f"{u}_bp": [_f(v) for v in m[u]] for u in ECB_CEVRE},
        "olaylar": [{k: r.get(k) for k in ("kimlik", "ad", "ulke", "kaynak", "ilk", "son", "zirve_bp",
                                           "zirve_gunu", "zirve_ayi", "fark_bas_bp", "fark_onceki_ay_bp",
                                           "fark_son_bp", "delta_fark_bp") if k in r}
                    for r in p["olaylar"]],
    }


# ═══════════════════════════════════════════════════════════════ giriş
def olc() -> dict:
    return oo.yuvarla({
        "p6a": p6a(),
        "p6b": p6b(),
        "p6c": p6c(),
        "p6d": p6d(),
        "arac_borc": arac_borc(),
        "sekil_09": sekil_09(),
        "sekil_10": sekil_10(),
        "sekil_11": sekil_11(),
    }, 4)


if __name__ == "__main__":
    import json
    import time
    t0 = time.time()
    d = olc()
    print(json.dumps(d, ensure_ascii=False)[:4000])
    print(f"süre {time.time() - t0:.1f} sn")
