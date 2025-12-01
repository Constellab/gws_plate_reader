
from gws_core import (ConfigParams, ConfigSpecs, InputSpec, InputSpecs, OutputSpec,
                      OutputSpecs, Task, TaskInputs, TaskOutputs, task_decorator)
from gws_core import Table


@task_decorator(unique_name="FermentalgMergeFeatureMetadata",
                human_name="Merge Fermentalg Feature and Metadata Tables",
                short_description="Merges feature table with metadata table based on 'Series' column")
class FermentalgMergeFeatureMetadata(Task):

    input_specs: InputSpecs = InputSpecs({'feature_table': InputSpec(Table, human_name="Feature Table"),
                                          'metadata_table': InputSpec(Table, human_name="Metadata Table")})
    output_specs: OutputSpecs = OutputSpecs(
        {'metadata_feature_table': OutputSpec(Table, human_name="Merged Metadata and Feature Table")})
    config_specs: ConfigSpecs = ConfigSpecs({})

    def run(self, params: ConfigParams, inputs: TaskInputs) -> TaskOutputs:  # Import modules

        df_feature = inputs['feature_table'].get_data()
        df_metadata = inputs['metadata_table'].get_data()

        df_merged = df_metadata.merge(df_feature, on="Series", how="inner")

        merged_table = Table(df_merged)
        merged_table.name = "metadata_metadata_feature_table"

        # set the new table a output or the agent
        return {
            'metadata_feature_table': merged_table
        }
