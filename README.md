# Roblox Up-and-Coming top-10 forecaster

An entry for make.fun's **Predict Roblox's Up-and-Coming top 10** competition.

`main.py` reads the chart's history (`history.ndjson`) and writes one forecast
(`forecast.json`): for each of the top 10 places, a probability for every game
it names at that place, plus its top-10 guess.

The model is persistence with a spread: a game's expected place is its current
place, shifted up by its player-count growth and rank momentum over the last
14 hours; around that place it gets an exponentially decaying probability, and
15% of every place is left to the games the forecast does not name there.

Python 3 standard library only, deterministic, no network.
