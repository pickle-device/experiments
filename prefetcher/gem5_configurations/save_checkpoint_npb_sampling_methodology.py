import argparse
import os
from pathlib import Path
import time

import m5

from gem5.utils.requires import requires
from gem5.utils.override import overrides
from gem5.components.boards.arm_board import ArmBoard
from gem5.components.memory.dram_interfaces.ddr4 import DDR4_2400_8x8
from gem5.components.memory.dram_interfaces.ddr5 import DDR5_8400_4x8
from gem5.components.memory.memory import ChanneledMemory
from gem5.components.processors.simple_processor import SimpleProcessor
from gem5.components.processors.cpu_types import CPUTypes
from gem5.isas import ISA
from gem5.coherence_protocol import CoherenceProtocol
from gem5.simulate.simulator import Simulator
from gem5.simulate.exit_event import ExitEvent
from gem5.resources.workload import Workload
from gem5.resources.resource import (
    Resource,
    CustomResource,
    CustomDiskImageResource,
    obtain_resource,
)
from gem5.components.processors.simple_switchable_processor import (
    SimpleSwitchableProcessor,
)

from MeshCache.MeshCache import MeshCache
from MeshCache.MeshCacheWithPickleDevice import MeshCacheWithPickleDevice
from MeshCache.components.PrebuiltMesh import PrebuiltMesh

from m5.objects import (
    PickleDevice,
    TrafficSnooper,
    AddrRange,
    ArmMMU,
    PickleDeviceRequestManager,
    PicklePrefetcher,
    TAGE_SC_L_64KB,
    CompressionType,
)

from m5.objects import (
    ArmDecoder,
    ArmDefaultRelease,
    ArmISA,
    VExpress_GEM5_V1,
    VExpress_GEM5_Foundation,
)

parser = argparse.ArgumentParser()
parser.add_argument("--application", type=str, required=True, choices={"cg", "is", "ua"})
parser.add_argument("--workload_class", type=str, required=True)
parser.add_argument("--mesh", type=int, required=True, choices={8, 10})
parser.add_argument("--sampling_site", type=int, required=True)
parser.add_argument("--sampling_point", type=int, required=True)
args = parser.parse_args()

application = args.application
workload_class = args.workload_class
mesh = args.mesh
sampling_site = args.sampling_site
sampling_point = args.sampling_point

# read the sampling points from the sampling point file
# example:
#      Input:  Workload: cg
#        Class: E
#        Sampling Site: 1
#        LLC Size: 32 MiB
#        Number of Sampling Points: 30
#        Sampling Points:
#          Sampling Point 1: Starting Iter = 646793, Num Warmup Iters = 3970
#          Sampling Point 2: Starting Iter = 4799697, Num Warmup Iters = 3976
#          Sampling Point 3: Starting Iter = 2414799, Num Warmup Iters = 3987
#          Sampling Point 4: Starting Iter = 7760004, Num Warmup Iters = 3963
#          Sampling Point 5: Starting Iter = 6205510, Num Warmup Iters = 3984
sampling_point_file = f"/workdir/experiments/prefetcher/gem5_configurations/npb_sampling_points/{application}.{workload_class}.sampling_site-{sampling_site}.llc-32MiB.sampling_points.txt"
sampling_points = {}
class SamplingPoint:
    def __init__(self, starting_iter, num_warmup_iters):
        self.starting_iter = starting_iter
        self.num_warmup_iters = num_warmup_iters
with open(sampling_point_file, "r") as f:
    for line in f:
        line = line.strip()
        if line.startswith("Sampling Point "):
            parts = line.split(" ")
            sampling_point_number = int(parts[2][:-1])
            starting_iter = int(parts[6][:-1])
            num_warmup_iters = int(parts[-1])
            sampling_points[sampling_point_number] = SamplingPoint(starting_iter, num_warmup_iters)
starting_iter = sampling_points[sampling_point].starting_iter
num_warmup_iters = sampling_points[sampling_point].num_warmup_iters

# validate the arguments
if application == "cg":
    assert workload_class in {"S", "E"}, f"Unsupported workload class for application {application}: {workload_class}"
    assert sampling_site == 1 or sampling_site == 2, f"Unsupported sampling site for application {application}: {sampling_site}"
