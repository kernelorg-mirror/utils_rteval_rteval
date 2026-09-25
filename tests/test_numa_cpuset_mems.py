#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright 2026 John Kacur <jkacur@redhat.com>
#
# Unit tests for NUMA-aware cpuset.mems assignment (Story 5).
#
# Verifies that CpusetManager pins each cpuset's cpuset.mems to the per-side
# NUMA nodes when --*-numa-nodes is used (measurement_memnodes / loads_memnodes),
# and falls back to all nodes otherwise -- the pre-NUMA-flag behavior. Both
# CpusetsInit and Cpuset are mocked so the test needs neither root nor cgroup v2.
#

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rteval.cpusetmanager import CpusetManager
from rteval.Log import Log


class TestNumaCpusetMems(unittest.TestCase):
    """Verify per-side cpuset.mems on a mocked 4-node system"""

    def setUp(self):
        # Mock CpusetsInit so construction succeeds off cgroup v2; 4 nodes -> "0-3"
        init_patcher = patch('rteval.cpusetmanager.CpusetsInit')
        mock_init = init_patcher.start()
        self.addCleanup(init_patcher.stop)
        mock_init.return_value.supported = True
        mock_init.return_value.numa_nodes = 4

        # Mock Cpuset so _create_cpuset writes to mocks, not real cgroup files.
        # Track the created cpuset objects by name for inspection.
        self.created = {}

        def make_cpuset(name):
            m = MagicMock()
            self.created[name] = m
            return m

        cpuset_patcher = patch('rteval.cpusetmanager.Cpuset', side_effect=make_cpuset)
        cpuset_patcher.start()
        self.addCleanup(cpuset_patcher.stop)

        self.logger = Log()
        self.logger.SetLogVerbosity(Log.ERR)

    def _memnode_arg(self, name):
        """Return the value write_memnode was called with for cpuset `name`"""
        return self.created[name].write_memnode.call_args.args[0]

    def test_numa_flags_pin_per_side_mems(self):
        """Measurement and loads get their named nodes; housekeeping stays all nodes"""
        manager = CpusetManager(
            housekeeping_cpus=[0, 1],
            measurement_cpus=[2, 3, 4, 5],
            logger=self.logger,
            loads_cpus=[6, 7, 8, 9],
            create_loads=True,
            measurement_memnodes="0",
            loads_memnodes="1",
        )
        manager.__enter__()

        self.assertEqual(self._memnode_arg('rteval_measurement'), "0")
        self.assertEqual(self._memnode_arg('rteval_loads'), "1")
        # Housekeeping is not NUMA-flag driven: keeps the all-nodes default
        self.assertEqual(self._memnode_arg('rteval_housekeeping'), "0-3")

    def test_no_numa_flags_defaults_to_all_nodes(self):
        """Without NUMA flags every cpuset.mems spans all nodes (unchanged)"""
        manager = CpusetManager(
            housekeeping_cpus=[0, 1],
            measurement_cpus=[2, 3],
            logger=self.logger,
            loads_cpus=[4, 5],
            create_loads=True,
        )
        manager.__enter__()

        self.assertEqual(self._memnode_arg('rteval_measurement'), "0-3")
        self.assertEqual(self._memnode_arg('rteval_loads'), "0-3")
        self.assertEqual(self._memnode_arg('rteval_housekeeping'), "0-3")

    def test_multi_node_side(self):
        """A multi-node flag value is passed through verbatim"""
        manager = CpusetManager(
            housekeeping_cpus=[],
            measurement_cpus=[0, 1, 2, 3],
            logger=self.logger,
            measurement_memnodes="0,1",
        )
        manager.__enter__()

        self.assertEqual(self._memnode_arg('rteval_measurement'), "0,1")


if __name__ == "__main__":
    unittest.main()
