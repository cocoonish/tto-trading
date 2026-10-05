#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EYLÜL 2026 TÜFE YAZISI (05.10.2026) — ölçüm katmanı.

Yazının ve figürlerin kullandığı HER sayı buradan gelir ve `veri/<çıpa>/olcum.json`a
yazılır. Girdi yalnız arşivdir (`arsivle.py`): canlı hat dosyası okunmaz, yani
yazı yayımlandığı günün ölçümüyle yeniden üretilebilir kalır. Arşivin her dosyası
okunmadan önce künyedeki özle sınanır.

Her sayı için ölçüm dosyasında: ham değer, Türkçe sözleşmeyle yazılmış metin
biçimi (ondalık virgül, eksi U+2212, yüzde önde, puan/bp arkada), kaynak (arşiv
dosyası ve sütun/anahtar) ve tanım. `dogrula.py` yayımlanan metindeki her sayıyı
bu metin biçimleriyle karşılaştırır.

Hattın yayımladığı sayılar burada YENİDEN KURULUR ve hattın `ozet.json`uyla
karşılaştırılır (manşet, alt göstergeler, arındırılmış eğilim, beklenti isabeti,
baz senaryoları, reel faiz). Bir karşılaştırma tutmazsa betik düşer: yazı, hattın
sayısıyla kendi hesabı ayrışan bir sayıyı taşımamalı.

Kapsam dışı ve ADIYLA: hattın bu koşuda geride kalan dört serisi (yönetilen
fiyatlar hariç endeks, özel kapsamlı A, özel kapsamlı F, manşet TÜFE'nin özel
kapsamlı göstergeler tablosundaki kopyası) hiçbir ölçüye girmez; üç haneli kesitte 095 ve 105 Eylül'de veri vermediği için dağılım
ölçüleri 45 değil 43 grupla kurulur. Ana harcama grubu ağırlıkları EVDS'te
yayımlanmaz; hattın kimlikten çözdüğü tahmindir ve 2026'da tekil değildir (9 ay,
13 bilinmeyen) — katkılar 2025 ağırlıklarıyla da hesaplanıp fark yazılır.

Koşum:  python3 olcum.py
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BURASI = Path(__file__).resolve().parent
CIPA = "2026-10-05"
VERI = BURASI / "veri" / CIPA
CIKTI = VERI / "olcum.json"

SON = pd.Timestamp("2026-09-01")          # yazının veri ayı
ONC = pd.Timestamp("2026-08-01")
ARA25 = pd.Timestamp("2025-12-01")        # zincir Laspeyres tabanı (2026)
ESIK_30 = 30.0                            # yazının sorduğu yuvarlak düzey
AY = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos",
      "Eylül", "Ekim", "Kasım", "Aralık"]

# hattın ana/özel kapsamlı seri adları (aylik.csv sütunu → yazı adı)
SERI = {
    "tufe": ("tufe", "TÜFE (manşet)"),
    "b": ("cekirdek_b", "B çekirdek göstergesi"),
    "c": ("cekirdek_c", "C çekirdek göstergesi"),
    "hizmet": ("hizmet", "hizmet"),
    "mal": ("temel_mal", "temel mallar"),
    "kira": ("kira", "kira"),
    "enerji": ("enerji", "enerji"),
    "gida": ("gida", "gıda ve alkolsüz içecekler"),
    "hamgida": ("islenmemis_gida", "işlenmemiş gıda"),
    "islgida": ("islenmis_gida", "işlenmiş gıda"),
    "ata": ("alkol_tutun_altin", "alkollü içecekler, tütün ve altın"),
    "mallar": ("mallar", "mallar (toplam)"),
    "ufe": ("yi_ufe", "Yİ-ÜFE"),
    "ito": ("ito_ist", "İTO İstanbul tüketici fiyatları"),
    "uge": ("ito_uge", "İTO İstanbul ücretliler geçinme endeksi"),
}
# ozet.json'daki karşılıkları (yeniden kurulan değerin hattın yayımladığıyla sınanması)
OZET_ESI = {"tufe": "tufe", "b": "b", "c": "c", "hizmet": "hizmet", "mal": "mal", "kira": "kira",
            "enerji": "enerji", "gida": "gida", "hamgida": "hamgida", "islgida": "islgida",
            "ata": "atg", "ufe": "ufe"}

ANA = {  # 13 ana harcama grubu (COICOP 2018, TÜİK 2025=100); figür etiketi kısa ad
    "01": "Gıda ve alkolsüz içecekler", "02": "Alkollü içecekler ve tütün",
    "03": "Giyim ve ayakkabı", "04": "Konut, su, elektrik, gaz",
    "05": "Mobilya, ev eşyası, ev bakımı", "06": "Sağlık", "07": "Ulaştırma",
    "08": "Bilgi ve iletişim", "09": "Eğlence, spor ve kültür", "10": "Eğitim hizmetleri",
    "11": "Lokanta ve konaklama", "12": "Sigorta ve finansal hizmetler",
    "13": "Kişisel bakım ve çeşitli",
}
ANA_SERI = {"tufe", "b", "c", "hizmet", "mal", "kira", "enerji", "gida"}   # değişim ve baz da ölçülenler
BESLI = {"oktg23": "hizmet", "oktg18": "temel mallar", "oktg09": "enerji",
         "oktg10": "gıda ve alkolsüz içecekler", "oktg22": "alkol, tütün ve altın"}

hatalar: list[str] = []
D: dict[str, dict] = {}


# ─────────────────────────────────────────────── biçim (ortak/bicim sözleşmesi)
def sayi(x: float, b: int = 2, arti: bool = False) -> str:
    """Ondalık virgül, binlik nokta, eksi U+2212; sıfıra yuvarlanan değer işaretsiz."""
    s = f"{abs(x):,.{b}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    sifir = float(s.replace(".", "").replace(",", ".")) == 0
    if x < 0 and not sifir:
        return "−" + s
    return ("+" + s) if (arti and x > 0 and not sifir) else s


def metin_bicimi(x: float, b: int, birim: str, arti: bool = False) -> str:
    """Birimli yazım: yüzde ÖNDE (işaret yüzdeden de önce: −%0,20), puan/bp/gün ARKADA."""
    if birim == "%":
        s = sayi(abs(x), b)
        sifir = float(s.replace(".", "").replace(",", ".")) == 0
        if x < 0 and not sifir:
            return "−%" + s
        return ("+%" if (arti and x > 0 and not sifir) else "%") + s
    if birim in ("puan", "bp", "ay", "gün", "kat"):
        return f"{sayi(x, b, arti)} {birim}"
    return sayi(x, b, arti)


def kaydet(anahtar: str, deger, b: int, birim: str, kaynak: str, tanim: str,
           arti: bool = False, dis: str | None = None) -> float:
    if anahtar in D:
        raise SystemExit(f"anahtar iki kez kaydedildi: {anahtar}")
    deger = float(deger)
    if not np.isfinite(deger):
        raise SystemExit(f"ölçülemeyen değer kaydedilmeye çalışıldı: {anahtar}")
    D[anahtar] = {"deger": deger, "b": b, "birim": birim, "arti": arti,
                  "metin": metin_bicimi(deger, b, birim, arti),
                  "kaynak": kaynak, "tanim": tanim}
    if dis:
        D[anahtar]["dis_kaynak"] = dis
    return deger


def etiket(anahtar: str, metin: str, kaynak: str, tanim: str) -> None:
    """Sayı olmayan ölçüm (ay adı, grup adı): metin olarak kaydedilir."""
    D[anahtar] = {"metin": metin, "kaynak": kaynak, "tanim": tanim}


def sina(kosul: bool, mesaj: str) -> None:
    if not kosul:
        hatalar.append(mesaj)


def ay_ad(t: pd.Timestamp) -> str:
    return f"{AY[t.month]} {t.year}"


# ─────────────────────────────────────────────── arşiv
def arsiv() -> tuple[dict, dict]:
    kunye = json.loads((VERI / "kunye.json").read_text(encoding="utf-8"))
    ham: dict[str, bytes] = {}
    for ad, k in kunye["dosyalar"].items():
        b = gzip.decompress((VERI / f"{ad}.gz").read_bytes())
        if hashlib.sha256(b).hexdigest() != k["sha256"]:
            raise SystemExit(f"arşiv özü künyeyle tutmuyor: {ad}")
        ham[ad] = b
    return kunye, ham


def csv(ham: dict, ad: str) -> pd.DataFrame:
    return pd.read_csv(io.BytesIO(ham[ad]), index_col=0, parse_dates=True)


def js(ham: dict, ad: str) -> dict:
    return json.loads(ham[ad].decode("utf-8"))


# ─────────────────────────────────────────────── yardımcı ölçüler
def aylik(p: pd.Series) -> pd.Series:
    return (p / p.shift(1) - 1) * 100


def yillik(p: pd.Series) -> pd.Series:
    return (p / p.shift(12) - 1) * 100


def saar3(p: pd.Series) -> pd.Series:
    return ((p / p.shift(3)) ** 4 - 1) * 100


def katki_ana(a: pd.DataFrame, w: dict, t: pd.Timestamp) -> tuple[pd.Series, float, float]:
    """C_i = ω_{i,t−1}·r_{i,t} (puan); ω etkin ağırlık (hattın `etkin_agirlik` tanımı):
    ω_{i,t−1} = w_i·(P_{i,t−1}/P_{i,Ara}) / Σ_j(…). Dönüş: katkılar, manşet, artık."""
    ad = [f"ana_{k}" for k in ANA]
    wv = pd.Series({k: w[k] for k in ad})
    onc = t - pd.DateOffset(months=1)
    ara = pd.Timestamp(f"{t.year - 1}-12-01")
    om = wv * (a.loc[onc, ad] / a.loc[ara, ad])
    om = om / om.sum()
    r = (a.loc[t, ad] / a.loc[onc, ad] - 1) * 100
    c = (om * r).astype(float)
    pi = float((a.loc[t, "tufe"] / a.loc[onc, "tufe"] - 1) * 100)
    return c, pi, pi - float(c.sum())


