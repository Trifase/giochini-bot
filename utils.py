import datetime
from collections import defaultdict

import httpx
import peewee
import timedelta

from dataclassy import dataclass
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from config import ID_GIOCHINI, MEDALS, TOKEN, Medaglia, Punteggio
from games import ALL_GAMES as GAMES
from games import get_day_from_date



@dataclass
class Giocata:
    user_id: int
    user_name: str
    game: str

    tries: int
    extra: int = 0

    posizione: int = 0
    stelle: int = 0

    @property
    def emoji(self) -> str:
        if self.posizione == 1:
            return "🥇 "
        if self.posizione == 2:
            return "🥈 "
        if self.posizione == 3:
            return "🥉 "
        return ""

    @property
    def processed_tries(self) -> str:
        return process_tries(self.game, self.tries)
    # lost is true if tries is 9999999
    @property
    def lost(self) -> bool:
        return self.tries == 9999999 or self.tries == "9999999"
    
    def to_string(self, aggregate=False):
        if self.lost:
            return f"<s><i>{self.user_name}</i></s>"
        else:
            if aggregate:
                return f"{self.emoji}{self.user_name} ({self.stelle}🔸)"
            else:
                stelle = f"{self.stelle}✮ " if self.stelle > 0 else ""
                return f"{self.emoji}{stelle}{self.user_name} ({self.processed_tries})"




@dataclass
class Classifica:
    game: str = ""
    day: str = ""
    date: datetime.date = None
    emoji: str = ""

    giocate: list[Giocata] = []
    aggregate: bool = False

    valid: bool = True
    header: str = ""
    last: str = ""

    def order_and_position(self):
        # Ordina per tries (crescente) e poi per extra (decrescente)
        sorted_giocate = sorted(
            [g for g in self.giocate if not g.lost],
            key=lambda g: (g.tries, -int(g.extra))
        )
        
        last_tries = None
        last_extra = None
        posizione_corrente = 0
        
        for i, g in enumerate(sorted_giocate):
            if g.tries == last_tries and g.extra == last_extra:
                pass
            else:
                posizione_corrente = i + 1
            
            g.posizione = posizione_corrente
            
            last_tries = g.tries
            last_extra = g.extra
        
        lost_giocate = [g for g in self.giocate if g.lost]
        self.giocate = sorted_giocate + lost_giocate

    def assign_stars(self, model: str = 'no_limit_with_lost'):
        scoring_models = {
            "standard": self._score_standard,
            "alternate": self._score_alternate,
            "alternate-with-lost": self._score_alternate_with_lost,
            "no_limit_with_lost": self._score_no_limit_with_lost,
        }
        
        scoring_function = scoring_models.get(model)
        # for gioc in self.giocate:
        #     print(gioc.user_name, gioc.tries, gioc.extra)
        if scoring_function:
            scoring_function()
        else:
            raise ValueError(f"Modello di scoring '{model}' non valido.")

    def _score_standard(self):
        stelle_assegnate = {1: 3, 2: 2, 3: 1}
        for g in self.giocate:
            g.stelle = stelle_assegnate.get(g.posizione, 0)

    def _score_alternate(self):
        valid_players = [g for g in self.giocate if not g.lost]
        num_players = len(valid_players)
        
        for g in valid_players:
            g.stelle = max(0, min(3, num_players - g.posizione + 1))
        
        for g in self.giocate:
            if g.lost:
                g.stelle = 0

    def _score_alternate_with_lost(self):
        valid_players = [g for g in self.giocate if not g.lost]
        num_players_with_lost = len(self.giocate)
        
        for g in valid_players:
            g.stelle = max(0, min(3, num_players_with_lost - g.posizione+ 1))
        
        for g in self.giocate:
            if g.lost:
                g.stelle = 0

    def _score_no_limit_with_lost(self):
        """
        Calcola le stelle per il modello NFLXdle. Il punteggio massimo è basato sul
        numero totale di giocatori (validi e persi).
        """
        # Contiamo il numero totale di giocatori, inclusi quelli persi.
        num_players = len(self.giocate)
        
        # Gruppa i giocatori validi per posizione per gestire il parimerito.
        valid_giocate = [g for g in self.giocate if not g.lost]
        positions = defaultdict(list)
        for g in valid_giocate:
            positions[g.posizione].append(g)
        
        # Assegna le stelle ai giocatori validi.
        for pos, group in positions.items():
            # Il punteggio è `num_players - posizione + 1`.
            stelle_assegnate = max(0, num_players - pos + 1)
            for g in group:
                g.stelle = stelle_assegnate

        # Le giocate perse hanno 0 stelle.
        for g in self.giocate:
            if g.lost:
                g.stelle = 0

    def to_string(self) -> str:
        classifica = ""
        if not self.aggregate:
            classifica += self.header + "\n"

        for posiz in self.giocate:
            classifica += posiz.to_string(self.aggregate) + "\n"

        if self.last and not self.aggregate:
            classifica += f"{self.last}"

        return classifica

    def get_stars(self):
        """
        Restituisce una nuova Classifica contenente solo le stelle per l'aggregazione.
        """
        stars_list = []
        for giocata in self.giocate:
            stars_list.append(Giocata(
                user_id=giocata.user_id,
                user_name=giocata.user_name,
                stelle=giocata.stelle,
                game='Aggregate',
                tries=0,
                extra=0
            ))
        
        return Classifica(
            game="Aggregate",
            day=self.day,
            date=self.date,
            giocate=stars_list,
            aggregate=True
        )

    def __add__(self, other):
        if not isinstance(other, Classifica):
            raise TypeError("Si possono sommare solo oggetti di tipo Classifica.")

        user_stars = defaultdict(lambda: {"user_name": "", "total_stars": 0})
        all_giocate = self.giocate + other.giocate
        
        for giocata in all_giocate:
            user_stars[giocata.user_id]["user_name"] = giocata.user_name
            user_stars[giocata.user_id]["total_stars"] += giocata.stelle

        aggregated_giocate = []
        for user_id, data in user_stars.items():
            aggregated_giocate.append(Giocata(
                user_id=user_id,
                user_name=data["user_name"],
                tries=0, extra=0,
                stelle=data["total_stars"],
                game="Aggregate"
            ))

        aggregated_giocate.sort(key=lambda g: g.stelle, reverse=True)

        # Assegna le posizioni finali, gestendo i parimerito
        last_stelle = None
        posizione_corrente = 0
        for i, g in enumerate(aggregated_giocate):
            if g.stelle == last_stelle:
                pass  # Parimerito: mantiene la stessa posizione
            else:
                posizione_corrente = i + 1
            g.posizione = posizione_corrente
            last_stelle = g.stelle

        return Classifica(
            game="Generale",
            day=f"{self.day} + {other.day}",
            date=datetime.date.today(),
            giocate=aggregated_giocate,
            aggregate=True
        )


