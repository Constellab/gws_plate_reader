"""
New Analysis Page for Fermentalg Dashboard
Allows users to create new Fermentalg analyses by uploading and configuring data
"""
import streamlit as st
from typing import List, Dict

from gws_core import (
    StringHelper, Tag, InputTask, ResourceModel, ResourceOrigin,
    ProcessProxy, ScenarioProxy, ProtocolProxy, ScenarioCreationType
)
from gws_core.streamlit import (
    StreamlitResourceSelect, StreamlitRouter, StreamlitTaskRunner, StreamlitContainers
)
from gws_plate_reader.fermentalg_dashboard._fermentalg_dashboard_core.fermentalg_state import FermentalgState
from gws_plate_reader.fermentalg_load_data.fermentalg_load_data import FermentalgLoadData


def render_new_analysis_page(fermentalg_state: FermentalgState) -> None:
    """Render the new analysis creation page"""

    translate_service = fermentalg_state.get_translate_service()

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

        with st.form(clear_on_submit=False, enter_to_submit=True, key="new_analysis_form"):
            st.markdown(f"## 🧬 {translate_service.translate('new_recipe_fermentalg')}")

            # Recipe details (moved to first position)
            st.subheader(f"📝 {translate_service.translate('recipe_details')}")

            analysis_name = st.text_input(
                translate_service.translate("recipe_name_label"),
                key="analysis_name_input",
                placeholder=translate_service.translate("recipe_name_placeholder")
            )

            # Microplate checkbox (full width)
            is_microplate = st.checkbox(
                translate_service.translate("microplate_recipe"),
                key="is_microplate_checkbox",
                help=translate_service.translate("microplate_help")
            )

            # Upload the 4 required files (moved to second position with 2x2 grid)
            st.subheader(f"📁 {translate_service.translate('import_required_files')}")

            # Documentation link button
            url_doc_context = "https://constellab.community/bricks/gws_plate_reader/latest/doc/technical-folder/task/FermentalgLoadData"
            st.link_button("**?**", url_doc_context)

            st.info(translate_service.translate('import_files_info'))

            # Create 2x2 grid for file uploads
            upload_col1, upload_col2 = st.columns(2)

            with upload_col1:
                st.write(f"**1. {translate_service.translate('file_info_csv')}**")
                info_csv_file = st.file_uploader(
                    translate_service.translate("select_info_csv"),
                    type=['csv'],
                    key="fermentalg_info_csv_uploader",
                    help=translate_service.translate("info_csv_help")
                )

                st.write(f"**3. {translate_service.translate('file_medium_csv')}**")
                medium_csv_file = st.file_uploader(
                    translate_service.translate("select_medium_csv"),
                    type=['csv'],
                    key="fermentalg_medium_csv_uploader",
                    help=translate_service.translate("medium_csv_help")
                )

            with upload_col2:
                st.write(f"**2. {translate_service.translate('file_raw_data_csv')}**")
                raw_data_csv_file = st.file_uploader(
                    translate_service.translate("select_raw_data_csv"),
                    type=['csv'],
                    key="fermentalg_raw_data_csv_uploader",
                    help=translate_service.translate("raw_data_csv_help")
                )

                st.write(f"**4. {translate_service.translate('file_followup_zip')}**")
                followup_zip_file = st.file_uploader(
                    translate_service.translate("select_followup_zip"),
                    type=['zip'],
                    key="fermentalg_followup_zip_uploader",
                    help=translate_service.translate("followup_zip_help")
                )

            # Submit button
            submit_button = st.form_submit_button(
                label=f"🚀 {translate_service.translate('create_recipe_button')}",
                type="primary",
                use_container_width=True
            )

            if submit_button:
                # Validation
                missing_fields = []

                # Check all 4 file uploads
                uploaded_files = {
                    'info_csv': (info_csv_file, "Info CSV"),
                    'raw_data_csv': (raw_data_csv_file, "Raw Data CSV"),
                    'medium_csv': (medium_csv_file, "Medium CSV"),
                    'followup_zip': (followup_zip_file, "Follow-up ZIP")
                }

                for file_key, (file_obj, file_name) in uploaded_files.items():
                    if file_obj is None:
                        missing_fields.append(file_name)

                # Check analysis name
                if not analysis_name or not analysis_name.strip():
                    missing_fields.append(translate_service.translate("recipe_name_label"))

                if missing_fields:
                    # Construire le message d'erreur sous forme "Champs manquant : '..', '...'"
                    fields_str = "', '".join(missing_fields)
                    error_message = f"{translate_service.translate('fill_all_fields')} '{fields_str}'"

                    st.error(error_message)
                    return

                try:
                    # Create File resources from uploaded files
                    from gws_core import File
                    import tempfile
                    import os

                    # Save uploaded files temporarily and create File resources
                    temp_files = {}
                    file_resources = {}

                    for file_key, (file_obj, file_name) in uploaded_files.items():
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

                    # Create scenario (using default folder)
                    scenario: ScenarioProxy = ScenarioProxy(
                        None,
                        folder=None,  # Use default folder
                        title=f"{analysis_name} - Fermentalg",
                        creation_type=ScenarioCreationType.MANUAL,
                    )

                    protocol: ProtocolProxy = scenario.get_protocol()

                    # Create ResourceModel from File resources using save_from_resource
                    file_resource_models = {}
                    for file_key, file_resource in file_resources.items():
                        resource_model = ResourceModel.save_from_resource(
                            resource=file_resource,
                            origin=ResourceOrigin.UPLOADED,
                            scenario=None,
                            task_model=None,
                            flagged=True
                        )
                        file_resource_models[file_key] = resource_model

                    # Add input tasks for each file resource using the ResourceModel IDs
                    info_csv_input = protocol.add_process(
                        InputTask, 'info_csv_input',
                        {InputTask.config_name: file_resource_models['info_csv'].id})

                    raw_data_csv_input = protocol.add_process(
                        InputTask, 'raw_data_csv_input',
                        {InputTask.config_name: file_resource_models['raw_data_csv'].id})

                    medium_csv_input = protocol.add_process(
                        InputTask, 'medium_csv_input',
                        {InputTask.config_name: file_resource_models['medium_csv'].id})

                    follow_up_zip_input = protocol.add_process(
                        InputTask, 'follow_up_zip_input',
                        {InputTask.config_name: file_resource_models['followup_zip'].id})                    # Add the Fermentalg data loading task
                    fermentalg_load_process: ProcessProxy = protocol.add_process(
                        FermentalgLoadData,
                        'fermentalg_data_processing'
                    )

                    # Connect the inputs to the task using connectors
                    protocol.add_connector(
                        out_port=info_csv_input >> 'resource',
                        in_port=fermentalg_load_process << 'info_csv')
                    protocol.add_connector(
                        out_port=raw_data_csv_input >> 'resource',
                        in_port=fermentalg_load_process << 'raw_data_csv')
                    protocol.add_connector(
                        out_port=medium_csv_input >> 'resource',
                        in_port=fermentalg_load_process << 'medium_csv')
                    protocol.add_connector(
                        out_port=follow_up_zip_input >> 'resource',
                        in_port=fermentalg_load_process << 'follow_up_zip')

                    # Add outputs
                    protocol.add_output(
                        fermentalg_state.LOAD_SCENARIO_OUTPUT_NAME,
                        fermentalg_load_process >> 'resource_set',
                        flag_resource=True
                    )

                    # Add venn diagram output (optional)
                    protocol.add_output(
                        'venn_diagram',
                        fermentalg_load_process >> 'venn_diagram',
                        flag_resource=False
                    )

                    # Add tags for identification
                    analysis_name_parsed = Tag.parse_tag(analysis_name)
                    pipeline_id = StringHelper.generate_uuid()

                    # Core tags
                    scenario.add_tag(Tag(fermentalg_state.TAG_FERMENTOR_FERMENTALG,
                                         fermentalg_state.TAG_DATA_PROCESSING,
                                         is_propagable=False))
                    scenario.add_tag(Tag(fermentalg_state.TAG_FERMENTOR_RECIPE_NAME,
                                         analysis_name_parsed,
                                         is_propagable=False))
                    scenario.add_tag(Tag(fermentalg_state.TAG_FERMENTOR_FERMENTALG_PIPELINE_ID,
                                         pipeline_id,
                                         is_propagable=False))

                    # Analysis type tag
                    scenario.add_tag(Tag(fermentalg_state.TAG_MICROPLATE_ANALYSIS,
                                         "true" if is_microplate else "false",
                                         is_propagable=False))

                    # Resource tags for the 4 files
                    scenario.add_tag(Tag("info_csv_file", Tag.parse_tag(
                        file_resources['info_csv'].name), is_propagable=False))
                    scenario.add_tag(Tag("raw_data_csv_file", Tag.parse_tag(
                        file_resources['raw_data_csv'].name), is_propagable=False))
                    scenario.add_tag(Tag("medium_csv_file", Tag.parse_tag(
                        file_resources['medium_csv'].name), is_propagable=False))
                    scenario.add_tag(Tag("followup_zip_file", Tag.parse_tag(
                        file_resources['followup_zip'].name), is_propagable=False))

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
                    # Construire le message d'erreur complet
                    error_message = f"{translate_service.translate('error_creating_recipe')}\n\n**{translate_service.translate('error_details')}** {str(e)}"
                    st.error(error_message)

                    # Afficher la stack trace en mode expandable pour le debug
                    with st.expander(translate_service.translate('technical_details'), expanded=False):
                        st.exception(e)
