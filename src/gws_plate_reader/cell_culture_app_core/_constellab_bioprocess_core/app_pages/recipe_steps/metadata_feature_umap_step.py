"""
Metadata Feature UMAP Analysis Step for Cell Culture Dashboard
Allows users to run UMAP analysis on combined metadata and feature extraction data
"""

import traceback
from datetime import datetime

import streamlit as st
from gws_core import InputTask, Scenario, ScenarioCreationType, ScenarioProxy, Tag
from gws_core.tag.entity_tag_list import EntityTagList
from gws_core.tag.tag_entity_type import TagEntityType
from gws_design_of_experiments.umap.umap import UMAPTask
from gws_plate_reader.cell_culture_app_core._constellab_bioprocess_core.cell_culture_recipe import (
    CellCultureRecipe,
)
from gws_plate_reader.cell_culture_app_core._constellab_bioprocess_core.cell_culture_state import (
    CellCultureState,
)
from gws_plate_reader.cell_culture_app_core._constellab_bioprocess_core.functions_steps import (
    render_launched_scenarios_expander,
)
from gws_plate_reader.cell_culture_filter import (
    CellCultureMergeFeatureMetadata,
    CellCulturePrepareFeatureMetadataTable,
)


def launch_metadata_feature_umap_scenario(
    quality_check_scenario: Scenario,
    cell_culture_state: CellCultureState,
    load_scenario: Scenario,
    feature_extraction_scenario: Scenario,
    medium_name_column: str,
    n_neighbors: int,
    min_dist: float,
    metric: str,
    scale_data: bool,
    n_clusters: int | None,
    columns_to_exclude: list[str] | None = None,
    hover_data_columns: list[str] | None = None,
) -> Scenario | None:
    """
    Launch a Metadata Feature UMAP analysis scenario

    :param quality_check_scenario: The parent quality check scenario
    :param cell_culture_state: The cell culture state
    :param load_scenario: The load scenario containing metadata_table output
    :param feature_extraction_scenario: The feature extraction scenario containing results_table
    :param medium_name_column: Column name containing medium names for coloring
    :param n_neighbors: Number of neighbors for UMAP
    :param min_dist: Minimum distance for UMAP
    :param metric: Distance metric for UMAP
    :param scale_data: Whether to scale data before UMAP
    :param n_clusters: Number of clusters for K-Means (optional)
    :param columns_to_exclude: List of column names to exclude from UMAP analysis
    :param hover_data_columns: List of column names to display as hover metadata
    :return: The created scenario or None if error
    """
    translate_service = cell_culture_state.get_translate_service()
    try:
        # Create a new scenario for Metadata Feature UMAP
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        scenario_proxy = ScenarioProxy(
            None,
            folder=quality_check_scenario.folder,
            title=f"Metadata Feature UMAP - {timestamp}",
            creation_type=ScenarioCreationType.MANUAL,
        )

        # Get the protocol
        protocol_proxy = scenario_proxy.get_protocol()

        # Get the metadata_table resource model from the quality check scenario output
        qc_scenario_proxy = ScenarioProxy.from_existing_scenario(quality_check_scenario.id)
        qc_protocol_proxy = qc_scenario_proxy.get_protocol()

        metadata_table_resource_model = qc_protocol_proxy.get_output_resource_model(
            cell_culture_state.QUALITY_CHECK_SCENARIO_METADATA_OUTPUT_NAME
        )

        if not metadata_table_resource_model:
            raise ValueError(
                translate_service.translate("metadata_feature_umap_metadata_output_unavailable")
            )

            # Get the results_table from feature extraction scenario
        fe_scenario_proxy = ScenarioProxy.from_existing_scenario(feature_extraction_scenario.id)
        fe_protocol_proxy = fe_scenario_proxy.get_protocol()

        results_table_resource_model = fe_protocol_proxy.get_output_resource_model("results_table")

        if not results_table_resource_model:
            raise ValueError(
                translate_service.translate("metadata_feature_umap_results_table_unavailable")
            )

            # Add input task for metadata_table
        metadata_input_task = protocol_proxy.add_process(
            InputTask,
            "metadata_table_input",
            {InputTask.config_name: metadata_table_resource_model.id},
        )

        # Add input task for results_table (features)
        features_input_task = protocol_proxy.add_process(
            InputTask,
            "features_table_input",
            {InputTask.config_name: results_table_resource_model.id},
        )

        # Add the Merge task (CellCultureMergeFeatureMetadata)
        merge_task = protocol_proxy.add_process(
            CellCultureMergeFeatureMetadata, "merge_feature_metadata_task"
        )

        # Connect inputs to merge task
        protocol_proxy.add_connector(
            out_port=features_input_task >> "resource", in_port=merge_task << "feature_table"
        )
        protocol_proxy.add_connector(
            out_port=metadata_input_task >> "resource", in_port=merge_task << "metadata_table"
        )

        # Add the Prepare task (CellCulturePrepareFeatureMetadataTable)
        prepare_task = protocol_proxy.add_process(
            CellCulturePrepareFeatureMetadataTable, "prepare_feature_metadata_task"
        )

        # Connect merge output to prepare task
        protocol_proxy.add_connector(
            out_port=merge_task >> "metadata_feature_table",
            in_port=prepare_task << "feature_metadata_table",
        )

        # Set prepare task parameters
        prepare_task.set_param("medium_name_column", medium_name_column)

        # Add the UMAP task
        umap_task = protocol_proxy.add_process(UMAPTask, "metadata_feature_umap_task")

        # Connect the prepared table to the UMAP task
        protocol_proxy.add_connector(
            out_port=prepare_task >> "ready_feature_metadata_table", in_port=umap_task << "data"
        )

        # Set UMAP parameters
        umap_task.set_param("n_neighbors", n_neighbors)
        umap_task.set_param("min_dist", min_dist)
        umap_task.set_param("metric", metric)
        umap_task.set_param("scale_data", scale_data)
        if n_clusters is not None:
            umap_task.set_param("n_clusters", n_clusters)
        if columns_to_exclude:
            umap_task.set_param("columns_to_exclude", columns_to_exclude)
        if hover_data_columns:
            umap_task.set_param("hover_data_columns", hover_data_columns)

            # Add outputs
        protocol_proxy.add_output("umap_2d_plot", umap_task >> "umap_2d_plot", flag_resource=True)
        protocol_proxy.add_output("umap_3d_plot", umap_task >> "umap_3d_plot", flag_resource=True)
        protocol_proxy.add_output("umap_2d_table", umap_task >> "umap_2d_table", flag_resource=True)
        protocol_proxy.add_output("umap_3d_table", umap_task >> "umap_3d_table", flag_resource=True)
        protocol_proxy.add_output(
            "merged_table", merge_task >> "metadata_feature_table", flag_resource=True
        )

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

        # Link to parent feature extraction scenario
        scenario_proxy.add_tag(
            Tag(
                "parent_feature_extraction_scenario",
                feature_extraction_scenario.id,
                is_propagable=False,
            )
        )

        # Add timestamp and analysis type tags
        scenario_proxy.add_tag(Tag("analysis_timestamp", timestamp, is_propagable=False))
        scenario_proxy.add_tag(Tag("analysis_type", "metadata_feature_umap", is_propagable=False))

        # Add to queue
        scenario_proxy.add_to_queue()
        st.toast(translate_service.translate("toast_scenario_launched"))

        # Return the new scenario
        new_scenario = scenario_proxy.get_model()
        return new_scenario

    except Exception as e:
        st.error(
            translate_service.translate("error_launching_scenario_generic").format(
                scenario_type="Metadata Feature UMAP", error=str(e)
            )
        )
        st.code(traceback.format_exc())
        return None


