import datetime
import inspect
import sys
import time
import locale

from dataclassy import dataclass
from telegram import Bot, Update
from telegram.ext.filters import MessageFilter


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
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
        date = datetime.datetime.strptime(date, "🌎 %b %d, %Y 🌍").date()
        locale.setlocale(locale.LC_TIME, "it_IT.UTF-8")

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
        block = block.strip()
        if is_connection_block_completed(block):
            completed_blocks += 1
    if completed_blocks == 4:
        return True
    return False


class GameFilter(MessageFilter):
    def __init__(self):
        self.data_filter = True

    def filter(self, message):
        if not message.text:
            return False

        # Iterate all games to find the FIRST that can handle the update.
        # Order matters. Maybe it's worth to order them in order of frequency of use?
        # Only the first game matched will be used to parse.
        # Returning a dictionary and setting data_filter = true means that PTB will build
        # a context.property (context.giochino) with the selected class. We just grab it on the other end.
        for giochino in ALL_CLASSES:
            if giochino.can_handle_this(message.text):
                return {"giochino": [giochino]}
        return False


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
    expected: list[dict] = None
    # Misc information about the game/class
    has_extra: bool = False  # if the game has additional points, currently set but unused
    can_lose: bool = True  # if the game can be lost (e.g has a copypaste string for lost plays), set but unused
    lost_message: str = "Hai perso :("  # per-game lose message
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
        self.raw_text = self.update.message.text

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


@dataclass
class UnsupportedGame(Giochino):
    message = "ignora"
    hidden_game = True

    @staticmethod
    def can_handle_this(raw_text):
        _can_handle_this = any(
            [
                "https://cuedle.fun" in raw_text,  # Cuedle
                "🔊" in raw_text and "#Heardle" in raw_text,  # Headle
                "I solved" in raw_text and "New York Times Mini Crossword" in raw_text,  # NY Mini Crossword
                "Strands #" in raw_text and "🔵" in raw_text,  # Strands
            ]
        )
        return _can_handle_this

    @property
    def punteggio(self):
        return None


@dataclass
class UnknownGame(Giochino):
    message = "sconosciuto"
    hidden_game = True

    @staticmethod
    def can_handle_this(raw_text):
        quadratini = ["🟥", "🟩", "⬜️", "🟨", "⬛️", "🟦", "🟢", "⚫️", "🟡", "🟠", "🔵", "🟣", "✅", "🌕", "🌗", "🌘", "🌑"]
        _can_handle_this = any(c in raw_text for c in quadratini)
        return _can_handle_this

    @property
    def punteggio(self):
        return None


