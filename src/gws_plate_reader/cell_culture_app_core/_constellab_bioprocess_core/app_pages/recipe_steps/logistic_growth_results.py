"""
Logistic Growth Fitter Results Display for Cell Culture Dashboard
Displays the results of a Logistic Growth Fitter analysis scenario
"""

import streamlit as st
from gws_core import Scenario, ScenarioProxy, ScenarioStatus, Table
from gws_core.impl.plotly.plotly_resource import PlotlyResource
from gws_plate_reader.cell_culture_app_core._constellab_bioprocess_core.cell_culture_recipe import (
    CellCultureRecipe,
)
from gws_plate_reader.cell_culture_app_core._constellab_bioprocess_core.cell_culture_state import (
    CellCultureState,
)


def render_logistic_growth_results(
    recipe: CellCultureRecipe, cell_culture_state: CellCultureState, lg_scenario: Scenario
) -> None:
    """
    Render the Logistic Growth Fitter analysis results

    :param recipe: The Recipe instance
    :param cell_culture_state: The cell culture state
    :param lg_scenario: The Logistic Growth scenario to display results for
    """
    translate_service = cell_culture_state.get_translate_service()

    # Info box with interpretation help
    with st.expander(f"💡 {translate_service.translate('interpretation_help')}"):
        st.markdown(translate_service.translate("logistic_growth_results_interpretation"))

    # Check scenario status
    if lg_scenario.status != ScenarioStatus.SUCCESS:
        st.warning(translate_service.translate("logistic_growth_analysis_not_finished"))
        return

    # Display Logistic Growth scenario outputs
    scenario_proxy = ScenarioProxy.from_existing_scenario(lg_scenario.id)
    protocol_proxy = scenario_proxy.get_protocol()

    # Create tabs for different views
    tab_params, tab_curves, tab_histogram = st.tabs(
        [
            translate_service.translate("parameters_tab"),
            translate_service.translate("fitted_curves_tab"),
            translate_service.translate("distribution_tab"),
        ]
    )

    with tab_params:
        st.markdown(f"### 📊 {translate_service.translate('growth_parameters_table')}")
        parameters_table = protocol_proxy.get_output("parameters")
        if parameters_table and isinstance(parameters_table, Table):
            df = parameters_table.get_data()
            st.dataframe(df, width="stretch", height=400)

            # Option to download
            csv = df.to_csv(index=True)
            st.download_button(
                label=translate_service.translate("download_parameters_csv"),
                data=csv,
                file_name=f"logistic_growth_params_{lg_scenario.id[:8]}.csv",
                mime="text/csv",
                icon=":material/download:",
            )

            # Display summary statistics
            st.markdown(f"#### {translate_service.translate('basic_statistics')}")
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(translate_service.translate("logistic_growth_wells_fitted"), len(df))

            if "Growth_Rate" in df.columns:
                with col2:
                    st.metric(
                        translate_service.translate("logistic_growth_mean_growth_rate"),
                        f"{df['Growth_Rate'].mean():.4f}",
                    )
                with col3:
                    st.metric(
                        translate_service.translate("logistic_growth_std_growth_rate"),
                        f"{df['Growth_Rate'].std():.4f}",
                    )

            if "Avg_R2" in df.columns:
                with col4:
                    st.metric(
                        translate_service.translate("logistic_growth_mean_r2"),
                        f"{df['Avg_R2'].mean():.3f}",
                    )
        else:
            st.warning(translate_service.translate("parameters_table_not_found"))

    with tab_curves:
        st.markdown(f"### 📈 {translate_service.translate('fitted_growth_curves')}")
        fitted_curves_plot = protocol_proxy.get_output("fitted_curves_plot")
        if fitted_curves_plot and isinstance(fitted_curves_plot, PlotlyResource):
            fig = fitted_curves_plot.figure
            st.plotly_chart(fig, width="stretch")
        else:
            st.warning(translate_service.translate("fitted_curves_not_found"))

    with tab_histogram:
        st.markdown(f"### 📊 {translate_service.translate('growth_rate_distribution')}")
        histogram_plot = protocol_proxy.get_output("growth_rate_histogram")
        if histogram_plot and isinstance(histogram_plot, PlotlyResource):
            fig = histogram_plot.figure
            st.plotly_chart(fig, width="stretch")
        else:
            st.warning(translate_service.translate("histogram_not_found"))
