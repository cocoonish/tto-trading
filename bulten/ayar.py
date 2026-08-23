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
    "dibs-verim-egrisi": 6,     # iş günü (eğri günlük kurulur)
    "odemeler-dengesi": 45,     # aylık, 6-8 hafta gecikmeli
    "butce-borc": 45,           # aylık (bütçe ayın 15'i)
}

# Bültende grup başlıkları ve sırası
GRUPLAR = [
    ("kur", "Kur ve rezervler"),
    ("faiz", "Faiz, fonlama ve likidite"),
    ("enflasyon", "Enflasyon"),
    ("kredi", "Kredi ve para"),
    ("borclanma", "Hazine borçlanması ve borç stoku"),
    ("dis", "Dış denge ve finansman"),
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

    # ─────────────────────────────── DİBS verim eğrisi
    Izlem("dibs-verim-egrisi", "gosterge_ytm", "Gösterge tahvil bileşik getirisi", "%", 2,
          "delta", 0.75, 1.75, "azalis",
          "En likit DİBS'in vadeye kadar getirisi; TL faizinin manşet fiyatı.", "faiz"),
    Izlem("dibs-verim-egrisi", "spot_2y", "DİBS 2 yıllık spot getiri", "%", 2, "delta",
          0.75, 1.75, "azalis", "", "faiz"),
    Izlem("dibs-verim-egrisi", "spot_9y", "DİBS 9 yıllık spot getiri", "%", 2, "delta",
          0.75, 1.75, "azalis", "", "faiz"),
    Izlem("dibs-verim-egrisi", "egim_2y9y", "DİBS 2y−9y eğimi", "puan", 2, "delta",
          1.0, 2.5, "", "Negatif = ters eğri; işaret değiştirmesi rejim değişimidir.", "faiz"),
    Izlem("dibs-verim-egrisi", "carry_2y_tlref", "2 yıllık taşıma (TLREF, bileşik)", "puan", 2,
          "delta", 1.5, 3.0, "artis",
          "Tahvili gecelikten fonlamanın maliyeti; negatifse pozisyon taşımak pahalıdır.", "faiz"),
    Izlem("dibs-verim-egrisi", "basabas_2y", "2 yıllık başabaş enflasyon", "%", 2, "delta",
          1.0, 2.5, "azalis",
          "Nominal ile enflasyona endeksli tahvilin ima ettiği enflasyon.", "enflasyon"),
    Izlem("dibs-verim-egrisi", "reel_egri_2y", "2 yıllık reel getiri", "%", 2, "delta",
          1.0, 2.0, "", "", "faiz"),

    # ─────────────────────────────── ödemeler dengesi ve dış finansman
    Izlem("odemeler-dengesi", "cari12_mia", "Cari denge (12 aylık birikimli)", "mlr USD", 1,
          "delta", 3.0, 7.0, "artis", "", "dis"),
    Izlem("odemeler-dengesi", "cekirdek12_mia", "Çekirdek cari denge (altın ve enerji hariç)",
          "mlr USD", 1, "delta", 3.0, 7.0, "artis",
          "Dış dengenin yapısal kısmı; enerji ve altın dalgası dışarıda.", "dis"),
    Izlem("odemeler-dengesi", "nhn12_mia", "Net hata noksan (12 aylık)", "mlr USD", 1,
          "delta", 4.0, 9.0, "", "Büyümesi kaynağı belirsiz döviz girişine işaret eder.", "dis"),
    Izlem("odemeler-dengesi", "cari_gsyh", "Cari denge / GSYH", "%", 2, "delta", 0.5, 1.0,
          "artis", "", "dis"),

    # ─────────────────────────────── bütçe ve borç stoku
    Izlem("butce-borc", "denge_gsyh", "Bütçe dengesi / GSYH (12 aylık)", "%", 2, "delta",
          0.4, 0.8, "artis", "", "borclanma"),
    Izlem("butce-borc", "fdd_gsyh", "Faiz dışı denge / GSYH (12 aylık)", "%", 2, "delta",
          0.4, 0.8, "artis", "", "borclanma"),
    Izlem("butce-borc", "faiz_vergi", "Faiz harcaması / vergi geliri", "%", 1, "delta",
          1.5, 3.0, "azalis",
          "Borç servisinin vergi tabanını ne kadar yediğinin ölçüsü.", "borclanma"),
    Izlem("butce-borc", "doviz_pay", "Borç stokunda döviz payı", "%", 1, "delta", 1.5, 3.0,
          "azalis", "Kur şokuna duyarlılığın ölçüsü.", "borclanma"),
    Izlem("butce-borc", "yurt_disi_pay", "Borç stokunda yurt dışı yerleşik payı", "%", 1,
          "delta", 1.5, 3.0, "", "", "borclanma"),
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

# ABD Hazinesi basın duyuruları — borç yönetimi operasyonlarının BİRİNCİL kaynağı.
# Bu kaynak eksikken sistem 19 Ağustos 2026'daki geri alım (buyback) büyüklüğü
# artırımını tamamen kaçırdı; oysa o duyuru haftanın dolar ve uzun vadeli faiz
# hareketinin ana sebebiydi. Merkez bankası odaklı aramalar bunu YAKALAYAMAZ:
# geri alım, refinansman ve ihale takvimi para politikası değil BORÇ YÖNETİMİDİR.
ABD_HAZINE_URL = "https://home.treasury.gov/news-data/press-releases/search/{yil}.json"
# Piyasayı ilgilendiren duyuru başlıkları (geri kalan: yaptırım, vergi, atama…).
ABD_HAZINE_ILGILI = (r"buyback|refunding|auction|debt|borrowing|financing|bill|note|bond|"
                     r"yield|treasury international capital|tic data|cash balance|"
                     r"quarterly|issuance|maturit|liquidity")

TCMB_DUYURU_URL = "https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Duyurular/Basin/{yil}"

HABER_KAYNAKLARI = [
    # bolge: "tr" | "global" | "karisik"    alan: "makro" | "politika" | "piyasa" | "karisik"
    # Kaynağın alanı VARSAYILANDIR; başlık/özetteki kalıplar bunu ezebilir.
    #
    # Sıra bilinçli: önce DOĞRUDAN YAYINCI akışları. Onların açıklama alanı gerçek
    # bir özet taşıyor ve bağlantıları doğrudan habere gidiyor; Google News
    # bağlantıları ise yayıncıya JS ile yönlendirdiği için ne özet ne de gövde
    # okunabiliyor. Google aramaları yalnız yayıncı akışlarının kapsamadığı
    # konularda, boşluk doldurucu olarak kalır.

    # ── Türkiye
    {"ad": "Anadolu Ajansı — Ekonomi", "bolge": "tr", "alan": "makro",
     "url": "https://www.aa.com.tr/tr/rss/default?cat=ekonomi"},
    {"ad": "Anadolu Ajansı — Politika", "bolge": "tr", "alan": "politika",
     "url": "https://www.aa.com.tr/tr/rss/default?cat=politika"},
    {"ad": "Bloomberg HT", "bolge": "tr", "alan": "piyasa",
     "url": "https://www.bloomberght.com/rss"},
    {"ad": "Dünya Gazetesi", "bolge": "tr", "alan": "makro",
     "url": "https://www.dunya.com/rss?dunya"},
    {"ad": "Ekonomim", "bolge": "tr", "alan": "makro",
     "url": "https://www.ekonomim.com/rss"},
    {"ad": "Hürriyet Ekonomi", "bolge": "tr", "alan": "makro",
     "url": "https://www.hurriyet.com.tr/rss/ekonomi"},
    {"ad": "Investing", "bolge": "tr", "alan": "piyasa",
     "url": "https://tr.investing.com/rss/news_285.rss"},

    # ── Global
    {"ad": "BBC Business", "bolge": "global", "alan": "makro",
     "url": "https://feeds.bbci.co.uk/news/business/rss.xml"},
    {"ad": "BBC World", "bolge": "global", "alan": "politika",
     "url": "https://feeds.bbci.co.uk/news/world/rss.xml"},
    {"ad": "The Guardian — Business", "bolge": "global", "alan": "makro",
     "url": "https://www.theguardian.com/uk/business/rss"},
    {"ad": "Al Jazeera", "bolge": "global", "alan": "politika",
     "url": "https://www.aljazeera.com/xml/rss/all.xml"},
    {"ad": "CNBC — dünya ekonomisi", "bolge": "global", "alan": "makro",
     "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100727362"},
    {"ad": "CNBC — piyasalar", "bolge": "global", "alan": "piyasa",
     "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258"},
    {"ad": "CNBC — finans", "bolge": "global", "alan": "makro",
     "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664"},
    {"ad": "MarketWatch", "bolge": "global", "alan": "piyasa",
     "url": "https://feeds.content.dowjones.io/public/rss/mw_topstories"},
    {"ad": "Financial Times", "bolge": "global", "alan": "karisik",
     "url": "https://www.ft.com/rss/home"},
    {"ad": "OilPrice", "bolge": "global", "alan": "piyasa",
     "url": "https://oilprice.com/rss/main"},
    {"ad": "Euronews Türkçe", "bolge": "karisik", "alan": "karisik",
     "url": "https://tr.euronews.com/rss"},

    # ── Hedefli aramalar (boşluk doldurucu; özet taşımazlar)
    {"ad": "Arama — TCMB ve faiz", "bolge": "tr", "alan": "makro", "ozet_yok": True,
     "url": "https://news.google.com/rss/search?q=(TCMB+OR+%22Merkez+Bankas%C4%B1%22+OR+PPK+OR+enflasyon)+when:2d&hl=tr&gl=TR&ceid=TR:tr"},
    {"ad": "Arama — Türkiye ekonomi politikası", "bolge": "tr", "alan": "politika", "ozet_yok": True,
     "url": "https://news.google.com/rss/search?q=(%22ekonomi+program%C4%B1%22+OR+%22orta+vadeli+program%22+OR+%22maliye+politikas%C4%B1%22+OR+%22asgari+%C3%BCcret%22+OR+vergi+d%C3%BCzenleme)+when:2d&hl=tr&gl=TR&ceid=TR:tr"},
    {"ad": "Arama — Türkiye (yabancı basın)", "bolge": "tr", "alan": "karisik", "ozet_yok": True,
     "url": "https://news.google.com/rss/search?q=(%22Turkish+lira%22+OR+CBRT+OR+%22Turkey+economy%22+OR+%22Turkey+inflation%22)+when:2d&hl=en-US&gl=US&ceid=US:en"},
    {"ad": "Arama — ABD borç yönetimi ve tahvil arzı", "bolge": "global", "alan": "makro",
     "ozet_yok": True,
     "url": "https://news.google.com/rss/search?q=(%22Treasury+buyback%22+OR+%22quarterly+refunding%22+OR+%22Treasury+auction%22+OR+%22debt+ceiling%22+OR+%22bond+supply%22+OR+%22term+premium%22)+when:3d&hl=en-US&gl=US&ceid=US:en"},
    {"ad": "Arama — Fed ve ECB", "bolge": "global", "alan": "makro", "ozet_yok": True,
     "url": "https://news.google.com/rss/search?q=(%22Federal+Reserve%22+OR+ECB+OR+%22Bank+of+Japan%22)+(rates+OR+inflation+OR+policy)+when:1d&hl=en-US&gl=US&ceid=US:en"},
]

# ─────────────────────────── haber sınıflandırma
# Kaynağın varsayılan bölge/alanı yeterli değil: AA Dünya'da bir ABD enflasyon
# haberi çıkabilir, Bloomberg HT'de bir seçim haberi. Başlık + özet metni bu
# kalıplarla taranır ve varsayılan EZİLİR.
ALAN_KALIPLARI = {
    "politika": (r"se[çc]im|meclis|kabine|bakan\b|cumhurba[şs]kan|yasa|kanun|teklif|"
                 r"diploma|savaş|sava[şs]|ate[şs]kes|yaptırım|yaptırım|tarife|g[üu]mr[üu]k vergi|"
                 r"nato|avrupa birli[ğg]i|m[üu]zakere|zirve|anla[şs]ma|protesto|referandum|"
                 r"koalisyon|parlamento|sanction|tariff|election|parliament|summit|ceasefire|"
                 r"peace talk|trade war|geopolit"),
    "makro": (r"enflasyon|b[üu]y[üu]me|istihdam|i[şs]sizlik|cari a[çc]|b[üu]t[çc]e|faiz|"
              r"para politikas|resesyon|pmi|gsyh|t[üu]ketici g[üu]ven|sanayi [üu]retim|"
              r"inflation|growth|employment|unemployment|deficit|rate cut|rate hike|"
              r"monetary policy|recession|gdp|payroll"),
    "piyasa": (r"borsa|endeks|hisse|tahvil|getiri|kur\b|dolar|euro|alt[ıi]n|petrol|brent|"
               r"kripto|bitcoin|cds|bist|stocks|bond|yield|oil|gold|currency|equit"),
}
BOLGE_KALIPLARI = {
    "tr": r"t[üu]rkiye|tcmb|merkez bankas|lira|bist|istanbul|ankara|turkish|turkey",
    "global": (r"\bfed\b|federal reserve|ecb|avrupa merkez|[çc]in\b|china|abd\b|"
               r"amerika|washington|brussels|japonya|japan|almanya|germany|rusya|russia|"
               r"opec|imf|d[üu]nya bankas|world bank"),
}

# Bülten bölümleri: (id, başlık, bölge, alan) — sıra sayfadaki sıradır.
HABER_BOLUMLERI = [
    ("kilit", "Kilit gelişmeler", None, "kilit"),
    ("kurum", "Kurum duyuruları — Türkiye", None, "kurum"),
    ("kurum_global", "Kurum duyuruları — ABD Hazinesi ve borç yönetimi", None, "kurum_global"),
    ("tr_makro", "Türkiye — makro ve veri", "tr", "makro"),
    ("tr_politika", "Türkiye — politika ve düzenleme", "tr", "politika"),
    ("tr_piyasa", "Türkiye — piyasa", "tr", "piyasa"),
    ("global_makro", "Global — makro ve merkez bankaları", "global", "makro"),
    ("global_politika", "Global — jeopolitik ve ticaret", "global", "politika"),
    ("global_piyasa", "Global — piyasa ve emtia", "global", "piyasa"),
]
# ─────────────────────────── haber ÖNEM puanlaması
# Sorun: bülten haberleri bölümlere dağıtıyor ama hepsini eşit ağırlıkta gösteriyordu.
# ABD Hazinesi'nin geri alım büyüklüğünü ikiye katlaması ile "ECB başkanı WEF'e aday"
# haberi yan yana, aynı puntoda duruyordu. Haftanın ana sürücüsü bu yüzden gözden kaçtı.
#
# Puan üç kaynaktan gelir:
#   1. Konu ağırlığı — aşağıdaki kalıplar (piyasayı fiilen hareket ettiren olaylar).
#   2. Kaynak itibarı — KAYNAK_PUANI (0-10) beşte bir ağırlıkla.
#   3. Kümedeki kaynak sayısı — aynı öyküyü kaç yayın yazdı; yayılma önemin ölçüsüdür.
# Kurum duyurusu ayrıca sabit bonus alır: birincil kaynaktır, haber değil OLAYdır.
ONEM_KALIPLARI = [
    # (ağırlık, kalıp) — sıra önemsiz, en yüksek eşleşen ağırlık alınır
    (6, r"buyback|geri al[ıi]m|quarterly refunding|refinansman duyuru|debt ceiling|"
        r"bor[çc] tavan|m[üu]dahale|intervention|emergency|ola[ğg]an[üu]st[üu] toplant|"
        r"moratoryum|default|temerr[üu]t|devalu|peg|kur [çc]apas"),
    (5, r"faiz karar|rate decision|rate cut|rate hike|policy decision|ppk karar|"
        r"zorunlu kar[şs][ıi]l|makroihtiyati|sermaye kontrol|capital control|"
        r"not indirim|downgrade|not art[ıi]r|upgrade|kredi notu"),
    (4, r"tarife|tariff|yapt[ıi]r[ıi]m|sanction|ticaret sava|trade war|ambargo|"
        r"ihale|auction|tahvil ihrac|bond sale|issuance|arz|supply|"
        r"bilan[çc]o k[üu][çc]|quantitative|qt|qe|swap hatt|swap line"),
    (3, r"t[üu]fe|cpi|enflasyon veri|inflation data|tar[ıi]m d[ıi][şs][ıi] istihdam|"
        r"payroll|i[şs]sizlik|unemployment|gsyh|gdp|b[üu]y[üu]me veri|pmi|"
        r"tutanak|minutes|enflasyon raporu|projeksiyon|dot plot"),
    (2, r"opec|petrol|oil price|alt[ıi]n|gold|repo|likidite|liquidity|"
        r"cari a[çc]|b[üu]t[çc]e a[çc]|rezerv|reserve"),
]
# Bu puanın üstündeki maddeler "Kilit gelişmeler" bölümüne çıkar ve ayrıntılı işlenir.
KILIT_ESIK = 6.0
# Kilit bölümünde gösterilecek azami madde.
KILIT_SINIRI = 6

# Bölüm başına azami madde (kurum duyuruları sınırsız).
BOLUM_SINIRI = 10

# Haber listesi OLMAYAN, yalnız yazıdan ibaret gündem bölümleri. Bunlar piyasa
# tablolarını ve takvimi okuyup yorumlayan bölümlerdir; kural tabanlı koşu
# bunları boş bırakır, yorum katmanı doldurur.
GUNDEM_YAZI_BOLUMLERI = [
    ("faiz_fx_surucu", "Faiz ve döviz piyasasının sürücüleri"),
    ("emtia_surucu", "Emtia ve enerji: fiyat hareketinin sebebi"),
    ("risk_firsat", "Riskler ve fırsatlar"),
    ("beklenti", "Yaklaşan veriler: beklentiler ve ne izlenmeli"),
]

# ─────────────────────────── alaka ve gürültü süzgeçleri
# BAŞLIKTA bu terimlerden biri geçmelidir. Özette geçmesi yetmez: özet çoğu akışta
# haberin ilk cümlesidir ve "ekonomi" gibi bir kelime rastgele düşebilir; başlık ise
# haberin ne hakkında olduğunu söyler.
HABER_ILGILI = (r"enflasyon|t[üu]fe|[üu]fe\b|faiz|tcmb|merkez bankas|kur\b|dolar|euro\b|"
                r"rezerv|swap|tahvil|bono|hazine|ihale|bor[çc]lan|kredi|mevduat|bddk|spk|"
                r"imf\b|moody|fitch|s&p|cds\b|bist|borsa|fed\b|ecb\b|ppk|b[üu]t[çc]e|"
                r"cari a[çc]|[öo]demeler dengesi|istihdam|i[şs]sizlik|b[üu]y[üu]me|gsyh|"
                r"resesyon|durgunluk|lira\b|asgari [üu]cret|vergi d[üu]zenle|vergi paketi|"
                r"orta vadeli program|ekonomi program|petrol|brent|do[ğg]al gaz|alt[ıi]n fiyat|"
                r"ons alt[ıi]n|yapt[ıi]r[ıi]m|tarife|g[üu]mr[üu]k vergi|ticaret sava|ate[şs]kes|"
                r"se[çc]im|zirve|m[üu]zakere|"
                r"inflation|interest rate|rate cut|rate hike|central bank|monetary polic|"
                r"treasury|bond|yield|deficit|recession|payroll|unemployment|gdp\b|"
                r"tariff|sanction|trade war|ceasefire|opec|oil price|gold price|"
                r"currenc|devalu|default|downgrade|upgrade|imf\b")

# Bunlardan biri geçiyorsa alınmaz — alaka terimi de geçse.
HABER_GURULTU = r"emekli zamm|emekli maa|ev kadın|arazi sat|kiraya ver|burç|ma[çc] [öo]zeti|transfer bombas|hava durumu|piyango|çekili[şs]|indirim kampanya|astroloji|promosyon|convert [0-9]|bybit|binance|coin fiyat|how much is|gong .{0,20}çaldı|ya[şs] g[üu]n[üu]|falc|tur[şs]u|lezzet|festival|g[ıi]da denetim|taksit f[ıi]rsat|72 taksit|ka[çc] para|ne kadar oldu|^about .{0,90}reuters|quote page|stock quote|hisse [öo]nerisi|katlanabilir|iphone|nvidia earnings|burcunuz|ma[çc] sonucu|teknik direkt[öo]r|cricket|nightclub|premier lig|şampiyonlar ligi|futbol|basketbol|oyuncu kadrosu"

# Kaynak itibar sıralaması: aynı öyküyü birden çok yer yazdığında bülten hangisini
# gösterecek? Yüksek puanlı kaynak temsilci olur. Puanı olmayan kaynak 0 sayılır;
# içerik çiftlikleri ve toplayıcılar böylece kendiliğinden geri düşer.
KAYNAK_PUANI = {
    "reuters": 10, "financial times": 10, "ft.com": 10, "bloomberg": 9, "wall street journal": 9,
    "wsj": 9, "economist": 9, "cnbc": 8, "bbc": 8, "associated press": 8, "ap news": 8,
    "anadolu ajansı": 7, "aa.com.tr": 7, "bloomberg ht": 7, "dünya": 6, "dunya": 6,
    "investing": 5, "euronews": 5, "hürriyet": 4, "milliyet": 4, "sözcü": 4, "sozcu": 4,
    "cumhuriyet": 4, "t24": 4, "ekonomim": 4, "patronlardunyasi": 3, "borsagundem": 3,
}

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
