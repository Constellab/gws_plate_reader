import os
import json
import streamlit as st
import pandas as pd
from streamlit_extras.stylable_container import stylable_container
from gws_core import File, ResourceOrigin, ResourceModel, Settings, FrontService, JSONImporter
# thoses variable will be set by the streamlit app
# don't initialize them, there are create to avoid errors in the IDE
sources: list
params: dict

# Initialize session state variable
if "success_message" not in st.session_state:
    st.session_state["success_message"] = None

def reset_wells():
    st.session_state['well_clicked'] = []

# Function to display success message after rerun
def show_success_message():
    if st.session_state["success_message"]:
        st.success(st.session_state["success_message"])
        # Clear message after displaying
        st.session_state["success_message"] = None

def show_content():

    # Create tabs
    tab_dict, tab_plate_layout = st.tabs(["Dict", "Plate Layout"])

    with tab_dict:
        st.header("Fill data")

        length_diff = len(st.session_state.compounds) - \
            len(st.session_state.dilutions)
        # Add None to the shorter list
        if length_diff > 0:  # Compounds list is longer
            st.session_state.dilutions.extend([None] * length_diff)
        elif length_diff < 0:  # Dilutions list is longer
            st.session_state.compounds.extend([None] * abs(length_diff))

        # Create the dataframe
        dict_df = pd.DataFrame(columns=["Compounds", "Dilutions"])
        dict_df["Compounds"] = st.session_state.compounds
        dict_df["Dilutions"] = st.session_state.dilutions
        dict_df["Compounds"] = dict_df["Compounds"].fillna('').astype('str')
        dict_df["Dilutions"] = dict_df["Dilutions"].fillna('').astype('str')

        edited_dict_df = st.data_editor(
            dict_df, use_container_width=True, hide_index=True, num_rows="dynamic")

        if st.button("Save data", icon = ":material/save:"):
            st.session_state['compounds'] = edited_dict_df["Compounds"].to_list()
            st.session_state['dilutions'] = edited_dict_df["Dilutions"].to_list()
            file_dict_compounds_path = os.path.join(
                folder_data, "compounds.json")
            with open(file_dict_compounds_path, "w") as json_file:
                json.dump(st.session_state.compounds, json_file, indent=4)

            file_dict_dilutions_path = os.path.join(
                folder_data, "dilutions.json")
            with open(file_dict_dilutions_path, "w") as json_file:
                json.dump(st.session_state.dilutions, json_file, indent=4)

            st.success("Information saved successfully! ✅")

    with tab_plate_layout:
        # Add the button to generate plate layout
        if st.button("Generate plate layout ressource", icon=":material/note_add:"):
            path_temp = os.path.join(os.path.abspath(
                os.path.dirname(__file__)), Settings.make_temp_dir())
            full_path = os.path.join(path_temp, f"Plate_layout.json")
            plate_layout: File = File(full_path)
            # Convert dict to JSON string
            json_str = json.dumps(st.session_state['plate_layout'], indent=4)
            plate_layout.write(json_str)
            # Import the resource as JSONDict
            plate_layout_json_dict = JSONImporter.call(plate_layout)
            plate_layout_resource = ResourceModel.save_from_resource(
                plate_layout_json_dict, ResourceOrigin.UPLOADED, flagged=True)
            st.success(
                f"Resource created! ✅ You can find it here : {FrontService.get_resource_url(plate_layout_resource.id)}")
        if not st.session_state['compounds'] and not st.session_state['dilutions']:
            st.warning("Please fill in at least one compound or dilution")
        else:
            if st.session_state['well_clicked']:
                st.write(
                    f"Fill informations for {', '.join(st.session_state['well_clicked'])}:")

                # Compound and dilution selection
                selected_compound = st.selectbox(
                    label="Compound", options=st.session_state['compounds'], placeholder="Choose an option", index=None)
                selected_dilution = st.selectbox(
                    label="Dilution", options=st.session_state['dilutions'], placeholder="Choose an option", index=None)

                # Save information for selected wells
                if st.button("Save these informations", icon = ":material/save:"):
                    if selected_compound is not None or selected_dilution is not None:
                        for well in st.session_state['well_clicked']:
                            if well not in st.session_state['plate_layout']:
                                st.session_state['plate_layout'][well] = {}
                        if selected_compound is not None:
                            for well in st.session_state['well_clicked']:
                                st.session_state['plate_layout'][well]["compound"] = selected_compound
                        if selected_dilution is not None:
                            for well in st.session_state['well_clicked']:
                                st.session_state['plate_layout'][well]["dilution"] = selected_dilution

                    # Save the plate layout to a JSON file
                    file_plate_layout_path = os.path.join(
                        folder_data, "plate_layout.json")
                    os.makedirs(os.path.dirname(file_plate_layout_path),
                                exist_ok=True)  # Ensure directory exists
                    with open(file_plate_layout_path, "w") as json_file:
                        json.dump(
                            st.session_state['plate_layout'], json_file, indent=4)

                    st.session_state["success_message"] = "Information saved successfully! ✅"
                    st.rerun()
                show_success_message()  # Show success message if it exists

                if any(well in st.session_state['plate_layout'] for well in st.session_state['well_clicked']):
                    # Remove information for selected wells
                    if st.button(f"**:red[Remove saved information]**", icon = ":material/delete:", key = "remove_button"):
                        for well in st.session_state['well_clicked']:
                            if well in st.session_state['plate_layout']:
                                st.session_state['plate_layout'].pop(well, None)

                        # Save the plate layout to a JSON file
                        file_plate_layout_path = os.path.join(
                            folder_data, "plate_layout.json")
                        os.makedirs(os.path.dirname(file_plate_layout_path),
                                    exist_ok=True)  # Ensure directory exists
                        with open(file_plate_layout_path, "w") as json_file:
                            json.dump(
                                st.session_state['plate_layout'], json_file, indent=4)

                        st.session_state["success_message"] = "Information saved successfully! ✅"
                        st.rerun()

            else:
                st.warning("Please select one well at least.")


