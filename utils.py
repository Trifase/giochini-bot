import datetime
from collections import defaultdict

import httpx
import peewee
from dataclassy import dataclass
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext.filters import MessageFilter

from config import ID_GIOCHINI, MEDALS, TOKEN, Medaglia, Punteggio
from games import ALL_GAMES as GAMES
from games import get_day_from_date


@dataclass
class Classifica:
    game: str = ""
    day: str = ""
    date: datetime.date = None
    emoji: str = ""
    pos: list[tuple[str, str]] = []
    valid: bool = True
    header: str = ""
    last: str = ""

    # def __repr__(self):
    #     classifica = ''
    #     classifica += self.header + '\n'
    #     for posto, username, tries in self.pos:
    #         classifica += f'{MEDALS.get(posto, "")}{username} ({tries})\n'
    #     if self.last:
    #         classifica += f'{self.last}'
    #     return classifica

    def to_string(self) -> str:
        classifica = ""
        classifica += self.header + "\n"
        for posto, username, tries in self.pos:
            classifica += f'{MEDALS.get(posto, "")}{username} ({tries})\n'
        if self.last:
            classifica += f"{self.last}"
        return classifica


class GameFilter(MessageFilter):
    def filter(self, message):
        if not message.text:
            return False

        quadratini = [
            "🟥",
            "🟩",
            "⬜️",
            "🟨",
            "⬛️",
            "🟦",
            "🟢",
            "⚫️",
            "🟡",
            "🟠",
            "🔵",
            "🟣",
            "✅",
            "🌕",
            "🌗",
            "🌘",
            "🌑",
        ]

        if b"\xE2\xAC\x9B".decode("utf-8") in message.text:
            return True

        # Se ha qualche emoji colorata, probabilmente è un messaggio di un gioco
        if any(c in message.text for c in quadratini):
            return True

        # Eccezione per Plotwords, che non usa emoji
        if "Plotwords" in message.text and "Clues used" in message.text:
            return True

        if "Murdle for" in message.text and ("❌" in message.text or "✅" in message.text) and "🔪" in message.text:
            return True

        if "#Angle" in message.text and ("⬇️" in message.text or "⬆️" in message.text or "🎉" in message.text):
            return True

        if "#travle " in message.text and "https://imois.in/games/travle" in message.text:
            return True

        if "DOMINO FIT #" in message.text and any(x in message.text for x in ["🏅", "🥈", "🥉"]):
            return True

        if all(x in message.text for x in ["❌", "🎧"]):  # spotle
            return True

        if "https://www.chronophoto.app/daily.html" in message.text and "Round 1" in message.text and "Round 4:" in message.text:
            return True

        return False


