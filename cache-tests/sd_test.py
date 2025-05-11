# Copyright (c) 2025 The Regents of the University of California
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

from m5.objects import (
    RubyDataMovementTracker,
)

from gem5.components.boards.test_board import TestBoard
from gem5.components.memory.dram_interfaces.ddr5 import DDR5_8400_4x8
from gem5.components.memory.memory import ChanneledMemory
from gem5.components.processors.traffic_generator import TrafficGenerator
from gem5.simulate.simulator import Simulator
from gem5.utils.override import overrides

from MeshCache.MeshCache import MeshCache
from MeshCache.MeshCacheWithPickleDevice import MeshCacheWithPickleDevice
from MeshCache.components.PrebuiltMesh import PrebuiltMesh

mesh_descriptor = PrebuiltMesh.getMesh9("Mesh9")

with open("mem_config1.cfg", "w") as f:
    #        STATE id    duration   type read_percent start_addr end_addr block_size min_period max_period data_limit
    f.write(
        "STATE  0   100000000 LINEAR            0          0 16777216         64     500000     600000          0\n"
    )
    f.write("STATE  1   100000000   EXIT\n")
    f.write("INIT 0\n")
    f.write("TRANSITION 0 1 1.0\n")
    f.write("TRANSITION 1 0 1.0\n")

with open("mem_config2.cfg", "w") as f:
    #        STATE id    duration   type read_percent start_addr end_addr block_size min_period max_period data_limit
    f.write("STATE  0      800000   IDLE\n")
    f.write(
        "STATE  1   100000000 LINEAR          100          0 16777216         64     500000     600000          0\n"
    )
    f.write("STATE  2   100000000   EXIT\n")
    f.write("INIT 0\n")
    f.write("TRANSITION 0 1 1.0\n")
    f.write("TRANSITION 1 2 1.0\n")
    f.write("TRANSITION 2 0 1.0\n")

generator = TrafficGenerator(
    [
        "mem_config1.cfg",
        "mem_config2.cfg",
    ]
)

memory = ChanneledMemory(
    dram_interface_class=DDR5_8400_4x8,
    num_channels=mesh_descriptor.get_num_mem_tiles(),
    interleaving_size=64,
    size="4GiB",
)

mesh_cache = MeshCache(
    l1i_size="32KiB",
    l1i_assoc=8,
    l1d_size="48KiB",
    l1d_assoc=12,
    l2_size="1MiB",
    l2_assoc=16,
    l3_size="32MiB",
    l3_assoc=16,
    num_core_complexes=1,
    is_fullsystem=False,
    mesh_descriptor=mesh_descriptor,
)


class PickleTestBoard(TestBoard):
    def __init__(self, clk_freq, generator, memory, cache_hierarchy):
        super().__init__(
            clk_freq=clk_freq,
            generator=generator,
            memory=memory,
            cache_hierarchy=cache_hierarchy,
        )

    @overrides(TestBoard)
    def _pre_instantiate(self, full_system):
        super()._pre_instantiate()
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


board = PickleTestBoard(
    clk_freq="1GHz",  # setting the clk period for the whole system
    generator=generator,
    memory=memory,
    cache_hierarchy=mesh_cache,
)

simulator = Simulator(board=board)
simulator.run()
