Title: Add regex subfield edits and removals (MarcEdit SUBFIELD_EDIT and SUBFIELD_REMOVE `0|2`)

Status: Completed
Size: S
Tier: normal — reuses the OMT-012 regex dialect; one new matching scope, characterized below
Milestone: M2 — Commands
Base: the local `main` commit that adds this ticket
Branch: codex/OMT-022

Why:
- 22 `SUBFIELD_EDIT` lines and 2 `SUBFIELD_REMOVE` lines use regex (`0|2`);
  regex SUBFIELD_EDIT is the only untranslated line in 8 tasks. Forms:
  `([a-zA-Z0-9])([^a-zA-Z0-9])` → `$1` (strip punctuation after a letter or
  digit, 19 lines), `852 $h .+` → `hOnline` (2), `852 $l ME.+` → `SCINT` (1),
  and the same strip pattern as a removal (2).

Observed with real MarcEdit 7.6 (orchestrator probes 2026-11-18, synthetic records):
- The regex runs on the subfield's **code followed by its value** (`hOnline`, not
  `Online`); the first character of the result becomes the code and the rest the
  value. So `.+` → `hOnline` sets every `$h` to `Online`; `^O` matches nothing
  (the text starts with `h`); `ME.+` → `SCINT` turns `$lMEBKS` into `$lSCINT`
  and leaves `$lSCME` (nothing after `ME`); `^.*$` → `X` produced code `X` with
  an empty value.
- The strip pattern: `$aab-12 cd.` → `$aab12cd`; `$a-x` → `$ax` (the code `a`
  and `-` form the first match); `$a.` → `$a` empty. Other codes are untouched.
- Every match in the text is replaced, left to right, as in replace_text regex mode.
- SUBFIELD_REMOVE `0|2` is the same with an empty replacement: `$bB2` with
  `[A-Z]` → `$b2`, `$bB` → `$b` empty; a result that is entirely empty (`^.*$`)
  removed the subfield, and a field left with no subfields was deleted.

Design (the spec records it):
- `edit_subfield` gains action `"replace_regex"` with `find` (OMT-012 dialect,
  validated at load) and `replace` (OMT-012 replacement rules).
- `remove_subfield` gains `remove_regex` (OMT-012 dialect), mutually exclusive
  with `if_contains` and `remove_text`.
- Both match on code + value, as observed. A result that is empty removes the
  subfield (and an emptied field is deleted, as remove_subfield already does).
  A non-empty result whose first character isn't a valid subfield code (lowercase
  ASCII letter or digit) raises a run-time error naming the record and step
  (MarcEdit wrote an invalid code `X`). Characterize with MarcEdit what an empty
  result does in SUBFIELD_EDIT and follow it.
- Reuse the OMT-012 compile and replacement code; don't copy it.

Scope:
- `open_marc_tasks/commands/edit_subfield.py`, `open_marc_tasks/commands/remove_subfield.py`;
  importer (`SUBFIELD_EDIT … 0|2` and `SUBFIELD_REMOVE … 0|2`); spec, schema,
  `ARCHITECTURE.md` status line.
- Conformance cases (synthetic records, `expected.mrc` only from
  `tools/marcedit_reference.py regenerate`): the strip pattern over values that
  start with punctuation, end with punctuation and are only punctuation; `.+` →
  `hOnline` over two `$h`; `ME.+` matching and not matching; a regex removal
  with a partly and a fully emptied subfield.

Out of scope:
- `EDITFIELD` regex, other options, other commands.

Likely files:
- open_marc_tasks/commands/edit_subfield.py, open_marc_tasks/commands/remove_subfield.py
- open_marc_tasks/regex_dialect.py (reuse only), open_marc_tasks/marcedit_import.py
- spec/format.md, spec/task.schema.json, ARCHITECTURE.md
- conformance/edit_subfield/<case>/…, conformance/remove_subfield/<case>/…
- tests/test_task_loading.py, tests/test_marcedit_import.py, tests/test_cli.py (extend parametrized tests)

Acceptance tests:
- Every new conformance case passes the suite and `tests/test_reference.py` on the host (not skipped).
- A result with an invalid first character raises an error naming record 2 and
  step 2 through `omt run` (extend the existing invalid-result row set).
- The invalid-task parametrize gains a dialect-invalid `find` and `remove_regex`
  (loader, with the step number) and `remove_regex` together with `remove_text` (loader and schema).
- The importer parametrize gains both regex forms (translated, passing
  `load_task`) and an option like `0|3` (not translated).

Verification:
- The Python 3.9 gate in AGENTS.md "Build and test".
- On the host from the worktree: `python3 -m pytest -q tests/test_reference.py`, counts reported.
- The orchestrator reruns the private 100-task measurement after the check.

Handoff:
- Head 043405a, merged into main (owner OK 2026-11-18). Python 3.9 gate 196 passed, 1 skipped; host reference passed. Measure 41/100, 0 differ, on all three samples.

Review:
- Regex on code+value per MarcEdit; SUBFIELD_EDIT keeps an emptied field (MarcEdit), SUBFIELD_REMOVE deletes it. Duplicated loop noted for later. No fix round.
