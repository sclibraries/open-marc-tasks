Title: Add edit_field and import MarcEdit EDITFIELD

Status: Ready
Size: S
Tier: normal — new command built from replace_text's matching and the text form
Milestone: M2 — Commands
Base: the local `main` commit that adds this ticket
Branch: codex/OMT-025

Why:
- `EDITFIELD` has 25 lines and is the only untranslated command in 9 tasks
  (most FOLIO ones strip `ocn|on|ocm` from 001). Forms: option `0` (plain) and
  `2` (regex), on 001, 003, 245, 935, 947, 950 and 956; the last column is
  always empty.

Observed with real MarcEdit 7.6 (orchestrator probes 2026-11-18, synthetic
records; `runs/OMT-025/probes.md` in the coordination repo has the detail):
- `EDITFIELD<TAB>tag<TAB>find<TAB>option<TAB>replace<TAB>` edits every field
  with that tag. The text matched is the field's text-form **body**: for a data
  field the `$`-subfields without the indicators (`10` matched `$c10 …`, never
  the indicators `10`; `^\$a` matched the start); for a control field its data
  with blanks as `\` (`2\3` matched `12 3`; find `\` with an empty replacement
  removed the blanks; a plain or regex space never matched).
- Option 0 is a case-sensitive literal replace of every occurrence; option 2 a
  regex replace of every match (`on|ocn|ocm` → `` gave `$a123$a9` from
  `$aon123$aocm9`; `(10\.3998\/\w{2,7}\.)(.+)` → `$2` worked across the
  `$b` that followed, as text).
- The result is read back as a body: `\` in control data becomes a blank;
  `{dollar}` becomes a literal `$` and a literal `$` in a value is matched as
  `{dollar}`; `$` starts a new subfield (`$aTitle` → `$aTi$tle` split it); text
  before the first `$` is dropped (`lead$a` → empty `$a`); a body left empty
  keeps the field with its indicators and no subfields (`.+` → `` on 956 gave
  `=956  40`). MarcEdit wrote an uppercase code `$A` as is.

Design (the spec records it):
- **Step** `edit_field`: `tag` (three characters), `find` (non-empty), `replace`
  (string), `regex` (boolean, default false; OMT-012 dialect and replacement
  rules, validated at load). Applies to every field with that tag, on the body
  as observed, and reads the result back as observed. Reuse `render_field`,
  `parse_field` and replace_text's matching; don't copy them.
- A result containing a subfield code that isn't a lowercase ASCII letter or
  digit raises a run-time error naming the record and step (as OMT-022 does).
- Importer: `EDITFIELD` with 6 columns, option `0` or `2` and an empty last
  column → `edit_field`. Other options, a non-empty last column, or other
  shapes stay not translated with a reason.

Scope:
- `open_marc_tasks/commands/edit_field.py`, table entry in `task.py`; importer;
  spec, schema, `ARCHITECTURE.md` status line.
- Conformance cases under `conformance/edit_field/` (synthetic records,
  `expected.mrc` only from `tools/marcedit_reference.py regenerate`): a 001
  with `ocn` and with a blank (regex `on|ocn|ocm`, and plain `\` → ``); a plain
  data-field edit that would match the indicators if they were included; the
  935 regex form across subfields; a regex that empties a data field's body.

Out of scope:
- `REPLACE`, `SUBFIELD_EDIT`; other options; the last column's meaning.

Likely files:
- open_marc_tasks/commands/edit_field.py, open_marc_tasks/task.py, open_marc_tasks/marcedit_import.py
- open_marc_tasks/commands/replace_text.py (only to share its matching)
- spec/format.md, spec/task.schema.json, ARCHITECTURE.md
- conformance/edit_field/<case>/…
- tests/test_task_loading.py, tests/test_marcedit_import.py, tests/test_cli.py (extend parametrized tests)

Acceptance tests:
- Every new conformance case passes the suite and `tests/test_reference.py` on
  the host (not skipped).
- An invalid result code raises an error naming record 2 and step 2 through
  `omt run` (extend the existing invalid-result row set).
- The invalid-task parametrize gains a missing `tag` and a dialect-invalid
  regex `find` (loader, with the step number; schema for the missing tag).
- The importer parametrize gains option 0 and option 2 lines (translated,
  passing `load_task`) and option `1` and a non-empty last column (not translated).

Verification:
- The Python 3.9 gate in AGENTS.md "Build and test".
- On the host from the worktree: `python3 -m pytest -q tests/test_reference.py`, counts reported.
- The orchestrator reruns the private 100-task measurement after the check.

Handoff:
- (orchestrator fills in after the check)

Review:
- (orchestrator fills in)
