#!/usr/bin/env python3
"""Forecast Roblox's Up-and-Coming chart, place by place, for the 72 hours after
entries close.

The program reads the chart's history from $MAKEFUN_INPUT_DIR (default /input):
  - history.ndjson: one read per line, oldest first, each with `at` and the
    chart's rows under `up_and_coming` (rank, universe_id, name, playing, ...);
  - task.json: `places` (10, the places scored) and the output file's name.
It writes one forecast to $MAKEFUN_OUTPUT_DIR (default /output): for each of the
top 10 places, a probability for every game it names at that place, plus its
top-10 guess. Source and the standard library only; deterministic, no network.

The model: the chart is persistent but drifts.  Each game's expected place is
its current place, pulled up by its player-count growth over the last
`LOOKBACK_HOURS` and by its recent rank momentum.  Around that expected place
the game gets an exponentially decaying probability (scale `SPREAD`); a share
`UNNAMED` of every place is left to the games the forecast does not name there,
which is what an honest forecast gives a game it cannot place.
"""

import json
import math
import os
from datetime import datetime

INPUT_DIR = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
OUTPUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")

# Tuned on the kit's sealed practice instance (10 archive reads over 72 hours).
LOOKBACK_HOURS = 16.0   # window over which player growth and rank momentum are measured
TOP_N = 15              # games named by current place
GROWTH_TOP = 10         # games named by recent player growth
SPREAD = 2.0            # decay scale of the sharp component, in places
SPREAD_TAIL = 14.0      # decay scale of the insurance component, in places
SHARP = 0.90            # weight of the sharp component; the 10% tail covers horizon drift
UNNAMED = 0.16          # share of each place left to the games not named there
BOOST = 400.0           # places pulled up per unit of log player growth per hour
GROWTH_THRESHOLD = 0.05 # growth per hour below which a game is not boosted
MOMENTUM = 0.0          # places pulled up per rank gained per hour
MOMENTUM_CLIP = 10.0    # cap on rank momentum, places per hour
BOOST_CAP = 30.0        # cap on the growth boost, places


def hours_of(at):
    """ISO 8601 UTC timestamp -> hours since the epoch (float)."""
    return datetime.fromisoformat(at.replace("Z", "+00:00")).timestamp() / 3600.0


def load_reads(path):
    """The history as [(hours, {universe_id: row}), ...], oldest first."""
    reads = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            read = json.loads(line)
            rows = read.get("up_and_coming")
            if not rows:
                continue
            reads.append((hours_of(read["at"]), {r["universe_id"]: r for r in rows}))
    reads.sort(key=lambda item: item[0])
    return reads


def base_read(reads, last_at):
    """The read at or before `last_at - LOOKBACK_HOURS`, else the first read."""
    target = last_at - LOOKBACK_HOURS
    chosen = 0
    for i in range(len(reads) - 2, -1, -1):
        if reads[i][0] <= target:
            chosen = i
            break
    return reads[chosen]


def game_features(last_map, base_map, dt):
    """For each game of the last read: current place, growth and rank momentum."""
    features = {}
    for uid, row in last_map.items():
        place = row["rank"]
        growth = 0.0
        momentum = 0.0
        old = base_map.get(uid)
        if old is not None and dt > 0:
            playing, was = row.get("playing"), old.get("playing")
            if playing and was and playing > 0 and was > 0:
                growth = math.log(playing / was) / dt
            momentum = (old["rank"] - place) / dt
        features[uid] = (place, growth, momentum)
    return features


def build_forecast(reads, places):
    """The forecast object: probabilities rows and the top-10 guess."""
    last_at, last_map = reads[-1]
    chart = [uid for uid, _ in sorted(last_map.items(), key=lambda kv: kv[1]["rank"])]
    base_at, base_map = base_read(reads, last_at)
    features = game_features(last_map, base_map, last_at - base_at)
    place_of = {uid: features[uid][0] for uid in chart}

    candidates = list(chart[:TOP_N])
    by_growth = sorted(chart, key=lambda uid: -features[uid][1])[:GROWTH_TOP]
    for uid in by_growth:
        if uid not in candidates:
            candidates.append(uid)

    probabilities = []
    for place in range(1, min(places, len(chart)) + 1):
        weights = {}
        for uid in candidates:
            current, growth, momentum = features[uid]
            boost = min(BOOST_CAP, BOOST * max(0.0, growth - GROWTH_THRESHOLD))
            pull = boost + MOMENTUM * max(-MOMENTUM_CLIP, min(MOMENTUM_CLIP, momentum)) * 8.0
            expected = current - pull
            distance = abs(expected - place)
            weights[uid] = (SHARP * math.exp(-distance / SPREAD)
                            + (1.0 - SHARP) * math.exp(-distance / SPREAD_TAIL))
        total = sum(weights.values())
        if total <= 0:
            continue
        for uid, weight in weights.items():
            p = (1.0 - UNNAMED) * weight / total
            if p > 0.0:
                probabilities.append({"universe_id": uid, "place": place, "p": round(p, 9)})
    return {"probabilities": probabilities, "top10": chart[:places]}


def main():
    with open(os.path.join(INPUT_DIR, "task.json"), encoding="utf-8") as f:
        task = json.load(f)
    places = int(task.get("places", 10))
    reads = load_reads(os.path.join(INPUT_DIR, "history.ndjson"))
    forecast = build_forecast(reads, places)
    out_path = os.path.join(OUTPUT_DIR, task.get("output", "forecast.json"))
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(forecast, f, separators=(",", ":"))
        f.write("\n")


if __name__ == "__main__":
    main()
