"""
Greencell Fermentor Recipe class - extends CellCultureRecipe with Greencell Fermentor-specific logic
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from gws_core import Scenario
from gws_core.tag.entity_tag_list import EntityTagList
from gws_core.tag.tag_entity_type import TagEntityType
from gws_plate_reader.cell_culture_app_core.cell_culture_recipe import CellCultureRecipe


@dataclass
class GreencellFermentorRecipe(CellCultureRecipe):
    """
    Represents a Greencell Fermentor recipe with its metadata and scenarios.
    Extends CellCultureRecipe with Greencell Fermentor-specific tag extraction.
    """

    @classmethod
    def from_scenario(cls, scenario: Scenario) -> 'GreencellFermentorRecipe':
        """
        Create a Greencell Fermentor Recipe object from a scenario with Greencell Fermentor-specific tags.

        :param scenario: The main scenario of the recipe
        :return: GreencellFermentorRecipe instance
        """
        # Get tags from scenario
        entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)

        # Extract recipe name using Greencell Fermentor-specific tag
        name = cls._extract_tag_value(entity_tag_list, "greencell_fermentor_recipe_name", scenario.title)

        # Extract pipeline ID using Greencell Fermentor-specific tag
        pipeline_id = cls._extract_tag_value(entity_tag_list, "greencell_fermentor_pipeline_id", scenario.id)
        # For Greencell Fermentor, we don't have the microplate distinction
        analysis_type = "standard"

        # Extract Greencell Fermentor-specific file information
        file_tags = [
            ("info_csv_file", "Info CSV"),
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
        """Add selection scenarios to this recipe"""
        self.add_scenarios_by_step('selection', selection_scenarios)

    def add_scenarios_by_step(self, step: str, scenarios: List[Scenario]):
        """Add scenarios for a specific step"""
        self.scenarios[step] = scenarios

    def get_scenarios_for_step(self, step: str) -> List[Scenario]:
        """Get scenarios for a specific step"""
        return self.scenarios.get(step, [])

    def get_load_scenario(self) -> Optional[Scenario]:
        """Get the main data processing scenario"""
        return self.scenarios.get('data_processing', [None])[0]

    def get_selection_scenarios(self) -> List[Scenario]:
        """Get selection scenarios for this recipe"""
        return self.get_scenarios_for_step('selection')

    def get_quality_check_scenarios(self) -> List[Scenario]:
        """Get all quality check scenarios for this recipe"""
        return self.get_scenarios_for_step('quality_check')

    def get_quality_check_scenarios_for_selection(self, selection_id: str) -> List[Scenario]:
        """Get quality check scenarios linked to a specific selection scenario"""
        all_qc_scenarios = self.get_quality_check_scenarios()
        filtered_scenarios = []
        for scenario in all_qc_scenarios:
            entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)
            parent_selection_tags = entity_tag_list.get_tags_by_key(
                "greencell_fermentor_quality_check_parent_selection")
            if parent_selection_tags and parent_selection_tags[0].tag_value == selection_id:
                filtered_scenarios.append(scenario)
        return filtered_scenarios

    def add_quality_check_scenario(self, selection_id: str, quality_check_scenario: Scenario) -> None:
        """Add a quality check scenario to this recipe"""
        existing_qc_scenarios = self.get_quality_check_scenarios()
        updated_qc_scenarios = [quality_check_scenario] + existing_qc_scenarios
        self.add_scenarios_by_step('quality_check', updated_qc_scenarios)

    def add_analyses_scenario(self, selection_id: str, analyses_scenario: Scenario) -> None:
        """Add an analyses scenario to this recipe"""
        existing_analyses_scenarios = self.get_analyses_scenarios()
        updated_analyses_scenarios = [analyses_scenario] + existing_analyses_scenarios
        self.add_scenarios_by_step('analyses', updated_analyses_scenarios)

    def get_analyses_scenarios(self) -> List[Scenario]:
        """Get all analyses scenarios for this recipe"""
        return self.get_scenarios_for_step('analyses')

    def get_analyses_scenarios_for_selection(self, selection_id: str) -> List[Scenario]:
        """Get analyses scenarios linked to a specific selection scenario"""
        all_analyses_scenarios = self.get_analyses_scenarios()
        filtered_scenarios = []
        for scenario in all_analyses_scenarios:
            entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)
            parent_selection_tags = entity_tag_list.get_tags_by_key("greencell_fermentor_analyses_parent_selection")
            if parent_selection_tags and parent_selection_tags[0].tag_value == selection_id:
                filtered_scenarios.append(scenario)
        return filtered_scenarios

    def get_medium_pca_scenarios_for_quality_check(self, qc_id: str) -> List[Scenario]:
        """Get Medium PCA scenarios for a specific quality check"""
        all_analyses_scenarios = self.get_scenarios_for_step('analyses')
        filtered = []
        for scenario in all_analyses_scenarios:
            entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)
            parent_qc_tags = entity_tag_list.get_tags_by_key("greencell_fermentor_analyses_parent_quality_check")
            analysis_type_tags = entity_tag_list.get_tags_by_key("analysis_type")
            is_medium_pca = analysis_type_tags and analysis_type_tags[0].tag_value == "medium_pca"
            is_for_qc = parent_qc_tags and parent_qc_tags[0].tag_value == qc_id
            if is_medium_pca and is_for_qc:
                filtered.append(scenario)
        return filtered

    def add_medium_pca_scenario(self, qc_id: str, pca_scenario: Scenario) -> None:
        """Add a Medium PCA scenario to this recipe"""
        existing_analyses_scenarios = self.get_scenarios_for_step('analyses')
        updated_analyses_scenarios = [pca_scenario] + existing_analyses_scenarios
        self.add_scenarios_by_step('analyses', updated_analyses_scenarios)

    def get_medium_umap_scenarios_for_quality_check(self, qc_id: str) -> List[Scenario]:
        """Get Medium UMAP scenarios for a specific quality check"""
        all_analyses_scenarios = self.get_scenarios_for_step('analyses')
        filtered = []
        for scenario in all_analyses_scenarios:
            entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)
            parent_qc_tags = entity_tag_list.get_tags_by_key("greencell_fermentor_analyses_parent_quality_check")
            analysis_type_tags = entity_tag_list.get_tags_by_key("analysis_type")
            is_medium_umap = analysis_type_tags and analysis_type_tags[0].tag_value == "medium_umap"
            is_for_qc = parent_qc_tags and parent_qc_tags[0].tag_value == qc_id
            if is_medium_umap and is_for_qc:
                filtered.append(scenario)
        return filtered

    def add_medium_umap_scenario(self, qc_id: str, umap_scenario: Scenario) -> None:
        """Add a Medium UMAP scenario to this recipe"""
        existing_analyses_scenarios = self.get_scenarios_for_step('analyses')
        updated_analyses_scenarios = [umap_scenario] + existing_analyses_scenarios
        self.add_scenarios_by_step('analyses', updated_analyses_scenarios)

    def get_feature_extraction_scenarios_for_quality_check(self, qc_id: str) -> List[Scenario]:
        """Get Feature Extraction scenarios for a specific quality check"""
        all_analyses_scenarios = self.get_scenarios_for_step('analyses')
        filtered = []
        for scenario in all_analyses_scenarios:
            entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)
            parent_qc_tags = entity_tag_list.get_tags_by_key("greencell_fermentor_analyses_parent_quality_check")
            analysis_type_tags = entity_tag_list.get_tags_by_key("analysis_type")
            is_feature_extraction = analysis_type_tags and analysis_type_tags[0].tag_value == "feature_extraction"
            is_for_qc = parent_qc_tags and parent_qc_tags[0].tag_value == qc_id
            if is_feature_extraction and is_for_qc:
                filtered.append(scenario)
        return filtered

    def add_feature_extraction_scenario(self, qc_id: str, fe_scenario: Scenario) -> None:
        """Add a Feature Extraction scenario to this recipe"""
        existing_analyses_scenarios = self.get_scenarios_for_step('analyses')
        updated_analyses_scenarios = [fe_scenario] + existing_analyses_scenarios
        self.add_scenarios_by_step('analyses', updated_analyses_scenarios)

    def get_metadata_feature_umap_scenarios_for_feature_extraction(self, fe_id: str) -> List[Scenario]:
        """Get Metadata Feature UMAP scenarios for a specific feature extraction scenario"""
        all_analyses_scenarios = self.get_scenarios_for_step('analyses')
        filtered = []
        for scenario in all_analyses_scenarios:
            entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)
            parent_fe_tags = entity_tag_list.get_tags_by_key("parent_feature_extraction_scenario")
            analysis_type_tags = entity_tag_list.get_tags_by_key("analysis_type")
            is_metadata_feature_umap = analysis_type_tags and analysis_type_tags[0].tag_value == "metadata_feature_umap"
            is_for_fe = parent_fe_tags and parent_fe_tags[0].tag_value == fe_id
            if is_metadata_feature_umap and is_for_fe:
                filtered.append(scenario)
        return filtered

    def add_metadata_feature_umap_scenario(self, fe_id: str, umap_scenario: Scenario) -> None:
        """Add a Metadata Feature UMAP scenario to this recipe"""
        existing_analyses_scenarios = self.get_scenarios_for_step('analyses')
        updated_analyses_scenarios = [umap_scenario] + existing_analyses_scenarios
        self.add_scenarios_by_step('analyses', updated_analyses_scenarios)

    def get_pls_regression_scenarios_for_feature_extraction(self, fe_id: str) -> List[Scenario]:
        """Get PLS Regression scenarios for a specific feature extraction scenario"""
        all_analyses_scenarios = self.get_scenarios_for_step('analyses')
        filtered = []
        for scenario in all_analyses_scenarios:
            entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)
            parent_fe_tags = entity_tag_list.get_tags_by_key("parent_feature_extraction_scenario")
            analysis_type_tags = entity_tag_list.get_tags_by_key("analysis_type")
            is_pls_regression = analysis_type_tags and analysis_type_tags[0].tag_value == "pls_regression"
            is_for_fe = parent_fe_tags and parent_fe_tags[0].tag_value == fe_id
            if is_pls_regression and is_for_fe:
                filtered.append(scenario)
        return filtered

    def add_pls_regression_scenario(self, fe_id: str, pls_scenario: Scenario) -> None:
        """Add a PLS Regression scenario to this recipe"""
        existing_analyses_scenarios = self.get_scenarios_for_step('analyses')
        updated_analyses_scenarios = [pls_scenario] + existing_analyses_scenarios
        self.add_scenarios_by_step('analyses', updated_analyses_scenarios)

    def get_random_forest_scenarios_for_feature_extraction(self, fe_id: str) -> List[Scenario]:
        """Get Random Forest Regression scenarios for a specific feature extraction scenario"""
        all_analyses_scenarios = self.get_scenarios_for_step('analyses')
        filtered = []
        for scenario in all_analyses_scenarios:
            entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)
            parent_fe_tags = entity_tag_list.get_tags_by_key("parent_feature_extraction_scenario")
            analysis_type_tags = entity_tag_list.get_tags_by_key("analysis_type")
            is_random_forest = analysis_type_tags and analysis_type_tags[0].tag_value == "random_forest_regression"
            is_for_fe = parent_fe_tags and parent_fe_tags[0].tag_value == fe_id
            if is_random_forest and is_for_fe:
                filtered.append(scenario)
        return filtered

    def add_random_forest_scenario(self, fe_id: str, rf_scenario: Scenario) -> None:
        """Add a Random Forest Regression scenario to this recipe"""
        existing_analyses_scenarios = self.get_scenarios_for_step('analyses')
        updated_analyses_scenarios = [rf_scenario] + existing_analyses_scenarios
        self.add_scenarios_by_step('analyses', updated_analyses_scenarios)

    def get_causal_effect_scenarios_for_feature_extraction(self, fe_id: str) -> List[Scenario]:
        """Get Causal Effect scenarios for a specific feature extraction scenario"""
        all_analyses_scenarios = self.get_scenarios_for_step('analyses')
        filtered = []
        for scenario in all_analyses_scenarios:
            entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)
            parent_fe_tags = entity_tag_list.get_tags_by_key("parent_feature_extraction_scenario")
            analysis_type_tags = entity_tag_list.get_tags_by_key("analysis_type")
            is_causal_effect = analysis_type_tags and analysis_type_tags[0].tag_value == "causal_effect"
            is_for_fe = parent_fe_tags and parent_fe_tags[0].tag_value == fe_id
            if is_causal_effect and is_for_fe:
                filtered.append(scenario)
        return filtered

    def add_causal_effect_scenario(self, fe_id: str, causal_scenario: Scenario) -> None:
        """Add a Causal Effect scenario to this recipe"""
        existing_analyses_scenarios = self.get_scenarios_for_step('analyses')
        updated_analyses_scenarios = [causal_scenario] + existing_analyses_scenarios
        self.add_scenarios_by_step('analyses', updated_analyses_scenarios)

    def get_optimization_scenarios_for_feature_extraction(self, fe_id: str) -> List[Scenario]:
        """Get Optimization scenarios for a specific feature extraction scenario"""
        all_analyses_scenarios = self.get_scenarios_for_step('analyses')
        filtered = []
        for scenario in all_analyses_scenarios:
            entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)
            parent_fe_tags = entity_tag_list.get_tags_by_key("parent_feature_extraction_scenario")
            analysis_type_tags = entity_tag_list.get_tags_by_key("analysis_type")
            is_optimization = analysis_type_tags and analysis_type_tags[0].tag_value == "optimization"
            is_for_fe = parent_fe_tags and parent_fe_tags[0].tag_value == fe_id
            if is_optimization and is_for_fe:
                filtered.append(scenario)
        return filtered

    def add_optimization_scenario(self, fe_id: str, opt_scenario: Scenario) -> None:
        """Add an Optimization scenario to this recipe"""
        existing_analyses_scenarios = self.get_scenarios_for_step('analyses')
        updated_analyses_scenarios = [opt_scenario] + existing_analyses_scenarios
        self.add_scenarios_by_step('analyses', updated_analyses_scenarios)
