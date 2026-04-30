#!/usr/bin/python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright 2026 John Kacur <jkacur@redhat.com>
"""
Manager for rteval cpusets with automatic cleanup

This module provides the CpusetManager class which orchestrates cpuset creation
and process migration for rteval workloads (housekeeping and measurement).
Loads use taskset for CPU affinity rather than cpusets.
"""

import time
import os
import glob
from rteval.cpuset import Cpuset, CpusetsInit, TaskMigrate
from rteval.cpulist_utils import collapse_cpulist
from rteval.Log import Log


class CpusetManager:
    """
    Manager for rteval cpusets with automatic cleanup

    Creates 1-2 cpusets based on configuration:
    - rteval_housekeeping: Only if housekeeping_cpus specified
    - rteval_measurement: Always created for measurement workloads

    Load workloads use taskset for CPU affinity (no cpuset needed).

    Uses context manager pattern for automatic cleanup.
    """

    @staticmethod
    def cleanup_leftover_cpusets(logger):
        """
        Clean up any leftover rteval cpusets from previous runs.

        This is called at startup to handle cases where rteval was killed
        and didn't clean up properly.

        Args:
            logger: rteval Log instance for logging
        """
        cpuset_dirs = glob.glob('/sys/fs/cgroup/rteval_*/')
        if not cpuset_dirs:
            logger.log(Log.INFO, "No leftover rteval cpusets found")
            return

        logger.log(Log.INFO, f"Cleaning up {len(cpuset_dirs)} leftover rteval cpusets from previous run")

        for cpuset_dir in cpuset_dirs:
            cpuset_name = os.path.basename(cpuset_dir.rstrip('/'))
            try:
                # Move all processes to root cgroup
                procs_file = os.path.join(cpuset_dir, 'cgroup.procs')
                if os.path.exists(procs_file):
                    with open(procs_file, 'r') as f:
                        pids = f.read().strip().split('\n')

                    for pid in pids:
                        if pid:  # Skip empty lines
                            try:
                                with open('/sys/fs/cgroup/cgroup.procs', 'w') as f:
                                    f.write(pid)
                            except (OSError, IOError):
                                pass  # Process may have exited, ignore

                # Remove the directory
                os.rmdir(cpuset_dir)
                logger.log(Log.DEBUG, f"Removed leftover cpuset: {cpuset_name}")
            except Exception as e:
                logger.log(Log.WARN, f"Failed to clean up {cpuset_name}: {e}")

    def __init__(self, housekeeping_cpus, measurement_cpus, logger):
        """
        Initialize cpuset manager

        Args:
            housekeeping_cpus: List of CPU integers for housekeeping (may be empty)
            measurement_cpus: List of CPU integers for measurement workloads
            logger: rteval Log instance for logging

        Note: Load workloads use taskset for CPU affinity and don't need cpusets.
        """
        # Check cpuset support
        self.cpusets_init = CpusetsInit()
        if not self.cpusets_init.supported:
            raise RuntimeError("cgroup v2 cpuset controller not available")

        # Store parameters
        self.housekeeping_cpus = housekeeping_cpus
        self.measurement_cpus = measurement_cpus
        self.logger = logger

        # Cpuset objects (will be created in __enter__)
        self.housekeeping_cpuset = None
        self.measurement_cpuset = None

        # Get NUMA node range for memory assignment
        self.numa_nodes = f"0-{self.cpusets_init.numa_nodes - 1}" if self.cpusets_init.numa_nodes > 1 else "0"

        self.logger.log(Log.DEBUG, f"CpusetManager initialized: "
                       f"housekeeping={collapse_cpulist(housekeeping_cpus) if housekeeping_cpus else 'none'}, "
                       f"measurement={collapse_cpulist(measurement_cpus)}")

    def __enter__(self):
        """
        Context manager entry: create cpusets

        Returns:
            self for use in with statement
        """
        self.logger.log(Log.INFO, "Creating rteval cpusets...")

        # Create housekeeping cpuset if requested
        if self.housekeeping_cpus:
            self.logger.log(Log.DEBUG, f"Creating rteval_housekeeping cpuset with CPUs {collapse_cpulist(self.housekeeping_cpus)}")
            self.housekeeping_cpuset = Cpuset('rteval_housekeeping')
            self.housekeeping_cpuset.write_memnode(self.numa_nodes)
            self.housekeeping_cpuset.assign_cpus(collapse_cpulist(self.housekeeping_cpus))
            self.housekeeping_cpuset.write_cpu_exclusive(False)  # partition=member

        # Create measurement cpuset
        self.logger.log(Log.DEBUG, f"Creating rteval_measurement cpuset with CPUs {collapse_cpulist(self.measurement_cpus)}")
        self.measurement_cpuset = Cpuset('rteval_measurement')
        self.measurement_cpuset.write_memnode(self.numa_nodes)
        self.measurement_cpuset.assign_cpus(collapse_cpulist(self.measurement_cpus))
        self.measurement_cpuset.write_cpu_exclusive(False)  # partition=member

        self.logger.log(Log.INFO, "Cpusets created successfully")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit: cleanup cpusets

        Moves all processes back to root cgroup and destroys cpusets in reverse order.

        Returns:
            False (don't suppress exceptions)
        """
        self.logger.log(Log.INFO, "Cleaning up rteval cpusets...")

        try:
            # Move all processes back to root cgroup before destroying cpusets
            # Destroy in reverse order of creation

            if self.measurement_cpuset:
                self._migrate_to_root(self.measurement_cpuset, 'rteval_measurement')
                self.measurement_cpuset.destroy()
                self.logger.log(Log.DEBUG, "Destroyed rteval_measurement cpuset")

            if self.housekeeping_cpuset:
                self._migrate_to_root(self.housekeeping_cpuset, 'rteval_housekeeping')
                self.housekeeping_cpuset.destroy()
                self.logger.log(Log.DEBUG, "Destroyed rteval_housekeeping cpuset")

            self.logger.log(Log.INFO, "Cpuset cleanup complete")
        except Exception as e:
            self.logger.log(Log.ERR, f"Error during cpuset cleanup: {e}")

        return False  # Don't suppress exceptions

    def _migrate_to_root(self, cpuset, name):
        """
        Migrate all tasks from a cpuset back to root cgroup

        Args:
            cpuset: Cpuset object to migrate from
            name: Name of cpuset (for logging)
        """
        try:
            tm = TaskMigrate(cpuset, self.cpusets_init)
            migrated, failed = tm.migrate()
            self.logger.log(Log.DEBUG, f"Migrated {migrated} tasks from {name} to root (failed: {failed})")
        except Exception as e:
            self.logger.log(Log.WARN, f"Error migrating tasks from {name}: {e}")

    def migrate_root_tasks_to_housekeeping(self):
        """
        Migrate all tasks from root cgroup to housekeeping cpuset

        Only executes if housekeeping cpuset was created.
        Logs migration results.
        """
        if not self.housekeeping_cpuset:
            self.logger.log(Log.DEBUG, "No housekeeping cpuset, skipping root task migration")
            return

        self.logger.log(Log.INFO, "Migrating system tasks to housekeeping cpuset...")

        try:
            tm = TaskMigrate(self.cpusets_init, self.housekeeping_cpuset)
            migrated, failed = tm.migrate()
            self.logger.log(Log.INFO, f"Migrated {migrated} system tasks to housekeeping (failed: {failed})")
        except Exception as e:
            self.logger.log(Log.ERR, f"Error migrating root tasks to housekeeping: {e}")

    def migrate_measurement_threads(self, pids):
        """
        Migrate measurement subprocess PIDs to rteval_measurement cpuset

        Args:
            pids: List of subprocess PIDs to migrate
        """
        if not pids:
            self.logger.log(Log.DEBUG, "No measurement PIDs to migrate")
            return

        if not self.measurement_cpuset:
            self.logger.log(Log.WARN, "rteval_measurement cpuset not created, cannot migrate measurement threads")
            return

        self.logger.log(Log.DEBUG, f"Migrating {len(pids)} measurement PIDs to rteval_measurement")

        migrated = 0
        failed = 0
        for pid in pids:
            if self.measurement_cpuset.write_pid(pid):
                migrated += 1
            else:
                failed += 1

        self.logger.log(Log.INFO, f"Migrated {migrated} measurement threads to rteval_measurement (failed: {failed})")
