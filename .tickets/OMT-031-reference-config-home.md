Title: Let the MarcEdit reference runner resolve called tasks and rule files itself

Status: In-Progress
Size: S
Tier: normal — reference tooling only; no engine or format change
Milestone: M2 — Commands
Base: the local `main` commit that adds this ticket
Branch: codex/OMT-031

Why:
- OMT-028 checks TASK_LIST by pasting called tasks in place for MarcEdit, an
  assumption. The upcoming cleanup commands (CLEANSMARTCHARACTERS, REMOVEISBD)
  read rule files MarcEdit couldn't find, so they silently did nothing.
  Orchestrator findings 2026-11-19 (decompiled cmarcedit plus confirming runs)
  show where command-line MarcEdit 7.6 looks:
  - `UserDataPath` = `$HOME/.config/marcedit75/` when that folder exists.
  - Rule files named on a line (`CLEANSMARTCHARACTERS<TAB>smartlist.txt`,
    `REMOVEISBD<TAB>remove_isbd_punc.txt`) are read from `UserDataPath/configs/`;
    a missing file changes nothing.
  - A top-level `TASK_LIST<TAB>name<TAB>tasksfile-X.txt` resolves `tasksfile-X.txt`
    against the process working directory; a TASK_LIST inside a called task
    resolves against `UserDataPath/macros/`. MarcEdit expands the called lines in
    place. Confirmed: `HOME=/work/home`, working directory
    `/work/home/.config/marcedit75/macros`, a two-level call ran both tasks.
- Note: TASK_LIST names the *file* (`tasksfile-X.txt`, the last column); in a
  `.task` archive the same task's entry is named `<name>.-tasksfile-X.txt`.

Scope:
- `tools/marcedit_reference.py` `run_marcedit`: optional `macros` (mapping of
  file name → task text) and `configs` (folder of rule files). When given, build
  a temporary `home/.config/marcedit75/{macros,configs}`, run with `HOME` set to
  it and the working directory set to its `macros` folder. Without them, runs
  are unchanged.
- Conformance: a case may have `marcedit-macros/` and `marcedit-configs/`
  folders, passed to the runner by `regenerate` and `tests/test_reference.py`.
  Change `conformance/call_task/inline-order/` to a real TASK_LIST line plus its
  file in `marcedit-macros/`; its regenerated `expected.mrc` must be unchanged.
- `tools/measure.py`: stop inlining. Stage every task the measured task calls,
  recursively, under its TASK_LIST file name, and pass a new `--configs DIR`
  through. The not-translated reasons for missing, ambiguous or incomplete
  called tasks stay as they are.

Out of scope:
- Implementing any cleanup command; the private rule files (they stay outside
  the repo); engine code.

Likely files:
- tools/marcedit_reference.py, tools/measure.py
- tests/test_reference.py, tests/test_conformance.py (only to pass the folders)
- conformance/call_task/inline-order/…
- spec/format.md (the measure paragraph), ARCHITECTURE.md (one line)

Acceptance tests:
- `call_task/inline-order` passes the suite and `tests/test_reference.py` on the
  host with the real TASK_LIST, its `expected.mrc` byte-identical to before.
- All other conformance cases pass unchanged.
- No new test functions; the reference test is the check.

Verification:
- The Python 3.9 gate in AGENTS.md "Build and test".
- On the host from the worktree: `python3 -m pytest -q tests/test_reference.py`, counts reported.
- The orchestrator reruns the private measurement with `--library` and `--configs`;
  it must still be 81/100 with 0 differing.

Handoff:
- (orchestrator fills in after the check)

Review:
- (orchestrator fills in)
