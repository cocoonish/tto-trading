"""
Türkiye Reel Efektif Döviz Kuru Analizi
- %30 PPI (Yi-ÜFE) + %70 CPI (TÜFE) bazlı ağırlıklı REDK
  (ağırlıklar aşağıdaki PPI_WEIGHT / CPI_WEIGHT ile parametrik)
- 10 yıllık hareketli ortalamadan % sapma hesaplama
- Plotly ile interaktif görselleştirme
"""

import json
import os
import sys
from datetime import date, datetime
from urllib.parse import urlencode

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ============================================
# PARAMETRİK DEĞİŞKENLER (Kolay değiştirilebilir)
# ============================================

# Tüm yollar script klasörüne göre — hangi dizinden çalıştırılırsa çalıştırılsın bulunur
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Dosya yolları (EVDS erişilemezse kullanılan YEDEK kaynak)
CPI_FILE = os.path.join(SCRIPT_DIR, "TUFE.xlsx")  # CPI bazlı REDK dosyası
PPI_FILE = os.path.join(SCRIPT_DIR, "Yi-UFE.xlsx")  # PPI bazlı REDK dosyası

# ============================================
# EVDS (TCMB) — BİRİNCİL VERİ KAYNAĞI
# ============================================
# Seri kodları EVDS kategori 2504 (REEL EFEKTİF DÖVİZ KURLARI) altındaki
# veri gruplarından doğrulandı:
#   bie_rktufey → TP.RK.T1.Y  "TÜFE Bazlı Reel Efektif Döviz Kuru (2025=100)"
#   bie_rkufey  → TP.RK.U01.Y "Yİ-ÜFE Bazlı Reel Efektif Döviz Kuru (2025=100)"
# Her ikisi de 01-1994'ten itibaren aylık. Elle indirilen TUFE.xlsx / Yi-UFE.xlsx
# ile aynı serilerdir (2026-02 için fark 0,01 puan); Excel yolu yedek olarak durur.
EVDS_BASE = "https://evds3.tcmb.gov.tr/igmevdsms-dis"
EVDS_CPI_SERIES = "TP.RK.T1.Y"    # TÜFE bazlı REDK
EVDS_PPI_SERIES = "TP.RK.U01.Y"   # Yİ-ÜFE bazlı REDK
EVDS_START = "01-01-1994"

# EVDS anahtarı KAYNAĞA GÖMÜLMEZ. Sırayla iki yerden okunur:
#   1) TTO_EVDS_KEY ortam değişkeni (CI: depo secret'ı)
#   2) proje klasöründeki .evds_key dosyası (yerel; .gitignore'da)
# İkisi de yoksa EVDS yolu hiç denenmez ve ekrana açık bir uyarı basılır.
EVDS_KEY_FILE = os.path.join(SCRIPT_DIR, ".evds_key")


def _evds_anahtari_oku():
    """EVDS anahtarını ortam değişkeninden ya da yerel .evds_key dosyasından oku.

    Dönüş: (anahtar, nereden) — anahtar yoksa (None, None).
    """
    anahtar = (os.environ.get("TTO_EVDS_KEY") or "").strip()
    if anahtar:
        return anahtar, "ortam değişkeni TTO_EVDS_KEY"
    # Okuma korumalı: bu fonksiyon MODÜL IMPORT'unda çalışıyor. Dosya okunamazsa
    # (izin, dizin olması, bozuk kodlama) korumasız open() import'u düşürür ve
    # `from main import load_data` yapan usdtry_reer_analysis.py'yi de yanında
    # götürür — hâlbuki anahtar yoksa Excel yedeğiyle devam edebilmeliyiz.
    if os.path.exists(EVDS_KEY_FILE):
        try:
            with open(EVDS_KEY_FILE, encoding="utf-8") as f:
                anahtar = f.read().strip()
        except OSError as e:
            print(f"   ⚠ {EVDS_KEY_FILE} okunamadı ({type(e).__name__}); "
                  f"anahtarsız devam ediliyor.", file=sys.stderr)
            return None, None
        if anahtar:
            return anahtar, EVDS_KEY_FILE
    return None, None


EVDS_KEY, EVDS_KEY_KAYNAGI = _evds_anahtari_oku()


