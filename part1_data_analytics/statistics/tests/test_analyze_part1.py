import sys
import unittest
from pathlib import Path

import pandas as pd

STATISTICS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STATISTICS_DIR))

from analyze_part1 import analyze


class Part1HolidayAnalysisTests(unittest.TestCase):
    def test_holiday_comparison_uses_calendar_dates_and_records_missing_dates(self):
        data = pd.DataFrame(
            [
                {
                    "holiday": "None",
                    "temp": 267.0,
                    "rain_1h": 0.0,
                    "snow_1h": 0.0,
                    "clouds_all": 25,
                    "weather_main": "Clear",
                    "weather_description": "sky is clear",
                    "date_time": pd.Timestamp("2016-01-01 01:00:00"),
                    "traffic_volume": 1000,
                },
                {
                    "holiday": "None",
                    "temp": 295.0,
                    "rain_1h": 0.0,
                    "snow_1h": 0.0,
                    "clouds_all": 30,
                    "weather_main": "Clear",
                    "weather_description": "sky is clear",
                    "date_time": pd.Timestamp("2016-09-05 01:00:00"),
                    "traffic_volume": 1200,
                },
            ]
        )

        result = analyze(data)
        holidays = result["holiday"].set_index(["holiday", "year"])

        self.assertEqual(len(holidays), 6)
        self.assertEqual(holidays.loc[("New Year's Day", 2015), "records"], 0)
        self.assertEqual(holidays.loc[("New Year's Day", 2016), "records"], 1)
        self.assertEqual(holidays.loc[("New Year's Day", 2016), "mean_temp_k"], 267.0)
        self.assertEqual(holidays.loc[("Labor Day", 2016), "records"], 1)


if __name__ == "__main__":
    unittest.main()
