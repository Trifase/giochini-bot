from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import date
from config import ID_GIOCHINI as CHAT_ID
from games import ALL_GAMES as GAMES
from config import Punteggio
import peewee
import timedelta


app = FastAPI()

origins = ["*"]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

games = dict()
for k,v in GAMES.items():
    games[k.lower()] = v

async def classifica_for_game(day, game_name) -> list:
    klassifica = []
    query = (
        Punteggio.select(Punteggio.user_name, Punteggio.tries, Punteggio.user_id, Punteggio.lost, Punteggio.extra, Punteggio.lost)
        .where(
            Punteggio.date == day,
            Punteggio.game == game_name,
            Punteggio.chat_id == CHAT_ID,
            Punteggio.lost == False,
        )
        .order_by(Punteggio.tries, Punteggio.extra.desc(), Punteggio.timestamp)
        .limit(10)
    )
    for p in list(query):
        klassifica.append({
            'user_name': p.user_name,
            'tries': p.tries,
            'extra': p.extra,
            'lost': p.lost
        })
    return klassifica


@app.get("/giochini/")
async def return_info(game_name: str | None = 'all'):
    if game_name == 'all':
        games = []
        for _,v in GAMES.items():
            games.append(v)
        return games

    games = dict()
    for k,v in GAMES.items():
        games[k.lower()] = v
    return games.get(game_name.lower(), {"error": "game not found"})

@app.get("/classifica/")
async def classifica(day: str | None = None, game: str | None = 'all'):
    return_list = []
    if not day:
        # new datetime in format yyyy-mm-dd with today date
        day = date.today().strftime("%Y-%m-%d")
    if game == 'all':
        for k,v in games.items():
            return_obj = dict()
            return_obj['game'] = v['game']
            return_obj['date'] = day
            return_obj['emoji'] = v['emoji']
            return_obj['category'] = v['category']
            return_obj['posizioni'] = await classifica_for_game(day, v['game'])
            return_list.append(return_obj)
        return return_list
    else:
        if game.lower() in games.keys():
            return_obj = dict()
            g = games[game.lower()]
            game_name = g['game']
            classifica = await classifica_for_game(day, game_name)
            return_obj['game'] = game_name
            return_obj['date'] = day
            return_obj['category'] = g['category']
            return_obj['posizioni'] = classifica
            return_list.append(return_obj)
            return return_obj
        else:
            return {"error": "game not found"}


@app.get("/stats/")
async def stats(player: str | None = 'all'):
    if not player:
        return {"error": "player not found"}
    return_obj = {}
    total_plays = Punteggio.select(peewee.fn.COUNT(Punteggio.game).alias("c")).where(Punteggio.user_name == player).scalar()
    
    long_streak_query = (
        Punteggio.select(peewee.fn.MAX(Punteggio.streak).alias("streak"), Punteggio.game)
        .where(Punteggio.user_name == player)
        .group_by(Punteggio.game)
        .order_by(Punteggio.streak.desc())
        .limit(1)
    )
    long_streak = long_streak_query[0].streak
    long_streak_game = long_streak_query[0].game
    long_streak_string = f"Il tuo streak più lungo è di <b>{long_streak}</b> partite a <b>{long_streak_game}.</b>\n"

    most_played_query = (
        Punteggio.select(Punteggio.game, peewee.fn.COUNT(Punteggio.game).alias("c"))
        .where(Punteggio.user_name == player)
        .group_by(Punteggio.game)
        .order_by(peewee.fn.COUNT(Punteggio.game).desc())
        .limit(1)
    )
    most_played = most_played_query[0].game
    most_played_count = most_played_query[0].c
    most_played_string = f"Il gioco a cui hai giocato di più è <b>{most_played}</b> con <b>{most_played_count}</b> partite!\n"

    least_played_query = (
        Punteggio.select(Punteggio.game, peewee.fn.COUNT(Punteggio.game).alias("c"))
        .where(Punteggio.user_name == player)
        .group_by(Punteggio.game)
        .order_by(peewee.fn.COUNT(Punteggio.game).asc())
        .limit(1)
    )
    least_played = least_played_query[0].game
    least_played_count = least_played_query[0].c
    least_played_string = f"Il gioco che ti piace di meno è <b>{least_played}</b>, hai giocato solo <b>{least_played_count}</b> partite...\n\n"

    # tempo perso a giocare (considerando 2min a giocata), in DD:HH:MM
    single_play_minutes = 2
    total_time = total_plays * single_play_minutes
    td = timedelta.Timedelta(minutes=total_time)
    time_string = ''
    if td.total.days > 0:
        time_string += f"{td.total.days} giorni, "
    if td.total.hours > 0:
        time_string += f"{td.total.hours % 24} ore e "
    time_string += f"{td.total.minutes % 60} minuti"
    total_plays_string = f"In totale hai fatto <b>{total_plays}</b> partite.\nA 2 minuti a partita, hai sprecato <b>{time_string}</b> della tua vita.\n"

    total_loses = (
        Punteggio.select(peewee.fn.COUNT(Punteggio.game).alias("c"))
        .where(
            Punteggio.user_name == player,
            Punteggio.lost == True,
        )
        .scalar()
    )
    if total_loses:
        total_loses_string = f"In totale, hai perso <b>{total_loses}</b> partite.\n"
    else:
        total_loses = 0

    return_obj['player'] = player
    return_obj['long_streak_game'] = long_streak_game
    return_obj['long_streak_days'] = long_streak
    return_obj['most_played_game'] = most_played
    return_obj['most_played_count'] = most_played_count
    return_obj['least_played_game'] = least_played
    return_obj['least_played_count'] = least_played_count
    return_obj['total_plays'] = total_plays
    return_obj['total_time_minutes'] = total_time
    return_obj['total_loses'] = total_loses

    return return_obj