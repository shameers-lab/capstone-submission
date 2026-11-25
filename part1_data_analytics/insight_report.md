# Smart City Mobility Analytics - Part 1 Insights

## Executive summary

The Metro Interstate Traffic Volume data describes hourly traffic and weather
on the Minneapolis-St Paul I-94 corridor. Its strongest practical signal is
the variation by hour: in 2017, mean hourly traffic peaked at 16:00
(5,797.54 vehicles/hour) and was lowest at 03:00 (381.71). Weather and
temperature add context, but the measured temperature/traffic correlation is
weak. These historical associations can guide further investigation; they do
not establish causes or guarantee future conditions.

## Evidence

The Part 1 database contains 48,204 source observations from 2012-10-02 through
2018-09-30, including 17 exact duplicates retained for this source-data
analysis. The requested annual totals vary sharply alongside record coverage:

| Year | Records | Total readings | Mean traffic/hour | YoY total change |
|---|---:|---:|---:|---:|
| 2012 | 2,559 | 8,208,767 | 3,207.80 | - |
| 2013 | 8,573 | 28,177,412 | 3,286.76 | +243.26% |
| 2014 | 4,839 | 15,731,289 | 3,250.94 | -44.17% |
| 2015 | 4,373 | 14,181,206 | 3,242.90 | -9.85% |
| 2016 | 9,306 | 29,494,821 | 3,169.44 | +107.99% |
| 2017 | 10,605 | 35,428,156 | 3,340.70 | +20.12% |

Annual totals are sums across the observed hours, not comparable full-year
demand estimates: counts range from 2,559 to 10,605 per year, and both endpoint
years are partial. Mean hourly traffic is more stable, ranging from about
3,169 to 3,341 vehicles/hour across 2012-2017.

Across all source rows, mean and median traffic are 3,259.82 and 3,380
vehicles/hour; sample standard deviation is 1,986.86 and sample variance is
3,947,615.32 (vehicles/hour)^2. The range is 0-7,280 vehicles/hour. Pearson's
temperature/traffic correlation is 0.1303 (0.1323 after excluding the 10
zero-K readings as a sensitivity check), a weak positive association that
does not support a causal or single-factor interpretation.

For the probability task, congestion is traffic volume >5,500, clear is
`weather_main = 'Clear'`, and high temperature is >292 K. P(congestion) is
0.1473; P(clear) is 0.2778; P(clear and congestion) is 0.0366;
P(clear | congestion) is 0.2483; and P(high temperature | congestion) is
0.2630. The joint probability is 0.00434 below the product of marginals
(0.04092), a small departure from independence. For the odds ratio, cloudy is
defined narrowly as `weather_main = 'Clouds'`; clear-versus-clouds congestion
odds ratio is 0.7354. Other weather categories are outside that comparison.
These are sample associations, not causal weather effects.

Temperature on New Year's Day 2016 and 2017 averaged 267.03 K (19 records) and
270.09 K (24). There are no January 1, 2015 records. Labor Day means were
295.32 K (24 records) in 2015, 294.75 K (40) in 2016, and 290.63 K (28) in
2017. Sparse date-level observations do not establish typical holiday
conditions or a traffic response.

Weather averages ranged from 2,061.75 vehicles/hour for Squall (n=4) to
3,618.45 for Clouds (n=15,164), a difference of 1,556.70. Interpret the Squall
value cautiously because its group is very small. The upper traffic quartile
begins at 4,933 vehicles/hour and spans -26.76 to 36.14 C among valid
temperatures, so high traffic occurs across a broad temperature range.

## Mobility implications and limitations

The hour-of-day and day-type views can help analysts identify periods for
follow-up signal-timing or commuter-information assessment. The weather
comparison can motivate closer review of weather-specific operating
conditions, not a causal intervention claim. The 2017 hourly peak and
lower-volume overnight period are historical patterns, not real-time travel
advice. All results describe one corridor, uneven observation coverage, and
limited context; they should not be generalized to the whole city without
additional data.

The source analysis retains and flags 10 zero-K temperature readings and one
9,831.3 mm rainfall observation rather than silently treating them as valid
measurements. The report's definitions, full probability results, and
additional limitations are in [traffic_statistics_summary.md](./statistics/traffic_statistics_summary.md).