def _gizle_anahtar(metin: str) -> str:
    """Hata mesajlarındaki ham anahtarı maskele.

    requests, bozuk bir başlık değerinde (ör. anahtarda satır sonu) istisna
    metnine başlığın HAM içeriğini gömer; o metin log'a basılınca anahtar
    stderr'e sızar. Anahtarı basmadan önce her zaman buradan geçir.
    """
    if EVDS_KEY and len(EVDS_KEY) >= 4:
        return metin.replace(EVDS_KEY, f"{EVDS_KEY[:2]}***{EVDS_KEY[-2:]}")
    return metin

# Veri kaynağı seçimi: "evds" (varsayılan) | "excel"
VERI_KAYNAGI = os.environ.get("TTO_REDK_KAYNAK", "evds").strip().lower()

# ============================================
# TAZELİK DENETİMİ
# ============================================
# TCMB REDK'yi ay kapanışını izleyen ayın ilk günlerinde yayımlar; yani normalde
# son gözlem "içinde bulunulan ay − 1"dir. Bu eşikten FAZLA geride kalan seri
# "bayat" sayılır — Excel yedeği elle indirildiği için tipik olarak aylarca geridir.
TAZELIK_ESIGI_AY = 2
# Bayat veriyle bilerek çıktı üretmek için: TTO_BAYAT_VERI_IZIN=1
BAYAT_VERI_IZIN = os.environ.get("TTO_BAYAT_VERI_IZIN", "").strip() == "1"

# Kaynak damgası (ozet_uret.py buradan okur)
KAYNAK_DAMGASI_JSON = os.path.join(SCRIPT_DIR, "kaynak_damgasi.json")

# Ağırlıklar (toplam 1.0 olmalı)
PPI_WEIGHT = 0.30  # PPI (Yi-ÜFE) ağırlığı
CPI_WEIGHT = 0.70  # CPI (TÜFE) ağırlığı

# Hareketli ortalama pencereleri (ay cinsinden)
MA_WINDOW_10Y = 120  # 10 yıllık hareketli ortalama
MA_WINDOW_5Y = 60    # 5 yıllık hareketli ortalama

# Çıktı dosyası
OUTPUT_HTML = os.path.join(SCRIPT_DIR, "reer_analysis.html")

# Ev paleti (site/src/styles/global.css ile uyumlu)
TEAL = "#1d5c5c"       # birincil seri
BORDO = "#8e1f2f"      # ikincil / pozitif sapma (pahalı TL)
ALTIN = "#9a7327"      # vurgu
MUREKKEP = "#211b12"   # nötr çizgi
BORDO_KENAR = "rgba(142, 31, 47, 0.8)"
BORDO_DOLGU = "rgba(142, 31, 47, 0.3)"
TEAL_KENAR = "rgba(29, 92, 92, 0.8)"
TEAL_DOLGU = "rgba(29, 92, 92, 0.3)"

# ============================================
# VERİ YÜKLEME VE İŞLEME
# ============================================

def _uyar(baslik, satirlar=()):
    """Görünür uyarı bloğu — stdout'a değil stderr'e; log akışında kaybolmasın."""
    print("", file=sys.stderr)
    print("!" * 78, file=sys.stderr)
    print(f"!! {baslik}", file=sys.stderr)
    for s in satirlar:
        print(f"!! {s}", file=sys.stderr)
    print("!" * 78, file=sys.stderr)
    print("", file=sys.stderr, flush=True)


def _ay_basina_normalize(seri):
    """Tarih serisini ayın ilk gününe çek.

    Excel dosyalarında ay başı OLMAYAN hücreler var (TUFE/Yi-ÜFE satır 230 =
    2013-03-02; Yi-ÜFE satır 235 = 2013-08-02). Birleştirme datetime eşitliği
    aradığı için normalize edilmezse o aylar sessizce düşer.
    """
    return pd.to_datetime(seri).dt.to_period("M").dt.to_timestamp()


def _gecikme_ay(son_gozlem, bugun=None):
    """Son gözlemin bugüne göre kaç ay geride kaldığı (ay farkı)."""
    bugun = bugun or date.today()
    return (bugun.year - son_gozlem.year) * 12 + (bugun.month - son_gozlem.month)


def _takvim_bosluklari(donem):
    """Aylık seride eksik takvim aylarını döndür: ['2013-08', ...]"""
    idx = pd.PeriodIndex(pd.to_datetime(donem).dt.to_period("M"))
    tam = pd.period_range(idx.min(), idx.max(), freq="M")
    return [str(p) for p in tam.difference(idx)]