def daily_ranking(model: str = "alternate-with-lost", from_day: datetime.date = None):
    """Creates the daily ranking for all games."""
    points = defaultdict(int)
    today = datetime.date.today()
    if not from_day:
        from_day = today

    # Score Calculation models:

    # standard: 3 points to the first, 2 points to the second and 1 point to the third, no matter how many plays there are.

    # skip-empty: same as the standard, but games with less than limit plays (default: 3) are not counted at all

    # alternate: We give n points to the first, n-1 to the second and so on, where n is the number of players in the game.
    # It's still capped at three, so if a game has 7 plays, the first gets 3 points, the second 2 and the third 1, same as standard;
    # BUT if a game has only two plays,the first gets only two points, and the second 1. If it has only one play, the winner gets a single point.

    # alternate-with-lost: same as alternate, but we count lost plays.
    # GAMES = get_games()
    for game in GAMES.keys():
        day = get_day_from_date(GAMES[game]["date"], GAMES[game]["day"], game, from_day)

        query = (
            Punteggio.select(Punteggio.user_name, Punteggio.user_id)
            .where(
                Punteggio.day == day,
                Punteggio.game == game,
                Punteggio.chat_id == ID_GIOCHINI,
                Punteggio.lost == False,
            )
            .order_by(Punteggio.tries, Punteggio.extra.desc(), Punteggio.timestamp)
            .limit(3)
        )

        # Score Processing
        if model == "standard":
            for i, _ in enumerate(query):
                try:
                    name = f"{query[i].user_id}_|_{query[i].user_name}"
                    points[name] += 3 - i
                except IndexError:
                    pass

        if model == "alternate":
            # This include lost plays, that we filter out when we assign points.
            query_alternate = (
                Punteggio.select(Punteggio.user_name, Punteggio.user_id)
                .where(
                    Punteggio.day == day,
                    Punteggio.game == game,
                    Punteggio.chat_id == ID_GIOCHINI,
                    Punteggio.lost == False,
                )
                .order_by(Punteggio.tries, Punteggio.extra.desc(), Punteggio.timestamp)
                .limit(3)
            )
            for i, _ in enumerate(query_alternate):
                try:
                    if not query[i].lost:
                        name = f"{query[i].user_id}_|_{query[i].user_name}"
                        points[name] += len(query) - i
                except IndexError:
                    pass

        if model == "alternate-with-lost":
            # This include lost plays
            query_alternate = (
                Punteggio.select(Punteggio.user_name, Punteggio.user_id)
                .where(Punteggio.day == day, Punteggio.game == game, Punteggio.chat_id == ID_GIOCHINI)
                .order_by(Punteggio.tries, Punteggio.extra.desc(), Punteggio.timestamp)
                .limit(3)
            )
            for i, _ in enumerate(query_alternate):
                try:
                    if not query[i].lost:
                        name = f"{query[i].user_id}_|_{query[i].user_name}"
                        points[name] += len(query_alternate) - i
                except IndexError:
                    pass

        if model == "skip-empty":
            limit = 3
            if len(query) < limit:
                continue
            for i, _ in enumerate(query):
                try:
                    name = f"{query[i].user_id}_|_{query[i].user_name}"
                    points[name] += 3 - i
                except IndexError:
                    pass

    cambiamenti = dict(points)
    cambiamenti = sorted(cambiamenti.items(), key=lambda x: x[1], reverse=True)
    return cambiamenti


def str_as_int(string: str) -> int:
    return int(string.replace(".", ""))


def get_date_from_day(game: str, day: str) -> datetime.date:
    # GAMES = get_games()
    days_difference = int(GAMES[game]["day"]) - int(day)
    return GAMES[game]["date"] - datetime.timedelta(days=days_difference)


def correct_name(name: str) -> str:
    # GAMES = get_games()
    return list(GAMES.keys())[[x.lower() for x in GAMES.keys()].index(name.lower())]


def make_buttons(game: str, message_id: int, day: int) -> InlineKeyboardMarkup:
    today = get_day_from_date(GAMES[game]["date"], GAMES[game]["day"], game, datetime.date.today())
    date_str = f"{get_date_from_day(game, day).strftime('%Y-%m-%d')}"
    day = int(day)
    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("⬅️", callback_data=f"cls_{game}_{message_id}_{day - 1}"),
                InlineKeyboardButton("📆 Oggi", callback_data=f"cls_{game}_{message_id}_{today}"),
                InlineKeyboardButton("➡️", callback_data=f"cls_{game}_{message_id}_{day + 1}"),
            ],
            [InlineKeyboardButton(date_str, callback_data="cls_do_nothing")],
        ]
    )
    return buttons


