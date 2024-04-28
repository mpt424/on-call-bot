from datetime import datetime
from enum import Enum

from pydantic import BaseModel

from on_call_bot.configuration import LANG_ID
from on_call_bot.consts import HEBREW_LANG_ID
from on_call_bot.utils import get_hebrew_weekday


class StatusName(Enum):
    here = "נוכח"
    out = "בחוץ"
    short_out = "בחוץ (יציאה זמנית)"
    released = "באפטר"


class Status(BaseModel):
    status_name: StatusName | None = StatusName.here
    update_time: datetime | None = datetime.now()


class Person(BaseModel):
    row: int
    name: str
    phone: str
    team: str | None = None
    email: str | None = None
    status: Status | None = Status
    chat_id: int = None

    @property
    def description(self):
        return f"{self.name} {self.phone}"


class Task(BaseModel):
    task_name: str
    row: int
    cols: list[int]
    sheet_index: int
    sheet: str
    members: list[Person] | None = []
    start: datetime
    end: datetime

    @property
    def members_description(self):
        return [m.description for m in self.members]

    def description(self, with_time: bool = True):
        if with_time:
            weekday = (
                get_hebrew_weekday(self.start.weekday())
                if LANG_ID == HEBREW_LANG_ID
                else self.start.strftime("%A")
            )
            return "%s %s %s - %s" % (
                self.task_name,
                weekday,
                self.start.strftime("%d.%m.%y %H:%M"),
                self.end.strftime("%H:%M"),
            )

        return self.task_name
