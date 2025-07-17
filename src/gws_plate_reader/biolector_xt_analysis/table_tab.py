import os

import streamlit as st
from gws_core import (File, FrontService, ResourceModel, ResourceOrigin,
                      Settings, TableImporter, Tag)
from gws_core.impl.table.table import Table
from gws_core.streamlit import StreamlitContainers, StreamlitAuthenticateUser
from gws_core.tag.tag import TagOrigins
from gws_core.tag.tag_dto import TagOriginType
from gws_core.user.current_user_service import CurrentUserService
from gws_plate_reader.biolector_xt_analysis.biolector_state import \
    BiolectorState
from gws_plate_reader.dashboard_components.select_filter_mode_inputs import \
    render_select_filter_mode_inputs
from gws_plate_reader.dashboard_components.select_replicates_input import \
    render_select_replicates_input


def render_table_tab():
    selected_filters, selected_well_or_replicate = render_select_filter_mode_inputs()

    selected_replicates = render_select_replicates_input(selected_well_or_replicate)

    for filter_selection in selected_filters:
        df = BiolectorState.get_table_by_filter(selected_well_or_replicate, filter_selection, selected_replicates)
        if df is not None and len(df.columns) > 2:
            st.write(f"$\\textsf{{\Large{{{filter_selection.replace('_', ' ')}}}}}$")
            with StreamlitContainers.full_width_dataframe_container('container-full-dataframe-' + str(filter_selection)):
                st.dataframe(df.style.format(thousands=" ", precision=4), use_container_width=True)

            # If the dashboard is not standalone, we add a button to generate a resource
            if not BiolectorState.is_standalone():
                # Add the button to resource containing the data parsed
                if st.button(f"Save {filter_selection} table", icon=":material/save:"):
                    with StreamlitAuthenticateUser():
                        path_temp = os.path.join(os.path.abspath(os.path.dirname(__file__)), Settings.make_temp_dir())
                        resource_name = f"{st.session_state['raw_data']}_{filter_selection}" if 'raw_data' in st.session_state and st.session_state['raw_data'] is not None else filter_selection
                        full_path = os.path.join(path_temp, f"{resource_name}.csv")
                        tab_parsed: File = File(full_path)
                        tab_parsed.write(df.to_csv(index=False))
                        # Import the resource as Table
                        tab_parsed_table: Table = TableImporter.call(tab_parsed)
                        # Add tags to resource
                        user_id = CurrentUserService.get_and_check_current_user().id
                        origins = TagOrigins(TagOriginType.USER, user_id)
                        tab_parsed_table.tags.add_tag(Tag(key="filter", value=filter_selection,
                                                        auto_parse=True, origins=origins))
                        if BiolectorState.get_input_tag():
                            tab_parsed_table.tags.add_tag(BiolectorState.get_input_tag())

                        if "comment_tag" in st.session_state and st.session_state["comment_tag"] is not None:
                            tab_parsed_table.tags.add_tag(
                                Tag(key="comment", value=st.session_state["comment_tag"], origins=origins))

                        if "name_tag" in st.session_state and  st.session_state["name_tag"] is not None:
                            tab_parsed_table.tags.add_tag(
                                Tag(key="name", value=st.session_state["name_tag"], origins=origins))

                        if "user_name_tag" in st.session_state and  st.session_state["user_name_tag"] is not None:
                            tab_parsed_table.tags.add_tag(
                                Tag(key="user_name", value=st.session_state["user_name_tag"], origins=origins))

                        if "date_tag" in st.session_state and  st.session_state["date_tag"] is not None:
                            tab_parsed_table.tags.add_tag(
                                Tag(key="date", value=st.session_state["date_tag"], origins=origins))

                        if "raw_data" in st.session_state and  st.session_state["raw_data"] is not None:
                            tab_parsed_table.tags.add_tag(
                                Tag(key="raw_data", value=st.session_state["raw_data"], origins=origins))

                        tab_parsed_table.tags.add_tag(Tag(key="origin", value='biolector_dashboard', origins=origins))

                        for col in tab_parsed_table.column_names:
                            dict_col = BiolectorState.get_well_data_description().get(col, None)
                            tab_parsed_table.add_column_tag_by_name(
                                col, key=Tag.parse_tag('well'),
                                value=Tag.parse_tag(col))
                            if dict_col is not None:
                                for key, value in dict_col.items():
                                    tab_parsed_table.add_column_tag_by_name(
                                        col, key=Tag.parse_tag(key),
                                        value=Tag.parse_tag(value))

                        tab_parsed_resource = ResourceModel.save_from_resource(
                            tab_parsed_table, ResourceOrigin.UPLOADED, flagged=True)

                        st.success(
                            f"Resource created! ✅ You can find it here : {FrontService.get_resource_url(tab_parsed_resource.id)}")
