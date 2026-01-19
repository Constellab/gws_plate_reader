"""
Overview Step for Cell Culture Dashboard
Displays analysis overview, input files, basic statistics, missing data information, and data visualizations
"""

from typing import Any, Dict, List

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from gws_core import Table
from gws_core.resource.resource_set.resource_set import ResourceSet

from gws_plate_reader.cell_culture_app_core.cell_culture_recipe import CellCultureRecipe
from gws_plate_reader.cell_culture_app_core.cell_culture_state import CellCultureState


def create_venn_diagram_3_sets_fallback(
    sample_sets: Dict[str, set], translate_service
) -> go.Figure:
    """
    Create a Venn diagram with 3 overlapping circles (info, raw_data, follow_up)
    showing all intersections - Fallback version for dashboard
    """

    # Extract sets
    A = sample_sets.get("info", set())  # Info
    B = sample_sets.get("raw_data", set())  # Raw Data
    C = sample_sets.get("follow_up", set())  # Follow-up

    # Calculate all regions
    only_A = len(A - B - C)  # Only Info
    only_B = len(B - A - C)  # Only Raw Data
    only_C = len(C - A - B)  # Only Follow-up
    A_and_B = len((A & B) - C)  # Info ∩ Raw Data (excluding Follow-up)
    A_and_C = len((A & C) - B)  # Info ∩ Follow-up (excluding Raw Data)
    B_and_C = len((B & C) - A)  # Raw Data ∩ Follow-up (excluding Info)
    A_and_B_and_C = len(A & B & C)  # All three (complete samples)

    # Create figure
    fig = go.Figure()

    # Circle parameters
    radius = 0.28
    Ax, Ay = 0.35, 0.5  # Info (left)
    Bx, By = 0.65, 0.5  # Raw Data (right)
    Cx, Cy = 0.5, 0.72  # Follow-up (top)

    # Create circles using parametric equations
    theta = np.linspace(0, 2 * np.pi, 100)

    # Circle A - Info (Blue)
    x_A = radius * np.cos(theta) + Ax
    y_A = radius * np.sin(theta) + Ay
    fig.add_trace(
        go.Scatter(
            x=x_A,
            y=y_A,
            fill="toself",
            fillcolor="rgba(33, 150, 243, 0.3)",
            line=dict(color="rgba(33, 150, 243, 0.8)", width=3),
            name="Info",
            mode="lines",
            hoverinfo="skip",
            showlegend=False,
        )
    )

    # Circle B - Raw Data (Green)
    x_B = radius * np.cos(theta) + Bx
    y_B = radius * np.sin(theta) + By
    fig.add_trace(
        go.Scatter(
            x=x_B,
            y=y_B,
            fill="toself",
            fillcolor="rgba(76, 175, 80, 0.3)",
            line=dict(color="rgba(76, 175, 80, 0.8)", width=3),
            name="Raw Data",
            mode="lines",
            hoverinfo="skip",
            showlegend=False,
        )
    )

    # Circle C - Follow-up (Purple)
    x_C = radius * np.cos(theta) + Cx
    y_C = radius * np.sin(theta) + Cy
    fig.add_trace(
        go.Scatter(
            x=x_C,
            y=y_C,
            fill="toself",
            fillcolor="rgba(156, 39, 176, 0.3)",
            line=dict(color="rgba(156, 39, 176, 0.8)", width=3),
            name="Follow-up",
            mode="lines",
            hoverinfo="skip",
            showlegend=False,
        )
    )

    # Add titles near the top of each circle
    fig.add_annotation(
        x=Ax, y=Ay + radius + 0.05, text="<b>Info</b>", showarrow=False, font=dict(size=14)
    )
    fig.add_annotation(
        x=Bx, y=By + radius + 0.05, text="<b>Raw Data</b>", showarrow=False, font=dict(size=14)
    )
    fig.add_annotation(
        x=Cx, y=Cy + radius + 0.05, text="<b>Follow-up</b>", showarrow=False, font=dict(size=14)
    )

    # Add region counts
    fig.add_annotation(x=Ax - 0.13, y=Ay, text=str(only_A), showarrow=False, font=dict(size=14))
    fig.add_annotation(x=Bx + 0.13, y=By, text=str(only_B), showarrow=False, font=dict(size=14))
    fig.add_annotation(x=Cx, y=Cy + 0.18, text=str(only_C), showarrow=False, font=dict(size=14))
    fig.add_annotation(
        x=(Ax + Bx) / 2, y=Ay - 0.08, text=str(A_and_B), showarrow=False, font=dict(size=14)
    )
    fig.add_annotation(
        x=Ax + 0.07, y=Ay + 0.16, text=str(A_and_C), showarrow=False, font=dict(size=14)
    )
    fig.add_annotation(
        x=Bx - 0.07, y=By + 0.16, text=str(B_and_C), showarrow=False, font=dict(size=14)
    )

    # Center - All three (complete)
    fig.add_annotation(
        x=Cx,
        y=Ay + 0.1,
        text=f"<b>{A_and_B_and_C}</b>",
        showarrow=False,
        font=dict(size=16, color="darkgreen"),
        bgcolor="rgba(255, 255, 255, 0.9)",
        borderpad=4,
        bordercolor="darkgreen",
        borderwidth=2,
    )

    # Update layout
    fig.update_layout(
        title=translate_service.translate("missing_data_pattern"),
        showlegend=False,
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False, range=[0, 1]),
        yaxis=dict(showticklabels=False, showgrid=False, zeroline=False, range=[0.2, 1.05]),
        height=500,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )

    return fig


