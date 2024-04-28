import logging
from collections import defaultdict
from datetime import datetime, timedelta
from io import BytesIO

from ics import Calendar, Event
from telegram import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import CallbackContext, ContextTypes, ConversationHandler, JobQueue

from on_call_bot import translator
from on_call_bot.configuration import (
    COMMANDERS,
    DEV_CHANNEL_ID,
    DEVELOPERS,
    MAIN_CHANNEL_ID,
    MAX_SHORT_OUT,
    MIN_IN,
    REMIND_LONG_OUT_HRS,
    REMIND_SHORT_OUT_HRS,
)
from on_call_bot.globals import persons, persons_by_chat_id, teams
from on_call_bot.helpers import generate_who_is_here_message, get_tasks
from on_call_bot.models import Person, Status, StatusName
from on_call_bot.sheet_helpers import (
    get_released_members,
    get_replacers,
    get_task_by_cell,
    get_teams_and_persons,
    switch_shifts_sheet,
    update_person_chat_id_sheet,
    update_person_sheet_status,
)
from on_call_bot.utils import (
    convert_to_gmt2,
    convert_to_markdown,
    create_google_calendar_link,
    extract_and_convert_to_datetime_range,
    next_interval_time,
    return_button,
    return_menu_markup,
)


async def identify_name(update: Update, _: ContextTypes.DEFAULT_TYPE):
    """Ask the user for info about the selected predefined choice."""
    chat_id = update.effective_chat.id
    name = update.message.text
    if name not in persons:
        await update.message.reply_text(
            text=translator.get(
                "Identify failed", "Identify failed. try use other name"
            )
        )
    else:
        person = persons[name]
        update_person_chat_id(person, chat_id)
        await show_menu(update, chat_id)

    return 0


