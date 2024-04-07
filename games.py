import datetime
from telegram import Update, Bot
import time
from dataclassy import dataclass

import inspect
import sys
import pprint

from config import GAMES
from utils import get_day_from_date, is_connection_completed, time_from_emoji

"""Un tentativo timido di convertire giochini, informazioni, parser e test in un'unica classe"""



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
            "day": self.day
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
            "stars": self.stars
        }


@dataclass
class Wordle(Giochino):
    examples = [
        'Wordle 1,011 5/6\n\n🟩🟩⬛️⬛️⬛️\n🟩🟩🟨⬛️⬛️\n🟩🟩⬛️🟨⬛️\n🟩🟩⬛️🟩🟩\n🟩🟩🟩🟩🟩',
        'Wordle 821 X/6\n\n🟨🟩⬛️⬛️⬛️\n⬛️🟩🟩⬛️⬛️\n⬛️🟩🟩⬛️⬛️\n⬛️🟩🟩⬛️⬛️\n⬛️🟩🟩⬛️⬛️\n⬛️🟩🟩🟩⬛️'
        ]
    expected = [
        {'day': '1011', 'name': 'Wordle', 'timestamp': 1712522008, 'tries': '5', 'user_id': 456481297, 'user_name': 'Trifase'},
        {'day': '821', 'name': 'Wordle', 'timestamp': 1712522008, 'tries': 'X', 'user_id': 456481297, 'user_name': 'Trifase'}
        ]

    def __init__(self, update):
        self._name = "Wordle"
        self._emoji = "🆒"
        self._category = "Giochi di parole"
        self._date = datetime.date(2023, 6, 23)
        self._day = "734"
        self._url = "https://www.nytimes.com/games/wordle/index.html"

        self.update = update
        self.raw_text =  self.update.message.text

        if self.can_handle_this:
            self.parse()

        self.has_extra: False
        self.can_lose: True


    @property
    def can_handle_this(self):
        _can_handle_this = 'Wordle' in self.raw_text and '/' in self.raw_text
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
        self.day = (first_line[1].replace(".", "").replace(",", ""))
        self.tries = first_line[-1].split("/")[0]
        self.stars = None
        self.timestamp = timestamp if timestamp else int(time.time())
        self.user_name = self.update.message.from_user.full_name
        self.user_id = self.update.message.from_user.id


