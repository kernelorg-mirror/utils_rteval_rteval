# SPDX-License-Identifier: GPL-2.0-or-later
#
#   Copyright 2009 - 2013   Clark Williams <williams@redhat.com>
#   Copyright 2012 - 2013   David Sommerseth <davids@redhat.com>
#   Copyright 2014 - 2017   Clark Williams <williams@redhat.com>
#

import sys
import os
import os.path
import glob
import re
import subprocess
from rteval.modules import rtevalRuntimeError
from rteval.modules.loads import CommandLineLoad
from rteval.Log import Log
from rteval.systopology import SysTopology
from rteval.cpulist_utils import CpuList, collapse_cpulist

DEFAULT_KERNEL_PREFIX = "linux-6.17.7"

class KBuildJob:
    '''Class to manage a build job bound to a particular node'''

    def __init__(self, node, kdir, logger=None, cpulist=None):
        self.kdir = kdir
        self.jobid = None
        self.node = node
        self.logger = logger
        self.binder = None
        self.builddir = os.path.dirname(kdir)
        self.objdir = f"{self.builddir}/node{int(node)}"

        if not os.path.isdir(self.objdir):
            os.mkdir(self.objdir)

        # Exclude isolated CPUs if cpulist not set
        cpus_available = len(CpuList(self.node.cpus).nonisolated().cpus)

        if os.path.exists('/usr/bin/numactl') and not cpulist:
            # Use numactl
            self.binder = f'numactl --cpunodebind {int(self.node)}'
            self.jobs = self.calc_jobs_per_cpu() * cpus_available
        elif cpulist:
            # Use taskset
            self.jobs = self.calc_jobs_per_cpu() * len(cpulist)
            self.binder = f'taskset -c {collapse_cpulist(cpulist)}'
        else:
            # Without numactl calculate number of jobs from the node
            self.jobs = self.calc_jobs_per_cpu() * cpus_available

        self.runcmd = f"make O={self.objdir} -C {self.kdir} -j{self.jobs}"
        self.cleancmd = f"make O={self.objdir} -C {self.kdir} clean allmodconfig"
        self.cleancmd += f"&& pushd {self.objdir} && {self.kdir}/scripts/config -d CONFIG_MODULE_SIG_SHA1 -e CONFIG_MODULE_SIG_SHA512 && popd && make O={self.objdir} -C {self.kdir} olddefconfig"
        if self.binder:
            self.runcmd = self.binder + " " + self.runcmd
            self.cleancmd = self.binder + " " + self.cleancmd

        self.log(Log.DEBUG, f"node {int(node)}: jobs == {self.jobs}")
        self.log(Log.DEBUG, f"cleancmd = {self.cleancmd}")
        self.log(Log.DEBUG, f"node{int(node)} kcompile command: {self.runcmd}")

    def __str__(self):
        return self.runcmd

    def log(self, logtype, msg):
        """ starting logging for the kcompile module """
        if self.logger:
            self.logger.log(logtype, f"[kcompile node{int(self.node)}] {msg}")

    def calc_jobs_per_cpu(self):
        """ Calculate the number of kcompile jobs to do """
        mult = 2
        self.log(Log.DEBUG, f"calulating jobs for node {int(self.node)}")
        # get memory total in gigabytes
        mem = int(self.node.meminfo['MemTotal']) / 1024.0 / 1024.0 / 1024.0
        # ratio of gigabytes to #cores
        ratio = float(mem) / float(len(self.node))
        ratio = max(ratio, 1.0)
        if ratio > 2.0:
            mult = 1
        self.log(Log.DEBUG, f"memory/cores ratio on node {int(self.node)}: {ratio}")
        self.log(Log.DEBUG, f"returning jobs/core value of: {int(ratio) * mult}")
        return int(int(ratio) * int(mult))

    def clean(self, sin=None, sout=None, serr=None):
        """ Runs command to clean any previous builds and configure kernel """
        self.log(Log.DEBUG, f"cleaning objdir {self.objdir}")
        subprocess.call(self.cleancmd, shell=True,
                        stdin=sin, stdout=sout, stderr=serr)

    def run(self, sin=None, sout=None, serr=None):
        """ Use Popen to launch a kcompile job """
        self.log(Log.INFO, f"starting workload on node {int(self.node)}")
        self.log(Log.DEBUG, f"running on node {int(self.node)}: {self.runcmd}")
        self.jobid = subprocess.Popen(self.runcmd, shell=True,
                                      stdin=sin, stdout=sout, stderr=serr)

    def isrunning(self):
        """ Query whether a job is running, returns True or False """
        if self.jobid is None:
            return False
        return self.jobid.poll() is None

    def stop(self):
        """ stop a kcompile job """
        if not self.jobid:
            return True
        return self.jobid.terminate()


