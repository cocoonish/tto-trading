#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRODAN KURA VE FAİZE — Bölüm 13 (Sentez: veri günü oyun kitabı) ölçüm katmanı.

Pratikler
  matris         ŞOK × REJİM matrisi: on şok × altı rejim sütunu × dört seri
                 (kur · 2 yıllık · uzun uç · eğim). Hücre: olay sayısı, olay günü
                 |Δ|'sının aynı rejimin sıradan günlerine oranı, kur–faiz eş hareketi
                 corr(Δ2y, Δpara değeri) ve durumu (ölçüldü · vaka · kaynak · kurulmadı).
  sekil_21       matrisin ısı haritası verisi (şok satırları × rejim sütunları).
  teshis_ornegi  beş adımlı teşhis protokolünün çıpa günü (30.09.2026) girdileri.
  kart_kanit     veri günü kartlarının her satırı için kanıt yolları (ölçüm
                 dosyasındaki anahtar yolu) ve kanıtın gücü.

Bu modül ÖLÇÜYÜ YENİDEN KURMAZ. Rejim etiketi Bölüm 1'in `rejim()`inden, olay
listeleri ve hizalar bölüm modüllerinden, plasebo kapısı `ortak_olc.olay_kapisi`den
gelir; bir seri × olay türünün kapısını daha önce bir bölüm ölçtüyse hüküm o
bölümün çıktısından okunur (aynı tohum, aynı seri — iki yerde iki hüküm olmaz).
Yalnız önceki bölümlerin hiç sormadığı seri × olay türleri (eğim; ABD 10 yıllığı
× FOMC; VIX sıçraması, haftalık rezerv ve enerji şoku günleri) burada ilk kez
aynı kapıdan geçirilir.

REJİM SÜTUNLARI. b01'in haftalık etiketi ABD için R1/R2/R5, Türkiye için
R3/R4/R5'tir. R5 küresel riskten kaçışın İKİ ayrı yüzüdür — DM tarafında dolar
ve ABD getirisi, EM tarafında lira ve DİBS — ve işaretleri ters olabildiği için
iki sütundur: R5_DM ve R5_EM. DM sütunları ABD verisiyle, EM sütunları Türkiye
verisiyle doldurulur; tek istisna bütçe satırının pencereleridir (İngiltere 2022
DM sütununa, euro çevresi EM sütununa) ve o satırın etiketi ölçülmüş bir hafta
etiketi değil, VIX ölçütü artı olay seçimidir (aşağıda tuzak 5).

HÜCRENİN ÖLÇÜLERİ
  oran      ortalama |Δ| olay günü / ortalama |Δ| sıradan gün; sıradan gün = aynı
            olay türünün ±2 dönemlik penceresinin dışında ve AYNI rejim
            etiketini taşıyan gün (plasebo profilinin tabanıyla aynı tanım, rejime
            koşullu). Çok günlük vaka pencerelerinde oran, aynı uzunluktaki sıradan
            pencerelerin ortalama |Δ|'sına göre kurulur ve vakaların ortalamasıdır.
  eş hareket corr(Δ2y, Δpara değeri) olay günlerinde; para değeri artışı YEREL
            PARANIN değer kazancıdır (Türkiye: −Δlog USD/TRY; ABD: dolar sepetinin
            dolar yönünde log değişimi). Artı = faiz ↑ para ↑ (B terimi, faiz farkı);
            eksi = faiz ↑ para ↓ (C terimi, risk primi). Yanında aynı rejimin sıradan
            günlerinin korelasyonu ve B kadranının payı (işaret çarpımı artı).
  durum     ölçüldü: en az bir seri kapıyı geçti ve olay ≥ 10 · vaka: 1–9 olay
            (oranlar yazılır, korelasyon yazılmaz) · kaynak: bu veriyle kurulamadı (seri
            ya da olay yok, ya da sınama geçmedi) ama dersin kaynak listesi kapsıyor
            (yalnız etiket ve bölüm işareti, sayı yok; işaret sebepten önce gelir) ·
            kurulmadı: sebebiyle. Kurulamayan her hücre sebebini `sebep_turu` ile de
            taşır (veri_yok · olay_yok · plasebo · olay_az). Kapıyı geçmeyen seri hücrede
            "kurulmadı (kapı)"dır; eş hareket ancak 2 yıllık ile kur İKİSİ DE kapıdan
            geçtiyse yazılır.

