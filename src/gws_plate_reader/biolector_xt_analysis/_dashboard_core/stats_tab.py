import itertools
import os
from typing import List

import matplotlib.pyplot as plt
import pandas as pd
import scikit_posthocs as sp
import scipy.stats as stats
import seaborn as sns
import streamlit as st
from gws_core import Settings
from gws_plate_reader.biolector_xt_analysis._dashboard_core.biolector_state import (
    BiolectorState,
    BiolectorStateMode,
)
from gws_plate_reader.dashboard_components.select_replicates_input import (
    render_select_replicates_input,
)
from gws_plate_reader.features_extraction.linear_logistic_cv import LogisticGrowthFitter
from gws_streamlit_main import StreamlitContainers, dataframe_paginated
from statsmodels.stats.multitest import multipletests


def render_stats_tab():
    # Récupération des filtres contenant le mot "Biomass"
    biomass_filters = [f for f in BiolectorState.get_filters_list() if "biomass" in f.lower()]
    # Vérification s'il y a des filtres correspondant
    if not biomass_filters:
        st.error("No filter containing 'Biomass' is available.")
        return

    col1, col2 = st.columns(2)
    with col1:
        filter_selection: List[str] = st.selectbox(
            "Select the observers", biomass_filters, index=0, key="analysis_filters"
        )

    # Allow the user to select duplicates
    init_value = BiolectorState.get_current_replicate_mode()
    options = ["Individual wells"] + BiolectorState.get_all_keys_well_description()
    index = options.index(init_value) if init_value in options else 0
    if init_value is None:
        init_value = options[0]
    with col2:
        selected_well_or_replicate: str = st.selectbox(
            "Filter by", options=options, index=index, key="analysis_well_or_replicate"
        )
    if selected_well_or_replicate != init_value:
        BiolectorState.set_current_replicate_mode(selected_well_or_replicate)
        st.rerun()

    selected_replicates = render_select_replicates_input(selected_well_or_replicate)

    df_analysis = _run_analysis_tab(
        filter_selection, selected_well_or_replicate, selected_replicates
    )

    # Statistics
    # run statistical tests only if there is the multiplate dashboard
    if not BiolectorState.get_mode() == BiolectorStateMode.MULTIPLE_PLATES:
        return

    st.write("**Statistical parameters:**")
    # Let the user filter the the dataframe based on the R2 threshold
    filter_r2_threshold = st.number_input(
        "R2 threshold",
        min_value=0.0,
        max_value=1.0,
        value=0.8,
        step=0.01,
        help="Minimum R2 value to consider a well for analysis.",
        key="filter_r2_threshold",
    )
    numerical_vars = ["Max_Absorbance"]

    # === Analysis Plan ===

    # Allow the user to select the analysis plan
    # This is a dictionary that defines the analysis plan
    # 'global' : test between the modalities of a variable on the whole dataset
    # 'cross' : test of a variable ('test_var') in each modality of another ('fixed_var')
    # 'nested_cross' : test of a variable in each combination of modalities
    # of several variables (more fine-grained conditional comparison)

    analysis_plan_global = st.multiselect(
        "Select the global analysis variables",
        options=["Well", "Plate_Name", "Label"],
        default=["Well", "Plate_Name", "Label"],
        key="analysis_plan_global",
        help="Test between the modalities of a variable on the whole dataset",
    )
    analysis_plan_cross = st.multiselect(
        "Select the cross analysis variables",
        options=["Well vs Label", "Plate_Name vs Well", "Label vs Plate_Name"],
        default=["Well vs Label", "Plate_Name vs Well", "Label vs Plate_Name"],
        key="analysis_plan_cross",
        help="Test of a variable (test_var) in each modality of another (fixed_var)",
    )

    analysis_nested_cross = st.multiselect(
        "Select the nested cross analysis variables",
        options=["Well+Plate vs Label", "Label+Plate vs Well"],
        default=["Well+Plate vs Label", "Label+Plate vs Well"],
        key="analysis_plan_nested_cross",
        help="Test of a variable in each combination of modalities of several variables (more fine-grained conditional comparison)",
    )

    st.info(
        "We advice you to select a few variables for the analysis, otherwise the plots may be too crowded. "
    )

    stats_button = st.button("Run Statistical tests", key="run_stats_button")

    if stats_button:
        with st.spinner("Running statistical tests..."):
            # Create temporary directory for results
            output_dir = Settings.make_temp_dir()
            png_metadata = []
            # Convert cross analysis selections to tuples
            cross_tuples = []
            for selection in analysis_plan_cross:
                if selection == "Well vs Label":
                    cross_tuples.append(("Well", "Label"))
                elif selection == "Plate_Name vs Well":
                    cross_tuples.append(("Plate_Name", "Well"))
                elif selection == "Label vs Plate_Name":
                    cross_tuples.append(("Label", "Plate_Name"))

            # Convert nested cross analysis selections to tuples with lists
            nested_cross_tuples = []
            for selection in analysis_nested_cross:
                if selection == "Well+Plate vs Label":
                    nested_cross_tuples.append((["Well", "Plate_Name"], "Label"))
                elif selection == "Label+Plate vs Well":
                    nested_cross_tuples.append((["Label", "Plate_Name"], "Well"))

            analysis_plan = {
                "global": analysis_plan_global,
                "cross": cross_tuples,
                "nested_cross": nested_cross_tuples,
            }

            # === SETUP ===
            df_analysis = df_analysis[df_analysis["Avg_R2"] > filter_r2_threshold]
            # reset index in order to have a column "index" for the dataframe
            df_analysis = df_analysis.reset_index()

            kruskal_results = []
            posthoc_all_dunn = []

            # === GLOBAL ===
            for group_var in analysis_plan.get("global", []):
                for num_var in numerical_vars:
                    kruskal_results, posthoc_all_dunn, png_metadata = run_test_and_plot(
                        kruskal_results,
                        posthoc_all_dunn,
                        df_analysis,
                        group_var,
                        num_var,
                        context="Global",
                        output_dir=output_dir,
                        png_metadata=png_metadata,
                    )

            # === COMPARAISONS 2 NIVEAUX ===
            for fixed_var, test_var in analysis_plan.get("cross", []):
                for fixed_val in df_analysis[fixed_var].unique():
                    subset = df_analysis[df_analysis[fixed_var] == fixed_val]
                    for num_var in numerical_vars:
                        context = f"{test_var} in {fixed_var} {fixed_val}"
                        kruskal_results, posthoc_all_dunn, png_metadata = run_test_and_plot(
                            kruskal_results,
                            posthoc_all_dunn,
                            subset,
                            test_var,
                            num_var,
                            context=context,
                            output_dir=output_dir,
                            png_metadata=png_metadata,
                        )

            # === COMPARAISONS 3 NIVEAUX ===
            for fixed_vars, test_var in analysis_plan.get("nested_cross", []):
                grouped = df_analysis.groupby(fixed_vars)
                for group_keys, group_df in grouped:
                    if isinstance(group_keys, str):
                        group_keys = [group_keys]
                    context = f"{test_var} in {' x '.join(fixed_vars)} = {', '.join(map(str, group_keys))}"
                    for num_var in numerical_vars:
                        kruskal_results, posthoc_all_dunn, png_metadata = run_test_and_plot(
                            kruskal_results,
                            posthoc_all_dunn,
                            group_df,
                            test_var,
                            num_var,
                            context=context,
                            output_dir=output_dir,
                            png_metadata=png_metadata,
                        )

            # === AJUSTEMENT MULTIPLE ===
            adjustable = [i for i, r in enumerate(kruskal_results) if r["Context"] == "Global"]
            if adjustable:
                pvals = [kruskal_results[i]["Kruskal-Wallis raw p-value"] for i in adjustable]
                _, adj, _, _ = multipletests(pvals, method="bonferroni")
                for i, p in zip(adjustable, adj):
                    kruskal_results[i]["Kruskal-Wallis adjusted p-value"] = p

            # === EXPORT FINAL ===
            pd.DataFrame(kruskal_results).to_csv(f"{output_dir}/kruskal_summary.csv", index=False)
            if posthoc_all_dunn:
                pd.concat(posthoc_all_dunn, ignore_index=True).to_csv(
                    f"{output_dir}/dunn_summary.csv", index=False
                )

            # Set the stats folder in BiolectorState
            BiolectorState.set_stats_folder(output_dir)
            BiolectorState.set_png_metadata(png_metadata)

    if not BiolectorState.get_stats_folder():
        return

    png_files = [f for f in os.listdir(BiolectorState.get_stats_folder()) if f.endswith(".png")]
    if not png_files:
        st.warning("Please select more wells to perform stastistical tests")
        return

    # Parse PNG files to extract metadata
    png_metadata = BiolectorState.get_png_metadata()

    if png_metadata:
        # Create selection interface
        st.write("**Statistical results**")

        # Display summary results
        with st.expander("Display Summary Results", expanded=False):
            # Display Kruskal-Wallis summary results
            kruskal_summary_path = os.path.join(
                BiolectorState.get_stats_folder(), "kruskal_summary.csv"
            )
            if os.path.exists(kruskal_summary_path):
                kruskal_summary = pd.read_csv(kruskal_summary_path)
                st.write("**Kruskal-Wallis Summary Results**")
                st.dataframe(kruskal_summary, width="stretch")
            else:
                st.warning("No Kruskal-Wallis summary results found.")
            # Display Dunn's post-hoc test summary results
            dunn_summary_path = os.path.join(BiolectorState.get_stats_folder(), "dunn_summary.csv")
            if os.path.exists(dunn_summary_path):
                dunn_summary = pd.read_csv(dunn_summary_path)
                st.write("**Dunn's Post-hoc Test Summary Results**")
                dataframe_paginated(
                    dunn_summary,
                    key="dunn_summary_paginator",
                    paginate_rows=True,
                    row_page_size_options=[25, 50, 100],
                    paginate_columns=False,
                    column_page_size_options=None,
                    use_container_width=True,
                )
            else:
                st.warning("No Dunn's post-hoc test summary results found.")

        # Get unique values for selection
        unique_group_vars = sorted(list(set([item["group_var"] for item in png_metadata])))

        col1, col2 = st.columns(2)

        with col1:
            selected_group_var = st.selectbox(
                "Select Group Variable:", options=unique_group_vars, key="selected_group_var"
            )

        with col2:
            # Only show contexts that match the selected group variable
            filtered_contexts = [
                item["context"] for item in png_metadata if item["group_var"] == selected_group_var
            ]
            unique_contexts = sorted(set(filtered_contexts))
            if not unique_contexts:
                st.warning("There are no contexts available for the selected group variable.")
                return
            selected_context = st.selectbox(
                "Select Context:", options=unique_contexts, key="selected_context"
            )

        # Find matching PNG file
        matching_png = None
        for item in png_metadata:
            if item["context"] == selected_context and item["group_var"] == selected_group_var:
                matching_png = item
                break

        if not matching_png:
            st.warning("No plot found for the selected combination.")
            return

        # Display the selected PNG
        st.image(os.path.join(BiolectorState.get_stats_folder(), matching_png["file"]))

        # Option to see CSV data
        with st.expander("View the plot's raw data", expanded=False):
            # Look for corresponding CSV file
            csv_filename = f"dunn_{matching_png['num_var']}_by_{matching_png['group_var']}_{matching_png['context_with_underscores']}.csv"
            csv_path = os.path.join(BiolectorState.get_stats_folder(), csv_filename)

            if os.path.exists(csv_path):
                csv_data = pd.read_csv(csv_path, index_col=0)
                st.write("**Post-hoc test results (Dunn's Test)**")
                st.dataframe(csv_data, width="stretch")

            else:
                st.warning("No corresponding CSV data found for this plot.")


