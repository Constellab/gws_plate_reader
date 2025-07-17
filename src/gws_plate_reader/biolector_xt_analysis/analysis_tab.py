import os
from typing import List
import streamlit as st

from gws_plate_reader.biolector_xt_analysis.biolector_state import BiolectorStateMode
from gws_core import (File, FrontService, ResourceModel, ResourceOrigin,
                      Settings, TableImporter)
from gws_core.streamlit import StreamlitContainers, StreamlitAuthenticateUser
from gws_core.tag.tag import Tag, TagOrigins
from gws_core.tag.tag_dto import TagOriginType
from gws_core.user.current_user_service import CurrentUserService
from gws_plate_reader.biolector_xt_analysis.biolector_state import \
    BiolectorState
from gws_plate_reader.dashboard_components.select_replicates_input import \
    render_select_replicates_input
from gws_plate_reader.features_extraction.linear_logistic_cv import \
    LogisticGrowthFitter

def render_analysis_tab():
    # Récupération des filtres contenant le mot "Biomass"
    biomass_filters = [f for f in BiolectorState.get_filters_list() if "biomass" in f.lower()]
    # Vérification s'il y a des filtres correspondant
    if not biomass_filters:
        st.error("No filter containing 'Biomass' is available.")
        return

    col1, col2 = st.columns(2)
    with col1:
        filter_selection: List[str] = st.selectbox(
            'Select the observers', biomass_filters, index=0,
            key="analysis_filters")

    # Select wells : all by default; otherwise those selected in the microplate
    if len(BiolectorState.get_wells_clicked()) > 0:
        st.write(f"All the wells clicked are: {', '.join(BiolectorState.get_wells_clicked())}")

    # Allow the user to select duplicates
    init_value = BiolectorState.get_current_replicate_mode()
    options = ["Individual wells"] + BiolectorState.get_all_keys_well_description()
    index = options.index(init_value) if init_value in options else 0
    if init_value is None:
        init_value = options[0]
    with col2:
        selected_well_or_replicate: str = st.selectbox("Filter by",
                                                    options=options, index=index, key="analysis_well_or_replicate")
    if selected_well_or_replicate != init_value:
        BiolectorState.set_current_replicate_mode(selected_well_or_replicate)
        st.rerun()

    selected_replicates = render_select_replicates_input(selected_well_or_replicate)

    df_analysis = _run_analysis_tab(filter_selection, selected_well_or_replicate, selected_replicates)


def _run_analysis_tab(filter_selection: str, selected_well_or_replicate: str,
                      selected_replicates: List[str]):
    with st.spinner("Running analysis..."):
        # Get the dataframe
        df = BiolectorState.get_table_by_filter(selected_well_or_replicate, filter_selection, selected_replicates)
        df = df.drop(["time"], axis=1)
        # Features extraction functions
        try:
            logistic_fitter = LogisticGrowthFitter(df)
            logistic_fitter.fit_logistic_growth_with_cv()
            fig = logistic_fitter.plot_fitted_curves_with_r2()
            histogram = logistic_fitter.plot_growth_rate_histogram()
            df_analysis = logistic_fitter.df_params
            with StreamlitContainers.full_width_dataframe_container('container-full-dataframe-growth-rate'):
                st.dataframe(df_analysis.style.format(
                    thousands=" ", precision=4), use_container_width=True)

            # If the dashboard is not standalone, we add a button to generate a resource
            if not BiolectorState.is_standalone():
                # Add the button to resource containing the analysis table
                if st.button("Generate analysis resource", icon=":material/note_add:"):
                    with StreamlitAuthenticateUser():
                        path_temp = os.path.join(os.path.abspath(os.path.dirname(__file__)), Settings.make_temp_dir())
                        full_path = os.path.join(path_temp, "Analysis.csv")
                        analysis_df: File = File(full_path)
                        analysis_df.write(df_analysis.to_csv(index=True))
                        # Import the resource as Table
                        analysis_df_table = TableImporter.call(analysis_df, params={"index_column": 0})
                        # Add tags to resource
                        user_id = CurrentUserService.get_and_check_current_user().id
                        origins = TagOrigins(TagOriginType.USER, user_id)
                        analysis_df_table.tags.add_tag(Tag(key="filter", value=filter_selection,
                                                        auto_parse=True, origins=origins))
                        if BiolectorState.get_input_tag():
                            analysis_df_table.tags.add_tag(BiolectorState.get_input_tag())

                        if "comment_tag" in st.session_state and st.session_state["comment_tag"] is not None:
                            analysis_df_table.tags.add_tag(
                                Tag(key="comment", value=st.session_state["comment_tag"], origins=origins))

                        if "name_tag" in st.session_state and st.session_state["name_tag"] is not None:
                            analysis_df_table.tags.add_tag(
                                Tag(key="name", value=st.session_state["name_tag"], origins=origins))

                        if "user_name_tag" in st.session_state and st.session_state["user_name_tag"] is not None:
                            analysis_df_table.tags.add_tag(
                                Tag(key="user_name", value=st.session_state["user_name_tag"], origins=origins))

                        if "date_tag" in st.session_state and st.session_state["date_tag"] is not None:
                            analysis_df_table.tags.add_tag(
                                Tag(key="date", value=st.session_state["date_tag"], origins=origins))

                        for row in analysis_df_table.row_names:
                            dict_row = BiolectorState.get_well_data_description().get(row, None)
                            if dict_row is not None:
                                analysis_df_table.tags.add_tag(
                                    Tag(key=row, value=dict_row, auto_parse=True, origins=origins))

                        analysis_df_resource = ResourceModel.save_from_resource(
                            analysis_df_table, ResourceOrigin.UPLOADED, flagged=True)
                        st.success(
                            f"Resource created! ✅ You can find it here : {FrontService.get_resource_url(analysis_df_resource.id)}")
            with st.expander("Analysis Plots", expanded=True):
                st.plotly_chart(fig)
                st.plotly_chart(histogram)
        except:
            st.error("Optimal parameters not found for some wells, try deselecting some wells.")
    return df_analysis