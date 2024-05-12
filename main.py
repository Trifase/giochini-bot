import datetime
import json
import locale
import logging
import sys
import time
import traceback
import zipfile

import peewee
import pytz
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    LinkPreviewOptions,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
    WebAppInfo,
)
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

from config import (
    ADMIN_ID,
    BACKUP_DEST,
    ID_BOTCENTRAL,
    ID_GIOCHINI,
    ID_TESTING,
    MEDALS,
    TOKEN,
    Medaglia,
    Punteggio,
    Punti,
)
from games import ALL_GAMES as GAMES
from games import GameFilter
from utils import (
    Classifica,
    correct_name,
    daily_ranking,
    get_day_from_date,
    group_stats,
    longest_streak,
    make_buttons,
    medaglie_count,
    personal_stats,
    process_tries,
    str_as_int,
    streak_at_day,
)

# Logging setup
logger = logging.getLogger()

logging.basicConfig(
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.handlers.RotatingFileHandler("logs/log.log", maxBytes=1000000, backupCount=5),
    ],
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="[%Y-%m-%d %H:%M:%S]",
)

# httpx become very noisy from 0.24.1, so we set it to WARNING
httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.WARNING)

# We also want to lower the log level of the scheduler
aps_logger = logging.getLogger("apscheduler")
aps_logger.setLevel(logging.WARNING)

locale.setlocale(locale.LC_TIME, "it_IT.UTF-8")

# Istanziamo il filtro custom
giochini_results_filter = GameFilter()


def make_single_classifica(game: str, chat_id: int, day: int = None, limit: int = 6, user_id=None, to_string=True) -> str:
    day = day or get_day_from_date(GAMES[game]["date"], GAMES[game]["day"], game, datetime.date.today())
    # print(f"Making classifica for {game} #{day}")
    emoji = GAMES[game]["emoji"]
    url = GAMES[game]["url"]

    user_id_found = False

    query = (
        Punteggio.select(Punteggio.user_name, Punteggio.tries, Punteggio.user_id)
        .where(
            Punteggio.day == day,
            Punteggio.game == game,
            Punteggio.chat_id == chat_id,
            # https://github.com/coleifer/peewee/issues/612#issuecomment-468029502
            Punteggio.lost == False,
        )
        .order_by(Punteggio.tries, Punteggio.extra.desc(), Punteggio.timestamp)
        .limit(limit)
    )
    # print(query.sql())
    if not query:
        return None

    classifica = Classifica()
    classifica.game = game
    classifica.day = day
    classifica.date = datetime.date.today()
    classifica.emoji = emoji
    classifica.header = f'<a href="{url}"><b>{emoji} {game} #{day}</b></a>'

    for posto, punteggio in enumerate(query, start=1):
        punteggio.tries = process_tries(game, punteggio.tries)

        if user_id and not user_id_found and punteggio.user_id == user_id:
            user_id_found = True

        classifica.pos.append((posto, punteggio.user_name, punteggio.tries))

    if len(classifica.pos) < 3:
        classifica.valid = False

    # At this point, if the user is not found in the first LIMIT positions, we search deeper in the db
    if user_id and not user_id_found:
        deep_query = (
            Punteggio.select(Punteggio.user_name, Punteggio.tries, Punteggio.user_id)
            .where(
                Punteggio.day == day,
                Punteggio.game == game,
                Punteggio.chat_id == chat_id,
                Punteggio.lost == False,
            )
            .order_by(Punteggio.tries, Punteggio.extra.desc(), Punteggio.timestamp)
        )

        for posto, punteggio in enumerate(deep_query, start=1):
            punteggio.tries = process_tries(game, punteggio.tries)

            if user_id and punteggio.user_id == user_id:
                user_id_found = True
                classifica.last = f"...\n{posto}. {punteggio.user_name} ({punteggio.tries})\n"

    if to_string:
        return classifica.to_string()

    return classifica


def make_games_classifica(days: int = 0) -> str:
    if not days:
        days = 30
    today = datetime.date.today()
    days_ago = today - datetime.timedelta(days=days)
    query = (
        Punteggio.select(Punteggio.game, Punteggio.timestamp, peewee.fn.COUNT(Punteggio.timestamp).alias("count"))
        .where(Punteggio.date >= days_ago)
        .group_by(Punteggio.game)
        .order_by(peewee.fn.COUNT(Punteggio.timestamp).desc())
    )

    if not query:
        return None

    classifica = ""
    for record in query:
        classifica += f"[{record.count}] {record.game}\n"

    return classifica


