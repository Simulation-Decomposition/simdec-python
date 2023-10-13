import bisect
import io

from bokeh.models import PrintfTickFormatter
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
def sensitivity_indices(inputs, output):
    sensitivity_indices = sd.sensitivity_indices(inputs=inputs, output=output)
    if 0.01 < sum(sensitivity_indices.si) < 2.0:
        indices = sensitivity_indices.si
    else:
        indices = sensitivity_indices.first_order
    return indices


def sensitivity_indices_table(si, inputs):
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


def filtered_si(sensitivity_indices_table, input_names):
    df = sensitivity_indices_table.value
    si = []
    for input_name in input_names:
        si.append(df.loc[df["Inputs"] == input_name, "Indices"])
    return np.asarray(si).flatten()


def explained_variance_80(sensitivity_indices_table):
    si = sensitivity_indices_table.value["Indices"]
    pos_80 = bisect.bisect_right(np.cumsum(si), 0.8)

    # pos_80 = max(2, pos_80)
    # pos_80 = min(len(si), pos_80)

    input_names = sensitivity_indices_table.value["Inputs"]
    return input_names.to_list()[: pos_80 + 1]


def decomposition(dec_limit, si, inputs, output):
    return sd.decomposition(
        inputs=inputs,
        output=output,
        sensitivity_indices=si,
        dec_limit=dec_limit,
        auto_ordering=False,
    )


def palette(res):
    return sd.palette(res.states)


def n_bins_auto(res):
    min_ = np.nanmin(res.bins)
    max_ = np.nanmax(res.bins)
    return len(np.histogram_bin_edges(res.bins, bins="auto", range=(min_, max_))) - 1


def display_n_bins(kind):
    if kind != "Stacked histogram":
        return

    return selector_n_bins


def figure(res, palette, n_bins, kind, output_name):
    kind = "histogram" if kind == "Stacked histogram" else "boxplot"
    plt.close("all")
    fig, ax = plt.subplots()
    _ = sd.visualization(
        bins=res.bins, palette=palette, n_bins=n_bins, kind=kind, ax=ax
    )
    ax.set(xlabel=output_name)
    return fig


def states_from_data(res, inputs):
    return sd.states_expansion(states=res.states, inputs=inputs)


def tableau(res, states, palette):
    # use a notebook to see the styling
    _, styler = sd.tableau(
        statistic=res.statistic,
        var_names=res.var_names,
        states=states,
        bins=res.bins,
        palette=palette,
    )
    return styler


def tableau_states(res, states):
    data = []
    for var_name, states_, bin_edges in zip(res.var_names, states, res.bin_edges):
        for i, state in enumerate(states_):
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

interactive_sensitivity_indices = pn.bind(
    sensitivity_indices, interactive_inputs, interactive_output
)
interactive_explained_variance = pn.bind(
    explained_variance, interactive_sensitivity_indices
)

interactive_sensitivity_indices_table = pn.bind(
    sensitivity_indices_table, interactive_sensitivity_indices, interactive_inputs
)

interactive_explained_variance_80 = pn.bind(
    explained_variance_80, interactive_sensitivity_indices_table
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
    filtered_si, interactive_sensitivity_indices_table, selector_inputs_decomposition
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

switch_histogram_boxplot = pn.widgets.RadioButtonGroup(
    name="Switch histogram - boxplot",
    options=["Stacked histogram", "Boxplot"],
)

interactive_n_bins_auto = pn.bind(n_bins_auto, interactive_decomposition)
selector_n_bins = pn.widgets.EditableIntSlider(
    name="Number of bins",
    start=0,
    end=100,
    value=interactive_n_bins_auto,
    step=10,
    # bar_color="#FFFFFF",  # does not work
    format=PrintfTickFormatter(format="%d bins"),
)
conditional_selector_n_bins = pn.bind(display_n_bins, switch_histogram_boxplot)


interactive_figure = pn.bind(
    figure,
    interactive_decomposition,
    interactive_palette,
    selector_n_bins,
    switch_histogram_boxplot,
    selector_output,
)


interactive_states = pn.bind(
    states_from_data, interactive_decomposition, interactive_inputs_decomposition
)
interactive_tableau = pn.bind(
    tableau, interactive_decomposition, interactive_states, interactive_palette
)
interactive_tableau_states = pn.bind(
    tableau_states, interactive_decomposition, interactive_states
)

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
## Scenarios
"""

states_description = """
## Details on inputs' states
"""


pn_params = pn.layout.WidgetBox(
    pn.pane.Markdown(top_description, styles={"color": "#0072b5"}),
    text_fname,
    selector_output,
    selector_inputs_sensitivity,
    pn.pane.Markdown(decomposition_description, styles={"color": "#0072b5"}),
    selector_inputs_decomposition,
    indicator_explained_variance,
    pn.pane.Markdown("## Visualization", styles={"color": "#0072b5"}),
    switch_histogram_boxplot,
    conditional_selector_n_bins,
    max_width=350,
    sizing_mode="stretch_width",
).servable(area="sidebar")

pn_app = pn.Column(
    pn.Row(
        pn.Column(
            pn.panel(
                pn.pane.Matplotlib(
                    interactive_figure,
                    tight=True,
                    format="svg",
                    sizing_mode="stretch_both",
                    max_height=500,
                    height_policy="min",
                )
            ),
            pn.Spacer(height=50),
            pn.pane.Markdown(si_description, styles={"color": "#0072b5"}),
            pn.Column(interactive_sensitivity_indices_table, width=400),
        ),
        pn.Column(
            pn.pane.Markdown(table_description, styles={"color": "#0072b5"}),
            pn.panel(interactive_tableau),
            pn.Spacer(height=125),
            pn.pane.Markdown(states_description, styles={"color": "#0072b5"}),
            pn.panel(interactive_tableau_states),
        ),
    )
).servable(title="Simulation Decomposition Dashboard")
