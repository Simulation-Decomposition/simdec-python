import matplotlib as mpl
import numpy as np
import seaborn as sns
import pandas as pd

__all__ = ["visualization"]

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


def visualization(decomposition: np.ndarray, bins: pd.DataFrame, states: np.ndarray):
    colors = []
    # one palette per first level state
    n_shades = np.prod(states[1:])
    for i in range(states[0]):
        palette = sequential_palettes[i]
        cmap = mpl.colormaps[palette].resampled(n_shades + 1)
        colors.append(cmap(range(1, n_shades + 1)))

    palette = np.concatenate(colors)

    sns.histplot(
        bins, multiple="stack", palette=palette, common_bins=True, common_norm=True
    )