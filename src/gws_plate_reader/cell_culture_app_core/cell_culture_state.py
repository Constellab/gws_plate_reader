"""
Base State class for Cell Culture Dashboards
Manages common state and session management - Abstract base class
"""
import streamlit as st
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from gws_core import ScenarioProxy, Scenario, ResourceSet
from gws_core.resource.resource import Resource
from gws_core.resource.resource_model import ResourceModel
from gws_core.streamlit import StreamlitTranslateService
import pandas as pd

from gws_core import Table, EntityTagList, TagEntityType, Tag

from .cell_culture_recipe import CellCultureRecipe


class CellCultureState(ABC):
    """
    Abstract base class for managing state in cell culture dashboard apps.
    Provides common session state management and recipe handling.
    Subclasses should define their own constants for tags and keys.
    """

    # Common session state keys (subclasses can override or extend)
    LANG_KEY = "lang_select"
    TRANSLATE_SERVICE = "translate_service"
    SELECTED_RECIPE_INSTANCE_KEY = "selected_recipe_instance"
    PROCESSING_RESULTS_KEY = "processing_results"
    PROCESSING_COMPLETED_KEY = "processing_completed"
    SELECTION_DATA_KEY = "selection_data"
    SELECTED_RESOURCES_KEY = "selected_resources"
    SELECTED_RESOURCE_SET_KEY = "selected_resource_set"
    MEDIUM_CSV_INPUT_KEY = "medium_csv_input"

    # Additional common session state keys
    LOAD_SCENARIO_KEY = "load_scenario"
    SELECTION_SCENARIOS_KEY = "selection_scenarios"
    RECIPE_NAME_KEY = "recipe_name"
    PIPELINE_ID_KEY = "pipeline_id"

    # Common tags (can be overridden by subclasses)
    TAG_FERMENTOR = "fermentor"
    TAG_FERMENTOR_RECIPE_NAME = "fermentor_recipe_name"
    TAG_FERMENTOR_PIPELINE_ID = "fermentor_pipeline_id"
    TAG_DATA_PROCESSING = "data_processing"
    TAG_SELECTION_PROCESSING = "selection_processing"
    TAG_QUALITY_CHECK_PROCESSING = "quality_check_processing"
    TAG_ANALYSES_PROCESSING = "analyses_processing"
    TAG_MICROPLATE_ANALYSIS = "microplate_analysis"
    TAG_FERMENTOR_SELECTION_STEP = "fermentor_selection_step"
    TAG_FERMENTOR_QUALITY_CHECK_PARENT_SELECTION = "fermentor_quality_check_parent_selection"
    TAG_FERMENTOR_ANALYSES_PARENT_SELECTION = "fermentor_analyses_parent_selection"
    TAG_FERMENTOR_ANALYSES_PARENT_QUALITY_CHECK = "fermentor_analyses_parent_quality_check"

    # Common tags for data
    TAG_BATCH = "batch"
    TAG_SAMPLE = "sample"
    TAG_MEDIUM = "medium"
    TAG_MISSING_VALUE = "missing_value"
    TAG_COLUMN_NAME = "column_name"

    # Column name constants (to be overridden by subclasses)
    BASE_TIME_COLUMN_NAME = None
    BATCH_COLUMN_NAME = None
    SAMPLE_COLUMN_NAME = None

    # Common output names
    LOAD_SCENARIO_METADATA_OUTPUT_NAME = "metadata_table"
    LOAD_SCENARIO_OUTPUT_NAME = 'load_scenario_output'
    INTERPOLATION_SCENARIO_OUTPUT_NAME = 'interpolation_scenario_output'
    QUALITY_CHECK_SCENARIO_OUTPUT_NAME = 'quality_check_scenario_output'
    QUALITY_CHECK_SCENARIO_INTERPOLATED_OUTPUT_NAME = 'quality_check_scenario_interpolated_output'
    QUALITY_CHECK_SCENARIO_METADATA_OUTPUT_NAME = 'quality_check_scenario_metadata_output'

    # Process names (subclasses must override)
    PROCESS_NAME_DATA_PROCESSING = None  # Must be set by subclasses

    ANALYSIS_TREE: Dict[str, Any] = {
        "medium_pca": {"title": "medium_pca_analysis", "icon": "scatter_plot", "children": []},
        "medium_umap": {"title": "medium_umap_analysis", "icon": "bubble_chart", "children": []},
        "feature_extraction": {"title": "feature_extraction_analysis", "icon": "functions", "children": []}
    }

    POST_FEATURE_EXTRACTION_ANALYSIS_TREE: Dict[str, Any] = {
        "metadata_feature_umap": {"title": "metadata_feature_umap_analysis", "icon": "bubble_chart", "children": []},
        "pls_regression": {"title": "pls_regression_analysis", "icon": "insights", "children": []},
        "random_forest_regression": {"title": "random_forest_regression_analysis", "icon": "account_tree", "children": []},
        "causal_effect": {"title": "causal_effect_analysis", "icon": "link", "children": []},
        "optimization": {"title": "optimization_analysis", "icon": "auto_mode", "children": []},
    }

    def __init__(self, lang_translation_folder_path: str):
        """
        Initialize the state manager with translation service.

        :param lang_translation_folder_path: Path to translation files folder
        """
        # Initialize translation service
        translate_service = StreamlitTranslateService(lang_translation_folder_path)
        st.session_state[self.TRANSLATE_SERVICE] = translate_service

        # Initialize session state variables
        self._initialize_session_state()

    def _initialize_session_state(self) -> None:
        """Initialize common session state variables if they don't exist."""
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

    # Translation service methods
    def get_translate_service(self) -> StreamlitTranslateService:
        """Get the translation service from session state."""
        return st.session_state.get(self.TRANSLATE_SERVICE)

    # Abstract method for creating recipe instances (to be implemented by subclasses)
    @abstractmethod
    def create_recipe_from_scenario(self, scenario: Scenario) -> CellCultureRecipe:
        """
        Create a recipe instance from a scenario.
        Must be implemented by subclasses to return the appropriate Recipe class.

        :param scenario: The scenario to create the recipe from
        :return: A CellCultureRecipe instance (or subclass)
        """
        pass

    # Recipe instance management
    def get_selected_recipe_instance(self) -> Optional[CellCultureRecipe]:
        """Get the selected Recipe instance from session state."""
        return st.session_state.get(self.SELECTED_RECIPE_INSTANCE_KEY)

    def set_selected_recipe_instance(self, recipe_instance: CellCultureRecipe) -> None:
        """Set the selected Recipe instance in session state."""
        st.session_state[self.SELECTED_RECIPE_INSTANCE_KEY] = recipe_instance

    # Processing results methods
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

    # Selection data methods
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

    # Recipe instance delegation methods
    def get_recipe_name(self) -> Optional[str]:
        """Get the current recipe name from the Recipe instance."""
        recipe = self.get_selected_recipe_instance()
        return recipe.name if recipe else None

    def get_pipeline_id(self) -> Optional[str]:
        """Get the current pipeline ID from the Recipe instance."""
        recipe = self.get_selected_recipe_instance()
        return recipe.pipeline_id if recipe else None

    def get_selection_scenarios(self) -> List[Scenario]:
        """Get the list of selection scenarios from the Recipe instance."""
        recipe = self.get_selected_recipe_instance()
        return recipe.get_selection_scenarios() if recipe else []

    def get_visualization_scenarios(self) -> List[Scenario]:
        """Get the list of visualization scenarios from the Recipe instance."""
        recipe = self.get_selected_recipe_instance()
        return recipe.get_visualization_scenarios() if recipe else []

    def get_main_scenario(self) -> Optional[Scenario]:
        """Get the main scenario from the Recipe instance."""
        recipe = self.get_selected_recipe_instance()
        return recipe.get_load_scenario() if recipe else None

    def get_load_scenario_input_resource_model(self, name: str) -> ResourceModel:
        """
        Get the input resource from the load scenario of the current recipe.

        :return: The input resource or None if not found
        """
        load_scenario = self.get_main_scenario()
        if not load_scenario:
            return None

        try:
            scenario_proxy = ScenarioProxy.from_existing_scenario(load_scenario.id)
            protocol_proxy = scenario_proxy.get_protocol()

            if not protocol_proxy:
                return FileNotFoundError

            return protocol_proxy.get_input_resource_model(name)

        except Exception as e:
            # Return empty dict if there's an error accessing inputs
            return None

    def get_load_scenario_output_resource_model(self, name: str) -> ResourceModel:
        """
        Get the output resource from the load scenario of the current recipe.

        :return: The output resource or None if not found
        """
        load_scenario = self.get_main_scenario()
        if not load_scenario:
            return None

        try:
            scenario_proxy = ScenarioProxy.from_existing_scenario(load_scenario.id)
            protocol_proxy = scenario_proxy.get_protocol()

            if not protocol_proxy:
                return FileNotFoundError

            return protocol_proxy.get_output_resource_model(name)

        except Exception as e:
            # Return empty dict if there's an error accessing outputs
            return None

    def get_scenario_output_resource_model(self, scenario: Scenario, name: str) -> ResourceModel:
        """
        Get the output resource from a given scenario.

        :param scenario: The scenario to get the output from
        :param name: The name of the output resource
        :return: The output resource model or None if not found
        """
        if not scenario:
            return None

        try:
            scenario_proxy = ScenarioProxy.from_existing_scenario(scenario.id)
            protocol_proxy = scenario_proxy.get_protocol()

            if not protocol_proxy:
                return FileNotFoundError

            return protocol_proxy.get_output_resource_model(name)

        except Exception as e:
            # Return empty dict if there's an error accessing outputs
            return None

    def get_medium_csv_input_resource_model(self) -> Optional[ResourceModel]:
        """
        Get the medium CSV input resource model from the load scenario.

        :return: The medium CSV input resource model or None if not found
        """
        return self.get_load_scenario_input_resource_model(self.MEDIUM_CSV_INPUT_KEY)

    def add_scenarios_to_recipe(self, step: str, scenarios: List[Scenario]) -> None:
        """Add scenarios to the current Recipe instance for a specific step."""
        recipe = self.get_selected_recipe_instance()
        if recipe:
            recipe.add_scenarios_by_step(step, scenarios)

    def update_recipe_with_selection_scenarios(self, selection_scenarios: List[Scenario]) -> None:
        """Update the current Recipe instance with selection scenarios."""
        recipe = self.get_selected_recipe_instance()
        if recipe:
            recipe.add_selection_scenarios(selection_scenarios)

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
        st.session_state[self.SELECTED_RECIPE_INSTANCE_KEY] = None

    def reset_selection(self) -> None:
        """Reset only the selection data."""
        st.session_state[self.SELECTION_DATA_KEY] = []
        st.session_state[self.SELECTED_RESOURCES_KEY] = []
        st.session_state[self.SELECTED_RESOURCE_SET_KEY] = None

    # Scenario utility methods
    def add_selection_scenario(self, scenario: Scenario) -> None:
        """Add a new selection scenario to the current recipe."""
        recipe = self.get_selected_recipe_instance()
        if recipe:
            current_scenarios = recipe.get_selection_scenarios()
            current_scenarios.append(scenario)
            recipe.add_scenarios_by_step('selection', current_scenarios)

    def get_latest_selection_scenario(self) -> Optional[Scenario]:
        """Get the most recent selection scenario."""
        selection_scenarios = self.get_selection_scenarios()
        if not selection_scenarios:
            return None
        return selection_scenarios[0]  # Assume sorted by creation date

    def has_load_scenario(self) -> bool:
        """Check if a load scenario is available."""
        return self.get_main_scenario() is not None

    def has_selection_scenarios(self) -> bool:
        """Check if any selection scenarios are available."""
        return len(self.get_selection_scenarios()) > 0

    def get_selection_scenarios_count(self) -> int:
        """Get the count of selection scenarios."""
        return len(self.get_selection_scenarios())

    # Navigation methods (can be overridden by subclasses)
    def get_selected_step(self) -> str:
        """Get the currently selected analysis step."""
        return st.session_state.get("selected_step", "data_overview")

    def set_selected_step(self, step: str) -> None:
        """Set the currently selected analysis step."""
        st.session_state["selected_step"] = step

    def set_selected_folder_id(self, folder_id: str) -> None:
        """Set the selected folder ID."""
        st.session_state["selected_folder_id"] = folder_id

    def get_selected_folder_id(self) -> Optional[str]:
        """Get the selected folder ID."""
        return st.session_state.get("selected_folder_id")

    def save_df_as_table(self,
                         df: pd.DataFrame,
                         table_name: str,
                         scenario: Scenario):
        """Save a DataFrame as a Table in the given scenario."""
        table = Table(data=df)
        table.name = table_name

        # Tags
        entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)

        tags_dict = entity_tag_list.get_tags_as_dict()

        tags: List[Tag] = []

        if self.TAG_FERMENTOR in tags_dict:
            tags.append(Tag(key=self.TAG_FERMENTOR, value=tags_dict[self.TAG_FERMENTOR]))

        if self.TAG_FERMENTOR_RECIPE_NAME in tags_dict:
            tags.append(Tag(key=self.TAG_FERMENTOR_RECIPE_NAME,
                            value=tags_dict[self.TAG_FERMENTOR_RECIPE_NAME]))

        table.tags.add_tags(tags)

        table_resource_model = ResourceModel.from_resource(table, scenario=scenario)

        table_resource_model.save()

    # Common utility methods for ResourceSet processing
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

    def get_quality_check_scenario_output_resource_model(
            self, quality_check_scenario: Scenario) -> Optional[ResourceModel]:
        """Get the filtered real data ResourceSet from a quality check scenario (for analyses)"""
        from gws_core.protocol.protocol_proxy import ProtocolProxy
        protocol_proxy = self.get_quality_check_protocol_proxy(quality_check_scenario)
        if not protocol_proxy:
            return None

        return protocol_proxy.get_output_resource_model(self.QUALITY_CHECK_SCENARIO_OUTPUT_NAME)

    def get_interpolation_scenario_output(self, selection_scenario: Scenario) -> Optional[ResourceSet]:
        """Get the subsampled ResourceSet from a selection scenario"""
        try:
            scenario_proxy = ScenarioProxy.from_existing_scenario(selection_scenario.id)
            protocol_proxy = scenario_proxy.get_protocol()

            return protocol_proxy.get_output(self.INTERPOLATION_SCENARIO_OUTPUT_NAME)
        except Exception:
            return None

    def get_quality_check_protocol_proxy(self, quality_check_scenario: Scenario):
        """Get the protocol proxy from a quality check scenario"""
        from gws_core.protocol.protocol_proxy import ProtocolProxy
        try:
            scenario_proxy = ScenarioProxy.from_existing_scenario(quality_check_scenario.id)
            protocol_proxy = scenario_proxy.get_protocol()

            return protocol_proxy
        except Exception:
            return None

    def get_quality_check_scenario_interpolated_output_resource_model(
            self, quality_check_scenario: Scenario) -> Optional[ResourceModel]:
        """Get the filtered subsampled ResourceSet from a quality check scenario"""
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

    # Utility functions for data processing with ResourceSet
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
                        col_tags = resource.get_column_tags_by_name(col_name)
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
