import pytest
import pathlib
import numpy as np
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


# Setup data path to match your decomposition tests
path_data = pathlib.Path(__file__).parent / "data"


@pytest.fixture
def stress_results():
    """Runs the actual decomposition to get a real result object."""
    fname = path_data / "stress.csv"
    data = pd.read_csv(fname)
    output_name, *v_names = list(data.columns)
    inputs, output = data[v_names], data[output_name]
    si = np.array([0.04, 0.50, 0.11, 0.28])

    res = sd.decomposition(
        inputs=inputs, output=output, sensitivity_indices=si, dec_limit=1
    )
    return res


def test_visualization_with_legend(stress_results):
    """Verify visualization works with print_legend using live decomposition results."""
    # Generate palette based on the live results
    palette = sd.palette(stress_results.states)

    # Test single visualization
    ax = sd.visualization(
        bins=stress_results.bins,
        palette=palette,
        print_legend=True,
        decomposition=stress_results,
    )

    assert isinstance(ax, plt.Axes)
    # Check that the columns were handled (RangeIndex is applied inside visualization)
    assert isinstance(stress_results.bins.columns, pd.RangeIndex)


def test_two_output_visualization_with_legend(stress_results):
    """Verify two_output works with print_legend using live decomposition results."""
    palette = sd.palette(stress_results.states)

    # Using the same bins for both axes for testing purposes
    fig, axs = sd.two_output_visualization(
        bins=stress_results.bins,
        bins2=stress_results.bins,
        palette=palette,
        print_legend=True,
        decomposition=stress_results,
        output_name="Primary",
        output_name2="Secondary",
    )

    assert isinstance(fig, plt.Figure)
    assert axs.shape == (2, 2)
    assert axs[1, 0].get_xlabel() == "Primary"
    assert axs[1, 0].get_ylabel() == "Secondary"


def test_visualization_missing_decomposition_warning():
    """Verify that omitting the decomposition object triggers a warning, not a crash."""
    # Using small dummy data for a quick standalone check
    bins = pd.DataFrame({"s1": [1, 2]})
    pal = [[1, 0, 0, 1]]

    with pytest.warns(UserWarning, match="requires the decomposition object"):
        sd.visualization(bins=bins, palette=pal, print_legend=True, decomposition=None)
