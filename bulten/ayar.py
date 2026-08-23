#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Günlük bülten — İZLEM ve EŞİK ayarları.

Bültenin "kayda değer" tanımı burada durur. Tek dosya, düz veri: eşikleri
değiştirmek için kod okumak gerekmez.

Her izlem bir hattın ozet.json'undaki BİR anahtarı izler. Karşılaştırma bir
önceki ANLIK GÖRÜNTÜYE göre yapılır (bulten/gecmis/<hat>.jsonl); yani "dün
neredeydi, bugün nerede".

Eşik iki kademeli:
  dikkat  → bültenin "not düşülenler" bölümüne girer
  onemli  → bültenin başındaki "öne çıkanlar" bölümüne girer

Eşikler bilinçli olarak GENİŞ tutulmuştur: her gün on madde üreten bir bülten
okunmaz. Bir eşik ayda birkaç kez tetikleniyorsa doğru yerdedir.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Izlem:
    hat: str                     # hangi hattın ozet.json'u (site slug'ı)
    anahtar: str
    ad: str                      # bültende görünecek Türkçe ad
    birim: str = ""
    ondalik: int = 1
    tip: str = "delta"           # delta | yuzde | akim | seviye | degisim
    dikkat: float | None = None
    onemli: float | None = None
    # seviye tipinde: eşik aşıldığında olay (mutlak değere bakılır)
    yon_iyi: str = ""            # "artis" | "azalis" | "" (nötr)
    aciklama: str = ""           # neden izliyoruz — bültende dipnot
    grup: str = ""               # bültende hangi başlık altında toplanacak


# Hatların yayım ritmi — "veri gecikti" uyarısı için. Gün cinsinden azami sessizlik.
RITIM = {
    "usdtry-deval": 4,          # günlük (hafta sonu boşluğu payı)
    "tcmb-net-rezerv": 10,      # haftalık (Perşembe)
    "yabanci-pozisyon": 11,     # haftalık (Cuma, 1 hafta gecikmeli)
    "fonlama-likidite": 6,      # günlük/haftalık karışık
    "kredi-parasal": 11,        # haftalık
    "enflasyon": 40,            # aylık (ayın 3'ü)
    "try-reer": 40,             # aylık
    "yiyecek-hizmetleri-marj": 45,
    "hazine-ihrac": 12,
    "fx-haber-endeksi": 9,
}

# Bültende grup başlıkları ve sırası
GRUPLAR = [
    ("kur", "Kur ve rezervler"),
    ("faiz", "Faiz, fonlama ve likidite"),
    ("enflasyon", "Enflasyon"),
    ("kredi", "Kredi ve para"),
    ("borclanma", "Hazine borçlanması"),
    ("akim", "Yabancı akımı"),
    ("diger", "Diğer"),
]

