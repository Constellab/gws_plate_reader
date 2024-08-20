
from typing import List, Optional

import streamlit as st
from gws_core import (Experiment, ExperimentCreationType,
                      ExperimentSearchBuilder, ExperimentStatus, FrontService,
                      IExperiment, Tag)

from gws_biolector.biolector_xt.tasks.biolector_download_experiment_task import \
    BiolectorDownloadExperiment2

DOWNLOAD_TAG_KEY = "biolector_download"


def download_exp_main(credentials_name: str, mock_service: bool):
    if 'existing_exp' not in st.session_state:
        st.session_state.existing_exp = None

    # Create a form
    with st.form(key='download_exp'):
        exp_id = st.text_input(label='Experiment id')
        submit_button = st.form_submit_button(label='Import biolector experiment result')

    # Handle form submission
    if submit_button:

        # check if the biolector experiment was already downloaded
        st.session_state.existing_exp = get_biolector_download_experiment(exp_id)

        # If there is no existing experiment, download the experiment
        if not st.session_state.existing_exp:
            download_experiment(exp_id, credentials_name, mock_service)

    if st.session_state.existing_exp:
        st.text('The biolector experiment result was already donwnloaded')
        if st.button('Force download'):
            download_experiment(exp_id, credentials_name, mock_service)
        else:
            st.session_state.exp_model_id = st.session_state.existing_exp

    # Show a link to open the experiment
    if 'exp_model_id' in st.session_state:

        exp_url = FrontService.get_experiment_url(st.session_state.exp_model_id)

        # show a link with target=_blank to open the experiment in a new tab
        st.link_button("Open constellab experiment", exp_url)


def download_experiment(biolector_exp_id: str,
                        credentials_name: str,
                        mock_service: bool) -> str:
    """
    Method that creates an experiment to download the biolector experiment data.

    :param biolector_exp_id: id of the biolector experiment
    :type biolector_exp_id: str
    :return: id of the experiment model
    :rtype: str
    """

    st.session_state.exp_model_id = None

    with st.spinner('Downloading experiment file'):
        experiment = IExperiment(title=f"Download Biolector experiment {biolector_exp_id}",
                                 creation_type=ExperimentCreationType.MANUAL)
        experiment.add_tag(Tag(DOWNLOAD_TAG_KEY, biolector_exp_id))
        protocol = experiment.get_protocol()

        download_task = protocol.add_task(BiolectorDownloadExperiment2, 'download', {
            'experiment_id': biolector_exp_id,
            'credentials': credentials_name,
            'mock_service': mock_service
        })

        protocol.add_sink('result', download_task >> 'result')
        protocol.add_sink('raw_data', download_task >> 'raw_data', False)

        experiment.run()

        st.session_state.exp_model_id = experiment.get_model_id()
        return experiment.get_model_id()


def get_biolector_download_experiment(biolector_exp_id: str) -> Optional[str]:
    """Method to retrieve the downloader experiment for a biolector exp id

    :param biolector_exp_id: _description_
    :type biolector_exp_id: str
    :return: experiment model id
    :rtype: str
    """

    search_builder = ExperimentSearchBuilder()
    search_builder.add_tag_filter(Tag(DOWNLOAD_TAG_KEY, biolector_exp_id))
    search_builder.add_expression(Experiment.status == ExperimentStatus.SUCCESS)

    experiments: List[Experiment] = list(search_builder.build_search())

    if len(experiments) > 0:
        return experiments[0].id

    return None
