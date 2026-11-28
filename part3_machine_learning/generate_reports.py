import argparse
import json
import logging
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Table,
    TableStyle,
)

from .feature_utils import load_processed_data

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PART3_DIR = Path(__file__).resolve().parent
DEFAULT_DATA = PROJECT_ROOT / "part2_python" / "data" / "processed" / "traffic_features.csv"


def load_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise FileNotFoundError(f"Required report input is missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def fmt(value: object, digits: int = 3) -> str:
    if value is None:
        return "not available"
    if isinstance(value, float) and not np.isfinite(value):
        return "not available"
    if isinstance(value, (int, np.integer)):
        return f"{int(value):,}"
    if isinstance(value, (float, np.floating)):
        return f"{float(value):,.{digits}f}"
    return str(value)


def part1_evidence(data_path: Path) -> dict[str, object]:
    data = load_processed_data(data_path)
    volume = data["traffic_volume"]
    congestion = volume > 5500
    clear = data["weather_main"].str.casefold().eq("clear")
    cloudy = data["weather_main"].str.casefold().eq("clouds")
    high_temperature = data["temp"] > 292
    clear_congested = int((clear & congestion).sum())
    clear_not_congested = int((clear & ~congestion).sum())
    cloudy_congested = int((cloudy & congestion).sum())
    cloudy_not_congested = int((cloudy & ~congestion).sum())
    odds_table = [
        clear_congested,
        clear_not_congested,
        cloudy_congested,
        cloudy_not_congested,
    ]
    corrected_odds = any(count == 0 for count in odds_table)
    odds_counts = [count + 0.5 for count in odds_table] if corrected_odds else odds_table
    clear_cong, clear_no_cong, cloudy_cong, cloudy_no_cong = odds_counts
    odds_ratio = float((clear_cong * cloudy_no_cong) / (clear_no_cong * cloudy_cong))
    probability = {
        "p_congestion": float(congestion.mean()),
        "p_clear": float(clear.mean()),
        "p_joint": float((clear & congestion).mean()),
        "p_clear_given_congestion": (
            float((clear & congestion).sum() / congestion.sum()) if congestion.sum() else None
        ),
        "p_high_temperature_given_congestion": (
            float((high_temperature & congestion).sum() / congestion.sum()) if congestion.sum() else None
        ),
        "independence_product": float(clear.mean() * congestion.mean()),
        "independence_difference": float((clear & congestion).mean() - clear.mean() * congestion.mean()),
        "odds_ratio_clear_vs_clouds": odds_ratio,
        "odds_ratio_cells": {
            "clear_congested": clear_congested,
            "clear_not_congested": clear_not_congested,
            "clouds_congested": cloudy_congested,
            "clouds_not_congested": cloudy_not_congested,
            "haldane_anscombe_correction_used": corrected_odds,
        },
    }
    holiday_temperatures: dict[str, float | None] = {}
    timestamps = data["date_time"]
    for year in (2015, 2016, 2017):
        labor_day = date(year, 9, 1)
        labor_day = date(year, 9, 1 + (0 - labor_day.weekday()) % 7)
        for label, month, day in [
            ("New Year's Day", 1, 1),
            ("Labor Day", labor_day.month, labor_day.day),
        ]:
            mask = timestamps.dt.date.eq(date(year, month, day))
            matching = data.loc[mask, "temp"]
            holiday_temperatures[f"{label} {year}"] = (
                float(matching.mean()) if not matching.empty else None
            )
    annual_totals = {
        str(year): int(group["traffic_volume"].sum())
        for year, group in data.assign(year=timestamps.dt.year)
        .groupby("year", observed=True)
        if 2012 <= year <= 2017
    }
    annual_change = {}
    prior = None
    for year, total in annual_totals.items():
        annual_change[year] = (
            float((total - prior) / prior * 100) if prior else None
        )
        prior = total
    with_year = data.assign(
        year=timestamps.dt.year,
        date=timestamps.dt.date,
        hour=timestamps.dt.hour,
    )
    daily_average_by_year = (
        with_year.groupby(["year", "date"], observed=True)["traffic_volume"]
        .mean()
        .groupby(level="year")
        .mean()
    )
    hourly_2017 = with_year.loc[with_year["year"].eq(2017)].groupby("hour")[
        "traffic_volume"
    ].mean()
    weather_average = data.groupby("weather_main", observed=True)["traffic_volume"].agg(
        ["mean", "size"]
    )
    high_traffic = data.loc[
        data["traffic_volume"].ge(data["traffic_volume"].quantile(0.75))
        & data["temp"].gt(0),
        "temp",
    ]
    stats = {
        "rows": int(len(data)),
        "mean": float(volume.mean()),
        "median": float(volume.median()),
        "std_sample": float(volume.std(ddof=1)),
        "variance_sample": float(volume.var(ddof=1)),
        "minimum": float(volume.min()),
        "maximum": float(volume.max()),
        "temperature_correlation": float(data["temp"].corr(data["traffic_volume"])),
        "annual_totals": annual_totals,
        "annual_yoy_percent": annual_change,
        "dashboard_patterns": {
            "daily_average_by_year": {
                str(year): float(value)
                for year, value in daily_average_by_year.items()
                if 2015 <= year <= 2017
            },
            "2017_peak_hour": int(hourly_2017.idxmax()),
            "2017_peak_hour_mean": float(hourly_2017.max()),
            "2017_low_hour": int(hourly_2017.idxmin()),
            "2017_low_hour_mean": float(hourly_2017.min()),
            "weather_highest": str(weather_average["mean"].idxmax()),
            "weather_highest_mean": float(weather_average["mean"].max()),
            "weather_highest_n": int(weather_average.loc[weather_average["mean"].idxmax(), "size"]),
            "weather_lowest": str(weather_average["mean"].idxmin()),
            "weather_lowest_mean": float(weather_average["mean"].min()),
            "weather_lowest_n": int(weather_average.loc[weather_average["mean"].idxmin(), "size"]),
            "top_traffic_temp_min_c": float(high_traffic.min() - 273.15),
            "top_traffic_temp_max_c": float(high_traffic.max() - 273.15),
        },
        "probabilities": probability,
        "holiday_mean_temperature_k": holiday_temperatures,
        "weekend_means": {
            str(key): float(value)
            for key, value in data.assign(
                day_type=np.where(data["date_time"].dt.dayofweek >= 5, "Weekend", "Weekday")
            ).groupby("day_type", observed=True)["traffic_volume"].mean().items()
        },
    }
    return stats


def paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(text), style)


