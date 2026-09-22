# AGENTS.md

Time2Stand (久坐提醒器) — a Windows desktop "sit-less reminder" in Python + Tkinter with a system tray icon, idle detection, Pomodoro mode, and a 3-minute forced rest dialog.

## Commands

- Run: `python Sight_Habit_Keeper.py` — requires `pip install pystray pillow`
- Package: `pyinstaller Sight_Habit_Keeper.spec` → `dist/Sight_Habit_Keeper.exe`
- No tests, linter, formatter, or CI exist. Don't invent a test framework for small fixes.

## Layout

- `Sight_Habit_Keeper.py` — the entire app: one ~600-line `StandUpApp` class (GUI, countdown, rest dialog, Pomodoro, tray). All UI strings are Chinese; keep new ones Chinese. Type-annotated throughout; logging via module-level `logger = logging.getLogger("SightHabitKeeper")`.
- `config.py` — JSON persistence. Key `countdown_minutes`, written to `%APPDATA%\SightHabitKeeper\` (Windows), `~/.config/` (Linux), `~/Library/Application Support` (macOS) — never in the repo. Load/save errors are silently swallowed by design.
- `stats.py` — statistics module (v2.0 feature 1). Records work seconds, completed rests, and interruptions to `SightHabitKeeper_stats.json` in the same config dir (90-day retention, corrupted files silently reset). `show_dashboard(root)` renders the 今日/本周/本月 Toplevel dashboard. `Sight_Habit_Keeper.py` calls the record functions at 5 hook points: full work segment end, manual stop (also counts an interruption), rest confirmed (≥3 min), rest ignored.
- `gamification.py` — gamification module (v2.0 feature 2). Read-only consumer of `stats.load_stats()`: check-in = a day with ≥1 completed rest; streak and 9 badges (rest/streak/work tiers) are all derived live, never stored. Its only state file `SightHabitKeeper_gamification.json` marks which new-badge notifications were already shown. `show_achievements(root)` renders the badge-wall window; `check_and_notify(root)` pops a one-time toast for freshly unlocked badges — called from `rest_confirm` in the main app. Note: it imports `_get_config_dir` from `config` at module top, so tests must patch it on `gamification` too, not just `stats`.
- `Sight_Habit_Keeper.spec` — PyInstaller onefile, `console=False`, exe icon from `assets/walking_icon.ico`.
- `archive/Sight_Habit_Keeper_bkp.py` — intentionally tracked historical backup (hardcoded 30 min); never edit or delete it.
- `优化分析报告.md` — marks 9 past technical issues as fixed; useful context, but verify before trusting (e.g. the "single-file architecture" issue is only partially addressed via `config.py`).

## Gotchas

- README is stale: it claims v1.2 and "zero dependencies", but the code is v1.4 (git tags v1.3/v1.4) and now depends on `pystray` + `Pillow`. Trust git history, not README.
- Real minimum Python is 3.7+, not 3.6 as README says — `from __future__ import annotations` is a 3.7+ feature.
- All timing uses `root.after()` recursion on the Tk main thread (self-correcting to wall-clock seconds). Never use threads for UI/timers. The only thread is the pystray daemon thread; its callbacks must hop back via `root.after(0, ...)`.
- Windows-only APIs: `winsound` and `ctypes.GetLastInputInfo` (idle detection). `get_idle_seconds()` returns 0 elsewhere; the countdown pauses when idle > 300 s (checked every 5 s).
- The window close button (`WM_DELETE_WINDOW`) minimizes to tray — it does not quit. Quit happens only via the tray "退出" item. `_on_closing()` exists but is never bound (dead code).
- Normal mode enforces a 3-minute minimum rest (`elapsed < 180` warning); Pomodoro uses 5 min / 15 min (every 4th cycle) breaks and auto-starts the next round.
- The tray icon is drawn at runtime with PIL (green circle "P"); `walking_icon.ico` is only the packaged-exe icon.

## Maintenance

When the project structure, build/test commands, architecture boundaries, development conventions, or other facts documented here change, update this instruction file in the same change.
