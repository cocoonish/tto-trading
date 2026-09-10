# -*- coding: utf-8 -*-
"""Kredi & parasal büyüklükler — ozet.json üretimi.

Sayfa metnindeki OYNAK her sayı buradan beslenir (CLAUDE.md kural 5):
MDX'te <Deger proje="kredi-parasal" anahtar="..." ondalik={1}>statik yedek</Deger>.
Tarihsel/metodolojik sabitler (formüller, kurum tanımları, kod listeleri) sayfada
STATİK kalır — onlar veri tazelendikçe değişmez.

Bütün değerler data/ altındaki ÜRETİLMİŞ dosyalardan OKUNUR; elle sayı yazılmaz.
Bir değer kaynakta yoksa anahtar ATLANIR ve stderr'e uyarı basılır — eksik bir
sayının yerine MDX'teki statik yedek görünür, uydurma bir değer değil.

TEK İSTİSNA — SAYFANIN ADIYLA ÇAĞIRDIĞI SAAT ANAHTARLARI (`SAYFA_SAATLERI`).
Onlar atlanmaz: ölçülemiyorsa BOŞ ("—") yazılır. Sebep 08.09.2026'da ölçüldü —
sayfanın adıyla çağırdığı bir anahtar düştüğünde yayın kapısı ENGEL verir ve
site durur; bir SAAT için donmuş statik yedek zaten yanlış cevaptır, çünkü
okura ölçülmemiş bir günü ölçülmüş gibi gösterir.

Koşum:  python3 ozet_uret.py   (önce veri.py → metrik.py → grafik.py)
"""
from __future__ import annotations

import datetime as dt
import json
import sys

import pandas as pd

from veri import (PROJE, VERI, AY_TR, AY_KISA, sekil_saatleri,
                  tazelik_tolerans)

O: dict = {}


def uyar(m: str) -> None:
    print(f"UYARI: {m}", file=sys.stderr)


def tr_sayi(v, ondalik: int = 1) -> str:
    """Türkçe sayı biçimi (binlik nokta, ondalık virgül).

    ozet.json'daki METİN anahtarları (kapsam/uyarı cümleleri) sayfaya olduğu
    gibi basılır; Python'un varsayılan `repr`i oraya "0.0" ve "33243.29" gibi
    İngilizce biçimler taşırdı.
    """
    if v is None:
        return "—"
    try:
        m = f"{float(v):,.{ondalik}f}"
    except (TypeError, ValueError):
        return str(v)
    # Sayfa tipografisi ASCII tire değil eksi işareti (U+2212) kullanır.
    return (m.replace(",", "\u00a0").replace(".", ",").replace("\u00a0", ".")
             .replace("-", "\u2212"))


OLCULEMEDI = "—"

# SAYFANIN ADIYLA ÇAĞIRDIĞI SAAT ANAHTARLARI — HER koşuda yazılır.
#
# Ölçüm katmanı bir sütunu yükleyemediğinde o sütunun saatini ATLIYOR
# (`metrik.anahtar_saati` yalnız dolu anahtarı yazar, `pka_tarih` serisi
# gelmezse None kalır) ve bu, "uydurma yok" ilkesinin doğru yarısı. Ama
# 08.09.2026'da DİBS'te ölçülen yarısı eksikti: SAYFANIN ADIYLA ÇAĞIRDIĞI bir
# anahtar düştüğünde yayın kapısı onu ENGEL sayar (doğru — donmuş bir yedek
# yayımlanmamalı) ve site durur; o gün yayın ÜÇ KEZ düştü. Kural o gün
# yazıldı ve burada uygulanıyor: ölçülebiliyorsa kendi tarihiyle,
# ölçülemiyorsa BOŞ ("—"); atlanmaz.
#
# Kapsam elle tutulmuyor: `duman.py` bu kümenin sayfanın gerçekten çağırdığı
# saat anahtarlarıyla ÖRTÜŞTÜĞÜNÜ sınar — sayfaya yeni bir saat eklenip küme
# güncellenmezse orada düşer, yayın kapısında değil.
SAYFA_SAATLERI = ("aofm_tarih", "dol_tarih", "gun_kur_tarih", "pka_tarih",
                  "spread_aofm_tarih", "zk_ima_oran_tarih")


def sayfa_saatlerini_tamamla(O: dict) -> list:
    """Ölçülemeyen saat anahtarını BOŞ yazar; hangileri boş kaldığını döndürür."""
    bos = [a for a in SAYFA_SAATLERI if not isinstance(O.get(a), str)]
    for a in bos:
        O[a] = OLCULEMEDI
    return bos


def koy(anahtar: str, deger, ondalik: int | None = 2) -> None:
    if deger is None or (isinstance(deger, float) and pd.isna(deger)):
        uyar(f"'{anahtar}' kaynakta yok — anahtar atlandı.")
        return
    if ondalik is None:
        O[anahtar] = deger
    elif ondalik == 0:
        O[anahtar] = int(round(float(deger)))
    else:
        O[anahtar] = round(float(deger), ondalik)