@dataclass
class Parole(Giochino):
    examples = [
        'Par🇮🇹le 825 4/6\n\n⬜️⬜️⬜️⬜️🟨\n⬜️🟨🟨⬜️⬜️\n🟩🟩🟩⬜️🟩\n🟩🟩🟩🟩🟩',
        'Par🇮🇹le 813 X/6\n\n⬜️🟨🟨⬜️⬜️\n🟨🟩⬜️⬜️🟩\n⬜️🟩🟩⬜️🟩\n⬜️🟩🟩⬜️🟩\n⬜️🟩🟩⬜️🟩\n🟩🟩🟩⬜️🟩'
        ]
    expected = [
        {'day': '825', 'name': 'Parole', 'timestamp': 1712522008, 'tries': '4', 'user_id': 456481297, 'user_name': 'Trifase'},
        {'day': '813', 'name': 'Parole', 'timestamp': 1712522008, 'tries': 'X', 'user_id': 456481297, 'user_name': 'Trifase'}
        ]

    def __init__(self, update):
        self._name = "Parole"
        self._category = "Giochi di parole"
        self._date = datetime.date(2023, 9, 30)
        self._day = "635"
        self._emoji = "🇮🇹"
        self._url = "https://par-le.github.io/gioco/"

        self.update = update
        self.raw_text =  self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

        self.has_extra: False
        self.can_lose: True

    @property
    def can_handle_this(self):
        lines = self.raw_text.splitlines()
        _can_handle_this = 'Par🇮🇹le' in lines[0]
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
        'Bandle #597 4/6\n⬛️⬛️⬛️🟩⬜️⬜️\nFound: 10/14 (71.4%)\nCurrent Streak: 1 (max 2)\n#Bandle #Heardle #Wordle \n https://bandle.app/'
        'Bandle #579 x/6\n⬛️⬛️⬛️⬛️⬛️⬛️\nFound: 3/5 (60%)\n#Bandle #Heardle #Wordle \n https://bandle.app/'
        ]
    expected = [
        {'day': '597','name': 'Bandle','timestamp': 1712522008,'tries': '4','user_id': 456481297,'user_name': 'Trifase'},
        {'day': '579','name': 'Bandle','timestamp': 1712522008,'tries': 'X', 'user_id': 456481297, 'user_name': 'Trifase'}
        ]

    def __init__(self, update):
        self._name = "Bandle"
        self._category = "Immagini, giochi e film"
        self._date = datetime.date(2024, 3, 3)
        self._day = "564"
        self._emoji = "🎸"
        self._url = "https://bandle.app/"

        self.update = update
        self.raw_text =  self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

        self.has_extra: False
        self.can_lose: True

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
        '🥇 CHRONO  #749\n\n🟢🟢🟢🟢🟢🟢\n\n⏱: 50.8\n🔥: 3\nhttps://chrono.quest',
        '🥈 CHRONO  #760\n\n🟢🟢🟢🟢⚪️⚪️\n🟢🟢🟢🟢🟢🟢\n\n⏱: 33.3\n🔥: 1\nhttps://chrono.quest',
        '🥉 CHRONO  #748\n\n🟢🟢⚪️⚪️⚪️🟢\n🟢🟢⚪️⚪️🟢🟢\n🟢🟢🟢🟢🟢🟢\n\n⏱: 55.8\n🔥: 2\nhttps://chrono.quest',
        '😬 CHRONO  #748\n\n🟢⚪️🟢⚪️⚪️🟢\n🟢⚪️⚪️⚪️🟢🟢\n🟢⚪️⚪️⚪️🟢🟢\n\n⏱: 81.8\n🔥: 0\nhttps://chrono.quest'
    ]
    expected = [
        {'day': '749', 'name': 'Chrono', 'stars': 9949.2, 'timestamp': 1712522008, 'tries': 1, 'user_id': 456481297, 'user_name': 'Trifase'},
        {'day': '760', 'name': 'Chrono', 'stars': 9966.7, 'timestamp': 1712522008, 'tries': 2, 'user_id': 456481297, 'user_name': 'Trifase'},
        {'day': '748', 'name': 'Chrono', 'stars': 9944.2, 'timestamp': 1712522008, 'tries': 3, 'user_id': 456481297, 'user_name': 'Trifase'},
        {'day': '748', 'name': 'Chrono', 'timestamp': 1712522008, 'tries': 'X', 'user_id': 456481297, 'user_name': 'Trifase'}
    ]

    def __init__(self, update):
        self._name = "Chrono"
        self._category = "Logica"
        self._date = datetime.date(2024, 3, 4)
        self._day = "734"
        self._emoji = "⏱️"
        self._url = "https://chrono.quest"

        self.update = update
        self.raw_text =  self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

        self.has_extra: True
        self.can_lose: True


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
                if line.startswith('⏱'):
                    self.stars = 10_000 - float(line.split(':')[-1].strip())
                    break


