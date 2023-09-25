import datetime
import peewee

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext.filters import MessageFilter

from config import GAMES, Punteggio


class GameFilter(MessageFilter):
    def filter(self, message):
        if not message.text:
            return False

        quadratini = ['🟥', '🟩', '⬜️', '🟨', '⬛️', '🟦', '🟢', '⚫️', '🟡', '🟠', '🔵', '🟣']

        # Se ha qualche emoji colorata, probabilmente è un messaggio di un gioco
        if any(c in message.text for c in quadratini):
            return True

        # Eccezione per Plotwords, che non usa emoji
        if 'Plotwords' in message.text and 'Clues used' in message.text:
            return True
        
        if 'Murdle for' in message.text and ('❌' in message.text or '✅' in message.text) and '🔪' in message.text:
            return True

        return False

def get_day_from_date(game: str, date: datetime.date | str = None) -> str:
    if isinstance(date, str) and game == 'Globle':
        date = datetime.datetime.strptime(date, '🌎 %b %d, %Y 🌍').date()

    if isinstance(date, str) and game == 'HighFive':
        date_str = date.split('/')[-1]
        date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()

    if isinstance(date, str) and game == 'Moviedle':
        date = datetime.datetime.strptime(date, '#%Y-%m-%d').date()
    
    if isinstance(date, str) and game == 'Murdle':
        date = datetime.datetime.strptime(date, '%m/%d/%Y').date()

    if isinstance(date, str) and game == 'Picsey':
        date = datetime.datetime.strptime(date, '%m.%d.%y').date()

    if date is None:
        date = datetime.date.today()

    days_difference = GAMES[game]['date'] - date
    return str(int(GAMES[game]['day']) - days_difference.days)

def get_date_from_day(game: str, day: str) -> datetime.date:
    days_difference = int(GAMES[game]['day']) - int(day)
    return GAMES[game]['date'] - datetime.timedelta(days=days_difference)

def correct_name(name: str) -> str:
    return list(GAMES.keys())[[x.lower() for x in GAMES.keys()].index(name.lower())]

def make_buttons(game: str, message_id: int, day: int) -> InlineKeyboardMarkup:
    today = get_day_from_date(game, datetime.date.today())
    date_str = f"{get_date_from_day(game, day).strftime('%Y-%m-%d')}"
    day = int(day)
    buttons = InlineKeyboardMarkup([[
        InlineKeyboardButton('⬅️', callback_data=f'cls_{game}_{message_id}_{day - 1}'),
        InlineKeyboardButton('📆 Oggi', callback_data=f'cls_{game}_{message_id}_{today}'),
        InlineKeyboardButton('➡️', callback_data=f'cls_{game}_{message_id}_{day + 1}'),
    ],
    [InlineKeyboardButton(date_str, callback_data='cls_do_nothing')]])
    return buttons

def time_from_emoji(input_string: str) -> str:
    emojidict = {
        '0️⃣': 0,
        '1️⃣': 1,
        '2️⃣': 2,
        '3️⃣': 3,
        '4️⃣': 4,
        '5️⃣': 5,
        '6️⃣': 6,
        '7️⃣': 7,
        '8️⃣': 8,
        '9️⃣': 9,
        '🔟': 10,
        ':': ''
    }
    for key, value in emojidict.items():
        input_string = input_string.replace(key, str(value))
    return input_string

def process_tries(game: str, tries: int|str) -> int|str:
    # This is a little exception for HighFive scores, which are negative because in the game the more the better.
    # We want to show them as positive.
    if game == 'HighFive':
        tries = abs(tries)

    # For Timeguesser, scores are points, the more the better. Max points is 50_000 so we save them as differences from max.
    if game == 'TimeGuesser':
        tries = 50_000 - tries

    # For Picsey, scores are points, the more the better. Max points is 100 so we save them as differences from max.
    if game == 'Picsey':
        tries = 100 - tries

    # So, murdle points are time. I store time (for exampe: 5:12) as an int (512) so I can order them. Here I convert them back to string, putting a semicolon two chars from the end.
    if game == 'Murdle':
        tries = str(tries)[:-2] + ':' + str(tries)[-2:]
    return tries

def is_connection_block_completed(block: str) -> bool:
    color = block[0]
    if block == color*4:
        return True
    return False

