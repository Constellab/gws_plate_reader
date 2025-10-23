import streamlit as st
from typing import List
from gws_core.streamlit import StreamlitContainers, StreamlitRouter
from gws_core import Tag, ScenarioSearchBuilder, Scenario
from gws_core.tag.tag_entity_type import TagEntityType
from gws_core.tag.entity_tag_list import EntityTagList
from gws_plate_reader.fermentalg_dashboard._fermentalg_dashboard_core.state import State
from gws_plate_reader.fermentalg_dashboard._fermentalg_dashboard_core.analyse import Analyse
from gws_plate_reader.fermentalg_dashboard._fermentalg_dashboard_core.functions_steps import (
    render_fermentalg_analysis_table,
    create_fermentalg_analysis_table_data
)


def render_first_page(fermentalg_state: State) -> None:
    """Render the main page showing list of existing analyses."""

    translate_service = fermentalg_state.get_translate_service()

    style = """
    [CLASS_NAME] {
        padding: 40px;
    }
    """

    with StreamlitContainers.container_full_min_height('container-center_first_page',
                                                       additional_style=style):

        # Header with title and create new analysis button
        col_title, col_button_new = StreamlitContainers.columns_with_fit_content(
            key="button_new",
            cols=[1, 'fit-content'], vertical_align_items='center')

        with col_title:
            st.markdown(f"## {translate_service.translate('analyses_list_title')}")

        with col_button_new:
            if st.button(translate_service.translate("create_new_analysis"),
                         icon=":material/add:", use_container_width=False, type="primary"):
                # Navigate to new analysis page
                router = StreamlitRouter.load_from_session()
                router.navigate("new-analysis")

        # Search for existing Fermentalg analyses (both load and selection scenarios)
        # Get load scenarios
        load_scenarios = ScenarioSearchBuilder() \
            .add_tag_filter(Tag(key=fermentalg_state.TAG_FERMENTOR_FERMENTALG, value=fermentalg_state.TAG_DATA_PROCESSING)) \
            .add_is_archived_filter(False) \
            .search_all()

        # Get selection scenarios
        selection_scenarios = ScenarioSearchBuilder() \
            .add_tag_filter(Tag(key=fermentalg_state.TAG_FERMENTOR_FERMENTALG, value=fermentalg_state.TAG_SELECTION_PROCESSING)) \
            .add_is_archived_filter(False) \
            .search_all()

        # Create dictionary with analysis name as key and scenarios structure as value
        analyses_dict = {}

        # First, organize load scenarios by analysis name
        for scenario in load_scenarios:
            entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)
            analysis_name_tags = entity_tag_list.get_tags_by_key(fermentalg_state.TAG_FERMENTOR_ANALYSIS_NAME)
            analysis_name = analysis_name_tags[0].tag_value if analysis_name_tags else scenario.title

            if analysis_name not in analyses_dict:
                analyses_dict[analysis_name] = {
                    'load_scenario': None,
                    'selection_scenarios': []
                }
            analyses_dict[analysis_name]['load_scenario'] = scenario

        # Then, add selection scenarios to their corresponding analyses
        for scenario in selection_scenarios:
            entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)
            analysis_name_tags = entity_tag_list.get_tags_by_key(fermentalg_state.TAG_FERMENTOR_ANALYSIS_NAME)
            analysis_name = analysis_name_tags[0].tag_value if analysis_name_tags else scenario.title

            if analysis_name in analyses_dict:
                analyses_dict[analysis_name]['selection_scenarios'].append(scenario)

        # Combine all scenarios for table display
        list_scenario_user: List[Scenario] = load_scenarios + selection_scenarios

        # Use the new centralized function to render the table
        selected_scenario_id = render_fermentalg_analysis_table(list_scenario_user, fermentalg_state)

        if selected_scenario_id:
            print(f"SELECTED {selected_scenario_id}")

            # Find the selected analysis name
            selected_analysis_name = None
            selected_load_scenario = None

            # Check if selected_scenario_id corresponds to a load scenario
            for scenario in load_scenarios:
                if scenario.id == selected_scenario_id:
                    entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)
                    analysis_name_tags = entity_tag_list.get_tags_by_key(fermentalg_state.TAG_FERMENTOR_ANALYSIS_NAME)
                    selected_analysis_name = analysis_name_tags[0].tag_value if analysis_name_tags else scenario.title
                    selected_load_scenario = scenario
                    break

            # If not found, try to find by analysis name from table
            if not selected_analysis_name:
                table_data = create_fermentalg_analysis_table_data(list_scenario_user, fermentalg_state)
                selected_row = next((row for row in table_data if row.get("id") == selected_scenario_id), None)
                if selected_row:
                    selected_analysis_name = selected_row["Analysis Name"]
                    if selected_analysis_name in analyses_dict:
                        selected_load_scenario = analyses_dict[selected_analysis_name]['load_scenario']

            if selected_analysis_name and selected_load_scenario and selected_analysis_name in analyses_dict:
                # Create Analyse instance from load scenario only
                analyse_instance = Analyse.from_scenario(selected_load_scenario)

                # Add selection scenarios if they exist
                analysis_data = analyses_dict[selected_analysis_name]
                if analysis_data['selection_scenarios']:
                    analyse_instance.add_selection_scenarios(analysis_data['selection_scenarios'])

                # Store the complete instance in state
                fermentalg_state.set_selected_analyse_instance(analyse_instance)

                # Navigate to analysis page
                router = StreamlitRouter.load_from_session()
                router.navigate("analysis")
                st.rerun()

        # Show info message and getting started if no analyses
        if not list_scenario_user:
            st.info(f"📊 {translate_service.translate('no_fermentalg_analysis_found')}")
            st.markdown(f"### 🚀 {translate_service.translate('getting_started')}")
            st.markdown(translate_service.translate('click_create_analysis'))

            # Show example of what the analysis includes
            with st.expander(f"ℹ️ {translate_service.translate('what_is_analysis')}"):
                st.markdown(f"""
                {translate_service.translate('analysis_includes')}

                **📁 {translate_service.translate('required_input_files')}**
                - {translate_service.translate('info_csv_desc')}
                - {translate_service.translate('raw_data_csv_desc')}
                - {translate_service.translate('medium_csv_desc')}
                - {translate_service.translate('follow_up_zip_desc')}

                **🔄 {translate_service.translate('automatic_processing')}**
                - {translate_service.translate('processing_merge')}
                - {translate_service.translate('processing_detect')}
                - {translate_service.translate('processing_create')}

                **📊 {translate_service.translate('results')}**
                - {translate_service.translate('results_cleaned')}
                - {translate_service.translate('results_viz')}
                - {translate_service.translate('results_stats')}
                - {translate_service.translate('results_export')}
                """)

            # Add direct call-to-action
            st.markdown("---")
            if st.button(f"🆕 {translate_service.translate('create_first_analysis')}", type="primary",
                         use_container_width=True):
                router = StreamlitRouter.load_from_session()
                router.navigate("new-analysis")
