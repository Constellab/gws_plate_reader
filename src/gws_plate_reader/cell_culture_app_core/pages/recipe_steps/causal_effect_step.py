"""
Causal Effect Analysis Step for Cell Culture Dashboard
Allows users to run causal effect analysis on combined metadata and feature extraction data
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
from gws_plate_reader.cell_culture_filter import CellCultureMergeFeatureMetadata
from gws_design_of_experiments import (CausalEffect, GenerateCausalEffectDashboard)


def launch_causal_effect_scenario(
        quality_check_scenario: Scenario,
        cell_culture_state: CellCultureState,
        feature_extraction_scenario: Scenario,
        target_columns: List[str],
        columns_to_exclude: Optional[List[str]] = None) -> Optional[Scenario]:
    """
    Launch a Causal Effect analysis scenario

    :param quality_check_scenario: The parent quality check scenario
    :param cell_culture_state: The cell culture state
    :param feature_extraction_scenario: The feature extraction scenario containing results_table
    :param target_columns: List of target column names
    :param columns_to_exclude: List of column names to exclude from analysis
    :return: The created scenario or None if error
    """
    try:
        with StreamlitAuthenticateUser():
            # Create a new scenario for Causal Effect
            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            scenario_proxy = ScenarioProxy(
                None,
                folder=quality_check_scenario.folder,
                title=f"Causal Effect - {timestamp}",
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

            # Add the Causal Effect task
            causal_effect_task = protocol_proxy.add_process(
                CausalEffect,
                'causal_effect_task'
            )

            # Connect the merged table to the Causal Effect task
            protocol_proxy.add_connector(
                out_port=merge_task >> 'metadata_feature_table',
                in_port=causal_effect_task << 'data'
            )

            # Set Causal Effect parameters
            causal_effect_task.set_param('targets', target_columns)
            if columns_to_exclude:
                causal_effect_task.set_param('columns_to_exclude', columns_to_exclude)

            # Add the GenerateCausalEffectDashboard task
            dashboard_task = protocol_proxy.add_process(
                GenerateCausalEffectDashboard,
                'generate_dashboard_task'
            )

            # Connect the results folder to the dashboard task
            protocol_proxy.add_connector(
                out_port=causal_effect_task >> 'results_folder',
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
            scenario_proxy.add_tag(Tag("analysis_type", "causal_effect", is_propagable=False))

            # Add to queue
            scenario_proxy.add_to_queue()

            # Return the new scenario
            new_scenario = scenario_proxy.get_model()
            return new_scenario

    except Exception as e:
        translate_service = cell_culture_state.get_translate_service()
        st.error(translate_service.translate('error_launching_scenario_generic').format(
            scenario_type='Causal Effect', error=str(e)))
        import traceback
        st.code(traceback.format_exc())
        return None


def render_causal_effect_step(recipe: CellCultureRecipe, cell_culture_state: CellCultureState,
                              quality_check_scenario: Scenario,
                              feature_extraction_scenario: Scenario) -> None:
    """
    Render the Causal Effect analysis step

    :param recipe: The Recipe instance
    :param cell_culture_state: The cell culture state
    :param quality_check_scenario: The quality check scenario to analyze
    :param feature_extraction_scenario: The feature extraction scenario to use for analysis
    """
    translate_service = cell_culture_state.get_translate_service()

    st.markdown("### 🔗 " + translate_service.translate('causal_effect_title'))

    st.info(translate_service.translate('causal_effect_info'))

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
            st.warning(translate_service.translate('metadata_table_unavailable_qc'))
            return

        metadata_table = metadata_table_resource_model.get_resource()
        metadata_df = metadata_table.get_data()

        if 'Series' not in metadata_df.columns:
            st.error(translate_service.translate('series_column_missing'))
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
        st.error(translate_service.translate('error_reading_tables').format(error=str(e)))
        import traceback
        st.code(traceback.format_exc())
        return

    # Check existing Causal Effect scenarios for this feature extraction
    existing_causal_scenarios = recipe.get_causal_effect_scenarios_for_feature_extraction(
        feature_extraction_scenario.id)

    if existing_causal_scenarios:
        st.markdown(f"**Analyses Causal Effect existantes** : {len(existing_causal_scenarios)}")
        with st.expander("📊 Voir les analyses Causal Effect existantes"):
            for idx, causal_scenario in enumerate(existing_causal_scenarios):
                st.write(
                    f"{idx + 1}. {causal_scenario.title} - Statut: {causal_scenario.status.name}")

    # Configuration form for new Causal Effect
    st.markdown("---")
    st.markdown("### ➕ Lancer une nouvelle analyse Causal Effect")

    st.markdown("**Configuration de l'analyse**")

    # Target columns selection (must select at least one)
    target_columns = st.multiselect(
        translate_service.translate('target_variables_label'),
        options=all_numeric_columns,
        default=[],
        key=f"causal_target_columns_{quality_check_scenario.id}_{feature_extraction_scenario.id}",
        help=translate_service.translate('target_variables_help')
    )

    st.markdown(f"**{translate_service.translate('advanced_options')}**")

    # Calculate default columns to exclude:
    # 1. All non-numeric columns
    # 2. All feature extraction columns (except those selected as targets)
    default_excluded = sorted(list(
        set(all_non_numeric_columns) |
        set([col for col in feature_extraction_columns if col not in target_columns])
    ))

    # Columns to exclude
    columns_to_exclude = st.multiselect(
        translate_service.translate('columns_to_exclude_label'),
        options=[col for col in all_merged_columns if col not in target_columns],
        default=default_excluded,
        key=f"causal_columns_exclude_{quality_check_scenario.id}_{feature_extraction_scenario.id}",
        help=translate_service.translate('columns_to_exclude_help')
    )
    # Convert empty list to None
    if not columns_to_exclude:
        columns_to_exclude = None

    # Submit button
    if st.button(
        translate_service.translate('launch_analysis_button_with_type').format(analysis_type='Causal Effect'),
        type="primary",
        key=f"causal_submit_{quality_check_scenario.id}_{feature_extraction_scenario.id}",
        use_container_width=True
    ):
        if len(target_columns) == 0:
            st.error(translate_service.translate('select_target_first'))
        else:
            # Launch Causal Effect scenario
            causal_scenario = launch_causal_effect_scenario(
                quality_check_scenario,
                cell_culture_state,
                feature_extraction_scenario,
                target_columns,
                columns_to_exclude
            )

            if causal_scenario:
                st.success(translate_service.translate('analysis_launched_success').format(
                    analysis_type='Causal Effect', id=causal_scenario.id))
                st.info(translate_service.translate('analysis_running'))

                # Add to recipe
                recipe.add_causal_effect_scenario(feature_extraction_scenario.id, causal_scenario)

                st.rerun()
            else:
                st.error(translate_service.translate('analysis_launch_error').format(analysis_type='Causal Effect'))

    # Info box with explanation
    with st.expander(translate_service.translate('help_title').format(analysis_type='Causal Effect')):
        st.markdown("""
