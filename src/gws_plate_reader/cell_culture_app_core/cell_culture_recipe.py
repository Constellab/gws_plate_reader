"""
Base Recipe class for Cell Culture Dashboards
Encapsulates recipe information and scenarios - Abstract base class
"""

from abc import ABC
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from gws_core import Scenario, User
from gws_core.tag.entity_tag_list import EntityTagList, TagEntityType

# Tag constants (matching CellCultureState)
_TAG_FERMENTOR_QUALITY_CHECK_PARENT_SELECTION = "fermentor_quality_check_parent_selection"
_TAG_FERMENTOR_ANALYSES_PARENT_SELECTION = "fermentor_analyses_parent_selection"
_TAG_FERMENTOR_ANALYSES_PARENT_QUALITY_CHECK = "fermentor_analyses_parent_quality_check"


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
    scenarios: dict[str, list[Scenario]]

    # Main scenario (data processing)
    main_scenario: Scenario | None = None

    # Additional metadata
    pipeline_id: str | None = None
    file_info: dict[str, str] | None = None  # Info about uploaded files
    has_data_raw: bool = True  # Whether this recipe has raw data (for feature extraction)
    has_medium_info: bool = (
        True  # Whether this recipe has medium info (for pca/umap and medium view step)
    )

    @classmethod
    def from_scenario(cls, scenario: Scenario) -> "CellCultureRecipe":
        """
        Create a Recipe object from a scenario (independent of state).
        This method must be implemented by subclasses to define specific tag extraction logic.

        :param scenario: The main scenario of the recipe
        :return: Recipe instance
        """
        # Get tags from scenario
        entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)

        # Extract recipe name using specific tag
        name = cls._extract_tag_value(entity_tag_list, "fermentor_recipe_name", scenario.title)

        # Extract pipeline ID using specific tag
        pipeline_id = cls._extract_tag_value(entity_tag_list, "fermentor_pipeline_id", scenario.id)

        # Extract analysis type (microplate or standard)
        microplate_value = cls._extract_tag_value(entity_tag_list, "microplate_analysis", "false")
        analysis_type = "microplate" if microplate_value == "true" else "standard"

        # Extract specific file information
        file_tags = [
            ("info_csv_file", "Info CSV"),
            ("raw_data_csv_file", "Raw Data CSV"),
            ("medium_csv_file", "Medium CSV"),
            ("followup_zip_file", "Follow-up ZIP"),
        ]
        file_info = cls._extract_file_info(entity_tag_list, file_tags)

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
        )

    @classmethod
    def _extract_tag_value(
        cls, entity_tag_list: EntityTagList, tag_key: str, default: str | None = None
    ) -> str | None:
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
    def _extract_file_info(
        cls, entity_tag_list: EntityTagList, file_tags: list[tuple]
    ) -> dict[str, str]:
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

    def add_selection_scenarios(self, selection_scenarios: list[Scenario]) -> None:
        """
        Add selection scenarios to this recipe

        :param selection_scenarios: List of selection scenarios to add
        """
        self.add_scenarios_by_step("selection", selection_scenarios)

    def add_scenarios_by_step(self, step: str, scenarios: list[Scenario]):
        """
        Add scenarios for a specific step

        :param step: Step name (e.g., 'selection', 'visualization')
        :param scenarios: List of scenarios for this step
        """
        self.scenarios[step] = scenarios

    def add_analyses_scenario(self, selection_id: str, analyses_scenario: Scenario) -> None:
        """
        Add an analyses scenario to this recipe

        :param selection_id: ID of the parent selection scenario (not used, for API compatibility)
        :param analyses_scenario: Analyses scenario to add
        """
        # Get existing analyses scenarios
        existing_analyses_scenarios = self.get_analyses_scenarios()

        # Add new scenario
        updated_analyses_scenarios = [analyses_scenario] + existing_analyses_scenarios

        # Sort by creation date (oldest first, most recent last)
        updated_analyses_scenarios.sort(
            key=lambda s: s.created_at or s.last_modified_at, reverse=False
        )

        # Update the scenarios dict
        self.add_scenarios_by_step("analyses", updated_analyses_scenarios)

    def get_analyses_scenarios(self) -> list[Scenario]:
        """
        Get all analyses scenarios for this recipe

        :return: List of analyses scenarios
        """
        return self.get_scenarios_for_step("analyses")

    def get_analyses_scenarios_for_selection(self, selection_id: str) -> list[Scenario]:
        """
        Get analyses scenarios linked to a specific selection scenario

        :param selection_id: ID of the parent selection scenario
        :return: List of analyses scenarios for this selection
        """
        all_analyses_scenarios = self.get_analyses_scenarios()

        # Filter by parent selection ID tag
        filtered_scenarios = []
        for scenario in all_analyses_scenarios:
            entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)
            parent_selection_tags = entity_tag_list.get_tags_by_key(
                _TAG_FERMENTOR_ANALYSES_PARENT_SELECTION
            )

            if parent_selection_tags and parent_selection_tags[0].tag_value == selection_id:
                filtered_scenarios.append(scenario)

        return filtered_scenarios

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

    def get_scenarios_for_step(self, step: str) -> list[Scenario]:
        """
        Get scenarios for a specific step

        :param step: Step name
        :return: List of scenarios for the step
        """
        return self.scenarios.get(step, [])

    def get_load_scenario(self) -> Scenario | None:
        """
        Get the main data processing scenario

        :return: Main scenario or None
        """
        return self.scenarios.get("data_processing", [None])[0]

    def get_selection_scenarios(self) -> list[Scenario]:
        """
        Get selection scenarios for this recipe

        :return: List of selection scenarios
        """
        return self.get_scenarios_for_step("selection")

    def get_quality_check_scenarios(self) -> list[Scenario]:
        """
        Get all quality check scenarios for this recipe

        :return: List of quality check scenarios
        """
        return self.get_scenarios_for_step("quality_check")

    def get_selection_scenarios_organized(self) -> dict[str, Scenario]:
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

    def get_visualization_scenarios(self) -> list[Scenario]:
        """
        Get visualization scenarios for this recipe

        :return: List of visualization scenarios
        """
        return self.get_scenarios_for_step("visualization")

    def has_selection_scenarios(self) -> bool:
        """
        Check if recipe has selection scenarios

        :return: True if selection scenarios exist
        """
        return "selection" in self.scenarios and len(self.scenarios["selection"]) > 0

    def has_quality_check_scenarios(self) -> bool:
        """
        Check if recipe has quality check scenarios

        :return: True if quality check scenarios exist
        """
        return "quality_check" in self.scenarios and len(self.scenarios["quality_check"]) > 0

    def has_visualization_scenarios(self) -> bool:
        """
        Check if recipe has visualization scenarios

        :return: True if visualization scenarios exist
        """
        return "visualization" in self.scenarios and len(self.scenarios["visualization"]) > 0

    def get_file_count(self) -> int:
        """
        Get number of uploaded files

        :return: Number of files
        """
        return len(self.file_info) if self.file_info else 0

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary representation

        :return: Dictionary with recipe information
        """
        return {
            "id": self.id,
            "name": self.name,
            "analysis_type": self.analysis_type,
            "created_by": self.created_by.to_dto().model_dump() if self.created_by else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "pipeline_id": self.pipeline_id,
            "file_info": self.file_info,
            "file_count": self.get_file_count(),
            "has_selection": self.has_selection_scenarios(),
            "has_visualization": self.has_visualization_scenarios(),
            "scenario_counts": {step: len(scenarios) for step, scenarios in self.scenarios.items()},
        }

    def get_quality_check_scenarios_for_selection(self, selection_id: str) -> list[Scenario]:
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
            parent_selection_tags = entity_tag_list.get_tags_by_key(
                _TAG_FERMENTOR_QUALITY_CHECK_PARENT_SELECTION
            )

            if parent_selection_tags and parent_selection_tags[0].tag_value == selection_id:
                filtered_scenarios.append(scenario)

        return filtered_scenarios

    def add_quality_check_scenario(
        self, selection_id: str, quality_check_scenario: Scenario
    ) -> None:
        """
        Add a quality check scenario to this recipe

        :param selection_id: ID of the parent selection scenario (not used, for API compatibility)
        :param quality_check_scenario: Quality check scenario to add
        """
        # Get existing quality check scenarios
        existing_qc_scenarios = self.get_quality_check_scenarios()

        # Add new scenario
        updated_qc_scenarios = [quality_check_scenario] + existing_qc_scenarios

        # Sort by creation date (oldest first, most recent last)
        updated_qc_scenarios.sort(key=lambda s: s.created_at or s.last_modified_at, reverse=False)

        # Update the scenarios dict
        self.add_scenarios_by_step("quality_check", updated_qc_scenarios)

    def get_medium_pca_scenarios_for_quality_check(self, qc_id: str) -> list[Scenario]:
        """
        Get Medium PCA scenarios for a specific quality check

        :param qc_id: Quality check scenario ID
        :return: List of Medium PCA scenarios for this quality check
        """
        # Get all analyses scenarios (medium_pca scenarios are stored in 'analyses' step)
        all_analyses_scenarios = self.get_scenarios_for_step("analyses")

        # Filter by parent quality check tag AND analysis type
        filtered = []
        for scenario in all_analyses_scenarios:
            entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)
            parent_qc_tags = entity_tag_list.get_tags_by_key(
                _TAG_FERMENTOR_ANALYSES_PARENT_QUALITY_CHECK
            )
            analysis_type_tags = entity_tag_list.get_tags_by_key("analysis_type")

            # Check if this is a medium_pca analysis for the specified quality check
            is_medium_pca = analysis_type_tags and analysis_type_tags[0].tag_value == "medium_pca"
            is_for_qc = parent_qc_tags and parent_qc_tags[0].tag_value == qc_id

            if is_medium_pca and is_for_qc:
                filtered.append(scenario)

        return filtered

    def add_medium_pca_scenario(self, qc_id: str, pca_scenario: Scenario) -> None:
        """
        Add a Medium PCA scenario to this recipe

        :param qc_id: ID of the parent quality check scenario (not used, for API compatibility)
        :param pca_scenario: Medium PCA scenario to add
        """
        # Get existing analyses scenarios (medium_pca scenarios are stored in 'analyses' step)
        existing_analyses_scenarios = self.get_scenarios_for_step("analyses")

        # Add new scenario at the beginning
        updated_analyses_scenarios = [pca_scenario] + existing_analyses_scenarios

        # Sort by creation date (oldest first, most recent last)
        updated_analyses_scenarios.sort(
            key=lambda s: s.created_at or s.last_modified_at, reverse=False
        )

        # Update the scenarios dict
        self.add_scenarios_by_step("analyses", updated_analyses_scenarios)

    def get_medium_umap_scenarios_for_quality_check(self, qc_id: str) -> list[Scenario]:
        """
        Get Medium UMAP scenarios for a specific quality check

        :param qc_id: Quality check scenario ID
        :return: List of Medium UMAP scenarios for this quality check
        """
        # Get all analyses scenarios (medium_umap scenarios are stored in 'analyses' step)
        all_analyses_scenarios = self.get_scenarios_for_step("analyses")

        # Filter by parent quality check tag AND analysis type
        filtered = []
        for scenario in all_analyses_scenarios:
            entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)
            parent_qc_tags = entity_tag_list.get_tags_by_key(
                _TAG_FERMENTOR_ANALYSES_PARENT_QUALITY_CHECK
            )
            analysis_type_tags = entity_tag_list.get_tags_by_key("analysis_type")

            # Check if this is a medium_umap analysis for the specified quality check
            is_medium_umap = analysis_type_tags and analysis_type_tags[0].tag_value == "medium_umap"
            is_for_qc = parent_qc_tags and parent_qc_tags[0].tag_value == qc_id

            if is_medium_umap and is_for_qc:
                filtered.append(scenario)

        return filtered

    def add_medium_umap_scenario(self, qc_id: str, umap_scenario: Scenario) -> None:
        """
        Add a Medium UMAP scenario to this recipe

        :param qc_id: ID of the parent quality check scenario (not used, for API compatibility)
        :param umap_scenario: Medium UMAP scenario to add
        """
        # Get existing analyses scenarios (medium_umap scenarios are stored in 'analyses' step)
        existing_analyses_scenarios = self.get_scenarios_for_step("analyses")

        # Add new scenario at the beginning
        updated_analyses_scenarios = [umap_scenario] + existing_analyses_scenarios

        # Sort by creation date (oldest first, most recent last)
        updated_analyses_scenarios.sort(
            key=lambda s: s.created_at or s.last_modified_at, reverse=False
        )

        # Update the scenarios dict
        self.add_scenarios_by_step("analyses", updated_analyses_scenarios)

    def get_feature_extraction_scenarios_for_quality_check(self, qc_id: str) -> list[Scenario]:
        """
        Get Feature Extraction scenarios for a specific quality check

        :param qc_id: Quality check scenario ID
        :return: List of Feature Extraction scenarios for this quality check
        """
        # Get all analyses scenarios (feature_extraction scenarios are stored in 'analyses' step)
        all_analyses_scenarios = self.get_scenarios_for_step("analyses")

        # Filter by parent quality check tag AND analysis type
        filtered = []
        for scenario in all_analyses_scenarios:
            entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)
            parent_qc_tags = entity_tag_list.get_tags_by_key(
                _TAG_FERMENTOR_ANALYSES_PARENT_QUALITY_CHECK
            )
            analysis_type_tags = entity_tag_list.get_tags_by_key("analysis_type")

            # Check if this is a feature_extraction analysis for the specified quality check
            is_feature_extraction = (
                analysis_type_tags and analysis_type_tags[0].tag_value == "feature_extraction"
            )
            is_for_qc = parent_qc_tags and parent_qc_tags[0].tag_value == qc_id

            if is_feature_extraction and is_for_qc:
                filtered.append(scenario)

        return filtered

    def add_feature_extraction_scenario(self, qc_id: str, fe_scenario: Scenario) -> None:
        """
        Add a Feature Extraction scenario to this recipe

        :param qc_id: ID of the parent quality check scenario (not used, for API compatibility)
        :param fe_scenario: Feature Extraction scenario to add
        """
        # Get existing analyses scenarios (feature_extraction scenarios are stored in 'analyses' step)
        existing_analyses_scenarios = self.get_scenarios_for_step("analyses")

        # Add new scenario at the beginning
        updated_analyses_scenarios = [fe_scenario] + existing_analyses_scenarios

        # Sort by creation date (oldest first, most recent last)
        updated_analyses_scenarios.sort(
            key=lambda s: s.created_at or s.last_modified_at, reverse=False
        )

        # Update the scenarios dict
        self.add_scenarios_by_step("analyses", updated_analyses_scenarios)

    def get_metadata_feature_umap_scenarios_for_feature_extraction(
        self, fe_id: str
    ) -> list[Scenario]:
        """
        Get Metadata Feature UMAP scenarios for a specific feature extraction scenario

        :param fe_id: Feature extraction scenario ID
        :return: List of Metadata Feature UMAP scenarios for this feature extraction
        """
        # Get all analyses scenarios (metadata_feature_umap scenarios are stored in 'analyses' step)
        all_analyses_scenarios = self.get_scenarios_for_step("analyses")

        # Filter by parent feature extraction tag AND analysis type
        filtered = []
        for scenario in all_analyses_scenarios:
            entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)
            parent_fe_tags = entity_tag_list.get_tags_by_key("parent_feature_extraction_scenario")
            analysis_type_tags = entity_tag_list.get_tags_by_key("analysis_type")

            # Check if this is a metadata_feature_umap analysis for the specified feature extraction
            is_metadata_feature_umap = (
                analysis_type_tags and analysis_type_tags[0].tag_value == "metadata_feature_umap"
            )
            is_for_fe = parent_fe_tags and parent_fe_tags[0].tag_value == fe_id

            if is_metadata_feature_umap and is_for_fe:
                filtered.append(scenario)

        return filtered

    def add_metadata_feature_umap_scenario(self, fe_id: str, umap_scenario: Scenario) -> None:
        """
        Add a Metadata Feature UMAP scenario to this recipe

        :param fe_id: ID of the parent feature extraction scenario (not used, for API compatibility)
        :param umap_scenario: Metadata Feature UMAP scenario to add
        """
        # Get existing analyses scenarios (metadata_feature_umap scenarios are stored in 'analyses' step)
        existing_analyses_scenarios = self.get_scenarios_for_step("analyses")

        # Add new scenario at the beginning
        updated_analyses_scenarios = [umap_scenario] + existing_analyses_scenarios

        # Sort by creation date (oldest first, most recent last)
        updated_analyses_scenarios.sort(
            key=lambda s: s.created_at or s.last_modified_at, reverse=False
        )

        # Update the scenarios dict
        self.add_scenarios_by_step("analyses", updated_analyses_scenarios)

    def get_pls_regression_scenarios_for_feature_extraction(self, fe_id: str) -> list[Scenario]:
        """
        Get PLS Regression scenarios for a specific feature extraction scenario

        :param fe_id: Feature extraction scenario ID
        :return: List of PLS Regression scenarios for this feature extraction
        """
        # Get all analyses scenarios (pls_regression scenarios are stored in 'analyses' step)
        all_analyses_scenarios = self.get_scenarios_for_step("analyses")

        # Filter by parent feature extraction tag AND analysis type
        filtered = []
        for scenario in all_analyses_scenarios:
            entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)
            parent_fe_tags = entity_tag_list.get_tags_by_key("parent_feature_extraction_scenario")
            analysis_type_tags = entity_tag_list.get_tags_by_key("analysis_type")

            # Check if this is a pls_regression analysis for the specified feature extraction
            is_pls_regression = (
                analysis_type_tags and analysis_type_tags[0].tag_value == "pls_regression"
            )
            is_for_fe = parent_fe_tags and parent_fe_tags[0].tag_value == fe_id

            if is_pls_regression and is_for_fe:
                filtered.append(scenario)

        return filtered

    def add_pls_regression_scenario(self, fe_id: str, pls_scenario: Scenario) -> None:
        """
        Add a PLS Regression scenario to this recipe

        :param fe_id: ID of the parent feature extraction scenario (not used, for API compatibility)
        :param pls_scenario: PLS Regression scenario to add
        """
        # Get existing analyses scenarios (pls_regression scenarios are stored in 'analyses' step)
        existing_analyses_scenarios = self.get_scenarios_for_step("analyses")

        # Add new scenario at the beginning
        updated_analyses_scenarios = [pls_scenario] + existing_analyses_scenarios

        # Sort by creation date (oldest first, most recent last)
        updated_analyses_scenarios.sort(
            key=lambda s: s.created_at or s.last_modified_at, reverse=False
        )

        # Update the scenarios dict
        self.add_scenarios_by_step("analyses", updated_analyses_scenarios)

    def get_random_forest_scenarios_for_feature_extraction(self, fe_id: str) -> list[Scenario]:
        """
        Get Random Forest Regression scenarios for a specific feature extraction scenario

        :param fe_id: Feature extraction scenario ID
        :return: List of Random Forest Regression scenarios for this feature extraction
        """
        # Get all analyses scenarios (random_forest scenarios are stored in 'analyses' step)
        all_analyses_scenarios = self.get_scenarios_for_step("analyses")

        # Filter by parent feature extraction tag AND analysis type
        filtered = []
        for scenario in all_analyses_scenarios:
            entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)
            parent_fe_tags = entity_tag_list.get_tags_by_key("parent_feature_extraction_scenario")
            analysis_type_tags = entity_tag_list.get_tags_by_key("analysis_type")

            # Check if this is a random_forest_regression analysis for the specified feature extraction
            is_random_forest = (
                analysis_type_tags and analysis_type_tags[0].tag_value == "random_forest_regression"
            )
            is_for_fe = parent_fe_tags and parent_fe_tags[0].tag_value == fe_id

            if is_random_forest and is_for_fe:
                filtered.append(scenario)

        return filtered

    def add_random_forest_scenario(self, fe_id: str, rf_scenario: Scenario) -> None:
        """
        Add a Random Forest Regression scenario to this recipe

        :param fe_id: ID of the parent feature extraction scenario (not used, for API compatibility)
        :param rf_scenario: Random Forest Regression scenario to add
        """
        # Get existing analyses scenarios (random_forest scenarios are stored in 'analyses' step)
        existing_analyses_scenarios = self.get_scenarios_for_step("analyses")

        # Add new scenario at the beginning
        updated_analyses_scenarios = [rf_scenario] + existing_analyses_scenarios

        # Sort by creation date (oldest first, most recent last)
        updated_analyses_scenarios.sort(
            key=lambda s: s.created_at or s.last_modified_at, reverse=False
        )

        # Update the scenarios dict
        self.add_scenarios_by_step("analyses", updated_analyses_scenarios)

    def get_causal_effect_scenarios_for_feature_extraction(self, fe_id: str) -> list[Scenario]:
        """
        Get Causal Effect scenarios for a specific feature extraction scenario

        :param fe_id: Feature extraction scenario ID
        :return: List of Causal Effect scenarios for this feature extraction
        """
        # Get all analyses scenarios (causal effect scenarios are stored in 'analyses' step)
        all_analyses_scenarios = self.get_scenarios_for_step("analyses")

        # Filter by parent feature extraction tag AND analysis type
        filtered = []
        for scenario in all_analyses_scenarios:
            entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)
            parent_fe_tags = entity_tag_list.get_tags_by_key("parent_feature_extraction_scenario")
            analysis_type_tags = entity_tag_list.get_tags_by_key("analysis_type")

            # Check if this is a causal_effect analysis for the specified feature extraction
            is_causal_effect = (
                analysis_type_tags and analysis_type_tags[0].tag_value == "causal_effect"
            )
            is_for_fe = parent_fe_tags and parent_fe_tags[0].tag_value == fe_id

            if is_causal_effect and is_for_fe:
                filtered.append(scenario)

        return filtered

    def add_causal_effect_scenario(self, fe_id: str, causal_scenario: Scenario) -> None:
        """
        Add a Causal Effect scenario to this recipe

        :param fe_id: ID of the parent feature extraction scenario (not used, for API compatibility)
        :param causal_scenario: Causal Effect scenario to add
        """
        # Get existing analyses scenarios (causal effect scenarios are stored in 'analyses' step)
        existing_analyses_scenarios = self.get_scenarios_for_step("analyses")

        # Add new scenario at the beginning
        updated_analyses_scenarios = [causal_scenario] + existing_analyses_scenarios

        # Sort by creation date (oldest first, most recent last)
        updated_analyses_scenarios.sort(
            key=lambda s: s.created_at or s.last_modified_at, reverse=False
        )

        # Update the scenarios dict
        self.add_scenarios_by_step("analyses", updated_analyses_scenarios)

    def get_optimization_scenarios_for_feature_extraction(self, fe_id: str) -> list[Scenario]:
        """
        Get Optimization scenarios for a specific feature extraction scenario

        :param fe_id: Feature extraction scenario ID
        :return: List of Optimization scenarios for this feature extraction
        """
        # Get all analyses scenarios (optimization scenarios are stored in 'analyses' step)
        all_analyses_scenarios = self.get_scenarios_for_step("analyses")

        # Filter by parent feature extraction tag AND analysis type
        filtered = []
        for scenario in all_analyses_scenarios:
            entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)
            parent_fe_tags = entity_tag_list.get_tags_by_key("parent_feature_extraction_scenario")
            analysis_type_tags = entity_tag_list.get_tags_by_key("analysis_type")

            # Check if this is an optimization analysis for the specified feature extraction
            is_optimization = (
                analysis_type_tags and analysis_type_tags[0].tag_value == "optimization"
            )
            is_for_fe = parent_fe_tags and parent_fe_tags[0].tag_value == fe_id

            if is_optimization and is_for_fe:
                filtered.append(scenario)

        return filtered

    def add_optimization_scenario(self, fe_id: str, opt_scenario: Scenario) -> None:
        """
        Add an Optimization scenario to this recipe

        :param fe_id: ID of the parent feature extraction scenario (not used, for API compatibility)
        :param opt_scenario: Optimization scenario to add
        """
        # Get existing analyses scenarios (optimization scenarios are stored in 'analyses' step)
        existing_analyses_scenarios = self.get_scenarios_for_step("analyses")

        # Add new scenario at the beginning
        updated_analyses_scenarios = [opt_scenario] + existing_analyses_scenarios

        # Sort by creation date (oldest first, most recent last)
        updated_analyses_scenarios.sort(
            key=lambda s: s.created_at or s.last_modified_at, reverse=False
        )

        # Update the scenarios dict
        self.add_scenarios_by_step("analyses", updated_analyses_scenarios)

    def get_logistic_growth_scenarios_for_quality_check(self, qc_id: str) -> list[Scenario]:
        """
        Get Logistic Growth scenarios for a specific quality check

        :param qc_id: Quality check scenario ID
        :return: List of Logistic Growth scenarios for this quality check
        """
        # Get all analyses scenarios (logistic_growth scenarios are stored in 'analyses' step)
        all_analyses_scenarios = self.get_scenarios_for_step("analyses")

        # Filter by parent quality check tag AND analysis type
        filtered = []
        for scenario in all_analyses_scenarios:
            entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)
            parent_qc_tags = entity_tag_list.get_tags_by_key(
                _TAG_FERMENTOR_ANALYSES_PARENT_QUALITY_CHECK
            )
            analysis_type_tags = entity_tag_list.get_tags_by_key("analysis_type")

            # Check if this is a logistic_growth analysis for the specified quality check
            is_logistic_growth = (
                analysis_type_tags and analysis_type_tags[0].tag_value == "logistic_growth"
            )
            is_for_qc = parent_qc_tags and parent_qc_tags[0].tag_value == qc_id

            if is_logistic_growth and is_for_qc:
                filtered.append(scenario)

        return filtered

    def add_logistic_growth_scenario(self, qc_id: str, lg_scenario: Scenario) -> None:
        """
        Add a Logistic Growth scenario to this recipe

        :param qc_id: ID of the parent quality check scenario (not used, for API compatibility)
        :param lg_scenario: Logistic Growth scenario to add
        """
        # Get existing analyses scenarios (logistic_growth scenarios are stored in 'analyses' step)
        existing_analyses_scenarios = self.get_scenarios_for_step("analyses")

        # Add new scenario at the beginning
        updated_analyses_scenarios = [lg_scenario] + existing_analyses_scenarios

        # Sort by creation date (oldest first, most recent last)
        updated_analyses_scenarios.sort(
            key=lambda s: s.created_at or s.last_modified_at, reverse=False
        )

        # Update the scenarios dict
        self.add_scenarios_by_step("analyses", updated_analyses_scenarios)
