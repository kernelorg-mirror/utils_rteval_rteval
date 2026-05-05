# Cpuset Integration Tests

Integration tests for rteval's cpuset functionality, which allows fine-grained CPU isolation for measurement and load workloads using cgroup v2 cpusets.

## Purpose

These tests verify that rteval's cpuset integration works correctly across various scenarios, including:
- Creating and cleaning up cpusets
- CPU assignment and partition configuration
- Housekeeping cpuset functionality
- Interaction with kernel isolcpus boot parameter
- Proper cleanup on interruption

## Test Files

- **test-cpusets.sh** - Comprehensive cpuset integration test suite with 10 test scenarios

## Prerequisites

**System Requirements:**
- Root privileges (cpuset operations require root)
- cgroup v2 mounted
- cpuset controller available
- Minimum 4 CPUs recommended for meaningful tests

**Optional:**
- Kernel boot parameter `isolcpus=<cpulist>` for testing isolcpus-specific scenarios
  - Without isolcpus: Tests that don't require it will run; isolcpus-specific tests will be skipped
  - With isolcpus: All 10 tests will run

## Running the Tests

### Via Makefile (Recommended)

```bash
sudo make cpuset-tests
```

This runs the complete cpuset test suite and generates a timestamped log file.

### Standalone Script

```bash
sudo ./tests/cpusets/test-cpusets.sh
```

## Test Scenarios

The test suite includes 10 comprehensive scenarios:

### Basic Scenarios (No isolcpus required)

1. **Prerequisites Check**
   - Verifies root privileges, cgroup v2, cpuset controller
   - Displays system CPU configuration

2. **Same CPUs - No Housekeeping**
   - Measurement and loads use same CPUs
   - Only measurement cpuset created (loads use taskset)
   - Partition type: `member`

3. **Different CPUs - No Housekeeping**
   - Measurement and loads use different CPUs
   - Only measurement cpuset created
   - Loads still use taskset (not isolated from system)

4. **With Housekeeping - Different CPUs**
   - Tests dual cpuset scenario
   - Creates both housekeeping and measurement cpusets
   - System tasks migrated to housekeeping cpuset
   - Loads use taskset on separate CPUs

5. **Housekeeping Without isolcpus**
   - Demonstrates new capability: housekeeping works with --cpusets flag
   - Does not require isolcpus boot parameter
   - Validates cpuset-based isolation vs. kernel isolcpus

6. **Backward Compatibility**
   - Runs rteval WITHOUT --cpusets flag
   - Verifies no cpusets are created
   - Ensures traditional behavior preserved

7. **Cleanup on Interrupt**
   - Tests signal handling (SIGINT/Ctrl+C)
   - Verifies cpusets are properly cleaned up on interruption
   - Critical for preventing leaked cpusets

### Advanced Scenarios (Require isolcpus boot parameter)

8. **Measurement Run on isolcpus**
   - Tests --measurement-run-on-isolcpus flag
   - Automatically uses isolated CPUs for measurement
   - Skipped if no isolcpus configured

9. **Housekeeping Requires isolcpus Without --cpusets**
   - Tests backward-compatible validation
   - Housekeeping CPUs must be in isolcpus WITHOUT --cpusets flag
   - Verifies proper error message
   - Skipped if no isolcpus configured

10. **Combining isolcpus and --cpusets**
    - Tests double-layer isolation strategy
    - Kernel-level (isolcpus) + userspace (cpusets) isolation
    - Measurement runs on isolated CPUs within cpuset
    - Skipped if no isolcpus configured

## Test Duration

Tests use a short duration (`10s`) for quick validation. Each test scenario includes:
- Pre-test cleanup
- cpuset creation verification during execution
- Post-test cleanup verification

Total test suite runtime: ~2-3 minutes without isolcpus, ~5-6 minutes with isolcpus.

## Expected Results

All tests should pass with proper cpuset creation, CPU assignment, and cleanup:

```
Total tests run: 10
Passed: 10
Failed: 0
✅ ALL TESTS PASSED
```

On systems without isolcpus, tests 8-10 will be skipped:
```
Total tests run: 10
Passed: 10 (3 skipped)
Failed: 0
```

## Log Files

Each test run creates a timestamped log file:
```
test-cpusets-YYYYMMDD-HHMMSS.log
```

The log contains full rteval output for debugging test failures.

## Troubleshooting

### Common Issues

**"ERROR: This script must be run as root"**
- Solution: Run with `sudo`

**"ERROR: cgroup v2 not mounted"**
- Check: `mount | grep cgroup2`
- Solution: Ensure cgroup v2 is enabled in kernel config

**"ERROR: cpuset controller not available"**
- Check: `cat /sys/fs/cgroup/cgroup.controllers`
- Solution: Ensure cpuset controller is enabled

**"Cpusets not cleaned up"**
- Indicates rteval cleanup code issue
- Manual cleanup: See test script's `cleanup_cpusets()` function
- Or use: `rteval-cmd --cleanup-cpusets`

### Verifying Cpusets During Test Execution

While a test is running, you can inspect cpusets with:

```bash
# Show all rteval cpusets (if show-cpusets is in your PATH)
show-cpusets

# Or manually inspect:
ls -la /sys/fs/cgroup/rteval_*/
cat /sys/fs/cgroup/rteval_measurement/cpuset.cpus
cat /sys/fs/cgroup/rteval_housekeeping/cpuset.cpus
```

## Implementation Details

The cpuset implementation follows the "isolcpus philosophy":
- Cpusets provide **additional** isolation capability
- With `--cpusets` flag: housekeeping works without requiring isolcpus
- Without `--cpusets` flag: traditional behavior (housekeeping requires isolcpus)
- Measurement cpuset uses `member` partition type
- Housekeeping cpuset moves all system tasks out of measurement CPUs
- Loads always use taskset (not in cpuset) to avoid interfering with cgroup memory controller

## Related Documentation

- Main rteval documentation: `doc/rteval.8`
- Cpuset implementation: `rteval/cpuset.py`
- Local development notes: `local/README-CPUSETS.md` (if exists)

## When to Run These Tests

- **Before releases** - Verify cpuset functionality across scenarios
- **After modifying cpuset code** - Ensure changes don't break existing behavior
- **After kernel updates** - Verify cgroup v2 and cpuset controller compatibility
- **When investigating cpuset issues** - Reproduce specific scenarios
- **On new hardware** - Validate cpuset behavior on different CPU topologies
