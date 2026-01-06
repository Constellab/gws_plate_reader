"""
Main Analysis Page for Cell Culture Dashboards
Coordinates the different analysis steps and sub-pages
"""

from typing import Dict, List, Optional, Tuple

import streamlit as st
from gws_core import Scenario, ScenarioStatus
from gws_core.streamlit import (
    StreamlitContainers,
    StreamlitRouter,
    StreamlitTreeMenu,
    StreamlitTreeMenuItem,
)
from gws_core.tag.entity_tag_list import EntityTagList
from gws_core.tag.tag_entity_type import TagEntityType

from gws_plate_reader.cell_culture_app_core.cell_culture_state import CellCultureState
from gws_plate_reader.cell_culture_app_core.functions_steps import (
    get_status_emoji,
    get_status_material_icon,
)

from .recipe_steps import (
    render_causal_effect_results,
    render_causal_effect_step,
    render_feature_extraction_results,
    render_feature_extraction_step,
    render_graph_view_step,
    render_medium_pca_results,
    render_medium_pca_step,
    render_medium_umap_results,
    render_medium_umap_step,
    render_medium_view_step,
    render_metadata_feature_umap_results,
    render_metadata_feature_umap_step,
    render_optimization_results,
    render_optimization_step,
    render_overview_step,
    render_pls_regression_results,
    render_pls_regression_step,
    render_quality_check_step,
    render_random_forest_results,
    render_random_forest_step,
    render_selection_step,
    render_table_view_step,
)


# Helper functions similar to ubiome
def has_successful_scenario(step_name: str, scenarios_by_step: Dict[str, List[Scenario]]) -> bool:
    """Check if steps are completed (have successful scenarios)"""
    if step_name not in scenarios_by_step:
        return False
    return any(s.status == ScenarioStatus.SUCCESS for s in scenarios_by_step[step_name])


def get_step_icon(
    step_name: str,
    scenarios_by_step: Dict[str, List[Scenario]],
    list_scenarios: Optional[List[Scenario]] = None,
) -> str:
    """Get icon for step - check_circle if step has scenarios, empty otherwise."""
    if step_name not in scenarios_by_step:
        return ""
    if not list_scenarios:
        return ""
    return "check_circle"


