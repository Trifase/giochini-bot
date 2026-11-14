import asyncio
import datetime
from collections import defaultdict
import html
import json
import locale
import logging
import logging.handlers
import sys
import os
import time
import traceback
import zipfile

import httpx
import peewee
import pytz
from telegram import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    LinkPreviewOptions,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    ReplyParameters,
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
    TypeHandler,
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
    HEARTBEAT_ID,
    STAR_SYMBOL,
    Medaglia,
    Punteggio,
    Punti,
)
import config
from games import ALL_GAMES as GAMES
from games import GameFilter, invalidate_anchor_cache
from utils import (
    Classifica,
    Giocata,
    GameStatus,
    GameAnchor,
    GiocoBonus,
    PuntiBonus,
    POOP_MEDAL,
    correct_name,
    daily_ranking,
    ensure_gioco_bonus_schema,
    ensure_punteggi_pk_migration,
    ensure_utenti_schema_and_backfill,
    Utente,
    get_display_names,
    get_day_from_date,
    get_date_from_day,
    get_all_bonuses_for_date,
    get_bonus_game,
    get_game_multiplier,
    get_new_games_for_date,
    get_reenabled_games_for_date,
    grant_reenabled_game_bonus,
    pick_or_get_bonus_game,
    sync_new_game_bonuses,
    sync_reenabled_game_bonuses,
    group_stats,
    longest_streak,
    make_buttons,
    medaglie_count,
    personal_stats,
    print_progressbar,
    str_as_int,
    streak_at_day,
    new_classifica,
    process_tries,
    seconds_to_time,
    sync_user,
    update_streak,
)

# Logging setup
logger = logging.getLogger()

os.makedirs("logs", exist_ok=True)
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


def format_bonus_badge(multiplier: int, bonus_type: str | None, bold: bool = False) -> str:
    """Formats a bonus badge such as ' [🎰 3x]', ' [🆕 2x]' or ' [✨ 3x]'."""
    if not bonus_type or multiplier <= 1:
        return ""
    if bonus_type == "new_game":
        icon = getattr(config, "NEW_GAME_EMOJI", "🆕")
    elif bonus_type == "reenabled":
        icon = getattr(config, "REENABLED_GAME_EMOJI", "✨")
    else:
        icon = "🎰"
    badge = f"[{icon} {multiplier}x]"
    return f" <b>{badge}</b>" if bold else f" {badge}"


def build_game_badge_getter(target_date: datetime.date = None, bold: bool = False):
    """Returns a lookup function mapping game_name -> formatted bonus badge for target_date."""
    bonuses = get_all_bonuses_for_date(target_date or datetime.date.today(), auto_pick_jolly=True)

    def get_game_badge(g_name: str) -> str:
        mult, b_type = bonuses.get(g_name, (1, None))
        return format_bonus_badge(mult, b_type, bold=bold)

    return get_game_badge


