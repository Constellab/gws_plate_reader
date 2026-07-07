import pandas as pd
import streamlit as st
from gws_core import (
    Scenario,
    ScenarioProxy,
    ScenarioSearchBuilder,
    ScenarioStatus,
    Tag,
)
from gws_core.entity_navigator.entity_navigator_service import EntityNavigatorService
from gws_core.protocol.protocol_model import ProtocolModel
from gws_core.scenario.scenario_service import ScenarioService
from gws_core.tag.entity_tag_list import EntityTagList
from gws_core.tag.tag import TagOrigin
from gws_core.tag.tag_entity_type import TagEntityType
from gws_plate_reader.cell_culture_app_core._constellab_bioprocess_core.cell_culture_state import (
    CellCultureState,
)
from gws_streamlit_main import StreamlitTranslateService
from streamlit_slickgrid import slickgrid


def get_status_emoji(status: ScenarioStatus) -> str:
    """Return appropriate emoji for scenario status"""
    emoji_map = {
        ScenarioStatus.DRAFT: "📝",
        ScenarioStatus.IN_QUEUE: "⏳",
        ScenarioStatus.WAITING_FOR_CLI_PROCESS: "⏸️",
        ScenarioStatus.RUNNING: "🔄",
        ScenarioStatus.SUCCESS: "✅",
        ScenarioStatus.ERROR: "❌",
        ScenarioStatus.PARTIALLY_RUN: "✔️",
    }
    return emoji_map.get(status, "❓")


def get_status_prettify(
    status: ScenarioStatus, translate_service: StreamlitTranslateService
) -> str:
    """Return a human-readable string for scenario status"""
    prettify_map = {
        ScenarioStatus.DRAFT: translate_service.translate("status_draft"),
        ScenarioStatus.IN_QUEUE: translate_service.translate("status_in_queue"),
        ScenarioStatus.WAITING_FOR_CLI_PROCESS: translate_service.translate("status_waiting"),
        ScenarioStatus.RUNNING: translate_service.translate("status_running"),
        ScenarioStatus.SUCCESS: translate_service.translate("status_success"),
        ScenarioStatus.ERROR: translate_service.translate("status_error"),
        ScenarioStatus.PARTIALLY_RUN: translate_service.translate("status_partially_run"),
    }
    return prettify_map.get(status, translate_service.translate("status_unknown"))


def get_status_material_icon(status: ScenarioStatus) -> str:
    """Return Material icon for scenario status"""
    icon_map = {
        ScenarioStatus.DRAFT: "edit_note",
        ScenarioStatus.IN_QUEUE: "schedule",
        ScenarioStatus.WAITING_FOR_CLI_PROCESS: "pause_circle",
        ScenarioStatus.RUNNING: "sync",
        ScenarioStatus.SUCCESS: "check_circle",
        ScenarioStatus.ERROR: "error",
        ScenarioStatus.PARTIALLY_RUN: "check_circle_outline",
    }
    return icon_map.get(status, "help")


def get_biolector_emoji(is_biolector: bool) -> str:
    """Return appropriate emoji for biolector analysis"""
    return "🧫" if is_biolector else "🧪"


def render_launched_scenarios_expander(
    scenarios: list[Scenario],
    nav_key_prefix: str,
    title_prefix: str,
    translate_service: StreamlitTranslateService,
) -> None:
    """Render an expander showing previously launched scenarios with clickable navigation buttons.

    :param scenarios: List of Scenario objects to display
    :param nav_key_prefix: Navigation key prefix for routing (e.g., "pca_result_")
    :param title_prefix: Prefix to strip from scenario titles for display (e.g., "Medium PCA - ")
    :param translate_service: Translation service instance
    """
    if not scenarios:
        return

    count = len(scenarios)
    expander_label = f"{translate_service.translate('launched_scenarios')} ({count})"

    with st.expander(expander_label, expanded=False):
        for scenario in scenarios:
            # Clean the title by removing the type prefix
            display_title = scenario.title
            if title_prefix and title_prefix in display_title:
                display_title = display_title.replace(title_prefix, "")

            # Build display line: emoji + title + status text
            emoji = get_status_emoji(scenario.status)
            status_text = get_status_prettify(scenario.status, translate_service)
            button_label = f"{emoji} {display_title} — {status_text}"

            if st.button(
                button_label,
                key=f"nav_{nav_key_prefix}{scenario.id}",
                width="stretch",
            ):
                st.session_state["_force_nav_key"] = f"{nav_key_prefix}{scenario.id}"
                st.rerun()


