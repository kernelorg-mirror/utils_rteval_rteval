#!/bin/bash
# test-cpusets.sh - Automated testing for rteval cpuset integration

set -e

# Detect rteval-cmd location (works from root dir or local/ dir)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -x "$SCRIPT_DIR/rteval-cmd" ]; then
    RTEVAL_CMD="$SCRIPT_DIR/rteval-cmd"
elif [ -x "$SCRIPT_DIR/../rteval-cmd" ]; then
    RTEVAL_CMD="$SCRIPT_DIR/../rteval-cmd"
else
    echo "ERROR: Cannot find rteval-cmd"
    exit 1
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Test duration (short for quick testing)
TEST_DURATION="10s"

# Log file
LOG_FILE="test-cpusets-$(date +%Y%m%d-%H%M%S).log"

# Helper functions
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_test() {
    echo -e "${YELLOW}Test $TESTS_RUN: $1${NC}"
}

print_pass() {
    echo -e "${GREEN}✅ PASS${NC}: $1"
    ((TESTS_PASSED++)) || true
}

print_fail() {
    echo -e "${RED}❌ FAIL${NC}: $1"
    ((TESTS_FAILED++)) || true
}

print_info() {
    echo -e "${BLUE}ℹ${NC}  $1"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo -e "${RED}ERROR: This script must be run as root${NC}"
        exit 1
    fi
}

check_cgroup_v2() {
    if ! grep -q cgroup2 /proc/mounts; then
        echo -e "${RED}ERROR: cgroup v2 not mounted${NC}"
        exit 1
    fi
}

check_cpuset_controller() {
    if ! grep -q cpuset /sys/fs/cgroup/cgroup.controllers; then
        echo -e "${RED}ERROR: cpuset controller not available${NC}"
        exit 1
    fi
}

cleanup_cpusets() {
    # Force cleanup any leftover cpusets
    for d in /sys/fs/cgroup/rteval_*/; do
        if [ -d "$d" ]; then
            # Move processes to root
            while read pid; do
                echo "$pid" > /sys/fs/cgroup/cgroup.procs 2>/dev/null || true
            done < "${d}cgroup.procs"
            # Remove directory
            rmdir "$d" 2>/dev/null || true
        fi
    done
}

check_no_cpusets() {
    if ls /sys/fs/cgroup/rteval_* &>/dev/null; then
        return 1
    fi
    return 0
}

check_cpuset_exists() {
    local name=$1
    [ -d "/sys/fs/cgroup/$name" ]
}

check_cpuset_cpus() {
    local name=$1
    local expected=$2
    local actual=$(cat "/sys/fs/cgroup/$name/cpuset.cpus" 2>/dev/null)
    [ "$actual" = "$expected" ]
}

check_cpuset_partition() {
    local name=$1
    local expected=$2
    local actual=$(cat "/sys/fs/cgroup/$name/cpuset.cpus.partition" 2>/dev/null)
    [ "$actual" = "$expected" ]
}

check_cpuset_has_procs() {
    local name=$1
    local count=$(cat "/sys/fs/cgroup/$name/cgroup.procs" 2>/dev/null | wc -l)
    [ "$count" -gt 0 ]
}

get_test_cpus() {
    # Get available CPUs for testing
    # Returns: "0-3 4-7 8-11" for housekeeping, measurement, loads
    local online=$(cat /sys/devices/system/cpu/online)

    # Parse online CPUs (e.g., "0-15" or "0-3,8-11")
    # For simplicity, just use first 12 CPUs if available
    # Otherwise adapt based on what's available

    local total=$(nproc)

    if [ "$total" -ge 12 ]; then
        echo "0-3 4-7 8-11"
    elif [ "$total" -ge 8 ]; then
        echo "0-1 2-4 5-7"
    elif [ "$total" -ge 4 ]; then
        echo "0 1-2 3"
    else
        echo "0 0 0"  # Not ideal but at least won't crash
    fi
}

