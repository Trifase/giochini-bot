import datetime
import peewee
import pytest

from config import Punteggio, Medaglia, ID_GIOCHINI
from utils import (
    PuntiBonus,
    GameStatus,
    GiocoBonus,
    daily_ranking,
    medaglie_count,
    personal_stats,
    POOP_MEDAL,
    get_active_games,
    choose_bonus_multiplier,
    get_bonus_game,
    pick_or_get_bonus_game,
)


@pytest.fixture(autouse=True)
def setup_test_db():
    # Setup test tables
    test_db = peewee.SqliteDatabase(":memory:")
    models = [Punteggio, Medaglia, PuntiBonus, GiocoBonus, GameStatus]
    test_db.bind(models, bind_refs=False, bind_backrefs=False)
    test_db.connect()
    test_db.create_tables(models)
    yield
    test_db.drop_tables(models)
    test_db.close()


def test_punti_bonus_model():
    today = datetime.date.today()
    PuntiBonus.create(
        date=today,
        user_id=123,
        user_name="Mario",
        punti=2,
        reason="Premio quiz",
        assigned_by=999,
        timestamp=1000,
    )
    PuntiBonus.create(
        date=today,
        user_id=123,
        user_name="Mario",
        punti=1,
        reason="Altro bonus",
        assigned_by=999,
        timestamp=1001,
    )

    bonuses = list(PuntiBonus.select().where(PuntiBonus.user_id == 123))
    assert len(bonuses) == 2
    assert sum(b.punti for b in bonuses) == 3


def test_daily_ranking_with_bonus_and_floor():
    today = datetime.date.today()

    # User 1 has a game play
    Punteggio.create(
        date=today,
        timestamp=100,
        chat_id=ID_GIOCHINI,
        user_id=1,
        user_name="Alice",
        game="Wordle",
        day="100",
        tries=3,
        extra=None,
        streak=1,
        lost=False,
    )

    # User 2 has a game play
    Punteggio.create(
        date=today,
        timestamp=101,
        chat_id=ID_GIOCHINI,
        user_id=2,
        user_name="Bob",
        game="Wordle",
        day="100",
        tries=4,
        extra=None,
        streak=1,
        lost=False,
    )

    # User 1 gets +2 bonus
    PuntiBonus.create(
        date=today,
        user_id=1,
        user_name="Alice",
        punti=2,
        reason="Quiz",
        assigned_by=999,
        timestamp=100,
    )

    # User 2 gets -10 malus (should floor at 0)
    PuntiBonus.create(
        date=today,
        user_id=2,
        user_name="Bob",
        punti=-10,
        reason="Penalità",
        assigned_by=999,
        timestamp=101,
    )

    # User 3 didn't play any game, but gets +3 bonus
    PuntiBonus.create(
        date=today,
        user_id=3,
        user_name="Charlie",
        punti=3,
        reason="Bonus speciale",
        assigned_by=999,
        timestamp=102,
    )

    ranking = daily_ranking("default", from_day=today)
    # ranking items are (position, user_id, user_name, stars, bonus)
    scores = {uid: (stars, bonus) for pos, uid, name, stars, bonus in ranking}

    # Charlie (user 3): 3 stars, +3 bonus
    assert scores[3] == (3, 3)

    # Alice (user 1): stars > 2, bonus +2
    assert scores[1][1] == 2
    assert scores[1][0] >= 2

    # Bob (user 2): floored at 0, bonus -10
    assert scores[2] == (0, -10)


def test_medaglie_count_and_personal_stats_with_poop():
    today = datetime.date.today()

    Punteggio.create(
        date=today,
        timestamp=199,
        chat_id=ID_GIOCHINI,
        user_id=10,
        user_name="Luigi",
        game="Wordle",
        day="100",
        tries=3,
        extra=None,
        streak=1,
        lost=False,
    )

    Medaglia.create(
        date=today,
        timestamp=200,
        chat_id=ID_GIOCHINI,
        user_id=10,
        user_name="Luigi",
        gold=1,
        silver=2,
        bronze=1,
        last=3,
    )

    # Test medaglie_count
    summary = medaglie_count(monthly=True, target_date=today)
    assert "Luigi (1/2/1/3):" in summary
    assert POOP_MEDAL.strip() in summary

    # Test personal_stats
    stats = personal_stats(10)
    assert f"3{POOP_MEDAL.strip()}" in stats


