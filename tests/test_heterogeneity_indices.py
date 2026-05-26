import pathlib
import pytest

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import simdec as sd


path_data = pathlib.Path(__file__).parent / "data"


@pytest.fixture(autouse=True)
def close_plots():
    yield
    plt.close("all")


@pytest.fixture
def dummy_data():
    rng = np.random.default_rng(42)
    n = 200

    inputs = pd.DataFrame(
        {
            "x1": rng.random(n),
            "x2": rng.random(n),
            "x3": rng.random(n),
            "cat_var": rng.choice(["A", "B", "C"], size=n),
        }
    )

    # Create a dummy output dependent on x1 and x2
    y = 2.0 * inputs["x1"] + 0.5 * inputs["x2"] + rng.normal(0, 0.1, n)
    return inputs, y


def test_heterogeneity_categorical_str(dummy_data):
    """Test splitting by a string column name (categorical)."""
    inputs, y = dummy_data

    res = sd.heterogeneity_indices(output=y, inputs=inputs, split_variable="cat_var")

    # Check object structure
    assert hasattr(res, "summary")
    assert hasattr(res, "regional_profiles")
    assert res.split_name == "cat_var"

    # Check DataFrame structures
    assert "Overall_SI" in res.summary.columns
    assert "Heterogeneity (across cat_var)" in res.summary.columns
    assert "SUM / TOTAL" in res.summary.index

    # 3 categories
    assert res.regional_profiles.shape[1] == 3
    assert list(res.regional_profiles.index) == ["x1", "x2", "x3", "cat_var"]


def test_heterogeneity_continuous_series(dummy_data):
    """Test splitting by passing a pandas Series (continuous)."""
    inputs, y = dummy_data
    split_series = inputs["x1"]

    res = sd.heterogeneity_indices(
        output=y, inputs=inputs, split_variable=split_series, n_subdivisions=4
    )

    assert res.split_name == "x1"
    assert res.regional_profiles.shape[1] == 4  # 4 quantiles


def test_heterogeneity_missing_column(dummy_data):
    """Test that a ValueError is raised when split_variable is not in inputs."""
    inputs, y = dummy_data

    with pytest.raises(ValueError, match="'missing_col' not found in inputs"):
        sd.heterogeneity_indices(output=y, inputs=inputs, split_variable="missing_col")


def test_heterogeneity_too_few_regions():
    """Test that a ValueError is raised when there are not enough valid subdivisions."""
    inputs = pd.DataFrame({"x1": [1, 2, 3, 4, 5], "cat": ["A", "B", "C", "D", "E"]})
    y = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])

    with pytest.raises(ValueError, match="Not enough valid subdivisions"):
        sd.heterogeneity_indices(output=y, inputs=inputs, split_variable="cat")


def test_heterogeneity_plot_argument(dummy_data):
    """Test that setting plot=True works without throwing an error."""
    inputs, y = dummy_data

    res = sd.heterogeneity_indices(
        output=y, inputs=inputs, split_variable="cat_var", plot=True
    )

    assert res is not None
    # Figure exists in the active pyplot state
    assert len(plt.get_fignums()) > 0


def test_plot_heterogeneity(dummy_data):
    """Test the independent plot_heterogeneity function."""
    inputs, y = dummy_data

    res = sd.heterogeneity_indices(output=y, inputs=inputs, split_variable="cat_var")

    ax = sd.plot_heterogeneity(res)

    assert isinstance(ax, plt.Axes)

    # Calculate the expected title format
    hetero_col_name = [c for c in res.summary.columns if "Heterogeneity" in c][0]
    total_hetero = res.summary.loc["SUM / TOTAL", hetero_col_name]
    expected_title = (
        f"Sensitivity Profiles across cat_var\n"
        f"(Total Heterogeneity: {total_hetero:.3f})"
    )

    assert ax.get_title() == expected_title
    assert ax.get_ylabel() == "Variance Contribution"
    assert ax.get_xlabel() == "Regions of cat_var"


def test_heterogeneity_real_data():
    """Integration test using the real stress.csv dataset from the project."""
    fname = path_data / "stress.csv"
    data = pd.read_csv(fname)
    output_name, *v_names = list(data.columns)

    inputs, output = data[v_names], data[output_name]

    res = sd.heterogeneity_indices(
        output=output, inputs=inputs, split_variable="R", n_subdivisions=2
    )

    assert res.split_name == "R"
    assert not res.summary.empty
    assert res.regional_profiles.shape[1] == 2
