from typing import Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from datetime import date, datetime, timedelta
import peewee

import config
from config import ID_GIOCHINI as CHAT_ID, Punteggio, Punti, Medaglia
from games import ALL_GAMES as GAMES, get_day_from_date
from utils import (
    daily_ranking,
    get_bonus_game,
    pick_or_get_bonus_game,
    process_tries,
    Classifica,
    Giocata,
    GiocoBonus,
    PuntiBonus,
)


app = FastAPI(title="Giochini API", version="2.0.0")

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

games = dict()
for k, v in GAMES.items():
    games[k.lower()] = v


def get_game_leaderboard(target_date: date, game_name: str) -> dict:
    """Calculates ranks, stars, and formatted scores for a game on target_date."""
    game_info = GAMES.get(game_name, {})
    if not game_info:
        return None

    game_day = get_day_from_date(game_info["date"], game_info["day"], game_name, target_date)
    str_day = str(game_day)

    # Bonus / Jolly game
    bonus_entry = None
    if getattr(config, "BONUS_GAME_ENABLED", True):
        if target_date == date.today():
            bonus_entry = get_bonus_game(target_date) or pick_or_get_bonus_game(target_date)
        else:
            bonus_entry = get_bonus_game(target_date)

    is_jolly = bonus_entry is not None and game_name == bonus_entry.game
    multiplier = bonus_entry.multiplier if is_jolly else 1

    try:
        Punteggio.create_table(safe=True)
        query = (
            Punteggio.select(Punteggio.user_name, Punteggio.user_id, Punteggio.tries, Punteggio.extra, Punteggio.lost)
            .where(
                (Punteggio.day == str_day) | (Punteggio.day == game_day),
                Punteggio.game == game_name,
            )
        )
        if CHAT_ID != 0:
            query = query.where(Punteggio.chat_id == CHAT_ID)
        query = query.order_by(Punteggio.tries, Punteggio.extra.cast('INTEGER').desc(), Punteggio.timestamp)

        giocate_list = list(query)
    except Exception as e:
        giocate_list = []

    posizioni = []
    if giocate_list:
        cl = Classifica()
        cl.game = game_name
        cl.day = str_day
        cl.date = target_date
        cl.emoji = game_info.get("emoji", "🎮")
        cl.giocate = [
            Giocata(
                user_id=g.user_id,
                user_name=g.user_name,
                tries=g.tries,
                game=game_name,
                extra=g.extra if g.extra else 0,
            )
            for g in giocate_list
        ]
        cl.order_and_position()
        cl.assign_stars("default", multiplier=multiplier)

        for g in cl.giocate:
            formatted = process_tries(game_name, g.tries)
            is_lost = bool(g.lost or str(g.tries) in ["9999999", "9999999.0"] or str(formatted) in ["9999999", "N/A"])
            if is_lost:
                formatted = "N/A"
            posizioni.append({
                "user_name": g.user_name,
                "user_id": g.user_id,
                "pos": g.posizione,
                "stars": g.stelle,
                "tries": g.tries,
                "tries_formatted": str(formatted) if formatted is not None else "N/A",
                "lost": is_lost,
                "extra": g.extra,
            })

    return {
        "game": game_name,
        "emoji": game_info.get("emoji", "🎮"),
        "category": game_info.get("category", "other"),
        "url": game_info.get("url", ""),
        "date": target_date.strftime("%Y-%m-%d"),
        "game_day": str_day,
        "is_jolly": is_jolly,
        "multiplier": multiplier,
        "total_players": len(posizioni),
        "posizioni": posizioni,
    }


@app.get("/games/")
@app.get("/games")
@app.get("/api/games/")
@app.get("/giochini-list/")
async def list_available_games():
    """Returns directory of all tracked games."""
    result = []
    for k, v in GAMES.items():
        result.append({
            "name": k,
            "emoji": v.get("emoji", "🎮"),
            "category": v.get("category", "other"),
            "url": v.get("url", ""),
            "disabled": v.get("disabled", False),
        })
    return result


@app.get("/giochini/")
@app.get("/api/giochini/")
async def return_info(game_name: str | None = 'all'):
    if game_name == 'all' or not game_name:
        games_list = []
        for _, v in GAMES.items():
            games_list.append(v)
        return games_list

    games_dict = {k.lower(): v for k, v in GAMES.items()}
    return games_dict.get(game_name.lower(), {"error": "game not found"})