# TCMB, Haftalık Para ve Banka İstatistiklerini referans Cuma'yı izleyen
# PERŞEMBE yayımlar (6 gün). Aylık para ve banka istatistikleri ile Banka
# Kredileri Eğilim Anketi dönem sonundan ~51 gün sonra gelir. Yayım gecikmesi
# bu takvimden ölçülür; "veri kaç gün önce yayımlandı" cümlesi buradan kurulur.
HAFTALIK_YAYIM_GUN = 6
AYLIK_YAYIM_GUN = 51


def _is_gunu(t: dt.date) -> dt.date:
    while t.weekday() >= 5:
        t += dt.timedelta(days=1)
    return t


def haftalik_yayim(son: pd.Timestamp) -> dt.date:
    return _is_gunu((son + pd.Timedelta(days=HAFTALIK_YAYIM_GUN)).date())


def aylik_yayim(son_ay: pd.Timestamp) -> dt.date:
    sonu = (son_ay + pd.offsets.MonthEnd(1)).date()
    return _is_gunu(sonu + dt.timedelta(days=AYLIK_YAYIM_GUN))


def ceyrek_yayim(son_ceyrek: pd.Timestamp) -> dt.date:
    sonu = (son_ceyrek + pd.offsets.MonthEnd(3)).date()
    return _is_gunu(sonu + dt.timedelta(days=AYLIK_YAYIM_GUN))


def gun_tr(t: pd.Timestamp) -> str:
    return f"{t.day} {AY_TR[t.month]} {t.year}"


def bayat_karari(yayim_gecikme_gun, uyarilar: list[str]) -> dict:
    """Bayat bayrağı ve okura basılan cümlesi — AĞA ÇIKMAZ, sahte girdiyle koşar.

    Karar `main()`in İÇİNDE duruyordu, yani hiçbir kapı onu koşturamıyordu:
    tek sınayıcısı `bayatlik_sinavi.py` ve o dosya `duman.py` adını taşımadığı
    için `guncelle.py` onu HİÇ görmüyor. Üstelik o sınav deponun O GÜNKÜ
    verisini ve DUVAR SAATİNİ okuduğu için bayrağın DOĞRU açıldığı her gün
    düşüyordu (10.09.2026'da ölçüldü: bugünkü ağaçta bayat=True ve sınav
    "SINAV DÜŞTÜ (ters yön)" diyor). Ağa çıkmayan iş ayrı fonksiyona çıkar;
    duman sınaması onu KENDİ çerçevesiyle çağırır. Kardeş hat Fonlama'da aynı
    ayrım 09.09.2026'da yapılmıştı; bu hat o düzeltmeyi almamıştı.
    """
    tol_hafta = tazelik_tolerans("haftalik")
    sebep: list[str] = []
    if (yayim_gecikme_gun or 0) > tol_hafta:
        sebep.append(f"haftalık bacak yayım tarihinden {yayim_gecikme_gun} gün "
                     f"geride (tolerans {tol_hafta} gün)")
    izler = [u for u in uyarilar
             if u.startswith(("TAZELİK", "ESKİ ÖNBELLEK", "BAYAT"))]
    if izler:
        sebep.append(f"veri katmanı {len(izler)} tazelik/önbellek "
                     "uyarısı bastı")
    return {
        "bayat": bool(sebep),
        "bayat_tolerans_hafta": tol_hafta,
        "bayat_cumlesi": (
            "BAYAT VERİ: " + "; ".join(sebep)
            + ". Sayfadaki sayılar bu koşuda İLERLEMEMİŞ olabilir."
            if sebep else
            "Veri taze: yayım gecikmesi tolerans içinde, tazelik uyarısı yok."),
    }


