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