@app.get("/classifica/")
@app.get("/api/classifica/")
async def classifica(day: str | None = None, game: str | None = 'all'):
    """Returns game leaderboards for the given date. Always returns a list."""
    if not day:
        target_date = date.today()
    else:
        try:
            target_date = datetime.strptime(day, "%Y-%m-%d").date()
        except Exception:
            target_date = date.today()

    if game and game.lower() != 'all':
        matched_game = None
        for k in GAMES.keys():
            if k.lower() == game.lower():
                matched_game = k
                break
        if not matched_game:
            return []
        data = get_game_leaderboard(target_date, matched_game)
        return [data] if data else []
    else:
        results = []
        for g_name, g_info in GAMES.items():
            if g_info.get("disabled", False):
                continue
            data = get_game_leaderboard(target_date, g_name)
            if data:
                results.append(data)
        return results


@app.get("/dailyranking/")
@app.get("/api/dailyranking/")
async def dailyranking(day: str | None = None, model: str = "default"):
    """Returns total daily points ranking."""
    today = date.today()
    if not day:
        dates = today
    else:
        try:
            dates = datetime.strptime(day, '%Y-%m-%d').date()
        except Exception:
            dates = today

    try:
        classifica_stelle = daily_ranking(model, dates)
    except Exception as e:
        classifica_stelle = []

    rankings = []
    for position, user_id, user_name, stelle, *rest in classifica_stelle:
        bonus = rest[0] if rest else 0
        rankings.append({
            'name': user_name,
            'user_id': user_id,
            'points': int(stelle),
            'pos': position,
            'bonus': bonus,
        })

    if getattr(config, "BONUS_GAME_ENABLED", True):
        if dates == today:
            bonus = get_bonus_game(dates) or pick_or_get_bonus_game(dates)
        else:
            bonus = get_bonus_game(dates)
    else:
        bonus = None

    bonus_data = None
    if bonus:
        g_info = GAMES.get(bonus.game, {})
        bonus_data = {
            'game': bonus.game,
            'multiplier': bonus.multiplier,
            'emoji': g_info.get("emoji", "🎮"),
            'url': g_info.get("url", ""),
        }

    return {
        'date': dates.strftime("%Y-%m-%d"),
        'rankings': rankings,
        'bonus_game': bonus_data,
        'total_participants': len(rankings),
    }


@app.get("/algorithm-comparison/")
@app.get("/api/algorithm-comparison/")
async def algorithm_comparison(day: str | None = None):
    """Compares the default daily ranking against various alternative scoring models."""
    today = date.today()
    if not day:
        dates = today
    else:
        try:
            dates = datetime.strptime(day, '%Y-%m-%d').date()
        except Exception:
            dates = today

    # 1. Default ranking
    try:
        raw_default = daily_ranking("default", dates)
    except Exception:
        raw_default = []

    default_rankings = []
    default_map = {}
    for pos, uid, name, pts, *rest in raw_default:
        bonus = rest[0] if rest else 0
        p_obj = {
            "name": name,
            "user_id": uid,
            "pos": pos,
            "points": int(pts),
            "bonus": bonus,
        }
        default_rankings.append(p_obj)
        default_map[name] = {"pos": pos, "points": int(pts)}
        default_map[uid] = {"pos": pos, "points": int(pts)}

    models_config = [
        {
            "id": "no-single-point-games",
            "title": "No Single-Point Games",
            "badge": "Anti-Farming",
            "description": "0 punti per partite con 1 solo giocatore: se nessuno ha rivaleggiato, le stelle non vengono assegnate.",
        },
        {
            "id": "no_limit_with_lost",
            "title": "No Limit with Lost",
            "badge": "Stack Punti",
            "description": "Punti = totale partecipanti (inclusi persi) meno posizione + 1. Ogni giocata persa alza il montepremi.",
        },
        {
            "id": "alternate-with-lost",
            "title": "Alternate with Lost",
            "badge": "Cap a 3",
            "description": "Progressivo fino a 3 punti max (3, 2, 1), conteggiando anche i giocatori che hanno perso nel pool.",
        },
        {
            "id": "standard",
            "title": "Standard Classico (3-2-1)",
            "badge": "Fisso Podio",
            "description": "3 punti al 1°, 2 al 2°, 1 al 3° fisso per ogni gioco, a prescindere dal numero di partecipanti.",
        },
        {
            "id": "alternate",
            "title": "Alternate (Solo Validi)",
            "badge": "No Persi",
            "description": "Progressivo fino a 3 punti (3, 2, 1) conteggiando solo ed esclusivamente le partite vinte/valide.",
        },
    ]

    comparisons = []
    for m in models_config:
        try:
            raw_alt = daily_ranking(m["id"], dates)
        except Exception:
            raw_alt = []

        alt_players = []
        seen_names = set()
        seen_uids = set()

        for pos, uid, name, pts, *rest in raw_alt:
            ref = default_map.get(name) or default_map.get(uid)
            ref_pos = ref["pos"] if ref else None
            ref_pts = ref["points"] if ref else 0

            int_pts = int(pts)
            diff_pts = int_pts - ref_pts
            diff_pos = (ref_pos - pos) if ref_pos is not None else 0

            alt_players.append({
                "name": name,
                "user_id": uid,
                "pos": pos,
                "points": int_pts,
                "ref_pos": ref_pos,
                "ref_points": ref_pts,
                "diff_points": diff_pts,
                "diff_pos": diff_pos,
            })
            seen_names.add(name)
            seen_uids.add(uid)

        fallback_pos = (max([p["pos"] for p in alt_players], default=0)) + 1
        for p_def in default_rankings:
            if p_def["name"] not in seen_names and p_def["user_id"] not in seen_uids:
                alt_players.append({
                    "name": p_def["name"],
                    "user_id": p_def["user_id"],
                    "pos": fallback_pos,
                    "points": 0,
                    "ref_pos": p_def["pos"],
                    "ref_points": p_def["points"],
                    "diff_points": -p_def["points"],
                    "diff_pos": p_def["pos"] - fallback_pos,
                })

        comparisons.append({
            "model_id": m["id"],
            "title": m["title"],
            "badge": m["badge"],
            "description": m["description"],
            "rankings": alt_players,
        })

    return {
        "date": dates.strftime("%Y-%m-%d"),
        "default_ranking": default_rankings,
        "comparisons": comparisons,
    }


