"""USDTRY yıllıklandırılmış devalüasyon (ACT/365) + TCMB fonlama maliyeti — statik PNG.

Bu script hattın DİĞER üç scriptiyle (usdtry_deval_plotly / _weekly_trends /
_monthly_trends) AYNI VERİ TABANINI kullanır:
  · Kaynak     : EVDS TP.DK.USD.A.YTL (TCMB gösterge alış kuru) — yfinance DEĞİL
  · Ön işleme  : günlük interpolasyon + hafta içi süzme
  · Yıllıklandırma: ACT/365, gerçek takvim günü farkı (sabit 252/n üssü KULLANILMAZ)
  · Çıktı      : script'in kendi klasörü (taşınmaya dayanıklı)

Neden duruyor: TCMB FONLAMA MALİYETİ (AOFM, TP.APIFON4) katmanı yalnız bu grafikte var.
Yayımlanan Şekil 01 faiz katmanını TLREF / kredi / mevduat serilerinden kurar; TCMB'nin
kendi fonlama maliyeti orada yok. Carry için asıl büyüklük budur: taşıma maliyetini
fiilen AOFM belirler, ilan edilen politika faizi değil (koridor tavanından fonlamada
ikisi ayrışır).

Çıktı siteye KOPYALANMAZ; yerel/ofline referans karesidir. Bu yüzden koyu matplotlib
teması korunmuştur — ev stili (beyaz zemin, Plotly) yayımlanan figürler için geçerlidir.
"""
import os
import requests
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")  # toplu/başsız çalıştırma: plt.show() beklemesin
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from urllib.parse import urlencode
from datetime import date
from evds_ortak import evds_anahtari, gizle_anahtar, EVDS_ILERI_GUN, EVDS_BASE, usdtry_serisi

# Çıktılar script'in kendi klasörüne yazılır (taşınmaya dayanıklı)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Tarih parametreleri (otomatik: bugün) ---
today = date.today()
# EVDS sorgu bitişi bilerek birkaç gün ileri alınır: TCMB, ertesi iş gününün gösterge
# kurunu bugün öğleden sonra yayımlar. endDate=bugün olduğunda o kur sistematik olarak
# dışarıda kalır. Gelecek tarih için EVDS boş döner — ileri almak zararsızdır.
fetch_end = (pd.Timestamp(today) + pd.Timedelta(days=EVDS_ILERI_GUN)).strftime("%d-%m-%Y")
fetch_start = "01-10-2024"  # EVDS geçmiş veri başlangıcı (63 günlük pencereye buffer)
display_start = pd.Timestamp("2025-03-01")  # grafik sabit başlangıç (İmamoğlu dönemi)

EVDS_KEY = evds_anahtari()

plt.rcParams['figure.facecolor'] = '#1a1a2e'
plt.rcParams['axes.facecolor'] = '#16213e'
plt.rcParams['text.color'] = '#e0e0e0'
plt.rcParams['axes.labelcolor'] = '#e0e0e0'
plt.rcParams['xtick.color'] = '#e0e0e0'
plt.rcParams['ytick.color'] = '#e0e0e0'
plt.rcParams['font.family'] = 'DejaVu Sans'


def fetch_evds(series_code: str, start: str, end: str) -> pd.Series:
    params = {"series": series_code, "startDate": start, "endDate": end, "type": "json"}
    url = f"{EVDS_BASE}/{urlencode(params)}"
    r = requests.get(url, headers={"key": EVDS_KEY}, timeout=30)
    r.raise_for_status()
    items = r.json().get("items", [])
    if not items:
        raise RuntimeError(f"EVDS no data for {series_code}")
    df = pd.DataFrame(items)
    df["Tarih"] = pd.to_datetime(df["Tarih"].astype(str), format="%d-%m-%Y")
    col = series_code.replace(".", "_")
    df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=[col]).sort_values("Tarih")
    return df.set_index("Tarih")[col].rename(series_code)


print(f"Veri aralığı: {fetch_start} – {fetch_end} (bugün: {today})")
print("Yahoo Finance'ten USD/TRY cekiliyor...")
usdtry = usdtry_serisi(fetch_start)
print(f"  {len(usdtry)} kayit, {usdtry.index[0].date()} - {usdtry.index[-1].date()}")

