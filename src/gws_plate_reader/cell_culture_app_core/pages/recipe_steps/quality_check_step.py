"""
Quality Check Step for Cell Culture Dashboard
Handles quality check configuration and scenario launching for selections
"""
import streamlit as st
from datetime import datetime
from typing import Optional, List, Dict

from gws_core import Scenario, ScenarioProxy, ScenarioCreationType, InputTask, Tag
from gws_core.tag.tag_entity_type import TagEntityType
from gws_core.tag.entity_tag_list import EntityTagList
from gws_core.streamlit import StreamlitAuthenticateUser
from gws_core.impl.table.table import Table
from gws_plate_reader.cell_culture_app_core.cell_culture_state import CellCultureState
from gws_plate_reader.cell_culture_app_core.cell_culture_recipe import CellCultureRecipe
from gws_plate_reader.fermentalg_filter import FermentalgQualityCheck


def get_available_columns_from_selection(selection_scenario: Scenario, cell_culture_state: CellCultureState) -> List[str]:
    """Get list of available numeric columns from a selection scenario's interpolated output"""
    try:
        # Get interpolated ResourceSet from selection scenario using state method
        resource_set = cell_culture_state.get_interpolation_scenario_output(selection_scenario)

        if not resource_set:
            return []

        # Collect all numeric columns
        columns = set()
        resources = resource_set.get_resources()

        for _, resource in resources.items():
            if isinstance(resource, Table):
                df = resource.get_data()
                # Get only numeric columns
                numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
                columns.update(numeric_cols)

        return sorted(list(columns))
    except Exception:
        return []


