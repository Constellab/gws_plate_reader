import os

from gws_core.streamlit import StreamlitRouter

import gws_plate_reader
from gws_plate_reader.biolector_cell_culture_dashboard._biolector_cell_culture_dashboard_core.biolector_state import (
    BiolectorState,
)
from gws_plate_reader.biolector_cell_culture_dashboard._biolector_cell_culture_dashboard_core.pages import (
    new_recipe_page,
)
from gws_plate_reader.cell_culture_app_core.pages import first_page, recipe_page, settings

sources: list
params: dict

# Get the directory of this file
current_dir = os.path.dirname(__file__)
# Path to gws_plate_reader translation files
gws_plate_reader_file = gws_plate_reader.__file__
if gws_plate_reader_file is None:
    raise ValueError("gws_plate_reader.__file__ is None")
lang_translation_folder_path_gws_plate_reader = os.path.join(os.path.dirname(gws_plate_reader_file), 'cell_culture_app_core')

core_dir = os.path.join(current_dir, '..', '_biolector_cell_culture_dashboard_core')
lang_translation_folder_path = os.path.abspath(core_dir)

# Initialize BiolectorXT state
biolector_state = BiolectorState(lang_translation_folder_path_gws_plate_reader, lang_translation_folder_path)


def display_first_page(biolector_state: BiolectorState):
    first_page.render_first_page(biolector_state)


def add_first_page(router: StreamlitRouter, biolector_state: BiolectorState):
    translate_service = biolector_state.get_translate_service()
    router.add_page(
        lambda: display_first_page(biolector_state),
        title=translate_service.translate('page_title_analyses'),
        url_path='first-page',
        icon='🧬',
        hide_from_sidebar=False
    )


def display_new_analysis_page(biolector_state: BiolectorState):
    new_recipe_page.render_new_recipe_page(biolector_state)


def add_new_analysis_page(router: StreamlitRouter, biolector_state: BiolectorState):
    router.add_page(
        lambda: display_new_analysis_page(biolector_state),
        title='New Analysis',
        url_path='new-analysis',
        icon='➕',
        hide_from_sidebar=True
    )


def display_analysis_page(biolector_state: BiolectorState):
    recipe_page.render_recipe_page(biolector_state)


def add_analysis_page(router: StreamlitRouter, biolector_state: BiolectorState):
    router.add_page(
        lambda: display_analysis_page(biolector_state),
        title='Analysis',
        url_path='analysis',
        icon='📊',
        hide_from_sidebar=True
    )


def display_settings_page(biolector_state: BiolectorState):
    settings.render_settings_page(biolector_state)


def add_settings_page(router: StreamlitRouter, biolector_state: BiolectorState):
    translate_service = biolector_state.get_translate_service()
    router.add_page(
        lambda: display_settings_page(biolector_state),
        title=translate_service.translate('page_title_settings'),
        url_path='settings',
        icon=':material/settings:',
        hide_from_sidebar=False
    )


router = StreamlitRouter.load_from_session()
# Add pages
add_first_page(router, biolector_state)
add_new_analysis_page(router, biolector_state)
add_analysis_page(router, biolector_state)
add_settings_page(router, biolector_state)

router.run()
