"""
Logistic Growth Analysis Step for Cell Culture Dashboard
Allows users to run logistic growth curve fitting with cross-validation
"""
import streamlit as st
from typing import Optional
from datetime import datetime

from gws_core import Scenario, ScenarioProxy, ScenarioCreationType, InputTask, Tag
from gws_core.tag.tag_entity_type import TagEntityType
from gws_core.tag.entity_tag_list import EntityTagList
from gws_core.streamlit import StreamlitAuthenticateUser
from gws_plate_reader.cell_culture_app_core.cell_culture_state import CellCultureState
from gws_plate_reader.cell_culture_app_core.cell_culture_recipe import CellCultureRecipe
from gws_plate_reader.features_extraction.logistic_growth_fitter import LogisticGrowthFitter
from gws_plate_reader.fermentalg_analysis import ResourceSetToDataTable


def launch_logistic_growth_scenario(
        quality_check_scenario: Scenario,
        cell_culture_state: CellCultureState,
        index_column: str,
        data_column: str,
        n_splits: int = 3,
        spline_smoothing: float = 0.045) -> Optional[Scenario]:
    """
    Launch a Logistic Growth Fitting scenario

    :param quality_check_scenario: The parent quality check scenario
    :param cell_culture_state: The cell culture state
    :param index_column: Column to use as index (time/temperature)
    :param data_column: Data column to analyze
    :param n_splits: Number of K-Fold cross-validation splits
    :param spline_smoothing: Smoothing parameter for spline preprocessing
    :return: The created scenario or None if error
    """
    try:
        with StreamlitAuthenticateUser():
            # Create a new scenario
            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            scenario_title = f"Logistic Growth - {data_column} - {timestamp}"

            scenario_proxy = ScenarioProxy(
                None,
                folder=quality_check_scenario.folder,
                title=scenario_title,
                creation_type=ScenarioCreationType.MANUAL,
            )

            # Get the protocol
            protocol_proxy = scenario_proxy.get_protocol()

            # Get the quality check interpolated output ResourceSet
            qc_output = cell_culture_state.get_quality_check_scenario_interpolated_output_resource_model(
                quality_check_scenario)
            if not qc_output:
                st.error("Impossible de récupérer le ResourceSet interpolé de sortie du Quality Check")
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

            # Set converter parameters with user-selected columns
            rs_to_table_task.set_param('index_column', index_column)
            rs_to_table_task.set_param('data_column', data_column)            # Add Logistic Growth Fitter task
            logistic_fitter_task = protocol_proxy.add_process(
                LogisticGrowthFitter,
                'logistic_growth_fitter'
            )

            # Connect table to fitter
            protocol_proxy.add_connector(
                out_port=rs_to_table_task >> 'data_table',
                in_port=logistic_fitter_task << 'table'
            )

            # Set parameters
            logistic_fitter_task.set_param('n_splits', n_splits)
            logistic_fitter_task.set_param('spline_smoothing', spline_smoothing)

            # Add outputs
            protocol_proxy.add_output(
                'parameters',
                logistic_fitter_task >> 'parameters',
                flag_resource=True
            )
            protocol_proxy.add_output(
                'fitted_curves_plot',
                logistic_fitter_task >> 'fitted_curves_plot',
                flag_resource=True
            )
            protocol_proxy.add_output(
                'growth_rate_histogram',
                logistic_fitter_task >> 'growth_rate_histogram',
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

            # Add analysis type tags
            scenario_proxy.add_tag(Tag("analysis_type", "logistic_growth", is_propagable=False))
            scenario_proxy.add_tag(Tag("analysis_timestamp", timestamp, is_propagable=False))
            scenario_proxy.add_tag(Tag("index_column", index_column, is_propagable=False))
            scenario_proxy.add_tag(Tag("data_column", data_column, is_propagable=False))
            scenario_proxy.add_tag(Tag("n_splits", str(n_splits), is_propagable=False))
            scenario_proxy.add_tag(Tag("spline_smoothing", str(spline_smoothing), is_propagable=False))

            # Add to queue
            scenario_proxy.add_to_queue()

            # Return the new scenario
            new_scenario = scenario_proxy.get_model()
            return new_scenario

    except Exception as e:
        st.error(f"Erreur lors du lancement du scénario Logistic Growth: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return None


def render_logistic_growth_step(recipe: CellCultureRecipe, cell_culture_state: CellCultureState,
                                quality_check_scenario: Scenario) -> None:
    """
    Render the Logistic Growth Fitting step

    :param recipe: The Recipe instance
    :param cell_culture_state: The cell culture state
    :param quality_check_scenario: The quality check scenario to analyze
    """
    translate_service = cell_culture_state.get_translate_service()

    st.markdown(f"### 📈 {translate_service.translate('logistic_growth_title')}")

    st.markdown(translate_service.translate('logistic_growth_description'))
    st.markdown(f"\n**{translate_service.translate('logistic_growth_params_extracted')}** :")
    st.markdown(f"- {translate_service.translate('logistic_growth_max_absorbance')}")
    st.markdown(f"- {translate_service.translate('logistic_growth_growth_rate')}")
    st.markdown(f"- {translate_service.translate('logistic_growth_lag_time')}")
    st.markdown(f"- {translate_service.translate('logistic_growth_initial_absorbance')}")
    st.markdown(f"- {translate_service.translate('logistic_growth_r_squared')}")

    # Get the quality check output for column selection
    qc_output = cell_culture_state.get_quality_check_scenario_interpolated_output_resource_model(quality_check_scenario)
    qc_output_resource_set = qc_output.get_resource() if qc_output else None

    if not qc_output_resource_set:
        st.warning(f"⚠️ {translate_service.translate('cannot_retrieve_qc_data')}")
        return

    # Get available columns
    index_columns = cell_culture_state.get_strict_index_columns_from_resource_set(qc_output_resource_set)
    data_columns = cell_culture_state.get_data_columns_from_resource_set(qc_output_resource_set)

    if not index_columns:
        st.warning(f"⚠️ {translate_service.translate('no_index_columns_found')}")
        return

    if not data_columns:
        st.warning(f"⚠️ {translate_service.translate('no_data_columns_found')}")
        return

    # Column selection
    st.markdown(f"#### 📊 {translate_service.translate('column_selection')}")
    col1, col2 = st.columns(2)

    with col1:
        index_column = st.selectbox(
            translate_service.translate('index_column_selection'),
            options=index_columns,
            index=0,
            help=translate_service.translate('index_column_help')
        )

    with col2:
        data_column = st.selectbox(
            translate_service.translate('data_column_selection'),
            options=data_columns,
            index=0,
            help=translate_service.translate('data_column_help')
        )

    # Configuration section
    st.markdown("---")
    with st.expander(f"⚙️ {translate_service.translate('analysis_configuration')}", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            n_splits = st.number_input(
                translate_service.translate('n_splits_cv'),
                min_value=2,
                max_value=10,
                value=3,
                help=translate_service.translate('n_splits_help')
            )

        with col2:
            spline_smoothing = st.number_input(
                translate_service.translate('spline_smoothing'),
                min_value=0.001,
                max_value=1.0,
                value=0.045,
                format="%.3f",
                help=translate_service.translate('spline_smoothing_help')
            )

    # Launch button
    if st.button(f"🚀 {translate_service.translate('launch_logistic_analysis')}", type="primary",
                 use_container_width=True):
        with st.spinner(f"{translate_service.translate('launching_analysis')}"):
            new_scenario = launch_logistic_growth_scenario(
                quality_check_scenario,
                cell_culture_state,
                index_column=index_column,
                data_column=data_column,
                n_splits=n_splits,
                spline_smoothing=spline_smoothing
            )

            if new_scenario:
                st.success(f"✅ {translate_service.translate('scenario_created_successfully')} : {new_scenario.title}")
                st.info(translate_service.translate('analysis_running_reload'))
                st.rerun()
            else:
                st.error(f"❌ {translate_service.translate('scenario_creation_failed')}")

    # Display existing scenarios
    st.markdown("---")
    st.markdown(f"#### 📊 {translate_service.translate('existing_analyses')}")

    # Get logistic growth scenarios for this quality check
    logistic_scenarios = recipe.get_logistic_growth_scenarios_for_quality_check(quality_check_scenario.id)

    if logistic_scenarios:
        for scenario in logistic_scenarios:
            # Extract data column from tags
            entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)
            data_col_tags = entity_tag_list.get_tags_by_key("data_column")
            data_col = data_col_tags[0].tag_value if data_col_tags else "N/A"

            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])

                with col1:
                    st.write(f"**{scenario.title}**")
                    st.caption(
                        f"{translate_service.translate('column_label')}: {data_col} | {translate_service.translate('status')}: {scenario.status.value}")

                with col2:
                    if scenario.status.value == "SUCCESS":
                        st.success(f"✅ {translate_service.translate('status_finished')}")
                    elif scenario.status.value == "RUNNING":
                        st.info(f"⏳ {translate_service.translate('status_in_progress')}")
                    elif scenario.status.value == "ERROR":
                        st.error(f"❌ {translate_service.translate('status_error')}")

                with col3:
                    if st.button(translate_service.translate('view_button'), key=f"view_lg_{scenario.id}"):
                        st.session_state['selected_logistic_scenario'] = scenario.id
                        st.rerun()

                st.markdown("---")
    else:
        st.info(translate_service.translate('no_logistic_analysis'))
