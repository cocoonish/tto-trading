# -*- coding: utf-8 -*-
"""ROT ayrı tahmini vs mevcut yöntem — örneklem DIŞI yürüyen-ileri yarış."""
import os
import numpy as np, pandas as pd
from scipy import stats

KOK = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "hazine_ihale_verileri.csv")
AMT, BID = 'Toplam(Gerçekleşme)', 'Toplam(Teklif)'
IHA, ROT = 'İhale(Gerçekleşme)', 'ROT Toplam(Gerçekleşme)'

df = pd.read_csv(KOK, encoding='utf-8-sig')
for c in [AMT, BID, IHA, ROT, 'Vade (Yıl)']:
    df[c] = pd.to_numeric(df[c], errors='coerce')
df['_d'] = pd.to_datetime(df['İhale Tarihi'], format='%d.%m.%Y', errors='coerce')
df = df.dropna(subset=['_d', AMT, IHA, ROT])
df = df[df[AMT] > 0].sort_values(['_d']).reset_index(drop=True)
print("ham satır:", len(df), "| kesit:", df['_d'].min().date(), "→", df['_d'].max().date())

# --- bozuk satır: ROT + İhale != Toplam ---
sap = (df[ROT] + df[IHA] - df[AMT]).abs()
bozuk = df[sap > 1.0]
print("özdeşlik bozuk satır:", len(bozuk))
for _, r in bozuk.iterrows():
    print("   ", r['ISIN'], r['İhale Tarihi'], "ROT", r[ROT], "+ İhale", r[IHA], "= ", r[ROT]+r[IHA], " ama Toplam", r[AMT])
df = df[sap <= 1.0].reset_index(drop=True)
print("temiz satır:", len(df))
df['pay'] = df[ROT] / df[AMT]

# --- kıyas kuralı: main.py _forecast_from_comparables birebir (backtest kipi: ISIN elde) ---
def kiyaslar(prior, isin, senet, vade):
    c = prior[prior['ISIN'] == isin]
    baz = 'ISIN'
    if c.empty:
        cand = prior[prior['Senet Tanımı'] == senet]
        if pd.notna(vade) and not cand.empty:
            near = cand[(cand['Vade (Yıl)'] - vade).abs() <= 1.0]
            cand = near if not near.empty else cand
        c, baz = cand, 'tip+vade'
    return c.sort_values('_d'), baz

# --- kısaltılmış lag (shrunk lag) için: aynı ISIN ardışık pay çiftleri ---
MIN_CIFT = 40
rows = []
for i in range(len(df)):
    r = df.iloc[i]
    prior = df.iloc[:i]                      # yalnız KENDİNDEN ÖNCEKİ veri
    if prior.empty:
        continue
    c, baz = kiyaslar(prior, r['ISIN'], r['Senet Tanımı'], r['Vade (Yıl)'])
    if c.empty:
        continue
    son3 = c.tail(3)
    a_toplam   = float(son3[AMT].mean())          # (A) MEVCUT
    b_ihale    = float(son3[IHA].mean())
    b_rot      = float(son3[ROT].mean())
    kiyas_pay  = float(son3['pay'].mean())

    # --- ROT payı tahminleri (yalnız prior ile) ---
    # kısaltılmış lag: pay_t ~ a + b*pay_{t-1}, aynı ISIN çiftleri, yalnız prior
    lag_pay = float(c.iloc[-1]['pay']) if baz == 'ISIN' else np.nan
    pri = prior.sort_values('_d')
    ciftler = []
    for isin_, g in pri.groupby('ISIN'):
        if len(g) >= 2:
            v = g['pay'].values
            ciftler.extend(zip(v[:-1], v[1:]))
    kisalt = np.nan; n_cift = len(ciftler)
    if n_cift >= MIN_CIFT and np.isfinite(lag_pay):
        X = np.array([p[0] for p in ciftler]); Y = np.array([p[1] for p in ciftler])
        b = np.cov(X, Y, ddof=1)[0, 1] / np.var(X, ddof=1)
        a = Y.mean() - b * X.mean()
        kisalt = a + b * lag_pay
    pri_med = float(pri['pay'].median())
    kisalt_kullanildi = np.isfinite(kisalt)
    pay_kisalt = kisalt if kisalt_kullanildi else pri_med
    pay_kisalt = min(max(pay_kisalt, 0.05), 0.95)

    rows.append(dict(
        tarih=r['İhale Tarihi'], d=r['_d'], isin=r['ISIN'], tip=r['Senet Tanımı'], baz=baz,
        gercek=float(r[AMT]), gercek_ihale=float(r[IHA]), gercek_rot=float(r[ROT]),
        A=a_toplam,
        B1=b_ihale + b_rot,                                   # bacak bacak toplam
        B2=b_ihale / (1.0 - min(max(kiyas_pay, 0.05), 0.95)), # İhale ÷ (1−kıyas payı)
        B3=b_ihale / (1.0 - pay_kisalt),                      # İhale ÷ (1−kısaltılmış lag payı)
        B4=b_ihale * 2.0,                                     # İhale ÷ (1−0,50)
        C1=float(pri[AMT].median()),                          # genişleyen genel medyan
        C2=float(pri.iloc[-1][AMT]),                          # rastgele yürüyüş
        C3=float(pri[pri['Senet Tanımı'] == r['Senet Tanımı']][AMT].median())
           if not pri[pri['Senet Tanımı'] == r['Senet Tanımı']].empty else float(pri[AMT].median()),
        kisalt_var=kisalt_kullanildi, n_cift=n_cift,
    ))

