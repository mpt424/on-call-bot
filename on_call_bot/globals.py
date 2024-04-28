from on_call_bot.models import Person

persons: dict[str, Person] = {}
persons_by_chat_id: dict[int, Person] = {}
teams: dict = {}