def process_tries(game: str, tries: int | str) -> int | str:
    # This is a little exception for HighFive scores, which are negative because in the game the more the better.
    # We want to show them as positive.
    if game == "HighFive":
        tries = abs(tries)

    # For Timeguesser, scores are points, the more the better. Max points is 50_000 so we save them as differences from max.
    if game == "TimeGuesser":
        tries = 50_000 - tries

    # For Chronophoto, scores are points, the more the better. Max points is 5_000 so we save them as differences from max.
    if game == "Chronophoto":
        tries = 5_000 - tries

    # For FoodGuessr, scores are points, the more the better. Max points is 15_000 so we save them as differences from max.
    if game == "FoodGuessr":
        tries = 15_000 - tries

    # For Spellcheck, scores are green squares, the more the better. Max points is 15 so we save them as differences from max.
    if game == "Spellcheck":
        tries = 15 - tries

    # For TempoIndovinr, scores are points, the more the better. Max points is 1_000 so we save them as differences from max.
    if game == "TempoIndovinr":
        tries = 1_000 - tries

    # For Picsey, scores are points, the more the better. Max points is 100 so we save them as differences from max.
    if game == "Picsey":
        tries = 100 - tries

    # So, murdle points are time. I store time (for exampe: 5:12) as an int (512) so I can order them. Here I convert them back to string, putting a semicolon two chars from the end.
    if game == "Murdle":
        tries = str(tries)[:-2] + ":" + str(tries)[-2:]

    # For NerdleCross, scores are points, the more the better. Max points is 6 so we save them as differences from max.
    if game == "NerdleCross":
        tries = 6 - tries
    return tries


def streak_at_day(user_id, game, day) -> int:
    # print(f'Searching streak for {user_id}, {game}, {day}')
    day = int(day)
    streak = 0

    games = (
        Punteggio.select(Punteggio.day, Punteggio.user_id)
        .where(
            Punteggio.user_id == int(user_id),
            Punteggio.game == game,
            Punteggio.lost == False,
        )
        .order_by(Punteggio.day.desc())
    )

    gamedays = set([int(x.day) for x in games])
    # print(gamedays)

    # day can never be in gamedays. Dumb.
    # if day not in gamedays:
    # return streak

    for day in range(day - 1, 0, -1):
        if day in gamedays:
            streak += 1
        else:
            break

    # print(f'Streak found: {streak}')
    return streak


def longest_streak(user_id, game) -> int:
    streak = Punteggio.select(peewee.fn.MAX(Punteggio.streak)).where(Punteggio.user_id == user_id, Punteggio.game == game)

    return streak.scalar()


def update_streak():
    c = 0
    for punt in Punteggio.select().where(Punteggio.streak < 500):
        c += 1
        streak = streak_at_day(punt.user_id, punt.game, int(punt.day))
        if c % 500 == 0:
            print(f"Selected: [{c}] {punt.user_id} {punt.game} {punt.day} {punt.streak} | calc-streak: {streak}")
        punt.streak = streak + 1
        # print(f"New Streak: {punt.streak}")
        punt.save()


def personal_stats(user_id: int) -> str:
    intro = "Ecco le tue statistiche personali:\n\n"

    # longest streak best game streak
    long_streak_query = (
        Punteggio.select(peewee.fn.MAX(Punteggio.streak).alias("streak"), Punteggio.game)
        .where(Punteggio.user_id == user_id)
        .group_by(Punteggio.game)
        .order_by(Punteggio.streak.desc())
        .limit(1)
    )
    long_streak = long_streak_query[0].streak
    long_streak_game = long_streak_query[0].game
    long_streak_string = f"Il tuo streak più lungo è di <b>{long_streak}</b> partite a <b>{long_streak_game}.</b>\n"

    # gioco più giocato
    most_played_query = (
        Punteggio.select(Punteggio.game, peewee.fn.COUNT(Punteggio.game).alias("c"))
        .where(Punteggio.user_id == user_id)
        .group_by(Punteggio.game)
        .order_by(peewee.fn.COUNT(Punteggio.game).desc())
        .limit(1)
    )
    most_played = most_played_query[0].game
    most_played_count = most_played_query[0].c
    most_played_string = f"Il gioco a cui hai giocato di più è <b>{most_played}</b> con <b>{most_played_count}</b> partite!\n"

    # gioco meno giocato
    least_played_query = (
        Punteggio.select(Punteggio.game, peewee.fn.COUNT(Punteggio.game).alias("c"))
        .where(Punteggio.user_id == user_id)
        .group_by(Punteggio.game)
        .order_by(peewee.fn.COUNT(Punteggio.game).asc())
        .limit(1)
    )
    least_played = least_played_query[0].game
    least_played_count = least_played_query[0].c
    least_played_string = f"Il gioco che ti piace di meno è <b>{least_played}</b>, hai giocato solo <b>{least_played_count}</b> partite...\n\n"

    # giocate totali
    total_plays = Punteggio.select(peewee.fn.COUNT(Punteggio.game).alias("c")).where(Punteggio.user_id == user_id).scalar()

    # tempo perso a giocare (considerando 2min a giocata), in DD:HH:MM
    single_play_minutes = 2
    total_time = total_plays * single_play_minutes
    duration = datetime.datetime.utcfromtimestamp(datetime.timedelta(minutes=total_time).total_seconds())
    total_plays_string = f"In totale hai fatto <b>{total_plays}</b> partite.\nA 2 minuti a partita, hai sprecato <b>{duration.strftime('%H ore e %M minuti')}</b> della tua vita.\n"

    # giocate perse totali
    total_loses = (
        Punteggio.select(peewee.fn.COUNT(Punteggio.game).alias("c"))
        .where(
            Punteggio.user_id == user_id,
            Punteggio.lost == True,
        )
        .scalar()
    )
    if total_loses:
        total_loses_string = f"In totale, hai perso <b>{total_loses}</b> partite.\n"

    result = intro + long_streak_string + most_played_string + least_played_string + total_plays_string
    if total_loses:
        result += total_loses_string
    return result


