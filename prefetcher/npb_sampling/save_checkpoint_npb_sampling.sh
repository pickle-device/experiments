#!/bin/bash

#application_workload_class_pairs=("is-S" "is-D" "cg-S" "cg-E")
application_workload_class_pairs=("is-S" "is-D" "cg-S")
meshes=("8")
OUTPUT_FOLDER="/workdir/ARTIFACTS/results_v8/"

for application_workload_class_pair in "${application_workload_class_pairs[@]}"
do
    application=$(echo "$application_workload_class_pair" | cut -d'-' -f1)
    workload_class=$(echo "$application_workload_class_pair" | cut -d'-' -f2)
    for mesh in "${meshes[@]}"
    do
        if [ "$application" == "is" ]; then
            sampling_sites=("1")
        elif [ "$application" == "cg" ]; then
            sampling_sites=("1" "2")
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
                echo "Running $application-$workload_class with mesh $mesh sampling_site $sampling_site sampling_point $sampling_point"
                HOME=/workdir /workdir/gem5/build/ARM/gem5.opt \
                        -re \
                    --outdir ${OUTPUT_FOLDER}/$application-$workload_class-mesh_$mesh-checkpoint \
                    experiments/prefetcher/gem5_configurations/save_checkpoint_npb_sampling_methodology.py \
                    --application $application \
                    --workload_class $workload_class \
                    --mesh $mesh \
                    --sampling_site $sampling_site \
                    --sampling_point $sampling_point
            done
        done
    done
done
