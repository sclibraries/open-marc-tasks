Title: Import empty-value SUBFIELD_REMOVE option 9 as no change, as MarcEdit does

Status: In-Progress
Size: S
Tier: normal — reverses an importer mapping (owner decision 2026-11-19)
Milestone: M2 — Commands
Base: the local `main` commit that adds this ticket
Branch: codex/OMT-030

Why:
- OMT-019 imports `SUBFIELD_REMOVE<TAB>945<TAB>b<TAB><TAB>9|0` (empty value,
  option 9) as "remove every `$b`", a documented difference from MarcEdit,
  which makes no change. Since OMT-028/029 the "Multiple FOLIO" tasks are
  measured in full: their 949s lose `$b` (barcode), `$m` (material type) and
  `$p` (holdings prefix), which MarcEdit keeps and the FOLIO job profile needs.
  Owner decision 2026-11-19: follow MarcEdit.

Scope:
- `open_marc_tasks/marcedit_import.py`: an empty-value `9|0` line produces no
  step and is not reported as not translated (it changes nothing in MarcEdit).
  `9|…` with a value stays not translated as today.
- `spec/format.md`: replace the "Difference from MarcEdit" paragraph with one
  sentence saying such a line imports as nothing because MarcEdit makes no change.
- `tools/measure.py`: remove the "deliberate: SUBFIELD_REMOVE option 9" label
  and its helper.
- `ARCHITECTURE.md` if it mentions the difference.

Out of scope:
- `remove_subfield` itself; other SUBFIELD_REMOVE options.

Likely files:
- open_marc_tasks/marcedit_import.py, tools/measure.py, spec/format.md, ARCHITECTURE.md
- tests/test_marcedit_import.py (change the existing `9|0` row; no new test function)

Acceptance tests:
- Importing a task whose lines are a translatable line plus
  `SUBFIELD_REMOVE<TAB>945<TAB>b<TAB><TAB>9|0` gives a complete task with only
  the other line's step and nothing not translated (the existing `9|0` row,
  changed to say so).
- `SUBFIELD_REMOVE<TAB>856<TAB>z<TAB>OCoLC<TAB>9|0` stays not translated.

Verification:
- The Python 3.9 gate in AGENTS.md "Build and test".
- The orchestrator reruns the private 100-task measurement after the check.

Handoff:
- (orchestrator fills in after the check)

Review:
- (orchestrator fills in)
