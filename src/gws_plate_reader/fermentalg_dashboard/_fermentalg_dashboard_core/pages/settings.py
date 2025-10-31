import streamlit as st
from gws_core.streamlit import StreamlitContainers, StreamlitTranslateLang
from gws_plate_reader.fermentalg_dashboard._fermentalg_dashboard_core.fermentalg_state import FermentalgState


def render_settings_page(fermentalg_state: FermentalgState):
    """
    Render the settings page for Fermentalg dashboard.
    Includes language settings and information about interpolation methods.
    """
    style = """
    [CLASS_NAME] {
        padding: 40px;
    }
    """

    with StreamlitContainers.container_full_min_height('container-center_settings_page',
                                                       additional_style=style):

        translate_service = fermentalg_state.get_translate_service()

        st.title(f"⚙️ {translate_service.translate('settings_title')}")

        st.markdown("---")

        # Section 1: General Settings - Language
        st.subheader(f"🌐 {translate_service.translate('general_settings')}")

        # Get current language from translate service
        current_lang = translate_service.get_lang()

        # Map enum to display strings and indices
        lang_options = ["English", "Français"]
        lang_enum_map = {
            "English": StreamlitTranslateLang.EN,
            "Français": StreamlitTranslateLang.FR
        }

        # Convert current enum to index
        if current_lang == StreamlitTranslateLang.EN:
            current_index = 0
        elif current_lang == StreamlitTranslateLang.FR:
            current_index = 1
        else:
            current_index = 1  # Default to French

        selected_lang_str = st.selectbox(
            translate_service.translate("select_language"),
            options=lang_options,
            index=current_index,
            key=fermentalg_state.LANG_KEY
        )

        # Convert selected string back to enum
        selected_lang_enum = lang_enum_map[selected_lang_str]

        # Check if language actually changed
        if current_lang != selected_lang_enum:
            # Change the language in the translate service
            translate_service.change_lang(selected_lang_enum)
            # Update the state
            fermentalg_state.set_translate_service(translate_service)
            st.rerun()

        st.markdown("---")

        # Section 2: Interpolation Preferences
        st.subheader(f"📈 {translate_service.translate('interpolation_settings')}")

        st.info(translate_service.translate('interpolation_description'))

        with st.expander(f"📋 {translate_service.translate('available_methods')}", expanded=False):
            st.markdown(f"""
            - **Linear**: {translate_service.translate('method_linear')}
            - **Nearest**: {translate_service.translate('method_nearest')}
            - **Quadratic**: {translate_service.translate('method_quadratic')}
            - **Cubic**: {translate_service.translate('method_cubic')}
            - **PCHIP**: {translate_service.translate('method_pchip')}
            - **Akima**: {translate_service.translate('method_akima')}
            - **Cubic Spline**: {translate_service.translate('method_cubic_spline')}
            - **Univariate Spline**: {translate_service.translate('method_univariate_spline')}
            - **Spline**: {translate_service.translate('method_spline')}
            """)

        st.markdown("---")

        # Section 3: About
        st.subheader(f"ℹ️ {translate_service.translate('about')}")

        st.markdown(translate_service.translate('dashboard_description'))

        st.markdown(f"**{translate_service.translate('features_title')}:**")
        st.markdown(f"""
        - 📤 {translate_service.translate('feature_upload')}
        - ⚙️ {translate_service.translate('feature_processing')}
        - ✅ {translate_service.translate('feature_quality')}
        - 🎯 {translate_service.translate('feature_selection')}
        - � {translate_service.translate('feature_visualization')}
        - � {translate_service.translate('feature_statistics')}
        - � {translate_service.translate('feature_comparison')}
        """)
