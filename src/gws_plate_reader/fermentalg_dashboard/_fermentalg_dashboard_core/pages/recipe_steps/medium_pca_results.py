"""
Medium PCA Results Display for Fermentalg Dashboard
Displays the results of a Medium PCA analysis scenario
"""
import streamlit as st

from gws_core import Scenario, ScenarioStatus, ScenarioProxy, Table
from gws_core.impl.plotly.plotly_resource import PlotlyResource
from gws_plate_reader.fermentalg_dashboard._fermentalg_dashboard_core.fermentalg_state import FermentalgState
from gws_plate_reader.fermentalg_dashboard._fermentalg_dashboard_core.fermentalg_recipe import FermentalgRecipe


def render_medium_pca_results(recipe: FermentalgRecipe, fermentalg_state: FermentalgState,
                              pca_scenario: Scenario) -> None:
    """
    Render the Medium PCA analysis results

    :param recipe: The Recipe instance
    :param fermentalg_state: The fermentalg state
    :param pca_scenario: The PCA scenario to display results for
    """
    translate_service = fermentalg_state.get_translate_service()

    st.title(f"{recipe.name} - {pca_scenario.title}")

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
        st.dataframe(df, use_container_width=True, height=400)

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

    # Info box with interpretation help
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
        st.markdown(f"- {translate_service.translate('pca_help_scatter_4')}")
        st.markdown(f"- {translate_service.translate('pca_help_scatter_5')}")
        st.markdown(f"- {translate_service.translate('pca_help_scatter_6')}")
        
        st.markdown(f"\n### {translate_service.translate('pca_help_biplot_title')}")
        st.markdown(f"- {translate_service.translate('pca_help_biplot_1')}")
        st.markdown(f"- {translate_service.translate('pca_help_biplot_2')}")
        st.markdown(f"    - {translate_service.translate('pca_help_biplot_2a')}")
        st.markdown(f"    - {translate_service.translate('pca_help_biplot_2b')}")
        st.markdown(f"    - {translate_service.translate('pca_help_biplot_2c')}")
        st.markdown(f"    - {translate_service.translate('pca_help_biplot_2d')}")
        st.markdown(f"- {translate_service.translate('pca_help_biplot_3')}")
        st.markdown(f"    - {translate_service.translate('pca_help_biplot_3a')}")
        st.markdown(f"    - {translate_service.translate('pca_help_biplot_3b')}")
        st.markdown(f"    - {translate_service.translate('pca_help_biplot_3c')}")
        st.markdown(f"\n{translate_service.translate('pca_help_biplot_tip')}")
