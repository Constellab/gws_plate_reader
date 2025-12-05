"""
Optimization Analysis Step for Cell Culture Dashboard
Allows users to run optimization on combined metadata and feature extraction data
"""
import streamlit as st
from typing import List, Optional
from datetime import datetime

from gws_core import (Scenario, ScenarioProxy, ScenarioCreationType, InputTask, Tag, ScenarioStatus,
                      ResourceModel, JSONDict)
from gws_core.tag.tag_entity_type import TagEntityType
from gws_core.tag.entity_tag_list import EntityTagList
from gws_core.streamlit import StreamlitAuthenticateUser, StreamlitResourceSelect
from gws_plate_reader.cell_culture_app_core.cell_culture_state import CellCultureState
from gws_plate_reader.cell_culture_app_core.cell_culture_recipe import CellCultureRecipe
from gws_plate_reader.cell_culture_filter import CellCultureMergeFeatureMetadata
from gws_design_of_experiments import Optimization, GenerateOptimizationDashboard


def launch_optimization_scenario(
        quality_check_scenario: Scenario,
        cell_culture_state: CellCultureState,
        feature_extraction_scenario: Scenario,
        manual_constraints_resource_id: str,
        population_size: int,
        iterations: int,
        targets_thresholds: List[dict],
        columns_to_exclude: Optional[List[str]] = None) -> Optional[Scenario]:
    """
    Launch an Optimization analysis scenario

    :param quality_check_scenario: The parent quality check scenario
    :param cell_culture_state: The cell culture state
    :param feature_extraction_scenario: The feature extraction scenario containing results_table
    :param manual_constraints_resource_id: ID of the JSONDict resource containing manual constraints
    :param population_size: Population size for optimization algorithm
    :param iterations: Number of iterations
    :param targets_thresholds: List of target/threshold dictionaries
    :param columns_to_exclude: List of column names to exclude from analysis
    :return: The created scenario or None if error
    """
    try:
        with StreamlitAuthenticateUser():
            # Create a new scenario for Optimization
            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            scenario_proxy = ScenarioProxy(
                None,
                folder=quality_check_scenario.folder,
                title=f"Optimization - {timestamp}",
                creation_type=ScenarioCreationType.MANUAL,
            )

            # Get the protocol
            protocol_proxy = scenario_proxy.get_protocol()

            # Get the metadata_table resource model from the quality check scenario output
            qc_scenario_proxy = ScenarioProxy.from_existing_scenario(quality_check_scenario.id)
            qc_protocol_proxy = qc_scenario_proxy.get_protocol()

            metadata_table_resource_model = qc_protocol_proxy.get_output_resource_model(
                cell_culture_state.QUALITY_CHECK_SCENARIO_METADATA_OUTPUT_NAME
            )

            if not metadata_table_resource_model:
                raise ValueError("La sortie 'metadata_table' n'est pas disponible dans le scénario de quality check")

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

            # Add input task for manual_constraints JSONDict
            constraints_input_task = protocol_proxy.add_process(
                InputTask, 'manual_constraints_input',
                {InputTask.config_name: manual_constraints_resource_id}
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

            # Add the Optimization task
            optimization_task = protocol_proxy.add_process(
                Optimization,
                'optimization_task'
            )

            # Connect the merged table and constraints to the Optimization task
            protocol_proxy.add_connector(
                out_port=merge_task >> 'metadata_feature_table',
                in_port=optimization_task << 'data'
            )
            protocol_proxy.add_connector(
                out_port=constraints_input_task >> 'resource',
                in_port=optimization_task << 'manual_constraints'
            )

            # Set Optimization parameters
            optimization_task.set_param('population_size', population_size)
            optimization_task.set_param('iterations', iterations)
            optimization_task.set_param('targets_thresholds', targets_thresholds)
            if columns_to_exclude:
                optimization_task.set_param('columns_to_exclude', columns_to_exclude)

            # Add the GenerateOptimizationDashboard task
            dashboard_task = protocol_proxy.add_process(
                GenerateOptimizationDashboard,
                'generate_dashboard_task'
            )

            # Connect the results folder to the dashboard task
            protocol_proxy.add_connector(
                out_port=optimization_task >> 'results_folder',
                in_port=dashboard_task << 'folder'
            )

            # Add output for the Streamlit app
            protocol_proxy.add_output(
                'streamlit_app',
                dashboard_task >> 'streamlit_app',
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
            scenario_proxy.add_tag(Tag("analysis_type", "optimization", is_propagable=False))

            # Add to queue
            scenario_proxy.add_to_queue()

            # Return the new scenario
            new_scenario = scenario_proxy.get_model()
            return new_scenario

    except Exception as e:
        st.error(translate_service.translate('error_launching_scenario_generic').format(
            scenario_type='Optimization', error=str(e)))
        import traceback
        st.code(traceback.format_exc())
        return None


def render_optimization_step(recipe: CellCultureRecipe, cell_culture_state: CellCultureState,
                             quality_check_scenario: Scenario,
                             feature_extraction_scenario: Scenario) -> None:
    """
    Render the Optimization analysis step

    :param recipe: The Recipe instance
    :param cell_culture_state: The cell culture state
    :param quality_check_scenario: The quality check scenario to analyze
    :param feature_extraction_scenario: The feature extraction scenario to use for analysis
    """
    translate_service = cell_culture_state.get_translate_service()

    st.markdown("### ⚙️ " + translate_service.translate('optimization_title'))

    st.info(translate_service.translate('optimization_info'))

    # Display selected feature extraction scenario
    st.info("📊 " + translate_service.translate('feature_extraction_scenario_info').format(title=feature_extraction_scenario.title))

    # Get available columns from merged table (metadata + features)
    try:
        # Get metadata table from quality check
        qc_scenario_proxy = ScenarioProxy.from_existing_scenario(quality_check_scenario.id)
        qc_protocol_proxy = qc_scenario_proxy.get_protocol()

        metadata_table_resource_model = qc_protocol_proxy.get_output_resource_model(
            cell_culture_state.QUALITY_CHECK_SCENARIO_METADATA_OUTPUT_NAME
        )

        if not metadata_table_resource_model:
            st.warning(
                "⚠️ La table des métadonnées (metadata_table) n'est pas disponible dans le scénario de quality check.")
            return

        metadata_table = metadata_table_resource_model.get_resource()
        metadata_df = metadata_table.get_data()

        if 'Series' not in metadata_df.columns:
            st.error(f"⚠️ {translate_service.translate('series_column_missing')}")
            return

        # Get feature extraction results to know all columns that will be in merged table
        fe_scenario_proxy = ScenarioProxy.from_existing_scenario(feature_extraction_scenario.id)
        fe_protocol_proxy = fe_scenario_proxy.get_protocol()
        results_table_resource_model = fe_protocol_proxy.get_output_resource_model('results_table')

        if results_table_resource_model:
            results_table = results_table_resource_model.get_resource()
            results_df = results_table.get_data()
            # Get all columns from both tables (excluding 'Series' which is the merge key)
            all_merged_columns = sorted(list(set(metadata_df.columns.tolist() + results_df.columns.tolist())))

            # Identify feature extraction columns
            feature_extraction_columns = sorted(results_df.columns.tolist())

            # Separate numeric and non-numeric columns
            metadata_numeric_cols = metadata_df.select_dtypes(include=['number']).columns.tolist()
            results_numeric_cols = results_df.select_dtypes(include=['number']).columns.tolist()
            all_numeric_columns = sorted(list(set(metadata_numeric_cols + results_numeric_cols)))

            # Calculate non-numeric columns to exclude by default
            all_non_numeric_columns = sorted(list(set(all_merged_columns) - set(all_numeric_columns)))
        else:
            # Fallback to metadata columns only
            all_merged_columns = sorted(metadata_df.columns.tolist())
            all_numeric_columns = sorted(metadata_df.select_dtypes(include=['number']).columns.tolist())
            feature_extraction_columns = []

            # Calculate non-numeric columns to exclude by default
            all_non_numeric_columns = sorted(list(set(all_merged_columns) - set(all_numeric_columns)))

        st.markdown("**" + translate_service.translate('numeric_columns_available') + "** : " +
                    str(len(all_numeric_columns)))
        cols_preview = ', '.join(all_numeric_columns[:10])
        if len(all_numeric_columns) > 10:
            st.markdown("**" + translate_service.translate('preview') + "** : " + cols_preview +
                        translate_service.translate('more_columns').format(count=len(all_numeric_columns)-10))
        else:
            st.markdown("**" + translate_service.translate('preview') + "** : " + cols_preview)

    except Exception as e:
        st.error(f"Erreur lors de la lecture des tables : {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return

    # Check existing Optimization scenarios for this feature extraction
    existing_optimization_scenarios = recipe.get_optimization_scenarios_for_feature_extraction(
        feature_extraction_scenario.id)

    if existing_optimization_scenarios:
        st.markdown(f"**Analyses Optimization existantes** : {len(existing_optimization_scenarios)}")
        with st.expander("📊 Voir les analyses Optimization existantes"):
            for idx, opt_scenario in enumerate(existing_optimization_scenarios):
                st.write(
                    f"{idx + 1}. {opt_scenario.title} - Statut: {opt_scenario.status.name}")

    # Configuration form for new Optimization
    st.markdown("---")
    st.markdown("### ➕ Lancer une nouvelle analyse Optimization")

    st.markdown(f"**{translate_service.translate('constraints_resource_selection')}**")

    # Use StreamlitResourceSelect to select JSONDict resource
    resource_select_constraints = StreamlitResourceSelect()
    # Filter to show only JSONDict resources
    resource_select_constraints.filters['resourceTypingNames'] = ['RESOURCE.gws_core.JSONDict']
    resource_select_constraints.select_resource(
        placeholder=translate_service.translate('select_constraints_resource_placeholder'),
        key=f"optimization_constraints_{quality_check_scenario.id}_{feature_extraction_scenario.id}",
        defaut_resource=None
    )

    # Get selected resource ID from session state
    constraints_selector_key = f"optimization_constraints_{quality_check_scenario.id}_{feature_extraction_scenario.id}"
    if constraints_selector_key not in st.session_state:
        st.session_state[constraints_selector_key] = {}

    selected_constraints_id = st.session_state.get(constraints_selector_key).get(
        "resourceId", None) if st.session_state.get(constraints_selector_key) else None

    # Check if a resource is selected
    if not selected_constraints_id:
        st.warning(f"⚠️ {translate_service.translate('select_jsondict_warning')}")
        st.info(
            "💡 Créez une ressource JSONDict contenant les contraintes au format : {\"feature_name\": {\"lower_bound\": value, \"upper_bound\": value}}")
        return

    st.markdown("**Configuration de l'analyse**")

    col1, col2 = st.columns(2)

    with col1:
        population_size = st.number_input(
            "Taille de population",
            min_value=50,
            max_value=2000,
            value=500,
            step=50,
            key=f"optimization_population_{quality_check_scenario.id}_{feature_extraction_scenario.id}",
            help="Nombre d'individus dans la population de l'algorithme génétique"
        )

    with col2:
        iterations = st.number_input(
            "Nombre d'itérations",
            min_value=10,
            max_value=1000,
            value=100,
            step=10,
            key=f"optimization_iterations_{quality_check_scenario.id}_{feature_extraction_scenario.id}",
            help="Nombre d'itérations de l'algorithme d'optimisation"
        )

    st.markdown("**Cibles et objectifs**")

    # Dynamic target/threshold pairs
    if 'num_targets' not in st.session_state:
        st.session_state.num_targets = 1

    targets_thresholds = []

    for i in range(st.session_state.num_targets):
        col_target, col_threshold = st.columns(2)

        with col_target:
            target = st.selectbox(
                f"Cible {i+1}",
                options=all_numeric_columns,
                key=f"optimization_target_{i}_{quality_check_scenario.id}_{feature_extraction_scenario.id}",
                help=translate_service.translate('variable_to_optimize')
            )

        with col_threshold:
            threshold = st.number_input(
                f"Objectif {i+1}",
                value=0.0,
                key=f"optimization_threshold_{i}_{quality_check_scenario.id}_{feature_extraction_scenario.id}",
                help="Valeur objectif minimale pour cette cible"
            )

        targets_thresholds.append({"targets": target, "thresholds": int(threshold)})

    col_add, col_remove = st.columns(2)
    with col_add:
        if st.button(translate_service.translate('add_target'),
                     key=f"add_target_{quality_check_scenario.id}_{feature_extraction_scenario.id}"):
            st.session_state.num_targets += 1
            st.rerun()

    with col_remove:
        if st.session_state.num_targets > 1:
            if st.button(
                translate_service.translate('remove_target'),
                    key=f"remove_target_{quality_check_scenario.id}_{feature_extraction_scenario.id}"):
                st.session_state.num_targets -= 1
                st.rerun()

    st.markdown(f"**{translate_service.translate('advanced_options')}**")

    # Calculate default columns to exclude:
    # 1. All non-numeric columns
    # 2. All feature extraction columns (except those selected as targets)
    selected_targets = [t["targets"] for t in targets_thresholds]
    default_excluded = sorted(list(
        set(all_non_numeric_columns) |
        set([col for col in feature_extraction_columns if col not in selected_targets])
    ))

    # Columns to exclude
    columns_to_exclude = st.multiselect(
        translate_service.translate('columns_to_exclude_label'),
        options=[col for col in all_merged_columns if col not in selected_targets],
        default=default_excluded,
        key=f"optimization_columns_exclude_{quality_check_scenario.id}_{feature_extraction_scenario.id}",
        help=translate_service.translate('columns_to_exclude_help')
    )
    # Convert empty list to None
    if not columns_to_exclude:
        columns_to_exclude = None

    # Submit button
    if st.button(
        translate_service.translate('launch_analysis_button_with_type').format(analysis_type='Optimization'),
        type="primary",
        key=f"optimization_submit_{quality_check_scenario.id}_{feature_extraction_scenario.id}",
        use_container_width=True
    ):
        if len(targets_thresholds) == 0:
            st.error(translate_service.translate('select_target_first'))
        else:
            # Launch Optimization scenario
            optimization_scenario = launch_optimization_scenario(
                quality_check_scenario,
                cell_culture_state,
                feature_extraction_scenario,
                selected_constraints_id,
                population_size,
                iterations,
                targets_thresholds,
                columns_to_exclude
            )

            if optimization_scenario:
                st.success(translate_service.translate('analysis_launched_success').format(
                    analysis_type='Optimization', id=optimization_scenario.id))
                st.info(translate_service.translate('analysis_running'))

                # Add to recipe
                recipe.add_optimization_scenario(feature_extraction_scenario.id, optimization_scenario)

                st.rerun()
            else:
                st.error(translate_service.translate('analysis_launch_error').format(analysis_type='Optimization'))

    # Info box with explanation
    with st.expander(translate_service.translate('help_title').format(analysis_type='Optimization')):
        st.markdown("""
### Qu'est-ce que l'analyse Optimization ?

L'analyse Optimization utilise des algorithmes évolutionnaires (NSGA-II ou GA) pour trouver les conditions optimales :
- **Variables d'entrée** : Composition des milieux de culture (métadonnées)
- **Variables cibles** : Caractéristiques biologiques à maximiser

### Algorithmes utilisés

1. **Entraînement de modèles ML** :
   - Random Forest
   - XGBoost
   - CatBoost
   - Sélection automatique du meilleur modèle basé sur R² CV

2. **Optimisation** :
   - NSGA-II pour multi-objectifs
   - GA pour objectif unique
   - Respect des contraintes définies

### Configuration requise

**Ressource de contraintes (JSONDict)** :
```json
{
  "Temperature": {"lower_bound": 20, "upper_bound": 40},
  "pH": {"lower_bound": 6.0, "upper_bound": 8.0},
  "Nutrient_A": {"lower_bound": 0, "upper_bound": 100}
}
```

**Cibles et objectifs** :
- Une ou plusieurs variables à optimiser
- Valeur seuil minimale pour chaque cible

### Résultats fournis

**Dashboard interactif Streamlit** avec :
- **Best Solution** : Meilleure solution trouvée
- **3D Surface Explorer** : Visualisation 3D interactive
- **Feature Importance** : Importance des variables
- **Observed vs Predicted** : Validation du modèle

**Fichiers CSV** :
- `generalized_solutions.csv` : Toutes les solutions trouvées
- `best_generalized_solution.csv` : Meilleure solution
- `feature_importance_matrix.csv` : Importance des features
- `optimization_progress.csv` : Historique de convergence

### Applications

- Optimiser la composition des milieux de culture
- Maximiser la croissance et le rendement
- Identifier les conditions optimales de production
- Explorer l'espace des solutions possibles

### Paramètres

- **Population size** : Plus grand = exploration plus large (plus lent)
- **Iterations** : Plus élevé = convergence meilleure (plus long)
- **Contraintes** : Définissent l'espace de recherche réaliste
        """)
