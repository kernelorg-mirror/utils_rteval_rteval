# SPDX-License-Identifier: GPL-2.0-or-later
#
#   Copyright 2012 - 2013   David Sommerseth <davids@redhat.com>
#

import time
from datetime import datetime
import threading
import argparse
import libxml2
from rteval.Log import Log
from rteval.rtevalConfig import rtevalCfgSection

__all__ = ["rtevalRuntimeError", "rtevalModulePrototype", "ModuleContainer", "RtEvalModules"]

class rtevalRuntimeError(RuntimeError):
    def __init__(self, mod, message):
        RuntimeError.__init__(self, message)

        # The module had a RuntimeError, we set the flag
        mod._setRuntimeError()


class rtevalModulePrototype(threading.Thread):
    """ Prototype rteval modules class - to be inherited by the real module """

    def __init__(self, modtype, name, logger=None):
        if logger and not isinstance(logger, Log):
            raise TypeError("logger attribute is not a Log() object")

        threading.Thread.__init__(self)

        self._module_type = modtype
        self._name = name
        self.__logger = logger
        self.__ready = False
        self.__runtimeError = False
        self.__events = {"start": threading.Event(),
                         "stop": threading.Event(),
                         "finished": threading.Event()}
        self._donotrun = False
        self._exclusive = False
        self._latency_test = False
        self.__timestamps = {}
        self.__sleeptime = 2.0


    def _log(self, logtype, msg):
        """ Common log function for rteval modules """
        if self.__logger:
            self.__logger.log(logtype, f"[{self._name}] {msg}")


    def isReady(self):
        """ Returns a boolean if the module is ready to run """
        if self._donotrun:
            return True
        return self.__ready


    def is_exclusive(self):
        """ Returns true if this workload should run alone """
        return self._exclusive


    def set_exclusive(self):
        """ Sets This module to run alone """
        self._exclusive = True


    def set_latency_test(self):
        """ Sets the module as an exclusive latency measurer """
        self._latency_test = True


    def set_donotrun(self):
        """ set a module's donotrun field to True """
        self._donotrun = True


    def _setReady(self, state=True):
        """ Sets the ready flag for the module """
        self.__ready = state


    def hadRuntimeError(self):
        """ Returns a boolean if the module had a RuntimeError """
        return self.__runtimeError


    def _setRuntimeError(self, state=True):
        """ Sets the runtimeError flag for the module """
        self.__runtimeError = state


    def setStart(self):
        """ Sets the start event state """
        self.__events["start"].set()
        self.__timestamps["start_set"] = datetime.now()


    def shouldStart(self):
        """Returns the start event state - indicating the module can start """
        return self.__events["start"].isSet()


    def setStop(self):
        """ Sets the stop event state """
        self.__events["stop"].set()
        self.__timestamps["stop_set"] = datetime.now()


    def shouldStop(self):
        """ Returns the stop event state - indicating the module should stop """
        return self.__events["stop"].isSet()


    def _setFinished(self):
        """ Sets the finished event state - indicating the module has completed
        """
        self.__events["finished"].set()
        self.__timestamps["finished_set"] = datetime.now()


    def WaitForCompletion(self, wtime=None):
        """ Blocks until the module has completed its workload """
        if self.hadRuntimeError() or not self.shouldStart():
            # If it failed or hasn't been started yet, nothing to wait for
            return None
        return self.__events["finished"].wait(wtime)


    def _WorkloadSetup(self):
        """ Required module method, which purpose is to do the initial workload
        setup, preparing for _WorkloadBuild()
        """
        raise NotImplementedError(f"_WorkloadSetup() method must be implemented in the {self._name} module")


    def _WorkloadBuild(self):
        """ Required module method, which purpose is to compile additional code
        needed for the worklaod
        """
        raise NotImplementedError(f"_WorkloadBuild() method must be implemented in the {self._name} module")


    def _WorkloadPrepare(self):
        """ Required module method, which will initialise and prepare the
        workload just before it is about to start
        """
        raise NotImplementedError(f"_WorkloadPrepare() method must be implemented in the {self._name} module")


    def _WorkloadTask(self):
        """ Required module method, which kicks off the workload """
        raise NotImplementedError(f"_WorkloadTask() method must be implemented in the {self._name} module")


    def WorkloadAlive(self):
        """ Required module method, which should return True if the workload is
        still alive
        """
        raise NotImplementedError(f"WorkloadAlive() method must be implemented in the {self._name} module")


    def _WorkloadCleanup(self):
        """ Required module method, which will be run after the _WorkloadTask()
        has completed or been aborted by the 'stop event flag'
        """
        raise NotImplementedError(f"_WorkloadCleanup() method must be implemented in the {self._name} module")


    def WorkloadWillRun(self):
        "Returns True if this workload will be run"
        return self._donotrun is False


    def __run(self):
        "Workload thread runner - takes care of keeping the workload running as long as needed"
        if self.shouldStop():
            return

        # Initial workload setups
        self._WorkloadSetup()

        if not self._donotrun:
            # Compile the workload
            self._WorkloadBuild()

            # Do final preparations of workload  before we're ready to start running
            self._WorkloadPrepare()

            # Wait until we're released
            while True:
                if self.shouldStop():
                    return
                self.__events["start"].wait(1.0)
                if self.shouldStart():
                    break

            self._log(Log.DEBUG, f"Starting {self._module_type} workload")
            self.__timestamps["runloop_start"] = datetime.now()
            while not self.shouldStop():
                # Run the workload
                self._WorkloadTask()

                if self.shouldStop():
                    break
                time.sleep(self.__sleeptime)

            self.__timestamps["runloop_stop"] = datetime.now()
            self._log(Log.DEBUG, f"stopping {self._module_type} workload")
        else:
            self._log(Log.DEBUG, "Workload was not started")

        self._WorkloadCleanup()

    def run(self):
        try:
            self.__run()
        except Exception as e:
            self._setRuntimeError()
            raise e

    def MakeReport(self):
        """ required module method, needs to return an libxml2.xmlNode object
        with the the results from running
        """
        raise NotImplementedError(f"MakeReport() method must be implemented in the {self._name} module")


    def GetTimestamps(self):
        "Return libxml2.xmlNode object with the gathered timestamps"

        ts_n = libxml2.newNode("timestamps")
        for k in list(self.__timestamps.keys()):
            ts_n.newChild(None, k, str(self.__timestamps[k]))

        return ts_n



