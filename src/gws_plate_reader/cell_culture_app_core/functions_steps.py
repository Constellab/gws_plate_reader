import os
import tempfile
from typing import Any, Dict, List, Optional, Union

import streamlit as st
from gws_core import (
    File,
    ResourceModel,
    ResourceOrigin,
    ResourceSearchBuilder,
    Scenario,
    ScenarioProxy,
    ScenarioSearchBuilder,
    ScenarioStatus,
    Tag,
)
from gws_core.streamlit import StreamlitTranslateService
from gws_core.tag.entity_tag_list import EntityTagList
from gws_core.tag.tag import TagOrigin
from gws_core.tag.tag_entity_type import TagEntityType
from streamlit_slickgrid import slickgrid

from gws_plate_reader.cell_culture_app_core.cell_culture_state import CellCultureState


def get_status_emoji(status: ScenarioStatus) -> str:
    """Return appropriate emoji for scenario status"""
    emoji_map = {
        ScenarioStatus.DRAFT: "📝",
        ScenarioStatus.IN_QUEUE: "⏳",
        ScenarioStatus.WAITING_FOR_CLI_PROCESS: "⏸️",
        ScenarioStatus.RUNNING: "🔄",
        ScenarioStatus.SUCCESS: "✅",
        ScenarioStatus.ERROR: "❌",
        ScenarioStatus.PARTIALLY_RUN: "✔️"
    }
    return emoji_map.get(status, "❓")


def get_status_prettify(status: ScenarioStatus, translate_service: StreamlitTranslateService) -> str:
    """Return a human-readable string for scenario status"""
    prettify_map = {
        ScenarioStatus.DRAFT: translate_service.translate('status_draft'),
        ScenarioStatus.IN_QUEUE: translate_service.translate('status_in_queue'),
        ScenarioStatus.WAITING_FOR_CLI_PROCESS: translate_service.translate('status_waiting'),
        ScenarioStatus.RUNNING: translate_service.translate('status_running'),
        ScenarioStatus.SUCCESS: translate_service.translate('status_success'),
        ScenarioStatus.ERROR: translate_service.translate('status_error'),
        ScenarioStatus.PARTIALLY_RUN: translate_service.translate('status_partially_run')
    }
    return prettify_map.get(status, translate_service.translate('status_unknown'))


def get_status_material_icon(status: ScenarioStatus) -> str:
    """Return Material icon for scenario status"""
    icon_map = {
        ScenarioStatus.DRAFT: "edit_note",
        ScenarioStatus.IN_QUEUE: "schedule",
        ScenarioStatus.WAITING_FOR_CLI_PROCESS: "pause_circle",
        ScenarioStatus.RUNNING: "sync",
        ScenarioStatus.SUCCESS: "check_circle",
        ScenarioStatus.ERROR: "error",
        ScenarioStatus.PARTIALLY_RUN: "check_circle_outline"
    }
    return icon_map.get(status, "help")


def get_biolector_emoji(is_biolector: bool) -> str:
    """Return appropriate emoji for biolector analysis"""
    return "🧫" if is_biolector else "🧪"