def fetch_evds_series(series_code, start=EVDS_START, end=None):
    """EVDS'ten tek bir aylık seriyi çek → pd.Series (index: ay başı Timestamp).

    USDTRYDeval/usdtry_deval_plotly.py içindeki fetch_evds ile aynı kalıp;
    aylık seriler 'YYYY-M' formatında Tarih döndürdüğü için ay başına çevrilir.
    """
    import requests  # yalnız EVDS yolunda gerekli — Excel yolu bağımsız kalsın

    if not EVDS_KEY:
        raise RuntimeError(
            "EVDS anahtarı yok: TTO_EVDS_KEY ortam değişkenini tanımlayın ya da "
            f"anahtarı '{EVDS_KEY_FILE}' dosyasına yazın."
        )

    if end is None:
        end = date.today().strftime("%d-%m-%Y")
    params = {
        "series": series_code,
        "startDate": start,
        "endDate": end,
        "type": "json",
    }
    url = f"{EVDS_BASE}/{urlencode(params)}"
    r = requests.get(url, headers={"key": EVDS_KEY}, timeout=60)
    r.raise_for_status()
    items = r.json().get("items", [])
    if not items:
        raise RuntimeError(f"EVDS boş yanıt: {series_code}")

    df = pd.DataFrame(items)
    col = series_code.replace(".", "_")
    if col not in df.columns:
        raise RuntimeError(f"EVDS yanıtında '{col}' sütunu yok: {list(df.columns)}")

    raw = df["Tarih"].astype(str)
    if raw.iloc[0].count("-") == 2 and len(raw.iloc[0].split("-")[0]) == 2:
        df["Tarih"] = pd.to_datetime(raw, format="%d-%m-%Y")
    else:  # aylık seri: 'YYYY-M' → ayın ilk günü
        df["Tarih"] = pd.to_datetime(raw + "-01", format="%Y-%m-%d")

    df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=[col]).sort_values("Tarih")
    return df.set_index("Tarih")[col]


def load_data_evds():
    """TCMB EVDS API'sinden TÜFE ve Yi-ÜFE bazlı REDK serilerini çek."""
    cpi = fetch_evds_series(EVDS_CPI_SERIES)
    ppi = fetch_evds_series(EVDS_PPI_SERIES)
    df = pd.DataFrame({"CPI_REER": cpi, "PPI_REER": ppi}).dropna()
    df = df.rename_axis("Dönem").reset_index().sort_values("Dönem").reset_index(drop=True)
    if df.empty:
        raise RuntimeError("EVDS'ten ortak tarihli REDK verisi gelmedi")
    return df[["Dönem", "CPI_REER", "PPI_REER"]]


def load_data_excel():
    """Excel dosyalarından verileri yükle ve birleştir (EVDS yedeği)"""
    # CPI (TÜFE) verisi
    df_cpi = pd.read_excel(CPI_FILE)
    # NaN satırlarını temizle (TCMB notları vs.)
    df_cpi = df_cpi.dropna(subset=['Dönem'])
    df_cpi['Dönem'] = pd.to_datetime(df_cpi['Dönem'], errors='coerce')
    df_cpi = df_cpi.dropna(subset=['Dönem'])  # Geçersiz tarihleri temizle
    cpi_col = [col for col in df_cpi.columns if 'TÜFE  Bazlı' in col][0]
    df_cpi = df_cpi[['Dönem', cpi_col]].rename(columns={cpi_col: 'CPI_REER'})
    
    # PPI (Yi-ÜFE) verisi
    df_ppi = pd.read_excel(PPI_FILE)
    # NaN satırlarını temizle
    df_ppi = df_ppi.dropna(subset=['Dönem'])
    df_ppi['Dönem'] = pd.to_datetime(df_ppi['Dönem'], errors='coerce')
    df_ppi = df_ppi.dropna(subset=['Dönem'])  # Geçersiz tarihleri temizle
    ppi_col = [col for col in df_ppi.columns if 'Yi-ÜFE' in col][0]
    df_ppi = df_ppi[['Dönem', ppi_col]].rename(columns={ppi_col: 'PPI_REER'})

    # Ay başına normalize ET, SONRA birleştir. Excel'de kaymış hücreler var
    # (2013-03-02, Yi-ÜFE'de ayrıca 2013-08-02); ham datetime'la iç birleştirme
    # yapılırsa 2013-08 sessizce düşüyordu (387 yerine 386 satır).
    df_cpi['Dönem'] = _ay_basina_normalize(df_cpi['Dönem'])
    df_ppi['Dönem'] = _ay_basina_normalize(df_ppi['Dönem'])

    # Normalizasyon aynı aya iki satır düşürürse (olmamalı) görünür uyar, sonuncuyu tut
    for ad, d in (('TÜFE', df_cpi), ('Yi-ÜFE', df_ppi)):
        yinelenen = d['Dönem'][d['Dönem'].duplicated()].dt.strftime('%Y-%m').tolist()
        if yinelenen:
            _uyar(f"Excel ({ad}): aynı ay için birden fazla satır",
                  [f"yinelenen aylar: {', '.join(yinelenen)} — sonuncusu kullanılıyor"])
    df_cpi = df_cpi.drop_duplicates(subset='Dönem', keep='last')
    df_ppi = df_ppi.drop_duplicates(subset='Dönem', keep='last')

    # Yalnız bir dosyada bulunan aylar iç birleştirmede düşer — sessiz kalmasın
    tek_tarafli = sorted(set(df_cpi['Dönem']).symmetric_difference(set(df_ppi['Dönem'])))
    if tek_tarafli:
        _uyar("Excel: iki seride ORTAK OLMAYAN aylar iç birleştirmede düştü",
              [f"{len(tek_tarafli)} ay: " +
               ", ".join(t.strftime('%Y-%m') for t in tek_tarafli[:12])])

    # Birleştir
    df = pd.merge(df_cpi, df_ppi, on='Dönem', how='inner')
    df = df.sort_values('Dönem').reset_index(drop=True)

    return df


