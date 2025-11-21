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

    TAG_FERMENTOR = "fermentor"
    TAG_FERMENTOR_RECIPE_NAME = "fermentor_recipe_name"
    TAG_FERMENTOR_PIPELINE_ID = "fermentor_pipeline_id"
    TAG_DATA_PROCESSING = "data_processing"
    TAG_SELECTION_PROCESSING = "selection_processing"
    TAG_QUALITY_CHECK_PROCESSING = "quality_check_processing"
    TAG_ANALYSES_PROCESSING = "analyses_processing"
    TAG_MICROPLATE_ANALYSIS = "microplate_analysis"

    # Process names (subclasses must override)
    PROCESS_NAME_DATA_PROCESSING = None  # Must be set by subclasses

    ANALYSIS_TREE: Dict[str, Any] = {
        "medium_pca": {"title": "medium_pca_analysis", "icon": "scatter_plot", "children": []},
        "feature_extraction": {"title": "feature_extraction_analysis", "icon": "functions", "children": []},
        "logistic_growth": {"title": "logistic_growth_analysis", "icon": "show_chart", "children": []},
        "spline_growth": {"title": "spline_growth_analysis", "icon": "insights", "children": []},
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

            print('LOAD SCENARIO:', load_scenario)
            if not protocol_proxy:
                return FileNotFoundError

            print('NAME:', name)
            return protocol_proxy.get_input_resource_model(name)

        except Exception as e:
            # Return empty dict if there's an error accessing inputs
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
