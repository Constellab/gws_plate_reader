import streamlit as st
import pandas as pd
import os
from typing import Dict, Any, List, Optional
from gws_core import ScenarioProxy, Scenario, ResourceSet, Table
from gws_core.streamlit import StreamlitTranslateService, StreamlitTranslateLang
from .analyse import Analyse


class State:
    """Class to manage the state of the Fermentalg dashboard app."""

    # Translation keys
    LANG_KEY = "lang_select"
    TRANSLATE_SERVICE = "translate_service"

    # Tags for fermentalg data
    TAG_FERMENTOR_FERMENTALG = "fermentor_fermentalg"
    TAG_BATCH = "batch"
    TAG_SAMPLE = "sample"
    TAG_MEDIUM = "medium"
    TAG_MISSING_VALUE = "missing_value"
    TAG_COLUMN_NAME = "column_name"

    # Analysis workflow tags
    TAG_DATA_PROCESSING = "data_processing"
    TAG_SELECTION_PROCESSING = "selection_processing"
    TAG_FERMENTOR_ANALYSIS_NAME = "fermentor_analysis_name"
    TAG_FERMENTOR_FERMENTALG_PIPELINE_ID = "fermentor_fermentalg_pipeline_id"
    TAG_MICROPLATE_ANALYSIS = "microplate_analysis"
    TAG_FERMENTOR_SELECTION_STEP = "fermentor_selection_step"

    # Session state keys
    PROCESSING_RESULTS_KEY = "processing_results"
    PROCESSING_COMPLETED_KEY = "processing_completed"
    SELECTION_DATA_KEY = "selection_data"
    SELECTED_RESOURCES_KEY = "selected_resources"
    SELECTED_RESOURCE_SET_KEY = "selected_resource_set"
    SELECTED_ANALYSE_INSTANCE_KEY = "selected_analyse_instance"

    # Analysis scenarios management
    LOAD_SCENARIO_KEY = "load_scenario"
    SELECTION_SCENARIOS_KEY = "selection_scenarios"
    ANALYSIS_NAME_KEY = "analysis_name"
    PIPELINE_ID_KEY = "pipeline_id"

    # File upload keys
    INFO_CSV_KEY = "info_csv_file"
    RAW_DATA_CSV_KEY = "raw_data_csv_file"
    MEDIUM_CSV_KEY = "medium_csv_file"
    FOLLOW_UP_ZIP_KEY = "follow_up_zip_file"

    LOAD_SCENARIO_OUTPUT_NAME = 'load_scenario_output'
    SELECTION_SCENARIO_OUTPUT_NAME = 'selection_scenario_output'
    INTERPOLATION_SCENARIO_OUTPUT_NAME = 'interpolation_scenario_output'

    def __init__(self, lang_translation_folder_path: str = None):
        """Initialize the state manager with translation service."""
        # Initialize translation service
        if lang_translation_folder_path is None:
            # Get the path of the current file's directory
            lang_translation_folder_path = os.path.dirname(os.path.abspath(__file__))

        translate_service = StreamlitTranslateService(lang_translation_folder_path)
        st.session_state[self.TRANSLATE_SERVICE] = translate_service

        # Initialize other session state variables
        self._initialize_session_state()

    def _initialize_session_state(self) -> None:
        """Initialize session state variables if they don't exist."""
        if self.PROCESSING_RESULTS_KEY not in st.session_state:
            st.session_state[self.PROCESSING_RESULTS_KEY] = None

        if self.PROCESSING_COMPLETED_KEY not in st.session_state:
            st.session_state[self.PROCESSING_COMPLETED_KEY] = False

        if self.SELECTION_DATA_KEY not in st.session_state:
            st.session_state[self.SELECTION_DATA_KEY] = []

        if self.SELECTED_RESOURCES_KEY not in st.session_state:
            st.session_state[self.SELECTED_RESOURCES_KEY] = []

        if self.SELECTED_RESOURCE_SET_KEY not in st.session_state:
            st.session_state[self.SELECTED_RESOURCE_SET_KEY] = None

    # Getters and setters for processing results
    def get_processing_results(self) -> Dict[str, Any]:
        """Get the processing results from session state."""
        return st.session_state.get(self.PROCESSING_RESULTS_KEY, {})

    def set_processing_results(self, results: Dict[str, Any]) -> None:
        """Set the processing results in session state."""
        st.session_state[self.PROCESSING_RESULTS_KEY] = results

    def get_processing_completed(self) -> bool:
        """Check if processing is completed."""
        return st.session_state.get(self.PROCESSING_COMPLETED_KEY, False)

    def set_processing_completed(self, completed: bool) -> None:
        """Set the processing completed flag in session state."""
        st.session_state[self.PROCESSING_COMPLETED_KEY] = completed

    # Getters and setters for selection data
    def get_selection_data(self) -> List[bool]:
        """Get the selection data from session state."""
        return st.session_state.get(self.SELECTION_DATA_KEY, [])

    def set_selection_data(self, selection: List[bool]) -> None:
        """Set the selection data (list of boolean values) in session state."""
        st.session_state[self.SELECTION_DATA_KEY] = selection

    def get_selected_resources(self) -> List[Dict[str, str]]:
        """Get the selected resources from session state."""
        return st.session_state.get(self.SELECTED_RESOURCES_KEY, [])

    def set_selected_resources(self, resources: List[Dict[str, str]]) -> None:
        """Set the selected resources in session state."""
        st.session_state[self.SELECTED_RESOURCES_KEY] = resources

    def get_selected_resource_set(self) -> Optional[Any]:
        """Get the selected resource set from session state."""
        return st.session_state.get(self.SELECTED_RESOURCE_SET_KEY)

    def set_selected_resource_set(self, resource_set: Any) -> None:
        """Set the selected resource set in session state."""
        st.session_state[self.SELECTED_RESOURCE_SET_KEY] = resource_set

    def get_selected_analyse_instance(self) -> Optional[Analyse]:
        """Get the selected Analyse instance from session state."""
        return st.session_state.get(self.SELECTED_ANALYSE_INSTANCE_KEY)

    def set_selected_analyse_instance(self, analyse_instance: Analyse) -> None:
        """Set the selected Analyse instance in session state."""
        st.session_state[self.SELECTED_ANALYSE_INSTANCE_KEY] = analyse_instance

    # Methods that delegate to the Analyse instance
    def get_analysis_name(self) -> Optional[str]:
        """Get the current analysis name from the Analyse instance."""
        analyse = self.get_selected_analyse_instance()
        return analyse.name if analyse else None

    def get_pipeline_id(self) -> Optional[str]:
        """Get the current pipeline ID from the Analyse instance."""
        analyse = self.get_selected_analyse_instance()
        return analyse.pipeline_id if analyse else None

    def get_selection_scenarios(self) -> List[Scenario]:
        """Get the list of selection scenarios from the Analyse instance."""
        analyse = self.get_selected_analyse_instance()
        return analyse.get_selection_scenarios() if analyse else []

    def get_visualization_scenarios(self) -> List[Scenario]:
        """Get the list of visualization scenarios from the Analyse instance."""
        analyse = self.get_selected_analyse_instance()
        return analyse.get_visualization_scenarios() if analyse else []

    def get_main_scenario(self) -> Optional[Scenario]:
        """Get the main scenario from the Analyse instance."""
        analyse = self.get_selected_analyse_instance()
        return analyse.get_load_scenario() if analyse else None

    def add_scenarios_to_analyse(self, step: str, scenarios: List[Scenario]) -> None:
        """Add scenarios to the current Analyse instance for a specific step."""
        analyse = self.get_selected_analyse_instance()
        if analyse:
            analyse.add_scenarios_by_step(step, scenarios)

    def update_analyse_with_selection_scenarios(self, selection_scenarios: List[Scenario]) -> None:
        """Update the current Analyse instance with selection scenarios."""
        analyse = self.get_selected_analyse_instance()
        if analyse:
            analyse.add_selection_scenarios(selection_scenarios)

    # Utility methods
    def has_selected_resources(self) -> bool:
        """Check if there are any selected resources."""
        selected = self.get_selected_resources()
        return len(selected) > 0

    def get_selected_count(self) -> int:
        """Get the count of selected resources."""
        return len(self.get_selected_resources())

    def reset_all_data(self) -> None:
        """Reset all data in the session state."""
        st.session_state[self.PROCESSING_RESULTS_KEY] = None
        st.session_state[self.PROCESSING_COMPLETED_KEY] = False
        st.session_state[self.SELECTION_DATA_KEY] = []
        st.session_state[self.SELECTED_RESOURCES_KEY] = []
        st.session_state[self.SELECTED_RESOURCE_SET_KEY] = None
        st.session_state[self.SELECTED_ANALYSE_INSTANCE_KEY] = None

    def reset_selection(self) -> None:
        """Reset only the selection data."""
        st.session_state[self.SELECTION_DATA_KEY] = []
        st.session_state[self.SELECTED_RESOURCES_KEY] = []
        st.session_state[self.SELECTED_RESOURCE_SET_KEY] = None
        st.session_state[self.SELECTED_RESOURCE_SET_KEY] = None

    # Analysis tree navigation methods
    def get_selected_step(self) -> str:
        """Get the currently selected analysis step."""
        return st.session_state.get("selected_fermentalg_step", "data_overview")

    def set_selected_step(self, step: str) -> None:
        """Set the currently selected analysis step."""
        st.session_state["selected_fermentalg_step"] = step

    def set_selected_folder_id(self, folder_id: str) -> None:
        """Set the selected folder ID."""
        st.session_state["selected_folder_id"] = folder_id

    def get_selected_folder_id(self) -> Optional[str]:
        """Get the selected folder ID."""
        return st.session_state.get("selected_folder_id")

    # Legacy methods for backward compatibility
    def set_load_scenario(self, scenario: Scenario) -> None:
        """Set the load scenario for the current analysis (deprecated - use Analyse instance)."""
        st.session_state[self.LOAD_SCENARIO_KEY] = scenario

    def get_load_scenario(self) -> Optional[Scenario]:
        """Get the load scenario for the current analysis (deprecated - use get_main_scenario)."""
        return self.get_main_scenario()

    def add_selection_scenario(self, scenario: Scenario) -> None:
        """Add a new selection scenario to the current analysis."""
        analyse = self.get_selected_analyse_instance()
        if analyse:
            current_scenarios = analyse.get_selection_scenarios()
            current_scenarios.append(scenario)
            analyse.add_scenarios_by_step('selection', current_scenarios)

    # Utility methods for working with stored scenarios
    def get_latest_selection_scenario(self) -> Optional[Scenario]:
        """Get the most recent selection scenario."""
        selection_scenarios = self.get_selection_scenarios()
        if not selection_scenarios:
            return None
        return selection_scenarios[0]  # Already sorted by creation date (most recent first)

    def has_load_scenario(self) -> bool:
        """Check if a load scenario is available."""
        return self.get_main_scenario() is not None

    def has_selection_scenarios(self) -> bool:
        """Check if any selection scenarios are available."""
        return len(self.get_selection_scenarios()) > 0

    def get_selection_scenarios_count(self) -> int:
        """Get the count of selection scenarios."""
        return len(self.get_selection_scenarios())

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

    def reset_analysis_scenarios(self) -> None:
        """Reset all analysis scenario data."""
        st.session_state[self.SELECTED_ANALYSE_INSTANCE_KEY] = None
        st.session_state[self.LOAD_SCENARIO_KEY] = None
        st.session_state[self.SELECTION_SCENARIOS_KEY] = []
        st.session_state[self.ANALYSIS_NAME_KEY] = None
        st.session_state[self.PIPELINE_ID_KEY] = None

    # Utility functions for data processing
    def get_index_columns_from_resource_set(self, resource_set: ResourceSet) -> List[str]:
        """Get columns that can be used as index (only is_index_column tagged columns, excluding Batch and Sample)"""
        try:
            resources = resource_set.get_resources()
            index_columns = []  # Don't include Batch and Sample

            for resource_name, resource in resources.items():
                if isinstance(resource, Table):
                    for col_name in resource.get_column_names():
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

            for resource_name, resource in resources.items():
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

    # Translation methods
    @classmethod
    def get_lang(cls) -> StreamlitTranslateLang:
        """Get the current language from the translate service."""
        translate_service = cls.get_translate_service()
        if translate_service:
            return translate_service.get_lang()
        return StreamlitTranslateLang.FR  # Default to French

    @classmethod
    def set_lang(cls, value: StreamlitTranslateLang) -> None:
        """Set the current language in the translate service."""
        translate_service = cls.get_translate_service()
        if translate_service:
            translate_service.change_lang(value)
            cls.set_translate_service(translate_service)

    @classmethod
    def get_translate_service(cls) -> StreamlitTranslateService:
        """Get the translate service from session state."""
        return st.session_state.get(cls.TRANSLATE_SERVICE, None)

    @classmethod
    def set_translate_service(cls, value: StreamlitTranslateService) -> None:
        """Set the translate service in session state."""
        st.session_state[cls.TRANSLATE_SERVICE] = value
