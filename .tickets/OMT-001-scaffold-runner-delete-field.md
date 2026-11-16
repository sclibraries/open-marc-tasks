Title: Scaffold the package with format v0.1, the task runner, the CLI, the conformance harness and delete_field

Status: Ready
Size: M
Tier: major — new project: first manifest and dependencies
Milestone: M1 — Format and runner
Base: the local `main` commit that adds this ticket
Branch: codex/OMT-001

Why:
- Every later command needs a place to live, a documented format, a way to run
  a task over records, and a conformance suite that says what correct means.
  Without these, nothing else in the plan can be built or checked.

Scope:
- `pyproject.toml` (setuptools): package `open_marc_tasks`, `requires-python >=3.9`,
  dependency `pymarc>=5.1.2,<6`, extra `test` = `pytest`, `jsonschema`;
  console script `omt`. `.gitignore` with `.worktrees/`, `reference/`, build output.
- `spec/format.md` v0.1: task object (`format_version` "0.1", `name`,
  `description`, ordered `steps`), step object (`command` plus that command's
  named settings), the matching rule (ARCHITECTURE.md "Fixed points"), and the
  `delete_field` command.
- `spec/task.schema.json` (JSON Schema draft 2020-12) for the same.
- `delete_field`: setting `tag`, three characters, digits or `X`, where `X`
  matches any digit (so `9XX`, `0X9`). Deletes every matching field, control
  or data. Nothing else in v0.1.
- Library: `load_task(path) -> Task` validates with plain Python (no jsonschema
  at runtime) and raises `TaskError` naming the step number and problem;
  `run_task(task, records) -> Iterator[Record]` applies steps in order to each
  record; `records_match(a, b) -> bool` implements the matching rule.
- CLI: `omt run TASK INPUT OUTPUT` reads binary MARC (UTF-8), writes binary
  MARC, exits non-zero with a one-line message on `TaskError` or unreadable
  input, and leaves no output file behind on failure.
- Conformance harness: a pytest test that discovers every
  `conformance/<command>/<case>/` folder (`task.json`, `input.mrc`,
  `expected.mrc`) and checks `records_match` record by record. Two
  `delete_field` cases: exact tag (`029`), wildcard (`9XX`, with a 999 and a 949
  and an unrelated 856 that must stay). Records synthetic. Expected files may be
  produced by the library for now; OMT-002 regenerates them from MarcEdit.
- GitHub Actions workflow: pytest on Python 3.9 and 3.12.
- README: what the project is, `omt run` usage, a link to `spec/format.md`.

Out of scope:
- Any other command, conditions, the importer, the MarcEdit reference runner,
  MARC-8 handling beyond refusing non-UTF-8 input with a clear message.

Likely files:
- pyproject.toml, .gitignore, README.md
- spec/format.md, spec/task.schema.json
- open_marc_tasks/__init__.py, task.py (load/validate/run), match.py, cli.py
- open_marc_tasks/commands/__init__.py, open_marc_tasks/commands/delete_field.py
- conformance/delete_field/{exact-tag,wildcard}/…
- tests/test_conformance.py, tests/test_task_loading.py, tests/test_cli.py
- .github/workflows/test.yml

Acceptance tests:
- Both `delete_field` conformance cases pass through `run_task`, and the 856 in
  the wildcard case survives, so wildcards can't over-delete.
- A task with an unknown command, a missing `tag`, or a malformed tag (`9X`,
  `abc`) is refused by `load_task` with the step number in the message, so a
  bad task never half-runs.
- Every conformance `task.json` validates against `spec/task.schema.json`
  (test-only jsonschema), so the spec and the library can't drift.
- `records_match` treats a field-order difference as a mismatch and ignores 005,
  so the success measure means what the spec says.
- `omt run` on a valid task writes the expected output; on an invalid task or an
  empty/unreadable input it exits non-zero, prints one line, and writes no output file.

Verification:
- The Python 3.9 gate in AGENTS.md "Build and test", run from the worktree.

Plan:
1. Manifest, package skeleton, .gitignore.
2. Spec and schema for the task object and delete_field.
3. load_task / run_task / records_match and delete_field.
4. Conformance cases and harness; loading and CLI tests.
5. CLI, README, CI workflow; run the gate.

Handoff:
- (orchestrator fills in after the check)

Review:
- (orchestrator fills in)
