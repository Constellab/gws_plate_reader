"""
Medium PCA Analysis Step for Cell Culture Dashboard
Allows users to run PCA analysis on medium composition data
"""
import streamlit as st
from typing import List, Optional
from datetime import datetime

from gws_core import Scenario, ScenarioProxy, ScenarioCreationType, InputTask, Tag
from gws_core.tag.tag_entity_type import TagEntityType
from gws_core.tag.entity_tag_list import EntityTagList
from gws_core.streamlit import StreamlitAuthenticateUser
from gws_plate_reader.cell_culture_app_core.cell_culture_state import CellCultureState
from gws_plate_reader.cell_culture_app_core.cell_culture_recipe import CellCultureRecipe
from gws_plate_reader.cell_culture_analysis import CellCultureMediumPCA, CellCultureMediumTableFilter


def get_available_media_from_quality_check(
        quality_check_scenario: Scenario, cell_culture_state: CellCultureState) -> List[str]:
    """
    Get list of unique medium names from the quality check scenario's filtered interpolated output

    :param quality_check_scenario: The quality check scenario
    :param cell_culture_state: The cell culture state
    :return: List of unique medium names
    """
    try:
        # Get the filtered interpolated ResourceSet from quality check
        scenario_proxy = ScenarioProxy.from_existing_scenario(quality_check_scenario.id)
        protocol_proxy = scenario_proxy.get_protocol()

        resource_set = protocol_proxy.get_output(cell_culture_state.QUALITY_CHECK_SCENARIO_INTERPOLATED_OUTPUT_NAME)

        if not resource_set:
            return []

        # Collect unique medium names from tags
        media = set()
        resources = resource_set.get_resources()

        from gws_core.impl.table.table import Table
        for resource in resources.values():
            if isinstance(resource, Table):
                if hasattr(resource, 'tags') and resource.tags:
                    for tag in resource.tags.get_tags():
                        if tag.key == cell_culture_state.TAG_MEDIUM:
                            if tag.value:
                                media.add(tag.value)

        return sorted(list(media))
    except Exception as e:
        # Handle any exception during media extraction
        st.error(f"Erreur lors de l'extraction des milieux : {str(e)}")
        return []


