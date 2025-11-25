"""
Medium UMAP Analysis Step for Cell Culture Dashboard
Allows users to run UMAP analysis on medium composition data
"""
import streamlit as st
from typing import List, Optional
from datetime import datetime

from gws_core import Scenario, ScenarioProxy, ScenarioCreationType, InputTask, Tag
from gws_core.tag.tag_entity_type import TagEntityType
from gws_core.tag.entity_tag_list import EntityTagList
from gws_core.streamlit import StreamlitAuthenticateUser
from gws_plate_reader.cell_culture_app_core.cell_culture_state import CellCultureState
from gws_plate_reader.cell_culture_app_core.cell_culture_recipe import CellCultureRecipe
from gws_plate_reader.fermentalg_analysis import CellCultureMediumTableFilter
from gws_design_of_experiments.umap.umap import UMAPTask


def get_available_media_from_quality_check(
        quality_check_scenario: Scenario, cell_culture_state: CellCultureState) -> List[str]:
    """
    Get list of unique medium names from the quality check scenario's filtered interpolated output

    :param quality_check_scenario: The quality check scenario
    :param cell_culture_state: The cell culture state
    :return: List of unique medium names
    """
    try:
        # Get the filtered interpolated ResourceSet from quality check
        scenario_proxy = ScenarioProxy.from_existing_scenario(quality_check_scenario.id)
        protocol_proxy = scenario_proxy.get_protocol()

        resource_set = protocol_proxy.get_output(cell_culture_state.QUALITY_CHECK_SCENARIO_INTERPOLATED_OUTPUT_NAME)

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
                        if tag.key == cell_culture_state.TAG_MEDIUM:
                            if tag.value:
                                media.add(tag.value)

        return sorted(list(media))
    except Exception as e:
        # Handle any exception during media extraction
        st.error(f"Erreur lors de l'extraction des milieux : {str(e)}")
        return []


