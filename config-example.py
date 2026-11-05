import peewee

TOKEN = 0
DBPATH = "sqlite.db"
DBPATH_TEST = "tests.db"
ID_GIOCHINI = 0
ID_TESTING = 0
ID_BOTCENTRAL = 0
BACKUP_DEST = 0
ADMIN_ID = 0

# LLM API configuration for /ask command (OpenAI or Gemini)
LLM_PROVIDER = "openai"  # "openai" oppure "gemini"
OPENAI_API_KEY = "sk-..."  # Chiave OpenAI (default model: gpt-4o-mini)
OPENAI_MODEL = "gpt-4o-mini"
GEMINI_API_KEY = ""
GEMINI_MODEL = "gemini-3.5-flash-lite"

HEARTBEAT_ID = ""
STAR_SYMBOL = "⭐"
ELSE_MEDAL = "✔️ "
POOP_MEDAL = "💩 "

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


class PuntiBonus(peewee.Model):
    id = peewee.AutoField()
    date = peewee.DateField()
    user_id = peewee.IntegerField()
    user_name = peewee.TextField()
    punti = peewee.IntegerField()
    reason = peewee.TextField(null=True)
    assigned_by = peewee.IntegerField(null=True)
    timestamp = peewee.IntegerField()

    class Meta:
        database = db
        table_name = "punti_bonus"


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


# ==========================================
# GIOCO BONUS DEL GIORNO (JOLLY)
# ==========================================
BONUS_GAME_ENABLED = True
# Lista pesata dei moltiplicatori [(moltiplicatore, peso)]
# 2x più comune (50%), 3x intermedio (35%), 4x più raro ma non tantissimo (15%)
BONUS_GAME_MULTIPLIERS = [
    (2, 50),
    (3, 35),
    (4, 15),
]
BONUS_GAME_NO_REPEAT_DAYS = 7


class GiocoBonus(peewee.Model):
    date = peewee.DateField(unique=True)
    game = peewee.TextField()
    multiplier = peewee.IntegerField()

    class Meta:
        database = db
        table_name = "gioco_bonus"
