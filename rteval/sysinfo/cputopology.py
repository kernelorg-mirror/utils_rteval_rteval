# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
#
#   Copyright 2010 - 2013   David Sommerseth <davids@redhat.com>
#

import os
import libxml2
from rteval.systopology import SysTopology

class CPUtopology:
    "Retrieves an overview over the installed CPU cores and the system topology"

    def __init__(self, root="/"):
        self.sysdir = os.path.join(root, 'sys', 'devices', 'system', 'cpu')
        self.__cputop_n = None
        self.__cpu_cores = 0
        self.__online_cores = 0
        self.__isolated_cores = 0
        self.__cpu_sockets = 0

    def __read(self, dirname, fname):
        fp = open(os.path.join(self.sysdir, dirname, fname), 'r')
        data = fp.readline()
        if len(data) > 0:
            ret = int(data)
        else:
            ret = 0
        fp.close()
        return ret

    def _parse(self):
        "Parses the cpu topology information from /sys/devices/system/cpu/cpu*"

        self.__cputop_n = libxml2.newNode('CPUtopology')

        # Get list of isolated CPUs from SysTopology
        systopology = SysTopology()
        isolated_cpus = {'cpu' + n for n in systopology.isolated_cpus_str()}

        cpusockets = []
        for dirname in os.listdir(self.sysdir):
            # Only parse directories which starts with 'cpu'
            if (dirname.find('cpu', 0) == 0) and os.path.isdir(os.path.join(self.sysdir, dirname)):
                # Make sure we only parse "proper" cpu<integer> directories, and not f.ex. 'cpuidle'
                try:
                    int(dirname[3:])
                except ValueError:
                    continue

                # Parse contents of the cpu dir
                for cpudir in os.listdir(os.path.join(self.sysdir, dirname)):
                    # Check if it is a proper CPU directory which should contain an 'online' file
                    # except on 'cpu0' which cannot be offline'd
                    if (cpudir.find('online', 0) == 0) or dirname == 'cpu0':
                        cpu_n = self.__cputop_n.newChild(None, 'cpu', None)
                        cpu_n.newProp('name', dirname)
                        online = (dirname == 'cpu0') and 1 or self.__read(dirname, 'online')
                        cpu_n.newProp('online', str(online))
                        self.__cpu_cores += 1

                        # Check if the CPU is online, if it is, grab more info available
                        if online == 1:
                            self.__online_cores += 1
                            cpu_n.newProp('core_id', \
                                str(self.__read(os.path.join(dirname, \
                                'topology'), 'core_id')))
                            phys_pkg_id = self.__read(os.path.join(dirname, 'topology'),
                                                      'physical_package_id')
                            cpu_n.newProp('physical_package_id', str(phys_pkg_id))
                            cpusockets.append(phys_pkg_id)
                            is_isolated = dirname in isolated_cpus
                            if is_isolated:
                             self.__isolated_cores += 1
                            cpu_n.newProp('isolated', str(int(dirname in isolated_cpus)))
                        break

        # Count unique CPU sockets
        lastsock = None
        sockcnt = 0
        cpusockets.sort()
        for sck in cpusockets:
            if sck != lastsock:
                lastsock = sck
                sockcnt += 1
        self.__cpu_sockets = sockcnt

        # Summarise the core counts
        self.__cputop_n.newProp('num_cpu_cores', str(self.__cpu_cores))
        self.__cputop_n.newProp('num_cpu_cores_online', str(self.__online_cores))
        self.__cputop_n.newProp('num_cpu_cores_isolated', str(self.__isolated_cores))
        self.__cputop_n.newProp('num_cpu_sockets', str(self.__cpu_sockets))

        return self.__cputop_n


    def add_core_sharing_warnings(self, housekeeping_cpus, measurement_cpus, load_cpus):
        """
        Add core sharing warnings to the CPUtopology XML node.
        Should be called after CPU lists are finalized.

        :param housekeeping_cpus: List of housekeeping CPU integers
        :param measurement_cpus: List of measurement CPU integers
        :param load_cpus: List of load CPU integers
        """
        if self.__cputop_n is None:
            return

        # Remove any existing CoreSharingWarnings section
        existing = self.__cputop_n.xpathEval('CoreSharingWarnings')
        if existing:
            for node in existing:
                node.unlinkNode()
                node.freeNode()

        # Generate new warnings
        from rteval.systopology import validate_core_sharing
        warnings = validate_core_sharing(
            housekeeping_cpus or [],
            measurement_cpus or [],
            load_cpus or []
        )

        # Add warnings to XML if any were found
        if warnings:
            warnings_n = self.__cputop_n.newChild(None, 'CoreSharingWarnings', None)
            for warning in warnings:
                warnings_n.newChild(None, 'warning', warning)

    def MakeReport(self):
        return self.__cputop_n

    def cpu_getCores(self, only_online):
        return only_online and self.__online_cores or self.__cpu_cores


    def cpu_getSockets(self):
        return self.__cpu_sockets


def unit_test(rootdir):
    try:
        cputop = CPUtopology()
        n = cputop._parse()

        print(" ---- XML Result ---- ")
        x = libxml2.newDoc('1.0')
        x.setRootElement(n)
        x.saveFormatFileEnc('-', 'UTF-8', 1)

        print(" ---- getCPUcores() / getCPUscokets() ---- ")
        print(f"CPU cores: {cputop.cpu_getCores(False)} (online: {cputop.cpu_getCores(True)}) - CPU sockets: {cputop.cpu_getSockets()}")
        return 0
    except Exception as e:
        # import traceback
        # traceback.print_exc(file=sys.stdout)
        print("** EXCEPTION %s", str(e))
        return 1

if __name__ == '__main__':
    unit_test(None)
