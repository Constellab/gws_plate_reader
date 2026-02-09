import streamlit as st

from gws_plate_reader.biolector_xt_analysis._dashboard_core.biolector_state import BiolectorState


def render_select_filter_mode_inputs():
    col1, col2 = st.columns(2)
    with col1:
        init_value = BiolectorState.get_selected_filters()
        if init_value is None:
            init_value = BiolectorState.get_filters_list()
        init_value = sorted(init_value)
        selected_filters: list[str] = st.multiselect(
            "Select the observers to display",
            options=BiolectorState.get_filters_list(),
            default=init_value,
            key="selected_filters_input",
        )
        if selected_filters != init_value:
            BiolectorState.set_selected_filters(selected_filters)
            st.rerun()

    with col2:
        # Allow the user to select duplicates
        init_value = BiolectorState.get_current_replicate_mode()
        options = ["Individual wells"] + BiolectorState.get_all_keys_well_description()
        index = options.index(init_value) if init_value in options else 0
        if init_value is None:
            init_value = options[0]

        selected_well_or_replicate: str = st.selectbox(
            "Filter by", options=options, index=index, key="well_or_replicate_input"
        )
        if selected_well_or_replicate != init_value:
            BiolectorState.set_current_replicate_mode(selected_well_or_replicate)
            st.rerun()

    return selected_filters, selected_well_or_replicate
