"""
New Analysis Page for BiolectorXT Dashboard
Allows users to create new BiolectorXT analyses by uploading and configuring data
"""

import os
import tempfile
import time

import streamlit as st
from gws_core import (
    Folder,
    InputTask,
    ProcessProxy,
    ProtocolProxy,
    ResourceModel,
    ResourceOrigin,
    ScenarioCreationType,
    ScenarioProxy,
    StringHelper,
    Table,
    Tag,
)
from gws_core.resource.resource_set.resource_set_tasks import ResourceStacker
from gws_core.streamlit import StreamlitContainers, StreamlitResourceSelect, StreamlitRouter

from gws_plate_reader.biolector_cell_culture_dashboard._biolector_cell_culture_dashboard_core.biolector_state import (
    BiolectorState,
)
from gws_plate_reader.biolector_xt_data_parser.biolector_xt_load_data import BiolectorXTLoadData


def render_new_recipe_page(biolector_state: BiolectorState) -> None:
    """Render the new analysis creation page"""

    translate_service = biolector_state.get_translate_service()

    style = """
    [CLASS_NAME] {
        padding: 40px;
    }
    """

    with StreamlitContainers.container_full_min_height(
        "container-center_new_analysis_page", additional_style=style
    ):
        # Add a return button aligned with title
        router = StreamlitRouter.load_from_session()

        col_back, col_title = st.columns([1, 15])

        with col_back:
            if st.button("", icon=":material/arrow_back:", width="content"):
                router.navigate("first-page")

        with col_title:
            st.markdown(f"## 🧬 {translate_service.translate('new_recipe_biolector')}")

        # Recipe details (outside form for better UX)
        st.subheader(f"📝 {translate_service.translate('recipe_details')}")

        analysis_name = st.text_input(
            translate_service.translate("recipe_name_label"),
            key="analysis_name_input",
            placeholder=translate_service.translate("recipe_name_placeholder"),
        )

        # Upload the required files
        st.subheader(f"📁 {translate_service.translate('import_required_files')}")

        st.info(translate_service.translate("import_files_info"))

        # Add option to choose between upload or select existing resources
        file_input_mode = st.radio(
            translate_service.translate("file_input_mode_label"),
            options=["select_existing", "upload"],
            format_func=lambda x: translate_service.translate(f"file_input_mode_{x}"),
            key="file_input_mode_radio",
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
                key="biolector_medium_table_uploader",
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
                key="biolector_medium_table_selector",
                defaut_resource=None,
            )
            if "biolector_medium_table_selector" not in st.session_state:
                st.session_state["biolector_medium_table_selector"] = {}
            medium_table_resource = (
                st.session_state.get("biolector_medium_table_selector").get("resourceId", None)
                if st.session_state.get("biolector_medium_table_selector")
                else None
            )
            medium_table_file = None

        # Per-plate inputs
        st.markdown("---")
        st.subheader(f"📋 {translate_service.translate('plate_configurations')}")

        # Initialize plates list in session state
        if "plates_list" not in st.session_state:
            st.session_state.plates_list = [0]  # Start with one plate (index 0)
        if "plate_counter" not in st.session_state:
            st.session_state.plate_counter = 1  # Counter for unique plate IDs

        plates_data = []

        for plate_idx in st.session_state.plates_list:
            # Plate title
            st.write(
                f"### 🧫 {translate_service.translate('plate')} {st.session_state.plates_list.index(plate_idx) + 1}"
            )

            with st.container():
                # Plate name with remove button
                col_name, col_remove = st.columns([6, 1])

                with col_name:
                    plate_name = st.text_input(
                        translate_service.translate("plate_name_label"),
                        value=f"plate_{st.session_state.plates_list.index(plate_idx) + 1}",
                        key=f"plate_name_{plate_idx}",
                        help=translate_service.translate("plate_name_help"),
                    )

                with col_remove:
                    # Remove button - always visible, disabled if only one plate
                    st.write("")  # Empty label for alignment
                    is_disabled = len(st.session_state.plates_list) <= 1
                    if st.button(
                        translate_service.translate("remove_plate"),
                        key=f"remove_plate_{plate_idx}",
                        disabled=is_disabled,
                        width="stretch",
                    ):
                        st.session_state.plates_list.remove(plate_idx)
                        st.rerun()

                if file_input_mode == "upload":
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.write(f"**{translate_service.translate('raw_data_table_required')}**")
                        raw_data_file = st.file_uploader(
                            f"{translate_service.translate('select_raw_data_table')} (CSV)",
                            type=["csv"],
                            key=f"raw_data_uploader_{plate_idx}",
                            help=translate_service.translate("raw_data_table_help"),
                        )

                    with col2:
                        st.write(f"**{translate_service.translate('folder_metadata_required')}**")
                        folder_metadata_file = st.file_uploader(
                            f"{translate_service.translate('select_folder_metadata')} (ZIP)",
                            type=["zip"],
                            key=f"folder_metadata_uploader_{plate_idx}",
                            help=translate_service.translate("folder_metadata_help"),
                        )

                    with col3:
                        st.write(f"**{translate_service.translate('info_table_optional')}**")
                        info_table_file = st.file_uploader(
                            f"{translate_service.translate('select_info_table')} (CSV)",
                            type=["csv"],
                            key=f"info_table_uploader_{plate_idx}",
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
                            key=f"raw_data_selector_{plate_idx}",
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
                            key=f"folder_metadata_selector_{plate_idx}",
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
                            key=f"info_table_selector_{plate_idx}",
                            defaut_resource=None,
                        )

                    # Initialize session state if needed
                    for key in [
                        f"raw_data_selector_{plate_idx}",
                        f"folder_metadata_selector_{plate_idx}",
                        f"info_table_selector_{plate_idx}",
                    ]:
                        if key not in st.session_state:
                            st.session_state[key] = {}

                    raw_data_resource = (
                        st.session_state.get(f"raw_data_selector_{plate_idx}").get(
                            "resourceId", None
                        )
                        if st.session_state.get(f"raw_data_selector_{plate_idx}")
                        else None
                    )
                    folder_metadata_resource = (
                        st.session_state.get(f"folder_metadata_selector_{plate_idx}").get(
                            "resourceId", None
                        )
                        if st.session_state.get(f"folder_metadata_selector_{plate_idx}")
                        else None
                    )
                    info_table_resource = (
                        st.session_state.get(f"info_table_selector_{plate_idx}").get(
                            "resourceId", None
                        )
                        if st.session_state.get(f"info_table_selector_{plate_idx}")
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
            f"➕ {translate_service.translate('add_plate')}", width="stretch", type="secondary"
        ):
            st.session_state.plates_list.append(st.session_state.plate_counter)
            st.session_state.plate_counter += 1
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
                    # Create temporary file
                    temp_dir = tempfile.gettempdir()
                    temp_file_path = os.path.join(
                        temp_dir, f"medium_table_{medium_table_file.name}"
                    )

                    # Write uploaded content to temp file
                    with open(temp_file_path, "wb") as temp_file:
                        temp_file.write(medium_table_file.getvalue())

                    # Create Table resource
                    table_resource = Table.from_csv(temp_file_path)
                    table_resource.name = medium_table_file.name

                    # Save as ResourceModel
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
                for plate_idx, plate_data in enumerate(plates_data):
                    plate_resources = {}

                    if file_input_mode == "upload":
                        # Save uploaded files as resources
                        if plate_data["raw_data_file"] is not None:
                            # Create temporary file for raw_data
                            temp_file_path = os.path.join(
                                temp_dir,
                                f"raw_data_plate_{plate_idx}_{plate_data['raw_data_file'].name}",
                            )
                            with open(temp_file_path, "wb") as temp_file:
                                temp_file.write(plate_data["raw_data_file"].getvalue())

                            # Create Table resource
                            raw_data_resource = Table.from_csv(temp_file_path)
                            raw_data_resource.name = plate_data["raw_data_file"].name

                            # Save as ResourceModel
                            plate_resources["raw_data"] = ResourceModel.save_from_resource(
                                resource=raw_data_resource,
                                origin=ResourceOrigin.UPLOADED,
                                scenario=None,
                                task_model=None,
                                flagged=True,
                            )

                        if plate_data["folder_metadata_file"] is not None:
                            # Create temporary file for folder_metadata (ZIP)
                            temp_zip_path = os.path.join(
                                temp_dir,
                                f"metadata_plate_{plate_idx}_{plate_data['folder_metadata_file'].name}",
                            )
                            with open(temp_zip_path, "wb") as temp_file:
                                temp_file.write(plate_data["folder_metadata_file"].getvalue())

                            # Create Folder resource from ZIP
                            folder_resource = Folder.from_zip(temp_zip_path)
                            folder_resource.name = plate_data["folder_metadata_file"].name

                            # Save as ResourceModel
                            plate_resources["folder_metadata"] = ResourceModel.save_from_resource(
                                resource=folder_resource,
                                origin=ResourceOrigin.UPLOADED,
                                scenario=None,
                                task_model=None,
                                flagged=True,
                            )

                        if plate_data["info_table_file"] is not None:
                            # Create temporary file for info_table
                            temp_info_path = os.path.join(
                                temp_dir,
                                f"info_table_plate_{plate_idx}_{plate_data['info_table_file'].name}",
                            )
                            with open(temp_info_path, "wb") as temp_file:
                                temp_file.write(plate_data["info_table_file"].getvalue())

                            # Create Table resource
                            info_table_resource = Table.from_csv(temp_info_path)
                            info_table_resource.name = plate_data["info_table_file"].name

                            # Save as ResourceModel
                            plate_resources["info_table"] = ResourceModel.save_from_resource(
                                resource=info_table_resource,
                                origin=ResourceOrigin.UPLOADED,
                                scenario=None,
                                task_model=None,
                                flagged=True,
                            )
                    else:
                        # Get existing resources
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

                # Create scenario (using default folder)
                scenario: ScenarioProxy = ScenarioProxy(
                    None,
                    folder=None,  # Use default folder
                    title=f"{analysis_name} - BiolectorXT",
                    creation_type=ScenarioCreationType.MANUAL,
                )

                protocol: ProtocolProxy = scenario.get_protocol()

                # Collect plate names for config
                plate_names = [plate["name"] for plate in plates_resources]

                # Add medium_table input if provided
                if medium_table_model is not None:
                    medium_table_input = protocol.add_process(
                        InputTask,
                        "medium_table_input",
                        {InputTask.config_name: medium_table_model.id},
                    )

                # Create ResourceStacker for each plate
                plate_stackers = []
                for plate_idx, plate_info in enumerate(plates_resources):
                    plate_name = plate_info["name"]
                    plate_resources = plate_info["resources"]

                    # Create InputTask for each resource in this plate
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

                    # Prepare keys for ResourceStacker based on available resources
                    stacker_keys = [
                        {"key": "raw_data"},
                        {"key": "folder_metadata"},
                    ]

                    # If info_table is provided, add it to the keys
                    if "info_table" in plate_resources:
                        stacker_keys.append({"key": "info_table"})

                    # Create ResourceStacker for this plate with all keys
                    stacker = protocol.add_process(
                        ResourceStacker, f"{plate_name}_stacker", {"keys": stacker_keys}
                    )

                    # Connect resources to stacker ports
                    # The first resource uses the default 'source' port, others need new dynamic ports

                    # Port 1 (default 'source'): raw_data
                    protocol.add_connector(
                        out_port=raw_data_input >> "resource", in_port=stacker << "source"
                    )

                    # Port 2 (new dynamic port): folder_metadata
                    port_folder_metadata = protocol.add_process_dynamic_input_port(
                        f"{plate_name}_stacker"
                    )
                    protocol.add_connector(
                        out_port=folder_metadata_input >> "resource", in_port=port_folder_metadata
                    )

                    # Port 3 (new dynamic port): info_table (if provided)
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
                biolector_load_process: ProcessProxy = protocol.add_process(
                    BiolectorXTLoadData,
                    biolector_state.PROCESS_NAME_DATA_PROCESSING,
                    {"plate_names": plate_names},
                )

                # Connect medium_table if provided
                if medium_table_model is not None:
                    protocol.add_connector(
                        out_port=medium_table_input >> "resource",
                        in_port=biolector_load_process << "medium_table",
                    )

                # For each plate stacker, create a dynamic input port and connect it
                for stacker in plate_stackers:
                    # Add a new dynamic input port to the load task
                    dynamic_port = protocol.add_process_dynamic_input_port(
                        biolector_state.PROCESS_NAME_DATA_PROCESSING
                    )
                    # Connect the stacker output to this new port
                    protocol.add_connector(out_port=stacker >> "resource_set", in_port=dynamic_port)

                # Add outputs
                protocol.add_output(
                    biolector_state.LOAD_SCENARIO_OUTPUT_NAME,
                    biolector_load_process >> "resource_set",
                    flag_resource=True,
                )

                # Add venn diagram output (optional)
                protocol.add_output(
                    "venn_diagram", biolector_load_process >> "venn_diagram", flag_resource=False
                )

                # Add metadata table output (optional)
                protocol.add_output(
                    "metadata_table",
                    biolector_load_process >> "metadata_table",
                    flag_resource=False,
                )

                # Add medium_table output (optional, pass-through)
                protocol.add_output(
                    "medium_table", biolector_load_process >> "medium_table", flag_resource=False
                )

                # Add tags for identification
                analysis_name_parsed = Tag.parse_tag(analysis_name)
                pipeline_id = StringHelper.generate_uuid()

                # Core tags
                scenario.add_tag(
                    Tag(
                        biolector_state.TAG_FERMENTOR,
                        biolector_state.TAG_DATA_PROCESSING,
                        is_propagable=False,
                    )
                )
                scenario.add_tag(
                    Tag(
                        biolector_state.TAG_FERMENTOR_RECIPE_NAME,
                        analysis_name_parsed,
                        is_propagable=False,
                    )
                )
                scenario.add_tag(
                    Tag(biolector_state.TAG_FERMENTOR_PIPELINE_ID, pipeline_id, is_propagable=False)
                )
                scenario.add_tag(
                    Tag(biolector_state.TAG_MICROPLATE_ANALYSIS, "true", is_propagable=False)
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

                # Navigate back after a short delay
                with st.spinner(translate_service.translate("view_recipe")):
                    time.sleep(2)

                router.navigate("first-page")
                st.rerun()

            except Exception as e:
                error_message = f"{translate_service.translate('error_creating_recipe')}\\n\\n**{translate_service.translate('error_details')}** {str(e)}"
                st.error(error_message)

                with st.expander(translate_service.translate("technical_details"), expanded=False):
                    st.exception(e)
