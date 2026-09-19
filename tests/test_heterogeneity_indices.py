import importlib

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

plt.switch_backend("Agg")

hi = importlib.import_module("simdec.heterogeneity_indices")


class _SensitivityResult:
    def __init__(self, si):
        self.si = np.asarray(si, dtype=float)


def _fake_sensitivity_indices(*, inputs, output):
    """Deterministic stand-in for API and result-structure tests."""
    X = pd.DataFrame(inputs).reset_index(drop=True)
    y = pd.Series(output).reset_index(drop=True)
    yy = pd.to_numeric(y, errors="raise").to_numpy(dtype=float)

    scores = []
    for column in X.columns:
        x = X[column]
        if not pd.api.types.is_numeric_dtype(x):
            xx = pd.factorize(x)[0].astype(float)
        else:
            xx = pd.to_numeric(x, errors="raise").to_numpy(dtype=float)

        if np.std(xx) < 1e-12 or np.std(yy) < 1e-12:
            score = 0.0
        else:
            score = float(np.corrcoef(xx, yy)[0, 1] ** 2)
            if not np.isfinite(score):
                score = 0.0

        # Positive floor keeps profiles normalizable in deliberately simple tests.
        scores.append(score + 0.02)

    return _SensitivityResult(scores)


@pytest.fixture
def example_data():
    rng = np.random.default_rng(123)
    n = 1000
    category = pd.Series(
        np.where(np.arange(n) % 2 == 0, "A", "B"),
        dtype="category",
        name="category",
    )
    X = pd.DataFrame(
        {
            "x1": rng.normal(size=n),
            "category": category,
            "x3": rng.normal(size=n),
        }
    )
    y = pd.Series(
        X["x1"]
        + (category == "B").astype(float) * 2.0 * X["x3"]
        + rng.normal(scale=0.2, size=n),
        name="Y",
    )
    return y, X


def test_public_package_export():
    import simdec

    assert callable(simdec.heterogeneity_indices)


def test_standard_call_computes_y_and_all_inputs(monkeypatch, example_data):
    monkeypatch.setattr(hi.simdec, "sensitivity_indices", _fake_sensitivity_indices)
    y, X = example_data

    H = hi.heterogeneity_indices(output=y, inputs=X)

    assert list(H.indices.index) == ["Y", "x1", "category", "x3"]
    assert H.indices.notna().all()
    assert set(H.details) == set(H.indices.index)
    assert H["x1"] == pytest.approx(H.indices["x1"])


def test_profiles_are_normalized_and_contributions_sum_to_h(monkeypatch, example_data):
    monkeypatch.setattr(hi.simdec, "sensitivity_indices", _fake_sensitivity_indices)
    y, X = example_data

    H = hi.heterogeneity_indices(output=y, inputs=X)

    for name, detail in H.details.items():
        assert np.allclose(detail.normalized_profiles.sum(axis=1), 1.0)
        assert np.isclose(detail.individual_contributions.sum(), H.indices[name])
        assert detail.regional_sums.index.equals(detail.region_counts.index)


def test_categorical_input_is_removed_from_its_own_profiles(monkeypatch, example_data):
    monkeypatch.setattr(hi.simdec, "sensitivity_indices", _fake_sensitivity_indices)
    y, X = example_data

    H = hi.heterogeneity_indices(output=y, inputs=X)

    detail = H.details["category"]
    assert "category" not in detail.raw_profiles.columns
    assert "category" not in detail.normalized_profiles.columns
    assert "category" not in detail.individual_contributions.index

    # The same categorical input remains available in profiles for other partitions.
    assert "category" in H.details["Y"].raw_profiles.columns
    assert "category" in H.details["x1"].raw_profiles.columns


def test_categorical_output_skips_h_y_but_continues(monkeypatch, example_data):
    monkeypatch.setattr(hi.simdec, "sensitivity_indices", _fake_sensitivity_indices)
    y, X = example_data
    y_binary = (y > y.median()).astype(int)

    with pytest.warns(UserWarning, match="output is categorical"):
        H = hi.heterogeneity_indices(output=y_binary, inputs=X)

    assert "Y" not in H.indices.index
    assert "Y" not in H.details
    assert list(H.indices.index) == ["x1", "category", "x3"]
    assert H.indices.notna().all()


