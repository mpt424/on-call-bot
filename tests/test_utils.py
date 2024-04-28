from datetime import datetime

import pytest

from on_call_bot.utils import extract_and_convert_to_datetime_range


@pytest.mark.parametrize(
    "datetime_range_value, expected_result",
    [
        (
            "10.3.2024 07:00 - 12.3.2024 08:00",
            (datetime(2024, 3, 10, 7, 00), datetime(2024, 3, 12, 8, 00)),
        ),
        (
            "10.3.2024 07:00-12.3.2024 08:00",
            (datetime(2024, 3, 10, 7, 00), datetime(2024, 3, 12, 8, 00)),
        ),
        (
            "10.3 07:00 - 12.3 08:00",
            (datetime(2024, 3, 10, 7, 00), datetime(2024, 3, 12, 8, 00)),
        ),
        (
            "10.3.2024 - 12.3.2024",
            (datetime(2024, 3, 10, 00, 00), datetime(2024, 3, 12, 00, 00)),
        ),
        ("10.3 - 12.3", (datetime(2024, 3, 10, 00, 00), datetime(2024, 3, 12, 00, 00))),
        ("10.3.2024", (datetime(2024, 3, 10, 00, 00), datetime(2024, 3, 11, 00, 00))),
        ("10.3", (datetime(2024, 3, 10, 00, 00), datetime(2024, 3, 11, 00, 00))),
    ],
)
def test_extract_and_convert_to_datetime_range(datetime_range_value, expected_result):
    assert (
        extract_and_convert_to_datetime_range(datetime_range_value) == expected_result
    )
