import csv
import math
import sqlite3
import statistics
from collections import defaultdict
from datetime import datetime

csv_path = r'd:\PhotonUser\Shameer\Capstone 2\Metro_Interstate_Traffic_Volume.csv'
sqlite_path = r'd:\PhotonUser\Shameer\Capstone 2\smart-city-traffic-capstone\part1_data_analytics\sql\traffic_part1.db'

rows = []
with open(csv_path, newline='') as f:
    reader = csv.DictReader(f)
    for r in reader:
        rows.append({
            'holiday': r['holiday'],
            'temp': float(r['temp']),
            'rain_1h': float(r['rain_1h']),
            'snow_1h': float(r['snow_1h']),
            'clouds_all': int(r['clouds_all']),
            'weather_main': r['weather_main'],
            'weather_description': r['weather_description'],
            'date_time': r['date_time'],
            'traffic_volume': int(r['traffic_volume'])
        })

print('TOTAL_ROWS', len(rows))
print('COLUMNS', list(rows[0].keys()))

# year totals
year_totals = defaultdict(int)
for r in rows:
    year = r['date_time'][:4]
    year_totals[year] += r['traffic_volume']
print('YEAR_TOTALS')
for year in sorted(year_totals):
    print(year, year_totals[year])

# Year-over-year change
years = sorted(year_totals)
print('YEAR_OVER_YEAR_PERCENT_CHANGE')
for i in range(1, len(years)):
    prev = year_totals[years[i-1]]
    curr = year_totals[years[i]]
    pct = ((curr - prev) / prev) * 100
    print(years[i-1], '->', years[i], round(pct, 2), '%')

# compare actual dates for NYD and Labor Day by year
print('NYD_AND_LABOR_DAY_TEMPERATURES')
for year in ['2015', '2016', '2017']:
    nyd = [r['temp'] for r in rows if r['date_time'].startswith(f'{year}-01-01')]
    labor_day = []
    for r in rows:
        d = datetime.strptime(r['date_time'], '%Y-%m-%d %H:%M:%S')
        if d.year == int(year):
            month = d.month
            day = d.day
            if month == 9 and d.weekday() == 0:
                # first Monday in September, same as Labor Day in US
                first_weekday = min(day for day in range(1, 8) if datetime(year, 9, day).weekday() == 0)
                if day == first_weekday:
                    labor_day.append(r['temp'])
    if nyd:
        print(year, 'NYD avg temp', round(statistics.fmean(nyd), 2), 'count', len(nyd))
    if labor_day:
        print(year, 'LaborDay avg temp', round(statistics.fmean(labor_day), 2), 'count', len(labor_day))

# summary stats
traffic_values = [r['traffic_volume'] for r in rows]
mean_traffic = statistics.fmean(traffic_values)
median_traffic = statistics.median(traffic_values)
std_traffic = statistics.pstdev(traffic_values)
var_traffic = statistics.pvariance(traffic_values)
min_traffic = min(traffic_values)
max_traffic = max(traffic_values)
range_traffic = max_traffic - min_traffic
print('TRAFFIC_SUMMARY')
print('mean', mean_traffic)
print('median', median_traffic)
print('stddev_population', std_traffic)
print('variance_population', var_traffic)
print('min', min_traffic)
print('max', max_traffic)
print('range', range_traffic)

# correlation temp and traffic
x = [r['temp'] for r in rows]
y = [r['traffic_volume'] for r in rows]
mx = statistics.fmean(x)
my = statistics.fmean(y)
num = sum((a - mx) * (b - my) for a, b in zip(x, y))
denx = sum((a - mx) ** 2 for a in x)
deny = sum((b - my) ** 2 for b in y)
pearson = num / math.sqrt(denx * deny)
print('TEMP_TRAFFIC_CORRELATION', pearson)

# probability stats
congestion = [r for r in rows if r['traffic_volume'] > 5500]
clear = [r for r in rows if r['weather_main'] == 'Clear']
clear_and_cong = [r for r in rows if r['weather_main'] == 'Clear' and r['traffic_volume'] > 5500]
high_temp_and_cong = [r for r in rows if r['traffic_volume'] > 5500 and r['temp'] > 292]

total = len(rows)
P_cong = len(congestion) / total
P_clear = len(clear) / total
P_clear_and_cong = len(clear_and_cong) / total
P_clear_given_cong = len(clear_and_cong) / len(congestion)
P_high_temp_given_cong = len(high_temp_and_cong) / len(congestion)
print('PROBABILITY')
print('P(Congestion)', P_cong)
print('P(Clear Weather)', P_clear)
print('P(Clear & Congestion)', P_clear_and_cong)
print('P(Clear | Congestion)', P_clear_given_cong)
print('P(High Temp >292K | Congestion)', P_high_temp_given_cong)
print('INDEPENDENCE_CHECK')
print('P(Clear)*P(Congestion)', P_clear * P_cong)
print('Joint - Product', P_clear_and_cong - (P_clear * P_cong))

# odds ratio clear vs cloudy
clear_total = len(clear)
cloudy = [r for r in rows if r['weather_main'] == 'Clouds']
cloudy_total = len(cloudy)
clear_cong_count = len(clear_and_cong)
cloudy_cong_count = len([r for r in cloudy if r['traffic_volume'] > 5500])
clear_not_cong = clear_total - clear_cong_count
cloudy_not_cong = cloudy_total - cloudy_cong_count
odds_clear = (clear_cong_count / clear_not_cong) / (cloudy_cong_count / cloudy_not_cong)
print('ODDS_RATIO_CLEAR_VS_CLOUDS', odds_clear)
print('CLEAR_GROUPING', 'weather_main == "Clear"')
print('CLOUDY_GROUPING', 'weather_main == "Clouds"')
print('COUNTS', {'clear_total': clear_total, 'clear_cong': clear_cong_count, 'cloudy_total': cloudy_total, 'cloudy_cong': cloudy_cong_count})

# power query prep stats
null_counts = {}
for key in rows[0].keys():
    null_counts[key] = sum(1 for r in rows if r[key] in ('', None))
print('NULL_COUNTS', null_counts)

# SQLite database creation
conn = sqlite3.connect(sqlite_path)
cur = conn.cursor()
cur.execute('DROP TABLE IF EXISTS traffic')
cur.execute('CREATE TABLE traffic (holiday TEXT, temp REAL, rain_1h REAL, snow_1h REAL, clouds_all INTEGER, weather_main TEXT, weather_description TEXT, date_time TEXT, traffic_volume INTEGER)')
cur.executemany('INSERT INTO traffic VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', [(
    r['holiday'],
    r['temp'],
    r['rain_1h'],
    r['snow_1h'],
    r['clouds_all'],
    r['weather_main'],
    r['weather_description'],
    r['date_time'],
    r['traffic_volume']) for r in rows])
conn.commit()
print('SQLITE_ROW_COUNT', cur.execute('SELECT COUNT(*) FROM traffic').fetchone()[0])
print('SQLITE_SAMPLE', cur.execute('SELECT holiday, temp, weather_main, date_time, traffic_volume FROM traffic ORDER BY date_time LIMIT 3').fetchall())
conn.close()