# Grafik penceresi bugünle değil VERİYLE biter; erken yayımlanan ertesi iş günü kuru
# da eksene girsin.
display_end = max(pd.Timestamp(usdtry.index[-1]), pd.Timestamp(today))

usdtry_full = usdtry.asfreq("D").interpolate(method="time")
business = usdtry_full[usdtry_full.index.dayofweek < 5]


def deval_act365(s: pd.Series, n: int) -> pd.Series:
    """Yıllıklandırılmış devalüasyon, ACT/365 takvim günü tabanı.

    Pencere n GÖZLEM (iş günü) geriye gider; üs, iki gözlem tarihinin GERÇEK
    takvim günü farkı Δd üzerinden: oran = (P_t / P_{t-n}) ** (365 / Δd) - 1.
    Sabit 252/n (iş günü) üssü kullanılmaz — TL faizleri ACT/365 kote edilir.
    """
    ratio = s / s.shift(n)
    delta_d = pd.Series(s.index, index=s.index).diff(n).dt.days.astype(float)
    return (ratio ** (365.0 / delta_d) - 1) * 100


week_days = 5
month_days = 21
quarter_days = 63

deval_1w = deval_act365(business, week_days)
deval_1m = deval_act365(business, month_days)
deval_3m = deval_act365(business, quarter_days)

# TCMB fonlama maliyeti — EVDS'ten CANLI çekilir (TP.APIFON4, Ağırlıklı Ortalama
# Fonlama Maliyeti).
#
# Neden elle tutulan PPK listesi değil: burada önceden 1 haftalık repo faizi elle
# yazılıyordu ve liste 22.01.2026'da (%37,0) bitmişti. TCMB'nin kendi verisine göre
# fonlama maliyeti 03.03.2026'da %39,35 → %40,00'a çıkmıştı; yani grafik beş ay
# boyunca 300 bp yanlış bir seviye çiziyordu. Elle bakımlı seri, hattın geri
# kalanı canlıyken sessizce bayatlar — bu yüzden bu katman da EVDS'e bağlandı.
#
# AOFM ≠ ilan edilen politika faizi: TCMB koridorun tavanından fonladığında AOFM
# politika faizinin üstüne çıkar. Carry karşılaştırması için AOFM zaten daha
# doğru büyüklüktür (taşıma maliyetini fiilen bu belirler), ama etiket bunu
# açıkça söylemeli — grafikte "Politika Faizi" değil "AOFM" yazar.
POLITIKA_SERI = "TP.APIFON4"
policy_rate = None
try:
    _aofm = fetch_evds(POLITIKA_SERI, fetch_start, fetch_end)
    if _aofm is not None and len(_aofm):
        policy_rate = _aofm.reindex(business.index).ffill()
except Exception as _e:
    print(f"UYARI: {POLITIKA_SERI} çekilemedi: "
          f"{type(_e).__name__}: {gizle_anahtar(str(_e))}")

if policy_rate is None or policy_rate.dropna().empty:
    # Sessizce eski/boş seriyle devam etmek, tam da giderilen hatanın kendisi olur.
    raise RuntimeError(
        f"{POLITIKA_SERI} (fonlama maliyeti) çekilemedi — faiz katmanı olmadan "
        "grafik üretilmiyor. Bayat/eksik faizle yayın yapmaktansa durmak doğrudur."
    )

all_dates = business.index

imamoglu_date = pd.Timestamp("2025-03-19")
iran_war_date = pd.Timestamp("2026-02-28")

mask = (business.index >= display_start) & (business.index <= display_end)

fig, ax1 = plt.subplots(figsize=(18, 9))

deval_1w_clip = deval_1w[mask].clip(lower=-50, upper=150)
deval_1m_clip = deval_1m[mask].clip(lower=-50, upper=150)
deval_3m_clip = deval_3m[mask].clip(lower=-50, upper=150)

ax1.plot(deval_1w_clip.index, deval_1w_clip, color='#00d2ff', linewidth=1.0, alpha=0.55, label='1 Haftalik Annualized Deval.')
ax1.plot(deval_1m_clip.index, deval_1m_clip, color='#ff6b6b', linewidth=1.8, alpha=0.85, label='1 Aylik Annualized Deval.')
ax1.plot(deval_3m_clip.index, deval_3m_clip, color='#ffd93d', linewidth=2.2, alpha=0.9, label='3 Aylik Annualized Deval.')