def build_analysis_tree_menu(cell_culture_state: CellCultureState) -> Tuple[StreamlitTreeMenu, str]:
    """Build tree menu for analysis navigation"""

    translate_service = cell_culture_state.get_translate_service()

    # Create tree menu
    button_menu = StreamlitTreeMenu()

    # Get Recipe instance to check if selection has been done
    recipe = cell_culture_state.get_selected_recipe_instance()

    # Overview section (always visible if there's a load scenario)
    overview_item = StreamlitTreeMenuItem(
        label=translate_service.translate("overview"), key="apercu", material_icon="description"
    )
    button_menu.add_item(overview_item)

    # Selection section (always visible to allow creating new selections)
    selection_item = StreamlitTreeMenuItem(
        label=translate_service.translate("selection"), key="selection", material_icon="check_box"
    )
    button_menu.add_item(selection_item)

    # Selection folders (one folder per selection with sub-items for Table, Graph, and Quality Check views)
    if recipe and recipe.has_selection_scenarios():
        selection_scenarios = recipe.get_selection_scenarios_organized()

        for selection_name, scenario in selection_scenarios.items():
            # Add status icon to selection scenario label
            status_emoji = get_status_emoji(scenario.status)
            selection_label = f"{status_emoji} {selection_name}"

            # Create folder for this selection
            selection_folder = StreamlitTreeMenuItem(
                label=selection_label,
                key=f"selection_folder_{scenario.id}",
                material_icon=get_status_material_icon(scenario.status),
            )

            # Add table view sub-item
            table_sub_item = StreamlitTreeMenuItem(
                label=translate_service.translate("table"),
                key=f"tableau_{scenario.id}",
                material_icon="table_chart",
            )
            selection_folder.add_child(table_sub_item)

            # Add graph view sub-item
            graph_sub_item = StreamlitTreeMenuItem(
                label=translate_service.translate("graphs"),
                key=f"graphiques_{scenario.id}",
                material_icon="analytics",
            )
            selection_folder.add_child(graph_sub_item)

            # Add medium view sub-item
            medium_sub_item = StreamlitTreeMenuItem(
                label=translate_service.translate("medium"),
                key=f"medium_{scenario.id}",
                material_icon="science",
            )
            selection_folder.add_child(medium_sub_item)

            # Add Quality Check folder - clicking on it opens the QC creation form
            quality_check_folder = StreamlitTreeMenuItem(
                label="Quality Check", key=f"quality_check_{scenario.id}", material_icon="folder"
            )

            # Add quality check scenario sub-folders with their own Table/Graph views
            quality_check_scenarios = recipe.get_quality_check_scenarios_for_selection(scenario.id)
            if quality_check_scenarios:
                for qc_scenario in quality_check_scenarios:
                    qc_timestamp = "QC"
                    if "Quality Check - " in qc_scenario.title:
                        qc_timestamp = qc_scenario.title.replace("Quality Check - ", "")

                    # Add status icon to QC scenario label
                    status_emoji = get_status_emoji(qc_scenario.status)
                    qc_label = f"{status_emoji} {qc_timestamp}"

                    # Create folder for this QC scenario
                    qc_folder = StreamlitTreeMenuItem(
                        label=qc_label,
                        key=f"qc_folder_{qc_scenario.id}",
                        material_icon=get_status_material_icon(qc_scenario.status),
                    )

                    # Add Table view for QC results
                    qc_table_item = StreamlitTreeMenuItem(
                        label=translate_service.translate("table"),
                        key=f"qc_table_{qc_scenario.id}",
                        material_icon="table_chart",
                    )
                    qc_folder.add_child(qc_table_item)

                    # Add Graph view for QC results
                    qc_graph_item = StreamlitTreeMenuItem(
                        label=translate_service.translate("graphs"),
                        key=f"qc_graph_{qc_scenario.id}",
                        material_icon="analytics",
                    )
                    qc_folder.add_child(qc_graph_item)

                    # Add Medium view for QC results
                    qc_medium_item = StreamlitTreeMenuItem(
                        label=translate_service.translate("medium"),
                        key=f"qc_medium_{qc_scenario.id}",
                        material_icon="science",
                    )
                    qc_folder.add_child(qc_medium_item)

                    # Analysis sub-folder
                    analysis_folder = StreamlitTreeMenuItem(
                        label=translate_service.translate("analysis"),
                        key=f"analysis_qc_{qc_scenario.id}",
                        material_icon="folder",
                    )
                    qc_folder.add_child(analysis_folder)

                    for analysis_type, analysis_info in cell_culture_state.ANALYSIS_TREE.items():
                        # Skip feature extraction if recipe doesn't have raw data
                        if analysis_type == "feature_extraction" and not recipe.has_data_raw:
                            continue

                        analysis_item = StreamlitTreeMenuItem(
                            label=translate_service.translate(analysis_info["title"]),
                            key=f"analysis_{analysis_type}_qc_{qc_scenario.id}",
                            material_icon=analysis_info["icon"],
                        )

                        # For Medium PCA, add existing scenarios as sub-folders
                        if analysis_type == "medium_pca":
                            pca_scenarios = recipe.get_medium_pca_scenarios_for_quality_check(
                                qc_scenario.id
                            )
                            if pca_scenarios:
                                for pca_scenario in pca_scenarios:
                                    pca_timestamp = pca_scenario.title
                                    if "Medium PCA - " in pca_scenario.title:
                                        pca_timestamp = pca_scenario.title.replace(
                                            "Medium PCA - ", ""
                                        )

                                    # Add status icon to PCA scenario label
                                    status_emoji = get_status_emoji(pca_scenario.status)
                                    pca_label = f"{status_emoji} {pca_timestamp}"

                                    # Create sub-item for this PCA scenario
                                    pca_result_item = StreamlitTreeMenuItem(
                                        label=pca_label,
                                        key=f"pca_result_{pca_scenario.id}",
                                        material_icon=get_status_material_icon(pca_scenario.status),
                                    )

                                    analysis_item.add_child(pca_result_item)

                        # For Medium UMAP, add existing scenarios as sub-folders
                        if analysis_type == "medium_umap":
                            umap_scenarios = recipe.get_medium_umap_scenarios_for_quality_check(
                                qc_scenario.id
                            )
                            if umap_scenarios:
                                for umap_scenario in umap_scenarios:
                                    umap_timestamp = umap_scenario.title
                                    if "Medium UMAP - " in umap_scenario.title:
                                        umap_timestamp = umap_scenario.title.replace(
                                            "Medium UMAP - ", ""
                                        )

                                    # Add status icon to UMAP scenario label
                                    status_emoji = get_status_emoji(umap_scenario.status)
                                    umap_label = f"{status_emoji} {umap_timestamp}"

                                    # Create sub-item for this UMAP scenario
                                    umap_result_item = StreamlitTreeMenuItem(
                                        label=umap_label,
                                        key=f"umap_result_{umap_scenario.id}",
                                        material_icon=get_status_material_icon(
                                            umap_scenario.status
                                        ),
                                    )
                                    analysis_item.add_child(umap_result_item)

                        # For Feature Extraction, add existing scenarios as sub-folders
                        if analysis_type == "feature_extraction":
                            fe_scenarios = (
                                recipe.get_feature_extraction_scenarios_for_quality_check(
                                    qc_scenario.id
                                )
                            )
                            if fe_scenarios:
                                for fe_scenario in fe_scenarios:
                                    fe_timestamp = fe_scenario.title
                                    if "Feature Extraction - " in fe_scenario.title:
                                        fe_timestamp = fe_scenario.title.replace(
                                            "Feature Extraction - ", ""
                                        )

                                    # Add status icon to FE scenario label
                                    status_emoji = get_status_emoji(fe_scenario.status)
                                    fe_label = f"{status_emoji} {fe_timestamp}"

                                    # Create sub-item for this FE scenario
                                    fe_result_item = StreamlitTreeMenuItem(
                                        label=fe_label,
                                        key=f"fe_result_{fe_scenario.id}",
                                        material_icon=get_status_material_icon(fe_scenario.status),
                                    )

                                    for (
                                        post_feature_extraction_analysis_type,
                                        post_feature_extraction_analysis_info,
                                    ) in cell_culture_state.POST_FEATURE_EXTRACTION_ANALYSIS_TREE.items():
                                        if (
                                            post_feature_extraction_analysis_type
                                            == "metadata_feature_umap"
                                        ):
                                            # Create sub-item for launching new metadata feature UMAP analysis
                                            fe_umap_launch_item = StreamlitTreeMenuItem(
                                                label=translate_service.translate(
                                                    post_feature_extraction_analysis_info["title"]
                                                ),
                                                key=f"analysis_{post_feature_extraction_analysis_type}_fe_{fe_scenario.id}",
                                                material_icon=post_feature_extraction_analysis_info[
                                                    "icon"
                                                ],
                                            )
                                            fe_result_item.add_child(fe_umap_launch_item)

                                            # Add existing metadata feature UMAP scenarios as sub-items
                                            metadata_umap_scenarios = recipe.get_metadata_feature_umap_scenarios_for_feature_extraction(
                                                fe_scenario.id
                                            )
                                            if metadata_umap_scenarios:
                                                for (
                                                    metadata_umap_scenario
                                                ) in metadata_umap_scenarios:
                                                    metadata_umap_timestamp = (
                                                        metadata_umap_scenario.title
                                                    )
                                                    if (
                                                        "Metadata Feature UMAP - "
                                                        in metadata_umap_scenario.title
                                                    ):
                                                        metadata_umap_timestamp = (
                                                            metadata_umap_scenario.title.replace(
                                                                "Metadata Feature UMAP - ", ""
                                                            )
                                                        )

                                                    # Add status icon to metadata UMAP scenario label
                                                    status_emoji = get_status_emoji(
                                                        metadata_umap_scenario.status
                                                    )
                                                    metadata_umap_label = (
                                                        f"{status_emoji} {metadata_umap_timestamp}"
                                                    )

                                                    # Create sub-sub-item for this metadata feature UMAP result
                                                    metadata_umap_result_item = StreamlitTreeMenuItem(
                                                        label=metadata_umap_label,
                                                        key=f"metadata_feature_umap_result_{metadata_umap_scenario.id}",
                                                        material_icon=get_status_material_icon(
                                                            metadata_umap_scenario.status
                                                        ),
                                                    )
                                                    fe_umap_launch_item.add_child(
                                                        metadata_umap_result_item
                                                    )

                                        elif (
                                            post_feature_extraction_analysis_type
                                            == "pls_regression"
                                        ):
                                            # Create sub-item for launching new PLS regression analysis
                                            fe_pls_launch_item = StreamlitTreeMenuItem(
                                                label=translate_service.translate(
                                                    post_feature_extraction_analysis_info["title"]
                                                ),
                                                key=f"analysis_{post_feature_extraction_analysis_type}_fe_{fe_scenario.id}",
                                                material_icon=post_feature_extraction_analysis_info[
                                                    "icon"
                                                ],
                                            )
                                            fe_result_item.add_child(fe_pls_launch_item)

                                            # Add existing PLS regression scenarios as sub-items
                                            pls_scenarios = recipe.get_pls_regression_scenarios_for_feature_extraction(
                                                fe_scenario.id
                                            )
                                            if pls_scenarios:
                                                for pls_scenario in pls_scenarios:
                                                    pls_timestamp = pls_scenario.title
                                                    if "PLS Regression - " in pls_scenario.title:
                                                        pls_timestamp = pls_scenario.title.replace(
                                                            "PLS Regression - ", ""
                                                        )

                                                    # Add status icon to PLS scenario label
                                                    status_emoji = get_status_emoji(
                                                        pls_scenario.status
                                                    )
                                                    pls_label = f"{status_emoji} {pls_timestamp}"

                                                    # Create sub-sub-item for this PLS regression result
                                                    pls_result_item = StreamlitTreeMenuItem(
                                                        label=pls_label,
                                                        key=f"pls_regression_result_{pls_scenario.id}",
                                                        material_icon=get_status_material_icon(
                                                            pls_scenario.status
                                                        ),
                                                    )
                                                    fe_pls_launch_item.add_child(pls_result_item)

                                        elif (
                                            post_feature_extraction_analysis_type
                                            == "random_forest_regression"
                                        ):
                                            # Create sub-item for launching new Random Forest regression analysis
                                            fe_rf_launch_item = StreamlitTreeMenuItem(
                                                label=translate_service.translate(
                                                    post_feature_extraction_analysis_info["title"]
                                                ),
                                                key=f"analysis_{post_feature_extraction_analysis_type}_fe_{fe_scenario.id}",
                                                material_icon=post_feature_extraction_analysis_info[
                                                    "icon"
                                                ],
                                            )
                                            fe_result_item.add_child(fe_rf_launch_item)

                                            # Add existing Random Forest regression scenarios as sub-items
                                            rf_scenarios = recipe.get_random_forest_scenarios_for_feature_extraction(
                                                fe_scenario.id
                                            )
                                            if rf_scenarios:
                                                for rf_scenario in rf_scenarios:
                                                    rf_timestamp = rf_scenario.title
                                                    if (
                                                        "Random Forest Regression - "
                                                        in rf_scenario.title
                                                    ):
                                                        rf_timestamp = rf_scenario.title.replace(
                                                            "Random Forest Regression - ", ""
                                                        )

                                                    # Add status icon to RF scenario label
                                                    status_emoji = get_status_emoji(
                                                        rf_scenario.status
                                                    )
                                                    rf_label = f"{status_emoji} {rf_timestamp}"

                                                    # Create sub-sub-item for this Random Forest regression result
                                                    rf_result_item = StreamlitTreeMenuItem(
                                                        label=rf_label,
                                                        key=f"random_forest_result_{rf_scenario.id}",
                                                        material_icon=get_status_material_icon(
                                                            rf_scenario.status
                                                        ),
                                                    )
                                                    fe_rf_launch_item.add_child(rf_result_item)

                                        elif (
                                            post_feature_extraction_analysis_type == "causal_effect"
                                        ):
                                            # Create sub-item for launching new Causal Effect analysis
                                            fe_causal_launch_item = StreamlitTreeMenuItem(
                                                label=translate_service.translate(
                                                    post_feature_extraction_analysis_info["title"]
                                                ),
                                                key=f"analysis_{post_feature_extraction_analysis_type}_fe_{fe_scenario.id}",
                                                material_icon=post_feature_extraction_analysis_info[
                                                    "icon"
                                                ],
                                            )
                                            fe_result_item.add_child(fe_causal_launch_item)

                                            # Add existing Causal Effect scenarios as sub-items
                                            causal_scenarios = recipe.get_causal_effect_scenarios_for_feature_extraction(
                                                fe_scenario.id
                                            )
                                            if causal_scenarios:
                                                for causal_scenario in causal_scenarios:
                                                    causal_timestamp = causal_scenario.title
                                                    if "Causal Effect - " in causal_scenario.title:
                                                        causal_timestamp = (
                                                            causal_scenario.title.replace(
                                                                "Causal Effect - ", ""
                                                            )
                                                        )

                                                    # Add status icon to Causal Effect scenario label
                                                    status_emoji = get_status_emoji(
                                                        causal_scenario.status
                                                    )
                                                    causal_label = (
                                                        f"{status_emoji} {causal_timestamp}"
                                                    )

                                                    # Create sub-sub-item for this Causal Effect result
                                                    causal_result_item = StreamlitTreeMenuItem(
                                                        label=causal_label,
                                                        key=f"causal_effect_result_{causal_scenario.id}",
                                                        material_icon=get_status_material_icon(
                                                            causal_scenario.status
                                                        ),
                                                    )
                                                    fe_causal_launch_item.add_child(
                                                        causal_result_item
                                                    )

                                        elif (
                                            post_feature_extraction_analysis_type == "optimization"
                                        ):
                                            # Create sub-item for launching new Optimization analysis
                                            fe_opt_launch_item = StreamlitTreeMenuItem(
                                                label=translate_service.translate(
                                                    post_feature_extraction_analysis_info["title"]
                                                ),
                                                key=f"analysis_{post_feature_extraction_analysis_type}_fe_{fe_scenario.id}",
                                                material_icon=post_feature_extraction_analysis_info[
                                                    "icon"
                                                ],
                                            )
                                            fe_result_item.add_child(fe_opt_launch_item)

                                            # Add existing Optimization scenarios as sub-items
                                            opt_scenarios = recipe.get_optimization_scenarios_for_feature_extraction(
                                                fe_scenario.id
                                            )
                                            if opt_scenarios:
                                                for opt_scenario in opt_scenarios:
                                                    opt_timestamp = opt_scenario.title
                                                    if "Optimization - " in opt_scenario.title:
                                                        opt_timestamp = opt_scenario.title.replace(
                                                            "Optimization - ", ""
                                                        )

                                                    # Add status icon to Optimization scenario label
                                                    status_emoji = get_status_emoji(
                                                        opt_scenario.status
                                                    )
                                                    opt_label = f"{status_emoji} {opt_timestamp}"

                                                    # Create sub-sub-item for this Optimization result
                                                    opt_result_item = StreamlitTreeMenuItem(
                                                        label=opt_label,
                                                        key=f"optimization_result_{opt_scenario.id}",
                                                        material_icon=get_status_material_icon(
                                                            opt_scenario.status
                                                        ),
                                                    )
                                                    fe_opt_launch_item.add_child(opt_result_item)

                                    analysis_item.add_child(fe_result_item)

                        analysis_folder.add_child(analysis_item)

                    quality_check_folder.add_child(qc_folder)

            selection_folder.add_child(quality_check_folder)

            button_menu.add_item(selection_folder)

    return button_menu, "apercu"


