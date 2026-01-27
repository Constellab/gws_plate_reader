"""
New Analysis Page for Constellab Bioprocess Dashboard
Allows users to create new analyses by uploading and configuring data
"""

import os
import tempfile
import time

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
from gws_core.impl.file.file_decompress_task import FileDecompressTask
from gws_core.impl.table.tasks.table_importer import TableImporter
from gws_core.resource.resource_set.resource_set_tasks import ResourceStacker
from gws_core.streamlit import StreamlitContainers, StreamlitResourceSelect, StreamlitRouter

from gws_plate_reader.biolector_xt_data_parser.biolector_xt_load_data import BiolectorXTLoadData
from gws_plate_reader.cell_culture_app_core.bioprocess_load_data import ConstellabBioprocessLoadData
from gws_plate_reader.cell_culture_app_core.cell_culture_state import CellCultureState


def render_new_recipe_page(cell_culture_state: CellCultureState) -> None:
    """Render the new analysis creation page with tabs for Fermentor and Microplate recipes"""

    translate_service = cell_culture_state.get_translate_service()
    router = StreamlitRouter.load_from_session()

    style = """
    [CLASS_NAME] {
        padding: 40px;
    }
    """

    with StreamlitContainers.container_full_min_height(
        "container-center_new_analysis_page", additional_style=style
    ):
        # Header with return button and title
        col_back, col_title = st.columns([1, 15])

        with col_back:
            if st.button("", icon=":material/arrow_back:", width="content"):
                router.navigate("first-page")

        with col_title:
            st.markdown(f"## 🧬 {translate_service.translate('new_recipe')}")

        st.markdown("---")

        # Tab menu
        tab_fermentor, tab_biolector = st.tabs(
            [
                f"🧪 {translate_service.translate('tab_fermentor_recipe')}",
                f"🧫 {translate_service.translate('tab_biolector_recipe')}",
            ]
        )

        with tab_fermentor:
            render_new_recipe_fermentor(cell_culture_state)

        with tab_biolector:
            render_new_recipe_microplate(cell_culture_state)


