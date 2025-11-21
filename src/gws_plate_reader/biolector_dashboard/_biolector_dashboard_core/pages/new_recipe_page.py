"""
New Analysis Page for Biolector Dashboard
Allows users to create new Biolector analyses by uploading and configuring data
"""
import streamlit as st

from gws_core import (
    StringHelper, Tag, InputTask, ResourceModel, ResourceOrigin,
    ProcessProxy, ScenarioProxy, ProtocolProxy, ScenarioCreationType
)
from gws_core.streamlit import (
    StreamlitResourceSelect, StreamlitRouter, StreamlitContainers
)
from gws_plate_reader.biolector_dashboard._biolector_dashboard_core.biolector_state import BiolectorState
from gws_plate_reader.biolector_xt.biolector_xt import BiolectorXT


def render_new_recipe_page(biolector_state: BiolectorState) -> None:
    """Render the new analysis creation page for Biolector"""

    translate_service = biolector_state.get_translate_service()

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

        st.markdown(f"## 🧬 {translate_service.translate('new_recipe_biolector')}")

        # Recipe details
        st.subheader(f"📝 {translate_service.translate('recipe_details')}")

        analysis_name = st.text_input(
            translate_service.translate("recipe_name_label"),
            key="analysis_name_input",
            placeholder=translate_service.translate("recipe_name_placeholder")
        )

        # Upload the Biolector Excel file
        st.subheader(f"📁 {translate_service.translate('import_biolector_file')}")

        # Documentation link button
        url_doc_context = "https://constellab.community/bricks/gws_plate_reader/latest/doc/technical-folder/task/BiolectorXT"
        st.link_button("**?**", url_doc_context)

        st.info(translate_service.translate('import_biolector_file_info'))

        # Add option to choose between upload or select existing resource
        file_input_mode = st.radio(
            translate_service.translate('file_input_mode_label'),
            options=['upload', 'select_existing'],
            format_func=lambda x: translate_service.translate(f'file_input_mode_{x}'),
            key="file_input_mode_radio",
            horizontal=True,
            help=translate_service.translate('file_input_mode_help')
        )

        if file_input_mode == 'upload':
            st.write(f"**{translate_service.translate('biolector_excel_file')}**")
            biolector_file = st.file_uploader(
                translate_service.translate("select_biolector_file"),
                type=['xlsx', 'xls'],
                key="biolector_file_uploader",
                help=translate_service.translate("biolector_file_help")
            )

            # Set resource selector value to None
            biolector_resource = None

        else:  # select_existing mode
            st.write(f"**{translate_service.translate('biolector_excel_file')}**")
            resource_select_biolector = StreamlitResourceSelect()
            # Filter to show only File resources
            resource_select_biolector.filters['resourceTypingNames'] = ['RESOURCE.gws_core.File']
            resource_select_biolector.select_resource(
                placeholder=translate_service.translate("select_biolector_file_resource"),
                key="biolector_file_selector",
                defaut_resource=None
            )

            # Get selected resource ID from session state
            if "biolector_file_selector" not in st.session_state:
                st.session_state["biolector_file_selector"] = {}

            biolector_resource = st.session_state.get("biolector_file_selector").get(
                "resourceId", None) if st.session_state.get("biolector_file_selector") else None

            # Set file uploader value to None
            biolector_file = None

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

            if not analysis_name or analysis_name.strip() == "":
                missing_fields.append(translate_service.translate("recipe_name_label"))

            # Check if file is provided (either uploaded or selected)
            if file_input_mode == 'upload':
                if not biolector_file:
                    missing_fields.append(translate_service.translate("biolector_excel_file"))
            else:
                if not biolector_resource:
                    missing_fields.append(translate_service.translate("biolector_excel_file"))

            # If validation fails, show error
            if missing_fields:
                st.error(f"{translate_service.translate('missing_fields')}: {', '.join(missing_fields)}")
                return

            # Create a unique pipeline ID
            pipeline_id = StringHelper.generate_uuid()

            try:
                # Create tags for the scenario
                tags = [
                    Tag.create_tag("biolector_recipe_name", analysis_name),
                    Tag.create_tag("biolector_pipeline_id", pipeline_id),
                    Tag.create_tag("biolector", "true"),
                ]

                # Create protocol with BiolectorXT task
                process_proxy = ProcessProxy.from_process_name(BiolectorXT.get_full_classname())

                # Handle file input based on mode
                if file_input_mode == 'upload':
                    # Upload file and create resource
                    with st.spinner(translate_service.translate('uploading_file')):
                        # Save uploaded file to a resource
                        biolector_resource_model = InputTask.upload_file(
                            biolector_file, origin=ResourceOrigin.UPLOADED
                        )

                        # Add file name tag
                        biolector_resource_model.add_tag("biolector_file", biolector_file.name)
                        tags.append(Tag.create_tag("biolector_file", biolector_file.name))

                        # Set file as input to the protocol
                        process_proxy.set_input_resource("file", biolector_resource_model)
                else:
                    # Use selected existing resource
                    biolector_resource_model = ResourceModel.get_by_id(biolector_resource)

                    # Add file name tag
                    file_name = biolector_resource_model.name
                    tags.append(Tag.create_tag("biolector_file", file_name))

                    # Set file as input to the protocol
                    process_proxy.set_input_resource("file", biolector_resource_model)

                # Create scenario
                with st.spinner(translate_service.translate('creating_scenario')):
                    scenario_proxy = ScenarioProxy.create(
                        title=f"Load - {analysis_name}",
                        creation_type=ScenarioCreationType.MANUAL
                    )

                    # Set protocol
                    scenario_proxy.set_protocol(process_proxy.get_protocol())

                    # Add tags
                    for tag in tags:
                        scenario_proxy.add_tag(tag)

                    # Save scenario
                    scenario = scenario_proxy.save()

                    # Store scenario in state
                    biolector_state.set_load_scenario(scenario)
                    biolector_state.set_recipe_name(analysis_name)
                    biolector_state.set_pipeline_id(pipeline_id)
                    biolector_state.set_biolector_file_input_resource_model(biolector_resource_model)

                st.success(translate_service.translate('recipe_created_success'))
                st.info(translate_service.translate('redirect_to_recipe'))

                # Navigate to recipe page
                router.navigate("first-page")

            except Exception as e:
                st.error(f"{translate_service.translate('error_creating_recipe')}: {str(e)}")
