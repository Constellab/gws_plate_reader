import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from gws_plate_reader.biolector_xt_analysis.biolector_state import (
    BiolectorState, BiolectorStateMode)
from gws_plate_reader.dashboard_components.select_filter_mode_inputs import \
    render_select_filter_mode_inputs
from gws_plate_reader.dashboard_components.select_replicates_input import \
    render_select_replicates_input


def render_plot_tab():
    legend_mean = ""

    selected_filters, selected_well_or_replicate = render_select_filter_mode_inputs()

    col1, col2 = st.columns([1, 1])
    with col1:
        options_time = ["Hours", "Minutes", "Seconds"]
        init_value_time = BiolectorState.get_plot_time()
        if init_value_time is None:
            index_init_value_time = 0
        else:
            index_init_value_time = options_time.index(init_value_time)
        selected_time = st.selectbox("Select the time unit", options_time, index=index_init_value_time, key="plot_time")
        if selected_time != init_value_time:
            BiolectorState.set_plot_time(selected_time)
            st.rerun()
    with col2:
        options_mode = ["Individual curves", "Mean"]
        init_value = BiolectorState.get_plot_mode()
        if init_value is None:
            index_init_value = 0
        else:
            index_init_value = options_mode.index(init_value)
        display_mode_selected = st.selectbox("Select the display mode",
                                    options_mode,
                                    index=index_init_value,
                                    key="plot_mode")
        if display_mode_selected != init_value:
            BiolectorState.set_plot_mode(display_mode_selected)
            st.rerun()

    if BiolectorState.get_plot_mode() == "Mean":
        init_value_error_band = BiolectorState.get_error_band()
        if init_value_error_band is None:
            init_value_error_band = False
        error_band = st.checkbox("Error band", value=init_value_error_band, key="error_band")
        if error_band != init_value_error_band:
            BiolectorState.set_error_band(error_band)
            st.rerun()

    selected_replicates = render_select_replicates_input(selected_well_or_replicate)

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

        dict_well_data_description = BiolectorState.get_well_data_description()

        # Individual curves
        if BiolectorState.get_plot_mode() == "Individual curves":
            for col in cols_y:

                # Create display name with well, label, and filter
                display_name = f"{filter_name} - {col}"

                fig.add_trace(go.Scatter(
                    x=df['time'],
                    y=df[col],
                    mode='lines',
                    name=display_name,
                    line={'shape': 'spline', 'smoothing': 1},
                    yaxis=yaxis_id
                ))
        # Mean curves
        elif BiolectorState.get_plot_mode() == "Mean":
            if selected_well_or_replicate == "Individual wells":
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
            elif selected_well_or_replicate != "Individual wells":
                if selected_replicates:
                    # Define function to pair the wells and calculate the mean
                    def calculate_replicates_mean_std(df, selected_replicates, operation):
                        # Group wells into pairs and calculate the mean for each pair
                        replicates = []
                        for replicate in selected_replicates:
                            columns = []
                            if BiolectorState.get_mode() == BiolectorStateMode.MULTIPLE_PLATES:
                                for plate, wells in BiolectorState.group_wells_by_options(selected_well_or_replicate)[
                                        replicate].items():
                                    for well in wells:
                                        if f"{well}_{plate}" in df.columns:
                                            columns.append(f"{well}_{plate}")
                            else:
                                columns = [col for col in df.columns if col in BiolectorState.group_wells_by_options(selected_well_or_replicate)[
                                    replicate]]
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
                    replicate_df_mean = calculate_replicates_mean_std(df, selected_replicates, "mean")
                    replicate_df_std = calculate_replicates_mean_std(df, selected_replicates, "std")

                    legend_mean = f"(Mean of replicates {', '.join(selected_replicates)})"
                    for col in replicate_df_mean.columns:
                        fig.add_trace(go.Scatter(
                            x=df['time'],
                            y=replicate_df_mean[col],
                            mode='lines',
                            name=f"{filter_name} - mean",
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
