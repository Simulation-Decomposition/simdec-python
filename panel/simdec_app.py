import bisect
import io
from pathlib import Path
import re

from bokeh.models import PrintfTickFormatter
from bokeh.models.widgets.tables import NumberFormatter
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pandas.io.formats.style import Styler
import panel as pn

import simdec as sd
from simdec.sensitivity_indices import SensitivityAnalysisResult
from simdec.visualization import sequential_cmaps, single_color_to_colormap

# panel app
pn.extension("tabulator", "floatpanel", notifications=True)

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

VALID_CHARACTERS = re.compile(r"[^A-Za-z0-9_ \-.]")

if Path("data/stress.csv").exists():
    DEFAULT_STRESS_CSV = Path("data/stress.csv")
else:
    # Fallback for if the zip was flattened or file is in the root
    DEFAULT_STRESS_CSV = Path("stress.csv")
GENERIC_ERROR_MSG = (
    "Could not parse the CSV file. "
    "Please check that it uses commas ',' as the delimiter "
    "and that column names contain no special characters."
)


@pn.cache
def load_data(text_fname):
    if text_fname is None:
        return pd.read_csv(DEFAULT_STRESS_CSV)
    try:
        raw = bytes(text_fname)
        first_line = raw.decode("utf-8").split("\n")[0].strip()
        if "," not in first_line:
            raise ValueError("No comma delimiter")
        col_names = [c.strip().strip('"').strip("'") for c in first_line.split(",")]
        if any(VALID_CHARACTERS.search(c) for c in col_names):
            raise ValueError("Bad column names")
        return pd.read_csv(io.BytesIO(raw))
    except Exception:
        pn.state.notifications.error(GENERIC_ERROR_MSG, duration=0)
        return pd.read_csv(DEFAULT_STRESS_CSV)


@pn.cache
def column_inputs(data, output):
    if data is None:
        return []
    inputs = list(data.columns)
    if output in inputs:
        inputs.remove(output)
    return inputs


@pn.cache
def column_output(data):
    if data is None:
        return []
    return list(data.columns)


@pn.cache
def filtered_data(data, output_name):
    if data is None or not output_name:
        return pd.DataFrame()
    try:
        if isinstance(output_name, str):
            return data[output_name]
        return data[output_name]
    except KeyError:
        return data.iloc[:, [0]]


@pn.cache
def sensitivity_indices_full(inputs, output):
    sensitivity_indices_ = sd.sensitivity_indices(inputs=inputs, output=output)
    return sensitivity_indices_


@pn.cache
def sensitivity_indices(sensitivity_indices_):
    if 0.01 < sum(sensitivity_indices_.si) < 2.0:
        indices = sensitivity_indices_.si
    else:
        indices = sensitivity_indices_.first_order
    return indices


@pn.cache
def sensitivity_indices_table(si, inputs):
    var_names = inputs.columns
    var_order = np.argsort(si)[::-1]
    var_names = var_names[var_order].tolist()

    si = list(si[var_order])
    sum_si = sum(si)

    # Insert labels and values at the top (index 0)
    var_names.insert(0, "Sum of Indices")

    si_numerics = si.copy()
    si.insert(0, 0)
    si_numerics.insert(0, sum_si)

    d = {"Inputs": var_names, "Indices": si, "Value": si_numerics}
    df = pd.DataFrame(data=d)

    formatters = {
        "Indices": {"type": "progress", "max": sum_si, "color": "#007eff"},
        "Value": NumberFormatter(format="0.00"),
    }

    widget = pn.widgets.Tabulator(
        df,
        show_index=False,
        formatters=formatters,
        theme="bulma",
        layout="fit_columns",
    )

    widget.style.apply(
        lambda x: (
            [
                "font-size: 11pt; font-style: italic; font-weight: bold; border-bottom: 2px solid #b5b5b5"
            ]
            * len(x)
            if x.name == 0
            else ["font-size: 11pt"] * len(x)
        ),
        axis=1,
    )
    return widget


@pn.cache
def explained_variance(si):
    return sum(si) + np.finfo(np.float64).eps


