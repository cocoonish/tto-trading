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
from datetime import datetime, timedelta, timezone
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
# Piyasa fotoğrafının BİLİNEN boşlukları. Düz bir isim listesiydi; okur neyin
# eksik olduğunu görüyor ama neden eksik olduğunu ve yerine neye bakması
# gerektiğini bilmiyordu. Kapsamı olduğundan geniş göstermemek profesyonelliğin
# şartı: bir Türkiye makro bülteninde CDS ve çapraz kur bazının yokluğu küçük
# bir ayrıntı değil, risk priminin ve offshore TL fonlamasının hiç ölçülmemesi
# demektir.
#
# `aday` alanı uygulanmayı bekleyen kaynağın TAM ucudur; `engel` neden henüz
# bağlanmadığını söyler. Bir kaynak bağlandığında kayıt buradan silinir.
KAYNAK_YOK = [
    {
        "ad": "Türkiye 5 yıllık CDS primi",
        "neden": "Türkiye risk priminin tek fiyatı. Kur, tahvil ve hisse "
                 "hareketlerinin ortak sürücüsü; yokluğunda bülten TL varlıklardaki "
                 "hareketin ne kadarının Türkiye'ye özgü olduğunu söyleyemiyor.",
        "aday": "Ücretsiz ve sözleşmesi net bir uç bulunamadı. Vekil seri olarak "
                "Türkiye USD eurobond getirisinin aynı vadeli ABD hazine getirisinden "
                "farkı (spread) hesaplanabilir; bunun için eurobond fiyat serisi gerekir.",
        "engel": "CDS kotasyonları ticari veri (ICE, S&P). Vekil eurobond serisi de "
                 "ücretsiz kaynaklarda güvenilir bulunamadı.",
    },
    {
        "ad": "TRY çapraz kur swap bazı (cross-currency basis)",
        "neden": "Offshore TL fonlamasının fiyatı. Onshore faizden ayrışması, "
                 "yurt dışındaki TL likiditesinin sıkıştığının en erken işareti — "
                 "TL taşıma pozisyonlarının çözülmesi buradan başlar.",
        "aday": "Vekil: USD/TRY forward puanlarının ima ettiği TL faizi ile onshore "
                "TLREF farkı. Forward puanları için ücretsiz bir günlük seri gerekir.",
        "engel": "Baz kotasyonu tezgâh üstü ve ticari. Forward puanları da ücretsiz "
                 "kaynaklarda düzenli bulunmuyor.",
    },
    {
        "ad": "Almanya 10 yıllık (Bund) getirisi",
        "neden": "Euro faizlerinin çıpası. ABD uzun ucu izleniyor ama Türkiye'nin "
                 "dış borçlanmasının ve ticaretinin ağırlığı euro tarafında.",
        "aday": "ECB Data Portal, euro alanı AAA devlet tahvili getiri eğrisi "
                "(data-api.ecb.europa.eu, YC serisi) — ücretsiz, anahtarsız, belgeli.",
        "engel": "Henüz bağlanmadı; hattın kendi çekme ve önbellek yolu yazılacak "
                 "(piyasa fotoğrafı yfinance üzerinden çalışıyor, bu ayrı bir uç).",
    },
    {
        "ad": "İngiltere 10 yıllık (Gilt) ve Japonya 10 yıllık (JGB) getirisi",
        "neden": "Küresel uzun uç anlatısının diğer iki ayağı; özellikle JGB, "
                 "'debasement trade' temasının doğrudan sınandığı yer.",
        "aday": "JGB için Japonya Maliye Bakanlığı günlük getiri CSV'si "
                "(mof.go.jp, jgbcm.csv) — ücretsiz ve düzenli. Gilt için İngiltere "
                "Merkez Bankası istatistik veri tabanı.",
        "engel": "Bund ile aynı: ayrı çekme yolu yazılmayı bekliyor.",
    },
]


def _onbellek_birlestir(yeni: dict, eski: dict) -> dict | None:
    """Çekilen seriyi önbellektekiyle birleştirir; yazılmamalıysa None döner.

    AĞA ÇIKMAZ — bilerek. Bu karar bir zamanlar `_ham_veri`nin içinde, yani
    yfinance çağrısının hemen ardında duruyordu ve hiçbir duman sınaması onu
    koşturamıyordu; kusuru da tam orada kaldı (bkz. `_ham_veri`). Karar ayrı bir
    fonksiyona çıktığı için artık sahte girdiyle sınanabiliyor.

    Sözleşme üç hâlli:
      · çekim BOŞ            → None (önbellek yazılmaz, damga ilerlemez)
      · sembol çekimde YOK   → önbellekteki seri devredilir, adı `getirilmeyen`de
      · sembol çekimde VAR   → çekilen seri eskisinin yerine geçer
    """
    if not yeni:
        return None
    getirilmeyen = sorted(set(eski) - set(yeni))
    return {
        "zaman": datetime.now().isoformat(timespec="seconds"),
        "seri": {**{k: v for k, v in eski.items() if k not in yeni}, **yeni},
        "getirilmeyen": getirilmeyen,
    }


# ─────────────────────────── kaynağın BOŞ verdiği seans
#
# ÖLÇÜLDÜ (23.09.2026, bulut keşfi bulten/kesif_piyasa_bosluk*.py). 04:20 UTC
# koşusunda 51 satırın 23'ü 22.09 Salı kapanışını taşımıyordu: bütün nakit hisse
# endeksleri, ETF'ler, DXY, MOVE ve Bitcoin. Kusur bizim kodumuzda DEĞİLDİ —
# Yahoo'nun günlük geçmişi 22.09 için bir SATIR açıyor ama kapanışını BOŞ (null)
# veriyordu ve `dropna()` o satırı atıyordu. Yahoo aynı sabah 04:20'de dolu
# verdiği ABD getiri ve VIX barlarını 06:47'de boşalttı; yani kaynak yayımlanmış
# bir barı da geri çekebiliyor. Bitcoin'de aynı boşluk neredeyse HER sabah var.
# Görüntü sağlığın görüntüsüyle aynıydı: koşu yeşil, satırlar kendi tarihini
# doğru taşıyor, başlık "22.09.2026 Salı kapanışı" diyor ve denetim — yalnız EN
# TAZE tarihe baktığı için — hiçbir şey görmüyordu.
#
# Onarımın yolu da ölçüldü. Piyasa KAPALIYKEN chart ucunun meta alanı
# `regularMarketPrice`, `regularMarketTime` gününün kapanışıdır: günlük satırı
# dolu olan altı sembolde fark 0,00 bp, ve XU100'ün boş gelen 22.09'u için
# 13198,84 — o günün haberlere geçen kapanışının kendisi. Reddedilen iki yol:
# gün içi SON BAR (BIST'te medyan 9, azami 63 bp; kapanış seansı gün içi
# barlarda yok) ve `chartPreviousClose` (etkilenen sembollerde son DOLU günü,
# yani 21.09'u veriyor; dövizde ±36 bp, vadelide yüzlerce bp sapıyor). Yani
# piyasası ŞU AN AÇIK olan bir sembolün (Bitcoin 7/24, sabah Hang Seng ve
# Şanghay, DXY) dünkü boş kapanışı bu kaynaktan KURULAMAZ; o satır onarılmaz,
# kendi tarihiyle kalır ve ADIYLA bildirilir.
#
# Vadeli sözleşmeler onarılmaz: meta fiyatı çoğu zaman en aktif kontratı verir,
# geçmiş ise ön ayı izler (devir düzeltmesinin notu) — boş günü meta fiyatıyla
# doldurmak sahte bir devir yazmak olurdu. Boşlukları yine bildirilir.
CHART_UCU = "https://query2.finance.yahoo.com/v8/finance/chart/{}"


