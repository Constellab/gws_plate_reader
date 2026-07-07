import streamlit as st
from gws_core import Scenario, ScenarioSearchBuilder, Tag
from gws_core.scenario.scenario_enums import ScenarioStatus
from gws_core.tag.entity_tag_list import EntityTagList
from gws_core.tag.tag_entity_type import TagEntityType
from gws_plate_reader.cell_culture_app_core._constellab_bioprocess_core.app_pages.comparison_page import (
    TAG_BIOPROCESS_COMPARISON,
)
from gws_plate_reader.cell_culture_app_core._constellab_bioprocess_core.cell_culture_state import (
    CellCultureState,
)
from gws_plate_reader.cell_culture_app_core._constellab_bioprocess_core.functions_steps import (
    create_recipe_table_data,
    delete_recipe_scenarios,
    rename_recipe_scenarios,
    render_recipe_table,
)
from gws_streamlit_main import StreamlitContainers, StreamlitRouter

# ---------------------------------------------------------------------------
# Modal dialogs (must be at module level for Streamlit to manage their state)
# ---------------------------------------------------------------------------

_CC_DIALOG_STATE_KEY = "_cc_dialog_state"
_CC_DIALOG_RECIPE_ID_KEY = "cell_culture_selected_recipe_id"
_CC_DIALOG_RECIPE_NAME_KEY = "_cc_dialog_recipe_name"
_CC_DIALOG_ACTION_KEY = "cell_culture_recipe_action"


@st.dialog("Rename Recipe")
def _render_rename_dialog() -> None:
    """Modal dialog for renaming a recipe."""
    recipe_id: str = st.session_state[_CC_DIALOG_RECIPE_ID_KEY]
    recipe_name: str = st.session_state.get(_CC_DIALOG_RECIPE_NAME_KEY, "")
    cell_culture_state: CellCultureState = st.session_state[_CC_DIALOG_STATE_KEY]
    translate_service = cell_culture_state.get_translate_service()

    new_name = st.text_input(
        translate_service.translate("rename_recipe_label"),
        value=recipe_name,
    )

    col_save, col_cancel = st.columns(2)
    with col_save:
        if st.button(
            translate_service.translate("save"),
            type="primary",
            use_container_width=True,
        ):
            if not (new_name or "").strip():
                st.error(translate_service.translate("recipe_name_cannot_be_empty"))
            else:
                try:
                    rename_recipe_scenarios(
                        recipe_id,
                        (new_name or "").strip(),
                        cell_culture_state,
                    )
                    st.session_state[_CC_DIALOG_ACTION_KEY] = None
                    st.session_state[_CC_DIALOG_RECIPE_ID_KEY] = None
                    st.session_state["cell_culture_recipes_refresh"] = (
                        st.session_state.get("cell_culture_recipes_refresh", 0) + 1
                    )
                    st.rerun()
                except Exception as e:  # noqa: BLE001
                    st.error(
                        translate_service.translate("error_renaming_recipe").format(error=str(e))
                    )
    with col_cancel:
        if st.button(translate_service.translate("cancel"), use_container_width=True):
            st.session_state[_CC_DIALOG_ACTION_KEY] = None
            st.session_state[_CC_DIALOG_RECIPE_ID_KEY] = None
            st.rerun()


@st.dialog("Delete Recipe")
def _render_delete_dialog() -> None:
    """Modal dialog for confirming recipe deletion."""
    recipe_id: str = st.session_state[_CC_DIALOG_RECIPE_ID_KEY]
    recipe_name: str = st.session_state.get(_CC_DIALOG_RECIPE_NAME_KEY, "")
    cell_culture_state: CellCultureState = st.session_state[_CC_DIALOG_STATE_KEY]
    translate_service = cell_culture_state.get_translate_service()

    st.warning(translate_service.translate("confirm_delete_recipe").format(recipe_name=recipe_name))

    col_confirm, col_cancel = st.columns(2)
    with col_confirm:
        if st.button(
            translate_service.translate("confirm_delete"),
            type="primary",
            use_container_width=True,
        ):
            try:
                delete_recipe_scenarios(recipe_id, cell_culture_state)
                st.session_state[_CC_DIALOG_ACTION_KEY] = None
                st.session_state[_CC_DIALOG_RECIPE_ID_KEY] = None
                st.session_state["cell_culture_recipes_refresh"] = (
                    st.session_state.get("cell_culture_recipes_refresh", 0) + 1
                )
                st.rerun()
            except Exception as e:  # noqa: BLE001
                st.error(translate_service.translate("error_deleting_recipe").format(error=str(e)))
    with col_cancel:
        if st.button(translate_service.translate("cancel"), use_container_width=True):
            st.session_state[_CC_DIALOG_ACTION_KEY] = None
            st.session_state[_CC_DIALOG_RECIPE_ID_KEY] = None
            st.rerun()


