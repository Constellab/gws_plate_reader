import os
import tempfile
from typing import List, Dict, Optional, Any, Union
import streamlit as st
from streamlit_slickgrid import slickgrid
from gws_plate_reader.fermentalg_dashboard._fermentalg_dashboard_core.fermentalg_state import FermentalgState
from gws_core.streamlit import StreamlitTranslateService
from gws_core import (
    ResourceModel, ResourceOrigin, Scenario, ScenarioSearchBuilder, ResourceSearchBuilder, ScenarioProxy,
    File, Tag, ScenarioStatus
)
from gws_core.tag.tag_entity_type import TagEntityType
from gws_core.tag.entity_tag_list import EntityTagList
from gws_core.tag.tag import TagOrigin


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


def get_microplate_emoji(is_microplate: bool) -> str:
    """Return appropriate emoji for microplate analysis"""
    return "🧪" if is_microplate else "🔬"


def create_fermentalg_recipe_table_data(scenarios: List[Scenario], fermentalg_state: FermentalgState,
                                        translate_service: StreamlitTranslateService) -> List[Dict]:
    """Create table data from Fermentalg recipe scenarios, grouped by recipe."""
    table_data = []

    # Group scenarios by recipe name
    recipes_dict = {}

    for scenario in scenarios:
        try:
            # Get tags for this scenario using find_by_entity to get existing tags
            entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)

            # Extract recipe name
            recipe_name = translate_service.translate('recipe_unnamed')
            recipe_name_tags = entity_tag_list.get_tags_by_key(fermentalg_state.TAG_FERMENTOR_RECIPE_NAME)
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
                    'pipeline_id': '',
                    'is_microplate': False,
                    'folder_name': translate_service.translate('summary_root_folder'),
                    'created_at': None,
                    'created_by': ''
                }

            # Check if this is a load scenario (data processing)
            fermentalg_tags = entity_tag_list.get_tags_by_key(fermentalg_state.TAG_FERMENTOR)
            is_load_scenario = any(tag.tag_value == fermentalg_state.TAG_DATA_PROCESSING for tag in fermentalg_tags)

            # Check if this is a selection scenario
            selection_tags = entity_tag_list.get_tags_by_key(fermentalg_state.TAG_FERMENTOR)
            is_selection_scenario = any(tag.tag_value == fermentalg_state.TAG_SELECTION_PROCESSING
                                        for tag in selection_tags)

            if is_load_scenario:
                recipes_dict[recipe_name]['load_scenario'] = scenario

                # Extract additional info from load scenario
                pipeline_id_tags = entity_tag_list.get_tags_by_key(
                    fermentalg_state.TAG_FERMENTOR_PIPELINE_ID)
                if pipeline_id_tags:
                    recipes_dict[recipe_name]['pipeline_id'] = pipeline_id_tags[0].tag_value[:8] + "..."

                # Extract microplate status
                microplate_tags = entity_tag_list.get_tags_by_key(fermentalg_state.TAG_MICROPLATE_ANALYSIS)
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
                "Type": f"{get_microplate_emoji(recipe_data['is_microplate'])} {translate_service.translate('type_microplate') if recipe_data['is_microplate'] else translate_service.translate('type_standard')}",
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


def create_fermentalg_slickgrid_columns(translate_service: StreamlitTranslateService) -> List[Dict]:
    """Create SlickGrid columns for Fermentalg recipe table with step columns."""
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


def render_fermentalg_recipe_table(scenarios: List[Scenario],
                                   fermentalg_state: FermentalgState) -> Union[Optional[str],
                                                                               List[Dict]]:
    """Render the Fermentalg recipe table using SlickGrid and return selected scenario ID."""

    translate_service = fermentalg_state.get_translate_service()

    if not scenarios:
        st.info(translate_service.translate('no_fermentalg_found'))
        return None

    # Create table data
    table_data = create_fermentalg_recipe_table_data(scenarios, fermentalg_state, translate_service)

    if not table_data:
        st.warning(translate_service.translate('cannot_load_recipe_data'))
        return None

    # Create columns
    columns = create_fermentalg_slickgrid_columns(translate_service)

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
    }

    # Render the grid with on_click for row selection
    grid_response = slickgrid(
        data=table_data,
        columns=columns,
        options=options,
        key="fermentalg_recipes_grid",
        on_click="rerun"
    )

    # Handle row selection like in ubiome
    if grid_response is not None:
        row_id, _ = grid_response  # _ is column, not needed for analysis selection
        # Return the selected scenario ID
        return row_id

    return None