@dataclass
class Angle(Giochino):
    _name = "Angle"
    _category = "Logica"
    _date = datetime.date(2023, 10, 28)
    _day = "494"
    _emoji = "📐"
    _url = "https://angle.wtf"

    examples = [
        "#Angle #657 4/4\n⬇️⬇️⬇️🎉\nhttps://www.angle.wtf",
        "#Angle #571 X/4\n⬆️⬆️⬆️⬆️: 2° off\nhttps://www.angle.wtf",
    ]
    expected = [
        {"day": "657", "name": "Angle", "timestamp": 10, "tries": "4", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "571", "name": "Angle", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        lines = raw_text.splitlines()
        _can_handle_this = "Angle" in lines[0]
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        lines = text.splitlines()
        points = lines[0].split()[-1].split("/")[0]
        self.day = lines[0].split()[1][1:]
        if points == "X":
            self.tries = "X"
        else:
            self.tries = points
        self.stars = None


@dataclass
class Apparle(Giochino):
    _name = "Apparle"
    _category = "Immagini, giochi e film"
    _date = datetime.date(2024, 4, 14)
    _day = "45"
    _emoji = "💵"
    _url = "https://www.apparle.com"

    examples = [
        "Apparle #28 1/6\n🏆 -1.2%\n\nhttps://apparle.com",
        "Apparle #28 3/6\n⬇️ +50%\n⬆️ -13.7%\n💵 -1.2%\n\nhttps://apparle.com",
        "Apparle #45 6/6\n⬆️ -32.2%\n⬆️ -66.1%\n⬆️ -83.1%\n⬆️ -66.1%\n⬆️ -57.6%\n💵 0%\n\nhttps://apparle.com",
        "Apparle #45 6/6\n⬆️ -84.7%\n⬆️ -16.1%\n⬇️ +102.5%\n⬇️ +68.6%\n⬇️ +145.8%\n❌ +154.2%\n\nhttps://apparle.com",
    ]
    expected = [
        {"day": "28", "name": "Apparle", "stars": None, "timestamp": 10, "tries": "1", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "28", "name": "Apparle", "stars": None, "timestamp": 10, "tries": "3", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "45", "name": "Apparle", "stars": None, "timestamp": 10, "tries": "6", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "45", "name": "Apparle", "stars": None, "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        lines = raw_text.splitlines()
        _can_handle_this = "Apparle #" in lines[0] and "https://apparle.com" in lines[-1]
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        lines = text.splitlines()
        points = lines[0].split()[-1].split("/")[0]
        self.day = lines[0].split()[1][1:]
        self.tries = points
        if "❌" in text:
            self.tries = "X"
        self.stars = None


@dataclass
class Bandle(Giochino):
    _name = "Bandle"
    _category = "Immagini, giochi e film"
    _date = datetime.date(2024, 3, 3)
    _day = "564"
    _emoji = "🎸"
    _url = "https://bandle.app/"

    examples = [
        "Bandle #597 4/6\n⬛️⬛️⬛️🟩⬜️⬜️\nFound: 10/14 (71.4%)\nCurrent Streak: 1 (max 2)\n#Bandle #Heardle #Wordle \n https://bandle.app/"
        "Bandle #579 x/6\n⬛️⬛️⬛️⬛️⬛️⬛️\nFound: 3/5 (60%)\n#Bandle #Heardle #Wordle \n https://bandle.app/"
    ]
    expected = [
        {"day": "597", "name": "Bandle", "timestamp": 10, "tries": "4", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "579", "name": "Bandle", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        lines = raw_text.splitlines()
        _can_handle_this = "Bandle #" in lines[0] and "https://bandle.app/" in lines[-1]
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        lines = text.splitlines()
        first_line = lines[0].split()
        self.day = first_line[1][1:]
        punti = first_line[2].split("/")[0]
        if punti != "x":
            self.tries = punti
        else:
            self.tries = "X"


@dataclass
class Chrono(Giochino):
    _name = "Chrono"
    _category = "Logica"
    _date = datetime.date(2024, 3, 4)
    _day = "734"
    _emoji = "⏱️"
    _url = "https://chrono.quest"

    has_extra: True

    examples = [
        "🥇 CHRONO  #749\n\n🟢🟢🟢🟢🟢🟢\n\n⏱: 50.8\n🔥: 3\nhttps://chrono.quest",
        "🥈 CHRONO  #760\n\n🟢🟢🟢🟢⚪️⚪️\n🟢🟢🟢🟢🟢🟢\n\n⏱: 33.3\n🔥: 1\nhttps://chrono.quest",
        "🥉 CHRONO  #748\n\n🟢🟢⚪️⚪️⚪️🟢\n🟢🟢⚪️⚪️🟢🟢\n🟢🟢🟢🟢🟢🟢\n\n⏱: 55.8\n🔥: 2\nhttps://chrono.quest",
        "😬 CHRONO  #748\n\n🟢⚪️🟢⚪️⚪️🟢\n🟢⚪️⚪️⚪️🟢🟢\n🟢⚪️⚪️⚪️🟢🟢\n\n⏱: 81.8\n🔥: 0\nhttps://chrono.quest",
    ]
    expected = [
        {"day": "749", "name": "Chrono", "stars": 9949.2, "timestamp": 10, "tries": 1, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "760", "name": "Chrono", "stars": 9966.7, "timestamp": 10, "tries": 2, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "748", "name": "Chrono", "stars": 9944.2, "timestamp": 10, "tries": 3, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "748", "name": "Chrono", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        lines = raw_text.splitlines()
        _can_handle_this = "CHRONO  #" in lines[0] and "https://chrono.ques" in lines[-1]
        return _can_handle_this

    def parse(self):
        text = self.raw_text

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
class Chronophoto(Giochino):
    _name = "Chronophoto"
    _category = "Immagini, giochi e film"
    _date = datetime.date(2024, 3, 6)
    _day = "100"
    _emoji = "⏳"
    _url = "https://www.chronophoto.app/daily.html"

    can_lose: False

    examples = [
        "I got a score of 2952 on today's Chronophoto: 1/4/2024\nRound 1: 290\nRound 2: 777\nRound 3: 396\nRound 4: 640\nRound 5: 849 https://www.chronophoto.app/daily.html",
        "I got a score of 3480 on today's Chronophoto: 6/4/2024\nRound 1: 924\nRound 2: 0❌\nRound 3: 924\nRound 4: 924\nRound 5: 708 https://www.chronophoto.app/daily.html",
    ]
    expected = [
        {"day": "126", "name": "Chronophoto", "timestamp": 10, "tries": 2048, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "131", "name": "Chronophoto", "timestamp": 10, "tries": 1520, "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        lines = raw_text.splitlines()
        _can_handle_this = "I got a score of" in lines[0] and "chronophoto.app" in lines[-1]
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        lines = text.splitlines()
        first_line = lines[0].split()
        self.day = get_day_from_date(self._date, self._day, "Chronophoto", first_line[-1])
        self.tries = 5_000 - int(first_line[5])
        if self.tries == 0:
            self.tries = "X"
        self.stars = None


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

    @staticmethod
    def can_handle_this(raw_text):
        lines = raw_text.splitlines()
        _can_handle_this = "Cloudle -" in lines[0]
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        lines = text.splitlines()
        first_line = lines[0].split()
        self.day = get_day_from_date(self._date, self._day, "Cloudle", datetime.date.today())
        self.tries = first_line[-1].split("/")[0]
        self.stars = None


@dataclass
class Colorfle(Giochino):
    _name = "Colorfle"
    _category = "Immagini, giochi e film"
    _date = datetime.date(2024, 3, 5)
    _day = "679"
    _emoji = "🎨"
    _url = "https://colorfle.com"

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

    @staticmethod
    def can_handle_this(raw_text):
        lines = raw_text.splitlines()
        _can_handle_this = "Colorfle" in lines[0] and "accuracy" in lines[-1]
        return _can_handle_this

    def parse(self):
        text = self.raw_text

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
class Connections(Giochino):
    _name = "Connections"
    _category = "Giochi di parole"
    _date = datetime.date(2023, 9, 18)
    _day = "99"
    _emoji = "🔀"
    _url = "https://www.nytimes.com/games/connections"

    lost_message = "Hai perso, ma sii forte. 💪🏼"

    examples = [
        "Connections \nPuzzle #299\n🟩🟩🟩🟩\n🟨🟨🟨🟨\n🟦🟦🟦🟦\n🟪🟪🟪🟪",
        "Connections \nPuzzle #300\n🟩🟪🟩🟩\n🟩🟪🟩🟩\n🟩🟪🟩🟩\n🟩🟩🟩🟩\n🟦🟦🟦🟦\n🟪🟪🟪🟪\n🟨🟨🟨🟨",
        "Connections \nPuzzle #302\n🟨🟨🟨🟨\n🟪🟩🟪🟪\n🟪🟪🟪🟦\n🟪🟦🟪🟪\n🟪🟪🟩🟪",
        'Connections\nPuzzle #324 \n🟨🟨🟨🟨 \n🟦🟦🟩🟦 \n🟦🟦🟪🟦 \n🟦🟦🟦🟦 \n🟩🟩🟩🟪 \n🟩🟩🟩🟩 \n🟪🟪🟪🟪',
    ]
    expected = [
        {"day": "299", "name": "Connections", "timestamp": 10, "tries": 1, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "300", "name": "Connections", "timestamp": 10, "tries": 4, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "302", "name": "Connections", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
        {'day': '324', 'name': 'Connections', 'timestamp': 10, 'tries': 4, 'user_id': 456481297, 'user_name': 'Trifase'},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        lines = raw_text.splitlines()
        _can_handle_this = "Connections" in lines[0]
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        lines = text.splitlines()
        self.day = lines[1].split()[-1][1:]
        points = lines[2:]
        if is_connection_completed(points):
            self.tries = len(points) - 3
        else:
            self.tries = "X"


@dataclass
class Contexto(Giochino):
    _name = "Contexto"
    _category = "Giochi di parole"
    _date = datetime.date(2023, 6, 23)
    _day = "278"
    _emoji = "🔄"
    _url = "https://contexto.me"

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

    @staticmethod
    def can_handle_this(raw_text):
        lines = raw_text.splitlines()
        _can_handle_this = "contexto.me" in lines[0]
        return _can_handle_this

    def parse(self):
        text = self.raw_text

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
class DominoFit(Giochino):
    _name = "DominoFit"
    _category = "Logica"
    _date = datetime.date(2024, 2, 18)
    _day = "1"
    _emoji = "🃏"
    _url = "https://dominofit.isotropic.us"

    can_lose: False

    examples = [
        "DOMINO FIT #42 6x6 \n🏅🧙\u200d♂️🧙\u200d♂️✅\n⌚️0️⃣4️⃣5️⃣",
        "DOMINO FIT #47 6x6 \n🏅🧙\u200d♂️🧙\u200d♂️🧙\u200d♂️\n⌚0️⃣2️⃣3️⃣",
    ]
    expected = [
        {"day": "42", "name": "DominoFit", "timestamp": 10, "tries": 45, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "47", "name": "DominoFit", "timestamp": 10, "tries": 23, "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        lines = raw_text.splitlines()
        _can_handle_this = "DOMINO FIT #" in lines[0]
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        lines = text.splitlines()
        first_line = lines[0].split()
        self.day = first_line[-2][1:]
        points = lines[-1]
        str_points = time_from_emoji(points.strip())
        self.tries = int(str_points.strip())
        self.stars = None


@dataclass
class Flagle(Giochino):
    _name = "Flagle"
    _category = "Geografia e Mappe"
    _date = datetime.date(2023, 9, 8)
    _day = "564"
    _emoji = "🏁"
    _url = "https://www.flagle.io"

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

    @staticmethod
    def can_handle_this(raw_text):
        lines = raw_text.splitlines()
        _can_handle_this = "#Flagle" in lines[0]
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        lines = text.splitlines()
        first_line = lines[0].split()
        self.day = first_line[1][1:]
        self.tries = first_line[3].split("/")[0]
        self.stars = None


@dataclass
class FoodGuessr(Giochino):
    _name = "FoodGuessr"
    _category = "Geografia e Mappe"
    _date = datetime.date(2024, 3, 9)
    _day = "200"
    _emoji = "🍝"
    _url = "https://foodguessr.com"

    can_lose: False

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

    @staticmethod
    def can_handle_this(raw_text):
        lines = raw_text.splitlines()
        _can_handle_this = "FoodGuessr" in lines[0] and "Play: https://foodguessr.com" in lines[-1]
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        lines = text.splitlines()
        self.day = get_day_from_date(self._date, self._day, "FoodGuessr", datetime.date.today())
        points = lines[4].split()[2].replace(",", "").replace(".", "")
        self.tries = 15_000 - int(points)
        self.stars = None


@dataclass
class Framed(Giochino):
    _name = "Framed"
    _category = "Immagini, giochi e film"
    _date = datetime.date(2023, 6, 23)
    _day = "469"
    _emoji = "🎞"
    _url = "https://framed.wtf"

    examples = [
        "Framed #756\n🎥 🟥 🟥 🟥 🟥 🟥 🟥\n\nhttps://framed.wtf",
        "Framed #758\n🎥 🟥 🟥 🟥 🟩 ⬛ ⬛\n\nhttps://framed.wtf",
    ]
    expected = [
        {"day": "756", "name": "Framed", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "758", "name": "Framed", "timestamp": 10, "tries": "4", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        lines = raw_text.splitlines()
        _can_handle_this = "Framed" in lines[0]
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        lines = text.splitlines()
        first_line = lines[0].split()
        self.day = first_line[1][1:]
        punteggio = lines[1].replace(" ", "")
        if "🟩" not in punteggio:
            self.tries = "X"
        else:
            self.tries = str(punteggio.index("🟩"))


@dataclass
class Globle(Giochino):
    _name = "Globle"
    _category = "Geografia e Mappe"
    _date = datetime.date(2023, 6, 23)
    _day = "200"
    _emoji = "🌍"
    _url = "https://globle-game.com"

    can_lose: False

    examples = [
        "🌎 Mar 30, 2024 🌍\n🔥 1 | Avg. Guesses: 8.94\n🟧🟨🟧🟩 = 4\n\nhttps://globle-game.com\n#globle",
        "🌎 Mar 5, 2024 🌍\n🔥 1 | Avg. Guesses: 6.88\n🟨🟨🟧🟧🟥🟧🟧🟥\n🟥🟥🟧🟨🟥🟥🟩 = 15\n\nhttps://globle-game.com\n#globle",
    ]
    expected = [
        {"day": "481", "name": "Globle", "timestamp": 10, "tries": "4", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "456", "name": "Globle", "timestamp": 10, "tries": "15", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        lines = raw_text.splitlines()
        _can_handle_this = "#globle" in lines[-1]
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        lines = text.splitlines()
        self.day = get_day_from_date(self._date, self._day, "Globle", lines[0])
        for line in lines:
            if "=" in line:
                self.tries = line.split("=")[-1][1:]
        self.stars = None


@dataclass
class GuessTheGame(Giochino):
    _name = "GuessTheGame"
    _category = "Immagini, giochi e film"
    _date = datetime.date(2023, 6, 23)
    _day = "405"
    _emoji = "🎮"
    _url = "https://guessthe.game"

    examples = [
        "#GuessTheGame #693\n\n🎮 🟥 🟥 🟥 🟥 🟥 🟥\n\n#ScreenshotSleuth\nhttps://GuessThe.Game/p/693",
        "#GuessTheGame #695\n\n🎮 🟥 🟥 🟨 🟥 🟥 🟥\n\n#ProGamer\nhttps://GuessThe.Game/p/695",
        "#GuessTheGame #692\n\n🎮 🟩 ⬜ ⬜ ⬜ ⬜ ⬜\n\n#ProGamer\nhttps://GuessThe.Game/p/692",
        "#GuessTheGame #684\n\n🎮 🟥 🟥 🟥 🟨 🟩 ⬜\n\n#ProGamer\nhttps://GuessThe.Game/p/684",
    ]
    expected = [
        {"day": "693", "name": "GuessTheGame", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "695", "name": "GuessTheGame", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "692", "name": "GuessTheGame", "timestamp": 10, "tries": "1", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "684", "name": "GuessTheGame", "timestamp": 10, "tries": "5", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        lines = raw_text.splitlines()
        _can_handle_this = "#GuessTheGame" in lines[0]
        return _can_handle_this

    def parse(self):
        text = self.raw_text

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
class HighFive(Giochino):
    _name = "HighFive"
    _category = "Giochi di parole"
    _date = datetime.date(2023, 6, 23)
    _day = "100"
    _emoji = "🖐️"
    _url = "https://highfivegame.app"

    examples = ["🖐 I scored 27 points on today's HighFive! Can you beat me?\n\n🟠🟠\n🟢🟢🟢🟢\n🔵\n🟣🟣🟣🟣🟣\n\nhttps://highfivegame.app/2024-02-28"]
    expected = [{"day": "350", "name": "HighFive", "timestamp": 10, "tries": "-27", "user_id": 456481297, "user_name": "Trifase"}]

    can_lose: False

    @staticmethod
    def can_handle_this(raw_text):
        lines = raw_text.splitlines()
        _can_handle_this = "https://highfivegame.app/2" in lines[-1]
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        lines = text.splitlines()
        self.day = get_day_from_date(self._date, self._day, "HighFive", lines[-1])
        self.tries = str(0 - int(lines[0].split()[3]))
        self.stars = None


@dataclass
class Metaflora(Giochino):
    _name = "Metaflora"
    _category = "Scienza"
    _date = datetime.date(2023, 10, 28)
    _day = "28"
    _emoji = "🌿"
    _url = "https://flora.metazooa.com/game"

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

    @staticmethod
    def can_handle_this(raw_text):
        lines = raw_text.splitlines()
        _can_handle_this = "Plant" in lines[0] and "#metaflora" in lines[-1]
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        lines = text.splitlines()
        self.day = lines[0].split()[2][1:]
        if "stumped" in lines[1]:
            self.tries = "X"
        else:
            self.tries = lines[1].split()[-2]
        self.stars = None


@dataclass
class Metazooa(Giochino):
    _name = "Metazooa"
    _category = "Scienza"
    _date = datetime.date(2023, 10, 7)
    _day = "68"
    _emoji = "🐢"
    _url = "https://metazooa.com/game"

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

    @staticmethod
    def can_handle_this(raw_text):
        lines = raw_text.splitlines()
        _can_handle_this = "Animal" in lines[0] and "#metazooa" in lines[-1]
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        lines = text.splitlines()
        self.day = lines[0].split()[2][1:]
        if "stumped" in lines[1]:
            self.tries = "X"
        else:
            self.tries = lines[1].split()[-2]
        self.stars = None


@dataclass
class Moviedle(Giochino):
    _name = "Moviedle"
    _category = "Immagini, giochi e film"
    _date = datetime.date(2023, 6, 23)
    _day = "200"
    _emoji = "🎥"
    _url = "https://moviedle.app"

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

    @staticmethod
    def can_handle_this(raw_text):
        lines = raw_text.splitlines()
        _can_handle_this = "Moviedle" in lines[0]
        return _can_handle_this

    def parse(self):
        text = self.raw_text

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
class Murdle(Giochino):
    _name = "Murdle"
    _category = "Logica"
    _date = datetime.date(2023, 6, 23)
    _day = "1"
    _emoji = "🔪"
    _url = "https://murdle.com"

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

    @staticmethod
    def can_handle_this(raw_text):
        lines = raw_text.splitlines()
        _can_handle_this = len(lines) > 1 and "Murdle" in lines[1]
        return _can_handle_this

    def parse(self):
        text = self.raw_text

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
class Nerdle(Giochino):
    _name = "Nerdle"
    _category = "Logica"
    _date = datetime.date(2023, 9, 21)
    _day = "610"
    _emoji = "🤓"
    _url = "https://nerdlegame.com"

    can_lose: False

    examples = [
        "nerdlegame 801 3/6\n\n⬛️⬛️🟪⬛️🟪🟪🟪⬛️\n🟪🟪⬛️🟪🟩⬛️🟩⬛️\n🟩🟩🟩🟩🟩🟩🟩🟩",
        "nerdlegame 791 5/6\n\n🟪⬛️🟪⬛️🟪🟩⬛️⬛️\n🟪🟪🟩⬛️🟪🟩⬛️🟪\n⬛️🟪🟩🟩🟪🟩🟪🟪\n🟩🟪🟩🟩⬛️🟩🟩🟩\n🟩🟩🟩🟩🟩🟩🟩🟩",
    ]
    expected = [
        {"day": "801", "name": "Nerdle", "timestamp": 10, "tries": "3", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "791", "name": "Nerdle", "timestamp": 10, "tries": "5", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        lines = raw_text.splitlines()
        _can_handle_this = "nerdlegame" in lines[0]
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        lines = text.splitlines()
        first_line = lines[0].split()
        self.day = first_line[1]
        self.tries = first_line[2].split("/")[0]
        self.stars = None


@dataclass
class NerdleCross(Giochino):
    _name = "NerdleCross"
    _category = "Logica"
    _date = datetime.date(2023, 12, 12)
    _day = "198"
    _emoji = "🧮"
    _url = "https://nerdlegame.com/crossnerdle"

    examples = [
        "cross nerdle #198\n⬛⬜⬜⬜🟩⬜⬜⬛⬛\n⬛⬛⬜⬛⬜⬛⬛⬛⬜\n🟩⬛⬜⬛🟩⬜⬜⬜🟩\n⬜⬛🟩⬛⬜⬛⬛⬛🟩\n⬜🟩🟩⬜⬜⬜🟩⬜⬜\n⬜⬛⬛⬛⬜⬛⬜⬛🟩\n🟩⬜⬜🟩⬜⬛⬜⬛⬜\n⬜⬛⬛⬛⬜⬛🟩⬛⬛\n⬛⬛⬜⬜⬜⬜🟩⬜⬛\nPerfect solve - no 🎁 or 👀.\n@nerdlegame points: 6/6",
        "cross nerdle #201\n⬛⬜🟩🟩🟩⬜🟩⬜⬛\n🟩⬛⬜⬛🟩⬛🟩⬛⬜\n🟩🟩🟩⬛🟩⬜🟩🟩🟩\n⬜⬛🟩⬛⬜⬛⬛⬛🟩\n⬜⬜🟩🟩⬜🟩🟩⬜🟩\n🟩⬛⬛⬛🟩⬛🟩⬛🟩\n🟩⬜🟩🟩🟩⬛🟩🟩⬜\n⬜⬛🟩⬛🟩⬛🟩⬛⬜\n⬛⬜🟩⬜⬜🟩🟩⬜⬛\n🟩*37 + 🎁*0 + 👀* 2\n@nerdlegame points:4/6",
        "cross nerdle #198\n⬛️⬜️⬜️⬜️🎁⬜️⬜️⬛️⬛️\n⬛️⬛️⬜️⬛️⬜️⬛️⬛️⬛️⬜️\n🎁⬛️⬜️⬛️🎁⬜️⬜️⬜️🎁\n⬜️⬛️🎁⬛️⬜️⬛️⬛️⬛️🎁\n⬜️🎁🎁⬜️⬜️⬜️🎁⬜️⬜️\n⬜️⬛️⬛️⬛️⬜️⬛️⬜️⬛️🎁\n🎁⬜️⬜️🎁⬜️⬛️⬜️⬛️⬜️\n⬜️⬛️⬛️⬛️⬜️⬛️🎁⬛️⬛️\n⬛️⬛️⬜️⬜️⬜️⬜️🎁⬜️⬛️\n🟩*0 + 🎁*14 + 👀* 1\n@nerdlegame points:0/6",
    ]
    expected = [
        {"day": "198", "name": "NerdleCross", "timestamp": 10, "tries": 0, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "201", "name": "NerdleCross", "timestamp": 10, "tries": 2, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "198", "name": "NerdleCross", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        lines = raw_text.splitlines()
        _can_handle_this = "cross nerdle #" in lines[0] and "@nerdlegame" in lines[-1]
        return _can_handle_this

    def parse(self):
        text = self.raw_text

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
class Parole(Giochino):
    _name = "Parole"
    _category = "Giochi di parole"
    _date = datetime.date(2023, 9, 30)
    _day = "635"
    _emoji = "🇮🇹"
    _url = "https://par-le.github.io/gioco/"

    examples = [
        "Par🇮🇹le 825 4/6\n\n⬜️⬜️⬜️⬜️🟨\n⬜️🟨🟨⬜️⬜️\n🟩🟩🟩⬜️🟩\n🟩🟩🟩🟩🟩",
        "Par🇮🇹le 813 X/6\n\n⬜️🟨🟨⬜️⬜️\n🟨🟩⬜️⬜️🟩\n⬜️🟩🟩⬜️🟩\n⬜️🟩🟩⬜️🟩\n⬜️🟩🟩⬜️🟩\n🟩🟩🟩⬜️🟩",
    ]
    expected = [
        {"day": "825", "name": "Parole", "timestamp": 10, "tries": "4", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "813", "name": "Parole", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        lines = raw_text.splitlines()
        _can_handle_this = "Par🇮🇹le" in lines[0]
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        lines = text.splitlines()
        first_line = lines[0].split()
        self.day = first_line[1]
        self.tries = first_line[2].split("/")[0]


@dataclass
class Picsey(Giochino):
    _name = "Picsey"
    _category = "Immagini, giochi e film"
    _date = datetime.date(2023, 9, 25)
    _day = "100"
    _emoji = "🪟"
    _url = "https://picsey.io"

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

    @staticmethod
    def can_handle_this(raw_text):
        lines = raw_text.splitlines()
        _can_handle_this = "Picsey" in lines[0] and '🟦' in  raw_text
        return _can_handle_this

    def parse(self):
        text = self.raw_text

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
class Polygonle(Giochino):
    _name = "Polygonle"
    _category = "Giochi di parole"
    _date = datetime.date(2024, 3, 5)
    _day = "583"
    _emoji = "🔷"
    _url = "https://www.polygonle.com"

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

    @staticmethod
    def can_handle_this(raw_text):
        lines = raw_text.splitlines()
        _can_handle_this = "#Polygonle" in lines[0] and "/" in lines[0]
        return _can_handle_this

    def parse(self):
        text = self.raw_text

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
class Rotaboxes(Giochino):
    _name = "Rotaboxes"
    _category = "Logica"
    _date = datetime.date(2024, 3, 5)
    _day = "497"
    _emoji = "🧩"
    _url = "https://rotaboxes.com"

    can_lose: False

    examples = [
        "🟩🟦🟪 streak: 1\n🟥🟧 clicks: 31/31\n🟨 overspin: 4\nrotabox.es/497\n🟩🟩🟩🟩🟩🟩\n🟩🟩🟩🟩🟩🟩\n🟩🟩🟩🟩🟩🟩\n🟩🟩🟩🟩🟩🟩",
        "🟩🟦🟪 streak: 2\n🟥🟧 clicks: 122/31\n🟨 overspin: 45.5\nrotabox.es/497\n🟨🟩🟧🟩🟥🟨\n🟧🟩🟨🟩🟩🟨\n🟥🟥🟥🟥🟨🟥\n🟧🟥🟨🟨🟥🟧",
    ]
    expected = [
        {"day": "497", "name": "Rotaboxes", "timestamp": 10, "tries": 31, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "497", "name": "Rotaboxes", "timestamp": 10, "tries": 122, "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        lines = raw_text.splitlines()
        _can_handle_this = len(lines) >= 4 and "rotabox.es" in raw_text and "clicks:" in lines[1]
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        lines = text.splitlines()
        self.day = lines[3].split("/")[-1]
        punti = lines[1]
        punti = punti.split("clicks: ")[-1]
        # max_points = int(punti.split("/")[-1])
        clicks = int(punti.split("/")[0])
        self.tries = clicks


@dataclass
class Spellcheck(Giochino):
    _name = "Spellcheck"
    _category = "Logica"
    _date = datetime.date(2024, 3, 9)
    _day = "57"
    _emoji = "👂"
    _url = "https://spellcheck.xyz"

    can_lose: False

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

    @staticmethod
    def can_handle_this(raw_text):
        lines = raw_text.splitlines()
        _can_handle_this = "Spellcheck #" in lines[0]
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        lines = text.splitlines()
        first_line = lines[0].split()
        self.day = first_line[1][1:]
        self.tries = 15 - text.count("🟩")
        self.stars = None


@dataclass
class Spotle(Giochino):
    _name = "Spotle"
    _category = "Immagini, giochi e film"
    _date = datetime.date(2024, 3, 22)
    _day = "695"
    _emoji = "🎧"
    _url = "https://spotle.io/"

    examples = [
        "Spotle #710🎧\n\n⬜⬜⬜🟩\n\nspotle.io",
        "Spotle #710🎧\n\n⬜⬜⬜⬜⬜⬜⬜⬜⬜❌\n\nspotle.io",
    ]
    expected = [
        {"day": "710", "name": "Spotle", "timestamp": 10, "tries": "4", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "710", "name": "Spotle", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        lines = raw_text.splitlines()
        _can_handle_this = "Spotle #" in lines[0] and "spotle.io" in lines[-1]
        return _can_handle_this

    def parse(self):
        text = self.raw_text

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


@dataclass
class Squareword(Giochino):
    _name = "Squareword"
    _category = "Giochi di parole"
    _date = datetime.date(2023, 9, 25)
    _day = "602"
    _emoji = "🔠"
    _url = "https://squareword.org"

    can_lose: False

    examples = [
        "squareword.org 777: 14 guesses\n\n🟩🟨🟩🟧🟨\n🟨🟩🟧🟧🟧\n🟨🟧🟨🟧🟩\n🟨🟨🟨🟨🟩\n🟧🟨🟨🟨🟩\n\nless6:🟩 less11:🟨 less16:🟧 16+:🟥\n#squareword #squareword777",
        "squareword.org 793: 7 guesses\n\n🟩🟩🟩🟩🟩\n🟨🟨🟩🟨🟨\n🟩🟩🟩🟩🟩\n🟩🟩🟩🟩🟩\n🟨🟨🟨🟨🟨\n\nless6:🟩 less11:🟨 less16:🟧 16+:🟥\n#squareword #squareword793",
    ]
    expected = [
        {"day": "777", "name": "Squareword", "timestamp": 10, "tries": "14", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "793", "name": "Squareword", "timestamp": 10, "tries": "7", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        lines = raw_text.splitlines()
        _can_handle_this = "squareword.org" in lines[0]
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        lines = text.splitlines()
        first_line = lines[0].split()
        self.day = first_line[1][:-1]
        self.tries = first_line[2]
        self.stars = None


@dataclass
class Stepdle(Giochino):
    _name = "Stepdle"
    _category = "Giochi di parole"
    _date = datetime.date(2024, 3, 5)
    _day = "537"
    _emoji = "🗼"
    _url = "https://www.stepdle.com"

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

    @staticmethod
    def can_handle_this(raw_text):
        lines = raw_text.splitlines()
        _can_handle_this = "Stepdle #" in lines[0]
        return _can_handle_this

    def parse(self):
        text = self.raw_text

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
class TempoIndovinr(Giochino):
    _name = "TempoIndovinr"
    _category = "Immagini, giochi e film"
    _date = datetime.date(2023, 11, 17)
    _day = "5"
    _emoji = "🗺️"
    _url = "https://jacopofarina.eu/experiments/tempoindovinr"

    can_lose: False

    examples = [
        "TempoIndovinr day 146\nHo fatto 593/1000 punti a TempoIndovinr!\n\n🟩🟩🟩 (99%) 💀⬛️⬛️ (2%)\n🟧⬛️⬛️ (77%) 🟩🟩🟩 (99%)\n🟩🟩🟩 (97%) 💀⬛️⬛️ (17%)\n🟩🟩🟩 (99%) 💀⬛️⬛️ (3%)\n🟩🟩🟩 (100%) 💀⬛️⬛️ (0%)\n https://jacopofarina.eu/experiments/tempoindovinr/",
        "TempoIndovinr day 138\nHo fatto 727/1000 punti a TempoIndovinr!\n\n🟩🟩⬛️ (95%) 🟩🟩🟩 (100%)\n🟨⬛️⬛️ (84%) 🟨⬛️⬛️ (84%)\n🟩🟩🟩 (97%) 💀⬛️⬛️ (60%)\n🟩⬛️⬛️ (86%) 💀⬛️⬛️ (13%)\n🟩🟩⬛️ (95%) 💀⬛️⬛️ (13%)\n https://jacopofarina.eu/experiments/tempoindovinr/",
    ]
    expected = [
        {"day": "146", "name": "TempoIndovinr", "timestamp": 10, "tries": 407, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "138", "name": "TempoIndovinr", "timestamp": 10, "tries": 273, "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        lines = raw_text.splitlines()
        _can_handle_this = "experiments/tempoindovinr/" in lines[-1]
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        lines = text.splitlines()
        self.day = lines[0].split()[-1]
        self.tries = 1000 - int(lines[1].split()[2].split("/")[0])
        self.stars = None


@dataclass
class TimeGuessr(Giochino):
    _name = "TimeGuessr"
    _category = "Immagini, giochi e film"
    _date = datetime.date(2023, 11, 27)
    _day = "179"
    _emoji = "📅"
    _url = "https://timeguessr.com"

    can_lose: False

    examples = [
        "TimeGuessr #268 33,990/50,000\n🌎🟩⬛️⬛️ 📅🟩⬛⬛\n🌎🟩⬛️⬛️ 📅🟩🟩🟨\n🌎⬛️⬛️⬛️ 📅🟩🟩🟨\n🌎🟩🟩🟨 📅🟩🟨⬛\n🌎🟩🟩🟩 📅🟨⬛️⬛️\nhttps://timeguessr.com",
        "TimeGuessr #282 42,214/50,000\n🌎🟩🟩🟨 📅🟩🟩🟨\n🌎🟩🟩🟨 📅🟩🟩🟨\n🌎🟩🟩🟨 📅🟩🟩🟨\n🌎🟩🟨⬛️ 📅🟩🟩🟩\n🌎⬛️⬛️⬛️ 📅🟩🟨⬛\nhttps://timeguessr.com",
    ]
    expected = [
        {"day": "268", "name": "TimeGuessr", "timestamp": 10, "tries": 16010, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "282", "name": "TimeGuessr", "timestamp": 10, "tries": 7786, "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        lines = raw_text.splitlines()
        _can_handle_this = "TimeGuessr" in lines[0]
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        lines = text.splitlines()
        first_line = lines[0].split()
        self.day = first_line[1][1:]
        self.tries = 50_000 - int(first_line[2].split("/")[0].replace(",", ""))
        self.stars = None


@dataclass
class Tradle(Giochino):
    _name = "Tradle"
    _category = "Geografia e Mappe"
    _date = datetime.date(2023, 6, 23)
    _day = "474"
    _emoji = "🚢"
    _url = "https://oec.world/en/tradle"

    examples = [
        "#Tradle #761 5/6\n🟩🟩🟨⬜⬜\n🟩🟩🟩🟩⬜\n🟩🟩🟩🟩🟨\n🟩🟩🟩🟩🟨\n🟩🟩🟩🟩🟩\nhttps://games.oec.world/en/tradle",
        "#Tradle #761 X/6\n🟩🟨⬜⬜⬜\n🟩🟩🟩🟨⬜\n🟩🟩🟩🟩🟨\n🟩🟩🟩🟩⬜\n🟩🟩🟩🟩🟨\n🟩🟩🟩🟩🟨\nhttps://games.oec.world/en/tradle",
    ]
    expected = [
        {"day": "761", "name": "Tradle", "timestamp": 10, "tries": "5", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "761", "name": "Tradle", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        lines = raw_text.splitlines()
        _can_handle_this = "#Tradle" in lines[0]
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        lines = text.splitlines()
        first_line = lines[0].split()
        self.day = first_line[1][1:]
        self.tries = first_line[2].split("/")[0]
        self.stars = None


@dataclass
class Travle(Giochino):
    _name = "Travle"
    _category = "Geografia e Mappe"
    _date = datetime.date(2023, 11, 30)
    _day = "351"
    _emoji = "🧭"
    _url = "https://travle.earth"

    has_extra: True

    examples = [
        "#travle #484 +3\n🟩🟧✅🟥🟧✅✅\nhttps://travle.earth",
        "#travle #484 +0 (Perfect)\n✅✅✅✅\nhttps://travle.earth",
        "#travle #484 (4 lontano)\n🟧🟧🟥🟥🟧🟥🟥🟥🟥\nhttps://travle.earth",
    ]
    expected = [
        {"day": "484", "name": "Travle", "timestamp": 10, "tries": "3", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "484", "name": "Travle", "stars": 1, "timestamp": 10, "tries": "0", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "484", "name": "Travle", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        lines = raw_text.splitlines()
        _can_handle_this = "#travle " in lines[0] and "travle.earth" in lines[-1]
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        lines = text.splitlines()
        first_line = lines[0].split()
        self.day = first_line[1][1:]
        if "✅" not in lines[1]:
            self.tries = "X"
        else:
            self.tries = first_line[2][1:]

        # (Perfetto), (Perfect), (Perfekt)
        self.stars = None
        if '(P' in lines[0] and ')' in lines[0]:
            self.stars = 1

        # Hints
        hints = 0
        if len(first_line) > 3 and not self.stars and '(' in lines[0] and ')' in lines[0] and self.tries != "X":
            hints = first_line[3][1:]
            self.tries = int(int(self.tries) + ((int(hints) * (int(hints) + 1)) / 2))  # +1, +2, +3 (triangulars)



@dataclass
class TravleITA(Giochino):
    _name = "TravleITA"
    _category = "Geografia e Mappe"
    _date = datetime.date(2024, 2, 29)
    _day = "256"
    _emoji = "👢"
    _url = "https://travle.earth/ita"

    has_extra = True

    examples = [
        "#travle_ita #484 +3\n🟩🟧✅🟥🟧✅✅\nhttps://travle.earth/ita",
        "#travle_ita #484 +0 (Perfect)\n✅✅✅✅\nhttps://travle.earth/ita",
        "#travle_ita #484 (4 lontano)\n🟧🟧🟥🟥🟧🟥🟥🟥🟥\nhttps://travle.earth/ita",
    ]
    expected = [
        {"day": "484", "name": "TravleITA", "timestamp": 10, "tries": "3", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "484", "name": "TravleITA", "stars": 1, "timestamp": 10, "tries": "0", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "484", "name": "TravleITA", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        lines = raw_text.splitlines()
        _can_handle_this = "#travle_ita" in lines[0] and "/ita" in lines[-1]
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        lines = text.splitlines()
        first_line = lines[0].split()
        self.day = first_line[1][1:]
        if "✅" not in lines[1]:
            self.tries = "X"
        else:
            self.tries = first_line[2][1:]

        # (Perfetto), (Perfect), (Perfekt)
        self.stars = None
        if '(P' in lines[0] and ')' in lines[0]:
            self.stars = 1

        # Hints
        hints = 0
        if len(first_line) > 3 and not self.stars and '(' in lines[0] and ')' in lines[0] and self.tries != "X":
            hints = first_line[3][1:]
            self.tries = int(int(self.tries) + ((int(hints) * (int(hints) + 1)) / 2))  # +1, +2, +3 (triangulars)


@dataclass
class Unzoomed(Giochino):
    _name = "Unzoomed"
    _category = "Geografia e Mappe"
    _date = datetime.date(2024, 4, 16)
    _day = "89"
    _emoji = "🔎"
    _url = "https://unzoomed.com"

    examples = [
        'Unzoomed #89 1/6 🟢⚪️⚪️⚪️⚪️⚪️\n https://unzoomed.com',
        'Unzoomed #89 4/6 🔴🔴🟡🟢⚪️⚪️\n https://unzoomed.com',
        'Unzoomed #89 5/6 🔴🔴🔴🔴🟢⚪️\n https://unzoomed.com',
        'Unzoomed #87 6/6 🔴🔴🔴🔴🟡🟡\n https://unzoomed.com',
    ]

    expected = [
        {'day': '89', 'name': 'Unzoomed', 'stars': None, 'timestamp': 10, 'tries': '1', 'user_id': 456481297, 'user_name': 'Trifase'},
        {'day': '89', 'name': 'Unzoomed', 'stars': None, 'timestamp': 10, 'tries': '4', 'user_id': 456481297, 'user_name': 'Trifase'},
        {'day': '89', 'name': 'Unzoomed', 'stars': None, 'timestamp': 10, 'tries': '5', 'user_id': 456481297, 'user_name': 'Trifase'},
        {'day': '87', 'name': 'Unzoomed', 'stars': None, 'timestamp': 10, 'tries': 'X', 'user_id': 456481297, 'user_name': 'Trifase'},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        _can_handle_this = "Unzoomed #" in raw_text and "https://unzoomed.com" in raw_text
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        lines = text.splitlines()
        first_line = lines[0].split()
        self.day = first_line[1][1:]
        self.tries = first_line[2].split("/")[0]
        if '🟢' not in text:
            self.tries = 'X'



@dataclass
class Waffle(Giochino):
    _name = "Waffle"
    _category = "Giochi di parole"
    _date = datetime.date(2023, 6, 23)
    _day = "518"
    _emoji = "🧇"
    _url = "https://wafflegame.net/daily"

    examples = [
        "#waffle807 1/5\n\n🟩🟩🟩🟩🟩\n🟩⬜️🟩⬜️🟩\n🟩🟩⭐️🟩🟩\n🟩⬜️🟩⬜️🟩\n🟩🟩🟩🟩🟩\n\n🔥 streak: 2\nwafflegame.net",
        "#waffle807 5/5\n\n🟩🟩🟩🟩🟩\n🟩⭐️🟩⭐️🟩\n🟩🟩⭐️🟩🟩\n🟩⭐️🟩⭐️🟩\n🟩🟩🟩🟩🟩\n\n🔥 streak: 1\nwafflegame.net",
        "#waffle629 X/5\n\n🟩🟩🟩🟩🟩\n🟩⬜️🟩⬜️🟩\n🟩🟩🟩🟩🟩\n🟩⬜️🟩⬜️🟩\n🟩⬛️🟩⬛️🟩\n\n💔 streak: 0\nwafflegame.net",
    ]
    expected = [
        {"day": "807", "name": "Waffle", "stars": 1, "timestamp": 10, "tries": 14, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "807", "name": "Waffle", "stars": 5, "timestamp": 10, "tries": 10, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "629", "name": "Waffle", "stars": 0, "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        lines = raw_text.splitlines()
        _can_handle_this = "#waffle" in lines[0]
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        lines = text.splitlines()
        first_line = lines[0].split()
        self.day = first_line[0].replace("#waffle", "")
        punti = first_line[1].split("/")[0]
        self.tries = 15 - int(punti) if punti != "X" else "X"
        self.stars = text.count(b"\xe2\xad\x90".decode("utf-8"))


@dataclass
class WhereTaken(Giochino):
    _name = "WhereTaken"
    _category = "Geografia e Mappe"
    _date = datetime.date(2023, 6, 23)
    _day = "117"
    _emoji = "📸"
    _url = "http://wheretaken.teuteuf.fr"

    has_extra: True

    examples = [
        "📷 #WhereTaken🌎 #407 (08.04.2024) X/6\n🟦🟦🟦🟦🟨⬅️\n🟦🟦🟦🟦⬜️⬅️\n🟦🟦🟦🟦⬜️⬅️\n🟦🟦🟦🟦⬜️↖️\n🟦🟦🟦🟦⬜️⬅️\n🟦🟦🟨⬜️⬜️↖️\n\n\nwheretaken.teuteuf.fr",
        "📷 #WhereTaken🌎 #407 (08.04.2024) X/6\n🟦🟦🟦🟦🟨⬅️\n🟦🟦🟦🟦⬜️⬅️\n🟦🟦🟦🟦⬜️⬅️\n🟦🟦🟦🟦⬜️↖️\n🟦🟦🟦🟦⬜️⬅️\n🟦🟦🟨⬜️⬜️↖️\n⭐️⭐️\n\nwheretaken.teuteuf.fr",
        "📷 #WhereTaken🌎 #399 (31.03.2024) 1/6\n🟦🟦🟦🟦🟦🎉\n⭐⭐⭐⭐\n\nwheretaken.teuteuf.fr",
        "📷 #WhereTaken🌎 #398 (30.03.2024) 4/6\n🟦🟦🟦🟦🟨➡️\n🟦🟦🟦🟦🟨➡️\n🟦🟦🟦🟦🟨↖️\n🟦🟦🟦🟦🟦🎉\n⭐️\n\nwheretaken.teuteuf.fr",
    ]
    expected = [
        {"day": "407", "name": "WhereTaken", "stars": 0, "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "407", "name": "WhereTaken", "stars": 2, "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "399", "name": "WhereTaken", "stars": 4, "timestamp": 10, "tries": "1", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "398", "name": "WhereTaken", "stars": 1, "timestamp": 10, "tries": "4", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        lines = raw_text.splitlines()
        _can_handle_this = "WhereTaken" in lines[0]
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        lines = text.splitlines()
        first_line = lines[0].split()
        self.day = first_line[2][1:]
        self.tries = first_line[4].split("/")[0]
        self.stars = text.count(b"\xe2\xad\x90".decode("utf-8"))


@dataclass
class Wordle(Giochino):
    _name = "Wordle"
    _emoji = "🆒"
    _category = "Giochi di parole"
    _date = datetime.date(2023, 6, 23)
    _day = "734"
    _url = "https://www.nytimes.com/games/wordle/index.html"

    examples = [
        "Wordle 1,011 5/6\n\n🟩🟩⬛️⬛️⬛️\n🟩🟩🟨⬛️⬛️\n🟩🟩⬛️🟨⬛️\n🟩🟩⬛️🟩🟩\n🟩🟩🟩🟩🟩",
        "Wordle 821 X/6\n\n🟨🟩⬛️⬛️⬛️\n⬛️🟩🟩⬛️⬛️\n⬛️🟩🟩⬛️⬛️\n⬛️🟩🟩⬛️⬛️\n⬛️🟩🟩⬛️⬛️\n⬛️🟩🟩🟩⬛️",
    ]
    expected = [
        {"day": "1011", "name": "Wordle", "timestamp": 10, "tries": "5", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "821", "name": "Wordle", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        _can_handle_this = "Wordle" in raw_text and "/" in raw_text
        return _can_handle_this

    def parse(self):
        text = self.raw_text
        lines = text.splitlines()
        first_line = lines[0].split()
        # Wordle ti odio, chi cazzo scrive 1000 come "1.000" o "1,000"
        self.day = first_line[1].replace(".", "").replace(",", "")
        self.tries = first_line[-1].split("/")[0]
        self.stars = None

@dataclass
class WordPeaks(Giochino):
    _name = "WordPeaks"
    _category = "Giochi di parole"
    _date = datetime.date(2024, 4, 16)
    _day = "782"
    _emoji = "🔤"
    _url = "https://wordpeaks.com"

    examples = [
        'Word Peaks #782 1/6\n\n  🟩🟩🟩🟩🟩\nhttps://wordpeaks.com',
        'Word Peaks #782 3/6\n\n  🔼🔼🔼🟩🔼\n  🔼🟩🔼🔽🔼\n  🟩🟩🟩🟩🟩\nhttps://wordpeaks.com',
        'Word Peaks #782 X/6\n\n  🔼🔽🔼🔽🔼\n  🔼🔽🔼🔼🔽\n  🟩🟩🔼🔽🔼\n  🔼🔼🔼🟩🔼\n  🔼🔽🔼🔽🔼\n  🔼🔼🔼🔽🔼\nhttps://wordpeaks.com',
    ]
    expected = [
        {'day': '782', 'name': 'WordPeaks', 'stars': None, 'timestamp': 10, 'tries': '1', 'user_id': 456481297, 'user_name': 'Trifase'},
        {'day': '782', 'name': 'WordPeaks', 'stars': None, 'timestamp': 10, 'tries': '3', 'user_id': 456481297, 'user_name': 'Trifase'},
        {'day': '782', 'name': 'WordPeaks', 'stars': None, 'timestamp': 10, 'tries': 'X', 'user_id': 456481297, 'user_name': 'Trifase'},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        _can_handle_this = any(x in raw_text for x in "🟩🔼🔽") and "https://wordpeaks.com" in raw_text
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        lines = text.splitlines()
        first_line = lines[0].split()
        self.day = first_line[2][1:]
        self.tries = first_line[3].split("/")[0]


@dataclass
class Worldle(Giochino):
    _name = "Worldle"
    _category = "Geografia e Mappe"
    _date = datetime.date(2023, 6, 23)
    _day = "518"
    _emoji = "🗺️"
    _url = "https://worldle.teuteuf.fr"

    examples = [
        "#Worldle #807 (07.04.2024) 1/6 (100%)\n🟩🟩🟩🟩🟩🎉\n🧭⭐\nhttps://worldle.teuteuf.fr",
        "#Worldle #808 (08.04.2024) 4/6 (100%)\n🟩🟩🟩🟨⬜↗️\n🟩🟩🟩🟩🟨↘️\n🟩🟩🟩🟩🟨⬇️\n🟩🟩🟩🟩🟩🎉\n\nhttps://worldle.teuteuf.fr",
        "#Worldle #808 (08.04.2024) X/6 (94%)\n🟩🟩🟩⬛️⬛️⬆️\n🟩🟩🟩🟩⬛️↖️\n🟩🟩🟩🟩🟨↖️\n🟩🟩🟨⬛️⬛️↗️\n🟩🟨⬛️⬛️⬛️↗️\n🟩🟩🟩🟩🟨➡️\n\nhttps://worldle.teuteuf.fr",
    ]
    expected = [
        {"day": "807", "name": "Worldle", "stars": 2, "timestamp": 10, "tries": "1", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "808", "name": "Worldle", "stars": 0, "timestamp": 10, "tries": "4", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "808", "name": "Worldle", "stars": 0, "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        lines = raw_text.splitlines()
        _can_handle_this = "Worldle" in lines[0]
        return _can_handle_this

    def parse(self):
        text = self.raw_text

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


#######
def get_giochini():
    klasses = [
        cls_obj
        for _, cls_obj in inspect.getmembers(sys.modules[__name__], inspect.isclass)
        if cls_obj.__module__ == sys.modules[__name__].__name__ and cls_obj.__base__ == Giochino and not cls_obj.hidden_game
        # TODO: some sort of frequency-of-use ordering?
    ]
    # Order matters - this have to be the last
    klasses.append(UnsupportedGame)
    klasses.append(UnknownGame)
    return klasses


def get_games() -> dict:
    games = {}
    giochini = get_giochini()
    for giochino in giochini:
        # Skip game if hidden
        if giochino.hidden_game:
            continue

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


def test(print_debug, giochino=None):
    if giochino:
        giochini = [giochino]
    else:
        giochini = [
            cls_obj
            for _, cls_obj in inspect.getmembers(sys.modules[__name__], inspect.isclass)
            if cls_obj.__module__ == sys.modules[__name__].__name__ and cls_obj.__base__ == Giochino and cls_obj.examples
        ]

    # giochini = [Wordle, Parole, Bandle, Chrono]

    for gioco in giochini:
        for i, _ in enumerate(gioco.examples):
            update = generate_sample_update(gioco.examples[i])
            giochino = gioco(update)
            print(f"[{i}] ==== {giochino._name} ====")
            if print_debug:
                print(f"info = {giochino.info}")
                print(f"expected = {giochino.expected[i]}")
                print(f"punteggio = {giochino.punteggio}")
            assert all(x in giochino.punteggio.items() for x in giochino.expected[i].items())
            print("test_passed ✅")
            print()

# Tests! you can pass None as second parameter to test all games
if __name__ == '__main__':
    giochino_da_testare = Connections
    test(True, giochino_da_testare)
