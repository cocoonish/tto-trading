#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bülten — cross-asset piyasa katmanı.

Kurumsal bir sabah bülteninin omurgası: bir trader'ın güne başlarken bilmesi
gereken fiyatlar ve bunların günlük/haftalık/aylık/yılbaşından bu yana değişimi.
TL faizleri ve DİBS eğrisi bu deponun kendi hatlarından, geri kalanı piyasa
verisinden gelir.

Tasarım kararları:
· GETİRİLER baz puanla, fiyatlar yüzdeyle raporlanır. Bir tahvil getirisinin
  "%2 arttı" denmesi trader için anlamsızdır; "8 baz puan arttı" anlamlıdır.
· Kapalı piyasa: hafta sonu "günlük değişim" son iki işlem gününün farkıdır ve
  hangi tarihe ait olduğu satırda YAZAR. Cumartesi sabahı cuma kapanışını
  "bugünkü hareket" diye sunmak yanıltıcı olurdu.
· Türev büyüklükler (2s10s, crack spread, altın/gümüş oranı) burada HESAPLANIR;
  yorum katmanına hazır gelir, orada yeniden hesaplanıp hata yapılmaz.
· Önbellek: aynı gün içinde tekrar koşulursa ağ beklenmez (varsayılan 4 saat).
"""
from __future__ import annotations

import json
import warnings
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from pathlib import Path

warnings.filterwarnings("ignore")

BURASI = Path(__file__).resolve().parent
ONBELLEK = BURASI / "onbellek"
ONBELLEK.mkdir(exist_ok=True)
HAM = ONBELLEK / "piyasa_ham.json"
TTL_SAAT = 4


@dataclass
class Varlik:
    kod: str
    ad: str
    grup: str
    birim: str = ""
    ondalik: int = 2
    tip: str = "fiyat"        # fiyat | getiri (getiri → değişim baz puanla)
    not_: str = ""


VARLIKLAR: list[Varlik] = [
    # ── Türkiye
    Varlik("XU100.IS", "BIST 100", "tr_hisse", "puan", 0),
    Varlik("XU030.IS", "BIST 30", "tr_hisse", "puan", 0),
    Varlik("XBANK.IS", "BIST Bankacılık", "tr_hisse", "puan", 0),
    Varlik("XUSIN.IS", "BIST Sınai", "tr_hisse", "puan", 0),
    Varlik("USDTRY=X", "USD/TRY", "tr_fx", "", 4),
    Varlik("EURTRY=X", "EUR/TRY", "tr_fx", "", 4),
    Varlik("GBPTRY=X", "GBP/TRY", "tr_fx", "", 4),
    Varlik("TUR", "iShares Türkiye ETF (USD)", "tr_hisse", "USD", 2,
           not_="Yabancı yatırımcının dolar bazlı getirisi"),

    # ── ABD hisse
    Varlik("^GSPC", "S&P 500", "abd_hisse", "puan", 2),
    Varlik("^NDX", "Nasdaq 100", "abd_hisse", "puan", 2),
    Varlik("^DJI", "Dow Jones", "abd_hisse", "puan", 2),
    Varlik("^RUT", "Russell 2000", "abd_hisse", "puan", 2),
    Varlik("^VIX", "VIX", "abd_hisse", "", 2, not_="S&P 500 örtük oynaklığı"),

    # ── Avrupa / Asya hisse
    Varlik("^STOXX", "STOXX Europe 600", "ab_hisse", "puan", 2),
    Varlik("^GDAXI", "DAX", "ab_hisse", "puan", 2),
    Varlik("^FCHI", "CAC 40", "ab_hisse", "puan", 2),
    Varlik("^FTSE", "FTSE 100", "ab_hisse", "puan", 2),
    Varlik("FTSEMIB.MI", "FTSE MIB", "ab_hisse", "puan", 2),
    Varlik("^N225", "Nikkei 225", "asya_hisse", "puan", 2),
    Varlik("^HSI", "Hang Seng", "asya_hisse", "puan", 2),
    Varlik("000001.SS", "Şanghay Bileşik", "asya_hisse", "puan", 2),

    # ── Faizler (getiri)
    Varlik("^IRX", "ABD 3 aylık bono", "faiz", "%", 3, "getiri"),
    Varlik("2YY=F", "ABD 2 yıllık", "faiz", "%", 3, "getiri"),
    Varlik("^FVX", "ABD 5 yıllık", "faiz", "%", 3, "getiri"),
    Varlik("^TNX", "ABD 10 yıllık", "faiz", "%", 3, "getiri"),
    Varlik("^TYX", "ABD 30 yıllık", "faiz", "%", 3, "getiri"),
    Varlik("^MOVE", "MOVE (tahvil oynaklığı)", "faiz", "", 2),

    # ── G10 FX
    Varlik("DX-Y.NYB", "Dolar endeksi (DXY)", "g10_fx", "", 3),
    Varlik("EURUSD=X", "EUR/USD", "g10_fx", "", 4),
    Varlik("USDJPY=X", "USD/JPY", "g10_fx", "", 3),
    Varlik("GBPUSD=X", "GBP/USD", "g10_fx", "", 4),
    Varlik("USDCHF=X", "USD/CHF", "g10_fx", "", 4),
    Varlik("AUDUSD=X", "AUD/USD", "g10_fx", "", 4),
    Varlik("NZDUSD=X", "NZD/USD", "g10_fx", "", 4),
    Varlik("USDCAD=X", "USD/CAD", "g10_fx", "", 4),
    Varlik("USDSEK=X", "USD/SEK", "g10_fx", "", 4),
    Varlik("USDNOK=X", "USD/NOK", "g10_fx", "", 4),

    # ── Metal
    Varlik("GC=F", "Altın (XAU, ons)", "metal", "USD", 2),
    Varlik("SI=F", "Gümüş (XAG, ons)", "metal", "USD", 3),
    Varlik("PL=F", "Platin", "metal", "USD", 2),
    Varlik("HG=F", "Bakır", "metal", "USD/lb", 4),

    # ── Enerji
    Varlik("BZ=F", "Brent", "enerji", "USD/varil", 2),
    Varlik("CL=F", "WTI", "enerji", "USD/varil", 2),
    Varlik("RB=F", "RBOB benzin", "enerji", "USD/galon", 4),
    Varlik("HO=F", "Kalorifer yakıtı", "enerji", "USD/galon", 4),
    Varlik("NG=F", "Doğal gaz (Henry Hub)", "enerji", "USD/mmBtu", 3),

    # ── Kredi ve gelişmekte olan piyasalar
    Varlik("HYG", "ABD yüksek getirili tahvil (HYG)", "kredi", "USD", 2),
    Varlik("LQD", "ABD yatırım yapılabilir tahvil (LQD)", "kredi", "USD", 2),
    Varlik("EMB", "GOÜ dolar tahvili (EMB)", "kredi", "USD", 2),
    Varlik("EEM", "GOÜ hisse (EEM)", "kredi", "USD", 2),

    # ── Kripto
    Varlik("BTC-USD", "Bitcoin", "kripto", "USD", 0),
]

GRUP_BASLIK = [
    ("tr_fx", "Türkiye — kur"),
    ("tr_hisse", "Türkiye — hisse"),
    ("faiz", "ABD faizleri ve tahvil oynaklığı"),
    ("g10_fx", "G10 döviz"),
    ("abd_hisse", "ABD hisse"),
    ("ab_hisse", "Avrupa hisse"),
    ("asya_hisse", "Asya hisse"),
    ("metal", "Değerli ve sanayi metalleri"),
    ("enerji", "Enerji"),
    ("kredi", "Kredi ve gelişmekte olan piyasalar"),
    ("kripto", "Kripto"),
]

# Kaynağı olmayan ama trader'ın bilmesi gereken büyüklükler — bülten bunları
# "kaynak yok" diye AÇIKÇA işaretler; yorum katmanı tarayıcıyla bakıp ekleyebilir.
KAYNAK_YOK = [
    "Almanya 10 yıllık (Bund) getirisi",
    "İngiltere 10 yıllık (Gilt) ve Japonya 10 yıllık (JGB) getirisi",
    "Türkiye 5 yıllık CDS primi",
    "TRY çapraz kur swap bazı (cross-currency basis)",
]


def _ham_veri(tazele: bool = False) -> dict:
    """Tüm enstrümanların günlük kapanış serisi. Önbellek TTL'li."""
    if HAM.exists() and not tazele:
        try:
            d = json.loads(HAM.read_text(encoding="utf-8"))
            t = datetime.fromisoformat(d["zaman"])
            if datetime.now() - t < timedelta(hours=TTL_SAAT):
                return d
        except Exception:
            pass
    import pandas as pd
    import yfinance as yf
    kodlar = [v.kod for v in VARLIKLAR]
    ham = yf.download(kodlar, period="1y", interval="1d", progress=False,
                      auto_adjust=False, group_by="ticker", threads=True)
    seri = {}
    for k in kodlar:
        try:
            s = ham[k]["Close"].dropna() if isinstance(ham.columns, pd.MultiIndex) else ham["Close"].dropna()
            if len(s) < 5:
                continue
            seri[k] = {"tarih": [str(x.date()) for x in s.index], "kapanis": [float(x) for x in s.values]}
        except Exception:
            continue
    d = {"zaman": datetime.now().isoformat(timespec="seconds"), "seri": seri}
    HAM.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    return d


