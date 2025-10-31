"""
Table View Step for Fermentalg Dashboard
Handles table visualization with filtering and column selection
"""
import streamlit as st
import pandas as pd
from typing import List, Dict, Any, Optional

from gws_core import Table, Scenario, ScenarioStatus, ScenarioProxy
from gws_core.resource.resource_set.resource_set import ResourceSet
from gws_plate_reader.fermentalg_dashboard._fermentalg_dashboard_core.fermentalg_state import FermentalgState
from gws_plate_reader.fermentalg_dashboard._fermentalg_dashboard_core.fermentalg_recipe import FermentalgRecipe


def get_available_columns_from_resource_set(resource_set: ResourceSet) -> Dict[str, Dict[str, str]]:
    """Get available columns from ResourceSet that have 'is_data_column' or 'is_index_column' tags"""
    try:
        resources = resource_set.get_resources()
        available_columns = {}

        for resource_name, resource in resources.items():
            if isinstance(resource, Table):
                for col_name in resource.get_column_names():

                    if col_name in available_columns:
                        continue

                    col_tags = resource.get_column_tags_by_name(col_name)

                    # Include columns that are tagged as index or data columns
                    is_index_column = col_tags.get('is_index_column') == 'true'
                    is_data_column = col_tags.get('is_data_column') == 'true'

                    if is_index_column or is_data_column:
                        available_columns[col_name] = col_tags

        return available_columns
    except Exception:
        return {}


def prepare_extended_data_for_visualization(resource_set: ResourceSet, fermentalg_state: FermentalgState,
                                            selected_columns: List[str] = None) -> List[Dict[str, Any]]:
    """Prepare extended data from ResourceSet including selected columns"""
    try:
        resources = resource_set.get_resources()
        visualization_data = []

        for resource_name, resource in resources.items():
            if isinstance(resource, Table):
                # Extract metadata from tags
                batch = ""
                sample = ""
                medium = ""

                # Basic metadata
                if hasattr(resource, 'tags') and resource.tags:
                    for tag in resource.tags.get_tags():
                        if tag.key == fermentalg_state.TAG_BATCH:
                            batch = tag.value
                        elif tag.key == fermentalg_state.TAG_SAMPLE:
                            sample = tag.value
                        elif tag.key == fermentalg_state.TAG_MEDIUM:
                            medium = tag.value

                # Prepare row data
                row_data = {
                    'Batch': batch,
                    'Sample': sample,
                    'Medium': medium,
                    'Resource_Name': resource_name
                }

                # Add selected columns data if specified
                if selected_columns:
                    df = resource.get_data()
                    for col_name in selected_columns:
                        if col_name in df.columns:
                            # Get the first value of the column or a summary if multiple values
                            if len(df) > 0:
                                if df[col_name].dtype in ['object', 'string']:
                                    row_data[col_name] = str(df[col_name].iloc[0])
                                else:
                                    # For numeric columns, show mean or first value
                                    row_data[col_name] = df[col_name].mean() if len(df) > 1 else df[col_name].iloc[0]
                            else:
                                row_data[col_name] = "N/A"
                        else:
                            row_data[col_name] = "N/A"

                visualization_data.append(row_data)

        return visualization_data
    except Exception:
        return []


def get_col_tag_list_from_available_columns(
        available_columns: Dict[str, Dict[str, str]],
        fermentalg_state: FermentalgState) -> List[str]:
    """Get a list of column tags from the available columns."""
    col_tags = []
    for col_info in available_columns.values():
        col_tags.extend(col_info.get(fermentalg_state.TAG_COLUMN_NAME, []))
    return col_tags


