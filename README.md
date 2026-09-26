# Agent setup

Shared personal instructions for coding agents. `profiles/signal.md` is the source of truth for response style. Its Markdown body is tool neutral; the YAML frontmatter supplies the metadata Claude Code needs for a named output style.

## Install locally

Run `./scripts/install.sh --backup-existing` from this checkout. The script links the same file at:

- `~/.claude/output-styles/signal.md` for Claude Code's `Signal` output style
- `~/.codex/AGENTS.md` for Codex's global instructions

The script backs up an existing file only when `--backup-existing` is given. Without it, an existing file causes the script to stop before changing either target. Run it again after moving the checkout. Start a new Codex session and restart Claude Code after installation so each loads the file.

Claude Code selects the style through `/output-style Signal` or `outputStyle: "Signal"` in its settings. The installer does not change Claude's active style. Codex loads its global `AGENTS.md` automatically.

## Project instructions

Put shared project conventions in a repository's `AGENTS.md`. Codex reads it automatically. Claude Code 2.1.277+ can read it directly when no project `CLAUDE.md` takes precedence. On older versions, put `@AGENTS.md` in a small `CLAUDE.md` beside it.

Keep provider-specific settings and tool names out of shared instructions unless they are clearly marked as adapters. Do not commit credentials or local auth files to this repository.
