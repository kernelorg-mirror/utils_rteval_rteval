# SPDX-License-Identifier: GPL-2.0-or-later
#
#   Copyright 2024  John Kacur <jkacur@redhat.com>
#
""" timerlat.py - object to manage rtla timerlat """
import os
import subprocess
import signal
import time
import tempfile
import math
import sys
import libxml2
from rteval.Log import Log
from rteval.modules import rtevalModulePrototype
from rteval.systopology import cpuinfo, SysTopology
from rteval.cpulist_utils import expand_cpulist, collapse_cpulist


class TLRunData:
    ''' class to store instance data from a timerlat run '''
    def __init__(self, coreid, datatype, priority, logfnc):
        self.__id = coreid
        self.__type = datatype
        self.__priority = int(priority)
        self.description = ''
        self._log = logfnc
        self.duration = ''
        # histogram data, irqs, kernel threads and user threads per core
        self.irqs = {}
        self.thrs = {}
        self.usrs = {}
        self.__samples = {}
        self.__numsamples = 0
        self.min = 100000000
        self.max = 0
        self.__stddev = 0.0
        self.__mean = 0.0
        self.__mode = 0.0
        self.__median = 0.0
        self.__range = 0.0

    def update_max(self, value):
        """ highest bucket with a value """
        if value > self.max:
            self.max = value

    def update_min(self, value):
        """ lowest bucket with a value """
        if value < self.min:
            self.min = value

    def bucket(self, index, val1, val2, val3):
        """ Store results index=bucket number, val1=IRQ, val2=thr, val3=usr """
        values = val1 + val2 + val3
        self.__samples[index] = self.__samples.setdefault(index, 0) + values
        self.irqs[index] = val1
        self.thrs[index] = val2
        self.usrs[index] = val3
        if values:
            self.update_max(index)
            self.update_min(index)
        self.__numsamples += values

    def reduce(self):
        """ Calculate statistics """
        # Check to see if we have any samples. If there are 1 or 0, return
        if self.__numsamples <= 1:
            self._log(Log.DEBUG, f"skipping {self.__id} ({self.__numsamples} samples)")
            self.__mad = 0
            self.__stddev = 0
            return

        self._log(Log.INFO, f"reducing {self.__id}")
        total = 0   # total number of samples
        total_us = 0
        keys = list(self.__samples.keys())
        keys.sort()

        # if numsamples is odd, then + 1 gives us the actual mid
        # if numsamples is even, we avg mid and mid + 1, so we actually
        # want to know mid + 1 since we will combine it with mid and
        # the lastkey if the last key is at the end of a previous bucket
        mid = int(self.__numsamples / 2) + 1

        # mean, mode and median
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
            total_us += i * self.__samples[i]
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

        # Mean Absolute Deviation and Standard Deviation
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
            n = stat_n.newTextChild(None, 'minimum', str(self.min))
            n.newProp('unit', 'us')

            n = stat_n.newTextChild(None, 'maximum', str(self.max))
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

