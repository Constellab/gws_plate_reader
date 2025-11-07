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
    st.title(f"{recipe.name} - {pca_scenario.title}")

    # Check scenario status
    if pca_scenario.status != ScenarioStatus.SUCCESS:
        st.warning(f"Le scénario PCA n'est pas encore terminé avec succès. Statut: {pca_scenario.status.name}")
        return

    # Display PCA scenario outputs (scores table, scatter plot, biplot)
    scenario_proxy = ScenarioProxy.from_existing_scenario(pca_scenario.id)
    protocol_proxy = scenario_proxy.get_protocol()

    # Display scores table
    st.markdown("### 📊 Tableau des Scores PCA")
    scores_table = protocol_proxy.get_output('pca_scores_table')
    if scores_table and isinstance(scores_table, Table):
        df = scores_table.get_data()
        st.dataframe(df, use_container_width=True, height=400)

        # Download button
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Télécharger les scores (CSV)",
            data=csv,
            file_name=f"pca_scores_{pca_scenario.id[:8]}.csv",
            mime="text/csv"
        )
    else:
        st.warning("Tableau des scores non encore disponible")

    # Display scatter plot
    st.markdown("### 📈 Graphique de dispersion PCA (PC1 vs PC2)")
    scatter_plot = protocol_proxy.get_output('pca_scatter_plot')
    if scatter_plot and isinstance(scatter_plot, PlotlyResource):
        fig = scatter_plot.figure
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Graphique de dispersion non encore disponible")

    # Display biplot
    st.markdown("### 🎯 Biplot PCA")
    biplot = protocol_proxy.get_output('pca_biplot')
    if biplot and isinstance(biplot, PlotlyResource):
        fig = biplot.figure
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Biplot non encore disponible")

    # Info box with interpretation help
    with st.expander("💡 Aide à l'interprétation"):
        st.markdown("""
        **Interprétation de l'analyse PCA**

        **Tableau des Scores :**
        - Montre les coordonnées de chaque milieu dans l'espace réduit (PC1, PC2, etc.)
        - Les milieux proches dans cet espace ont des compositions similaires

        **Graphique de dispersion (PC1 vs PC2) :**
        - Chaque point représente un milieu de culture
        - Les milieux regroupés ont des compositions chimiques similaires
        - Plus les points sont éloignés, plus les compositions diffèrent
        - PC1 et PC2 expliquent le maximum de variance possible (% indiqué sur les axes)

        **Biplot :**
        - Combine les échantillons (points) et les variables (flèches)
        - Les flèches indiquent quels composants contribuent le plus à chaque axe
        - Les milieux proches des flèches sont riches en ces composants
        - Les flèches dans la même direction indiquent des composants corrélés
        """)
