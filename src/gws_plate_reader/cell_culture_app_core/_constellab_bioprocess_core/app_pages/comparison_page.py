"""
Biolector / Fermentor Comparison Page
Allows users to select existing Biolector and Fermentor results and visualise
their time-series curves on the same plots. Comparison recipes can be saved
as persistent objects and listed on the home page.
"""

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from gws_core import Scenario, ScenarioSearchBuilder, Table, Tag
from gws_core.resource.resource_set.resource_set import ResourceSet
from gws_core.scenario.scenario_proxy import ScenarioProxy
from gws_core.tag.entity_tag_list import EntityTagList
from gws_core.tag.tag_entity_type import TagEntityType
from gws_plate_reader.cell_culture_app_core._constellab_bioprocess_core.cell_culture_state import (
    CellCultureState,
)

# Source labels injected into combined DataFrame
_SOURCE_BIOLECTOR = "Biolector"
_SOURCE_FERMENTOR = "Fermentor"

# ─────────────────────────────────────────────
# Tags for saved comparison recipes
# ─────────────────────────────────────────────
TAG_BIOPROCESS_COMPARISON = "comparison"  # value for TAG_BIOPROCESS
TAG_COMPARISON_BIO_QC_ID = "comparison_bio_qc_id"
TAG_COMPARISON_FERM_QC_ID = "comparison_ferm_qc_id"


# ─────────────────────────────────────────────
# Helper: recipe discovery
# ─────────────────────────────────────────────


def _get_data_processing_scenarios(cell_culture_state: CellCultureState) -> list[Scenario]:
    """Return all non-archived data_processing scenarios."""
    return (
        ScenarioSearchBuilder()
        .add_tag_filter(
            Tag(
                key=cell_culture_state.TAG_BIOPROCESS,
                value=cell_culture_state.TAG_DATA_PROCESSING,
            )
        )
        .add_is_archived_filter(False)
        .search_all()
    )


def _is_biolector(scenario: Scenario, cell_culture_state: CellCultureState) -> bool:
    """Return True if the data_processing scenario belongs to a Biolector recipe."""
    tags = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)
    microplate_tags = tags.get_tags_by_key(cell_culture_state.TAG_MICROPLATE_ANALYSIS)
    return bool(microplate_tags and microplate_tags[0].tag_value.lower() == "true")


def _get_recipe_name(scenario: Scenario, cell_culture_state: CellCultureState) -> str:
    """Extract the human-readable recipe name from a load scenario."""
    tags = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)
    recipe_name_tags = tags.get_tags_by_key(cell_culture_state.TAG_BIOPROCESS_RECIPE_NAME)
    return recipe_name_tags[0].tag_value if recipe_name_tags else scenario.title


def _get_pipeline_id(scenario: Scenario, cell_culture_state: CellCultureState) -> str | None:
    """Extract the pipeline_id from a scenario."""
    tags = EntityTagList.find_by_entity(TagEntityType.SCENARIO, scenario.id)
    pipeline_id_tags = tags.get_tags_by_key(cell_culture_state.TAG_BIOPROCESS_PIPELINE_ID)
    return pipeline_id_tags[0].tag_value if pipeline_id_tags else None


def _get_qc_scenarios_for_pipeline(
    pipeline_id: str, cell_culture_state: CellCultureState
) -> list[Scenario]:
    """Return all successful quality_check_processing scenarios for a given pipeline_id."""
    all_qc = (
        ScenarioSearchBuilder()
        .add_tag_filter(
            Tag(
                key=cell_culture_state.TAG_BIOPROCESS,
                value=cell_culture_state.TAG_QUALITY_CHECK_PROCESSING,
            )
        )
        .add_is_archived_filter(False)
        .search_all()
    )

    result = []
    for sc in all_qc:
        sc_pipeline_id = _get_pipeline_id(sc, cell_culture_state)
        if sc_pipeline_id == pipeline_id:
            result.append(sc)

    result.sort(key=lambda s: s.created_at or s.last_modified_at, reverse=False)
    return result


# ─────────────────────────────────────────────
# Helper: data extraction
# ─────────────────────────────────────────────