def render_recipe_page(cell_culture_state: CellCultureState) -> None:
    """Render the analysis page with tree navigation structure"""

    translate_service = cell_culture_state.get_translate_service()

    style = """
    [CLASS_NAME] {
        padding: 40px;
    }
    """

    with StreamlitContainers.container_full_min_height(
        "container-center_analysis_page", additional_style=style
    ):  # Create two columns like ubiome
        left_col, right_col = st.columns([1, 4])

        # Get Recipe instance from state (created in first_page)
        recipe = cell_culture_state.get_selected_recipe_instance()
        if not recipe:
            st.error(translate_service.translate("no_recipe_selected"))
            return

        with left_col:
            # Add return button at the top
            router = StreamlitRouter.load_from_session()

            if st.button(
                translate_service.translate("recipes_list"),
                icon=":material/arrow_back:",
                width="stretch",
            ):
                router.navigate("first-page")
                st.rerun()

            # Add refresh button
            if not cell_culture_state.get_is_standalone():
                if st.button(
                    translate_service.translate("refresh"),
                    icon=":material/refresh:",
                    width="stretch",
                ):
                    # Reload all scenarios from database to get updated status
                    recipe.reload_scenarios()
                    st.rerun()

            st.markdown("---")  # Separator line

            # Build and display navigation menu
            button_menu, key_default_item = build_analysis_tree_menu(cell_culture_state)

            # Display menu and get selected item
            selected_item = button_menu.render()
            selected_key = selected_item.key if selected_item else key_default_item

        with right_col:
            # Render the selected step
            if selected_key == "apercu":
                st.title(f"{recipe.name} - Overview")
                render_overview_step(recipe, cell_culture_state)
            elif selected_key == "selection":
                st.title(f"{recipe.name} - Sélection")
                render_selection_step(recipe, cell_culture_state)
            elif selected_key.startswith("quality_check_"):
                # Extract selection scenario ID from key (quality_check_{selection_id})
                selection_id = selected_key.replace("quality_check_", "")
                # Find the corresponding selection scenario
                selection_scenarios = recipe.get_selection_scenarios()
                target_selection_scenario = next(
                    (s for s in selection_scenarios if s.id == selection_id), None
                )
                if target_selection_scenario:
                    st.title(f"{recipe.name} - Quality Check")
                    render_quality_check_step(
                        recipe, cell_culture_state, selection_scenario=target_selection_scenario
                    )
                else:
                    st.error(translate_service.translate("selection_scenario_not_found"))
            elif selected_key.startswith("tableau_"):
                # Extract scenario ID from key
                scenario_id = selected_key.replace("tableau_", "")
                # Find the corresponding scenario
                selection_scenarios = recipe.get_selection_scenarios()
                target_scenario = next(
                    (s for s in selection_scenarios if s.id == scenario_id), None
                )
                if target_scenario:
                    st.title(f"{recipe.name} - {translate_service.translate('page_title_table')}")
                    render_table_view_step(
                        recipe,
                        cell_culture_state,
                        scenario=target_scenario,
                        output_name=cell_culture_state.INTERPOLATION_SCENARIO_OUTPUT_NAME,
                    )
                else:
                    st.error(translate_service.translate("selection_scenario_not_found"))
            elif selected_key.startswith("qc_table_"):
                # Extract quality check scenario ID from key
                qc_scenario_id = selected_key.replace("qc_table_", "")
                # Find the corresponding quality check scenario
                all_qc_scenarios = recipe.get_quality_check_scenarios()
                target_qc_scenario = next(
                    (s for s in all_qc_scenarios if s.id == qc_scenario_id), None
                )
                if target_qc_scenario:
                    st.title(
                        f"{recipe.name} - {translate_service.translate('page_title_table')} (QC)"
                    )
                    # Display quality check results in table view (use interpolated output)
                    render_table_view_step(
                        recipe,
                        cell_culture_state,
                        scenario=target_qc_scenario,
                        output_name=cell_culture_state.QUALITY_CHECK_SCENARIO_INTERPOLATED_OUTPUT_NAME,
                    )
                else:
                    st.error("Quality Check scenario not found")
            elif selected_key.startswith("qc_graph_"):
                # Extract quality check scenario ID from key
                qc_scenario_id = selected_key.replace("qc_graph_", "")
                # Find the corresponding quality check scenario
                all_qc_scenarios = recipe.get_quality_check_scenarios()
                target_qc_scenario = next(
                    (s for s in all_qc_scenarios if s.id == qc_scenario_id), None
                )
                if target_qc_scenario:
                    st.title(
                        f"{recipe.name} - {translate_service.translate('page_title_graphs')} (QC)"
                    )
                    # Display quality check results in graph view (use interpolated output)
                    render_graph_view_step(
                        recipe,
                        cell_culture_state,
                        scenario=target_qc_scenario,
                        output_name=cell_culture_state.QUALITY_CHECK_SCENARIO_INTERPOLATED_OUTPUT_NAME,
                    )
                else:
                    st.error("Quality Check scenario not found")
            elif selected_key.startswith("graphiques_"):
                # Extract scenario ID from key
                scenario_id = selected_key.replace("graphiques_", "")
                # Find the corresponding scenario
                selection_scenarios = recipe.get_selection_scenarios()
                target_scenario = next(
                    (s for s in selection_scenarios if s.id == scenario_id), None
                )
                if target_scenario:
                    st.title(f"{recipe.name} - {translate_service.translate('page_title_graphs')}")
                    render_graph_view_step(
                        recipe,
                        cell_culture_state,
                        scenario=target_scenario,
                        output_name=cell_culture_state.INTERPOLATION_SCENARIO_OUTPUT_NAME,
                    )
                else:
                    st.error(translate_service.translate("selection_scenario_not_found"))
            elif selected_key.startswith("medium_"):
                # Extract scenario ID from key
                scenario_id = selected_key.replace("medium_", "")
                # Find the corresponding scenario
                selection_scenarios = recipe.get_selection_scenarios()
                target_scenario = next(
                    (s for s in selection_scenarios if s.id == scenario_id), None
                )
                if target_scenario:
                    st.title(f"{recipe.name} - {translate_service.translate('page_title_medium')}")
                    render_medium_view_step(
                        recipe,
                        cell_culture_state,
                        scenario=target_scenario,
                        output_name=cell_culture_state.INTERPOLATION_SCENARIO_OUTPUT_NAME,
                    )
                else:
                    st.error(translate_service.translate("selection_scenario_not_found"))
            elif selected_key.startswith("qc_medium_"):
                # Extract quality check scenario ID from key
                qc_scenario_id = selected_key.replace("qc_medium_", "")
                # Find the corresponding quality check scenario
                all_qc_scenarios = recipe.get_quality_check_scenarios()
                target_qc_scenario = next(
                    (s for s in all_qc_scenarios if s.id == qc_scenario_id), None
                )
                if target_qc_scenario:
                    st.title(f"{recipe.name} - Medium (QC)")
                    # Display quality check results in medium view
                    render_medium_view_step(
                        recipe,
                        cell_culture_state,
                        scenario=target_qc_scenario,
                        output_name=cell_culture_state.QUALITY_CHECK_SCENARIO_OUTPUT_NAME,
                    )
                else:
                    st.error("Quality Check scenario not found")
            elif selected_key.startswith("analysis_medium_pca_qc_"):
                # Extract quality check scenario ID from key (analysis_medium_pca_qc_{qc_id})
                qc_scenario_id = selected_key.replace("analysis_medium_pca_qc_", "")
                # Find the corresponding quality check scenario
                all_qc_scenarios = recipe.get_quality_check_scenarios()
                target_qc_scenario = next(
                    (s for s in all_qc_scenarios if s.id == qc_scenario_id), None
                )
                if target_qc_scenario:
                    st.title(f"{recipe.name} - Medium PCA Analysis")
                    render_medium_pca_step(
                        recipe, cell_culture_state, quality_check_scenario=target_qc_scenario
                    )
                else:
                    st.error("Quality Check scenario not found")
            elif selected_key.startswith("analysis_medium_umap_qc_"):
                # Extract quality check scenario ID from key (analysis_medium_umap_qc_{qc_id})
                qc_scenario_id = selected_key.replace("analysis_medium_umap_qc_", "")
                # Find the corresponding quality check scenario
                all_qc_scenarios = recipe.get_quality_check_scenarios()
                target_qc_scenario = next(
                    (s for s in all_qc_scenarios if s.id == qc_scenario_id), None
                )
                if target_qc_scenario:
                    st.title(f"{recipe.name} - Medium UMAP Analysis")
                    render_medium_umap_step(
                        recipe, cell_culture_state, quality_check_scenario=target_qc_scenario
                    )
                else:
                    st.error("Quality Check scenario not found")
            elif selected_key.startswith("analysis_feature_extraction_qc_"):
                # Extract quality check scenario ID from key (analysis_feature_extraction_qc_{qc_id})
                qc_scenario_id = selected_key.replace("analysis_feature_extraction_qc_", "")
                # Find the corresponding quality check scenario
                all_qc_scenarios = recipe.get_quality_check_scenarios()
                target_qc_scenario = next(
                    (s for s in all_qc_scenarios if s.id == qc_scenario_id), None
                )
                if target_qc_scenario:
                    st.title(f"{recipe.name} - Feature Extraction Analysis")
                    render_feature_extraction_step(
                        recipe, cell_culture_state, quality_check_scenario=target_qc_scenario
                    )
                else:
                    st.error("Quality Check scenario not found")
            elif selected_key.startswith("pca_result_"):
                # Extract PCA scenario ID from key (pca_result_{pca_scenario_id})
                pca_scenario_id = selected_key.replace("pca_result_", "")
                # Find the corresponding PCA scenario in 'analyses' step
                all_analyses_scenarios = recipe.get_scenarios_for_step("analyses")
                target_pca_scenario = next(
                    (s for s in all_analyses_scenarios if s.id == pca_scenario_id), None
                )
                if target_pca_scenario:
                    # Use the render function from medium_pca_results.py
                    render_medium_pca_results(recipe, cell_culture_state, target_pca_scenario)
                else:
                    st.error("PCA scenario not found")
            elif selected_key.startswith("umap_result_"):
                # Extract UMAP scenario ID from key (umap_result_{umap_scenario_id})
                umap_scenario_id = selected_key.replace("umap_result_", "")
                # Find the corresponding UMAP scenario in 'analyses' step
                all_analyses_scenarios = recipe.get_scenarios_for_step("analyses")
                target_umap_scenario = next(
                    (s for s in all_analyses_scenarios if s.id == umap_scenario_id), None
                )
                if target_umap_scenario:
                    # Use the render function from medium_umap_results.py
                    render_medium_umap_results(recipe, cell_culture_state, target_umap_scenario)
                else:
                    st.error("UMAP scenario not found")
            elif selected_key.startswith("fe_result_"):
                # Extract Feature Extraction scenario ID from key (fe_result_{fe_scenario_id})
                fe_scenario_id = selected_key.replace("fe_result_", "")
                # Find the corresponding FE scenario in 'analyses' step
                all_analyses_scenarios = recipe.get_scenarios_for_step("analyses")
                target_fe_scenario = next(
                    (s for s in all_analyses_scenarios if s.id == fe_scenario_id), None
                )
                if target_fe_scenario:
                    # Use the render function from feature_extraction_results.py
                    render_feature_extraction_results(
                        recipe, cell_culture_state, target_fe_scenario
                    )
                else:
                    st.error("Feature Extraction scenario not found")
            elif selected_key.startswith("analysis_metadata_feature_umap_fe_"):
                # Extract Feature Extraction scenario ID from key (analysis_metadata_feature_umap_fe_{fe_scenario_id})
                fe_scenario_id = selected_key.replace("analysis_metadata_feature_umap_fe_", "")
                # Find the corresponding FE scenario in 'analyses' step
                all_analyses_scenarios = recipe.get_scenarios_for_step("analyses")
                target_fe_scenario = next(
                    (s for s in all_analyses_scenarios if s.id == fe_scenario_id), None
                )
                if target_fe_scenario:
                    # Find the quality check scenario (parent of the FE scenario)
                    entity_tag_list = EntityTagList.find_by_entity(
                        TagEntityType.SCENARIO, fe_scenario_id
                    )
                    parent_qc_tags = entity_tag_list.get_tags_by_key(
                        "fermentor_analyses_parent_quality_check"
                    )

                    if parent_qc_tags:
                        qc_scenario_id = parent_qc_tags[0].tag_value
                        all_qc_scenarios = recipe.get_quality_check_scenarios()
                        target_qc_scenario = next(
                            (s for s in all_qc_scenarios if s.id == qc_scenario_id), None
                        )

                        if target_qc_scenario:
                            st.title(f"{recipe.name} - Metadata Feature UMAP Analysis")
                            # Render the step page to launch new analyses or view existing ones
                            render_metadata_feature_umap_step(
                                recipe,
                                cell_culture_state,
                                quality_check_scenario=target_qc_scenario,
                                feature_extraction_scenario=target_fe_scenario,
                            )
                        else:
                            st.error("Quality Check scenario not found")
                    else:
                        st.error(
                            "Parent Quality Check scenario not found for this Feature Extraction"
                        )
                else:
                    st.error("Feature Extraction scenario not found")
            elif selected_key.startswith("metadata_feature_umap_result_"):
                # Extract UMAP scenario ID from key (metadata_feature_umap_result_{umap_scenario_id})
                umap_scenario_id = selected_key.replace("metadata_feature_umap_result_", "")
                # Find the corresponding UMAP scenario in 'analyses' step
                all_analyses_scenarios = recipe.get_scenarios_for_step("analyses")
                target_umap_scenario = next(
                    (s for s in all_analyses_scenarios if s.id == umap_scenario_id), None
                )
                if target_umap_scenario:
                    # Use the render function from metadata_feature_umap_results.py
                    render_metadata_feature_umap_results(
                        recipe, cell_culture_state, target_umap_scenario
                    )
                else:
                    st.error("UMAP Metadata+Features scenario not found")
            elif selected_key.startswith("analysis_pls_regression_fe_"):
                # Extract Feature Extraction scenario ID from key (analysis_pls_regression_fe_{fe_scenario_id})
                fe_scenario_id = selected_key.replace("analysis_pls_regression_fe_", "")
                # Find the corresponding FE scenario in 'analyses' step
                all_analyses_scenarios = recipe.get_scenarios_for_step("analyses")
                target_fe_scenario = next(
                    (s for s in all_analyses_scenarios if s.id == fe_scenario_id), None
                )
                if target_fe_scenario:
                    # Find the quality check scenario (parent of the FE scenario)
                    entity_tag_list = EntityTagList.find_by_entity(
                        TagEntityType.SCENARIO, fe_scenario_id
                    )
                    parent_qc_tags = entity_tag_list.get_tags_by_key(
                        "fermentor_analyses_parent_quality_check"
                    )

                    if parent_qc_tags:
                        qc_scenario_id = parent_qc_tags[0].tag_value
                        all_qc_scenarios = recipe.get_quality_check_scenarios()
                        target_qc_scenario = next(
                            (s for s in all_qc_scenarios if s.id == qc_scenario_id), None
                        )

                        if target_qc_scenario:
                            st.title(f"{recipe.name} - PLS Regression Analysis")
                            # Render the step page to launch new analyses or view existing ones
                            render_pls_regression_step(
                                recipe,
                                cell_culture_state,
                                quality_check_scenario=target_qc_scenario,
                                feature_extraction_scenario=target_fe_scenario,
                            )
                        else:
                            st.error("Quality Check scenario not found")
                    else:
                        st.error(
                            "Parent Quality Check scenario not found for this Feature Extraction"
                        )
                else:
                    st.error("Feature Extraction scenario not found")
            elif selected_key.startswith("pls_regression_result_"):
                # Extract PLS scenario ID from key (pls_regression_result_{pls_scenario_id})
                pls_scenario_id = selected_key.replace("pls_regression_result_", "")
                # Find the corresponding PLS scenario in 'analyses' step
                all_analyses_scenarios = recipe.get_scenarios_for_step("analyses")
                target_pls_scenario = next(
                    (s for s in all_analyses_scenarios if s.id == pls_scenario_id), None
                )
                if target_pls_scenario:
                    # Use the render function from pls_regression_results.py
                    render_pls_regression_results(recipe, cell_culture_state, target_pls_scenario)
                else:
                    st.error("PLS Regression scenario not found")
            elif selected_key.startswith("analysis_random_forest_regression_fe_"):
                # Extract Feature Extraction scenario ID from key (analysis_random_forest_regression_fe_{fe_scenario_id})
                fe_scenario_id = selected_key.replace("analysis_random_forest_regression_fe_", "")
                # Find the corresponding FE scenario in 'analyses' step
                all_analyses_scenarios = recipe.get_scenarios_for_step("analyses")
                target_fe_scenario = next(
                    (s for s in all_analyses_scenarios if s.id == fe_scenario_id), None
                )
                if target_fe_scenario:
                    # Find the quality check scenario (parent of the FE scenario)
                    entity_tag_list = EntityTagList.find_by_entity(
                        TagEntityType.SCENARIO, fe_scenario_id
                    )
                    parent_qc_tags = entity_tag_list.get_tags_by_key(
                        "fermentor_analyses_parent_quality_check"
                    )

                    if parent_qc_tags:
                        qc_scenario_id = parent_qc_tags[0].tag_value
                        all_qc_scenarios = recipe.get_quality_check_scenarios()
                        target_qc_scenario = next(
                            (s for s in all_qc_scenarios if s.id == qc_scenario_id), None
                        )

                        if target_qc_scenario:
                            st.title(f"{recipe.name} - Random Forest Regression Analysis")
                            # Render the step page to launch new analyses or view existing ones
                            render_random_forest_step(
                                recipe,
                                cell_culture_state,
                                quality_check_scenario=target_qc_scenario,
                                feature_extraction_scenario=target_fe_scenario,
                            )
                        else:
                            st.error("Quality Check scenario not found")
                    else:
                        st.error(
                            "Parent Quality Check scenario not found for this Feature Extraction"
                        )
                else:
                    st.error("Feature Extraction scenario not found")
            elif selected_key.startswith("random_forest_result_"):
                # Extract Random Forest scenario ID from key (random_forest_result_{rf_scenario_id})
                rf_scenario_id = selected_key.replace("random_forest_result_", "")
                # Find the corresponding Random Forest scenario in 'analyses' step
                all_analyses_scenarios = recipe.get_scenarios_for_step("analyses")
                target_rf_scenario = next(
                    (s for s in all_analyses_scenarios if s.id == rf_scenario_id), None
                )
                if target_rf_scenario:
                    # Use the render function from random_forest_results.py
                    render_random_forest_results(recipe, cell_culture_state, target_rf_scenario)
                else:
                    st.error("Random Forest Regression scenario not found")
            elif selected_key.startswith("analysis_causal_effect_fe_"):
                # Extract Feature Extraction scenario ID from key (analysis_causal_effect_fe_{fe_scenario_id})
                fe_scenario_id = selected_key.replace("analysis_causal_effect_fe_", "")
                # Find the corresponding FE scenario in 'analyses' step
                all_analyses_scenarios = recipe.get_scenarios_for_step("analyses")
                target_fe_scenario = next(
                    (s for s in all_analyses_scenarios if s.id == fe_scenario_id), None
                )
                if target_fe_scenario:
                    # Find the quality check scenario (parent of the FE scenario)
                    entity_tag_list = EntityTagList.find_by_entity(
                        TagEntityType.SCENARIO, fe_scenario_id
                    )
                    parent_qc_tags = entity_tag_list.get_tags_by_key(
                        "fermentor_analyses_parent_quality_check"
                    )

                    if parent_qc_tags:
                        qc_scenario_id = parent_qc_tags[0].tag_value
                        all_qc_scenarios = recipe.get_quality_check_scenarios()
                        target_qc_scenario = next(
                            (s for s in all_qc_scenarios if s.id == qc_scenario_id), None
                        )

                        if target_qc_scenario:
                            st.title(f"{recipe.name} - Causal Effect Analysis")
                            # Render the step page to launch new analyses or view existing ones
                            render_causal_effect_step(
                                recipe,
                                cell_culture_state,
                                quality_check_scenario=target_qc_scenario,
                                feature_extraction_scenario=target_fe_scenario,
                            )
                        else:
                            st.error("Quality Check scenario not found")
                    else:
                        st.error(
                            "Parent Quality Check scenario not found for this Feature Extraction"
                        )
                else:
                    st.error("Feature Extraction scenario not found")
            elif selected_key.startswith("causal_effect_result_"):
                # Extract Causal Effect scenario ID from key (causal_effect_result_{causal_scenario_id})
                causal_scenario_id = selected_key.replace("causal_effect_result_", "")
                # Find the corresponding Causal Effect scenario in 'analyses' step
                all_analyses_scenarios = recipe.get_scenarios_for_step("analyses")
                target_causal_scenario = next(
                    (s for s in all_analyses_scenarios if s.id == causal_scenario_id), None
                )
                if target_causal_scenario:
                    # Use the render function from causal_effect_results.py
                    render_causal_effect_results(recipe, cell_culture_state, target_causal_scenario)
                else:
                    st.error("Causal Effect scenario not found")
            elif selected_key.startswith("analysis_optimization_fe_"):
                # Extract Feature Extraction scenario ID from key (analysis_optimization_fe_{fe_scenario_id})
                fe_scenario_id = selected_key.replace("analysis_optimization_fe_", "")
                # Find the corresponding FE scenario in 'analyses' step
                all_analyses_scenarios = recipe.get_scenarios_for_step("analyses")
                target_fe_scenario = next(
                    (s for s in all_analyses_scenarios if s.id == fe_scenario_id), None
                )
                if target_fe_scenario:
                    # Find the quality check scenario (parent of the FE scenario)
                    entity_tag_list = EntityTagList.find_by_entity(
                        TagEntityType.SCENARIO, fe_scenario_id
                    )
                    parent_qc_tags = entity_tag_list.get_tags_by_key(
                        "fermentor_analyses_parent_quality_check"
                    )

                    if parent_qc_tags:
                        qc_scenario_id = parent_qc_tags[0].tag_value
                        all_qc_scenarios = recipe.get_quality_check_scenarios()
                        target_qc_scenario = next(
                            (s for s in all_qc_scenarios if s.id == qc_scenario_id), None
                        )

                        if target_qc_scenario:
                            st.title(f"{recipe.name} - Optimization Analysis")
                            # Render the step page to launch new analyses or view existing ones
                            render_optimization_step(
                                recipe,
                                cell_culture_state,
                                quality_check_scenario=target_qc_scenario,
                                feature_extraction_scenario=target_fe_scenario,
                            )
                        else:
                            st.error("Quality Check scenario not found")
                    else:
                        st.error(
                            "Parent Quality Check scenario not found for this Feature Extraction"
                        )
                else:
                    st.error("Feature Extraction scenario not found")
            elif selected_key.startswith("optimization_result_"):
                # Extract Optimization scenario ID from key (optimization_result_{opt_scenario_id})
                opt_scenario_id = selected_key.replace("optimization_result_", "")
                # Find the corresponding Optimization scenario in 'analyses' step
                all_analyses_scenarios = recipe.get_scenarios_for_step("analyses")
                target_opt_scenario = next(
                    (s for s in all_analyses_scenarios if s.id == opt_scenario_id), None
                )
                if target_opt_scenario:
                    # Use the render function from optimization_results.py
                    render_optimization_results(cell_culture_state, target_opt_scenario)
                else:
                    st.error("Optimization scenario not found")
            else:
                st.info(translate_service.translate("select_step_in_menu"))