# def daily_ranking(model: str = "alternate-with-lost", from_day: datetime.date = None):
#     """Creates the daily ranking for all games."""
#     points = defaultdict(int)
#     today = datetime.date.today()
#     if not from_day:
#         from_day = today

#     # Score Calculation models:

#     # standard: 3 points to the first, 2 points to the second and 1 point to the third, no matter how many plays there are.

#     # skip-empty: same as the standard, but games with less than limit plays (default: 3) are not counted at all

#     # alternate: We give n points to the first, n-1 to the second and so on, where n is the number of players in the game.
#     #   It's still capped at three, so if a game has 7 plays, the first gets 3 points, the second 2 and the third 1, same as standard;
#     #   BUT if a game has only two plays,the first gets only two points, and the second 1. If it has only one play, the winner gets a single point.

#     # alternate-with-lost: same as alternate, but we count lost plays whe we calculate the score. We still don't assign points to lost plays.

#     # no-limit-of-3: same as alternate-with-lost, but we don't limit the number of players to 3. So if a game has 7 plays, the first gets 7 points, the second 6 and so on.

#     # no-timestamp: same as alternate-with-lost, but it doesn't consider the timestamp of the play. Made for people who sleep a lot.

#     # only-gold: 1 point to the first of each game with at least 2 plays

#     # allow-ex-aequo: same as alternate-with-lost, but players with the same score get the same points. So if two players tie for first, they both get n points, and the next player gets n-2 points.

#     # GAMES = get_games()
    
#     for game in GAMES.keys():
#         day = get_day_from_date(GAMES[game]["date"], GAMES[game]["day"], game, from_day)



