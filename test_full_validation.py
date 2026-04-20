#!/usr/bin/env python3
"""
Test core sharing validation with mocked isolated CPUs
Tests both console warnings and XML output
"""

import sys
sys.path.insert(0, '.')

from unittest.mock import patch, Mock
import libxml2
from rteval.systopology import validate_core_sharing

# Mock isolated CPUs: simulate CPUs 0, 8, 1, 9 as isolated
# Based on actual topology: CPUs 0 and 8 share a core, 1 and 9 share a core
MOCK_ISOLATED_CPUS = [0, 8, 1, 9]

print("=" * 70)
print("TESTING CORE SHARING VALIDATION")
print("=" * 70)
print()
print("System core topology (from actual hardware):")
from rteval.sysinfo.coresiblings import CoreSiblings
cs = CoreSiblings()
for i, group in enumerate(cs.get_core_groups()[:4]):
    print(f"  Core {i}: {sorted(group)}")
print()
print(f"Simulating isolated CPUs: {MOCK_ISOLATED_CPUS}")
print()

# Test 1: Console warnings
print("=" * 70)
print("TEST 1: Console Warnings")
print("=" * 70)
print()

with patch('rteval.systopology.SysTopology') as mock_systopo:
    mock_instance = mock_systopo.return_value
    mock_instance.isolated_cpus.return_value = MOCK_ISOLATED_CPUS

    print("Scenario 1: Housekeeping and Measurement share core")
    print("  Housekeeping: [0]  (isolated)")
    print("  Measurement:  [8]  (isolated, shares core with 0)")
    print("  Load:         [2]  (non-isolated)")
    warnings = validate_core_sharing([0], [8], [2])
    if warnings:
        print(f"  ✓ Got {len(warnings)} warning(s):")
        for w in warnings:
            print(f"    {w}")
    else:
        print("  ✗ No warnings!")
    print()

    print("Scenario 2: All three workload types on different cores")
    print("  Housekeeping: [0]  (isolated)")
    print("  Measurement:  [1]  (isolated, different core)")
    print("  Load:         [2]  (non-isolated, different core)")
    warnings = validate_core_sharing([0], [1], [2])
    if warnings:
        print(f"  ✗ Unexpected warnings: {warnings}")
    else:
        print("  ✓ No warnings (correct!)")
    print()

    print("Scenario 3: Multiple conflicts")
    print("  Housekeeping: [0]     (isolated)")
    print("  Measurement:  [8]     (isolated, shares core with 0)")
    print("  Load:         [1,9]   (1 and 9 both isolated, share a core)")
    warnings = validate_core_sharing([0], [8], [1, 9])
    if warnings:
        print(f"  ✓ Got {len(warnings)} warning(s):")
        for w in warnings:
            print(f"    {w}")
    else:
        print("  ✗ No warnings!")
    print()

# Test 2: XML output
print("=" * 70)
print("TEST 2: XML Report Generation")
print("=" * 70)
print()

with patch('rteval.systopology.SysTopology') as mock_systopo:
    mock_instance = mock_systopo.return_value
    mock_instance.isolated_cpus.return_value = MOCK_ISOLATED_CPUS
    mock_instance.isolated_cpus_str.return_value = [str(cpu) for cpu in MOCK_ISOLATED_CPUS]

    from rteval.sysinfo.cputopology import CPUtopology
    from rteval.Log import Log

    # Create CPUtopology and parse
    cputop = CPUtopology()
    cputop._parse()

    # Now add warnings with conflicting CPU lists
    print("Adding warnings for:")
    print("  Housekeeping: [0]  (isolated)")
    print("  Measurement:  [8]  (isolated, shares core with 0)")
    print("  Load:         [1,9] (both isolated, share core with each other)")
    print()

    # First verify that validation itself works with the mock
    from rteval.systopology import validate_core_sharing
    test_warnings = validate_core_sharing([0], [8], [1, 9])
    print(f"Direct validation call returned {len(test_warnings)} warning(s)")
    print()

    cputop.add_core_sharing_warnings([0], [8], [1, 9])

    # Get the XML
    xml = cputop.MakeReport()

    # Check for warnings in XML
    # Search for CoreSharingWarnings child node
    warnings_section = None
    child = xml.children
    while child:
        if child.name == 'CoreSharingWarnings':
            warnings_section = child
            break
        child = child.next

    if warnings_section:
        warning_list = []
        warning_child = warnings_section.children
        while warning_child:
            if warning_child.name == 'warning':
                warning_list.append(warning_child.getContent())
            warning_child = warning_child.next

        if warning_list:
            print(f"✓ Found {len(warning_list)} warning(s) in XML:")
            for w in warning_list:
                print(f"  - {w}")
        else:
            print("✗ CoreSharingWarnings section exists but is empty!")
    else:
        print("✗ No CoreSharingWarnings section found in XML!")

    print()
    print("Full CPUtopology XML section:")
    print("-" * 70)
    temp_doc = libxml2.newDoc("1.0")
    temp_doc.setRootElement(xml.docCopyNode(temp_doc, 1))
    temp_doc.saveFormatFileEnc("-", "UTF-8", 1)

print()
print("=" * 70)
print("ALL TESTS COMPLETE")
print("=" * 70)