IZLEMLER: list[Izlem] = [
    # ─────────────────────────────── kur ve rezervler
    Izlem("usdtry-deval", "kur", "USD/TRY", "", 2, "yuzde", 0.6, 1.2, "",
          "Günlük yüzde değişim; %1,2 üstü TL varlıklarda gün içi fiyatlamayı değiştirir.", "kur"),
    Izlem("usdtry-deval", "d1a", "1 aylık yıllıklandırılmış devalüasyon hızı", "%", 1, "delta", 4, 8,
          "azalis", "Kurun seviyesi değil HIZI; TCMB'nin patika yönetimini bu gösterir.", "kur"),
    Izlem("usdtry-deval", "d3a", "3 aylık yıllıklandırılmış devalüasyon hızı", "%", 1, "delta", 3, 6,
          "azalis", "Daha yavaş ama daha güvenilir rejim göstergesi.", "kur"),
    Izlem("tcmb-net-rezerv", "h_net", "Net rezerv (haftalık, resmî)", "mlr USD", 1, "delta", 1.5, 3.0,
          "artis", "Analitik bilançodan piyasa tanımıyla; haftalık yayımlanır.", "kur"),
    Izlem("tcmb-net-rezerv", "h_swap_haric", "Swap hariç net rezerv", "mlr USD", 1, "delta", 1.5, 3.0,
          "artis", "Rezervin borçlanılmamış kısmı — kalite ölçüsü.", "kur"),
    Izlem("tcmb-net-rezerv", "h_brut", "Brüt rezerv", "mlr USD", 1, "delta", 2.5, 5.0, "artis", "", "kur"),
    Izlem("tcmb-net-rezerv", "g_net", "Net rezerv (günlük tahmin)", "mlr USD", 1, "delta", 2.0, 4.0,
          "artis", "Günlük analitik bilanço vekili; haftalık resmî seriden önce hareketi gösterir.", "kur"),
    Izlem("tcmb-net-rezerv", "p_altin", "Altın rezervi", "mlr USD", 1, "delta", 2.5, 5.0, "", "", "kur"),
    Izlem("try-reer", "redk", "TÜFE bazlı reel efektif kur", "endeks", 1, "delta", 2.0, 4.0, "",
          "Aylık; 100 üstü TL'nin uzun dönem ortalamasına göre değerli olduğunu gösterir.", "kur"),

    # ─────────────────────────────── faiz, fonlama, likidite
    Izlem("fonlama-likidite", "politika", "Politika faizi", "%", 2, "degisim", None, None, "",
          "Her değişim PPK kararıdır; koşulsuz olay.", "faiz"),
    Izlem("fonlama-likidite", "koridor_ust", "Koridor üst bandı (GLP)", "%", 2, "degisim", None, None, "", "", "faiz"),
    Izlem("fonlama-likidite", "koridor_alt", "Koridor alt bandı", "%", 2, "degisim", None, None, "", "", "faiz"),
    Izlem("fonlama-likidite", "tlref", "TLREF", "%", 2, "delta", 0.25, 0.75, "",
          "Gecelik gerçekleşen; politika faizinden sapması sıkılık göstergesi.", "faiz"),
    Izlem("fonlama-likidite", "aofm", "Ağırlıklı ortalama fonlama maliyeti", "%", 2, "delta", 0.25, 0.75, "", "", "faiz"),
    Izlem("fonlama-likidite", "spread_tlref_politika", "TLREF − politika farkı", "puan", 2, "seviye", 1.0, 2.0, "",
          "Farkın büyümesi TCMB'nin fiilî duruşunun ilan edilenden ayrıştığını söyler.", "faiz"),
    Izlem("fonlama-likidite", "net_fonlama_mlr", "TCMB net fonlaması", "mlr TL", 0, "delta", 150, 350, "",
          "Sistemin TCMB'ye net borcu; işaret değiştirmesi rejim değişimidir.", "faiz"),
    Izlem("fonlama-likidite", "swap_net_mlr_tl", "Net swap stoku", "mlr TL", 0, "delta", 100, 250, "", "", "faiz"),
    Izlem("fonlama-likidite", "zk_oran", "Ortalama zorunlu karşılık oranı", "%", 2, "delta", 0.3, 0.8, "",
          "Makroihtiyati sıkılaştırmanın sessiz kolu.", "faiz"),

    # ─────────────────────────────── enflasyon
    Izlem("enflasyon", "tufe_aylik", "Aylık TÜFE", "%", 2, "delta", 0.5, 1.0, "azalis",
          "Ayın 3'ünde gelir; bültende sürpriz olarak da ayrıca işlenir.", "enflasyon"),
    Izlem("enflasyon", "tufe_12a", "Yıllık TÜFE", "%", 2, "delta", 1.0, 2.5, "azalis", "", "enflasyon"),
    Izlem("enflasyon", "tufe_3a", "TÜFE 3 aylık yıllıklandırılmış (mevsimsellikten arındırılmış)", "%", 1,
          "delta", 3.0, 6.0, "azalis", "Panonun merkezî momentum ölçüsü.", "enflasyon"),
    Izlem("enflasyon", "tufe_3a_ham", "TÜFE 3 aylık yıllıklandırılmış (ham)", "%", 1, "delta", 3.0, 6.0,
          "azalis", "", "enflasyon"),
    Izlem("enflasyon", "b_12a", "Çekirdek B (yıllık)", "%", 2, "delta", 1.0, 2.5, "azalis", "", "enflasyon"),
    Izlem("enflasyon", "c_12a", "Çekirdek C (yıllık)", "%", 2, "delta", 1.0, 2.5, "azalis", "", "enflasyon"),
    Izlem("enflasyon", "hizmet_12a", "Hizmet enflasyonu (yıllık)", "%", 1, "delta", 1.0, 2.5, "azalis",
          "Ataleti en yüksek kalem; dezenflasyonun gerçek sınavı.", "enflasyon"),

    # ─────────────────────────────── kredi ve para
    Izlem("kredi-parasal", "g_ar_13y", "Kur etkisinden arındırılmış kredi büyümesi (13 haftalık yıllıklandırılmış)",
          "%", 1, "delta", 5.0, 10.0, "", "Makroihtiyati sınırların bağladığı asıl büyüklük.", "kredi"),
    Izlem("kredi-parasal", "g_tuketici_13y", "Tüketici kredisi büyümesi (13h yıllıklandırılmış)", "%", 1,
          "delta", 6.0, 12.0, "", "", "kredi"),
    Izlem("kredi-parasal", "g_ticari_13y", "Ticari kredi büyümesi (13h yıllıklandırılmış)", "%", 1,
          "delta", 6.0, 12.0, "", "", "kredi"),
    Izlem("kredi-parasal", "npl", "Takipteki alacak oranı", "%", 2, "delta", 0.15, 0.35, "azalis",
          "Yavaş hareket eder; sıçraması kredi döngüsünün dönüşüdür.", "kredi"),
    Izlem("kredi-parasal", "kredi_mevduat", "Kredi/mevduat oranı", "%", 1, "delta", 2.0, 4.0, "", "", "kredi"),

    # ─────────────────────────────── Hazine borçlanması
    Izlem("hazine-ihrac", "maliyet_son", "Son ihale ortalama bileşik maliyeti", "%", 2, "delta", 1.0, 2.5,
          "azalis", "Hazinenin fiilî borçlanma maliyeti.", "borclanma"),
    Izlem("hazine-ihrac", "b2c_son", "Son ihale teklif/karşılama oranı", "kat", 2, "delta", 0.4, 0.8, "artis",
          "Talebin gücü; 1,5'in altı zayıf ihale demektir.", "borclanma"),
    Izlem("hazine-ihrac", "n_ihale", "Toplam ihale sayısı", "adet", 0, "delta", 0.5, None, "",
          "Artması yeni ihale sonucu geldiği anlamına gelir.", "borclanma"),
    Izlem("hazine-ihrac", "wam_son", "Yeni ihraçların ağırlıklı ortalama vadesi", "yıl", 2, "delta", 0.5, 1.0,
          "artis", "", "borclanma"),

    # ─────────────────────────────── yabancı akımı
    Izlem("yabanci-pozisyon", "toplam_hafta", "Yabancı haftalık net akım (toplam)", "mn USD", 0, "akim",
          500, 1000, "artis", "Hisse + DİBS; stok değil AKIM (fiyat/kur etkisinden arındırılmış).", "akim"),
    Izlem("yabanci-pozisyon", "dibs_hafta", "Yabancı haftalık net akım (DİBS)", "mn USD", 0, "akim",
          400, 800, "artis", "", "akim"),
    Izlem("yabanci-pozisyon", "hisse_hafta", "Yabancı haftalık net akım (hisse)", "mn USD", 0, "akim",
          400, 800, "artis", "", "akim"),
]


