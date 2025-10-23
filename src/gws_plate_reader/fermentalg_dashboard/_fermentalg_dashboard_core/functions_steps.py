import os
import tempfile
from typing import List, Dict, Optional, Any, Union
import streamlit as st
from streamlit_slickgrid import slickgrid
from gws_plate_reader.fermentalg_dashboard._fermentalg_dashboard_core.state import State
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


def get_status_prettify(status: ScenarioStatus) -> str:
    """Return a human-readable string for scenario status"""
    prettify_map = {
        ScenarioStatus.DRAFT: "Brouillon",
        ScenarioStatus.IN_QUEUE: "En attente",
        ScenarioStatus.WAITING_FOR_CLI_PROCESS: "En pause",
        ScenarioStatus.RUNNING: "En cours",
        ScenarioStatus.SUCCESS: "Terminé",
        ScenarioStatus.ERROR: "Erreur",
        ScenarioStatus.PARTIALLY_RUN: "Partiellement exécuté"
    }
    return prettify_map.get(status, "Inconnu")


def get_microplate_emoji(is_microplate: bool) -> str:
    """Return appropriate emoji for microplate analysis"""
    return "🧪" if is_microplate else "🔬"


def get_selection_step_status(scenario_id: str, fermentalg_state: State) -> str:
    """Get the status of the selection step for a given analysis scenario."""
    try:
        # Search for resources tagged with the selection step for this analysis
        # We'll search for resources that have the selection tag and are linked to this scenario
        search_builder = ResourceSearchBuilder() \
            .add_tag_filter(Tag(key=fermentalg_state.TAG_FERMENTOR_SELECTION_STEP, value=scenario_id))

        selection_resources = search_builder.search_all()

        if selection_resources:
            # Get the most recent selection resource
            latest_resource = max(selection_resources, key=lambda r: r.created_at or r.last_modified_at)
            return f"✅ {latest_resource.id[:8]}..."
        else:
            return "⏳ Non effectuée"

    except Exception as e:
        return "❌ Erreur"