@app.get("/monthlyranking/")
@app.get("/api/monthlyranking/")
async def monthlyranking(month: str | None = None):
    """Returns monthly points ranking from Punti table."""
    today = date.today()
    if month:
        try:
            start_date = datetime.strptime(f"{month}-01", "%Y-%m-%d").date()
        except Exception:
            start_date = today.replace(day=1)
    else:
        start_date = today.replace(day=1)

    next_month = (start_date.replace(day=28) + timedelta(days=4)).replace(day=1)
    end_date = next_month - timedelta(days=1)

    try:
        Punti.create_table(safe=True)
        query = (
            Punti.select(Punti.user_id, Punti.user_name, peewee.fn.SUM(Punti.punti).alias("totale"))
            .where(Punti.date >= start_date, Punti.date <= end_date)
            .group_by(Punti.user_id)
            .order_by(peewee.fn.SUM(Punti.punti).desc())
        )
        rankings = []
        for i, q in enumerate(query):
            rankings.append({
                "pos": i + 1,
                "user_id": q.user_id,
                "name": q.user_name,
                "points": int(q.totale or 0),
            })
        return {
            "month": start_date.strftime("%Y-%m"),
            "month_name": start_date.strftime("%B %Y"),
            "rankings": rankings,
        }
    except Exception as e:
        return {"month": start_date.strftime("%Y-%m"), "rankings": [], "error": str(e)}


@app.get("/alltimeranking/")
@app.get("/api/alltimeranking/")
async def alltimeranking():
    """Returns all-time points ranking from Punti table."""
    try:
        Punti.create_table(safe=True)
        query = (
            Punti.select(Punti.user_id, Punti.user_name, peewee.fn.SUM(Punti.punti).alias("totale"))
            .group_by(Punti.user_id)
            .order_by(peewee.fn.SUM(Punti.punti).desc())
        )
        rankings = []
        for i, q in enumerate(query):
            rankings.append({
                "pos": i + 1,
                "user_id": q.user_id,
                "name": q.user_name,
                "points": int(q.totale or 0),
            })
        return {"rankings": rankings}
    except Exception as e:
        return {"rankings": [], "error": str(e)}


