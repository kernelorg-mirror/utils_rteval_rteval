#!/usr/bin/python3
# SPDX-License-Identifier: GPL-2.0-or-later
#
# Unit test for --measurement-module command-line argument
#
# This test verifies that the --measurement-module argument correctly
# overrides config file settings to select between cyclictest and timerlat.
#

import sys
import os
import unittest
import argparse

# Add rteval to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rteval import rtevalConfig
from rteval.Log import Log


class TestMeasurementModuleSelection(unittest.TestCase):
    """Test suite for measurement module selection via command-line argument"""

    def setUp(self):
        """Set up test fixtures"""
        self.logger = Log()
        self.logger.SetLogVerbosity(Log.NONE)

    def test_default_config_file_selection(self):
        """Test that config file settings are loaded correctly by default"""
        config = rtevalConfig.rtevalConfig(logger=self.logger)

        # Load the rteval.conf file (which currently has timerlat enabled)
        config_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'rteval.conf')
        if os.path.exists(config_file):
            config.Load(config_file)
            msrcfg = config.GetSection('measurement')

            # Based on current rteval.conf, timerlat should be set to 'module'
            timerlat_value = getattr(msrcfg, 'timerlat', None)
            self.assertEqual(timerlat_value, 'module',
                           "timerlat should be set to 'module' in rteval.conf")

    def test_override_with_cyclictest(self):
        """Test that --measurement-module cyclictest overrides config file"""
        config = rtevalConfig.rtevalConfig(logger=self.logger)
        config.AppendConfig('measurement', {
            'timerlat': 'module',
            'sysstat': 'module'
        })

        # Simulate the early argument parser
        measurement_parser = argparse.ArgumentParser(add_help=False)
        measurement_parser.add_argument('--measurement-module', dest='measurement_module',
                                        type=str, choices=['cyclictest', 'timerlat'])
        early_args, _ = measurement_parser.parse_known_args(['--measurement-module', 'cyclictest'])

        # Apply the override logic (same as in rteval-cmd)
        if early_args.measurement_module:
            msrcfg = config.GetSection('measurement')
            if 'cyclictest' in msrcfg:
                msrcfg.cyclictest = None
            if 'timerlat' in msrcfg:
                msrcfg.timerlat = None
            setattr(msrcfg, early_args.measurement_module, 'module')

        # Verify the results
        msrcfg = config.GetSection('measurement')
        cyclictest_value = getattr(msrcfg, 'cyclictest', None)
        timerlat_value = getattr(msrcfg, 'timerlat', None)

        self.assertEqual(cyclictest_value, 'module',
                        "cyclictest should be enabled after override")
        self.assertNotEqual(timerlat_value, 'module',
                           "timerlat should be disabled after override")

    def test_override_with_timerlat(self):
        """Test that --measurement-module timerlat overrides config file"""
        config = rtevalConfig.rtevalConfig(logger=self.logger)
        config.AppendConfig('measurement', {
            'cyclictest': 'module',
            'sysstat': 'module'
        })

        # Simulate the early argument parser
        measurement_parser = argparse.ArgumentParser(add_help=False)
        measurement_parser.add_argument('--measurement-module', dest='measurement_module',
                                        type=str, choices=['cyclictest', 'timerlat'])
        early_args, _ = measurement_parser.parse_known_args(['--measurement-module', 'timerlat'])

        # Apply the override logic (same as in rteval-cmd)
        if early_args.measurement_module:
            msrcfg = config.GetSection('measurement')
            if 'cyclictest' in msrcfg:
                msrcfg.cyclictest = None
            if 'timerlat' in msrcfg:
                msrcfg.timerlat = None
            setattr(msrcfg, early_args.measurement_module, 'module')

        # Verify the results
        msrcfg = config.GetSection('measurement')
        cyclictest_value = getattr(msrcfg, 'cyclictest', None)
        timerlat_value = getattr(msrcfg, 'timerlat', None)

        self.assertEqual(timerlat_value, 'module',
                        "timerlat should be enabled after override")
        self.assertNotEqual(cyclictest_value, 'module',
                           "cyclictest should be disabled after override")

    def test_no_override_when_argument_not_provided(self):
        """Test that config file settings remain when argument is not provided"""
        config = rtevalConfig.rtevalConfig(logger=self.logger)
        config.AppendConfig('measurement', {
            'timerlat': 'module',
            'sysstat': 'module'
        })

        # Simulate the early argument parser with no --measurement-module argument
        measurement_parser = argparse.ArgumentParser(add_help=False)
        measurement_parser.add_argument('--measurement-module', dest='measurement_module',
                                        type=str, choices=['cyclictest', 'timerlat'])
        early_args, _ = measurement_parser.parse_known_args([])

        # Only apply override if argument was provided
        if early_args.measurement_module:
            msrcfg = config.GetSection('measurement')
            if 'cyclictest' in msrcfg:
                msrcfg.cyclictest = None
            if 'timerlat' in msrcfg:
                msrcfg.timerlat = None
            setattr(msrcfg, early_args.measurement_module, 'module')

        # Verify the results - should remain unchanged
        msrcfg = config.GetSection('measurement')
        timerlat_value = getattr(msrcfg, 'timerlat', None)

        self.assertEqual(timerlat_value, 'module',
                        "timerlat should remain enabled when no override is provided")

    def test_argparse_rejects_invalid_module(self):
        """Test that argparse rejects invalid module names"""
        measurement_parser = argparse.ArgumentParser(add_help=False)
        measurement_parser.add_argument('--measurement-module', dest='measurement_module',
                                        type=str, choices=['cyclictest', 'timerlat'])

        # This should raise SystemExit due to invalid choice
        with self.assertRaises(SystemExit):
            measurement_parser.parse_args(['--measurement-module', 'invalid'])

    def test_both_modules_disabled_after_override(self):
        """Test that both modules are disabled when one is selected"""
        config = rtevalConfig.rtevalConfig(logger=self.logger)
        config.AppendConfig('measurement', {
            'cyclictest': 'module',
            'timerlat': 'module',
            'sysstat': 'module'
        })

        # Override with cyclictest
        measurement_parser = argparse.ArgumentParser(add_help=False)
        measurement_parser.add_argument('--measurement-module', dest='measurement_module',
                                        type=str, choices=['cyclictest', 'timerlat'])
        early_args, _ = measurement_parser.parse_known_args(['--measurement-module', 'cyclictest'])

        if early_args.measurement_module:
            msrcfg = config.GetSection('measurement')
            if 'cyclictest' in msrcfg:
                msrcfg.cyclictest = None
            if 'timerlat' in msrcfg:
                msrcfg.timerlat = None
            setattr(msrcfg, early_args.measurement_module, 'module')

        # Verify exactly one is enabled
        msrcfg = config.GetSection('measurement')
        cyclictest_value = getattr(msrcfg, 'cyclictest', None)
        timerlat_value = getattr(msrcfg, 'timerlat', None)

        enabled_count = sum([
            1 if cyclictest_value == 'module' else 0,
            1 if timerlat_value == 'module' else 0
        ])

        self.assertEqual(enabled_count, 1,
                        "Exactly one measurement module should be enabled")


def main():
    """Run the test suite"""
    # Run tests with verbosity
    unittest.main(verbosity=2)


if __name__ == '__main__':
    main()
