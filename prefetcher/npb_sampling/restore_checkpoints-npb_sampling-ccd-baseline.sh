#!/bin/bash

#application_workload_class_pairs=("is-S" "is-D" "cg-S" "cg-E")
application_workload_class_pairs=("is-S" "cg-S")
OUTPUT_FOLDER="/workdir/ARTIFACTS/results_tbe_64/npb_sampling/"
mesh=8
sampling_duration_milliseconds=100

for application_workload_class_pair in "${application_workload_class_pairs[@]}"
do
    application=$(echo "$application_workload_class_pair" | cut -d'-' -f1)
    workload_class=$(echo "$application_workload_class_pair" | cut -d'-' -f2)
    if [ "$application" == "is" ]; then
        sampling_sites=("1")
    elif [ "$application" == "cg" ]; then
        #sampling_sites=("1" "2")
        sampling_sites=("1")
    fi
    if [ "$workload_class" != "S" ]; then
        num_sampling_points=30
    else
        num_sampling_points=3
    fi
    for sampling_site in "${sampling_sites[@]}"
    do
        for sampling_point in $(seq 1 $num_sampling_points)
        do
            echo "Running $application-$workload_class with no prefetchers"
            HOME=/workdir /workdir/gem5/build/ARM/gem5.opt \
                -re \
                --outdir=$OUTPUT_FOLDER/$application-$workload_class-mesh_$mesh-sampling_site_$sampling_site-sampling_point_$sampling_point-baseline \
                --debug-flags=PickleDevicePrefetcherProgressTracker \
                experiments/prefetcher/gem5_configurations/restore_checkpoint_npb_sampling_methodology.py \
                --application $application \
                --workload_class $workload_class \
                --sampling_site $sampling_site \
                --sampling_point $sampling_point \
                --sampling_duration_milliseconds $sampling_duration_milliseconds \
                --enable_pdev=False \
                --pickle_cache_size 256KiB \
                --prefetch_distance 0 \
                --offset_from_pf_hint 0 \
                --prefetch_drop_distance 0 \
                --delegate_last_layer_prefetch False \
                --concurrent_work_item_capacity 64 \
                --pdev_num_tbes 1024 \
                --private_cache_prefetcher=none \
                --prefetch_mode single \
                --bulk_prefetch_chunk_size 1 \
                --bulk_prefetch_num_prefetches_per_hint 1 \
                --llc_delegation_timeout=0 \
                --mesh $mesh &
        done
    done
done
