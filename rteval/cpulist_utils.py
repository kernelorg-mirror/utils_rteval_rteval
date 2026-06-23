# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
#
#   Copyright 2016 - Clark Williams <williams@redhat.com>
#   Copyright 2021 - John Kacur <jkacur@redhat.com>
#   Copyright 2023 - Tomas Glozar <tglozar@redhat.com>
#   Copyright 2026 - John Kacur <jkacur@redhat.com>
#
"""Module providing CpuList class and utility functions for working with CPU lists"""

import os


cpupath = "/sys/devices/system/cpu"


def sysread(path, obj):
    """ Helper function for reading system files """
    with open(os.path.join(path, obj), "r") as fp:
        return fp.readline().strip()


def _online_file_exists():
    """ Check whether machine / kernel is configured with online file """
    # Note: some machines do not have cpu0/online so we check cpu1/online.
    # In the case of machines with a single CPU, there is no cpu1, but
    # that is not a problem, since a single CPU cannot be offline
    return os.path.exists(os.path.join(cpupath, "cpu1/online"))


def _isolated_file_exists():
    """ Check whether machine / kernel is configured with isolated file """
    return os.path.exists(os.path.join(cpupath, "isolated"))


#
# CpuList class - object-oriented interface for CPU list manipulation
#

class CpuList:
    """
    Object-oriented interface for CPU list manipulation.

    Represents a list of CPU numbers with methods for filtering and transformation.
    Operations return new CpuList instances, making them chainable.

    Examples:
        # Create from string
        cpus = CpuList("0-7,9-11")

        # Create from list
        cpus = CpuList([0, 1, 2, 3, 4, 5, 6, 7, 9, 10, 11])

        # Chain operations
        online_isolated = CpuList("0-15").online().isolated()

        # Use as iterator
        for cpu in CpuList("0-3"):
            print(cpu)
    """

    def __init__(self, cpulist):
        """
        Initialize CpuList from string or list.

        Args:
            cpulist: Either a string like "0-7,9-11" or a list of integers
        """
        if isinstance(cpulist, str):
            self._cpus = expand_cpulist(cpulist)
        elif isinstance(cpulist, list):
            self._cpus = [int(cpu) for cpu in cpulist]
        else:
            raise TypeError("cpulist must be a string or list")

        self._cpus.sort()

    @property
    def cpus(self):
        """Return the list of CPU numbers"""
        return self._cpus

    def getcpulist(self):
        """Return the list of CPU numbers (for backward compatibility)"""
        return self._cpus

    def online(self):
        """
        Return a new CpuList containing only online CPUs.

        Returns:
            CpuList: New instance with only online CPUs
        """
        return CpuList(online_cpulist(self._cpus))

    def isolated(self):
        """
        Return a new CpuList containing only isolated CPUs.

        Returns:
            CpuList: New instance with only isolated CPUs
        """
        return CpuList(isolated_cpulist(self._cpus))

    def nonisolated(self):
        """
        Return a new CpuList containing only non-isolated CPUs.

        Returns:
            CpuList: New instance with only non-isolated CPUs
        """
        return CpuList(nonisolated_cpulist(self._cpus))

    def __str__(self):
        """Return collapsed string representation (e.g., '0-7,9-11')"""
        return collapse_cpulist(self._cpus)

    def __repr__(self):
        """Return repr string"""
        return f"CpuList('{self}')"

    def __len__(self):
        """Return number of CPUs in the list"""
        return len(self._cpus)

    def __contains__(self, cpu):
        """Check if CPU is in the list"""
        return int(cpu) in self._cpus

    def __iter__(self):
        """Iterate over CPU numbers"""
        return iter(self._cpus)

    def __eq__(self, other):
        """Compare two CpuList objects"""
        if isinstance(other, CpuList):
            return self._cpus == other._cpus
        return False

    # Static methods for backward compatibility and direct use

    @staticmethod
    def expand(cpulist_str):
        """
        Expand a range string into a list of CPU numbers.

        Args:
            cpulist_str: String like "0-7,9-11"

        Returns:
            list: List of CPU numbers
        """
        return expand_cpulist(cpulist_str)

    @staticmethod
    def collapse(cpulist):
        """
        Collapse a list of CPU numbers into a string range.

        Args:
            cpulist: List of CPU numbers

        Returns:
            str: Collapsed string like "0-7,9-11"
        """
        return collapse_cpulist(cpulist)

    @staticmethod
    def compress(cpulist):
        """
        Return a string representation of cpulist.

        Args:
            cpulist: List of CPU numbers

        Returns:
            str: Comma-separated string
        """
        return compress_cpulist(cpulist)