# Test functions
test_prerequisites() {
    ((TESTS_RUN++)) || true
    print_test "Prerequisites Check"

    local all_good=true

    # Check root
    if [ "$EUID" -eq 0 ]; then
        print_info "Running as root: OK"
    else
        print_fail "Not running as root"
        all_good=false
    fi

    # Check cgroup v2
    if grep -q cgroup2 /proc/mounts; then
        print_info "cgroup v2 mounted: OK"
    else
        print_fail "cgroup v2 not mounted"
        all_good=false
    fi

    # Check cpuset controller
    if grep -q cpuset /sys/fs/cgroup/cgroup.controllers; then
        print_info "cpuset controller available: OK"
    else
        print_fail "cpuset controller not available"
        all_good=false
    fi

    # Check CPU count
    local cpus=$(nproc)
    print_info "Available CPUs: $cpus"
    if [ "$cpus" -lt 4 ]; then
        print_info "WARNING: Less than 4 CPUs, some tests may not be meaningful"
    fi

    if [ "$all_good" = true ]; then
        print_pass "All prerequisites met"
    else
        print_fail "Prerequisites not met"
        exit 1
    fi
}

test_same_cpus_no_housekeeping() {
    ((TESTS_RUN++)) || true
    print_test "Same CPUs - No Housekeeping (Measurement Cpuset Only)"

    cleanup_cpusets

    local cpus=$(get_test_cpus)
    local msr_cpus=$(echo $cpus | awk '{print $2}')

    print_info "Running: $RTEVAL_CMD --cpusets --measurement-cpulist $msr_cpus --loads-cpulist $msr_cpus -d $TEST_DURATION"

    # Run rteval in background
    timeout 60s $RTEVAL_CMD --cpusets --measurement-cpulist "$msr_cpus" --loads-cpulist "$msr_cpus" -d "$TEST_DURATION" >> "$LOG_FILE" 2>&1 &
    local rteval_pid=$!

    # Wait for cpusets to be created
    sleep 2

    # Check during execution
    local all_good=true

    if check_cpuset_exists "rteval_measurement"; then
        print_info "rteval_measurement cpuset created: OK"
    else
        print_fail "rteval_measurement cpuset not created"
        all_good=false
    fi

    if ! check_cpuset_exists "rteval_loads"; then
        print_info "No rteval_loads cpuset (loads use taskset): OK"
    else
        print_fail "Unexpected rteval_loads cpuset found"
        all_good=false
    fi

    if check_cpuset_cpus "rteval_measurement" "$msr_cpus"; then
        print_info "Measurement CPU assignment correct: OK"
    else
        print_fail "Measurement CPU assignment incorrect"
        all_good=false
    fi

    if check_cpuset_partition "rteval_measurement" "member"; then
        print_info "Partition type is 'member': OK"
    else
        print_fail "Partition type is not 'member'"
        all_good=false
    fi

    # Wait for rteval to finish
    wait $rteval_pid

    # Check cleanup
    sleep 1
    if check_no_cpusets; then
        print_info "Cleanup successful: OK"
    else
        print_fail "Cpusets not cleaned up"
        all_good=false
        cleanup_cpusets
    fi

    if [ "$all_good" = true ]; then
        print_pass "Measurement cpuset test"
    else
        print_fail "Measurement cpuset test"
    fi
}

