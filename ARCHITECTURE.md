# Architecture — open-marc-tasks

An open format for batch-editing MARC records, a Python library and CLI that
run it, and an importer for MarcEdit task files. This file describes `main`;
a change that alters it updates it in the same ticket.

## Parts

| Part | Path | Role |
|---|---|---|
| Format spec | `spec/format.md`, `spec/task.schema.json` | The contract. Language-neutral; another implementation (for example a FOLIO module) is built from this alone. |
| Library | `open_marc_tasks/` | Loads a task file, validates it, runs its steps over pymarc records. |
| Commands | `open_marc_tasks/commands/` | One module per command. |
| CLI | `omt` | `omt run task.json in.mrc out.mrc`; later `omt import`. |
| Conformance suite | `conformance/<command>/<case>/` | `task.json`, `input.mrc`, `expected.mrc`. Expected output comes from real MarcEdit. Any implementation must match it. |
| Reference tools | `tools/` (dev only) | Run real MarcEdit locally to make expected output and measure coverage. Never shipped. |

## Fixed points

- Python 3.9 and newer; the only runtime dependency is `pymarc>=5.1.2,<6`.
- Task files are data. Nothing in a task is evaluated, executed or imported.
- "Matches MarcEdit": every field's tag, indicators and content in the same
  order, plus Leader positions 05–09 and 17–19. Field 005 and Leader length
  and base address are ignored.
- Records are processed as Unicode (UTF-8).
- MarcEdit itself is never committed or redistributed; it is a local,
  development-time answer key (`reference/marcedit/`, git-ignored).
- Conformance records and tasks are synthetic. No institutional data, and no
  task files from GPL-licensed sources.

## Status

- Format v0.1 with `delete_field` (OMT-001; OMT-014 adds optional field-text
  matching) and `add_field` (OMT-004), both added 2026-11-16.
- `load_task` (plain-Python validation, `TaskError` with step numbers),
  `run_task` (modifies records in place, yields them in order) and
  `records_match` live in `open_marc_tasks/task.py` and `match.py`. Commands
  are dispatched by name through the table in `task.py`; each command module
  (`commands/<name>.py`) owns its `validate(step, number)` and `run(record, step)`.
- Conformance: `conformance/delete_field/` (9 cases), `conformance/add_field/` (6 cases), and `conformance/replace_text/` (10 cases), expected output from MarcEdit 7.6; each case keeps the MarcEdit task line in `marcedit-task.txt`.
- CI: Python 3.9 with pymarc 5.1.2, and Python 3.13 with the newest pymarc below 6.
- Known MarcEdit behavior: an `X` before a later digit (`0X9`) matches
  nothing; v0.1 follows it. Backslash indicators become blanks on every
  record before steps run (OMT-006, owner decision 2026-11-16). With the task
  option `normalize_typography` (default false; set true by the importer),
  curly quotes, dashes and ellipses are replaced like MarcEdit (OMT-009).
- CLI `omt run TASK INPUT OUTPUT` (`open_marc_tasks/cli.py`, OMT-002): UTF-8
  input only (Leader/09 `a`), refuses empty, unreadable or truncated input and
  records left with no fields, writes through a temporary file and replaces
  OUTPUT only on success, refuses OUTPUT equal to INPUT.
- CI: the Python 3.9 job runs in the `python:3.9-slim` container (GitHub's
  runners no longer provide 3.9).
- Reference runner `tools/marcedit_reference.py` (OMT-003): runs MarcEdit for a
  case and `regenerate`s `expected.mrc`; `tests/test_reference.py` reruns
  MarcEdit for every case and fails on any difference (skips without MarcEdit
  or Docker, as in CI).
- Importer `open_marc_tasks/marcedit_import.py` and `omt import` (OMT-005;
  DELETE match forms extended by OMT-014):
  translates MarcEdit `DELETE` (tag-only and field-text matching forms) and
  `ADD` (options 100/101/108, and 106 with Leader-class conditions), plus
  plain `REPLACE` (OMT-011); lists every other line with a reason and writes a
  task only when fully translated.
- `tools/measure.py` (dev only): imports MarcEdit task folders, runs fully
  translated tasks through the library and MarcEdit on a sample, reports
  "X of Y task files match MarcEdit". Folders and sample are local paths;
  nothing from them enters the repo.
- `edit_subfield` (OMT-007, OMT-022): every observed `SUBFIELD_EDIT` form, including regex option `0|2` via the OMT-012 dialect.
- `remove_subfield` (OMT-017, OMT-022): whole-subfield removal, `if_contains`, `remove_text`, and regex `remove_regex`; imports the observed `SUBFIELD_REMOVE` options `107|0`, `0|0`, and `0|2`.
- Field text form and `replace_text` (OMT-011, OMT-012): plain mode replaces
  literal, case-sensitive text; regex mode uses the portable dialect in
  `spec/format.md`. Regex REPLACE importing remains out of scope (OMT-013).
- `build_field` (OMT-015, OMT-016): add, add-if-missing and replace from field
  text templates, including the observed MarcEdit `buildnewfield` forms.
- `copy_field` (OMT-018): copies or moves exact-tag fields with optional
  case-sensitive field-text matching; filtered control sources and
  control-to-control COPY lines are not imported while their MarcEdit behavior
  remains unresolved.
- Not built yet: regex REPLACE import (OMT-013), TASK_LIST, SORTBY, EDITFIELD,
  INDICATOR.
