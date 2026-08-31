#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
#
# Unit test for NUMA node list parsing (parse_numa_node_list)
#
# Verifies that the --measurement-numa-nodes / --loads-numa-nodes argument
# strings are parsed into sorted integer lists, that valid syntax (single
# nodes, ranges, comma-separated combinations) is accepted, and that malformed
# input or nonexistent nodes are rejected.
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

from rteval.systopology import parse_numa_node_list


class TestNumaNodeParsing(unittest.TestCase):
    """Test suite for parse_numa_node_list with a mocked 4-node system"""

    # Simulate a system with NUMA nodes 0, 1, 2, 3
    MOCK_NODES = [0, 1, 2, 3]

    def setUp(self):
        patcher = patch('rteval.systopology.SysTopology')
        self.mock_systopo = patcher.start()
        self.addCleanup(patcher.stop)
        self.mock_systopo.return_value.getnodes.return_value = self.MOCK_NODES

    def test_empty_returns_empty_list(self):
        """Empty/None input yields an empty list (no NUMA flag given)"""
        self.assertEqual(parse_numa_node_list(""), [])
        self.assertEqual(parse_numa_node_list(None), [])

    def test_single_node(self):
        """A single node parses to a one-element list"""
        self.assertEqual(parse_numa_node_list("0"), [0])
        self.assertEqual(parse_numa_node_list("2"), [2])

    def test_range(self):
        """A range expands to each node in the range, inclusive"""
        self.assertEqual(parse_numa_node_list("0-1"), [0, 1])
        self.assertEqual(parse_numa_node_list("0-3"), [0, 1, 2, 3])

    def test_mixed_range_and_singles(self):
        """Comma-separated ranges and singles combine and sort"""
        self.assertEqual(parse_numa_node_list("0,2-3"), [0, 2, 3])
        self.assertEqual(parse_numa_node_list("3,1,0"), [0, 1, 3])

    def test_deduplication(self):
        """Duplicate nodes collapse to a unique, sorted list"""
        self.assertEqual(parse_numa_node_list("3,3,0,0"), [0, 3])

    def test_nonexistent_node_raises(self):
        """A node that does not exist on the system is rejected"""
        with self.assertRaises(RuntimeError):
            parse_numa_node_list("5")
        with self.assertRaises(RuntimeError):
            parse_numa_node_list("2,5")

    def test_nonexistent_node_message(self):
        """The error names the offending node and the available nodes"""
        with self.assertRaises(RuntimeError) as ctx:
            parse_numa_node_list("5", "--measurement-numa-nodes")
        msg = str(ctx.exception)
        self.assertIn("5", msg)
        self.assertIn("--measurement-numa-nodes", msg)

    def test_non_integer_raises(self):
        """Non-integer tokens are rejected as malformed"""
        with self.assertRaises(RuntimeError):
            parse_numa_node_list("x")
        with self.assertRaises(RuntimeError):
            parse_numa_node_list("0,foo")

    def test_malformed_range_raises(self):
        """Incomplete or reversed ranges are rejected as malformed"""
        for bad in ("0-", "-1", "0--1", "3-1"):
            with self.assertRaises(RuntimeError):
                parse_numa_node_list(bad)


if __name__ == "__main__":
    unittest.main()