### Qu'est-ce que l'analyse Causal Effect ?

L'analyse Causal Effect utilise des méthodes d'inférence causale pour identifier les relations de cause à effet entre :
- **Variables de traitement** : Composition des milieux de culture (métadonnées)
- **Variables cibles** : Caractéristiques biologiques extraites des courbes de croissance

### Méthodes utilisées

L'analyse utilise des modèles de machine learning sophistiqués :
- **LinearDML** : Pour les traitements discrets
- **CausalForestDML** : Pour les traitements continus

Ces méthodes permettent d'estimer l'effet causal moyen (Average Treatment Effect - ATE) en contrôlant les variables confondantes.

### Résultats fournis

**Dashboard interactif Streamlit** avec :
- **Heatmaps** : Visualisation matricielle des effets causaux
- **Barplots** : Comparaison des effets par traitement et cible
- **Clustermaps** : Analyse hiérarchique des patterns causaux

**Fichiers CSV** :
- Effets causaux estimés pour chaque paire traitement-cible
- Statistiques de performance des modèles
- Progression de l'optimisation

### Applications

- Identifier quels nutriments ont un effet causal sur la croissance
- Comprendre les mécanismes biologiques sous-jacents
- Optimiser la composition des milieux de culture
- Prédire l'impact de modifications de formulation

### Interprétation

**Effet causal positif** : Augmenter le traitement augmente la cible
**Effet causal négatif** : Augmenter le traitement diminue la cible
**Effet proche de zéro** : Pas d'effet causal significatif

### Avantages vs régression classique

- Distingue corrélation et causalité
- Contrôle automatique des variables confondantes
- Estime l'effet d'interventions (pas seulement des associations)
- Plus robuste aux biais de sélection
        """)