def create_fermentalg_analysis_table_data(scenarios: List[Scenario], fermentalg_state: State) -> List[Dict]:
    """Create table data from Fermentalg analysis scenarios, grouped by analysis."""
    table_data = []

    # Group scenarios by analysis name
    analyses_dict = {}

    for scenario in scenarios:
        try:
            # Get tags for this scenario using find_by_entity to get existing tags
            entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)

            # Extract analysis name
            analysis_name = "Sans nom"
            analysis_name_tags = entity_tag_list.get_tags_by_key(fermentalg_state.TAG_FERMENTOR_ANALYSIS_NAME)
            if analysis_name_tags:
                analysis_name = analysis_name_tags[0].tag_value
            else:
                # Fallback to scenario title if no tag found
                analysis_name = scenario.title if scenario.title else f"Scénario {scenario.id[:8]}"

            # Initialize analysis entry if not exists
            if analysis_name not in analyses_dict:
                analyses_dict[analysis_name] = {
                    'analysis_name': analysis_name,
                    'load_scenario': None,
                    'selection_scenarios': [],
                    'pipeline_id': '',
                    'is_microplate': False,
                    'folder_name': 'Dossier racine',
                    'created_at': None,
                    'created_by': ''
                }

            # Check if this is a load scenario (data processing)
            fermentalg_tags = entity_tag_list.get_tags_by_key(fermentalg_state.TAG_FERMENTOR_FERMENTALG)
            is_load_scenario = any(tag.tag_value == fermentalg_state.TAG_DATA_PROCESSING for tag in fermentalg_tags)

            # Check if this is a selection scenario
            selection_tags = entity_tag_list.get_tags_by_key(fermentalg_state.TAG_FERMENTOR_FERMENTALG)
            is_selection_scenario = any(tag.tag_value == fermentalg_state.TAG_SELECTION_PROCESSING
                                        for tag in selection_tags)

            if is_load_scenario:
                analyses_dict[analysis_name]['load_scenario'] = scenario

                # Extract additional info from load scenario
                pipeline_id_tags = entity_tag_list.get_tags_by_key(
                    fermentalg_state.TAG_FERMENTOR_FERMENTALG_PIPELINE_ID)
                if pipeline_id_tags:
                    analyses_dict[analysis_name]['pipeline_id'] = pipeline_id_tags[0].tag_value[:8] + "..."

                # Extract microplate status
                microplate_tags = entity_tag_list.get_tags_by_key(fermentalg_state.TAG_MICROPLATE_ANALYSIS)
                if microplate_tags:
                    analyses_dict[analysis_name]['is_microplate'] = microplate_tags[0].tag_value.lower() == "true"

                # Get folder name
                if scenario.folder:
                    analyses_dict[analysis_name]['folder_name'] = scenario.folder.name

                # Set creation info
                analyses_dict[analysis_name]['created_at'] = scenario.created_at
                analyses_dict[analysis_name]['created_by'] = scenario.created_by.full_name if scenario.created_by else ""

            elif is_selection_scenario:
                analyses_dict[analysis_name]['selection_scenarios'].append(scenario)

        except Exception as e:
            # Si erreur lors du traitement d'un scénario, on l'ignore et continue
            st.warning(f"Erreur lors du traitement du scénario {scenario.id}: {str(e)}")
            continue

    # Create table rows from grouped analyses
    for analysis_name, analysis_data in analyses_dict.items():
        try:
            load_scenario = analysis_data['load_scenario']

            # Get Load Step status
            if load_scenario:
                load_step_status = f"{get_status_emoji(load_scenario.status)} {get_status_prettify(load_scenario.status)}"
                analysis_id = load_scenario.id
            else:
                load_step_status = "❌ Non trouvé"
                analysis_id = analysis_name.replace(" ", "_").lower()

            # Get Selection Step status
            selection_scenarios = analysis_data['selection_scenarios']
            if selection_scenarios:
                # Get the most recent selection scenario
                latest_selection = max(selection_scenarios, key=lambda s: s.created_at or s.last_modified_at)
                selection_step_status = f"{get_status_emoji(latest_selection.status)} {get_status_prettify(latest_selection.status)}"
            else:
                selection_step_status = "⏳ Non effectuée"

            row_data = {
                "id": analysis_id,  # Use load scenario ID or analysis name
                "Analysis Name": analysis_data['analysis_name'],
                "Type": f"{get_microplate_emoji(analysis_data['is_microplate'])} {'Microplaque' if analysis_data['is_microplate'] else 'Standard'}",
                "Load Step": load_step_status,
                "Selection Step": selection_step_status,
                "Folder": analysis_data['folder_name'],
                "Created": analysis_data['created_at'].strftime("%d/%m/%Y %H:%M") if analysis_data['created_at'] else "",
                "Created By": analysis_data['created_by'],
            }

            table_data.append(row_data)

        except Exception as e:
            # Si erreur lors du traitement d'une analyse, on l'ignore et continue
            st.warning(f"Erreur lors du traitement de l'analyse {analysis_name}: {str(e)}")
            continue

    return table_data


def create_fermentalg_slickgrid_columns() -> List[Dict]:
    """Create SlickGrid columns for Fermentalg analysis table with step columns."""
    columns = [
        {
            "id": "Analysis Name",
            "name": "Nom de l'analyse",
            "field": "Analysis Name",
            "sortable": True,
            "type": "string",
            "filterable": True,
            "width": 250,
        },
        {
            "id": "Type",
            "name": "Type",
            "field": "Type",
            "sortable": True,
            "type": "string",
            "filterable": True,
            "width": 150,
        },
        {
            "id": "Load Step",
            "name": "🔄 Étape Load",
            "field": "Load Step",
            "sortable": True,
            "type": "string",
            "filterable": True,
            "width": 150,
        },
        {
            "id": "Selection Step",
            "name": "✅ Étape Sélection",
            "field": "Selection Step",
            "sortable": True,
            "type": "string",
            "filterable": True,
            "width": 180,
        },
        {
            "id": "Folder",
            "name": "Dossier",
            "field": "Folder",
            "sortable": True,
            "type": "string",
            "filterable": True,
            "width": 150,
        },
        {
            "id": "Created",
            "name": "Créé le",
            "field": "Created",
            "sortable": True,
            "type": "date",
            "filterable": True,
            "width": 130,
        },
        {
            "id": "Created By",
            "name": "Créé par",
            "field": "Created By",
            "sortable": True,
            "type": "string",
            "filterable": True,
            "width": 120,
        },
    ]
    return columns


