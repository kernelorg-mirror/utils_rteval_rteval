#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright 2026 John Kacur <jkacur@redhat.com>
"""
Unit tests for rteval CpusetManager functionality.

Tests verify cpuset creation, partition types, task migration, and the
--housekeeping-isolated flag functionality.
"""

import unittest
import os
import sys
import subprocess
import tempfile

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rteval.cpusetmanager import CpusetManager
from rteval import cpuset
from rteval.Log import Log


class TestCpusetManagerBasic(unittest.TestCase):
    """Test basic CpusetManager functionality (non-root tests)"""

    def test_import_cpusetmanager(self):
        """Test that CpusetManager can be imported"""
        self.assertIsNotNone(CpusetManager)

    def test_cleanup_leftover_cpusets_callable(self):
        """Test that cleanup_leftover_cpusets method exists"""
        self.assertTrue(hasattr(CpusetManager, 'cleanup_leftover_cpusets'))
        self.assertTrue(callable(CpusetManager.cleanup_leftover_cpusets))


@unittest.skipUnless(os.geteuid() == 0, "Requires root permissions")
@unittest.skipUnless(cpuset.CpusetsInit().supported, "Requires cgroup v2 support")
class TestCpusetManagerHousekeepingPartitions(unittest.TestCase):
    """Test housekeeping cpuset partition type behavior"""

    def setUp(self):
        """Clean up before each test"""
        self.logger = Log()
        self.logger.SetLogVerbosity(Log.ERR | Log.WARN)
        try:
            cpuset.cleanup_cpusets('rteval_*', force=True, recursive=False)
        except:
            pass

    def tearDown(self):
        """Clean up after each test"""
        try:
            cpuset.cleanup_cpusets('rteval_*', force=True, recursive=False)
        except:
            pass

    def test_housekeeping_default_partition_member(self):
        """Test that housekeeping cpuset defaults to partition=member"""
        with CpusetManager(
            housekeeping_cpus=[0, 1],
            measurement_cpus=[2, 3],
            logger=self.logger,
            housekeeping_isolated=False
        ) as manager:
            # Check housekeeping partition type
            hk_partition_file = '/sys/fs/cgroup/rteval_housekeeping/cpuset.cpus.partition'
            with open(hk_partition_file) as f:
                partition = f.read().strip()
            self.assertEqual(partition, 'member',
                           "Housekeeping cpuset should have partition=member by default")

    def test_housekeeping_isolated_flag(self):
        """Test that housekeeping_isolated=True makes partition=isolated"""
        with CpusetManager(
            housekeeping_cpus=[0, 1],
            measurement_cpus=[2, 3],
            logger=self.logger,
            housekeeping_isolated=True
        ) as manager:
            # Check housekeeping partition type
            hk_partition_file = '/sys/fs/cgroup/rteval_housekeeping/cpuset.cpus.partition'
            with open(hk_partition_file) as f:
                partition = f.read().strip()
            self.assertEqual(partition, 'isolated',
                           "Housekeeping cpuset should have partition=isolated when flag is True")

    def test_measurement_always_isolated(self):
        """Test that measurement cpuset is always partition=isolated"""
        # Test with housekeeping_isolated=False
        with CpusetManager(
            housekeeping_cpus=[0, 1],
            measurement_cpus=[2, 3],
            logger=self.logger,
            housekeeping_isolated=False
        ) as manager:
            measurement_partition_file = '/sys/fs/cgroup/rteval_measurement/cpuset.cpus.partition'
            with open(measurement_partition_file) as f:
                partition = f.read().strip()
            self.assertEqual(partition, 'isolated',
                           "Measurement cpuset should always be partition=isolated")

        # Test with housekeeping_isolated=True
        with CpusetManager(
            housekeeping_cpus=[0, 1],
            measurement_cpus=[2, 3],
            logger=self.logger,
            housekeeping_isolated=True
        ) as manager:
            measurement_partition_file = '/sys/fs/cgroup/rteval_measurement/cpuset.cpus.partition'
            with open(measurement_partition_file) as f:
                partition = f.read().strip()
            self.assertEqual(partition, 'isolated',
                           "Measurement cpuset should always be partition=isolated")

    def test_no_housekeeping_cpuset_created_when_empty(self):
        """Test that housekeeping cpuset is not created when housekeeping_cpus is empty"""
        with CpusetManager(
            housekeeping_cpus=[],
            measurement_cpus=[0, 1],
            logger=self.logger,
            housekeeping_isolated=False
        ) as manager:
            # Check that housekeeping cpuset does NOT exist
            hk_path = '/sys/fs/cgroup/rteval_housekeeping'
            self.assertFalse(os.path.exists(hk_path),
                           "Housekeeping cpuset should not exist when housekeeping_cpus is empty")

            # Check that measurement cpuset DOES exist
            measurement_path = '/sys/fs/cgroup/rteval_measurement'
            self.assertTrue(os.path.exists(measurement_path),
                          "Measurement cpuset should exist")


