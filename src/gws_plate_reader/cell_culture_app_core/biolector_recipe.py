"""
BiolectorXT Recipe class - extends CellCultureRecipe with BiolectorXT-specific logic for microplate recipes
"""

from dataclasses import dataclass

from gws_core import Scenario
from gws_core.scenario.scenario_proxy import ScenarioProxy
from gws_core.tag.entity_tag_list import EntityTagList
from gws_core.tag.tag_entity_type import TagEntityType

from gws_plate_reader.cell_culture_app_core.cell_culture_recipe import CellCultureRecipe

# Tag constants for BiolectorXT recipes
_TAG_BIOPROCESS_RECIPE_NAME = "bioprocess_recipe_name"
_TAG_BIOPROCESS_PIPELINE_ID = "bioprocess_pipeline_id"


@dataclass
class BiolectorRecipe(CellCultureRecipe):
    """
    Represents a BiolectorXT recipe with its metadata and scenarios.
    Extends CellCultureRecipe with BiolectorXT-specific tag extraction.
    BiolectorXT recipes support microplate analysis.
    """

    @classmethod
    def from_scenario(cls, scenario: Scenario) -> "BiolectorRecipe":
        """
        Create a BiolectorXT Recipe object from a scenario with BiolectorXT-specific tags.

        :param scenario: The main scenario of the recipe
        :return: BiolectorRecipe instance
        """
        # Get tags from scenario
        entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)

        # Extract recipe name using BiolectorXT-specific tag
        name = cls._extract_tag_value(entity_tag_list, _TAG_BIOPROCESS_RECIPE_NAME, scenario.title)

        # Extract pipeline ID using BiolectorXT-specific tag
        pipeline_id = cls._extract_tag_value(
            entity_tag_list, _TAG_BIOPROCESS_PIPELINE_ID, scenario.id
        )

        # BiolectorXT supports microplate analysis
        analysis_type = "microplate"

        # Extract BiolectorXT-specific file information
        file_tags = [
            ("bxt_excel_file", "BXT Excel"),
            ("folder_metadata_file", "Folder Metadata"),
            ("medium_table_file", "Medium Table"),
            ("info_table_file", "Info Table"),
        ]
        file_info = cls._extract_file_info(entity_tag_list, file_tags)

        try:
            scenario_proxy = ScenarioProxy.from_existing_scenario(scenario.id)
            protocol_proxy = scenario_proxy.get_protocol()

            if not protocol_proxy:
                return FileNotFoundError

            resource_model = protocol_proxy.get_input_resource_model("medium_table_input")
            resource = resource_model.get_resource() if resource_model else None
            has_medium_info = resource is not None
        except Exception:
            has_medium_info = False

        # Initialize with main scenario only, other scenarios will be loaded separately
        scenarios_by_step = {"data_processing": [scenario]}

        return cls(
            id=scenario.id,
            name=name,
            analysis_type=analysis_type,
            created_by=scenario.created_by,
            created_at=scenario.created_at,
            scenarios=scenarios_by_step,
            main_scenario=scenario,
            pipeline_id=pipeline_id,
            file_info=file_info,
            has_data_raw=True,  # BiolectorXT recipes have raw data from the parsed_data_tables output
            has_medium_info=has_medium_info,
        )
