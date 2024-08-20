
from datetime import datetime

import streamlit as st
from app.download_exp import download_exp_main
from pandas import DataFrame

from gws_biolector.biolector_xt.biolector_xt_dto import \
    CredentialsDataBiolector
from gws_biolector.biolector_xt.biolector_xt_mock_service import \
    BiolectorXTMockService
from gws_biolector.biolector_xt.biolector_xt_service import BiolectorXTService
from gws_biolector.biolector_xt.biolector_xt_service_i import \
    BiolectorXTServiceI

params: dict

""" run in local :
streamlit run /lab/user/bricks/gws_core/src/gws_core/streamlit/_main_streamlit_app.py -- --dev_config_file /lab/user/bricks/gws_biolector/src/gws_biolector/biolector_xt/_streamlit_dashboard/dev_config.json --dev_mode true
"""

# Parameters in local
params = {
    'mock_service': True,
    'biolector_credentials': None
}


def get_service(params: dict) -> BiolectorXTServiceI:

    if params.get('mock_service'):
        return BiolectorXTMockService()
    else:
        return BiolectorXTService(CredentialsDataBiolector.from_json(params.get('biolector_credentials')))


@st.cache_data
def get_experiments(_service: BiolectorXTServiceI) -> DataFrame:
    experiments = _service.get_experiments()
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

    return df


@st.cache_data
def get_protocols(_service: BiolectorXTServiceI) -> DataFrame:
    protocols = _service.get_protocols()
    protocol_dict = []
    for protocol in protocols:
        protocol_dict.append({'Id': protocol.protocol_id, 'Name': protocol.protocol_name})

    df = DataFrame(protocol_dict)

    # sort by protocol name
    df = df.sort_values(by='Name', ascending=True, ignore_index=True)

    return df


st.header("Biolector XT Dashboard")

exp_table, exp_list_tab, protocol_tab = st.tabs(
    ["Import Biolector experiment", "Biolector experiments", "Biolector protocols"])

service = get_service(params)

with exp_table:
    download_exp_main(params.get('credentials_name'), params.get('mock_service'))

with exp_list_tab:
    experiments_df = get_experiments(service)

    st.table(experiments_df)

with protocol_tab:
    protocols_df = get_protocols(service)
    st.table(protocols_df)


# Initialize session state for current directory
# if 'current_dir' not in st.session_state:
#     st.session_state.current_dir = '/lab/user/bricks'


# def switch_directory(path):
#     st.session_state.current_dir = path

# Function to display directory contents
