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
# %575'e fırlıyor; brüt yükümlülük paydasıyla 2010 sonrası bant
# %−1022 … %+2149; cari açık paydasıyla %−1063 … %+245. Sebep veri hatası
# değil, paydanın sıfıra yaklaşması ve İŞARET DEĞİŞTİRMESİ. 10.000 mn USD
# (10 milyar) eşiği, 12 aylık brüt yükümlülük oluşumunun tarihsel medyanının
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
            durdur: bool, dur_liste: list[str], birim: str = "mn USD") -> None:
    d = pd.DataFrame({"s": sol, "r": sag}).dropna()
    if d.empty:
        uyar(f"KİMLİK: '{ad}' sınanamadı — girdi serileri kesişmiyor.")
        return
    fark = (d["s"] - d["r"]).abs()
    gecti = bool(fark.max() <= esik)
    rapor[ad] = {"n": int(len(d)), "maks_fark": float(fark.max()),
                 "maks_tarih": str(fark.idxmax().date()),
                 "son_fark": float(fark.iloc[-1]), "birim": birim,
                 "esik": esik, "gecti": gecti, "durdurucu": bool(durdur)}
    if not gecti:
        m = (f"KİMLİK BOZUK: {ad} — en büyük sapma {fark.max():,.2f} {birim} "
             f"({fark.idxmax():%m.%Y}), eşik {esik} {birim}.")
        uyar(m)
        if durdur:
            dur_liste.append(m)


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

    # --- net giriş (rezerv HARİÇ) -----------------------------------------
    M["fin_giris"] = -a["fin_hesabi"]

    # --- kalem bazında net giriş (yükümlülük − varlık) ---------------------
    M["dyy_giris"] = a["dyy_yuk"] - a["dyy_varlik"]
    M["portfoy_giris"] = a["port_yuk"] - a["port_varlik"]
    M["turev_giris"] = tur_y - tur_v
    M["diger_giris"] = a["diger_yuk"] - a["diger_varlik"]

    # --- brüt bacaklar -----------------------------------------------------
    # Brüt yükümlülük oluşumu = yabancının Türkiye'ye yönelttiği brüt akım.
    # Yerleşiklerin dış varlık edinimi = yurt içinden dışarı çıkan akım.
    M["brut_yukumluluk"] = (a["dyy_yuk"] + a["port_yuk"] + tur_y + a["diger_yuk"])
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
    # SEYREK SERİ UYARISI: alt kırılımlar (A112 genel hükümet, A114 diğer
    # sektör) ihraç OLMAYAN ayda BOŞ gelir. Toplam serisi (A1) dolu olduğu
    # için toplamlar A1/A2 üzerinden kurulur; alt kırılımlar yalnız grafikte
    # ve yalnız kendi başlangıçlarından sonra sıfırla doldurulur.
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
              "diger_giris", "brut_yukumluluk", "yerlesik_varlik", "yuk_dyy",
              "yuk_port_hisse", "yuk_port_borc", "yuk_port_artik",
              "yuk_mevduat", "yuk_kredi", "yuk_diger_artik", "yuk_turev",
              "ticari_kredi_net", "kredi_bnk_uv_kul", "kredi_bnk_uv_ode",
              "kredi_dgr_uv_kul", "kredi_dgr_uv_ode", "kredi_gh_uv_kul",
              "kredi_gh_uv_ode", "kredi_bnk_kv", "kredi_dgr_kv",
              "eb_kullanim", "eb_odeme", "eb_kullanim_uv", "eb_odeme_uv",
              "eb_net"):
        M[k + "12"] = r12(M[k])
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

    # Payda (a): brüt yükümlülük oluşumu. Payda (b): cari açık.
    M["cari_acik12"] = (-M["cari12"]).clip(lower=0)
    M["kalite_pay_brut"] = _oran(M["kaliteli12"], M["brut_yukumluluk12"])
    M["kalite_pay_acik"] = _oran(M["kaliteli12"], M["cari_acik12"])

    for ad, kol, payda in (("brut", "kalite_pay_brut", "brut_yukumluluk12"),
                           ("acik", "kalite_pay_acik", "cari_acik12")):
        s = M[kol].dropna()
        p = M.loc[M.index >= "2010-01-01", kol]
        tani[f"pay_{ad}_son"] = round(float(s.iloc[-1]), 1) if len(s) else None
        tani[f"pay_{ad}_son_donem"] = str(s.index[-1].date()) if len(s) else None
        tani[f"pay_{ad}_medyan_2010"] = (round(float(p.median()), 1)
                                         if p.notna().any() else None)
        # Eşik yüzünden BOŞ bırakılan ay sayısı: boşluk grafikte gerekçelensin.
        gecerli_payda = M[payda].notna() & (M[payda].abs() >= ORAN_PAYDA_ESIK)
        tani[f"pay_{ad}_bos_ay"] = int((M[payda].notna() & ~gecerli_payda).sum())
    tani["payda_esik_mn_usd"] = ORAN_PAYDA_ESIK
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

    UV anapara geri ödemesi = banka + reel sektör + genel hükümet uzun vadeli
    kredi geri ödemesi + uzun vadeli tahvil (eurobond) anapara ödemesi.
    Eurobond, kredi değil PORTFÖY yükümlülüğüdür; bu yüzden brüt kullanım
    tarafında da tahvil İHRACI (A11) ile birlikte yer alır — yalnız birini
    almak tabloyu bir bacak kadar şişirir.
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
                      ("eb_net12", "eb_net")):
            v = M[k].dropna()
            tani[f"{ad}_12ay"] = round(float(v.iloc[-1]), 0) if len(v) else None
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
            gsyh_tani: dict) -> tuple[dict, list[str]]:
    """Bağımsız doğrulama. Durdurucu olanlar yanlış sayının yayına gitmesini keser."""
    D: dict = {}
    dur: list[str] = []

    # (1) Ödemeler dengesi kimliği — giriş işaretiyle yazılmış hâli.
    _kimlik(D, "−CA = fin_giris + KA + NHN − Rezerv (aylık)", -M["cari"],
            M["fin_giris"] + M["sermaye_hesabi"] + M["nhn"] - M["rezerv_akim"],
            ESIK_KIMLIK_TOPLAM, True, dur)
    # (2) İşaret çevirmesi tek yerde: net giriş = brüt yükümlülük − yerleşik varlık.
    _kimlik(D, "fin_giris = brüt yükümlülük − yerleşik varlık edinimi",
            M["fin_giris"], M["brut_yukumluluk"] - M["yerlesik_varlik"],
            ESIK_KIMLIK_TOPLAM, True, dur)
    # (3) Yükümlülük kırılımı toplamı brüt yükümlülüğe eşit olmalı.
    _kimlik(D, "Σ yükümlülük kalemleri = brüt yükümlülük oluşumu",
            M["yuk_dyy"] + M["yuk_port_hisse"] + M["yuk_port_borc"]
            + M["yuk_port_artik"] + M["yuk_mevduat"] + M["yuk_kredi"]
            + M["yuk_diger_artik"] + M["yuk_turev"], M["brut_yukumluluk"],
            ESIK_KIMLIK, True, dur)
    # (4) Çekirdek köprüsü (12 aylık): manşet = çekirdek + altın + enerji.
    _kimlik(D, "manşet CA(12a) = çekirdek + altın net + enerji net", M["cari12"],
            M["cekirdek12"] + M["altin_net12"] + M["enerji_net12"],
            ESIK_KIMLIK_12, True, dur)
    # (5) Cari dengenin alt kalemleri (12 aylık).
    _kimlik(D, "CA(12a) = mal + hizmet + birincil + ikincil", M["cari12"],
            M["mal_denge12"] + M["hizmet_denge12"] + M["birincil_denge12"]
            + M["ikincil_denge12"], ESIK_KIMLIK_12, True, dur)
    # (6) Finansman ihtiyacı tablosu birebir kapanmalı.
    _kimlik(D, "ihtiyaç(12a) = kaynak(12a)", M["ihtiyac_kimlik12"],
            M["kaynak_kimlik12"], ESIK_KIMLIK_12, True, dur)
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
        uyar(f"veri_durum.json okunamadı ({ex}) — veri katmanının uyarıları "
             "devralınamadı. Tazelik uyarıları bu koşuda GÖRÜNMEYEBİLİR.")
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
    D, dur = dogrula(M, a, G, gsyh_tani)

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
         "uyarilar": list(_UYARI), "dogrulama": D},
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
