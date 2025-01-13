from typing import List

import streamlit as st
from gws_biolector.biolector_xt_parser.biolectorxt_parser import \
    BiolectorXTParser


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
