#!/bin/bash

applications=("bfs" "pr")
graph_names=("amazon" "gplus" "higgs" "livejournal" "orkut" "pokec" "roadNetCA" "twitch" "youtube" "web_berkstan" "web_google" "wiki_talk" "wiki_topcats")
OUTPUT_FOLDER="/workdir/ARTIFACTS/results_v8/"

for application in "${applications[@]}"
do
    for graph_name in "${graph_names[@]}"
    do
        echo "Running $application-$graph_name with no prefetchers"
        /workdir/gem5/build/ARM/gem5.opt \
            -re \
            --outdir=$OUTPUT_FOLDER/$application-$graph_name-baseline \
            --debug-flags=PickleDevicePrefetcherProgressTracker \
            experiments/prefetcher/gem5_configurations/restore_checkpoint.py \
            --application $application \
            --graph_name=$graph_name \
            --enable_pdev=False \
            --prefetch_distance=0 \
            --offset_from_pf_hint=0 \
            --pdev_num_tbes 1024 \
            --private_cache_prefetcher=none &
    done
done
