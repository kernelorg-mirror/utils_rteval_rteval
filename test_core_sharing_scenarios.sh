#!/bin/bash
# Comprehensive test for core sharing warnings in different scenarios
# Tests both console warnings and XML/XSLT output

set -e

echo "========================================================================="
echo "Core Sharing Warning Test Suite"
echo "========================================================================="
echo ""

# Check for isolated CPUs
ISOLATED=$(cat /sys/devices/system/cpu/isolated 2>/dev/null || echo "")
if [ -z "$ISOLATED" ]; then
    echo "⚠ WARNING: No isolated CPUs found!"
    echo ""
    echo "This test requires isolated CPUs configured via kernel boot parameter."
    echo "Example: isolcpus=0,8,1,9 (or similar based on your CPU topology)"
    echo ""
    echo "To configure isolated CPUs:"
    echo "  1. Edit /etc/default/grub"
    echo "  2. Add isolcpus=<cpulist> to GRUB_CMDLINE_LINUX"
    echo "  3. Update bootloader:"
    echo "     - RHEL/Fedora: sudo grub2-mkconfig -o /boot/grub2/grub.cfg"
    echo "     - Debian/Ubuntu: sudo update-grub"
    echo "  4. Reboot"
    echo ""
    echo "SKIPPING: Tests require isolated CPUs"
    exit 0
fi
echo "✓ Isolated CPUs detected: $ISOLATED"
echo ""

# Cleanup old test results
rm -rf rteval-test-scenario-* 2>/dev/null || true

# CPU topology on this system:
# CPUs 0,8 share core 0 (both isolated)
# CPUs 1,9 share core 1 (both isolated)
# CPUs 4,12 share core 4 (neither isolated)

# =========================================================================
echo "Scenario 1: Only isolated CPU warnings (default behavior)"
echo "  Housekeeping: 0 (isol), Measurement: 8 (isol), Load: 1 (isol)"
echo "  Expected: Warnings for 0 vs 8 (both isol) only"
echo "-------------------------------------------------------------------------"

WORKDIR="rteval-test-scenario-1"
mkdir -p "$WORKDIR"

./rteval-cmd -D -L -d 30s --housekeeping 0 --measurement-cpulist 8 --loads-cpulist 1 \
    -w "$WORKDIR" 2>&1 | tee "$WORKDIR/console.log"

echo ""
echo "Console warnings:"
grep -i "warning.*shares core" "$WORKDIR/console.log" || echo "  (none found)"

# Find the actual rteval output directory
SUMMARY_XML=$(find "$WORKDIR" -name "summary.xml" -type f | head -1)

echo ""
echo "XML CoreSharingWarnings:"
if [ -z "$SUMMARY_XML" ]; then
    echo "  ✗ FAIL: summary.xml not found in $WORKDIR"
elif grep -q "CoreSharingWarnings" "$SUMMARY_XML"; then
    grep -A 10 "CoreSharingWarnings" "$SUMMARY_XML" | grep -E "(warning>|CoreSharingWarnings)" || true
    WARN_COUNT=$(grep -c "<warning>" "$SUMMARY_XML" || echo "0")
    echo "  Total warnings in XML: $WARN_COUNT"
    if [ "$WARN_COUNT" -eq 1 ]; then
        echo "  ✓ PASS: Expected 1 warning"
    else
        echo "  ✗ FAIL: Expected 1 warning, got $WARN_COUNT"
    fi
else
    echo "  ✗ FAIL: No CoreSharingWarnings section found"
fi

echo ""
echo "Text report (via -Z):"
if [ -n "$SUMMARY_XML" ]; then
    ./rteval-cmd -Z "$SUMMARY_XML" 2>&1 | grep -A 5 "Core Sharing" || echo "  (no warnings in text report)"
else
    echo "  (summary.xml not found)"
fi

echo ""
echo ""

