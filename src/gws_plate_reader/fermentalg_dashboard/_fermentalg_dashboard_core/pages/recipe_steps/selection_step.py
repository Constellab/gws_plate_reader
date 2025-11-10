"""
Selection Step for Fermentalg Dashboard
Handles data selection with interactive table and scenario launching
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Optional

from gws_core import Table, Scenario, ScenarioProxy, ScenarioCreationType, InputTask, Tag
from gws_core.resource.resource_set.resource_set import ResourceSet
from gws_core.tag.tag_entity_type import TagEntityType
from gws_core.tag.entity_tag_list import EntityTagList
from gws_core.streamlit import StreamlitTaskRunner, StreamlitAuthenticateUser
from gws_plate_reader.fermentalg_dashboard._fermentalg_dashboard_core.fermentalg_state import FermentalgState
from gws_plate_reader.fermentalg_dashboard._fermentalg_dashboard_core.fermentalg_recipe import FermentalgRecipe
from gws_plate_reader.fermentalg_filter import FilterFermentorAnalyseLoadedResourceSetBySelection, FermentalgInterpolation


def launch_selection_scenario(
        selected_df: pd.DataFrame, load_scenario: Scenario, fermentalg_state: FermentalgState,
        interpolation_config: dict = None) -> Optional[Scenario]:
    """Launch a scenario to filter the ResourceSet based on user selection."""

    translate_service = fermentalg_state.get_translate_service()

    try:
        # Authenticate user for database operations
        with StreamlitAuthenticateUser():
            # 1. Verify that selected_df is not empty
            if selected_df.empty:
                st.error(translate_service.translate('no_selection_provided'))
                return None

            # 2. Get the ResourceSet from the load scenario using the state
            resource_set = fermentalg_state.get_load_scenario_output()
            if not resource_set:
                st.error(translate_service.translate('cannot_retrieve_resourceset'))
                return None

            resource_set_model = ScenarioProxy.from_existing_scenario(load_scenario.id).get_protocol(
            ).get_process('fermentalg_data_processing').get_output_resource_model('resource_set')

            # 3. Create a new scenario for the selection filtering with timestamp
            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            scenario_proxy = ScenarioProxy(
                None,
                folder=load_scenario.folder,
                title=f"Sélection - {timestamp}",
                creation_type=ScenarioCreationType.MANUAL,
            )

            # Get the protocol for the new scenario
            protocol_proxy = scenario_proxy.get_protocol()

            # Add input task for the ResourceSet (using InputTask pattern from form page)
            input_task = protocol_proxy.add_process(
                InputTask, 'resource_set_input',
                {InputTask.config_name: resource_set_model.id}
            )

            # Add the filter task
            filter_task = protocol_proxy.add_process(
                FilterFermentorAnalyseLoadedResourceSetBySelection,
                'filter_selection_task'
            )

            # Add the interpolation task
            interpolation_task = protocol_proxy.add_process(
                FermentalgInterpolation,
                'interpolation_task'
            )

            # Connect the ResourceSet to the filter task
            protocol_proxy.add_connector(
                out_port=input_task >> 'resource',
                in_port=filter_task << 'resource_set'
            )

            # Connect the filter task to the interpolation task
            protocol_proxy.add_connector(
                out_port=filter_task >> 'filtered_resource_set',
                in_port=interpolation_task << 'resource_set'
            )

            # Convert selection to the format the task expects
            selection_criteria = []
            for _, row in selected_df.iterrows():
                selection_criteria.append({
                    'batch': row['Batch'],
                    'sample': row['Sample']
                })

            # Set the selection criteria as a parameter
            filter_task.set_param('selection_criteria', selection_criteria)

            # Set interpolation parameters from configuration (or use defaults)
            if interpolation_config is None:
                # Use default configuration if none provided
                interpolation_config = FermentalgInterpolation.config_specs.get_default_values()

            # Apply all configuration parameters to the interpolation task
            for param_name, param_value in interpolation_config.items():
                interpolation_task.set_param(param_name, param_value)

            # Add output to make the interpolated result visible
            protocol_proxy.add_output(
                fermentalg_state.INTERPOLATION_SCENARIO_OUTPUT_NAME,
                interpolation_task >> 'interpolated_resource_set',
                flag_resource=True
            )

            # Add tags to identify this as a selection scenario (suite du premier scénario)
            # Get the original analysis name from the parent scenario
            parent_entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, load_scenario.id)

            # Get original recipe name from parent scenario
            parent_recipe_name_tags = parent_entity_tag_list.get_tags_by_key(
                fermentalg_state.TAG_FERMENTOR_RECIPE_NAME)
            original_recipe_name = parent_recipe_name_tags[0].tag_value if parent_recipe_name_tags else load_scenario.title

            # Get pipeline ID from parent scenario
            parent_pipeline_id_tags = parent_entity_tag_list.get_tags_by_key(
                fermentalg_state.TAG_FERMENTOR_FERMENTALG_PIPELINE_ID)
            pipeline_id = parent_pipeline_id_tags[0].tag_value if parent_pipeline_id_tags else load_scenario.id

            # Get microplate analysis flag from parent scenario
            parent_microplate_tags = parent_entity_tag_list.get_tags_by_key(fermentalg_state.TAG_MICROPLATE_ANALYSIS)
            microplate_analysis = parent_microplate_tags[0].tag_value if parent_microplate_tags else "false"

            # Classification tag - indicate this is a selection processing step
            scenario_proxy.add_tag(Tag(fermentalg_state.TAG_FERMENTOR,
                                   fermentalg_state.TAG_SELECTION_PROCESSING, is_propagable=False))

            # Inherit core identification tags from parent scenario
            scenario_proxy.add_tag(Tag(fermentalg_state.TAG_FERMENTOR_RECIPE_NAME,
                                   original_recipe_name, is_propagable=False))
            scenario_proxy.add_tag(Tag(fermentalg_state.TAG_FERMENTOR_FERMENTALG_PIPELINE_ID,
                                   pipeline_id, is_propagable=False))
            scenario_proxy.add_tag(Tag(fermentalg_state.TAG_MICROPLATE_ANALYSIS,
                                   microplate_analysis, is_propagable=False))

            # Add specific selection step tag
            scenario_proxy.add_tag(Tag(fermentalg_state.TAG_FERMENTOR_SELECTION_STEP,
                                   load_scenario.id, is_propagable=False))
            scenario_proxy.add_tag(Tag("parent_analysis_id", load_scenario.id, is_propagable=False))

            # Add timestamp tag for easier organization
            scenario_proxy.add_tag(Tag("selection_timestamp", timestamp, is_propagable=False))

            # Add the scenario to the queue (following form page pattern)
            scenario_proxy.add_to_queue()

            # Add the new selection scenario to the state and update the analyse instance
            new_scenario = scenario_proxy.get_model()
            fermentalg_state.add_selection_scenario(new_scenario)

            return new_scenario

    except Exception as e:
        st.error(f"Erreur lors du lancement du scénario de sélection: {str(e)}")
        return None


def render_selection_step(recipe: FermentalgRecipe, fermentalg_state: FermentalgState) -> None:
    """Render the selection step with selectable table of valid data"""

    translate_service = fermentalg_state.get_translate_service()

    try:
        resource_set = fermentalg_state.get_load_scenario_output()

        if not resource_set or not isinstance(resource_set, ResourceSet):
            st.error(translate_service.translate('no_resourceset_found'))
            return

        # Get all resources from the ResourceSet
        resources = resource_set.get_resources()

        if not resources:
            st.warning(translate_service.translate('no_data_found'))
            return

        # Show existing selections info if any
        existing_selections = recipe.get_selection_scenarios()
        if existing_selections:
            st.info(f"📋 {len(existing_selections)} sélection(s) déjà créée(s). Vous pouvez en créer une nouvelle.")

            with st.expander("👁️ Voir les sélections existantes"):
                for i, selection in enumerate(existing_selections, 1):
                    # Extract timestamp from title or tags
                    timestamp = "Non défini"
                    if "Sélection - " in selection.title:
                        timestamp = selection.title.replace("Sélection - ", "")

                    st.write(f"**{i}.** {selection.title} (ID: {selection.id}) - Statut: {selection.status}")

        st.markdown(translate_service.translate('create_new_selection'))

        # Prepare valid samples (those with no missing data)
        valid_samples = []

        # Prepare valid data only (no missing data)
        valid_data = []

        for resource_name, resource in resources.items():
            if isinstance(resource, Table):
                # Extract metadata from tags
                batch = ""
                sample = ""
                medium = ""
                missing_value = ""

                if hasattr(resource, 'tags') and resource.tags:
                    for tag in resource.tags.get_tags():
                        if tag.key == fermentalg_state.TAG_BATCH:
                            batch = tag.value
                        elif tag.key == fermentalg_state.TAG_SAMPLE:
                            sample = tag.value
                        elif tag.key == fermentalg_state.TAG_MEDIUM:
                            medium = tag.value
                        elif tag.key == fermentalg_state.TAG_MISSING_VALUE:
                            missing_value = tag.value

                # Only include if no missing data
                if not missing_value:
                    valid_data.append({
                        'Batch': batch,
                        'Sample': sample,
                        'Medium': medium,
                        'Resource_Name': resource_name  # Keep track for later use
                    })

        if valid_data:
            df_valid = pd.DataFrame(valid_data)

            # Remove the Resource_Name column for display
            df_display = df_valid[['Batch', 'Sample', 'Medium']].copy()

            st.write(f"**{len(df_valid)} échantillons valides disponibles**")

            # Use st.dataframe with selection_mode for row selection
            selected_data = st.dataframe(
                df_display,
                use_container_width=True,
                hide_index=True,
                selection_mode="multi-row",
                on_select="rerun",
                key="data_selection_table"
            )

            # Configuration section for interpolation using StreamlitTaskRunner
            st.markdown(translate_service.translate('interpolation_config'))

            # Initialize session state for interpolation config
            if "interpolation_config" not in st.session_state:
                st.session_state["interpolation_config"] = None

            # Create a StreamlitTaskRunner for the interpolation task to generate the config form
            task_runner = StreamlitTaskRunner(FermentalgInterpolation)

            # Get all default parameters from the task config specs
            default_config = FermentalgInterpolation.config_specs.get_default_values()

            # Generate config form without running the task
            task_runner.generate_config_form_without_run(
                session_state_key="interpolation_config",
                default_config_values=default_config,
                is_default_config_valid=FermentalgInterpolation.config_specs.mandatory_values_are_set(default_config),
                key="interpolation_config_form"
            )            # Button to validate selection
            if st.button(translate_service.translate('validate_selection'), type="primary", use_container_width=True):
                if selected_data.selection.rows:
                    # Get selected rows
                    selected_indices = selected_data.selection.rows
                    selected_df = df_display.iloc[selected_indices]

                    # Launch selection scenario
                    try:
                        # Get interpolation config from session state
                        interpolation_config: dict = st.session_state.get("interpolation_config")
                        if interpolation_config is not None:
                            interpolation_config = interpolation_config.get("config", None)

                        selection_scenario = launch_selection_scenario(
                            selected_df, recipe.get_load_scenario(), fermentalg_state,
                            interpolation_config=interpolation_config
                        )

                        if selection_scenario:
                            st.success(f"✅ Scénario de sélection lancé ! ID : {selection_scenario.id}")
                            st.info(translate_service.translate('scenario_running'))

                            updated_selection_scenarios = [selection_scenario] + existing_selections

                            # Update the recipe instance with the new selection scenario
                            recipe.add_scenarios_by_step('selection', updated_selection_scenarios)
                            st.rerun()
                        else:
                            st.error(translate_service.translate('error_launching_scenario'))
                    except Exception as e:
                        st.error(f"❌ Erreur lors du lancement du scénario : {str(e)}")

                    st.markdown(f"### {translate_service.translate('selected_data')}")
                    st.write(f"**{len(selected_df)} échantillons sélectionnés :**")

                    # Display the selected data
                    st.dataframe(
                        selected_df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            'Batch': st.column_config.TextColumn('Batch'),
                            'Sample': st.column_config.TextColumn('Sample'),
                            'Medium': st.column_config.TextColumn('Medium')
                        }
                    )

                    # Show selection summary
                    unique_batches = selected_df['Batch'].nunique()
                    unique_samples = selected_df['Sample'].nunique()
                    unique_media = selected_df['Medium'].nunique()

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric(translate_service.translate('unique_batches'), unique_batches)
                    with col2:
                        st.metric(translate_service.translate('unique_samples'), unique_samples)
                    with col3:
                        st.metric(translate_service.translate('unique_media'), unique_media)

                else:
                    st.warning(translate_service.translate('select_at_least_one'))

            # Show current selection info
            if selected_data.selection.rows:
                st.info(f"📌 {len(selected_data.selection.rows)} ligne(s) actuellement sélectionnée(s)")
            else:
                st.info(translate_service.translate('click_to_select_hint'))

        else:
            st.warning(translate_service.translate('no_valid_samples'))

    except Exception as e:
        st.error(f"❌ Erreur: {str(e)}")
