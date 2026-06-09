import pandas as pd
from gws_core import BaseTestCase, Table, TaskRunner
from gws_plate_reader.cell_culture_analysis.cell_culture_medium_table_filter import (
    CellCultureMediumTableFilter,
)


class TestCellCultureMediumTableFilter(BaseTestCase):
    """Tests for CellCultureMediumTableFilter task."""

    def _make_medium_table(self) -> Table:
        """Create a sample medium composition table."""
        df = pd.DataFrame(
            {
                "Medium": ["M1", "M2", "M3", "M1", "M2"],
                "Glucose": [10.0, 20.0, 30.0, 11.0, 21.0],
                "Nitrogen": [5.0, 10.0, 15.0, 6.0, 11.0],
            }
        )
        return Table(df)

    def _run_task(self, table: Table, params: dict | None = None) -> dict:
        runner = TaskRunner(
            task_type=CellCultureMediumTableFilter,
            inputs={"medium_table": table},
            params=params or {},
        )
        return runner.run()

    def test_filter_by_selected_medium(self):
        """Selecting specific medium names keeps only matching rows."""
        table = self._make_medium_table()
        outputs = self._run_task(table, {"selected_medium": ["M1", "M3"]})

        filtered = outputs["filtered_table"]
        df = filtered.get_data()
        self.assertEqual(set(df["Medium"].unique()), {"M1", "M3"})
        self.assertEqual(len(df), 3)  # 2 rows M1 + 1 row M3

    def test_empty_selection_keeps_all(self):
        """Empty selection list returns all rows."""
        table = self._make_medium_table()
        outputs = self._run_task(table, {"selected_medium": []})

        filtered = outputs["filtered_table"]
        df = filtered.get_data()
        self.assertEqual(len(df), 5)

    def test_no_selection_param_keeps_all(self):
        """Default params (no selection) returns all rows."""
        table = self._make_medium_table()
        outputs = self._run_task(table)

        filtered = outputs["filtered_table"]
        df = filtered.get_data()
        self.assertEqual(len(df), 5)

    def test_missing_medium_silently_skipped(self):
        """Selecting a medium not in the table still works, returns only found ones."""
        table = self._make_medium_table()
        outputs = self._run_task(table, {"selected_medium": ["M1", "NONEXISTENT"]})

        filtered = outputs["filtered_table"]
        df = filtered.get_data()
        self.assertEqual(set(df["Medium"].unique()), {"M1"})
        self.assertEqual(len(df), 2)

    def test_all_selected_missing_returns_empty(self):
        """Selecting only non-existent medium returns empty table."""
        table = self._make_medium_table()
        outputs = self._run_task(table, {"selected_medium": ["NONEXISTENT"]})

        filtered = outputs["filtered_table"]
        df = filtered.get_data()
        self.assertEqual(len(df), 0)

    def test_custom_medium_column_name(self):
        """Custom medium_column parameter works correctly."""
        df = pd.DataFrame(
            {
                "Type": ["A", "B", "C"],
                "Value": [1.0, 2.0, 3.0],
            }
        )
        table = Table(df)
        outputs = self._run_task(
            table,
            {
                "medium_column": "Type",
                "selected_medium": ["A", "C"],
            },
        )

        filtered = outputs["filtered_table"]
        result_df = filtered.get_data()
        self.assertEqual(len(result_df), 2)
        self.assertEqual(set(result_df["Type"].unique()), {"A", "C"})

    def test_invalid_medium_column_raises(self):
        """ValueError raised when medium_column does not exist."""
        table = self._make_medium_table()
        with self.assertRaises(ValueError):
            self._run_task(table, {"medium_column": "INVALID_COL"})

    def test_output_preserves_columns(self):
        """All original columns are preserved in filtered output."""
        table = self._make_medium_table()
        outputs = self._run_task(table, {"selected_medium": ["M1"]})

        filtered = outputs["filtered_table"]
        df = filtered.get_data()
        self.assertEqual(list(df.columns), ["Medium", "Glucose", "Nitrogen"])
