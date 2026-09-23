---
name: add-game
description: Instructions and guidelines for adding a new game to giochini-bot. Use this skill whenever adding or modifying games.
---

# Guide: Adding a New Game to giochini-bot

Follow this step-by-step checklist to add a new game with minimum token usage and zero regression errors.

---

## 1. Gather Information
Before writing code, extract:
- **Game Name**: CamelCase class name (e.g. `MoreLess`, `DontWordle`).
- **Category**: One of existing categories:
  - `"Giochi di parole"`
  - `"Geografia"`
  - `"Cinema"`
  - `"Musica"`
  - `"Miscellanea"`
  - `"Osservazione e percezione"`
  - `"Logica e matematica"`
- **Anchor Date & Day**:
  - `_date = datetime.date(YYYY, M, D)`
  - `_day = "N"` (string)
- **Emoji**: Distinguishing emoji (e.g. `🧇`, `📊`, `🎨`).
- **URL**: Game website URL.
- **Scoring Type**:
  1. *Fewer tries is better* (e.g. Wordle): `tries = int(guesses)`.
  2. *Higher score is better (integer)*: `tries = -int(score)`.
  3. *Higher score is better (decimal)*: `tries = -round(score * 100)`.
  4. *Loss condition*: `tries = "X"` when player loses.
- **Examples**: 2-3 realistic sample share texts (won, lost if applicable, different scores).

---

## 2. Implement Class in `games.py`
Add `@dataclass` class inheriting from `Giochino`:

```python
@dataclass
class NewGame(Giochino):
    _name = "NewGame"
    _category = "..."
    _date = datetime.date(YYYY, M, D)
    _day = "..."
    _emoji = "..."
    _url = "https://..."

    examples = [
        "...",
        "..."
    ]
    expected = [
        {"day": "...", "name": "NewGame", "timestamp": 10, "tries": ..., "user_id": 456481297, "user_name": "Trifase"},
        {"day": "...", "name": "NewGame", "timestamp": 10, "tries": ..., "user_id": 456481297, "user_name": "Trifase"},
    ]

    @staticmethod
    def can_handle_this(raw_text):
        text_lower = raw_text.lower()
        return "keyword1" in text_lower and "keyword2" in text_lower

    def parse(self):
        text = self.raw_text
        # 1. Parse self.day (or use get_day_from_date if date string)
        # 2. Parse score / tries (store negative if higher is better)
        # 3. self.stars = None (avoid star ties unless specifically required)
```

---

## 3. Update `utils.py` (if negative tries / decimals used)
In `process_tries(game, tries)` in `utils.py`:
- If negative integer: add to `if game in ['Geozee', 'MinuteCryptic', 'DontWordle', 'MoreLess', 'NewGame']:`
- If decimal float: add to `if game in ["Color", "Color2", "Time", "NewGame"]:`

---

## 4. Update Web Frontends (if negative tries / decimals used)
Update `processTries` in:
1. `giochini.html`
2. `www/html/trifase.online/giochini/index.html`

Add `game === "NewGame"` to corresponding `Math.abs(tries)` or decimal formatting condition.

---

## 5. Verify & Test
Run automated test suite:
```bash
uv run pytest
```
Ensure all examples in `examples` match `expected` in `test/test_games.py`.

---

## 6. Commit & Push
Commit with descriptive message and push:
```bash
git add .
git commit -m "feat: add <NewGame> game support"
git push
```
