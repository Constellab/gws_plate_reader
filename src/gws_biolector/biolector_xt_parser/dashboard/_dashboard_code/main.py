from typing import List
import plotly.express as px
import streamlit as st #TODO : j'ai du l'updater vers la version 1.39
from gws_biolector.biolector_xt_parser.biolectorxt_parser import BiolectorXTParser
from streamlit_extras.stylable_container import stylable_container

# thoses variable will be set by the streamlit app
# don't initialize them, there are create to avoid errors in the IDE
sources: list
params: dict

# Your Streamlit app code here
st.title("Microplate Dashboard")


def show_content(microplate_object : BiolectorXTParser):

    #Create tabs
    tab_table, tab_plot, tab_analysis = st.tabs(["Table", "Plot", "Analysis"])

    with tab_table:
        filters = microplate_object.get_filter_name()
        selected_filters : List[str] = st.multiselect('$\\text{\large{Sélectionnez les observateurs à afficher}}$', filters, default=filters, key = "table_filters")
        #Select wells : all by default; otherwise those selected in the microplate
        selected_wells = st.selectbox('$\\text{\large{Sélectionnez les puits à afficher}}$',["Tous", "Sélection sur la plaque de puits"], index = 0, key = "table_wells")
        if selected_wells == "Sélection sur la plaque de puits":
            st.write(f"L'ensemble des puits cliqués sont : {st.session_state['well_clicked']}")
        for filter_selection in selected_filters :
            st.write(f"$\\text{{\Large{{{filter_selection}}}}}$")
            df = microplate.get_table_by_filter(filter_selection)
            if selected_wells == "Sélection sur la plaque de puits":
                df = df[["time", "Temps_en_h"] + st.session_state['well_clicked']] #TODO: voir si il faut les classer par ordre croissant ?
            st.dataframe(df.style.format(thousands=" ", precision=4))


    with tab_plot:
        legend_mean = ""
        selected_filters = st.multiselect('$\\text{\large{Sélectionnez les observateurs à afficher}}$', filters, default=filters, key = "plot_filters")
        #Select wells : all by default; otherwise those selected in the microplate
        selected_wells = st.selectbox('$\\text{\large{Sélectionnez les puits à afficher}}$',["Tous", "Sélection sur la plaque de puits"], index = 0, key = "plot_wells")
        if selected_wells == "Sélection sur la plaque de puits":
            st.write(f"L'ensemble des puits cliqués sont : {st.session_state['well_clicked']}")
        selected_time = st.selectbox("$\\text{\large{Sélectionnez l'unité de temps}}$",["Heures", "Minutes", "Secondes"], index = 0, key = "plot_time")
        selected_mode = st.selectbox("$\\text{\large{Sélectionnez le mode d'affichage}}$",["Courbes individuelles", "Moyenne des puits sélectionnés"], index = 0, key = "plot_mode")

        # Create an empty Plotly figure to add all the curves
        fig = px.line()
        for filter in selected_filters :
            df = microplate.get_table_by_filter(filter)
            df = df.iloc[:, 1:]
            if selected_wells == "Sélection sur la plaque de puits":
                df = df[["Temps_en_h"] + st.session_state['well_clicked']] #TODO: voir si il faut les classer par ordre croissant ?
            cols_y = [col for col in df.columns if col != 'Temps_en_h']
            #Adapt unit of time
            if selected_time == "Heures":
                df["time"] = df["Temps_en_h"]
            elif selected_time == "Minutes":
                df["time"] = df["Temps_en_h"]*60
            elif selected_time == "Secondes":
                df["time"] = df["Temps_en_h"]*3600
            if selected_mode == "Courbes individuelles":
                # Adding curves to the figure for each filter
                for col in cols_y:
                    fig.add_scatter(x=df['time'], y=df[col], mode='lines', name=f"{filter} - {col}", line= {'shape': 'spline', 'smoothing': 1})
            elif selected_mode == "Moyenne des puits sélectionnés":
                legend_mean = f"(Moyenne de {st.session_state['well_clicked']})"
                df_mean = df[cols_y].mean(axis = 1)
                fig.add_scatter(x=df['time'], y=df_mean, mode='lines', name=f"{filter} - moyenne", line= {'shape': 'spline', 'smoothing': 1})

        selected_filters_str = ', '.join(selected_filters)
        fig.update_layout(title=f'Graphique des {selected_filters_str} {legend_mean}', xaxis_title=f'Temps ({selected_time})', yaxis_title=f'{selected_filters_str}')
        # Show the plot
        st.plotly_chart(fig)


    with tab_analysis:
        st.write("Analysis")

#-------------------------------------------------------------------------------------------#

if not sources:
    raise Exception("Source paths are not provided.")

raw_data = sources[0]
folder_metadata = sources[1]
microplate = BiolectorXTParser(data_file = raw_data, metadata_folder = folder_metadata)

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
        with stylable_container(key="well_button", css_styles = """
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
                crossed_out_wells = [f"{chr(65 + row)}{col + 1:02d}" for row in range(2) for col in range(8)]  # A01-B08 crossed out

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
                        cols_object[col].button(f":gray[{well}]", key=well, help=well_data[well], disabled = True)
                        #cols_object[col].markdown(f"<p style='text-align:center;'><font size='3.2'>  ❌{well}  </font></p>", unsafe_allow_html=True)
                    elif well in st.session_state['well_clicked']:
                        if cols_object[col].button(f"**:green[{well}]**", key=well, help = well_data[well]):
                            st.session_state['well_clicked'].remove(well)
                            st.rerun(scope="app")
                    else:
                        if cols_object[col].button(well, key=well, help=well_data[well]):
                            st.session_state['well_clicked'].append(well)
                            st.rerun(scope="app")

            st.write(f"L'ensemble des puits cliqués sont : {st.session_state['well_clicked']}")

    fragment_sidebar_function()

    def reset_wells():
        st.session_state['well_clicked'] = []
    # Add the reset button
    st.button("Reset Wells", on_click=reset_wells)

show_content(microplate_object = microplate)
