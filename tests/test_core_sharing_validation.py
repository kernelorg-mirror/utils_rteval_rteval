#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
#
# Unit test for core sharing validation with mocked isolated CPUs
#
# This test verifies that core sharing warnings are correctly generated
# when isolated CPUs sharing a physical core are assigned to different
# workload types (housekeeping, measurement, load).
#
# The test uses mocked isolated CPUs to ensure reproducibility across
# different systems without requiring special boot parameters.
#

import sys
import os
import unittest
from unittest.mock import patch, Mock
import libxml2

# Add rteval to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rteval.systopology import validate_core_sharing
from rteval.sysinfo.cputopology import CPUtopology
from rteval.Log import Log


class TestCoreSharingValidation(unittest.TestCase):
    """Test suite for core sharing validation with mocked isolated CPUs"""

    # Mock isolated CPUs: simulate CPUs 0, 8, 1, 9 as isolated
    # Based on typical topology: CPUs 0 and 8 share a core, 1 and 9 share a core
    MOCK_ISOLATED_CPUS = [0, 8, 1, 9]

    @patch('rteval.systopology.SysTopology')
    def test_housekeeping_measurement_share_core(self, mock_systopo):
        """Test warning when housekeeping and measurement share a core"""
        mock_instance = mock_systopo.return_value
        mock_instance.isolated_cpus.return_value = self.MOCK_ISOLATED_CPUS

        # Housekeeping: [0] (isolated)
        # Measurement:  [8] (isolated, shares core with 0)
        # Load:         [2] (non-isolated)
        warnings = validate_core_sharing([0], [8], [2])

        self.assertGreater(len(warnings), 0,
                          "Expected warning when housekeeping and measurement share a core")
        self.assertTrue(any("housekeeping" in w.lower() and "measurement" in w.lower()
                           for w in warnings),
                       "Warning should mention both housekeeping and measurement")

    @patch('rteval.systopology.SysTopology')
    def test_no_warnings_different_cores(self, mock_systopo):
        """Test no warnings when all workload types use different cores"""
        mock_instance = mock_systopo.return_value
        mock_instance.isolated_cpus.return_value = self.MOCK_ISOLATED_CPUS

        # Housekeeping: [0]  (isolated)
        # Measurement:  [1]  (isolated, different core)
        # Load:         [2]  (non-isolated, different core)
        warnings = validate_core_sharing([0], [1], [2])

        self.assertEqual(len(warnings), 0,
                        "Expected no warnings when workloads use different cores")

    @patch('rteval.systopology.SysTopology')
    def test_multiple_conflicts(self, mock_systopo):
        """Test warnings when multiple core sharing conflicts exist"""
        mock_instance = mock_systopo.return_value
        mock_instance.isolated_cpus.return_value = self.MOCK_ISOLATED_CPUS

        # Housekeeping: [0]     (isolated)
        # Measurement:  [8]     (isolated, shares core with 0)
        # Load:         [1,9]   (1 and 9 both isolated, share a core)
        warnings = validate_core_sharing([0], [8], [1, 9])

        self.assertGreaterEqual(len(warnings), 1,
                               "Expected at least one warning for core sharing conflicts")
        # Verify the warning mentions the housekeeping/measurement conflict
        self.assertTrue(any("housekeeping" in w.lower() and "measurement" in w.lower()
                           for w in warnings),
                       "Warning should mention housekeeping/measurement conflict")

    @patch('rteval.systopology.SysTopology')
    def test_xml_report_generation(self, mock_systopo):
        """Test that warnings are properly added to XML report"""
        mock_instance = mock_systopo.return_value
        mock_instance.isolated_cpus.return_value = self.MOCK_ISOLATED_CPUS
        mock_instance.isolated_cpus_str.return_value = [str(cpu) for cpu in self.MOCK_ISOLATED_CPUS]

        # Create CPUtopology and parse
        cputop = CPUtopology()
        cputop._parse()

        # Add warnings with conflicting CPU lists
        # Housekeeping: [0]  (isolated)
        # Measurement:  [8]  (isolated, shares core with 0)
        # Load:         [1,9] (both isolated, share core with each other)
        cputop.add_core_sharing_warnings([0], [8], [1, 9])

        # Get the XML
        xml = cputop.MakeReport()

        # Search for CoreSharingWarnings child node
        warnings_section = None
        child = xml.children
        while child:
            if child.name == 'CoreSharingWarnings':
                warnings_section = child
                break
            child = child.next

        self.assertIsNotNone(warnings_section,
                            "CoreSharingWarnings section should exist in XML")

        # Extract warnings from XML
        warning_list = []
        if warnings_section:
            warning_child = warnings_section.children
            while warning_child:
                if warning_child.name == 'warning':
                    warning_list.append(warning_child.getContent())
                warning_child = warning_child.next

        self.assertGreater(len(warning_list), 0,
                          "CoreSharingWarnings section should contain at least one warning")

    @patch('rteval.systopology.SysTopology')
    def test_isolated_marker_in_warnings(self, mock_systopo):
        """Test that warnings include (isol) markers for isolated CPUs"""
        mock_instance = mock_systopo.return_value
        mock_instance.isolated_cpus.return_value = self.MOCK_ISOLATED_CPUS

        warnings = validate_core_sharing([0], [8], [2])

        self.assertGreater(len(warnings), 0, "Expected warnings")
        # Check that warnings mention isolated CPUs with (isol) marker
        self.assertTrue(any("(isol)" in w for w in warnings),
                       "Warnings should mark isolated CPUs with (isol)")

    @patch('rteval.systopology.SysTopology')
    def test_no_warnings_without_isolated_cpus(self, mock_systopo):
        """Test that no warnings are generated when no CPUs are isolated"""
        mock_instance = mock_systopo.return_value
        mock_instance.isolated_cpus.return_value = []  # No isolated CPUs

        # Even if CPUs share cores, no warnings if none are isolated
        warnings = validate_core_sharing([0], [8], [1])

        self.assertEqual(len(warnings), 0,
                        "Expected no warnings when no CPUs are isolated")


if __name__ == '__main__':
    unittest.main()
