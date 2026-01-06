"""
Metadata Feature UMAP Results Display for Cell Culture Dashboard
Displays the results of a Metadata Feature UMAP analysis scenario
"""
import streamlit as st

from gws_core import Scenario, ScenarioStatus, ScenarioProxy, Table
from gws_core.impl.plotly.plotly_resource import PlotlyResource
from gws_plate_reader.cell_culture_app_core.cell_culture_state import CellCultureState
from gws_plate_reader.cell_culture_app_core.cell_culture_recipe import CellCultureRecipe


def render_metadata_feature_umap_results(recipe: CellCultureRecipe, cell_culture_state: CellCultureState,
                                         umap_scenario: Scenario) -> None:
    """
    Render the Metadata Feature UMAP analysis results

    :param recipe: The Recipe instance
    :param cell_culture_state: The cell culture state
    :param umap_scenario: The UMAP scenario to display results for
    """
    translate_service = cell_culture_state.get_translate_service()

    st.title(f"{recipe.name} - {umap_scenario.title}")

    # Check scenario status
    if umap_scenario.status != ScenarioStatus.SUCCESS:
        if umap_scenario.status == ScenarioStatus.ERROR:
            st.error(f"❌ {translate_service.translate('umap_analysis_failed')}")
        elif umap_scenario.is_running:
            st.info(f"⏳ {translate_service.translate('umap_analysis_running')}")
        else:
            st.warning(translate_service.translate('umap_analysis_not_completed').format(
                status=umap_scenario.status.name))
        return

    st.success(translate_service.translate('umap_analysis_complete'))

    # Display UMAP scenario outputs
    scenario_proxy = ScenarioProxy.from_existing_scenario(umap_scenario.id)
    protocol_proxy = scenario_proxy.get_protocol()

    # Display merged table info
    st.markdown("### 📊 " + translate_service.translate('combined_data'))
    merged_table = protocol_proxy.get_output('merged_table')
    if merged_table and isinstance(merged_table, Table):
        merged_df = merged_table.get_data()
        n_rows, n_cols = merged_df.shape
        st.info(translate_service.translate('combined_table_info').format(rows=n_rows, cols=n_cols))

        with st.expander(f"📋 {translate_service.translate('preview_combined_table')}"):
            st.dataframe(merged_df.head(20), width='stretch')

            # Download button
            csv = merged_df.to_csv(index=False)
            st.download_button(
                label=f"💾 {translate_service.translate('download_combined_table_csv')}",
                data=csv,
                file_name=f"metadata_features_merged_{umap_scenario.id[:8]}.csv",
                mime="text/csv"
            )
    else:
        st.warning(translate_service.translate('combined_table_unavailable'))

    st.markdown("---")

    # Display 2D UMAP plot
    st.markdown(f"### 🗺️ {translate_service.translate('umap_2d_plot')}")
    st.markdown(translate_service.translate('visualization_2d_description'))

    umap_2d_plot = protocol_proxy.get_output('umap_2d_plot')
    if umap_2d_plot and isinstance(umap_2d_plot, PlotlyResource):
        fig = umap_2d_plot.figure
        st.plotly_chart(fig, use_container_width=True)

        st.markdown(f"""
        **{translate_service.translate('pls_train_interpretation').split(':')[0]}** :
        - {translate_service.translate('umap_help_plot_point')}
        - {translate_service.translate('umap_help_plot_color')}
        - {translate_service.translate('umap_help_plot_proximity')}
        - {translate_service.translate('umap_help_plot_groups')}
        """)
    else:
        st.warning(f"⚠️ {translate_service.translate('umap_2d_plot_not_found')}")

    st.markdown("---")

    # Display 3D UMAP plot
    st.markdown(f"### 🎲 {translate_service.translate('umap_3d_projection')}")
    st.markdown(translate_service.translate('3d_visualization_description'))

    umap_3d_plot = protocol_proxy.get_output('umap_3d_plot')
    if umap_3d_plot and isinstance(umap_3d_plot, PlotlyResource):
        fig = umap_3d_plot.figure
        st.plotly_chart(fig, use_container_width=True)

        st.markdown(f"""
        **{translate_service.translate('usage_tips')}** :
        - {translate_service.translate('rotate_graph_tip')}
        - {translate_service.translate('zoom_specific_areas')}
        - {translate_service.translate('compare_2d_3d')}
        """)
    else:
        st.warning(f"⚠️ {translate_service.translate('umap_3d_plot_not_found')}")

    st.markdown("---")

    # Display 2D coordinates table
    st.markdown(f"### 📊 {translate_service.translate('umap_2d_coordinates_title')}")
    umap_2d_table = protocol_proxy.get_output('umap_2d_table')
    if umap_2d_table and isinstance(umap_2d_table, Table):
        df_2d = umap_2d_table.get_data()

        col1, col2 = st.columns([2, 1])
        with col1:
            st.dataframe(df_2d, width='stretch', height=400)
        with col2:
            st.metric(translate_service.translate('number_of_series_label'), len(df_2d))
            st.metric(translate_service.translate('columns_label'), len(df_2d.columns))

            # Show column names
            st.caption(f"**{translate_service.translate('available_columns_caption')}**")
            for col in df_2d.columns:
                st.caption(f"- {col}")

        # Download button
        csv = df_2d.to_csv(index=False)
        st.download_button(
            label=f"💾 {translate_service.translate('download_2d_coordinates_csv')}",
            data=csv,
            file_name=f"umap_2d_coordinates_{umap_scenario.id[:8]}.csv",
            mime="text/csv"
        )
    else:
        st.warning(f"⚠️ {translate_service.translate('coordinates_2d_table_unavailable')}")

    st.markdown("---")

    # Display 3D coordinates table
    st.markdown(f"### 📊 {translate_service.translate('umap_3d_coordinates_title')}")
    umap_3d_table = protocol_proxy.get_output('umap_3d_table')
    if umap_3d_table and isinstance(umap_3d_table, Table):
        df_3d = umap_3d_table.get_data()

        col1, col2 = st.columns([2, 1])
        with col1:
            st.dataframe(df_3d, width='stretch', height=400)
        with col2:
            st.metric(translate_service.translate('number_of_series_label'), len(df_3d))
            st.metric(translate_service.translate('columns_label'), len(df_3d.columns))

            # Show column names
            st.caption(f"**{translate_service.translate('available_columns_caption')}**")
            for col in df_3d.columns:
                st.caption(f"- {col}")

        # Download button
        csv = df_3d.to_csv(index=False)
        st.download_button(
            label=f"💾 {translate_service.translate('download_3d_coordinates_csv')}",
            data=csv,
            file_name=f"umap_3d_coordinates_{umap_scenario.id[:8]}.csv",
            mime="text/csv"
        )
    else:
        st.warning(f"⚠️ {translate_service.translate('coordinates_3d_table_unavailable')}")

    # Info box with interpretation guide
    with st.expander(f"💡 {translate_service.translate('detailed_interpretation_guide')}"):
        st.markdown(f"### {translate_service.translate('understanding_umap_results_title')}")

        st.markdown(f"""
        #### {translate_service.translate('what_does_analysis_show')}

        {translate_service.translate('umap_combines_two_types')}

        1. {translate_service.translate('metadata_composition')}
           {translate_service.translate('metadata_nutrients')}
           {translate_service.translate('metadata_formulation')}
           {translate_service.translate('metadata_initial')}

        2. {translate_service.translate('features_performance')}
           {translate_service.translate('features_growth')}
           {translate_service.translate('features_metrics')}
           {translate_service.translate('features_intervals')}
           {translate_service.translate('features_times')}

        {translate_service.translate('umap_reveals_link')}

        #### {translate_service.translate('patterns_to_look_for')}

        {translate_service.translate('clusters_similar_media')}
        {translate_service.translate('same_color_grouped')}
        {translate_service.translate('different_colors_grouped')}

        {translate_service.translate('isolated_series')}
        {translate_service.translate('points_far_away')}
        {translate_service.translate('may_indicate')}

        {translate_service.translate('gradients')}
        {translate_service.translate('progressive_transition')}
        {translate_service.translate('useful_identify')}

        {translate_service.translate('global_shape')}
        {translate_service.translate('branching_structure')}
        {translate_service.translate('cloud_structure')}
        {translate_service.translate('distinct_clusters')}

        #### {translate_service.translate('practical_applications')}

        {translate_service.translate('medium_optimization')}
        {translate_service.translate('identify_best_media')}
        {translate_service.translate('find_common_characteristics')}
        {translate_service.translate('formulate_new_media')}

        {translate_service.translate('cost_reduction')}
        {translate_service.translate('look_close_points')}
        {translate_service.translate('test_cheaper_ingredients')}

        {translate_service.translate('quality_control')}
        {translate_service.translate('new_batches_same_region')}
        {translate_service.translate('deviations_reveal')}

        {translate_service.translate('experiment_design')}
        {translate_service.translate('unexplored_areas')}
        {translate_service.translate('plan_new_tests')}

        #### {translate_service.translate('limitations_precautions')}

        {translate_service.translate('umap_preserves_local')}
        {translate_service.translate('normalization_crucial')}
        {translate_service.translate('multiple_projections')}
        {translate_service.translate('always_validate')}

        #### {translate_service.translate('export_further_analysis')}

        {translate_service.translate('use_coordinate_tables')}
        {translate_service.translate('statistically_analyze')}
        {translate_service.translate('correlate_other_variables')}
        {translate_service.translate('create_predictive_models')}
        {translate_service.translate('communicate_results')}
        """)

        st.markdown("---")

        st.markdown(f"### {translate_service.translate('umap_parameters_used')}")
        st.markdown(f"""
        {translate_service.translate('umap_parameters_influence')}

        {translate_service.translate('n_neighbors_structure')}
        {translate_service.translate('min_dist_dispersion')}
        {translate_service.translate('metric_distance')}
        {translate_service.translate('scale_data_normalization')}

        {translate_service.translate('unsatisfactory_results')}
        """)
