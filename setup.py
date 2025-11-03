#!/usr/bin/python3
# SPDX-License-Identifier: GPL-2.0-or-later
""" install rteval """
import sysconfig
from os.path import relpath
import os
import shutil
import gzip
from setuptools import setup


# Get PYTHONLIB with no prefix so --prefix installs work.
SCHEME = 'rpm_prefix'
if SCHEME not in sysconfig.get_scheme_names():
    SCHEME = 'posix_prefix'
PYTHONLIB = relpath(sysconfig.get_path('platlib', SCHEME), '/usr')

# Tiny hack to make rteval-cmd become a rteval when building/installing the package
try:
    os.mkdir('dist', 0o755)
    distcreated = True
except OSError as e:
    if e.errno == 17:
        # If it already exists, ignore this error
        distcreated = False
    else:
        raise e
shutil.copy('rteval-cmd','dist/rteval')

# Hack to avoid importing libxml2 and a lot of other stuff
# when getting the rteval version.  These are modules which
# might not be available on the build box.
shutil.copy('rteval/version.py','dist/__init__.py')
from dist import RTEVAL_VERSION

# Compress the man page, so distutil will only care for the compressed file
mangz = gzip.GzipFile('dist/rteval.8.gz', 'w', 9)
with open('doc/rteval.8', 'rb') as man:
    mangz.writelines(man)
mangz.close()


# Do the setup stuff
setup(name="rteval",
      version = RTEVAL_VERSION,
      description = "Evaluate system performance for Realtime",
      author = "Clark Williams, David Sommerseth, John Kacur",
      author_email = "williams@redhat.com, davids@redhat.com, jkacur@redhat.com",
      maintainer = "John Kacur",
      maintainer_email = "jkacur@redhat.com",
      url = "https://git.kernel.org/pub/scm/utils/rteval/rteval.git",
      license = "GPLv2",
      long_description =
"""\
The rteval script is used to judge the behavior of a hardware
platform while running a Realtime Linux kernel under a moderate
to heavy load.

Provides control logic for starting a system load and then running a
response time measurement utility (cyclictest) for a specified amount
of time. When the run is finished, the sample data from cyclictest is
analyzed for standard statistical measurements (i.e mode, median, range,
mean, variance and standard deviation) and a report is generated.
""",
      packages = ["rteval",
                  "rteval.modules",
                  "rteval.modules.loads",
                  "rteval.modules.measurement",
                  "rteval.sysinfo"],
      package_dir = { "rteval": "rteval",
                      "rteval.modules": "rteval/modules",
                      "rteval.modules.loads": "rteval/modules/loads",
                      "rteval.modules.measurement": "rteval/modules/measurement",
                      "rteval.sysinfo": "rteval/sysinfo"
                      },
      data_files = [("share/rteval", ["rteval/rteval_dmi.xsl",
                                      "rteval/rteval_histogram_raw.xsl",
                                      "rteval/rteval_text.xsl"]),
                    ("/etc", ["rteval.conf"]),
                    ("share/man/man8", ["dist/rteval.8.gz"])
                    ],
      scripts = ["dist/rteval"]
      )


# Clean-up from our little hack
os.unlink('dist/rteval')
os.unlink('dist/rteval.8.gz')
os.unlink('dist/__init__.py')

if distcreated:
    try:
        os.rmdir('dist')
    except OSError:
        # Ignore any errors
        pass
