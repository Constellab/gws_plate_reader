"""
Biolector-specific state manager - extends CellCultureState
"""
import streamlit as st
from typing import Dict, List, Optional

from gws_core import Scenario, ResourceModel
from gws_plate_reader.cell_culture_app_core.cell_culture_state import CellCultureState
from gws_plate_reader.cell_culture_app_core.cell_culture_recipe import CellCultureRecipe
from gws_plate_reader.biolector_dashboard._biolector_dashboard_core.biolector_recipe import BiolectorRecipe


class BiolectorState(CellCultureState):
    """
    Biolector-specific state manager - extends CellCultureState with Biolector tags and methods.
    """

    # Biolector-specific tags for data (override base TAG_FERMENTOR)
    TAG_FERMENTOR = "biolector"
    TAG_BATCH = "batch"
    TAG_SAMPLE = "sample"
    TAG_MISSING_VALUE = "missing_value"
    TAG_COLUMN_NAME = "column_name"

    # Recipe workflow tags (Biolector-specific)
    TAG_DATA_PROCESSING = "data_processing"
    TAG_SELECTION_PROCESSING = "selection_processing"
    TAG_QUALITY_CHECK_PROCESSING = "quality_check_processing"
    TAG_ANALYSES_PROCESSING = "analyses_processing"
    TAG_FERMENTOR_PIPELINE_ID = "biolector_pipeline_id"
    TAG_BIOLECTOR_SELECTION_STEP = "biolector_selection_step"
    TAG_BIOLECTOR_QUALITY_CHECK_PARENT_SELECTION = "biolector_quality_check_parent_selection"
    TAG_BIOLECTOR_ANALYSES_PARENT_SELECTION = "biolector_analyses_parent_selection"
    TAG_BIOLECTOR_ANALYSES_PARENT_QUALITY_CHECK = "biolector_analyses_parent_quality_check"

    # Process names (Biolector-specific)
    PROCESS_NAME_DATA_PROCESSING = 'biolector_data_processing'

    # Additional Biolector session state keys
    LOAD_SCENARIO_KEY = "load_scenario"
    SELECTION_SCENARIOS_KEY = "selection_scenarios"
    RECIPE_NAME_KEY = "recipe_name"
    PIPELINE_ID_KEY = "pipeline_id"

    # File upload keys (Biolector-specific)
    BIOLECTOR_FILE_KEY = "biolector_file"  # For Biolector XT Excel file

    def __init__(self, lang_translation_folder_path: str):
        """
        Initialize the Biolector state manager.

        :param lang_translation_folder_path: Path to translation files folder
        """
        super().__init__(lang_translation_folder_path)
        self._initialize_biolector_session_state()

    def create_recipe_from_scenario(self, scenario: Scenario) -> CellCultureRecipe:
        """
        Create a BiolectorRecipe instance from a scenario.

        :param scenario: The scenario to create the recipe from
        :return: A BiolectorRecipe instance
        """
        return BiolectorRecipe.from_scenario(scenario)

    def _initialize_biolector_session_state(self) -> None:
        """Initialize Biolector-specific session state variables."""
        if self.LOAD_SCENARIO_KEY not in st.session_state:
            st.session_state[self.LOAD_SCENARIO_KEY] = None

        if self.SELECTION_SCENARIOS_KEY not in st.session_state:
            st.session_state[self.SELECTION_SCENARIOS_KEY] = []

        if self.RECIPE_NAME_KEY not in st.session_state:
            st.session_state[self.RECIPE_NAME_KEY] = ""

        if self.PIPELINE_ID_KEY not in st.session_state:
            st.session_state[self.PIPELINE_ID_KEY] = None

        if self.BIOLECTOR_FILE_KEY not in st.session_state:
            st.session_state[self.BIOLECTOR_FILE_KEY] = None

    # Load scenario management
    def get_load_scenario(self) -> Optional[Scenario]:
        """Get the load scenario from session state."""
        return st.session_state.get(self.LOAD_SCENARIO_KEY)

    def set_load_scenario(self, scenario: Scenario) -> None:
        """Set the load scenario in session state."""
        st.session_state[self.LOAD_SCENARIO_KEY] = scenario

    # Selection scenarios management
    def get_selection_scenarios(self) -> List[Scenario]:
        """Get the selection scenarios from session state."""
        return st.session_state.get(self.SELECTION_SCENARIOS_KEY, [])

    def add_selection_scenario(self, scenario: Scenario) -> None:
        """Add a selection scenario to session state."""
        scenarios = self.get_selection_scenarios()
        scenarios.append(scenario)
        st.session_state[self.SELECTION_SCENARIOS_KEY] = scenarios

    # Recipe metadata
    def get_recipe_name(self) -> str:
        """Get the recipe name from session state."""
        return st.session_state.get(self.RECIPE_NAME_KEY, "")

    def set_recipe_name(self, name: str) -> None:
        """Set the recipe name in session state."""
        st.session_state[self.RECIPE_NAME_KEY] = name

    def get_pipeline_id(self) -> Optional[str]:
        """Get the pipeline ID from session state."""
        return st.session_state.get(self.PIPELINE_ID_KEY)

    def set_pipeline_id(self, pipeline_id: str) -> None:
        """Set the pipeline ID in session state."""
        st.session_state[self.PIPELINE_ID_KEY] = pipeline_id

    # Biolector file management
    def get_biolector_file_input_resource_model(self) -> Optional[ResourceModel]:
        """Get the Biolector Excel file resource model from session state."""
        return st.session_state.get(self.BIOLECTOR_FILE_KEY)

    def set_biolector_file_input_resource_model(self, resource_model: ResourceModel) -> None:
        """Set the Biolector Excel file resource model in session state."""
        st.session_state[self.BIOLECTOR_FILE_KEY] = resource_model

    # Quality check scenario management (inherits from parent)
    def get_quality_check_scenarios(self) -> List[Scenario]:
        """Get all quality check scenarios."""
        return st.session_state.get("quality_check_scenarios", [])

    def add_quality_check_scenario(self, scenario: Scenario) -> None:
        """Add a quality check scenario."""
        scenarios = self.get_quality_check_scenarios()
        scenarios.append(scenario)
        st.session_state["quality_check_scenarios"] = scenarios

    def get_quality_check_scenario_output_resource_model(self, scenario: Scenario) -> Optional[ResourceModel]:
        """
        Get the output ResourceModel from a quality check scenario.

        :param scenario: The quality check scenario
        :return: ResourceModel or None
        """
        if not scenario:
            return None

        scenario_proxy = scenario.get_protocol().get_protocol_proxy()

        # Try to get the interpolated_resourceset output
        try:
            output_resource = scenario_proxy.get_output("interpolated_resourceset")
            if output_resource:
                return ResourceModel.get_by_id(output_resource.id)
        except Exception:
            pass

        return None
