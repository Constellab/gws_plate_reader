import json
import math
import copy
import itertools
import numpy as np
from gws_core import Table, JSONDict

class TecanParser:
    def __init__(self, data_file: Table = None, plate_layout : JSONDict = None):
        """
        Initialize the TecanParser object with the data file.
        """
        super().__init__()

        if data_file is not None:
            self.data_file = data_file
            self.plate_layout = plate_layout

    def get_wells_tecan(self):
        # Generate all possible values from A1 to H12
        rows = [chr(i) for i in range(ord('A'), ord('H') + 1)]
        cols = [str(i) for i in range(1, 13)]
        all_values = [r + c for r, c in itertools.product(rows, cols)]
        return all_values

    def get_wells_filled_with_info(self):
        return self.plate_layout.get_data().keys()

    def get_wells_label_description(self):
        """Give the string description """
        wells = self.get_wells_tecan()
        # Initialize the wells_label dictionary with all well labels and default value as None
        wells_label = {well: "" for well in wells}
        metadata_well = self.plate_layout.get_data()
        # Strip and update values for existing wells
        for well, description in metadata_well.items():
            if well in wells_label:
                wells_label[well] = json.dumps(description, sort_keys=True, indent=4, ensure_ascii=False)
        return wells_label

    def get_wells_label_description_dict(self):
        """Give the dict description """
        wells = self.get_wells_tecan()
        # Initialize the wells_label dictionary with all well labels and default value as None
        wells_label = {well: {} for well in wells}
        metadata_well = copy.deepcopy(self.plate_layout.get_data())

        # Strip and update values for existing wells
        for well, description in metadata_well.items():
            if well in wells_label:
                wells_label[well] = description
        return wells_label

    def enrich_well_metadata(self):
        wells_dict = self.get_wells_label_description_dict()
        df = self.data_file.get_data()
        # Add the 'data' key to each well in the dictionary
        for well, info in wells_dict.items():
            row = well[0]  # First character of well (A, B, etc.)
            col = int(well[1:])  # Remaining characters as column number
            if row in df.index and str(col) in df.columns:
                if well not in wells_dict:
                    wells_dict[well] = {}  # Initialize `well` if it doesn't exist
                if "data" not in wells_dict[well]:
                    wells_dict[well]["data"] = np.nan  # Initialize or handle default value if needed
                wells_dict[well]["data"] = df.at[row, str(col)]
        return wells_dict

    def get_wells_list_by_compound_type(self, compound_name):
        wells_dict = self.enrich_well_metadata()
        # Filter the wells that have the specified compound
        selected_wells = [
            well for well, description in wells_dict.items() if description.get("compound") == compound_name
        ]
        return selected_wells

    def remove_wells_from_dataframe(self, wells):
        """
        Remove the cells corresponding to the specified wells by replacing them with NaN.

        Args:
        df (pd.DataFrame): The input DataFrame with row labels and numeric column labels.
        wells (list): List of well identifiers (e.g., "A1", "B2") to remove.

        Returns:
        pd.DataFrame: The updated DataFrame with specified wells set to NaN.
        """
        df = self.data_file.get_data()
        for well in wells:
            row = well[0]  # Row label (e.g., 'A')
            col = int(well[1:])  # Column number (e.g., '1')
            if row in df.index and str(col) in df.columns:
                df.at[row, str(col)] = np.nan
        # Remove rows and columns where all values are NaN
        df = df.dropna(how="all", axis=0)  # Remove rows
        df = df.dropna(how="all", axis=1)  # Remove columns
        return df

    def mean_data_for_compound(self, compound_name):
        """Give the mean of values of a certain compound"""
        wells_dict = copy.deepcopy(self.enrich_well_metadata())
        # Filter the wells that have the specified compound
        selected_wells = [
            well["data"]
            for well in wells_dict.values()
            if well.get("compound") == compound_name and not math.isnan(well["data"])
        ]
        # Calculate the mean of the "data" values
        if selected_wells:
            return sum(selected_wells) / len(selected_wells)
        else:
            return None  # Return None if no wells with the specified compound were found

    def parse_data(self):
        ## Step 1
        # Data import
        row_data = self.data_file.get_data()

        return row_data

    def update_row_data(self, updated_row_data):
        self.data_file = Table(updated_row_data)