def create_recipe_table_data(
    scenarios: list[Scenario],
    cell_culture_state: CellCultureState,
    translate_service: StreamlitTranslateService,
) -> list[dict]:
    """Create table data from cell culture recipe scenarios, grouped by recipe."""
    table_data = []

    # Group scenarios by unique key (recipe name + scenario ID to handle duplicate names)
    recipes_dict = {}

    for scenario in scenarios:
        try:
            # Get tags for this scenario using find_by_entity to get existing tags
            entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)

            # Extract recipe name
            recipe_name = translate_service.translate("recipe_unnamed")
            recipe_name_tags = entity_tag_list.get_tags_by_key(
                cell_culture_state.TAG_BIOPROCESS_RECIPE_NAME
            )
            if recipe_name_tags:
                recipe_name = recipe_name_tags[0].tag_value
            else:
                # Fallback to scenario title if no tag found
                recipe_name = (
                    scenario.title
                    if scenario.title
                    else translate_service.translate("summary_scenario").format(id=scenario.id[:8])
                )

            # Check if this is a comparison scenario - add directly as its own row
            bioprocess_tags = entity_tag_list.get_tags_by_key(cell_culture_state.TAG_BIOPROCESS)
            is_comparison = any(tag.tag_value == "comparison" for tag in bioprocess_tags)
            if is_comparison:
                bio_qc_tags = entity_tag_list.get_tags_by_key("comparison_bio_qc_id")
                ferm_qc_tags = entity_tag_list.get_tags_by_key("comparison_ferm_qc_id")
                comparison_done = bool(bio_qc_tags and ferm_qc_tags)
                comparison_status = (
                    f"{get_status_emoji(ScenarioStatus.SUCCESS)} {get_status_prettify(ScenarioStatus.SUCCESS, translate_service)}"
                    if comparison_done
                    else ""
                )
                comparison_status_raw = ScenarioStatus.SUCCESS.value if comparison_done else "comparison"
                table_data.append(
                    {
                        "id": scenario.id,
                        "Recipe Name": recipe_name,
                        "Type": f"🔎 {translate_service.translate('type_comparison')}",
                        "Status": comparison_status,
                        "Folder": scenario.folder.name
                        if scenario.folder
                        else translate_service.translate("summary_root_folder"),
                        "Created": scenario.created_at.strftime("%d/%m/%Y %H:%M")
                        if scenario.created_at
                        else "",
                        "Created By": scenario.created_by.full_name if scenario.created_by else "",
                        "_status_raw": comparison_status_raw,
                        "_is_comparison": True,
                        "_action_rename": "✏️",
                        "_action_delete": "🗑️",
                    }
                )
                continue

            # Check if this is a load scenario (data processing)
            fermentor_tags = entity_tag_list.get_tags_by_key(cell_culture_state.TAG_BIOPROCESS)
            is_load_scenario = any(
                tag.tag_value == cell_culture_state.TAG_DATA_PROCESSING for tag in fermentor_tags
            )

            # Check if this is a selection scenario
            selection_tags = entity_tag_list.get_tags_by_key(cell_culture_state.TAG_BIOPROCESS)
            is_selection_scenario = any(
                tag.tag_value == cell_culture_state.TAG_SELECTION_PROCESSING
                for tag in selection_tags
            )

            # Check if this is a quality check scenario
            quality_check_tags = entity_tag_list.get_tags_by_key(cell_culture_state.TAG_BIOPROCESS)
            is_quality_check_scenario = any(
                tag.tag_value == cell_culture_state.TAG_QUALITY_CHECK_PROCESSING
                for tag in quality_check_tags
            )

            # Get pipeline_id to create unique key
            pipeline_id_tags = entity_tag_list.get_tags_by_key(
                cell_culture_state.TAG_BIOPROCESS_PIPELINE_ID
            )
            pipeline_id = pipeline_id_tags[0].tag_value if pipeline_id_tags else scenario.id

            # Use pipeline_id as unique key to group related scenarios
            unique_key = pipeline_id

            # Initialize recipe entry if not exists
            if unique_key not in recipes_dict:
                recipes_dict[unique_key] = {
                    "recipe_name": recipe_name,
                    "load_scenario": None,
                    "selection_scenarios": [],
                    "quality_check_scenarios": [],
                    "pipeline_id": "",
                    "is_microplate": False,
                    "folder_name": translate_service.translate("summary_root_folder"),
                    "created_at": None,
                    "created_by": "",
                }

            if is_load_scenario:
                recipes_dict[unique_key]["load_scenario"] = scenario
                recipes_dict[unique_key]["recipe_name"] = recipe_name

                # Extract additional info from load scenario
                if pipeline_id_tags:
                    recipes_dict[unique_key]["pipeline_id"] = (
                        pipeline_id_tags[0].tag_value[:8] + "..."
                    )

                # Extract microplate status
                microplate_tags = entity_tag_list.get_tags_by_key(
                    cell_culture_state.TAG_MICROPLATE_ANALYSIS
                )
                if microplate_tags:
                    recipes_dict[unique_key]["is_microplate"] = (
                        microplate_tags[0].tag_value.lower() == "true"
                    )

                # Get folder name
                if scenario.folder:
                    recipes_dict[unique_key]["folder_name"] = scenario.folder.name

                # Set creation info
                recipes_dict[unique_key]["created_at"] = scenario.created_at
                recipes_dict[unique_key]["created_by"] = (
                    scenario.created_by.full_name if scenario.created_by else ""
                )

            elif is_selection_scenario:
                recipes_dict[unique_key]["selection_scenarios"].append(scenario)

            elif is_quality_check_scenario:
                recipes_dict[unique_key]["quality_check_scenarios"].append(scenario)

        except Exception as e:
            # Si erreur lors du traitement d'un scénario, on l'ignore et continue
            st.warning(
                translate_service.translate("error_processing_scenario").format(
                    id=scenario.id, error=str(e)
                )
            )
            continue

    # Create table rows from grouped recipes
    for unique_key, recipe_data in recipes_dict.items():
        try:
            load_scenario = recipe_data["load_scenario"]

            # Only create a table row if there is a load scenario
            # Selection scenarios alone should not create rows
            if not load_scenario:
                continue

            recipe_id = load_scenario.id

            row_data = {
                "id": recipe_id,  # Use load scenario ID
                "Recipe Name": recipe_data["recipe_name"],
                "Type": f"{get_biolector_emoji(recipe_data['is_microplate'])} {translate_service.translate('type_biolector') if recipe_data['is_microplate'] else translate_service.translate('type_fermentor')}",
                "Status": f"{get_status_emoji(load_scenario.status)} {get_status_prettify(load_scenario.status, translate_service)}",
                "Folder": recipe_data["folder_name"],
                "Created": recipe_data["created_at"].strftime("%d/%m/%Y %H:%M")
                if recipe_data["created_at"]
                else "",
                "Created By": recipe_data["created_by"],
                "_status_raw": load_scenario.status.value,
                "_action_rename": "✏️",
                "_action_delete": "🗑️",
            }

            table_data.append(row_data)

        except Exception as e:
            # Si erreur lors du traitement d'une recette, on l'ignore et continue
            st.warning(
                translate_service.translate("error_processing_recipe").format(
                    recipe_name=unique_key, error=str(e)
                )
            )
            continue

    # order table_data by Created date descending
    table_data.sort(
        key=lambda x: pd.to_datetime(x["Created"], format="%d/%m/%Y %H:%M")
        if x["Created"]
        else pd.Timestamp.min,
        reverse=True,
    )

    return table_data


