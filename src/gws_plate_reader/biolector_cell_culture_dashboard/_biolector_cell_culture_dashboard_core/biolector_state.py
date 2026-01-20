"""
BiolectorXT-specific state manager - extends CellCultureState for microplate recipes
"""

from gws_core import Scenario

from gws_plate_reader.biolector_cell_culture_dashboard._biolector_cell_culture_dashboard_core.biolector_recipe import (
    BiolectorRecipe,
)
from gws_plate_reader.cell_culture_app_core.cell_culture_recipe import CellCultureRecipe
from gws_plate_reader.cell_culture_app_core.cell_culture_state import CellCultureState


class BiolectorState(CellCultureState):
    """
    BiolectorXT-specific state manager - extends CellCultureState with BiolectorXT tags and methods.
    Supports microplate recipes with BiolectorXTLoadData task.
    """

    # BiolectorXT-specific tags
    TAG_FERMENTOR = "biolector"
    TAG_FERMENTOR_RECIPE_NAME = "biolector_recipe_name"
    TAG_FERMENTOR_PIPELINE_ID = "biolector_pipeline_id"
    TAG_FERMENTOR_SELECTION_STEP = "biolector_selection_step"
    TAG_FERMENTOR_QUALITY_CHECK_PARENT_SELECTION = "biolector_quality_check_parent_selection"
    TAG_FERMENTOR_ANALYSES_PARENT_SELECTION = "biolector_analyses_parent_selection"
    TAG_FERMENTOR_ANALYSES_PARENT_QUALITY_CHECK = "biolector_analyses_parent_quality_check"

    # Process names (BiolectorXT-specific)
    PROCESS_NAME_DATA_PROCESSING = 'biolector_data_processing'

    # Column name constants (BiolectorXT-specific)
    BASE_TIME_COLUMN_NAME = "Temps_en_h"  # BiolectorXT time column
    BATCH_COLUMN_NAME = "batch"
    SAMPLE_COLUMN_NAME = "sample"

    # Input keys for medium composition tables (optional)
    MEDIUM_TABLE_INPUT_KEY = "medium_table"
    INFO_TABLE_INPUT_KEY = "info_table"

    def create_recipe_from_scenario(self, scenario: Scenario) -> CellCultureRecipe:
        """
        Create a BiolectorRecipe instance from a scenario.

        :param scenario: The scenario to create the recipe from
        :return: A BiolectorRecipe instance
        """
        return BiolectorRecipe.from_scenario(scenario)
