import datetime
import time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext.filters import MessageFilter

from config import GAMES, MEDALS, Punteggio


class GameFilter(MessageFilter):
    def filter(self, message):
        if not message:
            return False

        quadratini = ['🟥', '🟩', '⬜️', '🟨', '⬛️', '🟦', '🟢', '⚫️', '🟡', '🟠', '🔵', '🟣']

        # Se ha qualche emoji colorata, probabilmente è un messaggio di un gioco
        if any(c in message.text for c in quadratini):
            return True

        # Eccezione per Plotwords, che non usa emoji
        if 'Plotwords' in message.text and 'Clues used' in message.text:
            return True

        return False

def parse_results(text: str) -> dict:
    result = {}
    lines = text.splitlines()
    try:
        if 'Wordle' in lines[0]:
            result['name'] = 'Wordle'
            first_line = lines[0].split()
            result['day'] = first_line[1]
            result['tries'] = first_line[2].split('/')[0]
            result['timestamp'] = int(time.time())

        elif 'Worldle' in lines[0]:
            result['name'] = 'Worldle'
            first_line = lines[0].split()
            result['day'] = first_line[1][1:]
            result['tries'] = first_line[2].split('/')[0]
            result['timestamp'] = int(time.time())
            result['stars'] = text.count('⭐️') + text.count('🪙')

        elif 'Par🇮🇹le' in lines[0]:
            result['name'] = 'Parole'
            first_line = lines[0].split()
            result['day'] = first_line[1][2:]
            result['tries'] = first_line[2].split('/')[0]
            result['timestamp'] = int(time.time())

        elif 'contexto.me' in lines[0]:
            result['name'] = 'Contexto'
            first_line = lines[0].split()
            result['day'] = first_line[3][1:]
            if first_line[4] == 'but':
                result['tries'] = 'X'
            elif first_line[-1] == 'tips.':
                tips = int(first_line[-2])
                index = first_line.index('guesses')
                result['tries'] = int(first_line[index - 1]) + (tips * 15)
            else:
                result['tries'] = first_line[-2]
            result['timestamp'] = int(time.time())

        elif '#Tradle' in lines[0]:
            result['name'] = 'Tradle'
            first_line = lines[0].split()
            result['day'] = first_line[1][1:]
            result['tries'] = first_line[2].split('/')[0]
            result['timestamp'] = int(time.time())

        elif '#GuessTheGame' in lines[0]:
            result['name'] = 'GuessTheGame'
            result['timestamp'] = int(time.time())
            first_line = lines[0].split()
            result['day'] = first_line[1][1:]
            punteggio = lines[2].replace(' ', '')
            if '🟩' not in punteggio:
                result['tries'] = 'X'
            else:
                result['tries'] = str(punteggio.index('🟩'))

        elif '#globle' in lines[-1]:
            result['name'] = 'Globle'
            result['timestamp'] = int(time.time())
            # Globle doesn't have a #day, so we parse the date and get our own numeration (Jun 23, 2023 -> 200)
            result['day'] = get_day_from_date('Globle', lines[0])
            for line in lines:
                if '=' in line:
                    result['tries'] = line.split('=')[-1][1:]

        elif 'Flagle' in lines[0]:
            result['name'] = 'Flagle'
            first_line = lines[0].split()
            result['day'] = first_line[1][1:]
            result['tries'] = first_line[3].split('/')[0]
            result['timestamp'] = int(time.time())

        elif 'WhereTaken' in lines[0]:
            result['name'] = 'WhereTaken'
            first_line = lines[0].split()
            result['day'] = first_line[2][1:]
            result['tries'] = first_line[3].split('/')[0]
            result['timestamp'] = int(time.time())
            result['stars'] = text.count('⭐️')

        elif '#waffle' in lines[0]:
            result['name'] = 'Waffle'
            first_line = lines[0].split()
            result['day'] = first_line[0].replace('#waffle', '')
            punti = first_line[1].split('/')[0]
            result['tries'] = 15 - int(punti) if punti != 'X' else 'X'
            result['timestamp'] = int(time.time())
            result['stars'] = text.count('⭐️')

        elif 'Cloudle -' in lines[0]:
            result['name'] = 'Cloudle'
            first_line = lines[0].split()
            # Cloudle doesn't have a #day, so we parse the date and get our own numeration (Jun 23, 2023 -> 200)
            result['day'] = get_day_from_date('Cloudle', datetime.date.today())
            result['tries'] = first_line[-1].split('/')[0]
            result['timestamp'] = int(time.time())

        elif 'https://highfivegame.app/2' in lines[-1]:
            result['name'] = 'HighFive'
            result['timestamp'] = int(time.time())
            # HighFive doesn't have a #day, so we parse the date and get our own numeration (Jun 23, 2023 -> 200)
            result['day'] = get_day_from_date('HighFive', lines[-1])
            result['tries'] = str(0-int(lines[0].split()[3]))

        elif 'Plotwords' in lines[0]:
            result['name'] = 'Plotwords'
            result['timestamp'] = int(time.time())
            first_line = lines[0].split()
            result['day'] = first_line[1][1:]
            tries = lines[1].split()[-1].split('/')[0]
            result['tries'] = tries if tries != '13' else 'X'

        elif 'Framed' in lines[0]:
            result['name'] = 'Framed'
            result['timestamp'] = int(time.time())
            first_line = lines[0].split()
            result['day'] = first_line[1][1:]
            punteggio = lines[1].replace(' ', '').replace('🎥', '')
            if '🟩' not in punteggio:
                result['tries'] = 'X'
            else:
                result['tries'] = str(punteggio.index('🟩')+1)


    except IndexError:
        return None

    return result