@dataclass
class Contexto(Giochino):
    examples = [
        'I played contexto.me #556 and got it in 57 guesses.\n\n🟩🟩 11\n🟨🟨 10\n🟥🟥🟥🟥🟥🟥 36',
        'I played contexto.me #522 and got it in 39 guesses and 1 hints.\n\n🟩 9\n🟨 9\n🟥🟥🟥 22',
        'I played contexto.me #471 and got it in 42 guesses and 15 hints.\n\n🟩🟩 25\n🟨 12\n🟥🟥 20',
        'I played contexto.me #465 but I gave up in 31 guesses and 10 hints.\n\n🟩🟩🟩 22\n🟨 10\n🟥 9'
    ]
    expected = [
        {'day': '556', 'name': 'Contexto', 'timestamp': 1712522008, 'tries': '57', 'user_id': 456481297, 'user_name': 'Trifase'},
        {'day': '522', 'name': 'Contexto', 'timestamp': 1712522008, 'tries': 54, 'user_id': 456481297, 'user_name': 'Trifase'},
        {'day': '471', 'name': 'Contexto', 'timestamp': 1712522008, 'tries': 267, 'user_id': 456481297, 'user_name': 'Trifase'},
        {'day': '465', 'name': 'Contexto', 'timestamp': 1712522008, 'tries': 'X', 'user_id': 456481297, 'user_name': 'Trifase'}
    ]

    def __init__(self, update):
        self._name = "Contexto"
        self._category = "Giochi di parole"
        self._date = datetime.date(2023, 6, 23)
        self._day = "278"
        self._emoji = "🔄"
        self._url = "https://contexto.me"

        self.update = update
        self.raw_text =  self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

        self.has_extra: False
        self.can_lose: True

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
        'Stepdle #536\n16/20 4-4 5-3 6-4 7-5\n⬜️⬜️🟨⬜️\n🟩⬜️🟩⬜️\n🟩⬜️🟩🟩\n🟩🟩🟩🟩\n⬜️🟨⬜️⬜️🟨\n⬜️🟩🟩⬜️🟩\n🟩🟩🟩🟩🟩\n⬜️⬜️⬜️⬜️🟨🟨\n⬜️⬜️🟨🟩⬜️⬜️\n🟩🟩⬜️🟩🟨⬜️\n🟩🟩🟩🟩🟩🟩\n⬜️🟨⬜️🟨⬜️⬜️🟨\n⬜️🟨🟨⬜️⬜️🟨⬜️\n🟨⬜️🟨⬜️⬜️🟨⬜️\n⬜️🟨🟨⬜️⬜️🟩🟨\n🟩🟩🟩🟩🟩🟩🟩',
        'Stepdle #537\n20/20 4-4 5-7 6-5 7-4\n🟨⬜️⬜️⬜️\n⬜️⬜️⬜️🟩\n🟩🟩⬜️🟩\n🟩🟩🟩🟩\n🟨🟩⬜️⬜️🟩\n⬜️🟩🟩⬜️🟩\n⬜️🟩🟩⬜️🟩\n⬜️🟩🟩⬜️🟩\n⬜️🟩🟩⬜️🟩\n🟩🟩🟩⬜️🟩\n🟩🟩🟩🟩🟩\n⬜️⬜️🟨🟨⬜️🟨\n⬜️⬜️🟨⬜️🟩⬜️\n⬜️🟩⬜️🟨⬜️🟨\n🟩🟩⬜️⬜️🟩🟨\n🟩🟩🟩🟩🟩🟩\n⬜️⬜️🟨⬜️⬜️⬜️⬜️\n🟩🟨⬜️⬜️⬜️🟨⬜️\n🟩🟨🟨⬜️⬜️⬜️⬜️\n🟩🟩🟩🟩🟩🟩🟩',
        'Stepdle #536\n20/20 4-6 5-9 6-3 7-2\n⬜️🟨🟨⬜️\n🟨⬜️🟨🟨\n🟩🟩🟩⬜️\n🟩🟩🟩⬜️\n🟩🟩🟩⬜️\n🟩🟩🟩🟩\n⬜️⬜️⬜️⬜️⬜️\n⬜️⬜️⬜️⬜️🟩\n⬜️🟩⬜️⬜️🟩\n⬜️🟨🟨⬜️🟩\n⬜️🟩⬜️⬜️🟩\n🟨🟩⬜️⬜️🟩\n⬜️🟩🟨⬜️🟩\n🟩🟩⬜️🟩🟩\n🟩🟩🟩🟩🟩\n⬜️⬜️⬜️⬜️⬜️🟩\n⬜️🟩🟨⬜️🟨⬜️\n🟩🟩🟩🟩🟩🟩\n⬜️🟨🟨⬜️⬜️🟨⬜️\n⬜️⬜️🟨⬜️🟨🟩🟨'
    ]
    expected = [
        {'day': '536', 'name': 'Stepdle', 'timestamp': 1712522008, 'tries': '16', 'user_id': 456481297, 'user_name': 'Trifase'},
        {'day': '537', 'name': 'Stepdle', 'timestamp': 1712522008, 'tries': '20', 'user_id': 456481297, 'user_name': 'Trifase'},
        {'day': '536', 'name': 'Stepdle', 'timestamp': 1712522008, 'tries': 'X', 'user_id': 456481297, 'user_name': 'Trifase'}


    ]

    def __init__(self, update):
        self._name = "Stepdle"
        self._category = "Giochi di parole"
        self._date = datetime.date(2024, 3, 5)
        self._day = "537"
        self._emoji = "🗼"
        self._url = "https://www.stepdle.com"

        self.update = update
        self.raw_text =  self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

        self.has_extra: False
        self.can_lose: True

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
            self.tries = 'X'


