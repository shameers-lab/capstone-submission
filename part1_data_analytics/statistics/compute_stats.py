import csv
import math
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parents[3] / 'Metro_Interstate_Traffic_Volume.csv'


def load_rows(path: Path):
    rows = []
    with path.open(newline='') as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            row['temp'] = float(row['temp'])
            row['rain_1h'] = float(row['rain_1h'])
            row['snow_1h'] = float(row['snow_1h'])
            row['clouds_all'] = int(row['clouds_all'])
            row['traffic_volume'] = int(row['traffic_volume'])
            row['dt'] = datetime.strptime(row['date_time'], '%Y-%m-%d %H:%M:%S')
            rows.append(row)
    return rows


def safe_mean(values):
    return statistics.fmean(values) if values else None


rows = load_rows(DATA_PATH)
volumes = [row['traffic_volume'] for row in rows]
mean_traffic = safe_mean(volumes)
median_traffic = statistics.median(volumes)
std_sample = statistics.stdev(volumes) if len(volumes) > 1 else 0.0
variance_sample = statistics.variance(volumes) if len(volumes) > 1 else 0.0
min_traffic = min(volumes)
max_traffic = max(volumes)

# temperature vs traffic correlation
x_values = [row['temp'] for row in rows]
y_values = volumes
x_mean = safe_mean(x_values)
y_mean = safe_mean(y_values)
num = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
den_x = sum((x - x_mean) ** 2 for x in x_values)
den_y = sum((y - y_mean) ** 2 for y in y_values)
correlation = num / math.sqrt(den_x * den_y)

# year totals (2012-2017)
year_totals = defaultdict(int)
for row in rows:
    year_totals[row['dt'].year] += row['traffic_volume']

# hourly averages
hourly_traffic = defaultdict(list)
for row in rows:
    hourly_traffic[row['dt'].hour].append(row['traffic_volume'])

# weather averages
weather_traffic = defaultdict(list)
for row in rows:
    weather_traffic[row['weather_main']].append(row['traffic_volume'])

# holiday / weekday vs weekend
holiday_traffic = defaultdict(list)
for row in rows:
    holiday_traffic[row['holiday']].append(row['traffic_volume'])

# exact definitions used for the probability task from Part 1 instructions
congestion_threshold = 5500
high_temp_threshold_k = 292
clear_weather_values = {'Clear'}
cloud_weather_values = {'Clouds'}

congestion_count = sum(1 for row in rows if row['traffic_volume'] > congestion_threshold)
clear_weather_count = sum(1 for row in rows if row['weather_main'] in clear_weather_values)
joint_clear_congestion = sum(
    1 for row in rows if row['weather_main'] in clear_weather_values and row['traffic_volume'] > congestion_threshold
)

p_congestion = congestion_count / len(rows)
p_clear = clear_weather_count / len(rows)
p_congestion_and_clear = joint_clear_congestion / len(rows)
p_clear_given_congestion = joint_clear_congestion / congestion_count if congestion_count else 0.0
p_high_temp_given_congestion = sum(
    1 for row in rows if row['traffic_volume'] > congestion_threshold and row['temp'] > high_temp_threshold_k
) / congestion_count if congestion_count else 0.0

independence_difference = p_congestion_and_clear - (p_congestion * p_clear)

clear_and_congestion = sum(
    1 for row in rows if row['weather_main'] in clear_weather_values and row['traffic_volume'] > congestion_threshold
)
clear_and_not_congestion = sum(
    1 for row in rows if row['weather_main'] in clear_weather_values and row['traffic_volume'] <= congestion_threshold
)
cloudy_and_congestion = sum(
    1 for row in rows if row['weather_main'] in cloud_weather_values and row['traffic_volume'] > congestion_threshold
)
cloudy_and_not_congestion = sum(
    1 for row in rows if row['weather_main'] in cloud_weather_values and row['traffic_volume'] <= congestion_threshold
)

if clear_and_not_congestion and cloudy_and_congestion:
    odds_ratio = (clear_and_congestion * cloudy_and_not_congestion) / (clear_and_not_congestion * cloudy_and_congestion)
else:
    odds_ratio = None

# holiday temp comparisons for New Year's Day and Labor Day in 2015-2017
nyd_temps = {}
for year in [2015, 2016, 2017]:
    day_rows = [row['temp'] for row in rows if row['dt'].year == year and row['dt'].month == 1 and row['dt'].day == 1]
    nyd_temps[year] = safe_mean(day_rows)

laborday_temps = {}
for year in [2015, 2016, 2017]:
    day_rows = [
        row['temp']
        for row in rows
        if row['dt'].year == year
        and row['dt'].month == 9
        and row['dt'].weekday() == 0
        and 1 <= row['dt'].day <= 7
    ]
    laborday_temps[year] = safe_mean(day_rows)

print('rows=' + str(len(rows)))
print('mean_traffic=' + str(round(mean_traffic, 2)))
print('median_traffic=' + str(median_traffic))
print('std_sample=' + str(round(std_sample, 2)))
print('variance_sample=' + str(round(variance_sample, 2)))
print('min_traffic=' + str(min_traffic))
print('max_traffic=' + str(max_traffic))
print('corr_temp_traffic=' + str(round(correlation, 4)))
print('year_totals=' + str(dict(sorted(year_totals.items()))))
print('top_hourly_average_traffic=' + str(sorted(
    ((hour, safe_mean(values)) for hour, values in hourly_traffic.items()),
    key=lambda item: item[1],
    reverse=True,
)[:5]))
print('weather_average_traffic=' + str(sorted(
    ((weather, round(safe_mean(values), 2)) for weather, values in weather_traffic.items()),
    key=lambda item: item[1],
    reverse=True,
)))
print('holiday_average_traffic=' + str({key: round(safe_mean(values), 2) for key, values in holiday_traffic.items()}))
print('P(Congestion)=' + str(p_congestion))
print('P(Clear Weather)=' + str(p_clear))
print('P(Congestion and Clear Weather)=' + str(p_congestion_and_clear))
print('P(Clear Weather | Congestion)=' + str(p_clear_given_congestion))
print('P(High Temperature | Congestion)=' + str(p_high_temp_given_congestion))
print('independence_difference=' + str(independence_difference))
print('odds_ratio_clear_vs_cloudy=' + str(odds_ratio))
print('NYD_average_temp_2015_2017=' + str(nyd_temps))
print('Labor_Day_average_temp_2015_2017=' + str(laborday_temps))
