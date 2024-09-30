# SPDX-License-Identifier: GPL-2.0-or-later
#
#   Copyright 2009 - 2013   Clark Williams <williams@redhat.com>
#   Copyright 2009 - 2013   David Sommerseth <davids@redhat.com>
#

"""
Copyright (c) 2008-2016  Red Hat Inc.

Realtime verification utility
"""
__author__ = "Clark Williams <williams@redhat.com>, David Sommerseth <davids@redhat.com>"
__license__ = "GPLv2 License"

import os
import signal
import sys
import threading
import time
from datetime import datetime
import sysconfig
from rteval.modules.loads import LoadModules
from rteval.modules.measurement import MeasurementModules
from rteval.rtevalReport import rtevalReport
from rteval.Log import Log
from rteval import rtevalConfig
from rteval import version

RTEVAL_VERSION = version.RTEVAL_VERSION

EARLYSTOP = False

stopsig = threading.Event()
def sig_handler(signum, frame):
    """ Handle SIGINT (CTRL + C) or SIGTERM (Termination signal) """
    if signum in (signal.SIGINT, signal.SIGTERM):
        stopsig.set()
        print("*** stop signal received - stopping rteval run ***")
    else:
        raise RuntimeError(f"SIGNAL received! ({signum})")

class RtEval(rtevalReport):
    def __init__(self, config, loadmods, measuremods, logger):
        self.__version = RTEVAL_VERSION

        if not isinstance(config, rtevalConfig.rtevalConfig):
            raise TypeError("config variable is not an rtevalConfig object")

        if not isinstance(measuremods, MeasurementModules):
            raise TypeError("measuremods variable is not a MeasurementModules object")

        if not isinstance(logger, Log):
            raise TypeError("logger variable is not an Log object")

        self.__cfg = config
        self.__logger = logger
        self._loadmods = loadmods
        self._measuremods = measuremods

        self.__rtevcfg = self.__cfg.GetSection('rteval')
        self.__reportdir = None

        # Import SystemInfo here, to avoid DMI warnings if RtEval() is not used
        from .sysinfo import SystemInfo
        self._sysinfo = SystemInfo(self.__rtevcfg, logger=self.__logger)

        if not self.__rtevcfg.xslt_report or not os.path.exists(self.__rtevcfg.xslt_report):
            raise RuntimeError(f"can't find XSL template ({self.__rtevcfg.xslt_report})!")

        # Add rteval directory into module search path
        scheme = 'rpm_prefix'
        if scheme not in sysconfig.get_scheme_names():
            scheme = 'posix_prefix'
        pypath = f"{sysconfig.get_path('platlib', scheme)}/rteval"
        sys.path.insert(0, pypath)
        self.__logger.log(Log.DEBUG, f"Adding {pypath} to search path")

        # Initialise the report module
        rtevalReport.__init__(self, self.__version,
                              self.__rtevcfg.installdir, self.__rtevcfg.annotate)

    @staticmethod
    def __show_remaining_time(remaining):
        secs = int(remaining)
        days = int(secs / 86400)
        if days:
            secs = secs - (days * 86400)
        hours = int(secs / 3600)
        if hours:
            secs = secs - (hours * 3600)
        minutes = int(secs / 60)
        if minutes:
            secs = secs - (minutes * 60)
        print(f'rteval time remaining: {days}, {hours}, {minutes}, {secs}')


    def Prepare(self, onlyload=False):
        builddir = os.path.join(self.__rtevcfg.workdir, 'rteval-build')
        if not os.path.isdir(builddir):
            os.mkdir(builddir)

        # create our report directory
        try:
            # Only create a report dir if we're doing measurements
            # or the loads logging is enabled
            if not onlyload or self.__rtevcfg.logging:
                self.__reportdir = self._make_report_dir(self.__rtevcfg.workdir, "summary.xml")
        except Exception as err:
            raise RuntimeError(f"Cannot create report directory (NFS with rootsquash on?) [{err}]]") from err

        params = {'workdir':self.__rtevcfg.workdir,
                  'reportdir':self.__reportdir and self.__reportdir or "",
                  'builddir':builddir,
                  'srcdir':self.__rtevcfg.srcdir,
                  'verbose': self.__rtevcfg.verbose,
                  'debugging': self.__rtevcfg.debugging,
                  'numcores':self._sysinfo.cpu_getCores(True),
                  'logging':self.__rtevcfg.logging,
                  'memsize':self._sysinfo.mem_get_size(),
                  'numanodes':self._sysinfo.mem_get_numa_nodes(),
                  'duration': float(self.__rtevcfg.duration),
                  'usingCpupower': self.__rtevcfg.usingCpupower
                  }

        if self._loadmods:
            self.__logger.log(Log.INFO, "Preparing load modules")
            self._loadmods.Setup(params)

        self.__logger.log(Log.INFO, "Preparing measurement modules")
        self._measuremods.Setup(params)


    def __RunMeasurement(self):
        global EARLYSTOP

        measure_start = None
        try:
            nthreads = 0

            # start the loads
            if self._loadmods:
                self._loadmods.Start()

            print(f"rteval run on {os.uname()[2]} started at {time.asctime()}")
            onlinecpus = self._sysinfo.cpu_getCores(True)
            if self._loadmods:
                cpulist = self._loadmods._cfg.GetSection("loads").cpulist
                if cpulist:
                    print(f"started {self._loadmods.ModulesLoaded()} loads on cores {cpulist}",
                          end=' ')
                else:
                    print(f"started {self._loadmods.ModulesLoaded()} loads on {onlinecpus} cores",
                          end=' ')
                if self._sysinfo.mem_get_numa_nodes() > 1:
                    print(f" with {self._sysinfo.mem_get_numa_nodes()} numa nodes")
                else:
                    print("")
            cpulist = self._measuremods._cfg.GetSection("measurement").cpulist
            if cpulist:
                print(f"started measurement threads on cores {cpulist}")
            else:
                print(f"started measurement threads on {onlinecpus} cores")
            print(f"Run duration: {str(self.__rtevcfg.duration)} seconds")

            self._measuremods.Start()

            # Unleash the loads and measurement threads
            report_interval = int(self.__rtevcfg.report_interval)
            if self._loadmods:
                self._loadmods.Unleash()
                nthreads = threading.active_count()
            else:
                nthreads = None
            self._measuremods.Unleash()
            measure_start = datetime.now()

            # wait for time to expire or thread to die
            signal.signal(signal.SIGINT, sig_handler)
            signal.signal(signal.SIGTERM, sig_handler)
            self.__logger.log(Log.INFO, f"waiting for duration ({str(self.__rtevcfg.duration)})")
            stoptime = (time.time() + float(self.__rtevcfg.duration))
            currtime = time.time()
            rpttime = currtime + report_interval
            load_avg_checked = 5
            while (currtime <= stoptime) and not stopsig.is_set():
                stopsig.wait(min(stoptime - currtime, 60.0))
                if not self._measuremods.isAlive():
                    stoptime = currtime
                    EARLYSTOP = True
                    self.__logger.log(Log.WARN,
                                      "Measurement threads did not use the full time slot. Doing a controlled stop.")

                if nthreads:
                    if threading.active_count() < nthreads:
                        raise RuntimeError("load thread died!")

                if self._loadmods and not load_avg_checked:
                    self._loadmods.SaveLoadAvg()
                    load_avg_checked = 5
                else:
                    load_avg_checked -= 1

                if currtime >= rpttime:
                    left_to_run = stoptime - currtime
                    self.__show_remaining_time(left_to_run)
                    rpttime = currtime + report_interval
                    if self._loadmods:
                        print(f"load average: {self._loadmods.GetLoadAvg():.2f}")
                currtime = time.time()

            self.__logger.log(Log.DEBUG, "out of measurement loop")
            signal.signal(signal.SIGINT, signal.SIG_DFL)
            signal.signal(signal.SIGTERM, signal.SIG_DFL)

        except RuntimeError as err:
            if not stopsig.is_set():
                raise RuntimeError(f"appeared during measurement: {err}") from err

        finally:
            # stop measurement threads
            self._measuremods.Stop()

            # stop the loads
            if self._loadmods:
                self._loadmods.Stop()

        print(f"stopping run at {time.asctime()}")

        # wait for measurement modules to finish calculating stats
        self._measuremods.WaitForCompletion()

        return measure_start


    def Measure(self):
        """ Run the full measurement suite with reports """
        global EARLYSTOP
        rtevalres = 0
        measure_start = self.__RunMeasurement()

        self._report(measure_start, self.__rtevcfg.xslt_report)
        if self.__rtevcfg.sysreport:
            self._sysinfo.run_sysreport(self.__reportdir)

        if EARLYSTOP:
            rtevalres = 1
        self._sysinfo.copy_dmesg(self.__reportdir)
        self._tar_results()
        return rtevalres
