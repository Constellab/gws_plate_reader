
import json
import os

import streamlit as st
from gws_plate_reader.biolector_xt_parser.biolectorxt_parser_dashboard import \
    run

# thoses variable will be set by the streamlit app
# don't initialize them, there are create to avoid errors in the IDE
sources: list
params: dict

# -------------------------------------------------------------------------------------------#
if not sources:
    raise Exception("Source paths are not provided.")

raw_data = sources[0]
folder_metadata = sources[1]
if len(sources)>2:
    existing_plate_layout = sources[2].get_data()
else :
    existing_plate_layout = None
metadata: dict = None
for file_name in os.listdir(folder_metadata.path):
    if file_name.endswith('BXT.json'):
        file_path = os.path.join(folder_metadata.path, file_name)
        try:
            with open(file_path, 'r', encoding='UTF-8') as json_file:
                metadata = json.load(json_file)
        except Exception as e:
            st.error(f"Error while reading the metadata file {file_name}: {e}")
            st.stop()


if metadata is None:
    st.error("No metadata file found in the provided folder. The folder must contain a file that ends with 'BXT.json'")
    st.stop()

run(raw_data.get_data(), metadata, is_standalone = False, existing_plate_layout = existing_plate_layout)