def create_slickgrid_columns(translate_service: StreamlitTranslateService) -> list[dict]:
    """Create SlickGrid columns for cell culture recipe table with step columns."""
    columns = [
        {
            "id": "Recipe Name",
            "name": translate_service.translate("column_recipe_name"),
            "field": "Recipe Name",
            "sortable": True,
            "type": "string",
            "filterable": True,
            "width": 250,
        },
        {
            "id": "Type",
            "name": translate_service.translate("column_type"),
            "field": "Type",
            "sortable": True,
            "type": "string",
            "filterable": True,
            "width": 150,
        },
        {
            "id": "Status",
            "name": translate_service.translate("column_status"),
            "field": "Status",
            "sortable": True,
            "type": "string",
            "filterable": True,
            "width": 150,
        },
        {
            "id": "Created",
            "name": translate_service.translate("column_created"),
            "field": "Created",
            "sortable": True,
            "type": "date",
            "filterable": True,
            "width": 130,
        },
        {
            "id": "Created By",
            "name": translate_service.translate("column_created_by"),
            "field": "Created By",
            "sortable": True,
            "type": "string",
            "filterable": True,
            "width": 120,
        },
        {
            "id": "_action_rename",
            "name": "✏️",
            "field": "_action_rename",
            "sortable": False,
            "filterable": False,
            "width": 36,
            "resizable": False,
        },
        {
            "id": "_action_delete",
            "name": "🗑️",
            "field": "_action_delete",
            "sortable": False,
            "filterable": False,
            "width": 36,
            "resizable": False,
        },
    ]
    return columns


