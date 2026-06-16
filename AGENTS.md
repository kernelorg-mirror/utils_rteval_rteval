SPDX-License-Identifier: GPL-2.0-or-later

Copyright 2026 John Kacur <jkacur@redhat.com>

# AGENTS.md - AI Coding Assistant Guide for rteval

This document provides guidance for AI coding assistants working with the rteval codebase.

## Project Overview

**rteval** is a Python program for evaluating the performance of realtime Linux kernels on hardware platforms. It measures scheduling and timer latency under system load to assess platform suitability for real-time workloads.

- **License**: GPL-2.0-or-later
- **Language**: Python 3.8+
- **Primary Maintainer**: John Kacur <jkacur@redhat.com>
- **Original Authors**: Clark Williams, David Sommerseth
- **Repository**: https://git.kernel.org/pub/scm/utils/rteval/rteval.git

## Architecture

### Directory Structure

```
rteval/
├── rteval-cmd                     # Main entry point (executable)
├── rteval/                        # Core Python package
│   ├── __init__.py               # Main RtEval class and orchestration
│   ├── version.py                # Version information
│   ├── rtevalConfig.py           # Configuration handling
│   ├── rtevalReport.py           # Report generation
│   ├── xmlout.py                 # XML output formatting
│   ├── Log.py                    # Logging utilities
│   ├── systopology.py            # System topology and CPU management
│   ├── cpuset.py                 # CPU set management
│   ├── cpusetmanager.py          # CPU set manager
│   ├── cpulist_utils.py          # CPU list parsing utilities
│   ├── cpupower.py               # CPU power state management
│   ├── rteval_text.xsl           # XSLT template for text reports
│   ├── rteval_dmi.xsl            # XSLT template for DMI information
│   ├── rteval_histogram_raw.xsl  # XSLT template for raw histogram data
│   ├── modules/                  # Plugin modules
│   │   ├── __init__.py          # Module loading framework
│   │   ├── loads/               # Load generators
│   │   │   ├── kcompile.py     # Kernel compilation load
│   │   │   ├── hackbench.py    # Hackbench scheduler stress
│   │   │   └── stressng.py     # stress-ng workload
│   │   └── measurement/         # Measurement tools
│   │       ├── cyclictest.py   # cyclictest latency measurement
│   │       ├── timerlat.py     # timerlat latency measurement
│   │       └── sysstat.py      # System statistics collection
│   └── sysinfo/                 # System information collection
│       ├── __init__.py          # Main system info collector
│       ├── cmdline.py           # Command line parsing
│       ├── cputopology.py       # CPU topology detection
│       ├── coresiblings.py      # CPU core sibling relationships
│       ├── containercheck.py    # Container detection
│       ├── dmi.py               # DMI/SMBIOS information
│       ├── kernel.py            # Kernel information
│       ├── memory.py            # Memory information
│       ├── osinfo.py            # OS information
│       ├── newnet.py            # Network information
│       ├── services.py          # System services information
│       ├── tools.py             # System tools utilities
│       └── tuned.py             # Tuned profile information
├── doc/                         # Documentation
│   ├── rteval.8                 # Man page
│   └── rteval-legacy.txt        # Legacy documentation
├── loadsource/                  # Source tarballs for loads
│   ├── linux-6.17.7.tar.xz     # Kernel source for kcompile
│   └── dbench-4.0.tar.gz        # dbench source
├── tests/                       # Test suite
│   ├── e2e/                     # End-to-end tests (bash/TAP)
│   └── unittest-legacy.py       # Legacy unit test runner
├── setup.py                     # Legacy setuptools configuration
├── pyproject.toml               # Modern Python project metadata
├── Makefile                     # Build and test targets
├── rteval.conf                  # Default configuration
├── README                       # Main documentation
├── README-tests                 # Testing documentation
├── README-Dockerfile            # Docker container documentation
├── Dockerfile                   # Container build definition
├── COPYING                      # License file (GPL-2.0-or-later)
└── MANIFEST.in                  # Python packaging manifest
```

