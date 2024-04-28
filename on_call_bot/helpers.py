from datetime import datetime

from on_call_bot import translator
from on_call_bot.configuration import TASKS_SHEET_NAMES
from on_call_bot.globals import persons
from on_call_bot.models import Person, Task
from on_call_bot.sheet_helpers import get_tasks_from_sheet


def generate_who_is_here_message(
    tasks: list[Task],
    here: list[str],
    not_here: list[Person],
    released_members: list[str],
    teams: dict,
) -> str:
    here_count = len([n for n in here if n not in released_members])
    msg = (translator.get("Count here", "%d is here ") % here_count)

    for task in tasks:
        members_description = " \n ".join([p.description for p in task.members])
        msg += f"\n*{task.task_name}:* \n {members_description} ֿ"

    tasks_members = [m.description for t in tasks for m in t.members]
    for team, members in teams.items():
        msg += f"\n\n*{team}*: ֿ"
        commander = True
        for member in members:
            person = persons[member]
            if person.description in here and not any(
                [
                    person.description in tasks_members,
                    person.description in [p.description for p in not_here],
                    person.description in released_members,
                ]
            ):
                if commander:
                    msg += f"\n\t{translator.get('Commander')} {person.description}"
                    commander = False
                else:
                    msg += f"\n\t{person.description}"

    if released_members:
        released_msg = f"\n\n{translator.get('Count released', '%d released')} \n" % len(released_members)
        msg += released_msg

        for person in released_members:
            msg += f"- {person}\n"

    return msg


def get_tasks(
    now: bool = False,
    person: Person = None,
    start_from: datetime = None,
    end_in: datetime = None,
) -> list[Task]:
    """Get all tasks sorted by start time"""
    tasks = []
    for sheet_name in TASKS_SHEET_NAMES:
        tasks.extend(
            get_tasks_from_sheet(
                sheet_name, now=now, person=person, start_from=start_from, end_in=end_in
            )
        )
    return list(sorted(tasks, key=lambda t: t.start))
