

import os

from gws_core import (BoolParam, ConfigParams, ConfigSpecs, CredentialsParam,
                      CredentialsType, OutputSpec, OutputSpecs,
                      StreamlitResource, Task, TaskInputs, TaskOutputs,
                      TypingStyle, task_decorator)

from gws_biolector.biolector_xt.biolector_xt_dto import \
    CredentialsDataBiolector


@task_decorator(unique_name="BiolectorDashboard",
                human_name="Biolector Dashboard",
                short_description="Task to generate a dahsboard to interact with Biolector XT",
                style=TypingStyle.community_icon("bioreactor"))
class BiolectorDashboard(Task):

    config_specs: ConfigSpecs = {
        'credentials': CredentialsParam(credentials_type=CredentialsType.OTHER),
        'mock_service': BoolParam(human_name="Mock Service",
                                  short_description="Use the mock service to simulate the interaction with Biolector XT (for development purpose)",
                                  default_value=False, visibility="protected")
    }

    output_specs: OutputSpecs = OutputSpecs({'dashboard': OutputSpec(StreamlitResource)})

    app_path = os.path.join(
        os.path.abspath(os.path.dirname(__file__)),
        "_streamlit_dashboard"
    )

    def run(self, params: ConfigParams, inputs: TaskInputs) -> TaskOutputs:

        biolector_credentials: CredentialsDataBiolector
        try:
            biolector_credentials = CredentialsDataBiolector.from_json(params.get_value('credentials'))
        except Exception as e:
            raise ValueError("Invalid credentials data: " + str(e))

        streamlit_resource = StreamlitResource()

        streamlit_resource.set_streamlit_folder(self.app_path)
        streamlit_resource.set_param("biolector_credentials", biolector_credentials.to_json_dict())
        streamlit_resource.set_param("credentials_name", params.get_value('credentials').get('__meta__').get('name'))
        streamlit_resource.set_param("mock_service", params.get_value('mock_service'))

        streamlit_resource.style = TypingStyle.community_icon("bioreactor", background_color='#ff4b4b')

        return {'dashboard': streamlit_resource}
