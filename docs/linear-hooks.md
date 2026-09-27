# Optional portfolio Linear hooks

These local hooks warn about missing or unverified issue IDs in working branch
names. They never block Git, contact Linear, load signing keys, or change global
configuration. They are not installed by the shared agent setup. Scope is the
portfolio repositories explicitly passed to the installer.

`reference-transaction` checks newly created branches; `post-checkout` checks
switches and worktree checkouts, including existing branches. Both hooks live in
the common Git directory and cover linked worktrees. A command creating and
checking out a branch can emit a warning from both hooks. `main` and `master` are
exempt; detached checkouts have no branch to check.

## Install or refresh

Read the current Org Governance issues through the authenticated Linear MCP
connection, including all result pages. Save only their IDs and the lookup time
in a local JSON snapshot, for example:

```json
{"verified_at": 0, "issues": ["AI-7"]}
```

Replace `0` with the Unix timestamp of that successful lookup. Do not mark an old
list fresh or store tokens in this file. Install or refresh each repository with:

```sh
python3 scripts/linear_hook.py install /path/to/repo --snapshot /path/to/issues.json
```

Installation copies the runtime and snapshot into `.git/portfolio-linear/`, so
removing the source worktree does not break installed hooks. Reinstallation is
idempotent. Existing custom hooks or `core.hooksPath` cause the installer to stop
before modifying either hook; they require explicit integration rather than
being overwritten. Other hooks are left untouched.

## Offline behaviour and removal

A snapshot older than 24 hours, an unknown issue, corrupt data or unavailable
validation produces a warning and lets Git proceed. A recognised ID only proves
membership at the last lookup, not live issue state. Refresh through Linear when
starting a session or after creating an issue. The user can override a warning by
continuing; there is no mandatory bypass flag or remote merge restriction.

```sh
python3 scripts/linear_hook.py remove /path/to/repo
```

Removal refuses to delete hooks modified since installation. This mechanism is
user-controlled and can be disabled; it is not a security boundary. Tests exercise
real Git branches and linked worktrees in temporary repositories.
