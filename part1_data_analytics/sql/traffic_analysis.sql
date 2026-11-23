-- The source CSV is imported without dropping its 17 observed exact duplicates.
-- Timestamps in this dataset use the text format YYYY-MM-DD HH:MM:SS.

-- Verify row count, date span, and source schema.
SELECT COUNT(*) AS row_count,
       MIN(date_time) AS first_timestamp,
       MAX(date_time) AS last_timestamp
FROM traffic;

PRAGMA table_info(traffic);

-- Annual totals and observation coverage. 2018 is partial; the assignment comparison
-- requests 2012-2017. Sums should be interpreted alongside record_count and mean.
SELECT CAST(strftime('%Y', date_time) AS INTEGER) AS year,
       COUNT(*) AS record_count,
       SUM(traffic_volume) AS total_traffic_volume,
       AVG(traffic_volume) AS mean_traffic_volume
FROM traffic
WHERE CAST(strftime('%Y', date_time) AS INTEGER) BETWEEN 2012 AND 2017
GROUP BY year
ORDER BY year;

-- Year-over-year total and percentage changes (SQLite window functions).
WITH annual AS (
    SELECT CAST(strftime('%Y', date_time) AS INTEGER) AS year,
           COUNT(*) AS record_count,
           SUM(traffic_volume) AS total_volume
    FROM traffic
    WHERE CAST(strftime('%Y', date_time) AS INTEGER) BETWEEN 2012 AND 2017
    GROUP BY year
)
SELECT year, record_count, total_volume,
       total_volume - LAG(total_volume) OVER (ORDER BY year) AS change_from_previous_year,
       100.0 * (total_volume - LAG(total_volume) OVER (ORDER BY year))
           / NULLIF(LAG(total_volume) OVER (ORDER BY year), 0) AS percent_change
FROM annual
ORDER BY year;

-- Holiday temperature and traffic samples for New Year's Day and Labor Day.
-- Report sample counts; many holidays have only one or two hourly records.
SELECT holiday,
       CAST(strftime('%Y', date_time) AS INTEGER) AS year,
       COUNT(*) AS record_count,
       AVG(temp) AS mean_temperature_kelvin,
       AVG(temp - 273.15) AS mean_temperature_celsius,
       AVG(traffic_volume) AS mean_traffic_volume
FROM traffic
WHERE holiday IN ('New Years Day', 'Labor Day')
  AND CAST(strftime('%Y', date_time) AS INTEGER) BETWEEN 2015 AND 2017
GROUP BY holiday, year
ORDER BY holiday, year;

-- Descriptive statistics. SQLite does not provide median/stddev in its core;
-- calculate these in analyze_part1.py with Pandas (sample variance, ddof=1).
SELECT COUNT(*) AS n,
       AVG(traffic_volume) AS mean_traffic_volume,
       MIN(traffic_volume) AS min_traffic_volume,
       MAX(traffic_volume) AS max_traffic_volume,
       MAX(traffic_volume) - MIN(traffic_volume) AS traffic_range,
       AVG(temp) AS mean_temperature_kelvin
FROM traffic;

-- Congestion probabilities: congestion is strictly > 5,500; clear is weather_main=Clear.
SELECT COUNT(*) AS n,
       AVG(CASE WHEN traffic_volume > 5500 THEN 1.0 ELSE 0.0 END) AS p_congestion,
       AVG(CASE WHEN lower(weather_main) = 'clear' THEN 1.0 ELSE 0.0 END) AS p_clear,
       AVG(CASE WHEN traffic_volume > 5500 AND lower(weather_main) = 'clear'
                THEN 1.0 ELSE 0.0 END) AS p_clear_and_congestion,
       SUM(CASE WHEN traffic_volume > 5500 AND lower(weather_main) = 'clear' THEN 1 ELSE 0 END)
         * 1.0 / NULLIF(SUM(CASE WHEN traffic_volume > 5500 THEN 1 ELSE 0 END), 0)
         AS p_clear_given_congestion,
       SUM(CASE WHEN traffic_volume > 5500 AND temp > 292 THEN 1 ELSE 0 END)
         * 1.0 / NULLIF(SUM(CASE WHEN traffic_volume > 5500 THEN 1 ELSE 0 END), 0)
         AS p_high_temperature_given_congestion
FROM traffic;

-- Compare P(clear AND congestion) with P(clear)*P(congestion) for independence.
WITH events AS (
    SELECT AVG(CASE WHEN lower(weather_main) = 'clear' THEN 1.0 ELSE 0.0 END) AS p_clear,
           AVG(CASE WHEN traffic_volume > 5500 THEN 1.0 ELSE 0.0 END) AS p_congestion,
           AVG(CASE WHEN lower(weather_main) = 'clear' AND traffic_volume > 5500
                    THEN 1.0 ELSE 0.0 END) AS p_joint
    FROM traffic
)
SELECT p_clear, p_congestion, p_joint,
       p_clear * p_congestion AS product_if_independent,
       p_joint - p_clear * p_congestion AS difference
FROM events;

-- Odds ratio: clear versus the Clouds category specifically; other weather categories
-- are excluded. Odds = congested / not congested within each of the two categories.
WITH counts AS (
    SELECT
      SUM(CASE WHEN lower(weather_main) = 'clear' AND traffic_volume > 5500 THEN 1 ELSE 0 END) AS clear_congested,
      SUM(CASE WHEN lower(weather_main) = 'clear' AND traffic_volume <= 5500 THEN 1 ELSE 0 END) AS clear_not_congested,
      SUM(CASE WHEN lower(weather_main) = 'clouds' AND traffic_volume > 5500 THEN 1 ELSE 0 END) AS clouds_congested,
      SUM(CASE WHEN lower(weather_main) = 'clouds' AND traffic_volume <= 5500 THEN 1 ELSE 0 END) AS clouds_not_congested
    FROM traffic
)
SELECT *,
       (1.0 * clear_congested / NULLIF(clear_not_congested, 0))
       / NULLIF(1.0 * clouds_congested / NULLIF(clouds_not_congested, 0), 0)
         AS clear_vs_clouds_odds_ratio
FROM counts;

-- Power BI weather visual source: average volume, sorted for highest/lowest.
SELECT weather_main, COUNT(*) AS record_count, AVG(traffic_volume) AS mean_traffic_volume
FROM traffic
GROUP BY weather_main
ORDER BY mean_traffic_volume;