def get_day_from_date(game: str, date: datetime.date | str = None) -> str:
    if isinstance(date, str) and game == 'Globle':
        date = datetime.datetime.strptime(date, '🌎 %b %d, %Y 🌍').date()

    if isinstance(date, str) and game == 'HighFive':
        date_str = date.split('/')[-1]
        date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()

    if date is None:
        date = datetime.date.today()

    days_difference = GAMES[game]['date'] - date
    return str(int(GAMES[game]['day']) - days_difference.days)

def make_single_classifica(game: str, chat_id: int, day: int=None, limit: int=6) -> str:
    day = day or get_day_from_date(game, datetime.date.today())
    emoji = GAMES[game]['emoji']
    query = (Punteggio
        .select(Punteggio.user_name, Punteggio.tries)
        .where(Punteggio.day == day,
               Punteggio.game == game,
               Punteggio.chat_id == chat_id,
               Punteggio.tries != 999)
        .order_by(Punteggio.tries, Punteggio.extra.desc(), Punteggio.timestamp)
        .limit(limit))

    if not query:
        return None

    classifica = ''

    classifica += f'<b>{emoji} {game} #{day}</b>\n'

    for posto, punteggio in enumerate(query, start=1):
        # This is a little exception for HighFive scores, which are negative. We want to show them as positive.
        if game == 'HighFive':
            punteggio.tries = abs(punteggio.tries)
        classifica += f'{MEDALS.get(posto, " ")} {punteggio.user_name} ({punteggio.tries})\n'
    return classifica

def correct_name(name: str) -> str:
    return list(GAMES.keys())[[x.lower() for x in GAMES.keys()].index(name.lower())]

def make_buttons(game: str, message_id: int, day: int) -> InlineKeyboardMarkup:
    today = get_day_from_date(game, datetime.date.today())
    day = int(day)
    buttons = InlineKeyboardMarkup([[
        InlineKeyboardButton('⬅️', callback_data=f'cls_{game}_{message_id}_{day - 1}'),
        InlineKeyboardButton('📆 Oggi', callback_data=f'cls_{game}_{message_id}_{today}'),
        InlineKeyboardButton('➡️', callback_data=f'cls_{game}_{message_id}_{day + 1}'),
    ]])
    return buttons
