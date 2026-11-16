Title: Add a per-task option to normalize typography like MarcEdit, on for imported tasks

Status: Ready
Size: S
Tier: normal — changes record output when enabled; format gains an optional task property
Milestone: M2 — Commands
Base: the local `main` commit that adds this ticket
Branch: codex/OMT-009

Why:
- Owner decision 2026-11-16 (coordination repo
  `docs/decisions/2026-11-16-typography-normalization-option.md`). On raw vendor
  records, MarcEdit (default settings) replaces curly quotes with straight quotes
  and em/en dashes with hyphens on output, including in subject headings. Five
  real tasks that match MarcEdit on processed records differ on raw ones only
  because of this. Imported tasks should behave like MarcEdit; new tasks should
  not silently change data.

Scope:
- Characterize with real MarcEdit first: which characters it replaces and with
  what. Probe at least “ ” ‘ ’ — – … and a no-break space (U+00A0), in a data
  field value and in a control field, in records a task changes and records it
  doesn't (in a file where something changed). Record the exact mapping in the spec.
- Task format: optional task-level property `normalize_typography` (boolean,
  default `false`). When `true`, `run_task` applies the observed mapping to every
  record, at the point MarcEdit does (before or after the steps — observe it; if
  it can't be told apart, apply it before steps, like backslash indicators).
- Importer: every imported task gets `"normalize_typography": true`.
- Spec ("Record handling") and schema updated; `format_version` stays `"0.1"`.
- Conformance: one case under `conformance/record_handling/` with the property
  `true` (expected output from `tools/marcedit_reference.py regenerate`), using
  synthetic records containing the probed characters.

Out of scope:
- Any other normalization, commands, the reference runner.

Likely files:
- open_marc_tasks/task.py, open_marc_tasks/marcedit_import.py
- spec/format.md, spec/task.schema.json
- conformance/record_handling/typography/…
- tests/test_task_loading.py, tests/test_marcedit_import.py (extend existing parametrized tests)

Acceptance tests:
- The new conformance case passes the suite and `tests/test_reference.py` on the
  host, so with the option on, output equals MarcEdit's for the probed characters.
- An existing conformance case without the property still passes, and one row in
  the existing loading parametrize shows a non-boolean `normalize_typography` is
  rejected by both loader and schema, so the default stays "don't change data".
- The importer's parametrized test shows imported documents carry
  `"normalize_typography": true`.

Verification:
- The Python 3.9 gate in AGENTS.md "Build and test".
- On the host from the worktree: `python3 -m pytest -q tests/test_reference.py`, counts reported.

Handoff:
- (orchestrator fills in after the check)

Review:
- (orchestrator fills in)
