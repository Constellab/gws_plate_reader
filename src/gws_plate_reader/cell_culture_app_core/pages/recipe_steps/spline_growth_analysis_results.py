"""
Spline Growth Rate Analysis Results Display for Cell Culture Dashboard
"""
import streamlit as st

from gws_core import Scenario, ScenarioProxy, Table
from gws_core.impl.plotly.plotly_resource import PlotlyResource
from gws_plate_reader.cell_culture_app_core.cell_culture_state import CellCultureState
from gws_plate_reader.cell_culture_app_core.cell_culture_recipe import CellCultureRecipe


def render_spline_growth_results(recipe: CellCultureRecipe, cell_culture_state: CellCultureState,
                                 scenario: Scenario) -> None:
    """
    Render results of a Spline Growth Rate Inference analysis

    :param recipe: The Recipe instance
    :param cell_culture_state: The cell culture state
    :param scenario: The spline growth scenario to display
    """
    translate_service = cell_culture_state.get_translate_service()

    st.markdown(f"### 📊 {translate_service.translate('results_title')} : {scenario.title}")
    st.markdown(f"**{translate_service.translate('status')}** : {scenario.status.value}")

    if scenario.status.value != "SUCCESS":
        st.warning(f"⏳ {translate_service.translate('analysis_not_finished')}")
        if st.button(f"🔄 {translate_service.translate('refresh_button')}"):
            st.rerun()
        return

    try:
        # Get scenario outputs using ScenarioProxy
        scenario_proxy = ScenarioProxy.from_existing_scenario(scenario.id)
        protocol_proxy = scenario_proxy.get_protocol()

        # Get output resources by name
        parameters_table = protocol_proxy.get_output('parameters')
        growth_curves_plot = protocol_proxy.get_output('growth_curves_plot')
        growth_rate_comparison = protocol_proxy.get_output('growth_rate_comparison')

        # Display results in tabs
        tab1, tab2, tab3 = st.tabs([
            f"📊 {translate_service.translate('parameters_tab')}",
            f"📈 {translate_service.translate('curves_derivatives_tab')}",
            f"📊 {translate_service.translate('comparison_tab')}"
        ])

        with tab1:
            st.markdown(f"#### {translate_service.translate('inference_parameters_table')}")
            if parameters_table and isinstance(parameters_table, Table):
                df = parameters_table.get_data()
                st.dataframe(df, use_container_width=True)

                # Download button
                csv = df.to_csv(index=True).encode('utf-8')
                st.download_button(
                    label=f"💾 {translate_service.translate('download_parameters_csv')}",
                    data=csv,
                    file_name=f"spline_growth_parameters_{scenario.id}.csv",
                    mime="text/csv"
                )
            else:
                st.warning(translate_service.translate('parameters_table_not_found'))

        with tab2:
            st.markdown(f"#### {translate_service.translate('smoothed_curves_growth_rate')}")
            st.markdown(f"*{translate_service.translate('smoothed_curves_info')}*")
            if growth_curves_plot and isinstance(growth_curves_plot, PlotlyResource):
                st.plotly_chart(growth_curves_plot.figure, use_container_width=True)
            else:
                st.warning(translate_service.translate('curves_plot_not_found'))

        with tab3:
            st.markdown(f"#### {translate_service.translate('max_growth_rate_comparison')}")
            if growth_rate_comparison and isinstance(growth_rate_comparison, PlotlyResource):
                st.plotly_chart(growth_rate_comparison.figure, use_container_width=True)
            else:
                st.warning(translate_service.translate('comparison_plot_not_found'))

    except Exception as e:
        st.error(f"{translate_service.translate('error_displaying_results')} : {str(e)}")
        import traceback
        st.code(traceback.format_exc())
