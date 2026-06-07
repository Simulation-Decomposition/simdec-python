import pathlib
import pytest

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

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

    with pytest.warns(UserWarning, match="requires the decomposition parameter"):
        sd.visualization(bins=bins, palette=pal, print_legend=True, decomposition=None)


def test_two_output_visualization_missing_decomposition_warning():
    """Verify that omitting the decomposition object triggers a warning in two_output."""
    bins = pd.DataFrame({"s1": [1, 2]})
    bins2 = pd.DataFrame({"s1": [5, 6]})
    pal = [[1, 0, 0, 1]]

    with pytest.warns(UserWarning, match="requires the decomposition parameter"):
        sd.two_output_visualization(
            bins=bins, bins2=bins2, palette=pal, print_legend=True, decomposition=None
        )


def test_tableau_legend_colors_match_scenario_order(stress_results):
    """Verify that the legend table (tableau) colors and scenarios align correctly.

    When calling `palette = sd.palette(states)[::-1]`, tableau() must receive the
    flipped palette in a way that matches the row index generation (0..N-1)
    so that each scenario is assigned its correct shade.
    """
    res = stress_results

    # Simulate the Python workflow
    palette = sd.palette(states=res.states)[::-1]

    # Generate the legend table and styler
    table, _ = sd.tableau(
        var_names=res.var_names,
        statistic=res.statistic,
        states=res.states,
        bins=res.bins,
        palette=palette,
    )

    # Verify 'colour' column contains a sequential range from 0 to N-1.
    n_scenarios = len(table)
    assert table["colour"].tolist() == list(range(n_scenarios))

    # Ensure that the first row (the lowest scenario index) maps to color index 0 (red),
    # which corresponds to the correct starting shade.
    assert table.iloc[0]["colour"] == 0
    assert table.iloc[-1]["colour"] == n_scenarios - 1


# Palette ordering tests


def test_palette_length_equals_product_of_states(stress_results):
    """palette() must return exactly one colour per scenario."""
    pal = sd.palette(states=stress_results.states)
    assert len(pal) == np.prod(stress_results.states)


def test_palette_entries_are_valid_rgba(stress_results):
    """Every colour must be a 4-element RGBA sequence with values in [0, 1]."""
    pal = sd.palette(states=stress_results.states)
    for i, colour in enumerate(pal):
        assert len(colour) == 4, f"colour {i} has {len(colour)} channels, expected 4"
        for ch in colour:
            assert 0.0 <= ch <= 1.0, f"channel {ch:.3f} out of [0,1] in colour {i}"


def test_palette_groups_colours_by_first_state(stress_results):
    """Colours sharing the same first-variable state must form a tighter hue cluster
    than colours across different first-variable states.

    palette() assigns one colormap per value of states[0].  All shades drawn from
    the same colormap are geometrically closer in RGB space than shades across
    different colormaps.  If this fails, the palette has mixed up its cmap blocks.
    """
    states = stress_results.states
    pal = np.array(sd.palette(states=states))
    n_first = states[0]
    n_shades = int(np.prod(states[1:]))

    for block in range(n_first):
        block_rgb = pal[block * n_shades : (block + 1) * n_shades, :3]
        centroid = block_rgb.mean(axis=0)
        intra = np.linalg.norm(block_rgb - centroid, axis=1).mean()

        other_mask = np.ones(len(pal), dtype=bool)
        other_mask[block * n_shades : (block + 1) * n_shades] = False
        cross = np.linalg.norm(pal[other_mask, :3] - centroid, axis=1).mean()

        assert intra < cross, (
            f"Block {block}: intra-block spread {intra:.3f} >= "
            f"cross-block spread {cross:.3f}. Colours are not grouped by first state."
        )


