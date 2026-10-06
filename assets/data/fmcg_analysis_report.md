# FMCG Full-CSV Analysis and PDF Reconciliation

## Scope

This analysis uses the full uploaded CSV with **190,740 rows** and both uploaded PDFs as reference sources. No KPI has been copied blindly from the PDFs. Reported values were recomputed and reconciled against the raw data.

## Executive result

- **Revenue:** Rs 126.61 Cr, confirming the jury presentation's Rs 126.61 Cr after rounding.
- **Units sold:** 13.47 million, confirming the presentation's 13.47 million.
- **Average delivery:** 3.00 days. The Stage 5 visual values around 297-304 are aggregation artifacts, not literal days.
- **Fill rate:** 90.82% using the weighted ratio `SUM(delivered_qty) / SUM(stock_available)`. This confirms the presentation's 90.82%.
- **Sell-through rate:** 25.73% using the Appendix A denominator and weighted totals. The reported 23.68% is not reproducible from this CSV.
- **Promotion association:** promoted rows average **28.69% more units** and **26.85% more revenue per record** than non-promoted rows. This is association, not proof of causal lift.

## 1. Data quality audit

| Check | Result |
|---|---:|
| Rows | 190,740 |
| Raw columns | 14 |
| Date range | 2022-01-21 to 2024-12-31 |
| Missing cells | 0 |
| Exact duplicate rows | 0 |
| Invalid/negative rows flagged | 0 |
| Brands | 10 |
| SKUs | 60 |
| Categories | 20 |
| Segments | 9 |
| Channels | 4 |
| Regions | 5 |
| Pack types | 5 |

No rows were silently removed. Region labels were standardized from forms such as `WestIndia` to `West India`.

### Data realism warning

The table is exceptionally balanced: category row counts range from **9,537 to 9,537**, and every SKU appears under exactly **10 brands**. Every category also appears under all **9 segments**. Those patterns strongly suggest a generated or synthetic portfolio dataset, not an untouched FMCG transaction export. Use it for analytics demonstration, not for claims about a real company.

## 2. KPI reconciliation

The complete comparison is in `fmcg_kpi_reconciliation.csv`.

| KPI | PDF claim | CSV result | Decision |
|---|---|---|---|
| Revenue | Rs 126.61 Cr | Rs 126.6104 Cr | Confirmed |
| Units sold | 13.47 M | 13.474517 M | Confirmed |
| Fill rate | 90.76%-90.82% | 90.8172% | Use 90.82% |
| Average delivery | 3.0 days | 2.9963 days | Confirmed |
| Brands | 10 in report, 18 in presentation | 10 | Presentation is wrong |
| Sell-through | 23.68% | 25.7291% weighted | Report value not reproducible |
| Daily sales | 2,165.62 | 12522.79 units/calendar day | Report metric/filter is undocumented |
| Top promotion brand | Patanjali 41% | Dabur 31.39% | Report ranking not reproduced |

A crucial formula issue exists in the Stage 5 appendix: the DAX says `AVERAGE(fill_rate)`, but that row-average produces **127.97%**. The reported 90.82% is obtained by the weighted ratio of totals. The website should use the weighted result and explain it.

## 3. Revenue and sales

- **Top revenue brand:** Dabur at Rs 12.97 Cr (10.24% share).
- **Top revenue category:** Tea at Rs 22.97 Cr (18.14% share).
- **Top region:** West India at Rs 25.45 Cr (20.10% share).
- **Top channel:** Retail at Rs 31.75 Cr (25.08% share).
- The top five brands contribute **50.57%** of revenue. Brand concentration is low because revenue is almost evenly split.
- The top five categories contribute **49.52%** of revenue. Category concentration is materially higher than brand concentration.
- Weekend records average **73.18 units**, versus **69.63** on weekdays, a **5.09%** higher average.

### Top five categories by revenue

| category   |      revenue |   revenue_share_pct |   units_sold |   avg_price |
|:-----------|-------------:|--------------------:|-------------:|------------:|
| Tea        | 229700824.84 |               18.14 |      1151879 |      199.89 |
| Coffee     | 114343366.51 |                9.03 |       458255 |      250.32 |
| Milk       | 109076802.63 |                8.62 |      2184792 |       50.03 |
| Butter     |  96809188.46 |                7.65 |       323611 |      300.19 |
| Detergent  |  77087392.75 |                6.09 |       386233 |      200.11 |

