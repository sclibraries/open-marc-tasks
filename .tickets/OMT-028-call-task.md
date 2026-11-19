Title: Add call_task and import MarcEdit TASK_LIST

Status: Completed
Size: M
Tier: normal — new command that loads another task file; owner chose the design
Milestone: M2 — Commands
Base: the local `main` commit that adds this ticket
Branch: codex/OMT-028

Why:
- `TASK_LIST` (54 lines) is the only untranslated command in 19 of the 27
  tasks that don't fully translate. Owner decision 2026-11-18: a TASK_LIST
  becomes a step that runs another task file, so shared tasks (FOLIO core,
  OCLC clean-up, Edit Smart/HTML/ISBD, …) stay shared; not inlined at import.

What the MarcEdit lines look like (real files):
- `TASK_LIST<TAB>name<TAB>file` or `TASK_LIST<TAB>group<TAB>name<TAB>file`,
  e.g. `TASK_LIST<TAB>OCLC Records Clean up 001 and 035<TAB>tasksfile-2024_06_04_122910785.txt`
  and `TASK_LIST<TAB>FOLIO<TAB>FOLIO UM Core<TAB>tasksfile-2023_10_30_154434371.txt`.
- The called task is the MarcEdit task whose inner file is named
  `<name>.-<file>` (`OCLC Records Clean up 001 and 035.-tasksfile-2024_06_04_122910785.txt`
  inside `OCLCCleanUp001And035.task`). The importer already writes each task
  as `<inner file stem>.json`, so the called task's JSON is
  `<name>.-<file stem>.json`.
- The MarcEdit command-line reference can't be pointed at a task folder
  (orchestrator probes 2026-11-18: it skipped the TASK_LIST silently with the
  sub-task beside the task file and in 12 candidate config folders). MarcEdit
  runs each step over the whole file in order, so the reference for a task
  that calls another is the task with the called task's lines put in place of
  the TASK_LIST line (recursively). This is an assumption the spec states.

Design (the spec records it):
- **Step** `call_task`: `task` — a file name (no `/` or `\`, ends in `.json`)
  of another task in the same folder as the calling task file. The called
  task's steps run on the record at that point, after its own
  `normalize_typography` if set.
- `load_task` loads called tasks (recursively) when it loads the caller, so
  every error is a load error with the step number: a missing or invalid
  called file, and a call cycle (name the files in the cycle).
- A run-time error inside a called task names the record, the calling step
  and the called task's file and step.
- Importer: a 3- or 4-column `TASK_LIST` whose last column ends in `.txt` →
  `call_task` with `task` `<second-to-last column>.-<last column stem>.json`.
  Other shapes stay not translated with a reason. The importer does not check
  that the called task exists.
- `tools/measure.py`: import every task found in the given folders into one
  temporary folder, so calls resolve; build the MarcEdit reference by putting
  the called task's lines in place of each TASK_LIST line, recursively,
  finding called tasks by inner file name across the given folders. A task
  whose called task can't be found (or isn't fully translated) is reported as
  not translated with that reason, never as a crash or a difference.

Scope:
- `open_marc_tasks/commands/call_task.py`, `task.py` (table entry and the
  loading the design needs); importer; `tools/measure.py`; spec, schema,
  `ARCHITECTURE.md` status line.
- One conformance case `conformance/call_task/<case>/` with a calling task
  and a called task file; its `marcedit-task.txt` is the inlined equivalent and
  `expected.mrc` comes only from `tools/marcedit_reference.py regenerate`.
  Adjust the conformance runner only as far as a second task file needs.

Out of scope:
- MarcEdit loops (`#STARTLOOP` / `#ENDLOOP`), paths outside the calling
  task's folder, other commands.

Likely files:
- open_marc_tasks/commands/call_task.py, open_marc_tasks/task.py, open_marc_tasks/marcedit_import.py
- tools/measure.py
- spec/format.md, spec/task.schema.json, ARCHITECTURE.md
- conformance/call_task/<case>/…, tests/test_conformance.py (only if a second file needs it)
- tests/test_task_loading.py, tests/test_marcedit_import.py, tests/test_cli.py (extend parametrized tests)

Acceptance tests:
- The conformance case passes the suite and `tests/test_reference.py` on the
  host (not skipped).
- Loader (extend the invalid-task parametrize, with the step number): a
  missing called file, a called file that is invalid, a two-file call cycle,
  and a `task` with a `/`.
- A run-time error in a called task through `omt run` names record 2, the
  calling step and the called file's step (extend the existing row set).
- Importer: both real shapes translate to the expected `task` names; a
  2-column `TASK_LIST` is not translated.

Verification:
- The Python 3.9 gate in AGENTS.md "Build and test".
- On the host from the worktree: `python3 -m pytest -q tests/test_reference.py`, counts reported.
- The orchestrator reruns the private 100-task measurement after the check.

Plan:
1. Spec and schema for `call_task`; loader resolution and cycle check.
2. `call_task` command and error naming; conformance case.
3. Importer mapping.
4. `tools/measure.py` folder import and reference inlining.

Handoff:
- Head d5b09f8, merged into main (owner OK 2026-11-19). Python 3.9 gate 237 passed, 1 skipped; host reference passed. Measure 75/100, 0 differ, on all three samples (--library marcedit-main).

Review:
- One fix round: real TASK_LIST is 3 columns with optional `group|name` (ticket's 4-column shape was the orchestrator's error); measure duplicate-copy regression; --library. Reference for calls inlines the called task (stated assumption).
