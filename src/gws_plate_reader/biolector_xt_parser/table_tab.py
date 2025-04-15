import os
from typing import List

import streamlit as st
from gws_core import (File, FrontService, ResourceModel, ResourceOrigin,
                      Settings, TableImporter, Tag)
from gws_core.streamlit import StreamlitContainers
from gws_plate_reader.biolector_xt_parser.biolector_state import BiolectorState
from gws_plate_reader.biolector_xt_parser.biolectorxt_parser import \
    BiolectorXTParser


def render_table_tab(microplate_object: BiolectorXTParser, filters: list, well_data: dict,
                     all_keys_well_description: List, input_tag: List):
    init_value = BiolectorState.get_selected_filters()
    selected_filters: List[str] = st.multiselect(
        '$\\textsf{\large{Select the observers to be displayed}}$', options=filters, default=init_value,
        key="tab_filters")
    if BiolectorState.get_table_filters() != init_value:
        BiolectorState.update_selected_filters(BiolectorState.get_table_filters())

    # Select wells : all by default; otherwise those selected in the microplate
    if len(BiolectorState.get_well_clicked()) > 0:
        st.write(f"All the wells clicked are: {', '.join(BiolectorState.get_well_clicked())}")
    # Allow the user to select duplicates
    init_value = BiolectorState.get_selected_well_or_replicate()
    options = ["Individual well"] + all_keys_well_description
    index = options.index(init_value) if init_value in options else 0

    selected_well_or_replicate: str = st.selectbox("$\\textsf{\large{Select by}}$",
                                                   options=options, index=index, key="tab_well_or_replicate")
    if BiolectorState.get_table_well_or_replicate() != init_value:
        BiolectorState.reset_session_state_wells()
        BiolectorState.reset_plot_replicates_saved()
        BiolectorState.update_selected_well_or_replicate(BiolectorState.get_table_well_or_replicate())
        # To remove the bold of the wells
        st.rerun()

    if selected_well_or_replicate != "Individual well":
        dict_replicates = microplate_object.group_wells_by_selection(well_data, selected_well_or_replicate)

        st.write("Only replicates where all wells are selected and contain data will appear here.")

        init_value = BiolectorState.get_plot_replicates_saved()
        options = BiolectorState.get_options_replicates(dict_replicates, microplate_object)
        if init_value == []:
            default = options
        else:
            default = init_value
        selected_replicates: List[str] = st.multiselect(
            '$\\textsf{\large{Select the replicates to be displayed}}$', options, default=default,
            key="table_replicates")
        if BiolectorState.get_table_replicates() != init_value:
            BiolectorState.color_wells_replicates(dict_replicates, BiolectorState.get_table_replicates())

        if not selected_replicates:
            st.warning("Please select at least one replicate.")
    else:
        selected_replicates = None

    for filter_selection in selected_filters:
        st.write(f"$\\textsf{{\Large{{{filter_selection}}}}}$")
        df = microplate_object.get_table_by_filter(filter_selection)
        if len(BiolectorState.get_well_clicked()) > 0:
            df = df[["time", "Temps_en_h"] + BiolectorState.get_well_clicked()]
        if selected_replicates:
            # Filter df with the wells to keep
            df = df[["time", "Temps_en_h"] + BiolectorState.get_wells_to_show()]
        with StreamlitContainers.full_width_dataframe_container('container-full-dataframe-' + str(filter_selection)):
            st.dataframe(df.style.format(thousands=" ", precision=4), use_container_width=True)

        # If the dashboard is not standalone, we add a button to generate a resource
        if not BiolectorState.get_is_standalone():
            # Add the button to resource containing the data parsed
            if st.button(f"Generate {filter_selection} resource", icon=":material/note_add:"):
                path_temp = os.path.join(os.path.abspath(os.path.dirname(__file__)), Settings.make_temp_dir())
                full_path = os.path.join(path_temp, f"{filter_selection}.csv")
                tab_parsed: File = File(full_path)
                tab_parsed.write(df.to_csv(index=False))
                # Import the resource as Table
                tab_parsed_table = TableImporter.call(tab_parsed)
                # Add tags
                microplate_object.add_tags_to_resource(tab_parsed_table, filter_selection, input_tag)
                microplate_object.add_tags_to_table_columns(tab_parsed_table, well_data)

                tab_parsed_resource = ResourceModel.save_from_resource(
                    tab_parsed_table, ResourceOrigin.UPLOADED, flagged=True)

                st.success(
                    f"Resource created! ✅ You can find it here : {FrontService.get_resource_url(tab_parsed_resource.id)}")
