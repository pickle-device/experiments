#!/bin/bash

graph_names=("amazon", "gplus", "higgs", "livejournal", "orkut", "pokec", "roadNetCA", "twitch", "youtube", "web_berkstan", "web_google", "wiki_talk", "wiki_topcats")
OUTPUT_FOLDER="/workdir/ARTIFACTS/results/"

for graph_name in "${graph_names[@]}"
do
    echo "Running $graph_name"
    /workdir/gem5/build/ARM/gem5.opt -re --outdir=$OUTPUT_FOLDER/bfs-$graph_name-pdev-distance_32 --debug-flags=PickleDevicePrefetcherProgressTracker experiments/prefetcher/test.py --graph_name=$graph_name --enable_pdev=True &
    #/workdir/gem5/build/ARM/gem5.opt -re --outdir=$OUTPUT_FOLDER/bfs-$graph_name-baseline experiments/prefetcher/test.py --graph_name=$graph_name --enable_pdev=False &
done


    