# =========================================================================
echo "Scenario 2: Non-isolated warnings WITHOUT flag (should not warn)"
echo "  Measurement: 4 (non-isol), Load: 12 (non-isol)"
echo "  Expected: No warnings (flag not used)"
echo "-------------------------------------------------------------------------"

WORKDIR="rteval-test-scenario-2"
mkdir -p "$WORKDIR"

./rteval-cmd -D -L -d 30s --measurement-cpulist 4 --loads-cpulist 12 \
    -w "$WORKDIR" 2>&1 | tee "$WORKDIR/console.log"

echo ""
echo "Console warnings:"
if grep -qi "warning.*shares core" "$WORKDIR/console.log"; then
    echo "  ✗ FAIL: Unexpected warning found"
    grep -i "warning.*shares core" "$WORKDIR/console.log"
else
    echo "  ✓ PASS: No warnings (correct)"
fi

# Find the actual rteval output directory
SUMMARY_XML=$(find "$WORKDIR" -name "summary.xml" -type f | head -1)

echo ""
echo "XML CoreSharingWarnings:"
if [ -z "$SUMMARY_XML" ]; then
    echo "  ✗ FAIL: summary.xml not found in $WORKDIR"
elif grep -q "CoreSharingWarnings" "$SUMMARY_XML"; then
    echo "  ✗ FAIL: CoreSharingWarnings section should not exist"
    grep -A 10 "CoreSharingWarnings" "$SUMMARY_XML" | grep -E "(warning>|CoreSharingWarnings)" || true
else
    echo "  ✓ PASS: No CoreSharingWarnings section (correct)"
fi

echo ""
echo ""

# =========================================================================
echo "Scenario 3: Non-isolated warnings WITH flag (should warn)"
echo "  Measurement: 4 (non-isol), Load: 12 (non-isol)"
echo "  Flag: --warn-non-isolated-core-sharing"
echo "  Expected: Warning for 4 vs 12"
echo "-------------------------------------------------------------------------"

WORKDIR="rteval-test-scenario-3"
mkdir -p "$WORKDIR"

./rteval-cmd -D -L -d 30s --measurement-cpulist 4 --loads-cpulist 12 \
    --warn-non-isolated-core-sharing -w "$WORKDIR" 2>&1 | tee "$WORKDIR/console.log"

echo ""
echo "Console warnings:"
if grep -qi "warning.*CPU 4.*CPU 12" "$WORKDIR/console.log"; then
    echo "  ✓ PASS: Found expected warning"
    grep -i "warning.*shares core" "$WORKDIR/console.log"
else
    echo "  ✗ FAIL: Expected warning not found"
fi

# Find the actual rteval output directory
SUMMARY_XML=$(find "$WORKDIR" -name "summary.xml" -type f | head -1)

echo ""
echo "XML CoreSharingWarnings:"
if [ -z "$SUMMARY_XML" ]; then
    echo "  ✗ FAIL: summary.xml not found in $WORKDIR"
elif grep -q "CoreSharingWarnings" "$SUMMARY_XML"; then
    grep -A 10 "CoreSharingWarnings" "$SUMMARY_XML" | grep -E "(warning>|CoreSharingWarnings)" || true
    WARN_COUNT=$(grep -c "<warning>" "$SUMMARY_XML" || echo "0")
    echo "  Total warnings in XML: $WARN_COUNT"
    if [ "$WARN_COUNT" -eq 1 ]; then
        echo "  ✓ PASS: Expected 1 warning in XML"
    else
        echo "  ✗ FAIL: Expected 1 warning, got $WARN_COUNT"
    fi
else
    echo "  ✗ FAIL: CoreSharingWarnings section not found in XML"
fi

echo ""
echo "Text report (via -Z):"
if [ -n "$SUMMARY_XML" ]; then
    ./rteval-cmd -Z "$SUMMARY_XML" 2>&1 | grep -A 5 "Core Sharing" || echo "  ✗ FAIL: No warnings in text report"
else
    echo "  (summary.xml not found)"
fi

echo ""
echo ""

