# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
#
#   Copyright 2009 - 2013   Clark Williams <williams@redhat.com>
#   Copyright 2009 - 2013   David Sommerseth <davids@redhat.com>
#   Copyright 2012 - 2013   Raphaël Beamonte <raphael.beamonte@gmail.com>
#

import sys
import subprocess
import os
import glob
import fnmatch
import libxml2
from rteval.sysinfo.tools import getcmdpath
from rteval.Log import Log


class SystemServices:
    def __init__(self, logger=None):
        self.__logger = logger
        self.__init = "unknown"

    def __log(self, logtype, msg):
        if self.__logger:
            self.__logger.log(logtype, msg)


    def __get_services_sysvinit(self):
        reject = ('functions', 'halt', 'killall', 'single', 'linuxconf', 'kudzu',
                  'skeleton', 'README', '*.dpkg-dist', '*.dpkg-old', 'rc', 'rcS',
                  'single', 'reboot', 'bootclean.sh')
        for sdir in ('/etc/init.d', '/etc/rc.d/init.d'):
            if os.path.isdir(sdir):
                servicesdir = sdir
                break
        if not servicesdir:
            raise RuntimeError("No services dir (init.d) found on your system")
        self.__log(Log.DEBUG, f"Services located in {servicesdir}, going through each service file to check status")
        ret_services = {}
        for service in glob.glob(os.path.join(servicesdir, '*')):
            servicename = os.path.basename(service)
            if not [1 for p in reject if fnmatch.fnmatch(servicename, p)] \
                    and os.access(service, os.X_OK):
                cmd = fr'{getcmdpath("grep")} -qs "\(^\|\W\)status)" {service}'
                c = subprocess.Popen(cmd, shell=True, encoding='utf-8')
                c.wait()
                if c.returncode == 0:
                    cmd = ['env', '-i', f'LANG="{os.environ["LANG"]}"', f'PATH="{os.environ["PATH"]}"', f'TERM="{os.environ["TERM"]}"', service, 'status']
                    c = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')
                    c.wait()
                    if c.returncode == 0 and (c.stdout.read() or c.stderr.read()):
                        ret_services[servicename] = 'running'
                    else:
                        ret_services[servicename] = 'not running'
                else:
                    ret_services[servicename] = 'unknown'
        return ret_services


    def __get_services_systemd(self):
        ret_services = {}
        cmd = f'{getcmdpath("systemctl")} list-unit-files -t service --no-legend'
        self.__log(Log.DEBUG, f"cmd: {cmd}")
        c = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')
        for p in c.stdout:
            # p are lines like b'servicename.service status'
            v = p.strip().split()
            ret_services[v[0].split('.')[0]] = v[1]
        return ret_services


    def services_get(self):
        cmd = [getcmdpath('ps'), '-ocomm=', '1']
        c = subprocess.Popen(cmd, stdout=subprocess.PIPE, encoding='utf-8')
        self.__init = c.stdout.read().strip()
        if self.__init == 'systemd':
            self.__log(Log.DEBUG, "Using systemd to get services status")
            return self.__get_services_systemd()
        if self.__init == 'init':
            self.__init = 'sysvinit'
            self.__log(Log.DEBUG, "Using sysvinit to get services status")
            return self.__get_services_sysvinit()
        self.__init = 'container'
        self.__log(Log.DEBUG, "Running inside container")
        return {}


    def MakeReport(self):
        srvs = self.services_get()

        rep_n = libxml2.newNode("Services")
        rep_n.newProp("init", self.__init)

        for service, val in srvs.items():
            srv_n = libxml2.newNode("Service")
            srv_n.newProp("state", val)
            srv_n.addContent(service)
            rep_n.addChild(srv_n)

        return rep_n

def unit_test(rootdir):
    from pprint import pprint

    try:
        syssrv = SystemServices()
        pprint(syssrv.services_get())

        srv_xml = syssrv.MakeReport()
        xml_d = libxml2.newDoc("1.0")
        xml_d.setRootElement(srv_xml)
        xml_d.saveFormatFileEnc("-", "UTF-8", 1)

        return 0
    except Exception as err:
        print(f"** EXCEPTION: {str(err)}")
        return 1


if __name__ == '__main__':
    sys.exit(unit_test(None))
