# rteval Test Suite

This directory contains the test suite for rteval, using Python's `unittest` framework.

## Quick Start

```bash
# Run non-root unit tests only
make tests
# or
./tests/run_tests.sh

# Run ALL tests including root-required tests
sudo make test-all
# or
sudo python3 -m unittest discover -s tests -p "test_*.py" -v

# Run specific test module
python3 -m unittest tests.test_cpusetmanager -v            # Non-root tests only
sudo python3 -m unittest tests.test_cpusetmanager -v       # All tests including root
```

## Running Tests

### All Non-Root Tests

Run all unit tests that don't require root using the test runner:

```bash
# Using make
make tests
# or
make unit-tests

# Using the test runner directly
./tests/run_tests.sh

# Using Python unittest directly
python3 -m unittest discover -s tests -p "test_*.py" -v
```

### All Tests Including Root-Required

Run the complete test suite including tests that require root permissions:

```bash
# Using make (recommended)
sudo make test-all

# Using Python unittest directly
sudo python3 -m unittest discover -s tests -p "test_*.py" -v
```

### Specific Test File

Run a specific test file:

```bash
# Non-root tests
python3 -m unittest tests.test_cpusetmanager -v
python3 -m unittest tests.test_measurement_module_selection -v
python3 -m unittest tests.test_core_sharing_validation -v

# Root-required tests
sudo python3 -m unittest tests.test_cpusetmanager -v
```

### Specific Test Class

Run a specific test class:

```bash
# Non-root tests
python3 -m unittest tests.test_cpusetmanager.TestCpusetManagerBasic -v

# Root-required tests
sudo python3 -m unittest tests.test_cpusetmanager.TestCpusetManagerHousekeepingPartitions -v
```

### Specific Test Method

Run a single test method:

```bash
# Non-root tests
python3 -m unittest tests.test_cpusetmanager.TestCpusetManagerBasic.test_import_cpusetmanager -v

# Root-required tests
sudo python3 -m unittest tests.test_cpusetmanager.TestCpusetManagerHousekeepingPartitions.test_housekeeping_default_partition_member -v
```

## Test Organization

Tests are organized using Python's `unittest` framework. Each test file contains:
- A test class that inherits from `unittest.TestCase`
- Individual test methods (prefixed with `test_`)
- Setup/teardown methods if needed

### Current Tests

#### Non-Root Tests

- **test_measurement_module_selection.py** - Tests for measurement module selection logic
- **test_core_sharing_validation.py** - Tests for CPU core sharing validation
- **test_cpusetmanager.py::TestCpusetManagerBasic** (2 tests) - Basic CpusetManager functionality
  - test_import_cpusetmanager: Verify CpusetManager can be imported
  - test_cleanup_leftover_cpusets_callable: Verify cleanup method exists

#### Root-Required Tests

- **test_cpusetmanager.py** - CpusetManager functionality tests (requires root)
  - **TestCpusetManagerHousekeepingPartitions** (4 tests) - Housekeeping partition type tests
    - test_housekeeping_default_partition_member: Verify default partition=member
    - test_housekeeping_isolated_flag: Verify --housekeeping-isolated makes partition=isolated
    - test_measurement_always_isolated: Verify measurement is always partition=isolated
    - test_no_housekeeping_cpuset_created_when_empty: Verify no housekeeping cpuset when empty
  - **TestCpusetManagerCLIIntegration** (4 tests) - Command-line integration tests
    - test_housekeeping_isolated_requires_cpusets: Verify validation
    - test_housekeeping_isolated_requires_housekeeping: Verify validation
    - test_housekeeping_isolated_help_text: Verify help text
    - test_housekeeping_help_text_accuracy: Verify corrected help text
  - **TestCpusetManagerCleanup** (2 tests) - Cleanup functionality tests
    - test_cleanup_removes_leftover_cpusets: Verify cleanup removes cpusets
    - test_cleanup_logs_when_no_cpusets: Verify graceful handling when no cpusets
  - **TestCpusetManagerTaskMigration** (3 tests) - Task migration tests
    - test_migrate_root_tasks_to_housekeeping: Verify root task migration
    - test_migrate_measurement_threads: Verify measurement thread migration
    - test_no_migration_when_no_housekeeping: Verify graceful handling

### Test Requirements: Root vs Non-Root

The test suite is split between tests that require root and those that don't:

#### Non-Root Tests

These tests run without root privileges:
- Basic import and functionality checks
- Logic validation tests
- Tests using mock objects or read-only operations

**Benefits:**
- Developers can run basic tests without `sudo`
- Tests run in CI/CD environments without elevated privileges
- Tests are fast and don't affect the running system

