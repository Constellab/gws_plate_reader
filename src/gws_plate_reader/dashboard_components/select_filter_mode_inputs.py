from typing import List

import streamlit as st
from gws_plate_reader.biolector_xt_analysis.biolector_state import \
    BiolectorState


def render_select_filter_mode_inputs():
    col1, col2 = st.columns(2)
    with col1:
        init_value = BiolectorState.get_selected_filters()
        if init_value is None:
            init_value = BiolectorState.get_filters_list()
        init_value = sorted(init_value)
        selected_filters: List[str] = st.multiselect(
            '$\\textsf{\large{Select the observers to be displayed}}$', options=BiolectorState.get_filters_list(),
            default=init_value, key="selected_filters_input")
        if selected_filters != init_value:
            BiolectorState.set_selected_filters(selected_filters)
            st.rerun()

    with col2:

        # Allow the user to select duplicates
        init_value = BiolectorState.get_current_replicate_mode()
        options = ["Individual well"] + BiolectorState.get_all_keys_well_description()
        index = options.index(init_value) if init_value in options else 0
        if init_value is None:
            init_value = options[0]

        selected_well_or_replicate: str = st.selectbox("$\\textsf{\large{Select by}}$",
                                                       options=options, index=index, key="well_or_replicate_input")
        if selected_well_or_replicate != init_value:
            BiolectorState.set_current_replicate_mode(selected_well_or_replicate)
            st.rerun()
    # Select wells : all by default; otherwise those selected in the microplate
    if len(BiolectorState.get_wells_clicked()) > 0:
        st.write(f"All the wells clicked are: {', '.join(BiolectorState.get_wells_clicked())}")

    return selected_filters, selected_well_or_replicate
