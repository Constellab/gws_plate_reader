import streamlit as st
import pandas as pd

from gws_core import ScenarioProxy, Scenario, ResourceSet, Table
from gws_core.protocol.protocol_proxy import ProtocolProxy
from gws_core.resource.resource_model import ResourceModel
from gws_core.streamlit import StreamlitTranslateLang


import os
from typing import Dict, List, Optional

from gws_plate_reader.cell_culture_app_core.cell_culture_state import CellCultureState


class FermentalgState(CellCultureState):
    """
    Fermentalg-specific state manager - extends CellCultureState with Fermentalg tags and methods.
    """

    # Fermentalg-specific tags for data
    TAG_FERMENTOR_FERMENTALG = "fermentor_fermentalg"
    TAG_BATCH = "batch"
    TAG_SAMPLE = "sample"
    TAG_MEDIUM = "medium"
    TAG_MISSING_VALUE = "missing_value"
    TAG_COLUMN_NAME = "column_name"

    # Recipe workflow tags (Fermentalg-specific)
    TAG_DATA_PROCESSING = "data_processing"
    TAG_SELECTION_PROCESSING = "selection_processing"
    TAG_QUALITY_CHECK_PROCESSING = "quality_check_processing"
    TAG_ANALYSES_PROCESSING = "analyses_processing"
    TAG_FERMENTOR_RECIPE_NAME = "fermentor_recipe_name"
    TAG_FERMENTOR_FERMENTALG_PIPELINE_ID = "fermentor_fermentalg_pipeline_id"
    TAG_MICROPLATE_ANALYSIS = "microplate_analysis"
    TAG_FERMENTOR_SELECTION_STEP = "fermentor_selection_step"
    TAG_FERMENTOR_QUALITY_CHECK_PARENT_SELECTION = "fermentor_quality_check_parent_selection"
    TAG_FERMENTOR_ANALYSES_PARENT_SELECTION = "fermentor_analyses_parent_selection"
    TAG_FERMENTOR_ANALYSES_PARENT_QUALITY_CHECK = "fermentor_analyses_parent_quality_check"

    # Additional Fermentalg session state keys
    LOAD_SCENARIO_KEY = "load_scenario"
    SELECTION_SCENARIOS_KEY = "selection_scenarios"
    RECIPE_NAME_KEY = "recipe_name"
    PIPELINE_ID_KEY = "pipeline_id"

    # File upload keys (Fermentalg-specific)
    INFO_CSV_KEY = "info_csv_file"
    RAW_DATA_CSV_KEY = "raw_data_csv_file"
    MEDIUM_CSV_KEY = "medium_csv_file"
    FOLLOW_UP_ZIP_KEY = "follow_up_zip_file"

    # Scenario output names
    LOAD_SCENARIO_OUTPUT_NAME = 'load_scenario_output'
    SELECTION_SCENARIO_OUTPUT_NAME = 'selection_scenario_output'
    INTERPOLATION_SCENARIO_OUTPUT_NAME = 'interpolation_scenario_output'
    QUALITY_CHECK_SCENARIO_OUTPUT_NAME = 'quality_check_scenario_output'
    QUALITY_CHECK_SCENARIO_INTERPOLATED_OUTPUT_NAME = 'quality_check_scenario_interpolated_output'

    def __init__(self, lang_translation_folder_path: str = None):
        """Initialize the Fermentalg state manager with translation service."""
        # Get the path of the current file's directory if not provided
        if lang_translation_folder_path is None:
            lang_translation_folder_path = os.path.dirname(os.path.abspath(__file__))

        # Call parent constructor
        super().__init__(lang_translation_folder_path)

    def get_load_scenario_output(self) -> Optional[ResourceSet]:
        """Get a specific output from the main scenario."""
        main_scenario = self.get_main_scenario()
        if not main_scenario:
            return None

        try:
            scenario_proxy = ScenarioProxy.from_existing_scenario(main_scenario.id)
            protocol_proxy = scenario_proxy.get_protocol()

            return protocol_proxy.get_output(self.LOAD_SCENARIO_OUTPUT_NAME)
        except Exception:
            return None

    def get_venn_diagram_output(self):
        """Get the Venn diagram PlotlyResource from the main scenario."""
        main_scenario = self.get_main_scenario()
        if not main_scenario:
            return None

        try:
            scenario_proxy = ScenarioProxy.from_existing_scenario(main_scenario.id)
            protocol_proxy = scenario_proxy.get_protocol()

            return protocol_proxy.get_output('venn_diagram')
        except Exception:
            return None

    def get_selection_scenario_output(self, selection_scenario: Scenario) -> Optional[ResourceSet]:
        """Get the filtered ResourceSet from a selection scenario"""
        try:
            scenario_proxy = ScenarioProxy.from_existing_scenario(selection_scenario.id)
            protocol_proxy = scenario_proxy.get_protocol()

            return protocol_proxy.get_output(self.SELECTION_SCENARIO_OUTPUT_NAME)
        except Exception:
            return None

    def get_interpolation_scenario_output(self, selection_scenario: Scenario) -> Optional[ResourceSet]:
        """Get the interpolated ResourceSet from a selection scenario"""
        try:
            scenario_proxy = ScenarioProxy.from_existing_scenario(selection_scenario.id)
            protocol_proxy = scenario_proxy.get_protocol()

            return protocol_proxy.get_output(self.INTERPOLATION_SCENARIO_OUTPUT_NAME)
        except Exception:
            return None

    def get_quality_check_protocol_proxy(self, quality_check_scenario: Scenario) -> ProtocolProxy:
        """Get the protocol proxy from a quality check scenario"""
        try:
            scenario_proxy = ScenarioProxy.from_existing_scenario(quality_check_scenario.id)
            protocol_proxy = scenario_proxy.get_protocol()

            return protocol_proxy
        except Exception:
            return None

    def get_quality_check_scenario_output_resource_model(
            self, quality_check_scenario: Scenario) -> Optional[ResourceModel]:
        """Get the filtered ResourceSet from a quality check scenario (non-interpolated data)"""
        protocol_proxy = self.get_quality_check_protocol_proxy(quality_check_scenario)
        if not protocol_proxy:
            return None

        return protocol_proxy.get_output_resource_model(self.QUALITY_CHECK_SCENARIO_OUTPUT_NAME)

    def get_quality_check_scenario_interpolated_output_resource_model(
            self, quality_check_scenario: Scenario) -> Optional[ResourceModel]:
        """Get the filtered interpolated ResourceSet from a quality check scenario"""
        protocol_proxy = self.get_quality_check_protocol_proxy(quality_check_scenario)
        if not protocol_proxy:
            return None

        return protocol_proxy.get_output_resource_model(self.QUALITY_CHECK_SCENARIO_INTERPOLATED_OUTPUT_NAME)

    def reset_recipe_scenarios(self) -> None:
        """Reset all recipe scenario data."""
        st.session_state[self.SELECTED_RECIPE_INSTANCE_KEY] = None
        st.session_state[self.LOAD_SCENARIO_KEY] = None
        st.session_state[self.SELECTION_SCENARIOS_KEY] = []
        st.session_state[self.RECIPE_NAME_KEY] = None
        st.session_state[self.PIPELINE_ID_KEY] = None

    # Utility functions for data processing
    def get_index_columns_from_resource_set(self, resource_set: ResourceSet) -> List[str]:
        """
        Get all columns that can be used as index from the ResourceSet.
        Returns all columns that have either 'is_index_column' or 'is_data_column' tags.
        Time columns (is_index_column=true) are prioritized and appear first in the list.

        :param resource_set: ResourceSet containing tables
        :return: List of column names that can be used as index, with time columns first
        """
        try:
            resources = resource_set.get_resources()
            time_columns = []  # Columns specifically tagged as index (time columns)
            other_columns = []  # Other data columns that can also be used as index

            for resource in resources.values():
                if isinstance(resource, Table):
                    for col_name in resource.get_column_names():
                        # Skip if already in either list
                        if col_name in time_columns or col_name in other_columns:
                            continue

                        col_tags = resource.get_column_tags_by_name(col_name)
                        is_index_column = col_tags.get('is_index_column') == 'true'
                        is_data_column = col_tags.get('is_data_column') == 'true'

                        # Time columns go first
                        if is_index_column:
                            time_columns.append(col_name)
                        # Other data columns can also be used as index
                        elif is_data_column:
                            other_columns.append(col_name)

            # Return time columns first, then other columns (both sorted)
            return sorted(time_columns) + sorted(other_columns)
        except Exception:
            return []

    def get_strict_index_columns_from_resource_set(self, resource_set: ResourceSet) -> List[str]:
        """
        Get only columns with is_index_column=true tag (strict filtering).
        Use this for Feature Extraction where only time/temperature columns should be selectable.

        :param resource_set: ResourceSet containing tables
        :return: List of column names with is_index_column=true tag
        """
        try:
            resources = resource_set.get_resources()
            index_columns = []

            for resource in resources.values():
                if isinstance(resource, Table):
                    for col_name in resource.get_column_names():
                        # Skip if already in list
                        if col_name in index_columns:
                            continue

                        col_tags = resource.get_column_tags_by_name(col_name)
                        is_index_column = col_tags.get('is_index_column') == 'true'

                        if is_index_column:
                            index_columns.append(col_name)

            return sorted(list(set(index_columns)))
        except Exception:
            return []

    def get_data_columns_from_resource_set(self, resource_set: ResourceSet) -> List[str]:
        """Get columns that contain data (is_data_column tagged columns)"""
        try:
            resources = resource_set.get_resources()
            data_columns = []

            for resource in resources.values():
                if isinstance(resource, Table):
                    for col_name in resource.get_column_names():
                        if col_name in data_columns:
                            continue

                        col_tags = resource.get_column_tags_by_name(col_name)
                        is_data_column = col_tags.get('is_data_column') == 'true'

                        if is_data_column:
                            data_columns.append(col_name)

            return sorted(list(set(data_columns)))
        except Exception:
            return []

    def get_column_label_with_unit(self, resource_set: ResourceSet, column_name: str) -> str:
        """
        Get a formatted label for a column including its unit if available.

        :param resource_set: ResourceSet containing tables
        :param column_name: Name of the column
        :return: Formatted label like "Column Name (unit)" or just "Column Name"
        """
        try:
            resources = resource_set.get_resources()

            for resource in resources.values():
                if isinstance(resource, Table):
                    if column_name in resource.get_column_names():
                        col_tags = resource.get_column_tags_by_name(column_name)
                        unit = col_tags.get('unit')

                        if unit:
                            return f"{column_name} ({unit})"
                        return column_name

            return column_name
        except Exception:
            return column_name

    def build_selected_column_df_from_resource_set(self, resource_set: ResourceSet,
                                                   index_column: str,
                                                   selected_column: str) -> pd.DataFrame:
        """Build a DataFrame for a specific selected column from the ResourceSet
            The dataframe will contain the index column and data columns.
            One data column per couple batch/sample, the column name will be Batch_Sample and its values will be the values of the selected column.
        """
        try:
            resources = resource_set.get_resources()
            combined_data = pd.DataFrame()

            for resource_name, resource in resources.items():
                if isinstance(resource, Table):
                    df = resource.get_data()
                    if index_column in df.columns and selected_column in df.columns:
                        # Extract batch and sample from tags
                        batch = ""
                        sample = ""

                        if hasattr(resource, 'tags') and resource.tags:
                            for tag in resource.tags.get_tags():
                                if tag.key == self.TAG_BATCH:
                                    batch = tag.value
                                elif tag.key == self.TAG_SAMPLE:
                                    sample = tag.value

                        column_label = f"{batch}_{sample}" if batch and sample else resource_name

                        # Create a copy of the relevant columns
                        temp_df = df[[index_column, selected_column]].copy()
                        temp_df = temp_df.rename(columns={selected_column: column_label})

                        # Remove any NaN values in the index column
                        temp_df = temp_df.dropna(subset=[index_column])

                        if combined_data.empty:
                            combined_data = temp_df
                        else:
                            combined_data = pd.merge(combined_data, temp_df, on=index_column, how='outer')

            # Sort by index column if not empty
            if not combined_data.empty and index_column in combined_data.columns:
                combined_data = combined_data.sort_values(by=index_column).reset_index(drop=True)

            return combined_data
        except Exception:
            # Return empty DataFrame in case of error
            return pd.DataFrame()

    def prepare_data_for_visualization(self, resource_set: ResourceSet) -> List[Dict[str, str]]:
        """Prepare data from ResourceSet for visualization"""
        try:
            resources = resource_set.get_resources()
            visualization_data = []

            for resource_name, resource in resources.items():
                if isinstance(resource, Table):
                    # Extract metadata from tags
                    batch = ""
                    sample = ""
                    medium = ""

                    if hasattr(resource, 'tags') and resource.tags:
                        for tag in resource.tags.get_tags():
                            if tag.key == self.TAG_BATCH:
                                batch = tag.value
                            elif tag.key == self.TAG_SAMPLE:
                                sample = tag.value
                            elif tag.key == self.TAG_MEDIUM:
                                medium = tag.value

                    visualization_data.append({
                        'Batch': batch,
                        'Sample': sample,
                        'Medium': medium,
                        'Resource_Name': resource_name
                    })

            return visualization_data
        except Exception:
            return []

    # Fermentalg-specific translation methods
    @classmethod
    def get_lang(cls) -> StreamlitTranslateLang:
        """Get the current language from the translate service."""
        translate_service = st.session_state.get(cls.TRANSLATE_SERVICE)
        if translate_service:
            return translate_service.get_lang()
        return StreamlitTranslateLang.FR  # Default to French

    @classmethod
    def set_lang(cls, value: StreamlitTranslateLang) -> None:
        """Set the current language in the translate service."""
        translate_service = st.session_state.get(cls.TRANSLATE_SERVICE)
        if translate_service:
            translate_service.change_lang(value)
            st.session_state[cls.TRANSLATE_SERVICE] = translate_service