# ─────────────────────────────────────────────── ölçümler
def manset(a: pd.DataFrame, oz: dict) -> None:
    for k, (kol, ad) in SERI.items():
        s = a[kol].dropna()
        sina(s.index[-1] == SON, f"{kol}: son gözlem Eylül 2026 değil ({s.index[-1]:%Y-%m})")
        m, y = aylik(s), yillik(s)
        src = f"aylik.csv · {kol}"
        kaydet(f"{k}_aylik", m.loc[SON], 2, "%", src, f"{ad}, Eylül 2026 aylık değişim")
        kaydet(f"{k}_aylik_agu", m.loc[ONC], 2, "%", src, f"{ad}, Ağustos 2026 aylık değişim")
        kaydet(f"{k}_12a", y.loc[SON], 2, "%", src, f"{ad}, Eylül 2026 yıllık değişim")
        kaydet(f"{k}_12a_agu", y.loc[ONC], 2, "%", src, f"{ad}, Ağustos 2026 yıllık değişim")
        if k in OZET_ESI:
            e = OZET_ESI[k]
            for son_ek, deger in (("aylik", m.loc[SON]), ("12a", y.loc[SON])):
                sina(abs(round(deger, 2) - oz[f"{e}_{son_ek}"]) < 0.006,
                     f"{k}_{son_ek}: yeniden kurulan {deger:.4f}, hattın ozet.json'u {oz[f'{e}_{son_ek}']}")
        if k not in ANA_SERI:
            # yan serilerde yalnız düzey: her fazladan değer, kapının envanterinde tesadüfen eşleşebilecek
            # bir sayı daha demektir (dogrula.py metindeki sayıyı birim ve işaretle bu kümede arar)
            continue
        kaydet(f"{k}_12a_degisim", y.loc[SON] - y.loc[ONC], 2, "puan", src,
               f"{ad}, yıllık oranın Ağustos'tan Eylül'e değişimi", arti=True)
        kaydet(f"{k}_aylik_degisim", m.loc[SON] - m.loc[ONC], 2, "puan", src,
               f"{ad}, aylık oranın Ağustos'tan Eylül'e değişimi", arti=True)
        g = pd.Timestamp("2025-09-01")
        if g in m.index and pd.notna(m.loc[g]):
            kaydet(f"{k}_aylik_2025_09", m.loc[g], 2, "%", src, f"{ad}, Eylül 2025 aylık değişim (baz)")
    kaydet("tufe_endeks", a.loc[SON, "tufe"], 2, "", "aylik.csv · tufe", "TÜFE endeks düzeyi (2025=100), Eylül 2026")
    t = a["tufe"].dropna()
    y = yillik(t)
    kaydet("tufe_12a_2025_09", y.loc[pd.Timestamp("2025-09-01")], 2, "%", "aylik.csv · tufe",
           "TÜFE yıllık, Eylül 2025 (bir yıl önce)")
    kaydet("tufe_12a_tam", y.loc[SON], 4, "%", "aylik.csv · tufe",
           "TÜFE yıllık, dört ondalık (hattın EVDS ile birebir denetlediği değer)")
    # makaslar
    kaydet("hizmet_mal_makas", yillik(a["hizmet"]).loc[SON] - yillik(a["temel_mal"]).loc[SON],
           2, "puan", "aylik.csv · hizmet, temel_mal", "hizmet yıllık − temel mallar yıllık, Eylül 2026")
    kaydet("hizmet_mal_makas_agu", yillik(a["hizmet"]).loc[ONC] - yillik(a["temel_mal"]).loc[ONC],
           2, "puan", "aylik.csv · hizmet, temel_mal", "hizmet yıllık − temel mallar yıllık, Ağustos 2026")
    kaydet("ufe_tufe_makas", yillik(a["yi_ufe"]).loc[SON] - y.loc[SON], 2, "puan",
           "aylik.csv · yi_ufe, tufe", "Yİ-ÜFE yıllık − TÜFE yıllık, Eylül 2026")
    kaydet("c_tufe_aylik_fark", aylik(a["cekirdek_c"]).loc[SON] - aylik(t).loc[SON], 2, "puan",
           "aylik.csv · cekirdek_c, tufe", "C aylık − TÜFE aylık, Eylül 2026", arti=True)
    kaydet("kira_manset_kati", aylik(a["kira"]).loc[SON] / aylik(t).loc[SON], 2, "",
           "aylik.csv · kira, tufe", "kiranın Eylül 2026 aylık değişiminin manşet aylığına oranı")
    # Şekil 01'in sağ ucu: 24 aylık pencerede B ve C'nin ikisinin de manşetin üstünde bittiği ay sayısı
    son24 = [SON - pd.DateOffset(months=i) for i in range(23, -1, -1)]
    mb, mc = aylik(a["cekirdek_b"]), aylik(a["cekirdek_c"])
    mt = aylik(t)
    kaydet("bc_ust_manset_ay", sum(1 for u in son24 if mb.loc[u] > mt.loc[u] and mc.loc[u] > mt.loc[u]), 0, "",
           "aylik.csv · cekirdek_b, cekirdek_c, tufe",
           "Ekim 2024–Eylül 2026'nın 24 ayından kaçında B ve C'nin aylığı ikisi de manşetin üstünde")


def gecmis(a: pd.DataFrame) -> None:
    """Tarihçe ölçüleri: yıllık oran %30'un altına en son ne zaman indi, Eylül'ün geçmiş
    yıllardaki aylık oranları, hangi düzeyler hangi aydan beri görülmedi."""
    t = a["tufe"].dropna()
    y = yillik(t).dropna()
    ilk = y.index[0]
    etiket("tarihce_ilk_ay", ay_ad(ilk), "aylik.csv · tufe",
           "yıllık TÜFE tarihçesinin ilk ayı (endeks 2005 başından, yıllık oran 12 ay sonra tanımlı)")
    alt = y[(y < ESIK_30) & (y.index < SON)]
    sina(len(alt) > 0 and y.loc[SON] < ESIK_30, "yıllık %30 altı sorusu kurulamadı")
    son_alt = alt.index[-1]
    etiket("alti30_son_ay", ay_ad(son_alt), "aylik.csv · tufe",
           "Eylül 2026'dan önce yıllık TÜFE'nin %30'un altında olduğu son ay")
    kaydet("alti30_son_deger", y.loc[son_alt], 2, "%", "aylik.csv · tufe",
           f"o ayın ({ay_ad(son_alt)}) yıllık TÜFE'si")
    ust = y[(y.index > son_alt) & (y.index < SON)]
    sina(bool((ust >= ESIK_30).all()), "%30 üstü dönem kesintisiz değil")
    kaydet("ust30_ay_sayisi", len(ust), 0, "", "aylik.csv · tufe",
           f"yıllık TÜFE'nin kesintisiz %30 ve üstünde kaldığı ay sayısı ({ay_ad(ust.index[0])}–{ay_ad(ust.index[-1])})")
    etiket("ust30_ilk_ay", ay_ad(ust.index[0]), "aylik.csv · tufe", "%30 üstü dönemin ilk ayı")
    kaydet("esik_30", ESIK_30, 0, "%", "yazının sorusu",
           "yıllık oranın kıyaslandığı yuvarlak düzey (bir ölçüm değil, yazının sorusu)")
    m = aylik(t)
    for yil in range(2019, 2026):
        kaydet(f"eylul_aylik_{yil}", m.loc[pd.Timestamp(f"{yil}-09-01")], 2, "%", "aylik.csv · tufe",
               f"Eylül {yil} aylık TÜFE")
    eyl = m[(m.index.month == 9) & (m.index.year >= 2022) & (m.index.year <= 2025)]
    sina(len(eyl) == 4, "2022–2025 Eylül ortalaması dört Eylül'den kurulmadı")
    kaydet("eylul_aylik_ort_2022_2025", eyl.mean(), 2, "%", "aylik.csv · tufe",
           "Eylül aylık TÜFE'nin 2022–2025 ortalaması (dört Eylül)")
    # "hangi aydan beri" ölçüleri: yıllık oran en düşük/aylık oran en düşük-yüksek
    for k, kol, ad, yon, olcu in (
            ("tufe", "tufe", "TÜFE", "dusuk", "y"), ("b", "cekirdek_b", "B", "dusuk", "y"),
            ("c", "cekirdek_c", "C", "dusuk", "y"), ("hizmet", "hizmet", "hizmet", "dusuk", "y"),
            ("kira", "kira", "kira", "dusuk", "y"), ("enerji", "enerji", "enerji", "yuksek", "y"),
            ("hizmet", "hizmet", "hizmet", "dusuk", "m")):
        s = (yillik if olcu == "y" else aylik)(a[kol].dropna()).dropna()
        cur, onceki = s.loc[SON], s[s.index < SON]
        bul = onceki[onceki <= cur] if yon == "dusuk" else onceki[onceki >= cur]
        if len(bul):
            ek = "yillik" if olcu == "y" else "aylik"
            etiket(f"{k}_{ek}_{yon}_beri", ay_ad(bul.index[-1]), f"aylik.csv · {kol}",
                   f"{ad} {'yıllık' if olcu == 'y' else 'aylık'} oranının Eylül 2026 düzeyine "
                   f"{'eşit ya da altında' if yon == 'dusuk' else 'eşit ya da üstünde'} olduğu son ay")
            kaydet(f"{k}_{ek}_{yon}_beri_deger", bul.iloc[-1], 2, "%", f"aylik.csv · {kol}",
                   f"o ayın ({ay_ad(bul.index[-1])}) {ad} {'yıllık' if olcu == 'y' else 'aylık'} oranı")


