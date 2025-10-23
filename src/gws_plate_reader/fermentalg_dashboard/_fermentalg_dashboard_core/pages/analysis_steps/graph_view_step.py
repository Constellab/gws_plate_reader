"""
Graph View Step for Fermentalg Dashboard
Handles graph visualizations with filtering and interactive plots using Plotly
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import Optional

from gws_core import Scenario, ScenarioStatus
from gws_plate_reader.fermentalg_dashboard._fermentalg_dashboard_core import State
from gws_plate_reader.fermentalg_dashboard._fermentalg_dashboard_core.analyse import Analyse


def render_graph_view_step(
        analyse: Analyse, fermentalg_state: State, selection_scenario: Optional[Scenario] = None) -> None:
    """Render the graph view step with data visualizations using Plotly

    :param analyse: The Analyse instance
    :param fermentalg_state: The fermentalg state
    :param selection_scenario: Specific selection scenario to use (if None, use latest)
    """

    translate_service = fermentalg_state.get_translate_service()

    try:
        # Check if selection scenarios exist
        if not analyse.has_selection_scenarios():
            st.warning(translate_service.translate('no_selection_made'))
            return

        # Use provided selection scenario or get the latest one
        if selection_scenario:
            target_scenario = selection_scenario
            st.info(f"🎯 Affichage des graphiques pour : **{target_scenario.title}**")
        else:
            # Get the latest selection scenario (backward compatibility)
            selection_scenarios = analyse.get_selection_scenarios()
            target_scenario = selection_scenarios[0] if selection_scenarios else None

        if not target_scenario or target_scenario.status != ScenarioStatus.SUCCESS:
            st.warning(translate_service.translate('selection_not_successful'))
            return

        st.subheader(translate_service.translate('graph_visualizations'))

        # Get interpolated data from selection scenario
        filtered_resource_set = fermentalg_state.get_interpolation_scenario_output(target_scenario)
        if not filtered_resource_set:
            st.error(translate_service.translate('cannot_retrieve_filtered_data'))
            return

        # Extract data for visualization using State method
        visualization_data = fermentalg_state.prepare_data_for_visualization(filtered_resource_set)

        if not visualization_data:
            st.warning(translate_service.translate('no_data_for_visualization'))
            return

        # Create dataframe from visualization data
        # We need to expand the data to include all columns from the tables
        from gws_core import Table
        all_data_rows = []
        resources = filtered_resource_set.get_resources()

        for resource_name, resource in resources.items():
            if isinstance(resource, Table):
                # Extract metadata
                batch = ""
                sample = ""
                medium = ""

                if hasattr(resource, 'tags') and resource.tags:
                    for tag in resource.tags.get_tags():
                        if tag.key == fermentalg_state.TAG_BATCH:
                            batch = tag.value
                        elif tag.key == fermentalg_state.TAG_SAMPLE:
                            sample = tag.value
                        elif tag.key == fermentalg_state.TAG_MEDIUM:
                            medium = tag.value

                # Get DataFrame and add metadata columns
                df = resource.get_data()
                for _, row in df.iterrows():
                    row_dict = row.to_dict()
                    row_dict['Batch'] = batch
                    row_dict['Sample'] = sample
                    row_dict['Medium'] = medium
                    row_dict['Resource_Name'] = resource_name
                    all_data_rows.append(row_dict)

        df_all = pd.DataFrame(all_data_rows)

        # Get available columns for selection using the tagging system
        index_columns = fermentalg_state.get_index_columns_from_resource_set(filtered_resource_set)
        data_columns = fermentalg_state.get_data_columns_from_resource_set(filtered_resource_set)

        # === Section 1: Filters ===
        st.markdown("---")
        st.subheader(translate_service.translate('filters_and_selection'))

        # Get unique values for filters
        unique_batches = sorted(df_all['Batch'].unique().tolist())
        unique_samples = sorted(df_all['Sample'].unique().tolist())

        # Create 2x2 grid for filters
        col1, col2 = st.columns(2)

        with col1:
            st.write(translate_service.translate('batch_selection'))
            selected_batches = st.multiselect(
                "Choisir les batches à afficher",
                options=unique_batches,
                default=unique_batches,  # All batches selected by default
                key="graph_view_batches"
            )

        with col2:
            st.write(translate_service.translate('sample_selection'))
            selected_samples = st.multiselect(
                "Choisir les échantillons à afficher",
                options=unique_samples,
                default=unique_samples,  # All samples selected by default
                key="graph_view_samples"
            )

        # Second row of the 2x2 grid
        col3, col4 = st.columns(2)

        with col3:
            st.write(translate_service.translate('index_column'))
            # Check if index columns are available
            if index_columns:
                selected_index = st.selectbox(
                    "Choisir la colonne à utiliser comme index",
                    options=index_columns,
                    index=0,
                    key="graph_view_index",
                    help="La colonne sélectionnée sera utilisée comme axe X pour les graphiques"
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
                "Choisir les colonnes à afficher",
                options=filtered_data_columns,
                default=[],  # No columns selected by default
                key="graph_view_columns",
                help=f"Colonnes de données disponibles" +
                (f" (excluant l'index '{selected_index}')" if selected_index else "")
            )

        # Show info message if a data column is used as index
        if selected_index and selected_index in data_columns and selected_index not in ['Batch', 'Sample']:
            st.info(
                f"💡 La colonne '{selected_index}' est utilisée comme index et a été retirée de la liste des colonnes sélectionnables.")

        # Filter data to count actual couples
        filtered_df_all = df_all[
            (df_all['Batch'].isin(selected_batches)) &
            (df_all['Sample'].isin(selected_samples))
        ]
        displayed_couples = len(filtered_df_all[['Batch', 'Sample']].drop_duplicates())

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
            st.subheader(f"📊 Graphiques organisés par {selected_index}")

            # Create a section for each selected column with line plots
            for i, column_name in enumerate(selected_columns):
                st.markdown(f"### 📈 {column_name}")

                # Use the optimized function to build the DataFrame for this column
                column_df = fermentalg_state.build_selected_column_df_from_resource_set(
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

                        # Update layout
                        fig.update_layout(
                            title=translate_service.translate('chart_title_vs').format(
                                column=column_name, index=selected_index),
                            xaxis_title=selected_index, yaxis_title=column_name, hovermode='x unified',
                            template='plotly_white', height=500, showlegend=True)

                        # Display the plot
                        st.plotly_chart(fig, use_container_width=True)

                        # Add summary statistics
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

                        # Download button for this specific column data
                        csv_data = filtered_column_df.to_csv(index=False)
                        st.download_button(
                            label=translate_service.translate('download_data').format(column=column_name),
                            data=csv_data,
                            file_name=f"fermentalg_{column_name}_graph_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv", key=f"download_graph_{column_name}_{i}")
                    else:
                        st.warning(f"⚠️ Aucune donnée correspond aux filtres sélectionnés pour {column_name}")
                else:
                    st.warning(f"⚠️ Aucune donnée disponible pour la colonne {column_name}")

                # Add separator between columns (except for the last one)
                if i < len(selected_columns) - 1:
                    st.markdown("---")

        else:
            st.info(translate_service.translate('select_columns_hint'))

    except Exception as e:
        st.error(f"❌ Erreur lors du chargement de la vue graphique: {str(e)}")
