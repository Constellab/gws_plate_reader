
from gws_core import (ConfigParams, ConfigSpecs, InputSpec, InputSpecs, OutputSpec,
                      OutputSpecs, Task, TaskInputs, TaskOutputs, task_decorator)
from gws_core.config.param.param_spec import StrParam
from gws_core.impl.table.table import Table


@task_decorator(unique_name="CellCulturePrepareFeatureMetadataTable",
                human_name="Prepare Cell Culture Feature Metadata Table",
                short_description="Prepares merged feature-metadata table for UMAP analysis")
class CellCulturePrepareFeatureMetadataTable(Task):
    """
    Prepares the merged feature-metadata table for dimensionality reduction analysis.

    This task:
    1. Removes non-numeric columns (except the medium name column if specified)
    2. Fills NaN values with 0
    3. Keeps only the columns needed for UMAP analysis

    Inputs:
        - feature_metadata_table: Merged table from CellCultureMergeFeatureMetadata

    Outputs:
        - ready_feature_metadata_table: Cleaned table ready for UMAP

    Configuration:
        - medium_name_column: Name of the column containing medium names (will be kept for coloring in UMAP)

    The output table contains only numeric features plus the medium name column,
    making it suitable for direct input to UMAP analysis.
    """

    input_specs: InputSpecs = InputSpecs(
        {'feature_metadata_table': InputSpec(Table, human_name="Feature Metadata Table")})
    output_specs: OutputSpecs = OutputSpecs(
        {'ready_feature_metadata_table': OutputSpec(Table, human_name="Prepared Feature Metadata Table")})
    config_specs: ConfigSpecs = ConfigSpecs({
        'medium_name_column':
        StrParam(
            human_name="Medium Name Column",
            default_value='Medium',
            short_description="Name of the column containing medium names (kept for UMAP coloring)",
            optional=False)})

    def run(self, params: ConfigParams, inputs: TaskInputs) -> TaskOutputs:
        df_feature_metadata = inputs['feature_metadata_table'].get_data()
        medium_name_column = params.get_value('medium_name_column', 'Medium')

        # Remove non-numeric columns except medium name column
        if medium_name_column and medium_name_column in df_feature_metadata.columns:
            non_feature_columns = df_feature_metadata.select_dtypes(
                exclude=['number']).columns.tolist()
            # Keep the medium name column
            non_feature_columns.remove(medium_name_column)
            df_feature_metadata = df_feature_metadata.drop(columns=non_feature_columns)
        else:
            # If medium column not found or not specified, keep only numeric columns
            df_feature_metadata = df_feature_metadata.select_dtypes(include=['number'])

        # Replace NaN values with 0
        df_feature_metadata = df_feature_metadata.fillna(0)

        ready_feature_metadata_table = Table(df_feature_metadata)
        ready_feature_metadata_table.name = "ready_feature_metadata_table"

        return {
            'ready_feature_metadata_table': ready_feature_metadata_table
        }
