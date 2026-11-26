import argparse
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from feature_engineering import engineer_features
from visualizations import create_all_visuals, display_path

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = {
    'holiday',
    'temp',
    'rain_1h',
    'snow_1h',
    'clouds_all',
    'weather_main',
    'weather_description',
    'date_time',
    'traffic_volume',
}


def configure_logger(log_path: Path) -> logging.Logger:
    logger_obj = logging.getLogger()
    logger_obj.setLevel(logging.DEBUG)
    for handler in logger_obj.handlers[:]:
        logger_obj.removeHandler(handler)
        handler.close()
    logging.getLogger('matplotlib').setLevel(logging.WARNING)

    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(name)s | %(message)s')

    file_handler = logging.FileHandler(log_path, mode='w', encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.INFO)

    logger_obj.addHandler(file_handler)
    logger_obj.addHandler(stream_handler)

    logger.debug('Debug logging is enabled only in pipeline.log; normal console output remains INFO-level.')
    logger.info('Logger configured for pipeline run.')
    return logger_obj


def load_dataset(path: Path) -> pd.DataFrame:
    logger.info('Loading raw dataset from %s', display_path(path))
    if not path.exists():
        raise FileNotFoundError(f'Dataset not found: {display_path(path)}')

    try:
        df = pd.read_csv(
            path,
            keep_default_na=False,
            na_values=['', 'NaN', 'nan', 'NA', 'N/A', 'NULL'],
        )
    except pd.errors.EmptyDataError as exc:
        raise ValueError(f'Dataset is empty: {display_path(path)}') from exc
    except pd.errors.ParserError as exc:
        raise ValueError(f'Dataset could not be parsed: {display_path(path)}') from exc

    logger.info('Loaded raw dataset with %s rows and %s columns.', df.shape[0], df.shape[1])
    missing = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f'Missing required columns: {sorted(missing)}')
    return df


