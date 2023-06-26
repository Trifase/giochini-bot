import datetime
import time

import pytz
from collections import defaultdict
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler

from config import GAMES, ID_GIOCHINI, ID_TESTING, MEDALS, TOKEN, Punteggio, Punti


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
            result['day'] = get_day_from_date('Cloudle', datetime.date.today())
            result['tries'] = first_line[-1].split('/')[0]
            result['timestamp'] = int(time.time())

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


async def classifica_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query

    chat_id = query.message.chat.id
    m_id = query.message.id

    await query.answer()

    data = query.data
    _, game, message_id, day = data.split('_')

    classifica_text = make_single_classifica(game, chat_id=update.effective_chat.id, day=day, limit=6)

    if not classifica_text:
        classifica_text = "Non c'è niente da vedere qui."

    buttons = make_buttons(game, update.effective_message.message_id, day)


    await context.bot.edit_message_text(classifica_text, chat_id=chat_id, message_id=m_id, reply_markup=buttons, parse_mode='HTML')


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    giochi = [f'<code>{x}</code>' for x in GAMES.keys()]
    giochi = ' · '.join(giochi)
    message = [
        'Questo bot parsa automaticamente i punteggi dei giochi giornalieri, fa una classifica giornaliera e una classifica dei migliori player.',
        '',
        f'I giochi disponibili sono:\n {giochi}',
        '',
        '📚 <b>Lista dei comandi</b> 📚',
        '',
        '📌 /classifica - Mostra la classifica di tutti i giochi',
        '📌 /classifica <i>[gioco]</i> - Mostra la classifica di un gioco, ad esempio: <code>/classifica wordle</code>',
        '',
        '📌 /top - Mostra i migliori player - aggiornato ogni mezzanotte',
        '📌 /mytoday - Mostra i giochi a cui hai giocato oggi, e quelli che ti mancano',
        '📌 /help - Mostra questo messaggio',
    ]
    message_text = '\n'.join(message)
    await update.effective_message.reply_text(message_text, parse_mode='HTML')

