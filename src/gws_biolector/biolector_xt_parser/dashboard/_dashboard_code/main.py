import plotly.express as px
import streamlit as st
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
    tab_table, tab_plot = st.tabs(["Table", "Plot"])

    with tab_table:
        filters = microplate_object.get_filter_name()
        selected_filters = st.multiselect('$\\text{\large{Sélectionnez les observateurs à afficher}}$', filters, default=filters, key = "table_filters")
        #Select wells : all by default; otherwise those selected in the microplate
        selected_wells = st.selectbox('$\\text{\large{Sélectionnez les puits à afficher}}$',["Tous", "Sélection sur la plaque de puits"], index = 0, key = "table_wells")
        if selected_wells == "Sélection sur la plaque de puits":
            st.write(f"L'ensemble des puits cliqués sont : {st.session_state['well_clicked']}")
        for filter in selected_filters :
            st.write(f"$\\text{{\Large{{{filter}}}}}$")
            df = microplate.get_table_by_filter(filter)
            if selected_wells == "Sélection sur la plaque de puits":
                df = df[["time", "Temps_en_h"] + st.session_state['well_clicked']] #TODO: voir si il faut les classer par ordre croissant ?
            st.dataframe(df.style.format(thousands=" ", precision=4))


    with tab_plot:
        selected_filters = st.multiselect('$\\text{\large{Sélectionnez les observateurs à afficher}}$', filters, default=filters, key = "plot_filters")
        #Select wells : all by default; otherwise those selected in the microplate
        selected_wells = st.selectbox('$\\text{\large{Sélectionnez les puits à afficher}}$',["Tous", "Sélection sur la plaque de puits"], index = 0, key = "plot_wells")
        if selected_wells == "Sélection sur la plaque de puits":
            st.write(f"L'ensemble des puits cliqués sont : {st.session_state['well_clicked']}")
        # Création d'une figure Plotly vide pour ajouter toutes les courbes
        fig = px.line()
        for filter in selected_filters :
            df = microplate.get_table_by_filter(filter)
            df = df.iloc[:, 1:]
            if selected_wells == "Sélection sur la plaque de puits":
                df = df[["Temps_en_h"] + st.session_state['well_clicked']] #TODO: voir si il faut les classer par ordre croissant ?
            cols_y = [col for col in df.columns if col != 'Temps_en_h']
            # Ajout des courbes à la figure pour chaque filtre
            for col in cols_y:
                fig.add_scatter(x=df['Temps_en_h'], y=df[col], mode='lines', name=f"{filter} - {col}")
        selected_filters_str = ', '.join(selected_filters)
        fig.update_layout(title=f'Graphique des {selected_filters_str}', xaxis_title='Temps (heures)', yaxis_title=f'{selected_filters_str}')
        # Show the plot
        st.plotly_chart(fig)


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
    st.write("Microplate")
    with stylable_container(key="well_button", css_styles = """
        button{
            display: inline-block;
            width: 44px;  /* Adjust width and height as needed */
            height: 44px;
            border-radius: 50%;  /* Make it circular */
            background-color: #AD9393;  /* Button color */
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
        well_data = {f"{chr(65 + row)}{col + 1:02d}": f"{5 + row + col} ml" for row in range(ROWS) for col in range(COLS)}  #TODO: récup les vraies infos des puits
        well_clicked = []

        # Loop over the wells and create a grid of buttons
        for row in range(ROWS):
            cols_object = st.columns(COLS)
            for col in range(8):
                well = wells[row][col]

                # Check if the well should be crossed out
                if well in crossed_out_wells:
                    cols_object[col].markdown(f"<p style='text-align:center;'><font size='3.2'>  ❌{well}  </font></p>", unsafe_allow_html=True)
                else:
                    if cols_object[col].button(well, key=well, help=f"Volume: {well_data[well]}"):
                        # Save the clicked well to session state: remove or add
                        if well in st.session_state['well_clicked']:
                            st.session_state['well_clicked'].remove(well)
                        else:
                            st.session_state['well_clicked'].append(well)

        st.write(f"L'ensemble des puits cliqués sont : {st.session_state['well_clicked']}")



    # Add the reset button
    if st.button("Reset Wells"):
        st.session_state['well_clicked'] = []
        #st.experimental_rerun()
        st.rerun()

show_content(microplate_object = microplate)
