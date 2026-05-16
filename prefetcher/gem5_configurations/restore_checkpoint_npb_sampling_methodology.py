import argparse
from pathlib import Path
import time

import m5

from gem5.utils.requires import requires
from gem5.utils.override import overrides
from gem5.components.boards.arm_board import ArmBoard
from gem5.components.memory.dram_interfaces.ddr3 import DDR3_1600_8x8
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
    RubyDataMovementTracker,
    ProgramProgressTracker,
    ProgramProgressTrackerAgent,
    PrefetchSchedulingPolicy,
    CompressionType,
)

from m5.objects import (
    ArmDecoder,
    ArmDefaultRelease,
    ArmISA,
    VExpress_GEM5_V1,
    VExpress_GEM5_Foundation,
)


prefetch_mode_map = {
    "single": 1,
    "bulk": 2,
}

parser = argparse.ArgumentParser()
parser.add_argument("--application", type=str, required=True, choices={"is", "cg", "ua"})
parser.add_argument("--workload_class", type=str, required=True)
parser.add_argument("--sampling_site", type=int, required=True)
parser.add_argument("--sampling_point", type=int, required=True)
parser.add_argument("--enable_pdev", type=str, required=True, choices={"True", "False"})
parser.add_argument("--pickle_cache_size", type=str, required=True, help="Prefetcher cache size, e.g., 4KiB")
parser.add_argument("--prefetch_distance", type=int, required=True)
parser.add_argument("--prefetch_mode", type=str, required=True, choices=list(prefetch_mode_map.keys()))
parser.add_argument("--bulk_prefetch_chunk_size", type=int, required=True)
parser.add_argument("--bulk_prefetch_num_prefetches_per_hint", type=int, required=True)
parser.add_argument("--offset_from_pf_hint", type=int, required=True)
parser.add_argument("--prefetch_drop_distance", type=int, required=True)
parser.add_argument("--delegate_last_layer_prefetch", type=str, required=True, choices={"True", "False"})
parser.add_argument("--concurrent_work_item_capacity", type=int, required=True)
parser.add_argument("--pdev_num_tbes", type=int, required=True)
parser.add_argument("--llc_delegation_timeout", type=int, required=True, help="Number of cycles after which the prefetcher should stop waiting for a prefetch request to be picked up by an LLC agent before it tries to send the prefetch itself")
parser.add_argument(
    "--private_cache_prefetcher",
    type=str,
    required=True,
    choices=["none", "stride", "dmp", "dmp_with_page_walk", "imp", "ampm", "sms", "bop", "multiv1"],
)

# optional
parser.add_argument("--sssp_threshold_optimization_enabled", type=str, required=False, default="True", choices={"True", "False"})
parser.add_argument("--bc_depth_optimization_enabled", type=str, required=False, default="False", choices={"True", "False"})
parser.add_argument("--bc_depth_prefetch_to_both_llc_and_pickle_enabled", type=str, required=False, default="False", choices={"True", "False"})
parser.add_argument("--functional_pickle_mmu", type=str, required=False, default="False", choices={"True", "False"})
parser.add_argument("--llc_size", type=str, required=False, default="32MiB", choices={"16MiB", "32MiB", "64MiB"})
parser.add_argument("--ddr_technology", type=str, required=False, default="DDR5@8400", choices={"DDR3@1600", "DDR4@2400", "DDR5@8400"})
parser.add_argument(
    "--prefetch_scheduling_policy", type=str, required=False, default="earliest_deadline_first_using_hint_arrival_time",
    choices={"earliest_deadline_first_using_hint_arrival_time", "first_in_first_out"}
)

parser.add_argument("--mesh", type=int, required=True, choices={8, 10})
args = parser.parse_args()

application = args.application
workload_class = args.workload_class
sampling_site = args.sampling_site
sampling_point = args.sampling_point
enable_pdev = args.enable_pdev == "True"
pickle_cache_size = args.pickle_cache_size
prefetch_distance = args.prefetch_distance
prefetch_mode = prefetch_mode_map[args.prefetch_mode]
bulk_prefetch_chunk_size = args.bulk_prefetch_chunk_size
bulk_prefetch_num_prefetches_per_hint = args.bulk_prefetch_num_prefetches_per_hint
private_cache_prefetcher = args.private_cache_prefetcher
enable_core_mmu_ptw_for_prefetches = False
if private_cache_prefetcher == "dmp_with_page_walk":
    private_cache_prefetcher = "dmp"
    enable_core_mmu_ptw_for_prefetches = True
