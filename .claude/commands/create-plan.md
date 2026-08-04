---
description: Read a spec file and write a detailed implementation plan into .claude/plans/
argument-hint: "<spec_file_name> e.g. 03-login-logout.md"
allowed-tools: Read, Write, Glob, Bash(git:*)
---

You are a senior developer turning a finished Spendwise spec
into a concrete, ordered implementation plan. Always follow
the rules in CLAUDE.md.

User input: $ARGUMENTS

## Step 1 — Resolve the spec file

Treat $ARGUMENTS as the spec filename. Accept either:
- A bare filename: `03-login-logout.md`
- A path relative to `.claude/specs/`: `specs/03-login-logout.md`

Look it up under `.claude/specs/<spec_file_name>`. If the
file does not exist, stop and say:
"No spec found at `.claude/specs/<spec_file_name>`.
Run /create-spec first or check the filename."

If multiple paths are possible, pick the first match under
`.claude/specs/`. Do not proceed without a readable spec.

## Step 2 — Confirm working directory is clean

Run `git status`. If there are uncommitted, unstaged, or
untracked files (other than `.claude/plans/` itself, which
is gitignored per CLAUDE.md), stop and tell the user to
commit or stash before proceeding. Plans are scratch work —
they should not be written on top of in-flight code.

## Step 3 — Detect existing plan

Check if `.claude/plans/<spec_file_name>` already exists.

- If it does: stop and ask the user "A plan already exists
  at `.claude/plans/<spec_file_name>`. Overwrite, or cancel?"
  Do not proceed without an answer.
- If it does not: continue.

## Step 4 — Read the spec end to end

Read `.claude/specs/<spec_file_name>` completely before
writing anything. Note every:
- Route (method, path, access level)
- Database change (new tables, columns, helpers, indexes)
- Template change (create / modify)
- File change and file create
- New dependency
- Rule or constraint
- Item in the Definition of done

Treat each section as a checklist. The plan must produce
code that satisfies every bullet.

## Step 5 — Read supporting files

Before writing the plan, read:
- `CLAUDE.md` — for conventions (port 5001, CSS variables,
  `url_for` over hardcoded paths, no SQLAlchemy, parameterised
  queries, werkzeug password hashing, `app.py` extension
  pattern).
- `app.py` — for existing imports, route style, and to avoid
  duplicating helpers already wired.
- `database/db.py` — for the existing `get_db()` / `init_db()`
  / `seed_db()` interface and any helpers the spec refers to.
- `templates/base.html` — for the navbar, footer, block
  regions (`{% block content %}`, `{% block head %}`,
  `{% block scripts %}`) and any shared styling.
- The most recent plan in `.claude/plans/` (if any) — match
  its tone, heading depth, and code-block style so plans
  read as one series.

## Step 6 — Write the plan

Write the plan to `.claude/plans/<spec_file_name>` (same
filename as the spec). Use this exact structure:

---
# Implementation Plan: <Feature Title> (Step <NN>)

## Context

2–4 sentences. State what step this is, what previous step
it builds on, and what user-visible change the implementation
produces. Mention the branch name (infer from spec filename
or `feature/<feature-slug>`) and confirm the working tree
is clean. Reference the spec file path.

## Reusable utilities already present

Bullet list of helpers, files, CSS classes, Jinja blocks, or
DB helpers that already exist and that this step will reuse
instead of creating new ones. Pulled from CLAUDE.md,
`database/db.py`, `app.py`, `templates/base.html`, and
`static/css/style.css`.

## Files to change

For every file the spec lists under "Files to change" or
"Files to create", produce one sub-section. Each sub-section
opens with the file path as a heading, then:

- **Imports** — show exact `from X import Y` lines to add or
  modify. Quote current imports if a line needs merging.
- **Code** — show the smallest correct code block that, when
  pasted in, produces the spec's behaviour. Use `python`,
  `html`, `jinja`, or `bash` fences tagged appropriately.
  Mark new code clearly. Where the spec is ambiguous, pick
  the option that matches the existing codebase's style and
  explain the choice in one sentence after the block.
- **Why** — one sentence explaining what spec bullet this
  satisfies and any constraint (e.g. "matches the flash
  block in `register.html` per spec rule").

For modify-only files (no new files), use the same shape so
the reader sees the *delta*, not the whole file.

## Files to create

List every new file the spec calls for, with a one-paragraph
description of its purpose and its full path. If the spec
says no new files, state "None."

## New dependencies

List any pip packages to add. If the spec says none, write
"No new dependencies." If something is added, show the exact
`pip install` line and which `requirements.txt` entry to
append.

## Ordered build steps

A numbered list. Each step is one focused, verifiable
change that maps to one or more bullets in the spec. Order
matters — earlier steps unblock later ones. For each step:

1. **What to do** — one sentence.
2. **Where** — file path + section.
3. **Verify** — a manual or test command that proves the
   step worked (e.g. `pytest -k test_login`,
   `curl -i http://localhost:5001/login`,
   "open `/login` in the browser and confirm…").

Typical order: DB helpers first, then `app.py` route
handlers, then templates, then static assets, then the
manual end-to-end check that mirrors the spec's Definition
of done.

## Definition of done — how we verify it

A copy of the spec's Definition of done list, with each
item annotated by *how* to verify it (which command, which
URL, which file to read). The annotations turn a checklist
into a runnable script.

## Open questions

Any ambiguity you resolved with a default. One line per
question: "Spec said X → assumed Y because Z. Confirm?"
If there are none, write "None."
---

Rules for the plan itself:
- Use `python`, `html`, `jinja`, or `bash` fenced code blocks
  with a language tag.
- Reference existing code by `file:line` where it helps the
  reader.
- Do not invent routes, columns, or files that are not in
  the spec.
- Do not include the full spec — link to it instead.

## Step 7 — Save the plan

Write the file to `.claude/plans/<spec_file_name>` (no
`step-number-` prefix is added; the spec filename already
includes it, e.g. `03-login-logout.md` → `.claude/plans/03-login-logout.md`).

If the target directory `.claude/plans/` does not exist,
create it before writing.

## Step 8 — Report to the user

Print a short summary in this exact format:
```
Spec file: .claude/specs/<spec_file_name>
Plan file: .claude/plans/<spec_file_name>
Steps:     <count of "Ordered build steps">
```

Then tell the user:
"Review the plan at `.claude/plans/<spec_file_name>` then
begin implementation. The build steps in §"Ordered build
steps" are the suggested order — adjust if a step turns
out to depend on something earlier in the file."

Do not print the full plan in chat unless explicitly asked.
