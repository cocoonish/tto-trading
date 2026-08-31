# main.py
"""
Türkiye Hazinesi İhale Verileri Scraper ve Analiz Aracı
------------------------------------------------------
Bu script, hazineihrac.ipynb içeriğinden modüler ve parametrik olarak dönüştürülmüştür.
Kullanıcı dostu, kolay değiştirilebilir ve geliştirilebilir bir yapı sunar.

Performans İyileştirmeleri:
- Selenium YERİNE WordPress REST API (/portal/v2/posts) ile doğrudan veri çekme
  (tarayıcı/ChromeDriver gerekmez, ~10-50x daha hızlı ve daha kararlı)
- aiohttp ile gerçek paralel (eşzamanlı) PDF indirme
- ThreadPoolExecutor ile paralel PDF parse
- İnkremental tarama + URL cache mekanizması
"""

# =====================
# GEREKLİ KÜTÜPHANELER (tüm import'lar en üstte)
# =====================
import json
import html
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import os
from urllib.parse import urljoin
import PyPDF2
import io
from typing import List, Dict, Optional, Tuple
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio
import aiohttp

import plotly.graph_objects as go
from plotly.subplots import make_subplots


# =====================
# PARAMETRELER (KOLAY DEĞİŞTİRİLEBİLİR)
# =====================
MAX_PAGES = 200                     # Taranacak maksimum API sayfa sayısı (üst sınır)
ANALYZE_STRATEGY = True             # İç Borçlanma Stratejisi analizi yapılsın mı?
EXCEL_OUTPUT = "hazine_ihale_verileri.xlsx"
CSV_OUTPUT = "hazine_ihale_verileri.csv"
COMPARISON_CSV = "hazine_hedef_gerceklesme.csv"
WADE_CSV = "hazine_vade_analizi.csv"
HTML_OUTPUT = "vade_analizi.html"
FORCE_ALL_FETCH = False             # True ise, tüm veriler zorla çekilir (break yapılmaz)
HEDEF_GERCEKLESME_HTML = "hedef_gerceklesme.html"
PLANNED_CSV = "hazine_planlanan_ihaleler.csv"   # Önümüzdeki planlı ihraçlar + tahminler
PLANNED_CALENDAR_CACHE = ".planned_calendar.json"  # Strateji takvimi cache (tekrar indirmemek için)
BACKTEST_CSV = "hazine_tahmin_dogrulama.csv"    # Geçmiş ihalelerde tahmin vs gerçek (backtest)
MAX_RETRIES = 3                     # API/PDF isteği başarısız olursa maksimum deneme

# Performans parametreleri
MAX_WORKERS = 8                     # Paralel PDF indirme/parse için maksimum eşzamanlılık
API_PER_PAGE = 20                   # API'den sayfa başına çekilecek duyuru sayısı
HTTP_TIMEOUT = 30                   # API istekleri için timeout (saniye)
PDF_TIMEOUT = 120                   # PDF indirme timeout (saniye)
USE_ASYNC = True                    # Async (paralel) PDF indirme kullan (daha hızlı)

# Strateji PDF taraması (ihale erken-durmasından BAĞIMSIZ).
# İhale sonuçları için erken durma doğrudur (yeni ihale yoksa geriye gitmenin
# anlamı yok), fakat aynı break strateji PDF'i toplamayı da kesiyordu; bu yüzden
# revizyon tarihçesi yalnızca son birkaç aydan başlıyordu. Strateji taraması
# artık kendi (sınırlı) bütçesiyle devam eder.
STRATEGY_SCAN_MAX_PAGES = 90        # Strateji taramasının gidebileceği azami sayfa
STRATEGY_HISTORY_START = "2019-12"  # Bu aydan eski duyurulara inildiğinde dur
                                    # (ihale verisi Şubat 2020'de başlıyor; daha
                                    #  eski strateji raporları .docx, PDF değil)
STRATEGY_STALE_PAGE_THRESHOLD = 3   # Ardışık bu kadar sayfada yeni strateji PDF'i
                                    # yoksa taramayı bitir (sıcak cache'te hızlı çıkış)

# Strateji hedefi makullik kontrolü
STRATEGY_PARSER_VERSION = 2         # Sayı ayrıştırıcı sürümü — eski sürümle üretilmiş
                                    # cache kayıtları yüklenirken atılır ve yeniden çekilir
STRATEGY_TARGET_MIN = 0.5           # Aylık hedef alt sınırı (milyar TL)
STRATEGY_TARGET_MAX = 5000.0        # Aylık hedef üst sınırı (milyar TL)
STRATEGY_REVISION_MAX_RATIO = 4.0   # Aynı ay için raporlar arası azami revizyon katsayısı
# CSV'den geri tohumlama filtresi: gerçekleşme oranı bu bandın dışındaysa
# tarihsel hedef bozuk kabul edilir (2020-21 biçim hatasında oranlar %2,7–%9,0'a
# düşmüştü; gerçek verideki en düşük makul oran %31,5, en yüksek %223,2).
SEED_MIN_REALIZATION_PCT = 15.0
SEED_MAX_REALIZATION_PCT = 500.0


# =====================
# LOGGING AYARLARI
# =====================
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def normalize_month_name(month: str) -> str:
    """
    Türkçe ay isimlerini normalize eder (çeşitli yazım/harf varyasyonlarını düzeltir)
    """
    mapping = {
        "Ocak": "Ocak", "Subat": "Şubat", "Şubat": "Şubat", "Mart": "Mart", "Nisan": "Nisan",
        "Mayis": "Mayıs", "Mayıs": "Mayıs", "Haziran": "Haziran", "Temmuz": "Temmuz",
        "Agustos": "Ağustos", "Ağustos": "Ağustos", "Eylul": "Eylül", "Eylül": "Eylül",
        "Ekim": "Ekim", "Kasim": "Kasım", "Kasım": "Kasım", "Aralik": "Aralık", "Aralık": "Aralık"
    }
    
    def fold_tr(s: str) -> str:
        """Türkçe karakterleri ASCII'ye dönüştür"""
        s = str(s).replace("İ", "i").replace("ı", "i").replace("\u0307", "")
        return (s.strip().lower()
                .replace("ı", "i").replace("ş", "s").replace("ğ", "g")
                .replace("ü", "u").replace("ö", "o").replace("ç", "c"))
    
    m_fold = fold_tr(str(month))
    for k, v in mapping.items():
        if m_fold.startswith(fold_tr(k)[:3]):
            return v
    
    # Uymadıysa baş harfi büyük geri dön
    try:
        return str(month).strip().title()
    except Exception:
        return str(month)


MONTH_ORDER = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
               "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]


def generate_quarter_months(first_month_raw: str, last_month_raw: str) -> List[str]:
    """
    Çeyreklik strateji dökümanındaki ilk ve son ay isimlerinden
    aradaki tüm ayları üretir.
    Örn: ("Ocak", "Mart") -> ["Ocak", "Şubat", "Mart"]
         ("Kasım", "Ocak") -> ["Kasım", "Aralık", "Ocak"]
    """
    first_norm = normalize_month_name(first_month_raw)
    last_norm = normalize_month_name(last_month_raw)
    try:
        start_idx = MONTH_ORDER.index(first_norm)
        end_idx = MONTH_ORDER.index(last_norm)
        if end_idx < start_idx:
            end_idx += 12
        return [MONTH_ORDER[i % 12] for i in range(start_idx, end_idx + 1)]
    except ValueError as e:
        logger.warning(f"Ay sırası oluşturulamadı ({first_month_raw}-{last_month_raw}): {e}")
        return [first_norm]


# =====================
# BİÇİM-DUYARLI SAYI AYRIŞTIRMA (strateji PDF'leri)
# =====================
# HMB strateji PDF'lerinin bir bölümü Türkçe biçim ("256,8"), bir bölümü ise
# nokta ondalıklı biçim ("24.4") kullanıyor. Koşulsuz
# `float(v.replace('.', '').replace(',', '.'))` ikinci grupta değeri 10 KAT
# şişiriyordu (24.4 -> 244). Hata sessizdi: toplam satırı çapraz kontrolü de aynı
# ölçek kaymasını yaşadığı için oran tutuyor ve uyarı üretmiyordu.
# Çözüm: sayı sözcüğünü tek başına değil, bulunduğu tablo bağlamıyla birlikte
# değerlendirip ondalık ayracını bir kez tespit etmek.

# "24.4", "256,8", "1.234,5", "1,234.5" — en az bir ayraç içeren sayı sözcüğü
NUMBER_TOKEN_RE = re.compile(r"\d+(?:[.,]\d+)+")


def detect_decimal_separator(text: str) -> str:
    """Metin bloğundaki sayıların ondalık ayracını ('.' veya ',') tespit eder.

    Kural sırası:
      1) Bloktaki herhangi bir sayıda virgül varsa -> ondalık ',' (nokta binlik).
         Türkçe belgede virgül daima ondalıktır; "1.234,5" bu dalda çözülür.
      2) Yalnızca nokta varsa ve TÜM nokta gruplarının uzunluğu tam 3 ise ->
         nokta binlik ayracıdır ("1.234 5.678"), ondalık kısım yoktur.
      3) Aksi halde -> ondalık '.' ("24.4 37.7 30.0").
    """
    tokens = NUMBER_TOKEN_RE.findall(text)
    if not tokens:
        return ","                       # varsayılan: Türkçe biçim
    if any("," in t for t in tokens):
        return ","
    # Sadece nokta var: son grubun uzunluğu ayracın rolünü belli eder
    son_gruplar = [t.split(".")[-1] for t in tokens]
    if all(len(g) == 3 for g in son_gruplar):
        return ","                       # nokta = binlik ayracı, ondalık yok
    return "."


def parse_localized_number(token: str, decimal_sep: str) -> float:
    """Tespit edilen ayraçla sayı sözcüğünü float'a çevirir (binliği atar)."""
    thousands_sep = "." if decimal_sep == "," else ","
    return float(token.replace(thousands_sep, "").replace(decimal_sep, "."))


# =====================
# PLANLI İHRAÇ TAKVİMİ AYRIŞTIRMA (Strateji PDF'i içindeki ihraç takvimi)
# =====================
# Strateji raporlarındaki ihraç takvimi satır biçimi:
#   <İhaleTarihi> <ValörTarihi> <İtfaTarihi> <Senet Tanımı> <Vade terimi> <Yöntem>
# Örn: "7.07.2026 8.07.2026 16.04.2031 Sabit Kuponlu Devlet Tahvili 5Yıl /1743 Gün İhale / Yeniden ihraç"
ISSUANCE_ROW_RE = re.compile(
    r'(\d{1,2}\.\d{1,2}\.\d{4})\s+(\d{1,2}\.\d{1,2}\.\d{4})\s+(\d{1,2}\.\d{1,2}\.\d{4})\s+'
    r'(.+?)\s+(\d+\s*(?:Yıl|Ay)\s*/\s*[\d.]+\s*Gün)\s+'
    r'(İhale\s*/\s*(?:Yeniden|İlk)\s*ihra[cç]|Doğrudan\s*Satış)',
    re.IGNORECASE
)


def _normalize_date_str(d: str) -> str:
    """'7.07.2026' -> '07.07.2026' (gün/ay iki haneli)."""
    try:
        p = d.split('.')
        return f"{int(p[0]):02d}.{int(p[1]):02d}.{p[2]}"
    except Exception:
        return d


def parse_issuance_calendar(full_text: str) -> List[Dict]:
    """Strateji PDF metninden ihraç takvimini (planlı ihraçlar) ayrıştırır.

    Returns: her biri {ihale_tarihi, valor_tarihi, itfa_tarihi, senet_tanimi,
    vade_terimi, yontem} olan satır listesi. Mükerrer satırlar atılır.
    """
    rows = []
    seen = set()
    for m in ISSUANCE_ROW_RE.finditer(full_text):
        ihale = _normalize_date_str(m.group(1).strip())
        valor = _normalize_date_str(m.group(2).strip())
        itfa = _normalize_date_str(m.group(3).strip())
        senet = re.sub(r'\s+', ' ', m.group(4).strip())
        terim = re.sub(r'\s+', ' ', m.group(5).strip())
        yontem = re.sub(r'\s+', ' ', m.group(6).strip())
        key = (ihale, itfa, senet)
        if key in seen:
            continue
        seen.add(key)
        rows.append({
            'ihale_tarihi': ihale,
            'valor_tarihi': valor,
            'itfa_tarihi': itfa,
            'senet_tanimi': senet,
            'vade_terimi': terim,
            'yontem': yontem,
        })
    return rows


# =====================
# ASYNC PDF İNDİRME (PERFORMANS İÇİN)
# =====================
async def download_pdf_async(session: aiohttp.ClientSession, url: str) -> Optional[bytes]:
    """
    PDF'i async olarak indirir - daha hızlı paralel indirme için
    """
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=PDF_TIMEOUT)) as response:
            if response.status == 200:
                return await response.read()
            else:
                logger.warning(f"PDF indirme hatası: {url} - Status: {response.status}")
                return None
    except Exception as e:
        logger.error(f"Async PDF indirme hatası: {url} - {str(e)}")
        return None


async def download_multiple_pdfs_async(urls: List[str], concurrency: int = MAX_WORKERS) -> Dict[str, bytes]:
    """
    Birden fazla PDF'i GERÇEKTEN eşzamanlı (paralel) olarak indirir.

    NOT: Önceki sürüm coroutine'leri tek tek await ettiği için aslında sıralı
    çalışıyordu. Burada asyncio.gather + Semaphore ile gerçek paralellik sağlanır;
    Semaphore sunucuyu aşırı yüklememek için eşzamanlı bağlantı sayısını sınırlar.
    """
    results: Dict[str, bytes] = {}
    sem = asyncio.Semaphore(concurrency)

    async with aiohttp.ClientSession(
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    ) as session:
        async def _fetch(url: str):
            async with sem:
                content = await download_pdf_async(session, url)
            if content:
                results[url] = content

        await asyncio.gather(*(_fetch(url) for url in urls))

    return results