def _run_analysis_tab(
    filter_selection: str, selected_well_or_replicate: str, selected_replicates: List[str]
):
    with st.spinner("Running analysis..."):
        # Get the dataframe
        df = BiolectorState.get_table_by_filter(
            selected_well_or_replicate, filter_selection, selected_replicates
        )
        df = df.drop(["time"], axis=1)
        # Features extraction functions
        try:
            logistic_fitter = LogisticGrowthFitter(df)
            logistic_fitter.fit_logistic_growth_with_cv()
            df_analysis = logistic_fitter.df_params
            with st.expander("Dataframe", expanded=False):
                with StreamlitContainers.full_width_dataframe_container(
                    "container-full-dataframe-growth-rate"
                ):
                    st.dataframe(
                        df_analysis.style.format(thousands=" ", precision=4), width="stretch"
                    )

        except:
            st.error("Optimal parameters not found for some wells, try deselecting some wells.")
    return df_analysis


# === ANNOTATION DES P-VALUES DE DUNN (TOUTES LES PAIRES) ===
def annotate_posthoc(ax, posthoc_pvals, group_names, y_max=None):
    y = y_max * 1.05 if y_max else 1.05
    h = y_max * 0.05 if y_max else 0.05
    for i, j in itertools.combinations(range(len(group_names)), 2):
        g1, g2 = group_names[i], group_names[j]
        try:
            pval = posthoc_pvals.loc[g1, g2]
        except KeyError:
            try:
                pval = posthoc_pvals.loc[g2, g1]
            except KeyError:
                continue
        stars = ""
        if pval < 0.001:
            stars = "***"
        elif pval < 0.01:
            stars = "**"
        elif pval < 0.05:
            stars = "*"
        label = f"p={pval:.3f} {stars}"
        x1, x2 = i, j
        ax.plot([x1, x1, x2, x2], [y, y + h, y + h, y], lw=1.0, c="gray")
        ax.text((x1 + x2) / 2, y + h * 1.1, label, ha="center", fontsize=9)
        y += h * 1.5