def prepare_complete_data_for_visualization(
    resource_set: ResourceSet, cell_culture_state: CellCultureState
) -> List[Dict[str, str]]:
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

                if hasattr(resource, "tags") and resource.tags:
                    for tag in resource.tags.get_tags():
                        if tag.key == cell_culture_state.TAG_BATCH:
                            batch = tag.value
                        elif tag.key == cell_culture_state.TAG_SAMPLE:
                            sample = tag.value
                        elif tag.key == cell_culture_state.TAG_MEDIUM:
                            medium = tag.value
                        elif tag.key == cell_culture_state.TAG_MISSING_VALUE:
                            missing_value = tag.value

                # Only include if no missing data
                if not missing_value:
                    visualization_data.append(
                        {
                            "Batch": batch,
                            "Sample": sample,
                            "Medium": medium,
                            "Resource_Name": resource_name,
                        }
                    )

        return visualization_data
    except Exception:
        return []


def prepare_extended_complete_data(
    resource_set: ResourceSet,
    cell_culture_state: CellCultureState,
    selected_columns: List[str] = None,
) -> List[Dict[str, Any]]:
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

                if hasattr(resource, "tags") and resource.tags:
                    for tag in resource.tags.get_tags():
                        if tag.key == cell_culture_state.TAG_BATCH:
                            batch = tag.value
                        elif tag.key == cell_culture_state.TAG_SAMPLE:
                            sample = tag.value
                        elif tag.key == cell_culture_state.TAG_MEDIUM:
                            medium = tag.value
                        elif tag.key == cell_culture_state.TAG_MISSING_VALUE:
                            missing_value = tag.value

                # Only process resources without missing data
                if not missing_value:
                    resource_data = {
                        "Batch": batch,
                        "Sample": sample,
                        "Medium": medium,
                        "Resource_Name": resource_name,
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


def render_overview_step(recipe: CellCultureRecipe, cell_culture_state: CellCultureState) -> None:
    """Render the overview step showing basic recipe information and visualizations"""

    translate_service = cell_culture_state.get_translate_service()

    # Get the load scenario (main scenario) which should already exist when recipe is created
    load_scenario = recipe.get_load_scenario()

    if not load_scenario:
        st.error(translate_service.translate("no_resourceset_found"))
        return

    try:
        # Get the ResourceSet from the load scenario
        resource_set = cell_culture_state.get_load_scenario_output()
        if not resource_set:
            st.warning(translate_service.translate("no_data_found"))
            return

        resources = resource_set.get_resources()

        # Basic statistics
        st.markdown(f"### {translate_service.translate('basic_statistics')}")

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

                if hasattr(resource, "tags") and resource.tags:
                    for tag in resource.tags.get_tags():
                        if tag.key == cell_culture_state.TAG_BATCH:
                            batch = tag.value
                        elif tag.key == cell_culture_state.TAG_SAMPLE:
                            sample = tag.value
                        elif tag.key == cell_culture_state.TAG_MEDIUM:
                            medium = tag.value
                        elif tag.key == cell_culture_state.TAG_MISSING_VALUE:
                            missing_value = tag.value

                resource_info = {
                    "Batch": batch,
                    "Sample": sample,
                    "Medium": medium,
                    "Resource": resource,
                }

                if missing_value:
                    missing_info = resource_info.copy()
                    missing_info["Missing Value"] = missing_value
                    missing_data.append(missing_info)
                else:
                    valid_data.append(resource_info)

                all_data.append(df)

        # Display basic statistics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            total_samples = len(valid_data) + len(missing_data)
            st.metric(translate_service.translate("total_samples"), total_samples)

        with col2:
            st.metric(translate_service.translate("valid_samples"), len(valid_data))

        with col3:
            completion_rate = (len(valid_data) / total_samples * 100) if total_samples > 0 else 0
            st.metric(translate_service.translate("completion_rate"), f"{completion_rate:.1f}%")

        with col4:
            st.metric(translate_service.translate("data_tables"), len(resources))

        # Try to get the Venn diagram from the load scenario output
        venn_diagram = cell_culture_state.get_venn_diagram_output()

        if venn_diagram is not None:
            # Display the pre-computed Venn diagram from the load task
            try:
                fig = venn_diagram.get_figure()
                st.plotly_chart(fig, use_container_width=True)
            except Exception:
                # Fallback: compute on the fly if there's an issue
                if missing_data or valid_data:
                    # Build sets of (batch, sample) tuples for each data type
                    sample_sets = {"info": set(), "raw_data": set(), "follow_up": set()}

                    # Process all data (valid and missing)
                    for item in valid_data + missing_data:
                        batch = item.get("Batch", "")
                        sample = item.get("Sample", "")
                        missing_value = item.get("Missing Value", "")

                        if batch and sample:
                            sample_tuple = (batch, sample)

                            # Parse missing types (empty string means no missing data for basic types)
                            missing_types = (
                                [t.strip() for t in missing_value.split(",") if t.strip()]
                                if missing_value
                                else []
                            )

                            # Add to sets for data types that are NOT missing
                            if "info" not in missing_types:
                                sample_sets["info"].add(sample_tuple)
                            if "raw_data" not in missing_types:
                                sample_sets["raw_data"].add(sample_tuple)
                            if (
                                "follow_up" not in missing_types
                                and "follow_up_empty" not in missing_types
                            ):
                                sample_sets["follow_up"].add(sample_tuple)

                    # Create Venn diagram
                    fig_venn = create_venn_diagram_3_sets_fallback(sample_sets, translate_service)
                    st.plotly_chart(fig_venn, use_container_width=True)
        elif missing_data or valid_data:
            # Fallback: compute on the fly if venn diagram output not found
            # Build sets of (batch, sample) tuples for each data type
            sample_sets = {"info": set(), "raw_data": set(), "follow_up": set()}

            # Process all data (valid and missing)
            for item in valid_data + missing_data:
                batch = item.get("Batch", "")
                sample = item.get("Sample", "")
                missing_value = item.get("Missing Value", "")

                if batch and sample:
                    sample_tuple = (batch, sample)

                    # Parse missing types (empty string means no missing data for basic types)
                    missing_types = (
                        [t.strip() for t in missing_value.split(",") if t.strip()]
                        if missing_value
                        else []
                    )

                    # Add to sets for data types that are NOT missing
                    if "info" not in missing_types:
                        sample_sets["info"].add(sample_tuple)
                    if "raw_data" not in missing_types:
                        sample_sets["raw_data"].add(sample_tuple)
                    if "follow_up" not in missing_types and "follow_up_empty" not in missing_types:
                        sample_sets["follow_up"].add(sample_tuple)

            # Create Venn diagram
            fig_venn = create_venn_diagram_3_sets_fallback(sample_sets, translate_service)
            st.plotly_chart(fig_venn, use_container_width=True)

        if missing_data:
            # Section 3: Missing data information
            st.markdown(f"### {translate_service.translate('missing_data_couples')}")

            df_missing = pd.DataFrame(missing_data)

            # Make the detailed table collapsible
            with st.expander(
                translate_service.translate("view_missing_data_details"), expanded=False
            ):
                # Only show Batch, Sample, and Missing Value columns
                display_cols = ["Batch", "Sample", "Missing Value"]
                df_display = df_missing[display_cols]

                st.dataframe(
                    df_display,
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "Batch": st.column_config.TextColumn(
                            translate_service.translate("column_batch")
                        ),
                        "Sample": st.column_config.TextColumn(
                            translate_service.translate("column_sample")
                        ),
                        "Missing Value": st.column_config.TextColumn(
                            translate_service.translate("column_missing_value"),
                            help=translate_service.translate("column_missing_value"),
                        ),
                    },
                )
        else:
            st.success(translate_service.translate("no_missing_data"))

        # Section 4: Data Visualizations for complete data
        st.markdown(f"### {translate_service.translate('complete_data_viz')}")

        # Prepare visualization data for complete (non-missing) data
        complete_visualization_data = prepare_complete_data_for_visualization(
            resource_set, cell_culture_state
        )

        if complete_visualization_data:
            # Get unique values for grouping
            unique_batches = sorted(
                list(set(item["Batch"] for item in complete_visualization_data))
            )
            unique_samples = sorted(
                list(set(item["Sample"] for item in complete_visualization_data))
            )
            unique_media = sorted(list(set(item["Medium"] for item in complete_visualization_data)))

            # Create summary charts
            col1, col2 = st.columns(2)

            with col1:
                # Pie chart of samples by batch
                if len(unique_batches) > 1:
                    batch_counts = {}
                    for item in complete_visualization_data:
                        batch = item["Batch"]
                        batch_counts[batch] = batch_counts.get(batch, 0) + 1

                    fig_batch = px.pie(
                        values=list(batch_counts.values()),
                        names=list(batch_counts.keys()),
                        title=translate_service.translate("batch_distribution"),
                    )
                    fig_batch.update_layout(height=400)
                    st.plotly_chart(fig_batch, use_container_width=True)
                else:
                    st.info(translate_service.translate("distribution_single_batch"))

            with col2:
                # Bar chart of samples by medium
                if len(unique_media) > 1:
                    medium_counts = {}
                    for item in complete_visualization_data:
                        medium = item["Medium"]
                        medium_counts[medium] = medium_counts.get(medium, 0) + 1

                    fig_medium = px.bar(
                        x=list(medium_counts.keys()),
                        y=list(medium_counts.values()),
                        title=translate_service.translate("medium_distribution"),
                        labels={
                            "x": translate_service.translate("medium_label"),
                            "y": translate_service.translate("samples_count"),
                        },
                    )
                    fig_medium.update_layout(height=400)
                    st.plotly_chart(fig_medium, use_container_width=True)
                else:
                    st.info(translate_service.translate("distribution_single_medium"))
        else:
            st.warning(translate_service.translate("no_complete_data"))

    except Exception as e:
        st.error(translate_service.translate("error_loading_preview").format(error=str(e)))