def baz_yuku(a: pd.DataFrame, sa: pd.DataFrame) -> None:
    """Yıllık oranın Ağustos'tan Eylül'e düşüşü: (1+y_t) = (1+y_{t−1})(1+m_t)/(1+m_{t−12}).

    Kimlik her ay doğrudur ve tek başına baz etkisini ölçmez (her düşüşü "iki Eylül arasındaki
    farka" yazar). Baz payı bir KARŞI OLGUYLA ölçülür: Ağustos'un arındırılmış aylık hızı Eylül'de
    de sürseydi, Eylül'ün kendi mevsimsel bileşeniyle ham aylık ne olurdu ve yıllık oran nereye
    inerdi. Düşüşün o karşı olguya kadarki kısmı baz, kalanı eğilimdeki yavaşlamadır."""
    t = a["tufe"].dropna()
    m, y = aylik(t), yillik(t)
    m_eyl25 = m.loc[pd.Timestamp("2025-09-01")]
    sabit = ((1 + y.loc[ONC] / 100) * (1 + m.loc[SON] / 100) / (1 + m_eyl25 / 100) - 1) * 100
    sina(abs(sabit - y.loc[SON]) < 1e-9, "yıllık oran kimliği tutmuyor")
    s = sa["tufe"].dropna()
    ms = aylik(s)
    mev = (1 + m.loc[SON] / 100) / (1 + ms.loc[SON] / 100)          # Eylül'ün mevsim çarpanı (ham/arındırılmış)

    def yil_o(ham_aylik: float) -> float:
        return ((1 + y.loc[ONC] / 100) * (1 + ham_aylik / 100) / (1 + m_eyl25 / 100) - 1) * 100

    ko = ((1 + ms.loc[ONC] / 100) * mev - 1) * 100
    kaydet("karsi_olgu_aylik", ko, 2, "%", "aylik.csv · tufe; sa.csv · tufe",
           "Ağustos'un arındırılmış aylığı Eylül'de sürseydi Eylül'ün mevsim çarpanıyla ham aylık")
    ko12 = kaydet("karsi_olgu_12a", yil_o(ko), 2, "%", "aylik.csv · tufe; sa.csv · tufe",
                  "aynı karşı olguda Eylül yıllık TÜFE")
    kaydet("baz_payi", y.loc[ONC] - ko12, 2, "puan", "karşı olgu",
           "yıllık düşüşün baz kısmı: Ağustos yıllığı − karşı olgu yıllığı")
    kaydet("egilim_payi", ko12 - y.loc[SON], 2, "puan", "karşı olgu",
           "yıllık düşüşün eğilim kısmı: karşı olgu yıllığı − gerçekleşen Eylül yıllığı")
    q = lambda son: float((1 + ms.loc[:son].tail(3) / 100).prod() ** (1 / 3) - 1) * 100
    kaydet("karsi_olgu_mom_agu_12a", yil_o(((1 + q(ONC) / 100) * mev - 1) * 100), 2, "%", "sa.csv · tufe",
           "Ağustos'un üç aylık momentumu (Haziran–Ağustos) Eylül'de sürseydi Eylül yıllığı")
    kaydet("karsi_olgu_mom_eyl_12a", yil_o(((1 + q(SON) / 100) * mev - 1) * 100), 2, "%", "sa.csv · tufe",
           "Eylül'ün üç aylık momentumu (Temmuz–Eylül) Eylül aylığı yerine konsaydı Eylül yıllığı")
    kayma = kaydet("tcmb_kayma_agu", 0.25, 2, "puan", "dış kaynak",
                   "TCMB toplantı özeti (17 Eylül 2026): takvim kaymasının Ağustos enflasyonuna etkisi",
                   dis="TCMB PPK Toplantı Özeti (2026-42), 17 Eylül 2026")
    kaydet("karsi_olgu_kaymasiz_12a", yil_o(((1 + (ms.loc[ONC] - kayma) / 100) * mev - 1) * 100), 2, "%",
           "sa.csv · tufe ve dış kaynak",
           "Ağustos'un arındırılmış aylığından kaymanın tamamı düşülerek kurulan karşı olgu yıllığı (kaba sınama)")
    esik = ((1 + ESIK_30 / 100) * (1 + m_eyl25 / 100) / (1 + y.loc[ONC] / 100) - 1) * 100
    kaydet("esik30_eylul_ham", esik, 2, "%", "baz aritmetiği",
           "Eylül yıllığının %30'un altına inmesi için Eylül ham aylığının geçmemesi gereken düzey")
    kaydet("yillik_dusus", y.loc[ONC] - y.loc[SON], 2, "puan", "aylik.csv · tufe",
           "yıllık TÜFE'nin Ağustos'tan Eylül'e düşüşü")
    kaydet("eylul_aylik_fark", m_eyl25 - m.loc[SON], 2, "puan", "aylik.csv · tufe",
           "Eylül 2025 aylık − Eylül 2026 aylık (baz dışına çıkan ay ile yeni ay farkı)")


def mevsim(sa: pd.DataFrame, a: pd.DataFrame, oz: dict) -> None:
    for k, kol, ad in (("tufe", "tufe", "TÜFE"), ("b", "cekirdek_b", "B"), ("c", "cekirdek_c", "C"),
                       ("hizmet", "hizmet", "hizmet"), ("mal", "temel_mal", "temel mallar"),
                       ("gida", "gida", "gıda"), ("enerji", "enerji", "enerji")):
        s = sa[kol].dropna()
        m, q = aylik(s), saar3(s)
        src = f"sa.csv · {kol}"
        kaydet(f"{k}_aylik_sa", m.loc[SON], 2, "%", src,
               f"{ad}, mevsimsellikten arındırılmış aylık değişim, Eylül 2026 (hattın arındırması)")
        kaydet(f"{k}_aylik_sa_agu", m.loc[ONC], 2, "%", src,
               f"{ad}, arındırılmış aylık, Ağustos 2026 (bugünkü arındırma sürümü)")
        kaydet(f"{k}_3a_saar", q.loc[SON], 2, "%", src,
               f"{ad}, arındırılmış endeksin son 3 aylık değişiminin yıllıklandırılmışı (zincir), Eylül 2026")
        kaydet(f"{k}_3a_saar_agu", q.loc[ONC], 2, "%", src,
               f"{ad}, aynı ölçü Ağustos 2026 (bugünkü arındırma sürümü)")
        e = {"tufe": "tufe", "b": "b", "c": "c", "hizmet": "hizmet", "mal": "mal", "gida": "gida",
             "enerji": "enerji"}[k]
        sina(abs(round(m.loc[SON], 2) - oz[f"{e}_aylik_sa"]) < 0.006, f"{k}: arındırılmış aylık hattınkiyle ayrışıyor")
        sina(abs(round(q.loc[SON], 2) - oz[f"{e}_3a"]) < 0.006, f"{k}: 3 aylık eğilim hattınkiyle ayrışıyor")
    kaydet("tufe_3a_saar_degisim", saar3(sa["tufe"]).loc[ONC] - saar3(sa["tufe"]).loc[SON], 2, "puan", "sa.csv · tufe",
           "TÜFE'nin üç aylık yıllıklandırılmış eğiliminin Ağustos'tan Eylül'e düşüşü")
    kaydet("tufe_mevsim_payi", aylik(a["tufe"]).loc[SON] - aylik(sa["tufe"]).loc[SON], 2, "puan",
           "aylik.csv · tufe; sa.csv · tufe", "Eylül aylık TÜFE'de mevsimsel bileşen (ham − arındırılmış)")
    kaydet("hizmet_mevsim_payi", aylik(a["hizmet"]).loc[SON] - aylik(sa["hizmet"]).loc[SON], 2, "puan",
           "aylik.csv · hizmet; sa.csv · hizmet", "Eylül aylık hizmette mevsimsel bileşen (ham − arındırılmış)")
    kaydet("c_tufe_aylik_sa_fark", aylik(sa["cekirdek_c"]).loc[SON] - aylik(sa["tufe"]).loc[SON], 2, "puan",
           "sa.csv · cekirdek_c, tufe", "C arındırılmış aylık − TÜFE arındırılmış aylık, Eylül 2026")
    kaydet("c_tufe_aylik_mevsim_payi",
           (aylik(a["cekirdek_c"]).loc[SON] - aylik(a["tufe"]).loc[SON])
           - (aylik(sa["cekirdek_c"]).loc[SON] - aylik(sa["tufe"]).loc[SON]), 2, "puan",
           "aylik.csv; sa.csv", "C–manşet aylık farkının mevsimsel kısmı (ham fark − arındırılmış fark)")
    # Uç nokta revizyonu: hattın uç nokta testi (`metrik.vintage_revizyon`): ham seri 1–6 ay kesilip yeniden
    # arındırılır; o ay son gözlemken kestirilen arındırılmış aylık (ve 3 aylık yıllıklandırılmış) ile bugünkü
    # kestirim kıyaslanır (Mart–Ağustos 2026). Arşivlenmiş hat özetinden okunur; testin girdisi olan endeks
    # düzeyleri arşivdedir (yeniden koşturmak hattın arındırma kütüphanesini ister).
    tanim = (f"son {oz['sa_rev_k']} ayın her birinde, o ay son gözlemken kestirilen arındırılmış {{}} ile "
             "bugünkü kestirim arasındaki farkın en büyüğü (hattın uç nokta testi)")
    for k, ad in (("tufe", "TÜFE"), ("c", "C"), ("hizmet", "hizmet"), ("mal", "temel mallar"), ("oynak", "enerji")):
        kaydet(f"sa_rev_{k}_maks", oz[f"sa_rev_{k}_maks"], 2, "puan", f"enflasyon_ozet.json · sa_rev_{k}_maks",
               f"{ad}: " + tanim.format("aylık"))
    for k, ad in (("tufe", "TÜFE"), ("c", "C"), ("mal", "temel mallar"), ("oynak", "enerji")):
        kaydet(f"sa_rev_{k}_saar3", oz[f"sa_rev_{k}_saar3"], 2, "puan", f"enflasyon_ozet.json · sa_rev_{k}_saar3",
               f"{ad}: " + tanim.format("3 aylık yıllıklandırılmış"))
    sina(oz.get("sa_rev_oynak_ad") == "Enerji", f"en oynak seri enerji değil: {oz.get('sa_rev_oynak_ad')}")
    kaydet("sa_rev_surum", oz["sa_rev_k"], 0, "", "enflasyon_ozet.json · sa_rev_k",
           "uç nokta testinin kestiği ay sayısı")
    # yıllıklandırılmış eğilim ile hedef
    kaydet("hedef_yillik", oz["hedef_yillik"], 0, "%", "enflasyon_ozet.json · hedef_yillik", "TCMB enflasyon hedefi")
    kaydet("hedef_aylik", oz["hedef_aylik"], 2, "%", "enflasyon_ozet.json · hedef_aylik",
           "hedefle uyumlu aylık oran ((1,05)^(1/12) − 1)")