def _degisim(kapanis: list[float], tarih: list[str], geri: int) -> float | None:
    if len(kapanis) <= geri:
        return None
    return kapanis[-1] - kapanis[-1 - geri]


def _ybb_bas(tarih: list[str], kapanis: list[float]) -> float | None:
    yil = tarih[-1][:4]
    for i, t in enumerate(tarih):
        if t[:4] == yil:
            return kapanis[i - 1] if i > 0 else kapanis[i]
    return None


# Bir hareketin BÜYÜKLÜĞÜ ile OLAĞANDIŞILIĞI ayrı şeylerdir. Benzinde %11 ile
# tahvil oynaklığında %2,8 aynı ölçekte değildir: ilki normal bir gün, ikincisi
# üç standart sapma olabilir. Ham yüzdeye göre sıralanan bir "en çok hareket"
# listesi bu yüzden yazan tarafı sistematik olarak yanlış yere bakmaya iter —
# hep aynı oynak enstrümanlar başa çıkar, gerçekten anormal olan görünmez.
#
# Ölçü: son OYNAKLIK_GUN günlük değişimin standart sapması, değişimle AYNI
# birimde (fiyatta yüzde, getiride baz puan). Günlük hareket buna bölününce
# bütün enstrümanlar tek bir ölçekte kıyaslanabilir hâle gelir.
OYNAKLIK_GUN = 20
OYNAKLIK_ASGARI = 10        # bu kadar gözlem yoksa σ güvenilir değil


