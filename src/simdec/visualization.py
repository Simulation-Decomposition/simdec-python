import itertools
from typing import Literal

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import pandas as pd
from pandas.io.formats.style import Styler

__all__ = ["visualization", "tableau", "palette"]


sequential_palettes = [
    "Oranges",
    "Purples",
    "Reds",
    "Blues",
    "Greens",
    "YlOrBr",
    "YlOrRd",
    "OrRd",
    "PuRd",
    "RdPu",
    "BuPu",
    "GnBu",
    "PuBu",
    "YlGnBu",
    "PuBuGn",
    "BuGn",
    "YlGn",
    "Greys",
]


def palette(states: list[int]) -> list[list[float]]:
    """Colour palette.

    The product of the states gives the number of scenarios. For each
    scenario, a colour is set.

    Parameters
    ----------
    states : list of int
        List of possible states for the considered parameter.

    Returns
    -------
    palette : list of int of size (n, 4)
        List of colours corresponding to scenarios.
    """
    colors = []
    # one palette per first level state, could use more palette when there are
    # many levels
    n_shades = int(np.prod(states[1:]))
    for i in range(states[0]):
        palette_ = sequential_palettes[i]
        cmap = mpl.colormaps[palette_].resampled(n_shades + 1)
        colors.append(cmap(range(1, n_shades + 1)))

    return np.concatenate(colors).tolist()


def visualization(
    *,
    bins: pd.DataFrame,
    palette: list[list[float]],
    n_bins: str | int = "auto",
    kind: Literal["histogram", "boxplot"] = "histogram",
    ax=None,
) -> plt.Axes:
    """Histogram plot of scenarios.

    Parameters
    ----------
    bins : DataFrame
        Multidimensional bins.
    palette : list of int of size (n, 4)
        List of colours corresponding to scenarios.
    n_bins : str or int
        Number of bins or method from `np.histogram_bin_edges`.
    kind: {"histogram", "boxplot"}
        Histogram or Box Plot.
    ax : Axes, optional
        Matplotlib axis.

    Returns
    -------
    ax : Axes
        Matplotlib axis.

    """
    # needed to get the correct stacking order
    bins.columns = pd.RangeIndex(start=len(bins.columns), stop=0, step=-1)

    if kind == "histogram":
        ax = sns.histplot(
            bins,
            multiple="stack",
            stat="probability",
            palette=palette,
            common_bins=True,
            common_norm=True,
            bins=n_bins,
            legend=False,
            ax=ax,
        )
    elif kind == "boxplot":
        ax = sns.boxplot(
            bins,
            palette=palette[::-1],
            orient="h",
            order=list(bins.columns)[::-1],
            ax=ax,
        )
    else:
        raise ValueError("'kind' can only be 'histogram' or 'boxplot'")
    return ax


def tableau(
    *,
    var_names: list[str],
    statistic: np.ndarray,
    states: list[int | list[str]],
    bins: pd.DataFrame,
    palette: np.ndarray,
) -> tuple[pd.DataFrame, Styler]:
    """Generate a table of statistics for all scenarios.

    Parameters
    ----------
    var_names : list of str
        Variables name.
    states : list of int or list of str
        For each variable, number of states. Can either be a scalar or a list.

        ``states=[2, 2]`` or ``states=[['a', 'b'], ['low', 'high']]``
    bins : DataFrame
        Multidimensional bins.
    palette : list of int of size (n, 4)
        Ordered list of colours corresponding to each state.

    Returns
    -------
    table : DataFrame
        Summary table of statistics for the scenarios.
    styler : Styler
        Object to style the table with colours and formatting.
    """
    table = bins.describe(percentiles=[0.5]).T

    # get the index out to use a state id/colour
    table = table.reset_index()
    table.rename(columns={"index": "colour"}, inplace=True)

    # Default states for 2 or 3
    for i, state in enumerate(states):
        if isinstance(state, int):
            states: list
            if state == 2:
                states[i] = ["low", "high"]
            elif state == 3:
                states[i] = ["low", "medium", "high"]

    # get the list of states
    gen_states = [range(x) if isinstance(x, int) else x for x in states]
    states_ = np.asarray(list(itertools.product(*gen_states)))
    for i, var_name in enumerate(var_names):
        table.insert(loc=i + 1, column=var_name, value=states_[:, i])

    # groupby on the variable names
    table.set_index(list(var_names), inplace=True)

    proba = table["count"] / sum(table["count"])
    proba = np.asarray(proba)
    table["probability"] = proba
    table["mean"] = statistic.flatten()

    # only select/ordering interesting columns
    table = table[["colour", "std", "min", "mean", "max", "probability"]]

    table.insert(loc=0, column="N°", value=np.arange(1, stop=len(table) + 1))

    # style the colour background with palette
    cmap = mpl.colors.ListedColormap(palette[::-1])
    styler = table.style
    styler.format(precision=2)
    styler.background_gradient(subset=["colour"], cmap=cmap)
    styler.format(lambda x: "", subset=["colour"])

    styler.set_table_styles([{"selector": "th", "props": [("text-align", "center")]}])
    return table, styler