def make_single_classifica(game: str, chat_id: int, day: int = None, limit: int = 6, user_id=None, to_string=True, show_lost=False) -> str:
    day = day or get_day_from_date(GAMES[game]["date"], GAMES[game]["day"], game, datetime.date.today())
    # print(f"Making classifica for {game} #{day}")
    emoji = GAMES[game]["emoji"]
    url = GAMES[game]["url"]

    game_date = get_date_from_day(game, day)
    today = datetime.date.today()
    multiplier, bonus_type = get_game_multiplier(game, game_date, auto_pick_jolly=(game_date == today))

    # user_id_found = False
    # if show_lost:
    query = (
            Punteggio.select(Punteggio.user_name, Punteggio.tries, Punteggio.user_id, Punteggio.extra)
            .where(
                Punteggio.day == day,
                Punteggio.game == game,
                Punteggio.chat_id == chat_id
            )
            .order_by(Punteggio.tries, Punteggio.extra.cast('INTEGER').desc())
            # .limit(limit)
        )
    
    if not query:
        return None

    classifica = Classifica()
    classifica.game = game
    classifica.day = day
    classifica.date = game_date
    classifica.emoji = emoji
    badge = format_bonus_badge(multiplier, bonus_type)
    classifica.header = f'<a href="{url}"><b>{emoji} {game} #{day}</b></a>{badge}'
    classifica.giocate = [Giocata(user_id=g.user_id, user_name=g.user_name, tries=g.tries, game=game, extra=g.extra if g.extra else 0) for g in query]
    classifica.order_and_position()

    classifica.assign_stars('default', multiplier=multiplier)

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
        if GAMES[game].get("disabled", False):
            continue
        if game not in favs:
            keyboard.append(InlineKeyboardButton(game, callback_data=f"favs_add_{game}_{user_id}"))
        else:
            keyboard.append(InlineKeyboardButton(f"⭐ {game}", callback_data=f"favs_del_{game}_{user_id}"))
    columns = [keyboard[i : i + row_length] for i in range(0, len(keyboard), row_length)]
    if favs_extra_button:
        columns.append([InlineKeyboardButton("✅ Solo Preferiti", callback_data=f"fav_more_{user_id}")])
    else:
        columns.append([InlineKeyboardButton("Solo Preferiti", callback_data=f"fav_more_{user_id}")])

    columns.append([InlineKeyboardButton("Fine", callback_data=f"fav_close_{user_id}", api_kwargs={"style": "success"})])
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
    # delete the user message
    await update.effective_message.reply_text("Scegli i tuoi giochi preferiti", reply_markup=reply_keyboard)
    await update.effective_message.delete()
    return


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)
    logging.info(f"È accaduto un errore!\n============\n{tb_list[-2]}{tb_list[-1]}============")

    chat_id = update.effective_chat.id
    link_chat_id = str(chat_id).replace("-100", "")

    message_id = None

    if update.effective_message and update.effective_message.message_id:
        message_id = update.effective_message.message_id

    emoji_link = ''
    if link_chat_id and message_id:
        emoji_link = f'<a href="t.me/c/{link_chat_id}/{message_id}">🔗</a> '
    
    await context.bot.send_message(
        chat_id=ID_BOTCENTRAL,
        text=f'{emoji_link}ERRORE!',
        parse_mode="HTML",
    )
    await update.message.forward(ID_BOTCENTRAL)


    tb_escaped = html.escape(tb_string[:4000])
    await context.bot.send_message(
        chat_id=ID_BOTCENTRAL,
        text=f'<pre><code class="language-python">{tb_escaped}</code></pre>',
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
    message = [
        "Questo bot parsa automaticamente i punteggi dei giochi giornalieri, fa una classifica giornaliera e una classifica dei migliori player.",
        "",
        f"Alla fine di ogni giorno vengono assegnati dei punti {STAR_SYMBOL} in base ai risultati ottenuti in tutti i giochi, utilizzando l'algoritmo SWG4 Zip War Airganon.",
        "Alle tre persone con più punti vengono assegnate le medaglie d'oro, d'argento e di bronzo.",
        "",
        "📚 <b>Lista dei comandi</b> 📚",
        "",
        "<b>🎮 Oggi</b>",
        "📌 /myday - Giochi a cui non hai ancora giocato oggi",
        "📌 /myscore - Tuo punteggio e piazzamenti di oggi",
        "📌 /bonus - Giochi bonus attivi oggi (Jolly e Nuovi)",
        "📌 /favs - Scegli i tuoi giochi preferiti",
        "📌 /<i>nomegioco</i> - Link rapido al gioco di oggi (es. <code>/connections</code>, dura 5s)",
        "",
        "<b>🏆 Classifiche & Medaglie</b>",
        "📌 /ranking (o /dailyranking, /oggi) - Classifica generale di oggi",
        "📌 /c (o /classifica) - Classifica di tutti i giochi di oggi",
        "📌 /c <i>[gioco]</i> - Classifica di un gioco (es. <code>/c wordle</code>)",
        "📌 /medaglie - Medagliere mensile",
        "📌 /top - Classifica punti All-Time",
        "📌 /topmedaglie - Medagliere All-Time",
        "📌 /puntioggi - Punti bonus/malus assegnati oggi",
        "📌 /simuladaily <i>[modello]</i> - Simula la classifica odierna",
        "",
        "<b>📊 Statistiche & Giochi</b>",
        "📌 /mystats <i>[gioco]</i> - Le tue statistiche (globali o per gioco)",
        "📌 /weekstat - Statistiche degli ultimi 7 giorni",
        "📌 /groupstats - Statistiche del gruppo",
        "📌 /topgames <i>[giorni]</i> - Giochi più giocati (default 7gg)",
        "📌 /list - Lista di tutti i giochi supportati",
        "📌 /help - Mostra questo messaggio",
    ]

    if update.effective_user and update.effective_user.id == ADMIN_ID:
        message.extend([
            "",
            "<b>🔧 Admin</b>",
            "• /stelle - Assegna/resetta punti bonus o malus",
            "• /setanchor - Imposta il #giorno di un gioco",
            "• /ask <i>&lt;domanda&gt;</i> - Query AI sul database",
            "• /giochiamo | /nuovigiochi | /riassuntone - Trigger manuali",
            "• /listdisabled | /checkunused | /checkdisable - Stato giochi",
            "• /backup | /refresh | /restart - Manutenzione",
            "• /enable_debug | /disable_debug | /debug - Debug",
        ])

    message_text = "\n".join(message)
    mymsg = await update.effective_message.reply_text(message_text, parse_mode="HTML")
    schedule_delete(context, [mymsg, update.effective_message], after_seconds=60, name_prefix="help_delete", msg_id=update.effective_message.message_id)


async def post_single_classifica(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        return await classificona(update, context)

    query_raw = " ".join(context.args).strip().lower()
    query_nospace = query_raw.replace(" ", "")
    game = None
    for g_name in GAMES.keys():
        if g_name.lower() == query_raw or g_name.lower().replace(" ", "") == query_nospace:
            game = g_name
            break

    if not game:
        return

    # This will delete the original command after some time (iirc default 10 secs)
    await delete_original_command(update, context)

    day = get_day_from_date(GAMES[game]["date"], GAMES[game]["day"], game, datetime.date.today())

    classifica_text = make_single_classifica(game, chat_id=update.effective_chat.id, limit=6, user_id=update.effective_user.id, show_lost=True)

    if not classifica_text:
        classifica_text = "Non c'è niente da vedere qui."
    buttons = make_buttons(game, update.effective_message.message_id, day)

    await update.effective_message.reply_text(classifica_text, reply_markup=buttons, parse_mode="HTML", disable_web_page_preview=True)


async def top_players(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.id != ID_GIOCHINI:
        return

    message = "Classifica ALL TIME:\n"

    # query = (
    #     Punti.select(Punti.user_name, peewee.fn.SUM(Punti.punti).alias("totale"))
    #     .order_by(peewee.fn.SUM(Punti.punti).desc())
    #     .group_by(Punti.user_name)
    #     .limit(20)
    # )

    query = (
        Punti.select(Punti.user_id, Punti.user_name, peewee.fn.SUM(Punti.punti).alias("totale"))
        .order_by(peewee.fn.SUM(Punti.punti).desc())
        .group_by(Punti.user_id)
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


async def week_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=6)

    days = [start_date + datetime.timedelta(days=i) for i in range(7)]

    query = (
        Punteggio.select(Punteggio.date, Punteggio.game, Punteggio.user_id, Punteggio.user_name, Punteggio.lost)
        .where(
            Punteggio.chat_id == chat_id,
            Punteggio.date >= start_date
        )
    )

    DAY_NAMES_IT = {0: "Lu", 1: "Ma", 2: "Me", 3: "Gi", 4: "Ve", 5: "Sa", 6: "Do"}

    counts_by_date = {d: 0 for d in days}
    users_by_date = {d: set() for d in days}
    total_unique_users = set()
    game_counts = defaultdict(int)
    user_names = {}
    user_play_counts = defaultdict(int)
    total_plays = 0
    total_lost = 0

    for p in query:
        p_date = None
        if isinstance(p.date, datetime.datetime):
            p_date = p.date.date()
        elif isinstance(p.date, datetime.date):
            p_date = p.date
        elif isinstance(p.date, str):
            try:
                p_date = datetime.datetime.strptime(p.date[:10], "%Y-%m-%d").date()
            except ValueError:
                pass

        if p_date and p_date in counts_by_date:
            counts_by_date[p_date] += 1
            users_by_date[p_date].add(p.user_id)
            total_unique_users.add(p.user_id)
            total_plays += 1
            if p.lost:
                total_lost += 1
            game_counts[p.game] += 1
            user_names[p.user_id] = p.user_name
            user_play_counts[p.user_id] += 1

    if total_plays == 0:
        await update.message.reply_text("Non ci sono ancora giocate registrate negli ultimi 7 giorni.")
        return

    max_count = max(counts_by_date.values())
    max_bars = 20
    chart_lines = []

    for d in days:
        cnt = counts_by_date[d]
        u_cnt = len(users_by_date[d])
        day_name = DAY_NAMES_IT[d.weekday()]
        if max_count > 0 and cnt > 0:
            num_bars = max(1, int(round((cnt / max_count) * max_bars)))
            bars = "|" * num_bars
        else:
            bars = ""
        bars_padded = bars.ljust(20)
        chart_lines.append(f"{day_name}: {bars_padded}   🎮{cnt:3d}  👤{u_cnt:2d}")

    chart_str = "\n".join(chart_lines)

    top_game_str = "N/D"
    if game_counts:
        top_game_name = max(game_counts, key=game_counts.get)
        top_game_cnt = game_counts[top_game_name]
        top_game_str = f"<b>{top_game_name}</b> ({top_game_cnt} giocate)"

    top_user_str = "N/D"
    if user_play_counts:
        top_user_id = max(user_play_counts, key=user_play_counts.get)
        top_user_name = user_names[top_user_id]
        top_user_cnt = user_play_counts[top_user_id]
        top_user_str = f"<b>{top_user_name}</b> ({top_user_cnt} giocate)"

    lost_pct = round(total_lost / total_plays * 100, 1) if total_plays else 0.0
    total_users_count = len(total_unique_users)

    start_str = days[0].strftime("%d/%m")
    end_str = days[-1].strftime("%d/%m")

    msg = f"📊 <b>STATISTICHE DEGLI ULTIMI 7 GIORNI</b> 📊\n"
    msg += f"<i>(Da {DAY_NAMES_IT[days[0].weekday()]} {start_str} a {DAY_NAMES_IT[days[-1].weekday()]} {end_str})</i>\n\n"
    msg += f"📈 <b>Giocate giornaliere:</b>\n"
    msg += f"<code>{chart_str}</code>\n\n"
    msg += f"ℹ️ <b>Riepilogo settimana:</b>\n"
    msg += f"• Totale giocate: <code>{total_plays}</code>\n"
    msg += f"• Totale giocatori: <code>{total_users_count}</code>\n"
    msg += f"• Partite perse: <code>{total_lost}</code> (<code>{lost_pct}%</code>)\n"
    msg += f"• Gioco più giocato: {top_game_str}\n"
    msg += f"• Giocatore più attivo: {top_user_str}\n"

    await update.message.reply_text(msg, parse_mode="HTML", disable_web_page_preview=True)


async def send_long_message(bot_token: str, chat_id: int | str, message: str, reply_to_message_id: int | None = None) -> dict:
    url = f"https://api.telegram.org/bot{bot_token}/sendRichMessage"

    formatted_message = message.replace("\n", "<br>")

    payload = {
        "chat_id": chat_id,
        "rich_message": {
            "html": formatted_message
        },
    }

    if reply_to_message_id is not None:
        payload["reply_parameters"] = {"message_id": reply_to_message_id}

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, timeout=30.0)
        response_data = response.json()

    if not response_data.get("ok"):
        raise RuntimeError(f"Telegram API Error: {response_data}")

    return response_data


async def classificona(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    messaggio = ""
    print(f"ci sono in totale {len(GAMES.keys())} giochi")
    for game in GAMES.keys():
        if GAMES[game].get("disabled", False):
            continue
        classifica = make_single_classifica(game, chat_id=update.effective_chat.id, limit=3, show_lost=True)

        if classifica:
            messaggio += classifica + "\n"

    if messaggio:
        reply_to_id = update.effective_message.message_id if update.effective_message else None
        await send_long_message(
            bot_token=TOKEN,
            chat_id=update.effective_chat.id,
            message=messaggio.strip(),
            reply_to_message_id=reply_to_id,
        )
    return


async def link_single_game(update: Update, context: ContextTypes.DEFAULT_TYPE, correct_game) -> None:
    game = correct_game
    GAME = GAMES.get(game, None)

    if not GAME:
        return

    day = get_day_from_date(GAME["date"], GAME["day"], game, datetime.date.today())
    message = f'<a href="{GAME["url"]}">{GAME["emoji"]} {game} #{day}</a>'
    mymsg = await update.message.reply_html(message)
    schedule_delete(context, [mymsg, update.message], after_seconds=5, name_prefix="link_delete", msg_id=update.effective_message.message_id)
    return


async def parse_punteggio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    # context.giochino will be a list of a single class that can handle the game, built by the GameFilter
    giochino = context.giochino[0]
    giochino = giochino(update)
    result = giochino.punteggio
    sync_user(
        result.get("user_id"),
        result.get("user_name"),
        update.effective_user.username if update.effective_user else None,
    )

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

    # Hook for auto-reenabling games
    await check_reenable(giochino._name, update, context)

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
        if result.get("day") is None:
            logging.warning(f"Parsed result with null day for game {giochino._name}: {update.message.text}")
            return
        if result.get("tries") is None:
            logging.warning(f"Parsed result with null tries for game {giochino._name}: {update.message.text}")
            await update.message.reply_text(
                f"⚠️ Non riesco a leggere il punteggio per {giochino._name}. Assicurati che il messaggio includa il punteggio o il tempo!"
            )
            return

        query = Punteggio.select().where(
            Punteggio.day == str_as_int(result["day"]),
            Punteggio.game == result["name"],
            Punteggio.user_id == result["user_id"],
            Punteggio.chat_id == update.effective_chat.id,
        )

        if query:
            await update.message.reply_text(f"C'è già un risultato a nome tuo per {giochino._name} #{result['day']}.")
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
            extra=result.get("stars", None),
            streak=streak + 1,
            lost=play_is_lost,
        )

        # Check if this is a disabled game and notify the user
        if GAMES[result["name"]].get("disabled", False):
            await update.message.reply_text("⚠️ Questo gioco è disabilitato. Il punteggio è stato salvato ma non contribuirà alla classifica.")

        if play_is_lost:
            logging.info(f"Aggiungo tentativo di {result['user_name']} per {result['name']} #{result['day']} (fallito)")
            message = f'Classifica di {result["name"]} aggiornata.\n'
            classifica = make_single_classifica(result["name"], update.effective_chat.id, day=result["day"], show_lost=True)
            mymsg = await update.message.reply_html(classifica)
            schedule_delete(context, [mymsg], after_seconds=60, name_prefix="minimize", msg_id=update.effective_message.id)
            return

        today_game = int(get_day_from_date(GAMES[result["name"]]["date"], GAMES[result["name"]]["day"], result["name"], datetime.date.today()))

        favorites = []
        settings = context.bot_data.get("settings", {})
        user_id_str = str(result["user_id"])
        if user_id_str in settings:
            favorites = settings[user_id_str].get("favs", [])

        active_favorites = [g for g in favorites if g in GAMES and not GAMES[g].get("disabled", False)]
        tot_favs = len(active_favorites)
        played_today, not_played_today = get_user_played_games_today(result["user_id"])
        tot_games = len(played_today) + len(not_played_today)
        game_played_today = len(played_today)
        favs_played_today = len([g for g in played_today if g in active_favorites])

        if str_as_int(result["day"]) in [today_game, today_game - 1]:
            message = f'Classifica di {result["name"]} aggiornata.\n'
            classifica = make_single_classifica(result["name"], update.effective_chat.id, day=result["day"], show_lost=True)

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

                classifica += f"\n\nProgresso giornaliero:"
                if tot_favs > 0:
                    classifica += f'\n⭐ {print_progressbar(favs_played_today, complete=tot_favs, prefix="", suffix="")} {favs_played_today}/{tot_favs}'
                    classifica += f'\n🎮 {print_progressbar(game_played_today, complete=tot_games, prefix="", suffix="")} {game_played_today}/{tot_games}'
                else:
                    classifica += f'\n{print_progressbar(game_played_today, complete=tot_games, prefix="", suffix="")} {game_played_today}/{tot_games}'

                mymsg = await update.message.reply_html(classifica)

                await mymsg.reply_to_message.set_reaction(reaction="✍")
                if giochino.win_message:
                    await mymsg.reply_to_message.reply_html(giochino.win_message)

                completed_key = f"favs_completed_{datetime.date.today()}_{result['user_id']}"
                if tot_favs > 0 and favs_played_today == tot_favs and result["name"] in active_favorites:
                    if not context.bot_data.get(completed_key, False):
                        context.bot_data[completed_key] = True
                        await update.message.reply_html(f"🎉 Complimenti {result['user_name']}! Hai completato tutti i tuoi {tot_favs} giochi preferiti di oggi! 🥳")

                schedule_delete(context, [mymsg], after_seconds=60, name_prefix="minimize", msg_id=update.effective_message.id)

            else:
                mymsg = await update.message.reply_html("Ah, non l'ha ancora fatto nessuno, fico.")
                schedule_delete(context, [mymsg], after_seconds=60, name_prefix="delete_post", msg_id=update.effective_message.id)

        else:
            days_ago = int(today_game) - str_as_int(result["day"])
            if days_ago < 0:
                await update.message.reply_text('Ho salvato il tuo punteggio del futuro.')
            else:
                await update.message.reply_text(f'Ho salvato il tuo punteggio di {days_ago} giorni fa.')

        logging.info(f"Aggiungo punteggio di {result['user_name']} per {result['name']} #{result['day']} ({result['tries']})")

        if game_played_today == tot_games:
            # if the user has played all the games today, send a message
            await update.message.reply_text("Hai giocato a tutti i giochi oggi! Bravo! Esci un po' porca troia!")
            await update.message.set_reaction(reaction="🎉")


    else:  # should never be the case
        print('wtf?')

async def debug_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID or not update.message.reply_to_message:
        return
    import pprint
    rawtext = pprint.pformat(update.message.reply_to_message.text, width=300).replace("<", "less").replace(">", "more")
    await update.message.reply_html(f'<code>{rawtext}</code>')

async def manual_daily_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id == ADMIN_ID:
        await daily_reminder(context, pin=False)


async def manual_new_games_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id == ADMIN_ID:
        sent = await new_games_reminder(context)
        if not sent and update.message:
            await update.message.reply_text("Nessun gioco nuovo attivo oggi.")


async def manual_backup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id == ADMIN_ID:
        return await make_backup(context)


async def manual_riassunto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id == ADMIN_ID:
        context.bot_data["manual_riassunto"] = True
        return await riassunto_serale(context)


def get_user_played_games_today(
    user_id: int | str, target_date: datetime.date | None = None
) -> tuple[list[str], list[str]]:
    """Return (played_today, not_played_today) active games for a user using a single batched query."""
    if target_date is None:
        target_date = datetime.date.today()

    active_games = [g for g in GAMES.keys() if not GAMES[g].get("disabled", False)]
    expected_days = {
        g: int(get_day_from_date(GAMES[g]["date"], GAMES[g]["day"], g, target_date))
        for g in active_games
    }

    played_set: set[str] = set()
    if expected_days:
        rows = Punteggio.select(Punteggio.game, Punteggio.day).where(
            Punteggio.user_id == int(user_id),
            Punteggio.game.in_(active_games),
            Punteggio.day.in_(list(set(expected_days.values()))),
        )
        played_set = {row.game for row in rows if expected_days.get(row.game) == row.day}

    played_today = [g for g in active_games if g in played_set]
    not_played_today = [g for g in active_games if g not in played_set]
    return played_today, not_played_today


def build_myday_message(
    user_id: int | str, settings: dict, show_all: bool = False
) -> tuple[str, InlineKeyboardMarkup | None, int, int]:
    """Build the /myday HTML message, optional inline keyboard, and favorite counts."""
    user_settings = settings.get(str(user_id), {})
    favorites = user_settings.get("favs", [])
    solo_preferiti = False if show_all else user_settings.get("favs_extra_button", False)

    played_today, not_played_today = get_user_played_games_today(user_id)
    not_played_favs = [g for g in not_played_today if g in favorites]
    not_played_regs = [g for g in not_played_today if g not in favorites]
    get_game_badge = build_game_badge_getter()

    if not played_today:
        message = "Non hai giocato a nulla oggi.\n\n"
    elif not not_played_today:
        message = "Hai giocato a tutto!"
    elif not_played_favs:
        message = "Ti manca da giocare:\n\n"
    elif favorites:
        message = "Hai giocato a tutti i preferiti!\n\n"
    else:
        message = "Ti manca da giocare:\n\n"

    for game in not_played_favs:
        message += f'<a href="{GAMES[game]["url"]}">⭐ {GAMES[game]["emoji"]} {game}</a>{get_game_badge(game)}\n'

    message += "\n"

    if not_played_regs and not solo_preferiti:
        for game in not_played_regs:
            message += f'<a href="{GAMES[game]["url"]}">{GAMES[game]["emoji"]} {game}</a>{get_game_badge(game)}\n'

    active_favorites = [g for g in favorites if g in GAMES and not GAMES[g].get("disabled", False)]
    tot_favs = len(active_favorites)
    favs_played_today = len([g for g in played_today if g in active_favorites]) if tot_favs > 0 else 0
    if tot_favs > 0 and favs_played_today < tot_favs:
        message = message.strip()
        message += "\n\nProgresso preferiti:"
        message += f'\n⭐ {print_progressbar(favs_played_today, complete=tot_favs, prefix="", suffix="")} {favs_played_today}/{tot_favs}'

    keyboard = None
    if solo_preferiti:
        buttons = [[InlineKeyboardButton("Tutti i giochi", callback_data=f"myonly_more_{user_id}")]]
        keyboard = InlineKeyboardMarkup(buttons)

    return message, keyboard, tot_favs, favs_played_today


def extract_ephemeral_id(message) -> int | None:
    if not message:
        return None
    if hasattr(message, "api_kwargs") and isinstance(message.api_kwargs, dict):
        if "ephemeral_message_id" in message.api_kwargs:
            return message.api_kwargs["ephemeral_message_id"]
    if hasattr(message, "ephemeral_message_id") and message.ephemeral_message_id is not None:
        return message.ephemeral_message_id
    return getattr(message, "message_id", None)


async def myonly(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return

    user_id = update.effective_user.id
    settings = context.bot_data.get("settings", {})
    message, keyboard, tot_favs, favs_played_today = build_myday_message(user_id, settings, show_all=False)
    solo_preferiti = keyboard is not None

    ephemeral_params = {"receiver_user_id": user_id}
    reply_params = None
    if update.message:
        eph_id = getattr(update.message, "ephemeral_message_id", None)
        if eph_id:
            reply_params = ReplyParameters(message_id=update.message.message_id, api_kwargs={"ephemeral_message_id": eph_id})
        else:
            reply_params = ReplyParameters(message_id=update.message.message_id)

    mymsg = await update.message.reply_text(
        message,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=keyboard,
        reply_parameters=reply_params,
        api_kwargs={"ephemeral_message_parameters": ephemeral_params},
    )

    msg_eph_id = extract_ephemeral_id(mymsg)
    chat_user_key = f"myonly_eph_{update.effective_chat.id}_{user_id}"
    context.bot_data[chat_user_key] = {
        "ephemeral_message_id": msg_eph_id,
        "message": mymsg,
    }

    if solo_preferiti and msg_eph_id:
        try:
            updated_kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("Tutti i giochi", callback_data=f"myonly_more_{user_id}_{msg_eph_id}")]
            ])
            await context.bot._post(
                "editEphemeralMessageReplyMarkup",
                data={
                    "chat_id": update.effective_chat.id,
                    "receiver_user_id": user_id,
                    "ephemeral_message_id": msg_eph_id,
                    "reply_markup": updated_kb.to_dict(),
                }
            )
        except Exception as e:
            logger.debug(f"editEphemeralMessageReplyMarkup failed: {e}")

    if tot_favs > 0 and favs_played_today == tot_favs:
        try:
            await update.message.reply_text(
                "🥳",
                reply_parameters=reply_params,
                api_kwargs={"ephemeral_message_parameters": ephemeral_params},
            )
        except Exception:
            pass


