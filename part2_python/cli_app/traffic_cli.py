import argparse
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def configure_logger() -> None:
    logger_obj = logging.getLogger()
    logger_obj.setLevel(logging.DEBUG)
    for handler in logger_obj.handlers[:]:
        logger_obj.removeHandler(handler)
        handler.close()
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(name)s | %(message)s')

    log_path = Path(__file__).resolve().parents[1] / 'pipeline.log'
    file_handler = logging.FileHandler(log_path, mode='a', encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    stream = logging.StreamHandler()
    stream.setFormatter(formatter)
    stream.setLevel(logging.INFO)
    logger_obj.addHandler(file_handler)
    logger_obj.addHandler(stream)


def load_data(data_path: Path) -> pd.DataFrame:
    if not data_path.exists():
        raise FileNotFoundError(f'Input dataset not found: {data_path.name}')
    try:
        df = pd.read_csv(data_path)
    except pd.errors.EmptyDataError as exc:
        raise ValueError(f'Input dataset is empty: {data_path.name}') from exc
    except pd.errors.ParserError as exc:
        raise ValueError(f'Input dataset could not be parsed: {data_path.name}') from exc

    df['date_time'] = pd.to_datetime(df['date_time'], errors='coerce')
    return df


def parse_timestamp(value: str) -> pd.Timestamp:
    try:
        return pd.Timestamp(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'Invalid timestamp: {value}. Use YYYY-MM-DD HH:MM:SS format.') from exc


def query_timestamp(df: pd.DataFrame, timestamp: str) -> pd.DataFrame:
    ts = parse_timestamp(timestamp)
    match = df[df['date_time'] == ts]
    if match.empty:
        raise ValueError(f'No records found for timestamp {timestamp}.')
    return match


def query_high_traffic(df: pd.DataFrame, threshold: int) -> pd.DataFrame:
    if threshold <= 0:
        raise ValueError('Threshold must be positive.')
    return df[df['traffic_volume'] > threshold].sort_values('traffic_volume', ascending=False)


def query_day_type(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    weekday = df[df['date_time'].dt.day_of_week < 5]
    weekend = df[df['date_time'].dt.day_of_week >= 5]
    return pd.DataFrame({
        'day_type': ['Weekday', 'Weekend'],
        'avg_traffic': [weekday['traffic_volume'].mean(), weekend['traffic_volume'].mean()],
    })


def query_weather(df: pd.DataFrame, weather: str) -> pd.DataFrame:
    matches = df[df['weather_main'].fillna('Unknown').str.lower() == weather.lower().strip()]
    if matches.empty:
        raise ValueError(f'No rows found for weather condition: {weather}')
    return matches


def main() -> None:
    configure_logger()
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description='Traffic analysis CLI for smart city capstone')
    parser.add_argument('--data', default=str(root / 'Metro_Interstate_Traffic_Volume.csv'), help='Path to the source CSV file')
    subparsers = parser.add_subparsers(dest='command', required=True)

    lookup = subparsers.add_parser('lookup', help='Look up a timestamp in the dataset')
    lookup.add_argument('--timestamp', required=True)

    high = subparsers.add_parser('high-traffic', help='List high-traffic periods above a threshold')
    high.add_argument('--threshold', type=int, required=True)

    subparsers.add_parser('day-type', help='Compare weekday and weekend average traffic')

    weather = subparsers.add_parser('weather', help='Filter records by weather_main')
    weather.add_argument('--condition', required=True)

    args = parser.parse_args()

    df = load_data(Path(args.data))

    if args.command == 'lookup':
        result = query_timestamp(df, args.timestamp)
        print(result.head(5).to_string(index=False))
    elif args.command == 'high-traffic':
        result = query_high_traffic(df, args.threshold)
        print(result.head(10).to_string(index=False))
    elif args.command == 'day-type':
        result = query_day_type(df)
        print(result.to_string(index=False))
    elif args.command == 'weather':
        result = query_weather(df, args.condition)
        print(result.head(10).to_string(index=False))

    logger.info('CLI request completed successfully for command: %s', args.command)


if __name__ == '__main__':
    try:
        main()
    except (FileNotFoundError, ValueError) as exc:
        logger.error('CLI request failed: %s', exc)
        raise SystemExit(1)
