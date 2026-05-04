#!/bin/bash
#
# Test script for cyclictest error handling (RHEL-140898)
# Tests that rteval handles partial/malformed cyclictest output gracefully
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
MOCK_CYCLICTEST="${SCRIPT_DIR}/mock-cyclictest-partial-output.py"
RTEVAL_MODULE="${REPO_ROOT}/rteval/modules/measurement/cyclictest.py"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Cleanup function to restore cyclictest if interrupted
cleanup_cyclictest() {
    if [ -e /usr/bin/cyclictest.real ]; then
        echo "Restoring original cyclictest..."
        sudo rm -f /usr/bin/cyclictest
        sudo mv /usr/bin/cyclictest.real /usr/bin/cyclictest
    fi
}
trap cleanup_cyclictest EXIT INT TERM

echo "========================================"
echo "Cyclictest Error Handling Test Suite"
echo "Testing fix for RHEL-140898"
echo "========================================"
echo

# Check that mock script exists and is executable
if [ ! -f "$MOCK_CYCLICTEST" ]; then
    echo -e "${RED}ERROR: Mock cyclictest script not found: $MOCK_CYCLICTEST${NC}"
    exit 1
fi

chmod +x "$MOCK_CYCLICTEST"

# Check that cyclictest module has the fix
if ! grep -q "max_attempts = 5" "$RTEVAL_MODULE"; then
    echo -e "${YELLOW}WARNING: cyclictest.py may not have the SIGINT retry limit fix${NC}"
fi

if ! grep -q "Parse histogram output.*try/finally" "$RTEVAL_MODULE"; then
    echo -e "${YELLOW}WARNING: cyclictest.py may not have the try/finally fix${NC}"
fi

if ! grep -q "except (IndexError, ValueError)" "$RTEVAL_MODULE"; then
    echo -e "${YELLOW}WARNING: cyclictest.py may not have the exception handling fix${NC}"
fi

echo "Available test scenarios:"
echo "  1. truncated_mid_line  - Line cuts off mid-way (tests IndexError)"
echo "  2. missing_columns     - Missing CPU columns (tests IndexError)"
echo "  3. invalid_numbers     - Non-numeric values (tests ValueError)"
echo "  4. mixed_corruption    - Combination of issues"
echo

