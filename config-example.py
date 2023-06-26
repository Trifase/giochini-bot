import peewee
import datetime

TOKEN = 'token'
DBPATH = "sqlite.db"
ID_GIOCHINI = 0
ID_TESTING = 0

db = peewee.SqliteDatabase(DBPATH)

MEDALS = {
    1: '🥇',
    2: '🥈',
    3: '🥉'
}

GAMES = {
    'Wordle': {
        'date': datetime.date(2023, 6, 23),
        'day': '734',
        'emoji': '🆒',
        'url': 'https://www.nytimes.com/games/wordle/index.html'
    },
    'Parole': {
        'date': datetime.date(2023, 6, 23),
        'day': '535',
        'emoji': '🇮🇹',
        'url': 'https://pietroppeter.github.io/wordle-it/'
    },
    'Worldle': {
        'date': datetime.date(2023, 6, 23),
        'day': '518',
        'emoji': '🗺️',
        'url': 'https://worldle.teuteuf.fr/'
    },
    'Contexto': {
        'date': datetime.date(2023, 6, 23),
        'day': '278',
        'emoji': '🔄',
        'url': 'https://contexto.me/'
    },
    'Tradle': {
        'date': datetime.date(2023, 6, 23),
        'day': '474',
        'emoji': '🚢',
        'url': 'https://oec.world/en/tradle/'
    },
    'GuessTheGame': {
        'date': datetime.date(2023, 6, 23),
        'day': '405',
        'emoji': '🎮',
        'url': 'https://guessthe.game/'
    },
    'Flagle': {
        'date': datetime.date(2023, 6, 23),
        'day': '465',
        'emoji': '🏁',
        'url': 'https://flagle-game.com/'
    },
    'Globle': {
        'date': datetime.date(2023, 6, 23),
        'day': '200',
        'emoji': '🌍',
        'url': 'https://globle-game.com/'
    },
    'WhereTaken': {
        'date': datetime.date(2023, 6, 23),
        'day': '117',
        'emoji': '📸',
        'url': 'http://wheretaken.teuteuf.fr'
    },
    'Waffle': {
        'date': datetime.date(2023, 6, 23),
        'day': '518',
        'emoji': '🧇',
        'url': 'https://wafflegame.net/daily'
    },
    'Cloudle': {
        'date': datetime.date(2023, 6, 23),
        'day': '449',
        'emoji': '🌦️',
        'url': 'https://cloudle.app'
    },
}

class Punteggio(peewee.Model):
    date = peewee.DateField()
    timestamp = peewee.IntegerField()
    chat_id = peewee.IntegerField()
    user_id = peewee.IntegerField()
    user_name  = peewee.TextField()
    game = peewee.TextField()
    day = peewee.TextField()
    tries = peewee.IntegerField()
    extra = peewee.TextField(null=True)

    class Meta:
        database = db
        table_name = 'punteggi'
        primary_key = False

class Punti(peewee.Model):
    user_id = peewee.IntegerField(unique=True)
    user_name  = peewee.TextField()
    punti = peewee.IntegerField()

    class Meta:
        database = db
        table_name = 'punti'
        primary_key = False