@dataclass
class Waffle(Giochino):
    examples = [
        '#waffle807 1/5\n\n🟩🟩🟩🟩🟩\n🟩⬜️🟩⬜️🟩\n🟩🟩⭐️🟩🟩\n🟩⬜️🟩⬜️🟩\n🟩🟩🟩🟩🟩\n\n🔥 streak: 2\nwafflegame.net',
        '#waffle807 5/5\n\n🟩🟩🟩🟩🟩\n🟩⭐️🟩⭐️🟩\n🟩🟩⭐️🟩🟩\n🟩⭐️🟩⭐️🟩\n🟩🟩🟩🟩🟩\n\n🔥 streak: 1\nwafflegame.net',
        '#waffle629 X/5\n\n🟩🟩🟩🟩🟩\n🟩⬜️🟩⬜️🟩\n🟩🟩🟩🟩🟩\n🟩⬜️🟩⬜️🟩\n🟩⬛️🟩⬛️🟩\n\n💔 streak: 0\nwafflegame.net'
        ]
    expected = [
        {'day': '807', 'name': 'Waffle', 'stars': 1, 'timestamp': 1712522008, 'tries': 14, 'user_id': 456481297, 'user_name': 'Trifase'},
        {'day': '807', 'name': 'Waffle', 'stars': 5, 'timestamp': 1712522008, 'tries': 10, 'user_id': 456481297, 'user_name': 'Trifase'},
        {'day': '629', 'name': 'Waffle', 'stars': 0, 'timestamp': 1712522008, 'tries': 'X', 'user_id': 456481297, 'user_name': 'Trifase'}
    ]

    def __init__(self, update):
        self._name = "Waffle"
        self._category = "Giochi di parole"
        self._date = datetime.date(2023, 6, 23)
        self._day = "518"
        self._emoji = "🧇"
        self._url = "https://wafflegame.net/daily"

        self.update = update
        self.raw_text =  self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

        self.has_extra: False
        self.can_lose: True

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

# qua
@dataclass
class HighFive(Giochino):

    examples = [
        
    ]
    expected = [
        
    ]

    def __init__(self, update):
        self._name = "HighFive"
        self._category = "Giochi di parole"
        self._date = datetime.date(2023, 6, 23)
        self._day = "100"
        self._emoji = "🖐️"
        self._url = "https://highfivegame.app"

        self.update = update
        self.raw_text =  self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

        self.has_extra: False
        self.can_lose: True

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
        self.day = get_day_from_date("HighFive", lines[-1])
        self.tries = str(0 - int(lines[0].split()[3]))
        self.stars = None


@dataclass
class Polygonle(Giochino):

    examples = [
        
    ]
    expected = [
        
    ]

    def __init__(self, update):
        self._name = "Polygonle"
        self._category = "Giochi di parole"
        self._date = datetime.date(2024, 3, 5)
        self._day = "583"
        self._emoji = "🔷"
        self._url = "https://www.polygonle.com"

        self.update = update
        self.raw_text =  self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

        self.has_extra: False
        self.can_lose: True

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

        if punti == "X":
            self.tries = "X"
        elif punti == "🎯":
            self.tries = "1"
        else:
            self.tries = punti


