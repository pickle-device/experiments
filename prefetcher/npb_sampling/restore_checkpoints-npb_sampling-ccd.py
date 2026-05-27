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


import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# application_workload_class_pairs = ["is-S", "is-D", "cg-S", "cg-E"]
application_workload_class_pairs = ["is-D"]
private_cache_prefetchers=["stride", "dmp_with_page_walk"]

OUTPUT_FOLDER = Path("/workdir/ARTIFACTS/results_tbe_64/npb_sampling/")
MESH = 8
SAMPLING_DURATION_MILLISECONDS = 100
MAX_CONCURRENT = 10

SAMPLING_SITES_BY_APP = {
    "is": ["1"],
    "cg": ["1"],  # ["1", "2"]
}

SAMPLING_POINTS_S = [1, 2, 3]
SAMPLING_POINTS = list(range(1, 31))

PREFETCH_DISTANCE=32
PREFETCH_DROP_DISTANCE=16
OFFSET=0
PDEV_TBES=64
DELEGATE_LAST_LAYER_PREFETCH="True"
PICKLE_CACHE_SIZE="256KiB"
PREFETCH_MODE="single"
CHUNK_SIZE=1
PF_PER_HINT=1
LLC_AGENT_TIMEOUT=10000 # in cycles


def build_baseline_jobs():
    jobs = []
    for pair in application_workload_class_pairs:
        application, workload_class = pair.split("-")
        sampling_sites = SAMPLING_SITES_BY_APP[application]

        for sampling_site in sampling_sites:
            for sampling_point in SAMPLING_POINTS_S if workload_class == "S" else SAMPLING_POINTS:
                outdir = OUTPUT_FOLDER / (
                    f"{application}-{workload_class}"
                    f"-mesh_{MESH}"
                    f"-sampling_site_{sampling_site}"
                    f"-sampling_point_{sampling_point}"
                    f"-baseline"
                )
                cmd = [
                    "/workdir/gem5/build/ARM/gem5.opt",
                    "-re",
                    f"--outdir={outdir}",
                    "--debug-flags=PickleDevicePrefetcherProgressTracker",
                    "experiments/prefetcher/gem5_configurations/restore_checkpoint_npb_sampling_methodology.py",
                    "--application", application,
                    "--workload_class", workload_class,
                    "--sampling_site", sampling_site,
                    "--sampling_point", str(sampling_point),
                    "--sampling_duration_milliseconds", str(SAMPLING_DURATION_MILLISECONDS),
                    "--enable_pdev=False",
                    "--pickle_cache_size", "256KiB",
                    "--prefetch_distance", "0",
                    "--offset_from_pf_hint", "0",
                    "--prefetch_drop_distance", "0",
                    "--delegate_last_layer_prefetch", "False",
                    "--concurrent_work_item_capacity", "64",
                    "--pdev_num_tbes", "1024",
                    "--private_cache_prefetcher=none",
                    "--prefetch_mode", "single",
                    "--bulk_prefetch_chunk_size", "1",
                    "--bulk_prefetch_num_prefetches_per_hint", "1",
                    "--llc_delegation_timeout=0",
                    "--mesh", str(MESH),
                ]
                label = f"{application}-{workload_class} site={sampling_site} point={sampling_point} system=baseline"
                jobs.append((label, cmd))
    return jobs


def build_private_cache_prefetcher_jobs():
    jobs = []
    for pair in application_workload_class_pairs:
        application, workload_class = pair.split("-")
        sampling_sites = SAMPLING_SITES_BY_APP[application]

        for sampling_site in sampling_sites:
            for sampling_point in SAMPLING_POINTS_S if workload_class == "S" else SAMPLING_POINTS:
                for private_cache_prefetcher in private_cache_prefetchers:
                    outdir = OUTPUT_FOLDER / (
                        f"{application}-{workload_class}"
                        f"-mesh_{MESH}"
                        f"-sampling_site_{sampling_site}"
                        f"-sampling_point_{sampling_point}"
                        f"-prefetcher_{private_cache_prefetcher}"
                    )
                    cmd = [
                        "/workdir/gem5/build/ARM/gem5.opt",
                        "-re",
                        f"--outdir={outdir}",
                        "--debug-flags=PickleDevicePrefetcherProgressTracker",
                        "experiments/prefetcher/gem5_configurations/restore_checkpoint_npb_sampling_methodology.py",
                        "--application", application,
                        "--workload_class", workload_class,
                        "--sampling_site", sampling_site,
                        "--sampling_point", str(sampling_point),
                        "--sampling_duration_milliseconds", str(SAMPLING_DURATION_MILLISECONDS),
                        "--enable_pdev=False",
                        "--pickle_cache_size", "256KiB",
                        "--prefetch_distance", "0",
                        "--offset_from_pf_hint", "0",
                        "--prefetch_drop_distance", "0",
                        "--delegate_last_layer_prefetch", "False",
                        "--concurrent_work_item_capacity", "64",
                        "--pdev_num_tbes", "1024",
                        "--private_cache_prefetcher", private_cache_prefetcher,
                        "--prefetch_mode", "single",
                        "--bulk_prefetch_chunk_size", "1",
                        "--bulk_prefetch_num_prefetches_per_hint", "1",
                        "--llc_delegation_timeout=0",
                        "--mesh", str(MESH),
                    ]
                    label = f"{application}-{workload_class} site={sampling_site} point={sampling_point} system={private_cache_prefetcher}"
                    jobs.append((label, cmd))
    return jobs


