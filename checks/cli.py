import argparse
import json
import sys
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any

import yaml

from checks import dependencies, duplication, terraform, tooling
from checks.source import Finding, changed_lines, comments, git, parse, source_files


def load_policy(text: str) -> dict[str, Any]:
    policy = yaml.safe_load(text)
    if not isinstance(policy, dict) or policy.get("version") != 1:
        raise ValueError("engineering.yaml must declare version: 1")
    for name in ("terraform", "python", "typescript"):
        section = policy.get(name, {})
        for root in section.get("roots", []):
            if (
                not isinstance(root, str)
                or root.startswith("/")
                or ".." in root.split("/")
                or root.startswith("-")
            ):
                raise ValueError(f"Invalid {name} source root")
    for exception in policy.get("exceptions", []):
        if not all(exception.get(key) for key in ("rule", "file", "reason", "owner")):
            raise ValueError("Exceptions require rule, exact file, reason and owner")
    return policy


def evaluate(root: Path, base: str, policy: dict[str, Any], tools: Path) -> list[Finding]:
    changes = changed_lines(root, base)
    findings = []
    language_paths = []
    for path in source_files(root):
        if any(fnmatchcase(path, pattern) for pattern in policy.get("exclude", [])):
            continue
        language = (
            "terraform"
            if path.endswith((".tf", ".tfvars"))
            else "python"
            if path.endswith(".py")
            else "typescript"
        )
        section = policy.get(language, {})
        if not any(path.startswith(prefix + "/") for prefix in section.get("roots", [])):
            if path in changes:
                findings.append(
                    Finding(
                        "SCOPE001",
                        path,
                        1,
                        "Source is outside declared roots; owner review is required to expand scope.",
                    )
                )
            continue
        if (root / path).is_symlink():
            raise ValueError(f"Source symlinks are not supported: {path}")
        if language != "terraform":
            language_paths.append(path)
        if path not in changes:
            continue
        source = (root / path).read_text()
        tree = parse(path, source)
        if tree.has_error:
            findings.append(
                Finding(
                    "PARSE001",
                    path,
                    1,
                    "Source does not parse; resolve syntax errors before structural checks.",
                )
            )
            continue
        findings.extend(comments(path, tree, changes[path], policy["comments"]))
        if language == "terraform":
            findings.extend(terraform.check(path, source, tree, section))
        else:
            findings.extend(dependencies.check(path, tree, section))
    findings.extend(duplication.check(root, language_paths, changes, tools, policy["duplication"]))
    findings.extend(tooling.check(root, policy, tools))
    for path in git(root, "diff", "--name-only", base, "--").splitlines():
        if any(fnmatchcase(path, pattern) for pattern in policy.get("protected_paths", [])):
            findings.append(
                Finding(
                    "POLICY001",
                    path,
                    1,
                    "Policy changes require a separate owner-approved standards update; candidate policy cannot authorise itself.",
                )
            )
    exceptions = policy.get("exceptions", [])
    return [
        finding
        for finding in findings
        if not any(
            finding.rule == exception["rule"]
            and finding.file == exception["file"]
            and (not exception.get("symbol") or finding.symbol == exception["symbol"])
            for exception in exceptions
        )
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--base", required=True)
    parser.add_argument(
        "--policy",
        type=Path,
        help="Trusted policy outside the candidate checkout; defaults to base revision",
    )
    parser.add_argument(
        "--tools", type=Path, default=Path(__file__).resolve().parent.parent / "node_modules/.bin"
    )
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        root = args.root.resolve()
        git(root, "rev-parse", "--verify", args.base + "^{tree}")
        text = (
            args.policy.read_text()
            if args.policy
            else git(root, "show", f"{args.base}:engineering.yaml")
        )
        policy = load_policy(text)
        findings = evaluate(root, args.base, policy, args.tools.resolve())
        report: dict[str, Any] = {
            "status": "fail" if findings else "pass",
            "findings": [finding.json() for finding in findings],
        }
        code = 1 if findings else 0
    except Exception as error:
        report = {"status": "error", "findings": [], "error": str(error)}
        code = 2
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    for finding in report["findings"]:
        print(f"{finding['rule']} {finding['file']}:{finding['line']}: {finding['message']}")
    if report["status"] == "error":
        print(report["error"], file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