def _kaynak_damgala(df, kaynak):
    """Kullanılan kaynağı, son gözlemi ve tazeliği df.attrs'a yaz; bozukluğu görünür kıl.

    df.attrs anahtarları: kaynak (evds|excel), son_gozlem (YYYY-MM), gecikme_ay,
    bayat, eksik_aylar, cekim_zamani. CSV damgası ve ozet.json buradan beslenir —
    yayına giden sayının hangi kaynaktan geldiği artık ayırt edilebilir.
    """
    son = pd.to_datetime(df['Dönem']).max()
    gecikme = _gecikme_ay(son.date())
    eksik = _takvim_bosluklari(df['Dönem'])
    bayat = gecikme > TAZELIK_ESIGI_AY

    df.attrs.update({
        "kaynak": kaynak,
        "kaynak_etiket": "TCMB EVDS" if kaynak == "evds" else "yerel Excel (yedek)",
        "son_gozlem": son.strftime("%Y-%m"),
        "gecikme_ay": int(gecikme),
        "bayat": bool(bayat),
        "eksik_aylar": eksik,
        "cekim_zamani": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })

    # Takvim sürekliliği: rolling KONUMSAL olduğu için boşluk pencereleri kaydırır
    if eksik:
        _uyar("Aylık seride TAKVİM BOŞLUĞU var — hareketli ortalamalar kayar",
              [f"eksik ay ({len(eksik)}): " + ", ".join(eksik[:12]) +
               (" …" if len(eksik) > 12 else ""),
               "rolling(window=120) konumsaldır: 120 satır 120 takvim ayını kapsamıyor."])

    if bayat:
        satirlar = [
            f"kaynak={kaynak} · son gözlem={son:%Y-%m} · bugüne göre {gecikme} ay geride "
            f"(eşik: {TAZELIK_ESIGI_AY} ay)",
            "Bu veriden üretilen grafik ve ozet.json YAYINA GİTMEMELİ.",
        ]
        if BAYAT_VERI_IZIN:
            _uyar("BAYAT VERİ — TTO_BAYAT_VERI_IZIN=1 ile bilerek devam ediliyor", satirlar)
        else:
            _uyar("BAYAT VERİ — ÇIKTI ÜRETİLMİYOR", satirlar + [
                "Bilerek devam etmek için: TTO_BAYAT_VERI_IZIN=1 python main.py"])
            raise RuntimeError(
                f"Bayat REDK verisi: kaynak={kaynak}, son gözlem={son:%Y-%m}, "
                f"{gecikme} ay geride (eşik {TAZELIK_ESIGI_AY})"
            )

    print(f"   🏷️ kaynak={kaynak} · son gözlem={son:%Y-%m} · gecikme={gecikme} ay "
          f"· eksik ay={len(eksik)}")
    return df