def make_menu_setting_favs(favs: list = None, favs_extra_button: bool = False, user_id: str = None, row_length: int = 2) -> InlineKeyboardMarkup:
    keyboard = []
    games = [x for x in GAMES.keys()]
    games = sorted(games)
    for game in games:
        if game not in favs:
            keyboard.append(InlineKeyboardButton(game, callback_data=f"favs_add_{game}_{user_id}"))
        else:
            keyboard.append(InlineKeyboardButton(f"⭐ {game}", callback_data=f"favs_del_{game}_{user_id}"))
    columns = [keyboard[i : i + row_length] for i in range(0, len(keyboard), row_length)]
    if favs_extra_button:
        columns.append([InlineKeyboardButton("✅ Solo Preferiti", callback_data=f"fav_more_{user_id}")])
    else:
        columns.append([InlineKeyboardButton("Solo Preferiti", callback_data=f"fav_more_{user_id}")])

    columns.append([InlineKeyboardButton("Fine", callback_data=f"fav_close_{user_id}")])
    return columns


async def fav_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = context.bot_data["settings"]
    user_id = str(update.effective_user.id)

    favs = settings[user_id]["favs"]
    game = update.callback_query.data.split("_")[2]
    target_uid = update.callback_query.data.split("_")[3]
    if user_id != target_uid:
        return
    if game not in favs:
        favs.append(game)
    json.dump(settings, open("db/user_settings.json", "w"), indent=4)
    keyboard = make_menu_setting_favs(favs=favs, user_id=user_id, favs_extra_button=settings[user_id]["favs_extra_button"])
    reply_keyboard = InlineKeyboardMarkup(keyboard)
    await update.effective_message.edit_text("Scegli i tuoi giochi preferiti", reply_markup=reply_keyboard)


