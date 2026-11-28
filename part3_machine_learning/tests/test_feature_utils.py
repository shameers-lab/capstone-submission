import unittest
import tempfile
from pathlib import Path

import pandas as pd

from part3_machine_learning.feature_utils import (
    MODEL_FEATURES,
    add_model_features,
    create_targets,
    load_processed_data,
)


class FeatureUtilsTests(unittest.TestCase):
    def setUp(self) -> None:
        weather = ["Clear", "Rain", "Clear", "Fog"]
        self.data = pd.DataFrame(
            {
                "date_time": pd.date_range("2020-01-06", periods=4, freq="h"),
                "holiday": ["Unknown"] * 4,
                "temp": [280.0, 281.0, 282.0, 283.0],
                "rain_1h": [0.0, 1.0, 0.0, 0.0],
                "snow_1h": [0.0] * 4,
                "clouds_all": [0, 0, 80, 0],
                "weather_main": weather,
                "traffic_volume": [10, 20, 30, 40],
            }
        )

    def test_quartile_boundaries_and_proxy_definition(self) -> None:
        result, thresholds = create_targets(self.data, (10, 20, 30))

        self.assertEqual(
            result["congestion_category"].tolist(),
            ["Low", "Medium", "High", "Severe"],
        )
        self.assertEqual(result["proxy_accident_risk"].tolist(), [0, 0, 1, 1])
        self.assertEqual(thresholds, {"q1": 10, "q2": 20, "q3": 30})

    def test_supervised_predictors_exclude_volume_and_derived_targets(self) -> None:
        forbidden = {
            "traffic_volume",
            "congestion_category",
            "proxy_accident_risk",
        }
        self.assertTrue(forbidden.isdisjoint(MODEL_FEATURES))

    def test_time_features_are_cyclical_and_day_type_is_explicit(self) -> None:
        result = add_model_features(self.data)

        self.assertAlmostEqual(result.loc[0, "hour_sin"], 0.0, places=10)
        self.assertAlmostEqual(result.loc[0, "hour_cos"], 1.0, places=10)
        self.assertEqual(result.loc[0, "day_type"], "Weekday")

    def test_source_no_holiday_label_maps_to_existing_model_category(self) -> None:
        no_holiday = self.data.iloc[[0]].copy()
        no_holiday.loc[:, "holiday"] = "None"

        model_features = add_model_features(no_holiday)

        self.assertEqual(model_features.loc[0, "holiday"], "Unknown")

    def test_physically_impossible_precipitation_is_imputed_input_not_dropped_row(self) -> None:
        invalid = self.data.iloc[[0]].copy()
        invalid.loc[:, "rain_1h"] = 9831.3
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "processed.csv"
            invalid.to_csv(path, index=False)
            result = load_processed_data(path)

        self.assertEqual(len(result), 1)
        self.assertTrue(pd.isna(result.loc[0, "rain_1h"]))
        self.assertEqual(result.attrs["part3_invalid_weather_counts"]["rain_1h"], 1)


if __name__ == "__main__":
    unittest.main()
