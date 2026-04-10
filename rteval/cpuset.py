#!/usr/bin/python3
# Copyright 2026 John Kacur <jkacur@redhat.com>
""" Module for creating and using cpusets """

import errno
import os
from glob import glob


class Cpuset:
    """ Class for manipulating cpusets """

    mpath = '/sys/fs/cgroup'

    def __init__(self, name=None):
        self.cpuset_name = None
        self._cpuset_path = None
        self.create_cpuset(name)

    @property
    def cpuset_path(self):
        """ Return the cpuset path, for example /sys/fs/cgroup/rteval_0 """
        return self._cpuset_path

    def __str__(self):
        return f'cpuset_name={self.cpuset_name}, cpuset_path={self.cpuset_path}'

    def create_cpuset(self, name=None):
        """ Create a cpuset (cgroup) below /sys/fs/cgroup """
        if name is None:
            raise ValueError("cpuset name cannot be None")
        self.cpuset_name = name
        path = os.path.join(Cpuset.mpath, self.cpuset_name)
        if not os.path.exists(path):
            os.mkdir(path)
        self._cpuset_path = path
        # Enable cpuset controller in parent if needed
        self._enable_controllers()

    def _enable_controllers(self):
        """ Enable cpuset controller in parent cgroup """
        # Get parent path
        parent_path = os.path.dirname(self._cpuset_path)
        if parent_path == '/sys/fs':
            parent_path = '/sys/fs/cgroup'

        subtree_control = os.path.join(parent_path, 'cgroup.subtree_control')
        try:
            # Read current controllers
            with open(subtree_control, 'r', encoding='utf-8') as f:
                current = f.read().strip()

            # Enable cpuset if not already enabled
            # Controllers are space-separated, so split and check
            if 'cpuset' not in current.split():
                with open(subtree_control, 'w', encoding='utf-8') as f:
                    f.write('+cpuset')
        except (OSError, PermissionError):
            # May fail if already enabled or no permissions
            pass

    def assign_cpus(self, cpu_str):
        """
        Assign cpus in list-format to a cpuset
        Note: In cgroup v2, you must call write_memnode() before assign_cpus()
        """
        path = os.path.join(self._cpuset_path, "cpuset.cpus")
        with open(path, 'w', encoding='utf-8') as f:
            f.write(cpu_str)

    def write_pid(self, pid):
        """
        Place a pid in a cpuset
        Returns True if successful, False if the process cannot be moved
        Raises OSError for unexpected errors
        """
        path = os.path.join(self._cpuset_path, "cgroup.procs")
        pid_str = str(pid)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(pid_str)
                f.flush()
            return True
        except OSError as err:
            # EINVAL: Invalid argument (process can't be moved, or invalid PID format)
            # ESRCH: No such process (process died between read and write)
            # EBUSY: Device or resource busy (process can't be moved)
            # EACCES: Permission denied (some kernel threads can't be moved)
            if err.errno in (errno.EINVAL, errno.ESRCH, errno.EBUSY, errno.EACCES):
                return False
            else:
                raise

    def write_memnode(self, memnode):
        """ Place memnode in a cpuset """
        path = os.path.join(self._cpuset_path, "cpuset.mems")
        memnode_str = str(memnode)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(memnode_str)

    def write_cpu_exclusive(self, cpu_exclusive):
        """
        Set CPU partition type (cgroup v2)
        In v2, cpu_exclusive is replaced by cpuset.cpus.partition

        Args:
            cpu_exclusive: True/1/'1' for 'isolated', False/0/'0' for 'member'
        """
        path = os.path.join(self._cpuset_path, "cpuset.cpus.partition")
        if not os.path.exists(path):
            # cpuset.cpus.partition may not exist in all kernels
            return

        # Convert to boolean: handles bool, int, or string input
        if isinstance(cpu_exclusive, str):
            is_exclusive = cpu_exclusive not in ('0', '', 'false', 'False')
        else:
            is_exclusive = bool(cpu_exclusive)

        partition_type = 'isolated' if is_exclusive else 'member'
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(partition_type)
        except OSError:
            # Partition may not be supported or may fail
            pass

    def set_cpu_exclusive(self):
        """ Turn cpu_exclusive on (set partition to isolated) """
        self.write_cpu_exclusive(True)

    def unset_cpu_exclusive(self):
        """ Turn cpu_exclusive off (set partition to member) """
        self.write_cpu_exclusive(False)

    def write_memory_migrate(self, memory_migrate):
        """
        Memory migrate is not available in cgroup v2
        This is kept for API compatibility but does nothing
        """
        pass

    def set_memory_migrate(self):
        """ Memory_migrate not available in cgroup v2 (no-op for compatibility) """
        pass

    def unset_memory_migrate(self):
        """ Memory migrate not available in cgroup v2 (no-op for compatibility) """
        pass

    def destroy(self):
        """
        Remove this cpuset (cgroup directory)
        The cpuset must be empty (no processes) before it can be removed.
        Raises OSError if the directory is not empty or doesn't exist.
        """
        if self._cpuset_path and os.path.exists(self._cpuset_path):
            os.rmdir(self._cpuset_path)

    def __enter__(self):
        """
        Context manager entry point
        Allows usage: with Cpuset('name') as cpuset: ...
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit point
        Automatically destroys the cpuset when exiting the with block
        """
        self.destroy()
        return False  # Don't suppress exceptions

    def get_tasks(self):
        """ Get the tasks (PIDs) currently in a cpuset """
        path = os.path.join(self.cpuset_path, "cgroup.procs")
        with open(path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]