def get_fermentalg_input_files_info(scenario_id: str, fermentalg_state: FermentalgState,
                                    translate_service: StreamlitTranslateService) -> Dict[str, str]:
    """Get information about input files for a Fermentalg analysis."""
    files_info = {
        "info_csv": translate_service.translate('file_not_found'),
        "raw_data_csv": translate_service.translate('file_not_found'),
        "medium_csv": translate_service.translate('file_not_found'),
        "follow_up_zip": translate_service.translate('file_not_found')
    }

    try:
        # Get pipeline ID from scenario tags
        scenario_tags = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario_id)
        pipeline_id_tags = scenario_tags.get_tags_by_key(fermentalg_state.TAG_FERMENTOR_PIPELINE_ID)

        if not pipeline_id_tags:
            return files_info

        pipeline_id = pipeline_id_tags[0].tag_value

        # Search for resources with this pipeline ID
        resource_search = ResourceSearchBuilder() \
            .add_tag_filter(Tag('fermentalg_fermentalg_pipeline_id', pipeline_id)) \
            .add_tag_filter(Tag('fermentor_fermentalg', 'input_file'))

        resources = resource_search.build_search().get_resource_models()

        # Extract file information
        for resource in resources:
            resource_tags = EntityTagList.find_by_entity(TagEntityType.RESOURCE, resource.id)
            file_type_tags = resource_tags.get_tags_by_key('file_type')

            if file_type_tags:
                file_type = file_type_tags[0].tag_value
                if file_type in files_info:
                    files_info[file_type] = resource.name

    except Exception as e:
        st.error(translate_service.translate('error_retrieving_input_files').format(error=str(e)))

    return files_info


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.1f} {size_names[i]}"


def get_analysis_summary(scenario: Scenario, fermentalg_state: FermentalgState,
                         translate_service: StreamlitTranslateService) -> Dict[str, str]:
    """Get a summary of the analysis including key information."""
    summary = {}

    try:
        # Get tags
        entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)

        # Recipe name
        recipe_name_tags = entity_tag_list.get_tags_by_key(fermentalg_state.TAG_FERMENTOR_RECIPE_NAME)
        if recipe_name_tags:
            summary[translate_service.translate('summary_recipe_name')] = recipe_name_tags[0].tag_value
        else:
            # Fallback to scenario title if no tag found
            summary[translate_service.translate('summary_recipe_name')] = scenario.title if scenario.title else translate_service.translate(
                'summary_scenario').format(id=scenario.id[:8])

        # Pipeline ID
        pipeline_id_tags = entity_tag_list.get_tags_by_key(fermentalg_state.TAG_FERMENTOR_PIPELINE_ID)
        summary[translate_service.translate(
            'summary_pipeline_id')] = pipeline_id_tags[0].tag_value if pipeline_id_tags else translate_service.translate('summary_not_available')

        # Microplate status
        microplate_tags = entity_tag_list.get_tags_by_key(fermentalg_state.TAG_MICROPLATE_ANALYSIS)
        is_microplate = microplate_tags[0].tag_value.lower() == "true" if microplate_tags else False
        summary[translate_service.translate(
            'summary_analysis_type')] = f"{get_microplate_emoji(is_microplate)} {translate_service.translate('type_microplate') if is_microplate else translate_service.translate('type_standard')}"

        # Status
        summary[translate_service.translate(
            'summary_status')] = f"{get_status_emoji(scenario.status)} {get_status_prettify(scenario.status, translate_service)}"

        # Dates
        summary[translate_service.translate('summary_created_at')] = scenario.created_at.strftime(
            "%d/%m/%Y à %H:%M") if scenario.created_at else translate_service.translate('summary_not_available')
        summary[translate_service.translate('summary_modified_at')] = scenario.last_modified_at.strftime(
            "%d/%m/%Y à %H:%M") if scenario.last_modified_at else translate_service.translate('summary_not_available')

        # Creator
        summary[translate_service.translate(
            'summary_created_by')] = scenario.created_by.full_name if scenario.created_by else translate_service.translate('summary_not_available')

        # Folder
        summary[translate_service.translate(
            'summary_folder')] = scenario.folder.name if scenario.folder else translate_service.translate('summary_root_folder')

    except Exception as e:
        st.error(translate_service.translate('error_creating_summary').format(error=str(e)))

    return summary


def save_uploaded_file(
        uploaded_file: Any, recipe_name: Optional[str] = None, pipeline_id: Optional[str] = None,
        file_type: Optional[str] = None) -> Optional[ResourceModel]:
    """Sauvegarde un fichier uploadé et retourne un ResourceModel sauvegardé avec tags"""
    if uploaded_file is not None:
        # Créer un fichier temporaire
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, uploaded_file.name)

        # Écrire le contenu du fichier uploadé
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # Créer un objet File GWS
        gws_file = File(temp_path)
        gws_file.name = uploaded_file.name

        # Créer un ResourceModel à partir du fichier et le sauvegarder
        resource_model = ResourceModel.from_resource(
            gws_file,
            origin=ResourceOrigin.UPLOADED
        )
        resource_model.save_full()

        # Ajouter les tags à la ressource
        if recipe_name or pipeline_id or file_type:
            user_origin = TagOrigin.current_user_origin()
            entity_tags = EntityTagList.find_by_entity(TagEntityType.RESOURCE, resource_model.id)
            entity_tags._default_origin = user_origin

            if recipe_name:
                recipe_name_parsed = Tag.parse_tag(recipe_name)
                entity_tags.add_tag(Tag('fermentor_recipe_name', recipe_name_parsed))

            if pipeline_id:
                pipeline_id_parsed = Tag.parse_tag(pipeline_id)
                entity_tags.add_tag(Tag('fermentor_fermentalg_pipeline_id', pipeline_id_parsed))
                entity_tags.add_tag(Tag('fermentor_fermentalg', 'input_file'))

            if file_type:
                file_type_parsed = Tag.parse_tag(file_type)
                entity_tags.add_tag(Tag('file_type', file_type_parsed))

        return resource_model

    return None


