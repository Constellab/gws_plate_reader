from typing import List

import streamlit as st

class BiolectorState():

    WELL_CLICKED_KEY = 'well_clicked'
    IS_STANDALONE_KEY = "is_standalone"
    SELECTED_ROWS_KEY = "selected_rows"
    SELECTED_COLS_KEY = "selected_cols"
    PLATE_LAYOUT_KEY = "plate_layout"
    OPTIONS_REPLICATES_KEY = "options_replicates"
    REPLICATED_WELLS_SHOW_KEY = 'replicated_wells_show'
    WELLS_TO_SHOW_KEY = 'wells_to_show'
    PLOT_REPLICATES_KEY = "plot_replicates"
    PLOT_REPLICATES_SAVED_KEY = "plot_replicates_saved"

    @classmethod
    def init(cls, is_standalone : bool, existing_plate_layout):
        # Initialize the session state for clicked wells if it doesn't exist
        st.session_state[cls.WELL_CLICKED_KEY] = cls.get_well_clicked()
        # Session state to track if the dashboard is standalone or not
        st.session_state[cls.IS_STANDALONE_KEY] = cls.get_is_standalone(is_standalone)
        # Session state to track selected rows/columns
        st.session_state[cls.SELECTED_ROWS_KEY] = cls.get_selected_rows()
        st.session_state[cls.SELECTED_COLS_KEY] = cls.get_selected_cols()
        # existing plate layout
        st.session_state[cls.PLATE_LAYOUT_KEY] = cls.get_plate_layout(existing_plate_layout)
        # options_replicates
        st.session_state[cls.OPTIONS_REPLICATES_KEY] = cls.get_options_replicates()
        st.session_state[cls.WELLS_TO_SHOW_KEY] = cls.get_wells_to_show()
        st.session_state[cls.REPLICATED_WELLS_SHOW_KEY] = cls.get_replicated_wells_show()


    @classmethod
    def color_wells_replicates(cls, dict_replicates):
        selected_replicates = cls.get_plot_replicates()  # Retrieve the selected values
        st.session_state[cls.PLOT_REPLICATES_SAVED_KEY] = cls.get_plot_replicates()
        cls.reset_session_state_wells()
        if selected_replicates:
            # Get the corresponding wells
            for replicate in selected_replicates:
                wells = dict_replicates[replicate]
                st.session_state[cls.WELLS_TO_SHOW_KEY].extend(wells)
                for i in range (0, len(wells)):
                    if wells[i] not in st.session_state[cls.REPLICATED_WELLS_SHOW_KEY]:
                        st.session_state[cls.REPLICATED_WELLS_SHOW_KEY].append(wells[i])
        st.rerun()

    @classmethod
    def get_plot_replicates_saved(cls) -> List:
        #It's the value of multiselect replicates
        return st.session_state.get(cls.PLOT_REPLICATES_SAVED_KEY, [])

    @classmethod
    def get_plot_replicates(cls) -> List:
        #It's the value of multiselect replicates
        return st.session_state.get(cls.PLOT_REPLICATES_KEY, [])

    @classmethod
    def get_replicated_wells_show(cls) -> List:
        return st.session_state.get(cls.REPLICATED_WELLS_SHOW_KEY, [])

    @classmethod
    def get_wells_to_show(cls) -> List:
        return st.session_state.get(cls.WELLS_TO_SHOW_KEY, [])

    @classmethod
    def reset_session_state_wells(cls)-> None:
        st.session_state[cls.REPLICATED_WELLS_SHOW_KEY] = []
        st.session_state[cls.WELLS_TO_SHOW_KEY] = []

    @classmethod
    def get_options_replicates(cls, dict_replicates = None, microplate_object = None, cross_out_wells = None) -> List:
        st.session_state[cls.OPTIONS_REPLICATES_KEY] = []
        if dict_replicates:
            for replicate in dict_replicates:
                if microplate_object.is_microfluidics() and any(well in cross_out_wells for well in dict_replicates[replicate]) :
                    continue
                # If the user has selected some wells, all the wells of a replicates need to be selected to appear #TODO : see how to better manage it because it can be confusing
                elif len(cls.get_well_clicked()) > 0:
                    if any(well not in cls.get_well_clicked() for well in dict_replicates[replicate]):
                        continue
                    else:
                        st.session_state[cls.OPTIONS_REPLICATES_KEY].append(replicate)
                else:
                    st.session_state[cls.OPTIONS_REPLICATES_KEY].append(replicate)

        return st.session_state.get(cls.OPTIONS_REPLICATES_KEY, [])

    @classmethod
    def get_plate_layout(cls, existing_plate_layout = None):
        if existing_plate_layout:
            # Rename keys if they have a single-digit number : A1 -> A01
            existing_plate_layout = {
                (key[0] + "0" + key[1:]) if len(key) == 2 else key: value
                for key, value in existing_plate_layout.items()
            }
            st.session_state[cls.PLATE_LAYOUT_KEY] = existing_plate_layout
        return st.session_state.get(cls.PLATE_LAYOUT_KEY, existing_plate_layout)

    @classmethod
    def get_is_standalone(cls, is_standalone = None) -> List:
        return st.session_state.get(cls.IS_STANDALONE_KEY, is_standalone)

    @classmethod
    def get_selected_rows(cls) -> List:
        return st.session_state.get(cls.SELECTED_ROWS_KEY, [])

    @classmethod
    def append_selected_rows(cls, well) -> None:
        st.session_state[cls.SELECTED_ROWS_KEY].append(well)

    @classmethod
    def remove_selected_rows(cls, well) -> None:
        st.session_state[cls.SELECTED_ROWS_KEY].remove(well)

    @classmethod
    def get_selected_cols(cls) -> List:
        return st.session_state.get(cls.SELECTED_COLS_KEY, [])

    @classmethod
    def append_selected_cols(cls, well) -> None:
        st.session_state[cls.SELECTED_COLS_KEY].append(well)

    @classmethod
    def remove_selected_cols(cls, well) -> None:
        st.session_state[cls.SELECTED_COLS_KEY].remove(well)

    @classmethod
    def get_well_clicked(cls) -> List:
        return st.session_state.get(cls.WELL_CLICKED_KEY, [])

    @classmethod
    def append_well_clicked(cls, well) -> None:
        st.session_state[cls.WELL_CLICKED_KEY].append(well)

    @classmethod
    def remove_well_clicked(cls, well) -> None:
        st.session_state[cls.WELL_CLICKED_KEY].remove(well)

    @classmethod
    def reset_wells(cls)-> None:
        st.session_state[cls.WELL_CLICKED_KEY] = []


