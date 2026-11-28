# Part 1 — Data Analytics

Part 1 contains the Metro Interstate Traffic Volume data analysis, reproducible SQL/statistics artifacts, Power BI files, figures, and the decision-focused report.

## Deliverables

- `insights_report.pdf` — required, two-page decision-focused report; `insight_report.md` is an additional text version.
- `sql/traffic_analysis.db` — SQLite database with 48,204 source records and the prepared analysis columns.
- `sql/traffic_analysis.sql`, `sql/traffic_analytics.sql`, and `sql/sqlite_database_setup.sql` — SQLite validation, import, and analysis queries using the common `traffic` table.
- `statistics/analyze_part1.py` — reproducible analysis script.
- `statistics/` — annual, daily, hourly, holiday, weather, probability, and descriptive-statistics outputs and figures.
- `powerbi/Traffic_Data_Analysis.pbix` — native Power BI project file.
- `powerbi/traffic_dashboard_data.csv` and `powerbi/Traffic_Power_Query.m` — prepared input and Power Query source.
- `powerbi/dashboard_spec.md` and `powerbi/powerbi_build_steps.md` — visual definitions and build guidance.

## Data provenance and availability

The source is the Metro Interstate Traffic Volume dataset, attributed to the UCI Machine Learning Repository. The raw CSV is not included in this checkout; the SQLite database and prepared Power BI CSV are present. The database was verified to contain 48,204 rows in the expected source schema plus five derived fields. The dataset spans 2012-10-02 through 2018-09-30; 2018 is partial. Verify UCI's license and attribution terms before redistributing source data.

To regenerate the analysis from a locally obtained source CSV, place the unchanged file at the repository root or pass its path explicitly. The script validates the nine expected source columns and writes reports, figures, SQL data, and dashboard data under this folder:

```powershell
python -m pip install pandas numpy matplotlib
python -m pip install pandas numpy matplotlib reportlab
python .\part1_data_analytics\statistics\analyze_part1.py --input ".\Metro_Interstate_Traffic_Volume.csv"
```

The generated analysis preserves the 17 exact duplicate source records and flags implausible values for review rather than silently deleting valid traffic extremes. See `statistics/README.md` for definitions and outputs.

To reproduce the SQLite import without overwriting the checked-in database, open a fresh database from the repository root and run these SQLite CLI commands:

```text
sqlite3 traffic_analysis_repro.db
.read part1_data_analytics/sql/sqlite_database_setup.sql
.mode csv
.import --skip 1 "Metro_Interstate_Traffic_Volume.csv" traffic
.quit
```

The import retains the 48,204 source rows, including exact duplicates. Both analysis query files target the resulting `traffic` table and use SQLite date/time functions.

## Power BI

Open `powerbi/Traffic_Data_Analysis.pbix` in Power BI Desktop. The prepared CSV and Power Query source are included alongside the dashboard build guide.
