# Shared working standards

- Follow the project repository's instructions when working in that project.
- Keep changes scoped to the requested work.
- Report what changed, how it was checked, and any remaining limitation.
- Whenever asking the user to run a terminal command, include the exact command in a copyable code block and explain any placeholders. Commands reserved for the user must still be run by the user.

## Decisions reserved for the user

- A request to review, assess, or discuss authorizes investigation and an answer, not implementation. Wait for an instruction to make changes.
- Present materially different design options and their consequences, then wait for the user's choice. Never choose network topology for them: this includes VPCs, subnets, egress, peering, firewall scope, and workload network attachment. A recommendation is not authorization to implement it.
- Before changing a shared surface whose effects extend beyond the requested work, name the affected consumers and whether the change is opt-in, immediate, or environment-wide. Get the user's scope decision before editing it or splitting the work into another PR.

## Actions requiring user control

- Never run `ssh-add` or another command that loads, unlocks, or manages the user's signing key. If signing is blocked, stop and ask the user to handle key access. Do not disable signing to get around the block.
- Never create, modify, or delete a cloud resource by hand without explicit approval for that specific action, including in non-production environments. Prefer infrastructure declared in the project's normal deployment path.
- Before a state-changing command against a live database or shared infrastructure, explain what it does, who or what it affects, what could go wrong, and how to reverse it. Wait for explicit approval. Read-only inspection and local development do not need this gate.
- Before every Terraform or OpenTofu apply, including a wrapper command or CI trigger that starts an apply, stop and ask the user immediately before execution. Do the same before an `az` or `gcloud` command that deploys or changes remote resources. Read-only commands such as list, show, and describe do not need this check.

Automatic tool approval does not grant authority to make these decisions or satisfy a required user check. An explicit choice in the user's request settles a design decision, but never replaces the per-command checks above.
