# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
#
#   Copyright 2016 - Clark Williams <williams@redhat.com>
#   Copyright 2021 - John Kacur <jkacur@redhat.com>
#
""" Module for querying cpu cores and nodes """

import os
import os.path
import glob
from rteval.cpulist_utils import CpuList, sysread, is_relative, expand_relative_cpulist, collapse_cpulist

def cpuinfo():
    ''' return a dictionary of cpu keys with various cpu information '''
    core = -1
    info = {}
    with open('/proc/cpuinfo') as fp:
        for l in fp:
            l = l.strip()
            if not l:
                continue
            # Split a maximum of one time. In case a model name has ':' in it
            key, val = [i.strip() for i in l.split(':', 1)]
            if key == 'processor':
                core = val
                info[core] = {}
                continue
            info[core][key] = val

    for (core, pcdict) in info.items():
        if not 'model name' in pcdict:
            # On Arm CPU implementer is present
            # Construct the model_name from the following fields
            if 'CPU implementer' in pcdict:
                model_name = [pcdict.get('CPU implementer')]
                model_name.append(pcdict.get('CPU architecture'))
                model_name.append(pcdict.get('CPU variant'))
                model_name.append(pcdict.get('CPU part'))
                model_name.append(pcdict.get('CPU revision'))

                # If a list item is None, remove it
                model_name = [name for name in model_name if name]

                # Convert the model_name list into a string
                model_name = " ".join(model_name)
                pcdict['model name'] = model_name
            else:
                pcdict['model name'] = 'Unknown'

    return info


#
# class to abstract access to NUMA nodes in /sys filesystem
#

class NumaNode:
    "class representing a system NUMA node"

    def __init__(self, path):
        """ constructor argument is the full path to the /sys node file
        e.g. /sys/devices/system/node/node0
        """
        self.path = path
        self.nodeid = int(os.path.basename(path)[4:].strip())
        self.cpus = CpuList(sysread(self.path, "cpulist")).online().cpus
        self.getmeminfo()

    def __contains__(self, cpu):
        """ function for the 'in' operator """
        return cpu in self.cpus

    def __len__(self):
        """ allow the 'len' builtin """
        return len(self.cpus)

    def __str__(self):
        """ string representation of the cpus for this node """
        return self.getcpustr()

    def __int__(self):
        return self.nodeid

    def getmeminfo(self):
        """ read info about memory attached to this node """
        self.meminfo = {}
        with open(os.path.join(self.path, "meminfo"), "r") as fp:
            for l in fp:
                elements = l.split()
                key = elements[2][0:-1]
                val = int(elements[3])
                if len(elements) == 5 and elements[4] == "kB":
                    val *= 1024
                self.meminfo[key] = val

    def getcpustr(self):
        """ return list of cpus for this node as a string """
        return collapse_cpulist(self.cpus)

    def getcpulist(self):
        """ return list of cpus for this node """
        return self.cpus

class SimNumaNode(NumaNode):
    """class representing a simulated NUMA node.
    For systems which don't have NUMA enabled (no
    /sys/devices/system/node) such as Arm v7
    """

    cpupath = '/sys/devices/system/cpu'
    mempath = '/proc/meminfo'

    def __init__(self):
        self.nodeid = 0
        self.cpus = CpuList(sysread(SimNumaNode.cpupath, "possible")).online().cpus
        self.getmeminfo()

    def getmeminfo(self):
        self.meminfo = {}
        with open(SimNumaNode.mempath, "r") as fp:
            for l in fp:
                elements = l.split()
                key = elements[0][0:-1]
                val = int(elements[1])
                if len(elements) == 3 and elements[2] == "kB":
                    val *= 1024
                self.meminfo[key] = val

