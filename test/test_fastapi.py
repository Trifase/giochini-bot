import datetime
import peewee
import pytest
from fastapi.testclient import TestClient

from config import Punteggio, Punti, Medaglia, PuntiBonus, ID_GIOCHINI
from utils import GiocoBonus
from main_fastapi import app


@pytest.fixture(autouse=True)
def setup_fastapi_test_db():
    test_db = peewee.SqliteDatabase("file:testfastapidb?mode=memory&cache=shared", uri=True)
    models = [Punteggio, Punti, Medaglia, PuntiBonus, GiocoBonus]
    test_db.bind(models, bind_refs=False, bind_backrefs=False)
    test_db.connect()
    test_db.create_tables(models)
    yield
    test_db.drop_tables(models)
    test_db.close()


def test_api_games_list():
    client = TestClient(app)
    res = client.get("/api/games/")
    assert res.status_code == 200
    games = res.json()
    assert isinstance(games, list)
    assert len(games) > 0
    assert any(g["name"] == "Wordle" for g in games)


def test_api_classifica_and_dailyranking():
    client = TestClient(app)
    today = datetime.date.today()
    from games import get_day_from_date, ALL_GAMES
    wordle_day = get_day_from_date(ALL_GAMES["Wordle"]["date"], ALL_GAMES["Wordle"]["day"], "Wordle", today)

    # Insert test data
    Punteggio.create(
        date=today,
        timestamp=100,
        chat_id=ID_GIOCHINI,
        user_id=1,
        user_name="Mario",
        game="Wordle",
        day=wordle_day,
        tries=3,
        lost=False,
    )
    Punteggio.create(
        date=today,
        timestamp=101,
        chat_id=ID_GIOCHINI,
        user_id=2,
        user_name="Luigi",
        game="Wordle",
        day=wordle_day,
        tries=4,
        lost=False,
    )

    # Test classifica endpoint
    res_cls = client.get(f"/api/classifica/?day={today.strftime('%Y-%m-%d')}&game=Wordle")
    assert res_cls.status_code == 200
    cls_data = res_cls.json()
    assert isinstance(cls_data, list)
    assert len(cls_data) == 1
    assert cls_data[0]["game"] == "Wordle"
    assert len(cls_data[0]["posizioni"]) == 2
    assert cls_data[0]["posizioni"][0]["user_name"] == "Mario"
    assert cls_data[0]["posizioni"][0]["pos"] == 1

    # Test dailyranking endpoint
    res_daily = client.get(f"/api/dailyranking/?day={today.strftime('%Y-%m-%d')}")
    assert res_daily.status_code == 200
    daily_data = res_daily.json()
    assert "rankings" in daily_data
    assert len(daily_data["rankings"]) == 2
    assert daily_data["rankings"][0]["name"] == "Mario"


def test_api_monthly_and_alltime_rankings():
    client = TestClient(app)
    today = datetime.date.today()
    Punti.create(date=today, user_id=1, user_name="Mario", punti=10)
    Punti.create(date=today, user_id=2, user_name="Luigi", punti=5)

    res_monthly = client.get(f"/api/monthlyranking/?month={today.strftime('%Y-%m')}")
    assert res_monthly.status_code == 200
    monthly_data = res_monthly.json()
    assert len(monthly_data["rankings"]) == 2
    assert monthly_data["rankings"][0]["name"] == "Mario"
    assert monthly_data["rankings"][0]["points"] == 10

    res_alltime = client.get("/api/alltimeranking/")
    assert res_alltime.status_code == 200
    alltime_data = res_alltime.json()
    assert len(alltime_data["rankings"]) == 2


def test_api_medals_and_jolly():
    client = TestClient(app)
    today = datetime.date.today()
    Medaglia.create(
        date=today,
        timestamp=100,
        chat_id=ID_GIOCHINI,
        user_id=1,
        user_name="Mario",
        gold=1,
        silver=0,
        bronze=0,
        last=0,
    )

    res_medals = client.get("/api/medals/?all_time=true")
    assert res_medals.status_code == 200
    medals_data = res_medals.json()
    assert len(medals_data["medals"]) >= 1
    assert medals_data["medals"][0]["user_name"] == "Mario"
    assert medals_data["medals"][0]["gold"] == 1

    # Jolly endpoint for a specific date
    past_date = today - datetime.timedelta(days=5)
    GiocoBonus.create(date=past_date, game="Wordle", multiplier=3)
    res_jolly = client.get(f"/api/jolly/?day={past_date.strftime('%Y-%m-%d')}")
    assert res_jolly.status_code == 200
    jolly_data = res_jolly.json()
    assert jolly_data["active"] is True
    assert jolly_data["bonus"]["game"] == "Wordle"
    assert jolly_data["bonus"]["multiplier"] == 3
