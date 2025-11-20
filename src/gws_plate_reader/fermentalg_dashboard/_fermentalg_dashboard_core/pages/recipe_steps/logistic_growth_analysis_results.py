"""
Logistic Growth Analysis Results Display for Fermentalg Dashboard
"""
import streamlit as st

from gws_core import Scenario, ScenarioProxy, Table
from gws_core.impl.plotly.plotly_resource import PlotlyResource
from gws_plate_reader.fermentalg_dashboard._fermentalg_dashboard_core.fermentalg_state import FermentalgState
from gws_plate_reader.fermentalg_dashboard._fermentalg_dashboard_core.fermentalg_recipe import FermentalgRecipe


def render_logistic_growth_results(recipe: FermentalgRecipe, fermentalg_state: FermentalgState,
                                   scenario: Scenario) -> None:
    """
    Render results of a Logistic Growth Fitting analysis

    :param recipe: The Recipe instance
    :param fermentalg_state: The fermentalg state
    :param scenario: The logistic growth scenario to display
    """
    st.markdown(f"### 📈 Résultats : {scenario.title}")
    st.markdown(f"**Statut** : {scenario.status.value}")

    if scenario.status.value != "SUCCESS":
        st.warning("⏳ L'analyse n'est pas encore terminée ou a rencontré une erreur.")
        if st.button("🔄 Rafraîchir"):
            st.rerun()
        return

    try:
        # Get scenario outputs using ScenarioProxy
        scenario_proxy = ScenarioProxy.from_existing_scenario(scenario.id)
        protocol_proxy = scenario_proxy.get_protocol()

        # Get output resources by name
        parameters_table = protocol_proxy.get_output('parameters')
        fitted_curves_plot = protocol_proxy.get_output('fitted_curves_plot')
        growth_rate_histogram = protocol_proxy.get_output('growth_rate_histogram')

        # Display results in tabs
        tab1, tab2, tab3 = st.tabs(["📊 Paramètres", "📈 Courbes ajustées", "📊 Distribution"])

        with tab1:
            st.markdown("#### Tableau des paramètres de croissance")
            if parameters_table and isinstance(parameters_table, Table):
                df = parameters_table.get_data()
                st.dataframe(df, use_container_width=True)

                # Download button
                csv = df.to_csv(index=True).encode('utf-8')
                st.download_button(
                    label="💾 Télécharger les paramètres (CSV)",
                    data=csv,
                    file_name=f"logistic_growth_parameters_{scenario.id}.csv",
                    mime="text/csv"
                )
            else:
                st.warning("Tableau des paramètres non trouvé")

        with tab2:
            st.markdown("#### Courbes de croissance ajustées")
            if fitted_curves_plot and isinstance(fitted_curves_plot, PlotlyResource):
                st.plotly_chart(fitted_curves_plot.figure, use_container_width=True)
            else:
                st.warning("Graphique des courbes ajustées non trouvé")

        with tab3:
            st.markdown("#### Distribution des taux de croissance")
            if growth_rate_histogram and isinstance(growth_rate_histogram, PlotlyResource):
                st.plotly_chart(growth_rate_histogram.figure, use_container_width=True)
            else:
                st.warning("Histogramme non trouvé")

    except Exception as e:
        st.error(f"Erreur lors de l'affichage des résultats : {str(e)}")
        import traceback
        st.code(traceback.format_exc())