async def myonly_full(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.callback_query or not update.effective_user:
        return

    user_id = str(update.effective_user.id)
    parts = update.callback_query.data.split("_")
    target_uid = parts[2] if len(parts) > 2 else ""
    if user_id != target_uid:
        try:
            await update.callback_query.answer("Non puoi toccare i pulsanti degli altri!", show_alert=True)
        except Exception:
            pass
        return

    cb_eph_id = None
    if len(parts) > 3 and parts[3].isdigit():
        cb_eph_id = int(parts[3])

    settings = context.bot_data.get("settings", {})
    message, _, tot_favs, favs_played_today = build_myday_message(user_id, settings, show_all=True)

    chat_id = update.effective_chat.id
    receiver_user_id = update.effective_user.id
    cq_id = update.callback_query.id
    chat_user_key = f"myonly_eph_{chat_id}_{receiver_user_id}"

    saved_data = context.bot_data.get(chat_user_key, {})
    saved_eph_id = saved_data.get("ephemeral_message_id") if isinstance(saved_data, dict) else None
    saved_msg = saved_data.get("message") if isinstance(saved_data, dict) else None

    eph_id = (
        cb_eph_id
        or saved_eph_id
        or extract_ephemeral_id(update.callback_query.message)
        or extract_ephemeral_id(update.effective_message)
    )

    edited = False

    # Attempt 1: Try editEphemeralMessageText with eph_id
    if eph_id and eph_id != 0:
        try:
            await context.bot._post(
                "editEphemeralMessageText",
                data={
                    "chat_id": chat_id,
                    "receiver_user_id": receiver_user_id,
                    "ephemeral_message_id": eph_id,
                    "text": message,
                    "parse_mode": "HTML",
                }
            )
            edited = True
        except Exception as e:
            logger.warning(f"editEphemeralMessageText with eph_id {eph_id} failed: {e}")

    # Attempt 2: If edit failed, send new ephemeral message targeted by callback_query_id
    # Note: replace_callback_query_message MUST be omitted/False for callback queries from ephemeral messages
    if not edited and cq_id:
        try:
            new_msg = await context.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode="HTML",
                disable_web_page_preview=True,
                api_kwargs={
                    "ephemeral_message_parameters": {
                        "receiver_user_id": receiver_user_id,
                        "callback_query_id": cq_id,
                    }
                }
            )
            edited = True
            new_eph_id = extract_ephemeral_id(new_msg)
            context.bot_data[chat_user_key] = {
                "ephemeral_message_id": new_eph_id,
                "message": new_msg,
            }
            if eph_id and eph_id != 0:
                try:
                    await context.bot._post(
                        "deleteEphemeralMessage",
                        data={
                            "chat_id": chat_id,
                            "receiver_user_id": receiver_user_id,
                            "ephemeral_message_id": eph_id,
                        }
                    )
                except Exception:
                    pass
            if saved_msg and hasattr(saved_msg, "delete"):
                try:
                    await saved_msg.delete()
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"send_message ephemeral with callback_query_id failed: {e}")

    # Attempt 3: regular edit_text if non-ephemeral
    if not edited and update.effective_message and getattr(update.effective_message, "message_id", 0) != 0:
        try:
            await update.effective_message.edit_text(message, parse_mode="HTML", disable_web_page_preview=True)
            edited = True
        except Exception as e:
            logger.warning(f"effective_message.edit_text failed: {e}")

    # Attempt 4: Fallback send fresh ephemeral message (without callback_query_id)
    if not edited:
        try:
            fresh_msg = await context.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode="HTML",
                disable_web_page_preview=True,
                api_kwargs={
                    "ephemeral_message_parameters": {
                        "receiver_user_id": receiver_user_id,
                    }
                }
            )
            edited = True
        except Exception as e:
            logger.warning(f"fallback fresh send_message failed: {e}")

    # Always answer the callback query at the end
    try:
        await update.callback_query.answer()
    except Exception:
        pass

    if tot_favs > 0 and favs_played_today == tot_favs:
        try:
            ephemeral_params = {"receiver_user_id": receiver_user_id}
            await context.bot.send_message(
                chat_id=chat_id,
                text="🥳",
                api_kwargs={"ephemeral_message_parameters": ephemeral_params}
            )
        except Exception:
            pass


