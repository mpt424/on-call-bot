import logging
from datetime import datetime

import gspread

from on_call_bot.configuration import (
    PERSONS_SHEET_NAME,
    RELEASES_SHEET_NAME,
    SERVICE_ACCOUNT_JSON,
    SHEET_URL,
    TEAMS_SHEET_NAME,
)
from on_call_bot.consts import (
    DATA_ROW_IDX,
    DATE_IDX,
    HEADERS_ROW_IDX,
    MEMBERS_IDX,
    TASK_NAMES_IDX,
    TIME_IDX,
)
from on_call_bot.globals import persons
from on_call_bot.models import Person, Status, StatusName, Task
from on_call_bot.utils import extract_and_convert_to_datetime, index_strings

gc = gspread.service_account(filename=SERVICE_ACCOUNT_JSON)
sheet = gc.open_by_url(SHEET_URL)


def get_tasks_from_sheet(
    tab_name: str,
    now: bool = True,
    person: Person = None,
    start_from: datetime = None,
    end_in: datetime = None,
) -> list[Task]:
    tasks = []
    tab = sheet.worksheet(tab_name)
    tab_data = tab.get_all_values()
    task_names = tab_data[HEADERS_ROW_IDX][TASK_NAMES_IDX:]
    start_date = start_from or datetime.now()
    end_date = end_in or datetime.max
    prev_date_value = None
    for i, row in enumerate(tab_data[DATA_ROW_IDX:]):
        logging.info(f"Parsing row {i} at {tab_name}")
        date_value = row[DATE_IDX]
        time_value = row[TIME_IDX]
        names = row[MEMBERS_IDX:]
        if not date_value:
            date_value = prev_date_value
        else:
            prev_date_value = date_value

        start_task, end_task = extract_and_convert_to_datetime(date_value, time_value)
        is_now = now and end_task >= datetime.now() >= start_task
        is_between_dates = not now and (
            (end_date >= end_task >= start_date)
            or (end_date >= start_task >= start_date)
        )
        is_on_date = is_now or is_between_dates
        is_person = (person and person.name in names) or (not person)

        if is_person and is_on_date:
            task_indexes = index_strings(task_names)
            for task_name, task_idx in task_indexes.items():
                members = []
                cols = []
                for j in task_idx:
                    name = names[j]
                    if name:
                        if memeber_person := persons.get(name):
                            members.append(memeber_person)
                            cols.append(j + 2)
                        else:
                            logging.warning(f"{name} does not found in list")

                task = Task(
                    task_name=task_name,
                    sheet=tab_name,
                    sheet_index=tab.index,
                    row=i + 2,
                    cols=cols,
                    start=start_task,
                    end=end_task,
                    members=members,
                )
                task_member_names = [person.name for person in task.members]
                if (
                    person and person.name not in task_member_names
                ) or not task_member_names:
                    continue

                tasks.append(task)

    return tasks


def get_released_members():
    tab = sheet.worksheet(RELEASES_SHEET_NAME)
    tab_data = tab.get_all_values()
    released_persons = []
    for i, row in enumerate(tab_data[DATA_ROW_IDX:]):
        logging.info(f"Parsing row {i} at {RELEASES_SHEET_NAME}")
        date_value = row[DATE_IDX]
        time_value = row[TIME_IDX]
        start_time, end_time = extract_and_convert_to_datetime(date_value, time_value)

        if start_time < datetime.now() < end_time:
            return [name for name in row[MEMBERS_IDX:] if name]

    return released_persons


def get_teams_and_persons():
    persons = {}
    teams = {}

    # get teams
    tab = sheet.worksheet(TEAMS_SHEET_NAME)
    tab_data = tab.get_all_values()
    team_names = tab_data[0]
    for i, team_name in enumerate(team_names):
        teams[team_name] = [row[i] for row in tab_data[1:] if row[i]]

    tab = sheet.worksheet(PERSONS_SHEET_NAME)
    tab_data = tab.get_all_values()[1:]
    names = [data[0] for data in tab_data]
    phones = [data[1] for data in tab_data]
    emails = [data[4] for data in tab_data]
    statuses = [data[5] for data in tab_data]
    status_update_time = [data[6] for data in tab_data]
    chat_ids = [data[7] for data in tab_data]
    for i in range(len(names)):
        person_status = StatusName.here
        status_time = None
        name = names[i]
        if statuses and len(statuses) > i:
            person_status = statuses[i]
            status_time = datetime.fromisoformat(
                status_update_time[i] or datetime.now().isoformat()
            )

        person_team = None
        for team_name, team_members in teams.items():
            if name in team_members:
                person_team = team_name
        if not person_team:
            logging.warning(f"{name} has no team")
            continue

        person = Person(
            row=i + 2,
            name=name,
            phone=phones[i],
            email=emails[i],
            team=person_team,
            status=Status(
                status_name=person_status or StatusName.here, update_time=status_time
            ),
        )
        persons[name] = person

        if chat_ids and len(chat_ids) > i and chat_ids[i]:
            chat_id = int(chat_ids[i])
            person.chat_id = chat_id

    return teams, persons


