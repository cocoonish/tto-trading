#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Okura giden adlar — tek tanım. Figürler (sekil.py), tablolar (site verisi) ve ders metni
(ders.py) birimlerin, parametrelerin, olayların ve çıkış nedenlerinin adını YALNIZ buradan okur;
aynı şeyin iki yerde iki adı olursa okur onları iki ayrı şey sanır."""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

#: Strateji birimleri (kosu.BIRIMLER anahtarları): okura giden tam ad ve figür etiketi için kısa ad.
BIRIM = {
    "orb": ("Londra açılış aralığı kırılımı (ORB)", "Londra ORB"),
    "asya": ("Asya aralığı kırılımı", "Asya aralığı"),
    "nyib_0800": ("New York ilk denge kırılımı — 08:00 ET", "NY IB 08:00"),
    "nyib_0930": ("New York ilk denge kırılımı — 09:30 ET", "NY IB 09:30"),
    "icmum": ("İç mum (inside bar) kırılımı", "İç mum"),
    "sikisma": ("Sıkışma kırılımı (Bollinger–Keltner)", "Sıkışma"),
    "pdhl": ("Önceki gün tepe/dip kırılımı (PDH/PDL)", "PDH/PDL"),
    "sahte_orb": ("Başarısız kırılım — Londra aralığı (turtle soup)", "Sahte ORB"),
    "sahte_asya": ("Başarısız kırılım — Asya aralığı", "Sahte Asya"),
    "sahte_pdhl": ("Başarısız kırılım — önceki gün tepe/dip", "Sahte PDH/PDL"),
    "vwap_donus": ("VWAP'a dönüş", "VWAP dönüş"),
    "vwap_cekilme": ("VWAP geri çekilmesi (trend yönünde)", "VWAP çekilme"),
    "pivot_donus": ("Pivot dönüşü", "Pivot dönüş"),
    "pivot_kirilim": ("Pivot kırılımı", "Pivot kırılım"),
    "fiks_momentum": ("WM/R 16:00 fiksingi — momentum", "Fiks momentum"),
    "fiks_donus": ("WM/R 16:00 fiksingi — dönüş", "Fiks dönüş"),
    "momentum": ("Gün içi momentum: Londra ilk saati → New York öğleden sonrası", "Gün içi momentum"),
    "n1": ("N1 — haber kırılımı (ilk mumun yönünde)", "N1 kırılım"),
    "n2": ("N2 — haber fade'i (ilk mumun tersine)", "N2 fade"),
    "n3": ("N3 — haber öncesi aralık kırılımı (straddle)", "N3 straddle"),
    "n4": ("N4 — başarısız haber kırılımı", "N4 başarısız"),
    "n5": ("N5 — geri çekilme sonrası devam", "N5 devam"),
}

#: Derslerin birimleri (okuma sırası). Her birim tam olarak bir dersin konusudur.
DERS_BIRIM = {
    "fx-gunici-seans-kirilimlari": ["orb", "asya", "nyib_0800", "nyib_0930"],
    "fx-gunici-yapi-kirilimlari": ["icmum", "sikisma", "pdhl", "pivot_kirilim"],
    "fx-gunici-fade": ["sahte_orb", "sahte_asya", "sahte_pdhl", "vwap_donus", "pivot_donus", "fiks_donus"],
    "fx-gunici-haber": ["n1", "n2", "n3", "n4", "n5"],
    "fx-gunici-akis": ["fiks_momentum", "momentum", "vwap_cekilme"],
}

#: Serinin okuma sırası (sitedeki ders grubu `site/src/lib/dersGruplari.ts` aynı sırayı taşır; dogrula.py iki
#: listeyi karşılaştırır).
DERS_SIRA = ["fx-gunici-giris", "fx-gunici-seans-kirilimlari", "fx-gunici-yapi-kirilimlari", "fx-gunici-fade",
             "fx-gunici-haber", "fx-gunici-akis", "fx-gunici-karsilastirma", "fx-gunici-metodoloji"]

#: Parametrelerin okur adı ve değerlerinin okur yazımı.
PARAM = {
    "tf": "zaman dilimi",
    "stop_yeri": "stop yeri",
    "stop_turu": "stop türü",
    "hedef": "hedef",
    "son_giris_londra": "son giriş (Londra)",
    "aralik_sonu_londra": "aralık sonu (Londra)",
    "son_giris_et": "son giriş (New York)",
    "baslangic_et": "başlangıç (New York)",
    "ib_pencere": "ilk denge penceresi",
    "referans": "referans mum",
    "gecerlilik": "geçerlilik (mum)",
    "seans": "seans",
    "sure": "sıkışma süresi (mum)",
    "yon": "yön kuralı",
    "baslangic": "seviye geçerliliği",
    "stop_kurali": "stop kuralı",
    "seviye": "seviye",
    "pencere": "geri dönüş penceresi (mum)",
    "capa": "VWAP çapası",
    "k": "eşik (σ ya da ATR katı)",
    "n": "trend mumu sayısı",
    "tur": "tür",
    "gecikme_mum": "gecikme (mum)",
    "tutma_mum": "tutma (mum)",
    "cikis_et": "çıkış (New York)",
    "giris_mumu": "giriş mumu",
    "giris": "giriş",
    "on_mum": "haber öncesi aralık (mum)",
    "geri_cekilme": "geri çekilme oranı",
}
DEGER = {
    "karsi_uc": "karşı uç", "orta": "orta", "sert": "sert", "kapanis": "kapanış", "yok": "yok",
    "1R": "1R", "2R": "2R", "gun_sonu": "gün sonu", "zaman": "zaman", "vwap": "VWAP", "seviye": "seviye",
    "oncesi": "haber öncesi fiyat", "itki_ucu": "itkinin ucu",
    "tf": "tek mum", "60": "60 dk", "ic": "iç mum", "ana": "ana mum", "londra_ny": "Londra + New York",
    "tum_gun": "bütün gün", "kutu": "kutu kırılımı", "ttm": "TTM momentumu", "gun_basi": "gün başından",
    "londra": "Londra açılışından", "sinyal_mumu": "sinyal mumunun ucu", "atr_yarim": "0,5·ATR",
    "orb": "Londra aralığı", "asya": "Asya aralığı", "pdhl": "önceki gün tepe/dip", "fx_gunu": "FX günü başı",
    "P": "P", "R1S1": "R1/S1", "donus": "dönüş", "kirilim": "kırılım", "momentum": "momentum",
    "ilk_kapanis": "ilk mum kapanınca", "teyit": "teyit mumundan sonra",
}

#: Çıkış nedeni (motor.NEDEN kodları).
NEDEN = {1: "stop", 2: "hedef", 3: "zaman / gün sonu", 4: "kapanış stopu", 5: "boşlukla stop", 6: "boşlukla hedef"}

def neden_ad(i: dict, gun_sonu_et: str) -> str:
    """Çıkış nedeninin okur adı. Motor zaman çıkışı ile gün sonu kapanışını aynı kodla (3) yazar; ikisi çıkış
    dakikasının New York saatinden ayrılır (gün sonu kapanışı önceden kaydın gün sonu saatindedir)."""
    n = i.get("neden")
    if n == 3 and i.get("cikis_t") is not None:
        et = datetime.fromtimestamp(int(i["cikis_t"]), timezone.utc).astimezone(ZoneInfo("America/New_York"))
        return "gün sonu kapanışı" if et.strftime("%H:%M") == gun_sonu_et else "zaman çıkışı"
    return NEDEN.get(n, "")


#: Haber olayları.
OLAY = {
    "NFP": "ABD tarım dışı istihdam (NFP)", "CPI": "ABD TÜFE (CPI)", "FOMC_karar": "FOMC kararı",
    "FOMC_basin": "FOMC basın toplantısı", "ECB_karar": "ECB kararı", "ECB_basin": "ECB basın toplantısı",
    "BoE_karar": "BoE kararı",
}

#: Koşul kovalarının okuma sırası (metin ve figür aynı sırayı kullanır): "değil" önce, terciller küçükten büyüğe,
#: haftanın günleri takvim sırasıyla. Listede olmayan kova ölçümdeki sırasını korur.
KOVA_OKUMA = ["değil", "alt", "orta", "üst", "Pzt", "Sal", "Çar", "Per", "Cum"]

#: Hüküm (onkayit.toml [hukum]).
HUKUM = {"calisiyor": "çalışıyor", "zayif": "zayıf", "calismiyor": "çalışmıyor", "olculemedi": "ölçülemedi"}

#: Koşul değişkenleri (ozellik.py).
KOSUL = {
    "range_atr": "aralık / günlük ATR", "asya_atr": "Asya aralığı / günlük ATR",
    "onceki_gun_range_atr": "önceki gün aralığı / ATR", "onceki_gun_yon": "önceki günün yönü",
    "nr4": "NR4 (son 4 günün en dar aralığı)", "nr7": "NR7 (son 7 günün en dar aralığı)",
    "acilis_farki_atr": "açılış farkı / ATR", "oynaklik_yuzdelik": "oynaklık yüzdeliği",
    "trend60": "60 dk trend (EMA50 tarafı)", "hafta_gunu": "haftanın günü", "haber_gunu": "büyük olay günü",
    "ay_sonu": "ay sonu", "dst_gecis_haftasi": "saat değişimi haftası", "dst_ara_donem": "Londra–NY farkı 4 saat",
}


def param_yaz(ad: str, deger) -> str:
    return f"{PARAM.get(ad, ad)}: {DEGER.get(str(deger), str(deger))}"


def hepsi() -> dict:
    """Site verisine giden kopya (tablo bileşeni adları buradan okur)."""
    return {"birim": {k: {"ad": v[0], "kisa": v[1]} for k, v in BIRIM.items()}, "ders_birim": DERS_BIRIM,
            "param": PARAM, "deger": DEGER, "neden": {str(k): v for k, v in NEDEN.items()}, "olay": OLAY,
            "hukum": HUKUM, "kosul": KOSUL}
