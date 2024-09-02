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

import simdec as sd
from simdec.visualization import sequential_cmaps, single_color_to_colormap


# panel app
pn.extension("tabulator")
pn.extension("floatpanel")

pn.config.sizing_mode = "stretch_width"
pn.config.throttled = True
font_size = "12pt"
blue_color = "#4099da"

template = pn.template.FastGridTemplate(
    title="Simulation Decomposition Dashboard",
    # logo="_static/logo.gif",
    favicon="_static/favicon.png",
    meta_description="Simulation Decomposition",
    meta_keywords=(
        "Sensitivity Analysis, Visualization, Data Analysis, Auditing, "
        "Factors priorization, Colorization, Histogram"
    ),
    accent=blue_color,
    shadow=False,
    main_layout=None,
    theme_toggle=False,
    corner_radius=3,
    # save_layout=True,
)


@pn.cache
def load_data(text_fname):
    if text_fname is None:
        text_fname = "tests/data/stress.csv"
    else:
        text_fname = io.BytesIO(text_fname)

    data = pd.read_csv(text_fname)
    return data


@pn.cache
def column_inputs(data, output):
    inputs = list(data.columns)
    inputs.remove(output)
    return inputs


@pn.cache
def column_output(data):
    return list(data.columns)


@pn.cache
def filtered_data(data, output_name):
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
        layout="fit_columns",
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
    input_names = input_names.to_list()
    input_names.remove("Sum of Indices")
    return input_names[: pos_80 + 1]


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
    colors = []
    # ensure not more colors than states
    for cmap in sequential_cmaps()[: res.states[0]]:
        color = cmap(0.5)
        color = mpl.colors.rgb2hex(color, keep_alpha=False)
        colors.append(color)

    return colors


def update_colors_select(event):
    colors = [color_picker.value for color_picker in color_pickers]
    colors_select.param.update(
        options=colors,
        value=colors,
    )


def create_color_pickers(states, colors):
    color_picker_list = []
    for state, color in zip(states[0], colors):
        color_picker = pn.widgets.ColorPicker(name=state, value=color)
        color_picker.param.watch(update_colors_select, "value")
        color_picker_list.append(color_picker)
    color_pickers[:] = color_picker_list


@pn.cache
def palette(res, colors_picked):
    cmaps = [single_color_to_colormap(color_picked) for color_picked in colors_picked]
    # Reverse order as in figures high values take the first colors
    return sd.palette(res.states[::-1], cmaps=cmaps[::-1])


@pn.cache
def n_bins_auto(res):
    min_ = np.nanmin(res.bins)
    max_ = np.nanmax(res.bins)
    return len(np.histogram_bin_edges(res.bins, bins="auto", range=(min_, max_))) - 1


def display_n_bins(kind):
    return False if kind != "Stacked histogram" else True


@pn.cache
def xlim_auto(output):
    return (np.nanmin(output) * 0.95, np.nanmax(output) * 1.05)


@pn.cache
def figure(res, palette, n_bins, xlim, kind, output_name):
    kind = "histogram" if kind == "Stacked histogram" else "boxplot"
    plt.close("all")
    fig, ax = plt.subplots()
    _ = sd.visualization(
        bins=res.bins, palette=palette, n_bins=n_bins, kind=kind, ax=ax
    )
    ax.set(xlabel=output_name)
    ax.set_xlim(xlim)
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

    si_table = sensitivity_indices.value[["Inputs", ""]]
    si_table.rename(columns={"": "Indices"}, inplace=True)
    si_table.to_csv(sio, index=False)
    scenario.data.to_csv(sio)
    states.data.to_csv(sio)

    sio.seek(0)
    return sio


# Bindings
text_fname = pn.widgets.FileInput(sizing_mode="stretch_width", accept=".csv")

interactive_file = pn.bind(load_data, text_fname)

