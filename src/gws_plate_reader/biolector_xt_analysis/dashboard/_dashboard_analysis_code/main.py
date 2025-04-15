from typing import Dict, List

import streamlit as st
from gws_core.impl.table.table import Table
from gws_plate_reader.biolector_xt.tasks._streamlit_dashboard.app.download_exp import \
    DOWNLOAD_TAG_KEY
from gws_plate_reader.biolector_xt_analysis.biolectorxt_analysis_dashboard import \
    run

# thoses variable will be set by the streamlit app
# don't initialize them, there are create to avoid errors in the IDE
sources: list
params: dict

# -------------------------------------------------------------------------------------------#
if not sources:
    raise Exception("Source paths are not provided.")

parsed_data: List[Table] = sources

if len(parsed_data) == 0:
    st.error("No parsed data found.")
    st.stop()

comment_tag = parsed_data[0].tags.get_by_key('comment')[0] if len(
    parsed_data[0].tags.get_by_key('comment')) > 0 else None
st.session_state["comment_tag"] = comment_tag.value if comment_tag else None
name_tag = parsed_data[0].tags.get_by_key('name')[0] if len(
    parsed_data[0].tags.get_by_key('name')) > 0 else None
st.session_state["name_tag"] = name_tag.value if name_tag else None
user_name_tag = parsed_data[0].tags.get_by_key('user_name')[0] if len(
    parsed_data[0].tags.get_by_key('user_name')) > 0 else None
st.session_state["user_name_tag"] = user_name_tag.value if user_name_tag else None
date_tag = parsed_data[0].tags.get_by_key('date')[0] if len(
    parsed_data[0].tags.get_by_key('date')) > 0 else None
st.session_state["date_tag"] = date_tag.value if date_tag else None
experiment_id = parsed_data[0].tags.get_by_key('raw_data')[0] if len(
    parsed_data[0].tags.get_by_key('raw_data')) > 0 else None
st.session_state["raw_data"] = experiment_id.value if experiment_id else None

input_tag = parsed_data[0].tags.get_by_key(DOWNLOAD_TAG_KEY)[0] if len(
    parsed_data[0].tags.get_by_key(DOWNLOAD_TAG_KEY)) > 0 else None

data: Dict[str, Table] = {}
for table in parsed_data:
    table_name = table.name
    if table_name in data:
        raise Exception(f"Table {table_name} already exists in the data dictionary.")
    data[table_name] = table

run(data, is_standalone=False, input_tag=input_tag)