def test_continuous_custom_partition_uses_n_regions(monkeypatch, example_data):
    monkeypatch.setattr(hi.simdec, "sensitivity_indices", _fake_sensitivity_indices)
    y, X = example_data
    z = pd.Series(np.linspace(0.0, 1.0, len(y)), name="temperature")

    H = hi.heterogeneity_indices(
        output=y,
        inputs=X,
        n_regions=5,
        custom_partition=z,
    )

    assert list(H.indices.index) == ["temperature"]
    detail = H.details["temperature"]
    assert len(detail.region_counts) == 5
    assert detail.region_counts.sum() == len(y)
    assert (detail.region_counts >= 100).all()


def test_categorical_custom_partition_uses_categories_and_warns_if_n_regions_changed(
    monkeypatch, example_data
):
    monkeypatch.setattr(hi.simdec, "sensitivity_indices", _fake_sensitivity_indices)
    y, X = example_data
    z = pd.Series(
        np.where(np.arange(len(y)) % 2 == 0, "OK", "Flood"),
        dtype="category",
        name="Flood regime",
    )

    with pytest.warns(UserWarning, match="n_regions.*ignored"):
        H = hi.heterogeneity_indices(
            output=y,
            inputs=X,
            n_regions=10,
            custom_partition=z,
        )

    assert list(H.indices.index) == ["Flood regime"]
    detail = H.details["Flood regime"]
    assert set(detail.region_counts.index.astype(str)) == {"OK", "Flood"}
    assert sorted(detail.region_counts.tolist()) == [500, 500]


def test_minimum_region_size_is_100(monkeypatch, example_data):
    monkeypatch.setattr(hi.simdec, "sensitivity_indices", _fake_sensitivity_indices)
    y, X = example_data
    z = pd.Series(
        ["rare"] * 99 + ["common"] * (len(y) - 99),
        dtype="category",
        name="regime",
    )

    with pytest.raises(ValueError, match="at least 100"):
        hi.heterogeneity_indices(
            output=y,
            inputs=X,
            custom_partition=z,
        )


def test_region_counts_are_exposed(monkeypatch, example_data):
    monkeypatch.setattr(hi.simdec, "sensitivity_indices", _fake_sensitivity_indices)
    y, X = example_data

    H = hi.heterogeneity_indices(output=y, inputs=X, n_regions=5)

    for name, detail in H.details.items():
        assert detail.region_counts.sum() == len(y)
        assert len(detail.region_counts) >= 2


def test_binary_analytical_tv_reference():
    # Controlled-model a=4 reference used in the manuscript: H_K = 6/13.
    profiles = pd.DataFrame(
        [
            [0.5, 0.5],
            [1.0 / 26.0, 25.0 / 26.0],
        ],
        index=["K=0", "K=1"],
        columns=["A", "B"],
    )

    H, contributions = hi._mean_pairwise_tv(profiles)

    assert H == pytest.approx(6.0 / 13.0)
    assert contributions.sum() == pytest.approx(H)


def test_plot_uses_stored_results_without_recalculation(monkeypatch, example_data):
    monkeypatch.setattr(hi.simdec, "sensitivity_indices", _fake_sensitivity_indices)
    y, X = example_data
    H = hi.heterogeneity_indices(output=y, inputs=X)

    def _should_not_run(*args, **kwargs):
        raise AssertionError("sensitivity_indices should not be called by plot()")

    monkeypatch.setattr(hi.simdec, "sensitivity_indices", _should_not_run)

    ax = H.plot("x1")
    assert ax is not None
    plt.close(ax.figure)

    axes = H.plot(["Y", "x1"])
    assert len(np.ravel(axes)) >= 2
    plt.close(np.ravel(axes)[0].figure)
