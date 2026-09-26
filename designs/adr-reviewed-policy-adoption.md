# ADR: adopt policy changes after owner review

Status: proposed for opt-in adoption

## Context

The checker reads `engineering.yaml` from the PR base. This prevents a feature
from weakening its own checks, but previously also blocked legitimate policy
changes permanently: `POLICY001` had no executable approval path.

Terraform deployment PR #3 demonstrates the problem. `ci/main.tf` composes
`module.deployment_identity` from this repository. Its exact `TF002` exception
and new deployment workflow need review, while all other code checks must run.

## Decision

Consumers opt in with `--github-pr NUMBER`, a read-only GitHub token and
`GITHUB_REPOSITORY`. Existing consumers retain base-policy enforcement.

1. Read the owners and policy from the supplied base revision. Initially support
   one global CODEOWNERS rule containing individual accounts; reject other forms.
2. Verify a clean checkout matches the open PR's current head and base.
3. Fetch all reviews. Require a trusted owner's latest formal review to approve
   that head. Exclude the PR author and bots. Dismissal removes approval; a trusted
   owner's outstanding change request blocks adoption.
4. Load policy from the approved head and run the complete checker. Clear only
   `POLICY001`; keep all remaining findings and tool failures.
5. Record owner, head and base in the JSON report. Run the check again on review
   submission or dismissal. New commits require a fresh approval.

`engineering.yaml` and `.github/CODEOWNERS` are always protected. A policy
exception cannot suppress `POLICY001`. Candidate CODEOWNERS cannot grant its
author permission to adopt policy. API errors and unsupported owner rules fail
closed. No workflow uses a deployment credential for this check.

## Consequences and boundaries

An owner is authorizing the entire candidate policy, including scope exclusions
and exceptions. This is a review decision, not proof that the policy is strong.
For PR #3, the reviewed exception permits only the named identity module call;
an unrelated unpinned module still fails `TF002`.

The consumer pins the checker action to an immutable commit and checks out the
actual PR head. Review-triggered checks need `pull-requests: read`. Fork PRs with
insufficient token permissions fail closed and need a supported review context.

This checker is not an immutable security boundary: a PR can edit its workflow.
Repository rules must independently require checks and owner reviews, dismiss
stale approvals, and restrict bypass. CODEOWNERS alone does not enforce merging.
Do not describe a repository as protected until its active rules are verified.
Queued review runs can race; native review requirements remain necessary even
when the checker re-fetches the PR before accepting approval.

Policy approval does not approve Terraform apply. Deployment continues through
the separately gated deployment environment and requires explicit user approval.

## Acceptance evidence

Tests use temporary Git repositories and simulated GitHub responses. The fixture
adds a same-repository module and its exact exception, changes a workflow, and
attempts to replace CODEOWNERS. Tests verify approval by the base owner succeeds,
candidate-owner approval fails, and an unrelated bad module still fails. Stale,
dismissed, rejected, self-authored and missing reviews cannot adopt policy.
Dirty checkout, mismatched PR references and unavailable API also fail closed.
These tests do not claim to validate GitHub's live event delivery or branch rules.
