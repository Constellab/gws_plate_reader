"""
Main Analysis Page for Cell Culture Dashboards
Coordinates the different analysis steps and sub-pages
"""
import streamlit as st
from typing import Dict, List, Optional, Tuple

from gws_core import Scenario, ScenarioStatus
from gws_core.streamlit import StreamlitContainers, StreamlitTreeMenu, StreamlitTreeMenuItem, StreamlitRouter
from gws_plate_reader.cell_culture_app_core.cell_culture_state import CellCultureState
from .recipe_steps import (
    render_overview_step,
    render_selection_step,
    render_quality_check_step,
    render_table_view_step,
    render_graph_view_step,
    render_medium_view_step,
    render_medium_pca_step,
    render_medium_pca_results,
    render_medium_umap_step,
    render_medium_umap_results,
    render_feature_extraction_step,
    render_feature_extraction_results,
    render_logistic_growth_step,
    render_logistic_growth_results,
    render_spline_growth_step,
    render_spline_growth_results
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


def build_analysis_tree_menu(cell_culture_state: CellCultureState) -> Tuple[StreamlitTreeMenu, str]:
    """Build tree menu for analysis navigation"""

    translate_service = cell_culture_state.get_translate_service()

    # Create tree menu
    button_menu = StreamlitTreeMenu()

    # Get Recipe instance to check if selection has been done
    recipe = cell_culture_state.get_selected_recipe_instance()

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

            # Add medium view sub-item
            medium_sub_item = StreamlitTreeMenuItem(
                label=translate_service.translate('medium'),
                key=f'medium_{scenario.id}',
                material_icon='science'
            )
            selection_folder.add_child(medium_sub_item)

            # Add Quality Check folder - clicking on it opens the QC creation form
            quality_check_folder = StreamlitTreeMenuItem(
                label="Quality Check",
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

                    # Add Medium view for QC results
                    qc_medium_item = StreamlitTreeMenuItem(
                        label=translate_service.translate('medium'),
                        key=f'qc_medium_{qc_scenario.id}',
                        material_icon='science'
                    )
                    qc_folder.add_child(qc_medium_item)

                    # Analysis sub-folder
                    analysis_folder = StreamlitTreeMenuItem(
                        label=translate_service.translate('analysis'),
                        key=f'analysis_qc_{qc_scenario.id}',
                        material_icon='folder'
                    )
                    qc_folder.add_child(analysis_folder)

                    for analysis_type, analysis_info in cell_culture_state.ANALYSIS_TREE.items():
                        analysis_item = StreamlitTreeMenuItem(
                            label=translate_service.translate(analysis_info['title']),
                            key=f'analysis_{analysis_type}_qc_{qc_scenario.id}',
                            material_icon=analysis_info['icon']
                        )

                        # For Medium PCA, add existing scenarios as sub-folders
                        if analysis_type == 'medium_pca':
                            pca_scenarios = recipe.get_medium_pca_scenarios_for_quality_check(qc_scenario.id)
                            if pca_scenarios:
                                for pca_scenario in pca_scenarios:
                                    pca_timestamp = pca_scenario.title
                                    if "Medium PCA - " in pca_scenario.title:
                                        pca_timestamp = pca_scenario.title.replace("Medium PCA - ", "")

                                    # Create sub-item for this PCA scenario
                                    pca_result_item = StreamlitTreeMenuItem(
                                        label=pca_timestamp,
                                        key=f'pca_result_{pca_scenario.id}',
                                        material_icon='assessment'
                                    )
                                    analysis_item.add_child(pca_result_item)

                        # For Medium UMAP, add existing scenarios as sub-folders
                        if analysis_type == 'medium_umap':
                            umap_scenarios = recipe.get_medium_umap_scenarios_for_quality_check(qc_scenario.id)
                            if umap_scenarios:
                                for umap_scenario in umap_scenarios:
                                    umap_timestamp = umap_scenario.title
                                    if "Medium UMAP - " in umap_scenario.title:
                                        umap_timestamp = umap_scenario.title.replace("Medium UMAP - ", "")

                                    # Create sub-item for this UMAP scenario
                                    umap_result_item = StreamlitTreeMenuItem(
                                        label=umap_timestamp,
                                        key=f'umap_result_{umap_scenario.id}',
                                        material_icon='bubble_chart'
                                    )
                                    analysis_item.add_child(umap_result_item)

                        # For Feature Extraction, add existing scenarios as sub-folders
                        if analysis_type == 'feature_extraction':
                            fe_scenarios = recipe.get_feature_extraction_scenarios_for_quality_check(qc_scenario.id)
                            if fe_scenarios:
                                for fe_scenario in fe_scenarios:
                                    fe_timestamp = fe_scenario.title
                                    if "Feature Extraction - " in fe_scenario.title:
                                        fe_timestamp = fe_scenario.title.replace("Feature Extraction - ", "")

                                    # Create sub-item for this FE scenario
                                    fe_result_item = StreamlitTreeMenuItem(
                                        label=fe_timestamp,
                                        key=f'fe_result_{fe_scenario.id}',
                                        material_icon='auto_graph'
                                    )
                                    analysis_item.add_child(fe_result_item)

                        # For Logistic Growth, add existing scenarios as sub-folders
                        if analysis_type == 'logistic_growth':
                            lg_scenarios = recipe.get_logistic_growth_scenarios_for_quality_check(qc_scenario.id)
                            if lg_scenarios:
                                for lg_scenario in lg_scenarios:
                                    lg_timestamp = lg_scenario.title
                                    if "Logistic Growth Fitting - " in lg_scenario.title:
                                        lg_timestamp = lg_scenario.title.replace("Logistic Growth Fitting - ", "")

                                    # Create sub-item for this LG scenario
                                    lg_result_item = StreamlitTreeMenuItem(
                                        label=lg_timestamp,
                                        key=f'lg_result_{lg_scenario.id}',
                                        material_icon='show_chart'
                                    )
                                    analysis_item.add_child(lg_result_item)

                        # For Spline Growth, add existing scenarios as sub-folders
                        if analysis_type == 'spline_growth':
                            sg_scenarios = recipe.get_spline_growth_scenarios_for_quality_check(qc_scenario.id)
                            if sg_scenarios:
                                for sg_scenario in sg_scenarios:
                                    sg_timestamp = sg_scenario.title
                                    if "Spline Growth Rate - " in sg_scenario.title:
                                        sg_timestamp = sg_scenario.title.replace("Spline Growth Rate - ", "")

                                    # Create sub-item for this SG scenario
                                    sg_result_item = StreamlitTreeMenuItem(
                                        label=sg_timestamp,
                                        key=f'sg_result_{sg_scenario.id}',
                                        material_icon='insights'
                                    )
                                    analysis_item.add_child(sg_result_item)

                        analysis_folder.add_child(analysis_item)

                    quality_check_folder.add_child(qc_folder)

            selection_folder.add_child(quality_check_folder)

            button_menu.add_item(selection_folder)

    return button_menu, 'apercu'


def render_recipe_page(cell_culture_state: CellCultureState) -> None:
    """Render the analysis page with tree navigation structure"""

    translate_service = cell_culture_state.get_translate_service()

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
        recipe = cell_culture_state.get_selected_recipe_instance()
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
            button_menu, key_default_item = build_analysis_tree_menu(cell_culture_state)

            # Display menu and get selected item
            selected_item = button_menu.render()
            selected_key = selected_item.key if selected_item else key_default_item

        with right_col:
            # Render the selected step
            if selected_key == 'apercu':
                st.title(f"{recipe.name} - Overview")
                render_overview_step(recipe, cell_culture_state)
            elif selected_key == 'selection':
                st.title(f"{recipe.name} - Sélection")
                render_selection_step(recipe, cell_culture_state)
            elif selected_key.startswith('quality_check_'):
                # Extract selection scenario ID from key (quality_check_{selection_id})
                selection_id = selected_key.replace('quality_check_', '')
                # Find the corresponding selection scenario
                selection_scenarios = recipe.get_selection_scenarios()
                target_selection_scenario = next((s for s in selection_scenarios if s.id == selection_id), None)
                if target_selection_scenario:
                    st.title(f"{recipe.name} - Quality Check")
                    render_quality_check_step(recipe, cell_culture_state, selection_scenario=target_selection_scenario)
                else:
                    st.error(translate_service.translate('selection_scenario_not_found'))
            elif selected_key.startswith('tableau_'):
                # Extract scenario ID from key
                scenario_id = selected_key.replace('tableau_', '')
                # Find the corresponding scenario
                selection_scenarios = recipe.get_selection_scenarios()
                target_scenario = next((s for s in selection_scenarios if s.id == scenario_id), None)
                if target_scenario:
                    st.title(f"{recipe.name} - Tableau")
                    render_table_view_step(
                        recipe,
                        cell_culture_state,
                        scenario=target_scenario,
                        output_name=cell_culture_state.INTERPOLATION_SCENARIO_OUTPUT_NAME
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
                    st.title(f"{recipe.name} - Tableau (QC)")
                    # Display quality check results in table view (use interpolated output)
                    render_table_view_step(
                        recipe,
                        cell_culture_state,
                        scenario=target_qc_scenario,
                        output_name=cell_culture_state.QUALITY_CHECK_SCENARIO_INTERPOLATED_OUTPUT_NAME
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
                    st.title(f"{recipe.name} - Graphiques (QC)")
                    # Display quality check results in graph view (use interpolated output)
                    render_graph_view_step(
                        recipe,
                        cell_culture_state,
                        scenario=target_qc_scenario,
                        output_name=cell_culture_state.QUALITY_CHECK_SCENARIO_INTERPOLATED_OUTPUT_NAME
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
                    st.title(f"{recipe.name} - Graphiques")
                    render_graph_view_step(
                        recipe,
                        cell_culture_state,
                        scenario=target_scenario,
                        output_name=cell_culture_state.INTERPOLATION_SCENARIO_OUTPUT_NAME
                    )
                else:
                    st.error(translate_service.translate('selection_scenario_not_found'))
            elif selected_key.startswith('medium_'):
                # Extract scenario ID from key
                scenario_id = selected_key.replace('medium_', '')
                # Find the corresponding scenario
                selection_scenarios = recipe.get_selection_scenarios()
                target_scenario = next((s for s in selection_scenarios if s.id == scenario_id), None)
                if target_scenario:
                    st.title(f"{recipe.name} - Medium")
                    render_medium_view_step(
                        recipe,
                        cell_culture_state,
                        scenario=target_scenario,
                        output_name=cell_culture_state.INTERPOLATION_SCENARIO_OUTPUT_NAME
                    )
                else:
                    st.error(translate_service.translate('selection_scenario_not_found'))
            elif selected_key.startswith('qc_medium_'):
                # Extract quality check scenario ID from key
                qc_scenario_id = selected_key.replace('qc_medium_', '')
                # Find the corresponding quality check scenario
                all_qc_scenarios = recipe.get_quality_check_scenarios()
                target_qc_scenario = next((s for s in all_qc_scenarios if s.id == qc_scenario_id), None)
                if target_qc_scenario:
                    st.title(f"{recipe.name} - Medium (QC)")
                    # Display quality check results in medium view
                    render_medium_view_step(
                        recipe,
                        cell_culture_state,
                        scenario=target_qc_scenario,
                        output_name=cell_culture_state.QUALITY_CHECK_SCENARIO_OUTPUT_NAME
                    )
                else:
                    st.error("Quality Check scenario not found")
            elif selected_key.startswith('analysis_medium_pca_qc_'):
                # Extract quality check scenario ID from key (analysis_medium_pca_qc_{qc_id})
                qc_scenario_id = selected_key.replace('analysis_medium_pca_qc_', '')
                # Find the corresponding quality check scenario
                all_qc_scenarios = recipe.get_quality_check_scenarios()
                target_qc_scenario = next((s for s in all_qc_scenarios if s.id == qc_scenario_id), None)
                if target_qc_scenario:
                    st.title(f"{recipe.name} - Medium PCA Analysis")
                    render_medium_pca_step(recipe, cell_culture_state, quality_check_scenario=target_qc_scenario)
                else:
                    st.error("Quality Check scenario not found")
            elif selected_key.startswith('analysis_medium_umap_qc_'):
                # Extract quality check scenario ID from key (analysis_medium_umap_qc_{qc_id})
                qc_scenario_id = selected_key.replace('analysis_medium_umap_qc_', '')
                # Find the corresponding quality check scenario
                all_qc_scenarios = recipe.get_quality_check_scenarios()
                target_qc_scenario = next((s for s in all_qc_scenarios if s.id == qc_scenario_id), None)
                if target_qc_scenario:
                    st.title(f"{recipe.name} - Medium UMAP Analysis")
                    render_medium_umap_step(recipe, cell_culture_state, quality_check_scenario=target_qc_scenario)
                else:
                    st.error("Quality Check scenario not found")
            elif selected_key.startswith('analysis_feature_extraction_qc_'):
                # Extract quality check scenario ID from key (analysis_feature_extraction_qc_{qc_id})
                qc_scenario_id = selected_key.replace('analysis_feature_extraction_qc_', '')
                # Find the corresponding quality check scenario
                all_qc_scenarios = recipe.get_quality_check_scenarios()
                target_qc_scenario = next((s for s in all_qc_scenarios if s.id == qc_scenario_id), None)
                if target_qc_scenario:
                    st.title(f"{recipe.name} - Feature Extraction Analysis")
                    render_feature_extraction_step(recipe, cell_culture_state,
                                                   quality_check_scenario=target_qc_scenario)
                else:
                    st.error("Quality Check scenario not found")
            elif selected_key.startswith('analysis_logistic_growth_qc_'):
                # Extract quality check scenario ID from key (analysis_logistic_growth_qc_{qc_id})
                qc_scenario_id = selected_key.replace('analysis_logistic_growth_qc_', '')
                # Find the corresponding quality check scenario
                all_qc_scenarios = recipe.get_quality_check_scenarios()
                target_qc_scenario = next((s for s in all_qc_scenarios if s.id == qc_scenario_id), None)
                if target_qc_scenario:
                    st.title(f"{recipe.name} - Logistic Growth Analysis")
                    render_logistic_growth_step(recipe, cell_culture_state, quality_check_scenario=target_qc_scenario)
                else:
                    st.error("Quality Check scenario not found")
            elif selected_key.startswith('analysis_spline_growth_qc_'):
                # Extract quality check scenario ID from key (analysis_spline_growth_qc_{qc_id})
                qc_scenario_id = selected_key.replace('analysis_spline_growth_qc_', '')
                # Find the corresponding quality check scenario
                all_qc_scenarios = recipe.get_quality_check_scenarios()
                target_qc_scenario = next((s for s in all_qc_scenarios if s.id == qc_scenario_id), None)
                if target_qc_scenario:
                    st.title(f"{recipe.name} - Spline Growth Analysis")
                    render_spline_growth_step(recipe, cell_culture_state, quality_check_scenario=target_qc_scenario)
                else:
                    st.error("Quality Check scenario not found")
            elif selected_key.startswith('pca_result_'):
                # Extract PCA scenario ID from key (pca_result_{pca_scenario_id})
                pca_scenario_id = selected_key.replace('pca_result_', '')
                # Find the corresponding PCA scenario in 'analyses' step
                all_analyses_scenarios = recipe.get_scenarios_for_step('analyses')
                target_pca_scenario = next((s for s in all_analyses_scenarios if s.id == pca_scenario_id), None)
                if target_pca_scenario:
                    # Use the render function from medium_pca_results.py
                    render_medium_pca_results(recipe, cell_culture_state, target_pca_scenario)
                else:
                    st.error("PCA scenario not found")
            elif selected_key.startswith('umap_result_'):
                # Extract UMAP scenario ID from key (umap_result_{umap_scenario_id})
                umap_scenario_id = selected_key.replace('umap_result_', '')
                # Find the corresponding UMAP scenario in 'analyses' step
                all_analyses_scenarios = recipe.get_scenarios_for_step('analyses')
                target_umap_scenario = next((s for s in all_analyses_scenarios if s.id == umap_scenario_id), None)
                if target_umap_scenario:
                    # Use the render function from medium_umap_results.py
                    render_medium_umap_results(recipe, cell_culture_state, target_umap_scenario)
                else:
                    st.error("UMAP scenario not found")
            elif selected_key.startswith('fe_result_'):
                # Extract Feature Extraction scenario ID from key (fe_result_{fe_scenario_id})
                fe_scenario_id = selected_key.replace('fe_result_', '')
                # Find the corresponding FE scenario in 'analyses' step
                all_analyses_scenarios = recipe.get_scenarios_for_step('analyses')
                target_fe_scenario = next((s for s in all_analyses_scenarios if s.id == fe_scenario_id), None)
                if target_fe_scenario:
                    # Use the render function from feature_extraction_results.py
                    render_feature_extraction_results(recipe, cell_culture_state, target_fe_scenario)
                else:
                    st.error("Feature Extraction scenario not found")
            elif selected_key.startswith('lg_result_'):
                # Extract Logistic Growth scenario ID from key (lg_result_{lg_scenario_id})
                lg_scenario_id = selected_key.replace('lg_result_', '')
                # Find the corresponding LG scenario in 'analyses' step
                all_analyses_scenarios = recipe.get_scenarios_for_step('analyses')
                target_lg_scenario = next((s for s in all_analyses_scenarios if s.id == lg_scenario_id), None)
                if target_lg_scenario:
                    # Use the render function from logistic_growth_analysis_results.py
                    render_logistic_growth_results(recipe, cell_culture_state, target_lg_scenario)
                else:
                    st.error("Logistic Growth scenario not found")
            elif selected_key.startswith('sg_result_'):
                # Extract Spline Growth scenario ID from key (sg_result_{sg_scenario_id})
                sg_scenario_id = selected_key.replace('sg_result_', '')
                # Find the corresponding SG scenario in 'analyses' step
                all_analyses_scenarios = recipe.get_scenarios_for_step('analyses')
                target_sg_scenario = next((s for s in all_analyses_scenarios if s.id == sg_scenario_id), None)
                if target_sg_scenario:
                    # Use the render function from spline_growth_analysis_results.py
                    render_spline_growth_results(recipe, cell_culture_state, target_sg_scenario)
                else:
                    st.error("Spline Growth scenario not found")
                    st.error("Feature Extraction scenario not found")
            else:
                st.info(translate_service.translate('select_step_in_menu'))
