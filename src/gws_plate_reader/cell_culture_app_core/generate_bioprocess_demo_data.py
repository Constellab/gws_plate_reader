import os
import re
import zipfile

import numpy as np
import pandas as pd
from gws_core import (
    File,
    InputSpec,
    InputSpecs,
    OutputSpec,
    OutputSpecs,
    Table,
    Task,
    TypingStyle,
    task_decorator,
)


@task_decorator(
    "GenerateBioprocessDemoData",
    human_name="Generate Bioprocess Demo Data",
    short_description="Generate demo input files for the Bioprocess app from a metadata-feature table",
    style=TypingStyle.material_icon(material_icon_name="science", background_color="#4CAF50"),
)
class GenerateBioprocessDemoData(Task):
    """
    Generate demo input files for the Constellab Bioprocess app.

    This task takes a metadata-feature table (typically the output of CellCultureMergeFeatureMetadata)
    and generates the 4 input files required by ConstellabBioprocessLoadData:

    1. **Info CSV**: One row per sample with Batch, Fermentor, Medium, and experimental conditions
    2. **Medium CSV**: One row per unique medium with mean composition columns
    3. **Raw Data CSV**: Synthetic time-series measurements (Biomasse, pH, temperature, NaOH) correlated with growth
    4. **Follow-up ZIP**: Synthetic OD growth curves generated from logistic 4P model parameters (online monitoring)

    ## Input Table Structure

    The input table must have:
    - `Series` column: sample identifier in format `<Batch>_<Fermentor>` (e.g., "M1_1")
    - `Medium` column: medium name
    - Medium composition columns (numeric, positioned before condition columns)
    - Condition columns (e.g., "T ( C)", "pH (u_pH)", "OD at 880 nm", "NaOH (mL)")
    - `Model` column (or `param_*` columns): marks the boundary between metadata and features
    - `param_y0`, `param_A`, `param_mu`, `param_lag`: logistic 4P model parameters

    ## Column Detection

    - Metadata columns: all columns between `Medium` and `Model` (or first `param_*` column)
    - Composition columns: metadata columns before the first one containing parentheses
    - Condition columns: metadata columns from the first one containing parentheses onward

    ## Generated Data

    - **Raw data**: Biomasse (g/L) from logistic 4P model (offline measurements every 2h),
      pH decreases with growth, NaOH increases cumulatively, temperature stays constant (with noise)
    - **Follow-up**: OD at 880 nm from logistic 4P model (online monitoring every 0.5h, with noise)
    """

    input_specs: InputSpecs = InputSpecs(
        {
            "metadata_feature_table": InputSpec(
                Table,
                human_name="Metadata Feature Table",
                short_description="Merged metadata-feature table with Series, medium composition, conditions, and model parameters",
            ),
        }
    )

    output_specs: OutputSpecs = OutputSpecs(
        {
            "info_csv": OutputSpec(
                File,
                human_name="Info CSV file",
                short_description="CSV with Batch, Fermentor, Medium, and experimental conditions",
            ),
            "raw_data_csv": OutputSpec(
                File,
                human_name="Raw data CSV file",
                short_description="CSV with synthetic time-series measurements per sample",
            ),
            "medium_csv": OutputSpec(
                File,
                human_name="Medium CSV file",
                short_description="CSV with medium composition (one row per unique medium)",
            ),
            "follow_up_zip": OutputSpec(
                File,
                human_name="Follow-up ZIP file",
                short_description="ZIP containing synthetic OD growth curve CSVs per sample",
            ),
        }
    )

    def run(self, params, inputs):
        table: Table = inputs["metadata_feature_table"]
        df = table.get_data()
        tmp_dir = self.create_tmp_dir()

        np.random.seed(42)

        # Parse Series column into Batch and Fermentor
        # Series format: "M1_1" → Batch = "M1", Fermentor = "1"
        parsed = df["Series"].str.rsplit("_", n=1, expand=True)
        df["Batch"] = parsed[0]
        df["Fermentor"] = parsed[1]

        # Detect column groups
        composition_cols, condition_cols = self._detect_column_groups(df)
        self.log_info_message(f"Composition columns: {composition_cols}")
        self.log_info_message(f"Condition columns: {condition_cols}")

        # 1. Info CSV: Batch, Fermentor, Medium + conditions (one row per sample)
        info_df = df[["Batch", "Fermentor", "Medium"] + condition_cols].copy()
        info_path = os.path.join(tmp_dir, "info.csv")
        info_df.to_csv(info_path, index=False)

        # 2. Medium CSV: Medium + composition (one row per unique medium, averaged)
        medium_numeric = df[["Medium"] + composition_cols].copy()
        for col in composition_cols:
            medium_numeric[col] = pd.to_numeric(medium_numeric[col], errors="coerce")
        medium_agg = medium_numeric.groupby("Medium")[composition_cols].mean().reset_index()
        medium_path = os.path.join(tmp_dir, "medium.csv")
        medium_agg.to_csv(medium_path, index=False)

        # 3. Raw Data CSV: synthetic time-series correlated with growth
        raw_data_df = self._generate_raw_data(df, condition_cols)
        raw_data_path = os.path.join(tmp_dir, "raw_data.csv")
        raw_data_df.to_csv(raw_data_path, index=False)

        # 4. Follow-up ZIP: synthetic OD growth curves from logistic 4P model
        follow_up_zip_path = self._generate_follow_up_zip(df, tmp_dir)

        return {
            "info_csv": File(info_path),
            "raw_data_csv": File(raw_data_path),
            "medium_csv": File(medium_path),
            "follow_up_zip": File(follow_up_zip_path),
        }

    def _detect_column_groups(self, df: pd.DataFrame) -> tuple[list[str], list[str]]:
        """
        Detect medium composition columns and condition columns.

        Returns (composition_cols, condition_cols).
        """
        cols = df.columns.tolist()
        medium_idx = cols.index("Medium")

        # Find the boundary between metadata and feature columns
        feature_start = len(cols)
        for i, col in enumerate(cols):
            if col == "Model" or col.startswith("param_"):
                feature_start = i
                break

        metadata_cols = cols[medium_idx + 1: feature_start]

        # Split at the first column with parentheses in its name
        # Before = composition (e.g., Peptone, D-glucose, ...)
        # From there = conditions (e.g., T ( C), pH (u_pH), OD at 880 nm, NaOH (mL))
        first_paren = next(
            (i for i, c in enumerate(metadata_cols) if re.search(r"\(", c)),
            len(metadata_cols),
        )
        composition_cols = metadata_cols[:first_paren]
        condition_cols = metadata_cols[first_paren:]

        return composition_cols, condition_cols

    def _generate_raw_data(self, df: pd.DataFrame, condition_cols: list[str]) -> pd.DataFrame:
        """Generate synthetic time-series raw data for each (Batch, Fermentor) pair.

        Includes Biomasse (g/L) from the logistic 4P model (offline measurements every 2h)
        plus condition columns (pH, T, NaOH) correlated with the growth curve.
        OD is excluded here since it is generated as online data in follow_up.
        """
        # Exclude OD column from raw_data (it will be in follow_up as online monitoring)
        raw_cols = [c for c in condition_cols if "OD" not in c.upper()]
        # Every 2 hours for offline measurements (25 points, enough for feature extraction)
        time_points = np.arange(0, 49, 2.0)
        rows = []

        for _, row in df.iterrows():
            batch = row["Batch"]
            fermentor = row["Fermentor"]

            # Get growth parameters
            y0 = self._safe_param(row, "param_y0", 0.0)
            A = self._safe_param(row, "param_A", 1.0)
            mu = self._safe_param(row, "param_mu", 0.2)
            lag = self._safe_param(row, "param_lag", 10.0)

            # Generate biomasse from logistic 4P model
            biomasse = self._logistic_4p(time_points, y0, A, mu, lag)
            growth_frac = (biomasse - y0) / (A - y0) if A != y0 else np.zeros_like(time_points)

            for i, t in enumerate(time_points):
                raw_row = {"Batch": batch, "Fermentor": fermentor, "Time": float(t)}

                # Biomasse (g/L) - offline measurement with noise
                raw_row["Biomasse (g/L)"] = round(
                    biomasse[i] + np.random.normal(0, 0.02), 4
                )

                for col in raw_cols:
                    base_val = float(row[col]) if pd.notna(row[col]) else 0.0
                    col_upper = col.upper()

                    if "PH" in col_upper:
                        # pH decreases as cells grow (acid production)
                        val = base_val - 1.5 * growth_frac[i] + np.random.normal(0, 0.05)
                        raw_row[col] = round(val, 2)
                    elif "NAOH" in col_upper:
                        # NaOH increases cumulatively (added to counteract pH drop)
                        val = base_val * growth_frac[i] + np.random.normal(0, 0.5)
                        raw_row[col] = round(max(0, val), 1)
                    elif col_upper.startswith("T ") or col_upper.startswith("T("):
                        # Temperature is controlled, small noise
                        val = base_val + np.random.normal(0, 0.2)
                        raw_row[col] = round(val, 1)
                    else:
                        # Generic: constant with small noise
                        val = base_val + np.random.normal(0, abs(base_val) * 0.02)
                        raw_row[col] = round(val, 4)

                rows.append(raw_row)

        return pd.DataFrame(rows)

    def _generate_follow_up_zip(self, df: pd.DataFrame, tmp_dir: str) -> str:
        """Generate follow-up ZIP with synthetic OD growth curves from logistic 4P model."""
        follow_up_data_dir = os.path.join(tmp_dir, "follow_up_data")
        os.makedirs(follow_up_data_dir)

        time_points = np.arange(0, 49, 0.5)

        for _, row in df.iterrows():
            batch = row["Batch"]
            fermentor = row["Fermentor"]

            y0 = self._safe_param(row, "param_y0", 0.0)
            A = self._safe_param(row, "param_A", 1.0)
            mu = self._safe_param(row, "param_mu", 0.2)
            lag = self._safe_param(row, "param_lag", 10.0)

            # Generate OD curve from logistic 4P model
            od_values = self._logistic_4p(time_points, y0, A, mu, lag)

            # Add realistic measurement noise
            noise = np.random.normal(0, 0.015, len(time_points))
            od_noisy = np.round(od_values + noise, 4)

            follow_up_df = pd.DataFrame({"Time": time_points, "OD at 880 nm": od_noisy})

            file_path = os.path.join(follow_up_data_dir, f"{batch} {fermentor}.csv")
            follow_up_df.to_csv(file_path, index=False)

        # Create ZIP with follow_up_data/ as top-level folder
        zip_path = os.path.join(tmp_dir, "follow_up.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for filename in sorted(os.listdir(follow_up_data_dir)):
                file_path = os.path.join(follow_up_data_dir, filename)
                zipf.write(file_path, f"follow_up_data/{filename}")

        return zip_path

    @staticmethod
    def _logistic_4p(t, y0, A, mu, lag):
        """4-parameter logistic growth model."""
        return y0 + (A - y0) / (1.0 + np.exp(-mu * (t - lag)))

    @staticmethod
    def _safe_param(row, col_name: str, default: float) -> float:
        """Get a float parameter from a row, returning default if missing or NaN."""
        if col_name not in row.index:
            return default
        val = row[col_name]
        if pd.isna(val):
            return default
        return float(val)
