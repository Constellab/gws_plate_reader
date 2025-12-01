"""
Metadata Feature UMAP Analysis Step for Cell Culture Dashboard
Allows users to run UMAP analysis on combined metadata and feature extraction data
"""
import streamlit as st
from typing import List, Optional
from datetime import datetime

from gws_core import Scenario, ScenarioProxy, ScenarioCreationType, InputTask, Tag, ScenarioStatus
from gws_core.tag.tag_entity_type import TagEntityType
from gws_core.tag.entity_tag_list import EntityTagList
from gws_core.streamlit import StreamlitAuthenticateUser
from gws_plate_reader.cell_culture_app_core.cell_culture_state import CellCultureState
from gws_plate_reader.cell_culture_app_core.cell_culture_recipe import CellCultureRecipe
from gws_plate_reader.fermentalg_filter import CellCultureMergeFeatureMetadata, CellCulturePrepareFeatureMetadataTable
from gws_design_of_experiments.umap.umap import UMAPTask


def launch_metadata_feature_umap_scenario(
        quality_check_scenario: Scenario,
        cell_culture_state: CellCultureState,
        load_scenario: Scenario,
        feature_extraction_scenario: Scenario,
        medium_name_column: str,
        n_neighbors: int,
        min_dist: float,
        metric: str,
        scale_data: bool,
        n_clusters: Optional[int]) -> Optional[Scenario]:
    """
    Launch a Metadata Feature UMAP analysis scenario

    :param quality_check_scenario: The parent quality check scenario
    :param cell_culture_state: The cell culture state
    :param load_scenario: The load scenario containing metadata_table output
    :param feature_extraction_scenario: The feature extraction scenario containing results_table
    :param medium_name_column: Column name containing medium names for coloring
    :param n_neighbors: Number of neighbors for UMAP
    :param min_dist: Minimum distance for UMAP
    :param metric: Distance metric for UMAP
    :param scale_data: Whether to scale data before UMAP
    :param n_clusters: Number of clusters for K-Means (optional)
    :return: The created scenario or None if error
    """
    try:
        with StreamlitAuthenticateUser():
            # Create a new scenario for Metadata Feature UMAP
            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            scenario_proxy = ScenarioProxy(
                None,
                folder=quality_check_scenario.folder,
                title=f"Metadata Feature UMAP - {timestamp}",
                creation_type=ScenarioCreationType.MANUAL,
            )

            # Get the protocol
            protocol_proxy = scenario_proxy.get_protocol()

            # Get the metadata_table resource model from the load scenario
            load_scenario_proxy = ScenarioProxy.from_existing_scenario(load_scenario.id)
            load_protocol_proxy = load_scenario_proxy.get_protocol()

            metadata_table_resource_model = load_protocol_proxy.get_process(
                cell_culture_state.PROCESS_NAME_DATA_PROCESSING
            ).get_output_resource_model('metadata_table')

            if not metadata_table_resource_model:
                raise ValueError("La sortie 'metadata_table' n'est pas disponible dans le scénario de chargement")

            # Get the results_table from feature extraction scenario
            fe_scenario_proxy = ScenarioProxy.from_existing_scenario(feature_extraction_scenario.id)
            fe_protocol_proxy = fe_scenario_proxy.get_protocol()

            results_table_resource_model = fe_protocol_proxy.get_output_resource_model('results_table')

            if not results_table_resource_model:
                raise ValueError(
                    "La sortie 'results_table' n'est pas disponible dans le scénario d'extraction de caractéristiques")

            # Add input task for metadata_table
            metadata_input_task = protocol_proxy.add_process(
                InputTask, 'metadata_table_input',
                {InputTask.config_name: metadata_table_resource_model.id}
            )

            # Add input task for results_table (features)
            features_input_task = protocol_proxy.add_process(
                InputTask, 'features_table_input',
                {InputTask.config_name: results_table_resource_model.id}
            )

            # Add the Merge task (CellCultureMergeFeatureMetadata)
            merge_task = protocol_proxy.add_process(
                CellCultureMergeFeatureMetadata,
                'merge_feature_metadata_task'
            )

            # Connect inputs to merge task
            protocol_proxy.add_connector(
                out_port=features_input_task >> 'resource',
                in_port=merge_task << 'feature_table'
            )
            protocol_proxy.add_connector(
                out_port=metadata_input_task >> 'resource',
                in_port=merge_task << 'metadata_table'
            )

            # Add the Prepare task (CellCulturePrepareFeatureMetadataTable)
            prepare_task = protocol_proxy.add_process(
                CellCulturePrepareFeatureMetadataTable,
                'prepare_feature_metadata_task'
            )

            # Connect merge output to prepare task
            protocol_proxy.add_connector(
                out_port=merge_task >> 'metadata_feature_table',
                in_port=prepare_task << 'feature_metadata_table'
            )

            # Set prepare task parameters
            prepare_task.set_param('medium_name_column', medium_name_column)

            # Add the UMAP task
            umap_task = protocol_proxy.add_process(
                UMAPTask,
                'metadata_feature_umap_task'
            )

            # Connect the prepared table to the UMAP task
            protocol_proxy.add_connector(
                out_port=prepare_task >> 'ready_feature_metadata_table',
                in_port=umap_task << 'data'
            )

            # Set UMAP parameters
            umap_task.set_param('n_neighbors', n_neighbors)
            umap_task.set_param('min_dist', min_dist)
            umap_task.set_param('metric', metric)
            umap_task.set_param('scale_data', scale_data)
            umap_task.set_param('color_by', medium_name_column)
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
            protocol_proxy.add_output(
                'merged_table',
                merge_task >> 'metadata_feature_table',
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

            # Link to parent feature extraction scenario
            scenario_proxy.add_tag(Tag("parent_feature_extraction_scenario",
                                   feature_extraction_scenario.id, is_propagable=False))

            # Add timestamp and analysis type tags
            scenario_proxy.add_tag(Tag("analysis_timestamp", timestamp, is_propagable=False))
            scenario_proxy.add_tag(Tag("analysis_type", "metadata_feature_umap", is_propagable=False))

            # Add to queue
            scenario_proxy.add_to_queue()

            # Return the new scenario
            new_scenario = scenario_proxy.get_model()
            return new_scenario

    except Exception as e:
        st.error(f"Erreur lors du lancement du scénario Metadata Feature UMAP: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return None


def render_metadata_feature_umap_step(recipe: CellCultureRecipe, cell_culture_state: CellCultureState,
                                      quality_check_scenario: Scenario) -> None:
    """
    Render the Metadata Feature UMAP analysis step

    :param recipe: The Recipe instance
    :param cell_culture_state: The cell culture state
    :param quality_check_scenario: The quality check scenario to analyze
    """
    translate_service = cell_culture_state.get_translate_service()

    st.markdown(f"### 🗺️ Analyse UMAP Métadonnées + Features")

    st.info("L'analyse UMAP combine les données de composition des milieux (métadonnées) avec les caractéristiques extraites des courbes de croissance pour une visualisation intégrée en 2D ou 3D.")

    # Get the load scenario to check for metadata_table output
    load_scenario = recipe.get_load_scenario()

    if not load_scenario:
        st.warning("⚠️ Aucun scénario de chargement de données trouvé. L'analyse UMAP n'est pas disponible.")
        return

    # Check if load scenario has metadata_table output
    try:
        load_scenario_proxy = ScenarioProxy.from_existing_scenario(load_scenario.id)
        load_protocol_proxy = load_scenario_proxy.get_protocol()

        metadata_table_resource_model = load_protocol_proxy.get_process(
            cell_culture_state.PROCESS_NAME_DATA_PROCESSING
        ).get_output_resource_model('metadata_table')

        if not metadata_table_resource_model:
            st.warning(
                "⚠️ La table des métadonnées (metadata_table) n'est pas disponible dans le scénario de chargement.")
            return

        st.success(f"✅ Table des métadonnées disponible : {metadata_table_resource_model.name}")
    except Exception as e:
        st.warning(f"⚠️ Impossible de vérifier la disponibilité de la table des métadonnées : {str(e)}")
        return

    # Get feature extraction scenarios for this quality check
    feature_extraction_scenarios = recipe.get_feature_extraction_scenarios_for_quality_check(quality_check_scenario.id)

    if not feature_extraction_scenarios:
        st.warning(
            "⚠️ Aucun scénario d'extraction de caractéristiques trouvé. Veuillez d'abord exécuter une extraction de caractéristiques.")
        st.info("💡 Allez à l'étape 'Feature Extraction' pour lancer une analyse.")
        return

    # Filter only successful scenarios
    successful_fe_scenarios = [s for s in feature_extraction_scenarios if s.status == ScenarioStatus.SUCCESS]

    if not successful_fe_scenarios:
        st.warning("⚠️ Aucun scénario d'extraction de caractéristiques terminé avec succès.")
        pending_count = len([s for s in feature_extraction_scenarios if s.status.is_finished()])
        if pending_count > 0:
            st.info(f"⏳ {pending_count} scénario(s) en cours d'exécution. Veuillez attendre qu'ils soient terminés.")
        return

    st.markdown(
        f"**Analyses disponibles** : {len(successful_fe_scenarios)} scénario(s) d'extraction de caractéristiques")

    # Select which feature extraction scenario to use
    selected_fe_scenario = None
    if len(successful_fe_scenarios) == 1:
        selected_fe_scenario = successful_fe_scenarios[0]
        st.info(f"📊 Utilisation de : **{selected_fe_scenario.title}**")
    else:
        # Let user choose
        fe_options = {f"{s.title} (ID: {s.id[:8]})": s for s in successful_fe_scenarios}
        selected_fe_key = st.selectbox(
            "Sélectionner le scénario d'extraction de caractéristiques",
            options=list(fe_options.keys())
        )
        selected_fe_scenario = fe_options[selected_fe_key]

    if not selected_fe_scenario:
        return

    # Get available series from metadata table
    try:
        metadata_table = metadata_table_resource_model.get_resource()
        metadata_df = metadata_table.get_data()

        if 'Series' not in metadata_df.columns:
            st.error("⚠️ La colonne 'Series' est manquante dans la table des métadonnées.")
            return

        available_series = sorted(metadata_df['Series'].unique().tolist())
        n_series = len(available_series)

        # Get available columns for medium name
        available_columns = sorted(metadata_df.columns.tolist())

        # Default to 'Medium' if exists, otherwise first non-Series column
        default_medium_column = 'Medium' if 'Medium' in available_columns else (
            [col for col in available_columns if col != 'Series'][0] if len(available_columns) > 1 else 'Medium'
        )

        st.markdown(f"**Séries disponibles** : {n_series}")
        cols_preview = ', '.join(available_columns[:10])
        if len(available_columns) > 10:
            st.markdown(f"**Colonnes disponibles** : {cols_preview}, ... (+{len(available_columns)-10} autres)")
        else:
            st.markdown(f"**Colonnes disponibles** : {cols_preview}")

    except Exception as e:
        st.error(f"Erreur lors de la lecture de la table des métadonnées : {str(e)}")
        return

    # Check existing UMAP scenarios for this feature extraction
    existing_umap_scenarios = recipe.get_metadata_feature_umap_scenarios_for_feature_extraction(selected_fe_scenario.id)

    if existing_umap_scenarios:
        st.markdown(f"**Analyses UMAP existantes** : {len(existing_umap_scenarios)}")
        with st.expander("📊 Voir les analyses UMAP existantes"):
            for idx, umap_scenario in enumerate(existing_umap_scenarios):
                st.write(
                    f"{idx + 1}. {umap_scenario.title} (ID: {umap_scenario.id}) - Statut: {umap_scenario.status.name}")

    # Configuration form for new UMAP
    st.markdown("---")
    st.markdown("### ➕ Lancer une nouvelle analyse UMAP")

    with st.form(key=f"metadata_feature_umap_form_{quality_check_scenario.id}"):
        st.markdown("**Configuration de l'analyse**")

        # Medium column selection
        medium_name_column = st.selectbox(
            "Colonne pour le nom du milieu",
            options=available_columns,
            index=available_columns.index(default_medium_column) if default_medium_column in available_columns else 0,
            help="Colonne contenant les noms de milieux (utilisée pour colorer les points dans UMAP)"
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
                help="Standardiser les données avant UMAP (fortement recommandé car métadonnées et features ont des échelles différentes)"
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
            # Launch UMAP scenario
            umap_scenario = launch_metadata_feature_umap_scenario(
                quality_check_scenario,
                cell_culture_state,
                load_scenario,
                selected_fe_scenario,
                medium_name_column,
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
                recipe.add_metadata_feature_umap_scenario(selected_fe_scenario.id, umap_scenario)

                st.rerun()
            else:
                st.error("❌ Erreur lors du lancement de l'analyse UMAP")

    # Info box with explanation
    with st.expander("💡 Aide sur l'analyse UMAP Métadonnées + Features"):
        st.markdown("### Qu'est-ce que cette analyse ?")
        st.markdown("""
Cette analyse combine deux types de données complémentaires :

1. **Métadonnées** : Composition des milieux de culture (nutriments, concentrations, etc.)
2. **Features** : Paramètres biologiques extraits des courbes de croissance (taux de croissance, phase de latence, etc.)

L'analyse UMAP projette ces données combinées en 2D ou 3D pour révéler les relations entre composition du milieu et performances de croissance.

### Interprétation des résultats

**Graphiques 2D et 3D** :
- Chaque point représente une série (essai/fermenteur)
- La couleur distingue les différents milieux
- Les points proches ont des compositions ET des comportements de croissance similaires
- Les groupes révèlent des combinaisons milieu-performance cohérentes

**Applications** :
- Identifier quelles compositions donnent des performances similaires
- Découvrir des milieux alternatifs avec performances équivalentes
- Optimiser la formulation en reliant composition et résultats
- Détecter des patterns inattendus dans les données

### Paramètres recommandés

Pour l'analyse métadonnées + features :
- **Nombre de voisins** : 10-20 (compromis entre local et global)
- **Distance minimale** : 0.1-0.3
- **Normalisation** : Activée (fortement recommandé car les échelles des métadonnées et features diffèrent)
- **Métrique** : Euclidienne ou corrélation

### Clustering

Le clustering K-Means peut identifier automatiquement des groupes de séries avec profils similaires :
- Utile pour segmenter vos expériences en catégories
- Le nombre optimal de clusters dépend de vos données
- Comparez avec votre connaissance du domaine pour valider
""")