def _gunluk_degisimler(kapanis: list[float], getiri: bool, n: int) -> list[float]:
    """Son n günlük değişim — d1 ile aynı birimde (fiyat: %, getiri: bp)."""
    out = []
    for i in range(max(1, len(kapanis) - n), len(kapanis)):
        onceki = kapanis[i - 1]
        if onceki == 0:
            continue
        out.append((kapanis[i] - onceki) * 100.0 if getiri
                   else (kapanis[i] / onceki - 1) * 100.0)
    return out


def _oynaklik(kapanis: list[float], getiri: bool) -> float | None:
    d = _gunluk_degisimler(kapanis, getiri, OYNAKLIK_GUN)
    if len(d) < OYNAKLIK_ASGARI:
        return None
    ort = sum(d) / len(d)
    var = sum((x - ort) ** 2 for x in d) / (len(d) - 1)
    return var ** 0.5 or None


def satir(v: Varlik, seri: dict) -> dict | None:
    s = seri.get(v.kod)
    if not s:
        return None
    k, t = s["kapanis"], s["tarih"]
    son = k[-1]
    getiri = v.tip == "getiri"
    carpan = 100.0 if getiri else 1.0          # yüzde puanı → baz puan

    def d(geri):
        f = _degisim(k, t, geri)
        if f is None:
            return None
        return round(f * carpan, 1) if getiri else round(f / k[-1 - geri] * 100, 2)

    ybb_taban = _ybb_bas(t, k)
    ybb = None
    if ybb_taban:
        ybb = round((son - ybb_taban) * carpan, 1) if getiri else round((son / ybb_taban - 1) * 100, 2)

    pencere = k[-252:] if len(k) >= 252 else k
    sigma = _oynaklik(k, getiri)
    return {
        "kod": v.kod, "ad": v.ad, "grup": v.grup, "birim": v.birim,
        "ondalik": v.ondalik, "tip": v.tip, "not": v.not_,
        "son": round(son, v.ondalik), "tarih": t[-1],
        "d1": d(1), "h1": d(5), "a1": d(21), "ybb": ybb,
        "degisim_birim": "bp" if getiri else "%",
        "yil_yuksek": round(max(pencere), v.ondalik),
        "yil_dusuk": round(min(pencere), v.ondalik),
        "yil_konum": round((son - min(pencere)) / (max(pencere) - min(pencere)) * 100, 0)
        if max(pencere) > min(pencere) else None,
        # Günlük hareketin kaç standart sapma olduğu — enstrümanlar arası tek ölçek.
        "sigma_gun": None if sigma is None else round(sigma, 2 if getiri else 2),
        "d1_sigma": (None if sigma is None or d(1) is None
                     else round(d(1) / sigma, 1)),
    }