# =====================
# SCRAPER SINIFI
# =====================
class TreasuryAuctionScraper:
    """
    Türkiye Hazinesi ihale sonuçlarını çeken ve analiz eden ana sınıf
    """
    
    def __init__(self, max_pages: int = 50, analyze_strategy: bool = True):
        """
        Args:
            max_pages: Taranacak maksimum API sayfa sayısı (üst sınır)
            analyze_strategy: İç Borçlanma Stratejisi analizi yapılsın mı
        """
        self.base_url = "https://www.hmb.gov.tr"
        # WordPress REST API uç noktası — React arayüzünün veri kaynağı.
        # Duyuru başlığı, tarihi ve PDF linki doğrudan JSON içinde gelir;
        # tarayıcı (Selenium/ChromeDriver) gerektirmez.
        self.api_url = "https://www.hmb.gov.tr/portal/v2/posts"
        self.category_slug = "kamu-finansmani"
        self.max_pages = max_pages
        self.analyze_strategy = analyze_strategy
        # En güncel strateji raporunun PDF URL'si (ihraç takvimi/tahmin için)
        self.newest_strategy_url = None

        # HTTP Session (connection pooling için)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        # İşlenmiş URL cache (inkremental tarama için)
        self.url_cache_file = ".processed_urls.json"
        self.processed_urls = self._load_url_cache()

        # Strateji tarihsel cache (çeyrekler arası birikim)
        self.strategy_cache_file = ".strategy_history.json"
        self.strategy_history = self._load_strategy_history()
        
        # Çekilecek alanlar
        self.fields = [
            'ISIN', 'Senet Tanımı', 'İhale Tarihi', 'Valör Tarihi', 'İtfa Tarihi', 'Vade (Yıl)',
            'ROT Toplam(Teklif)', 'ROT Toplam(Gerçekleşme)',
            'ROT Kamu(Teklif)', 'ROT Kamu(Gerçekleşme)',
            'ROT Piyasa Yapıcılar(Teklif)', 'ROT Piyasa Yapıcılar(Gerçekleşme)',
            'ROT Piyasa Yapıcılar Kabul Oranı (%)',
            'İhale(Teklif)', 'İhale(Gerçekleşme)',
            'İhale Kabul Oranı (%)',
            'Toplam(Teklif)', 'Toplam(Gerçekleşme)',
            'Ortalama Yıllık Basit(Teklif)', 'Ortalama Yıllık Basit(Gerçekleşme)',
            'Ortalama Yıllık Bileşik(Teklif)', 'Ortalama Yıllık Bileşik(Gerçekleşme)',
            'En Düşük Yıllık Bileşik(Teklif)', 'En Düşük Yıllık Bileşik(Gerçekleşme)',
            'En Yüksek Yıllık Bileşik(Teklif)', 'En Yüksek Yıllık Bileşik(Gerçekleşme)',
            'Ortalama Fiyat(Teklif)', 'Ortalama Fiyat(Gerçekleşme)',
            'En Düşük Fiyat(Teklif)', 'En Düşük Fiyat(Gerçekleşme)',
            'En Yüksek Fiyat(Teklif)', 'En Yüksek Fiyat(Gerçekleşme)'
        ]
        
        # İngilizce-Türkçe ay mapping'i
        self.en_to_tr_months = {
            'January': 'Ocak', 'February': 'Şubat', 'March': 'Mart', 'April': 'Nisan',
            'May': 'Mayıs', 'June': 'Haziran', 'July': 'Temmuz', 'August': 'Ağustos',
            'September': 'Eylül', 'October': 'Ekim', 'November': 'Kasım', 'December': 'Aralık'
        }

    @staticmethod
    def _is_junk_cache_url(url: str) -> bool:
        """URL cache'ine sızmış çöp kayıtları tanır.

        Kaynak: WordPress'te çöp kutusuna atılan duyurular hâlâ API'de
        görünebiliyor ve slug'ları "__trashed" ekiyle geliyor
        (ör. .../duyuru/__trashed-2__trashed). Bu kayıtlar gerçek bir duyuruya
        karşılık gelmez; cache'te durup her çalıştırmada taşınırlar.
        """
        u = str(url).strip()
        if not u.startswith("http"):
            return True
        if "__trashed" in u:
            return True
        if u.rstrip("/").endswith("/duyuru"):          # slug'ı boş kalmış kayıt
            return True
        return False

    def _load_url_cache(self) -> set:
        """İşlenmiş URL'leri cache dosyasından yükler (çöp kayıtları ayıklayarak)"""
        try:
            if os.path.exists(self.url_cache_file):
                with open(self.url_cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    temiz = {u for u in data if not self._is_junk_cache_url(u)}
                    atilan = len(set(data)) - len(temiz)
                    if atilan:
                        logger.warning(f"URL cache'inden {atilan} çöp kayıt temizlendi: "
                                       f"{sorted(set(data) - temiz)}")
                    logger.info(f"URL cache'den {len(temiz)} URL yüklendi")
                    return temiz
        except Exception as e:
            logger.warning(f"URL cache okunamadı: {e}")
        return set()

    def _save_url_cache(self):
        """İşlenmiş URL'leri cache dosyasına kaydeder.

        set sıralaması çalıştırmalar arası değiştiğinden, gereksiz diff/churn
        oluşmaması için sıralı (deterministik) yazılır.
        """
        try:
            with open(self.url_cache_file, 'w', encoding='utf-8') as f:
                json.dump(sorted(self.processed_urls), f, ensure_ascii=False, indent=2)
            logger.info(f"URL cache'e {len(self.processed_urls)} URL kaydedildi")
        except Exception as e:
            logger.warning(f"URL cache kaydedilemedi: {e}")

    def _load_strategy_history(self) -> dict:
        """Strateji tarihsel verisini cache'den yükler.
        Format: {"Ocak 2026": {"target": 327.7, "source": "...", "parser": 2, "history": [...]}, ...}
        Her ay için tüm strateji raporlarındaki hedefler history listesinde saklanır.

        `parser` alanı, kaydı üreten sayı ayrıştırıcısının sürümüdür. Sürüm eskiyse
        kayıt DÜŞÜRÜLÜR ve ilgili strateji PDF'i URL cache'inden çıkarılır; böylece
        biçim hatasıyla üretilmiş tarihsel değerler kendini yeniden üretemez.
        (`_meta` gibi ay-dışı bir anahtar EKLEMİYORUZ: web_cikti_tahmin.py bu
        dosyanın tüm anahtarlarını "Ay Yıl" olarak sıralıyor.)
        """
        try:
            if os.path.exists(self.strategy_cache_file):
                with open(self.strategy_cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Eski format migration: history alanı yoksa ekle
                    for month_key, info in data.items():
                        if isinstance(info, dict) and "history" not in info:
                            info["history"] = [{"target": info.get("target", 0), "source": info.get("source", "")}]
                        elif not isinstance(info, dict):
                            data[month_key] = {"target": float(info), "source": "", "history": [{"target": float(info), "source": ""}]}

                    # Ayrıştırıcı sürümü eski olan kayıtları at.
                    # Sürüm okuması KAYIT BAZINDA korunur: tek bir bozuk kayıt
                    # (parser: null, beklenmedik tip) dıştaki geniş except'e
                    # düşerse 80+ aylık geçmişin TAMAMI sessizce kaybolurdu.
                    def _surum(v):
                        try:
                            return int(v.get("parser", 1))
                        except (AttributeError, TypeError, ValueError):
                            return 0  # okunamayan sürüm = en eski, düşürülür
                    eski = [k for k, v in data.items()
                            if _surum(v) < STRATEGY_PARSER_VERSION]
                    if eski:
                        logger.warning(
                            f"Strateji cache: {len(eski)} ay eski ayrıştırıcı sürümüyle "
                            f"üretilmiş (v<{STRATEGY_PARSER_VERSION}), düşürülüyor: {sorted(eski)}"
                        )
                        for k in eski:
                            data.pop(k, None)
                        self._invalidate_strategy_urls()
                    logger.info(f"Strateji cache'den {len(data)} ay yüklendi")
                    return data
        except Exception as e:
            logger.warning(f"Strateji cache okunamadı: {e}")
        return {}

    def _invalidate_strategy_urls(self):
        """Strateji PDF URL'lerini işlenmiş-cache'inden düşürür.

        Ayrıştırıcı sürümü değiştiğinde strateji PDF'lerinin YENİDEN indirilip
        yeniden ayrıştırılması gerekir; aksi halde `processed_urls` onları
        atlar ve düzeltilmiş ayrıştırıcı hiç çalışmaz.
        """
        # Not: eski dosya adlarında Türkçe karakter var
        # ("...İç-Borçlanma-Stratejisi.pdf"), bu yüzden diyakritiksiz ortak
        # parça olan "stratejisi" üzerinden eşleşiyoruz.
        strateji_urls = {u for u in self.processed_urls
                         if "stratejisi" in str(u).lower()}
        if strateji_urls:
            self.processed_urls -= strateji_urls
            logger.warning(f"{len(strateji_urls)} strateji PDF URL'si cache'den düşürüldü "
                           f"(yeniden ayrıştırılacak)")

    def _save_strategy_history(self):
        """Strateji tarihsel verisini cache'e kaydeder"""
        try:
            with open(self.strategy_cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.strategy_history, f, ensure_ascii=False, indent=2)
            logger.info(f"Strateji cache'e {len(self.strategy_history)} ay kaydedildi")
        except Exception as e:
            logger.warning(f"Strateji cache kaydedilemedi: {e}")

    def _update_strategy_history(self, strategy_data: Dict[str, float], source_title: str):
        """Yeni strateji verisini tarihsel cache'e ekler.
        Her ay için tüm strateji raporlarındaki hedefler history listesinde birikir.
        target/source alanları en son raporu gösterir.

        Makullik kontrolü — revizyon sürekliliği: Hazine aynı ayın hedefini
        çeyrekten çeyreğe revize eder, ama revizyonlar ölçek değiştirmez
        (gözlemlenen en büyük revizyon ~1,4x). Aynı ay için önceki rapora göre
        STRATEGY_REVISION_MAX_RATIO katından fazla sapma, ayrıştırma kaynaklı
        ölçek hatasının imzasıdır — dikkat çekmek için WARNING basılır.
        """
        for month_key, target in strategy_data.items():
            if month_key not in self.strategy_history:
                self.strategy_history[month_key] = {
                    "target": target,
                    "source": source_title,
                    "parser": STRATEGY_PARSER_VERSION,
                    "history": [{"target": target, "source": source_title}],
                }
            else:
                entry = self.strategy_history[month_key]
                onceki = entry.get("target")
                if isinstance(onceki, (int, float)) and onceki > 0 and target > 0:
                    oran = max(target / onceki, onceki / target)
                    if oran > STRATEGY_REVISION_MAX_RATIO:
                        logger.warning(
                            f"Şüpheli revizyon: {month_key} hedefi {onceki} -> {target} "
                            f"({oran:.1f}x, eşik {STRATEGY_REVISION_MAX_RATIO}x). "
                            f"Kaynak: {source_title}. Sayı biçimi ayrıştırmasını kontrol edin."
                        )
                # Aynı source'dan gelen veriyi tekrarlama
                existing_sources = [h["source"] for h in entry.get("history", [])]
                if source_title not in existing_sources:
                    entry.setdefault("history", []).append({"target": target, "source": source_title})
                else:
                    # Aynı source varsa güncelle
                    for h in entry["history"]:
                        if h["source"] == source_title:
                            h["target"] = target
                            break
                # En son raporu güncelle
                entry["target"] = target
                entry["source"] = source_title
                entry["parser"] = STRATEGY_PARSER_VERSION
        self._save_strategy_history()

    @staticmethod
    def _tr_to_en_month(text: str) -> str:
        """Türkçe ay isimlerini İngilizce'ye çevirir.

        pandas to_datetime '%B' formatı locale'den bağımsız olarak İngilizce ay
        isimleri bekler; bu yüzden tarih parse etmeden önce daima çeviri yaparız.
        """
        months_tr = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
                     'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']
        months_en = ['January', 'February', 'March', 'April', 'May', 'June',
                     'July', 'August', 'September', 'October', 'November', 'December']
        for tr, en in zip(months_tr, months_en):
            text = text.replace(tr, en)
        return text

    def _extract_pdf_url_from_content(self, content_html: str) -> Optional[str]:
        """Duyuru içeriğinden (WP REST API 'content.rendered') PDF linkini çıkarır.

        Önce "tıklayınız" bağlantısını, bulunamazsa ilk .pdf bağlantısını döndürür.
        """
        if not content_html:
            return None
        soup = BeautifulSoup(content_html, 'html.parser')

        # 1) "tıklayınız" bağlantısı
        for link in soup.find_all('a', href=True):
            link_text = link.get_text().strip().lower()
            href = link['href']
            if ('tıklayınız' in link_text or 'tiklayiniz' in link_text) and href:
                return href if href.startswith('http') else urljoin(self.base_url, href)

        # 2) Herhangi bir .pdf bağlantısı
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '.pdf' in href.lower():
                return href if href.startswith('http') else urljoin(self.base_url, href)

        return None

    def get_auction_announcement_urls(self) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str, str]]]:
        """
        WordPress REST API üzerinden ihale sonucu ve strateji duyurularını toplar.

        Selenium GEREKMEZ — başlık, tarih ve PDF linki doğrudan JSON içeriğinde gelir.

        Returns:
            Tuple:
              - auction_items: List[(announcement_url, pdf_url)]  (ihale sonucu duyuruları)
              - strategy_pdfs: List[(pdf_url, baslik, ay_bilgi)]  (strateji raporları)
        """
        # Mevcut Excel'den en son ihale tarihini al (inkremental erken durma için)
        latest_excel_date = None
        if not FORCE_ALL_FETCH and os.path.exists(EXCEL_OUTPUT):
            try:
                existing_df = pd.read_excel(EXCEL_OUTPUT, sheet_name='İhale Verileri')
                if 'İhale Tarihi' in existing_df.columns:
                    dates = pd.to_datetime(existing_df['İhale Tarihi'], format='%d.%m.%Y', errors='coerce')
                    if not dates.dropna().empty:
                        latest_excel_date = dates.max()
                        logger.info(f"Excel'deki en yeni ihale tarihi: {latest_excel_date.strftime('%d.%m.%Y')}")
            except Exception as e:
                logger.warning(f"Mevcut Excel okunamadı: {str(e)}")

        auction_items: List[Tuple[str, str]] = []
        seen_announcements = set()
        strategy_pdfs: List[Tuple[str, str, str]] = []
        strategy_titles_seen = set()

        # Erken durma: ardışık "tamamı eski" sayfa sayacı
        consecutive_old_auction_pages = 0
        OLD_AUCTION_PAGE_THRESHOLD = 3

        # İhale taraması bittikten sonra strateji taraması KENDİ bütçesiyle devam eder.
        # (Eskiden tek bir break ikisini birden kesiyordu; bu yüzden revizyon
        #  tarihçesi yalnızca son birkaç aydan başlıyordu.)
        auction_scan_done = False
        consecutive_pages_without_new_strategy = 0
        strategy_scan_limit = max(self.max_pages, STRATEGY_SCAN_MAX_PAGES)

        # İhale SONUCU başlık desenleri (planlanan değil, gerçekleşen ihaleler)
        result_pattern1 = r'Tarihinde\s+Gerçekleştirilen\s+İhalelerin\s+Sonuçlarına\s+İlişkin\s+Basın\s+Duyurusu'
        result_pattern2 = r'Tarihinde\s+Gerçekleştirilen\s+İhalenin\s+Sonuçlarına\s+İlişkin\s+Basın\s+Duyurusu'

        for page in range(1, strategy_scan_limit + 1):
            if not auction_scan_done and consecutive_old_auction_pages >= OLD_AUCTION_PAGE_THRESHOLD:
                logger.info(f"{OLD_AUCTION_PAGE_THRESHOLD} ardışık sayfada tüm ihaleler mevcut veriden eski. "
                            f"İhale taraması durduruldu; strateji taraması sürüyor.")
                auction_scan_done = True
            if not auction_scan_done and page > self.max_pages:
                logger.info(f"İhale taraması sayfa üst sınırına ({self.max_pages}) ulaştı.")
                auction_scan_done = True
            if auction_scan_done and consecutive_pages_without_new_strategy >= STRATEGY_STALE_PAGE_THRESHOLD:
                logger.info(f"{STRATEGY_STALE_PAGE_THRESHOLD} ardışık sayfada yeni strateji PDF'i yok. "
                            f"Strateji taraması da durduruluyor.")
                break

            # API'den sayfayı çek (gerektiğinde yeniden dene)
            posts = None
            for attempt in range(MAX_RETRIES):
                try:
                    resp = self.session.get(
                        self.api_url,
                        params={'category_name': self.category_slug, 'page': page, 'per_page': API_PER_PAGE},
                        timeout=HTTP_TIMEOUT,
                    )
                    # WP API, son sayfadan sonrası için 400 döndürür
                    if resp.status_code == 400:
                        logger.info(f"Sayfa {page}: API'de daha fazla içerik yok (HTTP 400).")
                        posts = []
                        break
                    resp.raise_for_status()
                    posts = resp.json()
                    break
                except Exception as e:
                    logger.warning(f"API sayfa {page} hatası (deneme {attempt + 1}/{MAX_RETRIES}): {e}")
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(1)

            if not posts:
                if posts is None:
                    logger.error(f"Sayfa {page} alınamadı, tarama durduruluyor.")
                break

            logger.info(f"Sayfa {page}: {len(posts)} duyuru alındı")
            page_has_any_auction = False
            page_has_new_auction = False
            page_has_new_strategy = False
            page_oldest_date = ""

            for post in posts:
                title = html.unescape((post.get('title') or {}).get('rendered', '') or '').strip()
                content = (post.get('content') or {}).get('rendered', '') or ''
                slug = post.get('slug', '') or ''
                post_date = str(post.get('date') or '')
                if post_date and (not page_oldest_date or post_date < page_oldest_date):
                    page_oldest_date = post_date

                # --- Strateji raporu mu? ---
                title_fold = (title.lower()
                              .replace('İ', 'i').replace('ı', 'i')
                              .replace('ç', 'c').replace('ö', 'o').replace('ş', 's')
                              .replace('ğ', 'g').replace('ü', 'u'))
                title_fold = ''.join(ch for ch in title_fold if ch != '̇')
                if 'borclanma stratejisi' in title_fold:
                    if title not in strategy_titles_seen:
                        strategy_titles_seen.add(title)
                        pdf_url = self._extract_pdf_url_from_content(content)
                        ay_match = re.search(r'(\w+\s*[-–]\s*\w+\s+\d{4})', title)
                        ay_bilgi = ay_match.group(1) if ay_match else title
                        if not pdf_url:
                            logger.warning(f"Strateji duyurusunda PDF bulunamadı: {title}")
                        elif not pdf_url.lower().endswith('.pdf'):
                            # 2019 ve öncesi raporlar .docx olarak yayımlanmış;
                            # PyPDF2 okuyamaz, her çalıştırmada boşuna indirilir.
                            logger.info(f"Strateji eki PDF değil, atlanıyor: {title} ({pdf_url})")
                        else:
                            strategy_pdfs.append((pdf_url, title, ay_bilgi))
                            if pdf_url not in self.processed_urls:
                                page_has_new_strategy = True
                            logger.info(f"✓ Strateji PDF bulundu: {title}")
                    continue

                # --- İhale sonucu duyurusu mu? ---
                is_result = (re.search(result_pattern1, title, re.IGNORECASE) or
                             re.search(result_pattern2, title, re.IGNORECASE))
                if not is_result:
                    continue

                # İhale taraması bittiyse sayfaların geri kalanı yalnızca
                # strateji PDF'i için taranır; ihale duyurusu toplanmaz.
                if auction_scan_done:
                    continue

                page_has_any_auction = True

                # Kanonik duyuru URL'si (mevcut URL cache ile uyumlu).
                # WordPress çöp kutusuna atılıp geri alınan duyuruların slug'ı
                # "__trashed" ekiyle bozuluyor; kalıcı kimlik değil, bu yüzden
                # sabit olan duyuru id'sini anahtar yapıyoruz.
                if slug and '__trashed' not in slug:
                    announcement_url = f"{self.base_url}/duyuru/{slug}"
                elif post.get('id'):
                    announcement_url = f"{self.base_url}/duyuru/?p={post['id']}"
                else:
                    announcement_url = post.get('link') or ''

                # İhale tarihini başlıktan parse et
                parsed_date = None
                tarih_match = re.search(r'(\d{1,2}\s+\w+\s+\d{4})', title)
                if tarih_match:
                    tarih_str_en = self._tr_to_en_month(tarih_match.group(1))
                    parsed_date = pd.to_datetime(tarih_str_en, format='%d %B %Y', errors='coerce')

                # Erken durma değerlendirmesi
                if not FORCE_ALL_FETCH and latest_excel_date is not None and parsed_date is not None and parsed_date >= latest_excel_date:
                    page_has_new_auction = True
                elif latest_excel_date is None:
                    page_has_new_auction = True

                pdf_url = self._extract_pdf_url_from_content(content)
                if not pdf_url:
                    logger.warning(f"İhale sonucu duyurusunda PDF bulunamadı: {title}")
                    continue

                if announcement_url not in seen_announcements:
                    seen_announcements.add(announcement_url)
                    auction_items.append((announcement_url, pdf_url))
                    logger.info(f"✓ İhale sonucu duyurusu: {title}")

            # Ardışık eski sayfa sayacını güncelle
            if not FORCE_ALL_FETCH and latest_excel_date is not None:
                if page_has_any_auction and not page_has_new_auction:
                    consecutive_old_auction_pages += 1
                    logger.info(f"Sayfadaki tüm ihaleler mevcut veriden eski (ardışık: {consecutive_old_auction_pages}/{OLD_AUCTION_PAGE_THRESHOLD})")
                else:
                    consecutive_old_auction_pages = 0

            # Strateji taraması sayaçları ve tarih sınırı (sonsuza kadar tarama yok)
            if page_has_new_strategy:
                consecutive_pages_without_new_strategy = 0
            elif auction_scan_done:
                consecutive_pages_without_new_strategy += 1
            if page_oldest_date and page_oldest_date[:7] < STRATEGY_HISTORY_START:
                logger.info(f"Sayfa {page}: duyurular {STRATEGY_HISTORY_START} tarihinden eskiye indi "
                            f"(en eski: {page_oldest_date[:10]}). Tarama durduruluyor.")
                break

        logger.info(f"Toplam {len(auction_items)} ihale sonucu duyurusu, {len(strategy_pdfs)} strateji PDF bulundu")
        return auction_items, strategy_pdfs

    def extract_data_from_pdf_sync(self, pdf_url: str) -> List[Dict]:
        """PDF'den veri çıkarır (senkron versiyon)"""
        try:
            logger.info(f"PDF indiriliyor: {pdf_url}")
            response = self.session.get(pdf_url, timeout=PDF_TIMEOUT)
            response.raise_for_status()
            return self._parse_pdf_content(response.content)
        except Exception as e:
            logger.error(f"PDF işlenirken hata: {str(e)}")
            return []

    def _parse_pdf_content(self, pdf_content: bytes) -> List[Dict]:
        """PDF içeriğini parse eder"""
        try:
            pdf_file = io.BytesIO(pdf_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            all_auction_data = []
            
            for page_num, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                logger.info(f"Sayfa {page_num + 1} işleniyor...")
                page_auctions = self._parse_auction_data(page_text)
                all_auction_data.extend(page_auctions)
            
            logger.info(f"✓ PDF'den toplam {len(all_auction_data)} ihale verisi çıkarıldı")
            return all_auction_data
        except Exception as e:
            logger.error(f"PDF parse hatası: {str(e)}")
            return []

    def _parse_auction_data(self, text: str) -> List[Dict]:
        """Metin içinden ihale verilerini parse eder"""
        auction_data = []
        try:
            isin_pattern = r'(TR[A-Z0-9]{10})'
            isin_matches = list(re.finditer(isin_pattern, text))
            
            for i, match in enumerate(isin_matches):
                current_auction = {field: '' for field in self.fields}
                isin = match.group(1)
                current_auction['ISIN'] = isin
                
                start_pos = match.start()
                end_pos = isin_matches[i + 1].start() if i < len(isin_matches) - 1 else len(text)
                block_text = text[start_pos:end_pos]
                
                self._extract_auction_details(block_text, current_auction)
                
                if current_auction['ISIN']:
                    auction_data.append(current_auction)
                    logger.info(f"✓ İhale verisi çıkarıldı: {current_auction['ISIN']} - {current_auction['Senet Tanımı']}")
                    
        except Exception as e:
            logger.error(f"Veri ayrıştırırken hata: {str(e)}")
        
        return auction_data

    def _extract_auction_details(self, block_text: str, auction_data: Dict):
        """Blok metinden ihale detaylarını çıkarır"""
        patterns = {
            'Senet Tanımı': r'Senet Tanımı\s*:\s*(.+?)(?:Ortalama|$)',
            'İhale Tarihi': r'İhale Tarihi\s*:\s*(\d{2}\.\d{2}\.\d{4})',
            'Valör Tarihi': r'(?:İhraç|Valör)\s*\(?Valör\)?\s*Tarihi\s*:\s*(\d{2}\.\d{2}\.\d{4})',
            'İtfa Tarihi': r'(?:Vade|İtfa)\s*Tarihi\s*:\s*(\d{2}\.\d{2}\.\d{4})'
        }
        
        for field, pattern in patterns.items():
            match = re.search(pattern, block_text, re.IGNORECASE | re.DOTALL)
            if match:
                value = match.group(1).strip().replace('\n', ' ')
                if field == 'Senet Tanımı':
                    value = re.sub(r'(Ortalama|En Düşük|En Yüksek).*', '', value).strip()
                auction_data[field] = value
        
        # Vade hesaplama
        if auction_data.get('Valör Tarihi') and auction_data.get('İtfa Tarihi'):
            try:
                valor_date = pd.to_datetime(auction_data['Valör Tarihi'], format='%d.%m.%Y')
                maturity_date = pd.to_datetime(auction_data['İtfa Tarihi'], format='%d.%m.%Y')
                days_diff = (maturity_date - valor_date).days
                auction_data['Vade (Yıl)'] = round(days_diff / 365.25, 2)
            except:
                auction_data['Vade (Yıl)'] = ''
        
        self._extract_numeric_values(block_text, auction_data)

    def _extract_numeric_values(self, block_text: str, auction_data: Dict):
        """Blok metinden sayısal değerleri çıkarır"""
        miktar_section = re.search(
            r'Miktar \(Net, Milyon TL\)(.*?)(?:Faiz Oranları|Fiyatlar|İhraç Sonrası|$)', 
            block_text, re.DOTALL | re.IGNORECASE
        )
        
        if miktar_section:
            miktar_text = miktar_section.group(1)
            
            # ROT değerleri
            rot_match = re.search(r'ROT\s*:\s*([\d.,-]+)\s+([\d.,-]+)', miktar_text)
            if rot_match:
                auction_data['ROT Toplam(Teklif)'] = rot_match.group(1).replace('.', '').replace(',', '.')
                auction_data['ROT Toplam(Gerçekleşme)'] = rot_match.group(2).replace('.', '').replace(',', '.')
            
            # ROT Kamu değerleri
            rot_kamu_match = re.search(r'Kamu Kurumları\s*:\s*([\d.,-]+)\s+([\d.,-]+)', miktar_text)
            if rot_kamu_match:
                auction_data['ROT Kamu(Teklif)'] = rot_kamu_match.group(1).replace('.', '').replace(',', '.')
                auction_data['ROT Kamu(Gerçekleşme)'] = rot_kamu_match.group(2).replace('.', '').replace(',', '.')
            
            # ROT Piyasa Yapıcılar
            rot_piyasa_pattern = r'(?:ROT.*?)?Piyasa Yapıcılar\s*:\s*([\d.,-]+)\s+([\d.,-]+)'
            rot_piyasa_matches = re.findall(rot_piyasa_pattern, miktar_text)
            if rot_piyasa_matches:
                auction_data['ROT Piyasa Yapıcılar(Teklif)'] = rot_piyasa_matches[0][0].replace('.', '').replace(',', '.')
                auction_data['ROT Piyasa Yapıcılar(Gerçekleşme)'] = rot_piyasa_matches[0][1].replace('.', '').replace(',', '.')
                try:
                    teklif = float(auction_data['ROT Piyasa Yapıcılar(Teklif)'])
                    gerceklesme = float(auction_data['ROT Piyasa Yapıcılar(Gerçekleşme)'])
                    if teklif > 0:
                        auction_data['ROT Piyasa Yapıcılar Kabul Oranı (%)'] = round((gerceklesme / teklif) * 100, 1)
                except:
                    pass
            
            # İhale değerleri
            ihale_match = re.search(r'İhale\s*:\s*([\d.,-]+)\s+([\d.,-]+)', miktar_text)
            if ihale_match:
                auction_data['İhale(Teklif)'] = ihale_match.group(1).replace('.', '').replace(',', '.')
                auction_data['İhale(Gerçekleşme)'] = ihale_match.group(2).replace('.', '').replace(',', '.')
                try:
                    teklif = float(auction_data['İhale(Teklif)'])
                    gerceklesme = float(auction_data['İhale(Gerçekleşme)'])
                    if teklif > 0:
                        auction_data['İhale Kabul Oranı (%)'] = round((gerceklesme / teklif) * 100, 1)
                except:
                    pass
            
            # Toplam değerleri
            toplam_match = re.search(r'Toplam\s*:\s*([\d.,-]+)\s+([\d.,-]+)', miktar_text)
            if toplam_match:
                auction_data['Toplam(Teklif)'] = toplam_match.group(1).replace('.', '').replace(',', '.')
                auction_data['Toplam(Gerçekleşme)'] = toplam_match.group(2).replace('.', '').replace(',', '.')
        
        # Faiz oranları
        faiz_patterns = {
            'Ortalama Yıllık Basit': r'Ortalama Yıllık Basit\s*:\s*([\d.,-]+)\s+([\d.,-]+)',
            'Ortalama Yıllık Bileşik': r'Ortalama Yıllık Bileşik\s*:\s*([\d.,-]+)\s+([\d.,-]+)',
            'En Düşük Yıllık Bileşik': r'En Düşük Yıllık Bileşik\s*:\s*([\d.,-]+)\s+([\d.,-]+)',
            'En Yüksek Yıllık Bileşik': r'En Yüksek Yıllık Bileşik\s*:\s*([\d.,-]+)\s+([\d.,-]+)'
        }
        
        for field_base, pattern in faiz_patterns.items():
            match = re.search(pattern, block_text, re.IGNORECASE)
            if match:
                auction_data[f'{field_base}(Teklif)'] = match.group(1).replace(',', '.')
                auction_data[f'{field_base}(Gerçekleşme)'] = match.group(2).replace(',', '.')
        
        # Fiyatlar
        fiyat_patterns = {
            'Ortalama Fiyat': r'Ortalama Fiyat\s*:\s*([\d.,-]+)\s+([\d.,-]+)',
            'En Yüksek Fiyat': r'En Yüksek Fiyat\s*:\s*([\d.,-]+)\s+([\d.,-]+)',
            'En Düşük Fiyat': r'En Düşük Fiyat\s*:\s*([\d.,-]+)\s+([\d.,-]+)'
        }
        
        for field_base, pattern in fiyat_patterns.items():
            match = re.search(pattern, block_text, re.IGNORECASE)
            if match:
                auction_data[f'{field_base}(Teklif)'] = match.group(1).replace('.', '').replace(',', '.')
                auction_data[f'{field_base}(Gerçekleşme)'] = match.group(2).replace('.', '').replace(',', '.')

    def extract_strategy_data(self, pdf_url: str) -> Dict[str, float]:
        """
        Strateji PDF'inden hedef verilerini çıkarır.
        Çeyreklik PDF'den 3 ayın tamamının verilerini alır.
        """
        try:
            logger.info(f"Strateji PDF'i indiriliyor: {pdf_url}")
            response = self.session.get(pdf_url, timeout=PDF_TIMEOUT)
            response.raise_for_status()

            pdf_file = io.BytesIO(response.content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)

            full_text = ""
            for page in pdf_reader.pages:
                full_text += page.extract_text() + "\n"

            # Dönem başlığından ilk ay, son ay ve yılı bul.
            # İki biçimi de destekle:
            #   "Haziran – Ağustos 2026"        (yıl yalnızca sonda)
            #   "Aralık 2025 – Şubat 2026"      (yıl geçişli çeyrek; ilk ayda da yıl)
            title_pattern = r'([A-Za-zçğıöşüÇĞİÖŞÜ]+)\s*(?:\d{4}\s*)?[-–]\s*([A-Za-zçğıöşüÇĞİÖŞÜ]+)\s+(\d{4})'
            title_match = re.search(title_pattern, full_text, re.IGNORECASE)

            if title_match:
                first_month_raw = title_match.group(1).strip()
                last_month_raw = title_match.group(2).strip()
                first_month = normalize_month_name(first_month_raw)
                last_month = normalize_month_name(last_month_raw)
                year = int(title_match.group(3))
                months = generate_quarter_months(first_month_raw, last_month_raw)
                logger.info(f"Dönem ayları: {months} {year}")
            else:
                logger.error(f"Dönem başlığı bulunamadı! PDF: {pdf_url}")
                return {}

            # Tabloyu satır satır işle
            lines = full_text.splitlines()
            piyasa_line = None
            kamu_line = None
            dogrudan_line = None
            ic_borclanma_line = None
            toplam_line = None

            for line in lines:
                if "Piyasadan İhale Yoluyla İç Borçlanma" in line:
                    piyasa_line = line
                if "Kamuya Satışlar" in line:
                    kamu_line = line
                if "Doğrudan Satışlar" in line:
                    dogrudan_line = line
                # "   İç Borçlanma 25.4 40.4 31.2" — finansman programının ara toplamı.
                # "Piyasadan İhale Yoluyla İç Borçlanma" satırıyla karışmaması için
                # satır başına sabitliyoruz.
                if re.match(r"\s*İç Borçlanma\s", line):
                    ic_borclanma_line = line
                if re.search(r"^Toplam\s", line) or "Toplam İç Borçlanma" in line:
                    toplam_line = line

            if piyasa_line and kamu_line:
                # Ondalık ayracını TEK SATIRDAN DEĞİL, tablo bağlamından tespit et:
                # "Kamuya Satışlar 1.000 2.000 3.000" gibi bir satır tek başına
                # binlik ayraçlı görünür; finansman programı satırlarının tamamı
                # ise aynı biçimdedir, birlikte bakınca biçim kesinleşir.
                tablo_baglam = "\n".join(
                    x for x in (piyasa_line, kamu_line, dogrudan_line, ic_borclanma_line) if x
                )
                decimal_sep = detect_decimal_separator(tablo_baglam)
                logger.info(f"Sayı biçimi tespiti: ondalık ayraç '{decimal_sep}'")

                piyasa_vals = NUMBER_TOKEN_RE.findall(piyasa_line)
                kamu_vals = NUMBER_TOKEN_RE.findall(kamu_line)

                logger.info(f"Piyasa değerleri ({len(piyasa_vals)} adet): {piyasa_vals}")
                logger.info(f"Kamu değerleri ({len(kamu_vals)} adet): {kamu_vals}")

                results = {}
                # Yıl geçişini yönet: başlıktaki yıl son aya ait
                # Eğer çeyrek yıl geçişi içeriyorsa (ör: Kasım-Ocak),
                # son aydan önceki aylar bir önceki yıla ait
                last_month_idx = MONTH_ORDER.index(last_month)

                for i, month in enumerate(months):
                    if i < len(piyasa_vals) and i < len(kamu_vals):
                        try:
                            piyasa = parse_localized_number(piyasa_vals[i], decimal_sep)
                            kamu = parse_localized_number(kamu_vals[i], decimal_sep)
                            toplam = piyasa + kamu

                            # Yıl hesapla: son ay yılı belli, önceki aylar yıl geçişinde year-1
                            month_idx = MONTH_ORDER.index(month)
                            if month_idx > last_month_idx:
                                # Bu ay, son aydan sonra geliyor -> bir önceki yıl
                                actual_year = year - 1
                            else:
                                actual_year = year

                            key = f"{month} {actual_year}"

                            # Makullik bandı: bant dışı değer ayrıştırma hatasıdır,
                            # sessizce kaydetmek yerine düşür.
                            if not (STRATEGY_TARGET_MIN <= toplam <= STRATEGY_TARGET_MAX):
                                logger.error(
                                    f"  {key}: {toplam} milyar TL makul bant dışında "
                                    f"[{STRATEGY_TARGET_MIN}, {STRATEGY_TARGET_MAX}] — atlandı"
                                )
                                continue

                            results[key] = toplam
                            logger.info(f"  {key}: Piyasa={piyasa}, Kamu={kamu}, Toplam={toplam} milyar TL")
                        except Exception as e:
                            logger.error(f"Ay {month} için değer parse hatası: {e}")

                # Makullik kontrolü — satırlar arası ölçek tutarlılığı.
                # Hedefimiz (Piyasadan İhale + Kamuya Satışlar), tablodaki
                # "İç Borçlanma" ara toplamının bir ALT KÜMESİDİR: aradaki fark
                # "Doğrudan Satışlar" kalemidir (altın/döviz cinsi ihraçlar; ihale
                # değil, bu yüzden hedefe katılmaz). Bu yüzden EŞİTLİK değil, ORAN
                # aranır: oran 0'a veya 1'e yakın olmalı; 10 kat sapma iki satırın
                # farklı biçimde ayrıştırıldığının işaretidir.
                # NOT: satırların TAMAMI aynı yönde kaysaydı oran korunur; ölçek
                # hatasına karşı asıl koruma biçim tespiti + revizyon süreklilik
                # kontrolüdür (bkz. _update_strategy_history).
                if ic_borclanma_line and results:
                    ic_vals = NUMBER_TOKEN_RE.findall(ic_borclanma_line)
                    for i in range(min(len(ic_vals), len(piyasa_vals), len(kamu_vals))):
                        try:
                            ihale_bazli = (parse_localized_number(piyasa_vals[i], decimal_sep)
                                           + parse_localized_number(kamu_vals[i], decimal_sep))
                            ic_toplam = parse_localized_number(ic_vals[i], decimal_sep)
                            if ic_toplam <= 0:
                                continue
                            oran = ihale_bazli / ic_toplam
                            if not (0.15 <= oran <= 1.05):
                                logger.warning(
                                    f"İhale bazlı borçlanma / İç Borçlanma oranı makul değil "
                                    f"(sütun {i + 1}): {round(ihale_bazli, 2)} / {ic_toplam} "
                                    f"= {oran:.2f} — satırlar farklı sayı biçiminde "
                                    f"ayrıştırılmış olabilir"
                                )
                        except Exception:
                            pass

                # Toplam satırı ile çapraz kontrol
                if toplam_line and results:
                    toplam_vals = NUMBER_TOKEN_RE.findall(toplam_line)
                    if toplam_vals:
                        try:
                            # Toplam satırındaki ilk değer genelde çeyrek toplamı
                            reported_total = parse_localized_number(
                                toplam_vals[0], detect_decimal_separator(toplam_line))
                            calculated_total = sum(results.values())
                            diff_pct = abs(reported_total - calculated_total) / reported_total * 100 if reported_total > 0 else 0
                            if diff_pct > 5:
                                logger.warning(f"Toplam uyumsuzluk! Rapor: {reported_total}, Hesaplanan: {calculated_total} (fark: %{diff_pct:.1f})")
                        except Exception:
                            pass

                if results:
                    return results

            logger.error(f"Tablo satırları bulunamadı! PDF: {pdf_url}")
            return {}
            
        except Exception as e:
            logger.error(f"Strateji PDF'si işlenirken hata: {str(e)}")
            return {}

    def _process_pdf_batch_parallel(self, pdf_urls: List[str]) -> List[Dict]:
        """
        PDF'leri paralel olarak işler (ThreadPoolExecutor ile)
        
        Bu metot, performans için kritik - birden fazla PDF'i aynı anda indirir ve parse eder
        """
        all_auction_data = []
        
        if USE_ASYNC:
            # Async versiyon (en hızlı)
            logger.info(f"Async olarak {len(pdf_urls)} PDF indiriliyor...")
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                pdf_contents = loop.run_until_complete(download_multiple_pdfs_async(pdf_urls))
                loop.close()
                
                # Parse işlemini paralel yap
                with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                    futures = {
                        executor.submit(self._parse_pdf_content, content): url 
                        for url, content in pdf_contents.items()
                    }
                    
                    for future in as_completed(futures):
                        url = futures[future]
                        try:
                            result = future.result()
                            all_auction_data.extend(result)
                            logger.info(f"✓ {url} işlendi: {len(result)} ihale")
                        except Exception as e:
                            logger.error(f"PDF parse hatası ({url}): {str(e)}")
                            
            except Exception as e:
                logger.error(f"Async indirme hatası: {str(e)}")
                # Fallback: senkron işleme
                for url in pdf_urls:
                    all_auction_data.extend(self.extract_data_from_pdf_sync(url))
        else:
            # Thread pool versiyon
            logger.info(f"ThreadPool ile {len(pdf_urls)} PDF işleniyor...")
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = {executor.submit(self.extract_data_from_pdf_sync, url): url for url in pdf_urls}
                
                for future in as_completed(futures):
                    url = futures[future]
                    try:
                        result = future.result()
                        all_auction_data.extend(result)
                        logger.info(f"✓ {url} işlendi: {len(result)} ihale")
                    except Exception as e:
                        logger.error(f"PDF işleme hatası ({url}): {str(e)}")
        
        return all_auction_data

    def analyze_borrowing_performance(self, auction_df: pd.DataFrame, strategy_data: Dict[str, float]) -> pd.DataFrame:
        """Borçlanma performansını analiz eder"""
        if not strategy_data or auction_df.empty:
            return pd.DataFrame()
        
        if 'İhale Tarihi' not in auction_df.columns:
            logger.error("DataFrame'de 'İhale Tarihi' sütunu bulunamadı.")
            return pd.DataFrame()
        
        monthly_realized = {}
        df_filtered = auction_df.dropna(subset=['İhale Tarihi', 'Toplam(Gerçekleşme)'])
        
        for _, row in df_filtered.iterrows():
            try:
                date_obj = pd.to_datetime(row['İhale Tarihi'], format='%d.%m.%Y')
                en_month = date_obj.strftime('%B')
                tr_month = self.en_to_tr_months.get(en_month, en_month)
                year = date_obj.year
                key = f"{tr_month} {year}"
                
                realized_str = str(row['Toplam(Gerçekleşme)']).replace(',', '').replace(' ', '')
                total_realized = float(realized_str) if realized_str.replace('.', '').isdigit() else 0
                
                if tr_month and total_realized > 0:
                    monthly_realized[key] = monthly_realized.get(key, 0) + total_realized
            except Exception as e:
                logger.debug(f"Tarih parse hatası: {row.get('İhale Tarihi')} - {str(e)}")
        
        logger.info(f"Bulunan aylar: {list(monthly_realized.keys())}")
        logger.info(f"Strateji ayları: {list(strategy_data.keys())}")

        # İhale veri setinin başladığı ay. Strateji raporları ihale verisinden
        # daha geriye gidebiliyor; o aylar için "gerçekleşen = 0" yazmak veri
        # yokluğunu "Hazine hiç borçlanmadı" gibi gösterir. Kapsam dışı ayları
        # karşılaştırmaya hiç almıyoruz.
        ilk_ihale_ay = None
        try:
            ihale_tarihleri = pd.to_datetime(
                df_filtered['İhale Tarihi'], format='%d.%m.%Y', errors='coerce').dropna()
            if not ihale_tarihleri.empty:
                ilk_ihale_ay = ihale_tarihleri.min().to_period('M')
        except Exception as e:
            logger.debug(f"İlk ihale ayı hesaplanamadı: {e}")

        comparison_data = []
        kapsam_disi = []
        for month_label, target in strategy_data.items():
            if re.match(r"^[A-Za-zçğıöşüÇĞİÖŞÜ]+ \d{4}$", month_label):
                parts = month_label.split()
                key = f"{normalize_month_name(parts[0])} {parts[1]}"
            else:
                key = normalize_month_name(month_label)
                for k in monthly_realized.keys():
                    if k.startswith(normalize_month_name(month_label)):
                        key = k
                        break

            # Kapsam kontrolü: ihale verisinin başlangıcından önceki aylar atlanır
            if ilk_ihale_ay is not None and key not in monthly_realized:
                try:
                    p = pd.Period(self._tr_to_en_month(key), freq='M')
                    if p < ilk_ihale_ay:
                        kapsam_disi.append(key)
                        continue
                except Exception:
                    pass

            realized = monthly_realized.get(key, 0) / 1000

            comparison_data.append({
                'Ay-Yıl': key,
                'Hedef Borçlanma (Milyar TL)': target,
                'Gerçekleşen Borçlanma (Milyar TL)': round(realized, 2),
                'Fark (Milyar TL)': round(realized - target, 2),
                'Gerçekleşme Oranı (%)': round((realized / target * 100) if target > 0 else 0, 1)
            })
        
        if kapsam_disi:
            logger.info(f"İhale verisi kapsamı dışındaki {len(kapsam_disi)} ay karşılaştırmaya "
                        f"alınmadı (ilk ihale ayı: {ilk_ihale_ay}): {sorted(kapsam_disi)}")

        if not comparison_data:
            logger.warning("Karşılaştırma verisi oluşturulamadı.")
            return pd.DataFrame()

        comparison_df = pd.DataFrame(comparison_data)
        
        logger.info("\n" + "="*60)
        logger.info("BORÇLANMA HEDEFLERİ ANALİZİ")
        logger.info("="*60)
        for _, row in comparison_df.iterrows():
            status = "✓" if row['Fark (Milyar TL)'] >= 0 else "✗"
            logger.info(f"{status} {row['Ay-Yıl']}: Hedef {row['Hedef Borçlanma (Milyar TL)']} Milyar TL, "
                        f"Gerçekleşen {row['Gerçekleşen Borçlanma (Milyar TL)']} Milyar TL "
                        f"(Fark: {row['Fark (Milyar TL)']} Milyar TL, %{row['Gerçekleşme Oranı (%)']})")
        
        return comparison_df

    # =====================
    # PLANLI İHRAÇLAR + TAHMİN
    # =====================
    def fetch_issuance_calendar(self, pdf_url: str) -> List[Dict]:
        """Strateji PDF'inden ihraç takvimini indirip ayrıştırır."""
        try:
            logger.info(f"İhraç takvimi için strateji PDF'i indiriliyor: {pdf_url}")
            response = self.session.get(pdf_url, timeout=PDF_TIMEOUT)
            response.raise_for_status()
            reader = PyPDF2.PdfReader(io.BytesIO(response.content))
            full_text = "".join((page.extract_text() or "") + "\n" for page in reader.pages)
            calendar = parse_issuance_calendar(full_text)
            logger.info(f"✓ İhraç takviminden {len(calendar)} planlı ihraç ayrıştırıldı")
            return calendar
        except Exception as e:
            logger.error(f"İhraç takvimi ayrıştırılamadı: {e}")
            return []

    def _load_planned_calendar_cache(self) -> dict:
        """Planlı takvim cache'ini yükler: {'source': url, 'items': [...]}."""
        try:
            if os.path.exists(PLANNED_CALENDAR_CACHE):
                with open(PLANNED_CALENDAR_CACHE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Planlı takvim cache okunamadı: {e}")
        return {}

    def _save_planned_calendar_cache(self, source: str, items: List[Dict]):
        try:
            with open(PLANNED_CALENDAR_CACHE, 'w', encoding='utf-8') as f:
                json.dump({'source': source, 'items': items}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Planlı takvim cache kaydedilemedi: {e}")

    @staticmethod
    def _recent_realization_rate(comparison_df: Optional[pd.DataFrame],
                                 n_months: int = 12, default: float = 0.85) -> float:
        """Son n tamamlanmış aydaki toplam gerçekleşen / toplam hedef oranı.

        Strateji hedefi planı temsil eder; Hazine genelde planın altında
        gerçekleştirir. Bu oran, ileriye dönük tahmindeki sistematik fazla-tahmini
        düzeltmek için kullanılır (hedef × oran).
        """
        if comparison_df is None or comparison_df.empty or 'Ay-Yıl' not in comparison_df.columns:
            return default
        tr = {'Ocak': 1, 'Şubat': 2, 'Mart': 3, 'Nisan': 4, 'Mayıs': 5, 'Haziran': 6,
              'Temmuz': 7, 'Ağustos': 8, 'Eylül': 9, 'Ekim': 10, 'Kasım': 11, 'Aralık': 12}
        c = comparison_df.copy()
        c['_real'] = pd.to_numeric(c['Gerçekleşen Borçlanma (Milyar TL)'], errors='coerce')
        c['_tgt'] = pd.to_numeric(c['Hedef Borçlanma (Milyar TL)'], errors='coerce')

        def keyf(s):
            p = str(s).split()
            return (int(p[1]), tr.get(p[0], 0)) if len(p) == 2 and p[1].isdigit() else (0, 0)

        c['_k'] = c['Ay-Yıl'].map(keyf)
        # Yalnızca tamamlanmış aylar (gerçekleşen > 0), en yeni n ay
        c = c[(c['_real'] > 0) & (c['_tgt'] > 0)].sort_values('_k').tail(n_months)
        if c.empty or c['_tgt'].sum() <= 0:
            return default
        rate = float(c['_real'].sum() / c['_tgt'].sum())
        return max(0.4, min(1.5, rate))  # makul sınırlar

    def build_planned_issuances(self, df: pd.DataFrame, newest_strategy_url: Optional[str],
                                comparison_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """Önümüzdeki planlı ihraçları derler ve geçmiş veriye dayalı tahmin üretir.

        Takvim, en güncel strateji raporundan gelir; rapor değişmediyse cache'ten
        okunur (yeniden indirilmez). Tahminler her çalıştırmada güncel geçmiş
        veriye göre yeniden hesaplanır.

        Tahmin mantığı:
          1) Her ihale için geçmiş kıyaslardan ham gerçekleşme + bid-to-cover + faiz.
          2) Bir ayın ihale tahminleri, o ayın strateji hedefiyle (piyasa+kamu) TUTARLI
             olacak şekilde ölçeklenir (ayın kalan hedefi = hedef - o ay gerçekleşen).
          3) Teklif (bid) tutarı = tahmini gerçekleşme × tahmini bid-to-cover.
        """
        # 1) Takvimi al (cache uyumluysa indirme yapma)
        cache = self._load_planned_calendar_cache()
        calendar = cache.get('items', [])
        if newest_strategy_url and cache.get('source') != newest_strategy_url:
            fetched = self.fetch_issuance_calendar(newest_strategy_url)
            if fetched:
                calendar = fetched
                self._save_planned_calendar_cache(newest_strategy_url, calendar)
        elif calendar:
            logger.info(f"İhraç takvimi cache'ten okundu ({len(calendar)} kayıt, yeniden indirilmedi)")

        if not calendar:
            logger.info("Planlı ihraç takvimi bulunamadı.")
            return pd.DataFrame()

        # 2) Geçmiş veriyi hazırla
        hist = df.copy()
        for col in ['Ortalama Yıllık Bileşik(Gerçekleşme)', 'Toplam(Gerçekleşme)',
                    'Toplam(Teklif)', 'Vade (Yıl)', 'İhale Kabul Oranı (%)']:
            if col in hist.columns:
                hist[col] = pd.to_numeric(hist[col], errors='coerce')
        hist['_d'] = pd.to_datetime(hist['İhale Tarihi'], format='%d.%m.%Y', errors='coerce')
        latest_done = hist['_d'].max()

        # Ay anahtarı yardımcı: tarih -> "Temmuz 2026"
        def month_key(d):
            if pd.isna(d):
                return ''
            return f"{self.en_to_tr_months.get(d.strftime('%B'), d.strftime('%B'))} {d.year}"

        # O aya kadar zaten gerçekleşen tutar (kısmi aylarda hedeften düşmek için)
        hist['_ay'] = hist['_d'].map(month_key)
        realized_by_month = hist.groupby('_ay')['Toplam(Gerçekleşme)'].sum().to_dict()

        # Aylık strateji hedefleri (Milyar TL) — karşılaştırma tablosundan
        targets = {}
        if comparison_df is not None and not comparison_df.empty and 'Ay-Yıl' in comparison_df.columns:
            for _, r in comparison_df.iterrows():
                try:
                    targets[str(r['Ay-Yıl']).strip()] = float(r['Hedef Borçlanma (Milyar TL)'])
                except (ValueError, TypeError, KeyError):
                    pass

        # Geçmiş gerçekleşme oranı (hedef × oran ile fazla-tahmini düzelt — Seçenek 2)
        realization_rate = self._recent_realization_rate(comparison_df)
        logger.info(f"Gerçekleşme oranı varsayımı (son ~12 ay): %{realization_rate * 100:.1f} "
                    f"(tahminler strateji hedefi × bu orana ölçeklenir)")

        rows = []
        for item in calendar:
            ihale_d = pd.to_datetime(item['ihale_tarihi'], format='%d.%m.%Y', errors='coerce')
            if pd.isna(ihale_d) or (pd.notna(latest_done) and ihale_d <= latest_done):
                continue  # geçmiş/gerçekleşmiş olanları atla

            # Türkçe İ.lower() birleşik nokta (U+0307) ürettiğinden onu temizle
            yontem_fold = item['yontem'].lower().replace('̇', '').replace('ı', 'i')
            is_auction = 'ihale' in yontem_fold
            yeniden = 'yeniden' in yontem_fold

            forecast = self._forecast_one_issuance(item, hist, is_auction, yeniden)
            rows.append({
                'İhale Tarihi': item['ihale_tarihi'],
                'Senet Tanımı': item['senet_tanimi'],
                'Vade Terimi': item['vade_terimi'],
                'İtfa Tarihi': item['itfa_tarihi'],
                'Yöntem': item['yontem'],
                **forecast,
            })

        planned_df = pd.DataFrame(rows)
        if planned_df.empty:
            return planned_df

        planned_df['_d'] = pd.to_datetime(planned_df['İhale Tarihi'], format='%d.%m.%Y', errors='coerce')
        planned_df['_ay'] = planned_df['_d'].map(month_key)
        raw_col = 'Geçmiş Ort. Gerçekleşme (Milyon TL)'

        # 3) Strateji-tutarlı ölçekleme (hedef × gerçekleşme oranı) + teklif hesabı
        planned_df['Aylık Strateji Hedefi (Milyar TL)'] = planned_df['_ay'].map(
            lambda a: round(targets[a], 1) if a in targets else None)
        planned_df['Gerçekleşme Oranı Varsayımı (%)'] = round(realization_rate * 100, 1)
        planned_df['Tahmini Gerçekleşme (Milyon TL)'] = planned_df[raw_col]

        for ay, grp in planned_df.groupby('_ay'):
            if ay not in targets:
                continue
            auc = grp[grp[raw_col].notna()]
            raw_sum = float(auc[raw_col].sum())
            # Ayın beklenen toplamı = hedef × gerçekleşme oranı; kalanı = beklenen - gerçekleşen
            expected = targets[ay] * 1000 * realization_rate
            remaining = expected - float(realized_by_month.get(ay, 0))
            if raw_sum > 0 and remaining > 0:
                scale = remaining / raw_sum
                planned_df.loc[auc.index, 'Tahmini Gerçekleşme (Milyon TL)'] = (
                    planned_df.loc[auc.index, raw_col] * scale).round(0)

        def _teklif(r):
            g, b = r['Tahmini Gerçekleşme (Milyon TL)'], r['Tahmini Bid-to-Cover']
            return round(float(g) * float(b), 0) if pd.notna(g) and pd.notna(b) else None
        planned_df['Tahmini Teklif (Milyon TL)'] = planned_df.apply(_teklif, axis=1)

        # 4) Sırala + sütun düzeni
        planned_df = planned_df.sort_values('_d').drop(columns=['_d', '_ay']).reset_index(drop=True)
        col_order = [
            'İhale Tarihi', 'Senet Tanımı', 'Vade Terimi', 'İtfa Tarihi', 'Yöntem',
            'Aylık Strateji Hedefi (Milyar TL)', 'Gerçekleşme Oranı Varsayımı (%)',
            'Tahmini Gerçekleşme (Milyon TL)', 'Tahmini Bid-to-Cover', 'Tahmini Teklif (Milyon TL)',
            'Geçmiş Ort. Gerçekleşme (Milyon TL)',
            'Kıyas Bazı', 'Kıyas İhale Sayısı', 'Son İhale Tarihi',
        ]
        planned_df = planned_df[[c for c in col_order if c in planned_df.columns]]
        logger.info(f"✓ {len(planned_df)} planlı ihraç + tahmin derlendi (strateji-tutarlı + bid-to-cover)")
        return planned_df

    def _forecast_one_issuance(self, item: Dict, hist: pd.DataFrame,
                               is_auction: bool, yeniden: bool) -> Dict:
        """Tek bir planlı ihraç için geçmişe dayalı ham tahmin üretir.

        - Yeniden ihraç: aynı tahvil (İtfa Tarihi eşleşmesi) geçmişinden.
        - İlk ihraç: aynı senet tipi + benzer vadeli son ihalelerden.
        - Doğrudan satış (kira sertifikası/altın/USD): ihale verisi yok → tahmin yok.

        NOT: Buradaki tutar 'geçmiş ortalama'dır; strateji hedefine ölçekleme
        ve teklif (bid) hesabı ay düzeyinde build_planned_issuances'ta yapılır.
        Bid-to-Cover = Toplam(Teklif) / Toplam(Gerçekleşme) (son ihalelerin ort.).
        Faiz tahmini yapılmaz: faiz piyasa koşullarına bağlı oynak bir değişken
        ve canlı piyasa verisine erişim yok.
        """
        empty = {
            'Geçmiş Ort. Gerçekleşme (Milyon TL)': None,
            'Tahmini Bid-to-Cover': None,
            'Kıyas Bazı': '',
            'Kıyas İhale Sayısı': 0,
            'Son İhale Tarihi': '',
        }
        if not is_auction:
            empty['Kıyas Bazı'] = 'Doğrudan satış — ihale tahmini yok'
            return empty

        ym = re.match(r'(\d+)\s*Yıl', item['vade_terimi'])
        mm = re.match(r'(\d+)\s*Ay', item['vade_terimi'])
        target_years = float(ym.group(1)) if ym else (float(mm.group(1)) / 12 if mm else None)

        res = self._forecast_from_comparables(item['senet_tanimi'], item['itfa_tarihi'],
                                              target_years, hist)
        if res is None:
            empty['Kıyas Bazı'] = 'Kıyas verisi yok'
            return empty
        return {
            'Geçmiş Ort. Gerçekleşme (Milyon TL)': res['raw_amt'],
            'Tahmini Bid-to-Cover': res['btc'],
            'Kıyas Bazı': res['basis'],
            'Kıyas İhale Sayısı': res['n'],
            'Son İhale Tarihi': res['last_date'],
        }

    @staticmethod
    def _forecast_from_comparables(senet_tanimi: str, itfa_tarihi: str,
                                   target_years: Optional[float], hist: pd.DataFrame) -> Optional[Dict]:
        """Geçmiş kıyas ihalelerden ham gerçekleşme + bid-to-cover üretir.

        Önce aynı tahvil (İtfa Tarihi eşleşmesi = yeniden ihraç), yoksa aynı tip +
        benzer vadeli son ihaleler. Hem ileriye dönük tahmin hem backtest bunu kullanır.
        hist: sayısal Toplam(Gerçekleşme)/Toplam(Teklif)/Vade (Yıl) ve '_d' sütunlarını içermeli.
        """
        amt_col = 'Toplam(Gerçekleşme)'
        bid_col = 'Toplam(Teklif)'
        comparables = hist[hist['İtfa Tarihi'] == itfa_tarihi] if itfa_tarihi else hist.iloc[0:0]
        basis = 'Aynı tahvil (itfa eşleşmesi)'
        if comparables.empty:
            cand = hist[hist['Senet Tanımı'] == senet_tanimi]
            if target_years is not None and 'Vade (Yıl)' in cand.columns:
                near = cand[(cand['Vade (Yıl)'] - target_years).abs() <= 1.0]
                cand = near if not near.empty else cand
            comparables = cand
            basis = 'Aynı tip + benzer vade'

        comparables = comparables.dropna(subset=[amt_col]).sort_values('_d')
        if comparables.empty:
            return None

        recent = comparables.tail(3)
        raw_amt = round(float(recent[amt_col].mean()), 0)
        btc = None
        if bid_col in comparables.columns:
            rr = recent[[bid_col, amt_col]].copy()
            rr[bid_col] = pd.to_numeric(rr[bid_col], errors='coerce')
            rr = rr.dropna()
            rr = rr[rr[amt_col] > 0]
            if not rr.empty:
                btc = round(float((rr[bid_col] / rr[amt_col]).mean()), 2)
        return {'raw_amt': raw_amt, 'btc': btc, 'basis': basis,
                'n': int(len(comparables)), 'last_date': str(comparables.iloc[-1]['İhale Tarihi'])}

    def backtest_forecasts(self, df: pd.DataFrame, comparison_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """Geçmiş ihaleleri 'o tarihten önceki veriyle' tahmin edip gerçeğe kıyaslar.

        Her ihale için, yalnızca o ihale tarihinden ÖNCEKİ ihalelerle (look-ahead yok)
        ileriye dönük yöntemin aynısı uygulanır:
          - Ham gerçekleşme (kıyasların son 3 ortalaması) + bid-to-cover
          - Aylık strateji hedefine ölçeklenmiş gerçekleşme (canlı yöntemle aynı)
          - Teklif = gerçekleşme × bid-to-cover
        Çıktı: tahmin vs gerçek + sapma yüzdeleri (Milyon TL).
        """
        hist = df.copy()
        for col in ['Toplam(Gerçekleşme)', 'Toplam(Teklif)', 'Vade (Yıl)']:
            if col in hist.columns:
                hist[col] = pd.to_numeric(hist[col], errors='coerce')
        hist['_d'] = pd.to_datetime(hist['İhale Tarihi'], format='%d.%m.%Y', errors='coerce')
        hist = hist.dropna(subset=['_d', 'Toplam(Gerçekleşme)'])
        hist = hist[hist['Toplam(Gerçekleşme)'] > 0].sort_values('_d').reset_index(drop=True)

        def month_key(d):
            return f"{self.en_to_tr_months.get(d.strftime('%B'), d.strftime('%B'))} {d.year}"

        targets = {}
        if comparison_df is not None and not comparison_df.empty and 'Ay-Yıl' in comparison_df.columns:
            for _, r in comparison_df.iterrows():
                try:
                    targets[str(r['Ay-Yıl']).strip()] = float(r['Hedef Borçlanma (Milyar TL)'])
                except (ValueError, TypeError, KeyError):
                    pass

        rows = []
        for _, r in hist.iterrows():
            prior = hist[hist['_d'] < r['_d']]
            if prior.empty:
                continue
            res = self._forecast_from_comparables(r['Senet Tanımı'], r['İtfa Tarihi'],
                                                  r.get('Vade (Yıl)'), prior)
            if res is None:
                continue
            actual_amt = float(r['Toplam(Gerçekleşme)'])
            actual_bid = pd.to_numeric(r.get('Toplam(Teklif)'), errors='coerce')
            actual_btc = (actual_bid / actual_amt) if (pd.notna(actual_bid) and actual_amt > 0) else None
            rows.append({
                'İhale Tarihi': r['İhale Tarihi'],
                'Senet Tanımı': r['Senet Tanımı'],
                '_ay': month_key(r['_d']),
                'Gerçek Gerçekleşme (Milyon TL)': round(actual_amt, 0),
                'Tahmin-Ham (Milyon TL)': res['raw_amt'],
                'Gerçek Bid-to-Cover': round(actual_btc, 2) if actual_btc is not None else None,
                'Tahmin Bid-to-Cover': res['btc'],
                'Gerçek Teklif (Milyon TL)': round(float(actual_bid), 0) if pd.notna(actual_bid) else None,
                'Kıyas Bazı': res['basis'],
            })

        bt = pd.DataFrame(rows)
        if bt.empty:
            return bt

        # Strateji-tutarlı tahmin: ayın ham tahminlerini o ayın hedefine ölçekle
        bt['Tahmin-Strateji (Milyon TL)'] = bt['Tahmin-Ham (Milyon TL)']
        for ay, grp in bt.groupby('_ay'):
            if ay in targets and grp['Tahmin-Ham (Milyon TL)'].sum() > 0:
                scale = targets[ay] * 1000 / grp['Tahmin-Ham (Milyon TL)'].sum()
                bt.loc[grp.index, 'Tahmin-Strateji (Milyon TL)'] = (grp['Tahmin-Ham (Milyon TL)'] * scale).round(0)

        # Düzeltilmiş tahmin (Seçenek 2): strateji × geçmiş gerçekleşme oranı
        realization_rate = self._recent_realization_rate(comparison_df)
        bt['Tahmin-Düzeltilmiş (Milyon TL)'] = (bt['Tahmin-Strateji (Milyon TL)'] * realization_rate).round(0)

        # Teklif, ileriye dönük yöntemle aynı: düzeltilmiş gerçekleşme × bid-to-cover
        bt['Tahmin Teklif (Milyon TL)'] = (bt['Tahmin-Düzeltilmiş (Milyon TL)'] * bt['Tahmin Bid-to-Cover']).round(0)

        # Sapma yüzdeleri
        def pct(f, a):
            return round((f - a) / a * 100, 1) if (pd.notna(f) and pd.notna(a) and a != 0) else None
        bt['Tutar Sapma % (düzeltilmiş)'] = bt.apply(lambda x: pct(x['Tahmin-Düzeltilmiş (Milyon TL)'], x['Gerçek Gerçekleşme (Milyon TL)']), axis=1)
        bt['Tutar Sapma % (strateji)'] = bt.apply(lambda x: pct(x['Tahmin-Strateji (Milyon TL)'], x['Gerçek Gerçekleşme (Milyon TL)']), axis=1)
        bt['Tutar Sapma % (ham)'] = bt.apply(lambda x: pct(x['Tahmin-Ham (Milyon TL)'], x['Gerçek Gerçekleşme (Milyon TL)']), axis=1)
        bt['B2C Sapma %'] = bt.apply(lambda x: pct(x['Tahmin Bid-to-Cover'], x['Gerçek Bid-to-Cover']), axis=1)
        bt['Teklif Sapma %'] = bt.apply(lambda x: pct(x['Tahmin Teklif (Milyon TL)'], x['Gerçek Teklif (Milyon TL)']), axis=1)

        bt = bt.drop(columns=['_ay'])
        logger.info(f"✓ Backtest: {len(bt)} geçmiş ihale tahmin edilip gerçekle kıyaslandı")
        return bt

    @staticmethod
    def _drop_invalid_date_rows(df: pd.DataFrame) -> pd.DataFrame:
        """İhale Tarihi'si geçersiz/boş olan satırları atar.

        Geçerli her ihale sonucunun bir ihale tarihi vardır; tarihsiz satırlar
        PDF parse artığıdır (ör. metin içinde ISIN'e benzeyen bir referans).
        """
        if df.empty or 'İhale Tarihi' not in df.columns:
            return df
        valid = pd.to_datetime(df['İhale Tarihi'], format='%d.%m.%Y', errors='coerce').notna()
        dropped = int((~valid).sum())
        if dropped:
            logger.info(f"Geçersiz tarihli {dropped} satır temizlendi (parse artığı)")
        return df[valid].reset_index(drop=True)

    def scrape_all_auctions(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Tüm ihale verilerini çeker ve analiz eder.

        İnkremental mod (FORCE_ALL_FETCH=False):
        - Mevcut Excel verisiyle birleştirir
        - Daha önce işlenmiş URL'leri atlar
        - ISIN bazlı dedup yapar
        """
        existing_isins = set()
        existing_df = None
        # BİRİKMİŞ GEÇMİŞ: önce Excel, YOKSA CSV.
        #
        # Excel .gitignore'da — depo yalnız CSV'yi taşıyor. Yerelde Excel hep
        # elde olduğu için bu hiç görünmedi; BULUTTA ise taze checkout'ta Excel
        # yok, existing_df None kalıyor ve artımlı tarama yalnız o koşuda
        # çekilen avuç dolusu ihaleyi döndürüyordu. Aşağıdaki to_csv da 448
        # satırlık birikmiş dosyayı 16 satırla EZİYORDU (25.08.2026 ve yeniden
        # 31.08.2026; ikincisinde yeni İç Borçlanma Stratejisi bu yüzden siteye
        # inemedi — guncelle.py'nin "VERİ GERİLEDİ" kapısı koşuyu reddetti).
        #
        # Yani kusur artımlı taramada değil, birikimin YANLIŞ DOSYADAN
        # okunmasındaydı: depoda duran sürüm CSV'dir, doğrusu odur.
        if not FORCE_ALL_FETCH:
            for yol, oku in ((EXCEL_OUTPUT, lambda f: pd.read_excel(f, sheet_name='İhale Verileri')),
                             (CSV_OUTPUT, lambda f: pd.read_csv(f, encoding='utf-8-sig'))):
                if not os.path.exists(yol):
                    continue
                try:
                    existing_df = oku(yol)
                except Exception as e:
                    logger.warning(f"Birikmiş veri okunamadı ({yol}): {e}")
                    existing_df = None
                    continue
                if existing_df is not None and not existing_df.empty:
                    if 'ISIN' in existing_df.columns:
                        existing_isins = set(existing_df['ISIN'].dropna().astype(str).unique())
                    logger.info(f"Birikmiş veri {yol}: {len(existing_isins)} ISIN, "
                                f"{len(existing_df)} satır okundu.")
                    break
            else:
                logger.warning("Birikmiş veri dosyası YOK (ne Excel ne CSV) — "
                               "bu koşu sıfırdan tarayacak.")

        all_auction_data = []
        comparison_df = pd.DataFrame()

        try:
            logger.info("İhale verisi çekme işlemi başlatılıyor...")
            start_time = time.time()

            # Duyuruları ve PDF linklerini API'den topla
            # auction_items: List[(announcement_url, pdf_url)]
            auction_items, strategy_pdfs = self.get_auction_announcement_urls()

            # En güncel strateji raporu (API en yeniden eskiye sıralı döner)
            if strategy_pdfs:
                self.newest_strategy_url = strategy_pdfs[0][0]

            if not auction_items:
                logger.warning("Hiç ihale sonucu duyurusu bulunamadı!")
                if existing_df is not None and not existing_df.empty:
                    logger.info("Mevcut veriler kullanılacak.")
                    return existing_df, pd.DataFrame()
                return pd.DataFrame(columns=self.fields), pd.DataFrame()

            # Cache'deki URL'leri filtrele (inkremental mod)
            if not FORCE_ALL_FETCH and self.processed_urls:
                new_items = [item for item in auction_items if item[0] not in self.processed_urls]
                skipped = len(auction_items) - len(new_items)
                if skipped > 0:
                    logger.info(f"URL cache'den {skipped} duyuru atlandı, {len(new_items)} yeni duyuru işlenecek")
                auction_items = new_items

            logger.info(f"İşlenecek: {len(auction_items)} duyuru, {len(strategy_pdfs)} strateji PDF")

            # Strateji PDF'lerini işle ve tarihsel cache'e ekle.
            # API en yeniden eskiye sıralı döner; en eskiden başlayıp en yeniye
            # doğru işleyerek (a) çakışan aylarda en güncel hedefin kazanmasını,
            # (b) strateji_history geçmişinin kronolojik sırada birikmesini sağlarız.
            # Daha önce işlenmiş strateji PDF'lerini TEKRAR İNDİRMEYİZ — verileri
            # zaten strateji_history'de kalıcı; yalnızca yeni raporlar indirilir.
            strategy_data = {}
            strategy_skipped = 0
            for pdf_url, baslik, ay_bilgi in reversed(strategy_pdfs):
                if not FORCE_ALL_FETCH and pdf_url in self.processed_urls:
                    strategy_skipped += 1
                    continue
                logger.info(f"Strateji PDF işleniyor: {baslik}")
                strat = self.extract_strategy_data(pdf_url)
                if strat:
                    strategy_data.update(strat)
                    self._update_strategy_history(strat, baslik)
                    self.processed_urls.add(pdf_url)
            if strategy_skipped:
                logger.info(f"{strategy_skipped} strateji PDF zaten işlenmiş, indirilmedi (cache)")

            # Tarihsel strateji verisini de birleştir (cache'deki tüm aylar).
            #
            # DİKKAT — bu yol CSV geri tohumlamasından ÖNCE ve BASKIN çalışır
            # (aşağıdaki seed `if key not in strategy_data` ile korunuyor). Burası
            # filtresiz kalırsa cache'e bir kez yazılmış bozuk bir hedef, CSV
            # yolundaki makullik filtresini TAMAMEN atlar. Bu yüzden aynı bant
            # kontrolü burada da uygulanır — filtre tek bir yolda değil, hedefin
            # strategy_data'ya girdiği HER yolda olmalı.
            history_rejected = []
            for month_key, info in self.strategy_history.items():
                if month_key in strategy_data:
                    continue
                hedef = info.get("target")
                try:
                    hedef = float(hedef)
                except (TypeError, ValueError):
                    history_rejected.append(f"{month_key}=? (sayı değil)")
                    continue
                if not (STRATEGY_TARGET_MIN <= hedef <= STRATEGY_TARGET_MAX):
                    history_rejected.append(f"{month_key}={hedef} (bant dışı)")
                    continue
                strategy_data[month_key] = hedef
            if history_rejected:
                logger.warning(
                    f"Strateji cache'inden {len(history_rejected)} ay reddedildi — "
                    f"makul olmayan hedef: {history_rejected}"
                )

            # Mevcut hedef/gerçekleşme CSV'sindeki tarihsel hedefleri koru.
            # (Geçmiş yıllara ait hedefler yalnızca bu çıktı dosyasında bulunabilir;
            #  strateji cache'i boşsa bile geçmiş veriyi kaybetmemek için seed ediyoruz.)
            #
            # DİKKAT — bu yol bir geri besleme döngüsüdür: CSV'yi bu hat üretir ve
            # aynı hat bir sonraki çalıştırmada CSV'den geri okur. Ayrıştırıcı
            # hatasıyla yazılmış bir değer, ayrıştırıcı düzeltilse bile buradan
            # geri tohumlanıp kendini yeniden üretir. Bu yüzden geri tohumlamayı
            # makullik filtresinden geçiriyoruz: gerçekleşme oranı bandın dışında
            # kalan satırların hedefi bozuk kabul edilir ve seed EDİLMEZ.
            if not FORCE_ALL_FETCH and os.path.exists(COMPARISON_CSV):
                try:
                    old_comp = pd.read_csv(COMPARISON_CSV, encoding='utf-8-sig')
                    seeded = 0
                    rejected = []
                    for _, row in old_comp.iterrows():
                        ay_yil = str(row.get('Ay-Yıl', '')).strip()
                        if not ay_yil or ay_yil.lower() == 'nan':
                            continue
                        parts = ay_yil.split()
                        key = f"{normalize_month_name(parts[0])} {parts[1]}" if len(parts) == 2 else ay_yil
                        if key not in strategy_data:
                            try:
                                hedef = float(row['Hedef Borçlanma (Milyar TL)'])
                            except (ValueError, TypeError, KeyError):
                                continue
                            if not (STRATEGY_TARGET_MIN <= hedef <= STRATEGY_TARGET_MAX):
                                rejected.append(f"{key}={hedef} (bant dışı)")
                                continue
                            # Gerçekleşme oranı çapraz kontrolü: gerçekleşen 0 ise
                            # (gelecek ay) kontrol uygulanmaz.
                            gercek = pd.to_numeric(
                                row.get('Gerçekleşen Borçlanma (Milyar TL)'), errors='coerce')
                            if pd.notna(gercek) and gercek > 0 and hedef > 0:
                                oran = gercek / hedef * 100
                                if not (SEED_MIN_REALIZATION_PCT <= oran <= SEED_MAX_REALIZATION_PCT):
                                    rejected.append(f"{key}={hedef} (gerçekleşme %{oran:.1f})")
                                    continue
                            strategy_data[key] = hedef
                            seeded += 1
                    if seeded:
                        logger.info(f"Mevcut hedef CSV'sinden {seeded} tarihsel hedef korundu")
                    if rejected:
                        logger.warning(
                            f"CSV'den geri tohumlama reddedildi ({len(rejected)} ay) — "
                            f"makul olmayan tarihsel hedef: {rejected}"
                        )
                except Exception as e:
                    logger.warning(f"Mevcut hedef CSV okunamadı: {e}")

            logger.info(f"Toplam strateji verisi: {len(strategy_data)} ay (yeni + tarihsel)")

            # PDF linkleri zaten API içeriğinden geldi — doğrudan topla
            # (artık duyuru başına ayrı sayfa ziyareti / Selenium gerekmiyor)
            pdf_urls_to_process = []
            for announcement_url, pdf_url in auction_items:
                pdf_urls_to_process.append(pdf_url)
                self.processed_urls.add(announcement_url)

            # PDF'leri paralel olarak işle
            if pdf_urls_to_process:
                logger.info(f"\n{'='*60}")
                logger.info(f"PARALEL PDF İŞLEME BAŞLIYOR: {len(pdf_urls_to_process)} PDF")
                logger.info(f"{'='*60}")

                all_auction_data = self._process_pdf_batch_parallel(pdf_urls_to_process)

                # ISIN+Tarih kontrolü (mevcut verilerle çakışmayı önle)
                # NOT: Sadece ISIN kontrolü yanlış, çünkü aynı ISIN farklı tarihlerde tekrar ihraç edilebilir (ROT)
                if not FORCE_ALL_FETCH and existing_df is not None and not existing_df.empty:
                    existing_keys = set(
                        zip(existing_df['ISIN'].astype(str), existing_df['İhale Tarihi'].astype(str))
                    )
                    before_count = len(all_auction_data)
                    all_auction_data = [
                        d for d in all_auction_data
                        if (str(d.get('ISIN', '')), str(d.get('İhale Tarihi', ''))) not in existing_keys
                    ]
                    skipped = before_count - len(all_auction_data)
                    if skipped > 0:
                        logger.info(f"ISIN+Tarih dedup: {skipped} mevcut kayıt atlandı")

            # URL cache'i kaydet
            self._save_url_cache()

            elapsed = time.time() - start_time
            logger.info(f"\nToplam süre: {elapsed:.1f} saniye")

        except Exception as e:
            logger.error(f"Ana işlem sırasında hata: {str(e)}")

        # Yeni veriyi mevcut veriyle birleştir
        if all_auction_data:
            new_df = pd.DataFrame(all_auction_data)

            # Sayısal sütunları dönüştür
            numeric_columns = [col for col in new_df.columns if any(x in col for x in ['Teklif', 'Gerçekleşme', 'Fiyat', 'Oranı', 'Vade'])]
            for col in numeric_columns:
                new_df[col] = pd.to_numeric(new_df[col], errors='coerce')

            # Mevcut veriyle birleştir
            if existing_df is not None and not existing_df.empty:
                df = pd.concat([existing_df, new_df], ignore_index=True)
                df = df.drop_duplicates(subset=['ISIN', 'İhale Tarihi'], keep='last')
                # Tarihe göre sırala
                df['_sort'] = pd.to_datetime(df['İhale Tarihi'], format='%d.%m.%Y', errors='coerce')
                df = df.sort_values('_sort', ascending=False).drop('_sort', axis=1).reset_index(drop=True)
                logger.info(f"\n{'='*60}")
                logger.info(f"✓ BAŞARIYLA TAMAMLANDI!")
                logger.info(f"✓ {len(new_df)} yeni + {len(existing_df)} mevcut = {len(df)} toplam ihale verisi")
                logger.info(f"{'='*60}")
            else:
                df = new_df
                logger.info(f"\n{'='*60}")
                logger.info(f"✓ BAŞARIYLA TAMAMLANDI!")
                logger.info(f"✓ Toplam {len(df)} ihale verisi çekildi")
                logger.info(f"{'='*60}")

            # Geçersiz tarihli parse artıklarını temizle
            df = self._drop_invalid_date_rows(df)

            if strategy_data and self.analyze_strategy:
                logger.info(f"Strateji verisi mevcut: {len(strategy_data)} ay")
                comparison_df = self.analyze_borrowing_performance(df, strategy_data)

            return df, comparison_df

        elif existing_df is not None and not existing_df.empty:
            logger.info("Yeni veri yok, mevcut veriler korunuyor.")
            df = self._drop_invalid_date_rows(existing_df)
            if strategy_data and self.analyze_strategy:
                comparison_df = self.analyze_borrowing_performance(df, strategy_data)
            return df, comparison_df
        else:
            logger.error("✗ HİÇ VERİ BULUNAMADI!")
            return pd.DataFrame(columns=self.fields), pd.DataFrame()

    def calculate_weighted_average_maturity(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ağırlıklı ortalama vade hesaplar"""
        if df.empty or 'İhale Tarihi' not in df.columns:
            return pd.DataFrame()
        
        df_copy = df.copy()
        df_copy['İhale Tarihi'] = pd.to_datetime(df_copy['İhale Tarihi'], format='%d.%m.%Y', errors='coerce')
        df_copy.dropna(subset=['İhale Tarihi', 'Vade (Yıl)', 'Toplam(Gerçekleşme)'], inplace=True)
        
        if df_copy.empty:
            return pd.DataFrame()
        
        df_copy['Yıl-Ay'] = df_copy['İhale Tarihi'].dt.to_period('M')
        
        monthly_wam = []
        for period in df_copy['Yıl-Ay'].unique():
            if pd.notna(period):
                month_data = df_copy[df_copy['Yıl-Ay'] == period]
                total_realized = month_data['Toplam(Gerçekleşme)'].sum()
                
                if total_realized > 0:
                    weighted_sum = (month_data['Vade (Yıl)'] * month_data['Toplam(Gerçekleşme)']).sum()
                    wam = weighted_sum / total_realized
                    
                    monthly_wam.append({
                        'Dönem': period,
                        'Tarih': period.to_timestamp(),
                        'Ağırlıklı Ortalama Vade (Yıl)': round(wam, 2),
                        'Toplam İhraç (Milyon TL)': round(total_realized, 2),
                        'İhale Sayısı': len(month_data)
                    })
        
        if not monthly_wam:
            return pd.DataFrame()
        
        wam_df = pd.DataFrame(monthly_wam).sort_values('Tarih')
        
        # 3 Aylık Ağırlıklı Ortalama Vade
        weighted_3mo = []
        for i in range(len(wam_df)):
            sub = wam_df.iloc[max(0, i-2):i+1]
            total_ihrac = sub['Toplam İhraç (Milyon TL)'].sum()
            if total_ihrac > 0:
                weighted_avg = (sub['Ağırlıklı Ortalama Vade (Yıl)'] * sub['Toplam İhraç (Milyon TL)']).sum() / total_ihrac
                weighted_3mo.append(round(weighted_avg, 2))
            else:
                weighted_3mo.append(None)
        
        wam_df['3 Aylık Ağırlıklı Ortalama Vade'] = weighted_3mo
        return wam_df

    def create_maturity_charts(self, wam_df: pd.DataFrame, output_file: str = "vade_analizi.html"):
        """Vade analizi grafiklerini oluşturur.

        Ev stili: tarih ekseni (otomatik yıl tikleri), ev paleti
        (teal #1d5c5c ana seri, bordo #8e1f2f ikincil seri, gri bar),
        2px düz çizgiler, lejant grafiğin altında yatay.
        """
        if wam_df.empty:
            logger.warning("Vade verisi bulunamadı, grafik oluşturulamadı")
            return

        wam_df = wam_df.copy()
        wam_df['Tarih'] = pd.to_datetime(wam_df['Tarih'])
        wam_df = wam_df.sort_values('Tarih')

        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Aylık ağırlıklı ortalama vade ve ihraç miktarı',
                            '3 aylık hareketli ağırlıklı ortalama vade'),
            vertical_spacing=0.16,
            specs=[[{"secondary_y": True}], [{"secondary_y": False}]]
        )

        # bar önce çizilir ki teal çizgi üstte kalsın
        fig.add_trace(
            go.Bar(
                x=wam_df['Tarih'], y=wam_df['Toplam İhraç (Milyon TL)'],
                name='İhraç miktarı (milyon TL, sağ eksen)',
                marker_color='rgba(144,164,174,0.45)',
                hovertemplate='İhraç: %{y:,.0f} milyon TL<extra></extra>'
            ),
            row=1, col=1, secondary_y=True
        )

        fig.add_trace(
            go.Scatter(
                x=wam_df['Tarih'], y=wam_df['Ağırlıklı Ortalama Vade (Yıl)'],
                mode='lines', name='Aylık ağırlıklı vade (yıl)',
                line=dict(color='#1d5c5c', width=2),
                hovertemplate='Ağırlıklı vade: %{y:.2f} yıl<extra></extra>'
            ),
            row=1, col=1, secondary_y=False
        )

        fig.add_trace(
            go.Scatter(
                x=wam_df['Tarih'], y=wam_df['3 Aylık Ağırlıklı Ortalama Vade'],
                mode='lines', name='3 aylık ağırlıklı ortalama (yıl)',
                line=dict(color='#8e1f2f', width=2),
                hovertemplate='3 aylık ort.: %{y:.2f} yıl<extra></extra>'
            ),
            row=2, col=1
        )

        fig.update_layout(
            title=dict(text='Türkiye Hazinesi — borçlanma vade analizi',
                       x=0.02, xanchor='left',
                       font=dict(size=16, color='#211b12')),
            height=760, showlegend=True, hovermode='x unified',
            paper_bgcolor='#ffffff', plot_bgcolor='#ffffff',
            font=dict(color='#211b12', size=12.5),
            legend=dict(orientation='h', yanchor='top', y=-0.1,
                        xanchor='left', x=0),
            margin=dict(t=72, r=64, b=96, l=64),
        )
        for a in fig.layout.annotations:
            a.font = dict(size=13, color='#211b12')

        fig.update_yaxes(title_text="Vade (yıl)", row=1, col=1, secondary_y=False)
        fig.update_yaxes(title_text="Milyon TL", row=1, col=1, secondary_y=True, showgrid=False)
        fig.update_yaxes(title_text="Vade (yıl)", row=2, col=1)
        fig.update_xaxes(hoverformat='%m.%Y',
                         gridcolor='#efe9dc', linecolor='#d8cfba')
        fig.update_yaxes(gridcolor='#efe9dc', linecolor='#d8cfba')

        fig.write_html(output_file, include_plotlyjs='cdn')
        logger.info(f"✓ Vade analizi grafikleri {output_file} dosyasına kaydedildi")
        
        # Özet log
        logger.info("\n" + "="*60)
        logger.info("VADE ANALİZİ ÖZETİ")
        logger.info("="*60)
        logger.info(f"Ortalama Vade: {wam_df['Ağırlıklı Ortalama Vade (Yıl)'].mean():.2f} yıl")
        logger.info(f"En Kısa Vade: {wam_df['Ağırlıklı Ortalama Vade (Yıl)'].min():.2f} yıl")
        logger.info(f"En Uzun Vade: {wam_df['Ağırlıklı Ortalama Vade (Yıl)'].max():.2f} yıl")
        if not wam_df.empty:
            logger.info(f"Son 3 Ay Ağırlıklı Ortalaması: {wam_df['3 Aylık Ağırlıklı Ortalama Vade'].iloc[-1]:.2f} yıl")
        
        return fig

    def create_borrowing_performance_chart(self, comparison_df: pd.DataFrame, output_file: str = "hedef_gerceklesme.html"):
        """Hedef vs gerçekleşme grafiğini oluşturur.

        Ev stili tasarım (79 aylık seri için okunabilirlik):
        - Tarih ekseni: kategori etiketi basılmaz, Plotly otomatik yıl tikleri atar.
        - Hedef = ince gri (#90a4ae) konturlu içi boş bar, gerçekleşen = teal
          (#1d5c5c) dolu bar; overlay — 79 dönemde iki dolu barı yan yana
          sıkıştırmak okunmuyor.
        - Oran = bordo (#8e1f2f) 2px düz çizgi, sağ eksen [0,150] dtick 25.
          %150'yi aşan oranlar 150'de üçgenle işaretlenir; hover gerçek değeri
          gösterir (customdata). Gelecek (gerçekleşmesi 0) aylarda çizgi kesilir.
        - Bar üstü metin etiketi yok (hover yeterli); lejant altta yatay.
        """
        if comparison_df is None or comparison_df.empty:
            logger.warning("Hedef/gerçekleşme verisi yok, grafik oluşturulamadı")
            return

        def parse_ay_yil(s):
            ay_mapping = {
                'Ocak': 1, 'Şubat': 2, 'Mart': 3, 'Nisan': 4, 'Mayıs': 5, 'Haziran': 6,
                'Temmuz': 7, 'Ağustos': 8, 'Eylül': 9, 'Ekim': 10, 'Kasım': 11, 'Aralık': 12,
                'Hazi̇ran': 6, 'Mayis': 5, 'Ni̇san': 4, 'Eki̇m': 10
            }
            m = re.match(r"([A-Za-zçğıöşüÇĞİÖŞÜ]+) (\d{4})", str(s))
            if m:
                ay, yil = m.group(1), int(m.group(2))
                ay_num = ay_mapping.get(ay, 1)
                return pd.Timestamp(year=yil, month=ay_num, day=1)
            return pd.Timestamp.min

        df = comparison_df.copy()
        df['Tarih'] = df['Ay-Yıl'].apply(parse_ay_yil)
        df = df.sort_values('Tarih').reset_index(drop=True)

        hedef = pd.to_numeric(df['Hedef Borçlanma (Milyar TL)'], errors='coerce')
        gercek = pd.to_numeric(df['Gerçekleşen Borçlanma (Milyar TL)'], errors='coerce')
        oran = pd.to_numeric(df['Gerçekleşme Oranı (%)'], errors='coerce')
        oran = oran.where(gercek > 0)          # gelecek aylarda çizgide boşluk
        oran_cizim = oran.clip(upper=150)      # aşanlar 150'de; gerçek değer hover'da

        AY_MS = 86_400_000 * 30  # tarih ekseninde bar genişliği (ms cinsinden ~1 ay)

        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=df['Tarih'], y=hedef.round(1),
            name='Hedef borçlanma',
            width=AY_MS * 0.78,
            marker=dict(color='rgba(0,0,0,0)',
                        line=dict(color='#90a4ae', width=1.3)),
            hovertemplate='Hedef: %{y:.1f} milyar TL<extra></extra>'
        ))

        fig.add_trace(go.Bar(
            x=df['Tarih'], y=gercek.round(1),
            name='Gerçekleşen borçlanma',
            width=AY_MS * 0.5,
            marker_color='#1d5c5c',
            hovertemplate='Gerçekleşen: %{y:.1f} milyar TL<extra></extra>'
        ))

        fig.add_trace(go.Scatter(
            x=df['Tarih'], y=oran_cizim.round(1),
            name='Gerçekleşme oranı (%, sağ eksen)',
            mode='lines', yaxis='y2',
            line=dict(color='#8e1f2f', width=2),
            customdata=oran.round(1),
            hovertemplate='Oran: %{customdata:.1f}%<extra></extra>'
        ))

        askin = oran > 150
        if askin.any():
            fig.add_trace(go.Scatter(
                x=df.loc[askin, 'Tarih'], y=[150] * int(askin.sum()),
                yaxis='y2', mode='markers',
                name='Oran > %150 (gerçek değer hover\'da)',
                marker=dict(symbol='triangle-up', size=8, color='#8e1f2f'),
                customdata=oran[askin].round(1),
                hovertemplate='Oran: %{customdata:.1f}% (eksende 150\'de kırpıldı)<extra></extra>'
            ))

        fig.update_layout(
            title=dict(text='Hazine borçlanma hedefi vs gerçekleşme',
                       x=0.02, xanchor='left',
                       font=dict(size=16, color='#211b12')),
            barmode='overlay',
            height=560,
            paper_bgcolor='#ffffff', plot_bgcolor='#ffffff',
            font=dict(color='#211b12', size=12.5),
            hovermode='x unified',
            xaxis=dict(type='date', hoverformat='%m.%Y',
                       gridcolor='#efe9dc', linecolor='#d8cfba'),
            yaxis=dict(title='Borçlanma (milyar TL)',
                       gridcolor='#efe9dc', linecolor='#d8cfba'),
            yaxis2=dict(title='Gerçekleşme oranı (%)', overlaying='y',
                        side='right', showgrid=False,
                        range=[0, 150], dtick=25),
            legend=dict(orientation='h', yanchor='top', y=-0.12,
                        xanchor='left', x=0),
            margin=dict(t=72, r=64, b=96, l=64),
        )

        fig.write_html(output_file, include_plotlyjs='cdn')
        logger.info(f"✓ Hedef/gerçekleşme grafiği {output_file} dosyasına kaydedildi")
        return fig

    def save_to_excel(self, df: pd.DataFrame, comparison_df: Optional[pd.DataFrame], wam_df: Optional[pd.DataFrame], filename: str = "hazine_ihale_verileri.xlsx"):
        """Verileri Excel dosyasına kaydeder"""
        try:
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                if df is not None and not df.empty:
                    df.to_excel(writer, index=False, sheet_name='İhale Verileri')
                    worksheet = writer.sheets['İhale Verileri']
                    for idx, col in enumerate(df.columns):
                        max_len = max(df[col].astype(str).map(len).max(), len(str(col))) + 2
                        worksheet.column_dimensions[worksheet.cell(1, idx + 1).column_letter].width = min(max_len, 50)
                
                if comparison_df is not None and not comparison_df.empty:
                    comparison_df.to_excel(writer, index=False, sheet_name='Hedef vs Gerçekleşme')
                    worksheet = writer.sheets['Hedef vs Gerçekleşme']
                    for idx, col in enumerate(comparison_df.columns):
                        max_len = max(comparison_df[col].astype(str).map(len).max(), len(str(col))) + 2
                        worksheet.column_dimensions[worksheet.cell(1, idx + 1).column_letter].width = min(max_len, 40)
                
                if wam_df is not None and not wam_df.empty:
                    wam_df.to_excel(writer, index=False, sheet_name='Vade Analizi')
                    worksheet = writer.sheets['Vade Analizi']
                    for idx, col in enumerate(wam_df.columns):
                        max_len = max(wam_df[col].astype(str).map(len).max(), len(str(col))) + 2
                        worksheet.column_dimensions[worksheet.cell(1, idx + 1).column_letter].width = min(max_len, 40)
            
            logger.info(f"✓ Veriler başarıyla {filename} dosyasına kaydedildi.")
        except Exception as e:
            logger.error(f"Excel dosyası kaydedilirken hata: {str(e)}")


# =====================
# ANA İŞ AKIŞI
# =====================
def main():
    """Ana fonksiyon - Tüm iş akışını yönetir"""
    try:
        print(f"\n{'='*60}")
        print("TÜRKIYE HAZİNESİ İHALE VERİLERİ SCRAPER")
        print(f"{'='*60}")
        print(f"Performans ayarları:")
        print(f"  - Veri kaynağı: WordPress REST API (Selenium kullanılmıyor)")
        print(f"  - Paralel indirme/parse: {MAX_WORKERS}")
        print(f"  - Async PDF indirme: {'Aktif' if USE_ASYNC else 'Pasif'}")
        print(f"{'='*60}\n")

        # Scraper'ı başlat
        scraper = TreasuryAuctionScraper(
            max_pages=MAX_PAGES,
            analyze_strategy=ANALYZE_STRATEGY
        )
        
        # Tüm ihale verilerini çek ve analiz et
        df, comparison_df = scraper.scrape_all_auctions()

        if not df.empty:
            print(f"\n{'='*60}")
            print(f"✓ BAŞARILI! Toplam {len(df)} ihale verisi çekildi")
            print(f"{'='*60}")
            
            # Özet bilgileri göster
            print("\nÇekilen ISIN kodları:")
            unique_isins = df.groupby('ISIN').agg({
                'Senet Tanımı': 'first',
                'İhale Tarihi': 'count'
            }).reset_index()
            unique_isins.columns = ['ISIN', 'Senet Tanımı', 'İhale Sayısı']
            for idx, row in unique_isins.iterrows():
                print(f"{idx + 1}. {row['ISIN']} - {row['Senet Tanımı']} ({row['İhale Sayısı']} ihale)")
            
            # Hedef vs Gerçekleşme tablosu
            if not comparison_df.empty:
                print(f"\n{'='*60}")
                print("HEDEF VS GERÇEKLEŞME ANALİZİ")
                print(f"{'='*60}")
                print(comparison_df.to_string(index=False))
                
                last_row = comparison_df.iloc[-1]
                remaining = last_row['Hedef Borçlanma (Milyar TL)'] - last_row['Gerçekleşen Borçlanma (Milyar TL)']
                if remaining > 0:
                    print(f"\n⚠ {last_row['Ay-Yıl']} ayı için kalan borçlanma hedefi: {round(remaining, 2)} Milyar TL")
            
            # Ağırlıklı ortalama vade analizi
            print(f"\n{'='*60}")
            print("AĞIRLIKLI ORTALAMA VADE ANALİZİ")
            print(f"{'='*60}")
            wam_df = scraper.calculate_weighted_average_maturity(df)
            
            if not wam_df.empty:
                print(wam_df[['Dönem', 'Ağırlıklı Ortalama Vade (Yıl)', '3 Aylık Ağırlıklı Ortalama Vade', 'Toplam İhraç (Milyon TL)']].to_string(index=False))
                scraper.create_maturity_charts(wam_df, output_file=HTML_OUTPUT)
                print(f"\n✓ Vade analizi grafikleri '{HTML_OUTPUT}' dosyasına kaydedildi")
            else:
                print("Vade analizi için yeterli veri bulunamadı")
            
            # Hedef/gerçekleşme grafiği
            scraper.create_borrowing_performance_chart(comparison_df, output_file=HEDEF_GERCEKLESME_HTML)
            print(f"\n✓ Hedef/gerçekleşme grafiği '{HEDEF_GERCEKLESME_HTML}' dosyasına kaydedildi")
            
            # Önümüzdeki planlı ihraçlar + tahminler (strateji-tutarlı + bid-to-cover)
            planned_df = scraper.build_planned_issuances(df, scraper.newest_strategy_url, comparison_df)
            if not planned_df.empty:
                print(f"\n{'='*60}")
                print("ÖNÜMÜZDEKİ PLANLI İHRAÇLAR + TAHMİNLER")
                print(f"{'='*60}")
                show_cols = ['İhale Tarihi', 'Senet Tanımı', 'Yöntem',
                             'Tahmini Bid-to-Cover', 'Tahmini Gerçekleşme (Milyon TL)',
                             'Tahmini Teklif (Milyon TL)']
                print(planned_df[show_cols].to_string(index=False))

            # Excel ve CSV'ye kaydet
            # SON KAPI: birikmiş dosyayı KÜÇÜLTEREK yazma. Yukarıdaki
            # birleştirme doğru çalışıyorsa bu satır hiç tetiklenmez; ama
            # aynı hasar iki kez yaşandığı için tek katmanlı sigortaya
            # güvenilmiyor. Küçülme bir hata değil, bir VERİ KAYBIDIR.
            if os.path.exists(CSV_OUTPUT):
                try:
                    _n_eski = len(pd.read_csv(CSV_OUTPUT, encoding='utf-8-sig'))
                except Exception:
                    _n_eski = 0
                if _n_eski and len(df) < _n_eski:
                    raise SystemExit(
                        f"YAZMA REDDEDİLDİ — birikmiş {_n_eski} ihale, yazılacak "
                        f"{len(df)}. Kaynak eksik veri döndürmüş olabilir; "
                        f"depodaki dosya korunuyor.")
            scraper.save_to_excel(df, comparison_df, wam_df, filename=EXCEL_OUTPUT)
            df.to_csv(CSV_OUTPUT, index=False, encoding='utf-8-sig')

            if not comparison_df.empty:
                comparison_df.to_csv(COMPARISON_CSV, index=False, encoding='utf-8-sig')
            if not wam_df.empty:
                wam_df.to_csv(WADE_CSV, index=False, encoding='utf-8-sig')
            if not planned_df.empty:
                planned_df.to_csv(PLANNED_CSV, index=False, encoding='utf-8-sig')

            # Backtest: geçmiş ihalelerde tahmin vs gerçek (yöntemin isabeti)
            backtest_df = scraper.backtest_forecasts(df, comparison_df)
            if not backtest_df.empty:
                backtest_df.to_csv(BACKTEST_CSV, index=False, encoding='utf-8-sig')
                import numpy as _np
                def _mape(col_f, col_a):
                    m = backtest_df[col_a].notna() & backtest_df[col_f].notna() & (backtest_df[col_a] != 0)
                    return float(_np.abs((backtest_df.loc[m, col_f] - backtest_df.loc[m, col_a]) / backtest_df.loc[m, col_a]).mean() * 100) if m.any() else float('nan')
                print(f"\n{'='*60}")
                print("TAHMİN DOĞRULAMA (BACKTEST) — geçmiş ihalelerde sapma")
                print(f"{'='*60}")
                print(f"  Backtest edilen ihale: {len(backtest_df)}")
                print(f"  Tutar MAPE (düzeltilmiş — Seçenek 2): %{_mape('Tahmin-Düzeltilmiş (Milyon TL)','Gerçek Gerçekleşme (Milyon TL)'):.1f}")
                print(f"  Tutar MAPE (ham):                     %{_mape('Tahmin-Ham (Milyon TL)','Gerçek Gerçekleşme (Milyon TL)'):.1f}")
                print(f"  Tutar MAPE (saf strateji):            %{_mape('Tahmin-Strateji (Milyon TL)','Gerçek Gerçekleşme (Milyon TL)'):.1f}")
                print(f"  Bid-to-Cover MAPE:                    %{_mape('Tahmin Bid-to-Cover','Gerçek Bid-to-Cover'):.1f}")

            print(f"\n✓ Veriler kaydedildi:")
            print(f"  - {EXCEL_OUTPUT}")
            print(f"  - {CSV_OUTPUT}")
            if not comparison_df.empty:
                print(f"  - {COMPARISON_CSV}")
            if not wam_df.empty:
                print(f"  - {WADE_CSV}")
                print(f"  - {HTML_OUTPUT} (interaktif grafikler)")
            if not planned_df.empty:
                print(f"  - {PLANNED_CSV} ({len(planned_df)} planlı ihraç + tahmin)")
            if not backtest_df.empty:
                print(f"  - {BACKTEST_CSV} ({len(backtest_df)} geçmiş ihale backtest)")
        else:
            print(f"\n{'='*60}")
            print(f"✗ HİÇ VERİ ÇEKİLEMEDİ!")
            print(f"{'='*60}")
            
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"✗ HATA: {str(e)}")
        print(f"{'='*60}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
