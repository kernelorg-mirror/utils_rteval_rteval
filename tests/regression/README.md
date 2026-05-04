# Regression Tests for Measurement Module Error Handling

Regression tests for verifying error handling fixes in the timerlat and cyclictest measurement modules (RHEL-140898).

## Purpose

These tests verify that rteval handles partial/malformed output from measurement modules gracefully. Both timerlat and cyclictest can crash or produce incomplete data, which previously caused rteval to hang indefinitely. These tests ensure the error handling prevents hangs, crashes, and infinite loops.

## Test Files

### Timerlat Testing
- **mock-rtla-timerlat-partial-output.py** - Mock rtla that simulates partial/malformed output
- **test-timerlat-error-handling.sh** - Test harness for timerlat

### Cyclictest Testing
- **mock-cyclictest-partial-output.py** - Mock cyclictest that simulates partial/malformed output
- **test-cyclictest-error-handling.sh** - Test harness for cyclictest

## Test Scenarios

Both test suites simulate four different failure modes:

1. **truncated_mid_line** - Output cuts off mid-line (simulates segfault)
   - Tests `IndexError` handling in bucket parsing
   - Mock exits with code 139 (segfault)

2. **missing_columns** - Missing CPU columns in some lines
   - Tests `IndexError` when accessing out-of-bounds array indices
   - Mock exits with code 1

3. **invalid_numbers** - Non-numeric values in histogram data
   - Tests `ValueError` handling when converting strings to int
   - Mock exits with code 1

4. **mixed_corruption** - Random combination of all issues
   - Comprehensive test of error handling
   - Mock exits with code 0 (to test handling of bad data with "success" exit)

## Running the Tests

**Requirements:**
- Root privileges (rteval requires root)
- Tests run from repository root directory

### Via Makefile (Recommended)

Run both test suites:
```bash
sudo make regression-tests
```

This runs all timerlat and cyclictest error handling tests automatically.

### Standalone Scripts

#### Run All Timerlat Tests
```bash
sudo ./tests/regression/test-timerlat-error-handling.sh
```

#### Run All Cyclictest Tests
```bash
sudo ./tests/regression/test-cyclictest-error-handling.sh
```

#### Run Specific Scenario
```bash
sudo ./tests/regression/test-timerlat-error-handling.sh truncated_mid_line
sudo ./tests/regression/test-cyclictest-error-handling.sh missing_columns
```

Available scenarios: `truncated_mid_line`, `missing_columns`, `invalid_numbers`, `mixed_corruption`

#### Run Both Test Suites
```bash
sudo ./tests/regression/test-timerlat-error-handling.sh && \
sudo ./tests/regression/test-cyclictest-error-handling.sh
```

## Expected Results

With the fixes applied, rteval should:

### ✓ Handle Partial Output Gracefully
- Log warnings about malformed data
- Continue processing what data is available
- **NOT crash** with unhandled exceptions

### ✓ Always Call _setFinished()
- Complete cleanup even if parsing fails
- **NOT hang** in WaitForCompletion

### ✓ Limit SIGINT Attempts
- Send maximum of 5 SIGINT signals
- Force SIGKILL if process doesn't respond
- **NOT loop infinitely**

### ✓ Log Non-Zero Exit Codes
- Detect and log when measurement tool exits abnormally
- Provide useful debugging information

## What to Look For in Logs

Successful handling should show:

```
[WARN] Error parsing timerlat bucket data for core X: ...
[WARN] Error parsing cyclictest bucket data for core X: ...
[DEBUG] Sending SIGINT (attempt 1/5)
[DEBUG] Sending SIGINT (attempt 2/5)
...
[WARN] timerlat exited with non-zero status: 139
[WARN] cyclictest exited with non-zero status: 139
```

Failures (old code) would show:
- Unhandled exceptions causing rteval to crash
- Infinite loop of SIGINT attempts
- Process hanging indefinitely

## When to Run These Tests

- **Before releases** - Verify error handling still works
- **After modifying measurement modules** - Ensure changes don't break error handling
- **After kernel updates** - Verify measurement tools still behave correctly
- **When investigating hang reports** - Reproduce error conditions

## Implementation Details

Both measurement modules received identical fixes:

1. **SIGINT retry limit** - Maximum 5 attempts, then SIGKILL
2. **try/finally for _setFinished()** - Ensures cleanup always happens
3. **Exception handling in bucket parsing** - Catches IndexError and ValueError
4. **Exception handling in helper methods** - Additional protection for special parsing
5. **Non-zero exit code logging** - Helps with debugging

See commit messages for detailed implementation:
- f5a1164b8ee4 - rteval: Fix timerlat error handling to prevent hangs
- b202ea46068b - rteval: Fix cyclictest error handling to prevent hangs

## Test Mechanics

- Tests require sudo because rteval needs root privileges
- Each test creates a workdir named `test-{module}-{scenario}-{pid}`
- Logs are saved as `test-{module}-{scenario}-{pid}.log`
- Duration set to 30 seconds to give rteval adequate setup time
- Tests automatically replace `/usr/bin/rtla` or `/usr/bin/cyclictest` temporarily
- Original binaries are restored on completion or interruption

## Related Issues

- **RHEL-140898** - rteval hangs in WaitForCompletion
- **RHEL-172903** - [Upstream]: rteval hangs in WaitForCompletion
- **RHEL-151475** - Root cause: rtla segfault (being fixed separately)
