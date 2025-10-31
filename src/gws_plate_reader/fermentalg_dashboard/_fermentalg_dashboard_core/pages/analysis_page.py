"""
Main Analysis Page for Fermentalg Dashboard
Coordinates the different analysis steps and sub-pages
"""
import streamlit as st
from typing import Dict, List, Optional, Tuple

from gws_core import Scenario, ScenarioStatus
from gws_core.streamlit import StreamlitContainers, StreamlitTreeMenu, StreamlitTreeMenuItem, StreamlitRouter
from gws_plate_reader.fermentalg_dashboard._fermentalg_dashboard_core.fermentalg_state import FermentalgState
from .analysis_steps import (
    render_overview_step,
    render_selection_step,
    render_quality_check_step,
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


def build_analysis_tree_menu(fermentalg_state: FermentalgState) -> Tuple[StreamlitTreeMenu, str]:
    """Build tree menu for analysis navigation"""

    translate_service = fermentalg_state.get_translate_service()

    # Create tree menu
    button_menu = StreamlitTreeMenu()

    # Get Recipe instance to check if selection has been done
    recipe = fermentalg_state.get_selected_recipe_instance()

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

    # Selection folders (one folder per selection with sub-items for Table, Graph, and Quality Check views)
    if recipe and recipe.has_selection_scenarios():
        selection_scenarios = recipe.get_selection_scenarios_organized()

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

            # Add Quality Check folder - clicking on it opens the QC creation form
            quality_check_folder = StreamlitTreeMenuItem(
                label="🔍 Quality Check",
                key=f'quality_check_{scenario.id}',
                material_icon='folder'
            )

            # Add quality check scenario sub-folders with their own Table/Graph views
            quality_check_scenarios = recipe.get_quality_check_scenarios_for_selection(scenario.id)
            if quality_check_scenarios:
                for qc_scenario in quality_check_scenarios:
                    qc_timestamp = "QC"
                    if "Quality Check - " in qc_scenario.title:
                        qc_timestamp = qc_scenario.title.replace("Quality Check - ", "")

                    # Create folder for this QC scenario
                    qc_folder = StreamlitTreeMenuItem(
                        label=qc_timestamp,
                        key=f'qc_folder_{qc_scenario.id}',
                        material_icon='science'
                    )

                    # Add Table view for QC results
                    qc_table_item = StreamlitTreeMenuItem(
                        label=translate_service.translate('table'),
                        key=f'qc_table_{qc_scenario.id}',
                        material_icon='table_chart'
                    )
                    qc_folder.add_child(qc_table_item)

                    # Add Graph view for QC results
                    qc_graph_item = StreamlitTreeMenuItem(
                        label=translate_service.translate('graphs'),
                        key=f'qc_graph_{qc_scenario.id}',
                        material_icon='analytics'
                    )
                    qc_folder.add_child(qc_graph_item)

                    quality_check_folder.add_child(qc_folder)

            selection_folder.add_child(quality_check_folder)
            button_menu.add_item(selection_folder)

    return button_menu, 'apercu'


def render_analysis_page(fermentalg_state: FermentalgState) -> None:
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

        # Get Recipe instance from state (created in first_page)
        recipe = fermentalg_state.get_selected_recipe_instance()
        if not recipe:
            st.error(translate_service.translate('no_recipe_selected'))
            return

        with left_col:
            # Add return button at the top
            router = StreamlitRouter.load_from_session()

            if st.button(translate_service.translate('recipes_list'),
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
            # Title section with recipe info
            st.markdown(f"### 🧪 {recipe.name}")

            # Render the selected step
            if selected_key == 'apercu':
                render_overview_step(recipe, fermentalg_state)
            elif selected_key == 'selection':
                render_selection_step(recipe, fermentalg_state)
            elif selected_key.startswith('quality_check_'):
                # Extract selection scenario ID from key (quality_check_{selection_id})
                selection_id = selected_key.replace('quality_check_', '')
                # Find the corresponding selection scenario
                selection_scenarios = recipe.get_selection_scenarios()
                target_selection_scenario = next((s for s in selection_scenarios if s.id == selection_id), None)
                if target_selection_scenario:
                    render_quality_check_step(recipe, fermentalg_state, selection_scenario=target_selection_scenario)
                else:
                    st.error(translate_service.translate('selection_scenario_not_found'))
            elif selected_key.startswith('tableau_'):
                # Extract scenario ID from key
                scenario_id = selected_key.replace('tableau_', '')
                # Find the corresponding scenario
                selection_scenarios = recipe.get_selection_scenarios()
                target_scenario = next((s for s in selection_scenarios if s.id == scenario_id), None)
                if target_scenario:
                    render_table_view_step(
                        recipe,
                        fermentalg_state,
                        scenario=target_scenario,
                        output_name=fermentalg_state.INTERPOLATION_SCENARIO_OUTPUT_NAME
                    )
                else:
                    st.error(translate_service.translate('selection_scenario_not_found'))
            elif selected_key.startswith('qc_table_'):
                # Extract quality check scenario ID from key
                qc_scenario_id = selected_key.replace('qc_table_', '')
                # Find the corresponding quality check scenario
                all_qc_scenarios = recipe.get_quality_check_scenarios()
                target_qc_scenario = next((s for s in all_qc_scenarios if s.id == qc_scenario_id), None)
                if target_qc_scenario:
                    # Display quality check results in table view
                    render_table_view_step(
                        recipe,
                        fermentalg_state,
                        scenario=target_qc_scenario,
                        output_name=fermentalg_state.QUALITY_CHECK_SCENARIO_OUTPUT_NAME
                    )
                else:
                    st.error("Quality Check scenario not found")
            elif selected_key.startswith('qc_graph_'):
                # Extract quality check scenario ID from key
                qc_scenario_id = selected_key.replace('qc_graph_', '')
                # Find the corresponding quality check scenario
                all_qc_scenarios = recipe.get_quality_check_scenarios()
                target_qc_scenario = next((s for s in all_qc_scenarios if s.id == qc_scenario_id), None)
                if target_qc_scenario:
                    # Display quality check results in graph view
                    render_graph_view_step(
                        recipe,
                        fermentalg_state,
                        scenario=target_qc_scenario,
                        output_name=fermentalg_state.QUALITY_CHECK_SCENARIO_OUTPUT_NAME
                    )
                else:
                    st.error("Quality Check scenario not found")
            elif selected_key.startswith('graphiques_'):
                # Extract scenario ID from key
                scenario_id = selected_key.replace('graphiques_', '')
                # Find the corresponding scenario
                selection_scenarios = recipe.get_selection_scenarios()
                target_scenario = next((s for s in selection_scenarios if s.id == scenario_id), None)
                if target_scenario:
                    render_graph_view_step(
                        recipe,
                        fermentalg_state,
                        scenario=target_scenario,
                        output_name=fermentalg_state.INTERPOLATION_SCENARIO_OUTPUT_NAME
                    )
                else:
                    st.error(translate_service.translate('selection_scenario_not_found'))
            else:
                st.info(translate_service.translate('select_step_in_menu'))
