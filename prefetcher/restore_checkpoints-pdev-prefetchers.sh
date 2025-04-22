#!/bin/bash

applications=("bfs" "pr")
graph_names=("amazon" "gplus" "higgs" "livejournal" "orkut" "pokec" "roadNetCA" "twitch" "youtube" "web_berkstan" "web_google" "wiki_talk" "wiki_topcats")
private_cache_prefetchers=("imp" "ampm" "stride" "multiv1")
OUTPUT_FOLDER="/workdir/ARTIFACTS/results_v8/"

PREFETCH_DISTANCE=48
OFFSET=16

for application in "${applications[@]}"
do
    for graph_name in "${graph_names[@]}"
    do
        for private_cache_prefetcher in "${private_cache_prefetchers[@]}"
        do
            echo "Running $application-$graph_name with $private_cache_prefetcher"
            /workdir/gem5/build/ARM/gem5.opt \
                -re \
                --outdir=$OUTPUT_FOLDER/$application-$graph_name-pdev_distance_${PREFETCH_DISTANCE}_offset_$OFFSET-$private_cache_prefetcher \
                --debug-flags=PickleDevicePrefetcherProgressTracker \
                experiments/prefetcher/gem5_configurations/restore_checkpoint.py \
                --application $application \
                --graph_name=$graph_name \
                --enable_pdev=True \
                --prefetch_distance=$PREFETCH_DISTANCE \
                --offset_from_pf_hint=$OFFSET \
                --pdev_num_tbes 1024 \
                --private_cache_prefetcher=$private_cache_prefetcher &
        done
    done
done
