"""
Visualization Step - Combines Table, Graph and Medium views in tabs
"""

import streamlit as st
from gws_core import Scenario

from gws_plate_reader.cell_culture_app_core.cell_culture_recipe import CellCultureRecipe
from gws_plate_reader.cell_culture_app_core.cell_culture_state import CellCultureState
from gws_plate_reader.cell_culture_app_core.pages.recipe_steps.graph_view_step import (
    render_graph_view_step,
)
from gws_plate_reader.cell_culture_app_core.pages.recipe_steps.medium_view_step import (
    render_medium_view_step,
)
from gws_plate_reader.cell_culture_app_core.pages.recipe_steps.table_view_step import (
    render_table_view_step,
)


def render_visualization_step(
    recipe: CellCultureRecipe,
    cell_culture_state: CellCultureState,
    scenario: Scenario,
    output_name: str,
) -> None:
    """
    Render the visualization step with tabs for Table, Graph and Medium views

    :param recipe: The Recipe instance
    :param cell_culture_state: The cell culture state
    :param scenario: The scenario to visualize
    :param output_name: The output name to display
    """
    translate_service = cell_culture_state.get_translate_service()

    # Create tabs for the three visualization types
    tab1, tab2, tab3 = st.tabs([
        translate_service.translate("table"),
        translate_service.translate("graphs"),
        translate_service.translate("medium")
    ])

    with tab1:
        render_table_view_step(recipe, cell_culture_state, scenario, output_name)

    with tab2:
        render_graph_view_step(recipe, cell_culture_state, scenario, output_name)

    with tab3:
        render_medium_view_step(recipe, cell_culture_state, scenario, output_name)
