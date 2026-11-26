-- Smart City Traffic Capstone
-- Part 1: Data Analytics
-- Dataset: Metro_Interstate_Traffic_Volume.csv

-- 1. Basic inspection
SELECT
    COUNT(*) AS total_rows,
    MIN(temp) AS min_temp,
    MAX(temp) AS max_temp,
    AVG(temp) AS avg_temp,
    MIN(traffic_volume) AS min_traffic,
    MAX(traffic_volume) AS max_traffic,
    AVG(traffic_volume) AS avg_traffic
FROM traffic_volume_data;

-- 2. Peak traffic hours by time-of-day
SELECT
    EXTRACT(HOUR FROM date_time) AS hour_of_day,
    AVG(traffic_volume) AS avg_traffic_volume,
    MAX(traffic_volume) AS peak_traffic_volume
FROM traffic_volume_data
GROUP BY EXTRACT(HOUR FROM date_time)
ORDER BY avg_traffic_volume DESC;

-- 3. Daily traffic trend
SELECT
    CAST(date_time AS DATE) AS traffic_date,
    AVG(traffic_volume) AS avg_daily_traffic,
    MAX(traffic_volume) AS max_daily_traffic,
    MIN(traffic_volume) AS min_daily_traffic
FROM traffic_volume_data
GROUP BY CAST(date_time AS DATE)
ORDER BY traffic_date;

-- 4. Impact of weather conditions
SELECT
    weather_main,
    COUNT(*) AS observation_count,
    AVG(traffic_volume) AS avg_traffic,
    MIN(traffic_volume) AS min_traffic,
    MAX(traffic_volume) AS max_traffic
FROM traffic_volume_data
GROUP BY weather_main
ORDER BY avg_traffic DESC;

-- 5. Holiday influence
SELECT
    holiday,
    AVG(traffic_volume) AS avg_traffic,
    COUNT(*) AS count_records
FROM traffic_volume_data
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
FROM traffic_volume_data
GROUP BY CASE
    WHEN rain_1h > 0 THEN 'Rain'
    WHEN snow_1h > 0 THEN 'Snow'
    ELSE 'No precipitation'
END
ORDER BY avg_traffic_volume DESC;

-- 7. Congestion threshold checks
SELECT
    COUNT(*) AS high_traffic_hours
FROM traffic_volume_data
WHERE traffic_volume >= 5000;

-- 8. Weekly traffic pattern
SELECT
    TO_CHAR(date_time, 'Day') AS day_name,
    AVG(traffic_volume) AS avg_traffic,
    MAX(traffic_volume) AS max_traffic
FROM traffic_volume_data
GROUP BY TO_CHAR(date_time, 'Day')
ORDER BY CASE
    WHEN TO_CHAR(date_time, 'Day') = 'Monday' THEN 1
    WHEN TO_CHAR(date_time, 'Day') = 'Tuesday' THEN 2
    WHEN TO_CHAR(date_time, 'Day') = 'Wednesday' THEN 3
    WHEN TO_CHAR(date_time, 'Day') = 'Thursday' THEN 4
    WHEN TO_CHAR(date_time, 'Day') = 'Friday' THEN 5
    WHEN TO_CHAR(date_time, 'Day') = 'Saturday' THEN 6
    WHEN TO_CHAR(date_time, 'Day') = 'Sunday' THEN 7
END;

-- 9. Commute-hour heatmap candidate query
SELECT
    EXTRACT(HOUR FROM date_time) AS hour_of_day,
    CASE
        WHEN EXTRACT(ISODOW FROM date_time) IN (1,2,3,4,5) THEN 'Weekday'
        ELSE 'Weekend'
    END AS traffic_day_type,
    AVG(traffic_volume) AS avg_volume
FROM traffic_volume_data
GROUP BY EXTRACT(HOUR FROM date_time),
    CASE
        WHEN EXTRACT(ISODOW FROM date_time) IN (1,2,3,4,5) THEN 'Weekday'
        ELSE 'Weekend'
    END
ORDER BY hour_of_day, traffic_day_type;