interactive_column_output = pn.bind(column_output, interactive_file)
# hack to make the default selection faster
interactive_output_ = pn.bind(lambda x: x[0], interactive_column_output)
selector_output = pn.widgets.Select(
    name="Output", value=interactive_output_, options=interactive_column_output
)
interactive_output = pn.bind(filtered_data, interactive_file, selector_output)

interactive_column_input = pn.bind(column_inputs, interactive_file, selector_output)
selector_inputs_sensitivity = pn.widgets.MultiSelect(
    name="Inputs", value=interactive_column_input, options=interactive_column_input
)
interactive_inputs = pn.bind(
    filtered_data, interactive_file, selector_inputs_sensitivity
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
    filtered_data, interactive_file, selector_inputs_decomposition
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

interactive_xlim = pn.rx(xlim_auto)(interactive_output)
selector_xlim = pn.widgets.EditableRangeSlider(
    name="X-lim",
    start=interactive_xlim.rx()[0],
    end=interactive_xlim.rx()[1],
    value=interactive_xlim.rx(),
    format="0.0[00]",
    step=0.1,
)


def callback_xlim(start, end):
    selector_xlim.param.update(dict(value=(start, end)))


selector_xlim.param.watch_values(fn=callback_xlim, parameter_names=["start", "end"])

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
    create_color_pickers,
    interactive_states,
    colors_select.param.value,
)

interactive_palette = pn.bind(
    palette, interactive_decomposition, colors_select.param.value
)

interactive_figure = pn.bind(
    figure,
    interactive_decomposition,
    interactive_palette,
    selector_n_bins,
    selector_xlim,
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
sidebar_area = pn.layout.WidgetBox(
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
    selector_xlim,
    dummy_color_pickers_bind,
    color_pickers,
    sizing_mode="stretch_width",
)

template.sidebar.append(sidebar_area)

# Main window
template.main[0:4, 0:6] = pn.panel(interactive_figure, loading_indicator=True)

template.main[0:4, 6:12] = pn.Column(
    pn.pane.Markdown("## Scenarios", styles={"color": blue_color}),
    pn.panel(interactive_tableau, loading_indicator=True),
)

template.main[4:7, 6:12] = pn.Column(
    pn.pane.Markdown("## Details on inputs' states", styles={"color": blue_color}),
    pn.panel(interactive_tableau_states, loading_indicator=True),
)

template.main[4:7, 0:4] = pn.Column(
    pn.pane.Markdown("## Sensitivity Indices", styles={"color": blue_color}),
    pn.panel(interactive_sensitivity_indices_table, loading_indicator=True),
    width_policy="fit",
    max_width=500,
)

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
    width=200,
    label="Download",
    align="center",
)

info_button = pn.widgets.Button(
    icon="info-circle",
    icon_size=icon_size,
    button_type="light",
    name="About",
    width=150,
    align="center",
)
info_button.js_on_click(code="""window.open('https://www.simdec.fi/')""")

issue_button = pn.widgets.Button(
    icon="message-report",
    icon_size=icon_size,
    button_type="light",
    name="Feedback",
    width=150,
    align="center",
)
issue_button.js_on_click(
    code="""window.open('https://github.com/Simulation-Decomposition/simdec-python/issues')"""
)

logout_button = pn.widgets.Button(name="Log out", width=100)
logout_button.js_on_click(code="""window.location.href = './logout'""")

docs_button = pn.widgets.Button(
    icon="notes",
    icon_size=icon_size,
    button_type="light",
    name="Docs",
    width=150,
    align="center",
)
docs = pn.Column(height=0, width=0)


def callback_docs(event):
    docs[:] = [
        pn.layout.FloatPanel(
            "This is some documentation",
            name="SimDec documentation",
            theme="info",
            contained=False,
            position="center",
        )
    ]


docs_button.on_click(callback_docs)


header_area = pn.Row(
    pn.HSpacer(),
    download_file_button,
    docs,
    docs_button,
    info_button,
    issue_button,
    # logout_button,
)

template.header.append(header_area)

# serve the template
template.servable()