def main() -> int:
    m = json.loads((VERI / "metrik_ozet.json").read_text(encoding="utf-8"))
    uy = json.loads((PROJE / "uyarilar.json").read_text(encoding="utf-8"))
    try:
        vd = json.loads((VERI / "veri_durum.json").read_text(encoding="utf-8"))
    except Exception as ex:
        uyar(f"veri_durum.json okunamadı ({ex}) — veri katmanının uyarıları "
             "sayıma girmiyor.")
        vd = {}
    s_h = pd.Timestamp(m["son_hafta"])
    s_g = pd.Timestamp(m["son_gun"])
    s_a = pd.Timestamp(m["son_ay"])
    s_c = pd.Timestamp(m["son_ceyrek"])

    # ---------------------------------------------------------------- dönem
    O["_tarih"] = s_h.strftime("%d.%m.%Y")
    O["hafta"] = gun_tr(s_h)
    O["hafta_kisa"] = f"{s_h.day} {AY_KISA[s_h.month]} {s_h.year}"
    # GÜNLÜK SAAT, BAĞLAYICI BACAKTIR (veri.son_gun — GUNLUK_AILE'ye bak):
    # bütün günlük ailelerin dolu olduğu son iş günü. Ailelerin kendi günleri
    # ayrıca yazılır, çünkü kur bacağı ERTESİ iş günü için ilan edilir ve
    # bağlayıcı günün iki iş günü ilerisinde durur; sayfa ikisini birlikte
    # söylemezse taze bacağı gizlemiş ya da bayat bacağı taze göstermiş olur.
    O["gun_tarih"] = s_g.strftime("%d.%m.%Y")
    O["gun"] = gun_tr(s_g)
    for aile, iso in (m.get("son_gun_aile") or {}).items():
        O[f"gun_{aile}_tarih"] = pd.Timestamp(iso).strftime("%d.%m.%Y")
    O["ay_tarih"] = s_a.strftime("%m.%Y")
    O["ay"] = f"{AY_TR[s_a.month]} {s_a.year}"
    O["ceyrek"] = f"{s_c.year}-Ç{(s_c.month - 1) // 3 + 1}"
    onc = s_h - pd.Timedelta(weeks=1)
    O["onceki_hafta"] = gun_tr(onc)
    cipa13 = s_h - pd.Timedelta(weeks=13)
    O["cipa_13h"] = gun_tr(cipa13)
    O["kosum_tarihi"] = dt.date.today().strftime("%d.%m.%Y")
    yt = haftalik_yayim(s_h)
    O["yayim_tarihi"] = yt.strftime("%d.%m.%Y")
    O["yayim_gecikme_gun"] = (dt.date.today() - yt).days
    O["ay_yayim_tarihi"] = aylik_yayim(s_a).strftime("%d.%m.%Y")
    O["ceyrek_yayim_tarihi"] = ceyrek_yayim(s_c).strftime("%d.%m.%Y")

    # ---------------------------------------------------------------- yöntem
    O["arindirma_yontem"] = m.get("arindirma_yontem")
    O["kur_serisi"] = m.get("kur_serisi")
    O["pencere_hafta"] = m.get("pencere_hafta")
    koy("yillik_us", m.get("yillik_us"), 0)
    O["sepet_kaynak"] = m.get("sepet_kaynak_son")
    O["sepet_olculdu"] = (m.get("sepet_kaynak_son") == "olculdu")
    O["kur_gun_kaynak"] = m.get("kur_gun_kaynak_son")
    st = m.get("sepet_tahmin") or {}
    koy("sepet_tahmin_artik_std", st.get("artik_std_pct"), 3)
    koy("sepet_tahmin_artik_maks", st.get("artik_maks_pct"), 3)
    koy("sepet_tahmin_n", st.get("n"), 0)
    # TAHMİN ARTIĞININ BÜYÜME KARŞILIĞI. Artık yalnız kur düzeyinde
    # yayımlandığında okur "kur seçimi önemsiz" sonucuna varıyor; asıl
    # belirsizlik bu bantta ve ölçülmüş seçenekler tablosundan büyük.
    kd = m.get("kur_duyarlilik") or {}
    koy("sepet_tahmin_buyume_bandi_pp", kd.get("sepet_tahmin_buyume_bandi_pp"), 2)
    koy("g_ar_13y_tahmin_alt", kd.get("g_ar_13y_tahmin_alt"))
    koy("g_ar_13y_tahmin_ust", kd.get("g_ar_13y_tahmin_ust"))
    koy("sepet_tahmin_hafta", kd.get("tahmin_hafta"), 0)
    # Çıpa seçimi: pencere DIŞI çıpalar (sayfa çıpanın keyfî olduğunu
    # söylüyordu ama büyüklüğünü ölçmüyordu).
    koy("g_cipa_yilbasi_13y", kd.get("g_cipa_yilbasi_13y"))
    koy("g_cipa_52hafta_13y", kd.get("g_cipa_52hafta_13y"))
    koy("cipa_yayilim_pp", kd.get("cipa_yayilim_pp"), 2)
    if kd.get("cipa_yilbasi_tarih"):
        O["cipa_yilbasi_tarih"] = gun_tr(pd.Timestamp(kd["cipa_yilbasi_tarih"]))
    if kd.get("cipa_52hafta_tarih"):
        O["cipa_52hafta_tarih"] = gun_tr(pd.Timestamp(kd["cipa_52hafta_tarih"]))

    # ---------------------------------------------------------------- kredi
    for a in ("g_ar_13y", "g_ham_13y", "g_ar_usd_13y", "g_cipa_13y", "g_tl_13y",
              "g_yp_ar_13y", "kur_etkisi_13y", "g_ar_52", "g_ham_52", "g_tl_52",
              "g_yp_ar_52", "cipa_zincir_farki", "usd_sepet_farki_13y",
              "g_tuketici_13y", "g_ticari_13y", "g_kobi_13y", "g_bkk_13y",
              "g_konut_13y", "g_tasit_13y", "g_ihtiyac_13y",
              "g_kurumsal_kart_13y", "g_finansal_13y",
              "yp_pay", "npl", "npl_tuketici", "npl_ticari", "karsilik_orani",
              "kredi_mevduat", "uzun_g_ar_13y", "mevduat_sektor_toplam_mlr"):
        koy(a, m.get(a))
    koy("kredi_toplam_mlr", m.get("kredi_toplam"), 0)
    koy("kredi_tl_mlr", m.get("kredi_tl_mlr"), 0)
    koy("kredi_yp_mlr", m.get("kredi_yp_mlr"), 0)
    koy("kredi_toplam_trn", (m.get("kredi_toplam") or 0) / 1000, 1)
    # TÜRETİLMİŞ MEKANİK BÜYÜKLÜKLER. Sayfadaki "kurdaki %1 toplam stoka ~X
    # puan ekler" cümlesi doğrudan yp_pay'den türer; statik yazılırsa yp_pay
    # değiştiğinde cümle kendiyle çelişir.
    if m.get("yp_pay") is not None:
        koy("kur1_puan", m["yp_pay"] / 100.0, 2)
        koy("kur30_puan", 0.30 * m["yp_pay"], 0)
    # TABAN SÖZLÜĞÜ: aynı ozet.json içinde birden çok kredi/mevduat tanımı
    # dolaşıyor. Anahtar adları tabanı taşımadığı için okur payları yanlış
    # paydaya bölebiliyor; sözlük sayfada bir kez basılır.
    O["kredi_yi_tl_mlr"] = O.get("kredi_tl_mlr")
    O["kredi_yi_yp_mlr"] = O.get("kredi_yp_mlr")
    O["yp_pay_yi"] = O.get("yp_pay")
    if O.get("kredi_tl_mlr") is not None and O.get("kredi_yp_mlr") is not None:
        koy("kredi_yi_toplam_mlr", O["kredi_tl_mlr"] + O["kredi_yp_mlr"], 0)
        if m.get("kredi_toplam"):
            koy("kredi_taban_farki_yuzde",
                100 * (m["kredi_toplam"] - (O["kredi_tl_mlr"] + O["kredi_yp_mlr"]))
                / m["kredi_toplam"], 2)
    # Kur etkisinin BÜYÜKLÜĞÜ (mlr TL) — "8,6 puan" soyut, "417 mlr TL" değil.
    koy("gama_13h_mlr", m.get("gama_13h_mlr"), 0)
    koy("lamda_13h_mlr", m.get("lamda_13h_mlr"), 0)
    koy("delta_13h_mlr", m.get("delta_13h_mlr"), 0)
    if m.get("delta_13h_mlr"):
        koy("gama_pay", 100 * (m["gama_13h_mlr"] / m["delta_13h_mlr"]), 1)
    ayr = m.get("ayristirma") or {}
    koy("kimlik_artik", ayr.get("artik_bagil_maks"), None)
    koy("d_zincir_mlr", ayr.get("d_zincir_mlr"), 1)
    if ayr.get("d_cipa"):
        O["d_cipa"] = gun_tr(pd.Timestamp(ayr["d_cipa"]))
    uz = m.get("uzun") or {}
    if uz.get("kirilma"):
        O["kredi_seri_kirilma"] = uz["kirilma"]
        O["kredi_seri_kirilma_tr"] = gun_tr(pd.Timestamp(uz["kirilma"]))
    koy("ortusme_hafta", uz.get("ortusme_hafta"), 0)
    koy("ortusme_oran_ilk", uz.get("oran_ilk"), 5)
    koy("ortusme_oran_son", uz.get("oran_son"), 5)
    koy("ortusme_surukleme", uz.get("oran_surukleme"), 6)
    if m.get("uzun_bas"):
        O["uzun_bas"] = gun_tr(pd.Timestamp(m["uzun_bas"]))

    # ---------------------------------------------------------------- para
    for a in ("m1_mlr", "m2_mlr", "m3_mlr"):
        koy(a, m.get(a), 0)
    for a in ("g_m1_ar_13y", "g_m2_ar_13y", "g_m3_ar_13y", "g_m1_ham_13y",
              "g_m2_ham_13y", "g_m3_ham_13y", "tcmb_ar_m1_13y", "tcmb_ar_m2_13y",
              "tcmb_ar_m3_13y", "tcmb_ham_m2_13y", "emisyon_m1", "zk_ima_oran"):
        koy(a, m.get(a))
    for a in ("carpan_m1", "carpan_m2", "carpan_m3"):
        koy(a, m.get(a), 3)
    for a in ("rezerv_para_mlr", "zk_bloke_mlr", "emisyon_mlr",
              "serbest_mevduat_mlr", "mb_parasi_mlr"):
        koy(a, m.get(a), 0)
    # KUR ETKİSİ — İKİ AYRI TANIM, İKİ AYRI AD.
    # `m2_kur_etkisi_tcmb`: TCMB'nin KENDİ endekslerinin farkı (ham − arındırılmış).
    # `m2_kur_etkisi_biz` : bizim ham M2 ile bizim arındırılmış M2'mizin farkı.
    # İkisi aynı sayı DEĞİLDİR (TCMB'nin arındırma yöntemi yayımlanmıyor);
    # kredi tarafındaki `kur_etkisi_13y` ile karşılaştırılacak olan BİZİMKİDİR.
    if m.get("tcmb_ham_m2_13y") is not None and m.get("tcmb_ar_m2_13y") is not None:
        koy("m2_kur_etkisi_tcmb", m["tcmb_ham_m2_13y"] - m["tcmb_ar_m2_13y"])
        # Eski ad geriye dönük uyum için korunur (MDX'te kullanılmaz).
        koy("m2_kur_etkisi", m["tcmb_ham_m2_13y"] - m["tcmb_ar_m2_13y"])
    if m.get("g_m2_ham_13y") is not None and m.get("g_m2_ar_13y") is not None:
        koy("m2_kur_etkisi_biz", m["g_m2_ham_13y"] - m["g_m2_ar_13y"])
    O["para_kirilma"] = (m.get("dogrulama") or {}).get("para_kirilma") or []

    # ------------------------------------------------------- dolarizasyon
    for a in ("dth_pay_ham", "dth_pay_ar", "bilanco_pay_ham"):
        koy(a, m.get(a))
    koy("mevduat_tl_mlr", m.get("mevduat_tl_mlr"), 0)
    koy("mevduat_yp_mlr", m.get("mevduat_yp_mlr"), 0)
    koy("mevduat_yp_usd_mia", m.get("mevduat_yp_usd_mia"), 1)
    # BLOK TARİHİ: bu blok tek ortak tarihe çıpalı (metrik.py · _blok).
    if m.get("dol_tarih"):
        t = pd.Timestamp(m["dol_tarih"])
        O["dol_tarih"] = gun_tr(t)
        O["dol_tarih_kisa"] = t.strftime("%d.%m.%Y")
        O["dol_gecikme_gun"] = (dt.date.today() - t.date()).days
        # Haftalık çıpaya göre kaç hafta geride: sayfa "aynı hafta" derken
        # gerçekten aynı haftadan mı söz ediyor?
        koy("dol_cipa_fark_gun", (s_h - t).days, 0)
    if m.get("dol_en_yeni_tarih"):
        O["dol_en_yeni_tarih"] = gun_tr(pd.Timestamp(m["dol_en_yeni_tarih"]))
    if m.get("dol_kayan"):
        O["dol_kayan"] = m["dol_kayan"]
    dol = m.get("dolarizasyon") or {}
    if dol.get("cipa"):
        O["dol_cipa"] = gun_tr(pd.Timestamp(dol["cipa"]))
        O["dol_cipa_tarih"] = pd.Timestamp(dol["cipa"]).strftime("%d.%m.%Y")
    koy("dol_cipa_kur", dol.get("cipa_kur"), 4)
    koy("dol_ham_cipa", dol.get("ham_cipa"))
    if dol.get("ham_cipa") is not None and dol.get("ham_son") is not None:
        koy("dol_ham_degisim", dol["ham_son"] - dol["ham_cipa"])
        koy("dol_ar_degisim", (dol.get("ar_son") or 0) - dol["ham_cipa"])
        # Kur etkisinin GİZLEDİĞİ pay: iki okumanın farkı
        koy("dol_gizlenen", (dol["ham_son"] - dol["ham_cipa"])
            - ((dol.get("ar_son") or 0) - dol["ham_cipa"]))

    # TABAN SÖZLÜĞÜ — aynı ozet.json'da üç mevduat ve iki kredi tanımı dolaşıyor.
    # Anahtar adları tabanı taşımadığı için okur payları yanlış paydaya
    # bölebiliyordu; tabanı adında taşıyan eşleri ve bir sözlük metni yazılır.
    O["mevduat_zk_tl_mlr"] = O.get("mevduat_tl_mlr")
    O["mevduat_zk_yp_mlr"] = O.get("mevduat_yp_mlr")
    if O.get("mevduat_tl_mlr") is not None and O.get("mevduat_yp_mlr") is not None:
        koy("mevduat_zk_toplam_mlr",
            O["mevduat_tl_mlr"] + O["mevduat_yp_mlr"], 0)
    O["taban_sozlugu"] = (
        "Bu sayfada iki ayrı kredi ve iki ayrı mevduat tabanı geçer. "
        f"KREDİ — yurt içi TL+YP kırılımı {tr_sayi(O.get('kredi_yi_toplam_mlr'), 0)} "
        "milyar TL: büyüme serileri, YP payı ve Laspeyres ayrıştırması bu "
        f"tabana dayanır; sektör toplamı {tr_sayi(O.get('kredi_toplam_mlr'), 0)} "
        "milyar TL (yurt içi + yurt dışı): takip oranı ve kredi/mevduat oranı "
        f"bu tabana dayanır — iki taban arasındaki fark "
        f"%{tr_sayi(O.get('kredi_taban_farki_yuzde'), 2)}. "
        f"MEVDUAT — ZK tabanı {tr_sayi(O.get('mevduat_zk_toplam_mlr'), 0)} "
        "milyar TL (dolarizasyon payları); sektör toplamı "
        f"{tr_sayi(O.get('mevduat_sektor_toplam_mlr'), 0)} milyar TL "
        "(kredi/mevduat oranının paydası). YP payını sektör toplamına bölmek "
        "ya da iki mevduat tabanını birbiriyle karıştırmak yanlış sonuç verir; "
        "her pay yalnız kendi paydasıyla okunur.")

    # ---------------------------------------------------------------- KKM
    kkm = m.get("kkm") or {}
    O["kkm_aktif"] = bool(kkm.get("aktif"))
    koy("kkm_son_mlr_tl", kkm.get("son_mlr_tl"), 1)
    koy("kkm_zirve_mlr_tl", kkm.get("zirve_mlr_tl"), 0)
    koy("kkm_erime_ay_mlr", kkm.get("erime_ay_mlr"), 1)
    koy("kkm_erime_ay", kkm.get("erime_ay"), 0)
    koy("kkm_ddkkm_mia_usd", kkm.get("ddkkm_son_mia_usd"), 3)
    koy("kkm_ddkkm_zirve_mia_usd", kkm.get("ddkkm_zirve_mia_usd"), 1)
    if kkm.get("zirve_tarih"):
        z = pd.Timestamp(kkm["zirve_tarih"])
        O["kkm_zirve_donem"] = f"{AY_TR[z.month]} {z.year}"
    if kkm.get("son_tarih"):
        # KKM AYLIK bir stok; hattın ana saati ise HAFTALIK. Şekil 07'nin
        # damgası buradan gelir. Hattın aylık ANA saatinden (`ay_tarih`) ayrı
        # bir anahtar, çünkü ikisi ayrı ayrı donabilir: bugün ikisi de Temmuz
        # 2026'yı gösteriyor, yarın KKM serisi dururken aylık banka türü
        # tablosu ilerleyebilir ve şekil o gün yanlış aya damgalanırdı.
        O["kkm_son_tarih"] = pd.Timestamp(kkm["son_tarih"]).strftime("%m.%Y")
    O["kkm_cumlesi"] = (
        "Program açık: stok ve aylık akım güncel." if kkm.get("aktif") else
        "Program fiilen kapanmıştır; grafik bir akım hikâyesi değil, bitmiş bir "
        "rejimin tarihidir.")

    # ---------------------------------------------------------------- faiz
    for a in ("f_ticari_tl", "f_ihtiyac", "f_konut", "f_tasit", "f_tuketici",
              "mev_tl", "kat_ticari", "kat_tuketici", "politika", "aofm",
              "koridor_alt", "koridor_ust", "makas_kredi_mevduat",
              "spread_politika", "spread_aofm", "pka_12a", "reel_ticari",
              "reel_tuketici", "reel_mevduat", "reel_ticari_yaklasik"):
        koy(a, m.get(a))
    if m.get("reel_ticari") is not None and m.get("reel_ticari_yaklasik") is not None:
        koy("fisher_farki", m["reel_ticari_yaklasik"] - m["reel_ticari"])
    # AOFM'NİN VİNTAJI VE GEÇERLİLİĞİ — fonlama hattıyla aynı sözleşme.
    O["aofm_gecerli"] = bool(m.get("aofm_gecerli"))
    if m.get("aofm_tarih"):
        t = pd.Timestamp(m["aofm_tarih"])
        O["aofm_tarih"] = t.strftime("%d.%m.%Y")
        koy("aofm_yas_gun", (s_h - t).days, 0)
    koy("aofm_ham", m.get("aofm_ham"))
    if m.get("spread_aofm_tarih"):
        O["spread_aofm_tarih"] = pd.Timestamp(
            m["spread_aofm_tarih"]).strftime("%d.%m.%Y")
    koy("aofm_taban_mlr", (m.get("aofm_taban_mn_tl") or 0) / 1000.0
        if m.get("aofm_taban_mn_tl") is not None else None, 1)
    koy("aofm_taban_esik_mlr", (m.get("aofm_taban_esik_mn_tl") or 0) / 1000.0, 0)
    O["aofm_cumlesi"] = (
        f"AOFM %{tr_sayi(O.get('aofm'), 2)} "
        f"(çıpa {O.get('aofm_tarih', '—')}); fonlama tabanı eşiğin üstünde, "
        "'fonlama maliyeti' cümlesi kurulabilir."
        if O["aofm_gecerli"] else
        "AOFM bu koşuda GEÇERSİZ: haftalık çıpa gününde APİ fonlaması "
        f"{tr_sayi(O.get('aofm_taban_mlr'), 1)} milyar TL ile "
        f"{tr_sayi(O.get('aofm_taban_esik_mlr'), 0)} milyar TL eşiğinin "
        "altında. Sistemin marjinal fiyatını sterilizasyon belirliyor; "
        f"tablodaki AOFM son GEÇERLİ güne aittir "
        f"({O.get('aofm_tarih', '—')}, {O.get('aofm_yas_gun', '—')} gün "
        "önce) ve 'kredi − AOFM' makası güncel duruşun ölçüsü değildir; "
        "yerine politika faizi makası okunur.")
    # PKA beklentisinin yaşı — reel faizlerin girdisi sessizce eskiyebilir.
    # ANKET AYLIKTIR, GÜN DEĞİL. EVDS aylık gözlemi ayın İLK gününe damgalar ve
    # o damga gün gibi yazıldığında ("01.08.2026") okura o GÜN yapılmış bir
    # ölçüm gibi görünür; biçim sözleşmesi aylık saati AA.YYYY ister (aynı
    # dosyada `ay_tarih` ve `kkm_son_tarih` zaten öyle yazılıyordu).
    # `pka_yas_gun` ay BAŞINDAN sayılmaya devam ediyor ve bu bilerek: anket
    # ayın ilk yarısında derlenir, yani ay başı yaşın ÜST SINIRIDIR ve sayfa
    # onu "en çok" diye yazar. Ay SONUNDAN saymak — ölçüldü — bir ay geciken
    # bir anketi (temmuz anketi, 28.08 çıpası) 58 gün yerine 28 gün gösterir
    # ve 45 günlük uyarı eşiğini sessizce kapatırdı.
    if m.get("pka_tarih"):
        O["pka_tarih"] = pd.Timestamp(m["pka_tarih"]).strftime("%m.%Y")
    koy("pka_yas_gun", m.get("pka_yas_gun"), 0)

    # HER ANAHTARIN KENDİ SAATİ (metrik.anahtar_tarih). Kapsam ölçüm
    # katmanında, sözleşmeden türetiliyor; burada yalnız yazım dönüşümü var —
    # iki yerde iki liste tutulsaydı biri sessizce ayrışırdı. `setdefault`:
    # açıkça yazılmış saatler (aofm) kazanır.
    for anahtar, iso in (m.get("anahtar_tarih") or {}).items():
        O.setdefault(f"{anahtar}_tarih",
                     pd.Timestamp(iso).strftime("%d.%m.%Y"))
    # Ölçülemeyen saat ATLANMAZ, boş yazılır — sebebi kayda geçer.
    for _a in sayfa_saatlerini_tamamla(O):
        uyar(f"'{_a}' bu koşuda ölçülemedi; sayfada boş görünecek "
             "(donmuş bir sayı basılmasın).")

    # --------------------------------------------------------- banka türü
    for a in ("g_kh_toplam_yil", "g_kh_haric_yil", "g_kh_katilim_yil", "katilim_pay"):
        koy(a, m.get(a))
    for a in ("kh_toplam_mlr", "kh_katilim_mlr", "kh_haric_mlr"):
        koy(a, m.get(a), 0)
    if m.get("g_kh_toplam_yil") is not None and m.get("g_kh_haric_yil") is not None:
        koy("katilim_etkisi", m["g_kh_toplam_yil"] - m["g_kh_haric_yil"])

    # ---------------------------------------------------------------- BKEA
    for a in ("bkea_std_isletme", "bkea_std_kobi", "bkea_std_buyuk", "bkea_talep",
              "bkea_talep_bek", "bkea_std_konut", "bkea_std_tasit", "bkea_std_diger"):
        koy(a, m.get(a), 1)

    # ------------------------------------------------------------ çapraz
    cx = m.get("uzun_capraz") or {}
    koy("capraz_n", cx.get("n"), 0)
    koy("capraz_en_iyi_gecikme", cx.get("en_iyi_gecikme"), 0)
    koy("capraz_en_iyi_korel", cx.get("en_iyi_korel"), 3)
    koy("capraz_esanli_korel", cx.get("esanli_korel"), 3)
    if cx.get("bas"):
        O["capraz_bas"] = pd.Timestamp(cx["bas"]).strftime("%m.%Y")
        O["capraz_son"] = pd.Timestamp(cx["son"]).strftime("%m.%Y")
    if cx.get("en_iyi_gecikme") is not None:
        g = int(cx["en_iyi_gecikme"])
        O["capraz_yon"] = (
            "enflasyon momentumu kredi büyümesinin önünde" if g < 0 else
            "kredi büyümesi enflasyon momentumunun önünde" if g > 0 else
            "iki seri eşanlı")
        O["capraz_ay"] = abs(g)
    O["capraz_ucta"] = bool(cx.get("ucta"))

    # ------------------------------------------------------------ doğrulama
    dg = m.get("dogrulama") or {}
    for ad in ("m1", "m2", "m3"):
        h = (dg.get("ham") or {}).get(ad) or {}
        koy(f"dog_ham_{ad}_maks", h.get("maks_pp"), 3)
        koy(f"dog_ham_{ad}_n", h.get("n"), 0)
        koy(f"dog_ham_{ad}_biz", h.get("biz_son"))
        koy(f"dog_ham_{ad}_tcmb", h.get("tcmb_son"))
        a = (dg.get("arindirilmis") or {}).get(ad) or {}
        koy(f"dog_ar_{ad}_yanlilik", a.get("yanlilik_pp"))
        koy(f"dog_ar_{ad}_rmse", a.get("rmse_pp"))
        koy(f"dog_ar_{ad}_korel", a.get("korel"), 3)
        koy(f"dog_ar_{ad}_biz", a.get("biz_son"))
        koy(f"dog_ar_{ad}_tcmb", a.get("tcmb_son"))
    koy("dog_esik_ham", dg.get("esik_ham_pp"), 1)
    koy("dog_esik_ar", dg.get("esik_ar_yanlilik_pp"), 1)
    kd = dg.get("kredi_capraz") or {}
    koy("dog_kredi_n", kd.get("buyume_n"), 0)
    koy("dog_kredi_yanlilik", kd.get("buyume_yanlilik_pp"), 2)
    koy("dog_kredi_maks", kd.get("buyume_maks_pp"), 2)
    koy("dog_kredi_oran", kd.get("oran_ort"), 4)
    koy("dog_kredi_oran_std", kd.get("oran_std"), 4)
    koy("dog_kredi_haftalik", kd.get("haftalik_son"))
    koy("dog_kredi_aylik", kd.get("aylik_son"))

    # ------------------------------------------------------------ uyarılar
    uyarilar = list(uy.get("uyarilar", []))
    # SON SAVUNMA: metrik katmanı devralmayı atlarsa uyarı burada yakalanır.
    for u in (vd.get("uyarilar") or []):
        if u not in uyarilar:
            uyarilar.append(u)

    # --- TAZELİK BAYRAĞI ---------------------------------------------------
    # Yayım gecikmesi haftalık aile toleransını aşarsa veri BAYATTIR; sayfada
    # görünür bir kutuya bağlanır. Kaynak durduğunda hat yeşil bitse bile
    # okurun gördüğü ilk şey bayatlık olur.
    O.update(bayat_karari(O.get("yayim_gecikme_gun"), uyarilar))

    O["uyari_sayisi"] = len(uyarilar)
    O["uyari_metni"] = ((O["bayat_cumlesi"] + " · " if O["bayat"] else "")
                        + (" · ".join(uyarilar) if uyarilar
                           else "Bu koşuda uyarı yok."))
    # Sayıyı ÇERÇEVELEYEN cümle de sayıdan türetilir: "tek uyarı budur (3 adet)"
    # gibi kendisiyle çelişen bir metin kalmasın.
    O["uyari_cumlesi"] = (
        "Bu koşuda uyarı düşmedi." if not uyarilar else
        "Bu koşuda düşen tek uyarı budur:" if len(uyarilar) == 1 else
        f"Bu koşuda {len(uyarilar)} uyarı düştü:")

    # ------------------------------------------------- şekil saat defteri
    # GrafikEmbed her şeklin altına "veri <tarih>" basar ve MDX'te ayrı bir
    # anahtar verilmemişse o tarih hattın TEK ana saatinden gelir. Bu hat üç
    # ritim taşıyor, yani tek damga dört figürde yalan söylüyordu; defter o
    # boşluğu kapatır. Değeri None olan figürün altına sayfa tarih BASMAZ.
    # Tanım — hangi figürün saati nereden geliyor, hangisi neden tarihsiz —
    # veri.sekil_saatleri'nde, tek yerde: aynı defteri grafik.py figürün KENDİ
    # alt başlığı için de okuyor ve iki liste bir gün sessizce ayrışırdı.
    O["_sekil_tarih"] = sekil_saatleri(m)

    yol = PROJE / "ozet.json"
    yol.write_text(json.dumps(O, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"ozet.json yazıldı: {len(O)} anahtar · hafta {O['hafta']} · "
          f"yayım {O['yayim_tarihi']} ({O['yayim_gecikme_gun']} gün önce)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
