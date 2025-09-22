import os
import json
import streamlit as st
from streamlit_extras.stylable_container import stylable_container
from gws_plate_reader.dashboard_plate_layout.plate_layout_state import PlateLayoutState
from gws_core import File, ResourceOrigin, ResourceModel, Settings, FrontService, JSONImporter, TagService
from gws_core import TagService, TagValueModel
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
        default=list(plate_layout_state.get_selected_key_tags().keys()) if plate_layout_state.get_selected_key_tags() else [],
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
    current_selected = set(plate_layout_state.get_multiselect_tag_keys())
    previous_selected = set(plate_layout_state.get_selected_key_tags().keys())

    # Check for removed keys
    removed_keys = previous_selected - current_selected

    if removed_keys:
        # Check if any removed key has data in wells
        keys_with_data = []
        for key in removed_keys:
            for well_data in plate_layout_state.get_plate_layout().values():
                if key in well_data and isinstance(well_data.get(key), dict): # Check if key exists
                    keys_with_data.append(key)
                    break

        if keys_with_data:
            # Store the removal request for confirmation
            plate_layout_state.set_pending_key_removal({
                'keys': list(removed_keys),
                'keys_with_data': keys_with_data,
                'new_selection': current_selected
            })
            # Revert the multiselect to previous state temporarily
            plate_layout_state.set_multiselect_tag_keys(list(previous_selected))
            return

    # Check for newly added keys
    added_keys = current_selected - previous_selected

    # If no data conflicts, proceed with normal update
    selected_key_tags = {key: tag_key_options[key] for key in current_selected}
    plate_layout_state.set_selected_key_tags(selected_key_tags)

    # Add new keys with empty values to existing wells
    if added_keys and plate_layout_state.get_plate_layout():
        plate_layout = plate_layout_state.get_plate_layout()
        for well_name, well_data in plate_layout.items():
            if well_data:  # Only add to wells that already have some data
                for new_key in added_keys:
                    if new_key not in well_data:
                        well_data[new_key] = {
                            "label": tag_key_options[new_key],
                            "value": ""
                        }

        plate_layout_state.set_plate_layout(plate_layout)

        # Save the updated plate layout
        file_plate_layout_path = os.path.join(folder_data, "plate_layout.json")
        with open(file_plate_layout_path, "w") as json_file:
            json.dump(plate_layout_state.get_plate_layout(), json_file, indent=4)

    # Save the selected keys to keys.json
    file_dict_keys_path = os.path.join(
        folder_data, "keys.json")
    with open(file_dict_keys_path, "w") as json_file:
        json.dump(plate_layout_state.get_selected_key_tags(), json_file, indent=4)

plate_layout_state = PlateLayoutState()

# Function to display success message after rerun
def show_success_message():
    if plate_layout_state.get_success_message():
        st.success(plate_layout_state.get_success_message())
        # Clear message after displaying
        plate_layout_state.set_success_message(None)

@st.dialog("Delete key(s)")
def dialog_delete_keys():
    removal_data = plate_layout_state.get_pending_key_removal()
    keys_with_data = removal_data['keys_with_data']

    st.warning(f"⚠️ The following key(s) have data in wells: **{', '.join(keys_with_data)}**")
    st.write("Do you want to really delete this key? Data related to this key will be deleted.")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("❌ No, keep the key(s)", key="keep_keys"):
            # Revert to previous selection
            plate_layout_state.set_pending_key_removal(None)
            st.rerun()

    with col2:
        if st.button("✅ Yes, delete key(s) and data", key="delete_keys"):
            # Proceed with removal
            removed_keys = removal_data['keys']
            new_selection = removal_data['new_selection']

            # Remove keys from selected_key_tags
            tag_service = TagService()
            all_tag_keys = tag_service.get_all_tags()
            tag_key_options = {tag.key: f"{tag.label}" for tag in all_tag_keys}

            selected_key_tags = {key: tag_key_options[key] for key in new_selection if key in tag_key_options}
            plate_layout_state.set_selected_key_tags(selected_key_tags)

            # Remove data from all wells for the removed keys
            plate_layout = plate_layout_state.get_plate_layout()
            for well_name in plate_layout:
                for key in removed_keys:
                    if key in plate_layout[well_name]:
                        del plate_layout[well_name][key]

            # Remove well entries that are now empty
            wells_to_delete = [well for well, data in plate_layout.items() if not data]
            for well in wells_to_delete:
                del plate_layout[well]

            plate_layout_state.set_plate_layout(plate_layout)

            # Save updated data
            file_dict_keys_path = os.path.join(folder_data, "keys.json")
            with open(file_dict_keys_path, "w") as json_file:
                json.dump(plate_layout_state.get_selected_key_tags(), json_file, indent=4)

            file_plate_layout_path = os.path.join(folder_data, "plate_layout.json")
            with open(file_plate_layout_path, "w") as json_file:
                json.dump(plate_layout_state.get_plate_layout(), json_file, indent=4)

            # Update multiselect state
            plate_layout_state.set_multiselect_tag_keys(list(new_selection))

            # Clean up
            plate_layout_state.set_pending_key_removal(None)
            st.rerun()


