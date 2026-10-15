# Copyright (c) 2026 The Regents of the University of California
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met: redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer;
# redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution;
# neither the name of the copyright holders nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import argparse
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

APPLICATIONS = ["bfs"]
#GRAPH_NAMES = ["as_skitter", "livejournal", "orkut", "pokec", "roadNetCA", "web_berkstan", "web_google", "wiki_talk", "youtube"]
GRAPH_NAMES = ["as_skitter", "livejournal", "orkut", "pokec", "roadNetCA", "web_berkstan", "web_google", "wiki_talk", "youtube"]
OUTPUT_FOLDER = "/workdir/ARTIFACTS/results_with_cxl/gapbs/"
WITH_CXL = ["True"]
CXL_LINK_LATENCY = [
    "100", # 25ns
    #"200", # 50ns
    "400", # 100ns
    "800", # 200ns
]
PREFETCH_DISTANCE_DROP_DISTANCE_PAIRS=[(32, 16)]
PDEV_TBES=64
PREFETCH_AGENT="True"
PICKLE_CACHE_SIZE="256KiB"
LLC_AGENT_TIMEOUT=10000 # in cycles

PREFETCH_MODE="single"
BULK_PREFETCH_CHUNK_SIZE=1
BULK_PREFETCH_NUM_PREFETCHES_PER_HINT=1

PRIVATE_CACHE_PREFETCHERS = ["stride", "dmp_with_page_walk"]

GEM5_BINARY = "/workdir/gem5/build/ARM/gem5.opt"
CONFIG_SCRIPT = (
    "experiments/prefetcher/gem5_configurations/restore_checkpoint.py"
)
with_cxl_mem = "True"
mesh = "8"
local_cxl_allocation_ratio = "2:1"