def katkilar(a: pd.DataFrame, agr: dict, kat: pd.DataFrame) -> dict:
    """İki ayrıştırma. (1) Beş bileşen (hattın katki.csv'si; 2026'da 9 denklem, 5 bilinmeyen —
    aşırı belirlenmiş, artık adıyla). (2) 13 ana harcama grubu (ağırlık 2026'da tekil değil;
    2025 ağırlıklarıyla da hesaplanır, fark yazılır)."""
    out: dict = {"besli": {}, "ana": {}}
    # (1) beşli
    for t, ek in ((SON, ""), (ONC, "_agu")):
        sina(t in kat.index, f"katki.csv'de {t:%Y-%m} yok")
        r = kat.loc[t]
        top = 0.0
        for kod, ad in BESLI.items():
            v = float(r[f"c_{kod}"]) * 100
            top += v
            kaydet(f"katki5_{kod}{ek}", v, 2, "puan", f"katki.csv · c_{kod}",
                   f"{ad} bileşeninin {ay_ad(t)} aylık TÜFE'ye katkısı")
            out["besli"].setdefault(kod, {})[t.strftime("%Y-%m")] = v
        kaydet(f"katki5_artik{ek}", float(r["pi"]) * 100 - top, 4, "puan", "katki.csv · pi, c_*",
               f"beş bileşen katkı toplamının manşetten farkı, {ay_ad(t)}")
    for kod, ad in BESLI.items():
        kaydet(f"katki5_{kod}_degisim", out["besli"][kod]["2026-09"] - out["besli"][kod]["2026-08"], 2, "puan",
               f"katki.csv · c_{kod}", f"{ad} katkısının Ağustos'tan Eylül'e değişimi", arti=True)
    kaydet("katki5_hizmet_pay", out["besli"]["oktg23"]["2026-09"] / (float(kat.loc[SON, "pi"]) * 100) * 100, 1,
           "%", "katki.csv", "hizmetin Eylül aylık TÜFE içindeki payı (katkı / manşet)")
    # (2) 13 ana grup
    w26 = agr["ana_grup"]["2026"]
    w25 = agr["ana_grup"]["2025"]
    etiket("ana_agirlik_kip", w26["kip"], "agirlik.json · ana_grup.2026.kip",
           f"2026 ana grup ağırlığı çözüm kipi; {w26['n_ay']} ay denklem, 13 bilinmeyen")
    kaydet("ana_agirlik_ay", w26["n_ay"], 0, "", "agirlik.json · ana_grup.2026.n_ay",
           "2026 ağırlıklarının çözüldüğü ay sayısı")
    satir = {}
    for t, ek in ((SON, ""), (ONC, "_agu")):
        c, pi, art = katki_ana(a, w26["paylar"], t)
        c25, _, art25 = katki_ana(a, w25["paylar"], t)
        sina(abs(art) < 0.01, f"ana grup katkı toplamı manşete oturmuyor ({ay_ad(t)}: {art:.4f} puan)")
        kaydet(f"katki13_artik{ek}", art, 4, "puan", "aylik.csv · ana_01…13; agirlik.json · ana_grup.2026",
               f"13 grup katkı toplamının manşetten farkı, {ay_ad(t)}")
        kaydet(f"katki13_artik_w25{ek}", art25, 2, "puan", "aylik.csv · ana_01…13; agirlik.json · ana_grup.2025",
               f"2025 ağırlıklarıyla 13 grup katkı toplamının manşetten farkı, {ay_ad(t)}", arti=True)
        kaydet(f"katki13_w_fark_maks{ek}", float((c - c25).abs().max()), 2, "puan",
               "agirlik.json · ana_grup.2026, 2025",
               f"tek bir grubun katkısı 2026 yerine 2025 ağırlığıyla hesaplanınca en çok bu kadar değişir, {ay_ad(t)}")
        r = (a.loc[t, [f"ana_{k}" for k in ANA]] / a.loc[t - pd.DateOffset(months=1),
                                                         [f"ana_{k}" for k in ANA]] - 1) * 100
        for kod in ANA:
            col = f"ana_{kod}"
            kaydet(f"ana{kod}_katki{ek}", c[col], 2, "puan", f"aylik.csv · {col}; agirlik.json",
                   f"{ANA[kod]} grubunun {ay_ad(t)} aylık TÜFE'ye katkısı (2026 tahmini ağırlıkla)")
            kaydet(f"ana{kod}_aylik{ek}", r[col], 2, "%", f"aylik.csv · {col}",
                   f"{ANA[kod]} grubu {ay_ad(t)} aylık değişim")
            satir.setdefault(kod, {})[t.strftime("%Y-%m")] = {"katki": float(c[col]), "aylik": float(r[col]),
                                                                "katki_w25": float(c25[col])}
    for kod in ANA:
        kaydet(f"ana{kod}_katki_degisim", satir[kod]["2026-09"]["katki"] - satir[kod]["2026-08"]["katki"], 2,
               "puan", "aylık katkı farkı", f"{ANA[kod]} katkısının Ağustos'tan Eylül'e değişimi", arti=True)
        kaydet(f"ana{kod}_agirlik", w26["paylar"][f"ana_{kod}"] * 100, 1, "%", "agirlik.json · ana_grup.2026",
               f"{ANA[kod]} 2026 yıl başı ağırlığı (hattın kimlikten tahmini)")
    sira = sorted(ANA, key=lambda k: -satir[k]["2026-09"]["katki"])
    for i, kod in enumerate(sira[:3], 1):
        etiket(f"katki13_sira{i}_ad", ANA[kod], "aylık katkı sıralaması", f"Eylül'de en büyük {i}. katkı")
        kaydet(f"katki13_sira{i}_pay", satir[kod]["2026-09"]["katki"] / (aylik(a["tufe"]).loc[SON]) * 100, 1, "%",
               "katkı / manşet", f"{ANA[kod]} katkısının Eylül aylık TÜFE içindeki payı")
    kaydet("ana07_pay_agu", satir["07"]["2026-08"]["katki"] / aylik(a["tufe"]).loc[ONC] * 100, 1, "%",
           "katkı / manşet", "Ulaştırma katkısının Ağustos aylık TÜFE içindeki payı")
    # eğitim: TCMB'nin "Eylül'ü mekanik biçimde aşağı çekecek" öngörüsü geçen yılla kıyas ister
    r10 = aylik(a["ana_10"])
    for u, ek in ((pd.Timestamp("2025-09-01"), "2025_09"), (pd.Timestamp("2025-08-01"), "2025_08")):
        kaydet(f"ana10_aylik_{ek}", r10.loc[u], 2, "%", "aylik.csv · ana_10", f"Eğitim hizmetleri, {ay_ad(u)} aylık değişim")
    for yil in (2026, 2025):
        b2 = (a.loc[pd.Timestamp(f"{yil}-09-01"), "ana_10"] / a.loc[pd.Timestamp(f"{yil}-07-01"), "ana_10"] - 1) * 100
        kaydet(f"ana10_agu_eyl_{yil}", b2, 2, "%", "aylik.csv · ana_10",
               f"Eğitim hizmetleri, Ağustos ve Eylül {yil} birikimli değişim (Temmuz → Eylül)")
    ilk3 = sum(satir[k]["2026-09"]["katki"] for k in sira[:3])
    kaydet("katki13_ilk3_toplam", ilk3, 2, "puan", "aylık katkı", "Eylül'de en büyük üç grubun katkı toplamı")
    kaydet("katki13_ilk3_pay", ilk3 / aylik(a["tufe"]).loc[SON] * 100, 1, "%", "katkı / manşet",
           "en büyük üç grubun Eylül aylık TÜFE içindeki payı")
    deg = sorted(ANA, key=lambda k: -abs(satir[k]["2026-09"]["katki"] - satir[k]["2026-08"]["katki"]))
    for i, kod in enumerate(deg[:4], 1):
        etiket(f"katki13_degisen{i}_ad", ANA[kod], "katkı farkı sıralaması",
               f"katkısı Ağustos'a göre en çok değişen {i}. grup")
    out["ana"] = satir
    out["ana_sira"] = sira
    return out


def dagilim_revizyon(dg: pd.DataFrame, d0909: pd.DataFrame) -> None:
    """Yayılımın bir aylık revizyonu: Ağustos ve Temmuz ölçüleri Ağustos verisiyle 9 Eylül'de hesaplanmıştı
    (arşivde `dagilim_0909.csv`); bugünkü değerle farkı aynı ayın revizyonudur."""
    sina(d0909.index[-1] == ONC, "9 Eylül dağılım dosyası Ağustos'ta bitmiyor")
    agu, tem = ONC, pd.Timestamp("2026-07-01")
    kaydet("difuzyon_hedef_agu_0909", d0909.loc[agu, "difuzyon_hedef"], 1, "%", "dagilim_0909.csv · difuzyon_hedef",
           "Ağustos'un hedef üstü kalem ağırlığı, 9 Eylül hesabı")
    kaydet("difuzyon_hedef_rev_agu", d0909.loc[agu, "difuzyon_hedef"] - dg.loc[agu, "difuzyon_hedef"], 1, "puan",
           "dagilim_0909.csv; dagilim.csv", "Ağustos hedef üstü oranının 9 Eylül'den bugüne revizyonu")
    kaydet("difuzyon_hedef_rev_tem", d0909.loc[tem, "difuzyon_hedef"] - dg.loc[tem, "difuzyon_hedef"], 1, "puan",
           "dagilim_0909.csv; dagilim.csv", "Temmuz hedef üstü oranının 9 Eylül'den bugüne revizyonu")
    kaydet("difuzyon_hedef_degisim", dg.loc[agu, "difuzyon_hedef"] - dg.loc[SON, "difuzyon_hedef"], 1, "puan",
           "dagilim.csv", "hedef üstü kalem ağırlığının Ağustos'tan Eylül'e düşüşü (bugünkü hesap)")
    kaydet("difuzyon_hedef_degisim_tem", dg.loc[tem, "difuzyon_hedef"] - dg.loc[agu, "difuzyon_hedef"], 1, "puan",
           "dagilim.csv", "hedef üstü kalem ağırlığının Temmuz'dan Ağustos'a düşüşü (bugünkü hesap)")
    kaydet("difuzyon_hedef_degisim_2ay", dg.loc[tem, "difuzyon_hedef"] - dg.loc[SON, "difuzyon_hedef"], 1, "puan",
           "dagilim.csv", "hedef üstü kalem ağırlığının Temmuz'dan Eylül'e düşüşü (bugünkü hesap)")
    kaydet("medyan_3a_agu_0909", d0909.loc[agu, "medyan_saar3"], 2, "%", "dagilim_0909.csv · medyan_saar3",
           "Ağustos'un medyan momentumu, 9 Eylül hesabı")
    kaydet("medyan_3a_rev_agu", d0909.loc[agu, "medyan_saar3"] - dg.loc[agu, "medyan_saar3"], 2, "puan",
           "dagilim_0909.csv; dagilim.csv", "Ağustos medyan momentumunun 9 Eylül'den bugüne revizyonu")
    kaydet("medyan_3a_degisim", dg.loc[agu, "medyan_saar3"] - dg.loc[SON, "medyan_saar3"], 2, "puan",
           "dagilim.csv", "medyan momentumunun Ağustos'tan Eylül'e düşüşü (bugünkü hesap)")


