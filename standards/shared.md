# Shared working standards

- Follow the project repository's instructions when working in that project.
- Keep changes scoped to the requested work.
- Report what changed, how it was checked, and any remaining limitation.
- Whenever asking the user to run a terminal command, include the exact command in a copyable code block and explain any placeholders. Commands reserved for the user must still be run by the user.
- Keep environment-specific Azure identifiers, storage-account names and Key Vault names in organization GitHub Secrets or a cloud secret store, not Actions Variables or tracked configuration/documentation. Grant consuming repositories access explicitly; preserve established secret names (`TF_BACKEND_RESOURCE_NAME` means the Terraform storage account). Load values at runtime and redact reports/logs. Keep state, saved plans and local bootstrap inputs access-restricted and out of Git. Removing current references does not remove published history; obtain approval before rewriting history.

## Deployment execution

- Deploy through the project's reviewed CI/CD workflows. Declare infrastructure changes in the project's normal infrastructure code and use its protected deployment environments and approval gates.
- Manual deployment is an exception only when a concrete dependency prevents CI from performing the change, such as bootstrapping the permissions CI itself needs or resolving a permission-ordering race. A local plan, convenience, pending review, or an unfinished CI workflow does not justify a manual deployment.
- Before proposing a manual exception, identify why CI cannot execute it, the minimum necessary action, affected resources, rollback and how normal CI deployment will resume. Obtain explicit approval for that exception and the specific command; reconcile the resulting configuration and state with the infrastructure code and record the evidence.
- Read-only local inspection, validation and planning remain allowed. A local saved plan is review evidence, not authorization or a reason to apply locally. Existing per-command approval requirements also apply to CI triggers that start deployment.

## Application packaging

- Prefer Docker images where the selected hosting service supports them. Use a supported alternative when service constraints justify it, such as ZIP packages for Azure Functions Flex Consumption. Record the constraint and chosen format; do not change hosting or network topology solely to satisfy this preference.
- Build and test the chosen artifact in CI and publish it through the reviewed deployment workflow. Pin container deployments by digest and package sources by immutable revision with locked dependencies. Verify the running application and its intended outcome after deployment; a successful build or upload is not deployment evidence.
- Pre-merge checks must reject incompatible hosting/artifact combinations and mutable deployment references. Include deliberately invalid combinations and supported non-container cases in acceptance tests. Identify the consuming workflow and active required check before calling the rule enforced; Docker preference alone must not reject a supported ZIP deployment.

## Pre-merge deployment validation

- Feature-branch PRs must exercise the real infrastructure plan path before merge: backend initialization, provider authentication, refresh and planning. Static validation alone is insufficient. Main re-plans for drift and gates apply; it must not be the first execution test of the planning path.
- Validate workflow YAML and embedded shell on every PR, with Actionlint and ShellCheck enabled. Missing tools or skipped shell analysis must fail the check. Keep a deliberately broken workflow as an acceptance test that proves the gate catches shell syntax errors.
- Require workflow validation and a successful plan for the current PR revision in active repository rules. A missing, skipped or failed required validation must not be presented as merge-ready. Verify the rules are active before claiming enforcement.
- Publish a commit-labelled, collapsible PR plan result, updating the existing bot comment. Redact secrets and environment identifiers before publishing; never upload raw state or saved plans. A PR plan is a preview, not permission to apply.

## Webhook security

- Authenticate webhook deliveries over HTTPS before processing, queueing or triggering downstream work. Reject missing, invalid or unavailable authentication; a public endpoint or unguessable URL is not authentication.
- Prefer the provider's supported signing mechanism. HMAC-SHA256 over the exact signed bytes with constant-time comparison is recommended where supported, not mandatory for every provider. Follow its actual protocol, including signed timestamps when available; never invent headers the sender does not supply.
- When signing is unsupported, document the provider limitation and supported alternative authentication, compensating controls, residual risk and owner acceptance. Prefer authenticated headers, validated tokens or mTLS where supported. A query-string secret requires an explicit exception, rotation and URL/log redaction; IP restrictions alone do not prove payload authenticity. Network changes retain their existing approval gate.
- Keep credentials in a secret store, bound request sizes, validate payloads, and make retries safe. Implement replay/deduplication controls appropriate to the sender and side effects; a valid signature or timestamp window alone does not prevent duplicate processing. Never log secrets, authentication headers or sensitive payloads.
- Prove rejection of missing/invalid authentication, tampered payloads where signatures are supported, and safe duplicate/replayed deliveries. After CI deployment, verify the real endpoint and downstream outcome before declaring completion; a green build or deployment alone is insufficient.

## Infrastructure documentation

- Before adding or changing Terraform/OpenTofu configuration, consult current official provider and cloud-service documentation. Check the provider version in the lock file and the engine version used by CI; confirm that proposed arguments, authentication and deployment methods are supported by those versions. Do not rely only on remembered examples or automatically upgrade to latest.
- Record the relevant documentation URLs, versions checked, configuration decisions and validation evidence in the PR or linked design. Identify deprecated fields and prefer supported replacements where compatible; provider upgrades require their own reviewed compatibility assessment.
- Validate against the locked provider schema locally and run the real PR plan before merge. Record missing access or unavailable documentation as an explicit verification gap; never claim a live lookup or successful plan that did not happen.

## Decisions reserved for the user

- A request to review, assess, or discuss authorizes investigation and an answer, not implementation. Wait for an instruction to make changes.
- Present materially different design options and their consequences, then wait for the user's choice. Never choose network topology for them: this includes VPCs, subnets, egress, peering, firewall scope, and workload network attachment. A recommendation is not authorization to implement it.
- Before changing a shared surface whose effects extend beyond the requested work, name the affected consumers and whether the change is opt-in, immediate, or environment-wide. Get the user's scope decision before editing it or splitting the work into another PR.

## Actions requiring user control

- Never run `ssh-add` or another command that loads, unlocks, or manages the user's signing key. If signing is blocked, stop and ask the user to handle key access. Do not disable signing to get around the block.
- Never create, modify, or delete a cloud resource by hand without an approved manual exception under Deployment execution and explicit approval for that specific action, including in non-production environments.
- Before a state-changing command against a live database or shared infrastructure, explain what it does, who or what it affects, what could go wrong, and how to reverse it. Wait for explicit approval. Read-only inspection and local development do not need this gate.
- Before every Terraform or OpenTofu apply, including a wrapper command or CI trigger that starts an apply, stop and ask the user immediately before execution. Do the same before an `az` or `gcloud` command that deploys or changes remote resources. Read-only commands such as list, show, and describe do not need this check.

Automatic tool approval does not grant authority to make these decisions or satisfy a required user check. An explicit choice in the user's request settles a design decision, but never replaces the per-command checks above.
