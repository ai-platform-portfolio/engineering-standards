# ai-platform-portfolio delivery requirements

Scope: repositories owned by `ai-platform-portfolio` only. This document is not
part of the shared installer, consumer policies, or requirements distributed with
modules. Downstream repositories do not inherit it.

## Pull requests

- This is a portfolio organisation with one human owner. Open regular pull
  requests by default; use draft status only when the owner explicitly asks.
- Pending CI, owner review, approvals or dependencies belong in the PR's
  acceptance checklist, not in an automatically chosen draft status. An open
  PR is not a claim that checks have passed or that it is ready to merge.
- Existing review requirements and per-command infrastructure approval gates
  still apply. Being the sole owner does not waive them.

## Track outcomes through completion

- Keep an acceptance checklist in the PR description that covers each requested
  outcome. Preserve outstanding items across follow-up requests and compaction;
  a narrower implementation does not replace the original request.
- Link each completed item to evidence for the current revision: a CI run,
  visible product result, or relevant test. A file or commit alone is not proof
  that an integration works. Distinguish local tests from live verification.
- Do not silently defer, drop, or split requested outcomes. Get the owner's
  agreement to a scope change. Keep blocked items unchecked with the exact
  dependency or approval needed; never mark the overall request complete early.
- Before requesting final review, reconcile the checklist against the original
  request and later corrections. Passing existing CI is not sufficient if CI
  does not cover a requested outcome. Live changes still require their existing
  per-command approvals.

For a requested PR plan preview, completion evidence includes a real successful
plan, a visible collapsible comment with the commit SHA, an update to that same
comment on rerun, and a failed-authentication case that posts a failure without
exposing secrets. Until all requested outcomes are evidenced, work is incomplete.

This is an org delivery rule, not an automated proof of semantic completeness.
Acceptance tests enforce the outcomes they cover; the owner reviews coverage.

## Linear and local branch checks

Use the [Org Governance project](https://linear.app/ai-platform-portfolio/project/org-governance-c9012ab30f01)
as the durable record for this organisation's governance requests. Read the active
issue before work, preserve remaining requirements across sessions, and link PRs
and verification evidence before marking it complete. A merged PR alone does not
close an outcome requiring deployment or live verification.

The owner chose optional, soft Linear checks for branches and worktrees. They
warn rather than block; they are not tamper-proof or a new remote merge gate.
Developers choose their workspace paths and authenticate individually. Installation
must preserve existing hooks and remain reversible. Scope by GitHub organisation,
keep policy separate from local settings, and install reviewed versions explicitly.
See [installation, refresh, limitations and removal](../docs/linear-hooks.md).

This extends the existing org-only completion rule with its Linear record and
adds an opt-in local check. It does not weaken owner approvals, required CI or
existing hooks, and introduces no downstream requirement.

## Repository governance

Discover organisation repositories from GitHub and audit each against the default
governance policy plus reviewed repository-specific overrides. Adding a repository
must not require an inventory edit. Missing protections or unverifiable controls
must still fail, with findings naming the affected repository and control.

Publish the discovered catalogue and findings in the audit run summary and report.
Link to that evidence instead of maintaining a static table claiming compliance.
Discovery is read-only: provisioning protections and refreshing the owner-verified
no-bypass baseline remain separate, reviewed operations.

## Optional automatic federation onboarding

This org opts in through `terraform-modules/ci/onboarding.json`; absent or disabled
configuration does not enroll repositories. Do not install this preference in
downstream projects or couple cloud access to local branch-hook installation.

Every discovered public org repository receives a desired `central-apply`
federation entry, even before it needs Azure. Use verified immutable org/repository
IDs and the existing CI identity. Add planning trust only for repositories that
actually plan infrastructure; preserve existing credential addresses.

Authenticated repository webhooks request an infrastructure plan. CI resolves the
inventory for PR, main and approved apply plans; changed inventory invalidates the
reviewed fingerprint. API errors, mismatched IDs and credential-capacity overflow
must fail rather than silently omit repositories. The webhook cannot invoke apply;
Azure writes retain the owner's protected CI approval and per-command gate.

Before publishing application code, require the named owner and main-only
deployment environment, verify actual OIDC claims against the declared repository
trust, and complete Azure login before deployment. Required CI must exercise
disabled onboarding, new-repository inclusion, invalid metadata and missing/wrong
authentication cases. Record the real plan, approval and successful token exchange;
declaring a credential does not prove it exists or works in Azure.

The automatic entries inherit this sandbox CI identity's existing permissions.
This opt-in is not a least-privilege workload identity policy. New repositories
still need protected environments and explicit secret access before deployment.
