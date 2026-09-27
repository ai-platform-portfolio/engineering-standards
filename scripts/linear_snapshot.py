"""Refresh issue IDs with individual authentication; never persist credentials."""

import json
import os
import time
from pathlib import Path
from urllib.request import Request, urlopen

QUERY = """query($project: ID!, $after: String) {
  issues(first: 100, after: $after, filter: {project: {id: {eq: $project}}}) {
    nodes { identifier }
    pageInfo { hasNextPage endCursor }
  }
}"""


def fetch_page(project, cursor):
    token = os.environ.get("LINEAR_OAUTH_TOKEN")
    authorization = f"Bearer {token}" if token else os.environ.get("LINEAR_API_KEY")
    if not authorization:
        raise ValueError(
            "Provide your own LINEAR_OAUTH_TOKEN or LINEAR_API_KEY through your secret manager, or import an MCP-verified snapshot."
        )
    request = Request(
        "https://api.linear.app/graphql",
        method="POST",
        headers={"Authorization": authorization, "Content-Type": "application/json"},
        data=json.dumps(
            {"query": QUERY, "variables": {"project": project, "after": cursor}}
        ).encode(),
    )
    with urlopen(request, timeout=20) as response:
        return json.load(response)


def refresh(policy, destination, fetch=fetch_page):
    cursor, seen, issues = None, set(), []
    while True:
        page = fetch(policy["project_id"], cursor)
        if page.get("errors"):
            raise ValueError("Linear rejected the lookup; previous snapshot retained.")
        connection = page["data"]["issues"]
        issues.extend(item["identifier"] for item in connection["nodes"])
        info = connection["pageInfo"]
        if not info["hasNextPage"]:
            break
        cursor = info["endCursor"]
        if not cursor or cursor in seen:
            raise ValueError("Invalid pagination; previous snapshot retained.")
        seen.add(cursor)
    snapshot = {
        "project_id": policy["project_id"],
        "policy": policy,
        "verified_at": time.time(),
        "issues": sorted(set(issues)),
    }
    temporary = Path(str(destination) + ".tmp")
    temporary.write_text(json.dumps(snapshot) + "\n")
    temporary.replace(destination)
    return len(snapshot["issues"])
