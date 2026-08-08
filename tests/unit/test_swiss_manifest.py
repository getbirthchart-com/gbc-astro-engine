from __future__ import annotations

import unittest

from gbc_astro.providers.swiss_manifest import manifest_summary


class SwissManifestTests(unittest.TestCase):
    def test_missing_core_files_errors_manifest(self) -> None:
        summary = manifest_summary(None)
        self.assertEqual(summary["status"], "error")
        self.assertIn("sepl_18.se1", summary["missingRequiredData"])
        self.assertIn("semo_18.se1", summary["missingRequiredData"])
        self.assertIn("seas_18.se1", summary["missingOptionalData"])


if __name__ == "__main__":
    unittest.main()
