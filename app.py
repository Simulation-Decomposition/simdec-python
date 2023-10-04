import io

import matplotlib.pyplot as plt
import pandas as pd
import panel as pn

import simdec as sd


# panel app
pn.extension(template="material")
pn.config.throttled = True

text_fname = pn.widgets.FileInput(sizing_mode="stretch_width")
slider_dec_limit = pn.widgets.EditableFloatSlider(
    start=0.0, value=1.0, step=0.1, end=1.0, name="Explained variance ratio"
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
def significance(data, output_name=None, v_names=None):
    inputs, output = data[v_names], data[output_name]

    si = sd.significance(inputs=inputs, output=output).si
    return si, inputs, output


def decomposition(dec_limit, data):
    si, inputs, output = data
    return sd.decomposition(
        inputs=inputs, output=output, significance=si, dec_limit=dec_limit
    )


def palette(res):
    return sd.palette(res.states)


def figure(res, palette, output_name):
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


# Bindings

interactive_file = pn.bind(load_data, text_fname)

interactive_column_output = pn.bind(column_output, interactive_file)
selector_output = pn.widgets.Select(name="Output", options=interactive_column_output)
interactive_column_input = pn.bind(column_inputs, interactive_file, selector_output)
selector_inputs = pn.widgets.MultiSelect(
    name="Inputs", value=interactive_column_input, options=interactive_column_input
)

interactive_data = pn.bind(
    significance, interactive_file, selector_output, selector_inputs
)
interactive_decomposition = pn.bind(decomposition, slider_dec_limit, interactive_data)
interactive_palette = pn.bind(palette, interactive_decomposition)
interactive_figure = pn.bind(
    figure, interactive_decomposition, interactive_palette, selector_output
)
interactive_tableau = pn.bind(tableau, interactive_decomposition, interactive_palette)


top_description = """
# Parameters

Select a CSV file:
- comma delimited and with point decimal separator;
- first column is the output of the model;
- rest of the columns are the inputs.
"""

params_description = """
The following parameters can be adjusted:
"""

pn_params = pn.layout.WidgetBox(
    top_description,
    text_fname,
    params_description,
    slider_dec_limit,
    selector_output,
    selector_inputs,
    max_width=350,
    sizing_mode="stretch_width",
).servable(area="sidebar")

pn_app = pn.Column(pn.Row(interactive_figure, interactive_tableau)).servable(
    title="Simulation Decomposition Dashboard"
)