def show_content():

    # Create tabs
    tab_dict, tab_plate_layout = st.tabs(["Tags", "Plate Layout"])

    with tab_dict:
        st.header("Select tag(s)")

        # Check for pending key removal confirmation
        if plate_layout_state.get_pending_key_removal():
            dialog_delete_keys()

        else:
            selected_key_tags = key_tag_selector()



    with tab_plate_layout:
        # Add the button to generate plate layout ressource
        if st.button("Generate plate layout ressource", icon=":material/note_add:"):
            path_temp = os.path.join(os.path.abspath(
                os.path.dirname(__file__)), Settings.make_temp_dir())
            full_path = os.path.join(path_temp, f"Plate_layout.json")
            plate_layout: File = File(full_path)
            # Convert dict to JSON string
            json_str = json.dumps(plate_layout_state.get_plate_layout(), indent=4)
            plate_layout.write(json_str)
            # Import the resource as JSONDict
            plate_layout_json_dict = JSONImporter.call(plate_layout)
            plate_layout_resource = ResourceModel.save_from_resource(
                plate_layout_json_dict, ResourceOrigin.UPLOADED, flagged=True)
            st.success(
                f"Resource created! ✅ You can find it here : {FrontService.get_resource_url(plate_layout_resource.id)}")
        if not plate_layout_state.get_selected_key_tags():
            st.warning("Please select at least one key")
        else:
            if plate_layout_state.get_well_clicked():
                st.write(
                    f"Fill informations for {', '.join(plate_layout_state.get_well_clicked())}:")

                # Add selector for each key
                set_selected_key = []
                for key, value in plate_layout_state.get_selected_key_tags().items():
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
                    plate_layout = plate_layout_state.get_plate_layout()
                    for selected_key, label in set_selected_key:
                        for well in plate_layout_state.get_well_clicked():
                            if well not in plate_layout:
                                plate_layout[well] = {}

                            # Find the actual key from the label
                            key = None
                            for k, v in plate_layout_state.get_selected_key_tags().items():
                                if v == label:
                                    key = k
                                    break

                            if key:
                                # Save in new format with label and value
                                plate_layout[well][key] = {
                                    "label": label,
                                    "value": selected_key if selected_key is not None else ""
                                }

                    # Remove wells where all values are empty
                    wells_to_delete = []
                    for well, well_data in plate_layout.items():
                        if all(data.get('value', '') == '' for data in well_data.values() if isinstance(data, dict)):
                            wells_to_delete.append(well)

                    for well in wells_to_delete:
                        del plate_layout[well]

                    plate_layout_state.set_plate_layout(plate_layout)

                    # Save the plate layout to a JSON file
                    file_plate_layout_path = os.path.join(
                        folder_data, "plate_layout.json")
                    os.makedirs(os.path.dirname(file_plate_layout_path),
                                exist_ok=True)  # Ensure directory exists
                    with open(file_plate_layout_path, "w") as json_file:
                        json.dump(
                            plate_layout_state.get_plate_layout(), json_file, indent=4)

                    plate_layout_state.set_success_message("Information saved successfully! ✅")
                    st.rerun()
                show_success_message()  # Show success message if it exists

                if any(well in plate_layout_state.get_plate_layout() for well in plate_layout_state.get_well_clicked()):
                    # Remove information for selected wells
                    if st.button(f"**:red[Remove saved information]**", icon = ":material/delete:", key = "remove_button"):
                        plate_layout = plate_layout_state.get_plate_layout()
                        for well in plate_layout_state.get_well_clicked():
                            if well in plate_layout:
                                plate_layout.pop(well, None)

                        plate_layout_state.set_plate_layout(plate_layout)

                        # Save the plate layout to a JSON file
                        file_plate_layout_path = os.path.join(
                            folder_data, "plate_layout.json")
                        os.makedirs(os.path.dirname(file_plate_layout_path),
                                    exist_ok=True)  # Ensure directory exists
                        with open(file_plate_layout_path, "w") as json_file:
                            json.dump(
                                plate_layout_state.get_plate_layout(), json_file, indent=4)

                        plate_layout_state.set_success_message("Information saved successfully! ✅")
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


