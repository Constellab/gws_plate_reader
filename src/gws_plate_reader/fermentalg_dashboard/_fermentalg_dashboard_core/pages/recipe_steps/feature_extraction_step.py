"""
Feature Extraction Step for Fermentalg Dashboard
Allows users to run growth curve feature extraction analysis on quality check data
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
from gws_plate_reader.fermentalg_analysis import ResourceSetToDataTable, CellCultureFeatureExtraction


def get_available_columns_from_quality_check(quality_check_scenario: Scenario,
                                             fermentalg_state: FermentalgState,
                                             index_only: bool = False) -> List[str]:
    """
    Get list of available columns from the quality check scenario's output

    :param quality_check_scenario: The quality check scenario
    :param fermentalg_state: The fermentalg state
    :param index_only: If True, return only columns with is_index_column=true tag (strict filtering)
    :return: List of column names
    """
    try:
        # Get the ResourceSet from quality check (non-interpolated data)
        resource_set_resource_model = fermentalg_state.get_quality_check_scenario_output_resource_model(
            quality_check_scenario)
        resource_set = resource_set_resource_model.get_resource() if resource_set_resource_model else None

        if not resource_set:
            return []

        # Get columns based on filter
        if index_only:
            # Use strict filtering for index columns (only is_index_column=true)
            return fermentalg_state.get_strict_index_columns_from_resource_set(resource_set)
        else:
            return fermentalg_state.get_data_columns_from_resource_set(resource_set)

    except Exception as e:
        st.error(f"Erreur lors de l'extraction des colonnes : {str(e)}")
        return []


def launch_feature_extraction_scenario(
        quality_check_scenario: Scenario,
        fermentalg_state: FermentalgState,
        index_column: str,
        data_column: str,
        models_to_fit: List[str]) -> Optional[Scenario]:
    """
    Launch a Feature Extraction analysis scenario

    :param quality_check_scenario: The parent quality check scenario
    :param fermentalg_state: The fermentalg state
    :param index_column: Column to use as index (time/temp)
    :param data_column: Data column to analyze
    :param models_to_fit: List of models to fit
    :return: The created scenario or None if error
    """
    try:
        with StreamlitAuthenticateUser():
            # Create a new scenario for Feature Extraction
            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            scenario_title = f"Feature Extraction - {data_column} - {timestamp}"

            scenario_proxy = ScenarioProxy(
                None,
                folder=quality_check_scenario.folder,
                title=scenario_title,
                creation_type=ScenarioCreationType.MANUAL,
            )

            # Get the protocol
            protocol_proxy = scenario_proxy.get_protocol()

            # Get the quality check output ResourceSet
            qc_output = fermentalg_state.get_quality_check_scenario_output_resource_model(quality_check_scenario)
            if not qc_output:
                st.error("Impossible de récupérer le ResourceSet de sortie du Quality Check")
                return None

            # Add input task for the ResourceSet
            resource_set_input_task = protocol_proxy.add_process(
                InputTask, 'resource_set_input',
                {InputTask.config_name: qc_output.id}
            )

            # Add ResourceSetToDataTable task
            rs_to_table_task = protocol_proxy.add_process(
                ResourceSetToDataTable,
                'resource_set_to_table'
            )

            # Connect ResourceSet to converter task
            protocol_proxy.add_connector(
                out_port=resource_set_input_task >> 'resource',
                in_port=rs_to_table_task << 'resource_set'
            )

            # Set converter parameters
            rs_to_table_task.set_param('index_column', index_column)
            rs_to_table_task.set_param('data_column', data_column)

            # Add Feature Extraction task
            feature_extraction_task = protocol_proxy.add_process(
                CellCultureFeatureExtraction,
                'feature_extraction_task'
            )

            # Connect table to feature extraction
            protocol_proxy.add_connector(
                out_port=rs_to_table_task >> 'data_table',
                in_port=feature_extraction_task << 'data_table'
            )

            # Set feature extraction parameters
            feature_extraction_task.set_param('models_to_fit', models_to_fit)

            # Add outputs
            protocol_proxy.add_output(
                'results_table',
                feature_extraction_task >> 'results_table',
                flag_resource=True
            )
            protocol_proxy.add_output(
                'plots',
                feature_extraction_task >> 'plots',
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

            # Add analysis type and column tags
            scenario_proxy.add_tag(Tag("analysis_type", "feature_extraction", is_propagable=False))
            scenario_proxy.add_tag(Tag("analysis_timestamp", timestamp, is_propagable=False))
            scenario_proxy.add_tag(Tag("data_column", data_column, is_propagable=False))
            scenario_proxy.add_tag(Tag("index_column", index_column, is_propagable=False))

            # Add to queue
            scenario_proxy.add_to_queue()

            # Return the new scenario
            new_scenario = scenario_proxy.get_model()
            return new_scenario

    except Exception as e:
        st.error(f"Erreur lors du lancement du scénario Feature Extraction: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return None


def render_feature_extraction_step(recipe: FermentalgRecipe, fermentalg_state: FermentalgState,
                                   quality_check_scenario: Scenario) -> None:
    """
    Render the Feature Extraction analysis step

    :param recipe: The Recipe instance
    :param fermentalg_state: The fermentalg state
    :param quality_check_scenario: The quality check scenario to analyze
    """
    st.markdown("### 📈 Extraction de Caractéristiques (Growth Curve Fitting)")

    st.info(
        "Cette analyse ajuste plusieurs modèles de croissance sigmoidaux aux données de culture cellulaire "
        "et extrait des paramètres biologiques clés (taux de croissance, temps de latence, etc.)."
    )

    # Get the quality check output
    qc_output = fermentalg_state.get_quality_check_scenario_output_resource_model(quality_check_scenario)
    qc_output_resource_set = qc_output.get_resource() if qc_output else None

    if not qc_output_resource_set:
        st.warning("⚠️ Impossible de récupérer les données du Quality Check.")
        return

    st.success(f"✅ Données Quality Check disponibles : {len(qc_output_resource_set.get_resources())} ressources")

    # Get available columns
    index_columns = get_available_columns_from_quality_check(quality_check_scenario, fermentalg_state, index_only=True)
    data_columns = get_available_columns_from_quality_check(quality_check_scenario, fermentalg_state, index_only=False)

    if not index_columns:
        st.warning("⚠️ Aucune colonne d'index (temps/température) trouvée dans les données.")
        return

    if not data_columns:
        st.warning("⚠️ Aucune colonne de données trouvée dans les données.")
        return

    st.markdown(f"**Colonnes d'index disponibles** : {', '.join(index_columns)}")
    st.markdown(f"**Colonnes de données disponibles** : {', '.join(data_columns)}")

    # Check existing feature extraction scenarios
    existing_fe_scenarios = recipe.get_feature_extraction_scenarios_for_quality_check(quality_check_scenario.id)

    if existing_fe_scenarios:
        st.markdown(f"**Analyses Feature Extraction existantes** : {len(existing_fe_scenarios)}")
        with st.expander("📊 Voir les analyses existantes"):
            for idx, fe_scenario in enumerate(existing_fe_scenarios):
                # Extract data column from tags
                entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, fe_scenario.id)
                data_col_tags = entity_tag_list.get_tags_by_key("data_column")
                data_col = data_col_tags[0].tag_value if data_col_tags else "N/A"

                st.write(f"{idx + 1}. {fe_scenario.title} - Colonne: **{data_col}** (Status: {fe_scenario.status.name})")

    # Configuration form for new Feature Extraction
    st.markdown("---")
    st.markdown("### ➕ Lancer une nouvelle analyse Feature Extraction")

    # Available models
    all_models = [
        "Logistic_4P",
        "Gompertz_4P",
        "ModifiedGompertz_4P",
        "Richards_5P",
        "WeibullSigmoid_4P",
        "BaranyiRoberts_4P"
    ]

    with st.form(key=f"feature_extraction_form_{quality_check_scenario.id}"):
        st.markdown("**Configuration de l'analyse**")

        # Index column selection
        index_column = st.selectbox(
            "Colonne d'index (temps/température)",
            options=index_columns,
            index=0,
            help="Colonne à utiliser comme axe X (généralement le temps ou la température)"
        )

        # Data columns multiselect
        selected_data_columns = st.multiselect(
            "Colonne(s) de données à analyser",
            options=data_columns,
            default=[],
            help="Sélectionnez une ou plusieurs colonnes à analyser. Un scénario sera créé pour chaque colonne."
        )

        # Models multiselect
        selected_models = st.multiselect(
            "Modèles de croissance à tester",
            options=all_models,
            default=all_models,
            help="Sélectionnez les modèles sigmoidaux à ajuster aux données"
        )

        # Info about multiple columns
        if len(selected_data_columns) > 1:
            st.info(f"ℹ️ {len(selected_data_columns)} scénarios seront créés (un par colonne de données)")

        # Submit button
        submit_button = st.form_submit_button(
            "🚀 Lancer l'analyse Feature Extraction",
            type="primary",
            use_container_width=True
        )

        if submit_button:
            if not selected_data_columns:
                st.error("❌ Veuillez sélectionner au moins une colonne de données à analyser.")
            elif not selected_models:
                st.error("❌ Veuillez sélectionner au moins un modèle de croissance.")
            else:
                # Launch scenarios
                created_scenarios = []

                progress_bar = st.progress(0, text="Création des scénarios...")

                for idx, data_column in enumerate(selected_data_columns):
                    progress = (idx + 1) / len(selected_data_columns)
                    progress_bar.progress(progress, text=f"Création du scénario pour {data_column}...")

                    fe_scenario = launch_feature_extraction_scenario(
                        quality_check_scenario,
                        fermentalg_state,
                        index_column,
                        data_column,
                        selected_models
                    )

                    if fe_scenario:
                        created_scenarios.append(fe_scenario)
                        # Add to recipe
                        recipe.add_feature_extraction_scenario(quality_check_scenario.id, fe_scenario)

                progress_bar.empty()

                if created_scenarios:
                    st.success(f"✅ {len(created_scenarios)} scénario(s) Feature Extraction lancé(s) !")
                    st.info(
                        "ℹ️ Les scénarios sont en cours d'exécution. Les résultats apparaîtront dans la navigation une fois terminés.")
                    st.rerun()
                else:
                    st.error("❌ Erreur lors de la création des scénarios.")

    # Info box with Feature Extraction explanation
    with st.expander("💡 À propos de l'analyse Feature Extraction"):
        st.markdown("""
        **Extraction de Caractéristiques (Growth Curve Fitting)**

        Cette analyse ajuste plusieurs modèles de croissance sigmoidaux aux courbes de culture cellulaire
        pour extraire des paramètres biologiques quantitatifs.

        **Modèles disponibles (6) :**
        1. **Logistic 4P** : Modèle logistique classique
        2. **Gompertz 4P** : Croissance asymétrique avec phase de latence
        3. **Modified Gompertz 4P** : Formulation alternative du Gompertz
        4. **Richards 5P** : Logistique généralisée avec paramètre de forme
        5. **Weibull Sigmoid 4P** : Courbe de croissance basée sur Weibull
        6. **Baranyi-Roberts 4P** : Modèle de croissance microbienne

        **Paramètres extraits :**
        - **Paramètres du modèle** : y0 (valeur initiale), A (asymptote), μ (taux de croissance), lag (phase de latence)
        - **Métriques statistiques** : R², AIC, BIC, RMSE, MAE
        - **Intervalles de croissance** : t5, t10, t20, t50, t80, t90, t95 (temps à % d'amplitude)
        - **Caractéristiques dynamiques** : slope_max (taux de croissance max), doubling_time (temps de doublement)

        **Sorties générées :**
        1. **Table de résultats** : Tous les paramètres, métriques et intervalles pour chaque modèle
        2. **Graphiques** : ResourceSet contenant les courbes ajustées et comparaisons

        **Notes :**
        - Optimisation multi-départ (10 points initiaux) pour robustesse
        - Intervalles de confiance à 95% pour tous les paramètres
        - Fonction de perte soft_l1 pour gérer les valeurs aberrantes
        """)
