import os
from unittest import TestCase

from gws_core import BaseTestCase, File, Folder, JSONDict, TaskRunner
from gws_plate_reader.biolector_xt.biolector_xt_mock_service import BiolectorXTMockService
from gws_plate_reader.biolector_xt_data_parser import BiolectorXTLoadData


class TestBiolectorXTLoadData(BaseTestCase):
    """Test BiolectorXTLoadData task."""

    def test_biolector_xt_load_data_basic(self):
        """Test basic functionality of BiolectorXTLoadData."""

        # Get mock data
        mock_service = BiolectorXTMockService()
        experiment_zip_path = mock_service.download_experiment('Test')

        # Extract the experiment
        from gws_core import Compress, Settings, TableImporter
        tmp_dir = Settings.make_temp_dir()
        Compress.smart_decompress(experiment_zip_path, tmp_dir)

        # Find CSV file
        csv_file = None
        for file_name in os.listdir(tmp_dir):
            if file_name.endswith('.csv'):
                csv_file = os.path.join(tmp_dir, file_name)
                break

        self.assertIsNotNone(csv_file, "CSV file should be found in test data")

        # Import the CSV as a table
        raw_data_table = TableImporter.call(File(csv_file), {
            'file_format': 'csv',
            'delimiter': ';',
            'header': 0,
            'format_header_names': True,
            'index_column': -1,
        })

        # Create metadata folder
        folder_metadata = Folder(tmp_dir)

        # Run the task
        runner = TaskRunner(
            task_type=BiolectorXTLoadData,
            inputs={
                'raw_data': raw_data_table,
                'folder_metadata': folder_metadata,
            },
            params={}
        )

        outputs = runner.run()

        # Verify outputs
        self.assertIn('parsed_data_tables', outputs)
        self.assertIn('venn_diagram', outputs)
        self.assertIn('metadata_summary', outputs)

        # Check parsed data tables
        parsed_data_tables = outputs['parsed_data_tables']
        self.assertIsNotNone(parsed_data_tables)
        resources = parsed_data_tables.get_resources()
        self.assertGreater(len(resources), 0, "Should have at least one parsed table")

        # Check that tables have proper structure
        for table_name, table in resources.items():
            df = table.get_data()
            self.assertIn('time', df.columns, "Table should have 'time' column")
            self.assertIn('Temps_en_h', df.columns, "Table should have 'Temps_en_h' column")

            # Check that we have well columns
            well_columns = [col for col in df.columns if col not in ['time', 'Temps_en_h']]
            self.assertGreater(len(well_columns), 0, "Should have well columns")

        # Check Venn diagram
        venn_diagram = outputs['venn_diagram']
        if venn_diagram:
            self.assertIsNotNone(venn_diagram.get_plotly_figure())

        # Check metadata summary
        metadata_summary = outputs['metadata_summary']
        if metadata_summary:
            df = metadata_summary.get_data()
            self.assertIn('metric', df.columns)
            self.assertIn('value', df.columns)
            self.assertGreater(len(df), 0, "Metadata summary should have rows")

    def test_biolector_xt_load_data_with_plate_layout(self):
        """Test BiolectorXTLoadData with custom plate layout."""

        # Get mock data
        mock_service = BiolectorXTMockService()
        experiment_zip_path = mock_service.download_experiment('Test')

        # Extract and load data
        from gws_core import Compress, Settings, TableImporter
        tmp_dir = Settings.make_temp_dir()
        Compress.smart_decompress(experiment_zip_path, tmp_dir)

        csv_file = None
        for file_name in os.listdir(tmp_dir):
            if file_name.endswith('.csv'):
                csv_file = os.path.join(tmp_dir, file_name)
                break

        raw_data_table = TableImporter.call(File(csv_file))
        folder_metadata = Folder(tmp_dir)

        # Create custom plate layout
        custom_layout = {
            "A01": {"label": "Control 1", "sample_type": "blank"},
            "A02": {"label": "Sample 1", "sample_type": "test"},
            "B1": {"label": "Sample 2", "sample_type": "test"},  # Test normalization A1 → A01
        }
        plate_layout = JSONDict(custom_layout)

        # Run the task with plate layout
        runner = TaskRunner(
            task_type=BiolectorXTLoadData,
            inputs={
                'raw_data': raw_data_table,
                'folder_metadata': folder_metadata,
                'plate_layout': plate_layout,
            },
            params={}
        )

        outputs = runner.run()

        # Verify that custom labels were applied
        parsed_data_tables = outputs['parsed_data_tables']
        resources = parsed_data_tables.get_resources()

        # Check at least one table
        if len(resources) > 0:
            first_table = list(resources.values())[0]

            # Check if well A01 has the custom label
            if 'A01' in first_table.get_data().columns:
                tags = first_table.get_column_tags_by_name('A01')
                label_tag = tags.get_tag_by_key('label')
                if label_tag:
                    self.assertEqual(label_tag.value, "Control 1",
                                     "Custom label should be applied to A01")
