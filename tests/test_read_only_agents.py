"""reviewer, security and researcher are read-only: the hook enforces it from agent_type."""
import json

from test_secret_guard import run

READ_ONLY = ["reviewer", "security", "researcher", "brain-core:reviewer", "brain-core:security", "brain-core:researcher"]


def ev(agent, tool, **tool_input):
    payload = {"tool_name": tool, "tool_input": tool_input}
    if agent is not None:
        payload["agent_type"] = agent
    return json.dumps(payload)


def blocked_read_only(payload):
    code, err = run(payload)
    return code == 2 and "blocked by secret_guard" in err and "read-only" in err


def test_read_only_agents_cannot_use_file_writing_tools():
    for agent in READ_ONLY:
        assert blocked_read_only(ev(agent, "Write", file_path="/repo/a.py", content="x = 1")), agent
        assert blocked_read_only(ev(agent, "Edit", file_path="/repo/a.py", old_string="a", new_string="b")), agent
        assert blocked_read_only(ev(agent, "MultiEdit", file_path="/repo/a.py", edits=[])), agent
        assert blocked_read_only(ev(agent, "NotebookEdit", notebook_path="/repo/a.ipynb", new_source="x")), agent


WRITING_COMMANDS = [
    "echo hi > notes.txt", "git log >> out.log", "ls 2> err.txt", "rm -rf build", "mv a b", "cp a b",
    "git diff | tee review.md", "sed -i s/a/b/ src/app.py", "truncate -s0 log", "chmod +x run.sh", "chown u f",
    "git commit -m x", "git push", "git reset --hard", "git checkout main", "git switch -c x", "git merge x",
    "git rebase main", "git stash", "git tag v1", "git apply p.diff", "git am p.patch", "git cherry-pick abc",
    "git restore .", "git clean -fd", "git -C sub commit -am x", "git add .",
    "npm install", "npm i left-pad", "pnpm add x", "yarn add x", "yarn remove x", "npm uninstall x",
    "pip install requests", "python -m pip install x", "pip3 install x",
    "cd src && rm x", "git status; git commit -m x", "bash -c 'rm -rf build'", "find . -name '*.tmp' -delete",
    "xargs rm < list.txt", "sudo rm x", "echo $(git push)",
]


def test_read_only_agents_cannot_run_writing_commands():
    for agent in ("reviewer", "brain-core:security"):
        for cmd in WRITING_COMMANDS:
            assert blocked_read_only(ev(agent, "Bash", command=cmd)), (agent, cmd)


READING_COMMANDS = [
    "git diff", "git diff main...HEAD", "git log --oneline -20", "git show HEAD", "git status", "git blame src/a.py",
    "grep -rn TODO src", "rg -n 'a > b' src", "ls -la", "cat src/app.py", "npm test", "pnpm test", "npx playwright test",
    "pytest -q", "python -m pytest -q tests", "npm audit", "pip-audit", "npm test 2>&1 | tail -20", "git log > /dev/null",
    "npm run lint 2>/dev/null", "echo 'a > b'", "git branch -a", "find . -name '*.py'", "wc -l src/*.py",
]


def test_read_only_agents_can_read_and_run_tests():
    for agent in ("brain-core:reviewer", "researcher"):
        for cmd in READING_COMMANDS:
            assert run(ev(agent, "Bash", command=cmd))[0] == 0, (agent, cmd)
        assert run(ev(agent, "Read", file_path="/repo/src/app.py"))[0] == 0
        assert run(ev(agent, "Grep", pattern="x", path="/repo/src"))[0] == 0


def test_other_agents_and_the_main_session_can_write():
    for agent in (None, "", "developer", "brain-core:developer", "brain-core:devops", "other-plugin:reviewer-helper"):
        assert run(ev(agent, "Write", file_path="/repo/a.py", content="x = 1"))[0] == 0, agent
        assert run(ev(agent, "Bash", command="git commit -m x && rm -rf build > out.log"))[0] == 0, agent


def test_secret_rules_still_apply_to_read_only_agents():
    code, err = run(ev("brain-core:reviewer", "Bash", command="cat .env"))
    assert code == 2 and "secret file" in err