def is_connection_completed(connection: list[str]) -> bool:
    completed_blocks = 0
    for block in connection:
        if is_connection_block_completed(block):
            completed_blocks += 1
    if completed_blocks == 4:
        return True
    return False


def streak_at_day(user_id, game, day) -> int:
    streak = 0

    games = (Punteggio
    .select(Punteggio.day, Punteggio.user_id)
    .where(Punteggio.user_id == user_id,
            Punteggio.game == game,
            Punteggio.tries != 999,
            Punteggio.tries != 9999999)
    .order_by(Punteggio.day.desc()))

    gamedays = set([int(x.day) for x in games])

    if day not in gamedays:
        return streak

    for day in range(day, 0, -1):
        if day in gamedays:
            streak += 1
        else:
            break

    return streak

def longest_streak(user_id, game) -> int:
    streak = (Punteggio
    .select(peewee.fn.MAX(Punteggio.streak))
    .where(Punteggio.user_id == user_id,
            Punteggio.game == game))
    
    return streak.scalar()

def update_streak():
    c = 0
    for punt in Punteggio.select().where(Punteggio.streak is not None):
        c += 1
        streak = streak_at_day(punt.user_id, punt.game, int(punt.day))
        print(f"Selected: [{c}] {punt.user_id} {punt.game} {punt.day} {punt.streak} | calc-streak: {streak}")
        punt.streak = streak
        # print(f"New Streak: {punt.streak}")
        punt.save()

def personal_stats(user_id: int) -> str:
    intro = 'Ecco le tue statistiche personali:\n\n'

    # longest streak best game streak
    long_streak_query = Punteggio.select(peewee.fn.MAX(Punteggio.streak).alias('streak'), Punteggio.game).where(Punteggio.user_id == user_id).group_by(Punteggio.game).order_by(Punteggio.streak.desc()).limit(1)
    long_streak = long_streak_query[0].streak
    long_streak_game = long_streak_query[0].game
    long_streak_string = f"Lo streak più lungo è di {long_streak} giocate di fila a {long_streak_game}.\n"

    # gioco più giocato
    most_played_query = Punteggio.select(Punteggio.game, peewee.fn.COUNT(Punteggio.game).alias('c')).where(Punteggio.user_id == user_id).group_by(Punteggio.game).order_by(peewee.fn.COUNT(Punteggio.game).desc()).limit(1)
    most_played = most_played_query[0].game
    most_played_count = most_played_query[0].c
    most_played_string = f"Il gioco a cui hai giocato di più è {most_played} con {most_played_count} partite!\n"

    # gioco meno giocato
    least_played_query = Punteggio.select(Punteggio.game, peewee.fn.COUNT(Punteggio.game).alias('c')).where(Punteggio.user_id == user_id).group_by(Punteggio.game).order_by(peewee.fn.COUNT(Punteggio.game).asc()).limit(1)
    least_played = least_played_query[0].game
    least_played_count = least_played_query[0].c
    least_played_string = f"Il gioco che invece ti fa cagare di più è {least_played}, hai giocato solo {least_played_count} volte.\n"

    # giocate totali
    total_plays = Punteggio.select(peewee.fn.COUNT(Punteggio.game).alias('c')).where(Punteggio.user_id == user_id).scalar()

    # tempo perso a giocare (considerando 2min a giocata), in DD:HH:MM
    single_play_minutes = 2
    total_time = total_plays * single_play_minutes
    duration = datetime.datetime.utcfromtimestamp(datetime.timedelta(minutes=total_time).total_seconds())
    total_plays_string = f"In totale hai fatto {total_plays} partite. A 2 minuti a partita, hai sprecato {duration.strftime('%H ore e %M minuti')} della tua vita.\n"

    # giocate perse totali
    total_loses = Punteggio.select(peewee.fn.COUNT(Punteggio.game).alias('c')).where(Punteggio.user_id == user_id, (Punteggio.tries == 999) | (Punteggio.tries == 9999999)).scalar()
    if total_loses:
        total_loses_string = f"In totale, hai perso {total_loses} partite\n"

    result = intro + long_streak_string + most_played_string + least_played_string + total_plays_string
    if total_loses:
        result += total_loses_string
    return result

