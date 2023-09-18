import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext.filters import MessageFilter

from config import GAMES


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
        print(date)
        date = datetime.datetime.strptime(date, '%m/%d/%Y').date()

    if date is None:
        date = datetime.date.today()

    days_difference = GAMES[game]['date'] - date
    return str(int(GAMES[game]['day']) - days_difference.days)

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


