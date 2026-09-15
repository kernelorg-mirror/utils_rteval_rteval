#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright 2026 Sana Sharma <sansshar@redhat.com>
""" Unit tests for the new stressng input validation """

import sys
import subprocess
import unittest
from unittest.mock import patch, MagicMock
sys.path.insert(0,'.')
from rteval.modules.loads import stressng

class TestGetValidStressors(unittest.TestCase):
    """Test suite for the function get_valid_stressors"""

    @patch('rteval.modules.loads.stressng.subprocess.run')
    def test_parses_stressor_list(self, mock_run):
        """Test parsing a valid stress-ng stressor list"""
        mock_run.return_value = MagicMock(stdout="cpu vm matrix\n")
        self.assertEqual(stressng.get_valid_stressors(), ['cpu', 'vm', 'matrix'])

    @patch('rteval.modules.loads.stressng.subprocess.run',
           side_effect=FileNotFoundError)
    def test_not_installed_exits(self, _):
        """Test when stress-ng is not installed"""
        with self.assertRaises(SystemExit) as cm:
            stressng.get_valid_stressors()
        self.assertEqual(cm.exception.code, 1)

    @patch('rteval.modules.loads.stressng.subprocess.run',
           side_effect=subprocess.CalledProcessError(1, 'stress-ng'))
    def test_query_failure_exits(self, _):
        """Test when the stress-ng query fails"""
        with self.assertRaises(SystemExit):
            stressng.get_valid_stressors()

class TestValidateStressor(unittest.TestCase):
    """Test suite for the function validate_stressor"""

    @patch('rteval.modules.loads.stressng.get_valid_stressors',
           return_value=['cpu', 'vm'])
    def test_valid_passes(self, _):
        """Test that a valid stressor is accepted"""
        stressng.validate_stressor('cpu')   # should not raise

    @patch('rteval.modules.loads.stressng.get_valid_stressors',
           return_value=['cpu', 'vm'])
    def test_invalid_exits(self, _):
        """Test that an invalid stressor is rejected"""
        with self.assertRaises(SystemExit) as cm:
            stressng.validate_stressor('bogus')
        self.assertEqual(cm.exception.code, 1)

def main():
    """Run the test suite"""
    unittest.main(verbosity=2)

if __name__ == '__main__':
    main()
