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
    st.markdown(f"### 📊 Résultats PLS Regression")
    st.markdown(f"**Analyse** : {pls_scenario.title}")
    st.markdown(f"**Statut** : {pls_scenario.status.name}")

    if pls_scenario.status != ScenarioStatus.SUCCESS:
        if pls_scenario.status == ScenarioStatus.ERROR:
            st.error("❌ L'analyse a échoué")
        elif pls_scenario.status.is_running():
            st.info("⏳ L'analyse est en cours d'exécution...")
        else:
            st.warning(f"⚠️ Statut de l'analyse : {pls_scenario.status.name}")
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
        merged_table_model = protocol_proxy.get_output_resource_model('merged_table')

        # Display results in tabs
        tabs = st.tabs([
            "📈 Performance",
            "🎯 Importance des variables",
            "🔬 Prédictions Train",
            "✅ Prédictions Test",
            "📊 Table fusionnée"
        ])

        # Tab 1: Performance metrics and components plot
        with tabs[0]:
            st.markdown("#### 📈 Performance du modèle")

            # Display components plot
            if plot_components_model:
                st.markdown("**Sélection du nombre de composantes (Validation croisée)**")
                plot_components = plot_components_model.get_resource()
                st.plotly_chart(plot_components.figure, use_container_width=True)
                st.info("💡 Le nombre optimal de composantes minimise l'erreur RMSE en validation croisée")

            st.markdown("---")

            # Display summary table
            if summary_table_model:
                st.markdown("**Métriques de performance**")
                summary_table = summary_table_model.get_resource()
                summary_df = summary_table.get_data()

                st.dataframe(summary_df, use_container_width=True)

                # Download button
                csv = summary_df.to_csv(index=True)
                st.download_button(
                    label="📥 Télécharger les métriques (CSV)",
                    data=csv,
                    file_name=f"pls_metrics_{pls_scenario.id[:8]}.csv",
                    mime="text/csv"
                )

                st.markdown("""
**Interprétation** :
- **R² (Train)** : Qualité d'ajustement sur les données d'entraînement (0-1, plus proche de 1 = meilleur)
- **R² (Test)** : Qualité de prédiction sur les données de test (indicateur de généralisation)
- **RMSE (Train/Test)** : Erreur quadratique moyenne (plus faible = meilleur)
- Si R² Test << R² Train : possible sur-apprentissage
""")

        # Tab 2: VIP scores
        with tabs[1]:
            st.markdown("#### 🎯 Importance des variables (VIP)")

            # Display VIP plot
            if vip_plot_model:
                st.markdown("**Top 20 variables les plus importantes**")
                vip_plot = vip_plot_model.get_resource()
                st.plotly_chart(vip_plot.figure, use_container_width=True)

                st.info("💡 Les variables avec VIP > 1 sont considérées comme importantes pour la prédiction")

            st.markdown("---")

            # Display VIP table
            if vip_table_model:
                st.markdown("**Table des scores VIP (Top variables)**")
                vip_table = vip_table_model.get_resource()
                vip_df = vip_table.get_data()

                st.dataframe(vip_df, use_container_width=True)

                # Download button
                csv = vip_df.to_csv(index=True)
                st.download_button(
                    label="📥 Télécharger les scores VIP (CSV)",
                    data=csv,
                    file_name=f"pls_vip_{pls_scenario.id[:8]}.csv",
                    mime="text/csv"
                )

                st.markdown("""
**Interprétation VIP** :
- **VIP > 1** : Variable importante pour le modèle
- **VIP > 1.5** : Variable très importante
- **VIP < 0.5** : Variable peu importante, peut être retirée
- Les scores VIP indiquent quelles variables (nutriments, conditions) influencent le plus les résultats
""")

        # Tab 3: Train predictions
        with tabs[2]:
            st.markdown("#### 🔬 Prédictions vs Observations (Train Set)")

            if plot_train_model:
                plot_train = plot_train_model.get_resource()
                st.plotly_chart(plot_train.figure, use_container_width=True)

                st.markdown("""
**Interprétation** :
- Les points proches de la diagonale indiquent de bonnes prédictions
- Dispersion autour de la diagonale = erreur de prédiction
- Patterns systématiques (courbe) peuvent indiquer un biais du modèle
""")

        # Tab 4: Test predictions
        with tabs[3]:
            st.markdown("#### ✅ Prédictions vs Observations (Test Set)")

            if plot_test_model:
                plot_test = plot_test_model.get_resource()
                st.plotly_chart(plot_test.figure, use_container_width=True)

                st.markdown("""
**Interprétation** :
- Performance sur données non vues pendant l'entraînement
- Évalue la capacité de généralisation du modèle
- Si performances train >> test : sur-apprentissage possible
- Points s'écartant fortement de la diagonale = outliers ou cas particuliers
""")

        # Tab 5: Merged table
        with tabs[4]:
            st.markdown("#### 📊 Table fusionnée (Métadonnées + Features)")

            if merged_table_model:
                merged_table = merged_table_model.get_resource()
                merged_df = merged_table.get_data()

                st.markdown(f"**Dimensions** : {merged_df.shape[0]} lignes × {merged_df.shape[1]} colonnes")

                # Display table
                st.dataframe(merged_df, use_container_width=True, height=400)

                # Download button
                csv = merged_df.to_csv(index=True)
                st.download_button(
                    label="📥 Télécharger la table fusionnée (CSV)",
                    data=csv,
                    file_name=f"pls_merged_table_{pls_scenario.id[:8]}.csv",
                    mime="text/csv"
                )

                st.info("💡 Cette table contient les données brutes utilisées pour l'analyse PLS (métadonnées + features)")

    except Exception as e:
        st.error(f"Erreur lors de l'affichage des résultats : {str(e)}")
        import traceback
        st.code(traceback.format_exc())

    # Additional information section
    with st.expander("ℹ️ Guide d'interprétation PLS"):
        st.markdown("""
### Comment interpréter les résultats PLS ?

#### 1. Performance du modèle (Tab 1)

**Graphique des composantes** :
- Montre l'erreur de validation croisée en fonction du nombre de composantes
- Le modèle sélectionne automatiquement le nombre optimal
- Plus de composantes ≠ nécessairement meilleur (risque de sur-apprentissage)

**Métriques** :
- **R² proche de 1** : Excellent modèle
- **R² autour de 0.7-0.9** : Bon modèle
- **R² < 0.5** : Modèle faible, revoir les variables
- **R² Test < R² Train** : Normal, mais l'écart ne doit pas être trop grand

#### 2. Importance des variables (VIP) (Tab 2)

**Scores VIP** :
- Identifie les nutriments/conditions les plus influents
- VIP > 1 : Variable importante à conserver
- Permet de simplifier les milieux en se concentrant sur les facteurs clés

**Applications** :
- Optimisation de formulation : focus sur variables à VIP élevé
- Réduction de coûts : éliminer variables à VIP faible
- Compréhension biologique : quels facteurs contrôlent la croissance ?

#### 3. Prédictions (Tabs 3 et 4)

**Train Set** :
- Doit montrer un bon ajustement (points sur la diagonale)
- Dispersion modérée acceptable

**Test Set** :
- Plus important : évalue la généralisation
- Performance similaire au train = bon modèle
- Outliers = conditions expérimentales particulières à investiguer

#### 4. Utilisation pratique

**Pour optimiser un milieu** :
1. Regarder les variables à VIP élevé
2. Analyser leur influence (coefficient positif/négatif)
3. Ajuster ces composants en priorité

**Pour prédire des performances** :
1. Vérifier R² Test > 0.7
2. Utiliser le modèle pour simuler de nouvelles compositions
3. Valider expérimentalement les prédictions

**Limites** :
- Le modèle interpole, pas extrapole : rester dans la gamme des données
- Corrélation ≠ causalité : confirmer les hypothèses expérimentalement
- Qualité des données critique : outliers et erreurs de mesure impactent les résultats
""")
