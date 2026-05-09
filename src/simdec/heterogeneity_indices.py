from .sensitivity_indices import sensitivity_indices
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

__all__ = ["heterogeneity_indices"]


def heterogeneity_indices(
    output: pd.Series,
    inputs: pd.DataFrame,
    split_variable: str | pd.Series,
    n_subdivisions: int | None = None,
    plot: bool = False,
) -> pd.DataFrame:
    """
    Compute sensitivity-based heterogeneity across subdivisions of a variable.

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
        If True, displays a stacked bar chart of regional sensitivities.

    Returns
    ----------
    summary : pd.Dataframe
        A summary of calculated heterogeneity indices.
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
        pd.api.types.is_categorical_dtype(z)
        or pd.api.types.is_object_dtype(z)
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
            res = sensitivity_indices(inputs=X_sub, output=y_sub)
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
        print(
            f"[heterogeneity_indices] Skipped {len(skipped)} region(s) of '{split_name}':"
        )
        for reg, n, reason in skipped:
            print(f"  - region={reg!r}, n={n}, reason={reason}")

    if len(regional_profiles) < 2:
        total_regions = len(regions.cat.categories)
        valid = len(regional_profiles)
        raise ValueError(
            f"Not enough valid subdivisions to compute heterogeneity: "
            f"{valid}/{total_regions} regions passed all checks for '{split_name}'.\n"
            f"Skipped regions:\n"
            + "\n".join(f"  {r!r}: n={n}, {reason}" for r, n, reason in skipped)
            + "\n\nTry: (1) reducing n_subdivisions, "
            "(2) using a different split_variable, or "
            "(3) ensuring more samples per region."
        )

    regional_si = pd.concat(regional_profiles, axis=1)

    res_global = sensitivity_indices(inputs=X, output=y)
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

    if plot:
        plot_order = summary.index[:-1]
        data_to_plot = regional_si.loc[plot_order].T

        cmap = plt.get_cmap("terrain")
        colors = [cmap(i) for i in np.linspace(0.05, 0.95, len(plot_order))]

        _ = data_to_plot.plot(
            kind="bar",
            stacked=True,
            figsize=(10, 6),
            color=colors,
            edgecolor="white",
            width=0.8,
        )

        plt.title(f"Sensitivity Profiles across {split_name}", fontsize=14)
        plt.ylabel("Variance Contribution", fontsize=12)
        plt.xlabel(f"Regions of {split_name}", fontsize=12)
        plt.legend(title="Input Variables", bbox_to_anchor=(1.05, 1), loc="upper left")
        plt.xticks(rotation=45)
        plt.grid(axis="y", linestyle="--", alpha=0.7)
        plt.tight_layout()
        plt.show()

    return summary
