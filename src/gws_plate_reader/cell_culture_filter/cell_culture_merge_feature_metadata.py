from gws_core import (
    ConfigParams,
    ConfigSpecs,
    InputSpec,
    InputSpecs,
    OutputSpec,
    OutputSpecs,
    Table,
    Task,
    TaskInputs,
    TaskOutputs,
    task_decorator,
)


@task_decorator(
    unique_name="CellCultureMergeFeatureMetadata",
    human_name="Merge Cell Culture Feature and Metadata Tables",
    short_description="Merges feature table with metadata table based on 'Series' column",
)
class CellCultureMergeFeatureMetadata(Task):
    """
    Merges feature extraction results with metadata table.

    Combines the growth curve features (from feature extraction) with the metadata
    (medium composition) based on the 'Series' column that identifies each experiment.

    Inputs:
        - feature_table: Table containing growth curve features with 'Series' column
        - metadata_table: Table containing medium composition with 'Series' column

    Outputs:
        - metadata_feature_table: Merged table containing both metadata and features

    The merge is performed as an inner join on the 'Series' column, keeping only
    rows where both feature and metadata data are available.
    """

    input_specs: InputSpecs = InputSpecs(
        {
            "feature_table": InputSpec(Table, human_name="Feature Table"),
            "metadata_table": InputSpec(Table, human_name="Metadata Table"),
        }
    )
    output_specs: OutputSpecs = OutputSpecs(
        {
            "metadata_feature_table": OutputSpec(
                Table, human_name="Merged Metadata and Feature Table"
            )
        }
    )
    config_specs: ConfigSpecs = ConfigSpecs({})

    def run(self, params: ConfigParams, inputs: TaskInputs) -> TaskOutputs:
        df_feature = inputs["feature_table"].get_data()
        df_metadata = inputs["metadata_table"].get_data()

        # Merge on Series column (inner join to keep only matching rows)
        df_merged = df_metadata.merge(df_feature, on="Series", how="inner")

        merged_table = Table(df_merged)
        merged_table.name = "metadata_feature_table"

        return {"metadata_feature_table": merged_table}
