import peewee

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