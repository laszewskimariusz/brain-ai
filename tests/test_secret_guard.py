"""Behaviour of the brain-core PreToolUse secret guard.

Secret-looking values are assembled at runtime so that this file itself never contains one.
"""
import json
import os
import pathlib
import subprocess
import sys

HOOK = pathlib.Path(__file__).resolve().parents[1] / "plugins/brain-core/hooks/secret_guard.py"
FAKE = "abcdefghijkl" + "123456"
KEYNAME = "API" + "_KEY"


def run(payload, env=None):
    r = subprocess.run([sys.executable, "-I", str(HOOK)], input=payload, capture_output=True, text=True,
                       env={**os.environ, **(env or {})})
    return r.returncode, r.stderr


def blocks(payload, env=None):
    """A block counts only when the guard itself explains it (exit 2 alone could be a crash)."""
    code, err = run(payload, env)
    return code == 2 and "blocked by secret_guard" in err


def ev(tool, **tool_input):
    return json.dumps({"tool_name": tool, "tool_input": tool_input})


# --- writes -------------------------------------------------------------------------------

def test_blocks_literal_assignment_to_secret_name():
    for content in [f"{KEYNAME}={FAKE}", f'dbPass' + f'word: "{FAKE}"', f"client_secret = '{FAKE}'"]:
        assert blocks(ev("Write", file_path="/repo/a.ts", content=content)), content


def test_blocks_known_token_shapes():
    shapes = [
        "sk-" + "proj-" + "A1b2C3d4" * 4,
        "sk-" + "ant-" + "A1b2C3d4" * 4,
        "gh" + "p_" + "A1b2C3d4E5" * 4,
        "AK" + "IA" + "ABCDEFGHIJKLMNOP",
        "-----BEGIN OPENSSH " + "PRIVATE KEY-----",
        "postgres://user:" + FAKE + "@db.example.com/app",
    ]
    for s in shapes:
        assert blocks(ev("Write", file_path="/repo/x.txt", content=f"value {s}")), s[:12]


def test_blocks_secret_in_edit_and_multiedit():
    assert blocks(ev("Edit", file_path="/repo/a.py", old_string="a", new_string=f"{KEYNAME}={FAKE}"))
    edits = [{"old_string": "a", "new_string": f"{KEYNAME}={FAKE}"}]
    assert blocks(ev("MultiEdit", file_path="/repo/a.py", edits=edits))


def test_block_message_names_guard_and_never_echoes_value():
    code, err = run(ev("Write", file_path="/repo/a.ts", content=f"{KEYNAME}={FAKE}"))
    assert code == 2 and "blocked by secret_guard" in err and FAKE not in err


def test_allows_normal_code_placeholders_and_references():
    ok = [
        "token = get_token()",
        "apiKey: process.env.API_KEY",
        "password: '<your-password>'",
        "secret = 'changeme'",
        "TOKEN=${GITHUB_TOKEN}",
        "api_key = os.environ['API_KEY']",
        "const key = import.meta.env.VITE_KEY",
        "password_reset_url = build_url(user)",
    ]
    for c in ok:
        assert run(ev("Write", file_path="/repo/README.md", content=c))[0] == 0, c


# --- reads --------------------------------------------------------------------------------

def test_blocks_read_of_secret_files():
    for p in ["/repo/.env", "/repo/.env.production", "/home/u/.secrets", "/repo/certs/server.pem", "/repo/id_ed25519"]:
        assert blocks(ev("Read", file_path=p)), p


def test_allows_read_of_examples_and_normal_files():
    for p in ["/repo/.env.example", "/repo/src/secrets-manager.ts", "/repo/docs/secrets.md", "/repo/package.json"]:
        assert run(ev("Read", file_path=p))[0] == 0, p


def test_extra_secret_paths_from_environment():
    env = {"BRAIN_GUARD_SECRET_PATHS": "*/vault-export/*:*.kdbx"}
    assert blocks(ev("Read", file_path="/srv/vault-export/all.json"), env)
    assert blocks(ev("Read", file_path="/home/u/pw.kdbx"), env)
    assert run(ev("Read", file_path="/srv/other/all.json"), env)[0] == 0


def test_blocks_grep_into_secret_file():
    assert blocks(ev("Grep", pattern="KEY", path="/repo/.env"))


# --- bash ---------------------------------------------------------------------------------

