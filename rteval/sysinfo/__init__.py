# SPDX-License-Identifier: GPL-2.0-or-later
#
#   Copyright 2009 - 2013   Clark Williams <williams@redhat.com>
#   Copyright 2009 - 2013   David Sommerseth <davids@redhat.com>
#

import sys
from glob import glob
import libxml2
from rteval.Log import Log
from rteval.sysinfo.kernel import KernelInfo
from rteval.sysinfo.services import SystemServices
from rteval.sysinfo.cputopology import CPUtopology
from rteval.sysinfo.memory import MemoryInfo
from rteval.sysinfo.osinfo import OSInfo
from rteval.sysinfo.newnet import NetworkInfo
from rteval.sysinfo.cmdline import cmdlineInfo
from rteval.sysinfo.tuned import TunedInfo
from rteval.sysinfo.containercheck import ContainerInfo
from rteval.sysinfo import dmi

class SystemInfo(KernelInfo, SystemServices, dmi.DMIinfo, CPUtopology,
                 MemoryInfo, OSInfo, NetworkInfo, cmdlineInfo, TunedInfo, ContainerInfo):
    def __init__(self, config, logger=None):
        self.__logger = logger
        KernelInfo.__init__(self, logger=logger)
        SystemServices.__init__(self, logger=logger)
        dmi.DMIinfo.__init__(self, logger=logger)
        CPUtopology.__init__(self)
        OSInfo.__init__(self, logger=logger)
        cmdlineInfo.__init__(self, logger=logger)
        NetworkInfo.__init__(self, logger=logger)
        TunedInfo.__init__(self, logger=logger)
        ContainerInfo.__init__(self, logger=logger)

        # Parse initial DMI decoding errors
        self.ProcessWarnings()

        # Parse CPU info
        # Note: CPU lists are not available at this point (they're finalized in rteval-cmd),
        # so we can't add core sharing warnings to the XML report yet.
        # Console warnings are still generated in rteval-cmd.
        CPUtopology._parse(self)


    def MakeReport(self):
        report_n = libxml2.newNode("SystemInfo")
        report_n.newProp("version", "1.0")

        # Populate the report
        report_n.addChild(OSInfo.MakeReport(self))
        report_n.addChild(KernelInfo.MakeReport(self))
        report_n.addChild(NetworkInfo.MakeReport(self))
        report_n.addChild(SystemServices.MakeReport(self))
        report_n.addChild(CPUtopology.MakeReport(self))
        report_n.addChild(MemoryInfo.MakeReport(self))
        report_n.addChild(dmi.DMIinfo.MakeReport(self))
        report_n.addChild(cmdlineInfo.MakeReport(self))
        report_n.addChild(TunedInfo.MakeReport(self))
        report_n.addChild(ContainerInfo.MakeReport(self))

        return report_n


if __name__ == "__main__":
    from rteval.rtevalConfig import rtevalConfig
    l = Log()
    l.SetLogVerbosity(Log.INFO|Log.DEBUG)
    cfg = rtevalConfig(logger=l)
    cfg.Load("../rteval.conf")
    cfg.installdir = "."
    si = SystemInfo(cfg, logger=l)

    print(f"\tRunning on {si.get_base_os()}")
    print(f"\tNUMA nodes: {si.mem_get_numa_nodes()}")
    print("\tMemory available: %03.2f %s\n" % si.mem_get_size())

    print("\tServices: ")
    for (s, r) in list(si.services_get().items()):
        print("\t\t%s: %s" % (s, r))
    (curr, avail) = si.kernel_get_clocksources()

    print("\tCurrent clocksource: %s" % curr)
    print("\tAvailable clocksources: %s" % avail)
    print("\tModules:")
    for m in si.kernel_get_modules():
        print("\t\t%s: %s" % (m['modname'], m['modstate']))
    print("\tKernel threads:")
    for (p, i) in list(si.kernel_get_kthreads().items()):
        print("\t\t%-30.30s pid: %-5.5s policy: %-7.7s prio: %-3.3s" % (
            str(i["name"])+":", p, i["policy"], i["priority"]
            ))

    print("\n\tCPU topology info - cores: %i  online: %i  sockets: %i" % (
        si.cpu_getCores(False), si.cpu_getCores(True), si.cpu_getSockets()
        ))

    xml = si.MakeReport()
    xml_d = libxml2.newDoc("1.0")
    xml_d.setRootElement(xml)
    xml_d.saveFormatFileEnc("-", "UTF-8", 1)
