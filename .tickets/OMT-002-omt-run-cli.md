Title: Add the omt run command with safe input and output handling, and fix the Python 3.9 CI job

Status: In-Progress
Size: S
Tier: normal — new user-facing behavior (CLI); no new dependencies
Milestone: M1 — Format and runner
Base: the local `main` commit that adds this ticket
Branch: codex/OMT-002

Why:
- People outside Smith Metadata Studio need to run a task on a MARC file with
  one command. A tool that edits catalog records must never leave a half-written
  or silently wrong file, or destroy the file it was given.
- CI fails on every push: GitHub's ubuntu-latest no longer offers Python 3.9
  through setup-python ("The version '3.9' with architecture 'x64' was not
  found for Ubuntu 26.04", run 43928092085).

Scope:
- `open_marc_tasks/cli.py` and console script `omt` in `pyproject.toml`:
  `omt run TASK INPUT OUTPUT`. Loads the task (`load_task`), reads INPUT as
  binary MARC, runs it (`run_task`), writes binary MARC to OUTPUT. Exit 0 on
  success. On any error: exit 1, exactly one line on stderr starting `omt:`,
  and OUTPUT is not created (or, if it already existed, is left byte-for-byte
  unchanged).
- Input rules: refuse an empty input file; refuse a record pymarc can't parse
  (the reader yields `None`), including a truncated last record; refuse a record
  whose Leader/09 is not `a` (MARC-8 or unknown encoding: "convert to UTF-8
  first"); refuse invalid UTF-8. Messages name the 1-based record number.
- Output rules: write to a temporary file in OUTPUT's directory and rename it
  over OUTPUT only after every record succeeded. Refuse OUTPUT that resolves to
  the same file as INPUT. Refuse a result record with no fields left (pymarc
  can't read such a record back), naming the record number.
- `.github/workflows/test.yml`: run the Python 3.9 job in the
  `python:3.9-slim` container (no setup-python for that job); keep the 3.13 job.
- README: `omt run` usage, one example.

Out of scope:
- `omt import`, new commands, MARC-8 conversion, reading `.mrk` text.

Likely files:
- open_marc_tasks/cli.py, pyproject.toml, README.md
- tests/test_cli.py
- .github/workflows/test.yml

Acceptance tests:
- `omt run` on the `delete_field/wildcard` conformance case writes output that
  matches its `expected.mrc` record for record, and a non-ASCII value from the
  input is byte-identical in the output, so the CLI and the library agree.
- One parametrized test: an invalid task, an empty input, a valid record followed
  by a truncated one, a MARC-8 record (Leader/09 blank), invalid UTF-8, INPUT
  given as OUTPUT, and a task that deletes every field — each exits 1 with one
  `omt:` line, and a pre-existing OUTPUT file is unchanged (or no OUTPUT
  appears when there was none), so a failed run never damages files.

Verification:
- The Python 3.9 gate in AGENTS.md "Build and test", run from the worktree.

Handoff:
- (orchestrator fills in after the check)

Review:
- (orchestrator fills in)
