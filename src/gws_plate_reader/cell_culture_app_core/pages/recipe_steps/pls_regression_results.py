"""
PLS Regression Results Display for Cell Culture Dashboard
Displays results from PLS regression analysis
"""
import streamlit as st
from gws_core import Scenario, ScenarioProxy, ScenarioStatus
from gws_plate_reader.cell_culture_app_core.cell_culture_state import CellCultureState
from gws_plate_reader.cell_culture_app_core.cell_culture_recipe import CellCultureRecipe


def render_pls_regression_results(recipe: CellCultureRecipe, cell_culture_state: CellCultureState,
                                  pls_scenario: Scenario) -> None:
    """
    Render the PLS Regression analysis results

    :param recipe: The Recipe instance
    :param cell_culture_state: The cell culture state
    :param pls_scenario: The PLS regression scenario to display results for
    """
    translate_service = cell_culture_state.get_translate_service()

    st.markdown(f"### 📊 {translate_service.translate('pls_regression_results_title')}")
    st.markdown(f"**{translate_service.translate('analysis_title_label')}** : {pls_scenario.title}")
    st.markdown(f"**{translate_service.translate('status_label')}** : {pls_scenario.status.name}")

    if pls_scenario.status != ScenarioStatus.SUCCESS:
        if pls_scenario.status == ScenarioStatus.ERROR:
            st.error(f"❌ {translate_service.translate('analysis_failed')}")
        elif pls_scenario.status.is_running():
            st.info(f"⏳ {translate_service.translate('analysis_in_progress')}")
        else:
            st.warning(translate_service.translate('analysis_status').format(status=pls_scenario.status.name))
        return

    try:
        # Get the scenario proxy to access outputs
        scenario_proxy = ScenarioProxy.from_existing_scenario(pls_scenario.id)
        protocol_proxy = scenario_proxy.get_protocol()

        # Get all output resources
        summary_table_model = protocol_proxy.get_output_resource_model('summary_table')
        vip_table_model = protocol_proxy.get_output_resource_model('vip_table')
        plot_components_model = protocol_proxy.get_output_resource_model('plot_components')
        vip_plot_model = protocol_proxy.get_output_resource_model('vip_plot')
        plot_train_model = protocol_proxy.get_output_resource_model('plot_train_set')
        plot_test_model = protocol_proxy.get_output_resource_model('plot_test_set')

        # Display results in tabs
        tabs = st.tabs([
            f"📈 {translate_service.translate('tab_performance')}",
            f"🎯 {translate_service.translate('tab_variable_importance')}",
            f"🔬 {translate_service.translate('tab_predictions_train')}",
            f"✅ {translate_service.translate('tab_predictions_test')}"
        ])

        # Tab 1: Performance metrics and components plot
        with tabs[0]:
            st.markdown(f"#### 📈 {translate_service.translate('model_performance')}")

            # Display components plot
            if plot_components_model:
                st.markdown(f"**{translate_service.translate('component_selection_cv')}**")
                plot_components = plot_components_model.get_resource()
                st.plotly_chart(plot_components.figure, use_container_width=True)
                st.info(f"💡 {translate_service.translate('optimal_components_info')}")

            st.markdown("---")

            # Display summary table
            if summary_table_model:
                st.markdown(f"**{translate_service.translate('performance_metrics')}**")
                summary_table = summary_table_model.get_resource()
                summary_df = summary_table.get_data()

                st.dataframe(summary_df, width='stretch')

                # Download button
                csv = summary_df.to_csv(index=True)
                st.download_button(
                    label=f"📥 {translate_service.translate('download_metrics_csv')}",
                    data=csv,
                    file_name=f"pls_metrics_{pls_scenario.id[:8]}.csv",
                    mime="text/csv"
                )

                st.markdown(translate_service.translate('pls_metrics_interpretation'))

        # Tab 2: VIP scores
        with tabs[1]:
            st.markdown(f"#### 🎯 {translate_service.translate('vip_scores')}")

            # Display VIP plot
            if vip_plot_model:
                st.markdown(f"**{translate_service.translate('top_20_important_variables')}**")
                vip_plot = vip_plot_model.get_resource()
                st.plotly_chart(vip_plot.figure, use_container_width=True)

                st.info(f"💡 {translate_service.translate('vip_importance_threshold_info')}")

            st.markdown("---")

            # Display VIP table
            if vip_table_model:
                st.markdown(f"**{translate_service.translate('vip_table_top')}**")
                vip_table = vip_table_model.get_resource()
                vip_df = vip_table.get_data()

                st.dataframe(vip_df, width='stretch')

                # Download button
                csv = vip_df.to_csv(index=True)
                st.download_button(
                    label=f"📥 {translate_service.translate('download_vip_csv')}",
                    data=csv,
                    file_name=f"pls_vip_{pls_scenario.id[:8]}.csv",
                    mime="text/csv"
                )

                st.markdown(translate_service.translate('pls_vip_interpretation'))

        # Tab 3: Train predictions
        with tabs[2]:
            st.markdown(f"#### 🔬 {translate_service.translate('predictions_vs_observations_train')}")

            if plot_train_model:
                plot_train = plot_train_model.get_resource()
                st.plotly_chart(plot_train.figure, use_container_width=True)

                st.markdown(translate_service.translate('pls_train_interpretation'))

        # Tab 4: Test predictions
        with tabs[3]:
            st.markdown(f"#### ✅ {translate_service.translate('predictions_vs_observations_test')}")

            if plot_test_model:
                plot_test = plot_test_model.get_resource()
                st.plotly_chart(plot_test.figure, use_container_width=True)

                st.markdown(translate_service.translate('pls_test_interpretation'))

    except Exception as e:
        st.error(translate_service.translate('error_displaying_results').format(error=str(e)))
        import traceback
        st.code(traceback.format_exc())

    # Additional information section
    with st.expander(f"ℹ️ {translate_service.translate('pls_interpretation_guide')}"):
        st.markdown(translate_service.translate('pls_guide_content'))