def turetilmis(seri: dict) -> list[dict]:
    """Eğri eğimleri, crack spread'ler, oranlar — trader'ın baktığı türevler."""
    def son(kod, geri=0):
        s = seri.get(kod)
        if not s or len(s["kapanis"]) <= geri:
            return None
        return s["kapanis"][-1 - geri]

    out = []

    def ekle(ad, deger, birim, d1, aciklama, ondalik=2):
        if deger is None:
            return
        out.append({"ad": ad, "deger": round(deger, ondalik), "birim": birim,
                    "d1": None if d1 is None else round(d1, 1), "aciklama": aciklama})

    # Verim eğrisi eğimleri (baz puan)
    for ad, uzun, kisa, acik in (
        ("ABD 2s10s", "^TNX", "2YY=F", "10 yıllık eksi 2 yıllık: eğrinin ana eğimi; "
                                        "dikleşme büyüme/enflasyon, yataylaşma sıkılaşma fiyatlar."),
        ("ABD 5s30s", "^TYX", "^FVX", "Uzun ucun eğimi: vade primi ve arz endişesinin ölçüsü."),
        ("ABD 3a-10y", "^TNX", "^IRX", "Para piyasası ile uzun uç arasındaki fark; "
                                        "ters eğim resesyon göstergesi sayılır."),
    ):
        u, ks = son(uzun), son(kisa)
        u1, k1 = son(uzun, 1), son(kisa, 1)
        if u is None or ks is None:
            continue
        e = (u - ks) * 100
        d1 = ((u - ks) - (u1 - k1)) * 100 if (u1 is not None and k1 is not None) else None
        ekle(ad, e, "bp", d1, acik, 0)

    # Crack spread'ler (rafineri marjı) — ABD kontratlarından, varil başına dolar.
    # 1 varil = 42 galon. 3:2:1 = 3 varil ham petrolden 2 varil benzin + 1 varil distilat.
    cl, rb, ho = son("CL=F"), son("RB=F"), son("HO=F")
    cl1, rb1, ho1 = son("CL=F", 1), son("RB=F", 1), son("HO=F", 1)
    if None not in (cl, rb, ho):
        c321 = (2 * rb * 42 + ho * 42 - 3 * cl) / 3
        d1 = None
        if None not in (cl1, rb1, ho1):
            d1 = c321 - (2 * rb1 * 42 + ho1 * 42 - 3 * cl1) / 3
        ekle("3:2:1 crack spread", c321, "USD/varil", d1,
             "Rafineri marjı: 3 varil ham petrolden 2 varil benzin + 1 varil distilat. "
             "Genişlemesi ürün talebinin ham petrolden güçlü olduğunu gösterir.")
        ekle("Benzin crack (RBOB−WTI)", rb * 42 - cl, "USD/varil",
             (rb * 42 - cl) - (rb1 * 42 - cl1) if None not in (rb1, cl1) else None,
             "Benzin rafineri marjı; sürüş sezonu ve ürün stoklarına duyarlı.")
        ekle("Distilat crack (HO−WTI)", ho * 42 - cl, "USD/varil",
             (ho * 42 - cl) - (ho1 * 42 - cl1) if None not in (ho1, cl1) else None,
             "Motorin/kalorifer marjı; sanayi ve nakliye talebinin göstergesi.")
    bz, bz1 = son("BZ=F"), son("BZ=F", 1)
    if None not in (bz, cl):
        ekle("Brent−WTI farkı", bz - cl, "USD/varil",
             (bz - cl) - (bz1 - cl1) if None not in (bz1, cl1) else None,
             "Atlantik havzası ile ABD iç piyasası arasındaki taşıma/arz farkı.")

    # Oranlar
    xau, xag = son("GC=F"), son("SI=F")
    xau1, xag1 = son("GC=F", 1), son("SI=F", 1)
    if None not in (xau, xag) and xag:
        ekle("Altın/gümüş oranı", xau / xag, "kat",
             (xau / xag - xau1 / xag1) if None not in (xau1, xag1) and xag1 else None,
             "Yükselmesi güvenli liman talebinin sanayi talebine baskın geldiğini gösterir.")

    # BIST'in dolar bazlı seviyesi — yabancı yatırımcının gördüğü getiri
    x, usd = son("XU100.IS"), son("USDTRY=X")
    x1, usd1 = son("XU100.IS", 1), son("USDTRY=X", 1)
    if None not in (x, usd) and usd:
        ekle("BIST 100 (dolar bazlı)", x / usd, "USD puan",
             ((x / usd) / (x1 / usd1) - 1) * 100 if None not in (x1, usd1) and usd1 else None,
             "TL endeksin kurdan arındırılmış hâli; yabancının gördüğü performans.", 1)
    return out


