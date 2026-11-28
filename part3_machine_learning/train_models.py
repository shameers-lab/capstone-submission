import json
import logging
from itertools import combinations
from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from lime.lime_tabular import LimeTabularExplainer
from mlflow.tracking import MlflowClient
from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.metrics import silhouette_score

from .feature_utils import (
    ABLATION_FEATURES,
    CATEGORICAL_FEATURES,
    MODEL_FEATURES,
    NUMERIC_FEATURES,
    add_model_features,
    create_targets,
    load_processed_data,
)

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PART3_DIR = Path(__file__).resolve().parent
DEFAULT_DATA = PROJECT_ROOT / "part2_python" / "data" / "processed" / "traffic_features.csv"


def configure_logging() -> None:
    log_path = PART3_DIR / "pipeline.log"
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()
    file_handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


def make_preprocessor(features: list[str]) -> ColumnTransformer:
    numeric = [column for column in NUMERIC_FEATURES if column in features]
    categorical = [column for column in CATEGORICAL_FEATURES if column in features]
    return ColumnTransformer(
        [
            (
                "numeric",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                numeric,
            ),
            ("categorical", OneHotEncoder(handle_unknown="ignore"), categorical),
        ],
        remainder="drop",
    )


def classification_metrics(y_true: pd.Series, probabilities: np.ndarray) -> dict[str, float]:
    predictions = (probabilities >= 0.5).astype("int8")
    metrics = {
        "accuracy": float(accuracy_score(y_true, predictions)),
        "precision": float(precision_score(y_true, predictions, zero_division=0)),
        "recall": float(recall_score(y_true, predictions, zero_division=0)),
        "f1": float(f1_score(y_true, predictions, zero_division=0)),
    }
    metrics["roc_auc"] = (
        float(roc_auc_score(y_true, probabilities))
        if pd.Series(y_true).nunique() == 2
        else float("nan")
    )
    return metrics


def log_candidate_run(
    name: str, metrics: dict[str, float], task: str, estimator: object
) -> None:
    with mlflow.start_run(run_name=f"{task}_{name}"):
        mlflow.log_param("algorithm", name)
        mlflow.log_param("task", task)
        mlflow.log_param("validation", "chronological 80/20")
        mlflow.log_params(
            {
                f"estimator.{key}": str(value)[:500]
                for key, value in estimator.get_params(deep=False).items()
                if value is not None
            }
        )
        for metric, value in metrics.items():
            if np.isfinite(value):
                mlflow.log_metric(metric, value)


def save_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    def convert(item: object) -> object:
        if isinstance(item, (np.integer,)):
            return int(item)
        if isinstance(item, (np.floating,)):
            return float(item)
        if isinstance(item, (pd.Timestamp,)):
            return item.isoformat()
        if isinstance(item, Path):
            return str(item)
        raise TypeError(f"Object of type {type(item).__name__} is not JSON serializable")

    path.write_text(json.dumps(value, indent=2, allow_nan=False, default=convert), encoding="utf-8")


def log_registered_model(
    model: Pipeline,
    experiment_name: str,
    registry_name: str,
    x_sample: pd.DataFrame,
    metrics: dict[str, float],
    parameters: dict[str, object],
) -> int:
    mlflow.set_experiment(experiment_name)
    with mlflow.start_run(run_name=f"registered_{registry_name}") as run:
        mlflow.log_params(parameters)
        mlflow.log_metrics({key: value for key, value in metrics.items() if np.isfinite(value)})
        mlflow.sklearn.log_model(
            sk_model=model,
            name="model",
            input_example=x_sample.head(3),
            serialization_format="cloudpickle",
            registered_model_name=registry_name,
        )
        client = MlflowClient()
        versions = client.search_model_versions(f"name='{registry_name}'")
        version = max(int(item.version) for item in versions)
        logger.info(
            "Registered %s version %s from MLflow run %s.",
            registry_name,
            version,
            run.info.run_id,
        )
        return version


