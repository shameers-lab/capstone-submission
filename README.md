# Smart City Traffic Intelligence Capstone

**From Data Analytics to AI-Powered Mobility**

This capstone applies SQL, statistical analysis, a reproducible Python workflow,
and machine-learning techniques to the Metro Interstate Traffic Volume data.
The analysis focuses on historical traffic and weather observations for the
Minneapolis–St Paul I-94 corridor. Its recommendations concern travel timing on
this corridor, not route selection.

## Project at a glance

| Part | Focus | Main deliverables |
|---|---|---|
| [Part 1 — Data analytics](./part1_data_analytics/README.md) | SQLite/SQL, statistics, probability, and Power BI preparation | SQLite database, SQL queries, statistical outputs, Power BI project and source files, report |
| [Part 2 — Python analytics](./part2_python/README.md) | Data validation and cleaning, feature engineering, visualizations, and CLI queries | Pipeline, cleaned and feature CSVs, figures, CLI, tests, methodology/findings report |
| [Part 3 — Machine learning and AI](./part3_machine_learning/README.md) | Traffic and proxy-label modeling, patterns, explainability, recommendations, deployment, and monitoring | Model artifacts, metrics, recommendation outputs, FastAPI mock, drift report, responsible-AI report |

The integrated report is available at
[final_capstone_report.pdf](./final_capstone_report.pdf).

## Repository map

```text
part1_data_analytics/
├── sql/                 # SQLite database and reusable queries
├── powerbi/             # Power BI project, prepared data, and build notes
├── statistics/          # Analysis scripts, tables, JSON results, and figures
├── insights_report.pdf  # Required two-page Part 1 report
└── insight_report.md    # Readable text companion

part2_python/
├── pipeline.py
├── feature_engineering.py
├── visualizations.py
├── cli_app/
├── data/processed/      # Cleaned and feature-engineered CSVs
├── figures/
├── tests/
├── pipeline.log
└── methodology_findings_report.md

part3_machine_learning/
├── notebooks/
├── models/
├── mlflow/
├── deployment/
├── recommendation_system/
├── monitoring/
└── responsible_ai_report.pdf

final_capstone_report.pdf
```

## Data source and availability

The source is the Metro Interstate Traffic Volume dataset attributed to the
[UCI Machine Learning Repository](https://archive.ics.uci.edu/dataset/492/metro+interstate+traffic+volume).
It was accessed for this project on 2026-11-21. The unchanged raw CSV is **not
included** in this repository. Before running the raw-data workflows, obtain the
source data and place `Metro_Interstate_Traffic_Volume.csv` at the repository
root. Check the source's current license and attribution terms before
redistributing it.

The expected source schema has nine columns: `holiday`, `temp`, `rain_1h`,
`snow_1h`, `clouds_all`, `weather_main`, `weather_description`, `date_time`,
and `traffic_volume`. The Part 1 SQLite database retains all 48,204 source rows,
including 17 exact duplicates. The prepared Power BI CSV also contains 48,204
rows; the dashboard query removes those duplicates, leaving 48,187 observations
for its final model. The verified Part 2 pipeline run used the unchanged raw
CSV, removed the same 17 exact duplicates, and produced 48,187 cleaned rows
and 27 engineered columns. Both processed Part 2 CSVs are outputs of that
pipeline run.

The raw source's literal `None` holiday value means no holiday, not missing
data. Part 2 preserves this category, and the Power BI query standardizes blank
holiday entries to `None`. The Part 2 pipeline also flagged and median-imputed
the physically implausible 9,831.3 mm/hour rainfall value while retaining its
observation. The raw CSV is not committed, so reproduce these outputs by
placing the source file at the repository root and running the documented
workflows. See the [Part 2 data notes](./part2_python/README.md) for details.

## Quick start

Use Python 3.12 (Python 3.10+ for the Part 3 workflow). From the repository
root, create an environment and install the dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install pandas numpy matplotlib
python -m pip install -r part3_machine_learning/requirements.txt
```

Place the raw CSV at the repository root before running Part 1 or Part 2.

### Part 1: analytics

```powershell
python .\part1_data_analytics\statistics\analyze_part1.py --input ".\Metro_Interstate_Traffic_Volume.csv"
```

Open [Traffic_Data_Analysis.pbix](./part1_data_analytics/powerbi/Traffic_Data_Analysis.pbix)
in Power BI Desktop. Prepared data, Power Query, and dashboard build notes are included
in `part1_data_analytics/powerbi/`.

### Part 2: pipeline, tests, and CLI

```powershell
python .\part2_python\pipeline.py
python -m unittest discover -s part2_python/tests -v
python .\part2_python\cli_app\traffic_cli.py day-type
python .\part2_python\cli_app\traffic_cli.py high-traffic --threshold 5000
```

The pipeline writes cleaned data and engineered features to
`part2_python/data/processed/` and figures to `part2_python/figures/`.

### Part 3: models, reports, and monitoring

```powershell
python -m part3_machine_learning.train_models
python -m part3_machine_learning.recommendation_system.recommend
python -m part3_machine_learning.monitoring.drift_check
python -m part3_machine_learning.generate_reports
python -m unittest discover -s part3_machine_learning/tests -p "test_*.py"
```

Run the mock prediction service with:

```powershell
python -m uvicorn part3_machine_learning.deployment.app:app --host 127.0.0.1 --port 8000
```

The API documentation is then available at `http://127.0.0.1:8000/docs`.
Part 3 training and report commands consume the checked-in
`part2_python/data/processed/traffic_features.csv` by default.

## Interpretation and limitations

- The dataset is historical and represents one corridor; results are
  descriptive and do not establish causal effects or generalize automatically
  to other roads.
- No accident records were provided. Part 3's classification target is a
  **constructed congestion/weather proxy**, not an observed accident label or
  real accident likelihood. Its predictions must not be used for real-world
  safety decisions.
- Weather and congestion features overlap with the proxy-label definition,
  creating a residual validity and leakage risk. Part 3 documents this risk and
  includes a feature-ablation analysis.
- The raw CSV is not included; obtain it and place it at the repository root to
  regenerate Part 1 and Part 2. The checked-in Part 2 CSVs are from a verified
  full-data pipeline run. The committed `pipeline.log` is a synthetic smoke-run
  sample, not the log from that full-data run.
- No accident records were provided; the Part 3 proxy warnings and limits are
  detailed in its README and reports.

For detailed definitions, methodology, outputs, and additional limitations,
see the README in each part folder.