@dataclass
class Connections(Giochino):

    examples = [
        
    ]
    expected = [
        
    ]

    def __init__(self, update):
        self._name = "Connections"
        self._category = "Giochi di parole"
        self._date = datetime.date(2023, 9, 18)
        self._day = "99"
        self._emoji = "🔀"
        self._url = "https://www.nytimes.com/games/connections"

        self.update = update
        self.raw_text =  self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

        self.has_extra: False
        self.can_lose: True

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
        
    ]
    expected = [
        
    ]

    def __init__(self, update):
        self._name = "Squareword"
        self._category = "Giochi di parole"
        self._date = datetime.date(2023, 9, 25)
        self._day = "602"
        self._emoji = "🔠"
        self._url = "https://squareword.org"

        self.update = update
        self.raw_text =  self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

        self.has_extra: False
        self.can_lose: True

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
        
    ]
    expected = [
        
    ]

    def __init__(self, update):
        self._name = "Worldle"
        self._category = "Geografia e Mappe"
        self._date = datetime.date(2023, 6, 23)
        self._day = "518"
        self._emoji = "🗺️"
        self._url = "https://worldle.teuteuf.fr"

        self.update = update
        self.raw_text =  self.update.message.text

        if self.can_handle_this:
            self.parse()

        self.has_extra: False
        self.can_lose: True

    @property
    def can_handle_this(self):
        lines = self.raw_text.splitlines()
        _can_handle_this = 'Worldle' in lines[0]
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
        bussola = text.count(b"\xf0\x9f\xa7\xad".decode("utf-8"))       # 🧭
        stars = text.count(b"\xe2\xad\x90".decode("utf-8"))             # ⭐️
        flag = text.count(b"\xf0\x9f\x9a\xa9".decode("utf-8"))          # 🚩
        abc = text.count(b"\xf0\x9f\x94\xa4".decode("utf-8"))           # 🔤
        language = text.count(b"\xf0\x9f\x97\xa3".decode("utf-8"))      # 🗣
        population = text.count(b"\xf0\x9f\x91\xab".decode("utf-8"))    # 👫
        coin = text.count(b"\xf0\x9f\xaa\x99".decode("utf-8"))          # 🪙
        cityscape = text.count(b"\xf0\x9f\x8f\x99".decode("utf-8"))     # 🏙
        area = text.count(b"\xf0\x9f\x93\x90".decode("utf-8"))          # 📐
        self.stars = bussola + stars + flag + abc + language + population + coin + cityscape + area


@dataclass
class Tradle(Giochino):

    examples = [
        
    ]
    expected = [
        
    ]

    def __init__(self, update):
        self._name = "Tradle"
        self._category = "Geografia e Mappe"
        self._date = datetime.date(2023, 6, 23)
        self._day = "474"
        self._emoji = "🚢"
        self._url = "https://oec.world/en/tradle"

        self.update = update
        self.raw_text =  self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

        self.has_extra: False
        self.can_lose: True

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
        
    ]
    expected = [
        
    ]

    def __init__(self, update):
        self._name = "Flagle"
        self._category = "Geografia e Mappe"
        self._date = datetime.date(2023, 9, 8)
        self._day = "564"
        self._emoji = "🏁"
        self._url = "https://www.flagle.io"

        self.update = update
        self.raw_text =  self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

        self.has_extra: False
        self.can_lose: True

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
        
    ]
    expected = [
        
    ]

    def __init__(self, update):
        self._name = "Globle"
        self._category = "Geografia e Mappe"
        self._date = datetime.date(2023, 6, 23)
        self._day = "200"
        self._emoji = "🌍"
        self._url = "https://globle-game.com"

        self.update = update
        self.raw_text =  self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

        self.has_extra: False
        self.can_lose: True

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
        self.day = get_day_from_date("Globle", lines[0])
        for line in lines:
            if "=" in line:
                self.tries = line.split("=")[-1][1:]
        self.stars = None


@dataclass
class WhereTaken(Giochino):

    examples = [
        
    ]
    expected = [
        
    ]

    def __init__(self, update):
        self._name = "WhereTaken"
        self._category = "Geografia e Mappe"
        self._date = datetime.date(2023, 6, 23)
        self._day = "117"
        self._emoji = "📸"
        self._url = "http://wheretaken.teuteuf.fr"

        self.update = update
        self.raw_text =  self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

        self.has_extra: False
        self.can_lose: True

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

    examples = [
        
    ]
    expected = [
        
    ]

    def __init__(self, update):
        self._name = "Cloudle"
        self._category = "Geografia e Mappe"
        self._date = datetime.date(2023, 6, 23)
        self._day = "449"
        self._emoji = "🌦️"
        self._url = "https://cloudle.app"

        self.update = update
        self.raw_text =  self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

        self.has_extra: False
        self.can_lose: True

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
        self.day = get_day_from_date("Cloudle", datetime.date.today())
        self.tries = first_line[-1].split("/")[0]
        self.stars = None


