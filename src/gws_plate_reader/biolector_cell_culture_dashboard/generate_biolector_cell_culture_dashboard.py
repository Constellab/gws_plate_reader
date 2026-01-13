import os

from gws_core import (
    AppConfig,
    AppType,
    ConfigParams,
    OutputSpec,
    OutputSpecs,
    StreamlitResource,
    Task,
    TaskInputs,
    TaskOutputs,
    TypingStyle,
    app_decorator,
    task_decorator,
)


@app_decorator("BiolectorCellCultureDashboardAppConfig", app_type=AppType.STREAMLIT,
               human_name="Generate BiolectorXT Cell Culture Dashboard app")
class BiolectorCellCultureDashboardAppConfig(AppConfig):
    """
    Configuration class for the BiolectorXT Cell Culture Dashboard Streamlit application.

    This class defines the configuration and setup for a Streamlit-based dashboard
    that provides visualization and analysis capabilities for BiolectorXT microplate data.
    """

    def get_app_folder_path(self):
        """Get the path to the app folder relative to this file."""
        return self.get_app_folder_from_relative_path(__file__, "_biolector_cell_culture_dashboard")


@task_decorator("GenerateBiolectorCellCultureDashboard", human_name="Generate BiolectorXT Cell Culture Dashboard app",
                short_description="Create a Streamlit dashboard for BiolectorXT microplate data analysis",
                style=StreamlitResource.copy_style())
class GenerateBiolectorCellCultureDashboard(Task):
    """
    Task that generates the BiolectorXT Cell Culture Dashboard app.
    This dashboard provides visualization and analysis capabilities for BiolectorXT microplate data.

    The BiolectorXT Cell Culture Dashboard is a Streamlit application designed for fermentation data analysis
    and visualization from BiolectorXT microplate readers. It provides an interactive interface for
    processing, analyzing, and interpreting data from BiolectorXT experiments through various analytical workflows.

    The aim is to simplify the use of the BiolectorXT data processing by providing an application
    that makes uploading, processing, and visualizing microplate fermentation data easier.

    Features:

    - **File Upload Interface**: Upload BiolectorXT raw data tables, metadata folders, and optional plate layouts
    - **Data Processing**: Automated processing using BiolectorXTLoadData task
    - **Data Quality Assessment**: Identification of missing values and incomplete datasets via Venn diagrams
    - **Interactive Selection**: Choose specific wells for detailed analysis
    - **Data Visualization**: Multiple chart types including time series, box plots, histograms, and scatter plots
    - **Statistical Analysis**: Descriptive statistics and data summaries
    - **Microplate Analysis**: Support for microplate-specific recipes and workflows
    - **Metadata Extraction**: ML-ready metadata tables for feature extraction

    Required Input Files:
    - Raw Data Table: CSV file containing BiolectorXT data with Well, Filterset, Time, Cal columns
    - Metadata Folder: ZIP file containing the BXT.json metadata file
    - Plate Layout (Optional): JSON file with custom well labels and metadata

    The dashboard automatically processes uploaded files, identifies data quality issues,
    and provides an intuitive interface for selecting and visualizing specific datasets
    of interest for detailed analysis.
    """

    output_specs: OutputSpecs = OutputSpecs({
        'dashboard': OutputSpec(StreamlitResource, human_name="BiolectorXT Cell Culture Dashboard")
    })

    def run(self, params: ConfigParams, inputs: TaskInputs) -> TaskOutputs:
        """Generate and return the BiolectorXT Cell Culture Dashboard Streamlit application."""
        dashboard = StreamlitResource()
        dashboard.set_app_config(BiolectorCellCultureDashboardAppConfig())

        return {"dashboard": dashboard}