def launch_medium_umap_scenario(
        quality_check_scenario: Scenario,
        cell_culture_state: CellCultureState,
        load_scenario: Scenario,
        selected_media: List[str],
        n_neighbors: int,
        min_dist: float,
        metric: str,
        scale_data: bool,
        n_clusters: Optional[int]) -> Optional[Scenario]:
    """
    Launch a Medium UMAP analysis scenario

    :param quality_check_scenario: The parent quality check scenario
    :param cell_culture_state: The cell culture state
    :param load_scenario: The load scenario containing medium_table output
    :param selected_media: List of selected medium names to include in analysis
    :param n_neighbors: Number of neighbors for UMAP
    :param min_dist: Minimum distance for UMAP
    :param metric: Distance metric for UMAP
    :param scale_data: Whether to scale data before UMAP
    :param n_clusters: Number of clusters for K-Means (optional)
    :return: The created scenario or None if error
    """
    try:
        with StreamlitAuthenticateUser():
            # Create a new scenario for Medium UMAP
            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            scenario_proxy = ScenarioProxy(
                None,
                folder=quality_check_scenario.folder,
                title=f"Medium UMAP - {timestamp}",
                creation_type=ScenarioCreationType.MANUAL,
            )

            # Get the protocol
            protocol_proxy = scenario_proxy.get_protocol()

            # Get the load scenario protocol to access its medium_table output
            load_scenario_proxy = ScenarioProxy.from_existing_scenario(load_scenario.id)
            load_protocol_proxy = load_scenario_proxy.get_protocol()

            # Get the medium_table resource model from the load scenario's process
            medium_table_resource_model = load_protocol_proxy.get_process(
                cell_culture_state.PROCESS_NAME_DATA_PROCESSING
            ).get_output_resource_model('medium_table')

            if not medium_table_resource_model:
                raise ValueError("La sortie 'medium_table' n'est pas disponible dans le scénario de chargement")

            # Add input task for the medium_table from load scenario
            medium_input_task = protocol_proxy.add_process(
                InputTask, 'medium_table_input',
                {InputTask.config_name: medium_table_resource_model.id}
            )

            # Add the Medium Table Filter task
            filter_task = protocol_proxy.add_process(
                CellCultureMediumTableFilter,
                'medium_filter_task'
            )

            # Connect input to filter
            protocol_proxy.add_connector(
                out_port=medium_input_task >> 'resource',
                in_port=filter_task << 'medium_table'
            )

            # Set filter parameters
            filter_task.set_param('medium_column', 'MILIEU')
            filter_task.set_param('selected_medium', selected_media)

            # Add the UMAP task
            umap_task = protocol_proxy.add_process(
                UMAPTask,
                'medium_umap_task'
            )

            # Connect the filtered table to the UMAP task
            protocol_proxy.add_connector(
                out_port=filter_task >> 'filtered_table',
                in_port=umap_task << 'data'
            )

            # Set UMAP parameters
            umap_task.set_param('n_neighbors', n_neighbors)
            umap_task.set_param('min_dist', min_dist)
            umap_task.set_param('metric', metric)
            umap_task.set_param('scale_data', scale_data)
            umap_task.set_param('color_by', 'MILIEU')
            if n_clusters is not None:
                umap_task.set_param('n_clusters', n_clusters)

            # Add outputs
            protocol_proxy.add_output(
                'umap_2d_plot',
                umap_task >> 'umap_2d_plot',
                flag_resource=True
            )
            protocol_proxy.add_output(
                'umap_3d_plot',
                umap_task >> 'umap_3d_plot',
                flag_resource=True
            )
            protocol_proxy.add_output(
                'umap_2d_table',
                umap_task >> 'umap_2d_table',
                flag_resource=True
            )
            protocol_proxy.add_output(
                'umap_3d_table',
                umap_task >> 'umap_3d_table',
                flag_resource=True
            )

            # Inherit tags from parent quality check scenario
            parent_entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, quality_check_scenario.id)

            # Get recipe name from parent
            parent_recipe_name_tags = parent_entity_tag_list.get_tags_by_key(
                cell_culture_state.TAG_FERMENTOR_RECIPE_NAME)
            original_recipe_name = parent_recipe_name_tags[0].tag_value if parent_recipe_name_tags else quality_check_scenario.title

            # Get pipeline ID from parent
            parent_pipeline_id_tags = parent_entity_tag_list.get_tags_by_key(
                cell_culture_state.TAG_FERMENTOR_PIPELINE_ID)
            pipeline_id = parent_pipeline_id_tags[0].tag_value if parent_pipeline_id_tags else quality_check_scenario.id

            # Get microplate analysis flag from parent
            parent_microplate_tags = parent_entity_tag_list.get_tags_by_key(cell_culture_state.TAG_MICROPLATE_ANALYSIS)
            microplate_analysis = parent_microplate_tags[0].tag_value if parent_microplate_tags else "false"

            # Classification tag - indicate this is an analysis
            scenario_proxy.add_tag(Tag(cell_culture_state.TAG_FERMENTOR,
                                   cell_culture_state.TAG_ANALYSES_PROCESSING, is_propagable=False))

            # Inherit core identification tags
            scenario_proxy.add_tag(Tag(cell_culture_state.TAG_FERMENTOR_RECIPE_NAME,
                                   original_recipe_name, is_propagable=False))
            scenario_proxy.add_tag(Tag(cell_culture_state.TAG_FERMENTOR_PIPELINE_ID,
                                   pipeline_id, is_propagable=False))
            scenario_proxy.add_tag(Tag(cell_culture_state.TAG_MICROPLATE_ANALYSIS,
                                   microplate_analysis, is_propagable=False))

            # Link to parent quality check scenario
            scenario_proxy.add_tag(Tag(cell_culture_state.TAG_FERMENTOR_ANALYSES_PARENT_QUALITY_CHECK,
                                   quality_check_scenario.id, is_propagable=False))

            # Add timestamp and analysis type tags
            scenario_proxy.add_tag(Tag("analysis_timestamp", timestamp, is_propagable=False))
            scenario_proxy.add_tag(Tag("analysis_type", "medium_umap", is_propagable=False))

            # Add to queue
            scenario_proxy.add_to_queue()

            # Return the new scenario
            new_scenario = scenario_proxy.get_model()
            return new_scenario

    except Exception as e:
        st.error(f"Erreur lors du lancement du scénario Medium UMAP: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return None


def render_medium_umap_step(recipe: CellCultureRecipe, cell_culture_state: CellCultureState,
                            quality_check_scenario: Scenario) -> None:
    """
    Render the Medium UMAP analysis step

    :param recipe: The Recipe instance
    :param cell_culture_state: The cell culture state
    :param quality_check_scenario: The quality check scenario to analyze
    """
    translate_service = cell_culture_state.get_translate_service()

    st.markdown(f"### 🗺️ Analyse UMAP des Milieux")

    st.info("L'analyse UMAP (Uniform Manifold Approximation and Projection) permet de visualiser les données de composition des milieux en 2D ou 3D, révélant des structures et groupes de milieux similaires.")

    # Get the load scenario to check for medium_table output
    load_scenario = recipe.get_load_scenario()

    if not load_scenario:
        st.warning("⚠️ Aucun scénario de chargement de données trouvé. L'analyse UMAP n'est pas disponible.")
        return

    # Check if load scenario has medium_table output
    try:
        load_scenario_proxy = ScenarioProxy.from_existing_scenario(load_scenario.id)
        load_protocol_proxy = load_scenario_proxy.get_protocol()

        # Get the medium_table resource model from the load process
        medium_table_resource_model = load_protocol_proxy.get_process(
            cell_culture_state.PROCESS_NAME_DATA_PROCESSING
        ).get_output_resource_model('medium_table')

        if not medium_table_resource_model:
            st.warning(
                "⚠️ La table des milieux (medium_table) n'est pas disponible dans le scénario de chargement. L'analyse UMAP n'est pas disponible.")
            st.info("💡 Assurez-vous que le scénario de chargement a été exécuté avec succès et qu'il produit une sortie 'medium_table'.")
            return

        st.success(f"✅ Table des milieux disponible : {medium_table_resource_model.name}")
    except Exception as e:
        st.warning(f"⚠️ Impossible de vérifier la disponibilité de la table des milieux : {str(e)}")
        return

    # Get available media from quality check scenario
    available_media = get_available_media_from_quality_check(quality_check_scenario, cell_culture_state)

    if not available_media:
        st.warning("⚠️ Aucun milieu trouvé dans le scénario de contrôle qualité.")
        return

    st.markdown(f"**Milieux disponibles** : {', '.join(available_media)}")

    # Check existing UMAP scenarios
    existing_umap_scenarios = recipe.get_medium_umap_scenarios_for_quality_check(quality_check_scenario.id)

    if existing_umap_scenarios:
        st.markdown(f"**Analyses UMAP existantes** : {len(existing_umap_scenarios)}")
        with st.expander(f"📊 Voir les analyses UMAP existantes"):
            for idx, umap_scenario in enumerate(existing_umap_scenarios):
                st.write(
                    f"{idx + 1}. {umap_scenario.title} (ID: {umap_scenario.id}) - Statut: {umap_scenario.status.name}")

    # Configuration form for new UMAP
    st.markdown("---")
    st.markdown(f"### ➕ Lancer une nouvelle analyse UMAP")

    with st.form(key=f"medium_umap_form_{quality_check_scenario.id}"):
        st.markdown(f"**Sélection des milieux**")

        # Multiselect for media selection
        selected_media = st.multiselect(
            "Milieux à inclure",
            options=available_media,
            default=available_media,
            help="Sélectionner les milieux à inclure dans l'analyse UMAP"
        )

        st.markdown("**Paramètres UMAP**")

        col1, col2 = st.columns(2)

        with col1:
            n_neighbors = st.slider(
                "Nombre de voisins",
                min_value=2,
                max_value=50,
                value=15,
                help="Contrôle l'équilibre entre structure locale et globale (plus élevé = structure plus globale)"
            )

            metric = st.selectbox(
                "Métrique de distance",
                options=["euclidean", "manhattan", "cosine", "correlation"],
                index=0,
                help="Métrique pour calculer la distance entre points"
            )

        with col2:
            min_dist = st.slider(
                "Distance minimale",
                min_value=0.0,
                max_value=0.99,
                value=0.1,
                step=0.05,
                help="Distance minimale entre points dans l'espace réduit (plus faible = points plus groupés)"
            )

            scale_data = st.checkbox(
                "Normaliser les données",
                value=True,
                help="Standardiser les données avant UMAP (recommandé)"
            )

        st.markdown("**Clustering (optionnel)**")
        enable_clustering = st.checkbox("Activer le clustering K-Means", value=False)
        n_clusters = None
        if enable_clustering:
            n_clusters = st.slider(
                "Nombre de clusters",
                min_value=2,
                max_value=10,
                value=3,
                help="Nombre de groupes à identifier"
            )

        # Submit button
        submit_button = st.form_submit_button(
            f"🚀 Lancer l'analyse UMAP",
            type="primary",
            use_container_width=True
        )

        if submit_button:
            if not selected_media:
                st.error("⚠️ Veuillez sélectionner au moins un milieu")
            else:
                # Launch UMAP scenario
                umap_scenario = launch_medium_umap_scenario(
                    quality_check_scenario,
                    cell_culture_state,
                    load_scenario,
                    selected_media,
                    n_neighbors,
                    min_dist,
                    metric,
                    scale_data,
                    n_clusters
                )

                if umap_scenario:
                    st.success(f"✅ Analyse UMAP lancée avec succès ! ID : {umap_scenario.id}")
                    st.info("⏳ L'analyse est en cours d'exécution...")

                    # Add to recipe
                    recipe.add_medium_umap_scenario(quality_check_scenario.id, umap_scenario)

                    st.rerun()
                else:
                    st.error("❌ Erreur lors du lancement de l'analyse UMAP")

    # Info box with UMAP explanation
    with st.expander(f"💡 Aide sur l'analyse UMAP"):
        st.markdown(f"### Qu'est-ce que UMAP ?")
        st.markdown("""
UMAP (Uniform Manifold Approximation and Projection) est une technique de réduction de dimensionnalité qui permet de visualiser des données complexes en 2D ou 3D.

### Interprétation des résultats

**Graphiques 2D et 3D** :
- Chaque point représente un milieu
- Les milieux proches ont des compositions similaires
- Les groupes de points indiquent des familles de milieux apparentés
- La couleur distingue les différents milieux (ou clusters si activés)

**Paramètres clés** :
- **Nombre de voisins** : Plus élevé préserve la structure globale, plus faible préserve la structure locale
- **Distance minimale** : Contrôle la dispersion des points (faible = groupes serrés, élevé = dispersion)
- **Métrique** : Euclidienne pour les données numériques générales, cosinus pour les proportions

**Clustering** :
- Identifie automatiquement des groupes de milieux similaires
- Utile pour découvrir des catégories naturelles dans vos données
- Le nombre de clusters doit être choisi en fonction de vos connaissances du domaine

### Conseils d'utilisation
- Commencez avec les paramètres par défaut
- Ajustez le nombre de voisins si vous voulez voir plus de structure locale ou globale
- Activez le clustering pour identifier des familles de milieux
- Comparez les résultats 2D et 3D pour une meilleure compréhension
""")
