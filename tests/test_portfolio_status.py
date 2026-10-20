import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("portfolio_status", ROOT / "scripts/portfolio_status.py")
ps = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ps)

EXAMPLE = ROOT / "brain-template/portfolio.yaml"


def test_loads_example_portfolio():
    projects = ps.load(EXAMPLE)
    assert [p["slug"] for p in projects] == ["invoice-app", "docs-site"]


def test_rows_use_injected_checks():
    rows = ps.rows(ps.load(EXAMPLE), repo_check=lambda url: "a1b2c3d", http_check=lambda url: "200")
    assert rows[0] == ("invoice-app", "live", "a1b2c3d", "200")
    assert rows[1] == ("docs-site", "build", "a1b2c3d", "-")  # no URL -> no HTTP check


def test_failures_become_statuses_not_exceptions():
    def boom(_):
        raise OSError("network down")
    rows = ps.rows(ps.load(EXAMPLE), repo_check=boom, http_check=boom)
    assert rows[0][2] == "error" and rows[0][3] == "error"


def test_check_repo_and_http_on_unreachable_targets():
    assert ps.check_repo("/nonexistent/repo.git") == "no-repo"
    assert ps.check_http("http://127.0.0.1:9/") == "down"


def test_main_prints_table(capsys, tmp_path):
    f = tmp_path / "p.yaml"
    f.write_text("projects:\n  - {slug: a, stage: idea, repo: /nonexistent/a.git, url: null}\n")
    assert ps.main([str(f)]) == 0
    out = capsys.readouterr().out
    assert "a" in out and "idea" in out and "no-repo" in out


# --- v4.0.1 -------------------------------------------------------------------------------

def test_git_never_prompts(monkeypatch):
    seen = {}

    def fake_run(cmd, **kw):
        seen.update(kw.get("env") or {})
        raise OSError("stop")
    monkeypatch.setattr(ps.subprocess, "run", fake_run)
    assert ps.check_repo("git@example.com:a/b.git") == "unreachable"
    assert seen.get("GIT_TERMINAL_PROMPT") == "0"
    assert "BatchMode=yes" in seen.get("GIT_SSH_COMMAND", "")


def test_head_not_allowed_falls_back_to_get():
    import http.server
    import threading

    class H(http.server.BaseHTTPRequestHandler):
        def do_HEAD(self):
            self.send_response(405)
            self.end_headers()

        def do_GET(self):
            self.send_response(200)
            self.end_headers()

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        assert ps.check_http(f"http://127.0.0.1:{srv.server_port}/") == "200"
    finally:
        srv.shutdown()


def test_entry_that_is_not_a_mapping_becomes_an_invalid_row():
    rows = ps.rows(["just-a-string", {"slug": "a", "stage": "idea"}], repo_check=str, http_check=str)
    assert rows[0] == ("?", "invalid", "-", "-")
    assert rows[1] == ("a", "idea", "-", "-")


def test_checks_run_in_parallel_with_an_overall_deadline():
    import time

    def slow(_):
        time.sleep(0.4)
        return "ok"
    projects = [{"slug": f"p{i}", "stage": "live", "repo": "r", "url": "u"} for i in range(6)]
    t = time.monotonic()
    rows = ps.rows(projects, repo_check=slow, http_check=slow)
    assert time.monotonic() - t < 1.5 and all(r[2:] == ("ok", "ok") for r in rows)

    def stuck(_):
        time.sleep(3)
        return "late"
    t = time.monotonic()
    rows = ps.rows(projects[:2], repo_check=stuck, http_check=stuck, deadline=0.5)
    assert time.monotonic() - t < 1.5 and rows[0][2:] == ("timeout", "timeout")


def test_brain_template_says_where_the_status_script_lives():
    t = (ROOT / "brain-template/CLAUDE.md").read_text()
    assert "from a clone of brain-ai" in t
    assert "pip install pyyaml" in (ROOT / "README.md").read_text()
