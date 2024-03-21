import datetime

import peewee

TOKEN = 0
DBPATH = "sqlite.db"
DBPATH_TEST = "tests.db"
ID_GIOCHINI = 0
ID_TESTING = 0
ID_BOTCENTRAL = 0
BACKUP_DEST = 0
ADMIN_ID = 0

db = peewee.SqliteDatabase(DBPATH)
db_test = peewee.SqliteDatabase(DBPATH_TEST)

MEDALS = {1: "🥇 ", 2: "🥈 ", 3: "🥉 "}

GAMES = {
    "Wordle": {
        "category": "Giochi di parole",
        "date": datetime.date(2023, 6, 23),
        "day": "734",
        "emoji": "🆒",
        "url": "https://www.nytimes.com/games/wordle/index.html",
    },
    "Parole": {
        "category": "Giochi di parole",
        "date": datetime.date(2023, 9, 30),
        "day": "635",
        "emoji": "🇮🇹",
        "url": "https://par-le.github.io/gioco/",
    },
    "Bandle": {
        "category": "Immagini, giochi e film",
        "date": datetime.date(2024, 3, 3),
        "day": "564",
        "emoji": "🎛️",
        "url": "https://bandle.app/",
    },
    "Chrono": {
        "category": "Logica",
        "date": datetime.date(2024, 3, 4),
        "day": "734",
        "emoji": "🎛️",
        "url": "https://chrono.quest",
    },
    "Contexto": {
        "category": "Giochi di parole",
        "date": datetime.date(2023, 6, 23),
        "day": "278",
        "emoji": "🔄",
        "url": "https://contexto.me",
    },
    "Waffle": {
        "category": "Giochi di parole",
        "date": datetime.date(2023, 6, 23),
        "day": "518",
        "emoji": "🧇",
        "url": "https://wafflegame.net/daily",
    },
    "HighFive": {
        "category": "Giochi di parole",
        "date": datetime.date(2023, 6, 23),
        "day": "100",
        "emoji": "🖐️",
        "url": "https://highfivegame.app",
    },
    "Connections": {
        "category": "Giochi di parole",
        "date": datetime.date(2023, 9, 18),
        "day": "99",
        "emoji": "🔀",
        "url": "https://www.nytimes.com/games/connections",
    },
    "Squareword": {
        "category": "Giochi di parole",
        "date": datetime.date(2023, 9, 25),
        "day": "602",
        "emoji": "🔠",
        "url": "https://squareword.org",
    },
    "Worldle": {
        "category": "Geografia e Mappe",
        "date": datetime.date(2023, 6, 23),
        "day": "518",
        "emoji": "🗺️",
        "url": "https://worldle.teuteuf.fr",
    },
    "Tradle": {
        "category": "Geografia e Mappe",
        "date": datetime.date(2023, 6, 23),
        "day": "474",
        "emoji": "🚢",
        "url": "https://oec.world/en/tradle",
    },
    "Flagle": {
        "category": "Geografia e Mappe",
        "date": datetime.date(2023, 9, 8),
        "day": "564",
        "emoji": "🏁",
        "url": "https://www.flagle.io",
    },
    "Globle": {
        "category": "Geografia e Mappe",
        "date": datetime.date(2023, 6, 23),
        "day": "200",
        "emoji": "🌍",
        "url": "https://globle-game.com",
    },
    "WhereTaken": {
        "category": "Geografia e Mappe",
        "date": datetime.date(2023, 6, 23),
        "day": "117",
        "emoji": "📸",
        "url": "http://wheretaken.teuteuf.fr",
    },
    "Cloudle": {
        "category": "Geografia e Mappe",
        "date": datetime.date(2023, 6, 23),
        "day": "449",
        "emoji": "🌦️",
        "url": "https://cloudle.app",
    },
    "GuessTheGame": {
        "category": "Immagini, giochi e film",
        "date": datetime.date(2023, 6, 23),
        "day": "405",
        "emoji": "🎮",
        "url": "https://guessthe.game",
    },
    "Framed": {
        "category": "Immagini, giochi e film",
        "date": datetime.date(2023, 6, 23),
        "day": "469",
        "emoji": "🎞",
        "url": "https://framed.wtf",
    },
    "TimeGuesser": {
        "category": "Immagini, giochi e film",
        "date": datetime.date(2023, 11, 27),
        "day": "179",
        "emoji": "📅",
        "url": "https://timeguessr.com",
    },
    "Moviedle": {
        "category": "Immagini, giochi e film",
        "date": datetime.date(2023, 6, 23),
        "day": "200",
        "emoji": "🎥",
        "url": "https://moviedle.app",
    },
    "Picsey": {
        "category": "Immagini, giochi e film",
        "date": datetime.date(2023, 9, 25),
        "day": "100",
        "emoji": "🪟",
        "url": "https://picsey.io",
    },
    "Murdle": {
        "category": "Logica",
        "date": datetime.date(2023, 6, 23),
        "day": "1",
        "emoji": "🔪",
        "url": "https://murdle.com",
    },
    "Nerdle": {
        "category": "Logica",
        "date": datetime.date(2023, 9, 21),
        "day": "610",
        "emoji": "🤓",
        "url": "https://nerdlegame.com",
    },
    "Metazooa": {
        "category": "Scienza",
        "date": datetime.date(2023, 10, 7),
        "day": "68",
        "emoji": "🐢",
        "url": "https://metazooa.com/game",
    },
    "Metaflora": {
        "category": "Scienza",
        "date": datetime.date(2023, 10, 28),
        "day": "28",
        "emoji": "🌿",
        "url": "https://flora.metazooa.com/game",
    },
    "Angle": {
        "category": "Logica",
        "date": datetime.date(2023, 10, 28),
        "day": "494",
        "emoji": "🧭",
        "url": "https://angle.wtf",
    },
    "TempoIndovinr": {
        "category": "Immagini, giochi e film",
        "date": datetime.date(2023, 11, 17),
        "day": "5",
        "emoji": "🗺️",
        "url": "https://jacopofarina.eu/experiments/tempoindovinr",
    },
    "Travle": {
        "category": "Geografia e Mappe",
        "date": datetime.date(2023, 11, 30),
        "day": "351",
        "emoji": "🧭",
        "url": "https://travle.earth",
    },
    "TravleITA": {
        "category": "Geografia e Mappe",
        "date": datetime.date(2024, 2, 29),
        "day": "256",
        "emoji": "👢",
        "url": "https://travle.earth/ita",
    },
    "NerdleCross": {
        "category": "Logica",
        "date": datetime.date(2023, 12, 12),
        "day": "198",
        "emoji": "🧮",
        "url": "https://nerdlegame.com/crossnerdle",
    },
    "DominoFit": {
        "category": "Logica",
        "date": datetime.date(2024, 2, 18),
        "day": "1",
        "emoji": "🃏",
        "url": "https://dominofit.isotropic.us",
    },
}