def _vadeli_mi(kod: str) -> bool:
    return kod in VADELI_KOK or kod.endswith("=F")


def _meta_ozet(sonuc: dict, simdi: datetime) -> dict | None:
    """Chart ucunun tek sembollük cevabından onarımın ihtiyaç duyduğu alanlar.

    AĞA ÇIKMAZ: cevabı ağdan alan `_meta_topla`dır; bu fonksiyon duman
    sınamasında gerçek cevabın biçimiyle kurulan sahte girdiyle koşar. Bütün
    tarihler BORSANIN yerel günüdür — yfinance'in günlük serisi de öyle
    etiketlenir, kıyas aynı takvimde yapılmalı.
    """
    if not sonuc:
        return None
    m = sonuc.get("meta") or {}
    off = timedelta(seconds=int(m.get("gmtoffset") or 0))
    yerel_bugun = (simdi + off).date().isoformat()
    ts = sonuc.get("timestamp") or []
    q = (((sonuc.get("indicators") or {}).get("quote")) or [{}])[0]
    kap = q.get("close") or [None] * len(ts)
    bos = sorted({(datetime.fromtimestamp(t, timezone.utc) + off).date().isoformat()
                  for t, c in zip(ts, kap) if c is None})
    rmt, fiyat = m.get("regularMarketTime"), m.get("regularMarketPrice")
    son_gun = ((datetime.fromtimestamp(rmt, timezone.utc) + off).date().isoformat()
               if rmt else None)
    reg = (m.get("currentTradingPeriod") or {}).get("regular") or {}
    acik = bool(reg.get("start") and reg.get("end")
                and reg["start"] <= simdi.timestamp() < reg["end"])
    return {"yerel_bugun": yerel_bugun, "bos": bos, "son_islem_gun": son_gun,
            "fiyat": float(fiyat) if isinstance(fiyat, (int, float)) else None,
            "acik": acik}


def _meta_topla(kodlar: list[str], simdi: datetime) -> tuple[dict, list[str]]:
    """Her sembol için chart ucundan son beş günlük geçmiş ve meta. Ağa çıkar.

    Düşen sembol onarımı kaybeder ama ölçümü düşürmez; adı ikinci listede döner
    (bir sembolün sınanamadığı, sınanıp temiz çıktığıyla aynı görünmesin).
    """
    try:
        from yfinance.data import YfData
        veri = YfData()
    except Exception:
        return {}, list(kodlar)
    out, olmadi = {}, []
    ust_uste = 0
    for k in kodlar:
        # DEVRE KESİCİ. Ağ kapalıyken her sembol kendi zaman aşımını beklerse
        # elli bir sembol on yedi dakika yakar ve bülten iş akışının bütçesini
        # bitirir. Üç ardışık düşüş kalan sembolleri denemeden "sınanamadı"
        # sayar; onarım bir iyileştirmedir, ölçümün önüne geçemez.
        if ust_uste >= 3:
            olmadi.append(k)
            continue
        try:
            r = veri.get(CHART_UCU.format(k), timeout=20,
                         params={"range": "5d", "interval": "1d", "includePrePost": "false"})
            sonuc = (((r.json() or {}).get("chart") or {}).get("result") or [None])[0] \
                if r.status_code == 200 else None
            oz = _meta_ozet(sonuc, simdi)
            if oz is None:
                olmadi.append(k)
                ust_uste += 1
            else:
                out[k] = oz
                ust_uste = 0
        except Exception:
            olmadi.append(k)
            ust_uste += 1
    return out, olmadi


