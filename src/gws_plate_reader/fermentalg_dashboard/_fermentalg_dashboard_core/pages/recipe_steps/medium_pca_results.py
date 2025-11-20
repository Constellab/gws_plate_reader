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
        ### Interprétation de la PCA

L'analyse en composantes principales (PCA) permet de réduire la dimension des données tout en conservant au maximum l'information. Elle aide à visualiser les relations entre échantillons et variables et à identifier des groupes ou tendances dans les données.

### Tableau des Scores :

-   Chaque ligne correspond à un milieu de culture
-   Montre les **coordonnées** de chaque milieu dans l'espace réduit (PC1, PC2, etc.)

-   Les milieux proches dans cet espace ont des compositions similaires

💡 Si deux milieux ont des coordonnées proches sur PC1 et PC2, ils réagissent de manière similaire vis-à-vis des variables mesurées (composants, nutriments, etc.).

### Graphique de dispersion (PC1 vs PC2) :

-   Chaque **point représente un milieu de culture**.
-   Les axes PC1 et PC2 sont les deux directions qui expliquent le plus de variance dans les données (le pourcentage est indiqué sur les axes).
-   Si plusieurs milieux forment un **cluster**, cela signifie qu'ils ont une composition chimique similaire.
-   Si un milieu est **isolé**, il a une composition qui diffère des autres milieux.

-   Les milieux situés du même côté d'un axe partagent des caractéristiques communes.
-   Les milieux aux extrêmes opposés de PC1 ou PC2 sont contrastés sur les variables dominantes de cet axe.

### Biplot :

-   Le biplot combine les échantillons (points) et les **variables** (flèches)
-   Lecture des flèches (variables)
    -   La direction d'une flèche indique dans quelle direction la variable augmente.
    -   La longueur de la flèche indique l'importance de la variable dans la construction de l'axe (plus elle est longue, plus elle contribue).
    -   Les flèches proches les unes des autres indiquent des variables corrélées (elles varient de la même façon).
    -   Des flèches opposées traduisent une corrélation négative (quand l'une augmente, l'autre diminue)

-   Lecture des points (échantillons)
    -   Les points proches d'une flèche sont riches en cette variable (valeur élevée).
    -   Les points à l'opposé de la flèche sont pauvres en cette variable.
    -   Les points proches entre eux ont des profils similaires sur les variables principales.

💡 Si un milieu est proche de la flèche "glucose", cela signifie qu'il contient une forte proportion de glucose ou qu'il est influencé par cette variable.
        """)
