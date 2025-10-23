import os
from gws_core import (
    ConfigParams, AppConfig, AppType, OutputSpec, OutputSpecs, StreamlitResource, Task, TaskInputs, TaskOutputs,
    app_decorator, task_decorator, TypingStyle
)


@app_decorator("FermentalgDashboardAppConfig", app_type=AppType.STREAMLIT,
               human_name="Generate Fermentalg Dashboard app")
class FermentalgDashboardAppConfig(AppConfig):
    """
    Configuration class for the Fermentalg Dashboard Streamlit application.

    This class defines the configuration and setup for a Streamlit-based dashboard
    that provides visualization and analysis capabilities for Fermentalg plate reader data.
    """

    def get_app_folder_path(self):
        """Get the path to the app folder relative to this file."""
        return self.get_app_folder_from_relative_path(__file__, "_fermentalg_dashboard")


@task_decorator("GenerateFermentalgDashboard", human_name="Generate Fermentalg Dashboard app",
                short_description="Create a Streamlit dashboard for Fermentalg data analysis",
                style=StreamlitResource.copy_style())
class GenerateFermentalgDashboard(Task):
    """
    Task that generates the Fermentalg Dashboard app.
    This dashboard provides visualization and analysis capabilities for Fermentalg plate reader data.

    The Fermentalg Dashboard is a Streamlit application designed for fermentation data analysis
    and visualization. It provides an interactive interface for processing, analyzing, and
    interpreting QC0 data from Fermentalg experiments through various analytical workflows.

    The aim is to simplify the use of the Fermentalg data processing by providing an application
    that makes uploading, processing, and visualizing fermentation data easier.

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

    The dashboard automatically processes uploaded files, identifies data quality issues,
    and provides an intuitive interface for selecting and visualizing specific datasets
    of interest for detailed analysis.
    """

    output_specs: OutputSpecs = OutputSpecs({
        'dashboard': OutputSpec(StreamlitResource, human_name="Fermentalg Dashboard")
    })

    def run(self, params: ConfigParams, inputs: TaskInputs) -> TaskOutputs:
        """Generate and return the Fermentalg Dashboard Streamlit application."""

        dashboard = StreamlitResource()
        dashboard.set_app_config(FermentalgDashboardAppConfig())

        return {"dashboard": dashboard}
