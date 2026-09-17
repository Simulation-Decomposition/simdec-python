from dataclasses import dataclass
import math
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .sensitivity_indices import sensitivity_indices

__all__ = [
    "HeterogeneityDetail",
    "HeterogeneityResult",
    "heterogeneity_indices",
]

_DEFAULT_N_REGIONS = 5
# Computational safeguard, not a guarantee of statistical stability.
_MIN_REGION_SIZE = 100


@dataclass
class HeterogeneityDetail:
    """Detailed results for one partitioning variable.

    Attributes
    ----------
    raw_profiles : pandas.DataFrame
        Raw regional combined sensitivity profiles. Rows are regions and
        columns are model inputs.
    normalized_profiles : pandas.DataFrame
        Regional profiles normalized to sum to one within each region. These
        profiles are used to calculate H.
    regional_sums : pandas.Series
        Sum of the raw combined sensitivity indices in each region.
    region_counts : pandas.Series
        Number of observations in each region.
    individual_contributions : pandas.Series
        Input-level contributions C_{i,Z}. These sum to H_Z. For a categorical
        input partition, the partitioning input itself is omitted because it is
        constant within each of its own categories.
    """

    raw_profiles: pd.DataFrame
    normalized_profiles: pd.DataFrame
    regional_sums: pd.Series
    region_counts: pd.Series
    individual_contributions: pd.Series

    def __repr__(self) -> str:
        n_regions, n_inputs = self.raw_profiles.shape
        return (
            "HeterogeneityDetail("
            f"regions={n_regions}, inputs={n_inputs}; "
            "raw_profiles, normalized_profiles, regional_sums, "
            "region_counts, individual_contributions)"
        )


@dataclass
class HeterogeneityResult:
    """Results returned by :func:`heterogeneity_indices`.

    The main heterogeneity estimates are available through ``indices``.
    Complete regional diagnostics are stored in ``details``.
    """

    indices: pd.Series
    details: dict
    _input_order: tuple

    def __getitem__(self, partition):
        """Return H for one partition, e.g. ``H[\"X1\"]``."""
        return self.indices.loc[partition]

    def __repr__(self) -> str:
        if self.indices.empty:
            return "HeterogeneityResult\n\nNo heterogeneity indices were computed."
        table = self.indices.rename("H").to_frame()
        return "HeterogeneityResult\n\n" + table.to_string()

    def plot(self, partition=None, ax=None):
        """Plot raw regional sensitivity profiles.

        Parameters
        ----------
        partition : str or sequence of str, optional
            Partition(s) to plot. If omitted, all available partitions are
            plotted. Examples: ``H.plot(\"X1\")`` or
            ``H.plot([\"Y\", \"X1\", \"X2\"])``.
        ax : matplotlib.axes.Axes, optional
            Existing axes. Only valid when plotting one partition.

        Returns
        -------
        matplotlib.axes.Axes or numpy.ndarray
            Axes containing the plot(s).
        """
        return _plot_heterogeneity(self, partition=partition, ax=ax)


def _as_dataframe(inputs) -> pd.DataFrame:
    X = pd.DataFrame(inputs).reset_index(drop=True).copy()
    if X.shape[1] == 0:
        raise ValueError("'inputs' must contain at least one input variable.")
    if X.columns.has_duplicates:
        raise ValueError("'inputs' must have unique column names.")
    return X


def _as_series(values, name=None) -> pd.Series:
    if isinstance(values, pd.Series):
        s = values.reset_index(drop=True).copy()
    else:
        s = pd.Series(values).reset_index(drop=True)
    if name is not None and s.name is None:
        s.name = name
    return s


