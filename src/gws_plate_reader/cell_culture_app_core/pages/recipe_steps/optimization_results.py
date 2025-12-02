"""
Optimization Results Page for Cell Culture Dashboard
Displays the results of an Optimization analysis scenario
"""
import streamlit as st
from gws_core import Scenario, ScenarioProxy, ScenarioStatus, Settings
from gws_plate_reader.cell_culture_app_core.cell_culture_state import CellCultureState


def render_optimization_results(cell_culture_state: CellCultureState, optimization_scenario: Scenario) -> None:
    """
    Render the Optimization analysis results page

    :param cell_culture_state: The cell culture state
    :param optimization_scenario: The Optimization scenario to display results for
    """
    translate_service = cell_culture_state.get_translate_service()

    st.markdown(f"### ⚙️ Résultats de l'analyse Optimization")

    st.markdown(f"**Scénario** : {optimization_scenario.title}")
    st.markdown(f"**ID** : `{optimization_scenario.id}`")

    # Display scenario status
    status = optimization_scenario.status
    if status == ScenarioStatus.SUCCESS:
        st.success(f"✅ **Statut** : Terminé avec succès")
    elif status == ScenarioStatus.ERROR:
        st.error(f"❌ **Statut** : Erreur lors de l'exécution")

        # Display error details if available
        try:
            scenario_proxy = ScenarioProxy.from_existing_scenario(optimization_scenario.id)
            protocol_proxy = scenario_proxy.get_protocol()

            # Try to get error from the protocol
            if protocol_proxy:
                st.error("**Détails de l'erreur** :")
                st.code(protocol_proxy.get_error_message() if hasattr(
                    protocol_proxy, 'get_error_message') else "Erreur inconnue")
        except Exception as e:
            st.warning(f"Impossible de récupérer les détails de l'erreur : {str(e)}")

        return
    elif status == ScenarioStatus.RUNNING or status == ScenarioStatus.IN_QUEUE:
        st.info(f"⏳ **Statut** : En cours d'exécution...")
        st.markdown("L'analyse est en cours. Actualisez cette page pour voir les résultats une fois terminée.")

        if st.button("🔄 Actualiser", key=f"refresh_optimization_{optimization_scenario.id}"):
            st.rerun()

        return
    else:
        st.warning(f"⚠️ **Statut** : {status.name}")
        return

    # Get the Streamlit app resource from scenario output
    try:
        scenario_proxy = ScenarioProxy.from_existing_scenario(optimization_scenario.id)
        protocol_proxy = scenario_proxy.get_protocol()

        streamlit_app_resource_model = protocol_proxy.get_output_resource_model('streamlit_app')

        if not streamlit_app_resource_model:
            st.warning("⚠️ La ressource de dashboard Streamlit n'est pas encore disponible.")
            return

        # Build the URL to the Streamlit app resource
        front_url = Settings.get_front_url()
        resource_url = f"{front_url}/app/resource/{streamlit_app_resource_model.id}"

        st.success("✅ Le dashboard d'optimisation est disponible !")

        st.markdown("---")
        st.markdown("### 📊 Dashboard interactif")

        st.markdown("""
Le dashboard Streamlit interactif vous permet d'explorer les résultats de l'analyse Optimization :
- **Summary** : Meilleure solution trouvée et métriques
- **3D Surface Explorer** : Exploration interactive de l'espace de recherche
- **Feature Importance** : Importance des variables dans le modèle
- **Observed vs Predicted** : Validation du modèle prédictif
- **Data Explorer** : Toutes les solutions trouvées
        """)

        # Button to open the Streamlit app
        st.markdown(
            f'<a href="{resource_url}" target="_blank">'
            f'<button style="'
            f'background-color: #FF4B4B; '
            f'color: white; '
            f'padding: 0.5rem 1rem; '
            f'border: none; '
            f'border-radius: 0.25rem; '
            f'cursor: pointer; '
            f'font-size: 1rem; '
            f'font-weight: 600; '
            f'width: 100%;'
            f'">'
            f'🚀 Ouvrir le Dashboard Optimization'
            f'</button>'
            f'</a>',
            unsafe_allow_html=True
        )

        st.markdown("---")

        # Additional info
        with st.expander("ℹ️ Informations sur les résultats"):
            st.markdown(f"""
**Ressource ID** : `{streamlit_app_resource_model.id}`

**Comment utiliser le dashboard :**
1. Cliquez sur le bouton ci-dessus pour ouvrir le dashboard dans un nouvel onglet
2. Explorez les solutions optimales proposées
3. Visualisez les compromis entre différents objectifs avec le 3D Surface Explorer
4. Identifiez les paramètres optimaux pour votre application

**Interprétation des résultats :**
- **Best Solution** : Valeurs optimales trouvées pour chaque variable d'entrée
- **Feature Importance** : Importance relative de chaque variable
- **Observed vs Predicted** : Validation croisée du modèle (R² score)
- **Data Explorer** : Tableau complet de toutes les solutions trouvées
            """)

    except Exception as e:
        st.error(f"Erreur lors de la récupération des résultats : {str(e)}")
        import traceback
        st.code(traceback.format_exc())

    # Help section
    with st.expander("💡 Aide sur les résultats"):
        st.markdown("""
### Interprétation des résultats

**Best Solution** :
- Valeurs optimales trouvées pour chaque variable d'entrée
- Prédictions pour chaque variable cible
- Score de fitness global

**3D Surface Explorer** :
- Visualisation de la surface de réponse
- Interaction avec les axes pour explorer différentes perspectives
- Points rouges = solutions générées

**Feature Importance** :
- Importance relative de chaque variable d'entrée
- Basé sur le modèle Random Forest/XGBoost/CatBoost
- Plus la valeur est élevée, plus la variable est importante

**Observed vs Predicted** :
- Validation croisée du modèle prédictif
- Points alignés sur la diagonale = bonnes prédictions
- R² score indique la qualité du modèle

**Data Explorer** :
- Tableau complet de toutes les solutions trouvées
- Tri et filtrage interactifs
- Export CSV possible

### Actions possibles

1. **Analyser les solutions** : Identifier les conditions optimales
2. **Valider les prédictions** : Vérifier le R² et les graphiques
3. **Explorer l'espace** : Utiliser le 3D Surface Explorer
4. **Exporter les données** : Télécharger les CSV depuis le dashboard
5. **Réitérer** : Lancer une nouvelle optimisation avec des contraintes ajustées
        """)
