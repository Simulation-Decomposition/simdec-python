import pytest
import pandas as pd
import matplotlib.pyplot as plt
import simdec as sd


@pytest.fixture(autouse=True)
def close_plots():
    yield
    plt.close("all")


def test_visualization_histogram():
    bins = pd.DataFrame({"s1": [1, 2], "s2": [3, 4]})
    palette = [[1, 0, 0, 1], [0, 1, 0, 1]]
    ax = sd.visualization(bins=bins, palette=palette, kind="histogram")
    assert isinstance(ax, plt.Axes)


def test_visualization_boxplot():
    bins = pd.DataFrame({"s1": [1, 2], "s2": [3, 4]})
    palette = [[1, 0, 0, 1], [0, 1, 0, 1]]
    ax = sd.visualization(bins=bins, palette=palette, kind="boxplot")
    assert isinstance(ax, plt.Axes)


def test_visualization_invalid_kind():
    bins = pd.DataFrame({"s1": [1]})
    with pytest.raises(ValueError, match="'kind' can only be 'histogram' or 'boxplot'"):
        sd.visualization(bins=bins, palette=[[1, 0, 0, 1]], kind="invalid")


def test_two_output_visualization_returns_correct_types():
    bins = pd.DataFrame({"s1": [1, 2]})
    bins2 = pd.DataFrame({"s1": [5, 6]})
    palette = [[1, 0, 0, 1]]
    fig, axs = sd.two_output_visualization(bins=bins, bins2=bins2, palette=palette)
    assert isinstance(fig, plt.Figure)
    assert axs.shape == (2, 2)


def test_two_output_visualization_axis_labels():
    bins = pd.DataFrame({"s1": [1, 2]})
    bins2 = pd.DataFrame({"s1": [5, 6]})
    palette = [[1, 0, 0, 1]]
    _, axs = sd.two_output_visualization(
        bins=bins,
        bins2=bins2,
        palette=palette,
        output_name="Stress",
        output_name2="Displacement",
    )
    assert axs[1, 0].get_xlabel() == "Stress"
    assert axs[1, 0].get_ylabel() == "Displacement"


def test_two_output_visualization_r_scatter():
    bins = pd.DataFrame({"s1": list(range(100))})
    bins2 = pd.DataFrame({"s1": list(range(100))})
    palette = [[1, 0, 0, 1]]
    fig, axs = sd.two_output_visualization(
        bins=bins, bins2=bins2, palette=palette, r_scatter=0.5
    )
    assert isinstance(fig, plt.Figure)
