"""
Medium UMAP Analysis Step for Cell Culture Dashboard
Allows users to run UMAP analysis on medium composition data
"""

import traceback
from datetime import datetime

import streamlit as st
from gws_core import (
    InputTask,
    ResourceModel,
    Scenario,
    ScenarioCreationType,
    ScenarioProxy,
    Table,
    Tag,
)
from gws_core.tag.entity_tag_list import EntityTagList
from gws_core.tag.tag_entity_type import TagEntityType
from gws_design_of_experiments.umap.umap import UMAPTask

from gws_plate_reader.cell_culture_analysis import CellCultureMediumTableFilter
from gws_plate_reader.cell_culture_app_core._constellab_bioprocess_core.cell_culture_recipe import (
    CellCultureRecipe,
)
from gws_plate_reader.cell_culture_app_core._constellab_bioprocess_core.cell_culture_state import (
    CellCultureState,
)


def get_available_media_from_quality_check(
    quality_check_scenario: Scenario, cell_culture_state: CellCultureState
) -> list[str]:
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

        resource_set = protocol_proxy.get_output(
            cell_culture_state.QUALITY_CHECK_SCENARIO_INTERPOLATED_OUTPUT_NAME
        )

        if not resource_set:
            return []

        # Collect unique medium names from tags
        media = set()
        resources = resource_set.get_resources()

        for resource in resources.values():
            if isinstance(resource, Table) and hasattr(resource, "tags") and resource.tags:
                for tag in resource.tags.get_tags():
                    if tag.key == cell_culture_state.TAG_MEDIUM and tag.value:
                        media.add(tag.value)

        return sorted(media)
    except Exception as e:
        # Handle any exception during media extraction
        st.error(translate_service.translate("error_extracting_media").format(error=str(e)))
        return []


