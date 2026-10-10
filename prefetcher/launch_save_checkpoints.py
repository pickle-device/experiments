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

MAX_CONCURRENT = 8

#APPLICATIONS = ["bc", "bfs", "tc", "cc", "pr", "sssp"]
APPLICATIONS = ["bc", "bfs", "cc", "pr", "sssp"]
MESHES = ["8"]
GRAPH_NAMES = ["test5", "as_skitter", "livejournal", "orkut", "pokec", "roadNetCA", "web_berkstan", "web_google", "wiki_talk", "youtube"]
OUTPUT_FOLDER = "/workdir/ARTIFACTS/results_v8/"
WITH_CXL = ["True", "False"]
CXL_LINK_LATENCY = ["200"]
#LOCAL_CXL_ALLOCATION_RATIO = ["1:1", "2:1", "3:1"]
LOCAL_CXL_ALLOCATION_RATIO = ["2:1"]

#WITH_CXL = ["False"]

GEM5_BINARY = "/workdir/gem5/build/ARM/gem5.opt"
CONFIG_SCRIPT = (
    "experiments/prefetcher/gem5_configurations/save_checkpoint.py"
)

def build_jobs():
    jobs = []
    for application in APPLICATIONS:
        for graph_name in GRAPH_NAMES:
            for mesh in MESHES:
                for with_cxl_mem in WITH_CXL:
                    if with_cxl_mem == "False":
                        outdir = os.path.join(
                            OUTPUT_FOLDER,
                            f"{application}-{graph_name}-mesh_{mesh}-cxl_{with_cxl_mem}-checkpoint",
                        )
                        cmd = [
                            GEM5_BINARY, "-re",
                            "--outdir", outdir,
                            CONFIG_SCRIPT,
                            "--application", application,
                            "--graph_name", graph_name,
                            "--mesh", mesh,
                            "--with_cxl_mem", with_cxl_mem,
                            "--cxl_link_latency_in_cycles", "1",
                            "--local_cxl_allocation_ratio", "invalid",
                        ]
                        label = (
                            f"{application}-{graph_name}-mesh_{mesh}-cxl_{with_cxl_mem}-checkpoint"
                        )
                        jobs.append((label, cmd))
                    else:
                        for cxl_link_latency in CXL_LINK_LATENCY:
                            for local_cxl_allocation_ratio in LOCAL_CXL_ALLOCATION_RATIO:
                                outdir = os.path.join(
                                    OUTPUT_FOLDER,
                                    f"{application}-{graph_name}-mesh_{mesh}-cxl_{with_cxl_mem}-cxl_link_latency_{cxl_link_latency}-local_cxl_allocation_ratio_{local_cxl_allocation_ratio}-checkpoint",
                                )
                                cmd = [
                                    GEM5_BINARY, "-re",
                                    "--outdir", outdir,
                                    CONFIG_SCRIPT,
                                    "--application", application,
                                    "--graph_name", graph_name,
                                    "--mesh", mesh,
                                    "--with_cxl_mem", with_cxl_mem,
                                    "--cxl_link_latency_in_cycles", cxl_link_latency,
                                    "--local_cxl_allocation_ratio", local_cxl_allocation_ratio,
                                ]
                                label = (
                                    f"{application}-{graph_name}-mesh_{mesh}-cxl_{with_cxl_mem}-{cxl_link_latency}-{local_cxl_allocation_ratio}-checkpoint"
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
