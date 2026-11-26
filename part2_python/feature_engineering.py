import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add time-based derived features used for later analysis."""
    logger.info('Adding time features to dataframe.')
    df = df.copy()
    df['date_time'] = pd.to_datetime(df['date_time'], errors='coerce')
    df['hour'] = df['date_time'].dt.hour
    df['day_of_week'] = df['date_time'].dt.day_name()
    df['day_of_week_num'] = df['date_time'].dt.day_of_week
    df['weekend_flag'] = df['day_of_week_num'].apply(lambda x: 1 if x >= 5 else 0)
    df['month'] = df['date_time'].dt.month
    df['date'] = df['date_time'].dt.date
    df['time_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
    df['time_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
    df['day_of_week_sin'] = np.sin(2 * np.pi * df['day_of_week_num'] / 7)
    df['day_of_week_cos'] = np.cos(2 * np.pi * df['day_of_week_num'] / 7)
    logger.info('Time features created with hour, weekday, weekend, month, and cyclic encodings.')
    return df


def add_weather_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add flags and encoded weather variables."""
    logger.info('Adding weather-derived features.')
    df = df.copy()
    weather_categories = pd.Categorical(df['weather_main'].fillna('Unknown'))
    df['weather_code'] = weather_categories.codes
    df['clear_flag'] = (df['weather_main'].fillna('Unknown').str.lower() == 'clear').astype(int)
    df['rain_flag'] = (df['rain_1h'] > 0).astype(int)
    df['snow_flag'] = (df['snow_1h'] > 0).astype(int)
    df['low_visibility_flag'] = (df['clouds_all'] >= 80).astype(int)
    logger.info('Weather flags created for clear, rain, snow, and visibility conditions.')
    return df


def add_scaled_features(df: pd.DataFrame, columns=('temp', 'traffic_volume')) -> pd.DataFrame:
    """Create scaled versions of selected continuous variables."""
    logger.info('Scaling selected continuous variables.')
    df = df.copy()
    for col in columns:
        if col in df.columns:
            mean_val = df[col].mean()
            std_val = df[col].std(ddof=0)
            if std_val == 0 or pd.isna(std_val):
                df[f'{col}_scaled'] = 0.0
            else:
                df[f'{col}_scaled'] = (df[col] - mean_val) / std_val
    logger.info('Scaling complete for continuous variables.')
    return df


def build_congestion_category(df: pd.DataFrame) -> pd.DataFrame:
    """Create a documented quartile-based congestion category."""
    logger.info('Creating congestion category.')
    df = df.copy()
    q1 = df['traffic_volume'].quantile(0.25)
    q2 = df['traffic_volume'].quantile(0.50)
    q3 = df['traffic_volume'].quantile(0.75)

    df['congestion_category'] = pd.cut(
        df['traffic_volume'],
        bins=[float('-inf'), q1, q2, q3, float('inf')],
        labels=['Low', 'Medium', 'High', 'Severe'],
        include_lowest=True,
    ).astype(str)
    logger.info(
        'Congestion category created using quartile thresholds: Q1=%.4f, Q2=%.4f, Q3=%.4f.',
        q1,
        q2,
        q3,
    )
    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Main feature engineering entry point."""
    df = add_time_features(df)
    df = add_weather_features(df)
    df = add_scaled_features(df, columns=['temp', 'traffic_volume'])
    df = build_congestion_category(df)
    return df