def load_data():
    """REDK ham serilerini getir: önce EVDS, hata olursa Excel yedeği.

    TTO_REDK_KAYNAK=excel ile doğrudan Excel yoluna zorlanabilir.
    Dönen sütunlar: Dönem, CPI_REER, PPI_REER.
    Kullanılan kaynak ve son gözlem df.attrs'a yazılır (bkz. _kaynak_damgala);
    Excel'e düşüş ve bayat veri artık SESSİZ değil — stderr'e uyarı basar,
    veri eşikten eskiyse istisna atar.
    """
    df = None
    if VERI_KAYNAGI != "excel":
        if not EVDS_KEY:
            _uyar("EVDS ANAHTARI YOK — EVDS yolu hiç denenmedi, Excel yedeğine düşülüyor",
                  ["Anahtarı şu iki yerden birine koyun:",
                   "  1) ortam değişkeni:  export TTO_EVDS_KEY=<anahtar>",
                   f"  2) yerel dosya:      {EVDS_KEY_FILE}  (.gitignore'da, commit edilmez)",
                   "Excel yedeği elle indirilir; EVDS kadar taze DEĞİLDİR."])
        else:
            # SADECE ÇEKİM korumalı. Tazelik/damga denetimi bilinçli olarak
            # try'ın DIŞINDA: içeride olsaydı "EVDS'e erişildi ama seri bayat"
            # durumunda atılan RuntimeError bu except tarafından yutulur ve
            # tam da giderilmek istenen SESSİZ Excel düşüşüne dönüşürdü.
            try:
                df = load_data_evds()
            except Exception as e:
                _uyar("EVDS'TEN ÇEKİLEMEDİ — YEREL EXCEL YEDEĞİNE DÜŞÜLÜYOR",
                      [f"{type(e).__name__}: {_gizle_anahtar(str(e))}",
                       f"anahtar kaynağı: {EVDS_KEY_KAYNAGI}",
                       "Excel dosyaları elle indirilir; EVDS kadar taze DEĞİLDİR."])
                df = None
            if df is not None:
                print(f"   📡 Kaynak: TCMB EVDS ({EVDS_CPI_SERIES} + {EVDS_PPI_SERIES})"
                      f" · anahtar: {EVDS_KEY_KAYNAGI}")
                # Bayatsa burada patlar ve Excel'e DÜŞMEZ — çekim başarılıydı,
                # sorun verinin kendisinde; sessizce başka kaynağa kaymak yanlış.
                return _kaynak_damgala(df, "evds")
    else:
        print("   📄 Kaynak: Excel (TTO_REDK_KAYNAK=excel)")

    df = load_data_excel()
    print(f"   📄 Kaynak: yerel Excel ({os.path.basename(CPI_FILE)}, {os.path.basename(PPI_FILE)})")
    return _kaynak_damgala(df, "excel")


def calculate_composite_reer(df):
    """Ağırlıklı kompozit REDK hesapla"""
    df['Composite_REER'] = (PPI_WEIGHT * df['PPI_REER']) + (CPI_WEIGHT * df['CPI_REER'])
    return df


def calculate_moving_average_deviation(df):
    """5 ve 10 yıllık hareketli ortalama ve % sapma hesapla (Kompozit, PPI, CPI için)"""
    
    # === KOMPOZİT REDK ===
    df['MA_10Y'] = df['Composite_REER'].rolling(window=MA_WINDOW_10Y, min_periods=MA_WINDOW_10Y).mean()
    df['MA_5Y'] = df['Composite_REER'].rolling(window=MA_WINDOW_5Y, min_periods=MA_WINDOW_5Y).mean()
    df['Deviation_10Y_Pct'] = ((df['Composite_REER'] - df['MA_10Y']) / df['MA_10Y']) * 100
    df['Deviation_5Y_Pct'] = ((df['Composite_REER'] - df['MA_5Y']) / df['MA_5Y']) * 100
    
    # === %100 PPI REDK ===
    df['PPI_MA_10Y'] = df['PPI_REER'].rolling(window=MA_WINDOW_10Y, min_periods=MA_WINDOW_10Y).mean()
    df['PPI_Deviation_10Y_Pct'] = ((df['PPI_REER'] - df['PPI_MA_10Y']) / df['PPI_MA_10Y']) * 100
    
    # === %100 CPI REDK ===
    df['CPI_MA_10Y'] = df['CPI_REER'].rolling(window=MA_WINDOW_10Y, min_periods=MA_WINDOW_10Y).mean()
    df['CPI_Deviation_10Y_Pct'] = ((df['CPI_REER'] - df['CPI_MA_10Y']) / df['CPI_MA_10Y']) * 100
    
    return df


