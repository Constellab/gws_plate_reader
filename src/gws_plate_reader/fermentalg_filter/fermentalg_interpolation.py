from gws_core import (InputSpec, OutputSpec, InputSpecs, OutputSpecs, Table, Tag,
                      TypingStyle, ResourceSet, Task, task_decorator, ConfigSpecs, ConfigParams,
                      StrParam, IntParam)
from typing import Dict, Any, List, Tuple
from scipy.interpolate import (
    UnivariateSpline,
    PchipInterpolator,
    Akima1DInterpolator,
    CubicSpline,
    interp1d,
)
import pandas as pd
import numpy as np


@task_decorator("FermentalgInterpolation",
                human_name="Fermentalg Time Series Interpolation",
                short_description="Interpolate fermentalg time series data with multiple advanced methods",
                style=TypingStyle.community_icon(icon_technical_name="chart-line", background_color="#17a2b8"))
class FermentalgInterpolation(Task):
    """
    Interpolate fermentalg time series data using various interpolation methods.

    This task takes a ResourceSet of fermentalg data and applies interpolation to create
    uniform time grids for all data series, enabling better comparison and analysis.

    Features:
    - Multiple interpolation methods: linear, nearest, quadratic, cubic, pchip, akima, cubic_spline, univariate_spline
    - Multiple grid strategies (global auto, per file, reference)
    - Configurable edge handling strategies
    - Automatic time grid generation based on data characteristics
    - Preservation of metadata and tags
    - Shape-preserving methods (PCHIP, Akima)

    Supported Methods:
    - linear: Fast linear interpolation (numpy)
    - nearest: Nearest neighbor interpolation
    - quadratic: Quadratic spline interpolation
    - cubic: Cubic spline interpolation
    - pchip: Piecewise Cubic Hermite Interpolating Polynomial (shape-preserving)
    - akima: Akima spline interpolation (shape-preserving, smooth)
    - cubic_spline: Natural cubic spline
    - univariate_spline: Adaptive order univariate spline with fallback
    - spline: Alias for univariate_spline
    """

    TIME_COL = "Temps de culture (h)"  # fixed column name

    SUPPORTED_METHODS = {
        "linear",               # np.interp
        "nearest",              # interp1d(kind='nearest')
        "quadratic",            # interp1d(kind='quadratic')
        "cubic",                # interp1d(kind='cubic')
        "pchip",                # PchipInterpolator (shape-preserving)
        "akima",                # Akima1DInterpolator
        "cubic_spline",         # CubicSpline
        "univariate_spline",    # UnivariateSpline (adaptive order)
        "spline",               # alias -> univariate_spline
    }

    input_specs: InputSpecs = InputSpecs({
        'resource_set': InputSpec(ResourceSet,
                                  human_name="Input ResourceSet to interpolate",
                                  short_description="ResourceSet containing fermentalg time series data",
                                  optional=False),
    })

    output_specs: OutputSpecs = OutputSpecs({
        'interpolated_resource_set': OutputSpec(ResourceSet,
                                                human_name="Interpolated ResourceSet",
                                                short_description="ResourceSet with interpolated time series data")
    })

    config_specs = ConfigSpecs({
        'method': StrParam(
            human_name="Interpolation method",
            short_description="Method: linear, nearest, quadratic, cubic, pchip, akima, cubic_spline, univariate_spline, spline",
            default_value="akima",
            allowed_values=list(SUPPORTED_METHODS)
        ),
        'grid_strategy': StrParam(
            human_name="Grid strategy",
            short_description="Strategy for time grid generation",
            default_value="global_auto",
            allowed_values=["global_auto", "per_file", "reference"]
        ),
        'n_points': IntParam(
            human_name="Number of points",
            short_description="Number of points in interpolation grid (auto if not set)",
            default_value=500,
            min_value=10,
            max_value=20000,
            optional=True
        ),
        'spline_order': IntParam(
            human_name="Spline order",
            short_description="Order of spline interpolation for univariate_spline method (1-5)",
            default_value=3,
            min_value=1,
            max_value=5
        ),
        'edge_strategy': StrParam(
            human_name="Edge handling strategy",
            short_description="How to handle data beyond original time range",
            default_value="nearest",
            allowed_values=["nearest", "linear", "nan"]
        ),
        'reference_index': IntParam(
            human_name="Reference resource index",
            short_description="Index of resource to use as reference for grid (when grid_strategy='reference')",
            default_value=0,
            min_value=0
        )
    })

    def convert_commas_to_dots(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert comma decimal separators to dots and coerce to numeric where possible"""
        out = df.copy()
        for col in out.columns:
            if out[col].dtype == object:
                # replace decimal comma by dot
                ser = out[col].astype(str).str.replace(",", ".", regex=False).replace("nan", np.nan)
                # try numeric coercion
                ser_num = pd.to_numeric(ser, errors="coerce")
                # keep numeric series if it has at least some finite values, else keep original text
                if np.isfinite(ser_num.astype(float)).sum() > 0:
                    out[col] = ser_num
                else:
                    out[col] = ser  # leave as cleaned text
        return out

    def auto_n_points_from_time_list(self, t_list: List[np.ndarray], max_points=20000, min_points=100) -> int:
        """Auto-calculate number of points based on time span and median time step"""
        dts = []
        for t in t_list:
            t = np.asarray(t, dtype=float)
            t = t[np.isfinite(t)]
            if t.size >= 2:
                t_sorted = np.sort(t)
                dt = np.diff(t_sorted)
                dt = dt[np.isfinite(dt) & (dt > 0)]
                if dt.size:
                    dts.append(np.median(dt))
        if not dts:
            return 1000
        median_dt = float(np.median(dts))
        tmins = [np.nanmin(tt) for tt in t_list if np.size(tt) > 0]
        tmaxs = [np.nanmax(tt) for tt in t_list if np.size(tt) > 0]
        if not tmins or not tmaxs or median_dt <= 0:
            return 1000
        span = float(np.nanmax(tmaxs) - np.nanmin(tmins))
        est = int(np.ceil(span / median_dt))
        return max(min_points, min(est, max_points))

    def prepare_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare DataFrame for interpolation"""
        df = self.convert_commas_to_dots(df)
        if self.TIME_COL not in df.columns:
            raise KeyError(f"'{self.TIME_COL}' column not found in data.")
        df[self.TIME_COL] = pd.to_numeric(df[self.TIME_COL], errors="coerce")
        df = df.dropna(subset=[self.TIME_COL]).sort_values(self.TIME_COL)
        return df

    def build_global_grid(self, dfs: List[pd.DataFrame], n_points: int = None) -> np.ndarray:
        """Build a global time grid covering all data"""
        t_arrays = [d[self.TIME_COL].to_numpy() for d in dfs]
        tmin = min(float(np.nanmin(t)) for t in t_arrays if t.size)
        tmax = max(float(np.nanmax(t)) for t in t_arrays if t.size)
        if not np.isfinite(tmin) or not np.isfinite(tmax) or tmin == tmax:
            raise ValueError("Invalid or no time range found.")
        if n_points is None:
            n_points = self.auto_n_points_from_time_list(t_arrays)
        return np.linspace(tmin, tmax, int(n_points))

    def _dedup_time_average(self, t_valid: np.ndarray, y_valid: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Remove duplicate time points by averaging y values"""
        t_unique, inv = np.unique(t_valid, return_inverse=True)
        if t_unique.size == t_valid.size:
            return t_valid, y_valid
        y_accum = np.zeros_like(t_unique, dtype=float)
        counts = np.zeros_like(t_unique, dtype=int)
        for i, yi in zip(inv, y_valid):
            y_accum[i] += yi
            counts[i] += 1
        y_avg = y_accum / np.maximum(counts, 1)
        return t_unique, y_avg

    def _core_interpolate(
        self,
        t_valid: np.ndarray,
        y_valid: np.ndarray,
        t_new: np.ndarray,
        method: str,
        spline_order: int,
    ) -> np.ndarray:
        """
        Returns interpolated values at t_new (WITHOUT edge extrapolation policy).
        Expects t_valid strictly increasing and deduplicated.
        """
        m = int(len(t_valid))
        if m < 2:
            return np.full_like(t_new, y_valid[0] if m == 1 else np.nan, dtype=float)

        method = method.lower()
        if method not in self.SUPPORTED_METHODS:
            raise ValueError(
                f"Unknown method='{method}'. Supported: {sorted(self.SUPPORTED_METHODS)}"
            )
        if method == "spline":
            method = "univariate_spline"

        # Fast linear interpolation
        if method == "linear":
            return np.interp(t_new, t_valid, y_valid)

        # Nearest neighbor
        if method == "nearest":
            f = interp1d(t_valid, y_valid, kind="nearest", bounds_error=False,
                         fill_value=(y_valid[0], y_valid[-1]))
            return f(t_new)

        # Quadratic and cubic from scipy.interpolate.interp1d
        if method in ("quadratic", "cubic"):
            f = interp1d(t_valid, y_valid, kind=method, bounds_error=False,
                         fill_value=(y_valid[0], y_valid[-1]))
            return f(t_new)

        # PCHIP - shape-preserving
        if method == "pchip":
            f = PchipInterpolator(t_valid, y_valid, axis=0)
            return f(t_new)

        # Akima - shape-preserving and smooth
        if method == "akima":
            f = Akima1DInterpolator(t_valid, y_valid, axis=0)
            return f(t_new)

        # Natural cubic spline
        if method == "cubic_spline":
            f = CubicSpline(t_valid, y_valid)
            return f(t_new)

        # Univariate spline with adaptive order and fallback
        if method == "univariate_spline":
            k_eff = int(max(1, min(int(spline_order), m - 1)))
            try:
                spline = UnivariateSpline(t_valid, y_valid, k=k_eff, s=0)
                return spline(t_new)
            except Exception:
                # Fallback to linear interpolation
                self.log_warning_message("UnivariateSpline failed, falling back to linear interpolation")
                return np.interp(t_new, t_valid, y_valid)

        # Should never reach here
        raise RuntimeError("Interpolation dispatch fell through.")

    def interpolate_one(
        self,
        df: pd.DataFrame,
        t_new: np.ndarray,
        method: str = "linear",
        spline_order: int = 3,
        edge_strategy: str = "nearest",
    ) -> pd.DataFrame:
        """Interpolate a single DataFrame"""
        t = df[self.TIME_COL].to_numpy()
        numeric_cols = [c for c in df.columns if c != self.TIME_COL and pd.api.types.is_numeric_dtype(df[c])]

        out = pd.DataFrame(index=pd.Index(t_new, name=self.TIME_COL))

        for col in numeric_cols:
            y = df[col].to_numpy()
            mask = np.isfinite(t) & np.isfinite(y)
            t_valid, y_valid = t[mask], y[mask]

            if t_valid.size < 2:
                if t_valid.size == 1:
                    out[col] = np.full_like(t_new, y_valid[0], dtype=float)
                continue

            # deduplicate time by averaging, then sort
            t_valid, y_valid = self._dedup_time_average(t_valid, y_valid)
            order = np.argsort(t_valid)
            t_valid = t_valid[order]
            y_valid = y_valid[order]

            # core interpolation (no edges yet)
            y_core = self._core_interpolate(t_valid, y_valid, t_new, method=method, spline_order=spline_order)

            # edges policy (consistent across methods)
            left_mask = t_new < t_valid[0]
            right_mask = t_new > t_valid[-1]
            if left_mask.any() or right_mask.any():
                if edge_strategy == "nearest":
                    y_core[left_mask] = y_valid[0]
                    y_core[right_mask] = y_valid[-1]
                elif edge_strategy == "linear":
                    if t_valid.size >= 2:
                        dtL = (t_valid[1] - t_valid[0])
                        mL = (y_valid[1] - y_valid[0]) / (dtL if dtL != 0 else 1)
                        y_core[left_mask] = y_valid[0] + mL * (t_new[left_mask] - t_valid[0])

                        dtR = (t_valid[-1] - t_valid[-2])
                        mR = (y_valid[-1] - y_valid[-2]) / (dtR if dtR != 0 else 1)
                        y_core[right_mask] = y_valid[-1] + mR * (t_new[right_mask] - t_valid[-1])
                elif edge_strategy == "nan":
                    y_core[left_mask] = np.nan
                    y_core[right_mask] = np.nan

            out[col] = y_core

        return out

    def run(self, params: ConfigParams, inputs) -> Dict[str, Any]:
        resource_set: ResourceSet = inputs['resource_set']

        # Get parameters
        method = params.get_value('method')
        grid_strategy = params.get_value('grid_strategy')
        n_points = params.get_value('n_points')
        spline_order = params.get_value('spline_order')
        edge_strategy = params.get_value('edge_strategy')
        reference_index = params.get_value('reference_index')

        self.log_info_message(f"Starting interpolation with method: {method}, grid strategy: {grid_strategy}")

        # Prepare data
        resources = resource_set.get_resources()
        raw_dfs = {}
        metadata = {}

        for resource_name, resource in resources.items():
            if not isinstance(resource, Table):
                continue

            df = self.prepare_dataframe(resource.get_data())
            raw_dfs[resource_name] = df

            # Store metadata
            metadata[resource_name] = {
                'original_resource': resource,
                'tags': resource.tags,
                'column_tags': {col: resource.get_column_tags_by_name(col) for col in resource.get_column_names()}
            }

        if not raw_dfs:
            raise ValueError("No valid Table resources found for interpolation")

        dfs = list(raw_dfs.values())

        # Build time grid based on strategy
        if grid_strategy == "per_file":
            # Each file gets its own grid
            results = {}
            for name, df in raw_dfs.items():
                t_array = df[self.TIME_COL].to_numpy()
                local_n = self.auto_n_points_from_time_list([t_array])
                t_new_local = np.linspace(float(np.nanmin(t_array)), float(np.nanmax(t_array)), int(local_n))
                results[name] = self.interpolate_one(df, t_new_local, method=method,
                                                     spline_order=spline_order, edge_strategy=edge_strategy)
                results[name].index.name = self.TIME_COL
        elif grid_strategy == "reference":
            # Use reference file's time range
            if reference_index >= len(dfs):
                reference_index = 0
                self.log_warning_message("Reference index out of range, using index 0")
            ref_df = dfs[reference_index]
            t_new = self.build_global_grid([ref_df], n_points)
            results = {}
            for name, df in raw_dfs.items():
                results[name] = self.interpolate_one(
                    df, t_new, method=method, spline_order=spline_order, edge_strategy=edge_strategy)
        else:  # global_auto
            # Use global time range
            t_new = self.build_global_grid(dfs, n_points)
            results = {}
            for name, df in raw_dfs.items():
                results[name] = self.interpolate_one(
                    df, t_new, method=method, spline_order=spline_order, edge_strategy=edge_strategy)

        # Create output ResourceSet
        interpolated_res = ResourceSet()

        for resource_name, interpolated_df in results.items():
            # Reset index to make time column a regular column
            interpolated_df_with_time = interpolated_df.reset_index()

            # Create new Table
            interpolated_table = Table(interpolated_df_with_time)
            interpolated_table.name = f"{resource_name}_interpolated"

            # Copy tags from original resource
            original_meta = metadata[resource_name]
            if original_meta['tags']:
                for tag in original_meta['tags'].get_tags():
                    interpolated_table.tags.add_tag(Tag(key=tag.key, value=tag.value))

            # Add interpolation info tag
            interpolated_table.tags.add_tag(Tag(key="interpolation_method", value=method))
            interpolated_table.tags.add_tag(Tag(key="interpolation_grid_strategy", value=grid_strategy))
            interpolated_table.tags.add_tag(Tag(key="interpolation_edge_strategy", value=edge_strategy))

            # Copy column tags for columns that exist in both original and interpolated
            for col in interpolated_df_with_time.columns:
                if col in original_meta['column_tags']:
                    col_tags = original_meta['column_tags'][col]
                    for tag_key, tag_value in col_tags.items():
                        interpolated_table.add_column_tag_by_name(col, tag_key, tag_value)

            interpolated_res.add_resource(interpolated_table, resource_name)

        self.log_success_message(f"Successfully interpolated {len(results)} resources using {method} method")

        return {
            'interpolated_resource_set': interpolated_res
        }
