import pandas as pd
from gws_core import BaseTestCase, Table, TaskRunner
from gws_plate_reader.cell_culture_filter.cell_culture_prepare_feature_metadata_table import (
    CellCulturePrepareFeatureMetadataTable,
)


class TestCellCulturePrepareFeatureMetadataTable(BaseTestCase):
    """Tests for CellCulturePrepareFeatureMetadataTable task."""

    def _make_feature_metadata_table(self) -> Table:
        df = pd.DataFrame(
            {
                "Series": ["B1_S1", "B1_S2", "B2_S1"],
                "Medium": ["M1", "M1", "M2"],
                "Glucose": [10.0, 10.0, 20.0],
                "y0": [0.1, 0.12, 0.11],
                "A": [1.0, 1.1, 0.95],
                "Notes": ["ok", "good", "poor"],
            }
        )
        return Table(df)

    def _run_task(self, table: Table, params: dict | None = None) -> dict:
        runner = TaskRunner(
            task_type=CellCulturePrepareFeatureMetadataTable,
            inputs={"feature_metadata_table": table},
            params=params or {},
        )
        return runner.run()

    def test_removes_non_numeric_except_medium(self):
        """Non-numeric columns (except Medium) are removed."""
        table = self._make_feature_metadata_table()
        outputs = self._run_task(table)

        df = outputs["ready_feature_metadata_table"].get_data()
        self.assertIn("Medium", df.columns)
        self.assertNotIn("Series", df.columns)
        self.assertNotIn("Notes", df.columns)

    def test_keeps_numeric_columns(self):
        """All numeric columns are preserved."""
        table = self._make_feature_metadata_table()
        outputs = self._run_task(table)

        df = outputs["ready_feature_metadata_table"].get_data()
        self.assertIn("Glucose", df.columns)
        self.assertIn("y0", df.columns)
        self.assertIn("A", df.columns)

    def test_nan_filled_with_zero(self):
        """NaN values are replaced with 0."""
        df = pd.DataFrame(
            {
                "Medium": ["M1", "M2"],
                "Glucose": [10.0, None],
                "y0": [None, 0.1],
            }
        )
        table = Table(df)
        outputs = self._run_task(table)

        result_df = outputs["ready_feature_metadata_table"].get_data()
        self.assertEqual(result_df["Glucose"].iloc[1], 0.0)
        self.assertEqual(result_df["y0"].iloc[0], 0.0)

    def test_custom_medium_column(self):
        """Custom medium_name_column parameter works."""
        df = pd.DataFrame(
            {
                "Type": ["A", "B"],
                "Val": [1.0, 2.0],
                "Label": ["x", "y"],
            }
        )
        table = Table(df)
        outputs = self._run_task(table, {"medium_name_column": "Type"})

        result_df = outputs["ready_feature_metadata_table"].get_data()
        self.assertIn("Type", result_df.columns)
        self.assertNotIn("Label", result_df.columns)

    def test_medium_column_not_found_keeps_only_numeric(self):
        """If medium column not found, only numeric columns are kept."""
        df = pd.DataFrame(
            {
                "Series": ["B1", "B2"],
                "Val": [1.0, 2.0],
            }
        )
        table = Table(df)
        outputs = self._run_task(table, {"medium_name_column": "NONEXISTENT"})

        result_df = outputs["ready_feature_metadata_table"].get_data()
        self.assertNotIn("Series", result_df.columns)
        self.assertIn("Val", result_df.columns)

    def test_output_name(self):
        """Output table has expected name."""
        table = self._make_feature_metadata_table()
        outputs = self._run_task(table)
        self.assertEqual(
            outputs["ready_feature_metadata_table"].name,
            "ready_feature_metadata_table",
        )
