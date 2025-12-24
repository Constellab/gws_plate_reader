"""
Medium UMAP Analysis Step for Cell Culture Dashboard
Allows users to run UMAP analysis on medium composition data
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
from gws_plate_reader.cell_culture_analysis import CellCultureMediumTableFilter
from gws_design_of_experiments.umap.umap import UMAPTask


def get_available_media_from_quality_check(
        quality_check_scenario: Scenario, cell_culture_state: CellCultureState) -> List[str]:
    """
    Get list of unique medium names from the quality check scenario's filtered interpolated output

    :param quality_check_scenario: The quality check scenario
    :param cell_culture_state: The cell culture state
    :return: List of unique medium names
    """
    translate_service = cell_culture_state.get_translate_service()
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
        st.error(translate_service.translate('error_extracting_media').format(error=str(e)))
        return []


def launch_medium_umap_scenario(
        quality_check_scenario: Scenario,
        cell_culture_state: CellCultureState,
        load_scenario: Scenario,
        selected_media: List[str],
        n_neighbors: int,
        min_dist: float,
        metric: str,
        scale_data: bool,
        n_clusters: Optional[int]) -> Optional[Scenario]:
    """
    Launch a Medium UMAP analysis scenario

    :param quality_check_scenario: The parent quality check scenario
    :param cell_culture_state: The cell culture state
    :param load_scenario: The load scenario containing medium_table output
    :param selected_media: List of selected medium names to include in analysis
    :param n_neighbors: Number of neighbors for UMAP
    :param min_dist: Minimum distance for UMAP
    :param metric: Distance metric for UMAP
    :param scale_data: Whether to scale data before UMAP
    :param n_clusters: Number of clusters for K-Means (optional)
    :return: The created scenario or None if error
    """
    translate_service = cell_culture_state.get_translate_service()
    try:
        with StreamlitAuthenticateUser():
            # Create a new scenario for Medium UMAP
            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            scenario_proxy = ScenarioProxy(
                None,
                folder=quality_check_scenario.folder,
                title=f"Medium UMAP - {timestamp}",
                creation_type=ScenarioCreationType.MANUAL,
            )

            # Get the protocol
            protocol_proxy = scenario_proxy.get_protocol()

            # Get the load scenario protocol to access its medium_table output
            load_scenario_proxy = ScenarioProxy.from_existing_scenario(load_scenario.id)
            load_protocol_proxy = load_scenario_proxy.get_protocol()

            # Get the medium_table resource model from the load scenario's process
            medium_table_resource_model = load_protocol_proxy.get_process(
                cell_culture_state.PROCESS_NAME_DATA_PROCESSING
            ).get_output_resource_model('medium_table')

            if not medium_table_resource_model:
                raise ValueError(translate_service.translate('medium_table_output_unavailable'))

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

            # Add the UMAP task
            umap_task = protocol_proxy.add_process(
                UMAPTask,
                'medium_umap_task'
            )

            # Connect the filtered table to the UMAP task
            protocol_proxy.add_connector(
                out_port=filter_task >> 'filtered_table',
                in_port=umap_task << 'data'
            )

            # Set UMAP parameters
            umap_task.set_param('n_neighbors', n_neighbors)
            umap_task.set_param('min_dist', min_dist)
            umap_task.set_param('metric', metric)
            umap_task.set_param('scale_data', scale_data)
            umap_task.set_param('color_by', 'MILIEU')
            umap_task.set_param('columns_to_exclude', ['MILIEU'])
            if n_clusters is not None:
                umap_task.set_param('n_clusters', n_clusters)

            # Add outputs
            protocol_proxy.add_output(
                'umap_2d_plot',
                umap_task >> 'umap_2d_plot',
                flag_resource=True
            )
            protocol_proxy.add_output(
                'umap_3d_plot',
                umap_task >> 'umap_3d_plot',
                flag_resource=True
            )
            protocol_proxy.add_output(
                'umap_2d_table',
                umap_task >> 'umap_2d_table',
                flag_resource=True
            )
            protocol_proxy.add_output(
                'umap_3d_table',
                umap_task >> 'umap_3d_table',
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
            scenario_proxy.add_tag(Tag("analysis_type", "medium_umap", is_propagable=False))

            # Add to queue
            scenario_proxy.add_to_queue()

            # Return the new scenario
            new_scenario = scenario_proxy.get_model()
            return new_scenario

    except Exception as e:
        st.error(translate_service.translate('error_launching_scenario_generic').format(
            scenario_type='Medium UMAP', error=str(e)))
        import traceback
        st.code(traceback.format_exc())
        return None


def render_medium_umap_step(recipe: CellCultureRecipe, cell_culture_state: CellCultureState,
                            quality_check_scenario: Scenario) -> None:
    """
    Render the Medium UMAP analysis step

    :param recipe: The Recipe instance
    :param cell_culture_state: The cell culture state
    :param quality_check_scenario: The quality check scenario to analyze
    """
    translate_service = cell_culture_state.get_translate_service()

    st.markdown("### 🗺️ " + translate_service.translate('medium_umap_title'))

    st.info(translate_service.translate('medium_umap_info'))

    # Get the load scenario to check for medium_table output
    load_scenario = recipe.get_load_scenario()

    if not load_scenario:
        st.warning(translate_service.translate('medium_umap_no_load_scenario'))
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
            st.warning(translate_service.translate('medium_table_not_available'))
            st.info(translate_service.translate('medium_table_success_info'))
            return

        st.success(translate_service.translate('medium_table_available').format(name=medium_table_resource_model.name))
    except Exception as e:
        st.warning(translate_service.translate('medium_table_check_error').format(error=str(e)))
        return

    # Get available media from quality check scenario
    available_media = get_available_media_from_quality_check(quality_check_scenario, cell_culture_state)

    if not available_media:
        st.warning(translate_service.translate('no_medium_found_qc'))
        return

    st.markdown(f"**{translate_service.translate('available_media')}** : {', '.join(available_media)}")

    # Check existing UMAP scenarios
    existing_umap_scenarios = recipe.get_medium_umap_scenarios_for_quality_check(quality_check_scenario.id)

    if existing_umap_scenarios:
        st.markdown(f"**{translate_service.translate('existing_umap_analyses')}** : {len(existing_umap_scenarios)}")
        with st.expander("📊 " + translate_service.translate('view_existing_umap')):
            for idx, umap_scenario in enumerate(existing_umap_scenarios):
                st.write(
                    f"{idx + 1}. {umap_scenario.title} (ID: {umap_scenario.id}) - Statut: {umap_scenario.status.name}")

    # Configuration form for new UMAP
    st.markdown("---")
    st.markdown(f"### ➕ {translate_service.translate('launch_new_umap')}")

    with st.form(key=f"medium_umap_form_{quality_check_scenario.id}"):
        st.markdown(f"**{translate_service.translate('media_selection')}**")

        # Multiselect for media selection
        selected_media = st.multiselect(
            translate_service.translate('media_to_include'),
            options=available_media,
            default=available_media,
            help=translate_service.translate('media_to_include_help')
        )

        st.markdown(f"**{translate_service.translate('umap_parameters')}**")

        col1, col2 = st.columns(2)

        with col1:
            n_neighbors = st.slider(
                translate_service.translate('n_neighbors_label'),
                min_value=2,
                max_value=50,
                value=15,
                help=translate_service.translate('n_neighbors_help')
            )

            metric = st.selectbox(
                translate_service.translate('distance_metric_label'),
                options=["euclidean", "manhattan", "cosine", "correlation"],
                index=0,
                help=translate_service.translate('distance_metric_help')
            )

        with col2:
            min_dist = st.slider(
                translate_service.translate('min_dist_label'),
                min_value=0.0,
                max_value=0.99,
                value=0.1,
                step=0.05,
                help=translate_service.translate('min_dist_help')
            )

            scale_data = st.checkbox(
                translate_service.translate('normalize_data_label'),
                value=True,
                help=translate_service.translate('normalize_data_help')
            )

        st.markdown(f"**{translate_service.translate('optional_clustering')}**")
        enable_clustering = st.checkbox(translate_service.translate('enable_clustering_label'), value=False)
        n_clusters = None
        if enable_clustering:
            n_clusters = st.slider(
                translate_service.translate('n_clusters_label'),
                min_value=2,
                max_value=10,
                value=3,
                help=translate_service.translate('n_clusters_help')
            )

        # Submit button
        submit_button = st.form_submit_button(
            translate_service.translate('launch_analysis_button_with_type').format(analysis_type='UMAP'),
            type="primary",
            width='stretch',
            disabled=cell_culture_state.get_is_standalone()
        )
        if cell_culture_state.get_is_standalone():
            st.info(translate_service.translate('standalone_mode_function_blocked'))

        if submit_button:
            if not selected_media:
                st.error(translate_service.translate('select_target_first'))
            else:
                # Launch UMAP scenario
                umap_scenario = launch_medium_umap_scenario(
                    quality_check_scenario,
                    cell_culture_state,
                    load_scenario,
                    selected_media,
                    n_neighbors,
                    min_dist,
                    metric,
                    scale_data,
                    n_clusters
                )

                if umap_scenario:
                    st.success(translate_service.translate('umap_launched_success').format(id=umap_scenario.id))
                    st.info(translate_service.translate('analysis_running'))

                    # Add to recipe
                    recipe.add_medium_umap_scenario(quality_check_scenario.id, umap_scenario)

                    st.rerun()
                else:
                    st.error(translate_service.translate('umap_launch_error'))

    # Info box with UMAP explanation
    with st.expander(translate_service.translate('help_title').format(analysis_type='UMAP')):
        st.markdown("### " + translate_service.translate('umap_help_what_is'))
        st.markdown(translate_service.translate('umap_help_intro'))

        st.markdown("### " + translate_service.translate('umap_help_interpretation'))

        st.markdown("**" + translate_service.translate('umap_help_2d_3d_plots') + "** :")
        st.markdown("- " + translate_service.translate('umap_help_plot_point'))
        st.markdown("- " + translate_service.translate('umap_help_plot_proximity'))
        st.markdown("- " + translate_service.translate('umap_help_plot_groups'))
        st.markdown("- " + translate_service.translate('umap_help_plot_color'))

        st.markdown("**" + translate_service.translate('umap_help_key_params') + "** :")
        st.markdown("- **" + translate_service.translate('n_neighbors_label') +
                    "** : " + translate_service.translate('umap_help_n_neighbors_desc'))
        st.markdown(
            "- **" + translate_service.translate('min_dist_label') + "** : " + translate_service.translate('umap_help_min_dist_desc'))
        st.markdown("- **" + translate_service.translate('distance_metric_label') +
                    "** : " + translate_service.translate('umap_help_metric_desc'))

        st.markdown("**" + translate_service.translate('optional_clustering') + "** :")
        st.markdown("- " + translate_service.translate('umap_help_clustering_desc'))
        st.markdown("- " + translate_service.translate('umap_help_clustering_useful'))
        st.markdown("- " + translate_service.translate('umap_help_clustering_choice'))

        st.markdown("### " + translate_service.translate('umap_help_usage_tips'))
        st.markdown("- " + translate_service.translate('umap_help_tip_defaults'))
        st.markdown("- " + translate_service.translate('umap_help_tip_neighbors'))
        st.markdown("- " + translate_service.translate('umap_help_tip_clustering'))
        st.markdown("- " + translate_service.translate('umap_help_tip_compare'))