#
# Class to abstract the system topology of numa nodes and cpus
#
class SysTopology:
    "Object that represents the system's NUMA-node/cpu topology"

    cpupath = '/sys/devices/system/cpu'
    nodepath = '/sys/devices/system/node'

    def __init__(self):
        self.nodes = {}
        self.getinfo()
        self.current = 0

    def __len__(self):
        return len(list(self.nodes.keys()))

    def __str__(self):
        s = f"{len(list(self.nodes.keys()))} node system "
        s += f"({(len(self.nodes[list(self.nodes.keys())[0]]))} cores per node)"
        return s

    def __contains__(self, node):
        """ inplement the 'in' function """
        for n in self.nodes:
            if self.nodes[n].nodeid == node:
                return True
        return False

    def __getitem__(self, key):
        """ allow indexing for the nodes """
        return self.nodes[key]

    def __iter__(self):
        """ allow iteration over the cpus for the node """
        return self

    def __next__(self):
        """ iterator function """
        if self.current >= len(self.nodes):
            raise StopIteration
        n = self.nodes[self.current]
        self.current += 1
        return n

    def getinfo(self):
        """ Initialize class Systopology """
        nodes = glob.glob(os.path.join(SysTopology.nodepath, 'node[0-9]*'))
        if nodes:
            nodes.sort()
            for n in nodes:
                node = int(os.path.basename(n)[4:])
                self.nodes[node] = NumaNode(n)
        else:
            self.nodes[0] = SimNumaNode()

    def getnodes(self):
        """ return a list of nodes """
        return list(self.nodes.keys())

    def getcpus(self, node):
        """ return a dictionary of cpus keyed with the node """
        return self.nodes[node].getcpulist()

    def online_cpus(self):
        """ return a list of integers of all online cpus """
        cpulist = []
        for n in self.nodes:
            cpulist += CpuList(self.getcpus(n)).online().cpus
        cpulist.sort()
        return cpulist

    def isolated_cpus(self):
        """ return a list of integers of all isolated cpus """
        cpulist = []
        for n in self.nodes:
            cpulist += CpuList(self.getcpus(n)).isolated().cpus
        cpulist.sort()
        return cpulist

    def default_cpus(self):
        """ return a list of integers of all default schedulable cpus, i.e. online non-isolated cpus """
        cpulist = []
        for n in self.nodes:
            cpulist += CpuList(self.getcpus(n)).nonisolated().cpus
        cpulist.sort()
        return cpulist

    def online_cpus_str(self):
        """ return a list of strings of numbers of all online cpus """
        cpulist = [str(cpu) for cpu in self.online_cpus()]
        return cpulist

    def isolated_cpus_str(self):
        """ return a list of strings of numbers of all isolated cpus """
        cpulist = [str(cpu) for cpu in self.isolated_cpus()]
        return cpulist

    def default_cpus_str(self):
        """ return a list of strings of numbers of all default schedulable cpus """
        cpulist = [str(cpu) for cpu in self.default_cpus()]
        return cpulist

    def invert_cpulist(self, cpulist):
        """ return a list of online cpus not in cpulist """
        return [c for c in self.online_cpus() if c not in cpulist]

    def online_cpulist(self, cpulist):
        """ return a list of online cpus in cpulist """
        return [c for c in self.online_cpus() if c in cpulist]


def validate_housekeeping_cpus(housekeeping_cpulist):
    """
    Validates that housekeeping CPUs are in isolated CPU list
    :param housekeeping_cpulist: CPU list string for housekeeping CPUs
    :return: Sorted list of validated housekeeping CPUs as integers
    :raises: RuntimeError if housekeeping CPUs are not in isolcpus
    """
    if not housekeeping_cpulist:
        return []

    housekeeping = CpuList(housekeeping_cpulist).online().cpus
    isolcpus = SysTopology().isolated_cpus()

    # Check if all housekeeping CPUs are in isolcpus
    not_isolated = [cpu for cpu in housekeeping if cpu not in isolcpus]
    if not_isolated:
        isolcpus_str = collapse_cpulist(isolcpus) if isolcpus else "none"
        raise RuntimeError(
            f"Housekeeping CPUs {collapse_cpulist(not_isolated)} are not in isolated CPUs [{isolcpus_str}]"
        )

    return sorted(housekeeping)


