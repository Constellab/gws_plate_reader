import os
from typing import List

import streamlit as st
from gws_plate_reader.biolector_xt_parser.biolectorxt_parser import \
    BiolectorXTParser
from gws_core import File, ResourceOrigin, ResourceModel, Settings, FrontService, TableImporter

def render_table_tab(microplate_object: BiolectorXTParser, filters: list):
    selected_filters: List[str] = st.multiselect(
        '$\\text{\large{Select the observers to be displayed}}$', filters, default=filters, key="table_filters")
    # Select wells : all by default; otherwise those selected in the microplate
    if len(st.session_state['well_clicked']) > 0:
        st.write(f"All the wells clicked are: {', '.join(st.session_state['well_clicked'])}")

    for filter_selection in selected_filters:
        st.write(f"$\\text{{\Large{{{filter_selection}}}}}$")
        df = microplate_object.get_table_by_filter(filter_selection)
        if len(st.session_state['well_clicked']) > 0:
            # TODO: voir si il faut les classer par ordre croissant ?
            df = df[["time", "Temps_en_h"] + st.session_state['well_clicked']]
        st.dataframe(df.style.format(thousands=" ", precision=4))
        #If the dashboard is not standalone, we add a button to generate a resource
        if not st.session_state.is_standalone:
            # Add the button to resource containing the data parsed
            if st.button(f"Generate {filter_selection} resource", icon = ":material/note_add:"):
                path_temp = os.path.join(os.path.abspath(os.path.dirname(__file__)), Settings.make_temp_dir())
                full_path = os.path.join(path_temp, f"{filter_selection}.csv")
                tab_parsed: File = File(full_path)
                tab_parsed.write(df.to_csv(index = False))
                #Import the resource as Table
                tab_parsed_table = TableImporter.call(tab_parsed)
                tab_parsed_resource = ResourceModel.save_from_resource(
                    tab_parsed_table, ResourceOrigin.UPLOADED, flagged=True)
                st.success(f"Resource created! ✅ You can find it here : {FrontService.get_resource_url(tab_parsed_resource.id)}")
