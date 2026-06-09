import pandas as pd
from gws_core import BaseTestCase, ResourceSet, Table, Tag, TaskRunner
from gws_plate_reader.cell_culture_analysis.resource_set_to_data_table import ResourceSetToDataTable


class TestResourceSetToDataTable(BaseTestCase):
    """Tests for ResourceSetToDataTable task."""

    def _make_tagged_table(
        self, batch: str, sample: str, time_vals: list, data_vals: list
    ) -> Table:
        """Create a Table with batch/sample tags."""
        df = pd.DataFrame({"Time": time_vals, "Biomasse": data_vals})
        table = Table(df)
        table.tags.add_tag(Tag("fermentor_batch", batch))
        table.tags.add_tag(Tag("fermentor_sample", sample))
        return table

    def _make_resource_set(self) -> ResourceSet:
        """Create a ResourceSet with 3 tables having different batch/sample combos."""
        rs = ResourceSet()
        rs.add_resource(
            self._make_tagged_table("B1", "S1", [0, 24, 48], [0.1, 0.5, 1.2]),
            "B1_S1",
        )
        rs.add_resource(
            self._make_tagged_table("B1", "S2", [0, 24, 48], [0.12, 0.48, 1.15]),
            "B1_S2",
        )
        rs.add_resource(
            self._make_tagged_table("B2", "S1", [0, 24, 48], [0.11, 0.52, 1.25]),
            "B2_S1",
        )
        return rs

    def _run_task(self, rs: ResourceSet, params: dict | None = None) -> dict:
        runner = TaskRunner(
            task_type=ResourceSetToDataTable,
            inputs={"resource_set": rs},
            params=params or {},
        )
        return runner.run()

    def test_basic_conversion(self):
        """ResourceSet with 3 tables converts to a table with Time + 3 data columns."""
        rs = self._make_resource_set()
        outputs = self._run_task(
            rs,
            {
                "index_column": "Time",
                "data_column": "Biomasse",
            },
        )

        data_table = outputs["data_table"]
        df = data_table.get_data()

        self.assertIn("Time", df.columns)
        # 3 data columns (one per batch/sample)
        data_cols = [c for c in df.columns if c != "Time"]
        self.assertEqual(len(data_cols), 3)
        self.assertEqual(len(df), 3)  # 3 time points

    def test_column_naming_from_tags(self):
        """Columns are named Batch_Sample from tags."""
        rs = self._make_resource_set()
        outputs = self._run_task(
            rs,
            {
                "index_column": "Time",
                "data_column": "Biomasse",
            },
        )

        df = outputs["data_table"].get_data()
        data_cols = [c for c in df.columns if c != "Time"]
        expected_cols = {"B1_S1", "B1_S2", "B2_S1"}
        self.assertEqual(set(data_cols), expected_cols)

    def test_sorted_by_index(self):
        """Output table is sorted by the index column."""
        rs = ResourceSet()
        rs.add_resource(
            self._make_tagged_table("B1", "S1", [48, 0, 24], [1.2, 0.1, 0.5]),
            "B1_S1",
        )
        outputs = self._run_task(
            rs,
            {
                "index_column": "Time",
                "data_column": "Biomasse",
            },
        )

        df = outputs["data_table"].get_data()
        self.assertEqual(list(df["Time"]), [0, 24, 48])

    def test_outer_join_preserves_all_time_points(self):
        """Tables with different time points are merged via outer join."""
        rs = ResourceSet()
        rs.add_resource(
            self._make_tagged_table("B1", "S1", [0, 24], [0.1, 0.5]),
            "B1_S1",
        )
        rs.add_resource(
            self._make_tagged_table("B1", "S2", [0, 48], [0.12, 1.15]),
            "B1_S2",
        )
        outputs = self._run_task(
            rs,
            {
                "index_column": "Time",
                "data_column": "Biomasse",
            },
        )

        df = outputs["data_table"].get_data()
        self.assertEqual(len(df), 3)  # 0, 24, 48

    def test_nan_in_index_removed(self):
        """Rows with NaN in the index column are dropped."""
        rs = ResourceSet()
        df_src = pd.DataFrame(
            {
                "Time": [0, None, 24],
                "Biomasse": [0.1, 0.3, 0.5],
            }
        )
        table = Table(df_src)
        table.tags.add_tag(Tag("fermentor_batch", "B1"))
        table.tags.add_tag(Tag("fermentor_sample", "S1"))
        rs.add_resource(table, "B1_S1")

        outputs = self._run_task(
            rs,
            {
                "index_column": "Time",
                "data_column": "Biomasse",
            },
        )

        df = outputs["data_table"].get_data()
        self.assertEqual(len(df), 2)

    def test_missing_index_column_skips_resource(self):
        """Resources missing the index column are skipped without error."""
        rs = ResourceSet()
        # Table without 'Time' column
        df_no_time = pd.DataFrame({"Temp": [20, 25], "Biomasse": [0.1, 0.5]})
        table1 = Table(df_no_time)
        table1.tags.add_tag(Tag("fermentor_batch", "B1"))
        table1.tags.add_tag(Tag("fermentor_sample", "S1"))
        rs.add_resource(table1, "B1_S1")

        # Table with 'Time' column
        rs.add_resource(
            self._make_tagged_table("B2", "S1", [0, 24], [0.1, 0.5]),
            "B2_S1",
        )

        outputs = self._run_task(
            rs,
            {
                "index_column": "Time",
                "data_column": "Biomasse",
            },
        )

        df = outputs["data_table"].get_data()
        data_cols = [c for c in df.columns if c != "Time"]
        self.assertEqual(len(data_cols), 1)

    def test_missing_data_column_skips_resource(self):
        """Resources missing the data column are skipped without error."""
        rs = ResourceSet()
        df_no_data = pd.DataFrame({"Time": [0, 24], "pH": [7.0, 6.5]})
        table1 = Table(df_no_data)
        table1.tags.add_tag(Tag("fermentor_batch", "B1"))
        table1.tags.add_tag(Tag("fermentor_sample", "S1"))
        rs.add_resource(table1, "B1_S1")

        rs.add_resource(
            self._make_tagged_table("B2", "S1", [0, 24], [0.1, 0.5]),
            "B2_S1",
        )

        outputs = self._run_task(
            rs,
            {
                "index_column": "Time",
                "data_column": "Biomasse",
            },
        )

        df = outputs["data_table"].get_data()
        data_cols = [c for c in df.columns if c != "Time"]
        self.assertEqual(len(data_cols), 1)

    def test_all_resources_missing_columns_raises(self):
        """ValueError raised when no resources have required columns."""
        rs = ResourceSet()
        df = pd.DataFrame({"Other": [1, 2], "Stuff": [3, 4]})
        table = Table(df)
        table.tags.add_tag(Tag("fermentor_batch", "B1"))
        table.tags.add_tag(Tag("fermentor_sample", "S1"))
        rs.add_resource(table, "B1_S1")

        with self.assertRaises(ValueError):
            self._run_task(
                rs,
                {
                    "index_column": "Time",
                    "data_column": "Biomasse",
                },
            )
