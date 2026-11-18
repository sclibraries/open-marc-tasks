Title: Add sort_fields and import MarcEdit SORTBY

Status: Completed
Size: S
Tier: normal — new command; the ordering rule is characterized against MarcEdit
Milestone: M2 — Commands
Base: the local `main` commit that adds this ticket
Branch: codex/OMT-023

Why:
- `SORTBY` has 44 lines: `SORTBY<TAB>ALL<TAB>True<TAB>True` (37) and
  `SORTBY<TAB>0XX` (7). It is the only untranslated line in 6 tasks, including
  Smith CORE Holdings and Items.

Observed with real MarcEdit 7.6 (orchestrator probes 2026-11-18, synthetic records):
- `ALL` (with any of the four True/False flag pairs; real files use `True True`)
  sorts every field, and fields with the same tag are ordered by content too:
  035 `$a2`, `$a1` → `$a1`, `$a2`; 856 `$ub`, `$ua` → `$ua`, `$ub`; 650 `$aB`,
  `$aA` → `$aA`, `$aB`. Control fields 003, 001, 008 → 001, 003, 008.
- `0XX` (with or without flags): the 0XX fields are sorted the same way and placed
  first; every other field keeps its original relative order after them
  (856 b, 245, 949, 856 a, 852 stayed in that order).

Design (the spec records it):
- **Step** `sort_fields`: `scope` `"all"` or `"0xx"`. Fields are ordered by a key
  MarcEdit's results define. Characterize first and specify exactly: whether the
  key is the field's text form (`=TAG  ` + indicators + `$`-subfields) compared
  by code point, or something else; cases to settle: same tag with different
  indicators (`\0` vs `10`), upper vs lower case (`$aB` vs `$aa`), digits vs
  letters, an exact duplicate (order kept?), a non-ASCII value, and a control
  field with a blank. If MarcEdit's order can't be pinned down as a simple rule,
  stop and say so in the handoff rather than guess.

Scope:
- `open_marc_tasks/commands/sort_fields.py`, table entry in `task.py`; spec, schema,
  `ARCHITECTURE.md` status line.
- Importer: `SORTBY\tALL` with any `True`/`False` pair, and `SORTBY\t0XX` with or
  without a pair → `sort_fields`. Other forms not translated, with a reason.
- Conformance cases under `conformance/sort_fields/` (synthetic records,
  `expected.mrc` only from `tools/marcedit_reference.py regenerate`): `all` over
  scrambled tags with repeated tags and the characterization cases above; `0xx`
  with 0XX fields scattered among others.

Out of scope:
- Other SORTBY targets, other commands.

Likely files:
- open_marc_tasks/commands/sort_fields.py, open_marc_tasks/task.py, open_marc_tasks/marcedit_import.py
- spec/format.md, spec/task.schema.json, ARCHITECTURE.md
- conformance/sort_fields/<case>/…
- tests/test_task_loading.py, tests/test_marcedit_import.py (extend parametrized tests)

Acceptance tests:
- Every new conformance case passes the suite and `tests/test_reference.py` on the host (not skipped).
- The invalid-task parametrize gains an unknown `scope` (loader and schema).
- The importer parametrize gains `ALL True True`, `ALL False False`, `0XX` (translated,
  passing `load_task`) and `SORTBY\t1XX` (not translated).

Verification:
- The Python 3.9 gate in AGENTS.md "Build and test".
- On the host from the worktree: `python3 -m pytest -q tests/test_reference.py`, counts reported.
- The orchestrator reruns the private 100-task measurement after the check.

Handoff:
- Head 1c87328, merged into main (owner OK 2026-11-18). Python 3.9 gate 210 passed, 1 skipped; host reference passed. Measure 57/56/56 of 100; 1 differ (eds_cc_umsiam) from add_field placement in out-of-order records, not sorting.

Review:
- Key = UTF-8 bytes read as cp1252, stable sort; 0xx stable tail. First round deferred (comparison unresolved); orchestrator pinned the key; one fix round. Minor: nine importer flag rows where three were asked.