def update_labels(dict_keys: dict):
    # Check if the label has changed for any key
    tag_service = TagService()
    all_tag_keys = tag_service.get_all_tags()
    tag_key_options = {tag.key: f"{tag.label}" for tag in all_tag_keys}
    updated = False

    # Handle selected_key_tags format (flat dictionary)
    if dict_keys and isinstance(next(iter(dict_keys.values()), None), str):
        for key in list(dict_keys.keys()):
            if key in tag_key_options and dict_keys[key] != tag_key_options[key]:
                dict_keys[key] = tag_key_options[key]
                updated = True

    # Handle plate_layout format (nested dictionary)
    else:
        for well_name, well_data in dict_keys.items():
            if isinstance(well_data, dict):
                for key, data in well_data.items():
                    if isinstance(data, dict) and 'label' in data:
                        if key in tag_key_options and data['label'] != tag_key_options[key]:
                            data['label'] = tag_key_options[key]
                            updated = True

    return updated, dict_keys


files_keys = [f for f in os.listdir(
    folder_data) if f.endswith("keys.json")]

if files_keys:
    # Load the file and display its contents
    file_path = os.path.join(folder_data, files_keys[0])
    with open(file_path, "r") as f:
        selected_key_tags = json.load(f)
        plate_layout_state.set_selected_key_tags(selected_key_tags)
    # Check if the label has changed for any key
    updated, updated_key_tags = update_labels(plate_layout_state.get_selected_key_tags())
    if updated:
        plate_layout_state.set_selected_key_tags(updated_key_tags)
        # Save the updated selected keys to keys.json
        file_dict_keys_path = os.path.join(
            folder_data, "keys.json")
        with open(file_dict_keys_path, "w") as json_file:
            json.dump(plate_layout_state.get_selected_key_tags(), json_file, indent=4)

files_plate_layout = [f for f in os.listdir(
    folder_data) if f.endswith("plate_layout.json")]
if files_plate_layout:
    # Load the file and display its contents
    file_path_plate_layout = os.path.join(folder_data, files_plate_layout[0])
    with open(file_path_plate_layout, "r") as f:
        plate_layout = json.load(f)
        plate_layout_state.set_plate_layout(plate_layout)

    # Check if the label has changed for any key
    updated, updated_plate_layout = update_labels(plate_layout_state.get_plate_layout())
    if updated:
        plate_layout_state.set_plate_layout(updated_plate_layout)
        # Save the updated selected keys to keys.json
        with open(file_path_plate_layout, "w") as json_file:
            json.dump(plate_layout_state.get_plate_layout(), json_file, indent=4)

