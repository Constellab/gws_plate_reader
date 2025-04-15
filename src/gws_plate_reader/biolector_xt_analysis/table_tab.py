import os
from typing import List

import streamlit as st
from gws_core import (File, FrontService, ResourceModel, ResourceOrigin,
                      Settings, TableImporter, Tag)
from gws_core.impl.table.table import Table
from gws_core.streamlit import StreamlitContainers
from gws_core.tag.tag import TagOrigins
from gws_core.tag.tag_dto import TagOriginType
from gws_core.user.current_user_service import CurrentUserService
from gws_plate_reader.biolector_xt_analysis.biolector_state import \
    BiolectorState


def render_table_tab():
    init_value = BiolectorState.get_selected_filters()
    if init_value is None:
        init_value = BiolectorState.get_filters_list()
    init_value = sorted(init_value)
    selected_filters: List[str] = st.multiselect(
        '$\\textsf{\large{Select the observers to be displayed}}$', options=BiolectorState.get_filters_list(),
        default=init_value, key="tab_selected_filters")
    if selected_filters != init_value:
        BiolectorState.set_selected_filters(selected_filters)
        st.rerun()

    # Select wells : all by default; otherwise those selected in the microplate
    if len(BiolectorState.get_wells_clicked()) > 0:
        st.write(f"All the wells clicked are: {', '.join(BiolectorState.get_wells_clicked())}")
    # Allow the user to select duplicates
    init_value = BiolectorState.get_current_replicate_mode()
    options = ["Individual well"] + BiolectorState.get_all_keys_well_description()
    index = options.index(init_value) if init_value in options else 0
    if init_value is None:
        init_value = options[0]

    selected_well_or_replicate: str = st.selectbox("$\\textsf{\large{Select by}}$",
                                                   options=options, index=index, key="tab_well_or_replicate")
    if selected_well_or_replicate != init_value:
        BiolectorState.set_current_replicate_mode(selected_well_or_replicate)
        st.rerun()

    if selected_well_or_replicate != "Individual well":
        dict_replicates = BiolectorState.group_wells_by_options(selected_well_or_replicate)

        st.write("Only replicates where all wells are selected and contain data will appear here.")

        # list of wells from A01 to B12
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
            key="table_replicates")
        if selected_replicates != init_value:
            BiolectorState.color_wells_replicates(dict_replicates, selected_replicates)
            st.rerun()

        if not selected_replicates:
            st.warning("Please select at least one replicate.")
    else:
        selected_replicates = None

    for filter_selection in selected_filters:
        df = BiolectorState.get_table_by_filter(selected_well_or_replicate, filter_selection, selected_replicates)
        if df is not None and len(df.columns) > 2:
            st.write(f"$\\textsf{{\Large{{{filter_selection.replace('_', ' ').capitalize()}}}}}$")
            with StreamlitContainers.full_width_dataframe_container('container-full-dataframe-' + str(filter_selection)):
                st.dataframe(df.style.format(thousands=" ", precision=4), use_container_width=True)

            # If the dashboard is not standalone, we add a button to generate a resource
            if not BiolectorState.is_standalone():
                # Add the button to resource containing the data parsed
                if st.button(f"Generate {filter_selection} resource", icon=":material/note_add:"):
                    path_temp = os.path.join(os.path.abspath(os.path.dirname(__file__)), Settings.make_temp_dir())
                    full_path = os.path.join(path_temp, f"{filter_selection}.csv")
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

                    if st.session_state["comment_tag"] is not None:
                        tab_parsed_table.tags.add_tag(
                            Tag(key="comment", value=st.session_state["comment_tag"], origins=origins))

                    if st.session_state["name_tag"] is not None:
                        tab_parsed_table.tags.add_tag(
                            Tag(key="name", value=st.session_state["name_tag"], origins=origins))

                    if st.session_state["user_name_tag"] is not None:
                        tab_parsed_table.tags.add_tag(
                            Tag(key="user_name", value=st.session_state["user_name_tag"], origins=origins))

                    if st.session_state["date_tag"] is not None:
                        tab_parsed_table.tags.add_tag(
                            Tag(key="date", value=st.session_state["date_tag"], origins=origins))

                    if st.session_state["raw_data"] is not None:
                        tab_parsed_table.tags.add_tag(
                            Tag(key="raw_data", value=st.session_state["raw_data"], origins=origins))

                    tab_parsed_table.tags.add_tag(Tag(key="origin", value='biolector_dashboard', origins=origins))

                    for col in tab_parsed_table.column_names:
                        dict_col = BiolectorState.get_well_data_description().get(col, None)
                        if dict_col is not None:
                            for key, value in dict_col.items():
                                tab_parsed_table.add_column_tag_by_name(
                                    col, key=Tag.parse_tag(key),
                                    value=Tag.parse_tag(value))

                    tab_parsed_resource = ResourceModel.save_from_resource(
                        tab_parsed_table, ResourceOrigin.UPLOADED, flagged=True)

                    st.success(
                        f"Resource created! ✅ You can find it here : {FrontService.get_resource_url(tab_parsed_resource.id)}")
