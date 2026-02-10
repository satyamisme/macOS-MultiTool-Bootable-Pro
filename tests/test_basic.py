"""
test_basic.py - Basic functionality tests for logic modules
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import constants
from detection import stub_validator, version_parser

class TestBasics(unittest.TestCase):
    def test_partition_calc_sonoma(self):
        # Sonoma (14.0) ~13GB -> KB
        size_kb = 13 * 1024 * 1024
        size_gb = constants.calculate_partition_size(size_kb, "14.0")
        # 13 + 1.3 (overhead) + 1 (boot) + 2.2 (buffer) = ~17.5 -> 18GB
        self.assertGreaterEqual(size_gb, 17)
        self.assertLessEqual(size_gb, 20)

    def test_partition_calc_sequoia_beta(self):
        # Sequoia (15.0) ~14GB -> KB
        size_kb = 14 * 1024 * 1024
        size_gb = constants.calculate_partition_size(size_kb, "15.0 Beta 2")
        # 14 + 1.4 + 1 + 2.5 = ~18.9 -> 19GB
        self.assertGreaterEqual(size_gb, 18)
        self.assertLessEqual(size_gb, 22)

    def test_version_parsing(self):
        self.assertEqual(version_parser.parse_version("14.6.1"), (14, 6, 1))
        self.assertEqual(version_parser.parse_version("15.0 Beta 3"), (15, 0, 0))
        self.assertEqual(version_parser.parse_version("10.15.7-RC"), (10, 15, 7))

    def test_version_extraction(self):
        self.assertEqual(constants._extract_version_key("14.6.1"), "14")
        self.assertEqual(constants._extract_version_key("15.2 Beta"), "15")
        self.assertEqual(constants._extract_version_key("10.15.7"), "10.15")

if __name__ == '__main__':
    unittest.main()
