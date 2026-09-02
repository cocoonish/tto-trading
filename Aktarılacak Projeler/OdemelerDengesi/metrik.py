# -*- coding: utf-8 -*-
"""Ödemeler dengesi ve dış finansman — metrik katmanı.

Ne hesaplar
-----------
1. **Cari denge: manşet ve ÇEKİRDEK.** 12 aylık birikimli manşet cari denge
   (Q01) ile altın ve enerji hariç çekirdek cari denge (K10); aradaki makas
   bu hattın başrol sayısıdır. Köprü kimliği sınanır:
   manşet = çekirdek + altın net + enerji net.
2. **Cari dengenin alt kalemleri.** Mal, hizmet, birincil gelir, ikincil
   gelir — 12 aylık birikimli. Toplamın manşete eşitliği sınanır.
3. **Cari denge / GSYH.** BİRİM ZİNCİRİ TEK YERDE: bin TL → /1000 → milyon TL
   → /çeyrek ORTALAMA USDTRY → milyon USD. Nokta kur (çeyrek sonu) akım
   büyüklüğünü çeyrek içi kur hareketi kadar yanıltır. Mertebe denetimi
   (4 çeyreklik GSYH 1,0–2,0 trilyon USD bandında) hattı DURDURUR.
4. **Finans hesabı kırılımı — GİRİŞ işaretiyle.** BPM6 işaret çevirmesi TEK
   YERDE yapılır (bkz. `finans_metrikleri`); grafik katmanı işaret çevirmez.
5. **Kaliteli finansman.** Net DYY girişi + özel sektörün net uzun vadeli
   kredi kullanımı. DÜZEY (mn USD) başroldür; oranlar payda mutlak eşiğin
   ÜSTÜNDEYKEN hesaplanır, altında NaN'a düşer (payda sıfıra yaklaşınca oran
   patlıyor — ölçüldü: %−1022 … %+2149).
6. **Uzun vadeli dış borç çevirme oranı** (banka / reel sektör / genel
   hükümet), 12 AYLIK TOPLAMLAR üzerinden. TCMB'nin kendi ODEROLL serisiyle
   YAN YANA ama AYRI çizilir: kapsamları farklı (TCMB kısa+uzun vadeyi ve
   tahvili birlikte alıyor); ortalama fark ölçülür ve raporlanır.
7. **Net hata ve noksan** — düzey, 12 aylık birikim, cari dengeye oranı,
   36 aylık yüzdelik dilim. Ölçüm; yorum yok.
8. **Brüt dış finansman ihtiyacı** ve karşılanması — ödemeler dengesi
   kimliğinden TÜRETİLEN, birebir kapanan bir tablo.
9. **Eurobond akımı** ve **haftalık dış borç ödeme takvimi** (hattın en taze
   verisi, kendi dönem etiketiyle).

Koşum:  python3 metrik.py   (önce veri.py)
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import veri
from veri import PROJE, VERI, ay_ad, ceyrek_ad, gun_ad

# --------------------------------------------------------------------------- eşikler
# 12 AYLIK TOPLAMLAR üzerinden çalışılır: aylık ödemeler dengesi mevsimsel ve
# gürültülü; aylık oran hesabı payda küçüldüğünde patlıyor.
PENCERE = 12

# ORAN PAYDASI EŞİĞİ (milyon USD, 12 aylık birikimli mutlak değer).
# ÖLÇÜLDÜ (keşif): net finansman girişi paydasıyla kalite oranı 2026-03'te
# %575'e fırlıyor; yükümlülük oluşumu paydasıyla 2010 sonrası bant
# %−1022 … %+2149; cari açık paydasıyla %−1063 … %+245. Sebep veri hatası
# değil, paydanın sıfıra yaklaşması ve İŞARET DEĞİŞTİRMESİ. 10.000 mn USD
# (10 milyar) eşiği, 12 aylık yükümlülük oluşumunun tarihsel medyanının
# yaklaşık onda biridir: bunun altındaki bir paydada oran bilgi taşımıyor
# sayılır ve seri BOŞ bırakılır (grafikte boşluk, gerekçesi altyazıda).
ORAN_PAYDA_ESIK = 10_000.0

# Çevirme oranında payda (geri ödeme bacağı) bu eşiğin altındaysa oran NaN.
# 12 aylık geri ödeme toplamı 500 mn USD'nin altına düşen bir sektörde
# "çevirme oranı" bir orandan çok bölme kazasıdır.
ROLL_PAYDA_ESIK = 500.0

# GSYH mertebe denetimi (trilyon USD). Türkiye'nin yıllık GSYH'si 2010 sonrası
# 0,8–1,4 trilyon USD bandında; 2026 için ölçülen 1,634 trilyon. Bant dışı bir
# değer birim zincirinin (bin TL → milyon USD) bozulduğunu gösterir ve hattı
# DURDURUR — 1000× hatanın tam olarak yakalanacağı yer burasıdır.
GSYH_BANT_TRN = (1.0, 2.0)

# FİNANSAL TÜREVLER KALEMİNİN BAŞLANGICI (tanım kırılması).
# Q37/Q38 bu tarihte başlıyor; öncesinde kalem YOK (sıfır değil). Yükümlülük
# toplamının TANIMI burada değişir, bu yüzden "2010 sonrası medyan" iki farklı
# paydanın karışımıdır ve 2014 sonrası medyan AYRICA hesaplanır. Sabit elle
# yazılı DEĞİL sayılmasın diye her koşuda verinin kendi ilk dolu ayıyla
# karşılaştırılır (bkz. `finans_metrikleri`), kayarsa uyarı düşer.
TUREV_BAS = "2014-01-01"

# Kimlik eşikleri (mn USD). Ödemeler dengesi tam sayıya yuvarlı yayımlanıyor;
# eşikler MUTLAK tutulur — bağıl eşik payda sıfıra yaklaşınca patlıyor.
ESIK_KIMLIK = 1.0
ESIK_KIMLIK_TOPLAM = 5.0
# 12 aylık birikimli kimliklerde 12 ayın yuvarlama artığı birikir.
ESIK_KIMLIK_12 = 12.0

_UYARI: list[str] = []


def uyar(m: str) -> None:
    if m not in _UYARI:
        _UYARI.append(m)
    print("  ! " + m, flush=True)


# --------------------------------------------------------------------------- yardımcılar
def r12(s: pd.Series, pencere: int = PENCERE) -> pd.Series:
    """12 aylık birikimli toplam. Eksik ay varsa NaN — kısmi toplam YAYIMLANMAZ.

    `min_periods=pencere` bilinçli: 11 aylık bir toplamı 12 aylık diye
    göstermek, seri başında sistematik olarak küçük bir açık uydurur.
    """
    return s.rolling(pencere, min_periods=pencere).sum()


def _oran(pay: pd.Series, payda: pd.Series, esik: float = ORAN_PAYDA_ESIK,
          yuzde: bool = True) -> pd.Series:
    """Payda mutlak eşiğin ALTINDAYKEN NaN döndüren bölme.

    Bu hattın en pahalı sunum hatası, paydası sıfıra yaklaşan bir oranı
    grafiğe basmaktır: çizgi tavana fırlar, okur olayı 'finansman kalitesi
    patladı' diye okur. Oysa değişen paydadır.
    """
    p = payda.where(payda.abs() >= esik)
    o = pay / p
    return o * 100.0 if yuzde else o


def fisher_reel(nominal_yuzde: pd.Series | float,
                enflasyon_yuzde: pd.Series | float):
    """Fisher reel getiri: (1+i)/(1+π) − 1. Basit çıkarma DEĞİL.

    Bu depoda BAĞLAYICI karar: yüksek enflasyon rejiminde i − π, reel getiriyi
    sistematik olarak yukarı sapmalı ölçer (i=%40, π=%35 için basit çıkarma 5,0
    puan der; Fisher 3,70 puan). Bu hat USD cinsi AKIM büyüklükleriyle çalışır
    ve şu an bir reel faiz/reel getiri serisi yayımlamaz — dolayısıyla
    fonksiyon yalnız türetme eklenirse kullanılmak üzere burada durur ve
    `metrik_ozet.json` içindeki `fisher_not` alanı bunu açıkça söyler.
    """
    i = np.asarray(nominal_yuzde, dtype=float) / 100.0
    p = np.asarray(enflasyon_yuzde, dtype=float) / 100.0
    r = (1.0 + i) / (1.0 + p) - 1.0
    if isinstance(nominal_yuzde, pd.Series):
        return pd.Series(r * 100.0, index=nominal_yuzde.index)
    return float(r * 100.0)


def _kimlik(rapor: dict, ad: str, sol: pd.Series, sag: pd.Series, esik: float,
            durdur: bool, dur_liste: list[str], birim: str = "mn USD",
            tautoloji: bool = False) -> None:
    """Kimlik sınaması. `tautoloji=True` ise kayıt SINAV SAYILMAZ.

    Sol taraf sağ taraftan cebirsel olarak türetiliyorsa sapma her koşuda
    0,00'dır ve denetim hiçbir hata yakalamaz. Böyle bir kaydı "sınandı" diye
    sunmak, olmayan bir güvence satmaktır; işaretlenir ve sayımdan düşer.
    """
    d = pd.DataFrame({"s": sol, "r": sag}).dropna()
    if d.empty:
        uyar(f"KİMLİK: '{ad}' sınanamadı — girdi serileri kesişmiyor.")
        return
    fark = (d["s"] - d["r"]).abs()
    gecti = bool(fark.max() <= esik)
    rapor[ad] = {"n": int(len(d)), "maks_fark": float(fark.max()),
                 "maks_tarih": str(fark.idxmax().date()),
                 "son_fark": float(fark.iloc[-1]), "birim": birim,
                 "esik": esik, "gecti": gecti, "durdurucu": bool(durdur),
                 "tautoloji": bool(tautoloji)}
    if tautoloji:
        rapor[ad]["not"] = (
            "TAUTOLOJİ: sol taraf sağ taraftan türetildiği için sapma tanım "
            "gereği sıfırdır. Bu kayıt bir SINAV DEĞİL, sunum tutarlılığının "
            "kaydıdır; kimlik sayımına girmez ve sayfada 'sınandı' diye "
            "gösterilmez.")
    if not gecti:
        m = (f"KİMLİK BOZUK: {ad} — en büyük sapma {fark.max():,.2f} {birim} "
             f"({fark.idxmax():%m.%Y}), eşik {esik} {birim}.")
        uyar(m)
        if durdur:
            dur_liste.append(m)


# --- artık, bacak ve mertebe denetimleri (tautoloji OLMAYAN sınavlar) ------
# Bu üçü, yığın ve finansman tablolarının GERÇEK denetimidir: girdileri
# bozulduğunda sonuç değişir. Tautolojik kimlikler bozulduğunda değişmiyordu.

# Diğer yatırım yükümlülüğünün artığı için üst sınır (12 aylık artık ÷ 12
# aylık brüt ciro). ÖLÇÜLDÜ (2010+): medyan %6,2 · en büyük %27,4 (2020-01).
# Eşik %35, yani ölçülen en büyük değerin yaklaşık %28 üstünde. Artık bu
# bandı aşarsa bir alt kalem düşmüş ya da birimi kaymış demektir.
ARTIK_BANT_YUZDE = 35.0

# Uzun vadeli anapara (aylık ÖD) ÷ haftalık dış borç ödemesi (52 haftalık).
# Kapsamlar farklı olduğu için eşitlik değil BANT sınanır. ÖLÇÜLDÜ
# (2013-12…2026-06, n=151): 1,50 … 6,14, medyan 3,26. Bant 1,0–8,0.
UV_HAFTA_BANT = (1.0, 8.0)


def _artik_denetimi(rapor: dict, a: pd.DataFrame) -> None:
    """Ayrıntılı sunumun alt kalemleri ile analitik sunumun toplamını kıyaslar.

    Q25 (3.8 Diğer Yatırımlar: net yükümlülük oluşumu, ODANA6) ile
    Q143 + Q157 + Q184 + Q203 (ODEAYRSUNUM6) İKİ AYRI TABLODAN gelir. Bu hat
    ayrıntılı sunumun "3.4.4 Diğer Yükümlülükler" kalemini çekmediği için
    eşitlik beklenmez; artık ölçülür ve bir banda oturması istenir.
    """
    alt = a[["ay_mevduat_yuk", "ay_kredi_yuk", "ay_ticari_kredi",
             "ay_sdr"]].fillna(0.0).sum(axis=1)
    artik12 = r12(a["diger_yuk"] - alt)
    # Payda: dört ana bacağın MUTLAK değerinin 12 aylık toplamı ("brüt ciro").
    # Net toplamı payda yapmak yanlış olurdu — net sıfıra yaklaşınca oran
    # patlıyor (2018-09'da %333 ölçüldü, veri bozuk olmadığı hâlde).
    ciro12 = r12(a["dyy_yuk"].abs() + a["port_yuk"].abs()
                 + a["diger_yuk"].abs() + a["turev_yuk"].fillna(0.0).abs())
    o = (artik12 / ciro12).abs().loc["2010-01-01":].dropna() * 100
    if o.empty:
        uyar("ARTIK DENETİMİ sınanamadı — Q25 alt kalemleri kesişmiyor.")
        return
    gecti = bool(o.max() <= ARTIK_BANT_YUZDE)
    rapor["artık bandı: Q25 − (Q143+Q157+Q184+Q203) ÷ brüt ciro"] = {
        "n": int(len(o)), "son_yuzde": round(float(o.iloc[-1]), 2),
        "maks_yuzde": round(float(o.max()), 2),
        "maks_tarih": str(o.idxmax().date()),
        "medyan_yuzde": round(float(o.median()), 2),
        "esik_yuzde": ARTIK_BANT_YUZDE, "gecti": gecti, "durdurucu": False,
        "not": ("İKİ AYRI EVDS TABLOSU kıyaslanır (analitik Q25 ↔ ayrıntılı "
                "sunumun alt kalemleri); eşitlik beklenmez çünkü '3.4.4 Diğer "
                "Yükümlülükler' bu hatta çekilmiyor. Artık bandı aşarsa bir "
                "alt kalem düşmüş ya da birimi kaymış demektir."),
    }
    if not gecti:
        uyar(f"ARTIK BANDI AŞILDI: Q25 artığı {o.max():.1f}% "
             f"({o.idxmax():%m.%Y}), bant {ARTIK_BANT_YUZDE}%. Ayrıntılı "
             "sunumun bir alt kalemi düşmüş olabilir.")


def _bacak_yoklamasi(rapor: dict, M: pd.DataFrame, ad: str, kolonlar: list[str],
                     dur_liste: list[str], baslangic: str = "2010-01-01",
                     son_ay: int = 24) -> None:
    """Yığın/toplam bacaklarının hepsi son `son_ay` ayda dolu mu?

    DURDURUCU. Bir bacağın sessizce NaN'a düşmesi (EVDS kalemi kaldırıldı, ad
    değişti) toplamı kısaltır ama yukarıdaki tautolojik kimlikleri hiç
    bozmaz — orada iki taraf da aynı eksik bacağı taşıdığı için sapma yine
    sıfır çıkar. Bu yoklama tam o boşluğu kapatır.

    SIFIR ORANI DA ÖLÇÜLÜR (uyarı, durdurucu değil): `fillna(0.0)` ile kurulan
    bir bacak (ör. finansal türevler) kaynağı büsbütün düşse bile NaN
    göstermez, sessizce sıfırlanır. Boş oranı o bacakta hep %0 kalırdı; sıfır
    oranı ise %100'e fırlar ve gözle görülür.
    """
    d = M.loc[M.index >= pd.Timestamp(baslangic)]
    if d.empty:
        return
    kuyruk = d.iloc[-son_ay:]
    oranlar = {k: round(float(kuyruk[k].isna().mean()) * 100, 1)
               for k in kolonlar if k in kuyruk.columns}
    sifir = {k: round(float((kuyruk[k].fillna(0.0) == 0).mean()) * 100, 1)
             for k in kolonlar if k in kuyruk.columns}
    eksik_kolon = [k for k in kolonlar if k not in M.columns]
    bos = {k: v for k, v in oranlar.items() if v > 0}
    olu = {k: v for k, v in sifir.items() if v >= 100.0}
    gecti = not bos and not eksik_kolon
    rapor[f"bacak yoklaması: {ad}"] = {
        "beklenen_kalem": len(kolonlar), "bulunan_kalem": len(oranlar),
        "son_ay": son_ay, "bos_oran_yuzde": oranlar,
        "sifir_oran_yuzde": sifir, "olu_bacak": list(olu),
        "gecti": gecti, "durdurucu": True,
        "not": ("Her bacağın son 24 aydaki BOŞ ve SIFIR oranı ölçülür. "
                "Tautolojik kimlikler düşen bir bacağı görmez: iki taraf da "
                "aynı eksiği taşır ve sapma yine 0,00 çıkar. fillna(0) ile "
                "kurulan bir bacak düştüğünde boş değil SIFIR görünür — ölü "
                "bacak listesi o durumu yakalar."),
    }
    if olu:
        uyar(f"ÖLÜ BACAK ({ad}): {list(olu)} son {son_ay} ayın TAMAMINDA 0 — "
             "kalem gerçekten sıfır olabilir, ama kaynağın düşmüş olması da "
             "aynı görüntüyü verir. Yığında görünmez.")
    if not gecti:
        m = (f"BACAK DÜŞTÜ ({ad}): "
             + (f"kolon yok {eksik_kolon}; " if eksik_kolon else "")
             + (f"son {son_ay} ayda boş kalan bacaklar {bos}" if bos else "")
             + ". Yığın eksik çizilirdi.")
        uyar(m)
        dur_liste.append(m)


def _mertebe_uv_anapara(rapor: dict, M: pd.DataFrame, H: pd.DataFrame) -> None:
    """Uzun vadeli anaparayı BAĞIMSIZ bir kaynakla mertebe olarak kıyaslar.

    Aylık ödemeler dengesinden türetilen `uv_anapara12` ile TCMB'nin HAFTALIK
    dış borç ödeme takviminin (bie_dbafod) 52 haftalık toplamı. Kapsamlar
    farklı — haftalık seri Hazine, TCMB ve duyurulmuş diğer ödemeleri kapsar,
    banka ve reel sektörün bütün kredi itfalarını değil — bu yüzden EŞİTLİK
    değil ORAN BANDI sınanır. Tautolojik kimliğin göremediği "anapara bacağı
    şişti/söndü" hatası burada yakalanır: karşı-deneyde bacaklar bozulunca
    oran 2,21'den 9,85'e çıkıyor ve bant dışına düşüyor.
    """
    if H is None or H.empty or "borc_odeme_top_52h" not in H.columns:
        uyar("MERTEBE KIYASI sınanamadı — haftalık 52 haftalık toplam yok.")
        return
    h52 = H["borc_odeme_top_52h"].dropna().resample("MS").last()
    d = pd.DataFrame({"uv": M["uv_anapara12"], "h": h52}).dropna()
    d = d[d["h"].abs() > 0]
    if d.empty:
        uyar("MERTEBE KIYASI sınanamadı — aylık ve haftalık kuyruklar kesişmiyor.")
        return
    o = d["uv"] / d["h"]
    alt, ust = UV_HAFTA_BANT
    gecti = bool((o.min() >= alt) and (o.max() <= ust))
    rapor["mertebe: UV anapara(12a) ÷ haftalık dış borç ödemesi(52h)"] = {
        "n": int(len(o)), "son_oran": round(float(o.iloc[-1]), 2),
        "min_oran": round(float(o.min()), 2), "maks_oran": round(float(o.max()), 2),
        "medyan_oran": round(float(o.median()), 2), "bant": list(UV_HAFTA_BANT),
        "son_uv_anapara12_mn_usd": round(float(d["uv"].iloc[-1]), 0),
        "son_hafta52_mn_usd": round(float(d["h"].iloc[-1]), 0),
        "gecti": gecti, "durdurucu": False,
        "not": ("BAĞIMSIZ KAYNAK kıyası, kimlik DEĞİL: kapsamlar farklı "
                "(haftalık seri Hazine + TCMB + duyurulmuş diğer ödemeler). "
                "Eşitlik beklenmez; oran bandın dışına çıkarsa anapara "
                "bacaklarından biri şişmiş ya da düşmüştür."),
    }
    if not gecti:
        uyar(f"MERTEBE BANDI AŞILDI: UV anapara ÷ haftalık 52h oranı "
             f"{o.min():.2f}–{o.max():.2f}, bant {UV_HAFTA_BANT}. Anapara "
             "bacaklarından biri şişmiş ya da düşmüş olabilir.")


# ===========================================================================
# (1) CARİ DENGE — MANŞET, ÇEKİRDEK VE ALT KALEMLER
# ===========================================================================
def cari_metrikleri(a: pd.DataFrame) -> pd.DataFrame:
    M = pd.DataFrame(index=a.index)
    # Düzeyler (aylık, milyon USD). İŞARET: cari denge negatif = AÇIK.
    M["cari"] = a["cari"]
    M["cekirdek"] = a["hc_cekirdek"]
    M["altin_net"] = a["hc_altin_net"]
    M["enerji_net"] = a["hc_enerji_net"]
    M["altin_haric"] = a["hc_altin_haric"]
    M["enerji_haric"] = a["hc_enerji_haric"]
    M["ihracat"] = a["ihracat"]
    M["ithalat"] = a["ithalat"]
    M["mal_denge"] = a["mal_denge"]
    M["hizmet_denge"] = a["hizmet_gelir"] - a["hizmet_gider"]
    M["birincil_denge"] = a["birincil_gelir"] - a["birincil_gider"]
    M["ikincil_denge"] = a["ikincil_denge"]
    M["sermaye_hesabi"] = a["sermaye_hesabi"]
    M["nhn"] = a["nhn"]
    M["rezerv_akim"] = a["rezerv_akim"]     # POZİTİF = rezerv ARTIŞI (stokla sınandı)

    # 12 aylık birikimli
    for k in ("cari", "cekirdek", "altin_net", "enerji_net", "altin_haric",
              "enerji_haric", "ihracat", "ithalat", "mal_denge",
              "hizmet_denge", "birincil_denge", "ikincil_denge",
              "sermaye_hesabi", "nhn", "rezerv_akim"):
        M[k + "12"] = r12(M[k])

    # Makas: manşet ile çekirdek arasındaki fark = altın net + enerji net.
    M["makas12"] = M["cari12"] - M["cekirdek12"]
    return M


# ===========================================================================
# (2) CARİ DENGE / GSYH — BİRİM ZİNCİRİ TEK YERDE
# ===========================================================================
def gsyh_metrikleri(M: pd.DataFrame, c: pd.DataFrame,
                    g: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Üç aylık çerçeve: GSYH (USD) ve cari denge / GSYH oranı.

    BİRİM TUZAĞI — bu hattın 1000× hata adayı:
      TP.GSYIH20.BY.B1GQ  → BİN TL, ÜÇ AYLIK
      Ödemeler dengesi    → MİLYON USD, AYLIK
    Zincir:  bin TL → /1000 → milyon TL → /çeyrek ORTALAMA USDTRY → milyon USD
    Çeyrek ORTALAMASI kullanılır; nokta kur (çeyrek sonu) bir AKIM büyüklüğünü
    çeyrek içi kur hareketi kadar yanıltır.

    FREKANS/GECİKME UYUMSUZLUĞU: ödemeler dengesi aylık ve ~2 ay gecikmeli,
    GSYH üç aylık ve ~5 ay gecikmeli. Oran GSYH'nin son çeyreğinde DURUR;
    'son ay' diye sunmak sessiz bayatlamadır. Oranın kendi dönemi ayrı
    taşınır (ozet.json'da `_tarih2`).
    """
    tani: dict = {}
    if c.empty or "gsyh_bin_tl" not in c.columns or g.empty:
        uyar("GSYH ya da kur serisi yok — cari denge/GSYH oranı hesaplanamadı.")
        return pd.DataFrame(), tani

    # Kur: çeyrek ORTALAMASI (iş günü kurlarının aritmetik ortalaması).
    kur_ceyrek = g["usdtry"].dropna().resample("QE").mean()
    kur_nokta = g["usdtry"].dropna().resample("QE").last()

    G = pd.DataFrame(index=c.index)
    G["gsyh_bin_tl"] = c["gsyh_bin_tl"]
    G["usdtry_ceyrek_ort"] = kur_ceyrek.reindex(G.index)
    G["usdtry_ceyrek_son"] = kur_nokta.reindex(G.index)
    # bin TL → milyon TL: /1000.  milyon TL → milyon USD: /kur.
    G["gsyh_mn_tl"] = G["gsyh_bin_tl"] / 1000.0
    G["gsyh_mn_usd"] = G["gsyh_mn_tl"] / G["usdtry_ceyrek_ort"]
    G["gsyh4_mn_usd"] = G["gsyh_mn_usd"].rolling(4, min_periods=4).sum()
    # Nokta kurla hesaplanan sürüm YALNIZ tanı içindir (fark ölçülsün diye).
    G["gsyh4_mn_usd_nokta"] = (G["gsyh_mn_tl"] / G["usdtry_ceyrek_son"]
                               ).rolling(4, min_periods=4).sum()

    # 12 aylık birikimli cari dengeyi çeyrek SONUNA hizala. Aylık seri ay
    # BAŞINA çapalı; çeyrek sonuyla eşleşmesi için ay sonuna taşınır.
    def _ceyrege(s: pd.Series) -> pd.Series:
        x = s.copy()
        x.index = x.index + pd.offsets.MonthEnd(0)
        return x.reindex(G.index)

    G["cari12_mn_usd"] = _ceyrege(M["cari12"])
    G["cekirdek12_mn_usd"] = _ceyrege(M["cekirdek12"])
    G["cari_gsyh"] = G["cari12_mn_usd"] / G["gsyh4_mn_usd"] * 100.0
    G["cekirdek_gsyh"] = G["cekirdek12_mn_usd"] / G["gsyh4_mn_usd"] * 100.0

    son = G["gsyh4_mn_usd"].dropna()
    if len(son):
        trn = float(son.iloc[-1]) / 1e6      # milyon USD → trilyon USD
        tani["gsyh4_trilyon_usd"] = round(trn, 3)
        tani["gsyh4_donem"] = str(son.index[-1].date())
        tani["mertebe_bant_trn"] = list(GSYH_BANT_TRN)
        tani["mertebe_gecti"] = bool(GSYH_BANT_TRN[0] <= trn <= GSYH_BANT_TRN[1])
        # Nokta kur ile ortalama kur arasındaki fark ÖLÇÜLÜR: "ortalama kur
        # kullanıyoruz" cümlesinin bedeli sayfada görünsün.
        n = G["gsyh4_mn_usd_nokta"].dropna()
        if len(n):
            tani["nokta_kur_farki_yuzde"] = round(
                float(n.iloc[-1] / son.iloc[-1] - 1) * 100, 2)
    o = G["cari_gsyh"].dropna()
    if len(o):
        tani["cari_gsyh_son"] = round(float(o.iloc[-1]), 2)
        tani["cari_gsyh_donem"] = str(o.index[-1].date())
        tani["cari_gsyh_min"] = round(float(o.min()), 2)
        tani["cari_gsyh_min_donem"] = str(o.idxmin().date())
        tani["cari_gsyh_maks"] = round(float(o.max()), 2)
        tani["cari_gsyh_maks_donem"] = str(o.idxmax().date())
    ck = G["cekirdek_gsyh"].dropna()
    if len(ck):
        tani["cekirdek_gsyh_son"] = round(float(ck.iloc[-1]), 2)
    return G, tani


