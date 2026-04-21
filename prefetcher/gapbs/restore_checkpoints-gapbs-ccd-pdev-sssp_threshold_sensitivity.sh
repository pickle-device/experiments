#!/bin/bash

applications=("sssp")
graph_names=("as_skitter" "livejournal" "orkut" "pokec" "roadNetCA" "youtube" "web_berkstan" "web_google" "wiki_talk")
graph_names_tc=("as_skitter" "roadNetCA" "youtube")
OUTPUT_FOLDER="/workdir/ARTIFACTS/results_tbe_64/gapbs/"

PREFETCH_DISTANCE_DROP_DISTANCE_PAIRS=( "32:16" )
PDEV_TBES=(64)
PREFETCH_AGENT=("True")
PICKLE_CACHE_SIZE=("256KiB")
LLC_AGENT_TIMEOUT=10000 # in cycles
mesh=8

prefetch_mode="single"
chunk_size=1
pf_per_hint=1

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
        for pair in "${PREFETCH_DISTANCE_DROP_DISTANCE_PAIRS[@]}"
        do
            IFS=':' read -r pf_distance prefetch_drop_distance <<< "$pair"
            for pdev_tbes in "${PDEV_TBES[@]}"
            do
                for delegate_last_layer_prefetch in "${PREFETCH_AGENT[@]}"
                do
                    for pickle_cache_size in "${PICKLE_CACHE_SIZE[@]}"
                    do
                        if [[ "$application" == "bfs" || "$application" == "bc" || "$application" == "sssp" ]]; then
                            OFFSET=16
                            prefetch_distance=$((pf_distance+16))
                        else
                            OFFSET=0
                            prefetch_distance=$pf_distance
                        fi
                        echo "Running $application-$graph_name with Pickle Prefetcher: distance $prefetch_distance, offset $OFFSET, drop $prefetch_drop_distance, tbe $pdev_tbes, llc_agent $delegate_last_layer_prefetch, cache_size $pickle_cache_size, mode $prefetch_mode, chunk_size $chunk_size, pf_per_hint $pf_per_hint"
                        HOME=/workdir /workdir/gem5/build/ARM/gem5.opt \
                            -re \
                            --outdir=$OUTPUT_FOLDER/$application-$graph_name-mesh_$mesh-pdev_distance_${prefetch_distance}_offset_${OFFSET}_drop_${prefetch_drop_distance}_tbe_${pdev_tbes}_delegate_${delegate_last_layer_prefetch}_cache_${pickle_cache_size}_mode_${prefetch_mode}_chunksize_${chunk_size}_bulksize_${pf_per_hint}_llctimeout_${LLC_AGENT_TIMEOUT}_ssspthresholdoptimization_False \
                            --debug-flags=PickleDevicePrefetcherProgressTracker \
                                experiments/prefetcher/gem5_configurations/restore_checkpoint.py \
                            --application $application \
                            --graph_name=$graph_name \
                            --enable_pdev=True \
                            --pickle_cache_size=$pickle_cache_size \
                            --prefetch_distance=$prefetch_distance \
                            --prefetch_mode=$prefetch_mode \
                            --bulk_prefetch_chunk_size=$chunk_size \
                            --bulk_prefetch_num_prefetches_per_hint=$pf_per_hint \
                            --offset_from_pf_hint=$OFFSET \
                            --prefetch_drop_distance=$prefetch_drop_distance\
                            --delegate_last_layer_prefetch=$delegate_last_layer_prefetch\
                            --pdev_num_tbes=$pdev_tbes \
                            --llc_delegation_timeout=$LLC_AGENT_TIMEOUT \
                            --concurrent_work_item_capacity=64 \
                            --private_cache_prefetcher=none \
                            --sssp_threshold_optimization_enabled=False \
                            --mesh $mesh &
                    done
                done
            done
        done
    done
done
