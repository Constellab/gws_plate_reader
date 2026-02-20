"""
Visualization Step - Combines Table, Graph and Medium views in tabs
"""

import streamlit as st
from gws_core import Scenario, ScenarioProxy, ScenarioStatus, Table
from gws_plate_reader.cell_culture_app_core._constellab_bioprocess_core.app_pages.recipe_steps.graph_view_step import (
    render_graph_view_step,
)
from gws_plate_reader.cell_culture_app_core._constellab_bioprocess_core.app_pages.recipe_steps.medium_view_step import (
    render_medium_view_step,
)
from gws_plate_reader.cell_culture_app_core._constellab_bioprocess_core.app_pages.recipe_steps.microplate_selector import (
    render_microplate_selector,
)
from gws_plate_reader.cell_culture_app_core._constellab_bioprocess_core.app_pages.recipe_steps.table_view_step import (
    render_table_view_step,
)
from gws_plate_reader.cell_culture_app_core._constellab_bioprocess_core.cell_culture_recipe import (
    CellCultureRecipe,
)
from gws_plate_reader.cell_culture_app_core._constellab_bioprocess_core.cell_culture_state import (
    CellCultureState,
)


def render_visualization_step(
    recipe: CellCultureRecipe,
    cell_culture_state: CellCultureState,
    scenario: Scenario,
    output_name: str,
) -> None:
    """
    Render the visualization step with tabs for Table, Graph and Medium views

    :param recipe: The Recipe instance
    :param cell_culture_state: The cell culture state
    :param scenario: The scenario to visualize
    :param output_name: The output name to display
    """
    translate_service = cell_culture_state.get_translate_service()

    try:
        # Get data from scenario
        target_scenario = scenario

        if target_scenario.status != ScenarioStatus.SUCCESS:
            st.warning(translate_service.translate("scenario_not_successful_yet"))
            return

        # Get data from scenario using the provided output name
        if not output_name:
            # Default to interpolation output for backward compatibility
            output_name = cell_culture_state.INTERPOLATION_SCENARIO_OUTPUT_NAME

        scenario_proxy = ScenarioProxy.from_existing_scenario(target_scenario.id)
        protocol_proxy = scenario_proxy.get_protocol()

        try:
            filtered_resource_set = protocol_proxy.get_output(output_name)
            if not filtered_resource_set:
                st.error(translate_service.translate("cannot_retrieve_data"))
                return

        except Exception as e:
            st.error(translate_service.translate("error_retrieving_data").format(error=str(e)))
            return

        # Extract data for visualization
        visualization_data = cell_culture_state.prepare_data_for_visualization(
            filtered_resource_set
        )

        if not visualization_data:
            st.warning(translate_service.translate("no_data_for_visualization"))
            return

        # Build all_data_rows from filtered_resource_set for use in graph and table views
        # This avoids duplicating this logic in each view
        all_data_rows = []
        resources = filtered_resource_set.get_resources()

        for resource_name, resource in resources.items():
            if isinstance(resource, Table):
                # Extract metadata from tags
                batch = ""
                sample = ""
                medium = ""

                if hasattr(resource, "tags") and resource.tags:
                    for tag in resource.tags.get_tags():
                        if tag.key == cell_culture_state.TAG_BATCH:
                            batch = tag.value
                        elif tag.key == cell_culture_state.TAG_SAMPLE:
                            sample = tag.value
                        elif tag.key == cell_culture_state.TAG_MEDIUM:
                            medium = tag.value

                # Get DataFrame
                df = resource.get_data()

                # Add rows to the list
                for _, row in df.iterrows():
                    row_dict = row.to_dict()
                    row_dict["Batch"] = batch
                    row_dict["Sample"] = sample
                    # Only add Medium if recipe has medium info
                    if recipe.has_medium_info:
                        row_dict["Medium"] = medium
                    row_dict["Resource_Name"] = resource_name
                    all_data_rows.append(row_dict)

        # Get unique batches and samples for filters (excluding empty strings)
        unique_batches = sorted({item["Batch"] for item in visualization_data if item["Batch"]})
        unique_samples = sorted({item["Sample"] for item in visualization_data if item["Sample"]})

        # Get available columns for selection using the new tagging system
        index_columns = cell_culture_state.get_index_columns_from_resource_set(
            filtered_resource_set
        )
        data_columns = cell_culture_state.get_data_columns_from_resource_set(filtered_resource_set)

        st.markdown(f"### {translate_service.translate('filters_selection_title')}")

        # Initialize applied selections for microplate mode
        if "viz_applied_wells" not in st.session_state:
            st.session_state.viz_applied_wells = []

        # Check if this is a microplate recipe
        is_microplate = recipe.analysis_type == "microplate"
        well_data = None

        if is_microplate:
            # Microplate mode: Display interactive plate selector
            st.info(f"🧫 {translate_service.translate('microplate_mode_info')}")

            # Build well data from the metadata table of the load scenario
            # Structure: {well: {Medium: 'name', metadata_col1: value1, ...}, ...}
            well_data = {}

            # First, build a mapping of well -> Medium from visualization_data (tags)
            well_to_medium = {}
            for item in visualization_data:
                batch = item.get("Batch", "")
                sample = item.get("Sample", "")
                medium = item.get("Medium", "")
                if sample and medium and batch:
                    well_to_medium[sample] = {batch: medium}

            # Get the metadata table from the load scenario
            metadata_resource_model = cell_culture_state.get_load_scenario_output_resource_model(
                cell_culture_state.LOAD_SCENARIO_METADATA_OUTPUT_NAME
            )

            if metadata_resource_model:
                metadata_table = metadata_resource_model.get_resource()
                if metadata_table:
                    df = metadata_table.get_data()

                    # The Series column contains "plate_name_well" format (e.g., "plate_0_C1")
                    # Extract well position from the last part after underscore
                    for _, row in df.iterrows():
                        series_value = str(row.get("Series", ""))
                        if series_value:
                            # Extract well from Series (last part after underscore)
                            parts = series_value.rsplit("_", 1)
                            well = parts[-1] if parts else series_value
                            plate = series_value[: -len(well) - 1]

                            # Build metadata dict (exclude Series column)
                            metadata = {col: row[col] for col in df.columns if col != "Series"}

                            # Add Medium name from visualization_data tags
                            if well in well_to_medium:
                                metadata["Medium"] = well_to_medium[well].get(plate, "")

                            well_data[well] = {plate: metadata}

            # Validate well_data against all_data_rows to ensure consistency
            # Extract batch/sample combinations from all_data_rows
            valid_batch_sample_combinations = set()
            for data_row in all_data_rows:
                batch = data_row.get("Batch", "")
                sample = data_row.get("Sample", "")
                if batch and sample:
                    valid_batch_sample_combinations.add((batch, sample))

            # Filter well_data to keep only wells that exist in all_data_rows
            validated_well_data = {}
            for base_well, plate_dict in well_data.items():
                validated_plate_dict = {}
                for plate, metadata in plate_dict.items():
                    # Check if this plate/well combination exists in actual data
                    if (plate, base_well) in valid_batch_sample_combinations:
                        validated_plate_dict[plate] = metadata
                if validated_plate_dict:
                    validated_well_data[base_well] = validated_plate_dict

            well_data = validated_well_data

            # Clean up selected and applied wells: remove wells that are no longer in well_data
            # This happens after quality checks when some samples are filtered out
            valid_wells_set = set()
            for base_well in well_data:
                # For multi-plate, need to check nested structure
                if isinstance(well_data[base_well], dict):
                    for plate_name in well_data[base_well]:
                        valid_wells_set.add(f"{plate_name}_{base_well}")

            # Clean up current selection
            if "visualization_selected_wells" in st.session_state:
                current_selection = st.session_state.visualization_selected_wells
                invalid_wells = [well for well in current_selection if well not in valid_wells_set]
                if invalid_wells:
                    st.session_state.visualization_selected_wells = [
                        well for well in current_selection if well in valid_wells_set
                    ]

            # Clean up applied wells
            if "viz_applied_wells" in st.session_state:
                current_applied = st.session_state.viz_applied_wells
                st.session_state.viz_applied_wells = [
                    well for well in current_applied if well in valid_wells_set
                ]

            # Render microplate selector
            selected_wells = render_microplate_selector(
                well_data=well_data,
                unique_samples=unique_samples,
                translate_service=translate_service,
                session_key_prefix="visualization",
                include_medium=recipe.has_medium_info,
            )

            # Build the list of all valid wells for select/deselect all
            all_valid_wells = []
            for base_well, data in well_data.items():
                if isinstance(data, dict):
                    # Check if multi-plate structure
                    has_nested = any(isinstance(v, dict) for v in data.values())
                    if has_nested:
                        for plate_name in data:
                            all_valid_wells.append(f"{plate_name}_{base_well}")
                    else:
                        all_valid_wells.append(base_well)

            # Buttons row: Select All, Deselect All, Apply - centered below the plate
            btn_col_left, btn_select_all, btn_deselect_all, btn_apply, btn_col_right = st.columns(
                [2, 1, 1, 1, 2]
            )

            with btn_select_all:
                if st.button(
                    translate_service.translate("select_all"),
                    width="stretch",
                    key="microplate_select_all",
                ):
                    st.session_state["visualization_selected_wells"] = list(all_valid_wells)

            with btn_deselect_all:
                if st.button(
                    translate_service.translate("deselect_all"),
                    width="stretch",
                    key="microplate_deselect_all",
                ):
                    st.session_state["visualization_selected_wells"] = []

            with btn_apply:
                if st.button(
                    translate_service.translate("apply_selection"),
                    type="primary",
                    width="stretch",
                    key="apply_microplate_viz_filters",
                ):
                    current_wells = st.session_state.get("visualization_selected_wells", [])
                    st.session_state.viz_applied_wells = current_wells.copy()

            # Check if there are unapplied changes (computed after button handlers)
            current_wells = st.session_state.get("visualization_selected_wells", [])
            wells_changed = set(current_wells) != set(st.session_state.viz_applied_wells)
            if wells_changed:
                st.info(translate_service.translate("selection_not_applied_yet"))

            st.markdown("---")

            # For compatibility with existing code, map selected wells to batch/sample
            # In microplate mode, selected_wells contains plate_name_well format (e.g., "plate_A_C1")
            # Extract unique plate names (batches) and base wells (samples) from selected wells
            temp_selected_batches = []
            temp_selected_samples = []
            for well in selected_wells:
                # Extract plate name and base well from "plate_name_well" format
                if "_" in well:
                    parts = well.rsplit("_", 1)
                    if len(parts) == 2:
                        plate_name = parts[0]
                        base_well = parts[1]
                        if plate_name not in temp_selected_batches:
                            temp_selected_batches.append(plate_name)
                        if base_well not in temp_selected_samples:
                            temp_selected_samples.append(base_well)

            # Use applied wells for visualization
            applied_wells = st.session_state.viz_applied_wells
            selected_batches = []
            selected_samples = []
            for well in applied_wells:
                # Extract plate name and base well from "plate_name_well" format
                if "_" in well:
                    parts = well.rsplit("_", 1)
                    if len(parts) == 2:
                        plate_name = parts[0]
                        base_well = parts[1]
                        if plate_name not in selected_batches:
                            selected_batches.append(plate_name)
                        if base_well not in selected_samples:
                            selected_samples.append(base_well)

        else:
            # Standard mode: Display batch and sample multiselect
            # Create 2x2 grid with batches and samples first
            col1, col2 = st.columns(2)

            with col1:
                col1_select, col1_button = st.columns([3, 1])
                if (
                    "visualization_batches" not in st.session_state
                    or len(
                        [
                            batch
                            for batch in st.session_state.visualization_batches
                            if batch not in unique_batches
                        ]
                    )
                    > 0
                ):
                    st.session_state.visualization_batches = []
                with col1_button:
                    if st.button(
                        translate_service.translate("select_all_batches"),
                        key="select_all_batches_viz",
                        width="stretch",
                    ):
                        st.session_state.visualization_batches = unique_batches
                with col1_select:
                    selected_batches = st.multiselect(
                        translate_service.translate("choose_batches"),
                        options=unique_batches,
                        key="visualization_batches",
                    )

            with col2:
                col2_select, col2_button = st.columns([3, 1])
                if (
                    "visualization_samples" not in st.session_state
                    or len(
                        [
                            sample
                            for sample in st.session_state.visualization_samples
                            if sample not in unique_samples
                        ]
                    )
                    > 0
                ):
                    st.session_state.visualization_samples = []
                with col2_button:
                    if st.button(
                        translate_service.translate("select_all_samples"),
                        key="select_all_samples_viz",
                        width="stretch",
                    ):
                        st.session_state.visualization_samples = unique_samples
                with col2_select:
                    selected_samples = st.multiselect(
                        translate_service.translate("choose_samples"),
                        options=unique_samples,
                        key="visualization_samples",
                    )

        # Second row of the 2x2 grid
        col3, col4 = st.columns(2)

        with col3:
            # Check if index columns are available
            if index_columns:
                selected_index = st.selectbox(
                    translate_service.translate("choose_index_column"),
                    options=index_columns,
                    index=0,
                    key="visualization_index",
                    help=translate_service.translate("choose_index_column_help"),
                )
            else:
                st.warning(translate_service.translate("no_index_column"))
                selected_index = None

        # Filter data columns to exclude the selected index
        # Always exclude the selected index from selectable columns
        if selected_index:
            filtered_data_columns = [col for col in data_columns if col != selected_index]
        else:
            filtered_data_columns = data_columns

        with col4:
            selected_columns = st.multiselect(
                translate_service.translate("choose_columns"),
                options=filtered_data_columns,
                key="visualization_columns",
                help=translate_service.translate("data_columns_available_help")
                + (
                    translate_service.translate("excluding_index_help").format(index=selected_index)
                    if selected_index
                    else ""
                ),
            )

        # Store selections in session state for tabs to access
        st.session_state["viz_selected_batches"] = selected_batches
        st.session_state["viz_selected_samples"] = selected_samples
        st.session_state["viz_selected_index"] = selected_index
        st.session_state["viz_selected_columns"] = selected_columns
        st.session_state["viz_filtered_resource_set"] = filtered_resource_set
        st.session_state["viz_target_scenario"] = target_scenario
        st.session_state["viz_visualization_data"] = visualization_data
        st.session_state["viz_all_data_rows"] = all_data_rows
        st.session_state["viz_well_data"] = well_data if is_microplate else None

        if recipe.has_medium_info:
            # Create tabs for the three visualization types
            tab1, tab2, tab3 = st.tabs(
                [
                    translate_service.translate("table"),
                    translate_service.translate("graphs"),
                    translate_service.translate("medium"),
                ]
            )

            with tab3:
                render_medium_view_step(
                    recipe,
                    cell_culture_state,
                    scenario,
                    output_name,
                    st.session_state.get("viz_selected_batches"),
                    st.session_state.get("viz_selected_samples"),
                )
        else:
            # Create tabs for Table and Graph only
            tab1, tab2 = st.tabs(
                [translate_service.translate("table"), translate_service.translate("graphs")]
            )

        with tab1:
            render_table_view_step(
                recipe,
                cell_culture_state,
                scenario,
                output_name,
                st.session_state.get("viz_filtered_resource_set"),
                st.session_state.get("viz_target_scenario"),
                st.session_state.get("viz_visualization_data"),
                st.session_state.get("viz_selected_batches"),
                st.session_state.get("viz_selected_samples"),
                st.session_state.get("viz_selected_index"),
                st.session_state.get("viz_selected_columns"),
            )

        with tab2:
            render_graph_view_step(
                recipe,
                cell_culture_state,
                scenario,
                output_name,
                st.session_state.get("viz_filtered_resource_set"),
                st.session_state.get("viz_target_scenario"),
                st.session_state.get("viz_visualization_data"),
                st.session_state.get("viz_selected_batches"),
                st.session_state.get("viz_selected_samples"),
                st.session_state.get("viz_selected_index"),
                st.session_state.get("viz_selected_columns"),
                st.session_state.get("viz_all_data_rows"),
                st.session_state.get("viz_well_data"),
            )

    except Exception as e:
        st.error(translate_service.translate("error_loading_visualization").format(error=str(e)))
