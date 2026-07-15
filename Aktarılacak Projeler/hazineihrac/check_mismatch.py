import pandas as pd

ihale = pd.read_csv('hazine_ihale_verileri.csv', encoding='utf-8-sig')
comp = pd.read_csv('hazine_hedef_gerceklesme.csv', encoding='utf-8-sig')

ihale['İhale Tarihi'] = pd.to_datetime(ihale['İhale Tarihi'], format='%d.%m.%Y', errors='coerce')
ihale = ihale.dropna(subset=['İhale Tarihi'])
ihale['Ay-Yıl'] = ihale['İhale Tarihi'].dt.strftime('%B %Y')
month_map = {'January':'Ocak','February':'Şubat','March':'Mart','April':'Nisan','May':'Mayıs','June':'Haziran','July':'Temmuz','August':'Ağustos','September':'Eylül','October':'Ekim','November':'Kasım','December':'Aralık'}
ihale['Ay-Yıl'] = ihale['Ay-Yıl'].str.split(' ').apply(lambda x: f"{month_map.get(x[0], x[0])} {x[1]}")
ihale['Toplam(Gerçekleşme)'] = pd.to_numeric(ihale['Toplam(Gerçekleşme)'], errors='coerce').fillna(0)
monthly = (ihale.groupby('Ay-Yıl')['Toplam(Gerçekleşme)'].sum()/1000).round(2).reset_index(name='Realized_Mlyr')
m = comp[['Ay-Yıl','Gerçekleşen Borçlanma (Milyar TL)']].merge(monthly, on='Ay-Yıl', how='left')
m['Diff'] = (m['Gerçekleşen Borçlanma (Milyar TL)'] - m['Realized_Mlyr']).round(2)
mism = m[(m['Realized_Mlyr'].notna()) & (m['Diff'].abs()>0.01)]
print('Mismatches count:', len(mism))
if len(mism):
    print(mism.to_string(index=False))