def _bos_seans_onar(seri: dict, metalar: dict, eski: dict, simdi: datetime) -> dict:
    """Kaynağın boş verdiği tamamlanmış seansları onar ya da ADIYLA işaretle.

    AĞA ÇIKMAZ. Sırayla üç adım, her biri yalnız VADELİ OLMAYAN seriye:
      1. Önbellekten devir — kaynak bugün boş verdiği bir günü daha önce dolu
         vermişse (bir sonraki sabah geri çekilen bar), eski değer yerinde
         kalır. Aksi hâlde "1 gün" değişimi sessizce iki seansı kapsardı.
      2. Son işlem fiyatı — boş gün kaynağın son işlem günüyse ve o seans
         BİTMİŞSE (borsa günü geride kaldı, ya da piyasa şu an kapalı ve UTC
         kapanış saati geçti) kapanış meta fiyatıdır.
      3. Kalan boş günler serinin son gününden sonraysa `eksik_seans` olarak
         seride durur; satır onu okura adıyla söyler, denetim uyarı verir.
    Kanıt kaynağın KENDİSİDİR (boş satır ya da son işlem günü): tatil günü
    kaynakta hiç satır açmaz ve burada hiçbir şey üretmez — Nikkei'nin 21–22.09
    tatili ölçümde tam böyle göründü.
    """
    gruplar = {v.kod: v.grup for v in VARLIKLAR}
    bugun_utc = simdi.date().isoformat()
    for k, m in (metalar or {}).items():
        s = seri.get(k)
        if not s or not s.get("tarih") or not m:
            continue
        for alan in ("onarim", "eksik_seans", "devredilen"):
            s.pop(alan, None)
        bos = [g for g in m.get("bos") or [] if g < m["yerel_bugun"]]
        vadeli = _vadeli_mi(k)
        if not vadeli:
            # (1) önbellekten devir
            e = (eski or {}).get(k) or {}
            eski_deger = dict(zip(e.get("tarih") or [], e.get("kapanis") or []))
            for g in bos:
                if g in s["tarih"] or g not in eski_deger:
                    continue
                i = sum(1 for t in s["tarih"] if t < g)
                s["tarih"].insert(i, g)
                s["kapanis"].insert(i, float(eski_deger[g]))
                s.setdefault("devredilen", []).append(g)
            # (2) son işlem fiyatı
            d, fiyat = m.get("son_islem_gun"), m.get("fiyat")
            if d and fiyat and fiyat > 0 and d > s["tarih"][-1] and d <= bugun_utc:
                bitti = d < m["yerel_bugun"] or not m.get("acik")
                if d == bugun_utc and simdi.hour < KAPANIS_UTC.get(gruplar.get(k, ""),
                                                                    VARSAYILAN_KAPANIS):
                    bitti = False
                if bitti:
                    s["tarih"].append(d)
                    s["kapanis"].append(float(fiyat))
                    s["onarim"] = {"gun": d, "kaynak": "son_islem"}
        # (3) kalan boş günler
        kalan = [g for g in bos if g > s["tarih"][-1]]
        if kalan:
            s["eksik_seans"] = kalan
    return seri


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
    # SIRA BAĞLAYICI — ve eskiden TERSİYDİ.
    #
    # Önce devir düzeltmesi koşuyordu, sonra yerleşmemiş bar düşürülüyordu.
    # Gerekçe "eşleştirme tarihsel barlara dayanır" idi; ama düzeltme, elinde
    # KAPANMAMIŞ günün barı varken çalışıyordu ve o barın kotasyonu tarihsel
    # barlarla aynı kontratı izlemiyor (Yahoo canlıda çoğu zaman en aktif
    # kontratı verir, tarihte ön ayı). Sonuç: düzeltme bugüne SAHTE bir devir
    # yazıyor ve o devirden önceki BÜTÜN günleri yanlış bir oranla ölçekliyordu.
    #
    # 27.08.2026'nın iki koşusu bunu ölçtü. 04:21 koşusunda Brent, benzin ve
    # kalorifer için devir günü '2026-08-27' olarak kaydedildi — serinin son
    # KAPALI günü 26.08 olmasına rağmen. Brent'in 26.08 kapanışı bu sahte
    # oranla 87,84'ten 86,94'e çekildi; benzin 3,3201'den 2,9606'ya indi ve
    # rafineri marjları (3:2:1 68,77 → 58,7) onunla birlikte kaydı. Hiçbiri
    # piyasa hareketi değildi. Günlük yüzde değişim, oran her iki güne de
    # uygulandığı için sağ kalıyordu; bozulan SEVİYELER ve seviyeden türeyen
    # marjlardı — ve bülten onları dolar fiyatı diye yayımlıyordu.
    #
    # Doğru sıra: önce kapanmamış barı düş, SONRA devri hesapla. Böylece
    # düzeltme yalnız kapanmış barlarla eşleştirme yapar ve bugüne devir
    # yazamaz.
    seri = _yerlesmemis_dus(seri)
    eski = {}
    try:
        eski = (json.loads(HAM.read_text(encoding="utf-8")) or {}).get("seri") or {}
    except Exception:
        pass
    # BOŞ SEANS ONARIMI — yerleşmemiş bar düştükten SONRA (onarım kapanmamış bir
    # günü asla kurmaz, ama elindeki seri de kapanmamış bar taşımamalı) ve devir
    # düzeltmesinden ÖNCE (vadeliler zaten onarılmaz; sıra yalnız okunurluk için).
    simdi = datetime.now(timezone.utc)
    # Toplu çekim BOŞ döndüyse ağ kapalıdır; meta istekleri de düşer.
    metalar, meta_yok = _meta_topla(kodlar, simdi) if seri else ({}, list(kodlar))
    seri = _bos_seans_onar(seri, metalar, eski, simdi)
    try:
        seri = _roll_duzelt(seri)
    except Exception:
        pass                       # düzeltme yapılamazsa ham seriyle devam
    # ÖNBELLEK BAŞARISIZ ÇEKİMLE EZİLMEZ. 31.08.2026'da ağı kapalı bir ortamda
    # tek bir çağrı elli serilik önbelleği SIFIR seriyle üzerine yazdı; dosya
    # izlenen bir dosya olduğu için depodaki iyi sürüm de tehlikeye girdi.
    # Yahoo bütün istekleri reddettiğinde çekim "başarılı ama boş" görünür —
    # "veri geldi" ile "veri TAM geldi" ayrımının bir örneği daha.
    #
    # KORUMANIN İLK YAZIMI ÖLÇÜLEN ARIZADAN GENİŞTİ ve o genişlik 09.09.2026'da
    # bültenin TAMAMINI dondurdu. Kural "yeni anlık görüntü eldekinden AZ seri
    # taşıyorsa yazılmaz, eski önbellek olduğu gibi döner" biçimindeydi; ölçülen
    # arıza ise TOPLU kayıptı (51 → 0). Aradaki fark bir sembolün KALICI olarak
    # kaybolduğu gün ortaya çıktı: Yahoo `2YY=F` (ABD 2 yıllık getiri vadelisi)
    # serisini emekliye ayırdı, çekim 51 yerine 50 seri döndürdü ve koruma tek
    # eksik yüzünden SAĞLIKLI 50 seriyi de reddetti. Sonuç, arızanın en sinsi
    # biçimiydi: koşu yeşil bitti, bülten dosyası yazıldı, ve elli bir piyasa
    # satırının ELLİ BİRİ bir gün önceki anlık görüntünün birebir kopyasıydı —
    # dünkü seansın günlük değişimi bugünün bülteninde yeniden yayımlanacaktı.
    # Üstelik açık YARIN da düzelmeyeceği için donma kalıcıydı: eksik sembol
    # geri gelmedikçe koruma her sabah aynı reddi verir ve fotoğraf her gün bir
    # seans daha bayatlar. Bir sigortanın hangi arızaya karşı konduğu
    # yazılmazsa, kapsamı sessizce o arızadan büyür.
    #
    # İki nesne birbirinden ayrıldı ve ayrım kasıtlı: ÖNBELLEK bir veri deposu,
    # ANLIK GÖRÜNTÜ bir ölçümdür. Önbellek hiçbir seriyi kaybetmez (çekimden
    # dönmeyen sembol eldeki seriyle DEVREDİLİR, yani kısmi bir çekim tarihçeyi
    # budayamaz); ölçüm ise her satırın KENDİ bar tarihini taşımaya devam eder,
    # yani devredilen bir sembol taze görünmez — sayfada 04.09 yazar, öbürleri
    # 08.09. Yalnız çekimin HİÇBİR şey döndürmediği hâl — ölçülmüş olan arıza —
    # yazmayı büsbütün durdurur; o durumda damga da ilerlemez, çünkü ilerlerse
    # bayat bir fotoğraf kendini taze ilan eder. (`eski` yukarıda, boş seans
    # onarımından önce okundu — onarımın önbellekten devir adımı da onu okur.)
    d = _onbellek_birlestir(seri, eski)
    if d is None:
        print(f"  ! piyasa çekimi BOŞ döndü — önbellek yazılmadı, "
              f"eldeki {len(eski)} seri korunuyor.")
        return json.loads(HAM.read_text(encoding="utf-8"))
    # Çekimden dönmeyen semboller ADIYLA yazılır. Sessizce devretmek, ölçülmemiş
    # bir günü ölçülmüş gibi göstermenin en sessiz biçimi olurdu.
    if d["getirilmeyen"]:
        _ad = {v.kod: v.ad for v in VARLIKLAR}
        _kunye = []
        for k in d["getirilmeyen"]:
            _son = (eski[k].get("tarih") or [None])[-1]
            _kunye.append(f"{_ad.get(k, k)} ({k}, son bar {_son})")
        print("  ! piyasa çekimi şu sembolleri döndürmedi — önbellekteki seri "
              "devredildi, satır KENDİ bar tarihiyle yayımlanacak: "
              + " · ".join(_kunye))
    # Boş seans onarımının sınayamadığı semboller de adıyla: meta çekilemediyse
    # o sembolün boş günü ne onarılabildi ne de işaretlenebildi.
    d["meta_olculemedi"] = sorted(meta_yok)
    if meta_yok:
        print(f"  ! boş seans denetimi {len(meta_yok)} sembolde yapılamadı "
              f"(chart ucu cevap vermedi): {' · '.join(sorted(meta_yok)[:12])}")
    _onarilan = [f"{k} {s['onarim']['gun']}" for k, s in d["seri"].items() if s.get("onarim")]
    _eksik = [f"{k} {','.join(s['eksik_seans'])}" for k, s in d["seri"].items() if s.get("eksik_seans")]
    if _onarilan:
        print("  · kaynağın boş verdiği kapanış son işlem fiyatından kuruldu: " + " · ".join(_onarilan))
    if _eksik:
        print("  ! kaynağın boş verdiği seans kurulamadı (piyasa açık ya da vadeli): "
              + " · ".join(_eksik))
    HAM.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    return d


