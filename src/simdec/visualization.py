import copy
import functools
import itertools
from typing import Literal

import colorsys
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import pandas as pd
from pandas.io.formats.style import Styler

__all__ = ["visualization", "two_output_visualization", "tableau", "palette"]


SEQUENTIAL_PALETTES = [
    "#DC267F",
    "#E8EA2F",
    "#26DCD1",
    "#C552E4",
    "#3F45D0",
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


@functools.cache
def sequential_cmaps():
    cmaps = []
    for cmap in SEQUENTIAL_PALETTES:
        try:
            cmap_ = mpl.colormaps[cmap]
        except KeyError:
            color = mpl.colors.hex2color(cmap)
            cmap_ = single_color_to_colormap(color)
        cmaps.append(cmap_)
    return cmaps


def single_color_to_colormap(
    rgba_color: list[float] | str, *, factor: float = 0.5
) -> mpl.colors.LinearSegmentedColormap:
    """Create a linear colormap using a single color."""
    if isinstance(rgba_color, str):
        rgba_color = mpl.colors.hex2color(rgba_color)
    # discard alpha channel
    if len(rgba_color) == 4:
        *rgb_color, alpha = rgba_color
    else:
        alpha = 1.0
        rgb_color = rgba_color
        rgba_color = list(rgba_color) + [1]

    # lighten and darken from factor around single color
    hls_color = colorsys.rgb_to_hls(*rgb_color)

    lightness = hls_color[1]
    lightened_hls_color = (hls_color[0], lightness * (1 + factor), hls_color[2])
    lightened_rgb_color = list(colorsys.hls_to_rgb(*lightened_hls_color))

    darkened_hls_color = (hls_color[0], lightness * (1 - factor), hls_color[2])
    darkened_rgb_color = list(colorsys.hls_to_rgb(*darkened_hls_color))

    lightened_rgba_color = lightened_rgb_color + [alpha]
    darkened_rgba_color = darkened_rgb_color + [alpha]

    # convert to CMAP
    cmap = mpl.colors.LinearSegmentedColormap.from_list(
        "CustomSingleColor",
        [lightened_rgba_color, rgba_color, darkened_rgba_color],
        N=3,
    )
    return cmap


def palette(
    states: list[int], cmaps: list[mpl.colors.LinearSegmentedColormap] = None
) -> list[list[float]]:
    """Colour palette.

    The product of the states gives the number of scenarios. For each
    scenario, a colour is set.

    Parameters
    ----------
    states : list of int
        List of possible states for the considered parameter.
    cmaps : list of LinearSegmentedColormap
        List of colormaps. Must have the same number of colormaps as the number
        of first level of states.
    Returns
    -------
    palette : list of float of size (n, 4)
        List of colors corresponding to scenarios. RGBA formatted.
    """
    n_cmaps = states[0]
    if cmaps is None:
        cmaps = sequential_cmaps()[:n_cmaps]
    else:
        cmaps = cmaps[:n_cmaps]
        if len(cmaps) != n_cmaps:
            raise ValueError(
                f"Must have the same number of cmaps ({len(cmaps)}) as the "
                f"number of first states ({n_cmaps})"
            )

    colors = []
    # one palette per first level state, could use more palette when there are
    # many levels
    n_shades = int(np.prod(states[1:]))
    for i in range(n_cmaps):
        cmap = cmaps[i].resampled(n_shades)
        colors.append(cmap(np.linspace(0, 1, n_shades)))

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
            palette=palette,
            orient="h",
            order=list(bins.columns)[::-1],
            ax=ax,
        )
    else:
        raise ValueError("'kind' can only be 'histogram' or 'boxplot'")
    return ax


