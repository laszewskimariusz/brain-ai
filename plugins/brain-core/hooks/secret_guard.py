#!/usr/bin/env python3
"""PreToolUse secret guard for the brain-core plugin.

Input:  Claude Code hook JSON on stdin ({"tool_name", "tool_input"}).
Output: exit 0 = allow; exit 2 + a reason on stderr = block (the agent sees the reason).

A seat belt against honest mistakes, not a sandbox. It runs in every project, so a false
positive on ordinary code is as bad as a missed leak.

Blocks:
- Write / Edit / MultiEdit / NotebookEdit: a literal value assigned to a *KEY / *SECRET / *TOKEN /
  *PASSWORD name (letters and digits, >= 12 chars, not a placeholder, not a call or reference),
  well-known token shapes, private keys, passwords embedded in URLs, Bearer tokens.
- Read / Grep / Glob of secret files: the PROTECTED list below (.env and its stages, not
  .env.example; .secrets; *.pem/*.p12/*.pfx; SSH keys and ~/.ssh), *.key files that hold a private
  key, plus globs from BRAIN_GUARD_SECRET_PATHS (colon-separated).
- Bash: environment dumps (env, printenv, export -p, set, /proc/*/environ, container env,
  docker inspect without --format) unless captured into a variable; printing secret files;
  copying them out (cp source, scp, rsync, curl @file, tar, ...) or feeding them with "<".

It never echoes the matched value. Malformed or unexpected input is allowed silently.
"""
import fnmatch
import json
import os
import re
import shlex
import sys

# --- file contents -------------------------------------------------------------------------

_KEYWORD = r'(?:api[_-]?key|apikey|secret(?:[_-]?key)?|client[_-]?secret|access[_-]?token|auth[_-]?token|token|password|passwd|pwd)'
_ASSIGN = re.compile(
    r'(?i)(?<![A-Za-z0-9])[A-Za-z0-9_]*?' + _KEYWORD + r'["\']?\s*[:=]\s*(["\'`]?)([^\s"\'`,;)}\]]*)'
)
_REFERENCE = re.compile(r'^(?:<|\$|env\.|process\.env|os\.environ|import\.meta\.env|getenv)')
_PLACEHOLDER = re.compile(r'(?i)(your|change|example|xxx|placeholder|dummy|sample|fake|redacted|replace|todo|\.\.\.|\*\*\*)')

_TOKEN_SHAPES = [
    (re.compile(r'-----BEGIN (?:RSA |OPENSSH |EC |DSA |PGP |ENCRYPTED )?PRIVATE KEY-----'), 'private key'),
    (re.compile(r'\bAKIA[0-9A-Z]{16}\b'), 'AWS access key id'),
    (re.compile(r'\bsk-(?:ant-|proj-|live_|test_)?[A-Za-z0-9_\-]{24,}'), 'API key (sk-...)'),
    (re.compile(r'\bgh[pousr]_[A-Za-z0-9]{30,}'), 'GitHub token'),
    (re.compile(r'\bglpat-[A-Za-z0-9_\-]{20,}'), 'GitLab token'),
    (re.compile(r'\bxox[abprs]-[A-Za-z0-9-]{10,}'), 'Slack token'),
]
_BEARER = re.compile(r'(?i)Authorization:\s*Bearer\s+([A-Za-z0-9+/_\-=.]{20,})')
_URL_CREDS = re.compile(r'://[^/\s:@"\']+:([^@\s/"\']+)@')


def _is_literal_secret(value, next_char='', quoted=True):
    if len(value) < 12 or next_char == '(':
        return False
    # Unquoted code (calls, attribute access) is not a literal: password = hashlib.sha256(x)
    if not quoted and re.search(r'[.(]', value):
        return False
    if _REFERENCE.match(value) or _PLACEHOLDER.search(value):
        return False
    if len(set(value)) <= 3:
        return False
    return bool(re.search(r'[A-Za-z]', value) and re.search(r'[0-9]', value))


def scan_content(text):
    """Return a block reason or None."""
    if not text:
        return None
    for pattern, reason in _TOKEN_SHAPES:
        if pattern.search(text):
            return reason
    for m in _ASSIGN.finditer(text):
        if _is_literal_secret(m.group(2), text[m.end():m.end() + 1], quoted=bool(m.group(1))):
            return 'literal secret value assigned to a key'
    for m in _BEARER.finditer(text):
        if _is_literal_secret(m.group(1)):
            return 'Bearer token'
    for m in _URL_CREDS.finditer(text):
        pw = m.group(1)
        if len(pw) >= 6 and not _REFERENCE.match(pw) and not _PLACEHOLDER.search(pw) \
                and pw.lower() not in ('password', 'pass', 'postgres'):
            return 'password in URL'
    return None


# --- paths ---------------------------------------------------------------------------------