# ─────────────────────────── vadeli sözleşme geçişi (roll)
# yfinance'in "=F" serileri geri-düzeltilmiş DEĞİL: her günün kapanışı o gün ön ay
# olan kontratın kapanışıdır ve ön ay değiştiği gün seri bir kontrattan diğerine
# ATLAR. Kod bu atlamayı fiyat hareketi sanıyordu. 26.08.2026'da beş enerji
# serisinin dördü aynı gün devretti ve bülten şunları yayımladı:
#   RBOB −%11,36 (gerçek −%1,35) · kalorifer −%4,98 (−%2,52)
#   doğal gaz +%3,18 (+%1,37)    · Brent −%3,76 (−%2,46)
# Brent'inki en ağırı oldu: 85,25 dolar kasım kontratının fiyatıydı, ön ay 86,40
# idi; buna rağmen bülten "Enerji teması çürütücü eşiğe (85 dolar) dayandı" dedi.
# İzlenen bir tez, sözleşme değişimi yüzünden çürütülmüş sayıldı.
#
# Çözüm: kontrat zinciri çekilip her günün hangi kontrata ait olduğu eşleştirilir,
# devir günlerinde seri ORANSAL olarak geriye dönük düzeltilir (back-adjustment).
# Son değer olduğu gibi kalır (gerçek güncel fiyat), ondan önceki her şey son
# kontratın birimine çevrilir — böylece d1 kadar h1, a1 ve ybb de temizlenir.
VADELI_KOK = {"RB=F": "RB", "HO=F": "HO", "CL=F": "CL", "NG=F": "NG", "BZ=F": "BZ"}
AY_KODU = "FGHJKMNQUVXZ"          # Ocak…Aralık, vadeli piyasa geleneği


def _kontrat_kodlari(kok: str, bugun: str) -> list[str]:
    """Yahoo'da HÂLÂ LİSTELİ kontratlar: bu aydan bir ay öncesi ile dört ay sonrası.

    Vadesi dolmuş kontratlar Yahoo'dan siliniyor (404), o yüzden geçmişe dönük
    tam bir zincir kurulamıyor. Uygulamada bu bir kayıp değil: düzeltilmesi
    gereken devir HER ZAMAN en yakın olanıdır ve o kontrat hâlâ listelidir.
    """
    ay = int(bugun[:4]) * 12 + int(bugun[5:7]) - 1
    return [f"{kok}{AY_KODU[m % 12]}{(m // 12) % 100:02d}.NYM"
            for m in range(ay - 1, ay + 5)]


# Eşleştirme SONDAN geriye doğru, eşleşme sürdüğü kadar ilerler. Sabit bir
# pencere işe yaramıyor: 70 gün geriye bakıldığında o günlerin ön ayı çoktan
# silinmiş oluyor, eşleşme oranı düşüyor ve sağlam bir seri bile reddediliyor.
# Kapsam ne kadar çıkarsa `roll_kapsam_gun` onu söyler; d1/h1/a1 (1, 5, 21 gün)
# kapsamın içindeyse temizdir, dışındaysa satır bunu bildirir.
ROLL_AZAMI_GERI = 130


