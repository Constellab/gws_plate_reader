import numpy as np
import pandas as pd
from gws_core import BaseTestCase, PlotlyResource, Table, TaskRunner
from gws_plate_reader.cell_culture_analysis.cell_culture_medium_pca import CellCultureMediumPCA


class TestCellCultureMediumPCA(BaseTestCase):
    """Tests for CellCultureMediumPCA task."""

    def _make_medium_table(self, n_rows: int = 10) -> Table:
        """Create a sample medium composition table with numeric features."""
        rng = np.random.default_rng(42)
        df = pd.DataFrame(
            {
                "Medium": [f"M{i % 3}" for i in range(n_rows)],
                "Glucose": rng.uniform(5, 30, n_rows),
                "Nitrogen": rng.uniform(1, 15, n_rows),
                "Phosphate": rng.uniform(0.5, 5, n_rows),
            }
        )
        return Table(df)

    def _run_task(self, table: Table, params: dict | None = None) -> dict:
        runner = TaskRunner(
            task_type=CellCultureMediumPCA,
            inputs={"medium_table": table},
            params=params or {},
        )
        return runner.run()

    def test_basic_pca_outputs(self):
        """PCA produces scores_table, scatter_plot, and biplot."""
        table = self._make_medium_table()
        outputs = self._run_task(table)

        self.assertIn("scores_table", outputs)
        self.assertIn("scatter_plot", outputs)
        self.assertIn("biplot", outputs)

    def test_scores_table_structure(self):
        """Scores table has correct number of rows and PC columns."""
        table = self._make_medium_table(10)
        outputs = self._run_task(table)

        scores_df = outputs["scores_table"].get_data()
        self.assertEqual(len(scores_df), 10)
        # Should have PC columns
        pc_cols = [c for c in scores_df.columns if c.startswith("PC")]
        self.assertGreater(len(pc_cols), 0)

    def test_scatter_plot_is_plotly(self):
        """Scatter plot output is a PlotlyResource with a figure."""
        table = self._make_medium_table()
        outputs = self._run_task(table)

        scatter = outputs["scatter_plot"]
        self.assertIsInstance(scatter, PlotlyResource)
        self.assertIsNotNone(scatter.get_figure())

    def test_biplot_is_plotly(self):
        """Biplot output is a PlotlyResource with a figure."""
        table = self._make_medium_table()
        outputs = self._run_task(table)

        biplot = outputs["biplot"]
        self.assertIsInstance(biplot, PlotlyResource)
        self.assertIsNotNone(biplot.get_figure())

    def test_columns_to_exclude(self):
        """Excluding columns reduces PCA features."""
        table = self._make_medium_table()
        outputs = self._run_task(table, {"columns_to_exclude": ["Phosphate"]})

        scores_df = outputs["scores_table"].get_data()
        # With 2 features remaining, should have at most 2 PCs
        pc_cols = [c for c in scores_df.columns if c.startswith("PC")]
        self.assertLessEqual(len(pc_cols), 2)

    def test_missing_medium_column_raises(self):
        """ValueError raised when medium column does not exist."""
        table = self._make_medium_table()
        with self.assertRaises(ValueError):
            self._run_task(table, {"medium_column": "NONEXISTENT"})

    def test_empty_table_raises(self):
        """ValueError raised for empty input table."""
        df = pd.DataFrame({"Medium": pd.Series(dtype=str), "Val": pd.Series(dtype=float)})
        table = Table(df)
        with self.assertRaises(ValueError):
            self._run_task(table)

    def test_single_row_raises(self):
        """ValueError raised when insufficient samples for PCA."""
        df = pd.DataFrame({"Medium": ["M1"], "Val1": [1.0], "Val2": [2.0]})
        table = Table(df)
        with self.assertRaises(ValueError):
            self._run_task(table)

    def test_no_numeric_columns_raises(self):
        """ValueError raised when all columns are excluded."""
        table = self._make_medium_table()
        with self.assertRaises(ValueError):
            self._run_task(
                table,
                {
                    "columns_to_exclude": ["Glucose", "Nitrogen", "Phosphate"],
                },
            )