def group_stats(chat_id: int) -> str:
    message = "Ecco le classifiche globali:\n\n"

    # Totali x giocate.
    total_plays = Punteggio.select(peewee.fn.COUNT(Punteggio.game).alias("c")).where(Punteggio.chat_id == chat_id).scalar()
    total_lost = Punteggio.select(peewee.fn.COUNT(Punteggio.game).alias("c")).where(Punteggio.chat_id == chat_id, Punteggio.lost == True).scalar()
    max_day = Punteggio.select(peewee.fn.MAX(Punteggio.date).alias("max_day")).where(Punteggio.chat_id == chat_id).scalar()
    min_day = Punteggio.select(peewee.fn.MIN(Punteggio.date).alias("min_day")).where(Punteggio.chat_id == chat_id).scalar()
    tracked_games = Punteggio.select(Punteggio.game).where(Punteggio.chat_id == chat_id).distinct().count()
    # three most played games
    most_played_games = (
        Punteggio.select(Punteggio.game, peewee.fn.COUNT(Punteggio.game).alias("c"))
        .where(Punteggio.chat_id == chat_id)
        .group_by(Punteggio.game)
        .order_by(peewee.fn.COUNT(Punteggio.game).desc())
        .limit(3)
    )
    least_played_games = (
        Punteggio.select(Punteggio.game, peewee.fn.COUNT(Punteggio.game).alias("c"))
        .where(Punteggio.chat_id == chat_id)
        .group_by(Punteggio.game)
        .order_by(peewee.fn.COUNT(Punteggio.game).asc())
        .limit(3)
    )
    most_played_games = "\n".join([f"- {x.game} ({x.c})" for x in most_played_games])
    least_played_games = "\n".join([f"- {x.game} ({x.c})" for x in least_played_games])

    total_players = Punteggio.select(Punteggio.user_id).where(Punteggio.chat_id == chat_id).distinct().count()

    most_active_players = (
        Punteggio.select(Punteggio.user_name, peewee.fn.COUNT(Punteggio.user_name).alias("c"))
        .where(Punteggio.chat_id == chat_id)
        .group_by(Punteggio.user_name)
        .order_by(peewee.fn.COUNT(Punteggio.user_name).desc())
        .limit(3)
    )
    most_active_players = "\n".join([f"- {x.user_name} ({x.c})" for x in most_active_players])

    # the record with the longest streak, with game name, username, day
    longest_streak = (
        Punteggio.select(Punteggio.streak, Punteggio.game, Punteggio.user_name, Punteggio.day)
        .where(Punteggio.chat_id == chat_id)
        .order_by(Punteggio.streak.desc())
        .limit(1)
    )

    # day differences between two dates in YYYY-MM-DD format
    day_diff = (max_day - min_day).days

    message += f"Ci sono {total_plays} partire registrate in {day_diff} giorni, dal {min_day} al {max_day}.\n"
    message += f"In media sono {round(total_plays/day_diff, 2)} giocate al giorno.\n"
    message += f"In totale sono state perse {total_lost} partite (il {round(total_lost/total_plays*100, 2)}%).\n\n"
    message += f"Ci sono {tracked_games} giochi tracciati.\n\n"
    message += f"I tre giochi più giocati sono:\n{most_played_games}\n\n"
    message += f"I tre giochi meno giocati sono:\n{least_played_games}\n\n"
    message += f"Ci sono {total_players} giocatori registrati.\n\n"
    message += f"I tre giocatori più attivi sono:\n{most_active_players}\n\n"
    message += f"Lo streak più lungo è di {longest_streak[0].streak} partite consecutive a {longest_streak[0].game}, di {longest_streak[0].user_name}.\n"

    return message


