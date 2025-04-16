import json
import os
from typing import Any, Dict, List, Optional

from gws_core import (ConfigParams, Folder, InputSpec, InputSpecs, JSONDict,
                      OutputSpec, OutputSpecs, ResourceSet, Table, Task,
                      TaskInputs, TaskOutputs, TypingStyle, task_decorator)
from gws_core.tag.tag import Tag, TagOrigins
from gws_core.tag.tag_dto import TagOriginType
from gws_core.user.current_user_service import CurrentUserService
from gws_plate_reader.biolector_xt.tasks._streamlit_dashboard.app.download_exp import \
    DOWNLOAD_TAG_KEY
from pandas import NA, DataFrame, Series


@task_decorator("BiolectorXTDataParser", human_name="BiolectorXT Data Parser",
                short_description="Task to parse BiolectorXT data before using the analysis dashboard",
                style=TypingStyle.community_icon(icon_technical_name="table", background_color="#c3fa7f"))
class BiolectorXTDataParser(Task):
    input_specs: InputSpecs = InputSpecs(
        {'raw_data': InputSpec(Table, human_name="Table containing the raw data"),
         'folder_metadata': InputSpec(Folder, human_name="Folder containing the metadata"),
         'plate_layout': InputSpec(JSONDict, human_name="JSONDict containing the plate_layout", is_optional=True)})

    output_specs: OutputSpecs = OutputSpecs(
        {'parsed_data_tables': OutputSpec(ResourceSet, human_name="Parsed data tables resource set", sub_class=True)})

    def is_micro_fluidics(self, data: DataFrame) -> bool:
        """
        Check if the task is running in a microfluidics environment.

        :return: True if the task is running in a microfluidics environment, False otherwise.
        """
        unique_wells = data['Well'].dropna().unique()
        if "A01" in unique_wells:
            return False
        return True

    def get_filters(self, metadata: Dict) -> List[str]:
        """
        Get the filters to apply to the data.

        :param metadata: The metadata to include in the parsed data.
        :return: The filters to apply to the data.
        """
        filters = []
        for channel in metadata.get('Channels', []):
            filters.append(channel['Name'])
        return filters

    def parse_data(self, data: DataFrame, metadata: Dict) -> Dict[str, DataFrame]:
        """
        Parse the raw data from BiolectorXT and save it in a JSON format.

        :param data: The raw data to parse.
        :param metadata: The metadata to include in the parsed data.
        :return: The parsed data.
        """

        # Step 1: Check if the task is running in a microfluidics environment and get the filters
        is_micro_fluidics: bool = self.is_micro_fluidics(data)
        filters: List[str] = self.get_filters(metadata)

        # Step 2
        # Filter the Filterset column alphabetically and the Well column
        row_data = data.sort_values(by=['Filterset', 'Well'])
        # Only keep columns: Well, Filterset, Time, Cal
        reduced_data = row_data[["Well", "Filterset", "Time", "Cal"]]
        # Extract unique values from 'Filterset' column
        unique_values = reduced_data['Filterset'].dropna().unique()

        # Create a dictionary to store data frames with filter names as keys
        df_filter_dict: Dict[str, DataFrame] = {}
        for i, value in enumerate(unique_values):
            # Create DataFrame for each unique filterset value
            df_filter = reduced_data[reduced_data['Filterset'] == value]

            # Step 3:
            # Filter Well column and Time
            df_filter = df_filter.sort_values(by=['Well', 'Time'])
            # Delete FilterSet column
            df_filter = df_filter.drop(columns="Filterset")

            # Check if it's microfluidics
            if is_micro_fluidics:
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
                df_filter[col] = Series(df_filter[col].dropna().values)

            # Drop nan rows at the end of the dataframe:
            df_filter = df_filter.dropna(subset=['time'])
            df_filter = df_filter.drop(columns="Well")
            df_filter = df_filter.drop(columns="Time")
            df_filter = df_filter.drop(columns="Cal")

            # Add the processed DataFrame to the dictionary with filter name as key
            if i < len(filters):  # Ensure index is within bounds of filters list
                filter_name = filters[i]
                df_filter_dict[filter_name] = df_filter
        return df_filter_dict

    def get_wells_cultivation(self, metadata: Dict) -> List[str]:
        microplate = metadata.get("Microplate", {})
        return microplate.get("CultivationLabels", [])

    def get_wells_reservoir(self, metadata: Dict) -> List[str]:
        microplate = metadata.get("Microplate", {})
        return microplate.get("ReservoirLabels", [])

    def get_wells(self, metadata: Dict) -> List[str]:
        """
        Get the wells from the metadata.

        :param metadata: The metadata to include in the parsed data.
        :return: The wells.
        """
        wells = []
        # Get the cultivation wells
        cultivation_wells = self.get_wells_cultivation(metadata)
        # Get the reservoir wells
        reservoir_wells = self.get_wells_reservoir(metadata)

        wells.extend(cultivation_wells)
        wells.extend(reservoir_wells)
        return wells

    def get_wells_label_description(self, metadata: Dict, existing_plate_layout: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Get the wells label description from the metadata.

        :param metadata: The metadata to include in the parsed data.
        :return: The wells label description.
        """
        # A01 to F08
        wells = [f"{chr(letter)}{str(num).zfill(2)}"
                 for letter in range(ord('A'),
                                     ord('F') + 1) for num in range(1, 9)]
        wells_label = {well: {"label": ""} for well in wells}
        microplate = metadata.get("Layout", {})
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
                if len(well) == 2:
                    well = f"{well[0]}0{well[1]}"
                if well in wells_label and isinstance(data, dict):  # Ensure it's a dictionary
                    # Get the existing data, ensuring it's a dictionary
                    existing_data = wells_label[well] if isinstance(wells_label[well], dict) else {
                        "label": wells_label[well]}
                    # If "label" exists in data, overwrite it
                    if "label" in data:
                        existing_data["label"] = data["label"]

                    # Update with all keys from data
                    existing_data.update(data)

                    # Assign back to wells_label
                    wells_label[well] = existing_data

        return wells_label

    def create_parsed_resource_set(
            self, data: DataFrame, metadata: Dict, existing_plate_layout: Optional[Dict] = None) -> ResourceSet:
        """
        Create a resource set from the parsed data.

        :param data: The parsed data.
        :param metadata: The metadata to include in the resource set.
        :return: The resource set.
        """
        # Create a resource set from the parsed data
        resource_set = ResourceSet()
        parsed_data: Dict[str, DataFrame] = self.parse_data(data=data, metadata=metadata)
        parsed_data_tables: Dict[str, Table] = {}
        wells_data = self.get_wells_label_description(metadata=metadata, existing_plate_layout=existing_plate_layout)
        for key, dataframe in parsed_data.items():
            if len(dataframe.columns)-2 != len(wells_data):
                # Add missing wells A01 to B08
                for well in wells_data.keys():
                    if well not in dataframe.columns:
                        # Add the well to the dataframe
                        dataframe[well] = NA
                        # Order wells columns
                columns = list(dataframe.columns)[:2]
                columns.extend(sorted(dataframe.columns[2:]))
                dataframe = dataframe[columns]
            table = Table(dataframe)
            parsed_data_tables[key] = table
        # Add the wells data to tables
        for well, well_data in wells_data.items():
            for table_key in parsed_data_tables.keys():
                if well in parsed_data_tables[table_key].get_data().columns:
                    for data_key, data_value in well_data.items():
                        parsed_data_tables[table_key].add_column_tag_by_name(well, data_key, data_value)
        for name, table in parsed_data_tables.items():
            # Add the table to the resource set
            table.name = name
            resource_set.add_resource(table, name)
        return resource_set

    def run(self, params: ConfigParams, inputs: TaskInputs) -> TaskOutputs:
        """
        Parse the raw data from BiolectorXT and save it in a JSON format.

        :param params: The parameters for the task.
        :param inputs: The inputs for the task.
        :return: The parsed data.
        """

        # get the input
        raw_data: Table = inputs.get('raw_data')
        folder_metadata: Folder = inputs.get('folder_metadata')
        plate_layout: JSONDict = inputs.get('plate_layout')

        metadata: dict = None
        for file_name in os.listdir(folder_metadata.path):
            if file_name.endswith('BXT.json'):
                file_path = os.path.join(folder_metadata.path, file_name)
                try:
                    with open(file_path, 'r', encoding='UTF-8') as json_file:
                        metadata = json.load(json_file)
                except Exception as e:
                    raise Exception(f"Error while reading the metadata file {file_name}: {e}")

        if metadata is None:
            raise Exception(
                "No metadata file found in the provided folder. The folder must contain a file that ends with 'BXT.json'")

        existing_plate_layout: Optional[Dict] = None
        if plate_layout:
            # convert the JSONDict to a dictionary
            existing_plate_layout = plate_layout.get_data()

        resource_set = self.create_parsed_resource_set(data=raw_data.get_data(), metadata=metadata,
                                                       existing_plate_layout=existing_plate_layout)
        resource_set.tags.add_tags(raw_data.tags.get_by_key(DOWNLOAD_TAG_KEY))

        user_id = CurrentUserService.get_current_user().id if CurrentUserService.get_current_user() else None
        origins = TagOrigins(TagOriginType.USER, user_id)

        list_tags: List[Tag] = []

        comment = metadata.get("Comment", None)
        if comment:
            list_tags.append(Tag(key="comment", value=comment, auto_parse=True,
                                 origins=origins, is_propagable=True))
        name = metadata.get("Name", None)
        if name:
            list_tags.append(Tag(key="name", value=name, auto_parse=True, origins=origins, is_propagable=True))
        user_name = metadata.get("UserName", None)
        if user_name:
            list_tags.append(Tag(key="user_name", value=user_name,
                                 auto_parse=True, origins=origins, is_propagable=True))
        date = metadata.get("LastModifiedAt", None)
        if date:
            list_tags.append(Tag(key="date", value=date, auto_parse=True, origins=origins, is_propagable=True))

        list_tags.append(Tag(key="raw_data", value=raw_data.name.lower().replace(
            " ", "_"), origins=origins, is_propagable=True))

        # Add the tags to the resource set resources
        for table_name, table in resource_set.get_resources().items():
            for tag in list_tags:
                table.tags.add_tag(tag)

        # return the parsed data
        return {'parsed_data_tables': resource_set}
