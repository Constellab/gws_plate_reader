import streamlit as st
from app.download_exp import render_download_exp_main
from gws_core import Credentials, CredentialsType
from gws_plate_reader.biolector_xt.biolector_xt_mock_service import \
    BiolectorXTMockService
from gws_plate_reader.biolector_xt.biolector_xt_service import \
    BiolectorXTService
from gws_plate_reader.biolector_xt.biolector_xt_service_i import \
    BiolectorXTServiceI
from gws_plate_reader.biolector_xt.biolector_xt_types import \
    CredentialsDataBiolector
from pandas import DataFrame

params: dict

""" run in local :
gws streamlit run-dev dev_config.json --server.runOnSave
"""

# TODO : handle error when biolector is off or not reachable
# TODO : if get experiment didn't work, don't break the app, same for protocol


@st.cache_data
def get_service(params: dict) -> BiolectorXTServiceI:
    if params.get('mock_service'):
        return BiolectorXTMockService()
    else:
        credentials_name = params.get('credentials_name')

        credentials = Credentials.find_by_name_and_check(credentials_name, CredentialsType.OTHER)

        data = CredentialsDataBiolector.from_json(credentials.get_data_object().data)
        return BiolectorXTService(data)


@st.cache_data
def get_experiments(_service: BiolectorXTServiceI) -> DataFrame:
    experiments = _service.get_biolector_experiments()
    exp_dict = []
    for exp in experiments:
        # date format : 2023-12-07T18:11:41+02:00, convert to datetime
        exp_dict.append({'Id': exp.id,
                         'Protocol id': exp.protocol.id,
                         'Protocol name': exp.protocol.name,
                         'Start Date': exp.start_time,
                         'File path': exp.file_path,
                         'Finished': 'Yes' if exp.finished else 'No'
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


service = get_service(params)


def experiments_page():
    try:
        st.header("Biolector experiments")
        experiments_df = get_experiments(service)
        st.dataframe(experiments_df, use_container_width=True,
                     hide_index=True, height=600)
    except Exception as e:
        st.error(f"An error occurred while fetching experiments: {str(e)}")


def protocols_page():
    try:
        st.header("Bioxlector protocols")
        protocols_df = get_protocols(service)
        st.dataframe(protocols_df, use_container_width=True,
                     hide_index=True, height=600)
    except Exception as e:
        st.error(f"An error occurred while fetching protocols: {str(e)}")


def render_download_exp_page():
    render_download_exp_main(params.get('credentials_name'), params.get('mock_service'))


pg = st.navigation([st.Page(render_download_exp_page, title='Import Biolector experiment', url_path='import'),
                    st.Page(experiments_page, title='Experiments', url_path='experiments'),
                    st.Page(protocols_page, title='Protocols', url_path='protocols')])
pg.run()