def clean_dataset(df: pd.DataFrame) -> pd.DataFrame:
    logger.info('Starting dataset cleaning. Before cleaning shape=%s', df.shape)
    df = df.copy()

    initial_rows = len(df)
    df = df.drop_duplicates()
    removed_duplicates = initial_rows - len(df)
    if removed_duplicates:
        logger.warning(
            'Removed %s exact duplicate rows because repeated identical observations do not add new records.',
            removed_duplicates,
        )
    else:
        logger.debug('Duplicate check complete: no exact duplicate rows found.')

    for col in ['temp', 'rain_1h', 'snow_1h', 'clouds_all', 'traffic_volume']:
        original_values = df[col]
        numeric_values = pd.to_numeric(original_values, errors='coerce')
        nonblank_values = (
            original_values.notna()
            & original_values.astype('string').str.strip().ne('').fillna(False)
        )
        conversion_failures = int((nonblank_values & numeric_values.isna()).sum())
        if conversion_failures:
            logger.warning(
                'Coerced %s non-numeric %s values to missing so physical checks and imputation can handle them.',
                conversion_failures,
                col,
            )
        else:
            logger.debug('Numeric parsing for %s completed with no conversion failures.', col)
        df[col] = numeric_values

    impossible_temp_mask = (df['temp'] < 150) | (df['temp'] > 400)
    impossible_traffic_mask = df['traffic_volume'] < 0
    impossible_temp_rows = int(impossible_temp_mask.sum())
    impossible_traffic_rows = int(impossible_traffic_mask.sum())

    if impossible_temp_rows:
        logger.warning(
            'Set %s temperatures outside the plausible 150–400 K range to missing before imputation.',
            impossible_temp_rows,
        )
        df.loc[impossible_temp_mask, 'temp'] = pd.NA
    else:
        logger.debug('Temperature physical-range check found no values outside 150–400 K.')

    if impossible_traffic_rows:
        logger.warning(
            'Set %s negative traffic-volume values to missing because vehicle counts cannot be negative.',
            impossible_traffic_rows,
        )
        df.loc[impossible_traffic_mask, 'traffic_volume'] = pd.NA
    else:
        logger.debug('Traffic-volume physical-range check found no negative values.')

    for col, lower, upper, unit in [
        ('rain_1h', 0, 500, 'mm/hour'),
        ('snow_1h', 0, 500, 'mm/hour'),
        ('clouds_all', 0, 100, 'percent'),
    ]:
        invalid_mask = df[col].notna() & (df[col].lt(lower) | df[col].gt(upper))
        invalid_count = int(invalid_mask.sum())
        if invalid_count:
            logger.warning(
                'Set %s %s values outside the documented physical range [%s, %s] %s to missing before median imputation.',
                invalid_count,
                col,
                lower,
                upper,
                unit,
            )
            df.loc[invalid_mask, col] = pd.NA
        else:
            logger.debug(
                'Physical-range check found no %s values outside [%s, %s] %s.',
                col,
                lower,
                upper,
                unit,
            )

    original_timestamps = df['date_time']
    parsed_timestamps = pd.to_datetime(original_timestamps, errors='coerce')
    missing_timestamps = int(original_timestamps.isna().sum())
    unparseable_timestamps = int((original_timestamps.notna() & parsed_timestamps.isna()).sum())
    invalid_timestamp_rows = missing_timestamps + unparseable_timestamps
    df['date_time'] = parsed_timestamps
    if invalid_timestamp_rows:
        logger.warning(
            'Removed %s rows with missing or unparseable timestamps (%s missing, %s unparseable) because time features require valid timestamps.',
            invalid_timestamp_rows,
            missing_timestamps,
            unparseable_timestamps,
        )
        df = df[df['date_time'].notna()].copy()
    else:
        logger.debug('Timestamp validation found no missing or unparseable values.')

    for col in ['holiday', 'weather_main', 'weather_description']:
        original_values = df[col]
        missing_count = int(original_values.isna().sum())
        blank_mask = (
            original_values.notna()
            & original_values.astype('string').str.strip().eq('').fillna(False)
        )
        blank_count = int(blank_mask.sum())
        values = original_values.fillna('Unknown').astype(str)
        trimmed_values = values.str.strip()
        trimmed_count = int(((values != trimmed_values) & ~blank_mask).sum())
        trimmed_values.loc[trimmed_values.eq('')] = 'Unknown'

        if missing_count:
            logger.warning(
                'Replaced %s missing %s categories with Unknown because category values must be explicit.',
                missing_count,
                col,
            )
        else:
            logger.debug('No missing %s categories required replacement.', col)

        if blank_count:
            logger.warning(
                'Replaced %s blank %s categories with Unknown because empty labels are not valid categories.',
                blank_count,
                col,
            )
        else:
            logger.debug('No blank %s categories required replacement.', col)

        if trimmed_count:
            logger.warning(
                'Trimmed surrounding whitespace from %s %s category values to normalize grouping labels.',
                trimmed_count,
                col,
            )
        else:
            logger.debug('No %s category values required whitespace trimming.', col)

        if col == 'weather_main':
            standardized_values = trimmed_values.str.title()
            standardized_count = int((trimmed_values != standardized_values).sum())
            if standardized_count:
                logger.warning(
                    'Standardized %s weather_main values to title case for consistent category grouping.',
                    standardized_count,
                )
            else:
                logger.debug('No weather_main values required case standardization.')
            trimmed_values = standardized_values
        elif col == 'weather_description':
            standardized_values = trimmed_values.str.lower()
            standardized_count = int((trimmed_values != standardized_values).sum())
            if standardized_count:
                logger.warning(
                    'Standardized %s weather_description values to lowercase for consistent category grouping.',
                    standardized_count,
                )
            else:
                logger.debug('No weather_description values required case standardization.')
            trimmed_values = standardized_values

        df[col] = trimmed_values

    for col in ['rain_1h', 'snow_1h', 'clouds_all']:
        missing_count = int(df[col].isna().sum())
        if not missing_count:
            logger.debug('No missing %s values required imputation.', col)
            continue

        median_value = df[col].median()
        if pd.isna(median_value):
            raise ValueError(f'Cannot impute {col}: no valid values are available for the median.')

        df.loc[df[col].isna(), col] = median_value
        logger.warning(
            'Imputed %s missing %s values with the dataset median %.4f because no month-specific strategy is defined for this field.',
            missing_count,
            col,
            median_value,
        )

    for month in sorted(df['date_time'].dt.month.dropna().unique(), key=int):
        month_mask = df['date_time'].dt.month == month
        for col in ['temp', 'traffic_volume']:
            missing_count = int((month_mask & df[col].isna()).sum())
            if not missing_count:
                logger.debug('Month %s: no missing %s values required imputation.', int(month), col)
                continue

            median_value = df.loc[month_mask & df[col].notna(), col].median()
            if pd.isna(median_value):
                raise ValueError(
                    f'Cannot impute {col} for month {int(month)}: no valid values are available for the monthly median.'
                )

            df.loc[month_mask & df[col].isna(), col] = median_value
            logger.warning(
                'Month %s: imputed %s missing %s values with the month-specific median %.4f to preserve seasonal patterns.',
                int(month),
                missing_count,
                col,
                median_value,
            )

    logger.info('Cleaning complete. After cleaning shape=%s', df.shape)
    logger.debug('Cleaning retained %s of %s raw rows.', len(df), initial_rows)
    return df


