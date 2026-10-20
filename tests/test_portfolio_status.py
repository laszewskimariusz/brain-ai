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
