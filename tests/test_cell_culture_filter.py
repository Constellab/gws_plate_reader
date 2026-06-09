import pandas as pd
from gws_core import BaseTestCase, ResourceSet, Table, Tag, TaskRunner
from gws_plate_reader.cell_culture_filter.cell_culture_filter import (
    FilterFermentorAnalyseLoadedResourceSetBySelection,
)


class TestFilterFermentorAnalyseLoadedResourceSetBySelection(BaseTestCase):
    """Tests for FilterFermentorAnalyseLoadedResourceSetBySelection task."""

    def _make_tagged_table(self, batch: str, sample: str) -> Table:
        """Create a simple tagged Table."""
        df = pd.DataFrame({"Time": [0, 24, 48], "Biomasse": [0.1, 0.5, 1.0]})
        table = Table(df)
        table.tags.add_tag(Tag("batch", batch))
        table.tags.add_tag(Tag("sample", sample))
        return table

    def _make_resource_set(self) -> ResourceSet:
        """Create a ResourceSet with 4 tables."""
        rs = ResourceSet()
        rs.add_resource(self._make_tagged_table("B1", "S1"), "B1_S1")
        rs.add_resource(self._make_tagged_table("B1", "S2"), "B1_S2")
        rs.add_resource(self._make_tagged_table("B2", "S1"), "B2_S1")
        rs.add_resource(self._make_tagged_table("B2", "S2"), "B2_S2")
        return rs

    def _run_task(self, rs: ResourceSet, selection: list[dict]) -> dict:
        runner = TaskRunner(
            task_type=FilterFermentorAnalyseLoadedResourceSetBySelection,
            inputs={"resource_set": rs},
            params={"selection_criteria": selection},
        )
        return runner.run()

    def test_filter_by_single_selection(self):
        """Selecting one batch/sample pair returns exactly one table."""
        rs = self._make_resource_set()
        outputs = self._run_task(rs, [{"batch": "B1", "sample": "S1"}])

        filtered = outputs["filtered_resource_set"]
        resources = filtered.get_resources()
        self.assertEqual(len(resources), 1)

    def test_filter_by_multiple_selections(self):
        """Selecting two batch/sample pairs returns exactly two tables."""
        rs = self._make_resource_set()
        outputs = self._run_task(
            rs,
            [
                {"batch": "B1", "sample": "S1"},
                {"batch": "B2", "sample": "S2"},
            ],
        )

        filtered = outputs["filtered_resource_set"]
        resources = filtered.get_resources()
        self.assertEqual(len(resources), 2)

    def test_tags_preserved_in_output(self):
        """Filtered tables preserve their original tags."""
        rs = self._make_resource_set()
        outputs = self._run_task(rs, [{"batch": "B1", "sample": "S1"}])

        filtered = outputs["filtered_resource_set"]
        resources = filtered.get_resources()
        table = list(resources.values())[0]

        batch_tags = [t for t in table.tags.get_tags() if t.key == "batch"]
        sample_tags = [t for t in table.tags.get_tags() if t.key == "sample"]
        self.assertEqual(len(batch_tags), 1)
        self.assertEqual(batch_tags[0].value, "B1")
        self.assertEqual(sample_tags[0].value, "S1")

    def test_data_preserved_in_output(self):
        """Filtered tables contain the original data."""
        rs = self._make_resource_set()
        outputs = self._run_task(rs, [{"batch": "B1", "sample": "S1"}])

        filtered = outputs["filtered_resource_set"]
        resources = filtered.get_resources()
        table = list(resources.values())[0]
        df = table.get_data()
        self.assertEqual(len(df), 3)
        self.assertIn("Time", df.columns)
        self.assertIn("Biomasse", df.columns)

    def test_no_match_returns_empty(self):
        """Selecting a non-existent batch/sample returns empty ResourceSet."""
        rs = self._make_resource_set()
        outputs = self._run_task(rs, [{"batch": "NONEXISTENT", "sample": "S1"}])

        filtered = outputs["filtered_resource_set"]
        resources = filtered.get_resources()
        self.assertEqual(len(resources), 0)

    def test_resource_without_tags_skipped(self):
        """Resources without tags are skipped without error."""
        rs = ResourceSet()
        # Table with no tags
        table_no_tags = Table(pd.DataFrame({"Time": [0, 24], "Val": [1, 2]}))
        rs.add_resource(table_no_tags, "no_tags")
        # Table with tags
        rs.add_resource(self._make_tagged_table("B1", "S1"), "B1_S1")

        outputs = self._run_task(rs, [{"batch": "B1", "sample": "S1"}])
        filtered = outputs["filtered_resource_set"]
        resources = filtered.get_resources()
        self.assertEqual(len(resources), 1)

    def test_case_sensitive_matching(self):
        """Tag matching is case-sensitive."""
        rs = self._make_resource_set()
        outputs = self._run_task(rs, [{"batch": "b1", "sample": "s1"}])

        filtered = outputs["filtered_resource_set"]
        resources = filtered.get_resources()
        self.assertEqual(len(resources), 0)  # lowercase doesn't match uppercase
