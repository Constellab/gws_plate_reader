import os
from datetime import datetime
import pytz
import json
import streamlit as st
import pandas as pd
import numpy as np
from gws_core import Table
from gws_plate_reader.tecan.tecan_parser import TecanParser
from streamlit_extras.stylable_container import stylable_container
# thoses variable will be set by the streamlit app
# don't initialize them, there are create to avoid errors in the IDE
sources: list
params: dict


def show_content(microplate: TecanParser):

    # Create tabs
    tab_table, tab_analysis = st.tabs(["Raw data", "Analysis"])

    with tab_table:
        # Select wells : all by default; otherwise those selected in the microplate
        st.header("Plate")
        df = microplate.parse_data()
        # Create an empty DataFrame of the same shape, filled with NaN
        df_filtered = pd.DataFrame(np.nan, index=df.index, columns=df.columns)
        # Check if there are any wells clicked
        if len(st.session_state['well_clicked']) > 0:
            # Loop through the clicked wells and set only those cells in df_filtered
            for well in st.session_state['well_clicked']:
                row = well[0]  # Extract the row letter
                col = well[1:]  # Extract the column number
                # Add value to df_filtered only if the cell is in bounds
                if row in df.index and col in df.columns:
                    df_filtered.loc[row, col] = df.loc[row, col]

            # Remove rows and columns where all values are NaN
            df_filtered = df_filtered.dropna(how="all", axis=0)  # Remove rows
            df_filtered = df_filtered.dropna(how="all", axis=1)  # Remove columns
            df = df_filtered

        # Display the full DataFrame if no wells are clicked
        # st.dataframe(df.style.applymap(lambda _: "background-color: CornflowerBlue;", subset=(["A"], slice(None)))) #TODO : cette ligne peut permettre de mettre de la couleur sur le dataframe pour mettre la couleur du composé par exemple

        # Preprocess the DataFrame to format numbers as strings with desired precision
        formatted_df = df.copy()
        for col in formatted_df.select_dtypes(include="number").columns:  # Apply formatting to numeric columns
            formatted_df[col] = formatted_df[col].apply(lambda x: f"{x:,.2f}".replace(",", " ")) #TODO voir si j'ajoute ça -> permettrait d'avoir un style plus joli mais transforme en string

        # Use the preprocessed DataFrame in st.data_editor
        df = st.data_editor(formatted_df)


        if st.button("Update raw data", use_container_width=False, icon = ":material/save:"):
            # Convert the formatted DataFrame back to floats for numeric columns
            for col in df.select_dtypes(include="object").columns:
                # Remove spaces introduced during formatting and convert back to numeric
                df[col] = df[col].str.replace(" ", "").apply(pd.to_numeric, errors='coerce')
            #Update the data of microplate :
            microplate.update_row_data(df)
            #Save dataframe in the folder
            timestamp = datetime.now(tz=pytz.timezone('Europe/Paris')).strftime(f"raw_data_%Y-%m-%d-%Hh%M.csv")
            path = os.path.join(raw_data_folder, timestamp)
            microplate.parse_data().to_csv(path, index = True)
            st.success("Saved!")
            st.rerun()

        if st.button("Reset changes", use_container_width=False, icon = ":material/restart_alt:"):
            df = original_raw_data.get_data()
            #Update the data of microplate :
            microplate.update_row_data(df)
            #Save dataframe in the folder
            timestamp = datetime.now(tz=pytz.timezone('Europe/Paris')).strftime(f"raw_data_%Y-%m-%d-%Hh%M.csv")
            path = os.path.join(raw_data_folder, timestamp)
            microplate.parse_data().to_csv(path, index = True)
            st.success("Saved!")
            st.rerun()


    with tab_analysis:
        choice_analysis = st.selectbox(label = "Analysis", options = ["Cytotoxicity-bioluminescence"])
        if choice_analysis == "Cytotoxicity-bioluminescence" :
            wells_dict = microplate.enrich_well_metadata()
            mean_untreated = microplate.mean_data_for_compound("untreated")
            if mean_untreated:
                st.write(f"Mean T-: {round(mean_untreated, 2)}")

                # Step 1: Flatten the dictionary into a list of rows
                data_list = [
                    {"Well": well, "Compound": info["compound"], "Dilution": float(info["dilution"]), "Data": round((info["data"]/mean_untreated)*100,2)}
                    for well, info in wells_dict.items() if info["compound"] != "untreated"
                ]
                # Step 2: Create a DataFrame
                df = pd.DataFrame(data_list)
                df_intermediaire = df.pivot_table(index ="Compound", columns="Dilution", values="Data", aggfunc=list)
                # Sort the dilution columns in descending order
                df_intermediaire = df_intermediaire.sort_index(axis=1, ascending=False)
                st.dataframe(df_intermediaire.style.format(thousands=" ", precision=2))

                df_final = df.pivot_table(index ="Compound", columns="Dilution", values="Data", aggfunc="mean")
                # Sort the dilution columns in descending order
                df_final = df_final.sort_index(axis=1, ascending=False)
                st.dataframe(df_final.style.format(thousands=" ", precision=2))