class ModuleContainer:
    """The ModuleContainer keeps an overview over loaded modules and the objects it
will instantiate.  These objects are accessed by iterating the ModuleContainer object."""

    def __init__(self, modules_root, logger):
        """Creates a ModuleContainer object.  modules_root defines the default
directory where the modules will be loaded from.  logger should point to a Log()
object which will be used for logging and will also be given to the instantiated
objects during module import."""
        if logger and not isinstance(logger, Log):
            raise TypeError("logger attribute is not a Log() object")

        self.__modules_root = modules_root
        self.__modtype = modules_root.split('.')[-1]
        self.__logger = logger
        self.__modobjects = {}  # Keeps track of instantiated objects
        self.__modsloaded = {}     # Keeps track of imported modules
        self.__iter_list = None


    def LoadModule(self, modname, modroot=None):
        """Imports a module and saves references to the imported module.
If the same module is tried imported more times, it will return the module
reference from the first import"""

        if modroot is None:
            modroot = self.__modules_root

        # If this module is already reported return the module,
        # if not (except KeyError:) import it and return the imported module
        try:
            idxname = f"{modroot}.{modname}"
            return self.__modsloaded[idxname]
        except KeyError:
            self.__logger.log(Log.INFO, f"importing module {modname}")
            mod = __import__(f"rteval.{modroot}.{modname}",
                             fromlist=f"rteval.{modroot}")
            self.__modsloaded[idxname] = mod
            return mod


    def SetupModuleOptions(self, parser, config):
        """Sets up a separate argparse ArgumentGroup per module with its supported parameters"""

        grparser = parser.add_argument_group(f"Group Options for {self.__modtype} modules")
        grparser.add_argument(f'--{self.__modtype}-cpulist',
                            dest=f'{self.__modtype}___cpulist', action='store',
                            default="",
                            help=f'CPU list where {self.__modtype} modules will run',
                            metavar='CPULIST')

        # Set up options for measurement modules only
        if self.__modtype == 'measurement':
            grparser.add_argument(f'--{self.__modtype}-run-on-isolcpus',
                                  dest = f'{self.__modtype}___run_on_isolcpus',
                                  action = "store_true",
                                  default = config.GetSection("measurement").setdefault("run-on-isolcpus", "false").lower() == "true",
                                  help = "Include isolated CPUs in default cpulist")
            grparser.add_argument('--idle-set',
                                  dest='measurement___idlestate',
                                  metavar='IDLESTATE',
                                  default=None,
                                  help='Idle state depth to set on cpus running measurement modules')

        for (modname, mod) in list(self.__modsloaded.items()):
            opts = mod.ModuleParameters()
            if len(opts) == 0:
                continue

            shortmod = modname.split('.')[-1]
            try:
                cfg = config.GetSection(shortmod)
            except KeyError:
                # Ignore if a section is not found
                cfg = None

            grparser = parser.add_argument_group(f"Options for the {shortmod} module")
            for (o, s) in list(opts.items()):
                descr = 'descr' in s and s['descr'] or ""
                metavar = 'metavar' in s and s['metavar'] or None

                try:
                    default = cfg and getattr(cfg, o) or None
                except AttributeError:
                    # Ignore if this isn't found in the configuration object
                    default = None

                if default is None:
                    default = 'default' in s and s['default'] or None


                grparser.add_argument(f'--{shortmod}-{o}',
                                         dest=f"{shortmod}___{o}",
                                         action='store',
                                         help='%s%s' % (descr,
                                                        default and ' (default: %s)' % default or ''),
                                         default=default,
                                         metavar=metavar)


    def InstantiateModule(self, modname, modcfg, modroot=None):
        """Imports a module and instantiates an object from the modules create() function.
The instantiated object is returned in this call"""

        if modcfg and not isinstance(modcfg, rtevalCfgSection):
            raise TypeError("modcfg attribute is not a rtevalCfgSection() object")

        mod = self.LoadModule(modname, modroot)
        return mod.create(modcfg, self.__logger)


    def RegisterModuleObject(self, modname, modobj):
        """Registers an instantiated module object.  This module object will be
returned when a ModuleContainer object is iterated over"""
        self.__modobjects[modname] = modobj


    def ModulesLoaded(self):
        "Returns number of registered module objects"
        return len(self.__modobjects)


    def __iter__(self):
        "Initiates the iterating process"

        self.__iter_list = list(self.__modobjects.keys())
        return self


    def __next__(self):
        """ Internal Python iterating method, returns the next
        module name and object to be processed
        """

        if len(self.__iter_list) == 0:
            self.__iter_list = None
            raise StopIteration
        modname = self.__iter_list.pop()
        return (modname, self.__modobjects[modname])



