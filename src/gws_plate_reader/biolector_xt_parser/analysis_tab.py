import os
from typing import List

import streamlit as st
from gws_plate_reader.biolector_xt_parser.biolectorxt_parser import \
    BiolectorXTParser
from gws_plate_reader.features_extraction.linear_logistic_cv import \
    LogisticGrowthFitter
from gws_core import File, ResourceOrigin, ResourceModel, Settings, FrontService, TableImporter

def render_analysis_tab(microplate_object: BiolectorXTParser, filters: list):
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

    _run_analysis_tab(microplate_object, filter_selection)


def _run_analysis_tab(microplate_object: BiolectorXTParser, filter_selection: List[str]):
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
            df_analysis = logistic_fitter.df_params
            st.dataframe(df_analysis.style.format(thousands=" ", precision=4))
            # Add the button to resource containing the analysis table
            if st.button("Generate analysis resource", icon = ":material/note_add:"):
                path_temp = os.path.join(os.path.abspath(os.path.dirname(__file__)), Settings.make_temp_dir())
                full_path = os.path.join(path_temp, "Analysis.csv")
                analysis_df: File = File(full_path)
                analysis_df.write(df_analysis.to_csv(index = False))
                #Import the resource as Table
                analysis_df_table = TableImporter.call(analysis_df)
                analysis_df_resource = ResourceModel.save_from_resource(
                    analysis_df_table, ResourceOrigin.UPLOADED, flagged=True)
                st.success(f"Resource created! ✅ You can find it here : {FrontService.get_resource_url(analysis_df_resource.id)}")
            st.plotly_chart(fig)
        except:
            st.error("Optimal parameters not found for some wells, try deselecting some wells.")