def get_task_by_cell(
    sheet_index: int, row: int, cols: list[int], person: Person = None
) -> Task | None:
    task = None
    tab = sheet.get_worksheet(sheet_index)
    values = tab.get_values(combine_merged_cells=True)
    row_data = values[row - 1]
    for c in cols:
        name = row_data[c]
        if person and person.name == name:
            task_name = values[HEADERS_ROW_IDX][c]
            date_value = row_data[DATE_IDX]
            time_value = row_data[TIME_IDX]
            start_task, end_task = extract_and_convert_to_datetime(
                date_value, time_value
            )
            task = Task(
                task_name=task_name,
                start=start_task,
                end=end_task,
                sheet=tab.title,
                sheet_index=tab.index,
                row=row,
                cols=[c],
                member=[person],
            )
    return task


def get_replacers(sheet_index: str, row: str, cols: str):
    tab = sheet.get_worksheet(int(sheet_index))
    cols = cols.split("_")
    replacers = []
    for c in cols:
        name = tab.cell(int(row) + 1, int(c) + 1).value
        replacers.append(name)
    return replacers


def update_person_sheet_status(row: int, status: Status):
    tab = sheet.worksheet(PERSONS_SHEET_NAME)
    worksheet = sheet.get_worksheet_by_id(tab.id)
    worksheet.update_cell(row, 6, status.status_name.value)
    worksheet.update_cell(row, 7, status.update_time.isoformat())


def update_person_chat_id_sheet(person: Person, chat_id: int):
    tab = sheet.worksheet(PERSONS_SHEET_NAME)
    worksheet = sheet.get_worksheet_by_id(tab.id)
    worksheet.update_cell(person.row, 8, chat_id)


def switch_shifts_sheet(
    requester_person: Person,
    first_shift_data: str,
    requested_person: Person,
    second_shift_data: str,
) -> str:
    second_sheet_index, srow, scols = second_shift_data.split("_", maxsplit=2)
    scols = [int(c) for c in scols.split("_")]
    sworksheet = sheet.get_worksheet(int(second_sheet_index))
    scol = None
    for c in scols:
        if requested_person.name == sworksheet.cell(srow, c + 1).value:
            scol = c + 1

    if not scol:
        logging.error(f"{requested_person.name} not found at [{srow}, {scols}]")
        raise ValueError(f"{requested_person.name} not found at [{srow}, {scols}]")

    if first_shift_data:
        first_sheet_index, frow, fcols = first_shift_data.split("_", maxsplit=2)
        fworksheet = sheet.get_worksheet(int(first_sheet_index))
        fcols = [int(c) for c in fcols.split("_")]
        fcol = None
        for c in fcols:
            if requester_person.name == sworksheet.cell(int(frow), c + 1).value:
                fcol = c + 1

        if fcol is None:
            logging.error(f"{requester_person.name} not found at [{fcol}, {fcols}]")
            raise ValueError(f"{requester_person.name} not found at [{fcol}, {fcols}]")

        logging.info(
            f"Replacing [{frow}, {fcol}]: {fworksheet.cell(int(frow), int(fcol)).value} with {requested_person.name}"
        )
        fworksheet.update_cell(int(frow), int(fcol), requested_person.name)
    msg = (
        f"{requester_person.name} replace shift with {requested_person.name} \n"
        f"Replacing [{srow}, {scol}]: {sworksheet.cell(int(srow), int(scol)).value} with {requester_person.name}"
    )
    logging.info(msg)
    sworksheet.update_cell(int(srow), int(scol), requester_person.name)
    return msg
