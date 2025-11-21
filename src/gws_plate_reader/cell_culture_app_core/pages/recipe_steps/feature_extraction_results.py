"""
Feature Extraction Results Display for Cell Culture Dashboard
Displays the results of a Feature Extraction analysis scenario
"""
import streamlit as st

from gws_core import Scenario, ScenarioStatus, ScenarioProxy, Table, ResourceSet
from gws_core.impl.plotly.plotly_resource import PlotlyResource
from gws_plate_reader.cell_culture_app_core.cell_culture_state import CellCultureState
from gws_plate_reader.cell_culture_app_core.cell_culture_recipe import CellCultureRecipe


def render_feature_extraction_results(recipe: CellCultureRecipe, cell_culture_state: CellCultureState,
                                      fe_scenario: Scenario) -> None:
    """
    Render the Feature Extraction analysis results

    :param recipe: The Recipe instance
    :param cell_culture_state: The cell culture state
    :param fe_scenario: The Feature Extraction scenario to display results for
    """
    translate_service = cell_culture_state.get_translate_service()

    st.title(f"{recipe.name} - {fe_scenario.title}")

    # Check scenario status
    if fe_scenario.status != ScenarioStatus.SUCCESS:
        st.warning(translate_service.translate('feature_extraction_analysis_not_finished'))
        return

    # Display Feature Extraction scenario outputs (results table and plots)
    scenario_proxy = ScenarioProxy.from_existing_scenario(fe_scenario.id)
    protocol_proxy = scenario_proxy.get_protocol()

    # Display results table in expandable section (at the top)
    with st.expander(f"📊 {translate_service.translate('view_button')} {translate_service.translate('feature_extraction_params_table').lower()}", expanded=False):
        st.markdown(f"**{translate_service.translate('feature_extraction_params_table')}**")
        results_table = protocol_proxy.get_output('results_table')
        if results_table and isinstance(results_table, Table):
            df = results_table.get_data()
            st.dataframe(df, use_container_width=True, height=600)

            # Option to download
            csv = df.to_csv(index=False)
            st.download_button(
                label=translate_service.translate('feature_extraction_download_csv'),
                data=csv,
                file_name=f"feature_extraction_results_{fe_scenario.id[:8]}.csv",
                mime="text/csv"
            )
        else:
            st.warning(translate_service.translate('feature_extraction_params_not_found'))

    # Display plots ResourceSet (main content)
    st.markdown(f"### 📈 {translate_service.translate('feature_extraction_fitted_curves')}")
    plots_resource_set = protocol_proxy.get_output('plots')

    if plots_resource_set and isinstance(plots_resource_set, ResourceSet):
        plots_resources = plots_resource_set.get_resources()
        st.info(f"📊 {len(plots_resources)} {translate_service.translate('resources')}")

        # Organize plots by type
        comparison_plots = []
        model_plots = {}  # Dictionary: model_name -> list of plots

        for plot_name, plot_resource in plots_resources.items():
            if isinstance(plot_resource, PlotlyResource):
                # Check if it's a comparison plot (usually contains "comparison" in name)
                if "comparison" in plot_name.lower() or "comparative" in plot_name.lower():
                    comparison_plots.append((plot_name, plot_resource))
                else:
                    # Extract model name from plot name (format: "Model_SeriesName" or similar)
                    # Common pattern: ModelName_4P_SeriesName or just ModelName_SeriesName
                    parts = plot_name.split('_')
                    if len(parts) >= 2:
                        # Try to identify model name (usually first part or first + second part)
                        if parts[1] in ['4P', '5P']:
                            model_name = f"{parts[0]}_{parts[1]}"
                        else:
                            model_name = parts[0]

                        if model_name not in model_plots:
                            model_plots[model_name] = []
                        model_plots[model_name].append((plot_name, plot_resource))
                    else:
                        # Fallback: use full name as model
                        if "Autre" not in model_plots:
                            model_plots["Autre"] = []
                        model_plots["Autre"].append((plot_name, plot_resource))

        # Create selection options
        plot_options = ["📊 Graphiques de Comparaison"] + [f"📈 {model}" for model in
                                                          sorted(model_plots.keys())]

        selected_option = st.selectbox(
            translate_service.translate('select_plots'),
            options=plot_options,
            index=0,
            help=translate_service.translate('select_plots_help')
        )

        # Display plots based on selection
        if selected_option.startswith("📊"):
            # Display comparison plots
            if comparison_plots:
                for plot_name, plot_resource in comparison_plots:
                    st.markdown(f"#### {plot_name}")
                    fig = plot_resource.figure
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(translate_service.translate('no_comparison_plots'))
                # Fallback: display all plots
                for plot_name, plot_resource in plots_resources.items():
                    if isinstance(plot_resource, PlotlyResource):
                        st.markdown(f"#### {plot_name}")
                        fig = plot_resource.figure
                        st.plotly_chart(fig, use_container_width=True)
        else:
            # Extract model name from selection
            model_name = selected_option.replace("📈 ", "")
            if model_name in model_plots:
                st.markdown(f"#### {translate_service.translate('model')}: {model_name}")
                for plot_name, plot_resource in model_plots[model_name]:
                    st.markdown(f"**{plot_name}**")
                    fig = plot_resource.figure
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning(translate_service.translate('feature_extraction_curves_not_found'))
    else:
        st.warning(translate_service.translate('feature_extraction_curves_not_found'))

    # Info box with interpretation help
    with st.expander("💡 Aide à l'interprétation des résultats"):
        st.markdown("""
        **Interprétation des résultats d'extraction de caractéristiques**

        **Table de résultats :**
        - Contient tous les paramètres estimés pour chaque modèle et série
        - **Paramètres du modèle** : y0 (valeur initiale), A (asymptote), μ (taux), lag (latence)
        - **Métriques statistiques** : R² (qualité d'ajustement), AIC/BIC (comparaison de modèles), RMSE/MAE (erreurs)
        - **Intervalles de croissance** : t5, t10, t20, t50, t80, t90, t95 (temps à % d'amplitude)
        - **Caractéristiques dynamiques** : slope_max (taux max), doubling_time (temps de doublement)

        **Graphiques de comparaison :**
        - Comparent tous les modèles ajustés pour une même série de données
        - Permettent d'identifier le meilleur modèle visuellement
        - Les points sont les données réelles, les lignes sont les ajustements

        **Graphiques par modèle :**
        - Montrent l'ajustement d'un modèle spécifique à toutes les séries
        - Utile pour voir les performances d'un modèle particulier
        - Intervalles de confiance à 95% souvent affichés

        **Comment choisir le meilleur modèle :**
        1. Regarder le R² : plus proche de 1 = meilleur ajustement
        2. Comparer AIC/BIC : plus faible = meilleur modèle
        3. Vérifier visuellement l'ajustement sur les graphiques
        4. Privilégier la parcimonie : modèles simples si performances similaires
        """)
