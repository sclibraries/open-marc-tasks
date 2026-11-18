Title: Add set_indicators and import MarcEdit INDICATOR

Status: In-Progress
Size: S
Tier: normal — new command
Milestone: M2 — Commands
Base: the local `main` commit that adds this ticket
Branch: codex/OMT-027

Why:
- `INDICATOR` has 4 lines and is the only untranslated command in 3 tasks:
  `INDICATOR<TAB>024<TAB>\<TAB><TAB>8`, `INDICATOR<TAB>856<TAB><TAB><TAB>40`,
  `INDICATOR<TAB>035<TAB>\<TAB><TAB>9` (×2).

Observed with real MarcEdit 7.6 (orchestrator probes 2026-11-18, synthetic
records; `runs/OMT-027/probes.md` in the coordination repo has every case):
- Shape: `INDICATOR<TAB>tag<TAB>find<TAB>condition<TAB>value`; `\` is a blank.
- For every field with the tag whose two indicators **start with** `find`
  (empty `find` matches all), the first len(`value`) indicator positions are
  overwritten by `value`: `\`→`9` on `[  ]` gives `[9 ]`; `4`→`7` on `[41]`
  gives `[71]`; empty→`9` on `[41]` gives `[91]`; empty→`40` gives `[40]`;
  `\`→`\9` on `[  ]` gives `[ 9]`. `find` `1` on `[41]` matched nothing.
  An empty `value` changes nothing.
- The condition column is a case-sensitive substring test on the field's text
  line (tag and indicators included). Real lines leave it empty.

Design (the spec records it):
- **Step** `set_indicators`: `tag` (three ASCII digits), `value` (1–2
  characters), optional `if_starts_with` (1–2 characters). Blanks are written
  as in add_field's `ind1`/`ind2`. Behavior as observed above.
- Importer: `INDICATOR` with 5 columns, an empty condition, a `value` of 1–2
  characters and a `find` of 0–2 characters no longer than `value` →
  `set_indicators` (`\` → blank). Other shapes stay not translated with a reason.

Scope:
- `open_marc_tasks/commands/set_indicators.py`, table entry in `task.py`;
  importer; spec, schema, `ARCHITECTURE.md` status line.
- Conformance cases under `conformance/set_indicators/` (synthetic records,
  `expected.mrc` only from `tools/marcedit_reference.py regenerate`): the three
  real line forms over fields that do and don't match, and empty `find` with a
  one-character `value` over `[41]`.

Out of scope:
- The condition column, other commands.

Likely files:
- open_marc_tasks/commands/set_indicators.py, open_marc_tasks/task.py, open_marc_tasks/marcedit_import.py
- spec/format.md, spec/task.schema.json, ARCHITECTURE.md
- conformance/set_indicators/<case>/…
- tests/test_task_loading.py, tests/test_marcedit_import.py (extend parametrized tests)

Acceptance tests:
- Every new conformance case passes the suite and `tests/test_reference.py` on
  the host (not skipped).
- The invalid-task parametrize gains a 3-character `value` and a missing `tag`
  (loader with the step number, and schema).
- The importer parametrize gains the three real forms (translated, passing
  `load_task`) and a non-empty condition (not translated).

Verification:
- The Python 3.9 gate in AGENTS.md "Build and test".
- On the host from the worktree: `python3 -m pytest -q tests/test_reference.py`, counts reported.
- The orchestrator reruns the private 100-task measurement after the check.

Handoff:
- (orchestrator fills in after the check)

Review:
- (orchestrator fills in)