def _build_data_rows(
    resource_set: ResourceSet,
    cell_culture_state: CellCultureState,
    source_label: str,
    recipe_name: str,
) -> list[dict[str, Any]]:
    """
    Extract all rows from a ResourceSet and tag them with Source and RecipeName.

    Each row contains:
    - All original data columns
    - Batch, Sample, Medium (from resource tags)
    - Source: 'Biolector' or 'Fermentor'
    - RecipeName: human-readable name of the parent recipe
    """
    rows: list[dict[str, Any]] = []
    resources = resource_set.get_resources()

    for resource_name, resource in resources.items():
        if not isinstance(resource, Table):
            continue

        batch = ""
        sample = ""
        medium = ""

        if hasattr(resource, "tags") and resource.tags:
            for tag in resource.tags.get_tags():
                if tag.key == cell_culture_state.TAG_BATCH:
                    batch = tag.value
                elif tag.key == cell_culture_state.TAG_SAMPLE:
                    sample = tag.value
                elif tag.key == cell_culture_state.TAG_MEDIUM:
                    medium = tag.value

        df = resource.get_data()
        for _, row in df.iterrows():
            row_dict = row.to_dict()
            row_dict["Batch"] = batch
            row_dict["Sample"] = sample
            row_dict["Medium"] = medium
            row_dict["Source"] = source_label
            row_dict["RecipeName"] = recipe_name
            row_dict["Resource_Name"] = resource_name
            rows.append(row_dict)

    return rows


def _get_resource_set_from_qc(
    qc_scenario: Scenario, cell_culture_state: CellCultureState
) -> ResourceSet | None:
    """Load the interpolated ResourceSet output from a QC scenario."""
    try:
        proxy = ScenarioProxy.from_existing_scenario(qc_scenario.id)
        protocol_proxy = proxy.get_protocol()
        return protocol_proxy.get_output(
            cell_culture_state.QUALITY_CHECK_SCENARIO_INTERPOLATED_OUTPUT_NAME
        )
    except Exception:
        return None


def _find_load_scenario_for_qc(
    qc_scenario_id: str, cell_culture_state: CellCultureState
) -> "Scenario | None":
    """Find the data_processing scenario whose pipeline_id matches the QC scenario."""
    qc_tags = EntityTagList.find_by_entity(TagEntityType.SCENARIO, qc_scenario_id)
    qc_pipeline_id_tags = qc_tags.get_tags_by_key(cell_culture_state.TAG_BIOPROCESS_PIPELINE_ID)
    if not qc_pipeline_id_tags:
        return None
    qc_pipeline_id = qc_pipeline_id_tags[0].tag_value

    for sc in _get_data_processing_scenarios(cell_culture_state):
        if _get_pipeline_id(sc, cell_culture_state) == qc_pipeline_id:
            return sc
    return None


def _get_index_and_data_columns(
    resource_set: ResourceSet,
) -> tuple[list[str], list[str]]:
    """
    Return (index_columns, data_columns) from a ResourceSet.

    index_columns: columns tagged is_index_column=true
    data_columns:  columns tagged is_data_column=true
    """
    index_cols: list[str] = []
    data_cols: list[str] = []

    resources = resource_set.get_resources()
    for resource in resources.values():
        if not isinstance(resource, Table):
            continue
        for col_name in resource.get_column_names():
            col_tags = resource.get_column_tags_by_name(col_name)
            if col_tags.get("is_index_column") == "true":
                if col_name not in index_cols:
                    index_cols.append(col_name)
            elif col_tags.get("is_data_column") == "true":
                if col_name not in data_cols:
                    data_cols.append(col_name)

    return sorted(index_cols), sorted(data_cols)


# ─────────────────────────────────────────────
# Plotting
# ─────────────────────────────────────────────

_BIOLECTOR_COLORS = [
    "#1f77b4",
    "#aec7e8",
    "#2ca02c",
    "#98df8a",
    "#9467bd",
    "#c5b0d5",
    "#17becf",
    "#9edae5",
]
_FERMENTOR_COLORS = [
    "#d62728",
    "#ff9896",
    "#ff7f0e",
    "#ffbb78",
    "#8c564b",
    "#c49c94",
    "#e377c2",
    "#f7b6d2",
]