#         # Score Processing
#         if model == "standard":
#             query = (
#                 Punteggio.select(Punteggio.user_name, Punteggio.user_id)
#                 .where(
#                     Punteggio.day == day,
#                     Punteggio.game == game,
#                     Punteggio.chat_id == ID_GIOCHINI,
#                     Punteggio.lost == False,
#                 )
#                 .order_by(Punteggio.tries, Punteggio.extra.desc(), Punteggio.timestamp)
#                 .limit(3)
#             )
#             for i, _ in enumerate(query):
#                 try:
#                     name = f"{query[i].user_id}_|_{query[i].user_name}"
#                     points[name] += 3 - i
#                 except IndexError:
#                     pass

#         if model == "skip-empty":
#             limit = 3
#             query = (
#                 Punteggio.select(Punteggio.user_name, Punteggio.user_id)
#                 .where(
#                     Punteggio.day == day,
#                     Punteggio.game == game,
#                     Punteggio.chat_id == ID_GIOCHINI,
#                     Punteggio.lost == False,
#                 )
#                 .order_by(Punteggio.tries, Punteggio.extra.desc(), Punteggio.timestamp)
#                 .limit(3)
#             )
#             if len(query) < limit:
#                 continue
#             for i, _ in enumerate(query):
#                 try:
#                     name = f"{query[i].user_id}_|_{query[i].user_name}"
#                     points[name] += 3 - i
#                 except IndexError:
#                     pass

#         if model == "alternate":
#             # This include lost plays, that we filter out when we assign points.
#             query_alternate = (
#                 Punteggio.select(Punteggio.user_name, Punteggio.user_id, Punteggio.lost)
#                 .where(
#                     Punteggio.day == day,
#                     Punteggio.game == game,
#                     Punteggio.chat_id == ID_GIOCHINI,
#                     Punteggio.lost == False,
#                 )
#                 .order_by(Punteggio.tries, Punteggio.extra.desc(), Punteggio.timestamp)
#                 .limit(3)
#             )
#             for i, _ in enumerate(query_alternate):
#                 try:
#                     if not query_alternate[i].lost:
#                         name = f"{query_alternate[i].user_id}_|_{query_alternate[i].user_name}"
#                         points[name] += len(query_alternate) - i
#                 except IndexError:
#                     pass

#         if model == "alternate-with-lost":
#             # This include lost plays
#             query_alternate = (
#                 Punteggio.select(Punteggio.user_name, Punteggio.user_id, Punteggio.lost)
#                 .where(Punteggio.day == day, Punteggio.game == game, Punteggio.chat_id == ID_GIOCHINI)
#                 .order_by(Punteggio.tries, Punteggio.extra.desc(), Punteggio.timestamp)
#                 .limit(3)
#             )
#             for i, _ in enumerate(query_alternate):
#                 # print(f"{game} {i} {query_alternate[i]} {query_alternate[i].lost}")
#                 try:
#                     if not query_alternate[i].lost:
#                         name = f"{query_alternate[i].user_id}_|_{query_alternate[i].user_name}"
#                         points[name] += len(query_alternate) - i
#                 except IndexError:
#                     pass

#         if model == "no-timestamp":
#             # This include lost plays, doesn't consider timestamps
#             query_alternate = (
#                 Punteggio.select(Punteggio.user_name, Punteggio.user_id, Punteggio.lost)
#                 .where(Punteggio.day == day, Punteggio.game == game, Punteggio.chat_id == ID_GIOCHINI)
#                 .order_by(Punteggio.tries, Punteggio.extra.desc())
#                 .limit(3)
#             )
#             for i, _ in enumerate(query_alternate):
#                 try:
#                     if not query_alternate[i].lost:
#                         name = f"{query_alternate[i].user_id}_|_{query_alternate[i].user_name}"
#                         points[name] += len(query_alternate) - i
#                 except IndexError:
#                     pass

#         if model == "no-limit-of-3":
#             # This include lost plays
#             query_alternate = (
#                 Punteggio.select(Punteggio.user_name, Punteggio.user_id, Punteggio.lost)
#                 .where(Punteggio.day == day, Punteggio.game == game, Punteggio.chat_id == ID_GIOCHINI)
#                 .order_by(Punteggio.tries, Punteggio.extra.desc(), Punteggio.timestamp)
#             )
#             for i, _ in enumerate(query_alternate):
#                 # print(f"{game} {i} {query_alternate[i]} {query_alternate[i].lost}")
#                 try:
#                     if not query_alternate[i].lost:
#                         name = f"{query_alternate[i].user_id}_|_{query_alternate[i].user_name}"
#                         points[name] += len(query_alternate) - i
#                 except IndexError:
#                     pass