def _is_categorical(series: pd.Series) -> bool:
    """Identify natural categorical partitions.

    Object, string, boolean, pandas categorical, and binary variables are
    treated as categorical. Numeric variables with more than two levels are
    treated as continuous unless explicitly stored with pandas ``category``
    dtype. This avoids silently interpreting low-cardinality integer-valued
    continuous variables as categories.
    """
    non_missing = series.dropna()
    n_unique = non_missing.nunique()
    return (
        isinstance(series.dtype, pd.CategoricalDtype)
        or pd.api.types.is_object_dtype(series)
        or pd.api.types.is_string_dtype(series)
        or pd.api.types.is_bool_dtype(series)
        or n_unique <= 2
    )


def _make_regions(
    z: pd.Series,
    n_regions: int,
    name: str,
) -> tuple[pd.Series, bool]:
    categorical = _is_categorical(z)

    if categorical:
        regions = z.astype("category").cat.remove_unused_categories()
    else:
        try:
            regions = pd.qcut(z, q=n_regions, duplicates="drop")
        except ValueError as exc:
            raise ValueError(
                f"Failed to divide '{name}' into {n_regions} equal-frequency "
                f"regions: {exc}"
            ) from exc

    if not hasattr(regions, "cat") or len(regions.cat.categories) < 2:
        raise ValueError(
            f"At least two regions are required to compute heterogeneity for "
            f"'{name}'."
        )

    return regions, categorical


def _safe_output_variance(y: pd.Series) -> float | None:
    try:
        values = pd.to_numeric(y, errors="raise").to_numpy(dtype=float)
    except (TypeError, ValueError):
        return None
    if len(values) < 2:
        return 0.0
    return float(np.var(values, ddof=1))


def _mean_pairwise_tv(
    normalized_profiles: pd.DataFrame,
) -> tuple[float, pd.Series]:
    """Mean pairwise total-variation distance and input contributions."""
    profiles = normalized_profiles.to_numpy(dtype=float)
    n_regions, n_inputs = profiles.shape

    if n_regions < 2:
        raise ValueError("At least two normalized regional profiles are required.")

    contribution_sum = np.zeros(n_inputs, dtype=float)
    n_pairs = 0

    for r in range(n_regions - 1):
        for s in range(r + 1, n_regions):
            contribution_sum += 0.5 * np.abs(profiles[r] - profiles[s])
            n_pairs += 1

    contributions = contribution_sum / n_pairs
    H = float(contributions.sum())

    # For nonnegative compositional profiles, H is theoretically in [0, 1].
    if np.nanmin(profiles) >= -1e-12:
        H = float(np.clip(H, 0.0, 1.0))

    return H, pd.Series(
        contributions,
        index=normalized_profiles.columns,
        dtype=float,
        name="C_i",
    )


