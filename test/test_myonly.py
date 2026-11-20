import os
import sys
from unittest.mock import AsyncMock, MagicMock
import peewee
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import Punteggio, Medaglia
from utils import PuntiBonus, GiocoBonus, GameStatus
from main import myonly, myonly_full, myscore, extract_ephemeral_id, mytoday, mytoday_full


@pytest.fixture(autouse=True)
def setup_test_db():
    test_db = peewee.SqliteDatabase(":memory:")
    models = [Punteggio, Medaglia, PuntiBonus, GiocoBonus, GameStatus]
    test_db.bind(models, bind_refs=False, bind_backrefs=False)
    test_db.connect()
    test_db.create_tables(models)
    yield
    test_db.drop_tables(models)
    test_db.close()


def test_extract_ephemeral_id():
    msg = MagicMock()
    msg.api_kwargs = {"ephemeral_message_id": 999}
    msg.message_id = 100
    assert extract_ephemeral_id(msg) == 999

    msg_fallback = MagicMock()
    msg_fallback.api_kwargs = {}
    del msg_fallback.ephemeral_message_id
    msg_fallback.message_id = 50
    assert extract_ephemeral_id(msg_fallback) == 50


@pytest.mark.anyio
async def test_myonly_sends_ephemeral_reply_and_schedules_deletion():
    user = MagicMock()
    user.id = 12345

    chat = MagicMock()
    chat.id = 999
    chat.type = "supergroup"

    bot_msg = MagicMock()
    bot_msg.message_id = 100
    bot_msg.api_kwargs = {"ephemeral_message_id": 777}

    message = MagicMock()
    message.message_id = 42
    message.from_user = user
    message.reply_text = AsyncMock(return_value=bot_msg)
    message.delete = AsyncMock()

    update = MagicMock()
    update.message = message
    update.effective_user = user
    update.effective_chat = chat
    update.effective_message = message

    job_queue = MagicMock()
    context = MagicMock()
    context.bot_data = {"settings": {}}
    context.job_queue = job_queue

    await myonly(update, context)

    assert message.reply_text.called
    kwargs = message.reply_text.call_args.kwargs
    assert "api_kwargs" in kwargs
    assert kwargs["api_kwargs"] == {
        "ephemeral_message_parameters": {
            "receiver_user_id": 12345
        }
    }
    # No deletion should be scheduled for ephemeral replies or their command
    assert not job_queue.run_once.called


@pytest.mark.anyio
async def test_myscore_sends_ephemeral_reply_without_reply_deletion():
    user = MagicMock()
    user.id = 12345

    chat = MagicMock()
    chat.id = 999

    message = MagicMock()
    message.message_id = 42
    message.from_user = user
    message.reply_text = AsyncMock()

    update = MagicMock()
    update.message = message
    update.effective_user = user
    update.effective_chat = chat
    update.effective_message = message

    job_queue = MagicMock()
    context = MagicMock()
    context.job_queue = job_queue

    await myscore(update, context)

    assert message.reply_text.called
    kwargs = message.reply_text.call_args.kwargs
    assert kwargs["api_kwargs"] == {
        "ephemeral_message_parameters": {"receiver_user_id": 12345}
    }
    assert not job_queue.run_once.called


@pytest.mark.anyio
async def test_myonly_full_callback_with_cb_eph_id():
    user = MagicMock()
    user.id = 12345

    chat = MagicMock()
    chat.id = 999
    chat.type = "supergroup"

    effective_msg = MagicMock()
    effective_msg.message_id = 55
    effective_msg.api_kwargs = {"ephemeral_message_id": 777}

    query = MagicMock()
    query.id = "cq_123"
    query.data = "myonly_more_12345_777"
    query.answer = AsyncMock()
    query.message = effective_msg

    update = MagicMock()
    update.effective_user = user
    update.effective_chat = chat
    update.effective_message = effective_msg
    update.callback_query = query

    bot = MagicMock()
    bot._post = AsyncMock()

    context = MagicMock()
    context.bot_data = {"settings": {}}
    context.bot = bot

    await myonly_full(update, context)

    assert query.answer.called
    bot._post.assert_awaited_with(
        "editEphemeralMessageText",
        data={
            "chat_id": 999,
            "receiver_user_id": 12345,
            "ephemeral_message_id": 777,
            "text": bot._post.call_args.kwargs["data"]["text"],
            "parse_mode": "HTML",
        }
    )