def new_classifica():
    classifica = [
        {
            "game": "Wordle",
            "day": "828",
            "emoji": "🆒",
            "url": "https://www.nytimes.com/games/wordle/index.html",
            "pos": [
                (1, "Wordle", 31866384, "Lara", 2),
                (2, "Wordle", 286213405, "sofia", 3),
                (3, "Wordle", 542430195, "Lord Davide eSwatini 🇸🇿", 4),
            ],
        },
        {
            "game": "Parole",
            "day": "629",
            "emoji": "🇮🇹",
            "url": "https://pietroppeter.github.io/wordle-it",
            "pos": [
                (1, "Parole", 456481297, "Trifase", 3),
                (2, "Parole", 16337572, "Jacopo", 4),
                (3, "Parole", 31866384, "Lara", 4),
            ],
        },
        {
            "game": "Contexto",
            "day": "372",
            "emoji": "🔄",
            "url": "https://contexto.me",
            "pos": [(1, "Contexto", 286213405, "sofia", 66), (2, "Contexto", 542430195, "Lord Davide eSwatini 🇸🇿", 71)],
        },
        {
            "game": "Waffle",
            "day": "612",
            "emoji": "🧇",
            "url": "https://wafflegame.net/daily",
            "pos": [
                (1, "Waffle", 286213405, "sofia", 10),
                (2, "Waffle", 31866384, "Lara", 13),
                (3, "Waffle", 456481297, "Trifase", 13),
            ],
        },
        {
            "game": "HighFive",
            "day": "194",
            "emoji": "🖐️",
            "url": "https://highfivegame.app",
            "pos": [(1, "HighFive", 286213405, "sofia", 97), (2, "HighFive", 542430195, "Lord Davide eSwatini 🇸🇿", 91)],
        },
        {
            "game": "Connections",
            "day": "106",
            "emoji": "🔀",
            "url": "https://www.nytimes.com/games/connections",
            "pos": [(1, "Connections", 286213405, "sofia", 1)],
        },
        {
            "game": "Squareword",
            "day": "602",
            "emoji": "🔠",
            "url": "https://squareword.org",
            "pos": [
                (1, "Squareword", 286213405, "sofia", 11),
                (2, "Squareword", 542430195, "Lord Davide eSwatini 🇸🇿", 14),
                (3, "Squareword", 456481297, "Trifase", 20),
            ],
        },
        {
            "game": "Worldle",
            "day": "612",
            "emoji": "🗺️",
            "url": "https://worldle.teuteuf.fr",
            "pos": [
                (1, "Worldle", 286213405, "sofia", 1),
                (2, "Worldle", 349305191, "Lamantino Lamentino", 1),
                (3, "Worldle", 198379603, "Mario", 1),
            ],
        },
        {
            "game": "Tradle",
            "day": "568",
            "emoji": "🚢",
            "url": "https://oec.world/en/tradle",
            "pos": [
                (1, "Tradle", 286213405, "sofia", 2),
                (2, "Tradle", 96000757, "Roberto", 5),
                (3, "Tradle", 198379603, "Mario", 5),
            ],
        },
        {
            "game": "Flagle",
            "day": "581",
            "emoji": "🏁",
            "url": "https://www.flagle.io",
            "pos": [
                (1, "Flagle", 286213405, "sofia", 2),
                (2, "Flagle", 16337572, "Jacopo", 3),
                (3, "Flagle", 542430195, "Lord Davide eSwatini 🇸🇿", 4),
            ],
        },
        {
            "game": "Globle",
            "day": "294",
            "emoji": "🌍",
            "url": "https://globle-game.com",
            "pos": [
                (1, "Globle", 286213405, "sofia", 2),
                (2, "Globle", 61260596, "Moreno", 5),
                (3, "Globle", 198379603, "Mario", 5),
            ],
        },
        {
            "game": "WhereTaken",
            "day": "211",
            "emoji": "📸",
            "url": "http://wheretaken.teuteuf.fr",
            "pos": [
                (1, "WhereTaken", 286213405, "sofia", 3),
                (2, "WhereTaken", 542430195, "Lord Davide eSwatini 🇸🇿", 4),
                (3, "WhereTaken", 198379603, "Mario", 6),
            ],
        },
        {
            "game": "Cloudle",
            "day": "543",
            "emoji": "🌦️",
            "url": "https://cloudle.app",
            "pos": [
                (1, "Cloudle", 542430195, "Lord Davide eSwatini 🇸🇿", 4),
                (2, "Cloudle", 286213405, "sofia", 5),
                (3, "Cloudle", 31866384, "Lara", 6),
            ],
        },
        {
            "game": "GuessTheGame",
            "day": "499",
            "emoji": "🎮",
            "url": "https://guessthe.game",
            "pos": [
                (1, "GuessTheGame", 286213405, "sofia", 2),
                (2, "GuessTheGame", 456481297, "Trifase", 5),
                (3, "GuessTheGame", 198379603, "Mario", 5),
            ],
        },
        None,
        {
            "game": "TimeGuesser",
            "day": "135",
            "emoji": "📅",
            "url": "https://timeguessr.com",
            "pos": [
                (1, "TimeGuesser", 286213405, "sofia", 47262),
                (2, "TimeGuesser", 542430195, "Lord Davide eSwatini 🇸🇿", 44652),
                (3, "TimeGuesser", 16337572, "Jacopo", 33821),
            ],
        },
        {
            "game": "Moviedle",
            "day": "294",
            "emoji": "🎥",
            "url": "https://moviedle.app",
            "pos": [(1, "Moviedle", 286213405, "sofia", 2)],
        },
        {
            "game": "Picsey",
            "day": "100",
            "emoji": "🪟",
            "url": "https://picsey.io",
            "pos": [
                (1, "Picsey", 542430195, "Lord Davide eSwatini 🇸🇿", 96),
                (2, "Picsey", 456481297, "Trifase", 88),
                (3, "Picsey", 16337572, "Jacopo", 63),
            ],
        },
        {
            "game": "Murdle",
            "day": "95",
            "emoji": "🔪",
            "url": "https://murdle.com",
            "pos": [
                (1, "Murdle", 286213405, "sofia", "1:32"),
                (2, "Murdle", 456481297, "Trifase", "1:49"),
                (3, "Murdle", 542430195, "Lord Davide eSwatini 🇸🇿", "3:38"),
            ],
        },
        {
            "game": "Nerdle",
            "day": "614",
            "emoji": "🤓",
            "url": "https://nerdlegame.com",
            "pos": [(1, "Nerdle", 286213405, "sofia", 3), (2, "Nerdle", 542430195, "Lord Davide eSwatini 🇸🇿", 3)],
        },
    ]

    final = {}

    for game in classifica:
        if game is None:
            continue
        for pos in game["pos"]:
            # 0 = posizione
            # 1 = game
            # 2 = user_id
            # 3 = nickname
            # 4 = punteggio
            if pos[2] not in final:
                final[pos[2]] = {"nickname": pos[3], "gold": 0, "silver": 0, "bronze": 0, "total": 0}
            if pos[0] == 1:
                final[pos[2]]["gold"] += 1
            elif pos[0] == 2:
                final[pos[2]]["silver"] += 1
            elif pos[0] == 3:
                final[pos[2]]["bronze"] += 1
            final[pos[2]]["total"] += 1
    import pprint

    pprint.pprint(final)
    classifica_users = sorted(final.items(), key=lambda x: x[1]["total"], reverse=True)
    pprint.pprint(classifica_users)

    for user in classifica_users:
        print(f"{user[1]['nickname']} [{user[1]['total']}]\n{user[1]['gold']*'🥇'}{user[1]['silver']*'🥈'}{user[1]['bronze']*'🥉'}\n")