def render_fermentalg_analysis_table(scenarios: List[Scenario],
                                     fermentalg_state: State) -> Union[Optional[str],
                                                                       List[Dict]]:
    """Render the Fermentalg analysis table using SlickGrid and return selected scenario ID."""

    translate_service = fermentalg_state.get_translate_service()

    if not scenarios:
        st.info(translate_service.translate('no_fermentalg_found'))
        return None

    # Create table data
    table_data = create_fermentalg_analysis_table_data(scenarios, fermentalg_state)

    if not table_data:
        st.warning(translate_service.translate('cannot_load_analysis_data'))
        return None

    # Create columns
    columns = create_fermentalg_slickgrid_columns()

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
        key="fermentalg_analyses_grid",
        on_click="rerun"
    )

    # Handle row selection like in ubiome
    if grid_response is not None:
        print(grid_response)
        row_id, _ = grid_response  # _ is column, not needed for analysis selection
        # Return the selected scenario ID
        return row_id

    return None


def get_fermentalg_input_files_info(scenario_id: str, fermentalg_state: State) -> Dict[str, str]:
    """Get information about input files for a Fermentalg analysis."""
    files_info = {
        "info_csv": "Non trouvé",
        "raw_data_csv": "Non trouvé",
        "medium_csv": "Non trouvé",
        "follow_up_zip": "Non trouvé"
    }

    try:
        # Get pipeline ID from scenario tags
        scenario_tags = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario_id)
        pipeline_id_tags = scenario_tags.get_tags_by_key(fermentalg_state.TAG_FERMENTOR_FERMENTALG_PIPELINE_ID)

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
        st.error(f"Erreur lors de la récupération des fichiers d'entrée: {str(e)}")

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


def get_analysis_summary(scenario: Scenario, fermentalg_state: State) -> Dict[str, str]:
    """Get a summary of the analysis including key information."""
    summary = {}

    try:
        # Get tags
        entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)

        # Analysis name
        analysis_name_tags = entity_tag_list.get_tags_by_key(fermentalg_state.TAG_FERMENTOR_ANALYSIS_NAME)
        if analysis_name_tags:
            summary["Nom de l'analyse"] = analysis_name_tags[0].tag_value
        else:
            # Fallback to scenario title if no tag found
            summary["Nom de l'analyse"] = scenario.title if scenario.title else f"Scénario {scenario.id[:8]}"

        # Pipeline ID
        pipeline_id_tags = entity_tag_list.get_tags_by_key(fermentalg_state.TAG_FERMENTOR_FERMENTALG_PIPELINE_ID)
        summary["ID Pipeline"] = pipeline_id_tags[0].tag_value if pipeline_id_tags else "N/A"

        # Microplate status
        microplate_tags = entity_tag_list.get_tags_by_key(fermentalg_state.TAG_MICROPLATE_ANALYSIS)
        is_microplate = microplate_tags[0].tag_value.lower() == "true" if microplate_tags else False
        summary["Type d'analyse"] = f"{get_microplate_emoji(is_microplate)} {'Microplaque' if is_microplate else 'Standard'}"

        # Status
        summary["Statut"] = f"{get_status_emoji(scenario.status)} {get_status_prettify(scenario.status)}"

        # Dates
        summary["Créé le"] = scenario.created_at.strftime("%d/%m/%Y à %H:%M") if scenario.created_at else "N/A"
        summary["Modifié le"] = scenario.last_modified_at.strftime(
            "%d/%m/%Y à %H:%M") if scenario.last_modified_at else "N/A"

        # Creator
        summary["Créé par"] = scenario.created_by.full_name if scenario.created_by else "N/A"

        # Folder
        summary["Dossier"] = scenario.folder.name if scenario.folder else "Dossier racine"

    except Exception as e:
        st.error(f"Erreur lors de la création du résumé: {str(e)}")

    return summary


