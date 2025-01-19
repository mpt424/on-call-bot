# Telegram Shift Management Bot

This Telegram bot facilitates shift management for teams by allowing users to report their exit/return, view shift schedules, change shifts with other team members, and check who is currently on shift. Additionally, commanders have the ability to view who is currently out or not on shift.

have fun!!!

## Features

### For All Users:
1. **Report Exit/Return**: Users can report when they exit or return from their shift.
2. **View Shift Schedule**: Users can view their upcoming shifts.
3. **Change Shifts**: Users can request to swap shifts with other team members.
4. **View Current Shift Status**: Users can check who is currently on shift.

### For Commanders:
1. **View All Members Status**: Commanders can see who is currently not on area and who is on shift or on call.

## Google Sheet Tables Format

To ensure proper integration with the bot, the Google Sheets tables must adhere to the following format:

### Persons Table:

The "Persons" table should contain the following columns in the specified order:

1. **Name**: Name of the person.
2. **Phone**: Phone number of the person.
3. **Reserved**: Reserved column (can be empty).
4. **Address**: Address of the person (can be empty).
5. **Email**: Email address of the person (can be empty).
6. **Status**: Status of the person (leave empty at first).
7. **Status Date**: Date of the status (leave empty at first).
8. **Chat ID**: Telegram chat ID of the person (leave empty at first).

### Example Persons Table:
|   Name   |    Phone    | Reserved |   Address   |   Email    |  Status  |  Status Date  |  Chat ID  |
|----------|-------------|----------|-------------|------------|----------|---------------|-----------|
| John Doe | 123-456-789 |          | 123 Main St |            | On Shift | 2024-03-21    | 123456789 |
| Jane Doe | 987-654-321 |          | 456 Elm St  | jane@example.com |          |               |           |
| Alice    | 555-555-555 |          |             | alice@example.com |      |               |           |


### Teams Table:

The "Teams" table should contain the team names in the headers, and each subsequent column should represent the team members by their names from the "Persons" table.

### Example Teams Table:
| Team A  |   Team B   |   Team C   |   Team D   |
|---------|--------------|--------------|-----------|
| Yoyo  |   Bob  |   Mary  |   Alice     |
| Jojo  |   Smith  |   Mary  |   Tom     |


### Releases Table:
The "Releases" table should have headers of date (in the format of dot-separated date like 7.10.23), time range (like 07:00-10:00)
### Example Releases Table:
|   Date  |  Time Range  | Released A | Released B |
|---------|--------------|------------|------------|
| 7.10.23 | 07:00-10:00  | John Doe   | Jane Doe   |
| 7.10.23 | 10:00-13:00  | Alice      | Bob Smith  |

### Tasks Table:

The "Tasks" table should have headers of date (in the format of dot-separated date like 7.10.23), time range (like 07:00-10:00), and the next headers should represent the position names (can be multiple).

### Example Tasks Table:
|   Date  |  Time Range  |  Position A  |  Position B  |
|---------|--------------|--------------|--------------|
| 7.10.23 | 07:00-10:00  |   John Doe   |   Jane Doe   |
| 7.10.23 | 10:00-13:00  |   Alice      |   Bob Smith  |


Ensure that these tables are correctly formatted and populated to enable seamless interaction between the bot and Google Sheets.


## Execute

NOTE: telegram bots allowed run only in a single instance per bot! otherwise it will make a conflicts

### Installation

To deploy this bot:

1. Clone this repository.
2. Set up a Telegram bot using BotFather and obtain the API token.
3. Create a Google Cloud Platform project and enable the Google Sheets API.
4. Obtain credentials for the Google Sheets API and place them in the appropriate location.
5. Configure the bot with the necessary environment variables.
6. Deploy the bot to a server or docker.

### Settings (Environment Variables)
Before deploying the bot, ensure the following environment variables are set:

1. TOKEN: Your bot token given by Telegram BotFather. Obtain this token from BotFather.
2. LANG_ID: Bot language ID. You can add your own language file to the langs directory if you want something else. Default is Hebrew language ID.
3. SHEET_URL: Google Sheet URL containing shift and team data.
4. SERVICE_ACCOUNT_JSON: Path to the Google Sheet credentials file.
5. RELEASES_SHEET_NAME: Sheet name that presents person releases. Default is "releases".
6. PERSONS_SHEET_NAME: Sheet name that presents the list of persons. Default is "persons".
7. TEAMS_SHEET_NAME: Sheet name that contains team division. Default is "teams".
8. TASKS_SHEET_NAMES: List of sheet names that present task shifts (separated by comma). Default is "tasks".
9. COMMANDERS: List of commander names (separated by comma).
10. DEVELOPERS: List of developers' Telegram account IDs (separated by comma).
11. MIN_IN: Minimum persons to stay on call. Default is 20.
12. MAX_SHORT_OUT: Maximum persons to make a short out. Default is 5.
13. REMIND_SHORT_OUT_HRS: Auto-remind iteration for short out (in hours). Default is 2.
14. REMIND_LONG_OUT_HRS: Auto-remind iteration for long out (in hours). Default is 4.
15. MAIN_CHANNEL_ID: Main channel ID to send updates.
16. DEV_CHANNEL_ID: Dev channel ID to send logs.

Ensure these variables are correctly set to enable the bot's functionality and integration with Google Sheets.

## Development

### Simulation of Other Person
Developers can simulate interactions with the bot as other users by using test accounts. 
This enables thorough testing of the bot's functionality from different user perspectives.
When developer first interact with the bot he will get a list of all members to simulate.

## Usage

### Basic Commands:
- `/start` - start interaction with the bot. you'll need to identify with full name at first step
- you can send the bot date or datetime range to get all shifts in that time e.g.: 
  - `1.12.23`: will present all shifts in the 1th Dec 23 (include thos who only starts/ends in that date). 
  - `1.12.23 07:00 - 2.12.23 09:00`: will present all shifts from 07:00am at the 1th Dec 23 till 09:00am 2th Dec 23 (include thos who only starts/ends in that range).

## Contributing

Contributions to improve the bot's functionality or fix any issues are welcome. Please follow the standard contribution guidelines and open a pull request.

## License

This project is licensed under the [MIT License](LICENSE).
