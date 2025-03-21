from typing import Dict, List

from pandas import NA, DataFrame, Series


class BiolectorXTParser:

    data: DataFrame = None
    metadata: dict = None

    _data_filtered: Dict[str, DataFrame] = None

    def __init__(self, data: DataFrame, metadata: dict):
        """
        Initialize the BiolectorXTParser object with the data file and metadata dict.
        """
        super().__init__()

        self.data = data
        self.metadata = metadata

    def get_filter_name(self) -> List[str]:
        filter_names = []
        for channel in self.metadata.get("Channels", []):
            filter_names.append(channel["Name"])
        return filter_names

    def get_wells_cultivation(self) -> List[str]:
        microplate = self.metadata.get("Microplate", {})
        return microplate.get("CultivationLabels", [])

    def get_wells_reservoir(self) -> List[str]:
        microplate = self.metadata.get("Microplate", {})
        return microplate.get("ReservoirLabels", [])

    def get_wells(self):
        wells_names = []
        # Get the cultivation wells
        cultivation_wells = self.get_wells_cultivation()
        # Get the reservoir wells
        reservoir_wells = self.get_wells_reservoir()
        # Merge the two lists
        wells_names.extend(cultivation_wells)
        wells_names.extend(reservoir_wells)
        return wells_names

    def get_wells_label_description(self) -> dict:
        wells = self.get_wells()
        # Initialize the wells_label dictionary with all well labels and default value as None
        wells_label = {well: "" for well in wells}
        microplate = self.metadata.get("Layout", {})
        cultivation_map = microplate.get("CultivationLabelDescriptionsMap", {})
        reservoir_map = microplate.get("ReservoirLabelDescriptionsMap", {})

        # Strip and update values for existing wells
        for well, description in cultivation_map.items():
            if well in wells_label:
                wells_label[well] = description.strip() or wells_label[well]
        for well, description in reservoir_map.items():
            if well in wells_label:
                wells_label[well] = description.strip() or wells_label[well]
        return wells_label

    def is_microfluidics(self):
        # if data is microfluidics, then there is no value in the wells A01 to B08
        unique_wells = self.data['Well'].dropna().unique()
        if "A01" in unique_wells:
            return False
        else:
            return True

    def parse_data(self) -> Dict[str, DataFrame]:

        if self._data_filtered is not None:
            return self._data_filtered

        microfluidics = self.is_microfluidics()
        filters = self.get_filter_name()

        # Step 2
        # Filter the Filterset column alphabetically and the Well column
        row_data = self.data.sort_values(by=['Filterset', 'Well'])
        # Only keep columns: Well, Filterset, Time, Cal
        reduced_data = row_data[["Well", "Filterset", "Time", "Cal"]]

        # Extract unique values from 'Filterset' column
        unique_values = reduced_data['Filterset'].dropna().unique()
        # Create a dictionary to store data frames with filter names as keys
        df_filter_dict = {}
        for i, value in enumerate(unique_values):
            # Create DataFrame for each unique filterset value
            df_filter = reduced_data[reduced_data['Filterset'] == value]

            # Step 3:
            # Filter Well column and Time
            df_filter = df_filter.sort_values(by=['Well', 'Time'])
            # Delete FilterSet column
            df_filter = df_filter.drop(columns="Filterset")

            # Check if it's microfluidics
            if microfluidics:
                # Add column C01 to F08
                columns_to_add = [f"{chr(letter)}{str(num).zfill(2)}"
                                  for letter in range(ord('C'),
                                                      ord('F') + 1) for num in range(1, 9)]
            else:
                # Else, add column A01 to F08
                columns_to_add = [f"{chr(letter)}{str(num).zfill(2)}"
                                  for letter in range(ord('A'),
                                                      ord('F') + 1) for num in range(1, 9)]

            # Add columns to the DataFrame
            df_filter = df_filter.assign(time=NA, Temps_en_h=NA, **{col: NA for col in columns_to_add})

            # Fill time and Temps_en_h columns
            df_filter["time"] = df_filter.loc[df_filter['Well'] == columns_to_add[0], 'Time']
            df_filter["Temps_en_h"] = df_filter["time"] / 3600

            # Copy values of 'Cal' in the corresponding column (A01, A02, ...)
            for name_col in columns_to_add:
                df_filter[name_col] = df_filter.loc[df_filter['Well'] == name_col, 'Cal']

            # Delete NaN values and set cell to up
            columns_to_process = df_filter.columns[3:len(df_filter.columns)]
            # reset index
            df_filter = df_filter.reset_index(drop=True)
            # Apply the shifting function to each specified column
            for col in columns_to_process:
                df_filter[col] = self._shift_cells_up(df_filter[col])
            # Drop nan rows at the end of the dataframe:
            df_filter = df_filter.dropna(subset=['time'])
            df_filter = df_filter.drop(columns="Well")
            df_filter = df_filter.drop(columns="Time")
            df_filter = df_filter.drop(columns="Cal")

            # Add the processed DataFrame to the dictionary with filter name as key
            if i < len(filters):  # Ensure index is within bounds of filters list
                filter_name = filters[i]
                df_filter_dict[filter_name] = df_filter

        # Return the dictionary of DataFrames, keyed by filter name
        self._data_filtered = df_filter_dict
        return df_filter_dict

    # Function to shift cells up within each column
    def _shift_cells_up(self, series):
        return Series(series.dropna().values)

    # Example of querying by filter name
    def get_table_by_filter(self, filter_name: str):
        if filter_name not in self.get_filter_name():
            raise Exception(
                f"The filter {filter_name} doesn't exist. The existing filters are : {self.get_filter_name()}")

        df_filter_dict = self.parse_data()
        return df_filter_dict.get(filter_name)

    def get_well_values(self, well_id: str, filter_name: str):
        """
        Get the values of a specific well from the data.
        Assumes well_id corresponds to a column in the data.
        """
        if filter_name not in self.get_filter_name():
            raise Exception(
                f"The filter {filter_name} doesn't exist. The existing filters are : {self.get_filter_name()}")
        df_filter = self.get_table_by_filter(filter_name)
        if well_id not in df_filter.columns:
            raise Exception(f"Well {well_id} not found in the data.")

        return df_filter[['Temps_en_h', well_id]]
