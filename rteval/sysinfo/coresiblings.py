# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
#
#   Copyright 2026   John Kacur <jkacur@redhat.com>
#

import os
from rteval.cpulist_utils import expand_cpulist

class CoreSiblings:
    """
    Query CPU core topology to determine which CPUs share physical cores

    Note: This class works correctly whether SMT/hyperthreading is enabled or disabled.
    When SMT is disabled, each CPU's thread_siblings_list contains only itself,
    so the class will correctly report that no CPUs share cores.
    """

    def __init__(self, root="/"):
        self.sysdir = os.path.join(root, 'sys', 'devices', 'system', 'cpu')
        self.core_map = {}  # Maps cpu -> set of sibling cpus
        self._parse()

    def _parse(self):
        """Parse thread_siblings_list for each CPU"""
        for dirname in os.listdir(self.sysdir):
            # Only parse cpu<integer> directories
            if dirname.startswith('cpu') and os.path.isdir(os.path.join(self.sysdir, dirname)):
                try:
                    cpu_id = int(dirname[3:])
                except ValueError:
                    continue

                siblings_file = os.path.join(self.sysdir, dirname, 'topology', 'thread_siblings_list')
                if os.path.exists(siblings_file):
                    with open(siblings_file, 'r') as f:
                        siblings_str = f.read().strip()
                        # expand_cpulist returns a list of cpu numbers
                        siblings = set(expand_cpulist(siblings_str))
                        self.core_map[cpu_id] = siblings

    def share_core(self, cpu1, cpu2):
        """
        Check if two CPUs share the same physical core.

        Args:
            cpu1: First CPU ID (int)
            cpu2: Second CPU ID (int)

        Returns:
            True if CPUs share a core, False otherwise
        """
        if cpu1 not in self.core_map:
            return False
        return cpu2 in self.core_map[cpu1]

    def get_siblings(self, cpu):
        """
        Get all CPUs that share a core with the given CPU.

        Args:
            cpu: CPU ID (int)

        Returns:
            Set of CPU IDs that share a core with cpu (includes cpu itself)
        """
        return self.core_map.get(cpu, set())

    def get_core_groups(self):
        """
        Get all unique core sibling groups.

        Returns:
            List of sets, where each set contains CPUs that share a core
        """
        seen = set()
        groups = []

        for cpu, siblings in self.core_map.items():
            # Use frozenset as a hashable representation
            group_key = frozenset(siblings)
            if group_key not in seen:
                seen.add(group_key)
                groups.append(siblings)

        return groups


def unit_test():
    """Simple unit test"""
    try:
        cs = CoreSiblings()

        print("Core Sibling Groups:")
        for i, group in enumerate(cs.get_core_groups()):
            print(f"  Core {i}: {sorted(group)}")

        # Test share_core with first two CPUs if they exist
        if len(cs.core_map) >= 2:
            cpus = sorted(cs.core_map.keys())
            cpu1, cpu2 = cpus[0], cpus[1]
            print(f"\nDo CPU {cpu1} and CPU {cpu2} share a core? {cs.share_core(cpu1, cpu2)}")
            print(f"CPU {cpu1} siblings: {sorted(cs.get_siblings(cpu1))}")
            print(f"CPU {cpu2} siblings: {sorted(cs.get_siblings(cpu2))}")

        return 0
    except Exception as e:
        print(f"** EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(unit_test())