def create_plot(df):
    """Plotly ile interaktif grafik oluştur - Kompozit, PPI ve CPI karşılaştırmalı"""
    # Sadece 10Y MA'nın hesaplandığı dönemler
    df_plot = df.dropna(subset=['MA_10Y', 'Deviation_10Y_Pct']).copy()
    
    # 5 alt grafik: REDK+MA, Kompozit 10Y Sapma, Kompozit 5Y Sapma, PPI Sapma, CPI Sapma
    fig = make_subplots(
        rows=5, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.24, 0.19, 0.19, 0.19, 0.19],
        subplot_titles=(
            f'Türkiye Reel Efektif Döviz Kuru ({PPI_WEIGHT*100:.0f}% PPI + {CPI_WEIGHT*100:.0f}% CPI)',
            'Kompozit REDK - 10Y MA\'dan % Sapma',
            'Kompozit REDK - 5Y MA\'dan % Sapma',
            '100% PPI (Yi-ÜFE) Bazlı REDK - 10Y MA\'dan % Sapma',
            '100% CPI (TÜFE) Bazlı REDK - 10Y MA\'dan % Sapma'
        )
    )
    
    # === ROW 1: REDK ve MA'lar ===
    fig.add_trace(
        go.Scatter(
            x=df_plot['Dönem'],
            y=df_plot['Composite_REER'],
            name='Kompozit REDK',
            line=dict(color=TEAL, width=2),
            hovertemplate='<b>Tarih:</b> %{x|%Y-%m}<br><b>REDK:</b> %{y:.2f}<extra></extra>'
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df_plot['Dönem'],
            y=df_plot['MA_10Y'],
            name='10Y MA',
            line=dict(color=BORDO, width=1.5),
            hovertemplate='<b>Tarih:</b> %{x|%Y-%m}<br><b>10Y MA:</b> %{y:.2f}<extra></extra>'
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df_plot['Dönem'],
            y=df_plot['MA_5Y'],
            name='5Y MA',
            line=dict(color=ALTIN, width=1.5),
            hovertemplate='<b>Tarih:</b> %{x|%Y-%m}<br><b>5Y MA:</b> %{y:.2f}<extra></extra>'
        ),
        row=1, col=1
    )
    
    # === ROW 2: Kompozit 10Y Sapma ===
    fig.add_trace(
        go.Scatter(
            x=df_plot['Dönem'],
            y=df_plot['Deviation_10Y_Pct'].clip(lower=0),
            fill='tozeroy',
            line=dict(color=BORDO_KENAR, width=0.5),
            fillcolor=BORDO_DOLGU,
            hoverinfo='skip',
            showlegend=False
        ),
        row=2, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=df_plot['Dönem'],
            y=df_plot['Deviation_10Y_Pct'].clip(upper=0),
            fill='tozeroy',
            line=dict(color=TEAL_KENAR, width=0.5),
            fillcolor=TEAL_DOLGU,
            hoverinfo='skip',
            showlegend=False
        ),
        row=2, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=df_plot['Dönem'],
            y=df_plot['Deviation_10Y_Pct'],
            name='Kompozit 10Y Sapma',
            line=dict(color=MUREKKEP, width=1.5),
            hovertemplate='<b>Tarih:</b> %{x|%Y-%m}<br><b>Kompozit 10Y:</b> %{y:.2f}%<extra></extra>'
        ),
        row=2, col=1
    )
    
    # === ROW 3: Kompozit 5Y Sapma ===
    fig.add_trace(
        go.Scatter(
            x=df_plot['Dönem'],
            y=df_plot['Deviation_5Y_Pct'].clip(lower=0),
            fill='tozeroy',
            line=dict(color=BORDO_KENAR, width=0.5),
            fillcolor=BORDO_DOLGU,
            hoverinfo='skip',
            showlegend=False
        ),
        row=3, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=df_plot['Dönem'],
            y=df_plot['Deviation_5Y_Pct'].clip(upper=0),
            fill='tozeroy',
            line=dict(color=TEAL_KENAR, width=0.5),
            fillcolor=TEAL_DOLGU,
            hoverinfo='skip',
            showlegend=False
        ),
        row=3, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=df_plot['Dönem'],
            y=df_plot['Deviation_5Y_Pct'],
            name='Kompozit 5Y Sapma',
            line=dict(color=MUREKKEP, width=1.5),
            hovertemplate='<b>Tarih:</b> %{x|%Y-%m}<br><b>Kompozit 5Y:</b> %{y:.2f}%<extra></extra>'
        ),
        row=3, col=1
    )
    
    # === ROW 4: %100 PPI Sapma ===
    fig.add_trace(
        go.Scatter(
            x=df_plot['Dönem'],
            y=df_plot['PPI_Deviation_10Y_Pct'].clip(lower=0),
            fill='tozeroy',
            line=dict(color=BORDO_KENAR, width=0.5),
            fillcolor=BORDO_DOLGU,
            hoverinfo='skip',
            showlegend=False
        ),
        row=4, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=df_plot['Dönem'],
            y=df_plot['PPI_Deviation_10Y_Pct'].clip(upper=0),
            fill='tozeroy',
            line=dict(color=TEAL_KENAR, width=0.5),
            fillcolor=TEAL_DOLGU,
            hoverinfo='skip',
            showlegend=False
        ),
        row=4, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=df_plot['Dönem'],
            y=df_plot['PPI_Deviation_10Y_Pct'],
            name='PPI 10Y Sapma',
            line=dict(color=MUREKKEP, width=1.5),
            hovertemplate='<b>Tarih:</b> %{x|%Y-%m}<br><b>PPI 10Y:</b> %{y:.2f}%<extra></extra>'
        ),
        row=4, col=1
    )
    
    # === ROW 5: %100 CPI Sapma ===
    fig.add_trace(
        go.Scatter(
            x=df_plot['Dönem'],
            y=df_plot['CPI_Deviation_10Y_Pct'].clip(lower=0),
            fill='tozeroy',
            line=dict(color=BORDO_KENAR, width=0.5),
            fillcolor=BORDO_DOLGU,
            hoverinfo='skip',
            showlegend=False
        ),
        row=5, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=df_plot['Dönem'],
            y=df_plot['CPI_Deviation_10Y_Pct'].clip(upper=0),
            fill='tozeroy',
            line=dict(color=TEAL_KENAR, width=0.5),
            fillcolor=TEAL_DOLGU,
            hoverinfo='skip',
            showlegend=False
        ),
        row=5, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=df_plot['Dönem'],
            y=df_plot['CPI_Deviation_10Y_Pct'],
            name='CPI 10Y Sapma',
            line=dict(color=MUREKKEP, width=1.5),
            hovertemplate='<b>Tarih:</b> %{x|%Y-%m}<br><b>CPI 10Y:</b> %{y:.2f}%<extra></extra>'
        ),
        row=5, col=1
    )
    
    # Sıfır çizgileri
    for row in [2, 3, 4, 5]:
        fig.add_hline(y=0, line_dash="solid", line_color="#90a4ae", line_width=1, row=row, col=1)
    
    # Son değerler
    last_date = df_plot['Dönem'].iloc[-1]
    last_deviation_10y = df_plot['Deviation_10Y_Pct'].iloc[-1]
    last_deviation_5y = df_plot['Deviation_5Y_Pct'].iloc[-1]
    last_ppi_dev = df_plot['PPI_Deviation_10Y_Pct'].iloc[-1]
    last_cpi_dev = df_plot['CPI_Deviation_10Y_Pct'].iloc[-1]
    last_reer = df_plot['Composite_REER'].iloc[-1]

    # Kaynak uyarısı yalnız EVDS DIŞI ya da bayat veride başlığa eklenir —
    # normal (EVDS, taze) grafiğin görünümü değişmesin
    kaynak_notu = ""
    if df.attrs.get("kaynak") not in (None, "evds") or df.attrs.get("bayat"):
        kaynak_notu = (f" | ⚠ kaynak: {df.attrs.get('kaynak_etiket', 'bilinmiyor')}"
                       f", son gözlem {df.attrs.get('son_gozlem', '?')}")

    # Layout ayarları
    fig.update_layout(
        height=1200,
        title=dict(
            text=f"<b>Türkiye REDK Analizi ({last_date.strftime('%Y-%m')})</b><br>" +
                 f"<sup>Kompozit: 10Y={last_deviation_10y:+.1f}%, 5Y={last_deviation_5y:+.1f}% | " +
                 f"PPI: {last_ppi_dev:+.1f}% | CPI: {last_cpi_dev:+.1f}%{kaynak_notu}</sup>",
            x=0.01,
            xanchor="left",
            font=dict(size=16)
        ),
        # Lejant altta — üstte tutulursa ana başlık ve ilk panel başlığıyla çakışıyor
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.04,
            xanchor="left",
            x=0
        ),
        hovermode='x unified',
        template='plotly_white'
    )
    
    # Y ekseni etiketleri
    fig.update_yaxes(title_text="REDK", row=1, col=1)
    fig.update_yaxes(title_text="% Sapma", row=2, col=1)
    fig.update_yaxes(title_text="% Sapma", row=3, col=1)
    fig.update_yaxes(title_text="% Sapma", row=4, col=1)
    fig.update_yaxes(title_text="% Sapma", row=5, col=1)
    
    # X ekseni
    fig.update_xaxes(title_text="Tarih", row=5, col=1)
    
    return fig


