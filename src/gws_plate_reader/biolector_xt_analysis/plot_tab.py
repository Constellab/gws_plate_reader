from typing import List

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from gws_plate_reader.biolector_xt_analysis.biolector_state import (
    BiolectorState, BiolectorStateMode)


def render_plot_tab():
    legend_mean = ""
    col1, col2 = st.columns([1, 1])
    with col1:
        init_value = BiolectorState.get_selected_filters()
        if init_value is None:
            init_value = BiolectorState.get_filters_list()
        init_value = sorted(init_value)
        selected_filters: List[str] = st.multiselect(
            '$\\textsf{\large{Select the observers to be displayed}}$', options=BiolectorState.get_filters_list(),
            default=init_value, key="plot_selected_filters")
        if selected_filters != init_value:
            BiolectorState.set_selected_filters(selected_filters)
            st.rerun()
    with col2:
        selected_time = st.selectbox("$\\textsf{\large{Select the time unit}}$", [
                                     "Hours", "Minutes", "Seconds"], index=0, key="plot_time")

    # Select wells: all by default; otherwise those selected in the microplate
    if len(BiolectorState.get_wells_clicked()) > 0:
        st.write(f"All the wells clicked are: {', '.join(BiolectorState.get_wells_clicked())}")

    col1, col2 = st.columns([1, 1])
    with col1:
        init_value = BiolectorState.get_current_replicate_mode()
        options = ["Individual well"] + BiolectorState.get_all_keys_well_description()
        index = options.index(init_value) if init_value in options else 0
        if init_value is None:
            init_value = options[0]
        selected_well_or_replicate: str = st.selectbox("$\\textsf{\large{Select by}}$",
                                                       options=options, index=index, key="plot_well_or_replicate")
        if selected_well_or_replicate != init_value:
            BiolectorState.set_current_replicate_mode(selected_well_or_replicate)
            selected_mode = "Individual curves"
            st.rerun()
    with col2:
        selected_mode = st.selectbox("$\\textsf{\large{Select the display mode}}$",
                                     ["Individual curves", "Mean"],
                                     index=0, key="plot_mode")

    if selected_mode == "Mean":
        error_band = st.checkbox("Error band")

    if selected_well_or_replicate != "Individual well":
        dict_replicates = BiolectorState.group_wells_by_options(selected_well_or_replicate)

        st.write("Only replicates where all wells are selected and contain data will appear here.")

        cross_out_wells = {f"{row}{col:02d}" for row in "AB" for col in range(1, 13)}
        init_value = BiolectorState.get_replicates_saved()
        BiolectorState.reset_options_replicates()
        for replicate, wells in dict_replicates.items():
            if BiolectorState.is_microfluidics() and any(well in cross_out_wells
                                                         for well in wells):
                continue
            elif len(BiolectorState.get_wells_clicked()) > 0:
                if not any(well in dict_replicates[replicate] for well in BiolectorState.get_wells_clicked()):
                    continue
                else:
                    BiolectorState.add_option_replicate(replicate)
            else:
                BiolectorState.add_option_replicate(replicate)
        options = BiolectorState.get_options_replicates()
        for v in init_value:
            if v not in options:
                init_value.remove(v)
        if init_value == []:
            default = options
        else:
            default = init_value
        selected_replicates: List[str] = st.multiselect(
            '$\\textsf{\large{Select the replicates to be displayed}}$', options, default=default,
            key="plot_replicates")
        if selected_replicates != init_value:
            BiolectorState.color_wells_replicates(dict_replicates, selected_replicates)
            st.rerun()

        if not selected_replicates:
            st.warning("Please select at least one replicate.")

    else:
        selected_replicates = None

    # Create an empty Plotly figure
    fig = go.Figure()

    for i, filter_name in enumerate(selected_filters):
        df = BiolectorState.get_table_by_filter(selected_well_or_replicate, filter_name, selected_replicates)
        df = df.iloc[:, 1:]

        # Adapt unit of time
        if selected_time == "Hours":
            df["time"] = df["Temps_en_h"]
        elif selected_time == "Minutes":
            df["time"] = df["Temps_en_h"] * 60
        elif selected_time == "Seconds":
            df["time"] = df["Temps_en_h"] * 3600

        # Assign a unique y-axis for each filter
        yaxis_id = f"y{i+1}"

        cols_y = [col for col in df.columns if col != 'time' and col != 'Temps_en_h']

        # Individual curves
        if selected_mode == "Individual curves":
            for col in cols_y:
                fig.add_trace(go.Scatter(
                    x=df['time'],
                    y=df[col],
                    mode='lines',
                    name=f"{filter_name} - {col}",
                    line={'shape': 'spline', 'smoothing': 1},
                    yaxis=yaxis_id
                ))
        # Mean curves
        elif selected_mode == "Mean":
            if selected_well_or_replicate == "Individual well":
                if not BiolectorState.get_wells_clicked():
                    legend_mean = "(Mean of all wells)"
                else:
                    legend_mean = f"(Mean of {', '.join(BiolectorState.get_wells_clicked())})"
                df_mean = df[cols_y].mean(axis=1)
                df_std = df[cols_y].std(axis=1)
                fig.add_trace(go.Scatter(
                    x=df['time'],
                    y=df_mean,
                    mode='lines',
                    name=f"{filter_name} - mean",
                    line={'shape': 'spline', 'smoothing': 1},
                    yaxis=yaxis_id
                ))
                if error_band:
                    fig.add_trace(go.Scatter(
                        x=df['time'],
                        y=df_mean + df_std,
                        mode='lines',
                        line=dict(width=0),
                        showlegend=False,
                        yaxis=yaxis_id
                    ))
                    fig.add_trace(go.Scatter(
                        x=df['time'],
                        y=df_mean - df_std,
                        mode='lines',
                        line=dict(width=0),
                        fill='tonexty',
                        name=f'Error Band {filter_name} (±1 SD)',
                        yaxis=yaxis_id
                    ))
            elif selected_well_or_replicate != "Individual well":
                if selected_replicates:
                    # Define function to pair the wells and calculate the mean
                    def calculate_replicates_mean_std(df, selected_replicates, dict_replicates, operation):
                        # Group wells into pairs and calculate the mean for each pair
                        replicates = []
                        for replicate in selected_replicates:
                            columns = []
                            if BiolectorState.get_mode() == BiolectorStateMode.MULTIPLE_PLATES:
                                for plate, wells in dict_replicates[replicate].items():
                                    for well in wells:
                                        if f"{well}_{plate}" in df.columns:
                                            columns.append(f"{well}_{plate}")
                            else:
                                columns = [col for col in df.columns if col in dict_replicates[replicate]]
                            if operation == "mean":
                                replicate = df[columns].mean(axis=1)
                            elif operation == "std":
                                replicate = df[columns].std(axis=1)
                            replicates.append(replicate)

                        # Create a new DataFrame for the replicates
                        replicate_df = pd.concat(replicates, axis=1)
                        # set columns names
                        replicate_df.columns = [replicate for replicate in selected_replicates]

                        return replicate_df

                    # Compute the mean of each replicate
                    replicate_df_mean = calculate_replicates_mean_std(df, selected_replicates, dict_replicates, "mean")
                    replicate_df_std = calculate_replicates_mean_std(df, selected_replicates, dict_replicates, "std")

                    legend_mean = f"(Mean of replicates {', '.join(selected_replicates)})"
                    for col in replicate_df_mean.columns:
                        fig.add_trace(go.Scatter(
                            x=df['time'],
                            y=replicate_df_mean[col],
                            mode='lines',
                            name=f"{filter_name} - mean {col}",
                            line={'shape': 'spline', 'smoothing': 1},
                            yaxis=yaxis_id
                        ))

                        if error_band:
                            fig.add_trace(go.Scatter(
                                x=df['time'],
                                y=replicate_df_mean[col] + replicate_df_std[col],
                                mode='lines',
                                line=dict(width=0),
                                showlegend=False,
                                yaxis=yaxis_id
                            ))
                            fig.add_trace(go.Scatter(
                                x=df['time'],
                                y=replicate_df_mean[col] - replicate_df_std[col],
                                mode='lines',
                                line=dict(width=0),
                                fill='tonexty',
                                name=f'Error Band {filter_name} - {col}(±1 SD)',
                                yaxis=yaxis_id
                            ))

        # Update layout for the y-axis
        fig.update_layout({
            f"yaxis{i+1}": dict(
                title=dict(
                    text=f"{filter_name}",
                    font=dict(
                        color=f"hsl({i * 60}, 70%, 50%)"
                    ),
                    standoff=8  # Bring the title closer to the axis
                ),
                tickfont=dict(
                    color=f"hsl({i * 60}, 70%, 50%)"
                ),
                anchor="free" if i > 0 else "x",
                overlaying="y" if i > 0 else None,
                side="left",  # right" if i % 2 == 1 else "left",
                position=1.0 if i % 2 == 1 else 0.0,  # Left at 0.0, Right at 1.0
            )
        })

    selected_filters_str = ', '.join(selected_filters)
    fig.update_layout(
        title_text=f'Plot of {selected_filters_str} {legend_mean}',
        xaxis=dict(title=f'Time ({selected_time})', domain=[0.1, 0.9]),
        width=800
    )

    # Show the plot
    st.plotly_chart(fig)