### Core Components

1. **Main Program** (`rteval-cmd`)
   - Command-line interface and orchestration
   - Configuration parsing and validation
   - Report generation coordinator

2. **Measurement Modules** (`rteval/modules/measurement/`)
   - `cyclictest.py` - Legacy latency measurement using rt-tests
   - `timerlat.py` - Modern latency measurement using rtla (recommended)
   - `sysstat.py` - System statistics collection (sar, iostat, mpstat)

3. **Load Modules** (`rteval/modules/loads/`)
   - `kcompile.py` - Kernel compilation load
   - `hackbench.py` - Scheduler stress test
   - `stressng.py` - CPU/memory stress testing

4. **System Information** (`rteval/sysinfo/`)
   - DMI table reading
   - CPU topology detection
   - Kernel configuration
   - Network interface enumeration
   - Service status
   - Container detection (`containercheck.py`)

5. **Configuration** (`rteval/rtevalConfig.py`)
   - INI-based configuration file parsing
   - Command-line option integration

6. **Reporting** (`rteval/rtevalReport.py`, `rteval/xmlout.py`)
   - XML report generation with raw data
   - XSLT transformation for text/HTML output
   - Statistical analysis (min/max, stddev, histograms)

7. **CPU Management**
   - `rteval/cpulist_utils.py` - CPU list parsing and manipulation
   - `rteval/systopology.py` - NUMA and CPU topology
   - `rteval/cpuset.py` - Cpuset manipulation
   - `rteval/cpupower.py` - CPU frequency management

## Development Guidelines

### Code Style

- Follow PEP 8 Python style guidelines
- Use 4-space indentation (no tabs)
- Maximum line length: 100 characters (flexible for readability)
- Use docstrings for modules, classes, and public methods
- SPDX license identifier at top of each file: `# SPDX-License-Identifier: GPL-2.0-or-later`

### Module Structure

Measurement and load modules follow a plugin architecture:

```python
class ModuleName(rtevalModulePrototype):
    def __init__(self, config, logger):
        rtevalModulePrototype.__init__(self, 'modulename', config, logger)
        # ... initialization

    def _WorkloadSetup(self):
        # Setup before execution

    def _WorkloadBuild(self):
        # Build/prepare workload

    def _WorkloadPrepare(self):
        # Final preparation before run

    def _WorkloadTask(self):
        # Main workload execution

    def WorkloadAlive(self):
        # Check if workload is running

    def _WorkloadCleanup(self):
        # Cleanup after execution

    def MakeReport(self):
        # Generate XML report node
```

### Error Handling

- Use exceptions for error conditions
- Log errors using `self._log(Log.DEBUG|INFO|WARN|ERR, message)`
- Provide informative error messages
- Clean up resources in `_WorkloadCleanup()` even on failure

### Testing

Run tests before submitting changes:

```bash
make test          # Unit tests
make e2e-tests     # End-to-end tests (requires root)
```

End-to-end tests are located in `tests/` and use Perl's Test::Harness.

### Container Detection

rteval now detects container environments and warns users. Check `rteval/sysinfo/containercheck.py`:

- Detects Docker, Podman, LXC, systemd-nspawn, Kubernetes
- Warns that latency measurements may be unreliable in containers
- Real-time measurements should be done on bare metal or proper RT virtualization

## Common Tasks

### Adding a New Load Module

1. Create `rteval/modules/loads/newload.py`
2. Inherit from `rtevalModulePrototype`
3. Implement required methods (`_WorkloadSetup`, `_WorkloadTask`, etc.)
4. Register in `rteval/modules/loads/__init__.py`
5. Add documentation to module docstring
6. Update README if adding new dependencies

### Adding a New Measurement Module

1. Create `rteval/modules/measurement/newmeasure.py`
2. Inherit from `rtevalModulePrototype`
3. Implement measurement-specific methods
4. Parse output and generate statistics
5. Implement `MakeReport()` to create XML report node with:
   - Raw data
   - Statistical summary (min, max, mean, stddev)
   - Histogram if applicable