class Kcompile(CommandLineLoad):
    """ class to compile the kernel as an rteval load """
    def __init__(self, config, logger):
        self.buildjobs = {}
        self.config = config
        self.topology = SysTopology()
        self.cpulist = config.cpulist
        CommandLineLoad.__init__(self, "kcompile", config, logger)
        self.logger = logger
        self._kernel_prefix = ""
        self._log(Log.DEBUG, f'self._cfg.source = {self._cfg.source}')

    def _extract_tarball(self):
        if self.source is None:
            raise rtevalRuntimeError(self, " no source tarball specified!")
        self._log(Log.DEBUG, "unpacking kernel tarball")
        tarargs = ['tar', '-C', self.builddir, '-x']
        if self.source.endswith(".bz2"):
            tarargs.append("-j")
        elif self.source.endswith(".gz"):
            tarargs.append("-z")
        tarargs.append("-f")
        tarargs.append(self.source)
        try:
            subprocess.call(tarargs)
        except:
            self._log(Log.DEBUG, "untarring kernel self.source failed!")
            sys.exit(-1)

    def _remove_build_dirs(self):
        if not os.path.isdir(self.builddir):
            return
        self._log(Log.DEBUG, f"removing kcompile directories in {self.builddir}")
        null = os.open("/dev/null", os.O_RDWR)
        cmd = ["rm", "-rf", self.mydir, *glob.glob(os.path.join(self.builddir, 'node*'))]
        ret = subprocess.call(cmd, stdin=null, stdout=null, stderr=null)
        if ret:
            raise rtevalRuntimeError(self, \
                f"error removing builddir ({self.builddir}) (ret={ret})")

    def _find_tarball(self):
        """ Find the tarball and self._kernel_prefix """

        if 'rc' in self._cfg.source:
            tarfile_prefix = re.search(r"\d{1,2}\.\d{1,3}\-rc\d{1,2}", self._cfg.source).group(0)
        elif 'rteval' in self._cfg.source:
            tarfile_prefix = re.search(r"(\d{1,2}\.\d{1,3}\.\d{1,3}\-rteval)|(\d{1,2}\.\d{1,3}\-rteval)", self._cfg.source).group(0)
        else:
            tarfile_prefix = re.search(r"(\d{1,2}\.\d{1,3}\.\d{1,3})|(\d{1,2}\.\d{1,3})", self._cfg.source).group(0)

        # Save the kernel prefix
        self._kernel_prefix = "linux-" + tarfile_prefix

        # If the user specifies the full kernel name, check if available
        tarfile = os.path.join(self.srcdir, self._cfg.source)
        if os.path.exists(tarfile):
            return tarfile

        # either a tar.xz or tar.gz might exist. Check for both.
        xz_file = os.path.join(self.srcdir,"linux-" + tarfile_prefix + ".tar.xz" )
        gz_file = os.path.join(self.srcdir,"linux-" + tarfile_prefix + ".tar.gz" )
        if os.path.exists(xz_file):
            return xz_file
        if os.path.exists(gz_file):
            return gz_file
        raise rtevalRuntimeError(self, f"tarfile {tarfile} does not exist!")

    def _WorkloadSetup(self):
        if self._donotrun:
            return

        # find our source tarball
        if self._cfg.source:
            self.source = self._find_tarball()
        else:
            tarfiles = glob.glob(os.path.join(self.srcdir, f"{DEFAULT_KERNEL_PREFIX}*"))
            if tarfiles:
                self.source = tarfiles[0]
            else:
                raise rtevalRuntimeError(self, f" no kernel tarballs found in {self.srcdir}")
            self._kernel_prefix = DEFAULT_KERNEL_PREFIX
        self._log(Log.DEBUG, f"self._kernel_prefix = {self._kernel_prefix}")

        # check for existing directory
        kdir = None
        names = os.listdir(self.builddir)
        for d in names:
            if d == self._kernel_prefix:
                kdir = d
                break
        if kdir is None:
            self._extract_tarball()
            names = os.listdir(self.builddir)
            for d in names:
                self._log(Log.DEBUG, f"checking {d}")
                if d == self._kernel_prefix:
                    kdir = d
                    break
        if kdir is None:
            raise rtevalRuntimeError(self, "Can't find kernel directory!")
        self.mydir = os.path.join(self.builddir, kdir)
        self._log(Log.DEBUG, f"mydir = {self.mydir}")
        self._log(Log.DEBUG, f"systopology: {self.topology}")
        self.jobs = len(self.topology)
        self.args = []

        # get the cpus for each node
        self.cpus = {}
        self.nodes = self.topology.getnodes()
        for n in self.nodes:
            self.cpus[n] = self.topology.getcpus(n)
            self.cpus[n].sort()

            # if a cpulist was specified, only allow cpus in that list on the node
            if self.cpulist:
                self.cpus[n] = [c for c in self.cpus[n] if c in CpuList(self.cpulist).cpus]

        # remove nodes with no cpus available for running
        for node, cpus in self.cpus.items():
            if not cpus:
                self.nodes.remove(node)
                self._log(Log.DEBUG, f"node {node} has no available cpus, removing")

        for n in self.nodes:
            self._log(Log.DEBUG, f"Configuring build job for node {int(n)}")
            self.buildjobs[n] = KBuildJob(self.topology[n], self.mydir, \
                self.logger, self.cpus[n] if self.cpulist else None)
            self.args.append(str(self.buildjobs[n])+";")


    def _WorkloadBuild(self):
        if self._donotrun:
            return

        null = os.open("/dev/null", os.O_RDWR)
        if self._logging:
            out = self.open_logfile("kcompile-build.stdout")
            err = self.open_logfile("kcompile-build.stderr")
        else:
            out = err = null

        # clean up any damage from previous runs
        try:
            cmd = ["make", "-C", self.mydir, "-j", str(os.cpu_count()), "mrproper"]
            ret = subprocess.call(cmd, stdin=null, stdout=out, stderr=err)
            if ret:
                # if the above make failed, remove and reinstall the source tree
                self._log(Log.DEBUG, "Invalid state in kernel build tree, reloading")
                self._remove_build_dirs()
                self._extract_tarball()
                ret = subprocess.call(cmd, stdin=null, stdout=out, stderr=err)
                if ret:
                    # give up
                    raise rtevalRuntimeError(self, f"kcompile setup failed: {ret}")
        except KeyboardInterrupt as m:
            self._log(Log.DEBUG, "keyboard interrupt, aborting")
            return
        self._log(Log.DEBUG, "ready to run")
        if self._logging:
            os.close(out)
            os.close(err)
        # clean up object dirs and make sure each has a config file
        for n in self.nodes:
            self.buildjobs[n].clean(sin=null, sout=null, serr=null)
        os.close(null)
        self._setReady()

    def _WorkloadPrepare(self):
        self.__nullfd = os.open("/dev/null", os.O_RDWR)
        if self._logging:
            self.__outfd = self.open_logfile("kcompile.stdout")
            self.__errfd = self.open_logfile("kcompile.stderr")
        else:
            self.__outfd = self.__errfd = self.__nullfd

        if 'cpulist' in self._cfg and self._cfg.cpulist:
            cpulist = self._cfg.cpulist
            self.num_cpus = len(CpuList(cpulist).cpus)
        else:
            cpulist = ""

    def _WorkloadTask(self):
        for n in self.nodes:
            if not self.buildjobs[n]:
                raise RuntimeError(f"Build job not set up for node {int(n)}")
            if self.buildjobs[n].jobid is None or self.buildjobs[n].jobid.poll() is not None:
                # A jobs was started, but now it finished. Check return code.
                # -2 is returned when user forced stop of execution (CTRL-C).
                if self.buildjobs[n].jobid is not None:
                    if self.buildjobs[n].jobid.returncode not in (0, -2):
                        raise RuntimeError(f"kcompile module failed to run (returned {self.buildjobs[n].jobid.returncode}), please check logs for more detail")
                self._log(Log.INFO, f"Starting load on node {n}")
                self.buildjobs[n].run(self.__nullfd, self.__outfd, self.__errfd)

    def WorkloadAlive(self):
        # if any of the jobs has stopped, return False
        for n in self.nodes:
            if self.buildjobs[n].jobid.poll() is not None:
                # Check return code (see above).
                if self.buildjobs[n].jobid.returncode not in (0, -2):
                    raise RuntimeError(f"kcompile module failed to run (returned {self.buildjobs[n].jobid.returncode}), please check logs for more detail")
                return False

        return True


    def _WorkloadCleanup(self):
        if self._donotrun:
            return

        self._log(Log.DEBUG, "out of stopevent loop")
        for n in self.buildjobs:
            if self.buildjobs[n].jobid.poll() is None:
                self._log(Log.DEBUG, f"stopping job on node {int(n)}")
                self.buildjobs[n].jobid.terminate()
                self.buildjobs[n].jobid.wait()
                del self.buildjobs[n].jobid
        os.close(self.__nullfd)
        del self.__nullfd
        if self._logging:
            os.close(self.__outfd)
            del self.__outfd
            os.close(self.__errfd)
            del self.__errfd
        self._setFinished()


def ModuleParameters():
    return {"source":   {"descr": "Source tar ball",
                         "default": "linux-6.17.7.tar.xz",
                         "metavar": "TARBALL"},
            "jobspercore": {"descr": "Number of working threads per core",
                            "default": 2,
                            "metavar": "NUM"},
            }



def create(config, logger):
    return Kcompile(config, logger)
