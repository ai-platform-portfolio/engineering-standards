# ai-platform-portfolio delivery requirements

Scope: repositories owned by `ai-platform-portfolio` only. This document is not
part of the shared installer, consumer policies, or requirements distributed with
modules. Downstream repositories do not inherit it.

## Owner identity

Use `michaelalinks` as the owner for this organisation. Never assign
`michaela-links` as a code owner, required deployment reviewer, policy-exception
owner, governance-policy owner or default owner in org configuration or tooling.
The active CLI account does not determine ownership. This rule applies only to
`ai-platform-portfolio`; do not distribute this account choice downstream.

Use a separate authorised account or app to author PRs that require approval from
`michaelalinks`; do not weaken review requirements to allow self-approval. Migrate
existing assignments explicitly and recapture governance evidence as the correct
account. Never relabel historical verification or authorship as another user.

## Pull requests

- This is a portfolio organisation with one human owner. Open regular pull
  requests by default; use draft status only when the owner explicitly asks.
- Pending CI, owner review, approvals or dependencies belong in the PR's
  acceptance checklist, not in an automatically chosen draft status. An open
  PR is not a claim that checks have passed or that it is ready to merge.
- Existing review requirements and per-command infrastructure approval gates
  still apply. Being the sole owner does not waive them.
- Keep `dismiss_stale_reviews_on_push` disabled in this org's branch rules.
  New commits retain existing PR approvals; required checks still validate the
  latest revision. This preference does not change deployment approvals or the
  separate current-commit approval required for protected policy changes.

## Terraform repository boundaries

`terraform-modules` is a library for reusable modules, examples and tests. Do not
put live deployment roots, environment configuration, state backends or deployment
pipelines there unless the owner explicitly requests that specific exception.
The availability of modules is not permission to deploy from their repository.

Implementation repositories call immutable module revisions. Central org
infrastructure and Function publishing belong in `ops-shared`, with Terraform
configuration under `ops-shared/ci`. This supersedes the earlier `terraform-modules/ci`
exception; do not carry that exception forward. Module validation must stay
backend-free and must not apply live resources. These boundaries are org-specific.

## Workflow triggers and deployment approval

For this org, do not add `workflow_dispatch` unless the owner explicitly requests
a manual trigger. Read-only checks, builds and plans run automatically on the
appropriate PR, push, schedule or authenticated event. Deployment workflows start
automatically after relevant changes merge to main; resource-changing jobs wait
for approval in the protected deployment environment.

A manual workflow launch is not the approval gate. Configure and verify the
environment's required owner, main-only deployment and disabled administrator
bypass before enabling deployment. Apply infrastructure and federation before
publishing application code that depends on them. The agent's per-command approval
requirements still apply when it initiates an apply or deployment.

This replaces the manual-dispatch default used for Function publishing. It is
org-specific and is not installed in downstream consumers or reusable defaults.

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
ruleset baseline remain separate, reviewed operations. The only permitted bypass
is the `ai-platform-portfolio-ops` GitHub App in `.github` for automated profile
updates; other repositories and human accounts retain no bypass. This replaces
the former blanket no-bypass requirement with that explicit repository exception.

For PR audits, validate the calling repository's proposed CODEOWNERS at the exact
current PR head and label it as proposed in the report. Continue checking other
repositories and all live protections normally. Main and scheduled audits must
verify ownership on main everywhere; migrations cannot create audit exemptions.

## Optional automatic federation onboarding

This org opts in through `ops-shared/ci/onboarding.json`; absent or disabled
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