def _roll_duzelt(seri: dict) -> dict:
    """Vadeli serileri devir günlerinde geriye dönük oransal düzelt.

    Kontrat zinciri çekilemez ya da eşleşme kurulamazsa seri OLDUĞU GİBİ
    bırakılır ve `roll_bilinmiyor` işaretlenir — uydurma düzeltme, düzeltmemekten
    kötüdür. Düzeltme yapılan seride `roll_kapsam_gun` alanı, geriye doğru kaç
    günün denetlendiğini söyler: ondan eskisi (ör. yıl başından beri) hâlâ devir
    izi taşıyor olabilir.
    """
    import yfinance as yf

    hedef = [k for k in VADELI_KOK if k in seri]
    if not hedef:
        return seri
    bugun = max(seri[k]["tarih"][-1] for k in hedef)
    istek = sorted({kod for k in hedef for kod in _kontrat_kodlari(VADELI_KOK[k], bugun)})
    try:
        ham = yf.download(istek, period="6mo", interval="1d", progress=False,
                          auto_adjust=False, group_by="ticker", threads=True)
    except Exception:
        for k in hedef:
            seri[k]["roll_bilinmiyor"] = True
        return seri

    def kapanis(kod: str) -> dict[str, float]:
        try:
            c = ham[kod]["Close"].dropna()
            return {str(x.date()): float(v) for x, v in zip(c.index, c.values)}
        except Exception:
            return {}

    for k in hedef:
        zincir = {kod: v for kod, v in
                  ((kod, kapanis(kod)) for kod in _kontrat_kodlari(VADELI_KOK[k], bugun)) if v}
        t, kap = seri[k]["tarih"], seri[k]["kapanis"]
        if not zincir or len(t) < 3:
            seri[k]["roll_bilinmiyor"] = True
            continue

        def hangi(i: int) -> str | None:
            for kod, sk in zincir.items():
                v = sk.get(t[i])
                # Tolerans göreli ve gevşek: iki ayrı indirmeden gelen aynı
                # kapanış yuvarlamada son basamakta ayrışabilir.
                if v is not None and abs(v - kap[i]) <= abs(kap[i]) * 1e-4:
                    return kod
            return None

        # Sondan geriye: eşleşme kesildiği yerde dur.
        ait: dict[int, str] = {}
        for i in range(len(t) - 1, max(-1, len(t) - 1 - ROLL_AZAMI_GERI), -1):
            kod = hangi(i)
            if kod is None:
                break
            ait[i] = kod
        bas = min(ait) if ait else len(t)
        if len(ait) < 2:
            seri[k]["roll_bilinmiyor"] = True      # son günler bile eşleşmiyor
            continue
        duzeltilmis = list(kap)
        devirler: list[str] = []
        for i in range(len(t) - 1, bas, -1):
            eski, yeni_k = ait.get(i - 1), ait.get(i)
            if not eski or not yeni_k or eski == yeni_k:
                continue
            a = zincir.get(eski, {}).get(t[i - 1])
            b = zincir.get(yeni_k, {}).get(t[i - 1])
            if not a or not b:
                continue
            oran = b / a
            for j in range(i):                     # devirden ÖNCEKİ her şey
                duzeltilmis[j] *= oran
            devirler.append(t[i])
        seri[k]["kapanis_ham"] = kap
        seri[k]["kapanis"] = duzeltilmis
        seri[k]["devir_gunleri"] = sorted(devirler)
        seri[k]["roll_duzeltildi"] = True
        seri[k]["roll_kapsam_gun"] = len(ait)
    return seri


# ─────────────────────────── yerleşmemiş (canlı) bar
# yf.download günün HENÜZ KAPANMAMIŞ barını da döndürür. Vadelilerde Yahoo'nun
# canlı kotasyonu çoğu zaman en aktif kontratı izlerken tarihsel barlar ön ayı
# izliyor; bu yüzden son bar ~%9 sapıyor ve ertesi gün sessizce düzeliyor.
# 23–25 Ağustos bültenlerinin üçü de bu yüzden sahte düşüş yayımladı ve
# yayımlanan sayılar sonradan değişti — ölçüm olması gereken bülten ölçüm
# olmaktan çıkıyordu. NYMEX uzlaşması 21:30 TSİ; pay bırakıp 22:00 alıyoruz.
UZLASMA_SAATI = 22

# BU KORUMA YALNIZ BEŞ ENERJİ VADELİSİNİ KAPSIYORDU ve asıl sorun oradan çok
# daha genişti. 27.08 bülteni 04:21 UTC'de koştu; 51 enstrümanın 21'i o anda
# HENÜZ AÇIK olan günün barını taşıyordu ve o barın kapanışa göre değişimi
# "günlük değişim" diye yayımlandı.
#
# Altın somut örneği: 25.08 kapanış 4.638,1 · 26.08 kapanış 4.598,2 — yani
# dünkü seans %0,86 EKSİDE bitti. Bülten ise 26.08 kapanışını 27.08'in 04:21
# UTC'deki canlı seviyesiyle (4.679,9) kıyaslayıp "altın +%1,78" yazdı. Ölçülen
# şey dünkü seans değil, GECELİK hareketti; işareti de dünküyle ters.
#
# Kural: bir günün barı, o piyasa kapanmadan kullanılamaz. Aşağıdaki eşik,
# grubun barının artık DEĞİŞMEYECEĞİ UTC saatidir. 7/24 işlem gören piyasalarda
# (spot döviz, kripto) günün barı gün bitmeden kapanmaz; onlara 24 yazılır,
# yani bugünün barı hiçbir saatte kullanılmaz. Tanımsız grup da 24 sayılır:
# yeni bir grup eklendiğinde bu kusur sessizce geri gelmesin.
KAPANIS_UTC = {
    "asya_hisse": 9,             # Tokyo 06:00, Şanghay 07:00, Hong Kong 08:00 UTC
    "tr_hisse": 16,              # BIST 15:00 UTC (18:00 TSİ)
    "ab_hisse": 18,              # Frankfurt/Paris/Londra 15:30–16:30 UTC
    "abd_hisse": 22,             # New York 20:00 UTC (yaz) / 21:00 (kış)
    "faiz": 22,                  # ABD tahvil seansı
    "kredi": 22,                 # ABD'de işlem gören kredi/GOP fonları
    "metal": UZLASMA_SAATI,      # COMEX uzlaşması 18:30 UTC
    "enerji": UZLASMA_SAATI,     # NYMEX uzlaşması 18:30 UTC
    "tr_fx": 24,                 # 7/24
    "g10_fx": 24,                # 7/24
    "kripto": 24,                # 7/24
}
VARSAYILAN_KAPANIS = 24


def _yerlesmemis_dus(seri: dict) -> dict:
    """Piyasası henüz kapanmamış günün barını seriden düşür.

    UTC ile çalışır: koşucu UTC'de, geliştirme makinesi değil. `datetime.now()`
    ikisinde farklı saat verir ve koruma sessizce kayar.
    """
    simdi = datetime.now(timezone.utc)
    bugun = simdi.date().isoformat()
    gruplar = {v.kod: v.grup for v in VARLIKLAR}
    for k in list(seri):
        s = seri[k]
        if not s.get("tarih") or s["tarih"][-1] != bugun:
            continue
        if simdi.hour >= KAPANIS_UTC.get(gruplar.get(k, ""), VARSAYILAN_KAPANIS):
            continue
        s["tarih"] = s["tarih"][:-1]
        s["kapanis"] = s["kapanis"][:-1]
        if s.get("kapanis_ham"):
            s["kapanis_ham"] = s["kapanis_ham"][:-1]
        s["yerlesmemis_dusuruldu"] = True
    return seri


def _tarih_gun(t: str):
    """ISO tarihi ordinal güne çevir; ayrıştırılamazsa None."""
    import datetime as _dt
    try:
        return _dt.date.fromisoformat(str(t)[:10]).toordinal()
    except Exception:
        return None


