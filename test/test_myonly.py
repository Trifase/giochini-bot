import os
import sys
from unittest.mock import AsyncMock, MagicMock
import peewee
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import Punteggio, Medaglia
from utils import PuntiBonus, GiocoBonus, GameStatus
from main import myonly, myonly_full, delete_ephemeral_post, extract_ephemeral_id


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
    # Verify 60s deletion was scheduled
    assert job_queue.run_once.called
    call_args = job_queue.run_once.call_args
    assert call_args[0][0] == delete_ephemeral_post
    assert call_args[0][1] == 60


@pytest.mark.anyio
async def test_delete_ephemeral_post():
    bot = MagicMock()
    bot._post = AsyncMock()

    msg_to_delete = MagicMock()
    msg_to_delete.delete = AsyncMock()

    job = MagicMock()
    job.data = [
        {
            "chat_id": 999,
            "receiver_user_id": 12345,
            "ephemeral_message_id": 777,
            "message": msg_to_delete,
        },
        msg_to_delete,
    ]

    context = MagicMock()
    context.bot = bot
    context.job = job

    await delete_ephemeral_post(context)

    bot._post.assert_awaited_with(
        "deleteEphemeralMessage",
        data={
            "chat_id": 999,
            "receiver_user_id": 12345,
            "ephemeral_message_id": 777,
        }
    )
    assert msg_to_delete.delete.called


@pytest.mark.anyio
async def test_myonly_full_callback_ephemeral():
    user = MagicMock()
    user.id = 12345

    chat = MagicMock()
    chat.id = 999
    chat.type = "supergroup"

    effective_msg = MagicMock()
    effective_msg.message_id = 55
    effective_msg.api_kwargs = {"ephemeral_message_id": 777}
    effective_msg.edit_text = AsyncMock()

    query = MagicMock()
    query.data = "myonly_more_12345"
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
    # It should have called editEphemeralMessageText
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