def filtered_si(sensitivity_indices_table, input_names):
    df = sensitivity_indices_table.value
    si = []
    for input_name in input_names:
        # Pull from "Value" explicit column
        si.append(df.loc[df["Inputs"] == input_name, "Value"])
    return np.asarray(si).flatten()


def explained_variance_80(sensitivity_indices_table):
    df = sensitivity_indices_table.value

    # Slice [1:] to skip the 'Sum of Indices' row at the top
    si_values = df["Value"].tolist()[1:]
    input_names = df["Inputs"].tolist()[1:]

    # Find the variables needed to reach 80% of explained variance
    total = sum(si_values)
    pos = bisect.bisect_left(np.cumsum(si_values), 0.8 * total)
    n_vars = min(pos + 1, 4)
    return input_names[:n_vars]


@pn.cache
def decomposition_(dec_limit, si, inputs, output):
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
        color_picker = pn.widgets.ColorPicker(name=str(state), value=color)
        color_picker.param.watch(update_colors_select, "value")
        color_picker_list.append(color_picker)
    color_pickers[:] = color_picker_list


@pn.cache
def palette_(states: list[list[str]], colors_picked: list[list[float]]):
    cmaps = [single_color_to_colormap(color_picked) for color_picked in colors_picked]
    states = [len(states_) for states_ in states]
    return sd.palette(states, cmaps=cmaps)[::-1]


@pn.cache
def n_bins_auto(res):
    min_ = np.nanmin(res.bins)
    max_ = np.nanmax(res.bins)
    return len(np.histogram_bin_edges(res.bins, bins="auto", range=(min_, max_))) - 1


def display_n_bins(kind):
    return False if kind not in ("Stacked histogram", "2 outputs") else True


def display_2_output(kind):
    return False if kind != "2 outputs" else True


@pn.cache
def xlim_auto(output):
    return (np.nanmin(output) * 0.95, np.nanmax(output) * 1.05)


@pn.cache
def figure_pn(
    res, res2, palette, n_bins, xlim, ylim, r_scatter, kind, output_name, output_2_name
):
    plt.close("all")

    if kind != "2 outputs":
        fig, ax = plt.subplots()

        kind = "histogram" if kind == "Stacked histogram" else "boxplot"
        _ = sd.visualization(
            bins=res.bins.copy(), palette=palette, n_bins=n_bins, kind=kind, ax=ax
        )
        ax.set(xlabel=output_name)
        if xlim is not None:
            ax.set_xlim(xlim)
    else:
        fig, _ = sd.two_output_visualization(
            bins=res.bins,
            bins2=res2.bins,
            palette=palette,
            n_bins=n_bins,
            output_name=output_name,
            output_name2=output_2_name,
            xlim=xlim,
            ylim=ylim,
            r_scatter=r_scatter,
        )

    return fig


@pn.cache
def states_from_data(res, inputs):
    return sd.states_expansion(states=res.states, inputs=inputs)


@pn.cache
def tableau_pn(res, states, palette):
    # use a notebook to see the styling
    _, styler = sd.tableau(
        statistic=res.statistic,
        var_names=res.var_names,
        states=res.states,
        bins=res.bins,
        palette=palette[::-1],  # reverse to match the order in the figure
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
    sensitivity_indices: SensitivityAnalysisResult,
    inputs: pd.DataFrame,
    scenario: Styler,
    states: Styler,
) -> io.StringIO:
    sio = io.StringIO()

    si = pd.DataFrame(sensitivity_indices.si.reshape(1, -1), columns=inputs.columns)
    first_order = pd.DataFrame(
        sensitivity_indices.first_order.reshape(1, -1), columns=inputs.columns
    )
    second_order = pd.DataFrame(
        sensitivity_indices.second_order, columns=inputs.columns
    )

    si.to_csv(sio, index=False)
    first_order.to_csv(sio, index=False)
    second_order.to_csv(sio, index=False)

    scenario.data.to_csv(sio)
    states.data.to_csv(sio)

    sio.seek(0)
    return sio


# Bindings
text_fname = pn.widgets.FileInput(sizing_mode="stretch_width", accept=".csv")

