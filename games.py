import datetime
from telegram import Update, Bot
import time
from dataclassy import dataclass

import inspect
import sys
import pprint

# from utils import get_day_from_date, is_connection_completed, time_from_emoji

"""Un tentativo timido di convertire giochini, informazioni, parser e test in un'unica classe"""

            # 'text': 'Wordle 1.022 2/6\n'
            #             '\n'
            #             '🟨⬛️🟨⬛️⬛️\n'
            #             '🟩🟩🟩🟩🟩'

            # 'text': '#Worldle #800 (31.03.2024) 1/6 '
            #         '(100%)\n'
            #         '🟩🟩🟩🟩🟩🎉\n'
            #         '🧭⭐️🚩🗣️🪙📐\n'
            #         'https://worldle.teuteuf.fr'



@dataclass
class Giochino:
    # Things about the game itself
    _name: str
    _emoji: str
    _category: str
    _date: datetime.date
    _day: str
    _url: str
    # Input
    update: str
    raw_text: str
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
            "timestamp": self.timestamp,
            "game": self._name,
            "user_name": self.user_name,
            "user_id": self.user_id,
            "tries": self.tries,
            "stars": self.stars,
            "is_lost": self.is_lost
        }

@dataclass
class Wordle(Giochino):
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

    @property
    def can_handle_this(self):
        lines = self.raw_text.splitlines()
        _can_handle_this = "CHRONO #" in lines[0] and "https://chrono.ques" in lines[-1]
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
class Worldle(Giochino):
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





def generate_sample_update(text):
    updict = {
        'message': {
            'channel_chat_created': False,
            'chat': {
                'id': -1001180175690,
                'title': 'Testing some bots',
                'type': 'supergroup'
                },
            'date': 1712444756,
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

giochini = [cls_obj for _, cls_obj in inspect.getmembers(sys.modules[__name__], inspect.isclass) if cls_obj.__module__ == sys.modules[__name__].__name__ and cls_obj.__base__ == Giochino]

#fake update for testing
text = '#Worldle #800 (31.03.2024) 1/6 (100%)\n 🟩🟩🟩🟩🟩🎉\n🧭⭐️🚩🗣️🪙📐\nhttps://worldle.teuteuf.fr'
update = generate_sample_update(text)

for giochino in giochini:
    giochino = giochino(update)
    if giochino.can_handle_this:
        pprint.pprint(giochino.info)
        pprint.pprint(giochino.punteggio)