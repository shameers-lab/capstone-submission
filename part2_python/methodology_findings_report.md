# Part 2 Methodology and Findings Report

## Overview

The Part 2 work focuses on building a reproducible data-processing pipeline for the Metro Interstate Traffic Volume dataset and generating features suitable for downstream mobility analysis. The workflow begins with raw CSV loading, schema validation, data cleaning, and explicit logging of changes. The target is to preserve the integrity of the original dataset while creating interpretable features for time-of-day, weather, and congestion analysis.

## Methodology

### Data validation and cleaning

The pipeline validates required columns before processing. It checks for the expected schema and raises a clear error if required attributes are missing. After loading the CSV, the pipeline removes duplicate rows and converts numeric fields to numeric data types. Invalid timestamps are detected and logged, while physically impossible values are treated as missing rather than silently dropped: temperature outside 150-400 K, negative traffic volume, rain or snow outside 0-500 mm/hour, and cloud cover outside 0-100 are logged with counts and reasons. The prior tracked input contained a 9,831.3 mm/hour rainfall value, far above the intentionally broad 500 mm/hour ceiling. The pipeline now flags it and median-imputes the field while retaining the traffic observation; the current Part 3 loader independently checks the same bounds.

To keep the cleaning reproducible and defensible, missing values are imputed by month-specific medians for the main numerical features. This is a group-aware strategy that avoids the bias of a single global imputation while preserving the original time structure of the dataset.

### Feature engineering

The feature engineering step creates time-based variables including hour, weekday, weekend flag, month, and cyclical encodings for time-of-day patterns. Weather features include category encoding for weather_main, clear/rain/snow flags, and a low-visibility indicator based on cloud cover. Continuous features such as temperature and traffic volume are also scaled so that downstream analysis can compare relative magnitudes more effectively.

A congestion category is created using traffic-volume quartiles. This produces operational categories such as Low, Medium, High, and Severe, which are useful for summarising high-demand periods without treating all high-volume instances as equivalent.

The pipeline saves the cleaned source columns separately from the engineered
features under `data/processed/`. This keeps reproducible data stages distinct
from the chart outputs in `figures/`.

### Visualisation

The pipeline generates at least four figures using Matplotlib:

1. average traffic by hour
2. average traffic by weather condition
3. weekday versus weekend comparison
4. temperature versus traffic volume scatter plot

These figures are saved under the `figures/` folder and provide a quick operational summary of the mobility patterns in the dataset.

## Findings

The processed dataset confirms a strong time-of-day pattern in traffic volume. Average traffic is materially higher during commuter-heavy hours, which is consistent with the wider city-transport interpretation of the project. The weekday/weekend comparison shows a meaningful difference between working-day travel demand and recreational or lower-demand periods, which supports travel-time planning and operational forecasting.

In the verified weekday/weekend output, average traffic was 3,533.60 vehicles on weekdays and 2,570.51 vehicles on weekends. These values are descriptive historical aggregates, not causal estimates or forecasts.

Weather conditions also carry a measurable relationship with traffic volume. The weather-based summary suggests that traffic varies by condition, with precipitation and poor visibility creating operationally relevant changes in drive patterns. The temperature-versus-traffic scatter plot shows that temperature alone is not a dominant predictor, but it remains part of the broader weather and time-of-day context that helps explain traffic variation.

The verified full-data run used the unchanged source CSV, loaded 48,204 rows, removed 17 exact duplicate rows, and produced 48,187 cleaned rows and 27 engineered columns. Both tracked processed CSVs are outputs of that pipeline run, not projections from one another. The raw CSV is not included in the repository; obtain it and place it at the repository root to reproduce the run. Its feature quartile thresholds were Q1=1,192.5, Q2=3,379, and Q3=4,933 vehicles: Low is at or below Q1, Medium is above Q1 and at or below Q2, High is above Q2 and at or below Q3, and Severe is above Q3.

## Operational meaning

For a smart-city mobility context, these findings are useful because they show where traffic management and communication should be prioritised. The city can focus on high-demand commute windows, plan for weather-sensitive operations during periods of poor visibility and precipitation, and use weekday/weekend differences to support commuter advice and network management.

## Limitations

This analysis is based on historical traffic and weather observations and is best interpreted as a descriptive, operational study rather than a causal model. The pipeline preserves valid extremes instead of deleting them indiscriminately, which is appropriate for a mobility dataset but also means that unusually high demand periods must be interpreted in context.

## Conclusion

The Part 2 pipeline demonstrates an end-to-end data-cleaning and feature-engineering workflow that is reproducible, logged, and grounded in the actual Metro Interstate Traffic Volume dataset. It provides the feature foundation and operational insights needed before the project moves into the machine learning and AI stages.