def launch_medium_umap_scenario(
    quality_check_scenario: Scenario,
    cell_culture_state: CellCultureState,
    load_scenario: Scenario,
    selected_media: list[str],
    n_neighbors: int,
    min_dist: float,
    metric: str,
    scale_data: bool,
    n_clusters: int | None,
    list_hover_data_columns: list[str] | None = None,
) -> Scenario | None:
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
    :param list_hover_data_columns: List of columns to include as hover data in UMAP plots (optional)
    :return: The created scenario or None if error
    """
    translate_service = cell_culture_state.get_translate_service()
    try:
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
        ).get_output_resource_model("medium_table")

        if not medium_table_resource_model:
            raise ValueError(translate_service.translate("medium_table_output_unavailable"))

            # Add input task for the medium_table from load scenario
        medium_input_task = protocol_proxy.add_process(
            InputTask,
            "medium_table_input",
            {InputTask.config_name: medium_table_resource_model.id},
        )

        # Add the Medium Table Filter task
        filter_task = protocol_proxy.add_process(CellCultureMediumTableFilter, "medium_filter_task")

        # Connect input to filter
        protocol_proxy.add_connector(
            out_port=medium_input_task >> "resource", in_port=filter_task << "medium_table"
        )

        # Set filter parameters
        filter_task.set_param("medium_column", cell_culture_state.MEDIUM_COLUMN_NAME)
        filter_task.set_param("selected_medium", selected_media)

        # Add the UMAP task
        umap_task = protocol_proxy.add_process(UMAPTask, "medium_umap_task")

        # Connect the filtered table to the UMAP task
        protocol_proxy.add_connector(
            out_port=filter_task >> "filtered_table", in_port=umap_task << "data"
        )

        # Set UMAP parameters
        umap_task.set_param("n_neighbors", n_neighbors)
        umap_task.set_param("min_dist", min_dist)
        umap_task.set_param("metric", metric)
        umap_task.set_param("scale_data", scale_data)
        umap_task.set_param("columns_to_exclude", [cell_culture_state.MEDIUM_COLUMN_NAME])
        if n_clusters is not None:
            umap_task.set_param("n_clusters", n_clusters)
        if list_hover_data_columns is not None:
            umap_task.set_param("hover_data_columns", list_hover_data_columns)

            # Add outputs
        protocol_proxy.add_output("umap_2d_plot", umap_task >> "umap_2d_plot", flag_resource=True)
        protocol_proxy.add_output("umap_3d_plot", umap_task >> "umap_3d_plot", flag_resource=True)
        protocol_proxy.add_output("umap_2d_table", umap_task >> "umap_2d_table", flag_resource=True)
        protocol_proxy.add_output("umap_3d_table", umap_task >> "umap_3d_table", flag_resource=True)

        # Inherit tags from parent quality check scenario
        parent_entity_tag_list = EntityTagList.find_by_entity(
            TagEntityType.SCENARIO, quality_check_scenario.id
        )

        # Get recipe name from parent
        parent_recipe_name_tags = parent_entity_tag_list.get_tags_by_key(
            cell_culture_state.TAG_BIOPROCESS_RECIPE_NAME
        )
        original_recipe_name = (
            parent_recipe_name_tags[0].tag_value
            if parent_recipe_name_tags
            else quality_check_scenario.title
        )

        # Get pipeline ID from parent
        parent_pipeline_id_tags = parent_entity_tag_list.get_tags_by_key(
            cell_culture_state.TAG_BIOPROCESS_PIPELINE_ID
        )
        pipeline_id = (
            parent_pipeline_id_tags[0].tag_value
            if parent_pipeline_id_tags
            else quality_check_scenario.id
        )

        # Get microplate analysis flag from parent
        parent_microplate_tags = parent_entity_tag_list.get_tags_by_key(
            cell_culture_state.TAG_MICROPLATE_ANALYSIS
        )
        microplate_analysis = (
            parent_microplate_tags[0].tag_value if parent_microplate_tags else "false"
        )

        # Classification tag - indicate this is an analysis
        scenario_proxy.add_tag(
            Tag(
                cell_culture_state.TAG_BIOPROCESS,
                cell_culture_state.TAG_ANALYSES_PROCESSING,
                is_propagable=False,
            )
        )

        # Inherit core identification tags
        scenario_proxy.add_tag(
            Tag(
                cell_culture_state.TAG_BIOPROCESS_RECIPE_NAME,
                original_recipe_name,
                is_propagable=False,
            )
        )
        scenario_proxy.add_tag(
            Tag(cell_culture_state.TAG_BIOPROCESS_PIPELINE_ID, pipeline_id, is_propagable=False)
        )
        scenario_proxy.add_tag(
            Tag(
                cell_culture_state.TAG_MICROPLATE_ANALYSIS,
                microplate_analysis,
                is_propagable=False,
            )
        )

        # Link to parent quality check scenario
        scenario_proxy.add_tag(
            Tag(
                cell_culture_state.TAG_ANALYSES_PARENT_QUALITY_CHECK,
                quality_check_scenario.id,
                is_propagable=False,
            )
        )

        # Add timestamp and analysis type tags
        scenario_proxy.add_tag(Tag("analysis_timestamp", timestamp, is_propagable=False))
        scenario_proxy.add_tag(Tag("analysis_type", "medium_umap", is_propagable=False))

        # Add to queue
        scenario_proxy.add_to_queue()

        # Return the new scenario
        new_scenario = scenario_proxy.get_model()
        return new_scenario

    except Exception as e:
        st.error(
            translate_service.translate("error_launching_scenario_generic").format(
                scenario_type="Medium UMAP", error=str(e)
            )
        )
        st.code(traceback.format_exc())
        return None


def render_medium_umap_step(
    recipe: CellCultureRecipe,
    cell_culture_state: CellCultureState,
    quality_check_scenario: Scenario,
) -> None:
    """
    Render the Medium UMAP analysis step

    :param recipe: The Recipe instance
    :param cell_culture_state: The cell culture state
    :param quality_check_scenario: The quality check scenario to analyze
    """
    translate_service = cell_culture_state.get_translate_service()

    # Info box with UMAP explanation
    with st.expander(translate_service.translate("help_title").format(analysis_type="UMAP")):
        st.markdown("### " + translate_service.translate("umap_help_what_is"))
        st.markdown(translate_service.translate("umap_help_intro"))

        st.markdown("### " + translate_service.translate("umap_help_interpretation"))

        st.markdown("**" + translate_service.translate("umap_help_2d_3d_plots") + "** :")
        st.markdown("- " + translate_service.translate("umap_help_plot_point"))
        st.markdown("- " + translate_service.translate("umap_help_plot_proximity"))
        st.markdown("- " + translate_service.translate("umap_help_plot_groups"))
        st.markdown("- " + translate_service.translate("umap_help_plot_color"))

        st.markdown("**" + translate_service.translate("umap_help_key_params") + "** :")
        st.markdown(
            "- **"
            + translate_service.translate("n_neighbors_label")
            + "** : "
            + translate_service.translate("umap_help_n_neighbors_desc")
        )
        st.markdown(
            "- **"
            + translate_service.translate("min_dist_label")
            + "** : "
            + translate_service.translate("umap_help_min_dist_desc")
        )
        st.markdown(
            "- **"
            + translate_service.translate("distance_metric_label")
            + "** : "
            + translate_service.translate("umap_help_metric_desc")
        )

        st.markdown("**" + translate_service.translate("optional_clustering") + "** :")
        st.markdown("- " + translate_service.translate("umap_help_clustering_desc"))
        st.markdown("- " + translate_service.translate("umap_help_clustering_useful"))
        st.markdown("- " + translate_service.translate("umap_help_clustering_choice"))

        st.markdown("### " + translate_service.translate("umap_help_usage_tips"))
        st.markdown("- " + translate_service.translate("umap_help_tip_defaults"))
        st.markdown("- " + translate_service.translate("umap_help_tip_neighbors"))
        st.markdown("- " + translate_service.translate("umap_help_tip_clustering"))
        st.markdown("- " + translate_service.translate("umap_help_tip_compare"))

    # Get the load scenario to check for medium_table output
    load_scenario = recipe.get_load_scenario()

    if not load_scenario:
        st.warning(translate_service.translate("medium_umap_no_load_scenario"))
        return

    # Check if load scenario has medium_table output
    try:
        load_scenario_proxy = ScenarioProxy.from_existing_scenario(load_scenario.id)
        load_protocol_proxy = load_scenario_proxy.get_protocol()

        # Get the medium_table resource model from the load process
        medium_table_resource_model = load_protocol_proxy.get_process(
            cell_culture_state.PROCESS_NAME_DATA_PROCESSING
        ).get_output_resource_model("medium_table")

        if not medium_table_resource_model:
            st.warning(translate_service.translate("medium_table_not_available"))
            st.info(translate_service.translate("medium_table_success_info"))
            return

        st.success(
            translate_service.translate("medium_table_available").format(
                name=medium_table_resource_model.name
            )
        )
    except Exception as e:
        st.warning(translate_service.translate("medium_table_check_error").format(error=str(e)))
        return

    # Get available media from quality check scenario
    available_media = get_available_media_from_quality_check(
        quality_check_scenario, cell_culture_state
    )

    if not available_media:
        st.warning(translate_service.translate("no_medium_found_qc"))
        return

    # Check existing UMAP scenarios
    recipe.get_medium_umap_scenarios_for_quality_check(quality_check_scenario.id)

    # Configuration form for new UMAP
    st.markdown("---")
    st.markdown(f"### ➕ {translate_service.translate('launch_new_umap')}")

    with st.form(key=f"medium_umap_form_{quality_check_scenario.id}"):
        # Get available columns from medium_table
        try:
            load_scenario_proxy = ScenarioProxy.from_existing_scenario(load_scenario.id)
            load_protocol_proxy = load_scenario_proxy.get_protocol()
            medium_table_resource_model = load_protocol_proxy.get_process(
                cell_culture_state.PROCESS_NAME_DATA_PROCESSING
            ).get_output_resource_model("medium_table")

            # Get the actual table resource to check columns
            medium_resource = ResourceModel.get_by_id_and_check(medium_table_resource_model.id)
            medium_df = medium_resource.get_resource().get_data()
            available_columns = medium_df.columns.tolist()

            # Try to auto-detect the medium column
            medium_col_candidates = [
                col for col in available_columns if col.upper() in ["MILIEU", "MEDIUM", "MEDIA"]
            ]
            default_medium_col = (
                medium_col_candidates[0]
                if medium_col_candidates
                else (available_columns[0] if available_columns else "MILIEU")
            )
        except Exception as e:
            available_columns = ["MILIEU", "Medium", "Media"]
            default_medium_col = "MILIEU"
            st.warning(f"⚠️ Impossible to load columns from the medium table: {str(e)}")

        # Check minimum number of data columns (excluding medium column)
        data_columns_count = len(
            [col for col in available_columns if col.upper() not in ["MILIEU", "MEDIUM", "MEDIA"]]
        )
        st.info(translate_service.translate("data_columns_count").format(count=data_columns_count))
        if data_columns_count < 2:
            st.warning(translate_service.translate("min_columns_required_for_analysis"))

        # Column selection for medium identifier
        medium_column = st.selectbox(
            translate_service.translate("medium_column_label_umap"),
            options=available_columns,
            index=available_columns.index(default_medium_col)
            if default_medium_col in available_columns
            else 0,
            help=translate_service.translate("medium_column_help"),
        )

        st.markdown(f"**{translate_service.translate('media_selection')}**")

        # Multiselect for media selection
        selected_media = st.multiselect(
            translate_service.translate("media_to_include"),
            options=available_media,
            default=available_media,
            help=translate_service.translate("media_to_include_help"),
        )

        st.markdown(f"**{translate_service.translate('umap_parameters')}**")

        col1, col2 = st.columns(2)

        with col1:
            n_neighbors = st.slider(
                translate_service.translate("n_neighbors_label"),
                min_value=2,
                max_value=50,
                value=15,
                help=translate_service.translate("n_neighbors_help"),
            )

            metric = st.selectbox(
                translate_service.translate("distance_metric_label"),
                options=["euclidean", "manhattan", "cosine", "correlation"],
                index=0,
                help=translate_service.translate("distance_metric_help"),
            )

        with col2:
            min_dist = st.slider(
                translate_service.translate("min_dist_label"),
                min_value=0.0,
                max_value=0.99,
                value=0.1,
                step=0.05,
                help=translate_service.translate("min_dist_help"),
            )

            scale_data = st.checkbox(
                translate_service.translate("normalize_data_label"),
                value=True,
                help=translate_service.translate("normalize_data_help"),
            )

        st.markdown(f"**{translate_service.translate('optional_clustering')}**")
        enable_clustering = st.checkbox(
            translate_service.translate("enable_clustering_label"), value=False
        )
        n_clusters = None
        if enable_clustering:
            n_clusters = st.slider(
                translate_service.translate("n_clusters_label"),
                min_value=2,
                max_value=10,
                value=3,
                help=translate_service.translate("n_clusters_help"),
            )
        list_hover_data_columns = st.multiselect(
            translate_service.translate("hover_data_columns_label"),
            options=available_columns,
            default=None,
            help=translate_service.translate("hover_data_columns_help"),
        )

        # Submit button
        submit_button = st.form_submit_button(
            translate_service.translate("launch_analysis_button_with_type").format(
                analysis_type="UMAP"
            ),
            type="primary",
            width="stretch",
            disabled=cell_culture_state.get_is_standalone(),
        )
        if cell_culture_state.get_is_standalone():
            st.info(translate_service.translate("standalone_mode_function_blocked"))

        if submit_button:
            if not selected_media:
                st.error(translate_service.translate("select_target_first"))
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
                    n_clusters,
                    list_hover_data_columns,
                )

                if umap_scenario:
                    st.success(translate_service.translate("umap_launched_success"))
                    st.info(translate_service.translate("analysis_running"))

                    # Add to recipe
                    recipe.add_medium_umap_scenario(quality_check_scenario.id, umap_scenario)

                    st.rerun()
                else:
                    st.error(translate_service.translate("umap_launch_error"))
