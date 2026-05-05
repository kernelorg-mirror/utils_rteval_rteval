#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
#
# Test runner for rteval unit tests
#
# This script runs all unit tests in the tests_progs/ directory
# and provides a summary of results.
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Test results tracking
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

echo "========================================="
echo "Running rteval Unit Tests"
echo "========================================="
echo ""

# Function to run a single test
run_test() {
    local test_file=$1
    local test_name=$(basename "$test_file" .py)

    echo -e "${YELLOW}Running: ${test_name}${NC}"
    echo "---"

    if python3 "$test_file"; then
        echo -e "${GREEN}✓ PASSED: ${test_name}${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}✗ FAILED: ${test_name}${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi

    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo ""
}

# Find and run all test files in tests/
if [ -d "tests" ]; then
    # Run test_measurement_module_selection.py
    if [ -f "tests/test_measurement_module_selection.py" ]; then
        run_test "tests/test_measurement_module_selection.py"
    fi

    # Run test_core_sharing_validation.py
    if [ -f "tests/test_core_sharing_validation.py" ]; then
        run_test "tests/test_core_sharing_validation.py"
    fi

    # Add more tests here as they are created
    # Example:
    # if [ -f "tests/test_another_feature.py" ]; then
    #     run_test "tests/test_another_feature.py"
    # fi
else
    echo -e "${RED}Error: tests/ directory not found${NC}"
    exit 1
fi

# Print summary
echo "========================================="
echo "Test Summary"
echo "========================================="
echo "Total tests run: $TOTAL_TESTS"
echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}"
if [ $FAILED_TESTS -gt 0 ]; then
    echo -e "Failed: ${RED}$FAILED_TESTS${NC}"
else
    echo -e "Failed: $FAILED_TESTS"
fi
echo ""

# Exit with appropriate code
if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi
