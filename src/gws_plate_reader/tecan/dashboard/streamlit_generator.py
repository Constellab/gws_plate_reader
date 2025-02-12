
import os

from gws_core import (ConfigParams, OutputSpec, OutputSpecs, StreamlitResource, Task, TaskInputs, TaskOutputs, task_decorator,
                      dashboard_decorator, Dashboard, DashboardType, Folder, JSONDict, TypingStyle, InputSpec, InputSpecs, Table)

@dashboard_decorator("GenerateDashboardTecan", dashboard_type=DashboardType.STREAMLIT)
class GenerateDashboardTecan(Dashboard):

    # retrieve the path of the app folder, relative to this file
    # the dashboard code folder starts with a underscore to avoid being loaded when the brick is loaded
    def get_app_folder_path(self):
        return os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            "_dashboard_code"
        )

@task_decorator("StreamlitGeneratorVisualisationTecan", human_name="Generate dashboard to visualise data from Tecan",
                short_description="Task to generate a custom Streamlit dashboard to visualise data from Tecan",
                style=TypingStyle.community_icon(icon_technical_name="dashboard", background_color="#c3fa7f"))
class StreamlitGeneratorTecan(Task):

    input_specs: InputSpecs = InputSpecs({'raw_data': InputSpec(Table, human_name="Table containing the raw data"),
                                          'plate_layout': InputSpec(JSONDict, human_name="JSON containg the plate layout")})
    output_specs: OutputSpecs = OutputSpecs({'streamlit_app': OutputSpec( StreamlitResource, human_name="Microplate dashboard")})


    def run(self, params: ConfigParams, inputs: TaskInputs) -> TaskOutputs:

        # build the streamlit resource with the code and the resources
        streamlit_resource = StreamlitResource()

        # set the input in the streamlit resource
        raw_data: Table = inputs.get('raw_data')
        streamlit_resource.add_resource(raw_data, create_new_resource=False)

        # set the input in the streamlit resource
        plate_layout: JSONDict = inputs.get('plate_layout')
        streamlit_resource.add_resource(plate_layout, create_new_resource=False)

        folder_raw_data: Folder = Folder(self.create_tmp_dir())
        folder_raw_data.name = "Updated Raw Data"
        streamlit_resource.add_resource(folder_raw_data, create_new_resource=True)

        # set dashboard reference
        streamlit_resource.set_dashboard(GenerateDashboardTecan())

        return {'streamlit_app': streamlit_resource}