def main():
    """Ana fonksiyon"""
    print("📊 Veri yükleniyor...")
    df = load_data()
    print(f"   ✅ {len(df)} satır veri yüklendi ({df['Dönem'].min().strftime('%Y-%m')} - {df['Dönem'].max().strftime('%Y-%m')})")
    
    print(f"\n📈 Kompozit REDK hesaplanıyor ({PPI_WEIGHT*100:.0f}% PPI + {CPI_WEIGHT*100:.0f}% CPI)...")
    df = calculate_composite_reer(df)
    
    print(f"\n📉 5Y ve 10Y hareketli ortalama ve % sapmalar hesaplanıyor...")
    df = calculate_moving_average_deviation(df)
    
    # Son değerler
    last_row = df.dropna(subset=['Deviation_10Y_Pct']).iloc[-1]
    print(f"\n📍 Son değerler ({last_row['Dönem'].strftime('%Y-%m')}):")
    print(f"   - PPI REDK: {last_row['PPI_REER']:.2f}")
    print(f"   - CPI REDK: {last_row['CPI_REER']:.2f}")
    print(f"   - Kompozit REDK: {last_row['Composite_REER']:.2f}")
    print(f"\n   Kompozit ({PPI_WEIGHT*100:.0f}% PPI + {CPI_WEIGHT*100:.0f}% CPI):")
    print(f"   - 10Y MA: {last_row['MA_10Y']:.2f} → Sapma: {last_row['Deviation_10Y_Pct']:+.2f}%")
    print(f"   - 5Y MA: {last_row['MA_5Y']:.2f} → Sapma: {last_row['Deviation_5Y_Pct']:+.2f}%")
    print(f"\n   %100 PPI (Yi-ÜFE):")
    print(f"   - 10Y MA: {last_row['PPI_MA_10Y']:.2f} → Sapma: {last_row['PPI_Deviation_10Y_Pct']:+.2f}%")
    print(f"\n   %100 CPI (TÜFE):")
    print(f"   - 10Y MA: {last_row['CPI_MA_10Y']:.2f} → Sapma: {last_row['CPI_Deviation_10Y_Pct']:+.2f}%")
    
    print(f"\n🎨 Grafik oluşturuluyor...")
    fig = create_plot(df)
    
    # HTML olarak kaydet (plotly.js CDN'den — dosya ~4.6MB yerine ~100KB olur)
    fig.write_html(OUTPUT_HTML, include_plotlyjs='cdn')
    print(f"   ✅ Grafik '{OUTPUT_HTML}' olarak kaydedildi")

    # Grafiği tarayıcıda aç (TTO_TARAYICI_ACMA=1 ile bastırılabilir; otomasyon için)
    if not os.environ.get("TTO_TARAYICI_ACMA"):
        try:
            import webbrowser
            webbrowser.open('file://' + os.path.realpath(OUTPUT_HTML))
            print(f"   🌐 Grafik tarayıcıda açılıyor...")
        except Exception as e:
            print(f"   ⚠️ Tarayıcı açılamadı: {e}")

    # İsteğe bağlı: Hesaplanmış veriyi CSV olarak kaydet — kaynak damgasıyla birlikte
    output_csv = os.path.join(SCRIPT_DIR, "reer_analysis_data.csv")
    df_out = df.copy()
    df_out["Kaynak"] = df.attrs.get("kaynak", "bilinmiyor")
    df_out.to_csv(output_csv, index=False)
    print(f"   ✅ Veri '{output_csv}' olarak kaydedildi (Kaynak={df_out['Kaynak'].iloc[-1]})")

    # Damganın tamamı ayrı JSON'da: ozet_uret.py buradan okuyup ozet.json'a taşır
    with open(KAYNAK_DAMGASI_JSON, "w", encoding="utf-8") as f:
        json.dump(df.attrs, f, ensure_ascii=False, indent=1)
    print(f"   ✅ Kaynak damgası '{KAYNAK_DAMGASI_JSON}' olarak kaydedildi")

    return df, fig


if __name__ == "__main__":
    df, fig = main()

