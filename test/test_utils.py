import datetime
import peewee
import pytest

from config import Punteggio, Medaglia, ID_GIOCHINI
from utils import PuntiBonus, daily_ranking, medaglie_count, personal_stats, POOP_MEDAL


@pytest.fixture(autouse=True)
def setup_test_db():
    # Setup test tables
    test_db = peewee.SqliteDatabase(":memory:")
    models = [Punteggio, Medaglia, PuntiBonus]
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