def launch_medium_pca_scenario(
        quality_check_scenario: Scenario,
        cell_culture_state: CellCultureState,
        load_scenario: Scenario,
        selected_media: List[str]) -> Optional[Scenario]:
    """
    Launch a Medium PCA analysis scenario

    :param quality_check_scenario: The parent quality check scenario
    :param cell_culture_state: The cell culture state
    :param load_scenario: The load scenario containing medium_table output
    :param selected_media: List of selected medium names to include in analysis
    :return: The created scenario or None if error
    """
    try:
        with StreamlitAuthenticateUser():
            # Create a new scenario for Medium PCA
            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            scenario_proxy = ScenarioProxy(
                None,
                folder=quality_check_scenario.folder,
                title=f"Medium PCA - {timestamp}",
                creation_type=ScenarioCreationType.MANUAL,
            )

            # Get the protocol
            protocol_proxy = scenario_proxy.get_protocol()

            # Get the load scenario protocol to access its medium_table output
            load_scenario_proxy = ScenarioProxy.from_existing_scenario(load_scenario.id)
            load_protocol_proxy = load_scenario_proxy.get_protocol()

            # Get the medium_table resource model from the load scenario's process
            # We need to get the process that produces the medium_table output
            medium_table_resource_model = load_protocol_proxy.get_process(
                cell_culture_state.PROCESS_NAME_DATA_PROCESSING
            ).get_output_resource_model('medium_table')

            if not medium_table_resource_model:
                raise ValueError("La sortie 'medium_table' n'est pas disponible dans le scénario de chargement")

            # Add input task for the medium_table from load scenario
            medium_input_task = protocol_proxy.add_process(
                InputTask, 'medium_table_input',
                {InputTask.config_name: medium_table_resource_model.id}
            )

            # Add the Medium Table Filter task
            filter_task = protocol_proxy.add_process(
                CellCultureMediumTableFilter,
                'medium_filter_task'
            )

            # Connect input to filter
            protocol_proxy.add_connector(
                out_port=medium_input_task >> 'resource',
                in_port=filter_task << 'medium_table'
            )

            # Set filter parameters
            filter_task.set_param('medium_column', 'MILIEU')
            filter_task.set_param('selected_medium', selected_media)

            # Add the Medium PCA task
            pca_task = protocol_proxy.add_process(
                CellCultureMediumPCA,
                'medium_pca_task'
            )

            # Connect the filtered table to the PCA task
            protocol_proxy.add_connector(
                out_port=filter_task >> 'filtered_table',
                in_port=pca_task << 'medium_table'
            )

            # Set PCA parameters
            pca_task.set_param('medium_column', 'MILIEU')

            # Add outputs
            protocol_proxy.add_output(
                'pca_scores_table',
                pca_task >> 'scores_table',
                flag_resource=True
            )
            protocol_proxy.add_output(
                'pca_scatter_plot',
                pca_task >> 'scatter_plot',
                flag_resource=True
            )
            protocol_proxy.add_output(
                'pca_biplot',
                pca_task >> 'biplot',
                flag_resource=True
            )

            # Inherit tags from parent quality check scenario
            parent_entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, quality_check_scenario.id)

            # Get recipe name from parent
            parent_recipe_name_tags = parent_entity_tag_list.get_tags_by_key(
                cell_culture_state.TAG_FERMENTOR_RECIPE_NAME)
            original_recipe_name = parent_recipe_name_tags[0].tag_value if parent_recipe_name_tags else quality_check_scenario.title

            # Get pipeline ID from parent
            parent_pipeline_id_tags = parent_entity_tag_list.get_tags_by_key(
                cell_culture_state.TAG_FERMENTOR_PIPELINE_ID)
            pipeline_id = parent_pipeline_id_tags[0].tag_value if parent_pipeline_id_tags else quality_check_scenario.id

            # Get microplate analysis flag from parent
            parent_microplate_tags = parent_entity_tag_list.get_tags_by_key(cell_culture_state.TAG_MICROPLATE_ANALYSIS)
            microplate_analysis = parent_microplate_tags[0].tag_value if parent_microplate_tags else "false"

            # Classification tag - indicate this is an analysis
            scenario_proxy.add_tag(Tag(cell_culture_state.TAG_FERMENTOR,
                                   cell_culture_state.TAG_ANALYSES_PROCESSING, is_propagable=False))

            # Inherit core identification tags
            scenario_proxy.add_tag(Tag(cell_culture_state.TAG_FERMENTOR_RECIPE_NAME,
                                   original_recipe_name, is_propagable=False))
            scenario_proxy.add_tag(Tag(cell_culture_state.TAG_FERMENTOR_PIPELINE_ID,
                                   pipeline_id, is_propagable=False))
            scenario_proxy.add_tag(Tag(cell_culture_state.TAG_MICROPLATE_ANALYSIS,
                                   microplate_analysis, is_propagable=False))

            # Link to parent quality check scenario
            scenario_proxy.add_tag(Tag(cell_culture_state.TAG_FERMENTOR_ANALYSES_PARENT_QUALITY_CHECK,
                                   quality_check_scenario.id, is_propagable=False))

            # Add timestamp and analysis type tags
            scenario_proxy.add_tag(Tag("analysis_timestamp", timestamp, is_propagable=False))
            scenario_proxy.add_tag(Tag("analysis_type", "medium_pca", is_propagable=False))

            # Add to queue
            scenario_proxy.add_to_queue()

            # Return the new scenario
            new_scenario = scenario_proxy.get_model()
            return new_scenario

    except Exception as e:
        st.error(translate_service.translate('error_launching_scenario_generic').format(
            scenario_type='Medium PCA', error=str(e)))
        import traceback
        st.code(traceback.format_exc())
        return None


