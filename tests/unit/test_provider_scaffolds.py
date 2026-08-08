from __future__ import annotations

import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from gbc_astro.errors import ProviderDependencyError
from gbc_astro.providers.jpl import JplEphemerisProvider
from gbc_astro.providers.swiss import SwissEphemerisProvider


class ProviderScaffoldTests(unittest.TestCase):
    def test_swiss_dependency_error_is_structured(self) -> None:
        target = "gbc_astro.providers.swiss.import_module"
        with patch(target, side_effect=ImportError), self.assertRaises(
            ProviderDependencyError
        ) as raised:
            SwissEphemerisProvider()
        self.assertEqual(raised.exception.code, "PROVIDER_DEPENDENCY_MISSING")

    def test_swiss_moshier_fallback_is_rejected(self) -> None:
        fake_swe = SimpleNamespace(
            SUN=0,
            MOON=1,
            MERCURY=2,
            VENUS=3,
            MARS=4,
            JUPITER=5,
            SATURN=6,
            URANUS=7,
            NEPTUNE=8,
            PLUTO=9,
            TRUE_NODE=10,
            MEAN_NODE=11,
            CHIRON=12,
            FLG_SWIEPH=2,
            FLG_MOSEPH=4,
            FLG_SPEED=256,
            version="test",
            set_ephe_path=lambda _path: None,
            calc_ut=lambda _jd, _body, _flags: ((0.0, 0.0, 1.0, 0.0), 260),
        )
        target = "gbc_astro.providers.swiss.import_module"
        with patch(target, return_value=fake_swe), self.assertRaises(
            ProviderDependencyError
        ) as raised:
            SwissEphemerisProvider().position("sun", datetime(2024, 1, 1, tzinfo=timezone.utc))
        self.assertEqual(raised.exception.code, "PROVIDER_DEPENDENCY_MISSING")

    def test_jpl_scaffold_declares_capabilities_but_does_not_calculate(self) -> None:
        provider = JplEphemerisProvider()
        self.assertTrue(provider.supports_body("sun"))
        self.assertFalse(provider.capabilities.supports_speed)
        with self.assertRaises(ProviderDependencyError):
            provider.position("sun", datetime(2024, 1, 1, tzinfo=timezone.utc))


if __name__ == "__main__":
    unittest.main()