# ─────────────────────────────── haber kaynakları
# İki tür kaynak var ve bültende AYRI durur:
#   kurum  → TCMB/Resmî Gazete duyuruları. Bunlar haber değil OLAY'dır; hepsi gösterilir.
#   haber  → RSS akışları. Gürültülü; alaka süzgecinden geçer ve sayısı sınırlanır.
#
# TCMB duyuru listesi RSS vermiyor ama liste sayfası düz HTTP ile okunabiliyor
# (haber.tcmb_duyurulari). Faiz kararı, makroihtiyati çerçeve, TL likidite yönetimi,
# swap düzenlemesi — hepsi oradan çıkar; bu kullanıcı için en değerli tek kaynak.
RESMI_GAZETE_URL = "https://www.resmigazete.gov.tr/"
# Kurum ve konu süzgeci: Resmî Gazete günde onlarca kalem yayımlar; bültene yalnız
# finans/makro ilgisi olanlar girer.
RG_ILGILI = (r"merkez bankas|tcmb|bddk|spk|hazine|maliye|vergi|kur\b|d[öo]viz|kredi|"
             r"banka|sermaye piyasas|zorunlu kar[şs][ıi]l|faiz|tahvil|bono|kambiyo|"
             r"finansal kiralama|sigortac|emeklilik|ihracat|ithalat|g[üu]mr[üu]k|te[şs]vik")