async def mytoday(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Trigger the ephemeral /myday message."""
    return await myonly(update, context)


async def mytoday_full(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Trigger the ephemeral /myday 'Tutti i giochi' callback handler."""
    return await myonly_full(update, context)


async def list_games(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    today = datetime.date.today()
    new_games_map = {bg.game: bg.multiplier for bg in get_new_games_for_date(today)}
    new_emoji = getattr(config, "NEW_GAME_EMOJI", "🆕")
    message = "Lista dei giochi:\n"

    for game in GAMES.keys():
        prefix = ""
        suffix = ""
        if GAMES[game].get("disabled", False):
            prefix = "🚫 "
        elif game in new_games_map:
            prefix = f"{new_emoji} "
            suffix = f" [{new_games_map[game]}x]"
        message += f'{prefix}{GAMES[game]["emoji"]} {game}{suffix}: {GAMES[game]["url"]}\n'

    reply_to_id = update.effective_message.message_id if update.effective_message else None
    resp = await send_long_message(
        bot_token=TOKEN,
        chat_id=update.effective_chat.id,
        message=message.strip(),
        reply_to_message_id=reply_to_id,
    )
    reply_msg_id = resp.get("result", {}).get("message_id") if isinstance(resp, dict) else None
    to_delete = [update.effective_message]
    if reply_msg_id:
        to_delete.append((update.effective_chat.id, reply_msg_id))
    schedule_delete(context, to_delete, after_seconds=60, name_prefix="list_delete", msg_id=reply_to_id)


async def show_disabled_games(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Admin-only command
    if update.effective_user.id != ADMIN_ID:
        return
    
    message = ""
    
    # Query auto-disabled games from DB
    auto_disabled_names = [st.game_name for st in GameStatus.select().where(GameStatus.is_disabled == True)]
    
    auto_disabled = []
    perma_disabled = []
    
    for game in GAMES.keys():
        if GAMES[game].get("disabled", False):
            if game in auto_disabled_names:
                auto_disabled.append(game)
            else:
                perma_disabled.append(game)
    
    if auto_disabled:
        message += "📉 **Disabilitati Automaticamente** (Inattività):\n"
        for game in auto_disabled:
            message += f'{GAMES[game]["emoji"]} {game} ({GAMES[game]["url"]})\n'
        message += "\n"
        
    if perma_disabled:
        message += "⛔ **Disabilitati Manualmente** (Permanent):\n"
        for game in perma_disabled:
            message += f'{GAMES[game]["emoji"]} {game} ({GAMES[game]["url"]})\n'
            
    if not message:
        message = "Non ci sono giochi disabilitati."
    else:
        message = "Giochi disabilitati:\n\n" + message
    
    await update.message.reply_text(message, parse_mode="HTML", disable_web_page_preview=True)
    # Delete the original command after 10 seconds
    await delete_original_command(update, context, 10)


async def cmd_setanchor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Admin-only command
    if update.effective_user.id != ADMIN_ID:
        return

    args = context.args

    # If no arguments or help requested, show detailed help message
    if not args or args[0].lower() in ["-h", "--help", "help"]:
        help_text = (
            "⚓️ <b>Gestione Ancoraggio Giochi</b> (<code>/setanchor</code> / <code>/setdate</code>)\n\n"
            "Uso del comando:\n"
            "• <code>/setanchor &lt;gioco&gt; &lt;giorno&gt; [data]</code>\n"
            "• <code>/setanchor list</code> — Mostra tutti gli ancoraggi personalizzati\n"
            "• <code>/setanchor reset &lt;gioco&gt;</code> — Rimuove l'ancoraggio personalizzato\n\n"
            "<b>Esempi:</b>\n"
            "• <code>/setanchor Geozee 18</code>\n"
            "  <i>Imposta il giorno #18 per Geozee alla data di OGGI.</i>\n"
            "• <code>/setanchor Timdle 128 2026-07-22</code>\n"
            "  <i>Imposta il giorno #128 per Timdle alla data specificata (YYYY-MM-DD oppure DD/MM/YYYY).</i>"
        )
        await update.message.reply_html(help_text)
        return

    subcmd = args[0].lower()

    if subcmd == "list":
        anchors = list(GameAnchor.select())
        if not anchors:
            await update.message.reply_text("Nessun ancoraggio personalizzato attivo nel database.")
            return

        msg = "⚓️ <b>Ancoraggi Personalizzati Attivi:</b>\n\n"
        for a in anchors:
            msg += f"• <b>{a.game_name}</b>: Giorno #{a.anchor_day} = Data {a.anchor_date}\n"
        await update.message.reply_html(msg)
        return

    if subcmd == "reset":
        if len(args) < 2:
            await update.message.reply_text("Uso: /setanchor reset <gioco>")
            return

        raw_game = " ".join(args[1:])
        target_game = correct_name(raw_game)
        if not target_game:
            await update.message.reply_text(f"Gioco '{raw_game}' non trovato.")
            return

        deleted = GameAnchor.delete().where(GameAnchor.game_name == target_game).execute()
        if deleted:
            invalidate_anchor_cache()
            await update.message.reply_html(f"✅ Ancoraggio personalizzato rimosso per <b>{target_game}</b>. Torna ai default.")
        else:
            await update.message.reply_html(f"Nessun ancoraggio personalizzato trovato per <b>{target_game}</b>.")
        return

    target_date = datetime.date.today()
    parsed_custom_date = None
    potential_date_str = args[-1]

    for date_fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            parsed_custom_date = datetime.datetime.strptime(potential_date_str, date_fmt).date()
            break
        except ValueError:
            pass

    if parsed_custom_date:
        target_date = parsed_custom_date
        remaining = args[:-1]
    else:
        remaining = args

    if not remaining:
        await update.message.reply_text("Specificare un giorno valido. Uso: /setanchor <gioco> <giorno> [data]")
        return

    day_str = remaining[-1]
    if not day_str.isdigit():
        await update.message.reply_text(f"Numero di giorno non valido: '{day_str}'. Uso: /setanchor <gioco> <giorno> [data]")
        return

    parsed_day = day_str
    raw_game = " ".join(remaining[:-1])

    if not raw_game:
        await update.message.reply_text("Specificare il nome del gioco. Uso: /setanchor <gioco> <giorno> [data]")
        return

    target_game = correct_name(raw_game)
    if not target_game:
        await update.message.reply_text(f"Gioco '{raw_game}' non trovato.")
        return

    GameAnchor.replace(
        game_name=target_game,
        anchor_date=target_date,
        anchor_day=str(parsed_day),
        updated_at=datetime.datetime.now()
    ).execute()
    invalidate_anchor_cache()

    await update.message.reply_html(
        f"✅ Ancoraggio aggiornato per <b>{target_game}</b>:\n"
        f"Giorno <b>#{parsed_day}</b> impostato alla data <b>{target_date.strftime('%Y-%m-%d')}</b>."
    )


async def cmd_stelle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Admin-only command
    if update.effective_user.id != ADMIN_ID:
        return

    args = context.args
    reply_msg = update.message.reply_to_message

    # Reset / Clear subcommands
    if args and args[0].lower() in ["reset", "clear"]:
        today = datetime.date.today()
        PuntiBonus.create_table(safe=True)
        if len(args) > 1:
            target = args[1].lstrip("@")
            deleted = PuntiBonus.delete().where(
                PuntiBonus.date == today,
                (PuntiBonus.user_name.contains(target) | (PuntiBonus.user_id.cast('TEXT') == target))
            ).execute()
            await update.message.reply_text(f"Azzerati {deleted} record di bonus per '{target}' di oggi.")
        else:
            deleted = PuntiBonus.delete().where(PuntiBonus.date == today).execute()
            await update.message.reply_text(f"Azzerati tutti i bonus/malus di oggi ({deleted} record rimossi).")
        return

    target_user_id = None
    target_user_name = None
    delta = None
    reason = None

    if reply_msg and reply_msg.from_user:
        # Modo Reply: /stelle +2 [motivo] o /stelle -1 [motivo]
        if not args:
            await update.message.reply_text(
                "ℹ️ <b>Uso via reply:</b> <code>/stelle &lt;+punti/-punti&gt; [motivo]</code>\n"
                "<i>Es:</i> <code>/stelle +2 Premio quiz</code>",
                parse_mode="HTML"
            )
            return

        try:
            delta = int(args[0])
        except ValueError:
            await update.message.reply_text("❌ Il valore dei punti deve essere un numero intero (es. +2 o -1).")
            return

        target_user_id = reply_msg.from_user.id
        target_user_name = reply_msg.from_user.full_name or reply_msg.from_user.first_name
        if len(args) > 1:
            reason = " ".join(args[1:])

    else:
        # Modo Argomenti: /stelle @utente +2 [motivo] o /stelle <user_id> +2 [motivo]
        if not args or len(args) < 2:
            await update.message.reply_text(
                "ℹ️ <b>Uso del comando:</b>\n"
                "• In risposta a un messaggio: <code>/stelle &lt;+punti/-punti&gt; [motivo]</code>\n"
                "• Diretto: <code>/stelle &lt;@username o user_id&gt; &lt;+punti/-punti&gt; [motivo]</code>\n"
                "• Reset: <code>/stelle reset [@username]</code>\n"
                "<i>Es:</i> <code>/stelle @Mario +2 Premio quiz</code>",
                parse_mode="HTML"
            )
            return

        user_param = args[0]
        try:
            delta = int(args[1])
        except ValueError:
            await update.message.reply_text("❌ Il valore dei punti deve essere un numero intero (es. +2 o -1).")
            return

        if len(args) > 2:
            reason = " ".join(args[2:])

        # Ricerca utente
        if user_param.isdigit():
            target_user_id = int(user_param)
            u_found = Utente.get_or_none(Utente.user_id == target_user_id) if Utente.table_exists() else None
            if u_found:
                target_user_name = u_found.user_name
            else:
                p_found = Punteggio.select(Punteggio.user_name).where(Punteggio.user_id == target_user_id).order_by(Punteggio.timestamp.desc()).first()
                target_user_name = p_found.user_name if p_found else f"User {target_user_id}"
        else:
            uname = user_param.lstrip("@")
            u_found = (
                Utente.select()
                .where(Utente.user_name.contains(uname) | (Utente.username == uname))
                .first()
                if Utente.table_exists()
                else None
            )
            if u_found:
                target_user_id = u_found.user_id
                target_user_name = u_found.user_name
            else:
                p_found = Punteggio.select(Punteggio.user_id, Punteggio.user_name).where(Punteggio.user_name.contains(uname)).order_by(Punteggio.timestamp.desc()).first()
                if not p_found:
                    p_found = Punti.select(Punti.user_id, Punti.user_name).where(Punti.user_name.contains(uname)).order_by(Punti.date.desc()).first()

                if p_found:
                    target_user_id = p_found.user_id
                    target_user_name = p_found.user_name
                else:
                    await update.message.reply_text(f"❌ Utente '{user_param}' non trovato nel database. Prova a rispondere (reply) direttamente a un suo messaggio.")
                    return

    today = datetime.date.today()
    PuntiBonus.create_table(safe=True)
    PuntiBonus.create(
        date=today,
        user_id=target_user_id,
        user_name=target_user_name,
        punti=delta,
        reason=reason,
        assigned_by=update.effective_user.id,
        timestamp=int(time.time()),
    )

    sign = "+" if delta > 0 else ""
    reason_str = f" per <i>{html.escape(reason)}</i>" if reason else ""
    await update.message.reply_text(
        f"⭐ Punti aggiornati per <b>{html.escape(target_user_name)}</b>: <b>{sign}{delta}</b>{reason_str}.",
        parse_mode="HTML"
    )


async def cmd_bonus_oggi(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    today = datetime.date.today()
    PuntiBonus.create_table(safe=True)
    bonuses = (
        PuntiBonus.select()
        .where(PuntiBonus.date == today)
        .order_by(PuntiBonus.timestamp.asc())
    )
    if not bonuses:
        await update.message.reply_text("Nessun punto bonus/malus registrato oggi.")
        return

    msg = f"⭐ <b>Bonus e Malus di oggi ({today.strftime('%Y-%m-%d')}):</b>\n\n"
    for b in bonuses:
        sign = "+" if b.punti > 0 else ""
        reason_str = f" — <i>{html.escape(b.reason)}</i>" if b.reason else ""
        msg += f"• <b>{html.escape(b.user_name)}</b>: <code>{sign}{b.punti}</code>{reason_str}\n"

    await update.message.reply_text(msg, parse_mode="HTML")


async def cmd_ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Admin-only command
    if update.effective_user.id != ADMIN_ID:
        return

    prompt = " ".join(context.args).strip() if context.args else ""
    if not prompt:
        help_text = (
            "🤖 <b>Assistente Statistiche Giochini (<code>/ask</code>)</b>\n\n"
            "Fai una domanda in linguaggio naturale sulle statistiche e i punteggi del database!\n\n"
            "<b>Esempi:</b>\n"
            "• <code>/ask chi ha vinto più volte a Geozee?</code>\n"
            "• <code>/ask percentuale di vittorie a Wordle per giocatore (minimo 10 partite)</code>\n"
            "• <code>/ask quali sono i 5 giochi con più partite registrate?</code>\n"
            "• <code>/ask chi ha la serie (streak) più lunga attiva?</code>"
        )
        await update.message.reply_html(help_text)
        return

    status_msg = await update.message.reply_html("🧠 <i>Analizzo la richiesta ed elaboro i dati...</i>")

    try:
        from ask_ai import process_ask_query
        db_path = Punteggio._meta.database.database
        explanation, sql_query = await process_ask_query(db_path, prompt)
        logger.info(f"Query SQL eseguita per /ask ('{prompt}'): {sql_query}")
        await status_msg.edit_text(explanation, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Errore comando /ask: {e}", exc_info=True)
        await status_msg.edit_text(
            f"❌ <b>Si è verificato un errore durante l'elaborazione:</b>\n<code>{e}</code>",
            parse_mode="HTML"
        )


async def check_unused_games(context: ContextTypes.DEFAULT_TYPE) -> None:
    today = datetime.date.today()
    cutoff_days = 20
    unused_games = []
    print("Controllo giochi inutilizzati...")

    for game in GAMES.keys():
        if GAMES[game].get("disabled", False):
            continue
        
        # Get the latest play for this game
        last_play = Punteggio.select().where(
            Punteggio.game == game
        ).order_by(Punteggio.date.desc()).first()
        
        days_since = None
        if last_play:
            # Ensure last_play.date is a date object
            last_date = last_play.date
            if isinstance(last_date, datetime.datetime):
                last_date = last_date.date()
                
            days_since = (today - last_date).days
            
            if days_since > cutoff_days:
                unused_games.append((game, days_since))
        else:
            # Never played
            unused_games.append((game, -1))

    if unused_games:
        # Sort by days since (descending), putting "Never" (-1) at the top or bottom?
        # Let's put "Never" first (treated as infinity), then descending days
        unused_games.sort(key=lambda x: x[1] if x[1] != -1 else 99999, reverse=True)
        
        message = f"⚠️ <b>Giochi senza partite negli ultimi {cutoff_days} giorni:</b>\n\n"
        for game, days in unused_games:
            days_str = f"{days} giorni fa" if days != -1 else "Mai giocato"
            message += f"<a href='{GAMES[game]['url']}'>{GAMES[game]['emoji']} {game}</a> ({days_str})\n"

        await context.bot.send_message(chat_id=ID_GIOCHINI, text=message, parse_mode="HTML")
    else:
        await context.bot.send_message(chat_id=ID_GIOCHINI, text="Tutti i giochi sono stati giocati di recente.", parse_mode="HTML")


async def manual_check_unused(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id == ADMIN_ID:
        await check_unused_games(context)
        await update.message.reply_text("Controllo eseguito. Se ci sono giochi inutilizzati, ho inviato un messaggio su BotCentral.")


async def manual_auto_disable(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id == ADMIN_ID:
        await auto_disable_games(context)
        await update.message.reply_text("Controllo disabilitazione automatica eseguito.")


async def auto_disable_games(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Daily check to automatically disable unused games."""
    logging.info("Running auto_disable_games...")
    today = datetime.datetime.now()
    cutoff_days = 30
    cutoff_date = today - datetime.timedelta(days=cutoff_days)
    
    disabled_count = 0
    newly_disabled = []

    for game_name, game_data in GAMES.items():
        # strict check: if it is already disabled, skip
        if game_data.get("disabled", False):
            continue

        # Check last play
        last_play = Punteggio.select().where(Punteggio.game == game_name).order_by(Punteggio.date.desc()).first()
        
        should_disable = False
        if not last_play:
            # Never played. Check if game is old enough? 
            # If game date is older than cutoff, disable.
            game_date = game_data.get("date") # This is a date object
            if isinstance(game_date, datetime.date):
                 # Convert to datetime for comparison or just compare dates
                 if game_date < cutoff_date.date():
                     should_disable = True
        else:
            if last_play.date < cutoff_date.date():
                should_disable = True
        
        if should_disable:
            # Disable it!
            logging.info(f"Auto-disabling {game_name} (Last play: {last_play.date if last_play else 'Never'})")
            
            # Update DB
            status, created = GameStatus.get_or_create(game_name=game_name)
            status.is_disabled = True
            status.last_disabled_date = today
            status.save()

            # Update Memory
            GAMES[game_name]["disabled"] = True
            
            newly_disabled.append(f"{game_data['emoji']} {game_name}")
            disabled_count += 1
            
    if newly_disabled:
        message = f"📉 **Pulizia Giochi** 📉\n\nI seguenti giochi sono stati disabilitati automaticamente per inattività (> {cutoff_days} gg):\n"
        message += "\n".join(newly_disabled)
        message += "\n\nSe qualcuno ci giocherà di nuovo, verranno riattivati automaticamente! 🪄"
        
        await context.bot.send_message(chat_id=ID_GIOCHINI, text=message)


async def check_reenable(game_name: str, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Checks if a game is auto-disabled and re-enables it if played."""
    try:
        status = GameStatus.get_or_none(GameStatus.game_name == game_name)
        if status and status.is_disabled:
            # It's disabled! Re-enable it.
            status.is_disabled = False
            status.last_enabled_date = datetime.datetime.now()
            status.save()
            
            # Update memory
            if game_name in GAMES:
                GAMES[game_name]["disabled"] = False

            grant_reenabled_game_bonus(game_name, datetime.date.today())
            logging.info(f"Auto-reenabling {game_name}!")

            # Notify user
            emoji = GAMES[game_name].get("emoji", "")
            days_disabled = (datetime.datetime.now() - status.last_disabled_date).days if status.last_disabled_date else "?"
            bonus_mult = getattr(config, "REENABLED_GAME_MULTIPLIER", 3)
            await update.message.reply_text(
                f"✨ Hai risvegliato {emoji} {game_name}!\n"
                f"Era stato disabilitato {days_disabled} giorni fa per inattività.\n"
                f"Ora è di nuovo attivo per tutti e vale bonus {bonus_mult}x oggi e domani! Buon divertimento! 🎮"
            )
            await update.message.set_reaction(reaction="✨")

    except Exception as e:
        logging.error(f"Error in check_reenable: {e}")


def sync_disabled_games():
    """Syncs in-memory GAMES dict with GameStatus DB."""
    # This runs on startup.
    logging.info("Syncing disabled games from DB...")
    disabled_games = GameStatus.select().where(GameStatus.is_disabled == True)
    count = 0
    for status in disabled_games:
        if status.game_name in GAMES:
            GAMES[status.game_name]["disabled"] = True
            count += 1
    logging.info(f"Synced {count} disabled games.")


async def restart_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id == ADMIN_ID:
        await update.message.reply_text("Riavvio in corso...")
        os.execl(sys.executable, sys.executable, *sys.argv)


async def refresh_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id == ADMIN_ID:
        import subprocess
        try:
            def _run_git(cmd: list[str]) -> str:
                return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.strip()

            # Get current HEAD hash before pulling
            old_head = await asyncio.to_thread(_run_git, ["git", "rev-parse", "HEAD"])

            # Execute git pull
            await asyncio.to_thread(_run_git, ["git", "pull"])

            # Get HEAD hash after pulling
            new_head = await asyncio.to_thread(_run_git, ["git", "rev-parse", "HEAD"])

            if old_head == new_head:
                pull_output = "Già aggiornato."
            else:
                # Get list of commit subject lines between the old and new HEAD
                log_stdout = await asyncio.to_thread(
                    _run_git, ["git", "log", f"{old_head}..{new_head}", "--format=%s"]
                )
                commits = log_stdout.split("\n")
                pull_output = "\n".join(f"- {commit}" for commit in commits if commit)

            await update.message.reply_text(f"Git pull completato:\n{pull_output}")
        except Exception as e:
            await update.message.reply_text(f"Errore durante git pull: {e}\nRiavvio comunque...")
        
        await update.message.reply_text("Riavvio in corso... 🔄")
        os.execl(sys.executable, sys.executable, *sys.argv)



async def mystats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = context.bot_data.get("settings", {})
    user_id_str = str(update.effective_user.id)
    favs = settings.get(user_id_str, {}).get("favs", [])
    favs_count = len(favs)

    if context.args:
        correct_game_names = [x for x in GAMES.keys()]
        game_names = [x.lower() for x in GAMES.keys()]
        game = context.args[0].lower()
        if game in game_names:
            correct_game = correct_game_names[game_names.index(game)]
            is_favorite = correct_game in favs
            try:
                message = personal_stats(
                    update.effective_user.id, 
                    correct_game=correct_game, 
                    favs_count=favs_count, 
                    is_favorite=is_favorite
                )
            except Exception as e:
                message = f"Ho qualche problema, scusa ({e})"
        else:
            try:
                message = personal_stats(update.effective_user.id, favs_count=favs_count)
            except Exception as e:
                message = f"Ho qualche problema, scusa ({e})"
    else:
        try:
            message = personal_stats(update.effective_user.id, favs_count=favs_count)
        except Exception as e:
            message = f"Ho qualche problema, scusa ({e})"

    mymsg = await update.message.reply_text(message, parse_mode="HTML", disable_web_page_preview=True)
    schedule_delete(context, [mymsg, update.message], after_seconds=60, name_prefix="mystats_delete", msg_id=update.message.message_id)


async def groupstats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.id not in [ID_GIOCHINI, ID_TESTING]:
        return

    message = group_stats(update.effective_chat.id)
    await update.message.reply_text(message, parse_mode="HTML", disable_web_page_preview=True)


async def myscore(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the user's score and game positions for the current day."""
    user_id = update.effective_user.id
    today = datetime.date.today()
    
    # Dictionary to store game results for the user
    user_games = []
    total_stars = 0

    bonuses_by_game = get_all_bonuses_for_date(today, auto_pick_jolly=True)

    active_games = [g for g in GAMES.keys() if not GAMES[g].get("disabled", False)]
    expected_days = {
        g: int(get_day_from_date(GAMES[g]["date"], GAMES[g]["day"], g, today))
        for g in active_games
    }

    scores_by_game: dict[str, list] = {}
    if expected_days:
        all_scores_query = (
            Punteggio.select(Punteggio.game, Punteggio.day, Punteggio.user_name, Punteggio.user_id, Punteggio.tries, Punteggio.extra, Punteggio.lost)
            .where(
                Punteggio.chat_id == update.effective_chat.id,
                Punteggio.game.in_(active_games),
                Punteggio.day.in_(list(set(expected_days.values()))),
            )
            .order_by(Punteggio.tries, Punteggio.extra.cast('INTEGER').desc(), Punteggio.timestamp)
        )
        for row in all_scores_query:
            if expected_days.get(row.game) == row.day:
                scores_by_game.setdefault(row.game, []).append(row)

    # Iterate through all active games
    for game in active_games:
        game_scores = scores_by_game.get(game, [])
        if not any(g.user_id == user_id for g in game_scores):
            continue

        day = expected_days[game]
        cl = Classifica()
        cl.game = game
        cl.day = str(day)
        cl.date = today
        cl.emoji = GAMES[game]["emoji"]
        cl.giocate = [
            Giocata(
                user_id=g.user_id,
                user_name=g.user_name,
                tries=g.tries,
                game=game,
                extra=g.extra if g.extra else 0
            )
            for g in game_scores
        ]
        mult, b_type = bonuses_by_game.get(game, (1, None))
        cl.order_and_position()
        cl.assign_stars("default", multiplier=mult)

        # Find the user's game in the classifica
        for giocata in cl.giocate:
            if giocata.user_id == user_id:
                # Only include non-lost games since lost games produce 0 points
                if not giocata.lost:
                    user_games.append({
                        "game": game,
                        "emoji": GAMES[game]["emoji"],
                        "position": giocata.posizione,
                        "stars": giocata.stelle,
                        "multiplier": mult,
                        "bonus_type": b_type,
                        "medal_emoji": giocata.emoji,
                        "tries": giocata.processed_tries,
                    })
                    total_stars += giocata.stelle
                break
    
    # Build the message
    if not user_games:
        message = "Non hai ancora giocato oggi. 🎮"
    else:
        message = f"<b>Il tuo punteggio di oggi:</b> {total_stars}{STAR_SYMBOL}\n\n"
        new_emoji = getattr(config, "NEW_GAME_EMOJI", "🆕")
        reenabled_emoji = getattr(config, "REENABLED_GAME_EMOJI", "✨")
        for game_info in user_games:
            b_type = game_info.get("bonus_type")
            if b_type == "new_game":
                b_icon = new_emoji
            elif b_type == "reenabled":
                b_icon = reenabled_emoji
            else:
                b_icon = "🎰"
            mult_str = f" (x{game_info['multiplier']} {b_icon})" if game_info.get("multiplier", 1) > 1 else ""
            stars_display = f"+{game_info['stars']}{STAR_SYMBOL}{mult_str}" if game_info['stars'] > 0 else ""
            message += f"{game_info['medal_emoji']}{stars_display} {game_info['game']}\n"
    
    reply_params = ReplyParameters(message_id=update.message.message_id)
    ephemeral_params = {"receiver_user_id": int(user_id)}
    await update.message.reply_text(
        message,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_parameters=reply_params,
        api_kwargs={"ephemeral_message_parameters": ephemeral_params},
    )


async def simula_daily(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    AVAILABLE_MODELS = {
        "default": "Default (solo vincenti, worst-rank)",
        "no_limit_with_lost_rank_based": "Default (solo vincenti, worst-rank)",
        "no_limit_with_lost": "No limit (include persi)",
        "alternate": "Alternate (max 3pt, solo vincenti)",
        "alternate-with-lost": "Alternate (max 3pt, include persi)",
        "standard": "Standard (3-2-1 fisso)",
        "no-single-point-games": "No single player (min. 2 giocate)",
        "no_single_point_games": "No single player (min. 2 giocate)",
        "only-popular-games": "Only popular games (min. 2 giocate)",
        "only_popular_games": "Only popular games (min. 2 giocate)",
        "participation-bonus": "Participation Bonus (1pt ai persi)",
        "participation_bonus": "Participation Bonus (1pt ai persi)",
        "participation": "Participation Bonus (1pt ai persi)",
    }

    selected_model = "no_limit_with_lost"
    if context.args:
        arg_model = context.args[0].lower()
        if arg_model in AVAILABLE_MODELS:
            selected_model = arg_model

    today = datetime.date.today()
    classifica_stelle = daily_ranking(selected_model, today)

    model_label = AVAILABLE_MODELS.get(selected_model, selected_model)

    if not classifica_stelle:
        await update.message.reply_text(f"Nessuna giocata registrata oggi per la simulazione con modello <b>{model_label}</b>.", parse_mode="HTML")
        return

    msg = f"🧪 <b>Simulazione Classifica di Oggi</b>\n"
    msg += f"⚙️ Modello: <code>{selected_model}</code> ({model_label})\n\n"

    for position, user_id, user_name, stelle, *rest in classifica_stelle:
        bonus = rest[0] if rest else 0
        stelle_val = int(stelle)
        stelle_str = f"  {stelle_val}" if stelle_val < 10 else f"{stelle_val}"
        bonus_str = f" ({'+' if bonus > 0 else ''}{bonus})" if bonus != 0 else ""
        msg += f"<code>{stelle_str}</code>⭐ <b>{user_name}</b>{bonus_str}\n"

    msg += f"\n<i>Prova altri modelli:</i>\n"
    msg += f"• <code>/simuladaily participation-bonus</code>\n"
    msg += f"• <code>/simuladaily no_limit_with_lost</code>\n"
    msg += f"• <code>/simuladaily default</code>\n"
    msg += f"• <code>/simuladaily no-single-point-games</code>\n"
    msg += f"• <code>/simuladaily alternate-with-lost</code>\n"
    msg += f"• <code>/simuladaily standard</code>"

    await update.message.reply_text(msg, parse_mode="HTML", disable_web_page_preview=True)


def build_bonus_summary_text(target_date: datetime.date = None, require_promo: bool = False) -> str | None:
    """Builds the unified bonus summary HTML message for /bonus and the midday reminder.
    When require_promo=True, returns None unless at least one new or re-enabled game is active."""
    today = target_date or datetime.date.today()

    new_entries = []
    if getattr(config, "NEW_GAME_ENABLED", True):
        new_entries = [
            e for e in get_new_games_for_date(today)
            if e.game in GAMES and not GAMES[e.game].get("disabled", False)
        ]

    reenabled_entries = []
    if getattr(config, "REENABLED_GAME_ENABLED", True):
        reenabled_entries = [
            e for e in get_reenabled_games_for_date(today)
            if e.game in GAMES and not GAMES[e.game].get("disabled", False)
        ]

    if require_promo and not new_entries and not reenabled_entries:
        return None

    sections = []
    if getattr(config, "BONUS_GAME_ENABLED", True):
        jolly = get_bonus_game(today) or pick_or_get_bonus_game(today)
        if jolly and jolly.game in GAMES and not GAMES[jolly.game].get("disabled", False):
            j_link = _format_game_link(jolly.game, today)
            sections.append(
                f"🎰 <b>Gioco Jolly ({jolly.multiplier}x):</b>\n"
                f"• {j_link}"
            )

    if new_entries:
        new_emoji = getattr(config, "NEW_GAME_EMOJI", "🆕")
        lines = [f"{new_emoji} <b>Giochi nuovi:</b>"]
        for entry in new_entries:
            g_link = _format_game_link(entry.game, today)
            lines.append(f"• {g_link} <b>[{entry.multiplier}x]</b>")
        sections.append("\n".join(lines))

    if reenabled_entries:
        reenabled_emoji = getattr(config, "REENABLED_GAME_EMOJI", "✨")
        lines = [f"{reenabled_emoji} <b>Giochi riattivati:</b>"]
        for entry in reenabled_entries:
            g_link = _format_game_link(entry.game, today)
            lines.append(f"• {g_link} <b>[{entry.multiplier}x]</b>")
        sections.append("\n".join(lines))

    if not sections:
        return None

    return "✨ <b>Giochi Bonus di oggi</b> ✨\n\n" + "\n\n".join(sections)


async def cmd_bonus_games(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Shows all games with an active bonus today (Jolly, New games, Re-enabled games)."""
    msg = build_bonus_summary_text(datetime.date.today(), require_promo=False)
    if not msg:
        await update.message.reply_text("Nessun gioco bonus attivo oggi.")
        return

    mymsg = await update.message.reply_text(msg, parse_mode="HTML", disable_web_page_preview=True)
    schedule_delete(context, [mymsg, update.message], after_seconds=60, name_prefix="bonus_delete", msg_id=update.message.message_id)


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

    model = "default"
    if not context.bot_data.get("manual_riassunto", None):
        # il riassunto viene fatto per il giorno precedente, perché scatta a mezzanotte e qualcosa
        classifica_stelle = daily_ranking(model, yesterday)
    else:
        classifica_stelle = daily_ranking(model)

    yesterday_bonus = get_bonus_game(yesterday)
    yesterday_new = get_new_games_for_date(yesterday, sync=False)
    yesterday_reenabled = get_reenabled_games_for_date(yesterday, sync=False)
    bonus_lines = []
    if yesterday_bonus:
        yg_emoji = GAMES.get(yesterday_bonus.game, {}).get("emoji", "🎮")
        bonus_lines.append(f"🎰 <i>Gioco Jolly: {yg_emoji} {yesterday_bonus.game} ({yesterday_bonus.multiplier}x punti)</i>")
    if yesterday_new:
        new_emoji = getattr(config, "NEW_GAME_EMOJI", "🆕")
        new_labels = ", ".join(
            f"{GAMES.get(e.game, {}).get('emoji', '🎮')} {e.game} ({e.multiplier}x)"
            for e in yesterday_new
        )
        bonus_lines.append(f"{new_emoji} <i>Giochi Nuovi: {new_labels}</i>")
    if yesterday_reenabled:
        reenabled_emoji = getattr(config, "REENABLED_GAME_EMOJI", "✨")
        reenabled_labels = ", ".join(
            f"{GAMES.get(e.game, {}).get('emoji', '🎮')} {e.game} ({e.multiplier}x)"
            for e in yesterday_reenabled
        )
        bonus_lines.append(f"{reenabled_emoji} <i>Giochi Riattivati: {reenabled_labels}</i>")
    bonus_note = ("\n".join(bonus_lines) + "\n\n") if bonus_lines else ""

    message = f"<b>Ecco come è andata oggi {yesterday.strftime('%Y-%m-%d')}</b>:\n{bonus_note}"

    min_score = min([s for _, _, _, s, *_ in classifica_stelle]) if classifica_stelle else None
    award_poop = len(classifica_stelle) >= 4

    for position, user_id, user_name, stelle, *rest in classifica_stelle:
        bonus = rest[0] if rest else 0
        user_id = int(user_id)
        stelle_val = int(stelle)
        stelle_formatted = f"  {stelle_val}" if stelle_val < 10 else f"{stelle_val}"
        bonus_str = f" ({'+' if bonus > 0 else ''}{bonus})" if bonus != 0 else ""

        is_last = award_poop and (stelle_val == min_score) and (position > 3)
        poop_str = f" {POOP_MEDAL.strip()}" if is_last else ""

        message += f"{stelle_formatted}{STAR_SYMBOL} {user_name}{bonus_str}{poop_str}\n"

        if not context.bot_data.get("manual_riassunto", None):
            Punti.create(date=yesterday, user_id=user_id, user_name=user_name, punti=stelle_val)

            if position <= 3 or is_last:
                Medaglia.create(
                    date=yesterday,
                    timestamp=int(time.time()),
                    chat_id=int(ID_GIOCHINI),
                    user_id=int(user_id),
                    user_name=user_name,
                    gold=1 if position == 1 else None,
                    silver=1 if position == 2 else None,
                    bronze=1 if position == 3 else None,
                    last=1 if is_last else None,
                )

    # for position, user_id, user_name, stelle in classifica_stelle:
        # user_id, user_name = user.split("_|_")
        

        # if not context.bot_data.get("manual_riassunto", None) and position <= 3:
            

    await context.bot.send_message(chat_id=ID_GIOCHINI, text=message, parse_mode="HTML", disable_web_page_preview=True)

    this_month = yesterday.replace(day=1)
    message = f"<b>Classifica di questo mese ({this_month.strftime('%B')})</b>:\n\n"

    query = list(
        Punti.select(Punti.user_id, Punti.user_name, peewee.fn.SUM(Punti.punti).alias("totale"))
        .where(Punti.date >= this_month)
        .order_by(peewee.fn.SUM(Punti.punti).desc())
        .group_by(Punti.user_id)
        .limit(10)
    )
    display_names = get_display_names(q.user_id for q in query)

    for q in query:
        name = display_names.get(q.user_id, q.user_name)
        message += f"[{q.totale}] {name}\n"

    next_month = this_month.replace(day=28) + datetime.timedelta(days=4)
    last_day_of_month = next_month - datetime.timedelta(days=next_month.day)
    if yesterday == last_day_of_month:
        message += "Ultimo giorno del mese!! Classifica finale!!"

    await context.bot.send_message(chat_id=ID_GIOCHINI, text=message, parse_mode="HTML", disable_web_page_preview=True)

    medaglie_str = medaglie_count(target_date=yesterday)

    await context.bot.send_message(chat_id=ID_GIOCHINI, text=medaglie_str, parse_mode="HTML", disable_web_page_preview=True)

    message2 = '<a href="https://trifase.online/giochini">★ Classifiche online! ★</a>'
    await context.bot.send_message(chat_id=ID_GIOCHINI, text=message2, disable_web_page_preview=True, parse_mode="HTML")

    # Annuncio del gioco Jolly per la nuova giornata
    if getattr(config, "BONUS_GAME_ENABLED", True) and not context.bot_data.get("manual_riassunto", None):
        bonus_today = pick_or_get_bonus_game(today)
        if bonus_today:
            emoji = GAMES.get(bonus_today.game, {}).get("emoji", "🎮")
            url = GAMES.get(bonus_today.game, {}).get("url", "")
            game_text = f'<a href="{url}">{emoji} {bonus_today.game}</a>' if url else f"<b>{emoji} {bonus_today.game}</b>"
            jolly_msg = (
                f"🎰 <b>GIOCO JOLLY DI OGGI ({today.strftime('%d/%m/%Y')})</b> 🎰\n\n"
                f"Il gioco estratto per oggi è {game_text}!\n"
                f"Tutti i punti ottenuti in questo gioco varranno <b>{bonus_today.multiplier}x</b> {STAR_SYMBOL}!\n\n"
                f"Buona sfida a tutti! 🍀"
            )
            await context.bot.send_message(
                chat_id=ID_GIOCHINI,
                text=jolly_msg,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )

    context.bot_data["manual_riassunto"] = False


async def heartbeat(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Make a GET to betterstack
    """
    hb_id = HEARTBEAT_ID
    url = f"https://uptime.betterstack.com/api/v1/heartbeat/{hb_id}"

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code == 200:
            print("[AUTO] Heartbeat sent successfully.")
        else:
            print("[AUTO] Failed to send heartbeat. Status code: {response.status_code}")


async def classifica_istantanea(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    model = "default"

    # if "-skip-empty" in context.args:
    #     model = "skip-empty"
    # elif "-alternate" in context.args:
    #     model = "alternate"
    # elif "-no-timestamp" in context.args:
    #     model = "no-timestamp"
    # elif "-alternate-with-lost" in context.args:
    #     model = "alternate-with-lost"
    # elif "-no-limit-of-3" in context.args:
    #     model = "no-limit-of-3"
    # elif "-standard" in context.args:
    #     model = "standard"
    # elif "-allow-ex-aequo" in context.args:
    #     model = "allow-ex-aequo"

    classifica_stelle = daily_ranking(model)
    # print(cambiamenti)

    message = "Ecco la classifica temporanea di oggi:\n\n"

    for position, user_id, user_name, stelle, *rest in classifica_stelle:
        bonus = rest[0] if rest else 0
        stelle_val = int(stelle)
        stelle_formatted = f"  {stelle_val}" if stelle_val < 10 else f"{stelle_val}"
        bonus_str = f" ({'+' if bonus > 0 else ''}{bonus})" if bonus != 0 else ""

        message += f"{stelle_formatted}{STAR_SYMBOL} {user_name}{bonus_str}\n"

    await update.message.reply_text(message, parse_mode="HTML", disable_web_page_preview=True)

    # This will delete the original command after 30 secs
    await delete_original_command(update, context, 30)


def _format_game_link(game_name: str, target_date: datetime.date) -> str:
    g_info = GAMES.get(game_name, {})
    g_emoji = g_info.get("emoji", "🎮")
    g_url = g_info.get("url", "")
    g_day = get_day_from_date(g_info["date"], g_info["day"], game_name, target_date)
    return f'<a href="{g_url}">{g_emoji} {game_name} #{g_day}</a>' if g_url else f"<b>{g_emoji} {game_name} #{g_day}</b>"


async def daily_reminder(context: ContextTypes.DEFAULT_TYPE, pin=True) -> None:
    today = datetime.date.today()
    bonus_today = (get_bonus_game(today) or pick_or_get_bonus_game(today)) if getattr(config, "BONUS_GAME_ENABLED", True) else None
    bonus_game_name = bonus_today.game if bonus_today else None
    bonus_multiplier = bonus_today.multiplier if bonus_today else 1

    new_entries = get_new_games_for_date(today)
    new_games_map = {
        bg.game: bg.multiplier
        for bg in new_entries
        if bg.game in GAMES and not GAMES[bg.game].get("disabled", False)
    }
    new_emoji = getattr(config, "NEW_GAME_EMOJI", "🆕")

    reenabled_entries = get_reenabled_games_for_date(today)
    reenabled_games_map = {
        bg.game: bg.multiplier
        for bg in reenabled_entries
        if bg.game in GAMES and not GAMES[bg.game].get("disabled", False)
    }
    reenabled_emoji = getattr(config, "REENABLED_GAME_EMOJI", "✨")

    categorie = set([GAMES[x]["category"] for x in GAMES.keys()])
    categorie = sorted(list(categorie)) # alphabetical order
    message = "Buongiorno, ecco a cosa si gioca oggi!\n\n"

    header_highlights = []
    if bonus_today and bonus_game_name in GAMES:
        b_link = _format_game_link(bonus_game_name, today)
        header_highlights.append(f"🎰 <b>Gioco Jolly di oggi ({bonus_multiplier}x):</b> {b_link}")
    if new_games_map:
        new_links = ", ".join(_format_game_link(g_name, today) for g_name in new_games_map.keys())
        header_highlights.append(f"{new_emoji} <b>Giochi nuovi ({getattr(config, 'NEW_GAME_MULTIPLIER', 2)}x):</b> {new_links}")
    if reenabled_games_map:
        reenabled_links = ", ".join(_format_game_link(g_name, today) for g_name in reenabled_games_map.keys())
        header_highlights.append(f"{reenabled_emoji} <b>Giochi riattivati ({getattr(config, 'REENABLED_GAME_MULTIPLIER', 3)}x):</b> {reenabled_links}")
    if header_highlights:
        message += "\n".join(header_highlights) + "\n\n"

    for categoria in categorie:
        message += f"<b>{categoria}</b>\n"
        for game in GAMES.keys():
            if GAMES[game].get("disabled", False):
                continue
            if GAMES[game]["category"] == categoria:
                day = get_day_from_date(GAMES[game]["date"], GAMES[game]["day"], game, today)
                if bonus_game_name and game == bonus_game_name:
                    badge = format_bonus_badge(bonus_multiplier, "jolly", bold=True)
                elif game in reenabled_games_map:
                    badge = format_bonus_badge(reenabled_games_map[game], "reenabled", bold=True)
                elif game in new_games_map:
                    badge = format_bonus_badge(new_games_map[game], "new_game", bold=True)
                else:
                    badge = ""
                message += f'<a href="{GAMES[game]["url"]}">{GAMES[game]["emoji"]} {game} #{day}</a>{badge}\n'
        message += "\n"
    # for game in GAMES.keys():
    #     day = get_day_from_date(GAMES[game]['date'], GAMES[game]['day'], game, datetime.date.today())
    #     message += f'<a href="{GAMES[game]["url"]}">{GAMES[game]["emoji"]} {game} #{day}</a>\n'
    mypost = await context.bot.send_message(chat_id=ID_GIOCHINI, text=message, disable_web_page_preview=True, parse_mode="HTML")
    message2 = '<a href="https://trifase.online/giochini">★ Classifiche online! ★</a>'
    await context.bot.send_message(chat_id=ID_GIOCHINI, text=message2, disable_web_page_preview=True, parse_mode="HTML")
    if pin:
        await mypost.pin(disable_notification=True)


async def new_games_reminder(context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Sends a midday reminder using the unified /bonus message when new or re-enabled games are active."""
    message = build_bonus_summary_text(datetime.date.today(), require_promo=True)
    if not message:
        return False

    await context.bot.send_message(
        chat_id=ID_GIOCHINI,
        text=message,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    return True


async def make_backup(context: ContextTypes.DEFAULT_TYPE) -> None:
    now = datetime.datetime.today().strftime("%Y%m%d_%H%M%S")

    backup_dir = "backups"
    archive_name = f"{backup_dir}/giochini-{now}-backup.zip"
    files_to_backup = ["db/sqlite.db"]

    with zipfile.ZipFile(archive_name, "w") as zip_ref:
        for file in files_to_backup:
            zip_ref.write(file)

    with open(archive_name, "rb") as f:
        await context.bot.send_document(chat_id=BACKUP_DEST, document=f)
    logging.info("[AUTO] Backup DB eseguito.")


def schedule_delete(
    context: ContextTypes.DEFAULT_TYPE,
    messages: list,
    after_seconds: int = 10,
    name_prefix: str = "delete",
    msg_id: int | str | None = None,
) -> None:
    valid = [m for m in messages if m is not None]
    if not valid or not getattr(context, "job_queue", None):
        return
    job_name = f"{name_prefix}_{msg_id}" if msg_id is not None else name_prefix
    context.job_queue.run_once(delete_post, after_seconds, data=valid, name=job_name)


async def delete_original_command(update: Update, context: ContextTypes.DEFAULT_TYPE, after_seconds: int = 10) -> None:
    command_msg = getattr(update, "message", None) or getattr(update, "effective_message", None)
    if command_msg:
        schedule_delete(
            context,
            [command_msg],
            after_seconds=after_seconds,
            name_prefix="cmd_delete",
            msg_id=command_msg.message_id,
        )


async def delete_post(context: ContextTypes.DEFAULT_TYPE) -> None:
    items = context.job.data or []
    for item in items:
        if item is None:
            continue
        try:
            if isinstance(item, tuple) and len(item) == 2:
                chat_id, message_id = item
                await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            else:
                await item.delete()
        except Exception as e:
            logger.debug(f"Could not delete message {item}: {e}")


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
    PuntiBonus.create_table()
    Medaglia.create_table()
    GameStatus.create_table()
    GameAnchor.create_table()
    ensure_punteggi_pk_migration()
    ensure_utenti_schema_and_backfill()
    ensure_gioco_bonus_schema()
    # Setting.create_table()
    
    sync_disabled_games()
    sync_new_game_bonuses(datetime.date.today())
    sync_reenabled_game_bonuses(datetime.date.today())

    # Recupero i settings e li storo in memoria
    if "settings" not in app.bot_data:
        app.bot_data["settings"] = {}

    with open("db/user_settings.json") as settings_db:
        settings = json.load(settings_db)
        app.bot_data["settings"] = settings

    my_commands = [
        BotCommand('myday', 'Giochi che ti mancano oggi', api_kwargs={'is_ephemeral': True}),
        BotCommand('myscore', 'Il tuo punteggio e piazzamenti di oggi', api_kwargs={'is_ephemeral': True}),
        BotCommand('ranking', 'Classifica generale di oggi'),
        BotCommand('classifica', 'Classifiche di oggi per gioco (o /c gioco)'),
        BotCommand('bonus', 'Giochi bonus attivi oggi (Jolly e Nuovi)'),
        BotCommand('favs', 'Scegli i tuoi giochi preferiti'),
        BotCommand('mystats', 'Le tue statistiche (o /mystats gioco)'),
        BotCommand('medaglie', 'Medagliere del mese'),
        BotCommand('top', 'Classifica punti All-Time'),
        BotCommand('topmedaglie', 'Medagliere All-Time'),
        BotCommand('weekstat', 'Statistiche degli ultimi 7 giorni'),
        BotCommand('help', 'Tutti i comandi e guida al bot'),
    ]
    await app.bot.set_my_commands(my_commands)

    await app.bot.send_message(chat_id=ID_BOTCENTRAL, text="Bot riavviato! 🔄")

    logger.info("Pronti!")


async def sync_telegram_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user:
        sync_user(
            update.effective_user.id,
            update.effective_user.full_name,
            update.effective_user.username,
        )


def main():
    defaults = Defaults(
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )

    builder = ApplicationBuilder()
    builder.token(TOKEN)
    builder.defaults(defaults)
    builder.post_init(post_init)

    app = builder.build()
    app.add_handler(TypeHandler(Update, sync_telegram_user), -1)

    j = app.job_queue
    # j.run_repeating(daily_reminder, interval=datetime.timedelta(days=1), first=datetime.time(hour=8, minute=00, tzinfo=pytz.timezone("Europe/Rome")), data=None)
    j.run_daily(daily_reminder, datetime.time(hour=8, minute=0, tzinfo=pytz.timezone("Europe/Rome")), data=None)
    j.run_daily(new_games_reminder, datetime.time(hour=12, minute=0, tzinfo=pytz.timezone("Europe/Rome")), data=None)
    j.run_daily(riassunto_serale, datetime.time(hour=0, minute=10, tzinfo=pytz.timezone("Europe/Rome")), data=None)
    j.run_daily(make_backup, datetime.time(hour=2, minute=0, tzinfo=pytz.timezone("Europe/Rome")), data=None)
    j.run_daily(check_unused_games, datetime.time(hour=0, minute=10, tzinfo=pytz.timezone("Europe/Rome")), data=None)
    j.run_daily(auto_disable_games, datetime.time(hour=7, minute=0, tzinfo=pytz.timezone("Europe/Rome")), data=None)
    j.run_repeating(heartbeat, interval=60 * 15, first=10)

    app.add_handler(CommandHandler("classificona", classificona), 1)
    app.add_handler(CommandHandler(["myday", "mytoday", "myonly", "my", "today", "daily"], mytoday), 1)
    app.add_handler(CommandHandler(["myscore", "score"], myscore), 1)
    app.add_handler(CommandHandler(["mystats", "mystat", "statistiche"], mystats), 1)
    app.add_handler(CommandHandler(["groupstats", "gstats", "statsgroup"], groupstats_command), 1)
    app.add_handler(CommandHandler(["weekstat", "weekstats", "wstat", "week"], week_stats_command), 1)
    app.add_handler(CommandHandler("help", show_help), 1)
    app.add_handler(CommandHandler(["list", "lista"], list_games), 1)
    app.add_handler(CommandHandler(["dailyranking", "ranking", "oggi"], classifica_istantanea), 1)
    app.add_handler(CommandHandler(["simuladaily", "simula"], simula_daily), 1)
    app.add_handler(CommandHandler(["bonus", "giochibonus"], cmd_bonus_games), 1)
    app.add_handler(CommandHandler(["stelle", "stelline", "malus", "punti"], cmd_stelle), 1)
    app.add_handler(CommandHandler(["puntioggi", "bonusoggi", "bonuslist"], cmd_bonus_oggi), 1)

    # app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))

    # app.add_handler(CallbackQueryHandler(handle_web_app_data, pattern=r"^webapp_launch"))

    app.add_handler(CommandHandler(["c", "classifica"], post_single_classifica), 2)
    app.add_handler(CommandHandler("top", top_players), 1)
    app.add_handler(CommandHandler(["topmedaglie", "top_medaglie"], top_medaglie), 1)
    app.add_handler(CommandHandler("medaglie", medaglie_mensile), 1)
    app.add_handler(CommandHandler(["favs", "fav"], setting_fav), 3)

    app.add_handler(MessageHandler(filters.COMMAND, unknown_command_handler), 1000)

    app.add_handler(CommandHandler("topgames", top_games), 1)
    app.add_handler(CallbackQueryHandler(classifica_buttons, pattern=r"^cls_"))
    app.add_handler(CallbackQueryHandler(fav_add, pattern=r"^favs_add_"))
    app.add_handler(CallbackQueryHandler(fav_del, pattern=r"^favs_del_"))
    app.add_handler(CallbackQueryHandler(fav_close, pattern=r"^fav_close"))
    app.add_handler(CallbackQueryHandler(fav_extra_toggle, pattern=r"^fav_more"))

    app.add_handler(CallbackQueryHandler(mytoday_full, pattern=r"^myday_more"))
    app.add_handler(CallbackQueryHandler(myonly_full, pattern=r"^myonly_more"))

    app.add_handler(MessageHandler(filters.ALL, spell_message), -150)
    app.add_handler(CommandHandler("enable_debug", enable_debug), 211)
    app.add_handler(CommandHandler("disable_debug", disable_debug), 212)
    app.add_handler(CommandHandler("debug", debug_text), 213)
    app.add_handler(CommandHandler("backup", manual_backup), 1)
    app.add_handler(CommandHandler("giochiamo", manual_daily_reminder), 1)
    app.add_handler(CommandHandler(["nuovigiochi", "newgames"], manual_new_games_reminder), 1)
    app.add_handler(CommandHandler("riassuntone", manual_riassunto), 1)
    app.add_handler(CommandHandler(["listdisabled", "disabledlist", "showdisabled", "disabled"], show_disabled_games), 1)
    app.add_handler(CommandHandler(["checkunused", "unusedcheck", "nongiocati", "unused", "checkunusedgames"], manual_check_unused), 1)
    app.add_handler(CommandHandler(["checkdisable", "forcecheckdisable"], manual_auto_disable), 1)
    app.add_handler(CommandHandler(["setanchor", "setdate"], cmd_setanchor), 1)
    app.add_handler(CommandHandler("ask", cmd_ask), 1)
    app.add_handler(CommandHandler("restart", restart_bot), 1)
    app.add_handler(CommandHandler("refresh", refresh_bot), 1)


    
    app.add_handler(MessageHandler(giochini_results_filter & ~filters.UpdateType.EDITED, parse_punteggio))

    # Error handler
    app.add_error_handler(error_handler)

    app.run_polling(drop_pending_updates=False, allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