# -------------------------------------------------------------------------------------------#
if not sources:
    raise Exception("Source paths are not provided.")

folder_data = sources[0].path
if len(sources)>1:
    existing_plate_layout = sources[1].get_data()
else :
    existing_plate_layout = None
number_wells = params["number_wells"]

def validate_plate_layout(existing_plate_layout, number_wells):
    if number_wells == 48:
        invalid_letters = {'G', 'H'}
        invalid_numbers = {'9', '10', '11', '12'}

        for well in existing_plate_layout.keys():
            letter, number = well[0], well[1:]

            if letter in invalid_letters or number in invalid_numbers:
                raise ValueError(f"Invalid well detected: {well}. Please verify that your plate layout correspond to the number of wells you entered in parameters")

    return True


# Initialize the session state for clicked wells if it doesn't exist
if 'well_clicked' not in st.session_state:
    st.session_state['well_clicked'] = []

files_compounds = [f for f in os.listdir(
    folder_data) if f.endswith("compounds.json")]
if files_compounds:
    # Load the file and display its contents
    file_path = os.path.join(folder_data, files_compounds[0])
    with open(file_path, "r") as f:
        st.session_state.compounds = json.load(f)
else:
    # Create a dictionary to store  data
    if 'compounds' not in st.session_state:
        st.session_state['compounds'] = []

files_dilutions = [f for f in os.listdir(
    folder_data) if f.endswith("dilutions.json")]
if files_dilutions:
    file_path = os.path.join(folder_data, files_dilutions[0])
    with open(file_path, "r") as f:
        st.session_state.dilutions = json.load(f)
else:
    # Create a dictionary to store  data
    if 'dilutions' not in st.session_state:
        st.session_state['dilutions'] = []

files_plate_layout = [f for f in os.listdir(
    folder_data) if f.endswith("plate_layout.json")]
if files_plate_layout:
    # Load the file and display its contents
    file_path_plate_layout = os.path.join(folder_data, files_plate_layout[0])
    with open(file_path_plate_layout, "r") as f:
        st.session_state.plate_layout = json.load(f)
#If is the first execution and there is an existing plate layout given in input, then we load it
elif existing_plate_layout:
    #check if the existing_plate_layout have the same size than the number entered in the parameters of the task
    try:
        validate_plate_layout(existing_plate_layout, number_wells)
    except ValueError as e:
        st.write(e)
    st.session_state.plate_layout = existing_plate_layout

    #Retrieve unique compounds and dilutions
    # Extract unique values while handling missing keys
    unique_compounds = list({v.get("compound") for v in st.session_state.plate_layout.values() if "compound" in v})
    unique_dilutions = list({v.get("dilution") for v in st.session_state.plate_layout.values() if "dilution" in v})
    st.session_state['compounds'] = unique_compounds
    st.session_state['dilutions'] = unique_dilutions