TCMB_DUYURU_URL = "https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Duyurular/Basin/{yil}"

HABER_KAYNAKLARI = [
    {"ad": "Bloomberg HT", "url": "https://www.bloomberght.com/rss",
     "etiket": "tr-piyasa", "yuksek_oncelik": False},
    {"ad": "AA Ekonomi", "url": "https://www.aa.com.tr/tr/rss/default?cat=ekonomi",
     "etiket": "tr-makro", "yuksek_oncelik": False},
    {"ad": "Investing TR", "url": "https://tr.investing.com/rss/news_285.rss",
     "etiket": "tr-piyasa", "yuksek_oncelik": False},
    {"ad": "Google News — TCMB/faiz", "etiket": "tr-makro", "yuksek_oncelik": False,
     "url": "https://news.google.com/rss/search?q=(TCMB+OR+%22Merkez+Bankas%C4%B1%22+OR+PPK)+when:2d&hl=tr&gl=TR&ceid=TR:tr"},
    {"ad": "Google News — Türkiye piyasalar (yabancı basın)", "etiket": "yabanci-basin",
     "yuksek_oncelik": False,
     "url": "https://news.google.com/rss/search?q=(%22Turkish+lira%22+OR+CBRT+OR+%22Turkey+bonds%22+OR+%22Turkey+inflation%22)+when:2d&hl=en-US&gl=US&ceid=US:en"},
    {"ad": "Google News — Fed/ECB", "etiket": "global", "yuksek_oncelik": False,
     "url": "https://news.google.com/rss/search?q=(%22Federal+Reserve%22+OR+ECB)+(rates+OR+inflation)+when:1d&hl=en-US&gl=US&ceid=US:en"},
]

# Alaka süzgeci: başlıkta bunlardan biri geçmiyorsa haber alınmaz.
HABER_ILGILI = (r"enflasyon|t[üu]fe|[üu]fe|faiz|tcmb|merkez bankas|kur\b|dolar|euro|rezerv|swap|"
                r"tahvil|bono|hazine|ihale|bor[çc]lan|kredi|mevduat|bddk|spk|imf|moody|fitch|"
                r"s&p|cds|bist|borsa|fed\b|ecb|ppk|b[üu]t[çc]e|cari a[çc]|[öo]demeler dengesi|"
                r"istihdam|b[üu]y[üu]me|gsyh|lira|inflation|rate|bond|yield|central bank|"
                r"treasury|deficit|reserve")
