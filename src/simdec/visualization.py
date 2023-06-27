import itertools

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import pandas as pd
from pandas.io.formats.style import Styler

__all__ = ["visualization", "tableau"]


sequential_palettes = [
    "Purples",
    "Blues",
    "Greens",
    "Oranges",
    "Reds",
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


def visualization(
    *, bins: pd.DataFrame, states: np.ndarray
) -> tuple[plt.Axes, np.ndarray]:
    """

    Parameters
    ----------
    states : list of int or str
        ...
    bins : ...
        ...

    Returns
    -------

    """
    colors = []
    # one palette per first level state
    n_shades = np.prod(states[1:])
    for i in range(states[0]):
        palette = sequential_palettes[i]
        cmap = mpl.colormaps[palette].resampled(n_shades + 1)
        colors.append(cmap(range(1, n_shades + 1)))

    palette = np.concatenate(colors).tolist()

    # needed to get the correct stacking order
    bins.columns = pd.RangeIndex(start=np.prod(states), stop=0, step=-1)

    ax = sns.histplot(
        bins,
        multiple="stack",
        stat="probability",
        palette=palette,
        common_bins=True,
        common_norm=True,
        legend=False,
    )
    return ax, palette


def tableau(
    *,
    var_names: list[str],
    statistic: np.ndarray,
    states: list[int | str],
    bins: pd.DataFrame,
    palette: np.ndarray,
) -> tuple[pd.DataFrame, Styler]:
    """Generate a table of statistics for all scenarios.

    Parameters
    ----------
    var_names : list of str
        Variables name.
    states : list of int or str
        For each variable, number of states. Can either be a scalar or a list.

        ``states=[2, 2]`` or ``states=[['a', 'b'], ['low', 'high']]``
    bins : DataFrame
        ...
    palette : ndarray of shape (n_states, 3)
        Ordered list of colours corresponding to each state.

    Returns
    -------
    table : ...
    styler : ...
    """
    table = bins.describe(percentiles=[0.5]).T

    # get the index out to use a state id/colour
    table = table.reset_index()
    table.rename(columns={"index": "colour"}, inplace=True)

    # get the list of states
    gen_states = [range(x) if isinstance(x, int) else x for x in states]
    states_ = np.asarray(list(itertools.product(*gen_states)))
    for i, var_name in enumerate(var_names):
        table.insert(loc=i + 1, column=var_name, value=states_[:, i])

    # groupby on the variable names
    table = (
        table.groupby(var_names, group_keys=True, sort=False)
        .apply(lambda x: x)
        .droplevel(-1)
    )

    proba = table["count"] / sum(table["count"])
    proba = np.asarray(proba)
    table["probability"] = proba

    table["weighted mean"] = statistic.flatten()

    # only select/ordering interesting columns
    table = table[["colour", "std", "min", "50%", "max", "probability"]]

    # style the colour background with palette
    cmap = mpl.colors.ListedColormap(palette)
    styler = table.style.background_gradient(subset=["colour"], cmap=cmap)

    return table, styler
