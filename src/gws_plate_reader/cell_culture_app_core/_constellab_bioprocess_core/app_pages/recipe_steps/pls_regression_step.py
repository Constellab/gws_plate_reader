"""
PLS Regression Analysis Step for Cell Culture Dashboard
Allows users to run PLS regression analysis on combined metadata and feature extraction data
"""

import traceback
from datetime import datetime

import streamlit as st
from gws_core import InputTask, Scenario, ScenarioCreationType, ScenarioProxy, Tag
from gws_core.tag.entity_tag_list import EntityTagList
from gws_core.tag.tag_entity_type import TagEntityType
from gws_design_of_experiments.pls.pls_regression_task import PLSRegressorTask

from gws_plate_reader.cell_culture_app_core._constellab_bioprocess_core.cell_culture_recipe import (
    CellCultureRecipe,
)
from gws_plate_reader.cell_culture_app_core._constellab_bioprocess_core.cell_culture_state import (
    CellCultureState,
)
from gws_plate_reader.cell_culture_filter import CellCultureMergeFeatureMetadata


def launch_pls_regression_scenario(
    quality_check_scenario: Scenario,
    cell_culture_state: CellCultureState,
    feature_extraction_scenario: Scenario,
    target_columns: list[str],
    columns_to_exclude: list[str] | None,
    scale_data: bool,
    test_size: float,
) -> Scenario | None:
    """
    Launch a PLS Regression analysis scenario

    :param quality_check_scenario: The parent quality check scenario
    :param cell_culture_state: The cell culture state
    :param load_scenario: The load scenario containing metadata_table output
    :param feature_extraction_scenario: The feature extraction scenario containing results_table
    :param target_columns: List of target column names to predict
    :param columns_to_exclude: List of column names to exclude from PLS analysis
    :param scale_data: Whether to scale data before PLS
    :param test_size: Proportion of data for testing (0.0 to 1.0)
    :return: The created scenario or None if error
    """
    translate_service = cell_culture_state.get_translate_service()
    try:
        # Create a new scenario for PLS Regression
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        scenario_proxy = ScenarioProxy(
            None,
            folder=quality_check_scenario.folder,
            title=f"PLS Regression - {timestamp}",
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
            raise ValueError(translate_service.translate("pls_metadata_output_unavailable"))

            # Get the results_table from feature extraction scenario
        fe_scenario_proxy = ScenarioProxy.from_existing_scenario(feature_extraction_scenario.id)
        fe_protocol_proxy = fe_scenario_proxy.get_protocol()

        results_table_resource_model = fe_protocol_proxy.get_output_resource_model("results_table")

        if not results_table_resource_model:
            raise ValueError(translate_service.translate("pls_results_table_unavailable"))

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

        # Add the PLS Regression task
        pls_task = protocol_proxy.add_process(PLSRegressorTask, "pls_regression_task")

        # Connect the merged table to the PLS task
        protocol_proxy.add_connector(
            out_port=merge_task >> "metadata_feature_table", in_port=pls_task << "data"
        )

        # Set PLS parameters
        pls_task.set_param("target", target_columns)
        pls_task.set_param("scale_data", scale_data)
        pls_task.set_param("test_size", test_size)
        if columns_to_exclude:
            pls_task.set_param("columns_to_exclude", columns_to_exclude)

            # Add outputs
        protocol_proxy.add_output("summary_table", pls_task >> "summary_table", flag_resource=True)
        protocol_proxy.add_output("vip_table", pls_task >> "vip_table", flag_resource=True)
        protocol_proxy.add_output(
            "plot_components", pls_task >> "plot_components", flag_resource=True
        )
        protocol_proxy.add_output("vip_plot", pls_task >> "vip_plot", flag_resource=True)
        protocol_proxy.add_output(
            "plot_train_set", pls_task >> "plot_train_set", flag_resource=True
        )
        protocol_proxy.add_output("plot_test_set", pls_task >> "plot_test_set", flag_resource=True)
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
        scenario_proxy.add_tag(Tag("analysis_type", "pls_regression", is_propagable=False))

        # Add to queue
        scenario_proxy.add_to_queue()
        st.toast(translate_service.translate("toast_scenario_launched"))

        # Return the new scenario
        new_scenario = scenario_proxy.get_model()
        return new_scenario

    except Exception as e:
        st.error(
            f"{translate_service.translate('error_launching_scenario_analyse').format(analysis_type='PLS Regression')}: {str(e)}"
        )
        st.code(traceback.format_exc())
        return None


def render_pls_regression_step(
    recipe: CellCultureRecipe,
    cell_culture_state: CellCultureState,
    quality_check_scenario: Scenario,
    feature_extraction_scenario: Scenario,
) -> None:
    """
    Render the PLS Regression analysis step

    :param recipe: The Recipe instance
    :param cell_culture_state: The cell culture state
    :param quality_check_scenario: The quality check scenario to analyze
    :param feature_extraction_scenario: The feature extraction scenario to use for analysis
    """
    translate_service = cell_culture_state.get_translate_service()

    # Info box with explanation
    with st.expander(
        translate_service.translate("help_title").format(analysis_type="PLS Regression")
    ):
        st.markdown(translate_service.translate("pls_help_content"))

    # Display selected feature extraction scenario
    st.info(
        f"📊 {translate_service.translate('feature_extraction_scenario_label')} : **{feature_extraction_scenario.title}**"
    )

    # Get the load scenario to check for metadata_table output
    load_scenario = recipe.get_load_scenario()

    if not load_scenario:
        st.warning(translate_service.translate("no_load_scenario"))
        return

    # Check if load scenario has metadata_table output
    try:
        load_scenario_proxy = ScenarioProxy.from_existing_scenario(load_scenario.id)
        load_protocol_proxy = load_scenario_proxy.get_protocol()

        metadata_table_resource_model = load_protocol_proxy.get_process(
            cell_culture_state.PROCESS_NAME_DATA_PROCESSING
        ).get_output_resource_model("metadata_table")

        if not metadata_table_resource_model:
            st.warning(translate_service.translate("metadata_table_unavailable"))
            return

        st.success(
            f"{translate_service.translate('metadata_table_available')} : {metadata_table_resource_model.name}"
        )
    except Exception as e:
        st.warning(f"Cannot verify metadata table: {str(e)}")
        return

    # Get available columns from merged table (metadata + features)
    try:
        metadata_table = metadata_table_resource_model.get_resource()
        metadata_df = metadata_table.get_data()

        if "Series" not in metadata_df.columns:
            st.error(translate_service.translate("series_column_missing"))
            return

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

            # Identify feature extraction columns
            feature_extraction_columns = sorted(results_df.columns.tolist())

            # Separate numeric and non-numeric columns
            metadata_numeric_cols = metadata_df.select_dtypes(include=["number"]).columns.tolist()
            results_numeric_cols = results_df.select_dtypes(include=["number"]).columns.tolist()
            all_numeric_columns = sorted(set(metadata_numeric_cols + results_numeric_cols))

            # Calculate non-numeric columns to exclude by default
            all_non_numeric_columns = sorted(set(all_merged_columns) - set(all_numeric_columns))
        else:
            # Fallback to metadata columns only
            all_merged_columns = sorted(metadata_df.columns.tolist())
            all_numeric_columns = sorted(
                metadata_df.select_dtypes(include=["number"]).columns.tolist()
            )
            feature_extraction_columns = []

            # Calculate non-numeric columns to exclude by default
            all_non_numeric_columns = sorted(set(all_merged_columns) - set(all_numeric_columns))

    except Exception as e:
        st.error(f"Error reading tables: {str(e)}")
        st.code(traceback.format_exc())
        return

    # Check existing PLS scenarios for this feature extraction
    recipe.get_pls_regression_scenarios_for_feature_extraction(feature_extraction_scenario.id)

    # Configuration form for new PLS
    st.markdown("---")
    st.markdown(
        f"### ➕ {translate_service.translate('create_new_analysis').format(analysis_type='PLS')}"
    )

    st.markdown("**Analysis Configuration**")

    # Target columns selection (must select at least one)
    target_columns = st.multiselect(
        translate_service.translate("target_variables_label"),
        options=all_numeric_columns,
        default=[],
        key=f"pls_target_columns_{quality_check_scenario.id}_{feature_extraction_scenario.id}",
        help=translate_service.translate("target_variables_help"),
    )

    st.markdown("**Model Parameters**")

    col1, col2 = st.columns(2)

    with col1:
        scale_data = st.checkbox(
            translate_service.translate("normalize_data_label"),
            value=True,
            key=f"pls_scale_data_{quality_check_scenario.id}_{feature_extraction_scenario.id}",
            help=translate_service.translate("normalize_data_help"),
        )

    with col2:
        test_size = st.slider(
            translate_service.translate("test_size_label"),
            min_value=0.1,
            max_value=0.5,
            value=0.2,
            step=0.05,
            key=f"pls_test_size_{quality_check_scenario.id}_{feature_extraction_scenario.id}",
            help=translate_service.translate("test_size_help"),
        )

    st.markdown("**Advanced Options**")

    # Calculate default columns to exclude:
    # 1. All non-numeric columns
    # 2. All feature extraction columns (except those selected as targets)
    default_excluded = sorted(
        set(all_non_numeric_columns)
        | {col for col in feature_extraction_columns if col not in target_columns}
    )

    # Columns to exclude
    columns_to_exclude = st.multiselect(
        translate_service.translate("columns_to_exclude_label"),
        options=[col for col in all_merged_columns if col not in target_columns],
        default=default_excluded,
        key=f"pls_columns_exclude_{quality_check_scenario.id}_{feature_extraction_scenario.id}",
        help=translate_service.translate("columns_to_exclude_help"),
    )
    # Convert empty list to None
    if not columns_to_exclude:
        columns_to_exclude = None

    # Submit button
    if st.button(
        translate_service.translate("launch_analysis_button_with_type").format(analysis_type="PLS"),
        type="primary",
        key=f"pls_submit_{quality_check_scenario.id}_{feature_extraction_scenario.id}",
        width="stretch",
        disabled=cell_culture_state.get_is_standalone(),
    ):
        if len(target_columns) == 0:
            st.error(translate_service.translate("select_target_first"))
        else:
            # Launch PLS scenario
            pls_scenario = launch_pls_regression_scenario(
                quality_check_scenario,
                cell_culture_state,
                feature_extraction_scenario,
                target_columns,
                columns_to_exclude,
                scale_data,
                test_size,
            )

            if pls_scenario:
                st.success(
                    translate_service.translate("analysis_launched_success").format(
                        analysis_type="PLS"
                    )
                )
                st.info(translate_service.translate("analysis_running"))

                # Add to recipe
                recipe.add_pls_regression_scenario(feature_extraction_scenario.id, pls_scenario)

                st.rerun()
            else:
                st.error(
                    translate_service.translate("analysis_launch_error").format(analysis_type="PLS")
                )

    if cell_culture_state.get_is_standalone():
        st.info(translate_service.translate("standalone_mode_function_blocked"))
