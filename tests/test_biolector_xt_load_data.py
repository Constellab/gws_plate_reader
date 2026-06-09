import os

from gws_core import (
    BaseTestCase,
    Compress,
    DynamicInputs,
    File,
    Folder,
    InputSpec,
    ResourceSet,
    Settings,
    Table,
    TableImporter,
    TaskRunner,
)
from gws_plate_reader.biolector_xt.biolector_xt_mock_service import BiolectorXTMockService
from gws_plate_reader.biolector_xt_data_parser import BiolectorXTLoadData


class TestBiolectorXTLoadData(BaseTestCase):
    """Test BiolectorXTLoadData task."""

    def _prepare_plate_resource_set(self) -> tuple[ResourceSet, str]:
        """Download mock data, extract it, and return a plate ResourceSet with tmp_dir."""
        mock_service = BiolectorXTMockService()
        experiment_zip_path = mock_service.download_experiment("Test")

        tmp_dir = Settings.make_temp_dir()
        Compress.smart_decompress(experiment_zip_path, tmp_dir)

        csv_file = None
        for file_name in os.listdir(tmp_dir):
            if file_name.endswith(".csv"):
                csv_file = os.path.join(tmp_dir, file_name)
                break

        self.assertIsNotNone(csv_file, "CSV file should be found in test data")

        raw_data_table = TableImporter.call(
            File(csv_file or ""),
            {
                "file_format": "csv",
                "delimiter": ";",
                "header": 0,
                "format_header_names": True,
                "index_column": -1,
            },
        )

        folder_metadata = Folder(tmp_dir)

        plate_resource_set = ResourceSet()
        plate_resource_set.add_resource(raw_data_table, "raw_data")
        plate_resource_set.add_resource(folder_metadata, "folder_metadata")

        return plate_resource_set, tmp_dir

    def _run_task(self, plate_resource_set: ResourceSet, params: dict | None = None) -> dict:
        """Run BiolectorXTLoadData with the given plate ResourceSet and return outputs."""
        runner = TaskRunner(
            task_type=BiolectorXTLoadData,
            inputs={"source": plate_resource_set},
            input_specs=DynamicInputs(
                default_specs={"source": InputSpec(ResourceSet)},
            ),
            params=params or {},
        )
        return runner.run()

    def test_biolector_xt_load_data_basic(self):
        """Test basic functionality of BiolectorXTLoadData."""
        plate_resource_set, _ = self._prepare_plate_resource_set()
        outputs = self._run_task(plate_resource_set)

        # Verify outputs
        self.assertIn("resource_set", outputs)
        self.assertIn("venn_diagram", outputs)
        self.assertIn("metadata_table", outputs)

        # Check parsed data tables
        resource_set = outputs["resource_set"]
        self.assertIsNotNone(resource_set)
        resources = resource_set.get_resources()
        self.assertGreater(len(resources), 0, "Should have at least one parsed table")

        # Check that tables have proper structure
        for _table_name, table in resources.items():
            df = table.get_data()
            self.assertIn("Time", df.columns, "Table should have 'Time' column (hours)")

            # Check that we have at least one measurement column
            measurement_cols = [col for col in df.columns if col != "Time"]
            self.assertGreater(len(measurement_cols), 0, "Should have measurement columns")

        # Check that batch and sample tags are set on tables
        first_table = list(resources.values())[0]
        self.assertGreater(
            len(first_table.tags.get_by_key("batch")), 0, "Table should have 'batch' tag"
        )
        self.assertGreater(
            len(first_table.tags.get_by_key("sample")), 0, "Table should have 'sample' tag"
        )

        # Check Venn diagram
        venn_diagram = outputs["venn_diagram"]
        if venn_diagram:
            self.assertIsNotNone(venn_diagram.get_figure())

        # Check metadata table
        metadata_table = outputs["metadata_table"]
        if metadata_table:
            self.assertIsInstance(metadata_table, Table)
            self.assertGreater(len(metadata_table.get_data()), 0, "Metadata table should have rows")

    def test_biolector_xt_load_data_with_custom_plate_name(self):
        """Test BiolectorXTLoadData with a custom plate name."""
        plate_resource_set, _ = self._prepare_plate_resource_set()
        outputs = self._run_task(plate_resource_set, params={"plate_names": ["my_plate"]})

        self.assertIn("resource_set", outputs)
        resource_set = outputs["resource_set"]
        resources = resource_set.get_resources()
        self.assertGreater(len(resources), 0, "Should have at least one parsed table")

        # All resource names should be prefixed with the custom plate name
        for well_name in resources:
            self.assertTrue(
                well_name.startswith("my_plate_"),
                f"Well name '{well_name}' should start with 'my_plate_'",
            )

        # All batch tags should use the custom plate name
        for _, table in resources.items():
            batch_tags = table.tags.get_by_key("batch")
            if batch_tags:
                self.assertEqual(
                    batch_tags[0].value, "my_plate", "Batch tag should match the custom plate name"
                )
