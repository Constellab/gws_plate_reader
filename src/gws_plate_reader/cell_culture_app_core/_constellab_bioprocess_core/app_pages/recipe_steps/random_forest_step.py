"""
Random Forest Regression Analysis Step for Cell Culture Dashboard
Allows users to run Random Forest regression analysis on combined metadata and feature extraction data
"""

import traceback
from datetime import datetime

import streamlit as st
from gws_core import InputTask, Scenario, ScenarioCreationType, ScenarioProxy, Tag
from gws_core.tag.entity_tag_list import EntityTagList
from gws_core.tag.tag_entity_type import TagEntityType
from gws_design_of_experiments.random_forest.random_forest_task import RandomForestRegressorTask
from gws_plate_reader.cell_culture_app_core._constellab_bioprocess_core.cell_culture_recipe import (
    CellCultureRecipe,
)
from gws_plate_reader.cell_culture_app_core._constellab_bioprocess_core.cell_culture_state import (
    CellCultureState,
)
from gws_plate_reader.cell_culture_app_core._constellab_bioprocess_core.functions_steps import (
    render_launched_scenarios_expander,
)
from gws_plate_reader.cell_culture_filter import CellCultureMergeFeatureMetadata


def launch_random_forest_scenario(
    quality_check_scenario: Scenario,
    cell_culture_state: CellCultureState,
    feature_extraction_scenario: Scenario,
    target_column: str,
    columns_to_exclude: list[str] | None,
    test_size: float,
) -> Scenario | None:
    """
    Launch a Random Forest Regression analysis scenario

    :param quality_check_scenario: The parent quality check scenario
    :param cell_culture_state: The cell culture state
    :param load_scenario: The load scenario containing metadata_table output
    :param feature_extraction_scenario: The feature extraction scenario containing results_table
    :param target_column: Target column name to predict
    :param columns_to_exclude: List of column names to exclude from Random Forest analysis
    :param test_size: Proportion of data for testing (0.0 to 1.0)
    :return: The created scenario or None if error
    """
    translate_service = cell_culture_state.get_translate_service()
    try:
        # Create a new scenario for Random Forest Regression
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        scenario_proxy = ScenarioProxy(
            None,
            folder=quality_check_scenario.folder,
            title=f"Random Forest Regression - {timestamp}",
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
            raise ValueError(translate_service.translate("rf_metadata_output_unavailable"))

            # Get the results_table from feature extraction scenario
        fe_scenario_proxy = ScenarioProxy.from_existing_scenario(feature_extraction_scenario.id)
        fe_protocol_proxy = fe_scenario_proxy.get_protocol()

        results_table_resource_model = fe_protocol_proxy.get_output_resource_model("results_table")

        if not results_table_resource_model:
            raise ValueError(translate_service.translate("rf_results_table_unavailable"))

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

        # Add the Random Forest Regression task
        rf_task = protocol_proxy.add_process(
            RandomForestRegressorTask, "random_forest_regression_task"
        )

        # Connect the merged table to the Random Forest task
        protocol_proxy.add_connector(
            out_port=merge_task >> "metadata_feature_table", in_port=rf_task << "data"
        )

        # Set Random Forest parameters
        rf_task.set_param("target", target_column)
        rf_task.set_param("test_size", test_size)
        if columns_to_exclude:
            rf_task.set_param("columns_to_exclude", columns_to_exclude)

            # Add outputs
        protocol_proxy.add_output("summary_table", rf_task >> "summary_table", flag_resource=True)
        protocol_proxy.add_output("vip_table", rf_task >> "vip_table", flag_resource=True)
        protocol_proxy.add_output(
            "plot_estimators", rf_task >> "plot_estimators", flag_resource=True
        )
        protocol_proxy.add_output("vip_plot", rf_task >> "vip_plot", flag_resource=True)
        protocol_proxy.add_output("plot_train_set", rf_task >> "plot_train_set", flag_resource=True)
        protocol_proxy.add_output("plot_test_set", rf_task >> "plot_test_set", flag_resource=True)
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
        scenario_proxy.add_tag(
            Tag("analysis_type", "random_forest_regression", is_propagable=False)
        )

        # Add to queue
        scenario_proxy.add_to_queue()
        st.toast(translate_service.translate("toast_scenario_launched"))

        # Return the new scenario
        new_scenario = scenario_proxy.get_model()
        return new_scenario

    except Exception as e:
        translate_service = cell_culture_state.get_translate_service()
        st.error(translate_service.translate("error_launching_random_forest").format(error=str(e)))
        st.code(traceback.format_exc())
        return None


def render_random_forest_step(
    recipe: CellCultureRecipe,
    cell_culture_state: CellCultureState,
    quality_check_scenario: Scenario,
    feature_extraction_scenario: Scenario,
) -> None:
    """
    Render the Random Forest Regression analysis step

    :param recipe: The Recipe instance
    :param cell_culture_state: The cell culture state
    :param quality_check_scenario: The quality check scenario to analyze
    :param feature_extraction_scenario: The feature extraction scenario to use for analysis
    """
    translate_service = cell_culture_state.get_translate_service()

    # Info box with explanation
    with st.expander(
        translate_service.translate("help_title").format(analysis_type="Random Forest Regression")
    ):
        st.markdown(translate_service.translate("rf_help_content"))

    # Get load scenario from recipe
    load_scenario = recipe.get_load_scenario()

    if not load_scenario:
        st.error(f"{translate_service.translate('load_scenario_not_found')}")
        return

    # Display selected feature extraction scenario

    # Get available columns from merged table (metadata + features)
    try:
        # Get metadata table from load scenario
        load_scenario_proxy = ScenarioProxy.from_existing_scenario(load_scenario.id)
        load_protocol_proxy = load_scenario_proxy.get_protocol()
        metadata_table_resource_model = load_protocol_proxy.get_process(
            cell_culture_state.PROCESS_NAME_DATA_PROCESSING
        ).get_output_resource_model("metadata_table")

        if not metadata_table_resource_model:
            st.error(translate_service.translate("metadata_table_unavailable"))
            return

        metadata_table = metadata_table_resource_model.get_resource()
        metadata_df = metadata_table.get_data()

        if "Series" not in metadata_df.columns:
            st.error(f"⚠️ {translate_service.translate('series_column_missing')}")
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
        st.error(translate_service.translate("error_reading_tables").format(error=str(e)))
        st.code(traceback.format_exc())
        return

    # Show existing Random Forest scenarios for this feature extraction
    existing_rf_scenarios = recipe.get_random_forest_scenarios_for_feature_extraction(
        feature_extraction_scenario.id
    )
    render_launched_scenarios_expander(
        scenarios=existing_rf_scenarios,
        nav_key_prefix="random_forest_result_",
        title_prefix="Random Forest Regression - ",
        translate_service=translate_service,
    )

    # Configuration form for new Random Forest
    st.markdown("---")
    st.markdown(
        f"### {translate_service.translate('create_new_analysis').format(analysis_type='Random Forest')}"
    )

    st.markdown(f"**{translate_service.translate('analysis_configuration')}**")

    # Filter target options: only allowed feature extraction columns + base metadata columns
    allowed_feature_columns = {"param_A", "param_lag", "param_mu", "param_y0", "t50", "t95"}
    allowed_target_columns = sorted(
        col for col in all_numeric_columns
        if col not in feature_extraction_columns or col in allowed_feature_columns
    )

    # Target column selection (must select exactly one)
    target_column = st.selectbox(
        translate_service.translate("target_variables_label"),
        options=allowed_target_columns,
        index=None,
        key=f"rf_target_column_{quality_check_scenario.id}_{feature_extraction_scenario.id}",
        help=translate_service.translate("target_variables_help"),
    )

    st.markdown(f"**{translate_service.translate('model_parameters')}**")

    test_size = st.slider(
        translate_service.translate("test_size_label"),
        min_value=0.1,
        max_value=0.5,
        value=0.2,
        step=0.05,
        key=f"rf_test_size_{quality_check_scenario.id}_{feature_extraction_scenario.id}",
        help=translate_service.translate("test_size_help"),
    )

    # Auto-compute columns to exclude (not user-editable):
    # 1. All non-numeric columns
    # 2. All feature extraction columns (except the target if it's from features)
    columns_to_exclude = sorted(
        set(all_non_numeric_columns)
        | {col for col in feature_extraction_columns if col != target_column}
    )
    # Convert empty list to None
    if not columns_to_exclude:
        columns_to_exclude = None

    # Submit button
    if st.button(
        translate_service.translate("launch_analysis_button_with_type").format(
            analysis_type="Random Forest"
        ),
        type="primary",
        key=f"rf_submit_{quality_check_scenario.id}_{feature_extraction_scenario.id}",
        width="stretch",
        disabled=cell_culture_state.get_is_standalone(),
    ):
        if not target_column:
            st.error(translate_service.translate("select_target_first"))
        else:
            # Launch Random Forest scenario
            rf_scenario = launch_random_forest_scenario(
                quality_check_scenario,
                cell_culture_state,
                feature_extraction_scenario,
                target_column,
                columns_to_exclude,
                test_size,
            )

            if rf_scenario:
                st.success(
                    translate_service.translate("analysis_launched_success").format(
                        analysis_type="Random Forest"
                    )
                )
                st.info(translate_service.translate("analysis_running"))

                # Add to recipe
                recipe.add_random_forest_scenario(feature_extraction_scenario.id, rf_scenario)

                st.rerun()
            else:
                st.error(
                    translate_service.translate("analysis_launch_error").format(
                        analysis_type="Random Forest"
                    )
                )

    if cell_culture_state.get_is_standalone():
        st.info(translate_service.translate("standalone_mode_function_blocked"))

    # Info box with explanation
    with st.expander(
        translate_service.translate("help_title").format(analysis_type="Random Forest Regression")
    ):
        st.markdown(translate_service.translate("rf_help_content"))
