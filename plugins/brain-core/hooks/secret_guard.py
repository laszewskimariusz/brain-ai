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

It never echoes the matched value. Unreadable input is allowed with a one-line warning; an
internal error while checking a covered tool blocks (fails closed).
"""
import fnmatch
import json
import os
import re
import shlex
import stat
import sys

# --- file contents -------------------------------------------------------------------------

_KEYWORD = r'(?:api[_-]?key|apikey|secret(?:[_-]?key)?|client[_-]?secret|access[_-]?token|auth[_-]?token|token|password|passwd|pwd)'
_ASSIGN = re.compile(
    r'(?i)(?<![A-Za-z0-9_])[A-Za-z0-9_]{0,64}?' + _KEYWORD + r'["\']?\s*[:=]\s*(["\'`]?)([^\s"\'`,;)}\]]*)'
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
_URL_CREDS = re.compile(r'://[^/\s:@"\']*:([^@\s/"\']+)@')  # user may be empty: redis://:pw@host


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
# Credential stores that git, psql and cloud CLIs read themselves: denied to Claude's file tools and the
# hook, but not hidden from the sandbox, where those programs need them.
CREDENTIAL_FILES = ['.netrc', '.pgpass', '.git-credentials', '~/.aws/credentials']


def read_rule(glob):
    """permissions.deny entry for a protected path (gitignore syntax, any depth under the project)."""
    return f'Read({glob})' if glob.startswith('~/') else f'Read(**/{glob})'


def sandbox_path(glob):
    """sandbox.filesystem.denyRead entry for a protected path ("./" = project root)."""
    if glob.startswith('~/'):
        return glob[:-3] if glob.endswith('/**') else glob
    return f'./**/{glob}'


_SAFE_ENV = re.compile(r'^\.env\.(?:example|sample|template|dist)$')
_ANY_ENV = re.compile(r'^\.env(?:\.[\w.-]+)?$')          # the hook also catches stages not listed above
_CODE_EXT = {'ts', 'tsx', 'js', 'jsx', 'mjs', 'cjs', 'py', 'rb', 'go', 'rs', 'java', 'kt', 'php', 'md'}
_NAME_GLOBS = [g for g in PROTECTED + CREDENTIAL_FILES if not g.startswith('~/')]
_HOME_FILES = [g[1:] for g in CREDENTIAL_FILES if g.startswith('~/')]   # matched as a path suffix
_EXAMPLES = [g.replace('*', 'x') for g in _NAME_GLOBS]
_SSH_DIR = re.compile(r'(?:^|/)\.ssh(?:/|$)')
_PROC_ENVIRON = re.compile(r'^/proc/[^/]+/environ$')
_GLOB_CHARS = re.compile(r'[*?\[\]]')


def _extra_globs():
    raw = os.environ.get('BRAIN_GUARD_SECRET_PATHS', '')
    return [g for g in raw.split(':') if g]


def _holds_private_key(path, cwd, unresolved=False):
    """*.key is also the extension of ordinary text files: block only a file that holds a key.

    unresolved: the answer for a file the hook cannot find (a variable in the path, a cd earlier in
    the command). Read passes it (nothing to leak); Bash blocks it.
    """
    if unresolved and path.startswith('.') and '/' not in path:
        unresolved = False  # a jq filter such as .data.key, not a file
    if '$' in path:
        return unresolved
    full = os.path.join(cwd or os.getcwd(), os.path.expanduser(path))
    try:
        if not stat.S_ISREG(os.stat(full).st_mode):
            return False  # FIFOs and devices would hang the hook
        fd = os.open(full, os.O_RDONLY | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as f:
            return b'PRIVATE KEY' in f.read(65536)
    except FileNotFoundError:
        return unresolved
    except OSError:
        return False


def _glob_may_hit(full, base):
    """A shell or Grep glob that could expand to a protected name (.env*, *.pem), not just any glob (*)."""
    if _SSH_DIR.search(full):
        return True
    literal = _GLOB_CHARS.sub('', base)
    return bool(literal.strip('.')) and any(fnmatch.fnmatchcase(e, base) for e in _EXAMPLES)


def is_secret_path(path, cwd=None, unresolved_key=False):
    if not isinstance(path, str) or not path:
        return False
    full = os.path.expanduser(path)
    base = full.rstrip('/').rsplit('/', 1)[-1]
    if _GLOB_CHARS.search(full):
        return _glob_may_hit(full, base)
    if _PROC_ENVIRON.match(full) or any(full.endswith(h) for h in _HOME_FILES):
        return True
    if _SAFE_ENV.match(base):
        return False
    if _ANY_ENV.match(base) and base.rsplit('.', 1)[-1] not in _CODE_EXT:
        return True
    if any(fnmatch.fnmatchcase(base, g) for g in _NAME_GLOBS):
        return True
    if _SSH_DIR.search(full) and not base.endswith('.pub'):
        return True
    if base.endswith('.key') and _holds_private_key(path, cwd, unresolved_key):
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


_ASSIGNED = re.compile(r'(?:^|[\s;&|(])(?:export\s+|local\s+|readonly\s+)?[A-Za-z_]\w*="?$')


def _captured(cmd, pos):
    """True when pos is inside NAME=$( ... ): the output goes into a variable, not to the screen.

    Only an assignment counts: in echo $(cat .env) or curl -d "$(cat .env)" the outer command
    prints or sends the value.
    """
    prefix = cmd[:pos]
    if prefix.count('$(') <= prefix.count(')'):
        return False
    return bool(_ASSIGNED.search(prefix[:prefix.rfind('$(')]))


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


# Options whose value is not a file the command reads out: --exclude .env, curl --cacert ca.pem, scp -i key.
_VALUE_OPTS = {'rsync': {'--exclude', '--exclude-from', '--include', '-e'}, 'tar': {'--exclude', '-X', '--exclude-from'},
               'zip': {'-x'}, 'curl': {'--cacert', '--cert', '--key', '--capath', '-E'}, 'scp': {'-i', '-F'},
               'grep': {'--exclude', '--exclude-from', '--include'}, 'rg': {'-g', '--glob', '--iglob'}}


def _operands(cmd, args):
    out, skip = [], False
    for a in args:
        if skip:
            skip = False
        elif a in _VALUE_OPTS.get(cmd, ()):
            skip = True
        elif not a.startswith('-'):
            out.append(a)
    return out


def _secret_args(operands, cwd):
    return [a for a in operands if any(is_secret_path(p, cwd, unresolved_key=True) for p in _arg_paths(a))]


def _scan_segment(part, cwd):
    words = _words(part)
    if not words:
        return None
    cmd, args = words[0].rsplit('/', 1)[-1], words[1:]
    for m in _INPUT_REDIRECT.finditer(part):
        if is_secret_path(m.group(1), cwd):
            return 'feeding a secret file to a command'
    operands = _operands(cmd, args)
    found = _secret_args(operands, cwd)
    if not found:
        return None
    if cmd in _MOVERS:
        return 'copying a secret file out'
    if cmd in _COPIERS:
        return 'copying a secret file out' if any(a in found for a in operands[:-1]) else None
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


# --- read-only agents ----------------------------------------------------------------------

# Agents whose prompts say "read-only". Plugin subagents report agent_type as "brain-core:<name>".
READ_ONLY_AGENTS = {'reviewer', 'security', 'researcher'}
_WRITE_TOOLS = ('Write', 'Edit', 'MultiEdit', 'NotebookEdit')
_WRITE_CMDS = {'rm', 'rmdir', 'unlink', 'shred', 'mv', 'cp', 'install', 'ln', 'truncate', 'dd', 'touch', 'mkdir',
               'mkfifo', 'mknod', 'chmod', 'chown', 'chgrp'}
_GIT_WRITE = {'commit', 'push', 'pull', 'reset', 'checkout', 'switch', 'merge', 'rebase', 'apply', 'am',
              'cherry-pick', 'revert', 'restore', 'clean', 'add', 'rm', 'mv'}
_GIT_OPTS_WITH_ARG = {'-C', '-c', '--git-dir', '--work-tree', '--namespace'}
_PKG_WRITE = {'install', 'i', 'ci', 'add', 'remove', 'rm', 'uninstall', 'un', 'update', 'up', 'upgrade', 'link',
              'publish', 'sync'}
_PKG_TOOLS = {'npm', 'pnpm', 'yarn', 'bun', 'pip', 'pip3', 'uv', 'poetry'}
# Wrappers that run the command after them, with the options that take a value.
_WRAPPERS = {'sudo': {'-u', '-g', '-C', '-D', '-h', '-p', '-R', '-r', '-t', '-U'},
             'env': {'-u', '-C', '-S', '--unset', '--chdir', '--split-string'},
             'nice': {'-n', '--adjustment'}, 'timeout': {'-s', '-k', '--signal', '--kill-after'},
             'time': {'-f', '-o'}, 'nohup': set(), 'command': set()}
_SAFE_TARGETS = {'/dev/null', '/dev/stdout', '/dev/stderr', '-'}
_PUNCT = set(';|&()<>')
# Operator characters inside quotes or after a backslash are text, not shell syntax.
_MASK = {c: chr(0xE000 + i) for i, c in enumerate(sorted(_PUNCT))}
_UNMASK = str.maketrans({v: k for k, v in _MASK.items()})


def is_read_only_agent(agent):
    if not isinstance(agent, str):
        return False
    return agent in READ_ONLY_AGENTS or (agent.startswith('brain-core:') and agent[11:] in READ_ONLY_AGENTS)


def _mask_quoted(cmd):
    out, quote, escaped = [], None, False
    for c in cmd:
        if escaped:
            out.append(_MASK.get(c, c))
            escaped = False
        elif c == '\\' and quote != "'":
            out.append(c)
            escaped = True
        elif quote:
            if c == quote:
                quote = None
            out.append(_MASK.get(c, c))
        else:
            if c in '"\'':
                quote = c
            out.append(c)
    return ''.join(out)


def _shell_tokens(cmd):
    """Shell words and operators; operator characters from quoted text stay masked."""
    masked = _mask_quoted(cmd.replace('\n', ';'))
    lex = shlex.shlex(masked, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    try:
        return list(lex)
    except ValueError:
        return masked.split()


def _strip_wrappers(words):
    while words:
        w = words[0]
        name = w.rsplit('/', 1)[-1]
        if re.match(r'^[A-Za-z_][A-Za-z0-9_]*=', w):
            words = words[1:]
            continue
        if name not in _WRAPPERS:
            break
        if name == 'command' and words[1:2] and words[1] in ('-v', '-V'):
            return []  # command -v only looks the name up
        words = words[1:]
        while words and words[0].startswith('-') and words[0] != '-':
            words = words[2:] if words[0] in _WRAPPERS[name] else words[1:]
        if name == 'timeout' and words:
            words = words[1:]  # the duration
    return words


def _option_value(args, short, longs):
    """Values given to an option: -o f, -sSLo f, -of, --output f, --output=f."""
    values = []
    for i, a in enumerate(args):
        nxt = args[i + 1] if i + 1 < len(args) else ''
        if a in longs:
            values.append(nxt)
        elif any(a.startswith(f'{o}=') for o in longs):
            values.append(a.split('=', 1)[1])
        elif re.match(r'^-[A-Za-z]', a) and short in a[1:]:
            i = a.index(short, 1)
            if re.fullmatch(r'[A-Za-z]*', a[1:i]):  # flags before it: -sSLo f, -qO-
                values.append(a[i + 1:] or nxt)
    return values


def _git_write(sub, rest):
    """git subcommands that only change state in some forms."""
    pos = [a for a in rest if not a.startswith('-')]
    flags = set(a.split('=', 1)[0] for a in rest if a.startswith('-'))
    if sub == 'stash':
        return not pos or pos[0] not in ('list', 'show')
    if sub == 'worktree':
        return not pos or pos[0] != 'list'
    if sub == 'tag':
        listing = flags & {'-l', '--list', '-n', '--contains', '--no-contains', '--points-at', '--merged',
                           '--no-merged', '-v', '--verify'}
        return bool(flags & {'-d', '--delete', '-a', '--annotate', '-s', '--sign', '-f', '--force', '-m', '-F',
                             '-u'}) or bool(pos and not listing)
    if sub == 'branch':
        listing = flags & {'-l', '--list', '-a', '--all', '-r', '--remotes', '--contains', '--no-contains',
                           '--merged', '--no-merged', '--points-at', '-v', '-vv', '--verbose', '--show-current'}
        return bool(flags & {'-d', '-D', '--delete', '-m', '-M', '--move', '-c', '-C', '--copy', '-u',
                             '--set-upstream-to', '--unset-upstream', '--edit-description', '-f', '--force'}) \
            or bool(pos and not listing)
    if sub == 'config':
        if pos and pos[0] in ('set', 'unset', 'rename-section', 'remove-section', 'edit'):
            return True
        if pos and pos[0] in ('get', 'list'):
            return False
        if flags & {'--unset', '--unset-all', '--add', '--replace-all', '--rename-section', '--remove-section',
                    '-e', '--edit'}:
            return True
        return not flags & {'--get', '--get-all', '--get-regexp', '--get-urlmatch', '-l', '--list'} and len(pos) >= 2
    return False


def _first_arg(args, with_value=()):
    """First argument that is not an option (skipping the values of options that take one)."""
    skip = False
    for a in args:
        if skip:
            skip = False
        elif a in with_value:
            skip = True
        elif not a.startswith('-'):
            return a
    return None


def _writing_command(words):
    """What a single command would change, or None."""
    words = _strip_wrappers(words)
    if not words:
        return None
    cmd, args = words[0].rsplit('/', 1)[-1], words[1:]
    if cmd in ('bash', 'sh', 'zsh', 'dash') and '-c' in args[:-1]:
        return _writing_shell(args[args.index('-c') + 1])
    if cmd == 'xargs':
        rest = args
        while rest and rest[0].startswith('-'):
            rest = rest[2:] if rest[0] in ('-I', '-n', '-P', '-L', '-d', '-a', '-E', '-s') else rest[1:]
        return _writing_command(rest)
    if cmd in _WRITE_CMDS:
        return f'run {cmd}'
    if cmd == 'tee' and any(a not in _SAFE_TARGETS for a in args if not a.startswith('-')):
        return 'write files with tee'
    if cmd == 'curl' and (any(re.match(r'^-[A-Za-z]*O', a) or a in ('--remote-name', '--remote-name-all')
                              for a in args) or any(
            v not in _SAFE_TARGETS for v in _option_value(args, 'o', ('--output',)) + _option_value(
                args, 'D', ('--dump-header',)) + _option_value(args, 'c', ('--cookie-jar',)))):
        return 'download into a file'
    if cmd == 'wget' and '--spider' not in args and not any(
            v in _SAFE_TARGETS for v in _option_value(args, 'O', ('--output-document',))):
        return 'download into a file'
    if cmd == 'sed' and any(a.startswith('-i') or a == '--in-place' for a in args):
        return 'edit files in place'
    if cmd == 'perl' and any(re.match(r'^-\w*i', a) for a in args):
        return 'edit files in place'
    if cmd == 'find':
        if any(a in ('-delete', '-fprint', '-fprintf', '-fls') for a in args):
            return 'delete or write files with find'
        for i, a in enumerate(args[:-1]):
            if a in ('-exec', '-execdir', '-ok', '-okdir') and args[i + 1].rsplit('/', 1)[-1] in _WRITE_CMDS:
                return f'run {args[i + 1]} through find'
    if cmd == 'git':
        sub = _first_arg(args, _GIT_OPTS_WITH_ARG)
        rest = args[args.index(sub) + 1:] if sub else []
        if sub in _GIT_WRITE or _git_write(sub, rest):
            return f'run git {sub}'
    if re.match(r'^python[0-9.]*$', cmd) and args[:2] == ['-m', 'pip']:
        cmd, args = 'pip', args[2:]
    if cmd in _PKG_TOOLS:
        sub = _first_arg(args)
        if cmd == 'uv' and sub == 'pip':
            sub = _first_arg(args[args.index('pip') + 1:])
        if sub in _PKG_WRITE or (cmd == 'yarn' and sub is None):
            return f'change dependencies ({cmd} {sub or "install"})'
    return None


def _writing_shell(cmd):
    tokens = _shell_tokens(cmd)
    words = []
    for i, t in enumerate(tokens):
        if t and set(t) <= _PUNCT and '>' in t:
            nxt = tokens[i + 1] if i + 1 < len(tokens) else ''
            if not ((t.endswith('&') and re.match(r'^(?:\d+|-)$', nxt)) or nxt in _SAFE_TARGETS):
                return 'redirect output into a file'
            continue
        if t and set(t) <= _PUNCT:
            reason = _writing_command(words)
            if reason:
                return reason
            words = []
        elif t != '$':
            words.append(t.translate(_UNMASK))
    return _writing_command(words)


def check_read_only(tool, ti):
    if tool in _WRITE_TOOLS:
        return f'{tool} is not available to a read-only agent'
    if tool == 'Bash' and isinstance(ti.get('command'), str):
        what = _writing_shell(ti['command'])
        return f'a read-only agent cannot {what}' if what else None
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
        for key in ('file_path', 'path', 'glob'):
            if is_secret_path(ti.get(key), cwd):
                return 'reading a secret file'
        return None
    if tool == 'Bash':
        return scan_bash(ti.get('command'), cwd)
    return None


_KNOWN_TOOLS = {'Write', 'Edit', 'MultiEdit', 'NotebookEdit', 'Read', 'Grep', 'Glob', 'Bash'}
_PREFIX = 'BLOCKED: blocked by secret_guard (brain-core): '


def _decide(data):
    """(exit code, message) for one hook event."""
    ti = data.get('tool_input') or {}
    tool = data.get('tool_name')
    if not isinstance(tool, str) or not tool or not isinstance(ti, dict):
        return 0, 'secret_guard (brain-core): unreadable hook input, allowed without a check'
    if tool not in _KNOWN_TOOLS:
        return 0, None
    cwd = data.get('cwd') if isinstance(data.get('cwd'), str) else None
    try:
        reason = check(tool, ti, cwd)
        if reason:
            return 2, (f'{_PREFIX}{reason}. '
                       'Use an environment variable or a reference such as ${API_KEY} instead of the value.')
        if is_read_only_agent(data.get('agent_type')):
            reason = check_read_only(tool, ti)
            if reason:
                return 2, (f'{_PREFIX}{reason} (read-only role). '
                           'Report the change you would make; the developer agent applies it.')
    except Exception:
        # A bug in a scanner must not turn into a silent pass for a tool the guard covers.
        return 2, f'{_PREFIX}internal error, failing closed. Retry differently or report a guard bug.'
    return 0, None


def main():
    try:
        data = json.loads(sys.stdin.read())
    except Exception:  # not JSON, not text, nested too deep
        data = None
    if not isinstance(data, dict):
        code, msg = 0, 'secret_guard (brain-core): unreadable hook input, allowed without a check'
    else:
        code, msg = _decide(data)
    if msg:
        print(msg, file=sys.stderr)
    return code


if __name__ == '__main__':
    sys.exit(main())
