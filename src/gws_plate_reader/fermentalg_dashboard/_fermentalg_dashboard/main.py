import streamlit as st

from gws_plate_reader.fermentalg_dashboard._fermentalg_dashboard_core.fermentalg_state import FermentalgState
from gws_plate_reader.fermentalg_dashboard._fermentalg_dashboard_core.pages import first_page, new_recipe_page, recipe_page, settings
from gws_core.streamlit import StreamlitRouter

sources: list
params: dict

# Initialize Fermentalg state
fermentalg_state = FermentalgState()


def display_first_page(fermentalg_state: FermentalgState):
    first_page.render_first_page(fermentalg_state)


def add_first_page(router: StreamlitRouter, fermentalg_state: FermentalgState):
    router.add_page(
        lambda: display_first_page(fermentalg_state),
        title='Analyses Fermentalg',
        url_path='first-page',
        icon='🧬',
        hide_from_sidebar=False
    )


def display_new_analysis_page(fermentalg_state: FermentalgState):
    new_recipe_page.render_new_recipe_page(fermentalg_state)


def add_new_analysis_page(router: StreamlitRouter, fermentalg_state: FermentalgState):
    router.add_page(
        lambda: display_new_analysis_page(fermentalg_state),
        title='Nouvelle Analyse',
        url_path='new-analysis',
        icon='➕',
        hide_from_sidebar=True
    )


def display_analysis_page(fermentalg_state: FermentalgState):
    recipe_page.render_recipe_page(fermentalg_state)


def add_analysis_page(router: StreamlitRouter, fermentalg_state: FermentalgState):
    router.add_page(
        lambda: display_analysis_page(fermentalg_state),
        title='Analyse',
        url_path='analysis',
        icon='📊',
        hide_from_sidebar=True
    )


def display_settings_page(fermentalg_state: FermentalgState):
    settings.render_settings_page(fermentalg_state)


def add_settings_page(router: StreamlitRouter, fermentalg_state: FermentalgState):
    router.add_page(
        lambda: display_settings_page(fermentalg_state),
        title='Paramètres',
        url_path='settings',
        icon=':material/settings:',
        hide_from_sidebar=False
    )


router = StreamlitRouter.load_from_session()
# Add pages
add_first_page(router, fermentalg_state)
add_new_analysis_page(router, fermentalg_state)
add_analysis_page(router, fermentalg_state)
add_settings_page(router, fermentalg_state)

router.run()
