import peewee
import datetime

TOKEN = '5960233207:AAF_s8D4DgRm3YdA5n8vMtZibS3nWSSaR5w'
DBPATH = "sqlite.db"

db = peewee.SqliteDatabase(DBPATH)

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

GAMES = {
    'Worldle': '🗺️',
    'Parole': '🇮🇹',
    'Contexto': '🔄',
    'Tradle': '🚢',
    'GuessTheGame': '🎮',
    'Wordle': '🆒',
    'Globle': '🌍',
    'Flagle': '🏁'
}

MEDALS = {
    1: '🥇',
    2: '🥈',
    3: '🥉'
}

DAYS = {
    'Wordle': {
        'date': datetime.date(2023, 6, 23),
        'day': '734'
    },
    'Parole': {
        'date': datetime.date(2023, 6, 23),
        'day': '535'
    },
    'Worldle': {
        'date': datetime.date(2023, 6, 23),
        'day': '518'
    },
    'Contexto': {
        'date': datetime.date(2023, 6, 23),
        'day': '278'
    },
    'Tradle': {
        'date': datetime.date(2023, 6, 23),
        'day': '474'
    },
    'GuessTheGame': {
        'date': datetime.date(2023, 6, 23),
        'day': '405'
    },
    'Flagle': {
        'date': datetime.date(2023, 6, 23),
        'day': '465'
    },
    'Globle': {
        'date': datetime.date(2023, 6, 23),
        'day': '200'
    }
}

def get_day_from_date(game: str, date: datetime.datetime | str) -> str:
    if isinstance(date, str) and game == 'Globle':
        date = datetime.datetime.strptime(date, '🌎 %b %d, %Y 🌍')

    days_difference = DAYS[game]['date'] - date
    return str(int(DAYS[game]['day']) - days_difference.days)

