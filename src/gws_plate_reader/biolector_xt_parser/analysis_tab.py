import os
from typing import List

import streamlit as st
from gws_plate_reader.biolector_xt_parser.biolectorxt_parser import \
    BiolectorXTParser
from gws_plate_reader.features_extraction.linear_logistic_cv import \
    LogisticGrowthFitter


def render_analysis_tab(microplate_object: BiolectorXTParser, filters: list,
                        growth_rate_folder_path: str):
    # Récupération des filtres contenant le mot "Biomass"
    biomass_filters = [f for f in filters if "Biomass" in f]
    # Vérification s'il y a des filtres correspondant
    if not biomass_filters:
        st.error("No filter containing 'Biomass' is available.")
        return

    filter_selection: List[str] = st.selectbox(
        '$\\text{\large{Select the observers to be displayed}}$', biomass_filters, index=0,
        key="analysis_filters")

    # Select wells : all by default; otherwise those selected in the microplate
    if len(st.session_state['well_clicked']) > 0:
        st.write(f"All the wells clicked are: {', '.join(st.session_state['well_clicked'])}")

    _run_analysis_tab(microplate_object, filter_selection, growth_rate_folder_path)


def _run_analysis_tab(microplate_object: BiolectorXTParser, filter_selection: List[str],
                      growth_rate_folder_path: str):
    with st.spinner("Running analysis..."):
        # Get the dataframe
        df = microplate_object.get_table_by_filter(filter_selection)
        df = df.drop(["time"], axis=1)
        if len(st.session_state['well_clicked']) > 0:
            # TODO: voir si il faut les classer par ordre croissant ?
            df = df[["Temps_en_h"] + st.session_state['well_clicked']]
        # Features extraction functions
        try:
            logistic_fitter = LogisticGrowthFitter(df)
            logistic_fitter.fit_logistic_growth_with_cv()
            fig = logistic_fitter.plot_fitted_curves_with_r2()
            st.dataframe(logistic_fitter.df_params.style.format(thousands=" ", precision=4))
            logistic_fitter.df_params.to_csv(os.path.join(growth_rate_folder_path, "growth_rate.csv"))
            st.plotly_chart(fig)
        except:
            st.error("Optimal parameters not found for some wells, try deselecting some wells.")