#
# Module-level functions - kept for backward compatibility
#

def collapse_cpulist(cpulist):
    """
    Collapse a list of cpu numbers into a string range
    of cpus (e.g. 0-5, 7, 9)
    """
    if not cpulist:
        return ""

    # Ensure we're working with integers, remove duplicates, and sort them
    sorted_cpus = sorted(set([int(cpu) for cpu in cpulist]))

    cur_range = [None, None]
    result = []
    for cpu in sorted_cpus + [None]:
        if cur_range[0] is None:
            cur_range[0] = cur_range[1] = cpu
            continue
        if cpu is not None and cpu == cur_range[1] + 1:
            # Extend currently processed range
            cur_range[1] += 1
        else:
            # Range processing finished, add range to string
            result.append(f"{cur_range[0]}-{cur_range[1]}"
                          if cur_range[0] != cur_range[1]
                          else str(cur_range[0]))
            # Reset
            cur_range[0] = cur_range[1] = cpu
    return ",".join(result)


def compress_cpulist(cpulist):
    """ return a string representation of cpulist """
    if not cpulist:
        return ""
    if isinstance(cpulist[0], int):
        return ",".join(str(e) for e in cpulist)
    return ",".join(cpulist)


def expand_cpulist(cpulist):
    """ expand a range string into an array of cpu numbers
    don't error check against online cpus
    """
    result = []

    if not cpulist:
        return result

    for part in cpulist.split(','):
        if '-' in part:
            a, b = part.split('-')
            a, b = int(a), int(b)
            result.extend(list(range(a, b + 1)))
        else:
            a = int(part)
            result.append(a)
    return [int(i) for i in list(set(result))]


def is_online(n):
    """ check whether cpu n is online """
    path = os.path.join(cpupath, f'cpu{n}')

    # Some hardware doesn't allow cpu0 to be turned off
    if not os.path.exists(path + '/online') and n == 0:
        return True

    return sysread(path, "online") == "1"


def online_cpulist(cpulist):
    """ Given a cpulist, return a cpulist of online cpus """
    # This only works if the sys online files exist
    if not _online_file_exists():
        return cpulist
    newlist = []
    for cpu in cpulist:
        if not _online_file_exists() and cpu == '0':
            newlist.append(cpu)
        elif is_online(int(cpu)):
            newlist.append(cpu)
    return newlist


def isolated_cpulist(cpulist):
    """Given a cpulist, return a cpulist of isolated CPUs"""
    if not _isolated_file_exists():
        return cpulist
    isolated_cpulist = sysread(cpupath, "isolated")
    isolated_cpulist = expand_cpulist(isolated_cpulist)
    return list(set(isolated_cpulist) & set(cpulist))


def nonisolated_cpulist(cpulist):
    """Given a cpulist, return a cpulist of non-isolated CPUs"""
    if not _isolated_file_exists():
        return cpulist
    isolated_cpulist = sysread(cpupath, "isolated")
    isolated_cpulist = expand_cpulist(isolated_cpulist)
    return list(set(cpulist).difference(set(isolated_cpulist)))


def is_relative(cpulist):
    return cpulist.startswith("+") or cpulist.startswith("-")


def expand_relative_cpulist(cpulist):
    """
    Expand a relative cpulist into a tuple of lists.
    :param cpulist: Relative cpulist of form +1,2,3,-4,5,6
    :return: Tuple of two lists, one for added CPUs, one for removed CPUs
    """
    added_cpus = []
    removed_cpus = []

    if not cpulist:
        return added_cpus, removed_cpus

    cpus = None

    for part in cpulist.split(','):
        if part.startswith('+') or part.startswith('-'):
            cpus = added_cpus if part[0] == '+' else removed_cpus
            part = part[1:]
        if '-' in part:
            a, b = part.split('-')
            a, b = int(a), int(b)
            cpus.extend(list(range(a, b + 1)))
        else:
            a = int(part)
            cpus.append(a)

    return list(set(added_cpus)), list(set(removed_cpus))
