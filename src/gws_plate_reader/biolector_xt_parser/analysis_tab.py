import os
from typing import List

import streamlit as st
from gws_plate_reader.biolector_xt_parser.biolectorxt_parser import \
    BiolectorXTParser
from gws_plate_reader.features_extraction.linear_logistic_cv import \
    LogisticGrowthFitter
from gws_plate_reader.biolector_xt_parser.biolector_state import BiolectorState
from gws_core import File, ResourceOrigin, ResourceModel, Settings, FrontService, TableImporter, Tag, CurrentUserService
from gws_core.tag.tag import TagOrigins
from gws_core.tag.tag_dto import TagOriginType

def render_analysis_tab(microplate_object: BiolectorXTParser, filters: List, input_tag : List ):
    # Récupération des filtres contenant le mot "Biomass"
    biomass_filters = [f for f in filters if "Biomass" in f]
    # Vérification s'il y a des filtres correspondant
    if not biomass_filters:
        st.error("No filter containing 'Biomass' is available.")
        return

    filter_selection: List[str] = st.selectbox(
        '$\\textsf{\large{Select the observers to be displayed}}$', biomass_filters, index=0,
        key="analysis_filters")

    # Select wells : all by default; otherwise those selected in the microplate
    if len(BiolectorState.get_well_clicked()) > 0:
        st.write(f"All the wells clicked are: {', '.join(BiolectorState.get_well_clicked())}")

    _run_analysis_tab(microplate_object, filter_selection, input_tag)


def _run_analysis_tab(microplate_object: BiolectorXTParser, filter_selection: List[str], input_tag : List):
    with st.spinner("Running analysis..."):
        # Get the dataframe
        df = microplate_object.get_table_by_filter(filter_selection)
        df = df.drop(["time"], axis=1)
        if len(BiolectorState.get_well_clicked()) > 0:
            # TODO: voir si il faut les classer par ordre croissant ?
            df = df[["Temps_en_h"] + BiolectorState.get_well_clicked()]
        # Features extraction functions
        try:
            logistic_fitter = LogisticGrowthFitter(df)
            logistic_fitter.fit_logistic_growth_with_cv()
            fig = logistic_fitter.plot_fitted_curves_with_r2()
            df_analysis = logistic_fitter.df_params
            st.dataframe(df_analysis.style.format(thousands=" ", precision=4))
            #If the dashboard is not standalone, we add a button to generate a resource
            if not BiolectorState.get_is_standalone():
                # Add the button to resource containing the analysis table
                if st.button("Generate analysis resource", icon = ":material/note_add:"):
                    path_temp = os.path.join(os.path.abspath(os.path.dirname(__file__)), Settings.make_temp_dir())
                    full_path = os.path.join(path_temp, "Analysis.csv")
                    analysis_df: File = File(full_path)
                    analysis_df.write(df_analysis.to_csv(index = False))
                    #Import the resource as Table
                    analysis_df_table = TableImporter.call(analysis_df)
                    # Add tags
                    user_id = CurrentUserService.get_and_check_current_user().id
                    analysis_df_table.tags.add_tag(Tag(key = "filter", value = filter_selection, auto_parse=True,origins=TagOrigins(TagOriginType.USER, user_id)))
                    if input_tag :
                        # If there was a tag biolector_download associated you the input table, then we add it to this table too
                        analysis_df_table.tags.add_tag(input_tag[0])
                    analysis_df_resource = ResourceModel.save_from_resource(
                        analysis_df_table, ResourceOrigin.UPLOADED, flagged=True)
                    st.success(f"Resource created! ✅ You can find it here : {FrontService.get_resource_url(analysis_df_resource.id)}")
            st.plotly_chart(fig)
        except:
            st.error("Optimal parameters not found for some wells, try deselecting some wells.")
