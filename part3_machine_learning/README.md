# Part 3 — Machine Learning and AI

This folder completes the machine-learning stage for the Metro Interstate traffic corridor. All classification results concern an explicitly constructed congestion/weather **proxy label**, not observed accidents. Predictions are not real accident likelihood and must not drive real-world safety decisions.

## Data input and provenance

The default input is the tracked Part 2 output:

```text
part2_python/data/processed/traffic_features.csv
```

The Part 2 README attributes the data to the UCI Metro Interstate Traffic Volume dataset and records its processing run. That processed file contains 48,187 rows and the expected source columns plus engineered fields. The original raw CSV is not present in the checkout, so Part 3 validates the processed-file schema and records that raw-to-clean processing could not be independently rerun. It does not substitute another dataset. The source schema used here includes holiday, temperature (Kelvin), precipitation, snow, cloud cover (0–100), weather category, timestamp, and traffic volume (vehicles/hour). The source license/redistribution terms are not included in this repository; verify them with UCI before redistributing source data.

Part 3 independently rechecks physical measurement ranges without dropping observations: temperature must be 150–400 K, cloud cover 0–100, and hourly rain/snow 0–500 mm. The 500 mm/hour precipitation ceiling is intentionally broad. The prior tracked feature artifact contained one 9,831.3 mm rain value; Part 2 now flags and imputes it before feature generation while retaining the observation. Any out-of-range values that remain are set missing by Part 3, and supervised imputers are fitted on training data only. The current Part 3 processed input is revalidated against these same bounds.

The Part 2 data layer preserves the source's literal `None` holiday value as the no-holiday category. For compatibility with the already fitted categorical encoders, `add_model_features` maps that source value to `Unknown` at the Part 3 model-input boundary; true missing and blank holiday values also use `Unknown`. This keeps the model's training feature matrix consistent while preserving the source meaning in the shared processed data.

## Proxy target and leakage controls

Congestion thresholds are computed from the chronological training portion only. The Part 3 category definition is `<= Q1 Low`, `<= Q2 Medium`, `<= Q3 High`, and `> Q3 Severe`; the proxy-positive label is traffic volume above training Q2 (the High/Severe bands) **and** either:

- `weather_main` is one of Drizzle, Dust, Fog, Haze, Mist, Rain, Sand, Smoke, Snow, Squall, Thunderstorm, or Tornado; or
- `clouds_all >= 80` on the source 0–100 scale (the chosen low-visibility proxy).

There are no accident observations in this dataset. Current traffic volume, the congestion category, and the proxy target are never supervised predictor inputs. Weather and visibility are nevertheless ingredients in the label, and weather/time correlate with its congestion ingredient; this residual definitional leakage is a major validity risk. The time/holiday-only ablation is a sensitivity analysis, not a way to turn this proxy into an accident target.

## Environment and commands

Use Python 3.10+ (3.12 recommended) from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r part3_machine_learning/requirements.txt
python -m part3_machine_learning.train_models
python -m part3_machine_learning.recommendation_system.recommend
python -m part3_machine_learning.monitoring.drift_check
python -m part3_machine_learning.generate_reports
python -m unittest discover -s part3_machine_learning/tests -p "test_*.py"
```

Optional custom processed CSV:

```powershell
python -m part3_machine_learning.train_models --data "path\to\traffic_features.csv"
```

Training sorts observations chronologically and uses the first 80% for training and the last 20% for the holdout. Scalers and one-hot encoders are fit inside model pipelines on training rows only. Classification threshold is 0.5. Run results, parameters, metrics, model files, a local MLflow tracking store, group-level error summaries, cluster profiles, rules, a LIME explanation, and model metadata are written below this folder. Model/report metrics are generated from the input; no values are hard-coded as findings.

## Folder map

- `train_models.py`, `feature_utils.py` — target construction, classification, regression, clustering, rule mining, LIME, and MLflow.
- `notebooks/` — reproducible notebook entry point for the scripts.
- `models/` — fitted joblib artifacts and generated metrics, model card, cluster/rule results, and explanation.
- `mlflow/` — MLflow README and portable run/version summary; training creates an ignored local SQLite store and artifact files.
- `deployment/` — FastAPI mock prediction service.
- `recommendation_system/` — single-corridor historical timing-window summary.
- `monitoring/` — chronological feature-distribution drift simulation.
- `responsible_ai_report.pdf` — separate bias/fairness and governance report.
- `pipeline.log` — timestamped training log.

The repository root contains `final_capstone_report.pdf`. Report source and generated metrics remain in this folder.

## Tasks and interpretation

### Classification and regression

Classification compares logistic regression, random forest, and a small multilayer perceptron; regression compares Ridge and random forest for traffic volume. The report includes accuracy, precision, recall, F1, ROC AUC, MAE, and R-squared, plus majority-class and training-median baselines. The proxy target may be imbalanced; class weighting is used for classification, but reported scores do not estimate accident prediction performance.

### Clustering and association rules

K-means clusters scaled traffic volume, time cycles, temperature, precipitation, snow, and cloud cover, not accident records. Four clusters are used for descriptive profiles; the sample silhouette and plain-language cluster summaries are included. Association-rule mining discretizes time band, weekday/weekend, and grouped weather, then reports support, confidence, and lift for high/severe congestion rules. These are historical associations, not causal statements.

### Neural network and explanation

The MLP is the neural-network model. LIME provides one local surrogate explanation of an MLP prediction; it is approximate and local rather than causal or a global account of model behavior.

### Advanced technique: MLflow experiment tracking

MLflow is used to compare chronological-holdout metrics and estimator parameters across the candidate algorithms, retain model artifacts, and register the selected proxy classifier and traffic regressor with versions. This makes the experiment and model lineage inspectable and repeatable without a hosted service. The tracking database and artifacts are local to this checkout; they are not backed up or shared, and registry versions alone do not establish model validity.

### Recommendations, deployment, and monitoring

The timing recommender ranks lower historical hourly averages by weekday/weekend and weather where sample counts support it. It addresses one corridor only and omits incidents, events, road works, and live traffic. The FastAPI service exposes a mock proxy endpoint:

```powershell
python -m uvicorn part3_machine_learning.deployment.app:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/docs` to try the endpoint. The monitoring script compares early and later chronological periods with PSI; it reports exactly `PASS / Normal` or `ALERT / Requires investigation`. This is a retrospective simulation, not production MLOps.

## Reproducibility and limitations

The MLflow store is local SQLite plus local artifact files; run training to populate it. The tracked `tracking_summary.json` preserves actual run parameters, metrics, and model versions without committing machine-specific file URIs. Inspect the local UI with:

```powershell
mlflow ui --backend-store-uri "sqlite:///C:/absolute/path/to/nus-capstone-final/part3_machine_learning/mlflow/mlflow.db"
```

MLflow serializes trusted local scikit-learn artifacts with cloudpickle for compatibility in this environment. Only load artifacts from this project after verifying their source; serialized Python models can execute code when loaded.

The input contains no accident labels, route alternatives, demographics, incidents, or real-time measurements. Model estimates are association-oriented and single-corridor only. No outputs should be used for safety-critical or enforcement decisions. Do not commit raw data, credentials, local caches, or a full virtual environment.