def render_recipe_table(
    scenarios: list[Scenario], cell_culture_state: CellCultureState
) -> tuple[str, str] | None:
    """Render the cell culture recipe table using SlickGrid and return selected scenario ID."""

    translate_service = cell_culture_state.get_translate_service()

    if not scenarios:
        st.info(translate_service.translate("no_recipe_found"))
        return None

    # Create table data
    table_data = create_recipe_table_data(scenarios, cell_culture_state, translate_service)

    if not table_data:
        st.warning(translate_service.translate("cannot_load_recipe_data"))
        return None

    # Create columns
    columns = create_slickgrid_columns(translate_service)

    # Configure SlickGrid options for row selection
    options = {
        "enableFiltering": True,
        "enableTextExport": True,
        "enableExcelExport": True,
        "enableColumnPicker": True,
        "autoResize": {
            "minHeight": 400,
        },
        "multiColumnSort": False,
        "rowHeight": 28,
    }

    # Use a dynamic key so that refresh forces a full re-initialization of the grid
    refresh_count = st.session_state.get("cell_culture_recipes_refresh", 0)
    grid_key = f"cell_culture_recipes_grid_{refresh_count}"

    # Render the grid with on_click for row selection
    grid_response = slickgrid(
        data=table_data,
        columns=columns,
        options=options,
        key=grid_key,
        on_click="rerun",
    )

    # Handle row selection — map the numeric column index back to a column id string
    # so the caller can distinguish navigation clicks from action-column clicks.
    if grid_response is not None:
        row_id, col_idx = grid_response
        action_col_ids = {"_action_rename", "_action_delete"}
        col_id_by_index = {
            i: col["id"] for i, col in enumerate(columns) if col["id"] in action_col_ids
        }
        clicked_col_id = col_id_by_index.get(col_idx, "navigate")
        return row_id, clicked_col_id

    return None


