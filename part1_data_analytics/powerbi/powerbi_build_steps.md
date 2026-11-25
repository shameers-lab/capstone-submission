# Power BI dashboard build and verification

The required dashboard visuals, measures, units, filters, and traffic-category boundaries are specified in `dashboard_spec.md`. The checked-in `Traffic_Data_Analysis.pbix` should be opened in Power BI Desktop and checked against that specification before submission. Power BI Desktop validation was not available during this work session.

## Data source and Power Query

The raw `Metro_Interstate_Traffic_Volume.csv` is not included in this checkout. Obtain the source dataset from the UCI Machine Learning Repository and preserve the original file. In Power Query, open `Traffic_Power_Query.m` and replace its placeholder path with the raw CSV location. The query declares the nine source fields and types, replaces missing holiday values with an empty no-holiday category, derives date/year/hour and Celsius temperature, assigns non-overlapping traffic categories (`<4500` Low, `4500–5500` Medium, `>5500` High), and adds flags for zero-K temperature and extreme rainfall. Review flagged records; do not remove associated traffic observations automatically.

`traffic_dashboard_data.csv` is a prepared 48,204-row extract that can be used to inspect the prepared fields when the raw source is unavailable. It is not a substitute for validating the query against the original CSV.

## Measures

Use measures equivalent to:

```DAX
Average Traffic = AVERAGE('traffic'[traffic_volume])
Average Temperature (C) = AVERAGE('traffic'[temp_c])
Observation Hours = COUNTROWS('traffic')
```

Confirm the table name after loading the data. The hours card counts hourly records, not elapsed clock time; slicers and filters apply to all cards.

## Required pages/visuals

1. Daily average traffic line chart, filtered to dates from 2015-01-01 through 2017-12-31.
2. 2017 average traffic by hour column chart, with hours sorted numerically from 0 to 23.
3. Average traffic by `weather_main`; identify the maximum, minimum, and difference, and show counts so small groups are visible.
4. Temperature-versus-traffic scatter using `temp_c` and `traffic_volume`; retain outliers and show higher-traffic temperature ranges.
5. Three KPI cards: hourly observation count, average traffic (vehicles/hour), and average temperature (°C).
6. Slicers for hour, `weather_main`, and traffic category.

Use average traffic consistently and label units. Define traffic categories as `<4500` Low, `4500–5500` Medium (inclusive), and `>5500` High. Explicitly document any visual-level filters and how missing or flagged values are handled. Do not describe association as causation.