# === TEST + PLOT ===
def run_test_and_plot(
    kruskal_results: list,
    posthoc_all_dunn: list,
    data,
    group_var,
    num_var,
    context,
    output_dir,
    png_metadata,
):
    sub_df = data[[group_var, num_var]].dropna()
    if sub_df[group_var].nunique() < 2:
        print(f"[!] Skipped: Only one group found in {context} for {group_var}")
        return kruskal_results, posthoc_all_dunn, png_metadata

    try:
        groups = [g[num_var].values for _, g in sub_df.groupby(group_var)]
        stat, p_kw = stats.kruskal(*groups)
    except Exception as e:
        print(f"[!] Error in Kruskal-Wallis test for {context} ({group_var}): {e}")
        return kruskal_results, posthoc_all_dunn, png_metadata

    result = {
        "Context": context,
        "Grouping Variable": group_var,
        "Numerical Variable": num_var,
        "Kruskal-Wallis raw p-value": p_kw,
        "Kruskal-Wallis adjusted p-value": None,
    }
    kruskal_results.append(result)

    try:
        dunn = sp.posthoc_dunn(sub_df, val_col=num_var, group_col=group_var, p_adjust="bonferroni")
        dunn_df = dunn.stack().reset_index()
        dunn_df.columns = ["Group1", "Group2", "Adjusted p-value"]
        dunn_df.insert(0, "Numerical Variable", num_var)
        dunn_df.insert(1, "Group Context", context)
        posthoc_all_dunn.append(dunn_df)
        filename = f"dunn_{num_var}_by_{group_var}_{context.replace(' ', '_').replace('(', '').replace(')', '')}.csv"
        dunn.to_csv(f"{output_dir}/{filename}")
    except Exception as e:
        print(f"[!] Error in Dunn's posthoc test for {context} ({group_var}): {e}")
        dunn = None

    # PLOT
    plt.figure(figsize=(8, 5))
    ax = sns.boxplot(data=sub_df, x=group_var, y=num_var)
    y_pos = sub_df[num_var].max() * 1.2
    ax.set_title(f"{num_var} par {group_var} [{context}]", pad=40)
    plt.xticks(rotation=45)

    if p_kw < 0.001:
        stars = "***"
    elif p_kw < 0.01:
        stars = "**"
    elif p_kw < 0.05:
        stars = "*"
    else:
        stars = ""
    p_label = f"Kruskal-Wallis p = {p_kw:.3e} {stars}"
    if context != "Global":
        p_label += " (uncorrected)"

    ax.text(0.5, 1.02, p_label, ha="center", fontsize=10, transform=ax.transAxes)

    if dunn is not None:
        group_order = list(sub_df[group_var].unique())
        annotate_posthoc(ax, dunn, group_order, y_max=sub_df[num_var].max())

    plt.tight_layout()
    context_with_underscores = context.replace(" ", "_").replace("(", "").replace(")", "")
    plot_name = f"boxplot_{num_var}_by_{group_var}_{context_with_underscores}.png"
    plt.savefig(f"{output_dir}/{plot_name}")
    plt.close()

    png_metadata.append(
        {
            "file": plot_name,
            "num_var": num_var,
            "group_var": group_var,
            "context_with_underscores": context_with_underscores,
            "context": context,
        }
    )
    return kruskal_results, posthoc_all_dunn, png_metadata
