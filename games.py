import datetime
import inspect
import re
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
        locale.setlocale(locale.LC_ALL, "en_US.UTF-8")
        date = datetime.datetime.strptime(date, "%b %d, %Y").date()
        locale.setlocale(locale.LC_TIME, "it_IT.UTF-8")

    if isinstance(date, str) and game == "BracketCity":
        locale.setlocale(locale.LC_ALL, "en_US.UTF-8")
        date = datetime.datetime.strptime(date, "%B %d, %Y").date()
        locale.setlocale(locale.LC_TIME, "it_IT.UTF-8")

    if isinstance(date, str) and game == "Timdle":
        locale.setlocale(locale.LC_ALL, "en_US.UTF-8")
        date = datetime.datetime.strptime(date, "%b %d %Y").date()
        locale.setlocale(locale.LC_TIME, "it_IT.UTF-8")

    if isinstance(date, str) and game == "HighFive":
        date = datetime.datetime.strptime(date, "%Y-%m-%d").date()

    if isinstance(date, str) and game == "Moviedle":
        date = datetime.datetime.strptime(date, "#%Y-%m-%d").date()

    if isinstance(date, str) and game == "NFLXdle":
        date = datetime.datetime.strptime(date, "#%Y-%m-%d").date()

    if isinstance(date, str) and game == "Posterdle":
        date = datetime.datetime.strptime(date, "#%Y-%m-%d").date()

    if isinstance(date, str) and game == "Murdle":
        date = datetime.datetime.strptime(date, "%m/%d/%Y").date()

    if isinstance(date, str) and game == "Picsey":
        date = datetime.datetime.strptime(date, "%m.%d.%y").date()

    if isinstance(date, str) and game == "Chronophoto":
        date = datetime.datetime.strptime(date, "%d/%m/%Y").date()

    if isinstance(date, str) and game == "Heardle":
        date = datetime.datetime.strptime(date, "%d/%m/%Y").date()

    if isinstance(date, str) and game == "Snoop":
        date = datetime.datetime.strptime(date, "%y/%m/%d").date()

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


def sanitize(text: str) -> str:
    # replace unicode \xa0 with space
    text_after = text.replace("\xa0", " ")
    # print(f"{text.encode('utf-8')}\n↓\n{text_after.encode('utf-8')}")
    return text_after