# If is the first execution and there is an existing plate layout given in input, then we load it
elif existing_plate_layout:
    # check if the existing_plate_layout have the same size than the number entered in the parameters of the task
    try:
        validate_plate_layout(existing_plate_layout, number_wells)
    except ValueError as e:
        st.write(e)
    plate_layout_state.set_plate_layout(existing_plate_layout)

    # Retrieve keys from the existing plate layout and get their labels
    existing_keys = {}
    tag_service = TagService()
    all_tag_keys = tag_service.get_all_tags()
    tag_key_options = {tag.key: f"{tag.label}" for tag in all_tag_keys}

    for well_name, well_data in plate_layout_state.get_plate_layout().items():
        for key in well_data.keys():
            if key not in existing_keys and key in tag_key_options:
                existing_keys[key] = tag_key_options[key]

    current_selected_key_tags = plate_layout_state.get_selected_key_tags()
    current_selected_key_tags.update(existing_keys)
    plate_layout_state.set_selected_key_tags(current_selected_key_tags)

    # Check if the label has changed for any key
    updated, updated_plate_layout = update_labels(plate_layout_state.get_plate_layout())
    updated2, updated_selected_key_tags = update_labels(plate_layout_state.get_selected_key_tags())

    if updated:
        plate_layout_state.set_plate_layout(updated_plate_layout)
    if updated2:
        plate_layout_state.set_selected_key_tags(updated_selected_key_tags)

    # Save the selected keys to keys.json
    file_dict_keys_path = os.path.join(
        folder_data, "keys.json")
    with open(file_dict_keys_path, "w") as json_file:
        json.dump(plate_layout_state.get_selected_key_tags(), json_file, indent=4)

    # Save the plate layout to a JSON file
    file_plate_layout_path = os.path.join(
        folder_data, "plate_layout.json")
    os.makedirs(os.path.dirname(file_plate_layout_path),
                exist_ok=True)  # Ensure directory exists
    with open(file_plate_layout_path, "w") as json_file:
        json.dump(
            plate_layout_state.get_plate_layout(), json_file, indent=4)

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
                    selected_cols = plate_layout_state.get_selected_cols()
                    well_clicked = plate_layout_state.get_well_clicked()

                    if col + 1 in selected_cols:
                        selected_cols.remove(col + 1)
                        for row in range(ROWS):
                            well = wells[row][col]
                            if well in well_clicked:
                                well_clicked.remove(well)
                    else:
                        selected_cols.append(col + 1)
                        for row in range(ROWS):
                            well = wells[row][col]
                            if well not in well_clicked:
                                well_clicked.append(well)

                    plate_layout_state.set_selected_cols(selected_cols)
                    plate_layout_state.set_well_clicked(well_clicked)
                    st.rerun(scope="app")


            # Loop over the wells and create a grid of buttons
            for row in range(ROWS):
                cols_object = st.columns(COLS + 1)
                # Row header button
                if cols_object[0].button(chr(65 + row), key=f"row_{chr(65 + row)}"):
                    selected_rows = plate_layout_state.get_selected_rows()
                    well_clicked = plate_layout_state.get_well_clicked()

                    if chr(65 + row) in selected_rows:
                        selected_rows.remove(chr(65 + row))
                        for col in range(COLS):
                            well = wells[row][col]
                            if well in well_clicked:
                                well_clicked.remove(well)
                    else:
                        selected_rows.append(chr(65 + row))
                        for col in range(COLS):
                            well = wells[row][col]
                            if well not in well_clicked:
                                well_clicked.append(well)

                    plate_layout_state.set_selected_rows(selected_rows)
                    plate_layout_state.set_well_clicked(well_clicked)
                    st.rerun(scope="app")

                for col in range(COLS):
                    well = wells[row][col]
                    # Dynamically create tooltip text from the plate_layout dictionary
                    if well in plate_layout_state.get_plate_layout():
                        sorted_items = sorted(plate_layout_state.get_plate_layout()[well].items())
                        help_tab = "| Property | Value |\n|----------|-------|\n" + "\n".join(
                            [f"| **{data.get('label', key)}** | {data.get('value', '')} |"
                             for key, data in sorted_items if isinstance(data, dict)])
                    else:
                        help_tab = "No data available"

                    well_clicked = plate_layout_state.get_well_clicked()
                    if well in well_clicked:
                        if well in plate_layout_state.get_plate_layout() and all(plate_layout_state.get_plate_layout()[well].get(key, {}).get('value') for key in plate_layout_state.get_selected_key_tags().keys()):
                            if cols_object[col+1].button(f":green[{well}] ✓", key=well, help=help_tab):
                                well_clicked.remove(well)
                                plate_layout_state.set_well_clicked(well_clicked)
                                st.rerun(scope="app")
                        elif well in plate_layout_state.get_plate_layout():
                            if cols_object[col+1].button(f":green[{well}]", key=well, help=help_tab):
                                well_clicked.remove(well)
                                plate_layout_state.set_well_clicked(well_clicked)
                                st.rerun(scope="app")
                        else:
                            if cols_object[col+1].button(f"**:green[{well}]**", key=well):
                                well_clicked.remove(well)
                                plate_layout_state.set_well_clicked(well_clicked)
                                st.rerun(scope="app")
                    else:
                        if well in plate_layout_state.get_plate_layout() and all(plate_layout_state.get_plate_layout()[well].get(key, {}).get('value') for key in plate_layout_state.get_selected_key_tags().keys()):
                            if cols_object[col+1].button(f"{well} ✓", key=well, help=help_tab):
                                well_clicked.append(well)
                                plate_layout_state.set_well_clicked(well_clicked)
                                st.rerun(scope="app")
                        elif well in plate_layout_state.get_plate_layout():
                            if cols_object[col+1].button(well, key=well, help=help_tab):
                                well_clicked.append(well)
                                plate_layout_state.set_well_clicked(well_clicked)
                                st.rerun(scope="app")
                        else:
                            if cols_object[col+1].button(f"**{well}**", key=well):
                                well_clicked.append(well)
                                plate_layout_state.set_well_clicked(well_clicked)
                                st.rerun(scope="app")

            st.write(
                f"All the wells clicked are: {', '.join(plate_layout_state.get_well_clicked())}")

    fragment_sidebar_function()

    # Add the reset button
    st.button("Reset wells selection", on_click=plate_layout_state.reset_wells)

show_content()
