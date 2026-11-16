Title: Treat backslash indicators as blanks, as MarcEdit does

Status: Completed
Size: S
Tier: normal — changes record output; no new dependencies
Milestone: M2 — Commands
Base: the local `main` commit that adds this ticket
Branch: codex/OMT-006

Why:
- Owner decision 2026-11-16 (coordination repo
  `docs/decisions/2026-11-16-normalize-backslash-indicators.md`). Some exported
  records (seen in a FOLIO export: 49 fields in a 92-record sample) store a
  literal backslash as an indicator. MarcEdit writes those as blanks, so every
  task that touched those records "differed" from MarcEdit until normalized; with
  normalization all 5 fully translated real tasks match. Catalogers expect
  MarcEdit's output.

Scope:
- Characterize with real MarcEdit (reference runner) first:
  1. a record with backslash indicators that the task changes;
  2. a record with backslash indicators that the task does not change, in the
     same file as a record that is changed (MarcEdit writes an empty file only
     when nothing at all changed);
  3. whether a backslash inside a subfield value is left alone (expected: yes).
- `run_task`: apply the observed rule (most likely: every data field's
  backslash indicator becomes a blank, on every record, before the steps run, so
  conditions and "identical" checks see the normalized record). If MarcEdit only
  normalizes records it changed, follow that instead and say so.
- Spec: a short "Record handling" section stating the rule.
- One conformance case `conformance/record_handling/backslash-indicators/`
  covering 1–3 in one input file, `expected.mrc` from the reference runner.
  A `task.json` that deletes a tag present in only some records is enough.

Out of scope:
- Any other normalization, any command change, the importer.

Likely files:
- open_marc_tasks/task.py, spec/format.md
- conformance/record_handling/backslash-indicators/…

Acceptance tests:
- The new conformance case passes the suite and `tests/test_reference.py` on the
  host, so the library's output equals MarcEdit's for changed and unchanged
  records with backslash indicators.
- All existing tests pass unchanged.

Verification:
- The Python 3.9 gate in AGENTS.md "Build and test".
- On the host from the worktree: `python3 -m pytest -q tests/test_reference.py`, counts reported.

Handoff:
- Head 3fbdfd8, merged into main (owner OK 2026-11-16). Python 3.9 gate 53 passed, 1 skipped; host reference passed. Real-data measure 5/100.

Review:
- MarcEdit blanks backslash indicators on every record, changed or not; subfield values untouched. No fix round.