# ÖLÇÜLDÜ — HAFTA SONU BOŞLUĞU σ'YI ŞİŞİRMİYOR (31.08.2026).
# Sezgi şunu söyler: pazartesi kapanışı Cuma'ya göre ÜÇ takvim günü kapsar,
# öyleyse günlük σ ile kıyaslamak hareketi olduğundan olağandışı gösterir.
# Sezgi YANLIŞ ve ölçüldü. 49 enstrümanın tamamında, bir yıllık seride, üç
# takvim günlük (hafta sonu) değişimlerin σ'sının bir günlüklere oranı:
#     medyan 1,00   (rastgele yürüyüş beklentisi √3 = 1,73)
#     1,30'u aşan yalnız 3/49 — NG, RB (hafta sonu seansı olan enerji) ve JPY
# Üç günden UZUN boşluklarda da (bayram, 4-11 gün) oran medyanı 1,02.
# Sebep basit: bunlar KAPANIŞTAN KAPANIŞA fiyatlar; hafta sonu seans yoktur,
# yani "üç takvim günü" hâlâ TEK seanslık risktir. USD/TRY'de hafta sonu
# değişimlerinin ortalaması (+0,029%) hafta içinin (+0,068%) ALTINDA — taşıma
# bile birikmiyor. Bu yüzden d1_sigma'ya boşluk ölçeklemesi UYGULANMAZ;
# uygulansaydı gerçek hareketleri sistematik olarak gizlerdi.
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

# Haftalık bültenin kıyas penceresi HAFTADIR; olağandışılık da o pencerede
# ölçülmeli. Günlük σ ile haftalık hareketi kıyaslamak ölçek hatasıdır: bir
# haftalık değişim doğası gereği günlüğün ~√5 katıdır, günlük σ'ya bölününce
# her şey "olağandışı" çıkar. Bu yüzden haftalık σ'nın kendi tabanı var.
OYNAKLIK_HAFTA = 20         # kaç haftalık gözlem
HAFTA_GUN = 5               # bir haftanın iş günü sayısı


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
    return _std(d)


def _haftalik_degisimler(kapanis: list[float], getiri: bool, n: int) -> list[float]:
    """Son n haftalık (5 iş günü) değişim — h1 ile aynı birimde.

    Pencereler ÖRTÜŞMEZ: adımlar beşer iş günü geriye atlanarak alınır.
    Örtüşen haftalık pencereler ardışık bağımlılık taşır ve standart sapmayı
    olduğundan küçük gösterir; küçük σ ise her hareketi olağandışı yapardı.
    """
    out = []
    i = len(kapanis) - 1
    while i - HAFTA_GUN >= 0 and len(out) < n:
        onceki = kapanis[i - HAFTA_GUN]
        if onceki:
            out.append((kapanis[i] - onceki) * 100.0 if getiri
                       else (kapanis[i] / onceki - 1) * 100.0)
        i -= HAFTA_GUN
    return out


def _oynaklik_hafta(kapanis: list[float], getiri: bool) -> float | None:
    d = _haftalik_degisimler(kapanis, getiri, OYNAKLIK_HAFTA)
    if len(d) < OYNAKLIK_ASGARI:
        return None
    return _std(d)


def _std(d: list[float]) -> float | None:
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
    # σ, main'in devir düzeltmesinden GEÇMİŞ seri üzerinden hesaplanır: ham
    # seride vade geçişi günleri oynaklığı şişirir ve z-skorunu küçültürdü.
    sigma = _oynaklik(k, getiri)
    sigma_h = _oynaklik_hafta(k, getiri)
    # Vadeli serilerde devir düzeltmesi yalnız hâlâ listeli kontratların
    # kapsadığı kadar geriye gider; ondan eskisi hâlâ devir izi taşıyabilir.
    # Satır bunu kendisi söylesin: okur hangi sayının temiz olduğunu bilmeli.
    ek_not = ""
    if v.kod in VADELI_KOK:
        if s.get("roll_bilinmiyor"):
            ek_not = ("vadeli seri; vade geçişi denetlenemedi — büyük hareketler "
                      "sözleşme değişiminden kaynaklanıyor olabilir")
        else:
            kapsam = s.get("roll_kapsam_gun") or 0
            uzun = [ad for ad, gun in (("aylık", 21), ("yıl başından beri", 252))
                    if kapsam < gun]
            if uzun:
                ek_not = ("vadeli seri; vade geçişleri son %d günde arındırıldı, "
                          "%s değişim yaklaşıktır" % (kapsam, " ve ".join(uzun)))
    return {
        "kod": v.kod, "ad": v.ad, "grup": v.grup, "birim": v.birim,
        "ondalik": v.ondalik, "tip": v.tip,
        "not": "; ".join(x for x in (v.not_, ek_not) if x),
        "vade_gecisi": s.get("devir_gunleri") or [],
        # Devir düzeltmesi kurulamadıysa SEVİYE ham kontrat kapanışıdır ve
        # önceki yayımla kıyaslanabilir değildir; denetim bunu uyarıya çevirir.
        "roll_bilinmiyor": bool(s.get("roll_bilinmiyor")),
        "son": round(son, v.ondalik), "tarih": t[-1],
        # Kaynağın boş verdiği seansın izi (bkz. _bos_seans_onar). `onarim`:
        # son kapanış kaynağın o günkü son işlem fiyatından kuruldu. `eksik_seans`:
        # kaynak bu tamamlanmış seansları boş verdi ve kurulamadı — satır kendi
        # (eski) tarihiyle duruyor. `devredilen`: kaynak bugün boş verdiği bir
        # günü daha önce dolu vermişti, eski değer yerinde bırakıldı.
        "onarim": s.get("onarim"),
        "eksik_seans": s.get("eksik_seans") or [],
        "devredilen": s.get("devredilen") or [],
        # d1'in kapsadığı TAKVİM günü. Pazartesi kapanışı Cuma'ya göre üç
        # takvim günü geride ama BİR seans ilerideymiş gibi ölçülür — ve bu
        # DOĞRUDUR: kapanıştan kapanışa hareket, arada kaç takvim günü olursa
        # olsun tek seanslık risktir. 49 enstrümanda ölçüldü, bkz. aşağıdaki
        # not. Alan yine de yazılıyor çünkü OKURUN gördüğü şey takvim: pazartesi
        # yayımlanan bültende "günlük değişim" Cuma'ya aitse bunun söylenmesi
        # gerekir (satır tarihini denetim de bu alandan okur).
        "gap_gun": ((_tarih_gun(t[-1]) - _tarih_gun(t[-2])) if len(t) > 1 else None),
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
        # Haftalık hareketin kaç HAFTALIK standart sapma olduğu. Haftaya bakış
        # bültenin kıyas penceresi hafta olduğu için olağandışılık orada bu
        # ölçüden okunur; günlük σ ile haftalık hareket kıyaslanmaz.
        "sigma_hafta": None if sigma_h is None else round(sigma_h, 2),
        "h1_sigma": (None if sigma_h is None or d(5) is None
                     else round(d(5) / sigma_h, 1)),
    }


