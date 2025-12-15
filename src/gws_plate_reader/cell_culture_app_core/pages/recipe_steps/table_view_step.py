"""
Table View Step for Cell Culture Dashboard
Handles table visualization with filtering and column selection
"""
import streamlit as st
import pandas as pd
from typing import List, Dict, Any, Optional

from gws_core import Table, Scenario, ScenarioStatus, ScenarioProxy
from gws_core.resource.resource_set.resource_set import ResourceSet
from gws_plate_reader.cell_culture_app_core.cell_culture_state import CellCultureState
from gws_plate_reader.cell_culture_app_core.cell_culture_recipe import CellCultureRecipe


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


def prepare_extended_data_for_visualization(resource_set: ResourceSet, cell_culture_state: CellCultureState,
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
                        if tag.key == cell_culture_state.TAG_BATCH:
                            batch = tag.value
                        elif tag.key == cell_culture_state.TAG_SAMPLE:
                            sample = tag.value
                        elif tag.key == cell_culture_state.TAG_MEDIUM:
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
        cell_culture_state: CellCultureState) -> List[str]:
    """Get a list of column tags from the available columns."""
    col_tags = []
    for col_info in available_columns.values():
        col_tags.extend(col_info.get(cell_culture_state.TAG_COLUMN_NAME, []))
    return col_tags


def render_table_view_step(recipe: CellCultureRecipe, cell_culture_state: CellCultureState,
                           scenario: Optional[Scenario] = None,
                           output_name: str = None) -> None:
    """Render the table view step with filtered data visualization

    :param recipe: The Recipe instance
    :param cell_culture_state: The cell culture state
    :param scenario: The scenario to display (selection or quality check)
    :param output_name: The output name to retrieve from the scenario (e.g., INTERPOLATION_SCENARIO_OUTPUT_NAME or QUALITY_CHECK_SCENARIO_OUTPUT_NAME or QUALITY_CHECK_SCENARIO_INTERPOLATED_OUTPUT_NAME)
    """

    translate_service = cell_culture_state.get_translate_service()

    try:
        # If scenario is provided, use it
        if scenario:
            target_scenario = scenario
            st.info(f"📋 {translate_service.translate('displaying_data')} : **{target_scenario.title}**")

            if target_scenario.status != ScenarioStatus.SUCCESS:
                st.warning(translate_service.translate('scenario_not_successful_yet'))
                return

            # Get data from scenario using the provided output name
            if not output_name:
                # Default to interpolation output for backward compatibility
                output_name = cell_culture_state.INTERPOLATION_SCENARIO_OUTPUT_NAME

            scenario_proxy = ScenarioProxy.from_existing_scenario(target_scenario.id)
            protocol_proxy = scenario_proxy.get_protocol()

            try:
                filtered_resource_set = protocol_proxy.get_output(output_name)
                if not filtered_resource_set:
                    st.error(translate_service.translate('cannot_retrieve_data'))
                    return

            except Exception as e:
                st.error(translate_service.translate('error_retrieving_data').format(error=str(e)))
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

            filtered_resource_set = cell_culture_state.get_interpolation_scenario_output(target_scenario)
            if not filtered_resource_set:
                st.error(translate_service.translate('cannot_retrieve_filtered_data'))
                return

        # Extract data for visualization
        visualization_data = cell_culture_state.prepare_data_for_visualization(filtered_resource_set)

        if not visualization_data:
            st.warning(translate_service.translate('no_data_for_visualization'))
            return

        # Get unique batches and samples for filters (excluding empty strings)
        unique_batches = sorted(list(set(item['Batch'] for item in visualization_data if item['Batch'])))
        unique_samples = sorted(list(set(item['Sample'] for item in visualization_data if item['Sample'])))

        # Get available columns for selection using the new tagging system
        index_columns = cell_culture_state.get_index_columns_from_resource_set(filtered_resource_set)
        data_columns = cell_culture_state.get_data_columns_from_resource_set(filtered_resource_set)

        st.markdown("---")
        st.markdown(f"### {translate_service.translate('filters_selection_title')}")

        # Create 2x2 grid with batches and samples first
        col1, col2 = st.columns(2)

        with col1:
            col1_header, col1_button = st.columns([3, 1])
            with col1_header:
                st.write(translate_service.translate('batch_selection_label'))
            with col1_button:
                if st.button(translate_service.translate('select_all_batches'),
                             key="select_all_batches_table", use_container_width=True):
                    st.session_state.table_view_batches = unique_batches
                    st.rerun()

            # Reset selection if batches changed
            if 'table_view_batches' not in st.session_state or len(
                    [batch for batch in st.session_state.table_view_batches if batch not in unique_batches]) > 0:
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
                if st.button(translate_service.translate('select_all_samples'),
                             key="select_all_samples_table", use_container_width=True):
                    st.session_state.table_view_samples = unique_samples
                    st.rerun()

            # Reset selection if samples changed
            if 'table_view_samples' not in st.session_state or len(
                    [sample for sample in st.session_state.table_view_samples if sample not in unique_samples]) > 0:
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
                    help=translate_service.translate('choose_index_column_help')
                )
            else:
                st.warning(translate_service.translate('no_index_column'))
                selected_index = None

        # Filter data columns to exclude the selected index
        # Always exclude the selected index from selectable columns
        if selected_index:
            filtered_data_columns = [col for col in data_columns if col != selected_index]
        else:
            filtered_data_columns = data_columns

        with col4:
            st.write(f"**{translate_service.translate('column_selection')}:**")
            selected_columns = st.multiselect(
                translate_service.translate('choose_columns'),
                options=filtered_data_columns,
                default=[],  # Aucune colonne sélectionnée par défaut
                key="table_view_columns",
                help=translate_service.translate('data_columns_available_help') +
                (translate_service.translate('excluding_index_help').format(index=selected_index) if selected_index else ""))

        # Prepare extended data with selected columns
        extended_data = prepare_extended_data_for_visualization(
            filtered_resource_set, cell_culture_state, selected_columns
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
            st.markdown("### 📊 " + translate_service.translate('data_organized_by').format(index=selected_index))

            # Create a section for each selected column using the optimized function
            for i, column_name in enumerate(selected_columns):
                st.markdown(f"##### 📈 {column_name}")

                # Use the optimized function to build the DataFrame for this column
                # The subsampling task already combined real and interpolated data
                column_df = cell_culture_state.build_selected_column_df_from_resource_set(
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
                        if st.button(translate_service.translate('save_table'), key=f"download_{column_name}_{i}"):
                            cell_culture_state.save_df_as_table(
                                filtered_column_df,
                                f"cell_culture_{column_name}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}",
                                scenario=target_scenario)
                        # csv_data = filtered_column_df.to_csv(index=False)
                        # st.download_button(
                        #     label=translate_service.translate('download_column').format(column=column_name),
                        #     data=csv_data,
                        #     file_name=f"cell_culture_{column_name}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        #     mime="text/csv",
                        #     key=f"download_{column_name}_{i}"
                        # )
                    else:
                        st.warning(translate_service.translate('no_data_matches_column').format(column=column_name))
                else:
                    st.warning(translate_service.translate('no_data_available_column').format(column=column_name))

                # Add separator between columns (except for the last one)
                if i < len(selected_columns) - 1:
                    st.markdown("---")

        else:
            st.info(translate_service.translate('select_columns_table_hint'))

    except Exception as e:
        st.error(translate_service.translate('error_loading_table_view').format(error=str(e)))