bt = pd.DataFrame(rows)
print("\ndeğerlendirilen ihale N =", len(bt), "| kıyas bazı:", bt['baz'].value_counts().to_dict())
print("kısaltılmış lag gerçekten kuruldu:", int(bt['kisalt_var'].sum()), "/", len(bt),
      "(kalanı genişleyen medyana düşüyor)")
print("ilk değerlendirilen:", bt['d'].min().date(), "son:", bt['d'].max().date())

ADAY = {'A':'MEVCUT: kıyas son3 Toplam ort',
        'B1':'AYRI ROT: kıyas son3 İhale ort + kıyas son3 ROT ort',
        'B2':'AYRI ROT: İhale son3 ÷ (1 − kıyas son3 ROT payı)',
        'B3':'AYRI ROT: İhale son3 ÷ (1 − kısaltılmış lag payı)',
        'B4':'AYRI ROT: İhale son3 ÷ (1 − 0,50)',
        'C1':'SAF KIYAS: genişleyen genel medyan',
        'C2':'SAF KIYAS: son ihalenin gerçekleşmesi',
        'C3':'SAF KIYAS: senet tipinin genişleyen medyanı'}

err = pd.DataFrame({k: (bt[k] - bt['gercek']).abs() for k in ADAY})
print("\n--- MAE (Milyon TL) · MedAE · RMSE · MAPE ---")
sat = []
for k, ad in ADAY.items():
    e = err[k]
    sat.append((k, ad, e.mean(), e.median(),
                float(np.sqrt(((bt[k]-bt['gercek'])**2).mean())),
                float((e/bt['gercek']).median()*100)))
for k, ad, m, md, rm, mp in sorted(sat, key=lambda x: x[2]):
    print(f"{k:3s} {ad:52s} MAE {m:10.2f}  MedAE {md:9.2f}  RMSE {rm:10.2f}  MedAPE {mp:6.2f}%")

print("\n--- EŞLİ FARK (aday − A), aynı N =", len(bt), "ihale ---")
for k in ADAY:
    if k == 'A':
        continue
    d = err[k] - err['A']
    if np.allclose(d, 0):
        print(f"{k:3s} fark BİREBİR SIFIR (maks |fark| tahmin düzeyinde "
              f"{np.abs(bt[k]-bt['A']).max():.3e} mn TL) — p kurulmaz, özdeş")
        continue
    t = stats.ttest_rel(err[k], err['A'])
    try:
        w = stats.wilcoxon(err[k], err['A'])
        wp = w.pvalue
    except Exception:
        wp = float('nan')
    print(f"{k:3s} ort fark {d.mean():+9.2f} mn TL  (medyan {d.median():+8.2f})  "
          f"eşli t p={t.pvalue:.4f}  Wilcoxon p={wp:.4f}  "
          f"{'A DAHA İYİ' if d.mean()>0 else 'aday daha iyi'}")

# alt dönem dayanıklılığı
print("\n--- Alt dönem MAE (yıl) ---")
bt['yil'] = bt['d'].dt.year
piv = bt.copy()
for k in ADAY: piv['e_'+k] = err[k]
g = piv.groupby('yil')[['e_'+k for k in ADAY]].mean().round(0)
g['n'] = piv.groupby('yil').size()
print(g.to_string())
bt.to_csv('/tmp/claude-0/-home-user/f0ed7f69-a629-5199-967a-344bc82e8f7b/scratchpad/bt.csv', index=False)

# ================= ÜRETİM ZİNCİRİ KONTROLÜ =================
# Ham adım tek başına değil: canlı zincir ham tahminleri AYLIK HEDEFE ölçekler.
hed = pd.read_csv('/home/user/tto-trading/Aktarılacak Projeler/hazineihrac/hazine_hedef_gerceklesme.csv',
                  encoding='utf-8-sig')
hedler = {str(r['Ay-Yıl']).strip(): float(r['Hedef Borçlanma (Milyar TL)']) for _, r in hed.iterrows()}
ay_tr = {1:'Ocak',2:'Şubat',3:'Mart',4:'Nisan',5:'Mayıs',6:'Haziran',7:'Temmuz',
         8:'Ağustos',9:'Eylül',10:'Ekim',11:'Kasım',12:'Aralık'}
bt['_ay'] = bt['d'].apply(lambda d: f"{ay_tr[d.month]} {d.year}")
K = ['A','B2','B3','B4']
sc = bt.copy()
for k in K: sc['S_'+k] = sc[k]
for ay, g in bt.groupby('_ay'):
    if ay in hedler:
        for k in K:
            s = g[k].sum()
            if s > 0:
                sc.loc[g.index, 'S_'+k] = g[k] * (hedler[ay]*1000/s)
for oran in (1.00, 0.87):
    e = pd.DataFrame({k: (sc['S_'+k]*oran - sc['gercek']).abs() for k in K})
    print(f"\n### AYLIK HEDEFE ÖLÇEKLİ × gerçekleşme oranı {oran:.2f} (N={len(sc)})")
    for k in K:
        print(f"  {k}: MAE {e[k].mean():9.0f}  MedAE {e[k].median():8.0f}")
    for k in ['B2','B3','B4']:
        d = e[k]-e['A']
        print(f"  {k}−A ort {d.mean():+8.0f} medyan {d.median():+7.0f} "
              f"t p={stats.ttest_rel(e[k],e['A']).pvalue:.4f} "
              f"W p={stats.wilcoxon(e[k],e['A']).pvalue:.4f} kazanma %{(d<0).mean()*100:.1f}")