_AXIS_COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]


def _render_comparison_plot(
    df_all: pd.DataFrame,
    selected_bio_index: str,
    selected_ferm_index: str,
    selected_bio_cols: list[str],
    selected_ferm_cols: list[str],
    selected_bio_batches: list[str],
    selected_bio_samples: list[str],
    selected_ferm_batches: list[str],
    selected_ferm_samples: list[str],
    translate_service: Any,
) -> None:
    """Render the Plotly comparison figure with up to 4 y-axes (one per unique column name)."""

    # Build ordered list of unique column names; bio and ferm sharing the same
    # column name will share the same y-axis.
    all_unique_cols = list(dict.fromkeys(selected_bio_cols + selected_ferm_cols))
    col_to_axis_idx = {col: idx for idx, col in enumerate(all_unique_cols)}
    num_axes = len(all_unique_cols)

    # Track which source(s) each column belongs to (for y-axis titles)
    col_sources: dict[str, list[str]] = {}
    for col in selected_bio_cols:
        col_sources.setdefault(col, []).append(_SOURCE_BIOLECTOR)
    for col in selected_ferm_cols:
        if _SOURCE_FERMENTOR not in col_sources.get(col, []):
            col_sources.setdefault(col, []).append(_SOURCE_FERMENTOR)

    bio_df = df_all[df_all["Source"] == _SOURCE_BIOLECTOR].copy()
    ferm_df = df_all[df_all["Source"] == _SOURCE_FERMENTOR].copy()

    fig = go.Figure()

    # ── Biolector traces ─────────────────────────────────
    for bio_col in selected_bio_cols:
        axis_idx = col_to_axis_idx[bio_col]
        yaxis_ref = "y" if axis_idx == 0 else f"y{axis_idx + 1}"

        bio_filtered = bio_df[
            (bio_df["Batch"].isin(selected_bio_batches))
            & (bio_df["Sample"].isin(selected_bio_samples))
            & (bio_df[selected_bio_index].notna())
            & (bio_df[bio_col].notna())
        ]
        bio_pairs = bio_filtered[["Batch", "Sample"]].drop_duplicates().values.tolist()
        for idx_pair, (batch, sample) in enumerate(bio_pairs):
            mask = (bio_filtered["Batch"] == batch) & (bio_filtered["Sample"] == sample)
            subset = bio_filtered[mask].sort_values(selected_bio_index)
            if subset.empty:
                continue
            color = _BIOLECTOR_COLORS[idx_pair % len(_BIOLECTOR_COLORS)]
            trace_name = f"[BIO] {batch} - {sample}"
            if num_axes > 1:
                trace_name += f" ({bio_col})"
            fig.add_trace(
                go.Scatter(
                    x=subset[selected_bio_index],
                    y=subset[bio_col],
                    mode="lines+markers",
                    name=trace_name,
                    line={"color": color, "width": 2, "shape": "spline"},
                    marker={"size": 5, "symbol": "circle", "color": color},
                    legendgroup=f"{_SOURCE_BIOLECTOR}_{bio_col}",
                    legendgrouptitle_text=f"{_SOURCE_BIOLECTOR} - {bio_col}",
                    yaxis=yaxis_ref,
                    hovertemplate=(
                        f"<b>{trace_name}</b><br>"
                        f"{selected_bio_index}: %{{x}}<br>"
                        f"{bio_col}: %{{y:.4f}}<extra></extra>"
                    ),
                )
            )

    # ── Fermentor traces ─────────────────────────────────
    for ferm_col in selected_ferm_cols:
        axis_idx = col_to_axis_idx[ferm_col]
        yaxis_ref = "y" if axis_idx == 0 else f"y{axis_idx + 1}"

        ferm_filtered = ferm_df[
            (ferm_df["Batch"].isin(selected_ferm_batches))
            & (ferm_df["Sample"].isin(selected_ferm_samples))
            & (ferm_df[selected_ferm_index].notna())
            & (ferm_df[ferm_col].notna())
        ]
        ferm_pairs = ferm_filtered[["Batch", "Sample"]].drop_duplicates().values.tolist()
        for idx_pair, (batch, sample) in enumerate(ferm_pairs):
            mask = (ferm_filtered["Batch"] == batch) & (ferm_filtered["Sample"] == sample)
            subset = ferm_filtered[mask].sort_values(selected_ferm_index)
            if subset.empty:
                continue
            color = _FERMENTOR_COLORS[idx_pair % len(_FERMENTOR_COLORS)]
            trace_name = f"[FERM] {batch} - {sample}"
            if num_axes > 1:
                trace_name += f" ({ferm_col})"
            fig.add_trace(
                go.Scatter(
                    x=subset[selected_ferm_index],
                    y=subset[ferm_col],
                    mode="lines+markers",
                    name=trace_name,
                    line={"color": color, "width": 2, "dash": "dash", "shape": "spline"},
                    marker={"size": 5, "symbol": "diamond", "color": color},
                    legendgroup=f"{_SOURCE_FERMENTOR}_{ferm_col}",
                    legendgrouptitle_text=f"{_SOURCE_FERMENTOR} - {ferm_col}",
                    yaxis=yaxis_ref,
                    hovertemplate=(
                        f"<b>{trace_name}</b><br>"
                        f"{selected_ferm_index}: %{{x}}<br>"
                        f"{ferm_col}: %{{y:.4f}}<extra></extra>"
                    ),
                )
            )

    # ── Y-axis layout (one per unique column name) ────────
    right_margin_per_axis = 0.07
    plot_domain_right = 1.0 - max(0, num_axes - 1) * right_margin_per_axis
    yaxis_layouts: dict = {}

    for axis_idx, col_name in enumerate(all_unique_cols):
        axis_color = _AXIS_COLORS[axis_idx % len(_AXIS_COLORS)]
        sources = col_sources.get(col_name, [])
        if sources == [_SOURCE_BIOLECTOR]:
            axis_title = f"{_SOURCE_BIOLECTOR} - {col_name}"
        elif sources == [_SOURCE_FERMENTOR]:
            axis_title = f"{_SOURCE_FERMENTOR} - {col_name}"
        else:
            axis_title = f"{_SOURCE_BIOLECTOR}/{_SOURCE_FERMENTOR} - {col_name}"
        if axis_idx == 0:
            yaxis_layouts["yaxis"] = {
                "title": {"text": axis_title, "font": {"color": axis_color}},
                "tickfont": {"color": axis_color},
            }
        elif axis_idx == 1:
            yaxis_layouts["yaxis2"] = {
                "title": {"text": axis_title, "font": {"color": axis_color}},
                "tickfont": {"color": axis_color},
                "overlaying": "y",
                "side": "right",
            }
        else:
            position = 1.0 - (axis_idx - 2) * right_margin_per_axis
            yaxis_layouts[f"yaxis{axis_idx + 1}"] = {
                "title": {"text": axis_title, "font": {"color": axis_color}},
                "tickfont": {"color": axis_color},
                "overlaying": "y",
                "side": "right",
                "position": position,
                "anchor": "free",
            }

    x_label = (
        selected_bio_index
        if selected_bio_index == selected_ferm_index
        else f"{selected_bio_index} / {selected_ferm_index}"
    )

    fig.update_layout(
        **yaxis_layouts,
        xaxis={"title": x_label, "domain": [0, plot_domain_right]},
        title=f"{_SOURCE_BIOLECTOR} ({', '.join(selected_bio_cols)})  vs  {_SOURCE_FERMENTOR} ({', '.join(selected_ferm_cols)})",
        legend={
            "groupclick": "toggleitem",
            "orientation": "h",
            "x": 0.5,
            "y": -0.15,
            "xanchor": "center",
            "yanchor": "top",
        },
        hovermode="closest",
        height=600,
        template="plotly_white",
    )

    st.plotly_chart(fig, use_container_width=True)