def test_blocks_environment_dumps_and_secret_file_dumps():
    for cmd in ["printenv", "env", "env | grep X", "ls; env", "export -p", "cat /proc/1/environ",
                "docker inspect web", "docker exec web env", "cat .env", "head -5 /repo/.env.production"]:
        assert blocks(ev("Bash", command=cmd)), cmd


def test_allows_normal_commands_and_captures():
    for cmd in ["git status", "env FOO=1 npm test", "HOME_DIR=$(printenv HOME)", "grep -rn environment src/",
                "docker inspect --format '{{.State.Status}}' web", "cat .env.example", "grep -q '^API_KEY=' .env"]:
        assert run(ev("Bash", command=cmd))[0] == 0, cmd


# --- robustness ---------------------------------------------------------------------------

def test_malformed_or_unknown_input_passes_quietly():
    for payload in ["", "not json", json.dumps({"tool_name": "Write"}), json.dumps({"tool_name": "Unknown", "tool_input": {}})]:
        code, err = run(payload)
        assert code == 0 and "Traceback" not in err, payload


# --- regressions from review: ordinary code must pass -------------------------------------

def test_allows_calls_and_attribute_access_assigned_to_secret_names():
    ok = [
        "password = hashlib.sha256(data1).hexdigest()",
        "token = jwt.encode(payload1, key)",
        "secret_key = base64.b64decode(raw)",
        "api_key = settings.API_KEY_V2",
        "password=hash_password(raw_password1)",
        "auth_token = create_token_v2(user)",
    ]
    for c in ok:
        assert run(ev("Write", file_path="/repo/app.py", content=c))[0] == 0, c


def test_allows_shell_that_does_not_print_secret_files():
    for cmd in ["jq .data.key config.json", "jq -r .api.key settings.json", "sed -i s/a/b/ .env",
                "echo X=1 | tee -a .env", "declare -x FOO=bar"]:
        assert run(ev("Bash", command=cmd))[0] == 0, cmd


def test_still_blocks_printing_key_files():
    # *.key files are judged by content: see test_protected_paths
    for cmd in ["cat certs/server.pem", "declare -p"]:
        assert blocks(ev("Bash", command=cmd)), cmd


def test_sed_that_prints_a_secret_file_is_still_blocked():
    assert blocks(ev("Bash", command="sed -n p .env"))


# --- error handling (v4.0.1) --------------------------------------------------------------

def _main_in_process(monkeypatch, capsys, payload, **patches):
    import importlib.util
    import io
    spec = importlib.util.spec_from_file_location("secret_guard_t4", HOOK)
    sg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sg)
    for name, fn in patches.items():
        monkeypatch.setattr(sg, name, fn)
    monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
    code = sg.main()
    return code, capsys.readouterr().err


def _boom(*_a, **_k):
    raise RuntimeError("scanner bug")


def test_scanner_exception_on_a_known_tool_fails_closed(monkeypatch, capsys):
    cases = [(ev("Write", file_path="/repo/a.py", content="x"), {"scan_content": _boom}),
             (ev("Read", file_path="/repo/a.py"), {"is_secret_path": _boom}),
             (ev("Bash", command="ls"), {"scan_bash": _boom})]
    for payload, patches in cases:
        code, err = _main_in_process(monkeypatch, capsys, payload, **patches)
        assert code == 2 and "internal error, failing closed" in err and "Traceback" not in err, payload
        assert "scanner bug" not in err


def test_unreadable_input_passes_with_a_short_warning():
    for payload in ["", "not json", "[1, 2]", json.dumps({"tool_input": {}})]:
        code, err = run(payload)
        assert code == 0 and "Traceback" not in err and "secret_guard" in err and len(err) < 200, payload


def test_blocks_more_url_credential_shapes():
    for url in ["redis://:" + FAKE + "@cache.example.com:6379", "mongodb+srv://app:" + FAKE + "@cluster0.example.net/db"]:
        assert blocks(ev("Write", file_path="/repo/config.ts", content=f'url = "{url}"')), url[:12]


def test_url_without_credentials_still_passes():
    for c in ["redis://cache.example.com:6379", "mongodb+srv://cluster0.example.net/db", "url = 'redis://:${REDIS_PASS}@cache'"]:
        assert run(ev("Write", file_path="/repo/config.ts", content=c))[0] == 0, c
