"""Run the NPB sampling-methodology checkpoint sweep with bounded concurrency.

Port of the original bash sweep. Up to MAX_CONCURRENT gem5 processes run at once.
gem5 is invoked with -re, so each process redirects its own stdout/stderr into its
outdir (simout/simerr); the terminal only carries this script's progress lines.
"""

import argparse
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

MAX_CONCURRENT = 8

# application_workload_class_pairs = ["is-S", "is-D", "cg-S", "cg-E"]
APPLICATION_WORKLOAD_CLASS_PAIRS = ["ua-D"]
MESHES = ["8"]
OUTPUT_FOLDER = "/workdir/ARTIFACTS/results_v8/"

WITH_CXL_MEM = ["True", "False"]
LOCAL_CXL_ALLOCATION_RATIOS = ["2:1", "1:1", "3:1", "1:2"]

GEM5_BINARY = "/workdir/gem5/build/ARM/gem5.opt"
CONFIG_SCRIPT = (
    "experiments/prefetcher/gem5_configurations/"
    "save_checkpoint_npb_sampling_methodology.py"
)


def sampling_sites_for(application):
    if application == "is":
        return ["1"]
    if application == "cg":
        return ["1", "2"]
    if application == "ua":
        # return ["1", "2"]
        return ["1"]
    return []


def build_jobs():
    jobs = []
    for pair in APPLICATION_WORKLOAD_CLASS_PAIRS:
        application, workload_class = pair.split("-", 1)
        num_sampling_points = 30 if workload_class != "S" else 3
        for mesh in MESHES:
            for with_cxl_mem in WITH_CXL_MEM:
                if not with_cxl_mem:
                    considering_ratios = ['invalid']
                else:
                    considering_ratios = LOCAL_CXL_ALLOCATION_RATIOS
                for ratio in considering_ratios:
                    for site in sampling_sites_for(application):
                        for point in range(1, num_sampling_points + 1):
                            outdir = os.path.join(
                                OUTPUT_FOLDER,
                                f"{application}-{workload_class}-mesh_{mesh}-with_cxl_mem_{with_cxl_mem}-local_cxl_allocation_ratio_{ratio}-"
                                f"sampling_site_{site}-sampling_point_{point}-checkpoint",
                            )
                            cmd = [
                                GEM5_BINARY, "-re",
                                "--outdir", outdir,
                                CONFIG_SCRIPT,
                                "--application", application,
                                "--workload_class", workload_class,
                                "--mesh", mesh,
                                "--with_cxl_mem", str(with_cxl_mem),
                                "--local_cxl_allocation_ratio", ratio,
                                "--sampling_site", site,
                                "--sampling_point", str(point),
                            ]
                            label = (
                                f"{application}-{workload_class}-mesh_{mesh}-with_cxl_mem_{with_cxl_mem}-local_cxl_allocation_ratio_{ratio}-"
                                f"sampling_site_{site}-sampling_point_{point}-checkpoint"
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
        "-j", "--max-concurrent", type=int, default=MAX_CONCURRENT,
        help=f"max gem5 processes running at once (default {MAX_CONCURRENT})",
    )
    args = parser.parse_args()

    jobs = build_jobs()
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