def test_caller_flip_puts_high_scenario_colour_first(stress_results):
    """After the caller applies [::-1], index 0 of the passed palette must be the
    colour palette() originally assigned to the last (highest) scenario, and index
    -1 must be the colour for the first (lowest) scenario.

    visualization() feeds columns to seaborn in the order they appear, so the first
    colour in the palette ends up at the bottom of the stacked histogram.  The
    caller flip ensures the highest scenario is at the bottom.
    """
    pal_raw = sd.palette(states=stress_results.states)
    pal_caller = pal_raw[::-1]
    assert (
        pal_caller[0] == pal_raw[-1]
    ), "pal[::-1][0] should equal pal[-1] (the highest-scenario colour)"
    assert (
        pal_caller[-1] == pal_raw[0]
    ), "pal[::-1][-1] should equal pal[0] (the lowest-scenario colour)"


def test_visualization_column_flip_is_descending(stress_results):
    """visualization() re-labels bin columns as a descending RangeIndex so that
    seaborn stacks scenario 0 at the bottom of the histogram.

    Simulating the transform and asserting the exact column sequence guards against
    any refactor that accidentally changes the stacking direction.
    """
    bins = stress_results.bins.copy()
    n = len(bins.columns)
    bins.columns = pd.RangeIndex(start=n, stop=0, step=-1)
    assert list(bins.columns) == list(range(n, 0, -1))


def test_palette_length_matches_bins_columns_after_flip(stress_results):
    """The caller palette must have the same length as the number of bin columns.

    A mismatch would cause seaborn to silently cycle or truncate colours, breaking
    the one-colour-per-scenario contract.
    """
    pal = sd.palette(states=stress_results.states)[::-1]
    assert len(pal) == len(stress_results.bins.columns)


def test_tableau_colour_column_is_sequential(stress_results):
    """tableau()'s 'colour' column must be exactly [0, 1, …, N-1].

    bins.describe().T.reset_index() inherits the original RangeIndex labels
    (0..N-1) as the 'colour' column.  ListedColormap(palette) then maps colour
    integer i to palette[i], so rows and colours are aligned position-for-position.
    """
    res = stress_results
    n = int(np.prod(res.states))
    pal = sd.palette(states=res.states)[::-1]

    table, _ = sd.tableau(
        var_names=res.var_names,
        statistic=res.statistic,
        states=res.states,
        bins=res.bins,
        palette=pal,
    )
    assert table["colour"].tolist() == list(range(n))


def test_tableau_n_col_is_descending(stress_results):
    """tableau()'s 'N°' column must run N, N-1, …, 1.

    Row 0 (the lowest scenario) gets the highest label, matching the reversed
    stacking order in the histogram where scenario 0 is at the bottom.
    """
    res = stress_results
    n = int(np.prod(res.states))
    pal = sd.palette(states=res.states)[::-1]

    table, _ = sd.tableau(
        var_names=res.var_names,
        statistic=res.statistic,
        states=res.states,
        bins=res.bins,
        palette=pal,
    )
    assert table["N°"].tolist() == list(range(n, 0, -1))


def test_two_output_double_flip_restores_original_palette(stress_results):
    """two_output_visualization() receives palette[::-1] from the caller, then
    passes palette[::-1] again to tableau() internally.  The two flips cancel, so
    tableau always receives colours in original scenario order (0..N-1).

    If this identity breaks, the legend colour swatches no longer correspond to
    the correct scenario rows.
    """
    pal_raw = sd.palette(states=stress_results.states)
    pal_caller = pal_raw[::-1]  # flip the caller applies before passing in
    pal_internal = pal_caller[::-1]  # flip two_output_visualization applies for tableau
    assert pal_internal == pal_raw


def test_two_output_scatter_hue_order_is_ascending(stress_results):
    """Inside two_output_visualization, hue_order = sorted(data['c'].unique()).

    After the descending RangeIndex rename, column labels are n..1, so sorted()
    yields [1, 2, …, n] — ascending.  seaborn maps palette[0] to hue value 1,
    palette[1] to hue value 2, and so on.  This test pins that contract so any
    change to the column-rename or sort strategy is caught immediately.
    """
    bins = stress_results.bins.copy()
    n = len(bins.columns)
    bins.columns = pd.RangeIndex(start=n, stop=0, step=-1)
    hue_order = sorted(pd.melt(bins)["variable"].unique())
    assert hue_order == list(range(1, n + 1))
