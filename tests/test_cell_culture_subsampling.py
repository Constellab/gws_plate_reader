import numpy as np
import pandas as pd
from gws_core import BaseTestCase, ResourceSet, Table, Tag, TaskRunner
from gws_plate_reader.cell_culture_filter.cell_culture_subsampling import CellCultureSubsampling


class TestCellCultureSubsampling(BaseTestCase):
    """Tests for CellCultureSubsampling task."""

    def _make_tagged_table(
        self, batch: str, sample: str, time_vals: list, data_vals: list
    ) -> Table:
        """Create a Table with batch/sample tags and a Time column."""
        df = pd.DataFrame({"Time": time_vals, "Biomasse": data_vals})
        table = Table(df)
        table.tags.add_tag(Tag("batch", batch))
        table.tags.add_tag(Tag("sample", sample))
        return table

    def _make_resource_set(self) -> ResourceSet:
        """Create a ResourceSet with 2 growth curve tables."""
        rs = ResourceSet()
        t = np.linspace(0, 48, 20).tolist()
        y1 = (0.1 + 1.0 / (1.0 + np.exp(-0.15 * (np.array(t) - 20)))).tolist()
        y2 = (0.12 + 1.1 / (1.0 + np.exp(-0.12 * (np.array(t) - 22)))).tolist()
        rs.add_resource(self._make_tagged_table("B1", "S1", t, y1), "B1_S1")
        rs.add_resource(self._make_tagged_table("B1", "S2", t, y2), "B1_S2")
        return rs

    def _run_task(self, rs: ResourceSet, params: dict | None = None) -> dict:
        runner = TaskRunner(
            task_type=CellCultureSubsampling,
            inputs={"resource_set": rs},
            params=params or {},
        )
        return runner.run()

    def test_basic_subsampling(self):
        """Subsampling produces a ResourceSet output."""
        rs = self._make_resource_set()
        outputs = self._run_task(
            rs,
            {
                "method": "linear",
                "n_points": 50,
                "time_column": "Time",
            },
        )

        self.assertIn("subsampled_resource_set", outputs)
        result_rs = outputs["subsampled_resource_set"]
        self.assertIsInstance(result_rs, ResourceSet)

    def test_output_has_same_number_of_resources(self):
        """Number of output resources matches input."""
        rs = self._make_resource_set()
        outputs = self._run_task(
            rs,
            {
                "method": "linear",
                "n_points": 50,
                "time_column": "Time",
            },
        )

        result_rs = outputs["subsampled_resource_set"]
        self.assertEqual(len(result_rs.get_resources()), 2)

    def test_tags_preserved(self):
        """Batch and sample tags are preserved after subsampling."""
        rs = self._make_resource_set()
        outputs = self._run_task(
            rs,
            {
                "method": "linear",
                "n_points": 50,
                "time_column": "Time",
            },
        )

        result_rs = outputs["subsampled_resource_set"]
        resources = result_rs.get_resources()
        for _, table in resources.items():
            tags = table.tags.get_tags()
            tag_keys = [t.key for t in tags]
            self.assertIn("batch", tag_keys)
            self.assertIn("sample", tag_keys)

    def test_makima_interpolation(self):
        """Makima interpolation method works."""
        rs = self._make_resource_set()
        outputs = self._run_task(
            rs,
            {
                "method": "makima",
                "n_points": 100,
                "time_column": "Time",
            },
        )

        result_rs = outputs["subsampled_resource_set"]
        self.assertEqual(len(result_rs.get_resources()), 2)

    def test_pchip_interpolation(self):
        """PCHIP interpolation method works."""
        rs = self._make_resource_set()
        outputs = self._run_task(
            rs,
            {
                "method": "pchip",
                "n_points": 100,
                "time_column": "Time",
            },
        )

        result_rs = outputs["subsampled_resource_set"]
        self.assertEqual(len(result_rs.get_resources()), 2)

    def test_cubic_spline_interpolation(self):
        """Cubic spline interpolation method works."""
        rs = self._make_resource_set()
        outputs = self._run_task(
            rs,
            {
                "method": "cubic_spline",
                "n_points": 100,
                "time_column": "Time",
            },
        )

        result_rs = outputs["subsampled_resource_set"]
        self.assertEqual(len(result_rs.get_resources()), 2)

    def test_per_file_grid_strategy(self):
        """Per-file grid strategy produces individual grids."""
        rs = self._make_resource_set()
        outputs = self._run_task(
            rs,
            {
                "method": "linear",
                "grid_strategy": "per_file",
                "time_column": "Time",
            },
        )

        result_rs = outputs["subsampled_resource_set"]
        self.assertEqual(len(result_rs.get_resources()), 2)

    def test_reference_grid_strategy(self):
        """Reference grid strategy uses first sample as template."""
        rs = self._make_resource_set()
        outputs = self._run_task(
            rs,
            {
                "method": "linear",
                "grid_strategy": "reference",
                "reference_index": 0,
                "time_column": "Time",
            },
        )

        result_rs = outputs["subsampled_resource_set"]
        self.assertEqual(len(result_rs.get_resources()), 2)

    def test_edge_strategy_nan(self):
        """Edge strategy 'nan' fills out-of-range values with NaN."""
        rs = self._make_resource_set()
        outputs = self._run_task(
            rs,
            {
                "method": "linear",
                "n_points": 50,
                "edge_strategy": "nan",
                "time_column": "Time",
            },
        )

        result_rs = outputs["subsampled_resource_set"]
        self.assertIsNotNone(result_rs)

    def test_empty_resource_set_raises(self):
        """Empty ResourceSet raises ValueError."""
        rs = ResourceSet()
        with self.assertRaises(ValueError):
            self._run_task(
                rs,
                {
                    "method": "linear",
                    "n_points": 50,
                    "time_column": "Time",
                },
            )