@dataclass
class GuessTheGame(Giochino):

    examples = [
        
    ]
    expected = [
        
    ]

    def __init__(self, update):
        self._name = "GuessTheGame"
        self._category = "Immagini, giochi e film"
        self._date = datetime.date(2023, 6, 23)
        self._day = "405"
        self._emoji = "🎮"
        self._url = "https://guessthe.game"

        self.update = update
        self.raw_text =  self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

        self.has_extra: False
        self.can_lose: True

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
        
    ]
    expected = [
        
    ]

    def __init__(self, update):
        self._name = "Framed"
        self._category = "Immagini, giochi e film"
        self._date = datetime.date(2023, 6, 23)
        self._day = "469"
        self._emoji = "🎞"
        self._url = "https://framed.wtf"

        self.update = update
        self.raw_text =  self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

        self.has_extra: False
        self.can_lose: True

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
class TimeGuesser(Giochino):

    examples = [
        
    ]
    expected = [
        
    ]

    def __init__(self, update):
        self._name = "TimeGuesser"
        self._category = "Immagini, giochi e film"
        self._date = datetime.date(2023, 11, 27)
        self._day = "179"
        self._emoji = "📅"
        self._url = "https://timeguessr.com"

        self.update = update
        self.raw_text =  self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

        self.has_extra: False
        self.can_lose: True

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
        
    ]
    expected = [
        
    ]

    def __init__(self, update):
        self._name = "Moviedle"
        self._category = "Immagini, giochi e film"
        self._date = datetime.date(2023, 6, 23)
        self._day = "200"
        self._emoji = "🎥"
        self._url = "https://moviedle.app"

        self.update = update
        self.raw_text =  self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

        self.has_extra: False
        self.can_lose: True

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
        self.day = get_day_from_date("Moviedle", first_line[-1])
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
        
    ]
    expected = [
        
    ]

    def __init__(self, update):
        self._name = "Picsey"
        self._category = "Immagini, giochi e film"
        self._date = datetime.date(2023, 9, 25)
        self._day = "100"
        self._emoji = "🪟"
        self._url = "https://picsey.io"

        self.update = update
        self.raw_text =  self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

        self.has_extra: False
        self.can_lose: True

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
        self.day = get_day_from_date("Picsey", date)
        points = lines[2].split("p/")[0]
        # Picsey uses positive poits, from 0 to 100. We as usual save 100-n and then revert it when printing the results.
        self.tries = 100 - int(points)
        if int(points) == 0:
            self.tries = "X"
        self.stars = None


