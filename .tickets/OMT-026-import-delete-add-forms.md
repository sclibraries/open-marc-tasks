Title: Import more DELETE and ADD line shapes

Status: Completed
Size: S
Tier: normal — importer accepts more MarcEdit line shapes; no engine change
Milestone: M2 — Commands
Base: the local `main` commit that adds this ticket
Branch: codex/OMT-026

Why:
- 14 real lines are not translated only because of their shape:
  `DELETE<TAB>9xx<TAB>…` with a lowercase `x` (9 lines, 9 tasks), a 9-column
  DELETE with an extra trailing tab (1), an ADD with two extra columns
  `…<TAB>/cond/<TAB>100<TAB>` (2), and an ADD whose field text starts with a
  space before the indicators (` \\$acomputer…`, 2).

Observed with real MarcEdit 7.6 (orchestrator probes 2026-11-18, synthetic records):
- `DELETE 9xx` deleted exactly what `DELETE 9XX` deleted (900, 949, 990).
- `DELETE<TAB>506<TAB><TAB>0<TAB>False×5<TAB>` (10 columns, last empty) deleted
  the 506 like the 9-column line.
- `ADD<TAB>877<TAB>\\$mImage<TAB>106<TAB>/=LDR.{8}[km].+/<TAB>100<TAB>` added
  the 877 only to the matching record, exactly as the same line without
  `<TAB>100<TAB>`.
- `ADD<TAB>337<TAB> \\$acomputer$bc$2rdamedia<TAB>100<TAB>` added
  `=337  \\$acomputer$bc$2rdamedia`: the leading space was ignored.

Scope (`open_marc_tasks/marcedit_import.py` only, plus spec):
- DELETE: a lowercase `x` in the tag is read as `X`; a 10th column is accepted
  when it is empty.
- ADD: 7 columns are accepted when the 6th is `100` and the 7th is empty, and
  translate as the first 5 columns do; leading spaces before the indicators in
  the field text are dropped.
- `spec/format.md` importer section: one line per shape.

Out of scope:
- The ADD field-text condition (`/650.+Newspapers.+/`), DELETE with its first
  flag `True`, other columns' meanings; the engine and loader (a lowercase tag
  in a task file stays invalid).

Likely files:
- open_marc_tasks/marcedit_import.py, spec/format.md
- tests/test_marcedit_import.py (extend the parametrized tests)

Acceptance tests:
- The translated-lines parametrize gains the four real shapes above (each
  passing `load_task`, with the expected step: `9xx` → tag `9XX`; the ADD forms
  equal to their 5-column equivalents, indicators blank).
- The not-translated parametrize gains a 10-column DELETE with a non-empty last
  column and a 7-column ADD whose 6th column isn't `100`.

Verification:
- The Python 3.9 gate in AGENTS.md "Build and test".
- The orchestrator reruns the private 100-task measurement after the check.

Handoff:
- Head 8af6a8a, merged into main (owner OK 2026-11-18). Python 3.9 gate 223 passed, 1 skipped. Measure 71/100, 0 differ, on all three samples.

Review:
- Four importer shapes as characterized. Minor: 7-column ADD accepted for any option (spec says 106). No fix round.