def en_cok_hareket(satirlar: list[dict], n: int = 6) -> dict:
    """Günün ve haftanın en büyük hareketleri — yorumun nereye bakacağını söyler.

    Üç ham sıralama (günlük %, haftalık %, haftalık bp) ile bir de OLAĞANDIŞILIK
    sıralaması döner. İkisi farklı soruları cevaplar: ham liste "en çok ne
    oynadı", σ listesi "ne olağandışı oynadı". Aynı gün ikisi bambaşka çıkabilir
    — 26.08.2026'da MOVE ve VIX ham listede ilk altıdaydı ama −0,6σ ve −0,4σ,
    yani sıradan bir gün; buna karşılık üç kredi endeksi +1,6σ ile ham listede
    hiç görünmüyordu. Yazan taraf yalnız hama bakarsa hep aynı oynak
    enstrümanları anlatır ve asıl haberi kaçırır.

    σ listesi getiri enstrümanlarını DIŞLAMAZ: z-skoru birimsizdir, baz puanla
    yüzde aynı ölçekte kıyaslanabilir. Ham listelerde bu mümkün olmadığı için
    faizler ayrı tutulmuştu.
    """
    def sirala(alan):
        aday = [s for s in satirlar if s.get(alan) is not None and s["tip"] != "getiri"]
        return sorted(aday, key=lambda s: abs(s[alan]), reverse=True)[:n]
    getiriler = [s for s in satirlar if s["tip"] == "getiri" and s.get("h1") is not None]
    sigmali = [s for s in satirlar if s.get("d1_sigma") is not None]
    return {
        "gunluk": [{"ad": s["ad"], "deger": s["d1"], "birim": "%"} for s in sirala("d1")],
        "haftalik": [{"ad": s["ad"], "deger": s["h1"], "birim": "%"} for s in sirala("h1")],
        "faiz_haftalik": [{"ad": s["ad"], "deger": s["h1"], "birim": "bp"}
                          for s in sorted(getiriler, key=lambda s: abs(s["h1"]), reverse=True)[:4]],
        "sigma": [{"ad": s["ad"], "deger": s["d1"], "birim": s["degisim_birim"],
                   "sigma": s["d1_sigma"], "oynaklik": s["sigma_gun"]}
                  for s in sorted(sigmali, key=lambda s: abs(s["d1_sigma"]),
                                  reverse=True)[:n]],
    }