def _compute_partition(
    *,
    y: pd.Series,
    X: pd.DataFrame,
    z: pd.Series,
    partition_name,
    n_regions: int,
    remove_partition_input: bool,
) -> tuple[float, HeterogeneityDetail]:
    regions, partition_is_categorical = _make_regions(
        z,
        n_regions=n_regions,
        name=str(partition_name),
    )

    X_profile = X
    if remove_partition_input and partition_is_categorical:
        X_profile = X.drop(columns=[partition_name])
        if X_profile.shape[1] == 0:
            raise ValueError(
                f"Cannot compute H for categorical input '{partition_name}' "
                "because no other inputs remain in the regional sensitivity "
                "profile."
            )

    profile_rows = []
    counts = {}

    # Every intended region must be admissible. H is not computed on a silently
    # reduced subset of the requested partition.
    for region in regions.cat.categories:
        mask = regions == region
        n_in_region = int(mask.sum())
        counts[region] = n_in_region

        if n_in_region < _MIN_REGION_SIZE:
            raise ValueError(
                f"Region {region!r} of '{partition_name}' contains only "
                f"{n_in_region} observations; at least {_MIN_REGION_SIZE} are "
                "required for regional sensitivity analysis."
            )

        X_sub = X_profile.loc[mask]
        y_sub = y.loc[mask]

        variance = _safe_output_variance(y_sub)
        if variance is not None and variance < 1e-12:
            raise ValueError(
                f"The output is constant, or approximately constant, in region "
                f"{region!r} of '{partition_name}'. Regional variance-based "
                "sensitivity indices and H are therefore undefined for this "
                "partition."
            )

        try:
            result = sensitivity_indices(inputs=X_sub, output=y_sub)
            si_values = np.asarray(result.si, dtype=float).ravel()
        except Exception as exc:
            raise ValueError(
                f"Regional sensitivity calculation failed in region {region!r} "
                f"of '{partition_name}': {exc}"
            ) from exc

        if len(si_values) != X_profile.shape[1]:
            raise ValueError(
                f"Sensitivity calculation for region {region!r} of "
                f"'{partition_name}' returned {len(si_values)} indices for "
                f"{X_profile.shape[1]} inputs."
            )

        if not np.all(np.isfinite(si_values)):
            raise ValueError(
                f"Non-finite sensitivity indices were returned for region "
                f"{region!r} of '{partition_name}'."
            )

        # Remove numerical dust only. Material negative estimates are preserved
        # and flagged below rather than silently altered.
        si_values[np.abs(si_values) < 1e-12] = 0.0

        profile_rows.append(
            pd.Series(si_values, index=X_profile.columns, name=region, dtype=float)
        )

    raw = pd.DataFrame(profile_rows)
    raw.index.name = "region"

    regional_sums = raw.sum(axis=1)
    regional_sums.name = "sum_S_i"

    bad_sums = (~np.isfinite(regional_sums)) | (np.abs(regional_sums) < 1e-12)
    if bad_sums.any():
        bad_regions = list(regional_sums.index[bad_sums])
        raise ValueError(
            f"Regional sensitivity profiles for '{partition_name}' cannot be "
            "normalized because their sensitivity-index sum is zero or "
            f"non-finite in region(s) {bad_regions}."
        )

    normalized = raw.div(regional_sums, axis=0)

    if (normalized.to_numpy(dtype=float) < -1e-12).any():
        warnings.warn(
            f"Negative combined sensitivity indices were found in regional "
            f"profiles for '{partition_name}'. H is still calculated from the "
            "normalized profiles, but the strict [0, 1] total-variation "
            "interpretation assumes nonnegative sensitivity compositions.",
            RuntimeWarning,
            stacklevel=3,
        )

    H, contributions = _mean_pairwise_tv(normalized)

    region_counts = pd.Series(counts, dtype=int, name="n")
    region_counts.index.name = "region"

    detail = HeterogeneityDetail(
        raw_profiles=raw,
        normalized_profiles=normalized,
        regional_sums=regional_sums,
        region_counts=region_counts,
        individual_contributions=contributions,
    )
    return H, detail