# -------------------------------------------------------------------------------------------#
if not sources:
    raise Exception("Source paths are not provided.")

raw_data = sources[0]
plate_layout_json = sources[1]
raw_data_folder = sources[2].path
original_raw_data = raw_data.clone()
#Save dataframe in the folder
if os.listdir(raw_data_folder):
    raw_data = pd.read_csv(os.path.join(raw_data_folder,sorted(os.listdir(raw_data_folder))[-1]), index_col= 0)
    raw_data = Table(raw_data)
else :
    timestamp = datetime.now(tz=pytz.timezone('Europe/Paris')).strftime(f"raw_data_%Y-%m-%d-%Hh%M.csv")
    path = os.path.join(raw_data_folder, timestamp)
    csv_raw_data = raw_data.get_data().to_csv(path, index = True)

microplate = TecanParser(data_file=raw_data, plate_layout=plate_layout_json)

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
    """
    <style>
        section[data-testid="stSidebar"] {
            width: 600px !important; /* Set the width to your desired value */
            min-width: 600px !important; /* Prevents resizing */
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
                width: 40px;  /* Adjust width and height as needed */
                height: 40px;
                border-radius: 50%;  /* Make it circular */
                background-color: #eb969d;  /* Button color */
                color: black;  /* Text color */
                text-align: center;
                line-height: 40px;  /* Center text vertically */
                font-size: 6px;  /* Text size */
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

            # Define the structure of the 96-well microplate
            ROWS = 8
            COLS = 12

            # Define the structure of the 96-well microplate
            wells = [[f"{chr(65 + row)}{col + 1}" for col in range(COLS)]
                     for row in range(ROWS)]
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
                            if well in st.session_state['well_clicked']:
                                st.session_state['well_clicked'].remove(well)
                    else:
                        st.session_state.selected_cols.append(col + 1)
                        for row in range(ROWS):
                            well = wells[row][col]
                            if well not in st.session_state['well_clicked']:
                                st.session_state['well_clicked'].append(well)
                    st.rerun(scope="app")

            # Loop over the wells and create a grid of buttons
            for row in range(ROWS):
                cols_object = st.columns(COLS + 1 )
                # Row header button
                if cols_object[0].button(chr(65 + row), key=f"row_{chr(65 + row)}"):
                    if chr(65 + row) in st.session_state.selected_rows:
                        st.session_state.selected_rows.remove(chr(65 + row))
                        for col in range(COLS):
                            well = wells[row][col]
                            if well  in st.session_state['well_clicked']:
                                st.session_state['well_clicked'].remove(well)
                    else:
                        st.session_state.selected_rows.append(chr(65 + row))
                        for col in range(COLS):
                            well = wells[row][col]
                            if well not in st.session_state['well_clicked']:
                                st.session_state['well_clicked'].append(well)
                    st.rerun(scope="app")

                for col in range(COLS):
                    well = wells[row][col]

                    if well in st.session_state['well_clicked']:
                        if cols_object[col+1].button(f"**:green[{well}]**", key=well, help=well_data[well]):
                            st.session_state['well_clicked'].remove(well)
                            st.rerun(scope="app")
                    else:
                        if cols_object[col+1].button(well, key=well, help=well_data[well]):
                            st.session_state['well_clicked'].append(well)
                            st.rerun(scope="app")



            st.write(
                f"All the wells clicked are: {', '.join(st.session_state['well_clicked'])}")

    fragment_sidebar_function()

    def reset_wells():
        st.session_state['well_clicked'] = []
    # Add the reset button
    st.button("Reset wells selection", on_click=reset_wells)

show_content(microplate=microplate)
