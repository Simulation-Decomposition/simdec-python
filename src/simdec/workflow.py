import matplotlib.pyplot as plt
import pandas as pd
import simdec as sd


def main():
    data = pd.read_csv("../../tests/data/stress.csv", sep=";", decimal=",")
    output_name, *v_names = list(data.columns)
    inputs, output = data[v_names], data[output_name]

    inputs = inputs.to_numpy()
    output = output.to_numpy()

    res = sd.significance(inputs=inputs, output=output)
    si = res.si

    res = sd.decomposition(inputs=inputs, output=output, significance=si)

    sd.visualization(bins=res.bins, states=res.states)
    plt.show()


if __name__ == "__main__":
    main()
