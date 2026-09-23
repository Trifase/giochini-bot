# giochini-bot Developer Instructions

When working in this repository:
- Follow concise communication style (terse, essential info, no fluff).
- Always run `uv run pytest` before committing to ensure no regressions across all games.
- Never push broken tests or syntax errors.

## Adding a New Game
Refer to the skill `.agents/skills/add-game/SKILL.md` for full checklist:
1. Add game class in `games.py` (`examples`, `expected`, `can_handle_this`, `parse`).
   - If higher score is better: store negative integer or negative decimal (* 100).
   - If game is lost: `tries = "X"`.
   - Default `self.stars = None` unless explicitly tracking stars.
2. If negative tries or float, update `process_tries` in `utils.py`.
3. If negative tries or float, update `processTries` in `giochini.html` and `www/html/trifase.online/giochini/index.html`.
4. Run `uv run pytest`.
5. Commit and push.
