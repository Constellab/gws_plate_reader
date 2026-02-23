"""
Causal Effect Results Display Page
"""

import traceback

import streamlit as st
from gws_core import Scenario, ScenarioProxy, ScenarioStatus
from gws_core.core.utils.settings import Settings
from gws_plate_reader.cell_culture_app_core._constellab_bioprocess_core.cell_culture_recipe import (
    CellCultureRecipe,
)
from gws_plate_reader.cell_culture_app_core._constellab_bioprocess_core.cell_culture_state import (
    CellCultureState,
)


def render_causal_effect_results(
    recipe: CellCultureRecipe, cell_culture_state: CellCultureState, causal_scenario: Scenario
) -> None:
    """
    Render the Causal Effect results page

    :param recipe: The Recipe instance
    :param cell_culture_state: The cell culture state
    :param causal_scenario: The Causal Effect scenario to display
    """
    translate_service = cell_culture_state.get_translate_service()

    # Display scenario status
    if causal_scenario.status == ScenarioStatus.SUCCESS:
        pass
    elif causal_scenario.status == ScenarioStatus.ERROR:
        st.error(f"❌ {translate_service.translate('analysis_failed')}")
        # Display error message if available
        if causal_scenario.error_info:
            with st.expander(f"{translate_service.translate('error_details_expander')}"):
                st.code(
                    causal_scenario.error_info.get("message", translate_service.translate("no_error_message_available"))
                )
            st.markdown("")
        return
    elif causal_scenario.is_running:
        st.info(f"⏳ {translate_service.translate('analysis_in_progress')}")
        st.markdown(translate_service.translate("refresh_page_for_results"))
        return
    else:
        st.warning(f"⚠️ {translate_service.translate('status_label')}: {causal_scenario.status.name}")
        return

    # If analysis is successful, get the Streamlit app resource
    try:
        causal_scenario_proxy = ScenarioProxy.from_existing_scenario(causal_scenario.id)
        causal_protocol_proxy = causal_scenario_proxy.get_protocol()

        # Get the streamlit_app output resource model
        streamlit_app_resource_model = causal_protocol_proxy.get_output_resource_model(
            "streamlit_app"
        )

        if not streamlit_app_resource_model:
            st.error(f"⚠️ {translate_service.translate('streamlit_app_resource_unavailable')}")
            return

        # Build the URL to the Streamlit app resource
        front_url = Settings.get_front_url()
        resource_url = f"{front_url}/app/resource/{streamlit_app_resource_model.id}"

        st.markdown("---")
        st.markdown(f"### {translate_service.translate('causal_effect_dashboard_title')}")

        st.markdown(translate_service.translate("causal_effect_dashboard_description"))

        if cell_culture_state.get_is_standalone():
            st.info(translate_service.translate("standalone_mode_function_blocked"))
            return

        # Button to open the Streamlit app
        st.markdown(
            f'<a href="{resource_url}" target="_blank">'
            f'<button style="'
            f"background-color: #FF4B4B; "
            f"color: white; "
            f"padding: 0.5rem 1rem; "
            f"border: none; "
            f"border-radius: 0.25rem; "
            f"cursor: pointer; "
            f"font-size: 1rem; "
            f"font-weight: 600; "
            f"width: 100%;"
            f'">'
            f"{translate_service.translate('open_interactive_dashboard')}"
            f"</button>"
            f"</a>",
            unsafe_allow_html=True,
        )

        st.markdown("---")

        # Additional info
        with st.expander(f"{translate_service.translate('results_info_label')}"):
            st.markdown(f"""
            {translate_service.translate("causal_effect_usage_guide")}
                        """)
        st.markdown("")

    except Exception as e:
        st.error(translate_service.translate("error_retrieving_results").format(error=str(e)))
        st.code(traceback.format_exc())
