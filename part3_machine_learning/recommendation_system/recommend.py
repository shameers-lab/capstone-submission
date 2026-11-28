import argparse
import json
import logging
from pathlib import Path

import pandas as pd

from ..feature_utils import load_processed_data

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA = PROJECT_ROOT / "part2_python" / "data" / "processed" / "traffic_features.csv"


def build_recommendations(data_path: Path) -> dict[str, object]:
    data = load_processed_data(data_path)
    data["hour"] = data["date_time"].dt.hour
    data["day_type"] = data["date_time"].dt.dayofweek.map(
        lambda value: "Weekend" if value >= 5 else "Weekday"
    )
    hour_summary = (
        data.groupby(["day_type", "hour"], observed=True)
        .agg(
            observations=("traffic_volume", "size"),
            mean_traffic=("traffic_volume", "mean"),
            median_traffic=("traffic_volume", "median"),
        )
        .reset_index()
    )
    recommendations: list[dict[str, object]] = []
    for day_type in ["Weekday", "Weekend"]:
        subset = hour_summary[
            (hour_summary["day_type"] == day_type) & (hour_summary["observations"] >= 100)
        ].sort_values(["mean_traffic", "hour"])
        if subset.empty:
            logger.warning("No hourly window meets the minimum sample size for %s.", day_type)
            continue
        for row in subset.head(3).itertuples(index=False):
            recommendations.append(
                {
                    "day_type": row.day_type,
                    "hour": int(row.hour),
                    "local_time_window": f"{int(row.hour):02d}:00-{(int(row.hour) + 1) % 24:02d}:00",
                    "historical_mean_traffic_vehicles_per_hour": round(float(row.mean_traffic), 2),
                    "historical_median_traffic_vehicles_per_hour": round(float(row.median_traffic), 2),
                    "observations": int(row.observations),
                    "basis": "Lowest historical hourly averages within this day type, minimum 100 observations.",
                }
            )
    weather_summary = (
        data.groupby(["weather_main", "hour"], observed=True)
        .agg(observations=("traffic_volume", "size"), mean_traffic=("traffic_volume", "mean"))
        .reset_index()
    )
    weather_windows = []
    for condition, group in weather_summary.groupby("weather_main", observed=True):
        sufficiently_sampled = group[group["observations"] >= 100]
        if sufficiently_sampled.empty:
            continue
        row = sufficiently_sampled.sort_values(["mean_traffic", "hour"]).iloc[0]
        weather_windows.append(
            {
                "weather_main": str(condition),
                "hour": int(row["hour"]),
                "historical_mean_traffic_vehicles_per_hour": round(float(row["mean_traffic"]), 2),
                "observations": int(row["observations"]),
            }
        )
    result = {
        "dataset_rows": int(len(data)),
        "date_start": str(data["date_time"].min()),
        "date_end": str(data["date_time"].max()),
        "corridor_scope": "Single observed Metro Interstate traffic corridor; no route optimization.",
        "recommendations_by_day_type": recommendations,
        "plain_language_recommendations": [
            (
                f"On {item['day_type'].lower()}s, consider the historical lower-volume window "
                f"{item['local_time_window']} (mean "
                f"{item['historical_mean_traffic_vehicles_per_hour']:.2f} vehicles/hour across "
                f"{item['observations']} observations); verify current conditions first."
            )
            for item in recommendations
        ],
        "lowest_sampled_hour_by_weather": weather_windows,
        "caution": (
            "Historical associations only; traffic is not guaranteed to be low in future. "
            "Recommendations are not safety guidance and do not account for incidents, events, "
            "road works, or live conditions."
        ),
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize lower-traffic windows for the observed corridor.")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "recommendations.json",
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    result = build_recommendations(args.data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    logger.info("Wrote historical timing recommendations to %s.", args.output)


if __name__ == "__main__":
    main()