def render_quality_check_config_form(
        selection: Scenario,
        cell_culture_state: CellCultureState,
        config_key: str) -> Dict:
    """Render custom quality check configuration form with column selection

    :param selection: The selection scenario
    :param cell_culture_state: The cell culture state
    :param config_key: Session state key for storing config
    :return: Configuration dictionary
    """
    translate_service = cell_culture_state.get_translate_service()

    # Get available columns from selection
    available_columns = get_available_columns_from_selection(selection, cell_culture_state)

    if not available_columns:
        st.warning("⚠️ Impossible de récupérer les colonnes disponibles. Le scénario parent est peut-être en cours d'exécution.")
        return None

    st.markdown(
        f"**Colonnes disponibles** : {', '.join(available_columns[:5])}..."
        if len(available_columns) > 5 else f"**Colonnes disponibles** : {', '.join(available_columns)}")

    config = {}

    # Section 1: Détection d'outliers
    with st.expander("🔍 Détection d'Outliers", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            config['outlier_method'] = st.selectbox(
                "Méthode de détection",
                options=["none", "zscore", "iqr", "percentile"],
                index=0,
                help="none: pas de détection | zscore: écarts-types | iqr: robuste (recommandé) | percentile: percentiles extrêmes",
                key=f"{config_key}_outlier_method"
            )

        with col2:
            config['outlier_action'] = st.selectbox(
                "Action si outliers détectés",
                options=["remove_rows", "mark_only", "remove_sample"],
                index=0,
                help="remove_rows: supprime les points | mark_only: ajoute un tag | remove_sample: exclut l'échantillon",
                key=f"{config_key}_outlier_action"
            )

        if config['outlier_method'] != 'none':
            col1, col2 = st.columns(2)

            with col1:
                if config['outlier_method'] in ['zscore', 'iqr']:
                    config['outlier_threshold'] = st.number_input(
                        "Seuil",
                        min_value=1.0,
                        max_value=10.0,
                        value=3.0 if config['outlier_method'] == 'zscore' else 1.5,
                        step=0.1,
                        help="zscore: nb d'écarts-types | iqr: multiplicateur (1.5 = Tukey)",
                        key=f"{config_key}_outlier_threshold"
                    )
                else:  # percentile
                    config['outlier_threshold'] = 3.0  # Default non utilisé

            with col2:
                if config['outlier_method'] == 'percentile':
                    config['outlier_percentile_low'] = st.number_input(
                        "Percentile bas (%)",
                        min_value=0.0,
                        max_value=50.0,
                        value=1.0,
                        step=0.5,
                        key=f"{config_key}_percentile_low"
                    )
                    config['outlier_percentile_high'] = st.number_input(
                        "Percentile haut (%)",
                        min_value=50.0,
                        max_value=100.0,
                        value=99.0,
                        step=0.5,
                        key=f"{config_key}_percentile_high"
                    )
                else:
                    config['outlier_percentile_low'] = 1.0
                    config['outlier_percentile_high'] = 99.0

            # Sélection des colonnes avec multiselect
            selected_cols = st.multiselect(
                "Colonnes à vérifier (vide = toutes)", options=available_columns, default=[],
                help="Sélectionnez les colonnes à analyser pour les outliers. Si vide, toutes les colonnes numériques seront vérifiées.",
                key=f"{config_key}_outlier_columns")
            config['outlier_columns'] = ", ".join(selected_cols) if selected_cols else ""
        else:
            config['outlier_threshold'] = 3.0
            config['outlier_percentile_low'] = 1.0
            config['outlier_percentile_high'] = 99.0
            config['outlier_columns'] = ""

    # Section 2: Validation de plages
    with st.expander("📊 Validation de Plages (Range Checks)", expanded=False):
        st.markdown(translate_service.translate('qc_range_definition'))

        # Nombre de validations
        num_range_checks = st.number_input(
            "Nombre de validations",
            min_value=0,
            max_value=10,
            value=0,
            step=1,
            key=f"{config_key}_num_range_checks"
        )

        range_checks = []
        for i in range(int(num_range_checks)):
            st.markdown(f"**Validation #{i+1}**")
            col1, col2, col3, col4 = st.columns([3, 2, 2, 2])

            with col1:
                col_name = st.selectbox(
                    "Colonne",
                    options=available_columns,
                    key=f"{config_key}_range_col_{i}"
                )

            with col2:
                min_val = st.number_input(
                    "Min",
                    value=0.0,
                    step=1.0,
                    key=f"{config_key}_range_min_{i}"
                )

            with col3:
                max_val = st.number_input(
                    "Max",
                    value=100.0,
                    step=1.0,
                    key=f"{config_key}_range_max_{i}"
                )

            with col4:
                action = st.selectbox(
                    "Action",
                    options=["remove_rows", "mark_only", "remove_sample"],
                    key=f"{config_key}_range_action_{i}"
                )

            range_checks.append({
                'column': col_name,
                'min_value': min_val,
                'max_value': max_val,
                'action': action
            })

        config['range_checks'] = range_checks

    # Section 3: Données manquantes
    with st.expander("❓ Données Manquantes", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            config['max_missing_percentage'] = st.number_input(
                "% max de données manquantes",
                min_value=0.0,
                max_value=100.0,
                value=100.0,
                step=5.0,
                help="Si un échantillon a plus de X% de NaN, il est exclu",
                key=f"{config_key}_max_missing"
            )

        with col2:
            # Colonnes requises avec multiselect
            required_cols = st.multiselect(
                "Colonnes requises",
                options=available_columns,
                default=[],
                help="Ces colonnes doivent exister avec au moins 1 valeur non-NaN",
                key=f"{config_key}_required_columns"
            )
            config['required_columns'] = ", ".join(required_cols) if required_cols else ""

    # Section 4: Minimum Data Points
    with st.expander("📏 Nombre Minimum de Points de Données", expanded=False):
        st.markdown(
            "Définissez le nombre minimum de mesures (valeurs non-NaN) requises pour chaque colonne. "
            "Utile pour s'assurer qu'il y a suffisamment de points pour les analyses (ex: fitting de courbes de croissance).")

        # Nombre de vérifications
        num_min_points_checks = st.number_input(
            "Nombre de vérifications",
            min_value=0,
            max_value=10,
            value=0,
            step=1,
            key=f"{config_key}_num_min_points_checks"
        )

        min_data_points = []
        for i in range(int(num_min_points_checks)):
            st.markdown(f"**Vérification #{i+1}**")
            col1, col2, col3 = st.columns([4, 2, 3])

            with col1:
                col_name = st.selectbox(
                    "Colonne",
                    options=available_columns,
                    key=f"{config_key}_minpts_col_{i}"
                )

            with col2:
                min_count = st.number_input(
                    "Min points",
                    min_value=1,
                    max_value=100,
                    value=3,
                    step=1,
                    help="Nombre minimum de valeurs non-NaN requises",
                    key=f"{config_key}_minpts_count_{i}"
                )

            with col3:
                action = st.selectbox(
                    "Action",
                    options=["remove_sample", "mark_only"],
                    help="remove_sample: exclut l'échantillon | mark_only: ajoute un warning",
                    key=f"{config_key}_minpts_action_{i}"
                )

            min_data_points.append({
                'column': col_name,
                'min_count': float(min_count),
                'action': action
            })

        config['min_data_points'] = min_data_points

    # Section 5: Options
    with st.expander("⚙️ Options", expanded=False):
        config['add_quality_tags'] = st.checkbox(
            "Ajouter des tags de qualité",
            value=True,
            help="Ajoute des tags pour traçabilité (quality_check_passed, quality_warnings, etc.)",
            key=f"{config_key}_add_tags"
        )

    return config


def launch_quality_check_scenario(
        selection_scenario: Scenario, cell_culture_state: CellCultureState,
        quality_check_config: dict = None) -> Optional[Scenario]:
    """Launch a quality check scenario for a specific selection."""

    try:
        # Authenticate user for database operations
        with StreamlitAuthenticateUser():
            # 1. Get the data ResourceSet from the load scenario output
            data_resource = cell_culture_state.get_load_scenario_output()

            if not data_resource:
                st.error("Impossible de récupérer les données brutes (data) depuis le scénario de load.")
                return None

            data_resource_id = data_resource.get_model_id()

            # 2. Get the interpolated ResourceSet from the selection scenario (using state method)
            interpolated_resource = cell_culture_state.get_interpolation_scenario_output(selection_scenario)

            if not interpolated_resource:
                st.error(
                    "Impossible de récupérer les données interpolées. Le scénario parent est peut-être encore en cours d'exécution.")
                return None

            interpolated_resource_id = interpolated_resource.get_model_id()

            # 3. Create a new scenario for quality check with timestamp
            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            scenario_proxy = ScenarioProxy(
                None,
                folder=selection_scenario.folder,
                title=f"Quality Check - {timestamp}",
                creation_type=ScenarioCreationType.MANUAL,
            )

            # Get the protocol for the new scenario
            protocol_proxy = scenario_proxy.get_protocol()

            # Add input task for the data ResourceSet (raw data)
            data_input_task = protocol_proxy.add_process(
                InputTask, 'data_input',
                {InputTask.config_name: data_resource_id}
            )

            # Add input task for the interpolated ResourceSet
            interpolated_input_task = protocol_proxy.add_process(
                InputTask, 'interpolated_input',
                {InputTask.config_name: interpolated_resource_id}
            )

            # Add the quality check task
            quality_check_task = protocol_proxy.add_process(
                FermentalgQualityCheck,
                'quality_check_task'
            )

            # Connect the data ResourceSet to the quality check task
            protocol_proxy.add_connector(
                out_port=data_input_task >> 'resource',
                in_port=quality_check_task << 'data'
            )

            # Connect the interpolated ResourceSet to the quality check task
            protocol_proxy.add_connector(
                out_port=interpolated_input_task >> 'resource',
                in_port=quality_check_task << 'interpolated_data'
            )

            # Set quality check parameters from configuration (or use defaults)
            if quality_check_config is None:
                # Use default configuration if none provided
                quality_check_config = FermentalgQualityCheck.config_specs.get_default_values()

            # Apply all configuration parameters to the quality check task
            for param_name, param_value in quality_check_config.items():
                quality_check_task.set_param(param_name, param_value)

            # Add outputs to make the quality-checked results visible
            protocol_proxy.add_output(
                cell_culture_state.QUALITY_CHECK_SCENARIO_OUTPUT_NAME,
                quality_check_task >> 'filtered_data',
                flag_resource=True
            )

            protocol_proxy.add_output(
                cell_culture_state.QUALITY_CHECK_SCENARIO_INTERPOLATED_OUTPUT_NAME,
                quality_check_task >> 'filtered_interpolated_data',
                flag_resource=True
            )

            # Inherit tags from parent selection scenario
            parent_entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, selection_scenario.id)

            # Get recipe name from parent
            parent_recipe_name_tags = parent_entity_tag_list.get_tags_by_key(
                cell_culture_state.TAG_FERMENTOR_RECIPE_NAME)
            original_recipe_name = parent_recipe_name_tags[0].tag_value if parent_recipe_name_tags else selection_scenario.title

            # Get pipeline ID from parent
            parent_pipeline_id_tags = parent_entity_tag_list.get_tags_by_key(
                cell_culture_state.TAG_FERMENTOR_PIPELINE_ID)
            pipeline_id = parent_pipeline_id_tags[0].tag_value if parent_pipeline_id_tags else selection_scenario.id

            # Get microplate analysis flag from parent
            parent_microplate_tags = parent_entity_tag_list.get_tags_by_key(cell_culture_state.TAG_MICROPLATE_ANALYSIS)
            microplate_analysis = parent_microplate_tags[0].tag_value if parent_microplate_tags else "false"

            # Classification tag - indicate this is a quality check step
            scenario_proxy.add_tag(Tag(cell_culture_state.TAG_FERMENTOR,
                                   cell_culture_state.TAG_QUALITY_CHECK_PROCESSING, is_propagable=False))

            # Inherit core identification tags
            scenario_proxy.add_tag(Tag(cell_culture_state.TAG_FERMENTOR_RECIPE_NAME,
                                   original_recipe_name, is_propagable=False))
            scenario_proxy.add_tag(Tag(cell_culture_state.TAG_FERMENTOR_PIPELINE_ID,
                                   pipeline_id, is_propagable=False))
            scenario_proxy.add_tag(Tag(cell_culture_state.TAG_MICROPLATE_ANALYSIS,
                                   microplate_analysis, is_propagable=False))

            # Link to parent selection scenario
            scenario_proxy.add_tag(Tag(cell_culture_state.TAG_FERMENTOR_QUALITY_CHECK_PARENT_SELECTION,
                                   selection_scenario.id, is_propagable=False))
            scenario_proxy.add_tag(Tag("parent_selection_id", selection_scenario.id, is_propagable=False))

            # Add timestamp tag
            scenario_proxy.add_tag(Tag("quality_check_timestamp", timestamp, is_propagable=False))

            # Add the scenario to the queue
            scenario_proxy.add_to_queue()

            # Return the new scenario
            new_scenario = scenario_proxy.get_model()
            return new_scenario

    except Exception as e:
        st.error(f"Erreur lors du lancement du scénario de quality check: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return None


def render_quality_check_step(
        recipe: CellCultureRecipe,
        cell_culture_state: CellCultureState,
        selection_scenario: Optional[Scenario] = None) -> None:
    """Render the quality check step with configuration form

    :param recipe: The Recipe instance
    :param cell_culture_state: The cell culture state
    :param selection_scenario: Specific selection scenario to manage quality checks for (if provided, shows only this selection)
    """
    translate_service = cell_culture_state.get_translate_service()

    # If a specific selection scenario is provided, only show that one
    if selection_scenario:
        st.info(f"📋 Quality Checks pour : **{selection_scenario.title}**")

        st.markdown(
            "Cette étape permet d'appliquer des contrôles de qualité sur les données de cette sélection : "
            "détection d'outliers, validation de plages de valeurs, vérification des données manquantes, etc."
        )

        # Display only this selection's quality checks
        _render_selection_quality_checks(selection_scenario, recipe, cell_culture_state)

    else:
        # Show all selections (backward compatibility if called without selection_scenario)
        st.markdown(
            "Cette étape permet d'appliquer des contrôles de qualité sur les données sélectionnées : "
            "détection d'outliers, validation de plages de valeurs, vérification des données manquantes, etc."
        )

        # Get existing selection scenarios
        selection_scenarios = recipe.get_selection_scenarios()

        if not selection_scenarios:
            st.warning(translate_service.translate('no_selection_available'))
            return

        # Show list of selection scenarios with quality check counts
        st.markdown(f"### {translate_service.translate('available_selections_title')}")

        for idx, selection in enumerate(selection_scenarios):
            _render_selection_quality_checks(selection, recipe, cell_culture_state, show_in_expander=True, idx=idx)

    # Info box with quality check tips
    with st.expander("💡 Conseils pour le Quality Check"):
        st.markdown("""
        **Méthodes de détection d'outliers:**
        - **Z-Score**: Détecte les valeurs à plus de k écarts-types de la moyenne (défaut: 3)
        - **IQR**: Méthode robuste basée sur les quartiles (recommandé pour données biologiques)
        - **Percentile**: Retire les valeurs dans les percentiles extrêmes

        **Actions possibles:**
        - **remove_rows**: Supprime les lignes contenant des outliers
        - **mark_only**: Ajoute des tags d'avertissement mais conserve les données
        - **remove_sample**: Exclut l'échantillon entier de la sortie

        **Validation de plages:**
        Définissez des valeurs min/max acceptables pour chaque colonne (ex: pH entre 4 et 9)

        **Nombre minimum de points de données:**
        Assurez-vous qu'il y a suffisamment de mesures pour les analyses (ex: fitting de courbes de croissance nécessite ≥3 points).
        Idéal pour garantir la qualité des résultats d'analyses ultérieures.

        **Recommandations:**
        1. Commencez avec `action=mark_only` pour voir la distribution
        2. Utilisez IQR pour les données biologiques (plus robuste)
        3. Vérifiez les logs pour voir les échantillons exclus
        4. Gardez les données originales pour comparaison
        5. Pour le fitting de courbes: définissez min 3 points pour Biomasse, Glucose, etc.
        """)


def _render_selection_quality_checks(
        selection: Scenario,
        recipe: CellCultureRecipe,
        cell_culture_state: CellCultureState,
        show_in_expander: bool = False,
        idx: int = 0) -> None:
    """Render quality check interface for a specific selection

    :param selection: The selection scenario
    :param recipe: The Recipe instance
    :param cell_culture_state: The cell culture state
    :param show_in_expander: Whether to show in an expander (for list view)
    :param idx: Index for display (used in list view)
    """
    translate_service = cell_culture_state.get_translate_service()

    # Extract timestamp from title
    timestamp = "Non défini"
    if "Sélection - " in selection.title:
        timestamp = selection.title.replace("Sélection - ", "")

    # Get quality check scenarios for this selection
    quality_check_scenarios = recipe.get_quality_check_scenarios_for_selection(selection.id)
    qc_count = len(quality_check_scenarios)

    # Container function to avoid code duplication
    def render_content():
        st.write(f"✅ **Quality Checks existants:** {qc_count}")

        # Always show quality check creation form
        st.markdown("---")
        st.markdown("### ➕ Créer un nouveau Quality Check")

        # Initialize session state for quality check config
        config_key = f"quality_check_config_{selection.id}"

        # Render custom quality check configuration form
        quality_check_config = render_quality_check_config_form(
            selection,
            cell_culture_state,
            config_key
        )

        # Launch button
        if st.button("🚀 Lancer le Quality Check", key=f"launch_qc_{selection.id}",
                     type="primary", use_container_width=True):
            try:
                # Authenticate for scenario creation
                with StreamlitAuthenticateUser():
                    # Launch quality check scenario
                    qc_scenario = launch_quality_check_scenario(
                        selection, cell_culture_state, quality_check_config
                    )

                    if qc_scenario:
                        st.success(f"✅ Quality Check lancé ! ID : {qc_scenario.id}")
                        st.info(
                            "ℹ️ Le scénario est en cours d'exécution. Consultez les résultats dans le sous-menu.")

                        # Add to recipe
                        recipe.add_quality_check_scenario(selection.id, qc_scenario)

                        st.rerun()
                    else:
                        st.error(translate_service.translate('error_launching_qc'))

            except Exception:
                st.error(translate_service.translate('error_creating_scenario'))    # Render in expander or directly
    if show_in_expander:
        with st.expander(f"**{idx + 1}. {selection.title}** - ID: {selection.id} - {qc_count} Quality Check(s)"):
            render_content()
    else:
        render_content()
