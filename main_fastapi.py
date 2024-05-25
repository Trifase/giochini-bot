from fastapi import FastAPI
from datetime import date
from config import ID_GIOCHINI as CHAT_ID
from games import ALL_GAMES as GAMES
from config import Punteggio


app = FastAPI()

games = dict()
for k,v in GAMES.items():
    games[k.lower()] = v

async def classifica_for_game(day, game_name) -> list:
    klassifica = []
    query = (
        Punteggio.select(Punteggio.user_name, Punteggio.tries, Punteggio.user_id, Punteggio.lost, Punteggio.extra)
        .where(
            Punteggio.date == day,
            Punteggio.game == game_name,
            Punteggio.chat_id == CHAT_ID
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