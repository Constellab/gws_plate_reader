from typing import List

import streamlit as st

class PlateLayoutState():

    SUCCESS_MESSAGE_KEY = 'success_message'
    WELL_CLICKED_KEY = 'well_clicked'
    SELECTED_ROWS_KEY = "selected_rows"
    SELECTED_COLS_KEY = "selected_cols"


    def __init__(self):
        # Initialize the session state for clicked wells if it doesn't exist
        st.session_state[self.WELL_CLICKED_KEY] = self.get_well_clicked()
        # Success message
        st.session_state[self.SUCCESS_MESSAGE_KEY] = self.get_success_message()
        # Session state to track selected rows/columns
        st.session_state[self.SELECTED_ROWS_KEY] = self.get_selected_rows()
        st.session_state[self.SELECTED_COLS_KEY] = self.get_selected_cols()

    @classmethod
    def get_success_message(self) -> str :
        return st.session_state.get(self.SUCCESS_MESSAGE_KEY, None)

    @classmethod
    def get_well_clicked(self) -> List:
        return st.session_state.get(self.WELL_CLICKED_KEY, [])

    @classmethod
    def reset_wells(self) -> None:
        st.session_state[self.WELL_CLICKED_KEY] = []

    @classmethod
    def get_selected_rows(self) -> List:
        return st.session_state.get(self.SELECTED_ROWS_KEY, [])

    @classmethod
    def get_selected_cols(self) -> List:
        return st.session_state.get(self.SELECTED_COLS_KEY, [])