def write_mlflow_summary(experiment_name: str, output_path: Path) -> None:
    client = MlflowClient()
    experiment = client.get_experiment_by_name(experiment_name)
    if experiment is None:
        raise ValueError(f"MLflow experiment was not created: {experiment_name}")
    runs = client.search_runs(
        [experiment.experiment_id],
        order_by=["attributes.start_time ASC"],
    )
    run_summaries = [
        {
            "run_id": run.info.run_id,
            "run_name": run.data.tags.get("mlflow.runName", ""),
            "parameters": dict(run.data.params),
            "metrics": {key: float(value) for key, value in run.data.metrics.items()},
        }
        for run in runs
    ]
    registered_models = {}
    for model_name in [
        "MetroTrafficProxyRiskClassifier",
        "MetroTrafficVolumeRegressor",
    ]:
        registered_models[model_name] = [
            {
                "version": int(item.version),
                "run_id": item.run_id,
                "status": item.status,
            }
            for item in client.search_model_versions(f"name='{model_name}'")
        ]
    save_json(
        output_path,
        {
            "experiment_name": experiment_name,
            "tracked_runs": run_summaries,
            "registered_models": registered_models,
            "note": (
                "Portable summary exported from the local MLflow tracking store. The SQLite database and "
                "artifact files use machine-specific file URIs and are intentionally not versioned."
            ),
        },
    )


def fit_classifiers(
    x_train: pd.DataFrame,
    y_train: pd.Series,
    x_test: pd.DataFrame,
    y_test: pd.Series,
) -> tuple[dict[str, object], dict[str, dict[str, float]]]:
    estimators = {
        "logistic_regression": LogisticRegression(
            max_iter=1200, class_weight="balanced", random_state=42
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=80,
            max_depth=10,
            min_samples_leaf=8,
            class_weight="balanced_subsample",
            n_jobs=-1,
            random_state=42,
        ),
        "mlp_neural_network": MLPClassifier(
            hidden_layer_sizes=(32, 16),
            max_iter=120,
            early_stopping=True,
            random_state=42,
        ),
    }
    fitted: dict[str, object] = {}
    metrics_by_model: dict[str, dict[str, float]] = {}
    for name, estimator in estimators.items():
        model = Pipeline(
            [("preprocess", make_preprocessor(MODEL_FEATURES)), ("estimator", estimator)]
        )
        logger.info("Fitting proxy classification model: %s", name)
        model.fit(x_train[MODEL_FEATURES], y_train)
        probabilities = model.predict_proba(x_test[MODEL_FEATURES])[:, 1]
        metrics = classification_metrics(y_test, probabilities)
        fitted[name] = model
        metrics_by_model[name] = metrics
        log_candidate_run(name, metrics, "proxy_classification", estimator)
        logger.info("%s holdout metrics: %s", name, metrics)
    return fitted, metrics_by_model


def fit_ablation(
    x_train: pd.DataFrame, y_train: pd.Series, x_test: pd.DataFrame, y_test: pd.Series
) -> dict[str, float]:
    model = Pipeline(
        [
            ("preprocess", make_preprocessor(ABLATION_FEATURES)),
            ("estimator", LogisticRegression(max_iter=1200, class_weight="balanced", random_state=42)),
        ]
    )
    model.fit(x_train[ABLATION_FEATURES], y_train)
    return classification_metrics(y_test, model.predict_proba(x_test[ABLATION_FEATURES])[:, 1])