def test_poop_medal_assignment_threshold():
    # Simulate the logic used in riassunto_serale:
    # 4 players: last gets poop
    ranking_4 = [
        (1, 101, "A", 10, 0),
        (2, 102, "B", 8, 0),
        (3, 103, "C", 5, 0),
        (4, 104, "D", 2, 0),
    ]
    min_score = min([s for _, _, _, s, *_ in ranking_4])
    award_poop = len(ranking_4) >= 4
    poop_winners = [uid for pos, uid, name, s, *_ in ranking_4 if award_poop and s == min_score and pos > 3]
    assert poop_winners == [104]

    # 3 players: no poop awarded
    ranking_3 = [
        (1, 101, "A", 10, 0),
        (2, 102, "B", 8, 0),
        (3, 103, "C", 5, 0),
    ]
    award_poop_3 = len(ranking_3) >= 4
    poop_winners_3 = [uid for pos, uid, name, s, *_ in ranking_3 if award_poop_3 and s == min([s for _, _, _, s, *_ in ranking_3]) and pos > 3]
    assert poop_winners_3 == []

def test_foximax_tiebreaking_with_letters():
    from utils import Classifica, Giocata

    cl = Classifica()
    cl.game = "FoxiMax"
    cl.day = "1409"

    # Charlie: 3 tries, 13 letters
    # Alice: 5 tries, 16 letters
    # Bob: 5 tries, 18 letters
    # David: 5 tries, no letters (extra=0)
    cl.giocate = [
        Giocata(user_id=1, user_name="Alice", game="FoxiMax", tries=5, extra=-16),
        Giocata(user_id=2, user_name="Bob", game="FoxiMax", tries=5, extra=-18),
        Giocata(user_id=3, user_name="Charlie", game="FoxiMax", tries=3, extra=-13),
        Giocata(user_id=4, user_name="David", game="FoxiMax", tries=5, extra=0),
    ]

    cl.order_and_position()

    positions = {g.user_name: g.posizione for g in cl.giocate}
    assert positions["Charlie"] == 1
    assert positions["Alice"] == 2
    assert positions["Bob"] == 3
    assert positions["David"] == 4

def test_classifica_to_string_ties_grouped():
    from utils import Classifica, Giocata

    cl = Classifica(game="Wordle", day="100", header="Wordle #100")
    cl.giocate = [
        Giocata(user_id=1, user_name="Alice", game="Wordle", tries=3),
        Giocata(user_id=2, user_name="Bob", game="Wordle", tries=3),
        Giocata(user_id=3, user_name="Charlie", game="Wordle", tries=4),
        Giocata(user_id=4, user_name="David", game="Wordle", tries=5),
        Giocata(user_id=5, user_name="Eve", game="Wordle", tries=5),
        Giocata(user_id=6, user_name="Frank", game="Wordle", tries=9999999),
    ]
    cl.order_and_position()
    cl.assign_stars('default')

    s = cl.to_string()
    expected = (
        "Wordle #100\n"
        "\U0001F947 4\u2B50Alice, Bob (3)\n"
        "\U0001F949 3\u2B50Charlie (4)\n"
        "\u2714\uFE0F 1\u2B50David, Eve (5)\n"
        "<s><i>Frank</i></s>\n"
    )
    assert s == expected