elif application == "is":
    assert workload_class in {"S", "D"}, f"Unsupported workload class for application {application}: {workload_class}"
    assert sampling_site == 1, f"Unsupported sampling site for application {application}: {sampling_site}"
elif application == "ua":
    assert workload_class in {"S", "D"}, f"Unsupported workload class for application {application}: {workload_class}"
    assert sampling_site == 1, f"Unsupported sampling site for application {application}: {sampling_site}"
else:
    assert False, f"Unsupported application: {application}"

if mesh == 8:
    mesh_descriptor = PrebuiltMesh.getMesh8("Mesh8")
else:
    assert False, f"Unsupported mesh: {mesh}"
num_cores = mesh_descriptor.get_num_core_tiles()

fast_forward_cpu_type = CPUTypes.KVM

special_memory_requirement = {
    ("cg", "E"): "128GiB",
    ("is", "D"): "48GiB",
    ("ua", "D"): "16GiB",
}
def choose_memory_size(application, workload_class):
    if (application, workload_class) in special_memory_requirement:
        return special_memory_requirement[(application, workload_class)]
    return "4GiB"

mesh_cache = MeshCacheWithPickleDevice(
    l1i_size="32KiB",
    l1i_assoc=8,
    l1d_size="48KiB",
    l1d_assoc=12,
    l2_size="1MiB",
    l2_assoc=16,
    l3_size="32MiB",
    l3_assoc=16,
    device_cache_size="32KiB",
    device_cache_assoc=8,
    num_core_complexes=1,
    is_fullsystem=True,
    mesh_descriptor=mesh_descriptor,
    data_prefetcher_class=None,
    pdev_num_tbes=64,
)

# Main memory
memory = ChanneledMemory(
    dram_interface_class=DDR5_8400_4x8,
    num_channels=mesh_descriptor.get_num_mem_tiles(),
    interleaving_size=64,
    size=choose_memory_size(application, workload_class),
)

processor = SimpleProcessor(cpu_type=CPUTypes.KVM, isa=ISA.ARM, num_cores=num_cores)

# Here we tell the KVM CPU (the starting CPU) not to use perf.
if fast_forward_cpu_type == CPUTypes.KVM:
    for proc in processor.get_cores():
        proc.core.usePerf = False


class PickleArmBoard(ArmBoard):
    def __init__(self, clk_freq, processor, memory, cache_hierarchy, release, platform):
        super().__init__(
            clk_freq=clk_freq,
            processor=processor,
            memory=memory,
            cache_hierarchy=cache_hierarchy,
            release=release,
            platform=platform,
        )

    @overrides(ArmBoard)
    def get_default_kernel_args(self):
        # The default kernel string is taken from the devices.py file.
        return [
            "console=ttyAMA0",
            "lpj=19988480",
            "norandmaps",
            "root=/dev/vda1",
            "disk_device=/dev/vda1",
            "rw",
            f"mem={self.get_memory().get_size()}",
            "init=/home/ubuntu/gem5-init.sh",
        ]

    @overrides(ArmBoard)
    def _pre_instantiate(self, full_system):
        num_PD_tiles = (
            self.cache_hierarchy.get_mesh_descriptor().get_num_pickle_device_tiles()
        )
        all_cores = [core.core for core in self.processor.get_cores()]
        self.traffic_snoopers = [
            TrafficSnooper(watch_ranges=[AddrRange(0x10110000, 0x10130000)])
            for i in range(num_PD_tiles * len(all_cores))
        ]
        self.pickle_device_mmus = [
            ArmMMU(release_se=ArmDefaultRelease()) for _ in range(num_PD_tiles)
        ]
        self.pickle_device_functional_mmus = [
            ArmMMU(release_se=ArmDefaultRelease()) for _ in range(num_PD_tiles)
        ]
        self.pickle_device_isas = [ArmISA() for _ in range(num_PD_tiles)]
        self.pickle_device_decoders = [
            ArmDecoder(isa=self.pickle_device_isas[i]) for i in range(num_PD_tiles)
        ]
        self.pickle_device_request_manager = [
            PickleDeviceRequestManager() for i in range(num_PD_tiles)
        ]
        self.pickle_device_prefetchers = [
            PicklePrefetcher(
                software_hint_prefetch_distance=1,
                prefetch_distance_offset_from_software_hint=0,
                num_cores=len(all_cores),
                expected_number_of_prefetch_generators=2,
                concurrent_work_item_capacity=64,
                prefetch_dropping_distance=16,
            )
            for i in range(num_PD_tiles)
        ]
        self.pickle_devices = [
            PickleDevice(
                mmu=self.pickle_device_mmus[i],
                functional_mmu=self.pickle_device_functional_mmus[i],
                isa=self.pickle_device_isas[i],
                decoder=self.pickle_device_decoders[i],
                device_id=i,
                associated_cores=all_cores[
                    i * len(all_cores) : (i + 1) * len(all_cores)
                ],
                num_cores=len(all_cores),
                request_manager=self.pickle_device_request_manager[i],
                prefetcher=self.pickle_device_prefetchers[i],
                core_to_pickle_latency_in_ticks=250,
                ticks_per_cycle=250,
                uncacheable_forwarders=self.traffic_snoopers[
                    i * len(all_cores) : (i + 1) * len(all_cores)
                ],
            )
            for i in range(num_PD_tiles)
        ]
        self.cache_hierarchy.set_pickle_devices(self.pickle_devices)
        self.cache_hierarchy.set_traffic_uncacheable_forwarders(self.traffic_snoopers)
        super()._pre_instantiate()

    @overrides(ArmBoard)
    def _post_instantiate(self):
        super()._post_instantiate()
        self.cache_hierarchy.post_instantiate()


