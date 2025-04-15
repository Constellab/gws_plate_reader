import os

from gws_core import (ConfigParams, Dashboard, DashboardType, OutputSpec,
                      OutputSpecs, StreamlitResource, Task, TaskInputs,
                      TaskOutputs, TypingStyle, dashboard_decorator,
                      task_decorator)


@dashboard_decorator("ParserMultipleExperimentsDashboard", dashboard_type=DashboardType.STREAMLIT)
class ParserMultipleExperimentsDashboardClass(Dashboard):

    def get_app_folder_path(self):
        return os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            "_parser_multiple_experiments_dashboard_code"
        )


@task_decorator("StreamlitGeneratorVisualisationMultipleExperiments",
                human_name="Generate dashboard to visualise data from multiple experiments",
                short_description="Task to generate a custom Streamlit dashboard to visualise data from multiple experiments",
                style=TypingStyle.community_icon(icon_technical_name="dashboard", background_color="#c3fa7f"))
class ParserMultipleExperimentsDashboard(Task):
    """
    Generate a dashboard to visualise data from multiple experiments.
    """

    output_specs: OutputSpecs = OutputSpecs(
        {'streamlit_app': OutputSpec(StreamlitResource, human_name="Microplate multiple experiments dashboard")}
    )

    def run(self, params: ConfigParams, inputs: TaskInputs) -> TaskOutputs:
        # build the streamlit resource with the code and the resources
        streamlit_resource = StreamlitResource()

        streamlit_resource.set_dashboard(ParserMultipleExperimentsDashboardClass())

        return {'streamlit_app': streamlit_resource}
