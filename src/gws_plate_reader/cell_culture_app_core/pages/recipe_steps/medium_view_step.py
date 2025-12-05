"""
Medium View Step for Cell Culture Dashboard
Displays culture medium composition for each batch-sample pair
"""
import streamlit as st
import pandas as pd
from typing import List, Dict, Any, Optional

from gws_core import Table, Scenario, ScenarioProxy, ScenarioStatus
from gws_core.resource.resource_set.resource_set import ResourceSet
from gws_plate_reader.cell_culture_app_core.cell_culture_state import CellCultureState
from gws_plate_reader.cell_culture_app_core.cell_culture_recipe import CellCultureRecipe


def get_medium_data_from_resource_set(
        resource_set: ResourceSet, cell_culture_state: CellCultureState) -> List[
        Dict[str, Any]]:
    """
    Extract medium composition data from ResourceSet.
    Returns a list of dictionaries with batch, sample, medium name, and composition.
    """
    try:
        resources = resource_set.get_resources()
        medium_data = []

        for resource_name, resource in resources.items():
            if isinstance(resource, Table):
                # Get resource tags
                resource_tags = resource.tags.get_tags()

                batch = None
                sample = None
                medium_name = None
                medium_composition = {}

                # Extract batch, sample, and medium from tags
                for tag in resource_tags:
                    if tag.key == cell_culture_state.TAG_BATCH:
                        batch = tag.value
                    elif tag.key == cell_culture_state.TAG_SAMPLE:
                        sample = tag.value
                    elif tag.key == cell_culture_state.TAG_MEDIUM:
                        medium_name = tag.value
                        # Extract composition from additional_info
                        # Debug: print what we have

                        if hasattr(tag, 'additional_info') and tag.additional_info and 'composed' in tag.additional_info:
                            medium_composition = tag.additional_info['composed']

                # Add to results if we have the required information
                if batch and sample and medium_name:
                    entry = {
                        'Batch': batch,
                        'Sample': sample,
                        'Medium': medium_name
                    }
                    # Add all composition components as separate columns
                    if medium_composition:
                        entry.update(medium_composition)
                    medium_data.append(entry)

        return medium_data
    except Exception as e:
        st.error(f"Error extracting medium data: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return []


def render_medium_view_step(recipe: CellCultureRecipe, cell_culture_state: CellCultureState,
                            scenario: Optional[Scenario] = None, output_name: str = None) -> None:
    """
    Render the medium view step showing medium composition for each batch-sample pair.

    Args:
        recipe: The CellCultureRecipe instance
        cell_culture_state: State manager
        scenario: The scenario to get data from (selection or quality check scenario)
        output_name: Name of the output to retrieve from the scenario
    """
    translate_service = cell_culture_state.get_translate_service()

    try:
        # If scenario is provided, use it
        if scenario:
            target_scenario = scenario
            st.info(f"📊 {translate_service.translate('displaying_data')} : **{target_scenario.title}**")

            if target_scenario.status != ScenarioStatus.SUCCESS:
                st.warning(translate_service.translate('selection_not_successful'))
                return

            # Get data from scenario using the provided output name
            if not output_name:
                # Default to interpolation output for backward compatibility
                output_name = cell_culture_state.INTERPOLATION_SCENARIO_OUTPUT_NAME

            scenario_proxy = ScenarioProxy.from_existing_scenario(target_scenario.id)
            protocol_proxy = scenario_proxy.get_protocol()

            try:
                filtered_resource_set = protocol_proxy.get_output(output_name)
                if not filtered_resource_set:
                    st.error(translate_service.translate('cannot_retrieve_data'))
                    return
            except Exception as e:
                st.error(translate_service.translate('error_retrieving_data').format(error=str(e)))
                return

        # Backward compatibility: if no scenario provided, try to get from load scenario
        else:
            if not recipe.load_scenario:
                st.error(translate_service.translate('no_resourceset_found'))
                return

            target_scenario = recipe.load_scenario
            output_name = cell_culture_state.LOAD_SCENARIO_OUTPUT_NAME

            scenario_proxy = ScenarioProxy.from_existing_scenario(target_scenario.id)
            protocol_proxy = scenario_proxy.get_protocol()

            try:
                filtered_resource_set = protocol_proxy.get_output(output_name)
                if not filtered_resource_set:
                    st.error(translate_service.translate('cannot_retrieve_data'))
                    return
            except Exception as e:
                st.error(translate_service.translate('error_retrieving_data').format(error=str(e)))
                return

        # Check if we have a ResourceSet
        if not isinstance(filtered_resource_set, ResourceSet):
            st.warning(translate_service.translate('no_data_found'))
            return

        # Extract medium data
        medium_data = get_medium_data_from_resource_set(filtered_resource_set, cell_culture_state)

        if not medium_data:
            st.info(translate_service.translate('no_medium_data'))
            return

        # Create DataFrame
        df = pd.DataFrame(medium_data)

        # Sort by Batch and Sample
        df = df.sort_values(['Batch', 'Sample'])

        # Display statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(translate_service.translate('total_samples'), len(df))
        with col2:
            unique_media = df['Medium'].nunique()
            st.metric(translate_service.translate('unique_media'), unique_media)
        with col3:
            composition_cols = [col for col in df.columns if col not in ['Batch', 'Sample', 'Medium']]
            st.metric(translate_service.translate('composition_components'), len(composition_cols))

        st.markdown("---")

        # Display the dataframe
        st.markdown(f"##### {translate_service.translate('experiments_medium_composition')}")

        # Configure column display
        column_config = {
            'Batch': st.column_config.TextColumn(
                translate_service.translate('batch'),
                width='small'
            ),
            'Sample': st.column_config.TextColumn(
                translate_service.translate('sample'),
                width='small'
            ),
            'Medium': st.column_config.TextColumn(
                translate_service.translate('medium'),
                width='medium'
            )
        }

        # Add configuration for composition columns (numeric)
        for col in composition_cols:
            column_config[col] = st.column_config.NumberColumn(
                col,
                format="%.4f",
                width='small'
            )

        st.dataframe(
            df,
            column_config=column_config,
            use_container_width=True,
            hide_index=True
        )

        # Download button
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label=translate_service.translate('download_medium_data'),
            data=csv,
            file_name=f"medium_composition_{target_scenario.id}.csv",
            mime="text/csv",
            icon=":material/download:"
        )

    except Exception as e:
        st.error(f"{translate_service.translate('cannot_retrieve_data')} {str(e)}")
