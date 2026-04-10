# SPDX-License-Identifier: GPL-2.0-or-later
#
#   Copyright 2009 - 2013   Clark Williams <williams@redhat.com>
#   Copyright 2012 - 2013   David Sommerseth <davids@redhat.com>
#

import os
import time
import threading
import libxml2
from rteval.Log import Log
from rteval.rtevalConfig import rtevalCfgSection
from rteval.modules import RtEvalModules, rtevalModulePrototype
from rteval.systopology import SysTopology as SysTop
from rteval.cpulist_utils import CpuList, collapse_cpulist

class LoadThread(rtevalModulePrototype):
    def __init__(self, name, config, logger=None):

        if name is None or not isinstance(name, str):
            raise TypeError("name attribute is not a string")

        if config and not isinstance(config, rtevalCfgSection):
            raise TypeError("config attribute is not a rtevalCfgSection() object")

        if logger and not isinstance(logger, Log):
            raise TypeError("logger attribute is not a Log() object")

        rtevalModulePrototype.__init__(self, "load", name, logger)
	# abs path to top dir
        self.builddir = config.setdefault('builddir',
                                          os.path.abspath("../build"))
        # abs path to src dir
        self.srcdir = config.setdefault('srcdir',
                                        os.path.abspath("../loadsource"))
        self.num_cpus = config.setdefault('numcores', 1)
        self.source = config.setdefault('source', None)
        self.reportdir = config.setdefault('reportdir', os.getcwd())
        self.memsize = config.setdefault('memsize', (0, 'GB'))
        self.cpulist = config.setdefault('cpulist', "")
        self._logging = config.setdefault('logging', True)
        self._cfg = config
        self.mydir = None
        self.jobs = 0
        self.args = None

        if not os.path.exists(self.builddir):
            os.makedirs(self.builddir)


    def open_logfile(self, name):
        return os.open(os.path.join(self.reportdir, "logs", name), os.O_CREAT|os.O_WRONLY)


class CommandLineLoad(LoadThread):
    def __init__(self, name, config, logger):
        LoadThread.__init__(self, name, config, logger)


    def MakeReport(self):
        if not (self.jobs and self.args) or self._donotrun:
            return None

        rep_n = libxml2.newNode("command_line")
        rep_n.newProp("name", self._name)

        if self.jobs:
            rep_n.newProp("job_instances", str(self.jobs))
            if self.args:
                rep_n.addContent(" ".join(self.args))

        return rep_n


class LoadModules(RtEvalModules):
    """Module container for LoadThread based modules"""

    def __init__(self, config, logger):
        self._module_type = "load"
        self._module_config = "loads"
        self._report_tag = "loads"
        self.__loadavg_accum = 0.0
        self.__loadavg_samples = 0
        RtEvalModules.__init__(self, config, "modules.loads", logger)
        self.__LoadModules(self._cfg.GetSection(self._module_config))


    def __LoadModules(self, modcfg):
        "Loads and imports all the configured modules"

        for m in modcfg:
            # hope to eventually have different kinds but module is only one
            # for now (jcw)
            if m[1].lower() == 'module':
                self._LoadModule(m[0])


    def Setup(self, modparams):
        if not isinstance(modparams, dict):
            raise TypeError("modparams attribute is not of a dictionary type")

        modcfg = self._cfg.GetSection(self._module_config)
        cpulist = modcfg.cpulist
        for m in modcfg:
            # hope to eventually have different kinds but module is only on
            # for now (jcw)
            if m[1].lower() == 'module':
                self._cfg.AppendConfig(m[0], modparams)
                self._cfg.AppendConfig(m[0], {'cpulist': cpulist})
                modobj = self._InstantiateModule(m[0], self._cfg.GetSection(m[0]))
                self._RegisterModuleObject(m[0], modobj)


    def MakeReport(self):
        rep_n = RtEvalModules.MakeReport(self)
        rep_n.newProp("load_average", str(self.GetLoadAvg()))
        rep_n.newProp("loads", str(self.ModulesLoaded()))
        cpulist = self._cfg.GetSection(self._module_config).cpulist
        if cpulist:
            # Convert str to list and remove offline cpus
            cpulist = CpuList(cpulist).online().cpus
        else:
            cpulist = SysTop().default_cpus()
        rep_n.newProp("loadcpus", collapse_cpulist(cpulist))

        return rep_n


    def SaveLoadAvg(self):
        with open("/proc/loadavg") as p:
            load = float(p.readline().split()[0])
        self.__loadavg_accum += load
        self.__loadavg_samples += 1


    def GetLoadAvg(self):
        if self.__loadavg_samples == 0:
            self.SaveLoadAvg()
        return float(self.__loadavg_accum / self.__loadavg_samples)
