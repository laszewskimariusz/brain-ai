#!/usr/bin/env python3
"""Print the state of every project in a brain's portfolio.yaml. Read-only.

For each project: stage, the latest commit on the remote (git ls-remote) and the HTTP status
of its production URL. Network failures become statuses; the script never raises on them.

Usage: python3 scripts/portfolio_status.py [path/to/portfolio.yaml]
"""
import subprocess
import sys
import urllib.error
import urllib.request

import yaml


def load(path):
    with open(path) as f:
        return (yaml.safe_load(f) or {}).get("projects") or []


def check_repo(url):
    try:
        r = subprocess.run(["git", "ls-remote", url, "HEAD"], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return "unreachable"
    if r.returncode != 0 or not r.stdout.strip():
        return "no-repo"
    return r.stdout.split()[0][:7]


def check_http(url, timeout=10):
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "portfolio-status"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return str(resp.status)
    except urllib.error.HTTPError as e:
        return str(e.code)
    except (urllib.error.URLError, OSError, ValueError):
        return "down"


def _safe(fn, arg):
    try:
        return fn(arg)
    except Exception:
        return "error"


def rows(projects, repo_check=check_repo, http_check=check_http):
    out = []
    for p in projects:
        repo = _safe(repo_check, p["repo"]) if p.get("repo") else "-"
        http = _safe(http_check, p["url"]) if p.get("url") else "-"
        out.append((p.get("slug", "?"), p.get("stage", "?"), repo, http))
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    path = argv[0] if argv else "portfolio.yaml"
    table = [("project", "stage", "commit", "http")] + rows(load(path))
    widths = [max(len(str(r[i])) for r in table) for i in range(4)]
    for r in table:
        print("  ".join(str(c).ljust(w) for c, w in zip(r, widths)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
