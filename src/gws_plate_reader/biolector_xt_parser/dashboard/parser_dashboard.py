
import os

from gws_core import (ConfigParams, Dashboard, DashboardType, Folder,
                      InputSpec, InputSpecs, OutputSpec, OutputSpecs,
                      StreamlitResource, Table, Task, TaskInputs, TaskOutputs,
                      TypingStyle, dashboard_decorator, task_decorator)


@dashboard_decorator("ParserDashboard", dashboard_type=DashboardType.STREAMLIT)
class ParserDashboardClass(Dashboard):

    # retrieve the path of the app folder, relative to this file
    # the dashboard code folder starts with a underscore to avoid being loaded when the brick is loaded
    def get_folder_path(self):
        return os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            "_dashboard_parser_code"
        )


@task_decorator("StreamlitGeneratorVisualisation", human_name="Generate dashboard to visualise data from BiolectorXT",
                short_description="Task to generate a custom Streamlit dashboard to visualise data from BiolectorXT",
                style=TypingStyle.community_icon(icon_technical_name="dashboard", background_color="#c3fa7f"))
class ParserDashboard(Task):
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
        {'raw_data': InputSpec(Table, human_name="Table containing the raw data"),
         'folder_metadata': InputSpec(Folder, human_name="Folder containing the metadata")})
    output_specs: OutputSpecs = OutputSpecs(
        {'streamlit_app': OutputSpec(StreamlitResource, human_name="Microplate dashboard")})

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
        streamlit_resource.set_dashboard(ParserDashboardClass())

        return {'streamlit_app': streamlit_resource}