async def time_range_handler(update: Update, _: ContextTypes.DEFAULT_TYPE):
    """Get time range to shoe shifts"""
    chat_id = update.effective_chat.id
    datetime_range_value = update.message.text
    person = persons_by_chat_id.get(chat_id)
    if not person:
        return await identify_name(update, _)

    else:
        start_from, end_in = extract_and_convert_to_datetime_range(datetime_range_value)
        tasks = get_tasks(start_from=start_from, end_in=end_in)
        tasks_by_times = defaultdict(list)
        for task in tasks:
            tasks_by_times[
                f"{task.start.strftime('%d.%m %H:%M')} - {task.end.strftime('%H:%M')}"
            ].append(task)

        msg = ""
        for time_range, tasks in tasks_by_times.items():
            msg += f"*{time_range}* \n"
            for task in tasks:
                msg += f"    _{task.task_name}_ \n"

                for member in task.members:
                    msg += f"    {member.description}  \n"

            msg += "\n\n"

        await update.message.reply_text(
            text=convert_to_markdown(msg),
            reply_markup=return_menu_markup,
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    return 0


async def show_menu(
    update: Update, chat_id: int, query: CallbackQuery = None, prefix: str = None
):
    action_prefix = prefix or ""
    person = persons_by_chat_id[chat_id]
    keyboard = [
        [
            InlineKeyboardButton(
                translator.get("Out report"), callback_data=f"{action_prefix}out"
            )
        ],
        [
            InlineKeyboardButton(
                translator.get("Back report"), callback_data=f"{action_prefix}back"
            )
        ],
        [
            InlineKeyboardButton(
                translator.get("My shifts"), callback_data=f"{action_prefix}my_shifts"
            )
        ],
        [
            InlineKeyboardButton(
                translator.get("Who's in shift"), callback_data=f"{action_prefix}shifts"
            )
        ],
        [
            InlineKeyboardButton(
                translator.get("My replacer"),
                callback_data=f"{action_prefix}show_replace",
            )
        ],
        [
            InlineKeyboardButton(
                translator.get("Change shift"),
                callback_data=f"{action_prefix}change_{chat_id}",
            )
        ],
    ]
    if person.name in COMMANDERS:
        keyboard.extend(
            [
                [
                    InlineKeyboardButton(
                        translator.get("Who is here"), callback_data="who_is_here"
                    )
                ],
            ]
        )

    reply_markup = InlineKeyboardMarkup(keyboard)
    welcome_message = translator.get("Welcome", "Welcome %s what would you like to do?")
    welcome_message = welcome_message % person.name
    if query:
        await query.edit_message_text(welcome_message, reply_markup=reply_markup)
    elif update.message:
        await update.message.reply_text(welcome_message, reply_markup=reply_markup)
    else:
        await update.effective_user.send_message(
            welcome_message, reply_markup=reply_markup
        )


async def show_dev_menu(update: Update):
    keyboard = []
    for chat_id, person in persons_by_chat_id.items():
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"{person.name} ({chat_id})", callback_data=f"simulate_{chat_id}"
                )
            ]
        )
    keyboard.append([InlineKeyboardButton("Restart", callback_data="start")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.edit_message_text(
            translator.get("Who to simulate?"), reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            translator.get("Who to simulate?"), reply_markup=reply_markup
        )


def update_person_chat_id(person: Person, chat_id: int):
    update_person_chat_id_sheet(person, chat_id)
    person.chat_id = chat_id
    persons_by_chat_id[chat_id] = person
    logging.info(f"{person.name} update his chat_id to {chat_id}")


async def start(update: Update, _: CallbackContext):
    chat_id = update.effective_chat.id
    if str(chat_id) not in DEVELOPERS and chat_id not in persons_by_chat_id:
        await update.message.reply_text(
            text=translator.get("Identify", "Please identify. What is your full name?")
        )
    else:
        if str(chat_id) in DEVELOPERS:
            await show_dev_menu(update)
        else:
            await show_menu(update, chat_id)
    return 0


def get_released() -> list[str]:
    released_names = get_released_members()
    not_here_persons = [persons[name] for name in released_names if name]
    return [person.description for person in not_here_persons]


async def show_who_is_here(query: CallbackQuery, context: CallbackContext):
    loaded_teams, loaded_persons = get_teams_and_persons()
    teams.update(loaded_teams)
    while persons:
        persons.popitem()

    persons.update(loaded_persons)
    for person in persons:
        if person not in loaded_persons:
            logging.warning(f"{person.name} removed")
    tasks = get_tasks(now=True)
    released_members = get_released()
    not_here = [
        person
        for person in persons.values()
        if person.status.status_name in [StatusName.out, StatusName.short_out]
        and person.description not in released_members
    ]
    here = [
        person.description
        for person in persons.values()
        if person.status.status_name == StatusName.here
    ]
    msg = generate_who_is_here_message(tasks, here, not_here, released_members, teams)
    inline_keyboard = []
    if not_here:
        not_here_msg = translator.get(
            "Not here count", "%d not in area. Press the name to remind them \n\n"
        ) % len(not_here)
        msg += not_here_msg

        for person in not_here:
            time_delta = datetime.now() - person.status.update_time
            person_not_here_msg = translator.get(
                "Person not here", "%s %s ~%d hours"
            ) % (
                person.name,
                person.status.status_name.value,
                int(time_delta.total_seconds() / 3600),
            )
            inline_keyboard.append(
                [
                    InlineKeyboardButton(
                        person_not_here_msg,
                        callback_data=f"remind_{person.chat_id}",
                    )
                ]
            )

    elif not released_members and not not_here:
        msg = translator.get("Everybody here") + "\n" + msg

    inline_keyboard.append([return_button])
    not_here_markup = InlineKeyboardMarkup(inline_keyboard)
    await query.edit_message_text(
        text=convert_to_markdown(msg),
        reply_markup=not_here_markup,
        parse_mode="MarkdownV2",
    )


async def show_shifts(
    query: CallbackQuery, chat_id: int = None, now: bool = False, with_time: bool = True
):
    person = persons_by_chat_id.get(chat_id)
    start_from_date = datetime.now()
    tasks = get_tasks(now=now, person=person, start_from=start_from_date)
    if not tasks:
        msg = translator.get("No tasks")
    else:
        task_messages = []
        for task in tasks:
            task_members = " \n".join(task.members_description)
            google_link = create_google_calendar_link(
                task.task_name, task_members, task.start, task.end
            )

            task_descriptor = (
                f"*{task.description(with_time=with_time)}:*\n{task_members}"
                if not person
                else f"*{task.description(with_time=with_time)}* [הוסף ליומן]({google_link}) \n{task_members}"
            )
            task_messages.append(task_descriptor)

        msg = " \n".join(task_messages)

    # TODO: order up ics file times
    # ics_button = InlineKeyboardButton(translater.get("Send ics file"), callback_data="get_ics")
    return_markup = InlineKeyboardMarkup(
        [
            # [ics_button],
            [return_button]
        ]
    )
    converted_text = convert_to_markdown(msg)
    await query.edit_message_text(
        text=converted_text,
        reply_markup=return_markup,
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def handle_status_change(
    chat_id: int,
    status_name: StatusName,
    query: CallbackQuery,
    context: CallbackContext,
):
    person = persons_by_chat_id[chat_id]
    if person.status.status_name == status_name:
        msg = (
            translator.get("Already in status", "You are already in status %s")
            % status_name.value
        )
        await query.edit_message_text(
            text=msg,
            reply_markup=return_menu_markup,
        )
    else:
        await update_person_status(chat_id, status_name, context)
        msg = (
            translator.get(
                "Your status changed", "Your status changes to %s. Update on change."
            )
            % status_name.value
        )
        await query.edit_message_text(
            text=msg,
            reply_markup=return_menu_markup,
        )
    released_members = get_released()
    here = [
        person
        for person in persons.values()
        if person.status.status_name == StatusName.here
        and f"{person.name} {person.phone}" not in released_members
    ]
    if len(here) <= MIN_IN:
        await notify(
            translator.get(
                "Out is full", "Too many peoples went out! you cannot exit right now"
            ),
            context,
            list(persons.keys()),
        )

    job = context.job_queue.get_jobs_by_name(name=str(chat_id))
    if job:
        job[0].schedule_removal()

    async def callback_auto_remind_message(context: CallbackContext):
        await remind_person_status(chat_id, context, by_who="System")

    if status_name in [StatusName.out, StatusName.short_out]:
        if status_name == StatusName.out:
            context.job_queue.run_repeating(
                callback_auto_remind_message,
                timedelta(hours=REMIND_LONG_OUT_HRS),
                chat_id=chat_id,
                name=str(chat_id),
            )
        elif status_name == StatusName.short_out:
            context.job_queue.run_repeating(
                callback_auto_remind_message,
                timedelta(hours=REMIND_SHORT_OUT_HRS),
                chat_id=chat_id,
                name=str(chat_id),
            )
        not_here = [
            person
            for person in persons.values()
            if person.status.status_name != StatusName.here
            and person.description not in released_members
        ]
        notification_msg = translator.get(
            "Notify commander", "FYI %d out of the area and more %d released for today"
        )
        if (len(not_here) + 1) % 5 == 0:
            notification_msg = notification_msg % (len(not_here), len(released_members))
            await notify_commanders(notification_msg, context)


async def remind_status(chat_id: int, context: CallbackContext, by_who="System"):
    await remind_person_status(chat_id, context, by_who)


async def remind_person_status(chat_id: int, context: CallbackContext, by_who: str):
    person = persons_by_chat_id[chat_id]
    msg = translator.get(
        "Remind status",
        "Your status is %s since %s.\n Please update if anything changed",
    )
    msg = msg % (
        person.status.status_name.value,
        person.status.update_time.strftime("%A, %d %B %Y %H:%M"),
    )

    inline_keyboard = [
        [InlineKeyboardButton(translator.get("Back report"), callback_data="back")],
        [return_button],
    ]
    await context.bot.send_message(
        chat_id=int(chat_id),
        text=msg,
        reply_markup=InlineKeyboardMarkup(inline_keyboard),
    )
    await notify_channel(
        channel_id=DEV_CHANNEL_ID,
        message=f"{by_who} remind {person.name} about {person.status.status_name.value}",
        context=context,
    )


async def notify_channel(channel_id: str, message: str, context: CallbackContext):
    if channel_id:
        await context.bot.send_message(chat_id=channel_id, text=message)


async def notify(
    message: str,
    context: CallbackContext,
    names_to_notify: list[str],
    keyboard_keys: list[list[InlineKeyboardButton]] | None = None,
):
    keyboard = keyboard_keys or []
    keyboard.append([return_button])
    reply_markup = InlineKeyboardMarkup(keyboard)
    for name in names_to_notify:
        logging.info("notifying %s", name)
        person = persons[name]
        if person.chat_id:
            try:
                await context.bot.send_message(
                    chat_id=person.chat_id, text=message, reply_markup=reply_markup
                )
            except Exception as e:
                logging.exception(
                    f"Failed to notify {message} to {person.name} due to {str(e)}"
                )


async def notify_commanders(message, context):
    await notify(
        message,
        context,
        COMMANDERS,
        [
            [
                InlineKeyboardButton(
                    translator.get("Who is here"), callback_data="who_is_here"
                )
            ]
        ],
    )


async def check_outs(query: CallbackQuery, chat_id: int):
    request_person = persons_by_chat_id[chat_id]
    if get_tasks(now=True, person=request_person):
        msg = translator.get(
            "Person in task", "You are in task and need to change to make an exit"
        )
        await query.edit_message_text(text=msg, reply_markup=return_menu_markup)
        return False

    released_members = get_released()
    here = [
        person
        for person in persons.values()
        if person.status.status_name == StatusName.here
        and f"{person.name} {person.phone}" not in released_members
    ]
    if len(here) <= MIN_IN:
        msg = translator.get("Out is full")
        inline_keyboard = [
            [
                InlineKeyboardButton(
                    translator.get("Show outs"), callback_data="who_is_out"
                ),
                return_button,
            ]
        ]
        await query.edit_message_text(
            text=msg, reply_markup=InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
        )
        return False

    return True


async def handle_query(
    chat_id: int, update: Update, context: CallbackContext, query: CallbackQuery
):
    if str(chat_id) not in DEVELOPERS and chat_id not in persons_by_chat_id.keys():
        await update.message.reply_text(
            text=translator.get(
                "Identify failed", "Identify failed. try use other name"
            )
        )

    action = query.data
    query_person = persons_by_chat_id.get(chat_id) or update.effective_user
    logging.info(f"QUERY: {query_person.name} - {action}")
    action_prefix = None
    if action.startswith("simulate"):
        split_action = action.split("_", maxsplit=2)
        chat_id = int(split_action[1])
        action_prefix = f"simulate_{chat_id}_"
        if len(split_action) <= 2:
            await show_menu(update, chat_id, query, prefix=action_prefix)
            return
        action = split_action[2]
    if action.startswith("remind"):
        _, chat_id = action.split("_")
        chat_id = int(chat_id)
        await remind_status(chat_id, context, by_who=query_person.name)
        reminder_person = persons_by_chat_id[chat_id]
        msg = translator.get("Remind sent", "Remind sent to %s") % reminder_person.name
        await query.edit_message_text(text=msg, reply_markup=return_menu_markup)
    elif action.startswith("replace"):
        _, sheet_index, row, cols = action.split("_", maxsplit=3)
        await show_replace(sheet_index, row, cols, query)
    elif action.startswith("change"):
        change_data = action.split("/")

        # what to change
        if len(change_data) == 1:
            await ask_shift_to_change(
                action, chat_id, translator.get("Which shift to replace"), query
            )
        if len(change_data) == 2:
            await ask_who_change(action, query)
        if len(change_data) == 3:
            await ask_shift_to_change(
                action,
                int(change_data[2]),
                translator.get("Which shift to take"),
                query,
            )
        if len(change_data) == 4:
            await ask_change(
                change_data[0],
                change_data[1],
                int(change_data[2]),
                change_data[3],
                query,
                context,
            )
        elif len(change_data) == 5:
            requester_id = int(change_data[0].split("_")[-1])
            await handle_change(
                requester_id,
                change_data[1],
                int(change_data[2]),
                change_data[3],
                bool(int(change_data[4])),
                query,
                context,
            )
    else:
        await handle_action(
            chat_id, action, update, context, query, prefix=action_prefix
        )


async def ask_when(query: CallbackQuery):
    msg = (
        "Please provide time range e.g.:"
        "All day: day.month.year \n"
        "Time range: day.month.year HH:mm - day.month.year HH:mm \n"
        "Or press now button"
    )
    inline_keyboard = [
        [
            InlineKeyboardButton(translator.get("Now"), callback_data="whos_in_shift"),
            return_button,
        ]
    ]
    await query.edit_message_text(
        text=translator.get("Choose when", msg),
        reply_markup=InlineKeyboardMarkup(inline_keyboard),
    )


async def switch_shifts(
    requester_chat_id: int,
    first_shift_data: str,
    requested_chat_id: int,
    second_shift_data: str,
    context: CallbackContext,
):
    requester_person = persons_by_chat_id[requester_chat_id]
    requested_person = persons_by_chat_id[requested_chat_id]
    msg = switch_shifts_sheet(
        requester_person, first_shift_data, requested_person, second_shift_data
    )
    await notify_channel(channel_id=DEV_CHANNEL_ID, message=msg, context=context)


async def handle_change(
    requester_chat_id: int,
    to_change_shift: str,
    requested_chat_id: int,
    requested_shift: str,
    approved: bool,
    query: CallbackQuery,
    context: CallbackContext,
):
    if approved:
        await switch_shifts(
            requester_chat_id,
            to_change_shift,
            requested_chat_id,
            requested_shift,
            context,
        )
        await context.bot.send_message(
            chat_id=requester_chat_id,
            text=translator.get("Change succeeded"),
            reply_markup=return_menu_markup,
        )

        await query.edit_message_text(
            text=translator.get("Change succeeded"), reply_markup=return_menu_markup
        )
    else:
        await context.bot.send_message(
            chat_id=requester_chat_id,
            text=translator.get("Change rejected"),
            reply_markup=return_menu_markup,
        )
        await query.edit_message_text(
            text=translator.get("Change rejected"), reply_markup=return_menu_markup
        )


def init_job_queue(job_queue: JobQueue, person: Person):
    job = job_queue.get_jobs_by_name(name=str(person.chat_id))
    if job:
        job[0].schedule_removal()

    async def callback_auto_remind_message(context: CallbackContext):
        await remind_person_status(person.chat_id, context, by_who="System")

    if person.status.status_name == StatusName.out:
        job_queue.run_repeating(
            callback_auto_remind_message,
            timedelta(hours=REMIND_LONG_OUT_HRS),
            first=next_interval_time(person.status.update_time, REMIND_SHORT_OUT_HRS),
            chat_id=person.chat_id,
            name=str(person.chat_id),
        )

    elif person.status.status_name == StatusName.short_out:
        job_queue.run_repeating(
            callback_auto_remind_message,
            timedelta(hours=REMIND_SHORT_OUT_HRS),
            first=next_interval_time(person.status.update_time, REMIND_SHORT_OUT_HRS),
            chat_id=person.chat_id,
            name=str(person.chat_id),
        )


async def update_person_status(
    chat_id: int, status: StatusName, context: CallbackContext
):
    person = persons_by_chat_id[chat_id]
    person.status = Status(status_name=status, update_time=datetime.now())
    update_person_sheet_status(person.row, person.status)
    logging.info(f"{person.name} change his status to {person.status}")
    msg = (
        f"{person.name} "
        f"{translator.get('Status change to')} "
        f"{person.status.status_name.value}"
    )
    await notify_channel(channel_id=MAIN_CHANNEL_ID, message=msg, context=context)


async def ask_change(
    action: str,
    to_change_shift: str,
    chat_id: int,
    requested_shift: str,
    query: CallbackQuery,
    context: CallbackContext,
):
    required_person = persons_by_chat_id[chat_id]
    to_change_person = persons_by_chat_id[query.message.chat_id]
    logging.info(
        f"{to_change_person.name} is request to change shift with {required_person.name}"
    )

    task_to_change = None
    if to_change_shift:
        sheet_index, row, cols = to_change_shift.split("_", maxsplit=2)
        task_to_change = get_task_by_cell(
            int(sheet_index),
            int(row),
            [int(c) for c in cols.split("_")],
            to_change_person,
        )
    sheet_index, row, cols = requested_shift.split("_", maxsplit=2)
    required_task = get_task_by_cell(
        int(sheet_index), int(row), [int(c) for c in cols.split("_")], required_person
    )
    inline_keyboard = [
        [
            InlineKeyboardButton(
                text=translator.get("Approve"),
                callback_data=f"{action}/{to_change_shift}/{required_person.chat_id}/{requested_shift}/{int(True)}",
            ),
            InlineKeyboardButton(
                text=translator.get("Denied"),
                callback_data=f"{action}/{to_change_shift}/{required_person.chat_id}/{requested_shift}/{int(False)}",
            ),
        ],
        [return_button],
    ]

    translator.get("Switch request", "%s want to change %s within %s")
    msg = (
        f"{to_change_person.name} "
        f"{translator.get('want to change')} \n"
        f"{task_to_change.description(with_time=True) if task_to_change else ''} \n"
        f"{translator.get('within')} \n"
        f"{required_task.description(with_time=True) if required_task else ''} \n"
    )
    await context.bot.send_message(
        chat_id=required_person.chat_id,
        text=msg,
        reply_markup=InlineKeyboardMarkup(inline_keyboard),
    )

    await query.edit_message_text(
        text=translator.get("Wait for approve"), reply_markup=return_menu_markup
    )


async def ask_shift_to_change(
    action: str, chat_id: int, msg: str, query: CallbackQuery
):
    change_person = persons_by_chat_id[chat_id]
    change_tasks = get_tasks(now=False, person=change_person, start_from=datetime.now())
    inline_keyboard = []
    for task in change_tasks:
        task_cols = "_".join([str(i) for i in task.cols])
        inline_keyboard.append(
            [
                InlineKeyboardButton(
                    text=task.description(with_time=True),
                    callback_data=f"{action}/{task.sheet_index}_{task.row}_{task_cols}",
                )
            ]
        )
    inline_keyboard.append(
        [
            InlineKeyboardButton(
                text=translator.get("Just taking"),
                callback_data=f"{action}/",
            )
        ]
    )
    inline_keyboard.append([return_button])
    await query.edit_message_text(
        text=msg, reply_markup=InlineKeyboardMarkup(inline_keyboard)
    )


async def ask_who_change(action: str, query: CallbackQuery):
    inline_keyboard = []
    for person_name, person_data in persons.items():
        inline_keyboard.append(
            InlineKeyboardButton(
                text=person_name,
                callback_data=f"{action}/{person_data.chat_id}",
            ),
        )

    inline_keyboard = [
        inline_keyboard[i : i + 2] for i in range(0, len(inline_keyboard), 2)
    ]
    inline_keyboard.append([return_button])
    await query.edit_message_text(
        text=translator.get("Change with who"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard),
    )


async def show_replace(sheet_index: str, row: str, cols: str, query: CallbackQuery):
    replacers = get_replacers(sheet_index, row, cols)
    msg = translator.get("Your replacer are")
    msg += ": \n"
    for name in replacers:
        if next := persons.get(name):
            msg += f"{next.description} \n"
    await query.edit_message_text(text=msg, reply_markup=return_menu_markup)


async def ask_replace(chat_id: int, query: CallbackQuery):
    person = persons_by_chat_id.get(chat_id)
    tasks = get_tasks(
        now=False, person=person, start_from=datetime.now() - timedelta(minutes=30)
    )
    inline_keyboard = []
    for task in tasks:
        task_cols = "_".join([str(i) for i in task.cols])
        inline_keyboard.append(
            [
                InlineKeyboardButton(
                    task.description(with_time=True),
                    callback_data=f"replace_{task.sheet_index}_{task.row}_{task_cols}",
                )
            ]
        )

    inline_keyboard.append([return_button])
    inline_keyboard_markup = InlineKeyboardMarkup(inline_keyboard)
    await query.edit_message_text(
        text=translator.get("Which shift to replace?"),
        reply_markup=inline_keyboard_markup,
    )


async def send_ics(
    query: CallbackQuery, chat_id: int, context: CallbackContext
) -> None:
    person = persons_by_chat_id.get(chat_id)
    tasks = get_tasks(now=False, person=person, start_from=datetime.now())

    # Create the .ics file
    cal = Calendar()
    for task in tasks:
        event = Event()
        event.name = task.task_name
        event.begin = convert_to_gmt2(task.start)
        event.end = convert_to_gmt2(task.end)
        description = "\n".join(task.members_description)
        event.description = description
        cal.events.add(event)

    # Save to a BytesIO object
    ics_buffer = BytesIO()
    ics_buffer.write(bytes(str(cal), "utf-8"))
    ics_buffer.seek(0)

    # Send the file to the user
    await query.message.reply_document(
        document=ics_buffer,
        caption="tasks",
        filename="tasks.ics",
        reply_markup=return_menu_markup,
    )


async def show_who_is_out(query: CallbackQuery):
    inline_keyboard = []
    released_members = get_released()
    not_here = [
        person
        for person in persons.values()
        if person.status.status_name in [StatusName.out, StatusName.short_out]
        and person.description not in released_members
    ]
    for person in not_here:
        time_delta = datetime.now() - person.status.update_time
        person_msg = translator.get("remind person button", "%s %s ~%s hours")
        person_msg = person_msg % (
            person.name,
            person.status.status_name.value,
            int(time_delta.total_seconds() / 3600),
        )
        inline_keyboard.append(
            [InlineKeyboardButton(person_msg, callback_data=f"remind_{person.chat_id}")]
        )
    inline_keyboard.append([return_button])
    await query.edit_message_text(
        text=translator.get("Press button to remind"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard),
    )


async def show_outs(query: CallbackQuery, chat_id: int, prefix: str = None):
    action_prefix = prefix or ""
    if await check_outs(query, chat_id):
        first_keyboard_row = []
        released_members = get_released()
        long_outs_alloc = len(persons) - len(released_members) - MAX_SHORT_OUT - MIN_IN
        long_outs = [
            person
            for person in persons.values()
            if person.status.status_name == StatusName.out
        ]
        msg = ""
        if len(long_outs) < long_outs_alloc:
            first_keyboard_row.append(
                InlineKeyboardButton(
                    translator.get("Long out"), callback_data=f"{action_prefix}long_out"
                )
            )
        else:
            msg += (
                translator.get(
                    "Long out allocation full", "Long out allocation is full (%d)\n"
                )
                % long_outs_alloc
            )

        short_outs = [
            person
            for person in persons.values()
            if person.status.status_name == StatusName.short_out
        ]
        if len(short_outs) < MAX_SHORT_OUT:
            first_keyboard_row.append(
                InlineKeyboardButton(
                    translator.get("Temp out", "Temporary (2-3 hrs)"),
                    callback_data=f"{action_prefix}short_out",
                )
            )
        else:
            msg += (
                translator.get(
                    "Temp out allocation full", "Temp out allocation is full (%d)\n"
                )
                % MAX_SHORT_OUT
            )

        inline_keyboard = []
        if first_keyboard_row:
            inline_keyboard.append(first_keyboard_row)

        inline_keyboard.append(
            [
                InlineKeyboardButton(
                    translator.get("Show who's out"), callback_data="who_is_out"
                )
            ]
        )
        inline_keyboard.append([return_button])
        await query.edit_message_text(
            text=msg + translator.get("Choose exit type"),
            reply_markup=InlineKeyboardMarkup(inline_keyboard),
        )


async def handle_action(
    chat_id: int,
    action: str,
    update: Update,
    context: CallbackContext,
    query: CallbackQuery,
    prefix: str = None,
):
    match action:
        case "start":
            await start(update, context)
        case "out":
            await show_outs(query, chat_id, prefix=prefix)
        case "who_is_out":
            await show_who_is_out(query)
        case "long_out":
            if await check_outs(query, chat_id):
                await handle_status_change(
                    chat_id,
                    StatusName.out,
                    query,
                    context,
                )
        case "short_out":
            if await check_outs(query, chat_id):
                await handle_status_change(
                    chat_id,
                    StatusName.short_out,
                    query,
                    context,
                )
        case "back":
            await handle_status_change(chat_id, StatusName.here, query, context)
        case "who_is_here":
            await show_who_is_here(query, context)
        case "my_shifts":
            await show_shifts(query, chat_id, now=False, with_time=True)
        case "whos_in_shift":
            await show_shifts(query, now=True, with_time=False)
        case "shifts":
            await ask_when(query)
        case "get_ics":
            await send_ics(query, chat_id, context)
        case "return_main":
            if str(chat_id) in DEVELOPERS:
                await show_dev_menu(update)
            else:
                await show_menu(update, chat_id)
        case "show_replace":
            await ask_replace(chat_id, query)
        case "change_shift":
            await change_shift(chat_id, query)


async def change_shift(chat_id, query):
    person = persons_by_chat_id.get(chat_id)
    tasks = get_tasks(now=False, person=person)
    keyboard = []
    for task in tasks:
        task_cols = "_".join([str(i) for i in task.cols])
        keyboard.append(
            [
                InlineKeyboardButton(
                    task.task_name,
                    callback_data=f"change_{task.sheet_index}_{task.row}_{task_cols}",
                )
            ]
        )

    keyboard.append([return_button])
    await query.edit_message_text(
        text=translator.get("Which shift to replace"),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def button(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    try:
        chat_id = query.message.chat_id
        await handle_query(chat_id, update, context, query)
    except Exception as error:
        logging.exception(f"Somthing went wrong {str(error)}")
        await query.edit_message_text(
            text=translator.get("Something went wrong"), reply_markup=return_menu_markup
        )
        await notify_channel(
            channel_id=DEV_CHANNEL_ID,
            message=f"Error occurred: {error.__class__.__name__}\n\n{str(error)}",
            context=context,
        )


async def done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data = context.user_data
    await update.message.reply_text(translator.get("Bye Bye"))
    user_data.clear()
    return ConversationHandler.END


def global_init():
    loaded_teams, loaded_persons = get_teams_and_persons()
    teams.update(loaded_teams)
    persons.update(loaded_persons)
    for person in persons.values():
        if person.chat_id:
            persons_by_chat_id[person.chat_id] = person