offset_from_pf_hint = args.offset_from_pf_hint
prefetch_drop_distance = args.prefetch_drop_distance
delegate_last_layer_prefetch = args.delegate_last_layer_prefetch
concurrent_work_item_capacity = args.concurrent_work_item_capacity
pdev_num_tbes = args.pdev_num_tbes
llc_delegation_timeout = args.llc_delegation_timeout
sssp_threshold_optimization_enabled = args.sssp_threshold_optimization_enabled == "True"
bc_depth_optimization_enabled = args.bc_depth_optimization_enabled == "True"
bc_depth_prefetch_to_both_llc_and_pickle_enabled = args.bc_depth_prefetch_to_both_llc_and_pickle_enabled == "True"
functional_pickle_mmu = args.functional_pickle_mmu == "True"
llc_size = args.llc_size
ddr_technology = args.ddr_technology
prefetch_scheduling_policy = {
    "earliest_deadline_first_using_hint_arrival_time": PrefetchSchedulingPolicy("EARLIEST_DEADLINE_FIRST_BASED_ON_HINT_ARRIVAL_TIME"),
    "first_in_first_out": PrefetchSchedulingPolicy("FIRST_IN_FIRST_OUT"),
}[args.prefetch_scheduling_policy]
mesh = args.mesh

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

print(f"Mesh: PrebuiltMesh{mesh}")
print(f"Application: {application}")
print(f"Workload class: {workload_class}")
print(f"Private Cache Prefetcher: {private_cache_prefetcher}, Enable core MMU page walk for prefetches: {enable_core_mmu_ptw_for_prefetches}")
print(f"Enable Pickle Device: {enable_pdev}")
print(f"Prefetch Distance: {prefetch_distance}, Offset: {offset_from_pf_hint}, Drop Distance: {prefetch_drop_distance}")
print(f"Prefetch Mode: {prefetch_mode}, Chunk Size: {bulk_prefetch_chunk_size}, Prefetches Per Hint: {bulk_prefetch_num_prefetches_per_hint}")
print(f"Delegate to LLC Agent: {delegate_last_layer_prefetch}")
print(f"Concurrent work item capacity: {concurrent_work_item_capacity}")
print(f"Num PDEV TBEs: {pdev_num_tbes}")
print(f"Sampling point: {sampling_point}, Starting iteration: {starting_iter}, Num warmup iterations: {num_warmup_iters}")

if mesh == 8:
    mesh_descriptor = PrebuiltMesh.getMesh8("Mesh8")
elif mesh == 10:
    mesh_descriptor = PrebuiltMesh.getMesh10("Mesh10")
else:
    assert False, f"Unsupported mesh: {mesh}"

num_cores = mesh_descriptor.get_num_core_tiles()

fast_forward_cpu_type = CPUTypes.KVM

special_memory_requirement = {
    ("cg", "E"): "192GiB",
    ("is", "D"): "48GiB",
    ("ua", "D"): "16GiB",
}
def choose_memory_size(application, workload_class):
    if (application, workload_class) in special_memory_requirement:
        return special_memory_requirement[(application, workload_class)]
    return "4GiB"
memory_size = choose_memory_size(application, workload_class)

def getNumPrefetchGeneratorsForApplication(application):
    return {
        "is": 1,
        "cg": 2,
    }[application]

mesh_cache = MeshCacheWithPickleDevice(
    l1i_size="32KiB",
    l1i_assoc=8,
    l1d_size="48KiB",
    l1d_assoc=12,
    l2_size="1MiB",
    l2_assoc=16,
    l3_size=llc_size,
    l3_assoc=16,
    device_cache_size=pickle_cache_size,
    device_cache_assoc=16,
    num_core_complexes=1,
    is_fullsystem=True,
    mesh_descriptor=mesh_descriptor,
    data_prefetcher_class=private_cache_prefetcher,
    pdev_num_tbes=pdev_num_tbes,
)

# Main memory
dram_class = {
    "DDR3@1600": DDR3_1600_8x8,
    "DDR4@2400": DDR4_2400_8x8,
    "DDR5@8400": DDR5_8400_4x8,
}[ddr_technology]
memory = ChanneledMemory(
    dram_interface_class=dram_class,
    num_channels=mesh_descriptor.get_num_mem_tiles(),
    interleaving_size=64,
    size=memory_size,
)

processor = SimpleProcessor(cpu_type=CPUTypes.O3, isa=ISA.ARM, num_cores=num_cores)

