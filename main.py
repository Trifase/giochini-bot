import datetime
import logging
import sys
import zipfile
from collections import defaultdict

import pytz
import peewee

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    Defaults,
    MessageHandler,
    filters,
)

from config import ADMIN_ID, BACKUP_DEST, GAMES, ID_GIOCHINI, ID_TESTING, MEDALS, TOKEN, Punteggio, Punti
from utils import correct_name, get_day_from_date, make_buttons, streak_at_day, longest_streak, get_date_from_day, GameFilter
from parsers import (wordle, worldle, parole, contexto, tradle, guessthegame, globle, flagle, wheretaken, waffle, cloudle, highfive, timeguesser, framed, moviedle, murdle, connections, nerdle)

# Logging setup
logger = logging.getLogger()

logging.basicConfig(
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.handlers.RotatingFileHandler('logs/log.log', maxBytes=1000000, backupCount=5),
    ],
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="[%Y-%m-%d %H:%M:%S]",
)

# httpx become very noisy from 0.24.1, so we set it to WARNING
httpx_logger = logging.getLogger('httpx')
httpx_logger.setLevel(logging.WARNING)

# We also want to lower the log level of the scheduler
aps_logger = logging.getLogger('apscheduler')
aps_logger.setLevel(logging.WARNING)

# Istanziamo il filtro custom
giochini_results_filter = GameFilter()


def parse_results(text: str) -> dict:
    lines = text.splitlines()

    if 'Wordle' in lines[0]:
        return wordle(text)

    elif 'Worldle' in lines[0]:
        return worldle(text)

    elif 'Par🇮🇹le' in lines[0]:
        return parole(text)

    elif 'contexto.me' in lines[0]:
        return contexto(text)

    elif '#Tradle' in lines[0]:
        return tradle(text)

    elif '#GuessTheGame' in lines[0]:
        return guessthegame(text)

    elif '#globle' in lines[-1]:
        return globle(text)

    elif '#Flagle' in lines[0]:
        return flagle(text)

    elif 'WhereTaken' in lines[0]:
        return wheretaken(text)

    elif '#waffle' in lines[0]:
        return waffle(text) 

    elif 'Cloudle -' in lines[0]:
        return cloudle(text)    

    elif 'https://highfivegame.app/2' in lines[-1]:
        return highfive(text)
    
    elif 'TimeGuessr' in lines[0]:
        return timeguesser(text)

    elif 'Moviedle' in lines[0]:
        return moviedle(text)

    elif 'Framed' in lines[0]:
        return framed(text)

    elif 'Murdle' in lines[1]:
        return murdle(text)
    
    elif 'Connections' in lines[0]:
        return connections(text)
    
    elif 'nerdlegame' in lines[0]:
        return nerdle(text)

    return None

