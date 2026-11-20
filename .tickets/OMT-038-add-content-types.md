Title: Implement add_content_types and import the Smith RDAHELPER line

Status: Ready
Size: M
Tier: normal — new command built from the OMT-037 black-box spec
Milestone: M2 — Commands
Base: the local `main` commit that adds this ticket
Branch: codex/OMT-038

Why:
- OMT-037 specified MarcEdit's 336/337/338 generation for
  `RDAHELPER<TAB>1|1|0|0|0|0|0|0|0|0|0|0|0|0|0|0|language of cataloging|0` (the
  only untranslated line in the four Smith CORE Instance tasks) and left two
  gaps: 007/01 values and Leader/06 values beyond those probed.
- **Clean-room rule (unchanged from OMT-037):** behavior comes only from
  MarcEdit's inputs and outputs. Do not read, search, decompile or disassemble
  MarcEdit code or binaries; do not open anything under `/private/tmp` or the
  orchestrator's folders. Confirm this in the handoff.

Scope:
1. Close the gaps first, by probe: every 007/01 value `a`–`z`, blank and `|`
   for each of the 007/00 classes `c`, `g`, `h`, `m`, `s`, `v`, `z`, and every
   Leader/06 value `a`–`z` and blank. Add the results to the spec tables (one
   compact grid case per class is enough; `expected.mrc` only from
   `tools/marcedit_reference.py regenerate`). After this there are no
   uncharacterized Leader/06 or 007/00–01 inputs for these classes; any other
   007/00 class uses the default, as observed.
2. `open_marc_tasks/commands/add_content_types.py` (no settings), table entry,
   schema; remove the OMT-038 skip so every `conformance/add_content_types/`
   case runs.
3. Importer: exactly the Smith line above → `add_content_types`. Any other
   RDAHELPER flag set stays not translated with a reason.
4. `spec/format.md`: drop "planned"/"not supported" wording and the closed open
   questions; `ARCHITECTURE.md` status line.

Out of scope:
- Other RDAHELPER flags (the EDS set), 344–347/380/381, abbreviations.

Likely files:
- open_marc_tasks/commands/add_content_types.py, open_marc_tasks/task.py, open_marc_tasks/marcedit_import.py
- spec/format.md, spec/task.schema.json, ARCHITECTURE.md
- conformance/add_content_types/<case>/…, tests/test_conformance.py (remove the skip)
- tests/test_task_loading.py, tests/test_marcedit_import.py (extend parametrized tests)

Acceptance tests:
- Every `add_content_types` conformance case (the five from OMT-037 and the new
  grids) passes the suite and `tests/test_reference.py` on the host, not skipped.
- The invalid-task parametrize gains an `add_content_types` step with an
  unknown setting (loader and schema).
- The importer parametrize gains the Smith line (translated, passing
  `load_task`) and the EDS flag set (not translated).

Verification:
- The Python 3.9 gate in AGENTS.md "Build and test".
- On the host from the worktree: `python3 -m pytest -q tests/test_reference.py`, counts reported.
- The orchestrator reruns the private measurement; the four Smith CORE
  Instance tasks should be compared.

Plan:
1. Probe grids and spec tables.
2. Command, schema, conformance (skip removed).
3. Importer.

Handoff:
- (orchestrator fills in after the check)

Review:
- (orchestrator fills in)
