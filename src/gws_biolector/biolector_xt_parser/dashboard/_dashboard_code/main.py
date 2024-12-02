
import streamlit as st
from analysis_tab import render_analysis_tab, set_run_analysis
from gws_biolector.biolector_xt_parser.biolectorxt_parser import \
    BiolectorXTParser
from plot_tab import render_plot_tab
from streamlit_extras.stylable_container import stylable_container
from table_tab import render_table_tab

# thoses variable will be set by the streamlit app
# don't initialize them, there are create to avoid errors in the IDE
sources: list
params: dict


def show_content(microplate_object: BiolectorXTParser):
    # Create tabs
    tab_table, tab_plot, tab_analysis = st.tabs(["Table", "Plot", "Analysis"])

    filters = microplate_object.get_filter_name()

    with tab_table:
        render_table_tab(microplate_object, filters)

    with tab_plot:
        render_plot_tab(microplate_object, filters)

    with tab_analysis:
        render_analysis_tab(microplate_object, filters, growth_rate_folder)


# -------------------------------------------------------------------------------------------#
if not sources:
    raise Exception("Source paths are not provided.")

raw_data = sources[0]
folder_metadata = sources[1]
growth_rate_folder = sources[2].path
microplate = BiolectorXTParser(data_file=raw_data, metadata_folder=folder_metadata)

# Initialize the session state for clicked wells if it doesn't exist
if 'well_clicked' not in st.session_state:
    st.session_state['well_clicked'] = []

# Inject custom CSS to set the width of the sidebar
st.markdown(
    """
    <style>
        section[data-testid="stSidebar"] {
            width: 400px !important; # Set the width to your desired value
        }
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
                width: 44px;  /* Adjust width and height as needed */
                height: 44px;
                border-radius: 50%;  /* Make it circular */
                background-color: #eb969d;  /* Button color */
                color: black;  /* Text color */
                text-align: center;
                line-height: 44px;  /* Center text vertically */
                font-size: 8px;  /* Text size */
                padding: 0;  /* Remove padding to avoid extra space */
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

            # Loop over the wells and create a grid of buttons
            for row in range(ROWS):
                cols_object = st.columns(COLS)
                for col in range(COLS):
                    well = wells[row][col]

                    # Check if the well should be crossed out
                    if well in crossed_out_wells:
                        cols_object[col].button(f":gray[{well}]", key=well, help=well_data[well], disabled=True)
                    elif well in st.session_state['well_clicked']:
                        if cols_object[col].button(f"**:green[{well}]**", key=well, help=well_data[well]):
                            st.session_state['well_clicked'].remove(well)
                            # when the selection changes, we clear the analysis
                            set_run_analysis(False)
                            st.rerun(scope="app")
                    else:
                        if cols_object[col].button(well, key=well, help=well_data[well]):
                            st.session_state['well_clicked'].append(well)
                            # when the selection changes, we clear the analysis
                            set_run_analysis(False)
                            st.rerun(scope="app")

            st.write(f"All the wells clicked are: {', '.join(st.session_state['well_clicked'])}")

    fragment_sidebar_function()

    def reset_wells():
        st.session_state['well_clicked'] = []
    # Add the reset button
    st.button("Reset Wells", on_click=reset_wells)

show_content(microplate_object=microplate)
