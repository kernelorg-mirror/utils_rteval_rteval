#!/bin/bash
# Test script for core sharing validation with real isolated CPUs
# Run as root after rebooting with isolcpus=0,8,1,9,2,10,3,11

set -e

echo "========================================================================"
echo "Testing Core Sharing Validation with Isolated CPUs"
echo "========================================================================"
echo

# Check if running as root
if [ "$EUID" -ne 0 ]; then
   echo "ERROR: This script must be run as root"
   exit 1
fi

# Verify isolated CPUs are configured
echo "Step 1: Verifying isolated CPUs setup"
echo "----------------------------------------"
ISOLATED=$(cat /sys/devices/system/cpu/isolated 2>/dev/null || echo "")
if [ -z "$ISOLATED" ]; then
    echo "⚠ WARNING: No isolated CPUs found!"
    echo ""
    echo "This test requires isolated CPUs configured via kernel boot parameter."
    echo "Example: isolcpus=0-3,8-11"
    echo ""
    echo "To configure isolated CPUs:"
    echo "  1. Edit /etc/default/grub"
    echo "  2. Add isolcpus=<cpulist> to GRUB_CMDLINE_LINUX"
    echo "  3. Update bootloader:"
    echo "     - RHEL/Fedora: sudo grub2-mkconfig -o /boot/grub2/grub.cfg"
    echo "     - Debian/Ubuntu: sudo update-grub"
    echo "  4. Reboot"
    echo ""
    echo "SKIPPING: All tests require isolated CPUs"
    exit 0
fi
echo "✓ Isolated CPUs: $ISOLATED"
echo

# Verify isolcpus in kernel command line
echo "Kernel command line:"
grep -o 'isolcpus=[^ ]*' /proc/cmdline || echo "WARNING: isolcpus not found in cmdline"
echo

# Show core topology
echo "Step 2: Core topology"
echo "----------------------------------------"
python3 rteval/sysinfo/coresiblings.py | head -12
echo

# Test 1: Trigger warning - split siblings across workloads
echo "========================================================================"
echo "TEST 1: Trigger Warning (siblings split across workloads)"
echo "========================================================================"
echo "Configuration:"
echo "  --housekeeping 0"
echo "  --measurement-cpulist 8"
echo "  --loads-cpulist 2"
echo
echo "Expected: Warning that CPUs 0 and 8 share a core"
echo "----------------------------------------"

./rteval-cmd -D -L -d30s --housekeeping 0 --measurement-cpulist 8 --loads-cpulist 2 2>&1 | \
    grep -E "(Warning:|shares core)" || echo "No warnings found"

# Check the XML report
REPORT=$(ls -t /tmp/rteval-* 2>/dev/null | head -1)
if [ -n "$REPORT" ]; then
    echo
    echo "Checking XML report: $REPORT"
    if grep -q "CoreSharingWarnings" "$REPORT"/*.xml 2>/dev/null; then
        echo "✓ XML contains CoreSharingWarnings section:"
        grep -A 5 "CoreSharingWarnings" "$REPORT"/*.xml | head -10
    else
        echo "✗ No CoreSharingWarnings in XML"
    fi
fi

echo
echo "========================================================================"
echo "TEST 2: No Warning (proper separation)"
echo "========================================================================"
echo "Configuration:"
echo "  --housekeeping 0,8"
echo "  --measurement-cpulist 1,9,2,10"
echo "  --loads-cpulist 3,11"
echo
echo "Expected: No warnings (each workload on separate cores)"
echo "----------------------------------------"

./rteval-cmd -D -L -d30s --housekeeping 0,8 --measurement-cpulist 1,9,2,10 --loads-cpulist 3,11 2>&1 | \
    grep -E "(Warning:|shares core)" && echo "✗ Unexpected warning!" || echo "✓ No warnings (correct!)"

echo
echo "========================================================================"
echo "TEST 3: Multiple conflicts"
echo "========================================================================"
echo "Configuration:"
echo "  --housekeeping 0"
echo "  --measurement-cpulist 8,1"
echo "  --loads-cpulist 9"
echo
echo "Expected: Warnings about 0 vs 8, and 1 vs 9"
echo "----------------------------------------"

./rteval-cmd -D -L -d30s --housekeeping 0 --measurement-cpulist 8,1 --loads-cpulist 9 2>&1 | \
    grep -E "(Warning:|shares core)" || echo "No warnings found"

echo
echo "========================================================================"
echo "All tests complete!"
echo "========================================================================"
echo
echo "Summary:"
echo "  Test 1: Should show warning about CPUs 0 and 8"
echo "  Test 2: Should show NO warnings"
echo "  Test 3: Should show warnings about 0 vs 8, and 1 vs 9"