def make_single_classifica(game: str, chat_id: int, day: int=None, limit: int=6, user_id=None) -> str:
    day = day or get_day_from_date(game, datetime.date.today())
    emoji = GAMES[game]['emoji']
    user_id_found = False
    query = (Punteggio
        .select(Punteggio.user_name, Punteggio.tries, Punteggio.user_id)
        .where(Punteggio.day == day,
               Punteggio.game == game,
               Punteggio.chat_id == chat_id,
               Punteggio.tries != 999,
               Punteggio.tries != 9999999)
        .order_by(Punteggio.tries, Punteggio.extra.desc(), Punteggio.timestamp)
        .limit(limit))

    # print(f'Sto cercando la classifica per {game}, giorno {day}')
    if not query:
        # print(f'Classifica per {game} nessun risultato!')
        return None

    classifica = ''
    url = GAMES[game]['url']
    classifica += f'<a href="{url}"><b>{emoji} {game} #{day}</b></a>\n'

    for posto, punteggio in enumerate(query, start=1):
        # This is a little exception for HighFive scores, which are negative because in the game the more the better.
        # We want to show them as positive.
        if game == 'HighFive':
            punteggio.tries = abs(punteggio.tries)

        # For Timeguesser, scores are points, the more the better. Max points is 50_000 so we save them as differences from max.
        if game == 'TimeGuesser':
            punteggio.tries = 50_000 - punteggio.tries

        #So, murdle points are time. I store time (for exampe: 5:12) as an int (512) so I can order them. Here I convert them back to string, putting a semicolon two chars from the end.
        if game == 'Murdle':
            punteggio.tries = str(punteggio.tries)[:-2] + ':' + str(punteggio.tries)[-2:]

        if user_id and not user_id_found and punteggio.user_id == user_id:
            user_id_found = True
        classifica += f'{MEDALS.get(posto, "")}{punteggio.user_name} ({punteggio.tries})\n'

    # At this point, if the user is not found, we search deeper in the db
    if user_id and not user_id_found:
        deep_query = (Punteggio
                .select(Punteggio.user_name, Punteggio.tries, Punteggio.user_id)
                .where(Punteggio.day == day,
                    Punteggio.game == game,
                    Punteggio.chat_id == chat_id,
                    Punteggio.tries != 999,
                    Punteggio.tries != 9999999)
                .order_by(Punteggio.tries, Punteggio.extra.desc(), Punteggio.timestamp))
        
        for posto, punteggio in enumerate(deep_query, start=1):
            if game == 'HighFive':
                punteggio.tries = abs(punteggio.tries)

            if game == 'TimeGuesser':
                punteggio.tries = 50_000 - punteggio.tries

            if game == 'Murdle':
                punteggio.tries = str(punteggio.tries)[:-2] + ':' + str(punteggio.tries)[-2:]

            if user_id and punteggio.user_id == user_id:
                user_id_found = True
                classifica += f'...\n{posto}. {punteggio.user_name} ({punteggio.tries})\n'

    return classifica

def make_games_classifica(days: int = 0) -> str:
    if not days:
        days = 30
    today = datetime.date.today() 
    days_ago = today - datetime.timedelta(days=days)
    query = (Punteggio
        .select(Punteggio.game, Punteggio.timestamp, peewee.fn.COUNT(Punteggio.timestamp).alias('count'))
        .where(Punteggio.date >= days_ago)
        .group_by(Punteggio.game)
        .order_by(peewee.fn.COUNT(Punteggio.timestamp).desc()))

    if not query:
        return None

    classifica = ''
    for record in query:
        classifica += f'[{record.count}] {record.game}\n'

    return classifica


async def classifica_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query

    chat_id = query.message.chat.id
    m_id = query.message.id

    await query.answer()

    data = query.data
    if data == 'cls_do_nothing':
        return
    _, game, message_id, day = data.split('_')

    classifica_text = make_single_classifica(game, chat_id=update.effective_chat.id, day=day, limit=6, user_id=update.effective_user.id)
    # date_str = f"== {get_date_from_day(game, day).strftime('%Y-%m-%d')} =="
    # classifica_text = f'{date_str}\n{classifica_text}'

    if not classifica_text:
        classifica_text = "Non c'è niente da vedere qui."

    buttons = make_buttons(game, update.effective_message.message_id, day)


    await context.bot.edit_message_text(classifica_text, chat_id=chat_id, message_id=m_id, reply_markup=buttons, parse_mode='HTML', disable_web_page_preview=True)

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
        '📌 /mytoday - Mostra i giochi a cui non hai ancora giocato oggi',
        '📌 /lista - Manda la lista di tutti i giochi supportati',
        '📌 /help - Mostra questo messaggio',
    ]
    message_text = '\n'.join(message)
    await update.effective_message.reply_text(message_text, parse_mode='HTML')