# The one list of protected paths. The project kit's permissions.deny and sandbox.filesystem.denyRead
# are generated from it (tests keep them in sync). Bare names match at any depth; "~/" is the home
# directory. .env stages are listed by name so that .env.example stays readable for every layer.
_ENV_STAGES = ('local', 'development', 'dev', 'production', 'prod', 'staging', 'stage', 'test', 'ci', 'preview')
PROTECTED = (
    ['.env'] + [f'.env.{s}' for s in _ENV_STAGES] + ['.env.*.local', '.secrets', '.secrets.*',
     '*.pem', '*.p12', '*.pfx', 'id_rsa', 'id_ed25519', 'id_ecdsa', 'id_dsa', '~/.ssh/**']
)


def read_rule(glob):
    """permissions.deny entry for a protected path (gitignore syntax, any depth under the project)."""
    return f'Read({glob})' if glob.startswith('~/') else f'Read(**/{glob})'


def sandbox_path(glob):
    """sandbox.filesystem.denyRead entry for a protected path ("./" = project root)."""
    return glob[:-3] if glob.startswith('~/') and glob.endswith('/**') else f'./**/{glob}'


_SAFE_ENV = re.compile(r'^\.env\.(?:example|sample|template|dist)$')
_ANY_ENV = re.compile(r'^\.env(?:\.[\w.-]+)?$')          # the hook also catches stages not listed above
_CODE_EXT = {'ts', 'tsx', 'js', 'jsx', 'mjs', 'cjs', 'py', 'rb', 'go', 'rs', 'java', 'kt', 'php', 'md'}
_NAME_GLOBS = [g for g in PROTECTED if not g.startswith('~/')]
_SSH_DIR = re.compile(r'(?:^|/)\.ssh/')


def _extra_globs():
    raw = os.environ.get('BRAIN_GUARD_SECRET_PATHS', '')
    return [g for g in raw.split(':') if g]


def _holds_private_key(path, cwd):
    """*.key is also the extension of ordinary text files: block only a file that holds a key."""
    try:
        with open(os.path.join(cwd or os.getcwd(), os.path.expanduser(path)), 'rb') as f:
            return b'PRIVATE KEY' in f.read(4096)
    except OSError:
        return False  # nothing there to leak


def is_secret_path(path, cwd=None):
    if not isinstance(path, str) or not path:
        return False
    full = os.path.expanduser(path)
    base = full.rstrip('/').rsplit('/', 1)[-1]
    if _SAFE_ENV.match(base):
        return False
    if _ANY_ENV.match(base) and base.rsplit('.', 1)[-1] not in _CODE_EXT:
        return True
    if any(fnmatch.fnmatchcase(base, g) for g in _NAME_GLOBS):
        return True
    if _SSH_DIR.search(full) and not base.endswith('.pub'):
        return True
    if base.endswith('.key') and _holds_private_key(path, cwd):
        return True
    return any(fnmatch.fnmatch(path, g) for g in _extra_globs())


# --- shell ---------------------------------------------------------------------------------

_SEP = re.compile(r'\|\||&&|[|;&\n]|\$\(|\)|`')
_DISPLAYERS = {'cat', 'less', 'more', 'head', 'tail', 'bat', 'strings', 'grep', 'egrep', 'rg', 'awk', 'sed',
               'nl', 'tac', 'diff', 'xxd', 'od', 'hexdump', 'base64', 'jq', 'cut', 'sort'}
# Commands that move a file's content somewhere else: any secret argument is a leak.
_MOVERS = {'scp', 'rsync', 'curl', 'wget', 'tar', 'zip', 'gzip', 'bzip2', 'xz', '7z', 'nc', 'ncat', 'socat', 'dd'}
_COPIERS = {'cp', 'install'}  # a secret source is a leak; a secret destination (cp .env.example .env) is not
_ANCHORED_KEY = r'["\']\^[A-Za-z0-9_]+=["\']'
_GREP_CHECK = re.compile(r'^grep\s+(?:-[A-Za-z]*\s+)*-[A-Za-z]*[qc][A-Za-z]*\s+(?:-[A-Za-z]+\s+)*' + _ANCHORED_KEY + r'\s+\S+$')
_INPUT_REDIRECT = re.compile(r'(?<![<0-9])<\s*([^\s<>|;&]+)')
_ENV_DUMPS = [
    (re.compile(r'(?:^|[;&|(`]\s*|\bsudo\s+)env(?:\s+-[0-9A-Za-z]+)*\s*(?:$|[|;&)`\'"])'), 'environment dump (env)'),
    (re.compile(r'\bprintenv\b(?!\s+[A-Za-z_][A-Za-z0-9_]*)'), 'printenv without a variable name'),
    (re.compile(r'\b(?:docker(?:\s+compose)?|docker-compose|podman)\s+(?:exec|run)\b[^|;&]*\s(?:env|printenv)\s*(?:$|[|;&)\'"])'), 'container environment dump'),
    (re.compile(r'\b(?:docker|podman)\s+(?:container\s+)?inspect\b(?![^|;&]*(?:--format|\s-f\b))'), 'docker inspect without --format (includes env)'),
    (re.compile(r'\bexport\s+-p\b'), 'export -p'),
    (re.compile(r'\bdeclare\s+-[A-Za-z]*p'), 'declare -p'),
    (re.compile(r'(?:^|[;&|(]\s*)set\s*(?:$|[|;&)])'), 'set (variable dump)'),
    (re.compile(r'/proc/[^\s/]+/environ'), '/proc/*/environ'),
]
_PRINTENV_VAR = re.compile(r'\bprintenv\s+[A-Za-z_][A-Za-z0-9_]*')