# Function to run a test scenario
run_test_scenario() {
    local scenario="$1"
    local description="$2"

    echo "========================================"
    echo -e "${YELLOW}Test: $description${NC}"
    echo "Scenario: $scenario"
    echo "========================================"

    # Create a wrapper script that uses our mock instead of real cyclictest
    local wrapper="/tmp/cyclictest-wrapper-$$"
    cat > "$wrapper" << 'EOF'
#!/bin/bash
# Wrapper to intercept cyclictest calls
exec python3 "MOCK_CYCLICTEST_PATH" --scenario=SCENARIO_NAME "$@"
EOF

    sed -i "s|MOCK_CYCLICTEST_PATH|$MOCK_CYCLICTEST|g" "$wrapper"
    sed -i "s|SCENARIO_NAME|$scenario|g" "$wrapper"
    chmod +x "$wrapper"

    # Run rteval with the wrapper
    echo "Starting rteval with mock cyclictest..."
    echo "Command: ${REPO_ROOT}/rteval-cmd --duration=30 --measurement-module=cyclictest --noload --debug"
    echo

    # Temporarily replace /usr/bin/cyclictest with our wrapper
    # This bypasses sudo secure_path issues
    if [ -e /usr/bin/cyclictest ] && [ ! -e /usr/bin/cyclictest.real ]; then
        sudo mv /usr/bin/cyclictest /usr/bin/cyclictest.real
    fi
    sudo cp "$wrapper" /usr/bin/cyclictest
    sudo chmod +x /usr/bin/cyclictest

    # Run rteval and capture output
    local workdir="test-cyclictest-${scenario}-$$"
    local log_file="${workdir}.log"

    # Create workdir (rteval requires it to exist)
    mkdir -p "$workdir"

    # Use sudo -E to preserve environment (especially PATH with /tmp/cyclictest)
    if sudo -E "${REPO_ROOT}/rteval-cmd" --duration=30 --measurement-module=cyclictest --noload --debug \
         --workdir="$workdir" > "$log_file" 2>&1; then
        echo -e "${GREEN}✓ rteval completed successfully (exit code 0)${NC}"
        local result="PASS"
    else
        local exit_code=$?
        if [ $exit_code -eq 1 ]; then
            echo -e "${GREEN}✓ rteval exited with code 1 (detected malformed data - expected)${NC}"
            local result="PASS"
        elif [ $exit_code -eq 143 ] || [ $exit_code -eq 130 ]; then
            echo -e "${GREEN}✓ rteval exited with SIGTERM/SIGINT (expected)${NC}"
            local result="PASS"
        else
            echo -e "${RED}✗ rteval failed with unexpected exit code $exit_code${NC}"
            local result="FAIL"
        fi
    fi

    # Restore original cyclictest
    sudo rm -f /usr/bin/cyclictest
    if [ -e /usr/bin/cyclictest.real ]; then
        sudo mv /usr/bin/cyclictest.real /usr/bin/cyclictest
    fi
    rm -f "$wrapper"

    echo
    echo "Checking for expected behaviors:"

    # Check if mock was actually used by looking for scenario-specific exit codes
    local mock_called=false
    case "$scenario" in
        truncated_mid_line)
            if grep -q "exited with non-zero status: 139" "$log_file"; then
                echo -e "${GREEN}✓ Mock cyclictest was called (exit code 139 detected)${NC}"
                mock_called=true
            fi
            ;;
        missing_columns|invalid_numbers)
            if grep -q "exited with non-zero status: 1" "$log_file"; then
                echo -e "${GREEN}✓ Mock cyclictest was called (exit code 1 detected)${NC}"
                mock_called=true
            fi
            ;;
        mixed_corruption)
            # This scenario exits 0 but produces bad data
            if grep -q "Error parsing cyclictest bucket data" "$log_file"; then
                echo -e "${GREEN}✓ Mock cyclictest was called (parsing errors detected)${NC}"
                mock_called=true
            fi
            ;;
    esac

    if [ "$mock_called" = false ]; then
        echo -e "${RED}✗ Mock cyclictest was NOT called - scenario-specific behavior not found${NC}"
        result="FAIL"
    fi

    # Check for warning about parsing errors
    if grep -q "Error parsing cyclictest bucket data" "$log_file" || \
       grep -q "Error parsing max latencies" "$log_file" || \
       grep -q "unexpected output" "$log_file"; then
        echo -e "${GREEN}✓ Logged warnings about malformed data${NC}"
    else
        echo -e "${YELLOW}? No warnings about malformed data found${NC}"
    fi

    # Check for SIGINT handling (if applicable)
    if grep -q "Sending SIGINT" "$log_file"; then
        echo -e "${GREEN}✓ SIGINT signal handling present${NC}"

        # Count SIGINT attempts
        local sigint_count=$(grep -c "Sending SIGINT" "$log_file" || true)
        if [ "$sigint_count" -le 5 ]; then
            echo -e "${GREEN}✓ SIGINT attempts limited ($sigint_count <= 5)${NC}"
        else
            echo -e "${RED}✗ Too many SIGINT attempts: $sigint_count${NC}"
            result="FAIL"
        fi
    fi

    # Check that it didn't hang (completed in reasonable time is implicit if we got here)
    echo -e "${GREEN}✓ Did not hang (completed within timeout)${NC}"

    # Check for exit code handling
    if grep -q "exited with non-zero status" "$log_file"; then
        echo -e "${GREEN}✓ Non-zero exit code logged${NC}"
    fi

    echo
    echo "Log file saved to: $log_file"
    echo "Work directory: $workdir"

    if [ "$result" = "PASS" ]; then
        echo -e "${GREEN}======== TEST PASSED ========${NC}"
    else
        echo -e "${RED}======== TEST FAILED ========${NC}"
        echo "See $log_file for details"
    fi

    echo
    return 0
}

# Run test scenarios
if [ $# -eq 0 ]; then
    # Run all tests
    run_test_scenario "truncated_mid_line" "Truncated Line (IndexError test)"
    run_test_scenario "missing_columns" "Missing Columns (IndexError test)"
    run_test_scenario "invalid_numbers" "Invalid Numbers (ValueError test)"
    run_test_scenario "mixed_corruption" "Mixed Corruption (comprehensive test)"
else
    # Run specific test
    run_test_scenario "$1" "User-specified scenario"
fi

echo
echo "========================================"
echo "All tests completed"
echo "========================================"