def parse_cpulist_from_config(cpulist, run_on_isolcpus=False):
    """
    Generates a cpulist based on --*-cpulist argument given by user
    :param cpulist: Value of --*-cpulist argument
    :param run_on_isolcpus: Value of --*-run-on-isolcpus argument
    :return: Sorted list of CPUs as integers
    """
    if cpulist and not is_relative(cpulist):
        # Only include online cpus
        result = CpuList(cpulist).online().cpus
    else:
        result = SysTopology().online_cpus()
        # Get the cpuset from the environment
        cpuset = os.sched_getaffinity(0)
        # Get isolated CPU list
        isolcpus = SysTopology().isolated_cpus()
        if cpulist and is_relative(cpulist):
            # Include cpus that are not removed in relative cpuset and are either in cpuset from affinity,
            # isolcpus (with run_on_isolcpus enabled, or added by relative cpuset
            added_cpus, removed_cpus = expand_relative_cpulist(cpulist)
            result = [c for c in result
                      if (c in cpuset or
                          c in added_cpus or
                          run_on_isolcpus and c in isolcpus) and
                      c not in removed_cpus]
        else:
            # Only include cpus that are in the cpuset and isolated CPUs if run_on_isolcpus is enabled
            result = [c for c in result if c in cpuset or run_on_isolcpus and c in isolcpus]
    return result


def validate_core_sharing(housekeeping_cpus, measurement_cpus, load_cpus):
    """
    Check for CPUs sharing physical cores across different workload types.
    Warns if isolated CPUs share cores between housekeeping, measurement, and load groups.

    :param housekeeping_cpus: List of housekeeping CPU integers
    :param measurement_cpus: List of measurement CPU integers
    :param load_cpus: List of load CPU integers
    :return: List of warning messages (empty if no issues)
    """
    from rteval.sysinfo.coresiblings import CoreSiblings

    warnings = []

    # Get isolated CPUs
    isolated_cpus = set(SysTopology().isolated_cpus())

    # Create CoreSiblings instance
    try:
        cs = CoreSiblings()
    except Exception:
        # If we can't read topology, skip validation
        return warnings

    def check_pair(cpu1, cpu2, type1, type2):
        """Check if two CPUs share a core and generate warning if at least one is isolated"""
        if cs.share_core(cpu1, cpu2):
            cpu1_isol = cpu1 in isolated_cpus
            cpu2_isol = cpu2 in isolated_cpus

            # Only warn if at least one CPU is isolated
            if cpu1_isol or cpu2_isol:
                cpu1_str = f"{type1} CPU {cpu1}{' (isol)' if cpu1_isol else ''}"
                cpu2_str = f"{type2} CPU {cpu2}{' (isol)' if cpu2_isol else ''}"
                warnings.append(f"Warning: {cpu1_str} shares core with {cpu2_str}")

    # Check all three combinations
    # 1. Housekeeping vs Measurement
    for hk_cpu in housekeeping_cpus:
        for msr_cpu in measurement_cpus:
            check_pair(hk_cpu, msr_cpu, "Housekeeping", "measurement")

    # 2. Housekeeping vs Load
    for hk_cpu in housekeeping_cpus:
        for ld_cpu in load_cpus:
            check_pair(hk_cpu, ld_cpu, "Housekeeping", "load")

    # 3. Measurement vs Load
    for msr_cpu in measurement_cpus:
        for ld_cpu in load_cpus:
            check_pair(msr_cpu, ld_cpu, "Measurement", "load")

    return warnings


if __name__ == "__main__":

    def unit_test():
        """ unit test, run python rteval/systopology.py """
        s = SysTopology()
        print(s)
        print(f"number of nodes: {len(s)}")
        for n in s:
            print(f"node[{n.nodeid}]: {n}")
        print(f"system has numa node 0: {0 in s}")
        print(f"system has numa node 2: {2 in s}")
        print(f"system has numa node 24: {24 in s}")

        cpus = {}
        print(f"nodes = {s.getnodes()}")
        for node in s.getnodes():
            cpus[node] = s.getcpus(int(node))
            print(f'cpus = {cpus}')

        onlcpus = s.online_cpus()
        print(f'onlcpus = {onlcpus}')
        onlcpus = collapse_cpulist(onlcpus)
        print(f'onlcpus = {onlcpus}')

        onlcpus_str = s.online_cpus_str()
        print(f'onlcpus_str = {onlcpus_str}')

        cpulist = [ 2, 4, 5 ]
        print(f"invert of {cpulist} = {s.invert_cpulist(cpulist)}")
    unit_test()
