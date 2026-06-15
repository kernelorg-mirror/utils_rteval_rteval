# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
#
#   Copyright 2026 - John Kacur <jkacur@redhat.com>
#
"""Module for detecting if rteval is running in a container"""

import os
import re
import subprocess
import libxml2
from rteval.Log import Log


def is_container():
    """
    Detect if running in a container (comprehensive check).

    Returns:
        bool: True if running in a container, False otherwise
    """

    # Check 1: .dockerenv file
    if os.path.exists('/.dockerenv'):
        return True

    # Check 2: /proc/1/cgroup
    try:
        with open('/proc/1/cgroup', 'r') as f:
            if re.search(r'docker|lxc|kubepods|libpod', f.read()):
                return True
    except (FileNotFoundError, PermissionError):
        pass

    # Check 3: Environment variables
    if os.environ.get('container'):
        return True

    # Check 4: Kubernetes
    if os.environ.get('KUBERNETES_SERVICE_HOST'):
        return True

    # Check 5: systemd-detect-virt (if available)
    try:
        result = subprocess.run(
            ['systemd-detect-virt', '-c'],
            capture_output=True,
            text=True,
            timeout=1
        )
        if result.returncode == 0:
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return False


class ContainerInfo:
    """Class for collecting container information for XML report"""
    def __init__(self, logger=None):
        self.__logger = logger

    def __log(self, logtype, msg):
        if self.__logger:
            self.__logger.log(logtype, msg)

    def MakeReport(self):
        """Generate XML report node for container status"""
        rep_n = libxml2.newNode("ContainerInfo")
        container_n = libxml2.newNode("container")

        in_container = is_container()
        container_n.addContent("true" if in_container else "false")
        self.__log(Log.DEBUG, f"Container detection: {in_container}")
        rep_n.addChild(container_n)

        return rep_n


def unit_test(rootdir):
    """Simple test of container detection"""
    result = is_container()
    print(f"Container detection result: {result}")
    if result:
        print("Running in a container")
    else:
        print("Not running in a container")


if __name__ == '__main__':
    unit_test(None)
