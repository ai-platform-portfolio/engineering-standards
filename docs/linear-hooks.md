# Optional Linear branch checks

Portfolio decision: soft, local warnings, including Git worktrees. Missing,
unknown or stale issue data never blocks Git. This is opt-in developer setup;
the shared agent installer and downstream consumers do not inherit it.

## Scope and policy

Each developer selects their own workspace directory. Git conditionally loads
the dispatcher for repositories beneath that directory, including future clones
and new repositories. Linked worktrees use the parent repository's Git directory.
Only remotes belonging to the configured GitHub organisation trigger Linear
warnings. A new repository without a remote is unchecked until that remote is set.

`policies/portfolio-linear.json` defines the organisation, Linear project, issue
prefix, exempt branches and maximum snapshot age. Paths and authentication are
local installation settings. For another organisation, supply a reviewed policy
with `HOOK_POLICY`; do not distribute personal paths or credentials.

`reference-transaction` checks new branches; `post-checkout` also covers switching
to existing branches and creating worktrees for them. One command can trigger
both warnings. Detached checkouts have no branch to validate.

## Install and update

Requires Git with `reference-transaction` support and Python 3.9+. Check out a
reviewed release tag or full commit of engineering-standards before installation.
The installer copies the runtime locally and records its commit and file hashes;
it never downloads a newer version automatically.

With individual API authentication available as described below, installation is:

```sh
make hooks-install WORKSPACE="$HOME/work"
```

The installer fetches a fresh snapshot before enabling the hooks. Alternatively,
use an existing authenticated MCP connection without exposing its credentials:

Read all Org Governance issue pages through the authenticated Linear connection
and save a local snapshot containing `project_id`, `verified_at` (the actual Unix
lookup time), and `issues` (the returned identifiers). Do not fabricate freshness
or store credentials in the snapshot. Then run:

```sh
make hooks-install WORKSPACE="$HOME/work" SNAPSHOT=/path/to/verified-issues.json
make hooks-status WORKSPACE="$HOME/work"
```

Repeat for additional workspace roots. Installation adds one directory-scoped
include to your global Git configuration and stores its runtime under
`WORKSPACE/.portfolio-linear/`. Nothing under that directory belongs in a project
repository. Run the same install command from a newer reviewed revision to update;
repeat from the previous revision to roll back. Reinstallation is idempotent.

Existing `.git/hooks` are forwarded their original arguments and input; their
exit codes still apply. An existing global `core.hooksPath` stops installation
for explicit reconciliation. Repository/worktree-specific `core.hooksPath`
overrides are preserved and take precedence, so those repositories need explicit
integration to receive these warnings. Custom hooks remain owner-controlled.

## Refresh and offline behaviour

Refresh after creating issues or when starting a session with a stale snapshot.
An agent can fetch a complete snapshot through the Linear MCP connection and
rerun installation. Developers can refresh directly with:

```sh
make hooks-refresh WORKSPACE="$HOME/work"
```

That command reads the developer's own `LINEAR_OAUTH_TOKEN` or `LINEAR_API_KEY`
from the environment. Supply it through an approved secret manager; never put a
token in a command argument or tracked file. MCP login does not automatically
export a token to this command. OAuth and personal-key header formats follow
[Linear's API documentation](https://linear.app/developers/graphql).

Refresh fetches every issue page for the configured project and replaces the
snapshot only on success. Errors retain the prior snapshot. The hooks themselves
make no network requests. A recognised identifier proves membership at the last
lookup, not the current issue state. Expired, missing or unknown data warns;
continuing is the explicit soft override. This is not a security boundary.

## Uninstall

```sh
make hooks-uninstall WORKSPACE="$HOME/work"
```

This removes only the installer's exact Git include. Original repository hooks
remain available; local runtime files remain for inspection or reinstallation.
If older per-repository installation was used, remove those managed hooks with
`python3 scripts/linear_hook.py remove /path/to/repo` before enabling workspace
installation. That command refuses to remove hooks somebody has edited.

Tests use temporary repositories, worktrees, clones and isolated Git configuration.
They cover matching/unrelated organisations, existing hooks, offline data,
pagination, idempotent install and rollback without changing developer credentials.
