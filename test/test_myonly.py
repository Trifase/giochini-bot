import os
import sys
from unittest.mock import AsyncMock, MagicMock
import peewee
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import Punteggio, Medaglia
from utils import PuntiBonus, GiocoBonus, GameStatus
from main import myonly, myonly_full


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


@pytest.mark.anyio
async def test_myonly_sends_ephemeral_reply():
    user = MagicMock()
    user.id = 12345

    chat = MagicMock()
    chat.id = 999
    chat.type = "supergroup"

    message = MagicMock()
    message.message_id = 42
    message.from_user = user
    message.reply_text = AsyncMock()
    message.delete = AsyncMock()

    update = MagicMock()
    update.message = message
    update.effective_user = user
    update.effective_chat = chat

    context = MagicMock()
    context.bot_data = {"settings": {}}

    await myonly(update, context)

    assert message.reply_text.called
    kwargs = message.reply_text.call_args.kwargs
    assert "api_kwargs" in kwargs
    assert kwargs["api_kwargs"] == {
        "ephemeral_message_parameters": {
            "receiver_user_id": 12345
        }
    }
    assert message.delete.called


@pytest.mark.anyio
async def test_myonly_private_chat_does_not_delete():
    user = MagicMock()
    user.id = 12345

    chat = MagicMock()
    chat.id = 12345
    chat.type = "private"

    message = MagicMock()
    message.message_id = 43
    message.from_user = user
    message.reply_text = AsyncMock()
    message.delete = AsyncMock()

    update = MagicMock()
    update.message = message
    update.effective_user = user
    update.effective_chat = chat

    context = MagicMock()
    context.bot_data = {"settings": {}}

    await myonly(update, context)

    assert message.reply_text.called
    assert not message.delete.called


@pytest.mark.anyio
async def test_myonly_full_callback():
    user = MagicMock()
    user.id = 12345

    chat = MagicMock()
    chat.id = 999
    chat.type = "supergroup"

    effective_msg = MagicMock()
    effective_msg.message_id = 55
    effective_msg.edit_text = AsyncMock()

    query = MagicMock()
    query.data = "myonly_more_12345"
    query.answer = AsyncMock()

    update = MagicMock()
    update.effective_user = user
    update.effective_chat = chat
    update.effective_message = effective_msg
    update.callback_query = query

    context = MagicMock()
    context.bot_data = {"settings": {}}

    await myonly_full(update, context)

    assert query.answer.called
    assert effective_msg.edit_text.called
