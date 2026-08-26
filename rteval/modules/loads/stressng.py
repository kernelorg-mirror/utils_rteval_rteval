# SPDX-License-Identifier: GPL-2.0-or-later
""" Module containing class Stressng to manage stress-ng as an rteval load """
import os
import os.path
import time
import subprocess
import signal
import sys
from rteval.modules.loads import CommandLineLoad
from rteval.Log import Log
from rteval.systopology import SysTopology
from rteval.cpulist_utils import CpuList

def get_valid_stressors():
    """Query stress-ng for list of valid stressor names."""
    try:
        result = subprocess.run(['stress-ng', '--stressors'],
                                capture_output=True, text=True, check=True)
        return result.stdout.strip().split()
    except FileNotFoundError:
        print("stress-ng is not installed. Please install the stress-ng package.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Failed to query stress-ng stressors: {e}")
        sys.exit(1)

def validate_stressor(stressor_name):
    """Validate a single stressor name against stress-ng's available stressors."""
    valid = get_valid_stressors()
    if stressor_name not in valid:
        print(f"Invalid stress-ng stressor: '{stressor_name}'. "
              f"Run 'stress-ng --stressors' to see valid options.")
        sys.exit(1)

class Stressng(CommandLineLoad):
    " This class creates a load module that runs stress-ng "
    def __init__(self, config, logger):
        CommandLineLoad.__init__(self, "stressng", config, logger)
        self.logger = logger
        self.started = False
        self.process = None
        self.cfg = config
        self.__in = None
        self.__out = None
        self.__err = None
        self.__nullfp = None
        self.args = None
        " Only run this module if the user specifies an stressor "
        if self.cfg.stressor is not None:
            self._donotrun = False
        else:
            self._donotrun = True
        # When this module runs, other load modules should not
        self.set_exclusive()

    def _WorkloadSetup(self):
        " Since there is nothing to build, we don't need to do anything here "
        return

    def _WorkloadBuild(self):
        " Nothing to build, so we are ready "
        self._setReady()

    def _WorkloadPrepare(self):
        " Set-up logging "
        self.__nullfp = os.open("/dev/null", os.O_RDWR)
        self.__in = self.__nullfp
        if self._logging:
            self.__out = self.open_logfile("stressng.stdout")
            self.__err = self.open_logfile("stressng.stderr")
        else:
            self.__out = self.__err = self.__nullfp

        # stress-ng is only run if the user specifies an stressor
        self.args = ['stress-ng']
        validate_stressor(self.cfg.stressor)
        self.args.append(f'--{str(self.cfg.stressor)}')
        if self.cfg.workers is not None:
            self.args.append(self.cfg.workers) #default is 0
        if self.cfg.timeout is not None:
            self.args.append('--timeout')
            self.args.append(self.cfg.timeout)

        systop = SysTopology()
        # get the number of nodes
        nodes = systop.getnodes()

        # get the cpus for each node
        cpus = {}
        for n in nodes:
            cpus[n] = systop.getcpus(int(n))
            # if a cpulist was specified, only allow cpus in that list on the node
            if self.cpulist:
                cpus[n] = [c for c in cpus[n] if c in CpuList(self.cpulist).cpus]
            # if a cpulist was not specified, exclude isolated cpus
            else:
                cpus[n] = CpuList(cpus[n]).nonisolated().cpus


        # remove nodes with no cpus available for running
        for node, cpu in cpus.items():
            if not cpu:
                nodes.remove(node)
                self._log(Log.DEBUG, f"node {node} has no available cpus, removing")

        # Always apply taskset to restrict stress-ng to available CPUs
        # This ensures isolated CPUs are excluded (reserved for measurement modules)
        all_cpus = []
        for node in nodes:
            all_cpus.extend(cpus[node])

        if all_cpus:
            cpulist = ",".join([str(c) for c in all_cpus])
            self.args.extend(['--taskset', cpulist])

    def _WorkloadTask(self):
        """ Kick of the workload here """
        if self.started:
            # Only start the task once
            return

        self._log(Log.DEBUG, f'starting with {" ".join(self.args)}')
        try:
            self.process = subprocess.Popen(self.args,
                                            stdout=self.__out,
                                            stderr=self.__err,
                                            stdin=self.__in)
            self.started = True
            self.jobs = 1
            self._log(Log.DEBUG, "running")
        except OSError:
            self._log(Log.DEBUG, "Failed to run")
            self.started = False
        return

    def WorkloadAlive(self):
        " Return true if stress-ng workload is alive "
        if self.started:
            return self.process.poll() is None
        return False

    def _WorkloadCleanup(self):
        " Makesure to kill stress-ng before rteval ends "
        if not self.started:
            return
        # poll() returns None if the process is still running
        while self.process.poll() is None:
            self._log(Log.DEBUG, "Sending SIGINT")
            self.process.send_signal(signal.SIGINT)
            time.sleep(2)
        return


def create(config, logger):
    """ Create an instance of the Stressng class in stressng module """
    return Stressng(config, logger)

def ModuleParameters():
    """ Commandline options for Stress-ng """
    return {
        "stressor": {
            "descr": "stressor name (eg. vm, cpu)",
            "metavar": "STRESSOR"
        },
        "workers": {
            "descr": "number of workers(default: 0 = one per CPU)",
            "default": "0",
            "metavar" : "N"
        },
        "timeout": {
            "descr": "timeout after T seconds",
            "metavar" : "T"
        },
        }