# ===========================================================================
# (3) FİNANS HESABI — İŞARET ÇEVİRMESİ TEK YERDE
# ===========================================================================
def finans_metrikleri(M: pd.DataFrame, a: pd.DataFrame) -> pd.DataFrame:
    """Finans hesabı kalemlerini GİRİŞ işaretiyle üretir.

    BPM6 KONVANSİYONU: finans hesabı = net varlık edinimi − net yükümlülük
    oluşumu; POZİTİF değer SERMAYE ÇIKIŞI demektir. Sayfada ve grafikte
    "giriş" okunacağı için işaret BURADA, TEK YERDE çevrilir. grafik.py bu
    kolonları OLDUĞU GİBİ çizer — orada tekrar çevrilirse iki kez çevrilir ve
    seri sessizce ters yöne bakar.

    HANGİ FİNANS HESABI? Analitik sunumun Q13'ü, yani REZERV HARİÇ. Ayrıntılı
    sunumun Q101'i rezervi İÇERİR ve ikisi 2026-03'te 43,4 milyar USD ayrışır.
    Rezerv değişimi (Q33) bu kırılımın İÇİNDE DEĞİL; ayrı kolon olarak taşınır
    ve grafikte ayrı etiketlenir.

    TÜREVLER 2014-01'de BAŞLIYOR: öncesinde kalem YOK (sıfır değil). Toplama
    girerken 0 kabul edilir — bu bir veri eksikliği değil, tanım genişlemesi;
    Q13 kimliği de ancak 2014'ten itibaren dört kalemle kapanıyor.
    """
    # Çerçeveyi birleştir: aşağıda çok sayıda sütun eklenecek ve pandas
    # parçalanmış blok yöneticisi için uyarı basıyor.
    M = M.copy()
    tur_v = a["turev_varlik"].fillna(0.0)
    tur_y = a["turev_yuk"].fillna(0.0)
    # TANIM KIRILMASI ÇIPASI SINANIR: TUREV_BAS elle yazılı bir sabit, ama
    # verinin kendisiyle her koşuda karşılaştırılır. EVDS kalemi geriye
    # uzatırsa (ya da başlangıcı kayarsa) 2014 sonrası medyan sessizce yanlış
    # pencereden hesaplanırdı.
    _tb = a["turev_yuk"].first_valid_index()
    if _tb is not None and _tb != pd.Timestamp(TUREV_BAS):
        uyar(f"TANIM ÇIPASI KAYDI: finansal türev kalemi {_tb:%Y-%m} ayında "
             f"başlıyor, kodda TUREV_BAS={TUREV_BAS}. Türev tanımına göre "
             "bölünen medyan pencereleri güncellenmeli.")

    # --- net giriş (rezerv HARİÇ) -----------------------------------------
    M["fin_giris"] = -a["fin_hesabi"]

    # --- kalem bazında net giriş (yükümlülük − varlık) ---------------------
    M["dyy_giris"] = a["dyy_yuk"] - a["dyy_varlik"]
    M["portfoy_giris"] = a["port_yuk"] - a["port_varlik"]
    M["turev_giris"] = tur_y - tur_v
    M["diger_giris"] = a["diger_yuk"] - a["diger_varlik"]

    # --- yükümlülük ve varlık bacakları ------------------------------------
    # ADLANDIRMA UYARISI — "BRÜT" DEĞİL, NET YÜKÜMLÜLÜK OLUŞUMU.
    # BPM6'da bu kalemlerin hepsi NET yükümlülük oluşumudur (net incurrence of
    # liabilities): Q38'in EVDS'teki adı bile "3.6.Finansal Türevler: NET
    # Yükümlülük Oluşumu". Negatif olabilirler ve olurlar. Kolon adı
    # `brut_yukumluluk` tarihsel sebeple duruyor; SUNUMDA "yükümlülük oluşumu
    # (net)" diye adlandırılır. "Brüt" demek, kalemin yalnız girişleri saydığı
    # izlenimini verirdi — vermez.
    #
    # TÜREV BACAĞI PAYDAYI SAVURUYOR (ölçüldü): son 12 ayda türev yükümlülük
    # −20,6 milyar USD; toplamı 87,3 → 66,7 milyar USD'ye indiriyor ve kalite
    # payını %48,9 yerine %64,0 gösteriyor (15,1 puan). Üstelik kalem
    # 2014-01'de BAŞLIYOR, yani payda 2014 öncesi türevsiz, sonrası türevli —
    # tek bir "2010 sonrası medyan" iki farklı tanımın karışımı olurdu.
    # Bu yüzden İKİ payda birden taşınır ve medyan 2014 SONRASI pencerede de
    # ayrıca hesaplanır (bkz. kalite_metrikleri).
    M["brut_yukumluluk"] = (a["dyy_yuk"] + a["port_yuk"] + tur_y + a["diger_yuk"])
    M["yukumluluk_turevsiz"] = (a["dyy_yuk"] + a["port_yuk"] + a["diger_yuk"])
    M["yerlesik_varlik"] = (a["dyy_varlik"] + a["port_varlik"] + tur_v
                            + a["diger_varlik"])

    # --- yükümlülük bacağının kırılımı (yığılmış grafik için) --------------
    # Toplamları brüt yükümlülüğe BİREBİR eşitlensin diye artık kalemler
    # türetilir; "diğer" kutusu uydurma değil, tanımlı bir artıktır.
    M["yuk_dyy"] = a["dyy_yuk"]
    M["yuk_port_hisse"] = a["port_yuk_hisse"]
    M["yuk_port_borc"] = a["port_yuk_borc"]
    # Portföy yükümlülüğünün hisse+borç senedi dışındaki artığı (2022-01'de
    # eklenen yatırım fonu payları buraya düşer).
    M["yuk_port_artik"] = (a["port_yuk"] - a["port_yuk_hisse"]
                           - a["port_yuk_borc"])
    M["yuk_mevduat"] = a["ay_mevduat_yuk"]
    M["yuk_kredi"] = a["ay_kredi_yuk"]
    # Diğer yatırım yükümlülüğünün mevduat ve kredi dışındaki artığı
    # (ticari krediler, diğer yükümlülükler, SDR).
    M["yuk_diger_artik"] = (a["diger_yuk"] - a["ay_mevduat_yuk"]
                            - a["ay_kredi_yuk"])
    M["yuk_turev"] = tur_y
    M["ticari_kredi_net"] = a["ay_ticari_kredi"]

    # --- vade ve sektör kırılımı (kaliteli finansman & çevirme oranı) ------
    M["kredi_bnk_uv_kul"] = a["ay_kredi_bnk_uv_kul"]
    M["kredi_bnk_uv_ode"] = a["ay_kredi_bnk_uv_ode"]
    M["kredi_dgr_uv_kul"] = a["ay_kredi_dgr_uv_kul"]
    M["kredi_dgr_uv_ode"] = a["ay_kredi_dgr_uv_ode"]
    M["kredi_gh_uv_kul"] = a["ay_kredi_gh_uv_kul"]
    M["kredi_gh_uv_ode"] = a["ay_kredi_gh_uv_ode"]
    M["kredi_bnk_kv"] = a["ay_kredi_bnk_kv"]
    M["kredi_dgr_kv"] = a["ay_kredi_dgr_kv"]
    M["kredi_bnk_uv_net"] = a["ay_kredi_bnk_uv"]
    M["kredi_dgr_uv_net"] = a["ay_kredi_dgr_uv"]

    # --- eurobond (yurt dışı borçlanma senedi) -----------------------------
    # SEYREK SERİ UYARISI: hem toplam (A1/A2) hem alt kırılımlar (A112 genel
    # hükümet, A114 diğer sektör) ihraç/itfa OLMAYAN ayda BOŞ gelir — sıfır
    # değil, hücre yok. AYLIK seri BOŞ bırakılır (grafikte "o ay işlem yok"
    # boşluğu doğrudur), alt kırılımlar yalnız kendi başlangıçlarından sonra
    # sıfırla doldurulur.
    for ad, kol in (("eb_kullanim", "eb_kullanim"), ("eb_odeme", "eb_odeme"),
                    ("eb_kullanim_uv", "eb_kullanim_uv"),
                    ("eb_odeme_uv", "eb_odeme_uv")):
        M[ad] = a[kol]
    for ad in ("eb_kullanim_gh", "eb_kullanim_bnk", "eb_kullanim_dgr"):
        s = a[ad]
        bas = s.first_valid_index()
        M[ad] = s.fillna(0.0).where(s.index >= bas) if bas is not None else s
    M["eb_net"] = M["eb_kullanim"].fillna(0.0) - M["eb_odeme"].fillna(0.0)

    # 12 aylık birikimli hâller
    for k in ("fin_giris", "dyy_giris", "portfoy_giris", "turev_giris",
              "diger_giris", "brut_yukumluluk", "yukumluluk_turevsiz",
              "yerlesik_varlik", "yuk_dyy",
              "yuk_port_hisse", "yuk_port_borc", "yuk_port_artik",
              "yuk_mevduat", "yuk_kredi", "yuk_diger_artik", "yuk_turev",
              "ticari_kredi_net", "kredi_bnk_uv_kul", "kredi_bnk_uv_ode",
              "kredi_dgr_uv_kul", "kredi_dgr_uv_ode", "kredi_gh_uv_kul",
              "kredi_gh_uv_ode", "kredi_bnk_kv", "kredi_dgr_kv"):
        M[k + "12"] = r12(M[k])

    # EUROBOND 12 AYLIK TOPLAMLARI: BOŞ AY = SIFIR AKIM ------------------
    # Bu bir hata düzeltmesidir, kozmetik değil. r12() eksik ayda NaN döndürür
    # (min_periods=12) — doğru kural, çünkü GERÇEKTEN eksik bir ay 12 aylık
    # toplamı sessizce küçültür. Ama eurobond serisinde boş ay eksik VERİ
    # değil, SIFIR AKIMDIR: A21 ihraç/itfa olmayan ayda hücre üretmiyor.
    # Ham NaN üzerinden r12 alınca 2010-01…2023-06 arasında 109 ay boş
    # kalıyordu; aynı bacak finansman ihtiyacına `fillna(0.0)` ile giriyordu.
    # SONUÇ (ölçüldü): Şekil 11'in yığılmış çubuğu ile kendi toplam çizgisi
    # 2023-04'te 18,2 milyar USD ayrışıyordu — çubukta eurobond bacağı yok,
    # çizgide vardı. İki taraf artık AYNI işlemi kullanıyor.
    # Aylık seriler (M["eb_odeme_uv"] vb.) BİLEREK NaN kalır: bir aylık çubuk
    # grafiğinde "o ay ihraç yoktu" ile "o ay sıfır ihraç edildi" aynı şeydir,
    # ama boş bırakmak dürüsttür.
    for k in ("eb_kullanim", "eb_odeme", "eb_kullanim_uv", "eb_odeme_uv",
              "eb_net"):
        M[k + "12"] = r12(M[k].fillna(0.0))
    return M


