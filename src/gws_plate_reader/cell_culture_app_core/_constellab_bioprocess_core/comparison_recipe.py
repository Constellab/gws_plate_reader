"""
Comparison Recipe class represents a saved Biolector / Fermentor comparison.
It is stored as a DRAFT Scenario with no protocol tasks; the two QC scenario IDs
are kept as tags and loaded here for visualisation.
"""

from dataclasses import dataclass

from gws_core import Scenario
from gws_core.tag.entity_tag_list import EntityTagList
from gws_core.tag.tag_entity_type import TagEntityType
from gws_plate_reader.cell_culture_app_core._constellab_bioprocess_core.cell_culture_recipe import (
    CellCultureRecipe,
)

_TAG_BIOPROCESS_RECIPE_NAME = "bioprocess_recipe_name"
_TAG_BIOPROCESS_PIPELINE_ID = "bioprocess_pipeline_id"
_TAG_COMPARISON_BIO_QC_ID = "comparison_bio_qc_id"
_TAG_COMPARISON_FERM_QC_ID = "comparison_ferm_qc_id"

# Protocol output names – the two ResourceSets stored inside the comparison scenario
COMPARISON_BIO_OUTPUT = "bio_resource_set"
COMPARISON_FERM_OUTPUT = "ferm_resource_set"


@dataclass
class ComparisonRecipe(CellCultureRecipe):
    """
    Represents a saved Biolector / Fermentor comparison recipe.
    Stores the IDs of the two QC scenarios used in the comparison.
    """

    bio_qc_id: str | None = None
    ferm_qc_id: str | None = None

    @classmethod
    def from_scenario(cls, scenario: Scenario) -> "ComparisonRecipe":
        """
        Create a ComparisonRecipe from a comparison scenario.

        :param scenario: The comparison scenario (DRAFT, no protocol)
        :return: ComparisonRecipe instance
        """
        entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)

        name = cls._extract_tag_value(entity_tag_list, _TAG_BIOPROCESS_RECIPE_NAME, scenario.title)
        pipeline_id = cls._extract_tag_value(
            entity_tag_list, _TAG_BIOPROCESS_PIPELINE_ID, scenario.id
        )
        bio_qc_id = cls._extract_tag_value(entity_tag_list, _TAG_COMPARISON_BIO_QC_ID)
        ferm_qc_id = cls._extract_tag_value(entity_tag_list, _TAG_COMPARISON_FERM_QC_ID)

        return cls(
            id=scenario.id,
            name=name,
            analysis_type="comparison",
            created_by=scenario.created_by,
            created_at=scenario.created_at,
            scenarios={"comparison": [scenario]},
            main_scenario=scenario,
            pipeline_id=pipeline_id,
            file_info={},
            has_data_raw=False,
            has_medium_info=False,
            bio_qc_id=bio_qc_id,
            ferm_qc_id=ferm_qc_id,
        )
