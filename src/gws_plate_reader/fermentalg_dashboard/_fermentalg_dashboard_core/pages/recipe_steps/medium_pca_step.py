"""
Medium PCA Analysis Step for Fermentalg Dashboard
Allows users to run PCA analysis on medium composition data
"""
import streamlit as st
from typing import List, Optional
from datetime import datetime

from gws_core import Scenario, ScenarioProxy, ScenarioCreationType, InputTask, Tag
from gws_core.tag.tag_entity_type import TagEntityType
from gws_core.tag.entity_tag_list import EntityTagList
from gws_core.streamlit import StreamlitAuthenticateUser
from gws_plate_reader.fermentalg_dashboard._fermentalg_dashboard_core.fermentalg_state import FermentalgState
from gws_plate_reader.fermentalg_dashboard._fermentalg_dashboard_core.fermentalg_recipe import FermentalgRecipe
from gws_plate_reader.fermentalg_analysis import CellCultureMediumPCA


def get_available_media_from_quality_check(
        quality_check_scenario: Scenario, fermentalg_state: FermentalgState) -> List[str]:
    """
    Get list of unique medium names from the quality check scenario's filtered interpolated output

    :param quality_check_scenario: The quality check scenario
    :param fermentalg_state: The fermentalg state
    :return: List of unique medium names
    """
    try:
        # Get the filtered interpolated ResourceSet from quality check
        scenario_proxy = ScenarioProxy.from_existing_scenario(quality_check_scenario.id)
        protocol_proxy = scenario_proxy.get_protocol()

        resource_set = protocol_proxy.get_output(fermentalg_state.QUALITY_CHECK_SCENARIO_INTERPOLATED_OUTPUT_NAME)

        if not resource_set:
            return []

        # Collect unique medium names from tags
        media = set()
        resources = resource_set.get_resources()

        from gws_core.impl.table.table import Table
        for resource in resources.values():
            if isinstance(resource, Table):
                if hasattr(resource, 'tags') and resource.tags:
                    for tag in resource.tags.get_tags():
                        if tag.key == fermentalg_state.TAG_MEDIUM:
                            if tag.value:
                                media.add(tag.value)

        return sorted(list(media))
    except Exception as e:
        # Handle any exception during media extraction
        st.error(f"Erreur lors de l'extraction des milieux : {str(e)}")
        return []