def render_first_page(cell_culture_state: CellCultureState) -> None:
    """Render the main page showing list of existing analyses."""

    translate_service = cell_culture_state.get_translate_service()

    style = """
    [CLASS_NAME] {
        padding: 40px;
    }
    """

    with StreamlitContainers.container_full_min_height(
        "container-center_first_page", additional_style=style
    ):
        # Header with title, refresh button and create new analysis button
        cols_config = [1, "fit-content"]
        if not cell_culture_state.get_is_standalone():
            cols_config = [1, "fit-content", "fit-content", "fit-content"]

        header_cols = StreamlitContainers.columns_with_fit_content(
            key="button_new", cols=cols_config, vertical_align_items="center"
        )

        with header_cols[0]:
            st.markdown(f"## {translate_service.translate('recipes_list_title')}")

        if not cell_culture_state.get_is_standalone():
            with header_cols[1]:
                if st.button(
                    translate_service.translate("refresh"),
                    icon=":material/refresh:",
                    width="content",
                ):
                    # Increment refresh counter to force slickgrid re-initialization
                    st.session_state["cell_culture_recipes_refresh"] = (
                        st.session_state.get("cell_culture_recipes_refresh", 0) + 1
                    )
                    # Also clear the old slickgrid key if present
                    keys_to_delete = [
                        k for k in st.session_state if k.startswith("cell_culture_recipes_grid")
                    ]
                    for k in keys_to_delete:
                        del st.session_state[k]
                    st.rerun()

            with header_cols[2]:
                if st.button(
                    translate_service.translate("create_new_recipe"),
                    icon=":material/add:",
                    width="content",
                    type="primary",
                ):
                    router = StreamlitRouter.load_from_session()
                    router.navigate("new-analysis")

        # Search for existing cell culture analyses (both load and selection scenarios)
        # Get load scenarios
        load_scenarios = (
            ScenarioSearchBuilder()
            .add_tag_filter(
                Tag(
                    key=cell_culture_state.TAG_BIOPROCESS,
                    value=cell_culture_state.TAG_DATA_PROCESSING,
                )
            )
            .add_is_archived_filter(False)
            .search_all()
        )

        # Get selection scenarios
        selection_scenarios = (
            ScenarioSearchBuilder()
            .add_tag_filter(
                Tag(
                    key=cell_culture_state.TAG_BIOPROCESS,
                    value=cell_culture_state.TAG_SELECTION_PROCESSING,
                )
            )
            .add_is_archived_filter(False)
            .search_all()
        )

        # Get quality check scenarios
        quality_check_scenarios = (
            ScenarioSearchBuilder()
            .add_tag_filter(
                Tag(
                    key=cell_culture_state.TAG_BIOPROCESS,
                    value=cell_culture_state.TAG_QUALITY_CHECK_PROCESSING,
                )
            )
            .add_is_archived_filter(False)
            .search_all()
        )

        # Get analyses scenarios
        analyses_scenarios = (
            ScenarioSearchBuilder()
            .add_tag_filter(
                Tag(
                    key=cell_culture_state.TAG_BIOPROCESS,
                    value=cell_culture_state.TAG_ANALYSES_PROCESSING,
                )
            )
            .add_is_archived_filter(False)
            .search_all()
        )

        # Sort all scenarios by creation date (oldest first, most recent last)
        selection_scenarios.sort(key=lambda s: s.created_at or s.last_modified_at, reverse=False)
        quality_check_scenarios.sort(
            key=lambda s: s.created_at or s.last_modified_at, reverse=False
        )
        analyses_scenarios.sort(key=lambda s: s.created_at or s.last_modified_at, reverse=False)

        # Create dictionary with unique key (recipe_name + scenario_id) and scenarios structure as value
        recipes_dict = {}

        # First, organize load scenarios by recipe name + scenario ID
        for scenario in load_scenarios:
            entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)
            recipe_name_tags = entity_tag_list.get_tags_by_key(
                cell_culture_state.TAG_BIOPROCESS_RECIPE_NAME
            )
            recipe_name = recipe_name_tags[0].tag_value if recipe_name_tags else scenario.title

            # Use a unique key combining recipe name and scenario ID to avoid collisions
            unique_key = f"{recipe_name}_{scenario.id}"

            recipes_dict[unique_key] = {
                "recipe_name": recipe_name,
                "load_scenario": scenario,
                "selection_scenarios": [],
                "quality_check_scenarios": [],
                "analyses_scenarios": [],
            }

        # Then, add selection scenarios to their corresponding recipes
        for scenario in selection_scenarios:
            entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)
            recipe_name_tags = entity_tag_list.get_tags_by_key(
                cell_culture_state.TAG_BIOPROCESS_RECIPE_NAME
            )
            recipe_name = recipe_name_tags[0].tag_value if recipe_name_tags else scenario.title

            # Get pipeline_id to match with the correct load scenario
            pipeline_id_tags = entity_tag_list.get_tags_by_key(
                cell_culture_state.TAG_BIOPROCESS_PIPELINE_ID
            )
            pipeline_id = pipeline_id_tags[0].tag_value if pipeline_id_tags else None

            # Find the matching recipe by pipeline_id
            for _unique_key, recipe_data in recipes_dict.items():
                load_scenario = recipe_data["load_scenario"]
                load_entity_tags = EntityTagList.find_by_entity(
                    TagEntityType.SCENARIO, load_scenario.id
                )
                load_pipeline_id_tags = load_entity_tags.get_tags_by_key(
                    cell_culture_state.TAG_BIOPROCESS_PIPELINE_ID
                )
                load_pipeline_id = (
                    load_pipeline_id_tags[0].tag_value if load_pipeline_id_tags else None
                )

                if pipeline_id and load_pipeline_id and pipeline_id == load_pipeline_id:
                    recipe_data["selection_scenarios"].append(scenario)
                    break

        # Then, add quality check scenarios to their corresponding recipes
        for scenario in quality_check_scenarios:
            entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)
            recipe_name_tags = entity_tag_list.get_tags_by_key(
                cell_culture_state.TAG_BIOPROCESS_RECIPE_NAME
            )
            recipe_name = recipe_name_tags[0].tag_value if recipe_name_tags else scenario.title

            # Get pipeline_id to match with the correct load scenario
            pipeline_id_tags = entity_tag_list.get_tags_by_key(
                cell_culture_state.TAG_BIOPROCESS_PIPELINE_ID
            )
            pipeline_id = pipeline_id_tags[0].tag_value if pipeline_id_tags else None

            # Find the matching recipe by pipeline_id
            for _unique_key, recipe_data in recipes_dict.items():
                load_scenario = recipe_data["load_scenario"]
                load_entity_tags = EntityTagList.find_by_entity(
                    TagEntityType.SCENARIO, load_scenario.id
                )
                load_pipeline_id_tags = load_entity_tags.get_tags_by_key(
                    cell_culture_state.TAG_BIOPROCESS_PIPELINE_ID
                )
                load_pipeline_id = (
                    load_pipeline_id_tags[0].tag_value if load_pipeline_id_tags else None
                )

                if pipeline_id and load_pipeline_id and pipeline_id == load_pipeline_id:
                    recipe_data["quality_check_scenarios"].append(scenario)
                    break

        # Finally, add analyses scenarios to their corresponding recipes
        for scenario in analyses_scenarios:
            entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)
            recipe_name_tags = entity_tag_list.get_tags_by_key(
                cell_culture_state.TAG_BIOPROCESS_RECIPE_NAME
            )
            recipe_name = recipe_name_tags[0].tag_value if recipe_name_tags else scenario.title

            # Get pipeline_id to match with the correct load scenario
            pipeline_id_tags = entity_tag_list.get_tags_by_key(
                cell_culture_state.TAG_BIOPROCESS_PIPELINE_ID
            )
            pipeline_id = pipeline_id_tags[0].tag_value if pipeline_id_tags else None

            # Find the matching recipe by pipeline_id
            for _unique_key, recipe_data in recipes_dict.items():
                load_scenario = recipe_data["load_scenario"]
                load_entity_tags = EntityTagList.find_by_entity(
                    TagEntityType.SCENARIO, load_scenario.id
                )
                load_pipeline_id_tags = load_entity_tags.get_tags_by_key(
                    cell_culture_state.TAG_BIOPROCESS_PIPELINE_ID
                )
                load_pipeline_id = (
                    load_pipeline_id_tags[0].tag_value if load_pipeline_id_tags else None
                )

                if pipeline_id and load_pipeline_id and pipeline_id == load_pipeline_id:
                    recipe_data["analyses_scenarios"].append(scenario)
                    break

        # Query comparison scenarios to include in the same table
        comparison_scenarios = (
            ScenarioSearchBuilder()
            .add_tag_filter(
                Tag(
                    key=cell_culture_state.TAG_BIOPROCESS,
                    value=TAG_BIOPROCESS_COMPARISON,
                )
            )
            .add_is_archived_filter(False)
            .search_all()
        )
        comparison_scenario_ids = {sc.id for sc in comparison_scenarios}

        # Pass all scenarios - the table function will filter and group them correctly
        list_scenario_user: list[Scenario] = (
            load_scenarios + selection_scenarios + quality_check_scenarios + comparison_scenarios
        )

        # Use the new centralized function to render the table
        grid_selection = render_recipe_table(list_scenario_user, cell_culture_state)

        if grid_selection is not None:
            selected_scenario_id, clicked_column = grid_selection

            if (
                clicked_column in ("_action_rename", "_action_delete")
                and not cell_culture_state.get_is_standalone()
            ):
                # Action icon column clicked — resolve recipe name then open dialog
                action = "rename" if clicked_column == "_action_rename" else "delete"
                table_data_for_dialog = create_recipe_table_data(
                    list_scenario_user, cell_culture_state, translate_service
                )
                action_row = next(
                    (r for r in table_data_for_dialog if r.get("id") == selected_scenario_id),
                    None,
                )
                st.session_state[_CC_DIALOG_RECIPE_ID_KEY] = selected_scenario_id
                st.session_state[_CC_DIALOG_ACTION_KEY] = action
                st.session_state[_CC_DIALOG_RECIPE_NAME_KEY] = (
                    action_row["Recipe Name"] if action_row else ""
                )
                st.session_state[_CC_DIALOG_STATE_KEY] = cell_culture_state
                st.rerun()

            elif selected_scenario_id in comparison_scenario_ids:
                # Comparison recipe clicked — navigate directly
                for sc in comparison_scenarios:
                    if sc.id == selected_scenario_id:
                        recipe_instance = cell_culture_state.create_recipe_from_scenario(sc)
                        cell_culture_state.set_selected_recipe_instance(recipe_instance)
                        router = StreamlitRouter.load_from_session()
                        router.navigate("analysis")
                        st.rerun()
                        break

            else:
                # Check if the load scenario finished successfully
                table_data_nav = create_recipe_table_data(
                    list_scenario_user, cell_culture_state, translate_service
                )
                selected_row = next(
                    (row for row in table_data_nav if row.get("id") == selected_scenario_id),
                    None,
                )
                if selected_row and selected_row.get("_status_raw") != ScenarioStatus.SUCCESS.value:
                    st.warning(translate_service.translate("recipe_not_ready"))
                else:
                    selected_recipe_name = None
                    selected_load_scenario = None

                    for scenario in load_scenarios:
                        if scenario.id == selected_scenario_id:
                            entity_tag_list = EntityTagList.find_by_entity(
                                TagEntityType.SCENARIO, scenario.id
                            )
                            recipe_name_tags = entity_tag_list.get_tags_by_key(
                                cell_culture_state.TAG_BIOPROCESS_RECIPE_NAME
                            )
                            selected_recipe_name = (
                                recipe_name_tags[0].tag_value
                                if recipe_name_tags
                                else scenario.title
                            )
                            selected_load_scenario = scenario
                            break

                    if not selected_recipe_name:
                        table_data_nav = create_recipe_table_data(
                            list_scenario_user, cell_culture_state, translate_service
                        )
                        selected_row_data = next(
                            (
                                row
                                for row in table_data_nav
                                if row.get("id") == selected_scenario_id
                            ),
                            None,
                        )
                        if selected_row_data:
                            selected_recipe_name = selected_row_data["Recipe Name"]
                            for _unique_key, recipe_data in recipes_dict.items():
                                if recipe_data["load_scenario"].id == selected_scenario_id:
                                    selected_load_scenario = recipe_data["load_scenario"]
                                    break

                    if selected_recipe_name and selected_load_scenario:
                        matching_unique_key = None
                        for unique_key, recipe_data in recipes_dict.items():
                            if recipe_data["load_scenario"].id == selected_load_scenario.id:
                                matching_unique_key = unique_key
                                break

                        if matching_unique_key:
                            recipe_instance = cell_culture_state.create_recipe_from_scenario(
                                selected_load_scenario
                            )
                            recipe_data = recipes_dict[matching_unique_key]
                            if recipe_data["selection_scenarios"]:
                                recipe_instance.add_selection_scenarios(
                                    recipe_data["selection_scenarios"]
                                )
                            if (
                                "quality_check_scenarios" in recipe_data
                                and recipe_data["quality_check_scenarios"]
                            ):
                                recipe_instance.add_scenarios_by_step(
                                    "quality_check", recipe_data["quality_check_scenarios"]
                                )
                            if (
                                "analyses_scenarios" in recipe_data
                                and recipe_data["analyses_scenarios"]
                            ):
                                recipe_instance.add_scenarios_by_step(
                                    "analyses", recipe_data["analyses_scenarios"]
                                )
                            cell_culture_state.set_selected_recipe_instance(recipe_instance)
                            router = StreamlitRouter.load_from_session()
                            router.navigate("analysis")
                            st.rerun()

        # Open the appropriate modal dialog when an action icon was clicked
        if (
            st.session_state.get(_CC_DIALOG_ACTION_KEY)
            and st.session_state.get(_CC_DIALOG_RECIPE_ID_KEY)
            and not cell_culture_state.get_is_standalone()
        ):
            if st.session_state[_CC_DIALOG_ACTION_KEY] == "rename":
                _render_rename_dialog()
            elif st.session_state[_CC_DIALOG_ACTION_KEY] == "delete":
                _render_delete_dialog()

        # Show info message and getting started if no recipes
        if not recipes_dict:
            # No recipes found - show getting started guide
            st.subheader(f"{translate_service.translate('getting_started')}")

            # Show example of what the recipe includes
            with st.expander(f"{translate_service.translate('what_is_recipe')}"):
                st.markdown(f"""
                {translate_service.translate("recipe_includes")}

                **📁 {translate_service.translate("required_input_files")}**
                - {translate_service.translate("info_csv_desc")}
                - {translate_service.translate("raw_data_csv_desc")}
                - {translate_service.translate("medium_csv_desc")}
                - {translate_service.translate("follow_up_zip_desc")}

                **🔄 {translate_service.translate("automatic_processing")}**
                - {translate_service.translate("processing_merge")}
                - {translate_service.translate("processing_detect")}
                - {translate_service.translate("processing_create")}

                **📊 {translate_service.translate("results")}**
                - {translate_service.translate("results_cleaned")}
                - {translate_service.translate("results_viz")}
                - {translate_service.translate("results_stats")}
                - {translate_service.translate("results_export")}
                """)
            st.markdown("")

            # Add direct call-to-action
            if not cell_culture_state.get_is_standalone():
                st.markdown("---")
                if st.button(
                    f"{translate_service.translate('create_first_analysis')}",
                    type="primary",
                    width="stretch",
                ):
                    router = StreamlitRouter.load_from_session()
                    router.navigate("new-analysis")
