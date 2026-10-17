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
    "fiks_momentum": ("WM/R 16:00 fiksingi — momentum", "Fiksing momentumu"),
    "fiks_donus": ("WM/R 16:00 fiksingi — dönüş", "Fiksing dönüşü"),
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

def islem_r(i: dict) -> float | None:
    """Bir örnek işlemin okura yazılan R'si: kaydın pip sonucu / riski (ikisi de iki haneli, okurun gördüğü sayılar).
    Kayıttaki r üç haneye yuvarlıdır; onu bir kez daha iki haneye yuvarlamak (0,785 → 0,79) yanında yazılan
    22,8 / 29,05 = 0,78 ile çelişirdi. Ders metni de figür başlığı da bu tanımı okur."""
    p, risk = i.get("pnl_pip"), i.get("R_pip")
    if p is not None and risk:
        return p / risk
    return i.get("r")


def mevsim_kovalari(saat_tsi: dict) -> tuple[int, int] | None:
    """Tek bir yerel saatte giren kuralın iki TSİ saat kovası: (yaz saati, kış saati); kural öyle değilse None.

    TSİ yıl boyu UTC + 3'tür; aynı yerel saatin TSİ karşılığı o şehrin yaz saatinde bir saat erkendir ve yaz saati
    yılın yedi-sekiz ayı sürer. Böyle bir kuralın bütün işlemleri iki ardışık TSİ saatine düşer ve erken kova daha
    kalabalıktır; kovalar yalnız bu iki koşul birlikte tutunca yaz ve kış saati diye adlandırılır. Metin
    (ders_motor) ve giriş saati figürü (sekil) bu tek tanımı okur."""
    st = {int(h): int(x.get("n") or 0) for h, x in (saat_tsi or {}).items() if (x.get("n") or 0) > 0}
    if len(st) != 2:
        return None
    a, b = sorted(st)
    erken, gec = (a, b) if (a + 1) % 24 == b else (b, a) if (b + 1) % 24 == a else (None, None)
    if erken is None or st[erken] <= st[gec]:
        return None
    return erken, gec


def turetilmis(b: dict) -> bool:
    """Birimin varsayılanı ön kayıtta yoksa doğru: birim, ön kaydın varsayılanında TANIMLI bir boyutu kendi sabitiyle
    değiştirmişse (NY IB 08:00: ön kayıt başlangıcı 09:30 seçti). Ön kaydın boş bıraktığı bir boyutu sabitlemek
    (başarısız kırılımın seviyesi) türetme değildir. Girdi ölçümün birim kaydıdır (sabit, onkayit_varsayilan)."""
    s, ov = b.get("sabit") or {}, b.get("onkayit_varsayilan") or {}
    return any(ov.get(k) is not None and ov.get(k) != v for k, v in s.items())


def varsayilan_ad(b: dict) -> str:
    """Birimin varsayılanının okur adı; metin ve figür bu tek tanımı okur."""
    return "türetilmiş varsayılan" if turetilmis(b) else "önceden kayıtlı varsayılan"


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
#: Olayların figür etiketindeki kısa adı (örnek günlerin olay çizgisi).
OLAY_KISA = {
    "NFP": "NFP", "CPI": "ABD TÜFE", "FOMC_karar": "FOMC karar", "FOMC_basin": "FOMC basın", "ECB_karar": "ECB karar",
    "ECB_basin": "ECB basın", "BoE_karar": "BoE karar",
}

#: Koşul kovalarının okuma sırası (metin ve figür aynı sırayı kullanır): "değil" önce, terciller küçükten büyüğe,
#: haftanın günleri takvim sırasıyla, işlem yönüne göre işaretli kovalarda önce "aynı yön"/"trend yönünde". Ölçümdeki
#: her kova listede durmalıdır (kapı: dogrula.kova_sirasi); listede olmayan kova ölçümdeki sırasını korurdu ve aynı
#: değişken figürden figüre ters sırayla basılıyordu.
KOVA_OKUMA = ["değil", "NR4", "NR7", "haber günü", "ay sonu", "geçiş haftası", "ara dönem", "alt", "orta", "üst",
              "Pzt", "Sal", "Çar", "Per", "Cum", "aynı yön", "ters yön", "trend yönünde", "trend tersine"]

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


def esik_birimi(aile: str) -> str:
    """'k' parametresinin birimi aileye göre: VWAP bandında σ, haber fade'inde ilk mum hareketinin ATR katı."""
    return "σ" if aile == "vwap_donus" else "×ATR"


def param_ad(ad: str, aile: str = "") -> str:
    """Parametrenin okur adı; 'k' aileye göre birimiyle ("eşik (σ)" · "eşik (×ATR)"). Aile verilmezse genel ad."""
    if ad == "k" and aile:
        return f"eşik ({esik_birimi(aile)})"
    return PARAM.get(ad, ad)


def _sayi(x: float, b: int) -> str:
    """Site sözleşmesi (ders_motor.sayi ile aynı): ondalık virgül, binlik nokta, eksi U+2212."""
    s = f"{abs(x):,.{b}f}".replace(",", "§").replace(".", ",").replace("§", ".")
    return ("−" + s) if x < 0 and float(s.replace(".", "").replace(",", ".")) != 0 else s


