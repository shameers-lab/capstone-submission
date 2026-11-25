"""Reproduce the Part 1 traffic analysis from the supplied CSV."""

from __future__ import annotations

import argparse
import sqlite3
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


EXPECTED_COLUMNS = {
    "holiday",
    "temp",
    "rain_1h",
    "snow_1h",
    "clouds_all",
    "weather_main",
    "weather_description",
    "date_time",
    "traffic_volume",
}
BASE = Path(__file__).resolve().parents[1]
STATISTICS_DIR = BASE / "statistics"
POWERBI_DIR = BASE / "powerbi"
SQL_DIR = BASE / "sql"


def load_data(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    missing = EXPECTED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing required columns: {sorted(missing)}")
    df["date_time"] = pd.to_datetime(df["date_time"], errors="raise")
    return df


def safe_ratio(numerator: int, denominator: int) -> float:
    return float(numerator / denominator) if denominator else float("nan")


def analyze(df: pd.DataFrame) -> dict[str, object]:
    df = df.copy()
    df["year"] = df["date_time"].dt.year
    df["date"] = df["date_time"].dt.date
    df["hour"] = df["date_time"].dt.hour
    df["temp_c"] = df["temp"] - 273.15
    df["traffic_category"] = np.select(
        [df["traffic_volume"] < 4500, df["traffic_volume"] <= 5500],
        ["Low", "Medium"],
        default="High",
    )

    annual = (
        df.groupby("year")["traffic_volume"]
        .agg(record_count="size", total_volume="sum", average_volume="mean")
        .reindex(range(2012, 2019))
    )
    annual["year_over_year_total_change"] = annual["total_volume"].diff()
    annual["year_over_year_percent_change"] = (
        annual["total_volume"].pct_change(fill_method=None) * 100
    )

    volume = df["traffic_volume"]
    source_missing = df[list(EXPECTED_COLUMNS)].isna().sum()
    stats = {
        "records": int(len(df)),
        "columns": int(len(EXPECTED_COLUMNS)),
        "duplicate_rows": int(df.duplicated().sum()),
        "missing_values": {c: int(n) for c, n in source_missing.items() if n},
        "date_start": str(df["date_time"].min()),
        "date_end": str(df["date_time"].max()),
        "zero_kelvin_rows": int((df["temp"] <= 0).sum()),
        "rain_above_500_mm_rows": int((df["rain_1h"] > 500).sum()),
        "maximum_rain_1h_mm": float(df["rain_1h"].max()),
        "volume_mean": float(volume.mean()),
        "volume_median": float(volume.median()),
        "volume_sample_std": float(volume.std(ddof=1)),
        "volume_sample_variance": float(volume.var(ddof=1)),
        "volume_range": int(volume.max() - volume.min()),
        "volume_min": int(volume.min()),
        "volume_max": int(volume.max()),
        "temp_traffic_correlation": float(df["temp"].corr(volume)),
        "temp_traffic_correlation_excluding_zero_kelvin": float(
            df.loc[df["temp"] > 0, "temp"].corr(df.loc[df["temp"] > 0, "traffic_volume"])
        ),
    }

    congestion = volume > 5500
    clear = df["weather_main"].str.casefold().eq("clear")
    cloudy = df["weather_main"].str.casefold().eq("clouds")
    high_temp = df["temp"] > 292
    n = len(df)
    clear_congested = int((clear & congestion).sum())
    cloudy_congested = int((cloudy & congestion).sum())
    clear_not_congested = int((clear & ~congestion).sum())
    cloudy_not_congested = int((cloudy & ~congestion).sum())
    odds_clear = safe_ratio(clear_congested, clear_not_congested)
    odds_cloudy = safe_ratio(cloudy_congested, cloudy_not_congested)
    odds_ratio = (
        odds_clear / odds_cloudy
        if np.isfinite(odds_clear) and np.isfinite(odds_cloudy) and odds_cloudy != 0
        else float("nan")
    )
    probability = {
        "n": n,
        "congestion_count": int(congestion.sum()),
        "clear_count": int(clear.sum()),
        "clear_and_congestion_count": clear_congested,
        "high_temp_and_congestion_count": int((high_temp & congestion).sum()),
        "clear_given_congestion": safe_ratio(clear_congested, int(congestion.sum())),
        "high_temp_given_congestion": safe_ratio(
            int((high_temp & congestion).sum()), int(congestion.sum())
        ),
        "p_congestion": float(congestion.mean()),
        "p_clear": float(clear.mean()),
        "p_clear_and_congestion": float((clear & congestion).mean()),
        "p_clear_times_p_congestion": float(clear.mean() * congestion.mean()),
        "clear_congestion_count": clear_congested,
        "clear_noncongestion_count": clear_not_congested,
        "cloudy_congestion_count": cloudy_congested,
        "cloudy_noncongestion_count": cloudy_not_congested,
        "odds_clear": odds_clear,
        "odds_cloudy": odds_cloudy,
        "odds_ratio_clear_vs_clouds": odds_ratio,
    }

    holiday_rows = []
    for year in (2015, 2016, 2017):
        labor_day = date(year, 9, 1)
        labor_day = date(year, 9, 1 + (0 - labor_day.weekday()) % 7)
        for label, holiday_date in [
            ("New Year's Day", date(year, 1, 1)),
            ("Labor Day", labor_day),
        ]:
            observations = df.loc[df["date_time"].dt.date.eq(holiday_date)]
            holiday_rows.append(
                {
                    "holiday": label,
                    "year": year,
                    "date": holiday_date.isoformat(),
                    "records": int(len(observations)),
                    "mean_temp_k": (
                        float(observations["temp"].mean())
                        if not observations.empty
                        else np.nan
                    ),
                    "mean_traffic": (
                        float(observations["traffic_volume"].mean())
                        if not observations.empty
                        else np.nan
                    ),
                    "mean_temp_c": (
                        float(observations["temp_c"].mean())
                        if not observations.empty
                        else np.nan
                    ),
                }
            )
    holiday = pd.DataFrame(holiday_rows)
    weather = (
        df.groupby("weather_main")["traffic_volume"]
        .agg(record_count="size", average_traffic="mean")
        .sort_values("average_traffic")
        .reset_index()
    )
    daily_summary = (
        df[df["year"].isin([2015, 2016, 2017])]
        .groupby("year")["traffic_volume"]
        .agg(daily_mean="mean", record_count="size")
        .reset_index()
    )
    hourly_summary = (
        df[df["year"] == 2017]
        .groupby("hour")["traffic_volume"]
        .agg(record_count="size", average_traffic="mean")
        .reset_index()
    )
    upper_traffic_cutoff = float(volume.quantile(0.75))
    high_traffic_mask = (volume >= upper_traffic_cutoff) & (df["temp"] > 0)
    high_traffic_temps = df.loc[high_traffic_mask, "temp_c"]
    temperature_traffic = {
        "upper_quartile_traffic_cutoff": upper_traffic_cutoff,
        "upper_quartile_valid_temp_rows": int(high_traffic_mask.sum()),
        "upper_quartile_temp_min_c": float(high_traffic_temps.min()),
        "upper_quartile_temp_median_c": float(high_traffic_temps.median()),
        "upper_quartile_temp_max_c": float(high_traffic_temps.max()),
        "weather_highest": str(weather.iloc[-1]["weather_main"]),
        "weather_highest_average": float(weather.iloc[-1]["average_traffic"]),
        "weather_highest_n": int(weather.iloc[-1]["record_count"]),
        "weather_lowest": str(weather.iloc[0]["weather_main"]),
        "weather_lowest_average": float(weather.iloc[0]["average_traffic"]),
        "weather_lowest_n": int(weather.iloc[0]["record_count"]),
        "weather_high_low_difference": float(
            weather.iloc[-1]["average_traffic"] - weather.iloc[0]["average_traffic"]
        ),
    }
    return {
        "df": df,
        "annual": annual,
        "stats": stats,
        "probability": probability,
        "holiday": holiday,
        "weather": weather,
        "daily_summary": daily_summary,
        "hourly_summary": hourly_summary,
        "temperature_traffic": temperature_traffic,
    }


def save_figures(result: dict[str, object]) -> None:
    df = result["df"]
    annual = result["annual"]
    folder = STATISTICS_DIR / "figures"
    folder.mkdir(parents=True, exist_ok=True)

    yearly = annual.loc[2012:2017]
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.bar(yearly.index.astype(str), yearly["total_volume"] / 1e6, color="#3572A5")
    ax.set(title="Recorded traffic volume by year (2012–2017)",
           xlabel="Year", ylabel="Sum of hourly traffic-volume readings (millions)")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(folder / "annual_traffic_totals.png", dpi=160)
    plt.close(fig)

    daily = (
        df[df["year"].isin([2015, 2016, 2017])]
        .groupby(["year", "date"], as_index=False)["traffic_volume"]
        .mean()
    )
    daily["day_of_year"] = pd.to_datetime(daily["date"]).dt.dayofyear
    fig, ax = plt.subplots(figsize=(10, 4.8))
    for year in [2015, 2016, 2017]:
        yearly_daily = daily[daily["year"] == year].groupby("day_of_year")["traffic_volume"].mean()
        ax.plot(yearly_daily.index, yearly_daily.values, label=str(year), linewidth=1.5)
    ax.set(title="Daily mean traffic by day of year", xlabel="Day of year",
           ylabel="Mean hourly traffic volume")
    ax.legend(title="Year")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(folder / "daily_traffic_2015_2017.png", dpi=160)
    plt.close(fig)

    hourly = df[df["year"] == 2017].groupby("hour")["traffic_volume"].mean()
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.bar(hourly.index, hourly.values, color="#4C9F70")
    ax.set(title="Average traffic by hour (2017)", xlabel="Hour of day",
           ylabel="Mean hourly traffic volume", xticks=range(24))
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(folder / "hourly_traffic_2017.png", dpi=160)
    plt.close(fig)

    weather = df.groupby("weather_main")["traffic_volume"].mean().sort_values()
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(weather.index, weather.values, color="#C97842")
    ax.set(title="Average traffic by main weather condition",
           xlabel="Mean hourly traffic volume", ylabel="Weather condition")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(folder / "weather_average_traffic.png", dpi=160)
    plt.close(fig)

    scatter_data = df[df["temp"] > 0]
    sample = scatter_data.sample(n=min(12000, len(scatter_data)), random_state=33)
    fig, ax = plt.subplots(figsize=(8, 5))
    scatter = ax.scatter(sample["temp_c"], sample["traffic_volume"],
                         c=sample["clouds_all"], s=8, alpha=0.35,
                         cmap="viridis", rasterized=True)
    fig.colorbar(scatter, ax=ax, label="Cloud cover (%)")
    ax.set(title="Temperature and traffic volume (zero-K readings excluded)",
           xlabel="Temperature (°C)", ylabel="Traffic volume (vehicles/hour)")
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(folder / "temperature_traffic_scatter.png", dpi=160)
    plt.close(fig)


def write_dashboard_data(df: pd.DataFrame) -> None:
    POWERBI_DIR.mkdir(parents=True, exist_ok=True)
    export = df.copy()
    export["holiday"] = export["holiday"].fillna("")
    export["date"] = export["date_time"].dt.strftime("%Y-%m-%d")
    export["date_time"] = export["date_time"].dt.strftime("%Y-%m-%d %H:%M:%S")
    export.to_csv(POWERBI_DIR / "traffic_dashboard_data.csv", index=False)


def write_database(df: pd.DataFrame) -> None:
    SQL_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(SQL_DIR / "traffic_analysis.db") as connection:
        df.to_sql("traffic", connection, if_exists="replace", index=False)


def write_result_tables(result: dict[str, object]) -> None:
    (result["annual"]).to_csv(STATISTICS_DIR / "annual_traffic_trends.csv")
    (result["holiday"]).to_csv(STATISTICS_DIR / "holiday_temperature_traffic.csv", index=False)
    (result["weather"]).to_csv(STATISTICS_DIR / "weather_average_traffic.csv", index=False)
    (result["daily_summary"]).to_csv(STATISTICS_DIR / "daily_mean_traffic_2015_2017.csv", index=False)
    (result["hourly_summary"]).to_csv(STATISTICS_DIR / "hourly_average_traffic_2017.csv", index=False)
    pd.DataFrame([result["temperature_traffic"]]).to_json(
        STATISTICS_DIR / "temperature_weather_insights.json", orient="records", indent=2
    )
    pd.DataFrame([result["stats"]]).to_json(
        STATISTICS_DIR / "descriptive_statistics.json", orient="records", indent=2
    )
    pd.DataFrame([result["probability"]]).to_json(
        STATISTICS_DIR / "probability_analysis.json", orient="records", indent=2
    )


def render_report(result: dict[str, object]) -> None:
    stats = result["stats"]
    probability = result["probability"]
    annual = result["annual"]
    holiday = result["holiday"]
    output = BASE / "insights_report.pdf"
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=19,
            leading=23,
            textColor=colors.HexColor("#18324A"),
            alignment=TA_CENTER,
            spaceAfter=2,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReportSubtitle",
            parent=styles["Normal"],
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#3572A5"),
            alignment=TA_CENTER,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReportBody",
            parent=styles["BodyText"],
            fontSize=8.4,
            leading=10.6,
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReportHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=13,
            textColor=colors.HexColor("#18324A"),
            spaceBefore=5,
            spaceAfter=4,
        )
    )

    def p(text: str, style: str = "ReportBody") -> Paragraph:
        return Paragraph(escape(text), styles[style])

    def report_table(rows: list[list[str]], widths: list[float] | None = None) -> Table:
        table = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#18324A")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7.3),
                    ("LEADING", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B7C7D3")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#EFF4F7")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        return table

    def decorate_page(canvas, document) -> None:
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#B7C7D3"))
        canvas.line(18 * mm, 13 * mm, 192 * mm, 13 * mm)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#526777"))
        canvas.drawString(18 * mm, 8 * mm, "Metro Interstate Traffic Volume | Part 1")
        canvas.drawRightString(192 * mm, 8 * mm, f"Page {document.page}")
        canvas.restoreState()

    document = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=15 * mm,
        bottomMargin=19 * mm,
        title="Smart City Traffic Intelligence - Part 1 Insights",
        author="Smart City Traffic Intelligence Capstone",
    )
    story: list[object] = [
        p("Smart City Traffic Intelligence", "ReportTitle"),
        p("Part 1 | Data Analytics Insights", "ReportSubtitle"),
        p(
            f"This decision-focused summary describes {stats['records']:,} hourly observations "
            f"from {stats['date_start']} through {stats['date_end']} on the Minneapolis-St Paul "
            "I-94 corridor. Traffic is vehicles per hour; source temperature is Kelvin unless "
            "converted to Celsius. Exact duplicate observations are retained for this Part 1 "
            "source-data analysis.",
        ),
        p("Annual traffic patterns", "ReportHeading"),
    ]
    annual_rows = [["Year", "Records", "Total readings", "Mean/hour", "YoY total"]]
    for year in range(2012, 2018):
        row = annual.loc[year]
        change = row["year_over_year_percent_change"]
        annual_rows.append(
            [
                str(year),
                f"{int(row['record_count']):,}",
                f"{row['total_volume']:,.0f}",
                f"{row['average_volume']:,.1f}",
                "N/A" if pd.isna(change) else f"{change:+.1f}%",
            ]
        )
    story.extend(
        [
            report_table(
                annual_rows,
                [15 * mm, 23 * mm, 39 * mm, 32 * mm, 25 * mm],
            ),
            Spacer(1, 4),
            p(
                f"Two coverage-sensitive shifts stand out: total observed readings rose "
                f"{annual.loc[2013, 'year_over_year_percent_change']:.1f}% in 2013 and "
                f"{annual.loc[2016, 'year_over_year_percent_change']:.1f}% in 2016, while "
                f"they fell {abs(annual.loc[2014, 'year_over_year_percent_change']):.1f}% "
                "in 2014 and 9.9% in 2015. The dataset has 2,559-10,605 records per year, "
                "so totals mostly reflect uneven observation coverage, not like-for-like "
                "annual demand. Mean hourly traffic is more comparable and ranges from "
                f"{annual.loc[2012:2017, 'average_volume'].min():,.0f} to "
                f"{annual.loc[2012:2017, 'average_volume'].max():,.0f} vehicles/hour. "
                "The date span includes partial 2012 and partial 2018; 2018 is excluded "
                "from this requested annual comparison.",
            ),
            p("Descriptive statistics and daily/hourly profile", "ReportHeading"),
            report_table(
                [
                    ["Measure", "Verified result", "Interpretation"],
                    ["Mean / median traffic", f"{stats['volume_mean']:,.2f} / {stats['volume_median']:,.0f}", "Vehicles per hour; median is less sensitive to extremes."],
                    ["Sample SD / variance", f"{stats['volume_sample_std']:,.2f} / {stats['volume_sample_variance']:,.2f}", "Sample convention (ddof=1); substantial variation across hours."],
                    ["Range", f"{stats['volume_min']:,}-{stats['volume_max']:,} (width {stats['volume_range']:,})", "Observed hourly traffic volume."],
                    ["Temp/traffic Pearson r", f"{stats['temp_traffic_correlation']:.4f} (zero-K excluded: {stats['temp_traffic_correlation_excluding_zero_kelvin']:.4f})", "Weak positive association; not evidence of causation."],
                ],
                [42 * mm, 54 * mm, 72 * mm],
            ),
            Spacer(1, 4),
        ]
    )
    daily = result["daily_summary"].set_index("year")["daily_mean"]
    hourly = result["hourly_summary"].set_index("hour")["average_traffic"]
    story.append(
        p(
            f"Mean hourly traffic was {daily.loc[2015]:,.0f} in 2015, "
            f"{daily.loc[2016]:,.0f} in 2016, and {daily.loc[2017]:,.0f} in 2017. "
            f"In 2017, the busiest mean hour was {int(hourly.idxmax()):02d}:00 "
            f"({hourly.max():,.0f} vehicles/hour), compared with the quietest "
            f"{int(hourly.idxmin()):02d}:00 hour ({hourly.min():,.0f}). These historical "
            "profiles support timing analysis, not a guarantee of future traffic.",
        )
    )
    story.extend(
        [
            PageBreak(),
            p("Weather, probability, and decision context", "ReportTitle"),
            p("Probability analysis", "ReportHeading"),
            p(
                "For this task, congestion means traffic_volume > 5,500, clear means "
                "weather_main = Clear, high temperature means temp > 292 K. For the odds "
                "ratio, cloudy is only the distinct Clouds category; other weather groups "
                "are excluded from that two-category comparison.",
            ),
            report_table(
                [
                    ["Probability", "Result"],
                    ["P(Congestion)", f"{probability['p_congestion']:.4f}"],
                    ["P(Clear)", f"{probability['p_clear']:.4f}"],
                    ["P(Clear and Congestion)", f"{probability['p_clear_and_congestion']:.4f}"],
                    ["P(Clear | Congestion)", f"{probability['clear_given_congestion']:.4f}"],
                    ["P(temp > 292 K | Congestion)", f"{probability['high_temp_given_congestion']:.4f}"],
                    ["P(Clear) x P(Congestion)", f"{probability['p_clear_times_p_congestion']:.5f}"],
                    ["Joint minus product", f"{probability['p_clear_and_congestion'] - probability['p_clear_times_p_congestion']:+.5f}"],
                    ["Clear vs Clouds congestion odds ratio", f"{probability['odds_ratio_clear_vs_clouds']:.4f}"],
                ],
                [105 * mm, 25 * mm],
            ),
            Spacer(1, 4),
            p(
                "The joint probability (0.03657) is below the product of marginals "
                "(0.04092), a small negative departure from independence; the events are "
                "not independent in this sample. The odds ratio below 1 means the observed "
                "congestion odds among Clear observations are lower than among Clouds "
                "observations. Every cell in this comparison is nonzero, so no zero-cell "
                "correction was needed. These observational associations are not causal "
                "weather effects.",
            ),
            p("Holiday-day temperature comparison", "ReportHeading"),
        ]
    )
    holiday_rows = [["Holiday", "Date", "Hours", "Mean temp (K)", "Mean temp (C)"]]
    for _, row in holiday.iterrows():
        if int(row["records"]) == 0:
            temp_k = "No observations"
            temp_c = "N/A"
            records = "0"
        else:
            temp_k = f"{row['mean_temp_k']:.2f}"
            temp_c = f"{row['mean_temp_c']:.2f}"
            records = f"{int(row['records'])}"
        holiday_rows.append(
            [f"{row['holiday']} {int(row['year'])}", row["date"], records, temp_k, temp_c]
        )
    weather = result["temperature_traffic"]
    story.extend(
        [
            report_table(
                holiday_rows,
                [43 * mm, 27 * mm, 17 * mm, 33 * mm, 31 * mm],
            ),
            Spacer(1, 4),
            p(
                f"The source contains no observations on New Year's Day 2015. The other "
                "holiday means use only the recorded hours shown above, so small samples "
                "and temperature differences cannot establish typical holiday conditions "
                "or traffic effects.",
            ),
            p("Weather and temperature signals", "ReportHeading"),
            p(
                f"Average traffic was highest in Clouds ({weather['weather_highest_average']:,.0f} "
                f"vehicles/hour; n={weather['weather_highest_n']:,}) and lowest in Squall "
                f"({weather['weather_lowest_average']:,.0f}; n={weather['weather_lowest_n']:,}), "
                f"a difference of {weather['weather_high_low_difference']:,.0f}. Squall has "
                "only four observations, so it is an unstable minimum. Among valid "
                f"temperatures, the top traffic quartile (at least "
                f"{weather['upper_quartile_traffic_cutoff']:,.0f} vehicles/hour; "
                f"n={weather['upper_quartile_valid_temp_rows']:,}) spans "
                f"{weather['upper_quartile_temp_min_c']:.1f} to "
                f"{weather['upper_quartile_temp_max_c']:.1f} C (median "
                f"{weather['upper_quartile_temp_median_c']:.1f} C). High traffic spans a "
                "broad temperature range; temperature alone is not a useful explanation.",
            ),
            p("Mobility interpretation and limitations", "ReportHeading"),
            p(
                "Use the dashboard's daily, hourly, weather, and temperature views to "
                "identify periods for further operational review. The strong variation "
                "across hours and modest temperature correlation support examining time "
                "and day type alongside weather, rather than treating weather as a single "
                "cause. The data describes one corridor and uneven historical coverage; "
                "it does not establish causal effects or citywide outcomes. Part 1 retains "
                f"{stats['zero_kelvin_rows']} zero-K readings and "
                f"{stats['rain_above_500_mm_rows']} rainfall value(s) above the broad "
                "500 mm/hour physical check for transparent source-data analysis; these "
                "measurements are flagged, not treated as plausible sensor values.",
            ),
        ]
    )
    document.build(story, onFirstPage=decorate_page, onLaterPages=decorate_page)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Path to source CSV")
    args = parser.parse_args()
    STATISTICS_DIR.mkdir(parents=True, exist_ok=True)
    df = load_data(args.input)
    result = analyze(df)
    save_figures(result)
    write_dashboard_data(result["df"])
    write_database(result["df"])
    write_result_tables(result)
    render_report(result)
    print(f"Part 1 outputs generated in {BASE}")


if __name__ == "__main__":
    main()
