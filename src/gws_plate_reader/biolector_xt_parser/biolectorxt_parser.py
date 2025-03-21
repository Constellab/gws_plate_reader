from typing import Dict, List
from pandas import NA, DataFrame, Series
from collections import defaultdict
from gws_core import Tag, CurrentUserService, Table
from gws_core.tag.tag import TagOrigins
from gws_core.tag.tag_dto import TagOriginType


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

    def get_wells_label_description(self, existing_plate_layout : None) -> dict:
        wells = self.get_wells()
        # Initialize the wells_label dictionary with all well labels and default value as None
        wells_label = {well: {"label": ""} for well in wells}
        microplate = self.metadata.get("Layout", {})
        cultivation_map = microplate.get("CultivationLabelDescriptionsMap", {})
        reservoir_map = microplate.get("ReservoirLabelDescriptionsMap", {})

        # Strip and update values for existing wells
        for well, description in cultivation_map.items():
            if well in wells_label:
                wells_label[well] = {"label": description.strip() or wells_label[well]}

        for well, description in reservoir_map.items():
            if well in wells_label:
                wells_label[well] = {"label": description.strip() or wells_label[well]}

        if existing_plate_layout:
            # Retrieve data in existing_plate_layout and override label if key "label" is present
            for well, data in existing_plate_layout.items():
                if well in wells_label and isinstance(data, dict):  # Ensure it's a dictionary
                    # Get the existing data, ensuring it's a dictionary
                    existing_data = wells_label[well] if isinstance(wells_label[well], dict) else {"label": wells_label[well]}
                    # If "label" exists in data, overwrite it
                    if "label" in data:
                        existing_data["label"] = data["label"]

                    # Update with all keys from data
                    existing_data.update(data)

                    # Assign back to wells_label
                    wells_label[well] = existing_data

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

    def group_wells_by_selection(self, well_data, selected_well_or_replicate):
        # Grouping wells by key choosen by the user
        dict_replicates = defaultdict(list)

        for well, info in well_data.items():
            if info.get(selected_well_or_replicate):
                dict_replicates[info[selected_well_or_replicate]].append(well)
        # Convert to a normal dict (if needed)
        dict_replicates = dict(dict_replicates)
        return dict_replicates

    def add_tags_to_table_columns(self, resource_to_tag : Table, well_data : dict):
        for column in resource_to_tag.column_names:
            dict_column = well_data.get(column, None)
            if dict_column :
                for key, value in dict_column.items() :
                    resource_to_tag.add_column_tag_by_name(column, key = Tag.parse_tag(key), value = Tag.parse_tag(value))

    def add_tags_to_table_rows(self, resource_to_tag : Table, well_data : dict):
        for row in resource_to_tag.row_names:
            dict_row = well_data.get(row, None)
            if dict_row :
                for key, value in dict_row.items() :
                    resource_to_tag.add_row_tag_by_name(row, key = Tag.parse_tag(key), value = Tag.parse_tag(value))

    def add_tags_to_resource(self, resource_to_tag, filter_selection, input_tag = None):
        user_id = CurrentUserService.get_and_check_current_user().id
        origins = TagOrigins(TagOriginType.USER, user_id)
        resource_to_tag.tags.add_tag(Tag(key = "filter", value = filter_selection, auto_parse = True, origins = origins))

        if input_tag :
            # If there was a tag biolector_download associated you the input table, then we add it to this table too
            resource_to_tag.tags.add_tag(input_tag[0])

        comment = self.metadata.get("Comment", None)
        if comment :
            resource_to_tag.tags.add_tag(Tag(key = "comment", value = comment, auto_parse = True, origins = origins))

        name = self.metadata.get("Name", None)
        if name :
            resource_to_tag.tags.add_tag(Tag(key = "name", value = name, auto_parse = True, origins = origins))

        user_name = self.metadata.get("UserName", None)
        if user_name :
            resource_to_tag.tags.add_tag(Tag(key = "user_name", value = user_name, auto_parse = True, origins = origins))

        date = self.metadata.get("LastModifiedAt", None)
        if date :
            resource_to_tag.tags.add_tag(Tag(key = "date", value = date, auto_parse = True, origins = origins))




