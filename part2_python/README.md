# Part 2 – Python Pipeline and Analytics Application

This folder contains the pipeline, feature engineering, visualizations, CLI, and reporting artifacts for the smart-city mobility capstone.

## Folder structure

- `pipeline.py` – end-to-end validation, cleaning, and feature-processing pipeline
- `feature_engineering.py` – time, weather, scaling, and congestion feature creation
- `visualizations.py` – Matplotlib visual outputs and saved figures
- `cli_app/traffic_cli.py` – user-friendly CLI for traffic queries
- `data/processed/` – distinct cleaned and feature-engineered CSV outputs
- `figures/` – generated visual outputs
- `tests/` – focused data validation, cleaning, and pipeline integration tests
- `pipeline.log` – synthetic pipeline/CLI smoke-run sample showing log levels and error handling
- `methodology_findings_report.md` – Part 2 reviewable methodology and findings summary

## Data provenance

The source is the Metro Interstate Traffic Volume dataset from the UCI Machine Learning Repository, historically distributed through Kaggle and commonly attributed to John Hogue. The raw CSV is not included in this repository; place the unchanged file at `Metro_Interstate_Traffic_Volume.csv` in the repository root before running the pipeline. It was accessed for this project on 2026-11-21. The repository does not contain a separate license file; verify the source terms before redistribution.

The verified full run loaded 48,204 raw rows, removed 17 duplicates, and produced 48,187 cleaned rows and 27 engineered columns. The tracked cleaned CSV is the nine source columns projected from the existing verified feature output. During this review, the tracked input was reprocessed to apply the physical measurement checks below; because the raw CSV is absent, this refresh is not a new raw-to-output run. Rerunning the pipeline with the source CSV regenerates both stages directly. The committed `pipeline.log` is a synthetic smoke-run sample, not a new full-data result; the original full-run counts above come from the earlier verified source-data run.

## Prerequisites

- Python 3.12 is recommended.
- Install `pandas`, `numpy`, and `matplotlib` in the project virtual environment.
- The raw CSV must remain at `Metro_Interstate_Traffic_Volume.csv` in the repository root.

## Environment setup

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install pandas numpy matplotlib
```

## Run the pipeline

From the repository root, run:

```bash
python part2_python/pipeline.py
```

Optional arguments:

```bash
python part2_python/pipeline.py --data "Metro_Interstate_Traffic_Volume.csv" --output-dir "part2_python/figures" --processed-dir "part2_python/data/processed"
```

The pipeline writes the cleaned nine-column dataset to
`part2_python/data/processed/traffic_cleaned.csv` and the feature-engineered
dataset to `part2_python/data/processed/traffic_features.csv`. Figures remain
under `part2_python/figures/`; the input CSV is never overwritten.

## Logging

Each module uses `logging.getLogger(__name__)`. The pipeline executable
configures timestamped DEBUG file logging and INFO console logging; the CLI
appends its messages to the same `pipeline.log`. The format includes timestamp,
level, module, and message. DEBUG records contain intermediate diagnostics;
INFO records mark milestones and output files; WARNING records identify
recoverable changes with affected counts and reasons; fatal pipeline failures
are logged at ERROR with traceback details. Machine-local paths are not written
to the log. The committed log is a synthetic smoke-run sample; running the
pipeline replaces it with the current run log.

## Run the CLI

The CLI derives the repository root from its own location, so an explicit `--data` argument is optional when the CSV is in the repository root:

```bash
python part2_python/cli_app/traffic_cli.py lookup --timestamp "2017-01-01 00:00:00"
python part2_python/cli_app/traffic_cli.py high-traffic --threshold 5000
python part2_python/cli_app/traffic_cli.py day-type
python part2_python/cli_app/traffic_cli.py weather --condition "Clear"
```

A custom input path can be supplied before the subcommand:

```bash
python part2_python/cli_app/traffic_cli.py --data "Metro_Interstate_Traffic_Volume.csv" lookup --timestamp "2017-01-01 00:00:00"
```

## Tests

From the repository root, run the focused Part 2 tests with:

```powershell
python -m unittest discover -s part2_python/tests -v
```

The tests cover required-column validation, duplicate removal and
month-specific imputation, and a synthetic end-to-end pipeline run that checks
the separate cleaned/features CSV outputs and generated figures.

## Expected outputs

- `data/processed/traffic_cleaned.csv`
- `data/processed/traffic_features.csv`
- `figures/hourly_average_traffic.png`
- `figures/weather_average_traffic.png`
- `figures/weekday_weekend_traffic.png`
- `figures/temperature_vs_traffic.png`
- `pipeline.log`
- `methodology_findings_report.md`

### Figure interpretations

- Hourly traffic shows whether commuter windows create identifiable peaks.
- Weather traffic compares average volume across weather categories and is descriptive, not causal.
- Weekday versus weekend traffic shows operational differences between work and leisure travel patterns.
- The temperature scatter plot indicates the strength of a broad temperature relationship, while exposing the limits of temperature as a single predictor.

## Notes

The raw data is not overwritten. Duplicate rows, invalid timestamps, and missing values are handled explicitly and logged. Physical measurement checks set temperatures outside 150-400 K, rain/snow outside 0-500 mm/hour, cloud cover outside 0-100, and negative traffic to missing before the documented imputations. The 9,831.3 mm/hour rainfall value in the prior tracked input exceeded the deliberately broad 500 mm/hour ceiling; it was flagged and median-imputed while its observation was retained. No upper traffic-volume cutoff is applied, so valid traffic extremes are preserved. Scaling is descriptive for this pipeline; any model training must fit scaling and encoding only on training data.