def heterogeneity_indices(
    output,
    inputs,
    n_regions: int = _DEFAULT_N_REGIONS,
    custom_partition=None,
) -> HeterogeneityResult:
    """Calculate heterogeneity in regional sensitivity profiles.

    The heterogeneity index H measures how much the relative sensitivity
    profile of a model changes across regions. H is calculated as the mean
    pairwise total-variation distance between normalized regional combined
    sensitivity profiles.

    With no ``custom_partition``, the function performs a full standard scan:
    H_Y is calculated across regions of the output and H_Xi across regions of
    every input. Continuous partitioning variables are divided into
    ``n_regions`` equal-frequency regions; categorical variables use their
    observed categories.

    If ``custom_partition`` is supplied, only H_Z for that partition is
    calculated. A continuous custom partition is divided into ``n_regions``
    equal-frequency regions. A categorical custom partition uses its natural
    categories, in which case ``n_regions`` is ignored.

    Parameters
    ----------
    output : pandas.Series or array-like
        Model output vector.
    inputs : pandas.DataFrame or array-like
        Model input matrix. DataFrame column names are used as input names.
    n_regions : int, default 5
        Number of equal-frequency regions used for continuous partitioning
        variables.
    custom_partition : pandas.Series or array-like, optional
        User-defined partitioning variable Z. When provided, only H_Z is
        calculated. The partition is used only to assign observations to
        regions and is not added to the model inputs.

    Returns
    -------
    HeterogeneityResult
        ``H.indices`` contains the calculated heterogeneity indices.
        ``H.details`` contains raw and normalized regional profiles, regional
        sensitivity-index sums, observation counts, and input-level
        contributions for every calculated partition.

    Notes
    -----
    For a categorical input X_i, X_i is removed from its own regional
    sensitivity profiles because it is constant within each category.

    H_Y is not calculated for a categorical output. Partitioning a categorical
    output by its categories makes the output constant within every region, so
    regional variance-based sensitivity indices are undefined. H_Xi is still
    calculated for all inputs for which the regional analysis is admissible.

    Multi-level numeric categorical variables should use pandas ``category``
    dtype. Binary numeric variables are recognized as categorical
    automatically.
    """
    if not isinstance(n_regions, (int, np.integer)) or n_regions < 2:
        raise ValueError("'n_regions' must be an integer greater than or equal to 2.")

    y = _as_series(output, name="Y")
    X = _as_dataframe(inputs)

    if len(y) != len(X):
        raise ValueError(
            "'output' and 'inputs' must contain the same number of observations "
            f"({len(y)} != {len(X)})."
        )

    input_order = tuple(X.columns)
    indices = {}
    details = {}

    # ------------------------------------------------------------
    # Custom partition: calculate only H_Z.
    # ------------------------------------------------------------
    if custom_partition is not None:
        z = _as_series(custom_partition)
        if len(z) != len(y):
            raise ValueError(
                "'custom_partition' must contain the same number of observations "
                "as output and inputs."
            )

        partition_name = z.name if z.name is not None else "Z"
        custom_is_categorical = _is_categorical(z)

        if custom_is_categorical and n_regions != _DEFAULT_N_REGIONS:
            warnings.warn(
                "'n_regions' is ignored because 'custom_partition' is "
                "categorical. Its observed categories are used as regions.",
                UserWarning,
                stacklevel=2,
            )

        H_value, detail = _compute_partition(
            y=y,
            X=X,
            z=z,
            partition_name=partition_name,
            n_regions=n_regions,
            remove_partition_input=False,
        )
        indices[partition_name] = H_value
        details[partition_name] = detail

        return HeterogeneityResult(
            indices=pd.Series(indices, dtype=float, name="H").rename_axis("partition"),
            details=details,
            _input_order=input_order,
        )

    # ------------------------------------------------------------
    # Standard scan: H_Y and H_Xi for all inputs.
    # ------------------------------------------------------------
    if _is_categorical(y):
        warnings.warn(
            "H_Y was not calculated because the output is categorical. "
            "Partitioning a categorical output by its own categories makes "
            "the output constant within each region, so regional variance-based "
            "sensitivity indices are undefined. H_Xi will still be calculated "
            "for all inputs where the output varies within the resulting "
            "regions.",
            UserWarning,
            stacklevel=2,
        )
    else:
        try:
            H_y, detail_y = _compute_partition(
                y=y,
                X=X,
                z=y,
                partition_name="Y",
                n_regions=n_regions,
                remove_partition_input=False,
            )
            indices["Y"] = H_y
            details["Y"] = detail_y
        except ValueError as exc:
            warnings.warn(
                f"H_Y could not be calculated: {exc}",
                UserWarning,
                stacklevel=2,
            )
            indices["Y"] = np.nan

    for input_name in X.columns:
        try:
            H_x, detail_x = _compute_partition(
                y=y,
                X=X,
                z=X[input_name],
                partition_name=input_name,
                n_regions=n_regions,
                remove_partition_input=True,
            )
            indices[input_name] = H_x
            details[input_name] = detail_x
        except ValueError as exc:
            warnings.warn(
                f"H for input '{input_name}' could not be calculated: {exc}",
                UserWarning,
                stacklevel=2,
            )
            indices[input_name] = np.nan

    return HeterogeneityResult(
        indices=pd.Series(indices, dtype=float, name="H").rename_axis("partition"),
        details=details,
        _input_order=input_order,
    )


