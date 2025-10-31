"""
Fermentalg Recipe class - extends CellCultureRecipe with Fermentalg-specific logic
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from gws_core import Scenario
from gws_core.tag.entity_tag_list import EntityTagList
from gws_core.tag.tag_entity_type import TagEntityType

from gws_cell_culture import CellCultureRecipe


@dataclass
class FermentalgRecipe(CellCultureRecipe):
    """
    Represents a Fermentalg recipe with its metadata and scenarios.
    Extends CellCultureRecipe with Fermentalg-specific tag extraction.
    """

    @classmethod
    def from_scenario(cls, scenario: Scenario) -> 'FermentalgRecipe':
        """
        Create a Fermentalg Recipe object from a scenario with Fermentalg-specific tags.

        :param scenario: The main scenario of the recipe
        :return: FermentalgRecipe instance
        """
        # Get tags from scenario
        entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)

        # Extract recipe name using Fermentalg-specific tag
        name = cls._extract_tag_value(entity_tag_list, "fermentor_recipe_name", scenario.title)

        # Extract pipeline ID using Fermentalg-specific tag
        pipeline_id = cls._extract_tag_value(entity_tag_list, "fermentor_fermentalg_pipeline_id", scenario.id)

        # Extract analysis type (microplate or standard)
        microplate_value = cls._extract_tag_value(entity_tag_list, "microplate_analysis", "false")
        analysis_type = "microplate" if microplate_value == "true" else "standard"

        # Extract Fermentalg-specific file information
        file_tags = [
            ("info_csv_file", "Info CSV"),
            ("raw_data_csv_file", "Raw Data CSV"),
            ("medium_csv_file", "Medium CSV"),
            ("followup_zip_file", "Follow-up ZIP")
        ]
        file_info = cls._extract_file_info(entity_tag_list, file_tags)

        # Initialize with main scenario only, other scenarios will be loaded separately
        scenarios_by_step = {
            "data_processing": [scenario]
        }

        return cls(
            id=scenario.id,
            name=name,
            analysis_type=analysis_type,
            created_by=scenario.created_by,
            created_at=scenario.created_at,
            scenarios=scenarios_by_step,
            main_scenario=scenario,
            pipeline_id=pipeline_id,
            file_info=file_info
        )

    def add_selection_scenarios(self, selection_scenarios: List[Scenario]) -> None:
        """
        Add selection scenarios to this recipe

        :param selection_scenarios: List of selection scenarios to add
        """
        self.add_scenarios_by_step('selection', selection_scenarios)

    def add_scenarios_by_step(self, step: str, scenarios: List[Scenario]):
        """
        Add scenarios for a specific step

        :param step: Step name (e.g., 'selection', 'visualization')
        :param scenarios: List of scenarios for this step
        """
        self.scenarios[step] = scenarios

    def get_scenarios_for_step(self, step: str) -> List[Scenario]:
        """
        Get scenarios for a specific step

        :param step: Step name
        :return: List of scenarios for the step
        """
        return self.scenarios.get(step, [])

    def get_load_scenario(self) -> Optional[Scenario]:
        """
        Get the main data processing scenario

        :return: Main scenario or None
        """
        return self.scenarios.get('data_processing', [None])[0]

    def get_selection_scenarios(self) -> List[Scenario]:
        """
        Get selection scenarios for this recipe

        :return: List of selection scenarios
        """
        return self.get_scenarios_for_step('selection')

    def get_quality_check_scenarios(self) -> List[Scenario]:
        """
        Get all quality check scenarios for this recipe

        :return: List of quality check scenarios
        """
        return self.get_scenarios_for_step('quality_check')

    def get_quality_check_scenarios_for_selection(self, selection_id: str) -> List[Scenario]:
        """
        Get quality check scenarios linked to a specific selection scenario

        :param selection_id: ID of the parent selection scenario
        :return: List of quality check scenarios for this selection
        """
        all_qc_scenarios = self.get_quality_check_scenarios()

        # Filter by parent selection ID tag
        filtered_scenarios = []
        for scenario in all_qc_scenarios:
            entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)
            parent_selection_tags = entity_tag_list.get_tags_by_key("fermentor_quality_check_parent_selection")

            if parent_selection_tags and parent_selection_tags[0].tag_value == selection_id:
                filtered_scenarios.append(scenario)

        return filtered_scenarios

    def add_quality_check_scenario(self, selection_id: str, quality_check_scenario: Scenario) -> None:
        """
        Add a quality check scenario to this recipe

        :param selection_id: ID of the parent selection scenario
        :param quality_check_scenario: Quality check scenario to add
        """
        # Get existing quality check scenarios
        existing_qc_scenarios = self.get_quality_check_scenarios()

        # Add new scenario
        updated_qc_scenarios = [quality_check_scenario] + existing_qc_scenarios

        # Update the scenarios dict
        self.add_scenarios_by_step('quality_check', updated_qc_scenarios)

    def get_selection_scenarios_organized(self) -> Dict[str, Scenario]:
        """
        Get selection scenarios organized by their display name (timestamp)

        :return: Dictionary with display name as key and scenario as value
        """
        selection_scenarios = self.get_selection_scenarios()
        organized = {}

        for scenario in selection_scenarios:
            # Extract display name from title or use scenario ID as fallback
            if "Sélection - " in scenario.title:
                display_name = scenario.title
            else:
                display_name = f"Sélection - {scenario.id[:8]}"

            organized[display_name] = scenario

        return organized

    def get_visualization_scenarios(self) -> List[Scenario]:
        """
        Get visualization scenarios for this recipe

        :return: List of visualization scenarios
        """
        return self.get_scenarios_for_step('visualization')

    def has_selection_scenarios(self) -> bool:
        """
        Check if recipe has selection scenarios

        :return: True if selection scenarios exist
        """
        return 'selection' in self.scenarios and len(self.scenarios['selection']) > 0

    def has_quality_check_scenarios(self) -> bool:
        """
        Check if recipe has quality check scenarios

        :return: True if quality check scenarios exist
        """
        return 'quality_check' in self.scenarios and len(self.scenarios['quality_check']) > 0

    def has_visualization_scenarios(self) -> bool:
        """
        Check if recipe has visualization scenarios

        :return: True if visualization scenarios exist
        """
        return 'visualization' in self.scenarios and len(self.scenarios['visualization']) > 0

    def get_file_count(self) -> int:
        """
        Get number of uploaded files

        :return: Number of files
        """
        return len(self.file_info) if self.file_info else 0

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation

        :return: Dictionary with recipe information
        """
        return {
            'id': self.id,
            'name': self.name,
            'analysis_type': self.analysis_type,
            'created_by': self.created_by.to_dto().model_dump() if self.created_by else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'pipeline_id': self.pipeline_id,
            'file_info': self.file_info,
            'file_count': self.get_file_count(),
            'has_selection': self.has_selection_scenarios(),
            'has_visualization': self.has_visualization_scenarios(),
            'scenario_counts': {
                step: len(scenarios) for step, scenarios in self.scenarios.items()
            }
        }
