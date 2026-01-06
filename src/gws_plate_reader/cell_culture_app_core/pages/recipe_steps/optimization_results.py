"""
Optimization Results Page for Cell Culture Dashboard
Displays the results of an Optimization analysis scenario
"""
import streamlit as st
from gws_core import Scenario, ScenarioProxy, ScenarioStatus, Settings

from gws_plate_reader.cell_culture_app_core.cell_culture_state import CellCultureState


def render_optimization_results(cell_culture_state: CellCultureState, optimization_scenario: Scenario) -> None:
    """
    Render the Optimization analysis results page

    :param cell_culture_state: The cell culture state
    :param optimization_scenario: The Optimization scenario to display results for
    """
    translate_service = cell_culture_state.get_translate_service()

    st.markdown("### ⚙️ " + translate_service.translate('optimization_results_title'))

    st.markdown("**" + translate_service.translate('scenario_label') + "** : " + optimization_scenario.title)

    # Display scenario status
    status = optimization_scenario.status
    if status == ScenarioStatus.SUCCESS:
        st.success(translate_service.translate('status_completed_success'))
    elif status == ScenarioStatus.ERROR:
        st.error(f"❌ **{translate_service.translate('status_label')}** : {translate_service.translate('status_error_execution')}")

        # Display error details if available
        try:
            scenario_proxy = ScenarioProxy.from_existing_scenario(optimization_scenario.id)
            protocol_proxy = scenario_proxy.get_protocol()

            # Try to get error from the protocol
            if protocol_proxy:
                st.error("**" + translate_service.translate('error_details_label') + "** :")
                st.code(protocol_proxy.get_error_message() if hasattr(
                    protocol_proxy, 'get_error_message') else translate_service.translate('unknown_error'))
        except Exception as e:
            st.warning(translate_service.translate('unable_retrieve_error_details').format(error=str(e)))

        return
    elif status in (ScenarioStatus.RUNNING, ScenarioStatus.IN_QUEUE):
        st.info(f"⏳ **{translate_service.translate('status_label')}** : {translate_service.translate('analysis_in_progress')}")
        st.markdown(translate_service.translate('analysis_in_progress_refresh'))

        if st.button(f"🔄 {translate_service.translate('refresh')}", key=f"refresh_optimization_{optimization_scenario.id}"):
            st.rerun()

        return
    else:
        st.warning(f"⚠️ **{translate_service.translate('status')}** : {status.name}")
        return

    # Get the Streamlit app resource from scenario output
    try:
        scenario_proxy = ScenarioProxy.from_existing_scenario(optimization_scenario.id)
        protocol_proxy = scenario_proxy.get_protocol()

        streamlit_app_resource_model = protocol_proxy.get_output_resource_model('streamlit_app')

        if not streamlit_app_resource_model:
            st.error(f"⚠️ {translate_service.translate('streamlit_app_resource_unavailable')}")
            return

        # Build the URL to the Streamlit app resource
        front_url = Settings.get_front_url()
        resource_url = f"{front_url}/app/resource/{streamlit_app_resource_model.id}"

        st.markdown("---")
        st.markdown(f"### {translate_service.translate('interactive_dashboard')}")

        st.markdown(translate_service.translate('optimization_dashboard_description'))

        if cell_culture_state.get_is_standalone():
            st.info(translate_service.translate('standalone_mode_function_blocked'))
            return

        # Button to open the Streamlit app
        st.markdown(
            f'<a href="{resource_url}" target="_blank">'
            f'<button style="'
            f'background-color: #FF4B4B; '
            f'color: white; '
            f'padding: 0.5rem 1rem; '
            f'border: none; '
            f'border-radius: 0.25rem; '
            f'cursor: pointer; '
            f'font-size: 1rem; '
            f'font-weight: 600; '
            f'width: 100%;'
            f'">'
            f'{translate_service.translate("open_interactive_dashboard")}'
            f'</button>'
            f'</a>',
            unsafe_allow_html=True
        )

        st.markdown("---")

        # Additional info
        with st.expander(f"ℹ️ {translate_service.translate('results_info_label')}"):
            st.markdown(translate_service.translate('optimization_dashboard_usage_guide'))
    except Exception as e:
        st.error(translate_service.translate('error_retrieving_results').format(error=str(e)))