interactive_file = pn.bind(load_data, text_fname)

interactive_column_output = pn.bind(column_output, interactive_file)
# hack to make the default selection faster
interactive_output_ = pn.bind(lambda x: x[0] if x else None, interactive_column_output)
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

interactive_sensitivity_indices_full = pn.bind(
    sensitivity_indices_full, interactive_inputs, interactive_output
)
interactive_sensitivity_indices = pn.bind(
    sensitivity_indices, interactive_sensitivity_indices_full
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
    decomposition_,
    interactive_explained_variance,
    interactive_filtered_si,
    interactive_inputs_decomposition,
    interactive_output,
)

switch_type_visualization = pn.widgets.RadioButtonGroup(
    name="Type of visualization",
    options=["Stacked histogram", "Boxplot", "2 outputs"],
)
show_n_bins = pn.rx(display_n_bins)(switch_type_visualization)
show_2_output = pn.rx(display_2_output)(switch_type_visualization)

selector_2_output = pn.widgets.Select(
    name="Second output",
    value=None,
    options=interactive_column_output,
    visible=show_2_output,
)
interactive_2_output = pn.bind(filtered_data, interactive_file, selector_2_output)

interactive_sensitivity_indices_full_2 = pn.bind(
    sensitivity_indices_full, interactive_inputs, interactive_2_output
)
interactive_sensitivity_indices_2 = pn.bind(
    sensitivity_indices, interactive_sensitivity_indices_full_2
)
interactive_explained_variance_2 = pn.bind(
    explained_variance, interactive_sensitivity_indices_2
)

interactive_sensitivity_indices_table_2 = pn.bind(
    sensitivity_indices_table, interactive_sensitivity_indices_2, interactive_inputs
)

interactive_filtered_si_2 = pn.bind(
    filtered_si, interactive_sensitivity_indices_table_2, selector_inputs_decomposition
)

interactive_decomposition_2 = pn.bind(
    decomposition_,
    interactive_explained_variance_2,
    interactive_filtered_si_2,
    interactive_inputs_decomposition,
    interactive_2_output,
)

selector_r_scatter = pn.widgets.EditableFloatSlider(
    name="Share of data shown",
    start=0.0,
    end=1.0,
    value=1.0,
    step=0.1,
    # bar_color="#FFFFFF",  # does not work
    visible=show_2_output,
)

interactive_n_bins_auto = pn.rx(n_bins_auto)(interactive_decomposition)
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

interactive_ylim = pn.rx(xlim_auto)(interactive_2_output)
selector_ylim = pn.widgets.EditableRangeSlider(
    name="Y-lim",
    start=interactive_ylim.rx()[0],
    end=interactive_ylim.rx()[1],
    value=interactive_ylim.rx(),
    format="0.0[00]",
    step=0.1,
    visible=show_2_output,
)


def callback_xlim(start, end):
    selector_xlim.param.update(dict(value=(start, end)))


selector_xlim.param.watch_values(fn=callback_xlim, parameter_names=["start", "end"])


def callback_ylim(start, end):
    selector_ylim.param.update(dict(value=(start, end)))


selector_ylim.param.watch_values(fn=callback_ylim, parameter_names=["start", "end"])


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

interactive_palette = pn.bind(palette_, interactive_states, colors_select.param.value)

interactive_figure = pn.bind(
    figure_pn,
    interactive_decomposition,
    interactive_decomposition_2,
    interactive_palette,
    selector_n_bins,
    selector_xlim,
    selector_ylim,
    selector_r_scatter,
    switch_type_visualization,
    selector_output,
    selector_2_output,
)

interactive_tableau = pn.bind(
    tableau_pn, interactive_decomposition, interactive_states, interactive_palette
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
    switch_type_visualization,
    selector_2_output,
    selector_n_bins,
    selector_r_scatter,
    selector_xlim,
    selector_ylim,
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
        interactive_sensitivity_indices_full,
        interactive_inputs,
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
    # docs_button,
    info_button,
    issue_button,
    # logout_button,
)

template.header.append(header_area)

# serve the template
template.servable()