else:
    if "plate_layout" not in st.session_state:
        st.session_state["plate_layout"] = {}

# Session state to track selected rows/columns
if "selected_rows" not in st.session_state:
    st.session_state.selected_rows = []
if "selected_cols" not in st.session_state:
    st.session_state.selected_cols = []

if number_wells == 96:
    # Define the structure of the 96-well microplate
    ROWS = 8
    COLS = 12
    size_sidebar = 600
    size_button = 42
    font_size = 4
elif number_wells == 48:
    # Define the structure of the 48-well microplate
    ROWS = 6
    COLS = 8
    size_sidebar = 450
    size_button = 44
    font_size = 8


# Inject custom CSS to set the width of the sidebar
st.markdown(
    f"""
    <style>
        section[data-testid="stSidebar"] {{
            width: {size_sidebar}px !important; /* Set the width to your desired value */
            min-width: {size_sidebar}px !important; /* Prevents resizing */
        }}
    </style>
    """,
    unsafe_allow_html=True,
)


with st.sidebar:
    @st.fragment
    def fragment_sidebar_function():
        st.write("Microplate")
        with stylable_container(key="well_button", css_styles=f"""
            button{{
                display: inline-block;
                width: {size_button}px;  /* Adjust width and height as needed */
                height: {size_button}px;
                border-radius: 50%;  /* Make it circular */
                background-color: #eb969d;  /* Button color */
                color: black;  /* Text color */
                text-align: center;
                line-height: {size_button}px;  /* Center text vertically */
                font-size: {font_size}px;  /* Text size */
                padding: 0;  /* Remove padding to avoid extra space */
                margin: 0;
                cursor: pointer;
                text-decoration: none;  /* Remove underline */
                }}
            button:active {{
                position:relative;
                top:1px;
                }}
                """,):

            # Define the structure of the microplate
            wells = [[f"{chr(65 + row)}{col + 1}" for col in range(COLS)]
                     for row in range(ROWS)]

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
                cols_object = st.columns(COLS + 1)
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
                        if well in st.session_state['plate_layout'] and st.session_state['plate_layout'][well].get("compound") and st.session_state['plate_layout'][well].get("dilution"):
                            if cols_object[col+1].button(f":green[{well}] ✓", key=well, help=json.dumps(st.session_state['plate_layout'][well], sort_keys=True, indent=4, ensure_ascii=False)):
                                st.session_state['well_clicked'].remove(well)
                                st.rerun(scope="app")
                        elif well in st.session_state['plate_layout']:
                            if cols_object[col+1].button(f":green[{well}]", key=well, help=json.dumps(st.session_state['plate_layout'][well], sort_keys=True, indent=4, ensure_ascii=False)):
                                st.session_state['well_clicked'].remove(well)
                                st.rerun(scope="app")
                        else:
                            if cols_object[col+1].button(f"**:green[{well}]**", key=well):
                                st.session_state['well_clicked'].remove(well)
                                st.rerun(scope="app")
                    else:
                        if well in st.session_state['plate_layout'] and st.session_state['plate_layout'][well].get("compound") and st.session_state['plate_layout'][well].get("dilution"):
                            if cols_object[col+1].button(f"{well} ✓", key=well, help=json.dumps(st.session_state['plate_layout'][well], sort_keys=True, indent=4, ensure_ascii=False)):
                                st.session_state['well_clicked'].append(well)
                                st.rerun(scope="app")
                        elif well in st.session_state['plate_layout']:
                            if cols_object[col+1].button(well, key=well, help=json.dumps(st.session_state['plate_layout'][well], sort_keys=True, indent=4, ensure_ascii=False)):
                                st.session_state['well_clicked'].append(well)
                                st.rerun(scope="app")
                        else:
                            if cols_object[col+1].button(f"**{well}**", key=well):
                                st.session_state['well_clicked'].append(well)
                                st.rerun(scope="app")

            st.write(
                f"All the wells clicked are: {', '.join(st.session_state['well_clicked'])}")

    fragment_sidebar_function()

    # Add the reset button
    st.button("Reset wells selection", on_click=reset_wells)

show_content()