### Top five brands by revenue

| brand     |      revenue |   revenue_share_pct |   units_sold |   avg_price |
|:----------|-------------:|--------------------:|-------------:|------------:|
| Dabur     | 129666312.26 |               10.24 |      1360443 |      132.44 |
| Patanjali | 128732358.13 |               10.17 |      1366516 |      131.18 |
| ITC       | 128280528.10 |               10.13 |      1350770 |      132.01 |
| MDH       | 127067327.80 |               10.04 |      1352120 |      130.79 |
| Britannia | 126482100.75 |                9.99 |      1360084 |      130.75 |

## 4. Promotion analysis

Promotions occur on **15.11%** of rows.

- Overall unit lift association: **28.69%**.
- Overall revenue lift association: **26.85%**.
- Strongest brand association: **Dabur (31.39%)**.
- Weakest brand association: **ITC (26.38%)**. It is still positive in this dataset.
- Cohen's d for promoted versus non-promoted unit sales is **0.353**, a small-to-moderate standardized difference. With 190,740 rows, tiny p-values are inevitable; effect size matters more than statistical significance.

### Brand promotion lift

| brand     |   nonpromo_mean_units |   promo_mean_units |   unit_lift_pct |   revenue_lift_pct |
|:----------|----------------------:|-------------------:|----------------:|-------------------:|
| Dabur     |                 67.27 |              88.38 |           31.39 |              22.41 |
| MDH       |                 68.11 |              88.74 |           30.30 |              28.32 |
| Nestle    |                 67.49 |              87.80 |           30.08 |              25.91 |
| Amul      |                 67.38 |              87.35 |           29.63 |              27.49 |
| Britannia |                 67.67 |              87.04 |           28.64 |              27.95 |
| HUL       |                 67.76 |              86.97 |           28.34 |              29.57 |
| Parle     |                 67.29 |              86.07 |           27.91 |              26.11 |
| Godrej    |                 67.96 |              86.39 |           27.12 |              30.68 |
| Patanjali |                 68.48 |              87.05 |           27.12 |              25.43 |
| ITC       |                 67.68 |              85.54 |           26.38 |              25.01 |

**Causality disclaimer:** The analysis identifies associations in the available dataset and does not prove causal impact.

## 5. Supply chain

- Fastest channel: **Supermarket**, 2.993 average days.
- Slowest channel: **Online**, 3.003 average days.
- The gap is only **0.009 days**, so the channels are operationally almost identical.
- Delivery status follows the PDF's rule: Healthy <=2, Watch >2 to 4, Critical >4 days.

| channel     |   avg_delivery_days |   fill_rate_pct |   sell_through_rate_pct |   Healthy |   Watch |   Critical |
|:------------|--------------------:|----------------:|------------------------:|----------:|--------:|-----------:|
| Kirana      |                3.00 |           90.54 |                   25.52 |     40.16 |   40.03 |      19.81 |
| Online      |                3.00 |           90.54 |                   25.73 |     39.87 |   40.17 |      19.95 |
| Retail      |                2.99 |           91.36 |                   25.91 |     40.30 |   39.78 |      19.92 |
| Supermarket |                2.99 |           90.84 |                   25.75 |     40.15 |   40.01 |      19.85 |

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
| Total Revenue | Rs 126.61 Cr |
| Total Units Sold | 13.47 M |
| Fill Rate | 90.82% |
| Sell-Through Rate | 25.73% |
| Average Delivery Days | 3.00 |
| Average Daily Units | 12522.79 |
| Promotion Lift - Units | 28.69% |
| Brands | 10 |
| Categories | 20 |
| Regions | 5 |
| Channels | 4 |

Do not use the PDF's 18-brand claim, 23.68% sell-through claim, 2,165.62 daily-sales value, or 297-304 delivery-day bars as verified facts.

## 9. Output files

- `fmcg_frontend_data.json`: chart-ready data and reconciled KPI values for a static HTML/CSS/JavaScript website.
- `fmcg_kpi_reconciliation.csv`: reported-versus-recomputed KPI table.
- `fmcg_analysis_tables/`: detailed trend, dimension, promotion, supply-chain, inventory, correlation, and audit tables.
- `analyze_fmcg.py`: reproducible analysis script.