#         if model == "allow-ex-aequo":
#             prev_tries = None
#             prev_extra = None
#             joint_winners = 0
#             # This include lost plays
#             query_alternate = (
#                 Punteggio.select(Punteggio.user_name, Punteggio.user_id, Punteggio.lost, Punteggio.tries, Punteggio.extra)
#                 .where(Punteggio.day == day, Punteggio.game == game, Punteggio.chat_id == ID_GIOCHINI)
#                 .order_by(Punteggio.tries, Punteggio.extra.desc(), Punteggio.timestamp)
#                 .limit(3)
#             )
#             for i, _ in enumerate(query_alternate):
#                 # print(f"{game} {i} {query_alternate[i]} {query_alternate[i].lost}")
#                 # print(f"prev_tries: {prev_tries}, prev_extra: {prev_extra}, current tries: {query_alternate[i].tries}, current extra: {query_alternate[i].extra}")
#                 try:

#                     if not query_alternate[i].lost:
#                         name = f"{query_alternate[i].user_id}_|_{query_alternate[i].user_name}"
#                         if query_alternate[i].tries == prev_tries and query_alternate[i].extra == prev_extra:
#                             joint_winners += 1
#                             points[name] += len(query_alternate) - i + joint_winners
#                         else:
#                             joint_winners = 0
#                             points[name] += len(query_alternate) - i
#                     prev_tries = query_alternate[i].tries
#                     prev_extra = query_alternate[i].extra
#                 except IndexError:
#                     pass


#     cambiamenti = dict(points)
#     cambiamenti = sorted(cambiamenti.items(), key=lambda x: x[1], reverse=True)
#     return cambiamenti


def daily_ranking(model: str = "no_limit_with_lost", from_day: datetime.date = None):
    """Creates the daily ranking for all games."""
    points = defaultdict(int)
    today = datetime.date.today()
    if not from_day:
        from_day = today

    # Score Calculation models:

    # standard: 3 points to the first, 2 points to the second and 1 point to the third, no matter how many plays there are.

    # skip-empty: same as the standard, but games with less than limit plays (default: 3) are not counted at all

    # alternate: We give n points to the first, n-1 to the second and so on, where n is the number of players in the game.
    #   It's still capped at three, so if a game has 7 plays, the first gets 3 points, the second 2 and the third 1, same as standard;
    #   BUT if a game has only two plays,the first gets only two points, and the second 1. If it has only one play, the winner gets a single point.

    # alternate-with-lost: same as alternate, but we count lost plays whe we calculate the score. We still don't assign points to lost plays.

    # no-limit-of-3: same as alternate-with-lost, but we don't limit the number of players to 3. So if a game has 7 plays, the first gets 7 points, the second 6 and so on.

    # no-timestamp: same as alternate-with-lost, but it doesn't consider the timestamp of the play. Made for people who sleep a lot.

    # only-gold: 1 point to the first of each game with at least 2 plays

    # allow-ex-aequo: same as alternate-with-lost, but players with the same score get the same points. So if two players tie for first, they both get n points, and the next player gets n-2 points.

    # GAMES = get_games()
    
    for game in GAMES.keys():
        day = get_day_from_date(GAMES[game]["date"], GAMES[game]["day"], game, from_day)

        query = (
                Punteggio.select(Punteggio.user_name, Punteggio.user_id, Punteggio.tries, Punteggio.extra, Punteggio.lost)
                .where(Punteggio.day == day, Punteggio.game == game, Punteggio.chat_id == ID_GIOCHINI)
                .order_by(Punteggio.tries, Punteggio.extra.desc(), Punteggio.timestamp)
            )

        model = 'no_limit_with_lost'

        if not query:
            continue

        cl = Classifica()
        cl.game = game
        cl.day = day
        cl.date = from_day
        cl.emoji = GAMES[game]["emoji"]
        cl.giocate = [Giocata(user_id=g.user_id, user_name=g.user_name, tries=g.tries, game=game, extra=g.extra if g.extra else 0) for g in query]
        cl.order_and_position()
        cl.assign_stars(model)

        for clg in cl.giocate:
            name = f"{clg.user_id}_|_{clg.user_name}"
            points[name] += clg.stelle


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