def create_recipe_table_data(scenarios: List[Scenario], cell_culture_state: CellCultureState,
                             translate_service: StreamlitTranslateService) -> List[Dict]:
    """Create table data from cell culture recipe scenarios, grouped by recipe."""
    table_data = []

    # Group scenarios by recipe name
    recipes_dict = {}

    for scenario in scenarios:
        try:
            # Get tags for this scenario using find_by_entity to get existing tags
            entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)

            # Extract recipe name
            recipe_name = translate_service.translate('recipe_unnamed')
            recipe_name_tags = entity_tag_list.get_tags_by_key(cell_culture_state.TAG_FERMENTOR_RECIPE_NAME)
            if recipe_name_tags:
                recipe_name = recipe_name_tags[0].tag_value
            else:
                # Fallback to scenario title if no tag found
                recipe_name = scenario.title if scenario.title else translate_service.translate(
                    'summary_scenario').format(id=scenario.id[:8])

            # Initialize recipe entry if not exists
            if recipe_name not in recipes_dict:
                recipes_dict[recipe_name] = {
                    'recipe_name': recipe_name,
                    'load_scenario': None,
                    'selection_scenarios': [],
                    'quality_check_scenarios': [],
                    'pipeline_id': '',
                    'is_microplate': False,
                    'folder_name': translate_service.translate('summary_root_folder'),
                    'created_at': None,
                    'created_by': ''
                }

            # Check if this is a load scenario (data processing)
            fermentor_tags = entity_tag_list.get_tags_by_key(cell_culture_state.TAG_FERMENTOR)
            is_load_scenario = any(tag.tag_value == cell_culture_state.TAG_DATA_PROCESSING for tag in fermentor_tags)

            # Check if this is a selection scenario
            selection_tags = entity_tag_list.get_tags_by_key(cell_culture_state.TAG_FERMENTOR)
            is_selection_scenario = any(tag.tag_value == cell_culture_state.TAG_SELECTION_PROCESSING
                                        for tag in selection_tags)

            # Check if this is a quality check scenario
            quality_check_tags = entity_tag_list.get_tags_by_key(cell_culture_state.TAG_FERMENTOR)
            is_quality_check_scenario = any(tag.tag_value == cell_culture_state.TAG_QUALITY_CHECK_PROCESSING
                                            for tag in quality_check_tags)

            if is_load_scenario:
                recipes_dict[recipe_name]['load_scenario'] = scenario

                # Extract additional info from load scenario
                pipeline_id_tags = entity_tag_list.get_tags_by_key(
                    cell_culture_state.TAG_FERMENTOR_PIPELINE_ID)
                if pipeline_id_tags:
                    recipes_dict[recipe_name]['pipeline_id'] = pipeline_id_tags[0].tag_value[:8] + "..."

                # Extract microplate status
                microplate_tags = entity_tag_list.get_tags_by_key(cell_culture_state.TAG_MICROPLATE_ANALYSIS)
                if microplate_tags:
                    recipes_dict[recipe_name]['is_microplate'] = microplate_tags[0].tag_value.lower() == "true"

                # Get folder name
                if scenario.folder:
                    recipes_dict[recipe_name]['folder_name'] = scenario.folder.name

                # Set creation info
                recipes_dict[recipe_name]['created_at'] = scenario.created_at
                recipes_dict[recipe_name]['created_by'] = scenario.created_by.full_name if scenario.created_by else ""

            elif is_selection_scenario:
                recipes_dict[recipe_name]['selection_scenarios'].append(scenario)

            elif is_quality_check_scenario:
                recipes_dict[recipe_name]['quality_check_scenarios'].append(scenario)

        except Exception as e:
            # Si erreur lors du traitement d'un scénario, on l'ignore et continue
            st.warning(translate_service.translate('error_processing_scenario').format(id=scenario.id, error=str(e)))
            continue

    # Create table rows from grouped recipes
    for recipe_name, recipe_data in recipes_dict.items():
        try:
            load_scenario = recipe_data['load_scenario']

            # Only create a table row if there is a load scenario
            # Selection scenarios alone should not create rows
            if not load_scenario:
                continue

            recipe_id = load_scenario.id

            row_data = {
                "id": recipe_id,  # Use load scenario ID
                "Recipe Name": recipe_data['recipe_name'],
                "Type": f"{get_biolector_emoji(recipe_data['is_microplate'])} {translate_service.translate('type_biolector') if recipe_data['is_microplate'] else translate_service.translate('type_fermentor')}",
                "Folder": recipe_data['folder_name'],
                "Created": recipe_data['created_at'].strftime("%d/%m/%Y %H:%M") if recipe_data['created_at'] else "",
                "Created By": recipe_data['created_by'],
            }

            table_data.append(row_data)

        except Exception as e:
            # Si erreur lors du traitement d'une recette, on l'ignore et continue
            st.warning(translate_service.translate('error_processing_recipe').format(
                recipe_name=recipe_name, error=str(e)))
            continue

    return table_data


def create_slickgrid_columns(translate_service: StreamlitTranslateService) -> List[Dict]:
    """Create SlickGrid columns for cell culture recipe table with step columns."""
    columns = [
        {
            "id": "Recipe Name",
            "name": translate_service.translate('column_recipe_name'),
            "field": "Recipe Name",
            "sortable": True,
            "type": "string",
            "filterable": True,
            "width": 250,
        },
        {
            "id": "Type",
            "name": translate_service.translate('column_type'),
            "field": "Type",
            "sortable": True,
            "type": "string",
            "filterable": True,
            "width": 150,
        },
        {
            "id": "Created",
            "name": translate_service.translate('column_created'),
            "field": "Created",
            "sortable": True,
            "type": "date",
            "filterable": True,
            "width": 130,
        },
        {
            "id": "Created By",
            "name": translate_service.translate('column_created_by'),
            "field": "Created By",
            "sortable": True,
            "type": "string",
            "filterable": True,
            "width": 120,
        },
    ]
    return columns


def render_recipe_table(scenarios: List[Scenario],
                        cell_culture_state: CellCultureState) -> Union[Optional[str], List[Dict]]:
    """Render the cell culture recipe table using SlickGrid and return selected scenario ID."""

    translate_service = cell_culture_state.get_translate_service()

    if not scenarios:
        st.info(translate_service.translate('no_recipe_found'))
        return None

    # Create table data
    table_data = create_recipe_table_data(scenarios, cell_culture_state, translate_service)

    if not table_data:
        st.warning(translate_service.translate('cannot_load_recipe_data'))
        return None

    # Create columns
    columns = create_slickgrid_columns(translate_service)

    # Configure SlickGrid options for row selection
    options = {
        "enableFiltering": True,
        "enableTextExport": True,
        "enableExcelExport": True,
        "enableColumnPicker": True,
        "autoResize": {
            "minHeight": 400,
        },
        "multiColumnSort": False,
        "rowHeight": 28,
    }

    # Render the grid with on_click for row selection
    grid_response = slickgrid(
        data=table_data,
        columns=columns,
        options=options,
        key="cell_culture_recipes_grid",
        on_click="rerun"
    )

    # Handle row selection like in ubiome
    if grid_response is not None:
        row_id, _ = grid_response  # _ is column, not needed for analysis selection
        # Return the selected scenario ID
        return row_id

    return None