class RtEvalModules:
    """ RtEvalModules should normally be inherrited by a more specific module
    class.  This class takes care of managing imported modules and has methods
    for starting and stopping the workload these modules contains.
    """

    def __init__(self, config, modules_root, logger):
        """ Initialises the RtEvalModules() internal variables.
        The modules_root argument should point at the root directory where
        the modules will be loaded from. The logger argument should point
        to a Log() object which will be used for logging and will also be given
        to the instantiated objects during module import.
        """

        self._cfg = config
        self._logger = logger
        self.__modules = ModuleContainer(modules_root, logger)
        self.__timestamps = {}


    # Export some of the internal module container methods
    # Primarily to have better control of the module containers
    # iteration API
    def _InstantiateModule(self, modname, modcfg, modroot=None):
        "Imports a module and returns an instantiated object from the module"
        return self.__modules.InstantiateModule(modname, modcfg, modroot)

    def _RegisterModuleObject(self, modname, modobj):
        "Registers an instantiated module object which RtEvalModules will control"
        return self.__modules.RegisterModuleObject(modname, modobj)

    def _LoadModule(self, modname, modroot=None):
        "Loads and imports a module"
        return self.__modules.LoadModule(modname, modroot)

    def ModulesLoaded(self):
        "Returns number of imported modules"
        return self.__modules.ModulesLoaded()

    def SetupModuleOptions(self, parser):
        "Sets up argparse based argument groups for the loaded modules"
        return self.__modules.SetupModuleOptions(parser, self._cfg)
    # End of exports


    def Start(self):
        """ Prepares all the imported modules workload to start, but they
        will not start their workloads yet
        """
        if self.__modules.ModulesLoaded() == 0:
            raise rtevalRuntimeError(f"No {self._module_type} modules configured")

        self._logger.log(Log.INFO, f"Preparing {self._module_type} modules")
        exclusive = 0
        latency_test = False
        for (modname, mod) in self.__modules:
            if mod.is_exclusive() and mod.WorkloadWillRun():
                exclusive += 1
            if mod._latency_test:
                if latency_test:
                    raise RuntimeError("More than one exclusive latency test")
                latency_test = True
        for (modname, mod) in self.__modules:
            if exclusive >= 1:
                if exclusive != 1:
                    msg = f"More than one exclusive load: {exclusive}"
                    raise RuntimeError(msg)
                if not mod.is_exclusive() and mod.WorkloadWillRun():
                    mod.set_donotrun()
            mod.start()
            if mod.WorkloadWillRun():
                self._logger.log(Log.DEBUG, f"\t - Started {modname} preparations")

        self._logger.log(Log.DEBUG, f"Waiting for all {self._module_type} modules to get ready")
        busy = True
        while busy:
            busy = False
            for (modname, mod) in self.__modules:
                if not mod.isReady():
                    if not mod.hadRuntimeError():
                        busy = True
                        self._logger.log(Log.DEBUG, f"Waiting for {modname}")
                    else:
                        raise RuntimeError(f"Runtime error starting the {modname} {self._module_type} module")

            if busy:
                time.sleep(1)

        self._logger.log(Log.DEBUG, f"All {self._module_type} modules are ready")


    def hadError(self):
        "Returns True if one or more modules had a RuntimeError"
        return self.__runtimeError


    def Unleash(self):
        """Unleashes all the loaded modules"""

        nthreads = 0
        self._logger.log(Log.INFO, f"Sending start event to all {self._module_type} modules")
        for (modname, mod) in self.__modules:
            mod.setStart()
            nthreads += 1

        self.__timestamps['unleash'] = datetime.now()
        return nthreads


    def isAlive(self):
        """Returns True if all modules are running"""

        for (modname, mod) in self.__modules:
            # We requiring all modules to run to pass
            if not mod.WorkloadAlive():
                return False
        return True


    def Stop(self):
        """Stops all the running workloads from in all the loaded modules"""

        if self.ModulesLoaded() == 0:
            raise RuntimeError(f"No {self._module_type} modules configured")

        self._logger.log(Log.INFO, f"Stopping {self._module_type} modules")
        for (modname, mod) in self.__modules:
            if not mod.WorkloadWillRun():
                continue

            mod.setStop()
            try:
                self._logger.log(Log.DEBUG, f"\t - Stopping {modname}")
                if mod.is_alive():
                    mod.join(2.0)
            except RuntimeError as e:
                self._logger.log(Log.ERR, f"\t\tFailed stopping {modname}: {str(e)}")
        self.__timestamps['stop'] = datetime.now()


    def WaitForCompletion(self, wtime=None):
        """Waits for the running modules to complete their running"""

        self._logger.log(Log.INFO, f"Waiting for {self._module_type} modules to complete")
        for (modname, mod) in self.__modules:
            self._logger.log(Log.DEBUG, f"\t - Waiting for {modname}")
            mod.WaitForCompletion(wtime)
        self._logger.log(Log.DEBUG, f"All {self._module_type} modules completed")


    def MakeReport(self):
        """Collects all the loaded modules reports in a single libxml2.xmlNode() object"""

        rep_n = libxml2.newNode(self._report_tag)

        for (modname, mod) in self.__modules:
            if mod.hadRuntimeError():
                continue
            self._logger.log(Log.DEBUG, f"Getting report from {modname}")
            modrep_n = mod.MakeReport()
            if modrep_n is not None:
                if self._module_type != 'load':
                    # Currently the <loads/> tag will not easily integrate
                    # timestamps. Not sure it makes sense to track this on
                    # load modules.
                    modrep_n.addChild(mod.GetTimestamps())
                rep_n.addChild(modrep_n)

        return rep_n