GUN_ADI = {0: "Pazartesi", 1: "Salı", 2: "Çarşamba", 3: "Perşembe",
           4: "Cuma", 5: "Cumartesi", 6: "Pazar"}


def _seans_metni(iso: str) -> str:
    """'2026-08-28' → '28.08.2026 Cuma kapanışı'."""
    import datetime as _dt
    try:
        g = _dt.date.fromisoformat(str(iso)[:10])
    except Exception:
        return str(iso)
    return f"{g:%d.%m.%Y} {GUN_ADI[g.weekday()]} kapanışı"


def turetilmis(seri: dict) -> list[dict]:
    """Eğri eğimleri, crack spread'ler, oranlar — trader'ın baktığı türevler."""
    def son(kod, geri=0):
        s = seri.get(kod)
        if not s or len(s["kapanis"]) <= geri:
            return None
        return s["kapanis"][-1 - geri]

    out = []

    def bar_gunu(*kodlar) -> str:
        """Bacakların son bar günü; farklıysa hepsi ('2026-08-28/2026-08-29').
        Türev satırın 'aynı gün' anahtarı budur — revizyon kıyası bu alandan yürür."""
        gunler = sorted({str(seri[k]["tarih"][-1]) for k in kodlar
                         if seri.get(k) and seri[k].get("tarih")})
        return "/".join(gunler)

    def ekle(ad, deger, birim, d1, aciklama, ondalik=2, kodlar=(), degisim_birim=None):
        if deger is None:
            return
        out.append({"ad": ad, "deger": round(deger, ondalik), "birim": birim,
                    "d1": None if d1 is None else round(d1, 1), "aciklama": aciklama,
                    # Revizyon ve biçim için: satırın günü, hanesi ve değişimin birimi
                    # (BIST dolar bazlı: seviye USD puan, günlük değişim %).
                    "tarih": bar_gunu(*kodlar), "ondalik": ondalik,
                    "degisim_birim": degisim_birim if degisim_birim is not None else birim})

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
        ekle(ad, e, "bp", d1, acik, 0, kodlar=(uzun, kisa))

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
             "Genişlemesi ürün talebinin ham petrolden güçlü olduğunu gösterir.",
             kodlar=("CL=F", "RB=F", "HO=F"))
        ekle("Benzin crack (RBOB−WTI)", rb * 42 - cl, "USD/varil",
             (rb * 42 - cl) - (rb1 * 42 - cl1) if None not in (rb1, cl1) else None,
             "Benzin rafineri marjı; sürüş sezonu ve ürün stoklarına duyarlı.",
             kodlar=("CL=F", "RB=F"))
        ekle("Distilat crack (HO−WTI)", ho * 42 - cl, "USD/varil",
             (ho * 42 - cl) - (ho1 * 42 - cl1) if None not in (ho1, cl1) else None,
             "Motorin/kalorifer marjı; sanayi ve nakliye talebinin göstergesi.",
             kodlar=("CL=F", "HO=F"))
    bz, bz1 = son("BZ=F"), son("BZ=F", 1)
    if None not in (bz, cl):
        ekle("Brent−WTI farkı", bz - cl, "USD/varil",
             (bz - cl) - (bz1 - cl1) if None not in (bz1, cl1) else None,
             "Atlantik havzası ile ABD iç piyasası arasındaki taşıma/arz farkı.",
             kodlar=("BZ=F", "CL=F"))

    # Oranlar
    xau, xag = son("GC=F"), son("SI=F")
    xau1, xag1 = son("GC=F", 1), son("SI=F", 1)
    if None not in (xau, xag) and xag:
        ekle("Altın/gümüş oranı", xau / xag, "kat",
             (xau / xag - xau1 / xag1) if None not in (xau1, xag1) and xag1 else None,
             "Yükselmesi güvenli liman talebinin sanayi talebine baskın geldiğini gösterir.",
             kodlar=("GC=F", "SI=F"))

    # BIST'in dolar bazlı seviyesi — yabancı yatırımcının gördüğü getiri
    x, usd = son("XU100.IS"), son("USDTRY=X")
    x1, usd1 = son("XU100.IS", 1), son("USDTRY=X", 1)
    if None not in (x, usd) and usd:
        ekle("BIST 100 (dolar bazlı)", x / usd, "USD puan",
             ((x / usd) / (x1 / usd1) - 1) * 100 if None not in (x1, usd1) and usd1 else None,
             "TL endeksin kurdan arındırılmış hâli; yabancının gördüğü performans.", 1,
             kodlar=("XU100.IS", "USDTRY=X"), degisim_birim="%")
    return out