def render_table_view_step(recipe: FermentalgRecipe, fermentalg_state: FermentalgState,
                           scenario: Optional[Scenario] = None,
                           output_name: str = None) -> None:
    """Render the table view step with filtered data visualization

    :param recipe: The Recipe instance
    :param fermentalg_state: The fermentalg state
    :param scenario: The scenario to display (selection or quality check)
    :param output_name: The output name to retrieve from the scenario (e.g., INTERPOLATION_SCENARIO_OUTPUT_NAME or QUALITY_CHECK_SCENARIO_OUTPUT_NAME)
    """

    translate_service = fermentalg_state.get_translate_service()

    try:
        # If scenario is provided, use it
        if scenario:
            target_scenario = scenario
            st.info(f"� Affichage des données : **{target_scenario.title}**")

            if target_scenario.status != ScenarioStatus.SUCCESS:
                st.warning("Le scénario n'est pas encore terminé avec succès.")
                return

            # Get data from scenario using the provided output name
            if not output_name:
                # Default to interpolation output for backward compatibility
                output_name = fermentalg_state.INTERPOLATION_SCENARIO_OUTPUT_NAME

            scenario_proxy = ScenarioProxy.from_existing_scenario(target_scenario.id)
            protocol_proxy = scenario_proxy.get_protocol()

            try:
                filtered_resource_set = protocol_proxy.get_output(output_name)
                if not filtered_resource_set:
                    st.error(translate_service.translate('cannot_retrieve_data'))
                    return
            except Exception as e:
                st.error(f"Erreur lors de la récupération des données: {str(e)}")
                return

        # Backward compatibility: if no scenario provided, try to get latest selection
        else:
            if not recipe.has_selection_scenarios():
                st.warning(translate_service.translate('no_selection_made'))
                return

            selection_scenarios = recipe.get_selection_scenarios()
            target_scenario = selection_scenarios[0] if selection_scenarios else None

            if not target_scenario or target_scenario.status != ScenarioStatus.SUCCESS:
                st.warning(translate_service.translate('selection_not_successful'))
                return

            filtered_resource_set = fermentalg_state.get_interpolation_scenario_output(target_scenario)
            if not filtered_resource_set:
                st.error(translate_service.translate('cannot_retrieve_filtered_data'))
                return

        st.subheader(translate_service.translate('table_visualization'))

        # Extract data for visualization
        visualization_data = fermentalg_state.prepare_data_for_visualization(filtered_resource_set)

        if not visualization_data:
            st.warning(translate_service.translate('no_data_for_visualization'))
            return

        # Get unique batches and samples for filters (excluding empty strings)
        unique_batches = sorted(list(set(item['Batch'] for item in visualization_data if item['Batch'])))
        unique_samples = sorted(list(set(item['Sample'] for item in visualization_data if item['Sample'])))

        # Get available columns for selection using the new tagging system
        index_columns = fermentalg_state.get_index_columns_from_resource_set(filtered_resource_set)
        data_columns = fermentalg_state.get_data_columns_from_resource_set(filtered_resource_set)

        st.markdown("---")
        st.subheader(translate_service.translate('filters_selection_title'))

        # Create 2x2 grid with batches and samples first
        col1, col2 = st.columns(2)

        with col1:
            col1_header, col1_button = st.columns([3, 1])
            with col1_header:
                st.write(translate_service.translate('batch_selection_label'))
            with col1_button:
                if st.button(translate_service.translate('select_all_batches'), key="select_all_batches_table", use_container_width=True):
                    st.session_state.table_view_batches = unique_batches
                    st.rerun()

            # Reset selection if batches changed
            if 'table_view_batches' not in st.session_state or len([batch for batch in st.session_state.table_view_batches if batch not in unique_batches]) > 0:
                st.session_state.table_view_batches = []

            selected_batches = st.multiselect(
                translate_service.translate('choose_batches'),
                options=unique_batches,
                key="table_view_batches"
            )

        with col2:
            col2_header, col2_button = st.columns([3, 1])
            with col2_header:
                st.write(translate_service.translate('sample_selection'))
            with col2_button:
                if st.button(translate_service.translate('select_all_samples'), key="select_all_samples_table", use_container_width=True):
                    st.session_state.table_view_samples = unique_samples
                    st.rerun()

            # Reset selection if samples changed
            if 'table_view_samples' not in st.session_state or len([sample for sample in st.session_state.table_view_samples if sample not in unique_samples]) > 0:
                st.session_state.table_view_samples = []

            selected_samples = st.multiselect(
                translate_service.translate('choose_samples'),
                options=unique_samples,
                key="table_view_samples"
            )

        # Second row of the 2x2 grid
        col3, col4 = st.columns(2)

        with col3:
            st.write(translate_service.translate('index_column'))
            # Check if index columns are available
            if index_columns:
                selected_index = st.selectbox(
                    translate_service.translate('choose_index_column'),
                    options=index_columns,
                    index=0,
                    key="table_view_index",
                    help=translate_service.translate('index_column_help_table')
                )
            else:
                st.warning(translate_service.translate('no_index_column'))
                selected_index = None

        # Filter data columns to exclude the selected index
        if selected_index and selected_index in data_columns:
            filtered_data_columns = [col for col in data_columns if col != selected_index]
        else:
            filtered_data_columns = data_columns

        with col4:
            st.write(translate_service.translate('column_selection'))
            selected_columns = st.multiselect(
                translate_service.translate('choose_columns'),
                options=filtered_data_columns,
                default=[],  # Aucune colonne sélectionnée par défaut
                key="table_view_columns",
                help=f"Colonnes de données disponibles" +
                (f" (excluant l'index '{selected_index}')" if selected_index else ""))

        # Show info message if a data column is used as index
        if selected_index and selected_index in data_columns and selected_index not in ['Batch', 'Sample']:
            st.info(
                f"💡 La colonne '{selected_index}' est utilisée comme index et a été retirée de la liste des colonnes sélectionnables.")

        # Prepare extended data with selected columns
        extended_data = prepare_extended_data_for_visualization(
            filtered_resource_set, fermentalg_state, selected_columns
        )

        # Filter data based on batch and sample selection
        filtered_data = [
            item for item in extended_data
            if item['Batch'] in selected_batches and item['Sample'] in selected_samples
        ]

        if not filtered_data:
            st.warning(translate_service.translate('no_data_matches_filters'))
            return

        # Display summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(translate_service.translate('selected_batches'), len(selected_batches))
        with col2:
            st.metric(translate_service.translate('selected_samples'), len(selected_samples))
        with col3:
            # Count actual displayed batch/sample couples
            displayed_couples = len(filtered_data)
            st.metric(translate_service.translate('displayed_couples'), displayed_couples)
        with col4:
            st.metric(translate_service.translate('selected_columns'), len(selected_columns))

        # Check if we have a valid index selected
        if not selected_index:
            st.warning(translate_service.translate('select_valid_index_table'))
            return

        # Display data organized by selected columns
        if selected_columns:
            st.subheader(f"📊 Données organisées par {selected_index}")

            # Create a section for each selected column using the optimized function
            for i, column_name in enumerate(selected_columns):
                st.markdown(f"### 📈 {column_name}")

                # Use the optimized function to build the DataFrame for this column
                column_df = fermentalg_state.build_selected_column_df_from_resource_set(
                    filtered_resource_set, selected_index, column_name
                )

                if not column_df.empty:
                    # Filter the DataFrame based on selected batches and samples
                    # Create a mask for filtering based on batch/sample combinations
                    batch_sample_combinations = set()
                    for batch in selected_batches:
                        for sample in selected_samples:
                            batch_sample_combinations.add(f"{batch}_{sample}")

                    # Keep only columns that match the selected batch/sample combinations
                    columns_to_keep = [selected_index]  # Always keep the index column
                    for col in column_df.columns:
                        if col != selected_index:
                            if col in batch_sample_combinations:
                                columns_to_keep.append(col)

                    # Filter the DataFrame
                    filtered_column_df = column_df[columns_to_keep] if len(
                        columns_to_keep) > 1 else column_df[[selected_index]]

                    if len(filtered_column_df.columns) > 1:
                        # Calculate summary statistics from all data columns (excluding index)
                        data_columns_only = filtered_column_df.select_dtypes(include=[float, int])
                        if selected_index in data_columns_only.columns:
                            data_columns_only = data_columns_only.drop(columns=[selected_index])

                        if not data_columns_only.empty:
                            # Add summary statistics
                            col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)
                            with col_stats1:
                                total_values = data_columns_only.count().sum()
                                st.metric(translate_service.translate('total_values'), int(total_values))
                            with col_stats2:
                                mean_val = data_columns_only.mean().mean()
                                st.metric(translate_service.translate('overall_average'), f"{mean_val:.3f}")
                            with col_stats3:
                                min_val = data_columns_only.min().min()
                                st.metric(translate_service.translate('minimum'), f"{min_val:.3f}")
                            with col_stats4:
                                max_val = data_columns_only.max().max()
                                st.metric(translate_service.translate('maximum'), f"{max_val:.3f}")

                        # Configure columns for display
                        column_config = {selected_index: st.column_config.TextColumn(
                            f'{selected_index}', width="medium")}

                        # Add configuration for each data column
                        for col in filtered_column_df.columns:
                            if col != selected_index:
                                column_config[col] = st.column_config.NumberColumn(
                                    col,
                                    width="medium",
                                    format="%.4f"
                                )

                        # Display the table for this column
                        st.dataframe(
                            filtered_column_df,
                            use_container_width=True,
                            hide_index=True,
                            column_config=column_config
                        )

                        # Download button for this specific column
                        csv_data = filtered_column_df.to_csv(index=False)
                        st.download_button(
                            label=translate_service.translate('download_column').format(column=column_name),
                            data=csv_data,
                            file_name=f"fermentalg_{column_name}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            key=f"download_{column_name}_{i}"
                        )
                    else:
                        st.warning(f"⚠️ Aucune donnée correspond aux filtres sélectionnés pour {column_name}")
                else:
                    st.warning(f"⚠️ Aucune donnée disponible pour la colonne {column_name}")

                # Add separator between columns (except for the last one)
                if i < len(selected_columns) - 1:
                    st.markdown("---")

        else:
            st.info(translate_service.translate('select_columns_table_hint'))

    except Exception as e:
        st.error(f"❌ Erreur lors du chargement de la vue tableau: {str(e)}")