async def post_single_classifica(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        return await classificona(update, context)
    
    if context.args[0].lower() not in [x.lower() for x in GAMES.keys()]:
        return await classificona(update, context)
    else:
        game = correct_name(context.args[0])
        day = get_day_from_date(game, datetime.date.today())
        classifica_text = make_single_classifica(game, chat_id=update.effective_chat.id, limit=6)
        if not classifica_text:
            return await classificona(update, context)
        buttons = make_buttons(game, update.effective_message.message_id, day)

        await update.effective_message.reply_text(classifica_text, reply_markup=buttons, parse_mode='HTML')
    return

async def top_players(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.id != ID_GIOCHINI:
        return

    message = 'Classifica aggiornata:\n'

    query = (Punti
        .select()
        .order_by(Punti.punti.desc())
        .limit(10))

    if not query:
        return await update.message.reply_text('Non ci sono ancora giocatori.')

    for i, q in enumerate(query, start=1):
        if i in [1, 2, 3]:
            message += f'{MEDALS[i]} [{q.punti}] {q.user_name}\n'
        else:
            message += f'[{q.punti}] {q.user_name}\n'

    await update.message.reply_text(text=message, parse_mode='HTML', disable_web_page_preview=True)

async def classificona(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    messaggio = ''
    for game in GAMES.keys():
        classifica = make_single_classifica(game, chat_id=update.effective_chat.id, limit=3)
        if classifica:
            messaggio += classifica + '\n'
    
    if messaggio:
        await update.message.reply_text(messaggio, parse_mode='HTML')
    return

async def parse_punteggio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    chars = ['🟥', '🟩', '⬜️', '🟨', '⬛️', '🟦', '🟢', '⚫️', '🟡']
    if not any(c in update.message.text for c in chars):
        return

    result = parse_results(update.message.text)

    if result:

        result['user_name'] = update.message.from_user.full_name
        result['user_id'] = update.message.from_user.id

        query = (Punteggio
            .select()
            .where(Punteggio.day == int(result['day']),
                   Punteggio.game == result['name'],
                   Punteggio.user_id == result['user_id'],
                   Punteggio.chat_id == update.effective_chat.id
                   )
            )

        if query:
            await update.message.reply_text('Hai già giocato questo round.')
            return

        if result.get('tries') == 'X':
            await update.message.reply_text('Hai perso loooool')
            result['tries'] = '999'


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

        today_game = int(get_day_from_date(result['name'], datetime.date.today()))

        if int(result['day']) in [today_game, today_game - 1]:
            message = f'Classifica di {result["name"]} aggiornata.\n'
            classifica = make_single_classifica(result["name"], update.effective_chat.id)
            message += classifica
            await update.message.reply_html(classifica)

        else:
            await update.message.reply_text(f'Ho salvato il tuo punteggio di {int(today_game) - int(result["day"])} giorni fa.')

        print(f"Aggiungo punteggio di {result['user_name']} per {result['name']} #{result['day']} ({result['tries']})")

    else:
        await update.message.reply_text('Non ho capito, scusa')

async def manual_daily_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await daily_reminder(context)

async def mytoday(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = 'Ecco a cosa hai già giocato oggi:\n'
    played_today = set()
    not_played_today = set()
    for game in GAMES.keys():
        day = get_day_from_date(game, datetime.date.today())
        query = (Punteggio
            .select()
            .where(Punteggio.day == int(day),
                     Punteggio.game == game,
                     Punteggio.user_id == update.message.from_user.id
                     )
                )
        if query:
            played_today.add(game)
            tries = query[0].tries
            if tries == 999:
                tries = 'X'
            message += f'{GAMES[game]["emoji"]} {game} #{day} ({query[0].tries})\n'
        else:
            not_played_today.add(game)

    if not played_today:
        message = 'Non hai giocato a nulla oggi.'

    elif not_played_today:
        message += '\nTi manca:\n'
        for game in not_played_today:
            message += f'<a href="{GAMES[game]["url"]}">{GAMES[game]["emoji"]} {game}</a>\n'
    elif not not_played_today:
        message += '\nHai giocato a tutto!'
    
    await update.message.reply_text(message, parse_mode='HTML', disable_web_page_preview=True)


async def riassunto_serale(context: ContextTypes.DEFAULT_TYPE) -> None:
    points = defaultdict(int)
    for game in GAMES.keys():

        day = get_day_from_date(game, datetime.date.today())

        query = (Punteggio
            .select(Punteggio.user_name, Punteggio.user_id)
            .where(Punteggio.day == day,
                Punteggio.game == game,
                # Punteggio.chat_id == update.effective_chat.id)
                Punteggio.chat_id == ID_GIOCHINI,
                Punteggio.tries != 999
                )
            .order_by(Punteggio.tries, Punteggio.extra.desc(), Punteggio.timestamp)
            .limit(3))

        for i in range(len(query)):
            try:
                name = f"{query[i].user_id}_|_{query[i].user_name}"
                points[name] += 3 - i
            except IndexError:
                pass

    cambiamenti = dict(points)
    cambiamenti = sorted(cambiamenti.items(), key=lambda x: x[1], reverse=True)

    message = 'Ecco come è andata oggi:\n'

    for user, points in cambiamenti:
        user_id, user_name = user.split('_|_')
        user_id = int(user_id)

        message += f'+{points} {user_name}\n'

        query = (Punti
            .select(Punti.punti)
            .where(Punti.user_id == user_id))
        
        if query:
            points += query[0].punti

        Punti.replace(user_id=user_id, user_name=user_name, punti=points).execute()

    await context.bot.send_message(chat_id=ID_GIOCHINI, text=message, parse_mode='HTML', disable_web_page_preview=True)

    message = 'Classifica aggiornata:\n'

    query = (Punti
        .select()
        .order_by(Punti.punti.desc())
        .limit(10))

    for q in query:
        message += f'[{q.punti}] {q.user_name}\n'

    await context.bot.send_message(chat_id=ID_GIOCHINI, text=message, parse_mode='HTML', disable_web_page_preview=True)

async def daily_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    message = 'Buongiorno, ecco a cosa si gioca oggi!\n\n'
    for game in GAMES.keys():
        day = get_day_from_date(game, datetime.date.today())
        message += f'{GAMES[game]["emoji"]} {game} #{day}\n'
        message += f'{GAMES[game]["url"]}\n\n'
    mypost = await context.bot.send_message(chat_id=ID_GIOCHINI, text=message, disable_web_page_preview=True)
    await mypost.pin()


async def post_init(app: Application) -> None:
    Punteggio.create_table()
    Punti.create_table()
    print("Pronti!")


def main():

    builder = ApplicationBuilder()
    builder.token(TOKEN)
    builder.post_init(post_init)

    app = builder.build()

    j = app.job_queue
    j.run_daily(daily_reminder, datetime.time(hour=8, minute=0, tzinfo=pytz.timezone('Europe/Rome')), data=None)
    j.run_daily(riassunto_serale, datetime.time(hour=23, minute=58, tzinfo=pytz.timezone('Europe/Rome')), data=None)

    app.add_handler(CommandHandler('classificona', classificona), 1)
    app.add_handler(CommandHandler('giochiamo', manual_daily_reminder), 1)
    app.add_handler(CommandHandler('mytoday', mytoday), 1)
    app.add_handler(CommandHandler('help', help), 1)

    app.add_handler(CommandHandler(['c', 'classifica'], post_single_classifica), 2)
    app.add_handler(CommandHandler('top', top_players), 1)
    app.add_handler(CallbackQueryHandler(classifica_buttons, pattern=r'^cls_'))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.UpdateType.EDITED, parse_punteggio))



    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)

main()
