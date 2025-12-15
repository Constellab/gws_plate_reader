"""
Feature Extraction Step for Cell Culture Dashboard
Allows users to run growth curve feature extraction analysis on quality check data
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
from gws_plate_reader.cell_culture_analysis import ResourceSetToDataTable, CellCultureFeatureExtraction


def get_available_columns_from_quality_check(quality_check_scenario: Scenario,
                                             cell_culture_state: CellCultureState,
                                             index_only: bool = False) -> List[str]:
    """
    Get list of available columns from the quality check scenario's output

    :param quality_check_scenario: The quality check scenario
    :param cell_culture_state: The cell culture state
    :param index_only: If True, return only columns with is_index_column=true tag (strict filtering)
    :return: List of column names
    """
    try:
        # Get the ResourceSet from quality check (non-interpolated data)
        resource_set_resource_model = cell_culture_state.get_quality_check_scenario_output_resource_model(
            quality_check_scenario)
        resource_set = resource_set_resource_model.get_resource() if resource_set_resource_model else None

        if not resource_set:
            return []

        # Get columns based on filter
        if index_only:
            # Use strict filtering for index columns (only is_index_column=true)
            return cell_culture_state.get_strict_index_columns_from_resource_set(resource_set)
        else:
            return cell_culture_state.get_data_columns_from_resource_set(resource_set)

    except Exception as e:
        st.error(f"Erreur lors de l'extraction des colonnes : {str(e)}")
        return []


def launch_feature_extraction_scenario(
        quality_check_scenario: Scenario,
        cell_culture_state: CellCultureState,
        index_column: str,
        data_column: str,
        models_to_fit: List[str]) -> Optional[Scenario]:
    """
    Launch a Feature Extraction analysis scenario

    :param quality_check_scenario: The parent quality check scenario
    :param cell_culture_state: The cell culture state
    :param index_column: Column to use as index (time/temp)
    :param data_column: Data column to analyze
    :param models_to_fit: List of models to fit
    :return: The created scenario or None if error
    """
    translate_service = cell_culture_state.get_translate_service()
    try:
        with StreamlitAuthenticateUser():
            # Create a new scenario for Feature Extraction
            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            scenario_title = f"Feature Extraction - {data_column} - {timestamp}"

            scenario_proxy = ScenarioProxy(
                None,
                folder=quality_check_scenario.folder,
                title=scenario_title,
                creation_type=ScenarioCreationType.MANUAL,
            )

            # Get the protocol
            protocol_proxy = scenario_proxy.get_protocol()

            # Get the quality check output ResourceSet
            qc_output = cell_culture_state.get_quality_check_scenario_output_resource_model(quality_check_scenario)
            if not qc_output:
                st.error(translate_service.translate('unable_retrieve_qc_output'))
                return None

            # Add input task for the ResourceSet
            resource_set_input_task = protocol_proxy.add_process(
                InputTask, 'resource_set_input',
                {InputTask.config_name: qc_output.id}
            )

            # Add ResourceSetToDataTable task
            rs_to_table_task = protocol_proxy.add_process(
                ResourceSetToDataTable,
                'resource_set_to_table'
            )

            # Connect ResourceSet to converter task
            protocol_proxy.add_connector(
                out_port=resource_set_input_task >> 'resource',
                in_port=rs_to_table_task << 'resource_set'
            )

            # Set converter parameters
            rs_to_table_task.set_param('index_column', index_column)
            rs_to_table_task.set_param('data_column', data_column)

            # Add Feature Extraction task
            feature_extraction_task = protocol_proxy.add_process(
                CellCultureFeatureExtraction,
                'feature_extraction_task'
            )

            # Connect table to feature extraction
            protocol_proxy.add_connector(
                out_port=rs_to_table_task >> 'data_table',
                in_port=feature_extraction_task << 'data_table'
            )

            # Set feature extraction parameters
            feature_extraction_task.set_param('models_to_fit', models_to_fit)

            # Add outputs
            protocol_proxy.add_output(
                'results_table',
                feature_extraction_task >> 'results_table',
                flag_resource=True
            )
            protocol_proxy.add_output(
                'plots',
                feature_extraction_task >> 'plots',
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

            # Add analysis type and column tags
            scenario_proxy.add_tag(Tag("analysis_type", "feature_extraction", is_propagable=False))
            scenario_proxy.add_tag(Tag("analysis_timestamp", timestamp, is_propagable=False))
            scenario_proxy.add_tag(Tag("data_column", data_column, is_propagable=False))
            scenario_proxy.add_tag(Tag("index_column", index_column, is_propagable=False))

            # Add to queue
            scenario_proxy.add_to_queue()

            # Return the new scenario
            new_scenario = scenario_proxy.get_model()
            return new_scenario

    except Exception as e:
        st.error(translate_service.translate('error_launching_scenario_generic').format(
            scenario_type='Feature Extraction', error=str(e)))
        import traceback
        st.code(traceback.format_exc())
        return None


def render_feature_extraction_step(recipe: CellCultureRecipe, cell_culture_state: CellCultureState,
                                   quality_check_scenario: Scenario) -> None:
    """
    Render the Feature Extraction analysis step

    :param recipe: The Recipe instance
    :param cell_culture_state: The cell culture state
    :param quality_check_scenario: The quality check scenario to analyze
    """
    translate_service = cell_culture_state.get_translate_service()

    st.markdown(f"### 📈 {translate_service.translate('feature_extraction_title')}")

    st.info(translate_service.translate('feature_extraction_info_intro'))

    # Get the quality check output
    qc_output = cell_culture_state.get_quality_check_scenario_output_resource_model(quality_check_scenario)
    qc_output_resource_set = qc_output.get_resource() if qc_output else None

    if not qc_output_resource_set:
        st.warning(translate_service.translate('cannot_retrieve_qc_data'))
        return

    st.success(f"✅ {len(qc_output_resource_set.get_resources())} {translate_service.translate('resources')}")

    # Get available columns
    index_columns = get_available_columns_from_quality_check(
        quality_check_scenario, cell_culture_state, index_only=True)
    data_columns = get_available_columns_from_quality_check(
        quality_check_scenario, cell_culture_state, index_only=False)

    if not index_columns:
        st.warning(translate_service.translate('no_index_columns_found'))
        return

    if not data_columns:
        st.warning(translate_service.translate('no_data_columns_found'))
        return

    st.markdown(f"**{translate_service.translate('column_selection')}** : {', '.join(index_columns)}")
    st.markdown(f"**{translate_service.translate('data_column_selection')}** : {', '.join(data_columns)}")

    # Check existing feature extraction scenarios
    existing_fe_scenarios = recipe.get_feature_extraction_scenarios_for_quality_check(quality_check_scenario.id)

    if existing_fe_scenarios:
        st.markdown(f"**{translate_service.translate('feature_extraction_existing_analyses')}** : {len(existing_fe_scenarios)}")
        with st.expander(f"📊 {translate_service.translate('view_button')} {translate_service.translate('feature_extraction_existing_analyses').lower()}"):
            for idx, fe_scenario in enumerate(existing_fe_scenarios):
                # Extract data column from tags
                entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, fe_scenario.id)
                data_col_tags = entity_tag_list.get_tags_by_key("data_column")
                data_col = data_col_tags[0].tag_value if data_col_tags else "N/A"

                st.write(f"{idx + 1}. {fe_scenario.title} - {translate_service.translate('column_label')}: **{data_col}** ({translate_service.translate('status')}: {fe_scenario.status.name})")

    # Configuration form for new Feature Extraction
    st.markdown("---")
    st.markdown(f"### ➕ {translate_service.translate('feature_extraction_launch_button')}")

    # Available models
    all_models = [
        "Logistic_4P",
        "Gompertz_4P",
        "ModifiedGompertz_4P",
        "Richards_5P",
        "WeibullSigmoid_4P",
        "BaranyiRoberts_4P"
    ]

    with st.form(key=f"feature_extraction_form_{quality_check_scenario.id}"):
        st.markdown(f"**{translate_service.translate('feature_extraction_analysis_config')}**")

        # Index column selection
        index_column = st.selectbox(
            translate_service.translate('feature_extraction_time_column'),
            options=index_columns,
            index=0,
            help=translate_service.translate('feature_extraction_time_column_help')
        )

        # Data columns multiselect
        selected_data_columns = st.multiselect(
            translate_service.translate('feature_extraction_data_column'),
            options=data_columns,
            default=[],
            help=translate_service.translate('feature_extraction_data_column_help')
        )

        # Models multiselect
        selected_models = st.multiselect(
            translate_service.translate('feature_extraction_model_selection'),
            options=all_models,
            default=["Logistic_4P"],
            help=translate_service.translate('feature_extraction_model_help')
        )

        # Info about multiple columns
        if len(selected_data_columns) > 1:
            st.info(translate_service.translate('feature_extraction_multi_scenario_info'))

        # Submit button
        submit_button = st.form_submit_button(
            f"🚀 {translate_service.translate('feature_extraction_launch_button')}",
            type="primary",
            width='stretch'
        )

        if submit_button:
            if not selected_data_columns:
                st.error(translate_service.translate('feature_extraction_column_warning'))
            elif not selected_models:
                st.error(translate_service.translate('feature_extraction_column_warning'))
            else:
                # Launch scenarios
                created_scenarios = []

                progress_bar = st.progress(0, text=translate_service.translate('launching'))

                for idx, data_column in enumerate(selected_data_columns):
                    progress = (idx + 1) / len(selected_data_columns)
                    progress_bar.progress(progress, text=f"{translate_service.translate('launching')} {data_column}...")

                    fe_scenario = launch_feature_extraction_scenario(
                        quality_check_scenario,
                        cell_culture_state,
                        index_column,
                        data_column,
                        selected_models
                    )

                    if fe_scenario:
                        created_scenarios.append(fe_scenario)
                        # Add to recipe
                        recipe.add_feature_extraction_scenario(quality_check_scenario.id, fe_scenario)

                progress_bar.empty()

                if created_scenarios:
                    st.success(translate_service.translate('feature_extraction_launched_success'))
                    st.info(translate_service.translate('analysis_running'))
                    st.rerun()
                else:
                    st.error(translate_service.translate('feature_extraction_error_launching'))

    # Info box with Feature Extraction explanation
    with st.expander(f"💡 {translate_service.translate('about_feature_extraction')}"):
        st.markdown(translate_service.translate('feature_extraction_help_content'))
