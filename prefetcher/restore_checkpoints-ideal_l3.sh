#!/bin/bash

applications=("bfs" "cc" "tc")
graph_names=("test5" "test10" "amazon" "as_skitter" "livejournal" "orkut" "pokec" "roadNetCA" "youtube" "web_berkstan" "web_google" "wiki_talk")
OUTPUT_FOLDER="/workdir/ARTIFACTS/results/gapbs/"
LLC_CAPACITIES=("96MiB" "6GiB")

for application in "${applications[@]}"
do
    for graph_name in "${graph_names[@]}"
    do
        for llc_capacity in "${LLC_CAPACITIES[@]}"
        do
            echo "Running $application-$graph_name with ${llc_capacity} LLC"
            HOME=/workdir /workdir/gem5/build/ARM/gem5.opt \
                -re \
                --outdir=$OUTPUT_FOLDER/$application-$graph_name-llc_$llc_capacity \
                --debug-flags=PickleDevicePrefetcherProgressTracker \
                experiments/prefetcher/gem5_configurations/restore_checkpoint_ideal_l3.py \
                --llc_capacity=$llc_capacity &
        done
    done
done

applications=("spmv")
graph_names=("steam1" "nlpkkt200" "consph" "roadnet" "Ga41As41H72")
OUTPUT_FOLDER="/workdir/ARTIFACTS/results/spmv/"

for application in "${applications[@]}"
do
    for graph_name in "${graph_names[@]}"
    do
        for llc_capacity in "${LLC_CAPACITIES[@]}"
        do
            echo "Running $application-$graph_name with ${llc_capacity} LLC"
            HOME=/workdir /workdir/gem5/build/ARM/gem5.opt \
                -re \
                --outdir=$OUTPUT_FOLDER/$application-$graph_name-llc_$llc_capacity \
                --debug-flags=PickleDevicePrefetcherProgressTracker \
                experiments/prefetcher/gem5_configurations/restore_checkpoint_ideal_l3.py \
                --llc_capacity=$llc_capacity &
        done
    done
done