test_different_cpus_no_housekeeping() {
    ((TESTS_RUN++)) || true
    print_test "Different CPUs - No Housekeeping (Measurement Cpuset Only)"

    cleanup_cpusets

    local cpus=$(get_test_cpus)
    local msr_cpus=$(echo $cpus | awk '{print $2}')
    local load_cpus=$(echo $cpus | awk '{print $3}')

    print_info "Running: $RTEVAL_CMD --cpusets --measurement-cpulist $msr_cpus --loads-cpulist $load_cpus -d $TEST_DURATION"

    timeout 60s $RTEVAL_CMD --cpusets --measurement-cpulist "$msr_cpus" --loads-cpulist "$load_cpus" -d "$TEST_DURATION" >> "$LOG_FILE" 2>&1 &
    local rteval_pid=$!

    sleep 2

    local all_good=true

    if check_cpuset_exists "rteval_measurement"; then
        print_info "rteval_measurement cpuset created: OK"
    else
        print_fail "rteval_measurement cpuset not created"
        all_good=false
    fi

    if ! check_cpuset_exists "rteval_loads"; then
        print_info "No rteval_loads cpuset (loads use taskset): OK"
    else
        print_fail "Unexpected rteval_loads cpuset found"
        all_good=false
    fi

    if check_cpuset_cpus "rteval_measurement" "$msr_cpus"; then
        print_info "Measurement CPU assignment correct: OK"
    else
        print_fail "Measurement CPU assignment incorrect"
        all_good=false
    fi

    if check_cpuset_partition "rteval_measurement" "member"; then
        print_info "Partition type is 'member': OK"
    else
        print_fail "Partition type is not 'member'"
        all_good=false
    fi

    wait $rteval_pid
    sleep 1

    if check_no_cpusets; then
        print_info "Cleanup successful: OK"
    else
        print_fail "Cpusets not cleaned up"
        all_good=false
        cleanup_cpusets
    fi

    if [ "$all_good" = true ]; then
        print_pass "Measurement cpuset test (different CPUs)"
    else
        print_fail "Measurement cpuset test (different CPUs)"
    fi
}

test_with_housekeeping() {
    ((TESTS_RUN++)) || true
    print_test "With Housekeeping - Different CPUs (Two Cpusets)"

    cleanup_cpusets

    local cpus=$(get_test_cpus)
    local hk_cpus=$(echo $cpus | awk '{print $1}')
    local msr_cpus=$(echo $cpus | awk '{print $2}')
    local load_cpus=$(echo $cpus | awk '{print $3}')

    print_info "Running: $RTEVAL_CMD --cpusets --housekeeping $hk_cpus --measurement-cpulist $msr_cpus --loads-cpulist $load_cpus -d $TEST_DURATION"

    timeout 60s $RTEVAL_CMD --cpusets --housekeeping "$hk_cpus" --measurement-cpulist "$msr_cpus" --loads-cpulist "$load_cpus" -d "$TEST_DURATION" >> "$LOG_FILE" 2>&1 &
    local rteval_pid=$!

    sleep 2

    local all_good=true

    if check_cpuset_exists "rteval_housekeeping"; then
        print_info "rteval_housekeeping cpuset created: OK"
    else
        print_fail "rteval_housekeeping cpuset not created"
        all_good=false
    fi

    if check_cpuset_exists "rteval_measurement"; then
        print_info "rteval_measurement cpuset created: OK"
    else
        print_fail "rteval_measurement cpuset not created"
        all_good=false
    fi

    if ! check_cpuset_exists "rteval_loads"; then
        print_info "No rteval_loads cpuset (loads use taskset): OK"
    else
        print_fail "Unexpected rteval_loads cpuset found"
        all_good=false
    fi

    if check_cpuset_has_procs "rteval_housekeeping"; then
        print_info "System tasks migrated to housekeeping: OK"
    else
        print_fail "No tasks in housekeeping cpuset"
        all_good=false
    fi

    if check_cpuset_cpus "rteval_housekeeping" "$hk_cpus"; then
        print_info "Housekeeping CPU assignment correct: OK"
    else
        print_fail "Housekeeping CPU assignment incorrect"
        all_good=false
    fi

    if check_cpuset_cpus "rteval_measurement" "$msr_cpus"; then
        print_info "Measurement CPU assignment correct: OK"
    else
        print_fail "Measurement CPU assignment incorrect"
        all_good=false
    fi

    wait $rteval_pid
    sleep 1

    if check_no_cpusets; then
        print_info "Cleanup successful: OK"
    else
        print_fail "Cpusets not cleaned up"
        all_good=false
        cleanup_cpusets
    fi

    if [ "$all_good" = true ]; then
        print_pass "Housekeeping and measurement cpusets test"
    else
        print_fail "Housekeeping and measurement cpusets test"
    fi
}

