"""
Test for CellCultureMediumTableFilter task
"""
import pandas as pd
from unittest import TestCase
from gws_core import TaskRunner, Table
from gws_plate_reader.fermentalg_analysis import CellCultureMediumTableFilter


class TestCellCultureMediumTableFilter(TestCase):
    """Test CellCultureMediumTableFilter task"""

    def test_filter_selected_medium(self):
        """Test filtering with selected medium"""

        # Create test data
        data = {
            'MILIEU': ['Medium A', 'Medium B', 'Medium C', 'Medium D'],
            'Glucose (g/L)': [10.0, 15.0, 20.0, 25.0],
            'NaCl (g/L)': [5.0, 6.0, 7.0, 8.0],
            'pH': [7.0, 7.2, 7.4, 7.6]
        }
        df = pd.DataFrame(data)
        input_table = Table(df)
        input_table.name = "Test Medium Table"

        # Run task with selection
        runner = TaskRunner(
            task_type=CellCultureMediumTableFilter,
            params={
                'medium_column': 'MILIEU',
                'selected_medium': ['Medium A', 'Medium C']
            },
            inputs={'medium_table': input_table}
        )
        outputs = runner.run()

        # Validate output
        filtered_table = outputs['filtered_table']
        filtered_df = filtered_table.get_data()

        # Should have 2 rows
        self.assertEqual(len(filtered_df), 2)

        # Should contain only Medium A and C
        self.assertIn('Medium A', filtered_df['MILIEU'].values)
        self.assertIn('Medium C', filtered_df['MILIEU'].values)
        self.assertNotIn('Medium B', filtered_df['MILIEU'].values)
        self.assertNotIn('Medium D', filtered_df['MILIEU'].values)

        # Check values
        medium_a_row = filtered_df[filtered_df['MILIEU'] == 'Medium A'].iloc[0]
        self.assertEqual(medium_a_row['Glucose (g/L)'], 10.0)
        self.assertEqual(medium_a_row['NaCl (g/L)'], 5.0)

    def test_filter_empty_selection(self):
        """Test that empty selection keeps all medium"""

        # Create test data
        data = {
            'MILIEU': ['Medium A', 'Medium B', 'Medium C'],
            'Glucose (g/L)': [10.0, 15.0, 20.0],
            'pH': [7.0, 7.2, 7.4]
        }
        df = pd.DataFrame(data)
        input_table = Table(df)

        # Run task with empty selection
        runner = TaskRunner(
            task_type=CellCultureMediumTableFilter,
            params={
                'medium_column': 'MILIEU',
                'selected_medium': []
            },
            inputs={'medium_table': input_table}
        )
        outputs = runner.run()

        # Validate output
        filtered_table = outputs['filtered_table']
        filtered_df = filtered_table.get_data()

        # Should have all 3 rows
        self.assertEqual(len(filtered_df), 3)
        self.assertEqual(list(filtered_df['MILIEU'].values), ['Medium A', 'Medium B', 'Medium C'])

    def test_filter_nonexistent_medium(self):
        """Test filtering with medium that don't exist"""

        # Create test data
        data = {
            'MILIEU': ['Medium A', 'Medium B'],
            'Glucose (g/L)': [10.0, 15.0]
        }
        df = pd.DataFrame(data)
        input_table = Table(df)

        # Run task selecting non-existent medium
        runner = TaskRunner(
            task_type=CellCultureMediumTableFilter,
            params={
                'medium_column': 'MILIEU',
                'selected_medium': ['Medium A', 'Medium X', 'Medium Y']  # X and Y don't exist
            },
            inputs={'medium_table': input_table}
        )
        outputs = runner.run()

        # Validate output
        filtered_table = outputs['filtered_table']
        filtered_df = filtered_table.get_data()

        # Should have only 1 row (Medium A)
        self.assertEqual(len(filtered_df), 1)
        self.assertEqual(filtered_df['MILIEU'].values[0], 'Medium A')

    def test_invalid_column(self):
        """Test that invalid column name raises error"""

        # Create test data
        data = {
            'MILIEU': ['Medium A', 'Medium B'],
            'Glucose (g/L)': [10.0, 15.0]
        }
        df = pd.DataFrame(data)
        input_table = Table(df)

        # Run task with invalid column name
        runner = TaskRunner(
            task_type=CellCultureMediumTableFilter,
            params={
                'medium_column': 'INVALID_COLUMN',
                'selected_medium': ['Medium A']
            },
            inputs={'medium_table': input_table}
        )

        # Should raise ValueError
        with self.assertRaises(ValueError) as context:
            runner.run()

        self.assertIn('INVALID_COLUMN', str(context.exception))