def en_cok_hareket(satirlar: list[dict], n: int = 6, haftalik: bool = False) -> dict:
    """Günün ve haftanın en büyük hareketleri — yorumun nereye bakacağını söyler.

    OLAĞANDIŞILIK LİSTESİ BÜLTENİN PENCERESİNİ İZLER. Günlük bültende günlük
    hareket günlük σ'ya, haftaya bakışta haftalık hareket HAFTALIK σ'ya bölünür.
    Karıştırmak ölçek hatasıdır: haftalık değişim doğası gereği günlüğün ~√5
    katıdır, günlük σ'ya bölününce sıradan bir hafta bile 2σ'yı aşar ve liste
    "olağandışı" olmayan şeylerle dolar. `sigma_kip` hangi pencerenin
    kullanıldığını açıkça söyler; okuyan katman (sayfa ve denetim) başlığı ve
    aradığı hareketi ona göre seçer.

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
    z_alan, dg_alan, oyn_alan = (("h1_sigma", "h1", "sigma_hafta") if haftalik
                                 else ("d1_sigma", "d1", "sigma_gun"))
    sigmali = [s for s in satirlar if s.get(z_alan) is not None]
    return {
        "gunluk": [{"ad": s["ad"], "deger": s["d1"], "birim": "%"} for s in sirala("d1")],
        "haftalik": [{"ad": s["ad"], "deger": s["h1"], "birim": "%"} for s in sirala("h1")],
        "faiz_haftalik": [{"ad": s["ad"], "deger": s["h1"], "birim": "bp"}
                          for s in sorted(getiriler, key=lambda s: abs(s["h1"]), reverse=True)[:4]],
        "sigma_kip": "haftalik" if haftalik else "gunluk",
        "sigma": [{"ad": s["ad"], "deger": s[dg_alan], "birim": s["degisim_birim"],
                   "sigma": s[z_alan], "oynaklik": s[oyn_alan]}
                  for s in sorted(sigmali, key=lambda s: abs(s[z_alan]),
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
            # BU CÜMLE BİR ZAMANLAR "kaynak bu değeri GÜNCEL saymıyor" diyordu ve
            # okur bunu "TCMB yayımlamıyor" diye anlıyordu. Yanlıştı: 30.08.2026'da
            # ölçüldü — TCMB AOFM'yi her gün basıyor ve 24 Ağustos'ta 40,00'dan
            # 37,00'ye indirmişti; değeri gizleyen bizim kendi geçerlilik
            # kapımızdı (fonlama tabanı 5 mlr TL eşiğinin altında). Bir ölçünün
            # neden gizlendiğini söylemeyen not, gizlemekten daha kötüdür.
            aciklama = ((aciklama + " · ") if aciklama else "") + \
                (d.get(f"{anahtar}_gecersiz_sebep")
                 or "hattın geçerlilik kapısı bu günü elemiş") + \
                "; gösterilen son geçerli gün"
        out.append({"ad": ad, "deger": round(float(v), ondalik), "birim": birim,
                    "tarih": tarih, "aciklama": aciklama,
                    "gecerli": False if gecerli is False else True})

    al("fonlama-likidite", "politika", "Politika faizi (1 hafta repo)")
    al("fonlama-likidite", "koridor_alt", "Koridor alt bandı")
    al("fonlama-likidite", "koridor_ust", "Koridor üst bandı (gecelik borç verme)")
    al("fonlama-likidite", "aofm", "Ağırlıklı ortalama fonlama maliyeti")
    # Fazla likidite rejiminde TCMB parasının marjinal fiyatını fonlama değil
    # STERİLİZASYON belirler; fonlama bacağı 4 mlr TL iken sterilizasyon 1.251
    # mlr TL ise "fonlama maliyeti" rejimi anlatmaz. AOFM'nin geçerlilik kapısı
    # kapandığında pano boş kalıyordu ve bülten üç haftadır "gevşemenin ölçüsü
    # yok" diye yazdı — oysa ölçü hattın içinde duruyordu. AOSM bu çalışmanın
    # TÜRETMESİDİR, TCMB serisi değildir; satır bunu kendi üstünde söylüyor.
    al("fonlama-likidite", "aosm", "Ağırlıklı ort. sterilizasyon maliyeti",
       aciklama="bu çalışmanın türetmesi, TCMB serisi DEĞİL; fazla likidite "
                "rejiminde marjinal TCMB faizi")
    al("fonlama-likidite", "marjinal", "Marjinal TCMB faizi",
       aciklama="rejime göre fonlama ya da sterilizasyon fiyatı")
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


def seans_ozeti(gruplar: list[dict]) -> dict:
    """Anlık görüntünün satırları hangi seanslara dağılıyor ve NEDEN.

    `kapanis_seansi` en TAZE satırın seansını söyler; 23.09.2026'da elli bir
    satırın yirmi üçü bir seans geride olduğu hâlde başlık "22.09.2026 Salı
    kapanışı" diyordu ve denetim yalnız o alana baktığı için hiçbir şey
    görmedi. Bu özet dağılımı ve sebebi AYRI AYRI taşır: tatil (kaynak o gün
    satır açmadı — burada iz bırakmaz), kaynağın boş verdiği ve kurulamayan
    seans, kaynağın son işlem fiyatından kurulan kapanış. AĞA ÇIKMAZ.
    """
    satirlar = [s for g in gruplar for s in g.get("satirlar") or [] if s.get("tarih")]
    say: dict[str, int] = {}
    for s in satirlar:
        say[s["tarih"]] = say.get(s["tarih"], 0) + 1
    return {
        "dagilim": [{"tarih": t, "satir": n} for t, n in sorted(say.items(), reverse=True)],
        "satir": len(satirlar),
        "kaynak_bos": [{"ad": s["ad"], "kod": s["kod"], "tarih": s["tarih"],
                        "gunler": s["eksik_seans"]}
                       for s in satirlar if s.get("eksik_seans")],
        "son_islemden": [{"ad": s["ad"], "kod": s["kod"], "gun": s["onarim"]["gun"]}
                         for s in satirlar if s.get("onarim")],
        "devredilen": [{"ad": s["ad"], "kod": s["kod"], "gunler": s["devredilen"]}
                       for s in satirlar if s.get("devredilen")],
    }


def topla(tazele: bool = False, haftalik: bool = False) -> dict:
    ham = _ham_veri(tazele)
    seri = ham["seri"]
    satirlar = [x for x in (satir(v, seri) for v in VARLIKLAR) if x]
    gruplar = []
    for gid, baslik in GRUP_BASLIK:
        icerik = [s for s in satirlar if s["grup"] == gid]
        if icerik:
            gruplar.append({"id": gid, "baslik": baslik, "satirlar": icerik})
    eksik = [v.ad for v in VARLIKLAR if v.kod not in seri]
    # ANLIK GÖRÜNTÜNÜN SEANSI. Satırların tamamı aynı güne ait olmayabilir
    # (farklı borsalar, farklı tatiller); en tazesi ile en bayatı ayrı ayrı
    # yazılır. Pazartesi yayımlanan bir bültende bu alan "Cuma" der ve okur
    # "günlük değişim"i bugüne ait sanmaz — 31.08.2026'da elli satırın ellisi
    # üç gün geride yayımlandı ve bunu söyleyen hiçbir alan yoktu.
    _tarihler = sorted({s["tarih"] for g in gruplar for s in g["satirlar"] if s.get("tarih")})
    return {
        "zaman": ham["zaman"],
        "kapanis_tarih": _tarihler[-1] if _tarihler else None,
        "kapanis_en_eski": _tarihler[0] if _tarihler else None,
        "kapanis_seansi": _seans_metni(_tarihler[-1]) if _tarihler else None,
        "seans_ozeti": seans_ozeti(gruplar),
        # Boş seans denetiminin chart ucuna ulaşamadığı semboller: o satırların
        # boş günü ne onarıldı ne işaretlendi; "temiz" sanılmasın.
        "seans_sinanamadi": ham.get("meta_olculemedi") or [],
        "gruplar": gruplar,
        "turetilmis": turetilmis(seri),
        "tr_faizleri": tr_faizleri(),
        "en_cok_hareket": en_cok_hareket(satirlar, haftalik=haftalik),
        "eksik": eksik,
        # Bu koşunun çekiminden DÖNMEYEN, yani önbellekten devredilen semboller.
        # Satırları anlık görüntüde durur ama kendi (eski) bar tarihiyle durur;
        # alan, "bu satır bugün ölçülmedi" sorusunun tek yerden cevabıdır.
        "getirilmeyen": ham.get("getirilmeyen") or [],
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
