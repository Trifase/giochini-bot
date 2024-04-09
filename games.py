import datetime
import inspect
import sys
import time

from dataclassy import dataclass
from telegram import Bot, Update


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


def time_from_emoji(input_string: str) -> str:
    emojidict = {"0️⃣": 0, "1️⃣": 1, "2️⃣": 2, "3️⃣": 3, "4️⃣": 4, "5️⃣": 5, "6️⃣": 6, "7️⃣": 7, "8️⃣": 8, "9️⃣": 9, "🔟": 10, ":": ""}
    for key, value in emojidict.items():
        input_string = input_string.replace(key, str(value))

    input_string = "".join([x for x in input_string if x in "0123456789"])
    return input_string


def get_day_from_date(game_date: datetime.date, game_day: str, game: str, date: datetime.date | str = None) -> str:
    if isinstance(date, str) and game == "Globle":
        date = datetime.datetime.strptime(date, "🌎 %b %d, %Y 🌍").date()

    if isinstance(date, str) and game == "HighFive":
        date_str = date.split("/")[-1]
        date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()

    if isinstance(date, str) and game == "Moviedle":
        date = datetime.datetime.strptime(date, "#%Y-%m-%d").date()

    if isinstance(date, str) and game == "Murdle":
        date = datetime.datetime.strptime(date, "%m/%d/%Y").date()

    if isinstance(date, str) and game == "Picsey":
        date = datetime.datetime.strptime(date, "%m.%d.%y").date()

    if isinstance(date, str) and game == "Chronophoto":
        date = datetime.datetime.strptime(date, "%d/%m/%Y").date()

    if date is None:
        date = datetime.date.today()

    # GAMES = get_games()
    days_difference = game_date - date
    return str(int(game_day) - days_difference.days)


def is_connection_block_completed(block: str) -> bool:
    color = block[0]
    if block == color * 4:
        return True
    return False


def is_connection_completed(connection: list[str]) -> bool:
    completed_blocks = 0
    for block in connection:
        if is_connection_block_completed(block):
            completed_blocks += 1
    if completed_blocks == 4:
        return True
    return False


@dataclass
class Giochino:
    # Infos
    _name: str
    _emoji: str
    _category: str
    _date: datetime.date
    _day: str
    _url: str
    # Input
    update: str
    raw_text: str
    # Tests
    examples: list[str]
    expected: list[dict]
    # Misc
    has_extra: bool
    can_lose: bool
    # Parsed result
    day: str
    tries: str
    timestamp: int
    stars: str
    user_name: str
    user_id: int
    is_lost: bool

    def __str__(self):
        return f"Partita di {self._name} il giorno {self.day} fatta da {self.user_name} ({self.user_id}). Risultato: {self.tries} punti{' (perso)' if self.is_lost else ''}."

    @property
    def can_handle_this(self):
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
        return {
            "day": self.day,
            "name": self._name,
            "timestamp": self.timestamp,
            "tries": self.tries,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "stars": self.stars,
        }