@pytest.mark.anyio
async def test_myonly_full_callback_replace_fallback():
    user = MagicMock()
    user.id = 12345

    chat = MagicMock()
    chat.id = 999
    chat.type = "supergroup"

    effective_msg = MagicMock()
    effective_msg.message_id = 55
    effective_msg.api_kwargs = {}

    query = MagicMock()
    query.id = "cq_456"
    query.data = "myonly_more_12345"
    query.answer = AsyncMock()
    query.message = effective_msg

    update = MagicMock()
    update.effective_user = user
    update.effective_chat = chat
    update.effective_message = effective_msg
    update.callback_query = query

    bot = MagicMock()
    bot.send_message = AsyncMock(return_value=effective_msg)

    job_queue = MagicMock()
    context = MagicMock()
    context.bot_data = {"settings": {}}
    context.bot = bot
    context.job_queue = job_queue

    await myonly_full(update, context)

    # Should send message replacing callback query BEFORE answering
    assert bot.send_message.called
    kwargs = bot.send_message.call_args.kwargs
    assert kwargs["api_kwargs"]["ephemeral_message_parameters"] == {
        "receiver_user_id": 12345,
        "callback_query_id": "cq_456",
    }
    assert query.answer.called


@pytest.mark.anyio
async def test_mytoday_delegates_to_myonly():
    user = MagicMock()
    user.id = 12345

    chat = MagicMock()
    chat.id = 999
    chat.type = "supergroup"

    bot_msg = MagicMock()
    bot_msg.message_id = 100
    bot_msg.api_kwargs = {"ephemeral_message_id": 777}

    message = MagicMock()
    message.message_id = 42
    message.from_user = user
    message.reply_text = AsyncMock(return_value=bot_msg)

    update = MagicMock()
    update.message = message
    update.effective_user = user
    update.effective_chat = chat
    update.effective_message = message

    job_queue = MagicMock()
    context = MagicMock()
    context.bot_data = {"settings": {}}
    context.job_queue = job_queue

    # Calling mytoday now sends ephemeral message via myonly
    await mytoday(update, context)

    assert message.reply_text.called
    kwargs = message.reply_text.call_args.kwargs
    assert kwargs["api_kwargs"] == {
        "ephemeral_message_parameters": {
            "receiver_user_id": 12345
        }
    }


@pytest.mark.anyio
async def test_myonly_and_myscore_detect_played_games_today():
    import datetime
    from games import ALL_GAMES, get_day_from_date

    today = datetime.date.today()
    w_day = get_day_from_date(ALL_GAMES["Wordle"]["date"], ALL_GAMES["Wordle"]["day"], "Wordle", today)

    Punteggio.create(
        date=today,
        timestamp=12345,
        chat_id=999,
        user_id=12345,
        user_name="Tester",
        game="Wordle",
        day=str(w_day),
        tries=3,
        lost=False,
    )

    user = MagicMock()
    user.id = 12345
    chat = MagicMock()
    chat.id = 999
    chat.type = "supergroup"

    bot_msg = MagicMock()
    bot_msg.message_id = 100
    bot_msg.api_kwargs = {"ephemeral_message_id": 777}

    message = MagicMock()
    message.message_id = 42
    message.from_user = user
    message.reply_text = AsyncMock(return_value=bot_msg)
    message.reply_html = AsyncMock(return_value=bot_msg)

    update = MagicMock()
    update.message = message
    update.effective_user = user
    update.effective_chat = chat
    update.effective_message = message

    context = MagicMock()
    context.bot_data = {"settings": {"12345": {"favs": ["Wordle"], "favs_extra_button": False}}}
    context.job_queue = MagicMock()

    await myonly(update, context)
    myday_text = message.reply_text.call_args_list[0].args[0]
    assert "Non hai giocato a nulla oggi" not in myday_text
    assert "Hai giocato a tutti i preferiti" in myday_text

    await myscore(update, context)
    myscore_text = message.reply_text.call_args_list[-1].args[0]
    assert "Non hai ancora giocato oggi" not in myscore_text
    assert "Wordle" in myscore_text


