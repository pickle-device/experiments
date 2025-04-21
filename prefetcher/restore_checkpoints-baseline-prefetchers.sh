#!/bin/bash

graph_names=("amazon" "gplus" "higgs" "livejournal" "orkut" "pokec" "roadNetCA" "twitch" "youtube" "web_berkstan" "web_google" "wiki_talk" "wiki_topcats")
private_cache_prefetchers=("imp" "ampm" "stride" "multiv1")
#private_cache_prefetchers=("imp" "stride")
#private_cache_prefetchers=("ampm" "multiv1")
OUTPUT_FOLDER="/workdir/ARTIFACTS/results_v7/"

for graph_name in "${graph_names[@]}"
do
    for private_cache_prefetcher in "${private_cache_prefetchers[@]}"
    do
        echo "Running $graph_name with $private_cache_prefetcher"
        /workdir/gem5/build/ARM/gem5.opt -re --outdir=$OUTPUT_FOLDER/bfs-$graph_name-baseline-$private_cache_prefetcher --debug-flags=PickleDevicePrefetcherProgressTracker experiments/prefetcher/gem5_configurations/restore_checkpoint.py --application bfs --graph_name=$graph_name  --enable_pdev=False --prefetch_distance=0 --offset_from_pf_hint=0 --pdev_num_tbes 1024 --private_cache_prefetcher=$private_cache_prefetcher &
    done
done