def seconds_to_time(seconds: int) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    string = ''
    if hours > 0:
        string += f"{hours}h "
    if minutes > 0:
        string += f"{minutes}m "
    string += f"{seconds}s"
    return string



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

    # For WhenTaken, scores are points, the more the better. Max points is 1_000 so we save them as differences from max.
    if game == "WhenTaken":
        tries = 1_000 - tries

    # For Picsey, scores are points, the more the better. Max points is 100 so we save them as differences from max.
    if game == "Picsey":
        tries = 100 - tries

    # So, murdle/Queens points are time. I store time (for exampe: 5:12) as an int (512) so I can order them. Here I convert them back to string, putting a semicolon two chars from the end.
    if game in ["Murdle", "Queens", "Tango", "Crossclimb", "Zip"]:
        tries = str(tries)[:-2] + ":" + str(tries)[-2:]
        if len(tries) == 2: # this fixes the bug where the time is '7' and is displayed as '0:7' instead of '0:07'
            tries = ':0' + tries[-1]
        if tries.startswith(':'):
            tries = '0' + tries
    
    if game == 'Snoop': 
        # from 023383 to 02:23.83
        # zfill on the left, so it can be 0:00.00
        tries = str(tries).zfill(6)
        hours = tries[0:2]
        minutes = tries[2:4]
        seconds = tries[4:6]
        tries = f"{hours}:{minutes}.{seconds}"

    # For NerdleCross, scores are points, the more the better. Max points is 6 so we save them as differences from max.
    if game == "NerdleCross":
        tries = 6 - tries

    # For WordGrid, the point is a float with one decimal. I store multiplying by 10 as ints, so i just need to divide by ten and round it to one decimal.
    if game == "WordGrid":
        tries = round(tries / 10, 1)

    # For Reversle, the point is a float with 2 decimals. I store multiplying by 10 as ints, so i just need to divide by 100 an round it to 2 decimals.
    if game == "Reversle":
        tries = f"{round(tries / 100, 2)}s"

    if game == 'Decipher':
        tries = seconds_to_time(tries)

    if game == 'BracketCity':
        tries = round(100 - tries, 1)

    if game == 'Timdle':
        tries = 36 - tries
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


def personal_stats(user_id: int, correct_game=None) -> str:
    if correct_game is not None:
        intro = f"Ecco le tue statistiche personali per {correct_game}:\n\n"
    else:
        intro = "Ecco le tue statistiche personali:\n\n"

    # giocate totali
    if correct_game is not None:
        total_plays = Punteggio.select(peewee.fn.COUNT(Punteggio.game).alias("c")).where(Punteggio.user_id == user_id, Punteggio.game == correct_game).scalar()
    else:
        total_plays = Punteggio.select(peewee.fn.COUNT(Punteggio.game).alias("c")).where(Punteggio.user_id == user_id).scalar()

    if not total_plays:
        return "Non hai mai giocato!"

    # longest streak best game streak
    if correct_game is not None:
        long_streak_query = (
            Punteggio.select(peewee.fn.MAX(Punteggio.streak).alias("streak"), Punteggio.game)
            .where(Punteggio.user_id == user_id, Punteggio.game == correct_game)
            .group_by(Punteggio.game)
            .order_by(Punteggio.streak.desc())
            .limit(1)
        )
        long_streak = long_streak_query[0].streak
        long_streak_string = f"Il tuo streak più lungo è di <b>{long_streak}</b> partite.\n"
    else:
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
    if correct_game is not None:
        most_played_string = ""
    else:
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
    if correct_game is not None:
        least_played_string = ""
    else:
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

    # giocate perse totali
    if correct_game is not None:
        total_loses = (
            Punteggio.select(peewee.fn.COUNT(Punteggio.game).alias("c"))
            .where(
                Punteggio.user_id == user_id,
                Punteggio.lost == True,
                Punteggio.game == correct_game,
            )
            .scalar()
        )
        if total_loses:
            total_loses_string = f"In totale, hai perso <b>{total_loses}</b> partite.\n"
    else:
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
            Medaglia.user_id,
            Medaglia.user_name,
            peewee.fn.SUM(Medaglia.gold).alias("gold"),
            peewee.fn.SUM(Medaglia.silver).alias("silver"),
            peewee.fn.SUM(Medaglia.bronze).alias("bronze"),
        )
        .where(Medaglia.date >= first_of_the_month)
        .group_by(Medaglia.user_id)
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


