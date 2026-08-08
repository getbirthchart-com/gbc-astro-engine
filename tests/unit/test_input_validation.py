from __future__ import annotations

import unittest

from gbc_astro.errors import InvalidCoordinateError, UnknownBirthTimeError
from gbc_astro.models.input import ChartInput


class InputValidationTests(unittest.TestCase):
    def test_invalid_latitude(self) -> None:
        with self.assertRaises(InvalidCoordinateError):
            ChartInput.from_public(
                local_datetime="1992-11-03T14:35:00",
                timezone="Asia/Ho_Chi_Minh",
                latitude=91.0,
                longitude=105.8542,
            )

    def test_invalid_longitude(self) -> None:
        with self.assertRaises(InvalidCoordinateError):
            ChartInput.from_public(
                local_datetime="1992-11-03T14:35:00",
                timezone="Asia/Ho_Chi_Minh",
                latitude=21.0285,
                longitude=181.0,
            )

    def test_unknown_time_rejects_time_component(self) -> None:
        with self.assertRaises(UnknownBirthTimeError):
            ChartInput.from_public(
                local_datetime="1992-11-03T14:35:00",
                timezone="Asia/Ho_Chi_Minh",
                latitude=21.0285,
                longitude=105.8542,
                birth_time_known=False,
            )


if __name__ == "__main__":
    unittest.main()