class CpusetsInit(Cpuset):
    """
    CpusetsInit initializes cpusets (cgroup v2)
    It verifies that cgroup v2 is mounted and cpuset controller is available
    This class represents the root cgroup /sys/fs/cgroup
    """

    mpath = '/sys/fs/cgroup'

    def __init__(self):
        self._supported = self._cpuset_supported()
        self._numa_nodes = self._get_numa_nodes() if self._supported else 0
        if self._supported:
            # Set attributes directly for the root cgroup
            self.cpuset_name = None
            self._cpuset_path = Cpuset.mpath

    @property
    def supported(self):
        """ Return True if cpuset is supported """
        return self._supported

    @property
    def numa_nodes(self):
        """ Return the number of numa nodes """
        return self._numa_nodes

    @staticmethod
    def _cpuset_supported():
        """
        Return True if cpusets are supported
        For cgroup v2, check if:
        1. cgroup2 filesystem is available
        2. /sys/fs/cgroup is mounted
        3. cpuset controller is available
        """
        # Check if cgroup2 is in /proc/filesystems
        cgroup2_found = False
        dpath = '/proc/filesystems'
        try:
            with open(dpath, encoding='utf-8') as fp:
                for line in fp:
                    elems = line.strip().split()
                    if len(elems) == 2 and elems[1] == "cgroup2":
                        cgroup2_found = True
                        break
        except OSError:
            return False

        if not cgroup2_found:
            return False

        # Check if /sys/fs/cgroup is mounted and has cpuset controller
        cgroup_path = '/sys/fs/cgroup'
        controllers_file = os.path.join(cgroup_path, 'cgroup.controllers')

        if not os.path.exists(controllers_file):
            return False

        try:
            with open(controllers_file, encoding='utf-8') as f:
                controllers = f.read().strip().split()
                return 'cpuset' in controllers
        except OSError:
            return False

    @staticmethod
    def _get_numa_nodes():
        """
        return the number of numa nodes
        used by init to set _numa_nodes
        Users of this class should use the "numa_nodes" method
        """
        return len(glob('/sys/devices/system/node/node*'))


class TaskMigrate:
    """ A class for migrating a set of pids from one cpuset to another """

    def __init__(self, cpuset_from, cpuset_to):
        self.cpuset_from = cpuset_from
        self.cpuset_to = cpuset_to
        # memory_migrate is not available in cgroup v2, but keep for API compat
        self.cpuset_to.set_memory_migrate()
        self.migrated = 0
        self.failed = 0

    def migrate(self):
        """ Do the migration, only attempt on pids where this is allowed """
        self.migrated = 0
        self.failed = 0
        tasks = self.cpuset_from.get_tasks()
        for task in tasks:
            if self.cpuset_to.write_pid(task):
                self.migrated += 1
            else:
                self.failed += 1
        return self.migrated, self.failed


if __name__ == '__main__':

    cpusets_init = CpusetsInit()
    print(f'cpusets_init.supported = {cpusets_init.supported}')
    if cpusets_init.supported:
        print(f'cpusets_init.numa_nodes = {cpusets_init.numa_nodes}')
        print(f'cpusets_init.cpuset_path = {cpusets_init.cpuset_path}')

        # Creating and manipulating cgroups requires root permissions
        print("\nTo test cpuset creation, run as root:")
        print("  sudo python3 cpuset.py")

        try:
            # Example 1: Using context manager (recommended)
            print("\n" + "="*60)
            print("Example 1: Context Manager (automatic cleanup)")
            print("="*60)
            with Cpuset('rteval_demo') as cpuset:
                print(f"Created cpuset: {cpuset.cpuset_path}")
                cpuset.write_memnode('0')
                cpuset.assign_cpus('0-3')
                print(f"Configured cpuset with CPUs 0-3")
            print("Context manager exited - cpuset automatically destroyed!")

            # Example 2: Manual cleanup (traditional approach)
            print("\n" + "="*60)
            print("Example 2: Manual Cleanup (traditional)")
            print("="*60)
            print("Creating cpuset0...")
            cpuset0 = Cpuset('rteval_0')
            print("Creating cpuset1...")
            cpuset1 = Cpuset('rteval_1')

            # In cgroup v2, must set mems before cpus
            print("Setting memory nodes...")
            cpuset0.write_memnode('0')
            cpuset1.write_memnode('0')

            print("Assigning CPUs to cpuset0 (0-4,8-11)...")
            cpuset0.assign_cpus('0-4,8-11')
            print("Assigning CPUs to cpuset1 (5-7)...")
            cpuset1.assign_cpus('5-7')

            print("Setting cpu_exclusive on cpuset1...")
            cpuset1.set_cpu_exclusive()

            print("Migrating tasks from root to cpuset0...")
            tm = TaskMigrate(cpusets_init, cpuset0)
            migrated, failed = tm.migrate()

            print(f"\nMigration complete: {migrated} moved, {failed} skipped")
            print(f"Tasks now in cpuset0: {len(cpuset0.get_tasks())}")

            # Cleanup: move processes back to root before removing cgroups
            print("\nCleaning up: moving processes back to root cgroup...")
            tm_back = TaskMigrate(cpuset0, cpusets_init)
            moved_back, _ = tm_back.migrate()
            print(f"Moved {moved_back} processes back to root")

            cpuset0.destroy()
            cpuset1.destroy()
            print("Manual cleanup complete")
        except PermissionError as e:
            print(f"\nPermission denied: {e}")
            print("Run as root to create and manipulate cgroups")
        except Exception as e:
            print(f"\nError at step: {e}")
            import traceback
            traceback.print_exc()
