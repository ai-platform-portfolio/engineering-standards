"""Read GitHub controls and check them against the portfolio's reviewed contract."""

import argparse
import base64
from datetime import datetime, timezone
import json
import os
import re
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
START = "<!-- governance-status:start -->"
END = "<!-- governance-status:end -->"


def api(path):
    try:
        result = subprocess.run(
            ["gh", "api", path], capture_output=True, text=True, check=False, timeout=30,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(f"GitHub read timed out: {path}") from error
    if result.returncode:
        raise RuntimeError(f"GitHub read failed: {path}; verify access and retry")
    return json.loads(result.stdout)


def pages(path, fetch=api):
    items = []
    for page in range(1, 101):
        separator = "&" if "?" in path else "?"
        batch = fetch(f"{path}{separator}per_page=100&page={page}")
        if not isinstance(batch, list):
            raise ValueError(f"Expected a list from {path}")
        items.extend(batch)
        if len(batch) < 100:
            return items
    raise ValueError(f"Pagination limit exceeded: {path}")


def ruleset(spec, app_id):
    """The same desired configuration is used for provisioning and auditing."""
    return {
        "name": "main",
        "target": "branch",
        "enforcement": "active",
        "bypass_actors": spec.get("bypass_actors", []),
        "conditions": {"ref_name": {"include": ["refs/heads/main"], "exclude": []}},
        "rules": [
            {"type": "deletion"},
            {"type": "non_fast_forward"},
            {"type": "pull_request", "parameters": {
                "required_approving_review_count": 1,
                "dismiss_stale_reviews_on_push": False,
                "require_code_owner_review": True,
                "require_last_push_approval": False,
                "required_review_thread_resolution": True,
                "allowed_merge_methods": ["merge", "squash", "rebase"],
            }},
            {"type": "required_status_checks", "parameters": {
                "strict_required_status_checks_policy": True,
                "do_not_enforce_on_create": False,
                "required_status_checks": [
                    {"context": name, "integration_id": app_id}
                    for name in spec["checks"]
                ],
            }},
        ],
    }


def repository_policy(contract, name):
    return {**contract["defaults"], **contract["repositories"].get(name, {})}


def repositories(contract, fetch=api):
    discovered = {item["name"] for item in pages(f"orgs/{contract['organization']}/repos?type=all", fetch)}
    # Keep explicitly configured repositories in scope if they become inaccessible.
    return {name: repository_policy(contract, name)
            for name in sorted(discovered | set(contract["repositories"]))}


def differences(actual, expected, path="ruleset"):
    """Ignore additional API fields, but never omit a required field or rule."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [f"{path}: missing object"]
        findings = []
        for key, value in expected.items():
            findings.extend(differences(actual.get(key), value, f"{path}.{key}"))
        return findings
    if isinstance(expected, list):
        if not isinstance(actual, list):
            return [f"{path}: missing list"]
        if expected and isinstance(expected[0], dict):
            identity = next(key for key in ("type", "context", "actor_id") if key in expected[0])
            findings = []
            if len(actual) != len(expected):
                findings.append(f"{path}: expected {len(expected)} entries, found {len(actual)}")
            for item in expected:
                matches = [entry for entry in actual if entry.get(identity) == item[identity]]
                if len(matches) != 1:
                    findings.append(f"{path}: expected one {item[identity]}")
                else:
                    findings.extend(differences(matches[0], item, f"{path}.{item[identity]}"))
            return findings
        if sorted(actual) == sorted(expected):
            return []
    elif type(actual) is type(expected) and actual == expected:
        return []
    return [f"{path}: expected {expected!r}, found {actual!r}"]


def canonical_timestamp(value):
    if not isinstance(value, str):
        raise ValueError("Ruleset update timestamp is missing")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Ruleset update timestamp must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat(timespec="microseconds")


def owner_team(contract):
    org, _, slug = contract["code_owner"].partition("/")
    if not slug or org != contract["organization"]:
        raise ValueError("code_owner must name a team as <organisation>/<team-slug>")
    return slug


def team_member(contract, login, fetch=api):
    path = f"orgs/{contract['organization']}/teams/{owner_team(contract)}/memberships/{login}"
    try:
        return fetch(path).get("state") == "active"
    except (RuntimeError, ValueError, KeyError, TypeError):
        return False


def team_writes(contract, fetch=api):
    """GitHub ignores a code-owner team that lacks write access, without reporting it.

    Listed rather than checked per repository: the single-repository permission
    endpoint answers 204 with no body, which carries no permission to read.
    """
    path = f"orgs/{contract['organization']}/teams/{owner_team(contract)}/repos"
    return {
        item["name"] for item in pages(path, fetch)
        if item.get("permissions", {}).get("push") is True
    }


def capture_baseline(contract, fetch=api):
    owner = fetch("user")["login"]
    if not team_member(contract, owner, fetch):
        raise ValueError("Capture requires an active member of the configured owner team")
    baseline = {"verified_by": owner, "verified_for": contract["code_owner"], "rulesets": {}}
    writable = team_writes(contract, fetch)
    for name, spec in repositories(contract, fetch).items():
        prefix = f"repos/{contract['organization']}/{name}"
        if name not in writable:
            raise ValueError(f"{name}: the owner team needs write access to be a code owner")
        matches = [item for item in pages(f"{prefix}/rulesets", fetch) if item["name"] == "main"]
        if len(matches) != 1:
            raise ValueError(f"{name}: expected exactly one main ruleset before capture")
        live = fetch(f"{prefix}/rulesets/{matches[0]['id']}")
        findings = differences(live, ruleset(spec, contract["checks_app_id"]))
        if findings:
            raise ValueError(f"{name}: cannot capture an unverified configuration: {findings}")
        if not live.get("updated_at"):
            raise ValueError(f"{name}: ruleset update timestamp is missing")
        baseline["rulesets"][name] = {
            "ruleset_id": live["id"], "updated_at": canonical_timestamp(live["updated_at"]),
            "bypass_actors": live["bypass_actors"],
        }
    return baseline


def inspect_repository(org, name, spec, contract, fetch=api, baseline=None, owners_ref="main"):
    prefix = f"repos/{org}/{name}"
    info = fetch(prefix)
    findings = []
    if info.get("visibility") != "public":
        findings.append("visibility must be public")
    if info.get("default_branch") != "main" or info.get("archived") is not False:
        findings.append("repository must be active with main as its default branch")
    listing = pages(f"{prefix}/rulesets", fetch)
    matches = [item for item in listing if item["name"] == "main"]
    if len(matches) != 1:
        findings.append("expected exactly one main ruleset")
    else:
        live = fetch(f"{prefix}/rulesets/{matches[0]['id']}")
        baseline = baseline or {}
        captured = baseline.get("rulesets", {}).get(name)
        expected_capture = {
            "ruleset_id": live.get("id"), "updated_at": canonical_timestamp(live.get("updated_at")),
            "bypass_actors": spec.get("bypass_actors", []),
        }
        if (baseline.get("verified_for") != contract["code_owner"] or not baseline.get("verified_by")
                or not live.get("updated_at") or captured != expected_capture):
            findings.append("ruleset version lacks a matching owner-verified baseline")
        visible = dict(live)
        if "bypass_actors" not in visible and captured == expected_capture:
            visible["bypass_actors"] = captured["bypass_actors"]
        findings.extend(differences(visible, ruleset(spec, contract["checks_app_id"])))
        effective = fetch(f"{prefix}/rules/branches/main")
        effective_types = {
            item["type"] for item in effective if item.get("ruleset_id") == matches[0]["id"]
        }
        required_types = {item["type"] for item in ruleset(spec, contract["checks_app_id"])["rules"]}
        if not required_types.issubset(effective_types):
            findings.append("the main ruleset is not effective on main")
    try:
        owners_file = fetch(f"{prefix}/contents/.github/CODEOWNERS?ref={owners_ref}")
        owners = base64.b64decode(owners_file["content"]).decode()
        lines = [line.split("#", 1)[0].strip() for line in owners.splitlines()]
        if [line for line in lines if line] != [f"* @{contract['code_owner']}"]:
            findings.append("CODEOWNERS must assign all files to the reviewed portfolio owner")
    except (RuntimeError, ValueError, KeyError, TypeError) as error:
        findings.append(f"cannot verify CODEOWNERS: {error}")
    return {
        "repository": name,
        "visibility": info.get("visibility", "unknown"),
        "branch": info.get("default_branch", "unknown"),
        "checks": spec["checks"],
        "owners_ref": owners_ref,
        "findings": findings,
    }


def render(rows):
    lines = [START, "| Repository | Visibility | Default branch | Merge controls | Required checks |",
             "|---|---|---|---|---|"]
    for row in rows:
        checks = ", ".join(f"`{name}`" for name in row["checks"])
        state = "drift detected" if row["findings"] else "enforced"
        if row.get("owners_ref", "main") != "main":
            state += f"; proposed CODEOWNERS `{row['owners_ref'][:7]}`"
        lines.append(f"| `{row['repository']}` | {row['visibility']} | `{row['branch']}` | {state} | {checks} |")
    return "\n".join([*lines, END])


def pull_request_context(environ, fetch=api):
    """Use only the current PR head, and only for the calling repository."""
    if environ.get("GITHUB_EVENT_NAME") != "pull_request":
        return None
    event = json.loads(Path(environ["GITHUB_EVENT_PATH"]).read_text())
    repo = environ["GITHUB_REPOSITORY"]
    pr = event["pull_request"]
    sha = pr["head"]["sha"]
    if (pr["base"]["repo"]["full_name"] != repo
            or not re.fullmatch(r"[0-9a-f]{40}", sha)):
        raise ValueError("Invalid pull request audit context")
    current = fetch(f"repos/{repo}/pulls/{int(event['number'])}")
    if current["state"] != "open" or current["head"]["sha"] != sha:
        raise ValueError("Pull request head changed; rerun governance on the current commit")
    return repo, sha


def audit(contract, fetch=api, baseline=None, proposed_owners=None):
    org = contract["organization"]
    findings = []
    rows = []
    for name, spec in repositories(contract, fetch).items():
        try:
            ref = proposed_owners[1] if proposed_owners and proposed_owners[0] == f"{org}/{name}" else "main"
            row = inspect_repository(org, name, spec, contract, fetch, baseline, ref)
        except (RuntimeError, ValueError, KeyError, TypeError) as error:
            row = {"repository": name, "visibility": "unknown", "branch": "unknown",
                   "checks": spec["checks"], "findings": [str(error)]}
        rows.append(row)
        findings.extend(f"{name}: {item}" for item in row["findings"])
    block = render(rows)
    return {"status": "fail" if findings else "pass", "findings": findings, "repositories": rows}, block


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=ROOT / "governance/repositories.json")
    parser.add_argument("--report", type=Path, default=ROOT / "reports/governance.json")
    parser.add_argument("--baseline", type=Path, default=ROOT / "governance/bypass-baseline.json")
    parser.add_argument("--ruleset", help="Print desired ruleset JSON for one repository; does not write to GitHub")
    parser.add_argument("--capture-baseline", action="store_true", help="Read the full configuration as owner and print a proposed ruleset baseline; never updates GitHub")
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text())
    if args.ruleset:
        print(json.dumps(ruleset(repository_policy(contract, args.ruleset), contract["checks_app_id"]), indent=2))
        return 0
    if args.capture_baseline:
        try:
            print(json.dumps(capture_baseline(contract), indent=2))
            return 0
        except (RuntimeError, ValueError, KeyError, TypeError) as error:
            print(str(error), file=sys.stderr)
            return 2
    try:
        report, block = audit(contract, baseline=json.loads(args.baseline.read_text()),
                              proposed_owners=pull_request_context(os.environ))
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        report, block = {"status": "error", "findings": [str(error)], "repositories": []}, ""
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    summary = "## Portfolio governance audit\n\n" + block + "\n\n"
    summary += "\n".join(f"- {finding}" for finding in report["findings"])
    print(summary)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a") as stream:
            stream.write(summary + "\n")
    return {"pass": 0, "fail": 1, "error": 2}[report["status"]]


if __name__ == "__main__":
    sys.exit(main())
