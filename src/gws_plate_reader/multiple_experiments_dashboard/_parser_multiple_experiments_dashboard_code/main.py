import streamlit as st
from gws_plate_reader.biolector_xt_analysis import (analysis_tab, plot_tab,
                                                    table_tab)
from gws_plate_reader.biolector_xt_analysis.biolector_state import (
    BiolectorState, BiolectorStateMode)
from gws_plate_reader.multiple_experiments_dashboard._parser_multiple_experiments_dashboard_code.pages import \
    find_experiments

sources: list
params: dict

WELLS_NUMBER = 48  # 96
ROWS = 6  # 8
COLS = 8  # 12

# 48 distinct colors
COLOR_PALETTE = [
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


def get_complete_wells_data(wells_data_list: dict) -> dict:
    """
    Get the complete wells data with the missing wells
    :param well_data_list: the list of wells data
    :return: the complete wells data
    """
    complete_wells_data_list = {}
    for well in range(WELLS_NUMBER):
        well_letter = chr(65 + well // COLS)
        # 2 digit number
        well_number = well % COLS + 1
        if well_number < 10:
            well_number = f'0{well_number}'
        well_name = f'{well_letter}{well_number}'
        complete_wells_data_list[well_name] = {}
        for plate, wells_data in wells_data_list.items():
            if well_name in wells_data:
                complete_wells_data_list[well_name][plate] = wells_data[well_name]
    return complete_wells_data_list


def get_well_data_help_tab(w_data: dict) -> str:
    """
    Get the help tab for the well data
    :param well_data: the well data
    :return: the help tab
    """
    if not w_data or w_data == {}:
        return "No data available"
    plates = list(w_data.keys())
    res = '| Property |' + "".join(f' {plate} |' for plate in plates) + "\n"
    all_metadata = set()
    res += '|----------|' + "".join(f"{''.join('-' for i in range(len(plate)+2))}|" for plate in plates) + "\n"
    for plate in plates:
        all_metadata.update(w for w in w_data[plate].keys())
    for metadata in all_metadata:
        res += f'| **{metadata}** |' + "".join(
            f" {w_data[plate].get(metadata, '')} |" for plate in plates) + "\n"
    return res


_find_experiments_page = st.Page(find_experiments.render_find_experiments_page,
                                 title='Find experiments', url_path='find_experiments', icon='🔍')
_tables_page = st.Page(table_tab.render_table_tab, title='Tables', url_path='tables', icon='📄')
_plots_page = st.Page(plot_tab.render_plot_tab, title='Plots', url_path='plots', icon='📈')
_analysis_page = st.Page(analysis_tab.render_analysis_tab, title='Analysis', url_path='protocols', icon='🔍')

pages = {'Experiments': [_find_experiments_page]}

if 'selected_experiments' in st.session_state:
    BiolectorState.init(st.session_state['selected_experiments'], BiolectorStateMode.MULTIPLE_PLATES)

if BiolectorState.is_init():
    st.markdown(
        f"""
            <style>
                section[data-testid="stSidebar"] {{
                    width: 420px !important; /* Set the width to your desired value */
                    min-width: 420px !important; /* Prevents resizing */
                }}
            </style>
            """,
        unsafe_allow_html=True,
    )

    if not [f for f in BiolectorState.get_filters_list() if "biomass" in f.lower()]:
        analysis_pages = [_tables_page, _plots_page]
    else:
        analysis_pages = [_tables_page, _plots_page, _analysis_page]
    pages['Analysis'] = analysis_pages

    well_data = BiolectorState.get_well_data_description()
    if 'A01' not in well_data:
        # Add {} for A01 to B0 + COLS
        for letter in "AB":
            for col in range(1, COLS + 1):
                well = f"{letter}{col:02d}"
                if well not in well_data:
                    well_data[well] = {}

    with st.sidebar:
        # Assign colors
        label_colors = {"wellbt": "#F991C3", "wellbt-disabled": "#E0E0E0"}

        # Create css code
        css_template = """
            div[class*="st-key-{label}"] .stButton button {{
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
        active = """ button:active {
                    position:relative;
                    top:1px;
                    }"""
        st.html(f"<style>{css_code} {active} </style>")

        wells = [[f"{chr(65 + row)}{col + 1:02d}" for col in range(COLS)] for row in range(ROWS)]

        cols_header = st.columns(COLS + 1)
        for col in range(COLS):
            if cols_header[col + 1].button(str(col + 1), key=f"wellbt-col_{col + 1}"):
                if col + 1 in BiolectorState.get_selected_cols():
                    BiolectorState.remove_selected_col(col + 1)
                    for row in range(ROWS):
                        well = wells[row][col]
                        if well_data[well] != {}:
                            if well in BiolectorState.get_wells_clicked():
                                BiolectorState.remove_well_clicked(well)
                else:
                    BiolectorState.append_selected_col(col + 1)
                    for row in range(ROWS):
                        well = wells[row][col]
                        if well_data[well] != {}:
                            if well not in BiolectorState.get_wells_clicked():
                                BiolectorState.append_well_clicked(well)
                st.rerun(scope="app")

        replicated_wells_show = set()
        for well in BiolectorState.get_replicated_wells_show():
            replicated_wells_show.add(well.split('_')[0])
        replicated_wells_show = list(replicated_wells_show)

        for row in range(ROWS):
            cols_object = st.columns(COLS + 1)
            # Row header button
            if cols_object[0].button(chr(65 + row), key=f"wellbt-row_{chr(65 + row)}"):
                if chr(65 + row) in BiolectorState.get_selected_rows():
                    BiolectorState.remove_selected_row(chr(65 + row))
                    for col in range(COLS):
                        well = wells[row][col]
                        if well_data[well] != {}:
                            if well in BiolectorState.get_wells_clicked():
                                BiolectorState.remove_well_clicked(well)
                else:
                    BiolectorState.append_selected_row(chr(65 + row))
                    for col in range(COLS):
                        well = wells[row][col]
                        if well_data[well] != {}:
                            if well not in BiolectorState.get_wells_clicked():
                                BiolectorState.append_well_clicked(well)
                st.rerun(scope="app")

            for col in range(COLS):
                well = wells[row][col]
                key = f"wellbt-{well}-button" if well_data[well] != {} else f"wellbt-disabled-{well}-button"
                if well_data[well] == {}:
                    cols_object[col+1].button(f":gray[{well}]", key=key, help="No data available", disabled=True)
                elif well in BiolectorState.get_wells_clicked():
                    if cols_object[col + 1].button(f":green[{well}]", key=key,
                                                   help=get_well_data_help_tab(well_data[well])):
                        if well in BiolectorState.get_wells_clicked():
                            BiolectorState.remove_well_clicked(well)
                            st.rerun(scope="app")
                elif well in replicated_wells_show:
                    if cols_object[col+1].button(f"**{well}**", key=key, help=get_well_data_help_tab(well_data[well])):
                        BiolectorState.append_well_clicked(well)
                        st.rerun(scope="app")
                else:
                    if cols_object[col+1].button(f"{well}", key=key, help=get_well_data_help_tab(well_data[well])):
                        BiolectorState.append_well_clicked(well)
                        st.rerun(scope="app")

pg = st.navigation(pages)
pg.run()
