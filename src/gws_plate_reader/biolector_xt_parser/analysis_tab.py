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

def render_analysis_tab(microplate_object: BiolectorXTParser, filters: List, well_data : dict, all_keys_well_description : List, input_tag : List ):
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

    #Allow the user to select duplicates
    init_value = BiolectorState.get_selected_well_or_replicate()
    options = ["Individual well"] + all_keys_well_description
    index = options.index(init_value) if init_value in options else 0

    selected_well_or_replicate : str = st.selectbox("$\\textsf{\large{Select by}}$",
                                     options = options, index = index, key="analysis_well_or_replicate")
    if BiolectorState.get_analysis_well_or_replicate() != init_value :
        BiolectorState.reset_session_state_wells()
        BiolectorState.reset_plot_replicates_saved()
        BiolectorState.update_selected_well_or_replicate(BiolectorState.get_analysis_well_or_replicate())
        # To remove the bold of the wells
        st.rerun()

    if selected_well_or_replicate != "Individual well":
        dict_replicates = microplate_object.group_wells_by_selection(well_data, selected_well_or_replicate)

        st.write("Only replicates where all wells are selected and contain data will appear here.")

        init_value = BiolectorState.get_plot_replicates_saved()
        options = BiolectorState.get_options_replicates(dict_replicates, microplate_object)
        if init_value == [] :
            default = options
        else:
            default = init_value
        selected_replicates: List[str] = st.multiselect(
                '$\\textsf{\large{Select the replicates to be displayed}}$', options, default = default, key="analysis_replicates")
        if BiolectorState.get_analysis_replicates() != init_value :
            BiolectorState.color_wells_replicates(dict_replicates, BiolectorState.get_analysis_replicates())

        if not selected_replicates:
            st.warning("Please select at least one replicate.")
    else:
        selected_replicates = None

    _run_analysis_tab(microplate_object, filter_selection, well_data, selected_replicates, input_tag)


def _run_analysis_tab(microplate_object: BiolectorXTParser, filter_selection: str, well_data : dict, selected_replicates: List[str] , input_tag : List):
    with st.spinner("Running analysis..."):
        # Get the dataframe
        df = microplate_object.get_table_by_filter(filter_selection)
        df = df.drop(["time"], axis=1)
        if len(BiolectorState.get_well_clicked()) > 0:
            df = df[["Temps_en_h"] + BiolectorState.get_well_clicked()]
        if selected_replicates:
            # Filter df with the wells to keep
            df = df[[ "Temps_en_h"] + BiolectorState.get_wells_to_show()]
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
                    analysis_df.write(df_analysis.to_csv(index = True))
                    #Import the resource as Table
                    analysis_df_table = TableImporter.call(analysis_df, params= {"index_column" : 0})
                    # Add tags
                    microplate_object.add_tags_to_resource(analysis_df_table, filter_selection, input_tag)
                    microplate_object.add_tags_to_table_rows(analysis_df_table, well_data)

                    analysis_df_resource = ResourceModel.save_from_resource(
                        analysis_df_table, ResourceOrigin.UPLOADED, flagged=True)
                    st.success(f"Resource created! ✅ You can find it here : {FrontService.get_resource_url(analysis_df_resource.id)}")
            st.plotly_chart(fig)
        except:
            st.error("Optimal parameters not found for some wells, try deselecting some wells.")
