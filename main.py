import datetime
import time

import pytz

from telegram import Update
from telegram.ext import Application, ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

from config import GAMES, ID_GIOCHINI, ID_TESTING, MEDALS, TOKEN, Punteggio


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

        elif 'WhereTaken' in lines[0]:
            result['name'] = 'WhereTaken'
            first_line = lines[0].split()
            result['day'] = first_line[2][1:]
            result['tries'] = first_line[3].split('/')[0]
            result['timestamp'] = int(time.time())
            result['stars'] = text.count('⭐️')

    except IndexError:
        return None

    return result

def get_day_from_date(game: str, date: datetime.date | str = None) -> str:
    if isinstance(date, str) and game == 'Globle':
        date = datetime.datetime.strptime(date, '🌎 %b %d, %Y 🌍').date()

    if date is None:
        date = datetime.date.today()

    days_difference = GAMES[game]['date'] - date
    return str(int(GAMES[game]['day']) - days_difference.days)

def make_daily_classifica(game: str, emoji: str, chat_id: int) -> str:
    query = (Punteggio
        .select(Punteggio.user_name, Punteggio.tries)
        .where(Punteggio.day == get_day_from_date(game, datetime.date.today()),
               Punteggio.game == game,
               Punteggio.chat_id == chat_id)
        .order_by(Punteggio.tries, Punteggio.extra.desc(), Punteggio.timestamp))

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
        classifica = make_daily_classifica(game, GAMES.get(game).get('emoji'), chat_id=update.effective_chat.id)
        if classifica:
            messaggio += classifica + '\n'
    
    if messaggio:
        await update.message.reply_text(messaggio, parse_mode='HTML')
    return

async def post_init(app: Application) -> None:
    Punteggio.create_table()

async def parse_punteggio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

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

        if update.effective_chat.id == ID_TESTING:
            import pprint
            pprint.pprint(result)
            punti = Punteggio(
                date=datetime.datetime.now(),
                timestamp=int(result['timestamp']),
                chat_id=int(update.message.chat.id),
                user_id=int(result['user_id']),
                user_name=result['user_name'],
                game=result['name'],
                day=int(result['day']),
                tries=int(result['tries']),
                extra=str(result.get('stars', None))
            )
            pprint.pprint(punti.__dict__)
            return

        query = (Punteggio
            .select()
            .where(Punteggio.day == int(result['day']),
                   Punteggio.game == result['name'],
                   Punteggio.user_id == result['user_id']
                   )
            )

        if query:
            await update.message.reply_text('Hai già giocato questo round.')
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
            extra=str(result.get('stars', None))
        )

        today_game = get_day_from_date(result['name'], datetime.date.today())
        if today_game == result['day']:
            message = f'Classifica di {result["name"]} aggiornata.\n'
            classifica = make_daily_classifica(result["name"], GAMES.get(result["name"]).get('emoji'), update.effective_chat.id)
            message += classifica
            await update.message.reply_html(classifica)

        else:
            await update.message.reply_text(f'Ho salvato il tuo punteggio di {int(today_game) - int(result["day"])} giorni fa.')

        print(f"Aggiungo punteggio di {result['user_name']} per {result['name']} #{result['day']} ({result['tries']})")

    else:
        await update.message.reply_text('Non ho capito, scusa')

async def daily_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    message = 'Buongiorno, ecco a cosa si gioca oggi!\n\n'
    for game in GAMES.keys():
        day = get_day_from_date(game, datetime.date.today())
        message += f'{GAMES[game]["emoji"]} {game} #{day}\n'
        message += f'{GAMES[game]["url"]}\n\n'
    mypost = await context.bot.send_message(chat_id=ID_GIOCHINI, text=message, disable_web_page_preview=True)
    await mypost.pin()

async def manual_daily_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await daily_reminder(context)

def main():


    builder = ApplicationBuilder()
    builder.token(TOKEN)
    builder.post_init(post_init)

    app = builder.build()

    j = app.job_queue
    j.run_daily(daily_reminder, datetime.time(hour=8, minute=0, tzinfo=pytz.timezone('Europe/Rome')), data=None)

    app.add_handler(CommandHandler('classifica', classifica), 1)
    app.add_handler(CommandHandler('giochiamo', manual_daily_reminder), 1)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.UpdateType.EDITED, parse_punteggio))

    print("Pronti!")

    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)


main()