class Timerlat(rtevalModulePrototype):
    """ measurement modules for rteval """
    def __init__(self, config, logger=None):
        rtevalModulePrototype.__init__(self, 'measurement', 'timerlat', logger)

        self.__cfg = config

        self.__numanodes = int(self.__cfg.setdefault('numanodes', 0))
        self.__priority = int(self.__cfg.setdefault('priority', 95))
        default_buckets = ModuleParameters()["buckets"]["default"]
        self.__buckets = int(self.__cfg.setdefault('buckets', default_buckets))

        self.__cpulist = self.__cfg.setdefault('cpulist', "")
        self.__cpus = [str(c) for c in expand_cpulist(self.__cpulist)]
        self.__numcores = len(self.__cpus)

        # Logging configuration
        self._logging = self.__cfg.setdefault('logging', False)
        self.__reportdir = self.__cfg.setdefault('reportdir', os.getcwd())

        # Has tracing been triggered
        self.__stoptrace = False
        # This stores the output from rtla
        self.__posttrace = ""
        # Stop Trace Data
        self.__stdata = {}
        # Stop Trace Cpu
        self.stcpu = -1

        self.__timerlat_out = None
        self.__timerlat_err = None
        self.__started = False

        # Create a TLRunData object for each core we'll measure
        info = cpuinfo()
        self.__timerlatdata = {}
        for core in self.__cpus:
            self.__timerlatdata[core] = TLRunData(core, 'core', self.__priority,
                                                logfnc=self._log)
            self.__timerlatdata[core].description = info[core]['model name']

        # Create a TLRunData object for the overall system
        self.__timerlatdata['system'] = TLRunData('system', 'system',
                                                  self.__priority,
                                                  logfnc=self._log)
        self.__timerlatdata['system'].description = (f"({self.__numcores} cores) ") + info['0']['model name']
        self._log(Log.DEBUG, f"system using {self.__numcores} cpu cores")
        self.set_latency_test()

    def __open_logfile(self, name):
        """Open a log file in the reportdir/logs directory"""
        logdir = os.path.join(self.__reportdir, "logs")
        if not os.path.exists(logdir):
            os.makedirs(logdir)
        return os.open(os.path.join(logdir, name), os.O_CREAT|os.O_RDWR|os.O_TRUNC)

    def _WorkloadSetup(self):
        self.__timerlat_process = None

    def _WorkloadBuild(self):
        self._setReady()

    def _WorkloadPrepare(self):
        # Use space-separated arguments to avoid rtla short option parsing bug
        # with attached arguments (e.g., -p100 vs -p 100)
        self.__cmd = ['rtla', 'timerlat', 'hist']
        if 'interval' in self.__cfg:
            self.__cmd.extend(['-p', str(int(self.__cfg.interval))])
        self.__cmd.extend(['-P', f'f:{int(self.__priority)}', '-u'])
        self.__cmd.extend(['-c', self.__cpulist])
        self.__cmd.extend(['-E', str(self.__buckets)])
        self.__cmd.append('--no-summary')
        # Disable auto-analysis
        self.__cmd.append('--no-aa')

        # Add dma-latency option if configured (default is 0)
        # If dma_latency is explicitly set to None, don't pass the option to rtla
        dma_latency = self.__cfg.setdefault('dma_latency', '0')
        if dma_latency is not None and str(dma_latency).lower() != 'none':
            self.__cmd.append(f'--dma-latency={dma_latency}')

        if self.__cfg.stoptrace:
            self.__cmd.extend(['-T', str(int(self.__cfg.stoptrace))])

        if self.__cfg.trace:
            if not self.__cfg.stoptrace:
                self._log(Log.WARN, f'Ignoring trace={self.__cfg.trace}, because stoptrace not invoked')
            else:
                self.__cmd.extend(['-t', self.__cfg.trace])

        self._log(Log.DEBUG, f'self.__cmd = {self.__cmd}')

        # Setup output files - use actual log files if logging enabled, otherwise temp files
        if self._logging:
            self.__timerlat_out = self.__open_logfile("timerlat.stdout")
            self.__timerlat_err = self.__open_logfile("timerlat.stderr")
        else:
            self.__timerlat_out = tempfile.SpooledTemporaryFile(mode='w+b')
            self.__timerlat_err = tempfile.SpooledTemporaryFile(mode='w+b')


    def _WorkloadTask(self):
        if self.__started:
            return

        self._log(Log.DEBUG, f'starting with cmd: {" ".join(self.__cmd)}')

        # Seek to beginning - only needed for temp files, file descriptors start at position 0
        if not self._logging:
            self.__timerlat_out.seek(0)
            self.__timerlat_err.seek(0)

        # If cpuset is configured, launch process inside the cpuset
        # This is critical for timerlat - migrating it mid-startup disrupts initialization
        preexec_fn = None
        if hasattr(self.__cfg, 'cpuset_path') and self.__cfg.cpuset_path:
            def move_to_cpuset():
                """Move child process into cpuset before exec"""
                try:
                    cpuset_procs = os.path.join(self.__cfg.cpuset_path, 'cgroup.procs')
                    with open(cpuset_procs, 'w') as f:
                        f.write(str(os.getpid()))
                except Exception:
                    pass  # Fail silently - parent will attempt migration as fallback
            preexec_fn = move_to_cpuset

        self.__timerlat_process = subprocess.Popen(self.__cmd,
                                                   stdout=self.__timerlat_out,
                                                   stderr=self.__timerlat_err,
                                                   stdin=None,
                                                   preexec_fn=preexec_fn)
        self.__started = True

    def WorkloadAlive(self):
        if self.__started:
            return self.__timerlat_process.poll() is None
        return False

    def get_subprocess_pids(self):
        """Return PID of timerlat process"""
        if self.__timerlat_process and self.__timerlat_process.poll() is None:
            return [self.__timerlat_process.pid]
        return []

    def _WorkloadCleanup(self):
        if not self.__started:
            return

        # Send SIGINT and wait for graceful exit
        # Limit attempts to avoid infinite loop and double-SIGINT issues (RHEL-140898)
        max_attempts = 5
        attempt = 0
        while self.__timerlat_process.poll() is None and attempt < max_attempts:
            self._log(Log.DEBUG, f"Sending SIGINT (attempt {attempt + 1}/{max_attempts})")
            os.kill(self.__timerlat_process.pid, signal.SIGINT)
            time.sleep(2)
            attempt += 1

        # Check if process exited
        exit_code = self.__timerlat_process.returncode
        if exit_code is None:
            # Process still running after max attempts, force kill
            self._log(Log.WARN, "timerlat did not respond to SIGINT, sending SIGKILL")
            os.kill(self.__timerlat_process.pid, signal.SIGKILL)
            self.__timerlat_process.wait()
            exit_code = self.__timerlat_process.returncode
        elif exit_code != 0:
            self._log(Log.WARN, f"timerlat exited with non-zero status: {exit_code}")


        # Parse histogram output - use try/finally to ensure _setFinished() is always called
        # This prevents hangs if parsing fails due to partial output (RHEL-140898)
        try:
            # Read output - handle both file descriptors and temp files
            if self._logging:
                # For file descriptors, read the entire file content
                os.lseek(self.__timerlat_out, 0, os.SEEK_SET)
                output_data = os.read(self.__timerlat_out, 10*1024*1024)  # Read up to 10MB
                output_lines = output_data.decode('utf-8', errors='replace').splitlines(keepends=True)
            else:
                # For temp files, use seek and iterate
                self.__timerlat_out.seek(0)
                output_lines = self.__timerlat_out

            blocking_thread_detected = False
            softirq_interference_detected = False
            irq_interference_detected = False

            for line in output_lines:
                if isinstance(line, bytes):
                    line = bytes.decode(line)
                elif not isinstance(line, str):
                    line = str(line)

                # Skip any blank lines
                if not line:
                    continue

                # Parsing if stoptrace has been invoked
                if self.__stoptrace:
                    self.__posttrace += line
                    line = line.strip()
                    fields = line.split()
                    if not line:
                        continue
                    if line.startswith("##") and fields[1] == "CPU":
                        self.stcpu = int(fields[2])
                        self._log(Log.DEBUG, f"self.stcpu = {self.stcpu}")
                        self.__stdata[self.stcpu] = {}
                        continue
                    if self.stcpu == -1:
                        self._log(Log.WARN, "Stop trace has been invoked, but a stop cpu has not been identified.")
                        continue
                    if line.startswith('------------------'):
                        blocking_thread_detected = False
                        softirq_interference_detected = False
                        irq_interference_detected = False
                        continue

                    # work around rtla not printing ':' after all names
                    if line.startswith('Softirq interference'):
                        name = 'Softirq_interference'
                    elif line.startswith('IRQ interference'):
                        name = 'IRQ_interference'
                    else:
                        name = ''.join(line.split(':')[0]).replace(' ', '_')
                    self._log(Log.DEBUG, f"name={name}")

                    if name in ['Thread_latency']:
                        latency = fields[-3]
                        percent = fields[-1].strip('()%')
                        self._log(Log.DEBUG, f'{name} = ({latency}, {percent})')
                        self.__stdata[self.stcpu][name] = (latency, percent)
                        continue
                    if name in ['Timerlat_IRQ_duration', 'IRQ_handler_delay', 'Blocking_thread', 'IRQ_interference', 'Softirq_interference']:
                        latency = fields[-4]
                        percent = fields[-2].strip('(')
                        if name == 'IRQ_handler_delay' and fields[3] == '(exit':
                            name = 'IRQ_handler_delay_exit_from_idle'
                        self._log(Log.DEBUG, f'{name} = ({latency}, {percent})')
                        self.__stdata[self.stcpu][name] = (latency, percent)
                        detected = {'Blocking_thread' : (True, False, False),
                                    'IRQ_interference' : (False, True, False),
                                    'Softirq_interference' : (False, False, True) }
                        if name in ('Blocking_thread', 'IRQ_interference', 'Softirq_interference'):
                            blocking_thread_detected, irq_interference_detected, softirq_interference_detected = detected.get(name)
                        continue
                    if name in ["IRQ_latency", "Previous_IRQ_interference"]:
                        latency = fields[-2]
                        self._log(Log.DEBUG, f'{name} = {fields[-2]}')
                        self.__stdata[self.stcpu][name] = fields[-2]
                        continue
                    if blocking_thread_detected or softirq_interference_detected or irq_interference_detected:
                        if blocking_thread_detected:
                            field_name = "blocking_thread"
                        elif softirq_interference_detected:
                            field_name = "softirq_interference"
                        elif irq_interference_detected:
                            field_name = "irq_interference"
                        thread = " ".join(fields[0:-2])
                        latency = fields[-2]
                        self._log(Log.DEBUG, f"{field_name} += [({thread}, {latency})]")
                        self.__stdata[self.stcpu].setdefault(field_name, [])
                        self.__stdata[self.stcpu][field_name] += [(thread, latency)]
                        continue
                    if name == "Max_timerlat_IRQ_latency_from_idle":
                        latency = fields[-5]
                        max_timerlat_cpu = int(fields[-1])
                        self._log(Log.DEBUG, f'self.__stdata[{max_timerlat_cpu}][{name}] = {latency}')
                        self.__stdata.setdefault(max_timerlat_cpu, {})
                        self.__stdata[max_timerlat_cpu][name] = latency
                    else:
                        self._log(Log.DEBUG, f'line = {line}')
                    continue

                if line.startswith('#'):
                    if line.startswith('# Duration:'):
                        duration = line.split()[2]
                        duration += line.split()[3]
                        self.__timerlatdata['system'].duration = duration
                    continue
                elif line.startswith('Index'):
                    #print(line)
                    continue
                elif line.startswith('over:'):
                    #print(line)
                    continue
                elif line.startswith('count:'):
                    #print(line)
                    continue
                elif line.startswith('min:'):
                    #print(line)
                    continue
                elif line.startswith('avg:'):
                    #print(line)
                    continue
                elif line.startswith('max:'):
                    #print(line)
                    continue
                elif line.startswith('rtla timerlat hit stop tracing'):
                    self.__stoptrace = True
                    self.__posttrace += line
                    continue
                elif line.startswith('ALL:'):
                    # We should only see 'ALL:' without timerlat --no-summary
                    # print(line)
                    continue
                else:
                    #print(line)
                    pass

                vals = line.split()
                if not vals:
                    # If we don't have any values, don't try parsing
                    continue
                try:
                    # The index corresponds to the bucket number
                    index = int(vals[0])
                except ValueError:
                    self._log(Log.DEBUG, f'timerlat: unexpected output: {line}')
                    continue

                # Validate line has expected number of fields: 1 index + (cores * 3 values)
                expected_fields = 1 + self.__numcores * 3
                if len(vals) < expected_fields:
                    self._log(Log.DEBUG, f'Skipping incomplete histogram line at bucket {index} '
                              f'({len(vals)} fields, expected {expected_fields})')
                    continue

                for i, core in enumerate(self.__cpus):
                    # There might not be a count on every cpu if tracing invoked
                    try:
                        if i*3 + 1 >= len(vals):
                            self.__timerlatdata[core].bucket(index, 0, 0, 0)
                            self.__timerlatdata['system'].bucket(index, 0, 0, 0)
                        else:
                            self.__timerlatdata[core].bucket(index, int(vals[i*3+1]),
                                                         int(vals[i*3+2]),
                                                         int(vals[i*3+3]))
                            self.__timerlatdata['system'].bucket(index, int(vals[i*3+1]),
                                                         int(vals[i*3+2]),
                                                         int(vals[i*3+3]))
                    except (IndexError, ValueError) as e:
                        # Handle partial output from rtla (can happen on SIGINT during cleanup)
                        self._log(Log.DEBUG, f"Skipping incomplete bucket data for core {core} "
                                  f"(expected during process termination): {e}")
                        continue

                # Generate statistics for each RunData object
                for n in list(self.__timerlatdata.keys()):
                    self.__timerlatdata[n].reduce()

        except Exception as e:
            self._log(Log.ERR, f"Error parsing timerlat output: {e}")
        finally:
            # Always signal completion to avoid hangs
            self._setFinished()
            self.__started = False

            # Close output files - method differs for file descriptors vs temp files
            if self._logging:
                os.close(self.__timerlat_out)
                os.close(self.__timerlat_err)
            else:
                self.__timerlat_out.close()
                self.__timerlat_err.close()

    def MakeReport(self):
        rep_n = libxml2.newNode('timerlat')
        rep_n.newProp('command_line', ' '.join(self.__cmd))

        max_val = self.__timerlatdata['system'].max

        stoptrace_invoked_n = libxml2.newNode('stoptrace_invoked')
        if self.stcpu != -1 and max_val > int(self.__cfg.stoptrace):
            stoptrace_invoked_n.newProp("invoked", "true")
        else:
            stoptrace_invoked_n.newProp("invoked", "")
        rep_n.addChild(stoptrace_invoked_n)

        if self.stcpu != -1:
            self._log(Log.DEBUG, f'self.__stdata = {self.__stdata}')
            for cpu in self.__stdata:
                # This is  Max timerlat IRQ latency from idle
                # With no other data from that cpu, so don't create a
                # stoptrace_report for this
                if len(self.__stdata[cpu]) == 1:
                    continue
                stoptrace_n = libxml2.newNode('stoptrace_report')
                stoptrace_n.newProp("CPU", str(cpu))
                for k, v in self.__stdata[cpu].items():
                    self._log(Log.DEBUG, f"cpu={cpu}, k={k}, v={v}")
                    if isinstance(v, tuple):
                        latency = str(v[0])
                        percent = str(v[1])
                        cpu_n = stoptrace_n.newTextChild(None, str(k), None)
                        n = cpu_n.newTextChild(None, "latency", latency)
                        n.newProp('unit', 'us')

                        n = cpu_n.newTextChild(None, "latency_percent", percent)
                        n.newProp('unit', '%')
                    elif isinstance(v, list):
                        if k in ("blocking_thread", "softirq_interference", "irq_interference"):
                            for name, latency in v:
                                cpu_n = stoptrace_n.newTextChild(None, k, None)
                                n = cpu_n.newTextChild(None, "name", name)
                                n = cpu_n.newTextChild(None, "latency", latency)
                                n.newProp('unit', 'us')
                    else:
                        if k == "Max_timerlat_IRQ_latency_from_idle":
                            continue
                        cpu_n = stoptrace_n.newTextChild(None, str(k), str(v))
                        cpu_n.newProp('unit', 'us')
                rep_n.addChild(stoptrace_n)

            self._log(Log.DEBUG, f'timerlat: posttrace = \n{self.__posttrace}')
            self._log(Log.DEBUG, 'timerlat: posttrace END')
            for cpu in self.__stdata:
                for k, v in self.__stdata[cpu].items():
                    if isinstance(v, tuple):
                        continue
                    if k == "Max_timerlat_IRQ_latency_from_idle":
                        max_timerlat_n = libxml2.newNode('max_timerlat_report')
                        max_timerlat_n.newProp("CPU", str(cpu))
                        cpu_n = max_timerlat_n.newTextChild(None, k, str(v))
                        cpu_n.newProp('unit', 'us')
                        rep_n.addChild(max_timerlat_n)
            return rep_n

        rep_n.addChild(self.__timerlatdata['system'].MakeReport())
        for thr in self.__cpus:
            if str(thr) not in self.__timerlatdata:
                continue
            rep_n.addChild(self.__timerlatdata[str(thr)].MakeReport())

        return rep_n