#### Root-Required Tests

These tests require root to create/manipulate cgroups:
- Tests that create actual cpusets in /sys/fs/cgroup
- Tests that verify CPU assignment and partition types
- Tests that migrate processes between cpusets
- All tests clean up created cpusets in tearDown()

**Why root is required:**
- Creating cgroups requires write access to /sys/fs/cgroup
- Migrating processes between cgroups requires CAP_SYS_ADMIN
- Testing with actual cgroups ensures real-world behavior

**Run without root:** Tests will be skipped with message "Requires root permissions"

## Writing New Tests

### Test File Structure

Create a new test file following this pattern:

```python
#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright 2026 John Kacur <jkacur@redhat.com>
"""
Description of what this test module tests.
"""

import unittest
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rteval import some_module


class TestSomething(unittest.TestCase):
    """Test cases for something in rteval"""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures (runs once before all tests)"""
        # Common setup for all tests in this class
        pass

    def setUp(self):
        """Set up for each test (runs before each test method)"""
        # Per-test setup
        pass

    def test_something(self):
        """Test that something works correctly"""
        # Your test code here
        self.assertEqual(expected, actual)
        self.assertTrue(condition)
        self.assertIn(item, collection)

    def tearDown(self):
        """Clean up after each test (runs after each test method)"""
        # Per-test cleanup
        pass


if __name__ == '__main__':
    unittest.main()
```

### Naming Conventions

- Test files: `test_*.py` (e.g., `test_cpusetmanager.py`)
- Test classes: `Test*` (e.g., `TestCpusetManager`)
- Test methods: `test_*` (e.g., `test_housekeeping_isolated_flag`)

### Common Assertions

```python
self.assertEqual(a, b)           # a == b
self.assertNotEqual(a, b)        # a != b
self.assertTrue(x)               # bool(x) is True
self.assertFalse(x)              # bool(x) is False
self.assertIn(a, b)              # a in b
self.assertNotIn(a, b)           # a not in b
self.assertIsNone(x)             # x is None
self.assertIsNotNone(x)          # x is not None
self.assertRaises(Exception, fn) # fn() raises Exception
```

### Adding Tests to the Test Runner

After creating a new test file, add it to `tests/run_tests.sh`:

```bash
# Run test_your_feature.py
if [ -f "tests/test_your_feature.py" ]; then
    run_test "tests/test_your_feature.py"
fi
```

## Requirements

### All Tests
- Python 3.6 or later
- rteval source code

### Root-Required Tests
- Root permissions (sudo)
- cgroup v2 support (kernel 4.5+, recommended 5.0+)
- cgroup v2 mounted at /sys/fs/cgroup with cpuset controller enabled

## Expected Output

### Non-Root Tests Only

Running without sudo will run only the non-root tests:

```bash
$ python3 -m unittest discover -s tests -p "test_*.py" -v
test_cleanup_leftover_cpusets_callable (tests.test_cpusetmanager.TestCpusetManagerBasic) ... ok
test_import_cpusetmanager (tests.test_cpusetmanager.TestCpusetManagerBasic) ... ok
... (root-required tests skipped: "Requires root permissions")

----------------------------------------------------------------------
Ran 2 tests in 0.XXXs

OK (skipped=13)
```

### All Tests Including Root-Required

Running with sudo will run all tests:

```bash
$ sudo python3 -m unittest discover -s tests -p "test_*.py" -v
... (2 non-root tests as above)
test_housekeeping_default_partition_member (tests.test_cpusetmanager.TestCpusetManagerHousekeepingPartitions) ... ok
test_housekeeping_isolated_flag (tests.test_cpusetmanager.TestCpusetManagerHousekeepingPartitions) ... ok
... (all 13 root-required cpusetmanager tests)

----------------------------------------------------------------------
Ran 15 tests in X.XXXs

OK
```

## Continuous Integration

### Non-Root Tests (Recommended for CI)

The non-root tests are designed to run in CI/CD environments:
- Run without root privileges
- No special system configuration required
- Exit code 0 on success, non-zero on failure
- Fast execution

```bash
# CI-friendly test command
make tests
# or
python3 -m unittest discover -s tests -p "test_*.py" -v
```

### Root-Required Tests (Optional for CI)

The root-required tests can run in CI with special setup:
- Requires root access or privileged containers
- Requires cgroup v2 support
- May need dedicated test runners with appropriate permissions

```bash
# Full test suite (requires root)
sudo make test-all
# or
sudo python3 -m unittest discover -s tests -p "test_*.py" -v
```