def two_output_visualization(
    *,
    bins: pd.DataFrame,
    bins2: pd.DataFrame,
    palette: list[list[float]],
    n_bins: str | int = "auto",
    output_name: str = "Output 1",
    output_name2: str = "Output 2",
    xlim: tuple[float, float] | None = None,
    ylim: tuple[float, float] | None = None,
    r_scatter: float = 1.0,
) -> tuple[plt.Figure, np.ndarray]:
    """Two-output visualization.

    Produces a 2x2 figure
    * top-left    : stacked histogram for *output 1* (axes hidden)
    * bottom-left : scatter of output 1 vs output 2, coloured by scenario
    * bottom-right: rotated stacked histogram for *output 2* (axes hidden)
    * top-right   : empty

    Parameters
    ----------
    bins : DataFrame
        Multidimensional bins for the primary output.
    bins2 : DataFrame
        Multidimensional bins for the secondary output.
    palette : list of int of size (n, 4)
        List of colours corresponding to scenarios.
    n_bins : str or int
        Number of bins for the histograms.
    output_name : str, default "Output 1"
        Axis label for the primary output.
    output_name2 : str, default "Output 2"
        Axis label for the secondary output.
    xlim : tuple of float, optional
        Limits for the primary output axis (scatter x / top histogram).
    ylim : tuple of float, optional
        Limits for the secondary output axis (scatter y / right histogram).
    r_scatter : float, default 1.0
        Fraction of data points shown in the scatter plot.

    Returns
    -------
    fig : Figure
    axs : ndarray of shape (2, 2)

    """
    fig, axs = plt.subplots(2, 2, sharex="col", sharey="row", figsize=(8, 8))

    axs[0, 1].axis("off")

    visualization(bins=bins.copy(), palette=palette, n_bins=n_bins, ax=axs[0, 0])
    if xlim is not None:
        axs[0, 0].set_xlim(xlim)
    axs[0, 0].set_box_aspect(1)
    axs[0, 0].axis("off")

    data = pd.concat([pd.melt(bins), pd.melt(bins2)["value"]], axis=1)
    data.columns = ["c", "x", "y"]
    if r_scatter < 1.0:
        data = data.sample(frac=r_scatter)

    sns.scatterplot(
        data=data,
        x="x",
        y="y",
        hue="c",
        palette=palette,
        ax=axs[1, 0],
        legend=False,
    )
    axs[1, 0].set(xlabel=output_name, ylabel=output_name2)
    if xlim is not None:
        axs[1, 0].set_xlim(xlim)
    if ylim is not None:
        axs[1, 0].set_ylim(ylim)
    axs[1, 0].set_box_aspect(1)

    sns.histplot(
        data,
        y="y",
        hue="c",
        multiple="stack",
        stat="probability",
        palette=palette,
        common_bins=True,
        common_norm=True,
        bins=40,
        legend=False,
        ax=axs[1, 1],
    )
    if ylim is not None:
        axs[1, 1].set_ylim(ylim)
    axs[1, 1].set_box_aspect(1)
    axs[1, 1].axis("off")

    fig.subplots_adjust(wspace=-0.015, hspace=0)
    return fig, axs


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
    statistic : ndarray of shape (n_factors, 1)
        Statistic in each bin.
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
    states_ = copy.deepcopy(states)
    for i, state in enumerate(states_):
        if isinstance(state, int):
            states_: list
            if state == 2:
                states_[i] = ["low", "high"]
            elif state == 3:
                states_[i] = ["low", "medium", "high"]

    # get the list of states
    gen_states = [range(x) if isinstance(x, int) else x for x in states_]
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

    table.insert(loc=0, column="N°", value=np.arange(1, stop=len(table) + 1)[::-1])

    # style the colour background with palette
    cmap = mpl.colors.ListedColormap(palette)
    styler = table.style
    styler.format(precision=2)
    styler.background_gradient(subset=["colour"], cmap=cmap)
    styler.format(lambda x: "", subset=["colour"])

    styler.set_table_styles([{"selector": "th", "props": [("text-align", "center")]}])
    return table, styler