def save_uploaded_file(
        uploaded_file: Any, analysis_name: Optional[str] = None, pipeline_id: Optional[str] = None,
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
        if analysis_name or pipeline_id or file_type:
            user_origin = TagOrigin.current_user_origin()
            entity_tags = EntityTagList.find_by_entity(TagEntityType.RESOURCE, resource_model.id)
            entity_tags._default_origin = user_origin

            if analysis_name:
                analysis_name_parsed = Tag.parse_tag(analysis_name)
                entity_tags.add_tag(Tag('fermentor_analysis_name', analysis_name_parsed))

            if pipeline_id:
                pipeline_id_parsed = Tag.parse_tag(pipeline_id)
                entity_tags.add_tag(Tag('fermentor_fermentalg_pipeline_id', pipeline_id_parsed))
                entity_tags.add_tag(Tag('fermentor_fermentalg', 'input_file'))

            if file_type:
                file_type_parsed = Tag.parse_tag(file_type)
                entity_tags.add_tag(Tag('file_type', file_type_parsed))

        return resource_model

    return None


def setup_analysis_scenarios(analysis_name: str, fermentalg_state: State) -> bool:
    """
    Setup and configure all scenarios related to an analysis in the state.
    This function finds the load scenario and all selection scenarios for a given analysis.

    Args:
        analysis_name: Name of the analysis to setup
        fermentalg_state: State object to configure

    Returns:
        bool: True if setup was successful, False otherwise
    """
    try:
        # Reset current analysis scenarios
        fermentalg_state.reset_analysis_scenarios()

        # 1. Find the load scenario for this analysis
        load_scenarios: List[Scenario] = ScenarioSearchBuilder() \
            .add_tag_filter(Tag(key=fermentalg_state.TAG_FERMENTOR_FERMENTALG, value=fermentalg_state.TAG_DATA_PROCESSING)) \
            .add_tag_filter(Tag(key=fermentalg_state.TAG_FERMENTOR_ANALYSIS_NAME, value=analysis_name)) \
            .add_is_archived_filter(False) \
            .search_all()

        if not load_scenarios:
            st.error(f"❌ Aucun scénario de load trouvé pour l'analyse '{analysis_name}'")
            return False

        # Take the most recent load scenario and store it in state
        load_scenario = max(load_scenarios, key=lambda s: s.created_at or s.last_modified_at)
        fermentalg_state.set_load_scenario(load_scenario)

        # Get additional info from load scenario
        entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, load_scenario.id)

        # Get and store pipeline ID in state
        pipeline_id_tags = entity_tag_list.get_tags_by_key(fermentalg_state.TAG_FERMENTOR_FERMENTALG_PIPELINE_ID)
        if pipeline_id_tags:
            fermentalg_state.set_pipeline_id(pipeline_id_tags[0].tag_value)

        # Store analysis name in state
        fermentalg_state.set_analysis_name(analysis_name)

        # 2. Find all selection scenarios for this analysis
        selection_scenarios: List[Scenario] = ScenarioSearchBuilder() \
            .add_tag_filter(Tag(key=fermentalg_state.TAG_FERMENTOR_FERMENTALG, value=fermentalg_state.TAG_SELECTION_PROCESSING)) \
            .add_tag_filter(Tag(key=fermentalg_state.TAG_FERMENTOR_ANALYSIS_NAME, value=analysis_name)) \
            .add_is_archived_filter(False) \
            .search_all()

        # Sort selection scenarios by creation date (most recent first) and store in state
        selection_scenarios.sort(key=lambda s: s.created_at or s.last_modified_at, reverse=True)
        fermentalg_state.set_selection_scenarios(selection_scenarios)

        st.success(f"✅ Configuration réussie pour l'analyse '{analysis_name}': "
                   f"1 scénario de load, {len(selection_scenarios)} scénario(s) de sélection")

        # Log the stored scenarios for debugging
        st.info(f"📊 Stocké dans le state: Load scenario ID {load_scenario.id}, "
                f"{len(selection_scenarios)} scénario(s) de sélection")

        return True

    except Exception as e:
        st.error(f"❌ Erreur lors de la configuration des scénarios: {str(e)}")
        return False


def get_analysis_resource_set(fermentalg_state: State) -> Optional[Any]:
    """
    Get the ResourceSet output from the load scenario of the current analysis.

    Args:
        fermentalg_state: State object with configured scenarios

    Returns:
        ResourceSet or None if not found
    """
    return fermentalg_state.get_load_scenario_output('resource_set')
