import json
import os
from functools import lru_cache

from on_call_bot.configuration import LANG_ID


@lru_cache(maxsize=1)
def load_lang(lang_id: str):
    with open(f"{os.getcwd()}/langs/{lang_id}.json", "r") as langf:
        lang = json.load(langf)
    return lang


def get(field: str, default: str = None):
    return load_lang(LANG_ID).get(field, default) or field
