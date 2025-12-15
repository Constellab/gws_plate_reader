"""
Graph View Step for Cell Culture Dashboard
Handles graph visualizations with filtering and interactive plots using Plotly
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import Optional

from gws_core import Scenario, ScenarioStatus, ScenarioProxy
from gws_plate_reader.cell_culture_app_core.cell_culture_state import CellCultureState
from gws_plate_reader.cell_culture_app_core.cell_culture_recipe import CellCultureRecipe


def render_graph_view_step(recipe: CellCultureRecipe, cell_culture_state: CellCultureState,
                           scenario: Optional[Scenario] = None,
                           output_name: str = None) -> None:
    """Render the graph view step with data visualizations using Plotly

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
            st.info(f"📊 {translate_service.translate('displaying_graphs')} : **{target_scenario.title}**")

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

        # Extract data for visualization using State method
        visualization_data = cell_culture_state.prepare_data_for_visualization(filtered_resource_set)

        if not visualization_data:
            st.warning(translate_service.translate('no_data_for_visualization'))
            return

        # Get unique values for filters (excluding empty strings)
        unique_batches = sorted(list(set(item['Batch'] for item in visualization_data if item['Batch'])))
        unique_samples = sorted(list(set(item['Sample'] for item in visualization_data if item['Sample'])))

        # Create dataframe from all resources for detailed plotting
        from gws_core import Table
        all_data_rows = []
        resources = filtered_resource_set.get_resources()

        for resource_name, resource in resources.items():
            if isinstance(resource, Table):
                # Extract metadata from tags
                batch = ""
                sample = ""
                medium = ""

                if hasattr(resource, 'tags') and resource.tags:
                    for tag in resource.tags.get_tags():
                        if tag.key == cell_culture_state.TAG_BATCH:
                            batch = tag.value
                        elif tag.key == cell_culture_state.TAG_SAMPLE:
                            sample = tag.value
                        elif tag.key == cell_culture_state.TAG_MEDIUM:
                            medium = tag.value

                # Get DataFrame
                df = resource.get_data()

                # Add rows to the list
                for _, row in df.iterrows():
                    row_dict = row.to_dict()
                    row_dict['Batch'] = batch
                    row_dict['Sample'] = sample
                    row_dict['Medium'] = medium
                    row_dict['Resource_Name'] = resource_name
                    all_data_rows.append(row_dict)

        df_all = pd.DataFrame(all_data_rows)

        # Get available columns for selection using the tagging system
        index_columns = cell_culture_state.get_index_columns_from_resource_set(filtered_resource_set)
        data_columns = cell_culture_state.get_data_columns_from_resource_set(filtered_resource_set)

        # === Section 1: Filters ===
        st.markdown("---")
        st.markdown(f"### {translate_service.translate('filters_and_selection')}")

        # Create 2x2 grid for filters
        col1, col2 = st.columns(2)

        with col1:
            col1_header, col1_button = st.columns([3, 1])
            with col1_header:
                st.write(translate_service.translate('batch_selection'))
            with col1_button:
                if st.button(translate_service.translate('select_all_batches'),
                             key="select_all_batches_graph", width='stretch'):
                    st.session_state.graph_view_batches = unique_batches
                    st.rerun()

            # Reset selection if batches changed
            if 'graph_view_batches' not in st.session_state or len(
                    [batch for batch in st.session_state.graph_view_batches if batch not in unique_batches]) > 0:
                st.session_state.graph_view_batches = []

            selected_batches = st.multiselect(
                translate_service.translate('choose_batches'),
                options=unique_batches,
                key="graph_view_batches"
            )

        with col2:
            col2_header, col2_button = st.columns([3, 1])
            with col2_header:
                st.write(translate_service.translate('sample_selection'))
            with col2_button:
                if st.button(translate_service.translate('select_all_samples'),
                             key="select_all_samples_graph", width='stretch'):
                    st.session_state.graph_view_samples = unique_samples
                    st.rerun()

            # Reset selection if samples changed
            if 'graph_view_samples' not in st.session_state or len(
                    [sample for sample in st.session_state.graph_view_samples if sample not in unique_samples]) > 0:
                st.session_state.graph_view_samples = []

            selected_samples = st.multiselect(
                translate_service.translate('choose_samples'),
                options=unique_samples,
                key="graph_view_samples"
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
                    key="graph_view_index",
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
            help_text = translate_service.translate('available_data_columns')
            if selected_index:
                help_text += " " + translate_service.translate('excluding_index').format(index=selected_index)
            selected_columns = st.multiselect(
                translate_service.translate('choose_columns'),
                options=filtered_data_columns,
                default=[],  # No columns selected by default
                key="graph_view_columns",
                help=help_text
            )

        # Option to combine all columns in one plot
        combine_columns = False
        if len(selected_columns) > 1:
            combine_columns = st.checkbox(
                f"📊 {translate_service.translate('combine_columns_in_same_graph')}",
                value=False,
                key="graph_view_combine_columns",
                help=translate_service.translate('combine_columns_help')
            )

        # Filter data to count actual couples
        filtered_df_all = df_all[
            (df_all['Batch'].isin(selected_batches)) &
            (df_all['Sample'].isin(selected_samples))
        ]
        displayed_couples = len(filtered_df_all[['Batch', 'Sample']].drop_duplicates())

        # Option to plot mean curves with error bands
        cols_mean = st.columns(2)
        with cols_mean[0]:
            options_mode = [translate_service.translate('individual_curves'), translate_service.translate('mean')]
            display_mode_selected = st.selectbox(translate_service.translate('select_display_mode'),
                                        options_mode,
                                        index=0,
                                        key="plot_mode")

        error_band = False
        if display_mode_selected == translate_service.translate('mean'):
            with cols_mean[1]:
                error_band = st.checkbox(translate_service.translate("error_band"), value=False, key="error_band")

        # Display summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(translate_service.translate('selected_batches'), len(selected_batches))
        with col2:
            st.metric(translate_service.translate('selected_samples'), len(selected_samples))
        with col3:
            st.metric(translate_service.translate('displayed_couples'), displayed_couples)
        with col4:
            st.metric(translate_service.translate('selected_columns'), len(selected_columns))

        # Check if we have a valid index selected
        if not selected_index:
            st.warning(translate_service.translate('select_valid_index'))
            return

        # Display graphs organized by selected columns
        if selected_columns:
            st.markdown(f"### 📊 {translate_service.translate('plots_organized_by')} {selected_index}")

            # If combine_columns is True, display all columns in one plot
            if combine_columns:
                st.markdown(f"##### 📈 {translate_service.translate('all_columns_combined')}")

                # Create one combined plot with all columns
                fig = go.Figure()

                # Define marker symbols to differentiate columns
                marker_symbols = ['circle', 'square', 'diamond', 'cross', 'x', 'triangle-up', 'triangle-down', 'star']

                # For each selected column, add traces for all batch/sample combinations
                for column_idx, column_name in enumerate(selected_columns):
                    # Assign a unique marker symbol for this column
                    marker_symbol = marker_symbols[column_idx % len(marker_symbols)]

                    # Use the optimized function to build the DataFrame for this column
                    # The subsampling task already combined real and interpolated data
                    column_df = cell_culture_state.build_selected_column_df_from_resource_set(
                        filtered_resource_set, selected_index, column_name
                    )

                    if not column_df.empty:
                        # Filter the DataFrame based on selected batches and samples
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
                            # Individual curves mode
                            if display_mode_selected == translate_service.translate('individual_curves'):
                                # Add traces for each batch_sample combination for this column
                                for col in filtered_column_df.columns:
                                    if col != selected_index:
                                        # Clean the data by removing NaN values
                                        clean_data = filtered_column_df[[selected_index, col]].dropna()

                                        if not clean_data.empty:
                                            fig.add_trace(go.Scatter(
                                                x=clean_data[selected_index],
                                                y=clean_data[col],
                                                mode='lines+markers',
                                                name=f"{column_name} - {col}",
                                                line=dict(width=2),
                                                marker=dict(size=6, symbol=marker_symbol),
                                                hovertemplate=f'<b>{column_name} - {col}</b><br>' +
                                                              f'{selected_index}: %{{x}}<br>' +
                                                              f'Valeur: %{{y:.4f}}<extra></extra>'
                                            ))
                            # Mean curves mode
                            elif display_mode_selected == translate_service.translate('mean'):
                                # Get data columns (exclude index)
                                data_cols = [col for col in filtered_column_df.columns if col != selected_index]

                                if data_cols:
                                    # Calculate mean and std across all batch_sample combinations
                                    df_mean = filtered_column_df[data_cols].mean(axis=1)
                                    df_std = filtered_column_df[data_cols].std(axis=1)

                                    # Clean data by removing NaN values
                                    clean_data = pd.DataFrame({
                                        selected_index: filtered_column_df[selected_index],
                                        'mean': df_mean,
                                        'std': df_std
                                    }).dropna()

                                    if not clean_data.empty:
                                        # Add mean trace
                                        fig.add_trace(go.Scatter(
                                            x=clean_data[selected_index],
                                            y=clean_data['mean'],
                                            mode='lines+markers',
                                            name=f"{column_name} - {translate_service.translate('mean')}",
                                            line=dict(width=2, shape='spline'),
                                            marker=dict(size=6, symbol=marker_symbol),
                                            hovertemplate=f'<b>{column_name} - {translate_service.translate("mean")}</b><br>' +
                                                          f'{selected_index}: %{{x}}<br>' +
                                                          f'{translate_service.translate("mean")}: %{{y:.4f}}<extra></extra>'
                                        ))

                                        # Add error band if requested
                                        if error_band:
                                            # Upper bound
                                            fig.add_trace(go.Scatter(
                                                x=clean_data[selected_index],
                                                y=clean_data['mean'] + clean_data['std'],
                                                mode='lines',
                                                line=dict(width=0),
                                                showlegend=False,
                                                hoverinfo='skip'
                                            ))
                                            # Lower bound with fill
                                            fig.add_trace(go.Scatter(
                                                x=clean_data[selected_index],
                                                y=clean_data['mean'] - clean_data['std'],
                                                mode='lines',
                                                line=dict(width=0),
                                                fill='tonexty',
                                                name=f'{column_name} - {translate_service.translate("error_band")} (±1 SD)',
                                                hoverinfo='skip'
                                            ))

                # Update layout
                fig.update_layout(
                    title=translate_service.translate('combined_graph_title').format(index=selected_index),
                    xaxis_title=selected_index,
                    yaxis_title=translate_service.translate('combined_y_axis'),
                    showlegend=True,
                    legend=dict(
                        x=1.02,
                        y=1,
                        xanchor='left',
                        yanchor='top'
                    ),
                    height=600
                )

                # Display the combined plot
                st.plotly_chart(fig, use_container_width=True)

                # Add note about combined view
                st.info(translate_service.translate('combined_graph_info'))

            else:
                # Original behavior: Create a section for each selected column with line plots
                for i, column_name in enumerate(selected_columns):
                    st.markdown(f"##### 📈 {column_name}")

                    # Use the optimized function to build the DataFrame for this column
                    # The subsampling task already combined real and interpolated data
                    column_df = cell_culture_state.build_selected_column_df_from_resource_set(
                        filtered_resource_set, selected_index, column_name
                    )

                    if not column_df.empty:
                        # Filter the DataFrame based on selected batches and samples
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
                            # Create interactive line plot using Plotly
                            fig = go.Figure()

                            # Individual curves mode
                            if display_mode_selected == translate_service.translate('individual_curves'):
                                # Add a line for each batch_sample combination
                                for col in filtered_column_df.columns:
                                    if col != selected_index:
                                        # Clean the data by removing NaN values
                                        clean_data = filtered_column_df[[selected_index, col]].dropna()

                                        if not clean_data.empty:
                                            fig.add_trace(go.Scatter(
                                                x=clean_data[selected_index],
                                                y=clean_data[col],
                                                mode='lines+markers',
                                                name=col,
                                                line=dict(width=2),
                                                marker=dict(size=4),
                                                hovertemplate=f'<b>{col}</b><br>' +
                                                              f'{selected_index}: %{{x}}<br>' +
                                                              f'{column_name}: %{{y:.4f}}<extra></extra>'
                                            ))

                            # Mean curves mode
                            elif display_mode_selected == translate_service.translate('mean'):
                                # Get data columns (exclude index)
                                data_cols = [col for col in filtered_column_df.columns if col != selected_index]

                                if data_cols:
                                    # Calculate mean and std across all batch_sample combinations
                                    df_mean = filtered_column_df[data_cols].mean(axis=1)
                                    df_std = filtered_column_df[data_cols].std(axis=1)

                                    # Clean data by removing NaN values
                                    clean_data = pd.DataFrame({
                                        selected_index: filtered_column_df[selected_index],
                                        'mean': df_mean,
                                        'std': df_std
                                    }).dropna()

                                    if not clean_data.empty:
                                        # Add mean trace
                                        fig.add_trace(go.Scatter(
                                            x=clean_data[selected_index],
                                            y=clean_data['mean'],
                                            mode='lines+markers',
                                            name=translate_service.translate("mean_of_selected_samples"),
                                            line=dict(width=2, shape='spline', smoothing=1),
                                            marker=dict(size=6),
                                            hovertemplate=f'<b>{translate_service.translate("mean")}</b><br>' +
                                                          f'{selected_index}: %{{x}}<br>' +
                                                          f'{column_name}: %{{y:.4f}}<extra></extra>'
                                        ))

                                        # Add error band if requested
                                        if error_band:
                                            # Upper bound
                                            fig.add_trace(go.Scatter(
                                                x=clean_data[selected_index],
                                                y=clean_data['mean'] + clean_data['std'],
                                                mode='lines',
                                                line=dict(width=0),
                                                showlegend=False,
                                                hoverinfo='skip'
                                            ))
                                            # Lower bound with fill
                                            fig.add_trace(go.Scatter(
                                                x=clean_data[selected_index],
                                                y=clean_data['mean'] - clean_data['std'],
                                                mode='lines',
                                                line=dict(width=0),
                                                fill='tonexty',
                                                name=f'{translate_service.translate("error_band")} (±1 SD)',
                                                hoverinfo='skip'
                                            ))

                            # Update layout
                            fig.update_layout(
                                title=translate_service.translate('chart_title_vs').format(
                                    column=column_name, index=selected_index),
                                xaxis_title=selected_index,
                                yaxis_title=column_name,
                                hovermode='x unified',
                                template='plotly_white', height=500, showlegend=True)

                            # Display the plot
                            st.plotly_chart(fig, use_container_width=True)

                            # Add summary statistics based on display mode
                            if display_mode_selected == translate_service.translate('individual_curves'):
                                data_columns_only = filtered_column_df.select_dtypes(include=[float, int])
                                if selected_index in data_columns_only.columns:
                                    data_columns_only = data_columns_only.drop(columns=[selected_index])

                                if not data_columns_only.empty:
                                    col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)
                                    with col_stats1:
                                        total_values = data_columns_only.count().sum()
                                        st.metric(translate_service.translate('data_points'), int(total_values))
                                    with col_stats2:
                                        mean_val = data_columns_only.mean().mean()
                                        st.metric(translate_service.translate('overall_average'), f"{mean_val:.3f}")
                                    with col_stats3:
                                        min_val = data_columns_only.min().min()
                                        st.metric(translate_service.translate('minimum'), f"{min_val:.3f}")
                                    with col_stats4:
                                        max_val = data_columns_only.max().max()
                                        st.metric(translate_service.translate('maximum'), f"{max_val:.3f}")

                                # Download button for individual curves
                                csv_data = filtered_column_df.to_csv(index=False)
                                st.download_button(
                                    label=translate_service.translate('download_data').format(column=column_name),
                                    data=csv_data,
                                    file_name=f"cell_culture_{column_name}_graph_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                    mime="text/csv", key=f"download_graph_{column_name}_{i}")

                            elif display_mode_selected == translate_service.translate('mean'):
                                # Statistics for mean data
                                if not clean_data.empty:
                                    col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)
                                    with col_stats1:
                                        total_values = len(clean_data)
                                        st.metric(translate_service.translate('data_points'), int(total_values))
                                    with col_stats2:
                                        mean_val = clean_data['mean'].mean()
                                        st.metric(translate_service.translate('overall_average'), f"{mean_val:.3f}")
                                    with col_stats3:
                                        min_val = clean_data['mean'].min()
                                        st.metric(translate_service.translate('minimum'), f"{min_val:.3f}")
                                    with col_stats4:
                                        max_val = clean_data['mean'].max()
                                        st.metric(translate_service.translate('maximum'), f"{max_val:.3f}")

                                # Download button for mean data
                                # Prepare download dataframe with mean and std
                                download_df = clean_data.copy()
                                download_df = download_df.rename(columns={'mean': f'{column_name}_mean', 'std': f'{column_name}_std'})
                                csv_data = download_df.to_csv(index=False)
                                st.download_button(
                                    label=translate_service.translate('download_data').format(column=f"{column_name} ({translate_service.translate('mean')})"),
                                    data=csv_data,
                                    file_name=f"cell_culture_{column_name}_mean_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                    mime="text/csv", key=f"download_graph_{column_name}_{i}")

                        else:
                            st.warning(translate_service.translate(
                                'no_data_matches_filters_column').format(column=column_name))
                    else:
                        st.warning(translate_service.translate(
                            'no_data_available_for_column').format(column=column_name))

                    # Add separator between columns (except for the last one)
                    if i < len(selected_columns) - 1:
                        st.markdown("---")

        else:
            st.info(translate_service.translate('select_columns_hint'))

    except Exception as e:
        st.error(f"❌ {translate_service.translate('error_details')} {str(e)}")
