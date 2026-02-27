import streamlit as st
from gws_streamlit_main import StreamlitMainState

# Initialize GWS - MUST be at the top
StreamlitMainState.initialize()


# -------------------------------------------------------------------------------------------#
sources = StreamlitMainState.get_sources()

st.info(
    "This dashboard is deprecated. Please use the new dashboard Constellab Bioprocess. You can find a demo here:"
)
st.link_button(
    "Constellab Bioprocess Dashboard Demo",
    "https://constellab.community/apps/e1ec0c56-43a3-4b4d-a642-1ca4e555c8c9/constellab-bioprocess",
)
