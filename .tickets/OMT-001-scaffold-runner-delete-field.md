Title: Scaffold the package with format v0.1, the task runner, the matching rule, the conformance harness and delete_field

Status: In-Review
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
  dependency `pymarc>=5.1.2,<6`, extra `test` = `pytest`, `jsonschema`.
  `.gitignore` with `.worktrees/`, `reference/`, build output.
- `spec/format.md` v0.1: task object (`format_version` "0.1", `name`,
  `description`, ordered `steps`), step object (`command` plus that command's
  named settings; unknown settings are an error), the matching rule
  (ARCHITECTURE.md "Fixed points"), and the `delete_field` command.
- `spec/task.schema.json` (JSON Schema draft 2020-12) for the same.
- `delete_field`: setting `tag`, three characters, digits or uppercase `X`,
  where `X` matches any digit (`9XX`, `0X9`). Deletes every matching field,
  control or data, keeping the order of the rest.
- Library (`open_marc_tasks`):
  - `load_task(path) -> Task`: validates with plain Python (no jsonschema at
    runtime). Raises `TaskError` for unreadable files, malformed JSON, a wrong
    `format_version`, a missing or unknown command, missing or malformed or
    unknown settings; the message names the step number when the problem is in
    a step.
  - `run_task(task, records) -> Iterator[Record]`: consumes any iterable of
    pymarc records once, applies every step in order to each record **in place**,
    and yields each record in input order. The spec says records are modified in place.
  - `records_match(a, b) -> bool`: the matching rule. Compares tags, indicators,
    control-field data, subfield codes, order and values exactly (whitespace
    preserved), and Leader 05–09 and 17–19. Ignores 005 and Leader 00–04 and
    12–16. Does not modify its inputs.
- Conformance harness (`tests/test_conformance.py`): discovers every
  `conformance/<command>/<case>/` folder. Each holds `task.json`, `input.mrc`,
  `expected.mrc` and `marcedit-task.txt` (the MarcEdit task line(s) that
  produced `expected.mrc`). Fails when zero cases are found, a folder is
  incomplete, or the output and expected files have different record counts.
- `delete_field` cases, records synthetic (`example.edu`), at least one
  non-ASCII UTF-8 value:
  - `exact-tag`: delete `029`.
  - `wildcard`: delete `9XX` from records with repeated 9XX fields (949, 999,
    999) and an 856 that must stay.
  - `control-and-absent`: delete `0X9` (removes a 009 control field and a 029)
    plus a record with no matching field.
  - `expected.mrc` comes from real MarcEdit: run each case's
    `marcedit-task.txt` with the MarcEdit copy in `reference/marcedit/`
    (AGENTS.md "Build and test", reference runs). If `reference/marcedit/` is
    missing, stop and say so in the handoff; don't generate expected output
    with this library. Known MarcEdit behavior (observed 2026-11-13): `-task`
    takes a tab-separated tasks text file, not a `.task` zip; a delete line is
    `DELETE<TAB><tag><TAB><TAB>0<TAB>False<TAB>False<TAB>False<TAB>False<TAB>False`;
    when a task changes nothing, MarcEdit writes an empty output file (then the
    expected output is the input unchanged). If MarcEdit treats `X` or control
    fields differently from this ticket, the MarcEdit result wins: record it in
    the handoff and make the spec and code follow it.
- GitHub Actions workflow: Python 3.9 with `pymarc==5.1.2`, and Python 3.13 with
  the newest pymarc `<6`; both run pytest.
- README: what the project is, a link to `spec/format.md`.

Out of scope:
- The CLI (OMT-002), any other command, conditions, the importer, MARC-8 or
  input/output file handling, and `ARCHITECTURE.md` (the orchestrator updates it).

Likely files:
- pyproject.toml, .gitignore, README.md
- spec/format.md, spec/task.schema.json
- open_marc_tasks/__init__.py, task.py, match.py
- open_marc_tasks/commands/__init__.py, open_marc_tasks/commands/delete_field.py
- conformance/delete_field/{exact-tag,wildcard,control-and-absent}/…
- tests/test_conformance.py, tests/test_task_loading.py, tests/test_match.py
- .github/workflows/test.yml

Acceptance tests:
- All three `delete_field` conformance cases pass, with expected output from
  MarcEdit, so the library is checked against MarcEdit, not against itself.
- One parametrized test feeds the same invalid tasks (wrong version, unknown
  command, missing/malformed `tag` such as `9X`, `abc`, `9xx`, an unknown
  setting, a step that isn't an object) to both `load_task` and the JSON
  Schema: both reject every one, and every conformance `task.json` passes
  both. Malformed JSON gives a `TaskError`. So the spec and the library can't drift.
- One parametrized `records_match` test: a difference in field order, an
  indicator, a subfield code, a subfield value's whitespace, control-field data,
  or Leader 06 is a mismatch; a different 005 or Leader 00–04 is a match. So the
  success measure means exactly what the spec says.
- The harness fails on a record-count difference and on zero discovered cases,
  so a truncated output can't pass.
- `run_task` over a one-pass generator of three records yields all three, in
  order, with the step applied to each.

Verification:
- The Python 3.9 gate in AGENTS.md "Build and test", run from the worktree.
- The same gate with `pip install "pymarc==5.1.2"` added before pytest.

Plan:
1. Manifest, package skeleton, .gitignore.
2. Spec and schema for the task object and delete_field.
3. load_task / run_task / records_match and delete_field.
4. Conformance cases: write synthetic inputs and MarcEdit task lines, generate
   expected output with MarcEdit, add the harness.
5. Loading and match tests, README, CI; run both gates.

Plan check (2026-11-16, OMT-001 01-verify, BLOCKING) answered:
- 1 (worktree missing): wrong for this flow; the runner creates it at build time.
- 2, 3 (library-generated expected output): fixed; expected output now comes from MarcEdit in this ticket.
- 4, 9, 10, 11, 12, 13: added as scope lines and acceptance tests above.
- 5, 6, 7, 8 (CLI input, MARC-8, output-file safety, zero-field records): moved with the CLI to OMT-002.
- 14 (ARCHITECTURE.md): the orchestrator updates it when the ticket completes.
- More than five real findings, so the ticket was split (CLI → OMT-002) per the tier rules.

Handoff:
- (orchestrator fills in after the check)

Review:
- (orchestrator fills in)