# (application, workload_class, sampling_site) -> tracked PC
tracking_pc = {
    ("is", "S", 1): 0x5284,
    ("is", "D", 1): 0x50c8,
    ("cg", "S", 1): 0x37b4,
    ("cg", "S", 2): 0x4014,
    ("cg", "E", 1): 0x37c4,
    ("cg", "E", 2): 0x4024,
}

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
            TrafficSnooper(
                watch_ranges=[AddrRange(0x10110000, 0x10130000)], snoop_on=True
            )
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
            PickleDeviceRequestManager(
                use_functional_mmu=functional_pickle_mmu,
            ) for i in range(num_PD_tiles)
        ]
        num_generators = getNumPrefetchGeneratorsForApplication(application)
        self.pickle_device_prefetchers = [
            PicklePrefetcher(
                software_hint_prefetch_distance=prefetch_distance,
                prefetch_distance_offset_from_software_hint=offset_from_pf_hint,
                prefetch_mode=prefetch_mode,
                bulk_prefetch_chunk_size=bulk_prefetch_chunk_size,
                bulk_prefetch_num_prefetches_per_hint=bulk_prefetch_num_prefetches_per_hint,
                num_cores=len(all_cores),
                expected_number_of_prefetch_generators=num_generators,
                concurrent_work_item_capacity=concurrent_work_item_capacity,
                prefetch_dropping_distance=prefetch_drop_distance,
                delegate_last_layer_prefetches_to_llc_agents=delegate_last_layer_prefetch,
                prefetch_scheduling_policy=prefetch_scheduling_policy,
                sssp_threshold_optimization_enabled=sssp_threshold_optimization_enabled,
                bc_depth_optimization_enabled=bc_depth_optimization_enabled,
                #bc_depth_prefetch_to_both_llc_and_pickle_enabled=bc_depth_prefetch_to_both_llc_and_pickle_enabled,
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
                is_on=False,
            )
            for i in range(num_PD_tiles)
        ]
        self.cache_hierarchy.set_pickle_devices(self.pickle_devices)
        self.cache_hierarchy.set_traffic_uncacheable_forwarders(self.traffic_snoopers)
        # configure the processors
        for core in all_cores:
            core.branchPred = TAGE_SC_L_64KB()
            core.branchPred.ras.numEntries = 52
            core.branchPred.btb.numEntries = 16384
            core.numROBEntries = 448
            core.LQEntries = 256
            core.SQEntries = 128
            core.numIQEntries = 512
            core.fetchQueueSize = 256
        if enable_core_mmu_ptw_for_prefetches:
            for core in all_cores:
                core.mmu.enable_page_walk_on_prefetch_request_tlb_miss = True
        super()._pre_instantiate()
        for agent in self.cache_hierarchy.llc_prefetch_agents:
            agent.timeout_cycles = llc_delegation_timeout
        if application in tracking_pc:
            self.pc_tracker_agents = [
                ProgramProgressTrackerAgent(
                    associated_core=core,
                    manager=core
                )
                for core in all_cores
            ]
            self.pc_tracker = ProgramProgressTracker(
                tracker_agents=self.pc_tracker_agents,
                tracking_pc=0 if (application, workload_class, sampling_site) not in tracking_pc else tracking_pc[(application, workload_class, sampling_site)],
                tracking_interval=100_000 if workload_class != "S" else 1
            )
        for core_tile in self.cache_hierarchy.core_tiles:
            if private_cache_prefetcher == "dmp":
                core_tile.l1d_cache.dmp_prefetcher.tracked_items_per_target_table_entry = 16
        # add the data movement stats
        for core_tile in self.cache_hierarchy.core_tiles:
            core_tile.l1d_cache.data_tracker = RubyDataMovementTracker(
                controller=core_tile.l1d_cache,
                ruby_system=self.cache_hierarchy.ruby_system,
            )
            core_tile.l2_cache.data_tracker = RubyDataMovementTracker(
                controller=core_tile.l2_cache,
                ruby_system=self.cache_hierarchy.ruby_system,
            )
            core_tile.l3_slice.data_tracker = RubyDataMovementTracker(
                controller=core_tile.l3_slice,
                ruby_system=self.cache_hierarchy.ruby_system,
            )
        if self.cache_hierarchy._has_l3_only_tiles:
            for l3_only_tile in self.cache_hierarchy.l3_only_tiles:
                l3_only_tile.l3_slice.data_tracker = RubyDataMovementTracker(
                    controller=l3_only_tile.l3_slice,
                    ruby_system=self.cache_hierarchy.ruby_system,
                )
        if num_PD_tiles > 0:
            for pdev_tile in board.cache_hierarchy.pickle_device_component_tiles:
                pdev_tile.controller.data_tracker = RubyDataMovementTracker(
                    controller=pdev_tile.controller,
                    ruby_system=self.cache_hierarchy.ruby_system,
                )
        print("Making the Pickle device links wider")
        for link in self.cache_hierarchy.ruby_system.network.int_links:
            if (
                link.src_node
                == board.cache_hierarchy.pickle_device_component_tiles[
                    0
                ].cross_tile_router
                or link.dst_node
                == board.cache_hierarchy.pickle_device_component_tiles[
                    0
                ].cross_tile_router
            ):
                link.bandwidth_factor = 512
        for link in self.cache_hierarchy.ruby_system.network.ext_links:
            if (
                link.int_node
                == board.cache_hierarchy.pickle_device_component_tiles[
                    0
                ].cross_tile_router
                or link.ext_node
                == board.cache_hierarchy.pickle_device_component_tiles[
                    0
                ].cross_tile_router
            ):
                link.bandwidth_factor = 512

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
board.checkpoint_mem_checksum = True

