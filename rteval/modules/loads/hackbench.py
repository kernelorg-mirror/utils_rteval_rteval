# SPDX-License-Identifier: GPL-2.0-or-later

#   hackbench.py - class to manage an instance of hackbench load
#
#   Copyright 2009 - 2013   Clark Williams <williams@redhat.com>
#   Copyright 2009 - 2013   David Sommerseth <davids@redhat.com>
#
""" Load module - run the hackbench program from rt-tests ad a load """

import sys
import os
import os.path
import time
import subprocess
import errno
from signal import SIGKILL
from rteval.modules.loads import CommandLineLoad
from rteval.Log import Log
from rteval.systopology import SysTopology
from rteval.cpulist_utils import CpuList

class Hackbench(CommandLineLoad):
    def __init__(self, config, logger):
        self.__cfg = config
        CommandLineLoad.__init__(self, "hackbench", config, logger)

    def _WorkloadSetup(self):
        if self._donotrun:
            return

        # calculate arguments based on input parameters
        (mem, units) = self.memsize
        if units == 'KB':
            mem = mem / (1024.0 * 1024.0)
        elif units == 'MB':
            mem = mem / 1024.0
        elif units == 'TB':
            mem = mem * 1024

        ratio = float(mem) / float(self.num_cpus)
        if ratio < 0.75:
            if self.__cfg.runlowmem:
                self._log(Log.WARN, f"Low memory system ({ratio} GB/core)!")
            else:
                self._log(Log.WARN, f"Low memory system ({ratio} GB/core)! Not running hackbench")
                self._donotrun = True

        sysTop = SysTopology()
        # get the number of nodes
        self.nodes = sysTop.getnodes()

        # get the cpus for each node
        self.cpus = {}
        biggest = 0
        for n in sysTop.getnodes():
            self.cpus[n] = sysTop.getcpus(int(n))
            # if a cpulist was specified, only allow cpus in that list on the node
            if self.cpulist:
                self.cpus[n] = [c for c in self.cpus[n] if c in CpuList(self.cpulist).cpus]
            # if a cpulist was not specified, exclude isolated cpus
            else:
                self.cpus[n] = CpuList(self.cpus[n]).nonisolated().cpus

            # track largest number of cpus used on a node
            node_biggest = len(self.cpus[n])
            if node_biggest > biggest:
                biggest = node_biggest

        # remove nodes with no cpus available for running
        for node, cpus in list(self.cpus.items()):
            if not cpus:
                self.nodes.remove(node)
                self._log(Log.DEBUG, f"node {node} has no available cpus, removing")

        # setup jobs based on the number of cores available per node
        self.jobs = biggest * 3

        # figure out if we can use numactl or have to use taskset
        self.__usenumactl = False
        self.__multinodes = False
        if len(self.nodes) > 1:
            self.__multinodes = True
            self._log(Log.INFO, f"running with multiple nodes ({len(self.nodes)})")
            if os.path.exists('/usr/bin/numactl') and not self.cpulist:
                self.__usenumactl = True
                self._log(Log.INFO, "using numactl for thread affinity")

        self.args = ['hackbench', '-P',
                     '-g', str(self.jobs),
                     '-l', str(self._cfg.setdefault('loops', '1000')),
                     '-s', str(self._cfg.setdefault('datasize', '1000'))
                     ]

    def _WorkloadBuild(self):
        # Nothing to build, so we're basically ready
        self._setReady()


    def _WorkloadPrepare(self):
        self.__nullfp = os.open("/dev/null", os.O_RDWR)
        if self._logging:
            self.__out = self.open_logfile("hackbench.stdout")
            self.__err = self.open_logfile("hackbench.stderr")
        else:
            self.__out = self.__err = self.__nullfp

        self.tasks = {}

        self._log(Log.DEBUG, f"starting loop (jobs: {self.jobs})")

        self.started = False

    def __starton(self, node):
        if self.__multinodes or self.cpulist:
            if self.__usenumactl:
                args = ['numactl', '--cpunodebind', str(node)] + self.args
            else:
                cpulist = ",".join([str(n) for n in self.cpus[node]])
                args = ['taskset', '-c', cpulist] + self.args
        else:
            args = self.args

        self._log(Log.DEBUG, f"starting on node {node}: args = {args}")
        p = subprocess.Popen(args,
                             stdin=self.__nullfp,
                             stdout=self.__out,
                             stderr=self.__err)
        if not p:
            self._log(Log.DEBUG, f"hackbench failed to start on node {node}")
            raise RuntimeError(f"hackbench failed to start on node {node}")
        return p

    def _WorkloadTask(self):
        if self.shouldStop():
            return

        # just do this once
        if not self.started:
            for n in self.nodes:
                self.tasks[n] = self.__starton(n)
            self.started = True
            return

        for n in self.nodes:
            try:
                if self.tasks[n].poll() is not None:
                    self.tasks[n].wait()
                    self.tasks[n] = self.__starton(n)
            except OSError as e:
                if e.errno != errno.ENOMEM:
                    raise e
                # Exit gracefully without a traceback for out-of-memory errors
                self._log(Log.DEBUG, "ERROR, ENOMEM while trying to launch hackbench")
                print("out-of-memory trying to launch hackbench, exiting")
                sys.exit(-1)


    def WorkloadAlive(self):
        # As hackbench is short-lived, lets pretend it is always alive
        return True


    def _WorkloadCleanup(self):
        if self._donotrun:
            return

        for node in self.nodes:
            if node in self.tasks and self.tasks[node].poll() is None:
                self._log(Log.INFO, f"cleaning up hackbench on node {node}")
                self.tasks[node].send_signal(SIGKILL)
                if self.tasks[node].poll() is None:
                    time.sleep(2)
            self.tasks[node].wait()
            del self.tasks[node]

        os.close(self.__nullfp)
        if self._logging:
            os.close(self.__out)
            del self.__out
            os.close(self.__err)
            del self.__err

        del self.__nullfp



def ModuleParameters():
    return {"jobspercore": {"descr": "Number of working threads per CPU core",
                            "default": 5,
                            "metavar": "NUM"},
            "runlowmem": {"descr": "Run hackbench on machines where low memory is detected",
                            "default": False,
                            "metavar": "True|False"}
            }



def create(config, logger):
    return Hackbench(config, logger)