# Gürültü süzgeci: bunlardan biri geçiyorsa alınmaz (alaka kelimesi olsa bile).
HABER_GURULTU = (r"emekli zamm|emekli maa|ev kadın|arazi|kiraya|burç|ma[çc] [öo]zeti|"
                 r"transfer|hava durumu|piyango|çekili[şs]|indirim kampanya|ya[şs] g[üu]n|"
                 r"astroloji|promosyon|kredi kartı borcu yapılandır|convert \d|bybit|"
                 r"binance|coin fiyat|how much is|gong .{0,20}çaldı|ödeme yaptı")

# Bültende gösterilecek azami haber sayısı (kurum duyuruları bu sınırın dışında).
HABER_SINIRI = 12


# ─────────────────────────── ekonomik takvim: önem filtresi
# TÜİK "Ulusal Veri Yayımlama Takvimi" günde onlarca kayıt içerir (günlük SPK fon
# istatistiği, EFT işlem hacmi…). Bülten hepsini yazsa okunmaz. Aşağıdaki kalıplar
# NELERİN bültene gireceğini belirler; eşleşmeyen kayıt DÜŞER.
#   onem 1 = kritik (bültenin başında, saatiyle)
#   onem 2 = önemli (takvim tablosunda)
#   onem 3 = takip (yalnız haftalık genişletilmiş görünümde)
# Kalıplar büyük/küçük harf duyarsız düzenli ifadelerdir; sıra önemlidir (ilk eşleşen kazanır).
TAKVIM_KURALLARI: list[tuple[str, int, str]] = [
    (r"Tüketici Fiyat Endeksi", 1, "TÜFE"),
    (r"Yurt İçi Üretici Fiyat", 1, "Yİ-ÜFE"),
    (r"Ödemeler Dengesi", 1, "Ödemeler dengesi"),
    (r"Merkezi Yönetim Bütçe", 1, "Bütçe dengesi"),
    (r"Gayrisafi Yurt İçi Hasıla", 1, "GSYH"),
    (r"İşgücü İstatistikleri", 1, "İşgücü"),
    (r"Uluslararası Rezervler ve Döviz Likiditesi", 1, "IRFCL rezerv"),
    (r"Haftalık Para ve Banka", 2, "Haftalık para-banka"),
    (r"Menkul Kıymet İstatistikleri", 2, "Menkul kıymet ist."),
    (r"Sanayi Üretim", 2, "Sanayi üretimi"),
    (r"Dış Ticaret", 2, "Dış ticaret"),
    (r"Kapasite Kullanım", 2, "Kapasite kullanımı"),
    (r"Reel Kesim Güven|İktisadi Yönelim", 2, "Reel kesim güveni"),
    (r"Tüketici Güven", 2, "Tüketici güveni"),
    (r"Merkezi Yönetim Borç", 2, "Borç stoku"),
    (r"Konut Satış", 3, "Konut satışları"),
    (r"Hizmet.*Güven|Perakende.*Güven", 3, "Sektörel güven"),
    (r"Finansal Hizmetler", 3, "Finansal hizmetler"),
    (r"Bankacılık Sektörü", 3, "BDDK bankacılık"),
    (r"Tarım Ürünleri Üretici", 3, "Tarım ÜFE"),
    (r"Yurt Dışı Üretici Fiyat", 3, "YD-ÜFE"),
    (r"Ciro Endeks", 3, "Ciro endeksleri"),
    (r"Perakende Satış", 3, "Perakende satış"),
]

# Bültenin takvim bölümünde gösterilecek asgari önem (3 = hepsi).
TAKVIM_ASGARI_ONEM = 2
# Haftalık genişletilmiş görünümde (Pazartesi bülteni) asgari önem.
TAKVIM_HAFTALIK_ASGARI_ONEM = 3
# Takvim ufku (gün).
TAKVIM_UFKU = 21
