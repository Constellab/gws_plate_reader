import os

from gws_core import (
    ConfigParams, AppConfig, AppType, OutputSpec, OutputSpecs, StreamlitResource, Task, TaskInputs, TaskOutputs,
    app_decorator, task_decorator, TypingStyle
)


@app_decorator("FermentalgStandaloneDashboard", app_type=AppType.STREAMLIT)
class FermentalgStandaloneDashboardClass(AppConfig):

    def get_app_folder_path(self):
        return os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            "_fermentalg_dashboard"
        )


@task_decorator("FermentalgStandaloneDashboard",
                human_name="Standalone Fermentalg Dashboard",
                short_description="Standalone Streamlit dashboard for Fermentalg data",
                style=TypingStyle.community_icon(icon_technical_name="dashboard", background_color="#2492FE"))
class FermentalgStandaloneDashboard(Task):
    """
    Standalone Fermentalg dashboard. No data persistence - temporary analysis only.

    This dashboard provides visualization for Fermentalg plate reader data without requiring
    permanent data storage. Perfect for quick analysis and exploration of fermentation datasets.

    The Fermentalg Dashboard is a Streamlit application designed for fermentation data visualization.
    It provides an interactive interface for interpreting QC0 data from Fermentalg experiments
    through various analytical workflows.

    The aim is to simplify the use of the Fermentalg data processing by providing an application
    that makes uploading and visualizing fermentation data easier for temporary analysis sessions.

    Features:

    - **File Upload Interface**: Upload CSV and ZIP files containing fermentation data
    - **Data Processing**: Automated processing using FermentalgLoadData task
    - **Data Quality Assessment**: Identification of missing values and incomplete datasets
    - **Interactive Selection**: Choose specific samples for detailed analysis
    - **Data Visualization**: Multiple chart types including time series, box plots, histograms, and scatter plots
    - **Statistical Analysis**: Descriptive statistics and data summaries
    - **Batch Analysis**: Compare different fermentation batches and fermentor conditions

    Required Input Files:
    - Info CSV: Contains experiment information and metadata
    - Raw Data CSV: Contains raw measurement data
    - Medium CSV: Contains medium composition information
    - Follow-up ZIP: Archive with additional time-series data

    Note: This is a standalone version that doesn't persist data between sessions.
    All uploaded files and analysis results are temporary and will be lost when the session ends.
    """

    output_specs: OutputSpecs = OutputSpecs({
        'dashboard': OutputSpec(StreamlitResource, human_name="Fermentalg Standalone Dashboard")
    })

    def run(self, params: ConfigParams, inputs: TaskInputs) -> TaskOutputs:
        """Generate and return the standalone Fermentalg Dashboard Streamlit application."""

        dashboard = StreamlitResource()
        dashboard.set_app_config_class(FermentalgStandaloneDashboardClass)

        return {"dashboard": dashboard}