def launch_medium_pca_scenario(
        quality_check_scenario: Scenario,
        fermentalg_state: FermentalgState,
        medium_csv_resource_id: str,
        selected_media: List[str],
        decimal_separator: str = ',') -> Optional[Scenario]:
    """
    Launch a Medium PCA analysis scenario

    :param quality_check_scenario: The parent quality check scenario
    :param fermentalg_state: The fermentalg state
    :param medium_csv_resource_id: Resource model ID of the medium CSV file
    :param selected_media: List of selected medium names to include in analysis
    :param decimal_separator: Decimal separator for CSV (default: ',')
    :return: The created scenario or None if error
    """
    try:
        with StreamlitAuthenticateUser():
            # Create a new scenario for Medium PCA
            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            scenario_proxy = ScenarioProxy(
                None,
                folder=quality_check_scenario.folder,
                title=f"Medium PCA - {timestamp}",
                creation_type=ScenarioCreationType.MANUAL,
            )

            # Get the protocol
            protocol_proxy = scenario_proxy.get_protocol()

            # Add input task for the medium CSV file
            medium_input_task = protocol_proxy.add_process(
                InputTask, 'medium_csv_input',
                {InputTask.config_name: medium_csv_resource_id}
            )

            # Add the Medium PCA task
            pca_task = protocol_proxy.add_process(
                CellCultureMediumPCA,
                'medium_pca_task'
            )

            # Connect the medium CSV file to the PCA task
            protocol_proxy.add_connector(
                out_port=medium_input_task >> 'resource',
                in_port=pca_task << 'medium_csv'
            )

            # Set PCA parameters
            pca_task.set_param('medium_column', 'MILIEU')
            pca_task.set_param('selected_medium', selected_media)
            pca_task.set_param('decimal_separator', decimal_separator)

            # Add outputs
            protocol_proxy.add_output(
                'pca_scores_table',
                pca_task >> 'scores_table',
                flag_resource=True
            )
            protocol_proxy.add_output(
                'pca_scatter_plot',
                pca_task >> 'scatter_plot',
                flag_resource=True
            )
            protocol_proxy.add_output(
                'pca_biplot',
                pca_task >> 'biplot',
                flag_resource=True
            )

            # Inherit tags from parent quality check scenario
            parent_entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, quality_check_scenario.id)

            # Get recipe name from parent
            parent_recipe_name_tags = parent_entity_tag_list.get_tags_by_key(
                fermentalg_state.TAG_FERMENTOR_RECIPE_NAME)
            original_recipe_name = parent_recipe_name_tags[0].tag_value if parent_recipe_name_tags else quality_check_scenario.title

            # Get pipeline ID from parent
            parent_pipeline_id_tags = parent_entity_tag_list.get_tags_by_key(
                fermentalg_state.TAG_FERMENTOR_FERMENTALG_PIPELINE_ID)
            pipeline_id = parent_pipeline_id_tags[0].tag_value if parent_pipeline_id_tags else quality_check_scenario.id

            # Get microplate analysis flag from parent
            parent_microplate_tags = parent_entity_tag_list.get_tags_by_key(fermentalg_state.TAG_MICROPLATE_ANALYSIS)
            microplate_analysis = parent_microplate_tags[0].tag_value if parent_microplate_tags else "false"

            # Classification tag - indicate this is an analysis
            scenario_proxy.add_tag(Tag(fermentalg_state.TAG_FERMENTOR_FERMENTALG,
                                   fermentalg_state.TAG_ANALYSES_PROCESSING, is_propagable=False))

            # Inherit core identification tags
            scenario_proxy.add_tag(Tag(fermentalg_state.TAG_FERMENTOR_RECIPE_NAME,
                                   original_recipe_name, is_propagable=False))
            scenario_proxy.add_tag(Tag(fermentalg_state.TAG_FERMENTOR_FERMENTALG_PIPELINE_ID,
                                   pipeline_id, is_propagable=False))
            scenario_proxy.add_tag(Tag(fermentalg_state.TAG_MICROPLATE_ANALYSIS,
                                   microplate_analysis, is_propagable=False))

            # Link to parent quality check scenario
            scenario_proxy.add_tag(Tag(fermentalg_state.TAG_FERMENTOR_ANALYSES_PARENT_QUALITY_CHECK,
                                   quality_check_scenario.id, is_propagable=False))

            # Add timestamp and analysis type tags
            scenario_proxy.add_tag(Tag("analysis_timestamp", timestamp, is_propagable=False))
            scenario_proxy.add_tag(Tag("analysis_type", "medium_pca", is_propagable=False))

            # Add to queue
            scenario_proxy.add_to_queue()

            # Return the new scenario
            new_scenario = scenario_proxy.get_model()
            return new_scenario

    except Exception as e:
        st.error(f"Erreur lors du lancement du scénario Medium PCA: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return None


def render_medium_pca_step(recipe: FermentalgRecipe, fermentalg_state: FermentalgState,
                           quality_check_scenario: Scenario) -> None:
    """
    Render the Medium PCA analysis step

    :param recipe: The Recipe instance
    :param fermentalg_state: The fermentalg state
    :param quality_check_scenario: The quality check scenario to analyze
    """
    st.markdown("### 🧬 Analyse en Composantes Principales des Milieux")

    st.info(
        "Cette analyse permet d'explorer les similarités et différences entre les compositions "
        "des milieux de culture utilisés pour les couples batch/sample filtrés après Quality Check."
    )

    # Get the medium CSV resource model
    medium_csv_resource_model = fermentalg_state.get_medium_csv_input_resource_model()

    if not medium_csv_resource_model:
        st.warning(
            "⚠️ Aucun fichier CSV de milieu n'a été chargé. Retournez à l'étape de chargement pour uploader le fichier des milieux.")
        return

    st.success(f"✅ Fichier de milieu disponible : {medium_csv_resource_model.name}")

    # Get available media from quality check scenario
    available_media = get_available_media_from_quality_check(quality_check_scenario, fermentalg_state)

    if not available_media:
        st.warning(
            "⚠️ Aucun milieu trouvé dans les données filtrées du Quality Check. Vérifiez que les échantillons ont des tags 'medium'.")
        return

    st.markdown(f"**Milieux disponibles** : {', '.join(available_media)}")

    # Check existing PCA scenarios
    existing_pca_scenarios = recipe.get_medium_pca_scenarios_for_quality_check(quality_check_scenario.id)

    if existing_pca_scenarios:
        st.markdown(f"**Analyses PCA existantes** : {len(existing_pca_scenarios)}")
        with st.expander("📊 Voir les analyses existantes"):
            for idx, pca_scenario in enumerate(existing_pca_scenarios):
                st.write(f"{idx + 1}. {pca_scenario.title} (ID: {pca_scenario.id}) - Status: {pca_scenario.status.name}")

    # Configuration form for new PCA
    st.markdown("---")
    st.markdown("### ➕ Lancer une nouvelle analyse PCA")

    with st.form(key=f"medium_pca_form_{quality_check_scenario.id}"):
        st.markdown("**Sélection des milieux à inclure dans l'analyse**")

        # Multiselect for media selection
        selected_media = st.multiselect(
            "Milieux à analyser",
            options=available_media,
            default=available_media,
            help="Sélectionnez les milieux à inclure dans l'analyse PCA (tous par défaut)"
        )

        # Decimal separator selection
        decimal_separator = st.selectbox(
            "Séparateur décimal du CSV",
            options=[',', '.'],
            index=0,
            help="Séparateur décimal utilisé dans le fichier CSV des milieux"
        )

        # Submit button
        submit_button = st.form_submit_button(
            "🚀 Lancer l'analyse PCA",
            type="primary",
            use_container_width=True
        )

        if submit_button:
            if not selected_media:
                st.error("❌ Veuillez sélectionner au moins un milieu pour l'analyse.")
            else:
                # Launch PCA scenario
                pca_scenario = launch_medium_pca_scenario(
                    quality_check_scenario,
                    fermentalg_state,
                    medium_csv_resource_model.id,
                    selected_media,
                    decimal_separator
                )

                if pca_scenario:
                    st.success(f"✅ Analyse PCA lancée ! ID : {pca_scenario.id}")
                    st.info("ℹ️ Le scénario est en cours d'exécution. Les résultats apparaîtront dans la navigation une fois terminé.")

                    # Add to recipe
                    recipe.add_medium_pca_scenario(quality_check_scenario.id, pca_scenario)

                    st.rerun()
                else:
                    st.error("❌ Erreur lors du lancement de l'analyse PCA.")

    # Info box with PCA explanation
    with st.expander("💡 À propos de l'analyse PCA des milieux"):
        st.markdown("""
        **Analyse en Composantes Principales (PCA)**

        La PCA permet de :
        - Visualiser les similarités entre les compositions des milieux
        - Identifier les composants qui contribuent le plus aux différences
        - Réduire la dimensionnalité des données de composition

        **Sorties générées :**
        1. **Table des Scores** : Coordonnées de chaque milieu dans l'espace PCA
        2. **Scatter Plot** : Projection des milieux sur PC1 vs PC2
        3. **Biplot** : Combine échantillons et variables (composants du milieu)

        **Utilisation :**
        - Sélectionnez les milieux que vous souhaitez comparer
        - Les milieux similaires seront regroupés dans le scatter plot
        - Le biplot montre quels composants différencient les milieux
        """)
