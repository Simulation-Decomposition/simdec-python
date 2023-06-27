from pathlib import Path
from typing_extensions import Annotated


import pandas as pd
import typer

import simdec as sd

app = typer.Typer()


@app.command()
def main(
    data: Annotated[
        Path,
        typer.Option(
            exists=True,
            file_okay=True,
            dir_okay=False,
            writable=False,
            readable=True,
            resolve_path=True,
        ),
    ]
):
    data = pd.read_csv(data, sep=";", decimal=",")
    output_name, *v_names = list(data.columns)
    inputs, output = data[v_names], data[output_name]

    res = sd.significance(inputs=inputs, output=output)
    si = res.si

    res = sd.decomposition(inputs=inputs, output=output, significance=si)

    ax, palette = sd.visualization(bins=res.bins, states=res.states)

    # use a notebook to see the styling
    table, styler = sd.tableau(
        statistic=res.statistic,
        var_names=res.var_names,
        states=res.states,
        bins=res.bins,
        palette=palette,
    )
    print(styler.to_html())