@app.get("/medals/")
@app.get("/api/medals/")
async def get_medals(month: str | None = None, all_time: bool = False):
    """Returns medals leaderboard (Gold, Silver, Bronze, Poop)."""
    try:
        Medaglia.create_table(safe=True)
        query = Medaglia.select(
            Medaglia.user_name,
            Medaglia.user_id,
            peewee.fn.SUM(Medaglia.gold).alias("gold"),
            peewee.fn.SUM(Medaglia.silver).alias("silver"),
            peewee.fn.SUM(Medaglia.bronze).alias("bronze"),
            peewee.fn.SUM(Medaglia.last).alias("last"),
        )
        today = date.today()
        period_label = "All Time" if all_time else today.strftime("%B %Y")
        if not all_time:
            if month:
                try:
                    start_date = datetime.strptime(f"{month}-01", "%Y-%m-%d").date()
                except Exception:
                    start_date = today.replace(day=1)
            else:
                start_date = today.replace(day=1)
            next_m = (start_date.replace(day=28) + timedelta(days=4)).replace(day=1)
            end_date = next_m - timedelta(days=1)
            period_label = start_date.strftime("%B %Y")
            query = query.where(Medaglia.date >= start_date, Medaglia.date <= end_date)

        query = query.group_by(Medaglia.user_id)
        results = []
        for row in query:
            g = int(row.gold or 0)
            s = int(row.silver or 0)
            b = int(row.bronze or 0)
            l = int(row.last or 0)
            score = g * 3 + s * 2 + b * 1
            results.append({
                "user_name": row.user_name,
                "user_id": row.user_id,
                "gold": g,
                "silver": s,
                "bronze": b,
                "last": l,
                "total_medals": g + s + b,
                "medal_score": score,
            })
        results.sort(key=lambda x: (x["gold"], x["silver"], x["bronze"], -x["last"]), reverse=True)
        for i, r in enumerate(results):
            r["pos"] = i + 1
        return {"period": period_label, "medals": results}
    except Exception as e:
        return {"period": "N/A", "medals": [], "error": str(e)}


@app.get("/jolly/")
@app.get("/api/jolly/")
async def api_jolly(day: str | None = None):
    """Returns the bonus game for the given date."""
    try:
        today = date.today()
        target_date = datetime.strptime(day, "%Y-%m-%d").date() if day else today
        if target_date == today:
            bonus = get_bonus_game(target_date) or pick_or_get_bonus_game(target_date)
        else:
            bonus = get_bonus_game(target_date)

        if not bonus:
            return {"active": False, "bonus": None}

        g_info = GAMES.get(bonus.game, {})
        return {
            "active": True,
            "bonus": {
                "date": target_date.strftime("%Y-%m-%d"),
                "game": bonus.game,
                "multiplier": bonus.multiplier,
                "emoji": g_info.get("emoji", "🎮"),
                "url": g_info.get("url", ""),
            }
        }
    except Exception as e:
        return {"active": False, "error": str(e)}


@app.get("/players/")
@app.get("/api/players/")
async def list_players():
    """Lists distinct active players with play counts."""
    try:
        Punteggio.create_table(safe=True)
        query = (
            Punteggio.select(Punteggio.user_name, peewee.fn.COUNT(Punteggio.game).alias("count"))
            .group_by(Punteggio.user_name)
            .order_by(peewee.fn.COUNT(Punteggio.game).desc())
        )
        players = [{"name": r.user_name, "plays": r.count} for r in query if r.user_name]
        return {"players": players}
    except Exception as e:
        return {"players": [], "error": str(e)}


