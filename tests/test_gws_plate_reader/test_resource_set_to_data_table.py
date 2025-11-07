"""
Unit tests for ResourceSetToDataTable task
"""
import pandas as pd

from gws_core import BaseTestCase, TaskRunner, Table, ResourceSet
from gws_plate_reader.fermentalg_analysis import ResourceSetToDataTable


class TestResourceSetToDataTable(BaseTestCase):
    """Test cases for ResourceSet to Data Table conversion task"""

    def test_basic_conversion(self):
        """Test basic conversion of ResourceSet to Table"""

        # Create sample data for 3 batch/sample combinations
        data1 = pd.DataFrame({
            'Temp': [20, 25, 30, 35],
            'Biomasse': [0.1, 0.3, 0.5, 0.7],
            'pH': [7.0, 7.1, 7.2, 7.3]
        })

        data2 = pd.DataFrame({
            'Temp': [20, 25, 30, 35],
            'Biomasse': [0.12, 0.28, 0.52, 0.68],
            'pH': [6.9, 7.0, 7.1, 7.2]
        })

        data3 = pd.DataFrame({
            'Temp': [20, 25, 30, 35],
            'Biomasse': [0.11, 0.32, 0.48, 0.72],
            'pH': [7.1, 7.2, 7.3, 7.4]
        })

        # Create Table resources with tags
        table1 = Table(data=data1)
        table1.add_tag("fermentor_batch", "Batch1")
        table1.add_tag("fermentor_sample", "Sample1")

        table2 = Table(data=data2)
        table2.add_tag("fermentor_batch", "Batch1")
        table2.add_tag("fermentor_sample", "Sample2")

        table3 = Table(data=data3)
        table3.add_tag("fermentor_batch", "Batch2")
        table3.add_tag("fermentor_sample", "Sample1")

        # Create ResourceSet
        resource_set = ResourceSet()
        resource_set.add_resource(table1, "Table_B1_S1")
        resource_set.add_resource(table2, "Table_B1_S2")
        resource_set.add_resource(table3, "Table_B2_S1")

        # Run task
        runner = TaskRunner(
            task_type=ResourceSetToDataTable,
            params={
                'index_column': 'Temp',
                'data_column': 'Biomasse'
            },
            inputs={'resource_set': resource_set}
        )
        outputs = runner.run()

        # Validate output
        self.assertIn('data_table', outputs)
        result_table = outputs['data_table']
        result_df = result_table.get_data()

        # Check structure
        self.assertIn('Temp', result_df.columns)
        self.assertIn('Batch1_Sample1', result_df.columns)
        self.assertIn('Batch1_Sample2', result_df.columns)
        self.assertIn('Batch2_Sample1', result_df.columns)

        # Should have 4 temperature points
        self.assertEqual(len(result_df), 4)

        # Check first row values
        first_row = result_df.iloc[0]
        self.assertEqual(first_row['Temp'], 20)
        self.assertAlmostEqual(first_row['Batch1_Sample1'], 0.1, places=2)
        self.assertAlmostEqual(first_row['Batch1_Sample2'], 0.12, places=2)
        self.assertAlmostEqual(first_row['Batch2_Sample1'], 0.11, places=2)

    def test_missing_values_handling(self):
        """Test that NaN values in index column are properly removed"""

        data1 = pd.DataFrame({
            'Time': [0, 24, None, 72],  # NaN in index
            'Biomasse': [0.1, 0.3, 0.5, 0.7]
        })

        data2 = pd.DataFrame({
            'Time': [0, 24, 48, 72],
            'Biomasse': [0.12, 0.28, 0.52, 0.68]
        })

        table1 = Table(data=data1)
        table1.add_tag("fermentor_batch", "B1")
        table1.add_tag("fermentor_sample", "S1")

        table2 = Table(data=data2)
        table2.add_tag("fermentor_batch", "B1")
        table2.add_tag("fermentor_sample", "S2")

        resource_set = ResourceSet()
        resource_set.add_resource(table1, "T1")
        resource_set.add_resource(table2, "T2")

        runner = TaskRunner(
            task_type=ResourceSetToDataTable,
            params={
                'index_column': 'Time',
                'data_column': 'Biomasse'
            },
            inputs={'resource_set': resource_set}
        )
        outputs = runner.run()

        result_df = outputs['data_table'].get_data()

        # Should have 4 rows (0, 24, 48, 72) with outer join
        self.assertEqual(len(result_df), 4)

        # Check that Time values are all valid (no NaN)
        self.assertFalse(result_df['Time'].isna().any())

    def test_different_time_points(self):
        """Test merging tables with different time points using outer join"""

        data1 = pd.DataFrame({
            'Time': [0, 24, 48],
            'pH': [7.0, 7.1, 7.2]
        })

        data2 = pd.DataFrame({
            'Time': [0, 12, 24, 36, 48],
            'pH': [6.9, 7.0, 7.1, 7.15, 7.2]
        })

        table1 = Table(data=data1)
        table1.add_tag("fermentor_batch", "A")
        table1.add_tag("fermentor_sample", "1")

        table2 = Table(data=data2)
        table2.add_tag("fermentor_batch", "A")
        table2.add_tag("fermentor_sample", "2")

        resource_set = ResourceSet()
        resource_set.add_resource(table1, "T1")
        resource_set.add_resource(table2, "T2")

        runner = TaskRunner(
            task_type=ResourceSetToDataTable,
            params={
                'index_column': 'Time',
                'data_column': 'pH'
            },
            inputs={'resource_set': resource_set}
        )
        outputs = runner.run()

        result_df = outputs['data_table'].get_data()

        # Should have 5 unique time points (0, 12, 24, 36, 48)
        self.assertEqual(len(result_df), 5)

        # Check that missing values are NaN for A_1 at times 12 and 36
        time_12_row = result_df[result_df['Time'] == 12].iloc[0]
        self.assertTrue(pd.isna(time_12_row['A_1']))
        self.assertFalse(pd.isna(time_12_row['A_2']))

    def test_missing_column_handling(self):
        """Test error handling when required columns are missing"""

        # Table without the required data column
        data = pd.DataFrame({
            'Temp': [20, 25, 30],
            'OtherColumn': [1, 2, 3]
        })

        table = Table(data=data)
        table.add_tag("fermentor_batch", "B1")
        table.add_tag("fermentor_sample", "S1")

        resource_set = ResourceSet()
        resource_set.add_resource(table, "T1")

        runner = TaskRunner(
            task_type=ResourceSetToDataTable,
            params={
                'index_column': 'Temp',
                'data_column': 'Biomasse'  # This column doesn't exist
            },
            inputs={'resource_set': resource_set}
        )

        # Should raise an error because no valid data could be extracted
        with self.assertRaises(ValueError):
            runner.run()

    def test_no_tags_fallback(self):
        """Test that resource name is used when batch/sample tags are missing"""

        data = pd.DataFrame({
            'X': [1, 2, 3],
            'Y': [10, 20, 30]
        })

        table = Table(data=data)
        # No tags added

        resource_set = ResourceSet()
        resource_set.add_resource(table, "MyTable")

        runner = TaskRunner(
            task_type=ResourceSetToDataTable,
            params={
                'index_column': 'X',
                'data_column': 'Y'
            },
            inputs={'resource_set': resource_set}
        )
        outputs = runner.run()

        result_df = outputs['data_table'].get_data()

        # Column should be named "MyTable" instead of "Batch_Sample"
        self.assertIn('MyTable', result_df.columns)
        self.assertEqual(len(result_df), 3)
