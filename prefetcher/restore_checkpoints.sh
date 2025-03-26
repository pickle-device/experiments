#!/bin/bash

graph_names=("amazon" "gplus" "higgs" "livejournal" "orkut" "pokec" "roadNetCA" "twitch" "youtube" "web_berkstan" "web_google" "wiki_talk" "wiki_topcats")
OUTPUT_FOLDER="/workdir/ARTIFACTS/results_v2/"

for graph_name in "${graph_names[@]}"
do
    echo "Running $graph_name"
    /workdir/gem5/build/ARM/gem5.opt -re --outdir=$OUTPUT_FOLDER/bfs-$graph_name-baseline --debug-flags=PickleDevicePrefetcherProgressTracker experiments/prefetcher/test_restore_checkpoint.py --graph_name=$graph_name --enable_pdev=False --prefetch_distance=0 &
    /workdir/gem5/build/ARM/gem5.opt -re --outdir=$OUTPUT_FOLDER/bfs-$graph_name-pdev-distance_128 --debug-flags=PickleDevicePrefetcherProgressTracker experiments/prefetcher/test_restore_checkpoint.py --graph_name=$graph_name --enable_pdev=True --prefetch_distance=128 &
done