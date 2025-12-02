import streamlit as st
import os

from gws_plate_reader.greencell_fermentor_dashboard._greencell_fermentor_dashboard_core.greencell_fermentor_state import GreencellFermentorState
from gws_plate_reader.greencell_fermentor_dashboard._greencell_fermentor_dashboard_core.pages import new_recipe_page
from gws_plate_reader.cell_culture_app_core.pages import first_page, recipe_page, settings
from gws_core.streamlit import StreamlitRouter

sources: list
params: dict

# Get the directory of this file
current_dir = os.path.dirname(__file__)
# Get the parent directory (_greencell_fermentor_dashboard_core)
core_dir = os.path.join(current_dir, '..', '_greencell_fermentor_dashboard_core')
# Build absolute path to translation folder
lang_translation_folder_path = os.path.abspath(core_dir)

# Initialize Greencell Fermentor state
greencell_state = GreencellFermentorState(lang_translation_folder_path)


def display_first_page(greencell_state: GreencellFermentorState):
    first_page.render_first_page(greencell_state)


def add_first_page(router: StreamlitRouter, greencell_state: GreencellFermentorState):
    router.add_page(
        lambda: display_first_page(greencell_state),
        title='Analyses Greencell Fermentor',
        url_path='first-page',
        icon='🧬',
        hide_from_sidebar=False
    )


def display_new_analysis_page(greencell_state: GreencellFermentorState):
    new_recipe_page.render_new_recipe_page(greencell_state)


def add_new_analysis_page(router: StreamlitRouter, greencell_state: GreencellFermentorState):
    router.add_page(
        lambda: display_new_analysis_page(greencell_state),
        title='Nouvelle Analyse',
        url_path='new-analysis',
        icon='➕',
        hide_from_sidebar=True
    )


def display_analysis_page(greencell_state: GreencellFermentorState):
    recipe_page.render_recipe_page(greencell_state)


def add_analysis_page(router: StreamlitRouter, greencell_state: GreencellFermentorState):
    router.add_page(
        lambda: display_analysis_page(greencell_state),
        title='Analyse',
        url_path='analysis',
        icon='📊',
        hide_from_sidebar=True
    )


def display_settings_page(greencell_state: GreencellFermentorState):
    settings.render_settings_page(greencell_state)


def add_settings_page(router: StreamlitRouter, greencell_state: GreencellFermentorState):
    router.add_page(
        lambda: display_settings_page(greencell_state),
        title='Paramètres',
        url_path='settings',
        icon=':material/settings:',
        hide_from_sidebar=False
    )


router = StreamlitRouter.load_from_session()
# Add pages
add_first_page(router, greencell_state)
add_new_analysis_page(router, greencell_state)
add_analysis_page(router, greencell_state)
add_settings_page(router, greencell_state)

router.run()
