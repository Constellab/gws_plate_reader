"""
Microplate Selector Component
Renders an interactive microplate grid for well selection with color coding by medium
"""
import re
import unicodedata
from typing import List

import streamlit as st


def render_microplate_selector(
    well_data: dict,
    unique_samples: list,
    translate_service,
    session_key_prefix: str = "graph_view",
    include_medium: bool = True
) -> List[str]:
    """Render an interactive microplate selector for well selection

    :param well_data: Dictionary with well information.
                      For multi-plate: {well: {plate: data_dict, ...}, ...}
                      For single-plate: {well: data_dict, ...}
    :param unique_samples: List of unique sample identifiers (wells with plate prefix for compatibility)
    :param translate_service: Translation service
    :param session_key_prefix: Prefix for session state keys
    :param include_medium: Whether to include Medium data in tooltips (default: True)
    :return: List of selected wells (with plate prefix for multi-plate)
    """

    # Initialize session state for selected wells
    wells_key = f"{session_key_prefix}_selected_wells"
    if wells_key not in st.session_state:
        st.session_state[wells_key] = []

    # Auto-detect plates and structure from well_data
    detected_plates = set()
    base_wells = set()
    is_multiplate_structure = False

    # Analyze well_data structure
    for well, data in well_data.items():
        base_wells.add(well)
        if isinstance(data, dict):
            # Check if this is multi-plate structure (nested dict with plate names)
            for key, value in data.items():
                if isinstance(value, dict) and 'plate' not in value:
                    # This looks like a plate name key with nested data
                    detected_plates.add(key)
                    is_multiplate_structure = True
                elif key == 'plate' and isinstance(data.get('plate'), str):
                    # Single plate mode with 'plate' field
                    detected_plates.add(value)

    # Determine plate names
    if is_multiplate_structure:
        plate_names = sorted(list(detected_plates))
        is_multiplate = len(plate_names) > 1
    else:
        # Not multi-plate structure, single plate mode
        is_multiplate = False
        plate_names = None

    base_wells = sorted(list(base_wells))

    # Color by medium if available, otherwise use default color
    st.write(f"**{translate_service.translate('microplate_selection')}**")
    if is_multiplate:
        unified_text = translate_service.translate('unified_view_plates').format(
            num_plates=len(plate_names),
            plate_names=', '.join(plate_names)
        )
        st.caption(f"📊 {unified_text}")
        st.caption(f"ℹ️ {translate_service.translate('selecting_well_info')}")

    # Check if Medium data is available
    has_medium = False
    for well, data in well_data.items():
        if is_multiplate_structure:
            # Check in nested structure
            for plate_data in data.values():
                if isinstance(plate_data, dict) and 'Medium' in plate_data and plate_data['Medium']:
                    has_medium = True
                    break
        else:
            # Check in flat structure
            if isinstance(data, dict) and 'Medium' in data and data['Medium']:
                has_medium = True
                break
        if has_medium:
            break

    selected_color_well = 'Medium' if has_medium else None

    # Color palette
    color_palette = [
        "#f4c2c2", "#7fbde3", "#85c985", "#fce79b", "#c58fd3",
        "#b9e9eb", "#ffbb7b", "#f5a8f6", "#c79a6c", "#88c7cc",
        "#9585d1", "#f08080", "#6da38a", "#dfb6a4", "#d4ecb4",
        "#c76887", "#87e7a6", "#8a8082", "#F9D9A1", "#baa6ec",
        "#F1E1F1", "#B2F3A1", "#FF5733", "#33FF57", "#D2F0A1",
        "#3357FF", "#F3FF33", "#A1E5D4", "#C8C8FF", "#E3D5C0",
        "#FF33A8", "#33FFF3", "#A833FF", "#FFA833", "#8D33FF",
        "#FF338D", "#33FF8D", "#8DFF33", "#338DFF", "#F033FF",
        "#FF8333", "#8333FF", "#33A8FF", "#E2D6F3", "#D1DFF5",
        "#FF33F0", "#33F0FF", "#57FF33",
    ]

    # Assign colors to labels based on Medium values
    if selected_color_well:
        # Extract unique medium values and normalize them
        unique_labels = set()
        for well, data in well_data.items():
            if is_multiplate_structure:
                # Check all plates for this well
                for plate_data in data.values():
                    if isinstance(plate_data, dict):
                        medium_value = plate_data.get(selected_color_well, "")
                        if medium_value:
                            label_normalized = re.sub(
                                r"[%\./]", "",
                                unicodedata.normalize("NFKD", str(medium_value).strip().replace(" ", "_"))
                                .encode("ascii", "ignore")
                                .decode("utf-8")
                            )
                            unique_labels.add(label_normalized)
            else:
                # Single plate mode
                if isinstance(data, dict):
                    medium_value = data.get(selected_color_well, "")
                    if medium_value:
                        label_normalized = re.sub(
                            r"[%\./]", "",
                            unicodedata.normalize("NFKD", str(medium_value).strip().replace(" ", "_"))
                            .encode("ascii", "ignore")
                            .decode("utf-8")
                        )
                        unique_labels.add(label_normalized)

        unique_labels = sorted(list(unique_labels))

        # Add empty label for wells without medium
        if "" not in unique_labels:
            unique_labels.append("")
    else:
        # No coloring, use default for all
        unique_labels = [""]

    label_colors = {}
    for i, label in enumerate(unique_labels):
        if label == "":
            label_colors[label] = "#F991C3"
        else:
            label_colors[label] = color_palette[i % len(color_palette)]

    # CSS for well buttons ONLY within microplate container
    # Use the container key to target the Streamlit-generated container
    container_selector = f'div[class*="{session_key_prefix}_microplate_container"]'

    css_template = f"""
        {container_selector} div[class*="st-key-{session_key_prefix}_{{label}}"]:not([class*="_col_"]):not([class*="_row_"]) .stButton .stTooltipHoverTarget {{{{
            width: 35px !important;
            height: 35px;
        }}}}

        {container_selector} div[class*="st-key-{session_key_prefix}_{{label}}"]:not([class*="_col_"]):not([class*="_row_"]) .stButton button:not([kind="primary"]) {{{{
            display: inline-block;
            width: 35px;
            height: 35px;
            border-radius: 50%;
            background-color: {{color}};
            color: black;
            text-align: center;
            line-height: 35px;
            font-size: 9px;
            padding: 0;
            margin: 0;
            cursor: pointer;
            text-decoration: none;
            border: 2px solid rgba(0, 0, 0, 0.1);
        }}}}

        {container_selector} div[class*="st-key-{session_key_prefix}_{{label}}"]:not([class*="_col_"]):not([class*="_row_"]) .stButton button:not([kind="primary"]):has(strong) {{{{
            border: 3px solid rgba(0, 0, 0, 0.6);
            font-weight: bold;
        }}}}
        """
    # Generate CSS only for non-empty labels (exclude default color wells)
    css_code = "".join(css_template.format(label=label, color=color) for label, color in label_colors.items() if label != "")

    # Add CSS for wells with empty label (no medium) - use more specific selector
    if "" in label_colors:
        empty_label_css = f"""
        {container_selector} div[class*="st-key-{session_key_prefix}_-"]:not([class*="_col_"]):not([class*="_row_"]) .stButton .stTooltipHoverTarget {{
            width: 35px !important;
            height: 35px;
        }}

        {container_selector} div[class*="st-key-{session_key_prefix}_-"]:not([class*="_col_"]):not([class*="_row_"]) .stButton button:not([kind="primary"]) {{
            display: inline-block;
            width: 35px;
            height: 35px;
            border-radius: 50%;
            background-color: {label_colors[""]};
            color: black;
            text-align: center;
            line-height: 35px;
            font-size: 9px;
            padding: 0;
            margin: 0;
            cursor: pointer;
            text-decoration: none;
            border: 2px solid rgba(0, 0, 0, 0.1);
        }}

        {container_selector} div[class*="st-key-{session_key_prefix}_-"]:not([class*="_col_"]):not([class*="_row_"]) .stButton button:not([kind="primary"]):has(strong) {{
            border: 3px solid rgba(0, 0, 0, 0.6);
            font-weight: bold;
        }}
        """
        css_code += empty_label_css

    # CSS for row and column header buttons - same style as wells with default color
    header_buttons_css = f"""
        {container_selector} div[class*="st-key-{session_key_prefix}_col_"] .stButton .stTooltipHoverTarget {{
            width: 35px !important;
            height: 35px;
        }}

        {container_selector} div[class*="st-key-{session_key_prefix}_col_"] .stButton button:not([kind="primary"]) {{
            display: inline-block;
            width: 35px;
            height: 35px;
            border-radius: 50%;
            background-color: #F991C3;
            color: black;
            text-align: center;
            line-height: 35px;
            font-size: 9px;
            padding: 0;
            margin: 0;
            cursor: pointer;
            text-decoration: none;
        }}

        {container_selector} div[class*="st-key-{session_key_prefix}_row_"] .stButton .stTooltipHoverTarget {{
            width: 35px !important;
            height: 35px;
        }}

        {container_selector} div[class*="st-key-{session_key_prefix}_row_"] .stButton button:not([kind="primary"]) {{
            display: inline-block;
            width: 35px;
            height: 35px;
            border-radius: 50%;
            background-color: #F991C3;
            color: black;
            text-align: center;
            line-height: 35px;
            font-size: 9px;
            padding: 0;
            margin: 0;
            cursor: pointer;
            text-decoration: none;
        }}
        """
    css_code += header_buttons_css

    # Keep primary buttons normal
    primary_button_css = """
        button[kind="primary"] {
            border-radius: 0.5rem !important;
            width: auto !important;
            height: auto !important;
            padding: 0.25rem 0.75rem !important;
            line-height: normal !important;
            font-size: 14px !important;
        }
        """

    active_css = f"""
        {container_selector} button:active {{
            position: relative;
            top: 1px;
        }}
        """

    # Container style to limit the width of the plate and control spacing
    container_css = f"""
        {container_selector} {{
            max-width: 600px;
            margin: 0 auto;
        }}
        {container_selector} div[data-testid="column"] {{
            gap: 5px !important;
            padding: 0 !important;
        }}
        {container_selector} div[data-testid="stHorizontalBlock"] {{
            gap: 5px !important;
        }}
        """

    st.html(f"<style>{css_code} {primary_button_css} {active_css} {container_css}</style>")

    # Create a container for the microplate
    with st.container(key=f"{session_key_prefix}_microplate_container"):
        # Always display all 6 rows (A-F) for complete microplate view
        # Wells without data will be displayed but disabled
        ROWS = 6  # A to F
        start_row = 0
        COLS = 8
        # Generate wells in C1 format (without leading zero: C1, C2, ... C8)
        # Wells are displayed if they have data in well_data, otherwise shown as disabled
        wells = [[f"{chr(65 + start_row + row)}{col + 1}" for col in range(COLS)] for row in range(ROWS)]

        # Column headers
        cols_header = st.columns([1] + [1] * COLS + [1])
        for col in range(COLS):
            if cols_header[col + 1].button(str(col + 1), key=f"{session_key_prefix}_col_{col + 1}"):
                # Toggle entire column
                for row in range(ROWS):
                    base_well = wells[row][col]
                    if base_well in well_data:  # Only toggle wells with data
                        # Handle multi-plate or single plate
                        if is_multiplate_structure and plate_names:
                            # Toggle for all plates
                            for plate_name in plate_names:
                                full_well = f"{plate_name}_{base_well}"
                                if full_well in st.session_state[wells_key]:
                                    st.session_state[wells_key].remove(full_well)
                                else:
                                    st.session_state[wells_key].append(full_well)
                        else:
                            # Single plate mode
                            if base_well in st.session_state[wells_key]:
                                st.session_state[wells_key].remove(base_well)
                            else:
                                st.session_state[wells_key].append(base_well)
                st.rerun()

        # Row buttons and well grid
        for row in range(ROWS):
            cols_object = st.columns([1] + [1] * COLS + [1])

            # Row header
            if cols_object[0].button(chr(65 + start_row + row), key=f"{session_key_prefix}_row_{chr(65 + start_row + row)}"):
                # Toggle entire row
                for col in range(COLS):
                    base_well = wells[row][col]
                    if base_well in well_data:  # Only toggle wells with data
                        # Handle multi-plate or single plate
                        if is_multiplate_structure and plate_names:
                            # Toggle for all plates
                            for plate_name in plate_names:
                                full_well = f"{plate_name}_{base_well}"
                                if full_well in st.session_state[wells_key]:
                                    st.session_state[wells_key].remove(full_well)
                                else:
                                    st.session_state[wells_key].append(full_well)
                        else:
                            # Single plate mode
                            if base_well in st.session_state[wells_key]:
                                st.session_state[wells_key].remove(base_well)
                            else:
                                st.session_state[wells_key].append(base_well)
                st.rerun()

            for col in range(COLS):
                base_well = wells[row][col]

                # Generate key for button (use base well for coloring)
                if selected_color_well:
                    # Get color from first available plate data
                    label_normalized = ""
                    if base_well in well_data:
                        if is_multiplate_structure and plate_names:
                            # Multi-plate: use first plate for coloring
                            first_plate_data = well_data[base_well].get(plate_names[0], {})
                            if isinstance(first_plate_data, dict):
                                medium_value = first_plate_data.get(selected_color_well, "")
                                if medium_value:
                                    label_normalized = re.sub(
                                        r'[%\./]', '',
                                        unicodedata.normalize('NFKD', str(medium_value).strip().replace(' ', '_'))
                                        .encode('ascii', 'ignore')
                                        .decode('utf-8')
                                    )
                        else:
                            # Single plate mode
                            well_info = well_data.get(base_well, {})
                            if isinstance(well_info, dict):
                                medium_value = well_info.get(selected_color_well, "")
                                if medium_value:
                                    label_normalized = re.sub(
                                        r'[%\./]', '',
                                        unicodedata.normalize('NFKD', str(medium_value).strip().replace(' ', '_'))
                                        .encode('ascii', 'ignore')
                                        .decode('utf-8')
                                    )
                else:
                    label_normalized = ""

                key = f"{session_key_prefix}_{label_normalized}-{base_well}"

                # Create tooltip
                if base_well in well_data:
                    if is_multiplate_structure and plate_names:
                        # Multi-plate: show data from all plates in a single table with columns per plate
                        # Collect all properties across all plates
                        all_properties = set()
                        plate_data_dict = {}
                        for plate_name in plate_names:
                            plate_data = well_data[base_well].get(plate_name, {})
                            if isinstance(plate_data, dict):
                                plate_data_dict[plate_name] = plate_data
                                all_properties.update(plate_data.keys())

                        if all_properties:
                            # Sort properties alphabetically
                            sorted_properties = sorted(all_properties)

                            # Build table header
                            header = "| Property | " + " | ".join(plate_names) + " |"
                            separator = "|----------|" + "|".join(["----------"] * len(plate_names)) + "|"

                            # Build table rows
                            table_rows = []
                            for prop in sorted_properties:
                                # Skip Medium property if include_medium is False
                                if not include_medium and prop == 'Medium':
                                    continue
                                row_values = [plate_data_dict.get(plate, {}).get(prop, "") for plate in plate_names]
                                table_row = f"| **{prop}** | " + " | ".join(str(v) for v in row_values) + " |"
                                table_rows.append(table_row)

                            help_tab = header + "\n" + separator + "\n" + "\n".join(table_rows)
                        else:
                            help_tab = translate_service.translate('no_data_available')
                    else:
                        # Single plate mode
                        well_info = well_data[base_well]
                        if isinstance(well_info, dict):
                            # Filter out Medium if include_medium is False
                            if include_medium:
                                sorted_items = sorted(well_info.items())
                            else:
                                sorted_items = sorted((k, v) for k, v in well_info.items() if k != 'Medium')

                            prop_header = translate_service.translate('property_header')
                            val_header = translate_service.translate('value_header')
                            help_tab = f"| {prop_header} | {val_header} |\n|----------|-------|\n" + "\n".join(
                                [f"| **{k}** | {v} |" for k, v in sorted_items])
                        else:
                            help_tab = translate_service.translate('no_data_available')
                else:
                    help_tab = translate_service.translate('no_data_available')

                # Check if well exists and is selected
                well_exists = base_well in well_data

                if is_multiplate_structure and plate_names:
                    # Check if ALL plates are selected for this well
                    all_selected = all(
                        f"{plate_name}_{base_well}" in st.session_state[wells_key]
                        for plate_name in plate_names
                    )
                else:
                    # Single plate mode
                    all_selected = base_well in st.session_state[wells_key]

                # Render button
                # Only disable wells that don't have data (regardless of crossed_out_wells list)
                if not well_exists:
                    cols_object[col+1].button(f":gray[{base_well}]", key=key, help=help_tab, disabled=True)
                elif all_selected:
                    if cols_object[col+1].button(f"**{base_well}**", key=key, help=help_tab):
                        # Deselect for all plates
                        if is_multiplate_structure and plate_names:
                            for plate_name in plate_names:
                                full_well = f"{plate_name}_{base_well}"
                                if full_well in st.session_state[wells_key]:
                                    st.session_state[wells_key].remove(full_well)
                        else:
                            if base_well in st.session_state[wells_key]:
                                st.session_state[wells_key].remove(base_well)
                        st.rerun()
                else:
                    if cols_object[col+1].button(base_well, key=key, help=help_tab):
                        # Select for all plates
                        if is_multiplate_structure and plate_names:
                            for plate_name in plate_names:
                                full_well = f"{plate_name}_{base_well}"
                                if full_well not in st.session_state[wells_key]:
                                    st.session_state[wells_key].append(full_well)
                        else:
                            if base_well not in st.session_state[wells_key]:
                                st.session_state[wells_key].append(base_well)
                        st.rerun()

        # Display selected wells
        if is_multiplate:
            # Group selected wells by plate for display
            selected_by_plate = {}
            for plate_name in plate_names:
                selected_by_plate[plate_name] = []

            for well in st.session_state[wells_key]:
                for plate_name in plate_names:
                    if well.startswith(f"{plate_name}_"):
                        base = well[len(plate_name)+1:]
                        selected_by_plate[plate_name].append(base)
                        break

            # Show summary
            total_selected = len(st.session_state[wells_key])
            unique_base_wells = set()
            for wells_list in selected_by_plate.values():
                unique_base_wells.update(wells_list)

            summary_text = translate_service.translate('selected_wells_summary').format(
                unique_wells=len(unique_base_wells),
                num_plates=len(plate_names),
                total=total_selected
            )
            st.write(f"**{summary_text}**")

            # Show details per plate
            with st.expander(f"📋 {translate_service.translate('selection_details_per_plate')}", expanded=False):
                for plate_name in plate_names:
                    wells_for_plate = sorted(selected_by_plate[plate_name])
                    none_text = translate_service.translate('none')
                    st.write(f"**{plate_name}:** {', '.join(wells_for_plate) if wells_for_plate else none_text}")
        else:
            selected_label = translate_service.translate('selected_wells_label')
            none_text = translate_service.translate('none')
            wells_text = ', '.join(sorted(st.session_state[wells_key])) if st.session_state[wells_key] else none_text
            st.write(f"**{selected_label}** {wells_text}")

    return st.session_state[wells_key]
