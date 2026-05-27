from dataclasses import dataclass
import logging

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import simdec as sd

logger = logging.getLogger(__name__)

__all__ = ["heterogeneity_indices", "plot_heterogeneity"]


@dataclass
class HeterogeneityResult:
    summary: pd.DataFrame
    regional_profiles: pd.DataFrame
    split_name: str


def heterogeneity_indices(
    output: pd.Series,
    inputs: pd.DataFrame,
    split_variable: str | pd.Series,
    n_subdivisions: int | None = None,
    plot: bool = False,
) -> HeterogeneityResult:
    """Heterogeneity indices.

    Compute sensitivity-based heterogeneity across subdivisions
    of a variable.

    Parameters
    ----------
    output : pd.Series
        Model output vector.
    inputs : pd.DataFrame
        Input/feature matrix.
    split_variable : str or pd.Series
        Variable to split on. If string, must be a column in 'inputs'.
    n_subdivisions : int, optional
        Number of regions for continuous variables. Defaults to 4.
    plot : bool, default False
        If True, displays a stacked bar chart of regional sensitivity profiles
        by calling :func:`plot_heterogeneity`. The chart shows variance
        contributions of each input across subdivisions of ``split_variable``,
        ranked by global sensitivity indices. To capture the returned
        ``matplotlib.axes.Axes`` object, call :func:`plot_heterogeneity`
        directly on the result instead.

    Returns
    -------
    res : HeterogeneityResult
        An object with attributes:

        summary : DataFrame
            A summary of calculated heterogeneity indices.
        regional_profiles : DataFrame
            Regional sensitivity indices for each input across subdivisions.
        split_name : str
            The name of the variable used to split the data.

    """
    y = pd.Series(output).reset_index(drop=True)
    X = pd.DataFrame(inputs).reset_index(drop=True)

    if isinstance(split_variable, str):
        if split_variable not in X.columns:
            raise ValueError(f"'{split_variable}' not found in inputs.")
        z = X[split_variable].reset_index(drop=True)
        split_name = split_variable
    else:
        z = pd.Series(split_variable).reset_index(drop=True)
        split_name = getattr(split_variable, "name", "split_variable")

    unique_vals = z.dropna().unique()
    n_unique = len(unique_vals)

    # Determine if variable is categorical/binary
    is_categorical = (
        isinstance(z.dtype, pd.CategoricalDtype)
        or pd.api.types.is_object_dtype(z)
        or pd.api.types.is_string_dtype(z)
        or pd.api.types.is_bool_dtype(z)
        or n_unique <= 2
    )

    if is_categorical:
        regions = z.astype("category")
    else:
        q = n_subdivisions if n_subdivisions is not None else 4
        try:
            regions = pd.qcut(z, q=q, duplicates="drop")
        except ValueError as e:
            raise ValueError(
                f"Failed to bin '{split_name}' into {q} quantiles: {e}"
            ) from e

    regional_profiles = []
    skipped = []

    for region in regions.cat.categories:
        mask = regions == region
        n_in_region = mask.sum()

        if n_in_region < 10:
            # Need enough samples for meaningful sensitivity indices
            skipped.append((region, n_in_region, "too few samples (< 10)"))
            continue

        X_sub = X.loc[mask]
        y_sub = y.loc[mask]

        # Skip if output has zero or near-zero variance in this region
        if y_sub.var() < 1e-12:
            skipped.append((region, n_in_region, "output variance ≈ 0"))
            continue

        try:
            res = sd.sensitivity_indices(inputs=X_sub, output=y_sub)
            si_vals = np.asarray(res.si).ravel()

            # Guard against NaN/Inf from degenerate sensitivity computation
            if not np.all(np.isfinite(si_vals)):
                skipped.append((region, n_in_region, "non-finite SI values"))
                continue

            si_region = pd.Series(si_vals, index=X.columns, name=region)
            regional_profiles.append(si_region)

        except Exception as e:
            skipped.append((region, n_in_region, f"exception: {e}"))
            continue

    if skipped:
        logger.info("Skipped %d region(s) of '%s':", len(skipped), split_name)
        for reg, n, reason in skipped:
            logger.info("  - region=%r, n=%d, reason=%s", reg, n, reason)

    if len(regional_profiles) < 2:
        total_regions = len(regions.cat.categories)
        valid = len(regional_profiles)
        raise ValueError(
            f"Not enough valid subdivisions to compute heterogeneity: "
            f"{valid}/{total_regions} regions passed all checks for '{split_name}'.\n"
            f"Skipped regions:\n"
            "\n".join(f"  {r!r}: n={n}, {reason} " for r, n, reason in skipped),
            "\n\nTry: (1) reducing n_subdivisions, "
            "(2) using a different split_variable, or "
            "(3) ensuring more samples per region.",
        )

    regional_si = pd.concat(regional_profiles, axis=1)

    res_global = sd.sensitivity_indices(inputs=X, output=y)
    overall_si = pd.Series(
        np.asarray(res_global.si).ravel(),
        index=X.columns,
        name="Overall_SI",
    )

    # Heterogeneity = 2 × population std dev across regions
    hetero_scores = 2 * regional_si.std(axis=1, ddof=0)
    total_hetero = hetero_scores.mean()

    hetero_col_name = f"Heterogeneity (across {split_name})"
    summary = pd.DataFrame(
        {"Overall_SI": overall_si, hetero_col_name: hetero_scores}
    ).sort_values(by=hetero_col_name, ascending=False)
    summary.loc["SUM / TOTAL"] = [overall_si.sum(), total_hetero]

    result = HeterogeneityResult(summary, regional_si, split_name)

    if plot:
        plot_heterogeneity(result)

    return result


def plot_heterogeneity(result: HeterogeneityResult, ax: plt.Axes = None) -> plt.Axes:
    """Plot regional sensitivity profiles.

    Parameters
    ----------
    result : HeterogeneityResult
        The result object from heterogeneity_indices.
    ax : matplotlib.axes.Axes, optional
        Existing axes to plot on.

    Returns
    -------
    ax : matplotlib.axes.Axes
        The axes with the plot.

    """
    summary = result.summary
    regional_si = result.regional_profiles
    split_name = result.split_name

    hetero_col_name = [c for c in summary.columns if "Heterogeneity" in c][0]
    total_hetero = summary.loc["SUM / TOTAL", hetero_col_name]

    plot_order = summary.index[summary.index != "SUM / TOTAL"]
    plot_order = (
        summary.loc[plot_order].sort_values(by="Overall_SI", ascending=False).index
    )

    cmap = plt.colormaps["terrain"]
    colors = [cmap(i) for i in np.linspace(0.05, 0.95, len(regional_si.index))]

    data_to_plot = regional_si.loc[plot_order].T

    if ax is None:
        _, ax = plt.subplots(figsize=(10, 6))

    data_to_plot.plot(
        kind="bar",
        stacked=True,
        ax=ax,
        color=colors,
        edgecolor="white",
        width=0.8,
    )

    ax.set_title(
        f"Sensitivity Profiles across {split_name}\n"
        f"(Total Heterogeneity: {total_hetero:.3f})",
        fontsize=10,
    )

    ax.set_ylabel("Variance Contribution", fontsize=8)
    ax.set_xlabel(f"Regions of {split_name}", fontsize=8)

    ax.legend(
        title="Inputs (Ranked by Global SI)",
        bbox_to_anchor=(1.05, 1),
        loc="upper left",
    )

    ax.tick_params(axis="x", labelrotation=45)
    ax.grid(axis="y", linestyle="--", alpha=0.7)

    if plt.get_backend().lower() != "agg":
        plt.tight_layout()

    return ax
