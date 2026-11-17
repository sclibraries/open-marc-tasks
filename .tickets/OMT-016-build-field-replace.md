Title: Add build_field replace mode and import MarcEdit buildnewfield replace lines

Status: In-Progress
Size: S
Tier: normal — adds one mode to an existing command
Milestone: M2 — Commands
Base: the local `main` commit that adds this ticket
Branch: codex/OMT-016

Why:
- 30 `buildnewfield` lines use replace (`False|True|False|False`), split from
  OMT-015: new 001s (`=001  FCSAF{950$a}`, 24 lines), 003 (2), 035 rebuilt from
  itself (`=035  9\$a(UMACS){035$a}`) or another field (2), and 710 (`=710  2\$a{945$a}`, 2).

Observed with real MarcEdit 7.6 (orchestrator probes 2026-11-17, synthetic
records; `open-marc-tasks-coordination/runs/OMT-015/probes.md`):
- Every existing field with the template's tag is replaced in place by the
  built field; two 950s both become `$aNabc123`. If the tag is absent, nothing
  is added.
- Sources are read before any replacement: three 035s (`$z` only, `$a(A)1`,
  `$a(B)2`) rebuilt with `=035  \\$aN{035$a}` all become `$aN(A)1`.
- Control fields: 001 and 003 are replaced in place; an empty result replaces
  the field with empty data (`=003  {950$a}` without 950 → empty 003).
- A data-field result whose subfields are all empty: MarcEdit wrote no output
  for the whole file (exit 0), while the same line on a file where every record
  has the source works. The reference runner treats empty output as "no change",
  so this can't be a conformance case.

Design (the spec records it):
- `build_field` `mode` gains `"replace"`, with the OMT-015 placeholders,
  substitution and one-pass parsing. `[x]` with `replace` is rejected at load.
- Each field with the template's tag is replaced at its position by its own new
  field object (a later step editing one doesn't change the others).
- An all-empty data-field result in replace mode raises a run-time error naming
  the record and step, so `omt run` writes no output, like MarcEdit. Orchestrator's
  call; the spec says why.

Scope:
- `open_marc_tasks/commands/build_field.py`, the importer's replace branch,
  spec, schema, `ARCHITECTURE.md` status line.
- Conformance cases under `conformance/build_field/` (synthetic records,
  `expected.mrc` only from `tools/marcedit_reference.py regenerate`):
  replace on a repeated data field read from itself (including a field without
  the code); replace 001 from another field and 003 to empty; a record without
  the target tag.

Out of scope:
- f1, other flag combinations, other commands.

Likely files:
- open_marc_tasks/commands/build_field.py, open_marc_tasks/marcedit_import.py
- spec/format.md, spec/task.schema.json, ARCHITECTURE.md
- conformance/build_field/<case>/…
- tests/test_task_loading.py, tests/test_marcedit_import.py, tests/test_cli.py (extend existing parametrized tests)

Acceptance tests:
- Every new conformance case passes the suite and `tests/test_reference.py` on
  the host (not skipped), so replace placement, self-reads and control results match MarcEdit.
- The all-empty replace result raises an error naming record 2 and step 2
  through `run_task`, and `omt run` prints one `omt:` line and writes no output
  (extend the existing invalid-result parametrize from OMT-011).
- Separate field objects: a later `edit_subfield` step on the replaced fields
  changes each once (part of a conformance case, or one row in an existing test).
- The invalid-task parametrize: `[x]` with `replace` (loader, with the step
  number); `mode` `"replace"` now loads. The importer parametrize moves the
  replace form to translated (passes `load_task`).

Verification:
- The Python 3.9 gate in AGENTS.md "Build and test".
- On the host from the worktree: `python3 -m pytest -q tests/test_reference.py`, counts reported.
- The orchestrator reruns the private 100-task measurement after the check.

Handoff:
- (orchestrator fills in after the check)

Review:
- (orchestrator fills in)
