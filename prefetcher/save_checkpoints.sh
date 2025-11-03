#!/bin/bash

#applications=("bfs" "pr")
applications=("bfs" "tc" "cc")
#graph_names=("test5" "test10" "amazon" "as_skitter" "gplus" "higgs" "livejournal" "orkut" "pokec" "roadNetCA" "twitch" "youtube" "web_berkstan" "web_google" "wiki_talk" "wiki_topcats")
graph_names=("test5" "test10" "amazon" "as_skitter" "livejournal" "orkut" "pokec" "roadNetCA" "youtube" "web_berkstan" "web_google" "wiki_talk")
OUTPUT_FOLDER="/workdir/ARTIFACTS/results_v8/"

for application in "${applications[@]}"
do
    for graph_name in "${graph_names[@]}"
    do
        echo "Running $application-$graph_name"
        HOME=/workdir /workdir/gem5/build/ARM/gem5.opt \
            -re \
            --outdir=$OUTPUT_FOLDER/$application-$graph_name-checkpoint \
            --debug-flags=PickleDevicePrefetcherProgressTracker \
            experiments/prefetcher/gem5_configurations/save_checkpoint.py \
            --application=$application \
            --graph_name=$graph_name;
    done
done

applications=("spmv")
graph_names=("steam1" "nlpkkt200" "consph" "roadnet" "Ga41As41H72")
OUTPUT_FOLDER="/workdir/ARTIFACTS/results_v8/"
for application in "${applications[@]}"
do
    for graph_name in "${graph_names[@]}"
    do
        echo "Running $application-$graph_name"
        HOME=/workdir /workdir/gem5/build/ARM/gem5.opt \
            -re \
            --outdir=$OUTPUT_FOLDER/$application-$graph_name-checkpoint \
            --debug-flags=PickleDevicePrefetcherProgressTracker \
            experiments/prefetcher/gem5_configurations/save_checkpoint.py \
            --application=$application \
            --graph_name=$graph_name;
    done
done