def medaglie_count(monthly=True) -> None:
    first_of_the_month = datetime.date.today().replace(day=1)
    month_name = first_of_the_month.strftime("%B")
    message = f"<b>Classifica mensile ({month_name}) delle medaglie:</b>\n\n"
    if not monthly:
        first_of_the_month = datetime.date(2020, 1, 1)
        message = "Classifica totale delle medaglie:\n\n"
    # Select user_name, medal, count(medal) from medaglie group by user_name, medal
    query = (
        Medaglia.select(
            Medaglia.user_name,
            peewee.fn.SUM(Medaglia.gold).alias("gold"),
            peewee.fn.SUM(Medaglia.silver).alias("silver"),
            peewee.fn.SUM(Medaglia.bronze).alias("bronze"),
        )
        .where(Medaglia.date >= first_of_the_month)
        .group_by(Medaglia.user_name)
        .order_by(
            peewee.fn.SUM(Medaglia.gold).alias("gold").desc(),
            peewee.fn.SUM(Medaglia.silver).alias("silver").desc(),
            peewee.fn.SUM(Medaglia.bronze).alias("bronze").desc(),
        )
        .limit(10)
    )

    if not query:
        message += "Non ci sono ancora medaglie questo mese."
        return message

    for q in query:
        message += f"{q.user_name} ({int(q.gold or 0)}/{int(q.silver or 0)}/{int(q.bronze or 0)}):\n{int(q.gold or 0)*MEDALS[1][:-1]}{int(q.silver or 0)*MEDALS[2][:-1]}{int(q.bronze or 0)*MEDALS[3][:-1]}\n"
    return message