async def post_single_classifica(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        return await classificona(update, context)
    
    # print(context.args)
    # print(context.args[0].lower())
    # print([x.lower() for x in GAMES.keys()])
    if context.args[0].lower() not in [x.lower() for x in GAMES.keys()]:
        return await classificona(update, context)
    else:
        game = correct_name(context.args[0])
        day = get_day_from_date(game, datetime.date.today())

        classifica_text = make_single_classifica(game, chat_id=update.effective_chat.id, limit=6, user_id=update.effective_user.id)
        # date_str = f"== {get_date_from_day(game, day).strftime('%Y-%m-%d')} =="
        # classifica_text = f'{date_str}\n{classifica_text}'
        if not classifica_text:
            # return await classificona(update, context)
            classifica_text = "Non c'è niente da vedere qui."
        buttons = make_buttons(game, update.effective_message.message_id, day)

        await update.effective_message.reply_text(classifica_text, reply_markup=buttons, parse_mode='HTML', disable_web_page_preview=True)
    return

async def top_players(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.id != ID_GIOCHINI:
        return

    message = 'Classifica aggiornata:\n'

    query = (Punti
        .select()
        .order_by(Punti.punti.desc())
        .limit(20))

    if not query:
        return await update.message.reply_text('Non ci sono ancora giocatori.')

    for i, q in enumerate(query, start=1):
        if i in [1, 2, 3]:
            message += f'{MEDALS[i]} [{q.punti}] {q.user_name}\n'
        else:
            message += f'[{q.punti}] {q.user_name}\n'

    await update.message.reply_text(text=message, parse_mode='HTML', disable_web_page_preview=True)

async def top_games(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # if update.effective_chat.id != ID_GIOCHINI:
    #     return
    days = 7

    if context.args:
        try:
            days = int(context.args[0])
        except ValueError:
            pass

    message = f'Classifica dei giochi degli ultimi {days} giorni:\n'

    classifica = make_games_classifica(days)

    if not classifica:
        classifica = 'Non so che dire'

    message += classifica

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
            if result.get('name') == 'Murdle':
                result['tries'] = '9999999'



        if update.effective_chat.id == ID_TESTING:
            import pprint
            rawtext = pprint.pformat(result)
            # await update.message.reply_html(f'<code>{bytes(update.effective_message.text, "utf-8")}</code>') / Bytes debug
            await update.message.reply_html(f'<code>{rawtext}</code>')

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

        if result['tries'] in ['999', '9999999']:
            return

        today_game = int(get_day_from_date(result['name'], datetime.date.today()))

        if int(result['day']) in [today_game, today_game - 1]:
            message = f'Classifica di {result["name"]} aggiornata.\n'
            classifica = make_single_classifica(result["name"], update.effective_chat.id, day=result['day'])
            if classifica:
                classifica = f"{message}\n{classifica}"
                streak = streak_at_day(user_id=result['user_id'], game=result['name'], day=int(result['day']))
                if streak:
                    classifica += f'\nCurrent streak: {streak}'
                long_streak = longest_streak(user_id=result['user_id'], game=result['name'])
                if long_streak:
                    if long_streak > streak:
                        classifica += f'\nLongest streak: {long_streak}'
                    else:
                        classifica += '\nLongest streak: current'
                mymsg = await update.message.reply_html(classifica)
                context.job_queue.run_once(minimize_post, 60, data=mymsg, name=f"minimize_{str(update.effective_message.id)}")
            else: 
                mymsg = await update.message.reply_html("Ah, non l'ha ancora fatto nessuno, fico.")
                context.job_queue.run_once(delete_post, 60, data=[mymsg], name=f"delete_post_{str(update.effective_message.id)}")

        else:
            await update.message.reply_text(f'Ho salvato il tuo punteggio di {int(today_game) - int(result["day"])} giorni fa.')

        logging.info(f"Aggiungo punteggio di {result['user_name']} per {result['name']} #{result['day']} ({result['tries']})")

    else:
        await update.message.reply_text('Non ho capito, scusa')

async def manual_daily_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id == ADMIN_ID:
        await daily_reminder(context)

async def manual_backup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id == ADMIN_ID:
        return await make_backup(context)

async def mytoday(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # message = 'Ecco a cosa hai già giocato oggi:\n'
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
            # message += f'{GAMES[game]["emoji"]} {game} #{day} ({query[0].tries})\n'
        else:
            not_played_today.add(game)

    if not played_today:
        message = 'Non hai giocato a nulla oggi.\n'
        for game in not_played_today:
            message += f'<a href="{GAMES[game]["url"]}">{GAMES[game]["emoji"]} {game}</a>\n'

    elif not_played_today:
        message = 'Ti manca da giocare:\n'
        for game in not_played_today:
            message += f'<a href="{GAMES[game]["url"]}">{GAMES[game]["emoji"]} {game}</a>\n'

    elif not not_played_today:
        message = 'Hai giocato a tutto!'
    
    mymsg = await update.message.reply_text(message, parse_mode='HTML', disable_web_page_preview=True)
    command_msg = update.message
    context.job_queue.run_once(delete_post, 60, data=[mymsg, command_msg], name=f"myday_delete_{str(update.effective_message.id)}")

async def list_games(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = 'Lista dei giochi:\n'
    for game in GAMES.keys():
        message += f'{GAMES[game]["emoji"]} {game}: {GAMES[game]["url"]}\n'
    
    await update.message.reply_text(message, parse_mode='HTML', disable_web_page_preview=True)


async def riassunto_serale(context: ContextTypes.DEFAULT_TYPE) -> None:
    points = defaultdict(int)
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    for game in GAMES.keys():

        day = get_day_from_date(game, yesterday)

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
    await mypost.pin(disable_notification=True)

async def make_backup(context: ContextTypes.DEFAULT_TYPE) -> None:
    now = datetime.datetime.today().strftime('%Y%m%d_%H%M%S')

    backup_dir = "backups"
    archive_name = f"{backup_dir}/giochini-{now}-backup.zip"
    files_to_backup = ['db/sqlite.db']

    with zipfile.ZipFile(archive_name, 'w') as zip_ref:
        for file in files_to_backup:
            zip_ref.write(file)

    await context.bot.send_document(chat_id=BACKUP_DEST, document=open(archive_name, 'rb'))
    logging.info("[AUTO] Backup DB eseguito.")

async def minimize_post(context: ContextTypes.DEFAULT_TYPE) -> None:
    message = context.job.data
    await message.edit_text("Punteggio salvato.")

async def delete_post(context: ContextTypes.DEFAULT_TYPE) -> None:
    messages: list = context.job.data
    for message in messages:
        await message.delete()


async def post_init(app: Application) -> None:
    Punteggio.create_table()
    Punti.create_table()
    logger.info("Pronti!")


def main():
    defaults = Defaults(
        disable_web_page_preview=True,
        )

    builder = ApplicationBuilder()
    builder.token(TOKEN)
    builder.defaults(defaults)
    builder.post_init(post_init)

    app = builder.build()

    j = app.job_queue
    j.run_daily(daily_reminder, datetime.time(hour=8, minute=0, tzinfo=pytz.timezone('Europe/Rome')), data=None)
    j.run_daily(riassunto_serale, datetime.time(hour=1, minute=0, tzinfo=pytz.timezone('Europe/Rome')), data=None)
    j.run_daily(make_backup, datetime.time(hour=2, minute=0, tzinfo=pytz.timezone('Europe/Rome')), data=None)

    app.add_handler(CommandHandler('classificona', classificona), 1)
    app.add_handler(CommandHandler('giochiamo', manual_daily_reminder), 1)
    app.add_handler(CommandHandler(['mytoday', 'myday', 'my', 'today', 'daily'], mytoday), 1)
    app.add_handler(CommandHandler('help', help), 1)
    app.add_handler(CommandHandler(['list', 'lista'], list_games), 1)
    app.add_handler(CommandHandler('backup', manual_backup), 1)

    app.add_handler(CommandHandler(['c', 'classifica'], post_single_classifica), 2)
    app.add_handler(CommandHandler('top', top_players), 1)

    app.add_handler(CommandHandler('topgames', top_games), 1)
    app.add_handler(CallbackQueryHandler(classifica_buttons, pattern=r'^cls_'))
    app.add_handler(MessageHandler(giochini_results_filter & ~filters.UpdateType.EDITED, parse_punteggio))

    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)

main()