def tr_faizleri() -> list[dict]:
    """TL faiz seti — bu deponun kendi hatlarından (piyasa verisinde yok)."""
    import gozlem
    out = []

    def al(hat, anahtar, ad, birim="%", ondalik=2, aciklama=""):
        """Bir büyüklüğü hattan al — KENDİ tarihi ve KENDİ geçerlilik bayrağıyla.

        Neden: hattın genel veri tarihi ile tek bir alanın tarihi ayrışabiliyor.
        Ağırlıklı ortalama fonlama maliyeti bunun canlı örneği: hat 21.08 tarihli
        koşsa da bu alanın son GEÇERLİ günü 07.08 olabiliyor ve hat bunu
        `<alan>_gecerli: false` ile ilan ediyor. Hattın tarihini bu alana yapıştırmak,
        iki hafta önceki bir sayıyı bugünkü gibi göstermek olurdu.
        """
        d = gozlem.anlik(hat) or {}
        v = d.get(anahtar)
        if v is None or isinstance(v, bool) or not isinstance(v, (int, float)):
            return
        tarih = d.get(f"{anahtar}_tarih") or d.get("_tarih", "")
        gecerli = d.get(f"{anahtar}_gecerli")
        if gecerli is False:
            aciklama = ((aciklama + " · ") if aciklama else "") + \
                "kaynak bu değeri GÜNCEL saymıyor; gösterilen son geçerli gün"
        out.append({"ad": ad, "deger": round(float(v), ondalik), "birim": birim,
                    "tarih": tarih, "aciklama": aciklama,
                    "gecerli": False if gecerli is False else True})

    al("fonlama-likidite", "politika", "Politika faizi (1 hafta repo)")
    al("fonlama-likidite", "koridor_alt", "Koridor alt bandı")
    al("fonlama-likidite", "koridor_ust", "Koridor üst bandı (gecelik borç verme)")
    al("fonlama-likidite", "aofm", "Ağırlıklı ortalama fonlama maliyeti")
    al("fonlama-likidite", "tlref", "TLREF (gecelik gerçekleşen)")
    al("fonlama-likidite", "bist_on", "BIST gecelik repo")
    al("fonlama-likidite", "spread_tlref_politika", "TLREF − politika farkı", "puan")
    al("hazine-ihrac", "maliyet_son", "Hazine son ihale ort. bileşik maliyeti", "%", 2,
       "Hazinenin fiilî borçlanma maliyeti")
    al("hazine-ihrac", "b2c_son", "Son ihale teklif/karşılama", "kat", 2)
    al("kredi-parasal", "g_ar_13y", "Kredi büyümesi (13h yıllıklandırılmış, kur arınd.)")

    # ── DİBS verim eğrisi (kendi hattımız): nominal spot eğri, reel eğri, başabaş
    for anahtar, ad, birim, acik in (
        ("gosterge_ytm", "Gösterge tahvil (bileşik getiri)", "%",
         "En likit DİBS'in vadeye kadar getirisi"),
        ("spot_3a", "DİBS spot 3 ay", "%", ""),
        ("spot_1y", "DİBS spot 1 yıl", "%", ""),
        ("spot_2y", "DİBS spot 2 yıl", "%", ""),
        ("spot_5y", "DİBS spot 5 yıl", "%", ""),
        ("spot_9y", "DİBS spot 9 yıl", "%", ""),
        ("egim_2y9y", "DİBS 2y−9y eğimi", "puan",
         "Negatif = ters eğri: kısa uç uzun uçtan yüksek"),
        ("forward_2y1y", "2 yıl sonrası 1 yıllık forward faiz", "%",
         "Piyasanın iki yıl sonrası için fiyatladığı kısa faiz"),
        ("carry_2y_tlref", "2 yıllık taşıma (TLREF'e karşı)", "puan",
         "Negatif = tahvili gecelik fonlamayla taşımak maliyetli"),
        ("reel_egri_2y", "Reel getiri 2 yıl", "%", "Başabaş enflasyondan arındırılmış"),
        ("reel_egri_5y", "Reel getiri 5 yıl", "%", ""),
        ("basabas_2y", "Başabaş enflasyon 2 yıl", "%",
         "Nominal ile enflasyona endeksli tahvilin ima ettiği enflasyon"),
        ("basabas_5y", "Başabaş enflasyon 5 yıl", "%", ""),
        ("pka_faiz_12a", "Anket: 12 ay sonrası politika faizi", "%",
         "TCMB Piyasa Katılımcıları Anketi"),
    ):
        al("dibs-verim-egrisi", anahtar, ad, birim, 2, acik)
    return out


