
import unittest
import os
import shutil
import tempfile
from detection import stub_validator

class TestStubValidator(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.app_path = os.path.join(self.test_dir, "Install macOS High Sierra.app")
        os.makedirs(os.path.join(self.app_path, "Contents/SharedSupport"))

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_missing_shared_support_but_large_total_size(self):
        # Create a dummy large file to simulate > 4GB size without SharedSupport.dmg
        # (We won't actually create 4GB file, but we'll mock the check)

        # Scenario: SharedSupport.dmg is missing.
        # But BaseSystem.dmg exists.
        base_system = os.path.join(self.app_path, "Contents/SharedSupport/BaseSystem.dmg")
        with open(base_system, "wb") as f:
            f.write(b"0" * 1024 * 1024 * 500) # 500MB

        # The current buggy code returns True (Stub) immediately if SharedSupport.dmg is missing.
        # It SHOULD return False (Full) because BaseSystem exists.

        is_stub = stub_validator.is_stub_installer(self.app_path)
        print(f"Is stub: {is_stub}")

        # We expect False (Not a stub)
        self.assertFalse(is_stub, "Should be FULL installer because BaseSystem.dmg exists")

if __name__ == "__main__":
    unittest.main()