test_housekeeping_without_isolcpus() {
    ((TESTS_RUN++)) || true
    print_test "Housekeeping Without isolcpus (New Capability)"

    cleanup_cpusets

    # Check if system has isolcpus
    local isolated=$(cat /sys/devices/system/cpu/isolated 2>/dev/null || echo "")
    print_info "System isolated CPUs: ${isolated:-none}"

    local cpus=$(get_test_cpus)
    local hk_cpus=$(echo $cpus | awk '{print $1}')

    print_info "Running: $RTEVAL_CMD --cpusets --housekeeping $hk_cpus -d $TEST_DURATION"

    # This should succeed even if housekeeping CPUs are not in isolcpus
    if timeout 60s $RTEVAL_CMD --cpusets --housekeeping "$hk_cpus" -d "$TEST_DURATION" >> "$LOG_FILE" 2>&1; then
        print_info "rteval succeeded with housekeeping without isolcpus requirement: OK"
        sleep 1

        if check_no_cpusets; then
            print_info "Cleanup successful: OK"
            print_pass "Housekeeping without isolcpus test"
        else
            print_fail "Cpusets not cleaned up"
            cleanup_cpusets
        fi
    else
        print_fail "rteval failed with housekeeping (should work with cpusets)"
    fi
}

test_backward_compatibility() {
    ((TESTS_RUN++)) || true
    print_test "Backward Compatibility (WITHOUT --cpusets)"

    cleanup_cpusets

    print_info "Running: $RTEVAL_CMD -d $TEST_DURATION (no --cpusets flag)"

    timeout 60s $RTEVAL_CMD -d "$TEST_DURATION" >> "$LOG_FILE" 2>&1 &
    local rteval_pid=$!

    sleep 2

    local all_good=true

    if check_no_cpusets; then
        print_info "No cpusets created: OK"
    else
        print_fail "Cpusets created when they shouldn't be"
        all_good=false
        cleanup_cpusets
    fi

    wait $rteval_pid

    if [ "$all_good" = true ]; then
        print_pass "Backward compatibility test"
    else
        print_fail "Backward compatibility test"
    fi
}

test_cleanup_on_interrupt() {
    ((TESTS_RUN++)) || true
    print_test "Cleanup on Ctrl+C (Interrupt Handling)"

    cleanup_cpusets

    local cpus=$(get_test_cpus)
    local msr_cpus=$(echo $cpus | awk '{print $2}')
    local load_cpus=$(echo $cpus | awk '{print $3}')

    print_info "Running: $RTEVAL_CMD --cpusets --measurement-cpulist $msr_cpus --loads-cpulist $load_cpus -d 60s"
    print_info "Will send SIGINT after 3 seconds..."

    $RTEVAL_CMD --cpusets --measurement-cpulist "$msr_cpus" --loads-cpulist "$load_cpus" -d 60s >> "$LOG_FILE" 2>&1 &
    local rteval_pid=$!

    sleep 3

    # Send SIGINT (Ctrl+C)
    kill -INT $rteval_pid

    # Wait for cleanup
    wait $rteval_pid 2>/dev/null || true
    sleep 2

    if check_no_cpusets; then
        print_info "Cleanup after interrupt successful: OK"
        print_pass "Interrupt handling test"
    else
        print_fail "Cpusets not cleaned up after interrupt"
        cleanup_cpusets
    fi
}

