"""
Main Analysis Page for Fermentalg Dashboard
Coordinates the different analysis steps and sub-pages
"""
import streamlit as st
from typing import Dict, List, Optional, Tuple

from gws_core import Scenario, ScenarioStatus
from gws_core.streamlit import StreamlitContainers, StreamlitTreeMenu, StreamlitTreeMenuItem, StreamlitRouter
from gws_plate_reader.fermentalg_dashboard._fermentalg_dashboard_core.state import State
from .analysis_steps import (
    render_overview_step,
    render_selection_step,
    render_table_view_step,
    render_graph_view_step
)


# Helper functions similar to ubiome
def has_successful_scenario(step_name: str, scenarios_by_step: Dict[str, List[Scenario]]) -> bool:
    """Check if steps are completed (have successful scenarios)"""
    if step_name not in scenarios_by_step:
        return False
    return any(s.status == ScenarioStatus.SUCCESS for s in scenarios_by_step[step_name])


def get_step_icon(
        step_name: str, scenarios_by_step: Dict[str, List[Scenario]],
        list_scenarios: Optional[List[Scenario]] = None) -> str:
    """Get icon for step - check_circle if step has scenarios, empty otherwise."""
    if step_name not in scenarios_by_step:
        return ''
    if not list_scenarios:
        return ''
    return 'check_circle'


def build_analysis_tree_menu(fermentalg_state: State) -> Tuple[StreamlitTreeMenu, str]:
    """Build tree menu for analysis navigation"""

    translate_service = fermentalg_state.get_translate_service()

    # Create tree menu
    button_menu = StreamlitTreeMenu()

    # Get Analyse instance to check if selection has been done
    analyse = fermentalg_state.get_selected_analyse_instance()

    # Overview section (always visible if there's a load scenario)
    overview_item = StreamlitTreeMenuItem(
        label=translate_service.translate('overview'),
        key='apercu',
        material_icon='description'
    )
    button_menu.add_item(overview_item)

    # Selection section (always visible to allow creating new selections)
    selection_item = StreamlitTreeMenuItem(
        label=translate_service.translate('selection'),
        key='selection',
        material_icon='check_box'
    )
    button_menu.add_item(selection_item)

    # Selection folders (one folder per selection with sub-items for Table and Graph views)
    if analyse and analyse.has_selection_scenarios():
        selection_scenarios = analyse.get_selection_scenarios_organized()

        for selection_name, scenario in selection_scenarios.items():
            # Create folder for this selection
            selection_folder = StreamlitTreeMenuItem(
                label=selection_name,
                key=f'selection_folder_{scenario.id}',
                material_icon='folder'
            )

            # Add table view sub-item
            table_sub_item = StreamlitTreeMenuItem(
                label=translate_service.translate('table'),
                key=f'tableau_{scenario.id}',
                material_icon='table_chart'
            )
            selection_folder.add_child(table_sub_item)

            # Add graph view sub-item
            graph_sub_item = StreamlitTreeMenuItem(
                label=translate_service.translate('graphs'),
                key=f'graphiques_{scenario.id}',
                material_icon='analytics'
            )
            selection_folder.add_child(graph_sub_item)

            button_menu.add_item(selection_folder)

    return button_menu, 'apercu'


def render_analysis_page(fermentalg_state: State) -> None:
    """Render the analysis page with tree navigation structure"""

    translate_service = fermentalg_state.get_translate_service()

    style = """
    [CLASS_NAME] {
        padding: 40px;
    }
    """

    with StreamlitContainers.container_full_min_height('container-center_analysis_page',
                                                       additional_style=style):

        # Create two columns like ubiome
        left_col, right_col = st.columns([1, 4])

        # Get Analyse instance from state (created in first_page)
        analyse = fermentalg_state.get_selected_analyse_instance()
        if not analyse:
            st.error(translate_service.translate('no_analysis_selected'))
            return

        with left_col:
            # Add return button at the top
            router = StreamlitRouter.load_from_session()

            if st.button(translate_service.translate('analyses_list'),
                         icon=":material/arrow_back:", use_container_width=True):
                router.navigate("first-page")
                st.rerun()

            st.markdown("---")  # Separator line

            # Build and display navigation menu
            button_menu, key_default_item = build_analysis_tree_menu(fermentalg_state)

            # Display menu and get selected item
            selected_item = button_menu.render()
            selected_key = selected_item.key if selected_item else key_default_item

        with right_col:
            # Title section with analysis info
            st.markdown(f"### 🧪 {analyse.name}")

            # Render the selected step
            if selected_key == 'apercu':
                render_overview_step(analyse, fermentalg_state)
            elif selected_key == 'selection':
                render_selection_step(analyse, fermentalg_state)
            elif selected_key.startswith('tableau_'):
                # Extract scenario ID from key
                scenario_id = selected_key.replace('tableau_', '')
                # Find the corresponding scenario
                selection_scenarios = analyse.get_selection_scenarios()
                target_scenario = next((s for s in selection_scenarios if s.id == scenario_id), None)
                if target_scenario:
                    render_table_view_step(analyse, fermentalg_state, selection_scenario=target_scenario)
                else:
                    st.error(translate_service.translate('selection_scenario_not_found'))
            elif selected_key.startswith('graphiques_'):
                # Extract scenario ID from key
                scenario_id = selected_key.replace('graphiques_', '')
                # Find the corresponding scenario
                selection_scenarios = analyse.get_selection_scenarios()
                target_scenario = next((s for s in selection_scenarios if s.id == scenario_id), None)
                if target_scenario:
                    render_graph_view_step(analyse, fermentalg_state, selection_scenario=target_scenario)
                else:
                    st.error(translate_service.translate('selection_scenario_not_found'))
            else:
                st.info(translate_service.translate('select_step_in_menu'))
