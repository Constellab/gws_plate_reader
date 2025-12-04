"""
Biolector-specific state manager - extends CellCultureState
"""
import streamlit as st
from typing import Dict, List, Optional

from gws_core import Scenario, ResourceModel
from gws_plate_reader.cell_culture_app_core.cell_culture_state import CellCultureState
from gws_plate_reader.cell_culture_app_core.cell_culture_recipe import CellCultureRecipe
from gws_plate_reader.greencell_fermentor_dashboard._greencell_fermentor_dashboard_core.greencell_fermentor_recipe import GreencellFermentorRecipe


class GreencellFermentorState(CellCultureState):
    """
    Greencell Fermentor-specific state manager - extends CellCultureState with Greencell Fermentor tags and methods.
    """

    # Greencell Fermentor-specific tags
    TAG_FERMENTOR = "greencell_fermentor"
    TAG_FERMENTOR_RECIPE_NAME = "greencell_fermentor_recipe_name"
    TAG_FERMENTOR_PIPELINE_ID = "greencell_fermentor_pipeline_id"
    TAG_FERMENTOR_SELECTION_STEP = "greencell_fermentor_selection_step"
    TAG_FERMENTOR_QUALITY_CHECK_PARENT_SELECTION = "greencell_fermentor_quality_check_parent_selection"
    TAG_FERMENTOR_ANALYSES_PARENT_SELECTION = "greencell_fermentor_analyses_parent_selection"
    TAG_FERMENTOR_ANALYSES_PARENT_QUALITY_CHECK = "greencell_fermentor_analyses_parent_quality_check"

    # Process names (Greencell Fermentor-specific)
    PROCESS_NAME_DATA_PROCESSING = 'greencell_fermentor_data_processing'

    # Column name constants (Greencell Fermentor-specific)
    BASE_TIME_COLUMN_NAME = "Temps de culture (h)"
    BATCH_COLUMN_NAME = "ESSAI"
    SAMPLE_COLUMN_NAME = "FERMENTEUR"

    # Session state key for medium CSV input
    MEDIUM_CSV_INPUT_KEY = "medium_csv_input"

    def __init__(self, lang_translation_folder_path: str):
        """
        Initialize the Greencell Fermentor state manager.

        :param lang_translation_folder_path: Path to translation files folder
        """
        super().__init__(lang_translation_folder_path)

    def create_recipe_from_scenario(self, scenario: Scenario) -> CellCultureRecipe:
        """
        Create a GreencellFermentorRecipe instance from a scenario.

        :param scenario: The scenario to create the recipe from
        :return: A GreencellFermentorRecipe instance
        """
        return GreencellFermentorRecipe.from_scenario(scenario)