def sanitize_extra():
    """
    This is used for manual cleaning of something in the db. Manual called sometimes.
    """
    c = 0
    for punt in Punteggio.select().where(Punteggio.extra == "None"):
        c += 1
        punt.extra = None
        punt.save()

def print_heatmap():
    """
    To be completed.
    This charts some graphs about the playtimes. It's a work in progress.
    It's also generate by ChatGPT 4o, so, whatever.
    """

    import matplotlib.pyplot as plt
    import datetime

    # Query the timestamps from the database
    timestamps = [record.timestamp for record in Punteggio.select(Punteggio.timestamp)]

    # Convert Unix timestamps to datetime objects
    datetimes = [datetime.datetime.fromtimestamp(ts) for ts in timestamps]

    # Extract hours and days of the week
    hours = [dt.hour for dt in datetimes]
    days_of_week = [dt.weekday() for dt in datetimes]  # Monday is 0 and Sunday is 6

    # Create a matrix to count occurrences using nested lists
    heatmap_data = [[0 for _ in range(24)] for _ in range(7)]

    for day, hour in zip(days_of_week, hours):
        heatmap_data[day][hour] += 1

    # Rearrange heatmap data to start at 4 AM and end at 3 AM
    heatmap_data_reordered = [day[4:] + day[:4] for day in heatmap_data]
    hours_reordered = list(range(4, 24)) + list(range(0, 4))

    # Calculate average counts per day and hour
    avg_counts_per_day = [sum(day) / 24 for day in heatmap_data]
    avg_counts_per_hour = [sum(hour[i] for hour in heatmap_data) / 7 for i in range(24)]
    avg_counts_per_hour_reordered = avg_counts_per_hour[4:] + avg_counts_per_hour[:4]

    fig = plt.figure(figsize=(18, 12))

    # Plot the heatmap
    ax1 = fig.add_subplot(2, 1, 1)
    cax = ax1.matshow(heatmap_data_reordered, cmap='viridis')
    ax1.set_xticks(range(24))
    ax1.set_yticks(range(7))
    ax1.set_xticklabels([f'{i}:00' for i in hours_reordered])
    ax1.set_yticklabels(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'])
    ax1.set_xlabel('Hour of the Day')
    ax1.set_ylabel('Day of the Week')
    ax1.set_title('Heatmap of Timestamps')
    ax1.tick_params(axis='x', rotation=45)

    # Create a new subplot to split the space equally between the two average count plots
    ax2 = fig.add_subplot(2, 2, 3)
    ax3 = fig.add_subplot(2, 2, 4)

    # Create and plot average counts per day of the week
    ax2.bar(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'], avg_counts_per_day, color='blue')
    ax2.set_xlabel('Day of the Week')
    ax2.set_ylabel('Average Count')
    ax2.set_title('Average Count per Day of the Week')

    # Create and plot average counts per hour of the day
    ax3.plot(range(24), avg_counts_per_hour_reordered, color='blue')
    ax3.set_xlabel('Hour of the Day')
    ax3.set_ylabel('Average Count')
    ax3.set_title('Average Count per Hour of the Day')
    ax3.set_xticks(range(24))
    ax3.set_xticklabels([f'{i}:00' for i in hours_reordered])
    ax3.tick_params(axis='x', rotation=45)

    plt.tight_layout()
    plt.savefig('00_combined_plot.png')

def get_all_scoring():
    # We will get all the daily ranking for every day using a specific model, from today all the way back.
    # We will also get the highest scoring ever
    import datetime

    today = datetime.date.today()
    max_points = 0
    max_user = 0
    max_date = today
    model = "alternate-with-lost"
    for day in range(0, 365): 
        date = today - datetime.timedelta(days=day)
        # Get the scores for this day
        cambiamenti = daily_ranking(model, from_day=date)
        for user, points in cambiamenti:
            user_id, user_name = user.split("_|_")
            user_id = int(user_id)
            if points > max_points:
                print(f'new highscore found! {user_name} with {points} points on {date}')
                max_points = points
                max_user = user_name
                max_date = date
    print(f"Highest scoring ever: {max_user} ({max_points}) on {max_date}.")



# Heatmap!
if __name__ == '__main__':
    print_heatmap()
    # get_all_scoring()

# sanitize_extra()