def dagilim(dg: pd.DataFrame, oz: dict) -> None:
    for t, ek in ((SON, ""), (ONC, "_agu"), (pd.Timestamp("2026-07-01"), "_tem")):
        r = dg.loc[t]
        kaydet(f"difuzyon_hedef{ek}", r["difuzyon_hedef"], 1, "%", "dagilim.csv · difuzyon_hedef",
               f"arındırılmış aylık değişimi hedefle uyumlu aylık oranın (%{sayi(oz['hedef_aylik'], 2)}) "
               f"üstünde olan üç haneli grupların ağırlık payı, {ay_ad(t)}")
        kaydet(f"difuzyon_0{ek}", r["difuzyon_0"], 1, "%", "dagilim.csv · difuzyon_0",
               f"arındırılmış aylık değişimi sıfırın üstünde olan grupların ağırlık payı, {ay_ad(t)}")
        kaydet(f"difuzyon_manset{ek}", r["difuzyon_mansete_gore"], 1, "%", "dagilim.csv · difuzyon_mansete_gore",
               f"arındırılmış aylık değişimi arındırılmış kesit ortalamasının üstünde olan grupların payı, {ay_ad(t)}")
        kaydet(f"medyan_aylik{ek}", r["medyan"], 2, "%", "dagilim.csv · medyan",
               f"ağırlıklı medyan arındırılmış aylık değişim, {ay_ad(t)}")
        kaydet(f"kirpma_aylik{ek}", r["kirpma_08"], 2, "%", "dagilim.csv · kirpma_08",
               f"%16 kırpılmış ortalama (her uçtan %8) arındırılmış aylık değişim, {ay_ad(t)}")
        kaydet(f"medyan_3a{ek}", r["medyan_saar3"], 2, "%", "dagilim.csv · medyan_saar3",
               f"medyanın son 3 ay ortalamasının yıllıklandırılmışı, {ay_ad(t)}")
        kaydet(f"kirpma_3a{ek}", r["kirpma_08_saar3"], 2, "%", "dagilim.csv · kirpma_08_saar3",
               f"kırpılmış ortalamanın son 3 ay ortalamasının yıllıklandırılmışı, {ay_ad(t)}")
    kaydet("kesit_n", dg.loc[SON, "kesit_n"], 0, "", "dagilim.csv · kesit_n",
           "Eylül kesitindeki üç haneli grup sayısı (45 grubun ikisi — 095, 105 — Eylül'de veri vermedi)")
    sina(abs(round(dg.loc[SON, "difuzyon_hedef"], 1) - oz["difuzyon_hedef"]) < 0.06, "difüzyon hattınkiyle ayrışıyor")
    sina(abs(round(dg.loc[SON, "medyan"], 2) - oz["medyan_aylik"]) < 0.006, "medyan hattınkiyle ayrışıyor")
    sina(abs(round(dg.loc[SON, "kirpma_08"], 2) - oz["kirpma_aylik"]) < 0.006, "kırpılmış ortalama ayrışıyor")


def beklenti(a: pd.DataFrame, oz: dict, bek: dict) -> None:
    m = aylik(a["tufe"].dropna())
    kaydet("pka_eylul", a.loc[SON, "pka_ay_cari"], 2, "%", "aylik.csv · pka_ay_cari",
           "TCMB Piyasa Katılımcıları Anketi, Eylül 2026 anketinin Eylül aylık TÜFE beklentisi")
    kaydet("pka_eylul_h1", a.loc[ONC, "pka_ay_1"], 2, "%", "aylik.csv · pka_ay_1",
           "Ağustos 2026 anketinin bir sonraki ay (Eylül) için aylık TÜFE beklentisi")
    kaydet("pka_eylul_h2", a.loc[pd.Timestamp("2026-07-01"), "pka_ay_2"], 2, "%", "aylik.csv · pka_ay_2",
           "Temmuz 2026 anketinin iki ay sonrası (Eylül) için aylık TÜFE beklentisi")
    e = (m - a["pka_ay_cari"]).dropna()
    kaydet("pka_surpriz", e.loc[SON], 2, "puan", "aylik.csv · tufe, pka_ay_cari",
           "gerçekleşen − anket (Eylül 2026)")
    sina(abs(round(e.loc[SON], 2) - oz["anket_ay_surpriz"]) < 0.006, "anket sürprizi hattınkiyle ayrışıyor")
    e36 = e.tail(36)
    sina(e36.index[-1] == SON and len(e36) == 36, "36 aylık isabet penceresi Eylül'de bitmiyor")
    mae = float(e36.abs().mean())
    kaydet("pka_mae36", mae, 2, "puan", "aylik.csv", "anketin son 36 aydaki (Ekim 2023–Eylül 2026) ortalama mutlak hatası")
    kaydet("pka_yanlilik36", float(e36.mean()), 2, "puan", "aylik.csv",
           "son 36 ayda ortalama hata (gerçekleşen − anket; artı: anket eksik tahmin etmiş)", arti=True)
    kaydet("pka_rmse36", float(np.sqrt((e36 ** 2).mean())), 2, "puan", "aylik.csv",
           "son 36 ayda hata kareleri ortalamasının karekökü")
    sina(abs(round(mae, 2) - oz["isabet_h0_p36_mae"]) < 0.006, "anket MAE hattınkiyle ayrışıyor")
    kaydet("pka_surpriz_mae_kati", abs(e.loc[SON]) / mae, 2, "", "aylik.csv", "|sürpriz| / ortalama mutlak hata")
    onceki = e36.iloc[:-1]
    kaydet("pka_buyuk_hata_ay", int((onceki.abs() > abs(e.loc[SON])).sum()), 0, "", "aylik.csv",
           "önceki 35 ayın kaçında anketin mutlak hatası bu ayınkinden büyüktü")
    kaydet("pka_fazla_tahmin_ay", int((e36 < 0).sum()), 0, "", "aylik.csv",
           "son 36 ayın kaçında gerçekleşme anketin altında kaldı (Eylül dahil)")
    e12 = e.tail(12)
    kaydet("pka_fazla_tahmin_12", int((e12 < 0).sum()), 0, "", "aylik.csv",
           "son 12 ayın kaçında gerçekleşme anketin altında kaldı (Eylül dahil)")
    # ileri patika ve 12 ay
    for k, kol, ad in (("pka_ekim", "pka_ay_1", "Ekim 2026 aylık"), ("pka_kasim", "pka_ay_2", "Kasım 2026 aylık"),
                       ("pka_yilsonu", "pka_yilsonu", "2026 yıl sonu yıllık"),
                       ("pka_12a", "pka_12a", "12 ay sonrası (Eylül 2027) yıllık"),
                       ("pka_24a", "pka_24a", "24 ay sonrası yıllık")):
        kaydet(k, a.loc[SON, kol], 2, "%", f"aylik.csv · {kol}", f"Eylül 2026 anketinin {ad} TÜFE beklentisi")
    kaydet("pka_yilsonu_agu", a.loc[ONC, "pka_yilsonu"], 2, "%", "aylik.csv · pka_yilsonu",
           "Ağustos 2026 anketinin 2026 yıl sonu beklentisi")
    kaydet("pka_katilimci", a.loc[SON, "pka_12a_n"], 0, "", "aylik.csv · pka_12a_n", "Eylül anketinin katılımcı sayısı")
    sina(bek["ileri"]["h1"]["oran"] == round(float(a.loc[SON, "pka_ay_1"]), 2), "beklenti.json ileri patikası ayrışıyor")
    # İTO (öncü) ve hattın kural seti
    kaydet("ito_model_merkez", oz["br_k_merkez"], 2, "%", "enflasyon_ozet.json · br_k_merkez",
           "hattın İTO regresyonunun Eylül tahmini (İTO yayımından sonra, TÜFE'den önce)")
    kaydet("ito_model_sapma", oz["br_k_merkez_sapma"], 2, "puan", "enflasyon_ozet.json · br_k_merkez_sapma",
           "İTO regresyonu − gerçekleşen (artı: model yüksek tahmin etti)", arti=True)
    kaydet("ito_model_p25", oz["br_k_p25"], 2, "%", "enflasyon_ozet.json · br_k_p25", "İTO tahmin bulutunun 25. yüzdeliği")
    kaydet("ito_model_p75", oz["br_k_p75"], 2, "%", "enflasyon_ozet.json · br_k_p75", "İTO tahmin bulutunun 75. yüzdeliği")
    # Dış kaynak: AA Finans beklenti anketi (sabah bülteninin aktardığı) — ölçülmez, adıyla taşınır
    dis = "AA Finans Enflasyon Beklenti Anketi (5 Ekim 2026 sabah bülteninin aktarımı)"
    aa = kaydet("aa_beklenti", 2.18, 2, "%", "dış kaynak", "AA Finans anketinde 20 ekonomistin Eylül aylık TÜFE beklentisinin ortalaması", dis=dis)
    kaydet("aa_alt", 1.90, 2, "%", "dış kaynak", "AA Finans anketinde en düşük tahmin", dis=dis)
    kaydet("aa_ust", 2.60, 2, "%", "dış kaynak", "AA Finans anketinde en yüksek tahmin", dis=dis)
    kaydet("aa_katilimci", 20, 0, "", "dış kaynak", "AA Finans anketine katılan ekonomist sayısı", dis=dis)
    kaydet("aa_surpriz", m.loc[SON] - aa, 2, "puan", "aylik.csv · tufe − dış kaynak",
           "gerçekleşen − AA Finans ortalaması")
    kaydet("aa_alt_fark", m.loc[SON] - 1.90, 2, "puan", "aylik.csv · tufe − dış kaynak",
           "gerçekleşen − AA Finans en düşük tahmini (eksi: en düşük tahminin de altında)")
    t = a["tufe"].dropna()
    ima = ((t.loc[ONC] * (1 + aa / 100)) / t.loc[pd.Timestamp("2025-09-01")] - 1) * 100
    kaydet("aa_ima_yillik", ima, 2, "%", "aylik.csv · tufe ve dış kaynak",
           "AA Finans ortalaması (%2,18) gerçekleşseydi Eylül yıllık TÜFE")
    ima_p = ((t.loc[ONC] * (1 + a.loc[SON, "pka_ay_cari"] / 100)) / t.loc[pd.Timestamp("2025-09-01")] - 1) * 100
    kaydet("pka_ima_yillik", ima_p, 2, "%", "aylik.csv · tufe, pka_ay_cari",
           "TCMB anketinin Eylül beklentisi (%2,12) gerçekleşseydi Eylül yıllık TÜFE")


