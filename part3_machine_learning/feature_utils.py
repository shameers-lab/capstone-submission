import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = {
    "holiday",
    "temp",
    "rain_1h",
    "snow_1h",
    "clouds_all",
    "weather_main",
    "date_time",
    "traffic_volume",
}

SEVERE_WEATHER_CATEGORIES = {
    "drizzle",
    "dust",
    "fog",
    "haze",
    "mist",
    "rain",
    "sand",
    "smoke",
    "snow",
    "squall",
    "thunderstorm",
    "tornado",
}

NUMERIC_FEATURES = [
    "temp",
    "rain_1h",
    "snow_1h",
    "clouds_all",
    "hour_sin",
    "hour_cos",
    "day_of_week_sin",
    "day_of_week_cos",
]
CATEGORICAL_FEATURES = ["holiday", "weather_main", "day_type"]
MODEL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
ABLATION_FEATURES = [
    "hour_sin",
    "hour_cos",
    "day_of_week_sin",
    "day_of_week_cos",
    "holiday",
    "day_type",
]


def load_processed_data(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Processed traffic data not found: {path}")
    data = pd.read_csv(path)
    source_column_count = int(data.shape[1])
    missing = REQUIRED_COLUMNS.difference(data.columns)
    if missing:
        raise ValueError(f"Processed data is missing required columns: {sorted(missing)}")
    data = data.copy()
    data["date_time"] = pd.to_datetime(data["date_time"], errors="coerce")
    data["traffic_volume"] = pd.to_numeric(data["traffic_volume"], errors="coerce")
    data["temp"] = pd.to_numeric(data["temp"], errors="coerce")
    data["rain_1h"] = pd.to_numeric(data["rain_1h"], errors="coerce")
    data["snow_1h"] = pd.to_numeric(data["snow_1h"], errors="coerce")
    data["clouds_all"] = pd.to_numeric(data["clouds_all"], errors="coerce")
    invalid_weather_counts: dict[str, int] = {}
    for column, lower, upper in [
        ("temp", 150.0, 400.0),
        ("rain_1h", 0.0, 500.0),
        ("snow_1h", 0.0, 500.0),
        ("clouds_all", 0.0, 100.0),
    ]:
        invalid = data[column].notna() & (
            data[column].lt(lower) | data[column].gt(upper)
        )
        invalid_count = int(invalid.sum())
        invalid_weather_counts[column] = invalid_count
        if invalid_count:
            data.loc[invalid, column] = np.nan
            logger.warning(
                "Set %s %s values outside the documented physical range [%s, %s] to missing for Part 3; "
                "numeric model imputation is fitted on training data.",
                invalid_count,
                column,
                lower,
                upper,
            )
    data = data.dropna(subset=["date_time", "traffic_volume"]).copy()
    data["holiday"] = data["holiday"].fillna("Unknown").astype(str).str.strip()
    data["weather_main"] = data["weather_main"].fillna("Unknown").astype(str).str.strip()
    data = data.sort_values("date_time", kind="stable").reset_index(drop=True)
    if data.empty:
        raise ValueError("No usable observations remain after validating timestamps and traffic volume.")
    if data["date_time"].duplicated().any():
        logger.warning(
            "%s timestamps have more than one observation; preserving all rows in stable order.",
            int(data["date_time"].duplicated(keep=False).sum()),
        )
    logger.info(
        "Loaded %s processed observations across %s to %s.",
        len(data),
        data["date_time"].min().date(),
        data["date_time"].max().date(),
    )
    data.attrs["part3_invalid_weather_counts"] = invalid_weather_counts
    data.attrs["part3_source_column_count"] = source_column_count
    return data


def add_model_features(data: pd.DataFrame) -> pd.DataFrame:
    features = data.copy()
    hour = features["date_time"].dt.hour
    day_of_week = features["date_time"].dt.dayofweek
    features["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    features["hour_cos"] = np.cos(2 * np.pi * hour / 24)
    features["day_of_week_sin"] = np.sin(2 * np.pi * day_of_week / 7)
    features["day_of_week_cos"] = np.cos(2 * np.pi * day_of_week / 7)
    features["day_type"] = np.where(day_of_week >= 5, "Weekend", "Weekday")
    holiday_values = features["holiday"].fillna("Unknown").astype(str).str.strip()
    no_holiday_count = int(holiday_values.eq("None").sum())
    if no_holiday_count:
        logger.info(
            "Mapped %s source no-holiday labels to the existing Unknown model category for encoder compatibility.",
            no_holiday_count,
        )
    features["holiday"] = holiday_values.replace({"": "Unknown", "None": "Unknown"})
    features["weather_main"] = features["weather_main"].replace("", "Unknown")
    features["weather_main_normalized"] = features["weather_main"].str.lower()
    for column in NUMERIC_FEATURES:
        features[column] = pd.to_numeric(features[column], errors="coerce").astype(float)
    return features


def create_targets(
    data: pd.DataFrame,
    congestion_thresholds: tuple[float, float, float] | None = None,
) -> tuple[pd.DataFrame, dict[str, float]]:
    features = add_model_features(data)
    if congestion_thresholds is None:
        quantiles = features["traffic_volume"].quantile([0.25, 0.50, 0.75])
        congestion_thresholds = (
            float(quantiles.loc[0.25]),
            float(quantiles.loc[0.50]),
            float(quantiles.loc[0.75]),
        )
    q1, q2, q3 = congestion_thresholds
    features["congestion_category"] = np.select(
        [
            features["traffic_volume"] <= q1,
            features["traffic_volume"] <= q2,
            features["traffic_volume"] <= q3,
        ],
        ["Low", "Medium", "High"],
        default="Severe",
    )
    severe_weather = features["weather_main_normalized"].isin(SEVERE_WEATHER_CATEGORIES)
    low_visibility = features["clouds_all"] >= 80
    features["proxy_accident_risk"] = (
        features["traffic_volume"].gt(q2) & (severe_weather | low_visibility)
    ).astype("int8")
    thresholds = {"q1": q1, "q2": q2, "q3": q3}
    logger.info(
        "Created training-threshold congestion bins (Q1=%.1f, Q2=%.1f, Q3=%.1f) and the explicitly defined proxy label.",
        q1,
        q2,
        q3,
    )
    return features, thresholds