@dataclass
class Wordle(Giochino):
    examples = [
        "Wordle 1,011 5/6\n\n🟩🟩⬛️⬛️⬛️\n🟩🟩🟨⬛️⬛️\n🟩🟩⬛️🟨⬛️\n🟩🟩⬛️🟩🟩\n🟩🟩🟩🟩🟩",
        "Wordle 821 X/6\n\n🟨🟩⬛️⬛️⬛️\n⬛️🟩🟩⬛️⬛️\n⬛️🟩🟩⬛️⬛️\n⬛️🟩🟩⬛️⬛️\n⬛️🟩🟩⬛️⬛️\n⬛️🟩🟩🟩⬛️",
    ]
    expected = [
        {"day": "1011", "name": "Wordle", "timestamp": 10, "tries": "5", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "821", "name": "Wordle", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
    ]

    _name = "Wordle"
    _emoji = "🆒"
    _category = "Giochi di parole"
    _date = datetime.date(2023, 6, 23)
    _day = "734"
    _url = "https://www.nytimes.com/games/wordle/index.html"

    has_extra: False
    can_lose: True

    def __init__(self, update):
        self.update = update
        self.raw_text = self.update.message.text

        if self.can_handle_this:
            self.parse()

    @property
    def can_handle_this(self):
        _can_handle_this = "Wordle" in self.raw_text and "/" in self.raw_text
        return _can_handle_this

    @property
    def is_lost(self):
        return self.tries == "X"

    def parse(self):
        text = self.raw_text
        timestamp = int(datetime.datetime.timestamp(self.update.effective_message.date))
        lines = text.splitlines()
        first_line = lines[0].split()
        # Wordle ti odio, chi cazzo scrive 1000 come "1.000" o "1,000"
        self.day = first_line[1].replace(".", "").replace(",", "")
        self.tries = first_line[-1].split("/")[0]
        self.stars = None
        self.timestamp = timestamp if timestamp else int(time.time())
        self.user_name = self.update.message.from_user.full_name
        self.user_id = self.update.message.from_user.id


@dataclass
class Parole(Giochino):
    examples = [
        "Par🇮🇹le 825 4/6\n\n⬜️⬜️⬜️⬜️🟨\n⬜️🟨🟨⬜️⬜️\n🟩🟩🟩⬜️🟩\n🟩🟩🟩🟩🟩",
        "Par🇮🇹le 813 X/6\n\n⬜️🟨🟨⬜️⬜️\n🟨🟩⬜️⬜️🟩\n⬜️🟩🟩⬜️🟩\n⬜️🟩🟩⬜️🟩\n⬜️🟩🟩⬜️🟩\n🟩🟩🟩⬜️🟩",
    ]
    expected = [
        {"day": "825", "name": "Parole", "timestamp": 10, "tries": "4", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "813", "name": "Parole", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
    ]

    _name = "Parole"
    _category = "Giochi di parole"
    _date = datetime.date(2023, 9, 30)
    _day = "635"
    _emoji = "🇮🇹"
    _url = "https://par-le.github.io/gioco/"

    has_extra: False
    can_lose: True

    def __init__(self, update):
        self.update = update
        self.raw_text = self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

    @property
    def can_handle_this(self):
        lines = self.raw_text.splitlines()
        _can_handle_this = "Par🇮🇹le" in lines[0]
        return _can_handle_this

    @property
    def is_lost(self):
        return self.tries == "X"

    def parse(self):
        text = self.raw_text
        timestamp = int(datetime.datetime.timestamp(self.update.effective_message.date))
        self.user_name = self.update.message.from_user.full_name
        self.user_id = self.update.message.from_user.id
        self.timestamp = timestamp if timestamp else int(time.time())

        lines = text.splitlines()
        first_line = lines[0].split()
        self.day = first_line[1]
        self.tries = first_line[2].split("/")[0]


@dataclass
class Bandle(Giochino):
    examples = [
        "Bandle #597 4/6\n⬛️⬛️⬛️🟩⬜️⬜️\nFound: 10/14 (71.4%)\nCurrent Streak: 1 (max 2)\n#Bandle #Heardle #Wordle \n https://bandle.app/"
        "Bandle #579 x/6\n⬛️⬛️⬛️⬛️⬛️⬛️\nFound: 3/5 (60%)\n#Bandle #Heardle #Wordle \n https://bandle.app/"
    ]
    expected = [
        {"day": "597", "name": "Bandle", "timestamp": 10, "tries": "4", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "579", "name": "Bandle", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
    ]

    _name = "Bandle"
    _category = "Immagini, giochi e film"
    _date = datetime.date(2024, 3, 3)
    _day = "564"
    _emoji = "🎸"
    _url = "https://bandle.app/"

    has_extra: False
    can_lose: True

    def __init__(self, update):
        self.update = update
        self.raw_text = self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

    @property
    def can_handle_this(self):
        lines = self.raw_text.splitlines()
        _can_handle_this = "Bandle #" in lines[0] and "https://bandle.app/" in lines[-1]
        return _can_handle_this

    @property
    def is_lost(self):
        return self.tries == "X"

    def parse(self):
        text = self.raw_text
        timestamp = int(datetime.datetime.timestamp(self.update.effective_message.date))
        self.user_name = self.update.message.from_user.full_name
        self.user_id = self.update.message.from_user.id
        self.timestamp = timestamp if timestamp else int(time.time())

        lines = text.splitlines()
        first_line = lines[0].split()
        self.day = first_line[1][1:]
        punti = first_line[2].split("/")[0]
        if punti == "x":
            self.tries = first_line[2].split("/")[0]
        else:
            self.tries = punti


@dataclass
class Chrono(Giochino):
    examples = [
        "🥇 CHRONO  #749\n\n🟢🟢🟢🟢🟢🟢\n\n⏱: 50.8\n🔥: 3\nhttps://chrono.quest",
        "🥈 CHRONO  #760\n\n🟢🟢🟢🟢⚪️⚪️\n🟢🟢🟢🟢🟢🟢\n\n⏱: 33.3\n🔥: 1\nhttps://chrono.quest",
        "🥉 CHRONO  #748\n\n🟢🟢⚪️⚪️⚪️🟢\n🟢🟢⚪️⚪️🟢🟢\n🟢🟢🟢🟢🟢🟢\n\n⏱: 55.8\n🔥: 2\nhttps://chrono.quest",
        "😬 CHRONO  #748\n\n🟢⚪️🟢⚪️⚪️🟢\n🟢⚪️⚪️⚪️🟢🟢\n🟢⚪️⚪️⚪️🟢🟢\n\n⏱: 81.8\n🔥: 0\nhttps://chrono.quest",
    ]
    expected = [
        {
            "day": "749",
            "name": "Chrono",
            "stars": 9949.2,
            "timestamp": 10,
            "tries": 1,
            "user_id": 456481297,
            "user_name": "Trifase",
        },
        {
            "day": "760",
            "name": "Chrono",
            "stars": 9966.7,
            "timestamp": 10,
            "tries": 2,
            "user_id": 456481297,
            "user_name": "Trifase",
        },
        {
            "day": "748",
            "name": "Chrono",
            "stars": 9944.2,
            "timestamp": 10,
            "tries": 3,
            "user_id": 456481297,
            "user_name": "Trifase",
        },
        {"day": "748", "name": "Chrono", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
    ]

    _name = "Chrono"
    _category = "Logica"
    _date = datetime.date(2024, 3, 4)
    _day = "734"
    _emoji = "⏱️"
    _url = "https://chrono.quest"

    has_extra: True
    can_lose: True

    def __init__(self, update):
        self.update = update
        self.raw_text = self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

    @property
    def can_handle_this(self):
        lines = self.raw_text.splitlines()
        _can_handle_this = "CHRONO  #" in lines[0] and "https://chrono.ques" in lines[-1]
        return _can_handle_this

    @property
    def is_lost(self):
        return self.tries == "X"

    def parse(self):
        text = self.raw_text
        timestamp = int(datetime.datetime.timestamp(self.update.effective_message.date))
        self.user_name = self.update.message.from_user.full_name
        self.user_id = self.update.message.from_user.id
        self.timestamp = timestamp if timestamp else int(time.time())

        lines = text.splitlines()
        first_line = lines[0].split()
        self.day = first_line[2][1:]
        punti = first_line[0]
        if punti == "😬":
            self.tries = "X"
        elif punti == "🥉":
            self.tries = 3
        elif punti == "🥈":
            self.tries = 2
        elif punti == "🥇":
            self.tries = 1
        if self.tries in [1, 2, 3] and len(lines) >= 4:
            for line in lines:
                if line.startswith("⏱"):
                    self.stars = 10_000 - float(line.split(":")[-1].strip())
                    break


@dataclass
class Contexto(Giochino):
    examples = [
        "I played contexto.me #556 and got it in 57 guesses.\n\n🟩🟩 11\n🟨🟨 10\n🟥🟥🟥🟥🟥🟥 36",
        "I played contexto.me #522 and got it in 39 guesses and 1 hints.\n\n🟩 9\n🟨 9\n🟥🟥🟥 22",
        "I played contexto.me #471 and got it in 42 guesses and 15 hints.\n\n🟩🟩 25\n🟨 12\n🟥🟥 20",
        "I played contexto.me #465 but I gave up in 31 guesses and 10 hints.\n\n🟩🟩🟩 22\n🟨 10\n🟥 9",
    ]
    expected = [
        {"day": "556", "name": "Contexto", "timestamp": 10, "tries": "57", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "522", "name": "Contexto", "timestamp": 10, "tries": 54, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "471", "name": "Contexto", "timestamp": 10, "tries": 267, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "465", "name": "Contexto", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
    ]

    _name = "Contexto"
    _category = "Giochi di parole"
    _date = datetime.date(2023, 6, 23)
    _day = "278"
    _emoji = "🔄"
    _url = "https://contexto.me"

    has_extra: False
    can_lose: True

    def __init__(self, update):
        self.update = update
        self.raw_text = self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

    @property
    def can_handle_this(self):
        lines = self.raw_text.splitlines()
        _can_handle_this = "contexto.me" in lines[0]
        return _can_handle_this

    @property
    def is_lost(self):
        return self.tries == "X"

    def parse(self):
        text = self.raw_text
        timestamp = int(datetime.datetime.timestamp(self.update.effective_message.date))
        self.user_name = self.update.message.from_user.full_name
        self.user_id = self.update.message.from_user.id
        self.timestamp = timestamp if timestamp else int(time.time())

        lines = text.splitlines()
        first_line = lines[0].split()
        self.day = first_line[3][1:]
        if first_line[4] == "but":
            self.tries = "X"
        elif first_line[-1] == "hints.":
            tips = int(first_line[-2])
            index = first_line.index("guesses")
            self.tries = int(first_line[index - 1]) + (tips * 15)
        else:
            self.tries = first_line[-2]


@dataclass
class Stepdle(Giochino):
    examples = [
        "Stepdle #536\n16/20 4-4 5-3 6-4 7-5\n⬜️⬜️🟨⬜️\n🟩⬜️🟩⬜️\n🟩⬜️🟩🟩\n🟩🟩🟩🟩\n⬜️🟨⬜️⬜️🟨\n⬜️🟩🟩⬜️🟩\n🟩🟩🟩🟩🟩\n⬜️⬜️⬜️⬜️🟨🟨\n⬜️⬜️🟨🟩⬜️⬜️\n🟩🟩⬜️🟩🟨⬜️\n🟩🟩🟩🟩🟩🟩\n⬜️🟨⬜️🟨⬜️⬜️🟨\n⬜️🟨🟨⬜️⬜️🟨⬜️\n🟨⬜️🟨⬜️⬜️🟨⬜️\n⬜️🟨🟨⬜️⬜️🟩🟨\n🟩🟩🟩🟩🟩🟩🟩",
        "Stepdle #537\n20/20 4-4 5-7 6-5 7-4\n🟨⬜️⬜️⬜️\n⬜️⬜️⬜️🟩\n🟩🟩⬜️🟩\n🟩🟩🟩🟩\n🟨🟩⬜️⬜️🟩\n⬜️🟩🟩⬜️🟩\n⬜️🟩🟩⬜️🟩\n⬜️🟩🟩⬜️🟩\n⬜️🟩🟩⬜️🟩\n🟩🟩🟩⬜️🟩\n🟩🟩🟩🟩🟩\n⬜️⬜️🟨🟨⬜️🟨\n⬜️⬜️🟨⬜️🟩⬜️\n⬜️🟩⬜️🟨⬜️🟨\n🟩🟩⬜️⬜️🟩🟨\n🟩🟩🟩🟩🟩🟩\n⬜️⬜️🟨⬜️⬜️⬜️⬜️\n🟩🟨⬜️⬜️⬜️🟨⬜️\n🟩🟨🟨⬜️⬜️⬜️⬜️\n🟩🟩🟩🟩🟩🟩🟩",
        "Stepdle #536\n20/20 4-6 5-9 6-3 7-2\n⬜️🟨🟨⬜️\n🟨⬜️🟨🟨\n🟩🟩🟩⬜️\n🟩🟩🟩⬜️\n🟩🟩🟩⬜️\n🟩🟩🟩🟩\n⬜️⬜️⬜️⬜️⬜️\n⬜️⬜️⬜️⬜️🟩\n⬜️🟩⬜️⬜️🟩\n⬜️🟨🟨⬜️🟩\n⬜️🟩⬜️⬜️🟩\n🟨🟩⬜️⬜️🟩\n⬜️🟩🟨⬜️🟩\n🟩🟩⬜️🟩🟩\n🟩🟩🟩🟩🟩\n⬜️⬜️⬜️⬜️⬜️🟩\n⬜️🟩🟨⬜️🟨⬜️\n🟩🟩🟩🟩🟩🟩\n⬜️🟨🟨⬜️⬜️🟨⬜️\n⬜️⬜️🟨⬜️🟨🟩🟨",
    ]
    expected = [
        {"day": "536", "name": "Stepdle", "timestamp": 10, "tries": "16", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "537", "name": "Stepdle", "timestamp": 10, "tries": "20", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "536", "name": "Stepdle", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
    ]

    _name = "Stepdle"
    _category = "Giochi di parole"
    _date = datetime.date(2024, 3, 5)
    _day = "537"
    _emoji = "🗼"
    _url = "https://www.stepdle.com"

    has_extra: False
    can_lose: True

    def __init__(self, update):
        self.update = update
        self.raw_text = self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

    @property
    def can_handle_this(self):
        lines = self.raw_text.splitlines()
        _can_handle_this = "Stepdle #" in lines[0]
        return _can_handle_this

    @property
    def is_lost(self):
        return self.tries == "X"

    def parse(self):
        text = self.raw_text
        timestamp = int(datetime.datetime.timestamp(self.update.effective_message.date))
        self.user_name = self.update.message.from_user.full_name
        self.user_id = self.update.message.from_user.id
        self.timestamp = timestamp if timestamp else int(time.time())

        lines = text.splitlines()
        first_line = lines[0].split()
        self.day = first_line[1][1:]
        count = lines[-1].count("🟩")
        won = count == 7
        if won:
            punti = lines[1].split()[0].split("/")[0]
            self.tries = punti
        else:
            self.tries = "X"


@dataclass
class Waffle(Giochino):
    examples = [
        "#waffle807 1/5\n\n🟩🟩🟩🟩🟩\n🟩⬜️🟩⬜️🟩\n🟩🟩⭐️🟩🟩\n🟩⬜️🟩⬜️🟩\n🟩🟩🟩🟩🟩\n\n🔥 streak: 2\nwafflegame.net",
        "#waffle807 5/5\n\n🟩🟩🟩🟩🟩\n🟩⭐️🟩⭐️🟩\n🟩🟩⭐️🟩🟩\n🟩⭐️🟩⭐️🟩\n🟩🟩🟩🟩🟩\n\n🔥 streak: 1\nwafflegame.net",
        "#waffle629 X/5\n\n🟩🟩🟩🟩🟩\n🟩⬜️🟩⬜️🟩\n🟩🟩🟩🟩🟩\n🟩⬜️🟩⬜️🟩\n🟩⬛️🟩⬛️🟩\n\n💔 streak: 0\nwafflegame.net",
    ]
    expected = [
        {
            "day": "807",
            "name": "Waffle",
            "stars": 1,
            "timestamp": 10,
            "tries": 14,
            "user_id": 456481297,
            "user_name": "Trifase",
        },
        {
            "day": "807",
            "name": "Waffle",
            "stars": 5,
            "timestamp": 10,
            "tries": 10,
            "user_id": 456481297,
            "user_name": "Trifase",
        },
        {
            "day": "629",
            "name": "Waffle",
            "stars": 0,
            "timestamp": 10,
            "tries": "X",
            "user_id": 456481297,
            "user_name": "Trifase",
        },
    ]

    _name = "Waffle"
    _category = "Giochi di parole"
    _date = datetime.date(2023, 6, 23)
    _day = "518"
    _emoji = "🧇"
    _url = "https://wafflegame.net/daily"

    has_extra: False
    can_lose: True

    def __init__(self, update):
        self.update = update
        self.raw_text = self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

    @property
    def can_handle_this(self):
        lines = self.raw_text.splitlines()
        _can_handle_this = "#waffle" in lines[0]
        return _can_handle_this

    @property
    def is_lost(self):
        return self.tries == "X"

    def parse(self):
        text = self.raw_text
        timestamp = int(datetime.datetime.timestamp(self.update.effective_message.date))
        self.user_name = self.update.message.from_user.full_name
        self.user_id = self.update.message.from_user.id
        self.timestamp = timestamp if timestamp else int(time.time())

        lines = text.splitlines()
        first_line = lines[0].split()
        self.day = first_line[0].replace("#waffle", "")
        punti = first_line[1].split("/")[0]
        self.tries = 15 - int(punti) if punti != "X" else "X"
        self.stars = text.count(b"\xe2\xad\x90".decode("utf-8"))


@dataclass
class HighFive(Giochino):
    examples = ["🖐 I scored 27 points on today's HighFive! Can you beat me?\n\n🟠🟠\n🟢🟢🟢🟢\n🔵\n🟣🟣🟣🟣🟣\n\nhttps://highfivegame.app/2024-02-28"]
    expected = [{"day": "350", "name": "HighFive", "timestamp": 10, "tries": "-27", "user_id": 456481297, "user_name": "Trifase"}]

    _name = "HighFive"
    _category = "Giochi di parole"
    _date = datetime.date(2023, 6, 23)
    _day = "100"
    _emoji = "🖐️"
    _url = "https://highfivegame.app"

    has_extra: False
    can_lose: False

    def __init__(self, update):
        self.update = update
        self.raw_text = self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

    @property
    def can_handle_this(self):
        lines = self.raw_text.splitlines()
        _can_handle_this = "https://highfivegame.app/2" in lines[-1]
        return _can_handle_this

    @property
    def is_lost(self):
        return self.tries == "X"

    def parse(self):
        text = self.raw_text
        timestamp = int(datetime.datetime.timestamp(self.update.effective_message.date))
        self.user_name = self.update.message.from_user.full_name
        self.user_id = self.update.message.from_user.id
        self.timestamp = timestamp if timestamp else int(time.time())

        lines = text.splitlines()
        self.day = get_day_from_date(self._date, self._day, "HighFive", lines[-1])
        self.tries = str(0 - int(lines[0].split()[3]))
        self.stars = None


@dataclass
class Polygonle(Giochino):
    examples = [
        "#Polygonle 614 🎯/6\n\u2005◥\u2005\u2004⬢\u2004\u2005◢\u2005\u2005◣\u2005\u2005◆\u2005\u2005◢\u2005\u2005◣\u2005\u2005◆\u2005\n🟩🟩🟩🟩🟩🟩🟩🟩\n\n🔥 streak:4\nhttps://www.polygonle.com",
        "#Polygonle 613 3/6\n\u2005◥\u2005\u2005◣\u2005\u2005◥\u2005\u2004⬢\u2004\u2005◤\u2005\u2005◢\u2005\u2005◣\u2005\n⬜️⬜️⬜️🟨⬜️⬜️⬜️\n🟩⬜️🟩⬜️⬜️🟨🟨\n🟩🟩🟩🟩🟩🟩🟩\n\n🔥 streak:24\nhttps://www.polygonle.com",
        "#Polygonle 617 😔/6\n\u2004⬢\u2004\u2005◢\u2005\u2005◥\u2005\u2005◥\u2005\u2005◤\u2005\u2005◥\u2005\u2005◢\u2005\n⬜️⬜️⬜️⬜️⬜️🟨⬜️\n⬜️🟩⬜️🟨⬜️⬜️⬜️\n⬜️⬜️⬜️⬜️⬜️🟩⬜️\n⬜️⬜️🟨⬜️🟩🟩⬜️\n⬜️⬜️⬜️⬜️🟨⬜️⬜️\n⬜️⬜️⬜️⬜️⬜️🟩⬜️\nhttps://www.polygonle.com",
    ]
    expected = [
        {"day": "614", "name": "Polygonle", "timestamp": 10, "tries": "1", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "613", "name": "Polygonle", "timestamp": 10, "tries": "3", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "617", "name": "Polygonle", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
    ]

    _name = "Polygonle"
    _category = "Giochi di parole"
    _date = datetime.date(2024, 3, 5)
    _day = "583"
    _emoji = "🔷"
    _url = "https://www.polygonle.com"

    has_extra: False
    can_lose: True

    def __init__(self, update):
        self.update = update
        self.raw_text = self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

    @property
    def can_handle_this(self):
        lines = self.raw_text.splitlines()
        _can_handle_this = "#Polygonle" in lines[0] and "/" in lines[0]
        return _can_handle_this

    @property
    def is_lost(self):
        return self.tries == "X"

    def parse(self):
        text = self.raw_text
        timestamp = int(datetime.datetime.timestamp(self.update.effective_message.date))
        self.user_name = self.update.message.from_user.full_name
        self.user_id = self.update.message.from_user.id
        self.timestamp = timestamp if timestamp else int(time.time())

        lines = text.splitlines()
        first_line = lines[0].split()
        self.day = first_line[1]
        punti = first_line[2].split("/")[0]

        if punti == "X" or punti == "😔":
            self.tries = "X"
        elif punti == "🎯":
            self.tries = "1"
        else:
            self.tries = punti


@dataclass
class Connections(Giochino):
    examples = [
        "Connections \nPuzzle #299\n🟩🟩🟩🟩\n🟨🟨🟨🟨\n🟦🟦🟦🟦\n🟪🟪🟪🟪",
        "Connections \nPuzzle #300\n🟩🟪🟩🟩\n🟩🟪🟩🟩\n🟩🟪🟩🟩\n🟩🟩🟩🟩\n🟦🟦🟦🟦\n🟪🟪🟪🟪\n🟨🟨🟨🟨",
        "Connections \nPuzzle #302\n🟨🟨🟨🟨\n🟪🟩🟪🟪\n🟪🟪🟪🟦\n🟪🟦🟪🟪\n🟪🟪🟩🟪",
    ]
    expected = [
        {"day": "299", "name": "Connections", "timestamp": 10, "tries": 1, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "300", "name": "Connections", "timestamp": 10, "tries": 4, "user_id": 456481297, "user_name": "Trifase"},
        {
            "day": "302",
            "name": "Connections",
            "timestamp": 10,
            "tries": "X",
            "user_id": 456481297,
            "user_name": "Trifase",
        },
    ]

    _name = "Connections"
    _category = "Giochi di parole"
    _date = datetime.date(2023, 9, 18)
    _day = "99"
    _emoji = "🔀"
    _url = "https://www.nytimes.com/games/connections"

    has_extra: False
    can_lose: True

    def __init__(self, update):
        self.update = update
        self.raw_text = self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

    @property
    def can_handle_this(self):
        lines = self.raw_text.splitlines()
        _can_handle_this = "Connections" in lines[0]
        return _can_handle_this

    @property
    def is_lost(self):
        return self.tries == "X"

    def parse(self):
        text = self.raw_text
        timestamp = int(datetime.datetime.timestamp(self.update.effective_message.date))
        self.user_name = self.update.message.from_user.full_name
        self.user_id = self.update.message.from_user.id
        self.timestamp = timestamp if timestamp else int(time.time())

        lines = text.splitlines()
        self.day = lines[1].split()[-1][1:]
        points = lines[2:]
        if is_connection_completed(points):
            self.tries = len(points) - 3
        else:
            self.tries = "X"


@dataclass
class Squareword(Giochino):
    examples = [
        "squareword.org 777: 14 guesses\n\n🟩🟨🟩🟧🟨\n🟨🟩🟧🟧🟧\n🟨🟧🟨🟧🟩\n🟨🟨🟨🟨🟩\n🟧🟨🟨🟨🟩\n\nless6:🟩 less11:🟨 less16:🟧 16+:🟥\n#squareword #squareword777",
        "squareword.org 793: 7 guesses\n\n🟩🟩🟩🟩🟩\n🟨🟨🟩🟨🟨\n🟩🟩🟩🟩🟩\n🟩🟩🟩🟩🟩\n🟨🟨🟨🟨🟨\n\nless6:🟩 less11:🟨 less16:🟧 16+:🟥\n#squareword #squareword793",
    ]
    expected = [
        {
            "day": "777",
            "name": "Squareword",
            "timestamp": 10,
            "tries": "14",
            "user_id": 456481297,
            "user_name": "Trifase",
        },
        {
            "day": "793",
            "name": "Squareword",
            "timestamp": 10,
            "tries": "7",
            "user_id": 456481297,
            "user_name": "Trifase",
        },
    ]

    _name = "Squareword"
    _category = "Giochi di parole"
    _date = datetime.date(2023, 9, 25)
    _day = "602"
    _emoji = "🔠"
    _url = "https://squareword.org"

    has_extra: False
    can_lose: False

    def __init__(self, update):
        self.update = update
        self.raw_text = self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

    @property
    def can_handle_this(self):
        lines = self.raw_text.splitlines()
        _can_handle_this = "squareword.org" in lines[0]
        return _can_handle_this

    @property
    def is_lost(self):
        return self.tries == "X"

    def parse(self):
        text = self.raw_text
        timestamp = int(datetime.datetime.timestamp(self.update.effective_message.date))
        self.user_name = self.update.message.from_user.full_name
        self.user_id = self.update.message.from_user.id
        self.timestamp = timestamp if timestamp else int(time.time())

        lines = text.splitlines()
        first_line = lines[0].split()
        self.day = first_line[1][:-1]
        self.tries = first_line[2]
        self.stars = None


@dataclass
class Worldle(Giochino):
    examples = [
        "#Worldle #807 (07.04.2024) 1/6 (100%)\n🟩🟩🟩🟩🟩🎉\n🧭⭐\nhttps://worldle.teuteuf.fr",
        "#Worldle #808 (08.04.2024) 4/6 (100%)\n🟩🟩🟩🟨⬜↗️\n🟩🟩🟩🟩🟨↘️\n🟩🟩🟩🟩🟨⬇️\n🟩🟩🟩🟩🟩🎉\n\nhttps://worldle.teuteuf.fr",
        "#Worldle #808 (08.04.2024) X/6 (94%)\n🟩🟩🟩⬛️⬛️⬆️\n🟩🟩🟩🟩⬛️↖️\n🟩🟩🟩🟩🟨↖️\n🟩🟩🟨⬛️⬛️↗️\n🟩🟨⬛️⬛️⬛️↗️\n🟩🟩🟩🟩🟨➡️\n\nhttps://worldle.teuteuf.fr",
    ]
    expected = [
        {
            "day": "807",
            "name": "Worldle",
            "stars": 2,
            "timestamp": 10,
            "tries": "1",
            "user_id": 456481297,
            "user_name": "Trifase",
        },
        {
            "day": "808",
            "name": "Worldle",
            "stars": 0,
            "timestamp": 10,
            "tries": "4",
            "user_id": 456481297,
            "user_name": "Trifase",
        },
        {
            "day": "808",
            "name": "Worldle",
            "stars": 0,
            "timestamp": 10,
            "tries": "X",
            "user_id": 456481297,
            "user_name": "Trifase",
        },
    ]

    _name = "Worldle"
    _category = "Geografia e Mappe"
    _date = datetime.date(2023, 6, 23)
    _day = "518"
    _emoji = "🗺️"
    _url = "https://worldle.teuteuf.fr"

    has_extra: False
    can_lose: True

    def __init__(self, update):
        self.update = update
        self.raw_text = self.update.message.text

        if self.can_handle_this:
            self.parse()

    @property
    def can_handle_this(self):
        lines = self.raw_text.splitlines()
        _can_handle_this = "Worldle" in lines[0]
        return _can_handle_this

    @property
    def is_lost(self):
        return self.tries == "X"

    def parse(self):
        text = self.raw_text
        timestamp = int(datetime.datetime.timestamp(self.update.effective_message.date))
        self.user_name = self.update.message.from_user.full_name
        self.user_id = self.update.message.from_user.id
        self.timestamp = timestamp if timestamp else int(time.time())

        lines = text.splitlines()
        first_line = lines[0].split()
        self.day = first_line[1][1:]
        self.tries = first_line[3].split("/")[0]
        bussola = text.count(b"\xf0\x9f\xa7\xad".decode("utf-8"))  # 🧭
        stars = text.count(b"\xe2\xad\x90".decode("utf-8"))  # ⭐️
        flag = text.count(b"\xf0\x9f\x9a\xa9".decode("utf-8"))  # 🚩
        abc = text.count(b"\xf0\x9f\x94\xa4".decode("utf-8"))  # 🔤
        language = text.count(b"\xf0\x9f\x97\xa3".decode("utf-8"))  # 🗣
        population = text.count(b"\xf0\x9f\x91\xab".decode("utf-8"))  # 👫
        coin = text.count(b"\xf0\x9f\xaa\x99".decode("utf-8"))  # 🪙
        cityscape = text.count(b"\xf0\x9f\x8f\x99".decode("utf-8"))  # 🏙
        area = text.count(b"\xf0\x9f\x93\x90".decode("utf-8"))  # 📐
        self.stars = bussola + stars + flag + abc + language + population + coin + cityscape + area


# qua
@dataclass
class Tradle(Giochino):
    examples = [
        "#Tradle #761 5/6\n🟩🟩🟨⬜⬜\n🟩🟩🟩🟩⬜\n🟩🟩🟩🟩🟨\n🟩🟩🟩🟩🟨\n🟩🟩🟩🟩🟩\nhttps://games.oec.world/en/tradle",
        "#Tradle #761 X/6\n🟩🟨⬜⬜⬜\n🟩🟩🟩🟨⬜\n🟩🟩🟩🟩🟨\n🟩🟩🟩🟩⬜\n🟩🟩🟩🟩🟨\n🟩🟩🟩🟩🟨\nhttps://games.oec.world/en/tradle",
    ]
    expected = [
        {"day": "761", "name": "Tradle", "timestamp": 10, "tries": "5", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "761", "name": "Tradle", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
    ]

    _name = "Tradle"
    _category = "Geografia e Mappe"
    _date = datetime.date(2023, 6, 23)
    _day = "474"
    _emoji = "🚢"
    _url = "https://oec.world/en/tradle"

    has_extra: False
    can_lose: True

    def __init__(self, update):
        self.update = update
        self.raw_text = self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

    @property
    def can_handle_this(self):
        lines = self.raw_text.splitlines()
        _can_handle_this = "#Tradle" in lines[0]
        return _can_handle_this

    @property
    def is_lost(self):
        return self.tries == "X"

    def parse(self):
        text = self.raw_text
        timestamp = int(datetime.datetime.timestamp(self.update.effective_message.date))
        self.user_name = self.update.message.from_user.full_name
        self.user_id = self.update.message.from_user.id
        self.timestamp = timestamp if timestamp else int(time.time())

        lines = text.splitlines()
        first_line = lines[0].split()
        self.day = first_line[1][1:]
        self.tries = first_line[2].split("/")[0]
        self.stars = None


@dataclass
class Flagle(Giochino):
    examples = [
        "#Flagle #777 (08.04.2024) 1/6\n🟩🟩🟩\n🟩🟩🟩\nhttps://www.flagle.io",
        "#Flagle #773 (04.04.2024) 5/6\n🟥🟩🟥\n🟩🟥🟥\nhttps://www.flagle.io",
        "#Flagle #773 (04.04.2024) X/6\n🟥🟥🟥\n🟥🟥🟥\nhttps://www.flagle.io",
    ]
    expected = [
        {"day": "777", "name": "Flagle", "timestamp": 10, "tries": "1", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "773", "name": "Flagle", "timestamp": 10, "tries": "5", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "773", "name": "Flagle", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
    ]

    _name = "Flagle"
    _category = "Geografia e Mappe"
    _date = datetime.date(2023, 9, 8)
    _day = "564"
    _emoji = "🏁"
    _url = "https://www.flagle.io"

    has_extra: False
    can_lose: True

    def __init__(self, update):
        self.update = update
        self.raw_text = self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

    @property
    def can_handle_this(self):
        lines = self.raw_text.splitlines()
        _can_handle_this = "#Flagle" in lines[0]
        return _can_handle_this

    @property
    def is_lost(self):
        return self.tries == "X"

    def parse(self):
        text = self.raw_text
        timestamp = int(datetime.datetime.timestamp(self.update.effective_message.date))
        self.user_name = self.update.message.from_user.full_name
        self.user_id = self.update.message.from_user.id
        self.timestamp = timestamp if timestamp else int(time.time())

        lines = text.splitlines()
        first_line = lines[0].split()
        self.day = first_line[1][1:]
        self.tries = first_line[3].split("/")[0]
        self.stars = None


@dataclass
class Globle(Giochino):
    examples = [
        "🌎 Mar 30, 2024 🌍\n🔥 1 | Avg. Guesses: 8.94\n🟧🟨🟧🟩 = 4\n\nhttps://globle-game.com\n#globle",
        "🌎 Mar 5, 2024 🌍\n🔥 1 | Avg. Guesses: 6.88\n🟨🟨🟧🟧🟥🟧🟧🟥\n🟥🟥🟧🟨🟥🟥🟩 = 15\n\nhttps://globle-game.com\n#globle",
    ]
    expected = [
        {"day": "481", "name": "Globle", "timestamp": 10, "tries": "4", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "456", "name": "Globle", "timestamp": 10, "tries": "15", "user_id": 456481297, "user_name": "Trifase"},
    ]

    _name = "Globle"
    _category = "Geografia e Mappe"
    _date = datetime.date(2023, 6, 23)
    _day = "200"
    _emoji = "🌍"
    _url = "https://globle-game.com"

    has_extra: False
    can_lose: False

    def __init__(self, update):
        self.update = update
        self.raw_text = self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

    @property
    def can_handle_this(self):
        lines = self.raw_text.splitlines()
        _can_handle_this = "#globle" in lines[-1]
        return _can_handle_this

    @property
    def is_lost(self):
        return self.tries == "X"

    def parse(self):
        text = self.raw_text
        timestamp = int(datetime.datetime.timestamp(self.update.effective_message.date))
        self.user_name = self.update.message.from_user.full_name
        self.user_id = self.update.message.from_user.id
        self.timestamp = timestamp if timestamp else int(time.time())

        lines = text.splitlines()
        self.day = get_day_from_date(self._date, self._day, "Globle", lines[0])
        for line in lines:
            if "=" in line:
                self.tries = line.split("=")[-1][1:]
        self.stars = None


# qua
@dataclass
class WhereTaken(Giochino):
    examples = [
        "📷 #WhereTaken🌎 #407 (08.04.2024) X/6\n🟦🟦🟦🟦🟨⬅️\n🟦🟦🟦🟦⬜️⬅️\n🟦🟦🟦🟦⬜️⬅️\n🟦🟦🟦🟦⬜️↖️\n🟦🟦🟦🟦⬜️⬅️\n🟦🟦🟨⬜️⬜️↖️\n\n\nwheretaken.teuteuf.fr",
        "📷 #WhereTaken🌎 #407 (08.04.2024) X/6\n🟦🟦🟦🟦🟨⬅️\n🟦🟦🟦🟦⬜️⬅️\n🟦🟦🟦🟦⬜️⬅️\n🟦🟦🟦🟦⬜️↖️\n🟦🟦🟦🟦⬜️⬅️\n🟦🟦🟨⬜️⬜️↖️\n⭐️⭐️\n\nwheretaken.teuteuf.fr",
        "📷 #WhereTaken🌎 #399 (31.03.2024) 1/6\n🟦🟦🟦🟦🟦🎉\n⭐⭐⭐⭐\n\nwheretaken.teuteuf.fr",
        "📷 #WhereTaken🌎 #398 (30.03.2024) 4/6\n🟦🟦🟦🟦🟨➡️\n🟦🟦🟦🟦🟨➡️\n🟦🟦🟦🟦🟨↖️\n🟦🟦🟦🟦🟦🎉\n⭐️\n\nwheretaken.teuteuf.fr",
    ]
    expected = [
        {
            "day": "407",
            "name": "WhereTaken",
            "stars": 0,
            "timestamp": 10,
            "tries": "X",
            "user_id": 456481297,
            "user_name": "Trifase",
        },
        {
            "day": "407",
            "name": "WhereTaken",
            "stars": 2,
            "timestamp": 10,
            "tries": "X",
            "user_id": 456481297,
            "user_name": "Trifase",
        },
        {
            "day": "399",
            "name": "WhereTaken",
            "stars": 4,
            "timestamp": 10,
            "tries": "1",
            "user_id": 456481297,
            "user_name": "Trifase",
        },
        {
            "day": "398",
            "name": "WhereTaken",
            "stars": 1,
            "timestamp": 10,
            "tries": "4",
            "user_id": 456481297,
            "user_name": "Trifase",
        },
    ]

    _name = "WhereTaken"
    _category = "Geografia e Mappe"
    _date = datetime.date(2023, 6, 23)
    _day = "117"
    _emoji = "📸"
    _url = "http://wheretaken.teuteuf.fr"

    has_extra: True
    can_lose: True

    def __init__(self, update):
        self.update = update
        self.raw_text = self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

    @property
    def can_handle_this(self):
        lines = self.raw_text.splitlines()
        _can_handle_this = "WhereTaken" in lines[0]
        return _can_handle_this

    @property
    def is_lost(self):
        return self.tries == "X"

    def parse(self):
        text = self.raw_text
        timestamp = int(datetime.datetime.timestamp(self.update.effective_message.date))
        self.user_name = self.update.message.from_user.full_name
        self.user_id = self.update.message.from_user.id
        self.timestamp = timestamp if timestamp else int(time.time())

        lines = text.splitlines()
        first_line = lines[0].split()
        self.day = first_line[2][1:]
        self.tries = first_line[4].split("/")[0]
        self.stars = text.count(b"\xe2\xad\x90".decode("utf-8"))


@dataclass
class Cloudle(Giochino):
    _name = "Cloudle"
    _category = "Geografia e Mappe"
    _date = datetime.date(2023, 6, 23)
    _day = "449"
    _emoji = "🌦️"
    _url = "https://cloudle.app"

    examples = [
        "Cloudle - Bujumbura, Burundi: 4/6\n\n⚫⚫⚫⚫🟢\n⚫⚫🟢🟢🟢\n⚫🟢🟢🟢🟢\n🟢🟢🟢🟢🟢\n https://cloudle.app/",
        "Cloudle - Milan, Italy: X/6\n\n🟢⚫⚫🟢🟢\n🟢⚫⚫🟢🟢\n🟢⚫🟢🟢🟢\n🟢⚫🟢🟢🟢\n🟢⚫🟢🟢🟢\n🟢⚫🟢🟢🟢\n https://cloudle.app/",
    ]
    # Cloudle is the only game without a day - we assume that the date is today.
    expected = [
        {
            "day": f'{get_day_from_date(_date, _day, "Cloudle", datetime.date.today())}',
            "name": "Cloudle",
            "timestamp": 10,
            "tries": "4",
            "user_id": 456481297,
            "user_name": "Trifase",
        },
        {
            "day": f'{get_day_from_date(_date, _day, "Cloudle", datetime.date.today())}',
            "name": "Cloudle",
            "timestamp": 10,
            "tries": "X",
            "user_id": 456481297,
            "user_name": "Trifase",
        },
    ]

    has_extra: False
    can_lose: True

    def __init__(self, update):
        self.update = update
        self.raw_text = self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

    @property
    def can_handle_this(self):
        lines = self.raw_text.splitlines()
        _can_handle_this = "Cloudle -" in lines[0]
        return _can_handle_this

    @property
    def is_lost(self):
        return self.tries == "X"

    def parse(self):
        text = self.raw_text
        timestamp = int(datetime.datetime.timestamp(self.update.effective_message.date))
        self.user_name = self.update.message.from_user.full_name
        self.user_id = self.update.message.from_user.id
        self.timestamp = timestamp if timestamp else int(time.time())

        lines = text.splitlines()
        first_line = lines[0].split()
        self.day = get_day_from_date(self._date, self._day, "Cloudle", datetime.date.today())
        self.tries = first_line[-1].split("/")[0]
        self.stars = None


@dataclass
class GuessTheGame(Giochino):
    examples = [
        "#GuessTheGame #693\n\n🎮 🟥 🟥 🟥 🟥 🟥 🟥\n\n#ScreenshotSleuth\nhttps://GuessThe.Game/p/693",
        "#GuessTheGame #695\n\n🎮 🟥 🟥 🟨 🟥 🟥 🟥\n\n#ProGamer\nhttps://GuessThe.Game/p/695",
        "#GuessTheGame #692\n\n🎮 🟩 ⬜ ⬜ ⬜ ⬜ ⬜\n\n#ProGamer\nhttps://GuessThe.Game/p/692",
        "#GuessTheGame #684\n\n🎮 🟥 🟥 🟥 🟨 🟩 ⬜\n\n#ProGamer\nhttps://GuessThe.Game/p/684",
    ]
    expected = [
        {
            "day": "693",
            "name": "GuessTheGame",
            "timestamp": 10,
            "tries": "X",
            "user_id": 456481297,
            "user_name": "Trifase",
        },
        {
            "day": "695",
            "name": "GuessTheGame",
            "timestamp": 10,
            "tries": "X",
            "user_id": 456481297,
            "user_name": "Trifase",
        },
        {
            "day": "692",
            "name": "GuessTheGame",
            "timestamp": 10,
            "tries": "1",
            "user_id": 456481297,
            "user_name": "Trifase",
        },
        {
            "day": "684",
            "name": "GuessTheGame",
            "timestamp": 10,
            "tries": "5",
            "user_id": 456481297,
            "user_name": "Trifase",
        },
    ]

    _name = "GuessTheGame"
    _category = "Immagini, giochi e film"
    _date = datetime.date(2023, 6, 23)
    _day = "405"
    _emoji = "🎮"
    _url = "https://guessthe.game"

    has_extra: False
    can_lose: True

    def __init__(self, update):
        self.update = update
        self.raw_text = self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

    @property
    def can_handle_this(self):
        lines = self.raw_text.splitlines()
        _can_handle_this = "#GuessTheGame" in lines[0]
        return _can_handle_this

    @property
    def is_lost(self):
        return self.tries == "X"

    def parse(self):
        text = self.raw_text
        timestamp = int(datetime.datetime.timestamp(self.update.effective_message.date))
        self.user_name = self.update.message.from_user.full_name
        self.user_id = self.update.message.from_user.id
        self.timestamp = timestamp if timestamp else int(time.time())

        lines = text.splitlines()
        first_line = lines[0].split()
        self.day = first_line[1][1:]
        punteggio = lines[2].replace(" ", "")
        if "🟩" not in punteggio:
            self.tries = "X"
        else:
            self.tries = str(punteggio.index("🟩"))
        self.stars = None


@dataclass
class Framed(Giochino):
    examples = [
        "Framed #756\n🎥 🟥 🟥 🟥 🟥 🟥 🟥\n\nhttps://framed.wtf",
        "Framed #758\n🎥 🟥 🟥 🟥 🟩 ⬛ ⬛\n\nhttps://framed.wtf",
    ]
    expected = [
        {"day": "756", "name": "Framed", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "758", "name": "Framed", "timestamp": 10, "tries": "4", "user_id": 456481297, "user_name": "Trifase"},
    ]

    _name = "Framed"
    _category = "Immagini, giochi e film"
    _date = datetime.date(2023, 6, 23)
    _day = "469"
    _emoji = "🎞"
    _url = "https://framed.wtf"

    has_extra: False
    can_lose: True

    def __init__(self, update):
        self.update = update
        self.raw_text = self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

    @property
    def can_handle_this(self):
        lines = self.raw_text.splitlines()
        _can_handle_this = "Framed" in lines[0]
        return _can_handle_this

    @property
    def is_lost(self):
        return self.tries == "X"

    def parse(self):
        text = self.raw_text
        timestamp = int(datetime.datetime.timestamp(self.update.effective_message.date))
        self.user_name = self.update.message.from_user.full_name
        self.user_id = self.update.message.from_user.id
        self.timestamp = timestamp if timestamp else int(time.time())

        lines = text.splitlines()
        first_line = lines[0].split()
        self.day = first_line[1][1:]
        punteggio = lines[1].replace(" ", "")
        if "🟩" not in punteggio:
            self.tries = "X"
        else:
            self.tries = str(punteggio.index("🟩"))


@dataclass
class TimeGuessr(Giochino):
    examples = [
        "TimeGuessr #268 33,990/50,000\n🌎🟩⬛️⬛️ 📅🟩⬛⬛\n🌎🟩⬛️⬛️ 📅🟩🟩🟨\n🌎⬛️⬛️⬛️ 📅🟩🟩🟨\n🌎🟩🟩🟨 📅🟩🟨⬛\n🌎🟩🟩🟩 📅🟨⬛️⬛️\nhttps://timeguessr.com",
        "TimeGuessr #282 42,214/50,000\n🌎🟩🟩🟨 📅🟩🟩🟨\n🌎🟩🟩🟨 📅🟩🟩🟨\n🌎🟩🟩🟨 📅🟩🟩🟨\n🌎🟩🟨⬛️ 📅🟩🟩🟩\n🌎⬛️⬛️⬛️ 📅🟩🟨⬛\nhttps://timeguessr.com",
    ]
    expected = [
        {
            "day": "268",
            "name": "TimeGuessr",
            "timestamp": 10,
            "tries": 16010,
            "user_id": 456481297,
            "user_name": "Trifase",
        },
        {
            "day": "282",
            "name": "TimeGuessr",
            "timestamp": 10,
            "tries": 7786,
            "user_id": 456481297,
            "user_name": "Trifase",
        },
    ]

    _name = "TimeGuessr"
    _category = "Immagini, giochi e film"
    _date = datetime.date(2023, 11, 27)
    _day = "179"
    _emoji = "📅"
    _url = "https://timeguessr.com"

    has_extra: False
    can_lose: False

    def __init__(self, update):
        self.update = update
        self.raw_text = self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

    @property
    def can_handle_this(self):
        lines = self.raw_text.splitlines()
        _can_handle_this = "TimeGuessr" in lines[0]
        return _can_handle_this

    @property
    def is_lost(self):
        return self.tries == "X"

    def parse(self):
        text = self.raw_text
        timestamp = int(datetime.datetime.timestamp(self.update.effective_message.date))
        self.user_name = self.update.message.from_user.full_name
        self.user_id = self.update.message.from_user.id
        self.timestamp = timestamp if timestamp else int(time.time())

        lines = text.splitlines()
        first_line = lines[0].split()
        self.day = first_line[1][1:]
        self.tries = 50_000 - int(first_line[2].split("/")[0].replace(",", ""))
        self.stars = None


@dataclass
class Moviedle(Giochino):
    examples = [
        "#Moviedle #2024-03-08 \n\n 🎥 ⬛️ ⬛️ ⬛️ ⬛️ ⬛️ ⬛️  \n\n https://likewisetv.com/arcade/moviedle",
        "#Moviedle #2024-01-29 \n\n 🎥 🟥 🟥 ⬛️ ⬛️ ⬛️ ⬛️  \n\n https://likewisetv.com/arcade/moviedle",
        "#Moviedle #2024-03-07 \n\n 🎥 🟩 ⬜️ ⬜️ ⬜️ ⬜️ ⬜️  \n\n https://likewisetv.com/arcade/moviedle",
        "#Moviedle #2024-01-21 \n\n 🎥 ⬛️ ⬛️ 🟩 ⬜️ ⬜️ ⬜️  \n\n https://likewisetv.com/arcade/moviedle",
    ]
    expected = [
        {"day": "459", "name": "Moviedle", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "420", "name": "Moviedle", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "458", "name": "Moviedle", "timestamp": 10, "tries": "1", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "412", "name": "Moviedle", "timestamp": 10, "tries": "3", "user_id": 456481297, "user_name": "Trifase"},
    ]

    _name = "Moviedle"
    _category = "Immagini, giochi e film"
    _date = datetime.date(2023, 6, 23)
    _day = "200"
    _emoji = "🎥"
    _url = "https://moviedle.app"

    has_extra: False
    can_lose: True

    def __init__(self, update):
        self.update = update
        self.raw_text = self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

    @property
    def can_handle_this(self):
        lines = self.raw_text.splitlines()
        _can_handle_this = "Moviedle" in lines[0]
        return _can_handle_this

    @property
    def is_lost(self):
        return self.tries == "X"

    def parse(self):
        text = self.raw_text
        timestamp = int(datetime.datetime.timestamp(self.update.effective_message.date))
        self.user_name = self.update.message.from_user.full_name
        self.user_id = self.update.message.from_user.id
        self.timestamp = timestamp if timestamp else int(time.time())

        lines = text.splitlines()
        first_line = lines[0].split()
        point_line = lines[2][3:]
        self.day = get_day_from_date(self._date, self._day, "Moviedle", first_line[-1])
        punteggio = point_line.replace(" ", "")
        punteggio_bonificato = ""
        # Moviedle uses black-magic squares that inject empty invisible spaces fugging up the count. We remove them with a whitelisted chars list.
        for char in punteggio:
            if char in ["⬛", "🟥", "🟩", "⬜"]:
                punteggio_bonificato += char
        if "🟩" not in punteggio_bonificato:
            self.tries = "X"
        else:
            self.tries = str(punteggio_bonificato.index("🟩") + 1)


@dataclass
class Picsey(Giochino):
    examples = [
        "Picsey 04.08.24 \nNature : Phenomena \n0p/49t/3g \n🟦🟦🟦🟦🟦🟦🟦 \n🟦🟦🟦🟦🟦🟦🟦 \n🟦🟦🟦🟦🟦🟦🟦 \n🟦🟦🟦🟦🟦🟦🟦 \n🟦🟦🟦🟦🟦🟦🟦 \n🟦🟦🟦🟦🟦🟦🟦 \n🟦🟦🟦🟦🟦🟦🟦 \n🟠🟠🟠",
        "Picsey 04.08.24 \nNature : Phenomena \n66p/4t/2g \n🟦🟦🟦🟦 \n🟠🟠",
        "Picsey 04.07.24 \nIndustry : Companies \n60p/6t/2g \n🟦🟦🟦🟦🟦🟦 \n🟠🟠",
    ]
    expected = [
        {"day": "296", "name": "Picsey", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "296", "name": "Picsey", "timestamp": 10, "tries": 34, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "295", "name": "Picsey", "timestamp": 10, "tries": 40, "user_id": 456481297, "user_name": "Trifase"},
    ]

    _name = "Picsey"
    _category = "Immagini, giochi e film"
    _date = datetime.date(2023, 9, 25)
    _day = "100"
    _emoji = "🪟"
    _url = "https://picsey.io"

    has_extra: False
    can_lose: True

    def __init__(self, update):
        self.update = update
        self.raw_text = self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

    @property
    def can_handle_this(self):
        lines = self.raw_text.splitlines()
        _can_handle_this = "Picsey" in lines[0]
        return _can_handle_this

    @property
    def is_lost(self):
        return self.tries == "X"

    def parse(self):
        text = self.raw_text
        timestamp = int(datetime.datetime.timestamp(self.update.effective_message.date))
        self.user_name = self.update.message.from_user.full_name
        self.user_id = self.update.message.from_user.id
        self.timestamp = timestamp if timestamp else int(time.time())

        lines = text.splitlines()
        date = lines[0].split()[-1]
        self.day = get_day_from_date(self._date, self._day, "Picsey", date)
        points = lines[2].split("p/")[0]
        # Picsey uses positive poits, from 0 to 100. We as usual save 100-n and then revert it when printing the results.
        self.tries = 100 - int(points)
        if int(points) == 0:
            self.tries = "X"
        self.stars = None


@dataclass
class Colorfle(Giochino):
    examples = [
        "Colorfle 679 X/6 \n⬜⬜⬜\n⬜⬜⬜\n⬜⬜⬜\n🟨🟨⬜\n🟩🟩⬜\n🟩🟩⬜\nMy closest guess had a color accuracy of 95.1%!",
        "Colorfle 713 2/6 \n⬜⬜⬜\n🟩🟩🟩\nMy average color accuracy was 96.2%!",
        "Colorfle 711 5/6 \n⬜🟨⬜\n🟨⬜⬜\n🟨⬜🟨\n🟨🟨🟨\n🟩🟩🟩\nMy average color accuracy was 86%!",
    ]
    expected = [
        {"day": "679", "name": "Colorfle", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "713", "name": "Colorfle", "timestamp": 10, "tries": "2", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "711", "name": "Colorfle", "timestamp": 10, "tries": "5", "user_id": 456481297, "user_name": "Trifase"},
    ]

    _name = "Colorfle"
    _category = "Immagini, giochi e film"
    _date = datetime.date(2024, 3, 5)
    _day = "679"
    _emoji = "🎨"
    _url = "https://colorfle.com"

    has_extra: False
    can_lose: True

    def __init__(self, update):
        self.update = update
        self.raw_text = self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

    @property
    def can_handle_this(self):
        lines = self.raw_text.splitlines()
        _can_handle_this = "Colorfle" in lines[0] and "accuracy" in lines[-1]
        return _can_handle_this

    @property
    def is_lost(self):
        return self.tries == "X"

    def parse(self):
        text = self.raw_text
        timestamp = int(datetime.datetime.timestamp(self.update.effective_message.date))
        self.user_name = self.update.message.from_user.full_name
        self.user_id = self.update.message.from_user.id
        self.timestamp = timestamp if timestamp else int(time.time())

        lines = text.splitlines()
        first_line = lines[0].split()
        self.day = first_line[1]
        punti = first_line[2].split("/")[0]
        if punti == "X":
            self.tries = "X"
        else:
            self.tries = punti
        self.stars = None


@dataclass
class Murdle(Giochino):
    examples = [
        "THE CASE OF THE PENCIL\nMurdle for 12/8/2023\n\n👤🔪🏡     🕰️\n✅✅✅     3️⃣:2️⃣0️⃣\n\n⚖️\n👤\n\n\n\nhttps://murdle.com",
        "THE CONFUSING CASE OF THE COWHIDE GLOVE\nMurdle for 11/28/2023\n\n👤🔪🏡❓     🕰️\n✅✅✅✅     7️⃣:2️⃣4️⃣\n\n⚖️\n👤\n\n\n\nhttps://murdle.com",
        "THE MYSTERY OF THE POISONED GOBLET\nMurdle for 10/31/2023\n\n👤🔪🏡❓     🕰\n✅✅❌✅     3️⃣:1️⃣7️⃣\n\n⚖️\n❌\n\n\n\nhttps://murdle.com",
    ]
    expected = [
        {"day": "169", "name": "Murdle", "timestamp": 10, "tries": "320", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "159", "name": "Murdle", "timestamp": 10, "tries": "724", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "131", "name": "Murdle", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
    ]

    _name = "Murdle"
    _category = "Logica"
    _date = datetime.date(2023, 6, 23)
    _day = "1"
    _emoji = "🔪"
    _url = "https://murdle.com"

    has_extra: False
    can_lose: True

    def __init__(self, update):
        self.update = update
        self.raw_text = self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

    @property
    def can_handle_this(self):
        lines = self.raw_text.splitlines()
        _can_handle_this = "Murdle" in lines[1]
        return _can_handle_this

    @property
    def is_lost(self):
        return self.tries == "X"

    def parse(self):
        text = self.raw_text
        timestamp = int(datetime.datetime.timestamp(self.update.effective_message.date))
        self.user_name = self.update.message.from_user.full_name
        self.user_id = self.update.message.from_user.id
        self.timestamp = timestamp if timestamp else int(time.time())

        lines = text.splitlines()
        day = lines[1].split()[-1]
        # Murdle doesn't have a #day, so we parse the date and get our own numeration (Jun 23, 2023 -> 200)
        self.day = get_day_from_date(self._date, self._day, "Murdle", day)
        points_line = lines[4]
        punteggio = points_line.split()[-1]
        if "❌" in points_line:
            self.tries = "X"
        else:
            self.tries = str(time_from_emoji(punteggio))
        self.stars = None


@dataclass
class Rotaboxes(Giochino):
    examples = [
        "🟩🟦🟪 streak: 1\n🟥🟧 clicks: 31/31\n🟨 overspin: 4\nrotabox.es/497\n🟩🟩🟩🟩🟩🟩\n🟩🟩🟩🟩🟩🟩\n🟩🟩🟩🟩🟩🟩\n🟩🟩🟩🟩🟩🟩",
        "🟩🟦🟪 streak: 2\n🟥🟧 clicks: 122/31\n🟨 overspin: 45.5\nrotabox.es/497\n🟨🟩🟧🟩🟥🟨\n🟧🟩🟨🟩🟩🟨\n🟥🟥🟥🟥🟨🟥\n🟧🟥🟨🟨🟥🟧",
    ]
    expected = [
        {"day": "497", "name": "Rotaboxes", "timestamp": 10, "tries": 31, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "497", "name": "Rotaboxes", "timestamp": 10, "tries": 122, "user_id": 456481297, "user_name": "Trifase"},
    ]

    _name = "Rotaboxes"
    _category = "Logica"
    _date = datetime.date(2024, 3, 5)
    _day = "497"
    _emoji = "🧩"
    _url = "https://rotaboxes.com"

    has_extra: False
    can_lose: False

    def __init__(self, update):
        self.update = update
        self.raw_text = self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

    @property
    def can_handle_this(self):
        lines = self.raw_text.splitlines()
        _can_handle_this = len(lines) >= 4 and "rotabox.es" in self.raw_text and "clicks:" in lines[1]
        return _can_handle_this

    @property
    def is_lost(self):
        return self.tries == "X"

    def parse(self):
        text = self.raw_text
        timestamp = int(datetime.datetime.timestamp(self.update.effective_message.date))
        self.user_name = self.update.message.from_user.full_name
        self.user_id = self.update.message.from_user.id
        self.timestamp = timestamp if timestamp else int(time.time())

        lines = text.splitlines()
        self.day = lines[3].split("/")[-1]
        punti = lines[1]
        punti = punti.split("clicks: ")[-1]
        # max_points = int(punti.split("/")[-1])
        clicks = int(punti.split("/")[0])
        self.tries = clicks


@dataclass
class Nerdle(Giochino):
    examples = [
        "nerdlegame 801 3/6\n\n⬛️⬛️🟪⬛️🟪🟪🟪⬛️\n🟪🟪⬛️🟪🟩⬛️🟩⬛️\n🟩🟩🟩🟩🟩🟩🟩🟩",
        "nerdlegame 791 5/6\n\n🟪⬛️🟪⬛️🟪🟩⬛️⬛️\n🟪🟪🟩⬛️🟪🟩⬛️🟪\n⬛️🟪🟩🟩🟪🟩🟪🟪\n🟩🟪🟩🟩⬛️🟩🟩🟩\n🟩🟩🟩🟩🟩🟩🟩🟩",
    ]
    expected = [
        {"day": "801", "name": "Nerdle", "timestamp": 10, "tries": "3", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "791", "name": "Nerdle", "timestamp": 10, "tries": "5", "user_id": 456481297, "user_name": "Trifase"},
    ]

    _name = "Nerdle"
    _category = "Logica"
    _date = datetime.date(2023, 9, 21)
    _day = "610"
    _emoji = "🤓"
    _url = "https://nerdlegame.com"

    has_extra: False
    can_lose: False

    def __init__(self, update):
        self.update = update
        self.raw_text = self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

    @property
    def can_handle_this(self):
        lines = self.raw_text.splitlines()
        _can_handle_this = "nerdlegame" in lines[0]
        return _can_handle_this

    @property
    def is_lost(self):
        return self.tries == "X"

    def parse(self):
        text = self.raw_text
        timestamp = int(datetime.datetime.timestamp(self.update.effective_message.date))
        self.user_name = self.update.message.from_user.full_name
        self.user_id = self.update.message.from_user.id
        self.timestamp = timestamp if timestamp else int(time.time())

        lines = text.splitlines()
        first_line = lines[0].split()
        self.day = first_line[1]
        self.tries = first_line[2].split("/")[0]
        self.stars = None


@dataclass
class Metazooa(Giochino):
    examples = [
        "🦮 Animal #156 🦎\nI figured it out in 1 guesses!\n🟩\n🔥 1 | Avg. Guesses: 9.7\n\nhttps://metazooa.com\n#metazooa",
        "🐞 Animal #249 🐼\nI figured it out in 6 guesses!\n🟨🟨🟨🟨🟩🟩\n🔥 1 | Avg. Guesses: 6\n\nhttps://metazooa.com\n#metazooa",
        "🐶 Animal #154 🪲\nI figured it out in 6 guesses!\n🟧🟩🟨🟥🟧🟩\n🔥 1 | Avg. Guesses: 8.5\n\nhttps://metazooa.com\n#metazooa",
        "🦆 Animal #127 🐈\nI was stumped by today's game!\n🟧🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩\n🔥 1 | Avg. Guesses: 9.1\n\nhttps://metazooa.com\n#metazooa",
    ]
    expected = [
        {"day": "156", "name": "Metazooa", "timestamp": 10, "tries": "1", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "249", "name": "Metazooa", "timestamp": 10, "tries": "6", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "154", "name": "Metazooa", "timestamp": 10, "tries": "6", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "127", "name": "Metazooa", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
    ]

    _name = "Metazooa"
    _category = "Scienza"
    _date = datetime.date(2023, 10, 7)
    _day = "68"
    _emoji = "🐢"
    _url = "https://metazooa.com/game"

    has_extra: False
    can_lose: True

    def __init__(self, update):
        self.update = update
        self.raw_text = self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

    @property
    def can_handle_this(self):
        lines = self.raw_text.splitlines()
        _can_handle_this = "Animal" in lines[0] and "#metazooa" in lines[-1]
        return _can_handle_this

    @property
    def is_lost(self):
        return self.tries == "X"

    def parse(self):
        text = self.raw_text
        timestamp = int(datetime.datetime.timestamp(self.update.effective_message.date))
        self.user_name = self.update.message.from_user.full_name
        self.user_id = self.update.message.from_user.id
        self.timestamp = timestamp if timestamp else int(time.time())

        lines = text.splitlines()
        self.day = lines[0].split()[2][1:]
        if "stumped" in lines[1]:
            self.tries = "X"
        else:
            self.tries = lines[1].split()[-2]
        self.stars = None


@dataclass
class Metaflora(Giochino):
    examples = [
        "🌱 Plant #141 🌾\nI figured it out in 3 guesses!\n🟨🟩🟩\n🔥 1 | Avg. Guesses: 6.7\n\nhttps://flora.metazooa.com\n#metaflora",
        "🍁 Plant #163 🌳\nI figured it out in 9 guesses!\n🟫🟧🟧🟧🟨🟨🟨🟨🟩\n🔥 1 | Avg. Guesses: 7.8\n\nhttps://flora.metazooa.com\n#metaflora",
        "🌳 Plant #191 🌵\nI was stumped by today's game!\n🟧🟧🟨🟧🟫🟧🟫🟨🟨🟧🟨🟫🟨🟨🟨🟨🟨🟨🟩🟩🟩🟩🟩🟩🟨\n🔥 0 | Avg. Guesses: 0\n\nhttps://flora.metazooa.com\n#metaflora",
    ]
    expected = [
        {"day": "141", "name": "Metaflora", "timestamp": 10, "tries": "3", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "163", "name": "Metaflora", "timestamp": 10, "tries": "9", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "191", "name": "Metaflora", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
    ]

    _name = "Metaflora"
    _category = "Scienza"
    _date = datetime.date(2023, 10, 28)
    _day = "28"
    _emoji = "🌿"
    _url = "https://flora.metazooa.com/game"

    has_extra: False
    can_lose: True

    def __init__(self, update):
        self.update = update
        self.raw_text = self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

    @property
    def can_handle_this(self):
        lines = self.raw_text.splitlines()
        _can_handle_this = "Plant" in lines[0] and "#metaflora" in lines[-1]
        return _can_handle_this

    @property
    def is_lost(self):
        return self.tries == "X"

    def parse(self):
        text = self.raw_text
        timestamp = int(datetime.datetime.timestamp(self.update.effective_message.date))
        self.user_name = self.update.message.from_user.full_name
        self.user_id = self.update.message.from_user.id
        self.timestamp = timestamp if timestamp else int(time.time())

        lines = text.splitlines()
        self.day = lines[0].split()[2][1:]
        if "stumped" in lines[1]:
            self.tries = "X"
        else:
            self.tries = lines[1].split()[-2]
        self.stars = None


@dataclass
class Angle(Giochino):
    examples = [
        "#Angle #657 4/4\n⬇️⬇️⬇️🎉\nhttps://www.angle.wtf",
        "#Angle #571 X/4\n⬆️⬆️⬆️⬆️: 2° off\nhttps://www.angle.wtf",
    ]
    expected = [
        {"day": "657", "name": "Angle", "timestamp": 10, "tries": "4", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "571", "name": "Angle", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
    ]

    _name = "Angle"
    _category = "Logica"
    _date = datetime.date(2023, 10, 28)
    _day = "494"
    _emoji = "📐"
    _url = "https://angle.wtf"

    has_extra: False
    can_lose: True

    def __init__(self, update):
        self.update = update
        self.raw_text = self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

    @property
    def can_handle_this(self):
        lines = self.raw_text.splitlines()
        _can_handle_this = "Angle" in lines[0]
        return _can_handle_this

    @property
    def is_lost(self):
        return self.tries == "X"

    def parse(self):
        text = self.raw_text
        timestamp = int(datetime.datetime.timestamp(self.update.effective_message.date))
        self.user_name = self.update.message.from_user.full_name
        self.user_id = self.update.message.from_user.id
        self.timestamp = timestamp if timestamp else int(time.time())

        lines = text.splitlines()
        points = lines[0].split()[-1].split("/")[0]
        self.day = lines[0].split()[1][1:]
        if points == "X":
            self.tries = "X"
        else:
            self.tries = points
        self.stars = None


@dataclass
class TempoIndovinr(Giochino):
    examples = [
        "TempoIndovinr day 146\nHo fatto 593/1000 punti a TempoIndovinr!\n\n🟩🟩🟩 (99%) 💀⬛️⬛️ (2%)\n🟧⬛️⬛️ (77%) 🟩🟩🟩 (99%)\n🟩🟩🟩 (97%) 💀⬛️⬛️ (17%)\n🟩🟩🟩 (99%) 💀⬛️⬛️ (3%)\n🟩🟩🟩 (100%) 💀⬛️⬛️ (0%)\n https://jacopofarina.eu/experiments/tempoindovinr/",
        "TempoIndovinr day 138\nHo fatto 727/1000 punti a TempoIndovinr!\n\n🟩🟩⬛️ (95%) 🟩🟩🟩 (100%)\n🟨⬛️⬛️ (84%) 🟨⬛️⬛️ (84%)\n🟩🟩🟩 (97%) 💀⬛️⬛️ (60%)\n🟩⬛️⬛️ (86%) 💀⬛️⬛️ (13%)\n🟩🟩⬛️ (95%) 💀⬛️⬛️ (13%)\n https://jacopofarina.eu/experiments/tempoindovinr/",
    ]
    expected = [
        {
            "day": "146",
            "name": "TempoIndovinr",
            "timestamp": 10,
            "tries": 407,
            "user_id": 456481297,
            "user_name": "Trifase",
        },
        {
            "day": "138",
            "name": "TempoIndovinr",
            "timestamp": 10,
            "tries": 273,
            "user_id": 456481297,
            "user_name": "Trifase",
        },
    ]

    _name = "TempoIndovinr"
    _category = "Immagini, giochi e film"
    _date = datetime.date(2023, 11, 17)
    _day = "5"
    _emoji = "🗺️"
    _url = "https://jacopofarina.eu/experiments/tempoindovinr"

    has_extra: False
    can_lose: False

    def __init__(self, update):
        self.update = update
        self.raw_text = self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

    @property
    def can_handle_this(self):
        lines = self.raw_text.splitlines()
        _can_handle_this = "experiments/tempoindovinr/" in lines[-1]
        return _can_handle_this

    @property
    def is_lost(self):
        return self.tries == "X"

    def parse(self):
        text = self.raw_text
        timestamp = int(datetime.datetime.timestamp(self.update.effective_message.date))
        self.user_name = self.update.message.from_user.full_name
        self.user_id = self.update.message.from_user.id
        self.timestamp = timestamp if timestamp else int(time.time())

        lines = text.splitlines()
        self.day = lines[0].split()[-1]
        self.tries = 1000 - int(lines[1].split()[2].split("/")[0])
        self.stars = None


@dataclass
class Chronophoto(Giochino):
    examples = [
        "I got a score of 2952 on today's Chronophoto: 1/4/2024\nRound 1: 290\nRound 2: 777\nRound 3: 396\nRound 4: 640\nRound 5: 849 https://www.chronophoto.app/daily.html",
        "I got a score of 3480 on today's Chronophoto: 6/4/2024\nRound 1: 924\nRound 2: 0❌\nRound 3: 924\nRound 4: 924\nRound 5: 708 https://www.chronophoto.app/daily.html",
    ]
    expected = [
        {
            "day": "126",
            "name": "Chronophoto",
            "timestamp": 10,
            "tries": 2048,
            "user_id": 456481297,
            "user_name": "Trifase",
        },
        {
            "day": "131",
            "name": "Chronophoto",
            "timestamp": 10,
            "tries": 1520,
            "user_id": 456481297,
            "user_name": "Trifase",
        },
    ]

    _name = "Chronophoto"
    _category = "Immagini, giochi e film"
    _date = datetime.date(2024, 3, 6)
    _day = "100"
    _emoji = "⏳"
    _url = "https://www.chronophoto.app/daily.html"

    has_extra: False
    can_lose: False

    def __init__(self, update):
        self.update = update
        self.raw_text = self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

    @property
    def can_handle_this(self):
        lines = self.raw_text.splitlines()
        _can_handle_this = "I got a score of" in lines[0] and "chronophoto.app" in lines[-1]
        return _can_handle_this

    @property
    def is_lost(self):
        return self.tries == "X"

    def parse(self):
        text = self.raw_text
        timestamp = int(datetime.datetime.timestamp(self.update.effective_message.date))
        self.user_name = self.update.message.from_user.full_name
        self.user_id = self.update.message.from_user.id
        self.timestamp = timestamp if timestamp else int(time.time())

        lines = text.splitlines()
        first_line = lines[0].split()
        self.day = get_day_from_date(self._date, self._day, "Chronophoto", first_line[-1])
        self.tries = 5_000 - int(first_line[5])
        if self.tries == 0:
            self.tries = "X"
        self.stars = None


@dataclass
class Travle(Giochino):
    examples = [
        "#travle #481 (5/10)\n✅✅✅✅✅\nhttps://travle.earth",
        "#travle #481 (8/10)\n✅✅✅✅🟧🟧🟧✅\nhttps://travle.earth",
        "#travle #468 (8/13) (3 suggerimenti)\n✅✅✅✅✅✅🟧✅\nhttps://travle.earth",
        "#travle #481 (?/10) (4 lontano)\n⬛️🟥🟥🟥✅🟧🟥⬛️⬛️⬛️\nhttps://travle.earth",
    ]
    expected = [
        {"day": "481", "name": "Travle", "timestamp": 10, "tries": 5, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "481", "name": "Travle", "timestamp": 10, "tries": 8, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "468", "name": "Travle", "timestamp": 10, "tries": 14, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "481", "name": "Travle", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
    ]

    _name = "Travle"
    _category = "Geografia e Mappe"
    _date = datetime.date(2023, 11, 30)
    _day = "351"
    _emoji = "🧭"
    _url = "https://travle.earth"

    has_extra: False
    can_lose: True

    def __init__(self, update):
        self.update = update
        self.raw_text = self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

    @property
    def can_handle_this(self):
        lines = self.raw_text.splitlines()
        _can_handle_this = "#travle " in lines[0] and "travle.earth" in lines[-1]
        return _can_handle_this

    @property
    def is_lost(self):
        return self.tries == "X"

    def parse(self):
        text = self.raw_text
        timestamp = int(datetime.datetime.timestamp(self.update.effective_message.date))
        self.user_name = self.update.message.from_user.full_name
        self.user_id = self.update.message.from_user.id
        self.timestamp = timestamp if timestamp else int(time.time())

        lines = text.splitlines()
        first_line = lines[0].split()
        self.day = first_line[1][1:]
        tries = first_line[2].split("/")[0][1:]
        if tries == "?":
            self.tries = "X"
        else:
            hints = 0
            if len(first_line) > 3:
                hints = first_line[3][1:]
            self.tries = int(int(tries) + ((int(hints) * (int(hints) + 1)) / 2))  # +1, +2, +3 (triangulars)
        self.stars = None


@dataclass
class TravleITA(Giochino):
    examples = [
        "#travle_ita #294 (4/9)\n✅✅✅✅\nhttps://travle.earth/ita",
        "#travle_ita #289 (13/14) (1 hint)\n✅🟧✅✅🟧✅🟧🟧🟧✅✅✅✅\nhttps://travle.earth/ita",
        "#travle_ita #215 (13/13) (3 Hinweise)\n🟧🟥✅✅🟧✅✅🟧🟥🟧✅✅✅\nhttps://travle.earth/ita",
        "#travle_ita #213 (8/9) (3 suggerimenti)\n🟧✅🟧🟧✅🟥✅✅\nhttps://travle.earth/ita",
        "#travle_ita #256 (?/9) (1 lontano)\n✅✅🟧🟧🟧✅🟧🟧🟧\nhttps://travle.earth/ita",
    ]
    expected = [
        {"day": "294", "name": "TravleITA", "timestamp": 10, "tries": 4, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "289", "name": "TravleITA", "timestamp": 10, "tries": 14, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "215", "name": "TravleITA", "timestamp": 10, "tries": 19, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "213", "name": "TravleITA", "timestamp": 10, "tries": 14, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "256", "name": "TravleITA", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
    ]

    _name = "TravleITA"
    _category = "Geografia e Mappe"
    _date = datetime.date(2024, 2, 29)
    _day = "256"
    _emoji = "👢"
    _url = "https://travle.earth/ita"

    has_extra: False
    can_lose: True

    def __init__(self, update):
        self.update = update
        self.raw_text = self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

    @property
    def can_handle_this(self):
        lines = self.raw_text.splitlines()
        _can_handle_this = "#travle_ita" in lines[0] and "/ita" in lines[-1]
        return _can_handle_this

    @property
    def is_lost(self):
        return self.tries == "X"

    def parse(self):
        text = self.raw_text
        timestamp = int(datetime.datetime.timestamp(self.update.effective_message.date))
        self.user_name = self.update.message.from_user.full_name
        self.user_id = self.update.message.from_user.id
        self.timestamp = timestamp if timestamp else int(time.time())

        lines = text.splitlines()
        first_line = lines[0].split()
        self.day = first_line[1][1:]
        tries = first_line[2].split("/")[0][1:]
        if tries == "?":
            self.tries = "X"
        else:
            hints = 0
            if len(first_line) > 3:
                hints = first_line[3][1:]
            self.tries = int(int(tries) + ((int(hints) * (int(hints) + 1)) / 2))  # +1, +2, +3 (triangulars)


@dataclass
class NerdleCross(Giochino):
    examples = [
        "cross nerdle #198\n⬛⬜⬜⬜🟩⬜⬜⬛⬛\n⬛⬛⬜⬛⬜⬛⬛⬛⬜\n🟩⬛⬜⬛🟩⬜⬜⬜🟩\n⬜⬛🟩⬛⬜⬛⬛⬛🟩\n⬜🟩🟩⬜⬜⬜🟩⬜⬜\n⬜⬛⬛⬛⬜⬛⬜⬛🟩\n🟩⬜⬜🟩⬜⬛⬜⬛⬜\n⬜⬛⬛⬛⬜⬛🟩⬛⬛\n⬛⬛⬜⬜⬜⬜🟩⬜⬛\nPerfect solve - no 🎁 or 👀.\n@nerdlegame points: 6/6",
        "cross nerdle #201\n⬛⬜🟩🟩🟩⬜🟩⬜⬛\n🟩⬛⬜⬛🟩⬛🟩⬛⬜\n🟩🟩🟩⬛🟩⬜🟩🟩🟩\n⬜⬛🟩⬛⬜⬛⬛⬛🟩\n⬜⬜🟩🟩⬜🟩🟩⬜🟩\n🟩⬛⬛⬛🟩⬛🟩⬛🟩\n🟩⬜🟩🟩🟩⬛🟩🟩⬜\n⬜⬛🟩⬛🟩⬛🟩⬛⬜\n⬛⬜🟩⬜⬜🟩🟩⬜⬛\n🟩*37 + 🎁*0 + 👀* 2\n@nerdlegame points:4/6",
        "cross nerdle #198\n⬛️⬜️⬜️⬜️🎁⬜️⬜️⬛️⬛️\n⬛️⬛️⬜️⬛️⬜️⬛️⬛️⬛️⬜️\n🎁⬛️⬜️⬛️🎁⬜️⬜️⬜️🎁\n⬜️⬛️🎁⬛️⬜️⬛️⬛️⬛️🎁\n⬜️🎁🎁⬜️⬜️⬜️🎁⬜️⬜️\n⬜️⬛️⬛️⬛️⬜️⬛️⬜️⬛️🎁\n🎁⬜️⬜️🎁⬜️⬛️⬜️⬛️⬜️\n⬜️⬛️⬛️⬛️⬜️⬛️🎁⬛️⬛️\n⬛️⬛️⬜️⬜️⬜️⬜️🎁⬜️⬛️\n🟩*0 + 🎁*14 + 👀* 1\n@nerdlegame points:0/6",
    ]
    expected = [
        {"day": "198", "name": "NerdleCross", "timestamp": 10, "tries": 0, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "201", "name": "NerdleCross", "timestamp": 10, "tries": 2, "user_id": 456481297, "user_name": "Trifase"},
        {
            "day": "198",
            "name": "NerdleCross",
            "timestamp": 10,
            "tries": "X",
            "user_id": 456481297,
            "user_name": "Trifase",
        },
    ]

    _name = "NerdleCross"
    _category = "Logica"
    _date = datetime.date(2023, 12, 12)
    _day = "198"
    _emoji = "🧮"
    _url = "https://nerdlegame.com/crossnerdle"

    has_extra: False
    can_lose: True

    def __init__(self, update):
        self.update = update
        self.raw_text = self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

    @property
    def can_handle_this(self):
        lines = self.raw_text.splitlines()
        _can_handle_this = "cross nerdle #" in lines[0] and "@nerdlegame" in lines[-1]
        return _can_handle_this

    @property
    def is_lost(self):
        return self.tries == "X"

    def parse(self):
        text = self.raw_text
        timestamp = int(datetime.datetime.timestamp(self.update.effective_message.date))
        self.user_name = self.update.message.from_user.full_name
        self.user_id = self.update.message.from_user.id
        self.timestamp = timestamp if timestamp else int(time.time())

        lines = text.splitlines()
        first_line = lines[0].split()
        self.day = first_line[-1][1:]
        points = lines[-1].split(":")[-1].split("/")[0].strip()
        # Nerdle Cross uses positive poits, from 0 to 6. We as usual save 6-n and then revert it when printing the results.
        self.tries = 6 - int(points)
        if self.tries == 6:
            self.tries = "X"
        self.stars = None


@dataclass
class DominoFit(Giochino):
    examples = [
        "DOMINO FIT #42 6x6 \n🏅🧙\u200d♂️🧙\u200d♂️✅\n⌚️0️⃣4️⃣5️⃣",
        "DOMINO FIT #47 6x6 \n🏅🧙\u200d♂️🧙\u200d♂️🧙\u200d♂️\n⌚0️⃣2️⃣3️⃣",
    ]
    expected = [
        {"day": "42", "name": "DominoFit", "timestamp": 10, "tries": 45, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "47", "name": "DominoFit", "timestamp": 10, "tries": 23, "user_id": 456481297, "user_name": "Trifase"},
    ]

    _name = "DominoFit"
    _category = "Logica"
    _date = datetime.date(2024, 2, 18)
    _day = "1"
    _emoji = "🃏"
    _url = "https://dominofit.isotropic.us"

    has_extra: False
    can_lose: False

    def __init__(self, update):
        self.update = update
        self.raw_text = self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

    @property
    def can_handle_this(self):
        lines = self.raw_text.splitlines()
        _can_handle_this = "DOMINO FIT #" in lines[0]
        return _can_handle_this

    @property
    def is_lost(self):
        return self.tries == "X"

    def parse(self):
        text = self.raw_text
        timestamp = int(datetime.datetime.timestamp(self.update.effective_message.date))
        self.user_name = self.update.message.from_user.full_name
        self.user_id = self.update.message.from_user.id
        self.timestamp = timestamp if timestamp else int(time.time())

        lines = text.splitlines()
        first_line = lines[0].split()
        self.day = first_line[-2][1:]
        points = lines[-1]
        str_points = time_from_emoji(points.strip())
        self.tries = int(str_points.strip())
        self.stars = None


@dataclass
class FoodGuessr(Giochino):
    _name = "FoodGuessr"
    _category = "Geografia e Mappe"
    _date = datetime.date(2024, 3, 9)
    _day = "200"
    _emoji = "🍝"
    _url = "https://foodguessr.com"

    examples = [
        "FoodGuessr\n  Round 1 🌑🌑🌑🌑\n  Round 2 🌖🌑🌑🌑\n  Round 3 🌑🌑🌑🌑\nTotal score: 645 / 15.000\nPlay: https://foodguessr.com",
        "FoodGuessr\n  Round 1 🌘🌑🌑🌑\n  Round 2 🌕🌕🌕🌘\n  Round 3 🌖🌑🌑🌑\nTotal score: 5.242 / 15.000\nPlay: https://foodguessr.com",
        "FoodGuessr\n  Round 1 🌕🌕🌕🌕\n  Round 2 🌕🌕🌕🌕\n  Round 3 🌕🌕🌕🌑\nTotal score: 13.500 / 15.000\nPlay: https://foodguessr.com",
    ]
    # FoodGuessr doesn't have any day/date, so we assume it's today.
    day = get_day_from_date(_date, _day, "FoodGuessr", datetime.date.today())
    expected = [
        {"day": day, "name": "FoodGuessr", "timestamp": 10, "tries": 14355, "user_id": 456481297, "user_name": "Trifase"},
        {"day": day, "name": "FoodGuessr", "timestamp": 10, "tries": 9758, "user_id": 456481297, "user_name": "Trifase"},
        {"day": day, "name": "FoodGuessr", "timestamp": 10, "tries": 1500, "user_id": 456481297, "user_name": "Trifase"},
    ]

    has_extra: False
    can_lose: False

    def __init__(self, update):
        self.update = update
        self.raw_text = self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

    @property
    def can_handle_this(self):
        lines = self.raw_text.splitlines()
        _can_handle_this = "FoodGuessr" in lines[0] and "Play: https://foodguessr.com" in lines[-1]
        return _can_handle_this

    @property
    def is_lost(self):
        return self.tries == "X"

    def parse(self):
        text = self.raw_text
        timestamp = int(datetime.datetime.timestamp(self.update.effective_message.date))
        self.user_name = self.update.message.from_user.full_name
        self.user_id = self.update.message.from_user.id
        self.timestamp = timestamp if timestamp else int(time.time())

        lines = text.splitlines()
        self.day = get_day_from_date(self._date, self._day, "FoodGuessr", datetime.date.today())
        points = lines[4].split()[2].replace(",", "").replace(".", "")
        self.tries = 15_000 - int(points)
        self.stars = None


@dataclass
class Spellcheck(Giochino):
    examples = [
        "Spellcheck #75\n🟩🟩🟩🟩🟩\n🟩🟩🟩🟩🟩\n🟩🟩🟩🟩🟩",
        "Spellcheck #74\n🟩🟥🟩🟥🟩\n🟩🟩🟩🟩🟩\n🟩🟥🟥🟥🟥",
        "Spellcheck #87\n🟥🟥🟥🟥🟥\n🟥🟥🟥🟥🟥\n🟥🟥🟥🟥🟥\n\nhttps://spellcheckgame.com/",
    ]
    expected = [
        {"day": "75", "name": "Spellcheck", "timestamp": 10, "tries": 0, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "74", "name": "Spellcheck", "timestamp": 10, "tries": 6, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "87", "name": "Spellcheck", "timestamp": 10, "tries": 15, "user_id": 456481297, "user_name": "Trifase"},
    ]
    _name = "Spellcheck"
    _category = "Logica"
    _date = datetime.date(2024, 3, 9)
    _day = "57"
    _emoji = "👂"
    _url = "https://spellcheck.xyz"

    has_extra: False
    can_lose: False

    def __init__(self, update):
        self.update = update
        self.raw_text = self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

    @property
    def can_handle_this(self):
        lines = self.raw_text.splitlines()
        _can_handle_this = "Spellcheck #" in lines[0]
        return _can_handle_this

    @property
    def is_lost(self):
        return self.tries == "X"

    def parse(self):
        text = self.raw_text
        timestamp = int(datetime.datetime.timestamp(self.update.effective_message.date))
        self.user_name = self.update.message.from_user.full_name
        self.user_id = self.update.message.from_user.id
        self.timestamp = timestamp if timestamp else int(time.time())

        lines = text.splitlines()
        first_line = lines[0].split()
        self.day = first_line[1][1:]
        self.tries = 15 - text.count("🟩")
        self.stars = None


@dataclass
class Spotle(Giochino):
    examples = [
        "Spotle #710🎧\n\n⬜⬜⬜🟩\n\nspotle.io",
        "Spotle #710🎧\n\n⬜⬜⬜⬜⬜⬜⬜⬜⬜❌\n\nspotle.io",
    ]
    expected = [
        {"day": "710", "name": "Spotle", "timestamp": 10, "tries": "4", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "710", "name": "Spotle", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
    ]
    _name = "Spotle"
    _category = "Immagini, giochi e film"
    _date = datetime.date(2024, 3, 22)
    _day = "695"
    _emoji = "🎧"
    _url = "https://spotle.io/"

    has_extra: False
    can_lose: True

    def __init__(self, update):
        self.update = update
        self.raw_text = self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

    @property
    def can_handle_this(self):
        lines = self.raw_text.splitlines()
        _can_handle_this = "Spotle #" in lines[0] and "spotle.io" in lines[-1]
        return _can_handle_this

    @property
    def is_lost(self):
        return self.tries == "X"

    def parse(self):
        text = self.raw_text
        timestamp = int(datetime.datetime.timestamp(self.update.effective_message.date))
        self.user_name = self.update.message.from_user.full_name
        self.user_id = self.update.message.from_user.id
        self.timestamp = timestamp if timestamp else int(time.time())

        lines = text.splitlines()
        first_line = lines[0].split()
        self.day = first_line[1][1:-1]
        punteggio = lines[2].replace(" ", "")
        punteggio_bonificato = ""
        for char in punteggio:
            if char in ["⬛", "🟥", "🟩", "⬜"]:
                punteggio_bonificato += char
        if "🟩" not in punteggio or "❌" in punteggio:
            self.tries = "X"
        else:
            self.tries = str(punteggio_bonificato.index("🟩") + 1)


def get_giochini():
    return [
        cls_obj
        for _, cls_obj in inspect.getmembers(sys.modules[__name__], inspect.isclass)
        if cls_obj.__module__ == sys.modules[__name__].__name__ and cls_obj.__base__ == Giochino
    ]


def get_games() -> dict:
    games = {}
    giochini = get_giochini()
    for giochino in giochini:
        games[giochino._name] = {
            "game": giochino._name,
            "emoji": giochino._emoji,
            "category": giochino._category,
            "url": giochino._url,
            "date": giochino._date,
            "day": giochino._day,
        }
    return games


# This make a dictionary with every game info (grabbed from the list of classes) and it's imported almost everywhere
ALL_GAMES = get_games()
# This is a list of every class of game, used to instantiate them
ALL_CLASSES = get_giochini()

# tests = []
# for klass in ALL_CLASSES:
#     tests.extend(klass.examples)

# for test in tests:
#     upd = generate_sample_update(test)
#     for giochino in ALL_CLASSES:
#         giochino = giochino(upd)

#         if giochino.can_handle_this:
#             result = giochino.punteggio
#             print(f"{giochino._name} - {giochino.can_handle_this} - {any(x.items() <= result.items() for x in giochino.expected)}")
#             for x in giochino.expected:
#                 print(x)
#             print(f'result = {giochino.punteggio}')
#             break