def setup_recipe_scenarios(recipe_name: str, fermentalg_state: FermentalgState,
                           translate_service: StreamlitTranslateService) -> bool:
    """
    Set up the scenarios for a given recipe by finding and storing the load and selection scenarios.

    Args:
        recipe_name: Name of the recipe to set up
        fermentalg_state: State object to store the scenarios

    Returns:
        bool: True if setup was successful, False otherwise
    """
    try:
        # Reset current recipe scenarios
        fermentalg_state.reset_recipe_scenarios()

        # 1. Find the load scenario for this recipe
        load_scenarios: List[Scenario] = ScenarioSearchBuilder() \
            .add_tag_filter(Tag(key=fermentalg_state.TAG_FERMENTOR, value=fermentalg_state.TAG_DATA_PROCESSING)) \
            .add_tag_filter(Tag(key=fermentalg_state.TAG_FERMENTOR_RECIPE_NAME, value=recipe_name)) \
            .add_is_archived_filter(False) \
            .search_all()

        if not load_scenarios:
            st.error(translate_service.translate('no_load_scenario_found').format(recipe_name=recipe_name))
            return False

        # Take the most recent load scenario and store it in state
        load_scenario = max(load_scenarios, key=lambda s: s.created_at or s.last_modified_at)
        fermentalg_state.set_load_scenario(load_scenario)

        # Get additional info from load scenario
        entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, load_scenario.id)

        # Get and store pipeline ID in state
        pipeline_id_tags = entity_tag_list.get_tags_by_key(fermentalg_state.TAG_FERMENTOR_PIPELINE_ID)
        if pipeline_id_tags:
            fermentalg_state.set_pipeline_id(pipeline_id_tags[0].tag_value)

        # Store recipe name in state
        fermentalg_state.set_recipe_name(recipe_name)

        # 2. Find all selection scenarios for this recipe
        selection_scenarios: List[Scenario] = ScenarioSearchBuilder() \
            .add_tag_filter(Tag(key=fermentalg_state.TAG_FERMENTOR, value=fermentalg_state.TAG_SELECTION_PROCESSING)) \
            .add_tag_filter(Tag(key=fermentalg_state.TAG_FERMENTOR_RECIPE_NAME, value=recipe_name)) \
            .add_is_archived_filter(False) \
            .search_all()

        # Sort selection scenarios by creation date (most recent first) and store in state
        selection_scenarios.sort(key=lambda s: s.created_at or s.last_modified_at, reverse=True)
        fermentalg_state.set_selection_scenarios(selection_scenarios)

        # 3. Find all quality check scenarios for this recipe
        quality_check_scenarios: List[Scenario] = ScenarioSearchBuilder() \
            .add_tag_filter(Tag(key=fermentalg_state.TAG_FERMENTOR, value=fermentalg_state.TAG_QUALITY_CHECK_PROCESSING)) \
            .add_tag_filter(Tag(key=fermentalg_state.TAG_FERMENTOR_RECIPE_NAME, value=recipe_name)) \
            .add_is_archived_filter(False) \
            .search_all()

        # Sort quality check scenarios by creation date (most recent first) and store in state
        quality_check_scenarios.sort(key=lambda s: s.created_at or s.last_modified_at, reverse=True)
        fermentalg_state.set_quality_check_scenarios(quality_check_scenarios)

        st.success(translate_service.translate('configuration_success').format(
            recipe_name=recipe_name,
            details=f"1 scénario de load, {len(selection_scenarios)} scénario(s) de sélection, "
                   f"{len(quality_check_scenarios)} scénario(s) de quality check"))

        return True

    except Exception as e:
        st.error(translate_service.translate('error_configuring_scenarios').format(error=str(e)))
        return False


def get_analysis_resource_set(fermentalg_state: FermentalgState) -> Optional[Any]:
    """
    Get the ResourceSet output from the load scenario of the current analysis.

    Args:
        fermentalg_state: State object with configured scenarios

    Returns:
        ResourceSet or None if not found
    """
    return fermentalg_state.get_load_scenario_output('resource_set')
