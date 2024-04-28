from os import getenv

from on_call_bot.consts import HEBREW_LANG_ID

# your bot token given by telegram father bot (https://telegram.me/BotFather)
TOKEN = getenv("BOT_TOKEN")

# bot language id - you must add your own lang file to langs dir if you want something else
LANG_ID = getenv("LANG_ID", HEBREW_LANG_ID)

# Google sheet settings
SHEET_URL = getenv("SHEET_URL")  # google sheet url
SERVICE_ACCOUNT_JSON = getenv("SERVICE_ACCOUNT_JSON")  # path to google sheet credentials file
RELEASES_SHEET_NAME = getenv("RELEASES_SHEET_NAME", "releases")  # sheet that present person releases
PERSONS_SHEET_NAME = getenv("PERSONS_SHEET_NAME", "persons")  # sheet that present list ofp persons
TEAMS_SHEET_NAME = getenv("TEAMS_SHEET_NAME", "teams")  # sheet that team division

# LIST of sheet names that present tasks shifts (seperated by comma)
TASKS_SHEET_NAMES = getenv("TASKS_SHEET_NAMES", "tasks").split(",")

# List of commander names
COMMANDERS = getenv("COMMANDERS", "").split(",")

# List of developers telegram account id
DEVELOPERS = getenv("DEVELOPERS", "").split(",")

# Minimum persons to stay on call
MIN_IN = int(getenv("MIN_IN", 20))

# Max persons to make a short out
MAX_SHORT_OUT = int(getenv("MAX_SHORT_OUT", 5))

# Auto remind iteration (hours)
REMIND_SHORT_OUT_HRS = int(getenv("REMIND_SHORT_HRS", 2))
REMIND_LONG_OUT_HRS = int(getenv("REMIND_LONG_OUT_HRS", 4))

# Main channel to send updates
MAIN_CHANNEL_ID = getenv("MAIN_CHANNEL_ID", "main_channel_id")

# Dev channel to send logs
DEV_CHANNEL_ID = getenv("DEV_CHANNEL_ID", "dev_channel_id")

