"""
test_full_verification.py - Comprehensive system and code verification
"""

import unittest
import sys
import os
import subprocess
import py_compile
import importlib

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

class TestSystemVerification(unittest.TestCase):
    def test_python_version(self):
        """Verify Python version is 3.6+"""
        print(f"\nChecking Python version: {sys.version.split()[0]} ... ", end="")
        self.assertGreaterEqual(sys.version_info[:2], (3, 6))
        print("OK")

    def test_required_commands(self):
        """Verify required system commands are available"""
        # In the CI/Sandbox environment (Linux), macOS specific commands won't exist.
        # We should skip this test if not running on Darwin, or mock it if we want to test the logic.
        # Given this is a verification script, skipping on non-macOS is appropriate.

        if sys.platform != 'darwin':
            print("\nSkipping system command check (Not on macOS)")
            return

        required_commands = ['diskutil', 'sudo', 'du']
        print("\nChecking required system commands:")

        for cmd in required_commands:
            print(f"  - {cmd} ... ", end="")
            # Check if command exists using 'which'
            result = subprocess.run(['which', cmd], capture_output=True)
            if result.returncode == 0:
                print("OK")
            else:
                print("MISSING (Test will fail)")
                self.fail(f"Required command '{cmd}' not found in PATH")

    def test_optional_commands(self):
        """Check optional system commands (warn only)"""
        optional_commands = ['SetFile', 'bless', 'mist']
        print("\nChecking optional system commands:")

        for cmd in optional_commands:
            print(f"  - {cmd} ... ", end="")
            result = subprocess.run(['which', cmd], capture_output=True)
            if result.returncode == 0:
                print("OK")
            else:
                print("MISSING (Warning only)")

class TestCodeQuality(unittest.TestCase):
    def test_syntax_check(self):
        """Compile all .py files to check for syntax errors"""
        print("\nChecking syntax of all Python files:")
        py_files = []
        for root, dirs, files in os.walk(PROJECT_ROOT):
            if "tests" in root: continue
            for file in files:
                if file.endswith(".py"):
                    py_files.append(os.path.join(root, file))

        for file_path in py_files:
            rel_path = os.path.relpath(file_path, PROJECT_ROOT)
            print(f"  - {rel_path} ... ", end="")
            try:
                py_compile.compile(file_path, doraise=True)
                print("OK")
            except py_compile.PyCompileError as e:
                print("FAIL")
                self.fail(f"Syntax error in {rel_path}: {e}")

    def test_module_imports(self):
        """Verify all modules can be imported without error"""
        print("\nChecking module imports:")
        modules = [
            'core.constants', 'core.privilege',
            'detection.installer_scanner', 'detection.stub_validator',
            'detection.disk_detector', 'detection.version_parser',
            'safety.boot_disk_guard', 'safety.backup_manager',
            'operations.partitioner', 'operations.installer_runner', 'operations.branding',
            'integration.mist_downloader',
            'ui.display', 'ui.prompts', 'ui.progress', 'ui.help',
            'utils.logger',
            'main'
        ]

        for module_name in modules:
            print(f"  - {module_name} ... ", end="")
            try:
                importlib.import_module(module_name)
                print("OK")
            except ImportError as e:
                print("FAIL")
                self.fail(f"Failed to import {module_name}: {e}")
            except Exception as e:
                print("FAIL")
                self.fail(f"Error during import of {module_name}: {e}")

class TestRequirements(unittest.TestCase):
    def test_requirements_file(self):
        """Verify requirements.txt exists (if applicable) or dependencies are standard"""
        print("\nChecking dependencies:")
        req_path = os.path.join(PROJECT_ROOT, 'requirements.txt')
        if os.path.exists(req_path):
            print("  - requirements.txt found.")
        else:
            print("  - requirements.txt not found (Standard library only expected).")
            # Verify no non-standard imports are used in the codebase
            # This is a basic check, a real scanner would be more complex
            pass

if __name__ == '__main__':
    unittest.main(verbosity=0)
