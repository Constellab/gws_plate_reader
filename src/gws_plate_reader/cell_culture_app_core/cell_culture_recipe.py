"""
Base Recipe class for Cell Culture Dashboards
Encapsulates recipe information and scenarios - Abstract base class
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from gws_core import Scenario, User
from gws_core.tag.entity_tag_list import EntityTagList


@dataclass
class CellCultureRecipe(ABC):
    """
    Abstract base class for cell culture recipes with their metadata and scenarios.
    Subclasses should implement from_scenario() with specific tag extraction logic.
    """
    # Basic information
    id: str
    name: str
    analysis_type: str  # "standard" or "microplate"
    created_by: User
    created_at: datetime

    # Analysis scenarios organized by step
    scenarios: Dict[str, List[Scenario]]

    # Main scenario (data processing)
    main_scenario: Optional[Scenario] = None

    # Additional metadata
    pipeline_id: Optional[str] = None
    file_info: Optional[Dict[str, str]] = None  # Info about uploaded files
    has_data_raw: bool = True  # Whether this recipe has raw data (for feature extraction)

    @classmethod
    @abstractmethod
    def from_scenario(cls, scenario: Scenario) -> 'CellCultureRecipe':
        """
        Create a Recipe object from a scenario (independent of state).
        This method must be implemented by subclasses to define specific tag extraction logic.

        :param scenario: The main scenario of the recipe
        :return: Recipe instance
        """
        raise NotImplementedError("Subclasses must implement from_scenario()")

    @classmethod
    def _extract_tag_value(cls, entity_tag_list: EntityTagList, tag_key: str,
                           default: Optional[str] = None) -> Optional[str]:
        """
        Helper method to extract a single tag value.

        :param entity_tag_list: Entity tag list to search in
        :param tag_key: Key of the tag to extract
        :param default: Default value if tag not found
        :return: Tag value or default
        """
        tags = entity_tag_list.get_tags_by_key(tag_key)
        return tags[0].tag_value if tags else default

    @classmethod
    def _extract_file_info(cls, entity_tag_list: EntityTagList,
                           file_tags: List[tuple]) -> Dict[str, str]:
        """
        Helper method to extract file information from tags.

        :param entity_tag_list: Entity tag list to search in
        :param file_tags: List of (tag_key, display_name) tuples
        :return: Dictionary of display_name -> filename
        """
        file_info = {}
        for tag_key, display_name in file_tags:
            file_name_tags = entity_tag_list.get_tags_by_key(tag_key)
            if file_name_tags:
                file_info[display_name] = file_name_tags[0].tag_value
        return file_info

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

    def reload_scenarios(self) -> None:
        """
        Reload all scenarios from database to get updated status and sort them by creation date
        """
        # Reload main scenario
        if self.main_scenario:
            self.main_scenario = Scenario.get_by_id(self.main_scenario.id)

        # Reload all scenarios in each step
        for step_name, scenarios_list in self.scenarios.items():
            reloaded_scenarios = []
            for scenario in scenarios_list:
                reloaded_scenario = Scenario.get_by_id(scenario.id)
                reloaded_scenarios.append(reloaded_scenario)

            # Sort scenarios by creation date (oldest first, most recent last)
            reloaded_scenarios.sort(key=lambda s: s.created_at or s.last_modified_at, reverse=False)
            self.scenarios[step_name] = reloaded_scenarios

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
