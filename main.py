from telegram import Update
import time
import datetime
from telegram.ext import ApplicationBuilder, ContextTypes, filters, MessageHandler, Application, CommandHandler

from config import TOKEN, GAMES, MEDALS, DAYS, Punteggio



def parse_results(text) -> dict:
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
            result['stars'] = text.count('⭐️')

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
                index = first_line.index('guesses')
                result['tries'] = first_line[index - 1]
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

    except IndexError:
        return None

    return result

def get_day_from_date(game: str, date: datetime.date | str = datetime.datetime.today()) -> str:
    if isinstance(date, str) and game == 'Globle':
        date = datetime.datetime.strptime(date, '🌎 %b %d, %Y 🌍').date()

    days_difference = DAYS[game]['date'] - date
    return str(int(DAYS[game]['day']) - days_difference.days)


def make_daily_classifica(game, emoji) -> str:
    query = (Punteggio
        .select(Punteggio.user_name, Punteggio.tries)
        .where(Punteggio.day == get_day_from_date(game, datetime.date.today()), Punteggio.game == game)
        .order_by(Punteggio.tries, Punteggio.timestamp))
    if not query:
        return None
    classifica = ''

    classifica += f'<b>{emoji} {game} #{get_day_from_date(game, datetime.date.today())}</b>\n'

    for posto, punteggio in enumerate(query, start=1):
        classifica += f'{MEDALS.get(posto, " ")} {punteggio.user_name} ({punteggio.tries})\n'
    return classifica

async def classifica(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    messaggio = ''
    for game in GAMES.keys():
        classifica = make_daily_classifica(game, GAMES.get(game))
        if classifica:
            messaggio += classifica + '\n'
    
    if messaggio:
        await update.message.reply_text(messaggio, parse_mode='HTML')
    return


async def post_init(app: Application) -> None:
    Punteggio.create_table()

async def print_everything(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    chars = ['🟥', '🟩', '⬜️', '🟨', '⬛️']
    if not any(c in update.message.text for c in chars):
        return

    result = parse_results(update.message.text)

    if result:
        if result.get('tries') == 'X':
            await update.message.reply_text('Hai perso loooool')
            return

        result['user_name'] = update.message.from_user.full_name
        result['user_id'] = update.message.from_user.id

        query = (Punteggio
            .select()
            .where(Punteggio.date == datetime.date.today(),
                   Punteggio.game == result['name'].capitalize(),
                   Punteggio.user_id == result['user_id']
                   )
            )
        if query:
            await update.message.reply_text('Hai già giocato oggi')
            return

        Punteggio.create(
            date=datetime.datetime.now(),
            timestamp=int(result['timestamp']),
            chat_id=int(update.message.chat.id),
            user_id=int(result['user_id']),
            user_name=result['user_name'],
            game=result['name'],
            day=int(result['day']),
            tries=int(result['tries']),
            extra=result.get('stars', None)
            )
        message = f'Classifica di {result["name"]} aggiornata.\n'
        classifica = make_daily_classifica(result["name"], GAMES.get(result["name"]))
        message += classifica
        await update.message.reply_html(classifica)
        print(f"Aggiungo punteggio di {result['user_name']} per {result['name']} ({result['tries']})")
    else:
        await update.message.reply_text('Non ho capito, scusa')

def main():
    builder = ApplicationBuilder()
    builder.token(TOKEN)
    builder.post_init(post_init)

    app = builder.build()

    app.add_handler(CommandHandler('classifica', classifica), 1)
    app.add_handler(MessageHandler(filters.TEXT, print_everything))


    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)


main()
