"""
Analyse class for Fermentalg Dashboard
Encapsulates analysis information and scenarios
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from gws_core import Scenario, User
from gws_core.tag.entity_tag_list import EntityTagList
from gws_core.tag.tag_entity_type import TagEntityType


@dataclass
class Analyse:
    """
    Represents a Fermentalg analysis with its metadata and scenarios
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

    @classmethod
    def from_scenario(cls, scenario: Scenario) -> 'Analyse':
        """
        Create an Analyse object from a scenario (independent of state)

        :param scenario: The main scenario of the analysis
        :return: Analyse instance
        """
        # Get tags from scenario
        entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)

        # Extract analysis name using known tag keys
        analysis_name_tags = entity_tag_list.get_tags_by_key("fermentor_analysis_name")
        name = analysis_name_tags[0].tag_value if analysis_name_tags else scenario.title

        # Extract pipeline ID
        pipeline_id_tags = entity_tag_list.get_tags_by_key("fermentor_fermentalg_pipeline_id")
        pipeline_id = pipeline_id_tags[0].tag_value if pipeline_id_tags else scenario.id

        # Extract analysis type (microplate or standard)
        microplate_tags = entity_tag_list.get_tags_by_key("microplate_analysis")
        analysis_type = "microplate" if (microplate_tags and
                                         microplate_tags[0].tag_value == "true") else "standard"

        # Extract file information
        file_info = {}
        file_tags = [
            ("info_csv_file", "Info CSV"),
            ("raw_data_csv_file", "Raw Data CSV"),
            ("medium_csv_file", "Medium CSV"),
            ("followup_zip_file", "Follow-up ZIP")
        ]

        for tag_key, display_name in file_tags:
            file_name_tags = entity_tag_list.get_tags_by_key(tag_key)
            if file_name_tags:
                file_info[display_name] = file_name_tags[0].tag_value

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
        Add selection scenarios to this analysis

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
        Get selection scenarios for this analysis

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
        Get visualization scenarios for this analysis

        :return: List of visualization scenarios
        """
        return self.get_scenarios_for_step('visualization')

    def has_selection_scenarios(self) -> bool:
        """
        Check if analysis has selection scenarios

        :return: True if selection scenarios exist
        """
        return 'selection' in self.scenarios and len(self.scenarios['selection']) > 0

    def has_visualization_scenarios(self) -> bool:
        """
        Check if analysis has visualization scenarios

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

        :return: Dictionary with analysis information
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
