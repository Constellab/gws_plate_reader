import os

from gws_core.streamlit import StreamlitRouter

from gws_plate_reader.cell_culture_app_core.cell_culture_state import CellCultureState
from gws_plate_reader.cell_culture_app_core.pages import (
    first_page,
    new_recipe_page,
    recipe_page,
    settings,
)

sources: list
params: dict

# Get the directory of this file
current_dir = os.path.dirname(__file__)

# Path to gws_plate_reader translation files
lang_translation_folder_path_gws_plate_reader = os.path.join(current_dir, "..")

# Initialize Fermentor state
cell_culture_state = CellCultureState(lang_translation_folder_path_gws_plate_reader)


def display_first_page(cell_culture_state: CellCultureState):
    first_page.render_first_page(cell_culture_state)


def add_first_page(router: StreamlitRouter, cell_culture_state: CellCultureState):
    translate_service = cell_culture_state.get_translate_service()
    router.add_page(
        lambda: display_first_page(cell_culture_state),
        title=translate_service.translate("page_title_analyses"),
        url_path="first-page",
        icon="🧬",
        hide_from_sidebar=False,
    )


def display_new_analysis_page(cell_culture_state: CellCultureState):
    new_recipe_page.render_new_recipe_page(cell_culture_state)


def add_new_analysis_page(router: StreamlitRouter, cell_culture_state: CellCultureState):
    router.add_page(
        lambda: display_new_analysis_page(cell_culture_state),
        title="Nouvelle Analyse",
        url_path="new-analysis",
        icon="➕",
        hide_from_sidebar=True,
    )


def display_analysis_page(cell_culture_state: CellCultureState):
    recipe_page.render_recipe_page(cell_culture_state)


def add_analysis_page(router: StreamlitRouter, cell_culture_state: CellCultureState):
    router.add_page(
        lambda: display_analysis_page(cell_culture_state),
        title="Analyse",
        url_path="analysis",
        icon="📊",
        hide_from_sidebar=True,
    )


def display_settings_page(cell_culture_state: CellCultureState):
    settings.render_settings_page(cell_culture_state)


def add_settings_page(router: StreamlitRouter, cell_culture_state: CellCultureState):
    translate_service = cell_culture_state.get_translate_service()
    router.add_page(
        lambda: display_settings_page(cell_culture_state),
        title=translate_service.translate("page_title_settings"),
        url_path="settings",
        icon=":material/settings:",
        hide_from_sidebar=False,
    )


router = StreamlitRouter.load_from_session()
# Add pages
add_first_page(router, cell_culture_state)
add_new_analysis_page(router, cell_culture_state)
add_analysis_page(router, cell_culture_state)
add_settings_page(router, cell_culture_state)

router.run()
