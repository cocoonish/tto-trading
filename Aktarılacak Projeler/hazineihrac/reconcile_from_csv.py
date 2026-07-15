import pandas as pd
from typing import Dict

# Constants (align with main.py)
CSV_OUTPUT = "hazine_ihale_verileri.csv"
COMPARISON_CSV = "hazine_hedef_gerceklesme.csv"

def normalize_month_name(month):
    mapping = {
        "Ocak": "Ocak", "Subat": "Şubat", "Şubat": "Şubat", "Mart": "Mart", "Nisan": "Nisan",
        "Mayis": "Mayıs", "Mayıs": "Mayıs", "Haziran": "Haziran", "Temmuz": "Temmuz",
        "Agustos": "Ağustos", "Ağustos": "Ağustos", "Eylul": "Eylül", "Eylül": "Eylül",
        "Ekim": "Ekim", "Kasim": "Kasım", "Kasım": "Kasım", "Aralik": "Aralık", "Aralık": "Aralık"
    }
    def fold_tr(s: str) -> str:
        s = str(s).replace("İ", "i").replace("ı", "i").replace("\u0307", "")
        return (s.strip().lower()
                .replace("ı", "i").replace("ş", "s").replace("ğ", "g")
                .replace("ü", "u").replace("ö", "o").replace("ç", "c"))
    m_fold = fold_tr(str(month))
    for k, v in mapping.items():
        if m_fold.startswith(fold_tr(k)[:3]):
            return v
    try:
        return str(month).strip().title()
    except Exception:
        return str(month)


def build_strategy_from_comparison_csv(path: str) -> Dict[str, float]:
    df = pd.read_csv(path, encoding='utf-8-sig')
    strategy: Dict[str, float] = {}
    for _, row in df.iterrows():
        ay_yil = str(row['Ay-Yıl']).strip()
        parts = ay_yil.split()
        if len(parts) >= 2:
            month = normalize_month_name(parts[0])
            year = parts[1]
            key = f"{month} {year}"
        else:
            key = ay_yil
        target = float(row['Hedef Borçlanma (Milyar TL)'])
        strategy[key] = target
    return strategy


def analyze_borrowing_performance_offline(auction_df: pd.DataFrame, strategy_data: Dict[str, float]) -> pd.DataFrame:
    if not strategy_data or auction_df is None or auction_df.empty:
        return pd.DataFrame()
    if 'İhale Tarihi' not in auction_df.columns:
        return pd.DataFrame()
    en_to_tr_months = {
        'January': 'Ocak', 'February': 'Şubat', 'March': 'Mart', 'April': 'Nisan',
        'May': 'Mayıs', 'June': 'Haziran', 'July': 'Temmuz', 'August': 'Ağustos',
        'September': 'Eylül', 'October': 'Ekim', 'November': 'Kasım', 'December': 'Aralık'
    }
    monthly_realized: Dict[str, float] = {}
    df_filtered = auction_df.dropna(subset=['İhale Tarihi', 'Toplam(Gerçekleşme)'])
    for _, row in df_filtered.iterrows():
        try:
            date_obj = pd.to_datetime(row['İhale Tarihi'], format='%d.%m.%Y')
            en_month = date_obj.strftime('%B')
            tr_month = en_to_tr_months.get(en_month, en_month)
            key = f"{tr_month} {date_obj.year}"
            realized_str = str(row['Toplam(Gerçekleşme)']).replace(',', '').replace(' ', '')
            total_realized = float(realized_str) if realized_str.replace('.', '').isdigit() else 0.0
            if total_realized > 0:
                monthly_realized[key] = monthly_realized.get(key, 0.0) + total_realized
        except Exception:
            continue
    comparison_data = []
    for month_label, target in strategy_data.items():
        parts = str(month_label).split()
        if len(parts) >= 2:
            key = f"{normalize_month_name(parts[0])} {parts[1]}"
        else:
            key = normalize_month_name(month_label)
        realized = monthly_realized.get(key, 0.0) / 1000.0
        comparison_data.append({
            'Ay-Yıl': key,
            'Hedef Borçlanma (Milyar TL)': float(target),
            'Gerçekleşen Borçlanma (Milyar TL)': round(realized, 2),
            'Fark (Milyar TL)': round(realized - float(target), 2),
            'Gerçekleşme Oranı (%)': round((realized / float(target) * 100.0) if float(target) > 0 else 0.0, 1)
        })
    return pd.DataFrame(comparison_data)


def reconcile():
    ihale_df = pd.read_csv(CSV_OUTPUT, encoding='utf-8-sig')
    comp_path = COMPARISON_CSV
    _ = pd.read_csv(comp_path, encoding='utf-8-sig')  # ensure loadable

    strategy = build_strategy_from_comparison_csv(comp_path)
    new_comp_df = analyze_borrowing_performance_offline(ihale_df, strategy)

    if new_comp_df is None or new_comp_df.empty:
        print("Karşılaştırma tablosu üretilemedi (boş).")
        return

    new_comp_df.to_csv(comp_path, index=False, encoding='utf-8-sig')

    print("\nGüncellenmiş hedef/gerçekleşme (ilk 10):")
    print(new_comp_df.head(10).to_string(index=False))


if __name__ == '__main__':
    reconcile()
