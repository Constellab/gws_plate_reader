import os
import json
import streamlit as st
import pandas as pd
from streamlit_extras.stylable_container import stylable_container
from gws_plate_reader.dashboard_plate_layout.plate_layout_state import PlateLayoutState
from gws_core import File, ResourceOrigin, ResourceModel, Settings, FrontService, JSONImporter, TagService, EntityTagList, TagList
from gws_core import TagService, TagKeyModel, TagValueModel, Tag
from typing import Optional, Tuple

# thoses variable will be set by the streamlit app
# don't initialize them, there are create to avoid errors in the IDE
sources: list
params: dict

def key_tag_selector() -> Optional[Tuple[str, any]]:
    """Simple tag key selector that returns (key, value) tuple"""

    # Get all tag keys
    tag_service = TagService()
    all_tag_keys = tag_service.get_all_tags()

    if not all_tag_keys:
        st.warning("No tags found in the lab. Please create some tags first.")
        return None

    # Select tag key
    tag_key_options = {tag.key: f"{tag.label}" for tag in all_tag_keys}

    selected_keys = st.multiselect(
        "Select tag(s):",
        options=list(tag_key_options.keys()),
        default=list(st.session_state['selected_key_tags'].keys()) if st.session_state['selected_key_tags'] else [],
        format_func=lambda x: tag_key_options[x],
        placeholder="Choose at least a tag...",
        on_change=save_selected_keys,
        args=(tag_key_options,),
        key="multiselect_tag_keys"
    )

    if not selected_keys:
        return None

    # Return dictionary format {key: label}
    return {key: tag_key_options[key] for key in selected_keys}


def save_selected_keys(tag_key_options : dict):
    selected_key_tags = {key: tag_key_options[key] for key in st.session_state.get('multiselect_tag_keys')}
    # Store in session state
    st.session_state['selected_key_tags'] = selected_key_tags

    # Save the selected keys to keys.json
    file_dict_keys_path = os.path.join(
        folder_data, "keys.json")
    with open(file_dict_keys_path, "w") as json_file:
        json.dump(st.session_state['selected_key_tags'], json_file, indent=4)

plate_layout_state = PlateLayoutState()

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
        st.header("Select tag(s)")

        selected_key_tags = key_tag_selector()

        """if selected_key_tags:
            # Store in session state
            st.session_state['selected_key_tags'] = selected_key_tags"""


    with tab_plate_layout:
        # Add the button to generate plate layout ressource
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
        if not st.session_state['selected_key_tags']:
            st.warning("Please select at least one key")
        else:
            if st.session_state['well_clicked']:
                st.write(
                    f"Fill informations for {', '.join(st.session_state['well_clicked'])}:")

                # Add selector for each key
                set_selected_key = []
                for key, value in st.session_state['selected_key_tags'].items():
                    # Get values for selected key
                    tag_values = list(TagValueModel.select().where(TagValueModel.tag_key == key))

                    if tag_values:
                        # Select from existing values
                        values = [tv.get_tag_value() for tv in tag_values]
                        selected_key = st.selectbox(
                            label=value, options=values, placeholder="Choose an option", index=None, key=f"select_{key}")
                        set_selected_key.append((selected_key, value))


                # Save information for selected wells
                if st.button("Save these informations", icon = ":material/save:"):
                    for selected_key, value in set_selected_key:
                        for well in st.session_state['well_clicked']:
                            if well not in st.session_state['plate_layout']:
                                st.session_state['plate_layout'][well] = {}
                            # Save the value (even if None/empty)
                            st.session_state['plate_layout'][well][value] = selected_key if selected_key is not None else ""

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
# Retrieve existing plate layout if provided
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


files_keys = [f for f in os.listdir(
    folder_data) if f.endswith("keys.json")]

if files_keys:
    # Load the file and display its contents
    file_path = os.path.join(folder_data, files_keys[0])
    with open(file_path, "r") as f:
        st.session_state.selected_key_tags = json.load(f)
else:
    # Create a dictionary to store  data
    if 'selected_key_tags' not in st.session_state:
        st.session_state['selected_key_tags'] = {}

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

    # Retrieve keys from the existing plate layout and get their labels
    existing_keys = {}
    tag_service = TagService()
    all_tag_keys = tag_service.get_all_tags()
    tag_key_options = {tag.key: f"{tag.label}" for tag in all_tag_keys}

    for well_name, well_data in st.session_state.plate_layout.items():
        for key in well_data.keys():
            if key not in existing_keys and key in tag_key_options:
                existing_keys[key] = tag_key_options[key]

    st.session_state['selected_key_tags'].update(existing_keys)
    # Save the selected keys to keys.json
    file_dict_keys_path = os.path.join(
        folder_data, "keys.json")
    with open(file_dict_keys_path, "w") as json_file:
        json.dump(st.session_state['selected_key_tags'], json_file, indent=4)

    # Save the plate layout to a JSON file
    file_plate_layout_path = os.path.join(
        folder_data, "plate_layout.json")
    os.makedirs(os.path.dirname(file_plate_layout_path),
                exist_ok=True)  # Ensure directory exists
    with open(file_plate_layout_path, "w") as json_file:
        json.dump(
            st.session_state['plate_layout'], json_file, indent=4)

else:
    if "plate_layout" not in st.session_state:
        st.session_state["plate_layout"] = {}

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
                    # Dynamically create tooltip text from the st.session_state['plate_layout'] dictionary
                    if well in st.session_state['plate_layout']:
                        sorted_items = sorted(st.session_state['plate_layout'][well].items())
                        help_tab =  "| Property | Value |\n|----------|-------|\n" + "\n".join(
                                    [f"| **{key}** | {value} |" for key, value in sorted_items])
                    else:
                        help_tab = "No data available"

                    if well in st.session_state['well_clicked']:
                        if well in st.session_state['plate_layout'] and st.session_state['plate_layout'][well].get("compound") and st.session_state['plate_layout'][well].get("dilution"):
                            if cols_object[col+1].button(f":green[{well}] ✓", key=well, help=help_tab):
                                st.session_state['well_clicked'].remove(well)
                                st.rerun(scope="app")
                        elif well in st.session_state['plate_layout']:
                            if cols_object[col+1].button(f":green[{well}]", key=well, help=help_tab):
                                st.session_state['well_clicked'].remove(well)
                                st.rerun(scope="app")
                        else:
                            if cols_object[col+1].button(f"**:green[{well}]**", key=well):
                                st.session_state['well_clicked'].remove(well)
                                st.rerun(scope="app")
                    else:
                        if well in st.session_state['plate_layout'] and st.session_state['plate_layout'][well].get("compound") and st.session_state['plate_layout'][well].get("dilution"):
                            if cols_object[col+1].button(f"{well} ✓", key=well, help=help_tab):
                                st.session_state['well_clicked'].append(well)
                                st.rerun(scope="app")
                        elif well in st.session_state['plate_layout']:
                            if cols_object[col+1].button(well, key=well, help=help_tab):
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
    st.button("Reset wells selection", on_click=plate_layout_state.reset_wells)

show_content()
