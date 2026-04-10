# SPDX-License-Identifier: GPL-2.0-or-later

# Copyright 2024    Anubhav Shelat <ashelat@redhat.com>
""" Object to execute cpupower tool """

import subprocess
import os
import shutil
import sys
from rteval.Log import Log
from rteval.systopology import SysTopology as SysTop
from rteval.cpulist_utils import collapse_cpulist

PATH = '/sys/devices/system/cpu/'

class Cpupower:
    """ class to store data for executing cpupower and restoring idle state configuration """
    def __init__(self, cpulist, idlestate, logger=None):
        if not self.cpupower_present():
            print('cpupower not found')
            sys.exit(1)

        self.__idle_state = int(idlestate)
        self.__states = os.listdir(PATH + 'cpu0/cpuidle/')
        # self.__idle_states is a dict with cpus as keys,
        # and another dict as the value. The value dict
        # has idle states as keys and a boolean as the
        # value indicating if the state is disabled.
        self.__idle_states = {}
        self.__name = "cpupower"
        self.__online_cpus = SysTop().online_cpus()
        self.__cpulist = cpulist
        self.__logger = logger


    def _log(self, logtype, msg):
        """ Common log function for rteval modules """
        if self.__logger:
            self.__logger.log(logtype, f"[{self.__name}] {msg}")


    def enable_idle_state(self):
        """ Use cpupower to set the idle state """
        self.get_idle_states()

        # ensure that idle state is in range of available idle states
        if self.__idle_state > len(self.__states) - 1 or self.__idle_state < 0:
            print(f'Idle state {self.__idle_state} is out of range')
            sys.exit(1)

        # enable all idle states to a certain depth, and disable any deeper idle states
        with open(os.devnull, 'wb') as buffer:
            for state in self.__states:
                s = state.strip("state")
                if int(s) > self.__idle_state:
                    self.run_cpupower(['cpupower', '-c', self.__cpulist,'idle-set', '-d', s], buffer)
                else:
                    self.run_cpupower(['cpupower', '-c', self.__cpulist,'idle-set', '-e', s], buffer)

        self._log(Log.DEBUG, f'Idle state depth {self.__idle_state} enabled on CPUs {self.__cpulist}')


    def run_cpupower(self, args, output_buffer=None):
        """ execute cpupower """
        try:
            subprocess.run(args, check=True, stdout=output_buffer)
        except subprocess.CalledProcessError:
            print('cpupower failed')
            sys.exit(1)


    def get_idle_states(self):
        """ Store the current idle state setting """
        for cpu in self.__online_cpus:
            self.__idle_states[cpu] = {}
            for state in self.__states:
                fp = os.path.join(PATH, 'cpu' + str(cpu) + '/cpuidle/' + state + '/disable')
                self.__idle_states[cpu][state] = self.read_idle_state(fp)


    def restore_idle_states(self):
        """ restore the idle state setting """
        for cpu, states in self.__idle_states.items():
            for state, disabled in states.items():
                fp = os.path.join(PATH, 'cpu' + str(cpu) + '/cpuidle/' + state + '/disable')
                self.write_idle_state(fp, disabled)
        self._log(Log.DEBUG, 'Idle state settings restored')


    def read_idle_state(self, file):
        """ read the disable value for an idle state """
        with open(file, 'r', encoding='utf-8') as f:
            return f.read(1)


    def write_idle_state(self, file, state):
        """ write the disable value for and idle state """
        with open(file, 'w', encoding='utf-8') as f:
            f.write(state)


    def get_idle_info(self):
        """ execute cpupower idle-info """
        self.run_cpupower(['cpupower', 'idle-info'])


    def cpupower_present(self):
        """ check if cpupower is downloaded """
        return shutil.which("cpupower") is not None


if __name__ == '__main__':
    l = Log()
    l.SetLogVerbosity(Log.DEBUG)

    online_cpus = collapse_cpulist(SysTop().online_cpus())
    idlestate = '1'
    info = True

    cpupower = Cpupower(online_cpus, idlestate, logger=l)
    if idlestate:
        cpupower.enable_idle_state()
        cpupower.restore_idle_states()
    print()
    cpupower.get_idle_info()
