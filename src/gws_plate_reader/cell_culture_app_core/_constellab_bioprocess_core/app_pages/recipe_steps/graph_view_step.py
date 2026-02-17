"""
Graph View Step for Cell Culture Dashboard
Handles graph visualizations with filtering and interactive plots using Plotly
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from gws_core import Scenario, ScenarioProxy, ScenarioStatus, Table
from gws_plate_reader.cell_culture_app_core._constellab_bioprocess_core.cell_culture_recipe import (
    CellCultureRecipe,
)
from gws_plate_reader.cell_culture_app_core._constellab_bioprocess_core.cell_culture_state import (
    CellCultureState,
)


def render_graph_view_step(
    recipe: CellCultureRecipe,
    cell_culture_state: CellCultureState,
    scenario: Scenario | None = None,
    output_name: str | None = None,
    filtered_resource_set=None,
    target_scenario: Scenario | None = None,
    visualization_data: list | None = None,
    selected_batches: list | None = None,
    selected_samples: list | None = None,
    selected_index: str | None = None,
    selected_columns: list | None = None,
    all_data_rows: list | None = None,
    well_data: dict | None = None,
) -> None:
    """Render the graph view step with data visualizations using Plotly

    :param recipe: The Recipe instance
    :param cell_culture_state: The cell culture state
    :param scenario: The scenario to display (selection or quality check)
    :param output_name: The output name to retrieve from the scenario
    :param filtered_resource_set: Pre-loaded resource set (optional, for performance)
    :param target_scenario: Pre-loaded target scenario (optional, for performance)
    :param visualization_data: Pre-loaded visualization data (optional, for performance)
    :param selected_batches: Pre-selected batches (optional, from parent)
    :param selected_samples: Pre-selected samples (optional, from parent)
    :param selected_index: Pre-selected index column (optional, from parent)
    :param selected_columns: Pre-selected data columns (optional, from parent)
    :param all_data_rows: Pre-built all_data_rows (optional, from parent)
    :param well_data: Well metadata for microplate mode (optional)
    """

    translate_service = cell_culture_state.get_translate_service()

    try:
        # If data not provided, load it (backward compatibility)
        if filtered_resource_set is None or target_scenario is None or visualization_data is None:
            # If scenario is provided, use it
            if scenario:
                target_scenario = scenario

                if target_scenario.status != ScenarioStatus.SUCCESS:
                    st.warning(translate_service.translate("scenario_not_successful_yet"))
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
                        st.error(translate_service.translate("cannot_retrieve_data"))
                        return

                except Exception as e:
                    st.error(
                        translate_service.translate("error_retrieving_data").format(error=str(e))
                    )
                    return

            # Backward compatibility: if no scenario provided, try to get latest selection
            else:
                if not recipe.has_selection_scenarios():
                    st.warning(translate_service.translate("no_selection_made"))
                    return

                selection_scenarios = recipe.get_selection_scenarios()
                target_scenario = selection_scenarios[0] if selection_scenarios else None

                if not target_scenario or target_scenario.status != ScenarioStatus.SUCCESS:
                    st.warning(translate_service.translate("selection_not_successful"))
                    return

                filtered_resource_set = cell_culture_state.get_interpolation_scenario_output(
                    target_scenario
                )
                if not filtered_resource_set:
                    st.error(translate_service.translate("cannot_retrieve_filtered_data"))
                    return

            # Extract data for visualization using State method
            visualization_data = cell_culture_state.prepare_data_for_visualization(
                filtered_resource_set
            )

            if not visualization_data:
                st.warning(translate_service.translate("no_data_for_visualization"))
                return

        # Build all_data_rows if not provided
        if all_data_rows is None:
            all_data_rows = []
            resources = filtered_resource_set.get_resources()

            for resource_name, resource in resources.items():
                if isinstance(resource, Table):
                    # Extract metadata from tags
                    batch = ""
                    sample = ""
                    medium = ""

                    if hasattr(resource, "tags") and resource.tags:
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
                        row_dict["Batch"] = batch
                        row_dict["Sample"] = sample
                        # Only add Medium if recipe has medium info
                        if recipe.has_medium_info:
                            row_dict["Medium"] = medium
                        row_dict["Resource_Name"] = resource_name
                        all_data_rows.append(row_dict)

        # Create dataframe from all_data_rows for detailed plotting

        df_all = pd.DataFrame(all_data_rows)

        # Option to combine all columns in one plot
        combine_columns = False
        if len(selected_columns) > 1:
            combine_columns = st.checkbox(
                f"📊 {translate_service.translate('combine_columns_in_same_graph')}",
                value=False,
                key="graph_view_combine_columns",
                help=translate_service.translate("combine_columns_help"),
            )

        # Filter data to count actual couples
        filtered_df_all = df_all[
            (df_all["Batch"].isin(selected_batches)) & (df_all["Sample"].isin(selected_samples))
        ]
        displayed_couples = len(filtered_df_all[["Batch", "Sample"]].drop_duplicates())

        # Option to plot mean curves with error bands
        is_microplate = recipe.analysis_type == "microplate"

        options_mode = [
            translate_service.translate("individual_curves"),
            translate_service.translate("mean_selected_batches"),
            translate_service.translate("plot_by_batch"),
        ]
        if is_microplate and well_data:
            options_mode.append(translate_service.translate("plot_by_replicate"))

        cols_mean = st.columns(2)
        with cols_mean[0]:
            display_mode_selected = st.selectbox(
                translate_service.translate("select_display_mode"),
                options_mode,
                index=0,
                key="plot_mode",
            )

        error_band = False
        if display_mode_selected != translate_service.translate("individual_curves"):
            with cols_mean[1]:
                error_band = st.checkbox(
                    translate_service.translate("error_band"), value=False, key="error_band"
                )

        # Replicate selectors (only for "Plot by replicate" mode)
        replicate_type = None
        selected_replicate_values = []
        replicate_well_mapping = {}  # maps "batch_sample" -> replicate_value

        if display_mode_selected == translate_service.translate("plot_by_replicate") and well_data:
            # Extract available replicate keys from well_data (same logic as microplate "Color by")
            available_replicate_keys = set()
            for _well, data in well_data.items():
                if isinstance(data, dict):
                    for plate_or_value in data.values():
                        if isinstance(plate_or_value, dict):
                            available_replicate_keys.update(plate_or_value.keys())

            available_replicate_keys = sorted(available_replicate_keys)
            if "Medium" in available_replicate_keys:
                available_replicate_keys.remove("Medium")
                available_replicate_keys = ["Medium"] + available_replicate_keys

            cols_replicate = st.columns(2)
            with cols_replicate[0]:
                replicate_type = st.selectbox(
                    translate_service.translate("replicate_type"),
                    options=available_replicate_keys,
                    index=0,
                    key="replicate_type_selector",
                )

            if replicate_type:
                # Extract unique values for the selected replicate type
                unique_replicate_values = set()
                for base_well, data in well_data.items():
                    if isinstance(data, dict):
                        for plate_name, plate_data in data.items():
                            if isinstance(plate_data, dict):
                                value = plate_data.get(replicate_type, "")
                                if value != "":
                                    unique_replicate_values.add(str(value))
                                    # Build mapping: "plate_sample" -> replicate_value
                                    replicate_well_mapping[f"{plate_name}_{base_well}"] = str(value)

                unique_replicate_values = sorted(unique_replicate_values)

                with cols_replicate[1]:
                    selected_replicate_values = st.multiselect(
                        translate_service.translate("replicate_values"),
                        options=unique_replicate_values,
                        default=unique_replicate_values,
                        key="replicate_values_selector",
                    )

        # Display summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(translate_service.translate("selected_batches"), len(selected_batches))
        with col2:
            st.metric(translate_service.translate("selected_samples"), len(selected_samples))
        with col3:
            st.metric(translate_service.translate("displayed_couples"), displayed_couples)
        with col4:
            st.metric(translate_service.translate("selected_columns"), len(selected_columns))

        # Check if we have a valid index selected
        if not selected_index:
            st.warning(translate_service.translate("select_valid_index"))
            return

        # Display graphs organized by selected columns
        if selected_columns:
            st.markdown("---")

            st.markdown(
                f"### 📊 {translate_service.translate('plots_organized_by')} {selected_index}"
            )

            # If combine_columns is True, display all columns in one plot
            if combine_columns:
                st.markdown(f"##### 📈 {translate_service.translate('all_columns_combined')}")

                # Create a single figure with multiple overlaid y-axes
                num_columns = len(selected_columns)
                fig = go.Figure()

                # Define marker symbols to differentiate columns
                marker_symbols = [
                    "circle",
                    "square",
                    "diamond",
                    "cross",
                    "x",
                    "triangle-up",
                    "triangle-down",
                    "star",
                ]

                # Axis colors to visually associate traces with their y-axis
                axis_colors = [
                    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
                    "#9467bd", "#8c564b", "#e377c2", "#7f7f7f",
                ]

                # For each selected column, add traces assigned to its own y-axis
                for column_idx, column_name in enumerate(selected_columns):
                    # Assign a unique marker symbol for this column
                    marker_symbol = marker_symbols[column_idx % len(marker_symbols)]
                    axis_color = axis_colors[column_idx % len(axis_colors)]

                    # First column uses "y", subsequent use "y2", "y3", etc.
                    yaxis_ref = "y" if column_idx == 0 else f"y{column_idx + 1}"

                    # Use the optimized function to build the DataFrame for this column
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
                        columns_to_keep = [selected_index]
                        for col in column_df.columns:
                            if col != selected_index and col in batch_sample_combinations:
                                columns_to_keep.append(col)

                        # Filter the DataFrame
                        filtered_column_df = (
                            column_df[columns_to_keep]
                            if len(columns_to_keep) > 1
                            else column_df[[selected_index]]
                        )

                        if len(filtered_column_df.columns) > 1:
                            # Individual curves mode
                            if display_mode_selected == translate_service.translate(
                                "individual_curves"
                            ):
                                for col in filtered_column_df.columns:
                                    if col != selected_index:
                                        clean_data = filtered_column_df[
                                            [selected_index, col]
                                        ].dropna()

                                        if not clean_data.empty:
                                            fig.add_trace(
                                                go.Scatter(
                                                    x=clean_data[selected_index],
                                                    y=clean_data[col],
                                                    mode="lines+markers",
                                                    name=f"{column_name} - {col}",
                                                    line={"width": 2},
                                                    marker={"size": 6, "symbol": marker_symbol},
                                                    legendgroup=column_name,
                                                    legendgrouptitle_text=column_name,
                                                    yaxis=yaxis_ref,
                                                    hovertemplate=f"<b>{column_name} - {col}</b><br>"
                                                    + f"{selected_index}: %{{x}}<br>"
                                                    + f"{column_name}: %{{y:.4f}}<extra></extra>",
                                                ),
                                            )
                            # Mean curves mode
                            elif display_mode_selected == translate_service.translate(
                                "mean_selected_batches"
                            ):
                                data_cols = [
                                    col
                                    for col in filtered_column_df.columns
                                    if col != selected_index
                                ]

                                if data_cols:
                                    df_mean = filtered_column_df[data_cols].mean(axis=1)
                                    df_std = filtered_column_df[data_cols].std(axis=1)

                                    clean_data = pd.DataFrame(
                                        {
                                            selected_index: filtered_column_df[selected_index],
                                            "mean": df_mean,
                                            "std": df_std,
                                        }
                                    ).dropna()

                                    if not clean_data.empty:
                                        fig.add_trace(
                                            go.Scatter(
                                                x=clean_data[selected_index],
                                                y=clean_data["mean"],
                                                mode="lines+markers",
                                                name=f"{column_name} - {translate_service.translate('mean')}",
                                                line={"width": 2, "shape": "spline"},
                                                marker={"size": 6, "symbol": marker_symbol},
                                                legendgroup=column_name,
                                                legendgrouptitle_text=column_name,
                                                yaxis=yaxis_ref,
                                                hovertemplate=f"<b>{column_name} - {translate_service.translate('mean')}</b><br>"
                                                + f"{selected_index}: %{{x}}<br>"
                                                + f"{translate_service.translate('mean')}: %{{y:.4f}}<extra></extra>",
                                            ),
                                        )

                                        if error_band:
                                            fig.add_trace(
                                                go.Scatter(
                                                    x=clean_data[selected_index],
                                                    y=clean_data["mean"] + clean_data["std"],
                                                    mode="lines",
                                                    line={"width": 0},
                                                    showlegend=False,
                                                    hoverinfo="skip",
                                                    yaxis=yaxis_ref,
                                                ),
                                            )
                                            fig.add_trace(
                                                go.Scatter(
                                                    x=clean_data[selected_index],
                                                    y=clean_data["mean"] - clean_data["std"],
                                                    mode="lines",
                                                    line={"width": 0},
                                                    fill="tonexty",
                                                    name=f"{column_name} - {translate_service.translate('error_band')} (±1 SD)",
                                                    legendgroup=column_name,
                                                    hoverinfo="skip",
                                                    yaxis=yaxis_ref,
                                                ),
                                            )
                            # Plot by batch mode
                            elif display_mode_selected == translate_service.translate(
                                "plot_by_batch"
                            ):
                                data_cols = [
                                    col
                                    for col in filtered_column_df.columns
                                    if col != selected_index
                                ]

                                if data_cols:
                                    for batch in selected_batches:
                                        batch_cols = [
                                            col for col in data_cols if col.startswith(f"{batch}_")
                                        ]

                                        if batch_cols:
                                            batch_mean = filtered_column_df[batch_cols].mean(axis=1)
                                            batch_std = (
                                                filtered_column_df[batch_cols].std(axis=1).fillna(0)
                                            )

                                            clean_data = pd.DataFrame(
                                                {
                                                    selected_index: filtered_column_df[
                                                        selected_index
                                                    ],
                                                    "mean": batch_mean,
                                                    "std": batch_std,
                                                }
                                            ).dropna(subset=["mean"])

                                            if not clean_data.empty:
                                                fig.add_trace(
                                                    go.Scatter(
                                                        x=clean_data[selected_index],
                                                        y=clean_data["mean"],
                                                        mode="lines+markers",
                                                        name=f"{column_name} - {batch}",
                                                        line={"width": 2, "shape": "spline"},
                                                        marker={"size": 6, "symbol": marker_symbol},
                                                        legendgroup=column_name,
                                                        legendgrouptitle_text=column_name,
                                                        yaxis=yaxis_ref,
                                                        hovertemplate=f"<b>{column_name} - {batch}</b><br>"
                                                        + f"{selected_index}: %{{x}}<br>"
                                                        + f"{translate_service.translate('mean')}: %{{y:.4f}}<extra></extra>",
                                                    ),
                                                )

                                                if error_band:
                                                    fig.add_trace(
                                                        go.Scatter(
                                                            x=clean_data[selected_index],
                                                            y=clean_data["mean"]
                                                            + clean_data["std"],
                                                            mode="lines",
                                                            line={"width": 0},
                                                            showlegend=False,
                                                            hoverinfo="skip",
                                                            yaxis=yaxis_ref,
                                                        ),
                                                    )
                                                    fig.add_trace(
                                                        go.Scatter(
                                                            x=clean_data[selected_index],
                                                            y=clean_data["mean"]
                                                            - clean_data["std"],
                                                            mode="lines",
                                                            line={"width": 0},
                                                            fill="tonexty",
                                                            name=f"{column_name} - {batch} - {translate_service.translate('error_band')}",
                                                            legendgroup=column_name,
                                                            hoverinfo="skip",
                                                            yaxis=yaxis_ref,
                                                        ),
                                                    )
                            # Plot by replicate mode
                            elif display_mode_selected == translate_service.translate(
                                "plot_by_replicate"
                            ):
                                data_cols = [
                                    col
                                    for col in filtered_column_df.columns
                                    if col != selected_index
                                ]

                                if data_cols and selected_replicate_values:
                                    for rep_value in selected_replicate_values:
                                        # Get columns that belong to this replicate value
                                        rep_cols = [
                                            col for col in data_cols
                                            if replicate_well_mapping.get(col) == rep_value
                                        ]

                                        if rep_cols:
                                            rep_mean = filtered_column_df[rep_cols].mean(axis=1)
                                            rep_std = (
                                                filtered_column_df[rep_cols].std(axis=1).fillna(0)
                                            )

                                            clean_data = pd.DataFrame(
                                                {
                                                    selected_index: filtered_column_df[
                                                        selected_index
                                                    ],
                                                    "mean": rep_mean,
                                                    "std": rep_std,
                                                }
                                            ).dropna(subset=["mean"])

                                            if not clean_data.empty:
                                                fig.add_trace(
                                                    go.Scatter(
                                                        x=clean_data[selected_index],
                                                        y=clean_data["mean"],
                                                        mode="lines+markers",
                                                        name=f"{column_name} - {rep_value}",
                                                        line={"width": 2, "shape": "spline"},
                                                        marker={"size": 6, "symbol": marker_symbol},
                                                        legendgroup=column_name,
                                                        legendgrouptitle_text=column_name,
                                                        yaxis=yaxis_ref,
                                                        hovertemplate=f"<b>{column_name} - {rep_value}</b><br>"
                                                        + f"{selected_index}: %{{x}}<br>"
                                                        + f"{translate_service.translate('mean')}: %{{y:.4f}}<extra></extra>",
                                                    ),
                                                )

                                                if error_band:
                                                    fig.add_trace(
                                                        go.Scatter(
                                                            x=clean_data[selected_index],
                                                            y=clean_data["mean"]
                                                            + clean_data["std"],
                                                            mode="lines",
                                                            line={"width": 0},
                                                            showlegend=False,
                                                            hoverinfo="skip",
                                                            yaxis=yaxis_ref,
                                                        ),
                                                    )
                                                    fig.add_trace(
                                                        go.Scatter(
                                                            x=clean_data[selected_index],
                                                            y=clean_data["mean"]
                                                            - clean_data["std"],
                                                            mode="lines",
                                                            line={"width": 0},
                                                            fill="tonexty",
                                                            name=f"{column_name} - {rep_value} - {translate_service.translate('error_band')}",
                                                            legendgroup=column_name,
                                                            hoverinfo="skip",
                                                            yaxis=yaxis_ref,
                                                        ),
                                                    )

                # Build y-axis layout: first axis on the left, others on the right with offset
                # Reserve space on the right for each additional axis beyond the first
                right_margin_per_axis = 0.07
                plot_domain_right = 1.0 - max(0, (num_columns - 1)) * right_margin_per_axis

                yaxis_layouts = {}
                for column_idx, column_name in enumerate(selected_columns):
                    axis_color = axis_colors[column_idx % len(axis_colors)]
                    if column_idx == 0:
                        # First y-axis on the left
                        yaxis_layouts["yaxis"] = {
                            "title": {"text": column_name, "font": {"color": axis_color}},
                            "tickfont": {"color": axis_color},
                        }
                    elif column_idx == 1:
                        # Second y-axis on the right side
                        yaxis_layouts["yaxis2"] = {
                            "title": {"text": column_name, "font": {"color": axis_color}},
                            "tickfont": {"color": axis_color},
                            "overlaying": "y",
                            "side": "right",
                        }
                    else:
                        # Additional y-axes offset further to the right
                        position = 1.0 - (column_idx - 2) * right_margin_per_axis
                        yaxis_layouts[f"yaxis{column_idx + 1}"] = {
                            "title": {"text": column_name, "font": {"color": axis_color}},
                            "tickfont": {"color": axis_color},
                            "overlaying": "y",
                            "side": "right",
                            "position": position,
                            "anchor": "free",
                        }

                # Update layout with all y-axes
                fig.update_layout(
                    **yaxis_layouts,
                    title=translate_service.translate("combined_graph_title").format(
                        index=selected_index
                    ),
                    xaxis={
                        "title": selected_index,
                        "domain": [0, plot_domain_right],
                    },
                    showlegend=True,
                    legend={"orientation": "h", "x": 0.5, "y": -0.15,
                            "xanchor": "center", "yanchor": "top"},
                    height=650,
                )

                # Display the combined plot
                st.plotly_chart(fig, use_container_width=True)

                # Add note about combined view
                st.info(translate_service.translate("combined_graph_info"))

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
                            if col != selected_index and col in batch_sample_combinations:
                                columns_to_keep.append(col)

                        # Filter the DataFrame
                        filtered_column_df = (
                            column_df[columns_to_keep]
                            if len(columns_to_keep) > 1
                            else column_df[[selected_index]]
                        )

                        if len(filtered_column_df.columns) > 1:
                            # Create interactive line plot using Plotly
                            fig = go.Figure()

                            # Individual curves mode
                            if display_mode_selected == translate_service.translate(
                                "individual_curves"
                            ):
                                # Original individual curves plotting
                                for col in filtered_column_df.columns:
                                    if col != selected_index:
                                        clean_data = filtered_column_df[
                                            [selected_index, col]
                                        ].dropna()
                                        if not clean_data.empty:
                                            fig.add_trace(
                                                go.Scatter(
                                                    x=clean_data[selected_index],
                                                    y=clean_data[col],
                                                    mode="lines+markers",
                                                    name=col,
                                                    line={"width": 2},
                                                    marker={"size": 4},
                                                    hovertemplate=f"<b>{col}</b><br>"
                                                    + f"{selected_index}: %{{x}}<br>"
                                                    + f"{column_name}: %{{y:.4f}}<extra></extra>",
                                                )
                                            )

                            # Mean curves mode
                            elif display_mode_selected == translate_service.translate(
                                "mean_selected_batches"
                            ):
                                # Get data columns (exclude index)
                                data_cols = [
                                    col
                                    for col in filtered_column_df.columns
                                    if col != selected_index
                                ]

                                if data_cols:
                                    # Calculate mean and std across all batch_sample combinations
                                    df_mean = filtered_column_df[data_cols].mean(axis=1)
                                    df_std = filtered_column_df[data_cols].std(axis=1).fillna(0)

                                    # Clean data by removing NaN values
                                    clean_data = pd.DataFrame(
                                        {
                                            selected_index: filtered_column_df[selected_index],
                                            "mean": df_mean,
                                            "std": df_std,
                                        }
                                    ).dropna(subset=["mean"])

                                    if not clean_data.empty:
                                        # Add mean trace
                                        fig.add_trace(
                                            go.Scatter(
                                                x=clean_data[selected_index],
                                                y=clean_data["mean"],
                                                mode="lines+markers",
                                                name=f"{column_name} - {translate_service.translate('mean')}",
                                                line={"width": 2, "shape": "spline"},
                                                marker={"size": 6},
                                                hovertemplate=f"<b>{column_name} - {translate_service.translate('mean')}</b><br>"
                                                + f"{selected_index}: %{{x}}<br>"
                                                + f"{translate_service.translate('mean')}: %{{y:.4f}}<extra></extra>",
                                            )
                                        )

                                        # Add error band if requested
                                        if error_band:
                                            # Upper bound
                                            fig.add_trace(
                                                go.Scatter(
                                                    x=clean_data[selected_index],
                                                    y=clean_data["mean"] + clean_data["std"],
                                                    mode="lines",
                                                    line={"width": 0},
                                                    showlegend=False,
                                                    hoverinfo="skip",
                                                )
                                            )
                                            # Lower bound with fill
                                            fig.add_trace(
                                                go.Scatter(
                                                    x=clean_data[selected_index],
                                                    y=clean_data["mean"] - clean_data["std"],
                                                    mode="lines",
                                                    line={"width": 0},
                                                    fill="tonexty",
                                                    name=f"{column_name} - {translate_service.translate('error_band')} (±1 SD)",
                                                    hoverinfo="skip",
                                                )
                                            )
                            # Plot by batch mode
                            elif display_mode_selected == translate_service.translate(
                                "plot_by_batch"
                            ):
                                # Get data columns (exclude index)
                                data_cols = [
                                    col
                                    for col in filtered_column_df.columns
                                    if col != selected_index
                                ]

                                if data_cols:
                                    # Calculate mean and std for each batch
                                    for batch in selected_batches:
                                        # Get columns that belong to this batch
                                        batch_cols = [
                                            col for col in data_cols if col.startswith(f"{batch}_")
                                        ]

                                        if batch_cols:
                                            # Calculate mean and std for this batch
                                            batch_mean = filtered_column_df[batch_cols].mean(axis=1)
                                            batch_std = (
                                                filtered_column_df[batch_cols].std(axis=1).fillna(0)
                                            )

                                            clean_data = pd.DataFrame(
                                                {
                                                    selected_index: filtered_column_df[
                                                        selected_index
                                                    ],
                                                    "mean": batch_mean,
                                                    "std": batch_std,
                                                }
                                            ).dropna(subset=["mean"])

                                            if not clean_data.empty:
                                                fig.add_trace(
                                                    go.Scatter(
                                                        x=clean_data[selected_index],
                                                        y=clean_data["mean"],
                                                        mode="lines+markers",
                                                        name=f"{column_name} - {batch}",
                                                        line={"width": 2, "shape": "spline"},
                                                        marker={"size": 6},
                                                        hovertemplate=f"<b>{column_name} - {batch}</b><br>"
                                                        + f"{selected_index}: %{{x}}<br>"
                                                        + f"{translate_service.translate('mean')}: %{{y:.4f}}<extra></extra>",
                                                    )
                                                )

                                                if error_band:
                                                    fig.add_trace(
                                                        go.Scatter(
                                                            x=clean_data[selected_index],
                                                            y=clean_data["mean"]
                                                            + clean_data["std"],
                                                            mode="lines",
                                                            line={"width": 0},
                                                            showlegend=False,
                                                            hoverinfo="skip",
                                                        )
                                                    )
                                                    fig.add_trace(
                                                        go.Scatter(
                                                            x=clean_data[selected_index],
                                                            y=clean_data["mean"]
                                                            - clean_data["std"],
                                                            mode="lines",
                                                            line={"width": 0},
                                                            fill="tonexty",
                                                            name=f"{column_name} - {batch} - {translate_service.translate('error_band')}",
                                                            hoverinfo="skip",
                                                        )
                                                    )
                            # Plot by replicate mode
                            elif display_mode_selected == translate_service.translate(
                                "plot_by_replicate"
                            ):
                                data_cols = [
                                    col
                                    for col in filtered_column_df.columns
                                    if col != selected_index
                                ]

                                if data_cols and selected_replicate_values:
                                    for rep_value in selected_replicate_values:
                                        rep_cols = [
                                            col for col in data_cols
                                            if replicate_well_mapping.get(col) == rep_value
                                        ]

                                        if rep_cols:
                                            rep_mean = filtered_column_df[rep_cols].mean(axis=1)
                                            rep_std = (
                                                filtered_column_df[rep_cols].std(axis=1).fillna(0)
                                            )

                                            clean_data = pd.DataFrame(
                                                {
                                                    selected_index: filtered_column_df[
                                                        selected_index
                                                    ],
                                                    "mean": rep_mean,
                                                    "std": rep_std,
                                                }
                                            ).dropna(subset=["mean"])

                                            if not clean_data.empty:
                                                fig.add_trace(
                                                    go.Scatter(
                                                        x=clean_data[selected_index],
                                                        y=clean_data["mean"],
                                                        mode="lines+markers",
                                                        name=f"{column_name} - {rep_value}",
                                                        line={"width": 2, "shape": "spline"},
                                                        marker={"size": 6},
                                                        hovertemplate=f"<b>{column_name} - {rep_value}</b><br>"
                                                        + f"{selected_index}: %{{x}}<br>"
                                                        + f"{translate_service.translate('mean')}: %{{y:.4f}}<extra></extra>",
                                                    )
                                                )

                                                if error_band:
                                                    fig.add_trace(
                                                        go.Scatter(
                                                            x=clean_data[selected_index],
                                                            y=clean_data["mean"]
                                                            + clean_data["std"],
                                                            mode="lines",
                                                            line={"width": 0},
                                                            showlegend=False,
                                                            hoverinfo="skip",
                                                        )
                                                    )
                                                    fig.add_trace(
                                                        go.Scatter(
                                                            x=clean_data[selected_index],
                                                            y=clean_data["mean"]
                                                            - clean_data["std"],
                                                            mode="lines",
                                                            line={"width": 0},
                                                            fill="tonexty",
                                                            name=f"{column_name} - {rep_value} - {translate_service.translate('error_band')}",
                                                            hoverinfo="skip",
                                                        )
                                                    )

                            # Update layout
                            fig.update_layout(
                                title=translate_service.translate("chart_title_vs").format(
                                    column=column_name, index=selected_index
                                ),
                                xaxis_title=selected_index,
                                yaxis_title=column_name,
                                hovermode="x unified",
                                template="plotly_white",
                                height=500,
                                showlegend=True,
                            )

                            # Display the plot
                            st.plotly_chart(fig, use_container_width=True)

                            # Add summary statistics based on display mode
                            if display_mode_selected == translate_service.translate(
                                "individual_curves"
                            ):
                                data_columns_only = filtered_column_df.select_dtypes(
                                    include=[float, int]
                                )
                                if selected_index in data_columns_only.columns:
                                    data_columns_only = data_columns_only.drop(
                                        columns=[selected_index]
                                    )

                                if not data_columns_only.empty:
                                    col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)
                                    with col_stats1:
                                        total_values = data_columns_only.count().sum()
                                        st.metric(
                                            translate_service.translate("data_points"),
                                            int(total_values),
                                        )
                                    with col_stats2:
                                        mean_val = data_columns_only.mean().mean()
                                        st.metric(
                                            translate_service.translate("overall_average"),
                                            f"{mean_val:.3f}",
                                        )
                                    with col_stats3:
                                        min_val = data_columns_only.min().min()
                                        st.metric(
                                            translate_service.translate("minimum"), f"{min_val:.3f}"
                                        )
                                    with col_stats4:
                                        max_val = data_columns_only.max().max()
                                        st.metric(
                                            translate_service.translate("maximum"), f"{max_val:.3f}"
                                        )

                                # Download button for individual curves
                                csv_data = filtered_column_df.to_csv(index=False)
                                st.download_button(
                                    label=translate_service.translate("download_data").format(
                                        column=column_name
                                    ),
                                    data=csv_data,
                                    file_name=f"cell_culture_{column_name}_graph_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                    mime="text/csv",
                                    key=f"download_graph_{column_name}_{i}",
                                )

                            elif display_mode_selected == translate_service.translate(
                                "mean_selected_batches"
                            ):
                                # Statistics for mean data
                                if not clean_data.empty:
                                    col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)
                                    with col_stats1:
                                        total_values = len(clean_data)
                                        st.metric(
                                            translate_service.translate("data_points"),
                                            int(total_values),
                                        )
                                    with col_stats2:
                                        mean_val = clean_data["mean"].mean()
                                        st.metric(
                                            translate_service.translate("overall_average"),
                                            f"{mean_val:.3f}",
                                        )
                                    with col_stats3:
                                        min_val = clean_data["mean"].min()
                                        st.metric(
                                            translate_service.translate("minimum"), f"{min_val:.3f}"
                                        )
                                    with col_stats4:
                                        max_val = clean_data["mean"].max()
                                        st.metric(
                                            translate_service.translate("maximum"), f"{max_val:.3f}"
                                        )

                                # Download button for mean data
                                download_df = clean_data.copy()
                                download_df = download_df.rename(
                                    columns={
                                        "mean": f"{column_name}_mean",
                                        "std": f"{column_name}_std",
                                    }
                                )
                                csv_data = download_df.to_csv(index=False)
                                download_label = translate_service.translate(
                                    "download_data"
                                ).format(
                                    column=f"{column_name} {translate_service.translate('mean')}"
                                )
                                st.download_button(
                                    label=download_label,
                                    data=csv_data,
                                    file_name=f"cell_culture_{column_name}_mean_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                    mime="text/csv",
                                    key=f"download_graph_{column_name}_{i}",
                                )
                            elif display_mode_selected == translate_service.translate(
                                "plot_by_batch"
                            ):
                                # Statistics for mean data
                                if not clean_data.empty:
                                    col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)
                                    with col_stats1:
                                        total_values = len(clean_data)
                                        st.metric(
                                            translate_service.translate("data_points"),
                                            int(total_values),
                                        )
                                    with col_stats2:
                                        mean_val = clean_data["mean"].mean()
                                        st.metric(
                                            translate_service.translate("overall_average"),
                                            f"{mean_val:.3f}",
                                        )
                                    with col_stats3:
                                        min_val = clean_data["mean"].min()
                                        st.metric(
                                            translate_service.translate("minimum"), f"{min_val:.3f}"
                                        )
                                    with col_stats4:
                                        max_val = clean_data["mean"].max()
                                        st.metric(
                                            translate_service.translate("maximum"), f"{max_val:.3f}"
                                        )

                                # Download button for mean data
                                download_df = clean_data.copy()
                                download_df = download_df.rename(
                                    columns={
                                        "mean": f"{column_name}_mean",
                                        "std": f"{column_name}_std",
                                    }
                                )
                                csv_data = download_df.to_csv(index=False)
                                download_label = translate_service.translate(
                                    "download_data"
                                ).format(
                                    column=f"{column_name} {translate_service.translate('mean')}"
                                )
                                download_label += f" {translate_service.translate('by_batch')}"
                                st.download_button(
                                    label=download_label,
                                    data=csv_data,
                                    file_name=f"cell_culture_{column_name}_mean_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                    mime="text/csv",
                                    key=f"download_graph_{column_name}_{i}",
                                )
                            elif display_mode_selected == translate_service.translate(
                                "plot_by_replicate"
                            ):
                                if not clean_data.empty:
                                    col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)
                                    with col_stats1:
                                        total_values = len(clean_data)
                                        st.metric(
                                            translate_service.translate("data_points"),
                                            int(total_values),
                                        )
                                    with col_stats2:
                                        mean_val = clean_data["mean"].mean()
                                        st.metric(
                                            translate_service.translate("overall_average"),
                                            f"{mean_val:.3f}",
                                        )
                                    with col_stats3:
                                        min_val = clean_data["mean"].min()
                                        st.metric(
                                            translate_service.translate("minimum"), f"{min_val:.3f}"
                                        )
                                    with col_stats4:
                                        max_val = clean_data["mean"].max()
                                        st.metric(
                                            translate_service.translate("maximum"), f"{max_val:.3f}"
                                        )

                                download_df = clean_data.copy()
                                download_df = download_df.rename(
                                    columns={
                                        "mean": f"{column_name}_mean",
                                        "std": f"{column_name}_std",
                                    }
                                )
                                csv_data = download_df.to_csv(index=False)
                                download_label = translate_service.translate(
                                    "download_data"
                                ).format(
                                    column=f"{column_name} {translate_service.translate('mean')}"
                                )
                                download_label += f" {translate_service.translate('by_replicate')}"
                                st.download_button(
                                    label=download_label,
                                    data=csv_data,
                                    file_name=f"cell_culture_{column_name}_replicate_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                    mime="text/csv",
                                    key=f"download_graph_{column_name}_{i}",
                                )

    except Exception as e:
        st.error(f"❌ {translate_service.translate('error_details')} {str(e)}")