async def fav_del(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = context.bot_data["settings"]
    user_id = str(update.effective_user.id)

    favs = settings[user_id]["favs"]
    game = update.callback_query.data.split("_")[2]
    target_uid = update.callback_query.data.split("_")[3]
    if user_id != target_uid:
        return
    if game in favs:
        favs.remove(game)
    json.dump(settings, open("db/user_settings.json", "w"), indent=4)
    keyboard = make_menu_setting_favs(favs=favs, user_id=user_id, favs_extra_button=settings[user_id]["favs_extra_button"])
    reply_keyboard = InlineKeyboardMarkup(keyboard)
    await update.effective_message.edit_text("Scegli i tuoi giochi preferiti", reply_markup=reply_keyboard)


async def fav_extra_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = context.bot_data["settings"]
    user_id = str(update.effective_user.id)
    target_uid = update.callback_query.data.split("_")[2]
    if user_id != target_uid:
        return

    favs = settings[user_id]["favs"]
    favs_extra_button = settings[user_id]["favs_extra_button"]
    context.bot_data["settings"][user_id]["favs_extra_button"] = not favs_extra_button
    json.dump(settings, open("db/user_settings.json", "w"), indent=4)

    keyboard = make_menu_setting_favs(favs=favs, user_id=user_id, favs_extra_button=not favs_extra_button)
    reply_keyboard = InlineKeyboardMarkup(keyboard)
    await update.effective_message.edit_text("Scegli i tuoi giochi preferiti", reply_markup=reply_keyboard)


async def fav_close(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    target_uid = update.callback_query.data.split("_")[2]
    if user_id != target_uid:
        return
    await update.effective_message.delete()


async def setting_fav(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # with open("db/user_settings.json") as settings_db:
    #     settings = json.load(settings_db)
    settings = context.bot_data["settings"]
    user_id = str(update.effective_user.id)

    if user_id not in settings:
        settings[user_id] = {}

    if "favs" not in settings[user_id]:
        settings[user_id]["favs"] = []

    if "favs_extra_button" not in settings[user_id]:
        settings[user_id]["favs_extra_button"] = False

    favs = settings[user_id]["favs"]
    # json.dump(settings, open("db/user_settings.json", "w"), indent=4)
    keyboard = make_menu_setting_favs(favs=favs, user_id=user_id, favs_extra_button=settings[user_id]["favs_extra_button"])

    reply_keyboard = InlineKeyboardMarkup(keyboard)

    await update.effective_message.reply_text("Scegli i tuoi giochi preferiti", reply_markup=reply_keyboard)
    return


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)
    logging.info(f"È accaduto un errore!\n============\n{tb_list[-2]}{tb_list[-1]}============")

    await context.bot.send_message(
        chat_id=ID_BOTCENTRAL,
        text=f'<pre><code class="language-python">{tb_string[:4000]}</code></pre>',
        parse_mode="HTML",
    )


async def classifica_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query

    chat_id = query.message.chat.id
    m_id = query.message.id

    await query.answer()

    data = query.data
    if data == "cls_do_nothing":
        return

    _, game, _, day = data.split("_")

    classifica_text = make_single_classifica(game, chat_id=update.effective_chat.id, day=day, limit=6, user_id=update.effective_user.id)
    # date_str = f"== {get_date_from_day(game, day).strftime('%Y-%m-%d')} =="
    # classifica_text = f'{date_str}\n{classifica_text}'

    if not classifica_text:
        classifica_text = "Non c'è niente da vedere qui."

    buttons = make_buttons(game, update.effective_message.message_id, day)

    await context.bot.edit_message_text(
        classifica_text,
        chat_id=chat_id,
        message_id=m_id,
        reply_markup=buttons,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # giochi = [f"<code>{x}</code>" for x in GAMES.keys()]
    # giochi = " · ".join(giochi)
    message = [
        "Questo bot parsa automaticamente i punteggi dei giochi giornalieri, fa una classifica giornaliera e una classifica dei migliori player.",
        "",
        "Ogni giorno vengono assegnati punti ai primi tre giocatori di ogni gioco (3 punti al primo, 2 al secondo e 1 al terzo).",
        "Se un gioco ha meno di tre giocatori, vengono assegnati punti solo ai giocatori presenti, in modo proporzionale.",
        "Alle tre persone con più punti vengono assegnate le medaglie d'oro, d'argento e di bronzo.",
        "",
        # f"I giochi disponibili sono:\n {giochi}",
        "",
        "📚 <b>Lista dei comandi</b> 📚",
        "",
        "📌 /c o /classifica - Mostra la classifica di tutti i giochi",
        "📌 /c <i>[gioco]</i> - Mostra la classifica di un gioco, ad esempio: <code>/c wordle</code>",
        "",
        "📌 /mytoday - Mostra i giochi a cui non hai ancora giocato oggi",
        "📌 /dailyranking - Mostra i punti del giorno corrente",
        "📌 /medaglie - Mostra il medagliere mensile",
        "",
        "📌 /top - Mostra la classifica punteggi all time",
        "📌 /top_medaglie - Mostra il medagliere all time",
        "",
        "📌 /mystats - Mostra le tue statistiche",
        "📌 /favs - Mostra e setta i giochi preferiti",
        "📌 /topgames - Mostra i giochi più giocati",
        "📌 /lista - Mostra la lista di tutti i giochi supportati",
        "",
        "📌 /help - Mostra questo messaggio",
    ]
    message_text = "\n".join(message)
    await update.effective_message.reply_text(message_text, parse_mode="HTML")
    # This will delete the original command after some time (iirc default 10 secs)
    await delete_original_command(update, context)


async def post_single_classifica(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        return await classificona(update, context)

    # This will delete the original command after some time (iirc default 10 secs)
    await delete_original_command(update, context)

    # print(context.args)
    # print(context.args[0].lower())
    # print([x.lower() for x in GAMES.keys()])
    if context.args[0].lower() not in [x.lower() for x in GAMES.keys()]:
        return await classificona(update, context)

    else:
        game = correct_name(context.args[0])
        day = get_day_from_date(GAMES[game]["date"], GAMES[game]["day"], game, datetime.date.today())

        classifica_text = make_single_classifica(game, chat_id=update.effective_chat.id, limit=6, user_id=update.effective_user.id)

        if not classifica_text:
            classifica_text = "Non c'è niente da vedere qui."
        buttons = make_buttons(game, update.effective_message.message_id, day)

        await update.effective_message.reply_text(classifica_text, reply_markup=buttons, parse_mode="HTML", disable_web_page_preview=True)


async def top_players(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.id != ID_GIOCHINI:
        return

    message = "Classifica ALL TIME:\n"

    query = (
        Punti.select(Punti.user_name, peewee.fn.SUM(Punti.punti).alias("totale"))
        .order_by(peewee.fn.SUM(Punti.punti).desc())
        .group_by(Punti.user_name)
        .limit(20)
    )

    if not query:
        return await update.message.reply_text("Non ci sono ancora giocatori.")

    for i, q in enumerate(query, start=1):
        if i in [1, 2, 3]:
            message += f"{MEDALS[i]} [{q.totale}] {q.user_name}\n"
        else:
            message += f"[{q.totale}] {q.user_name}\n"

    await update.message.reply_text(text=message, parse_mode="HTML", disable_web_page_preview=True)


async def top_medaglie(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.id != ID_GIOCHINI:
        return

    medaglie_str = medaglie_count(monthly=False)
    if not medaglie_str:
        message = "Niente da vedere"
    else:
        message = medaglie_str

    await update.message.reply_text(text=message, parse_mode="HTML", disable_web_page_preview=True)


async def top_games(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # if update.effective_chat.id != ID_GIOCHINI:
    #     return
    days = 7

    if context.args:
        try:
            days = int(context.args[0])
        except ValueError:
            pass

    message = f"Classifica dei giochi degli ultimi {days} giorni:\n"

    classifica = make_games_classifica(days)

    if not classifica:
        classifica = "Non so che dire"

    message += classifica

    await update.message.reply_text(text=message, parse_mode="HTML", disable_web_page_preview=True)


async def classificona(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    messaggio = ""
    for game in GAMES.keys():
        classifica = make_single_classifica(game, chat_id=update.effective_chat.id, limit=3)

        # print(make_single_classifica(game, chat_id=update.effective_chat.id, limit=3, data=True))

        if classifica:
            messaggio += classifica + "\n"

    if messaggio:
        await update.message.reply_text(messaggio, parse_mode="HTML")
    return


async def link_single_game(update: Update, context: ContextTypes.DEFAULT_TYPE, correct_game) -> None:
    game = correct_game
    GAME = GAMES.get(game, None)

    if not GAME:
        return

    day = get_day_from_date(GAME["date"], GAME["day"], game, datetime.date.today())
    message = f'<a href="{GAME["url"]}">{GAME["emoji"]} {game} #{day}</a>'
    mymsg = await update.message.reply_html(message)
    command_msg = update.message
    context.job_queue.run_once(delete_post, 5, data=[mymsg, command_msg], name=f"myday_delete_{str(update.effective_message.id)}")
    return


async def parse_punteggio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    # context.giochino will be a list of a single class that can handle the game, built by the GameFilter
    giochino = context.giochino[0]
    giochino = giochino(update)
    result = giochino.punteggio

    # This is a way to skip a known, unsupported game.
    if giochino.message == "ignora":
        await update.message.set_reaction(reaction="👌")
        return

    if giochino.message == "sconosciuto":
        await update.message.set_reaction(reaction="🤔")
        return


    # If it's a lost game, send a message and change the score to 9999999
    play_is_lost = False
    if giochino.is_lost:
        if update.effective_chat.id != ID_TESTING:
            await update.message.reply_text(f"{giochino.lost_message}")
            await update.message.set_reaction(reaction="😭")
        result["tries"] = "9999999"  # Tries have to be populated nonetheless
        play_is_lost = True

    # We convert stars None to stars 0 - if the game has stars
    if giochino.has_extra and result.get("stars", None) is None:
        result["stars"] = 0

    # Testing debug
    if update.effective_chat.id == ID_TESTING:
        import pprint
        if result is None:
            result == ''
        rawresult = pprint.pformat(result, width=300).replace("<", "less").replace(">", "more")
        rawtext = pprint.pformat(update.message.text, width=300).replace("<", "less").replace(">", "more")
        # await update.message.reply_html(f'<code>{bytes(update.effective_message.text, "utf-8")}</code>') / Bytes debug
        await update.message.reply_html(
            f'<code>{rawtext},\n</code>\n\n<code>{rawresult},\n</code><pre><code class="language-python">{update.message.text.replace("<", "less").replace(">", "more")}</code></pre>'
        )
        return

    if result:  # should always be the case
        query = Punteggio.select().where(
            Punteggio.day == str_as_int(result["day"]),
            Punteggio.game == result["name"],
            Punteggio.user_id == result["user_id"],
            Punteggio.chat_id == update.effective_chat.id,
        )

        if query:
            await update.message.reply_text(f"Hai già giocato a {giochino._name} oggi.")
            await update.message.set_reaction(reaction="🤨")
            return



        streak = streak_at_day(user_id=int(result["user_id"]), game=result["name"], day=str_as_int(result["day"]))
        # streak is how many consecutive plays there are before this one. So we add 1 to it when saving the score.

        Punteggio.create(
            date=datetime.datetime.now(),
            timestamp=int(result["timestamp"]),
            chat_id=int(update.message.chat.id),
            user_id=int(result["user_id"]),
            user_name=result["user_name"],
            game=result["name"],
            day=str_as_int(result["day"]),
            tries=int(result["tries"]),
            extra=str(result.get("stars", None)),
            streak=streak + 1,
            lost=play_is_lost,
        )

        if play_is_lost:
            logging.info(f"Aggiungo tentativo di {result['user_name']} per {result['name']} #{result['day']} (fallito)")
            return

        today_game = int(get_day_from_date(GAMES[result["name"]]["date"], GAMES[result["name"]]["day"], result["name"], datetime.date.today()))

        if str_as_int(result["day"]) in [today_game, today_game - 1]:
            message = f'Classifica di {result["name"]} aggiornata.\n'
            classifica = make_single_classifica(result["name"], update.effective_chat.id, day=result["day"])
            if classifica:
                classifica = f"{message}\n{classifica}"
                streak = streak + 1
                if streak:
                    classifica += f"\nCurrent streak: {streak}"
                long_streak = longest_streak(user_id=result["user_id"], game=result["name"])
                if long_streak:
                    if long_streak > streak:
                        classifica += f"\nLongest streak: {long_streak}"
                    else:
                        classifica += "\nLongest streak: current"
                mymsg = await update.message.reply_html(classifica)
                await mymsg.reply_to_message.set_reaction(reaction="✍")
                context.job_queue.run_once(minimize_post, 60, data=mymsg, name=f"minimize_{str(update.effective_message.id)}")
            else:
                mymsg = await update.message.reply_html("Ah, non l'ha ancora fatto nessuno, fico.")
                context.job_queue.run_once(delete_post, 60, data=[mymsg], name=f"delete_post_{str(update.effective_message.id)}")

        else:
            days_ago = int(today_game) - str_as_int(result["day"])
            if days_ago < 0:
                await update.message.reply_text('Ho salvato il tuo punteggio del futuro.')
            else:
                await update.message.reply_text(f'Ho salvato il tuo punteggio di {days_ago} giorni fa.')

        logging.info(f"Aggiungo punteggio di {result['user_name']} per {result['name']} #{result['day']} ({result['tries']})")

    else:  # should never be the case
        print('wtf?')


async def manual_daily_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id == ADMIN_ID:
        await daily_reminder(context)


async def manual_backup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id == ADMIN_ID:
        return await make_backup(context)


async def manual_riassunto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id == ADMIN_ID:
        context.bot_data["manual_riassunto"] = True
        return await riassunto_serale(context)


async def mytoday(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # message = 'Ecco a cosa hai già giocato oggi:\n'
    played_today = set()
    not_played_today = set()
    not_played_favs = []
    not_played_regs = []
    favorites = []
    solo_preferiti = False

    if str(update.effective_user.id) in context.bot_data["settings"]:
        favorites = context.bot_data["settings"][str(update.effective_user.id)]["favs"]
        solo_preferiti = context.bot_data["settings"][str(update.effective_user.id)].get("favs_extra_button", False)

    # Divido i giochi in giocati e non giocati
    for game in GAMES.keys():
        day = get_day_from_date(GAMES[game]["date"], GAMES[game]["day"], game, datetime.date.today())
        query = Punteggio.select().where(Punteggio.day == int(day), Punteggio.game == game, Punteggio.user_id == update.message.from_user.id)

        if query:
            played_today.add(game)
        else:
            not_played_today.add(game)

    # divido i non giocati tra favs e regulars
    for game in not_played_today:
        if game in favorites:
            not_played_favs.append(game)
        else:
            not_played_regs.append(game)

    # non ha giocate
    if not played_today:
        message = "Non hai giocato a nulla oggi.\n\n"

    # ha giocato a tutti i giochi
    elif not not_played_today:
        message = "Hai giocato a tutto!"

    # ha giocato a qualcosa
    else:
        if not_played_favs:
            message = "Ti manca da giocare:\n\n"

        elif not not_played_favs and favorites:
            message = "Hai giocato a tutti i preferiti!\n\n"

        else:
            message = "Ti manca da giocare:\n\n"

    if not_played_favs:
        for game in not_played_favs:
            message += f'<a href="{GAMES[game]["url"]}">⭐ {GAMES[game]["emoji"]} {game}</a>\n'

    message += "\n"

    if not_played_regs and not solo_preferiti:
        for game in not_played_regs:
            message += f'<a href="{GAMES[game]["url"]}">{GAMES[game]["emoji"]} {game}</a>\n'

    if solo_preferiti:
        buttons = [[InlineKeyboardButton("Tutti i giochi", callback_data=f"myday_more_{update.effective_user.id}")]]
        keyboard = InlineKeyboardMarkup(buttons)
        mymsg = await update.message.reply_text(message, parse_mode="HTML", disable_web_page_preview=True, reply_markup=keyboard)
    else:
        mymsg = await update.message.reply_text(message, parse_mode="HTML", disable_web_page_preview=True)
    command_msg = update.message
    context.job_queue.run_once(delete_post, 60, data=[mymsg, command_msg], name=f"myday_delete_{str(update.effective_message.id)}")


async def mytoday_full(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    target_uid = update.callback_query.data.split("_")[2]
    if user_id != target_uid:
        return

    played_today = set()
    not_played_today = set()
    for game in GAMES.keys():
        day = get_day_from_date(GAMES[game]["date"], GAMES[game]["day"], game, datetime.date.today())
        query = Punteggio.select().where(Punteggio.day == int(day), Punteggio.game == game, Punteggio.user_id == user_id)
        if query:
            played_today.add(game)
        else:
            not_played_today.add(game)

    if not played_today:
        message = "Non hai giocato a nulla oggi.\n\n"

    elif not_played_today:
        message = "Ti manca da giocare:\n\n"

    favs = []
    regs = []
    favorites = []
    if str(user_id) in context.bot_data["settings"]:
        favorites = context.bot_data["settings"][str(user_id)]["favs"]

    for game in not_played_today:
        if game in favorites:
            favs.append(game)
        else:
            regs.append(game)
    if favs:
        for game in favs:
            message += f'<a href="{GAMES[game]["url"]}">⭐ {GAMES[game]["emoji"]} {game}</a>\n'
    message += "\n"
    if regs:
        for game in regs:
            message += f'<a href="{GAMES[game]["url"]}">{GAMES[game]["emoji"]} {game}</a>\n'

    elif not not_played_today:
        message = "Hai giocato a tutto!"

    # edit the message
    await update.effective_message.edit_text(message, parse_mode="HTML", disable_web_page_preview=True)


async def list_games(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = "Lista dei giochi:\n"

    for game in GAMES.keys():
        message += f'{GAMES[game]["emoji"]} {game}: {GAMES[game]["url"]}\n'

    await update.message.reply_text(message, parse_mode="HTML", disable_web_page_preview=True)
    # This will delete the original command after some time (iirc default 10 secs)
    await delete_original_command(update, context)


async def mystats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        message = personal_stats(update.effective_user.id)
    except Exception as e:
        message = f"Ho qualche problema, scusa ({e})"

    await update.message.reply_text(message, parse_mode="HTML", disable_web_page_preview=True)
    if update.effective_user.id == ADMIN_ID and "-group" in context.args:
        group_message = group_stats(update.effective_chat.id)
        await update.message.reply_text(group_message, parse_mode="HTML", disable_web_page_preview=True)


async def medaglie_mensile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.id != ID_GIOCHINI:
        return

    medaglie_str = medaglie_count()
    if not medaglie_str:
        message = "Niente da vedere"
    else:
        message = medaglie_str

    await update.message.reply_text(text=message, parse_mode="HTML", disable_web_page_preview=True)


async def riassunto_serale(context: ContextTypes.DEFAULT_TYPE) -> None:
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)

    model = "alternate-with-lost"
    cambiamenti = daily_ranking(model, yesterday)

    message = f"<b>Ecco come è andata oggi {yesterday.strftime('%Y-%m-%d')}</b>:\n\n"

    for user, points in cambiamenti:
        user_id, user_name = user.split("_|_")
        user_id = int(user_id)

        message += f"+{points} {user_name}\n"
        if not context.bot_data.get("manual_riassunto", None):
            Punti.create(date=yesterday, user_id=user_id, user_name=user_name, punti=points)

    # Medals
    i = 0

    for user, points in cambiamenti[:3]:
        user_id, user_name = user.split("_|_")
        user_id = int(user_id)

        if not context.bot_data.get("manual_riassunto", None):
            Medaglia.create(
                date=yesterday,
                timestamp=int(time.time()),
                chat_id=int(ID_GIOCHINI),
                user_id=int(user_id),
                user_name=user_name,
                gold=1 if i == 0 else None,
                silver=1 if i == 1 else None,
                bronze=1 if i == 2 else None,
            )
        i += 1

    await context.bot.send_message(chat_id=ID_GIOCHINI, text=message, parse_mode="HTML", disable_web_page_preview=True)

    this_month = yesterday.replace(day=1)
    message = f"<b>Classifica di questo mese ({this_month.strftime('%B')})</b>:\n\n"

    query = (
        Punti.select(Punti.user_name, peewee.fn.SUM(Punti.punti).alias("totale"))
        .where(Punti.date >= this_month)
        .order_by(peewee.fn.SUM(Punti.punti).desc())
        .group_by(Punti.user_name)
        .limit(10)
    )

    for q in query:
        message += f"[{q.totale}] {q.user_name}\n"

    next_month = this_month.replace(day=28) + datetime.timedelta(days=4)
    last_day_of_month = next_month - datetime.timedelta(days=next_month.day)
    if yesterday == last_day_of_month:
        message += "Ultimo giorno del mese!! Classifica finale!!"

    await context.bot.send_message(chat_id=ID_GIOCHINI, text=message, parse_mode="HTML", disable_web_page_preview=True)

    medaglie_str = medaglie_count()

    await context.bot.send_message(chat_id=ID_GIOCHINI, text=medaglie_str, parse_mode="HTML", disable_web_page_preview=True)
    context.bot_data["manual_riassunto"] = False


async def classifica_istantanea(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    model = "alternate-with-lost"
    if "-skip-empty" in context.args:
        model = "skip-empty"
    elif "-alternate" in context.args:
        model = "alternate"
    elif "-no-timestamp" in context.args:
        model = "no-timestamp"
    elif "-alternate-with-lost" in context.args:
        model = "alternate-with-lost"

    cambiamenti = daily_ranking(model)

    message = "Ecco la classifica temporanea di oggi:\n"

    for user, points in cambiamenti:
        user_id, user_name = user.split("_|_")
        user_id = int(user_id)

        message += f"+{points} {user_name}\n"

    await update.message.reply_text(message, parse_mode="HTML", disable_web_page_preview=True)

    # This will delete the original command after some time (iirc default 10 secs)
    await delete_original_command(update, context, 60)


async def daily_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    categorie = set([GAMES[x]["category"] for x in GAMES.keys()])
    message = "Buongiorno, ecco a cosa si gioca oggi!\n\n"
    for categoria in categorie:
        message += f"<b>{categoria}</b>\n"
        for game in GAMES.keys():
            if GAMES[game]["category"] == categoria:
                day = get_day_from_date(GAMES[game]["date"], GAMES[game]["day"], game, datetime.date.today())
                message += f'<a href="{GAMES[game]["url"]}">{GAMES[game]["emoji"]} {game} #{day}</a>\n'
        message += "\n"
    # for game in GAMES.keys():
    #     day = get_day_from_date(GAMES[game]['date'], GAMES[game]['day'], game, datetime.date.today())
    #     message += f'<a href="{GAMES[game]["url"]}">{GAMES[game]["emoji"]} {game} #{day}</a>\n'
    mypost = await context.bot.send_message(chat_id=ID_GIOCHINI, text=message, disable_web_page_preview=True, parse_mode="HTML")
    await mypost.pin(disable_notification=True)


async def make_backup(context: ContextTypes.DEFAULT_TYPE) -> None:
    now = datetime.datetime.today().strftime("%Y%m%d_%H%M%S")

    backup_dir = "backups"
    archive_name = f"{backup_dir}/giochini-{now}-backup.zip"
    files_to_backup = ["db/sqlite.db"]

    with zipfile.ZipFile(archive_name, "w") as zip_ref:
        for file in files_to_backup:
            zip_ref.write(file)

    await context.bot.send_document(chat_id=BACKUP_DEST, document=open(archive_name, "rb"))
    logging.info("[AUTO] Backup DB eseguito.")


async def minimize_post(context: ContextTypes.DEFAULT_TYPE) -> None:
    message = context.job.data
    delete_message = True
    if delete_message:
        await message.delete()
    else:
        await message.edit_text("Punteggio salvato.")


async def delete_original_command(update: Update, context: ContextTypes.DEFAULT_TYPE, after_seconds: int = 10) -> None:
    command_msg = update.message
    context.job_queue.run_once(delete_post, after_seconds, data=[command_msg], name=f"myday_delete_{str(update.effective_message.id)}")


async def delete_post(context: ContextTypes.DEFAULT_TYPE) -> None:
    messages: list = context.job.data
    for message in messages:
        await message.delete()


async def launch_web_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # display our web-app!
    # kb = [
    #     [InlineKeyboardButton(
    #         "Show me my Web-App!",
    #        web_app=WebAppInfo("https://trifase.github.io/emily-mini-app/"), # obviously, set yours here.
    #        callback_data='webapp_launch'
    #     )]
    # ]
    # await update.message.reply_text("Let's do this...", reply_markup=InlineKeyboardMarkup(kb))

    kb = [
        [
            KeyboardButton(
                "Show me my Web-App!",
                web_app=WebAppInfo("https://trifase.github.io/emily-mini-app/index.html?type=sale&sort=price_descending&page=43"),  # obviously, set yours here.
                #    callback_data='webapp_launch'
            )
        ]
    ]
    await update.message.reply_text("Let's do this...", reply_markup=ReplyKeyboardMarkup(kb))


async def handle_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = json.loads(update.to_json())

    import html
    import pprint

    rawtext = pprint.pformat(data)
    # print(rawtext)
    rawtext = html.escape(rawtext)
    # print('callback data:', update.callback_query.data)
    # wat = await context.bot.answer_callback_query(update.callback_query.id)
    # print(wat)
    await update.message.reply_html(f'<pre><code class="language-python">{rawtext}</code></pre>', reply_markup=ReplyKeyboardRemove())


async def enable_debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        if "debug_message" not in context.bot_data:
            context.bot_data["debug_mode"] = True
        context.bot_data["debug_mode"] = True
        await update.message.reply_html(f"Debug mode: {context.bot_data['debug_mode']}")
    return


async def disable_debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        if "debug_message" not in context.bot_data:
            context.bot_data["debug_mode"] = False
        context.bot_data["debug_mode"] = False
        await update.message.reply_html(f"Debug mode: {context.bot_data['debug_mode']}")
    return


async def spell_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "debug_mode" not in context.bot_data:
        context.bot_data["debug_mode"] = False

    if context.bot_data["debug_mode"]:
        text = update.message.text
        mess = ""
        for c in text:
            mess += f"{c}: {ord(c)}\n"
        await update.message.reply_html(f'<pre><code class="language-python">{text.encode("unicode-escape")}</code></pre>')
        await update.message.reply_html(f'<pre><code class="language-python">{mess}</code></pre>')

    return

async def unknown_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    correct_game_names = [x for x in GAMES.keys()]
    game_names = [x.lower() for x in GAMES.keys()]
    game = update.message.text.lower().replace('/', '')
    if game in game_names:
        correct_game = correct_game_names[game_names.index(game)]
        return await link_single_game(update, context, correct_game)
    return


async def post_init(app: Application) -> None:
    Punteggio.create_table()
    Punti.create_table()
    Medaglia.create_table()
    # Setting.create_table()

    # Recupero i settings e li storo in memoria
    if "settings" not in app.bot_data:
        app.bot_data["settings"] = {}

    with open("db/user_settings.json") as settings_db:
        settings = json.load(settings_db)
        app.bot_data["settings"] = settings
    logger.info("Pronti!")


def main():
    defaults = Defaults(
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )

    builder = ApplicationBuilder()
    builder.token(TOKEN)
    builder.defaults(defaults)
    builder.post_init(post_init)

    app = builder.build()

    j = app.job_queue
    j.run_daily(daily_reminder, datetime.time(hour=7, minute=0, tzinfo=pytz.timezone("Europe/Rome")), data=None)
    j.run_daily(riassunto_serale, datetime.time(hour=1, minute=0, tzinfo=pytz.timezone("Europe/Rome")), data=None)
    j.run_daily(make_backup, datetime.time(hour=2, minute=0, tzinfo=pytz.timezone("Europe/Rome")), data=None)

    app.add_handler(CommandHandler("classificona", classificona), 1)
    app.add_handler(CommandHandler("giochiamo", manual_daily_reminder), 1)
    app.add_handler(CommandHandler(["mytoday", "myday", "my", "today", "daily"], mytoday), 1)
    app.add_handler(CommandHandler(["mystats", "mystat", "stats", "statistiche"], mystats), 1)
    app.add_handler(CommandHandler("help", show_help), 1)
    app.add_handler(CommandHandler(["list", "lista"], list_games), 1)
    app.add_handler(CommandHandler("backup", manual_backup), 1)
    app.add_handler(CommandHandler("riassuntone", manual_riassunto), 1)
    app.add_handler(CommandHandler("dailyranking", classifica_istantanea), 1)

    app.add_handler(CommandHandler("webapp", launch_web_ui))
    # app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))

    # app.add_handler(CallbackQueryHandler(handle_web_app_data, pattern=r"^webapp_launch"))

    app.add_handler(CommandHandler(["c", "classifica"], post_single_classifica), 2)
    app.add_handler(CommandHandler("top", top_players), 1)
    app.add_handler(CommandHandler("top_medaglie", top_medaglie), 1)
    app.add_handler(CommandHandler("medaglie", medaglie_mensile), 1)
    app.add_handler(CommandHandler("favs", setting_fav), 3)

    app.add_handler(MessageHandler(filters.COMMAND, unknown_command_handler), 1000)

    app.add_handler(CommandHandler("topgames", top_games), 1)
    app.add_handler(CallbackQueryHandler(classifica_buttons, pattern=r"^cls_"))
    app.add_handler(CallbackQueryHandler(fav_add, pattern=r"^favs_add_"))
    app.add_handler(CallbackQueryHandler(fav_del, pattern=r"^favs_del_"))
    app.add_handler(CallbackQueryHandler(fav_close, pattern=r"^fav_close"))
    app.add_handler(CallbackQueryHandler(fav_extra_toggle, pattern=r"^fav_more"))

    app.add_handler(CallbackQueryHandler(mytoday_full, pattern=r"^myday_more"))

    app.add_handler(MessageHandler(filters.ALL, spell_message), -150)
    app.add_handler(CommandHandler("enable_debug", enable_debug), 211)
    app.add_handler(CommandHandler("disable_debug", disable_debug), 212)

    app.add_handler(MessageHandler(giochini_results_filter & ~filters.UpdateType.EDITED, parse_punteggio))

    # Error handler
    app.add_error_handler(error_handler)

    app.run_polling(drop_pending_updates=False, allowed_updates=Update.ALL_TYPES)


main()
