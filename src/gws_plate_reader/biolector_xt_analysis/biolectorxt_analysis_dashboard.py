import re
import unicodedata
from typing import Any, Dict

import streamlit as st
from gws_core.tag.tag import Tag
from gws_plate_reader.biolector_xt_analysis.biolector_state import (
    CROSSED_OUT_WELLS, BiolectorState, BiolectorStateMode)

from .analysis_tab import render_analysis_tab
from .plot_tab import render_plot_tab
from .table_tab import render_table_tab


def show_content():

    if BiolectorState.get_selected_filters() == None:
        BiolectorState.set_selected_filters(BiolectorState.get_filters_list())

    def render_table_page():
        render_table_tab()

    def render_plot_page():
        render_plot_tab()

    def render_analysis_page():
        render_analysis_tab()

    tables_page = st.Page(render_table_page, title='Tables', url_path='tables', icon='📄')
    plots_page = st.Page(render_plot_page, title='Plots', url_path='plots', icon='📈')
    analysis_page = st.Page(render_analysis_page, title='Growth rate analysis', url_path='protocols', icon='🔍')

    pg = st.navigation([tables_page, plots_page, analysis_page])

    pg.run()


def run(data: Dict[str, Any], is_standalone: bool, input_tag: Tag):
    BiolectorState.init(data=data, mode=BiolectorStateMode.SINGLE_PLATE
                        if not is_standalone else BiolectorStateMode.STANDALONE, input_tag=input_tag)

    # Define well data (e.g., volume information for each well)
    well_data = BiolectorState.get_well_data_description()

    # Inject custom CSS to set the width of the sidebar
    st.markdown(
        f"""
        <style>
            section[data-testid="stSidebar"] {{
                width: 420px !important;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        @st.fragment
        def fragment_sidebar_function():
            st.write("Microplate")

            all_keys_well_description = set()
            for well, info in well_data.items():
                all_keys_well_description.update(info.keys())
            all_keys_well_description = [item for item in all_keys_well_description]

            # Color microplate by ...
            selected_color_well = st.selectbox("Color microplate by ...",
                                               all_keys_well_description,
                                               index=0, key="selected_color_well")

            # 48 distinct colors
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

            # Assign colors dynamically to labels
            unique_labels = list(set(
                re.sub(r"[%\./]", "", unicodedata.normalize("NFKD", well.get(selected_color_well, "").strip().replace(" ", "_"))
                       .encode("ascii", "ignore")
                       .decode("utf-8"))
                for well in well_data.values()
            ))

            # Ensure "" is in unique_labels -> because A, B etc doesn't have labels for example
            if "" not in unique_labels:
                unique_labels.append("")

            # Make sure that the more specific rules (such as for B57M3Fed) are defined after the more general rules (for B57M3)
            unique_labels = sorted(unique_labels)

            # Assign colors
            label_colors = {}
            for i, label in enumerate(unique_labels):
                # for empty labels, we assign a color
                if label == "":
                    label_colors[label] = "#F991C3"
                else:
                    label_colors[label] = color_palette[i % len(color_palette)]

            # Create css code
            css_template = """
                div[class*="st-key-{label}"] .stButton button:not([kind="primary"]) {{
                    display: inline-block;
                    width: 41px;  /* Adjust width and height as needed */
                    height: 41px;
                    border-radius: 50%;  /* Make it circular */
                    background-color: {color};  /* Button color */
                    color: black;  /* Text color */
                    text-align: center;
                    line-height: 41px;  /* Center text vertically */
                    font-size: 4px;  /* Text size */
                    padding: 0;  /* Remove padding to avoid extra space */
                    margin: 0;
                    cursor: pointer;
                    text-decoration: none;  /* Remove underline */
                }}

                """
            css_code = "".join(css_template.format(label=label, color=color) for label, color in label_colors.items())
            
            # Add CSS for primary buttons to keep normal styling
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
            
            active = """ button:active {
                        position:relative;
                        top:1px;
                        }"""
            st.html(f"<style>{css_code} {primary_button_css} {active} </style>")

            # Define the structure of the 48-well microplate
            ROWS = 6
            COLS = 8
            crossed_out_wells = []
            if BiolectorState.is_microfluidics():
                crossed_out_wells = CROSSED_OUT_WELLS
            # Define the structure of the 48-well microplate
            wells = [[f"{chr(65 + row)}{col + 1:02d}" for col in range(COLS)] for row in range(ROWS)]

            # Column header buttons
            # add a column for extra space to the right but shorter than the other
            cols_header = st.columns([4] * (COLS +1) + [1])

            for col in range(COLS):
                if cols_header[col + 1].button(str(col + 1), key=f"col_{col + 1}"):
                    if col + 1 in BiolectorState.get_selected_cols():
                        BiolectorState.remove_selected_col(col + 1)
                        for row in range(ROWS):
                            well = wells[row][col]
                            if well not in crossed_out_wells:
                                if well in BiolectorState.get_wells_clicked():
                                    BiolectorState.remove_well_clicked(well)
                    else:
                        BiolectorState.append_selected_col(col + 1)
                        for row in range(ROWS):
                            well = wells[row][col]
                            if well not in crossed_out_wells:
                                if well not in BiolectorState.get_wells_clicked():
                                    BiolectorState.append_well_clicked(well)
                    st.rerun(scope="app")

            has_changed = False
            # Loop over the wells and create a grid of buttons
            for row in range(ROWS):
                # Add space to the right of the plate
                cols_object = st.columns([4] * (COLS +1) + [1])
                # Row header button
                if cols_object[0].button(chr(65 + row), key=f"row_{chr(65 + row)}"):
                    if chr(65 + row) in BiolectorState.get_selected_rows():
                        BiolectorState.remove_selected_row(chr(65 + row))
                        for col in range(COLS):
                            well = wells[row][col]
                            if well not in crossed_out_wells:
                                if well in BiolectorState.get_wells_clicked():
                                    BiolectorState.remove_well_clicked(well)
                    else:
                        BiolectorState.append_selected_row(chr(65 + row))
                        for col in range(COLS):
                            well = wells[row][col]
                            if well not in crossed_out_wells:
                                if well not in BiolectorState.get_wells_clicked():
                                    BiolectorState.append_well_clicked(well)
                    st.rerun(scope="app")

                for col in range(COLS):
                    well = wells[row][col]
                    # Key
                    label_normalized = re.sub(r'[%\./]', '', unicodedata.normalize('NFKD', well_data[well].get(
                        selected_color_well, "").strip().replace(' ', '_')).encode('ascii', 'ignore').decode('utf-8'))
                    key = f"{label_normalized}-{well}"
                    # Dynamically create tooltip text from the well_data dictionary
                    if well in well_data:
                        sorted_items = sorted(well_data[well].items())
                        help_tab = "| Property | Value |\n|----------|-------|\n" + "\n".join(
                            [f"| **{key}** | {value} |" for key, value in sorted_items])
                    else:
                        help_tab = "No data available"
                    # Check if the well should be crossed out
                    if well in crossed_out_wells:
                        cols_object[col+1].button(f":gray[{well}]", key=key, help=help_tab, disabled=True)
                    elif well in BiolectorState.get_wells_clicked():
                        if cols_object[col+1].button(f"**{well}**", key=key, help=help_tab):
                            if well in BiolectorState.get_wells_clicked():
                                BiolectorState.remove_well_clicked(well)
                            has_changed = True
                    else:
                        if cols_object[col+1].button(well, key=key, help=help_tab):
                            BiolectorState.append_well_clicked(well)
                            has_changed = True

            if has_changed:
                # when the selection changes, we rerun the app to update the content
                st.rerun(scope="app")

            st.write(f"All the wells clicked are: {', '.join(BiolectorState.get_wells_clicked())}")

            all_keys_well_description
        fragment_sidebar_function()

        # Add the reset button
        st.button("Reset wells selection", on_click=BiolectorState.clear_wells_clicked)

    show_content()
