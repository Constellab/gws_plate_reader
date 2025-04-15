
import os

from gws_core import (ConfigParams, Dashboard, DashboardType, InputSpec,
                      InputSpecs, OutputSpec, OutputSpecs, ResourceSet,
                      StreamlitResource, Task, TaskInputs, TaskOutputs,
                      TypingStyle, dashboard_decorator, task_decorator)


@dashboard_decorator("AnalysisDashboard", dashboard_type=DashboardType.STREAMLIT)
class AnalysisDashboardClass(Dashboard):

    # retrieve the path of the app folder, relative to this file
    # the dashboard code folder starts with a underscore to avoid being loaded when the brick is loaded
    def get_app_folder_path(self):
        return os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            "_dashboard_analysis_code"
        )


@task_decorator("StreamlitGeneratorVisualisation",
                human_name="Generate dashboard to visualise data from BiolectorXT",
                short_description="Task to generate a custom Streamlit dashboard to visualise data from BiolectorXT",
                style=TypingStyle.community_icon(icon_technical_name="dashboard", background_color="#c3fa7f"))
class AnalysisDashboard(Task):
    """
    Generate a dashboard to visualise data from BiolectorXT.

    Check this story for more details: [BiolectorXT](https://constellab.community/stories/4f2d0ea1-8718-430d-8501-2778fbbbedcf/unlock-the-power-of-your-biolector-xt-data-with-constellab)

    ## How It Works: 

    - ⬆️ Upload your CSV and JSON files.
    - 🚀 Get redirected to the intuitive Analysis Dashboard.
    - 🔍 Navigate through data and insights effortlessly.

    ## Tables page

    This page lets you explore raw data for each observer (e.g., biomass).
    Simply select the wells you want to focus on directly on the microplate view.
    Selected wells are highlighted in green, and the table dynamically updates to display results for your selection.

    ## Plots page

    Visualize your data with interactive plots. 

    - 📊 View observer data for all wells.
    - ⚙️ Choose specific observers, adjust time units (hours, minutes, or seconds), and switch between display modes (“Individual Curves” or “Mean”).
    - 🎯 Select wells on the microplate to focus only on relevant curves.
    - 📈 Add an error band to the “Mean” plot for enhanced analysis.

    Choosing Mean calculates the average of the selected wells, and you can optionally display an error band to enrich the plot.

    ## Analysis page

    Dive deeper with advanced metrics: 

    - 🔬 Calculate growth rates and maximum absorbance values.
    - 🧮 Overlay raw data and fitted curves for precise insights.
    """

    input_specs: InputSpecs = InputSpecs(
        {'parsed_data': InputSpec(ResourceSet, human_name="Parsed Biolector XT data")})
    output_specs: OutputSpecs = OutputSpecs(
        {'streamlit_app': OutputSpec(StreamlitResource, human_name="Microplate dashboard")})

    def run(self, params: ConfigParams, inputs: TaskInputs) -> TaskOutputs:

        # build the streamlit resource with the code and the resources
        streamlit_resource = StreamlitResource()

        # set the input in the streamlit resource
        parsed_data: ResourceSet = inputs.get('parsed_data')
        streamlit_resource.add_multiple_resources([parsed_data])

        # set the app folder
        streamlit_resource.set_dashboard(AnalysisDashboardClass())

        return {'streamlit_app': streamlit_resource}
