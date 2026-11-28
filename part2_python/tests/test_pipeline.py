import csv
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

PART2_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PART2_DIR))

import pipeline
from pipeline import clean_dataset, load_dataset, run_pipeline


def make_row(timestamp, temp, traffic_volume, weather='Clear'):
    return {
        'holiday': 'None',
        'temp': temp,
        'rain_1h': 0.0,
        'snow_1h': 0.0,
        'clouds_all': 10,
        'weather_main': weather,
        'weather_description': 'sky is clear',
        'date_time': timestamp,
        'traffic_volume': traffic_volume,
    }


class PipelineTests(unittest.TestCase):
    def test_main_configures_logging_before_running_pipeline(self):
        argv = [
            'pipeline.py',
            '--data', 'source.csv',
            '--output-dir', 'figures',
            '--processed-dir', 'processed',
        ]
        with patch.object(sys, 'argv', argv):
            with patch('pipeline.configure_logger') as configure_logging:
                with patch('pipeline.run_pipeline') as run:
                    pipeline.main()

        configure_logging.assert_called_once_with(PART2_DIR / 'pipeline.log')
        run.assert_called_once_with('source.csv', 'figures', 'processed')

    def test_load_dataset_rejects_missing_required_columns(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'incomplete.csv'
            path.write_text('date_time\n2020-01-01 00:00:00\n', encoding='utf-8')

            with self.assertRaisesRegex(ValueError, 'Missing required columns'):
                load_dataset(path)

    def test_load_dataset_preserves_no_holiday_category_and_reads_blank_as_missing(self):
        rows = [
            make_row('2020-01-01 00:00:00', 280, 100, weather='Clear'),
            make_row('2020-01-01 01:00:00', 281, 200, weather='Clouds'),
        ]
        rows[1]['holiday'] = ''

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'traffic.csv'
            with path.open('w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)

            loaded = load_dataset(path)

        self.assertEqual(loaded.loc[0, 'holiday'], 'None')
        self.assertTrue(pd.isna(loaded.loc[1, 'holiday']))
        with self.assertLogs('pipeline', level='WARNING'):
            cleaned = clean_dataset(loaded)
        self.assertEqual(cleaned.loc[0, 'holiday'], 'None')
        self.assertEqual(cleaned.loc[1, 'holiday'], 'Unknown')

    def test_clean_dataset_removes_duplicates_and_uses_month_medians(self):
        rows = [
            make_row('2020-01-01 00:00:00', 280, 100),
            make_row('2020-01-01 00:00:00', 280, 100),
            make_row('2020-01-02 00:00:00', 500, -1),
            make_row('2020-02-01 00:00:00', 300, 200),
            make_row('2020-02-02 00:00:00', 320, 400),
            make_row('2020-02-03 00:00:00', None, None),
            make_row('not-a-timestamp', 285, 500),
        ]
        rows[0]['holiday'] = None
        rows[0]['weather_main'] = ' clear '
        rows[1]['holiday'] = None
        rows[1]['weather_main'] = ' clear '
        rows[2]['rain_1h'] = 'not-numeric'
        rows[2]['snow_1h'] = None
        rows[2]['clouds_all'] = None
        rows[2]['weather_description'] = '  '

        with self.assertLogs('pipeline', level='WARNING') as captured:
            cleaned = clean_dataset(pd.DataFrame(rows))

        self.assertEqual(len(cleaned), 5)
        january_imputed = cleaned.loc[cleaned['date_time'].eq('2020-01-02 00:00:00')].iloc[0]
        february_imputed = cleaned.loc[cleaned['date_time'].eq('2020-02-03 00:00:00')].iloc[0]
        self.assertEqual(january_imputed['temp'], 280)
        self.assertEqual(january_imputed['traffic_volume'], 100)
        self.assertEqual(february_imputed['temp'], 310)
        self.assertEqual(february_imputed['traffic_volume'], 300)
        messages = '\n'.join(captured.output)
        self.assertIn('Removed 1 exact duplicate rows', messages)
        self.assertIn('Coerced 1 non-numeric rain_1h values', messages)
        self.assertIn('outside the plausible 150–400 K range', messages)
        self.assertIn('negative traffic-volume values', messages)
        self.assertIn('missing or unparseable timestamps', messages)
        self.assertIn('Replaced 1 missing holiday categories', messages)
        self.assertIn('Replaced 1 blank weather_description categories', messages)
        self.assertIn('Trimmed surrounding whitespace from 1 weather_main', messages)
        self.assertIn('Standardized 1 weather_main values', messages)
        self.assertIn('Imputed 1 missing rain_1h values', messages)
        self.assertIn('Imputed 1 missing snow_1h values', messages)
        self.assertIn('Imputed 1 missing clouds_all values', messages)
        self.assertIn('Month 1: imputed 1 missing temp values', messages)
        self.assertIn('Month 1: imputed 1 missing traffic_volume values', messages)
        self.assertIn('Month 2: imputed 1 missing temp values', messages)
        self.assertIn('Month 2: imputed 1 missing traffic_volume values', messages)

    def test_clean_dataset_flags_and_imputes_impossible_weather_measurements(self):
        rows = [
            make_row('2020-01-01 00:00:00', 280, 100),
            make_row('2020-01-01 01:00:00', 281, 200),
        ]
        rows[1]['rain_1h'] = 9831.3
        rows[1]['snow_1h'] = -1
        rows[1]['clouds_all'] = 101

        with self.assertLogs('pipeline', level='WARNING') as captured:
            cleaned = clean_dataset(pd.DataFrame(rows))

        self.assertEqual(len(cleaned), 2)
        self.assertEqual(cleaned.loc[1, 'rain_1h'], 0)
        self.assertEqual(cleaned.loc[1, 'snow_1h'], 0)
        self.assertEqual(cleaned.loc[1, 'clouds_all'], 10)
        messages = '\n'.join(captured.output)
        self.assertIn(
            'Set 1 rain_1h values outside the documented physical range [0, 500] mm/hour to missing',
            messages,
        )
        self.assertIn(
            'Set 1 snow_1h values outside the documented physical range [0, 500] mm/hour to missing',
            messages,
        )
        self.assertIn(
            'Set 1 clouds_all values outside the documented physical range [0, 100] percent to missing',
            messages,
        )

    def test_pipeline_separates_cleaned_data_features_and_figures(self):
        rows = [
            make_row('2020-01-01 00:00:00', 280, 100),
            make_row('2020-01-01 01:00:00', 281, 200, 'Clouds'),
            make_row('2020-01-01 02:00:00', 282, 300, 'Rain'),
            make_row('2020-01-01 03:00:00', 283, 400),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_path = root / 'source.csv'
            with input_path.open('w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            original_input = input_path.read_bytes()
            figures_dir = root / 'figures'
            processed_dir = root / 'data' / 'processed'

            with patch('pipeline.configure_logger') as configure_logging:
                with self.assertLogs('visualizations', level='INFO') as figure_logs:
                    engineered = run_pipeline(
                        str(input_path),
                        str(figures_dir),
                        str(processed_dir),
                    )
            configure_logging.assert_not_called()

            cleaned_path = processed_dir / 'traffic_cleaned.csv'
            features_path = processed_dir / 'traffic_features.csv'
            self.assertTrue(cleaned_path.is_file())
            self.assertTrue(features_path.is_file())
            self.assertNotIn('hour', pd.read_csv(cleaned_path).columns)
            feature_data = pd.read_csv(features_path)
            self.assertIn('hour', feature_data.columns)
            self.assertIn('congestion_category', feature_data.columns)
            self.assertEqual(len(feature_data), len(engineered))
            self.assertEqual(input_path.read_bytes(), original_input)
            self.assertEqual(len(list(figures_dir.glob('*.png'))), 4)
            for name in [
                'hourly_average_traffic.png',
                'weather_average_traffic.png',
                'weekday_weekend_traffic.png',
                'temperature_vs_traffic.png',
            ]:
                self.assertIn(f'Saved figure to {name}', '\n'.join(figure_logs.output))


if __name__ == '__main__':
    unittest.main()
