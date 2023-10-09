import bisect
import io

from bokeh.models.widgets.tables import NumberFormatter
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import panel as pn

import simdec as sd


# panel app
pn.extension(template="material")
pn.extension("tabulator")
pn.config.sizing_mode = "stretch_width"


pn.config.throttled = True
font_size = "12pt"


@pn.cache
def load_data(text_fname):
    if text_fname is None:
        text_fname = "tests/data/stress.csv"
    else:
        text_fname = io.BytesIO(text_fname)

    data = pd.read_csv(text_fname)
    pn.state.clear_caches()
    return data


@pn.cache
def column_inputs(data, output):
    inputs = list(data.columns)
    inputs.remove(output)
    return inputs


@pn.cache
def filtered_inputs(data, input_names):
    return data[input_names]


@pn.cache
def column_output(data):
    return list(data.columns)


@pn.cache
def filtered_output(data, output_name):
    return data[output_name]


@pn.cache
def significance(inputs, output):
    si = sd.significance(inputs=inputs, output=output).si
    return si


def significance_table(si, inputs):
    var_names = inputs.columns
    var_order = np.argsort(si)[::-1]
    var_names = var_names[var_order].tolist()

    si = list(si[var_order])
    sum_si = sum(si)

    var_names.append("Sum of Indices")
    si_numerics = si.copy()
    si.append(0)
    si_numerics.append(sum_si)

    d = {"Inputs": var_names, "Indices": si, "": si_numerics}
    df = pd.DataFrame(data=d)
    formatters = {
        "Indices": {"type": "progress", "max": sum_si, "color": "#007eff"},
        "": NumberFormatter(format="0.00"),
    }
    widget = pn.widgets.Tabulator(
        df,
        show_index=False,
        formatters=formatters,
        theme="bulma",
    )
    widget.style.apply(
        lambda x: ["font-style: italic"] * 3, axis=1, subset=df.index[-1]
    )
    widget.style.apply(lambda x: ["font-size: 11pt"] * len(si))
    return widget


@pn.cache
def explained_variance(si):
    return sum(si) + np.finfo(np.float64).eps


def filtered_si(significance_table, input_names):
    df = significance_table.value
    si = []
    for input_name in input_names:
        si.append(df.loc[df["Inputs"] == input_name, "Indices"])
    return np.asarray(si).flatten()


def explained_variance_80(significance_table):
    si = significance_table.value["Indices"]
    pos_80 = bisect.bisect_right(np.cumsum(si), 0.8)

    # pos_80 = max(2, pos_80)
    # pos_80 = min(len(si), pos_80)

    input_names = significance_table.value["Inputs"]
    return input_names.to_list()[: pos_80 + 1]


def decomposition(dec_limit, si, inputs, output):
    return sd.decomposition(
        inputs=inputs, output=output, significance=si, dec_limit=dec_limit
    )


def palette(res):
    return sd.palette(res.states)


def figure(res, palette, output_name):
    plt.close("all")
    fig, ax = plt.subplots()
    _ = sd.visualization(bins=res.bins, palette=palette, states=res.states, ax=ax)
    ax.set(xlabel=output_name)
    return fig


def tableau(res, palette):
    # use a notebook to see the styling
    _, styler = sd.tableau(
        statistic=res.statistic,
        var_names=res.var_names,
        states=res.states,
        bins=res.bins,
        palette=palette,
    )
    return styler


def tableau_states(res):
    # TODO re-use state formation default
    # Default states for 2 or 3
    states = res.states
    for i, state in enumerate(states):
        if isinstance(state, int):
            states: list
            if state == 2:
                states[i] = ["low", "high"]
            elif state == 3:
                states[i] = ["low", "medium", "high"]

    data = []
    for var_name, states, bin_edges in zip(res.var_names, res.states, res.bin_edges):
        for i, state in enumerate(states):
            data.append([var_name, state, bin_edges[i], bin_edges[i + 1]])

    table = pd.DataFrame(data, columns=["variable", "state", "min", "max"])
    table.set_index(["variable", "state"], inplace=True)

    styler = table.style
    styler.format(precision=2)
    styler.set_table_styles([{"selector": "th", "props": [("text-align", "center")]}])
    return styler


# Bindings
text_fname = pn.widgets.FileInput(sizing_mode="stretch_width", accept=".csv")

interactive_file = pn.bind(load_data, text_fname)

interactive_column_output = pn.bind(column_output, interactive_file)
selector_output = pn.widgets.Select(name="Output", options=interactive_column_output)
interactive_output = pn.bind(filtered_output, interactive_file, selector_output)

interactive_column_input = pn.bind(column_inputs, interactive_file, selector_output)
selector_inputs_sensitivity = pn.widgets.MultiSelect(
    name="Inputs", value=interactive_column_input, options=interactive_column_input
)
interactive_inputs = pn.bind(
    filtered_output, interactive_file, selector_inputs_sensitivity
)

interactive_significance = pn.bind(significance, interactive_inputs, interactive_output)
interactive_explained_variance = pn.bind(explained_variance, interactive_significance)

interactive_significance_table = pn.bind(
    significance_table, interactive_significance, interactive_inputs
)

interactive_explained_variance_80 = pn.bind(
    explained_variance_80, interactive_significance_table
)
selector_inputs_decomposition = pn.widgets.MultiChoice(
    name="Select inputs for decomposition",
    value=interactive_explained_variance_80,
    options=selector_inputs_sensitivity,
    solid=False,
)
interactive_inputs_decomposition = pn.bind(
    filtered_output, interactive_file, selector_inputs_decomposition
)

interactive_filtered_si = pn.bind(
    filtered_si, interactive_significance_table, selector_inputs_decomposition
)
interactive_filtered_explained_variance = pn.bind(
    explained_variance, interactive_filtered_si
)
indicator_explained_variance = pn.indicators.Number(
    name="Explained variance ratio from selected inputs:",
    value=interactive_filtered_explained_variance,
    title_size=font_size,
    font_size=font_size,
    format="{value:.2f}",
)


interactive_decomposition = pn.bind(
    decomposition,
    interactive_explained_variance,
    interactive_filtered_si,
    interactive_inputs_decomposition,
    interactive_output,
)
interactive_palette = pn.bind(palette, interactive_decomposition)
interactive_figure = pn.bind(
    figure, interactive_decomposition, interactive_palette, selector_output
)
interactive_tableau = pn.bind(tableau, interactive_decomposition, interactive_palette)
interactive_tableau_states = pn.bind(tableau_states, interactive_decomposition)

# App layout

top_description = """
## Data
"""

si_description = """
## Sensitivity Indices
"""

decomposition_description = """
## Decomposition
"""

table_description = """
## Scenario decomposition
"""

states_description = """
## Details on states
"""


pn_params = pn.layout.WidgetBox(
    top_description,
    text_fname,
    selector_output,
    selector_inputs_sensitivity,
    si_description,
    interactive_significance_table,
    decomposition_description,
    selector_inputs_decomposition,
    indicator_explained_variance,
    max_width=350,
    sizing_mode="stretch_width",
).servable(area="sidebar")

pn_app = pn.Column(
    pn.Row(
        pn.panel(interactive_figure, loading_indicator=True),
        pn.Column(
            table_description,
            pn.panel(interactive_tableau, loading_indicator=True),
            pn.Spacer(height=50),
            states_description,
            pn.panel(interactive_tableau_states, loading_indicator=True),
        ),
    )
).servable(title="Simulation Decomposition Dashboard")
