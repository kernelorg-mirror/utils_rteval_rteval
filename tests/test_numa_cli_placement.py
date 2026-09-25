#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright 2026 John Kacur <jkacur@redhat.com>
#
# Multi-node-gated integration tests for the NUMA placement flags as wired into
# the rteval-cmd script.
#
# The expansion + subset-validation logic lives inline in rteval-cmd (a script,
# not an importable module), so these tests drive the real script as a subprocess
# and exercise that path end to end -- something the mocked unit tests cannot do.
#
# Following the isolcpus philosophy already used in tests/cpusets: the tests run
# when a multi-NUMA-node system is present (a VM configured with more than one
# node, or real multi-socket hardware) and skip cleanly otherwise. No VM is a
# prerequisite for the suite -- these simply skip on single-node machines.
#
# All cases here stop before rteval does any real work: subset validation runs
# before the root check, and the expansion/accept cases use a nonexistent
# --workdir so that even when run as root rteval exits right after resolving the
# CPU lists (no measurement or load is ever started).
#

import os
import sys
import subprocess
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rteval.systopology import SysTopology, get_cpus_for_numa_nodes
from rteval.cpulist_utils import collapse_cpulist, CpuList

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RTEVAL_CMD = os.path.join(REPO_ROOT, "rteval-cmd")

NODES = SysTopology().getnodes()
MULTINODE = len(NODES) > 1

# A workdir that does not exist, so rteval exits at the workdir check (right after
# resolving CPU lists) instead of running anything, even when invoked as root.
BOGUS_WORKDIR = "/nonexistent-rteval-numa-test-dir"


def run_rteval(*args, timeout=60):
    """Run rteval-cmd with args from the repo root; return CompletedProcess."""
    return subprocess.run(
        [sys.executable, RTEVAL_CMD, *args],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=timeout)


@unittest.skipUnless(MULTINODE, "Requires a multi-NUMA-node system")
class TestNumaCliPlacement(unittest.TestCase):
    """Drive rteval-cmd against real multi-node topology (no VM prerequisite)."""

    @classmethod
    def setUpClass(cls):
        # Two distinct nodes to play the measurement / loads roles.
        cls.node_a = NODES[0]
        cls.node_b = NODES[1]
        cls.cpus_a = collapse_cpulist(get_cpus_for_numa_nodes([cls.node_a]))
        cls.cpus_b = collapse_cpulist(get_cpus_for_numa_nodes([cls.node_b]))

    # --- subset validation: runs before the root check, so needs no root -------

    def test_subset_reject_measurement(self):
        """A measurement cpulist on another node is a hard error (exit 1)"""
        cp = run_rteval("--measurement-numa-nodes", str(self.node_a),
                        "--measurement-cpulist", self.cpus_b)
        self.assertEqual(cp.returncode, 1, cp.stderr)
        self.assertIn("--measurement-cpulist", cp.stderr)
        self.assertIn(f"--measurement-numa-nodes {self.node_a}", cp.stderr)
        # Clean message, not a traceback
        self.assertNotIn("Traceback", cp.stderr)

    def test_subset_reject_loads(self):
        """A loads cpulist on another node is a hard error (exit 1)"""
        cp = run_rteval("--loads-numa-nodes", str(self.node_a),
                        "--loads-cpulist", self.cpus_b)
        self.assertEqual(cp.returncode, 1, cp.stderr)
        self.assertIn("--loads-cpulist", cp.stderr)
        self.assertIn(f"--loads-numa-nodes {self.node_a}", cp.stderr)

    def test_subset_accept_measurement(self):
        """A measurement cpulist within the named node passes validation"""
        one = CpuList(self.cpus_a).cpus[0]
        cp = run_rteval("--measurement-numa-nodes", str(self.node_a),
                        "--measurement-cpulist", str(one),
                        "--workdir", BOGUS_WORKDIR)
        # Passing validation means the subset error is never emitted.
        self.assertNotIn("not in --measurement-numa-nodes", cp.stdout + cp.stderr)

    # --- one-sided expansion: observed via --debug, before any work is done ----

    def test_oneside_expansion_measurement(self):
        """--measurement-numa-nodes alone expands to that node's CPU list"""
        cp = run_rteval("--debug", "--measurement-numa-nodes", str(self.node_a),
                        "--workdir", BOGUS_WORKDIR)
        self.assertIn(f"measurement cpulist: {self.cpus_a}", cp.stdout)

    def test_oneside_expansion_loads(self):
        """--loads-numa-nodes alone expands to that node's CPU list"""
        cp = run_rteval("--debug", "--loads-numa-nodes", str(self.node_b),
                        "--workdir", BOGUS_WORKDIR)
        self.assertIn(f"loads cpulist: {self.cpus_b}", cp.stdout)


if __name__ == "__main__":
    unittest.main()