def fit_regressors(
    x_train: pd.DataFrame,
    y_train: pd.Series,
    x_test: pd.DataFrame,
    y_test: pd.Series,
) -> tuple[dict[str, object], dict[str, dict[str, float]]]:
    estimators = {
        "ridge_regression": Ridge(alpha=1.0),
        "random_forest_regression": RandomForestRegressor(
            n_estimators=80,
            max_depth=10,
            min_samples_leaf=8,
            n_jobs=-1,
            random_state=42,
        ),
    }
    fitted: dict[str, object] = {}
    metrics_by_model: dict[str, dict[str, float]] = {}
    for name, estimator in estimators.items():
        model = Pipeline(
            [("preprocess", make_preprocessor(MODEL_FEATURES)), ("estimator", estimator)]
        )
        logger.info("Fitting traffic-volume regression model: %s", name)
        model.fit(x_train[MODEL_FEATURES], y_train)
        predictions = model.predict(x_test[MODEL_FEATURES])
        metrics = {
            "mae": float(mean_absolute_error(y_test, predictions)),
            "r_squared": float(r2_score(y_test, predictions)),
        }
        fitted[name] = model
        metrics_by_model[name] = metrics
        log_candidate_run(name, metrics, "traffic_regression", estimator)
        logger.info("%s holdout metrics: %s", name, metrics)
    return fitted, metrics_by_model


def group_error_metrics(
    classifier: Pipeline,
    regressor: Pipeline,
    x_test: pd.DataFrame,
    y_test: pd.Series,
    y_test_traffic: pd.Series,
) -> dict[str, dict[str, dict[str, float]]]:
    probabilities = classifier.predict_proba(x_test[MODEL_FEATURES])[:, 1]
    predictions = (probabilities >= 0.5).astype("int8")
    volume_predictions = regressor.predict(x_test[MODEL_FEATURES])
    grouped_data = x_test.copy()
    grouped_data["time_band"] = pd.cut(
        grouped_data["date_time"].dt.hour,
        bins=[-1, 5, 9, 15, 19, 23],
        labels=["Overnight", "AM peak", "Midday", "PM peak", "Evening"],
    ).astype(str)
    results: dict[str, dict[str, dict[str, float]]] = {}
    for column in ["day_type", "time_band", "weather_main"]:
        groups: dict[str, dict[str, float]] = {}
        for label, indexes in grouped_data.groupby(column, dropna=False, observed=True).groups.items():
            subset = x_test.index.isin(indexes)
            actual_proxy = y_test.loc[indexes]
            actual_volume = y_test_traffic.loc[indexes]
            if len(indexes) < 30:
                continue
            subset_probability = probabilities[subset]
            subset_prediction = predictions[subset]
            subset_volume_prediction = volume_predictions[subset]
            groups[str(label)] = {
                "n": int(len(indexes)),
                "proxy_prevalence": float(actual_proxy.mean()),
                "proxy_precision": float(precision_score(actual_proxy, subset_prediction, zero_division=0)),
                "proxy_recall": float(recall_score(actual_proxy, subset_prediction, zero_division=0)),
                "proxy_f1": float(f1_score(actual_proxy, subset_prediction, zero_division=0)),
                "proxy_mean_probability": float(subset_probability.mean()),
                "traffic_mae": float(mean_absolute_error(actual_volume, subset_volume_prediction)),
            }
        results[column] = groups
    return results