def render_medium_pca_step(recipe: CellCultureRecipe, cell_culture_state: CellCultureState,
                           quality_check_scenario: Scenario) -> None:
    """
    Render the Medium PCA analysis step

    :param recipe: The Recipe instance
    :param cell_culture_state: The cell culture state
    :param quality_check_scenario: The quality check scenario to analyze
    """
    translate_service = cell_culture_state.get_translate_service()

    st.markdown(f"### 🧬 {translate_service.translate('pca_title')}")

    st.info(translate_service.translate('pca_info_intro'))

    # Get the load scenario to check for medium_table output
    load_scenario = recipe.get_load_scenario()

    if not load_scenario:
        st.warning(translate_service.translate('medium_pca_no_load_scenario'))
        return

    # Check if load scenario has medium_table output
    try:
        load_scenario_proxy = ScenarioProxy.from_existing_scenario(load_scenario.id)
        load_protocol_proxy = load_scenario_proxy.get_protocol()

        # Get the medium_table resource model from the load process
        medium_table_resource_model = load_protocol_proxy.get_process(
            cell_culture_state.PROCESS_NAME_DATA_PROCESSING
        ).get_output_resource_model('medium_table')

        if not medium_table_resource_model:
            st.warning(translate_service.translate('medium_pca_table_unavailable'))
            st.info(translate_service.translate('medium_pca_table_success_info'))
            return

        st.success(translate_service.translate('medium_table_available').format(name=medium_table_resource_model.name))
    except Exception as e:
        st.warning(translate_service.translate('medium_pca_table_check_error').format(error=str(e)))
        return

    # Get available media from quality check scenario
    available_media = get_available_media_from_quality_check(quality_check_scenario, cell_culture_state)

    if not available_media:
        st.warning(translate_service.translate('pca_error_media_info'))
        return

    st.markdown(f"**{translate_service.translate('pca_available_media')}** : {', '.join(available_media)}")

    # Check existing PCA scenarios
    existing_pca_scenarios = recipe.get_medium_pca_scenarios_for_quality_check(quality_check_scenario.id)

    if existing_pca_scenarios:
        st.markdown(f"**{translate_service.translate('pca_existing_analyses')}** : {len(existing_pca_scenarios)}")
        with st.expander(f"📊 {translate_service.translate('view_button')} {translate_service.translate('pca_existing_analyses').lower()}"):
            for idx, pca_scenario in enumerate(existing_pca_scenarios):
                st.write(
                    f"{idx + 1}. {pca_scenario.title} (ID: {pca_scenario.id}) - {translate_service.translate('status')}: {pca_scenario.status.name}")

    # Configuration form for new PCA
    st.markdown("---")
    st.markdown(f"### ➕ {translate_service.translate('pca_launch_button')}")

    with st.form(key=f"medium_pca_form_{quality_check_scenario.id}"):
        st.markdown(f"**{translate_service.translate('pca_select_media')}**")

        # Multiselect for media selection
        selected_media = st.multiselect(
            translate_service.translate('pca_select_media'),
            options=available_media,
            default=available_media,
            help=translate_service.translate('pca_select_media')
        )

        # Submit button
        submit_button = st.form_submit_button(
            f"🚀 {translate_service.translate('pca_launch_button')}",
            type="primary",
            use_container_width=True
        )

        if submit_button:
            if not selected_media:
                st.error(translate_service.translate('pca_select_media_warning'))
            else:
                # Launch PCA scenario
                pca_scenario = launch_medium_pca_scenario(
                    quality_check_scenario,
                    cell_culture_state,
                    load_scenario,
                    selected_media
                )

                if pca_scenario:
                    st.success(f"✅ {translate_service.translate('pca_launched_success')} ID : {pca_scenario.id}")
                    st.info(translate_service.translate('analysis_running'))

                    # Add to recipe
                    recipe.add_medium_pca_scenario(quality_check_scenario.id, pca_scenario)

                    st.rerun()
                else:
                    st.error(translate_service.translate('pca_error_launching'))

    # Info box with PCA explanation
    with st.expander(f"💡 {translate_service.translate('pca_help_title')}"):
        st.markdown(f"### {translate_service.translate('pca_help_intro_title')}")
        st.markdown(translate_service.translate('pca_help_intro_text'))

        st.markdown(f"\n### {translate_service.translate('pca_help_scores_title')}")
        st.markdown(f"- {translate_service.translate('pca_help_scores_1')}")
        st.markdown(f"- {translate_service.translate('pca_help_scores_2')}")
        st.markdown(f"- {translate_service.translate('pca_help_scores_3')}")
        st.markdown(f"\n{translate_service.translate('pca_help_scores_tip')}")

        st.markdown(f"\n### {translate_service.translate('pca_help_scatter_title')}")
        st.markdown(f"- {translate_service.translate('pca_help_scatter_1')}")
        st.markdown(f"- {translate_service.translate('pca_help_scatter_2')}")
        st.markdown(f"- {translate_service.translate('pca_help_scatter_3')}")
        st.markdown(f"- {translate_service.translate('pca_help_scatter_4')}")
        st.markdown(f"- {translate_service.translate('pca_help_scatter_5')}")
        st.markdown(f"- {translate_service.translate('pca_help_scatter_6')}")

        st.markdown(f"\n### {translate_service.translate('pca_help_biplot_title')}")
        st.markdown(f"- {translate_service.translate('pca_help_biplot_1')}")
        st.markdown(f"- {translate_service.translate('pca_help_biplot_2')}")
        st.markdown(f"    - {translate_service.translate('pca_help_biplot_2a')}")
        st.markdown(f"    - {translate_service.translate('pca_help_biplot_2b')}")
        st.markdown(f"    - {translate_service.translate('pca_help_biplot_2c')}")
        st.markdown(f"    - {translate_service.translate('pca_help_biplot_2d')}")
        st.markdown(f"- {translate_service.translate('pca_help_biplot_3')}")
        st.markdown(f"    - {translate_service.translate('pca_help_biplot_3a')}")
        st.markdown(f"    - {translate_service.translate('pca_help_biplot_3b')}")
        st.markdown(f"    - {translate_service.translate('pca_help_biplot_3c')}")
        st.markdown(f"\n{translate_service.translate('pca_help_biplot_tip')}")
