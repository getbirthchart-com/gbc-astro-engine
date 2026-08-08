from __future__ import annotations

import unittest
from unittest.mock import patch

from gbc_astro.errors import ProviderDependencyError
from gbc_astro.houses.swiss import SwissHouseCalculator


class SwissHouseProviderTests(unittest.TestCase):
    def test_swiss_house_dependency_error_is_structured(self) -> None:
        target = "gbc_astro.houses.swiss.import_module"
        with patch(target, side_effect=ImportError), self.assertRaises(
            ProviderDependencyError
        ) as raised:
            SwissHouseCalculator()
        self.assertEqual(raised.exception.code, "PROVIDER_DEPENDENCY_MISSING")


if __name__ == "__main__":
    unittest.main()
