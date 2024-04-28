import urllib
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timedelta
from re import Match

import pytz
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from on_call_bot import translator
from on_call_bot.consts import COMPILED_DATE_REGEX, COMPILED_TIME_RANGE_REGEX

return_button = InlineKeyboardButton(
    translator.get("Back to main menu"), callback_data="return_main"
)
return_keyboard = [[return_button]]
return_menu_markup = InlineKeyboardMarkup(return_keyboard)


def index_strings(input_list: list[str]):
    index_dict = defaultdict(list)
    for idx, string in enumerate(input_list):
        index_dict[string].append(idx)
    return index_dict


def parse_times(time_value: str) -> dict:
    """
    Getting time value to parse into start and end time
    :param time_value: time range value should looks like HH:mm-HH:mm
    :return: dict of start time and end time
    """
    if not time_value:
        return {
            "start": {
                "hours": 0,
                "minutes": 0,
            },
            "end": {
                "hours": 23,
                "minutes": 59,
            },
        }
    parse_time_value = deepcopy(time_value)
    # if time_value == "בוקר":
    #     parse_time_value = "07:00-22:00"
    # elif time_value == "לילה":
    #     parse_time_value = "22:00-07:00"

    start_time, end_time = parse_time_value.split("-")
    start_hrs, start_min = start_time.split(":")
    end_hrs, end_min = end_time.split(":")
    return {
        "start": {
            "hours": int(start_hrs),
            "minutes": int(start_min),
        },
        "end": {
            "hours": int(end_hrs),
            "minutes": int(end_min),
        },
    }


def extract_and_convert_to_datetime(
    date_value, time_value
) -> tuple[datetime, datetime] | tuple[None, None]:
    parsed_times = parse_times(time_value)
    # Convert the matched date string to a datetime object
    try:
        formatted_date = parse_datetime(date_value)
        start_time = datetime(
            formatted_date.year,
            formatted_date.month,
            formatted_date.day,
            parsed_times["start"]["hours"],
            parsed_times["start"]["minutes"],
        )
        end_time = datetime(
            formatted_date.year,
            formatted_date.month,
            formatted_date.day,
            parsed_times["end"]["hours"],
            parsed_times["end"]["minutes"],
        )

        # crossed day case
        if end_time < start_time:
            end_time = end_time + timedelta(days=1)
        return start_time, end_time
    except ValueError:
        # Handle the case where the date string doesn't match the expected format
        print("Error: Invalid date format.")
        return None, None


def get_datetime_from_match(datetime_match: Match) -> datetime:
    hours = datetime_match.group("hours") or "00"
    minutes = datetime_match.group("minutes") or "00"
    date_value = (
        f"{datetime_match.group('day')}.{datetime_match.group('month')}.{get_year(datetime_match.group('year'))} "
        f"{hours}:{minutes}"
    )
    date_obj = datetime.strptime(date_value, "%d.%m.%Y %H:%M")
    return date_obj


def extract_and_convert_to_datetime_range(
    datetime_range_value: str,
) -> tuple[datetime, datetime] | None:
    matches = list(COMPILED_TIME_RANGE_REGEX.finditer(datetime_range_value))
    start_datetime_match = matches[0]
    start_date = get_datetime_from_match(start_datetime_match)
    end_date = start_date + timedelta(days=1)
    if len(matches) > 1:
        end_date = get_datetime_from_match(matches[1])

    return start_date, end_date


def get_hebrew_weekday(weekday: int) -> str:
    hebrew_days = {
        6: "יום ראשון",  # Sunday
        0: "יום שני",  # Monday
        1: "יום שלישי",  # Tuesday
        2: "יום רביעי",  # Wednesday
        3: "יום חמישי",  # Thursday
        4: "יום שישי",  # Friday
        5: "יום שבת",  # Saturday
    }
    return hebrew_days[weekday]


def convert_to_gmt2(dt):
    # Convert datetime to GMT+2
    gmt2_tz = pytz.timezone("Europe/Bucharest")
    dt_gmt2 = dt.astimezone(gmt2_tz)
    return dt_gmt2


def next_interval_time(start_time: datetime, interval_val: int) -> datetime:
    rounded_time = deepcopy(start_time)
    while rounded_time < datetime.now():
        rounded_time += timedelta(hours=interval_val)
    return rounded_time


def create_google_calendar_link(title, description, start_time, end_time):
    # Format start_time and end_time to strings in the required format
    start_time_str = start_time.strftime("%Y%m%dT%H%M%S")
    end_time_str = end_time.strftime("%Y%m%dT%H%M%S")

    # Encode the description for the URL
    encoded_title = urllib.parse.quote(title)
    encoded_description = urllib.parse.quote(description)
    # Google Calendar event creation link format
    calendar_link = (
        f"https://www.google.com/calendar/event?action=TEMPLATE&text={encoded_title}&"
        f"details={encoded_description}&"
        f"dates={start_time_str}/{end_time_str}"
    )

    return calendar_link


def convert_to_markdown(input_text: str) -> str:
    return (
        input_text.replace(".", "\\.")
        .replace("-", "\\-")
        .replace("=", "\\=")
        .replace("!", "\\!")
    )


def get_year(year_match) -> int:
    if not year_match:
        return datetime.today().year

    if len(year_match) == 4:
        return int(year_match)

    return int(year_match) + 2000


def parse_datetime(date_value: str) -> datetime:
    match = COMPILED_DATE_REGEX.search(date_value)
    return datetime(
        day=int(match.group("day")),
        month=int(match.group("month")),
        year=get_year(match.group("year")),
    )