def topla(tazele: bool = False) -> dict:
    ham = _ham_veri(tazele)
    seri = ham["seri"]
    satirlar = [x for x in (satir(v, seri) for v in VARLIKLAR) if x]
    gruplar = []
    for gid, baslik in GRUP_BASLIK:
        icerik = [s for s in satirlar if s["grup"] == gid]
        if icerik:
            gruplar.append({"id": gid, "baslik": baslik, "satirlar": icerik})
    eksik = [v.ad for v in VARLIKLAR if v.kod not in seri]
    return {
        "zaman": ham["zaman"],
        "gruplar": gruplar,
        "turetilmis": turetilmis(seri),
        "tr_faizleri": tr_faizleri(),
        "en_cok_hareket": en_cok_hareket(satirlar),
        "eksik": eksik,
        "kaynak_yok": KAYNAK_YOK,
    }


if __name__ == "__main__":
    import sys
    p = topla("--tazele" in sys.argv)
    print(f"veri zamanı: {p['zaman']}  ·  {sum(len(g['satirlar']) for g in p['gruplar'])} enstrüman")
    for g in p["gruplar"]:
        print(f"\n### {g['baslik']}")
        for s in g["satirlar"]:
            b = s["degisim_birim"]
            print(f"  {s['ad']:34s} {s['son']:>12,.{s['ondalik']}f} {s['birim']:<10s}"
                  f" 1g {str(s['d1']):>7s}{b}  1h {str(s['h1']):>7s}{b}  YBB {str(s['ybb']):>8s}{b}")
    print("\n### Türev büyüklükler")
    for t in p["turetilmis"]:
        print(f"  {t['ad']:30s} {t['deger']:>10.2f} {t['birim']:<12s} 1g {str(t['d1']):>8s}")
    print("\n### TL faizleri")
    for t in p["tr_faizleri"]:
        print(f"  {t['ad']:46s} {t['deger']:>8.2f} {t['birim']:<6s} ({t['tarih']})")
    if p["eksik"]:
        print("\nveri gelmeyen:", ", ".join(p["eksik"]))
