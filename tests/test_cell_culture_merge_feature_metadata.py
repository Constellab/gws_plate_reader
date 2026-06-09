import pandas as pd
from gws_core import BaseTestCase, Table, TaskRunner
from gws_plate_reader.cell_culture_filter.cell_culture_merge_feature_metadata import (
    CellCultureMergeFeatureMetadata,
)


class TestCellCultureMergeFeatureMetadata(BaseTestCase):
    """Tests for CellCultureMergeFeatureMetadata task."""

    def _make_feature_table(self) -> Table:
        df = pd.DataFrame(
            {
                "Series": ["B1_S1", "B1_S2", "B2_S1"],
                "Model": ["Logistic_4P", "Logistic_4P", "Logistic_4P"],
                "y0": [0.1, 0.12, 0.11],
                "A": [1.0, 1.1, 0.95],
                "mu": [0.15, 0.14, 0.16],
                "R2": [0.98, 0.97, 0.99],
            }
        )
        return Table(df)

    def _make_metadata_table(self) -> Table:
        df = pd.DataFrame(
            {
                "Series": ["B1_S1", "B1_S2", "B2_S1", "B3_S1"],
                "Medium": ["M1", "M1", "M2", "M3"],
                "Glucose": [10.0, 10.0, 20.0, 30.0],
            }
        )
        return Table(df)

    def _run_task(self, feature_table: Table, metadata_table: Table) -> dict:
        runner = TaskRunner(
            task_type=CellCultureMergeFeatureMetadata,
            inputs={
                "feature_table": feature_table,
                "metadata_table": metadata_table,
            },
        )
        return runner.run()

    def test_basic_merge(self):
        """Inner join on Series produces merged table."""
        outputs = self._run_task(self._make_feature_table(), self._make_metadata_table())

        merged = outputs["metadata_feature_table"]
        df = merged.get_data()
        # Inner join: 3 matching Series (B1_S1, B1_S2, B2_S1)
        self.assertEqual(len(df), 3)

    def test_merged_has_columns_from_both(self):
        """Merged table includes columns from both feature and metadata tables."""
        outputs = self._run_task(self._make_feature_table(), self._make_metadata_table())

        df = outputs["metadata_feature_table"].get_data()
        # From metadata
        self.assertIn("Medium", df.columns)
        self.assertIn("Glucose", df.columns)
        # From features
        self.assertIn("y0", df.columns)
        self.assertIn("A", df.columns)
        self.assertIn("R2", df.columns)

    def test_inner_join_excludes_unmatched(self):
        """Series in metadata but not in features are excluded (inner join)."""
        outputs = self._run_task(self._make_feature_table(), self._make_metadata_table())

        df = outputs["metadata_feature_table"].get_data()
        # B3_S1 is only in metadata, should be excluded
        self.assertNotIn("B3_S1", df["Series"].values)

    def test_no_matching_series_produces_empty(self):
        """Tables with no common Series produce empty merged table."""
        feature_df = pd.DataFrame(
            {
                "Series": ["X1", "X2"],
                "y0": [0.1, 0.2],
            }
        )
        metadata_df = pd.DataFrame(
            {
                "Series": ["Y1", "Y2"],
                "Medium": ["M1", "M2"],
            }
        )
        outputs = self._run_task(Table(feature_df), Table(metadata_df))

        df = outputs["metadata_feature_table"].get_data()
        self.assertEqual(len(df), 0)

    def test_output_name(self):
        """Merged table has expected name."""
        outputs = self._run_task(self._make_feature_table(), self._make_metadata_table())
        self.assertEqual(outputs["metadata_feature_table"].name, "metadata_feature_table")
