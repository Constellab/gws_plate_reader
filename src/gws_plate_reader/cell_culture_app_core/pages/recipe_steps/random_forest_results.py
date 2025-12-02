"""
Random Forest Regression Results Display for Cell Culture Dashboard
Displays results from Random Forest regression analysis
"""
import streamlit as st
from gws_core import Scenario, ScenarioProxy, ScenarioStatus
from gws_plate_reader.cell_culture_app_core.cell_culture_state import CellCultureState
from gws_plate_reader.cell_culture_app_core.cell_culture_recipe import CellCultureRecipe


def render_random_forest_results(recipe: CellCultureRecipe, cell_culture_state: CellCultureState,
                                 rf_scenario: Scenario) -> None:
    """
    Render the Random Forest Regression analysis results

    :param recipe: The Recipe instance
    :param cell_culture_state: The cell culture state
    :param rf_scenario: The Random Forest regression scenario to display results for
    """
    st.markdown(f"### 🌲 Résultats Random Forest Regression")
    st.markdown(f"**Analyse** : {rf_scenario.title}")
    st.markdown(f"**Statut** : {rf_scenario.status.name}")

    if rf_scenario.status != ScenarioStatus.SUCCESS:
        if rf_scenario.status == ScenarioStatus.ERROR:
            st.error("❌ L'analyse a échoué")
        elif rf_scenario.status.is_running():
            st.info("⏳ L'analyse est en cours d'exécution...")
        else:
            st.warning(f"⚠️ Statut de l'analyse : {rf_scenario.status.name}")
        return

    try:
        # Get the scenario proxy to access outputs
        scenario_proxy = ScenarioProxy.from_existing_scenario(rf_scenario.id)
        protocol_proxy = scenario_proxy.get_protocol()

        # Get all output resources
        summary_table_model = protocol_proxy.get_output_resource_model('summary_table')
        vip_table_model = protocol_proxy.get_output_resource_model('vip_table')
        plot_estimators_model = protocol_proxy.get_output_resource_model('plot_estimators')
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

        # Tab 1: Performance metrics and estimators plot
        with tabs[0]:
            st.markdown("#### 📈 Performance du modèle")

            # Display estimators plot
            if plot_estimators_model:
                st.markdown("**Optimisation des hyperparamètres (Validation croisée)**")
                plot_estimators = plot_estimators_model.get_resource()
                st.plotly_chart(plot_estimators.figure, use_container_width=True)
                st.info(
                    "💡 Le graphique montre la performance (score) pour différentes combinaisons d'hyperparamètres (nombre d'arbres, profondeur)")

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
                    file_name=f"rf_metrics_{rf_scenario.id[:8]}.csv",
                    mime="text/csv"
                )

                st.markdown("""
**Interprétation** :
- **R² (Train)** : Qualité d'ajustement sur les données d'entraînement (0-1, plus proche de 1 = meilleur)
- **R² (Test)** : Qualité de prédiction sur les données de test (indicateur de généralisation)
- **RMSE (Train/Test)** : Erreur quadratique moyenne (plus faible = meilleur)
- Si R² Test << R² Train : possible sur-apprentissage
""")

        # Tab 2: Feature importances
        with tabs[1]:
            st.markdown("#### 🎯 Importance des variables (Feature Importances)")

            # Display importance plot
            if vip_plot_model:
                st.markdown("**Top 10 variables les plus importantes**")
                vip_plot = vip_plot_model.get_resource()
                st.plotly_chart(vip_plot.figure, use_container_width=True)

                st.info("💡 Les barres plus longues indiquent les variables qui contribuent le plus aux prédictions du modèle")

            st.markdown("---")

            # Display importance table
            if vip_table_model:
                st.markdown("**Table des importances (Top variables)**")
                vip_table = vip_table_model.get_resource()
                vip_df = vip_table.get_data()

                st.dataframe(vip_df, use_container_width=True)

                # Download button
                csv = vip_df.to_csv(index=True)
                st.download_button(
                    label="📥 Télécharger les importances (CSV)",
                    data=csv,
                    file_name=f"rf_importances_{rf_scenario.id[:8]}.csv",
                    mime="text/csv"
                )

                st.markdown("""
**Interprétation Feature Importance** :
- Les scores sont normalisés (somme = 1)
- Plus le score est élevé, plus la variable est importante
- Indique quelles variables (nutriments, conditions) influencent le plus les résultats
- Contrairement au VIP de PLS, pas de seuil strict, mais comparer les valeurs relatives
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
- Random Forest peut sur-apprendre sur le train set (normal si R² Train très élevé)
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
- Si performances train >> test : sur-apprentissage (réduire profondeur des arbres)
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
                    file_name=f"rf_merged_table_{rf_scenario.id[:8]}.csv",
                    mime="text/csv"
                )

                st.info("💡 Cette table contient les données brutes utilisées pour l'analyse Random Forest (métadonnées + features)")

    except Exception as e:
        st.error(f"Erreur lors de l'affichage des résultats : {str(e)}")
        import traceback
        st.code(traceback.format_exc())

    # Additional information section
    with st.expander("ℹ️ Guide d'interprétation Random Forest"):
        st.markdown("""
### Comment interpréter les résultats Random Forest ?

#### 1. Performance du modèle (Tab 1)

**Graphique d'optimisation des hyperparamètres** :
- Montre le score de validation croisée pour différentes configurations
- **n_estimators** : nombre d'arbres dans la forêt
- **max_depth** : profondeur maximale de chaque arbre
- Le modèle sélectionne automatiquement la meilleure combinaison

**Métriques** :
- **R² proche de 1** : Excellent modèle
- **R² autour de 0.7-0.9** : Bon modèle
- **R² < 0.5** : Modèle faible, revoir les variables ou les données
- **RMSE** : Erreur en unités de la variable cible (plus faible = meilleur)

**Différence Random Forest vs PLS** :
- Random Forest peut capturer des relations non-linéaires
- Généralement meilleur R² Train (peut sur-apprendre)
- Moins sensible à la multicolinéarité

#### 2. Importance des variables (Tab 2)

**Feature Importances** :
- Basées sur la réduction de l'impureté (Gini importance)
- Identifie les variables les plus utilisées pour les décisions
- Scores normalisés : somme = 1

**Applications** :
- Identifier les facteurs critiques pour la variable cible
- Simplifier les expériences futures en se concentrant sur les variables importantes
- Compréhension des mécanismes biologiques

**Différence avec VIP (PLS)** :
- Pas de seuil universel comme VIP > 1
- Comparer les importances relatives entre variables
- Les importances faibles (<0.01) peuvent souvent être ignorées

#### 3. Prédictions (Tabs 3 et 4)

**Train Set** :
- Random Forest tend à avoir un très bon R² Train (proche de 1)
- Normal car le modèle peut "mémoriser" les données
- Ce n'est pas nécessairement du sur-apprentissage si Test est bon aussi

**Test Set** :
- **CRITIQUE** : vrai indicateur de performance
- Si R² Test > 0.7 : bon modèle généralisable
- Si R² Test < 0.5 : modèle faible ou données insuffisantes
- Écart Train-Test < 0.2 : modèle équilibré

#### 4. Utilisation pratique

**Pour optimiser un procédé** :
1. Identifier les top 5-10 variables importantes
2. Analyser leur distribution dans les meilleurs résultats
3. Tester de nouvelles conditions en variant ces facteurs clés

**Pour prédire des performances** :
1. Vérifier R² Test > 0.7
2. S'assurer que les nouvelles conditions sont dans le range des données Train
3. Random Forest prédit mieux que PLS si relations non-linéaires

**Comparer avec PLS** :
- Si RF >> PLS : relations non-linéaires importantes
- Si RF ≈ PLS : relations plutôt linéaires, PLS plus interprétable
- Utiliser les deux pour confirmer les variables importantes

#### 5. Limites et précautions

**Sur-apprentissage** :
- Si R² Train = 1 et R² Test < 0.6 : sur-apprentissage sévère
- Solution : augmenter test_size, limiter max_depth

**Extrapolation** :
- Random Forest ne peut pas extrapoler hors des données d'entraînement
- Les prédictions seront plateaux aux limites des données

**Interprétabilité** :
- Moins interprétable que PLS (boîte noire)
- Importances donnent une idée, mais pas d'équation simple
- Pour comprendre les mécanismes : privilégier PLS ou modèles linéaires
""")