@dataclass
class Colorfle(Giochino):

    examples = [
        
    ]
    expected = [
        
    ]

    def __init__(self, update):
        self._name = "Colorfle"
        self._category = "Immagini, giochi e film"
        self._date = datetime.date(2024, 3, 5)
        self._day = "679"
        self._emoji = "🎨"
        self._url = "https://colorfle.com"

        self.update = update
        self.raw_text =  self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

        self.has_extra: False
        self.can_lose: True

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
        
    ]
    expected = [
        
    ]

    def __init__(self, update):
        self._name = "Murdle"
        self._category = "Logica"
        self._date = datetime.date(2023, 6, 23)
        self._day = "1"
        self._emoji = "🔪"
        self._url = "https://murdle.com"

        self.update = update
        self.raw_text =  self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

        self.has_extra: False
        self.can_lose: True

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
        self.day = get_day_from_date("Murdle", day)
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
        
    ]
    expected = [
        
    ]

    def __init__(self, update):
        self._name = "Rotaboxes"
        self._category = "Logica"
        self._date = datetime.date(2024, 3, 5)
        self._day = "497"
        self._emoji = "🧩"
        self._url = "https://rotaboxes.com"

        self.update = update
        self.raw_text =  self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

        self.has_extra: False
        self.can_lose: True

    @property
    def can_handle_this(self):
        lines = self.raw_text.splitlines()
        _can_handle_this = len(lines) >= 3 and "rotabox.es" in lines[3] and "clicks:" in lines[1]
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
        
    ]
    expected = [
        
    ]

    def __init__(self, update):
        self._name = "Nerdle"
        self._category = "Logica"
        self._date = datetime.date(2023, 9, 21)
        self._day = "610"
        self._emoji = "🤓"
        self._url = "https://nerdlegame.com"

        self.update = update
        self.raw_text =  self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

        self.has_extra: False
        self.can_lose: True

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
        
    ]
    expected = [
        
    ]

    def __init__(self, update):
        self._name = "Metazooa"
        self._category = "Scienza"
        self._date = datetime.date(2023, 10, 7)
        self._day = "68"
        self._emoji = "🐢"
        self._url = "https://metazooa.com/game"

        self.update = update
        self.raw_text =  self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

        self.has_extra: False
        self.can_lose: True

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
        
    ]
    expected = [
        
    ]

    def __init__(self, update):
        self._name = "Metaflora"
        self._category = "Scienza"
        self._date = datetime.date(2023, 10, 28)
        self._day = "28"
        self._emoji = "🌿"
        self._url = "https://flora.metazooa.com/game"

        self.update = update
        self.raw_text =  self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

        self.has_extra: False
        self.can_lose: True

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
        
    ]
    expected = [
        
    ]

    def __init__(self, update):
        self._name = "Angle"
        self._category = "Logica"
        self._date = datetime.date(2023, 10, 28)
        self._day = "494"
        self._emoji = "📐"
        self._url = "https://angle.wtf"

        self.update = update
        self.raw_text =  self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

        self.has_extra: False
        self.can_lose: True

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
        
    ]
    expected = [
        
    ]

    def __init__(self, update):
        self._name = "TempoIndovinr"
        self._category = "Immagini, giochi e film"
        self._date = datetime.date(2023, 11, 17)
        self._day = "5"
        self._emoji = "🗺️"
        self._url = "https://jacopofarina.eu/experiments/tempoindovinr"

        self.update = update
        self.raw_text =  self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

        self.has_extra: False
        self.can_lose: True

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
        
    ]
    expected = [
        
    ]

    def __init__(self, update):
        self._name = "Chronophoto"
        self._category = "Immagini, giochi e film"
        self._date = datetime.date(2024, 3, 6)
        self._day = "100"
        self._emoji = "⏳"
        self._url = "https://www.chronophoto.app/daily.html"

        self.update = update
        self.raw_text =  self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

        self.has_extra: False
        self.can_lose: True

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
        self.day = get_day_from_date("Chronophoto", first_line[-1])
        self.tries = 5_000 - int(first_line[5])
        if self.tries == 0:
            self.tries = "X"
        self.stars = None


@dataclass
class Travle(Giochino):

    examples = [
        
    ]
    expected = [
        
    ]

    def __init__(self, update):
        self._name = "Travle"
        self._category = "Geografia e Mappe"
        self._date = datetime.date(2023, 11, 30)
        self._day = "351"
        self._emoji = "🧭"
        self._url = "https://travle.earth"

        self.update = update
        self.raw_text =  self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

        self.has_extra: False
        self.can_lose: True

    @property
    def can_handle_this(self):
        lines = self.raw_text.splitlines()
        _can_handle_this = "#travle" in lines[0] and "travle.earth" in lines[-1]
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
        
    ]
    expected = [
        
    ]

    def __init__(self, update):
        self._name = "TravleITA"
        self._category = "Geografia e Mappe"
        self._date = datetime.date(2024, 2, 29)
        self._day = "256"
        self._emoji = "👢"
        self._url = "https://travle.earth/ita"

        self.update = update
        self.raw_text =  self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

        self.has_extra: False
        self.can_lose: True

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
        
    ]
    expected = [
        
    ]

    def __init__(self, update):
        self._name = "NerdleCross"
        self._category = "Logica"
        self._date = datetime.date(2023, 12, 12)
        self._day = "198"
        self._emoji = "🧮"
        self._url = "https://nerdlegame.com/crossnerdle"

        self.update = update
        self.raw_text =  self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

        self.has_extra: False
        self.can_lose: True

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
        
    ]
    expected = [
        
    ]

    def __init__(self, update):
        self._name = "DominoFit"
        self._category = "Logica"
        self._date = datetime.date(2024, 2, 18)
        self._day = "1"
        self._emoji = "🃏"
        self._url = "https://dominofit.isotropic.us"

        self.update = update
        self.raw_text =  self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

        self.has_extra: False
        self.can_lose: True

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

    examples = [
        
    ]
    expected = [
        
    ]

    def __init__(self, update):
        self._name = "FoodGuessr"
        self._category = "Geografia e Mappe"
        self._date = datetime.date(2024, 3, 9)
        self._day = "200"
        self._emoji = "🍝"
        self._url = "https://foodguessr.com"

        self.update = update
        self.raw_text =  self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

        self.has_extra: False
        self.can_lose: True

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
        self.day = get_day_from_date("FoodGuessr", datetime.date.today())
        points = lines[4].split()[2].replace(",", "").replace(".", "")
        self.tries = 15_000 - int(points)
        self.stars = None


