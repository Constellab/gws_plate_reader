
import os
from gws_core import (ConfigParams, InputSpec, InputSpecs,
                      OutputSpec, OutputSpecs, Task, TaskInputs, TaskOutputs, task_decorator, Table, Folder, TypingStyle)
from gws_core.streamlit.streamlit_resource import StreamlitResource


@task_decorator("StreamlitGeneratorVisualisation", human_name="Generate dashboard to visualise data from BiolectorXT",
                short_description="Task to generate a custom Streamlit dashboard to visualise data from BiolectorXT",
                style=TypingStyle.community_icon(icon_technical_name="dashboard", background_color="#c3fa7f"))
class StreamlitGenerator(Task):

    input_specs: InputSpecs = InputSpecs({'raw_data': InputSpec(Table, human_name="Table containing the raw data"),
                                          'folder_metadata': InputSpec(Folder, human_name="Folder containing the metadata")})
    output_specs: OutputSpecs = OutputSpecs({'streamlit_app': OutputSpec( StreamlitResource, human_name="Microplate dashboard")})

    # retrieve the path of the app folder, relative to this file
    # the dashboard code folder starts with a underscore to avoid being loaded when the brick is loaded
    streamlit_app_folder = os.path.join(
        os.path.abspath(os.path.dirname(__file__)),
        "_dashboard_code"
    )

    def run(self, params: ConfigParams, inputs: TaskInputs) -> TaskOutputs:

        # build the streamlit resource with the code and the resources
        streamlit_resource = StreamlitResource()

        # set the input in the streamlit resource
        raw_data: Table = inputs.get('raw_data')
        folder_metadata: Folder = inputs.get('folder_metadata')
        streamlit_resource.add_resource(raw_data, create_new_resource=False)
        streamlit_resource.add_resource(folder_metadata, create_new_resource=False)

        folder_growth_rate: Folder = Folder(self.create_tmp_dir())
        folder_growth_rate.name = "Growth Rate"
        streamlit_resource.add_resource(folder_growth_rate, create_new_resource=True)
        # set the app folder
        streamlit_resource.set_streamlit_folder(self.streamlit_app_folder)

        return {'streamlit_app': streamlit_resource}