def build_pdf(path: Path, title: str, story: list[object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        rightMargin=19 * mm,
        leftMargin=19 * mm,
        topMargin=17 * mm,
        bottomMargin=17 * mm,
        title=title,
        author="Smart City Traffic Intelligence Capstone",
    )
    document.build(story)
    logger.info("Generated report PDF at %s.", path)


def table(rows: list[list[str]], widths: list[float] | None = None) -> Table:
    result = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
    result.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#18324A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("LEADING", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B7C7D3")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#EFF4F7")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return result


def responsible_ai_story(metrics: dict[str, object], styles: dict[str, ParagraphStyle]) -> list[object]:
    label = metrics["proxy_label"]
    split = metrics["split"]
    fairness = metrics["group_error_analysis"]
    classification = metrics["classification"]
    invalid_weather = metrics["dataset"]["part3_impossible_weather_values_set_missing"]
    stories: list[object] = [
        paragraph("Responsible AI, Bias and Fairness Report", styles["TitleCenter"]),
        paragraph("Smart City Traffic Intelligence: proxy-label model governance", styles["Subtitle"]),
        paragraph(
            "Critical limitation: the available data has no accident outcome. "
            "The classification target is a proxy defined as traffic above the training-set median "
            "and either a selected severe-weather category or cloud cover of at least 80/100. "
            "Predictions are not real accident likelihood and must not drive real-world safety decisions.",
            styles["Body"],
        ),
        paragraph("Data coverage and sampling", styles["Heading1"]),
        paragraph(
            f"The modeling input is the committed Part 2 processed table ({fmt(metrics['dataset']['rows'])} rows; "
            f"{metrics['dataset']['date_start']} through {metrics['dataset']['date_end']}). "
            "The original raw CSV was absent from the checkout; Part 3 therefore consumes the processed "
            "artifact, whose Part 2 README records UCI Metro Interstate provenance and cleaning counts. "
            "Raw-to-processed cleaning could not be independently rerun in this stage. The data describes "
            "one corridor and historical hourly observations, not the full city, individual journeys, incidents, "
            "or a representative sample of all road users.",
            styles["Body"],
        ),
        paragraph(
            "Part 2 and Part 3 now use consistent physical checks for temperature (150-400 K), rain/snow "
            "(0-500 mm/hour), and cloud cover (0-100). The prior tracked Part 2 input contained a 9,831.3 "
            "mm/hour rainfall value; Part 2 flags and median-imputes it while retaining its observation. "
            f"Part 3 independently revalidated the current input and found "
            f"{fmt(invalid_weather.get('rain_1h', 0))} remaining invalid rainfall value(s); any remaining "
            "missing weather values are imputed within the training pipeline. No traffic-volume outlier was removed.",
            styles["Body"],
        ),
        paragraph("Proxy label, validity and leakage risk", styles["Heading1"]),
        paragraph(
            f"Training-derived traffic thresholds are Q1={fmt(label['training_congestion_thresholds']['q1'], 1)}, "
            f"Q2={fmt(label['training_congestion_thresholds']['q2'], 1)}, and "
            f"Q3={fmt(label['training_congestion_thresholds']['q3'], 1)} vehicles/hour. "
            f"Selected severe-weather values are {', '.join(label['severe_weather_categories'])}; "
            f"low visibility is {label['low_visibility_definition']}. The label has "
            f"{fmt(label['train_positive_count'])} positive training samples ({fmt(label['train_positive_rate'] * 100, 2)}%) "
            f"and {fmt(label['test_positive_count'])} positive holdout samples "
            f"({fmt(label['test_positive_rate'] * 100, 2)}%).",
            styles["Body"],
        ),
        paragraph(
            "Current traffic volume, congestion categories and the proxy target are excluded from predictors. "
            "Nevertheless, severe-weather categories and visibility inputs are direct ingredients of the label, "
            "while traffic-related weather/time patterns are correlated with its congestion ingredient. This is "
            "residual definitional leakage and can make scores appear stronger than any genuine safety signal. "
            "The time/holiday-only ablation provides a partial sensitivity check; it does not eliminate the "
            "target-validity problem.",
            styles["Body"],
        ),
        paragraph("Time validation, imbalance and model errors", styles["Heading1"]),
        paragraph(
            f"Evaluation uses an ordered 80/20 chronological split: training through {split['train_end']} "
            f"and holdout from {split['test_start']} to {split['test_end']}. Scaling/one-hot encoding "
            "are fitted inside training pipelines. Classification uses a fixed 0.5 probability threshold and "
            "class weighting; metrics are compared with the training-majority baseline. Results evaluate the "
            "constructed proxy only, not accident prediction.",
            styles["Body"],
        ),
    ]
    best_name = metrics["selected_models"]["proxy_classifier"]
    best_scores = classification[best_name]
    stories.append(
        paragraph(
            f"Selected classifier ({best_name}) holdout scores: accuracy {fmt(best_scores['accuracy'])}, "
            f"precision {fmt(best_scores['precision'])}, recall {fmt(best_scores['recall'])}, "
            f"F1 {fmt(best_scores['f1'])}, and ROC AUC {fmt(best_scores['roc_auc'])}. "
            f"Training-majority accuracy baseline is {fmt(metrics['baselines']['majority_class_accuracy'])}.",
            styles["Body"],
        )
    )
    ablation = metrics["classification_ablation_without_weather_features"]
    stories.append(
        paragraph(
            f"The logistic time/holiday-only ablation, excluding direct weather inputs, yielded "
            f"accuracy {fmt(ablation['accuracy'])}, precision {fmt(ablation['precision'])}, recall "
            f"{fmt(ablation['recall'])}, F1 {fmt(ablation['f1'])}, and ROC AUC {fmt(ablation['roc_auc'])}. "
            "The comparison quantifies sensitivity to weather inputs but should not be read as causal evidence.",
            styles["Body"],
        )
    )
    group_rows = [["Holdout group", "n", "Proxy prevalence", "Precision", "Recall", "Traffic MAE"]]
    for group_column, groups in fairness.items():
        for name, values in groups.items():
            group_rows.append(
                [
                    f"{group_column}: {name}",
                    fmt(values["n"]),
                    fmt(values["proxy_prevalence"], 3),
                    fmt(values["proxy_precision"], 3),
                    fmt(values["proxy_recall"], 3),
                    fmt(values["traffic_mae"], 1),
                ]
            )
    stories.extend(
        [
            paragraph("Observed error differences", styles["Heading1"]),
            paragraph(
                "The following holdout summaries are descriptive and only include groups with at least 30 "
                "records. Differences may reflect unequal sample composition and proxy-label construction; "
                "they are not evidence of fairness or unfairness toward protected groups, which are not present "
                "in the dataset.",
                styles["Body"],
            ),
            table(group_rows, [42 * mm, 13 * mm, 26 * mm, 22 * mm, 20 * mm, 25 * mm]),
            paragraph("Governance and human oversight", styles["Heading1"]),
            paragraph(
                "This is a research prototype for historical analysis and single-corridor timing advice. "
                "Do not use the proxy score to trigger enforcement, emergency response, road closures, driver "
                "alerts, or safety interventions. Before any operational consideration, obtain verified incident "
                "labels with lawful provenance, conduct a privacy/legal review, establish data-quality and "
                "subgroup audit procedures, independently validate against a time-forward deployment sample, "
                "calibrate thresholds with accountable transport and safety stakeholders, document a human "
                "override and appeal path, and monitor failures with a rollback owner.",
                styles["Body"],
            ),
            paragraph("Environmental and resource trade-offs", styles["Heading1"]),
            paragraph(
                "The experiments use CPU-oriented scikit-learn models, a small multilayer perceptron, and a "
                "single four-cluster analysis on tens of thousands of rows; no GPU or large foundation model is "
                "required. Training and local MLflow artifact storage still consume compute and disk. Re-run only "
                "when data or methodology changes, retain the compact selected artifacts, and avoid continuous "
                "retraining without measured benefit.",
                styles["Body"],
            ),
            paragraph("Monitoring simulation", styles["Heading1"]),
            paragraph(
                "The monitoring artifact compares the earlier training period with the later holdout period using "
                "population stability index (PSI). Its PASS/ALERT result is a retrospective drift simulation, "
                "not a production service or evidence of accident-risk change. An alert requests investigation, "
                "not automatic retraining or operational action.",
                styles["Body"],
            ),
        ]
    )
    return stories


def final_report_story(
    metrics: dict[str, object],
    recommendations: dict[str, object],
    drift: dict[str, object],
    part1: dict[str, object],
    styles: dict[str, ParagraphStyle],
) -> list[object]:
    annual_rows = [["Year", "Total hourly traffic volume", "YoY change"]]
    annual_rows.extend(
        [
            [
                year,
                fmt(total),
                "—" if part1["annual_yoy_percent"][year] is None
                else f"{fmt(part1['annual_yoy_percent'][year], 2)}%",
            ]
            for year, total in part1["annual_totals"].items()
        ]
    )
    classification_rows = [["Proxy classification model", "Accuracy", "Precision", "Recall", "F1", "ROC AUC"]]
    for name, values in metrics["classification"].items():
        classification_rows.append(
            [name, fmt(values["accuracy"]), fmt(values["precision"]), fmt(values["recall"]), fmt(values["f1"]), fmt(values["roc_auc"])]
        )
    regression_rows = [["Traffic regression model", "MAE (vehicles/hour)", "R-squared"]]
    for name, values in metrics["regression"].items():
        regression_rows.append([name, fmt(values["mae"], 1), fmt(values["r_squared"], 3)])
    top_rules = load_json(PART3_DIR / "models" / "association_rules_summary.json")
    cluster = load_json(PART3_DIR / "models" / "unsupervised_summary.json")
    cluster_profiles = pd.read_csv(PART3_DIR / "models" / "cluster_profiles.csv")
    story: list[object] = [
        paragraph("Final Capstone Report", styles["TitleCenter"]),
        paragraph("Smart City Traffic Intelligence: From Data Analytics to AI-Powered Mobility", styles["Subtitle"]),
        paragraph(
            "This project analyzes historical hourly traffic on the Metro Interstate corridor, builds a "
            "reproducible Part 2 pipeline, and demonstrates machine-learning and operational-analysis methods "
            "without claiming real accident prediction or citywide generalization.",
            styles["Body"],
        ),
        paragraph("Data and scope", styles["Heading1"]),
        paragraph(
            f"Part 3 used the tracked Part 2 processed artifact with {fmt(metrics['dataset']['rows'])} rows and "
            f"{fmt(metrics['dataset']['columns'])} columns, dated {metrics['dataset']['date_start']} through "
            f"{metrics['dataset']['date_end']}. Its README attributes the dataset to the UCI Metro Interstate "
            "Traffic Volume data; the raw CSV was not available in this checkout, so its original cleaning and "
            "schema validation were not independently rerun. Traffic is vehicles per hour; temperature is Kelvin; "
            "cloud cover is the source 0–100 scale.",
            styles["Body"],
        ),
        paragraph("Part 1 — analytics", styles["Heading1"]),
        paragraph(
            f"Recomputed from the available processed table: mean hourly traffic {fmt(part1['mean'], 2)}, "
            f"median {fmt(part1['median'], 2)}, sample standard deviation {fmt(part1['std_sample'], 2)}, "
            f"sample variance {fmt(part1['variance_sample'], 2)}, range {fmt(part1['minimum'])}–"
            f"{fmt(part1['maximum'])}, and temperature/traffic Pearson correlation "
            f"{fmt(part1['temperature_correlation'], 4)}. Correlation is descriptive and does not establish "
            "causality. Annual totals for the requested period are shown below.",
            styles["Body"],
        ),
        table(annual_rows, [25 * mm, 70 * mm, 35 * mm]),
        paragraph(
            "For the required probability exercise, congestion is traffic volume above 5,500 vehicles/hour, "
            "clear weather is weather_main=Clear, cloudy is weather_main=Clouds, and high temperature is above "
            "292 K. On this processed table: "
            f"P(congestion)={fmt(part1['probabilities']['p_congestion'], 4)}, "
            f"P(clear)={fmt(part1['probabilities']['p_clear'], 4)}, "
            f"P(clear and congestion)={fmt(part1['probabilities']['p_joint'], 4)}, "
            f"P(clear|congestion)={fmt(part1['probabilities']['p_clear_given_congestion'], 4)}, and "
            f"P(temp>292 K|congestion)={fmt(part1['probabilities']['p_high_temperature_given_congestion'], 4)}. "
            f"The joint-minus-product difference is {fmt(part1['probabilities']['independence_difference'], 5)}. "
            f"The clear-versus-clouds congestion odds ratio is "
            f"{fmt(part1['probabilities']['odds_ratio_clear_vs_clouds'], 4)}; when any cell is zero, a "
            "0.5 Haldane–Anscombe correction is applied to all four cells. A nonzero joint-minus-product "
            "difference indicates departure from independence; odds ratios below/above one indicate lower/higher "
            "sample congestion odds for Clear than Clouds, not a causal weather effect.",
            styles["Body"],
        ),
        paragraph(
            "Mean temperature on New Year’s Day and Labor Day, as available in the processed observations, "
            "is shown in Kelvin:",
            styles["Body"],
        ),
        table(
            [["Date", "Mean temperature (K)"]]
            + [
                [label, fmt(value, 2)]
                for label, value in part1["holiday_mean_temperature_k"].items()
            ],
            [75 * mm, 45 * mm],
        ),
        paragraph(
            "Temperature differences can be relevant context for mobility planning, but a small set of holiday "
            "dates does not establish that temperature caused traffic changes; traffic also depends on time, "
            "day type, weather, and unobserved events.",
            styles["Body"],
        ),
        paragraph(
            "These annual, probability, holiday, summary-statistic, and correlation calculations are descriptive. "
            "The local Part 1 report also discusses commuter-period and weather associations; none establish "
            "causal effects.",
            styles["Body"],
        ),
        paragraph(
            "Part 1 includes SQL/statistics artifacts and Power Query/dashboard preparation. Association-rule "
            "support is the share of all observations containing both antecedent and high/severe congestion; "
            "confidence is the share of antecedent observations with high/severe congestion; lift compares that "
            "confidence with the overall high/severe congestion rate. The Power BI .pbix and prepared "
            "query/data files are included, and the project owner manually validated the interactive dashboard.",
            styles["Body"],
        ),
        paragraph("Part 1 dashboard evidence", styles["Heading1"]),
        paragraph(
            "On the shared processed observations, the mean of daily traffic averages was "
            + ", ".join(
                f"{year}: {fmt(value, 1)} vehicles/hour"
                for year, value in part1["dashboard_patterns"]["daily_average_by_year"].items()
            )
            + f". The 2017 hourly mean peaked at {part1['dashboard_patterns']['2017_peak_hour']:02d}:00 "
            f"({fmt(part1['dashboard_patterns']['2017_peak_hour_mean'], 1)}) and was lowest at "
            f"{part1['dashboard_patterns']['2017_low_hour']:02d}:00 "
            f"({fmt(part1['dashboard_patterns']['2017_low_hour_mean'], 1)}). "
            f"Weather averages ranged from {part1['dashboard_patterns']['weather_lowest']} "
            f"({fmt(part1['dashboard_patterns']['weather_lowest_mean'], 1)}; "
            f"n={fmt(part1['dashboard_patterns']['weather_lowest_n'])}) to "
            f"{part1['dashboard_patterns']['weather_highest']} "
            f"({fmt(part1['dashboard_patterns']['weather_highest_mean'], 1)}; "
            f"n={fmt(part1['dashboard_patterns']['weather_highest_n'])}). "
            f"The top traffic quartile spans "
            f"{fmt(part1['dashboard_patterns']['top_traffic_temp_min_c'], 1)}-"
            f"{fmt(part1['dashboard_patterns']['top_traffic_temp_max_c'], 1)} C among valid "
            "temperature readings. Weather-category group sizes vary, and the extremes are "
            "descriptive rather than causal.",
            styles["Body"],
        ),
        paragraph("Part 2 — pipeline and analytics", styles["Heading1"]),
        paragraph(
            "Part 2 documents CSV validation, duplicate handling, month-specific numeric imputation, feature "
            "engineering, and visual outputs. Its logged run reports 48,204 raw observations, 17 duplicate rows "
            "removed, and 48,187 output rows. The raw source is not committed here, so those raw-input counts "
            "are reported from the stored log/README and were not regenerated for this report. Engineered "
            "features include time cycles, weather indicators, scaled descriptive variables, and a quartile "
            "congestion category. Part 2 also includes four Matplotlib figures and CLI examples for timestamp, "
            "threshold, day-type, and weather queries. Its recorded weekday/weekend averages are "
            f"{fmt(part1['weekend_means'].get('Weekday'), 2)} and "
            f"{fmt(part1['weekend_means'].get('Weekend'), 2)} vehicles/hour respectively, recomputed here "
            "from the available processed table.",
            styles["Body"],
        ),
        paragraph(
            "Part 2 and Part 3 use the same physical measurement bounds. The prior tracked Part 2 input's "
            "9,831.3 mm/hour rainfall value is now flagged and median-imputed before feature generation while "
            "retaining the observation; Part 3 independently rechecks the current data and reports its own "
            f"invalid-weather counts ({fmt(metrics['dataset']['part3_impossible_weather_values_set_missing'])}). "
            "The processed table includes repeated timestamps, which Part 3 preserves as separate observations; "
            "duplicate timestamps are not automatically duplicate records.",
            styles["Body"],
        ),
        paragraph("Part 3 — models and evaluation", styles["Heading1"]),
        paragraph(
            f"Chronological training/holdout sizes were {fmt(metrics['split']['train_rows'])}/"
            f"{fmt(metrics['split']['test_rows'])}; training ends {metrics['split']['train_end']} and holdout "
            f"begins {metrics['split']['test_start']}. Preprocessing was fitted in training pipelines. "
            "Classification estimates the explicitly defined congestion/weather proxy; current traffic, "
            "congestion label, and target fields were excluded as predictors. Because weather and congestion "
            "ingredients overlap with proxy-label inputs, residual definitional leakage remains.",
            styles["Body"],
        ),
        table(classification_rows, [40 * mm, 22 * mm, 22 * mm, 18 * mm, 15 * mm, 21 * mm]),
        table(regression_rows, [55 * mm, 43 * mm, 35 * mm]),
        paragraph(
            f"The majority-class test accuracy baseline is {fmt(metrics['baselines']['majority_class_accuracy'])}; "
            f"the training-median traffic baseline MAE is {fmt(metrics['baselines']['median_training_traffic_mae'], 1)} "
            "vehicles/hour. Positive-class imbalance, fixed 0.5 threshold, group errors, and a weather-feature "
            "ablation are recorded in models/metrics.json and the responsible-AI report.",
            styles["Body"],
        ),
        paragraph("Unsupervised analysis, rules and explanation", styles["Heading1"]),
        paragraph(
            f"K-means was applied to scaled traffic/weather/time conditions (not accident records), with "
            f"{fmt(cluster['n_clusters'])} clusters and sample silhouette {fmt(cluster['silhouette_score'], 4)}. "
            "The cluster profiles are descriptive traffic regimes, not accident types:",
            styles["Body"],
        ),
        table(
            [["Cluster", "Rows", "Mean traffic", "Plain-language interpretation"]]
            + [
                [
                    fmt(row["cluster"]),
                    fmt(row["observations"]),
                    fmt(row["mean_traffic"], 1),
                    str(row["plain_language_interpretation"]),
                ]
                for _, row in cluster_profiles.iterrows()
            ],
            [15 * mm, 18 * mm, 27 * mm, 105 * mm],
        ),
        paragraph(
            "Association-rule metrics are in association_rules.csv; the strongest qualifying rules are:",
            styles["Body"],
        ),
        table(
            [["Condition", "Support", "Confidence", "Lift"]]
            + [
                [str(item["antecedent"]), fmt(item["support"], 3), fmt(item["confidence"], 3), fmt(item["lift"], 3)]
                for item in top_rules[:5]
            ],
            [76 * mm, 24 * mm, 28 * mm, 20 * mm],
        ),
        paragraph(
            "A compact multilayer perceptron was trained as an additional proxy classifier and explained with "
            "one LIME local surrogate example. This explanation is local, approximate, and not causal; see "
            "models/lime_explanation.json.",
            styles["Body"],
        ),
        paragraph("Recommendations and MLOps simulation", styles["Heading1"]),
        paragraph(
            "The timing recommender ranks historically lower-traffic hourly windows separately for weekdays and "
            "weekends, with a minimum sample requirement, and optionally stratifies by weather. It covers this "
            "single observed corridor only; it is not route selection and not real-time guidance. Local FastAPI "
            "deployment exposes a mock proxy classification endpoint. MLflow tracks experiments, metrics, "
            f"artifacts, and registered model versions "
            f"{metrics['selected_models']['mlflow_model_versions']}. The retrospective drift simulation reports "
            f"{drift['status']} using PSI threshold {fmt(drift['threshold'])}; this status is not a "
            "production monitoring result.",
            styles["Body"],
        ),
        paragraph(
            "Historical lower-volume timing candidates: "
            + " ".join(recommendations.get("plain_language_recommendations", [])),
            styles["Body"],
        ),
        paragraph("Limitations and responsible use", styles["Heading1"]),
        paragraph(
            "The data is a single-corridor historical sample with no accident labels, limited contextual "
            "variables, and no demographic or incident coverage. The proxy label is a design exercise and does "
            "not represent actual accident likelihood. No score or recommendation should inform safety-critical "
            "decisions. Deployment would require genuine incident data, lawful governance, independent "
            "time-forward validation, stakeholder review, subgroup/error monitoring, a human override, and "
            "operational rollback procedures. Small CPU-based models limit compute use but still incur training "
            "and artifact-storage costs.",
            styles["Body"],
        ),
    ]
    return story


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the required capstone PDF reports.")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    metrics = load_json(PART3_DIR / "models" / "metrics.json")
    recommendations = load_json(
        PART3_DIR / "recommendation_system" / "recommendations.json"
    )
    drift = load_json(PART3_DIR / "monitoring" / "drift_report.json")
    part1 = part1_evidence(args.data)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TitleCenter", parent=styles["Title"], alignment=TA_CENTER, fontSize=20, leading=24))
    styles.add(ParagraphStyle(name="Subtitle", parent=styles["Normal"], alignment=TA_CENTER, fontSize=10, leading=14, spaceAfter=12))
    styles.add(ParagraphStyle(name="Body", parent=styles["BodyText"], fontSize=9, leading=12, spaceAfter=7))
    styles["Heading1"].fontSize = 13
    styles["Heading1"].leading = 16
    styles["Heading1"].spaceBefore = 8
    styles["Heading1"].spaceAfter = 4

    rai_story = responsible_ai_story(metrics, styles)
    rai_path = PART3_DIR / "responsible_ai_report.pdf"
    build_pdf(rai_path, "Responsible AI, Bias and Fairness Report", rai_story)

    final_story = final_report_story(metrics, recommendations, drift, part1, styles)
    final_path = PROJECT_ROOT / "final_capstone_report.pdf"
    build_pdf(final_path, "Smart City Traffic Intelligence Final Capstone Report", final_story)
    logger.info("Report generation completed.")


if __name__ == "__main__":
    main()
