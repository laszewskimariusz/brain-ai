"""CI validates the manifests, installs the plugin from this checkout and pins third-party actions."""
import re

import yaml

from conftest import ROOT

CI = (ROOT / ".github/workflows/ci.yml").read_text()


def _runs():
    jobs = yaml.safe_load(CI)["jobs"]
    return "\n".join(step.get("run", "") for job in jobs.values() for step in job["steps"])


def test_ci_validates_both_manifests():
    runs = _runs()
    assert "claude plugin validate ." in runs
    assert "claude plugin validate plugins/brain-core" in runs


def test_ci_installs_the_plugin_from_the_checkout_in_a_clean_home():
    runs = _runs()
    assert re.search(r"HOME=.*mktemp", runs)
    assert 'claude plugin marketplace add "$GITHUB_WORKSPACE"' in runs
    assert "claude plugin install brain-core@brain-ai" in runs
    assert "Agents (7)" in runs and "Skills (4)" in runs


def test_ci_pins_claude_code_and_gitleaks():
    assert re.search(r"npm i(?:nstall)? -g @anthropic-ai/claude-code@\d+\.\d+\.\d+", CI)
    m = re.search(r"uses:\s*gitleaks/gitleaks-action@(\S+)", CI)
    assert m and re.fullmatch(r"[0-9a-f]{40}", m.group(1)), "pin gitleaks-action to a commit SHA"


def test_ci_pins_every_action_by_sha_and_drops_checkout_credentials():
    jobs = yaml.safe_load(CI)["jobs"]
    for job in jobs.values():
        for step in job["steps"]:
            if "uses" in step:
                assert re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", step["uses"]), step["uses"]
            if step.get("uses", "").startswith("actions/checkout@"):
                assert step["with"]["persist-credentials"] is False