async def react_to_message(update, context, chat_id, message_id, reaction, is_big):
    bot_token = TOKEN
    api_url = f"https://api.telegram.org/bot{bot_token}/setMessageReaction"

    # supported_emoji = 'Currently, it can be one of "👍", "👎", "❤", "🔥", "🥰", "👏", "😁", "🤔", "🤯", "😱", "🤬", "😢", "🎉", "🤩", "🤮", "💩", "🙏", "👌", "🕊", "🤡", "🥱", "🥴", "😍", "🐳", "❤‍🔥", "🌚", "🌭", "💯", "🤣", "⚡", "🍌", "🏆", "💔", "🤨", "😐", "🍓", "🍾", "💋", "🖕", "😈", "😴", "😭", "🤓", "👻", "👨‍💻", "👀", "🎃", "🙈", "😇", "😨", "🤝", "✍", "🤗", "🫡", "🎅", "🎄", "☃", "💅", "🤪", "🗿", "🆒", "💘", "🙉", "🦄", "😘", "💊", "🙊", "😎", "👾", "🤷‍♂", "🤷", "🤷‍♀", "😡"'
    dati = {
        "chat_id": chat_id,
        "message_id": message_id,
        "reaction": [
            {
                "type": "emoji",
                "emoji": reaction,
            }
        ],
        "is_big": is_big,
    }

    async with httpx.AsyncClient() as client:
        await client.post(api_url, json=dati)
        # risposta_json = risposta.json()


# Testing

# giochini = get_giochini()
# print(giochini)
# update_streak()
# streak =streak_at_day(user_id=31866384, game='Cloudle', day='736')
# print(group_stats(-1001681280224))
# print(streak)
# from games import Wordle
# print(Wordle.__module__)
