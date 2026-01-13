import json
import os
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from gws_core import (
    ConfigParams,
    ConfigSpecs,
    DictParam,
    DynamicInputs,
    Folder,
    InputSpec,
    InputSpecs,
    ListParam,
    OutputSpec,
    OutputSpecs,
    PlotlyResource,
    ResourceSet,
    Table,
    Task,
    TaskInputs,
    TaskOutputs,
    TypingStyle,
    task_decorator,
)
from gws_core.resource.resource_set.resource_list import ResourceList
from gws_core.tag.tag import Tag, TagOrigins
from gws_core.tag.tag_dto import TagOriginType
from gws_core.tag.tag_key_model import TagKeyModel
from gws_core.user.current_user_service import CurrentUserService
from pandas import NA, DataFrame, Series

DOWNLOAD_TAG_KEY = "biolector_download"


def create_venn_diagram_wells(well_sets: dict[str, set[str]]) -> go.Figure:
    """
    Create a Venn diagram showing data availability across wells.

    Args:
        well_sets: Dict with sets of well identifiers for each data type
            Keys: 'cultivation_labels', 'medium_info' (optional), 'raw_data'
            Values: Set of well identifiers (e.g., 'A01', 'B02')

    Returns:
        Plotly Figure with the Venn diagram showing well data completeness
    """

    # Extract sets
    A = well_sets.get('cultivation_labels', set())  # CultivationLabels from metadata
    B = well_sets.get('medium_info', set())  # Wells in medium_info (info_table)
    C = well_sets.get('raw_data', set())  # Wells with raw_data

    # Check if we have medium_info (3 circles) or not (2 circles)
    has_medium_info = 'medium_info' in well_sets and len(B) > 0

    if not has_medium_info:
        # 2-circle Venn diagram (cultivation_labels and raw_data only)
        only_A = len(A - C)  # Only CultivationLabels
        only_C = len(C - A)  # Only raw_data
        A_and_C = len(A & C)  # Both (complete wells)

        fig = go.Figure()

        # Circle parameters for 2 circles
        radius = 0.3
        Ax, Ay = 0.4, 0.5   # CultivationLabels (left)
        Cx, Cy = 0.6, 0.5   # raw_data (right)

        # Create circles
        theta = np.linspace(0, 2 * np.pi, 100)

        # Circle A - CultivationLabels (Blue)
        x_A = radius * np.cos(theta) + Ax
        y_A = radius * np.sin(theta) + Ay
        fig.add_trace(go.Scatter(
            x=x_A, y=y_A,
            fill='toself',
            fillcolor='rgba(33, 150, 243, 0.3)',
            line=dict(color='rgba(33, 150, 243, 0.8)', width=3),
            name='CultivationLabels',
            mode='lines',
            hoverinfo='skip',
            showlegend=False
        ))

        # Circle C - raw_data (Orange)
        x_C = radius * np.cos(theta) + Cx
        y_C = radius * np.sin(theta) + Cy
        fig.add_trace(go.Scatter(
            x=x_C, y=y_C,
            fill='toself',
            fillcolor='rgba(255, 152, 0, 0.3)',
            line=dict(color='rgba(255, 152, 0, 0.8)', width=3),
            name='raw_data',
            mode='lines',
            hoverinfo='skip',
            showlegend=False
        ))

        # Add titles
        fig.add_annotation(x=Ax, y=Ay + radius + 0.08, text="<b>CultivationLabels</b>",
                          showarrow=False, font=dict(size=14))
        fig.add_annotation(x=Cx, y=Cy + radius + 0.08, text="<b>raw_data</b>",
                          showarrow=False, font=dict(size=14))

        # Add counts
        fig.add_annotation(x=Ax - 0.15, y=Ay, text=str(only_A),
                          showarrow=False, font=dict(size=14))
        fig.add_annotation(x=Cx + 0.15, y=Cy, text=str(only_C),
                          showarrow=False, font=dict(size=14))
        fig.add_annotation(
            x=(Ax + Cx) / 2, y=Ay,
            text=f"<b>{A_and_C}</b>",
            showarrow=False,
            font=dict(size=16, color='darkgreen'),
            bgcolor='rgba(255, 255, 255, 0.9)',
            borderpad=4,
            bordercolor='darkgreen',
            borderwidth=2
        )

        # Update layout
        fig.update_layout(
            title="Well Data Availability - Venn Diagram (CultivationLabels, raw_data)",
            showlegend=False,
            xaxis=dict(showticklabels=False, showgrid=False, zeroline=False, range=[0, 1]),
            yaxis=dict(
                showticklabels=False, showgrid=False, zeroline=False, range=[0.1, 0.9],
                scaleanchor="x", scaleratio=1),
            height=600, width=600,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
        )

        return fig

    # 3-circle Venn diagram (original code for when medium_info is present)
    only_A = len(A - B - C)  # Only CultivationLabels
    only_B = len(B - A - C)  # Only medium_info
    only_C = len(C - A - B)  # Only raw_data
    A_and_B = len((A & B) - C)  # CultivationLabels ∩ medium_info (excluding raw_data)
    A_and_C = len((A & C) - B)  # CultivationLabels ∩ raw_data (excluding medium_info)
    B_and_C = len((B & C) - A)  # medium_info ∩ raw_data (excluding CultivationLabels)
    A_and_B_and_C = len(A & B & C)  # All three (complete wells - no missing_value)

    # Create figure
    fig = go.Figure()

    # Circle parameters
    radius = 0.28
    Ax, Ay = 0.5, 0.72   # CultivationLabels (top)
    Bx, By = 0.35, 0.5   # medium_info (left)
    Cx, Cy = 0.65, 0.5   # raw_data (right)

    # Create circles using parametric equations
    theta = np.linspace(0, 2 * np.pi, 100)

    # Circle A - CultivationLabels (Blue)
    x_A = radius * np.cos(theta) + Ax
    y_A = radius * np.sin(theta) + Ay
    fig.add_trace(go.Scatter(
        x=x_A, y=y_A,
        fill='toself',
        fillcolor='rgba(33, 150, 243, 0.3)',
        line=dict(color='rgba(33, 150, 243, 0.8)', width=3),
        name='CultivationLabels',
        mode='lines',
        hoverinfo='skip',
        showlegend=False
    ))

    # Circle B - medium_info (Green)
    x_B = radius * np.cos(theta) + Bx
    y_B = radius * np.sin(theta) + By
    fig.add_trace(go.Scatter(
        x=x_B, y=y_B,
        fill='toself',
        fillcolor='rgba(76, 175, 80, 0.3)',
        line=dict(color='rgba(76, 175, 80, 0.8)', width=3),
        name='medium_info',
        mode='lines',
        hoverinfo='skip',
        showlegend=False
    ))

    # Circle C - raw_data (Orange)
    x_C = radius * np.cos(theta) + Cx
    y_C = radius * np.sin(theta) + Cy
    fig.add_trace(go.Scatter(
        x=x_C, y=y_C,
        fill='toself',
        fillcolor='rgba(255, 152, 0, 0.3)',
        line=dict(color='rgba(255, 152, 0, 0.8)', width=3),
        name='raw_data',
        mode='lines',
        hoverinfo='skip',
        showlegend=False
    ))

    # Add titles near the top of each circle
    fig.add_annotation(x=Ax, y=Ay + radius + 0.05, text="<b>CultivationLabels</b>",
                       showarrow=False, font=dict(size=14))
    fig.add_annotation(x=Bx, y=By + radius + 0.05, text="<b>medium_info</b>",
                       showarrow=False, font=dict(size=14))
    fig.add_annotation(x=Cx, y=Cy + radius + 0.05, text="<b>raw_data</b>",
                       showarrow=False, font=dict(size=14))

    # Add region counts
    fig.add_annotation(x=Ax, y=Ay + 0.18, text=str(only_A),
                       showarrow=False, font=dict(size=14))
    fig.add_annotation(x=Bx - 0.13, y=By, text=str(only_B),
                       showarrow=False, font=dict(size=14))
    fig.add_annotation(x=Cx + 0.13, y=Cy, text=str(only_C),
                       showarrow=False, font=dict(size=14))
    fig.add_annotation(x=Ax - 0.07, y=Ay + 0.1, text=str(A_and_B),
                       showarrow=False, font=dict(size=14))
    fig.add_annotation(x=Ax + 0.07, y=Ay + 0.1, text=str(A_and_C),
                       showarrow=False, font=dict(size=14))
    fig.add_annotation(x=(Bx + Cx) / 2, y=By - 0.08, text=str(B_and_C),
                       showarrow=False, font=dict(size=14))
    fig.add_annotation(
        x=Ax, y=By + 0.1,
        text=f"<b>{A_and_B_and_C}</b>",
        showarrow=False,
        font=dict(size=16, color='darkgreen'),
        bgcolor='rgba(255, 255, 255, 0.9)',
        borderpad=4,
        bordercolor='darkgreen',
        borderwidth=2
    )

    # Update layout
    fig.update_layout(
        title="Well Data Availability - Venn Diagram (CultivationLabels, medium_info, raw_data)",
        showlegend=False,
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False, range=[0, 1]),
        yaxis=dict(
            showticklabels=False, showgrid=False, zeroline=False, range=[0.2, 1.05],
            scaleanchor="x", scaleratio=1),
        height=600, width=600,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )

    return fig