def render_metadata_feature_umap_step(
    recipe: CellCultureRecipe,
    cell_culture_state: CellCultureState,
    quality_check_scenario: Scenario,
    feature_extraction_scenario: Scenario,
) -> None:
    """
    Render the Metadata Feature UMAP analysis step

    :param recipe: The Recipe instance
    :param cell_culture_state: The cell culture state
    :param quality_check_scenario: The quality check scenario to analyze
    :param feature_extraction_scenario: The feature extraction scenario to use for analysis
    """
    translate_service = cell_culture_state.get_translate_service()

    # Info box with explanation
    with st.expander(
        translate_service.translate("help_title").format(
            analysis_type=translate_service.translate("umap_metadata_features")
        )
    ):
        st.markdown(f"### {translate_service.translate('what_is_this_analysis')}")
        st.markdown(
            f"""{translate_service.translate("metadata_feature_umap_help_intro")}

1. {translate_service.translate("metadata_feature_umap_help_metadata")}
2. {translate_service.translate("metadata_feature_umap_help_features")}

{translate_service.translate("metadata_feature_umap_help_projection")}

### {translate_service.translate("metadata_feature_umap_help_results_title")}

**{translate_service.translate("metadata_feature_umap_help_charts_title")}** :
- {translate_service.translate("metadata_feature_umap_help_chart_point")}
- {translate_service.translate("metadata_feature_umap_help_chart_color")}
- {translate_service.translate("metadata_feature_umap_help_chart_proximity")}
- {translate_service.translate("metadata_feature_umap_help_chart_groups")}

**{translate_service.translate("metadata_feature_umap_help_applications_title")}** :
- {translate_service.translate("metadata_feature_umap_help_app_similar")}
- {translate_service.translate("metadata_feature_umap_help_app_alternative")}
- {translate_service.translate("metadata_feature_umap_help_app_optimize")}
- {translate_service.translate("metadata_feature_umap_help_app_patterns")}

### {translate_service.translate("metadata_feature_umap_help_params_title")}

{translate_service.translate("metadata_feature_umap_help_params_intro")}
- {translate_service.translate("metadata_feature_umap_help_param_neighbors")}
- {translate_service.translate("metadata_feature_umap_help_param_dist")}
- {translate_service.translate("metadata_feature_umap_help_param_normalize")}
- {translate_service.translate("metadata_feature_umap_help_param_metric")}

### {translate_service.translate("metadata_feature_umap_help_clustering_title")}

{translate_service.translate("metadata_feature_umap_help_clustering_desc")}
- {translate_service.translate("metadata_feature_umap_help_clustering_segment")}
- {translate_service.translate("metadata_feature_umap_help_clustering_optimal")}
- {translate_service.translate("metadata_feature_umap_help_clustering_validate")}

### {translate_service.translate("metadata_feature_umap_help_advanced_title")}

**{translate_service.translate("metadata_feature_umap_help_exclude_title")}** :
- {translate_service.translate("metadata_feature_umap_help_exclude_desc")}
- {translate_service.translate("metadata_feature_umap_help_exclude_useful")}
- {translate_service.translate("metadata_feature_umap_help_exclude_ignored")}

**{translate_service.translate("metadata_feature_umap_help_hover_title")}** :
- {translate_service.translate("metadata_feature_umap_help_hover_desc")}
- {translate_service.translate("metadata_feature_umap_help_hover_useful")}
- {translate_service.translate("metadata_feature_umap_help_hover_display_only")}
"""
        )

    # Get the load scenario to check for metadata_table output
    load_scenario = recipe.get_load_scenario()

    if not load_scenario:
        st.warning(translate_service.translate("medium_umap_no_load_scenario"))
        return

    # Check if load scenario has metadata_table output
    try:
        load_scenario_proxy = ScenarioProxy.from_existing_scenario(load_scenario.id)
        load_protocol_proxy = load_scenario_proxy.get_protocol()

        metadata_table_resource_model = load_protocol_proxy.get_process(
            cell_culture_state.PROCESS_NAME_DATA_PROCESSING
        ).get_output_resource_model("metadata_table")

        if not metadata_table_resource_model:
            st.warning(translate_service.translate("metadata_table_unavailable_load"))
            return

    except Exception as e:
        st.warning(translate_service.translate("metadata_table_check_failed").format(error=str(e)))
        return

    # Get available series from metadata table
    try:
        metadata_table = metadata_table_resource_model.get_resource()
        metadata_df = metadata_table.get_data()

        if "Series" not in metadata_df.columns:
            st.error(f"⚠️ {translate_service.translate('series_column_missing')}")
            return

        available_series = sorted(metadata_df["Series"].unique().tolist())
        n_series = len(available_series)

        # Get available columns for medium name
        available_columns = sorted(metadata_df.columns.tolist())

        # Get feature extraction results to know all columns that will be in merged table
        fe_scenario_proxy = ScenarioProxy.from_existing_scenario(feature_extraction_scenario.id)
        fe_protocol_proxy = fe_scenario_proxy.get_protocol()
        results_table_resource_model = fe_protocol_proxy.get_output_resource_model("results_table")

        if results_table_resource_model:
            results_table = results_table_resource_model.get_resource()
            results_df = results_table.get_data()
            # Get all columns from both tables (excluding 'Series' which is the merge key)
            all_merged_columns = sorted(
                set(metadata_df.columns.tolist() + results_df.columns.tolist())
            )
        else:
            # Fallback to metadata columns only
            all_merged_columns = available_columns

        # Default to 'Medium' if exists, otherwise first non-Series column
        default_medium_column = (
            "Medium"
            if "Medium" in available_columns
            else (
                [col for col in available_columns if col != "Series"][0]
                if len(available_columns) > 1
                else "Medium"
            )
        )

        # Check minimum number of data columns (excluding Series and Medium columns)
        data_columns_for_analysis = [
            col
            for col in all_merged_columns
            if col not in ["Series", "Medium", default_medium_column]
        ]
        data_columns_count = len(data_columns_for_analysis)
        if data_columns_count < 2:
            st.warning(translate_service.translate("min_columns_required_for_analysis"))

    except Exception as e:
        st.error(translate_service.translate("error_reading_metadata").format(error=str(e)))
        return

    # Check existing UMAP scenarios for this feature extraction
    existing_metadata_umap_scenarios = (
        recipe.get_metadata_feature_umap_scenarios_for_feature_extraction(
            feature_extraction_scenario.id
        )
    )
    render_launched_scenarios_expander(
        scenarios=existing_metadata_umap_scenarios,
        nav_key_prefix="metadata_feature_umap_result_",
        title_prefix="Metadata Feature UMAP - ",
        translate_service=translate_service,
    )

    # Configuration form for new UMAP
    st.markdown("---")
    st.markdown(f"### ➕ {translate_service.translate('launch_new_umap_analysis')}")

    with st.form(key=f"metadata_feature_umap_form_{quality_check_scenario.id}"):
        st.markdown(f"**{translate_service.translate('analysis_configuration')}**")

        # Medium column selection
        medium_name_column = st.selectbox(
            translate_service.translate("medium_column_label"),
            options=available_columns,
            index=available_columns.index(default_medium_column)
            if default_medium_column in available_columns
            else 0,
            help=translate_service.translate("medium_name_column_help"),
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
            translate_service.translate("enable_clustering"), value=False
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

        st.markdown(f"**{translate_service.translate('advanced_options')}**")

        # Columns to exclude
        columns_to_exclude = st.multiselect(
            translate_service.translate("columns_to_exclude_label"),
            options=all_merged_columns,
            default=[medium_name_column] if medium_name_column in all_merged_columns else [],
            help=translate_service.translate("columns_to_exclude_help"),
        )
        # Convert empty list to None
        if not columns_to_exclude:
            columns_to_exclude = None

        # Hover data columns
        hover_data_columns = st.multiselect(
            translate_service.translate("hover_columns_label"),
            options=all_merged_columns,
            default=None,
            help=translate_service.translate("hover_data_help"),
        )
        # Convert empty list to None
        if not hover_data_columns:
            hover_data_columns = None

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
            # Launch UMAP scenario
            umap_scenario = launch_metadata_feature_umap_scenario(
                quality_check_scenario,
                cell_culture_state,
                load_scenario,
                feature_extraction_scenario,
                medium_name_column,
                n_neighbors,
                min_dist,
                metric,
                scale_data,
                n_clusters,
                columns_to_exclude,
                hover_data_columns,
            )

            if umap_scenario:
                st.success(translate_service.translate("umap_launched_success"))
                st.info(translate_service.translate("analysis_running"))

                # Add to recipe
                recipe.add_metadata_feature_umap_scenario(
                    feature_extraction_scenario.id, umap_scenario
                )

                st.rerun()
            else:
                st.error(translate_service.translate("umap_launch_error"))
