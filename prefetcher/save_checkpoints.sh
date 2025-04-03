#!/bin/bash

graph_names=("amazon" "gplus" "higgs" "livejournal" "orkut" "pokec" "roadNetCA" "twitch" "youtube" "web_berkstan" "web_google" "wiki_talk" "wiki_topcats")
OUTPUT_FOLDER="/workdir/ARTIFACTS/results_v2/"

for graph_name in "${graph_names[@]}"
do
    echo "Running $graph_name"
    /workdir/gem5/build/ARM/gem5.opt -re --outdir=$OUTPUT_FOLDER/bfs-$graph_name-checkpoint --debug-flags=PickleDevicePrefetcherProgressTracker experiments/prefetcher/gem5_configurations/save_checkpoint.py --graph_name=$graph_name;
done
