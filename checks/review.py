"""Authorize policy adoption from a trusted owner's review of the checked-out head."""

import json
import os
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from checks.source import git

ENTRY = re.compile(r"@([A-Za-z0-9-]+)(?:/([A-Za-z0-9._-]+))?")


def owners_at_base(root: Path, base: str) -> list[tuple[str, str | None]]:
    lines = [
        line.split("#", 1)[0].split()
        for line in git(root, "show", f"{base}:.github/CODEOWNERS").splitlines()
        if line.split("#", 1)[0].strip()
    ]
    if len(lines) != 1 or lines[0][0] != "*" or len(lines[0]) < 2:
        raise ValueError("Policy adoption requires one global CODEOWNERS rule in the base revision")
    entries = []
    for owner in lines[0][1:]:
        match = ENTRY.fullmatch(owner)
        if match is None:
            raise ValueError("CODEOWNERS entries must be @account or @organisation/team")
        entries.append((match.group(1), match.group(2)))
    return entries


def owner_logins(
    entries: list[tuple[str, str | None]], fetch: Callable[[str], Any] | None = None
) -> set[str]:
    """A team owner is whoever belongs to it, so the team has to be expanded to decide."""
    fetch = fetch or request
    logins: set[str] = set()
    for name, team in entries:
        if not team:
            logins.add(name.lower())
            continue
        for page in range(1, 101):
            batch = fetch(f"orgs/{name}/teams/{team}/members?per_page=100&page={page}")
            logins |= {member["login"].lower() for member in batch if member.get("type") == "User"}
            if len(batch) < 100:
                break
        else:
            raise ValueError("Team membership pagination limit exceeded")
    return logins


def approved_owner(reviews: list[dict[str, Any]], head: str, owners: set[str]) -> str | None:
    latest: dict[str, dict[str, Any]] = {}
    for review in sorted(reviews, key=lambda item: item["id"]):
        login = review["user"]["login"].lower()
        if login in owners and review["user"]["type"] == "User":
            if review["state"] in {"APPROVED", "CHANGES_REQUESTED", "DISMISSED"}:
                latest[login] = review
    if any(review["state"] == "CHANGES_REQUESTED" for review in latest.values()):
        return None
    return next(
        (
            login
            for login, review in latest.items()
            if review["state"] == "APPROVED" and review["commit_id"] == head
        ),
        None,
    )


def request(path: str) -> Any:
    req = Request(
        f"https://api.github.com/{path}",
        headers={
            "Authorization": f"Bearer {os.environ['GH_TOKEN']}",
            "Accept": "application/vnd.github+json",
        },
    )
    with urlopen(req, timeout=15) as response:
        return json.load(response)


def github_approval(root: Path, base: str, number: int) -> dict[str, str] | None:
    repository = os.environ["GITHUB_REPOSITORY"]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository) or number < 1:
        raise ValueError("Invalid GitHub repository or pull request")
    head = git(root, "rev-parse", "HEAD").strip()
    base_sha = git(root, "rev-parse", base + "^{commit}").strip()
    if git(root, "status", "--porcelain", "--untracked-files=all").strip():
        raise ValueError("Reviewed policy requires a clean checkout of the reviewed commit")
    pull = request(f"repos/{repository}/pulls/{number}")
    if (
        pull["state"] != "open"
        or pull["head"]["sha"] != head
        or pull["base"]["sha"] != base_sha
        or pull["base"]["repo"]["full_name"].lower() != repository.lower()
    ):
        raise ValueError("Review does not match the open PR's current head and base")
    owners = owner_logins(owners_at_base(root, base)) - {pull["user"]["login"].lower()}
    reviews = []
    for page in range(1, 101):
        batch = request(f"repos/{repository}/pulls/{number}/reviews?per_page=100&page={page}")
        reviews.extend(batch)
        if len(batch) < 100:
            owner = approved_owner(reviews, head, owners)
            current = request(f"repos/{repository}/pulls/{number}")
            if current != pull:
                raise ValueError("PR changed during review verification; rerun the check")
            return {"owner": owner, "head": head, "base": base_sha} if owner else None
    raise ValueError("Review pagination limit exceeded")
