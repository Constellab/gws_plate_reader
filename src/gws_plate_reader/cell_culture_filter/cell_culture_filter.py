from gws_core import (InputSpec, OutputSpec, InputSpecs, OutputSpecs, Table, ListParam, Tag,
                      TypingStyle, ResourceSet, Task, task_decorator, ConfigSpecs, ConfigParams)
from typing import Dict, Any, List
import json


BATCH_TAG_KEY = "batch"
SAMPLE_TAG_KEY = "sample"


@task_decorator("FilterFermentorAnalyseLoadedResourceSetBySelection",
                human_name="Filter Cell Culture ResourceSet by Selection",
                short_description="Filter cell culture data by selecting specific batch/sample combinations",
                style=TypingStyle.community_icon(icon_technical_name="filter", background_color="#28a745"))
class FilterFermentorAnalyseLoadedResourceSetBySelection(Task):
    """
    Filter fermentation data ResourceSet by selecting specific batch/sample combinations.

    ## Overview
    This task enables selective analysis by filtering a ResourceSet to include only
    specific batch/sample combinations. It works seamlessly with the output from
    CellCultureLoadData task and preserves all tags and metadata.

    ## Purpose
    - Select specific fermenters and experiments for focused analysis
    - Remove incomplete or problematic samples from analysis
    - Create subsets for comparative studies (e.g., different media, conditions)
    - Reduce dataset size for faster processing and visualization

    ## How It Works

    ### Input Requirements
    - **ResourceSet**: Output from CellCultureLoadData containing Tables with tags
    - **Selection Criteria**: List of batch/sample pairs to include

    ### Tag-Based Filtering
    Each Table in the ResourceSet is examined for two required tags:
    - `batch`: Experiment/trial identifier (e.g., "EPA-WP3-25-001")
    - `sample`: Fermenter identifier (e.g., "23A", "23B")

    Only Tables matching the selection criteria are included in the output.

    ### Filtering Process
    1. Parses selection criteria (JSON format or dict)
    2. Creates fast lookup set for O(1) matching
    3. Iterates through all resources in input ResourceSet
    4. For each Table resource:
       - Extracts 'batch' and 'sample' tag values
       - Checks if pair exists in selection criteria
       - Includes resource in output if matched
       - Logs warning if resource missing required tags
    5. Returns filtered ResourceSet with only selected samples

    ## Configuration

    ### Selection Criteria Format
    The `selection_criteria` parameter accepts a list of dictionaries or JSON strings:

    #### Python Format
    ```python
    [
        {'batch': 'EPA-WP3-25-001', 'sample': '23A'},
        {'batch': 'EPA-WP3-25-001', 'sample': '23B'},
        {'batch': 'EPA-WP3-25-002', 'sample': '23A'},
    ]
    ```

    #### JSON Format
    ```json
    [
        {"batch": "EPA-WP3-25-001", "sample": "23A"},
        {"batch": "EPA-WP3-25-001", "sample": "23B"},
        {"batch": "EPA-WP3-25-002", "sample": "23A"}
    ]
    ```

    #### Alternative Format (with couple keys)
    ```python
    {
        'couple0': {'batch': 'batch01', 'sample': 'A1'},
        'couple1': {'batch': 'batch01', 'sample': 'B1'},
        'couple2': {'batch': 'batch02', 'sample': 'A1'}
    }
    ```

    ## Input Specifications

    ### resource_set (ResourceSet)
    - **Source**: Typically from CellCultureLoadData task
    - **Requirements**:
      - Must contain Table resources
      - Each Table must have 'batch' and 'sample' tags
      - Tags are case-sensitive
    - **Example Structure**:
      ```
      ResourceSet {
        "EPA-WP3-25-001_23A": Table [tags: batch=EPA-WP3-25-001, sample=23A, medium=M1]
        "EPA-WP3-25-001_23B": Table [tags: batch=EPA-WP3-25-001, sample=23B, medium=M1]
        "EPA-WP3-25-002_23A": Table [tags: batch=EPA-WP3-25-002, sample=23A, medium=M2]
      }
      ```

    ## Output Specifications

    ### filtered_resource_set (ResourceSet)
    - **Contents**: Only Tables matching selection criteria
    - **Preservation**:
      - All original columns preserved
      - All tags preserved (batch, sample, medium, missing_value, etc.)
      - Column tags preserved (is_index_column, is_data_column, unit)
      - Table names preserved
    - **Example**: If selecting 2 out of 10 samples, output contains 2 Tables

    ## Behavior Details

    ### Matching Logic
    - **Exact Match**: Tag values must match exactly (case-sensitive)
    - **Both Tags Required**: Resources missing either tag are excluded with warning
    - **Non-Table Resources**: Ignored (only Table resources are processed)
    - **Duplicate Prevention**: Same resource won't be added multiple times

    ### Error Handling
    - **Missing Tags**: Logs warning and skips resource
    - **Invalid JSON**: Attempts to parse as dict, logs error if fails
    - **Empty Selection**: Returns empty ResourceSet (valid but unusual)
    - **No Matches**: Returns empty ResourceSet with info message

    ## Use Cases

    ### 1. Quality-Based Filtering
    ```
    CellCultureLoadData → View Venn Diagram →
    Select only complete samples → Filter → Analysis
    ```

    ### 2. Comparative Analysis
    ```
    Select samples from Medium A → Filter → Analyze
    Select samples from Medium B → Filter → Analyze
    Compare results
    ```

    ### 3. Time-Period Selection
    ```
    Select experiments from specific date range →
    Filter by batch names → Analysis
    ```

    ### 4. Fermenter Comparison
    ```
    Select same experiment across different fermenters →
    Filter → Compare performance
    ```

    ## Integration with CellCulture Dashboard

    The dashboard provides an interactive interface:
    1. **Overview Step**: View all samples in table
    2. **Selection Step**:
       - Click rows to select samples
       - See batch/sample/medium information
       - Preview selection count
    3. **Automatic Filtering**: Dashboard creates and runs filter scenario
    4. **Visualization**: View filtered data in graphs and tables

    ## Example Workflow

    ```
    [ResourceSet with 50 samples]
          ↓
    [Select 10 samples of interest]
          ↓
    FilterFermentorAnalyseLoadedResourceSetBySelection
          ↓
    [Filtered ResourceSet with 10 samples]
          ↓
    [Interpolation / Visualization / Export]
    ```

    ## Performance Notes

    - **Fast Lookup**: Uses set-based matching for O(1) complexity
    - **Memory Efficient**: Only copies selected resources, not all data
    - **Scalable**: Handles hundreds of samples efficiently
    - **No Data Copy**: References original Table objects (metadata preserved)

    ## Tips and Best Practices

    1. **Check Data First**: View overview and Venn diagram before filtering
    2. **Use Dashboard**: Interactive selection is easier than manual JSON
    3. **Save Selection**: Document selected samples for reproducibility
    4. **Verify Output**: Check filtered count matches expected selection
    5. **Chain Operations**: Filter → Interpolate → Visualize for complete workflow

    ## Troubleshooting

    | Issue | Cause | Solution |
    |-------|-------|----------|
    | Empty output | No matches found | Verify tag values are exact (case-sensitive) |
    | Missing samples | Tags not set | Check input from CellCultureLoadData |
    | Warning messages | Resources missing tags | Review input data quality |
    | JSON parse error | Invalid format | Use list of dicts or valid JSON string |

    ## Notes

    - Designed specifically for CellCulture workflow (follows CellCultureLoadData)
    - Preserves complete data integrity (no data modification)
    - Tag keys ('batch', 'sample') are hardcoded constants for consistency
    - Output can be used directly with CellCultureSubsampling task
    - Compatible with Streamlit dashboard for interactive use
    """

    input_specs: InputSpecs = InputSpecs({
        'resource_set': InputSpec(ResourceSet,
                                  human_name="Input ResourceSet to filter",
                                  short_description="ResourceSet from CellCultureLoadData containing batch/sample tagged resources",
                                  optional=False),
    })

    output_specs: OutputSpecs = OutputSpecs({
        'filtered_resource_set': OutputSpec(ResourceSet,
                                            human_name="Filtered ResourceSet",
                                            short_description="ResourceSet containing only selected batch/sample combinations")
    })

    config_specs = ConfigSpecs({
        'selection_criteria': ListParam(
            human_name="Selection criteria with Batch/Sample pairs",
            short_description="List of dictionaries with 'batch' and 'sample' keys for filtering",
            optional=False
        )
    })

    def run(self, params: ConfigParams, inputs) -> Dict[str, Any]:
        resource_set: ResourceSet = inputs['resource_set']
        selection_criteria: List[Dict[str, str]] = params.get_value('selection_criteria')

        self.log_info_message(
            f"Filtering ResourceSet with {len(selection_criteria)} selected batch/sample combinations")

        # Create a new ResourceSet for filtered data
        filtered_res = ResourceSet()

        # Create selection criteria set for faster lookup
        selection_set = set()
        for criteria in selection_criteria:
            if type(criteria) != dict and type(criteria) == str:
                criteria = json.loads(criteria)
            batch = criteria.get(BATCH_TAG_KEY, '')
            sample_name = criteria.get(SAMPLE_TAG_KEY, '')
            selection_set.add((batch, sample_name))

        self.log_info_message(f"Selection criteria: {selection_set}")

        matched_count = 0
        total_resources = len(resource_set.get_resources())

        # Filter each resource in the ResourceSet based on tags
        for resource_name, resource in resource_set.get_resources().items():

            if not isinstance(resource, Table):
                self.log_debug_message(
                    f"⏭️ Skipping non-Table resource '{resource_name}'")
                continue

            if not resource.tags:
                self.log_warning_message(
                    f"⚠️ Resource '{resource_name}' has no tags and will be skipped")
                continue

            # Check if this resource matches any of the selected Batch/Sample pairs
            # by examining its tags
            should_include = False

            if resource.tags:
                batch_tag_value = None
                sample_tag_value = None

                # Extract Batch and Sample values from resource tags
                for tag in resource.tags.get_tags():
                    if tag.key == BATCH_TAG_KEY:
                        batch_tag_value = tag.value
                    elif tag.key == SAMPLE_TAG_KEY:
                        sample_tag_value = tag.value

                # Check if this resource's batch/sample combination matches selection criteria
                if batch_tag_value and sample_tag_value:
                    if (batch_tag_value, sample_tag_value) in selection_set:
                        should_include = True
                        self.log_info_message(
                            f"✅ Including resource '{resource_name}' - batch: '{batch_tag_value}', sample: '{sample_tag_value}'")
                    else:
                        self.log_debug_message(
                            f"⏭️ Skipping resource '{resource_name}' - batch: '{batch_tag_value}', sample: '{sample_tag_value}' not in selection")
                else:
                    self.log_warning_message(
                        f"⚠️ Resource '{resource_name}' missing required tags - batch: {batch_tag_value}, sample: {sample_tag_value}")

            # If this resource should be included, add it to filtered ResourceSet
            if should_include:
                # Create a copy of the resource to preserve all tags and properties
                filtered_table = Table(resource.get_data().copy())
                filtered_table.name = resource.name

                # Copy all original tags to ensure they are preserved
                if resource.tags:
                    for tag in resource.tags.get_tags():
                        filtered_table.tags.add_tag(Tag(key=tag.key, value=tag.value))

                for column_name in resource.get_column_names():
                    col_tags: Dict[str, str] = resource.get_column_tags_by_name(column_name)
                    for col_tag_key, col_tag_value in col_tags.items():
                        filtered_table.add_column_tag_by_name(column_name, col_tag_key, col_tag_value)

                # Add the filtered resource with preserved tags
                filtered_res.add_resource(filtered_table, resource_name)
                matched_count += 1

        self.log_success_message(f"Filtered {matched_count}/{total_resources} resources based on selection criteria")

        if matched_count == 0:
            self.log_warning_message(
                "No resources matched the selection criteria. Check that resources have proper 'batch' and 'sample' tags.")

        return {'filtered_resource_set': filtered_res}
