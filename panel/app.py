import bisect
import io

from bokeh.models import PrintfTickFormatter
from bokeh.models.widgets.tables import NumberFormatter
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pandas.io.formats.style import Styler
import panel as pn
from panel.layout.gridstack import GridStack

import simdec as sd
from simdec.visualization import colormap_from_single_color


# panel app
pn.extension(template="material")
pn.extension("tabulator")
pn.extension("gridstack")

pn.config.sizing_mode = "stretch_width"
pn.config.throttled = True
font_size = "12pt"
blue_color = "#0072b5"


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


@pn.cache
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
        frozen_rows=[-1],
        # page_size=5,
        # pagination='local',
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


@pn.cache
def decomposition(dec_limit, si, inputs, output):
    return sd.decomposition(
        inputs=inputs,
        output=output,
        sensitivity_indices=si,
        dec_limit=dec_limit,
        auto_ordering=False,
    )


@pn.cache
def base_colors(res):
    all_colors = sd.palette(res.states)
    colors = all_colors[:: res.states[0]]
    colors = [mpl.colors.rgb2hex(color, keep_alpha=False) for color in colors]
    return colors


def update_colors_select(event):
    colors = [color_picker.value for color_picker in color_pickers]
    colors_select.param.update(
        options=colors,
        value=colors,
    )


def create_color_pickers(states, colors):
    color_picker_list = []
    for state, color in zip(states[0][::-1], colors):
        color_picker = pn.widgets.ColorPicker(name=state, value=color)
        color_picker.param.watch(update_colors_select, "value")
        color_picker_list.append(color_picker)
    color_pickers[:] = color_picker_list


@pn.cache
def palette(res, colors_picked):
    cmaps = [colormap_from_single_color(color_picked) for color_picked in colors_picked]
    return sd.palette(res.states, cmaps=cmaps)


@pn.cache
def n_bins_auto(res):
    min_ = np.nanmin(res.bins)
    max_ = np.nanmax(res.bins)
    return len(np.histogram_bin_edges(res.bins, bins="auto", range=(min_, max_))) - 1


def display_n_bins(kind):
    return False if kind != "Stacked histogram" else True


@pn.cache
def figure(res, palette, n_bins, kind, output_name):
    kind = "histogram" if kind == "Stacked histogram" else "boxplot"
    plt.close("all")
    fig, ax = plt.subplots()
    _ = sd.visualization(
        bins=res.bins, palette=palette, n_bins=n_bins, kind=kind, ax=ax
    )
    ax.set(xlabel=output_name)
    return fig


@pn.cache
def states_from_data(res, inputs):
    return sd.states_expansion(states=res.states, inputs=inputs)


@pn.cache
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


@pn.cache
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


def csv_data(
    sensitivity_indices: pn.widgets.Tabulator, scenario: Styler, states: Styler
) -> io.StringIO:
    sio = io.StringIO()

    sensitivity_indices.value.to_csv(sio)
    scenario.data.to_csv(sio)
    states.data.to_csv(sio)

    sio.seek(0)
    return sio


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

switch_histogram_boxplot = pn.widgets.RadioButtonGroup(
    name="Switch histogram - boxplot",
    options=["Stacked histogram", "Boxplot"],
)
show_n_bins = pn.bind(display_n_bins, switch_histogram_boxplot)

interactive_n_bins_auto = pn.bind(n_bins_auto, interactive_decomposition)
selector_n_bins = pn.widgets.EditableIntSlider(
    name="Number of bins",
    start=0,
    end=100,
    value=interactive_n_bins_auto,
    step=10,
    # bar_color="#FFFFFF",  # does not work
    format=PrintfTickFormatter(format="%d bins"),
    visible=show_n_bins,
)

interactive_states = pn.bind(
    states_from_data, interactive_decomposition, interactive_inputs_decomposition
)


interactive_base_colors = pn.bind(base_colors, interactive_decomposition)


color_pickers = pn.Card(title="Main color for states")
colors_select = pn.widgets.MultiSelect(
    value=interactive_base_colors,
    options=interactive_base_colors,
    name="Colors",
    visible=False,
)

dummy_color_pickers_bind = pn.bind(
    create_color_pickers, interactive_states, colors_select.param.value, watch=True
)

interactive_palette = pn.bind(
    palette, interactive_decomposition, colors_select.param.value
)

interactive_figure = pn.bind(
    figure,
    interactive_decomposition,
    interactive_palette,
    selector_n_bins,
    switch_histogram_boxplot,
    selector_output,
)

interactive_tableau = pn.bind(
    tableau, interactive_decomposition, interactive_states, interactive_palette
)
interactive_tableau_states = pn.bind(
    tableau_states, interactive_decomposition, interactive_states
)

# App layout

# Sidebar
pn_params = pn.layout.WidgetBox(
    pn.pane.Markdown("## Data", styles={"color": blue_color}),
    text_fname,
    selector_output,
    selector_inputs_sensitivity,
    pn.pane.Markdown("## Decomposition", styles={"color": blue_color}),
    selector_inputs_decomposition,
    indicator_explained_variance,
    pn.pane.Markdown("## Visualization", styles={"color": blue_color}),
    switch_histogram_boxplot,
    selector_n_bins,
    dummy_color_pickers_bind,
    color_pickers,
    max_width=350,
    sizing_mode="stretch_width",
).servable(area="sidebar")

# Main window
gstack = GridStack(sizing_mode="stretch_both", min_height=600)

gstack[0:3, 0:3] = pn.pane.Matplotlib(
    interactive_figure,
    tight=True,
    format="svg",
)

gstack[0:3, 3:5] = pn.Column(
    pn.pane.Markdown("## Scenarios", styles={"color": blue_color}),
    interactive_tableau,
)

gstack[3:5, 3:5] = pn.Column(
    pn.pane.Markdown("## Details on inputs' states", styles={"color": blue_color}),
    interactive_tableau_states,
)

gstack[3:5, 0:2] = pn.Column(
    pn.pane.Markdown("## Sensitivity Indices", styles={"color": blue_color}),
    interactive_sensitivity_indices_table,
)

gstack.servable(title="Simulation Decomposition Dashboard")

# Header
icon_size = "1.5em"

download_file_button = pn.widgets.FileDownload(
    callback=pn.bind(
        csv_data,
        interactive_sensitivity_indices_table,
        interactive_tableau,
        interactive_tableau_states,
    ),
    icon="file-download",
    icon_size=icon_size,
    button_type="success",
    filename="simdec.csv",
    width=150,
    height_policy="min",
    label="Download",
    styles={"margin-top": "0"},
    # align="center"  # does not work
)

info_button = pn.widgets.Button(
    icon="info-circle",
    icon_size=icon_size,
    button_type="light",
    name="More info",
    width=150,
    align="center",
)
info_button.js_on_click(code="""window.open('https://www.simdec.fi/')""")

issue_button = pn.widgets.Button(
    icon="bug",
    icon_size=icon_size,
    button_type="danger",
    name="Report an issue",
    width=200,
    align="center",
)
issue_button.js_on_click(
    code="""window.open('https://github.com/Simulation-Decomposition/simdec-python/issues')"""
)

logout_button = pn.widgets.Button(name="Log out", width=100)
logout_button.js_on_click(code="""window.location.href = './logout'""")

pn.Row(
    pn.HSpacer(),
    download_file_button,
    info_button,
    issue_button,
    # logout_button,
).servable(area="header")
