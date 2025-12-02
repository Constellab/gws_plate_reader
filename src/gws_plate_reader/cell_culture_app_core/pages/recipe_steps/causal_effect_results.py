"""
Causal Effect Results Display Page
"""
import streamlit as st
from gws_core import Scenario, ScenarioProxy, ScenarioStatus
from gws_core.core.utils.settings import Settings
from gws_plate_reader.cell_culture_app_core.cell_culture_state import CellCultureState
from gws_plate_reader.cell_culture_app_core.cell_culture_recipe import CellCultureRecipe


def render_causal_effect_results(recipe: CellCultureRecipe, cell_culture_state: CellCultureState,
                                 causal_scenario: Scenario) -> None:
    """
    Render the Causal Effect results page

    :param recipe: The Recipe instance
    :param cell_culture_state: The cell culture state
    :param causal_scenario: The Causal Effect scenario to display
    """
    st.markdown(f"### 🔗 Résultats Causal Effect")

    st.markdown(f"**Scénario** : {causal_scenario.title}")
    st.markdown(f"**ID** : {causal_scenario.id}")
    st.markdown(f"**Date de création** : {causal_scenario.created_at.strftime('%d/%m/%Y %H:%M:%S')}")

    # Display scenario status
    if causal_scenario.status == ScenarioStatus.SUCCESS:
        st.success(f"✅ Analyse terminée avec succès")
    elif causal_scenario.status == ScenarioStatus.ERROR:
        st.error(f"❌ Erreur lors de l'exécution de l'analyse")
        # Display error message if available
        if causal_scenario.error_info:
            with st.expander("📋 Détails de l'erreur"):
                st.code(causal_scenario.error_info.get('message', 'Aucun message d\'erreur disponible'))
        return
    elif causal_scenario.status.is_running():
        st.info(f"⏳ Analyse en cours d'exécution...")
        st.markdown("Veuillez rafraîchir la page pour voir les résultats une fois l'analyse terminée.")
        return
    else:
        st.warning(f"⚠️ Statut : {causal_scenario.status.name}")
        return

    # If analysis is successful, get the Streamlit app resource
    try:
        causal_scenario_proxy = ScenarioProxy.from_existing_scenario(causal_scenario.id)
        causal_protocol_proxy = causal_scenario_proxy.get_protocol()

        # Get the streamlit_app output resource model
        streamlit_app_resource_model = causal_protocol_proxy.get_output_resource_model('streamlit_app')

        if not streamlit_app_resource_model:
            st.error("⚠️ La ressource Streamlit app n'est pas disponible dans le scénario")
            return

        # Build the URL to the Streamlit app resource
        front_url = Settings.get_front_url()
        resource_url = f"{front_url}/app/resource/{streamlit_app_resource_model.id}"

        st.markdown("---")
        st.markdown("### 📊 Dashboard interactif")

        st.markdown("""
Le dashboard Streamlit interactif vous permet d'explorer les résultats de l'analyse Causal Effect :
- **Heatmaps** : Visualisation matricielle des effets causaux
- **Barplots** : Comparaison des effets par traitement et cible
- **Clustermaps** : Analyse hiérarchique des patterns causaux
- **Filtres interactifs** : Sélection dynamique des variables et combinaisons
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
            f'🚀 Ouvrir le Dashboard Interactif'
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
2. Utilisez les filtres dans la barre latérale pour sélectionner les variables d'intérêt
3. Explorez les différents onglets pour différentes visualisations
4. Les effets causaux sont affichés avec transformation logarithmique pour une meilleure lisibilité

**Interprétation des résultats :**
- **Valeurs positives** : Le traitement augmente la variable cible
- **Valeurs négatives** : Le traitement diminue la variable cible
- **Valeurs proches de zéro** : Pas d'effet causal significatif
            """)

    except Exception as e:
        st.error(f"Erreur lors de la récupération des résultats : {str(e)}")
        import traceback
        st.code(traceback.format_exc())
