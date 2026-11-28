-- SQLite database setup for Smart City Traffic Analytics
-- Use the same table name as traffic_analysis.db and the Part 1 query files.
-- From the repository root, start a fresh database and enter:
-- .read part1_data_analytics/sql/sqlite_database_setup.sql
-- .mode csv
-- .import --skip 1 "Metro_Interstate_Traffic_Volume.csv" traffic
-- .quit

-- Create table
CREATE TABLE IF NOT EXISTS traffic (
    holiday TEXT,
    temp REAL,
    rain_1h REAL,
    snow_1h REAL,
    clouds_all INTEGER,
    weather_main TEXT,
    weather_description TEXT,
    date_time TEXT,
    traffic_volume INTEGER
);

-- Example analysis queries
SELECT COUNT(*) AS total_records,
       MIN(traffic_volume) AS min_traffic,
       MAX(traffic_volume) AS max_traffic,
       AVG(traffic_volume) AS avg_traffic,
       ROUND((SELECT AVG(traffic_volume) FROM traffic), 2) AS avg_traffic_2
FROM traffic;

SELECT CAST(strftime('%H', date_time) AS INTEGER) AS hour_of_day,
       AVG(traffic_volume) AS avg_traffic
FROM traffic
GROUP BY CAST(strftime('%H', date_time) AS INTEGER)
ORDER BY avg_traffic DESC;

SELECT weather_main,
       AVG(traffic_volume) AS avg_traffic,
       COUNT(*) AS records
FROM traffic
GROUP BY weather_main
ORDER BY avg_traffic DESC;

SELECT holiday,
       AVG(traffic_volume) AS avg_traffic
FROM traffic
GROUP BY holiday;

SELECT CASE
           WHEN rain_1h > 0 THEN 'Rain'
           WHEN snow_1h > 0 THEN 'Snow'
           ELSE 'No precipitation'
       END AS precipitation_type,
       AVG(traffic_volume) AS avg_traffic
FROM traffic
GROUP BY CASE
           WHEN rain_1h > 0 THEN 'Rain'
           WHEN snow_1h > 0 THEN 'Snow'
           ELSE 'No precipitation'
       END;
