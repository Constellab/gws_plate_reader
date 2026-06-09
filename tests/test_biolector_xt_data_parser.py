import json
import os

import pandas as pd
from gws_core import (
    BaseTestCase,
    Compress,
    Settings,
)
from gws_plate_reader.biolector_xt.biolector_xt_mock_service import BiolectorXTMockService
from gws_plate_reader.biolector_xt_data_parser.biolector_xt_data_parser import BiolectorXTDataParser


class TestBiolectorXTDataParser(BaseTestCase):
    """Tests for BiolectorXTDataParser task (unit-level tests of helper methods)."""

    def _get_mock_data(self) -> tuple[pd.DataFrame, dict, str]:
        """Download mock data and return raw DataFrame, BXT metadata dict, and tmp_dir."""
        mock_service = BiolectorXTMockService()
        experiment_zip_path = mock_service.download_experiment("Test")
        tmp_dir = Settings.make_temp_dir()
        Compress.smart_decompress(experiment_zip_path, tmp_dir)

        # Find CSV file and read as DataFrame
        csv_file = None
        for file_name in os.listdir(tmp_dir):
            if file_name.endswith(".csv"):
                csv_file = os.path.join(tmp_dir, file_name)
                break
        self.assertIsNotNone(csv_file, "CSV file should be found in test data")
        df = pd.read_csv(csv_file, sep=";", low_memory=False)

        # Load BXT metadata JSON
        metadata = {}
        for file_name in os.listdir(tmp_dir):
            if file_name.endswith("BXT.json"):
                json_path = os.path.join(tmp_dir, file_name)
                with open(json_path, "r") as f:
                    metadata = json.load(f)
                break

        return df, metadata, tmp_dir

    def test_is_micro_fluidics_standard_plate(self):
        """Standard plate (with A01 wells) is not microfluidics."""
        parser = BiolectorXTDataParser()
        df = pd.DataFrame({"Well": ["A01", "A02", "B01"]})
        self.assertFalse(parser.is_micro_fluidics(df))

    def test_is_micro_fluidics_detected(self):
        """Plate without A01 wells is detected as microfluidics."""
        parser = BiolectorXTDataParser()
        df = pd.DataFrame({"Well": ["C01", "C02", "D01"]})
        self.assertTrue(parser.is_micro_fluidics(df))

    def test_get_filters_with_channels(self):
        """get_filters extracts channel names from metadata."""
        parser = BiolectorXTDataParser()
        metadata = {
            "Channels": [
                {"Name": "Biomass"},
                {"Name": "pH"},
                {"Name": "DO"},
            ]
        }
        filters = parser.get_filters(metadata)
        self.assertEqual(filters, ["Biomass", "pH", "DO"])

    def test_get_filters_empty_channels(self):
        """get_filters returns empty list when no channels."""
        parser = BiolectorXTDataParser()
        metadata = {"Channels": []}
        filters = parser.get_filters(metadata)
        self.assertEqual(filters, [])

    def test_get_filters_missing_key(self):
        """get_filters returns empty list when Channels key is missing."""
        parser = BiolectorXTDataParser()
        metadata = {}
        filters = parser.get_filters(metadata)
        self.assertEqual(filters, [])

    def test_get_wells(self):
        """get_wells returns combined cultivation and reservoir wells."""
        parser = BiolectorXTDataParser()
        metadata = {
            "Microplate": {
                "CultivationLabels": ["A01", "A02", "B01"],
                "ReservoirLabels": ["F07", "F08"],
            }
        }
        wells = parser.get_wells(metadata)
        self.assertEqual(len(wells), 5)
        self.assertIn("A01", wells)
        self.assertIn("F08", wells)

    def test_get_wells_cultivation(self):
        """get_wells_cultivation returns cultivation labels."""
        parser = BiolectorXTDataParser()
        metadata = {
            "Microplate": {
                "CultivationLabels": ["A01", "A02"],
            }
        }
        cultivation = parser.get_wells_cultivation(metadata)
        self.assertEqual(cultivation, ["A01", "A02"])

    def test_get_wells_reservoir(self):
        """get_wells_reservoir returns reservoir labels."""
        parser = BiolectorXTDataParser()
        metadata = {
            "Microplate": {
                "ReservoirLabels": ["F07", "F08"],
            }
        }
        reservoir = parser.get_wells_reservoir(metadata)
        self.assertEqual(reservoir, ["F07", "F08"])

    def test_parse_data_with_mock_data(self):
        """parse_data correctly parses mock BiolectorXT data."""
        df, metadata, _ = self._get_mock_data()

        if not metadata or not isinstance(metadata, dict):
            self.skipTest("Mock BXT metadata not available or not a dict")

        parser = BiolectorXTDataParser()
        result = parser.parse_data(df, metadata)

        self.assertIsInstance(result, dict)
        self.assertGreater(len(result), 0, "Should parse at least one filter")
        for key, value_df in result.items():
            self.assertIsInstance(key, str)
            self.assertIn(
                "Temps_en_h", value_df.columns, f"Filter '{key}' should have 'Temps_en_h' column"
            )

    def test_get_wells_label_description(self):
        """get_wells_label_description returns descriptions for all 48 wells."""
        parser = BiolectorXTDataParser()
        metadata = {
            "Layout": {
                "CultivationLabelDescriptionsMap": {
                    "A01": "Sample 1",
                    "A02": "Sample 2",
                },
                "ReservoirLabelDescriptionsMap": {},
            }
        }
        labels = parser.get_wells_label_description(metadata)

        self.assertIsInstance(labels, dict)
        # Should have entries for wells A01-F08 (48 wells)
        self.assertEqual(len(labels), 48)
        self.assertIn("A01", labels)
