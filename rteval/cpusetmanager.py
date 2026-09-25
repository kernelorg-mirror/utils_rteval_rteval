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

    Creates 1-3 cpusets based on configuration:
    - rteval_housekeeping: Only if housekeeping_cpus specified
    - rteval_loads: Only if create_loads is True (partition=member)
    - rteval_measurement: Created unless create_measurement is False
      (e.g. --onlyload, which runs no measurement workloads)

    Unless create_loads is set, load workloads use taskset for CPU affinity
    (no cpuset needed).

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

    def __init__(self, housekeeping_cpus, measurement_cpus, logger, housekeeping_isolated=False, create_measurement=True, measurement_member=False, loads_cpus=None, create_loads=False, measurement_memnodes=None, loads_memnodes=None):
        """
        Initialize cpuset manager

        Args:
            housekeeping_cpus: List of CPU integers for housekeeping (may be empty)
            measurement_cpus: List of CPU integers for measurement workloads
            logger: rteval Log instance for logging
            housekeeping_isolated: If True, use partition=isolated for housekeeping (default: False = partition=member)
            create_measurement: If False, skip creating the rteval_measurement cpuset
                (e.g. --onlyload, which runs no measurement workloads; default: True)
            measurement_member: If True, use partition=member for measurement, allowing
                loads and measurement to share CPUs (default: False = partition=isolated)
            loads_cpus: List of CPU integers for load workloads (used only when
                create_loads is True)
            create_loads: If True, create the rteval_loads cpuset (partition=member)
                and confine loads to it instead of relying only on taskset
                (default: False = loads use taskset, as before)
            measurement_memnodes: NUMA node spec (string) for the measurement
                cpuset.mems, set when --measurement-numa-nodes is used. When None,
                cpuset.mems spans all nodes (pre-NUMA-flag behavior).
            loads_memnodes: NUMA node spec (string) for the loads cpuset.mems,
                set when --loads-numa-nodes is used. When None, spans all nodes.

        Note: Unless create_loads is set, load workloads use taskset for CPU
        affinity and don't need a cpuset. The load cpuset is always a member
        partition (confinement only), so its CPUs stay in the root cgroup's
        effective set -- the main rteval process, when left in root (no
        housekeeping), still has those CPUs to run on.
        """
        # Check cpuset support
        self.cpusets_init = CpusetsInit()
        if not self.cpusets_init.supported:
            raise RuntimeError("cgroup v2 cpuset controller not available")

        # Store parameters
        self.housekeeping_cpus = housekeeping_cpus
        self.measurement_cpus = measurement_cpus
        self.logger = logger
        self.housekeeping_isolated = housekeeping_isolated
        self.create_measurement = create_measurement
        self.measurement_member = measurement_member
        self.loads_cpus = loads_cpus if loads_cpus is not None else []
        self.create_loads = create_loads
        # Per-side NUMA memory nodes (None => all nodes, set below). Housekeeping
        # keeps the all-nodes default; only the NUMA-flag-driven sides are pinned.
        self.measurement_memnodes = measurement_memnodes
        self.loads_memnodes = loads_memnodes

        # Cpuset objects (will be created in __enter__)
        self.housekeeping_cpuset = None
        self.loads_cpuset = None
        self.measurement_cpuset = None

        # Get NUMA node range for memory assignment
        self.numa_nodes = f"0-{self.cpusets_init.numa_nodes - 1}" if self.cpusets_init.numa_nodes > 1 else "0"

        self.logger.log(Log.DEBUG, f"CpusetManager initialized: "
                       f"housekeeping={collapse_cpulist(housekeeping_cpus) if housekeeping_cpus else 'none'}, "
                       f"measurement={collapse_cpulist(measurement_cpus)}")

    def _create_cpuset(self, name, cpus, isolated, memnodes=None):
        """
        Create a single cpuset with the given CPUs and partition type.

        Args:
            name: cpuset name (e.g. 'rteval_measurement')
            cpus: list of CPU integers to assign
            isolated: True for partition=isolated, False for partition=member
            memnodes: NUMA node spec (string) for cpuset.mems. When None,
                defaults to self.numa_nodes (all nodes), preserving the
                pre-NUMA-flag behavior.

        Returns:
            the created Cpuset object
        """
        if memnodes is None:
            memnodes = self.numa_nodes
        partition_type = "isolated" if isolated else "member"
        self.logger.log(Log.DEBUG, f"Creating {name} cpuset with CPUs "
                        f"{collapse_cpulist(cpus)} (partition={partition_type}, "
                        f"mems={memnodes})")
        cpuset = Cpuset(name)
        cpuset.write_memnode(memnodes)
        cpuset.assign_cpus(collapse_cpulist(cpus))
        cpuset.write_cpu_exclusive(isolated)  # partition=isolated if True, member if False
        return cpuset

    def __enter__(self):
        """
        Context manager entry: create cpusets

        Returns:
            self for use in with statement
        """
        self.logger.log(Log.INFO, "Creating rteval cpusets...")

        # Creation order is not significant: each cpuset is created from an
        # explicit, pre-computed disjoint CPU list, so creating one never
        # changes what another gets. The main rteval process is placed into
        # housekeeping by the separate migrate_root_tasks_to_housekeeping()
        # sweep, which runs after all cpusets exist; the workloads then self-home
        # into their own cpusets before exec. The only overlap ever allowed is
        # member+member (loads + --measurement-member), which needs no ordering
        # since member partitions are not exclusive; the isolated-measurement
        # overlap case is rejected upstream. Measurement (the potential isolated
        # partition) is created last as a defensive habit.

        # Create housekeeping cpuset if requested.
        if self.housekeeping_cpus:
            self.housekeeping_cpuset = self._create_cpuset(
                'rteval_housekeeping', self.housekeeping_cpus, self.housekeeping_isolated)

        # Create loads cpuset if requested (always a member partition, so its
        # CPUs remain in the root cgroup's effective set)
        if self.create_loads:
            self.loads_cpuset = self._create_cpuset(
                'rteval_loads', self.loads_cpus, isolated=False,
                memnodes=self.loads_memnodes)

        # Create measurement cpuset (skipped when there are no measurement
        # workloads, e.g. --onlyload)
        if self.create_measurement:
            self.measurement_cpuset = self._create_cpuset(
                'rteval_measurement', self.measurement_cpus, isolated=not self.measurement_member,
                memnodes=self.measurement_memnodes)

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
            # Move all processes back to root cgroup before destroying cpusets.
            # Destroy in reverse order of creation.
            self._destroy_cpuset(self.measurement_cpuset, 'rteval_measurement')
            self._destroy_cpuset(self.loads_cpuset, 'rteval_loads')
            self._destroy_cpuset(self.housekeeping_cpuset, 'rteval_housekeeping')

            self.logger.log(Log.INFO, "Cpuset cleanup complete")
        except Exception as e:
            self.logger.log(Log.ERR, f"Error during cpuset cleanup: {e}")

        return False  # Don't suppress exceptions

    def _destroy_cpuset(self, cpuset, name):
        """
        Migrate a cpuset's tasks back to root and destroy it (no-op if None).

        Args:
            cpuset: Cpuset object to tear down, or None
            name: Name of cpuset (for logging)
        """
        if not cpuset:
            return
        self._migrate_to_root(cpuset, name)
        cpuset.destroy()
        self.logger.log(Log.DEBUG, f"Destroyed {name} cpuset")

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