def ModuleParameters():
    """ default parameters """
    return {"interval": {"descr": "Base interval or period of threads in microseconds",
                         "default": 100,
                         "metavar": "INTV_US"},
            "priority": {"descr": "Run rtla timerlat with this priority",
                         "default": 95,
                         "metavar": "PRIO" },
            "buckets":  {"descr": "Number of buckets",
                         "default": 3500,
                         "metavar": "NUM" },
            "stoptrace": {"descr": "Stop trace if thread latency higher than USEC",
                          "default": None,
                          "metavar": "USEC" },
            "trace":    {"descr": "File to save trace to",
                         "default": None,
                         "metavar": "FILE" },
            "dma_latency": {"descr": "Set /dev/cpu_dma_latency to USEC (set to None to disable)",
                            "default": "0",
                            "metavar": "USEC" },
           }

def create(params, logger):
    """ Instantiate a Timerlat measurement module object"""
    return Timerlat(params, logger)

if __name__ == '__main__':
    from rteval.rtevalConfig import rtevalConfig

    if os.getuid() != 0:
        print("Must be root to run timerlat!")
        sys.exit(1)

    l = Log()
    l.SetLogVerbosity(Log.INFO|Log.DEBUG|Log.ERR|Log.WARN)

    cfg = rtevalConfig({}, logger=l)
    prms = {}
    modprms = ModuleParameters()
    for c, p in list(modprms.items()):
        prms[c] = p['default']
    cfg.AppendConfig('timerlat', prms)

    cfg_tl = cfg.GetSection('timerlat')
    cfg_tl.cpulist = collapse_cpulist(SysTopology().online_cpus())
    cfg_tl.stoptrace=50

    RUNTIME = 10

    tl = Timerlat(cfg_tl, l)
    tl._WorkloadSetup()
    tl._WorkloadPrepare()
    tl._WorkloadTask()
    time.sleep(RUNTIME)
    tl._WorkloadCleanup()
    rep_n = tl.MakeReport()

    xml = libxml2.newDoc('1.0')
    xml.setRootElement(rep_n)
    xml.saveFormatFileEnc('-', 'UTF-8', 1)