def _format_region_label(region) -> str:
    if isinstance(region, pd.Interval):
        left = f"{region.left:.3g}"
        right = f"{region.right:.3g}"
        return f"{left}-{right}"
    if isinstance(region, (float, np.floating)):
        return f"{region:.3g}"
    return str(region)


def _plot_heterogeneity(
    result: HeterogeneityResult,
    partition=None,
    ax=None,
):
    available = list(result.details)
    if not available:
        raise ValueError("The result contains no regional profiles to plot.")

    if partition is None:
        names = available
    elif isinstance(partition, str) or not hasattr(partition, "__iter__"):
        names = [partition]
    else:
        names = list(partition)

    missing = [name for name in names if name not in result.details]
    if missing:
        raise KeyError(
            f"Partition(s) {missing} are not available. Choose from {available}."
        )

    if ax is not None and len(names) != 1:
        raise ValueError("'ax' can only be supplied when plotting one partition.")

    input_order = list(result._input_order)
    cmap = plt.colormaps["terrain"]
    colors = {
        name: cmap(pos)
        for name, pos in zip(
            input_order,
            np.linspace(0.05, 0.95, max(len(input_order), 1)),
        )
    }

    if len(names) == 1:
        if ax is None:
            _, ax = plt.subplots(figsize=(7.0, 4.8))
        axes = np.array([ax], dtype=object)
    else:
        ncols = min(3, len(names))
        nrows = math.ceil(len(names) / ncols)
        _, grid = plt.subplots(
            nrows,
            ncols,
            figsize=(5.2 * ncols, 4.2 * nrows),
            squeeze=False,
        )
        axes = grid.ravel()

    used_inputs = []

    for axis, name in zip(axes, names):
        detail = result.details[name]
        raw = detail.raw_profiles
        order = [item for item in input_order if item in raw.columns]
        order += [item for item in raw.columns if item not in order]
        data = raw.loc[:, order]
        used_inputs.extend(item for item in order if item not in used_inputs)

        data.plot(
            kind="bar",
            stacked=True,
            ax=axis,
            color=[colors.get(item, cmap(0.5)) for item in order],
            edgecolor="white",
            linewidth=0.4,
            width=0.82,
            legend=False,
        )

        H_value = result.indices.loc[name]
        axis.set_title(f"{name}: H = {H_value:.3f}")
        axis.set_ylabel(r"Combined sensitivity index, $S_i$")
        axis.set_xlabel("Region")
        axis.set_xticklabels(
            [_format_region_label(region) for region in raw.index],
            rotation=45,
            ha="right",
        )
        axis.grid(axis="y", linestyle=":", alpha=0.30)
        axis.set_axisbelow(True)

    for axis in axes[len(names) :]:
        axis.remove()

    handles = [
        plt.Rectangle(
            (0, 0),
            1,
            1,
            facecolor=colors.get(name, cmap(0.5)),
            edgecolor="white",
            label=str(name),
        )
        for name in used_inputs
    ]

    if len(names) == 1:
        if handles:
            axes[0].legend(
                handles=handles,
                title="Inputs",
                bbox_to_anchor=(1.02, 1),
                loc="upper left",
            )
        axes[0].figure.tight_layout()
        return axes[0]

    if handles:
        axes[0].figure.legend(
            handles=handles,
            title="Inputs",
            loc="lower center",
            bbox_to_anchor=(0.5, 0.01),
            ncol=min(5, len(handles)),
            frameon=False,
        )
    axes[0].figure.subplots_adjust(bottom=0.16, hspace=0.48, wspace=0.28)
    return axes