def rename_recipe_scenarios(
    recipe_id: str,
    new_name: str,
    cell_culture_state: CellCultureState,
) -> None:
    """Rename a recipe: updates the TAG_BIOPROCESS_RECIPE_NAME tag and rebuilds
    the scenario title by replacing only the first part (before " - ").

    :param recipe_id: ID of the load (or comparison) scenario for the recipe
    :param new_name: New recipe name (the part the user typed)
    :param cell_culture_state: The current cell culture state
    """
    new_name_parsed = Tag.parse_tag(new_name.strip())
    recipe_tag = Tag(key=cell_culture_state.TAG_BIOPROCESS_RECIPE_NAME, value=new_name_parsed)
    user_origin = TagOrigin.current_user_origin()

    # Update the scenario title: keep any " - suffix", replace only the first part
    main_scenario = Scenario.get_by_id_and_check(recipe_id)
    current_title = main_scenario.title or ""
    new_title = (
        f"{new_name_parsed} - {current_title.split(' - ', 1)[1]}"
        if " - " in current_title
        else new_name_parsed
    )
    ScenarioService.update_scenario_title(recipe_id, new_title)

    # Update the tag on the main scenario
    main_tags = EntityTagList.find_by_entity(
        TagEntityType.SCENARIO, recipe_id, default_origin=user_origin
    )
    main_tags.replace_tag(recipe_tag)

    # Also update the tag on all related scenarios sharing the same pipeline_id
    pipeline_id_tags = main_tags.get_tags_by_key(cell_culture_state.TAG_BIOPROCESS_PIPELINE_ID)
    pipeline_id = pipeline_id_tags[0].tag_value if pipeline_id_tags else None
    if pipeline_id:
        related = (
            ScenarioSearchBuilder()
            .add_tag_filter(
                Tag(key=cell_culture_state.TAG_BIOPROCESS_PIPELINE_ID, value=pipeline_id)
            )
            .add_is_archived_filter(False)
            .search_all()
        )
        for scenario in related:
            if scenario.id == recipe_id:
                continue
            EntityTagList.find_by_entity(
                TagEntityType.SCENARIO, scenario.id, default_origin=user_origin
            ).replace_tag(recipe_tag)


def delete_recipe_scenarios(
    recipe_id: str,
    cell_culture_state: CellCultureState,
) -> None:
    """Delete all scenarios associated with a recipe.

    :param recipe_id: ID of the load (or comparison) scenario for the recipe
    :param cell_culture_state: The current cell culture state
    """
    entity_tag_list = EntityTagList.find_by_entity(TagEntityType.SCENARIO, recipe_id)
    pipeline_id_tags = entity_tag_list.get_tags_by_key(
        cell_culture_state.TAG_BIOPROCESS_PIPELINE_ID
    )
    pipeline_id = pipeline_id_tags[0].tag_value if pipeline_id_tags else None

    scenarios_to_delete = (
        ScenarioSearchBuilder()
        .add_tag_filter(Tag(key=cell_culture_state.TAG_BIOPROCESS_PIPELINE_ID, value=pipeline_id))
        .add_is_archived_filter(False)
        .search_all()
        if pipeline_id
        else [Scenario.get_by_id_and_check(recipe_id)]
    )

    for scenario in scenarios_to_delete:
        try:
            EntityNavigatorService.delete_scenario(scenario.id)
        except Exception:  # noqa: BLE001
            pass


def display_scenario_task_configs(
    scenario: Scenario, translate_service: StreamlitTranslateService
) -> None:
    """Display configuration parameters of all Task processes in a scenario expander."""
    try:
        scenario_proxy = ScenarioProxy.from_existing_scenario(scenario.id)
        protocol_proxy = scenario_proxy.get_protocol()
        all_processes = protocol_proxy.get_all_processes()

        # Collect configs only for Task-type processes
        task_configs = []
        for instance_name, process_proxy in all_processes.items():
            process_model = process_proxy.get_model()

            # Skip sub-protocols, inputs (Source) and outputs (Sink)
            if isinstance(process_model, ProtocolModel):
                continue
            if process_model.is_input_task() or process_model.is_output_task():
                continue

            config_dto = process_model.config.to_simple_dto()
            config_params = config_dto.values if config_dto else {}
            task_name = process_model.name or instance_name

            if config_params:
                task_configs.append(
                    {
                        "name": task_name,
                        "params": config_params,
                    }
                )

        if task_configs:
            with st.expander(f"⚙️ {translate_service.translate('scenario_configurations')}"):
                for i, task_info in enumerate(task_configs):
                    if i > 0:
                        st.markdown("---")
                    st.markdown(f"**{task_info['name']}**")
                    param_data = []
                    for key, value in task_info["params"].items():
                        readable_key = key.replace("_", " ").replace("-", " ").title()
                        param_data.append(
                            {
                                translate_service.translate("parameter"): readable_key,
                                translate_service.translate("value"): str(value),
                            }
                        )
                    if param_data:
                        param_df = pd.DataFrame(param_data)
                        st.dataframe(param_df, width="stretch", hide_index=True)

    except Exception:
        pass
