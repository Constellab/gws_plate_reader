"""
Medium PCA Results Display for Cell Culture Dashboard
Displays the results of a Medium PCA analysis scenario
"""
import streamlit as st
from gws_core import Scenario, ScenarioProxy, ScenarioStatus, Table
from gws_core.impl.plotly.plotly_resource import PlotlyResource

from gws_plate_reader.cell_culture_app_core.cell_culture_recipe import CellCultureRecipe
from gws_plate_reader.cell_culture_app_core.cell_culture_state import CellCultureState


def render_medium_pca_results(recipe: CellCultureRecipe, cell_culture_state: CellCultureState,
                              pca_scenario: Scenario) -> None:
    """
    Render the Medium PCA analysis results

    :param recipe: The Recipe instance
    :param cell_culture_state: The cell culture state
    :param pca_scenario: The PCA scenario to display results for
    """
    translate_service = cell_culture_state.get_translate_service()

    # Info box with PCA explanation
    with st.expander(f"💡 {translate_service.translate('pca_help_title')}"):
        st.markdown(f"### {translate_service.translate('pca_help_intro_title')}")
        st.markdown(translate_service.translate('pca_help_intro_text'))

        st.markdown(f"\n### {translate_service.translate('pca_help_scores_title')}")
        st.markdown(f"- {translate_service.translate('pca_help_scores_1')}")
        st.markdown(f"- {translate_service.translate('pca_help_scores_2')}")
        st.markdown(f"- {translate_service.translate('pca_help_scores_3')}")
        st.markdown(f"\n{translate_service.translate('pca_help_scores_tip')}")

        st.markdown(f"\n### {translate_service.translate('pca_help_scatter_title')}")
        st.markdown(f"- {translate_service.translate('pca_help_scatter_1')}")
        st.markdown(f"- {translate_service.translate('pca_help_scatter_2')}")
        st.markdown(f"- {translate_service.translate('pca_help_scatter_3')}")

        st.markdown(f"\n### {translate_service.translate('pca_help_biplot_title')}")
        st.markdown(f"- {translate_service.translate('pca_help_biplot_1')}")
        st.markdown(f"- {translate_service.translate('pca_help_biplot_2')}")
        st.markdown(f"- {translate_service.translate('pca_help_biplot_3')}")

    # Check scenario status
    if pca_scenario.status != ScenarioStatus.SUCCESS:
        st.warning(translate_service.translate('pca_analysis_not_finished'))
        return

    # Display PCA scenario outputs (scores table, scatter plot, biplot)
    scenario_proxy = ScenarioProxy.from_existing_scenario(pca_scenario.id)
    protocol_proxy = scenario_proxy.get_protocol()

    # Display scores table
    st.markdown(
        f"### 📊 {translate_service.translate('pca_results_title')} - {translate_service.translate('parameters_tab')}")
    scores_table = protocol_proxy.get_output('pca_scores_table')
    if scores_table and isinstance(scores_table, Table):
        df = scores_table.get_data()
        st.dataframe(df, width='stretch', height=400)

        # Download button
        csv = df.to_csv(index=False)
        st.download_button(
            label=translate_service.translate('download_parameters_csv'),
            data=csv,
            file_name=f"pca_scores_{pca_scenario.id[:8]}.csv",
            mime="text/csv"
        )
    else:
        st.warning(translate_service.translate('pca_biplot_not_found'))

    # Display scatter plot
    st.markdown("### 📈 PCA Scatter Plot (PC1 vs PC2)")
    scatter_plot = protocol_proxy.get_output('pca_scatter_plot')
    if scatter_plot and isinstance(scatter_plot, PlotlyResource):
        fig = scatter_plot.figure
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning(translate_service.translate('pca_variance_not_found'))

    # Display biplot
    st.markdown("### 🎯 PCA Biplot")
    biplot = protocol_proxy.get_output('pca_biplot')
    if biplot and isinstance(biplot, PlotlyResource):
        fig = biplot.figure
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning(translate_service.translate('pca_biplot_not_found'))