def deger_yaz(ad: str, deger, aile: str = "") -> str:
    """Parametre değerinin okur yazımı (figür etiketi ve alt yazısı): 'k' birimiyle ("1,5σ", "2,0×ATR"), geri çekilme
    oranı yüzdeyle ("%38,2"), zaman dilimi dakikayla, ondalıklı değer virgülle; öbürleri DEGER'den. Değer ızgara
    ekseninden dizge olarak da gelebilir ("1.0")."""
    if deger is None:
        return "—"
    if ad == "tf":
        return f"{deger} dk"
    if ad in ("k", "geri_cekilme"):
        x = float(deger)
        return f"%{_sayi(100 * x, 1)}" if ad == "geri_cekilme" else f"{_sayi(x, 1)}{esik_birimi(aile)}"
    if isinstance(deger, float):
        return _sayi(deger, 3 if deger != round(deger, 1) else 1)
    return DEGER.get(str(deger), str(deger))


def param_yaz(ad: str, deger, aile: str = "") -> str:
    """"ad: değer". Değer birimini taşıyorsa ('k': "2,0σ") ad birimsiz yazılır ("eşik: 2,0σ")."""
    return f"{'eşik' if ad == 'k' else param_ad(ad, aile)}: {deger_yaz(ad, deger, aile)}"


def hepsi() -> dict:
    """Site verisine giden kopya (tablo bileşeni adları buradan okur)."""
    return {"birim": {k: {"ad": v[0], "kisa": v[1]} for k, v in BIRIM.items()}, "ders_birim": DERS_BIRIM,
            "param": PARAM, "deger": DEGER, "neden": {str(k): v for k, v in NEDEN.items()}, "olay": OLAY,
            "hukum": HUKUM, "kosul": KOSUL}


# ───────────────────────────────────────────── saat: yerel saatin TSİ karşılığı (ders metni ve figürler aynı tanım)
#: TSİ karşılığının üç saat rejimi, temsilci günlerle: iki şehir de yaz saatinde · ikisi de kış saatinde · ara
#: hafta (ABD yaz, İngiltere kış saatinde). Giriş dersinin saat tablosuyla aynı rejimler; yıl metinde geçmez.
TSI_REJIM = (("yazın", "2026-07-15"), ("kışın", "2026-01-15"), ("ara haftalarda", "2026-03-18"))
SEHIR_BOLGE = {"Londra": "Europe/London", "New York": "America/New_York", "Frankfurt": "Europe/Berlin",
               "Tokyo": "Asia/Tokyo"}
#: Saat değerli parametrelerin şehri (değer o şehrin yerel saatidir).
SAAT_SEHIR = {"son_giris_londra": "Londra", "aralik_sonu_londra": "Londra", "son_giris_et": "New York",
              "baslangic_et": "New York", "cikis_et": "New York"}


def tsi_an(gun: str, saat: str, bolge: str) -> datetime:
    y, a, d = (int(x) for x in gun[:10].split("-"))
    hh, mm = (int(x) for x in saat.split(":"))
    return datetime(y, a, d, hh, mm, tzinfo=ZoneInfo(bolge)).astimezone(ZoneInfo("Europe/Istanbul"))


def tsi_yaz(saatler, birlestir: str = "") -> str:
    """Yerel saatlerin TSİ karşılığı: ["Londra 08:00", "New York 14:00"], "→" → "TSİ yazın 10:00 → 21:00, kışın
    11:00 → 22:00, ara haftalarda 11:00 → 21:00". Her öğe "<şehir> SS:DD" ya da "<şehir> SS:DD–SS:DD"; aynı sonucu
    veren rejimler bir kez yazılır (yalnız Londra saati taşıyan bir öğede ara hafta kışla aynıdır). Okunamayan öğe
    ValueError."""
    import re
    cozum = []
    for s in saatler:
        m = re.fullmatch(r"(Londra|New York|Frankfurt|Tokyo) (\d{2}:\d{2})(?:–(\d{2}:\d{2}))?", s.strip())
        if not m:
            raise ValueError(f"tsi: okunamayan saat: {s!r}")
        cozum.append((SEHIR_BOLGE[m.group(1)], m.group(2), m.group(3)))
    if not cozum:
        raise ValueError("tsi: saat yok")
    sonuc: list[tuple[str, str]] = []
    for ad, gun in TSI_REJIM:
        parca = []
        for bolge, s1, s2 in cozum:
            x = f"{tsi_an(gun, s1, bolge):%H:%M}"
            if s2:
                x += f"–{tsi_an(gun, s2, bolge):%H:%M}"
            parca.append(x)
        metin = f" {birlestir} ".join(parca) if birlestir else parca[0]
        if all(metin != m_ for _, m_ in sonuc):
            sonuc.append((ad, metin))
    return "TSİ " + ", ".join(f"{ad} {m_}" for ad, m_ in sonuc)
