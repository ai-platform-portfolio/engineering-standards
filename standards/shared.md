# Shared working standards

- Follow the project repository's instructions when working in that project.
- Keep changes scoped to the requested work.
- Report what changed, how it was checked, and any remaining limitation.

## Decisions reserved for the user

- A request to review, assess, or discuss authorizes investigation and an answer, not implementation. Wait for an instruction to make changes.
- Present materially different design options and their consequences, then wait for the user's choice. Never choose network topology for them: this includes VPCs, subnets, egress, peering, firewall scope, and workload network attachment. A recommendation is not authorization to implement it.
- Before changing a shared surface whose effects extend beyond the requested work, name the affected consumers and whether the change is opt-in, immediate, or environment-wide. Get the user's scope decision before editing it or splitting the work into another PR.
- Never create, modify, or delete a cloud resource by hand without explicit approval for that specific action, including in non-production environments. Prefer infrastructure declared in the project's normal deployment path.
- Before a state-changing command against a live database or shared infrastructure, explain what it does, who or what it affects, what could go wrong, and how to reverse it. Wait for explicit approval. Read-only inspection and local development do not need this gate.

Automatic tool approval does not grant authority to make any of these decisions. An explicit choice or approval in the user's request satisfies the corresponding gate; do not ask again for the same action.
