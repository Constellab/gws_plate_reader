"""
Overview Step for Fermentalg Dashboard
Displays analysis overview, input files, basic statistics, missing data information, and data visualizations
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from typing import List, Dict, Tuple, Optional, Any

from gws_core import Table, Scenario
from gws_core.resource.resource_set.resource_set import ResourceSet
from gws_plate_reader.fermentalg_dashboard._fermentalg_dashboard_core.state import State
from gws_plate_reader.fermentalg_dashboard._fermentalg_dashboard_core.analyse import Analyse


def prepare_complete_data_for_visualization(resource_set: ResourceSet, fermentalg_state: State) -> List[Dict[str, str]]:
    """Prepare complete (non-missing) data from ResourceSet for visualization"""
    try:
        resources = resource_set.get_resources()
        visualization_data = []

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
                    visualization_data.append({
                        'Batch': batch,
                        'Sample': sample,
                        'Medium': medium,
                        'Resource_Name': resource_name
                    })

        return visualization_data
    except Exception:
        return []


def prepare_extended_complete_data(resource_set: ResourceSet, fermentalg_state: State,
                                   selected_columns: List[str] = None) -> List[Dict[str, Any]]:
    """Prepare extended complete data from ResourceSet including selected columns"""
    try:
        resources = resource_set.get_resources()
        visualization_data = []

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

                # Only process resources without missing data
                if not missing_value:
                    resource_data = {
                        'Batch': batch,
                        'Sample': sample,
                        'Medium': medium,
                        'Resource_Name': resource_name
                    }

                    # Add selected column data if requested
                    if selected_columns:
                        df = resource.get_data()
                        for col in selected_columns:
                            if col in df.columns:
                                # Get the first non-null value for this column
                                col_values = df[col].dropna()
                                if not col_values.empty:
                                    resource_data[col] = col_values.iloc[0]

                    visualization_data.append(resource_data)

        return visualization_data
    except Exception:
        return []


def render_overview_step(analyse: Analyse, fermentalg_state: State) -> None:
    """Render the overview step showing basic analysis information and visualizations"""

    translate_service = fermentalg_state.get_translate_service()

    # Get the load scenario (main scenario) which should already exist when analyse is created
    load_scenario = analyse.get_load_scenario()

    if not load_scenario:
        st.error(translate_service.translate('no_resourceset_found'))
        return

    try:
        # Get the ResourceSet from the load scenario
        resource_set = fermentalg_state.get_load_scenario_output()
        if not resource_set:
            st.warning(translate_service.translate('no_data_found'))
            return

        st.subheader(translate_service.translate('analysis_overview'))

        # Display input files information
        st.subheader(translate_service.translate('input_files'))

        resources = resource_set.get_resources()
        file_info = []
        for resource_name, resource in resources.items():
            if isinstance(resource, Table):
                file_info.append({
                    "Nom du fichier": resource_name,
                    "Type": "Table",
                    "Nombre de lignes": len(resource.get_data()) if hasattr(resource, 'get_data') else "N/A"
                })

        if file_info:
            st.dataframe(pd.DataFrame(file_info), use_container_width=True, hide_index=True)
        else:
            st.info(translate_service.translate('no_input_files'))

        # Section 2: Basic statistics
        st.subheader(translate_service.translate('basic_statistics'))

        # Prepare data for analysis
        valid_data = []
        missing_data = []
        all_data = []

        for resource_name, resource in resources.items():
            if isinstance(resource, Table):
                df = resource.get_data()

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

                resource_info = {
                    'Batch': batch,
                    'Sample': sample,
                    'Medium': medium,
                    'Resource': resource
                }

                if missing_value:
                    missing_info = resource_info.copy()
                    missing_info['Missing Value'] = missing_value
                    missing_data.append(missing_info)
                else:
                    valid_data.append(resource_info)

                all_data.append(df)

        # Display basic statistics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            total_samples = len(valid_data) + len(missing_data)
            st.metric(translate_service.translate('total_samples'), total_samples)

        with col2:
            st.metric(translate_service.translate('valid_samples'), len(valid_data))

        with col3:
            completion_rate = (len(valid_data) / total_samples * 100) if total_samples > 0 else 0
            st.metric(translate_service.translate('completion_rate'), f"{completion_rate:.1f}%")

        with col4:
            st.metric(translate_service.translate('data_tables'), len(resources))

        # Section 3: Missing data information
        st.subheader(translate_service.translate('missing_data_couples'))

        if missing_data:
            df_missing = pd.DataFrame(missing_data)
            # Only show Batch, Sample, and Missing Value columns
            display_cols = ['Batch', 'Sample', 'Missing Value']
            df_display = df_missing[display_cols]

            st.dataframe(
                df_display,
                use_container_width=True,
                hide_index=True,
                column_config={
                    'Batch': st.column_config.TextColumn('Batch'),
                    'Sample': st.column_config.TextColumn('Sample'),
                    'Missing Value': st.column_config.TextColumn(
                        'Donnée manquante',
                        help='Types de données manquantes'
                    )
                }
            )
        else:
            st.success(translate_service.translate('no_missing_data'))

        # Section 4: Data Visualizations for complete data
        st.subheader(translate_service.translate('complete_data_viz'))

        # Prepare visualization data for complete (non-missing) data
        complete_visualization_data = prepare_complete_data_for_visualization(resource_set, fermentalg_state)

        if complete_visualization_data:

            # Get unique values for grouping
            unique_batches = sorted(list(set(item['Batch'] for item in complete_visualization_data)))
            unique_samples = sorted(list(set(item['Sample'] for item in complete_visualization_data)))
            unique_media = sorted(list(set(item['Medium'] for item in complete_visualization_data)))

            # Create summary charts
            col1, col2 = st.columns(2)

            with col1:
                # Pie chart of samples by batch
                if len(unique_batches) > 1:
                    batch_counts = {}
                    for item in complete_visualization_data:
                        batch = item['Batch']
                        batch_counts[batch] = batch_counts.get(batch, 0) + 1

                    fig_batch = px.pie(
                        values=list(batch_counts.values()),
                        names=list(batch_counts.keys()),
                        title=translate_service.translate('batch_distribution')
                    )
                    fig_batch.update_layout(height=400)
                    st.plotly_chart(fig_batch, use_container_width=True)
                else:
                    st.info(translate_service.translate('distribution_single_batch'))

            with col2:
                # Bar chart of samples by medium
                if len(unique_media) > 1:
                    medium_counts = {}
                    for item in complete_visualization_data:
                        medium = item['Medium']
                        medium_counts[medium] = medium_counts.get(medium, 0) + 1

                    fig_medium = px.bar(
                        x=list(medium_counts.keys()),
                        y=list(medium_counts.values()),
                        title=translate_service.translate('medium_distribution'),
                        labels={'x': translate_service.translate('medium_label'),
                                'y': translate_service.translate('samples_count')})
                    fig_medium.update_layout(height=400)
                    st.plotly_chart(fig_medium, use_container_width=True)
                else:
                    st.info(translate_service.translate('distribution_single_medium'))
        else:
            st.warning(translate_service.translate('no_complete_data'))

    except Exception as e:
        st.error(f"❌ Erreur lors du chargement de l'aperçu: {str(e)}")