### Modifying Report Output

- XML structure: `rteval/rtevalReport.py`, `rteval/xmlout.py`
- XSLT templates: `rteval/rteval_text.xsl`, `rteval/rteval_dmi.xsl`, etc.
- Statistical calculations happen in measurement modules
- Report assembly happens in `RtEval.Measure()` and `rtevalReport.py`

### Working with CPU Lists

Use `rteval/cpulist_utils.py` for CPU list manipulation:

```python
from rteval.cpulist_utils import CpuList, collapse_cpulist

cpulist = CpuList("0-3,8-11")
cpulist.append(16)
result = collapse_cpulist(cpulist)  # "0-3,8-11,16"
```

### Handling Truncated Output

Recent changes improved handling of truncated histogram output from cyclictest and timerlat. See commits:
- `6b38190d2d66` - timerlat truncation handling
- `3abdf7bf7b24` - cyclictest truncation handling

When parsing external tool output, always handle incomplete/truncated data gracefully.

## Key Files

- `rteval-cmd` - Main entry point
- `rteval/__init__.py` - Core RtEval class
- `rteval/rtevalConfig.py` - Configuration management
- `rteval/version.py` - Version information
- `rteval.conf` - Default configuration file
- `Makefile` - Build and installation
- `setup.py` / `pyproject.toml` - Python packaging

## Dependencies

**Required**:
- Python >= 3.8
- python3-lxml - XML processing
- python3-libxml2 - XML processing
- sysstat - System performance tools
- numactl, dmidecode, procps-ng

**Measurement tools** (at least one):
- rt-tests (for cyclictest)
- rtla (for timerlat, requires kernel 5.15+ with CONFIG_OSNOISE_TRACER)

**Load generation**:
- gcc, make, binutils - For kcompile
- stress-ng (optional)
- hackbench (usually in rt-tests)

## Build and Installation

### Build Commands

```bash
# Run a quick test (10 seconds by default)
make runit

# Run with custom duration (in seconds)
make runit D=60

# Run unit tests
make test
# or
make unittest

# Run end-to-end tests (requires root, needs load source tarballs)
sudo make e2e-tests

# Install locally
sudo make install

# Create source tarball
make tarfile

# Generate ctags
make tags

# Test loads only (no measurements)
make load

# Run with SOS report generation
make sysreport

# RPM packaging
make help  # See available targets
```

### Installation

```bash
# Install with pip (development mode)
pip install -e .

# Install with setup.py
python3 setup.py install

# Install via Makefile (preferred)
sudo make install
```

## Testing

### Four Types of Tests

1. **Unit Tests** (`tests/` directory)
   - Python unittest modules
   - Run with: `make test` or `./run_tests.sh`
   - Do not require root

2. **End-to-End Tests** (`tests/e2e/`)
   - Bash scripts producing TAP output
   - Run with: `sudo make e2e-tests`
   - Requires root and load source tarballs

3. **Manual Test Targets**
   - `make runit`: Quick test run (both loads and measurements)
   - `make load`: Test loads only
   - `make sysreport`: Run with SOS report generation

4. **Legacy Unit Tests**
   - Embedded in source files
   - Run with: `sudo python3 tests/unittest-legacy.py`

### Important Testing Notes

- **Most tests require root privileges** (rteval needs root to set RT priorities and access hardware)
- Load source tarballs must be present in `loadsource/` for full functionality
- Current kernel source: `linux-6.17.7.tar.xz`

## Debugging

Enable debug logging:

```bash
rteval -d 3600 --debug
```

Log levels defined in `rteval/Log.py`:
- `Log.DEBUG` - Verbose debugging
- `Log.INFO` - Informational messages
- `Log.WARN` - Warnings
- `Log.ERR` - Errors

## Configuration

Configuration hierarchy (highest priority first):
1. Command-line arguments
2. User config file (`~/.rteval.conf`)
3. System config file (`/etc/rteval.conf`)
4. Default config (`rteval/rteval.conf`)