def yil_sonu(a: pd.DataFrame, sa: pd.DataFrame, oz: dict, baz: pd.DataFrame) -> dict:
    """Baz aritmetiği: 1+π^(12)_{t+h} = (1+π^(12)_t)·Π(1+π_{t+s})/Π(1+π_{t+s−12}).
    Paydadaki çarpım TAMAMEN bilinir; senaryo yalnız payın aylık varsayımıdır."""
    t = a["tufe"].dropna()
    m = (t / t.shift(1) - 1)
    msa = (sa["tufe"] / sa["tufe"].shift(1) - 1).dropna()
    y0 = float(t.loc[SON] / t.loc[SON - pd.DateOffset(months=12)] - 1)
    ufuk = [SON + pd.DateOffset(months=h) for h in range(1, 13)]
    dusen = [float(m.loc[u - pd.DateOffset(months=12)]) for u in ufuk]
    for u, d in zip(ufuk[:3], dusen[:3]):
        kaydet(f"baz_{u.month:02d}", d * 100, 2, "%", "aylik.csv · tufe",
               f"{AY[u.month]} 2025 aylık TÜFE — {AY[u.month]} 2026'da yıllık orandan düşecek ay")
    kum = float(t.loc[SON] / t.loc[ARA25] - 1) * 100
    kaydet("ys_kumulatif", kum, 2, "%", "aylik.csv · tufe", "Aralık 2025 → Eylül 2026 birikimli TÜFE")
    mom = float((1 + msa.tail(3)).prod() ** (1 / 3) - 1)
    son12 = float((1 + m.dropna().tail(12)).prod() ** (1 / 12) - 1)
    kaydet("mom_aylik", mom * 100, 2, "%", "sa.csv · tufe",
           "momentum: arındırılmış son 3 ayın (Temmuz–Eylül) geometrik ortalama aylık değişimi")
    kaydet("son12_aylik", son12 * 100, 2, "%", "aylik.csv · tufe", "son 12 ayın geometrik ortalama aylık değişimi")
    # anketin patikası: Ekim ve Kasım anketin kendi aylık beklentisi, Aralık yıl sonu beklentisinden ima
    # edilir, Ocak–Eylül 2027 sabit aylık hızla 12 ay sonrası beklentiye (Eylül 2027) bağlanır.
    ek, ka = a.loc[SON, "pka_ay_1"] / 100, a.loc[SON, "pka_ay_2"] / 100
    ys, y12 = a.loc[SON, "pka_yilsonu"] / 100, a.loc[SON, "pka_12a"] / 100
    ara = (1 + ys) / ((1 + kum / 100) * (1 + ek) * (1 + ka)) - 1
    sonra = ((1 + y12) / ((1 + ek) * (1 + ka) * (1 + ara))) ** (1 / 9) - 1
    kaydet("pka_aralik_ima", ara * 100, 2, "%", "aylik.csv · pka_yilsonu, pka_ay_1, pka_ay_2",
           "anketin yıl sonu, Ekim ve Kasım beklentilerinin birlikte ima ettiği Aralık 2026 aylık TÜFE")
    kaydet("pka_2027_aylik_ima", sonra * 100, 2, "%", "aylik.csv · pka_12a ve yukarıdaki",
           "anketin 12 ay sonrası beklentisine (Eylül 2027) varmak için Ocak–Eylül 2027'de gereken sabit aylık oran")
    gereken = ((1 + ys) / (1 + kum / 100)) ** (1 / 3) - 1
    kaydet("ys_gereken_aylik", gereken * 100, 2, "%", "aylik.csv · tufe, pka_yilsonu",
           "anketin yıl sonu beklentisine varmak için Ekim–Aralık'ta gereken sabit HAM aylık oran")
    sina(abs(round(gereken * 100, 2) - oz["ys_gereken_aylik"]) < 0.006, "gereken aylık hattınkiyle ayrışıyor")
    sina(abs(round(kum, 2) - oz["ys_kumulatif"]) < 0.006, "birikimli TÜFE hattınkiyle ayrışıyor")
    # MEVSİM: momentum ARINDIRILMIŞ bir hızdır, düşen aylar ve eşikler HAM. Aynı birime çevirmek için gelen
    # aya o takvim ayının mevsim çarpanı (ham/arındırılmış aylık oranı) uygulanır. Çarpan yıldan yıla büyüyor;
    # ana kıyas son yılın (Ekim–Aralık 2025, Ocak–Eylül 2026) çarpanı, duyarlılık 2022–2024 çarpanları.
    mev = (1 + m) / (1 + msa) - 1

    def carpan(yil: int) -> list[float]:
        return [float(mev.loc[pd.Timestamp(f"{yil if u.month >= 10 else yil + 1}-{u.month:02d}-01")]) for u in ufuk]

    carp = {y_: carpan(y_) for y_ in (2025, 2024, 2023, 2022)}
    for ay_, ad_ in ((11, "kasim"),):
        for y_ in (2022, 2025):
            kaydet(f"mevsim_{ad_}_{y_}", float(mev.loc[pd.Timestamp(f"{y_}-{ay_:02d}-01")]) * 100, 2, "puan",
                   "aylik.csv; sa.csv · tufe", f"{AY[ay_]} {y_} mevsim çarpanı (ham − arındırılmış aylık, çarpımsal)")
    for u, ad_ in ((pd.Timestamp("2025-11-01"), "11"), (pd.Timestamp("2025-12-01"), "12")):
        kaydet(f"baz_{ad_}_sa", float(msa.loc[u]) * 100, 2, "%", "sa.csv · tufe",
               f"{AY[u.month]} 2025 arındırılmış aylık TÜFE (yıllık orandan düşecek ayın arındırılmış hâli)")
    senaryo = {
        "momentum": [mom] * 12,
        "son12": [son12] * 12,
        "anket": [ek, ka, ara] + [sonra] * 9,
        "gecen_yil": list(dusen),
        **{f"momentum_mev{y_ % 100}": [(1 + mom) * (1 + c) - 1 for c in carp[y_]] for y_ in carp},
        "son12_mev25": [(1 + son12) * (1 + c) - 1 for c in carp[2025]],
    }
    yol: dict[str, list[float]] = {}
    for ad, pat in senaryo.items():
        yol[ad] = []
        for h in range(1, 13):
            pay = float(np.prod([1 + x for x in pat[:h]]))
            payda = float(np.prod([1 + x for x in dusen[:h]]))
            yol[ad].append(((1 + y0) * pay / payda - 1) * 100)
    # hattın baz_* hesabıyla karşılaştırma (momentum, son 12, geçen yıl)
    for ad, kol in (("momentum", "son3_sa"), ("son12", "son12_ort"), ("gecen_yil", "gecen_yil")):
        fark = max(abs(x - y) for x, y in zip(yol[ad], baz[kol].values))
        sina(fark < 1e-6, f"baz senaryosu '{ad}' hattınkiyle ayrışıyor (azami {fark:.2e} puan)")
        D.setdefault("_sinama", {})[f"baz_{ad}_azami_fark"] = fark
    sina(max(abs(x - y0 * 100) for x in yol["gecen_yil"]) < 1e-9, "geçen yıl senaryosu yıllık oranı sabit tutmuyor")
    sina(abs(yol["anket"][2] - ys * 100) < 1e-9 and abs(yol["anket"][11] - y12 * 100) < 1e-9,
         "anket patikası yıl sonu ve 12 ay çıpalarını tutturmuyor")
    # Mevsimsiz momentum (arındırılmış hızın ham ay gibi bileşiklenmesi) yalnız hattın baz_senaryo'suyla aynı
    # hesabı yaptığımızın sınamasıdır; birimleri karıştırdığı için yazıya girmez ve değer olarak kaydedilmez.
    for ad, adm in (("momentum_mev25", "momentum (2025 mevsim çarpanlarıyla)"),
                    ("momentum_mev24", "momentum (2024 mevsim çarpanlarıyla)"),
                    ("son12_mev25", "son 12 ay ortalaması (2025 mevsim çarpanlarıyla)"),
                    ("anket", "anket patikası")):
        for i, ay in ((0, "ekim"), (1, "kasim"), (2, "aralik")):
            kaydet(f"yol_{ad}_{ay}", yol[ad][i], 2, "%", "baz aritmetiği", f"{adm} senaryosunda {AY[i + 10]} 2026 yıllık TÜFE")
        kaydet(f"yol_{ad}_2027_09", yol[ad][11], 2, "%", "baz aritmetiği", f"{adm} senaryosunda Eylül 2027 yıllık TÜFE")
    for ad in ("momentum_mev23", "momentum_mev22"):
        kaydet(f"yol_{ad}_aralik", yol[ad][2], 2, "%", "baz aritmetiği",
               f"momentum ({ad[-2:]} → 20{ad[-2:]} mevsim çarpanlarıyla) senaryosunda Aralık 2026 yıllık TÜFE")
    # momentumun HAM karşılığı (2025 çarpanlarıyla) ve eşiklerin ARINDIRILMIŞ karşılığı
    pm = senaryo["momentum_mev25"]
    kaydet("mom_ham25_ekim", pm[0] * 100, 2, "%", "sa.csv; aylik.csv", "momentumun Ekim için ham karşılığı (2025 Ekim çarpanı)")
    kaydet("mom_ham25_ekkas", (np.prod([1 + x for x in pm[:2]]) ** 0.5 - 1) * 100, 2, "%", "sa.csv; aylik.csv",
           "momentumun Ekim–Kasım için ham karşılığının geometrik ortalaması (2025 çarpanları)")
    kaydet("mom_ham25_eka", (np.prod([1 + x for x in pm[:3]]) ** (1 / 3) - 1) * 100, 2, "%", "sa.csv; aylik.csv",
           "momentumun Ekim–Aralık için ham karşılığının geometrik ortalaması (2025 çarpanları)")
    for y_ in (2025, 2024, 2023, 2022):
        pf = float(np.prod([1 + c for c in carp[y_][:3]]))
        kaydet(f"esik_aralik_sa{y_ % 100}", (((1 + ESIK_30 / 100) / (1 + kum / 100) / pf) ** (1 / 3) - 1) * 100, 2, "%",
               "baz aritmetiği; sa.csv",
               f"yıl sonu %30 eşiğinin arındırılmış karşılığı: Ekim–Aralık'ta geçilmemesi gereken sabit arındırılmış "
               f"aylık hız ({y_} mevsim çarpanlarıyla)")
    pf25 = float(np.prod([1 + c for c in carp[2025][:3]]))
    kaydet("ys_gereken_sa25", (((1 + ys) / (1 + kum / 100) / pf25) ** (1 / 3) - 1) * 100, 2, "%", "aylik.csv; sa.csv",
           "anketin yıl sonu beklentisine varmak için gereken sabit arındırılmış aylık hız (2025 çarpanlarıyla)")
    # eşikler: Ekim'de yıllık oranın %30'un altında kalması ve yıl sonunda %30 için gereken aylık
    ekim_esik = ((1 + ESIK_30 / 100) * (1 + dusen[0]) / (1 + y0) - 1) * 100
    kaydet("esik_ekim_aylik", ekim_esik, 2, "%", "baz aritmetiği",
           "Ekim yıllık TÜFE'nin %30'u aşmaması için Ekim aylığının geçmemesi gereken düzey")
    kas_esik = (((1 + ESIK_30 / 100) * (1 + dusen[0]) * (1 + dusen[1]) / (1 + y0)) ** 0.5 - 1) * 100
    kaydet("esik_kasim_aylik", kas_esik, 2, "%", "baz aritmetiği",
           "Kasım yıllık TÜFE'nin %30'u aşmaması için Ekim–Kasım'da geçilmemesi gereken sabit aylık oran")
    ara_esik = (((1 + ESIK_30 / 100) / (1 + kum / 100)) ** (1 / 3) - 1) * 100
    kaydet("esik_aralik_aylik", ara_esik, 2, "%", "baz aritmetiği",
           "yıl sonu yıllık TÜFE'nin %30'u aşmaması için Ekim–Aralık'ta geçilmemesi gereken sabit aylık oran")
    kaydet("esik_aralik_sa25_mom_fark", D["esik_aralik_sa25"]["deger"] - mom * 100, 2, "puan", "baz aritmetiği",
           "yıl sonu %30 eşiğinin arındırılmış karşılığı (2025 çarpanları) − momentum")
    return {"ufuk": [u.strftime("%Y-%m") for u in ufuk],
            "yol": {k: yol[k] for k in ("anket", "momentum_mev25", "momentum_mev22", "son12_mev25")},
            "aylik": {k: [x * 100 for x in v] for k, v in senaryo.items()}, "dusen": [d * 100 for d in dusen]}