@dataclass
class Spellcheck(Giochino):

    examples = [
        
    ]
    expected = [
        
    ]

    def __init__(self, update):
        self._name = "Spellcheck"
        self._category = "Logica"
        self._date = datetime.date(2024, 3, 9)
        self._day = "57"
        self._emoji = "👂"
        self._url = "https://spellcheck.xyz"

        self.update = update
        self.raw_text =  self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

        self.has_extra: False
        self.can_lose: True

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
        
    ]
    expected = [
        
    ]

    def __init__(self, update):
        self._name = "Spotle"
        self._category = "Immagini, giochi e film"
        self._date = datetime.date(2024, 3, 22)
        self._day = "695"
        self._emoji = "🎧"
        self._url = "https://spotle.io/"

        self.update = update
        self.raw_text =  self.update.message.text

        self.user_name = None
        self.user_id = None
        self.timestamp = None
        self.day = None
        self.tries = None
        self.stars = None

        if self.can_handle_this:
            self.parse()

        self.has_extra: False
        self.can_lose: True

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
        punteggio_bonificato = ''
        for char in punteggio:
            if char in ["⬛", "🟥", "🟩", "⬜"]:
                punteggio_bonificato += char
        if "🟩" not in punteggio or "❌" in punteggio:
            self.tries = "X"
        else:
            self.tries = str(punteggio_bonificato.index("🟩") + 1)




def generate_sample_update(text):
    updict = {
        'message': {
            'channel_chat_created': False,
            'chat': {
                'id': -1001180175690,
                'title': 'Testing some bots',
                'type': 'supergroup'
                },
            'date': 1712522008,
            'delete_chat_photo': False,
            'from': {
                    'first_name': 'Trifase',
                    'id': 456481297,
                    'is_bot': False,
                    'is_premium': True,
                    'language_code': 'en',
                    'username': 'Trifase'
                    },
            'group_chat_created': False,
            'message_id': 19378,
            'message_thread_id': 19376,
            'text': text
        },
        'update_id': 922829533}

    # Creo un fake update
    bot = Bot("123456789")
    upd = Update.de_json(updict, bot)
    return upd

giochini = [cls_obj for _, cls_obj in inspect.getmembers(sys.modules[__name__], inspect.isclass) if cls_obj.__module__ == sys.modules[__name__].__name__ and cls_obj.__base__ == Giochino and cls_obj.examples]
# giochini = [Wordle, Parole, Bandle, Chrono]
for gioco in giochini:
    for i in range(len(gioco.examples)):
        update = generate_sample_update(gioco.examples[i])
        giochino = gioco(update)
        print(f'[{i}] ==== {giochino._name} ====')
        print(f'info = {giochino.info}')
        print(f'expected = {giochino.expected[i]}')
        print(f'punteggio = {giochino.punteggio}')
        assert(all(x in giochino.punteggio.items() for x in giochino.expected[i].items()))
        print('test_passed ✅')
        print()

missing_conf = [name for name, cls_obj in inspect.getmembers(sys.modules[__name__], inspect.isclass) if cls_obj.__module__ == sys.modules[__name__].__name__ and cls_obj.__base__ == Giochino and not cls_obj.examples]
print(f'Mancano ancora da configurare: ({len(missing_conf)})')
print(missing_conf)


#fake update for testing
# text = '#Worldle #800 (31.03.2024) 1/6 (100%)\n 🟩🟩🟩🟩🟩🎉\n🧭⭐️🚩🗣️🪙📐\nhttps://worldle.teuteuf.fr'
# update = generate_sample_update(text)

# for giochino in giochini:
#     giochino = giochino(update)
#     if giochino.can_handle_this:
#         pprint.pprint(giochino.info)
#         pprint.pprint(giochino.punteggio)