def _captured(cmd, pos):
    """True when pos is inside $( ... ): the output goes into a variable, not to the screen."""
    prefix = cmd[:pos]
    return prefix.count('$(') > prefix.count(')')


def _words(segment):
    """Shell words of one command, without leading sudo and VAR=value assignments."""
    try:
        words = shlex.split(segment)
    except ValueError:
        words = segment.split()
    while words and (words[0] == 'sudo' or re.match(r'^[A-Za-z_][A-Za-z0-9_]*=', words[0])):
        words.pop(0)
    return words


def _arg_paths(word):
    """A word and the file names it may carry: curl -F f=@.env, dd if=.env."""
    yield word
    for sep in ('@', '='):
        if sep in word:
            yield word.rsplit(sep, 1)[-1]


def _secret_args(args, cwd):
    return [a for a in args if not a.startswith('-') and any(is_secret_path(p, cwd) for p in _arg_paths(a))]


def _scan_segment(part, cwd):
    words = _words(part)
    if not words:
        return None
    cmd, args = words[0].rsplit('/', 1)[-1], words[1:]
    for m in _INPUT_REDIRECT.finditer(part):
        if is_secret_path(m.group(1), cwd):
            return 'feeding a secret file to a command'
    found = _secret_args(args, cwd)
    if not found:
        return None
    if cmd in _MOVERS:
        return 'copying a secret file out'
    if cmd in _COPIERS:
        positional = [a for a in args if not a.startswith('-')]
        return 'copying a secret file out' if any(a in found for a in positional[:-1]) else None
    if cmd not in _DISPLAYERS or _GREP_CHECK.match(part.strip()):
        return None
    if cmd == 'sed' and re.search(r'\s(?:-i\S*|--in-place)\b', part):
        return None  # in-place edit prints nothing
    return 'printing a secret file (use .env.example, or capture one value into a variable)'


def scan_bash(cmd, cwd=None):
    if not isinstance(cmd, str) or not cmd:
        return None
    for pattern, reason in _ENV_DUMPS:
        m = pattern.search(cmd)
        if m and not _captured(cmd, m.start()):
            return reason
    for m in _PRINTENV_VAR.finditer(cmd):
        if not _captured(cmd, m.start()) and re.search(r'(?i)(key|secret|token|pass|pwd)', m.group(0)):
            return 'printing a secret variable'
    pos = 0
    for part in _SEP.split(cmd):
        start = cmd.find(part, pos)
        pos = start + len(part) if start >= 0 else pos
        reason = _scan_segment(part, cwd)
        if reason and not (reason.startswith('printing') and _captured(cmd, max(start, 0))):
            return reason
    return None


# --- dispatch ------------------------------------------------------------------------------

def check(tool, ti, cwd=None):
    if tool in ('Write', 'Edit', 'MultiEdit', 'NotebookEdit'):
        parts = [ti.get('content'), ti.get('new_string'), ti.get('new_source')]
        edits = ti.get('edits')
        if isinstance(edits, list):
            parts += [e.get('new_string') for e in edits if isinstance(e, dict)]
        return scan_content('\n'.join(p for p in parts if isinstance(p, str)))
    if tool in ('Read', 'Grep', 'Glob'):
        for key in ('file_path', 'path'):
            if is_secret_path(ti.get(key), cwd):
                return 'reading a secret file'
        return None
    if tool == 'Bash':
        return scan_bash(ti.get('command'), cwd)
    return None


def main():
    try:
        data = json.load(sys.stdin)
        ti = data.get('tool_input') or {}
        if not isinstance(ti, dict):
            return 0
        cwd = data.get('cwd') if isinstance(data.get('cwd'), str) else None
        reason = check(data.get('tool_name') or '', ti, cwd)
    except Exception:
        return 0
    if reason:
        print(f'BLOCKED: blocked by secret_guard (brain-core): {reason}. '
              'Use an environment variable or a reference such as ${API_KEY} instead of the value.',
              file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
