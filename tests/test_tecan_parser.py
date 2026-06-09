import numpy as np
import pandas as pd
from gws_core import BaseTestCase, JSONDict, Table
from gws_plate_reader.tecan.tecan_parser import TecanParser


class TestTecanParser(BaseTestCase):
    """Tests for TecanParser class."""

    def _make_data_table(self) -> Table:
        """Create a simple 8x12 plate data table (rows A-H, columns 1-12)."""
        data = {}
        for col in range(1, 13):
            data[str(col)] = [float(row * 12 + col) for row in range(8)]
        df = pd.DataFrame(data, index=[chr(i) for i in range(ord("A"), ord("H") + 1)])
        return Table(df)

    def _make_plate_layout(self) -> JSONDict:
        """Create a sample plate layout JSONDict."""
        layout = {
            "A1": {"compound": "glucose", "concentration": "10mM"},
            "A2": {"compound": "glucose", "concentration": "20mM"},
            "B1": {"compound": "lactose", "concentration": "10mM"},
            "B2": {"compound": "lactose", "concentration": "20mM"},
            "C1": {"compound": "blank"},
        }
        return JSONDict(layout)

    def test_get_wells_tecan(self):
        """get_wells_tecan returns all 96 well positions (A1 to H12)."""
        parser = TecanParser()
        wells = parser.get_wells_tecan()

        self.assertEqual(len(wells), 96)
        self.assertIn("A1", wells)
        self.assertIn("H12", wells)

    def test_get_wells_filled_with_info(self):
        """get_wells_filled_with_info returns wells defined in plate layout."""
        parser = TecanParser(
            data_file=self._make_data_table(),
            plate_layout=self._make_plate_layout(),
        )
        filled = parser.get_wells_filled_with_info()

        self.assertIn("A1", filled)
        self.assertIn("B1", filled)
        self.assertEqual(len(filled), 5)

    def test_get_wells_label_description(self):
        """get_wells_label_description returns string descriptions for all wells."""
        parser = TecanParser(
            data_file=self._make_data_table(),
            plate_layout=self._make_plate_layout(),
        )
        labels = parser.get_wells_label_description()

        self.assertEqual(len(labels), 96)
        # Wells in layout should have non-empty descriptions
        self.assertNotEqual(labels["A1"], "")
        # Wells not in layout should have empty descriptions
        self.assertEqual(labels["H12"], "")

    def test_get_wells_label_description_dict(self):
        """get_wells_label_description_dict returns dict descriptions."""
        parser = TecanParser(
            data_file=self._make_data_table(),
            plate_layout=self._make_plate_layout(),
        )
        labels = parser.get_wells_label_description_dict()

        self.assertEqual(len(labels), 96)
        self.assertIsInstance(labels["A1"], dict)
        self.assertEqual(labels["A1"]["compound"], "glucose")
        self.assertIsInstance(labels["H12"], dict)
        self.assertEqual(len(labels["H12"]), 0)  # empty dict

    def test_enrich_well_metadata(self):
        """enrich_well_metadata adds data values to each well."""
        parser = TecanParser(
            data_file=self._make_data_table(),
            plate_layout=self._make_plate_layout(),
        )
        enriched = parser.enrich_well_metadata()

        # A1 should have both metadata and data
        self.assertIn("compound", enriched["A1"])
        self.assertIn("data", enriched["A1"])
        self.assertFalse(np.isnan(enriched["A1"]["data"]))

    def test_get_wells_list_by_compound_type(self):
        """get_wells_list_by_compound_type filters wells by compound."""
        parser = TecanParser(
            data_file=self._make_data_table(),
            plate_layout=self._make_plate_layout(),
        )
        glucose_wells = parser.get_wells_list_by_compound_type("glucose")

        self.assertEqual(len(glucose_wells), 2)
        self.assertIn("A1", glucose_wells)
        self.assertIn("A2", glucose_wells)

    def test_get_wells_list_by_compound_type_no_match(self):
        """get_wells_list_by_compound_type returns empty for unknown compound."""
        parser = TecanParser(
            data_file=self._make_data_table(),
            plate_layout=self._make_plate_layout(),
        )
        result = parser.get_wells_list_by_compound_type("unknown_compound")
        self.assertEqual(len(result), 0)

    def test_mean_data_for_compound(self):
        """mean_data_for_compound returns average of matched wells."""
        parser = TecanParser(
            data_file=self._make_data_table(),
            plate_layout=self._make_plate_layout(),
        )
        mean_val = parser.mean_data_for_compound("glucose")

        self.assertIsNotNone(mean_val)
        self.assertIsInstance(mean_val, float)

    def test_mean_data_for_compound_no_match(self):
        """mean_data_for_compound returns None for unknown compound."""
        parser = TecanParser(
            data_file=self._make_data_table(),
            plate_layout=self._make_plate_layout(),
        )
        result = parser.mean_data_for_compound("unknown_compound")
        self.assertIsNone(result)

    def test_remove_wells_from_dataframe(self):
        """remove_wells_from_dataframe sets specified wells to NaN and cleans."""
        parser = TecanParser(
            data_file=self._make_data_table(),
            plate_layout=self._make_plate_layout(),
        )
        result_df = parser.remove_wells_from_dataframe(["A1", "A2"])

        # Original data at A1 (row A, col 1) should now be NaN or removed
        if "A" in result_df.index and "1" in result_df.columns:
            self.assertTrue(np.isnan(result_df.at["A", "1"]))

    def test_parse_data(self):
        """parse_data returns the raw DataFrame."""
        parser = TecanParser(
            data_file=self._make_data_table(),
            plate_layout=self._make_plate_layout(),
        )
        result = parser.parse_data()

        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(result.shape[0], 8)
        self.assertEqual(result.shape[1], 12)

    def test_update_row_data(self):
        """update_row_data replaces the internal data table."""
        parser = TecanParser(
            data_file=self._make_data_table(),
            plate_layout=self._make_plate_layout(),
        )
        new_df = pd.DataFrame({"1": [1.0], "2": [2.0]}, index=["A"])
        parser.update_row_data(new_df)

        result = parser.parse_data()
        self.assertEqual(result.shape[0], 1)
