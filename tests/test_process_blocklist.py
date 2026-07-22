#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright 2026 John Kacur <jkacur@redhat.com>
"""
Unit tests for process blocklist functionality in rteval.

Tests verify that critical system processes (systemd, systemd-logind, etc.)
are never moved to custom cpusets to prevent system instability and shutdown issues.
"""

import unittest
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rteval import cpuset


class TestProcessBlocklist(unittest.TestCase):
    """Test cases for process blocklist functionality"""

    def test_blocklist_constant_exists(self):
        """Test that PROCESS_BLOCKLIST is defined"""
        self.assertIsNotNone(cpuset.PROCESS_BLOCKLIST)
        self.assertIsInstance(cpuset.PROCESS_BLOCKLIST, set)
        self.assertGreater(len(cpuset.PROCESS_BLOCKLIST), 0)

    def test_blocklist_contains_critical_processes(self):
        """Test that blocklist contains expected critical processes"""
        expected_processes = {'systemd', 'systemd-logind', 'systemd-journald'}
        for proc in expected_processes:
            self.assertIn(proc, cpuset.PROCESS_BLOCKLIST,
                         f"Critical process '{proc}' should be in blocklist")

    def test_get_process_name_for_init(self):
        """Test getting process name for PID 1 (init/systemd)"""
        name = cpuset.Cpuset._get_process_name(1)
        self.assertIsNotNone(name)
        # PID 1 is typically systemd on modern systems, but could be init
        self.assertIn(name, ['systemd', 'init'],
                     f"PID 1 should be systemd or init, got: {name}")

    def test_get_process_name_for_nonexistent_pid(self):
        """Test getting process name for non-existent PID"""
        # Use a very high PID that's unlikely to exist
        name = cpuset.Cpuset._get_process_name(999999)
        self.assertIsNone(name)

    def test_get_process_name_for_self(self):
        """Test getting process name for our own process"""
        pid = os.getpid()
        name = cpuset.Cpuset._get_process_name(pid)
        self.assertIsNotNone(name)
        # Should be python3 or similar
        self.assertIn('python', name.lower())

    def test_is_process_blocklisted_for_init(self):
        """Test that PID 1 (systemd) is blocklisted"""
        # This test works without root - just checks if PID 1 would be blocked
        is_blocked = cpuset.Cpuset._is_process_blocklisted(1)
        self.assertTrue(is_blocked, "PID 1 (systemd/init) should be blocklisted")

    def test_is_process_blocklisted_for_normal_process(self):
        """Test that normal processes are not blocklisted"""
        pid = os.getpid()
        is_blocked = cpuset.Cpuset._is_process_blocklisted(pid)
        self.assertFalse(is_blocked, "Normal processes should not be blocklisted")

    def test_is_process_blocklisted_for_nonexistent_pid(self):
        """Test that non-existent PIDs are not considered blocklisted"""
        is_blocked = cpuset.Cpuset._is_process_blocklisted(999999)
        self.assertFalse(is_blocked, "Non-existent PIDs should not be blocklisted")

    @unittest.skipUnless(os.geteuid() == 0, "Requires root permissions")
    def test_write_pid_blocks_systemd(self):
        """Test that write_pid actually blocks systemd from being moved"""
        ci = cpuset.CpusetsInit()
        if not ci.supported:
            self.skipTest("cgroup v2 not supported")

        cs = cpuset.Cpuset('test_blocklist_systemd')

        try:
            cs.write_memnode('0')
            cs.assign_cpus('0')

            # Try to move PID 1 (systemd)
            result = cs.write_pid(1)

            # Should return False (blocked)
            self.assertFalse(result, "write_pid should return False for systemd (PID 1)")

            # Verify PID 1 is NOT in the cpuset
            tasks = cs.get_tasks()
            self.assertNotIn('1', tasks, "PID 1 should not be in the cpuset")

        finally:
            # Cleanup
            try:
                tm = cpuset.TaskMigrate(cs, ci)
                tm.migrate()
                cs.destroy()
            except:
                pass

    @unittest.skipUnless(os.geteuid() == 0, "Requires root permissions")
    def test_write_pid_allows_normal_process(self):
        """Test that write_pid still allows normal processes to be moved"""
        ci = cpuset.CpusetsInit()
        if not ci.supported:
            self.skipTest("cgroup v2 not supported")

        cs = cpuset.Cpuset('test_blocklist_normal')

        try:
            cs.write_memnode('0')
            cs.assign_cpus('0')

            # Try to move our own PID
            pid = os.getpid()
            result = cs.write_pid(pid)

            # Should return True (allowed)
            self.assertTrue(result, "write_pid should return True for normal processes")

            # Verify our PID is in the cpuset
            tasks = cs.get_tasks()
            self.assertIn(str(pid), tasks, "Our PID should be in the cpuset")

        finally:
            # Cleanup - migrate back and destroy
            try:
                tm = cpuset.TaskMigrate(cs, ci)
                tm.migrate()
                cs.destroy()
            except:
                pass


if __name__ == '__main__':
    unittest.main()