def time_to_seconds(time_str: str) -> int:
    time_lst: list[str] = time_str.split(" ")
    seconds = 0
    for t in time_lst:
        if t.endswith("s"):
            seconds += int(t[:-1])
        elif t.endswith("m"):
            seconds += int(t[:-1]) * 60
        elif t.endswith("h"):
            seconds += int(t[:-1]) * 60 * 60
    return seconds


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
                "Apparle #" in raw_text and "https://apparle.com" in raw_text,  # Apparle
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
        wordlist = ["#Angle", "https://www.angle.wtf"]
        _can_handle_this = all(c in raw_text for c in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text
        self.stars = None

        day_match = re.search(r"#Angle #(\d+)", text)
        self.day = day_match.group(1) if day_match else None

        score_match = re.search(r"#Angle #\d+ ([X\d]+)/\d+", text)

        if score_match:
            points = score_match.group(1)
            self.tries = points  # Will be either a number or "X"
        else:
            self.tries = None


# @dataclass
# class Apparle(Giochino):
#     _name = "Apparle"
#     _category = "Immagini, giochi e musica"
#     _date = datetime.date(2024, 4, 14)
#     _day = "45"
#     _emoji = "💵"
#     _url = "https://www.apparle.com"

#     message = "sconosciuto"
#     hidden_game = True

#     examples = [
#         "Apparle #28 1/6\n🏆 -1.2%\n\nhttps://apparle.com",
#         "Apparle #28 3/6\n⬇️ +50%\n⬆️ -13.7%\n💵 -1.2%\n\nhttps://apparle.com",
#         "Apparle #45 6/6\n⬆️ -32.2%\n⬆️ -66.1%\n⬆️ -83.1%\n⬆️ -66.1%\n⬆️ -57.6%\n💵 0%\n\nhttps://apparle.com",
#         "Apparle #45 6/6\n⬆️ -84.7%\n⬆️ -16.1%\n⬇️ +102.5%\n⬇️ +68.6%\n⬇️ +145.8%\n❌ +154.2%\n\nhttps://apparle.com",
#     ]
#     expected = [
#         {"day": "28", "name": "Apparle", "stars": None, "timestamp": 10, "tries": "1", "user_id": 456481297, "user_name": "Trifase"},
#         {"day": "28", "name": "Apparle", "stars": None, "timestamp": 10, "tries": "3", "user_id": 456481297, "user_name": "Trifase"},
#         {"day": "45", "name": "Apparle", "stars": None, "timestamp": 10, "tries": "6", "user_id": 456481297, "user_name": "Trifase"},
#         {"day": "45", "name": "Apparle", "stars": None, "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
#     ]

#     @staticmethod
#     def can_handle_this(raw_text):
#         lines = raw_text.splitlines()
#         _can_handle_this = "Apparle #" in lines[0] and "https://apparle.com" in lines[-1]
#         return _can_handle_this

#     def parse(self):
#         text = self.raw_text

#         lines = text.splitlines()
#         points = lines[0].split()[-1].split("/")[0]
#         self.day = lines[0].split()[1][1:]
#         self.tries = points
#         if "❌" in text:
#             self.tries = "X"
#         self.stars = None


@dataclass
class Bandle(Giochino):
    _name = "Bandle"
    _category = "Immagini, giochi e musica"
    _date = datetime.date(2024, 3, 3)
    _day = "564"
    _emoji = "🎸"
    _url = "https://bandle.app/"

    examples = [
        "Bandle #597 4/6\n⬛️⬛️⬛️🟩⬜️⬜️\nFound: 10/14 (71.4%)\nCurrent Streak: 1 (max 2)\n#Bandle #Heardle #Wordle \n https://bandle.app/",
        "Bandle #579 x/6\n⬛️⬛️⬛️⬛️⬛️⬛️\nFound: 3/5 (60%)\n#Bandle #Heardle #Wordle \n https://bandle.app/",
        'Bandle #956 2/5\n🟨🟩⬜⬜⬜\nFound: 102/116 (87.9%)\nCurrent Daily Streak: 1 (max 5)\n#Bandle #Heardle \nhttps://bandle.app'
    ]
    expected = [
        {"day": "597", "name": "Bandle", "timestamp": 10, "tries": "4", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "579", "name": "Bandle", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "956", "name": "Bandle", "timestamp": 10, "tries": "2", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["Bandle #", "https://bandle.app"]
        _can_handle_this = all(c in raw_text for c in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text
        self.tries = "X"
        matches = re.search(r"Bandle\s#(\d+)\s(\d+|x|X)\/", text)
        self.day = matches.group(1)

        punti = matches.group(2)

        if punti.lower() != "x":
            self.tries = punti



@dataclass
class BracketCity(Giochino):
    _name = "BracketCity"
    _category = "Giochi di parole"
    _date = datetime.date(2025, 5, 1)
    _day = "100"
    _emoji = "🈁"
    _url = "https://www.theatlantic.com/games/bracket-city/"

    can_lose: False

    examples = [
        '[Bracket City]\nApril 30, 2025\n\nhttps://www.theatlantic.com/games/bracket-city/\n\nRank: 📸 (Tourist)\n❌ Wrong guesses: 7\n👀 Peeks: 10\n🛟 Answers Revealed: 6\n\nTotal Score: 0.0\n⬜️⬜️⬜️⬜️⬜️⬜️⬜️⬜️⬜️⬜️',
        '[Bracket City]\nApril 30, 2025\n\nhttps://www.theatlantic.com/games/bracket-city/\n\nRank: 💼 (Power Broker)\n❌ Wrong guesses: 4\n\nTotal Score: 92.0\n🟩🟩🟩🟩🟩🟩🟩🟩🟩⬜',
        '[Bracket City]\nApril 28, 2025\n\nhttps://www.theatlantic.com/games/bracket-city/\n\nRank: 📸 (Tourist)\n❌ Wrong guesses: 4\n👀 Peeks: 5\n🛟 Answers Revealed: 4\n\nTotal Score: 7.0\n🟥⬜️⬜️⬜️⬜️⬜️⬜️⬜️⬜️⬜️',
    ]
    expected = [
        {"day": "99", "name": "BracketCity", "timestamp": 10, "tries": "100", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "99", "name": "BracketCity", "timestamp": 10, "tries": "8", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "97", "name": "BracketCity", "timestamp": 10, "tries": "93", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["[Bracket City]", "https://www.theatlantic.com/games/bracket-city/"]
        _can_handle_this = all(c in raw_text for c in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text


        
        match_date = re.search(r"(\w+ \d{1,2}, \d{4})", text)
        if match_date:
            date_str = match_date.group(1)
            print('regex date: ', date_str)
        else:
            date_str = text.split('\n')[1]
            print('string date', date_str)
        self.day = get_day_from_date(self._date, self._day, "BracketCity", date_str)
        point_match = re.search(r"Total Score: (\d+\.\d)", text)
        if point_match:
            points = float(point_match.group(1))
            self.tries = str(int(100 - points))


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
        "Chrono\n🥈 CHRONO  #1107\n\n🟢🟢⚪️🟢🟢⚪️\n🟢🟢🟢🟢🟢🟢\n\n⏱: 36.4\n🔥: 2\nhttps://chrono.quest",
    ]
    expected = [
        {"day": "749", "name": "Chrono", "stars": 9949.2, "timestamp": 10, "tries": 1, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "760", "name": "Chrono", "stars": 9966.7, "timestamp": 10, "tries": 2, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "748", "name": "Chrono", "stars": 9944.2, "timestamp": 10, "tries": 3, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "748", "name": "Chrono", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "1107", "name": "Chrono", "stars": 9963.6, "timestamp": 10, "tries": 2, "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["CHRONO", "https://chrono.quest", "🔥"]
        _can_handle_this = all(c in raw_text for c in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        day_match = re.search(r"CHRONO\s+#(\d+)", text)
        self.day = day_match.group(1) if day_match else None

        medal_match = re.search(r"(🥇|🥈|🥉|😬)", text)
        medal = medal_match.group(1) if medal_match else None

        # Set tries based on medal
        if medal == "🥇":
            self.tries = 1
        elif medal == "🥈":
            self.tries = 2
        elif medal == "🥉":
            self.tries = 3
        elif medal == "😬":
            self.tries = "X"
        else:
            self.tries = None

        time_match = re.search(r"⏱: (\d+\.\d+)", text)
        time = float(time_match.group(1)) if time_match else None

        # Calculate stars based on time (10000 - time)
        if time is not None and self.tries != "X":
            self.stars = 10_000 - time
        else:
            self.stars = None


@dataclass
class Chronophoto(Giochino):
    _name = "Chronophoto"
    _category = "Immagini, giochi e musica"
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
        wordlist = ["I got a score of", "chronophoto.app"]
        _can_handle_this = all(c in raw_text for c in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        score_match = re.search(r"I got a score of (\d+)", text)
        score = int(score_match.group(1)) if score_match else None

        date_match = re.search(r"Chronophoto: (\d+/\d+/\d+)", text)
        date_str = date_match.group(1) if date_match else None

        if date_str:
            self.day = get_day_from_date(self._date, self._day, "Chronophoto", date_str)
        else:
            self.day = None

        # Calculate tries (5000 - score)
        if score is not None:
            self.tries = 5_000 - score
            if self.tries == 0:
                self.tries = "X"
        else:
            self.tries = None

        self.stars = None


@dataclass
class Cloudle(Giochino):
    _name = "Cloudle"
    _category = "Geografia e Mappe"
    _date = datetime.date(2023, 6, 23)
    _day = "449"
    _emoji = "🌦️"
    _url = "https://cloudle.app"

    hidden_game = True

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
        wordlist = ["Cloudle -", "https://cloudle.app"]
        _can_handle_this = all(c in raw_text for c in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        tries_match = re.search(r": ([X\d]+)/\d+", text)
        if tries_match:
            self.tries = tries_match.group(1)
        else:
            self.tries = None

        # Cloudle is the only game without a day - we assume that the date is today.
        self.day = get_day_from_date(self._date, self._day, "Cloudle", datetime.date.today())

        self.stars = None


@dataclass
class CluesBySam(Giochino):
    _name = "CluesBySam"
    _category = "Logica"
    _date = datetime.date(2025, 9, 9)
    _day = "100"
    _emoji = "🔎"
    _url = "https://cluesbysam.com"
    
    examples = [
        "Clues by Sam - Sep 13th 2025\nLess than 36 minutes\n🟩🟩🟠🟨\n🟨🟩🟠🟩\n🟩🟩🟩🟩\n🟠🟠🟡🟠\n🟩🟠🟠🟩",
        "I solved the daily Clues by Sam (Sep 9th 2025) in 05:46\n🟩🟩🟩🟩\n🟩🟩🟩🟩\n🟨🟩🟩🟩\n🟩🟩🟩🟩\n🟩🟩🟩🟩\nhttps://cluesbysam.com",
        "I solved the daily Clues by Sam, Nov 15th 2025 (Hard), in 03:56\n🟩🟩🟩🟩\n🟩🟩🟩🟩\n🟨🟩🟩🟩\n🟩🟩🟩🟩\n🟡🟩🟩🟩\nhttps://cluesbysam.com",
        "I solved the daily Clues by Sam, Nov 16th 2025 (Hard), in less than 12 minutes\n🟩🟩🟩🟩\n🟩🟩🟨🟩\n🟩🟩🟩🟩\n🟩🟡🟨🟩\n🟠🟨🟩🟩\nhttps://cluesbysam.com"
    ]
    expected = [
        {"day": "104", "name": "CluesBySam", "timestamp": 10, "tries": 2580, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "100", "name": "CluesBySam", "timestamp": 10, "tries": 361, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "167", "name": "CluesBySam", "timestamp": 10, "tries": 281, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "168", "name": "CluesBySam", "timestamp": 10, "tries": 795, "user_id": 456481297, "user_name": "Trifase"}, # New Expected (660 base + 255 penalty)
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["Clues by Sam ", "Clues by Sam, "]
        return any(w in raw_text for w in wordlist)

    def parse(self):
        text = self.raw_text
        self.tries = 0 # Initialize tries to 0, which holds the total seconds

        ## 📅 Extract Date and Calculate Day (Made robust)
        # Handles "Sep 13th 2025" and "(Sep 9th 2025)" and ", Nov 15th 2025 (Hard),"
        date_match = re.search(r"(\w+)\s*(\d+)(?:st|nd|rd|th)?\s*(\d{4})", text)
        
        if date_match:
            month, day, year = date_match.groups()
            date_str = f"{month} {day} {year}"
            
            locale.setlocale(locale.LC_ALL, "en_US.UTF-8")
            try:
                actual_date = datetime.datetime.strptime(date_str, "%b %d %Y").date()
                self.day = get_day_from_date(self._date, self._day, self._name, actual_date)
            except ValueError:
                self.day = None
            finally:
                locale.setlocale(locale.LC_TIME, "it_IT.UTF-8") 

        ## ⏱️ Calculate Base Time (Made robust)
        minutes_match = re.search(r"less\s+than\s+(\d+)\s+minutes", text, re.IGNORECASE)
        solved_match = re.search(r"in (\d+):(\d+)", text)
        
        if minutes_match:
            base_minutes = int(minutes_match.group(1)) - 1
            self.tries += base_minutes * 60
        elif solved_match:
            base_minutes = int(solved_match.group(1))
            base_seconds = int(solved_match.group(2))
            self.tries += base_minutes * 60 + base_seconds
        
        ## ➕ Add Penalties
        penalties = {
            "🟨": 15,
            "🟡": 30,
            "🟠": 60,
        }
        
        # Ensure self.tries is an integer before addition
        if isinstance(self.tries, int):
            for emoji, penalty in penalties.items():
                self.tries += text.count(emoji) * penalty
        
        self.stars = None


@dataclass
class Colorfle(Giochino):
    _name = "Colorfle"
    _category = "Immagini, giochi e musica"
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
        wordlist = ["Colorfle", "accuracy"]
        _can_handle_this = all(c in raw_text for c in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        day_match = re.search(r"Colorfle (\d+)", text)
        self.day = day_match.group(1) if day_match else None

        tries_match = re.search(r"(\d+|X)/6", text)
        self.tries = tries_match.group(1) if tries_match else None

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
    has_extra = True

    examples = [
        "Connections \nPuzzle #299\n🟩🟩🟩🟩\n🟨🟨🟨🟨\n🟦🟦🟦🟦\n🟪🟪🟪🟪",
        "Connections \nPuzzle #300\n🟩🟪🟩🟩\n🟩🟪🟩🟩\n🟩🟪🟩🟩\n🟩🟩🟩🟩\n🟦🟦🟦🟦\n🟪🟪🟪🟪\n🟨🟨🟨🟨",
        "Connections \nPuzzle #302\n🟨🟨🟨🟨\n🟪🟩🟪🟪\n🟪🟪🟪🟦\n🟪🟦🟪🟪\n🟪🟪🟩🟪",
        "Connections\nPuzzle #324 \n🟨🟨🟨🟨 \n🟦🟦🟩🟦 \n🟦🟦🟪🟦 \n🟦🟦🟦🟦 \n🟩🟩🟩🟪 \n🟩🟩🟩🟩 \n🟪🟪🟪🟪",
        "Connections\nPuzzle #528\n🟪🟪🟪🟪\n🟦🟦🟦🟦\n🟩🟩🟩🟩\n🟨🟨🟨🟨",
    ]
    expected = [
        {"day": "299", "name": "Connections", "timestamp": 10, "tries": 1, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "300", "name": "Connections", "timestamp": 10, "tries": 4, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "302", "name": "Connections", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "324", "name": "Connections", "timestamp": 10, "tries": 4, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "528", "name": "Connections", "timestamp": 10, "tries": 1, "user_id": 456481297, "user_name": "Trifase", "stars": 1},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["Connections", "Puzzle #"]
        _can_handle_this = all(c in raw_text for c in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        # Extract day number
        day_match = re.search(r"Puzzle #(\d+)", text)
        self.day = day_match.group(1) if day_match else None

        # Extract all lines with colored squares
        square_lines = re.findall(r"[🟩🟨🟦🟪]+", text)

        # Use the existing is_connection_completed function to check completion
        if is_connection_completed(square_lines):
            self.tries = len(square_lines) - 3
        else:
            self.tries = "X"

        # Reverse rainbow
        if self.tries == 1 and [squares[0] for squares in square_lines] == ["🟪", "🟦", "🟩", "🟨"]:
            self.stars = 1
            self.win_message = "🌟 Nice! 🌈"


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
        wordlist = ["I played contexto.me"]
        _can_handle_this = all(c in raw_text for c in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        # Extract day number
        day_match = re.search(r"contexto\.me #(\d+)", text)
        self.day = day_match.group(1) if day_match else None

        # Check if the user gave up
        if re.search(r"but I gave up", text):
            self.tries = "X"
        # Check if hints were used
        elif hint_match := re.search(r"got it in (\d+) guesses and (\d+) hints", text):
            guesses = int(hint_match.group(1))
            hints = int(hint_match.group(2))
            self.tries = guesses + (hints * 15)
        # Regular case - no hints
        else:
            tries_match = re.search(r"got it in (\d+) guesses", text)
            self.tries = tries_match.group(1) if tries_match else None


@dataclass
class Countryle(Giochino):
    _name = "Countryle"
    _category = "Geografia e Mappe"
    _date = datetime.date(2025, 8, 25)
    _day = "1284"
    _emoji = "🌐"
    _url = "https://countryle.com"

    can_lose: False

    examples = [
        "#Countryle 818\nGuessed in 1 tries.\n\n🟢🟢🟢🟢🟢\n\nhttps://countryle.com",
        "#Countryle 818\nGuessed in 4 tries.\n\n🟢⚪️⚪️⚪️⚪️\n🟢🟢⚪️⚪️⚪️\n🟢🟢🟢⚪️⚪️\n🟢🟢🟢🟢🟢\n\nhttps://countryle.com",
        "#Countryle 818\nEncertat en 4 intents.\n\n🟢⚪️⚪️⚪️⚪️\n🟢🟢⚪️⚪️⚪️\n🟢🟢🟢⚪️⚪️\n🟢🟢🟢🟢🟢\n\nhttps://countryle.com",
        "#Countryle 818\nDeviné en 4 essais.\n\n🟢⚪️⚪️⚪️⚪️\n🟢🟢⚪️⚪️⚪️\n🟢🟢🟢⚪️⚪️\n🟢🟢🟢🟢🟢\n\nhttps://countryle.com",
        "#Countryle 818\nErraten in 4 versuchen.\n\n🟢⚪️⚪️⚪️⚪️\n🟢🟢⚪️⚪️⚪️\n🟢🟢🟢⚪️⚪️\n🟢🟢🟢🟢🟢\n\nhttps://countryle.com",
    ]

    expected = [
        {"day": "818", "name": "Countryle", "timestamp": 10, "tries": "1", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "818", "name": "Countryle", "timestamp": 10, "tries": "4", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "818", "name": "Countryle", "timestamp": 10, "tries": "4", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "818", "name": "Countryle", "timestamp": 10, "tries": "4", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "818", "name": "Countryle", "timestamp": 10, "tries": "4", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["#Countryle", "https://countryle.com"]
        _can_handle_this = all(c in raw_text for c in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        # Extract day number using regex
        day_match = re.search(r"#Countryle (\d+)", text)
        self.day = day_match.group(1) if day_match else None

        # Extract tries count using regex
        tries_match = re.search(r"(\d+)\s(?:[a-z]+).", text)
        self.tries = tries_match.group(1) if tries_match else None

        self.stars = None


@dataclass
class Crossclimb(Giochino):
    _name = "Crossclimb"
    _category = "Giochi di parole"
    _date = datetime.date(2024, 10, 10)
    _day = "163"
    _emoji = "🪜"
    _url = "https://lnkd.in/crossclimb"

    can_lose: False

    examples = [
        "Crossclimb #159 | 1:27\nFill order: 1️⃣ 2️⃣ 3️⃣ 4️⃣ 5️⃣ ⬆️ ⬇️ 🪜\nlnkd.in/crossclimb.",
        "Crossclimb #160 | 0:45 and flawless\nFill order: 1️⃣ 2️⃣ 3️⃣ 4️⃣ 5️⃣ ⬆️ ⬇️ 🪜\nlnkd.in/crossclimb.",
        "Crossclimb #162 | 1:42 and flawless\nFill order: 1️⃣ 2️⃣ 3️⃣ 4️⃣ 5️⃣ ⬆️ ⬇️ 🪜\nlnkd.in/crossclimb.",
        "Crossclimb #163 | 1:34\nFill order: 1️⃣ 2️⃣ 3️⃣ 5️⃣ 4️⃣ ⬇️ ⬆️ 🪜\nlnkd.in/crossclimb.",
        "Crossclimb #225\n0:38 🪜\nlnkd.in/crossclimb.",
        "Crossclimb #223\n1:02 🪜\nlnkd.in/crossclimb.",
    ]
    expected = [
        {"day": "159", "name": "Crossclimb", "timestamp": 10, "tries": "127", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "160", "name": "Crossclimb", "timestamp": 10, "tries": "045", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "162", "name": "Crossclimb", "timestamp": 10, "tries": "142", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "163", "name": "Crossclimb", "timestamp": 10, "tries": "134", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "225", "name": "Crossclimb", "timestamp": 10, "tries": "038", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "223", "name": "Crossclimb", "timestamp": 10, "tries": "102", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["Crossclimb", "lnkd.in/crossclimb"]
        _can_handle_this = all(c in raw_text for c in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        day_match = re.search(r"Crossclimb #(\d+)", text)
        self.day = day_match.group(1) if day_match else None

        if "|" in text:
            time_match = re.search(r"\| (\d+:\d+)", text)
            if time_match:
                time_str = time_match.group(1)
                self.tries = "".join([x for x in time_str if x in "0123456789"])

        else:
            time_match = re.search(r"\n(\d+:\d+)", text)
            if time_match:
                time_str = time_match.group(1)
                self.tries = "".join([x for x in time_str if x in "0123456789"])


@dataclass
class Decipher(Giochino):
    _name = "Decipher"
    _category = "Giochi di parole"
    _date = datetime.date(2025, 2, 27)
    _day = "254"
    _emoji = "🔎"
    _url = "https://decipher.wtf"

    can_lose: True

    examples = [
        "Decipher #2\ndeciphered in ⏱️ 3h 1m 44s\n⭐⭐⭐⭐\nhttps://decipher.wtf",
        "Decipher #84\ndeciphered in ⏱ 3m 15s\n⭐️⭐️\nhttps://decipher.wtf",
        "Decipher #248\n💥 Failed\nhttps://decipher.wtf",
        "Decipher #254\ndeciphered in ⏱️ 39s\n⭐️⭐️\nhttps://decipher.wtf",
    ]
    expected = [
        {"day": "2", "name": "Decipher", "timestamp": 10, "tries": 10914, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "84", "name": "Decipher", "timestamp": 10, "tries": 225, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "248", "name": "Decipher", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "254", "name": "Decipher", "timestamp": 10, "tries": 69, "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["Decipher #", "https://decipher.wtf"]
        _can_handle_this = all(c in raw_text for c in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        # Extract day number using regex
        day_match = re.search(r"Decipher #(\d+)", text)
        self.day = day_match.group(1) if day_match else None

        # Check for failed attempt
        if re.search(r"Failed|💥", text):
            self.tries = "X"
        else:
            # Extract time using regex
            time_match = re.search(r"deciphered in ⏱[️]?\s+(.+)", text)
            if time_match:
                string_time = time_match.group(1)
                self.tries = time_to_seconds(string_time)

                # Count stars and apply penalty
                stars = text.count("⭐")
                # 10 seconds penalty for each star lost
                self.tries += (5 - stars) * 10


@dataclass
class Disorderly(Giochino):
    _name = "Disorderly"
    _category = "Logica"
    _date = datetime.date(2025, 5, 1)
    _day = "100"
    _emoji = "📄"
    _url = "https://playdisorderly.com/"

    can_lose: False

    examples = [
        "I just played Disorderly! - Sort these video game consoles by how many units they've sold\nhttps://playdisorderly.com/\n\n1️⃣ 🟢 🟢\n2️⃣ 🔴 🟢\n3️⃣ 🟢 🟢\n4️⃣ 🔴 🟢\n5️⃣ 🔴 🟢\n6️⃣ 🔴 🟢",
        "I just played Disorderly! - Sort these video game consoles by how many units they've sold\nhttps://playdisorderly.com/\n\n1️⃣ 🔴 🟢 🟢\n2️⃣ 🔴 🔴 🟢\n3️⃣ 🟢 🟢 🟢\n4️⃣ 🔴 🔴 🟢\n5️⃣ 🔴 🟢 🟢\n6️⃣ 🔴 🟢 🟢",
        'I just played Disorderly! - Sort these amounts of money from most to least valuable (as of February 15\nhttps://playdisorderly.com/\n\n1️⃣ 🔴 🔴 🔴 🔴 🔴 🔴 🔴 🔴 🟢\n2️⃣ 🔴 🔴 🔴 🔴 🔴 🔴 🟢 🟢 🟢\n3️⃣ 🔴 🔴 🔴 🔴 🔴 🔴 🔴 🟢 🟢\n4️⃣ 🔴 🔴 🔴 🟢 🟢 🟢 🟢 🟢 🟢\n5️⃣ 🔴 🔴 🔴 🔴 🟢 🟢 🟢 🟢 🟢\n6️⃣ 🔴 🔴 🔴 🔴 🔴 🔴 🔴 🔴 🟢',
    ]
    expected = [
        {
            "day": f'{get_day_from_date(_date, _day, "Disorderly", datetime.date.today())}',
            "name": "Disorderly",
            "timestamp": 10,
            "tries": 2,
            "user_id": 456481297,
            "user_name": "Trifase"
        },
        {
            "day": f'{get_day_from_date(_date, _day, "Disorderly", datetime.date.today())}',
            "name": "Disorderly",
            "timestamp": 10,
            "tries": 3,
            "user_id": 456481297,
            "user_name": "Trifase"
        },
        {
            "day": f'{get_day_from_date(_date, _day, "Disorderly", datetime.date.today())}',
            "name": "Disorderly",
            "timestamp": 10,
            "tries": 9,
            "user_id": 456481297,
            "user_name": "Trifase"
        },

    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["I just played Disorderly!", "https://playdisorderly.com/"]
        _can_handle_this = all(c in raw_text for c in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        # Disorderly doesn't have a day - we assume today
        self.day = get_day_from_date(self._date, self._day, "Disorderly", datetime.date.today())
        last_line = text.split('\n')[-1]

        self.tries = last_line.count("🟢") + last_line.count("🔴")


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
        "DOMINO FIT #329 6x6 \n🏅🧙\u200d♂️⬜⬜\n⌚0️⃣1️⃣3️⃣",
        "DOMINO FIT #329 6x6 \n🏅✅✅⬜️\n⌚️0️⃣2️⃣2️⃣",
    ]
    expected = [
        {"day": "42", "name": "DominoFit", "timestamp": 10, "tries": 45, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "47", "name": "DominoFit", "timestamp": 10, "tries": 23, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "329", "name": "DominoFit", "timestamp": 10, "tries": 213, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "329", "name": "DominoFit", "timestamp": 10, "tries": 122, "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["DOMINO FIT #"]
        _can_handle_this = all(c in raw_text for c in wordlist) and '7x7' not in raw_text and '8x8' not in raw_text
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        # Extract day number using regex
        day_match = re.search(r"DOMINO FIT #(\d+)", text)
        self.day = day_match.group(1) if day_match else None

        # Extract time using emoji pattern
        time_pattern = re.search(r"⌚[]]?([0-9️⃣]+)", text)
        if time_pattern:
            time_str = time_pattern.group(1)
            str_points = time_from_emoji(time_str.strip())
            self.tries = int(str_points.strip())

            # Count white squares for penalties
            white_squares = text.count("⬜")
            if white_squares:
                self.tries += 100 * white_squares
                self.win_message = (
                    f"Ok, però guarda che hai saltato dei livelli e avrai {white_squares} {'minuto' if white_squares == 1 else 'minuti'} di penalità!"
                )

        self.stars = None


@dataclass
class Flagle(Giochino):
    _name = "Flagle"
    _category = "Geografia e Mappe"
    _date = datetime.date(2023, 9, 8)
    _day = "564"
    _emoji = "🏁"
    _url = "https://www.flagle.io"

    has_extra = True

    examples = [
        "#Flagle #777 (08.04.2024) 1/6\n🟩🟩🟩\n🟩🟩🟩\nhttps://www.flagle.io",
        "#Flagle #773 (04.04.2024) 5/6\n🟥🟩🟥\n🟩🟥🟥\nhttps://www.flagle.io",
        "#Flagle #773 (04.04.2024) X/6\n🟥🟥🟥\n🟥🟥🟥\nhttps://www.flagle.io",
        "#Flagle #1049 (05.01.2025) 4/6\n🟩🟩🟥\n🟥🟥🟩\n🗺🛡⛳️🧭👫\nhttps://www.flagle.io",
        "#Flagle #1043 (30.12.2024) 4/6\n🟩🟥🟥\n🟩🟥🟩\n🗺🛡🧭\nhttps://www.flagle.io",
        "#Flagle #1049 (05.01.2025) 4/6\n🟩🟩🟥\n🟥🟥🟩\n🗺🛡⛳️🧭👫🪙\nhttps://www.flagle.io",
    ]
    expected = [
        {"day": "777", "name": "Flagle", "timestamp": 10, "tries": "1", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "773", "name": "Flagle", "timestamp": 10, "tries": "5", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "773", "name": "Flagle", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "1049", "name": "Flagle", "stars": 5, "timestamp": 10, "tries": "4", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "1043", "name": "Flagle", "stars": 3, "timestamp": 10, "tries": "4", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "1049", "name": "Flagle", "stars": 6, "timestamp": 10, "tries": "4", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["#Flagle", "https://www.flagle.io"]
        _can_handle_this = all(c in raw_text for c in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        # Extract day number using regex
        day_match = re.search(r"#Flagle #(\d+)", text)
        self.day = day_match.group(1) if day_match else None

        # Extract the tries count using regex
        tries_match = re.search(r"(\d+|X)/6", text)
        self.tries = tries_match.group(1) if tries_match else None

        # Count special symbols for stars
        bussola = text.count("🧭")
        population = text.count("👫")
        coin = text.count("🪙")
        mappa = text.count("🗺")
        scudo = text.count("🛡")
        golf = text.count("⛳")

        self.stars = bussola + population + coin + mappa + scudo + golf


@dataclass
class Flags(Giochino):
    _name = "Flags"
    _category = "Geografia e Mappe"
    _date = datetime.date(2025, 7, 28)
    _day = "8"
    _emoji = "🏳️‍🌈"
    _url = "https://flagsgame.net"

    examples = [
        'Flag #4\n🟥 🟩 ⬛️ ⬛️ ⬛️ ⬛️\nhttps://flagsgame.net',
        'Flag #8\n🟥 🟥 🟥 🟥 🟥 🟥\nhttps://flagsgame.net',
    ]
    expected = [
        {"day": "4", "name": "Flags", "timestamp": 10, "tries": "2", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "8", "name": "Flags", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["Flag", "https://flagsgame.net"]
        _can_handle_this = all(c in raw_text for c in wordlist) and "one-frame" not in raw_text
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        # Extract day number using regex
        day_match = re.search(r"Flag #(\d+)", text)
        self.day = day_match.group(1) if day_match else None
        self.tries = 'X'
        for line in text.splitlines():
            if any(emoji in line for emoji in ["🟩", "🟥", "⬛"]):
                emoji_line = line.strip()

                green_index = emoji_line.find("🟩")
                if green_index != -1:
                    # Calculate position by counting squares before green
                    self.tries = str(emoji_line[:green_index].count("🟥") + emoji_line[:green_index].count("⬜") + 1)
                break



@dataclass
class FoodGuessr(Giochino):
    _name = "FoodGuessr"
    _category = "Geografia e Mappe"
    _date = datetime.date(2024, 3, 9)
    _day = "200"
    _emoji = "🍝"
    _url = "https://foodguessr.com"

    can_lose: False
    
    # examples = [
    #     "FoodGuessr - 09 Mar 2024 GMT\n  Round 1 🌕🌕🌕🌖\n  Round 2 🌕🌕🌕🌕\n  Round 3 🌕🌕🌗🌑\nTotal score: 12,500 / 15,000\n\nCan you beat my score? New game daily!\nPlay at https://foodguessr.com",
    # ]
    # expected = [{"day": "200", "name": "FoodGuessr", "stars": None, "timestamp": 10, "tries": 2500, "user_id": 456481297, "user_name": "Trifase"}]

    # @staticmethod
    # def can_handle_this(raw_text):
    #     wordlist = ["FoodGuessr", "Play at https://foodguessr.com"]
    #     _can_handle_this = all(c in raw_text for c in wordlist)
    #     return _can_handle_this

    # def parse(self):
    #     text = self.raw_text

    #     # Extract date with regex
    #     date_match = re.search(r"FoodGuessr - ([\d]+ [A-Za-z]+ [\d]{4})", text)
    #     if date_match:
    #         locale.setlocale(locale.LC_ALL, "en_US.UTF-8")
    #         actual_day = datetime.datetime.strptime(date_match.group(1).replace(" GMT", ""), "%d %b %Y").date()
    #         locale.setlocale(locale.LC_TIME, "it_IT.UTF-8")
    #         self.day = get_day_from_date(self._date, self._day, "FoodGuessr", actual_day)

    #     # Extract score with regex
    #     score_match = re.search(r"Total score: ([\d,\.]+)", text)
    #     if score_match:
    #         points = score_match.group(1).replace(",", "").replace(".", "")
    #         self.tries = 15_000 - int(points)

    #     self.stars = None

    examples = [
        "FoodGuessr - Wednesday, Aug 6, 2025 UTC\n🌕🌕🌕🌕 5000 ⋅ Round 1 💯\n🌕🌕🌕🌘 4000 ⋅ Round 2\n🌕🌕🌕🌖 4500 ⋅ Round 3\nTotal score: 13.500/15.000\n(+2094 above today's average!) 🎉\nPlay here: https://www.foodguessr.com/",
        "I got 13.500 on the FoodGuessr Daily!\n\nThat's 2094 points above today's average! 🎉\n\n🌕🌕🌕🌕 5000 (Round 1) 💯\n🌕🌕🌕🌘 4000 (Round 2)\n🌕🌕🌕🌖 4500 (Round 3)\n\nWednesday, Aug 6, 2025\nPlay here: https://www.foodguessr.com/",
        "I got 15,000 on the FoodGuessr Daily!\n\nThat's 3,595 points above today's average! 🎉\n\n🌕🌕🌕🌕 5,000 (Round 1) 💯\n🌕🌕🌕🌕 5,000 (Round 2) 💯\n🌕🌕🌕🌕 5,000 (Round 3) 💯\n\nWednesday, Aug 6, 2025\nPlay here: https://www.foodguessr.com/"
    ]
    expected = [
        {"day": "715", "name": "FoodGuessr", "timestamp": 10, "tries": 1500, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "715", "name": "FoodGuessr", "timestamp": 10, "tries": 1500, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "715", "name": "FoodGuessr", "timestamp": 10, "tries": 0, "user_id": 456481297, "user_name": "Trifase"}
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["FoodGuessr", "Play here: https://www.foodguessr.com/"]
        _can_handle_this = all(c in raw_text for c in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        # Extract date from the various formats
        date_match = re.search(r"FoodGuessr - [\w\s]+, (\w+ \d+, \d{4})|([\w\s]+, (\w+ \d+, \d{4}))", text)
        if date_match:
            date_str = date_match.group(1) or date_match.group(3)
            # print(f'date_str: "{date_str}"')
            locale.setlocale(locale.LC_ALL, "en_US.UTF-8")
            actual_day = datetime.datetime.strptime(date_str.strip(), "%b %d, %Y").date()
            locale.setlocale(locale.LC_TIME, "it_IT.UTF-8")
            self.day = get_day_from_date(self._date, self._day, "FoodGuessr", actual_day)

        # Extract score from the various formats and clean it
        score_match = re.search(r"(\d+[.,]?\d+)\/15\.000|I got (\d+[,.]?\d+) on the FoodGuessr", text)
        if score_match:
            points_str = score_match.group(1) or score_match.group(2)
            # Normalize points string by removing thousands separators
            points_str = points_str.replace(",", "").replace(".", "")
            points = int(points_str)
            self.tries = 15_000 - int(points)

        self.stars = None


@dataclass
class Framed(Giochino):
    _name = "Framed"
    _category = "Cinema e Serie TV"
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
        wordlist = ["Framed", "https://framed.wtf"]
        _can_handle_this = all(c in raw_text for c in wordlist) and "one-frame" not in raw_text and "titleshot" not in raw_text
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        # Extract day number using regex
        day_match = re.search(r"Framed #(\d+)", text)
        self.day = day_match.group(1) if day_match else None

        # Find the emoji line containing the results
        emoji_line = re.search(r"🎥\s+([🟥🟩⬛\s]+)", text)
        if emoji_line:
            # Remove spaces and get the results string
            punteggio = emoji_line.group(1).replace(" ", "")
            if "🟩" not in punteggio:
                self.tries = "X"
            else:
                # Find the position of the first green square
                self.tries = str(punteggio.index("🟩") + 1)


@dataclass
class Flickle(Giochino):
    _name = "Flickle"
    _category = "Cinema e Serie TV"
    _date = datetime.date(2025, 3, 14)
    _day = "1067"
    _emoji = "🎬"
    _url = "https://flickle.app"

    can_lose: True

    examples = [
        "#Flickle #1067\n\n    🎬⬛️⬛️⬛️🟩⬜️⬜️\n\n    📆 Daily Streak: 1 (Best 1)\n    🏆 Win Streak: 1 (Best 1)\n\n    https://flickle.app/",
        "#Flickle #1067\n\n    🎬⬛️⬛️⬛️⬛️⬛️⬛️❌\n\n    📆 Daily Streak: 1 (Best 1)\n    💀 Loss Streak: 1 (Worst 1)\n\n    https://flickle.app/",
        "#Flickle #1066\n\n🎬🟥🟥🟥⬛⬛⬛❌\n\n📆 Daily Streak: 1 (Best 1)\n💀 Loss Streak: 1 (Worst 1)\n\nhttps://flickle.app/",
        '#Flickle #1074\n\n🎬⬛️⬛️⬛️⬛️⬛️🟩\n\n📆 Daily Streak: 2 (Best 2)\n🏆 Win Streak: 1 (Best 1)\n\nhttps://flickle.app/',
    ]
    expected = [
        {"day": "1067", "name": "Flickle", "timestamp": 10, "tries": "4", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "1067", "name": "Flickle", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "1066", "name": "Flickle", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "1074", "name": "Flickle", "timestamp": 10, "tries": "6", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["#Flickle", "https://flickle.app"]
        _can_handle_this = all(c in raw_text for c in wordlist) and "one-frame" not in raw_text
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        # Extract day number using regex
        day_match = re.search(r"Flickle #(\d+)", text)
        self.day = day_match.group(1) if day_match else None

        # Find the emoji line containing the results
        emoji_line = re.search(r"🎬((?:[🟥🟩⬜️⬛️\s]+))", text)
        print(f"emoji_line: {emoji_line.group(1)}")
        if emoji_line:
            punteggio_bonificato = ""
            # Flickle uses black-magic squares that inject empty invisible spaces fugging up the count. We remove them with a whitelisted chars list.
            for char in emoji_line.group(1):
                if char in ["⬛", "🟥", "🟩", "⬜"]:
                    punteggio_bonificato += char
            print(f"punteggio: {punteggio_bonificato}")
            if "🟩" not in punteggio_bonificato or "❌" in text:
                self.tries = "X"
            else:
                # Find the position of the first green square
                self.tries = str(punteggio_bonificato.index("🟩") + 1)


@dataclass
class FramedOneFrame(Giochino):
    _name = "Framed One Frame"
    _category = "Cinema e Serie TV"
    _date = datetime.date(2024, 12, 11)
    _day = "9"
    _emoji = "🎞"
    _url = "https://framed.wtf/one-frame"

    examples = [
        "Framed - One Frame Challenge #9\n🎥 🟥 🟥 🟥 🟥 🟥 🟥\n\nhttps://framed.wtf/one-frame",
        "Framed - One Frame Challenge #9\n🎥 🟥 🟥 🟥 🟩 ⬛ ⬛\n\nhttps://framed.wtf/one-frame",
    ]
    expected = [
        {"day": "9", "name": "Framed One Frame", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "9", "name": "Framed One Frame", "timestamp": 10, "tries": "4", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["Framed", "https://framed.wtf/one-frame"]
        _can_handle_this = all(c in raw_text for c in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        # Extract day number using regex
        day_match = re.search(r"Challenge #(\d+)", text)
        self.day = day_match.group(1) if day_match else None

        # Find emoji pattern and evaluate results
        emoji_line = re.search(r"🎥\s+((?:[🟥🟩⬛\s]+))", text)
        if emoji_line:
            punteggio = emoji_line.group(1).replace(" ", "")
            if "🟩" not in punteggio:
                self.tries = "X"
            else:
                # Find position of first green square (1-indexed)
                green_index = punteggio.find("🟩")
                self.tries = str(green_index + 1) if green_index >= 0 else "X"


@dataclass
class Flipple(Giochino):
    _name = "Flipple"
    _category = "Giochi di parole"
    _date = datetime.date(2024, 9, 4)
    _day = "96"
    _emoji = "🔃"
    _url = "flipple.clevergoat.com"

    can_lose: False

    examples = [
        "Flipple #96 ⬇️\n🟩⬜️⬜️⬜️🟩\n🟩⬜️🟩⬜️🟩\n🟩⬜️🟩🟩🟩\n🟩🟩🟩🟩🟩\nflipple.clevergoat.com 🐐",
        "Flipple #194 ⬇️\n🟩🟩⬜⬜🟩\n🟩🟩⬜🟩🟩\n🟩🟩🟩🟩🟩\nflipple.clevergoat.com 🐐",
        "Flipple #196 ⬇️\n⬜⬜⬜🟩\n🟩⬜⬜🟩\n🟩⬜🟩🟩\n🟩🟩🟩🟩\nflipple.clevergoat.com 🐐",
        "Flipple 4 #196 ⬇️\n⬜⬜⬜🟩\n🟩⬜⬜🟩\n🟩⬜🟩🟩\n🟩🟩🟩🟩\nflipple.clevergoat.com 🐐",
    ]
    expected = [
        {"day": "96", "name": "Flipple", "timestamp": 10, "tries": "4", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "194", "name": "Flipple", "timestamp": 10, "tries": "3", "user_id": 456481297, "user_name": "Trifase"},
        None,
        None,
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["Flipple ", "flipple.clevergoat.com", "🟩🟩🟩🟩🟩"]
        _can_handle_this = all(c in raw_text for c in wordlist) and "Flipple 4" not in raw_text
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        # Extract day number using regex
        day_match = re.search(r"Flipple\s+(?:#|4\s+#)?(\d+)", text)
        self.day = day_match.group(1) if day_match else None

        # Count lines containing emoji squares (excluding header/footer lines)
        emoji_lines = [f for f in re.findall(r"[🟩⬜️]+", text, re.MULTILINE) if f != "️"]

        # The number of tries is the count of valid game rows
        if emoji_lines and len(emoji_lines) > 0:
            self.tries = str(len(emoji_lines))
        else:
            self.tries = None

        self.stars = None


@dataclass
class Geogrid(Giochino):
    _name = "Geogrid"
    _category = "Geografia e Mappe"
    _date = datetime.date(2024, 5, 21)
    _day = "45"
    _emoji = "🌎"
    _url = "https://geogridgame.com"

    can_lose: False

    examples = [
        # "✅ ✅ ✅\n✅ ✅ ✅\n✅ ✅ ✅\n\n🌎Game Summary🌎\nBoard #45\nScore: 112.3\nRank: 1,242 / 3,262\nhttps://geogridgame.com\n@geogridgame",
        # "❌ ✅ ✅\n✅ ❌ ❌\n❌ ❌ ❌\n\n🌎Game Summary🌎\nBoard #45\nScore: 629.3\nRank: 8,858 / 11,488\nhttps://geogridgame.com\n@geogridgame",
        # "❌ ❌ ❌\n❌ ❌ ❌\n❌ ❌ ❌\n\n🌎Game Summary🌎\nBoard #45\nScore: 900\nRank: 9,082 / 11,501\nhttps://geogridgame.com\n@geogridgame",
        '🟩🟩🟩\n🟩🟩🟩\n🟩🟩🟩\nScore: 80.7 | Rank: 882/5,869\nTop Brass 🎺 | ★★★★\nI scored better than 85% of #geogridgame players!\nBoard #524 | ♾️ Mode: Off\nhttps://geogridgame.com',
        '🟩❌❌\n🟩❌❌\n❌❌❌\nScore: 722.2 | Rank: 4,718/4,882\nElite Among Mortals 🎖\nOrdinary among #geogridgame savants, extraordinary among mere mortals.\nBoard #447 | ♾️ Mode: Off\nhttps://geogridgame.com',
        '🟩🟩🟩\n❌🟩🟩\n🟩❌❌\nScore: 399.7 | Rank: 2.124/2.949\nElite Among Mortals 🎖\nOrdinary among #geogridgame savants, extraordinary among mere mortals.\nBoard #475 | ♾️ Mode: Off\nhttps://geogridgame.com'
    ]
    expected = [
        {"day": "524", "name": "Geogrid", "timestamp": 10, "tries": "80", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "447", "name": "Geogrid", "timestamp": 10, "tries": "722", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "475", "name": "Geogrid", "timestamp": 10, "tries": "399", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["https://geogridgame.com", "#geogridgame"]
        _can_handle_this = all(c in raw_text for c in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        # Use regex to extract day number from anywhere in text
        day_match = re.search(r"Board #(\d+)", text)
        self.day = day_match.group(1) if day_match else None

        # Use regex to extract score
        score_match = re.search(r"Score: ([0-9.,]+)", text)
        if score_match:
            # Convert to integer by removing decimal and thousands separators
            score = int(float(score_match.group(1)))
            self.tries = "X" if score == 900 else str(score)

        self.stars = None


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
        wordlist = ["#globle", "https://globle-game.com"]
        _can_handle_this = all(c in raw_text for c in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        # Extract date from first line for day calculation
        date_match = re.search(r"🌎\s+([A-Za-z]+\s+\d+,\s+\d{4})", text)
        if date_match:
            date_str = date_match.group(1)
            self.day = get_day_from_date(self._date, self._day, "Globle", date_str)

        # Find score using regex pattern for "= N" format
        tries_match = re.search(r"=\s*(\d+)", text)
        if tries_match:
            self.tries = tries_match.group(1)

        self.stars = None


@dataclass
class GuessTheAngle(Giochino):
    _name = "GuessTheAngle"
    _category = "Logica"
    _date = datetime.date(2025, 7, 31)
    _day = "173"
    _emoji = "📐"
    _url = "https://guesstheangle.wtf"

    examples = [
        "#GuessTheAngle #173\n\n📐 🟥 🟥 🟩 ⬜️\n\n#AngleAmateur\nhttps://GuessTheAngle.wtf/p/173",
        "#GuessTheAngle #173\n\n📐 🟥 🟥 🟥 🟥\n\n#AngleAmateur\nhttps://GuessTheAngle.wtf/p/173",
    ]
    expected = [
        {"day": "173", "name": "GuessTheAngle", "timestamp": 10, "tries": "3", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "173", "name": "GuessTheAngle", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["#GuessTheAngle", "https://GuessTheAngle.wtf/p"]
        _can_handle_this = all(w in raw_text for w in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        day_match = re.search(r"#GuessTheAngle #(\d+)", text)
        self.day = day_match.group(1) if day_match else None
        
        emoji_line = re.search(r"📐\s*([\s🟥🟩⬜️]+)", text)
        if emoji_line:
            punteggio = emoji_line.group(1).replace(" ", "")

            if "🟩" not in punteggio:
                self.tries = "X"
            else:
                self.tries = str(punteggio.index("🟩") + 1)
        
        self.stars = None

@dataclass
class GuessTheFootballClub(Giochino):
    _name = "GuessTheFootballClub"
    _category = "Immagini, giochi e musica"
    _date = datetime.date(2025, 4, 17)
    _day = "80"
    _emoji = "🛡️"
    _url = "https://playfootball.games/guess-the-football-club/"

    examples = [
        "'#GuessTheFootballClub 80 X/6\n\n🛡️🟢⬆️⬇️⚪⚪\n🛡️🟢⬇️⬇️⚪⚪\n🛡️⚪⬆️⬇️⚪⚪\n🛡️🟢⬇️⬇️⚪⚪\n🛡️🟢⬆️⬇️⚪⚪\n🛡️🟢⬆️⬇️⚪⚪\n\n#PlayFootballGames\n\nhttps://playfootball.games/guess-the-football-club/'",
        "'#GuessTheFootballClub 78 3/6\n\n🛡️⚪⬆️⬇️⚪⚪\n🛡️⚪⬆️⬇️⚪⚪\n🎉🟢🟢🟢🟢🟢\n\n#PlayFootballGames\n https://playfootball.games/guess-the-football-club/'",
    ]
    expected = [
        {"day": "80", "name": "GuessTheFootballClub", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "78", "name": "GuessTheFootballClub", "timestamp": 10, "tries": "3", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["#GuessTheFootballClub", "#PlayFootballGames", "https://playfootball.games/guess-the-football-club/"]
        _can_handle_this = all(w in raw_text for w in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        match = re.search(r"#GuessTheFootballClub (\d+) (\d+|X)/6", text)
        self.day = match.group(1) if match else None
        self.tries = match.group(2) if match else None


@dataclass
class GuessTheGame(Giochino):
    _name = "GuessTheGame"
    _category = "Immagini, giochi e musica"
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
        wordlist = ["#GuessTheGame", "https://GuessThe.Game/p"]
        _can_handle_this = all(w in raw_text for w in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        day_match = re.search(r"#GuessTheGame #(\d+)", text)
        self.day = day_match.group(1) if day_match else None

        # Find emoji pattern and evaluate results
        emoji_line = re.search(r"🎮\s+((?:[🟥🟩🟨⬜\s]+))", text)
        if emoji_line:
            punteggio = emoji_line.group(1).replace(" ", "")
            if "🟩" not in punteggio:
                self.tries = "X"
            else:
                # Find position of first green square (1-indexed)
                green_index = punteggio.find("🟩")
                self.tries = str(green_index + 1) if green_index >= 0 else "X"


@dataclass
class GuessTheHouse(Giochino):
    _name = "GuessTheHouse"
    _category = "Logica"
    _date = datetime.date(2025, 7, 31)
    _day = "310"
    _emoji = "🏠"
    _url = "https://guessthe.house"

    examples = [
        "#GuessTheHouse #310\n🏠 🟥 🟥 🟥 🟥 🟩 ⬜️\n#HomeHobbyist\nhttps://GuessThe.House/p/310",
        "#GuessTheHouse #310\n🏠 🟥 🟥 🟥 🟥 🟥 🟩\n#HomeHobbyist\nhttps://GuessThe.House/p/310",
    ]
    expected = [
        {"day": "310", "name": "GuessTheHouse", "timestamp": 10, "tries": "5", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "310", "name": "GuessTheHouse", "timestamp": 10, "tries": "6", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["#GuessTheHouse", "https://GuessThe.House/p"]
        _can_handle_this = all(w in raw_text for w in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        day_match = re.search(r"#GuessTheHouse #(\d+)", text)
        self.day = day_match.group(1) if day_match else None
        
        # Fi    nd the line with the house emoji and the result squares
        emoji_line = re.search(r"🏠\s*([\s🟥🟩⬜️]+)", text)
        if emoji_line:
            punteggio = emoji_line.group(1).replace(" ", "")

            # If there's no green emoji, the user lost
            if "🟩" not in punteggio:
                self.tries = "X"
            else:
                # The number of tries is the position of the green square
                self.tries = str(punteggio.index("🟩") + 1)
        
        self.stars = None


@dataclass
class GuessTheLogo(Giochino):
    _name = "GuessTheLogo"
    _category = "Immagini, giochi e musica"
    _date = datetime.date(2025, 7, 31)
    _day = "318"
    _emoji = "®"
    _url = "https://guessthelogo.wtf"

    examples = [
        "#GuessTheLogo #318\n\n® 🟥 🟥 🟥 🟥 🟥\n\n#LogoLearner\nhttps://GuessTheLogo.wtf/p/318",
        "#GuessTheLogo #318\n\n® 🟥 🟩 ⬜️ ⬜️\n\n#LogoLearner\nhttps://GuessTheLogo.wtf/p/318",
    ]
    expected = [
        {"day": "318", "name": "GuessTheLogo", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "318", "name": "GuessTheLogo", "timestamp": 10, "tries": "2", "user_id": 456481297, "user_name": "Trifase"},
    ]
    
    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["#GuessTheLogo", "https://GuessTheLogo.wtf/p"]
        _can_handle_this = all(w in raw_text for w in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        day_match = re.search(r"#GuessTheLogo #(\d+)", text)
        self.day = day_match.group(1) if day_match else None
        
        emoji_line = re.search(r"®\s*([\s🟥🟩⬜️]+)", text)
        if emoji_line:
            punteggio = emoji_line.group(1).replace(" ", "")

            if "🟩" not in punteggio:
                self.tries = "X"
            else:
                self.tries = str(punteggio.index("🟩") + 1)
        
        self.stars = None


@dataclass
class GuessTheMovie(Giochino):
    _name = "GuessTheMovie"
    _category = "Cinema e Serie TV"
    _date = datetime.date(2025, 3, 29)
    _day = "178"
    _emoji = "📽"
    _url = "https://GuessTheMovie.Name"

    examples = [
        '#GuessTheMovie #178\n\n🎥 🟩 ⬜ ⬜ ⬜ ⬜ ⬜\n\n#RookieReeler\nhttps://GuessTheMovie.Name/p/178',
        '#GuessTheMovie #178\n\n🎥 🟥 🟥 🟥 🟥 🟥 🟥\n\n#RookieReeler\nhttps://GuessTheMovie.Name/p/178',
    ]
    expected = [
        {"day": "178", "name": "GuessTheMovie", "timestamp": 10, "tries": "1", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "178", "name": "GuessTheMovie", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["#GuessTheMovie", "https://GuessTheMovie.Name/p"]
        _can_handle_this = all(w in raw_text for w in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        day_match = re.search(r"#GuessTheMovie #(\d+)", text)
        self.day = day_match.group(1) if day_match else None

        # Find emoji pattern and evaluate results
        emoji_line = re.search(r"🎥\s+((?:[🟥🟩🟨⬜\s]+))", text)
        if emoji_line:
            punteggio = emoji_line.group(1).replace(" ", "")
            if "🟩" not in punteggio:
                self.tries = "X"
            else:
                # Find position of first green square (1-indexed)
                green_index = punteggio.find("🟩")
                self.tries = str(green_index + 1) if green_index >= 0 else "X"


@dataclass
class Heardle(Giochino):
    _name = "Heardle"
    _category = "Immagini, giochi e musica"
    _date = datetime.date(2025, 6, 19)
    _day = "100"
    _emoji = "🔊"
    _url = "https://heardle.it"

    can_lose: True

    examples = [
        '🔊🟩⬜️⬜️⬜️⬜️⬜️\n#HeardleItalia 19/06/2025\n\nhttps://heardle.it',
        '🔇🟥🟥🟥🟥🟥🟥 \n #HeardleItalia 26/06/2025 \n \n https://heardle.it',
    ]
    expected = [
        {"day": "100", "name": "Heardle", "timestamp": 10, "tries": "1", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "107", "name": "Heardle", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["#HeardleItalia", "https://heardle.it"]
        _can_handle_this = all(w in raw_text for w in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        # Extract day from the URL in the last line - search for dd/mm/yyyy
        date_match = re.search(r" (\d+/\d+/\d+)", text)
        if date_match:
            date_str = date_match.group(1)
            self.day = get_day_from_date(self._date, self._day, "Heardle", date_str)

        self.tries = "X"
        self.stars = None
        # Find emoji pattern and evaluate results
        emoji_line = None
        lines = text.strip().split("\n")
        # Cerca la linea che contiene gli emoji dei quadrati
        for line in lines:
            if any(emoji in line for emoji in ["🟩", "🟥", "⬜"]):
                emoji_line = line.strip()

                green_index = emoji_line.find("🟩")
                if green_index != -1:
                    # Calculate position by counting squares before green
                    self.tries = str(emoji_line[:green_index].count("🟥") + emoji_line[:green_index].count("⬜") + 1)
                break


@dataclass
class Hexcodle(Giochino):
    _name = "Hexcodle"
    _category = "Immagini, giochi e musica"
    _date = datetime.date(2025, 4, 17)
    _day = "616"
    _emoji = "🎨"
    _url = "https://hexcodle.com"

    examples = [
        "I didn't get Hexcodle #616 :( Score: 48%\n\n⏫⏬✅🔼⏬⏫\n🔼⏬🔽✅⏬⏫\n🔼⏬🔽🔽⏬⏫\n✅⏬⏬🔽⏬🔼\n🔽⏬⏬⏬⏬🔼\n\nhttps://hexcodle.com",
        'I got Hexcodle #616 in 5! Score: 52%\n\n⏫🔽⏫⏫⏬🔼\n✅✅⏬🔽⏬🔼\n✅✅⏫✅🔽✅\n✅✅✅✅🔽✅\n✅✅✅✅✅✅\n\nhttps://hexcodle.com',
        'I got Hexcodle #616 in 4! Score: 68%\n\n⏫🔽⏫⏫⏬⏫\n⏫✅✅🔼🔽⏫\n✅✅✅🔽✅🔼\n✅✅✅✅✅✅\n\nhttps://hexcodle.com'
    ]

    expected = [
        {"day": "616", "name": "Hexcodle", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "616", "name": "Hexcodle", "timestamp": 10, "tries": "5", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "616", "name": "Hexcodle", "timestamp": 10, "tries": "4", "user_id": 456481297, "user_name": "Trifase"},
        ]

    can_lose: True

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["Hexcodle #", "https://hexcodle.com"]
        _can_handle_this = all(c in raw_text for c in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text
        if "✅✅✅✅✅✅" not in text:
            self.tries = "X"
        else:
            match_points = re.search(r"(\d)!", text)
            self.tries = match_points.group(1) if match_points else None

        match_day = re.search(r"#(\d+)", text)
        self.day = match_day.group(1) if match_day else None
        self.stars = None


# @dataclass
# class HighFive(Giochino):
#     _name = "HighFive"
#     _category = "Giochi di parole"
#     _date = datetime.date(2023, 6, 23)
#     _day = "100"
#     _emoji = "🖐️"
#     _url = "https://highfivegame.app"

#     examples = ["🖐 I scored 27 points on today's HighFive! Can you beat me?\n\n🟠🟠\n🟢🟢🟢🟢\n🔵\n🟣🟣🟣🟣🟣\n\nhttps://highfivegame.app/2024-02-28"]
#     expected = [{"day": "350", "name": "HighFive", "timestamp": 10, "tries": "-27", "user_id": 456481297, "user_name": "Trifase"}]

#     can_lose: False

#     @staticmethod
#     def can_handle_this(raw_text):
#         wordlist = ["HighFive! ", "https://highfivegame.app"]
#         _can_handle_this = all(c in raw_text for c in wordlist)
#         return _can_handle_this

#     def parse(self):
#         text = self.raw_text

#         # Extract day from the URL in the last line
#         url_match = re.search(r"(\d{4}-\d{2}-\d{2})", text)
#         if url_match:
#             date_str = url_match.group(1)
#             self.day = get_day_from_date(self._date, self._day, "HighFive", date_str)

#         # Extract score from first line with regex
#         score_match = re.search(r"I scored (\d+) points", text)
#         if score_match:
#             score = int(score_match.group(1))
#             # Store as negative since that's the format used in the system
#             self.tries = str(0 - score)

#         self.stars = None


@dataclass
class Lyricle(Giochino):
    _name = "Lyricle"
    _category = "Immagini, giochi e musica"
    _date = datetime.date(2025, 3, 12)
    _day = "1053"
    _emoji = "📜"
    _url = "https://lyricle.app"

    examples = [
        "#Lyricle #1052\n\n⬛️⬛️⬛️⬛️⬛️⬛️\n\nGuess the song by lyrics in this fun, daily challenge!\n\nhttps://lyricle.app",
        "#Lyricle #1051\n\n🟩⬛⬛⬛⬛⬛\n\nGuess the song by lyrics in this fun, daily challenge!\n\nhttps://lyricle.app",
        '#Lyricle #1072\n\n⬛️🟩⬛️⬛️⬛️⬛️\n\nGuess the song by lyrics in this fun, daily challenge!\n\nhttps://lyricle.app',
        '#Lyricle #1201\n\n🟨🟩⬛️⬛️⬛️⬛️\n\nGuess the song by lyrics in this fun, daily challenge!\n\nhttps://lyricle.app',
    ]
    expected = [
        {"day": "1052", "name": "Lyricle", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "1051", "name": "Lyricle", "timestamp": 10, "tries": "1", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "1072", "name": "Lyricle", "timestamp": 10, "tries": "2", "user_id": 456481297, "user_name": "Trifase"},
        {'day': '1201', 'name': 'Lyricle', 'timestamp': 10, 'tries': '2', 'user_id': 456481297, 'user_name': 'Trifase'},

    ]

    can_lose: True

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["#Lyricle", "https://lyricle.app"]
        _can_handle_this = all(c in raw_text for c in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        day_match = re.search(r"#Lyricle #(\d+)", text)
        self.day = day_match.group(1) if day_match else None
        self.tries = "X"
        self.stars = None

        emoji_line = None
        lines = text.strip().split("\n")
        # Cerca la linea che contiene gli emoji dei quadrati
        for line in lines:
            if any(emoji in line for emoji in ["⬛", "🟩", "🟨", "⬜", "🟥"]):
                emoji_line = line.strip()

                green_index = emoji_line.find("🟩")
                if green_index != -1:
                    # Calculate position by counting squares before green
                    self.tries = str(emoji_line[:green_index].count("⬛") + emoji_line[:green_index].count("🟥") + emoji_line[:green_index].count("🟨") + emoji_line[:green_index].count("⬜") + 1)
                break


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
        wordlist = ["Plant ", "#metaflora"]
        _can_handle_this = all(c in raw_text for c in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        # Extract day number using regex
        day_match = re.search(r"Plant #(\d+)", text)
        self.day = day_match.group(1) if day_match else None

        # Check if the user was stumped or successful
        if re.search(r"I was stumped", text):
            self.tries = "X"
        else:
            # Extract number of guesses
            tries_match = re.search(r"in (\d+) guesses", text)
            self.tries = tries_match.group(1) if tries_match else None

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
        wordlist = ["Animal ", "#metazooa"]
        _can_handle_this = all(c in raw_text for c in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        # Extract day number using regex
        day_match = re.search(r"Animal #(\d+)", text)
        self.day = day_match.group(1) if day_match else None

        # Check if the user was stumped or successful
        if re.search(r"I was stumped", text):
            self.tries = "X"
        else:
            # Extract number of guesses using regex
            tries_match = re.search(r"in (\d+) guesses?!", text)
            self.tries = tries_match.group(1) if tries_match else None

        self.stars = None


@dataclass
class Moviedle(Giochino):
    _name = "Moviedle"
    _category = "Cinema e Serie TV"
    _date = datetime.date(2023, 6, 23)
    _day = "200"
    _emoji = "🎥"
    _url = "https://likewise.com/games/moviedle"

    examples = [
        "#Moviedle #2024-03-08 \n\n 🎥 ⬛️ ⬛️ ⬛️ ⬛️ ⬛️ ⬛️  \n https://likewise.com/games/moviedle/2024-03-08",
        "#Moviedle #2024-01-29 \n\n 🎥 🟥 🟥 ⬛️ ⬛️ ⬛️ ⬛️  \n https://likewise.com/games/moviedle/2024-01-29",
        "#Moviedle #2024-03-07 \n\n 🎥 🟩 ⬜️ ⬜️ ⬜️ ⬜️ ⬜️  \n https://likewise.com/games/moviedle/2024-03-07",
        "#Moviedle #2024-01-21 \n\n 🎥 ⬛️ ⬛️ 🟩 ⬜️ ⬜️ ⬜️  \n https://likewise.com/games/moviedle/2024-01-21",
        "#Moviedle #2025-03-04 \n\n 🎥 ⬛️ ⬛️ ⬛️ ⬛️ ⬛️ ⬛️  \n https://likewise.com/games/moviedle/2025-03-04",
    ]
    expected = [
        {"day": "459", "name": "Moviedle", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "420", "name": "Moviedle", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "458", "name": "Moviedle", "timestamp": 10, "tries": "1", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "412", "name": "Moviedle", "timestamp": 10, "tries": "3", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "820", "name": "Moviedle", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["#Moviedle ", "https://likewise.com/games/moviedle"]
        _can_handle_this = all(c in raw_text for c in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        date_str = re.search(r"#Moviedle (#\d{4}-\d{2}-\d{2})", text).group(1)
        self.day = get_day_from_date(self._date, self._day, "Moviedle", date_str)

        # Find emoji pattern and evaluate results
        emoji_line = re.search(r"🎥\s+((?:[🟥🟩⬜️⬛️\s]+))", text)
        if emoji_line:
            punteggio = emoji_line.group(1).replace(" ", "")

            punteggio_bonificato = ""
            # Moviedle uses black-magic squares that inject empty invisible spaces fugging up the count. We remove them with a whitelisted chars list.
            for char in punteggio:
                if char in ["⬛", "🟥", "🟩", "⬜"]:
                    punteggio_bonificato += char

            if "🟩" not in punteggio_bonificato:
                self.tries = "X"
            else:
                # Find position of first green square (1-indexed)
                green_index = punteggio_bonificato.find("🟩")
                self.tries = str(green_index + 1) if green_index >= 0 else "X"


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
        wordlist = ["Murdle for", "https://murdle.com"]
        _can_handle_this = all(c in raw_text for c in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        date_match = re.search(r"Murdle for (\d+/\d+/\d+)", text)
        if date_match:
            date_str = date_match.group(1)
            # Murdle doesn't have a #day, so we parse the date and get our own numeration (Jun 23, 2023 -> 200)
            self.day = get_day_from_date(self._date, self._day, "Murdle", date_str)

        punteggio = re.search(r"(.\ufe0f.:.\ufe0f..\ufe0f.)", text).group(1)
        if "❌" in text:
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
        wordlist = ["nerdlegame ", "/6"]
        _can_handle_this = all(c in raw_text for c in wordlist) and 'cross nerdle' not in raw_text
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        match = re.search(r"nerdlegame\s+(\d+)\s+(\d+|X)/\d+", text)
        if match:
            self.day = match.group(1)
            self.tries = match.group(2)
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
        'cross nerdle #665\n⬛🔲🔲🔲🔲🔲🟩🟩🔲🟩\n🔲⬛⬛🟩⬛⬛⬛🟩⬛🟩\n🟩🟩🔲🟩🟩🟩🟩🟩⬛🟩\n🟩⬛⬛🟩⬛⬛🔲⬛⬛🟩\n🔲🟩🟩🟩🔲⬛🟩⬛⬛🔲\n🔲⬛⬛🔲⬛🔲🟩🔲🔲🟩\n🟩⬛⬛🟩⬛⬛🟩⬛⬛🟩\n🟩⬛🟩🔲🔲🔲🔲🟩🔲🟩\n🔲⬛🟩⬛⬛⬛🟩⬛⬛🔲\n🟩🟩🟩🔲🔲🔲🔲🟩🟩⬛\nPerfect solve - no 🎁 or 👀.\n@nerdlegame points: 6/6',
    ]
    expected = [
        {"day": "198", "name": "NerdleCross", "timestamp": 10, "tries": 0, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "201", "name": "NerdleCross", "timestamp": 10, "tries": 2, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "198", "name": "NerdleCross", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "665", "name": "NerdleCross", "timestamp": 10, "tries": 0, "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["cross nerdle #", "@nerdlegame"]
        _can_handle_this = all(c in raw_text for c in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        # Extract day number using regex
        day_match = re.search(r"cross nerdle #(\d+)", text, re.IGNORECASE)
        self.day = day_match.group(1) if day_match else None

        points_match = re.search(r"points:\s?(\d+)\/6", text, re.IGNORECASE)
        if points_match:
            points = int(points_match.group(1))
            # Convert score: NerdleCross uses positive points from 0 to 6
            # We interpret 6 as failure, and otherwise use 6 - points
            self.tries = 6 - points
            if self.tries == 6:
                self.tries = "X"


@dataclass
class NFLXdle(Giochino):
    _name = "NFLXdle"
    _category = "Cinema e Serie TV"
    _date = datetime.date(2024, 9, 4)
    _day = "100"
    _emoji = "📺"
    _url = "https://likewise.com/games/nflxdle"

    has_extra = True

    examples = [
        "#NFLXdle #2024-09-04 \n\n ⌛️ 3️⃣ seconds \n 📺 🟩 ⬜️ ⬜️ ⬜️ ⬜️ ⬜️  \n https://likewise.com/games/nflxdle/2024-09-04",  # vinta
        "#NFLXdle #2024-09-04 \n\n ⌛️ 6️⃣ seconds \n 📺 🟥 🟥 🟩 ⬜️ ⬜️ ⬜️  \n https://likewise.com/games/nflxdle/2024-09-04",  # vinta
        "#NFLXdle #2024-09-04 \n\n ⌛️ 2️⃣1️⃣ seconds \n 📺 ⬜️ ⬜️ ⬜️ ⬜️ ⬜️ ⬜️  \n https://likewise.com/games/nflxdle/2024-09-04",  # persa (tempo)
        "#NFLXdle #2024-09-03 \n\n ⌛️ 6️⃣ seconds \n 📺 🟥 🟥 🟥 🟥 🟥 🟥  \n https://likewise.com/games/nflxdle/2024-09-03",  # persa (tentativi)
    ]
    expected = [
        {"day": "100", "name": "NFLXdle", "timestamp": 10, "tries": "3", "user_id": 456481297, "user_name": "Trifase", "stars": "5"},
        {"day": "100", "name": "NFLXdle", "timestamp": 10, "tries": "6", "user_id": 456481297, "user_name": "Trifase", "stars": "3"},
        {"day": "100", "name": "NFLXdle", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "99", "name": "NFLXdle", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["#NFLXdle", "https://likewise.com/games/nflxdle"]
        _can_handle_this = all(c in raw_text for c in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        date_str = re.search(r"#NFLXdle (#\d{4}-\d{2}-\d{2})", text).group(1)
        self.day = get_day_from_date(self._date, self._day, "NFLXdle", date_str)

        if "🟩" not in text:
            self.tries = "X"
        else:
            self.stars = str(text.count("⬜️"))
            time = re.search(r"((?:\S\ufe0f\S)+)", text).group(1)
            self.tries = time_from_emoji(time)


@dataclass
class Numble(Giochino):
    _name = "Numble"
    _category = "Logica"
    _date = datetime.date(2024, 5, 27)
    _day = "834"
    _emoji = "➗"
    _url = "https://numble.wtf"

    examples = [
        "Numble #832\nSOLVED: ❌\nNumbers used: 6/6\nFinal answer: 80\n32.652s\nhttps://numble.wtf",
        "Numble #832\nSOLVED: ✅\nNumbers used: 6/6\nFinal answer: 900\n50.538s\nhttps://numble.wtf",
        "Numble #834\nSOLVED: ✅\nNumbers used: 3/6\nFinal answer: 48\n1m 28.660s\nhttps://numble.wtf",
        'Numble #1134\nSOLVED: ✅\nNumbers used: 6/6\nFinal answer: 640\n2m .644s\nhttps://numble.wtf'
    ]
    expected = [
        {"day": "832", "name": "Numble", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "832", "name": "Numble", "timestamp": 10, "tries": "50", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "834", "name": "Numble", "timestamp": 10, "tries": "88", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "1134", "name": "Numble", "timestamp": 10, "tries": "120", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["Numble", "SOLVED:", "https://numble.wtf"]
        _can_handle_this = all(c in raw_text for c in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        day_match = re.search(r"Numble #(\d+)", text)
        self.day = day_match.group(1) if day_match else None

        solved = "✅" in text
        if not solved:
            self.tries = "X"
        else:
            time_match = re.search(r"(\d+m\s+)?((:?\d+)?\.\d+)s", text)
            # print('time match 0', time_match.group(0),'time match 1',time_match.group(1),'time match 2',time_match.group(2) )
            self.tries = str(self.duration(time_match.group(0)))
            numbers_match = re.search(r"Numbers used: (\d+)/(\d+)", text)
            if numbers_match:
                used = numbers_match.group(1)
                maximum = numbers_match.group(2)
                self.stars = str(int(maximum) - int(used))

    def duration(self, string):
        string = string.replace(" .", "0.")
        # print("string", string)

        mult = {"s": 1, "m": 60, "h": 60 * 60, "d": 60 * 60 * 24}
        parts = re.findall(r"(\d+(?:\.\d+)?)([smhd])", string)
        # print("parts", parts)
        total_seconds = sum(float(x) * mult[m] for x, m in parts)
        return int(total_seconds)


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
        wordlist = ["Par🇮🇹le", "/6"]
        _can_handle_this = all(c in raw_text for c in wordlist)
        return _can_handle_this

    def parse(self):
        matches = re.search(r"le (\d+) (\d|X)/6", self.raw_text)
        self.day = matches.group(1)
        self.tries = matches.group(2)


@dataclass
class Pedantle(Giochino):
    _name = "Pedantle"
    _category = "Giochi di parole"
    _date = datetime.date(2024, 9, 5)
    _day = "840"
    _emoji = "🌥️"
    _url = "https://pedantle.certitudes.org"

    can_lose: False

    examples = [
        "I found #pedantle #833 in 133 guesses!\n🟩🟩🟩🟩🟩🟩🟩🟩🟧🟧🟧🟧🟧🟧🟧🟥🟥🟥🟥🟥\nhttps://pedantle.certitudes.org/",
        "I found #pedantle #840 in 99 guesses!\n🟩🟩🟩🟩🟩🟩🟩🟧🟧🟧🟧🟧🟧🟧🟧🟥🟥🟥🟥🟥\nhttps://pedantle.certitudes.org/",
    ]
    expected = [
        {"day": "833", "name": "Pedantle", "timestamp": 10, "tries": "133", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "840", "name": "Pedantle", "timestamp": 10, "tries": "99", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["#pedantle", "https://pedantle.certitudes.org/"]
        _can_handle_this = all(w in raw_text for w in wordlist)
        return _can_handle_this

    def parse(self):
        matches = re.search(r"#pedantle #(\d+) in (\d+) guesses", self.raw_text)
        self.day = matches.group(1)
        self.tries = matches.group(2)


@dataclass
class Picsey(Giochino):
    _name = "Picsey"
    _category = "Immagini, giochi e musica"
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
        wordlist = ["Picsey", "🟦"]
        _can_handle_this = all(w in raw_text for w in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        day_match = re.search(r"Picsey (\d+\.\d+\.\d+)", text).group(1)
        self.day = get_day_from_date(self._date, self._day, "Picsey", day_match)

        point_match = re.search(r"(\d+)p", text).group(1)
        points = int(point_match)
        # Picsey uses positive poits, from 0 to 100. We as usual save 100-n and then revert it when printing the results.
        self.tries = 100 - points
        if points == 0:
            self.tries = "X"
        self.stars = None


@dataclass
class Pinpoint(Giochino):
    _name = "Pinpoint"
    _category = "Logica"
    _date = datetime.date(2024, 10, 17)
    _day = "170"
    _emoji = "📌"
    _url = "https://lnkd.in/pinpoint"

    can_lose: True

    examples = [
        "Pinpoint n. 159 | 3 risposte giuste\n1️⃣ | 0% di corrispondenza \n2️⃣ | 3% di corrispondenza \n3️⃣ | 100% di corrispondenza  📌\nlnkd.in/pinpoint.",
        "Pinpoint #167 | 2 tentativi\n1️⃣ | Corrispondenza: 18%\n2️⃣ | Corrispondenza: 100% 📌\nlnkd.in/pinpoint.",
        "Pinpoint #169\n📌 ⬜ ⬜ ⬜ ⬜ (1/5)\nlnkd.in/pinpoint.",
        "Pinpoint #169\n🤔 📌 ⬜ ⬜ ⬜ (2/5)\nlnkd.in/pinpoint.",
        "Pinpoint #169\n🤔 🤔 🤔 🤔 📌 (5/5)\nlnkd.in/pinpoint.",
        "Pinpoint #169\n🤔 🤔 🤔 🤔 🤔 (X/5)\nlnkd.in/pinpoint.",
        "Pinpoint #170 | 3 guesses\n1️⃣  | 64% match\n2️⃣  | 78% match\n3️⃣  | 100% match 📌\nlnkd.in/pinpoint.",
        "Pinpoint #181 | 1 guess\n1️⃣  | 100% match 📌\nlnkd.in/pinpoint.",
        "Pinpoint #195 | 1 tentativo\n1️⃣ | Corrispondenza: 100% 📌\nlnkd.in/pinpoint.",
        'Pinpoint Nr. 323 | 3 Rateversuche\n1️⃣ | 24 % Treffer \n2️⃣ | 2 % Treffer \n3️⃣ | 100 % Treffer 📌\nlnkd.in/pinpoint.',
        'Pinpoint #323 | 4 aciertos\n1️⃣ | 8 % de coincidencia\n2️⃣ | 2 % de coincidencia\n3️⃣ | 5 % de coincidencia\n4️⃣ | 100 % de coincidencia 📌\nlnkd.in/pinpoint.',
        'Pinpoint Nr. 323 | 3 Rateversuche\n1️⃣ | 24 % Treffer \n2️⃣ | 2 % Treffer \n3️⃣ | 100 % Treffer 📌\nlnkd.in/pinpoint.',
        # 'Pinpoint #323 | 推測3回\n1️⃣ | 3%件マッチ\n2️⃣ | 1%件マッチ\n3️⃣ | 100%件マッチ 📌\n🏅 今日、私は全プレーヤーの上位10%に入っています!',  # Does not work
        'Pinpoint n. 323 | 3 risposte giuste\n1️⃣ | 24% di corrispondenza \n2️⃣ | 19% di corrispondenza \n3️⃣ | 100% di corrispondenza 📌\n🏅 Oggi sono più intelligente del 75% dei CEO!\nlnkd.in/pinpoint.',
        'Pinpoint nr. 323 | 3 încercări\n1️⃣ | potrivire 8 % \n2️⃣ | potrivire 27 % \n3️⃣ | potrivire 100 % 📌\n🏅 Sunt mai deștept decât 90 % dintre directorii generali de astăzi\nlnkd.in/pinpoint.',
        'Pinpoint #328\n1️⃣ | 6% match\n2️⃣ | 3% match\n3️⃣ | 5% match\n4️⃣ | 1% match\n5️⃣ | 5% match\nlnkd.in/pinpoint.'
    ]
    expected = [
        {"day": "159", "name": "Pinpoint", "timestamp": 10, "tries": "3", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "167", "name": "Pinpoint", "timestamp": 10, "tries": "2", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "169", "name": "Pinpoint", "timestamp": 10, "tries": "1", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "169", "name": "Pinpoint", "timestamp": 10, "tries": "2", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "169", "name": "Pinpoint", "timestamp": 10, "tries": "5", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "169", "name": "Pinpoint", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "170", "name": "Pinpoint", "timestamp": 10, "tries": "3", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "181", "name": "Pinpoint", "timestamp": 10, "tries": "1", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "195", "name": "Pinpoint", "timestamp": 10, "tries": "1", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "323", "name": "Pinpoint", "timestamp": 10, "tries": "3", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "323", "name": "Pinpoint", "timestamp": 10, "tries": "4", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "323", "name": "Pinpoint", "timestamp": 10, "tries": "3", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "323", "name": "Pinpoint", "timestamp": 10, "tries": "3", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "323", "name": "Pinpoint", "timestamp": 10, "tries": "3", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "328", "name": "Pinpoint", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["Pinpoint", "lnkd.in/pinpoint"]
        _can_handle_this = all(w in raw_text for w in wordlist)
        # print(f"Pinpoint can_handle_this: {_can_handle_this}")
        return _can_handle_this

    def parse(self):
        text = self.raw_text
        if '|' in text and "📌" in text:
            matches = re.search(r"(\d+)\s\|\s(\d+)", text)
            self.day = matches.group(1)
            self.tries = matches.group(2)
        else:
            matches = re.search(r"(?:n\. |#|Nr\. )(\d+)", text)
            self.day = matches.group(1)
            self.tries = "X"

            # Check for different result formats
            if "📌" in text and '/5' in text:
                position_match = re.search(r"\((\d+)/5\)", text)
                self.tries = position_match.group(1) if position_match else None


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
        wordlist = ["#Polygonle", "https://www.polygonle.com"]
        _can_handle_this = all(w in raw_text for w in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        matches = re.search(r"Polygonle (\d+) (.)", text)
        self.day = matches.group(1)
        punti = matches.group(2)

        if punti == "X" or punti == "😔":
            self.tries = "X"
        elif punti == "🎯":
            self.tries = "1"
        else:
            self.tries = punti


@dataclass
class Posterdle(Giochino):
    _name = "Posterdle"
    _category = "Cinema e Serie TV"
    _date = datetime.date(2024, 9, 4)
    _day = "100"
    _emoji = "🍿"
    _url = "https://likewise.com/games/posterdle"

    has_extra = True

    examples = [
        "#Posterdle #2024-09-04 \n\n ⌛️ 3️⃣ seconds \n 🍿 🟩 ⬜️ ⬜️ ⬜️ ⬜️ ⬜️  \n https://likewise.com/games/posterdle/2024-09-04",  # vinta
        "#Posterdle #2024-09-04 \n\n ⌛️ 6️⃣ seconds \n 🍿 🟥 🟥 🟩 ⬜️ ⬜️ ⬜️  \n https://likewise.com/games/posterdle/2024-09-04",  # vinta
        "#Posterdle #2024-09-04 \n\n ⌛️ 2️⃣1️⃣ seconds \n 🍿 ⬜️ ⬜️ ⬜️ ⬜️ ⬜️ ⬜️  \n https://likewise.com/games/posterdle/2024-09-04",  # persa (tempo)
        "#Posterdle #2024-09-03 \n\n ⌛️ 6️⃣ seconds \n 🍿 🟥 🟥 🟥 🟥 🟥 🟥  \n https://likewise.com/games/posterdle/2024-09-03",  # persa (tentativi)
    ]
    expected = [
        {"day": "100", "name": "Posterdle", "timestamp": 10, "tries": "3", "user_id": 456481297, "user_name": "Trifase", "stars": "5"},
        {"day": "100", "name": "Posterdle", "timestamp": 10, "tries": "6", "user_id": 456481297, "user_name": "Trifase", "stars": "3"},
        {"day": "100", "name": "Posterdle", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "99", "name": "Posterdle", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["#Posterdle", "https://likewise.com/games/posterdle/"]
        _can_handle_this = all(w in raw_text for w in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        date_str = re.search(r"#Posterdle (#\d{4}-\d{2}-\d{2})", text).group(1)
        self.day = get_day_from_date(self._date, self._day, "Posterdle", date_str)

        if "🟩" not in text:
            self.tries = "X"
        else:
            self.stars = str(text.count("⬜️"))
            time = re.search(r"((?:\S\ufe0f\S)+)", text).group(1)
            self.tries = time_from_emoji(time)


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


@dataclass
class Reversle(Giochino):
    _name = "Reversle"
    _category = "Giochi di parole"
    _date = datetime.date(2024, 10, 6)
    _day = "966"
    _emoji = "⤴️"
    _url = "https://reversle.net/"

    can_lose: False

    examples = [
        "Reversle #966 65.47s\n\n⬜️🟨⬜️⬜️🟨 12.69s\n⬜️⬜️🟨🟨⬜️ 25.97s\n⬜️🟨🟨🟨⬜️ 9.50s\n⬜️⬜️🟩⬜️🟩 17.31s\n🟩🟩🟩🟩🟩\n\nreversle.net",
    ]
    expected = [
        {"day": "966", "name": "Reversle", "timestamp": 10, "tries": 6547, "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["Reversle #", "reversle.net"]
        _can_handle_this = all(w in raw_text for w in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        matches = re.search(r"Reversle #(\d+) (\d+\.\d+)s", text)
        self.day = matches.group(1) if matches else None
        punti = matches.group(2).replace(".", "").replace(",", "")
        self.tries = int(punti)


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
        wordlist = ["rotabox.es/", "clicks:"]
        _can_handle_this = all(w in raw_text for w in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text
        day_match = re.search(r"rotabox.es/(\d+)", text)
        clicks_match = re.search(r"clicks: (\d+)", text)
        self.day = day_match.group(1) if day_match else None
        self.tries = int(clicks_match.group(1)) if clicks_match else None


@dataclass
class Snoop(Giochino):
    _name = "Snoop"
    _category = "Immagini, giochi e musica"
    _date = datetime.date(2025, 5, 17)
    _day = "100"
    _emoji = "🔍"
    _url = "https://www.shockwave.com/gamelanding/the-daily-snoop-a-hidden-object-game"

    can_lose: False

    examples = [
        'Daily SNOOP 25/05/17 completed in 01:58.10.\n\n🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟨🟩🟩🟩🔍🟩\n\nCan you beat my time? Try here: https://shockwave.com/gamelanding/the-daily-snoop-a-hidden-object-game',
        'Daily SNOOP 25/05/17 completed in 00:24.24.\n\n🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩\n\nCan you beat my time? Try here: https://shockwave.com/gamelanding/the-daily-snoop-a-hidden-object-game',
        'Daily SNOOP 25/05/17 completed in 02:33.83.\n\n🔍🟨🟩🟨🟨🟨🟨🟨🟩🟨🟨🟨🟨🟨🟩🟨🟩🟨🟩🟩🟩🟩🟩🟩🟨🟨🟨🟩🟩🟩🟩🟨🟨🟨🟨🟩\n\nCan you beat my time? Try here: https://shockwave.com/gamelanding/the-daily-snoop-a-hidden-object-game',
    ]
    expected = [
        {"day": "100", "name": "Snoop", "timestamp": 10, "tries": "015810", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "100", "name": "Snoop", "timestamp": 10, "tries": "002424", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "100", "name": "Snoop", "timestamp": 10, "tries": "023383", "user_id": 456481297, "user_name": "Trifase"},
        
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["Daily SNOOP", "https://shockwave.com/gamelanding/the-daily-snoop-a-hidden-object-game"]
        _can_handle_this = all(w in raw_text for w in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text
        day_match = re.search(r"(\d+\/\d+\/\d+)", text)
        time_match = re.search(r"(\d+:\d+.\d+)", text)

        self.day = get_day_from_date(self._date, self._day, "Snoop", day_match.group(1)) if day_match else None
        self.tries = time_match.group(1).replace(':', '').replace('.','')
        self.stars = None


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
        wordlist = ["Spellcheck #"]
        _can_handle_this = all(w in raw_text for w in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text
        day_match = re.search(r"Spellcheck #(\d+)", text)
        self.day = day_match.group(1) if day_match else None

        self.tries = 15 - text.count("🟩")
        self.stars = None


@dataclass
class Spotle(Giochino):
    _name = "Spotle"
    _category = "Immagini, giochi e musica"
    _date = datetime.date(2025, 9, 13)
    _day = "1233"
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
        wordlist = ["Spotle #", "spotle.io"]
        _can_handle_this = all(w in raw_text for w in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text
        day_match = re.search(r"Spotle #(\d+)", text)
        self.day = day_match.group(1) if day_match else None

        punteggio_bonificato = ""
        for char in text:
            if char in ["⬛", "🟥", "🟩", "⬜", "🎁"]:
                punteggio_bonificato += char

        if ("🟩" not in text and "🎁" not in text) or "❌" in text:
            self.tries = "X"
        else:
            if "🎁" in text:
                self.tries = str(punteggio_bonificato.index("🎁") + 1)
            else:
                self.tries = str(punteggio_bonificato.index("🟩") + 1)


@dataclass
class Spots(Giochino):
    _name = "Spots"
    _category = "Logica"
    _date = datetime.date(2024, 9, 4)
    _day = "54"
    _emoji = "🟡"
    _url = "https://spots.wtf"

    examples = [
        "Spots Code #54\nGuesses: 10\n🟨⬛️⬛️⬛️\n🟩🟩⬛️⬛️\n🟩⬛️⬛️⬛️\n🟨🟨⬛️⬛️\n🟨⬛️⬛️⬛️\n🟨🟨⬛️⬛️\n🟨⬛️⬛️⬛️\n🟨⬛️⬛️⬛️\n⬛️⬛️⬛️⬛️\n🟨⬛️⬛️⬛️\nhttps://spots.wtf",
        "Spots Code #54\nGuesses: 4\n🟩🟩🟩🟩\n🟩🟩🟩⬛️\n🟩🟩⬛️⬛️\n🟩⬛️⬛️⬛️\nhttps://spots.wtf",
    ]
    expected = [
        {"day": "54", "name": "Spots", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "54", "name": "Spots", "timestamp": 10, "tries": "4", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["Spots Code #", "https://spots.wtf"]
        _can_handle_this = all(w in raw_text for w in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        day_match = re.search(r"Spots Code #(\d+)", text)
        self.day = day_match.group(1) if day_match else None

        guesses_match = re.search(r"Guesses: (\d+)", text)
        self.tries = guesses_match.group(1) if "🟩🟩🟩🟩" in text else "X"


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
        wordlist = ["squareword.org", "#squareword"]
        _can_handle_this = all(w in raw_text for w in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        matches = re.search(r"squareword.org (\d+): (\d+) guesses", text)
        self.day = matches.group(1) if matches else None
        self.tries = matches.group(2) if matches else None
        self.stars = None


@dataclass
class Stepdle(Giochino):
    _name = "Stepdle"
    _category = "Giochi di parole"
    _date = datetime.date(2024, 9, 16)
    _day = "27"
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
        wordlist = ["Stepdle #", "/20"]
        _can_handle_this = all(w in raw_text for w in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        day_match = re.search(r"Stepdle #(\d+)", text)
        self.day = day_match.group(1) if day_match else None

        punti_match = re.search(r"(\d+)/20", text)
        won = any(line.count("🟩") == 7 for line in text.splitlines())
        if won:
            self.tries = punti_match.group(1) if punti_match else None
        else:
            self.tries = "X"


@dataclass
class Strands(Giochino):
    _name = "Strands"
    _category = "Giochi di parole"
    _date = datetime.date(2024, 5, 17)
    _day = "75"
    _emoji = "💡"
    _url = "https://www.nytimes.com/games/strands"

    can_lose: False

    examples = ["Strands #74\n“Tasty!”\n🔵🔵🔵🔵\n🔵🔵🟡🔵\n🔵", "Strands #75\n“Looking for a mate”\n💡🔵💡🔵\n💡🔵🔵🔵\n🟡🔵🔵"]
    expected = [
        {"day": "74", "name": "Strands", "timestamp": 10, "tries": "0", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "75", "name": "Strands", "timestamp": 10, "tries": "3", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["Strands #"]
        _can_handle_this = all(w in raw_text for w in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        day_match = re.search(r"Strands #(\d+)", text)
        self.day = day_match.group(1) if day_match else None
        count = 0
        count += text.count("💡")
        self.tries = str(count)


@dataclass
class Tango(Giochino):
    _name = "Tango"
    _category = "Logica"
    _date = datetime.date(2024, 10, 10)
    _day = "3"
    _emoji = "🌗"
    _url = "https://lnkd.in/tango"

    can_lose: False

    examples = [
        "Tango #3 | 1:24 and flawless\nFirst 5 placements:\n🟨 🟨 🟨 🟨 🟨 🟨 \n2️⃣ 🟨 🟨 🟨 🟨 1️⃣ \n3️⃣ 4️⃣ 🟨 🟨 🟨 🟨 \n🟨 5️⃣ 🟨 🟨 🟨 🟨 \n🟨 🟨 🟨 🟨 🟨 🟨 \n🟨 🟨 🟨 🟨 🟨 🟨 \nlnkd.in/tango.",
        "Tango #3\n2:44 🌗\nlnkd.in/tango.",
        "Tango #3 | 0:55 e impeccabilePrimi 5 posizionamenti:\n🟨🟨🟨🟨🟨🟨\n1️⃣🟨🟨🟨🟨🟨\n2️⃣3️⃣🟨🟨🟨🟨\n🟨🟨🟨🟨🟨🟨\n🟨🟨🟨🟨🟨🟨\n🟨🟨5️⃣4️⃣🟨🟨\nlnkd.in/tango.",
        'Tango n. 199 | 1:35 e impeccabile\nPrimi 5 posti in classifica:\n🟨🟨🟨🟨🟨🟨\n🟨🟨🟨🟨🟨🟨\n🟨🟨🟨🟨🟨🟨\n🟨🟨🟨🟨🟨🟨\n🟨1️⃣2️⃣5️⃣🟨🟨\n🟨🟨3️⃣4️⃣🟨🟨\nlnkd.in/tango.'
    ]
    expected = [
        {"day": "3", "name": "Tango", "timestamp": 10, "tries": "124", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "3", "name": "Tango", "timestamp": 10, "tries": "244", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "3", "name": "Tango", "timestamp": 10, "tries": "055", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "199", "name": "Tango", "timestamp": 10, "tries": "135", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["Tango", "lnkd.in/tango."]
        _can_handle_this = all(w in raw_text for w in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        # matches_day = re.search(r"Tango #(\d+)", text)
        matches_day = re.search(r"Tango (?:n\. |#|Nr\. )(\d+)", text)
        matches_time = re.search(r"(\d+):(\d+)", text)
        self.day = matches_day.group(1) if matches_day else None
        self.tries = matches_time.group(1) + matches_time.group(2) if matches_time else None


@dataclass
class TempoIndovinr(Giochino):
    _name = "TempoIndovinr"
    _category = "Immagini, giochi e musica"
    _date = datetime.date(2023, 11, 17)
    _day = "5"
    _emoji = "🗺️"
    _url = "https://jacopofarina.eu/experiments/tempoindovinr"

    can_lose: False
    hidden_game = True

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
        wordlist = ["TempoIndovinr", "https://jacopofarina.eu/experiments/tempoindovinr/"]
        _can_handle_this = all(w in raw_text for w in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text
        day_match = re.search(r"day (\d+)", text)
        self.day = day_match.group(1) if day_match else None
        point_match = re.search(r"Ho fatto (\d+)/1000 punti", text)
        self.tries = 1000 - int(point_match.group(1)) if point_match else None
        self.stars = None


@dataclass
class Thirdle(Giochino):
    _name = "Thirdle"
    _category = "Giochi di parole"
    _date = datetime.date(2024, 5, 22)
    _day = "777"
    _emoji = "#️⃣"
    _url = "https://thirdle.org/"

    can_lose: False

    examples = [
        "#thirdle #thirdle775\n\n🏆 1 / 6 | 🔥 1\n\n🟩🟩 🟩🟩 🟩🟩",
        "#thirdle #thirdle776\n\n🏆 4 / 6 | 🔥 2\n\n🟧⬛️ 🟧⬛️ 🟧⬛️\n🟩🟩 🟩⬛️ 🟧⬛️\n🟩🟩 🟩⬛️ 🟩🟩\n🟩🟩 🟩🟩 🟩🟩",
        "#thirdle #thirdle777\n\n🏆 X / 6 \n\n🟩🟩 🟩⬛️ 🟩🟩\n🟩🟩 🟩⬛️ 🟩🟩\n🟩🟩 🟩⬛️ 🟩🟩\n🟩🟩 🟩⬛️ 🟩🟩\n🟩🟩 🟩⬛️ 🟩🟩\n🟩🟩 🟩⬛️ 🟩🟩",
    ]
    expected = [
        {"day": "775", "name": "Thirdle", "timestamp": 10, "tries": 1, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "776", "name": "Thirdle", "timestamp": 10, "tries": 4, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "777", "name": "Thirdle", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["#thirdle", "🏆"]
        _can_handle_this = all(w in raw_text for w in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text
        day_match = re.search(r"#thirdle(\d+)", text)
        self.day = day_match.group(1) if day_match else None

        match_points = re.search(r"(\d+|X) / 6", text)
        if match_points.group(1) == "X":
            self.tries = match_points.group(1)
        else:
            self.tries = int(match_points.group(1))
            self.stars = None


@dataclass
class Timdle(Giochino):
    _name = "Timdle"
    _category = "Logica"
    _date = datetime.date(2025, 6, 24)
    _day = "100"
    _emoji = "⏳"
    _url = "https://www.timdle.com/"

    can_lose: False

    examples = [
        'TIMDLE Jun 24\n🌟 34/36\n1: 1p     5: 5p\n2: 2p     6: 5p\n3: 3p     7: 7p\n4: 4p     8: 7p\nPlay at https://timdle.com',
        'TIMDLE Jun 27\n😌 31/36\n1: 1p     5: 5p\n2: 1p     6: 4p\n3: 3p     7: 6p\n4: 4p     8: 7p\nPlay at https://timdle.com',
    ]
    expected = [
        {"day": "100", "name": "Timdle", "timestamp": 10, "tries": 2, "user_id": 456481297, "user_name": "Trifase"},
        {"day": "103", "name": "Timdle", "timestamp": 10, "tries": 5, "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["TIMDLE", "Play at https://timdle.com"]
        _can_handle_this = all(w in raw_text for w in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        match_date = re.search(r"TIMDLE (\w+ \d{1,2})", text)
        current_year = datetime.datetime.now().year
    
        if match_date:
            date_str = match_date.group(1)
        current_day = f"{date_str} {current_year}"
        self.day = get_day_from_date(self._date, self._day, "Timdle", current_day)

        match_points = re.search(r"(\d+)/36", text)

        self.tries = 36 - int(match_points.group(1)) if match_points else None
        self.stars = None


@dataclass
class TimeGuessr(Giochino):
    _name = "TimeGuessr"
    _category = "Immagini, giochi e musica"
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
        wordlist = ["TimeGuessr #", "50,000"]
        _can_handle_this = all(w in raw_text for w in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text
        match_day = re.search(r"#(\d+)", text)
        self.day = match_day.group(1) if match_day else None

        match_points = re.search(r"(\d+),(\d+)", text)
        self.tries = 50_000 - int(match_points.group(1) + match_points.group(2)) if match_points else None
        self.stars = None

@dataclass
class Titleshot(Giochino):
    _name = "Titleshot"
    _category = "Cinema e Serie TV"
    _date = datetime.date(2025, 7, 28)
    _day = "54"
    _emoji = "🎦"
    _url = "https://framed.wtf/titleshot"

    examples = [
        'Framed - Title Shot Challenge #54\n🎥 🟥 🟥 🟥 🟥 🟥 🟥\n\nhttps://framed.wtf/titleshot',
        'Framed - Title Shot Challenge #42\n    🎥 🟥 🟩 ⬛️ ⬛️ ⬛️ ⬛️\n\n    https://framed.wtf/titleshot',
    ]
    expected = [
        {"day": "54", "name": "Titleshot", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "42", "name": "Titleshot", "timestamp": 10, "tries": "2", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["Framed", 'Title Shot Challenge', 'https://framed.wtf/titleshot']
        _can_handle_this = all(c in raw_text for c in wordlist) and "one-frame" not in raw_text
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        # Extract day number using regex
        day_match = re.search(r"Challenge #(\d+)", text)
        self.day = day_match.group(1) if day_match else None

        # Find the emoji line containing the results
        emoji_line = re.search(r"🎥\s+([🟥🟩⬛\s]+)", text)
        if emoji_line:
            # Remove spaces and get the results string
            punteggio = emoji_line.group(1).replace(" ", "")
            if "🟩" not in punteggio:
                self.tries = "X"
            else:
                # Find the position of the first green square
                self.tries = str(punteggio.index("🟩") + 1)


@dataclass
class Tradle(Giochino):
    _name = "Tradle"
    _category = "Geografia e Mappe"
    _date = datetime.date(2023, 6, 23)
    _day = "474"
    _emoji = "🚢"
    _url = "https://games.oec.world/en/tradle"

    examples = [
        "#Tradle #761 5/6\n🟩🟩🟨⬜⬜\n🟩🟩🟩🟩⬜\n🟩🟩🟩🟩🟨\n🟩🟩🟩🟩🟨\n🟩🟩🟩🟩🟩\nhttps://games.oec.world/en/tradle",
        "#Tradle #761 X/6\n🟩🟨⬜⬜⬜\n🟩🟩🟩🟨⬜\n🟩🟩🟩🟩🟨\n🟩🟩🟩🟩⬜\n🟩🟩🟩🟩🟨\n🟩🟩🟩🟩🟨\nhttps://games.oec.world/en/tradle",
        "#Tradle #761 5/6\n🟩🟩🟨⬜⬜\n🟩🟩🟩🟩⬜\n🟩🟩🟩🟩🟨\n🟩🟩🟩🟩🟨\n🟩🟩🟩🟩🟩\nhttps://oec.world/en/tradle",
        "#Tradle #761 X/6\n🟩🟨⬜⬜⬜\n🟩🟩🟩🟨⬜\n🟩🟩🟩🟩🟨\n🟩🟩🟩🟩⬜\n🟩🟩🟩🟩🟨\n🟩🟩🟩🟩🟨\nhttps://oec.world/en/tradle",
        '#Tradle #1128 2/6\n🟩🟩🟩🟩⬜\n🟩🟩🟩🟩🟩\nhttps://oec.world/en/games/tradle',
    ]
    expected = [
        {"day": "761", "name": "Tradle", "timestamp": 10, "tries": "5", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "761", "name": "Tradle", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "761", "name": "Tradle", "timestamp": 10, "tries": "5", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "761", "name": "Tradle", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "1128", "name": "Tradle", "timestamp": 10, "tries": "2", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["#Tradle", "https://games.oec.world/en/tradle"]
        wordlist2 = ["#Tradle", "https://oec.world/en/tradle"]
        wordlist3 = ["#Tradle", "https://oec.world/en/games/tradle"]
        _can_handle_this = any(all(w in raw_text for w in wl) for wl in [wordlist, wordlist2, wordlist3])
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        matches = re.search(r"#(\d+) (\d+|X)/6", text)

        self.day = matches.group(1)
        self.tries = matches.group(2)
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
        "#travle #484 +3\n🟩🟧✅🟥🟧✅✅\nhttps://travle.earth",  # vinto
        "#travle #484 +0 (Perfect)\n✅✅✅✅\nhttps://travle.earth",  # vinto, perfetto
        "#travle #484 +3 (1 suggerimento)\n✅✅✅✅\nhttps://travle.earth",  # vinto, malus di 1
        "#travle #484 +3 (2 suggerimento)\n✅✅✅✅\nhttps://travle.earth",  # vinto, malus di 2 (3)
        "#travle #484 +3 (3 suggerimento)\n✅✅✅✅\nhttps://travle.earth",  # vinto, malus di 3 (6)
        "#travle #484 +3 (🎌)\n🟩🟧✅🟥🟧✅✅\nhttps://travle.earth",  # vinto, bonus
        "#travle #484 +0 (🎌) (Perfect)\n✅✅✅✅\nhttps://travle.earth",  # vinto, bonus, perfetto
        "#travle #484 +3 (🎌) (1 suggerimento)\n✅✅✅✅\nhttps://travle.earth",  # vinto, bonus, malus di 1
        "#travle #484 +3 (🎌) (2 suggerimento)\n✅✅✅✅\nhttps://travle.earth",  # vinto, bonus, malus di 2 (3)
        "#travle #484 +3 (🎌) (3 suggerimento)\n✅✅✅✅\nhttps://travle.earth",  # vinto, bonus, malus di 3 (6)
        "#travle #484 (4 lontano)\n🟧🟧🟥🟥🟧🟥🟥🟥🟥\nhttps://travle.earth",  # perso
    ]
    expected = [
        {"day": "484", "name": "Travle", "timestamp": 10, "tries": "3", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "484", "name": "Travle", "timestamp": 10, "tries": "0", "user_id": 456481297, "user_name": "Trifase", "stars": 1},
        {"day": "484", "name": "Travle", "timestamp": 10, "tries": "4", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "484", "name": "Travle", "timestamp": 10, "tries": "6", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "484", "name": "Travle", "timestamp": 10, "tries": "9", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "484", "name": "Travle", "timestamp": 10, "tries": "3", "user_id": 456481297, "user_name": "Trifase", "stars": 1},
        {"day": "484", "name": "Travle", "timestamp": 10, "tries": "0", "user_id": 456481297, "user_name": "Trifase", "stars": 2},
        {"day": "484", "name": "Travle", "timestamp": 10, "tries": "4", "user_id": 456481297, "user_name": "Trifase", "stars": 1},
        {"day": "484", "name": "Travle", "timestamp": 10, "tries": "6", "user_id": 456481297, "user_name": "Trifase", "stars": 1},
        {"day": "484", "name": "Travle", "timestamp": 10, "tries": "9", "user_id": 456481297, "user_name": "Trifase", "stars": 1},
        {"day": "484", "name": "Travle", "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["#travle ", "https://travle.earth"]
        _can_handle_this = all(w in raw_text for w in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        # Extract day number using regex
        day_match = re.search(r"#travle #(\d+)", text)
        self.day = day_match.group(1) if day_match else None

        # Check if game was lost or won
        if "✅" not in text.splitlines()[1]:
            self.tries = "X"
        else:
            # Extract tries count
            tries_match = re.search(r"#travle #\d+ \+(\d+)", text)
            self.tries = tries_match.group(1) if tries_match else None

        # Initialize stars calculation
        self.stars = 0

        # Check for perfect game
        if re.search(r"\((Perfect|Perfetto|Perfekt)\)", text):
            self.stars += 1

        # Check for bonus flag
        if "🎌" in text:
            self.stars += 1

        # If there are no stars, set to None instead of 0
        if self.stars == 0:
            self.stars = None

        # Process hints if the game was won
        if self.tries != "X" and self.tries is not None:
            # Look for hint pattern
            hint_match = re.search(r"\((\d+) suggerimento\)", text)
            if hint_match:
                hint_count = int(hint_match.group(1))
                # Apply triangular penalty formula: n(n+1)/2
                penalty = (hint_count * (hint_count + 1)) // 2
                self.tries = str(int(self.tries) + penalty)


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
        wordlist = ["#travle_ita ", "https://travle.earth/ita"]
        _can_handle_this = all(w in raw_text for w in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        # Extract day number using regex
        day_match = re.search(r"#travle_ita #(\d+)", text)
        self.day = day_match.group(1) if day_match else None

        # Check if game was lost or won
        if "✅" not in text.splitlines()[1]:
            self.tries = "X"
        else:
            # Extract tries count
            tries_match = re.search(r"#travle_ita #\d+ \+(\d+)", text)
            self.tries = tries_match.group(1) if tries_match else None

        # Check for perfect game - this sets stars
        self.stars = None
        if re.search(r"\((Perfect|Perfetto|Perfekt)\)", text):
            self.stars = 1

        # Process hints if the game was won and not perfect
        if self.tries != "X" and self.tries is not None and not self.stars:
            # Look for hint pattern
            hint_match = re.search(r"\((\d+) [^\)]+\)", text)
            if hint_match:
                hint_count = int(hint_match.group(1))
                # Apply triangular penalty formula: n(n+1)/2
                penalty = int((hint_count * (hint_count + 1)) / 2)
                self.tries = int(self.tries) + penalty


@dataclass
class Unzoomed(Giochino):
    _name = "Unzoomed"
    _category = "Geografia e Mappe"
    _date = datetime.date(2024, 4, 16)
    _day = "89"
    _emoji = "🔎"
    _url = "https://unzoomed.com"

    examples = [
        "Unzoomed #89 1/6 🟢⚪️⚪️⚪️⚪️⚪️\n https://unzoomed.com",
        "Unzoomed #89 4/6 🔴🔴🟡🟢⚪️⚪️\n https://unzoomed.com",
        "Unzoomed #89 5/6 🔴🔴🔴🔴🟢⚪️\n https://unzoomed.com",
        "Unzoomed #87 6/6 🔴🔴🔴🔴🟡🟡\n https://unzoomed.com",
    ]

    expected = [
        {"day": "89", "name": "Unzoomed", "stars": None, "timestamp": 10, "tries": "1", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "89", "name": "Unzoomed", "stars": None, "timestamp": 10, "tries": "4", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "89", "name": "Unzoomed", "stars": None, "timestamp": 10, "tries": "5", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "87", "name": "Unzoomed", "stars": None, "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["Unzoomed #", "https://unzoomed.com"]
        _can_handle_this = all(w in raw_text for w in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        matches = re.search(r"#(\d+) (\d+)/6", text)
        self.day = matches.group(1) if matches else None
        self.tries = matches.group(2) if matches else None
        if "🟢" not in text:
            self.tries = "X"


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
        wordlist = ["#waffle", "/5"]
        _can_handle_this = all(w in raw_text for w in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text
        matches = re.search(r"#waffle(\d+) (\d+|X)/5", text)
        self.day = matches.group(1) if matches else None
        self.tries = 15 - int(matches.group(2)) if matches.group(2) != "X" else "X"
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
        wordlist = ["#WhereTaken", "wheretaken.teuteuf.fr"]
        _can_handle_this = all(w in raw_text for w in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        day_matches = re.search(r"#(\d+)", text)
        self.day = day_matches.group(1) if day_matches else None
        punti_matches = re.search(r"(\d+|X)/6", text)
        self.tries = punti_matches.group(1) if punti_matches else None

        self.stars = text.count(b"\xe2\xad\x90".decode("utf-8"))


@dataclass
class WhenTaken(Giochino):
    _name = "WhenTaken"
    _category = "Geografia e Mappe"
    _date = datetime.date(2024, 9, 5)
    _day = "191"
    _emoji = "📍"
    _url = "https://whentaken.com"

    examples = [
        "#WhenTaken #191 (05.09.2024)\n\nI scored 505/1000 🎉\n\n1️⃣ 📍 3499 km - 🗓 22 yrs - ⚡️ 82 / 200\n2️⃣ 📍 441 km - 🗓 7 yrs - ⚡️ 178 / 200\n3️⃣ 📍 16972 km - 🗓 11 yrs - ⚡️ 82 / 200\n4️⃣ 📍 1181 km - 🗓 4 yrs - ⚡️ 162 / 200\n5️⃣ 📍 9698 km - 🗓 62 yrs - ⚡️ 1 / 200\n\nhttps://whentaken.com"
    ]
    expected = [
        {"day": "191", "name": "WhenTaken", "timestamp": 10, "tries": "495", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["#WhenTaken", "https://whentaken.com"]
        _can_handle_this = all(w in raw_text for w in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        day_matches = re.search(r"#(\d+)", text)
        self.day = day_matches.group(1) if day_matches else None
        punti_matches = re.search(r"I scored (\d+)", text)
        self.tries = str(1000 - int(punti_matches.group(1))) if punti_matches else None


@dataclass
class WordGrid(Giochino):
    _name = "WordGrid"
    _category = "Giochi di parole"
    _date = datetime.date(2024, 6, 11)
    _day = "11"
    _emoji = "🦄"
    _url = "https://wordgrid.clevergoat.com/"

    examples = [
        "Word Grid #11\n🟨🟪🦄\n🦄🟦🟨\n🦄🦄🟦\nRarity: 6.0\nwordgrid.clevergoat.com 🐐",
        "Word Grid #11\n🟨🟪🦄\n🦄🟦🟨\n🦄🦄🟦\nRarity: 6.1\nwordgrid.clevergoat.com 🐐",
    ]
    # Remember: tries are multiplied by 10
    expected = [
        {"day": "11", "name": "WordGrid", "timestamp": 10, "tries": "60", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "11", "name": "WordGrid", "timestamp": 10, "tries": "61", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["Word Grid #", "Rarity:"]
        _can_handle_this = all(w in raw_text for w in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text
        match_day = re.search(r"#(\d+)", text)
        self.day = match_day.group(1) if match_day else None
        match_rarity = re.search(r"Rarity: (\d+\.\d+)", text)
        # The point is always a flat with a decimal. We will multiply by 10 to get a whole int, and then will divide by then when displaying it in the classifica.
        self.tries = str(int(float(match_rarity.group(1)) * 10))


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
        wordlist = ["Wordle", "/6"]
        _can_handle_this = all(w in raw_text for w in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        matches = re.search(r"Wordle (\d?[\,\.]?\d*) (\d+|X)/6", text)
        # print(f'matches: {matches.group(1)}')
        self.day = matches.group(1).replace(",", "").replace(".", "") if matches else None
        self.tries = matches.group(2) if matches else None
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
        "Word Peaks #782 1/6\n\n  🟩🟩🟩🟩🟩\nhttps://wordpeaks.com",
        "Word Peaks #782 3/6\n\n  🔼🔼🔼🟩🔼\n  🔼🟩🔼🔽🔼\n  🟩🟩🟩🟩🟩\nhttps://wordpeaks.com",
        "Word Peaks #782 X/6\n\n  🔼🔽🔼🔽🔼\n  🔼🔽🔼🔼🔽\n  🟩🟩🔼🔽🔼\n  🔼🔼🔼🟩🔼\n  🔼🔽🔼🔽🔼\n  🔼🔼🔼🔽🔼\nhttps://wordpeaks.com",
    ]
    expected = [
        {"day": "782", "name": "WordPeaks", "stars": None, "timestamp": 10, "tries": "1", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "782", "name": "WordPeaks", "stars": None, "timestamp": 10, "tries": "3", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "782", "name": "WordPeaks", "stars": None, "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["Word Peaks #", "https://wordpeaks.com"]
        _can_handle_this = all(w in raw_text for w in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        matches = re.search(r"Word Peaks #(\d+) (\d+|X)/6", text)
        self.day = matches.group(1) if matches else None
        self.tries = matches.group(2) if matches else None
        self.stars = None



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
        "#Worldle #1148 (14.03.2025) 1/6 (100%)\n🟩🟩🟩🟩🟩🎉\n🧭⭐📍🚩🗿📜🛡️🔤🗣️👫🪙🏙📦📐\nhttps://worldle.teuteuf.fr",
    ]
    expected = [
        {"day": "807", "name": "Worldle", "stars": 2, "timestamp": 10, "tries": "1", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "808", "name": "Worldle", "stars": 0, "timestamp": 10, "tries": "4", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "808", "name": "Worldle", "stars": 0, "timestamp": 10, "tries": "X", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "1148", "name": "Worldle", "stars": 14, "timestamp": 10, "tries": "1", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["#Worldle", "https://worldle.teuteuf.fr"]
        _can_handle_this = all(w in raw_text for w in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text

        match_day = re.search(r"#(\d+)", text)
        self.day = match_day.group(1) if match_day else None
        match_points = re.search(r"(\d+|X)/6", text)
        self.tries = match_points.group(1) if match_points else None

        bussola = text.count(b"\xf0\x9f\xa7\xad".decode("utf-8"))       # 🧭
        stars = text.count(b"\xe2\xad\x90".decode("utf-8"))             # ⭐️
        pinpoint = text.count(b"\xf0\x9f\x93\x8d".decode("utf-8"))      # 📍
        flag = text.count(b"\xf0\x9f\x9a\xa9".decode("utf-8"))          # 🚩
        head = text.count(b"\xf0\x9f\x97\xbf".decode("utf-8"))          # 🗿
        paper = text.count(b"\xf0\x9f\x93\x9c".decode("utf-8"))         # 📜
        shield = text.count(b"\xf0\x9f\x9b\xa1".decode("utf-8"))        # 🛡️
        abc = text.count(b"\xf0\x9f\x94\xa4".decode("utf-8"))           # 🔤
        language = text.count(b"\xf0\x9f\x97\xa3".decode("utf-8"))      # 🗣
        population = text.count(b"\xf0\x9f\x91\xab".decode("utf-8"))    # 👫
        coin = text.count(b"\xf0\x9f\xaa\x99".decode("utf-8"))          # 🪙
        cityscape = text.count(b"\xf0\x9f\x8f\x99".decode("utf-8"))     # 🏙
        box = text.count(b"\xf0\x9f\x93\xa6".decode("utf-8"))           # 📦
        area = text.count(b"\xf0\x9f\x93\x90".decode("utf-8"))          # 📐
        self.stars = bussola + stars + pinpoint + flag + head + paper + shield + abc + language + population + coin + cityscape + box + area


@dataclass
class Zip(Giochino):
    _name = "Zip"
    _category = "Logica"
    _date = datetime.date(2025, 3, 19)
    _day = "2"
    _emoji = "⚡"
    _url = "https://lnkd.in/zip"

    examples = [
        'Zip #2 | 0:19 🏁\nWith 1 backtrack 🛑\n🏅 I’m in the Top 10% of all players today!\nlnkd.in/zip.',
        'Zip #1 | 0:09 and flawless 🏁\nWith no backtracks 🟢\nlnkd.in/zip.',
        'Zip 第 2 | 0:49 和完美无瑕 🏁\n无撤销操作 🟢\n🏅 我今天在所有玩家中排名前 75%！\nlnkd.in/zip.',
        'Zip no. 2 | 3:21 🏁\nAvec 30 retours en arrière 🛑\nlnkd.in/zip.',
        'Zip n.º 2 | 0:20 🏁\nSin ningún retroceso 🟢\n🏅 ¡Hoy he estado más audaz que el 90 % de los consejeros delegados!\n#AreYouSmarterThanaCEO\nlnkd.in/zip.',
        'Zip #9\n0:07 🏁\nlnkd.in/zip.',

    ]
    expected = [
        {"day": "2", "name": "Zip", "timestamp": 10, "tries": "019", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "1", "name": "Zip", "timestamp": 10, "tries": "009", "user_id": 456481297, "user_name": "Trifase", "stars": 1},
        {"day": "2", "name": "Zip", "timestamp": 10, "tries": "049", "user_id": 456481297, "user_name": "Trifase", "stars": 1},
        {"day": "2", "name": "Zip", "timestamp": 10, "tries": "321", "user_id": 456481297, "user_name": "Trifase"},
        {"day": "2", "name": "Zip", "timestamp": 10, "tries": "020", "user_id": 456481297, "user_name": "Trifase", "stars": 1},
        {"day": "9", "name": "Zip", "timestamp": 10, "tries": "007", "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        wordlist = ["Zip", "lnkd.in/zip."]
        _can_handle_this = all(w in raw_text for w in wordlist)
        return _can_handle_this

    def parse(self):
        text = self.raw_text
        matches = re.search(r'Zip.*?(\d+)(?:\s*\|\s*|\n)?(\d+:\d+)', text)
        self.day = matches.group(1) if matches else None
        self.tries = matches.group(2).replace(":", "") if matches else None
        self.stars = None
        if '🟢' in text:
            self.stars = 1


#######
def get_giochini():
    klasses = [
        cls_obj
        for _, cls_obj in inspect.getmembers(sys.modules[__name__], inspect.isclass)
        if cls_obj.__module__ == sys.modules[__name__].__name__ and cls_obj.__base__ == Giochino and not cls_obj.hidden_game
        # TODO: some sort of frequency-of-use ordering?
    ]
    # print(klasses)
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
    # print(games)
    return games


# This make a dictionary with every game info (grabbed from the list of classes) and it's imported almost everywhere
ALL_GAMES = get_games()
# This is a list of every class of game, used to instantiate them
ALL_CLASSES = get_giochini()


def test(print_debug, giochino=None):
    giochini_n = 0
    casi = 0
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
        giochini_n += 1
        for i, _ in enumerate(gioco.examples):
            update = generate_sample_update(gioco.examples[i])
            giochino = gioco(update)
            print(f"[{i+1}] ==== {giochino._name} ====")
            if print_debug:
                # print(f'{giochino.examples[i],}')
                print(f"info = {giochino.info}")
                print(f"expected = {giochino.expected[i]}")
                print(f"punteggio = {giochino.punteggio}")
            assert (giochino.expected[i] is None and giochino.punteggio is None) or all(x in giochino.punteggio.items() for x in giochino.expected[i].items())
            casi += 1
            print("test_passed ✅")
            print()
    print(f"Test passed for {giochini_n} games and {casi} cases")


# Tests! you can pass None as second parameter to test all games
if __name__ == "__main__":
    giochino_da_testare = None
    giochino_da_testare = CluesBySam

    test(True, giochino_da_testare)