class Punteggio(peewee.Model):
    date = peewee.DateField()
    timestamp = peewee.IntegerField()
    chat_id = peewee.IntegerField()
    user_id = peewee.IntegerField()
    user_name = peewee.TextField()
    game = peewee.TextField()
    day = peewee.TextField()
    tries = peewee.IntegerField()
    extra = peewee.TextField(null=True)
    streak = peewee.IntegerField(null=True)
    lost = peewee.BooleanField(null=True)

    class Meta:
        database = db
        table_name = "punteggi"
        primary_key = peewee.CompositeKey("timestamp", "user_name", "game", "day")


class Punti(peewee.Model):
    date = peewee.DateField()
    user_id = peewee.IntegerField()
    user_name = peewee.TextField()
    punti = peewee.IntegerField()

    class Meta:
        database = db
        table_name = "punti"
        primary_key = peewee.CompositeKey("date", "user_id")


class Medaglia(peewee.Model):
    date = peewee.DateField()
    timestamp = peewee.IntegerField()
    chat_id = peewee.IntegerField()
    user_id = peewee.IntegerField()
    user_name = peewee.TextField()
    gold = peewee.IntegerField(null=True)
    silver = peewee.IntegerField(null=True)
    bronze = peewee.IntegerField(null=True)
    last = peewee.IntegerField(null=True)
    special = peewee.IntegerField(null=True)

    class Meta:
        database = db
        table_name = "medaglie"
        primary_key = peewee.CompositeKey("timestamp", "user_id")
