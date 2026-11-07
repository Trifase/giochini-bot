import datetime
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from main import daily_reminder
from utils import GiocoBonus


@pytest.mark.anyio
async def test_daily_reminder_with_bonus():
    mock_bot = MagicMock()
    mock_post = MagicMock()
    mock_post.pin = AsyncMock()
    mock_bot.send_message = AsyncMock(return_value=mock_post)

    context = MagicMock()
    context.bot = mock_bot

    fake_bonus = GiocoBonus(
        date=datetime.date.today(),
        game="Wordle",
        multiplier=3,
    )

    with patch("main.get_bonus_game", return_value=fake_bonus), patch("main.pick_or_get_bonus_game", return_value=fake_bonus):
        await daily_reminder(context, pin=True)

    assert mock_bot.send_message.called
    first_call_args = mock_bot.send_message.call_args_list[0]
    message_text = first_call_args.kwargs["text"]

    assert "🎰 <b>Gioco Jolly di oggi (3x):</b>" in message_text
    assert "Wordle" in message_text
    assert "<b>[🎰 3x]</b>" in message_text
    assert mock_post.pin.called


@pytest.mark.anyio
async def test_daily_reminder_without_bonus():
    mock_bot = MagicMock()
    mock_post = MagicMock()
    mock_post.pin = AsyncMock()
    mock_bot.send_message = AsyncMock(return_value=mock_post)

    context = MagicMock()
    context.bot = mock_bot

    with patch("main.get_bonus_game", return_value=None), patch("main.pick_or_get_bonus_game", return_value=None):
        await daily_reminder(context, pin=False)

    assert mock_bot.send_message.called
    first_call_args = mock_bot.send_message.call_args_list[0]
    message_text = first_call_args.kwargs["text"]

    assert "Buongiorno, ecco a cosa si gioca oggi!" in message_text
    assert "🎰 <b>Gioco Jolly di oggi" not in message_text
    assert "[🎰" not in message_text
    assert not mock_post.pin.called
