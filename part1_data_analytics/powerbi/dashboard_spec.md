# Power BI dashboard specification

Use hourly observations from the Metro Interstate Traffic Volume data. Keep traffic in vehicles per hour and temperature in Celsius in visuals; the source `temp` field is Kelvin. The main reporting window for daily trends is 2015–2017, and the 2017 hourly chart must be filtered to 2017. Use average traffic unless a visual below states otherwise. Preserve dates as dates and do not infer missing observations.

## Required visuals

1. **Daily average traffic, 2015–2017:** line chart with calendar date on the x-axis and average `traffic_volume` on the y-axis; filter dates to 2015-01-01 through 2017-12-31.
2. **2017 average traffic by hour:** column chart with hour 0–23 on the x-axis and average `traffic_volume` on the y-axis; filter year to 2017.
3. **Average traffic by weather:** bar chart grouped by `weather_main`; show average traffic and call out the highest category, lowest category, and their difference. Display record counts to provide context for small groups.
4. **Temperature versus traffic:** scatter plot with `temp_c` on x and `traffic_volume` on y. Show higher-traffic temperature ranges and retain/identify outliers rather than silently dropping them.

## KPI cards and slicers

Provide cards for:

- Number of hourly observations (hours), respecting report filters.
- Average traffic volume (vehicles/hour).
- Average temperature (°C).

Provide slicers for hour, `weather_main`, and traffic category. Define categories without gaps or overlaps: `<4500` Low, `4500–5500` Medium (both endpoints inclusive), and `>5500` High.

Document visual-level filters, aggregation, date range, units, and any excluded invalid values. The Power Query source flags zero-K temperatures and extreme rainfall for review; do not silently treat those flags as valid measurements or delete associated traffic observations.
