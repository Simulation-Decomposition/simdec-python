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
    bins: pd.DataFrame, states: np.ndarray
) -> tuple[plt.Axes, np.ndarray]:
    colors = []
    # one palette per first level state
    n_shades = np.prod(states[1:])
    for i in range(states[0]):
        palette = sequential_palettes[i]
        cmap = mpl.colormaps[palette].resampled(n_shades + 1)
        colors.append(cmap(range(1, n_shades + 1)))

    palette = np.concatenate(colors)

    # needed to get the correct stacking order
    bins.columns = pd.RangeIndex(start=np.prod(states), stop=0, step=-1)

    ax = sns.histplot(
        bins,
        multiple="stack",
        palette=palette,
        common_bins=True,
        common_norm=True,
        legend=False,
    )
    return ax, palette


def tableau(
    var_names: list[str], states: np.ndarray, bins: pd.DataFrame, palette: np.ndarray
) -> tuple[pd.DataFrame, Styler]:
    table = bins.describe().T

    # add colour column
    table = table.reset_index()
    table.rename(columns={"index": "colour"}, inplace=True)
    # style the colour background with palette
    cmap = mpl.colors.ListedColormap(palette)
    styler = table.style.hide(axis="index").background_gradient(
        subset=["colour"], cmap=cmap
    )

    # get the list of states
    gen_states = [range(x) if isinstance(x, int) else x for x in states]
    states_ = np.asarray(list(itertools.product(*gen_states)))
    for i, var_name in enumerate(var_names):
        table.insert(loc=i + 1, column=var_name, value=states_[:, i])

    return table, styler
