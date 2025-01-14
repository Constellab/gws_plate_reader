
import os

from gws_core import (ConfigParams, Dashboard, DashboardType, Folder,
                      InputSpecs, OutputSpec, OutputSpecs, StreamlitResource,
                      Task, TaskInputs, TaskOutputs, TypingStyle,
                      dashboard_decorator, task_decorator)


@dashboard_decorator("BiolectorParserStandalone", dashboard_type=DashboardType.STREAMLIT)
class BiolectorParserStandaloneClass(Dashboard):

    # retrieve the path of the app folder, relative to this file
    # the dashboard code folder starts with a underscore to avoid being loaded when the brick is loaded
    def get_folder_path(self):
        return os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            "_standalone_dashboard_parser_code"
        )


@task_decorator("BiolectorParserStandalone",
                human_name="Generate a standalone dashboard to visualise data from BiolectorXT",
                short_description="Task to generate a standalone Streamlit dashboard to visualise data from BiolectorXT",
                style=TypingStyle.community_icon(icon_technical_name="dashboard", background_color="#c3fa7f"))
class BiolectorParserStandalone(Task):

    input_specs: InputSpecs = InputSpecs()
    output_specs: OutputSpecs = OutputSpecs(
        {'streamlit_app': OutputSpec(StreamlitResource, human_name="Microplate dashboard")})

    def run(self, params: ConfigParams, inputs: TaskInputs) -> TaskOutputs:

        # build the streamlit resource with the code and the resources
        streamlit_resource = StreamlitResource()
        streamlit_resource.set_dashboard(BiolectorParserStandaloneClass())

        stats_folder: Folder = Folder(self.create_tmp_dir())
        stats_folder.name = "Stats"
        streamlit_resource.add_resource(stats_folder, create_new_resource=True)

        return {'streamlit_app': streamlit_resource}
