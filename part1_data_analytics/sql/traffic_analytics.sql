-- Smart City Traffic Capstone
-- Part 1: Data Analytics
-- Dataset: Metro_Interstate_Traffic_Volume.csv
-- These SQLite queries use the checked-in database table named traffic.

-- 1. Basic inspection
SELECT
    COUNT(*) AS total_rows,
    MIN(temp) AS min_temp,
    MAX(temp) AS max_temp,
    AVG(temp) AS avg_temp,
    MIN(traffic_volume) AS min_traffic,
    MAX(traffic_volume) AS max_traffic,
    AVG(traffic_volume) AS avg_traffic
FROM traffic;

-- 2. Peak traffic hours by time-of-day
SELECT
    CAST(strftime('%H', date_time) AS INTEGER) AS hour_of_day,
    AVG(traffic_volume) AS avg_traffic_volume,
    MAX(traffic_volume) AS peak_traffic_volume
FROM traffic
GROUP BY CAST(strftime('%H', date_time) AS INTEGER)
ORDER BY avg_traffic_volume DESC;

-- 3. Daily traffic trend
SELECT
    date(date_time) AS traffic_date,
    AVG(traffic_volume) AS avg_daily_traffic,
    MAX(traffic_volume) AS max_daily_traffic,
    MIN(traffic_volume) AS min_daily_traffic
FROM traffic
GROUP BY date(date_time)
ORDER BY traffic_date;

-- 4. Impact of weather conditions
SELECT
    weather_main,
    COUNT(*) AS observation_count,
    AVG(traffic_volume) AS avg_traffic,
    MIN(traffic_volume) AS min_traffic,
    MAX(traffic_volume) AS max_traffic
FROM traffic
GROUP BY weather_main
ORDER BY avg_traffic DESC;

-- 5. Holiday influence
SELECT
    holiday,
    AVG(traffic_volume) AS avg_traffic,
    COUNT(*) AS count_records
FROM traffic
GROUP BY holiday
ORDER BY avg_traffic DESC;

-- 6. Rain and snow impact on traffic
SELECT
    CASE
        WHEN rain_1h > 0 THEN 'Rain'
        WHEN snow_1h > 0 THEN 'Snow'
        ELSE 'No precipitation'
    END AS precipitation_status,
    AVG(traffic_volume) AS avg_traffic_volume,
    COUNT(*) AS records
FROM traffic
GROUP BY CASE
    WHEN rain_1h > 0 THEN 'Rain'
    WHEN snow_1h > 0 THEN 'Snow'
    ELSE 'No precipitation'
END
ORDER BY avg_traffic_volume DESC;

-- 7. Congestion threshold checks
-- Match the Part 1 probability definition: congestion is strictly above 5,500.
SELECT
    COUNT(*) AS high_traffic_hours
FROM traffic
WHERE traffic_volume > 5500;

-- 8. Weekly traffic pattern
WITH daily AS (
    SELECT
        CAST(strftime('%w', date_time) AS INTEGER) AS weekday_num,
        traffic_volume
    FROM traffic
)
SELECT
    CASE weekday_num
        WHEN 0 THEN 'Sunday'
        WHEN 1 THEN 'Monday'
        WHEN 2 THEN 'Tuesday'
        WHEN 3 THEN 'Wednesday'
        WHEN 4 THEN 'Thursday'
        WHEN 5 THEN 'Friday'
        WHEN 6 THEN 'Saturday'
    END AS day_name,
    AVG(traffic_volume) AS avg_traffic,
    MAX(traffic_volume) AS max_traffic
FROM daily
GROUP BY weekday_num
ORDER BY CASE weekday_num WHEN 1 THEN 1 WHEN 2 THEN 2 WHEN 3 THEN 3
                          WHEN 4 THEN 4 WHEN 5 THEN 5 WHEN 6 THEN 6 ELSE 7 END;

-- 9. Commute-hour heatmap candidate query
WITH hourly AS (
    SELECT
        CAST(strftime('%H', date_time) AS INTEGER) AS hour_of_day,
        CASE
            WHEN CAST(strftime('%w', date_time) AS INTEGER) BETWEEN 1 AND 5
                THEN 'Weekday'
            ELSE 'Weekend'
        END AS traffic_day_type,
        traffic_volume
    FROM traffic
)
SELECT hour_of_day, traffic_day_type, AVG(traffic_volume) AS avg_volume
FROM hourly
GROUP BY hour_of_day, traffic_day_type
ORDER BY hour_of_day, traffic_day_type;