@app.get("/stats/")
@app.get("/api/stats/")
async def stats(player: str | None = 'all'):
    """Detailed personal stats for a player."""
    if not player or player == 'all':
        return {"error": "player not specified"}

    try:
        Punteggio.create_table(safe=True)
        total_plays = Punteggio.select(peewee.fn.COUNT(Punteggio.game).alias("c")).where(Punteggio.user_name == player).scalar() or 0
        if not total_plays:
            return {
                "player": player,
                "total_plays": 0,
                "total_time_minutes": 0,
                "total_loses": 0,
                "win_rate": 0,
                "long_streak_game": "N/A",
                "long_streak_days": 0,
                "most_played_game": "N/A",
                "most_played_count": 0,
                "least_played_game": "N/A",
                "least_played_count": 0,
                "total_points": 0,
                "medals": {"gold": 0, "silver": 0, "bronze": 0, "last": 0},
            }

        long_streak_query = (
            Punteggio.select(peewee.fn.MAX(Punteggio.streak).alias("streak"), Punteggio.game)
            .where(Punteggio.user_name == player)
            .group_by(Punteggio.game)
            .order_by(peewee.fn.MAX(Punteggio.streak).desc())
            .limit(1)
        )
        long_streak = long_streak_query[0].streak if long_streak_query else 0
        long_streak_game = long_streak_query[0].game if long_streak_query else "N/A"

        most_played_query = (
            Punteggio.select(Punteggio.game, peewee.fn.COUNT(Punteggio.game).alias("c"))
            .where(Punteggio.user_name == player)
            .group_by(Punteggio.game)
            .order_by(peewee.fn.COUNT(Punteggio.game).desc())
            .limit(1)
        )
        most_played = most_played_query[0].game if most_played_query else "N/A"
        most_played_count = most_played_query[0].c if most_played_query else 0

        least_played_query = (
            Punteggio.select(Punteggio.game, peewee.fn.COUNT(Punteggio.game).alias("c"))
            .where(Punteggio.user_name == player)
            .group_by(Punteggio.game)
            .order_by(peewee.fn.COUNT(Punteggio.game).asc())
            .limit(1)
        )
        least_played = least_played_query[0].game if least_played_query else "N/A"
        least_played_count = least_played_query[0].c if least_played_query else 0

        total_time_minutes = total_plays * 2
        total_loses = Punteggio.select(peewee.fn.COUNT(Punteggio.game).alias("c")).where(
            Punteggio.user_name == player,
            Punteggio.lost == True,
        ).scalar() or 0

        win_rate = round(((total_plays - total_loses) / total_plays) * 100, 1) if total_plays > 0 else 0

        # Points
        try:
            Punti.create_table(safe=True)
            total_points = Punti.select(peewee.fn.SUM(Punti.punti)).where(Punti.user_name == player).scalar() or 0
        except Exception:
            total_points = 0

        # Medals
        try:
            Medaglia.create_table(safe=True)
            med_row = Medaglia.select(
                peewee.fn.SUM(Medaglia.gold).alias("g"),
                peewee.fn.SUM(Medaglia.silver).alias("s"),
                peewee.fn.SUM(Medaglia.bronze).alias("b"),
                peewee.fn.SUM(Medaglia.last).alias("l"),
            ).where(Medaglia.user_name == player).first()
            medals = {
                "gold": int(med_row.g or 0) if med_row else 0,
                "silver": int(med_row.s or 0) if med_row else 0,
                "bronze": int(med_row.b or 0) if med_row else 0,
                "last": int(med_row.l or 0) if med_row else 0,
            }
        except Exception:
            medals = {"gold": 0, "silver": 0, "bronze": 0, "last": 0}

        return {
            "player": player,
            "total_plays": total_plays,
            "total_time_minutes": total_time_minutes,
            "total_loses": total_loses,
            "win_rate": win_rate,
            "long_streak_game": long_streak_game,
            "long_streak_days": long_streak or 0,
            "most_played_game": most_played,
            "most_played_count": most_played_count,
            "least_played_game": least_played,
            "least_played_count": least_played_count,
            "total_points": int(total_points),
            "medals": medals,
        }
    except Exception as e:
        return {"player": player, "error": str(e)}


@app.get("/game-stats/")
@app.get("/api/game-stats/")
async def get_game_stats(player: Optional[str] = None, game: Optional[str] = None):
    """Retrieve activity count per day for the last 365 days."""
    try:
        one_year_ago = datetime.now() - timedelta(days=365)
        Punteggio.create_table(safe=True)
        query = (
            Punteggio
            .select(
                Punteggio.date,
                peewee.fn.COUNT(peewee.fn.DISTINCT(Punteggio.timestamp)).alias('game_count')
            )
            .where(Punteggio.date >= one_year_ago)
        )

        if player:
            query = query.where(Punteggio.user_name == player)
        if game:
            query = query.where(Punteggio.game == game)

        query = query.group_by(Punteggio.date).order_by(Punteggio.date)

        stats_list = [
            {"day": row.date.strftime("%Y-%m-%d") if isinstance(row.date, (date, datetime)) else str(row.date), "game_count": row.game_count}
            for row in query
        ]

        return {
            "total_stats": stats_list,
            "total_games": sum(stat['game_count'] for stat in stats_list),
            "date_range": {
                "start": one_year_ago.date().isoformat(),
                "end": datetime.now().date().isoformat(),
            }
        }
    except Exception as e:
        return {
            "total_stats": [],
            "total_games": 0,
            "error": str(e),
            "date_range": {
                "start": (datetime.now() - timedelta(days=365)).date().isoformat(),
                "end": datetime.now().date().isoformat(),
            }
        }


# Direct web shortcuts
@app.get("/", include_in_schema=False)
async def serve_root():
    return FileResponse("www/html/trifase.online/giochini/index.html")

@app.get("/giochini", include_in_schema=False)
@app.get("/giochini/", include_in_schema=False)
async def serve_giochini_root():
    return FileResponse("www/html/trifase.online/giochini/index.html")

@app.get("/giochini/players.html", include_in_schema=False)
async def serve_players_page():
    return FileResponse("www/html/trifase.online/giochini/players.html")


# Mount static files under root path
app.mount("/", StaticFiles(directory="www/html/trifase.online", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main_fastapi:app", host="0.0.0.0", port=8000, reload=False)