@unittest.skipUnless(os.geteuid() == 0, "Requires root permissions")
@unittest.skipUnless(cpuset.CpusetsInit().supported, "Requires cgroup v2 support")
class TestCpusetManagerCLIIntegration(unittest.TestCase):
    """Test rteval-cmd integration with --housekeeping-isolated"""

    def setUp(self):
        """Clean up before each test"""
        try:
            cpuset.cleanup_cpusets('rteval_*', force=True, recursive=False)
        except:
            pass

    def tearDown(self):
        """Clean up after each test"""
        try:
            cpuset.cleanup_cpusets('rteval_*', force=True, recursive=False)
        except:
            pass

    def test_housekeeping_isolated_requires_cpusets(self):
        """Test that --housekeeping-isolated requires --cpusets"""
        result = subprocess.run(
            [sys.executable, '/home/jkacur/src/rteval/rteval-cmd',
             '--housekeeping', '0-1', '--housekeeping-isolated',
             '--duration', '1', '--onlyload'],
            capture_output=True,
            text=True
        )

        self.assertNotEqual(result.returncode, 0,
                          "--housekeeping-isolated without --cpusets should fail")
        self.assertIn('requires --cpusets', result.stderr,
                     "Error message should mention --cpusets requirement")

    def test_housekeeping_isolated_requires_housekeeping(self):
        """Test that --housekeeping-isolated requires --housekeeping"""
        result = subprocess.run(
            [sys.executable, '/home/jkacur/src/rteval/rteval-cmd',
             '--cpusets', '--housekeeping-isolated',
             '--duration', '1', '--onlyload'],
            capture_output=True,
            text=True
        )

        self.assertNotEqual(result.returncode, 0,
                          "--housekeeping-isolated without --housekeeping should fail")
        self.assertIn('requires --housekeeping', result.stderr,
                     "Error message should mention --housekeeping requirement")

    def test_housekeeping_isolated_help_text(self):
        """Test that --housekeeping-isolated appears in help"""
        result = subprocess.run(
            [sys.executable, '/home/jkacur/src/rteval/rteval-cmd', '--help'],
            capture_output=True,
            text=True
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn('--housekeeping-isolated', result.stdout,
                     "--housekeeping-isolated should appear in help")
        self.assertIn('partition=isolated', result.stdout,
                     "Help should mention partition=isolated")

    def test_housekeeping_help_text_accuracy(self):
        """Test that --housekeeping help text is accurate (no longer says 'isolated CPUs')"""
        result = subprocess.run(
            [sys.executable, '/home/jkacur/src/rteval/rteval-cmd', '--help'],
            capture_output=True,
            text=True
        )

        self.assertEqual(result.returncode, 0)
        # Find the --housekeeping help text
        lines = result.stdout.split('\n')
        housekeeping_help = None
        for i, line in enumerate(lines):
            if '--housekeeping' in line and '--housekeeping-isolated' not in line:
                # Get this line and potentially the next line (help text may wrap)
                housekeeping_help = line
                if i + 1 < len(lines):
                    housekeeping_help += ' ' + lines[i + 1]
                break

        self.assertIsNotNone(housekeeping_help, "--housekeeping should be in help")
        # Should NOT say "isolated CPUs"
        self.assertNotIn('isolated CPUs', housekeeping_help,
                        "--housekeeping help should not incorrectly say 'isolated CPUs'")
        # Should say something about system tasks
        self.assertIn('system tasks', housekeeping_help,
                     "--housekeeping help should mention system tasks")


@unittest.skipUnless(os.geteuid() == 0, "Requires root permissions")
@unittest.skipUnless(cpuset.CpusetsInit().supported, "Requires cgroup v2 support")
class TestCpusetManagerCleanup(unittest.TestCase):
    """Test cleanup_leftover_cpusets functionality"""

    def setUp(self):
        """Clean up before each test"""
        self.logger = Log()
        self.logger.SetLogVerbosity(Log.ERR | Log.WARN)
        try:
            cpuset.cleanup_cpusets('rteval_*', force=True, recursive=False)
        except:
            pass

    def tearDown(self):
        """Clean up after each test"""
        try:
            cpuset.cleanup_cpusets('rteval_*', force=True, recursive=False)
        except:
            pass

    def test_cleanup_removes_leftover_cpusets(self):
        """Test that cleanup removes leftover rteval cpusets"""
        # Create some leftover cpusets
        cs1 = cpuset.Cpuset('rteval_test1')
        cs1.write_memnode('0')
        cs1.assign_cpus('0')

        cs2 = cpuset.Cpuset('rteval_test2')
        cs2.write_memnode('0')
        cs2.assign_cpus('1')

        # Verify they exist
        self.assertTrue(os.path.exists('/sys/fs/cgroup/rteval_test1'))
        self.assertTrue(os.path.exists('/sys/fs/cgroup/rteval_test2'))

        # Run cleanup
        CpusetManager.cleanup_leftover_cpusets(self.logger)

        # Verify they're gone
        self.assertFalse(os.path.exists('/sys/fs/cgroup/rteval_test1'),
                        "cleanup should remove rteval_test1")
        self.assertFalse(os.path.exists('/sys/fs/cgroup/rteval_test2'),
                        "cleanup should remove rteval_test2")

    def test_cleanup_logs_when_no_cpusets(self):
        """Test that cleanup handles no leftover cpusets gracefully"""
        # Make sure no rteval cpusets exist
        try:
            cpuset.cleanup_cpusets('rteval_*', force=True, recursive=False)
        except:
            pass

        # This should not raise an exception
        try:
            CpusetManager.cleanup_leftover_cpusets(self.logger)
        except Exception as e:
            self.fail(f"cleanup_leftover_cpusets raised exception: {e}")


@unittest.skipUnless(os.geteuid() == 0, "Requires root permissions")
@unittest.skipUnless(cpuset.CpusetsInit().supported, "Requires cgroup v2 support")
class TestCpusetManagerTaskMigration(unittest.TestCase):
    """Test task migration functionality"""

    def setUp(self):
        """Clean up before each test"""
        self.logger = Log()
        self.logger.SetLogVerbosity(Log.ERR | Log.WARN)
        try:
            cpuset.cleanup_cpusets('rteval_*', force=True, recursive=False)
        except:
            pass

    def tearDown(self):
        """Clean up after each test and move current process back to root"""
        # Move current process back to root
        try:
            ci = cpuset.CpusetsInit()
            ci.write_pid(os.getpid())
        except:
            pass

        # Clean up cpusets
        try:
            cpuset.cleanup_cpusets('rteval_*', force=True, recursive=False)
        except:
            pass

    def test_migrate_root_tasks_to_housekeeping(self):
        """Test migrating root tasks to housekeeping cpuset"""
        with CpusetManager(
            housekeeping_cpus=[0, 1],
            measurement_cpus=[2, 3],
            logger=self.logger,
            housekeeping_isolated=False
        ) as manager:
            # Migrate root tasks
            manager.migrate_root_tasks_to_housekeeping()

            # Verify some tasks were migrated
            with open('/sys/fs/cgroup/rteval_housekeeping/cgroup.procs') as f:
                tasks = f.read().strip().split('\n')
                tasks = [t for t in tasks if t]  # Filter empty strings

            self.assertGreater(len(tasks), 0,
                             "Should have migrated some tasks to housekeeping")

    def test_migrate_measurement_threads(self):
        """Test migrating measurement threads to measurement cpuset"""
        with CpusetManager(
            housekeeping_cpus=[0, 1],
            measurement_cpus=[2, 3],
            logger=self.logger,
            housekeeping_isolated=False
        ) as manager:
            # Use current process as a test measurement thread
            current_pid = os.getpid()

            # Migrate
            manager.migrate_measurement_threads([current_pid])

            # Verify PID is in measurement cpuset
            with open('/sys/fs/cgroup/rteval_measurement/cgroup.procs') as f:
                tasks = f.read().strip().split('\n')

            self.assertIn(str(current_pid), tasks,
                         "Current PID should be in measurement cpuset")

    def test_no_migration_when_no_housekeeping(self):
        """Test that root task migration is skipped when no housekeeping cpuset"""
        with CpusetManager(
            housekeeping_cpus=[],
            measurement_cpus=[0, 1],
            logger=self.logger,
            housekeeping_isolated=False
        ) as manager:
            # This should not raise an exception
            try:
                manager.migrate_root_tasks_to_housekeeping()
            except Exception as e:
                self.fail(f"migrate_root_tasks_to_housekeeping raised exception: {e}")


def suite():
    """Create test suite"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestCpusetManagerBasic))
    suite.addTests(loader.loadTestsFromTestCase(TestCpusetManagerHousekeepingPartitions))
    suite.addTests(loader.loadTestsFromTestCase(TestCpusetManagerCLIIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestCpusetManagerCleanup))
    suite.addTests(loader.loadTestsFromTestCase(TestCpusetManagerTaskMigration))

    return suite


if __name__ == '__main__':
    # Check if running as root
    if os.geteuid() != 0:
        print("\n" + "="*60)
        print("WARNING: Not running as root")
        print("="*60)
        print("Most tests require root permissions.")
        print("\nTo run tests:")
        print("  sudo python3 -m unittest tests.test_cpusetmanager -v")
        print("="*60 + "\n")

    # Check cgroup v2 support
    ci = cpuset.CpusetsInit()
    if not ci.supported:
        print("\n" + "="*60)
        print("WARNING: cgroup v2 not supported")
        print("="*60)
        print("Most tests require cgroup v2 support.")
        print("="*60 + "\n")

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite())

    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
