# SPDX-License-Identifier: GPL-2.0-or-later
#
#   cyclictest.py - object to manage a cyclictest executable instance
#
#   Copyright 2009 - 2013   Clark Williams <williams@redhat.com>
#   Copyright 2012 - 2013   David Sommerseth <davids@redhat.com>
#
""" cyclictest.py - object to manage a cyclictest executable instance """

import os
import subprocess
import signal
import time
import tempfile
import math
import libxml2
from rteval.Log import Log
from rteval.modules import rtevalModulePrototype
from rteval.systopology import cpuinfo, SysTopology
from rteval.cpulist_utils import expand_cpulist, collapse_cpulist

class RunData:
    '''class to keep instance data from a cyclictest run'''
    def __init__(self, coreid, datatype, priority, logfnc):
        self.__id = coreid
        self.__type = datatype
        self.__priority = int(priority)
        self.description = ''
        # histogram of data
        self.__samples = {}
        self.__numsamples = 0
        self.__min = 100000000
        self.__max = 0
        self.__stddev = 0.0
        self.__mean = 0.0
        self.__mode = 0.0
        self.__median = 0.0
        self.__range = 0.0
        self.__mad = 0.0
        self._log = logfnc

    def __str__(self):
        retval = f"id:         {self.__id}\n"
        retval += f"type:       {self.__type}\n"
        retval += f"numsamples: {self.__numsamples}\n"
        retval += f"min:        {self.__min}\n"
        retval += f"max:        {self.__max}\n"
        retval += f"stddev:     {self.__stddev}\n"
        retval += f"mad:        {self.__mad}\n"
        retval += f"mean:       {self.__mean}\n"
        return retval

    def get_max(self):
        return self.__max

    def update_max(self, value):
        if value > self.__max:
            self.__max = value

    def update_min(self, value):
        if value < self.__min:
            self.__min = value

    def bucket(self, index, value):
        self.__samples[index] = self.__samples.setdefault(index, 0) + value
        if value:
            self.update_max(index)
            self.update_min(index)
        self.__numsamples += value

    def reduce(self):

        # check to see if we have any samples and if we
        # only have 1 (or none) set the calculated values
        # to zero and return
        if self.__numsamples <= 1:
            self._log(Log.DEBUG, f"skipping {self.__id} ({self.__numsamples} samples)")
            self.__mad = 0
            self.__stddev = 0
            return

        self._log(Log.INFO, f"reducing {self.__id}")
        total = 0 # total number of samples
        total_us = 0
        keys = list(self.__samples.keys())
        keys.sort()

        # if numsamples is odd, then + 1 gives us the actual mid
        # if numsamples is even, we avg mid and mid + 1, so we actually
        # want to know mid + 1 since we will combine it with mid and
        # the lastkey if the last key is at the end of a previous bucket
        mid = int(self.__numsamples / 2) + 1

        # mean, mode, and median
        occurrences = 0
        lastkey = -1
        for i in keys:
            if mid > total and mid <= total + self.__samples[i]:
                # Test if numsamples is even and if mid+1 is the next bucket
                if self.__numsamples & 1 != 0 and mid == total+1:
                    self.__median = (lastkey + i) / 2
                else:
                    self.__median = i
            lastkey = i
            total += self.__samples[i]
            total_us += (i * self.__samples[i])
            if self.__samples[i] > occurrences:
                occurrences = self.__samples[i]
                self.__mode = i
        self.__mean = float(total_us) / float(self.__numsamples)

        # range
        for i in keys:
            if self.__samples[i]:
                low = i
                break
        high = keys[-1]
        while high and self.__samples.get(high, 0) == 0:
            high -= 1
        self.__range = high - low

        # Mean Absolute Deviation and standard deviation
        madsum = 0
        varsum = 0
        for i in keys:
            madsum += float(abs(float(i) - self.__mean) * self.__samples[i])
            varsum += float(((float(i) - self.__mean) ** 2) * self.__samples[i])
        self.__mad = madsum / self.__numsamples
        self.__stddev = math.sqrt(varsum / (self.__numsamples - 1))


    def MakeReport(self):
        rep_n = libxml2.newNode(self.__type)
        if self.__type == 'system':
            rep_n.newProp('description', self.description)
        else:
            rep_n.newProp('id', str(self.__id))
            rep_n.newProp('priority', str(self.__priority))

        stat_n = rep_n.newChild(None, 'statistics', None)

        stat_n.newTextChild(None, 'samples', str(self.__numsamples))

        if self.__numsamples > 0:
            n = stat_n.newTextChild(None, 'minimum', str(self.__min))
            n.newProp('unit', 'us')

            n = stat_n.newTextChild(None, 'maximum', str(self.__max))
            n.newProp('unit', 'us')

            n = stat_n.newTextChild(None, 'median', str(self.__median))
            n.newProp('unit', 'us')

            n = stat_n.newTextChild(None, 'mode', str(self.__mode))
            n.newProp('unit', 'us')

            n = stat_n.newTextChild(None, 'range', str(self.__range))
            n.newProp('unit', 'us')

            n = stat_n.newTextChild(None, 'mean', str(self.__mean))
            n.newProp('unit', 'us')

            n = stat_n.newTextChild(None, 'mean_absolute_deviation', str(self.__mad))
            n.newProp('unit', 'us')

            n = stat_n.newTextChild(None, 'standard_deviation', str(self.__stddev))
            n.newProp('unit', 'us')

            hist_n = rep_n.newChild(None, 'histogram', None)
            hist_n.newProp('nbuckets', str(len(self.__samples)))
            keys = list(self.__samples.keys())
            keys.sort()
            for k in keys:
                if self.__samples[k] == 0:
                    # Don't report buckets without any samples
                    continue
                b_n = hist_n.newChild(None, 'bucket', None)
                b_n.newProp('index', str(k))
                b_n.newProp('value', str(self.__samples[k]))

        return rep_n


