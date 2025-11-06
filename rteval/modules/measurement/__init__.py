# SPDX-License-Identifier: GPL-2.0-or-later
#
#   Copyright 2012 - 2013   David Sommerseth <davids@redhat.com>
#

import libxml2
from rteval.modules import RtEvalModules, ModuleContainer
from rteval.systopology import parse_cpulist_from_config
import rteval.cpulist_utils as cpulist_utils

class MeasurementModules(RtEvalModules):
    """Module container for measurement modules"""

    def __init__(self, config, logger):
        self._module_type = "measurement"
        self._report_tag = "Measurements"
        RtEvalModules.__init__(self, config, "modules.measurement", logger)
        self.__LoadModules(self._cfg.GetSection("measurement"))


    def __LoadModules(self, modcfg):
        "Loads and imports all the configured modules"

        for m in modcfg:
            # hope to eventually have different kinds but module is only on
            # for now (jcw)
            if m[1] and m[1].lower() == 'module':
                self._LoadModule(m[0])

    def SetupModuleOptions(self, parser):
        "Sets up all the measurement modules' parameters for the option parser"
        super().SetupModuleOptions(parser)


    def Setup(self, modparams):
        "Loads all measurement modules"

        if not isinstance(modparams, dict):
            raise TypeError("modparams attribute is not of a dictionary type")

        modcfg = self._cfg.GetSection("measurement")
        cpulist = modcfg.cpulist
        run_on_isolcpus = modcfg.run_on_isolcpus
        if cpulist is None:
            # Get default cpulist value
            cpulist = cpulist_utils.collapse_cpulist(parse_cpulist_from_config("", run_on_isolcpus))

        for (modname, modtype) in modcfg:
            if isinstance(modtype, str) and modtype.lower() == 'module':  # Only 'module' will be supported (ds)
                self._cfg.AppendConfig(modname, modparams)
                self._cfg.AppendConfig(modname, {'cpulist':cpulist})
                self._cfg.AppendConfig(modname, {'run-on-isolcpus':run_on_isolcpus})

                modobj = self._InstantiateModule(modname, self._cfg.GetSection(modname))
                self._RegisterModuleObject(modname, modobj)


    def MakeReport(self):
        rep_n = super().MakeReport()

        cpulist = self._cfg.GetSection("measurement").cpulist
        run_on_isolcpus = self._cfg.GetSection("measurement").run_on_isolcpus
        cpulist = parse_cpulist_from_config(cpulist, run_on_isolcpus)
        rep_n.newProp("measurecpus", cpulist_utils.collapse_cpulist(cpulist))

        return rep_n