# --- regressions from the v4.0.1 review ---------------------------------------------------

def test_quoted_operators_are_not_redirects():
    for cmd in ['grep -rn ">" src', "grep -n '->' src/app.ts", 'echo "a>b"', "rg -n 'x => y' src", "tr '>' '<' < a.txt",
                'grep "a|b;c&d" src', r"grep \> src"]:
        assert run(ev("brain-core:reviewer", "Bash", command=cmd))[0] == 0, cmd


def test_wrapper_options_do_not_hide_the_command():
    for cmd in ["sudo -n rm x", "sudo -u app rm x", "nice -n 5 rm x", "env -i rm x", "timeout -s KILL 5 rm x",
                "timeout 5 rm x", "nohup rm x"]:
        assert blocked_read_only(ev("brain-core:reviewer", "Bash", command=cmd)), cmd


def test_more_writing_commands_are_blocked():
    for cmd in ["touch x", "mkdir d", "mkfifo p", "curl -o f https://example.com", "curl -sSLo f https://example.com",
                "wget -O f https://example.com", "wget https://example.com/f", "git config user.name x",
                "git config --unset user.name", "git branch -D x", "git branch new-branch", "git stash", "git stash pop",
                "git tag v1", "git tag -d v1", "git worktree add ../w", "tee out.txt"]:
        assert blocked_read_only(ev("brain-core:security", "Bash", command=cmd)), cmd


def test_listing_forms_of_git_and_tee_to_dev_null_pass():
    for cmd in ["git stash list", "git stash show -p", "git tag", "git tag -l", "git tag --list 'v4*'",
                "git worktree list", "git branch", "git branch -a", "git branch --list 'v4*'", "git branch --show-current",
                "git config user.name", "git config --get user.name", "git config --list",
                "git diff | tee /dev/null", "curl -s https://example.com", "curl -sI https://example.com",
                "wget -qO- https://example.com"]:
        assert run(ev("brain-core:reviewer", "Bash", command=cmd))[0] == 0, cmd


# --- security review of v4.0.1 ------------------------------------------------------------

def test_compound_commands_substitutions_and_eval_are_looked_into():
    for cmd in ["if true; then rm f; fi", "for i in 1; do rm f; done", "{ rm f; }", "! rm f", "while false; do mv a b; done",
                'bash -lc "rm f"', 'bash -ec "rm f"', "echo `rm f`", 'echo "$(rm f)"', 'eval "rm f"', "time rm f"]:
        assert blocked_read_only(ev("brain-core:reviewer", "Bash", command=cmd)), cmd


def test_more_tools_that_write_files():
    for cmd in ["rsync -a src/ dst/", "tar xzf a.tgz", "tar czf a.tgz src", "unzip a.zip", "gzip big.log", "gunzip a.gz",
                "patch -p1 < fix.diff", "sponge out.txt", "awk -i inplace '{print}' f", "find . -exec sed -i s/a/b/ {} +",
                "npx prettier --write .", "npx eslint --fix src", "npm audit fix", "pip download x",
                "git remote add up https://example.com/r.git", "git remote set-url origin x", "git clone https://example.com/r",
                "git gc", "git update-ref refs/heads/x HEAD", "git submodule update --init", "git init", "git notes add -m x"]:
        assert blocked_read_only(ev("brain-core:security", "Bash", command=cmd)), cmd


def test_help_dry_run_and_check_forms_pass():
    for cmd in ["git apply --check fix.diff", "git checkout --help", "cp --help", "rm --version", "pip install --dry-run x",
                "npm ci --dry-run", "npm install --dry-run", "tar tzf a.tgz", "tar --list -f a.tgz", "unzip -l a.zip",
                "git remote -v", "git remote show origin", "git submodule status", "git fetch origin", "npx prettier --check .",
                "npx eslint src", "patch --dry-run -p1 < fix.diff", "rsync -an src/ dst/", "rsync --dry-run -a src/ dst/"]:
        assert run(ev("brain-core:reviewer", "Bash", command=cmd))[0] == 0, cmd