command_prefix = ""
if application == "is":
    command = f"{command_prefix} /home/ubuntu/NPB/NPB3.4-OMP/bin/{application}.{workload_class}.x.sampling.m5.pdev {starting_iter} {num_warmup_iters}"
elif application == "cg":
    command = f"{command_prefix} /home/ubuntu/NPB/NPB3.4-OMP/bin/{application}.{workload_class}.x.sampling.m5.pdev {sampling_site} {starting_iter} {num_warmup_iters}"
else:
    raise UnimplementedError(f"Application {application} is not implemented")

checkpoint_name = f"{application}-{workload_class}"
checkpoint_name += f"-mesh_{mesh}"
checkpoint_name += f"-sampling_site_{sampling_site}"
checkpoint_name += f"-starting_iter_{starting_iter}"
checkpoint_name += f"-num_warmup_iters_{num_warmup_iters}"
checkpoint_path = Path(f"/workdir/ARTIFACTS/checkpoints/{checkpoint_name}")
board.set_kernel_disk_workload(
    kernel=CustomResource("/workdir/ARTIFACTS/vmlinux-6.6.71"),
    disk_image=CustomDiskImageResource("/workdir/ARTIFACTS/arm64.img.v10"),
    #bootloader=obtain_resource("arm64-bootloader", resource_version="1.0.0"),
    bootloader=CustomResource("/workdir/.cache/gem5/arm64-bootloader"),
    checkpoint=checkpoint_path,
    readfile_contents=command,
)


def handle_exit_with_pdev():
    print("[exit 2] done with warmup, starting sampling")
    m5.stats.dump()
    print("   -> turning on devices")
    for dev in board.pickle_devices:
        dev.switchOn()
    for snooper in board.traffic_snoopers:
        snooper.switchOn()
    yield False

    print("[exit 3] done with sampling, stopping sim")
    m5.stats.dump()
    yield True


def handle_exit_without_pdev():
    print("[exit 2] done with warmup, starting sampling")
    m5.stats.dump()
    for snooper in board.traffic_snoopers:
        snooper.switchOn()
    yield False

    print("[exit 3] done with sampling, stopping sim")
    m5.stats.dump()
    yield True


def handle_max_tick():
    print("[exit 1] starting warmup")
    m5.stats.dump()
    # trigger the test, the prefetch agent 0 should send out requests to LLC
    #for agent in board.cache_hierarchy.llc_prefetch_agents:
    #    agent.triggerTests()
    #m5.debug.flags["ProtocolTrace"].enable()
    #m5.debug.flags["RubyProtocol"].enable()
    #m5.debug.flags["PickleRubyDebug"].enable()
    yield False


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


handle_exit = handle_exit_with_pdev if enable_pdev else handle_exit_without_pdev

simulator = Simulator(
    board=board,
    on_exit_event={
        ExitEvent.EXIT: handle_exit(),
        ExitEvent.MAX_TICK: handle_max_tick(),
        ExitEvent.WORKBEGIN: handle_work_begin(),
        ExitEvent.WORKEND: handle_work_end(),
    },
)

globalStart = time.time()

print("Running the simulation")

# We start the simulation.
simulator.run(1)
simulator.run(10 ** 18)

print(f"Ran a total of {simulator.get_current_tick() / 1e12} simulated seconds")

print(
    "Total wallclock time: %.2fs, %.2f min"
    % (time.time() - globalStart, (time.time() - globalStart) / 60)
)

print("Exit cause: ", simulator.get_last_exit_event_cause())
