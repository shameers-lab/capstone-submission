import argparse
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from ..feature_utils import create_targets, load_processed_data

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PART3_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATA = PROJECT_ROOT / "part2_python" / "data" / "processed" / "traffic_features.csv"


def numeric_psi(reference: pd.Series, current: pd.Series) -> float:
    reference = pd.to_numeric(reference, errors="coerce").dropna().to_numpy(dtype=float)
    current = pd.to_numeric(current, errors="coerce").dropna().to_numpy(dtype=float)
    if reference.size == 0 or current.size == 0:
        raise ValueError("Cannot calculate drift for an empty numeric sample.")
    edges = np.unique(np.quantile(reference, np.linspace(0, 1, 11)))
    if len(edges) < 3:
        edges = np.linspace(float(reference.min()), float(reference.max()) + 1.0, 3)
    edges[0] = -np.inf
    edges[-1] = np.inf
    reference_counts = np.histogram(reference, bins=edges)[0].astype(float)
    current_counts = np.histogram(current, bins=edges)[0].astype(float)
    reference_share = (reference_counts + 1e-6) / (reference_counts.sum() + 1e-6 * len(edges[:-1]))
    current_share = (current_counts + 1e-6) / (current_counts.sum() + 1e-6 * len(edges[:-1]))
    return float(np.sum((current_share - reference_share) * np.log(current_share / reference_share)))


def categorical_psi(reference: pd.Series, current: pd.Series) -> float:
    reference = reference.fillna("Unknown").astype(str)
    current = current.fillna("Unknown").astype(str)
    categories = sorted(set(reference) | set(current))
    reference_share = np.array([(reference == value).mean() for value in categories])
    current_share = np.array([(current == value).mean() for value in categories])
    reference_share = np.clip(reference_share, 1e-6, None)
    current_share = np.clip(current_share, 1e-6, None)
    return float(np.sum((current_share - reference_share) * np.log(current_share / reference_share)))


def run_drift_check(data_path: Path, threshold: float = 0.2) -> dict[str, object]:
    data = load_processed_data(data_path)
    split_index = int(len(data) * 0.8)
    reference = data.iloc[:split_index]
    current = data.iloc[split_index:]
    if reference.empty or current.empty:
        raise ValueError("Chronological reference/current split produced an empty sample.")
    numeric_features = ["temp", "rain_1h", "snow_1h", "clouds_all"]
    numeric_features = [name for name in numeric_features if name in data.columns]
    scores = {
        name: numeric_psi(reference[name], current[name]) for name in numeric_features
    }
    reference_hour = reference["date_time"].dt.hour.astype(str)
    current_hour = current["date_time"].dt.hour.astype(str)
    scores["hour"] = categorical_psi(reference_hour, current_hour)
    scores["weather_main"] = categorical_psi(reference["weather_main"], current["weather_main"])
    targets, thresholds = create_targets(reference)
    later_targets, _ = create_targets(
        current,
        (thresholds["q1"], thresholds["q2"], thresholds["q3"]),
    )
    reference_prevalence = float(targets["proxy_accident_risk"].mean())
    current_prevalence = float(later_targets["proxy_accident_risk"].mean())
    prevalence_ratio = (
        float(current_prevalence / reference_prevalence) if reference_prevalence > 0 else None
    )
    concerning = {name: score for name, score in scores.items() if score >= threshold}
    status = "ALERT / Requires investigation" if concerning else "PASS / Normal"
    if concerning:
        logger.warning(
            "Drift alert: %s feature(s) exceeded PSI threshold %.2f: %s",
            len(concerning),
            threshold,
            concerning,
        )
    else:
        logger.info("No monitored feature exceeded PSI threshold %.2f.", threshold)
    return {
        "status": status,
        "method": "Simulated chronological feature-distribution monitoring using population stability index (PSI).",
        "threshold": threshold,
        "reference_rows": int(len(reference)),
        "current_rows": int(len(current)),
        "reference_date_range": [str(reference["date_time"].min()), str(reference["date_time"].max())],
        "current_date_range": [str(current["date_time"].min()), str(current["date_time"].max())],
        "feature_psi": scores,
        "concerning_features": concerning,
        "proxy_label_prevalence": {
            "reference_period": reference_prevalence,
            "current_period": current_prevalence,
            "ratio_current_to_reference": prevalence_ratio,
        },
        "thresholds_used_for_proxy_label": thresholds,
        "interpretation": (
            "This is a retrospective simulation, not production monitoring. A drift alert requests review; "
            "it does not establish model failure or a change in real accident risk."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate chronological feature drift monitoring.")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--threshold", type=float, default=0.2)
    parser.add_argument(
        "--output",
        type=Path,
        default=PART3_DIR / "monitoring" / "drift_report.json",
    )
    args = parser.parse_args()
    if not 0 < args.threshold:
        parser.error("--threshold must be greater than zero.")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    result = run_drift_check(args.data, args.threshold)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    logger.info("Wrote drift simulation report to %s.", args.output)


if __name__ == "__main__":
    main()
