from __future__ import annotations

import json
import math
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    from scipy import stats
except Exception:
    stats = None

INPUT_CSV = Path('/mnt/data/indian_fmcg_high_quality_dataset (1).csv')
OUT_DIR = Path('/mnt/data/fmcg_analysis_tables')
OUT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_PATH = Path('/mnt/data/fmcg_analysis_report.md')
JSON_PATH = Path('/mnt/data/fmcg_frontend_data.json')
RECON_PATH = Path('/mnt/data/fmcg_kpi_reconciliation.csv')
ZIP_PATH = Path('/mnt/data/fmcg_analysis_package.zip')

EXPECTED_COLUMNS = [
    'date','sku','brand','segment','category','channel','region','pack_type',
    'price_unit','promotion_flag','delivery_days','stock_available','delivered_qty','units_sold'
]

REGION_MAP = {
    'WestIndia': 'West India',
    'EastIndia': 'East India',
    'SouthIndia': 'South India',
    'CentralIndia': 'Central India',
    'NorthIndia': 'North India',
}


def jsafe(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        if np.isnan(value) or np.isinf(value):
            return None
        return float(value)
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if isinstance(value, (pd.Period,)):
        return str(value)
    if isinstance(value, dict):
        return {str(k): jsafe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsafe(v) for v in value]
    return value


def records(df: pd.DataFrame, n: int | None = None) -> list[dict[str, Any]]:
    data = df.head(n) if n else df
    return [{str(k): jsafe(v) for k, v in row.items()} for row in data.to_dict(orient='records')]


def fmt_num(x: float, digits: int = 2) -> str:
    return f'{x:,.{digits}f}'


def pct_rank(s: pd.Series, ascending: bool = True) -> pd.Series:
    return s.rank(method='average', pct=True, ascending=ascending).fillna(0.5)


# ----------------------------- Load and clean -----------------------------
raw = pd.read_csv(INPUT_CSV)
rows_before = len(raw)
columns_before = len(raw.columns)
missing_expected = [c for c in EXPECTED_COLUMNS if c not in raw.columns]
extra_columns = [c for c in raw.columns if c not in EXPECTED_COLUMNS]
if missing_expected:
    raise ValueError(f'Missing required columns: {missing_expected}')

df = raw.copy()
cleaning_log: list[dict[str, Any]] = []

# Normalize text, preserve original row count.
for col in ['sku','brand','segment','category','channel','region','pack_type']:
    before_changed = int((df[col].astype(str) != df[col].astype(str).str.strip()).sum())
    df[col] = df[col].astype(str).str.strip()
    cleaning_log.append({'operation': f'Strip whitespace: {col}', 'rows_affected': before_changed})

df['region'] = df['region'].replace(REGION_MAP)
cleaning_log.append({'operation': 'Standardize region labels', 'rows_affected': int(raw['region'].isin(REGION_MAP.keys()).sum())})

df['date'] = pd.to_datetime(df['date'], errors='coerce')
for col in ['price_unit','promotion_flag','delivery_days','stock_available','delivered_qty','units_sold']:
    df[col] = pd.to_numeric(df[col], errors='coerce')

missing_counts = df.isna().sum()
duplicate_count = int(df.duplicated().sum())

# Flags only. Nothing silently deleted.
invalid_flags = pd.DataFrame(index=df.index)
invalid_flags['invalid_date'] = df['date'].isna()
invalid_flags['invalid_promotion_flag'] = ~df['promotion_flag'].isin([0,1])
invalid_flags['nonpositive_price'] = df['price_unit'] <= 0
invalid_flags['invalid_delivery_days'] = (df['delivery_days'] < 0) | (df['delivery_days'] > 30)
invalid_flags['negative_stock'] = df['stock_available'] < 0
invalid_flags['negative_delivered'] = df['delivered_qty'] < 0
invalid_flags['negative_units'] = df['units_sold'] < 0
invalid_flags['any_invalid'] = invalid_flags.any(axis=1)
flagged_rows = int(invalid_flags['any_invalid'].sum())

# ----------------------------- Derived metrics -----------------------------
df['revenue'] = df['price_unit'] * df['units_sold']
df['available_supply_proxy'] = df['stock_available'] + df['delivered_qty']
df['sell_through_rate_row'] = np.where(df['stock_available'] > 0, df['units_sold'] / df['stock_available'], np.nan)
df['fill_rate_row'] = np.where(df['stock_available'] > 0, df['delivered_qty'] / df['stock_available'], np.nan)
df['sell_through_supply_proxy_row'] = np.where(df['available_supply_proxy'] > 0, df['units_sold'] / df['available_supply_proxy'], np.nan)
df['inventory_remaining_proxy'] = df['available_supply_proxy'] - df['units_sold']
df['daily_sales_proxy'] = np.where(df['delivery_days'] > 0, df['units_sold'] / df['delivery_days'], np.nan)
df['demand_coverage_days_proxy'] = np.where(df['daily_sales_proxy'] > 0, df['stock_available'] / df['daily_sales_proxy'], np.nan)
df['delivery_status'] = np.select(
    [df['delivery_days'] <= 2, df['delivery_days'] <= 4],
    ['Healthy', 'Watch'], default='Critical'
)
df['promotion_label'] = np.where(df['promotion_flag'].eq(1), 'Promotion', 'No Promotion')
df['year'] = df['date'].dt.year
df['quarter'] = df['date'].dt.to_period('Q').astype(str)
df['month'] = df['date'].dt.month
df['month_name'] = df['date'].dt.month_name().str[:3]
df['month_period'] = df['date'].dt.to_period('M').astype(str)
df['week'] = df['date'].dt.isocalendar().week.astype('Int64')
df['day'] = df['date'].dt.day
df['day_name'] = df['date'].dt.day_name()
df['is_weekend'] = df['date'].dt.dayofweek >= 5

df['price_band'] = pd.qcut(df['price_unit'], q=5, labels=['Very Low','Low','Mid','High','Very High'], duplicates='drop')

# ----------------------------- Core KPIs -----------------------------
unique_days = int(df['date'].nunique())
core = {
    'records': int(len(df)),
    'columns': int(len(EXPECTED_COLUMNS)),
    'date_start': df['date'].min().date().isoformat(),
    'date_end': df['date'].max().date().isoformat(),
    'brands': int(df['brand'].nunique()),
    'skus': int(df['sku'].nunique()),
    'categories': int(df['category'].nunique()),
    'segments': int(df['segment'].nunique()),
    'channels': int(df['channel'].nunique()),
    'regions': int(df['region'].nunique()),
    'pack_types': int(df['pack_type'].nunique()),
    'missing_values': int(missing_counts.sum()),
    'duplicate_rows': duplicate_count,
    'flagged_invalid_rows': flagged_rows,
    'total_revenue': float(df['revenue'].sum()),
    'total_revenue_cr': float(df['revenue'].sum() / 1e7),
    'total_units_sold': int(df['units_sold'].sum()),
    'total_units_million': float(df['units_sold'].sum() / 1e6),
    'avg_delivery_days': float(df['delivery_days'].mean()),
    'median_delivery_days': float(df['delivery_days'].median()),
    # Weighted ratios follow Appendix A's denominator but avoid row-average distortion.
    'fill_rate_pct': float(df['delivered_qty'].sum() / df['stock_available'].sum() * 100),
    'sell_through_rate_pct': float(df['units_sold'].sum() / df['stock_available'].sum() * 100),
    'row_average_fill_rate_pct': float(df['fill_rate_row'].mean() * 100),
    'row_average_sell_through_rate_pct': float(df['sell_through_rate_row'].mean() * 100),
    'supply_proxy_sell_through_pct': float(df['units_sold'].sum() / df['available_supply_proxy'].sum() * 100),
    'avg_units_per_record': float(df['units_sold'].mean()),
    'avg_daily_units_calendar': float(df.groupby('date')['units_sold'].sum().mean()),
    'unique_days': unique_days,
}

promo_group = df.groupby('promotion_flag').agg(
    records=('units_sold','size'), mean_units=('units_sold','mean'), median_units=('units_sold','median'),
    mean_revenue=('revenue','mean'), median_revenue=('revenue','median'),
    total_units=('units_sold','sum'), total_revenue=('revenue','sum')
)
core['promotion_lift_units_pct'] = float((promo_group.loc[1,'mean_units'] / promo_group.loc[0,'mean_units'] - 1) * 100)
core['promotion_lift_revenue_pct'] = float((promo_group.loc[1,'mean_revenue'] / promo_group.loc[0,'mean_revenue'] - 1) * 100)
core['promotion_share_pct'] = float(df['promotion_flag'].mean() * 100)

# ----------------------------- Summaries -----------------------------
def summary_by(col: str) -> pd.DataFrame:
    out = df.groupby(col, dropna=False).agg(
        records=('sku','size'),
        revenue=('revenue','sum'),
        units_sold=('units_sold','sum'),
        avg_price=('price_unit','mean'),
        avg_delivery_days=('delivery_days','mean'),
        stock_available=('stock_available','sum'),
        delivered_qty=('delivered_qty','sum')
    )
    out['revenue_share_pct'] = out['revenue'] / out['revenue'].sum() * 100
    out['units_share_pct'] = out['units_sold'] / out['units_sold'].sum() * 100
    out['fill_rate_pct'] = out['delivered_qty'] / out['stock_available'] * 100
    out['sell_through_rate_pct'] = out['units_sold'] / out['stock_available'] * 100
    return out.sort_values('revenue', ascending=False).reset_index()

brand_summary = summary_by('brand')
category_summary = summary_by('category')
region_summary = summary_by('region')
channel_summary = summary_by('channel')
pack_summary = summary_by('pack_type')
segment_summary = summary_by('segment')

yearly = df.groupby('year').agg(records=('sku','size'), revenue=('revenue','sum'), units_sold=('units_sold','sum')).reset_index()
yearly['revenue_growth_pct'] = yearly['revenue'].pct_change() * 100
yearly['units_growth_pct'] = yearly['units_sold'].pct_change() * 100

monthly = df.groupby('month_period').agg(records=('sku','size'), revenue=('revenue','sum'), units_sold=('units_sold','sum')).reset_index()
monthly['mom_revenue_pct'] = monthly['revenue'].pct_change() * 100
monthly['mom_units_pct'] = monthly['units_sold'].pct_change() * 100
monthly['year'] = monthly['month_period'].str[:4].astype(int)
monthly['month_num'] = monthly['month_period'].str[5:7].astype(int)
monthly['yoy_revenue_pct'] = monthly.groupby('month_num')['revenue'].pct_change() * 100
monthly['yoy_units_pct'] = monthly.groupby('month_num')['units_sold'].pct_change() * 100

quarterly = df.groupby('quarter').agg(records=('sku','size'), revenue=('revenue','sum'), units_sold=('units_sold','sum')).reset_index()
quarterly['qoq_revenue_pct'] = quarterly['revenue'].pct_change() * 100
quarterly['qoq_units_pct'] = quarterly['units_sold'].pct_change() * 100

daily = df.groupby('date').agg(records=('sku','size'), revenue=('revenue','sum'), units_sold=('units_sold','sum')).reset_index()

weekday = df.groupby(['day_name','is_weekend']).agg(
    records=('sku','size'), mean_units=('units_sold','mean'), total_units=('units_sold','sum'),
    mean_revenue=('revenue','mean'), total_revenue=('revenue','sum')
).reset_index()
order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
weekday['day_name'] = pd.Categorical(weekday['day_name'], categories=order, ordered=True)
weekday = weekday.sort_values('day_name')

# SKU identity is brand + SKU because the same SKU code appears across all brands.
sku_summary = df.groupby(['brand','sku','category']).agg(
    records=('sku','size'), revenue=('revenue','sum'), units_sold=('units_sold','sum'),
    avg_price=('price_unit','mean'), avg_delivery_days=('delivery_days','mean'),
    stock_available=('stock_available','sum'), delivered_qty=('delivered_qty','sum')
).reset_index()
sku_summary['revenue_share_pct'] = sku_summary['revenue'] / sku_summary['revenue'].sum() * 100
sku_summary['fill_rate_pct'] = sku_summary['delivered_qty'] / sku_summary['stock_available'] * 100
sku_summary['sell_through_rate_pct'] = sku_summary['units_sold'] / sku_summary['stock_available'] * 100
sku_summary = sku_summary.sort_values('revenue', ascending=False)

# ----------------------------- Promotion analysis -----------------------------
def promotion_lift(group_col: str) -> pd.DataFrame:
    unit_means = df.pivot_table(index=group_col, columns='promotion_flag', values='units_sold', aggfunc='mean')
    rev_means = df.pivot_table(index=group_col, columns='promotion_flag', values='revenue', aggfunc='mean')
    counts = df.pivot_table(index=group_col, columns='promotion_flag', values='sku', aggfunc='size', fill_value=0)
    out = pd.DataFrame(index=unit_means.index)
    out['nonpromo_mean_units'] = unit_means.get(0)
    out['promo_mean_units'] = unit_means.get(1)
    out['unit_lift_pct'] = (out['promo_mean_units'] / out['nonpromo_mean_units'] - 1) * 100
    out['nonpromo_mean_revenue'] = rev_means.get(0)
    out['promo_mean_revenue'] = rev_means.get(1)
    out['revenue_lift_pct'] = (out['promo_mean_revenue'] / out['nonpromo_mean_revenue'] - 1) * 100
    out['nonpromo_records'] = counts.get(0, 0)
    out['promo_records'] = counts.get(1, 0)
    return out.reset_index().sort_values('unit_lift_pct', ascending=False)

promo_brand = promotion_lift('brand')
promo_category = promotion_lift('category')
promo_region = promotion_lift('region')
promo_channel = promotion_lift('channel')
promo_pack = promotion_lift('pack_type')
promo_price_band = promotion_lift('price_band')

# ----------------------------- Supply chain -----------------------------
delivery_by_channel = df.groupby('channel').agg(
    records=('sku','size'), avg_delivery_days=('delivery_days','mean'), median_delivery_days=('delivery_days','median'),
    stock_available=('stock_available','sum'), delivered_qty=('delivered_qty','sum'), units_sold=('units_sold','sum'), revenue=('revenue','sum')
).reset_index()
delivery_by_channel['fill_rate_pct'] = delivery_by_channel['delivered_qty'] / delivery_by_channel['stock_available'] * 100
delivery_by_channel['sell_through_rate_pct'] = delivery_by_channel['units_sold'] / delivery_by_channel['stock_available'] * 100

status_pct_channel = pd.crosstab(df['channel'], df['delivery_status'], normalize='index').mul(100).reset_index()
delivery_by_channel = delivery_by_channel.merge(status_pct_channel, on='channel', how='left')

supply_region = df.groupby('region').agg(
    records=('sku','size'), avg_delivery_days=('delivery_days','mean'), median_delivery_days=('delivery_days','median'),
    stock_available=('stock_available','sum'), delivered_qty=('delivered_qty','sum'), units_sold=('units_sold','sum'), revenue=('revenue','sum')
).reset_index()
supply_region['fill_rate_pct'] = supply_region['delivered_qty'] / supply_region['stock_available'] * 100
supply_region['sell_through_rate_pct'] = supply_region['units_sold'] / supply_region['stock_available'] * 100

status_overall = df['delivery_status'].value_counts().rename_axis('delivery_status').reset_index(name='records')
status_overall['share_pct'] = status_overall['records'] / len(df) * 100

delivery_distribution = df['delivery_days'].value_counts().sort_index().rename_axis('delivery_days').reset_index(name='records')
delivery_distribution['share_pct'] = delivery_distribution['records'] / len(df) * 100

# ----------------------------- Inventory scoring -----------------------------
inv_keys = ['brand','sku','category','region','channel']
inv = df.groupby(inv_keys).agg(
    records=('sku','size'), stock_available=('stock_available','sum'), delivered_qty=('delivered_qty','sum'),
    units_sold=('units_sold','sum'), revenue=('revenue','sum'), avg_delivery_days=('delivery_days','mean'),
    promotion_rate_pct=('promotion_flag','mean')
).reset_index()
inv['promotion_rate_pct'] *= 100
inv['fill_rate_pct'] = inv['delivered_qty'] / inv['stock_available'] * 100
inv['sell_through_rate_pct'] = inv['units_sold'] / inv['stock_available'] * 100
inv['available_supply_proxy'] = inv['stock_available'] + inv['delivered_qty']
inv['remaining_inventory_proxy'] = inv['available_supply_proxy'] - inv['units_sold']

# Last 90 days vs preceding 90 days velocity.
max_date = df['date'].max()
recent_start = max_date - pd.Timedelta(days=89)
prior_start = recent_start - pd.Timedelta(days=90)
recent = df[df['date'].between(recent_start, max_date)].groupby(inv_keys)['units_sold'].sum().rename('recent_90d_units')
prior = df[df['date'].between(prior_start, recent_start - pd.Timedelta(days=1))].groupby(inv_keys)['units_sold'].sum().rename('prior_90d_units')
inv = inv.merge(recent.reset_index(), on=inv_keys, how='left').merge(prior.reset_index(), on=inv_keys, how='left')
inv[['recent_90d_units','prior_90d_units']] = inv[['recent_90d_units','prior_90d_units']].fillna(0)
inv['recent_growth_pct'] = np.where(inv['prior_90d_units'] > 0, (inv['recent_90d_units']/inv['prior_90d_units'] - 1)*100, np.nan)

# Promotion response for each operational combination.
combo = df.pivot_table(index=inv_keys, columns='promotion_flag', values='units_sold', aggfunc='mean')
combo['promotion_response_pct'] = np.where(combo.get(0, np.nan) > 0, (combo.get(1, np.nan)/combo.get(0, np.nan)-1)*100, np.nan)
inv = inv.merge(combo[['promotion_response_pct']].reset_index(), on=inv_keys, how='left')

low_stock = 1 - pct_rank(inv['stock_available'])
high_sales = pct_rank(inv['units_sold'])
high_str = pct_rank(inv['sell_through_rate_pct'])
long_delivery = pct_rank(inv['avg_delivery_days'])
low_fill = 1 - pct_rank(inv['fill_rate_pct'])
inv['reorder_priority_score'] = 100 * (0.20*low_stock + 0.25*high_sales + 0.20*high_str + 0.20*long_delivery + 0.15*low_fill)

high_stock = pct_rank(inv['stock_available'])
low_sales = 1 - pct_rank(inv['units_sold'])
low_str = 1 - pct_rank(inv['sell_through_rate_pct'])
low_promo_response = 1 - pct_rank(inv['promotion_response_pct'].fillna(inv['promotion_response_pct'].median()))
slow_recent = 1 - pct_rank(inv['recent_growth_pct'].fillna(0))
inv['overstock_risk_score'] = 100 * (0.25*high_stock + 0.25*low_sales + 0.25*low_str + 0.10*low_promo_response + 0.15*slow_recent)

inv['stock_risk_flag'] = pd.cut(inv['reorder_priority_score'], bins=[-np.inf,55,70,np.inf], labels=['Healthy','Watch','Critical'])
inv['overstock_flag'] = pd.cut(inv['overstock_risk_score'], bins=[-np.inf,55,70,np.inf], labels=['Healthy','Watch','Critical'])
reorder_alerts = inv.sort_values('reorder_priority_score', ascending=False).head(50)
overstock_alerts = inv.sort_values('overstock_risk_score', ascending=False).head(50)

# ----------------------------- Statistics -----------------------------
stat_results: dict[str, Any] = {}
promo_units = df.loc[df['promotion_flag'].eq(1), 'units_sold'].astype(float)
nonpromo_units = df.loc[df['promotion_flag'].eq(0), 'units_sold'].astype(float)
mean_diff = promo_units.mean() - nonpromo_units.mean()
pooled_sd = math.sqrt(((len(promo_units)-1)*promo_units.var(ddof=1) + (len(nonpromo_units)-1)*nonpromo_units.var(ddof=1)) / (len(promo_units)+len(nonpromo_units)-2))
cohens_d = mean_diff / pooled_sd
stat_results['promotion_mean_difference_units'] = float(mean_diff)
stat_results['promotion_cohens_d'] = float(cohens_d)
if stats is not None:
    t_res = stats.ttest_ind(promo_units, nonpromo_units, equal_var=False, nan_policy='omit')
    mw_res = stats.mannwhitneyu(promo_units, nonpromo_units, alternative='two-sided')
    stat_results['welch_t_stat'] = float(t_res.statistic)
    stat_results['welch_t_pvalue'] = float(t_res.pvalue)
    stat_results['mann_whitney_u'] = float(mw_res.statistic)
    stat_results['mann_whitney_pvalue'] = float(mw_res.pvalue)

corr_cols = ['price_unit','promotion_flag','delivery_days','stock_available','delivered_qty','units_sold','revenue','sell_through_rate_row','fill_rate_row']
correlation = df[corr_cols].corr(method='pearson').reset_index().rename(columns={'index':'metric'})

# IQR outlier audit
outlier_rows = []
for col in ['price_unit','delivery_days','stock_available','delivered_qty','units_sold','revenue']:
    q1, q3 = df[col].quantile([0.25,0.75])
    iqr = q3 - q1
    lower = q1 - 1.5*iqr
    upper = q3 + 1.5*iqr
    mask = (df[col] < lower) | (df[col] > upper)
    outlier_rows.append({'column':col,'lower_bound':lower,'upper_bound':upper,'outlier_rows':int(mask.sum()),'outlier_pct':float(mask.mean()*100)})
outlier_summary = pd.DataFrame(outlier_rows)

# Data-construction diagnostics
category_counts = df['category'].value_counts()
region_counts = df['region'].value_counts()
channel_counts = df['channel'].value_counts()
brand_counts = df['brand'].value_counts()
construction = {
    'category_record_count_min': int(category_counts.min()),
    'category_record_count_max': int(category_counts.max()),
    'category_count_cv_pct': float(category_counts.std()/category_counts.mean()*100),
    'region_count_cv_pct': float(region_counts.std()/region_counts.mean()*100),
    'channel_count_cv_pct': float(channel_counts.std()/channel_counts.mean()*100),
    'brand_count_cv_pct': float(brand_counts.std()/brand_counts.mean()*100),
    'each_sku_appears_across_brand_count_min': int(df.groupby('sku')['brand'].nunique().min()),
    'each_sku_appears_across_brand_count_max': int(df.groupby('sku')['brand'].nunique().max()),
    'each_category_appears_across_segment_count_min': int(df.groupby('category')['segment'].nunique().min()),
    'each_category_appears_across_segment_count_max': int(df.groupby('category')['segment'].nunique().max()),
}

# ----------------------------- KPI reconciliation -----------------------------
recon = pd.DataFrame([
    {'kpi':'Record count','stage5_reported':'190,740','presentation_reported':'190,740','csv_recomputed':f"{core['records']:,}",'difference':'0','final_website_value':f"{core['records']:,}",'note':'Exact match.'},
    {'kpi':'Columns','stage5_reported':'14','presentation_reported':'Not stated','csv_recomputed':str(core['columns']),'difference':'0','final_website_value':str(core['columns']),'note':'Exact match for raw schema.'},
    {'kpi':'Date range','stage5_reported':'2022-2024','presentation_reported':'2022-2024','csv_recomputed':f"{core['date_start']} to {core['date_end']}",'difference':'CSV begins 21 Jan 2022','final_website_value':f"{core['date_start']} to {core['date_end']}",'note':'Use exact dates, not only years.'},
    {'kpi':'Brands','stage5_reported':'10','presentation_reported':'18','csv_recomputed':str(core['brands']),'difference':'Presentation +8','final_website_value':str(core['brands']),'note':'CSV confirms Stage 5 report; presentation count is not supported.'},
    {'kpi':'Categories','stage5_reported':'20','presentation_reported':'20','csv_recomputed':str(core['categories']),'difference':'0','final_website_value':str(core['categories']),'note':'Exact match.'},
    {'kpi':'Regions','stage5_reported':'5','presentation_reported':'All major regions','csv_recomputed':str(core['regions']),'difference':'N/A','final_website_value':str(core['regions']),'note':'North, South, East, West and Central.'},
    {'kpi':'Channels','stage5_reported':'4','presentation_reported':'Not stated','csv_recomputed':str(core['channels']),'difference':'0','final_website_value':str(core['channels']),'note':'Kirana, Online, Retail, Supermarket.'},
    {'kpi':'Total revenue','stage5_reported':'Mislabelled as Daily Sales in Appendix A','presentation_reported':'Rs 126.61 Cr','csv_recomputed':f"Rs {core['total_revenue_cr']:.4f} Cr",'difference':f"Rs {core['total_revenue_cr']-126.61:.4f} Cr",'final_website_value':f"Rs {core['total_revenue_cr']:.2f} Cr",'note':'Presentation is confirmed by CSV.'},
    {'kpi':'Total units sold','stage5_reported':'Not clearly reported as total','presentation_reported':'13.47 Million','csv_recomputed':f"{core['total_units_million']:.6f} Million",'difference':f"{core['total_units_million']-13.47:.6f} Million",'final_website_value':f"{core['total_units_million']:.2f} Million",'note':'Presentation is confirmed after rounding.'},
    {'kpi':'Average delivery days','stage5_reported':'Roughly 3 days; chart artifact 297-304','presentation_reported':'3.0 days','csv_recomputed':f"{core['avg_delivery_days']:.4f} days",'difference':f"{core['avg_delivery_days']-3.0:.4f} days",'final_website_value':f"{core['avg_delivery_days']:.2f} days",'note':'Use actual 1-5 day averages; never display 297-304 as days.'},
    {'kpi':'Fill rate','stage5_reported':'90.76%','presentation_reported':'90.82%','csv_recomputed':f"{core['fill_rate_pct']:.4f}%",'difference':f"vs Stage 5: {core['fill_rate_pct']-90.76:.4f} pp",'final_website_value':f"{core['fill_rate_pct']:.2f}%",'note':'Ratio of totals matches presentation. Row-average DAX would incorrectly produce a much larger value.'},
    {'kpi':'Sell-through rate','stage5_reported':'23.68%','presentation_reported':'Not stated','csv_recomputed':f"{core['sell_through_rate_pct']:.4f}% weighted; {core['row_average_sell_through_rate_pct']:.4f}% row-average",'difference':f"Weighted vs report: {core['sell_through_rate_pct']-23.68:.4f} pp",'final_website_value':f"{core['sell_through_rate_pct']:.2f}%",'note':'Reported 23.68% cannot be reproduced from the full CSV using Appendix A or Appendix C formulas.'},
    {'kpi':'Daily sales','stage5_reported':'2,165.62','presentation_reported':'Not stated','csv_recomputed':f"{core['avg_daily_units_calendar']:.2f} units/calendar day",'difference':f"{core['avg_daily_units_calendar']-2165.62:.2f}",'final_website_value':f"{core['avg_daily_units_calendar']:.2f} units/day",'note':'2,165.62 may reflect an undocumented filter or a misnamed measure.'},
    {'kpi':'Promotion lift - units','stage5_reported':'Patanjali 41%, Nestle 37%, Britannia 36%, HUL 35%','presentation_reported':'Not numeric','csv_recomputed':f"Overall {core['promotion_lift_units_pct']:.2f}%; top brand {promo_brand.iloc[0]['brand']} {promo_brand.iloc[0]['unit_lift_pct']:.2f}%",'difference':'Reported brand ranking not reproduced','final_website_value':f"Overall {core['promotion_lift_units_pct']:.2f}%",'note':'Observational association, not causal impact.'},
])
recon.to_csv(RECON_PATH, index=False)

# ----------------------------- Save tables -----------------------------
tables = {
    'brand_summary.csv': brand_summary,
    'category_summary.csv': category_summary,
    'region_summary.csv': region_summary,
    'channel_summary.csv': channel_summary,
    'pack_type_summary.csv': pack_summary,
    'segment_summary.csv': segment_summary,
    'yearly_trend.csv': yearly,
    'monthly_trend.csv': monthly,
    'quarterly_trend.csv': quarterly,
    'daily_trend.csv': daily,
    'weekday_analysis.csv': weekday,
    'sku_summary.csv': sku_summary,
    'promotion_overall.csv': promo_group.reset_index(),
    'promotion_by_brand.csv': promo_brand,
    'promotion_by_category.csv': promo_category,
    'promotion_by_region.csv': promo_region,
    'promotion_by_channel.csv': promo_channel,
    'promotion_by_pack_type.csv': promo_pack,
    'promotion_by_price_band.csv': promo_price_band,
    'delivery_by_channel.csv': delivery_by_channel,
    'supply_chain_by_region.csv': supply_region,
    'delivery_status_overall.csv': status_overall,
    'delivery_distribution.csv': delivery_distribution,
    'inventory_reorder_alerts_top50.csv': reorder_alerts,
    'inventory_overstock_alerts_top50.csv': overstock_alerts,
    'correlation_matrix.csv': correlation,
    'outlier_summary.csv': outlier_summary,
    'cleaning_log.csv': pd.DataFrame(cleaning_log),
    'sample_data_100.csv': df[EXPECTED_COLUMNS + ['revenue','delivery_status','sell_through_rate_row','fill_rate_row']].head(100),
}
for name, table in tables.items():
    table.to_csv(OUT_DIR / name, index=False)

# ----------------------------- Frontend JSON -----------------------------
frontend = {
    'project': {
        'title': 'Smart Supply Chain Intelligence',
        'subtitle': 'FMCG analytics portfolio built from the full uploaded CSV and reconciled against both PDFs.',
        'source_files': [
            'indian_fmcg_high_quality_dataset (1).csv',
            'FMCG_Stage5_Dashboard_Report(1) (1).pdf',
            'Smart Supply Chain Intelligence - FMCG Dashboard (1).pdf',
        ]
    },
    'generated_from': {'records': core['records'], 'date_start': core['date_start'], 'date_end': core['date_end']},
    'kpis': core,
    'data_quality': {
        'rows_before': rows_before,
        'rows_after': int(len(df)),
        'rows_removed': 0,
        'rows_flagged': flagged_rows,
        'missing_values_by_column': jsafe(missing_counts.to_dict()),
        'duplicate_rows': duplicate_count,
        'missing_expected_columns': missing_expected,
        'extra_columns': extra_columns,
        'construction_diagnostics': construction,
    },
    'reconciliation': records(recon),
    'charts': {
        'yearly_trend': records(yearly),
        'monthly_trend': records(monthly),
        'brand_summary': records(brand_summary),
        'category_summary': records(category_summary),
        'region_summary': records(region_summary),
        'channel_summary': records(channel_summary),
        'promotion_by_brand': records(promo_brand),
        'promotion_by_category': records(promo_category),
        'promotion_by_region': records(promo_region),
        'promotion_by_channel': records(promo_channel),
        'delivery_by_channel': records(delivery_by_channel),
        'supply_chain_by_region': records(supply_region),
        'delivery_status': records(status_overall),
        'weekday_analysis': records(weekday),
        'top_skus': records(sku_summary, 20),
        'bottom_skus': records(sku_summary.sort_values('revenue'), 20),
        'reorder_alerts': records(reorder_alerts, 30),
        'overstock_alerts': records(overstock_alerts, 30),
        'correlation_matrix': records(correlation),
    },
    'statistical_analysis': stat_results,
    'methodology': {
        'revenue': 'price_unit * units_sold',
        'fill_rate_pct': 'SUM(delivered_qty) / SUM(stock_available) * 100',
        'sell_through_rate_pct': 'SUM(units_sold) / SUM(stock_available) * 100, following the Stage 5 Appendix A denominator',
        'promotion_lift_pct': '(mean units on promoted rows - mean units on non-promoted rows) / mean non-promoted units * 100',
        'delivery_status': {'Healthy':'<=2 days','Watch':'>2 and <=4 days','Critical':'>4 days'},
        'reorder_priority_score': '0.20 low-stock + 0.25 high-sales + 0.20 high-STR + 0.20 long-delivery + 0.15 low-fill; percentile-normalized to 0-100',
        'overstock_risk_score': '0.25 high-stock + 0.25 low-sales + 0.25 low-STR + 0.10 weak-promotion-response + 0.15 slow-recent-growth; percentile-normalized to 0-100',
    },
    'limitations': [
        'Promotion results are observational associations and do not prove causality.',
        'stock_available and delivered_qty are row-level quantities; totals are not a current warehouse snapshot.',
        'The dataset is unusually balanced and shows strong signs of synthetic construction, so business conclusions should be treated as portfolio-demo insights rather than real-company claims.',
        'The report value 23.68% for sell-through and 2,165.62 for daily sales are not reproducible from the full CSV without undocumented filters or alternate formulas.',
    ]
}
JSON_PATH.write_text(json.dumps(jsafe(frontend), indent=2, ensure_ascii=False), encoding='utf-8')

# ----------------------------- Markdown report -----------------------------
top_brand = brand_summary.iloc[0]
top_category = category_summary.iloc[0]
top_region = region_summary.iloc[0]
top_channel = channel_summary.iloc[0]
fastest_channel = delivery_by_channel.sort_values('avg_delivery_days').iloc[0]
slowest_channel = delivery_by_channel.sort_values('avg_delivery_days', ascending=False).iloc[0]
strongest_promo_brand = promo_brand.iloc[0]
weakest_promo_brand = promo_brand.iloc[-1]
weekend_mean = df.loc[df['is_weekend'], 'units_sold'].mean()
weekday_mean = df.loc[~df['is_weekend'], 'units_sold'].mean()
weekend_lift = (weekend_mean/weekday_mean - 1)*100

top5_brand_share = brand_summary.head(5)['revenue_share_pct'].sum()
top5_category_share = category_summary.head(5)['revenue_share_pct'].sum()

report = f"""# FMCG Full-CSV Analysis and PDF Reconciliation

## Scope

This analysis uses the full uploaded CSV with **{core['records']:,} rows** and both uploaded PDFs as reference sources. No KPI has been copied blindly from the PDFs. Reported values were recomputed and reconciled against the raw data.

## Executive result

- **Revenue:** Rs {core['total_revenue_cr']:.2f} Cr, confirming the jury presentation's Rs 126.61 Cr after rounding.
- **Units sold:** {core['total_units_million']:.2f} million, confirming the presentation's 13.47 million.
- **Average delivery:** {core['avg_delivery_days']:.2f} days. The Stage 5 visual values around 297-304 are aggregation artifacts, not literal days.
- **Fill rate:** {core['fill_rate_pct']:.2f}% using the weighted ratio `SUM(delivered_qty) / SUM(stock_available)`. This confirms the presentation's 90.82%.
- **Sell-through rate:** {core['sell_through_rate_pct']:.2f}% using the Appendix A denominator and weighted totals. The reported 23.68% is not reproducible from this CSV.
- **Promotion association:** promoted rows average **{core['promotion_lift_units_pct']:.2f}% more units** and **{core['promotion_lift_revenue_pct']:.2f}% more revenue per record** than non-promoted rows. This is association, not proof of causal lift.

## 1. Data quality audit

| Check | Result |
|---|---:|
| Rows | {core['records']:,} |
| Raw columns | {core['columns']} |
| Date range | {core['date_start']} to {core['date_end']} |
| Missing cells | {core['missing_values']:,} |
| Exact duplicate rows | {core['duplicate_rows']:,} |
| Invalid/negative rows flagged | {core['flagged_invalid_rows']:,} |
| Brands | {core['brands']} |
| SKUs | {core['skus']} |
| Categories | {core['categories']} |
| Segments | {core['segments']} |
| Channels | {core['channels']} |
| Regions | {core['regions']} |
| Pack types | {core['pack_types']} |

No rows were silently removed. Region labels were standardized from forms such as `WestIndia` to `West India`.

### Data realism warning

The table is exceptionally balanced: category row counts range from **{construction['category_record_count_min']:,} to {construction['category_record_count_max']:,}**, and every SKU appears under exactly **{construction['each_sku_appears_across_brand_count_min']} brands**. Every category also appears under all **{construction['each_category_appears_across_segment_count_min']} segments**. Those patterns strongly suggest a generated or synthetic portfolio dataset, not an untouched FMCG transaction export. Use it for analytics demonstration, not for claims about a real company.

## 2. KPI reconciliation

The complete comparison is in `fmcg_kpi_reconciliation.csv`.

| KPI | PDF claim | CSV result | Decision |
|---|---|---|---|
| Revenue | Rs 126.61 Cr | Rs {core['total_revenue_cr']:.4f} Cr | Confirmed |
| Units sold | 13.47 M | {core['total_units_million']:.6f} M | Confirmed |
| Fill rate | 90.76%-90.82% | {core['fill_rate_pct']:.4f}% | Use {core['fill_rate_pct']:.2f}% |
| Average delivery | 3.0 days | {core['avg_delivery_days']:.4f} days | Confirmed |
| Brands | 10 in report, 18 in presentation | {core['brands']} | Presentation is wrong |
| Sell-through | 23.68% | {core['sell_through_rate_pct']:.4f}% weighted | Report value not reproducible |
| Daily sales | 2,165.62 | {core['avg_daily_units_calendar']:.2f} units/calendar day | Report metric/filter is undocumented |
| Top promotion brand | Patanjali 41% | {strongest_promo_brand['brand']} {strongest_promo_brand['unit_lift_pct']:.2f}% | Report ranking not reproduced |

A crucial formula issue exists in the Stage 5 appendix: the DAX says `AVERAGE(fill_rate)`, but that row-average produces **{core['row_average_fill_rate_pct']:.2f}%**. The reported 90.82% is obtained by the weighted ratio of totals. The website should use the weighted result and explain it.

## 3. Revenue and sales

- **Top revenue brand:** {top_brand['brand']} at Rs {top_brand['revenue']/1e7:.2f} Cr ({top_brand['revenue_share_pct']:.2f}% share).
- **Top revenue category:** {top_category['category']} at Rs {top_category['revenue']/1e7:.2f} Cr ({top_category['revenue_share_pct']:.2f}% share).
- **Top region:** {top_region['region']} at Rs {top_region['revenue']/1e7:.2f} Cr ({top_region['revenue_share_pct']:.2f}% share).
- **Top channel:** {top_channel['channel']} at Rs {top_channel['revenue']/1e7:.2f} Cr ({top_channel['revenue_share_pct']:.2f}% share).
- The top five brands contribute **{top5_brand_share:.2f}%** of revenue. Brand concentration is low because revenue is almost evenly split.
- The top five categories contribute **{top5_category_share:.2f}%** of revenue. Category concentration is materially higher than brand concentration.
- Weekend records average **{weekend_mean:.2f} units**, versus **{weekday_mean:.2f}** on weekdays, a **{weekend_lift:.2f}%** higher average.

### Top five categories by revenue

{category_summary[['category','revenue','revenue_share_pct','units_sold','avg_price']].head(5).to_markdown(index=False, floatfmt='.2f')}

### Top five brands by revenue

{brand_summary[['brand','revenue','revenue_share_pct','units_sold','avg_price']].head(5).to_markdown(index=False, floatfmt='.2f')}

## 4. Promotion analysis

Promotions occur on **{core['promotion_share_pct']:.2f}%** of rows.

- Overall unit lift association: **{core['promotion_lift_units_pct']:.2f}%**.
- Overall revenue lift association: **{core['promotion_lift_revenue_pct']:.2f}%**.
- Strongest brand association: **{strongest_promo_brand['brand']} ({strongest_promo_brand['unit_lift_pct']:.2f}%)**.
- Weakest brand association: **{weakest_promo_brand['brand']} ({weakest_promo_brand['unit_lift_pct']:.2f}%)**. It is still positive in this dataset.
- Cohen's d for promoted versus non-promoted unit sales is **{cohens_d:.3f}**, a small-to-moderate standardized difference. With 190,740 rows, tiny p-values are inevitable; effect size matters more than statistical significance.

### Brand promotion lift

{promo_brand[['brand','nonpromo_mean_units','promo_mean_units','unit_lift_pct','revenue_lift_pct']].to_markdown(index=False, floatfmt='.2f')}

**Causality disclaimer:** The analysis identifies associations in the available dataset and does not prove causal impact.

## 5. Supply chain

- Fastest channel: **{fastest_channel['channel']}**, {fastest_channel['avg_delivery_days']:.3f} average days.
- Slowest channel: **{slowest_channel['channel']}**, {slowest_channel['avg_delivery_days']:.3f} average days.
- The gap is only **{slowest_channel['avg_delivery_days']-fastest_channel['avg_delivery_days']:.3f} days**, so the channels are operationally almost identical.
- Delivery status follows the PDF's rule: Healthy <=2, Watch >2 to 4, Critical >4 days.

{delivery_by_channel[['channel','avg_delivery_days','fill_rate_pct','sell_through_rate_pct','Healthy','Watch','Critical']].to_markdown(index=False, floatfmt='.2f')}

The 297-304 values shown in the Stage 5 dashboard are not valid delivery-day averages. The raw field only ranges from 1 to 5, and actual channel averages are near 3 days.

## 6. Inventory intelligence

Two transparent percentile scores were built for dashboard use:

- **Reorder priority:** low stock, high sales, high sell-through, long delivery, and low fill rate.
- **Overstock risk:** high stock, low sales, low sell-through, weak promotion response, and slow recent growth.

These are ranking scores, not true forecasts. The top 50 alerts are exported separately. Also, `stock_available` and `delivered_qty` are row-level quantities, so their full-dataset sums should not be presented as today's physical inventory.

## 7. Statistical relationships

- Price and units sold are negatively correlated, while price and revenue are positively correlated. This is expected because revenue mechanically includes price.
- Delivery days show almost no linear relationship with units or revenue in this generated dataset.
- Promotion has a positive relationship with units, but the data-generation process may have embedded that pattern.
- Revenue outliers are mostly high-value transactions caused by the multiplication of high price and high units, not invalid records.

## 8. Values recommended for the website

| Website KPI | Verified value |
|---|---:|
| Total Revenue | Rs {core['total_revenue_cr']:.2f} Cr |
| Total Units Sold | {core['total_units_million']:.2f} M |
| Fill Rate | {core['fill_rate_pct']:.2f}% |
| Sell-Through Rate | {core['sell_through_rate_pct']:.2f}% |
| Average Delivery Days | {core['avg_delivery_days']:.2f} |
| Average Daily Units | {core['avg_daily_units_calendar']:.2f} |
| Promotion Lift - Units | {core['promotion_lift_units_pct']:.2f}% |
| Brands | {core['brands']} |
| Categories | {core['categories']} |
| Regions | {core['regions']} |
| Channels | {core['channels']} |

Do not use the PDF's 18-brand claim, 23.68% sell-through claim, 2,165.62 daily-sales value, or 297-304 delivery-day bars as verified facts.

## 9. Output files

- `fmcg_frontend_data.json`: chart-ready data and reconciled KPI values for a static HTML/CSS/JavaScript website.
- `fmcg_kpi_reconciliation.csv`: reported-versus-recomputed KPI table.
- `fmcg_analysis_tables/`: detailed trend, dimension, promotion, supply-chain, inventory, correlation, and audit tables.
- `analyze_fmcg.py`: reproducible analysis script.
"""
REPORT_PATH.write_text(report, encoding='utf-8')

# Bundle useful outputs, excluding the original 19 MB CSV and PDFs.
with zipfile.ZipFile(ZIP_PATH, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
    zf.write(REPORT_PATH, REPORT_PATH.name)
    zf.write(JSON_PATH, JSON_PATH.name)
    zf.write(RECON_PATH, RECON_PATH.name)
    zf.write(Path('/mnt/data/analyze_fmcg.py'), 'analyze_fmcg.py')
    for file in sorted(OUT_DIR.glob('*.csv')):
        zf.write(file, f'fmcg_analysis_tables/{file.name}')

print(json.dumps({
    'report': str(REPORT_PATH),
    'frontend_json': str(JSON_PATH),
    'reconciliation': str(RECON_PATH),
    'package': str(ZIP_PATH),
    'core_kpis': core,
    'top_brand': top_brand['brand'],
    'top_category': top_category['category'],
    'strongest_promo_brand': strongest_promo_brand['brand'],
}, indent=2, default=jsafe))