def fit_clusters(features: pd.DataFrame, out_dir: Path) -> dict[str, float]:
    columns = [
        "traffic_volume",
        "temp",
        "rain_1h",
        "snow_1h",
        "clouds_all",
        "hour_sin",
        "hour_cos",
        "day_of_week_sin",
        "day_of_week_cos",
    ]
    cluster_data = features[columns].fillna(features[columns].median())
    scaler = StandardScaler()
    scaled = scaler.fit_transform(cluster_data)
    model = KMeans(n_clusters=4, n_init=10, random_state=42)
    labels = model.fit_predict(scaled)
    score_sample_size = min(3000, len(scaled))
    sample_indexes = np.linspace(0, len(scaled) - 1, score_sample_size, dtype=int)
    silhouette = float(
        silhouette_score(scaled[sample_indexes], labels[sample_indexes], metric="euclidean")
    )
    clustered = features[
        ["traffic_volume", "temp", "rain_1h", "snow_1h", "clouds_all", "hour", "day_type", "weather_main"]
    ].copy()
    clustered["time_band"] = pd.cut(
        clustered["hour"],
        bins=[-1, 5, 9, 15, 19, 23],
        labels=["Overnight", "AM peak", "Midday", "PM peak", "Evening"],
    ).astype(str)
    clustered["cluster"] = labels
    profiles = (
        clustered.groupby("cluster", observed=True)
        .agg(
            observations=("traffic_volume", "size"),
            mean_traffic=("traffic_volume", "mean"),
            median_traffic=("traffic_volume", "median"),
            mean_temperature_k=("temp", "mean"),
            mean_rain_1h=("rain_1h", "mean"),
            mean_snow_1h=("snow_1h", "mean"),
            mean_cloud_cover=("clouds_all", "mean"),
            mean_hour=("hour", "mean"),
            weekend_share=("day_type", lambda values: float((values == "Weekend").mean())),
            dominant_time_band=("time_band", lambda values: str(values.mode().iloc[0])),
            dominant_weather=("weather_main", lambda values: str(values.mode().iloc[0])),
        )
        .reset_index()
    )
    overall_median = float(features["traffic_volume"].median())

    def describe_cluster(row: pd.Series) -> str:
        traffic_level = "above" if row["mean_traffic"] > overall_median else "at or below"
        cloud_context = "high average cloud cover" if row["mean_cloud_cover"] >= 80 else "lower average cloud cover"
        precipitation = (
            "with measurable average rainfall" if row["mean_rain_1h"] > 0 else "with no average rainfall"
        )
        return (
            f"Mean traffic is {traffic_level} the full-period median; the most common time band is "
            f"{row['dominant_time_band']}, modal weather is {row['dominant_weather']}, and conditions show "
            f"{cloud_context} {precipitation}."
        )

    profiles["plain_language_interpretation"] = profiles.apply(describe_cluster, axis=1)
    out_dir.mkdir(parents=True, exist_ok=True)
    profiles.to_csv(out_dir / "cluster_profiles.csv", index=False)
    joblib.dump({"scaler": scaler, "model": model, "features": columns}, out_dir / "traffic_kmeans.joblib")
    logger.info("K-means completed with 4 clusters; sample silhouette score=%.4f.", silhouette)
    return {"n_clusters": 4, "silhouette_sample_size": score_sample_size, "silhouette_score": silhouette}


def mine_association_rules(features: pd.DataFrame, out_dir: Path) -> pd.DataFrame:
    rules_data = pd.DataFrame(index=features.index)
    hour = features["date_time"].dt.hour
    rules_data["time_band"] = pd.cut(
        hour,
        bins=[-1, 5, 9, 15, 19, 23],
        labels=["Overnight", "AM peak", "Midday", "PM peak", "Evening"],
    ).astype(str)
    rules_data["day_type"] = features["day_type"]
    rules_data["weather_group"] = features["weather_main_normalized"].map(
        lambda value: (
            "Clear" if value == "clear" else
            "Rain" if value in {"rain", "drizzle"} else
            "Snow" if value == "snow" else
            "Thunderstorm" if value == "thunderstorm" else
            "Fog_or_low_visibility" if value in {"fog", "mist", "haze", "smoke"} else
            "Other"
        )
    )
    rules_data["high_or_severe_congestion"] = features["congestion_category"].isin(["High", "Severe"])
    base_rate = float(rules_data["high_or_severe_congestion"].mean())
    condition_columns = ["time_band", "day_type", "weather_group"]
    rule_rows: list[dict[str, object]] = []
    for size in (1, 2):
        for fields in combinations(condition_columns, size):
            for value_tuple in rules_data[list(fields)].drop_duplicates().itertuples(index=False, name=None):
                mask = pd.Series(True, index=rules_data.index)
                antecedent = []
                for field, value in zip(fields, value_tuple):
                    mask &= rules_data[field].eq(value)
                    antecedent.append(f"{field}={value}")
                antecedent_count = int(mask.sum())
                both_count = int((mask & rules_data["high_or_severe_congestion"]).sum())
                support = both_count / len(rules_data)
                confidence = both_count / antecedent_count if antecedent_count else 0.0
                lift = confidence / base_rate if base_rate else float("nan")
                if support >= 0.01 and antecedent_count >= 30:
                    rule_rows.append(
                        {
                            "antecedent": " AND ".join(antecedent),
                            "consequent": "high_or_severe_congestion",
                            "antecedent_count": antecedent_count,
                            "support": support,
                            "confidence": confidence,
                            "lift": lift,
                        }
                    )
    rules = pd.DataFrame(rule_rows)
    if not rules.empty:
        rules = rules.sort_values(["lift", "confidence", "support"], ascending=False)
    out_dir.mkdir(parents=True, exist_ok=True)
    rules.to_csv(out_dir / "association_rules.csv", index=False)
    logger.info("Association rule mining generated %s qualifying rules.", len(rules))
    return rules


