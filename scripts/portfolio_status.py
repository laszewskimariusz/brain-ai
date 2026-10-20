#!/usr/bin/env python3
"""Print the state of every project in a brain's portfolio.yaml. Read-only.

For each project: stage, the latest commit on the remote (git ls-remote) and the HTTP status
of its production URL. Network failures become statuses; the script never raises on them.
Checks run in parallel under one overall deadline; git never prompts for credentials.

Usage: python3 scripts/portfolio_status.py [path/to/portfolio.yaml]
"""
import concurrent.futures
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

import yaml


def load(path):
    with open(path) as f:
        return (yaml.safe_load(f) or {}).get("projects") or []


_REPO = re.compile(r'^(?:https?://|ssh://|git://|file://|git@[\w.-]+:|/|\.{1,2}/|[\w.-]+/)')


def check_repo(url):
    # a value from the YAML must not become a git option (--upload-pack=...) or transport (ext::)
    if not isinstance(url, str) or url.startswith('-') or '::' in url or not _REPO.match(url):
        return "invalid"
    try:
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_SSH_COMMAND": "ssh -o BatchMode=yes"}
        r = subprocess.run(["git", "ls-remote", "--", url, "HEAD"], capture_output=True, text=True, timeout=20, env=env)
    except (OSError, subprocess.TimeoutExpired):
        return "unreachable"
    if r.returncode != 0 or not r.stdout.strip():
        return "no-repo"
    return r.stdout.split()[0][:7]


def _status(url, method, timeout):
    req = urllib.request.Request(url, method=method, headers={"User-Agent": "portfolio-status"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code


def check_http(url, timeout=10):
    if not isinstance(url, str) or not re.match(r'(?i)^https?://', url):
        return "invalid"
    try:
        code = _status(url, "HEAD", timeout)
        if code in (405, 501):  # some servers refuse HEAD
            code = _status(url, "GET", timeout)
        return str(code)
    except (urllib.error.URLError, OSError, ValueError):
        return "down"


def _safe(fn, arg):
    try:
        return fn(arg)
    except Exception:
        return "error"


def rows(projects, repo_check=check_repo, http_check=check_http, deadline=60):
    """One row per project. Checks run in parallel; anything unfinished at the deadline is 'timeout'."""
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=8)
    jobs = []
    for p in projects:
        if not isinstance(p, dict):
            jobs.append(None)
            continue
        repo = pool.submit(_safe, repo_check, p["repo"]) if p.get("repo") else None
        http = pool.submit(_safe, http_check, p["url"]) if p.get("url") else None
        jobs.append((p, repo, http))
    end = time.monotonic() + deadline

    def result(future):
        if future is None:
            return "-"
        try:
            return future.result(timeout=max(0, end - time.monotonic()))
        except concurrent.futures.TimeoutError:
            return "timeout"

    out = []
    for job in jobs:
        if job is None:
            out.append(("?", "invalid", "-", "-"))
        else:
            p, repo, http = job
            out.append((p.get("slug", "?"), p.get("stage", "?"), result(repo), result(http)))
    pool.shutdown(wait=False, cancel_futures=True)
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
    code = main()
    sys.stdout.flush()
    os._exit(code)  # do not wait for checks still running past the deadline
