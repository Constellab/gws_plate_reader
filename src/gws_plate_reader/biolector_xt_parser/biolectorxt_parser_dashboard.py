

import streamlit as st
from gws_plate_reader.biolector_xt_parser.biolectorxt_parser import \
    BiolectorXTParser
from pandas import DataFrame
from streamlit_extras.stylable_container import stylable_container

from .analysis_tab import render_analysis_tab
from .plot_tab import render_plot_tab
from .table_tab import render_table_tab


def show_content(microplate_object: BiolectorXTParser):

    filters = microplate_object.get_filter_name()

    def render_table_page():
        render_table_tab(microplate_object, filters)

    def render_plot_page():
        render_plot_tab(microplate_object, filters)

    def render_analysis_page():
        render_analysis_tab(microplate_object, filters)

    tables_page = st.Page(render_table_page, title='Tables', url_path='tables', icon='📄')
    plots_page = st.Page(render_plot_page, title='Plots', url_path='plots', icon='📈')
    analysis_page = st.Page(render_analysis_page, title='Analysis', url_path='protocols', icon='🔍')

    pg = st.navigation([tables_page, plots_page, analysis_page])

    pg.run()


def reset_wells():
    st.session_state['well_clicked'] = []


def run(raw_data: DataFrame, metadata: dict):

    microplate = BiolectorXTParser(data=raw_data, metadata=metadata)

    # Initialize the session state for clicked wells if it doesn't exist
    if 'well_clicked' not in st.session_state:
        st.session_state['well_clicked'] = []

    # Session state to track selected rows/columns
    if "selected_rows" not in st.session_state:
        st.session_state.selected_rows = []
    if "selected_cols" not in st.session_state:
        st.session_state.selected_cols = []

    # Inject custom CSS to set the width of the sidebar
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

    with st.sidebar:
        @st.fragment
        def fragment_sidebar_function():
            st.write("Microplate")
            with stylable_container(key="well_button", css_styles="""
                button{
                    display: inline-block;
                    width: 41px;  /* Adjust width and height as needed */
                    height: 41px;
                    border-radius: 50%;  /* Make it circular */
                    background-color: #eb969d;  /* Button color */
                    color: black;  /* Text color */
                    text-align: center;
                    line-height: 41px;  /* Center text vertically */
                    font-size: 4px;  /* Text size */
                    padding: 0;  /* Remove padding to avoid extra space */
                    margin: 0;
                    cursor: pointer;
                    text-decoration: none;  /* Remove underline */
                    }
                button:active {
                    position:relative;
                    top:1px;
                    }
                    """,):

                # Define the structure of the 48-well microplate
                ROWS = 6
                COLS = 8
                crossed_out_wells = []
                if microplate.is_microfluidics():
                    crossed_out_wells = [f"{chr(65 + row)}{col + 1:02d}" for row in range(2)
                                         for col in range(8)]  # A01-B08 crossed out

                # Define the structure of the 48-well microplate
                wells = [[f"{chr(65 + row)}{col + 1:02d}" for col in range(COLS)] for row in range(ROWS)]
                # Define well data (e.g., volume information for each well)
                well_data = microplate.get_wells_label_description()

                # Column header buttons
                cols_header = st.columns(COLS + 1)
                for col in range(COLS):
                    if cols_header[col + 1].button(str(col + 1), key=f"col_{col + 1}"):
                        if col + 1 in st.session_state.selected_cols:
                            st.session_state.selected_cols.remove(col + 1)
                            for row in range(ROWS):
                                well = wells[row][col]
                                if well not in crossed_out_wells:
                                    if well in st.session_state['well_clicked']:
                                        st.session_state['well_clicked'].remove(well)
                        else:
                            st.session_state.selected_cols.append(col + 1)
                            for row in range(ROWS):
                                well = wells[row][col]
                                if well not in crossed_out_wells:
                                    if well not in st.session_state['well_clicked']:
                                        st.session_state['well_clicked'].append(well)
                        st.rerun(scope="app")

                has_changed = False
                # Loop over the wells and create a grid of buttons
                for row in range(ROWS):
                    cols_object = st.columns(COLS + 1)
                    # Row header button
                    if cols_object[0].button(chr(65 + row), key=f"row_{chr(65 + row)}"):
                        if chr(65 + row) in st.session_state.selected_rows:
                            st.session_state.selected_rows.remove(chr(65 + row))
                            for col in range(COLS):
                                well = wells[row][col]
                                if well not in crossed_out_wells:
                                    if well  in st.session_state['well_clicked']:
                                        st.session_state['well_clicked'].remove(well)
                        else:
                            st.session_state.selected_rows.append(chr(65 + row))
                            for col in range(COLS):
                                well = wells[row][col]
                                if well not in crossed_out_wells:
                                    if well not in st.session_state['well_clicked']:
                                        st.session_state['well_clicked'].append(well)
                        st.rerun(scope="app")

                    for col in range(COLS):
                        well = wells[row][col]

                        # Check if the well should be crossed out
                        if well in crossed_out_wells:
                            cols_object[col+1].button(f":gray[{well}]", key=well, help=well_data[well], disabled=True)
                        elif well in st.session_state['well_clicked']:
                            if cols_object[col+1].button(f"**:green[{well}]**", key=well, help=well_data[well]):
                                st.session_state['well_clicked'].remove(well)
                                has_changed = True
                        else:
                            if cols_object[col+1].button(well, key=well, help=well_data[well]):
                                st.session_state['well_clicked'].append(well)
                                has_changed = True

                if has_changed:
                    # when the selection changes, we rerun the app to update the content
                    st.rerun(scope="app")

                st.write(f"All the wells clicked are: {', '.join(st.session_state['well_clicked'])}")

        fragment_sidebar_function()

        # Add the reset button
        st.button("Reset wells selection", on_click=reset_wells)

    show_content(microplate_object=microplate)
