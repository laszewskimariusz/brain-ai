# Why v4: the measurements

v3 grew by addition: more personas, more indexes, more hooks. Before planning v4 we measured how the system was actually used over 60 days (110 main sessions, 553 subagent runs) and kept only what earned its cost.

## What the data said

**Subagents dominated cost.** They produced 80 % of cache-creation tokens and 76 % of output tokens. One implementation agent accounted for about 70 % of subagent cost, and 80 of its calls ran with the inherited (most expensive) model because the agent file did not pin one.
→ *Every agent pins its model. Reading, searching and implementing run on a mid-tier model; only architecture runs on the strongest one.*

**A third of the team never worked.** 6 of 18 personas had zero calls in 60 days. Research on persona prompts finds no gain in performance ([Zheng et al., arXiv:2311.10054](https://arxiv.org/abs/2311.10054)).
→ *7 role agents. Each file is a procedure, hard rules, a definition of done and a report format — no personality.*

**Custom machinery went unread.** The generated manifest and full-text index were read about 28 times in 60 days while being regenerated and validated about 44 times. Plain notes (infrastructure, index, topics) were read 100–190 times each.
→ *Removed the manifest, index and generator. Plain files and `grep`.*

**Instructions are not enforcement.** A hook that checked frontmatter format blocked 0 writes. The secret guard blocked 8.
→ *Keep the guard, drop the format hook. Guarantees come from hooks and `permissions.deny`, and the guard ships inside the plugin so every agent gets it.*

**Nobody worked inside project repos.** 0 sessions started in a project repo; all work began in the brain or the home directory, so every session loaded the brain's context.
→ *Each project gets its own kit and its own sessions. The brain coordinates.*

**Copies drifted.** Agents lived as files on several machines and in a repo that was months behind.
→ *One versioned plugin in one marketplace; every machine and project installs the same release.*

**Session start was heavy.** Two memories and a long `CLAUDE.md` loaded every time.
→ *One memory, a brain `CLAUDE.md` under 2 KB, lookups moved into skills. Context at session start: 81k → 40k tokens.*

## What v4 does not try to do

- Replace an issue tracker. The portfolio file lists projects; tasks live in your tracker.
- Run agents autonomously. The owner approves specs and anything irreversible.
