#!/bin/bash

applications=("bc" "bfs" "cc" "pr" "sssp" "tc")
graph_names=("as_skitter" "livejournal" "orkut" "pokec" "roadNetCA" "youtube" "web_berkstan" "web_google" "wiki_talk")
graph_names_tc=("as_skitter" "roadNetCA" "youtube")
OUTPUT_FOLDER="/workdir/ARTIFACTS/results/gapbs/"
LLC_CAPACITIES=("6GiB")
mesh=8

for application in "${applications[@]}"
do
    # for tc, we only run a subset of the graphs since tc only works with
    # undirected graphs
    if [[ "$application" == "tc" ]]; then
        actual_graph_names=("${graph_names_tc[@]}")
    else
        actual_graph_names=("${graph_names[@]}")
    fi
    for graph_name in "${actual_graph_names[@]}"
    do
        for llc_capacity in "${LLC_CAPACITIES[@]}"
        do
            echo "Running $application-$graph_name with ${llc_capacity} LLC"
            HOME=/workdir /workdir/gem5/build/ARM/gem5.opt \
                -re \
                --outdir=$OUTPUT_FOLDER/$application-$graph_name-mesh_$mesh-llc_$llc_capacity \
                --debug-flags=PickleDevicePrefetcherProgressTracker \
                experiments/prefetcher/gem5_configurations/restore_checkpoint_ideal_l3.py \
                --application=$application \
                --graph_name=$graph_name \
                --llc_capacity=$llc_capacity \
                --mesh $mesh &
        done
    done
done
