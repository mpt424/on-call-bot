import re

DATE_REGEX = r"(?P<day>\d{1,2})(\.|/)(?P<month>\d{1,2})((\.|/)(?P<year>\d{2,4}))?"
COMPILED_DATE_REGEX = re.compile(DATE_REGEX)
TIME_REGEX = r"(?P<hours>\d{2}):(?P<minutes>\d{2})"
TIME_RANGE_REGEX = rf"{DATE_REGEX}(\s{TIME_REGEX})?(\s*-\s*|$)?"
COMPILED_TIME_RANGE_REGEX = re.compile(TIME_RANGE_REGEX)

HEADERS_ROW_IDX = 0
DATA_ROW_IDX = 1
TASK_NAMES_IDX = 2
DATE_IDX = 0
TIME_IDX = 1
MEMBERS_IDX = 2
HEBREW_LANG_ID = "he-IL"