@task_decorator("BiolectorXTLoadData", human_name="BiolectorXT Load Data",
                short_description="Load and process BiolectorXT data with quality control visualization",
                style=TypingStyle.community_icon(icon_technical_name="file-upload", background_color="#c3fa7f"))
class BiolectorXTLoadData(Task):
    """
    [Generated by Task Expert Agent]

    Load and process BiolectorXT data from raw measurements and metadata files.

    ## Overview
    This task integrates BiolectorXT data from raw measurements and metadata to create a comprehensive dataset
    for microplate analysis. It handles data parsing, well labeling, quality control visualization,
    and generates statistics about data completeness.

    ## Input Files Required

    ### 1. Raw Data Table (`raw_data`)
    Table containing raw measurement data from BiolectorXT with columns:
    - `Well`: Well identifier (e.g., "A01", "B02")
    - `Filterset`: Filter/channel name (e.g., "Biomass", "pH", "DO")
    - `Time`: Measurement time in seconds
    - `Cal`: Calibrated measurement value
    - Additional metadata columns may be present

    ### 2. Metadata Folder (`folder_metadata`)
    Folder containing JSON metadata file(s) ending with 'BXT.json':
    - **Channels**: List of measurement channels/filters
    - **Microplate**: Well configuration
      - `CultivationLabels`: Wells used for cultivation
      - `ReservoirLabels`: Wells used as reservoirs
    - **Layout**: Well label descriptions
      - `CultivationLabelDescriptionsMap`: Descriptions for cultivation wells
      - `ReservoirLabelDescriptionsMap`: Descriptions for reservoir wells
    - **Comment**: Experiment comment/description
    - **Name**: Experiment name
    - **UserName**: User who created the experiment
    - **LastModifiedAt**: Last modification date

    ### 3. Plate Layout (Optional) (`plate_layout`)
    JSONDict containing custom well labels and additional metadata:
    - Keys: Well identifiers (e.g., "A1", "A01")
    - Values: Dict with `label` key and optional additional metadata
    - Overrides metadata labels if provided

    ## Processing Steps

    1. **Metadata Extraction**: Reads BXT.json file from metadata folder
    2. **Data Parsing**: Transforms raw data from long to wide format
       - Groups by Filterset to separate different measurement channels
       - Creates intermediate tables with wells as columns
       - Handles both microfluidics (C01-F08) and standard (A01-F08) layouts
    3. **Data Restructuring**: Pivots data to create one table per well
       - Each table contains time column and all measurement channels
       - Filters out wells with no data (all NaN)
    4. **Well Labeling**: Merges labels from metadata and optional plate layout
    5. **Quality Control**: Tracks well data availability
       - Cultivation wells
       - Reservoir wells
       - Labeled wells
    6. **Tagging**: Adds comprehensive tags from metadata
       - Batch (experiment/plate name) and sample (well ID)
       - Experiment name, comment, user, date
       - Raw data source
       - Well-specific labels and metadata
    6. **Statistics**: Generates metadata summary table with well counts

    ## Outputs

    ### 1. Parsed Data Tables (`parsed_data_tables`)
    A ResourceSet containing one Table per well (batch/sample combination):
    - **Table Name**: Well identifier (e.g., "A01", "B02", "C03")
    - **Columns**:
      - `Temps_en_h`: Time in hours
      - One column per measurement channel (e.g., "Biomass", "pH", "pO2", "DO")
    - **Resource Tags**:
      - `batch`: Experiment/plate name (from metadata Name field)
      - `sample`: Well identifier (e.g., "A01")
      - `label`: Well label/description (if available)
      - `comment`: Experiment comment
      - `name`: Experiment name
      - `user_name`: User who created the experiment
      - `date`: Last modification date
      - `raw_data`: Raw data table name
      - `biolector_download`: Download tag (if present in raw data)
      - Additional custom metadata from plate_layout

    ### 2. Venn Diagram (`venn_diagram`) - Optional
    A PlotlyResource containing an interactive Venn diagram showing:
    - **3 Overlapping Circles**: Cultivation, Reservoir, Labeled
    - **Circle Labels**: Show count of wells in each category
    - **Center Label**: Shows count of fully characterized wells (all 3 categories)
    - **Color Coding**:
      - Blue: Cultivation wells
      - Green: Reservoir wells
      - Purple: Labeled wells

    ### 3. Metadata Summary Table (`metadata_summary`) - Optional
    A Table containing experiment-level statistics:
    - **Columns**:
      - `metric`: Metric name
      - `value`: Metric value
    - **Metrics**:
      - Total channels/filters
      - Total wells
      - Cultivation wells count
      - Reservoir wells count
      - Labeled wells count
      - Experiment name
      - User name
      - Comment
      - Last modified date

    ## Data Quality

    ### Well Type Detection
    The task automatically identifies:
    - **Cultivation wells**: From metadata CultivationLabels
    - **Reservoir wells**: From metadata ReservoirLabels
    - **Labeled wells**: Wells with non-empty labels from metadata or plate layout

    ### Microfluidics Detection
    Automatically detects microfluidics mode:
    - Checks if "A01" is present in well identifiers
    - If not present: Microfluidics mode (C01-F08 wells)
    - If present: Standard mode (A01-F08 wells)

    ## Use Cases

    1. **Quality Control**: Use Venn diagram to assess well labeling completeness
    2. **Data Exploration**: Browse parsed data with proper well labels
    3. **Batch Processing**: Process multiple experiments with consistent structure
    4. **Dashboard Preparation**: Provides clean, tagged data ready for visualization
    5. **Downstream Analysis**: Standardized format for filtering, analysis tasks

    ## Example Workflow

    ```
    [BiolectorXT Download] ──┬──> [Raw Table]
                             └──> [Metadata Folder]
                                      │
                                      │
    [Plate Layout JSON] ─────────────┼──> BiolectorXTLoadData ──┬──> [Well Tables] ──> Filter/Analysis
                                                                  ├──> [Venn Diagram] ──> QC Report
                                                                  └──> [Metadata Summary] ──> Stats
    ```

    ## Example Output Structure

    For a plate with 3 wells (A01, A02, B01) and 2 measurements (Biomass, pH):
    ```
    ResourceSet containing 3 tables:

    Table "A01":
      Temps_en_h | Biomass | pH
      0.0        | 0.123   | 7.2
      0.5        | 0.156   | 7.1
      1.0        | 0.198   | 7.0

    Table "A02":
      Temps_en_h | Biomass | pH
      0.0        | 0.115   | 7.3
      0.5        | 0.142   | 7.2
      ...
    ```

    ## Notes

    - All JSON files must be UTF-8 encoded
    - Metadata file must end with 'BXT.json'
    - Well identifiers are normalized (e.g., "A1" → "A01")
    - Wells with no data (all NaN) are excluded from the output
    - Time is provided in hours (Temps_en_h)
    - Each table represents one well with all its measurements
    - Output format is compatible with filtering and analysis tasks
    - Plate layout overrides metadata labels when provided
    - Tags include batch (experiment name) and sample (well ID) for easy filtering

    ## Comparison with BiolectorXTDataParser

    This task differs from BiolectorXTDataParser:
    - **Different output structure**: One table per well instead of one table per channel
    - **Added features**:
      - Venn diagram for data availability visualization
      - Metadata summary table with experiment statistics
      - Batch/sample tagging for consistent data organization
    - **Enhanced documentation** with usage examples
    - **Consistent naming** with other load tasks (e.g., FermentalgLoadData)
    """

    input_specs: InputSpecs = DynamicInputs(
        default_specs={
            'medium_table': InputSpec(
                Table,
                human_name="Medium composition table",
                short_description="Table with medium compositions (Medium, Component1, Component2, ...)",
                optional=True
            )
        },
        additionnal_port_spec=InputSpec(
            ResourceSet,
            human_name="Plate data (raw_data, folder_metadata, info_table)",
            short_description="ResourceSet containing: raw_data (Table), folder_metadata (Folder), info_table (Table)"
        )
    )

    config_specs: ConfigSpecs = ConfigSpecs({
        'plate_names': ListParam(
            human_name="Plate names",
            short_description="Custom names for each plate. Leave empty to use default names (plate_0, plate_1, etc.). Must match the number of input plates if provided.",
            optional=True,
            default_value=[]
        )
    })

    output_specs: OutputSpecs = OutputSpecs({
        'resource_set': OutputSpec(
            ResourceSet,
            human_name="Parsed data tables resource set",
            short_description="One table per well with all measurement channels as columns",
            sub_class=True
        ),
        'venn_diagram': OutputSpec(
            PlotlyResource,
            human_name="Venn diagram of well data availability",
            short_description="Visual representation of cultivation, reservoir, and labeled wells",
            optional=True
        ),
        'metadata_table': OutputSpec(
            Table,
            human_name="Metadata table for ML",
            short_description="Table with well metadata for feature extraction",
            optional=True
        ),
        'medium_table': OutputSpec(
            Table,
            human_name="Medium composition table",
            short_description="Table with unique medium compositions (output when medium_table provided as input)",
            optional=True
        )
    })

    def is_micro_fluidics(self, data: DataFrame) -> bool:
        """
        Check if the data is from a microfluidics experiment.

        :param data: Raw data DataFrame
        :return: True if microfluidics, False otherwise
        """
        unique_wells = data['Well'].dropna().unique()
        if "A01" in unique_wells:
            return False
        return True

    def get_filters(self, metadata: dict) -> list[str]:
        """
        Get the list of measurement filters/channels from metadata.

        :param metadata: Metadata dictionary
        :return: List of filter names
        """
        filters = []
        for channel in metadata.get('Channels', []):
            filters.append(channel['Name'])
        return filters

    def parse_data(self, data: DataFrame, metadata: dict) -> dict[str, DataFrame]:
        """
        Parse the raw data from BiolectorXT into wide format tables.

        :param data: Raw data DataFrame
        :param metadata: Metadata dictionary
        :return: Dictionary mapping filter names to parsed DataFrames
        """

        is_micro_fluidics: bool = self.is_micro_fluidics(data)
        filters: list[str] = self.get_filters(metadata)

        # Sort and filter data
        row_data = data.sort_values(by=['Filterset', 'Well'])
        reduced_data = row_data[["Well", "Filterset", "Time", "Cal"]]
        unique_values = reduced_data['Filterset'].dropna().unique()

        df_filter_dict: dict[str, DataFrame] = {}

        for i, value in enumerate(unique_values):
            df_filter = reduced_data[reduced_data['Filterset'] == value]
            df_filter = df_filter.sort_values(by=['Well', 'Time'])
            df_filter = df_filter.drop(columns="Filterset")

            # Determine well range based on microfluidics mode
            if is_micro_fluidics:
                columns_to_add = [f"{chr(letter)}{str(num).zfill(2)}"
                                  for letter in range(ord('C'), ord('F') + 1)
                                  for num in range(1, 9)]
            else:
                columns_to_add = [f"{chr(letter)}{str(num).zfill(2)}"
                                  for letter in range(ord('A'), ord('F') + 1)
                                  for num in range(1, 9)]

            # Add columns for time and wells
            df_filter = df_filter.assign(time=NA, Temps_en_h=NA, **{col: NA for col in columns_to_add})

            # Fill time columns
            df_filter["time"] = df_filter.loc[df_filter['Well'] == columns_to_add[0], 'Time']
            df_filter["Temps_en_h"] = df_filter["time"] / 3600

            # Populate well columns
            for name_col in columns_to_add:
                df_filter[name_col] = df_filter.loc[df_filter['Well'] == name_col, 'Cal']

            # Shift values up to remove NaN rows
            columns_to_process = df_filter.columns[3:len(df_filter.columns)]
            df_filter = df_filter.reset_index(drop=True)

            for col in columns_to_process:
                df_filter[col] = Series(df_filter[col].dropna().values)

            # Clean up
            df_filter = df_filter.dropna(subset=['time'])
            df_filter = df_filter.drop(columns=["Well", "Time", "Cal"])

            # Add to dictionary
            if i < len(filters):
                filter_name = filters[i]
                df_filter_dict[filter_name] = df_filter

        return df_filter_dict

    def get_wells_cultivation(self, metadata: dict) -> list[str]:
        """Get cultivation wells from metadata."""
        microplate = metadata.get("Microplate", {})
        return microplate.get("CultivationLabels", [])

    def get_wells_reservoir(self, metadata: dict) -> list[str]:
        """Get reservoir wells from metadata."""
        microplate = metadata.get("Microplate", {})
        return microplate.get("ReservoirLabels", [])

    def get_wells(self, metadata: dict) -> list[str]:
        """Get all wells (cultivation + reservoir) from metadata."""
        wells = []
        wells.extend(self.get_wells_cultivation(metadata))
        wells.extend(self.get_wells_reservoir(metadata))
        return wells

    def get_wells_label_description(
            self, metadata: dict, existing_plate_layout: dict | None = None) -> dict[str, Any]:
        """
        Get well labels and descriptions from metadata and optional plate layout.

        :param metadata: Metadata dictionary
        :param existing_plate_layout: Optional plate layout override
        :return: Dictionary mapping well IDs to their metadata
        """
        # Create all possible wells A01 to F08
        wells = [f"{chr(letter)}{str(num).zfill(2)}"
                 for letter in range(ord('A'), ord('F') + 1)
                 for num in range(1, 9)]
        wells_label = {well: {"label": ""} for well in wells}

        # Get labels from metadata
        microplate = metadata.get("Layout", {})
        cultivation_map = microplate.get("CultivationLabelDescriptionsMap", {})
        reservoir_map = microplate.get("ReservoirLabelDescriptionsMap", {})

        for well, description in cultivation_map.items():
            if well in wells_label:
                wells_label[well] = {"label": description.strip() or wells_label[well]}

        for well, description in reservoir_map.items():
            if well in wells_label:
                wells_label[well] = {"label": description.strip() or wells_label[well]}

        # Override with plate layout if provided
        if existing_plate_layout:
            for well, data in existing_plate_layout.items():
                # Normalize well ID (A1 → A01)
                if len(well) == 2:
                    well = f"{well[0]}0{well[1]}"
                if well in wells_label and isinstance(data, dict):
                    existing_data = wells_label[well] if isinstance(wells_label[well], dict) else {
                        "label": wells_label[well]}
                    if "label" in data:
                        existing_data["label"] = data["label"]
                    existing_data.update(data)
                    wells_label[well] = existing_data

        return wells_label

    def create_parsed_resource_set(
            self, data: DataFrame, metadata: dict,
            existing_plate_layout: dict | None = None,
            medium_table: Table | None = None,
            info_table: Table | None = None,
            plate_name: str = "plate_0") -> ResourceSet:
        """
        Create a ResourceSet from parsed data with proper tagging.

        Creates one table per well (batch/sample combination) with all measurements as columns.

        :param data: Raw data DataFrame
        :param metadata: Metadata dictionary
        :param existing_plate_layout: Optional plate layout override
        :param medium_table: Optional table with medium compositions
        :param info_table: Optional table mapping wells to medium names
        :param plate_name: Name of the plate (e.g., "plate_0", "plate_1")
        :return: ResourceSet containing one table per well
        """
        resource_set = ResourceSet()

        # Prepare medium composition mapping if tables are provided
        well_to_medium = {}
        medium_compositions = {}

        if medium_table is not None and info_table is not None:
            # Get DataFrames
            medium_df = medium_table.get_data()
            info_df = info_table.get_data()

            # Normalize well IDs in info_table (A1 -> A01, etc.)
            def normalize_well_id(well_id: str) -> str:
                if len(well_id) == 2:
                    return f"{well_id[0]}0{well_id[1]}"
                return well_id

            info_df['Well'] = info_df['Well'].apply(normalize_well_id)

            # Create well -> medium name mapping
            well_to_medium = dict(zip(info_df['Well'], info_df['Medium']))

            # Create medium name -> composition dict mapping
            for _, row in medium_df.iterrows():
                medium_name = row['Medium']
                composition = {col: row[col] for col in medium_df.columns if col != 'Medium'}
                medium_compositions[medium_name] = composition

            # Medium data prepared for tagging

        # Get parsed data (one DataFrame per filter/channel)
        parsed_data: dict[str, DataFrame] = self.parse_data(data=data, metadata=metadata)
        wells_data = self.get_wells_label_description(metadata=metadata,
                                                       existing_plate_layout=existing_plate_layout)

        # Get expected wells from metadata
        expected_wells = self.get_wells(metadata)  # Cultivation + Reservoir wells
        cultivation_wells = self.get_wells_cultivation(metadata)

        # Get all well columns (excluding time columns)
        first_filter = list(parsed_data.keys())[0] if parsed_data else None
        if not first_filter:
            return resource_set

        first_df = parsed_data[first_filter]
        well_columns = [col for col in first_df.columns if col not in ['time', 'Temps_en_h']]

        # Find missing wells (expected but no data)
        wells_with_data = set(well_columns)
        expected_cultivation_set = set(cultivation_wells)
        missing_wells = expected_cultivation_set - wells_with_data

        if missing_wells:
            self.log_info_message(f"⚠️ {len(missing_wells)} missing wells (in metadata but no data)")

        # Create one table per well
        for well in well_columns:
            # Convert well name from C01 format to C1 format (remove leading zero)
            # This ensures consistency with resource names used throughout the system
            well_clean = f"{well[0]}{int(well[1:])}" if len(well) >= 2 else well

            # Start with time column(s)
            well_df = first_df[['Temps_en_h']].copy()

            # Add measurement columns for this well from each filter
            for filter_name, filter_df in parsed_data.items():
                if well in filter_df.columns:
                    # Rename the well column to the filter name
                    well_df[filter_name] = filter_df[well]

            # Only create table if we have data (not all NaN)
            if not well_df.drop(columns=['Temps_en_h']).isna().all().all():
                table = Table(well_df)
                table.name = well_clean  # Use clean name without leading zero

                # Get user info for tag origins
                user_id = CurrentUserService.get_current_user().id if CurrentUserService.get_current_user() else None
                origins = TagOrigins(TagOriginType.USER, user_id)

                # Add column tags for proper column identification
                # Tag time column as index column
                table.add_column_tag_by_name('Temps_en_h', 'column_name', 'Temps')
                table.add_column_tag_by_name('Temps_en_h', 'unit', 'h')
                table.add_column_tag_by_name('Temps_en_h', 'is_index_column', 'true')

                # Tag measurement columns as data columns
                for col in table.column_names:
                    if col != 'Temps_en_h':
                        # This is a measurement column (Biomass, pH, pO2, etc.)
                        table.add_column_tag_by_name(col, 'column_name', col)
                        table.add_column_tag_by_name(col, 'is_data_column', 'true')

                # Add batch and sample tags only
                # Batch is the plate name, sample is the well identifier
                batch_tag = Tag(key='batch', value=plate_name, auto_parse=True,
                                origins=origins, is_propagable=True)
                sample_tag = Tag(key='sample', value=well_clean, auto_parse=True,  # Use clean name
                                 origins=origins, is_propagable=True)
                table.tags.add_tag(batch_tag)
                table.tags.add_tag(sample_tag)

                # Add medium tag if medium data is available for this well
                if well in well_to_medium:
                    medium_name = well_to_medium[well]
                    medium_composition = medium_compositions.get(medium_name, {})

                    medium_tag = Tag(key='medium', value=medium_name, auto_parse=True,
                                    additional_info={'composed': medium_composition},
                                    origins=origins, is_propagable=True)
                    table.tags.add_tag(medium_tag)

                # Check if well is missing from plate_layout (only if plate_layout is provided)
                if existing_plate_layout:
                    # Try both formats: C01 and C1
                    well_normalized = well  # C01 format
                    well_short = well_clean  # C1 format

                    has_plate_layout = (well_normalized in existing_plate_layout or
                                       well_short in existing_plate_layout)

                    if not has_plate_layout:
                        # Well is missing from plate_layout - add missing_value tag
                        missing_tag = Tag(key='missing_value', value='plate_layout', auto_parse=True,
                                         origins=origins, is_propagable=True)
                        table.tags.add_tag(missing_tag)

                resource_set.add_resource(table, well_clean)  # Use clean name

        # Create tables for missing wells (expected in metadata but no data in raw_data)
        wells_with_data = set(well_columns)
        expected_cultivation_set = set(cultivation_wells)
        missing_wells = expected_cultivation_set - wells_with_data

        if missing_wells:
            self.log_info_message(f"\nCreating {len(missing_wells)} empty tables for missing wells")
            user_id = CurrentUserService.get_current_user().id if CurrentUserService.get_current_user() else None
            origins = TagOrigins(TagOriginType.USER, user_id)

            for well in sorted(missing_wells):
                # Convert well name from C01 format to C1 format
                well_clean = f"{well[0]}{int(well[1:])}" if len(well) >= 2 else well

                # Create empty table with just time column
                empty_df = DataFrame({'Temps_en_h': []})
                table = Table(empty_df)
                table.name = well_clean

                # Add column tags
                table.add_column_tag_by_name('Temps_en_h', 'column_name', 'Temps')
                table.add_column_tag_by_name('Temps_en_h', 'unit', 'h')
                table.add_column_tag_by_name('Temps_en_h', 'is_index_column', 'true')

                # Add batch and sample tags
                batch_tag = Tag(key='batch', value='plate_0', auto_parse=True,
                                origins=origins, is_propagable=True)
                sample_tag = Tag(key='sample', value=well_clean, auto_parse=True,
                                 origins=origins, is_propagable=True)
                table.tags.add_tag(batch_tag)
                table.tags.add_tag(sample_tag)

                # Add medium tag if medium data is available for this well
                if well in well_to_medium:
                    medium_name = well_to_medium[well]
                    medium_composition = medium_compositions.get(medium_name, {})

                    medium_tag = Tag(key='medium', value=medium_name, auto_parse=True,
                                    additional_info={'composed': medium_composition},
                                    origins=origins, is_propagable=True)
                    table.tags.add_tag(medium_tag)

                # Add missing_value tag for raw_data
                missing_tag = Tag(key='missing_value', value='raw_data', auto_parse=True,
                                 origins=origins, is_propagable=True)
                table.tags.add_tag(missing_tag)

                # Also check plate_layout for this missing well
                if existing_plate_layout:
                    well_normalized = well  # C01 format
                    well_short = well_clean  # C1 format

                    has_plate_layout = (well_normalized in existing_plate_layout or
                                       well_short in existing_plate_layout)

                    if not has_plate_layout:
                        # Well is also missing from plate_layout - update tag
                        table.tags.remove_by_key('missing_value')
                        combined_missing_tag = Tag(key='missing_value', value='raw_data, plate_layout',
                                                   auto_parse=True, origins=origins, is_propagable=True)
                        table.tags.add_tag(combined_missing_tag)

                resource_set.add_resource(table, well_clean)

        return resource_set

    def create_metadata_table(self, resource_set: ResourceSet,
                              existing_plate_layout: dict | None = None,
                              medium_table: Table | None = None,
                              info_table: Table | None = None) -> Table:
        """
        Create a metadata table for machine learning purposes.

        Combines well metadata from plate_layout or medium composition data.
        Each row represents one well (batch_sample combination).

        :param resource_set: ResourceSet containing all well tables
        :param existing_plate_layout: Optional plate layout with well metadata (legacy)
        :param medium_table: Optional table with medium compositions
        :param info_table: Optional table mapping wells to medium names
        :return: Table with metadata for ML feature extraction
        """
        import pandas as pd

        metadata_rows = []

        # If medium_table and info_table are provided, use them
        if medium_table is not None and info_table is not None:
            self.log_info_message("Creating metadata table from medium_table and info_table...")

            # Get dataframes
            medium_df = medium_table.get_data()
            info_df = info_table.get_data()

            # Normalize well identifiers in info_df to C1 format (C01 → C1, C10 → C10, A1 → A1, A01 → A1)
            def normalize_well_id(well_id):
                """Normalize well ID to format like A1, C1, C10, etc. (without leading zero)."""
                well_id = str(well_id).strip()
                if len(well_id) >= 2:
                    # Extract letter and number parts
                    letter = well_id[0]
                    number_str = well_id[1:]
                    # Convert to int and back to string to remove leading zeros
                    return f"{letter}{int(number_str)}"
                return well_id

            # Create a copy to avoid modifying the original
            info_df_normalized = info_df.copy()
            info_df_normalized['Well'] = info_df_normalized['Well'].apply(normalize_well_id)

            # Create a mapping from well to medium name
            well_to_medium = dict(zip(info_df_normalized['Well'], info_df_normalized['Medium']))

            for well_name, table in resource_set.get_resources().items():
                if not isinstance(table, Table):
                    continue

                # Extract plate_name from batch tag
                batch_tags = table.tags.get_by_key('batch')
                plate_name = batch_tags[0].value if batch_tags else 'plate_0'

                # Initialize row with Series identifier
                metadata_row = {
                    'Series': f"{plate_name}_{well_name}"
                }

                # Get medium name for this well
                medium_name = well_to_medium.get(well_name)

                if medium_name:
                    # Get medium composition from medium_table
                    medium_row = medium_df[medium_df['Medium'] == medium_name]

                    if not medium_row.empty:
                        # Add all medium composition columns (except 'Medium' column)
                        for col in medium_df.columns:
                            value = medium_row.iloc[0][col]
                            metadata_row[col] = value

                metadata_rows.append(metadata_row)

        else:
            # Legacy mode: use plate_layout
            self.log_info_message("Creating metadata table from plate_layout (legacy mode)...")

            for well_name, table in resource_set.get_resources().items():
                if not isinstance(table, Table):
                    continue

                # Extract plate_name from batch tag
                batch_tags = table.tags.get_by_key('batch')
                plate_name = batch_tags[0].value if batch_tags else 'plate_0'

                # Initialize row with Series identifier
                metadata_row = {
                    'Series': f"{plate_name}_{well_name}"
                }

                # Add plate_layout metadata if available
                if existing_plate_layout:
                    # well_name is already in C1 format from resource_set keys
                    # Try both formats for backward compatibility
                    well_c1 = well_name  # Already C1 format (e.g., "C1")
                    well_c01 = f"{well_name[0]}{int(well_name[1:]):02d}"  # C01 format (e.g., "C01")

                    plate_data = None
                    if well_c1 in existing_plate_layout:
                        plate_data = existing_plate_layout[well_c1]
                    elif well_c01 in existing_plate_layout:
                        plate_data = existing_plate_layout[well_c01]

                    if plate_data and isinstance(plate_data, dict):
                        for key, value in plate_data.items():
                            # Add plate_layout metadata
                            metadata_row[f"plate_{key}"] = value

                metadata_rows.append(metadata_row)

        # Create DataFrame
        if not metadata_rows:
            # Return empty table if no data
            metadata_df = pd.DataFrame()
        else:
            metadata_df = pd.DataFrame(metadata_rows)

            # Get list of medium composition columns (from medium_table if provided)
            medium_columns = set()
            if medium_table is not None:
                medium_df = medium_table.get_data()
                medium_columns = set(medium_df.columns) - {'Medium'}

            # Remove columns that only contain NaN (but keep medium composition columns even if all 0)
            cols_to_remove = []
            for col in metadata_df.columns:
                if col == 'Series':
                    continue

                # Keep medium composition columns even if all NaN or all 0
                if col in medium_columns:
                    continue

                # Check if all values are NaN
                if metadata_df[col].isna().all():
                    cols_to_remove.append(col)
                    continue

                # For other columns (legacy plate_layout), check if all non-NaN values are 0
                try:
                    numeric_col = pd.to_numeric(metadata_df[col], errors='coerce')
                    non_nan_values = numeric_col.dropna()
                    if len(non_nan_values) > 0 and (non_nan_values == 0).all():
                        cols_to_remove.append(col)
                except Exception:
                    pass

            # Drop identified columns
            if cols_to_remove:
                metadata_df = metadata_df.drop(columns=cols_to_remove)

        # Create Table
        metadata_table = Table(metadata_df)
        metadata_table.name = "Metadata Table for ML"

        return metadata_table

    def run(self, params: ConfigParams, inputs: TaskInputs) -> TaskOutputs:
        """
        Execute the BiolectorXT data loading and processing.

        :param params: Task configuration parameters
        :param inputs: Task inputs
        :return: Task outputs
        """

        # Get medium table (unique across all plates) from dedicated port
        medium_table: Table = inputs.get('medium_table')
        self.log_info_message(f"Medium table from dedicated port: {medium_table is not None}")

        # Get all dynamic inputs (plates as ResourceList)
        plates_resource_list: ResourceList = inputs.get('source')
        self.log_info_message(f"ResourceList type: {type(plates_resource_list)}")

        if not isinstance(plates_resource_list, ResourceList):
            raise Exception(f"Expected ResourceList for 'source' input, got {type(plates_resource_list)}")

        # Get the actual list of resources from ResourceList
        plates_list = plates_resource_list.get_resources()
        self.log_info_message(f"Total resources in ResourceList: {len(plates_list)}")

        # Log type of each resource in the list
        for idx, resource in enumerate(plates_list):
            self.log_info_message(f"Resource {idx}: type={type(resource).__name__}, name={getattr(resource, 'name', 'N/A')}")

        # Filter out None resources (can happen with empty dynamic ports)
        actual_plates = [plate for plate in plates_list if plate is not None]
        num_actual_plates = len(actual_plates)

        if len(actual_plates) < len(plates_list):
            self.log_warning_message(f"Filtered out {len(plates_list) - len(actual_plates)} None/empty resources from ResourceList")

        if medium_table is not None:
            self.log_info_message(f"Found medium_table from dedicated input port: {medium_table.name if hasattr(medium_table, 'name') else 'unnamed'}")

            # Ensure "medium" tag key exists with "composed" additional info
            tag_key_model = TagKeyModel.find_by_key("medium")
            if not tag_key_model:
                self.log_info_message("Creating 'medium' tag key with 'composed' additional info spec")
                tag_key_model = TagKeyModel.create_tag_key_model(
                    key="medium",
                    label="Medium"
                )
                composed_additional_info_spec = DictParam(optional=False, human_name="Composed")
                tag_key_model.additional_infos_specs = {
                    "composed": composed_additional_info_spec.to_dto().to_json_dict()
                }
                tag_key_model.save()

        self.log_info_message(f"Processing {num_actual_plates} plate(s)")

        # Get plate names from config
        plate_names: list[str] = params.get_value('plate_names')
        self.log_info_message(f"Plate names from config: {plate_names} (count: {len(plate_names) if plate_names else 0})")

        # Validate plate names
        if plate_names and len(plate_names) > 0:
            # User provided plate names - validate count
            if len(plate_names) != num_actual_plates:
                self.log_error_message(
                    f"MISMATCH: plate_names count={len(plate_names)}, actual_plates count={num_actual_plates}"
                )
                raise Exception(
                    f"Number of plate names ({len(plate_names)}) does not match number of input plates ({num_actual_plates}). "
                    f"Please provide either no names (for default names) or exactly {num_actual_plates} names."
                )
            self.log_info_message(f"Using custom plate names: {plate_names}")
        else:
            # Use default plate names
            plate_names = [f"plate_{i}" for i in range(num_actual_plates)]
            self.log_info_message(f"Using default plate names: {plate_names}")

        # Process each plate

        # Initialize combined outputs
        all_resource_sets = []
        all_cultivation_labels = set()
        all_medium_info_wells = set()
        all_raw_data_wells = set()
        all_metadata_dfs = []

        # Process each plate
        for plate_idx, plate_resource_set in enumerate(actual_plates):
            plate_name = plate_names[plate_idx]
            self.log_info_message(f"\n{'=' * 80}")
            self.log_info_message(f"PROCESSING {plate_name.upper()}")
            self.log_info_message(f"{'=' * 80}")

            # Extract resources from ResourceSet
            if not isinstance(plate_resource_set, ResourceSet):
                raise Exception(
                    f"Plate {plate_idx} must be a ResourceSet containing 'raw_data', 'folder_metadata', and 'info_table'. "
                    f"Got {type(plate_resource_set)}"
                )

            # Get inputs for this plate from the ResourceSet
            raw_data: Table = plate_resource_set.get_resource('raw_data')
            folder_metadata: Folder = plate_resource_set.get_resource('folder_metadata')

            # info_table is optional
            info_table: Table = plate_resource_set.get_resource_or_none('info_table')
            if info_table is not None:
                self.log_info_message(f"Found info_table for plate {plate_idx}")
            else:
                self.log_info_message(f"No info_table provided for plate {plate_idx}")

            if raw_data is None or folder_metadata is None:
                available_resources = list(plate_resource_set.get_resources().keys())
                raise Exception(
                    f"Plate {plate_idx} ResourceSet must contain 'raw_data' (Table) and 'folder_metadata' (Folder). "
                    f"'info_table' is optional. Found: {available_resources}"
                )

            # Load metadata file

            # Load metadata
            metadata: dict = None
            for file_name in os.listdir(folder_metadata.path):
                if file_name.endswith('BXT.json'):
                    file_path = os.path.join(folder_metadata.path, file_name)
                    try:
                        with open(file_path, 'r', encoding='UTF-8') as json_file:
                            metadata = json.load(json_file)

                    except Exception as e:
                        raise Exception(f"Error while reading the metadata file {file_name}: {e}")

            if metadata is None:
                raise Exception(
                    f"No metadata file found in the provided folder for {plate_name}. "
                    "The folder must contain a file that ends with 'BXT.json'"
                )

            # Parse data for this plate

            # Create parsed resource set for this plate
            self.log_info_message(f"Parsing BiolectorXT data for {plate_name}...")
            resource_set = self.create_parsed_resource_set(
                data=raw_data.get_data(),
                metadata=metadata,
                existing_plate_layout=None,
                medium_table=medium_table,
                info_table=info_table,
                plate_name=plate_name
            )

            # Copy download tags from raw data
            resource_set.tags.add_tags(raw_data.tags.get_by_key(DOWNLOAD_TAG_KEY))

            self.log_success_message(f"Created {len(resource_set.get_resources())} parsed tables for {plate_name}")

            # Collect for combined outputs
            all_resource_sets.append(resource_set)

            # Gather sets of wells for Venn diagram with plate prefix
            cultivation_labels_set = set(self.get_wells_cultivation(metadata))
            # Add plate prefix to cultivation labels (convert C01 to C1 format)
            for well in cultivation_labels_set:
                well_c1 = f"{well[0]}{int(well[1:])}" if len(well) > 1 else well
                all_cultivation_labels.add(f"({plate_name}_{well_c1})")

            # Wells with medium info (from info_table if provided)
            medium_info_wells = set()
            if info_table is not None:
                info_df = info_table.get_data()
                # Normalize well IDs to C1 format (remove leading zeros)
                def normalize_well_id(well_id):
                    """Convert to C1 format: C01 → C1, C10 → C10, A1 → A1"""
                    if isinstance(well_id, str) and len(well_id) >= 2:
                        letter = well_id[0]
                        number_str = well_id[1:]
                        return f"{letter}{int(number_str)}"
                    return well_id
                info_df_normalized = info_df.copy()
                info_df_normalized['Well'] = info_df_normalized['Well'].apply(normalize_well_id)
                medium_info_wells = set(info_df_normalized['Well'].unique())
            # Add plate prefix to medium info wells (convert C01 to C1 format)
            for well in medium_info_wells:
                well_c1 = f"{well[0]}{int(well[1:])}" if len(well) > 1 else well
                all_medium_info_wells.add(f"({plate_name}_{well_c1})")

            # Wells with raw_data (already in C1 format from resource_set keys)
            raw_data_wells = set(resource_set.get_resources().keys())
            # Add plate prefix to raw data wells (wells are already in C1 format)
            for well in raw_data_wells:
                all_raw_data_wells.add(f"({plate_name}_{well})")

            # Create metadata table for this plate and collect it
            plate_metadata_table = self.create_metadata_table(
                resource_set,
                None,
                medium_table,
                info_table
            )
            all_metadata_dfs.append(plate_metadata_table.get_data())

        # Combine all resource sets with plate prefixes
        combined_resource_set = ResourceSet()
        for plate_idx, resource_set in enumerate(all_resource_sets):
            plate_name = plate_names[plate_idx]
            for well_name, table in resource_set.get_resources().items():
                # Remove leading zero from well number (C01 -> C1, C10 stays C10)
                well_name_short = well_name[0] + str(int(well_name[1:]))
                # Format: plate_0_C1 or custom_name_C1
                combined_well_name = f"{plate_name}_{well_name_short}"
                # Update the table name to match
                table.name = combined_well_name
                combined_resource_set.add_resource(table, combined_well_name)

        self.log_success_message(f"Combined total: {len(combined_resource_set.get_resources())} parsed tables from {num_actual_plates} plate(s)")

        # Combine all metadata DataFrames
        if all_metadata_dfs:
            combined_metadata_df = pd.concat(all_metadata_dfs, ignore_index=True)
            metadata_table = Table(combined_metadata_df)
            metadata_table.name = "Metadata table"
            self.log_success_message(f"Combined metadata table created with {len(combined_metadata_df)} wells")
        else:
            metadata_table = Table(pd.DataFrame({'Series': []}))
            metadata_table.name = "Metadata table"

        # Create Venn diagram for well data availability using combined data
        self.log_info_message("="*80)
        self.log_info_message("VENN DIAGRAM CONSTRUCTION")
        self.log_info_message("="*80)

        well_sets = {
            'cultivation_labels': all_cultivation_labels,
            'raw_data': all_raw_data_wells
        }

        self.log_info_message(f"cultivation_labels count: {len(all_cultivation_labels)}")
        self.log_info_message(f"cultivation_labels samples: {list(all_cultivation_labels)[:5]}")
        self.log_info_message(f"raw_data count: {len(all_raw_data_wells)}")
        self.log_info_message(f"raw_data samples: {list(all_raw_data_wells)[:5]}")

        # Calculate intersections and differences
        intersection_cult_raw = all_cultivation_labels & all_raw_data_wells
        only_in_cultivation = all_cultivation_labels - all_raw_data_wells
        only_in_raw_data = all_raw_data_wells - all_cultivation_labels

        self.log_info_message(f"Intersection (cultivation ∩ raw_data): {len(intersection_cult_raw)} wells")
        if only_in_cultivation:
            self.log_info_message(f"Only in cultivation_labels: {len(only_in_cultivation)} wells - {list(only_in_cultivation)[:5]}")
        if only_in_raw_data:
            self.log_info_message(f"Only in raw_data: {len(only_in_raw_data)} wells - {list(only_in_raw_data)[:5]}")

        # Only include medium_info in Venn diagram if medium_table was provided
        if medium_table is not None:
            well_sets['medium_info'] = all_medium_info_wells
            self.log_info_message(f"medium_info count: {len(all_medium_info_wells)}")
            self.log_info_message(f"medium_info samples: {list(all_medium_info_wells)[:5]}")
        else:
            self.log_info_message("No medium_table provided - medium_info excluded from Venn diagram")

        # Create Venn diagram
        venn_diagram = None
        if any(len(s) > 0 for s in well_sets.values()):
            fig = create_venn_diagram_wells(well_sets)
            venn_diagram = PlotlyResource(fig)
            venn_diagram.name = "BiolectorXT Well Data Availability"

        # Clean NaN values in metadata table numeric columns
        metadata_df = metadata_table.get_data().copy()

        # Try to convert columns to numeric only if they are actually numeric
        for col in metadata_df.columns:
            if col not in ['Series', 'Well', 'Medium', 'compound']:  # Exclude identifier and text columns
                original_dtype = metadata_df[col].dtype
                # Try converting to numeric
                converted_col = pd.to_numeric(metadata_df[col], errors='coerce')
                # Only keep the conversion if at least 50% of values are valid numbers
                valid_ratio = converted_col.notna().sum() / len(converted_col)
                if valid_ratio >= 0.5:
                    metadata_df[col] = converted_col

        numeric_cols_meta = metadata_df.select_dtypes(include=[np.number]).columns.tolist()

        if numeric_cols_meta:
            nan_counts_meta = metadata_df[numeric_cols_meta].isna().sum()
            total_nans_meta = nan_counts_meta.sum()

            if total_nans_meta > 0:
                metadata_df[numeric_cols_meta] = metadata_df[numeric_cols_meta].fillna(0)

        # Update metadata table with cleaned data
        metadata_table = Table(metadata_df)
        metadata_table.name = "Metadata table"

        # Prepare outputs
        outputs = {
            'resource_set': combined_resource_set,
            'venn_diagram': venn_diagram,
            'metadata_table': metadata_table
        }

        # Add medium_table to outputs if provided as input
        if medium_table is not None:
            # Replace NaN values in numeric columns with 0
            medium_df = medium_table.get_data().copy()

            # Try to convert columns to numeric only if they are actually numeric
            for col in medium_df.columns:
                if col not in ['Medium', 'Well', 'compound']:  # Exclude identifier and text columns
                    original_dtype = medium_df[col].dtype
                    # Try converting to numeric
                    converted_col = pd.to_numeric(medium_df[col], errors='coerce')
                    # Only keep the conversion if at least 50% of values are valid numbers
                    valid_ratio = converted_col.notna().sum() / len(converted_col)
                    if valid_ratio >= 0.5:
                        medium_df[col] = converted_col

            numeric_cols = medium_df.select_dtypes(include=[np.number]).columns.tolist()

            if numeric_cols:
                nan_counts = medium_df[numeric_cols].isna().sum()
                total_nans = nan_counts.sum()

                if total_nans > 0:
                    medium_df[numeric_cols] = medium_df[numeric_cols].fillna(0)

                    # Update the table with cleaned data
                    medium_table = Table(medium_df)
                    medium_table.name = "Medium table"

            outputs['medium_table'] = medium_table

        # Return outputs
        return outputs