class Cyclictest(rtevalModulePrototype):
    """ measurement module for rteval """
    def __init__(self, config, logger=None):
        rtevalModulePrototype.__init__(self, 'measurement', 'cyclictest', logger)
        self.__cfg = config

        # Create a RunData object per CPU core
        self.__numanodes = int(self.__cfg.setdefault('numanodes', 0))
        self.__priority = int(self.__cfg.setdefault('priority', 95))
        default_buckets = ModuleParameters()["buckets"]["default"]
        self.__buckets = int(self.__cfg.setdefault('buckets', default_buckets))
        self.__numcores = 0
        self.__cyclicdata = {}
        self.__cpulist = self.__cfg.setdefault('cpulist', "")
        self.__cpus = [str(c) for c in expand_cpulist(self.__cpulist)]
        self.__numcores = len(self.__cpus)

        info = cpuinfo()

        # create a RunData object for each core we'll measure
        for core in self.__cpus:
            self.__cyclicdata[core] = RunData(core, 'core', self.__priority,
                                              logfnc=self._log)
            self.__cyclicdata[core].description = info[core]['model name']

        # Create a RunData object for the overall system
        self.__cyclicdata['system'] = RunData('system',
                                              'system', self.__priority,
                                              logfnc=self._log)
        self.__cyclicdata['system'].description = (f"({self.__numcores} cores) ") + info['0']['model name']

        # Logging configuration
        self._logging = self.__cfg.setdefault('logging', False)
        self.__reportdir = self.__cfg.setdefault('reportdir', os.getcwd())

        self._log(Log.DEBUG, f"system using {self.__numcores} cpu cores")
        self.__started = False
        self.__cyclicoutput = None
        self.__breaktraceval = None
        self.set_latency_test()


    def __open_logfile(self, name):
        """Open a log file in the reportdir/logs directory"""
        logdir = os.path.join(self.__reportdir, "logs")
        if not os.path.exists(logdir):
            os.makedirs(logdir)
        return os.open(os.path.join(logdir, name), os.O_CREAT|os.O_RDWR|os.O_TRUNC)

    @staticmethod
    def __get_debugfs_mount():
        ret = None
        with open('/proc/mounts') as mounts:
            for l in mounts:
                field = l.split()
                if field[2] == "debugfs":
                    ret = field[1]
                    break
            return ret


    def _WorkloadSetup(self):
        self.__cyclicprocess = None


    def _WorkloadBuild(self):
        self._setReady()


    def _WorkloadPrepare(self):
        self.__interval = 'interval' in self.__cfg and f'-i{int(self.__cfg.interval)}' or ""

        self.__cmd = ['cyclictest',
                      self.__interval,
                      '-qmu',
                      f'-h {self.__buckets}',
                      f"-p{int(self.__priority)}",
                      ]
        self.__cmd.append(f'-t{self.__numcores}')
        self.__cmd.append(f'-a{self.__cpulist}')

        if (self.__cfg.usingCpupower):
            self.__cmd.append('--default-system')

        if 'threads' in self.__cfg and self.__cfg.threads:
            self.__cmd.append(f"-t{int(self.__cfg.threads)}")

        # Should have either breaktrace or threshold, not both
        if 'breaktrace' in self.__cfg and self.__cfg.breaktrace:
            self.__cmd.append(f"-b{int(self.__cfg.breaktrace)}")
            self.__cmd.append("--tracemark")
        elif self.__cfg.threshold:
            self.__cmd.append(f"-b{int(self.__cfg.threshold)}")

        # Setup output file - use actual log file if logging enabled, otherwise temp file
        if self._logging:
            self.__cyclicoutput = self.__open_logfile("cyclictest.stdout")
        else:
            self.__cyclicoutput = tempfile.SpooledTemporaryFile(mode='w+b')


    def _WorkloadTask(self):
        if self.__started:
            # Don't restart cyclictest if it is already running
            return

        self._log(Log.DEBUG, f'starting with cmd: {" ".join(self.__cmd)}')
        self.__nullfp = os.open('/dev/null', os.O_RDWR)

        debugdir = self.__get_debugfs_mount()
        if 'breaktrace' in self.__cfg and self.__cfg.breaktrace and debugdir:
            # Ensure that the trace log is clean
            trace = os.path.join(debugdir, 'tracing', 'trace')
            with open(os.path.join(trace), "w") as fp:
                fp.write("0")
                fp.flush()

        # Seek to beginning - only needed for temp files, file descriptors start at position 0
        if not self._logging:
            self.__cyclicoutput.seek(0)

        self.__cyclicprocess = subprocess.Popen(self.__cmd,
                                                stdout=self.__cyclicoutput,
                                                stderr=self.__nullfp,
                                                stdin=self.__nullfp)
        self.__started = True

    def WorkloadAlive(self):
        if self.__started:
            return self.__cyclicprocess.poll() is None
        return False

    def get_subprocess_pids(self):
        """Return PID of cyclictest process"""
        if self.__cyclicprocess and self.__cyclicprocess.poll() is None:
            return [self.__cyclicprocess.pid]
        return []

    def _parse_max_latencies(self, line):
        if not line.startswith('# Max Latencies: '):
            return

        try:
            line = line.split(':')[1]
            vals = [int(x) for x in line.split()]

            for i, core in enumerate(self.__cpus):
                self.__cyclicdata[core].update_max(vals[i])
                self.__cyclicdata['system'].update_max(vals[i])
        except (IndexError, ValueError) as e:
            self._log(Log.WARN, f"Error parsing max latencies: {e}")


    def _WorkloadCleanup(self):
        if not self.__started:
            return

        # Send SIGINT and wait for graceful exit
        # Limit attempts to avoid infinite loop (RHEL-140898)
        max_attempts = 5
        attempt = 0
        while self.__cyclicprocess.poll() is None and attempt < max_attempts:
            self._log(Log.DEBUG, f"Sending SIGINT (attempt {attempt + 1}/{max_attempts})")
            os.kill(self.__cyclicprocess.pid, signal.SIGINT)
            time.sleep(2)
            attempt += 1

        # Check if process exited
        exit_code = self.__cyclicprocess.returncode
        if exit_code is None:
            # Process still running after max attempts, force kill
            self._log(Log.WARN, "cyclictest did not respond to SIGINT, sending SIGKILL")
            os.kill(self.__cyclicprocess.pid, signal.SIGKILL)
            self.__cyclicprocess.wait()
            exit_code = self.__cyclicprocess.returncode
        elif exit_code != 0:
            self._log(Log.WARN, f"cyclictest exited with non-zero status: {exit_code}")

        # Parse histogram output - use try/finally to ensure _setFinished() is always called
        # This prevents hangs if parsing fails due to partial output (RHEL-140898)
        try:
            # Read output - handle both file descriptors and temp files
            if self._logging:
                # For file descriptors, read the entire file content
                os.lseek(self.__cyclicoutput, 0, os.SEEK_SET)
                output_data = os.read(self.__cyclicoutput, 10*1024*1024)  # Read up to 10MB
                output_lines = output_data.decode('utf-8', errors='replace').splitlines(keepends=True)
            else:
                # For temp files, use seek and iterate
                self.__cyclicoutput.seek(0)
                output_lines = self.__cyclicoutput

            for line in output_lines:
                if isinstance(line, bytes):
                    line = bytes.decode(line)
                elif not isinstance(line, str):
                    line = str(line)
                if line.startswith('#'):
                    # Catch if cyclictest stopped due to a breaktrace
                    if line.startswith('# Break value: '):
                        try:
                            self.__breaktraceval = int(line.split(':')[1])
                        except (IndexError, ValueError) as e:
                            self._log(Log.WARN, f"Error parsing break value: {e}")
                    elif line.startswith('# Max Latencies: '):
                        self._parse_max_latencies(line)
                    continue

                # Skipping blank lines
                if not line:
                    continue

                vals = line.split()
                if not vals:
                    # If we don't have any values, don't try parsing
                    continue

                try:
                    index = int(vals[0])
                except (ValueError, IndexError):
                    self._log(Log.DEBUG, f"cyclictest: unexpected output: {line}")
                    continue

                # Validate line has expected number of fields: 1 index + (cores * 1 value)
                expected_fields = 1 + self.__numcores
                if len(vals) < expected_fields:
                    self._log(Log.DEBUG, f'Skipping incomplete histogram line at bucket {index} '
                              f'({len(vals)} fields, expected {expected_fields})')
                    continue

                for i, core in enumerate(self.__cpus):
                    try:
                        self.__cyclicdata[core].bucket(index, int(vals[i+1]))
                        self.__cyclicdata['system'].bucket(index, int(vals[i+1]))
                    except (IndexError, ValueError) as e:
                        # Handle partial output from cyclictest (can happen on SIGINT during cleanup)
                        self._log(Log.DEBUG, f"Skipping incomplete bucket data for core {core} "
                                  f"(expected during process termination): {e}")
                        continue

            # generate statistics for each RunData object
            for n in list(self.__cyclicdata.keys()):
                #print "reducing self.__cyclicdata[%s]" % n
                self.__cyclicdata[n].reduce()
                #print self.__cyclicdata[n]

        except Exception as e:
            self._log(Log.ERR, f"Error parsing cyclictest output: {e}")
        finally:
            # Always signal completion to avoid hangs
            self._setFinished()
            self.__started = False

            # Close output file - use os.close for file descriptors, .close() for temp files
            if self._logging:
                os.close(self.__cyclicoutput)
            else:
                self.__cyclicoutput.close()

            os.close(self.__nullfp)
            del self.__nullfp


    def MakeReport(self):
        rep_n = libxml2.newNode('cyclictest')
        rep_n.newProp('command_line', ' '.join(self.__cmd))

        # If it was detected cyclictest was aborted somehow,
        # report the reason
        abrt_n = libxml2.newNode('abort_report')
        abrt = False
        if self.__breaktraceval:
            abrt_n.newProp('reason', 'breaktrace')
            btv_n = abrt_n.newChild(None, 'breaktrace', None)
            btv_n.newProp('latency_threshold', str(self.__cfg.breaktrace) if self.__cfg.breaktrace else str(self.__cfg.threshold))
            btv_n.newProp('measured_latency', str(self.__breaktraceval))
            abrt = True

        # Only add the <abort_report/> node if an abortion happened
        if abrt:
            rep_n.addChild(abrt_n)

        # Let the user know if max latency overshot the number of buckets
        if self.__cyclicdata["system"].get_max() > self.__buckets:
            self._log(Log.ERR, f'Max latency({self.__cyclicdata["system"].get_max()}us) exceeded histogram range({self.__buckets}us). Skipping statistics')
            self._log(Log.ERR, "Increase number of buckets to avoid lost samples")
            return rep_n

        rep_n.addChild(self.__cyclicdata["system"].MakeReport())
        for thr in self.__cpus:
            if str(thr) not in self.__cyclicdata:
                continue
            rep_n.addChild(self.__cyclicdata[str(thr)].MakeReport())

        return rep_n