def test_score_no_single_point_games():
    from utils import Classifica, Giocata

    # Scenario 1: Only 1 valid player, no lost plays -> 0 stars
    cl1 = Classifica(game="Wordle", day="100")
    cl1.giocate = [
        Giocata(user_id=1, user_name="Alice", game="Wordle", tries=3),
    ]
    cl1.order_and_position()
    cl1.assign_stars("no-single-point-games")
    assert cl1.giocate[0].stelle == 0

    # Also test with alias "only-popular-games"
    cl1.assign_stars("only-popular-games")
    assert cl1.giocate[0].stelle == 0

    # Scenario 2: 1 valid player + 1 lost player -> total players > 1, so valid player gets 1 star, lost gets 0
    cl2 = Classifica(game="Wordle", day="100")
    cl2.giocate = [
        Giocata(user_id=1, user_name="Alice", game="Wordle", tries=3),
        Giocata(user_id=2, user_name="Bob", game="Wordle", tries=9999999),
    ]
    cl2.order_and_position()
    cl2.assign_stars("no-single-point-games")
    assert cl2.giocate[0].stelle == 1
    assert cl2.giocate[1].stelle == 0

    # Scenario 3: Multiple valid players -> works identical to default
    cl3 = Classifica(game="Wordle", day="100")
    cl3.giocate = [
        Giocata(user_id=1, user_name="Alice", game="Wordle", tries=3),
        Giocata(user_id=2, user_name="Bob", game="Wordle", tries=4),
    ]
    cl3.order_and_position()
    cl3.assign_stars("no-single-point-games")
    assert cl3.giocate[0].stelle == 2
    assert cl3.giocate[1].stelle == 1


def test_get_active_games_filters_disabled():
    from games import ALL_GAMES
    active = get_active_games()
    assert len(active) > 0

    # Statically disabled games must not be in active
    for g, data in ALL_GAMES.items():
        if data.get("disabled", False):
            assert g not in active

    # Dynamically disabled games must not be in active
    test_game = active[0]
    GameStatus.create(game_name=test_game, is_disabled=True)
    new_active = get_active_games()
    assert test_game not in new_active


def test_choose_bonus_multiplier():
    for _ in range(50):
        mult = choose_bonus_multiplier()
        assert mult in [2, 3, 4]


def test_pick_or_get_bonus_game():
    today = datetime.date.today()
    bg = pick_or_get_bonus_game(today)
    assert bg is not None
    assert bg.date == today
    assert bg.multiplier in [2, 3, 4]
    assert bg.game in get_active_games()

    # Calling again for today should return the same record (idempotent)
    bg2 = pick_or_get_bonus_game(today)
    assert bg2.id == bg.id
    assert bg2.game == bg.game
    assert bg2.multiplier == bg.multiplier

    # Test no repeat: tomorrow should not pick today's game if other games exist
    active = get_active_games()
    if len(active) > 1:
        tomorrow = today + datetime.timedelta(days=1)
        bg_tomorrow = pick_or_get_bonus_game(tomorrow)
        assert bg_tomorrow.game != bg.game


def test_daily_ranking_with_bonus_game():
    today = datetime.date.today()
    from games import get_day_from_date, ALL_GAMES
    wordle_day = get_day_from_date(ALL_GAMES["Wordle"]["date"], ALL_GAMES["Wordle"]["day"], "Wordle", today)

    # Set Wordle as bonus game with 3x multiplier
    GiocoBonus.create(date=today, game="Wordle", multiplier=3)

    # Alice gets 1st place in Wordle (2 stars base)
    Punteggio.create(
        date=today,
        timestamp=100,
        chat_id=ID_GIOCHINI,
        user_id=1,
        user_name="Alice",
        game="Wordle",
        day=wordle_day,
        tries=3,
        extra=None,
        streak=1,
        lost=False,
    )

    # Bob gets 2nd place in Wordle (1 star base)
    Punteggio.create(
        date=today,
        timestamp=101,
        chat_id=ID_GIOCHINI,
        user_id=2,
        user_name="Bob",
        game="Wordle",
        day=wordle_day,
        tries=4,
        extra=None,
        streak=1,
        lost=False,
    )

    ranking = daily_ranking("default", today)
    scores = {user_name: stars for pos, uid, user_name, stars, bonus in ranking}

    # Alice: 2 base * 3 = 6 stars
    # Bob: 1 base * 3 = 3 stars
    assert scores["Alice"] == 6
    assert scores["Bob"] == 3