def explain_mlp_with_lime(
    model: Pipeline, x_train: pd.DataFrame, x_test: pd.DataFrame, out_path: Path
) -> dict[str, object]:
    categorical_positions = [MODEL_FEATURES.index(column) for column in CATEGORICAL_FEATURES]
    category_values = {
        column: sorted(x_train[column].astype(str).unique().tolist()) for column in CATEGORICAL_FEATURES
    }
    category_codes = {
        column: {value: index for index, value in enumerate(values)}
        for column, values in category_values.items()
    }
    numeric_medians = x_train[NUMERIC_FEATURES].median()

    def encode(frame: pd.DataFrame) -> np.ndarray:
        encoded = frame[MODEL_FEATURES].copy()
        for column in NUMERIC_FEATURES:
            encoded[column] = pd.to_numeric(encoded[column], errors="coerce").fillna(
                numeric_medians[column]
            )
        for column in CATEGORICAL_FEATURES:
            encoded[column] = encoded[column].astype(str).map(category_codes[column]).fillna(-1)
        return encoded.to_numpy(dtype=float)

    def predict(encoded_values: np.ndarray) -> np.ndarray:
        frame = pd.DataFrame(encoded_values, columns=MODEL_FEATURES)
        for column in CATEGORICAL_FEATURES:
            rounded = frame[column].round().astype(int)
            values = category_values[column]
            frame[column] = [
                values[index] if 0 <= index < len(values) else "Unknown"
                for index in rounded
            ]
        return model.predict_proba(frame[MODEL_FEATURES])

    explainer = LimeTabularExplainer(
        training_data=encode(x_train),
        feature_names=MODEL_FEATURES,
        class_names=["Not proxy-positive", "Proxy-positive"],
        categorical_features=categorical_positions,
        categorical_names={
            MODEL_FEATURES.index(column): values for column, values in category_values.items()
        },
        mode="classification",
        discretize_continuous=True,
        random_state=42,
    )
    sample = x_test[MODEL_FEATURES].iloc[len(x_test) // 2]
    explanation = explainer.explain_instance(
        encode(sample.to_frame().T)[0],
        predict,
        num_features=min(12, len(MODEL_FEATURES)),
        num_samples=1200,
    )
    result = {
        "model": "mlp_neural_network",
        "method": "LIME tabular local surrogate",
        "test_observation_date_time": str(x_test.iloc[len(x_test) // 2]["date_time"]),
        "predicted_proxy_probability": float(model.predict_proba(sample.to_frame().T)[0, 1]),
        "local_feature_contributions": [
            {"condition": condition, "contribution": float(weight)}
            for condition, weight in explanation.as_list()
        ],
        "limitation": "One local approximation; not a causal explanation or global model summary.",
    }
    save_json(out_path, result)
    return result


def run(data_path: Path = DEFAULT_DATA) -> dict[str, object]:
    configure_logging()
    PART3_DIR.mkdir(parents=True, exist_ok=True)
    models_dir = PART3_DIR / "models"
    mlflow_dir = PART3_DIR / "mlflow"
    models_dir.mkdir(parents=True, exist_ok=True)
    mlflow_dir.mkdir(parents=True, exist_ok=True)
    database_path = (mlflow_dir / "mlflow.db").resolve()
    tracking_uri = f"sqlite:///{database_path.as_posix()}"
    mlflow.set_tracking_uri(tracking_uri)
    if mlflow.get_experiment_by_name("metro-traffic-capstone") is None:
        mlflow.create_experiment(
            "metro-traffic-capstone",
            artifact_location=(mlflow_dir / "artifacts").resolve().as_uri(),
        )
    mlflow.set_experiment("metro-traffic-capstone")

    raw = load_processed_data(data_path)
    split_index = int(len(raw) * 0.8)
    if split_index < 2 or split_index >= len(raw):
        raise ValueError("Not enough chronological observations for an 80/20 split.")
    train_raw, test_raw = raw.iloc[:split_index], raw.iloc[split_index:]
    train_data, thresholds = create_targets(train_raw)
    full_data, _ = create_targets(raw, (thresholds["q1"], thresholds["q2"], thresholds["q3"]))
    test_data = full_data.iloc[split_index:].copy()
    train_features = add_model_features(train_data)
    test_features = add_model_features(test_data)
    y_train = train_data["proxy_accident_risk"]
    y_test = test_data["proxy_accident_risk"]
    if y_train.nunique() != 2 or y_test.nunique() != 2:
        raise ValueError("Proxy label must contain both classes in chronological train and test splits.")
    x_train = train_features
    x_test = test_features
    y_train_traffic = train_data["traffic_volume"]
    y_test_traffic = test_data["traffic_volume"]

    class_counts = y_train.value_counts().to_dict()
    majority_label = int(y_train.mode().iloc[0])
    majority_baseline = float((y_test == majority_label).mean())
    regression_baseline_mae = float(mean_absolute_error(y_test_traffic, np.repeat(y_train_traffic.median(), len(y_test))))
    logger.info(
        "Chronological split: train=%s rows, test=%s rows; proxy positives train=%s, test=%s.",
        len(x_train), len(x_test), int(y_train.sum()), int(y_test.sum())
    )

    classifiers, classification_results = fit_classifiers(x_train, y_train, x_test, y_test)
    ablation_metrics = fit_ablation(x_train, y_train, x_test, y_test)
    regressors, regression_results = fit_regressors(
        x_train, y_train_traffic, x_test, y_test_traffic
    )
    best_classifier_name = max(
        classification_results,
        key=lambda name: (
            classification_results[name]["f1"],
            classification_results[name]["roc_auc"],
        ),
    )
    best_regressor_name = min(regression_results, key=lambda name: regression_results[name]["mae"])
    best_classifier = classifiers[best_classifier_name]
    best_regressor = regressors[best_regressor_name]

    model_versions = {
        "proxy_risk_classifier": log_registered_model(
            best_classifier,
            "metro-traffic-capstone",
            "MetroTrafficProxyRiskClassifier",
            x_train[MODEL_FEATURES],
            classification_results[best_classifier_name],
            {"algorithm": best_classifier_name, "threshold": 0.5, "split": "chronological 80/20"},
        ),
        "traffic_volume_regressor": log_registered_model(
            best_regressor,
            "metro-traffic-capstone",
            "MetroTrafficVolumeRegressor",
            x_train[MODEL_FEATURES],
            regression_results[best_regressor_name],
            {"algorithm": best_regressor_name, "split": "chronological 80/20"},
        ),
    }
    joblib.dump(best_classifier, models_dir / "proxy_risk_classifier.joblib")
    joblib.dump(best_regressor, models_dir / "traffic_volume_regressor.joblib")

    fairness = group_error_metrics(
        best_classifier, best_regressor, x_test, y_test, y_test_traffic
    )
    try:
        report_data_path = data_path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        report_data_path = data_path.name
    metrics = {
        "dataset": {
            "path": report_data_path,
            "rows": int(len(raw)),
            "date_start": str(raw["date_time"].min()),
            "date_end": str(raw["date_time"].max()),
            "columns": int(raw.attrs["part3_source_column_count"]),
            "provenance_note": "Processed Part 2 output; raw CSV was not present in the checkout.",
            "part3_impossible_weather_values_set_missing": raw.attrs.get(
                "part3_invalid_weather_counts", {}
            ),
        },
        "split": {
            "method": "chronological",
            "train_rows": int(len(train_data)),
            "test_rows": int(len(test_data)),
            "train_start": str(train_raw["date_time"].min()),
            "train_end": str(train_raw["date_time"].max()),
            "test_start": str(test_raw["date_time"].min()),
            "test_end": str(test_raw["date_time"].max()),
        },
        "proxy_label": {
            "definition": "traffic_volume > training Q2 and (severe weather category or clouds_all >= 80)",
            "severe_weather_categories": sorted(
                ["Drizzle", "Dust", "Fog", "Haze", "Mist", "Rain", "Sand", "Smoke", "Snow", "Squall", "Thunderstorm", "Tornado"]
            ),
            "low_visibility_definition": "clouds_all >= 80 on the source 0-100 scale",
            "training_congestion_thresholds": thresholds,
            "train_positive_count": int(y_train.sum()),
            "train_positive_rate": float(y_train.mean()),
            "test_positive_count": int(y_test.sum()),
            "test_positive_rate": float(y_test.mean()),
            "train_class_counts": {str(key): int(value) for key, value in class_counts.items()},
        },
        "baselines": {
            "majority_class_accuracy": majority_baseline,
            "median_training_traffic_mae": regression_baseline_mae,
        },
        "classification": classification_results,
        "classification_ablation_without_weather_features": ablation_metrics,
        "regression": regression_results,
        "selected_models": {
            "proxy_classifier": best_classifier_name,
            "traffic_regressor": best_regressor_name,
            "mlflow_model_versions": model_versions,
        },
        "group_error_analysis": fairness,
    }
    save_json(models_dir / "metrics.json", metrics)
    save_json(models_dir / "thresholds.json", thresholds)
    save_json(
        models_dir / "model_card.json",
        {
            "model_version": "1.0",
            "dataset": metrics["dataset"],
            "selected_models": metrics["selected_models"],
            "predictor_features": MODEL_FEATURES,
            "explicitly_excluded_predictors": [
                "traffic_volume",
                "congestion_category",
                "proxy_accident_risk",
                "all target-derived fields",
            ],
            "target_warning": "This is a congestion/weather proxy label, not an accident label or accident likelihood.",
        },
    )
    cluster_summary = fit_clusters(add_model_features(full_data), models_dir)
    rules = mine_association_rules(add_model_features(full_data), models_dir)
    lime_summary = explain_mlp_with_lime(
        classifiers["mlp_neural_network"], x_train, x_test, models_dir / "lime_explanation.json"
    )
    save_json(models_dir / "unsupervised_summary.json", cluster_summary)
    save_json(models_dir / "association_rules_summary.json", rules.head(10).to_dict(orient="records"))
    save_json(models_dir / "lime_summary.json", lime_summary)
    write_mlflow_summary("metro-traffic-capstone", mlflow_dir / "tracking_summary.json")
    logger.info("Part 3 model training and analysis completed.")
    return metrics


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Train and evaluate Part 3 traffic models.")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA, help="Processed Part 2 traffic CSV.")
    arguments = parser.parse_args()
    run(arguments.data)