def render_new_recipe_fermentor(cell_culture_state: CellCultureState) -> None:
    """Render the fermentor recipe creation form

    This method can be overridden in child apps to provide custom fermentor recipe creation
    """

    translate_service = cell_culture_state.get_translate_service()
    router = StreamlitRouter.load_from_session()

    # Recipe details
    st.subheader(f"📝 {translate_service.translate('recipe_details')}")

    analysis_name = st.text_input(
        translate_service.translate("recipe_name_label"),
        key="fermentor_analysis_name_input",
        placeholder=translate_service.translate("recipe_name_placeholder"),
    )

    # Upload the 4 required files
    col_title, col_doc_button = st.columns([5, 1])
    with col_title:
        st.subheader(f"📁 {translate_service.translate('import_required_files')}")
    with col_doc_button:
        url_doc_context = "https://constellab.community/bricks/gws_plate_reader/latest/doc/technical-folder/task/ConstellabBioprocessLoadData"
        st.link_button(translate_service.translate("documentation"), url_doc_context)

    st.info(translate_service.translate("import_files_info"))

    # Add option to choose between upload or select existing resources
    file_input_mode = st.radio(
        translate_service.translate("file_input_mode_label"),
        options=["upload", "select_existing"],
        format_func=lambda x: translate_service.translate(f"file_input_mode_{x}"),
        key="fermentor_file_input_mode_radio",
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
                key="fermentor_info_csv_uploader",
                help=translate_service.translate("info_csv_help"),
            )

            st.write(f"**3. {translate_service.translate('file_medium_csv')}**")
            medium_csv_file = st.file_uploader(
                translate_service.translate("select_medium_csv"),
                type=["csv"],
                key="fermentor_medium_csv_uploader",
                help=translate_service.translate("medium_csv_help"),
            )

        with upload_col2:
            st.write(f"**2. {translate_service.translate('file_raw_data_csv')}**")
            raw_data_csv_file = st.file_uploader(
                translate_service.translate("select_raw_data_csv"),
                type=["csv"],
                key="fermentor_raw_data_csv_uploader",
                help=translate_service.translate("raw_data_csv_help"),
            )

            st.write(f"**4. {translate_service.translate('file_followup_zip')}**")
            followup_zip_file = st.file_uploader(
                translate_service.translate("select_followup_zip"),
                type=["zip"],
                key="fermentor_followup_zip_uploader",
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
            resource_select_info.set_resource_typing_names_filter(
                ["RESOURCE.gws_core.File"], disabled=True
            )
            resource_select_info.select_resource(
                placeholder=translate_service.translate("select_info_csv_resource"),
                key="fermentor_info_csv_selector",
                defaut_resource=None,
            )

            st.write(f"**3. {translate_service.translate('file_medium_csv')}**")
            resource_select_medium = StreamlitResourceSelect()
            resource_select_medium.set_resource_typing_names_filter(
                ["RESOURCE.gws_core.File"], disabled=True
            )
            resource_select_medium.select_resource(
                placeholder=translate_service.translate("select_medium_csv_resource"),
                key="fermentor_medium_csv_selector",
                defaut_resource=None,
            )

        with select_col2:
            st.write(f"**2. {translate_service.translate('file_raw_data_csv')}**")
            resource_select_raw = StreamlitResourceSelect()
            resource_select_raw.set_resource_typing_names_filter(
                ["RESOURCE.gws_core.File"], disabled=True
            )
            resource_select_raw.select_resource(
                placeholder=translate_service.translate("select_raw_data_csv_resource"),
                key="fermentor_raw_data_csv_selector",
                defaut_resource=None,
            )

            st.write(f"**4. {translate_service.translate('file_followup_zip')}**")
            resource_select_followup = StreamlitResourceSelect()
            resource_select_followup.set_resource_typing_names_filter(
                ["RESOURCE.gws_core.File"], disabled=True
            )
            resource_select_followup.select_resource(
                placeholder=translate_service.translate("select_followup_zip_resource"),
                key="fermentor_followup_zip_selector",
                defaut_resource=None,
            )

        # Get selected resource IDs from session state
        if "fermentor_info_csv_selector" not in st.session_state:
            st.session_state["fermentor_info_csv_selector"] = {}
        if "fermentor_raw_data_csv_selector" not in st.session_state:
            st.session_state["fermentor_raw_data_csv_selector"] = {}
        if "fermentor_medium_csv_selector" not in st.session_state:
            st.session_state["fermentor_medium_csv_selector"] = {}
        if "fermentor_followup_zip_selector" not in st.session_state:
            st.session_state["fermentor_followup_zip_selector"] = {}

        info_csv_resource = (
            st.session_state.get("fermentor_info_csv_selector").get("resourceId", None)
            if st.session_state.get("fermentor_info_csv_selector")
            else None
        )
        raw_data_csv_resource = (
            st.session_state.get("fermentor_raw_data_csv_selector").get("resourceId", None)
            if st.session_state.get("fermentor_raw_data_csv_selector")
            else None
        )
        medium_csv_resource = (
            st.session_state.get("fermentor_medium_csv_selector").get("resourceId", None)
            if st.session_state.get("fermentor_medium_csv_selector")
            else None
        )
        followup_zip_resource = (
            st.session_state.get("fermentor_followup_zip_selector").get("resourceId", None)
            if st.session_state.get("fermentor_followup_zip_selector")
            else None
        )

        # Set file uploader values to None
        info_csv_file = None
        raw_data_csv_file = None
        medium_csv_file = None
        followup_zip_file = None

    # Submit button
    submit_button = st.button(
        label=f"🚀 {translate_service.translate('create_recipe_button')}",
        type="primary",
        width="stretch",
        key="fermentor_create_recipe_submit_button",
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
            fields_str = "', '".join(missing_fields)
            error_message = f"{translate_service.translate('fill_all_fields')} '{fields_str}'"
            st.error(error_message)
            return

        try:
            # Create or get File resources based on input mode
            file_resource_models = {}

            if file_input_mode == "upload":
                # Create File resources from uploaded files
                uploaded_files = {
                    "info_csv": info_csv_file,
                    "raw_data_csv": raw_data_csv_file,
                    "medium_csv": medium_csv_file,
                    "followup_zip": followup_zip_file,
                }

                # Save uploaded files temporarily and create File resources
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
                folder=None,
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
            )

            # Add the data loading task
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
            protocol.add_output("venn_diagram", load_process >> "venn_diagram", flag_resource=False)

            # Add medium table output (optional)
            protocol.add_output("medium_table", load_process >> "medium_table", flag_resource=False)

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

            # Analysis type tag - fermentor recipe
            scenario.add_tag(
                Tag(
                    cell_culture_state.TAG_MICROPLATE_ANALYSIS,
                    "false",
                    is_propagable=False,
                )
            )

            # Resource tags for the 4 files
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
                time.sleep(2)

            router.navigate("first-page")
            st.rerun()

        except Exception as e:
            error_message = f"{translate_service.translate('error_creating_recipe')}\n\n**{translate_service.translate('error_details')}** {str(e)}"
            st.error(error_message)

            with st.expander(translate_service.translate("technical_details"), expanded=False):
                st.exception(e)


def render_new_recipe_microplate(cell_culture_state: CellCultureState) -> None:
    """Render the microplate recipe creation form

    This method can be overridden in child apps to provide custom microplate recipe creation
    """

    translate_service = cell_culture_state.get_translate_service()
    router = StreamlitRouter.load_from_session()

    # Recipe details
    st.subheader(f"📝 {translate_service.translate('recipe_details')}")

    analysis_name = st.text_input(
        translate_service.translate("recipe_name_label"),
        key="microplate_analysis_name_input",
        placeholder=translate_service.translate("microplate_recipe_name_placeholder"),
    )

    # Upload the required files
    col_title, col_doc_button = st.columns([5, 1])
    with col_title:
        st.subheader(f"📁 {translate_service.translate('import_required_files')}")
    with col_doc_button:
        # Documentation link button aligned to the right
        st.markdown(
            """
            <style>
                div[data-testid="column"]:has(a[data-testid="baseButton-secondary"]) {
                    display: flex;
                    justify-content: flex-end;
                    align-items: center;
                }
            </style>
        """,
            unsafe_allow_html=True,
        )
        url_doc_context = "https://constellab.community/bricks/gws_plate_reader/latest/doc/technical-folder/task/BiolectorLoadData"
        st.link_button(translate_service.translate("documentation"), url_doc_context)

    st.info(translate_service.translate("microplate_import_files_info"))

    # Add option to choose between upload or select existing resources
    file_input_mode = st.radio(
        translate_service.translate("file_input_mode_label"),
        options=["upload", "select_existing"],
        format_func=lambda x: translate_service.translate(f"file_input_mode_{x}"),
        key="microplate_file_input_mode_radio",
        horizontal=True,
        help=translate_service.translate("file_input_mode_help"),
    )

    st.markdown("---")

    # First: Medium table (optional, shared across all plates)
    st.write(f"**{translate_service.translate('medium_table_optional')}**")

    if file_input_mode == "upload":
        medium_table_file = st.file_uploader(
            f"{translate_service.translate('select_medium_table')} (CSV)",
            type=["csv"],
            key="microplate_medium_table_uploader",
            help=translate_service.translate("medium_table_help"),
        )
        medium_table_resource = None
    else:
        resource_select_medium = StreamlitResourceSelect()
        resource_select_medium.set_resource_typing_names_filter(
            ["RESOURCE.gws_core.Table"], disabled=True
        )
        resource_select_medium.select_resource(
            placeholder=translate_service.translate("select_medium_table"),
            key="microplate_medium_table_selector",
            defaut_resource=None,
        )
        if "microplate_medium_table_selector" not in st.session_state:
            st.session_state["microplate_medium_table_selector"] = {}
        medium_table_resource = (
            st.session_state.get("microplate_medium_table_selector").get("resourceId", None)
            if st.session_state.get("microplate_medium_table_selector")
            else None
        )
        medium_table_file = None

    # Per-plate inputs
    st.markdown("---")
    st.subheader(f"📋 {translate_service.translate('plate_configurations')}")

    # Initialize plates list in session state
    if "microplate_plates_list" not in st.session_state:
        st.session_state.microplate_plates_list = [0]  # Start with one plate
    if "microplate_plate_counter" not in st.session_state:
        st.session_state.microplate_plate_counter = 1

    plates_data = []

    for plate_idx in st.session_state.microplate_plates_list:
        # Plate title
        st.write(
            f"### 🧫 {translate_service.translate('plate')} {st.session_state.microplate_plates_list.index(plate_idx) + 1}"
        )

        with st.container():
            # Plate name with remove button
            col_name, col_remove = st.columns([6, 1])

            with col_name:
                plate_name = st.text_input(
                    translate_service.translate("plate_name_label"),
                    value=f"plate_{st.session_state.microplate_plates_list.index(plate_idx) + 1}",
                    key=f"microplate_plate_name_{plate_idx}",
                    help=translate_service.translate("plate_name_help"),
                )

            with col_remove:
                st.write("")  # Empty label for alignment
                is_disabled = len(st.session_state.microplate_plates_list) <= 1
                if st.button(
                    translate_service.translate("remove_plate"),
                    key=f"microplate_remove_plate_{plate_idx}",
                    disabled=is_disabled,
                    width="stretch",
                ):
                    st.session_state.microplate_plates_list.remove(plate_idx)
                    st.rerun()

            if file_input_mode == "upload":
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.write(f"**{translate_service.translate('raw_data_table_required')}**")
                    raw_data_file = st.file_uploader(
                        f"{translate_service.translate('select_raw_data_table')} (CSV)",
                        type=["csv"],
                        key=f"microplate_raw_data_uploader_{plate_idx}",
                        help=translate_service.translate("raw_data_table_help"),
                    )

                with col2:
                    st.write(f"**{translate_service.translate('folder_metadata_required')}**")
                    folder_metadata_file = st.file_uploader(
                        f"{translate_service.translate('select_folder_metadata')} (ZIP)",
                        type=["zip"],
                        key=f"microplate_folder_metadata_uploader_{plate_idx}",
                        help=translate_service.translate("folder_metadata_help"),
                    )

                with col3:
                    st.write(f"**{translate_service.translate('info_table_optional')}**")
                    info_table_file = st.file_uploader(
                        f"{translate_service.translate('select_info_table')} (CSV)",
                        type=["csv"],
                        key=f"microplate_info_table_uploader_{plate_idx}",
                        help=translate_service.translate("info_table_help"),
                    )

                plates_data.append(
                    {
                        "plate_name": plate_name,
                        "raw_data_file": raw_data_file,
                        "folder_metadata_file": folder_metadata_file,
                        "info_table_file": info_table_file,
                        "raw_data_resource": None,
                        "folder_metadata_resource": None,
                        "info_table_resource": None,
                    }
                )

            else:  # select_existing mode
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.write(f"**{translate_service.translate('raw_data_table_required')}**")
                    resource_select_raw_data = StreamlitResourceSelect()
                    resource_select_raw_data.set_resource_typing_names_filter(
                        ["RESOURCE.gws_core.Table"], disabled=True
                    )
                    resource_select_raw_data.select_resource(
                        placeholder=translate_service.translate("select_raw_data_table"),
                        key=f"microplate_raw_data_selector_{plate_idx}",
                        defaut_resource=None,
                    )

                with col2:
                    st.write(f"**{translate_service.translate('folder_metadata_required')}**")
                    resource_select_metadata = StreamlitResourceSelect()
                    resource_select_metadata.set_resource_typing_names_filter(
                        ["RESOURCE.gws_core.Folder"], disabled=True
                    )
                    resource_select_metadata.select_resource(
                        placeholder=translate_service.translate("select_folder_metadata"),
                        key=f"microplate_folder_metadata_selector_{plate_idx}",
                        defaut_resource=None,
                    )

                with col3:
                    st.write(f"**{translate_service.translate('info_table_optional')}**")
                    resource_select_info = StreamlitResourceSelect()
                    resource_select_info.set_resource_typing_names_filter(
                        ["RESOURCE.gws_core.Table"], disabled=True
                    )
                    resource_select_info.select_resource(
                        placeholder=translate_service.translate("select_info_table"),
                        key=f"microplate_info_table_selector_{plate_idx}",
                        defaut_resource=None,
                    )

                # Initialize session state if needed
                for key in [
                    f"microplate_raw_data_selector_{plate_idx}",
                    f"microplate_folder_metadata_selector_{plate_idx}",
                    f"microplate_info_table_selector_{plate_idx}",
                ]:
                    if key not in st.session_state:
                        st.session_state[key] = {}

                raw_data_resource = (
                    st.session_state.get(f"microplate_raw_data_selector_{plate_idx}").get(
                        "resourceId", None
                    )
                    if st.session_state.get(f"microplate_raw_data_selector_{plate_idx}")
                    else None
                )
                folder_metadata_resource = (
                    st.session_state.get(f"microplate_folder_metadata_selector_{plate_idx}").get(
                        "resourceId", None
                    )
                    if st.session_state.get(f"microplate_folder_metadata_selector_{plate_idx}")
                    else None
                )
                info_table_resource = (
                    st.session_state.get(f"microplate_info_table_selector_{plate_idx}").get(
                        "resourceId", None
                    )
                    if st.session_state.get(f"microplate_info_table_selector_{plate_idx}")
                    else None
                )

                plates_data.append(
                    {
                        "plate_name": plate_name,
                        "raw_data_file": None,
                        "folder_metadata_file": None,
                        "info_table_file": None,
                        "raw_data_resource": raw_data_resource,
                        "folder_metadata_resource": folder_metadata_resource,
                        "info_table_resource": info_table_resource,
                    }
                )

            st.markdown("---")

    # Add plate button
    if st.button(
        f"➕ {translate_service.translate('add_plate')}",
        width="stretch",
        type="secondary",
        key="microplate_add_plate_button",
    ):
        st.session_state.microplate_plates_list.append(st.session_state.microplate_plate_counter)
        st.session_state.microplate_plate_counter += 1
        st.rerun()

    st.markdown("---")

    # Validate plate names uniqueness
    plate_names = [plate_data["plate_name"] for plate_data in plates_data]
    has_duplicate_names = len(plate_names) != len(set(plate_names))

    if has_duplicate_names:
        st.error(translate_service.translate("duplicate_plate_names_error"))

    if st.button(
        translate_service.translate("create_recipe_button"),
        type="primary",
        width="stretch",
        icon="🚀",
        disabled=has_duplicate_names,
        key="microplate_create_recipe_button",
    ):
        # Validate inputs
        if not analysis_name:
            st.error(translate_service.translate("missing_recipe_name"))
            return

        # Validate plates data
        for plate_idx, plate_data in enumerate(plates_data):
            if file_input_mode == "upload":
                if not plate_data["raw_data_file"]:
                    st.error(
                        f"Plate {plate_idx + 1}: {translate_service.translate('missing_raw_data_table')}"
                    )
                    return
                if not plate_data["folder_metadata_file"]:
                    st.error(
                        f"Plate {plate_idx + 1}: {translate_service.translate('missing_folder_metadata')}"
                    )
                    return
            else:
                if not plate_data["raw_data_resource"]:
                    st.error(
                        f"Plate {plate_idx + 1}: {translate_service.translate('missing_raw_data_table')}"
                    )
                    return
                if not plate_data["folder_metadata_resource"]:
                    st.error(
                        f"Plate {plate_idx + 1}: {translate_service.translate('missing_folder_metadata')}"
                    )
                    return

        try:
            # Process medium_table (shared across all plates)
            medium_table_model = None
            if file_input_mode == "upload" and medium_table_file is not None:
                temp_dir = tempfile.gettempdir()
                temp_file_path = os.path.join(temp_dir, f"medium_table_{medium_table_file.name}")

                with open(temp_file_path, "wb") as temp_file:
                    temp_file.write(medium_table_file.getvalue())

                table_resource = TableImporter.call(File(temp_file_path))
                table_resource.name = medium_table_file.name

                medium_table_model = ResourceModel.save_from_resource(
                    resource=table_resource,
                    origin=ResourceOrigin.UPLOADED,
                    scenario=None,
                    task_model=None,
                    flagged=True,
                )
            elif file_input_mode == "select_existing" and medium_table_resource is not None:
                medium_table_model = ResourceModel.get_by_id(medium_table_resource)

            # Process each plate's resources
            plates_resources = []
            temp_dir = tempfile.gettempdir()

            for plate_idx, plate_data in enumerate(plates_data):
                plate_resources = {}

                if file_input_mode == "upload":
                    if plate_data["raw_data_file"] is not None:
                        temp_file_path = os.path.join(
                            temp_dir,
                            f"raw_data_plate_{plate_idx}_{plate_data['raw_data_file'].name}",
                        )
                        with open(temp_file_path, "wb") as temp_file:
                            temp_file.write(plate_data["raw_data_file"].getvalue())

                        raw_data_resource = TableImporter.call(File(temp_file_path))
                        raw_data_resource.name = plate_data['raw_data_file'].name

                        plate_resources["raw_data"] = ResourceModel.save_from_resource(
                            resource=raw_data_resource,
                            origin=ResourceOrigin.UPLOADED,
                            scenario=None,
                            task_model=None,
                            flagged=True,
                        )

                    if plate_data["folder_metadata_file"] is not None:
                        temp_zip_path = os.path.join(
                            temp_dir,
                            f"metadata_plate_{plate_idx}_{plate_data['folder_metadata_file'].name}",
                        )
                        with open(temp_zip_path, "wb") as temp_file:
                            temp_file.write(plate_data["folder_metadata_file"].getvalue())

                        folder_resource = FileDecompressTask.call(File(temp_zip_path))
                        folder_resource.name = plate_data['folder_metadata_file'].name

                        plate_resources["folder_metadata"] = ResourceModel.save_from_resource(
                            resource=folder_resource,
                            origin=ResourceOrigin.UPLOADED,
                            scenario=None,
                            task_model=None,
                            flagged=True,
                        )

                    if plate_data["info_table_file"] is not None:
                        temp_info_path = os.path.join(
                            temp_dir,
                            f"info_table_plate_{plate_idx}_{plate_data['info_table_file'].name}",
                        )
                        with open(temp_info_path, "wb") as temp_file:
                            temp_file.write(plate_data["info_table_file"].getvalue())

                        info_table_resource = TableImporter.call(File(temp_info_path))
                        info_table_resource.name = plate_data['info_table_file'].name

                        plate_resources["info_table"] = ResourceModel.save_from_resource(
                            resource=info_table_resource,
                            origin=ResourceOrigin.UPLOADED,
                            scenario=None,
                            task_model=None,
                            flagged=True,
                        )
                else:
                    if plate_data["raw_data_resource"] is not None:
                        plate_resources["raw_data"] = ResourceModel.get_by_id(
                            plate_data["raw_data_resource"]
                        )
                    if plate_data["folder_metadata_resource"] is not None:
                        plate_resources["folder_metadata"] = ResourceModel.get_by_id(
                            plate_data["folder_metadata_resource"]
                        )
                    if plate_data["info_table_resource"] is not None:
                        plate_resources["info_table"] = ResourceModel.get_by_id(
                            plate_data["info_table_resource"]
                        )

                plates_resources.append(
                    {"name": plate_data["plate_name"], "resources": plate_resources}
                )

            # Create scenario
            scenario: ScenarioProxy = ScenarioProxy(
                None,
                folder=None,
                title=f"{analysis_name} - BiolectorXT",
                creation_type=ScenarioCreationType.MANUAL,
            )

            protocol: ProtocolProxy = scenario.get_protocol()

            # Collect plate names for config
            plate_names = [plate["name"] for plate in plates_resources]

            # Add medium_table input if provided
            if medium_table_model is not None:
                medium_table_input = protocol.add_process(
                    InputTask, "medium_table_input", {InputTask.config_name: medium_table_model.id}
                )

            # Create ResourceStacker for each plate
            plate_stackers = []
            for plate_idx, plate_info in enumerate(plates_resources):
                plate_name = plate_info["name"]
                plate_resources = plate_info["resources"]

                raw_data_input = protocol.add_process(
                    InputTask,
                    f"{plate_name}_raw_data_input",
                    {InputTask.config_name: plate_resources["raw_data"].id},
                )

                folder_metadata_input = protocol.add_process(
                    InputTask,
                    f"{plate_name}_folder_metadata_input",
                    {InputTask.config_name: plate_resources["folder_metadata"].id},
                )

                stacker_keys = [
                    {"key": "raw_data"},
                    {"key": "folder_metadata"},
                ]

                if "info_table" in plate_resources:
                    stacker_keys.append({"key": "info_table"})

                stacker = protocol.add_process(
                    ResourceStacker, f"{plate_name}_stacker", {"keys": stacker_keys}
                )

                protocol.add_connector(
                    out_port=raw_data_input >> "resource", in_port=stacker << "source"
                )

                port_folder_metadata = protocol.add_process_dynamic_input_port(
                    f"{plate_name}_stacker"
                )
                protocol.add_connector(
                    out_port=folder_metadata_input >> "resource", in_port=port_folder_metadata
                )

                if "info_table" in plate_resources:
                    info_table_input = protocol.add_process(
                        InputTask,
                        f"{plate_name}_info_table_input",
                        {InputTask.config_name: plate_resources["info_table"].id},
                    )
                    port_info_table = protocol.add_process_dynamic_input_port(
                        f"{plate_name}_stacker"
                    )
                    protocol.add_connector(
                        out_port=info_table_input >> "resource", in_port=port_info_table
                    )

                plate_stackers.append(stacker)

            # Add the BiolectorXT data loading task
            # No need to pass column names - they are standardized
            biolector_load_process: ProcessProxy = protocol.add_process(
                BiolectorXTLoadData,
                cell_culture_state.PROCESS_NAME_DATA_PROCESSING,
                {"plate_names": plate_names},
            )

            # Connect medium_table if provided
            if medium_table_model is not None:
                protocol.add_connector(
                    out_port=medium_table_input >> "resource",
                    in_port=biolector_load_process << "medium_table",
                )

            # Connect plate stackers
            for stacker in plate_stackers:
                dynamic_port = protocol.add_process_dynamic_input_port(
                    cell_culture_state.PROCESS_NAME_DATA_PROCESSING
                )
                protocol.add_connector(out_port=stacker >> "resource_set", in_port=dynamic_port)

            # Add outputs
            protocol.add_output(
                cell_culture_state.LOAD_SCENARIO_OUTPUT_NAME,
                biolector_load_process >> "resource_set",
                flag_resource=True,
            )

            protocol.add_output(
                "venn_diagram", biolector_load_process >> "venn_diagram", flag_resource=False
            )

            protocol.add_output(
                "metadata_table", biolector_load_process >> "metadata_table", flag_resource=False
            )

            protocol.add_output(
                "medium_table", biolector_load_process >> "medium_table", flag_resource=False
            )

            # Add tags
            analysis_name_parsed = Tag.parse_tag(analysis_name)
            pipeline_id = StringHelper.generate_uuid()

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
                Tag(cell_culture_state.TAG_FERMENTOR_PIPELINE_ID, pipeline_id, is_propagable=False)
            )
            scenario.add_tag(
                Tag(cell_culture_state.TAG_MICROPLATE_ANALYSIS, "true", is_propagable=False)
            )

            # Resource tags for the plates
            for plate_idx, plate_info in enumerate(plates_resources):
                plate_resources = plate_info["resources"]
                scenario.add_tag(
                    Tag(
                        f"plate_{plate_idx}_raw_data",
                        Tag.parse_tag(plate_resources["raw_data"].name),
                        is_propagable=False,
                    )
                )
                scenario.add_tag(
                    Tag(
                        f"plate_{plate_idx}_folder_metadata",
                        Tag.parse_tag(plate_resources["folder_metadata"].name),
                        is_propagable=False,
                    )
                )
                if "info_table" in plate_resources:
                    scenario.add_tag(
                        Tag(
                            f"plate_{plate_idx}_info_table",
                            Tag.parse_tag(plate_resources["info_table"].name),
                            is_propagable=False,
                        )
                    )

            if medium_table_model:
                scenario.add_tag(
                    Tag(
                        "medium_table_file",
                        Tag.parse_tag(medium_table_model.name),
                        is_propagable=False,
                    )
                )

            # Add to queue and navigate back
            scenario.add_to_queue()

            st.success(
                translate_service.translate("recipe_created").format(recipe_name=analysis_name)
            )
            st.info(translate_service.translate("creating_recipe"))

            with st.spinner(translate_service.translate("view_recipe")):
                time.sleep(2)

            router.navigate("first-page")
            st.rerun()

        except Exception as e:
            error_message = f"{translate_service.translate('error_creating_recipe')}\n\n**{translate_service.translate('error_details')}** {str(e)}"
            st.error(error_message)

            with st.expander(translate_service.translate("technical_details"), expanded=False):
                st.exception(e)
