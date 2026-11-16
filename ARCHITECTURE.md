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

New project (2026-11-16). Nothing built yet; first ticket is OMT-001.
