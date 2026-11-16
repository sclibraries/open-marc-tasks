Title: Add the MarcEdit reference runner and a check that conformance answers really come from MarcEdit

Status: Completed
Size: S
Tier: normal — new developer tooling; no library behavior changes
Milestone: M1 — Format and runner
Base: the local `main` commit that adds this ticket
Branch: codex/OMT-003

Why:
- Every command ticket needs expected output from real MarcEdit. Today each
  worker re-derives the Docker command by hand, and OMT-002's first round
  showed an expected file can be edited without MarcEdit and nothing notices.
  One repeatable command, and a check that compares every committed
  `expected.mrc` with a fresh MarcEdit run, close both gaps.

Scope:
- `tools/marcedit_reference.py` (dev only, stdlib + pymarc):
  - `run_marcedit(tasks_file: Path, input_mrc: Path, output_mrc: Path, marcedit_dir: Path) -> None`:
    runs `cmarcedit -s -d -task -silent` in
    `mcr.microsoft.com/dotnet/runtime-deps:8.0` (`--platform linux/amd64
    --network none`, `HOME=/tmp`, `DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1`),
    mounting `marcedit_dir` read-only and a temporary work folder. When
    MarcEdit writes an empty output, `output_mrc` is a copy of the input (the
    observed "no changes" behavior; spec "Conformance").
  - CLI: `python tools/marcedit_reference.py regenerate <case-dir>...` writes
    each case's `expected.mrc` from its `marcedit-task.txt` and `input.mrc`.
    Default `marcedit_dir` is `reference/marcedit`; a clear error if it's missing.
- `tests/test_reference.py`: for every conformance case, run MarcEdit fresh and
  assert the committed `expected.mrc` matches it record for record
  (`records_match`, same record count). Skips with the reason
  "reference/marcedit not found" when the MarcEdit copy is absent (CI), so it
  runs on developer machines and in Codex rounds only.
- `spec/format.md` "Conformance": one paragraph on regenerating expected output
  with the tool. `README.md`: a short "Developer: reference runs" section.

Out of scope:
- The match-count measurement over MarcEdit task folders (needs the importer;
  moves to the importer ticket). Any library or CLI change. Committing MarcEdit.

Likely files:
- tools/marcedit_reference.py
- tests/test_reference.py
- spec/format.md, README.md

Acceptance tests:
- With `reference/marcedit/` present, `tests/test_reference.py` passes for all
  four existing `delete_field` cases, so the committed answers are proven to be
  MarcEdit's.
- Changing one byte of a committed field value in a copy of a case makes that
  test fail (shown once in the handoff, not committed), so an edited answer can't pass.
- Without `reference/marcedit/`, the test reports a skip with the reason above,
  and the rest of the suite is unaffected, so CI stays green.
- `regenerate` on the four cases reproduces the committed `expected.mrc` files
  with no `git diff` under `conformance/`.

Verification:
- The Python 3.9 gate in AGENTS.md "Build and test" (reference tests skip there:
  the gate container has no Docker).
- On the host from the worktree: `python3 -m pytest -q tests/test_reference.py`
  (runs MarcEdit through Docker) and report its counts.

Handoff:
- Head 73d637a, merged into main (owner OK 2026-11-16). Python 3.9 gate 30 passed, 1 skipped; host reference test passed against MarcEdit 7.6.

Review:
- All acceptance tests met; extra 'docker not found' skip accepted. No bloat, no fix round.
