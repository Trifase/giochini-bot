import datetime
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from main import daily_reminder, new_games_reminder, manual_new_games_reminder
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


@pytest.mark.anyio
async def test_daily_reminder_with_new_games():
    mock_bot = MagicMock()
    mock_post = MagicMock()
    mock_post.pin = AsyncMock()
    mock_bot.send_message = AsyncMock(return_value=mock_post)

    context = MagicMock()
    context.bot = mock_bot

    today = datetime.date.today()
    fake_bonus = GiocoBonus(date=today, game="Wordle", multiplier=3, bonus_type="jolly")
    fake_new = [
        GiocoBonus(date=today, game="Bordivide", multiplier=2, bonus_type="new_game"),
        GiocoBonus(date=today, game="Extraplot", multiplier=2, bonus_type="new_game"),
    ]

    with (
        patch("main.get_bonus_game", return_value=fake_bonus),
        patch("main.pick_or_get_bonus_game", return_value=fake_bonus),
        patch("main.get_new_games_for_date", return_value=fake_new),
    ):
        await daily_reminder(context, pin=False)

    message_text = mock_bot.send_message.call_args_list[0].kwargs["text"]
    assert "🆕 <b>Giochi nuovi (2x):</b>" in message_text
    assert "Bordivide" in message_text
    assert "Extraplot" in message_text
    assert "<b>[🆕 2x]</b>" in message_text
    assert "<b>[🎰 3x]</b>" in message_text


@pytest.mark.anyio
async def test_new_games_reminder_with_new_and_jolly():
    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock()
    context = MagicMock()
    context.bot = mock_bot

    today = datetime.date.today()
    fake_bonus = GiocoBonus(date=today, game="Wordle", multiplier=3, bonus_type="jolly")
    fake_new = [
        GiocoBonus(date=today, game="Bordivide", multiplier=2, bonus_type="new_game"),
        GiocoBonus(date=today, game="Extraplot", multiplier=2, bonus_type="new_game"),
    ]

    with (
        patch("main.get_bonus_game", return_value=fake_bonus),
        patch("main.pick_or_get_bonus_game", return_value=fake_bonus),
        patch("main.get_new_games_for_date", return_value=fake_new),
    ):
        await new_games_reminder(context)

    assert mock_bot.send_message.call_count == 1
    message_text = mock_bot.send_message.call_args.kwargs["text"]
    assert "🆕 <b>Giochi Nuovi di oggi!</b>" in message_text
    assert "Bordivide" in message_text
    assert "Extraplot" in message_text
    assert "<b>[2x]</b>" in message_text
    assert "🎰 <b>Gioco Jolly di oggi (3x):</b>" in message_text
    assert "Wordle" in message_text


@pytest.mark.anyio
async def test_new_games_reminder_without_new_games():
    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock()
    context = MagicMock()
    context.bot = mock_bot

    with patch("main.get_new_games_for_date", return_value=[]):
        await new_games_reminder(context)

    assert not mock_bot.send_message.called


@pytest.mark.anyio
async def test_manual_new_games_reminder_admin_only():
    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock()
    context = MagicMock()
    context.bot = mock_bot

    # Non-admin user: ignored
    update_non_admin = MagicMock()
    update_non_admin.effective_user.id = 999999999
    update_non_admin.message.reply_text = AsyncMock()

    with patch("main.ADMIN_ID", 123456), patch("main.get_new_games_for_date", return_value=[]):
        await manual_new_games_reminder(update_non_admin, context)
    assert not mock_bot.send_message.called
    assert not update_non_admin.message.reply_text.called

    # Admin user with no new games: replies with notice
    update_admin = MagicMock()
    update_admin.effective_user.id = 123456
    update_admin.message.reply_text = AsyncMock()

    with patch("main.ADMIN_ID", 123456), patch("main.get_new_games_for_date", return_value=[]):
        await manual_new_games_reminder(update_admin, context)
    assert not mock_bot.send_message.called
    update_admin.message.reply_text.assert_awaited_once_with("Nessun gioco nuovo attivo oggi.")

    # Admin user with active new game: sends announcement
    today = datetime.date.today()
    fake_new = [GiocoBonus(date=today, game="Bordivide", multiplier=2, bonus_type="new_game")]
    update_admin.message.reply_text.reset_mock()
    with (
        patch("main.ADMIN_ID", 123456),
        patch("main.get_new_games_for_date", return_value=fake_new),
        patch("main.get_bonus_game", return_value=None),
        patch("main.pick_or_get_bonus_game", return_value=None),
    ):
        await manual_new_games_reminder(update_admin, context)
    assert mock_bot.send_message.call_count == 1
    assert not update_admin.message.reply_text.called
