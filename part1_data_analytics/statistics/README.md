# Part 1 statistical outputs

`analyze_part1.py` validates the nine-column source CSV and reproducibly generates the statistics, probability analysis, annual/daily/hourly/weather/holiday tables, figures, SQLite database, dashboard-ready CSV, and `insights_report.pdf`.

Run from the repository root after placing the unchanged Metro Interstate Traffic Volume CSV at that root. The script uses ReportLab to generate the required two-page PDF:

```powershell
python -m pip install pandas numpy matplotlib reportlab
python .\part1_data_analytics\statistics\analyze_part1.py --input ".\Metro_Interstate_Traffic_Volume.csv"
```

The checked-in output files were generated from the 48,204-row source. The raw CSV is not included in this checkout, so a fresh raw-data run requires obtaining it from the attributed source. The holiday comparison selects calendar dates from timestamps, reports the number of hourly observations, and explicitly represents dates with no observations. Descriptive standard deviation and variance use the sample convention (`ddof=1`). The probability task defines congestion as `traffic_volume > 5500`, clear as `weather_main = Clear`, high temperature as `temp > 292 K`, and the odds-ratio comparison as Clear versus the distinct Clouds category. See the report and SQL files for the exact definitions and interpretation cautions.

The source contains 17 exact duplicate rows, missing holiday values, zero-K temperatures, and one 9,831.3 mm rainfall observation. The Part 1 analysis retains source rows and flags implausible measurements; it does not remove valid traffic extremes. Part 2 separately applies documented physical checks and imputes the flagged rainfall value.

Run the focused Part 1 holiday-date test from the repository root with:

```powershell
python -m unittest discover -s .\part1_data_analytics\statistics\tests -v
```
