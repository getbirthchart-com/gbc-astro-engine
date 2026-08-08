"""Solver tests against analytic functions.

Checked against closed-form roots rather than the ephemeris, so a failure here
is a solver failure and nothing else.
"""

from __future__ import annotations

import math
import unittest

from gbc_astro.search.solver import (
    DEFAULT_TOLERANCE_DAYS,
    SECONDS_PER_DAY,
    find_roots,
)


class RootFindingTests(unittest.TestCase):
    def test_finds_a_single_linear_root(self) -> None:
        roots = find_roots(lambda x: x - 2.5, 0.0, 10.0, coarse_step_days=1.0)
        self.assertEqual(len(roots), 1)
        self.assertAlmostEqual(roots[0].julian_day, 2.5, places=6)

    def test_finds_every_root_of_a_periodic_function(self) -> None:
        """sin(pi x) is zero at every integer; the window holds nine interior ones."""
        roots = find_roots(
            lambda x: math.sin(math.pi * x), 0.5, 9.5, coarse_step_days=0.25
        )
        located = [round(root.julian_day, 6) for root in roots]
        self.assertEqual(located, [float(value) for value in range(1, 10)])

    def test_reports_precision_it_actually_achieved(self) -> None:
        roots = find_roots(lambda x: x - 2.5, 0.0, 10.0, coarse_step_days=1.0)
        self.assertLessEqual(
            roots[0].precision_seconds, DEFAULT_TOLERANCE_DAYS * SECONDS_PER_DAY * 2
        )
        self.assertLess(abs(roots[0].residual), 1e-6)

    def test_bracket_is_recorded_for_audit(self) -> None:
        roots = find_roots(lambda x: x - 2.5, 0.0, 10.0, coarse_step_days=1.0)
        root = roots[0]
        self.assertLessEqual(root.bracket_start, root.julian_day)
        self.assertGreaterEqual(root.bracket_end, root.julian_day)
        self.assertGreater(root.iterations, 0)

    def test_a_coarse_step_that_straddles_two_roots_is_a_known_limitation(self) -> None:
        """Two roots inside one step cancel: the step must suit the quantity.

        This is why `events.py` keeps a per-body table instead of one default.
        """
        missed = find_roots(lambda x: math.sin(math.pi * x), 0.5, 9.5, coarse_step_days=2.0)
        found = find_roots(lambda x: math.sin(math.pi * x), 0.5, 9.5, coarse_step_days=0.25)
        self.assertLess(len(missed), len(found))

    def test_no_roots_when_the_function_never_crosses(self) -> None:
        self.assertEqual(find_roots(lambda x: x * x + 1.0, 0.0, 10.0, 1.0), ())

    def test_a_touching_root_without_sign_change_is_invisible_to_bracketing(self) -> None:
        """x^2 touches zero without crossing, so no bracket ever forms.

        This is exactly why an aspect search targets the two exact longitudes
        rather than the separation, which touches zero the same way. The window
        starts at 0.1 so no sample lands exactly on the root, which would be
        found as a genuine zero rather than by bracketing.
        """
        self.assertEqual(find_roots(lambda x: (x - 5.0) ** 2, 0.1, 10.0, 0.5), ())

    def test_a_sample_landing_exactly_on_zero_is_still_reported(self) -> None:
        """An exact zero is a root even when no sign change surrounds it."""
        roots = find_roots(lambda x: (x - 5.0) ** 2, 0.0, 10.0, 0.5)
        self.assertEqual(len(roots), 1)
        self.assertEqual(roots[0].julian_day, 5.0)
        self.assertEqual(roots[0].residual, 0.0)

    def test_wraps_are_rejected_when_a_threshold_is_given(self) -> None:
        """A sawtooth jumping -180 to +180 is a wrap, not nine crossings."""

        def sawtooth(x: float) -> float:
            return ((x * 100.0 + 180.0) % 360.0) - 180.0

        without = find_roots(sawtooth, 0.0, 9.0, coarse_step_days=0.05)
        with_threshold = find_roots(
            sawtooth, 0.0, 9.0, coarse_step_days=0.05, discontinuity_threshold=180.0
        )
        self.assertGreater(len(without), len(with_threshold))

    def test_adjacent_detections_of_one_event_are_merged(self) -> None:
        roots = find_roots(
            lambda x: x - 2.5, 0.0, 10.0, coarse_step_days=0.001, dedupe_days=1.0
        )
        self.assertEqual(len(roots), 1)

    def test_empty_or_inverted_windows_return_nothing(self) -> None:
        self.assertEqual(find_roots(lambda x: x, 5.0, 5.0, 1.0), ())
        self.assertEqual(find_roots(lambda x: x, 5.0, 1.0, 1.0), ())

    def test_a_non_positive_step_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            find_roots(lambda x: x, 0.0, 10.0, coarse_step_days=0.0)

    def test_roots_come_back_in_time_order(self) -> None:
        roots = find_roots(lambda x: math.sin(math.pi * x), 0.5, 9.5, 0.25)
        times = [root.julian_day for root in roots]
        self.assertEqual(times, sorted(times))
