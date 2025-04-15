

import os

from gws_core import (BoolParam, ConfigParams, ConfigSpecs,
                      CredentialsDataOther, CredentialsParam, CredentialsType,
                      Dashboard, DashboardType, OutputSpec, OutputSpecs,
                      StreamlitResource, Task, TaskInputs, TaskOutputs,
                      TypingStyle, dashboard_decorator, task_decorator)
from gws_plate_reader.biolector_xt.biolector_xt_types import \
    CredentialsDataBiolector


@dashboard_decorator("BiolectorDashboard", dashboard_type=DashboardType.STREAMLIT)
class BiolectorDashboardClass(Dashboard):

    # retrieve the path of the app folder, relative to this file
    # the dashboard code folder starts with a underscore to avoid being loaded when the brick is loaded
    def get_app_folder_path(self):
        return os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            "_streamlit_dashboard"
        )


@task_decorator(unique_name="BiolectorDashboard",
                human_name="Biolector Dashboard",
                short_description="Task to generate a dashboard to interact with Biolector XT",
                style=TypingStyle.community_icon("bioreactor"))
class BiolectorDashboard(Task):
    """Generate a dahsboard to interact with Biolector XT.

    With the dashbaord the user can:
    - Download the data from a Biolector XT experiment and extract the table
    - List the available experiments
    - List the available protocols

    To work, this task requires the credentials to access the Biolector XT API. The credentials must be provided in the
    Monitoring Credentials section. The credentials must be of type 'Other' and must contain the following fields:
    - endpoint_url: The URL of the Biolector XT API
    - secure_channel: A boolean ('true' or 'false') to indicate if the connection is secure (HTTPS) or not

    The task also has an advanced parameter 'Mock Service' that can be used to simulate the interaction with Biolector XT. This
    parameter is useful for development purposes when the Biolector XT API is not available.

    """

    config_specs: ConfigSpecs = ConfigSpecs({
        'credentials': CredentialsParam(credentials_type=CredentialsType.OTHER),
        'mock_service': BoolParam(human_name="Mock Service",
                                  short_description="Use the mock service to simulate the interaction with Biolector XT (for development purpose)",
                                  default_value=False, visibility="protected")
    })

    output_specs: OutputSpecs = OutputSpecs(
        {'dashboard': OutputSpec(StreamlitResource)})

    def run(self, params: ConfigParams, inputs: TaskInputs) -> TaskOutputs:

        credentials_data: CredentialsDataOther = params.get_value(
            'credentials')

        # check the credentials data
        try:
            CredentialsDataBiolector.from_json(credentials_data.data)
        except Exception as e:
            self.log_error_message("Invalid credentials data: " + str(e))
            raise ValueError(
                "Invalid credentials data. The credentials must be of type 'Other' and must contain the fields 'endpoint_url' and 'secure_channel'. Please update your credentials.")

        streamlit_resource = StreamlitResource()

        streamlit_resource.set_dashboard(BiolectorDashboardClass())
        streamlit_resource.set_param(
            "credentials_name", credentials_data.meta.name)
        streamlit_resource.set_param(
            "mock_service", params.get_value('mock_service'))

        streamlit_resource.style = TypingStyle.community_icon(
            "bioreactor", background_color='#ff4b4b')

        return {'dashboard': streamlit_resource}
