-- SQLite database setup for Smart City Traffic Analytics
-- This file is intended to support a local SQLite database for Part 1 analysis.

-- Create table
CREATE TABLE IF NOT EXISTS traffic_volume (
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

-- Example import commands for SQLite CLI
-- .mode csv
-- .import --skip 1 'D:/PhotonUser/Shameer/Capstone 2/Metro_Interstate_Traffic_Volume.csv' traffic_volume

-- Example analysis queries
SELECT COUNT(*) AS total_records,
       MIN(traffic_volume) AS min_traffic,
       MAX(traffic_volume) AS max_traffic,
       AVG(traffic_volume) AS avg_traffic,
       ROUND((SELECT AVG(traffic_volume) FROM traffic_volume), 2) AS avg_traffic_2
FROM traffic_volume;

SELECT CAST(strftime('%H', date_time) AS INTEGER) AS hour_of_day,
       AVG(traffic_volume) AS avg_traffic
FROM traffic_volume
GROUP BY CAST(strftime('%H', date_time) AS INTEGER)
ORDER BY avg_traffic DESC;

SELECT weather_main,
       AVG(traffic_volume) AS avg_traffic,
       COUNT(*) AS records
FROM traffic_volume
GROUP BY weather_main
ORDER BY avg_traffic DESC;

SELECT holiday,
       AVG(traffic_volume) AS avg_traffic
FROM traffic_volume
GROUP BY holiday;

SELECT CASE
           WHEN rain_1h > 0 THEN 'Rain'
           WHEN snow_1h > 0 THEN 'Snow'
           ELSE 'No precipitation'
       END AS precipitation_type,
       AVG(traffic_volume) AS avg_traffic
FROM traffic_volume
GROUP BY CASE
           WHEN rain_1h > 0 THEN 'Rain'
           WHEN snow_1h > 0 THEN 'Snow'
           ELSE 'No precipitation'
       END;
