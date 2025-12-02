import streamlit as st
import os
from typing import Optional

from gws_core import Scenario
from gws_core.streamlit import StreamlitTranslateLang

from gws_plate_reader.cell_culture_app_core.cell_culture_state import CellCultureState
from gws_plate_reader.cell_culture_app_core.cell_culture_recipe import CellCultureRecipe
from gws_plate_reader.fermentalg_dashboard._fermentalg_dashboard_core.fermentalg_recipe import FermentalgRecipe


class FermentalgState(CellCultureState):
    """
    Fermentalg-specific state manager - extends CellCultureState with Fermentalg tags and methods.
    """

    # Fermentalg-specific tags
    TAG_FERMENTOR = "fermentor_fermentalg"
    TAG_MICROPLATE_ANALYSIS = "microplate_analysis"
    TAG_FERMENTOR_PIPELINE_ID = "fermentor_fermentalg_pipeline_id"

    # Process names (Fermentalg-specific)
    PROCESS_NAME_DATA_PROCESSING = 'fermentalg_data_processing'

    # Column name constants (Fermentalg-specific)
    BASE_TIME_COLUMN_NAME = "Temps de culture (h)"
    BATCH_COLUMN_NAME = "ESSAI"
    SAMPLE_COLUMN_NAME = "FERMENTEUR"

    def __init__(self, lang_translation_folder_path: str = None):
        """Initialize the Fermentalg state manager with translation service."""
        # Get the path of the current file's directory if not provided
        if lang_translation_folder_path is None:
            lang_translation_folder_path = os.path.dirname(os.path.abspath(__file__))

        # Call parent constructor
        super().__init__(lang_translation_folder_path)

    def create_recipe_from_scenario(self, scenario: Scenario) -> CellCultureRecipe:
        """
        Create a FermentalgRecipe instance from a scenario.

        :param scenario: The scenario to create the recipe from
        :return: A FermentalgRecipe instance
        """
        return FermentalgRecipe.from_scenario(scenario)

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
