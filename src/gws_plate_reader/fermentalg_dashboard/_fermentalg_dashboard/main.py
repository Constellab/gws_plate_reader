import streamlit as st

from gws_plate_reader.fermentalg_dashboard._fermentalg_dashboard_core.state import State
from gws_plate_reader.fermentalg_dashboard._fermentalg_dashboard_core.pages import first_page, new_analysis_page, analysis_page, settings
from gws_core.streamlit import StreamlitRouter

sources: list
params: dict

# Initialize Fermentalg state
fermentalg_state = State()


def display_first_page(fermentalg_state: State):
    first_page.render_first_page(fermentalg_state)


def add_first_page(router: StreamlitRouter, fermentalg_state: State):
    router.add_page(
        lambda: display_first_page(fermentalg_state),
        title='Analyses Fermentalg',
        url_path='first-page',
        icon='🧬',
        hide_from_sidebar=False
    )


def display_new_analysis_page(fermentalg_state: State):
    new_analysis_page.render_new_analysis_page(fermentalg_state)


def add_new_analysis_page(router: StreamlitRouter, fermentalg_state: State):
    router.add_page(
        lambda: display_new_analysis_page(fermentalg_state),
        title='Nouvelle Analyse',
        url_path='new-analysis',
        icon='➕',
        hide_from_sidebar=True
    )


def display_analysis_page(fermentalg_state: State):
    analysis_page.render_analysis_page(fermentalg_state)


def add_analysis_page(router: StreamlitRouter, fermentalg_state: State):
    router.add_page(
        lambda: display_analysis_page(fermentalg_state),
        title='Analyse',
        url_path='analysis',
        icon='📊',
        hide_from_sidebar=True
    )


def display_settings_page(fermentalg_state: State):
    settings.render_settings_page(fermentalg_state)


def add_settings_page(router: StreamlitRouter, fermentalg_state: State):
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
