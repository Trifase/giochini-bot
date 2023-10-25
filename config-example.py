import peewee
import datetime

TOKEN = "token"
DBPATH = "sqlite.db"
ID_GIOCHINI = 0
ID_TESTING = 0
BACKUP_DEST = 0
ADMIN_ID = 0

db = peewee.SqliteDatabase(DBPATH)

MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}

GAMES = {
    "Wordle": {
        "date": datetime.date(2023, 6, 23),
        "day": "734",
        "emoji": "🆒",
        "url": "https://www.nytimes.com/games/wordle/index.html",
    },
    "Parole": {
        "date": datetime.date(2023, 6, 23),
        "day": "535",
        "emoji": "🇮🇹",
        "url": "https://pietroppeter.github.io/wordle-it",
    },
    "Worldle": {
        "date": datetime.date(2023, 6, 23),
        "day": "518",
        "emoji": "🗺️",
        "url": "https://worldle.teuteuf.fr",
    },
    "Contexto": {
        "date": datetime.date(2023, 6, 23),
        "day": "278",
        "emoji": "🔄",
        "url": "https://contexto.me",
    },
    "Tradle": {
        "date": datetime.date(2023, 6, 23),
        "day": "474",
        "emoji": "🚢",
        "url": "https://oec.world/en/tradle",
    },
    "GuessTheGame": {
        "date": datetime.date(2023, 6, 23),
        "day": "405",
        "emoji": "🎮",
        "url": "https://guessthe.game",
    },
    "Flagle": {
        "date": datetime.date(2023, 9, 8),
        "day": "564",
        "emoji": "🏁",
        "url": "https://www.flagle.io",
    },
    "Globle": {
        "date": datetime.date(2023, 6, 23),
        "day": "200",
        "emoji": "🌍",
        "url": "https://globle-game.com",
    },
    "WhereTaken": {
        "date": datetime.date(2023, 6, 23),
        "day": "117",
        "emoji": "📸",
        "url": "http://wheretaken.teuteuf.fr",
    },
    "Waffle": {
        "date": datetime.date(2023, 6, 23),
        "day": "518",
        "emoji": "🧇",
        "url": "https://wafflegame.net/daily",
    },
    "Cloudle": {
        "date": datetime.date(2023, 6, 23),
        "day": "449",
        "emoji": "🌦️",
        "url": "https://cloudle.app",
    },
    "HighFive": {
        "date": datetime.date(2023, 6, 23),
        "day": "100",
        "emoji": "🖐️",
        "url": "https://highfivegame.app",
    },
    "Framed": {
        "date": datetime.date(2023, 6, 23),
        "day": "469",
        "emoji": "🎞",
        "url": "https://framed.wtf/",
    },
    "TimeGuesser": {
        "date": datetime.date(2023, 9, 10),
        "day": "121",
        "emoji": "📅",
        "url": "https://timeguessr.com",
    },
    "Moviedle": {
        "date": datetime.date(2023, 6, 23),
        "day": "200",
        "emoji": "🎥",
        "url": "https://moviedle.app",
    },
    "Murdle": {
        "date": datetime.date(2023, 6, 23),
        "day": "1",
        "emoji": "🔪",
        "url": "https://murdle.com",
    },
    "Connections": {
        "date": datetime.date(2023, 9, 18),
        "day": "99",
        "emoji": "🔀",
        "url": "https://www.nytimes.com/games/connections",
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

    class Meta:
        database = db
        table_name = "punteggi"
        primary_key = False


class Punti(peewee.Model):
    user_id = peewee.IntegerField(unique=True)
    user_name = peewee.TextField()
    punti = peewee.IntegerField()

    class Meta:
        database = db
        table_name = "punti"
        primary_key = False
