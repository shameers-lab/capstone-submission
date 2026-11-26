import logging
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

logger = logging.getLogger(__name__)


def display_path(path: Path) -> str:
    project_root = Path(__file__).resolve().parents[1]
    try:
        return path.resolve().relative_to(project_root).as_posix()
    except ValueError:
        return path.name


def save_figure(fig, path: Path) -> None:
    logger.debug('Saving figure to %s', display_path(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=200, bbox_inches='tight')
    plt.close(fig)
    logger.info('Saved figure to %s', display_path(path))


def plot_hourly_average_traffic(df: pd.DataFrame, output_dir: Path) -> Path:
    logger.info('Generating hourly average traffic figure.')
    by_hour = df.groupby('hour')['traffic_volume'].mean().sort_index()
    fig, ax = plt.subplots(figsize=(10, 5))
    by_hour.plot(kind='bar', ax=ax, color='steelblue')
    ax.set_title('Average Traffic Volume by Hour')
    ax.set_xlabel('Hour of Day')
    ax.set_ylabel('Average Traffic Volume')
    ax.grid(axis='y', linestyle='--', alpha=0.4)
    out = output_dir / 'hourly_average_traffic.png'
    save_figure(fig, out)
    return out


def plot_weather_average_traffic(df: pd.DataFrame, output_dir: Path) -> Path:
    logger.info('Generating weather impact figure.')
    weather_summary = df.groupby('weather_main')['traffic_volume'].mean().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(10, 5))
    weather_summary.plot(kind='bar', ax=ax, color='darkorange')
    ax.set_title('Average Traffic by Weather Condition')
    ax.set_xlabel('Weather')
    ax.set_ylabel('Average Traffic Volume')
    ax.grid(axis='y', linestyle='--', alpha=0.4)
    out = output_dir / 'weather_average_traffic.png'
    save_figure(fig, out)
    return out


def plot_weekday_weekend_comparison(df: pd.DataFrame, output_dir: Path) -> Path:
    logger.info('Generating weekday versus weekend comparison figure.')
    summary = df.groupby('weekend_flag')['traffic_volume'].mean().reset_index()
    summary['day_type'] = summary['weekend_flag'].map({0: 'Weekday', 1: 'Weekend'})
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(summary['day_type'], summary['traffic_volume'], color=['#4C72B0', '#DD8452'])
    ax.set_title('Average Traffic by Day Type')
    ax.set_xlabel('Day Type')
    ax.set_ylabel('Average Traffic Volume')
    ax.grid(axis='y', linestyle='--', alpha=0.4)
    out = output_dir / 'weekday_weekend_traffic.png'
    save_figure(fig, out)
    return out


def plot_temperature_vs_traffic(df: pd.DataFrame, output_dir: Path) -> Path:
    logger.info('Generating temperature versus traffic scatter plot.')
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.scatter(df['temp'], df['traffic_volume'], s=12, alpha=0.4, c='seagreen')
    ax.set_title('Temperature vs Traffic Volume')
    ax.set_xlabel('Temperature (K)')
    ax.set_ylabel('Traffic Volume')
    ax.grid(True, linestyle='--', alpha=0.3)
    out = output_dir / 'temperature_vs_traffic.png'
    save_figure(fig, out)
    return out


def create_all_visuals(df: pd.DataFrame, output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    plots = [
        plot_hourly_average_traffic(df, output_dir),
        plot_weather_average_traffic(df, output_dir),
        plot_weekday_weekend_comparison(df, output_dir),
        plot_temperature_vs_traffic(df, output_dir),
    ]
    logger.info('All Part 2 visualisations saved to %s', display_path(output_dir))
    return plots
