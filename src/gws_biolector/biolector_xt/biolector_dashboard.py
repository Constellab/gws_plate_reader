

import os

from gws_core import (ConfigParams, ConfigSpecs, CredentialsParam,
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

        streamlit_resource.style = TypingStyle.community_icon("bioreactor", background_color='#ff4b4b')

        return {'dashboard': streamlit_resource}
