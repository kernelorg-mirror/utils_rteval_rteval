#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
#
# Unit test for expanding NUMA nodes into CPUs (get_cpus_for_numa_nodes)
#
# Verifies that a list of NUMA node integers is expanded into the CPUs that
# belong to those nodes, that the result is sorted and deduplicated, and that
# an empty node list yields an empty CPU list.
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

from rteval.systopology import get_cpus_for_numa_nodes


class TestNumaCpuGeneration(unittest.TestCase):
    """Test get_cpus_for_numa_nodes with a mocked 2-node, 8-cpu-per-node system"""

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

    def test_empty_returns_empty_list(self):
        """An empty node list yields an empty CPU list (SysTopology untouched)"""
        self.assertEqual(get_cpus_for_numa_nodes([]), [])
        self.mock_systopo.assert_not_called()

    def test_single_node(self):
        """A single node expands to exactly that node's CPUs"""
        self.assertEqual(get_cpus_for_numa_nodes([0]), [0, 1, 2, 3, 4, 5, 6, 7])
        self.assertEqual(get_cpus_for_numa_nodes([1]),
                         [8, 9, 10, 11, 12, 13, 14, 15])

    def test_multiple_nodes_combined_and_sorted(self):
        """Multiple nodes combine into one sorted CPU list"""
        self.assertEqual(get_cpus_for_numa_nodes([0, 1]), list(range(16)))

    def test_node_order_does_not_affect_result(self):
        """CPUs come back sorted regardless of the node list order"""
        self.assertEqual(get_cpus_for_numa_nodes([1, 0]), list(range(16)))

    def test_deduplication(self):
        """A repeated node does not duplicate its CPUs"""
        self.assertEqual(get_cpus_for_numa_nodes([0, 0]),
                         [0, 1, 2, 3, 4, 5, 6, 7])


if __name__ == "__main__":
    unittest.main()
