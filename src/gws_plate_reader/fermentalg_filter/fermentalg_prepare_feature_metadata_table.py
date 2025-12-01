
from gws_core import (ConfigParams, ConfigSpecs, InputSpec, InputSpecs, OutputSpec,
                      OutputSpecs, Task, TaskInputs, TaskOutputs, task_decorator)
from gws_core.config.param.param_spec import StrParam
from gws_core.impl.table.table import Table


@task_decorator(unique_name="FermentalgPrepareFeatureMetadataTable",
                human_name="Prepare Fermentalg Feature and Metadata Tables",
                short_description="Prepares feature and metadata tables for merging by ensuring 'Series' column exists")
class FermentalgPrepareFeatureMetadataTable(Task):

    input_specs: InputSpecs = InputSpecs({'feature_metadata_table': InputSpec(Table, human_name="Feature Table")})
    output_specs: OutputSpecs = OutputSpecs(
        {'ready_feature_metadata_table': OutputSpec(Table, human_name="Prepared Feature Table")})
    config_specs: ConfigSpecs = ConfigSpecs({
        'medium_name_column':
        StrParam(
            human_name="Medium Name Column", default_value='Medium',
            short_description="Name of the column containing medium names in the metadata table",
            optional=True)})

    def run(self, params: ConfigParams, inputs: TaskInputs) -> TaskOutputs:

        df_feature_metadata = inputs['feature_metadata_table'].get_data()
        medium_name_column = params.get_value('medium_name_column', None)

        # Remove non-feature columns from feature table (non-numeric columns) except medium name column if provided
        if medium_name_column and medium_name_column in df_feature_metadata.columns:
            non_feature_columns = df_feature_metadata.select_dtypes(
                exclude=['number']).columns.tolist()
            non_feature_columns.remove(medium_name_column)
            df_feature_metadata = df_feature_metadata.drop(columns=non_feature_columns)
        else:
            df_feature_metadata = df_feature_metadata.select_dtypes(include=['number'])

        # Replace NaN values with 0
        df_feature_metadata = df_feature_metadata.fillna(0)

        ready_feature_metadata_table = Table(df_feature_metadata)

        return {
            'ready_feature_metadata_table': ready_feature_metadata_table
        }