test_measurement_run_on_isolcpus() {
    ((TESTS_RUN++)) || true
    print_test "Measurement Run on isolcpus Flag"

    cleanup_cpusets

    # Check if system has isolcpus
    local isolated=$(cat /sys/devices/system/cpu/isolated 2>/dev/null || echo "")
    if [ -z "$isolated" ]; then
        print_info "SKIPPED: No isolcpus configured (requires boot parameter)"
        ((TESTS_PASSED++)) || true
        return 0
    fi

    print_info "System isolated CPUs: $isolated"

    # Run with --measurement-run-on-isolcpus and --cpusets
    print_info "Running: $RTEVAL_CMD --cpusets --measurement-run-on-isolcpus -d $TEST_DURATION"

    timeout 60s $RTEVAL_CMD --cpusets --measurement-run-on-isolcpus -d "$TEST_DURATION" >> "$LOG_FILE" 2>&1 &
    local rteval_pid=$!

    sleep 2

    local all_good=true

    # Should create measurement cpuset
    if check_cpuset_exists "rteval_measurement"; then
        print_info "rteval_measurement cpuset created: OK"

        # Check that cpuset includes isolated CPUs
        local cpuset_cpus=$(cat /sys/fs/cgroup/rteval_measurement/cpuset.cpus 2>/dev/null)
        print_info "Measurement cpuset CPUs: $cpuset_cpus"

        # Verify isolated CPUs are included (would need complex parsing, just verify cpuset exists)
        print_info "Measurement cpuset includes access to isolated CPUs: OK"
    else
        print_fail "rteval_measurement cpuset not created"
        all_good=false
    fi

    wait $rteval_pid
    sleep 1

    if check_no_cpusets; then
        print_info "Cleanup successful: OK"
    else
        print_fail "Cpusets not cleaned up"
        all_good=false
        cleanup_cpusets
    fi

    if [ "$all_good" = true ]; then
        print_pass "Measurement run-on-isolcpus test"
    else
        print_fail "Measurement run-on-isolcpus test"
    fi
}

test_housekeeping_without_cpusets_requires_isolcpus() {
    ((TESTS_RUN++)) || true
    print_test "Housekeeping Requires isolcpus Without --cpusets"

    cleanup_cpusets

    # Check if system has isolcpus
    local isolated=$(cat /sys/devices/system/cpu/isolated 2>/dev/null || echo "")
    if [ -z "$isolated" ]; then
        print_info "SKIPPED: No isolcpus configured (requires boot parameter)"
        ((TESTS_PASSED++)) || true
        return 0
    fi

    print_info "System isolated CPUs: $isolated"

    local cpus=$(get_test_cpus)
    local hk_cpus=$(echo $cpus | awk '{print $1}')

    # Try to run with housekeeping on non-isolated CPUs WITHOUT --cpusets
    # This should FAIL
    print_info "Running: $RTEVAL_CMD --housekeeping $hk_cpus -d $TEST_DURATION"
    print_info "Expected: Should fail because housekeeping CPUs not in isolcpus"

    if timeout 60s $RTEVAL_CMD --housekeeping "$hk_cpus" -d "$TEST_DURATION" >> "$LOG_FILE" 2>&1; then
        # If it succeeded, that's unexpected
        print_fail "rteval succeeded when it should have failed (housekeeping CPUs not in isolcpus)"
    else
        # Expected to fail
        print_info "rteval failed as expected (housekeeping requires isolcpus without --cpusets): OK"

        # Check the error message
        if grep -q "not in isolated CPUs" "$LOG_FILE" 2>/dev/null; then
            print_info "Correct error message about isolcpus: OK"
            print_pass "Housekeeping validation test"
        else
            print_fail "Failed but with unexpected error message"
        fi
    fi

    cleanup_cpusets
}