def reel(a: pd.DataFrame, rf: pd.DataFrame, g: pd.DataFrame, fon: dict, oz: dict, sa: pd.DataFrame) -> None:
    """Hattın tanımı: tam Fisher (1+i)/(1+π) − 1; i = TCMB ağırlıklı ortalama fonlama maliyetinin ay
    içi son kotasyonu (bugün politika faizine eşit)."""
    def f(i, p):
        return ((1 + i / 100) / (1 + p / 100) - 1) * 100
    i = float(g["aofm"].dropna().iloc[-1])
    gun = g["aofm"].dropna().index[-1]
    etiket("aofm_gun", f"{gun:%d.%m.%Y}", "gunluk.csv · aofm", "fonlama maliyetinin son kotasyon günü")
    kaydet("aofm", i, 2, "%", "gunluk.csv · aofm", "TCMB ağırlıklı ortalama fonlama maliyeti, son kotasyon")
    kaydet("politika", fon["politika"], 2, "%", "fonlama_ozet.json · politika", "politika faizi (bir hafta vadeli repo)")
    kaydet("politika_yalin", fon["politika"], 0, "%", "fonlama_ozet.json · politika", "politika faizi (tam sayı yazımı)")
    kaydet("politika_onceki", fon["politika_onceki"], 2, "%", "fonlama_ozet.json · politika_onceki",
           "22 Ocak 2026'dan önceki politika faizi")
    etiket("politika_son_degisim", fon["politika_son_degisim"], "fonlama_ozet.json", "politika faizinin son değiştiği gün")
    gunler = (pd.Timestamp("2026-10-05") - pd.Timestamp("2026-01-22")).days
    kaydet("politika_sabit_gun", gunler, 0, "gün", "takvim", "22 Ocak 2026'dan 5 Ekim 2026'ya gün sayısı")
    kaydet("ppk_kalan_gun", (pd.Timestamp("2026-10-22") - pd.Timestamp("2026-10-05")).days, 0, "gün", "takvim",
           "5 Ekim'den 22 Ekim PPK toplantısına gün sayısı")
    kaydet("tlref", fon["tlref"], 2, "%", "fonlama_ozet.json · tlref", "TLREF, 2 Ekim 2026")
    kaydet("koridor_ust", fon["koridor_ust"], 2, "%", "fonlama_ozet.json · koridor_ust", "gecelik borç verme faizi")
    kaydet("koridor_alt", fon["koridor_alt"], 2, "%", "fonlama_ozet.json · koridor_alt", "gecelik borçlanma faizi")
    p12 = float(yillik(a["tufe"]).loc[SON]); p12a = float(yillik(a["tufe"]).loc[ONC])
    kaydet("reel_expost", f(i, p12), 2, "%", "Fisher · aofm, TÜFE yıllık", "gerçekleşene bakan reel faiz (Eylül yıllık TÜFE ile)")
    kaydet("reel_expost_agu", f(float(rf.loc[ONC, "faiz"]), p12a), 2, "%", "reel_faiz.csv · faiz; aylik.csv",
           "gerçekleşene bakan reel faiz, Ağustos TÜFE'siyle")
    kaydet("reel_exante", f(i, float(a.loc[SON, "pka_12a"])), 2, "%", "Fisher · aofm, pka_12a",
           "ileriye bakan reel faiz (anketin 12 ay sonrası beklentisiyle)")
    kaydet("reel_exante_agu", f(float(rf.loc[ONC, "faiz"]), float(a.loc[ONC, "pka_12a"])), 2, "%",
           "reel_faiz.csv · faiz; aylik.csv · pka_12a", "ileriye bakan reel faiz, Ağustos anketiyle")
    q = float(saar3(sa["tufe"]).loc[SON])
    kaydet("reel_egilim", f(i, q), 2, "%", "Fisher · aofm, arındırılmış 3 aylık eğilim",
           "eğilime bakan reel faiz (arındırılmış son 3 ayın yıllıklandırılmışıyla)")
    kaydet("reel_egilim_agu", f(float(rf.loc[ONC, "faiz"]), float(saar3(sa["tufe"]).loc[ONC])), 2, "%",
           "Fisher · reel_faiz.csv faiz, sa.csv", "eğilime bakan reel faiz, Ağustos (bugünkü arındırma sürümü)")
    kaydet("reel_ileri", f(float(a.loc[SON, "pka_faiz_12a"]), float(a.loc[SON, "pka_24a"])), 2, "%",
           "Fisher · pka_faiz_12a, pka_24a", "12 ay sonrası beklenen politika faizi ile 24 ay sonrası beklenen enflasyon")
    kaydet("reel_ileri_agu", f(float(a.loc[ONC, "pka_faiz_12a"]), float(a.loc[ONC, "pka_24a"])), 2, "%",
           "Fisher · pka_faiz_12a, pka_24a (Ağustos anketi)", "ileriye dönük reel politika faizi, Ağustos anketiyle")
    sina(abs(D["reel_ileri_agu"]["deger"] - float(rf.loc[ONC, "ileri_ex_ante"])) < 1e-6,
         "reel_ileri_agu hattın reel_faiz.csv'siyle ayrışıyor")
    kaydet("pka_faiz_12a", a.loc[SON, "pka_faiz_12a"], 2, "%", "aylik.csv · pka_faiz_12a",
           "anketin 12 ay sonrası politika faizi beklentisi")
    kaydet("pka_faiz_indirim", (i - float(a.loc[SON, "pka_faiz_12a"])) * 100, 0, "bp", "aofm − pka_faiz_12a",
           "anketin 12 ay içinde beklediği toplam indirim")
    for k, kol in (("reel_expost", "ex_post"), ("reel_exante", "ex_ante"), ("reel_egilim", "egilime_gore"),
                   ("reel_ileri", "ileri_ex_ante")):
        sina(abs(D[k]["deger"] - float(rf.loc[SON, kol])) < 1e-6, f"{k} hattın reel_faiz.csv'siyle ayrışıyor")
    sina(abs(round(D["reel_expost"]["deger"], 2) - oz["reel_expost"]) < 0.006, "ex post hattın özetiyle ayrışıyor")