ÖLÇÜLEREK BULUNAN TUZAKLAR (kod onları kapatır, metin adıyla anar)
  1. REJİM ETİKETİ AYNI HAFTANIN KADRANINDAN KURULUR. R2 ve R4, uzun ucun yükselip
     paranın değer kaybettiği haftalardır; olay günü o haftanın içindeyse R2/R4
     hücresinin eş hareketi kısmen tanım gereği eksidir (seçim). Her günlük hücreye
     bu yüzden bir ÖNCEKİ haftanın etiketiyle kurulmuş ex ante sürüm (`onceki_hafta`)
     eklenir; iki sürüm ayrışıyorsa hücrenin işareti etiketin kendisinden gelir.
  2. TÜRKİYE HAFTASI PERŞEMBE KAPANIŞIYLA ÖRNEKLENİR (b01, tuzak 5): cuma etiketli
     haftanın değişimi önceki perşembeden bu perşembeye kadardır. CUMA günü düşen
     bir olay bu yüzden takvim haftasının değil BİR SONRAKİ etiketin değişimine
     girer; gün → hafta eşlemesi takvim haftasıyla değil, örnek günüyle yapılır
     (gün, değişim aralığı onu içeren haftaya yazılır).
  3. VIX SIÇRAMASI GÜNLERİ ÇIKTI ÜZERİNDEN SEÇİLİR: VIX'in büyük artışı dolar ve ABD
     getirisinin büyük hareketiyle aynı günde doğar; ABD tarafında kapının geçmesi
     ve oranın yüksekliği kısmen seçimin kendisidir. Aynı sebeple bu günlerin çoğu
     R5 haftasına düşer (R5 haftanın VIX düzeyiyle tanımlıdır).
  4. HAFTALIK REZERV OLAYI BİR YAYIM DEĞİL, REZERVİN HAREKET ETTİĞİ HAFTADIR. Rezerv
     cuma stokudur ve bir sonraki perşembe yayımlanır; burada ölçülen, yayımın
     tepkisi değil, rezervin büyük oynadığı haftayla aynı haftanın kur ve getiri
     hareketidir (Bölüm 9'un eşzamanlı ayrışımıyla aynı soru). Kur haftası perşembe
     kapanışıdır, rezerv cuma stoku: bir seanslık kayma.
  5. ÇEVRE ÜLKE VE İNGİLTERE PENCERELERİNİN KENDİ REJİM ETİKETİ YOK (Bölüm 1 yalnız
     ABD ve Türkiye için kurar). Pencerenin günleri VIX ölçütünü (ABD haftasının cuma
     VIX'i ≥ genişleyen 75. yüzdelik) çoğunlukla geçiyorsa R5, geçmiyorsa olay mali
     stres penceresi olarak seçildiği için R2 (İngiltere) ya da R4 (euro çevresi)
     sütununa yazılır: etiket ölçüm değil, olay seçimidir ve hücrede `etiket_kaynagi`
     alanıyla durur. ÇOK GÜNLÜK PENCERENİN ETİKETİ ÇOĞUNLUKTUR: İtalya 2011 penceresi
     (30.06 → 30.11) tepki gününe göre R4'e düşüyordu (01.07.2011'de VIX 16), oysa
     108 günün 92'si R5 haftasıdır. Pencere ve aynı uzunluktaki sıradan pencereler
     günlerinin çoğunluk etiketini alır (eşitlikte şiddetlisi).
  6. ÇİFT SAYIM: ABD'nin 2023 Ağustos borçlanma penceresi Fitch'in 02.08.2023 tepki
     gününü içerir (Bölüm 5, tuzak 2: iki haber tek günde). Moody's 2025 kararı
     bütçe satırına GİRMEZ, yalnız not kararı satırındadır; Fitch günü iki satırda
     da görünür ve öyle işaretlenir.
  7. YÖNETİLEN KUR DÖNEMİ (2021-12 … 2023-06) Türkiye'nin KUR serisinde ve eş
     harekette havuza girmez (kapıyla aynı kural); DİBS oranları dönemi içerir. Seri
     başına olay sayısı bu yüzden farklıdır (`n_seri`).
  8. KAPI İKİ SORUYU BİRDEN SORAR ve haftalık rezervde ikisi ayrışır: kurun plasebo
     profilinin tepesi olay haftasındadır (tarih sözleşmesi tutuyor) ama oran olay
     haftasında da komşu haftalarda da 1'in ALTINDADIR (0,52–0,65): büyük rezerv
     hareketi haftalarında kur sıradan haftadan SESSİZDİR ve güçlü kapı (rastgele
     kümelerin %95'ini aşmak) bu yüzden düşer. Hücre kurala uyar ("kurulmadı (kapı)");
     profil `matris_meta.rezerv.kapi_em.kur`da durur. DİBS'in profili ise bütün
     kaymalarda ≈2 ve düzdür: rezerv şokları oynak dönemlere kümelenir, haftayı ayırmaz.
  9. VIX SIÇRAMALARI KÜMELENİR: Türkiye serilerinde olay günü oranı komşu günlerden
     ayrışmıyor (DİBS profili 0,9–1,2, tepe +2); kur tepe 0'da ama güçlü kapı sınırın
     dışında (p 0,06). Küresel risk satırının EM yüzü bu yüzden kurulmadı; ABD yüzünde
     dört seri de kapıyı geçer (tuzak 3: seçim).
 10. EŞ HAREKETİN "FAİZİ" PİYASA GETİRİSİDİR, POLİTİKA SÜRPRİZİ DEĞİL. PPK günlerinde
     2 yıllık DİBS ile liranın değeri TERS yönde oynar (R3'te korelasyon eksi, sıra
     korelasyonuyla da): 13.09.2018 ve 24.08.2023 artırımlarında lira değer kazanırken
     2 yıllık 330 ve 184 baz puan DÜŞTÜ. Aynı günlerin anket sürprizine karşı kur
     eğimi (Bölüm 3) B yönlüdür (şahin sürpriz → lira ↑). İki ölçü çelişmez: güvenilir
     bir artırım risk primini düşürür ve 2 yıllık getiri primi taşır. Hücre işareti
     "politika sürprizinin kura etkisi" diye okunmaz.
 11. DÖRT ONDALIKTA ÇAKIŞMA: ABD bütçe pencerelerinin R1 kur oranı ile Fitch
     tepki gününün kur oranı dört ondalıkta aynı sayıdır (1,5487) — üç pencerenin
     ortalaması ile tek günün oranı, tesadüf. Sayı envanteri bir metin sayısını iki
     anahtardan birine bağlarken bunu bilmelidir.
"""
from __future__ import annotations

import math
import warnings
from functools import lru_cache

import numpy as np
import pandas as pd

import bulut
import ortak_olc as oo
import olcum_b01 as b01
import olcum_b02 as b02
import olcum_b03 as b03
import olcum_b04 as b04
import olcum_b05 as b05
import olcum_b06 as b06
import olcum_b08 as b08
import olcum_b09 as b09
import olcum_b10 as b10
import olcum_b12 as b12

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)
try:
    warnings.filterwarnings("ignore", category=pd.errors.Pandas4Warning)  # type: ignore[attr-defined]
except AttributeError:
    pass

_iso, _f, kurulmadi = oo._iso, oo._f, oo.kurulmadi

# ───────────────────────────────────────────────────────── sabitler (adlı)
VAKA_ASGARI = 10                    # n < 10: vaka (oranlar yazılır, korelasyon yazılmaz)
PENCERE = oo.OLAY_PENCERE           # ±2 dönem: olay penceresi ve sıradan günün tanımı
HIZA = "gun_sonu"                   # DİBS ↔ gün sonu kapanışı (ortak_olc.DIBS_KAYMA)
ENERJI_SOK_SIGMA = 1.5              # emtia şoku: |Δlog enerji| ≥ 1,5σ (görev tanımı)
REZERV_SOK_SIGMA = 1.5              # rezerv şoku: |rezerv bileşeni| ≥ 1,5σ (enerjiyle aynı eşik)
REZERV_DUYARLILIK = (1.0, 2.0)
VIX_UST_PAY = 0.02                  # küresel risk: günlük VIX artışının üst %2'si
VIX_ILK = "2000-01-01"              # ABD çerçevesinin başı (Bölüm 1)
TOHUM = 1300                        # bu modülde İLK KEZ sorulan kapıların tohum tabanı

SERILER = ("kur", "2y", "uzun", "egim")
SERI_AD = {"kur": "kur", "2y": "2 yıllık getiri", "uzun": "uzun uç", "egim": "eğim (uzun − 2 yıllık)"}
SERI_BIRIM = {"dm": {"kur": "G10 dolar sepeti, log %", "2y": "ABD 2 yıllık, bp", "uzun": "ABD 10 yıllık, bp",
                     "egim": "10 yıllık − 2 yıllık, bp"},
              "em": {"kur": "USD/TRY, log %", "2y": "DİBS 2 yıllık, bp", "uzun": "DİBS 5 yıllık, bp",
                     "egim": "5 yıllık − 2 yıllık, bp"}}

SUTUNLAR = (("R1", "DM normal", "dm"), ("R2", "DM mali kaygı", "dm"),
            ("R3", "EM güvenilir merkez bankası", "em"), ("R4", "EM mali baskınlık", "em"),
            ("R5_DM", "küresel riskten kaçış, DM tarafı (ABD)", "dm"),
            ("R5_EM", "küresel riskten kaçış, EM tarafı (Türkiye)", "em"))
SUTUN_KIM = tuple(s for s, _, _ in SUTUNLAR)
TARAF_SUTUN = {"dm": ("R1", "R2", "R5_DM"), "em": ("R3", "R4", "R5_EM")}
ETIKET_SUTUN = {"dm": {"R1": "R1", "R2": "R2", "R5": "R5_DM"}, "em": {"R3": "R3", "R4": "R4", "R5": "R5_EM"}}
SIDDET = {"R5_DM": 3, "R5_EM": 3, "R2": 2, "R4": 2, "R1": 1, "R3": 1}   # aylık çoğunluk eşitliğinde

SOKLAR = (("butce", "Bütçe / borçlanma programı"), ("gsyh", "GSYH, PMI/ISM"), ("istihdam", "İstihdam"),
          ("tufe", "TÜFE"), ("para", "Para politikası (PPK · FOMC)"), ("cari", "Cari denge / dış ticaret"),
          ("rezerv", "Haftalık rezerv"), ("not", "Not kararı"), ("emtia", "Emtia / enerji şoku"),
          ("kuresel", "Küresel risk (VIX sıçraması)"))

# Kaynak işaretleri: bu veriyle kurulamayan ama dersin KAYNAK LİSTESİNİN kapsadığı
# hücreler (içindekilerdeki bölüm maddelerinden). Sayı ve atıf metni burada
# DEĞİLDİR (kaynak iddiası ölçüm dosyasına girmez); yalnız bölüm işareti. İşaret,
# hücre kurulamadığında sebebinden (veri yok · olay yok · plasebo) ÖNCE gelir; sebep
# hücrede ayrıca durur (`sebep_turu`). Not kararı R3/R4 bu listede YOK: Bölüm 12'nin
# kaynakları EM not kararının piyasa tepkisini anlatmıyor (konunun aday kaynakları
# doğrulanamadı), hücre kapının kendi sonucuyla "kurulmadı"dır.
KAYNAK_BOLUM = {
    ("butce", "R1"): "Bölüm 5", ("butce", "R2"): "Bölüm 5", ("butce", "R4"): "Bölüm 6",
    ("gsyh", "R1"): "Bölüm 3", ("istihdam", "R1"): "Bölüm 3",
    ("tufe", "R1"): "Bölüm 4", ("tufe", "R4"): "Bölüm 4",
    ("para", "R1"): "Bölüm 3", ("para", "R4"): "Bölüm 6",
    ("cari", "R1"): "Bölüm 8", ("cari", "R4"): "Bölüm 8",
    ("rezerv", "R1"): "Bölüm 9", ("rezerv", "R3"): "Bölüm 9", ("rezerv", "R4"): "Bölüm 9",
    ("not", "R2"): "Bölüm 12",
    ("emtia", "R1"): "Bölüm 10", ("emtia", "R4"): "Bölüm 10",
    ("kuresel", "R5_DM"): "Bölüm 11", ("kuresel", "R5_EM"): "Bölüm 11",
}
# Kurulamayan hücrenin sebebi (kurulmadı ve kaynak hücrelerinde; okur dili matris tanımında)
SEBEP_TURU = {"veri_yok": "olay günü listesi ya da seri elde yok",
              "olay_yok": "bu rejim etiketinde olay yok",
              "plasebo": "olay var ama sınanan serilerin hiçbiri plasebo sınamasını geçmedi",
              "olay_az": "plasebo sınaması geçti ama rejim ayrımı için olay sayısı yetmiyor"}

KAYNAK_DM = ["abd_hazine_gunluk", "cnbc_kur_gunluk", "yahoo_dxy_vix_gunluk"]
KAYNAK_EM = ["dibs_egri_gunluk", "usdtry_yahoo_gunluk", "fonlama_gunluk (iş günü takvimi)"]


# ═══════════════════════════════════════════════════════════════ çerçeveler
@lru_cache(maxsize=1)
def _dm_gunluk() -> pd.DataFrame:
    """ABD günlük değişim çerçevesi (Bölüm 2'nin ABD serileriyle aynı: ortak gün, 2000+)."""
    g = oo.abd_gunluk_degisim()
    g = g[g.index >= b01.ILK_GUN]
    return pd.DataFrame({"kur": g["dolar_yuzde"], "2y": g["us2_bp"], "uzun": g["us10_bp"],
                         "egim": g["us10_bp"] - g["us2_bp"], "para": g["dolar_yuzde"]}, index=g.index)


@lru_cache(maxsize=1)
def _em_gunluk() -> pd.DataFrame:
    """Türkiye günlük değişim çerçevesi: DİBS gün sonu hizası, USD/TRY Yahoo, 18.12.2023
    öncesi cuma kur değişimi boş (Bölüm 3–4'ün olay çerçevesiyle aynı)."""
    d = oo.tr_gunluk_degisim(HIZA, ("n2y", "n5y"), kur=True, tcmb=False, cuma_dus=True)
    return pd.DataFrame({"kur": d["usdtry"], "2y": d["n2y"], "uzun": d["n5y"], "egim": d["n5y"] - d["n2y"],
                         "para": -d["usdtry"]}, index=d.index)


@lru_cache(maxsize=1)
def _em_haftalik() -> pd.DataFrame:
    """Bölüm 1'in Türkiye haftası (perşembe kapanışı, DİBS gün sonu hizası)."""
    w = b01._tr_haftalik()
    w = w[~w["_kismi"].astype(bool)]
    return pd.DataFrame({"kur": w["dkur_yuzde"], "2y": w["d2_bp"], "uzun": w["d5_bp"], "egim": w["degim_bp"],
                         "para": -w["dkur_yuzde"]}, index=w.index)


@lru_cache(maxsize=1)
def _dm_aylik() -> pd.DataFrame:
    a = oo.abd_gunluk()
    m = a[["us2", "us10", "sepet"]].resample("MS").last()
    d = pd.DataFrame({"kur": m["sepet"].diff() * 100, "2y": m["us2"].diff() * 100, "uzun": m["us10"].diff() * 100})
    d["egim"] = d["uzun"] - d["2y"]
    d["para"] = d["kur"]
    return d.loc[b10.BAS:b10.SON]


@lru_cache(maxsize=1)
def _em_aylik() -> pd.DataFrame:
    """Ay sonu (Bölüm 10'un Türkiye aylık çerçevesiyle aynı hiza; aylık pencereler bitişik
    kalsın diye cuma değeri tutulur, b10 tuzak 5)."""
    s, _ = oo.usdtry()
    ls = np.log(s.dropna()) * 100
    d = oo.dibs(HIZA, ("n2y", "n5y"))
    dm = d.resample("MS").last() * 100
    out = pd.DataFrame({"kur": ls.resample("MS").last().diff(), "2y": dm["n2y"].diff(), "uzun": dm["n5y"].diff()})
    out["egim"] = out["uzun"] - out["2y"]
    out["para"] = -out["kur"]
    return out.loc[b10.TR_BAS:b10.SON]


# ═══════════════════════════════════════════════════════════════ rejim eşlemesi
@lru_cache(maxsize=2)
def _hafta(taraf: str) -> tuple:
    """(örnek günleri, sütun etiketleri, R5 bayrağı, hafta etiketleri) — çıpa haftası hariç."""
    r = b01.rejim()
    r = r[~r["kismi"].astype(bool)]
    u = "abd" if taraf == "dm" else "tr"
    z = r[[u, f"{u}_gun", f"{u}_r5"]].dropna(subset=[u, f"{u}_gun"]).copy()
    z["_g"] = pd.DatetimeIndex(z[f"{u}_gun"])
    z = z.sort_values("_g")
    return (pd.DatetimeIndex(z["_g"]), np.array([ETIKET_SUTUN[taraf][x] for x in z[u]], dtype=object),
            z[f"{u}_r5"].astype(bool).values, pd.DatetimeIndex(z.index))


def gun_rejimi(gunler, taraf: str, onceki: bool = False) -> pd.Series:
    """Gün → rejim sütunu. Gün, değişim aralığı (önceki örnek günü, örnek günü] onu içeren
    haftanın etiketini alır (tuzak 2). `onceki`: bir önceki haftanın etiketi (ex ante)."""
    gun, lab, _, _ = _hafta(taraf)
    gunler = pd.DatetimeIndex(gunler)
    j = gun.searchsorted(gunler, side="left")
    out = []
    for d, jj in zip(gunler, j):
        if jj >= len(gun) or (jj == 0 and d <= gun[0] - pd.Timedelta(days=7)):
            out.append(None)
            continue
        k = jj - 1 if onceki else jj
        out.append(lab[k] if k >= 0 else None)
    return pd.Series(out, index=gunler, dtype=object)


def gun_r5(gunler, taraf: str = "dm") -> pd.Series:
    """Günün haftası VIX ölçütünü (R5) geçiyor mu (Bölüm 1'in kuralı)."""
    gun, _, r5, _ = _hafta(taraf)
    gunler = pd.DatetimeIndex(gunler)
    j = gun.searchsorted(gunler, side="left")
    return pd.Series([bool(r5[jj]) if jj < len(gun) else None for jj in j], index=gunler, dtype=object)


def hafta_rejimi(hafta_etiketleri, taraf: str, onceki: bool = False) -> pd.Series:
    """Haftalık çerçeve: aynı cuma etiketinin rejimi (ya da bir önceki haftanınki)."""
    r = b01.rejim()
    r = r[~r["kismi"].astype(bool)]
    u = "abd" if taraf == "dm" else "tr"
    lab = r[u].dropna().map(ETIKET_SUTUN[taraf])
    if onceki:
        lab = lab.shift(1)
    return lab.reindex(pd.DatetimeIndex(hafta_etiketleri)).astype(object).where(lambda x: x.notna(), None)


def ay_rejimi(aylar, taraf: str, onceki: bool = False) -> pd.Series:
    """Ay → örnek günü o ayda olan haftaların ÇOĞUNLUK etiketi (eşitlikte şiddetlisi)."""
    gun, lab, _, _ = _hafta(taraf)
    df = pd.DataFrame({"ay": gun.to_period("M"), "lab": lab})
    harita = {}
    for ay, g in df.groupby("ay"):
        say = g["lab"].value_counts()
        tepe = say.max()
        aday = sorted([k for k, v in say.items() if v == tepe], key=lambda k: (-SIDDET[k], k))
        harita[ay] = aday[0]
    aylar = pd.DatetimeIndex(aylar)
    p = aylar.to_period("M")
    if onceki:
        p = p - 1
    return pd.Series([harita.get(x) for x in p], index=aylar, dtype=object)


# ═══════════════════════════════════════════════════════════════ kapılar
DONEM_BIRIMI = {"gun": ("iş gününde", "olay günü"), "hafta": ("haftada", "olay haftası"), "ay": ("ayda", "olay ayı")}


def _kapi_yeni(seri: pd.Series, olaylar, kur_em: bool, tohum: int, donem: str = "gun") -> dict:
    """Bu modülde ilk kez sorulan seri × olay türü: kanonik güçlü kapı. Haftalık ve aylık
    çerçevede kayma birimi hafta ve aydır (sebep metni birimini taşır)."""
    k = oo.olay_kapisi(seri, olaylar, guclu=True, k_tohum=TOHUM + tohum, haric=oo.YONETILEN if kur_em else None)
    o = oo.kapi_ozeti(k)
    o["kaynak"] = "bu bölümde ilk kez sorulan seri"
    o["kayma_birimi"] = {"gun": "iş günü", "hafta": "hafta", "ay": "ay"}[donem]
    if not k["gecti"]:
        kayma, olay = DONEM_BIRIMI[donem]
        o["sebep"] = oo.kapi_sebebi(k).replace("iş gününde", kayma).replace("olay günü", olay)
    return o


def _kapi_hazir(ozet: dict, kaynak: str) -> dict:
    o = {a: ozet[a] for a in ("n_olay", "tepe", "kapi", "kapi_guclu", "p_rastgele_oran0", "guclu_sinirda", "gecti")
         if a in ozet}
    o["kaynak"] = kaynak
    if not o.get("gecti"):
        o["sebep"] = oo.kapi_sebebi(ozet) if "tepe" in ozet else "kapı kurulmadı"
    return o


def _b02_kapi(seri: str, olay: str, kaynak: str) -> dict:
    r = next(x for x in b02._tablo()[0] if x["seri"] == seri and x["olay"] == olay)
    o = {"n_olay": r.get("n_olay"), "tepe": r.get("tepe"), "kapi": r.get("kapi"), "kapi_guclu": r.get("kapi_guclu"),
         "p_rastgele_oran0": r.get("p_rastgele_oran0"), "guclu_sinirda": r.get("guclu_sinirda"),
         "saat_tutarli": r.get("saat_tutarli"), "gecti": bool(r.get("kurulabilir")), "kaynak": kaynak}
    if not o["gecti"]:
        o["sebep"] = oo.kapi_sebebi(r) if r.get("tepe") is not None else r.get("sebep", "kapı kurulmadı")
    return o


# ═══════════════════════════════════════════════════════════════ hücre
def _ort_abs(x: pd.Series) -> float | None:
    x = x.dropna()
    return float(x.abs().mean()) if len(x) else None


def _oran(ee: pd.Series, ss: pd.Series) -> float | None:
    a, b = _ort_abs(ee), _ort_abs(ss)
    if a is None or b is None or b == 0:
        return None
    return a / b


def _es(y: pd.Series, p: pd.Series, sira: bool = False):
    """(n, Pearson, B kadranı payı[, Spearman]): 2 yıllık değişim × para değeri değişimi."""
    d = pd.concat([y.rename("y"), p.rename("p")], axis=1, sort=True).dropna()
    n = int(len(d))
    if n < 3 or d["y"].std() == 0 or d["p"].std() == 0:
        return (n, None, None, None) if sira else (n, None, None)
    kor = float(np.corrcoef(d["y"], d["p"])[0, 1])
    sg = np.sign(d["y"]) * np.sign(d["p"])
    sg = sg[sg != 0]
    b_pay = float((sg > 0).mean()) if len(sg) else None
    if sira:
        return n, kor, b_pay, float(d["y"].corr(d["p"], method="spearman"))
    return n, kor, b_pay


def _fisher_z(r1: float | None, n1: int, r2: float | None, n2: int) -> float | None:
    """Olay günü ile sıradan gün korelasyonunun farkı, Fisher dönüşümüyle (bağımsız ve normal
    gözlem varsayımı; kalın kuyruklu günlük değişimde yaklaşık): |z| ≥ 2 ayrışma."""
    if r1 is None or r2 is None or n1 < 4 or n2 < 4 or abs(r1) >= 1 or abs(r2) >= 1:
        return None
    return float((math.atanh(r1) - math.atanh(r2)) / math.sqrt(1 / (n1 - 3) + 1 / (n2 - 3)))


def _durum(sok: str, sutun: str, n: int, gecen: list, sebep_yok: str | None = None,
           tur_yok: str = "veri_yok") -> tuple[str, str | None, str | None]:
    """(durum, not, sebep türü). Kaynak işareti sebepten önce gelir; sebep türü yine yazılır."""
    if sebep_yok:
        d, s, tur = "kurulmadi", sebep_yok, tur_yok
    elif n == 0:
        d, s, tur = "kurulmadi", "bu rejim etiketinde olay yok", "olay_yok"
    elif not gecen:
        d, s, tur = "kurulmadi", "kapı: dört serinin hiçbiri plasebo kapısını geçmedi", "plasebo"
    elif n < VAKA_ASGARI:
        return "vaka", None, None
    else:
        return "olculdu", None, None
    if (sok, sutun) in KAYNAK_BOLUM:
        return "kaynak", s, tur
    return d, s, tur


def _bos_hucre(sok: str, sutun: str, sebep: str, tur: str = "veri_yok") -> dict:
    d, s, t = _durum(sok, sutun, 0, [], sebep, tur)
    h = {"durum": d, "n": 0, "oranlar": None, "es_hareket": None, "not": s, "sebep_turu": t}
    if (sok, sutun) in KAYNAK_BOLUM:
        h["kaynak_bolum"] = KAYNAK_BOLUM[(sok, sutun)]
        h["olcum_denemesi"] = s
    return h


def _olay_hucreleri(sok: str, F: pd.DataFrame, olaylar, taraf: str, kapilar: dict, reg: pd.Series,
                    reg_o: pd.Series, birim: str, pencere_not: str) -> dict:
    """Olay listesi olan şok (günlük, haftalık ya da aylık çerçeve): taraf sütunlarının hücreleri."""
    idx = F.index
    ev = idx.intersection(pd.DatetimeIndex(olaylar).normalize())
    yon = pd.Series(oo.yonetilen_mi(idx) if taraf == "em" else np.zeros(len(idx), bool), index=idx)
    seri = {}
    for c in SERILER + ("para",):
        x = F[c]
        if taraf == "em" and c in ("kur", "para"):
            x = x[~yon.values]
        seri[c] = x.dropna()
    sakin = {c: b03.sakin_gunler(seri[c].index, ev, PENCERE) for c in seri}
    sakin_ortak = b03.sakin_gunler(idx, ev, PENCERE)
    gecen = [c for c in SERILER if kapilar[c].get("gecti")]
    es_ok = bool(kapilar["2y"].get("gecti") and kapilar["kur"].get("gecti"))
    out = {}
    rejimsiz = int(reg.loc[ev].isna().sum()) if len(ev) else 0
    for col in TARAF_SUTUN[taraf]:
        e = ev[(reg.loc[ev] == col).values] if len(ev) else ev
        n = int(len(e))
        d, s, tur = _durum(sok, col, n, gecen)
        h = {"durum": d, "n": n, "birim": birim, "pencere": pencere_not}
        if s:
            h["not"] = s
        if tur:
            h["sebep_turu"] = tur
        if (sok, col) in KAYNAK_BOLUM:
            h["kaynak_bolum"] = KAYNAK_BOLUM[(sok, col)]
            if d == "kaynak":
                h["olcum_denemesi"] = s
        if n:
            h["ilk"], h["son"] = _iso(e.min()), _iso(e.max())
        oran, nser = {}, {}
        for c in SERILER:
            if not kapilar[c].get("gecti"):
                oran[c] = "kurulmadı (kapı)"
                continue
            x = seri[c]
            ee = x.reindex(e).dropna()
            sk = sakin[c]
            ss = x.loc[sk][(reg.reindex(sk) == col).values]
            oran[c] = _f(_oran(ee, ss)) if len(ee) else None
            nser[c] = int(len(ee))
        h["oranlar"] = oran if n else None
        h["n_seri"] = nser if n else None
        if taraf == "em" and n:
            h["n_yonetilen"] = int(yon.reindex(e).sum())
        # eş hareket
        if not n:
            h["es_hareket"] = None
        elif not es_ok:
            h["es_hareket"] = "kurulmadı (kapı)"
        else:
            ne, kor, bpay, spe = _es(seri["2y"].reindex(e), seri["para"].reindex(e), sira=True)
            sk = sakin_ortak[(reg.reindex(sakin_ortak) == col).values]
            ns, kor_s, bpay_s = _es(seri["2y"].reindex(sk), seri["para"].reindex(sk))
            h["n_es"] = ne
            if ne < VAKA_ASGARI:
                h["es_hareket"] = None
                h["es_not"] = "vaka: on çiftten az, korelasyon yazılmaz"
                h["vakalar"] = _vaka_listesi(seri, e)
            else:
                h["es_hareket"] = _f(kor)
                h["es_hareket_spearman"] = _f(spe)
                h["b_payi"] = _f(bpay)
                h["es_hareket_sakin"] = _f(kor_s)
                h["b_payi_sakin"] = _f(bpay_s)
                h["n_sakin"] = ns
                h["es_fark_z"] = _f(_fisher_z(kor, ne, kor_s, ns))
                # ex ante etiket: bir önceki haftanın rejimi (tuzak 1)
                eo = ev[(reg_o.loc[ev] == col).values]
                no, kor_o, _ = _es(seri["2y"].reindex(eo), seri["para"].reindex(eo))
                h["onceki_hafta"] = {"n": int(len(eo)), "n_es": no,
                                     "es_hareket": _f(kor_o) if no >= VAKA_ASGARI else None}
        out[col] = h
    return out, {"n_olay_cercevede": int(len(ev)), "rejim_etiketi_olmayan_olay": rejimsiz}


def _vaka_listesi(seri: dict, e: pd.DatetimeIndex) -> list:
    v = []
    for t in e:
        y = seri["2y"].get(t, np.nan)
        p = seri["para"].get(t, np.nan)
        if pd.isna(y) or pd.isna(p):
            continue
        v.append([_iso(t), _f(y), _f(p), oo.kadran(float(y), float(p), "guvenli_liman")])
    return v


# ── çok günlük vaka pencereleri (bütçe ve DM not kararları)
def _cogunluk(lab: pd.Series, h: int) -> pd.Series:
    """(t−h, t] penceresinin ÇOĞUNLUK etiketi (gün ağırlıklı; eşitlikte şiddetlisi). Pencerenin
    yarısından azı etiketliyse boş."""
    kol = sorted({x for x in lab.dropna().unique()}, key=lambda k: (-SIDDET[k], k))
    if not kol:
        return pd.Series(None, index=lab.index, dtype=object)
    say = pd.DataFrame({k: (lab == k).astype(float) for k in kol}, index=lab.index).rolling(h, min_periods=h).sum()
    tepe = np.array(kol, dtype=object)[np.nan_to_num(say.values, nan=-1).argmax(axis=1)]   # ilk tepe = şiddetlisi
    out = pd.Series(tepe, index=lab.index, dtype=object)
    out[(say.sum(axis=1) < h / 2).values | say.isna().any(axis=1).values] = None
    return out


def _pencere_vakalari(sok: str, L: pd.DataFrame, olaylar: list, gun_etiketi, etiket_kaynagi: str,
                      birim: dict, ulke: str) -> list:
    """L: düzey çerçevesi (kur = paranın değeri log×100, 2y/uzun bp, egim bp) ortak günlerde.
    `gun_etiketi(günler)` → gün başına sütun etiketi. Pencerenin sütunu, (başlangıç, bitiş]
    günlerinin çoğunluk etiketidir (tek günlük pencerede tepki gününün haftası); sıradan
    pencereler aynı uzunlukta, aynı kuralla etiketlenir ve hiçbir olay penceresiyle örtüşmez."""
    idx = L.index
    pencereler = [(oo.bas_gun(idx, o["baslangic"]), oo.son_gun(idx, o["bitis"])) for o in olaylar]
    gun_lab = gun_etiketi(idx)
    satir = []
    for o, (b, s) in zip(olaylar, pencereler):
        if b is None or s is None or s <= b:
            continue
        h = int(idx.get_loc(s) - idx.get_loc(b))
        tepki = idx[idx > b][0]
        sk_lab = _cogunluk(gun_lab, h)
        col = sk_lab.get(s)
        icerik = gun_lab.loc[(gun_lab.index > b) & (gun_lab.index <= s)].dropna()
        r = {"kimlik": o["kimlik"], "ad": o["ad"], "ulke": ulke, "ilk": _iso(b), "son": _iso(s), "pencere_gun": h,
             "tepki_gunu": _iso(tepki), "sutun": col, "etiket_kaynagi": etiket_kaynagi,
             "pencere_etiketleri": {k: int(v) for k, v in sorted(icerik.value_counts().items())}}
        oranlar, deg = {}, {}
        for c in SERILER:
            if c not in L.columns:
                oranlar[c] = None
                continue
            x = L[c].dropna()
            if b not in x.index or s not in x.index:
                oranlar[c] = None
                continue
            dlt = float(x.loc[s] - x.loc[b])
            deg[c] = dlt
            dh = (x - x.shift(h)).dropna()
            # sıradan pencere: aynı sütun etiketi, hiçbir olay penceresiyle örtüşmeyen (t−h, t]
            bas = pd.DatetimeIndex(pd.Series(x.index, index=x.index).shift(h).reindex(dh.index))
            ok = np.ones(len(dh), bool)
            for (pb, ps) in pencereler:
                if pb is None or ps is None:
                    continue
                ok &= ~((dh.index > pb) & (bas < ps))
            ok &= (sk_lab.reindex(dh.index) == col).values
            taban = dh[ok].abs().mean() if ok.any() else np.nan
            oranlar[c] = _f(abs(dlt) / taban) if taban and np.isfinite(taban) else None
        r["degisim"] = {c: _f(v) for c, v in deg.items()}
        r["oranlar"] = oranlar
        if "2y" in deg and "kur" in deg:
            r["kadran_2y"] = oo.kadran(deg["2y"], deg["kur"], "guvenli_liman")
        if "uzun" in deg and "kur" in deg:
            r["kadran_uzun"] = oo.kadran(deg["uzun"], deg["kur"], "guvenli_liman")
        r["birim"] = birim
        satir.append(r)
    return satir


def _vix_etiketi(yuksek: str, normal: str):
    """Kendi rejim etiketi olmayan ülke penceresi: gün VIX ölçütünü (R5) geçiyorsa `yuksek`,
    geçmiyorsa olay seçimi gereği `normal` (tuzak 5)."""
    def f(gunler):
        r5 = gun_r5(gunler)
        return pd.Series([None if v is None else (yuksek if v else normal) for v in r5], index=r5.index, dtype=object)
    return f


def _pencere_hucreleri(sok: str, satirlar: list, sutunlar: tuple, birim: dict, not_metni: str) -> dict:
    out = {}
    for col in sutunlar:
        v = [r for r in satirlar if r["sutun"] == col]
        n = len(v)
        d, s, tur = _durum(sok, col, n, ["pencere"])
        h = {"durum": d, "n": n, "birim": birim, "pencere": "olay penceresi (vaka), aynı uzunluktaki sıradan "
                                                          "pencerelere göre"}
        if tur:
            h["sebep_turu"] = tur
        if (sok, col) in KAYNAK_BOLUM:
            h["kaynak_bolum"] = KAYNAK_BOLUM[(sok, col)]
        if not n:
            h.update({"oranlar": None, "es_hareket": None, "not": s})
        else:
            h["oranlar"] = {c: _f(np.mean([r["oranlar"][c] for r in v if r["oranlar"].get(c) is not None]))
                            if any(r["oranlar"].get(c) is not None for r in v) else None for c in SERILER}
            h["es_hareket"] = None
            h["es_not"] = "vaka: korelasyon yazılmaz; kadranlar vaka satırlarında"
            h["vakalar"] = [{k: r[k] for k in ("kimlik", "ad", "ulke", "ilk", "son", "pencere_gun", "tepki_gunu",
                                               "etiket_kaynagi", "pencere_etiketleri", "degisim", "oranlar",
                                               "kadran_2y", "kadran_uzun")
                             if k in r} for r in v]
            h["kapi"] = "uygulanmaz: vaka tablosu (çok günlük pencere)"
            h["not"] = not_metni
        out[col] = h
    return out


# ═══════════════════════════════════════════════════════════════ şoklar
def _sok_butce() -> tuple[dict, dict]:
    # DM: Bölüm 5'in olay tablosu (alt pencereler hariç; Moody's not kararı satırında — tuzak 6)
    a = oo.abd_gunluk()
    L = pd.DataFrame({"kur": a["sepet"] * 100, "2y": a["us2"] * 100, "uzun": a["us10"] * 100,
                      "egim": (a["us10"] - a["us2"]) * 100})
    abd = [o for o in b05.OLAYLAR_ABD if not o.get("alt") and "moodys" not in o["kimlik"]]
    dm_birim = SERI_BIRIM["dm"]
    sat = _pencere_vakalari("butce", L, abd, lambda g: gun_rejimi(g, "dm"), "ölçülen hafta etiketi (ABD)",
                            dm_birim, "ABD")
    # İngiltere 2022 (gilt Londra kapanışı, sterlin New York 17:00)
    igb_sebep = None
    try:
        g = bulut.gilt()
        k = oo.cnbc_kur()["gbp"]
        f = pd.concat([g[["gb2y", "gb10y", "gb30y"]], np.log(k).rename("lgbp")], axis=1, sort=True).dropna()
        f = f[f.index.dayofweek < 5]
        Lg = pd.DataFrame({"kur": f["lgbp"] * 100, "2y": f["gb2y"] * 100, "uzun": f["gb10y"] * 100,
                           "egim": (f["gb10y"] - f["gb2y"]) * 100})
        igb = [o for o in b05.OLAYLAR_IGB if not o.get("alt")]
        sat += _pencere_vakalari("butce", Lg, igb, _vix_etiketi("R5_DM", "R2"), "VIX ölçütü + olay seçimi (tuzak 5)",
                                 {"kur": "sterlin, log %", "2y": "gilt 2 yıllık, bp", "uzun": "gilt 10 yıllık, bp",
                                  "egim": "10 yıllık − 2 yıllık, bp"}, "İngiltere")
    except bulut.VeriYok as e:
        igb_sebep = f"İngiltere penceresi kurulmadı: {e}"
    dm = _pencere_hucreleri("butce", sat, TARAF_SUTUN["dm"], dm_birim,
                            "ABD satırları ölçülen hafta etiketiyle; İngiltere satırı VIX ölçütü ve olay seçimiyle "
                            "sütuna yazıldı. ABD 2023 Ağustos penceresi Fitch'in tepki gününü de taşır.")
    # EM: euro çevresi pencereleri (Bölüm 6; günlük olanlar)
    cev, _ = b06.cevre_gunluk()
    e = oo.cnbc_kur()["eur"]
    em_sat = []
    for o in b06.OLAYLAR_AVRUPA:
        if o["kaynak"] != "cnbc_gunluk":
            continue
        u = o["ulke"].lower()
        kol = {"uzun": cev[f"_{u}10y"]}
        if f"_{u}2y" in cev.columns:
            kol["2y"] = cev[f"_{u}2y"]
        f = pd.concat([np.log(e).rename("leur")] + [v.rename(k) for k, v in kol.items()], axis=1, sort=True).dropna()
        f = f[f.index.dayofweek < 5]
        Le = pd.DataFrame({"kur": f["leur"] * 100, "uzun": f["uzun"] * 100}, index=f.index)
        if "2y" in f:
            Le["2y"] = f["2y"] * 100
            Le["egim"] = (f["uzun"] - f["2y"]) * 100
        em_sat += _pencere_vakalari("butce", Le, [o], _vix_etiketi("R5_EM", "R4"), "VIX ölçütü + olay seçimi (tuzak 5)",
                                    {"kur": "euro, log %", "2y": f"{o['ulke']} 2 yıllık, bp" if "2y" in f else None,
                                     "uzun": f"{o['ulke']} 10 yıllık, bp",
                                     "egim": "10 yıllık − 2 yıllık, bp" if "2y" in f else None}, o["ulke"])
    em = _pencere_hucreleri("butce", em_sat, TARAF_SUTUN["em"],
                            {"kur": "euro, log %", "2y": "ülke 2 yıllık, bp (yalnız İtalya)",
                             "uzun": "ülke 10 yıllık, bp", "egim": "10 yıllık − 2 yıllık, bp (yalnız İtalya)"},
                            "Euro çevresinin kendi rejim etiketi yok: VIX ölçütünü geçmeyen mali stres penceresi "
                            "R4 sütununa yazıldı (olay seçimi). Kur bacağı ortak para eurodur; getiriler Avrupa "
                            "kapanışı, euro New York 17:00. Yunanistan penceresi yalnız aylık farkla ölçüldüğü için "
                            "hücreye girmedi.")
    for col in ("R3",):
        if em[col]["n"] == 0:
            em[col]["not"] = ("EM bütçe olayı olarak yalnız euro çevresinin mali stres pencereleri var; güvenilir "
                              "merkez bankası rejiminde bütçe olayı kurulmadı")
    hucre = {**dm, **em}
    meta = {"dm_pencereleri": [o["kimlik"] for o in abd] + [o["kimlik"] for o in b05.OLAYLAR_IGB if not o.get("alt")],
            "em_pencereleri": [o["kimlik"] for o in b06.OLAYLAR_AVRUPA if o["kaynak"] == "cnbc_gunluk"],
            "disarida": {"abd_2025_moodys_1g": "not kararı satırında (tuzak 6)",
                         "yunanistan_2010_2012": "yalnız aylık fark; günlük seri 2014'te başlıyor"},
            "kaynak": KAYNAK_DM + ["cnbc_avrupa_getiri_gunluk", "bulut: gilt"]}
    if igb_sebep:
        meta["igb"] = igb_sebep
    return hucre, meta


def _sok_gsyh() -> tuple[dict, dict]:
    hucre, meta = {}, {}
    try:
        g = pd.DatetimeIndex(bulut.gsyh_gunleri()).normalize()
    except bulut.VeriYok as e:
        for col in TARAF_SUTUN["em"]:
            hucre[col] = _bos_hucre("gsyh", col, f"TÜİK GSYH yayım günleri elde yok ({e})")
        g = None
    if g is not None:
        p3d = b03.p3d()["tr_gsyh"]["kapi"]
        F = _em_gunluk()
        kap = {"2y": _kapi_hazir(p3d["n2y"], "Bölüm 3, GSYH yayım günü kapısı"),
               "uzun": _kapi_hazir(p3d["n5y"], "Bölüm 3, GSYH yayım günü kapısı"),
               "kur": _kapi_hazir(p3d["usdtry"], "Bölüm 3, GSYH yayım günü kapısı"),
               "egim": _kapi_yeni(F["egim"], g, False, 1)}
        reg, reg_o = gun_rejimi(F.index, "em"), gun_rejimi(F.index, "em", onceki=True)
        h, m = _olay_hucreleri("gsyh", F, g, "em", kap, reg, reg_o, SERI_BIRIM["em"], "yayım günü (10:00 TSİ)")
        hucre.update(h)
        meta = {"kapi_em": kap, **m, "n_yayim": int(len(g)), "kaynak": KAYNAK_EM + ["bulut: tuik_takvim"]}
    for col in TARAF_SUTUN["dm"]:
        hucre[col] = _bos_hucre("gsyh", col, "ABD ISM/PMI ve GSYH yayım takvimi arşivde yok")
    return hucre, meta


def _sok_istihdam() -> tuple[dict, dict]:
    hucre = {}
    try:
        bulut.abd_istihdam_gunleri()
        sebep = None
    except bulut.VeriYok as e:
        sebep = f"ABD istihdam raporu yayım günleri elde yok ({e})"
    for col in TARAF_SUTUN["dm"]:
        hucre[col] = _bos_hucre("istihdam", col, sebep or "kurulmadı")
    for col in TARAF_SUTUN["em"]:
        hucre[col] = _bos_hucre("istihdam", col, "Türkiye işgücü istatistiklerinin yayım takvimi arşivde yok")
    return hucre, {"kaynak": ["bulut: bls_takvim"]}


def _tufe_olaylari(F: pd.DataFrame) -> pd.DatetimeIndex:
    """Bölüm 4'ün yayım günü kümesi: sürpriz serisinde ayı olan yayımlar (eşleme benzersiz)."""
    sp = b04.surpriz_serisi()
    g = pd.DatetimeIndex(bulut.tufe_gunleri())
    es = pd.Series(g.to_period("M") - 1, index=g)
    es = es[es.isin(sp.index)]
    return es.index.intersection(F.index)


def _sok_tufe() -> tuple[dict, dict]:
    hucre, meta = {}, {}
    F = _em_gunluk()
    try:
        g = bulut.tufe_gunleri()
    except bulut.VeriYok as e:
        g = None
        for col in TARAF_SUTUN["em"]:
            hucre[col] = _bos_hucre("tufe", col, f"TÜİK TÜFE yayım günleri elde yok ({e})")
    if g is not None:
        olay = _tufe_olaylari(F)
        kb = b04.tufe_gunu_tepkisi(g)["kapi"]
        kap = {"2y": _kapi_hazir(kb["n2y"], "Bölüm 4, TÜFE yayım günü kapısı"),
               "uzun": _kapi_hazir(kb["n5y"], "Bölüm 4, TÜFE yayım günü kapısı"),
               "kur": _kapi_hazir(kb["usdtry"], "Bölüm 4, TÜFE yayım günü kapısı"),
               "egim": _kapi_yeni(F["egim"], olay, False, 2)}
        reg, reg_o = gun_rejimi(F.index, "em"), gun_rejimi(F.index, "em", onceki=True)
        h, m = _olay_hucreleri("tufe", F, olay, "em", kap, reg, reg_o, SERI_BIRIM["em"], "yayım günü (10:00 TSİ)")
        hucre.update(h)
        meta = {"kapi_em": kap, **m, "kaynak": KAYNAK_EM + ["bulut: tuik_takvim", "enflasyon_aylik"]}
    try:
        bulut.abd_tufe_gunleri()
        sebep = None
    except bulut.VeriYok as e:
        sebep = f"ABD TÜFE yayım günleri elde yok ({e})"
    for col in TARAF_SUTUN["dm"]:
        hucre[col] = _bos_hucre("tufe", col, sebep or "kurulmadı")
    return hucre, meta


def _sok_para() -> tuple[dict, dict]:
    # Türkiye: PPK (Bölüm 3'ün kapısı; 111 karar)
    Fe = _em_gunluk()
    ppk = pd.DatetimeIndex(oo.oku("ppk_kararlari").index).normalize()
    kb = b03.p3b()["kapi"]
    kap_em = {"2y": _kapi_hazir(kb["n2y"], "Bölüm 3, PPK kapısı"), "uzun": _kapi_hazir(kb["n5y"], "Bölüm 3, PPK kapısı"),
              "kur": _kapi_hazir(kb["usdtry"], "Bölüm 3, PPK kapısı"), "egim": _kapi_yeni(Fe["egim"], ppk, False, 3)}
    reg, reg_o = gun_rejimi(Fe.index, "em"), gun_rejimi(Fe.index, "em", onceki=True)
    he, me = _olay_hucreleri("para", Fe, ppk, "em", kap_em, reg, reg_o, SERI_BIRIM["em"], "karar günü (14:00 TSİ)")
    # ABD: planlı FOMC (Bölüm 2'nin kapısı)
    Fd = _dm_gunluk()
    try:
        fomc = pd.DatetimeIndex(bulut.fomc_gunleri(planli=True)).normalize()
        kap_dm = {"2y": _b02_kapi("us2", "fomc", "Bölüm 2, FOMC kapısı"),
                  "kur": _b02_kapi("dolar_sepeti", "fomc", "Bölüm 2, FOMC kapısı"),
                  "uzun": _kapi_yeni(Fd["uzun"], fomc, False, 4), "egim": _kapi_yeni(Fd["egim"], fomc, False, 5)}
        rd, rd_o = gun_rejimi(Fd.index, "dm"), gun_rejimi(Fd.index, "dm", onceki=True)
        hd, md = _olay_hucreleri("para", Fd, fomc, "dm", kap_dm, rd, rd_o, SERI_BIRIM["dm"],
                                 "karar günü (14:00 New York)")
    except bulut.VeriYok as e:
        hd = {col: _bos_hucre("para", col, f"FOMC takvimi elde yok ({e})") for col in TARAF_SUTUN["dm"]}
        md, kap_dm = {}, {}
    return {**hd, **he}, {"kapi_em": kap_em, "kapi_dm": kap_dm, "em": me, "dm": md,
                          "olay": {"em": "PPK karar günleri (111)", "dm": "planlı FOMC kararları"},
                          "kaynak": KAYNAK_EM + KAYNAK_DM + ["ppk_kararlari", "bulut: fomc_takvim"]}


def _sok_cari() -> tuple[dict, dict]:
    hucre = {}
    for col in TARAF_SUTUN["em"]:
        hucre[col] = _bos_hucre("cari", col, "TCMB ödemeler dengesi yayım günleri arşivde yok: olay günü kurulamaz; "
                                             "aylık ilişki Bölüm 8'dedir (yön kurdan cari dengeye)")
    for col in TARAF_SUTUN["dm"]:
        hucre[col] = _bos_hucre("cari", col, "DM cari denge yayım takvimi arşivde yok")
    return hucre, {"aylik_iliski": "Bölüm 8 (REDK sapması → sonraki 12 ayın cari dengesi; J-eğrisi)"}


def _sok_rezerv() -> tuple[dict, dict]:
    F = _em_haftalik()
    k = b09.emp_bilesenleri()["rezerv"]
    ev = k.index[k.abs() >= REZERV_SOK_SIGMA]
    kap = {c: _kapi_yeni(F[c], ev, c == "kur", 10 + i, "hafta") for i, c in enumerate(SERILER)}
    reg, reg_o = hafta_rejimi(F.index, "em"), hafta_rejimi(F.index, "em", onceki=True)
    h, m = _olay_hucreleri("rezerv", F, ev, "em", kap, reg, reg_o,
                           {"kur": "USD/TRY haftalık, log %", "2y": "DİBS 2 yıllık haftalık, bp",
                            "uzun": "DİBS 5 yıllık haftalık, bp", "egim": "5 yıllık − 2 yıllık haftalık, bp"},
                           "rezervin büyük oynadığı hafta (aynı hafta; ±2 hafta)")
    for col in TARAF_SUTUN["dm"]:
        h[col] = _bos_hucre("rezerv", col, "DM haftalık rezerv serisi arşivde yok")
    # Eşik duyarlılığı yalnız OLAY SAYISIDIR: kapıyı geçmeyen seride eş hareket ya da oran
    # (havuzda bile) yazılmaz.
    duy = {f"esik_{e:g}_sigma": int(len(k.index[k.abs() >= e])) for e in sorted(REZERV_DUYARLILIK + (REZERV_SOK_SIGMA,))}
    kayip = int((k.loc[ev] > 0).sum())
    return h, {"kapi_em": kap, **m, "n_olay_haftasi": int(len(ev)), "rezerv_kaybi_haftasi": kayip,
               "rezerv_artisi_haftasi": int(len(ev) - kayip), "esik_sigma": REZERV_SOK_SIGMA,
               "esik_duyarliligi_hafta_sayisi": duy,
               "olcu": "swap hariç net rezervin haftalık değişimi, brüt rezerve oranla, kendi standart sapmasıyla "
                       "(Bölüm 9'un kur baskısı bileşeni; artı = rezerv kaybı)",
               "kaynak": ["rezerv_haftalik", "dibs_egri_gunluk", "usdtry_yahoo_gunluk", "fonlama_gunluk"]}


def _sok_not() -> tuple[dict, dict]:
    a = oo.abd_gunluk()
    L = pd.DataFrame({"kur": a["sepet"] * 100, "2y": a["us2"] * 100, "uzun": a["us10"] * 100,
                      "egim": (a["us10"] - a["us2"]) * 100})
    ol = [{"kimlik": f"{k['kurum'].lower().replace(chr(39), '')}_{k['karar_gunu']}", "ad": k["ad"],
           "baslangic": k["karar_gunu"], "bitis": k["tepki_gunu"]} for k in b12.DM_KARARLARI]
    sat = _pencere_vakalari("not", L, ol, lambda g: gun_rejimi(g, "dm"), "ölçülen hafta etiketi (ABD)",
                            SERI_BIRIM["dm"], "ABD")
    h = _pencere_hucreleri("not", sat, TARAF_SUTUN["dm"], SERI_BIRIM["dm"],
                           "Karar New York kapanışından sonra; pencere karar günü kapanışından tepki günü kapanışına. "
                           "Fitch'in tepki günü ABD Hazinesi'nin üç aylık borçlanma açıklamasını da taşır.")
    try:
        bulut.not_kararlari()
        p = b12.p12()
        kk = p["plasebo_kapisi"]
        gecen = [ad for ad in kk if kk[ad].get("gecti")]
        if gecen:
            sebep, tur = (f"Bölüm 12'de {', '.join(gecen)} için olay çalışması kuruldu ({p['n']} karar); rejim "
                          "ayrımı için karar sayısı yetmiyor"), "olay_az"
        else:
            sebep, tur = (f"kapı: Türkiye not kararlarında ({p['n']} karar, Bölüm 12) tepki günü hareketi komşu "
                          "günlerden ayrışmıyor — " + "; ".join(
                              f"{'kur' if ad == 'kur' else '5 yıllık'}: {kk[ad].get('sebep', '')}" for ad in kk)), "plasebo"
    except bulut.VeriYok as e:
        sebep, tur = f"Türkiye kredi notu kararlarının tarih listesi gelmedi ({e})", "veri_yok"
    for col in TARAF_SUTUN["em"]:
        h[col] = _bos_hucre("not", col, sebep, tur)
    return h, {"dm_kararlari": [o["kimlik"] for o in ol], "kaynak": KAYNAK_DM + ["bulut: not_kararlari"]}


@lru_cache(maxsize=1)
def _enerji_soklari() -> tuple[pd.DatetimeIndex, float]:
    de = b10._emtia()["enerji"].diff().loc[b10.BAS:b10.SON].dropna()
    sig = float(de.std())
    return pd.DatetimeIndex(de.index[de.abs() >= ENERJI_SOK_SIGMA * sig]), sig


def _sok_emtia() -> tuple[dict, dict]:
    ev, sig = _enerji_soklari()
    out, meta = {}, {"sigma_enerji_log_yuzde": sig, "esik_sigma": ENERJI_SOK_SIGMA, "n_sok_ayi": int(len(ev)),
                     "artis_ayi": int((b10._emtia()["enerji"].diff().reindex(ev) > 0).sum()),
                     "kaynak": ["kuresel_aylik (Dünya Bankası Pink Sheet enerji)"] + KAYNAK_DM + KAYNAK_EM}
    for taraf, F, tb in (("dm", _dm_aylik(), 20), ("em", _em_aylik(), 30)):
        kap = {c: _kapi_yeni(F[c], ev, taraf == "em" and c == "kur", tb + i, "ay") for i, c in enumerate(SERILER)}
        reg, reg_o = ay_rejimi(F.index, taraf), ay_rejimi(F.index, taraf, onceki=True)
        birim = {"kur": SERI_BIRIM[taraf]["kur"].replace("log %", "aylık log %"),
                 **{c: SERI_BIRIM[taraf][c].replace("bp", "aylık bp") for c in ("2y", "uzun", "egim")}}
        h, m = _olay_hucreleri("emtia", F, ev, taraf, kap, reg, reg_o, birim,
                               "şok ayı (ay sonu kur ve getiri; enerji aylık ortalama; ±2 ay)")
        out.update(h)
        meta[f"kapi_{taraf}"] = kap
        meta[taraf] = m
    meta["ay_rejimi"] = "ayın etiketi, örnek günü o ayda olan haftaların çoğunluk etiketi (eşitlikte şiddetlisi)"
    return out, meta


@lru_cache(maxsize=1)
def _vix_gunleri() -> tuple[pd.DatetimeIndex, float]:
    v = oo.oku("yahoo_dxy_vix_gunluk")["vix"].dropna()
    v = v[(v.index.dayofweek < 5) & (v.index <= oo.CIPA_GUN)]
    dv = v.diff().loc[VIX_ILK:].dropna()
    esik = float(dv.quantile(1 - VIX_UST_PAY))
    return pd.DatetimeIndex(dv.index[dv >= esik]), esik


def _sok_kuresel() -> tuple[dict, dict]:
    ev, esik = _vix_gunleri()
    out, meta = {}, {"esik_vix_puan": esik, "ust_pay": VIX_UST_PAY, "n_gun": int(len(ev)),
                     "ilk": _iso(ev.min()), "son": _iso(ev.max()),
                     "saat": "VIX New York kapanışı (23:15 TSİ). DİBS gün sonu hizasında D'nin değeri D+1 sabahının "
                             "sabitlemesidir ve ABD seansını içerir; USD/TRY 18.12.2023'e kadar Londra gece yarısı "
                             "(ABD seansını içerir), sonra İstanbul 18:00 (ABD öğleden sonrasını içermez).",
                     "kaynak": ["yahoo_dxy_vix_gunluk"] + KAYNAK_DM + KAYNAK_EM}
    for taraf, F, tb in (("dm", _dm_gunluk(), 40), ("em", _em_gunluk(), 50)):
        kap = {c: _kapi_yeni(F[c], ev, taraf == "em" and c == "kur", tb + i) for i, c in enumerate(SERILER)}
        reg, reg_o = gun_rejimi(F.index, taraf), gun_rejimi(F.index, taraf, onceki=True)
        h, m = _olay_hucreleri("kuresel", F, ev, taraf, kap, reg, reg_o, SERI_BIRIM[taraf],
                               "VIX sıçraması günü (ABD tarihi)")
        out.update(h)
        meta[f"kapi_{taraf}"] = kap
        meta[taraf] = m
    return out, meta


# ═══════════════════════════════════════════════════════════════ matris ve şekil
@lru_cache(maxsize=1)
def _matris() -> tuple[dict, dict]:
    kur = {"butce": _sok_butce, "gsyh": _sok_gsyh, "istihdam": _sok_istihdam, "tufe": _sok_tufe,
           "para": _sok_para, "cari": _sok_cari, "rezerv": _sok_rezerv, "not": _sok_not,
           "emtia": _sok_emtia, "kuresel": _sok_kuresel}
    mat, meta = {}, {}
    for s, _ad in SOKLAR:
        h, m = kur[s]()
        mat[s] = {col: h[col] for col in SUTUN_KIM}
        meta[s] = m
    return mat, meta


def _desen(h: dict) -> str:
    d = h["durum"]
    if d == "olculdu":
        return "olculdu" if isinstance(h.get("es_hareket"), float) else "olculdu_es_hareket_yok"
    return d


def _vaka_imza(h: dict) -> float | None:
    """Vaka hücresinde kadran dengesi: (B − C) / vaka sayısı, 2 yıllık × para değeri (test değil)."""
    if h["durum"] != "vaka":
        return None
    k = []
    for v in h.get("vakalar") or []:
        kd = v[3] if isinstance(v, list) else v.get("kadran_2y")
        if kd in ("politika", "gevseme"):
            k.append(1)
        elif kd in ("prim", "guvenli_liman", "prim_dusus"):
            k.append(-1)
    return float(np.mean(k)) if k else None


def sekil_21(mat: dict) -> dict:
    sat = [s for s, _ in SOKLAR]
    return {
        "satirlar": sat, "satir_ad": [a for _, a in SOKLAR],
        "sutunlar": list(SUTUN_KIM), "sutun_ad": [a for _, a, _ in SUTUNLAR],
        "durum": [[mat[s][c]["durum"] for c in SUTUN_KIM] for s in sat],
        "desen": [[_desen(mat[s][c]) for c in SUTUN_KIM] for s in sat],
        "es_hareket": [[mat[s][c]["es_hareket"] if isinstance(mat[s][c].get("es_hareket"), float) else None
                        for c in SUTUN_KIM] for s in sat],
        "b_payi": [[mat[s][c].get("b_payi") for c in SUTUN_KIM] for s in sat],
        "vaka_imza": [[_vaka_imza(mat[s][c]) for c in SUTUN_KIM] for s in sat],
        "n": [[mat[s][c]["n"] for c in SUTUN_KIM] for s in sat],
        "oran_2y": [[(mat[s][c].get("oranlar") or {}).get("2y") if isinstance((mat[s][c].get("oranlar") or {}).get("2y"), float)
                     else None for c in SUTUN_KIM] for s in sat],
        "oran_kur": [[(mat[s][c].get("oranlar") or {}).get("kur") if isinstance((mat[s][c].get("oranlar") or {}).get("kur"), float)
                      else None for c in SUTUN_KIM] for s in sat],
        "renk_olcegi": "eş hareket korelasyonu −1 … +1: artı, 2 yıllık faiz ile yerel paranın değeri aynı yönde "
                       "(B terimi: faiz ↑ para ↑); eksi, ters yönde (C terimi: faiz ↑ para ↓)",
        "desen_kodlari": {"olculdu": "renkli (korelasyon)", "olculdu_es_hareket_yok": "ölçüldü ama eş hareket kapıdan "
                          "dönmüş: renksiz çerçeve, oranlar yazılı", "vaka": "noktalı (vaka imzası: kadran dengesi, test "
                          "değil)", "kaynak": "taralı", "kurulmadi": "boş"},
        "n_satir": len(sat), "n_sutun": len(SUTUN_KIM),
        "yontem": "Her hücrenin rengi olay günlerinde 2 yıllık getiri değişimi ile yerel paranın değer değişimi "
                  "arasındaki korelasyon, deseni hücrenin durumudur.",
        "kaynak": KAYNAK_DM + KAYNAK_EM,
    }


def _matris_ozeti(mat: dict) -> dict:
    say = {}
    for s in mat:
        for c in mat[s]:
            d = mat[s][c]["durum"]
            say[d] = say.get(d, 0) + 1
    olc = [[s, c] for s in mat for c in SUTUN_KIM if mat[s][c]["durum"] == "olculdu"]
    sebep = {}
    for s in mat:
        for c in mat[s]:
            h = mat[s][c]
            if h["durum"] in ("kaynak", "kurulmadi"):
                d = sebep.setdefault(h["durum"], {})
                t = h.get("sebep_turu") or "belirsiz"
                d[t] = d.get(t, 0) + 1
    kaynak_plasebo = [[s, c] for s in mat for c in SUTUN_KIM
                      if mat[s][c]["durum"] == "kaynak" and mat[s][c].get("sebep_turu") == "plasebo"]
    return {"hucre": len(mat) * len(SUTUN_KIM), "durum_sayisi": dict(sorted(say.items())), "olculen_hucreler": olc,
            "sebep_sayisi": {d: dict(sorted(v.items())) for d, v in sorted(sebep.items())},
            "kaynak_plasebo_hucreleri": kaynak_plasebo}


# ═══════════════════════════════════════════════════════════════ teşhis örneği
def _yuzdelik(gecmis: pd.Series, x: float) -> float | None:
    g = gecmis.dropna()
    return float((g <= x).mean()) if len(g) else None


def teshis_ornegi() -> dict:
    r = b01.rejim()
    tam = r[~r["kismi"].astype(bool)]
    cip = r[r["kismi"].astype(bool)]
    tr_h, ab_h = b01._tr_haftalik(), b01._abd_haftalik()
    a = oo.abd_gunluk()
    dxy_h = a["dxy"][a.index.dayofweek <= 4].resample("W-FRI").last()
    vix = oo.oku("yahoo_dxy_vix_gunluk")["vix"].dropna()
    vix = vix[(vix.index.dayofweek < 5) & (vix.index <= oo.CIPA_GUN)]
    vw = vix.resample("W-FRI").last().dropna()

    def hafta(etiket, kismi: bool) -> dict:
        z = r.loc[etiket]
        t, b = tr_h.loc[etiket], ab_h.loc[etiket]
        tr_g, ab_g = pd.Timestamp(z["tr_gun"]), pd.Timestamp(z["abd_gun"])
        onceki = dxy_h.index[dxy_h.index < etiket].max()
        out = {
            "hafta": _iso(etiket), "yarim_hafta": bool(kismi),
            "tr": {"etiket": z["tr"], "ornek_gunu": _iso(tr_g), "d2y_bp": _f(t["d2_bp"]), "d5y_bp": _f(t["d5_bp"]),
                   "degim_bp": _f(t["degim_bp"]), "dkur_yuzde": _f(t["dkur_yuzde"]),
                   "kur_sapma_yuzde": _f(t["kur_sapma_yuzde"]),
                   "kadran_5y": oo.kadran(float(t["d5_bp"]), float(-t["dkur_yuzde"]), "prim_dusus"),
                   "kadran_2y": oo.kadran(float(t["d2_bp"]), float(-t["dkur_yuzde"]), "prim_dusus"),
                   "kadran_etiket": z["tr_kadran"],
                   "kur_esik_yuzde": _f(b01.KUR_SAPMA_SD * z["tr_sd_para_yuzde"]),
                   "diklesme_esik_bp": _f(b01.DIKLESME_SD * z["tr_sd_egim_bp"]),
                   "vix": _f(z["tr_vix"]), "yonetilen": bool(z["tr_yonetilen"])},
            "abd": {"etiket": z["abd"], "ornek_gunu": _iso(ab_g), "d2y_bp": _f(b["d2_bp"]), "d10y_bp": _f(b["d10_bp"]),
                    "degim_bp": _f(b["degim_bp"]), "ddolar_sepet_yuzde": _f(b["ddolar_yuzde"]),
                    "dolar_sapma_yuzde": _f(b["dolar_sapma_yuzde"]),
                    "ddxy_yuzde": _f((dxy_h.loc[etiket] - dxy_h.loc[onceki]) * 100),
                    "kadran_10y": oo.kadran(float(b["d10_bp"]), float(b["ddolar_yuzde"]), "guvenli_liman"),
                    "kadran_2y": oo.kadran(float(b["d2_bp"]), float(b["ddolar_yuzde"]), "guvenli_liman"),
                    "kadran_etiket": z["abd_kadran"], "vix": _f(z["abd_vix"])},
            "vix_esik_r5": _f(z["vix_esik"]),
        }
        return out

    son_tam = tam.dropna(subset=["abd", "tr"]).index.max()
    v0 = float(vix.loc[oo.CIPA_GUN])
    cipa_etiketi = cip.index.max() if len(cip) else vw.index.max()
    gecmis_haftalik = vw[vw.index < cipa_etiketi]          # R5 kuralı: bir önceki haftaya kadar
    adim1 = _adim1()
    out = {
        "cipa_gunu": _iso(oo.CIPA_GUN),
        "adim1_beklenti": adim1,
        "son_tam_hafta": hafta(son_tam, False),
        "cipa_haftasi": hafta(cip.index.max(), True) if len(cip) else None,
        "vix_cipa_gunu": {"seviye": _f(v0),
                          "genisleyen_yuzdelik_haftalik": _yuzdelik(gecmis_haftalik, v0),
                          "genisleyen_yuzdelik_gunluk": _yuzdelik(vix[vix.index < oo.CIPA_GUN], v0),
                          "r5_esigi": _f(cip["vix_esik"].iloc[-1]) if len(cip) else _f(tam["vix_esik"].iloc[-1]),
                          "gecmis_ilk": _iso(vix.index.min()),
                          "not": "Haftalık yüzdelik Bölüm 1'in R5 kuralıyla aynı geçmişten (1990'dan bir önceki "
                                 "haftaya kadar haftalık kapanışlar); günlük yüzdelik çıpa gününden önceki bütün "
                                 "günlük kapanışlardan."},
        "dolar_olcusu": "Birincil dolar ölçüsü CNBC G10 sepetidir: Yahoo DXY barının gövde/aralık sınaması bu "
                        "arşivden kurulamadı (yalnız kapanış var); DXY yanında yazılıdır.",
        "yontem": "Çıpa gününün teşhis girdileri: son tam haftanın ve yarım çıpa haftasının rejim etiketi, haftalık "
                  "faiz ve kur değişimleri ve kadranları, VIX düzeyi ve genişleyen yüzdeliği, dolar sepetinin "
                  "haftalık değişimi.",
        "kaynak": KAYNAK_DM + KAYNAK_EM + ["ppk_kararlari", "bulut: tuik_takvim", "bulut: fomc_takvim",
                                          "enflasyon_aylik", "rezerv_haftalik"],
        "n": 2, "ilk": _iso(son_tam), "son": _iso(oo.CIPA_GUN),
    }
    return out


def _adim1() -> dict:
    """Adım 1 — sayısal beklenti var mı: arşivdeki olay türlerinin çıpa gününe en yakın geçmiş
    kaydı ve beklentisi olan tek yayım (TÜFE; Piyasa Katılımcıları Anketi)."""
    c = oo.CIPA_GUN
    son = {}
    ppk = pd.DatetimeIndex(oo.oku("ppk_kararlari").index)
    son["ppk"] = {"son": _iso(ppk[ppk <= c].max()), "beklenti": "anketin toplantı beklentisi (Bölüm 3)"}
    for ad, f, bek in (("tufe", bulut.tufe_gunleri, "PKA cari ay beklentisi (sürpriz yalnız burada)"),
                       ("gsyh", bulut.gsyh_gunleri, "sayısal beklenti yok"),
                       ("fomc", lambda: bulut.fomc_gunleri(planli=True), "sayısal beklenti yok")):
        try:
            g = pd.DatetimeIndex(f())
            son[ad] = {"son": _iso(g[g <= c].max()), "sonraki_arsivde": _iso(g[g > c].min()) if (g > c).any() else None,
                       "beklenti": bek}
        except bulut.VeriYok as e:
            son[ad] = kurulmadi(str(e))
    ev, _ = _vix_gunleri()
    son["vix_sicramasi"] = {"son": _iso(ev[ev <= c].max())}
    k = b09.emp_bilesenleri()["rezerv"]
    er = k.index[k.abs() >= REZERV_SOK_SIGMA]
    son["rezerv_sok_haftasi"] = {"son": _iso(er.max()), "son_hafta_bileseni_sigma": _f(k.iloc[-1]),
                                 "son_hafta": _iso(k.index[-1])}
    try:
        p = bulut.pka_enflasyon()
        p_son = p.dropna(subset=["ay1"]).index.max()
        sp = b04.surpriz_serisi()
        son_ay = sp.index.max()
        tufe_bek = {"anket_donemi": str(pd.Timestamp(p_son).to_period("M")), "bir_ay_sonrasi_aylik_tufe_yuzde":
                    _f(p.loc[p_son, "ay1"]), "kapsadigi_ay": str(pd.Timestamp(p_son).to_period("M") + 1),
                    "son_surpriz_ayi": str(son_ay), "son_surpriz_puan": _f(sp.loc[son_ay, "surpriz"]),
                    "not": "Sıradaki TÜFE ayının anketi aylık çıpanın dışında; arşivdeki son sayısal beklenti bir "
                           "önceki anketin bir ay sonrası sorusudur."}
    except (bulut.VeriYok, KeyError) as e:
        tufe_bek = kurulmadi(f"anket beklentisi elde yok ({e})")
    return {"son_olaylar": son, "tufe_beklentisi": tufe_bek,
            "kural": "Sayısal beklentisi olan tek yayım Türkiye TÜFE'sidir; öbürlerinde yalnız olay günü oynaklığı "
                     "ve eş hareket okunur."}


# ═══════════════════════════════════════════════════════════════ kart kanıtları
def _dugum(kok: dict, yol: list):
    x = kok
    for p in yol:
        if isinstance(x, dict) and p in x:
            x = x[p]
        elif isinstance(x, list) and isinstance(p, int) and -len(x) <= p < len(x):
            x = x[p]
        else:
            raise KeyError(".".join(map(str, yol)))
    return x


def _guc_es(d) -> str | None:
    """Matris hücresinde eş hareketin gücü: korelasyon örneklem dışı sınanmadığı için en çok
    tarif edicidir; olay ile sıradan gün farkı |z| ≥ 2 ise bu ayrıca söylenir."""
    if not isinstance(d, dict) or "es_hareket" not in d:
        return None
    e = d.get("es_hareket")
    if isinstance(e, float):
        z = d.get("es_fark_z")
        return "tarif edici (sıradan günden ayrışıyor)" if z is not None and abs(z) >= 2 else "tarif edici"
    if e == "kurulmadı (kapı)":
        return "kurulmadı (kapı)"
    return "vaka" if d.get("durum") == "vaka" else None


def _guc(d) -> str:
    """Kanıtın gücü, düğümün KENDİ alanlarından: ölçüldü · tarif edici · vaka · kaynak · kurulmadı.
    Hüküm dizgesi ("ölçülü" · "tarif edici") doğrudan okunur; olay satırları listesi vakadır."""
    if isinstance(d, str):
        return "ölçüldü" if d == "ölçülü" else "tarif edici"
    if isinstance(d, list):
        return "vaka"
    if not isinstance(d, dict):
        return "tarif edici"
    if d.get("vaka_tablosu") is True or "vaka" in str(d.get("tur", "")):
        return "vaka"
    du = str(d.get("durum", ""))
    if du == "kurulmadi":
        return "kurulmadı"
    if du == "kaynak":
        return "kaynak"
    if "vaka" in du:
        return "vaka"
    if du == "olculdu":
        return "ölçüldü"        # oranın kapısı (gün eşlemeli rastgele kümeler) geçti; eş hareket ayrı (`guc_es`)
    if "hukum" in d:
        return "ölçüldü" if d["hukum"] == "ölçülü" else "tarif edici"
    if "gecti" in d:
        return "ölçüldü" if d["gecti"] else "kurulmadı (kapı)"
    return "tarif edici"


def _not_eksik(p: dict) -> str:
    """Not kararı kartının eksik satırı, Bölüm 12'nin ölçümünden (karar sayısı ve kapı hükmü)."""
    if p.get("durum") == "kurulmadi":
        return f"Türkiye not kararlarının olay çalışması kurulmadı: {p.get('sebep', '')}; CDS serisi yok."
    kk = p.get("plasebo_kapisi", {})
    gecen = [("kur" if ad == "kur" else "5 yıllık") for ad in kk if kk[ad].get("gecti")]
    dis = len(p.get("gunu_kaynakta_olmayan") or [])
    gun = (f"; {dis} kararın günü kaynakta yazmıyor, ertesi günün haberinden ya da kurumun takviminden çıkarıldı"
           if dis else "")
    if gecen:
        return (f"Türkiye not kararlarında (Bölüm 12, {p['n']} karar{gun}) plasebo sınamasını yalnız "
                f"{', '.join(gecen)} geçti; rejim ayrımı için karar sayısı yetmiyor; CDS serisi yok.")
    return (f"Türkiye not kararlarında (Bölüm 12, {p['n']} karar{gun}) tepki günü hareketi plasebo sınamasını "
            "geçmedi: kararlar vaka listesidir; CDS serisi yok.")


def kart_kanit(mat: dict, meta: dict) -> list:
    """Veri günü kartlarının (içindekiler tablosu) kanıt yolları. Yol ölçüm dosyasındaki anahtar
    zinciridir (`bNN.anahtar…`); güç, yolun gösterdiği düğümün kendi durum/hüküm alanından türer."""
    # Bölüm 2'nin tam çıktısı (p2) ~10 sn sürer; kapı satırları önbellekli tablodan okunur ve
    # özetin "kurulabilir" listesi aynı kuralla kurulur (yol ayrıca yazılmış dosyada sınanır).
    b02_kur = [f"{r['seri']}×{r['olay']}" for r in b02._tablo()[0] if r.get("kurulabilir")]
    kaynaklar = {
        "b02": {"p2": {"kapi_ozet": {"kurulabilir": b02_kur}}},
        "b03": {"p3b": b03.p3b(), "p3d": b03.p3d()},
        "b04": {"p4a": b04.p4a(), "p4b": b04.p4b(), "p4c": b04.p4c()},
        "b05": {"p5a": b05.p5a(), "sekil_07": b05.sekil_07()},
        "b06": {"p6c": b06.p6c(), "p6d": b06.p6d()},
        "b08": {"p8b": b08.p8b(), "p8c": b08.p8c(), "p8d": b08.p8d()},
        "b09": {"p9a": b09.p9a(), "p9b": b09.p9b()},
        "b12": {"p12_dm": b12.p12_dm(), "p12": b12.p12(), "p12_vekil": b12.p12_vekil()},
        "b13": {"matris": mat, "matris_meta": meta},
    }
    # (yol, ölçü, kartın hangi sütununu destekler, doğrudan mı). "Doğrudan": kartın tepki iddiasını
    # (olay günü, yayım ayı ya da vaka penceresi) ölçen kanıt; "dolaylı": ilişkili ama başka yönde ya
    # da başka sıklıkta bir yapısal ilişki (ör. kurdan cari dengeye, seviye regresyonu).
    kartlar = [
        ("Bütçe / borçlanma programı", "butce", [
            ("b13.matris.butce.R1", "ABD mali pencereleri, normal rejim", ["dm"], True),
            ("b13.matris.butce.R5_DM", "ABD ve İngiltere pencereleri, küresel riskten kaçış", ["dm"], True),
            ("b13.matris.butce.R4", "euro çevresi mali stres pencereleri", ["em"], True),
            ("b13.matris.butce.R5_EM", "İtalya 2011", ["em"], True),
            ("b05.sekil_07", "DM mali olay kadranı ve uzun uç baskınlığı", ["dm", "ilk_iki_olcu", "gecersiz_kilan"], True),
            ("b05.p5a", "ABD 2023 ayılı dikleşmesi ve vade primi", ["dm"], True),
            ("b06.p6d.olaylar", "çevre ülke − Almanya farkı pencereleri", ["em"], True),
            ("b06.p6c.n5y.degisim", "faiz dışı denge ↔ 5 yıllık getiri (çeyreklik seviye ilişkisi)", ["em"], False)],
         "Türkiye'nin kendi bütçe olayı günleri arşivde yok."),
        ("GSYH, PMI/ISM", "gsyh", [
            ("b13.matris.gsyh.R3", "Türkiye GSYH yayım günü", ["em"], True),
            ("b03.p3d.tr_gsyh.kapi.n2y", "GSYH günü × 2 yıllık kapısı", ["ilk_iki_olcu", "gecersiz_kilan"], True),
            ("b03.p3d.tr_gsyh.kapi.usdtry", "GSYH günü × kur kapısı", ["em"], True),
            ("b13.matris.gsyh.R1", "ABD ISM/PMI", ["dm"], True)],
         "ABD ISM/PMI ve GSYH yayım takvimi arşivde yok; politika beklentisi ölçüsü (ilk iki ölçünün ikincisi) "
         "yayım günü için kurulmadı."),
        ("İstihdam", "istihdam", [
            ("b13.matris.istihdam.R1", "ABD istihdam günü", ["dm"], True),
            ("b03.p3d.abd_istihdam", "yayım günü ile sıradan günün kovaryansı", ["dm", "gecersiz_kilan"], True)],
         "BLS yayım arşivi elde yok; Türkiye işgücü yayım takvimi arşivde yok."),
        ("TÜFE", "tufe", [
            ("b13.matris.tufe.R3", "Türkiye TÜFE günü, normal rejim", ["em"], True),
            ("b13.matris.tufe.R4", "Türkiye TÜFE günü, mali baskınlık", ["em"], True),
            ("b04.p4a.yayim_gunu.kapi.n2y", "TÜFE günü × 2 yıllık kapısı", ["ilk_iki_olcu", "gecersiz_kilan"], True),
            ("b04.p4a.yayim_gunu.kapi.usdtry", "TÜFE günü × kur kapısı", ["em"], True),
            ("b04.p4a.aylik_iliski.d_n2y.d2023_2026", "sürpriz → yayım ayında 2 yıllık", ["em", "ilk_iki_olcu"], True),
            ("b04.p4a.aylik_iliski.d_usdtry.d2023_2026", "sürpriz → yayım ayında kur", ["em"], True),
            ("b04.p4c", "Türkiye 2021 ↔ ABD 2022", ["dm", "em"], True),
            ("b04.p4b", "ABD TÜFE günü kovaryansı", ["dm"], True),
            ("b13.matris.tufe.R1", "ABD TÜFE", ["dm"], True)],
         "ABD TÜFE yayım günleri (BLS) elde yok."),
        ("PPK / FOMC / ECB", "para", [
            ("b13.matris.para.R1", "FOMC, normal rejim", ["dm"], True),
            ("b13.matris.para.R5_DM", "FOMC, küresel riskten kaçış", ["dm"], True),
            ("b13.matris.para.R3", "PPK, güvenilir merkez bankası", ["em"], True),
            ("b13.matris.para.R4", "PPK, mali baskınlık", ["em"], True),
            ("b13.matris.para.R5_EM", "PPK, küresel riskten kaçış", ["em"], True),
            ("b03.p3b.tepki.usdtry.yonetilen_haric", "anket sürprizi → kur (PPK günü)", ["em"], True),
            ("b03.p3b.ima_surprizi", "kısa uç ima sürprizi (3 aylık)", ["ilk_iki_olcu", "gecersiz_kilan"], True),
            ("b03.p3b.kapi.n2y", "PPK × 2 yıllık kapısı", ["ilk_iki_olcu"], True),
            ("b03.p3b.kapi.usdtry", "PPK × kur kapısı", ["em"], True),
            ("b02.p2.kapi_ozet.kurulabilir", "kurulabilir seri × olay türleri (FOMC dahil)", ["dm", "em"], True)],
         "ECB karar günleri arşivde yok."),
        ("Cari denge / dış ticaret", "cari", [
            ("b13.matris.cari.R4", "cari denge yayım günü", ["em"], True),
            ("b13.matris.cari.R1", "DM cari denge yayım günü", ["dm"], True),
            ("b08.p8d", "Kırılgan Beşli 2013 (finansman kalitesi)", ["em"], True),
            ("b08.p8c.cari", "REDK sapması → sonraki 12 ayın cari dengesi", ["em"], False),
            ("b08.p8b.hukum_gecikme_12", "J-eğrisi: reel kur → mal dengesi, 12 ay gecikme", ["em"], False)],
         "TCMB ödemeler dengesi yayım günleri arşivde yok; çekirdek cari ve finansman bileşiminin yayım günü "
         "tepkisi kurulmadı."),
        ("Haftalık rezerv", "rezerv", [
            ("b13.matris.rezerv.R3", "rezerv şoku haftası, güvenilir merkez bankası", ["em"], True),
            ("b13.matris.rezerv.R5_EM", "rezerv şoku haftası, küresel riskten kaçış", ["em"], True),
            ("b13.matris_meta.rezerv.kapi_em.kur", "rezerv şoku haftasında kurun plasebo profili", ["em", "gecersiz_kilan"], True),
            ("b09.p9b", "kur baskısının kur, rezerv ve faiz ayrışımı", ["em", "gecersiz_kilan"], True),
            ("b09.p9a.son_deger", "swap hariç net rezerv ve kapsama", ["ilk_iki_olcu"], False),
            ("b13.matris.rezerv.R1", "DM rezervi", ["dm"], True)],
         None),
        ("Not kararı", "not", [
            ("b13.matris.not.R1", "Fitch 2023 tepki günü", ["dm"], True),
            ("b13.matris.not.R2", "Moody's 2025 tepki günü", ["dm"], True),
            ("b12.p12_dm", "DM not kararları, z ve iki günlük pencere", ["dm"], True),
            ("b12.p12", "Türkiye not kararları", ["em"], True),
            ("b12.p12_vekil.dibs5y_abd10y.donemler.tum_yonetilen_haric", "ülke primi vekili DİBS 5y − ABD 10y ↔ kur "
             "(haftalık)", ["ilk_iki_olcu"], False)],
         _not_eksik(kaynaklar["b12"]["p12"])),
    ]
    out = []
    for ad, sat, kan, eksik in kartlar:
        satir = []
        for yol, olcu, sutun, dogrudan in kan:
            dugum = _dugum(kaynaklar, yol.split("."))       # yol yoksa KeyError: kart sessizce kanıtsız kalmaz
            g = _guc(dugum)
            if yol == "b09.p9b":
                g = "tarif edici"              # ağırlıklar tam örneklemden: tarif ayrışımı (Bölüm 9, sınır alanı)
            if yol == "b02.p2.kapi_ozet.kurulabilir":
                g = "ölçüldü" if dugum else "kurulmadı (kapı)"
            if yol == "b09.p9a.son_deger":
                g = "tarif edici"              # vekil paydalı oran, test değil
            if yol == "b05.p5a":
                g = "vaka"                     # tek pencere (31.07 → 19.10.2023)
            k = {"yol": yol, "olcu": olcu, "sutun": sutun, "dogrudan": bool(dogrudan), "guc": g}
            ge = _guc_es(dugum) if yol.startswith("b13.matris.") else None
            if ge:
                k["guc_es_hareket"] = ge
            satir.append(k)
        ozet = {}
        for taraf in ("dm", "em"):
            gg = [x["guc"] for x in satir if x["dogrudan"] and taraf in x["sutun"]]
            ozet[taraf] = _en_guclu(gg) if gg else "kurulmadı"
        r = {"kart": ad, "matris_satiri": sat, "kanitlar": satir, "guc_ozeti": ozet}
        if eksik:
            r["eksik"] = eksik
        out.append(r)
    return out


_GUC_SIRA = ("ölçüldü", "tarif edici", "vaka", "kaynak", "kurulmadı (kapı)", "kurulmadı")


def _en_guclu(g: list) -> str:
    return min(g, key=lambda x: _GUC_SIRA.index(x) if x in _GUC_SIRA else len(_GUC_SIRA))


def yollari_sina(olcum: dict, kk: list | None = None) -> list:
    """Kart kanıt yollarının yazılmış ölçüm dosyasında bulunduğunu sınar (olc() dışında,
    `olcum.py` koştuktan sonra). Eksik yolları döndürür."""
    kk = kk if kk is not None else olcum["b13"]["kart_kanit"]
    eksik = []
    for kart in kk:
        for k in kart["kanitlar"]:
            try:
                _dugum(olcum, k["yol"].split("."))
            except KeyError:
                eksik.append(k["yol"])
    return eksik


# ═══════════════════════════════════════════════════════════════ giriş
def olc() -> dict:
    mat, meta = _matris()
    out = {
        "matris": mat,
        "matris_meta": meta,
        "matris_ozeti": _matris_ozeti(mat),
        "matris_tanim": {
            "sutunlar": [{"kimlik": k, "ad": a, "taraf": t} for k, a, t in SUTUNLAR],
            "soklar": [{"kimlik": k, "ad": a} for k, a in SOKLAR],
            "seriler": {"dm": SERI_BIRIM["dm"], "em": SERI_BIRIM["em"]},
            "durumlar": {"olculdu": "en az bir seri kapıyı geçti, olay en az on",
                         "vaka": "bir ile dokuz olay: oranlar yazılır, korelasyon yazılmaz",
                         "kaynak": "bu veriyle kurulamadı (seri ya da olay yok, ya da sınama geçmedi); ilgili bölüm "
                                   "konuyu kaynakla anlatır (yalnız etiket). Bu işaret kurulamama sebebinden önce "
                                   "gelir, sebep hücrede ayrıca yazılır",
                         "kurulmadi": "sebebiyle"},
            "sebep_turleri": dict(SEBEP_TURU),
            "es_hareket_yonu": "para değeri artışı yerel paranın değer kazancıdır; artı korelasyon faiz ↑ para ↑ "
                               "(B terimi), eksi faiz ↑ para ↓ (C terimi)",
            "vaka_asgari": VAKA_ASGARI, "pencere": PENCERE,
        },
        "n": int(sum(mat[s][c]["n"] for s in mat for c in mat[s])),
        "ilk": "2000-01-03", "son": _iso(oo.CIPA_GUN),
        "yontem": "On şok türünün olay günlerinde kur, 2 yıllık, uzun uç ve eğim değişiminin mutlak büyüklüğü aynı "
                  "rejimin sıradan günlerine oranlandı ve 2 yıllık getiri ile yerel paranın değeri arasındaki "
                  "korelasyon alındı; rejim olay gününün düştüğü haftanın Bölüm 1 etiketidir.",
        "kaynak": sorted(set(KAYNAK_DM + KAYNAK_EM + ["ppk_kararlari", "rezerv_haftalik", "kuresel_aylik",
                                                    "cnbc_avrupa_getiri_gunluk", "enflasyon_aylik",
                                                    "bulut: tuik_takvim", "bulut: fomc_takvim", "bulut: gilt"])),
    }
    out["sekil_21"] = sekil_21(mat)
    out["teshis_ornegi"] = teshis_ornegi()
    out["kart_kanit"] = kart_kanit(mat, meta)
    return oo.yuvarla(out, 4)


if __name__ == "__main__":
    import json
    import sys
    import time
    t0 = time.monotonic()
    d = olc()
    metin = json.dumps(d, ensure_ascii=False, allow_nan=False)
    print(f"süre {time.monotonic() - t0:.1f} sn · {len(metin) // 1024} KB")
    if "--sina" in sys.argv:
        from pathlib import Path
        o = json.loads((Path(__file__).resolve().parent / "veri" / "olcum.json").read_text(encoding="utf-8"))
        e = yollari_sina(o)
        print("eksik yol:", e or "yok")
