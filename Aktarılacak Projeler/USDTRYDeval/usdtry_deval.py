import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from datetime import datetime, timedelta, date

# --- Tarih parametreleri (otomatik: bugün) ---
today = date.today()
end_date = datetime.combine(today, datetime.min.time()) + timedelta(days=1)  # yfinance end exclusive
fetch_start = datetime(2024, 10, 1)
display_start = datetime(2025, 3, 1)
plt.rcParams['figure.facecolor'] = '#1a1a2e'
plt.rcParams['axes.facecolor'] = '#16213e'
plt.rcParams['text.color'] = '#e0e0e0'
plt.rcParams['axes.labelcolor'] = '#e0e0e0'
plt.rcParams['xtick.color'] = '#e0e0e0'
plt.rcParams['ytick.color'] = '#e0e0e0'
plt.rcParams['font.family'] = 'DejaVu Sans'

print(f"Veri aralığı: {fetch_start.date()} – {today} (bugün)")
print("USDTRY verisi indiriliyor...")
usdtry = yf.download("USDTRY=X", start=fetch_start, end=end_date, progress=False)
usdtry = usdtry['Close'].dropna()
if isinstance(usdtry, pd.DataFrame):
    usdtry = usdtry.squeeze()
usdtry.index = usdtry.index.tz_localize(None)

print(f"Veri aralığı: {usdtry.index[0].date()} - {usdtry.index[-1].date()}")
print(f"Toplam gün: {len(usdtry)}")

week_days = 5
month_days = 21
quarter_days = 63

deval_1w = ((usdtry / usdtry.shift(week_days)) ** (252 / week_days) - 1) * 100
deval_1m = ((usdtry / usdtry.shift(month_days)) ** (252 / month_days) - 1) * 100
deval_3m = ((usdtry / usdtry.shift(quarter_days)) ** (252 / quarter_days) - 1) * 100

tcmb_changes = [
    ("2024-03-22", 50.0),
    ("2024-12-26", 47.5),
    ("2025-01-23", 45.0),
    ("2025-03-06", 42.5),
    ("2025-04-17", 46.0),
    ("2025-07-24", 43.0),
    ("2025-09-11", 40.5),
    ("2025-10-23", 39.5),
    ("2025-12-11", 38.0),
    ("2026-01-22", 37.0),
]

policy_rate = pd.Series(dtype=float)
all_dates = usdtry.index
for date_str, rate in tcmb_changes:
    dt = pd.Timestamp(date_str)
    policy_rate[dt] = rate

policy_rate = policy_rate.reindex(all_dates, method='ffill')
policy_rate = policy_rate.ffill()

imamoglu_date = pd.Timestamp("2025-03-19")
iran_war_date = pd.Timestamp("2026-02-28")

mask = usdtry.index >= display_start

fig, ax1 = plt.subplots(figsize=(18, 9))

deval_1w_clip = deval_1w[mask].clip(lower=-50, upper=150)
deval_1m_clip = deval_1m[mask].clip(lower=-50, upper=150)
deval_3m_clip = deval_3m[mask].clip(lower=-50, upper=150)

ax1.plot(deval_1w_clip.index, deval_1w_clip, color='#00d2ff', linewidth=1.0, alpha=0.55, label='1 Haftalik Annualized Deval.')
ax1.plot(deval_1m_clip.index, deval_1m_clip, color='#ff6b6b', linewidth=1.8, alpha=0.85, label='1 Aylik Annualized Deval.')
ax1.plot(deval_3m_clip.index, deval_3m_clip, color='#ffd93d', linewidth=2.2, alpha=0.9, label='3 Aylik Annualized Deval.')

ax1.set_ylabel('Annualized Devaluasyon (%)', fontsize=13, fontweight='bold')
ax1.set_xlabel('')

ax2 = ax1.twinx()
ax2.step(policy_rate[mask].index, policy_rate[mask], color='#6bff6b', linewidth=2.5,
         linestyle='-', alpha=0.85, label='TCMB Politika Faizi (%)', where='post')
ax2.set_ylabel('Politika Faizi (%)', fontsize=13, fontweight='bold', color='#6bff6b')
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

if iran_war_date <= end_date:
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
ax1.set_title(f'USDTRY Annualized Devaluasyon & TCMB Politika Faizi\n'
              f'({display_start.strftime("%b %Y")} - {today.strftime("%b %Y")})',
             fontsize=15, fontweight='bold', pad=15, color='#ffffff')

ax1.text(0.01, 0.02, 'Kaynak: Yahoo Finance, TCMB  |  Deval. >%150 veya <-%50 kliplendi',
         transform=ax1.transAxes, fontsize=8, color='#888', ha='left', va='bottom')

fig.tight_layout()

output_path = "/Users/tunatanozmen/Documents/aktif projeler/USDTRYDeval/usdtry_deval_chart.png"
fig.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
print(f"\nGrafik kaydedildi: {output_path}")

plt.show()