# =========================================================================
echo "Scenario 4: BOTH isolated and non-isolated warnings WITH flag"
echo "  Housekeeping: 0 (isol), Measurement: 8,4 (8 isol, 4 not), Load: 12 (not isol)"
echo "  Flag: --warn-non-isolated-core-sharing"
echo "  Expected: 2 warnings - one for 0 vs 8 (both isol), one for 4 vs 12 (neither isol)"
echo "-------------------------------------------------------------------------"

WORKDIR="rteval-test-scenario-4"
mkdir -p "$WORKDIR"

./rteval-cmd -D -L -d 30s --housekeeping 0 --measurement-cpulist 8,4 --loads-cpulist 12 \
    --warn-non-isolated-core-sharing -w "$WORKDIR" 2>&1 | tee "$WORKDIR/console.log"

echo ""
echo "Console warnings:"
grep -i "warning.*shares core" "$WORKDIR/console.log" || echo "  (none found)"

CONSOLE_WARN_COUNT=$(grep -ci "warning.*shares core" "$WORKDIR/console.log" || echo "0")
echo "  Total console warnings: $CONSOLE_WARN_COUNT"

# Find the actual rteval output directory
SUMMARY_XML=$(find "$WORKDIR" -name "summary.xml" -type f | head -1)

echo ""
echo "XML CoreSharingWarnings:"
if [ -z "$SUMMARY_XML" ]; then
    echo "  ✗ FAIL: summary.xml not found in $WORKDIR"
elif grep -q "CoreSharingWarnings" "$SUMMARY_XML"; then
    echo "  Warnings found:"
    grep -A 10 "CoreSharingWarnings" "$SUMMARY_XML" | grep "<warning>" | sed 's/^/    /'

    XML_WARN_COUNT=$(grep -c "<warning>" "$SUMMARY_XML" || echo "0")
    echo "  Total warnings in XML: $XML_WARN_COUNT"

    # Check for both expected warnings
    HAS_ISOL_WARN=$(grep -c "CPU 0.*isol.*CPU 8.*isol" "$SUMMARY_XML" || echo "0")
    HAS_NON_ISOL_WARN=$(grep -c "CPU 4 shares core with load CPU 12" "$SUMMARY_XML" || echo "0")

    if [ "$XML_WARN_COUNT" -eq 2 ] && [ "$HAS_ISOL_WARN" -eq 1 ] && [ "$HAS_NON_ISOL_WARN" -eq 1 ]; then
        echo "  ✓ PASS: Both warnings present in XML"
    else
        echo "  ✗ FAIL: Expected 2 specific warnings (isolated and non-isolated)"
    fi
else
    echo "  ✗ FAIL: CoreSharingWarnings section not found in XML"
fi

echo ""
echo "Text report (via -Z):"
if [ -n "$SUMMARY_XML" ]; then
    ./rteval-cmd -Z "$SUMMARY_XML" 2>&1 | grep -A 10 "Core Sharing" || echo "  ✗ FAIL: No warnings in text report"
else
    echo "  (summary.xml not found)"
fi

echo ""
echo ""

# =========================================================================
echo "========================================================================="
echo "Test Summary"
echo "========================================================================="
echo ""
echo "All test results are saved in rteval-test-scenario-* directories"
echo "You can review:"
echo "  - Console output: rteval-test-scenario-*/console.log"
echo "  - XML reports: rteval-test-scenario-*/rteval-*/summary.xml"
echo "  - Text reports: ./rteval-cmd -Z rteval-test-scenario-*/rteval-*/summary.xml"
echo ""
echo "Quick check of all XML files:"
for dir in rteval-test-scenario-*/rteval-*/summary.xml; do
    if [ -f "$dir" ]; then
        echo "  $dir"
        if grep -q "CoreSharingWarnings" "$dir"; then
            echo "    - Has CoreSharingWarnings section"
        else
            echo "    - No CoreSharingWarnings section"
        fi
    fi
done
echo ""
