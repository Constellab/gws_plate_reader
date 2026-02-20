"""
Random Forest Regression Results Display for Cell Culture Dashboard
Displays results from Random Forest regression analysis
"""

import traceback

import streamlit as st
from gws_core import Scenario, ScenarioProxy, ScenarioStatus
from gws_plate_reader.cell_culture_app_core._constellab_bioprocess_core.cell_culture_recipe import (
    CellCultureRecipe,
)
from gws_plate_reader.cell_culture_app_core._constellab_bioprocess_core.cell_culture_state import (
    CellCultureState,
)


def render_random_forest_results(
    recipe: CellCultureRecipe, cell_culture_state: CellCultureState, rf_scenario: Scenario
) -> None:
    """
    Render the Random Forest Regression analysis results

    :param recipe: The Recipe instance
    :param cell_culture_state: The cell culture state
    :param rf_scenario: The Random Forest regression scenario to display results for
    """
    translate_service = cell_culture_state.get_translate_service()

    # Additional information section
    with st.expander(f"💡 {translate_service.translate('rf_interpretation_guide')}"):
        st.markdown(translate_service.translate("rf_guide_content"))

    if rf_scenario.status != ScenarioStatus.SUCCESS:
        if rf_scenario.status == ScenarioStatus.ERROR:
            st.error(f"❌ {translate_service.translate('analysis_failed')}")
        elif rf_scenario.is_running:
            st.info(f"⏳ {translate_service.translate('analysis_in_progress')}")
        else:
            st.warning(
                translate_service.translate("analysis_status").format(
                    status=rf_scenario.status.name
                )
            )
        return

    try:
        # Get the scenario proxy to access outputs
        scenario_proxy = ScenarioProxy.from_existing_scenario(rf_scenario.id)
        protocol_proxy = scenario_proxy.get_protocol()

        # Get all output resources
        summary_table_model = protocol_proxy.get_output_resource_model("summary_table")
        vip_table_model = protocol_proxy.get_output_resource_model("vip_table")
        vip_plot_model = protocol_proxy.get_output_resource_model("vip_plot")
        plot_estimators_model = protocol_proxy.get_output_resource_model("plot_estimators")
        plot_train_model = protocol_proxy.get_output_resource_model("plot_train_set")
        plot_test_model = protocol_proxy.get_output_resource_model("plot_test_set")

        # Display results in tabs
        tabs = st.tabs(
            [
                f"📈 {translate_service.translate('tab_performance')}",
                f"🎯 {translate_service.translate('tab_variable_importance')}",
                f"🔬 {translate_service.translate('tab_predictions_train')}",
                f"✅ {translate_service.translate('tab_predictions_test')}",
            ]
        )

        # Tab 1: Performance metrics and estimators plot
        with tabs[0]:
            st.markdown(f"#### 📈 {translate_service.translate('model_performance')}")

            # Display CV plot
            if plot_estimators_model:
                st.markdown(f"**{translate_service.translate('hyperparameter_optimization_cv')}**")
                plot_estimators = plot_estimators_model.get_resource()
                st.plotly_chart(plot_estimators.figure, width="stretch")
                st.info(translate_service.translate("rf_cv_plot_info"))

            st.markdown("---")

            # Display summary table
            if summary_table_model:
                st.markdown(f"**{translate_service.translate('performance_metrics')}**")
                summary_table = summary_table_model.get_resource()
                summary_df = summary_table.get_data()

                st.dataframe(summary_df, width="stretch")

                # Download button
                csv = summary_df.to_csv(index=True)
                st.download_button(
                    label=f"{translate_service.translate('download_metrics_csv')}",
                    data=csv,
                    file_name=f"rf_metrics_{rf_scenario.id[:8]}.csv",
                    mime="text/csv",
                    icon=":material/download:",
                )

                st.markdown(translate_service.translate("rf_metrics_interpretation"))

        # Tab 2: Feature importances
        with tabs[1]:
            st.markdown(f"#### 🎯 {translate_service.translate('feature_importance')}")

            # Display importance plot
            if vip_plot_model:
                vip_plot = vip_plot_model.get_resource()
                st.plotly_chart(vip_plot.figure, width="stretch")

                st.info(f"💡 {translate_service.translate('longer_bars_info')}")

            st.markdown("---")

            # Display importance table
            if vip_table_model:
                st.markdown(f"**{translate_service.translate('importance_table_top')}**")
                vip_table = vip_table_model.get_resource()
                vip_df = vip_table.get_data()

                st.dataframe(vip_df, width="stretch")

                # Download button
                csv = vip_df.to_csv(index=True)
                st.download_button(
                    label=f"{translate_service.translate('download_importances_csv')}",
                    data=csv,
                    file_name=f"rf_importances_{rf_scenario.id[:8]}.csv",
                    mime="text/csv",
                    icon=":material/download:",
                )

                st.markdown(translate_service.translate("rf_importance_interpretation"))

        # Tab 3: Train predictions
        with tabs[2]:
            st.markdown(
                f"#### 🔬 {translate_service.translate('predictions_vs_observations_train')}"
            )

            if plot_train_model:
                plot_train = plot_train_model.get_resource()
                st.plotly_chart(plot_train.figure, width="stretch")

                st.markdown(translate_service.translate("rf_train_interpretation"))

        # Tab 4: Test predictions
        with tabs[3]:
            st.markdown(
                f"#### ✅ {translate_service.translate('predictions_vs_observations_test')}"
            )

            if plot_test_model:
                plot_test = plot_test_model.get_resource()
                st.plotly_chart(plot_test.figure, width="stretch")

                st.markdown(translate_service.translate("rf_test_interpretation"))

    except Exception as e:
        st.error(translate_service.translate("error_displaying_results").format(error=str(e)))
        st.code(traceback.format_exc())
