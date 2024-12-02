
import plotly.express as px
import streamlit as st
from gws_biolector.biolector_xt_parser.biolectorxt_parser import \
    BiolectorXTParser


def render_plot_tab(microplate_object: BiolectorXTParser, filters: list):
    legend_mean = ""
    selected_filters = st.multiselect(
        '$\\text{\large{Select the observers to be displayed}}$', filters, default=filters, key="plot_filters")
    # Select wells : all by default; otherwise those selected in the microplate
    if len(st.session_state['well_clicked']) > 0:
        st.write(f"All the wells clicked are: {', '.join(st.session_state['well_clicked'])}")
    col1, col2 = st.columns([1, 1])
    with col1:
        selected_time = st.selectbox("$\\text{\large{Select the time unit}}$", [
            "Hours", "Minutes", "Seconds"], index=0, key="plot_time")
    with col2:
        selected_mode = st.selectbox("$\\text{\large{Select the display mode}}$", [
            "Individual curves", "Mean of selected wells"], index=0, key="plot_mode")
    if selected_mode == "Mean of selected wells":
        error_band = st.checkbox("Error band")

    # Create an empty Plotly figure to add all the curves
    fig = px.line()
    for filter in selected_filters:
        df = microplate_object.get_table_by_filter(filter)
        df = df.iloc[:, 1:]
        if len(st.session_state['well_clicked']) > 0:
            # TODO: voir si il faut les classer par ordre croissant ?
            df = df[["Temps_en_h"] + st.session_state['well_clicked']]
        cols_y = [col for col in df.columns if col != 'Temps_en_h']
        # Adapt unit of time
        if selected_time == "Hours":
            df["time"] = df["Temps_en_h"]
        elif selected_time == "Minutes":
            df["time"] = df["Temps_en_h"]*60
        elif selected_time == "Seconds":
            df["time"] = df["Temps_en_h"]*3600
        if selected_mode == "Individual curves":
            # Adding curves to the figure for each filter
            for col in cols_y:
                fig.add_scatter(x=df['time'], y=df[col], mode='lines',
                                name=f"{filter} - {col}", line={'shape': 'spline', 'smoothing': 1})
        elif selected_mode == "Mean of selected wells":
            legend_mean = f"(Mean of  {', '.join(st.session_state['well_clicked'])})"
            df_mean = df[cols_y].mean(axis=1)
            df_std = df[cols_y].std(axis=1)
            fig.add_scatter(x=df['time'], y=df_mean, mode='lines',
                            name=f"{filter} - mean", line={'shape': 'spline', 'smoothing': 1})
            if error_band:
                # Add the error band (mean ± standard deviation)
                fig.add_scatter(x=df['time'], y=df_mean + df_std, mode='lines',
                                line=dict(width=0), showlegend=False)
                fig.add_scatter(
                    x=df['time'],
                    y=df_mean - df_std, mode='lines', line=dict(width=0),
                    fill='tonexty', name=f'Error Band {filter} (±1 SD)')

    selected_filters_str = ', '.join(selected_filters)
    fig.update_layout(title=f'Plot of {selected_filters_str} {legend_mean}',
                      xaxis_title=f'Time ({selected_time})', yaxis_title=f'{selected_filters_str}')
    # Show the plot
    st.plotly_chart(fig)
