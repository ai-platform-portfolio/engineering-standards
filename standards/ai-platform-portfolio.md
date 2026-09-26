# ai-platform-portfolio delivery requirements

Scope: repositories owned by `ai-platform-portfolio` only. This document is not
part of the shared installer, consumer policies, or requirements distributed with
modules. Downstream repositories do not inherit it.

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