ax1.set_ylabel('Annualized Devaluasyon (%, ACT/365)', fontsize=13, fontweight='bold')
ax1.set_xlabel('')

ax2 = ax1.twinx()
ax2.step(policy_rate[mask].index, policy_rate[mask], color='#6bff6b', linewidth=2.5,
         linestyle='-', alpha=0.85, label='TCMB Ağırlıklı Ort. Fonlama Maliyeti (%)', where='post')
ax2.set_ylabel('AOFM (%)', fontsize=13, fontweight='bold', color='#6bff6b')
ax2.tick_params(axis='y', labelcolor='#6bff6b')

ax1.set_ylim(-50, 155)

rate_min = policy_rate[mask].min()
rate_max = policy_rate[mask].max()
rate_padding = (rate_max - rate_min) * 0.3
ax2.set_ylim(rate_min - rate_padding, rate_max + rate_padding)

peak_1w = deval_1w[mask].max()
peak_1w_date = deval_1w[mask].idxmax()

if imamoglu_date >= display_start:
    ax1.axvline(x=imamoglu_date, color='#ff4757', linestyle='-', linewidth=2.5, alpha=0.85)
    ax1.annotate(f'Imamoglu Tutuklanmasi\n19 Mart 2025\n(1H spike: %{peak_1w:.0f})',
                xy=(imamoglu_date, 148),
                xytext=(50, -5), textcoords='offset points',
                fontsize=10, color='#ff4757', fontweight='bold',
                ha='left', va='top',
                arrowprops=dict(arrowstyle='->', color='#ff4757', lw=1.5),
                bbox=dict(boxstyle='round,pad=0.4', facecolor='#1a1a2e', edgecolor='#ff4757', alpha=0.95))

if iran_war_date <= display_end:
    ax1.axvline(x=iran_war_date, color='#ffa502', linestyle='-', linewidth=2.5, alpha=0.85)
    ax1.annotate('Iran-ABD Savasi Baslangici\n28 Subat 2026',
                xy=(iran_war_date, 148),
                xytext=(-180, -5), textcoords='offset points',
                fontsize=10, color='#ffa502', fontweight='bold',
                ha='right', va='top',
                arrowprops=dict(arrowstyle='->', color='#ffa502', lw=1.5),
                bbox=dict(boxstyle='round,pad=0.4', facecolor='#1a1a2e', edgecolor='#ffa502', alpha=0.95))

ax1.axhline(y=0, color='#ffffff', linestyle=':', linewidth=0.8, alpha=0.4)

ax1.fill_between(deval_3m_clip.index, 0, deval_3m_clip, alpha=0.08, color='#ffd93d')

lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right', fontsize=10,
          facecolor='#16213e', edgecolor='#555', labelcolor='#e0e0e0',
          framealpha=0.92, ncol=2)

ax1.xaxis.set_major_locator(mdates.MonthLocator())
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b\n%Y'))
plt.setp(ax1.xaxis.get_majorticklabels(), fontsize=9)

ax1.grid(True, alpha=0.15, color='#ffffff')
ax1.set_title(f'USDTRY Annualized Devaluasyon (ACT/365) & TCMB Politika Faizi\n'
              f'({display_start.strftime("%b %Y")} - {display_end.strftime("%b %Y")})',
             fontsize=15, fontweight='bold', pad=15, color='#ffffff')

ax1.text(0.01, 0.02, 'Kaynak: Yahoo Finance (USDTRY=X), TCMB PPK  |  Deval. >%150 veya <-%50 kliplendi',
         transform=ax1.transAxes, fontsize=8, color='#888', ha='left', va='bottom')

fig.tight_layout()

output_path = os.path.join(BASE_DIR, "usdtry_deval_chart.png")
fig.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
print(f"\nGrafik kaydedildi: {output_path}")

# Son değer özeti (log/rapor için) — plotly scripti ile birebir aynı olmalı
last_dt = deval_3m.dropna().index[-1]
print(f"Son gözlem ({last_dt.date()}): "
      f"1H {deval_1w.dropna().iloc[-1]:+.2f}% · "
      f"1A {deval_1m.dropna().iloc[-1]:+.2f}% · "
      f"3A {deval_3m.dropna().iloc[-1]:+.2f}%  (yıllıklandırılmış, ACT/365)  "
      f"| AOFM: %{policy_rate.iloc[-1]:.1f}")
