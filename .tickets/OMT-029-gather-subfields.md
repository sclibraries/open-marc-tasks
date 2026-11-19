Title: Add gather_subfields and import the 856-to-945 loop idiom

Status: Ready
Size: S
Tier: normal — new command plus one importer idiom; owner chose this over emulating loops
Milestone: M2 — Commands
Base: the local `main` commit that adds this ticket
Branch: codex/OMT-029

Why:
- 8 tasks call the cataloger's "Building a new 945 field form multiple 856s
  looping" task, which uses a MarcEdit loop. Owner decision 2026-11-18: no
  general loop support; a plain step does what the loop is for (collect every
  856 URL into the 945 that becomes the FOLIO holdings 949). The loop task is
  used in its corrected form (the original repeats the last URL; decision
  `2026-11-18-loop-task-fix.md` in the coordination repo).

The corrected loop task (synthetic restatement):
```
ADD<TAB>945<TAB>\\$aplaceholder<TAB>101<TAB>
#STARTLOOP:r=0
REPLACE<TAB>(=856)([^\r\n]*?)(\$u[^\r\n]*)(.*)(=945[^\n\r]*)(.*)/m<TAB>=999$2$3$4$5$3$6<TAB>2<TAB><TAB>0<TAB>False
#ENDLOOP
SUBFIELD_REMOVE<TAB>945<TAB>a<TAB>placeholder<TAB>107<TAB>0
DELETE<TAB>999<TAB><TAB>0<TAB>False<TAB>False<TAB>False<TAB>False<TAB>False
```
Observed with real MarcEdit 7.6 (orchestrator probe 2026-11-18): 856 40
`$uhttp://one$znote1`, 856 41 `$3part$uhttp://two`, 856 40 `$uhttp://three`
→ one 945 `\\$uhttp://one$znote1$uhttp://two$uhttp://three`, no 856 left; the
loop repeats until a pass changes nothing. Each pass takes the first remaining
856 that has a `$u`, appends its subfields from that `$u` to the end of the
field onto the last 945 that comes after it, and retags the 856 as 999.

Design (the spec records it):
- **Step** `gather_subfields`: `from_tag`, `code`, `to_tag` (three ASCII
  digits, data tags), `remove_source` (boolean, default false). For each field
  with `from_tag` that has a `code` subfield, in record order: append its
  subfields from the first `code` subfield onward to the last `to_tag` field
  that comes after it in the record; when there is no such field, leave the
  source alone. With `remove_source`, a source that was gathered is deleted.
  Characterize first with MarcEdit (corrected loop) and follow it: a source
  with `code` repeated, no `to_tag` field, a `to_tag` field before the source,
  two `to_tag` fields.
- Importer: the exact idiom `#STARTLOOP:r=0`, one REPLACE of the corrected
  form above (any tags in place of 856/945, any code in place of `u`), then
  `#ENDLOOP`, translates to `gather_subfields` with `remove_source: true`, and
  the `999` it retags to must be deleted by a later `DELETE 999` in the same
  task (else not translated). Any other loop, including the uncorrected
  `(.*)` form, stays not translated with a reason.

Scope:
- `open_marc_tasks/commands/gather_subfields.py`, table entry in `task.py`;
  importer; spec, schema, `ARCHITECTURE.md` status line.
- Conformance cases under `conformance/gather_subfields/` (synthetic records;
  `marcedit-task.txt` is the corrected loop task; `expected.mrc` only from
  `tools/marcedit_reference.py regenerate`): three 856s as above; the
  characterization cases; a record with no 856.

Out of scope:
- General MarcEdit loops, the uncorrected loop form, the 949 loop variant.

Likely files:
- open_marc_tasks/commands/gather_subfields.py, open_marc_tasks/task.py, open_marc_tasks/marcedit_import.py
- spec/format.md, spec/task.schema.json, ARCHITECTURE.md
- conformance/gather_subfields/<case>/…
- tests/test_task_loading.py, tests/test_marcedit_import.py (extend parametrized tests)

Acceptance tests:
- Every new conformance case passes the suite and `tests/test_reference.py` on
  the host (not skipped).
- The invalid-task parametrize gains a control-field `to_tag` and a missing
  `code` (loader with the step number, and schema).
- The importer parametrize gains the corrected idiom (translated, passing
  `load_task`), the uncorrected `(.*)` form and the idiom without a later
  `DELETE 999` (not translated).

Verification:
- The Python 3.9 gate in AGENTS.md "Build and test".
- On the host from the worktree: `python3 -m pytest -q tests/test_reference.py`, counts reported.
- The orchestrator reruns the private 100-task measurement after the check,
  with `--library` pointing at the folder holding the corrected loop task.

Handoff:
- (orchestrator fills in after the check)

Review:
- (orchestrator fills in)