def build_pickle_prefetcher_jobs():
    jobs = []
    for pair in application_workload_class_pairs:
        application, workload_class = pair.split("-")
        sampling_sites = SAMPLING_SITES_BY_APP[application]

        for sampling_site in sampling_sites:
            for sampling_point in SAMPLING_POINTS_S if workload_class == "S" else SAMPLING_POINTS:
                outdir = OUTPUT_FOLDER / (
                    f"{application}-{workload_class}"
                    f"-mesh_{MESH}"
                    f"-sampling_site_{sampling_site}"
                    f"-sampling_point_{sampling_point}"
                    f"-pdev_distance_{PREFETCH_DISTANCE}"
                    f"-offset_{OFFSET}"
                    f"-drop_{PREFETCH_DROP_DISTANCE}"
                    f"-tbe_{PDEV_TBES}"
                    f"-delegate_{DELEGATE_LAST_LAYER_PREFETCH}"
                    f"-cache_{PICKLE_CACHE_SIZE}"
                    f"-mode_{PREFETCH_MODE}"
                    f"-chunksize_{CHUNK_SIZE}"
                    f"-bulksize_{PF_PER_HINT}"
                    f"-llctimeout_{LLC_AGENT_TIMEOUT}"
                )
                cmd = [
                    "/workdir/gem5/build/ARM/gem5.opt",
                    "-re",
                    f"--outdir={outdir}",
                    "--debug-flags=PickleDevicePrefetcherProgressTracker",
                    "experiments/prefetcher/gem5_configurations/restore_checkpoint_npb_sampling_methodology.py",
                    "--application", application,
                    "--workload_class", workload_class,
                    "--sampling_site", sampling_site,
                    "--sampling_point", str(sampling_point),
                    "--sampling_duration_milliseconds", str(SAMPLING_DURATION_MILLISECONDS),
                    "--enable_pdev=True",
                    "--pickle_cache_size", PICKLE_CACHE_SIZE,
                    "--prefetch_distance", str(PREFETCH_DISTANCE),
                    "--offset_from_pf_hint", str(OFFSET),
                    "--prefetch_drop_distance", str(PREFETCH_DROP_DISTANCE),
                    "--delegate_last_layer_prefetch", DELEGATE_LAST_LAYER_PREFETCH,
                    "--concurrent_work_item_capacity", "64",
                    "--pdev_num_tbes", str(PDEV_TBES),
                    "--private_cache_prefetcher", "none",
                    "--prefetch_mode", PREFETCH_MODE,
                    "--bulk_prefetch_chunk_size", str(CHUNK_SIZE),
                    "--bulk_prefetch_num_prefetches_per_hint", str(PF_PER_HINT),
                    "--llc_delegation_timeout", str(LLC_AGENT_TIMEOUT),
                    "--mesh", str(MESH),
                ]
                label = f"{application}-{workload_class} site={sampling_site} point={sampling_point} system=pickle_prefetcher"
                jobs.append((label, cmd))
    return jobs


