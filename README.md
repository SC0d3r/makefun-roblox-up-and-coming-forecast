# Roblox Up-and-Coming top-10 forecaster

Entry for make.fun's **roblox-up-and-coming-forecast-01** competition.

`main.py` reads the chart's history (`/input/history.ndjson`, `/input/task.json`)
and writes one forecast to `/output/forecast.json`: for each of the chart's top
10 places, a probability for every game named at that place, plus a top-10
guess. It is scored on every hourly read of Roblox's Up-and-Coming chart over
the 72 hours after entries close.

Model: persistence with a Laplace rank spread, shifted by each game's player
growth and rank momentum over a 16-hour lookback, with 15% of every place left
to the games the forecast does not name there. Python 3.13, standard library
only, deterministic.

Run locally:

```sh
mkdir -p out
MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Licence: MIT.