def ModuleParameters():
    """ default parameters """
    return {"interval": {"descr": "Base interval of the threads in microseconds",
                         "default": 100,
                         "metavar": "INTV_US"},
            "buckets":  {"descr": "Histogram width",
                         "default": 3500,
                         "metavar": "NUM"},
            "priority": {"descr": "Run cyclictest with the given priority",
                         "default": 95,
                         "metavar": "PRIO"},
            "breaktrace": {"descr": "Send a break trace command when latency > USEC",
                           "default": None,
                           "metavar": "USEC"},
            "threshold": {"descr": "Exit rteval if latency > USEC",
                          "default": None,
                          "metavar": "USEC"}
            }



def create(params, logger):
    """ Instantiate a Cyclictest measurement module object """
    return Cyclictest(params, logger)


if __name__ == '__main__':
    from rteval.rtevalConfig import rtevalConfig

    l = Log()
    l.SetLogVerbosity(Log.INFO|Log.DEBUG|Log.ERR|Log.WARN)

    cfg = rtevalConfig({}, logger=l)
    prms = {}
    modprms = ModuleParameters()
    for c, p in list(modprms.items()):
        prms[c] = p['default']
    cfg.AppendConfig('cyclictest', prms)

    cfg_ct = cfg.GetSection('cyclictest')
    cfg_ct.cpulist = collapse_cpulist(SysTopology().online_cpus())

    runtime = 10

    c = Cyclictest(cfg_ct, l)
    c._WorkloadSetup()
    c._WorkloadPrepare()
    c._WorkloadTask()
    time.sleep(runtime)
    c._WorkloadCleanup()
    rep_n = c.MakeReport()

    xml = libxml2.newDoc('1.0')
    xml.setRootElement(rep_n)
    xml.saveFormatFileEnc('-', 'UTF-8', 1)