# ===========================================================================
# (4) KALİTELİ FİNANSMAN VE SICAK PARA
# ===========================================================================
def kalite_metrikleri(M: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """KALİTELİ FİNANSMAN = net DYY girişi + özel sektör net UV kredi kullanımı.

    'Kalite' burada bir değer yargısı değil VADE ve GERİ ÇAĞRILABİLİRLİK
    ölçüsüdür: doğrudan yatırım ile uzun vadeli kredi, portföy ve mevduattan
    daha yavaş çıkar. Tanım açıkça yazılır; okur katılmıyorsa bileşenleri
    grafikte ayrı ayrı görür.

    DÜZEY BAŞROLDÜR, ORAN YARDIMCIDIR: iki payda da tek başına kırılgan
    (payda sıfıra yaklaşınca oran patlıyor), bu yüzden oranlar eşik altında
    BOŞ bırakılır.
    """
    # Çerçeveyi birleştir: aşağıda çok sayıda sütun eklenecek ve pandas
    # parçalanmış blok yöneticisi için uyarı basıyor.
    M = M.copy()
    tani: dict = {}
    M["ozel_uv_kredi_net"] = ((M["kredi_bnk_uv_kul"] - M["kredi_bnk_uv_ode"])
                              + (M["kredi_dgr_uv_kul"] - M["kredi_dgr_uv_ode"]))
    M["kaliteli"] = M["dyy_giris"] + M["ozel_uv_kredi_net"]
    # SICAK PARA: portföy girişi (yükümlülük bacağı) + kısa vadeli kredi
    # yükümlülüğü + mevduat yükümlülüğü. Yükümlülük bacağı bilinçli: soru
    # "yabancı ne kadar hızlı çıkabilir", "yerleşik ne kadar dışarı çıktı" değil.
    M["sicak_para"] = (M["yuk_port_hisse"] + M["yuk_port_borc"]
                       + M["yuk_port_artik"] + M["kredi_bnk_kv"]
                       + M["kredi_dgr_kv"] + M["yuk_mevduat"])
    for k in ("ozel_uv_kredi_net", "kaliteli", "sicak_para"):
        M[k + "12"] = r12(M[k])

    # ÜÇ PAYDA, İKİSİ AYNI BÜYÜKLÜĞÜN İKİ TANIMI:
    #   (a) yükümlülük oluşumu (net, TÜREVLER DÂHİL) — hattın ana paydası,
    #   (b) aynı büyüklük TÜREVSİZ — türev bacağı 2014-01'de başlıyor ve son
    #       12 ayda −20,6 mia USD; paydayı küçültüp oranı yukarı savuruyor,
    #   (c) cari açık.
    # İkisi birden yayımlanır: okur hangi tanımı okuduğunu bilmeli.
    M["cari_acik12"] = (-M["cari12"]).clip(lower=0)
    M["kalite_pay_brut"] = _oran(M["kaliteli12"], M["brut_yukumluluk12"])
    M["kalite_pay_turevsiz"] = _oran(M["kaliteli12"], M["yukumluluk_turevsiz12"])
    M["kalite_pay_acik"] = _oran(M["kaliteli12"], M["cari_acik12"])

    for ad, kol, payda in (("brut", "kalite_pay_brut", "brut_yukumluluk12"),
                           ("turevsiz", "kalite_pay_turevsiz",
                            "yukumluluk_turevsiz12"),
                           ("acik", "kalite_pay_acik", "cari_acik12")):
        s = M[kol].dropna()
        p = M.loc[M.index >= "2010-01-01", kol]
        # 2014 SONRASI PENCERE: türev kalemi 2014-01'de eklendiği için "brüt"
        # paydanın TANIMI orada değişiyor. 2010 sonrası medyan iki tanımın
        # karışımıdır; tanım kırılmasından sonraki medyan da ayrıca verilir.
        p14 = M.loc[M.index >= TUREV_BAS, kol]
        tani[f"pay_{ad}_son"] = round(float(s.iloc[-1]), 1) if len(s) else None
        tani[f"pay_{ad}_son_donem"] = str(s.index[-1].date()) if len(s) else None
        tani[f"pay_{ad}_medyan_2010"] = (round(float(p.median()), 1)
                                         if p.notna().any() else None)
        tani[f"pay_{ad}_medyan_2014"] = (round(float(p14.median()), 1)
                                         if p14.notna().any() else None)
        # Eşik yüzünden BOŞ bırakılan ay sayısı: boşluk grafikte gerekçelensin.
        gecerli_payda = M[payda].notna() & (M[payda].abs() >= ORAN_PAYDA_ESIK)
        tani[f"pay_{ad}_bos_ay"] = int((M[payda].notna() & ~gecerli_payda).sum())
    tani["payda_esik_mn_usd"] = ORAN_PAYDA_ESIK
    tani["payda_notu"] = (
        "PAYDA BİR TANIM SEÇİMİDİR. Ana payda BPM6'nın net yükümlülük "
        "oluşumudur ve finansal türevleri (Q38, 2014-01'den itibaren) İÇERİR; "
        "türev bacağı negatif olabildiği için paydayı küçültür ve oranı yukarı "
        "savurur. Türevsiz sürüm aynı koşuda ayrıca hesaplanır. Kalem "
        "2014-01'de başladığından payda tanımı o tarihte KIRILIR; medyan hem "
        "2010 hem 2014 sonrası pencerede verilir.")
    for k, ad in (("brut_yukumluluk12", "payda_brut"),
                  ("yukumluluk_turevsiz12", "payda_turevsiz"),
                  ("yuk_turev12", "turev_bacagi")):
        s = M[k].dropna()
        tani[f"{ad}_12ay"] = round(float(s.iloc[-1]), 0) if len(s) else None
    for k, ad in (("kaliteli12", "kaliteli"), ("dyy_giris12", "dyy"),
                  ("ozel_uv_kredi_net12", "ozel_uv_kredi"),
                  ("sicak_para12", "sicak_para")):
        s = M[k].dropna()
        tani[f"{ad}_12ay"] = round(float(s.iloc[-1]), 0) if len(s) else None
    return M, tani


# ===========================================================================
# (5) UZUN VADELİ DIŞ BORÇ ÇEVİRME ORANI
# ===========================================================================
def rollover_metrikleri(M: pd.DataFrame, a: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """12 AYLIK toplamlar üzerinden çevirme oranı.

    AYLIK ORAN GÜRÜLTÜLÜ VE BÖLME PATLAMASI RİSKLİ: geri ödeme bacağı bazı
    aylarda çok küçük; oran tavana fırlıyor. Bu yüzden pay ve payda ayrı ayrı
    12 aya toplanır, sonra bölünür (12 aylık oranların ortalaması DEĞİL).

    İKİ FARKLI TANIM YAN YANA: TCMB'nin ODEROLL serisi KISA+UZUN vadeyi (K3/K4
    ayrıca tahvili) kapsar; burada türetilen oran YALNIZ UZUN VADELİ kredidir.
    Aynı seri gibi sunmak yanlış olur — fark ölçülür ve raporlanır.
    """
    # Çerçeveyi birleştir: aşağıda çok sayıda sütun eklenecek ve pandas
    # parçalanmış blok yöneticisi için uyarı basıyor.
    M = M.copy()
    tani: dict = {}
    for ad, kul, ode in (("bnk", "kredi_bnk_uv_kul12", "kredi_bnk_uv_ode12"),
                         ("dgr", "kredi_dgr_uv_kul12", "kredi_dgr_uv_ode12"),
                         ("gh", "kredi_gh_uv_kul12", "kredi_gh_uv_ode12")):
        M[f"roll_uv_{ad}"] = _oran(M[kul], M[ode], esik=ROLL_PAYDA_ESIK)
    # TCMB'nin kendi oranları (YÜZDE olarak yayımlanıyor) — olduğu gibi taşınır.
    for ad, kol in (("tcmb_bnk", "roll_bnk"), ("tcmb_dgr", "roll_dgr"),
                    ("tcmb_bnk_tahvil", "roll_bnk_tahvil"),
                    ("tcmb_dgr_tahvil", "roll_dgr_tahvil")):
        M[f"roll_{ad}"] = a[kol]

    for ad, bizim, tcmb in (("bnk", "roll_uv_bnk", "roll_tcmb_bnk"),
                            ("dgr", "roll_uv_dgr", "roll_tcmb_dgr")):
        s = M[bizim].dropna()
        t = M[tcmb].dropna()
        d = pd.DataFrame({"b": M[bizim], "t": M[tcmb]}).dropna()
        tani[f"roll_{ad}_son"] = round(float(s.iloc[-1]), 1) if len(s) else None
        tani[f"roll_{ad}_tcmb_son"] = round(float(t.iloc[-1]), 1) if len(t) else None
        p = M.loc[M.index >= "2010-01-01", bizim].dropna()
        if len(p):
            tani[f"roll_{ad}_min_2010"] = round(float(p.min()), 1)
            tani[f"roll_{ad}_maks_2010"] = round(float(p.max()), 1)
            tani[f"roll_{ad}_medyan_2010"] = round(float(p.median()), 1)
            tani[f"roll_{ad}_100_alti_ay"] = int((p < 100).sum())
            tani[f"roll_{ad}_ay"] = int(len(p))
        if len(d):
            tani[f"roll_{ad}_kapsam_farki_ort_puan"] = round(
                float((d["b"] - d["t"]).abs().mean()), 1)
            tani[f"roll_{ad}_kapsam_farki_son_puan"] = round(
                float(d["b"].iloc[-1] - d["t"].iloc[-1]), 1)
    tani["kapsam_notu"] = (
        "TCMB'nin çevirme oranı kısa+uzun vadeyi (K3/K4 ayrıca tahvili) "
        "kapsar; burada türetilen oran YALNIZ uzun vadeli krediyi ölçer. "
        "Fark kapsam farkıdır, veri hatası değildir.")
    tani["payda_esik_mn_usd"] = ROLL_PAYDA_ESIK
    return M, tani


# ===========================================================================
# (6) NET HATA VE NOKSAN
# ===========================================================================
def nhn_metrikleri(M: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """NHN büyüklüğü ÖLÇÜLÜR, yorumlanmaz.

    İki ölçü: (a) |12 aylık NHN| / |12 aylık cari denge|; (b) aylık NHN'nin
    12 aylık standart sapması ve mutlak değerinin 36 aylık yüzdelik dilimi.
    Yüzdelik dilim, "bu ay olağandışı mı" sorusuna tarihçenin kendisiyle
    cevap verir — sabit bir eşik uydurmak yerine.
    """
    # Çerçeveyi birleştir: aşağıda çok sayıda sütun eklenecek ve pandas
    # parçalanmış blok yöneticisi için uyarı basıyor.
    M = M.copy()
    tani: dict = {}
    M["nhn_std12"] = M["nhn"].rolling(12, min_periods=12).std()
    M["nhn_oran"] = _oran(M["nhn12"].abs(), M["cari12"].abs())
    M["nhn_yuzdelik36"] = (M["nhn"].abs()
                           .rolling(36, min_periods=36)
                           .apply(lambda x: float((x[:-1] < x[-1]).mean()) * 100.0,
                                  raw=True))
    s = M["nhn12"].dropna()
    if len(s):
        tani["nhn12_son"] = round(float(s.iloc[-1]), 0)
        tani["nhn12_min"] = round(float(s.min()), 0)
        tani["nhn12_min_donem"] = str(s.idxmin().date())
        tani["nhn12_maks"] = round(float(s.max()), 0)
        tani["nhn12_maks_donem"] = str(s.idxmax().date())
        # Mevcut değer tarihsel uçlara ne kadar yakın? (ölçüm, yorum değil)
        tani["nhn12_yuzdelik_tam_tarihce"] = round(
            float((s < s.iloc[-1]).mean()) * 100, 1)
    for k, ad in (("nhn_oran", "nhn_oran"), ("nhn_std12", "nhn_std12"),
                  ("nhn_yuzdelik36", "nhn_yuzdelik36")):
        v = M[k].dropna()
        tani[f"{ad}_son"] = round(float(v.iloc[-1]), 1) if len(v) else None
    return M, tani


# ===========================================================================
# (7) BRÜT DIŞ FİNANSMAN İHTİYACI — KİMLİKTEN TÜRETİLİR
# ===========================================================================
def finansman_ihtiyaci(M: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """İhtiyaç ve karşılanması, ödemeler dengesi kimliğinden BİREBİR türetilir.

    Kimlik (aylık, mn USD):  CA + KA + NHN = FA(rezerv hariç) + Rezerv
    Giriş işaretiyle:        −CA = fin_giris + KA + NHN − Rezerv

    Buna uzun vadeli anapara geri ödemesini İKİ TARAFA da eklersek:
        İHTİYAÇ  = −CA + UV anapara
        KAYNAK   = UV brüt kullanım + (fin_giris − UV net) + KA + NHN − Rezerv
    ve iki taraf birebir eşit olur. 'Rezerv' terimi negatif işaretle girer:
    rezerv ARTIŞI bir kaynak değil, kaynağın bir kısmının rezervde birikmesidir.

    BU EŞİTLİK BİR DENETİM DEĞİLDİR — TAUTOLOJİDİR. `diger_net_giris` bizzat
    `fin_giris − uv_net` diye tanımlandığı için kaynak tarafında uv_kullanim ve
    uv_anapara sadeleşir; geriye ana ödemeler dengesi kimliği kalır. Yani iki
    tarafın kapanması, anapara bacaklarının doğruluğu hakkında HİÇBİR ŞEY
    söylemez (ölçüldü: bacaklar bozulup uv_anapara12 86,8 → 386,8 milyar USD
    yapıldığında sapma yine 0,00). Anaparanın gerçek denetimi `dogrula()`
    içindeki mertebe kıyası ve bacak yoklamasıdır.

    UV anapara geri ödemesi = banka + reel sektör + genel hükümet uzun vadeli
    kredi geri ödemesi + uzun vadeli tahvil (eurobond) anapara ödemesi.
    Eurobond, kredi değil PORTFÖY yükümlülüğüdür; bu yüzden brüt kullanım
    tarafında da tahvil İHRACI ile birlikte yer alır — yalnız birini almak
    tabloyu bir bacak kadar şişirir.

    KAPSAM UYARISI: buraya YALNIZ UZUN VADELİ eurobond bacağı girer (A11 ihraç,
    A21 anapara). Şekil 12'nin çizdiği A1/A2 ise KISA VADEYİ DE içeren toplamdır
    ve son 12 ayda 57,9 / 34,7 milyar USD; uzun vadeli sürüm 55,7 / 29,3. Aynı
    etiketle iki farklı kapsamı yan yana koymak sahte bir sapma üretir, bu
    yüzden iki sürüm de `tani`ye yazılır ve sayfada ayrı adlandırılır.
    """
    # Çerçeveyi birleştir: aşağıda çok sayıda sütun eklenecek ve pandas
    # parçalanmış blok yöneticisi için uyarı basıyor.
    M = M.copy()
    tani: dict = {}
    M["uv_anapara"] = (M["kredi_bnk_uv_ode"] + M["kredi_dgr_uv_ode"]
                       + M["kredi_gh_uv_ode"] + M["eb_odeme_uv"].fillna(0.0))
    M["uv_kullanim"] = (M["kredi_bnk_uv_kul"] + M["kredi_dgr_uv_kul"]
                        + M["kredi_gh_uv_kul"] + M["eb_kullanim_uv"].fillna(0.0))
    M["uv_net"] = M["uv_kullanim"] - M["uv_anapara"]
    M["diger_net_giris"] = M["fin_giris"] - M["uv_net"]
    # İHTİYAÇ: manşet sunumda cari AÇIK (fazla varsa sıfır) + UV anapara.
    for k in ("uv_anapara", "uv_kullanim", "uv_net", "diger_net_giris"):
        M[k + "12"] = r12(M[k])
    M["ihtiyac12"] = M["cari_acik12"] + M["uv_anapara12"]
    # Kimlik sürümü: cari FAZLA dönemlerinde de kapanan hâl (−CA + UV anapara).
    M["ihtiyac_kimlik12"] = -M["cari12"] + M["uv_anapara12"]
    M["kaynak_kimlik12"] = (M["uv_kullanim12"] + M["diger_net_giris12"]
                            + M["sermaye_hesabi12"] + M["nhn12"]
                            - M["rezerv_akim12"])
    s = M["ihtiyac12"].dropna()
    if len(s):
        tani["ihtiyac12_son"] = round(float(s.iloc[-1]), 0)
        tani["ihtiyac12_donem"] = str(s.index[-1].date())
        for k, ad in (("cari_acik12", "cari_acik"), ("uv_anapara12", "uv_anapara"),
                      ("uv_kullanim12", "uv_kullanim"), ("uv_net12", "uv_net"),
                      ("eb_kullanim12", "eb_kullanim"), ("eb_odeme12", "eb_odeme"),
                      ("eb_net12", "eb_net"),
                      # UZUN VADELİ SÜRÜM: ihtiyaç tablosuna GİREN bacak budur.
                      # A1/A2 (yukarıdaki eb_kullanim/eb_odeme) kısa vadeyi de
                      # içerir; ikisi aynı etiketle sunulursa okur 86,8 milyar
                      # USD'lik anaparayı 5,4 milyar USD şaşarak tutturamaz.
                      ("eb_kullanim_uv12", "eb_kullanim_uv"),
                      ("eb_odeme_uv12", "eb_odeme_uv"),
                      # İhtiyaç bacaklarının kendisi: okur toplamı elle
                      # doğrulayabilsin diye hepsi ayrı ayrı yayımlanır.
                      ("kredi_bnk_uv_ode12", "anapara_bnk"),
                      ("kredi_dgr_uv_ode12", "anapara_dgr"),
                      ("kredi_gh_uv_ode12", "anapara_gh")):
            v = M[k].dropna()
            tani[f"{ad}_12ay"] = round(float(v.iloc[-1]), 0) if len(v) else None
        tani["eurobond_kapsam_notu"] = (
            "İki eurobond kapsamı vardır ve KARIŞTIRILMAMALIDIR: A1/A2 kısa "
            "vadeyi DE içeren toplam (Şekil 12), A11/A21 yalnız uzun vadeli "
            "(Şekil 11'in anapara ve brüt kullanım bacağı). Fark bir sapma "
            "değil, kapsam farkıdır.")
        tani["kimlik_tautoloji_notu"] = (
            "Alt paneldeki 'ihtiyaç = kaynak' eşitliği TAUTOLOJİDİR: kaynak "
            "tarafı ihtiyaç tarafından türetildiği için sapma tanım gereği "
            "sıfırdır ve anapara bacaklarını sınamaz. Anaparanın bağımsız "
            "denetimi haftalık dış borç ödeme takvimiyle yapılan mertebe "
            "kıyasıdır (bkz. uyarilar.json).")
        # İhtiyacın cari açıktan gelen payı: "açık kadar borç çevirmek" cümlesi
        # sayfada sayıya bağlansın.
        if float(s.iloc[-1]) != 0:
            tani["ihtiyacta_cari_acik_payi_yuzde"] = round(
                float(M["cari_acik12"].iloc[-1] / s.iloc[-1]) * 100, 1)
    return M, tani


# ===========================================================================
# (8) HAFTALIK DIŞ BORÇ ÖDEME TAKVİMİ
# ===========================================================================
def haftalik_metrikleri(h: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    tani: dict = {}
    if h.empty or "borc_odeme_top" not in h.columns:
        uyar("Haftalık dış borç ödeme serisi yok.")
        return pd.DataFrame(), tani
    H = pd.DataFrame(index=h.index)
    for k in ("borc_odeme_top", "borc_odeme_haz", "borc_odeme_dgr",
              "borc_odeme_tcmb"):
        H[k] = h[k]
        H[k + "_4h"] = h[k].rolling(4, min_periods=4).sum()
    H["borc_odeme_top_52h"] = h["borc_odeme_top"].rolling(52, min_periods=52).sum()
    s = H["borc_odeme_top"].dropna()
    if len(s):
        tani["son_hafta"] = str(s.index[-1].date())
        tani["son_hafta_mn_usd"] = round(float(s.iloc[-1]), 1)
        tani["son_4hafta_mn_usd"] = round(float(H["borc_odeme_top_4h"].dropna().iloc[-1]), 1)
        v = H["borc_odeme_top_52h"].dropna()
        tani["son_52hafta_mn_usd"] = round(float(v.iloc[-1]), 1) if len(v) else None
        for k, ad in (("borc_odeme_haz", "hazine"), ("borc_odeme_dgr", "diger"),
                      ("borc_odeme_tcmb", "tcmb")):
            x = H[k].dropna()
            tani[f"son_hafta_{ad}_mn_usd"] = round(float(x.iloc[-1]), 1) if len(x) else None
    return H, tani


# ===========================================================================
# (9) DOĞRULAMA
# ===========================================================================
def dogrula(M: pd.DataFrame, a: pd.DataFrame, G: pd.DataFrame,
            gsyh_tani: dict, H: pd.DataFrame) -> tuple[dict, list[str]]:
    """Bağımsız doğrulama. Durdurucu olanlar yanlış sayının yayına gitmesini keser.

    TAUTOLOJİ AYRIMI BU KATMANIN OMURGASIDIR. Bir "kimlik", sol tarafı sağ
    taraftan TÜRETİLMİŞSE hiçbir şeyi sınamaz: her koşuda 0,00 sapmayla geçer,
    girdiler ne kadar bozuk olursa olsun. Böyle kayıtlar `tautoloji=True` ile
    işaretlenir, DURDURUCU sayılmaz ve sayfada "sınandı" diye sunulmaz — yerine
    bağımsız kaynağa dayanan mertebe ve bacak denetimleri konur.
    """
    D: dict = {}
    dur: list[str] = []

    # (1) Ödemeler dengesi kimliği — giriş işaretiyle yazılmış hâli.
    _kimlik(D, "−CA = fin_giris + KA + NHN − Rezerv (aylık)", -M["cari"],
            M["fin_giris"] + M["sermaye_hesabi"] + M["nhn"] - M["rezerv_akim"],
            ESIK_KIMLIK_TOPLAM, True, dur)
    # (2) İşaret çevirmesi tek yerde: net giriş = yükümlülük oluşumu (net)
    #     − yerleşik varlık edinimi.
    _kimlik(D, "fin_giris = yükümlülük oluşumu (net) − yerleşik varlık edinimi",
            M["fin_giris"], M["brut_yukumluluk"] - M["yerlesik_varlik"],
            ESIK_KIMLIK_TOPLAM, True, dur)
    # (3) Yükümlülük yığınının SUNUM kimliği — TAUTOLOJİ olarak işaretlidir.
    # `yuk_port_artik` ve `yuk_diger_artik` ARTIK olarak tanımlı
    # (artık = toplam − bilinen alt kalemler), bu yüzden Σ = toplam cebirsel
    # olarak zorunludur ve hiçbir veri hatasını yakalayamaz. ÖLÇÜLDÜ:
    # `ay_mevduat_yuk` 100× yapılıp `ay_kredi_yuk` sıfırlandığında sapma yine
    # 0,00 çıkıyor. Kayıt, grafikteki yığının çizgiyle örtüştüğünü göstermek
    # için tutulur; DURDURUCU DEĞİLDİR ve "sınandı" diye sunulmaz.
    # Gerçek denetim (3b) ve (3c)'dedir.
    _kimlik(D, "sunum: Σ yığın kutuları = yükümlülük oluşumu (tautoloji)",
            M["yuk_dyy"] + M["yuk_port_hisse"] + M["yuk_port_borc"]
            + M["yuk_port_artik"] + M["yuk_mevduat"] + M["yuk_kredi"]
            + M["yuk_diger_artik"] + M["yuk_turev"], M["brut_yukumluluk"],
            ESIK_KIMLIK, False, dur, tautoloji=True)
    # (3b) GERÇEK DENETİM — İKİ AYRI EVDS TABLOSU ARASINDA.
    # Analitik sunumun Q25'i (Diğer Yatırımlar: net yükümlülük oluşumu) ile
    # ayrıntılı sunumun alt kalemleri (Q143 mevduat + Q157 kredi + Q184 ticari
    # kredi + Q203 SDR) karşılaştırılır. Bu bir ARTIK TANIMI DEĞİL: iki farklı
    # tabloya ait sayılar. Eşitlik BEKLENMEZ — ayrıntılı sunumda bu hatta
    # çekilmeyen "3.4.4 Diğer Yükümlülükler" kalemi var — ama artık BİR BANDA
    # sığmalı. Bir alt kalem düşerse ya da birimi kayarsa artık patlar.
    _artik_denetimi(D, a)
    # (3c) BACAK YOKLAMASI: yığının her kutusu son 24 ayda dolu mu?
    # Bir bacağın sessizce NaN'a düşmesi (seri adı değişti, EVDS kalemi
    # kaldırıldı) yığını kısaltır ama yukarıdaki tautoloji bunu görmez.
    _bacak_yoklamasi(D, M, "yığın bacakları (Şekil 05)",
                     ["yuk_dyy", "yuk_port_hisse", "yuk_port_borc",
                      "yuk_mevduat", "yuk_kredi", "yuk_turev"], dur,
                     baslangic=TUREV_BAS)
    # (4) Çekirdek köprüsü (12 aylık): manşet = çekirdek + altın + enerji.
    _kimlik(D, "manşet CA(12a) = çekirdek + altın net + enerji net", M["cari12"],
            M["cekirdek12"] + M["altin_net12"] + M["enerji_net12"],
            ESIK_KIMLIK_12, True, dur)
    # (5) Cari dengenin alt kalemleri (12 aylık).
    _kimlik(D, "CA(12a) = mal + hizmet + birincil + ikincil", M["cari12"],
            M["mal_denge12"] + M["hizmet_denge12"] + M["birincil_denge12"]
            + M["ikincil_denge12"], ESIK_KIMLIK_12, True, dur)
    # (6) Finansman tablosunun SUNUM kimliği — TAUTOLOJİ olarak işaretlidir.
    # `diger_net_giris = fin_giris − uv_net` ve `uv_net = uv_kullanim −
    # uv_anapara` olduğu için kaynak tarafında uv_kullanim ve uv_anapara
    # SADELEŞİYOR; geriye (1) numaralı kimliğin kendisi kalıyor. Yani bu
    # denetim ihtiyaç sayısını HİÇ sınamıyor. ÖLÇÜLDÜ: eurobond bacağı
    # silinip banka anaparası 10× yapıldığında uv_anapara12 86,8 → 386,8
    # milyar USD'ye çıkıyor, sapma yine 0,00. Kayıt, alt panelin görsel
    # olarak kapandığını göstermek için tutulur; DURDURUCU DEĞİLDİR.
    # İhtiyacın gerçek denetimi (6b) ve (6c)'dedir.
    _kimlik(D, "sunum: ihtiyaç(12a) = kaynak(12a) (tautoloji)",
            M["ihtiyac_kimlik12"], M["kaynak_kimlik12"], ESIK_KIMLIK_12,
            False, dur, tautoloji=True)
    # (6b) GERÇEK MERTEBE DENETİMİ — BAĞIMSIZ KAYNAK.
    # Uzun vadeli anapara geri ödemesi (aylık ödemeler dengesi) ile TCMB'nin
    # HAFTALIK dış borç ödeme takviminin 52 haftalık toplamı kıyaslanır.
    # Kapsamlar farklı (haftalık seri Hazine + TCMB + duyurulmuş diğer
    # ödemeleri kapsar, banka/reel sektör kredi itfalarının tamamını değil) →
    # EŞİTLİK BEKLENMEZ, ORAN bir BANTTA kalmalı.
    _mertebe_uv_anapara(D, M, H)
    # (6c) BACAK YOKLAMASI: ihtiyaç ve kaynak bacaklarının hepsi yerinde mi?
    _bacak_yoklamasi(D, M, "finansman ihtiyacı bacakları (Şekil 11)",
                     ["kredi_bnk_uv_ode", "kredi_dgr_uv_ode",
                      "kredi_gh_uv_ode", "kredi_bnk_uv_kul",
                      "kredi_dgr_uv_kul", "kredi_gh_uv_kul"], dur)
    # (7) Mal dengesi = ihracat − ithalat.
    _kimlik(D, "mal dengesi = ihracat − ithalat", M["mal_denge"],
            M["ihracat"] - M["ithalat"], ESIK_KIMLIK, False, dur)
    # (8) Türetilen çevirme oranının payı/paydası ile net kalem tutarlılığı.
    _kimlik(D, "banka UV net(12a) = kullanım − geri ödeme",
            r12(M["kredi_bnk_uv_net"]),
            M["kredi_bnk_uv_kul12"] - M["kredi_bnk_uv_ode12"],
            ESIK_KIMLIK_12, False, dur)

    # (9) GSYH mertebe denetimi — DURDURUCU. 1000× hata tam burada yakalanır.
    if gsyh_tani:
        gecti = bool(gsyh_tani.get("mertebe_gecti"))
        D["GSYH mertebe denetimi"] = {
            "trilyon_usd": gsyh_tani.get("gsyh4_trilyon_usd"),
            "bant": list(GSYH_BANT_TRN), "donem": gsyh_tani.get("gsyh4_donem"),
            "gecti": gecti, "durdurucu": True,
            "not": ("bin TL → /1000 → mn TL → /çeyrek ort. USDTRY → mn USD; "
                    "4 çeyreklik toplam YILLIK GSYH'dir."),
        }
        if not gecti:
            m = (f"MERTEBE DENETİMİ DÜŞTÜ: 4 çeyreklik GSYH "
                 f"{gsyh_tani.get('gsyh4_trilyon_usd')} trilyon USD, beklenen "
                 f"bant {GSYH_BANT_TRN}. Birim zinciri (bin TL → mn USD) "
                 "bozulmuş olabilir.")
            uyar(m)
            dur.append(m)

    # (10) KIYAS (durdurucu DEĞİL): türetilen UV oranı ile TCMB'nin ODEROLL'ü.
    d = pd.DataFrame({"b": M["roll_uv_bnk"], "t": M["roll_tcmb_bnk"]}).dropna()
    if len(d):
        D["kıyas: UV çevirme oranı ↔ TCMB ODEROLL (banka)"] = {
            "n": int(len(d)),
            "ortalama_mutlak_fark_puan": round(float((d["b"] - d["t"]).abs().mean()), 1),
            "son_bizim": round(float(d["b"].iloc[-1]), 1),
            "son_tcmb": round(float(d["t"].iloc[-1]), 1),
            "gecti": True, "durdurucu": False,
            "not": ("Bu bir doğrulama DEĞİL kıyastır: kapsamlar farklı (TCMB "
                    "kısa+uzun vade, biz yalnız uzun vade). Eşit çıkmaları "
                    "beklenmez; aynı seri gibi sunulmaları yanlış olur."),
        }
    # (11) Rezerv akımı ↔ stok (veri katmanında ölçüldü, burada devralınır).
    try:
        vd = json.loads((VERI / "veri_durum.json").read_text(encoding="utf-8"))
        if vd.get("isaret_rezerv"):
            D["işaret: rezerv akımı ↔ stok"] = dict(vd["isaret_rezerv"],
                                                    durdurucu=False)
    except Exception:
        pass
    return D, dur


# ===========================================================================
def kos() -> int:
    a = pd.read_csv(VERI / "aylik.csv", index_col=0, parse_dates=True)
    h = pd.read_csv(VERI / "haftalik.csv", index_col=0, parse_dates=True)
    c = pd.read_csv(VERI / "ceyreklik.csv", index_col=0, parse_dates=True)
    g = pd.read_csv(VERI / "gunluk.csv", index_col=0, parse_dates=True)

    s_ay = veri.son_ay(a)
    s_ceyrek = veri.son_ceyrek(c)
    s_hafta = veri.son_hafta(h)
    s_gun = veri.son_gun(g)
    print(f"Ödemeler dengesi — metrik · veri {ay_ad(s_ay)} · "
          f"GSYH {ceyrek_ad(s_ceyrek)} · haftalık {gun_ad(s_hafta)}")

    # VERİ KATMANININ UYARILARI BURADA DEVRALINIR. Devralınmazsa tazelik ve
    # "ESKİ ÖNBELLEK" uyarıları uyarilar.json'a hiç girmez ve sayfada
    # GÖRÜNMEZ — düzenin yasakladığı sessiz bayatlama.
    devir: list[str] = list(veri.uyarilar())
    try:
        vd = json.loads((VERI / "veri_durum.json").read_text(encoding="utf-8"))
        devir += list(vd.get("uyarilar") or [])
    except Exception as ex:
        uyar(f"VERİ KATMANI KAYDI OKUNAMADI ({type(ex).__name__}) — veri katmanının "
             "uyarıları devralınamadı; tazelik uyarıları bu koşuda GÖRÜNMEYEBİLİR.")
        vd = {}
    for u in devir:
        if u not in _UYARI:
            _UYARI.append(u)
            print("  ! (veri) " + u, flush=True)

    M = cari_metrikleri(a)
    M = finans_metrikleri(M, a)
    M, kalite_tani = kalite_metrikleri(M)
    M, roll_tani = rollover_metrikleri(M, a)
    M, nhn_tani = nhn_metrikleri(M)
    M, ihtiyac_tani = finansman_ihtiyaci(M)
    G, gsyh_tani = gsyh_metrikleri(M, c, g)
    H, hafta_tani = haftalik_metrikleri(h)
    D, dur = dogrula(M, a, G, gsyh_tani, H)

    # --- başrol büyüklükler ------------------------------------------------
    def _son(kol: str, ondalik: int = 0):
        s = M[kol].dropna()
        return (round(float(s.iloc[-1]), ondalik), str(s.index[-1].date())) \
            if len(s) else (None, None)

    cari12, cari12_t = _son("cari12")
    cek12, _ = _son("cekirdek12")
    makas12, _ = _son("makas12")
    basrol = {
        "cari12_mn_usd": cari12, "cari12_donem": cari12_t,
        "cekirdek12_mn_usd": cek12, "makas12_mn_usd": makas12,
        "altin_net12_mn_usd": _son("altin_net12")[0],
        "enerji_net12_mn_usd": _son("enerji_net12")[0],
        "fin_giris12_mn_usd": _son("fin_giris12")[0],
        "brut_yukumluluk12_mn_usd": _son("brut_yukumluluk12")[0],
        "yukumluluk_turevsiz12_mn_usd": _son("yukumluluk_turevsiz12")[0],
        "yuk_turev12_mn_usd": _son("yuk_turev12")[0],
        "yerlesik_varlik12_mn_usd": _son("yerlesik_varlik12")[0],
        "rezerv_akim12_mn_usd": _son("rezerv_akim12")[0],
        "cari_aylik_mn_usd": _son("cari")[0],
        "cekirdek_aylik_mn_usd": _son("cekirdek")[0],
    }

    # --- kırılganlık bayrakları (olgu var mı?) -----------------------------
    bayrak = {
        "cari_acik_var": bool((cari12 or 0) < 0),
        "cekirdek_fazla_var": bool((cek12 or 0) > 0),
        "rezerv_artiyor": bool((basrol["rezerv_akim12_mn_usd"] or 0) > 0),
        "roll_bnk_100_alti": bool((roll_tani.get("roll_bnk_son") or 0) < 100),
        "roll_dgr_100_alti": bool((roll_tani.get("roll_dgr_son") or 0) < 100),
        "kalite_orani_bos": bool(kalite_tani.get("pay_acik_son") is None),
        "turev_kalemi_var": bool(a["turev_yuk"].dropna().shape[0] > 0),
    }

    # --- yazım -------------------------------------------------------------
    M.to_csv(VERI / "metrik.csv")
    if not G.empty:
        G.to_csv(VERI / "ceyrek_metrik.csv")
    if not H.empty:
        H.to_csv(VERI / "haftalik_metrik.csv")

    ozet = {
        # DÖRT AYRI DÖNEM ÇIPASI. Tek etiket kullanmak, 145 gün geride kalan
        # GSYH oranını "bu ayın sayısı" gibi gösterirdi.
        "son_ay": s_ay.strftime("%Y-%m-%d"),
        "son_ceyrek": s_ceyrek.strftime("%Y-%m-%d"),
        "son_hafta": s_hafta.strftime("%Y-%m-%d"),
        "son_gun": s_gun.strftime("%Y-%m-%d"),
        # Grafik ve metin katmanı eşikleri BURADAN okur — iki yerde iki farklı
        # sayı dolaşmasın.
        "esik": {
            "oran_payda_mn_usd": ORAN_PAYDA_ESIK,
            "roll_payda_mn_usd": ROLL_PAYDA_ESIK,
            "pencere_ay": PENCERE,
            "gsyh_bant_trn": list(GSYH_BANT_TRN),
        },
        "basrol": basrol,
        "bayrak": bayrak,
        "gsyh": gsyh_tani,
        "kalite": kalite_tani,
        "rollover": roll_tani,
        "nhn": nhn_tani,
        "ihtiyac": ihtiyac_tani,
        "haftalik": hafta_tani,
        "dogrulama": D,
        "tanim_notu": (
            "Bu hat finans hesabı olarak ANALİTİK sunumun REZERV HARİÇ kalemini "
            "(TP.ODANA6.Q13) kullanır. Ayrıntılı sunumun TP.ODEAYRSUNUM6.Q101 "
            "kalemi rezervi İÇERİR; köprü Q101 = Q13 + Q33'tür ve ikisi aynı "
            "grafikte 'finans hesabı' diye yan yana konulamaz."),
        "isaret_notu": (
            "BPM6: finans hesabı = net varlık edinimi − net yükümlülük "
            "oluşumu; POZİTİF = sermaye ÇIKIŞI. Giriş gösterimi için işaret "
            "metrik katmanında TEK YERDE çevrilir. Rezerv akımı POZİTİF = "
            "rezerv ARTIŞI (stokla sınandı)."),
        "kalite_notu": (
            "'Kaliteli finansman' bir değer yargısı değil VADE ölçüsüdür: net "
            "doğrudan yatırım girişi + özel sektörün net uzun vadeli kredi "
            "kullanımı. Oranların paydası küçüldüğünde oran patladığı için "
            "DÜZEY başroldür; oran payda eşiğin altındayken boş bırakılır."),
        "fisher_not": (
            "Depo kuralı: reel getiri Fisher ile hesaplanır ((1+i)/(1+π)−1), "
            "basit çıkarmayla değil. Bu hat USD cinsi akım büyüklükleriyle "
            "çalışır ve şu an bir reel faiz serisi yayımlamaz; kural, "
            "metrik.py'deki fisher_reel() ile kodda hazır durur."),
        "revizyon_notu": (
            "Ödemeler dengesi TCMB'nin revizyon politikasına tabidir: son "
            "3–12 ay rutin olarak, yıllık revizyonlarda daha geriye dönük "
            "değişir. Çekirdek cari denge TÜİK dış ticaret istatistiklerinden "
            "beslenir ve TÜİK revizyonu buraya da yansır. Yayımlanmış bir "
            "sayının bir sonraki koşuda farklı çıkması NORMALDİR."),
        "uyarilar": list(_UYARI),
    }
    (VERI / "metrik_ozet.json").write_text(
        json.dumps(ozet, ensure_ascii=False, indent=1), encoding="utf-8")
    (PROJE / "uyarilar.json").write_text(json.dumps(
        {"tarih": s_ay.strftime("%Y-%m-%d"),
         "kosum": pd.Timestamp.today().strftime("%Y-%m-%d"),
         "uyarilar": list(_UYARI),
         # DENETİM SAYIMIYLA YAYIMLANAN KÜME AYNI OLMALI. Eskiden sayfa "21
         # denetim çalıştı" diyor ama uyarilar.json yalnız bu katmanın 11
         # kaydını taşıyordu: veri katmanının 16 kimliği hiçbir yayımlanan
         # dosyada yoktu (veri_durum.json siteye kopyalanmıyor), buna karşılık
         # yayımlanan 11 kaydın 6'sı sayıma girmiyordu. Okur 21'i hiçbir
         # yoldan doğrulayamıyordu. İki katman da BURADA yayımlanır ve
         # ozet_uret.py sayımı bu iki sözlükten yapar.
         "dogrulama": D, "dogrulama_veri": (vd.get("kimlik") or {})},
        ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"  yazıldı: data/metrik.csv ({M.shape[0]}x{M.shape[1]}), "
          f"data/ceyrek_metrik.csv ({G.shape[0]}x{G.shape[1]}), "
          f"data/haftalik_metrik.csv ({H.shape[0]}x{H.shape[1]})")
    for ad, r in D.items():
        if "gecti" in r and "maks_fark" in r:
            print(f"    kimlik {'✓' if r['gecti'] else '✗'} {ad}: n={r['n']}, "
                  f"maks {r['maks_fark']:,.2f} {r['birim']}")
    print(f"    12 aylık cari denge {cari12:,.0f} mn USD · çekirdek "
          f"{cek12:,.0f} · makas {makas12:,.0f}")
    print(f"    kaliteli finansman (12a) {kalite_tani.get('kaliteli_12ay'):,.0f} "
          f"mn USD · UV çevirme banka %{roll_tani.get('roll_bnk_son')} · "
          f"reel sektör %{roll_tani.get('roll_dgr_son')}")
    print(f"    CA/GSYH %{gsyh_tani.get('cari_gsyh_son')} "
          f"({gsyh_tani.get('cari_gsyh_donem')}) · 4 çeyreklik GSYH "
          f"{gsyh_tani.get('gsyh4_trilyon_usd')} trn USD")
    if _UYARI:
        print(f"\n[{len(_UYARI)} uyarı]")
    if dur:
        for x in dur:
            print("  ✗ " + x)
        raise SystemExit(
            "DUR: doğrulama düştü. Yanlış sayı yayına gitmesin diye grafik ve "
            "ozet üretilmiyor. Ayrıntı: uyarilar.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(kos())
