#!/bin/bash

graph_names=("amazon" "gplus" "higgs" "livejournal" "orkut" "pokec" "roadNetCA" "twitch" "youtube" "web_berkstan" "web_google" "wiki_talk" "wiki_topcats")
OUTPUT_FOLDER="/workdir/ARTIFACTS/results_v2/"

for graph_name in "${graph_names[@]}"
do
    echo "Running $graph_name with no prefetchers"
    /workdir/gem5/build/ARM/gem5.opt \
        -re --outdir=$OUTPUT_FOLDER/bfs-$graph_name-pdev_distance_32_offset_16 \
        --debug-flags=PickleDevicePrefetcherProgressTracker \
        experiments/prefetcher/gem5_configurations/restore_checkpoint.py \
        --graph_name=$graph_name \
        --enable_pdev=True \
        --prefetch_distance=32 \
        --offset_from_pf_hint=16 \
        --pdev_num_tbes 1024 \
        --private_cache_prefetcher=none &
done