@pytest.mark.anyio
async def test_retrying_httpx_request_retries_network_error(monkeypatch):
    from unittest.mock import patch
    from telegram.error import NetworkError, RetryAfter
    from telegram.request import HTTPXRequest
    from main import RetryingHTTPXRequest

    req = RetryingHTTPXRequest(max_retries=3)

    calls = {"count": 0}

    async def fake_super_do_request(self, *args, **kwargs):
        calls["count"] += 1
        if calls["count"] < 3:
            raise NetworkError("ConnectError")
        return 200, b'{"ok": true}'

    monkeypatch.setattr(HTTPXRequest, "do_request", fake_super_do_request)
    with patch("main.asyncio.sleep", new=AsyncMock()):
        status, body = await req.do_request("https://example.com", "POST")
    assert status == 200
    assert calls["count"] == 3

    async def fake_retry_after(self, *args, **kwargs):
        raise RetryAfter(5)

    monkeypatch.setattr(HTTPXRequest, "do_request", fake_retry_after)
    with pytest.raises(RetryAfter):
        await req.do_request("https://example.com", "POST")

    calls["count"] = 0

    async def fake_502_then_ok(self, *args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return 502, b"Bad Gateway"
        return 200, b'{"ok": true}'

    monkeypatch.setattr(HTTPXRequest, "do_request", fake_502_then_ok)
    with patch("main.asyncio.sleep", new=AsyncMock()):
        status, _ = await req.do_request("https://example.com", "POST")
    assert status == 200
    assert calls["count"] == 2


@pytest.mark.anyio
async def test_error_handler_handles_none_update():
    from main import error_handler

    bot = MagicMock()
    bot.send_message = AsyncMock()
    context = MagicMock()
    context.bot = bot
    context.error = RuntimeError("boom")

    await error_handler(None, context)
    assert bot.send_message.await_count == 2


@pytest.mark.anyio
async def test_myscore_sorts_by_medal_and_shows_counts():
    import datetime
    from games import ALL_GAMES, get_day_from_date

    today = datetime.date.today()

    # Angle: 4th place (no medal) -> 3 opponents beat user 12345
    angle_day = str(get_day_from_date(ALL_GAMES["Angle"]["date"], ALL_GAMES["Angle"]["day"], "Angle", today))
    for i, tries in enumerate([1, 2, 3], start=1):
        Punteggio.create(date=today, timestamp=100 + i, chat_id=999, user_id=i, user_name=f"P{i}", game="Angle", day=angle_day, tries=tries, lost=False)
    Punteggio.create(date=today, timestamp=105, chat_id=999, user_id=12345, user_name="Tester", game="Angle", day=angle_day, tries=4, lost=False)

    # Bandle: 2nd place (silver) -> 1 opponent beats user 12345
    bandle_day = str(get_day_from_date(ALL_GAMES["Bandle"]["date"], ALL_GAMES["Bandle"]["day"], "Bandle", today))
    Punteggio.create(date=today, timestamp=200, chat_id=999, user_id=1, user_name="P1", game="Bandle", day=bandle_day, tries=1, lost=False)
    Punteggio.create(date=today, timestamp=201, chat_id=999, user_id=12345, user_name="Tester", game="Bandle", day=bandle_day, tries=3, lost=False)

    # Wordle: 1st place (gold)
    wordle_day = str(get_day_from_date(ALL_GAMES["Wordle"]["date"], ALL_GAMES["Wordle"]["day"], "Wordle", today))
    Punteggio.create(date=today, timestamp=300, chat_id=999, user_id=12345, user_name="Tester", game="Wordle", day=wordle_day, tries=2, lost=False)
    Punteggio.create(date=today, timestamp=301, chat_id=999, user_id=1, user_name="P1", game="Wordle", day=wordle_day, tries=4, lost=False)

    user = MagicMock()
    user.id = 12345
    chat = MagicMock()
    chat.id = 999
    message = MagicMock()
    message.message_id = 42
    message.reply_text = AsyncMock()
    update = MagicMock()
    update.message = message
    update.effective_user = user
    update.effective_chat = chat
    context = MagicMock()

    await myscore(update, context)
    text = message.reply_text.call_args.args[0]
    assert text.index("Wordle") < text.index("Bandle") < text.index("Angle")
    assert "🥇 1  🥈 1  🥉 0" in text

