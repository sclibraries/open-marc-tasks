Title: Import SUBFIELD_REMOVE option 9 with an empty value as remove-all, and reject control-to-control copy_field

Status: Completed
Size: S
Tier: normal — importer mapping (owner decision) plus one load-time rejection
Milestone: M2 — Commands
Base: the local `main` commit that adds this ticket
Branch: codex/OMT-019

Why:
- Owner decision 2026-11-17 (`open-marc-tasks-coordination/docs/decisions/2026-11-17-subfield-remove-option-9.md`):
  32 UMass "Multiple FOLIO" lines `SUBFIELD_REMOVE 945 b|m|p <empty> 9|0` are
  meant to remove the barcode, material type and holdings prefix from each 945
  before the 946–949 copies are built. The MarcEdit 7.6 command-line version
  changes nothing for them (option 9 keeps the first subfield containing the
  value and removes later ones; an empty value matches nothing). The format
  follows the cataloger's intent, as a documented difference.
- OMT-018 review: `copy_field` runs a control-to-control copy that the importer
  never emits and no MarcEdit case covers.

Scope:
- Importer: `SUBFIELD_REMOVE` with an empty value and option `9|0` →
  `remove_subfield` with no filter. Option `9|…` with a non-empty value stays not
  translated ("option 9 with a value is not supported").
- `spec/format.md`: a "Differences from MarcEdit" note for this mapping (next to
  the existing `{dollar}` and byte-level notes), with the reason in one or two sentences.
- `tools/measure.py`: a task that differs from MarcEdit and whose source contains
  a `SUBFIELD_REMOVE` line with an empty value and option `9|0` prints
  `differs (deliberate: SUBFIELD_REMOVE option 9)` instead of `differs`; it still
  doesn't count as a match.
- `copy_field`: reject a control-to-control copy at load with the step number,
  and remove its run branch.

Out of scope:
- Option 9 with a value, other commands.

Likely files:
- open_marc_tasks/marcedit_import.py, open_marc_tasks/commands/copy_field.py
- spec/format.md, tools/measure.py
- tests/test_marcedit_import.py, tests/test_task_loading.py (extend parametrized tests)

Acceptance tests:
- The importer parametrize moves `SUBFIELD_REMOVE\t945\tb\t\t9|0` to translated
  (`remove_subfield`, tag 945, code b, no filter; passes `load_task`) and keeps
  `9|0` with a value not translated.
- The invalid-task parametrize gains a control-to-control `copy_field`
  (loader and schema if the schema can express it, otherwise loader only, with the step number).
- Existing copy_field and remove_subfield conformance cases pass unchanged.
- The measure label is not unit-tested (private tool); the orchestrator checks it in the measurement run.

Verification:
- The Python 3.9 gate in AGENTS.md "Build and test".
- The orchestrator reruns the private 100-task measurement after the check.

Handoff:
- Head 42e331b, merged into main (owner OK 2026-11-17). Python 3.9 gate 185 passed, 1 skipped. Measure 26/100 on all three samples.

Review:
- Empty option 9 → remove-all with a documented difference; copy_field control→control rejected; measure labels deliberate differences. No fix round.