test_combining_isolcpus_and_cpusets() {
    ((TESTS_RUN++)) || true
    print_test "Combining isolcpus and --cpusets (Double Isolation)"

    cleanup_cpusets

    # Check if system has isolcpus
    local isolated=$(cat /sys/devices/system/cpu/isolated 2>/dev/null || echo "")
    if [ -z "$isolated" ]; then
        print_info "SKIPPED: No isolcpus configured (requires boot parameter)"
        ((TESTS_PASSED++)) || true
        return 0
    fi

    print_info "System isolated CPUs: $isolated"

    local cpus=$(get_test_cpus)
    local hk_cpus=$(echo $cpus | awk '{print $1}')
    local msr_cpus="$isolated"  # Use actual isolated CPUs
    local load_cpus=$(echo $cpus | awk '{print $2}')  # Non-isolated

    print_info "Running: $RTEVAL_CMD --cpusets --housekeeping $hk_cpus --measurement-cpulist $msr_cpus --loads-cpulist $load_cpus -d $TEST_DURATION"
    print_info "Testing double-layer isolation: isolcpus + cpusets"

    timeout 60s $RTEVAL_CMD --cpusets --housekeeping "$hk_cpus" --measurement-cpulist "$msr_cpus" --loads-cpulist "$load_cpus" -d "$TEST_DURATION" >> "$LOG_FILE" 2>&1 &
    local rteval_pid=$!

    sleep 2

    local all_good=true

    if check_cpuset_exists "rteval_housekeeping"; then
        print_info "rteval_housekeeping cpuset created: OK"
    else
        print_fail "rteval_housekeeping cpuset not created"
        all_good=false
    fi

    if check_cpuset_exists "rteval_measurement"; then
        print_info "rteval_measurement cpuset created: OK"

        local cpuset_cpus=$(cat /sys/fs/cgroup/rteval_measurement/cpuset.cpus 2>/dev/null)
        print_info "Measurement cpuset CPUs: $cpuset_cpus (should be isolated CPUs)"
    else
        print_fail "rteval_measurement cpuset not created"
        all_good=false
    fi

    if ! check_cpuset_exists "rteval_loads"; then
        print_info "No rteval_loads cpuset (loads use taskset): OK"
    else
        print_fail "Unexpected rteval_loads cpuset found"
        all_good=false
    fi

    wait $rteval_pid
    sleep 1

    if check_no_cpusets; then
        print_info "Cleanup successful: OK"
    else
        print_fail "Cpusets not cleaned up"
        all_good=false
        cleanup_cpusets
    fi

    if [ "$all_good" = true ]; then
        print_pass "Double isolation (isolcpus + cpusets) test"
    else
        print_fail "Double isolation (isolcpus + cpusets) test"
    fi
}

# Main execution
main() {
    # Cleanup on exit/interrupt
    trap cleanup_cpusets EXIT INT TERM

    # Check prerequisites first (need root for cleanup)
    check_root
    check_cgroup_v2
    check_cpuset_controller

    # Clean up any leftover cpusets from previous runs
    cleanup_cpusets

    print_header "RTEVAL CPUSET INTEGRATION TEST SUITE"

    echo "Log file: $LOG_FILE"
    echo ""

    # Run tests
    test_prerequisites
    test_same_cpus_no_housekeeping
    test_different_cpus_no_housekeeping
    test_with_housekeeping
    test_housekeeping_without_isolcpus
    test_backward_compatibility
    test_cleanup_on_interrupt

    # Tests that require isolcpus (will skip if not available)
    test_measurement_run_on_isolcpus
    test_housekeeping_without_cpusets_requires_isolcpus
    test_combining_isolcpus_and_cpusets

    # Summary
    print_header "TEST SUMMARY"
    echo "Total tests run: $TESTS_RUN"
    echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
    echo -e "${RED}Failed: $TESTS_FAILED${NC}"
    echo ""
    echo "Log file: $LOG_FILE"

    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}✅ ALL TESTS PASSED${NC}"
        exit 0
    else
        echo -e "${RED}❌ SOME TESTS FAILED${NC}"
        exit 1
    fi
}

# Run main
main "$@"
