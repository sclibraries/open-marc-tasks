Title: Add remove_subfield and import MarcEdit SUBFIELD_REMOVE (whole-subfield and text forms)

Status: Ready
Size: S
Tier: normal — new command with plain settings; no new syntax
Milestone: M2 — Commands
Base: the local `main` commit that adds this ticket
Branch: codex/OMT-017

Why:
- `SUBFIELD_REMOVE` has 90 lines in the Smith and UMass task files and is the
  only blocker for 5 tasks: removing 856 `$z`/`$3`/`$y`, 852 `$p`, 956 `$y`
  (empty value, option `107|0`, 52 lines incl. one with a value), and removing
  text such as `(OCoLC)` or a ProQuest URL prefix from a value (`0|0`, 4 lines).
  Option `9|0` (32 lines) waits on an owner decision; regex `0|2` (2 lines) is a
  later ticket.

Observed with real MarcEdit 7.6 (orchestrator probes 2026-11-17, synthetic
records). Line form: `SUBFIELD_REMOVE<TAB>tag<TAB>code<TAB>value<TAB>N|M`.
- Empty value (any first number tried except 9: 0, 1, 3, 8, 11, 64, 99, 107):
  every `$code` in every field with the tag is removed; a field left with no
  subfields is deleted (856 with only `$z`; 945 with only `$b`).
- `107|0` with a value: removes each `$code` whose value contains it
  (case-sensitive substring: `D` removes `xDyD` and `D`, keeps `d1`); a field left
  with no subfields is deleted.
- `0|0` with a value: removes every occurrence of the text from each `$code`
  value (case-sensitive: `(OCoLC)123` → `123`, `xDyD` → `xy`, `d1` kept); a value
  that becomes empty stays as an empty subfield (`D` → `$b` empty). `5|0` behaved the same.
- An uppercase code (`Z`) matched nothing.

Design (the spec records it):
- **Step** `remove_subfield`: `tag` (three digits), `code` (one lowercase ASCII
  letter or digit), and at most one of `if_contains` (non-empty string: remove
  subfields whose value contains it) or `remove_text` (non-empty string: remove
  that text from values, keeping empty subfields). With neither, remove every
  `$code`. A data field left with no subfields is deleted (both forms that remove
  whole subfields). A control-field tag is rejected at load.
- Confirm with MarcEdit (conformance cases): a field whose every subfield is
  removed by `if_contains` is deleted, and `if_contains` matches anywhere in the
  value (`(OCoLC)` in the middle).

Scope:
- `open_marc_tasks/commands/remove_subfield.py`, table entry in `task.py`; spec,
  schema, `ARCHITECTURE.md` status line.
- Importer: `SUBFIELD_REMOVE` with an empty value and first number `107` or `0`
  → `remove_subfield` (no extra setting); `107|0` with a value → `if_contains`;
  `0|0` with a value → `remove_text`. Not translated, with a reason: `9|…`
  ("waiting on owner decision"), `…|2` (regex, later), any other option, a
  control-field tag, an unsupported `{…}` mnemonic in the value.
- Conformance cases under `conformance/remove_subfield/` (synthetic records,
  `expected.mrc` only from `tools/marcedit_reference.py regenerate`): remove all
  `$z` from repeated 856s with one 856 left empty (deleted); `if_contains` with
  case and middle-of-value matches; `remove_text` with repeats, case and an
  emptied value.

Out of scope:
- Options `9` and `…|2`, tag wildcards, other commands.

Likely files:
- open_marc_tasks/commands/remove_subfield.py, open_marc_tasks/task.py, open_marc_tasks/marcedit_import.py
- spec/format.md, spec/task.schema.json, ARCHITECTURE.md
- conformance/remove_subfield/<case>/…
- tests/test_task_loading.py, tests/test_marcedit_import.py (extend parametrized tests)

Acceptance tests:
- Every new conformance case passes the suite and `tests/test_reference.py` on
  the host (not skipped), so removal, field deletion and text removal match MarcEdit.
- The invalid-task parametrize gains: a bad `code`, a control-field `tag`, both
  `if_contains` and `remove_text`, an empty `remove_text` (loader and schema).
- The importer parametrize gains the empty-value, `107|0` with value and `0|0`
  with value forms (translated, passing `load_task`) and `9|0`, `0|2`, `3|1`
  (not translated).

Verification:
- The Python 3.9 gate in AGENTS.md "Build and test".
- On the host from the worktree: `python3 -m pytest -q tests/test_reference.py`, counts reported.
- The orchestrator reruns the private 100-task measurement after the check.

Handoff:
- (orchestrator fills in after the check)

Review:
- (orchestrator fills in)
