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
