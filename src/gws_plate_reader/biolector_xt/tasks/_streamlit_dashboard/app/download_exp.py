
from typing import List, Optional

import streamlit as st
from gws_core import (FrontService, Scenario, ScenarioCreationType,
                      ScenarioProxy, ScenarioSearchBuilder, ScenarioStatus,
                      Tag)
from gws_plate_reader.biolector_xt.tasks.biolector_download_experiment_task import \
    BiolectorDownloadExperiment
from gws_plate_reader.biolector_xt_parser.dashboard.parser_dashboard import \
    ParserDashboard

DOWNLOAD_TAG_KEY = "biolector_download"


def render_download_exp_main(credentials_name: str, mock_service: bool):
    st.header("Import Biolector experiment")
    if 'existing_scenario' not in st.session_state:
        st.session_state.existing_scenario = None

    # Create a form
    with st.form(key='download_exp'):
        exp_id = st.text_input(label='Experiment id')
        submit_button = st.form_submit_button(label='Import biolector experiment result')

    # Handle form submission
    if submit_button:

        if not exp_id:
            st.error('Please provide the biolector experiment id')
            return

        # check if the biolector experiment was already downloaded
        st.session_state.existing_scenario = get_biolector_download_experiment(exp_id)

        # If there is no existing scenario, download the experiment
        if not st.session_state.existing_scenario:
            scenario = download_experiment(exp_id, credentials_name, mock_service)
            st.session_state.scenario_model = scenario

    if st.session_state.existing_scenario:
        st.text('The biolector experiment result was already downloaded')
        if st.button('Force download'):
            scenario = download_experiment(exp_id, credentials_name, mock_service)
            st.session_state.scenario_model = scenario

        else:
            st.session_state.scenario_model = st.session_state.existing_scenario

    # Show a link to open the scenario
    if 'scenario_model' in st.session_state:

        scenario: Scenario = st.session_state.scenario_model

        exp_url = FrontService.get_scenario_url(scenario.id)

        # show a link with target=_blank to open the scenario in a new tab
        st.link_button("Open constellab scenario", exp_url)


def download_experiment(biolector_exp_id: str,
                        credentials_name: str,
                        mock_service: bool) -> Scenario:
    """
    Method that creates a scenario to download the biolector experiment data.

    :param biolector_exp_id: id of the biolector experiment
    :type biolector_exp_id: str
    :return: id of the scenario model
    :rtype: str
    """

    st.session_state.scenario_model = None

    with st.spinner('Downloading experiment file'):
        scenario = ScenarioProxy(title=f"Download Biolector experiment {biolector_exp_id}",
                                 creation_type=ScenarioCreationType.MANUAL)
        scenario.add_tag(Tag(DOWNLOAD_TAG_KEY, biolector_exp_id))
        protocol = scenario.get_protocol()

        download_task = protocol.add_task(BiolectorDownloadExperiment, 'download', {
            'experiment_id': biolector_exp_id,
            'credentials': credentials_name,
            'mock_service': mock_service
        })

        protocol.add_output('result', download_task.get_output_port('result'))
        protocol.add_output('raw_data', download_task.get_output_port('raw_data'), False)

        streamlit_generator = protocol.add_task(ParserDashboard, 'streamlit_generator')

        protocol.add_connector(download_task.get_output_port('result'), streamlit_generator.get_input_port('raw_data'))
        protocol.add_connector(
            download_task.get_output_port('raw_data'),
            streamlit_generator.get_input_port('folder_metadata'))
        protocol.add_output('streamlit_app', streamlit_generator.get_output_port('streamlit_app'))

        try:
            scenario.run()
        except Exception as e:
            st.error(f'An error occurred while downloading the experiment : {str(e)}')

        return scenario.refresh().get_model()


def get_biolector_download_experiment(biolector_exp_id: str) -> Optional[Scenario]:
    """Method to retrieve the downloader scenario for a biolector exp id

    :param biolector_exp_id: _description_
    :type biolector_exp_id: str
    :return: scenario model id
    :rtype: str
    """

    search_builder = ScenarioSearchBuilder()
    search_builder.add_tag_filter(Tag(DOWNLOAD_TAG_KEY, biolector_exp_id))
    search_builder.add_expression(Scenario.status == ScenarioStatus.SUCCESS)

    scenarios: List[Scenario] = list(search_builder.build_search())

    if len(scenarios) > 0:
        return scenarios[0]

    return None
