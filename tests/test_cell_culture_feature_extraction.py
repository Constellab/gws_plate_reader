import numpy as np
import pandas as pd
from gws_core import BaseTestCase, ResourceSet, Table, TaskRunner
from gws_plate_reader.cell_culture_analysis.cell_culture_feature_extraction import (
    CellCultureFeatureExtraction,
)


class TestCellCultureFeatureExtraction(BaseTestCase):
    """Tests for CellCultureFeatureExtraction task."""

    @staticmethod
    def _logistic_curve(t, y0=0.1, A=1.2, mu=0.15, lag=10.0):
        """Generate synthetic logistic growth data."""
        return y0 + (A - y0) / (1.0 + np.exp(-mu * (t - lag)))

    def _make_data_table(self, n_series: int = 2) -> Table:
        """Create a data table with logistic growth curves."""
        rng = np.random.default_rng(42)
        t = np.linspace(0, 48, 25)
        data = {"Time": t}
        for i in range(n_series):
            y = self._logistic_curve(
                t,
                y0=0.05 + 0.05 * i,
                A=1.0 + 0.2 * i,
                mu=0.12 + 0.03 * i,
                lag=8.0 + 2.0 * i,
            )
            noise = rng.normal(0, 0.01, len(t))
            data[f"Sample_{i}"] = y + noise
        return Table(pd.DataFrame(data))

    def _run_task(self, table: Table, params: dict | None = None) -> dict:
        runner = TaskRunner(
            task_type=CellCultureFeatureExtraction,
            inputs={"data_table": table},
            params=params or {},
        )
        return runner.run()

    def test_basic_outputs(self):
        """Task produces results_table and plots."""
        table = self._make_data_table(1)
        outputs = self._run_task(table, {"models_to_fit": ["Logistic_4P"]})

        self.assertIn("results_table", outputs)
        self.assertIn("plots", outputs)

    def test_results_table_has_rows(self):
        """Results table contains one row per series×model."""
        table = self._make_data_table(2)
        models = ["Logistic_4P", "Gompertz_4P"]
        outputs = self._run_task(table, {"models_to_fit": models})

        df = outputs["results_table"].get_data()
        # 2 series × 2 models = 4 rows
        self.assertEqual(len(df), 4)

    def test_results_contain_key_columns(self):
        """Results table has Series, Model, parameter, and metric columns."""
        table = self._make_data_table(1)
        outputs = self._run_task(table, {"models_to_fit": ["Logistic_4P"]})

        df = outputs["results_table"].get_data()
        # Check for key columns
        self.assertIn("Series", df.columns)
        self.assertIn("Model", df.columns)
        self.assertIn("R2", df.columns)
        self.assertIn("param_y0", df.columns)
        self.assertIn("param_A", df.columns)
        self.assertIn("param_mu", df.columns)
        self.assertIn("param_lag", df.columns)

    def test_logistic_fit_r2_is_high(self):
        """Fitting a logistic model to logistic data should yield R² > 0.95."""
        table = self._make_data_table(1)
        outputs = self._run_task(table, {"models_to_fit": ["Logistic_4P"]})

        df = outputs["results_table"].get_data()
        r2 = df["R2"].iloc[0]
        self.assertGreater(r2, 0.95, f"Expected R² > 0.95, got {r2}")

    def test_plots_resource_set(self):
        """Plots output is a ResourceSet with model fit plots."""
        table = self._make_data_table(1)
        outputs = self._run_task(table, {"models_to_fit": ["Logistic_4P"]})

        plots = outputs["plots"]
        self.assertIsInstance(plots, ResourceSet)
        resources = plots.get_resources()
        self.assertGreater(len(resources), 0)

    def test_all_models_produce_results(self):
        """All 6 models can be fitted."""
        table = self._make_data_table(1)
        all_models = CellCultureFeatureExtraction.ALL_MODELS
        outputs = self._run_task(table, {"models_to_fit": all_models})

        df = outputs["results_table"].get_data()
        fitted_models = set(df["Model"].unique())
        self.assertEqual(fitted_models, set(all_models))

    def test_insufficient_data_skipped(self):
        """Series with < 5 data points are skipped."""
        # Create table with only 3 valid points
        df = pd.DataFrame(
            {
                "Time": [0, 24, 48],
                "Sample_0": [0.1, 0.5, 1.0],
            }
        )
        table = Table(df)
        # Task should raise or produce empty results since all series < 5 points
        with self.assertRaises(ValueError):
            self._run_task(table, {"models_to_fit": ["Logistic_4P"]})

    def test_single_column_raises(self):
        """Table with only index column (no data columns) raises ValueError."""
        df = pd.DataFrame({"Time": [0, 24, 48]})
        table = Table(df)
        with self.assertRaises(ValueError):
            self._run_task(table, {"models_to_fit": ["Logistic_4P"]})

    def test_growth_intervals_in_results(self):
        """Results include growth interval columns (t5, t50, t95, etc.)."""
        table = self._make_data_table(1)
        outputs = self._run_task(table, {"models_to_fit": ["Logistic_4P"]})

        df = outputs["results_table"].get_data()
        for col in ["t5", "t50", "t95", "Delta_t_10_90"]:
            self.assertIn(col, df.columns, f"Missing growth interval column: {col}")

    def test_results_tags(self):
        """Results table has analysis tags."""
        table = self._make_data_table(1)
        outputs = self._run_task(table, {"models_to_fit": ["Logistic_4P"]})

        results_table = outputs["results_table"]
        tags = results_table.tags.get_tags()
        tag_keys = [t.key for t in tags]
        self.assertIn("analysis_type", tag_keys)
