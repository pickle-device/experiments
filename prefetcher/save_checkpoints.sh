#!/bin/bash

applications=("bfs" "pr")
graph_names=("amazon" "gplus" "higgs" "livejournal" "orkut" "pokec" "roadNetCA" "twitch" "youtube" "web_berkstan" "web_google" "wiki_talk" "wiki_topcats" "test5" "test10")
OUTPUT_FOLDER="/workdir/ARTIFACTS/results_v8/"

for application in "${applications[@]}"
do
    for graph_name in "${graph_names[@]}"
    do
        echo "Running $application-$graph_name"
        /workdir/gem5/build/ARM/gem5.opt \
            -re \
            --outdir=$OUTPUT_FOLDER/$application-$graph_name-checkpoint \
            --debug-flags=PickleDevicePrefetcherProgressTracker \
            experiments/prefetcher/gem5_configurations/save_checkpoint.py \
            --application=$application \
            --graph_name=$graph_name;
    done
done
