
import os

from gws_core import (ConfigParams, ConfigSpecs, OutputSpec, OutputSpecs, StreamlitResource, Task, TaskInputs, TaskOutputs, task_decorator,
                      dashboard_decorator, Dashboard, DashboardType, Folder, TypingStyle, StrParam, JSONDict, InputSpecs, InputSpec)

@dashboard_decorator("GenerateDashboardPlateLayout", dashboard_type=DashboardType.STREAMLIT)
class GenerateDashboardPlateLayout(Dashboard):

    # retrieve the path of the app folder, relative to this file
    # the dashboard code folder starts with a underscore to avoid being loaded when the brick is loaded
    def get_app_folder_path(self):
        return os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            "_dashboard_code"
        )

@task_decorator("StreamlitGeneratorPlateLayout", human_name="Generate dashboard to fill Plate Layout",
                short_description="Task to generate a custom Streamlit dashboard to fill Plate Layout",
                style=TypingStyle.community_icon(icon_technical_name="matrix", background_color="#60a182"))
class StreamlitGeneratorPlateLayout(Task):

    config_specs: ConfigSpecs = {
        'number_wells': StrParam(allowed_values=["48", "96"],
                                human_name="Number of wells",
                                default_value="48",optional=False,
                                  short_description="The number of wells of the microplate"),

    }
    input_specs: InputSpecs = InputSpecs(
        {'plate_layout': InputSpec(JSONDict, human_name="JSONDict containing the plate_layout", is_optional=True)})

    output_specs: OutputSpecs = OutputSpecs({'streamlit_app': OutputSpec( StreamlitResource, human_name="Microplate dashboard")})

    def run(self, params: ConfigParams, inputs: TaskInputs) -> TaskOutputs:
        # Get the number of wells
        number_wells: int = int(params.get_value('number_wells'))

        # build the streamlit resource with the code and the resources
        streamlit_resource = StreamlitResource()

        folder_data: Folder = Folder(self.create_tmp_dir())
        folder_data.name = "Data"
        streamlit_resource.add_resource(folder_data, create_new_resource=True)

        # set the input in the streamlit resource
        plate_layout: JSONDict = inputs.get('plate_layout')
        if plate_layout:
            streamlit_resource.add_resource(plate_layout, create_new_resource=False)

        # set dashboard reference
        streamlit_resource.set_dashboard(GenerateDashboardPlateLayout())
        streamlit_resource.set_params({"number_wells": number_wells})

        return {'streamlit_app': streamlit_resource}
