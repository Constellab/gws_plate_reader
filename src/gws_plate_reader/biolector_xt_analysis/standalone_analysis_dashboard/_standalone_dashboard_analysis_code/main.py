import streamlit as st
from gws_streamlit_main import StreamlitMainState

# Initialize GWS - MUST be at the top
StreamlitMainState.initialize()

# This dashboard is a micro-Saas that allows users to analyze Biolector data.
# It is a standalone dashboard where user can upload their zip biolector XT data
# and get the analysis of the data.


st.info(
    "This dashboard is a deprecated dashboard. Please use the new dashboard Constellab Bioprocess. You can find a demo here:"
)
st.link_button(
    "Constellab Bioprocess Dashboard Demo",
    "https://constellab.community/apps/e1ec0c56-43a3-4b4d-a642-1ca4e555c8c9/constellab-bioprocess",
)
