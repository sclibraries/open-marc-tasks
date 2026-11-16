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

- Format v0.1 with `delete_field` (OMT-001) and `add_field` (OMT-004), both added 2026-11-16.
- `load_task` (plain-Python validation, `TaskError` with step numbers),
  `run_task` (modifies records in place, yields them in order) and
  `records_match` live in `open_marc_tasks/task.py` and `match.py`. Commands
  are dispatched by name through the per-command table in `task.py`.
- Conformance: `conformance/delete_field/` (4 cases) and `conformance/add_field/` (6 cases), expected output from MarcEdit 7.6; each case keeps the MarcEdit task line in `marcedit-task.txt`.
- CI: Python 3.9 with pymarc 5.1.2, and Python 3.13 with the newest pymarc below 6.
- Known MarcEdit behavior: an `X` before a later digit (`0X9`) matches
  nothing; v0.1 follows it.
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
- Importer `open_marc_tasks/marcedit_import.py` and `omt import` (OMT-005):
  translates MarcEdit `DELETE` (tag only, default flags) and `ADD` (options
  100/101/108, and 106 with Leader-class conditions); lists every other line
  with a reason and writes a task only when fully translated.
- `tools/measure.py` (dev only): imports MarcEdit task folders, runs fully
  translated tasks through the library and MarcEdit on a sample, reports
  "X of Y task files match MarcEdit". Folders and sample are local paths;
  nothing from them enters the repo.
- Not built yet: the other MarcEdit commands (SUBFIELD_EDIT, REPLACE, build
  field, DELETE by value, SUBFIELD_REMOVE, COPY, TASK_LIST, SORTBY, EDITFIELD,
  INDICATOR).
