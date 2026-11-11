# Autopilot log

Decisions made without asking during the autopilot session, one entry per decision.
Format: date · task · decision · why · alternatives rejected.

## Task 1 — Metrics module

- **2026-11-11 · outcome:** already built, tested (78 tests passing) and merged as c026d77 before this session
  started, so no new branch. Apple FY2026 inventory (5,718 → 14,541M) was verified then as the fiscal
  year-end `InventoryNet` balance from the FY2026 10-K.

## Task 2 — GitHub Actions CI

- **2026-11-11 · decision:** one workflow, `uv run --locked pytest`, on every push and PR, using
  `astral-sh/setup-uv`. **Why:** uses the same command as locally; `--locked` fails if `uv.lock` is
  out of date with `pyproject.toml`. **Rejected:** a Python version matrix (the project pins 3.12 only);
  adding lint (not asked for).
- **2026-11-11 · decision:** log entries ride on each task's branch and reach master through its PR.
  **Why:** the hard rule bans pushing to master directly. **Rejected:** a separate log-only PR per task
  (doubles the PRs for no gain).
- **2026-11-11 · outcome:** PR #7 open, `pytest` check passed on GitHub (78 tests, ~12s).
  **Blocked:** `gh pr merge --squash` was denied by Claude Code's permission classifier ("merge without
  review"). **Decision:** don't work around it; build every later task on a branch stacked on the
  previous one, each PR targeting the previous task's branch so its diff shows only that task.
  **Why:** later tasks need earlier code (the compare page needs app.py). **Rejected:** branching every
  task from master (would leave tasks 4–6 without the code they build on); stopping the queue.
  The owner merges the stack in order (see the summary at the top).
