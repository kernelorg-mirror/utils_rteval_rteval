#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
#
# Unit tests for NUMA subset validation and the CPU->node mapping helper
# (validate_cpulist_numa_nodes, get_numa_nodes_for_cpus).
#
# Verifies that a --*-cpulist confined by a --*-numa-nodes flag must stay within
# the named node(s): a subset passes, a cpulist spanning all named nodes passes,
# and a cpulist that leaves the named node(s) is a hard error naming the
# offending CPUs and the node they actually live on.
#
# SysTopology is mocked so the test runs on any system regardless of its
# actual NUMA topology.
#

import sys
import os
import unittest
from unittest.mock import patch

# Add rteval to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rteval.systopology import get_numa_nodes_for_cpus, validate_cpulist_numa_nodes


class TestNumaSubsetValidation(unittest.TestCase):
    """Test subset validation with a mocked 2-node, 8-cpu-per-node system"""

    # Simulate a 2-node system: node 0 -> CPUs 0-7, node 1 -> CPUs 8-15
    NODE_CPUS = {
        0: [0, 1, 2, 3, 4, 5, 6, 7],
        1: [8, 9, 10, 11, 12, 13, 14, 15],
    }

    def setUp(self):
        patcher = patch('rteval.systopology.SysTopology')
        self.mock_systopo = patcher.start()
        self.addCleanup(patcher.stop)
        instance = self.mock_systopo.return_value
        instance.getnodes.return_value = list(self.NODE_CPUS.keys())
        instance.getcpus.side_effect = lambda node: self.NODE_CPUS[node]

    # --- get_numa_nodes_for_cpus ---------------------------------------------

    def test_nodes_for_cpus_empty(self):
        """An empty cpulist yields no nodes (SysTopology untouched)"""
        self.assertEqual(get_numa_nodes_for_cpus([]), [])
        self.mock_systopo.assert_not_called()

    def test_nodes_for_cpus_single_node(self):
        """CPUs entirely within one node map to that node"""
        self.assertEqual(get_numa_nodes_for_cpus([0, 1, 2]), [0])
        self.assertEqual(get_numa_nodes_for_cpus([8, 15]), [1])

    def test_nodes_for_cpus_spanning(self):
        """CPUs spanning both nodes map to both, sorted"""
        self.assertEqual(get_numa_nodes_for_cpus([7, 8]), [0, 1])

    def test_nodes_for_cpus_dedup(self):
        """Repeated CPUs on the same node do not duplicate the node"""
        self.assertEqual(get_numa_nodes_for_cpus([0, 0, 1]), [0])

    # --- validate_cpulist_numa_nodes: passing cases --------------------------

    def test_subset_within_node_passes(self):
        """A cpulist that is a subset of the named node passes"""
        validate_cpulist_numa_nodes([0, 1, 2, 3], [0])

    def test_full_node_passes(self):
        """A cpulist equal to the named node's CPUs passes"""
        validate_cpulist_numa_nodes(self.NODE_CPUS[0], [0])

    def test_spanning_named_nodes_passes(self):
        """A cpulist within the union of the named nodes passes"""
        validate_cpulist_numa_nodes([0, 1, 8, 9], [0, 1])

    def test_empty_cpulist_passes(self):
        """No cpulist means nothing to check"""
        validate_cpulist_numa_nodes([], [0])
        self.mock_systopo.assert_not_called()

    def test_empty_numa_nodes_passes(self):
        """No NUMA flag means no confinement to check"""
        validate_cpulist_numa_nodes([0, 8], [])
        self.mock_systopo.assert_not_called()

    # --- validate_cpulist_numa_nodes: error cases ----------------------------

    def test_cpu_outside_named_node_raises(self):
        """A single CPU outside the named node is a hard error"""
        with self.assertRaises(RuntimeError) as ctx:
            validate_cpulist_numa_nodes([0, 1, 8], [0])
        msg = str(ctx.exception)
        self.assertIn("8", msg)          # offending CPU
        self.assertIn("node", msg)

    def test_cpulist_entirely_outside_raises(self):
        """A cpulist wholly on another node is a hard error"""
        with self.assertRaises(RuntimeError):
            validate_cpulist_numa_nodes([8, 9, 10, 11], [0])

    def test_error_message_names_actual_node_and_flag_prefix(self):
        """The error names the offending CPUs, their node, and the flag prefix"""
        with self.assertRaises(RuntimeError) as ctx:
            validate_cpulist_numa_nodes([8], [0], flag_prefix="--loads")
        msg = str(ctx.exception)
        self.assertIn("--loads-cpulist", msg)
        self.assertIn("--loads-numa-nodes", msg)
        self.assertIn("8", msg)          # offending CPU
        self.assertIn("1", msg)          # node 8 actually lives on


if __name__ == "__main__":
    unittest.main()