def build_pickle_prefetcher_with_private_cache_prefetcher_jobs():
    jobs = []
    for pair in application_workload_class_pairs:
        application, workload_class = pair.split("-")
        sampling_sites = SAMPLING_SITES_BY_APP[application]

        for sampling_site in sampling_sites:
            for sampling_point in SAMPLING_POINTS_S if workload_class == "S" else SAMPLING_POINTS:
                for private_cache_prefetcher in private_cache_prefetchers:
                    outdir = OUTPUT_FOLDER / (
                        f"{application}-{workload_class}"
                        f"-mesh_{MESH}"
                        f"-sampling_site_{sampling_site}"
                        f"-sampling_point_{sampling_point}"
                        f"-prefetcher_{private_cache_prefetcher}"
                        f"-pdev_distance_{PREFETCH_DISTANCE}"
                        f"-offset_{OFFSET}"
                        f"-drop_{PREFETCH_DROP_DISTANCE}"
                        f"-tbe_{PDEV_TBES}"
                        f"-delegate_{DELEGATE_LAST_LAYER_PREFETCH}"
                        f"-cache_{PICKLE_CACHE_SIZE}"
                        f"-mode_{PREFETCH_MODE}"
                        f"-chunksize_{CHUNK_SIZE}"
                        f"-bulksize_{PF_PER_HINT}"
                        f"-llctimeout_{LLC_AGENT_TIMEOUT}"
                    )
                    cmd = [
                        "/workdir/gem5/build/ARM/gem5.opt",
                        "-re",
                        f"--outdir={outdir}",
                        "--debug-flags=PickleDevicePrefetcherProgressTracker",
                        "experiments/prefetcher/gem5_configurations/restore_checkpoint_npb_sampling_methodology.py",
                        "--application", application,
                        "--workload_class", workload_class,
                        "--sampling_site", sampling_site,
                        "--sampling_point", str(sampling_point),
                        "--sampling_duration_milliseconds", str(SAMPLING_DURATION_MILLISECONDS),
                        "--enable_pdev=True",
                        "--pickle_cache_size", PICKLE_CACHE_SIZE,
                        "--prefetch_distance", str(PREFETCH_DISTANCE),
                        "--offset_from_pf_hint", str(OFFSET),
                        "--prefetch_drop_distance", str(PREFETCH_DROP_DISTANCE),
                        "--delegate_last_layer_prefetch", DELEGATE_LAST_LAYER_PREFETCH,
                        "--concurrent_work_item_capacity", "64",
                        "--pdev_num_tbes", str(PDEV_TBES),
                        "--private_cache_prefetcher", private_cache_prefetcher,
                        "--prefetch_mode", PREFETCH_MODE,
                        "--bulk_prefetch_chunk_size", str(CHUNK_SIZE),
                        "--bulk_prefetch_num_prefetches_per_hint", str(PF_PER_HINT),
                        "--llc_delegation_timeout", str(LLC_AGENT_TIMEOUT),
                        "--mesh", str(MESH),
                    ]
                    label = f"{application}-{workload_class} site={sampling_site} point={sampling_point} system=pickle_prefetcher_with_{private_cache_prefetcher}"
                    jobs.append((label, cmd))
    return jobs


def run_job(job):
    label, cmd = job
    print(f"[start] {label}", flush=True)
    result = subprocess.run(cmd, env={"HOME": "/workdir"})
    print(f"[done ] {label} (rc={result.returncode})", flush=True)
    return label, result.returncode


def main():
    jobs = []
    baseline_jobs = build_baseline_jobs()
    private_cache_prefetcher_jobs = build_private_cache_prefetcher_jobs()
    pickle_prefetcher_jobs = build_pickle_prefetcher_jobs()
    pickle_prefetcher_with_private_cache_prefetcher_jobs = build_pickle_prefetcher_with_private_cache_prefetcher_jobs()
    
    # interleaving jobs (4 at a time, 1 from each category) so that we can get all data
    # for same checkpoint
    num_sampling_points = len(baseline_jobs)
    num_private_cache_prefetchers = len(private_cache_prefetchers)
    assert len(private_cache_prefetcher_jobs) == num_sampling_points * num_private_cache_prefetchers
    assert len(pickle_prefetcher_jobs) == num_sampling_points
    assert len(pickle_prefetcher_with_private_cache_prefetcher_jobs) == num_sampling_points * num_private_cache_prefetchers

    for i in range(num_sampling_points):
        jobs.append(baseline_jobs[i])
        jobs.append(pickle_prefetcher_jobs[i])
        jobs.extend(private_cache_prefetcher_jobs[num_private_cache_prefetchers*i:num_private_cache_prefetchers*(i+1)])
        jobs.extend(pickle_prefetcher_with_private_cache_prefetcher_jobs[num_private_cache_prefetchers*i:num_private_cache_prefetchers*(i+1)])

    print(f"Dispatching {len(jobs)} jobs, max {MAX_CONCURRENT} concurrent")

    failures = []
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT) as pool:
        for label, rc in pool.map(run_job, jobs):
            if rc != 0:
                failures.append((label, rc))

    if failures:
        print(f"\n{len(failures)} job(s) failed:")
        for label, rc in failures:
            print(f"  rc={rc}  {label}")
    else:
        print("\nAll jobs completed successfully.")


if __name__ == "__main__":
    main()
