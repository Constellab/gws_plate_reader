from typing import List, Dict, Optional, Any

import streamlit as st

class PlateLayoutState():

    SUCCESS_MESSAGE_KEY = 'success_message'
    WELL_CLICKED_KEY = 'well_clicked'
    SELECTED_ROWS_KEY = "selected_rows"
    SELECTED_COLS_KEY = "selected_cols"
    SELECTED_KEY_TAGS_KEY = 'selected_key_tags'
    PLATE_LAYOUT_KEY = 'plate_layout'
    PENDING_KEY_REMOVAL_KEY = 'pending_key_removal'
    MULTISELECT_TAG_KEYS_KEY = 'multiselect_tag_keys'

    def __init__(self):
        # Initialize the session state for clicked wells if it doesn't exist
        st.session_state[self.WELL_CLICKED_KEY] = self.get_well_clicked()
        # Success message
        st.session_state[self.SUCCESS_MESSAGE_KEY] = self.get_success_message()
        # Session state to track selected rows/columns
        st.session_state[self.SELECTED_ROWS_KEY] = self.get_selected_rows()
        st.session_state[self.SELECTED_COLS_KEY] = self.get_selected_cols()
        # Selected key tags
        st.session_state[self.SELECTED_KEY_TAGS_KEY] = self.get_selected_key_tags()
        # Plate layout
        st.session_state[self.PLATE_LAYOUT_KEY] = self.get_plate_layout()

    @classmethod
    def get_success_message(cls) -> Optional[str]:
        return st.session_state.get(cls.SUCCESS_MESSAGE_KEY, None)

    @classmethod
    def set_success_message(cls, message: Optional[str]) -> None:
        st.session_state[cls.SUCCESS_MESSAGE_KEY] = message

    @classmethod
    def get_well_clicked(cls) -> List[str]:
        return st.session_state.get(cls.WELL_CLICKED_KEY, [])

    @classmethod
    def set_well_clicked(cls, wells: List[str]) -> None:
        st.session_state[cls.WELL_CLICKED_KEY] = wells

    @classmethod
    def reset_wells(cls) -> None:
        st.session_state[cls.WELL_CLICKED_KEY] = []

    @classmethod
    def get_selected_rows(cls) -> List[str]:
        return st.session_state.get(cls.SELECTED_ROWS_KEY, [])

    @classmethod
    def set_selected_rows(cls, rows: List[str]) -> None:
        st.session_state[cls.SELECTED_ROWS_KEY] = rows

    @classmethod
    def get_selected_cols(cls) -> List[int]:
        return st.session_state.get(cls.SELECTED_COLS_KEY, [])

    @classmethod
    def set_selected_cols(cls, cols: List[int]) -> None:
        st.session_state[cls.SELECTED_COLS_KEY] = cols

    @classmethod
    def get_selected_key_tags(cls) -> Dict[str, str]:
        return st.session_state.get(cls.SELECTED_KEY_TAGS_KEY, {})

    @classmethod
    def set_selected_key_tags(cls, key_tags: Dict[str, str]) -> None:
        st.session_state[cls.SELECTED_KEY_TAGS_KEY] = key_tags

    @classmethod
    def get_plate_layout(cls) -> Dict[str, Any]:
        return st.session_state.get(cls.PLATE_LAYOUT_KEY, {})

    @classmethod
    def set_plate_layout(cls, layout: Dict[str, Any]) -> None:
        st.session_state[cls.PLATE_LAYOUT_KEY] = layout

    @classmethod
    def get_pending_key_removal(cls) -> Optional[Dict[str, Any]]:
        return st.session_state.get(cls.PENDING_KEY_REMOVAL_KEY, None)

    @classmethod
    def set_pending_key_removal(cls, removal_data: Optional[Dict[str, Any]]) -> None:
        if removal_data is None:
            if cls.PENDING_KEY_REMOVAL_KEY in st.session_state:
                del st.session_state[cls.PENDING_KEY_REMOVAL_KEY]
        else:
            st.session_state[cls.PENDING_KEY_REMOVAL_KEY] = removal_data

    @classmethod
    def get_multiselect_tag_keys(cls) -> List[str]:
        return st.session_state.get(cls.MULTISELECT_TAG_KEYS_KEY, [])

    @classmethod
    def set_multiselect_tag_keys(cls, keys: List[str]) -> None:
        st.session_state[cls.MULTISELECT_TAG_KEYS_KEY] = keys