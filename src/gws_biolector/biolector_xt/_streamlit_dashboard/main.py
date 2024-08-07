
import os
from datetime import datetime

import streamlit as st
from pandas import DataFrame

from gws_biolector.biolector_xt.biolector_xt_dto import \
    CredentialsDataBiolector
from gws_biolector.biolector_xt.biolector_xt_mock_service import \
    BiolectorXTMockService
from gws_biolector.biolector_xt.biolector_xt_service import BiolectorXTService

params: dict

# run in local :  streamlit run /lab/user/bricks/gws_core/src/gws_core/streamlit/_main_streamlit_app.py -- --dev_config_file /lab/user/bricks/gws_biolector/src/gws_biolector/biolector_xt/_streamlit_dashboard/dev_config.json --dev_mode true
st.header("Biolector XT Dashboard")
# service = BiolectorXTService(CredentialsDataBiolector.from_json(params.get('biolector_credentials')))
service = BiolectorXTMockService()

protocol_tab, exp_list_tab, exp_table = st.tabs(["Protocols", "Experiments", "Experiment"])

with protocol_tab:

    # show the protocol in a table
    protocols = service.get_protocols()
    protocol_dict = []
    for protocol in protocols:
        protocol_dict.append({'Id': protocol.protocol_id, 'Name': protocol.protocol_name})

    df = DataFrame(protocol_dict)
    st.table(df)


with exp_list_tab:
    experiments = service.get_experiments()
    exp_dict = []
    for exp_folder in experiments:
        # date format : 2023-12-07T18:11:41+02:00, convert to datetime
        exp_dict.append({'Id': exp_folder.experiment_id,
                         'Protocol id': exp_folder.protocol_id,
                         'Start Date': datetime.fromisoformat(exp_folder.start_time),
                         'File path': exp_folder.file_path,
                         'Finished': 'Yes' if exp_folder.finished else 'No'
                         })

    df = DataFrame(exp_dict)

    # sort by start date
    df = df.sort_values(by='Start Date', ascending=False, ignore_index=True)

    # add a button to download the file in last column

    st.table(df)

with exp_table:

    # Create a form
    with st.form(key='download_exp'):
        exp_id = st.text_input(label='Experiment id')
        submit_button = st.form_submit_button(label='Download experiment')

    # Handle form submission
    if submit_button:

        with st.spinner('Downloading experiment file'):
            exp_folder = service.download_experiment(exp_id)
            st.session_state.exp_folder = exp_folder

    if 'exp_folder' in st.session_state:
        st.write('Experiment folder:', st.session_state.exp_folder)
        exp_folder = st.session_state.exp_folder

        # list the files in the folder
        files = os.listdir(exp_folder)

        selected_file = st.selectbox("View file", files, index=0)

        # show a download file button
        with open(os.path.join(exp_folder, selected_file), 'rb') as f:
            st.download_button('Download file', f, file_name=selected_file)


# Initialize session state for current directory
# if 'current_dir' not in st.session_state:
#     st.session_state.current_dir = '/lab/user/bricks'


# def switch_directory(path):
#     st.session_state.current_dir = path

# Function to display directory contents
