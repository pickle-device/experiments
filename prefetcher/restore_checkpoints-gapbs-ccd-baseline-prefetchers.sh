#!/bin/bash

private_cache_prefetchers=("stride" "imp" "dmp")

applications=("bfs" "cc" "tc" "pr")
graph_names=("amazon" "as_skitter" "livejournal" "orkut" "pokec" "roadNetCA" "youtube" "web_berkstan" "web_google" "wiki_talk")
OUTPUT_FOLDER="/workdir/ARTIFACTS/results/gapbs/"
mesh=8

for application in "${applications[@]}"
do
    for graph_name in "${graph_names[@]}"
    do
        for private_cache_prefetcher in "${private_cache_prefetchers[@]}"
        do
            echo "Running $application-$graph_name with $private_cache_prefetcher prefetcher"
            HOME=/workdir /workdir/gem5/build/ARM/gem5.opt \
                -re \
                --outdir=$OUTPUT_FOLDER/$application-$graph_name-mesh_$mesh-prefetcher_$private_cache_prefetcher \
                --debug-flags=DifferentialMatchingPrefetcherIndirectRelationTableDebug \
                experiments/prefetcher/gem5_configurations/restore_checkpoint.py \
                --application $application \
                --graph_name=$graph_name \
                --enable_pdev=False \
                --pickle_cache_size 256KiB \
                --prefetch_distance 0 \
                --offset_from_pf_hint 0 \
                --prefetch_drop_distance 0 \
                --delegate_last_layer_prefetch False \
                --concurrent_work_item_capacity 64 \
                --pdev_num_tbes 1024 \
                --private_cache_prefetcher=$private_cache_prefetcher \
                --prefetch_mode single \
                --bulk_prefetch_chunk_size 1 \
                --bulk_prefetch_num_prefetches_per_hint 1 \
                --mesh $mesh &
        done
    done
done