def run_pipeline(
    data_path: str,
    output_dir: str,
    processed_dir: str | None = None,
) -> pd.DataFrame:
    data_file = Path(data_path)
    logger.info('Part 2 pipeline started at %s', datetime.now().isoformat())
    raw_df = load_dataset(data_file)
    cleaned = clean_dataset(raw_df)
    processed_folder = (
        Path(processed_dir)
        if processed_dir is not None
        else Path(__file__).resolve().parent / 'data' / 'processed'
    )
    processed_folder.mkdir(parents=True, exist_ok=True)
    cleaned_path = processed_folder / 'traffic_cleaned.csv'
    cleaned.to_csv(cleaned_path, index=False)
    logger.info('Saved cleaned data to %s', display_path(cleaned_path))

    logger.debug('Before feature engineering shape=%s', cleaned.shape)
    engineered = engineer_features(cleaned)
    logger.info('Feature engineering complete. Before/after shape=%s -> %s', cleaned.shape, engineered.shape)

    output_folder = Path(output_dir)
    output_folder.mkdir(parents=True, exist_ok=True)

    figures = create_all_visuals(engineered, output_folder)
    logger.info('Generated visual outputs: %s', [display_path(path) for path in figures])

    save_path = processed_folder / 'traffic_features.csv'
    engineered.to_csv(save_path, index=False)
    logger.info('Saved engineered feature data to %s', display_path(save_path))
    logger.info('Pipeline finished successfully.')
    return engineered


def main() -> None:
    parser = argparse.ArgumentParser(description='Smart City Traffic Pipeline')
    parser.add_argument('--data', default=str(Path(__file__).resolve().parents[1] / 'Metro_Interstate_Traffic_Volume.csv'), help='Path to the raw CSV file')
    parser.add_argument('--output-dir', default=str(Path(__file__).resolve().parent / 'figures'), help='Folder for generated figures')
    parser.add_argument('--processed-dir', default=str(Path(__file__).resolve().parent / 'data' / 'processed'), help='Folder for cleaned and feature-engineered CSV outputs')
    args = parser.parse_args()

    try:
        configure_logger(Path(__file__).resolve().parent / 'pipeline.log')
        run_pipeline(args.data, args.output_dir, args.processed_dir)
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        logger.exception('Fatal pipeline failure: %s', exc)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
