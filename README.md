# Agent setup

Shared working standards for coding agents, with an optional `Signal` response style. The repo holds the canonical Markdown; local Claude and Codex files are adapters.

## Start here

Requires Python 3.9+ and Make. Clone this repository, then run:

```sh
make plan
make install
make verify
```

`make plan` prints each proposed file change and edits nothing. `make install` shows the same diff and asks once before applying the complete set. It preserves existing text, adds or updates only the `agent-setup:shared` section, and backs up existing files before writing. `make verify` reports missing or changed sections without editing. Repeat `make install` when the shared standard changes.

The shared standard is in `standards/shared.md`. Its adapters are `~/.codex/AGENTS.md` and `~/.claude/CLAUDE.md`. This works with the older Claude Code versions that do not read `AGENTS.md` directly. Existing symlinks, non-regular files, and damaged section markers require manual review; the script changes neither target until those issues are resolved. A developer should also review their existing instructions for a semantic conflict, since the script can preserve text but cannot judge whether two rules agree.

The shared standard reserves design and live-infrastructure decisions for the developer, and keeps signing-key access with them. Agent auto modes may approve tool execution, but they do not make those decisions or replace the required check before an apply or deployment. Review these boundaries alongside any existing personal or project instructions before installing.

## Optional Signal style

`profiles/signal.md` is the single source for Signal. To opt in:

```sh
make signal-plan
make signal-install
```

For Codex, this adds or updates a separate `agent-setup:signal` section in the global `AGENTS.md`. For Claude Code, it installs a named output style at `~/.claude/output-styles/signal.md`. Claude does not activate it automatically; select it with `/output-style Signal` or set `outputStyle: "Signal"` in `~/.claude/settings.json`. If that style file already exists, installation displays the full diff and asks before replacing it. It backs up the old file.

Run `make signal-verify` to check an opted-in installation for drift.

If you decline the prompt, no file changes. Rerun `make plan` or `make signal-plan` after resolving a conflict. Backups are stored beside the changed files with a `.backup.<timestamp>.<pid>` suffix; copy one back to restore it. An operating-system write failure can still leave one target updated; use its backup to restore it. No command edits Claude or Codex settings JSON/TOML or auth files.

## Project guidance

Put project-specific conventions in the project's `AGENTS.md`. Codex reads it automatically. Claude Code 2.1.277+ can read it directly when no project `CLAUDE.md` takes precedence. On older versions, put `@AGENTS.md` in a small `CLAUDE.md` beside it. Keep personal preferences out of the shared project file.

Run `make test` to exercise fresh, existing, conflicting, and repeat installation cases in temporary home directories. Review changes to `standards/shared.md` and `profiles/signal.md` like code before rolling them out; do not commit credentials or local auth files.
