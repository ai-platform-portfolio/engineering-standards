# Engineering standards

Shared working standards for coding agents, with an optional `Signal` response style. The repo holds the canonical Markdown; local Claude and Codex files are adapters.

Formerly `agent-setup`. Existing Make targets and `agent-setup:*` managed markers
remain stable so installed configurations continue to reconcile without duplication.

## Executable quality policies

The setup instructions below need Python 3.9+. Quality checks need Python 3.12,
Node 22 and uv. Run `make tools` to install the locked toolchain locally.

Copy `policies/consumer.yaml` to a consumer's `engineering.yaml` and review its
source roots and dependency boundaries. Then run:

```sh
engineering-standards/.venv/bin/engineering-checks \
  --root implementation-repo --base origin/main \
  --report implementation-repo/reports/quality.json
```

The policy is read from the base revision, not the working tree. Use `--policy`
only to supply a separately trusted policy during initial adoption. Exit codes:
0 passes, 1 means policy findings, 2 means the check could not complete.

Checks parse HCL, Python and TypeScript; enforce configured import boundaries;
limit changed comment blocks; and compare changed Python/TypeScript code with
all declared source files using jscpd. Ruff, mypy, Biome and TypeScript run with
tool-owned settings. Consumer lint configuration cannot silently weaken them.
The TypeScript profile currently supports relative imports; alias mappings and
framework-specific type configuration need a reviewed profile extension.

`engineering-acceptance` holds the end-to-end cases. They cover good changes,
bad changes and tool failure. Semantic equivalence is not a guaranteed detection
capability: independently written implementations may evade clone detection.
Import rules constrain direct dependencies, not every possible runtime access.

Exceptions require an exact rule/file plus reason and owner in the trusted
policy. Use symbol-specific exceptions for Terraform. Generated-file exclusions
must also be declared there; inline suppression comments do not grant exceptions.
Policy changes require owner-approved adoption. Consumers may opt in with
`--github-pr NUMBER`, `GH_TOKEN` with pull-request read access, and
`GITHUB_REPOSITORY`. Approval must come from a base-revision owner for the current
head. See [the adoption ADR](designs/adr-reviewed-policy-adoption.md) for the
workflow wiring, trust boundary and acceptance cases.

### CI and enforcement status

Consumers pin this repository's composite action to a full commit SHA. It installs
the tools; the consumer invokes the emitted checker against the PR base and uploads
the JSON report. See the acceptance repository for a working pinned consumer.
Installation executes no consumer package scripts and needs no deployment secrets.

The organisation currently uses GitHub Free with private repositories. GitHub's
branch-protection API returned HTTP 403: upgrade or public visibility is required.
CI reports failures, but **merging is not protected**. CODEOWNERS identifies the
reviewer but does not enforce approval without the corresponding repository rule.
After that capability is available, require quality checks on the current revision,
owner review for policy/workflow changes, stale-approval dismissal and no agent bypass.

Agent repair loops, model-based reviews and deployment automation are deferred.

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

### Optional personal portfolio preference

`profiles/portfolio.md` contains Michaela's preference for production-style
platform design during local portfolio development. Opt in with
`make portfolio-plan` followed by `make portfolio-install`; check drift with
`make portfolio-verify`. It uses a separate managed block in the local Claude
and Codex guidance files and preserves existing instructions.

Default installation excludes this profile. It is not a downstream requirement
or CI policy: do not copy it into project instructions or distribute it with
modules. Installing it in global agent guidance makes it visible to local
sessions, but its instructions apply only to portfolio work. Shared approval
boundaries continue to apply.

### Repository instructions

Put project-specific conventions in the project's `AGENTS.md`. Codex reads it automatically. Claude Code 2.1.277+ can read it directly when no project `CLAUDE.md` takes precedence. On older versions, put `@AGENTS.md` in a small `CLAUDE.md` beside it. Keep personal preferences out of the shared project file.

Run `make test` to exercise fresh, existing, conflicting, and repeat installation cases in temporary home directories. Review changes to `standards/shared.md` and `profiles/signal.md` like code before rolling them out; do not commit credentials or local auth files.