Configuration uses Python's `configparser` module with INI format.

## Real-time Considerations

- rteval must run as root to set RT priorities
- Measurement threads run with SCHED_FIFO priority
- Load modules should NOT interfere with measurement threads
- CPU isolation can be specified via `--isolcpus` or config file
- Housekeeping CPUs separate load from measurement

## Output Files

Default output directory: `/usr/share/rteval/`

Generated files:
- `summary.xml` - Full XML report with raw data
- `summary.xml.tar.bz2` - Compressed archive of results
- Text summary (via XSLT transformation)

## Related Projects

- **rt-tests**: https://git.kernel.org/pub/scm/utils/rt-tests/rt-tests.git
  - Includes cyclictest, hackbench, and other RT test tools
- **rtla** (rtla/osnoise): Part of Linux kernel tools
  - Modern latency measurement using kernel tracing

## Support and Contact

- Mailing list: linux-rt-users@vger.kernel.org
- Maintainer: John Kacur <jkacur@redhat.com>
- Bug reports: Via mailing list or kernel.org infrastructure

## Git Workflow

- **Main branch**: `main`
- **Repository**: https://git.kernel.org/pub/scm/utils/rteval/rteval.git
- **Patch submission**: Use standard git format-patch/send-email for contributions
- **Mailing list**: Send patches to linux-rt-users@vger.kernel.org

### Development Workflow

1. Make changes to code
2. Run unit tests: `make test`
3. Test manually: `sudo make runit D=10` (quick 10-second run)
4. Run full e2e tests: `sudo make e2e-tests` (when available)
5. Update documentation if needed
6. Submit patches to mailing list or create pull request

## Common Gotchas

1. **Root Required**: rteval requires root privileges to run properly (RT scheduling, hardware access)
2. **Load Sources**: Kernel compilation requires `loadsource/linux-*.tar.xz` to be present
3. **CPU Isolation**: The tool validates CPU isolation and warns about housekeeping/measurement CPU conflicts
4. **Core Sharing**: Recent work added validation for hyperthreading/SMT core sharing warnings
5. **Module Loading**: Modules are discovered dynamically; add `module` in config to enable
6. **XML Reports**: Reports use XSLT for transformation; edit .xsl files carefully
7. **Version Management**: Version is in `rteval/version.py` and must be updated for releases
8. **Container Detection**: rteval detects container environments (Docker, Podman, LXC, etc.) and warns that latency measurements may be unreliable

## Additional Notes for AI Assistants

1. **Python Version**: Target Python 3.8+ for compatibility with RHEL 8/9
2. **XML Generation**: Use `lxml.etree` for XML, not stdlib xml module
3. **Subprocess Handling**: Use `subprocess.Popen()` for external commands
4. **Platform Support**: Code should work on x86_64, aarch64, ppc64le, s390x
5. **Error Recovery**: Measurement failures should not crash entire program
6. **Signal Handling**: rteval handles SIGINT/SIGTERM for graceful shutdown
7. **Thread Safety**: Measurement modules run in separate threads
8. **Resource Cleanup**: Always clean up temp files, processes, and system state changes

## Recent Changes

Check `git log` for recent commits. Notable recent development focus:

**Container Detection:**
- Added container detection and warnings (commits 329dbe89, 70171b29)
- Detects Docker, Podman, LXC, systemd-nspawn, Kubernetes
- Warns users that latency measurements may be unreliable in containers

**Core Sharing Validation:**
- Detection and warning when isolated CPUs share cores with non-isolated CPUs
- Enhanced CPU sibling detection and topology mapping
- New `--warn-non-isolated-core-sharing` option
- XML report enhancements for core sharing warnings

**Measurement Improvements:**
- Improved truncated histogram handling for timerlat (commit 6b38190d)
- Improved truncated histogram handling for cyclictest (commit 3abdf7bf)
- Better error handling for incomplete measurement output

---

**Last Updated**: 2026-06-16
**Document Version**: 1.0
