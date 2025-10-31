import streamlit as st
from typing import List
from gws_core.streamlit import StreamlitContainers, StreamlitRouter
from gws_core import Tag, ScenarioSearchBuilder, Scenario
from gws_core.tag.tag_entity_type import TagEntityType
from gws_core.tag.entity_tag_list import EntityTagList
from gws_plate_reader.fermentalg_dashboard._fermentalg_dashboard_core.fermentalg_state import FermentalgState
from gws_plate_reader.fermentalg_dashboard._fermentalg_dashboard_core.fermentalg_recipe import FermentalgRecipe
from gws_plate_reader.fermentalg_dashboard._fermentalg_dashboard_core.functions_steps import (
    render_fermentalg_recipe_table,
    create_fermentalg_recipe_table_data
)


def render_first_page(fermentalg_state: FermentalgState) -> None:
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
            st.markdown(f"## {translate_service.translate('recipes_list_title')}")

        with col_button_new:
            if st.button(translate_service.translate("create_new_recipe"),
                         icon=":material/add:", use_container_width=False, type="primary"):
                # Navigate to new recipe page
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

        # Get quality check scenarios
        quality_check_scenarios = ScenarioSearchBuilder() \
            .add_tag_filter(Tag(key=fermentalg_state.TAG_FERMENTOR_FERMENTALG, value=fermentalg_state.TAG_QUALITY_CHECK_PROCESSING)) \
            .add_is_archived_filter(False) \
            .search_all()

        # Create dictionary with recipe name as key and scenarios structure as value
        recipes_dict = {}

        # First, organize load scenarios by recipe name
        for scenario in load_scenarios:
            entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)
            recipe_name_tags = entity_tag_list.get_tags_by_key(fermentalg_state.TAG_FERMENTOR_RECIPE_NAME)
            recipe_name = recipe_name_tags[0].tag_value if recipe_name_tags else scenario.title

            if recipe_name not in recipes_dict:
                recipes_dict[recipe_name] = {
                    'load_scenario': None,
                    'selection_scenarios': [],
                    'quality_check_scenarios': []
                }
            recipes_dict[recipe_name]['load_scenario'] = scenario

        # Then, add selection scenarios to their corresponding recipes
        for scenario in selection_scenarios:
            entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)
            recipe_name_tags = entity_tag_list.get_tags_by_key(fermentalg_state.TAG_FERMENTOR_RECIPE_NAME)
            recipe_name = recipe_name_tags[0].tag_value if recipe_name_tags else scenario.title

            if recipe_name in recipes_dict:
                recipes_dict[recipe_name]['selection_scenarios'].append(scenario)

        # Finally, add quality check scenarios to their corresponding recipes
        for scenario in quality_check_scenarios:
            entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)
            recipe_name_tags = entity_tag_list.get_tags_by_key(fermentalg_state.TAG_FERMENTOR_RECIPE_NAME)
            recipe_name = recipe_name_tags[0].tag_value if recipe_name_tags else scenario.title

            if recipe_name in recipes_dict:
                recipes_dict[recipe_name]['quality_check_scenarios'].append(scenario)

        # Pass both load and selection scenarios - the table function will filter and group them correctly
        list_scenario_user: List[Scenario] = load_scenarios + selection_scenarios

        # Use the new centralized function to render the table
        selected_scenario_id = render_fermentalg_recipe_table(list_scenario_user, fermentalg_state)

        if selected_scenario_id:
            # Find the selected recipe name
            selected_recipe_name = None
            selected_load_scenario = None

            # Check if selected_scenario_id corresponds to a load scenario
            for scenario in load_scenarios:
                if scenario.id == selected_scenario_id:
                    entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)
                    recipe_name_tags = entity_tag_list.get_tags_by_key(fermentalg_state.TAG_FERMENTOR_RECIPE_NAME)
                    selected_recipe_name = recipe_name_tags[0].tag_value if recipe_name_tags else scenario.title
                    selected_load_scenario = scenario
                    break

            # If not found, try to find by recipe name from table
            if not selected_recipe_name:
                table_data = create_fermentalg_recipe_table_data(list_scenario_user, fermentalg_state)
                selected_row = next((row for row in table_data if row.get("id") == selected_scenario_id), None)
                if selected_row:
                    selected_recipe_name = selected_row["Recipe Name"]
                    if selected_recipe_name in recipes_dict:
                        selected_load_scenario = recipes_dict[selected_recipe_name]['load_scenario']

            if selected_recipe_name and selected_load_scenario and selected_recipe_name in recipes_dict:
                # Create Recipe instance from load scenario only
                recipe_instance = FermentalgRecipe.from_scenario(selected_load_scenario)

                # Add selection scenarios if they exist
                recipe_data = recipes_dict[selected_recipe_name]
                if recipe_data['selection_scenarios']:
                    recipe_instance.add_selection_scenarios(recipe_data['selection_scenarios'])

                # Add quality check scenarios if they exist
                if 'quality_check_scenarios' in recipe_data and recipe_data['quality_check_scenarios']:
                    recipe_instance.add_scenarios_by_step('quality_check', recipe_data['quality_check_scenarios'])

                # Store the complete instance in state
                fermentalg_state.set_selected_recipe_instance(recipe_instance)

                # Navigate to analysis page
                router = StreamlitRouter.load_from_session()
                router.navigate("analysis")
                st.rerun()

        # Show info message and getting started if no recipes
        if not list_scenario_user:
            st.info(f"📊 {translate_service.translate('no_fermentalg_recipe_found')}")
            st.markdown(f"### 🚀 {translate_service.translate('getting_started')}")
            st.markdown(translate_service.translate('click_create_recipe'))

            # Show example of what the recipe includes
            with st.expander(f"ℹ️ {translate_service.translate('what_is_recipe')}"):
                st.markdown(f"""
                {translate_service.translate('recipe_includes')}

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
