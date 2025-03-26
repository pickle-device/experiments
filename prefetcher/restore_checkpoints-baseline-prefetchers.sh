#!/bin/bash

#graph_names=("amazon" "gplus" "higgs" "livejournal" "orkut" "pokec" "roadNetCA" "twitch" "youtube" "web_berkstan" "web_google" "wiki_talk" "wiki_topcats")
small_graph_names=("amazon" "gplus" "higgs" "roadNetCA" "twitch" "youtube" "web_google" "wiki_talk")
private_cache_prefetchers=("imp" "ampm" "stride")
OUTPUT_FOLDER="/workdir/ARTIFACTS/results_v2/"

for graph_name in "${small_graph_names[@]}"
do
    for private_cache_prefetcher in "${private_cache_prefetchers[@]}"
    do
        echo "Running $graph_name with $private_cache_prefetcher"
        /workdir/gem5/build/ARM/gem5.opt -re --outdir=$OUTPUT_FOLDER/bfs-$graph_name-baseline-$private_cache_prefetcher --debug-flags=PickleDevicePrefetcherProgressTracker experiments/prefetcher/test_restore_checkpoint.py --graph_name=$graph_name --enable_pdev=False --prefetch_distance=0 --private_cache_prefetcher=$private_cache_prefetcher &
    done
done
