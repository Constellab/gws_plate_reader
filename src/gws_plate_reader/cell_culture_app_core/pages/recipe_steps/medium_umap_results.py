"""
Medium UMAP Results Display for Cell Culture Dashboard
Displays the results of a Medium UMAP analysis scenario
"""

import streamlit as st
from gws_core import Scenario, ScenarioProxy, ScenarioStatus, Table
from gws_core.impl.plotly.plotly_resource import PlotlyResource

from gws_plate_reader.cell_culture_app_core.cell_culture_recipe import CellCultureRecipe
from gws_plate_reader.cell_culture_app_core.cell_culture_state import CellCultureState


def render_medium_umap_results(
    recipe: CellCultureRecipe, cell_culture_state: CellCultureState, umap_scenario: Scenario
) -> None:
    """
    Render the Medium UMAP analysis results

    :param recipe: The Recipe instance
    :param cell_culture_state: The cell culture state
    :param umap_scenario: The UMAP scenario to display results for
    """
    translate_service = cell_culture_state.get_translate_service()

    # Info box with UMAP explanation
    with st.expander(f"💡 {translate_service.translate('umap_help_title')}"):
        st.markdown(f"### {translate_service.translate('umap_help_intro_title')}")
        st.markdown(translate_service.translate("umap_help_intro_text"))

        st.markdown(f"\n### {translate_service.translate('umap_help_2d_title')}")
        st.markdown(f"- {translate_service.translate('umap_help_2d_1')}")
        st.markdown(f"- {translate_service.translate('umap_help_2d_2')}")
        st.markdown(f"- {translate_service.translate('umap_help_2d_3')}")

        st.markdown(f"\n### {translate_service.translate('umap_help_3d_title')}")
        st.markdown(f"- {translate_service.translate('umap_help_3d_1')}")
        st.markdown(f"- {translate_service.translate('umap_help_3d_2')}")
        st.markdown(f"- {translate_service.translate('umap_help_3d_3')}")

        st.markdown(f"\n### {translate_service.translate('umap_help_usage_title')}")
        st.markdown(f"- {translate_service.translate('umap_help_usage_1')}")
        st.markdown(f"- {translate_service.translate('umap_help_usage_2')}")
        st.markdown(f"- {translate_service.translate('umap_help_usage_3')}")

    # Check scenario status
    if umap_scenario.status != ScenarioStatus.SUCCESS:
        st.warning(translate_service.translate("umap_analysis_not_finished"))
        return

    # Display UMAP scenario outputs (2D plot, 3D plot, 2D table, 3D table)
    scenario_proxy = ScenarioProxy.from_existing_scenario(umap_scenario.id)
    protocol_proxy = scenario_proxy.get_protocol()

    # Display 2D UMAP plot
    st.markdown(f"### 📊 {translate_service.translate('umap_2d_plot_title')}")
    umap_2d_plot = protocol_proxy.get_output("umap_2d_plot")
    if umap_2d_plot and isinstance(umap_2d_plot, PlotlyResource):
        fig = umap_2d_plot.figure
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning(translate_service.translate("umap_2d_plot_not_found"))

    # Display 3D UMAP plot
    st.markdown(f"### 📈 {translate_service.translate('umap_3d_plot_title')}")
    umap_3d_plot = protocol_proxy.get_output("umap_3d_plot")
    if umap_3d_plot and isinstance(umap_3d_plot, PlotlyResource):
        fig = umap_3d_plot.figure
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning(translate_service.translate("umap_3d_plot_not_found"))

    # Display 2D coordinates table
    st.markdown(f"### 📋 {translate_service.translate('umap_2d_table_title')}")
    umap_2d_table = protocol_proxy.get_output("umap_2d_table")
    if umap_2d_table and isinstance(umap_2d_table, Table):
        df = umap_2d_table.get_data()
        st.dataframe(df, width="stretch", height=400)

        # Download button
        csv = df.to_csv(index=False)
        st.download_button(
            label=translate_service.translate("download_umap_2d_csv"),
            data=csv,
            file_name=f"umap_2d_coordinates_{umap_scenario.id[:8]}.csv",
            mime="text/csv",
        )
    else:
        st.warning(translate_service.translate("umap_2d_table_not_found"))

    # Display 3D coordinates table
    st.markdown(f"### 📋 {translate_service.translate('umap_3d_table_title')}")
    umap_3d_table = protocol_proxy.get_output("umap_3d_table")
    if umap_3d_table and isinstance(umap_3d_table, Table):
        df = umap_3d_table.get_data()
        st.dataframe(df, width="stretch", height=400)

        # Download button
        csv = df.to_csv(index=False)
        st.download_button(
            label=translate_service.translate("download_umap_3d_csv"),
            data=csv,
            file_name=f"umap_3d_coordinates_{umap_scenario.id[:8]}.csv",
            mime="text/csv",
        )
    else:
        st.warning(translate_service.translate("umap_3d_table_not_found"))

