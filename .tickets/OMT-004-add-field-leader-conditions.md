Title: Add the add_field command with MarcEdit's placement, its skip options and Leader conditions

Status: In-Progress
Size: M
Tier: normal — new command behavior; no new dependencies
Milestone: M2 — Commands
Base: the local `main` commit that adds this ticket
Branch: codex/OMT-004

Why:
- `ADD` is the most common MarcEdit command in the Smith and UMass task files
  (809 lines): 528 add only when the Leader matches (option 106), 264 always add
  (100), 11 use option 108 and 6 use option 101. Every 106 condition in those
  files tests Leader/06 or Leader/07 against a set of letters, for example
  `/=LDR.{8}[amt][m].+/` (06 in a,m,t and 07 = m) or `/=LDR.{9}s.+/` (07 = s).
  Without `add_field` almost no real task can run.
- MarcEdit puts an added field in a specific place (observed 2026-11-13: five
  ADDs of 506 came out in reverse order, so each is inserted before existing
  506s). Catalogers' records must come out the same.

Scope:
- `add_field` command, settings:
  - `tag` (three digits). Data field: `ind1`, `ind2` (one character each, space
    allowed) and `subfields` (non-empty array of `[code, value]`, code one
    lowercase letter or digit). Control field (00X): `data` (string) instead.
  - `if_tag_exists`: `"add"` (default; MarcEdit 100), plus the behaviors of
    MarcEdit options 101 and 108, named in plain English after you've observed
    what MarcEdit does with each (for example `"skip"`, `"skip_if_identical"`).
  - `when` (optional): array of conditions, all must hold. This ticket defines
    one condition kind: `{"leader": <position 0–23>, "in": [<one-character strings>]}`.
    Conditions are a reusable part of the format (later commands use them), so
    the spec gives them their own section.
- Placement: wherever MarcEdit puts the new field, for the cases below.
  Characterize with real MarcEdit first; the spec states the rule you observe.
- `open_marc_tasks/task.py`: replace the hardcoded `delete_field` checks with a
  small per-command table (name → settings validator, function), as
  ARCHITECTURE.md notes is due with the second command. No other refactor.
- Spec and schema sections for `add_field` and conditions.
- Conformance cases under `conformance/add_field/`, synthetic records, each with
  `marcedit-task.txt` and `expected.mrc` produced by
  `tools/marcedit_reference.py regenerate` (never by this library):
  1. always add, tag absent (where does it go among other tags?);
  2. always add, tag present (before or after the existing same-tag fields?), with
     two ADD steps for the same tag to show the order;
  3. option 101 with the tag present and absent;
  4. option 108 with an identical field present and with a different one;
  5. Leader condition true and false in one input file (06 in a,m,t and 07 = m;
     and 07 = s), using MarcEdit's own regex form in `marcedit-task.txt`;
  6. a control-field add (for example 006) if MarcEdit's ADD supports it; if it
     doesn't, leave control fields out of `add_field` and say so.
  MarcEdit task line shape (from the task files): `ADD<TAB>506<TAB>1\$aText$5MU<TAB>100<TAB>`;
  with a condition: `ADD<TAB>655<TAB>\7$aText.$2local<TAB>106<TAB>/=LDR.{8}[amt][m].+/`.
  In MarcEdit's field text `\` is a blank indicator and `$` starts a subfield.

Out of scope:
- The importer, other condition kinds (008, field values), regex conditions,
  other commands.

Likely files:
- open_marc_tasks/task.py, open_marc_tasks/commands/add_field.py,
  open_marc_tasks/conditions.py
- spec/format.md, spec/task.schema.json
- conformance/add_field/<case>/…
- tests/test_task_loading.py (extend the existing parametrized invalid-task test)

Acceptance tests:
- Every `add_field` case passes the conformance suite and `tests/test_reference.py`
  on the host, so placement, skip options and conditions match MarcEdit.
- The existing parametrized invalid-task test gains `add_field` cases (missing
  `subfields`, bad indicator length, bad subfield code, unknown `if_tag_exists`,
  a condition with position 24 or an empty `in`), and both `load_task` and the
  JSON Schema reject each, so the spec and the library stay aligned.
- All existing tests still pass unchanged, so the command-table refactor breaks nothing.

Verification:
- The Python 3.9 gate in AGENTS.md "Build and test".
- On the host from the worktree: `python3 -m pytest -q tests/test_reference.py`, counts reported.

Handoff:
- (orchestrator fills in after the check)

Review:
- (orchestrator fills in)