def piyasa(dibs: dict, tufex: dict, a: pd.DataFrame) -> None:
    """Veri yayımından ÖNCEKİ seans (2 Ekim 2026 Cuma kapanışı). Yayıma tepki burada yok."""
    for k in ("_tarih",):
        sina(dibs[k] == "02.10.2026" and tufex[k] == "02.10.2026", "piyasa panoları 2 Ekim kapanışı değil")
    for k, ad in (("spot_3a", "3 aylık"), ("spot_6a", "6 aylık"), ("spot_1y", "1 yıllık"), ("spot_2y", "2 yıllık"),
                  ("spot_5y", "5 yıllık"), ("forward_1y1y", "1 yıl sonrası 1 yıllık vadeli")):
        kaydet(f"dibs_{k}", dibs[k], 2, "%", f"dibs_ozet.json · {k}", f"DİBS sıfır kuponlu {ad} getiri, 2 Ekim 2026")
    for k, ad in (("basabas_1y", "1 yıllık başabaş enflasyon"), ("basabas_2y", "2 yıllık başabaş enflasyon"),
                  ("reel_1y", "1 yıllık TÜFEX reel getiri"), ("prim_1y", "1 yıllık başabaş − anket (enflasyon riski primi)")):
        kaydet(f"tufex_{k}", tufex[k], 2, "%" if k != "prim_1y" else "puan", f"tufex_ozet.json · {k}",
               f"{ad}, 2 Ekim 2026")
    for k, ad in (("kiyas_1ay_1y_degisim_bp", "1 yıllık getirinin son bir aydaki değişimi (2 Eylül → 2 Ekim)"),
                  ("kiyas_3ay_1y_degisim_bp", "1 yıllık getirinin son üç aydaki değişimi (2 Temmuz → 2 Ekim)")):
        kaydet(f"dibs_{k}", dibs[k], 0, "bp", f"dibs_ozet.json · {k}", ad, arti=True)
    # KONVANSİYON: strip getirisi yıllık BİLEŞİK, politika faizi BASİT yayımlanır (1 hafta vadeli repo).
    # Kıyaslanabilir ölçü politika faizinin bileşiğe çevrilmiş hâlidir (DİBS hattının politika_bilesik'i:
    # (1+r·7/365)^(365/7)−1). Basit faizle kıyas işareti TERS çıkarır; ham fark yalnız bu uyarıyla tutulur.
    kaydet("politika_bilesik", dibs["politika_bilesik"], 2, "%", "dibs_ozet.json · politika_bilesik",
           "politika faizinin yıllık bileşiğe çevrilmiş hâli (1 hafta vade, haftalık yenileme)")
    kaydet("dibs_1y_politika_bilesik", (dibs["spot_1y"] - dibs["politika_bilesik"]) * 100, 0, "bp",
           "dibs_ozet.json · spot_1y, politika_bilesik",
           "1 yıllık sıfır kuponlu getiri − bileşiğe çevrilmiş politika faizi (aynı konvansiyon), 2 Ekim 2026", arti=True)
    for k, ad in (("3a", "3 aylık"), ("6a", "6 aylık")):
        kaydet(f"dibs_{k}_politika_bilesik", (dibs[f"spot_{k}"] - dibs["politika_bilesik"]) * 100, 0, "bp",
               f"dibs_ozet.json · spot_{k}, politika_bilesik",
               f"{ad} sıfır kuponlu getiri − bileşiğe çevrilmiş politika faizi, 2 Ekim 2026", arti=True)
    kaydet("dibs_1y_politika_ham", (dibs["spot_1y"] - dibs["politika"]) * 100, 0, "bp",
           "dibs_ozet.json · spot_1y, politika",
           "1 yıllık getiri (bileşik) − politika faizi (basit): KONVANSİYONLARI FARKLI, yön hükmü bundan kurulmaz",
           arti=True)
    kaydet("basabas_1y_gercek_fark", tufex["basabas_1y"] - float(yillik(a["tufe"]).loc[SON]), 2, "puan",
           "tufex_ozet.json · basabas_1y; aylik.csv", "1 yıllık başabaş (2 Ekim) − Eylül yıllık TÜFE", arti=True)
    kaydet("basabas_1y_agu_fark", tufex["basabas_1y"] - float(yillik(a["tufe"]).loc[ONC]), 2, "puan",
           "tufex_ozet.json · basabas_1y; aylik.csv", "1 yıllık başabaş (2 Ekim) − Ağustos yıllık TÜFE", arti=True)


def sekil_serileri(a: pd.DataFrame, kat: dict, ys: dict) -> dict:
    """Figürlerin çizdiği seriler — figür bu dosyadan başka hiçbir yerden okumaz."""
    son24 = [SON - pd.DateOffset(months=i) for i in range(23, -1, -1)]
    m = {k: aylik(a[c]) for k, c in (("tufe", "tufe"), ("b", "cekirdek_b"), ("c", "cekirdek_c"))}
    s01 = {"ay": [t.strftime("%Y-%m") for t in son24],
           **{k: [round(float(v.loc[t]), 4) for t in son24] for k, v in m.items()},
           "pka": [round(float(a.loc[t, "pka_ay_cari"]), 2) if pd.notna(a.loc[t, "pka_ay_cari"]) else None
                   for t in son24]}
    son36 = [SON - pd.DateOffset(months=i) for i in range(35, -1, -1)]
    y = {k: yillik(a[c]) for k, c in (("hizmet", "hizmet"), ("mal", "temel_mal"), ("kira", "kira"),
                                       ("tufe", "tufe"))}
    s04 = {"ay": [t.strftime("%Y-%m") for t in son36],
           **{k: [round(float(v.loc[t]), 4) for t in son36] for k, v in y.items()}}
    yt = yillik(a["tufe"])
    s03 = {"gercek_ay": [t.strftime("%Y-%m") for t in son24],
           "gercek": [round(float(yt.loc[t]), 4) for t in son24], **ys}
    defter = {
        "01_aylik": {"seriler": "TÜFE, B, C aylık; anket (PKA) aylık beklentisi", "bas": s01["ay"][0],
                     "son": s01["ay"][-1]},
        "02_katki": {"seriler": "13 ana grubun aylık katkısı", "aylar": ["2026-08", "2026-09"],
                     "son": "2026-09"},
        "03_yillik_yol": {"seriler": "yıllık TÜFE ve baz senaryoları", "gercek_son": s03["gercek_ay"][-1],
                          "senaryo_son": ys["ufuk"][-1]},
        "04_hizmet_mal": {"seriler": "hizmet, temel mallar, kira, TÜFE yıllık", "bas": s04["ay"][0],
                          "son": s04["ay"][-1]},
    }
    return {"01": s01, "02": {"ana": kat["ana"], "sira": kat["ana_sira"], "ad": ANA}, "03": s03, "04": s04,
            "defter": defter}


def main() -> int:
    kunye, ham = arsiv()
    a = csv(ham, "aylik.csv")
    sa = csv(ham, "sa.csv")
    kat = csv(ham, "katki.csv")
    dg = csv(ham, "dagilim.csv")
    d0909 = csv(ham, "dagilim_0909.csv")
    rf = csv(ham, "reel_faiz.csv")
    g = csv(ham, "gunluk.csv")
    baz = csv(ham, "baz_senaryo.csv")
    oz = js(ham, "enflasyon_ozet.json")
    agr = js(ham, "agirlik.json")
    bek = js(ham, "beklenti.json")
    dibs, fon, tufex = js(ham, "dibs_ozet.json"), js(ham, "fonlama_ozet.json"), js(ham, "tufex_ozet.json")
    sina(oz["_tarih"] == "09.2026", f"enflasyon özeti Eylül 2026 değil: {oz['_tarih']}")
    sina(a["tufe"].dropna().index[-1] == SON, "aylık TÜFE serisi Eylül 2026'da bitmiyor")
    # kısmi yayım: geride kalan seriler yazıya girmez — hangileri olduğu ölçülür, adıyla yazılır
    geride = [c for c in ("yonetilen_haric", "oktg01", "oktg02", "oktg07")
              if pd.isna(a.loc[SON, c])]
    etiket("kismi_yayim_geride", ", ".join(geride), "aylik.csv",
           "Eylül değeri arşivde olmayan seriler (yönetilen fiyatlar hariç endeks, özel kapsamlı TÜFE kontrol "
           "kopyası, A, F) — yazının hiçbir ölçüsüne girmez")
    kaydet("kismi_yayim_n", len(geride), 0, "", "aylik.csv", "Eylül değeri arşivde olmayan seri sayısı")

    manset(a, oz)
    gecmis(a)
    baz_yuku(a, sa)
    mevsim(sa, a, oz)
    kt = katkilar(a, agr, kat)
    dagilim(dg, oz)
    dagilim_revizyon(dg, d0909)
    beklenti(a, oz, bek)
    ys = yil_sonu(a, sa, oz, baz)
    reel(a, rf, g, fon, oz, sa)
    piyasa(dibs, tufex, a)
    seriler = sekil_serileri(a, kt, ys)

    if hatalar:
        print(f"✗ ölçüm · {len(hatalar)} sınama tutmadı")
        for h in hatalar:
            print("  ·", h)
        return 1
    sinama = D.pop("_sinama", {})
    cikti = {
        "cipa": CIPA,
        "veri_ayi": "2026-09",
        "arsiv": {ad: k["sha256"] for ad, k in kunye["dosyalar"].items()},
        "olcum_py_oz": hashlib.sha256((BURASI / "olcum.py").read_bytes()).hexdigest(),
        "sozlesme": "ondalık virgül · binlik nokta · eksi U+2212 · yüzde önde · puan/bp arkada",
        "degerler": D,
        "sinama": sinama,
        "seriler": seriler,
    }
    CIKTI.write_text(json.dumps(cikti, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    sayilar = sum(1 for v in D.values() if "deger" in v)
    print(f"✓ ölçüm · {sayilar} sayı, {len(D) - sayilar} etiket · {CIKTI.relative_to(BURASI)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
