import datetime
import inspect
import re
import sys
import time
import locale

from dataclassy import dataclass
from telegram import Bot, Update
from telegram.ext.filters import MessageFilter



@dataclass
class Giochino:
    # Information about the game
    _name: str = None
    _emoji: str = None
    _category: str = None
    _date: datetime.date = None
    _day: str = None
    _url: str = None
    # Telegram input
    update: str = None
    raw_text: str = None
    # Tests and expected results
    examples: list[str] = None
    expected: list[dict | None] = None
    # Misc information about the game/class
    has_extra: bool = False  # if the game has additional points, currently set but unused
    can_lose: bool = True  # if the game can be lost (e.g has a copypaste string for lost plays), set but unused
    lost_message: str = "Hai perso :("  # per-game lose message
    win_message: str = None  # per-game win message
    hidden_game: bool = False  # set this to true to hide game from list/dicts/info
    # Parsed result
    day: str = None
    tries: str = None
    timestamp: int = None
    stars: str = None
    user_name: str = None
    user_id: int = None
    is_lost: bool = None
    # Result misc information
    message: str = None  # a message property used to handle specific case. At the moment is only used for unsupported games.
    parsed: bool = False  # A boolean set to true when a game successfully parse a play

    def __str__(self):
        return f"Partita di {self._name} il giorno {self.day} fatta da {self.user_name} ({self.user_id}). Risultato: {self.tries} punti{' (perso)' if self.is_lost else ''}."

    def __init__(self, update):
        self.update = update
        self.raw_text = sanitize(self.update.message.text)

        timestamp = int(datetime.datetime.timestamp(self.update.effective_message.date))
        self.user_name = self.update.message.from_user.full_name
        self.user_id = self.update.message.from_user.id
        self.timestamp = timestamp if timestamp else int(time.time())

        if self.can_handle_this(self.raw_text):
            self.parse()
            self.parsed = True

    # Used to define conditions to tell if this game matches the input update.
    @staticmethod
    def can_handle_this(raw_text):
        return False

    @property
    def info(self):
        return {
            "game": self._name,
            "emoji": self._emoji,
            "category": self._category,
            "url": self._url,
            "date": self._date,
            "day": self.day,
        }

    @property
    def punteggio(self):
        if self.parsed:
            return {
                "day": self.day,
                "name": self._name,
                "timestamp": self.timestamp,
                "tries": self.tries,
                "user_id": self.user_id,
                "user_name": self.user_name,
                "stars": self.stars,
            }
        else:
            return None

    @property
    def is_lost(self):
        return self.parsed and self.tries == "X"

    def parse(self):
        return

def generate_sample_update(text):
    updict = {
        "message": {
            "channel_chat_created": False,
            "chat": {"id": -1001180175690, "title": "Testing some bots", "type": "supergroup"},
            "date": 10,
            "delete_chat_photo": False,
            "from": {"first_name": "Trifase", "id": 456481297, "is_bot": False, "is_premium": True, "language_code": "en", "username": "Trifase"},
            "group_chat_created": False,
            "message_id": 19378,
            "message_thread_id": 19376,
            "text": text,
        },
        "update_id": 922829533,
    }

    # Creo un fake update
    bot = Bot("123456789")
    upd = Update.de_json(updict, bot)
    return upd




@dataclass
class Queens(Giochino):
    _name = "Queens"
    _category = "Logica"
    _date = datetime.date(2024, 10, 8)
    _day = "161"
    _emoji = "👑"
    _url = "https://lnkd.in/queens"

    can_lose: False

    examples = [
        "Queens n. 159 | 1:36 \nAi primi posti 👑: 🟦 🟨 🟪\nlnkd.in/queens.",
        "Queens #161 | 2:56\nAi primi posti 👑: 🟥 🟧 ⬜️\nlnkd.in/queens.",
        "Queens #161 | 0:58 and flawless\nFirst 👑s: 🟫 🟥 🟧 \nlnkd.in/queens.",
        "Queens #161\n0:58 👑\nlnkd.in/queens.",
        'Queens Nr. 323 | 0:58 und fehlerfrei\nErste 👑: ⬜ 🟥 🟦\nlnkd.in/queens.',
    ]
    expected = [
        {"day": "159", "name": "Queens", "timestamp": 10, "tries": "136", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "161", "name": "Queens", "timestamp": 10, "tries": "256", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "161", "name": "Queens", "timestamp": 10, "tries": "058", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "161", "name": "Queens", "timestamp": 10, "tries": "058", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "323", "name": "Queens", "timestamp": 10, "tries": "058", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["Queens", "lnkd.in/queens.", "👑"]
        _can_handle_this = all(w in raw_text for w in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        matches_day = re.search(r"Queens (?:n\. |#|Nr\. )(\d+)", text)
        matches_time = re.search(r"(\d+):(\d+)", text)
        self.day = matches_day.group(1) if matches_day else None
        self.tries = matches_time.group(1) + matches_time.group(2) if matches_time else None



def sanitize(text: str) -> str:
    # replace unicode \xa0 with space
    text_after = text.replace("\xa0", " ")
    # print(f"{text.encode('utf-8')}\n↓\n{text_after.encode('utf-8')}")
    return text_after

q = Queens
update = generate_sample_update(q.examples[0])
giochino = q(update)
print(giochino)
print()
print(giochino.punteggio)
print()
print(giochino.__dict__)