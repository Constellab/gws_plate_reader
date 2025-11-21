"""
Biolector Recipe class - extends CellCultureRecipe with Biolector-specific logic
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from gws_core import Scenario
from gws_core.tag.entity_tag_list import EntityTagList
from gws_core.tag.tag_entity_type import TagEntityType
from gws_plate_reader.cell_culture_app_core.cell_culture_recipe import CellCultureRecipe


@dataclass
class BiolectorRecipe(CellCultureRecipe):
    """
    Represents a Biolector recipe with its metadata and scenarios.
    Extends CellCultureRecipe with Biolector-specific tag extraction.
    """

    @classmethod
    def from_scenario(cls, scenario: Scenario) -> 'BiolectorRecipe':
        """
        Create a Biolector Recipe object from a scenario with Biolector-specific tags.

        :param scenario: The main scenario of the recipe
        :return: BiolectorRecipe instance
        """
        # Get tags from scenario
        entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)

        # Extract recipe name using Biolector-specific tag
        name = cls._extract_tag_value(entity_tag_list, "biolector_recipe_name", scenario.title)

        # Extract pipeline ID using Biolector-specific tag
        pipeline_id = cls._extract_tag_value(entity_tag_list, "biolector_pipeline_id", scenario.id)

        # For Biolector, we don't have the microplate distinction
        analysis_type = "standard"

        # Extract Biolector-specific file information
        file_tags = [
            ("biolector_file", "Biolector Excel File")
        ]
        file_info = cls._extract_file_info(entity_tag_list, file_tags)

        # Initialize with main scenario only, other scenarios will be loaded separately
        return cls(
            name=name,
            id=scenario.id,
            pipeline_id=pipeline_id,
            main_scenario=scenario,
            analysis_type=analysis_type,
            file_info=file_info,
            # Child scenarios are initialized empty and loaded separately
            selection_scenarios=[],
            quality_check_scenarios=[],
            medium_pca_scenarios=[],
            feature_extraction_scenarios=[],
            logistic_growth_scenarios=[],
            spline_growth_scenarios=[]
        )

    @staticmethod
    def _extract_tag_value(entity_tag_list: EntityTagList, tag_key: str, default: str = "") -> str:
        """Extract a tag value from entity tag list."""
        tags = entity_tag_list.get_tags_by_key(tag_key)
        return tags[0].tag_value if tags else default

    @staticmethod
    def _extract_file_info(entity_tag_list: EntityTagList, file_tags: List[tuple]) -> Dict[str, str]:
        """
        Extract file information from tags.

        :param entity_tag_list: Entity tag list
        :param file_tags: List of tuples (tag_key, display_name)
        :return: Dictionary with file info
        """
        file_info = {}
        for tag_key, display_name in file_tags:
            file_name = BiolectorRecipe._extract_tag_value(entity_tag_list, tag_key)
            if file_name:
                file_info[display_name] = file_name
        return file_info
