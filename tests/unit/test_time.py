from __future__ import annotations

import unittest
from datetime import datetime, timezone

from gbc_astro.astronomy.time import datetime_to_julian_day, normalize_local_datetime
from gbc_astro.errors import AmbiguousLocalTimeError, NonexistentLocalTimeError


class TimeNormalizationTests(unittest.TestCase):
    def test_known_utc_conversion(self) -> None:
        normalized = normalize_local_datetime(
            datetime(1992, 11, 3, 14, 35),
            "Asia/Ho_Chi_Minh",
        )
        self.assertEqual(normalized.utc_datetime.isoformat(), "1992-11-03T07:35:00+00:00")

    def test_julian_day_reference(self) -> None:
        jd = datetime_to_julian_day(datetime(2000, 1, 1, 12, tzinfo=timezone.utc))
        self.assertEqual(jd, 2451545.0)

    def test_nonexistent_dst_time(self) -> None:
        with self.assertRaises(NonexistentLocalTimeError):
            normalize_local_datetime(datetime(2024, 3, 10, 2, 30), "America/New_York")

    def test_ambiguous_dst_time_requires_fold(self) -> None:
        with self.assertRaises(AmbiguousLocalTimeError):
            normalize_local_datetime(datetime(2024, 11, 3, 1, 30), "America/New_York")

        first = normalize_local_datetime(datetime(2024, 11, 3, 1, 30), "America/New_York", fold=0)
        second = normalize_local_datetime(datetime(2024, 11, 3, 1, 30), "America/New_York", fold=1)
        self.assertNotEqual(first.utc_datetime, second.utc_datetime)


if __name__ == "__main__":
    unittest.main()