board = PickleArmBoard(
    clk_freq="4GHz",
    processor=processor,
    memory=memory,
    cache_hierarchy=mesh_cache,
    release=ArmDefaultRelease.for_kvm(),
    platform=VExpress_GEM5_V1(),
)
board.compression_type = CompressionType("ZSTD")
board.checkpoint_mem_checksum = True

command_prefix = ""
if application == "is":
    command = f"{command_prefix} /home/ubuntu/NPB/NPB3.4-OMP/bin/{application}.{workload_class}.x.sampling.m5.pdev {starting_iter} {num_warmup_iters}"
elif application == "cg":
    command = f"{command_prefix} /home/ubuntu/NPB/NPB3.4-OMP/bin/{application}.{workload_class}.x.sampling.m5.pdev {sampling_site} {starting_iter} {num_warmup_iters}"
else:
    raise UnimplementedError(f"Application {application} is not implemented")

board.set_kernel_disk_workload(
    kernel=CustomResource("/workdir/ARTIFACTS/linux-6.6.71/vmlinux"),
    disk_image=CustomDiskImageResource("/workdir/ARTIFACTS/arm64.img.v11"),
    #bootloader=obtain_resource("arm64-bootloader", resource_version="1.0.0"),
    bootloader=CustomResource("/workdir/.cache/gem5/arm64-bootloader"),
    readfile_contents=command,
)


def handle_exit():
    print("exit 1")
    yield True


def handle_work_begin():
    print("Workbegin")
    print("Should not be here")
    assert False
    yield True


def handle_work_end():
    print("Workend")
    print("Should not be here")
    assert False
    yield True


simulator = Simulator(
    board=board,
    on_exit_event={
        ExitEvent.EXIT: handle_exit(),
        ExitEvent.WORKBEGIN: handle_work_begin(),
        ExitEvent.WORKEND: handle_work_end(),
    },
)

# We maintain the wall clock time.

globalStart = time.time()

print("Running the simulation")

# We start the simulation.
simulator.run()

checkpoint_name = f"{application}-{workload_class}"
checkpoint_name += f"-mesh_{mesh}"
checkpoint_name += f"-sampling_site_{sampling_site}"
checkpoint_name += f"-starting_iter_{starting_iter}"
checkpoint_name += f"-num_warmup_iters_{num_warmup_iters}"
simulator.save_checkpoint(Path(f"/workdir/ARTIFACTS/checkpoints/{checkpoint_name}"))

print(f"Ran a total of {simulator.get_current_tick() / 1e12} simulated seconds")

print(
    "Total wallclock time: %.2fs, %.2f min"
    % (time.time() - globalStart, (time.time() - globalStart) / 60)
)

print("Exit cause: ", simulator.get_last_exit_event_cause())
