
import plotly.graph_objects as go
import streamlit as st
from gws_biolector.biolector_xt_parser.biolectorxt_parser import \
    BiolectorXTParser


def render_plot_tab(microplate_object: BiolectorXTParser, filters: list):
    legend_mean = ""
    selected_filters = st.multiselect('$\\text{\large{Select the observers to be displayed}}$', filters, default=filters, key="plot_filters")

    # Select wells: all by default; otherwise those selected in the microplate
    if len(st.session_state['well_clicked']) > 0:
        st.write(f"All the wells clicked are: {', '.join(st.session_state['well_clicked'])}")

    col1, col2 = st.columns([1, 1])
    with col1:
        selected_time = st.selectbox("$\\text{\large{Select the time unit}}$", ["Hours", "Minutes", "Seconds"], index=0, key="plot_time")
    with col2:
        selected_mode = st.selectbox("$\\text{\large{Select the display mode}}$", ["Individual curves", "Mean of selected wells"], index=0, key="plot_mode")

    if selected_mode == "Mean of selected wells":
        error_band = st.checkbox("Error band")

    # Create an empty Plotly figure
    fig = go.Figure()

    for i, filter_name in enumerate(selected_filters):
        df = microplate_object.get_table_by_filter(filter_name)
        df = df.iloc[:, 1:]
        if len(st.session_state['well_clicked']) > 0:
            df = df[["Temps_en_h"] + st.session_state['well_clicked']]

        cols_y = [col for col in df.columns if col != 'Temps_en_h']

        # Adapt unit of time
        if selected_time == "Hours":
            df["time"] = df["Temps_en_h"]
        elif selected_time == "Minutes":
            df["time"] = df["Temps_en_h"] * 60
        elif selected_time == "Seconds":
            df["time"] = df["Temps_en_h"] * 3600

        # Assign a unique y-axis for each filter
        yaxis_id = f"y{i+1}"

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
        elif selected_mode == "Mean of selected wells":
            legend_mean = f"(Mean of  {', '.join(st.session_state['well_clicked'])})"
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
                anchor= "free" if i > 0 else "x",
                overlaying="y" if i > 0 else None,
                side="left", #right" if i % 2 == 1 else "left",
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