def build_jobs():
    jobs = []
    for application in APPLICATIONS:
        for graph_name in GRAPH_NAMES:
            for cxl_link_latency in CXL_LINK_LATENCY:
                local_weight, cxl_weight = local_cxl_allocation_ratio.split(":")
                for private_cache_prefetcher in PRIVATE_CACHE_PREFETCHERS:
                    outdir = os.path.join(
                        OUTPUT_FOLDER,
                        f"{application}-{graph_name}-mesh_{mesh}-prefetcher_{private_cache_prefetcher}-cxl_{with_cxl_mem}-cxl_link_latency_{cxl_link_latency}-local_cxl_allocation_ratio_{local_weight}_{cxl_weight}",
                    )
                    cmd = [
                        GEM5_BINARY, "-re",
                        "--outdir", outdir,
                        CONFIG_SCRIPT,
                        "--application", application,
                        "--graph_name", graph_name,
                        "--enable_pdev", "False",
                        "--pickle_cache_size", "256KiB",
                        "--prefetch_distance", "0",
                        "--offset_from_pf_hint", "0",
                        "--prefetch_drop_distance", "0",
                        "--delegate_last_layer_prefetch", "False",
                        "--concurrent_work_item_capacity", "64",
                        "--pdev_num_tbes", "1024",
                        "--llc_delegation_timeout", "0",
                        "--private_cache_prefetcher", private_cache_prefetcher,
                        "--prefetch_mode", "single",
                        "--bulk_prefetch_chunk_size", "1",
                        "--bulk_prefetch_num_prefetches_per_hint", "1",
                        "--mesh", mesh,
                        "--with_cxl_mem", with_cxl_mem,
                        "--cxl_link_latency_in_cycles", cxl_link_latency,
                        "--local_cxl_allocation_ratio", local_cxl_allocation_ratio
                    ]
                    label = (
                        f"{application}-{graph_name}-mesh_{mesh}-cxl_{with_cxl_mem}-prefetcher_{private_cache_prefetcher}"
                    )
                    jobs.append((label, cmd))
                for prefetch_distance, drop_distance in PREFETCH_DISTANCE_DROP_DISTANCE_PAIRS:
                    if application in {"bc", "bfs", "sssp"}:
                        offset_from_pf_hint = 16
                        prefetch_distance += 16
                    else:
                        offset_from_pf_hint = 0
                    outdir = os.path.join(
                        OUTPUT_FOLDER,
                        f"{application}-{graph_name}-mesh_{mesh}-cxl_{with_cxl_mem}-cxl_link_latency_{cxl_link_latency}-local_cxl_allocation_ratio_{local_weight}_{cxl_weight}-pdev_distance_{prefetch_distance}_offset_{offset_from_pf_hint}_drop_{drop_distance}_tbe_{PDEV_TBES}_delegate_{PREFETCH_AGENT}_cache_{PICKLE_CACHE_SIZE}_mode_{PREFETCH_MODE}_chunksize_{BULK_PREFETCH_CHUNK_SIZE}_bulksize_{BULK_PREFETCH_NUM_PREFETCHES_PER_HINT}_llctimeout_{LLC_AGENT_TIMEOUT}",
                    )
                    cmd = [
                        GEM5_BINARY, "-re",
                        "--outdir", outdir,
                        "--debug-flags", "PickleDevicePrefetcherProgressTracker",
                        CONFIG_SCRIPT,
                        "--application", application,
                        "--graph_name", graph_name,
                        "--enable_pdev", "True",
                        "--pickle_cache_size", PICKLE_CACHE_SIZE,
                        "--prefetch_distance", str(prefetch_distance),
                        "--offset_from_pf_hint", str(offset_from_pf_hint),
                        "--prefetch_drop_distance", str(drop_distance),
                        "--delegate_last_layer_prefetch", str(PREFETCH_AGENT),
                        "--concurrent_work_item_capacity", "64",
                        "--pdev_num_tbes", str(PDEV_TBES),
                        "--llc_delegation_timeout", str(LLC_AGENT_TIMEOUT),
                        "--private_cache_prefetcher", "none",
                        "--prefetch_mode", "single",
                        "--bulk_prefetch_chunk_size", "1",
                        "--bulk_prefetch_num_prefetches_per_hint", "1",
                        "--mesh", mesh,
                        "--with_cxl_mem", with_cxl_mem,
                        "--cxl_link_latency_in_cycles", cxl_link_latency,
                        "--local_cxl_allocation_ratio", local_cxl_allocation_ratio,
                    ]
                    label = (
                        f"{application}-{graph_name}-mesh_{mesh}-cxl_{with_cxl_mem}-{cxl_link_latency}-{local_cxl_allocation_ratio}-pdev_distance_{prefetch_distance}_offset_{offset_from_pf_hint}_drop_{drop_distance}_tbe_{PDEV_TBES}_delegate_{PREFETCH_AGENT}_cache_{PICKLE_CACHE_SIZE}_mode_{PREFETCH_MODE}_chunksize_{BULK_PREFETCH_CHUNK_SIZE}_bulksize_{BULK_PREFETCH_NUM_PREFETCHES_PER_HINT}_llctimeout_{LLC_AGENT_TIMEOUT}"
                    )
                    jobs.append((label, cmd))
    return jobs


def run_job(job):
    label, cmd = job
    print(f"Running {label}", flush=True)
    env = dict(os.environ, HOME="/workdir")
    result = subprocess.run(cmd, env=env)
    return label, result.returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-j", "--max-concurrent", type=int, required=True,
        help=f"max gem5 processes running at once; 0 means no limit",
    )
    args = parser.parse_args()

    jobs = build_jobs()
    if args.max_concurrent <= 0:
        args.max_concurrent = len(jobs)
    print(f"{len(jobs)} jobs, {args.max_concurrent} at a time", flush=True)

    failures = []
    with ThreadPoolExecutor(max_workers=args.max_concurrent) as executor:
        futures = [executor.submit(run_job, job) for job in jobs]
        for future in as_completed(futures):
            label, rc = future.result()
            status = "ok" if rc == 0 else f"FAILED (rc={rc})"
            print(f"Done: {label} -> {status}", flush=True)
            if rc != 0:
                failures.append((label, rc))

    if failures:
        print(f"\n{len(failures)} job(s) failed:", flush=True)
        for label, rc in failures:
            print(f"  {label} (rc={rc})", flush=True)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
