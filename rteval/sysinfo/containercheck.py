# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
#
#   Copyright 2026 - John Kacur <jkacur@redhat.com>
#
"""Module for detecting if rteval is running in a container"""

import os
import re
import subprocess


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
