"""
New Analysis Page for Greencell Fermentor Dashboard
Allows users to create new Greencell Fermentor analyses by uploading and configuring data
"""
import streamlit as st

from gws_core import (
    StringHelper, Tag, InputTask, ResourceModel, ResourceOrigin,
    ProcessProxy, ScenarioProxy, ProtocolProxy, ScenarioCreationType
)
from gws_core.streamlit import (
    StreamlitResourceSelect, StreamlitRouter, StreamlitContainers
)
from gws_plate_reader.greencell_fermentor_dashboard._greencell_fermentor_dashboard_core.greencell_fermentor_state import GreencellFermentorState
from gws_plate_reader.greencell_fermentor_load_data.greencell_fermentor_load_data import GreencellFermentorLoadData


def render_new_recipe_page(greencell_state: GreencellFermentorState) -> None:
    """Render the new analysis creation page"""

    translate_service = greencell_state.get_translate_service()

    style = """
    [CLASS_NAME] {
        padding: 40px;
    }
    """

    with StreamlitContainers.container_full_min_height('container-center_new_analysis_page',
                                                       additional_style=style):

        # Add a return button
        router = StreamlitRouter.load_from_session()

        if st.button(
            f"{translate_service.translate('return_to_recipes')}", icon=":material/arrow_back:",
                use_container_width=False):
            router.navigate("first-page")

        st.markdown(f"## 🧬 {translate_service.translate('new_recipe_greencell')}")

        # Recipe details (outside form for better UX)
        st.subheader(f"📝 {translate_service.translate('recipe_details')}")

        analysis_name = st.text_input(
            translate_service.translate("recipe_name_label"),
            key="analysis_name_input",
            placeholder=translate_service.translate("recipe_name_placeholder")
        )

        # Upload the 3 required files
        st.subheader(f"📁 {translate_service.translate('import_required_files')}")

        # Documentation link button
        url_doc_context = "https://constellab.community/bricks/gws_plate_reader/latest/doc/technical-folder/task/BiolectorLoadData"
        st.link_button("**?**", url_doc_context)

        st.info(translate_service.translate('import_files_info'))

        # Add option to choose between upload or select existing resources
        file_input_mode = st.radio(
            translate_service.translate('file_input_mode_label'),
            options=['upload', 'select_existing'],
            format_func=lambda x: translate_service.translate(f'file_input_mode_{x}'),
            key="file_input_mode_radio",
            horizontal=True,
            help=translate_service.translate('file_input_mode_help')
        )

        if file_input_mode == 'upload':
            # Create 1x3 grid for file uploads
            upload_col1, upload_col2, upload_col3 = st.columns(3)

            with upload_col1:
                st.write(f"**1. {translate_service.translate('file_info_csv')}**")
                info_csv_file = st.file_uploader(
                    translate_service.translate("select_info_csv"),
                    type=['csv'],
                    key="greencell_info_csv_uploader",
                    help=translate_service.translate("info_csv_help")
                )

            with upload_col2:
                st.write(f"**2. {translate_service.translate('file_medium_csv')}**")
                medium_csv_file = st.file_uploader(
                    translate_service.translate("select_medium_csv"),
                    type=['csv'],
                    key="greencell_medium_csv_uploader",
                    help=translate_service.translate("medium_csv_help")
                )

            with upload_col3:
                st.write(f"**3. {translate_service.translate('file_followup_zip')}**")
                followup_zip_file = st.file_uploader(
                    translate_service.translate("select_followup_zip"),
                    type=['zip'],
                    key="greencell_followup_zip_uploader",
                    help=translate_service.translate("followup_zip_help")
                )

            # Set resource selector values to None
            info_csv_resource = None
            medium_csv_resource = None
            followup_zip_resource = None

        else:  # select_existing mode
            # Create 1x3 grid for resource selection
            select_col1, select_col2, select_col3 = st.columns(3)

            with select_col1:
                st.write(f"**1. {translate_service.translate('file_info_csv')}**")
                resource_select_info = StreamlitResourceSelect()
                resource_select_info.filters['resourceTypingNames'] = ['RESOURCE.gws_core.File']
                resource_select_info.select_resource(
                    placeholder=translate_service.translate("select_info_csv_resource"),
                    key="greencell_info_csv_selector",
                    defaut_resource=None
                )

            with select_col2:
                st.write(f"**2. {translate_service.translate('file_medium_csv')}**")
                resource_select_medium = StreamlitResourceSelect()
                resource_select_medium.filters['resourceTypingNames'] = ['RESOURCE.gws_core.File']
                resource_select_medium.select_resource(
                    placeholder=translate_service.translate("select_medium_csv_resource"),
                    key="greencell_medium_csv_selector",
                    defaut_resource=None
                )

            with select_col3:
                st.write(f"**3. {translate_service.translate('file_followup_zip')}**")
                resource_select_followup = StreamlitResourceSelect()
                resource_select_followup.filters['resourceTypingNames'] = ['RESOURCE.gws_core.File']
                resource_select_followup.select_resource(
                    placeholder=translate_service.translate("select_followup_zip_resource"),
                    key="greencell_followup_zip_selector",
                    defaut_resource=None
                )

            # Get selected resource IDs from session state
            if "greencell_info_csv_selector" not in st.session_state:
                st.session_state["greencell_info_csv_selector"] = {}
            if "greencell_medium_csv_selector" not in st.session_state:
                st.session_state["greencell_medium_csv_selector"] = {}
            if "greencell_followup_zip_selector" not in st.session_state:
                st.session_state["greencell_followup_zip_selector"] = {}

            info_csv_resource = st.session_state.get("greencell_info_csv_selector").get(
                "resourceId", None) if st.session_state.get("greencell_info_csv_selector") else None
            medium_csv_resource = st.session_state.get("greencell_medium_csv_selector").get(
                "resourceId", None) if st.session_state.get("greencell_medium_csv_selector") else None
            followup_zip_resource = st.session_state.get("greencell_followup_zip_selector").get(
                "resourceId", None) if st.session_state.get("greencell_followup_zip_selector") else None

            # Set file uploader values to None
            info_csv_file = None
            medium_csv_file = None
            followup_zip_file = None

        # Submit button
        submit_button = st.button(
            label=f"🚀 {translate_service.translate('create_recipe_button')}",
            type="primary",
            use_container_width=True,
            key="create_recipe_submit_button"
        )

        if submit_button:
            # Validation
            missing_fields = []

            # Check analysis name
            if not analysis_name or not analysis_name.strip():
                missing_fields.append(translate_service.translate("recipe_name_label"))

            # Validate based on input mode
            if file_input_mode == 'upload':
                # Check all 3 file uploads
                uploaded_files = {
                    'info_csv': (info_csv_file, "Info CSV"),
                    'medium_csv': (medium_csv_file, "Medium CSV"),
                    'followup_zip': (followup_zip_file, "Follow-up ZIP")
                }

                for file_key, (file_obj, file_name) in uploaded_files.items():
                    if file_obj is None:
                        missing_fields.append(file_name)
            else:  # select_existing mode
                # Check all 3 resource selections
                selected_resources = {
                    'info_csv': (info_csv_resource, "Info CSV"),
                    'medium_csv': (medium_csv_resource, "Medium CSV"),
                    'followup_zip': (followup_zip_resource, "Follow-up ZIP")
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

                if file_input_mode == 'upload':
                    # Create File resources from uploaded files
                    from gws_core import File
                    import tempfile
                    import os

                    # Define uploaded files mapping
                    uploaded_files = {
                        'info_csv': info_csv_file,
                        'medium_csv': medium_csv_file,
                        'followup_zip': followup_zip_file
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

                    # Create ResourceModel from File resources
                    for file_key, file_resource in file_resources.items():
                        resource_model = ResourceModel.save_from_resource(
                            resource=file_resource,
                            origin=ResourceOrigin.UPLOADED,
                            scenario=None,
                            task_model=None,
                            flagged=True
                        )
                        file_resource_models[file_key] = resource_model

                else:  # select_existing mode
                    # Get existing resource models from IDs
                    selected_resources = {
                        'info_csv': info_csv_resource,
                        'medium_csv': medium_csv_resource,
                        'followup_zip': followup_zip_resource
                    }

                    # Validate that all selected resources are File type
                    invalid_resources = []
                    for resource_key, resource_id in selected_resources.items():
                        if resource_id is not None:
                            resource_model = ResourceModel.get_by_id(resource_id)

                            if resource_model.resource_typing_name != 'RESOURCE.gws_core.File':
                                resource_name_mapping = {
                                    'info_csv': "Info CSV",
                                    'medium_csv': "Medium CSV",
                                    'followup_zip': "Follow-up ZIP"
                                }
                                invalid_resources.append(
                                    f"{resource_name_mapping[resource_key]} ({resource_model.name})"
                                )
                            else:
                                file_resource_models[resource_key] = resource_model

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
                    title=f"{analysis_name} - Greencell Fermentor",
                    creation_type=ScenarioCreationType.MANUAL,
                )

                protocol: ProtocolProxy = scenario.get_protocol()

                # Add input tasks for each file resource
                info_csv_input = protocol.add_process(
                    InputTask, 'info_csv_input',
                    {InputTask.config_name: file_resource_models['info_csv'].id})

                medium_csv_input = protocol.add_process(
                    InputTask, greencell_state.MEDIUM_CSV_INPUT_KEY,
                    {InputTask.config_name: file_resource_models['medium_csv'].id})

                follow_up_zip_input = protocol.add_process(
                    InputTask, 'follow_up_zip_input',
                    {InputTask.config_name: file_resource_models['followup_zip'].id})

                # Add the Greencell Fermentor data loading task
                greencell_load_process: ProcessProxy = protocol.add_process(
                    GreencellFermentorLoadData,
                    'greencell_fermentor_data_processing'
                )

                # Connect the inputs to the task
                protocol.add_connector(
                    out_port=info_csv_input >> 'resource',
                    in_port=greencell_load_process << 'info_csv')
                protocol.add_connector(
                    out_port=medium_csv_input >> 'resource',
                    in_port=greencell_load_process << 'medium_csv')
                protocol.add_connector(
                    out_port=follow_up_zip_input >> 'resource',
                    in_port=greencell_load_process << 'follow_up_zip')

                # Add outputs
                protocol.add_output(
                    greencell_state.LOAD_SCENARIO_OUTPUT_NAME,
                    greencell_load_process >> 'resource_set',
                    flag_resource=True
                )

                # Add venn diagram output (optional)
                protocol.add_output(
                    'venn_diagram',
                    greencell_load_process >> 'venn_diagram',
                    flag_resource=False
                )

                # Add medium table output (optional)
                protocol.add_output(
                    'medium_table',
                    greencell_load_process >> 'medium_table',
                    flag_resource=False
                )

                # Add metadata table output (optional)
                protocol.add_output(
                    'metadata_table',
                    greencell_load_process >> 'metadata_table',
                    flag_resource=False
                )

                # Add tags for identification
                analysis_name_parsed = Tag.parse_tag(analysis_name)
                pipeline_id = StringHelper.generate_uuid()

                # Core tags
                scenario.add_tag(Tag(greencell_state.TAG_FERMENTOR,
                                     greencell_state.TAG_DATA_PROCESSING,
                                     is_propagable=False))
                scenario.add_tag(Tag(greencell_state.TAG_FERMENTOR_RECIPE_NAME,
                                     analysis_name_parsed,
                                     is_propagable=False))
                scenario.add_tag(Tag(greencell_state.TAG_FERMENTOR_PIPELINE_ID,
                                     pipeline_id,
                                     is_propagable=False))

                # Resource tags for the 3 files
                scenario.add_tag(Tag("info_csv_file", Tag.parse_tag(
                    file_resource_models['info_csv'].name), is_propagable=False))
                scenario.add_tag(Tag("medium_csv_file", Tag.parse_tag(
                    file_resource_models['medium_csv'].name), is_propagable=False))
                scenario.add_tag(Tag("followup_zip_file", Tag.parse_tag(
                    file_resource_models['followup_zip'].name), is_propagable=False))

                # Add to queue and navigate back
                scenario.add_to_queue()

                st.success(translate_service.translate('recipe_created').format(recipe_name=analysis_name))
                st.info(translate_service.translate('creating_recipe'))

                # Navigate back after a short delay
                with st.spinner(translate_service.translate('view_recipe')):
                    import time
                    time.sleep(2)

                router.navigate("first-page")
                st.rerun()

            except Exception as e:
                error_message = f"{translate_service.translate('error_creating_recipe')}\n\n**{translate_service.translate('error_details')}** {str(e)}"
                st.error(error_message)

                with st.expander(translate_service.translate('technical_details'), expanded=False):
                    st.exception(e)
