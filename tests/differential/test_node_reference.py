"""Independent lunar-node reference tests.

The nodes are checked against their own defining properties and against the
independent reference, never against Swiss Ephemeris alone.
"""

from __future__ import annotations

import os
import unittest
from datetime import datetime, timezone

from gbc_astro.validation.astronomy import ASTRONOMY_BODIES, NODE_BODIES


def _jpl_available() -> bool:
    try:
        import skyfield  # noqa: F401
    except ImportError:
        return False
    path = os.environ.get("GBC_JPL_EPHEMERIS_PATH")
    return bool(path and os.path.exists(path))


def _swiss_available() -> bool:
    try:
        import swisseph  # noqa: F401
    except ImportError:
        return False
    path = os.environ.get("GBC_SWISS_EPHE_PATH")
    return bool(path and os.path.exists(os.path.join(path, "semo_18.se1")))


class NodeCoverageTests(unittest.TestCase):
    def test_both_nodes_are_in_the_astronomy_corpus(self) -> None:
        self.assertIn("true_node", ASTRONOMY_BODIES)
        self.assertIn("mean_node", ASTRONOMY_BODIES)
        self.assertEqual(set(NODE_BODIES), {"true_node", "mean_node"})


@unittest.skipUnless(
    _jpl_available() and _swiss_available(),
    "Node reference needs the JPL kernel and Swiss Ephemeris data",
)
class NodeReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from gbc_astro.validation.reference import JplReferenceSource

        cls.reference = JplReferenceSource()

    def _instant(self, iso: str) -> datetime:
        return datetime.fromisoformat(iso).replace(tzinfo=timezone.utc)

    def test_nodes_lie_exactly_on_the_ecliptic(self) -> None:
        """Both nodes are ecliptic points by definition, so latitude is exactly zero."""
        for body in NODE_BODIES:
            position = self.reference.body_position(body, self._instant("1992-11-03T07:35:00"))
            self.assertEqual(position.latitude_deg, 0.0, body)

    def test_mean_node_regresses_at_the_expected_rate(self) -> None:
        """The mean node completes a retrograde circuit in about 18.6 years."""
        first = self.reference.body_position("mean_node", self._instant("2000-01-01T00:00:00"))
        later = self.reference.body_position("mean_node", self._instant("2001-01-01T00:00:00"))

        travelled = (first.longitude_deg - later.longitude_deg) % 360.0
        self.assertAlmostEqual(travelled, 360.0 / 18.6, delta=0.5)

    def test_mean_node_is_always_retrograde(self) -> None:
        for iso in (
            "1901-06-15T00:00:00",
            "1955-03-02T12:00:00",
            "2000-01-01T00:00:00",
            "2024-09-30T18:00:00",
        ):
            position = self.reference.body_position("mean_node", self._instant(iso))
            self.assertTrue(position.retrograde, iso)

    def test_true_node_stays_near_the_mean_node(self) -> None:
        """The osculating node oscillates about the mean node by under two degrees."""
        for iso in (
            "1910-04-01T00:00:00",
            "1970-07-20T06:00:00",
            "2015-11-11T11:00:00",
            "2026-02-02T02:00:00",
        ):
            instant = self._instant(iso)
            true_node = self.reference.body_position("true_node", instant)
            mean_node = self.reference.body_position("mean_node", instant)

            separation = abs(
                (true_node.longitude_deg - mean_node.longitude_deg + 180.0) % 360.0 - 180.0
            )
            self.assertLess(separation, 2.0, iso)

    def test_unsupported_body_still_raises(self) -> None:
        from gbc_astro.errors import UnsupportedBodyError

        with self.assertRaises(UnsupportedBodyError):
            self.reference.body_position("chiron", self._instant("2000-01-01T00:00:00"))
