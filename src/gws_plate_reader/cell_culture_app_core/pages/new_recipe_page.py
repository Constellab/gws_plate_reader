"""
New Analysis Page for Constellab Bioprocess Dashboard
Allows users to create new analyses by uploading and configuring data
"""

import os
import tempfile

import streamlit as st
from gws_core import (
    File,
    InputTask,
    ProcessProxy,
    ProtocolProxy,
    ResourceModel,
    ResourceOrigin,
    ScenarioCreationType,
    ScenarioProxy,
    StringHelper,
    Tag,
)
from gws_core.streamlit import StreamlitContainers, StreamlitResourceSelect, StreamlitRouter

from gws_plate_reader.cell_culture_app_core.bioprocess_load_data import ConstellabBioprocessLoadData
from gws_plate_reader.cell_culture_app_core.cell_culture_state import CellCultureState


def render_new_recipe_page(cell_culture_state: CellCultureState) -> None:
    """Render the new analysis creation page"""

    translate_service = cell_culture_state.get_translate_service()

    style = """
    [CLASS_NAME] {
        padding: 40px;
    }
    """

    with StreamlitContainers.container_full_min_height(
        "container-center_new_analysis_page", additional_style=style
    ):
        # Add a return button
        router = StreamlitRouter.load_from_session()

        if st.button(
            f"{translate_service.translate('return_to_recipes')}",
            icon=":material/arrow_back:",
            width="content",
        ):
            router.navigate("first-page")

        st.markdown(f"## 🧬 {translate_service.translate('new_recipe')}")

        # Recipe details (outside form for better UX)
        st.subheader(f"📝 {translate_service.translate('recipe_details')}")

        analysis_name = st.text_input(
            translate_service.translate("recipe_name_label"),
            key="analysis_name_input",
            placeholder=translate_service.translate("recipe_name_placeholder"),
        )

        # Microplate checkbox (full width)
        is_microplate = st.checkbox(
            translate_service.translate("microplate_recipe"),
            key="is_microplate_checkbox",
            help=translate_service.translate("microplate_help"),
        )

        # Upload the 4 required files (moved to second position with 2x2 grid)
        st.subheader(f"📁 {translate_service.translate('import_required_files')}")

        # Documentation link button
        url_doc_context = "https://constellab.community/bricks/gws_plate_reader/latest/doc/technical-folder/task/ConstellabBioprocessLoadData"
        st.link_button("**?**", url_doc_context)

        st.info(translate_service.translate("import_files_info"))

        # Add option to choose between upload or select existing resources (OUTSIDE FORM)
        file_input_mode = st.radio(
            translate_service.translate("file_input_mode_label"),
            options=["upload", "select_existing"],
            format_func=lambda x: translate_service.translate(f"file_input_mode_{x}"),
            key="file_input_mode_radio",
            horizontal=True,
            help=translate_service.translate("file_input_mode_help"),
        )

        if file_input_mode == "upload":
            # Create 2x2 grid for file uploads
            upload_col1, upload_col2 = st.columns(2)

            with upload_col1:
                st.write(f"**1. {translate_service.translate('file_info_csv')}**")
                info_csv_file = st.file_uploader(
                    translate_service.translate("select_info_csv"),
                    type=["csv"],
                    key="info_csv_uploader",
                    help=translate_service.translate("info_csv_help"),
                )

                st.write(f"**3. {translate_service.translate('file_medium_csv')}**")
                medium_csv_file = st.file_uploader(
                    translate_service.translate("select_medium_csv"),
                    type=["csv"],
                    key="medium_csv_uploader",
                    help=translate_service.translate("medium_csv_help"),
                )

            with upload_col2:
                st.write(f"**2. {translate_service.translate('file_raw_data_csv')}**")
                raw_data_csv_file = st.file_uploader(
                    translate_service.translate("select_raw_data_csv"),
                    type=["csv"],
                    key="raw_data_csv_uploader",
                    help=translate_service.translate("raw_data_csv_help"),
                )

                st.write(f"**4. {translate_service.translate('file_followup_zip')}**")
                followup_zip_file = st.file_uploader(
                    translate_service.translate("select_followup_zip"),
                    type=["zip"],
                    key="followup_zip_uploader",
                    help=translate_service.translate("followup_zip_help"),
                )

            # Set resource selector values to None
            info_csv_resource = None
            raw_data_csv_resource = None
            medium_csv_resource = None
            followup_zip_resource = None

        else:  # select_existing mode
            # Create 2x2 grid for resource selection
            select_col1, select_col2 = st.columns(2)

            with select_col1:
                st.write(f"**1. {translate_service.translate('file_info_csv')}**")
                resource_select_info = StreamlitResourceSelect()
                # Filter to show only File resources
                resource_select_info.set_resource_typing_names_filter(["RESOURCE.gws_core.File"], disabled=True)
                resource_select_info.select_resource(
                    placeholder=translate_service.translate("select_info_csv_resource"),
                    key="info_csv_selector",
                    defaut_resource=None,
                )

                st.write(f"**3. {translate_service.translate('file_medium_csv')}**")
                resource_select_medium = StreamlitResourceSelect()
                # Filter to show only File resources
                resource_select_medium.set_resource_typing_names_filter(["RESOURCE.gws_core.File"], disabled=True)
                resource_select_medium.select_resource(
                    placeholder=translate_service.translate("select_medium_csv_resource"),
                    key="medium_csv_selector",
                    defaut_resource=None,
                )

            with select_col2:
                st.write(f"**2. {translate_service.translate('file_raw_data_csv')}**")
                resource_select_raw = StreamlitResourceSelect()
                # Filter to show only File resources
                resource_select_raw.set_resource_typing_names_filter(["RESOURCE.gws_core.File"], disabled=True)
                resource_select_raw.select_resource(
                    placeholder=translate_service.translate("select_raw_data_csv_resource"),
                    key="raw_data_csv_selector",
                    defaut_resource=None,
                )

                st.write(f"**4. {translate_service.translate('file_followup_zip')}**")
                resource_select_followup = StreamlitResourceSelect()
                # Filter to show only File resources
                resource_select_followup.set_resource_typing_names_filter(["RESOURCE.gws_core.File"], disabled=True)
                resource_select_followup.select_resource(
                    placeholder=translate_service.translate("select_followup_zip_resource"),
                    key="followup_zip_selector",
                    defaut_resource=None,
                )

            # Get selected resource IDs from session state
            if "info_csv_selector" not in st.session_state:
                st.session_state["info_csv_selector"] = {}
            if "raw_data_csv_selector" not in st.session_state:
                st.session_state["raw_data_csv_selector"] = {}
            if "medium_csv_selector" not in st.session_state:
                st.session_state["medium_csv_selector"] = {}

            info_csv_resource = (
                st.session_state.get("info_csv_selector").get("resourceId", None)
                if st.session_state.get("info_csv_selector")
                else None
            )
            raw_data_csv_resource = (
                st.session_state.get("raw_data_csv_selector").get("resourceId", None)
                if st.session_state.get("raw_data_csv_selector")
                else None
            )
            medium_csv_resource = (
                st.session_state.get("medium_csv_selector").get("resourceId", None)
                if st.session_state.get("medium_csv_selector")
                else None
            )
            followup_zip_resource = (
                st.session_state.get("followup_zip_selector").get("resourceId", None)
                if st.session_state.get("followup_zip_selector")
                else None
            )

            # Set file uploader values to None
            info_csv_file = None
            raw_data_csv_file = None
            medium_csv_file = None
            followup_zip_file = None

        # Submit button (outside form since we removed the form)
        submit_button = st.button(
            label=f"🚀 {translate_service.translate('create_recipe_button')}",
            type="primary",
            width="stretch",
            key="create_recipe_submit_button",
        )

        if submit_button:
            # Validation
            missing_fields = []

            # Check analysis name
            if not analysis_name or not analysis_name.strip():
                missing_fields.append(translate_service.translate("recipe_name_label"))

            # Validate based on input mode
            if file_input_mode == "upload":
                # Check all 4 file uploads
                uploaded_files = {
                    "info_csv": (info_csv_file, "Info CSV"),
                    "raw_data_csv": (raw_data_csv_file, "Raw Data CSV"),
                    "medium_csv": (medium_csv_file, "Medium CSV"),
                    "followup_zip": (followup_zip_file, "Follow-up ZIP"),
                }

                for file_key, (file_obj, file_name) in uploaded_files.items():
                    if file_obj is None:
                        missing_fields.append(file_name)
            else:  # select_existing mode
                # Check all 4 resource selections
                selected_resources = {
                    "info_csv": (info_csv_resource, "Info CSV"),
                    "raw_data_csv": (raw_data_csv_resource, "Raw Data CSV"),
                    "medium_csv": (medium_csv_resource, "Medium CSV"),
                    "followup_zip": (followup_zip_resource, "Follow-up ZIP"),
                }

                for resource_key, (resource_id, resource_name) in selected_resources.items():
                    if resource_id is None:
                        missing_fields.append(resource_name)

            if missing_fields:
                # Construire le message d'erreur sous forme "Champs manquant : '..', '...'"
                fields_str = "', '".join(missing_fields)
                error_message = f"{translate_service.translate('fill_all_fields')} '{fields_str}'"

                st.error(error_message)
                return

            try:
                # Create or get File resources based on input mode
                file_resource_models = {}

                if file_input_mode == "upload":
                    # Create File resources from uploaded files

                    # Define uploaded files mapping
                    uploaded_files = {
                        "info_csv": info_csv_file,
                        "raw_data_csv": raw_data_csv_file,
                        "medium_csv": medium_csv_file,
                        "followup_zip": followup_zip_file,
                    }

                    # Save uploaded files temporarily and create File resources
                    temp_files = {}
                    file_resources = {}

                    for file_key, file_obj in uploaded_files.items():
                        if file_obj is not None:
                            # Create temporary file
                            temp_dir = tempfile.gettempdir()
                            temp_file_path = os.path.join(temp_dir, f"{file_key}_{file_obj.name}")

                            # Write uploaded content to temp file
                            with open(temp_file_path, "wb") as temp_file:
                                temp_file.write(file_obj.getvalue())

                            # Create File resource
                            file_resource = File(temp_file_path)
                            file_resource.name = file_obj.name
                            file_resources[file_key] = file_resource
                            temp_files[file_key] = temp_file_path

                    # Create ResourceModel from File resources using save_from_resource
                    for file_key, file_resource in file_resources.items():
                        resource_model = ResourceModel.save_from_resource(
                            resource=file_resource,
                            origin=ResourceOrigin.UPLOADED,
                            scenario=None,
                            task_model=None,
                            flagged=True,
                        )
                        file_resource_models[file_key] = resource_model

                else:  # select_existing mode
                    # Get existing resource models from IDs
                    selected_resources = {
                        "info_csv": info_csv_resource,
                        "raw_data_csv": raw_data_csv_resource,
                        "medium_csv": medium_csv_resource,
                        "followup_zip": followup_zip_resource,
                    }

                    # Validate that all selected resources are File type
                    invalid_resources = []
                    for resource_key, resource_id in selected_resources.items():
                        if resource_id is not None:
                            resource_model = ResourceModel.get_by_id(resource_id)

                            # Check if resource is of type File
                            if resource_model.resource_typing_name != "RESOURCE.gws_core.File":
                                resource_name_mapping = {
                                    "info_csv": "Info CSV",
                                    "raw_data_csv": "Raw Data CSV",
                                    "medium_csv": "Medium CSV",
                                    "followup_zip": "Follow-up ZIP",
                                }
                                invalid_resources.append(
                                    f"{resource_name_mapping[resource_key]} ({resource_model.name})"
                                )
                            else:
                                file_resource_models[resource_key] = resource_model

                    # If any invalid resources found, show error and stop
                    if invalid_resources:
                        invalid_str = "', '".join(invalid_resources)
                        st.error(
                            f"❌ {translate_service.translate('invalid_resource_type')}: '{invalid_str}'. "
                            f"{translate_service.translate('must_select_file_resources')}"
                        )
                        return

                # Create scenario (using default folder)
                scenario: ScenarioProxy = ScenarioProxy(
                    None,
                    folder=None,  # Use default folder
                    title=f"{analysis_name} - Constellab Bioprocess",
                    creation_type=ScenarioCreationType.MANUAL,
                )

                protocol: ProtocolProxy = scenario.get_protocol()

                # Add input tasks for each file resource using the ResourceModel IDs
                info_csv_input = protocol.add_process(
                    InputTask,
                    "info_csv_input",
                    {InputTask.config_name: file_resource_models["info_csv"].id},
                )

                raw_data_csv_input = protocol.add_process(
                    InputTask,
                    "raw_data_csv_input",
                    {InputTask.config_name: file_resource_models["raw_data_csv"].id},
                )

                medium_csv_input = protocol.add_process(
                    InputTask,
                    cell_culture_state.MEDIUM_CSV_INPUT_KEY,
                    {InputTask.config_name: file_resource_models["medium_csv"].id},
                )

                follow_up_zip_input = protocol.add_process(
                    InputTask,
                    "follow_up_zip_input",
                    {InputTask.config_name: file_resource_models["followup_zip"].id},
                )  # Add the data loading task
                load_process: ProcessProxy = protocol.add_process(
                    ConstellabBioprocessLoadData, "data_processing"
                )

                # Connect the inputs to the task using connectors
                protocol.add_connector(
                    out_port=info_csv_input >> "resource", in_port=load_process << "info_csv"
                )
                protocol.add_connector(
                    out_port=raw_data_csv_input >> "resource",
                    in_port=load_process << "raw_data_csv",
                )
                protocol.add_connector(
                    out_port=medium_csv_input >> "resource", in_port=load_process << "medium_csv"
                )
                protocol.add_connector(
                    out_port=follow_up_zip_input >> "resource",
                    in_port=load_process << "follow_up_zip",
                )

                # Add outputs
                protocol.add_output(
                    cell_culture_state.LOAD_SCENARIO_OUTPUT_NAME,
                    load_process >> "resource_set",
                    flag_resource=True,
                )

                # Add venn diagram output (optional)
                protocol.add_output(
                    "venn_diagram", load_process >> "venn_diagram", flag_resource=False
                )

                # Add medium table output (optional)
                protocol.add_output(
                    "medium_table", load_process >> "medium_table", flag_resource=False
                )

                # Add metadata table output (optional)
                protocol.add_output(
                    "metadata_table", load_process >> "metadata_table", flag_resource=False
                )

                # Add tags for identification
                analysis_name_parsed = Tag.parse_tag(analysis_name)
                pipeline_id = StringHelper.generate_uuid()

                # Core tags
                scenario.add_tag(
                    Tag(
                        cell_culture_state.TAG_FERMENTOR,
                        cell_culture_state.TAG_DATA_PROCESSING,
                        is_propagable=False,
                    )
                )
                scenario.add_tag(
                    Tag(
                        cell_culture_state.TAG_FERMENTOR_RECIPE_NAME,
                        analysis_name_parsed,
                        is_propagable=False,
                    )
                )
                scenario.add_tag(
                    Tag(
                        cell_culture_state.TAG_FERMENTOR_PIPELINE_ID,
                        pipeline_id,
                        is_propagable=False,
                    )
                )

                # Analysis type tag
                scenario.add_tag(
                    Tag(
                        cell_culture_state.TAG_MICROPLATE_ANALYSIS,
                        "true" if is_microplate else "false",
                        is_propagable=False,
                    )
                )

                # Resource tags for the 4 files (get resource names from ResourceModels)
                scenario.add_tag(
                    Tag(
                        "info_csv_file",
                        Tag.parse_tag(file_resource_models["info_csv"].name),
                        is_propagable=False,
                    )
                )
                scenario.add_tag(
                    Tag(
                        "raw_data_csv_file",
                        Tag.parse_tag(file_resource_models["raw_data_csv"].name),
                        is_propagable=False,
                    )
                )
                scenario.add_tag(
                    Tag(
                        "medium_csv_file",
                        Tag.parse_tag(file_resource_models["medium_csv"].name),
                        is_propagable=False,
                    )
                )
                scenario.add_tag(
                    Tag(
                        "followup_zip_file",
                        Tag.parse_tag(file_resource_models["followup_zip"].name),
                        is_propagable=False,
                    )
                )

                # Add to queue and navigate back
                scenario.add_to_queue()

                st.success(
                    translate_service.translate("recipe_created").format(recipe_name=analysis_name)
                )
                st.info(translate_service.translate("creating_recipe"))

                # Navigate back after a short delay
                with st.spinner(translate_service.translate("view_recipe")):
                    import time

                    time.sleep(2)

                router.navigate("first-page")
                st.rerun()

            except Exception as e:
                # Construire le message d'erreur complet
                error_message = f"{translate_service.translate('error_creating_recipe')}\n\n**{translate_service.translate('error_details')}** {str(e)}"
                st.error(error_message)

                # Afficher la stack trace en mode expandable pour le debug
                with st.expander(translate_service.translate("technical_details"), expanded=False):
                    st.exception(e)
