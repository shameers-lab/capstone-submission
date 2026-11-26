# Traffic Statistics Summary

## Dataset and conventions

The Part 1 source table contains 48,204 hourly observations, including 17 exact
duplicate rows, from 2012-10-02 through 2018-09-30. The requested annual
comparison covers 2012-2017; both 2012 and 2018 are partial calendar years.
Traffic is vehicles per hour and temperature is Kelvin. The Part 1 analysis
retains the source rows and flags implausible sensor values rather than silently
altering them. Standard deviation and variance use the sample convention
(`ddof=1`).

## Descriptive statistics

- Mean traffic volume: 3,259.82 vehicles/hour
- Median traffic volume: 3,380 vehicles/hour
- Sample standard deviation: 1,986.86 vehicles/hour
- Sample variance: 3,947,615.32 (vehicles/hour)^2
- Range: 0-7,280 vehicles/hour (width 7,280)
- Pearson temperature/traffic correlation: 0.1303; excluding the 10 zero-K
  readings as a sensitivity check, 0.1323

The correlation is weakly positive and descriptive; it does not imply that
temperature causes traffic changes. Time of day, day type, season, weather, and
other unmeasured conditions may affect the observed relationship.

## Annual totals and year-on-year change

Totals are sums of the observed hourly traffic readings. The number of records
varies substantially by year, so total changes are not like-for-like annual
demand comparisons.

| Year | Records | Total readings | Mean traffic/hour | YoY total change | YoY change |
|---|---:|---:|---:|---:|---:|
| 2012 | 2,559 | 8,208,767 | 3,207.80 | - | - |
| 2013 | 8,573 | 28,177,412 | 3,286.76 | +19,968,645 | +243.26% |
| 2014 | 4,839 | 15,731,289 | 3,250.94 | -12,446,123 | -44.17% |
| 2015 | 4,373 | 14,181,206 | 3,242.90 | -1,550,083 | -9.85% |
| 2016 | 9,306 | 29,494,821 | 3,169.44 | +15,313,615 | +107.99% |
| 2017 | 10,605 | 35,428,156 | 3,340.70 | +5,933,335 | +20.12% |

Two clear patterns are the observed-record total rebound in 2016 and the
continued increase in 2017, and the large shifts in annual record counts.
Because coverage changes with those totals, the yearly mean hourly readings
(3,169-3,341 vehicles/hour) are more suitable for cautious comparison.

## Probability and congestion

The required definitions are congestion = `traffic_volume > 5500`, clear
weather = `weather_main = 'Clear'`, and high temperature = `temp > 292 K`.
For the odds ratio only, cloudy means the distinct `weather_main = 'Clouds'`
category; other weather categories are outside that two-category comparison.

- P(Congestion): 0.1473
- P(Clear): 0.2778
- P(Clear and Congestion): 0.0366
- P(Clear | Congestion): 0.2483
- P(High Temperature | Congestion): 0.2630
- P(Clear) x P(Congestion): 0.04092
- Joint probability minus product: -0.00434
- Clear-versus-Clouds congestion odds ratio: 0.7354

The joint probability is below the product of the marginal probabilities, so
the two events are not independent in this sample; the difference is small.
The odds ratio below one means sample congestion odds are lower for Clear than
for Clouds observations. All four odds-table cells are nonzero, so no
zero-count correction was required. Neither result is a causal weather effect.

## Holiday temperatures and dashboard signals

The calendar dates below were selected directly from timestamps, rather than
relying on a non-null holiday-name flag. Values are means across the available
hourly observations on each date; `n` is the number of records.

| Holiday | Date | n | Mean temperature |
|---|---|---:|---:|
| New Year's Day | 2015-01-01 | 0 | No observations |
| New Year's Day | 2016-01-01 | 19 | 267.03 K (-6.12 C) |
| New Year's Day | 2017-01-01 | 24 | 270.09 K (-3.06 C) |
| Labor Day | 2015-09-07 | 24 | 295.32 K (22.17 C) |
| Labor Day | 2016-09-05 | 40 | 294.75 K (21.60 C) |
| Labor Day | 2017-09-04 | 28 | 290.63 K (17.48 C) |

The small date-level samples, including no New Year's Day 2015 observations,
do not establish typical holiday conditions or a temperature effect on traffic.
In 2017, mean hourly traffic was 3,340.70 vehicles/hour; the hourly profile
peaked at 16:00 (5,797.54) and was lowest at 03:00 (381.71).

Weather averages ranged from 2,061.75 vehicles/hour for Squall (n=4) to
3,618.45 for Clouds (n=15,164), a difference of 1,556.70. The Squall minimum
is based on very few records. The top traffic quartile begins at 4,933
vehicles/hour; among valid temperatures it spans -26.76 to 36.14 C (median
11.23 C), showing high traffic across a broad temperature range.

## Mobility interpretation and limitations

The historical hour-of-day and day-type patterns are useful for choosing
periods to investigate with the dashboard. Weather categories and the weak
temperature correlation provide context, not evidence that weather caused
traffic changes. This is a single-corridor dataset with uneven time coverage;
annual sums, sparse holiday dates, and small weather groups require caution.
The Part 1 outputs preserve 10 zero-K temperatures and one 9,831.3 mm rainfall
reading for transparent source-data analysis; they are flagged as implausible
measurements, not treated as valid sensor values.
