from typing import List

import streamlit as st
from gws_plate_reader.biolector_xt_analysis.biolector_state import \
    BiolectorState


def render_select_replicates_input(selected_well_or_replicate: str):
    if selected_well_or_replicate == "Individual well":
        return None
    dict_replicates = BiolectorState.group_wells_by_options(selected_well_or_replicate)

    st.write("Only replicates where all wells are selected and contain data will appear here.")

    init_value = BiolectorState.get_replicates_saved()
    BiolectorState.reset_options_replicates(dict_replicates)
    options = BiolectorState.get_options_replicates()
    if init_value is not None:
        for v in init_value[:]:
            if v not in options:
                init_value.remove(v)
        default = init_value
    else:
        default = options
    selected_replicates: List[str] = st.multiselect(
        '$\\textsf{\large{Select the replicates to be displayed}}$', options, default=default,
        key="select_replicates_input")
    if selected_replicates != init_value:
        BiolectorState.color_wells_replicates(dict_replicates, selected_replicates)
        st.rerun()

    if not selected_replicates:
        st.warning("Please select at least one replicate.")

    return selected_replicates
